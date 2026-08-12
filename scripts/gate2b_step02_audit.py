#!/usr/bin/env python3
"""Permanent evidence-integrity audit for Gate 2B Step 2B.02."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any

import jsonschema


BASE = "7bea4320c08670d8e9a0c71f88d10922fced8c1e"
STEP01_MANIFEST = "e43fc0ec2dded8129ee0256cb84bbd2c6775161f31cadfda350249c49f56f097"
STEP01_SUMMARY = "f32c18a3949291af15cb6915269e7ffcf78354f6285ba15bd29aceef06e7f36b"
GATE2A = "a28361c34b9d1c2089eee786324ad34cffbf54e3495f59a276c489865e5630f0"
LOCK = "855e5edff2cb86eb64ea9856d239b19010e7d3b1f80c40e370ed81d66b8e4e7c"
DIAGNOSTIC_RUN = "gate2b-step02-20260812T010531Z-00000001"
DIAGNOSTIC_MANIFEST = "6bbb9619df39cfba939f09223bde9ce160b52476598d2b847a0591c3a0edb5f5"
DIAGNOSTIC_SUMMARY = "e7c2bde43dcc30c8b912099ac2e6682684649ebbd0125a10b5fe0d3940494aee"
FRESH_RUN = "gate2b-step02-20260812T015108Z-00000001"
FRESH_MANIFEST = "8339eca113dfb1bc5cfa15d2fcbc1f95e104d908852e0656024f299f4e2c2b66"
FRESH_SUMMARY = "b03d7c8a787757b020f889faa8cb3f6393edfb0f477e2a39dd93dbbd868ef349"
EXPECTED_FILES = {
    "api-surface.json", "architecture-recommendation.json", "authorization.json",
    "evidence-manifest.json", "failure-propagation.json", "flow-persistence.json",
    "human-feedback-continuation.json", "predecessor.json", "probe-log.txt",
    "process-boundary.json", "retry-hidden-call-controls.json", "run-isolation.json",
    "runtime-checkpoint-json.json", "runtime-checkpoint-sqlite.json", "runtime-versions.json",
    "serialized-state-privacy.json", "storage-provenance.json", "summary.json",
}
REQUIRED_INSTALLED = {
    "crewai/runtime_probe/__init__.py", "crewai/runtime_probe/step2b02_probe.py",
    "crewai/runtime_probe/step2b02_worker.py",
    "docs/gates/GATE-2B-STEP02-CREWAI-RUNTIME-PERSISTENCE-AND-CONTINUATION-PROBE.md",
    "shared/schemas/gate2b-step02-runtime-probe-evidence.schema.json",
    "scripts/gate2b_step02_audit.py",
    "scripts/run-gate2b-step02-crewai-runtime-persistence-and-continuation-probe.sh",
    "crewai/runtime_probe/step2b02_followup.py",
    "shared/schemas/gate2b-step02-followup-evidence.schema.json",
    "scripts/run-gate2b-step02-hidden-network-retry-and-checkpoint-semantics-followup.sh",
}
FOLLOWUP_FILES = {
    "architecture-impact.json", "authorization.json", "checkpoint-network-provenance.json",
    "checkpoint-semantics.json", "evidence-manifest.json", "pinned-source-findings.json",
    "predecessor.json", "summary.json", "targeted-probe-log.txt",
}
FOLLOWUP_RUN = "gate2b-step02-followup-20260812T022947Z-00000001"
FOLLOWUP_MANIFEST = "6654fd33e10efdf275f0aa9ea104293ed1f7ba3092d054718a9ac0a491b07a79"
FOLLOWUP_SUMMARY = "48fa2e41db6089cf63d3f250b8a31c547c322dc8e72d8a25ae9dc1078a734a57"
DISPOSITION_FILES = {
    "architecture-disposition.json", "authorization.json", "evidence-manifest.json",
    "network-event-disposition.json", "provenance.json", "summary.json",
}
DISPOSITION_PHASES = {
    "checkpoint-json-write", "checkpoint-json-restore",
    "checkpoint-sqlite-write", "checkpoint-sqlite-restore",
}
DISPOSITION_RUN = "gate2b-step02-disposition-20260812T024610Z-00000001"
DISPOSITION_MANIFEST = "8666c77d3fc7f6a82a88adec652ea30b59198a3ce700ea14069b2ea6496c0f7d"
DISPOSITION_SUMMARY = "77d56c2a9df0c3f6c269c1c9b3a5e9a4ec816541827aa5add74b570bcf15ad45"
DISPOSITION_ARCHITECTURE = "ab23b6a78638b7c45346ba0b5419745779f37b56e0fe6c67faac8b49597040d8"
ADR_PATH = "docs/decisions/ADR-0012-crewai-flow-persistence-and-human-review-continuation.md"
CLOSURE_PATH = "shared/contracts/GATE2B-STEP02-CREWAI-ARCHITECTURE-CLOSURE.json"
CLOSURE_SCHEMA_PATH = "shared/schemas/gate2b-step02-architecture-closure.schema.json"
CLOSURE_WRAPPER_PATH = "scripts/run-gate2b-step02-crewai-architecture-closure.sh"
NEXT_PACKAGE = "gate-2b-step03-crewai-shared-operation-adapters-v1.0.0"
CHECKPOINT_CHARACTERIZATION = "terminal-output reconstruction observed; live Flow state restoration/continuation not demonstrated"
VERSION_CALL_PREFIX = [
    ("crewai/events/event_bus.py", "_call_handlers"),
    ("crewai/events/utils/handlers.py", "is_call_handler_safe"),
    ("crewai/events/event_listener.py", "on_flow_started"),
    ("crewai/events/utils/console_formatter.py", "handle_flow_started"),
    ("crewai/events/utils/console_formatter.py", "_show_version_update_message_if_needed"),
    ("crewai_core/version.py", "is_newer_version_available"),
    ("crewai_core/version.py", "check_version"),
    ("crewai_core/version.py", "get_latest_version_from_pypi"),
]
REQUIRED_INSTALLED.update({
    "scripts/gate2b_step02_version_disposition.py",
    "shared/schemas/gate2b-step02-network-disposition-evidence.schema.json",
    "scripts/run-gate2b-step02-version-check-path-classification-and-architecture-disposition.sh",
})
REQUIRED_INSTALLED.update({ADR_PATH, CLOSURE_PATH, CLOSURE_SCHEMA_PATH, CLOSURE_WRAPPER_PATH})


def fail(message: str) -> None:
    raise SystemExit(f"[ERROR] {message}")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Invalid JSON {path}: {exc}")


def classify_network_frames(frames: list[dict[str, Any]]) -> str:
    sources = [str(frame.get("source", "")) for frame in frames]
    if any(source.startswith("openai/") or "crewai/llms/" in source for source in sources):
        return "model_or_provider_path"
    if any(source.startswith("opentelemetry/") or "telemetry" in source or "tracing" in source for source in sources):
        return "telemetry_or_tracing_path"
    if any("lancedb" in source or "crewai/memory/" in source for source in sources):
        return "memory_path"
    if any("crewai/state/" in source or "checkpoint" in source for source in sources):
        return "runtime_checkpoint_path"
    return "unresolved_path"


def activation(repo: Path) -> None:
    for relative in REQUIRED_INSTALLED:
        path = repo / relative
        if not path.is_file() or path.is_symlink():
            fail(f"Missing or unsafe installed artifact: {relative}")
    schema = load(repo / "shared/schemas/gate2b-step02-runtime-probe-evidence.schema.json")
    jsonschema.Draft202012Validator.check_schema(schema)
    disposition_schema = load(repo / "shared/schemas/gate2b-step02-network-disposition-evidence.schema.json")
    jsonschema.Draft202012Validator.check_schema(disposition_schema)
    for relative in ("crewai/runtime_probe/step2b02_probe.py", "crewai/runtime_probe/step2b02_worker.py", "crewai/runtime_probe/step2b02_followup.py", "scripts/gate2b_step02_audit.py", "scripts/gate2b_step02_version_disposition.py"):
        compile((repo / relative).read_text(encoding="utf-8"), relative, "exec")
    print("[PASS] Gate 2B Step 2B.02 activation audit passed.")


def followup_acceptance_failures(documents: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    architecture = documents.get("architecture-impact.json", {})
    ready = architecture.get("status") == "recommendation_ready"
    if architecture.get("status") not in {"recommendation_ready", "unresolved"}:
        errors.append("invalid supplemental architecture status")
    semantics = documents.get("checkpoint-semantics.json", {})
    if semantics.get("status") != "corrected" or semantics.get("runtime_checkpoint_required_by_selected_architecture") is not False:
        errors.append("runtime checkpoint is not explicitly corrected and excluded from the selected path")
    if semantics.get("runtime_checkpoint_disposition") != "investigated_optional_nonselected_path":
        errors.append("runtime checkpoint optional/nonselected disposition missing")
    for backend in ("json", "sqlite"):
        finding = semantics.get("backends", {}).get(backend, {})
        if finding.get("terminal_output_reconstructed") is not True:
            errors.append(f"{backend} terminal output reconstruction missing")
        if finding.get("live_flow_state_restored") is not False or finding.get("continuation_demonstrated") is not False:
            errors.append(f"{backend} checkpoint semantics overstate live state restoration/continuation")
        if finding.get("characterization") != "terminal-output reconstruction observed; live Flow state restoration/continuation not demonstrated":
            errors.append(f"{backend} corrected checkpoint characterization missing")
    source = documents.get("pinned-source-findings.json", {})
    fallback = source.get("structured_output_fallback", {})
    if fallback.get("native_parse_can_fall_through_to_create") is not True or fallback.get("additional_provider_request_possible") is not True:
        errors.append("native structured parse fallback remains incorrectly classified")
    learning = source.get("learning_paths", {})
    if learning.get("can_add_inference") is not True or learning.get("later_requirement") != "set learn=False for the controlled review boundary":
        errors.append("learning-related inference control remains unresolved")
    network = documents.get("checkpoint-network-provenance.json", {})
    if network.get("attempts_blocked_before_connect") is not True or network.get("model_calls") != 0 or network.get("provider_calls") != 0:
        errors.append("network attempts were not safely blocked with zero calls")
    events = network.get("events", [])
    for event in events:
        destination = event.get("destination", {})
        if set(destination) != {"host", "port"} or any(token in str(destination) for token in ("@", "/", "?", "#")):
            errors.append("network destination provenance is not safely sanitized")
        for frame in event.get("frames", []):
            if set(frame) != {"source", "function", "line"} or str(frame.get("source", "")).startswith("/") or "/home/" in str(frame.get("source", "")):
                errors.append("network call-stack provenance is not safely sanitized")
        if event.get("path_classification") != classify_network_frames(event.get("frames", [])):
            errors.append("network pathway classification does not match retained call frames")
    if not ready:
        if architecture.get("selected_candidate") is not None or not architecture.get("blocking_reasons") or architecture.get("adr_created") is not False:
            errors.append("unresolved architecture has a candidate, lacks blockers, or prematurely created an ADR")
        return errors
    if network.get("selected_architecture_uses_runtime_checkpoint") is not False:
        errors.append("selected architecture unexpectedly depends on runtime checkpoint")
    if network.get("selected_path_network_attempts_in_fresh_capture") != 0:
        errors.append("selected architecture path has hidden network activity")
    if not events or any(event.get("blocked_before_connect") is not True or not event.get("frames") or event.get("path_classification") == "unresolved_path" for event in events):
        errors.append("checkpoint hidden network activity remains unexplained")
    phases = network.get("targeted_phases", {})
    expected_phases = {"checkpoint-json-write", "checkpoint-json-restore", "checkpoint-sqlite-write", "checkpoint-sqlite-restore"}
    if set(phases) != expected_phases or len(events) != 4 or {event.get("declared_phase") for event in events} != expected_phases:
        errors.append("the exact four targeted checkpoint network phases/attempts are not retained")
    if any(phase.get("completed") is not True or phase.get("timed_out") is not False for phase in phases.values()):
        errors.append("one or more targeted checkpoint phases did not complete")
    phase_pids = [phase.get("worker_pid") for phase in phases.values()]
    if len(set(phase_pids)) != 4 or any(not isinstance(value, int) for value in phase_pids):
        errors.append("targeted phases lack four separate worker processes")
    if architecture.get("selected_candidate", {}).get("runtime_checkpoint") != "excluded; optional investigated nonselected path":
        errors.append("selected candidate does not explicitly exclude runtime checkpoint")
    prerequisites = architecture.get("prerequisites", {})
    required = {
        "supported_public_extension", "no_private_instrumentation_dependency",
        "process_boundary_persistence_and_isolation", "pending_resume_same_identity",
        "pending_resume_no_prior_replay", "drupal_authority_preserved", "privacy_pass",
        "selected_path_hidden_network_clear", "checkpoint_optional_path_attributed_or_excluded",
        "checkpoint_semantics_corrected", "structured_output_fallback_corrected",
        "selected_path_retry_controls_sufficient", "learning_controls_resolved",
        "zero_authorization_counts",
    }
    if set(prerequisites) != required or not all(value is True for value in prerequisites.values()):
        errors.append("selected architecture prerequisites incomplete")
    if architecture.get("blocking_reasons") != [] or architecture.get("adr_created") is not False:
        errors.append("recommendation has blockers or prematurely created an ADR")
    return errors


def selected_path_failures(fresh: dict[str, Any], supplemental: dict[str, Any]) -> list[str]:
    """Recompute selected Flow-path support from the retained v2 capture."""
    if supplemental.get("architecture-impact.json", {}).get("status") != "recommendation_ready":
        return []
    errors: list[str] = []
    flow = fresh.get("flow-persistence.json", {})
    public = flow.get("supported_public_extension", {})
    if public.get("extension") != "set_memory_storage_factory" or public.get("private_override") is not None or public.get("candidate_viability") != "viable":
        errors.append("fresh capture does not support the selected public Flow extension")
    for name in ("write_run_a", "write_run_b"):
        phase = public.get(name, {})
        if phase.get("completed") is not True or (phase.get("result") or {}).get("blocked_provider_network_attempts") != 0:
            errors.append(f"selected public Flow phase failed or attempted network: {name}")
    isolation = fresh.get("run-isolation.json", {})
    required_isolation = {
        "independent_run_a_persisted_and_reloaded", "independent_run_b_persisted_and_reloaded",
        "unknown_identity_returns_empty", "cross_identity_returns_requested_b_not_a",
        "a_and_b_payloads_distinct",
    }
    checks = isolation.get("checks", {})
    if isolation.get("status") != "pass" or any(checks.get(name) is not True for name in required_isolation) or checks.get("state_leak_or_alias_detected") is not False:
        errors.append("fresh capture does not prove independent A/B and wrong/unknown identity isolation")
    feedback = fresh.get("human-feedback-continuation.json", {})
    if not (
        feedback.get("logical_identity_preserved") is True
        and feedback.get("separate_process_reconstruction") is True
        and feedback.get("pending_persisted") is True
        and feedback.get("emit") is None
        and feedback.get("llm") is None
        and feedback.get("learn") is False
        and str(feedback.get("drupal_authority", "")).startswith("preserved")
    ):
        errors.append("fresh capture does not support Drupal-authoritative pending/resume")
    pause = feedback.get("pause", {})
    resume = feedback.get("resume", {})
    if pause.get("worker_pid") == resume.get("worker_pid") or pause.get("completed") is not True or resume.get("completed") is not True:
        errors.append("pending and resume were not completed across separate processes")
    trace = ((resume.get("result") or {}).get("state") or {}).get("trace", [])
    if trace.count("crewai-probe-run-a:first") != 1 or trace.count("crewai-probe-run-a:second") != 1:
        errors.append("selected review continuation replayed prior model-owning units or lacks trace proof")
    for phase in (pause, resume):
        if (phase.get("result") or {}).get("blocked_provider_network_attempts") != 0:
            errors.append("selected pending/resume path attempted hidden network activity")
    privacy = fresh.get("serialized-state-privacy.json", {})
    storage = fresh.get("storage-provenance.json", {})
    if privacy.get("status") != "pass" or privacy.get("findings") != []:
        errors.append("fresh selected-path privacy evidence failed")
    if storage.get("status") != "pass" or storage.get("ownership") != "crewai" or storage.get("shared_storage_used") is not False:
        errors.append("fresh selected-path storage provenance failed")
    retry = fresh.get("retry-hidden-call-controls.json", {})
    transport = retry.get("transport", {})
    validation = retry.get("validation", {})
    if not (
        retry.get("sufficient_for_later_one_call_design") is True
        and transport.get("source_resolution_sufficient") is True
        and transport.get("openai_sdk_zero_disables_retries") is True
        and transport.get("retry_can_occur_below_framework_counter") is True
        and validation.get("source_resolution_sufficient") is True
        and validation.get("structured_output_correction_can_call_llm") is True
        and validation.get("guardrail_failure_reinvokes_agent") is True
    ):
        errors.append("fresh selected-path retry controls are insufficient for later one-call design")
    return errors


def verify_followup_set(evidence: Path) -> dict[str, Any]:
    actual = {path.name for path in evidence.iterdir() if path.is_file()}
    nonfiles = [path.name for path in evidence.iterdir() if not path.is_file()]
    if actual != FOLLOWUP_FILES or nonfiles:
        fail(f"Exact follow-up evidence set mismatch: files={sorted(actual)}, nonfiles={nonfiles}")
    manifest = load(evidence / "evidence-manifest.json")
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        fail("Invalid follow-up manifest")
    entries = manifest.get("files")
    if not isinstance(entries, dict) or set(entries) != FOLLOWUP_FILES - {"evidence-manifest.json"}:
        fail("Follow-up manifest does not hash the exact other eight files")
    for name, expected in entries.items():
        if not isinstance(expected, str) or digest(evidence / name) != expected:
            fail(f"Follow-up evidence hash mismatch: {name}")
    return {name: load(evidence / name) for name in FOLLOWUP_FILES if name.endswith(".json")}


def permanent_followup(repo: Path, evidence: Path) -> None:
    activation(repo)
    expected_root = (repo / "evidence/gates/gate-2b/runtime-probe-followup").resolve()
    resolved = evidence.resolve()
    if not resolved.is_dir() or resolved.is_symlink() or resolved.parent != expected_root:
        fail("Follow-up evidence is outside the exact supplemental root")
    if not re.fullmatch(r"gate2b-step02-followup-[0-9]{8}T[0-9]{6}Z-[0-9]{8}", resolved.name):
        fail("Invalid follow-up evidence ID")
    documents = verify_followup_set(resolved)
    summary = documents["summary.json"]
    schema = load(repo / "shared/schemas/gate2b-step02-followup-evidence.schema.json")
    jsonschema.validate(summary, schema)
    if summary.get("evidence_id") != resolved.name or summary.get("status") != "pass":
        fail("Follow-up summary identity/status mismatch")
    if summary.get("architecture_status") != documents["architecture-impact.json"].get("status"):
        fail("Follow-up summary/architecture status mismatch")
    auth = documents["authorization.json"]
    if auth != summary.get("authorization") or any(value != 0 for value in auth.values()):
        fail("Follow-up authorization counts are nonzero or inconsistent")
    if summary.get("gate2c") != "deferred_unclaimed":
        fail("Gate 2C boundary mismatch")
    predecessor = documents["predecessor.json"]
    expected_runs = {
        DIAGNOSTIC_RUN: {"manifest_sha256": DIAGNOSTIC_MANIFEST, "summary_sha256": DIAGNOSTIC_SUMMARY, "disposition": "diagnostic_superseded_unaccepted"},
        FRESH_RUN: {"manifest_sha256": FRESH_MANIFEST, "summary_sha256": FRESH_SUMMARY, "disposition": "completed_capture_architecture_unresolved"},
    }
    if predecessor.get("predecessor_sha") != BASE or predecessor.get("retained_runs") != expected_runs:
        fail("Follow-up predecessor provenance mismatch")
    root = repo / "evidence/gates/gate-2b/runtime-probe"
    for run, values in expected_runs.items():
        if digest(root / run / "evidence-manifest.json") != values["manifest_sha256"] or digest(root / run / "summary.json") != values["summary_sha256"]:
            fail(f"Retained Step 2B.02 evidence changed: {run}")
    fresh_documents = verify_evidence_set(root / FRESH_RUN)
    errors = followup_acceptance_failures(documents)
    errors.extend(selected_path_failures(fresh_documents, documents))
    sources = documents["pinned-source-findings.json"]
    completion = repo / sources.get("structured_output_fallback", {}).get("source", "missing")
    learning = sources.get("learning_paths", {})
    definition = repo / learning.get("definition_source", "missing")
    invocation = repo / learning.get("invocation_source", "missing")
    if not completion.is_file() or digest(completion) != sources.get("structured_output_fallback", {}).get("sha256"):
        errors.append("pinned structured-output source provenance mismatch")
    if not definition.is_file() or digest(definition) != learning.get("definition_sha256"):
        errors.append("pinned learning-definition source provenance mismatch")
    if not invocation.is_file() or digest(invocation) != learning.get("invocation_sha256"):
        errors.append("pinned learning-invocation source provenance mismatch")
    if errors:
        fail("Unsupported follow-up architecture recommendation: " + "; ".join(errors))
    raw = b"\n".join((resolved / name).read_bytes() for name in sorted(FOLLOWUP_FILES))
    for pattern in (rb"sk-[A-Za-z0-9_-]{12,}", rb"data:image/[^;]+;base64,", rb"authorization\s*:", rb"hidden reasoning", rb"chain[ _-]?of[ _-]?thought"):
        if re.search(pattern, raw, re.I):
            fail(f"Follow-up secret/privacy scan matched prohibited pattern: {pattern!r}")
    print(f"[PASS] Gate 2B Step 2B.02 targeted follow-up permanent audit passed: {resolved.name}")


def verify_public_version_control(repo: Path) -> bool:
    """Exercise the pinned public guard without allowing a network connection."""
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
    with tempfile.TemporaryDirectory(prefix="gate2b-version-audit-") as temporary:
        env.update({"XDG_CACHE_HOME": temporary, "XDG_CONFIG_HOME": temporary, "XDG_DATA_HOME": temporary, "NO_PROXY": "*"})
        result = subprocess.run([str(repo / "crewai/.venv/bin/python"), "-c", code], cwd=repo, env=env, text=True, capture_output=True, timeout=15, check=False)
    try:
        observed = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        return False
    return result.returncode == 0 and observed.get("enabled_blocked_attempts", 0) >= 1 and observed.get("disabled_blocked_attempts") == 0


def recompute_disposition_predicates(fresh: dict[str, Any], followup: dict[str, Any], events_ok: bool, control_ok: bool) -> dict[str, bool]:
    """Independently recompute every material selected-architecture predicate."""
    flow = fresh["flow-persistence.json"]
    default = flow["default_unmodified"]
    public = flow["supported_public_extension"]
    isolation = fresh["run-isolation.json"]
    feedback = fresh["human-feedback-continuation.json"]
    privacy = fresh["serialized-state-privacy.json"]
    storage = fresh["storage-provenance.json"]
    retry = fresh["retry-hidden-call-controls.json"]
    semantics = followup["checkpoint-semantics.json"]
    source = followup["pinned-source-findings.json"]
    trace = feedback["resume"]["result"]["state"]["trace"]
    checks = isolation["checks"]
    required_isolation = ["independent_run_a_persisted_and_reloaded", "independent_run_b_persisted_and_reloaded", "unknown_identity_returns_empty", "cross_identity_returns_requested_b_not_a", "a_and_b_payloads_distinct"]
    selected_phases = [public["write_run_a"], public["write_run_b"], feedback["pause"], feedback["resume"]]
    transport = retry["transport"]
    validation = retry["validation"]
    corrected = "terminal-output reconstruction observed; live Flow state restoration/continuation not demonstrated"
    auth_reports = [fresh["authorization.json"], followup["authorization.json"]]
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
        "all_authorization_counts_zero": all(all(value == 0 for value in report.values()) for report in auth_reports),
        "gate2c_deferred_unexecuted": fresh["failure-propagation.json"].get("gate2c_seam_exercised") is False and fresh["summary.json"].get("gate2c") == "deferred_unclaimed" and followup["summary.json"].get("gate2c") == "deferred_unclaimed",
        "all_required_evidence_and_hashes_intact": True,
    }


def disposition_acceptance_failures(repo: Path, documents: dict[str, Any], fresh: dict[str, Any], followup: dict[str, Any], *, live_control: bool = True) -> list[str]:
    errors: list[str] = []
    network = documents.get("network-event-disposition.json", {})
    provenance = documents.get("provenance.json", {})
    architecture = documents.get("architecture-disposition.json", {})
    immutable_events = followup["checkpoint-network-provenance.json"].get("events", [])
    governed_events = network.get("events", [])
    immutable_by_phase = {event.get("declared_phase"): event for event in immutable_events}
    events_ok = (
        len(immutable_events) == 4
        and len(governed_events) == 4
        and set(immutable_by_phase) == DISPOSITION_PHASES
        and {event.get("declared_phase") for event in governed_events} == DISPOSITION_PHASES
    )
    for governed in governed_events:
        raw = immutable_by_phase.get(governed.get("declared_phase"), {})
        prefix = [(frame.get("source"), frame.get("function")) for frame in raw.get("frames", [])[: len(VERSION_CALL_PREFIX)]]
        if raw.get("path_classification") != "unresolved_path" or governed.get("original_classification") != "unresolved_path":
            errors.append("raw unresolved_path classification was not preserved")
            events_ok = False
        if prefix != VERSION_CALL_PREFIX or governed.get("retained_call_path") != raw.get("frames") or governed.get("event_sha256") != canonical_digest(raw):
            errors.append("governed disposition is not bound to the immutable call stack")
            events_ok = False
        if governed.get("governed_disposition") != "crewai_version_availability_check" or governed.get("architecture_blocking") is not False:
            errors.append("network event has a false governed/model/provider classification")
            events_ok = False
    if network.get("raw_classification_preserved") != "unresolved_path" or network.get("governed_disposition") != "crewai_version_availability_check":
        errors.append("governed network disposition header mismatch")
        events_ok = False
    if network.get("supplemental_run_id") != FOLLOWUP_RUN or network.get("supplemental_manifest_sha256") != FOLLOWUP_MANIFEST:
        errors.append("governed disposition is not bound to the supplemental evidence")
        events_ok = False
    pinned = provenance.get("pinned_source", {})
    console_info = pinned.get("console_formatter", {})
    version_info = pinned.get("version_module", {})
    console = repo / console_info.get("path", "missing")
    version = repo / version_info.get("path", "missing")
    source_ok = console.is_file() and version.is_file() and digest(console) == console_info.get("sha256") and digest(version) == version_info.get("sha256")
    if source_ok:
        console_text = console.read_text(encoding="utf-8")
        version_text = version.read_text(encoding="utf-8")
        source_ok = all(token in console_text for token in ("CREWAI_DISABLE_VERSION_CHECK", "_show_version_update_message_if_needed", "is_newer_version_available()")) and all(token in version_text for token in ("def get_latest_version_from_pypi", "request.urlopen(", "def check_version", "def is_newer_version_available")) and console_text.index("CREWAI_DISABLE_VERSION_CHECK") < console_text.index("is_newer_version_available()")
    if not source_ok or not all(pinned.get(name) is True for name in ("not_model_or_provider", "not_checkpoint_persistence", "not_memory_initialization", "not_telemetry_export")):
        errors.append("pinned-source version-check interpretation is missing or false")
        events_ok = False
    control_doc = provenance.get("public_control_test", {})
    network_control = network.get("public_disable_control", {})
    control_fields_ok = (
        control_doc.get("name") == "CREWAI_DISABLE_VERSION_CHECK"
        and control_doc.get("value") == "true"
        and control_doc.get("enabled_control_called_version_helpers") is True
        and control_doc.get("disabled_control_called_version_helpers") is False
        and control_doc.get("successful_network_connections") == 0
        and all(network_control.get(key) == control_doc.get(key) for key in ("name", "value", "enabled_control_called_version_helpers", "disabled_control_called_version_helpers", "successful_network_connections"))
    )
    control_ok = control_fields_ok and (verify_public_version_control(repo) if live_control else True)
    if not control_ok:
        errors.append("public version-check disable-control proof is absent or failed")
    versions = network.get("pinned_runtime", {})
    if versions != {"crewai": "1.15.10", "crewai_core": "1.15.10", "crewai_tools": "1.15.10"}:
        errors.append("pinned runtime versions mismatch")
    try:
        live_versions = {"crewai": importlib.metadata.version("crewai"), "crewai_core": importlib.metadata.version("crewai-core"), "crewai_tools": importlib.metadata.version("crewai-tools")}
    except importlib.metadata.PackageNotFoundError:
        live_versions = {}
    if live_versions != versions:
        errors.append("live pinned runtime metadata mismatch")
    retained_runs = provenance.get("retained_runs", {})
    expected_runs = {
        DIAGNOSTIC_RUN: {"manifest_sha256": DIAGNOSTIC_MANIFEST, "summary_sha256": DIAGNOSTIC_SUMMARY, "disposition": "diagnostic_superseded_unaccepted"},
        FRESH_RUN: {"manifest_sha256": FRESH_MANIFEST, "summary_sha256": FRESH_SUMMARY, "disposition": "completed_capture_architecture_unresolved"},
        FOLLOWUP_RUN: {"manifest_sha256": FOLLOWUP_MANIFEST, "summary_sha256": FOLLOWUP_SUMMARY, "disposition": "completed_supplemental_capture_architecture_unresolved"},
    }
    if provenance.get("predecessor_sha") != BASE or retained_runs != expected_runs:
        errors.append("retained evidence provenance/disposition mismatch")
    predicates = recompute_disposition_predicates(fresh, followup, events_ok, control_ok)
    recorded = architecture.get("acceptance_predicates")
    ready = all(predicates.values())
    if recorded != predicates:
        errors.append("architecture acceptance predicates are not independently reproducible")
    if architecture.get("status") != ("recommendation_ready" if ready else "unresolved"):
        errors.append("architecture status does not match recomputed predicates")
    if architecture.get("blocking_reasons") != [name for name, passed in predicates.items() if not passed]:
        errors.append("architecture blocking reasons mismatch")
    candidate = architecture.get("selected_candidate")
    if ready:
        if not isinstance(candidate, dict) or candidate.get("runtime_checkpoint") != "excluded; investigated optional/nonselected facility":
            errors.append("recommendation_ready lacks the supported selected candidate or checkpoint exclusion")
        if architecture.get("private_instrumentation_is_architecture_support") is not False:
            errors.append("selected architecture relies on private instrumentation")
    elif candidate is not None:
        errors.append("unresolved architecture has a selected candidate")
    if architecture.get("adr_created") is not False or architecture.get("human_architecture_approval_required") is not True:
        errors.append("architecture was prematurely accepted or no longer requires human approval")
    auth = documents.get("authorization.json", {})
    summary = documents.get("summary.json", {})
    if not auth or any(value != 0 for value in auth.values()) or summary.get("authorization") != auth:
        errors.append("authorization counts are nonzero or inconsistent")
    if summary.get("gate2c") != "deferred_unclaimed" or summary.get("architecture_status") != architecture.get("status"):
        errors.append("summary lifecycle/architecture status mismatch")
    return errors


def verify_disposition_set(evidence: Path) -> dict[str, Any]:
    actual = {path.name for path in evidence.iterdir() if path.is_file()}
    nonfiles = [path.name for path in evidence.iterdir() if not path.is_file()]
    if actual != DISPOSITION_FILES or nonfiles:
        fail(f"Exact disposition evidence set mismatch: files={sorted(actual)}, nonfiles={nonfiles}")
    manifest = load(evidence / "evidence-manifest.json")
    if manifest.get("schema_version") != 1 or set(manifest.get("files", {})) != DISPOSITION_FILES - {"evidence-manifest.json"}:
        fail("Disposition manifest does not hash the exact other five files")
    for name, expected in manifest["files"].items():
        if not isinstance(expected, str) or digest(evidence / name) != expected:
            fail(f"Disposition evidence hash mismatch: {name}")
    return {name: load(evidence / name) for name in DISPOSITION_FILES if name.endswith(".json")}


def permanent_disposition(repo: Path, evidence: Path) -> None:
    activation(repo)
    expected_root = (repo / "evidence/gates/gate-2b/runtime-probe-disposition").resolve()
    resolved = evidence.resolve()
    if not resolved.is_dir() or resolved.is_symlink() or resolved.parent != expected_root:
        fail("Disposition evidence is outside the exact governed root")
    if not re.fullmatch(r"gate2b-step02-disposition-[0-9]{8}T[0-9]{6}Z-[0-9]{8}", resolved.name):
        fail("Invalid disposition evidence ID")
    documents = verify_disposition_set(resolved)
    schema = load(repo / "shared/schemas/gate2b-step02-network-disposition-evidence.schema.json")
    jsonschema.validate(documents["network-event-disposition.json"], schema)
    runtime_root = repo / "evidence/gates/gate-2b/runtime-probe"
    followup_root = repo / "evidence/gates/gate-2b/runtime-probe-followup"
    for path, manifest, summary in (
        (runtime_root / DIAGNOSTIC_RUN, DIAGNOSTIC_MANIFEST, DIAGNOSTIC_SUMMARY),
        (runtime_root / FRESH_RUN, FRESH_MANIFEST, FRESH_SUMMARY),
        (followup_root / FOLLOWUP_RUN, FOLLOWUP_MANIFEST, FOLLOWUP_SUMMARY),
    ):
        if digest(path / "evidence-manifest.json") != manifest or digest(path / "summary.json") != summary:
            fail(f"Retained evidence changed: {path.name}")
    fresh = verify_evidence_set(runtime_root / FRESH_RUN)
    followup = verify_followup_set(followup_root / FOLLOWUP_RUN)
    errors = disposition_acceptance_failures(repo, documents, fresh, followup)
    if errors:
        fail("Unsupported governed architecture disposition: " + "; ".join(errors))
    raw = b"\n".join((resolved / name).read_bytes() for name in sorted(DISPOSITION_FILES))
    for pattern in (rb"sk-[A-Za-z0-9_-]{12,}", rb"data:image/[^;]+;base64,", rb"authorization\s*:", rb"hidden reasoning", rb"chain[ _-]?of[ _-]?thought"):
        if re.search(pattern, raw, re.I):
            fail(f"Disposition secret/privacy scan matched prohibited pattern: {pattern!r}")
    print(f"[PASS] Gate 2B Step 2B.02 governed disposition permanent audit passed: {resolved.name}")


def closure_acceptance_failures(closure: dict[str, Any], adr_text: str, lifecycle_documents: dict[str, str]) -> list[str]:
    """Independently verify the human decision and Step 2B.02 closure semantics."""
    errors: list[str] = []
    if closure.get("schema_version") != 1 or closure.get("step") != "2B.02" or closure.get("status") != "complete":
        errors.append("Step 2B.02 closure identity/status mismatch")
    if closure.get("decision_date") != "2026-08-11":
        errors.append("human decision date mismatch")
    machine = closure.get("machine_recommendation", {})
    expected_machine = {
        "status": "recommendation_ready",
        "evidence_id": DISPOSITION_RUN,
        "manifest_sha256": DISPOSITION_MANIFEST,
        "summary_sha256": DISPOSITION_SUMMARY,
        "architecture_disposition_sha256": DISPOSITION_ARCHITECTURE,
        "permanent_predicates_passed": 25,
    }
    if machine != expected_machine:
        errors.append("machine recommendation provenance mismatch")
    human = closure.get("human_decision", {})
    expected_candidate = [
        "supported CrewAI Flow",
        "public set_memory_storage_factory(...) extension",
        "SQLiteFlowPersistence",
        "HumanFeedbackPending",
        "from_pending()/resume()",
        "Drupal-authoritative human review",
        "learn=False",
        "CREWAI_DISABLE_VERSION_CHECK=true",
        "later transport retries configured to zero",
        "guardrail retries zero or avoided",
        "invalid structured output fails closed",
        "structured-output correction/fallback prevented or separately budgeted",
        "every SDK/provider request counted",
    ]
    if human.get("status") != "approved" or human.get("authority") != "human approval authority":
        errors.append("human architecture approval provenance missing")
    if human.get("approved_candidate") != expected_candidate:
        errors.append("human-approved architecture candidate mismatch")
    if human.get("checkpoint_characterization") != CHECKPOINT_CHARACTERIZATION:
        errors.append("checkpoint characterization is missing or overstrong")
    if human.get("nonselected") != ["runtime CheckpointConfig", "private _skip_auto_memory"]:
        errors.append("nonselected checkpoint/private-instrumentation paths mismatch")
    adr = closure.get("adr", {})
    if adr.get("path") != ADR_PATH or adr.get("status") != "Accepted":
        errors.append("accepted ADR path/status mismatch")
    if adr.get("sha256") != hashlib.sha256(adr_text.encode("utf-8")).hexdigest():
        errors.append("ADR hash mismatch")
    expected_evidence = [
        {
            "evidence_id": DIAGNOSTIC_RUN,
            "path": f"evidence/gates/gate-2b/runtime-probe/{DIAGNOSTIC_RUN}",
            "manifest_sha256": DIAGNOSTIC_MANIFEST,
            "summary_sha256": DIAGNOSTIC_SUMMARY,
            "disposition": "diagnostic; superseded/unaccepted for architecture selection",
        },
        {
            "evidence_id": FRESH_RUN,
            "path": f"evidence/gates/gate-2b/runtime-probe/{FRESH_RUN}",
            "manifest_sha256": FRESH_MANIFEST,
            "summary_sha256": FRESH_SUMMARY,
            "disposition": "completed runtime capture; initially architecture unresolved",
        },
        {
            "evidence_id": FOLLOWUP_RUN,
            "path": f"evidence/gates/gate-2b/runtime-probe-followup/{FOLLOWUP_RUN}",
            "manifest_sha256": FOLLOWUP_MANIFEST,
            "summary_sha256": FOLLOWUP_SUMMARY,
            "disposition": "completed supplemental capture; source attribution initially unresolved",
        },
        {
            "evidence_id": DISPOSITION_RUN,
            "path": f"evidence/gates/gate-2b/runtime-probe-disposition/{DISPOSITION_RUN}",
            "manifest_sha256": DISPOSITION_MANIFEST,
            "summary_sha256": DISPOSITION_SUMMARY,
            "architecture_disposition_sha256": DISPOSITION_ARCHITECTURE,
            "disposition": "machine recommendation_ready; human architecture approval governed separately",
        },
    ]
    if closure.get("retained_evidence") != expected_evidence:
        errors.append("four-boundary retained evidence provenance mismatch")
    authorization = closure.get("authorization", {})
    expected_authorization = {
        "model_calls", "provider_calls", "outbound_successful_connections", "drupal_mutations",
        "source_mutations", "human_review_actions", "dependency_changes",
        "recommendation_submissions", "gate2c_executions", "runtime_probe_reruns",
        "checkpoint_reruns", "new_experiment_evidence_runs",
    }
    if set(authorization) != expected_authorization or any(value != 0 for value in authorization.values()):
        errors.append("closure authorization counts are missing or nonzero")
    if closure.get("gate2c") != "deferred_unclaimed":
        errors.append("Gate 2C was claimed or executed")
    if closure.get("next_boundary") != {"step": "2B.03", "package": NEXT_PACKAGE, "status": "named_not_begun"}:
        errors.append("Step 2B.03 is not correctly named and locked")
    required_adr_tokens = (
        "# ADR-0012: CrewAI Flow persistence and human-review continuation",
        "**Status:** Accepted",
        "**Machine recommendation:** `recommendation_ready`",
        "supported CrewAI `Flow`",
        "`set_memory_storage_factory(...)`",
        "`SQLiteFlowPersistence`",
        "`HumanFeedbackPending`",
        "`from_pending()` / `resume()`",
        "Drupal `alt_text_suggestion` review by `editor_dana`",
        "`CREWAI_DISABLE_VERSION_CHECK=true`",
        "Runtime `CheckpointConfig` is excluded",
        "Private `_skip_auto_memory` instrumentation",
        CHECKPOINT_CHARACTERIZATION,
        "native OpenAI structured parsing can fall through",
        "no production-readiness",
        "Gate 2C failure/recovery evidence",
    )
    for token in required_adr_tokens:
        if token not in adr_text:
            errors.append(f"ADR required decision/nonclaim token missing: {token}")
    if not lifecycle_documents:
        errors.append("lifecycle documents were not supplied")
    for name, text in lifecycle_documents.items():
        if "Step 2B.02" not in text or "complete" not in text or NEXT_PACKAGE not in text:
            errors.append(f"lifecycle document does not close 2B.02 and lock/name 2B.03: {name}")
        if "Step 2B.02 remains open" in text or "architecture remains pending human approval" in text:
            errors.append(f"lifecycle document retains a stale current Step 2B.02 status: {name}")
        if "Gate 2C" not in text or "deferred" not in text or "unclaimed" not in text:
            errors.append(f"lifecycle document does not preserve Gate 2C status: {name}")
    return errors


def permanent_closure(repo: Path) -> None:
    """Permanent Step 2B.02 architecture/ADR closure audit."""
    activation(repo)
    disposition = repo / f"evidence/gates/gate-2b/runtime-probe-disposition/{DISPOSITION_RUN}"
    permanent_disposition(repo, disposition)
    closure_path = repo / CLOSURE_PATH
    schema_path = repo / CLOSURE_SCHEMA_PATH
    adr_path = repo / ADR_PATH
    closure = load(closure_path)
    schema = load(schema_path)
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(closure, schema)
    adr_text = adr_path.read_text(encoding="utf-8")
    lifecycle_paths = ("AGENTS.md", "PLAN.md", "README.md", "docs/CURRENT-STATUS.md", "docs/CODEX-GATE-2B-RUNBOOK.md")
    lifecycle = {name: (repo / name).read_text(encoding="utf-8") for name in lifecycle_paths}
    errors = closure_acceptance_failures(closure, adr_text, lifecycle)
    if errors:
        fail("Unsupported Step 2B.02 architecture closure: " + "; ".join(errors))
    for item in closure["retained_evidence"]:
        root = repo / item["path"]
        if digest(root / "evidence-manifest.json") != item["manifest_sha256"] or digest(root / "summary.json") != item["summary_sha256"]:
            fail(f"Retained closure evidence changed: {item['evidence_id']}")
        if "architecture_disposition_sha256" in item and digest(root / "architecture-disposition.json") != item["architecture_disposition_sha256"]:
            fail("Governed architecture-disposition evidence changed")
    raw = closure_path.read_bytes() + b"\n" + adr_path.read_bytes()
    for pattern in (rb"sk-[A-Za-z0-9_-]{12,}", rb"data:image/[^;]+;base64,", rb"authorization\s*:", rb"hidden reasoning", rb"chain[ _-]?of[ _-]?thought"):
        if re.search(pattern, raw, re.I):
            fail(f"Closure secret/privacy scan matched prohibited pattern: {pattern!r}")
    print("[PASS] Gate 2B Step 2B.02 permanent ADR/architecture closure audit passed.")


def acceptance_failures(documents: dict[str, Any]) -> list[str]:
    """Recompute recommendation prerequisites; runner status is never self-authenticating."""
    errors: list[str] = []
    architecture = documents.get("architecture-recommendation.json", {})
    if architecture.get("status") != "recommendation_ready":
        return errors
    flow = documents.get("flow-persistence.json", {})
    default = flow.get("default_unmodified", {})
    public = flow.get("supported_public_extension", {})
    isolated = flow.get("probe_isolated", {})
    if not default or default.get("private_override") is not None:
        errors.append("missing valid default/unmodified Flow classification")
    default_phase = default.get("phase", {})
    if default_phase.get("classification") not in {"completed", "failed", "timeout"}:
        errors.append("default Flow phase was not truthfully characterized")
    if public.get("extension") != "set_memory_storage_factory" or public.get("private_override") is not None:
        errors.append("selected candidate is not supported public configuration/extension evidence")
    if not all(public.get(name, {}).get("completed") is True for name in ("write_run_a", "write_run_b")):
        errors.append("selected candidate lacks independent supported run A/run B writes")
    if isolated.get("override") != "_skip_auto_memory = True" or "diagnostic only" not in isolated.get("architecture_limitation", ""):
        errors.append("private instrumentation is missing or mislabeled")
    if architecture.get("private_instrumentation_is_sole_support") is not False:
        errors.append("recommendation relies solely on private instrumentation")

    isolation = documents.get("run-isolation.json", {})
    checks = isolation.get("checks", {})
    for name in (
        "independent_run_a_persisted_and_reloaded", "independent_run_b_persisted_and_reloaded",
        "unknown_identity_returns_empty", "cross_identity_returns_requested_b_not_a", "a_and_b_payloads_distinct",
    ):
        if checks.get(name) is not True:
            errors.append(f"run-isolation predicate failed: {name}")
    if checks.get("state_leak_or_alias_detected") is not False or isolation.get("status") != "pass":
        errors.append("run isolation leaked or aliased state")
    for section in ("run_a", "run_b", "unknown_identity", "wrong_cross_identity"):
        if section not in isolation:
            errors.append(f"missing isolation control: {section}")

    retry = documents.get("retry-hidden-call-controls.json", {})
    transport = retry.get("transport", {})
    validation = retry.get("validation", {})
    if transport.get("source_resolution_sufficient") is not True or transport.get("openai_sdk_zero_disables_retries") is not True:
        errors.append("transport retry finding remains unresolved")
    if validation.get("source_resolution_sufficient") is not True:
        errors.append("validation/task/guardrail retry finding remains unresolved")
    if retry.get("sufficient_for_later_one_call_design") is not True:
        errors.append("one-call control strategy is not sufficiently resolved")

    process = documents.get("process-boundary.json", {})
    for name in ("all_phase_pids_distinct", "all_process_groups_owned", "all_workers_reaped"):
        if process.get(name) is not True:
            errors.append(f"process-boundary predicate failed: {name}")
    allowed_phase_classes = {"default-unmodified", "supported-public-extension", "probe-isolated", "provider-only"}
    phases = process.get("phases", [])
    if not phases or any(item.get("execution_classification") not in allowed_phase_classes for item in phases):
        errors.append("one or more phases lack machine-readable execution classification")
    if not any(item.get("execution_classification") == "default-unmodified" for item in phases):
        errors.append("process evidence lacks the default/unmodified Flow phase")
    privacy = documents.get("serialized-state-privacy.json", {})
    provenance = documents.get("storage-provenance.json", {})
    if privacy.get("status") != "pass" or privacy.get("findings") != []:
        errors.append("privacy inspection failed")
    if provenance.get("status") != "pass" or provenance.get("ownership") != "crewai" or provenance.get("shared_storage_used") is not False:
        errors.append("storage provenance failed")
    feedback = documents.get("human-feedback-continuation.json", {})
    if feedback.get("emit") is not None or feedback.get("llm") is not None or feedback.get("drupal_authority", "").startswith("preserved") is not True:
        errors.append("human-feedback/Drupal authority implications incomplete")
    prerequisites = architecture.get("prerequisites", {})
    if not isinstance(prerequisites, dict) or not prerequisites or not all(value is True for value in prerequisites.values()):
        errors.append("machine recommendation prerequisites are incomplete")
    if architecture.get("blocking_reasons") != []:
        errors.append("recommendation_ready contains blocking reasons")
    return errors


def verify_evidence_set(evidence: Path) -> dict[str, Any]:
    actual = {path.name for path in evidence.iterdir() if path.is_file()}
    nonfiles = [path.name for path in evidence.iterdir() if not path.is_file()]
    if actual != EXPECTED_FILES or nonfiles:
        fail(f"Exact evidence set mismatch: files={sorted(actual)}, nonfiles={nonfiles}")
    manifest = load(evidence / "evidence-manifest.json")
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 2:
        fail("Fresh evidence manifest must use schema version 2")
    entries = manifest.get("files")
    if not isinstance(entries, dict) or set(entries) != EXPECTED_FILES - {"evidence-manifest.json"}:
        fail("Evidence manifest does not hash the exact other 17 files")
    for name, expected in entries.items():
        if not isinstance(expected, str) or digest(evidence / name) != expected:
            fail(f"Evidence hash mismatch: {name}")
    return {name: load(evidence / name) for name in EXPECTED_FILES if name.endswith(".json")}


def permanent(repo: Path, evidence: Path) -> None:
    activation(repo)
    expected_root = (repo / "evidence/gates/gate-2b/runtime-probe").resolve()
    resolved = evidence.resolve()
    if not resolved.is_dir() or resolved.is_symlink() or resolved.parent != expected_root:
        fail("Evidence path is outside the exact Step 2B.02 root")
    if resolved.name == DIAGNOSTIC_RUN:
        fail("The retained first run is diagnostic/unaccepted and cannot satisfy the superseding permanent audit")
    if not re.fullmatch(r"gate2b-step02-[0-9]{8}T[0-9]{6}Z-[0-9]{8}", resolved.name):
        fail("Invalid evidence ID")
    documents = verify_evidence_set(resolved)
    summary = documents["summary.json"]
    schema = load(repo / "shared/schemas/gate2b-step02-runtime-probe-evidence.schema.json")
    jsonschema.validate(summary, schema)
    if summary.get("evidence_id") != resolved.name or summary.get("status") != "pass" or summary.get("evidence_disposition") != "superseding_candidate":
        fail("Summary identity/status/disposition mismatch")
    auth = documents["authorization.json"]
    if auth != summary.get("authorization") or any(value != 0 for value in auth.values()):
        fail("Nonzero or inconsistent authorization count")
    if documents["failure-propagation.json"].get("gate2c_seam_exercised") is not False or summary.get("gate2c") != "deferred_unclaimed":
        fail("Gate 2C boundary mismatch")
    failures = acceptance_failures(documents)
    if failures:
        fail("Unsupported architecture recommendation: " + "; ".join(failures))

    predecessor = documents["predecessor.json"]
    if predecessor.get("predecessor_sha") != BASE:
        fail("Predecessor provenance mismatch")
    diagnostic = predecessor.get("diagnostic_predecessor", {})
    if diagnostic != {"evidence_id": DIAGNOSTIC_RUN, "disposition": "retained_diagnostic_unaccepted", "manifest_sha256": DIAGNOSTIC_MANIFEST, "summary_sha256": DIAGNOSTIC_SUMMARY}:
        fail("Diagnostic-run provenance/disposition mismatch")
    retained = repo / "evidence/gates/gate-2b/runtime-probe" / DIAGNOSTIC_RUN
    if digest(retained / "evidence-manifest.json") != DIAGNOSTIC_MANIFEST or digest(retained / "summary.json") != DIAGNOSTIC_SUMMARY:
        fail("Retained diagnostic evidence changed")
    versions = documents["runtime-versions.json"]
    if (versions.get("python"), versions.get("crewai"), versions.get("crewai_tools")) != ("3.12.13", "1.15.10", "1.15.10"):
        fail("Pinned runtime version mismatch")
    if versions.get("uv_lock_sha256") != LOCK or versions.get("dependency_changes") != 0:
        fail("Dependency lock provenance mismatch")
    if digest(repo / "crewai/uv.lock") != LOCK or digest(repo / "shared/contracts/GATE2A-LANGGRAPH-FREEZE.json") != GATE2A:
        fail("Live frozen dependency/predecessor digest changed")
    step01 = repo / "evidence/gates/gate-2b/contract/gate2b-step01-20260811T231020Z-00000002"
    if digest(step01 / "package-files-sha256.txt") != STEP01_MANIFEST or digest(step01 / "summary.json") != STEP01_SUMMARY:
        fail("Step 2B.01 accepted evidence changed")
    raw = b"\n".join((resolved / name).read_bytes() for name in sorted(EXPECTED_FILES))
    for pattern in (rb"sk-[A-Za-z0-9_-]{12,}", rb"data:image/[^;]+;base64,", rb"authorization\s*:", rb"hidden reasoning", rb"chain[ _-]?of[ _-]?thought"):
        if re.search(pattern, raw, re.I):
            fail(f"Evidence secret/privacy scan matched prohibited pattern: {pattern!r}")
    print(f"[PASS] Gate 2B Step 2B.02 permanent evidence audit passed: {resolved.name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--activation", action="store_true")
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--supplemental", type=Path)
    parser.add_argument("--disposition", type=Path)
    parser.add_argument("--closure", action="store_true")
    args = parser.parse_args()
    repo = args.repo.resolve()
    top = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "--show-toplevel"], text=True).strip()
    if top != str(repo):
        fail("Repository path is not the Git root")
    if args.activation:
        activation(repo)
    elif args.closure:
        permanent_closure(repo)
    elif args.disposition is not None:
        permanent_disposition(repo, args.disposition)
    elif args.supplemental is not None:
        permanent_followup(repo, args.supplemental)
    elif args.evidence is None:
        fail("--evidence is required for permanent audit")
    else:
        permanent(repo, args.evidence)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
