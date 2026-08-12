#!/usr/bin/env python3
"""Create a governed interpretation of immutable Step 2B.02 network evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any


BASE = "7bea4320c08670d8e9a0c71f88d10922fced8c1e"
DIAGNOSTIC = ("gate2b-step02-20260812T010531Z-00000001", "6bbb9619df39cfba939f09223bde9ce160b52476598d2b847a0591c3a0edb5f5", "e7c2bde43dcc30c8b912099ac2e6682684649ebbd0125a10b5fe0d3940494aee")
FRESH = ("gate2b-step02-20260812T015108Z-00000001", "8339eca113dfb1bc5cfa15d2fcbc1f95e104d908852e0656024f299f4e2c2b66", "b03d7c8a787757b020f889faa8cb3f6393edfb0f477e2a39dd93dbbd868ef349")
FOLLOWUP = ("gate2b-step02-followup-20260812T022947Z-00000001", "6654fd33e10efdf275f0aa9ea104293ed1f7ba3092d054718a9ac0a491b07a79", "48fa2e41db6089cf63d3f250b8a31c547c322dc8e72d8a25ae9dc1078a734a57")
FILES = {"architecture-disposition.json", "authorization.json", "evidence-manifest.json", "network-event-disposition.json", "provenance.json", "summary.json"}
PHASES = {"checkpoint-json-write", "checkpoint-json-restore", "checkpoint-sqlite-write", "checkpoint-sqlite-restore"}
CALL_PREFIX = [
    ("crewai/events/event_bus.py", "_call_handlers"),
    ("crewai/events/utils/handlers.py", "is_call_handler_safe"),
    ("crewai/events/event_listener.py", "on_flow_started"),
    ("crewai/events/utils/console_formatter.py", "handle_flow_started"),
    ("crewai/events/utils/console_formatter.py", "_show_version_update_message_if_needed"),
    ("crewai_core/version.py", "is_newer_version_available"),
    ("crewai_core/version.py", "check_version"),
    ("crewai_core/version.py", "get_latest_version_from_pypi"),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def retained(repo: Path) -> tuple[Path, Path, Path]:
    runtime = repo / "evidence/gates/gate-2b/runtime-probe"
    followup = repo / "evidence/gates/gate-2b/runtime-probe-followup"
    paths = (runtime / DIAGNOSTIC[0], runtime / FRESH[0], followup / FOLLOWUP[0])
    for path, (_, manifest, summary) in zip(paths, (DIAGNOSTIC, FRESH, FOLLOWUP), strict=True):
        if sha(path / "evidence-manifest.json") != manifest or sha(path / "summary.json") != summary:
            raise SystemExit(f"Retained evidence changed: {path.name}")
    return paths


def version_sources(repo: Path) -> dict[str, Any]:
    console = repo / "crewai/.venv/lib/python3.12/site-packages/crewai/events/utils/console_formatter.py"
    version = repo / "crewai/.venv/lib/python3.12/site-packages/crewai_core/version.py"
    console_text = console.read_text(encoding="utf-8")
    version_text = version.read_text(encoding="utf-8")
    required_console = ["CREWAI_DISABLE_VERSION_CHECK", "_show_version_update_message_if_needed", "is_newer_version_available()"]
    required_version = ["def get_latest_version_from_pypi", "request.urlopen(", "def check_version", "def is_newer_version_available"]
    if any(token not in console_text for token in required_console) or any(token not in version_text for token in required_version):
        raise SystemExit("Pinned version-check source path is incomplete")
    if console_text.index("CREWAI_DISABLE_VERSION_CHECK") > console_text.index("is_newer_version_available()"):
        raise SystemExit("Public disable control does not precede the version helper")
    return {
        "console_formatter": {"path": str(console.relative_to(repo)), "sha256": sha(console)},
        "version_module": {"path": str(version.relative_to(repo)), "sha256": sha(version)},
        "source_path": [name for name, _ in CALL_PREFIX] + ["urllib/request.py"],
        "interpretation": "CrewAI console version-availability check triggered by Flow-start events",
        "not_model_or_provider": True,
        "not_checkpoint_persistence": True,
        "not_memory_initialization": True,
        "not_telemetry_export": True,
    }


def public_control(repo: Path) -> dict[str, Any]:
    code = r'''
import json, os, socket
import crewai.events.utils.console_formatter as module
attempts = {"count": 0}
def blocked(*args, **kwargs):
    attempts["count"] += 1
    raise OSError("gate2b disposable network guard")
socket.create_connection = blocked
formatter = module.ConsoleFormatter(verbose=True)
os.environ.pop("CI", None)
os.environ.pop("CREWAI_DISABLE_VERSION_CHECK", None)
formatter._show_version_update_message_if_needed()
enabled = attempts["count"]
attempts["count"] = 0
os.environ["CREWAI_DISABLE_VERSION_CHECK"] = "true"
formatter._show_version_update_message_if_needed()
print(json.dumps({"enabled_blocked_attempts": enabled, "disabled_blocked_attempts": attempts["count"]}, sort_keys=True))
'''
    env = {key: value for key, value in os.environ.items() if key not in {"OPENAI_API_KEY", "DRUPAL_PASSWORD", "DRUPAL_BASIC_AUTH_PASSWORD", "ANTHROPIC_API_KEY"}}
    with tempfile.TemporaryDirectory(prefix="gate2b-version-control-") as temporary:
        env.update({"XDG_CACHE_HOME": temporary, "XDG_CONFIG_HOME": temporary, "XDG_DATA_HOME": temporary, "NO_PROXY": "*"})
        result = subprocess.run([str(repo / "crewai/.venv/bin/python"), "-c", code], cwd=repo, env=env, text=True, capture_output=True, timeout=15, check=False)
    if result.returncode != 0:
        raise SystemExit("Public version-check control test failed")
    observed = json.loads(result.stdout.strip())
    if observed.get("enabled_blocked_attempts", 0) < 1 or observed.get("disabled_blocked_attempts") != 0:
        raise SystemExit(f"Unexpected public version-check control behavior: {observed}")
    return {
        "name": "CREWAI_DISABLE_VERSION_CHECK",
        "value": "true",
        "enabled_control_called_version_helpers": True,
        "disabled_control_called_version_helpers": False,
        "successful_network_connections": 0,
        "blocked_network_attempts_enabled": observed["enabled_blocked_attempts"],
        "blocked_network_attempts_disabled": observed["disabled_blocked_attempts"],
        "test_method": "disposable socket.create_connection guard before DNS/connect; no connection attempted",
    }


def architecture_predicates(fresh: dict[str, Any], supplement: dict[str, Any], events_ok: bool, control_ok: bool) -> dict[str, bool]:
    flow = fresh["flow-persistence.json"]
    default = flow["default_unmodified"]
    public = flow["supported_public_extension"]
    isolation = fresh["run-isolation.json"]
    feedback = fresh["human-feedback-continuation.json"]
    privacy = fresh["serialized-state-privacy.json"]
    storage = fresh["storage-provenance.json"]
    retry = fresh["retry-hidden-call-controls.json"]
    semantics = supplement["checkpoint-semantics.json"]
    source = supplement["pinned-source-findings.json"]
    auth = [fresh["authorization.json"], supplement["authorization.json"]]
    trace = feedback["resume"]["result"]["state"]["trace"]
    checks = isolation["checks"]
    required_isolation = ["independent_run_a_persisted_and_reloaded", "independent_run_b_persisted_and_reloaded", "unknown_identity_returns_empty", "cross_identity_returns_requested_b_not_a", "a_and_b_payloads_distinct"]
    selected_phases = [public["write_run_a"], public["write_run_b"], feedback["pause"], feedback["resume"]]
    transport = retry["transport"]
    validation = retry["validation"]
    corrected = "terminal-output reconstruction observed; live Flow state restoration/continuation not demonstrated"
    return {
        "supported_public_crewai_apis": public.get("extension") == "set_memory_storage_factory",
        "no_private_instrumentation_dependency": public.get("private_override") is None,
        "default_and_public_flow_lifecycle_pass": default["phase"].get("completed") is True and all(phase.get("completed") is True for phase in (public["write_run_a"], public["write_run_b"])),
        "sqlite_flow_process_boundary_persistence_observed": all(checks.get(name) is True for name in required_isolation[:2]),
        "independent_ab_isolation_passes": isolation.get("status") == "pass" and all(checks.get(name) is True for name in required_isolation) and checks.get("state_leak_or_alias_detected") is False,
        "wrong_and_unknown_identity_controls_pass": checks.get("unknown_identity_returns_empty") is True and checks.get("cross_identity_returns_requested_b_not_a") is True,
        "pending_resume_preserves_logical_identity": feedback.get("logical_identity_preserved") is True and feedback.get("separate_process_reconstruction") is True,
        "prior_model_owning_work_not_replayed": trace.count("crewai-probe-run-a:first") == 1 and trace.count("crewai-probe-run-a:second") == 1,
        "drupal_remains_authoritative": str(feedback.get("drupal_authority", "")).startswith("preserved"),
        "privacy_and_storage_provenance_pass": privacy.get("status") == "pass" and privacy.get("findings") == [] and storage.get("status") == "pass" and storage.get("ownership") == "crewai" and storage.get("shared_storage_used") is False,
        "checkpoint_semantics_narrow": semantics.get("status") == "corrected" and all(item.get("characterization") == corrected and item.get("live_flow_state_restored") is False and item.get("continuation_demonstrated") is False for item in semantics.get("backends", {}).values()),
        "runtime_checkpoint_explicitly_nonselected": semantics.get("runtime_checkpoint_required_by_selected_architecture") is False and semantics.get("runtime_checkpoint_disposition") == "investigated_optional_nonselected_path",
        "native_parse_to_create_fallback_possible": source["structured_output_fallback"].get("native_parse_can_fall_through_to_create") is True and source["structured_output_fallback"].get("additional_provider_request_possible") is True,
        "transport_retries_zeroable_later": transport.get("openai_sdk_zero_disables_retries") is True and transport.get("source_resolution_sufficient") is True,
        "guardrail_retries_zeroed_or_avoided_later": validation.get("guardrail_failure_reinvokes_agent") is True,
        "structured_correction_disabled_or_budgeted_later": validation.get("structured_output_correction_can_call_llm") is True and validation.get("source_resolution_sufficient") is True,
        "learning_disabled_later": feedback.get("learn") is False and source["learning_paths"].get("later_requirement") == "set learn=False for the controlled review boundary",
        "feedback_collapse_disabled_unless_budgeted": feedback.get("emit") is None and feedback.get("llm") is None,
        "every_provider_request_counted_later": transport.get("retry_can_occur_below_framework_counter") is True and retry.get("sufficient_for_later_one_call_design") is True,
        "version_events_governed_from_immutable_stacks": events_ok,
        "public_version_check_disable_control_verified": control_ok,
        "no_unexplained_selected_path_network_behavior": all((phase.get("result") or {}).get("blocked_provider_network_attempts") == 0 for phase in selected_phases),
        "all_authorization_counts_zero": all(all(value == 0 for value in report.values()) for report in auth),
        "gate2c_deferred_unexecuted": fresh["failure-propagation.json"].get("gate2c_seam_exercised") is False and fresh["summary.json"].get("gate2c") == "deferred_unclaimed" and supplement["summary.json"].get("gate2c") == "deferred_unclaimed",
        "all_required_evidence_and_hashes_intact": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--evidence-id", required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    evidence = args.evidence.resolve()
    if evidence.parent != (repo / "evidence/gates/gate-2b/runtime-probe-disposition").resolve() or evidence.name != args.evidence_id:
        raise SystemExit("Disposition evidence path is outside the exact owned root")
    diagnostic, fresh_path, followup_path = retained(repo)
    fresh = {path.name: read(path) for path in fresh_path.iterdir() if path.suffix == ".json"}
    supplement = {path.name: read(path) for path in followup_path.iterdir() if path.suffix == ".json"}
    events = supplement["checkpoint-network-provenance.json"].get("events", [])
    governed = []
    for event in events:
        frames = event.get("frames", [])
        observed_prefix = [(frame.get("source"), frame.get("function")) for frame in frames[: len(CALL_PREFIX)]]
        if event.get("path_classification") != "unresolved_path" or observed_prefix != CALL_PREFIX:
            raise SystemExit("Immutable event does not support governed version-check disposition")
        governed.append({
            "declared_phase": event["declared_phase"],
            "event_order": event["order"],
            "event_sha256": canonical_sha(event),
            "original_classification": "unresolved_path",
            "governed_disposition": "crewai_version_availability_check",
            "retained_call_path": frames,
            "selected_path_relevance": "unrelated_console_version_behavior; publicly suppressible; selected Flow/pending-resume capture recorded zero attempts",
            "architecture_blocking": False,
        })
    events_ok = len(governed) == 4 and {item["declared_phase"] for item in governed} == PHASES
    source = version_sources(repo)
    control = public_control(repo)
    versions = {name: importlib.metadata.version(name) for name in ("crewai", "crewai-core", "crewai-tools")}
    network = {
        "schema_version": 1,
        "evidence_id": args.evidence_id,
        "status": "pass",
        "supplemental_run_id": FOLLOWUP[0],
        "supplemental_manifest_sha256": FOLLOWUP[1],
        "raw_classification_preserved": "unresolved_path",
        "governed_disposition": "crewai_version_availability_check",
        "pinned_runtime": {"crewai": versions["crewai"], "crewai_core": versions["crewai-core"], "crewai_tools": versions["crewai-tools"]},
        "public_disable_control": {key: control[key] for key in ("name", "value", "enabled_control_called_version_helpers", "disabled_control_called_version_helpers", "successful_network_connections")},
        "events": governed,
    }
    predicates = architecture_predicates(fresh, supplement, events_ok, control["disabled_control_called_version_helpers"] is False)
    ready = all(predicates.values())
    candidate = {
        "orchestration": "supported CrewAI Flow",
        "memory_storage": "public set_memory_storage_factory extension",
        "workflow_persistence": "SQLiteFlowPersistence",
        "review_boundary": "HumanFeedbackPending plus from_pending()/resume(); Drupal authoritative",
        "runtime_checkpoint": "excluded; investigated optional/nonselected facility",
        "inference_controls": ["CREWAI_DISABLE_VERSION_CHECK=true", "max_retries=0", "guardrail retries zero/avoided", "correction fallback prevented or separately budgeted", "learn=False", "count every SDK/provider request"],
    }
    architecture = {
        "status": "recommendation_ready" if ready else "unresolved",
        "selected_candidate": candidate if ready else None,
        "acceptance_predicates": predicates,
        "blocking_reasons": [name for name, passed in predicates.items() if not passed],
        "adr_created": False,
        "human_architecture_approval_required": True,
        "private_instrumentation_is_architecture_support": False,
    }
    authorization = {"model_calls": 0, "provider_calls": 0, "outbound_successful_connections": 0, "drupal_mutations": 0, "source_mutations": 0, "human_review_actions": 0, "dependency_changes": 0, "recommendation_submissions": 0, "gate2c_executions": 0, "runtime_probe_runs": 0, "checkpoint_runs": 0}
    provenance = {
        "predecessor_sha": BASE,
        "branch_at_generation": subprocess.check_output(["git", "-C", str(repo), "branch", "--show-current"], text=True).strip(),
        "head_at_generation": subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip(),
        "retained_runs": {
            DIAGNOSTIC[0]: {"manifest_sha256": DIAGNOSTIC[1], "summary_sha256": DIAGNOSTIC[2], "disposition": "diagnostic_superseded_unaccepted"},
            FRESH[0]: {"manifest_sha256": FRESH[1], "summary_sha256": FRESH[2], "disposition": "completed_capture_architecture_unresolved"},
            FOLLOWUP[0]: {"manifest_sha256": FOLLOWUP[1], "summary_sha256": FOLLOWUP[2], "disposition": "completed_supplemental_capture_architecture_unresolved"},
        },
        "pinned_source": source,
        "public_control_test": control,
        "historical_interpretation": [
            "targeted capture retained the calls as unresolved_path",
            "architecture remained unresolved at capture time",
            "later pinned-source inspection established the governed disposition",
        ],
    }
    summary = {"schema_version": 1, "evidence_id": args.evidence_id, "status": "pass", "architecture_status": architecture["status"], "human_architecture_approval_required": True, "authorization": authorization, "gate2c": "deferred_unclaimed"}
    evidence.mkdir(parents=True, exist_ok=False)
    for name, value in (("architecture-disposition.json", architecture), ("authorization.json", authorization), ("network-event-disposition.json", network), ("provenance.json", provenance), ("summary.json", summary)):
        write(evidence / name, value)
    write(evidence / "evidence-manifest.json", {"schema_version": 1, "files": {name: sha(evidence / name) for name in sorted(FILES - {"evidence-manifest.json"})}})
    print(f"[PASS] governed disposition generated: {args.evidence_id} ({architecture['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
