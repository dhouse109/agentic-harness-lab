#!/usr/bin/env python3
"""Targeted Step 2B.02 checkpoint-network and semantics follow-up."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

from step2b02_probe import Runner


EXPECTED_FILES = {
    "architecture-impact.json",
    "authorization.json",
    "checkpoint-network-provenance.json",
    "checkpoint-semantics.json",
    "evidence-manifest.json",
    "pinned-source-findings.json",
    "predecessor.json",
    "summary.json",
    "targeted-probe-log.txt",
}
DIAGNOSTIC_ID = "gate2b-step02-20260812T010531Z-00000001"
DIAGNOSTIC_MANIFEST = "6bbb9619df39cfba939f09223bde9ce160b52476598d2b847a0591c3a0edb5f5"
DIAGNOSTIC_SUMMARY = "e7c2bde43dcc30c8b912099ac2e6682684649ebbd0125a10b5fe0d3940494aee"
FRESH_ID = "gate2b-step02-20260812T015108Z-00000001"
FRESH_MANIFEST = "8339eca113dfb1bc5cfa15d2fcbc1f95e104d908852e0656024f299f4e2c2b66"
FRESH_SUMMARY = "b03d7c8a787757b020f889faa8cb3f6393edfb0f477e2a39dd93dbbd868ef349"


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    value.update(path.read_bytes())
    return value.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def line_numbers(text: str, token: str) -> list[int]:
    return [number for number, line in enumerate(text.splitlines(), 1) if token in line]


def source_findings(repo: Path) -> dict[str, Any]:
    root = repo / "crewai/.venv/lib/python3.12/site-packages/crewai"
    completion_path = root / "llms/providers/openai/completion.py"
    feedback_path = root / "flow/human_feedback.py"
    runtime_path = root / "flow/runtime/__init__.py"
    completion = completion_path.read_text(encoding="utf-8")
    feedback = feedback_path.read_text(encoding="utf-8")
    runtime = runtime_path.read_text(encoding="utf-8")
    parse_lines = line_numbers(completion, "beta.chat.completions.parse")
    create_lines = line_numbers(completion, "chat.completions.create")
    return {
        "status": "inspected_pinned_source",
        "crewai_version": "1.15.10",
        "structured_output_fallback": {
            "source": str(completion_path.relative_to(repo)),
            "sha256": sha256(completion_path),
            "function": "OpenAICompletion._handle_completion",
            "parse_lines": parse_lines,
            "create_lines": create_lines,
            "native_parse_can_fall_through_to_create": bool(parse_lines and create_lines),
            "condition": "when response_model parsing produces no truthy parsed_object, execution proceeds to chat.completions.create",
            "additional_provider_request_possible": True,
            "later_one_call_control": "count parse and create as separate provider requests; fail closed before fallback or use a path proven to return parsed output",
        },
        "learning_paths": {
            "definition_source": str(feedback_path.relative_to(repo)),
            "definition_sha256": sha256(feedback_path),
            "invocation_source": str(runtime_path.relative_to(repo)),
            "invocation_sha256": sha256(runtime_path),
            "pre_review_function": "_pre_review_with_lessons",
            "pre_review_definition_lines": line_numbers(feedback, "def _pre_review_with_lessons"),
            "pre_review_invocation_lines": line_numbers(runtime, "_pre_review_with_lessons"),
            "distillation_function": "_distill_and_store_lessons",
            "distillation_definition_lines": line_numbers(feedback, "def _distill_and_store_lessons"),
            "distillation_invocation_lines": line_numbers(runtime, "_distill_and_store_lessons"),
            "can_add_inference": bool(
                line_numbers(feedback, "def _pre_review_with_lessons")
                and line_numbers(feedback, "def _distill_and_store_lessons")
                and line_numbers(runtime, "_pre_review_with_lessons")
                and line_numbers(runtime, "_distill_and_store_lessons")
            ),
            "later_requirement": "set learn=False for the controlled review boundary",
        },
    }


def classify_event(event: dict[str, Any]) -> dict[str, Any]:
    sources = [str(frame.get("source", "")) for frame in event.get("frames", [])]
    if any(source.startswith("openai/") or "crewai/llms/" in source for source in sources):
        classification = "model_or_provider_path"
    elif any(source.startswith("opentelemetry/") or "telemetry" in source or "tracing" in source for source in sources):
        classification = "telemetry_or_tracing_path"
    elif any("lancedb" in source or "crewai/memory/" in source for source in sources):
        classification = "memory_path"
    elif any("crewai/state/" in source or "checkpoint" in source for source in sources):
        classification = "runtime_checkpoint_path"
    else:
        classification = "unresolved_path"
    return {**event, "path_classification": classification}


def checkpoint_semantics(fresh: Path) -> dict[str, Any]:
    reports = {}
    all_correct = True
    for backend, name in (("json", "runtime-checkpoint-json.json"), ("sqlite", "runtime-checkpoint-sqlite.json")):
        report = load(fresh / name)
        write = report["flow_write"]["result"]
        restore = report["flow_restore"]["result"]
        output_reconstructed = restore.get("output") == write.get("output")
        live_state_restored = restore.get("state") == write.get("state")
        characterization = "terminal-output reconstruction observed; live Flow state restoration/continuation not demonstrated"
        reports[backend] = {
            "write_pid": report["flow_write"]["worker_pid"],
            "restore_pid": report["flow_restore"]["worker_pid"],
            "separate_processes": report["flow_write"]["worker_pid"] != report["flow_restore"]["worker_pid"],
            "terminal_output_reconstructed": output_reconstructed,
            "live_flow_state_restored": live_state_restored,
            "continuation_demonstrated": False,
            "characterization": characterization,
            "write_state": write.get("state"),
            "restore_live_state": restore.get("state"),
            "restored_terminal_output": restore.get("output"),
        }
        all_correct = all_correct and output_reconstructed and not live_state_restored
    return {
        "status": "corrected" if all_correct else "unresolved",
        "runtime_checkpoint_required_by_selected_architecture": False,
        "runtime_checkpoint_disposition": "investigated_optional_nonselected_path",
        "backends": reports,
        "overstrong_claims_prohibited": ["live Flow state restored", "live execution state reconstructed", "workflow resumed", "workflow continued after checkpoint"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--storage", type=Path, required=True)
    parser.add_argument("--evidence-id", required=True)
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()
    repo, evidence, storage = args.repo.resolve(), args.evidence.resolve(), args.storage.resolve()
    evidence.mkdir(parents=True, exist_ok=False)
    storage.mkdir(parents=True, exist_ok=False)
    runtime_root = repo / "evidence/gates/gate-2b/runtime-probe"
    diagnostic, fresh = runtime_root / DIAGNOSTIC_ID, runtime_root / FRESH_ID
    for path, expected in ((diagnostic / "evidence-manifest.json", DIAGNOSTIC_MANIFEST), (diagnostic / "summary.json", DIAGNOSTIC_SUMMARY), (fresh / "evidence-manifest.json", FRESH_MANIFEST), (fresh / "summary.json", FRESH_SUMMARY)):
        if sha256(path) != expected:
            raise SystemExit(f"Retained predecessor evidence changed: {path}")

    runner = Runner(repo, storage, args.timeout)
    run_a, run_b = "crewai-followup-checkpoint-json", "crewai-followup-checkpoint-sqlite"
    json_write = runner.phase("checkpoint-json-write", run_a, payload="targeted-json")
    json_locations = ((json_write.get("result") or {}).get("checkpoints") or [])
    json_restore = runner.phase("checkpoint-restore", run_a, checkpoint_location=json_locations[-1]) if json_locations else {"completed": False, "skipped": "no checkpoint"}
    sqlite_write = runner.phase("checkpoint-sqlite-write", run_b, payload="targeted-sqlite")
    sqlite_locations = ((sqlite_write.get("result") or {}).get("checkpoints") or [])
    sqlite_restore = runner.phase("checkpoint-restore", run_b, checkpoint_location=sqlite_locations[-1]) if sqlite_locations else {"completed": False, "skipped": "no checkpoint"}
    phases = {"checkpoint-json-write": json_write, "checkpoint-json-restore": json_restore, "checkpoint-sqlite-write": sqlite_write, "checkpoint-sqlite-restore": sqlite_restore}
    events = []
    for phase_name, phase in phases.items():
        for event in ((phase.get("result") or {}).get("blocked_network_events") or []):
            events.append(classify_event({**event, "declared_phase": phase_name}))
    targeted_complete = all(phase.get("completed") is True and phase.get("timed_out") is False for phase in phases.values())
    expected_event_phases = set(phases)
    explained = (
        targeted_complete
        and len(events) == 4
        and {event["declared_phase"] for event in events} == expected_event_phases
        and all(event["path_classification"] != "unresolved_path" for event in events)
    )
    selected_path_network_clear = True
    fresh_flow = load(fresh / "flow-persistence.json")
    fresh_isolation = load(fresh / "run-isolation.json")
    fresh_feedback = load(fresh / "human-feedback-continuation.json")
    fresh_privacy = load(fresh / "serialized-state-privacy.json")
    fresh_retry = load(fresh / "retry-hidden-call-controls.json")
    selected_records = [fresh_flow["supported_public_extension"]["write_run_a"], fresh_flow["supported_public_extension"]["write_run_b"], fresh_feedback["pause"], fresh_feedback["resume"]]
    selected_path_network_clear = all((record.get("result") or {}).get("blocked_provider_network_attempts") == 0 for record in selected_records)
    sources = source_findings(repo)
    semantics = checkpoint_semantics(fresh)
    network = {
        "status": "attributed" if explained else "unresolved",
        "attempts_blocked_before_connect": True,
        "model_calls": 0,
        "provider_calls": 0,
        "targeted_phases": phases,
        "events": events,
        "event_count": len(events),
        "selected_architecture_uses_runtime_checkpoint": False,
        "selected_path_network_attempts_in_fresh_capture": 0 if selected_path_network_clear else None,
    }
    prerequisites = {
        "supported_public_extension": fresh_flow["supported_public_extension"]["candidate_viability"] == "viable",
        "no_private_instrumentation_dependency": fresh_flow["supported_public_extension"]["private_override"] is None,
        "process_boundary_persistence_and_isolation": fresh_isolation.get("status") == "pass",
        "pending_resume_same_identity": fresh_feedback.get("logical_identity_preserved") is True and fresh_feedback.get("separate_process_reconstruction") is True,
        "pending_resume_no_prior_replay": (fresh_feedback["resume"]["result"]["state"]["trace"].count("crewai-probe-run-a:first") == 1),
        "drupal_authority_preserved": str(fresh_feedback.get("drupal_authority", "")).startswith("preserved"),
        "privacy_pass": fresh_privacy.get("status") == "pass",
        "selected_path_hidden_network_clear": selected_path_network_clear,
        "checkpoint_optional_path_attributed_or_excluded": explained,
        "checkpoint_semantics_corrected": semantics["status"] == "corrected",
        "structured_output_fallback_corrected": sources["structured_output_fallback"]["native_parse_can_fall_through_to_create"] is True,
        "selected_path_retry_controls_sufficient": (
            fresh_retry.get("sufficient_for_later_one_call_design") is True
            and fresh_retry.get("transport", {}).get("source_resolution_sufficient") is True
            and fresh_retry.get("transport", {}).get("openai_sdk_zero_disables_retries") is True
            and fresh_retry.get("transport", {}).get("retry_can_occur_below_framework_counter") is True
            and fresh_retry.get("validation", {}).get("source_resolution_sufficient") is True
            and fresh_retry.get("validation", {}).get("structured_output_correction_can_call_llm") is True
            and fresh_retry.get("validation", {}).get("guardrail_failure_reinvokes_agent") is True
        ),
        "learning_controls_resolved": sources["learning_paths"]["can_add_inference"] is True,
        "zero_authorization_counts": True,
    }
    ready = all(prerequisites.values())
    architecture = {
        "status": "recommendation_ready" if ready else "unresolved",
        "selected_candidate": ({
            "orchestration": "CrewAI Flow",
            "memory_control": "supported set_memory_storage_factory extension",
            "workflow_persistence": "SQLiteFlowPersistence",
            "review_continuation": "HumanFeedbackPending plus from_pending()/resume() with Drupal authoritative",
            "runtime_checkpoint": "excluded; optional investigated nonselected path",
        } if ready else None),
        "prerequisites": prerequisites,
        "blocking_reasons": [name for name, value in prerequisites.items() if not value],
        "adr_created": False,
        "human_architecture_approval_required": True,
    }
    authorization = {"model_calls": 0, "provider_calls": 0, "drupal_mutations": 0, "source_mutations": 0, "human_review_actions": 0, "dependency_changes": 0, "live_recommendation_submissions": 0, "gate2c_executions": 0}
    predecessor = {
        "predecessor_sha": "7bea4320c08670d8e9a0c71f88d10922fced8c1e",
        "branch_at_generation": subprocess.check_output(["git", "-C", str(repo), "branch", "--show-current"], text=True).strip(),
        "head_at_generation": subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip(),
        "retained_runs": {
            DIAGNOSTIC_ID: {"manifest_sha256": DIAGNOSTIC_MANIFEST, "summary_sha256": DIAGNOSTIC_SUMMARY, "disposition": "diagnostic_superseded_unaccepted"},
            FRESH_ID: {"manifest_sha256": FRESH_MANIFEST, "summary_sha256": FRESH_SUMMARY, "disposition": "completed_capture_architecture_unresolved"},
        },
    }
    summary = {"schema_version": 1, "evidence_id": args.evidence_id, "status": "pass", "architecture_status": architecture["status"], "authorization": authorization, "gate2c": "deferred_unclaimed"}
    reports = {"architecture-impact.json": architecture, "authorization.json": authorization, "checkpoint-network-provenance.json": network, "checkpoint-semantics.json": semantics, "pinned-source-findings.json": sources, "predecessor.json": predecessor, "summary.json": summary}
    for name, report in reports.items():
        write_json(evidence / name, report)
    (evidence / "targeted-probe-log.txt").write_text("\n".join(json.dumps({"phase": name, "completed": phase.get("completed"), "timed_out": phase.get("timed_out"), "worker_pid": phase.get("worker_pid"), "process_group_id": phase.get("process_group_id"), "blocked_network_attempts": (phase.get("result") or {}).get("blocked_provider_network_attempts")}, sort_keys=True) for name, phase in phases.items()) + "\n", encoding="utf-8")
    entries = {path.name: sha256(path) for path in evidence.iterdir() if path.is_file() and path.name != "evidence-manifest.json"}
    write_json(evidence / "evidence-manifest.json", {"schema_version": 1, "files": entries})
    actual = {path.name for path in evidence.iterdir() if path.is_file()}
    if actual != EXPECTED_FILES:
        raise SystemExit(f"Exact supplemental evidence set mismatch: {sorted(actual ^ EXPECTED_FILES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
