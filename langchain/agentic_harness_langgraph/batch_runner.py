"""Gate 2A LangGraph 12-target batch runner and Step 2A.07 construction test.

Step 2A.07 executes only ``construction_test``. The live ``start`` and ``resume``
entrypoints are installed for Step 2A.08, whose wrapper owns model-call authorization,
Drupal snapshot/restore, retained failure handling, and promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from agentic_harness_langgraph.state import LangGraphRunState, advance_target, initial_state

TARGET_COUNT = 12
BOUNDARY_AFTER_SEQUENCE = 6
RESUME_AT_SEQUENCE = 7
TARGET_HASH = "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728"
MODEL_ID = "gpt-4.1-mini-2025-04-14"
TEMPERATURE = 0.0
PROMPT_VERSION = "langgraph-alt-text-v1.0.0"
VALIDATOR_VERSION = "gate05-validator-1.0.0"
ACCEPTED_TARGETS_REL = (
    "evidence/gates/gate-2a/tool-adapters/"
    "gate2a-step03-20260809T233127Z-2375581/targets.json"
)
SCHEMA_MAP_REL = "shared/contracts/GATE2A-LANGGRAPH-EVIDENCE-SCHEMA-MAP.json"
RUN_ID_RE = re.compile(r"^langgraph-[0-9]{8}T[0-9]{6}Z-[a-z0-9]{4,12}$")


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError(message)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def append_event(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")


def read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        require(bool(line.strip()), f"Blank event line at {number}")
        value = json.loads(line)
        require(isinstance(value, dict), f"Event line {number} is not an object")
        events.append(value)
    return events


def emit_event(
    path: Path,
    *,
    event_type: str,
    run_id: str,
    source_framework: str = "langgraph",
    sequence: int | None = None,
    correlation_id: str,
    target: dict[str, Any] | None = None,
    outcome: str = "persisted",
    error_code: str | None = None,
) -> dict[str, Any]:
    events = read_events(path)
    event = {
        "schema_version": 1,
        "event_index": len(events) + 1,
        "event_type": event_type,
        "run_id": run_id,
        "source_framework": source_framework,
        "occurred_at": now(),
        "sequence": sequence,
        "correlation_id": correlation_id,
        "target": target,
        "outcome": outcome,
        "error_code": error_code,
    }
    append_event(path, event)
    return event


def load_targets(repo: Path) -> list[dict[str, Any]]:
    targets = json.loads((repo / ACCEPTED_TARGETS_REL).read_text(encoding="utf-8"))
    require(isinstance(targets, list) and len(targets) == TARGET_COUNT, "Accepted target list is not 12 items")
    require(hashlib.sha256(canonical(targets)).hexdigest() == TARGET_HASH, "Accepted target hash differs from frozen contract")
    require([int(x.get("sequence", -1)) for x in targets] == list(range(1, 13)), "Target sequence is not 1..12")
    return targets


def task_interrupt_count(snapshot: Any) -> int:
    total = 0
    for task in getattr(snapshot, "tasks", ()) or ():
        total += len(getattr(task, "interrupts", ()) or ())
    return total


def validate_json(repo: Path, schema_name: str, value: Any, label: str) -> None:
    schema_python = repo / "crewai/.venv/bin/python"
    helper = repo / "scripts/gate2a_step07_schema_validate.py"
    require(schema_python.is_file(), "Repository schema-validation Python is missing")
    require(helper.is_file(), "Step 2A.07 schema-validation helper is missing")
    proc = subprocess.run(
        [str(schema_python), str(helper), "--repo", str(repo), "--schema", schema_name, "--label", label],
        input=json.dumps(value, ensure_ascii=False),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    require(proc.returncode == 0, proc.stdout.strip() or f"{label} failed {schema_name}")


def validate_events(repo: Path, path: Path, label: str) -> None:
    events = read_events(path)
    require(events, f"{label} has no events")
    for expected_index, event in enumerate(events, 1):
        require(event.get("event_index") == expected_index, f"{label} event_index is not contiguous at {expected_index}")
        validate_json(repo, "langgraph-batch-event.schema.json", event, f"{label} event {expected_index}")

def checkpoint_privacy(
    sqlite_path: Path,
    state: dict[str, Any],
    evidence: Path,
    probes: dict[str, str],
) -> dict[str, Any]:
    db_bytes = sqlite_path.read_bytes()
    state_bytes = canonical(state)
    evidence_bytes = b""
    privacy_report_names = {
        "checkpoint-privacy-before-continuation.json",
        "checkpoint-privacy-after-continuation.json",
    }
    for path in evidence.iterdir():
        if path.is_file() and path != sqlite_path and path.name not in privacy_report_names:
            evidence_bytes += path.read_bytes()
    haystacks = (db_bytes, state_bytes, evidence_bytes)
    generic_patterns = [
        b"data:image/", b"Authorization:", b"Bearer ", b"Basic ",
        b"OPENAI_API_KEY", b"GATE2A_DRUPAL_PASSWORD",
        b"hidden_reasoning", b"chain_of_thought",
    ]
    generic_hits = [
        pattern.decode("ascii", errors="replace")
        for pattern in generic_patterns
        if any(pattern in data for data in haystacks)
    ]
    exact_hits: list[str] = []
    for label, value in probes.items():
        if not value:
            continue
        encoded = value.encode("utf-8")
        if any(encoded in data for data in haystacks):
            exact_hits.append(label)
    result = {
        "schema_version": 1,
        "status": "pass" if not generic_hits and not exact_hits else "fail",
        "generic_prohibited_pattern_hits": generic_hits,
        "exact_ephemeral_value_hits": exact_hits,
        "raw_image_or_data_url_persisted": any(label.startswith("image_representation_") for label in exact_hits) or "data:image/" in generic_hits,
        "article_body_persisted": any(label.startswith("article_body_") for label in exact_hits),
        "credential_persisted": any(label in {"drupal_password", "openai_api_key"} for label in exact_hits),
        "hidden_reasoning_persisted": "hidden_reasoning" in generic_hits or "chain_of_thought" in generic_hits,
    }
    return result


def mark_boundary(state: LangGraphRunState, timestamp: str) -> LangGraphRunState:
    require(int(state["next_target_index"]) == BOUNDARY_AFTER_SEQUENCE, "Boundary reached before sequence 6 persisted")
    updated = deepcopy(dict(state))
    updated["continuation_boundary_armed"] = True
    updated["continuation_boundary_reached"] = True
    updated["status"] = "interrupted"
    updated["interrupted_at"] = timestamp
    updated["updated_at"] = timestamp
    return updated  # type: ignore[return-value]


def resume_boundary(state: LangGraphRunState, timestamp: str) -> LangGraphRunState:
    require(int(state["next_target_index"]) == BOUNDARY_AFTER_SEQUENCE, "Resume does not begin after sequence 6")
    updated = deepcopy(dict(state))
    updated["status"] = "running"
    updated["resumed_at"] = timestamp
    updated["updated_at"] = timestamp
    return updated  # type: ignore[return-value]


def complete_state(state: LangGraphRunState, timestamp: str) -> LangGraphRunState:
    require(int(state["next_target_index"]) == TARGET_COUNT, "Completion attempted before target 12")
    updated = deepcopy(dict(state))
    updated["status"] = "completed"
    updated["completed_at"] = timestamp
    updated["updated_at"] = timestamp
    return updated  # type: ignore[return-value]


def build_graph(process_target: Callable[[int, LangGraphRunState], LangGraphRunState], checkpointer: Any) -> Any:
    builder = StateGraph(LangGraphRunState)

    for sequence in range(1, TARGET_COUNT + 1):
        def node(state: LangGraphRunState, seq: int = sequence) -> LangGraphRunState:
            return process_target(seq, state)
        builder.add_node(f"target_{sequence:02d}", node)

    def continuation_boundary(state: LangGraphRunState) -> LangGraphRunState:
        require(int(state["next_target_index"]) == BOUNDARY_AFTER_SEQUENCE, "Continuation node entered at wrong index")
        signal = interrupt({
            "kind": "controlled_same_run_continuation",
            "failure_injection": False,
            "completed_through_sequence": 6,
            "resume_at_sequence": 7,
            "run_id": state["run_id"],
            "thread_id": state["thread_id"],
        })
        require(isinstance(signal, dict) and signal.get("continue_after_sequence") == 6, "Continuation resume signal is invalid")
        return resume_boundary(state, now())

    builder.add_node("continuation_boundary", continuation_boundary)
    builder.add_edge(START, "target_01")
    for sequence in range(1, 6):
        builder.add_edge(f"target_{sequence:02d}", f"target_{sequence + 1:02d}")
    builder.add_edge("target_06", "continuation_boundary")
    builder.add_edge("continuation_boundary", "target_07")
    for sequence in range(7, 12):
        builder.add_edge(f"target_{sequence:02d}", f"target_{sequence + 1:02d}")
    builder.add_edge("target_12", END)
    return builder.compile(checkpointer=checkpointer)


def construction_test(repo: Path, evidence: Path, run_id: str) -> dict[str, Any]:
    """Model-free real LangGraph/SQLite construction proof over frozen target identities."""
    require(RUN_ID_RE.fullmatch(run_id) is not None, "Construction-test run_id is not frozen langgraph form")
    require(not os.environ.get("OPENAI_API_KEY"), "Step 2A.07 construction test requires OPENAI_API_KEY unset")
    evidence.mkdir(parents=True, exist_ok=False)
    targets = load_targets(repo)
    write_json(evidence / "targets.json", {
        "schema_version": 1,
        "target_sequence_sha256": TARGET_HASH,
        "targets": targets,
    })

    model_calls = 0
    drupal_calls = 0
    processed: list[int] = []

    def process(sequence: int, state: LangGraphRunState) -> LangGraphRunState:
        nonlocal model_calls, drupal_calls
        require(sequence == int(state["next_target_index"]) + 1, "Construction graph would reprocess or skip a target")
        require(sequence not in processed, "Construction graph duplicate sequence")
        processed.append(sequence)
        updated = advance_target(state, targets[sequence - 1], now())
        validation = {
            "sequence": sequence,
            "target": targets[sequence - 1],
            "structured_output_schema_valid": True,
            "deterministic_validation_passed": True,
            "errors": [],
        }
        updated["validation_results"] = [*state["validation_results"], validation]
        updated["recommendation_ids"] = [
            *state["recommendation_ids"],
            {
                "sequence": sequence,
                "node_id": 1000 + sequence,
                "uuid": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{run_id}:{sequence}")),
                "revision_id": 2000 + sequence,
            },
        ]
        if sequence == BOUNDARY_AFTER_SEQUENCE:
            updated = mark_boundary(updated, now())
        if sequence == TARGET_COUNT:
            updated = complete_state(updated, now())
        return updated

    runtime_root = repo / "langchain/.gate2a-runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=f"{run_id}-step07-", suffix=".sqlite", dir=runtime_root, delete=False) as tmp:
        sqlite_path = Path(tmp.name)
    sqlite_path.unlink(missing_ok=True)
    config = {"configurable": {"thread_id": run_id}}
    try:
        with SqliteSaver.from_conn_string(str(sqlite_path)) as saver:
            graph = build_graph(process, saver)
            graph.invoke(initial_state(run_id, now()), config)
            before = graph.get_state(config)
            before_state = dict(before.values)
            require(task_interrupt_count(before) > 0, "Construction graph did not persist a genuine interrupt")
            require(before_state["status"] == "interrupted", "Construction midpoint status is not interrupted")
            require(before_state["next_target_index"] == 6, "Construction midpoint index is not 6")
            require([x["sequence"] for x in before_state["completed_target_identities"]] == [1, 2, 3, 4, 5, 6], "Midpoint completed sequence differs")
            require(before_state["continuation_boundary_reached"] is True, "Continuation boundary was not marked reached")
            require(before_state["gate2c_failure_injection_fired"] is False, "Gate 2C failure injection fired during construction")
            validate_json(repo, "langgraph-run-state.schema.json", before_state, "construction midpoint state")
            write_json(evidence / "checkpoint-before-continuation.json", before_state)
            write_json(evidence / "interrupt-event.json", {
                "schema_version": 1,
                "event": "construction-test-langgraph-interrupt",
                "run_id": run_id,
                "thread_id": run_id,
                "interrupt_count": task_interrupt_count(before),
                "completed_before_stop": [1, 2, 3, 4, 5, 6],
                "resume_at_sequence": 7,
                "gate2c_failure_injection": False,
            })

            result = graph.invoke(Command(resume={"continue_after_sequence": 6}), config)
            after = graph.get_state(config)
            after_state = dict(after.values)
            require(task_interrupt_count(after) == 0, "Construction interrupt remains after resume")
            require(after_state == result, "Construction final checkpoint differs from graph result")
            require(after_state["status"] == "completed", "Construction final status is not completed")
            require(after_state["next_target_index"] == 12, "Construction final index is not 12")
            require([x["sequence"] for x in after_state["completed_target_identities"]] == list(range(1, 13)), "Construction completed sequence differs")
            require(processed == list(range(1, 13)), "Construction processed order differs or contains duplicate")
            require(after_state["run_id"] == run_id and after_state["thread_id"] == run_id, "Run/thread identity changed")
            require(after_state["resumed_at"] is not None, "Construction resumed_at is missing")
            require(after_state["gate2c_failure_injection_fired"] is False, "Gate 2C failure injection fired")
            validate_json(repo, "langgraph-run-state.schema.json", after_state, "construction completed state")
            write_json(evidence / "checkpoint-after-continuation.json", after_state)

        db_sha = hashlib.sha256(sqlite_path.read_bytes()).hexdigest()
    finally:
        sqlite_path.unlink(missing_ok=True)

    # Prove that the derived full-batch collection schemas accept truthful LangGraph provenance.
    timestamp = now()
    outputs = []
    recs = []
    validations = []
    submissions = []
    observations = []
    traces = []
    for sequence, target in enumerate(targets, 1):
        proposed = f"Construction-test alt text for frozen target {sequence}."
        model_output = {"proposed_alt_text": proposed}
        rec_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{run_id}:{sequence}"))
        evidence_hash = "sha256:" + hashlib.sha256(f"construction:{sequence}".encode()).hexdigest()
        recommendation = {
            "schema_version": 1,
            "target": target,
            "proposed_alt_text": proposed,
            "source_framework": "langgraph",
            "run_id": run_id,
            "evidence_hash": evidence_hash,
            "validator_version": VALIDATOR_VERSION,
        }
        validation = {
            "sequence": sequence,
            "target": target,
            "structured_output_schema_valid": True,
            "deterministic_validation_passed": True,
            "errors": [],
        }
        outputs.append({"sequence": sequence, "target": target, "model_output": model_output})
        recs.append({"sequence": sequence, "target": target, "recommendation": recommendation})
        validations.append(validation)
        submissions.append({
            "sequence": sequence,
            "target": target,
            "node_id": 1000 + sequence,
            "uuid": rec_uuid,
            "revision_id": 2000 + sequence,
            "initial_status": "pending",
            "idempotent_replay_same_identity": False,
        })
        observations.append({
            "recommendation_uuid": rec_uuid,
            "revision_id": 2000 + sequence,
            "status": "pending",
            "observed_at": timestamp,
        })
        traces.append({
            "operation": "get_image_context",
            "correlation_id": f"{run_id}-construction-{sequence}",
            "started_at": timestamp,
            "completed_at": timestamp,
            "ok": True,
            "sequence": sequence,
            "target": target,
            "result_sha256": evidence_hash,
            "recommendation_uuid": None,
            "error": None,
        })

    collections = {
        "targets": ("langgraph-batch-target-sequence.schema.json", {
            "schema_version": 1, "target_sequence_sha256": TARGET_HASH, "targets": targets,
        }),
        "model_outputs": ("langgraph-batch-model-outputs.schema.json", {
            "schema_version": 1, "run_id": run_id, "framework_origin": "langgraph", "outputs": outputs,
        }),
        "recommendations": ("langgraph-batch-recommendations.schema.json", {
            "schema_version": 1, "run_id": run_id, "source_framework": "langgraph", "recommendations": recs,
        }),
        "validation": ("langgraph-batch-validation.schema.json", {
            "schema_version": 1, "run_id": run_id, "source_framework": "langgraph", "validator_version": VALIDATOR_VERSION, "results": validations,
        }),
        "submissions": ("langgraph-batch-submissions.schema.json", {
            "schema_version": 1, "run_id": run_id, "framework_origin": "langgraph", "submissions": submissions,
        }),
        "statuses": ("langgraph-batch-statuses.schema.json", {
            "schema_version": 1, "run_id": run_id, "framework_origin": "langgraph", "observations": observations,
        }),
        "tool_traces": ("langgraph-batch-tool-traces.schema.json", {
            "schema_version": 1, "run_id": run_id, "source_framework": "langgraph", "traces": traces,
        }),
        "recovery": ("langgraph-batch-recovery.schema.json", {
            "schema_version": 1,
            "run_id": run_id,
            "source_framework": "langgraph",
            "controlled_stop_after_sequence": 6,
            "resume_at_sequence": 7,
            "completed_before_stop": [1, 2, 3, 4, 5, 6],
            "interrupted_at": before_state["interrupted_at"],
            "resumed_at": after_state["resumed_at"],
            "resumed_with_run_id": run_id,
            "duplicate_count": 0,
            "completed_after_resume": [7, 8, 9, 10, 11, 12],
            "gate2c_failure_injection_fired": False,
        }),
        "summary": ("langgraph-batch-summary.schema.json", {
            "schema_version": 1,
            "status": "pass",
            "run_id": run_id,
            "source_framework": "langgraph",
            "provider": "OpenAI",
            "model": MODEL_ID,
            "temperature": 0.0,
            "target_count": 12,
            "completed_count": 12,
            "failed_count": 0,
            "duplicate_count": 0,
            "validator_version": VALIDATOR_VERSION,
            "review_destination": "alt_text_suggestion",
            "source_article_unchanged": True,
            "automatic_publication_performed": False,
            "failure_seam_observed": False,
            "resume_sequence": 7,
            "started_at": before_state["started_at"],
            "completed_at": after_state["completed_at"],
            "human_review_completed": False,
        }),
    }
    construction_events = [
        {
            "schema_version": 1, "event_index": 1, "event_type": "run_initialized",
            "run_id": run_id, "source_framework": "langgraph", "occurred_at": timestamp,
            "sequence": None, "correlation_id": f"{run_id}-construction", "target": None,
            "outcome": "started", "error_code": None,
        },
        {
            "schema_version": 1, "event_index": 2, "event_type": "continuation_interrupted",
            "run_id": run_id, "source_framework": "langgraph", "occurred_at": timestamp,
            "sequence": 6, "correlation_id": f"{run_id}-construction", "target": targets[5],
            "outcome": "interrupted", "error_code": None,
        },
        {
            "schema_version": 1, "event_index": 3, "event_type": "run_resumed",
            "run_id": run_id, "source_framework": "langgraph", "occurred_at": timestamp,
            "sequence": 7, "correlation_id": f"{run_id}-construction", "target": targets[6],
            "outcome": "resumed", "error_code": None,
        },
        {
            "schema_version": 1, "event_index": 4, "event_type": "run_completed",
            "run_id": run_id, "source_framework": "langgraph", "occurred_at": timestamp,
            "sequence": 12, "correlation_id": f"{run_id}-construction", "target": targets[11],
            "outcome": "completed", "error_code": None,
        },
    ]
    for item in construction_events:
        validate_json(repo, "langgraph-batch-event.schema.json", item, "construction event")

    schema_results: dict[str, str] = {"langgraph-batch-event.schema.json": "pass"}
    for label, (schema_name, value) in collections.items():
        validate_json(repo, schema_name, value, f"construction {label}")
        schema_results[schema_name] = "pass"

    summary = {
        "schema_version": 1,
        "status": "pass",
        "proof_scope": "step2a07-model-free-batch-runner-construction",
        "synthetic_graph_run_id": run_id,
        "thread_id": run_id,
        "target_count": 12,
        "target_sequence_sha256": TARGET_HASH,
        "completed_before_continuation": [1, 2, 3, 4, 5, 6],
        "resumed_at_sequence": 7,
        "completed_after_resume": [7, 8, 9, 10, 11, 12],
        "completed_sequences": list(range(1, 13)),
        "duplicate_count": 0,
        "same_run_thread_resumed": True,
        "genuine_langgraph_interrupt_persisted": True,
        "checkpoint_backend": "sqlite",
        "checkpoint_schema_validation_pass": True,
        "derived_collection_schema_validation": schema_results,
        "runtime_db_sha256_before_disposal": db_sha,
        "runtime_db_retained": False,
        "model_call_count": model_calls,
        "drupal_semantic_call_count": drupal_calls,
        "recommendation_write_count": 0,
        "source_article_mutation_performed": False,
        "automatic_publication_performed": False,
        "human_review_performed": False,
        "gate2c_failure_injection_exercised": False,
        "live_step2a08_batch_executed": False,
    }
    write_json(evidence / "summary.json", summary)
    (evidence / "summary.md").write_text(
        "# Gate 2A Step 2A.07 construction proof\n\n"
        "- status: pass\n"
        "- model calls: 0\n"
        "- Drupal semantic calls: 0\n"
        "- genuine LangGraph continuation interrupt: yes\n"
        "- same run/thread resumed at sequence 7: yes\n"
        "- completed sequences: 1–12 exactly once\n"
        "- Gate 2C failure injection: not exercised\n"
        "- live Step 2A.08 batch: not executed\n",
        encoding="utf-8",
    )
    manifest_files = sorted(p for p in evidence.iterdir() if p.is_file() and p.name != "package-files-sha256.txt")
    (evidence / "package-files-sha256.txt").write_text(
        "".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in manifest_files),
        encoding="utf-8",
    )
    return summary


def _load_collection(path: Path, key: str, envelope: dict[str, Any]) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    value = json.loads(path.read_text(encoding="utf-8"))
    for name, expected in envelope.items():
        require(value.get(name) == expected, f"Existing {path.name} {name} differs")
    items = value.get(key)
    require(isinstance(items, list), f"Existing {path.name} {key} is not a list")
    return items


def validate_resume_boundary(
    repo: Path,
    evidence: Path,
    run_id: str,
    targets: list[dict[str, Any]],
    counters: dict[str, Any],
    before_state: dict[str, Any],
    interrupt_count: int,
) -> None:
    """Fail closed before Step 2A.08 spends calls 7-12."""
    require(interrupt_count > 0, "Stored continuation checkpoint is not genuinely interrupted")
    require(before_state.get("run_id") == run_id and before_state.get("thread_id") == run_id, "Stored run/thread identity differs before resume")
    require(before_state.get("status") == "interrupted" and before_state.get("next_target_index") == 6, "Stored midpoint lifecycle differs")
    require(before_state.get("continuation_boundary_armed") is True and before_state.get("continuation_boundary_reached") is True, "Stored continuation boundary flags differ")
    require(before_state.get("gate2c_failure_injection_fired") is False, "Gate 2C failure flag is set before continuation")
    require([x.get("sequence") for x in before_state.get("completed_target_identities", [])] == [1, 2, 3, 4, 5, 6], "Stored completed targets before resume differ")
    require(len(before_state.get("recommendation_ids", [])) == 6, "Stored recommendation identity count before resume differs")
    require(len(before_state.get("validation_results", [])) == 6, "Stored validation count before resume differs")
    validate_json(repo, "langgraph-run-state.schema.json", before_state, "pre-resume checkpoint")

    run_state = json.loads((evidence / "run.json").read_text(encoding="utf-8"))
    checkpoint_state = json.loads((evidence / "checkpoint-before-continuation.json").read_text(encoding="utf-8"))
    require(run_state == before_state, "run.json differs from stored midpoint checkpoint")
    require(checkpoint_state == before_state, "checkpoint-before-continuation.json differs from stored midpoint checkpoint")
    validate_json(repo, "langgraph-run-state.schema.json", run_state, "pre-resume run.json")

    expected_counters = {
        "model_invocations_attempted": 6,
        "model_invocations_succeeded": 6,
        "automatic_model_retries_configured": 0,
        "semantic_retry_loop_performed": False,
        "find_images_needing_review": 1,
        "get_image_context": 18,
        "submit_recommendation": 6,
        "get_recommendation_status": 6,
    }
    require(counters == expected_counters, f"midpoint call counters differ: {counters!r}")

    targets_value = json.loads((evidence / "targets.json").read_text(encoding="utf-8"))
    validate_json(repo, "langgraph-batch-target-sequence.schema.json", targets_value, "pre-resume targets")
    require(targets_value.get("targets") == targets, "Pre-resume target evidence differs from frozen targets")

    def load_items(filename: str, key: str) -> list[dict[str, Any]]:
        value = json.loads((evidence / filename).read_text(encoding="utf-8"))
        items = value.get(key)
        require(isinstance(items, list) and len(items) == 6, f"Pre-resume {filename} does not contain exactly six items")
        return items

    outputs = load_items("model-outputs.json", "outputs")
    recommendations = load_items("recommendations.json", "recommendations")
    validations = load_items("validation.json", "results")
    submissions = load_items("submissions.json", "submissions")
    statuses = load_items("statuses.json", "observations")
    expected_sequences = [1, 2, 3, 4, 5, 6]
    for label, items in (("model outputs", outputs), ("recommendations", recommendations), ("validations", validations), ("submissions", submissions)):
        require([item.get("sequence") for item in items] == expected_sequences, f"Pre-resume {label} sequence differs")
    for index, target in enumerate(targets[:6]):
        require(outputs[index].get("target") == target, f"Pre-resume model-output target differs at sequence {index + 1}")
        require(recommendations[index].get("target") == target, f"Pre-resume recommendation target differs at sequence {index + 1}")
        require(validations[index].get("target") == target and validations[index].get("deterministic_validation_passed") is True, f"Pre-resume validation differs at sequence {index + 1}")
        require(submissions[index].get("target") == target and submissions[index].get("initial_status") == "pending", f"Pre-resume submission differs at sequence {index + 1}")
        recommendation = recommendations[index].get("recommendation", {})
        require(recommendation.get("run_id") == run_id and recommendation.get("source_framework") == "langgraph", f"Pre-resume recommendation provenance differs at sequence {index + 1}")

    submission_uuids = [item.get("uuid") for item in submissions]
    state_uuids = [item.get("uuid") for item in before_state.get("recommendation_ids", [])]
    status_uuids = [item.get("recommendation_uuid") for item in statuses]
    require(len(set(submission_uuids)) == 6, "Pre-resume submission UUIDs contain duplicates")
    require(submission_uuids == state_uuids == status_uuids, "Pre-resume submission/status/checkpoint identities differ")
    require(all(item.get("status") == "pending" for item in statuses), "Pre-resume status evidence is not all pending")

    privacy = json.loads((evidence / "checkpoint-privacy-before-continuation.json").read_text(encoding="utf-8"))
    require(privacy.get("status") == "pass", "Midpoint privacy proof is not pass")
    validate_events(repo, evidence / "events.jsonl", "pre-resume events")


def live_run(repo: Path, evidence: Path, run_id: str, mode: str) -> dict[str, Any]:
    """Step 2A.08 live path. Never called by the Step 2A.07 shell entrypoint."""
    require(mode in {"start", "resume"}, "Live mode must be start or resume")
    require(RUN_ID_RE.fullmatch(run_id) is not None, "Live run_id is not frozen langgraph form")
    require(os.environ.get("OPENAI_API_KEY", "") != "", "OPENAI_API_KEY is required for Step 2A.08 live execution")
    base_url = os.environ.get("GATE2A_DRUPAL_BASE_URL", "")
    username = os.environ.get("GATE2A_DRUPAL_USERNAME", "")
    password = os.environ.get("GATE2A_DRUPAL_PASSWORD", "")
    require(base_url and username and password, "Drupal live environment is incomplete")
    require(username == "agent_bot", "LangGraph batch semantic operations must run as agent_bot")

    # Lazy imports keep Step 2A.07 construction verification provider/Drupal free.
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI
    from agentic_harness_langgraph.tools import build_tools
    from agentic_harness_langgraph.vertical_slice import (
        ModelOutput,
        SYSTEM_PROMPT,
        context_summary,
        deterministic_validate,
        user_prompt,
    )
    from shared.drupal_client.client import DrupalClient

    targets = load_targets(repo)
    evidence.mkdir(parents=True, exist_ok=True)
    events_path = evidence / "events.jsonl"
    sqlite_path = repo / "langchain/.gate2a-runtime" / f"{run_id}.sqlite"
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    config = {"configurable": {"thread_id": run_id}}

    if mode == "start":
        require(not sqlite_path.exists(), "Live batch runtime DB already exists")
        require(not (evidence / "run.json").exists(), "Live batch result directory is not fresh")
    else:
        require(sqlite_path.exists() and sqlite_path.stat().st_size > 0, "Live batch runtime DB is missing for resume")
        require((evidence / "run.json").is_file(), "Live batch run.json is missing for resume")

    client = DrupalClient(base_url=base_url, username=username, password=password, verify_tls=False, timeout_seconds=60)
    tools = build_tools(client, correlation_id=f"{run_id}-batch")
    expected_tools = ["find_images_needing_review", "get_image_context", "submit_recommendation", "get_recommendation_status"]
    require(list(tools) == expected_tools, "LangGraph tool surface differs from frozen shared operation set")

    counters_path = evidence / "call-counters.json"
    if counters_path.exists():
        counters = json.loads(counters_path.read_text(encoding="utf-8"))
    else:
        counters = {
            "model_invocations_attempted": 0,
            "model_invocations_succeeded": 0,
            "automatic_model_retries_configured": 0,
            "semantic_retry_loop_performed": False,
            "find_images_needing_review": 0,
            "get_image_context": 0,
            "submit_recommendation": 0,
            "get_recommendation_status": 0,
        }
    write_json(counters_path, counters)

    output_items = _load_collection(evidence / "model-outputs.json", "outputs", {"run_id": run_id, "framework_origin": "langgraph"})
    rec_items = _load_collection(evidence / "recommendations.json", "recommendations", {"run_id": run_id, "source_framework": "langgraph"})
    validation_items = _load_collection(evidence / "validation.json", "results", {"run_id": run_id, "source_framework": "langgraph"})
    submission_items = _load_collection(evidence / "submissions.json", "submissions", {"run_id": run_id, "framework_origin": "langgraph"})
    status_items = _load_collection(evidence / "statuses.json", "observations", {"run_id": run_id, "framework_origin": "langgraph"})
    trace_items = _load_collection(evidence / "tool-traces.json", "traces", {"run_id": run_id, "source_framework": "langgraph"})
    privacy_probes: dict[str, str] = {"drupal_password": password, "openai_api_key": os.environ.get("OPENAI_API_KEY", "")}

    def flush() -> None:
        write_json(evidence / "model-outputs.json", {"schema_version": 1, "run_id": run_id, "framework_origin": "langgraph", "outputs": output_items})
        write_json(evidence / "recommendations.json", {"schema_version": 1, "run_id": run_id, "source_framework": "langgraph", "recommendations": rec_items})
        write_json(evidence / "validation.json", {"schema_version": 1, "run_id": run_id, "source_framework": "langgraph", "validator_version": VALIDATOR_VERSION, "results": validation_items})
        write_json(evidence / "submissions.json", {"schema_version": 1, "run_id": run_id, "framework_origin": "langgraph", "submissions": submission_items})
        write_json(evidence / "statuses.json", {"schema_version": 1, "run_id": run_id, "framework_origin": "langgraph", "observations": status_items})
        write_json(evidence / "tool-traces.json", {"schema_version": 1, "run_id": run_id, "source_framework": "langgraph", "traces": trace_items})
        write_json(counters_path, counters)

    def invoke_tool(name: str, payload: dict[str, Any], target: dict[str, Any] | None = None) -> dict[str, Any]:
        started = now()
        counters[name] += 1
        write_json(counters_path, counters)
        result = tools[name].invoke(payload)
        require(isinstance(result, dict) and result.get("ok") is True and result.get("error") is None, f"{name} failed")
        require(result.get("tool_name") == name and isinstance(result.get("data"), dict), f"{name} envelope differs")
        data = result["data"]
        completed = now()
        trace_items.append({
            "operation": name,
            "correlation_id": str(result.get("correlation_id") or f"{run_id}-batch"),
            "started_at": started,
            "completed_at": completed,
            "ok": True,
            "sequence": target.get("sequence") if target else None,
            "target": target,
            "result_sha256": "sha256:" + sha(data),
            "recommendation_uuid": data.get("uuid") if name in {"submit_recommendation", "get_recommendation_status"} else None,
            "error": None,
        })
        flush()
        return data

    if mode == "start":
        discovery = invoke_tool("find_images_needing_review", {})
        discovered = discovery.get("targets")
        require(discovery.get("total_count") == 12 and discovered == targets, "Live discovery differs from frozen target sequence")
        write_json(evidence / "targets.json", {"schema_version": 1, "target_sequence_sha256": TARGET_HASH, "targets": targets})
        started_at = now()
        write_json(evidence / "run-metadata.json", {
            "schema_version": 1,
            "run_id": run_id,
            "framework_origin": "langgraph",
            "thread_id": run_id,
            "provider": "OpenAI",
            "model": MODEL_ID,
            "temperature": TEMPERATURE,
            "prompt_version": PROMPT_VERSION,
            "validator_version": VALIDATOR_VERSION,
            "target_count": 12,
            "controlled_stop_after_sequence": 6,
            "resume_at_sequence": 7,
            "automatic_model_retries": 0,
            "semantic_retry_loop": False,
            "gate2c_failure_injection": False,
            "started_at": started_at,
        })
        emit_event(events_path, event_type="run_initialized", run_id=run_id, correlation_id=f"{run_id}-batch", outcome="started")
        emit_event(events_path, event_type="run_started", run_id=run_id, correlation_id=f"{run_id}-batch", outcome="started")
    else:
        started_at = json.loads((evidence / "run.json").read_text(encoding="utf-8"))["started_at"]
        emit_event(events_path, event_type="run_resumed", run_id=run_id, sequence=7, correlation_id=f"{run_id}-batch", target=targets[6], outcome="resumed")

    def process(sequence: int, state: LangGraphRunState) -> LangGraphRunState:
        require(sequence == int(state["next_target_index"]) + 1, "Live graph attempted to skip/reprocess target")
        target = targets[sequence - 1]
        emit_event(events_path, event_type="target_started", run_id=run_id, sequence=sequence, correlation_id=f"{run_id}-batch", target=target, outcome="started")
        before_model = invoke_tool("get_image_context", {"target": target}, target)
        emit_event(events_path, event_type="context_collected", run_id=run_id, sequence=sequence, correlation_id=f"{run_id}-batch", target=target, outcome="persisted")
        require(before_model.get("target") == target, "Pre-model context target differs")
        article_body = str(before_model["article"]["body_plain"])
        representation = str(before_model["image"]["representation"]["value"])
        privacy_probes[f"article_body_{sequence}"] = article_body
        privacy_probes[f"image_representation_{sequence}"] = representation
        prompt = user_prompt(target, before_model)

        model = ChatOpenAI(model=MODEL_ID, temperature=TEMPERATURE, max_retries=0).with_structured_output(ModelOutput, method="json_schema", strict=True)
        counters["model_invocations_attempted"] += 1
        write_json(counters_path, counters)
        emit_event(events_path, event_type="model_invocation_started", run_id=run_id, sequence=sequence, correlation_id=f"{run_id}-batch", target=target, outcome="started")
        result = model.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": representation, "detail": "auto"}},
            ]),
        ])
        parsed = result if isinstance(result, ModelOutput) else ModelOutput.model_validate(result)
        counters["model_invocations_succeeded"] += 1
        model_output = parsed.model_dump()
        output_items.append({"sequence": sequence, "target": target, "model_output": model_output})
        flush()
        emit_event(events_path, event_type="model_output_received", run_id=run_id, sequence=sequence, correlation_id=f"{run_id}-batch", target=target, outcome="persisted")

        before_submit = invoke_tool("get_image_context", {"target": target}, target)
        require(before_submit.get("evidence_hash") == before_model.get("evidence_hash"), "Context changed between model and submission")
        errors = deterministic_validate(model_output["proposed_alt_text"], before_submit)
        validation = {"sequence": sequence, "target": target, "structured_output_schema_valid": True, "deterministic_validation_passed": not errors, "errors": errors}
        validation_items.append(validation)
        flush()
        emit_event(events_path, event_type="validation_completed", run_id=run_id, sequence=sequence, correlation_id=f"{run_id}-batch", target=target, outcome="passed" if not errors else "failed", error_code=errors[0] if errors else None)
        require(not errors, f"Deterministic validation failed for sequence {sequence}: {errors!r}")

        recommendation = {
            "schema_version": 1,
            "target": target,
            "proposed_alt_text": model_output["proposed_alt_text"].strip(),
            "source_framework": "langgraph",
            "run_id": run_id,
            "evidence_hash": before_submit["evidence_hash"],
            "validator_version": VALIDATOR_VERSION,
        }
        rec_items.append({"sequence": sequence, "target": target, "recommendation": recommendation})
        flush()
        submission = invoke_tool("submit_recommendation", {"recommendation": recommendation}, target)
        require(submission.get("status") == "pending" and submission.get("run_id") == run_id and submission.get("target") == target, "Submission differs")
        rec_uuid = str(submission["uuid"])
        submission_items.append({
            "sequence": sequence,
            "target": target,
            "node_id": int(submission["node_id"]),
            "uuid": rec_uuid,
            "revision_id": int(submission["revision_id"]),
            "initial_status": "pending",
            "idempotent_replay_same_identity": False,
        })
        flush()
        emit_event(events_path, event_type="recommendation_submitted", run_id=run_id, sequence=sequence, correlation_id=f"{run_id}-batch", target=target, outcome="persisted")
        status_data = invoke_tool("get_recommendation_status", {"recommendation_id": rec_uuid}, target)
        require(status_data.get("status") == "pending" and status_data.get("reviewer_username") is None, "Pending status differs")
        status_items.append({"recommendation_uuid": rec_uuid, "revision_id": int(status_data["revision_id"]), "status": "pending", "observed_at": now()})
        flush()
        emit_event(events_path, event_type="status_observed", run_id=run_id, sequence=sequence, correlation_id=f"{run_id}-batch", target=target, outcome="persisted")
        after_submit = invoke_tool("get_image_context", {"target": target}, target)
        require(after_submit.get("evidence_hash") == before_model.get("evidence_hash"), "Source context changed after submission")
        emit_event(events_path, event_type="context_collected", run_id=run_id, sequence=sequence, correlation_id=f"{run_id}-batch", target=target, outcome="persisted")

        updated = advance_target(state, target, now())
        updated["recommendation_ids"] = [*state["recommendation_ids"], {"sequence": sequence, "node_id": int(submission["node_id"]), "uuid": rec_uuid, "revision_id": int(submission["revision_id"])}]
        updated["validation_results"] = [*state["validation_results"], validation]
        if sequence == 6:
            updated = mark_boundary(updated, now())
        if sequence == 12:
            updated = complete_state(updated, now())
        flush()
        emit_event(events_path, event_type="target_completed", run_id=run_id, sequence=sequence, correlation_id=f"{run_id}-batch", target=target, outcome="persisted")
        return updated

    with SqliteSaver.from_conn_string(str(sqlite_path)) as saver:
        graph = build_graph(process, saver)
        if mode == "start":
            graph.invoke(initial_state(run_id, started_at), config)
            snapshot = graph.get_state(config)
            state = dict(snapshot.values)
            require(task_interrupt_count(snapshot) > 0, "Live batch did not persist continuation interrupt")
            require(state.get("next_target_index") == 6 and state.get("status") == "interrupted", "Live midpoint state differs")
            require(counters["model_invocations_succeeded"] == 6 and counters["model_invocations_attempted"] == 6, "Live start did not use exactly six model calls")
            require(counters["find_images_needing_review"] == 1 and counters["get_image_context"] == 18 and counters["submit_recommendation"] == 6 and counters["get_recommendation_status"] == 6, "Live midpoint Drupal semantic call counters differ")
            validate_json(repo, "langgraph-run-state.schema.json", state, "live midpoint checkpoint")
            write_json(evidence / "checkpoint-before-continuation.json", state)
            write_json(evidence / "run.json", state)
            privacy = checkpoint_privacy(sqlite_path, state, evidence, privacy_probes)
            write_json(evidence / "checkpoint-privacy-before-continuation.json", privacy)
            require(privacy["status"] == "pass", f"Live midpoint checkpoint/evidence privacy failed: {privacy!r}")
            emit_event(events_path, event_type="continuation_interrupted", run_id=run_id, sequence=6, correlation_id=f"{run_id}-batch", target=targets[5], outcome="interrupted")
            validate_events(repo, events_path, "live midpoint events")
            write_json(evidence / "continuation-event.json", {"schema_version": 1, "run_id": run_id, "thread_id": run_id, "completed_before_stop": [1,2,3,4,5,6], "resume_at_sequence": 7, "controlled_stop": True, "gate2c_failure_injection": False, "interrupt_count": task_interrupt_count(snapshot)})
        else:
            before = graph.get_state(config)
            before_state = dict(before.values)
            validate_resume_boundary(repo, evidence, run_id, targets, counters, before_state, task_interrupt_count(before))
            first_half_ids = deepcopy(before_state.get("recommendation_ids", []))
            result = graph.invoke(Command(resume={"continue_after_sequence": 6}), config)
            after = graph.get_state(config)
            state = dict(after.values)
            require(task_interrupt_count(after) == 0 and state == result, "Live resume checkpoint differs")
            require(state.get("status") == "completed" and state.get("next_target_index") == 12, "Live batch did not complete 12 targets")
            require(state.get("recommendation_ids", [])[:6] == first_half_ids, "First six recommendation identities changed on resume")
            all_uuids = [item["uuid"] for item in state.get("recommendation_ids", [])]
            require(len(all_uuids) == 12 and len(set(all_uuids)) == 12, "Live batch duplicate recommendation identity detected")
            require(counters["model_invocations_succeeded"] == 12 and counters["model_invocations_attempted"] == 12, "Live batch did not use exactly 12 model calls")
            require(counters["find_images_needing_review"] == 1 and counters["get_image_context"] == 36 and counters["submit_recommendation"] == 12 and counters["get_recommendation_status"] == 12, "Live completed Drupal semantic call counters differ")
            require(counters["automatic_model_retries_configured"] == 0 and counters["semantic_retry_loop_performed"] is False, "Retry policy changed")
            write_json(evidence / "checkpoint-after-continuation.json", state)
            recovery = {
                "schema_version": 1,
                "run_id": run_id,
                "source_framework": "langgraph",
                "controlled_stop_after_sequence": 6,
                "resume_at_sequence": 7,
                "completed_before_stop": [1,2,3,4,5,6],
                "interrupted_at": before_state["interrupted_at"],
                "resumed_at": state["resumed_at"],
                "resumed_with_run_id": run_id,
                "duplicate_count": 0,
                "completed_after_resume": [7,8,9,10,11,12],
                "gate2c_failure_injection_fired": False,
            }
            write_json(evidence / "recovery.json", recovery)
            summary = {
                "schema_version": 1,
                "status": "pass",
                "run_id": run_id,
                "source_framework": "langgraph",
                "provider": "OpenAI",
                "model": MODEL_ID,
                "temperature": 0.0,
                "target_count": 12,
                "completed_count": 12,
                "failed_count": 0,
                "duplicate_count": 0,
                "validator_version": VALIDATOR_VERSION,
                "review_destination": "alt_text_suggestion",
                "source_article_unchanged": True,
                "automatic_publication_performed": False,
                "failure_seam_observed": False,
                "resume_sequence": 7,
                "started_at": started_at,
                "completed_at": state["completed_at"],
                "human_review_completed": False,
            }
            write_json(evidence / "summary.json", summary)
            write_json(evidence / "run.json", state)
            final_privacy = checkpoint_privacy(sqlite_path, state, evidence, privacy_probes)
            write_json(evidence / "checkpoint-privacy-after-continuation.json", final_privacy)
            require(final_privacy["status"] == "pass", f"Live completed checkpoint/evidence privacy failed: {final_privacy!r}")
            emit_event(events_path, event_type="run_completed", run_id=run_id, sequence=12, correlation_id=f"{run_id}-batch", target=targets[11], outcome="completed")
            validate_events(repo, events_path, "live completed events")
            (evidence / "summary.md").write_text(
                "# LangGraph 12-target batch\n\n- status: pass\n- continuation: after 6, resume at 7\n- duplicate count: 0\n- human review: not performed by batch runner\n",
                encoding="utf-8",
            )
            flush()
            validate_json(repo, "langgraph-batch-target-sequence.schema.json", json.loads((evidence / "targets.json").read_text()), "targets")
            for filename, schema_name in (
                ("model-outputs.json", "langgraph-batch-model-outputs.schema.json"),
                ("recommendations.json", "langgraph-batch-recommendations.schema.json"),
                ("validation.json", "langgraph-batch-validation.schema.json"),
                ("submissions.json", "langgraph-batch-submissions.schema.json"),
                ("statuses.json", "langgraph-batch-statuses.schema.json"),
                ("tool-traces.json", "langgraph-batch-tool-traces.schema.json"),
                ("recovery.json", "langgraph-batch-recovery.schema.json"),
                ("summary.json", "langgraph-batch-summary.schema.json"),
            ):
                validate_json(repo, schema_name, json.loads((evidence / filename).read_text()), filename)
            validate_json(repo, "langgraph-run-state.schema.json", state, "completed checkpoint")
            validate_json(repo, "langgraph-run-state.schema.json", json.loads((evidence / "run.json").read_text()), "run.json")

    return {"mode": mode, "run_id": run_id, "state": state, "call_counters": counters}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--mode", choices=("construction-test", "start", "resume"), required=True)
    args = ap.parse_args()
    repo = Path(args.repo).resolve()
    evidence = Path(args.evidence).resolve()
    if args.mode == "construction-test":
        result = construction_test(repo, evidence, args.run_id)
    else:
        result = live_run(repo, evidence, args.run_id, args.mode)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
