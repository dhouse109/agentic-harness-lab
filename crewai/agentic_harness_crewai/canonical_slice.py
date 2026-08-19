"""CrewAI-owned canonical target-1 Flow with a one-request provider budget.

This module owns CrewAI orchestration and Flow state only. Frozen target
discovery, context retrieval, validation/submission, persistence in Drupal,
and status observation remain behind the accepted Step 2B.03 adapters.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from crewai import LLM
from crewai.flow import Flow, listen, start
from crewai.flow.persistence import SQLiteFlowPersistence, persist
from crewai.llms.hooks.base import BaseInterceptor
from crewai.memory.storage.backend import StorageBackend
from crewai.memory.storage.factory import set_memory_storage_factory
from crewai.memory.types import MemoryRecord, ScopeInfo

from .tools import build_tools


MODEL_ID = "gpt-4.1-mini-2025-04-14"
TEMPERATURE = 0.0
PROMPT_VERSION = "crewai-alt-text-v1.0.0"
VALIDATOR_VERSION = "gate05-validator-1.0.0"
TARGET_SEQUENCE_SHA256 = "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728"
CANONICAL_TARGET = {
    "schema_version": 1,
    "sequence": 1,
    "node_uuid": "344eb273-ac74-5be8-85fb-6c2efd1f93a6",
    "revision_id": 1,
    "field_name": "field_image",
    "delta": 0,
    "file_uuid": "07af2dce-7bfd-5de6-b291-e090669eda25",
    "target_state": "missing",
    "existing_alt": "",
}

SYSTEM_PROMPT = """You draft one alt-text recommendation for one verified Drupal image-field usage.

Use only the supplied image and page context. Describe the image's meaningful content and purpose
in that context. Be concise and specific. Do not begin with \"image of\", \"photo of\", \"picture of\",
\"graphic of\", \"Here is\", or \"Alt text:\". Do not repeat the filename. Do not invent facts that are
not visible in the image or stated in the supplied page context.

Return only the structured model-output object required by
recommendation.schema.json#/$defs/model_output. The proposed_alt_text value must be nonempty and no
more than 250 Unicode characters."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


class ModelOutput(BaseModel):
    """The only inferential field retained from the provider response."""

    model_config = ConfigDict(extra="forbid")
    proposed_alt_text: str = Field(min_length=1, max_length=250)


class ProviderRequestBudgetExceeded(RuntimeError):
    """Raised before an unbudgeted logical or physical provider request."""


class SingleRequestBudget:
    """One logical-generation permit, separate from transport accounting."""

    def __init__(self) -> None:
        self.logical_generations = 0

    def claim(self) -> None:
        if self.logical_generations >= 1:
            raise ProviderRequestBudgetExceeded("The one logical generation budget is exhausted")
        self.logical_generations += 1


class SingleRequestInterceptor(BaseInterceptor[httpx.Request, httpx.Response]):
    """Count SDK HTTP attempts and block a second request before transport."""

    def __init__(self) -> None:
        self.actual_provider_requests = 0
        self.successful_provider_responses = 0
        self.response_statuses: list[int] = []

    def on_outbound(self, message: httpx.Request) -> httpx.Request:
        if self.actual_provider_requests >= 1:
            raise ProviderRequestBudgetExceeded("A second provider HTTP request was blocked before transport")
        self.actual_provider_requests += 1
        return message

    def on_inbound(self, message: httpx.Response) -> httpx.Response:
        self.response_statuses.append(message.status_code)
        if 200 <= message.status_code < 300:
            self.successful_provider_responses += 1
        return message

    def snapshot(self) -> dict[str, Any]:
        return {
            "actual_provider_requests": self.actual_provider_requests,
            "successful_provider_responses": self.successful_provider_responses,
            "response_statuses": list(self.response_statuses),
            "transport_retries": 0,
            "provider_retries": 0,
            "guardrail_correction_retries": 0,
            "structured_repair_calls": 0,
            "fallback_provider_calls": 0,
            "learning_distillation_calls": 0,
            "feedback_collapse_calls": 0,
        }


