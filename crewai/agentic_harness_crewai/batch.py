"""CrewAI-owned serial frozen 12-target batch with explicit zero-retry budgets."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from crewai.flow import Flow, start
from crewai.flow.persistence import SQLiteFlowPersistence, persist
from crewai.llms.hooks.base import BaseInterceptor
from crewai.memory.storage.factory import set_memory_storage_factory

from .canonical_slice import (
    MODEL_ID, PROMPT_VERSION, SYSTEM_PROMPT, TEMPERATURE, VALIDATOR_VERSION,
    ModelOutput, RunScopedMemoryStorage, build_live_llm, canonical_sha256,
    context_summary, require, unwrap, user_prompt,
)
from .tools import build_tools


TARGET_SEQUENCE_SHA256 = "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728"
MAX_TARGETS = 12


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class BatchRequestBudgetExceeded(RuntimeError):
    """Raised before an unbudgeted logical or physical provider request."""


class BatchRequestBudget:
    def __init__(self, permitted: int = MAX_TARGETS) -> None:
        self.permitted = permitted
        self.logical_generations = 0
        self.claimed_sequences: list[int] = []

    def claim(self, sequence: int) -> None:
        if sequence in self.claimed_sequences:
            raise BatchRequestBudgetExceeded(f"Target {sequence} already consumed its logical permit")
        if self.logical_generations >= self.permitted:
            raise BatchRequestBudgetExceeded("Logical generation budget exhausted")
        self.claimed_sequences.append(sequence)
        self.logical_generations += 1


class BatchRequestInterceptor(BaseInterceptor[httpx.Request, httpx.Response]):
    def __init__(self, permitted: int = MAX_TARGETS) -> None:
        self.permitted = permitted
        self.actual_provider_requests = 0
        self.successful_provider_responses = 0
        self.response_statuses: list[int] = []

    def on_outbound(self, message: httpx.Request) -> httpx.Request:
        if self.actual_provider_requests >= self.permitted:
            raise BatchRequestBudgetExceeded("Provider request budget exhausted before transport")
        self.actual_provider_requests += 1
        return message

    def on_inbound(self, message: httpx.Response) -> httpx.Response:
        self.response_statuses.append(message.status_code)
        if 200 <= message.status_code < 300:
            self.successful_provider_responses += 1
        return message

    def snapshot(self) -> dict[str, Any]:
        return {
            "logical_generation_budget": MAX_TARGETS,
            "provider_request_budget": MAX_TARGETS,
            "actual_provider_requests": self.actual_provider_requests,
            "successful_provider_responses": self.successful_provider_responses,
            "transport_retries": 0,
            "sdk_retries": 0,
            "guardrail_retries": 0,
            "structured_output_correction_calls": 0,
            "repair_calls": 0,
            "fallback_calls": 0,
            "learning_calls": 0,
            "feedback_collapse_calls": 0,
        }


class BatchState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = "unset"
    run_id: str = "unset"
    framework_origin: str = "crewai"
    status: str = "initialized"
    lifecycle_stage: str = "initialized"
    target_sequence_sha256: str = TARGET_SEQUENCE_SHA256
    current_sequence: int = 0
    completed_sequences: list[int] = Field(default_factory=list)
    recommendation_ids: list[str] = Field(default_factory=list)
    target_ledger: list[dict[str, Any]] = Field(default_factory=list)
    model_outputs: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    submissions: list[dict[str, Any]] = Field(default_factory=list)
    statuses: list[dict[str, Any]] = Field(default_factory=list)
    provider_accounting: dict[str, Any] = Field(default_factory=dict)
    operation_accounting: dict[str, int] = Field(default_factory=lambda: {
        "discovery": 0, "context": 0, "generation": 0, "assembly": 0,
        "validation": 0, "submission": 0, "status": 0,
    })
    source_projection_before: str | None = None
    source_projection_after: str | None = None
    started_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


def build_batch_flow(*, client: Any, correlation_id: str, run_id: str,
                     runtime_db: Path, llm: Any, request_budget: BatchRequestBudget,
                     interceptor: BatchRequestInterceptor | None = None,
                     expected_targets: list[dict[str, Any]]) -> Flow[BatchState]:
    """Build the one-pass serial Flow. A pre-existing runtime fails closed."""
    require(len(expected_targets) == MAX_TARGETS, "Expected target list must contain 12 entries")
    require(canonical_sha256(expected_targets) == TARGET_SEQUENCE_SHA256,
            "Expected target sequence hash drifted")
    require(runtime_db.parent.name == run_id, "Runtime must be scoped to the logical run")
    require("/shared/" not in runtime_db.resolve().as_posix(), "Runtime may not use shared/")
    require(not runtime_db.parent.exists(), "Stale or previously accepted batch runtime exists")
    runtime_db.parent.mkdir(parents=True, exist_ok=False)
    persistence = SQLiteFlowPersistence(str(runtime_db))
    set_memory_storage_factory(lambda spec: RunScopedMemoryStorage())
    tools = build_tools(client, correlation_id=correlation_id)

    def save_checkpoint(flow: Flow[BatchState], stage: str) -> None:
        flow.state.lifecycle_stage = stage
        flow.state.updated_at = utc_now()
        persistence.save_state(flow.state.id, stage, flow.state)

    @persist(persistence)
    class FrozenBatchFlow(Flow[BatchState]):
        @start()
        def process_batch(self) -> dict[str, Any]:
            discovery = unwrap(tools["find_images_needing_review"].run(), "find_images_needing_review")
            targets = discovery.get("targets")
            require(targets == expected_targets, "Discovered target identity/order drifted")
            require(canonical_sha256(targets) == TARGET_SEQUENCE_SHA256, "Target hash drifted")
            self.state.operation_accounting["discovery"] += 1
            self.state.status = "running"
            save_checkpoint(self, "targets_discovered")

            for expected_sequence, target in enumerate(targets, start=1):
                require(target["sequence"] == expected_sequence, "Target-order drift")
                require(expected_sequence not in self.state.completed_sequences,
                        "Re-entry into completed target")
                self.state.current_sequence = expected_sequence
                save_checkpoint(self, "target_selected")

                context = unwrap(tools["get_image_context"].run(target=target), "get_image_context")
                require(context.get("target") == target, "Context target mismatch")
                self.state.operation_accounting["context"] += 1
                provenance = context_summary(context)
                save_checkpoint(self, "context_retrieved")

                request_budget.claim(expected_sequence)
                self.state.operation_accounting["generation"] += 1
                prompt = user_prompt(target, context)
                raw = llm.call(messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": context["image"]["representation"]["value"],
                         "detail": "auto"},
                    ]},
                ])
                parsed = raw if isinstance(raw, ModelOutput) else ModelOutput.model_validate_json(str(raw))
                self.state.model_outputs.append({
                    "sequence": expected_sequence,
                    "proposed_alt_text": parsed.proposed_alt_text,
                })
                save_checkpoint(self, "model_output_parsed")

                recommendation = {
                    "schema_version": 1, "target": target,
                    "proposed_alt_text": parsed.proposed_alt_text.strip(),
                    "source_framework": "crewai", "run_id": self.state.run_id,
                    "evidence_hash": provenance["evidence_hash"],
                    "validator_version": VALIDATOR_VERSION,
                }
                self.state.operation_accounting["assembly"] += 1
                self.state.recommendations.append(recommendation)
                save_checkpoint(self, "recommendation_assembled")

                fresh = unwrap(tools["get_image_context"].run(target=target), "get_image_context")
                self.state.operation_accounting["context"] += 1
                require(fresh.get("evidence_hash") == provenance["evidence_hash"],
                        "Context changed before validation/submission")
                self.state.operation_accounting["validation"] += 1
                save_checkpoint(self, "validator_passed")

                submitted = unwrap(tools["submit_recommendation"].run(recommendation=recommendation),
                                   "submit_recommendation")
                self.state.operation_accounting["submission"] += 1
                recommendation_id = submitted["uuid"]
                require(recommendation_id not in self.state.recommendation_ids,
                        "Duplicate recommendation UUID")
                status = unwrap(tools["get_recommendation_status"].run(
                    recommendation_id=recommendation_id), "get_recommendation_status")
                self.state.operation_accounting["status"] += 1
                require(status.get("status") == "pending", "Recommendation is not pending")

                after = unwrap(tools["get_image_context"].run(target=target), "get_image_context")
                self.state.operation_accounting["context"] += 1
                require(after.get("evidence_hash") == provenance["evidence_hash"],
                        "Source context changed after submission")
                self.state.recommendation_ids.append(recommendation_id)
                self.state.submissions.append({
                    "sequence": expected_sequence, "uuid": recommendation_id,
                    "node_id": submitted["node_id"], "revision_id": submitted["revision_id"],
                })
                self.state.statuses.append({
                    "sequence": expected_sequence, "uuid": recommendation_id,
                    "status": status["status"], "revision_id": status["revision_id"],
                })
                self.state.completed_sequences.append(expected_sequence)
                self.state.target_ledger.append({
                    "sequence": expected_sequence,
                    "target_sha256": canonical_sha256(target),
                    "context_evidence_hash": provenance["evidence_hash"],
                    "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                    "recommendation_uuid": recommendation_id,
                    "revision_id": submitted["revision_id"],
                    "status": status["status"],
                    "stage": "target_finalized",
                })
                save_checkpoint(self, "target_finalized")

            require(self.state.completed_sequences == list(range(1, 13)), "Batch completion drift")
            require(len(set(self.state.recommendation_ids)) == 12, "Recommendation duplicate detected")
            self.state.provider_accounting = interceptor.snapshot() if interceptor else {
                "logical_generation_budget": 12, "provider_request_budget": 12,
                "actual_provider_requests": 0, "successful_provider_responses": 0,
                "rehearsal_fake": True, "transport_retries": 0, "sdk_retries": 0,
                "guardrail_retries": 0, "structured_output_correction_calls": 0,
                "repair_calls": 0, "fallback_calls": 0, "learning_calls": 0,
                "feedback_collapse_calls": 0,
            }
            self.state.provider_accounting["logical_generations"] = request_budget.logical_generations
            self.state.status = "complete"
            self.state.current_sequence = 12
            save_checkpoint(self, "batch_complete")
            return {"status": "complete", "recommendations": list(self.state.recommendation_ids)}

    flow = FrozenBatchFlow(suppress_flow_events=True, tracing=False)
    flow.state.id = run_id
    flow.state.run_id = run_id
    return flow


__all__ = [
    "BatchRequestBudget", "BatchRequestBudgetExceeded", "BatchRequestInterceptor",
    "BatchState", "MAX_TARGETS", "TARGET_SEQUENCE_SHA256", "build_batch_flow",
    "build_live_llm",
]
