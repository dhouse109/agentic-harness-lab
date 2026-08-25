"""Continuation-only CrewAI Flow for the Drupal-authoritative review boundary.

This module deliberately has no discovery, context, model, assembly, validation,
or submission methods.  It binds an already accepted Step 2B.04 state to
CrewAI's public async-human-feedback lifecycle and observes Drupal read-only.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from pydantic import Field

from crewai.flow import Flow, human_feedback, listen, start
from crewai.flow.async_feedback import HumanFeedbackPending, PendingFeedbackContext
from crewai.flow.persistence import SQLiteFlowPersistence, persist
from crewai.memory.storage.factory import set_memory_storage_factory

from .canonical_slice import CanonicalSliceState, RunScopedMemoryStorage


SOURCE_RUN_ID = "crewai-20260818T215017Z-8e03fc95"
RECOMMENDATION_UUID = "1878ae86-834c-4813-9134-4c3b8d0833c9"
RECOMMENDATION_NODE_ID = 21
SOURCE_RECOMMENDATION_REVISION = 21
SOURCE_CANONICAL_MANIFEST_SHA256 = "c6115ffea4b7ceefb7858e6b482713fc92998dcf2bde7bc6de8831d583665aaf"
SOURCE_CANONICAL_SUMMARY_SHA256 = "5cd324d26b866c83d9728e7634887bcf3ccc46c2df5f4fc6a9563069f71ef490"
SOURCE_CLOSURE_MANIFEST_SHA256 = "d62ababa96b223643ab23e3d67c75b3fcc2bb325a8a3e69787fff870cc56583b"
SOURCE_CLOSURE_SUMMARY_SHA256 = "e482aa166485ea97c0698b82dade0cfdadbe9947fb06aa2ce0d59c9a3cc87f01"
SOURCE_PROJECTION_SHA256 = "f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17"


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


class ContinuationState(CanonicalSliceState):
    """Accepted source state plus continuation-only accounting."""

    source_run_id: str = SOURCE_RUN_ID
    continuation_id: str = "unset"
    pending_context_sha256: str | None = None
    resume_payload_sha256: str | None = None
    review_observation: dict[str, Any] | None = None
    replay_attempts: dict[str, int] = Field(default_factory=lambda: {
        "find_images_needing_review": 0,
        "get_image_context": 0,
        "model_generation": 0,
        "recommendation_assembly": 0,
        "deterministic_validation": 0,
        "submit_recommendation": 0,
        "get_recommendation_status": 0,
    })
    additional_activity: dict[str, int] = Field(default_factory=lambda: {
        "logical_generations": 0,
        "provider_requests": 0,
        "provider_responses": 0,
        "provider_retries": 0,
        "structured_repair_calls": 0,
        "fallback_calls": 0,
        "feedback_collapse_calls": 0,
        "learning_calls": 0,
        "recommendation_submissions": 0,
        "source_mutations": 0,
    })


class DrupalAuthorityPendingProvider:
    """Public async provider: persist a pending boundary without acting in Drupal."""

    def request_feedback(self, context: PendingFeedbackContext, flow: Flow[Any]) -> str:
        del flow
        require(context.flow_id == SOURCE_RUN_ID, "Pending context Flow identity drifted")
        require(context.emit is None and context.llm is None, "Model-backed outcome routing is prohibited")
        require(context.metadata.get("recommendation_uuid") == RECOMMENDATION_UUID,
                "Pending recommendation identity drifted")
        raise HumanFeedbackPending(
            context=context,
            callback_info={"authority": "Drupal", "reviewer": "editor_dana"},
        )


StatusReader = Callable[[], dict[str, Any]]


def normalize_observation(value: dict[str, Any]) -> dict[str, Any]:
    """Return only governed, nonsecret Drupal review fields."""
    return {
        "uuid": value.get("uuid"),
        "node_id": value.get("node_id", RECOMMENDATION_NODE_ID),
        "revision_id": value.get("revision_id"),
        "status": value.get("status"),
        "reviewer_username": value.get("reviewer_username"),
        "reviewed_at": value.get("reviewed_at"),
    }


def validate_pending_observation(value: dict[str, Any]) -> dict[str, Any]:
    observed = normalize_observation(value)
    require(observed == {
        "uuid": RECOMMENDATION_UUID,
        "node_id": RECOMMENDATION_NODE_ID,
        "revision_id": SOURCE_RECOMMENDATION_REVISION,
        "status": "pending",
        "reviewer_username": None,
        "reviewed_at": None,
    }, "Drupal pre-review state differs from the frozen pending recommendation")
    return observed


def validate_reviewed_observation(value: dict[str, Any]) -> dict[str, Any]:
    observed = normalize_observation(value)
    require(observed["uuid"] == RECOMMENDATION_UUID, "Reviewed recommendation UUID drifted")
    require(observed["node_id"] == RECOMMENDATION_NODE_ID, "Reviewed recommendation node drifted")
    require(observed["revision_id"] == 22,
            "Drupal review revision is not the frozen expected revision 22")
    require(observed["status"] == "approved", "Drupal authoritative status is not approved")
    require(observed["reviewer_username"] == "editor_dana", "Drupal reviewer is not editor_dana")
    require(isinstance(observed["reviewed_at"], str) and observed["reviewed_at"],
            "Drupal review timestamp is missing")
    return observed


def resume_signal(observation: dict[str, Any]) -> str:
    """Deterministic transport signal; it is never an approval authority."""
    observed = validate_reviewed_observation(observation)
    return json.dumps({
        "authority": "Drupal",
        "signal": "authoritative-review-ready",
        "recommendation_uuid": RECOMMENDATION_UUID,
        "revision_id": observed["revision_id"],
        "status": observed["status"],
        "reviewer_username": observed["reviewer_username"],
        "reviewed_at": observed["reviewed_at"],
    }, sort_keys=True, separators=(",", ":"))


def parse_resume_signal(value: str) -> dict[str, Any]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Resume signal is not canonical JSON") from exc
    require(isinstance(payload, dict), "Resume signal must be an object")
    require(payload.get("authority") == "Drupal"
            and payload.get("signal") == "authoritative-review-ready",
            "Resume signal does not identify the Drupal observation boundary")
    return payload


def build_continuation_flow(
    *,
    persistence: SQLiteFlowPersistence,
    status_reader: StatusReader,
    continuation_id: str,
) -> type[Flow[ContinuationState]]:
    """Build a continuation-only class over the accepted public APIs."""
    memory_backend = RunScopedMemoryStorage()
    set_memory_storage_factory(lambda spec: memory_backend)
    provider = DrupalAuthorityPendingProvider()

    @persist(persistence)
    class DrupalReviewContinuationFlow(Flow[ContinuationState]):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self._status_reader = status_reader

        @start()
        @human_feedback(
            message="Wait for editor_dana to review the existing recommendation in Drupal.",
            emit=None,
            llm=None,
            provider=provider,
            learn=False,
            metadata={
                "authority": "Drupal",
                "reviewer": "editor_dana",
                "recommendation_uuid": RECOMMENDATION_UUID,
                "source_run_id": SOURCE_RUN_ID,
            },
        )
        def await_drupal_authoritative_review(self) -> dict[str, Any]:
            require(self.state.id == SOURCE_RUN_ID and self.state.run_id == SOURCE_RUN_ID,
                    "Source CrewAI Flow state identity drifted")
            require(self.state.source_run_id == SOURCE_RUN_ID, "Source run binding drifted")
            require(self.state.recommendation_id == RECOMMENDATION_UUID,
                    "Source recommendation binding drifted")
            require(self.state.status == "awaiting_human_review"
                    and self.state.lifecycle_stage == "awaiting_drupal_authoritative_review",
                    "Step 2B.04 source state is not at the accepted terminal boundary")
            observed = validate_pending_observation(self._status_reader())
            self.state.replay_attempts["get_recommendation_status"] += 1
            self.state.continuation_id = continuation_id
            self.state.continuation_status = "pending_external_drupal_review"
            self.state.review_observation = observed
            return {
                "source_run_id": SOURCE_RUN_ID,
                "flow_state_id": self.state.id,
                "recommendation_uuid": RECOMMENDATION_UUID,
                "continuation_id": continuation_id,
            }

        @listen(await_drupal_authoritative_review)
        def observe_authoritative_review(self, feedback_result: Any) -> dict[str, Any]:
            payload = parse_resume_signal(feedback_result.feedback)
            observed = validate_reviewed_observation(self._status_reader())
            self.state.replay_attempts["get_recommendation_status"] += 1
            expected = {
                "recommendation_uuid": observed["uuid"],
                "revision_id": observed["revision_id"],
                "status": observed["status"],
                "reviewer_username": observed["reviewer_username"],
                "reviewed_at": observed["reviewed_at"],
            }
            for key, expected_value in expected.items():
                require(payload.get(key) == expected_value,
                        f"Resume signal contradicts authoritative Drupal field: {key}")
            self.state.resume_payload_sha256 = hashlib.sha256(
                feedback_result.feedback.encode("utf-8")
            ).hexdigest()
            self.state.review_observation = observed
            self.state.review_status = observed["status"]
            self.state.status = "completed"
            self.state.lifecycle_stage = "drupal_authoritative_review_observed"
            self.state.continuation_status = "completed"
            return {
                "status": "completed",
                "flow_state_id": self.state.id,
                "recommendation_uuid": observed["uuid"],
                "review_revision_id": observed["revision_id"],
            }

    return DrupalReviewContinuationFlow


def load_source_state(persistence: SQLiteFlowPersistence) -> dict[str, Any]:
    state = persistence.load_state(SOURCE_RUN_ID)
    require(isinstance(state, dict), "Copied Step 2B.04 state is missing")
    state = dict(state)
    state.update({"source_run_id": SOURCE_RUN_ID})
    return state


def pending_identity(context: PendingFeedbackContext) -> str:
    return canonical_sha256(context.to_dict())


def persistence_for(runtime_db: Path) -> SQLiteFlowPersistence:
    resolved = runtime_db.resolve()
    require("/shared/" not in resolved.as_posix(), "CrewAI runtime may not use shared/")
    return SQLiteFlowPersistence(str(resolved))


__all__ = [
    "ContinuationState", "DrupalAuthorityPendingProvider", "RECOMMENDATION_NODE_ID",
    "RECOMMENDATION_UUID", "SOURCE_RUN_ID", "build_continuation_flow",
    "load_source_state", "pending_identity", "persistence_for", "resume_signal",
    "validate_pending_observation", "validate_reviewed_observation",
]