class RunScopedMemoryStorage(StorageBackend):
    """Deterministic run-local memory backend selected via the public factory.

    The canonical Flow does not write memory records. This backend prevents
    automatic Flow construction from selecting ambient/default storage while
    avoiding the private ``_skip_auto_memory`` switch.
    """

    def __init__(self) -> None:
        self.records: dict[str, MemoryRecord] = {}

    def save(self, records: list[MemoryRecord]) -> None:
        for record in records:
            self.records[str(record.id)] = record

    def search(self, query_embedding: list[float], scope_prefix: str | None = None,
               categories: list[str] | None = None, metadata_filter: dict[str, Any] | None = None,
               limit: int = 10, min_score: float = 0.0) -> list[tuple[MemoryRecord, float]]:
        del query_embedding, scope_prefix, categories, metadata_filter, limit, min_score
        return []

    def delete(self, scope_prefix: str | None = None, categories: list[str] | None = None,
               record_ids: list[str] | None = None, older_than: datetime | None = None,
               metadata_filter: dict[str, Any] | None = None) -> int:
        del scope_prefix, categories, older_than, metadata_filter
        ids = record_ids or list(self.records)
        before = len(self.records)
        for record_id in ids:
            self.records.pop(record_id, None)
        return before - len(self.records)

    def update(self, record: MemoryRecord) -> None:
        self.records[str(record.id)] = record

    def get_record(self, record_id: str) -> MemoryRecord | None:
        return self.records.get(record_id)

    def list_records(self, scope_prefix: str | None = None, limit: int = 200,
                     offset: int = 0) -> list[MemoryRecord]:
        del scope_prefix
        return list(self.records.values())[offset: offset + limit]

    def get_scope_info(self, scope: str) -> ScopeInfo:
        return ScopeInfo(scope=scope, record_count=len(self.records), categories={}, date_range=None, child_scopes=[])

    def list_scopes(self, parent: str = "/") -> list[str]:
        del parent
        return []

    def list_categories(self, scope_prefix: str | None = None) -> dict[str, int]:
        del scope_prefix
        return {}

    def count(self, scope_prefix: str | None = None) -> int:
        del scope_prefix
        return len(self.records)

    def reset(self, scope_prefix: str | None = None) -> None:
        del scope_prefix
        self.records.clear()

    async def asave(self, records: list[MemoryRecord]) -> None:
        self.save(records)

    async def asearch(self, query_embedding: list[float], scope_prefix: str | None = None,
                      categories: list[str] | None = None, metadata_filter: dict[str, Any] | None = None,
                      limit: int = 10, min_score: float = 0.0) -> list[tuple[MemoryRecord, float]]:
        return self.search(query_embedding, scope_prefix, categories, metadata_filter, limit, min_score)

    async def adelete(self, scope_prefix: str | None = None, categories: list[str] | None = None,
                      record_ids: list[str] | None = None, older_than: datetime | None = None,
                      metadata_filter: dict[str, Any] | None = None) -> int:
        return self.delete(scope_prefix, categories, record_ids, older_than, metadata_filter)


class CanonicalSliceState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = "unset"
    run_id: str = "unset"
    framework_origin: str = "crewai"
    lifecycle_stage: str = "initialized"
    status: str = "running"
    continuation_status: str = "untested"
    target_sequence_hash: str = f"sha256:{TARGET_SEQUENCE_SHA256}"
    canonical_target: dict[str, Any] | None = None
    context_provenance: dict[str, Any] | None = None
    prompt_version: str = PROMPT_VERSION
    prompt_sha256: str | None = None
    model_id: str = MODEL_ID
    temperature: float = TEMPERATURE
    raw_model_output: dict[str, Any] | None = None
    assembled_recommendation: dict[str, Any] | None = None
    deterministic_validation: dict[str, Any] | None = None
    recommendation_id: str | None = None
    recommendation_revision_id: int | None = None
    review_status: str | None = None
    persistence_provenance: dict[str, Any] | None = None
    request_accounting: dict[str, Any] = Field(default_factory=dict)
    started_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


def context_summary(context: dict[str, Any]) -> dict[str, Any]:
    article = context["article"]
    image = context["image"]
    representation = image["representation"]
    body = article["body_plain"]
    value = representation["value"]
    return {
        "evidence_hash": context["evidence_hash"],
        "target": context["target"],
        "article_title": article["title"],
        "article_body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "article_body_length": len(body),
        "image_sha256": image["sha256"],
        "image_filename": image["filename"],
        "image_mime_type": image["mime_type"],
        "image_width": image.get("width"),
        "image_height": image.get("height"),
        "representation_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
        "representation_length": len(value),
        "raw_body_retained": False,
        "raw_representation_retained": False,
    }


