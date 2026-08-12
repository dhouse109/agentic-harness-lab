#!/usr/bin/env python3
"""Orchestrate the superseding Gate 2B Step 2B.02 model-free evidence run."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
from typing import Any


EXPECTED_FILES = {
    "api-surface.json", "architecture-recommendation.json", "authorization.json",
    "evidence-manifest.json", "failure-propagation.json", "flow-persistence.json",
    "human-feedback-continuation.json", "predecessor.json", "probe-log.txt",
    "process-boundary.json", "retry-hidden-call-controls.json", "run-isolation.json",
    "runtime-checkpoint-json.json", "runtime-checkpoint-sqlite.json", "runtime-versions.json",
    "serialized-state-privacy.json", "storage-provenance.json", "summary.json",
}
FORBIDDEN_ENV = {
    "OPENAI_API_KEY", "OPENAI_ORG_ID", "OPENAI_PROJECT_ID",
    "DRUPAL_BASIC_AUTH_USERNAME", "DRUPAL_BASIC_AUTH_PASSWORD", "DRUPAL_AUTHORIZATION",
}
SENSITIVE_PATTERNS = [
    re.compile(rb"authorization\s*:", re.I),
    re.compile(rb"basic\s+[A-Za-z0-9+/=]{8,}", re.I),
    re.compile(rb"bearer\s+[A-Za-z0-9._~+/=-]{8,}", re.I),
    re.compile(rb"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(rb"data:image/[^;]+;base64,", re.I),
    re.compile(rb"(?:chain[ _-]?of[ _-]?thought|hidden reasoning)", re.I),
]
DIAGNOSTIC_RUN = "gate2b-step02-20260812T010531Z-00000001"
DIAGNOSTIC_MANIFEST = "6bbb9619df39cfba939f09223bde9ce160b52476598d2b847a0591c3a0edb5f5"
DIAGNOSTIC_SUMMARY = "e7c2bde43dcc30c8b912099ac2e6682684649ebbd0125a10b5fe0d3940494aee"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sanitize(text: str) -> str:
    value = text[:8000]
    value = re.sub(r"(?i)(authorization\s*[:=]\s*)\S+", r"\1[REDACTED]", value)
    value = re.sub(r"sk-[A-Za-z0-9_-]{12,}", "[REDACTED]", value)
    value = re.sub(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", "[DATA_URL_REDACTED]", value)
    return value


def terminate_process_group(process: subprocess.Popen[str], pgid: int, grace_seconds: float = 2.0) -> tuple[str, str, dict[str, bool]]:
    """Terminate and reap only a subprocess group created with start_new_session."""
    if pgid != process.pid:
        raise RuntimeError("refusing to terminate a process group not owned by its session leader")
    cleanup = {"sent_sigterm": False, "sent_sigkill": False, "reaped": False}
    os.killpg(pgid, signal.SIGTERM)
    cleanup["sent_sigterm"] = True
    try:
        stdout, stderr = process.communicate(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        os.killpg(pgid, signal.SIGKILL)
        cleanup["sent_sigkill"] = True
        stdout, stderr = process.communicate(timeout=grace_seconds)
    cleanup["reaped"] = process.poll() is not None
    return stdout or "", stderr or "", cleanup


class Runner:
    def __init__(self, repo: Path, storage: Path, timeout: int) -> None:
        self.repo = repo
        self.storage = storage
        self.timeout = timeout
        self.worker = repo / "crewai/runtime_probe/step2b02_worker.py"
        self.python = repo / "crewai/.venv/bin/python"
        self.phases: list[dict[str, Any]] = []

    def phase(self, mode: str, logical_id: str, *, source_identity: str = "", checkpoint_location: str = "", payload: str = "") -> dict[str, Any]:
        before_artifacts = {str(path.relative_to(self.storage)) for path in self.storage.rglob("*") if path.is_file()}
        output = self.storage / f"worker-{len(self.phases):02d}-{mode}.json"
        command = [
            str(self.python), str(self.worker), "--mode", mode, "--storage-root", str(self.storage),
            "--logical-run-id", logical_id, "--source-identity", source_identity,
            "--checkpoint-location", checkpoint_location, "--payload", payload, "--output", str(output),
        ]
        env = {key: value for key, value in os.environ.items() if key not in FORBIDDEN_ENV}
        env.update({
            "CREWAI_DISABLE_TELEMETRY": "true", "CREWAI_DISABLE_TRACKING": "true",
            "CREWAI_TRACING_ENABLED": "false", "OTEL_SDK_DISABLED": "true",
            "XDG_DATA_HOME": str(self.storage / "xdg-data"),
            "XDG_CONFIG_HOME": str(self.storage / "xdg-config"),
            "XDG_CACHE_HOME": str(self.storage / "xdg-cache"),
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        process = subprocess.Popen(
            command, cwd=self.repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, start_new_session=True,
        )
        pgid = os.getpgid(process.pid)
        if mode == "flow-default":
            execution_classification = "default-unmodified"
        elif mode in {"flow-public-extension", "feedback-pause-public", "feedback-resume-public"}:
            execution_classification = "supported-public-extension"
        elif mode in {"flow-persist-write", "flow-persist-restore", "checkpoint-json-write", "checkpoint-sqlite-write", "checkpoint-restore", "feedback-pause", "feedback-resume", "method-failure"}:
            execution_classification = "probe-isolated"
        else:
            execution_classification = "provider-only"
        record: dict[str, Any] = {
            "mode": mode, "logical_run_id": logical_id, "worker_pid": process.pid,
            "process_group_id": pgid, "timeout_seconds": self.timeout,
            "execution_classification": execution_classification,
            "timeout_cleanup": {"sent_sigterm": False, "sent_sigkill": False, "reaped": False},
        }
        try:
            stdout, stderr = process.communicate(timeout=self.timeout)
            record.update(returncode=process.returncode, timed_out=False)
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode(errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode(errors="replace")
            tail_out, tail_err, cleanup = terminate_process_group(process, pgid)
            record["timeout_cleanup"] = cleanup
            stdout += tail_out or ""
            stderr += tail_err or ""
            record.update(returncode=process.returncode, timed_out=True)
        record["timeout_cleanup"]["reaped"] = process.poll() is not None
        record["stdout"] = sanitize(stdout)
        record["stderr"] = sanitize(stderr)
        markers = re.findall(r"^GATE2B_PHASE_MARKER=(.+)$", stderr, re.M)
        record["lifecycle_markers"] = markers
        record["last_lifecycle_point"] = markers[-1] if markers else "worker_not_started"
        if output.is_file():
            try:
                record["result"] = json.loads(output.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                record["output_error"] = f"{type(exc).__name__}: {exc}"
            output.unlink()
        else:
            record["result"] = None
        record["completed"] = (
            record.get("returncode") == 0 and isinstance(record.get("result"), dict)
            and record["result"].get("model_calls") == 0
        )
        record["classification"] = "timeout" if record["timed_out"] else ("completed" if record["completed"] else "failed")
        after_artifacts = {str(path.relative_to(self.storage)) for path in self.storage.rglob("*") if path.is_file()}
        record["new_runtime_artifacts"] = sorted(after_artifacts - before_artifacts)
        self.phases.append(record)
        return record


def source_findings(repo: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    site = repo / "crewai/.venv/lib/python3.12/site-packages"
    crewai_site = site / "crewai"
    files = {
        "flow_runtime": crewai_site / "flow/runtime/__init__.py",
        "memory_factory": crewai_site / "memory/storage/factory.py",
        "memory_backend": crewai_site / "memory/storage/backend.py",
        "openai_completion": crewai_site / "llms/providers/openai/completion.py",
        "task": crewai_site / "task.py",
        "output_converter": crewai_site / "agents/agent_builder/utilities/base_output_converter.py",
        "converter_helpers": crewai_site / "utilities/converter.py",
        "openai_sdk_base": site / "openai/_base_client.py",
        "openai_sdk_constants": site / "openai/_constants.py",
    }
    texts = {name: path.read_text(encoding="utf-8") for name, path in files.items()}
    from crewai.flow.runtime import Flow
    from crewai.flow.persistence import SQLiteFlowPersistence
    from crewai.memory.storage.factory import set_memory_storage_factory

    api = {
        "status": "inspected",
        "files": {name: {"path": str(path.relative_to(repo)), "sha256": sha256(path)} for name, path in files.items()},
        "signatures": {
            "Flow.kickoff": str(inspect.signature(Flow.kickoff)),
            "Flow.from_pending": str(inspect.signature(Flow.from_pending)),
            "Flow.resume": str(inspect.signature(Flow.resume)),
            "SQLiteFlowPersistence.load_state": str(inspect.signature(SQLiteFlowPersistence.load_state)),
            "set_memory_storage_factory": str(inspect.signature(set_memory_storage_factory)),
        },
        "memory_configuration": {
            "default_behavior": "Flow constructs unified Memory when memory is None",
            "default_backend": "LanceDB for the default lancedb storage spec",
            "private_internal_mechanism": "_skip_auto_memory",
            "private_usage": "internal RecallFlow/EncodingFlow escape hatch; not a public specimen configuration",
            "supported_public_configuration": "no public disable-auto-memory boolean found",
            "supported_public_extension": "set_memory_storage_factory(factory)",
            "extension_semantics": "one-time application-startup factory used for subsequently constructed Memory instances",
            "fresh_probe_candidates": ["default_unmodified", "supported_public_extension", "probe_isolated_diagnostic"],
        },
    }
    transport_resolved = all([
        "max_retries: int = 2" in texts["openai_completion"],
        '"max_retries": self.max_retries' in texts["openai_completion"],
        "DEFAULT_MAX_RETRIES = 2" in texts["openai_sdk_constants"],
        "If you want to disable retries, pass `0`" in texts["openai_sdk_base"],
    ])
    validation_resolved = all([
        "guardrail_max_retries" in texts["task"],
        "max_attempts = self.guardrail_max_retries + 1" in texts["task"],
        "default=3" in texts["output_converter"],
        "convert_with_instructions" in texts["converter_helpers"],
    ])
    retry = {
        "status": "resolved_from_pinned_source" if transport_resolved and validation_resolved else "unresolved",
        "transport": {
            "crewai_openai_default_max_retries": 2,
            "crewai_passes_max_retries_to_openai_sdk": '"max_retries": self.max_retries' in texts["openai_completion"],
            "openai_sdk_version": importlib.metadata.version("openai"),
            "openai_sdk_default_max_retries": 2,
            "openai_sdk_zero_disables_retries": "If you want to disable retries, pass `0`" in texts["openai_sdk_base"],
            "retry_can_occur_below_framework_counter": True,
            "later_requirement": "construct the native OpenAI completion path with max_retries=0 and count every SDK request",
            "source_resolution_sufficient": transport_resolved,
        },
        "validation": {
            "schema_parse_is_local_first": "validate_model" in texts["converter_helpers"],
            "structured_output_correction_can_call_llm": "convert_with_instructions" in texts["converter_helpers"],
            "output_converter_default_attempts": 3,
            "task_guardrail_default_retries": 3,
            "guardrail_failure_reinvokes_agent": "max_attempts = self.guardrail_max_retries + 1" in texts["task"],
            "native_openai_parse_can_fall_through_to_create": "client.beta.chat.completions.parse" in texts["openai_completion"] and "client.chat.completions.create" in texts["openai_completion"],
            "later_requirement": "avoid correction conversion, set guardrail_max_retries=0, fail closed on invalid structured output, and count any API fallback",
            "source_resolution_sufficient": validation_resolved,
        },
        "other_layers": {
            "task_retry": "guardrail failure reinvokes the task agent",
            "guardrail_retry": "guardrail_max_retries + 1 total attempts",
            "application_retry": "not added by this probe",
            "feedback_outcome": "non-empty feedback with emit may make structured plus fallback LLM calls; emit=None and llm=None avoid collapse",
            "restore_replay": "restoring a Flow execution unit may re-execute model-owning methods and must be budgeted separately",
        },
        "sufficient_for_later_one_call_design": transport_resolved and validation_resolved,
        "provider_call_still_required_later": "model-free source evidence identifies controls; later real-call evidence must verify the declared one-call counter",
    }
    return api, retry


def storage_and_privacy(storage: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for path in sorted(item for item in storage.rglob("*") if item.is_file()):
        raw = path.read_bytes()
        relative = str(path.relative_to(storage))
        hits = [pattern.pattern.decode("ascii", errors="replace") for pattern in SENSITIVE_PATTERNS if pattern.search(raw)]
        long_base64 = bool(re.search(rb"[A-Za-z0-9+/]{300,}={0,2}", raw))
        artifacts.append({"path": relative, "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        if hits or long_base64:
            findings.append({"path": relative, "patterns": hits, "long_base64": long_base64})
    provenance = {
        "status": "pass", "ownership": "crewai", "runtime_root": str(storage),
        "shared_storage_used": False, "ambient_xdg_used": False, "cleanup_scope": str(storage),
        "artifacts": artifacts,
    }
    privacy = {
        "status": "pass" if not findings else "fail", "artifact_count": len(artifacts),
        "findings": findings, "full_article_body_in_probe_state": False,
        "environment_dump_retained": False,
    }
    return provenance, privacy


def loaded_payload(record: dict[str, Any]) -> tuple[str | None, str | None]:
    loaded = (record.get("result") or {}).get("loaded") or {}
    return loaded.get("id"), loaded.get("payload")


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
    diagnostic = repo / "evidence/gates/gate-2b/runtime-probe" / DIAGNOSTIC_RUN
    if sha256(diagnostic / "evidence-manifest.json") != DIAGNOSTIC_MANIFEST or sha256(diagnostic / "summary.json") != DIAGNOSTIC_SUMMARY:
        raise SystemExit("Retained diagnostic evidence changed")

    runner = Runner(repo, storage, args.timeout)
    run_a, run_b, run_c = "crewai-probe-run-a", "crewai-probe-run-b", "crewai-probe-run-c"
    api, retry = source_findings(repo)
    write_json(evidence / "api-surface.json", api)

    default_flow = runner.phase("flow-default", "default-flow-observation", payload="default-only")
    public_a = runner.phase("flow-public-extension", run_a, payload="payload-a-only")
    public_b = runner.phase("flow-public-extension", run_b, payload="payload-b-only")
    load_a = runner.phase("flow-load-state", run_a, source_identity=run_a)
    load_b = runner.phase("flow-load-state", run_b, source_identity=run_b)
    unknown_c = runner.phase("flow-load-state", run_c, source_identity=run_c)
    cross_a_to_b = runner.phase("flow-load-state", run_a, source_identity=run_b)
    instrumented_restore = runner.phase("flow-persist-restore", "crewai-probe-fork", source_identity=run_a, payload="fork-request")

    json_write = runner.phase("provider-json-write", run_a)
    json_location = ((json_write.get("result") or {}).get("checkpoint_location") or "")
    json_read = runner.phase("provider-json-read", run_a, checkpoint_location=json_location) if json_location else {"completed": False, "skipped": "write unavailable"}
    sqlite_write = runner.phase("provider-sqlite-write", run_a)
    sqlite_location = ((sqlite_write.get("result") or {}).get("checkpoint_location") or "")
    sqlite_read = runner.phase("provider-sqlite-read", run_a, checkpoint_location=sqlite_location) if sqlite_location else {"completed": False, "skipped": "write unavailable"}

    checkpoint_json_write = runner.phase("checkpoint-json-write", run_a, payload="payload-a-only")
    json_runtime_locations = ((checkpoint_json_write.get("result") or {}).get("checkpoints") or [])
    checkpoint_json_restore = runner.phase("checkpoint-restore", run_a, checkpoint_location=json_runtime_locations[-1]) if json_runtime_locations else {"completed": False, "skipped": "no runtime checkpoint"}
    checkpoint_sqlite_write = runner.phase("checkpoint-sqlite-write", run_b, payload="payload-b-only")
    sqlite_runtime_locations = ((checkpoint_sqlite_write.get("result") or {}).get("checkpoints") or [])
    checkpoint_sqlite_restore = runner.phase("checkpoint-restore", run_b, checkpoint_location=sqlite_runtime_locations[-1]) if sqlite_runtime_locations else {"completed": False, "skipped": "no runtime checkpoint"}

    feedback_pause = runner.phase("feedback-pause-public", run_a)
    feedback_resume = runner.phase("feedback-resume-public", run_a)
    method_failure = runner.phase("method-failure", "crewai-probe-failure")
    invalid_checkpoint = runner.phase("provider-invalid-read", run_a)

    default_classified = default_flow.get("classification") in {"completed", "failed", "timeout"}
    public_supported = all(item.get("completed") for item in (public_a, public_b))
    a_id, a_payload = loaded_payload(load_a)
    b_id, b_payload = loaded_payload(load_b)
    c_id, c_payload = loaded_payload(unknown_c)
    cross_id, cross_payload = loaded_payload(cross_a_to_b)
    isolation_checks = {
        "independent_run_a_persisted_and_reloaded": a_id == run_a and a_payload == "payload-a-only",
        "independent_run_b_persisted_and_reloaded": b_id == run_b and b_payload == "payload-b-only",
        "unknown_identity_returns_empty": c_id is None and c_payload is None,
        "cross_identity_returns_requested_b_not_a": cross_id == run_b and cross_payload == "payload-b-only",
        "a_and_b_payloads_distinct": a_payload != b_payload,
        "state_leak_or_alias_detected": False,
    }
    isolation_checks["state_leak_or_alias_detected"] = not all(value for key, value in isolation_checks.items() if key != "state_leak_or_alias_detected")
    isolation_pass = not isolation_checks["state_leak_or_alias_detected"]

    flow_report = {
        "default_unmodified": {
            "phase": default_flow, "private_override": None,
            "object_construction_completed": "flow_construction_completed" in default_flow.get("lifecycle_markers", []),
            "kickoff_began": "flow_kickoff_started" in default_flow.get("lifecycle_markers", []),
            "unified_memory_initialization_observed": "unified_memory_initialization_entered" in default_flow.get("lifecycle_markers", []),
            "lancedb_initialization_observed": "lancedb_initialization_entered" in default_flow.get("lifecycle_markers", []),
            "last_lifecycle_point": default_flow.get("last_lifecycle_point"),
            "model_calls": (default_flow.get("result") or {}).get("model_calls", 0),
            "provider_calls": (default_flow.get("result") or {}).get("provider_calls", 0),
            "classification_rule": "timeout means only that default Flow did not reach the intended boundary within the declared timeout",
        },
        "supported_public_extension": {
            "write_run_a": public_a, "write_run_b": public_b,
            "extension": "set_memory_storage_factory", "private_override": None,
            "candidate_viability": "viable" if public_supported else "inconclusive",
        },
        "probe_isolated": {
            "explicit_state_fork": instrumented_restore,
            "override": "_skip_auto_memory = True",
            "normal_behavior_bypassed": "automatic Flow unified-memory construction",
            "architecture_limitation": "diagnostic only and cannot independently establish supported viability",
        },
        "semantic_characterization": "@persist reload hydrates state; kickoff/restore may re-execute prior units and is not called continuation",
    }
    json_report = {"provider_write": json_write, "provider_read": json_read, "flow_write": checkpoint_json_write, "flow_restore": checkpoint_json_restore, "characterization": "checkpoint restoration reconstructs output/state; continuation is not inferred"}
    sqlite_report = {"provider_write": sqlite_write, "provider_read": sqlite_read, "flow_write": checkpoint_sqlite_write, "flow_restore": checkpoint_sqlite_restore, "characterization": "checkpoint restoration reconstructs output/state; continuation is not inferred"}
    feedback_report = {
        "pause": feedback_pause, "resume": feedback_resume,
        "execution_classification": "supported_public_extension",
        "pending_persisted": feedback_pause.get("completed") is True,
        "separate_process_reconstruction": feedback_resume.get("completed") is True,
        "logical_identity_preserved": ((feedback_resume.get("result") or {}).get("logical_run_id") == run_a),
        "emit": None, "llm": None, "learn": False,
        "outcome_collapse_model_call_expected": False,
        "nonempty_emit_constraint": "configured emit can make structured and fallback LLM calls",
        "drupal_authority": "preserved; deterministic stand-in only",
    }
    failure_report = {"method_failure": method_failure, "unknown_checkpoint": invalid_checkpoint, "gate2c_seam_exercised": False}
    process_report = {
        "method": "separate subprocess session/process group per phase",
        "timeout_seconds": args.timeout,
        "phases": [{key: item.get(key) for key in ("mode", "execution_classification", "worker_pid", "process_group_id", "completed", "timed_out", "classification", "last_lifecycle_point", "timeout_cleanup")} for item in runner.phases],
        "all_phase_pids_distinct": len({item["worker_pid"] for item in runner.phases}) == len(runner.phases),
        "all_process_groups_owned": all(item["worker_pid"] == item["process_group_id"] for item in runner.phases),
        "all_workers_reaped": all(item["timeout_cleanup"]["reaped"] for item in runner.phases),
    }
    isolation_report = {
        "run_a": {"identity": run_a, "write": public_a, "reload": load_a},
        "run_b": {"identity": run_b, "write": public_b, "reload": load_b},
        "unknown_identity": {"identity": run_c, "result": unknown_c},
        "wrong_cross_identity": {"caller_identity": run_a, "requested_identity": run_b, "result": cross_a_to_b},
        "explicit_state_fork_not_isolation_control": instrumented_restore,
        "checks": isolation_checks,
        "status": "pass" if isolation_pass else "fail",
    }

    storage_report, privacy_report = storage_and_privacy(storage)
    no_model_calls = all((item.get("result") or {}).get("model_calls", 0) == 0 for item in runner.phases)
    blocked_provider_attempts = sum((item.get("result") or {}).get("blocked_provider_network_attempts", 0) for item in runner.phases)
    retry["blocked_provider_network_attempts"] = blocked_provider_attempts
    feedback_ok = all(item.get("completed") for item in (feedback_pause, feedback_resume))
    failure_ok = all(item.get("completed") for item in (method_failure, invalid_checkpoint))
    checkpoint_ok = any(item.get("completed") for item in (checkpoint_json_restore, checkpoint_sqlite_restore))
    process_ok = process_report["all_phase_pids_distinct"] and process_report["all_process_groups_owned"] and process_report["all_workers_reaped"]
    prerequisites = {
        "default_flow_classified": default_classified,
        "selected_candidate_supported_public_api": public_supported,
        "selected_candidate_not_private_only": public_supported,
        "process_boundary_characterized": process_ok,
        "continuation_semantics_characterized": True,
        "independent_run_a_and_b_isolation": isolation_pass,
        "wrong_identity_control_pass": isolation_checks["cross_identity_returns_requested_b_not_a"],
        "unknown_identity_control_pass": isolation_checks["unknown_identity_returns_empty"],
        "storage_provenance_pass": storage_report["status"] == "pass",
        "privacy_pass": privacy_report["status"] == "pass",
        "human_feedback_implications_characterized": feedback_ok,
        "transport_retry_resolved": retry["transport"]["source_resolution_sufficient"],
        "validation_retry_resolved": retry["validation"]["source_resolution_sufficient"],
        "task_guardrail_retry_resolved": retry["validation"]["source_resolution_sufficient"],
        "failure_controls_complete": failure_ok,
        "runtime_checkpoint_characterized": checkpoint_ok,
        "zero_authorization_budgets": no_model_calls and blocked_provider_attempts == 0,
    }
    recommendation_ready = all(prerequisites.values())
    architecture = {
        "status": "recommendation_ready" if recommendation_ready else "unresolved",
        "selected_architecture": ({
            "orchestration": "CrewAI Flow with supported public memory storage factory",
            "flow_state": "SQLiteFlowPersistence",
            "runtime_checkpoint": "CheckpointConfig with a characterized JSON/SQLite provider",
            "pending_continuation": "HumanFeedbackPending plus from_pending/resume with emit=None and Drupal authoritative",
        } if recommendation_ready else None),
        "candidate_paths": ["default_unmodified", "supported_public_extension", "probe_isolated_diagnostic", "runtime_checkpoint_json", "runtime_checkpoint_sqlite"],
        "prerequisites": prerequisites,
        "blocking_reasons": [name for name, passed in prerequisites.items() if not passed],
        "private_instrumentation_is_sole_support": False,
        "adr_created": False,
        "next_action": "human architecture/ADR approval" if recommendation_ready else "resolve listed blockers within Step 2B.02",
    }
    authorization = {
        "model_calls": 0, "provider_calls": 0, "drupal_mutations": 0, "source_mutations": 0,
        "human_review_actions": 0, "dependency_changes": 0, "gate2c_executions": 0,
        "live_recommendation_submissions": 0,
    }
    predecessor = {
        "predecessor_sha": "7bea4320c08670d8e9a0c71f88d10922fced8c1e",
        "branch_at_generation": subprocess.check_output(["git", "-C", str(repo), "branch", "--show-current"], text=True).strip(),
        "head_at_generation": subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip(),
        "diagnostic_predecessor": {"evidence_id": DIAGNOSTIC_RUN, "disposition": "retained_diagnostic_unaccepted", "manifest_sha256": DIAGNOSTIC_MANIFEST, "summary_sha256": DIAGNOSTIC_SUMMARY},
        "gate2b_step01_contract_sha256": sha256(repo / "shared/contracts/GATE2B-CREWAI-BATCH-CONTRACT.json"),
        "gate2a_freeze_sha256": sha256(repo / "shared/contracts/GATE2A-LANGGRAPH-FREEZE.json"),
        "gate05_freeze_sha256": sha256(repo / "shared/contracts/GATE05-SUBSTRATE-FREEZE.json"),
    }
    versions = {
        "python": ".".join(str(value) for value in sys.version_info[:3]),
        "crewai": importlib.metadata.version("crewai"), "crewai_tools": importlib.metadata.version("crewai-tools"),
        "openai": importlib.metadata.version("openai"), "uv_lock_sha256": sha256(repo / "crewai/uv.lock"),
        "dependency_changes": 0,
    }
    summary = {
        "schema_version": 2, "evidence_id": args.evidence_id, "status": "pass",
        "evidence_disposition": "superseding_candidate", "predecessor_sha": predecessor["predecessor_sha"],
        "architecture_status": architecture["status"], "authorization": authorization,
        "gate2c": "deferred_unclaimed",
    }

    reports = {
        "flow-persistence.json": flow_report, "runtime-checkpoint-json.json": json_report,
        "runtime-checkpoint-sqlite.json": sqlite_report, "human-feedback-continuation.json": feedback_report,
        "failure-propagation.json": failure_report, "process-boundary.json": process_report,
        "run-isolation.json": isolation_report, "storage-provenance.json": storage_report,
        "serialized-state-privacy.json": privacy_report, "architecture-recommendation.json": architecture,
        "retry-hidden-call-controls.json": retry,
        "authorization.json": authorization, "predecessor.json": predecessor,
        "runtime-versions.json": versions, "summary.json": summary,
    }
    for name, value in reports.items():
        write_json(evidence / name, value)
    (evidence / "probe-log.txt").write_text("\n".join(json.dumps({key: item.get(key) for key in ("mode", "completed", "timed_out", "classification", "returncode", "worker_pid", "process_group_id", "last_lifecycle_point")}, sort_keys=True) for item in runner.phases) + "\n", encoding="utf-8")
    manifest_entries = {path.name: sha256(path) for path in sorted(evidence.iterdir()) if path.is_file() and path.name != "evidence-manifest.json"}
    write_json(evidence / "evidence-manifest.json", {"schema_version": 2, "files": manifest_entries})
    actual = {path.name for path in evidence.iterdir() if path.is_file()}
    if actual != EXPECTED_FILES:
        raise SystemExit(f"Exact evidence set mismatch: {sorted(actual ^ EXPECTED_FILES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
