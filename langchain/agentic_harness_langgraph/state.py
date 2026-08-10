"""Frozen LangGraph run-state helpers for Gate 2A.

This module owns framework-local graph-channel state only. Optional checkpoint metadata from the frozen evidence schema is kept outside the StateGraph channel namespace. It performs no model calls,
Drupal calls, validation business logic, recommendation writes, or persistence
outside the LangGraph checkpoint runtime selected by ADR-0010.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, TypedDict

TARGET_SEQUENCE_HASH = "sha256:1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728"
PROMPT_VERSION = "langgraph-alt-text-v1.0.0"
MODEL_ID = "gpt-4.1-mini-2025-04-14"


class LangGraphRunState(TypedDict):
    schema_version: int
    run_id: str
    framework_origin: str
    thread_id: str
    checkpoint_backend: str
    status: str
    target_sequence_hash: str
    next_target_index: int
    completed_target_identities: list[dict[str, Any]]
    recommendation_ids: list[dict[str, Any]]
    validation_results: list[dict[str, Any]]
    started_at: str
    updated_at: str
    completed_at: str | None
    interrupted_at: str | None
    resumed_at: str | None
    continuation_boundary_armed: bool
    continuation_boundary_reached: bool
    gate2c_failure_injection_fired: bool
    prompt_version: str
    model_id: str


def initial_state(run_id: str, timestamp: str) -> LangGraphRunState:
    if not run_id:
        raise ValueError("run_id is required")
    return {
        "schema_version": 1,
        "run_id": run_id,
        "framework_origin": "langgraph",
        "thread_id": run_id,
        "checkpoint_backend": "sqlite",
        "status": "running",
        "target_sequence_hash": TARGET_SEQUENCE_HASH,
        "next_target_index": 0,
        "completed_target_identities": [],
        "recommendation_ids": [],
        "validation_results": [],
        "started_at": timestamp,
        "updated_at": timestamp,
        "completed_at": None,
        "interrupted_at": None,
        "resumed_at": None,
        "continuation_boundary_armed": False,
        "continuation_boundary_reached": False,
        "gate2c_failure_injection_fired": False,
        "prompt_version": PROMPT_VERSION,
        "model_id": MODEL_ID,
    }


def advance_target(
    state: LangGraphRunState,
    target: dict[str, Any],
    timestamp: str,
) -> LangGraphRunState:
    expected_sequence = int(state["next_target_index"]) + 1
    actual_sequence = int(target.get("sequence", -1))
    if actual_sequence != expected_sequence:
        raise ValueError(
            f"Deterministic target order violated: expected {expected_sequence}, got {actual_sequence}"
        )
    updated = deepcopy(dict(state))
    updated["completed_target_identities"] = [
        *deepcopy(state["completed_target_identities"]),
        deepcopy(target),
    ]
    updated["next_target_index"] = expected_sequence
    updated["updated_at"] = timestamp
    updated["status"] = "running"
    return updated  # type: ignore[return-value]