def user_prompt(target: dict[str, Any], context: dict[str, Any]) -> str:
    article = context["article"]
    image = context["image"]
    existing_alt = context.get("existing_alt")
    width = image.get("width") if image.get("width") is not None else "unknown"
    height = image.get("height") if image.get("height") is not None else "unknown"
    return (
        "TARGET\n"
        f"- Sequence: {target['sequence']}\n"
        f"- Node UUID: {target['node_uuid']}\n"
        f"- Article revision: {target['revision_id']}\n"
        f"- Field: {target['field_name']}\n"
        f"- Delta: {target['delta']}\n"
        f"- File UUID: {target['file_uuid']}\n"
        f"- Existing alt text: {'null' if existing_alt is None else existing_alt}\n\n"
        "PAGE CONTEXT\n"
        f"- Article title: {article['title']}\n"
        f"- Article body: {article['body_plain']}\n\n"
        "IMAGE CONTEXT\n"
        f"- Filename: {image['filename']}\n"
        f"- MIME type: {image['mime_type']}\n"
        f"- Dimensions: {width} x {height}\n"
        "- Image input: identical PNG bytes, represented as a Base64-encoded PNG data URL "
        "with detail=auto or the Drupal AI ImageFile equivalent over the same bytes\n\n"
        "Produce the model-output object only."
    )


def unwrap(result: Any, expected_tool: str) -> dict[str, Any]:
    require(isinstance(result, dict), f"{expected_tool} did not return an object")
    require(result.get("tool_name") == expected_tool, f"{expected_tool} envelope name mismatch")
    require(result.get("ok") is True and result.get("error") is None, f"{expected_tool} failed")
    require(isinstance(result.get("data"), dict), f"{expected_tool} data is missing")
    return result["data"]


def build_live_llm(interceptor: SingleRequestInterceptor, *, api_key: str) -> LLM:
    """Build the pinned native CrewAI OpenAI Responses client."""
    return LLM(
        model=f"openai/{MODEL_ID}",
        temperature=TEMPERATURE,
        max_retries=0,
        api="responses",
        response_format=ModelOutput,
        api_key=api_key,
        stream=False,
        store=False,
        auto_chain=False,
        auto_chain_reasoning=False,
        interceptor=interceptor,
    )


def build_flow(*, client: Any, correlation_id: str, run_id: str, runtime_db: Path,
               llm: Any, request_budget: SingleRequestBudget,
               interceptor: SingleRequestInterceptor | None = None) -> Flow[CanonicalSliceState]:
    """Construct the persisted canonical Flow with injected accepted boundaries."""
    require(runtime_db.parent.name == run_id, "Runtime DB must be scoped to the logical run")
    require("/shared/" not in runtime_db.resolve().as_posix(), "CrewAI runtime state may not use shared/")
    runtime_db.parent.mkdir(parents=True, exist_ok=False)
    backend = SQLiteFlowPersistence(str(runtime_db))
    memory_backend = RunScopedMemoryStorage()
    set_memory_storage_factory(lambda spec: memory_backend)
    tools = build_tools(client, correlation_id=correlation_id)

    @persist(backend)
    class CanonicalTargetFlow(Flow[CanonicalSliceState]):
        @start()
        def discover_target(self) -> dict[str, Any]:
            self._current_stage = "target_discovery"
            discovery = unwrap(tools["find_images_needing_review"].run(), "find_images_needing_review")
            targets = discovery.get("targets")
            require(isinstance(targets, list) and len(targets) == 12, "Discovery did not return 12 targets")
            require(canonical_sha256(targets) == TARGET_SEQUENCE_SHA256, "Frozen target sequence hash drifted")
            require(targets[0] == CANONICAL_TARGET, "Canonical target 1 identity drifted")
            self.state.canonical_target = targets[0]
            self.state.lifecycle_stage = "target_discovered"
            self.state.updated_at = utc_now()
            return targets[0]

        @listen(discover_target)
        def retrieve_context(self, target: dict[str, Any]) -> dict[str, Any]:
            self._current_stage = "context_retrieval"
            context = unwrap(tools["get_image_context"].run(target=target), "get_image_context")
            require(context.get("target") == target, "Context target differs from canonical target")
            self._ephemeral_context = context
            self.state.context_provenance = context_summary(context)
            self.state.lifecycle_stage = "context_retrieved"
            self.state.updated_at = utc_now()
            return target

        @listen(retrieve_context)
        def invoke_model(self, target: dict[str, Any]) -> dict[str, Any]:
            self._current_stage = "provider_request"
            context = self._ephemeral_context
            prompt = user_prompt(target, context)
            self.state.prompt_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": context["image"]["representation"]["value"], "detail": "auto"},
                ]},
            ]
            request_budget.claim()
            raw = llm.call(messages=messages)
            self._current_stage = "structured_parsing"
            parsed = raw if isinstance(raw, ModelOutput) else ModelOutput.model_validate_json(str(raw))
            output = parsed.model_dump()
            self.state.raw_model_output = output
            accounting = interceptor.snapshot() if interceptor is not None else {
                "actual_provider_requests": 0,
                "successful_provider_responses": 0,
                "rehearsal_fake": True,
            }
            accounting["logical_generations"] = request_budget.logical_generations
            self.state.request_accounting = accounting
            self.state.lifecycle_stage = "model_output_parsed"
            self.state.updated_at = utc_now()
            return output

        @listen(invoke_model)
        def assemble_recommendation(self, output: dict[str, Any]) -> dict[str, Any]:
            self._current_stage = "recommendation_assembly"
            recommendation = {
                "schema_version": 1,
                "target": self.state.canonical_target,
                "proposed_alt_text": output["proposed_alt_text"].strip(),
                "source_framework": "crewai",
                "run_id": self.state.run_id,
                "evidence_hash": self.state.context_provenance["evidence_hash"],
                "validator_version": VALIDATOR_VERSION,
            }
            self.state.assembled_recommendation = recommendation
            self.state.lifecycle_stage = "recommendation_assembled"
            self.state.updated_at = utc_now()
            return recommendation

        @listen(assemble_recommendation)
        def submit_and_observe(self, recommendation: dict[str, Any]) -> dict[str, Any]:
            self._current_stage = "deterministic_validation"
            target = self.state.canonical_target
            fresh = unwrap(tools["get_image_context"].run(target=target), "get_image_context")
            require(fresh.get("evidence_hash") == self.state.context_provenance["evidence_hash"],
                    "Context changed before submission")
            self._current_stage = "submission"
            submitted = unwrap(tools["submit_recommendation"].run(recommendation=recommendation),
                               "submit_recommendation")
            require(submitted.get("status") == "pending", "Submission did not create pending review state")
            observed = unwrap(tools["get_recommendation_status"].run(
                recommendation_id=submitted["uuid"]), "get_recommendation_status")
            require(observed.get("status") == "pending", "Read-only status is not pending")
            after = unwrap(tools["get_image_context"].run(target=target), "get_image_context")
            require(after.get("evidence_hash") == self.state.context_provenance["evidence_hash"],
                    "Source context changed after recommendation submission")
            self.state.deterministic_validation = {
                "status": "pass",
                "owner": "shared submit_recommendation boundary",
                "separate_adapter_validation": False,
            }
            self.state.recommendation_id = submitted["uuid"]
            self.state.recommendation_revision_id = submitted["revision_id"]
            self.state.review_status = "pending"
            self.state.status = "awaiting_human_review"
            self.state.lifecycle_stage = "awaiting_drupal_authoritative_review"
            self.state.persistence_provenance = {
                "mechanism": "SQLiteFlowPersistence",
                "runtime_db": f"crewai/.runtime/gate2b-step04/{run_id}/flow-state.sqlite",
                "shared_runtime_storage": False,
                "continuation_claimed": False,
            }
            self._current_stage = "state_persistence"
            self.state.updated_at = utc_now()
            return {"submission": submitted, "status": observed, "source_after": context_summary(after)}

    flow = CanonicalTargetFlow(suppress_flow_events=True, tracing=False)
    flow.state.id = run_id
    flow.state.run_id = run_id
    return flow


__all__ = [
    "CANONICAL_TARGET", "MODEL_ID", "PROMPT_VERSION", "SYSTEM_PROMPT", "TEMPERATURE",
    "CanonicalSliceState", "ModelOutput", "ProviderRequestBudgetExceeded",
    "SingleRequestBudget", "SingleRequestInterceptor", "build_flow", "build_live_llm",
    "canonical_sha256", "context_summary", "user_prompt",
]
