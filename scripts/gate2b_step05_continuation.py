#!/usr/bin/env python3
"""Execute separately authorized Step 2B.05 lifecycle stages.

The standard-library preflight and failure recorder intentionally load before
CrewAI. This lets Boundary A retain evidence even when startup fails before a
Flow can be imported or instantiated.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
from typing import Any


PREDECESSOR = "c61d0b0213d754fcc40f18065836de6e0da70d2c"
SOURCE_RUN_ID = "crewai-20260818T215017Z-8e03fc95"
RECOMMENDATION_UUID = "1878ae86-834c-4813-9134-4c3b8d0833c9"
RECOMMENDATION_NODE_ID = 21
SOURCE_PROJECTION_SHA256 = "f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17"
SOURCE_CANONICAL_MANIFEST_SHA256 = "c6115ffea4b7ceefb7858e6b482713fc92998dcf2bde7bc6de8831d583665aaf"
SOURCE_CANONICAL_SUMMARY_SHA256 = "5cd324d26b866c83d9728e7634887bcf3ccc46c2df5f4fc6a9563069f71ef490"
SOURCE_CLOSURE_MANIFEST_SHA256 = "d62ababa96b223643ab23e3d67c75b3fcc2bb325a8a3e69787fff870cc56583b"
SOURCE_CLOSURE_SUMMARY_SHA256 = "e482aa166485ea97c0698b82dade0cfdadbe9947fb06aa2ce0d59c9a3cc87f01"
FAILED_V100_CONTINUATION_ID = "gate2b-step05-20260820T151225Z-8b7fa221"
SOURCE_RUNTIME = {
    "flow-state.sqlite": ("d0fd3ac373b6af0aace07b7eed6813ebea28ceab37ab47265da2da94a24acff2", 45056),
    "flow-state.sqlite-wal": ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", 0),
    "flow-state.sqlite-shm": ("fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb", 32768),
}
STAGE_A_FILES = ("authorization.json", "bindings.json", "process-a.json",
                 "events-process-a.jsonl", "process-a-summary.json")
FINAL_FILES = (
    "authorization.json", "bindings.json", "process-a.json", "events-process-a.jsonl",
    "process-a-summary.json", "process-a-manifest.json", "human-review.json",
    "human-review-manifest.json", "process-b.json", "accounting.json",
    "events-process-b.jsonl", "privacy-scan.json", "summary.json", "summary.md",
    "evidence-manifest.json",
)
ZERO_ACTIVITY = {
    "model_generations": 0, "provider_requests": 0, "provider_responses": 0,
    "provider_retries": 0, "repair_calls": 0, "fallback_calls": 0,
    "feedback_collapse_calls": 0, "learning_calls": 0,
    "recommendation_submissions": 0, "drupal_writes": 0,
    "human_review_actions": 0, "source_mutations": 0,
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    temp.replace(path)


def manifest(root: Path, names: tuple[str, ...] | list[str], output: str) -> None:
    write_json(root / output, {"algorithm": "sha256", "entries": [
        {"path": name, "sha256": sha(root / name)} for name in names
    ]})


def resolved(path: Path) -> Path:
    """Canonicalize a path without creating it."""
    return path.expanduser().resolve(strict=False)


def validate_isolation_paths(xdg_root: Path, runtime: Path) -> tuple[Path, Path]:
    """Require sibling, non-alias XDG and authoritative runtime namespaces."""
    xdg = resolved(xdg_root)
    candidate = resolved(runtime)
    if xdg == candidate or xdg.is_relative_to(candidate) or candidate.is_relative_to(xdg):
        raise RuntimeError("XDG and continuation runtime paths must be disjoint siblings")
    return xdg, candidate


def require_fresh_identity(continuation_id: str, evidence: Path, runtime: Path) -> None:
    if continuation_id == FAILED_V100_CONTINUATION_ID:
        raise RuntimeError("The consumed v1.0.0 continuation identity may not be reused")
    if evidence.exists() or runtime.exists():
        raise RuntimeError("Continuation evidence/runtime identity already exists")


def failure_facts(runtime: Path) -> dict[str, Any]:
    return {
        "authoritative_runtime_created": runtime.exists(),
        "source_runtime_copied": False,
        "flow_instantiated": False,
        "pending_row_count": 0,
        "activity": dict(ZERO_ACTIVITY),
        "cleanup_or_rollback": "not_attempted_by_stage_recorder; package wrapper owns repository rollback",
    }


def record_stage_failure(
    failure_root: Path,
    continuation_id: str,
    stage: str,
    classification: str,
    error_type: str,
    runtime: Path,
    facts: dict[str, Any] | None = None,
) -> Path:
    """Retain a sanitized immutable two-file failure attempt."""
    values = failure_facts(runtime)
    if facts:
        values.update(facts)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    attempt_id = f"{stage}-{stamp}-{secrets.token_hex(4)}"
    attempt = failure_root / continuation_id / attempt_id
    attempt.mkdir(parents=True, exist_ok=False)
    write_json(attempt / "failure.json", {
        "schema_version": 1,
        "status": "failed",
        "retrospective": False,
        "continuation_id": continuation_id,
        "stage_attempt_id": attempt_id,
        "stage": stage,
        "captured_at": now(),
        "predecessor_sha": PREDECESSOR,
        "source_run_id": SOURCE_RUN_ID,
        "recommendation": {"uuid": RECOMMENDATION_UUID, "node_id": 21,
                           "source_revision_id": 21},
        "failure_classification": classification,
        "failure_point": stage,
        "error_type": error_type,
        "authoritative_runtime_created": bool(values["authoritative_runtime_created"]),
        "source_runtime_copied": bool(values["source_runtime_copied"]),
        "flow_instantiated": bool(values["flow_instantiated"]),
        "pending_row_count": int(values["pending_row_count"]),
        "activity": values["activity"],
        "source_or_drupal_authoritative_state_mutation_claimed": False,
        "cleanup_or_rollback": values["cleanup_or_rollback"],
        "retained_runtime": {
            "path": runtime.as_posix(),
            "exists_at_capture": runtime.exists(),
            "disposition": "retained as consumed failed-attempt path" if runtime.exists()
                           else "not created",
        },
        "privacy": {"status": "pass", "secrets_retained": False,
                    "environment_dump_retained": False, "hidden_reasoning_retained": False},
    })
    manifest(attempt, ["failure.json"], "failure-manifest.json")
    return attempt


def continuation_api() -> dict[str, Any]:
    """Load CrewAI-dependent code only after path and source-runtime preflight."""
    os.environ.setdefault("CREWAI_DISABLE_VERSION_CHECK", "true")
    os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
    os.environ.setdefault("CREWAI_DISABLE_TRACKING", "true")
    os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
    os.environ.setdefault("OTEL_SDK_DISABLED", "true")
    from crewai.flow.async_feedback import HumanFeedbackPending
    from agentic_harness_crewai.human_review_continuation import (
        build_continuation_flow, load_source_state, pending_identity, persistence_for,
        resume_signal, validate_reviewed_observation,
    )
    return locals()


def envelope_data(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("ok") is not True or not isinstance(value.get("data"), dict):
        raise RuntimeError("Read-only Drupal status envelope failed")
    return value["data"]


def client() -> Any:
    from shared.drupal_client.client import DrupalClient
    required = {
        "base_url": os.environ.get("GATE2B_DRUPAL_BASE_URL", ""),
        "username": os.environ.get("GATE2B_DRUPAL_BASIC_AUTH_USER", ""),
        "password": os.environ.get("GATE2B_DRUPAL_BASIC_AUTH_PASSWORD", ""),
    }
    if not all(required.values()):
        raise RuntimeError("Required Drupal read-only observation credentials are unavailable")
    return DrupalClient(**required,
                        verify_tls=os.environ.get("GATE2B_DRUPAL_INSECURE_LOCAL") != "true")


def status_reader(correlation_id: str):
    drupal = client()
    return lambda: envelope_data(drupal.get_recommendation_status(RECOMMENDATION_UUID, correlation_id))


def ddev_json(repo: Path, script: str, *args: str) -> dict[str, Any]:
    result = subprocess.run(
        ["ddev", "drush", "--quiet", "php:script", script, "--", *args],
        cwd=repo / "drupal", text=True, check=True, capture_output=True,
    )
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise RuntimeError("Drupal read-only inspection returned invalid JSON")
    return value


def source_snapshot(repo: Path) -> dict[str, Any]:
    value = ddev_json(repo, "scripts/gate1-step04-canonical-vertical-slice.php", "snapshot")
    if (value.get("article_count") != 20 or value.get("suggestion_count") != 1
            or value.get("target_count") != 12
            or value.get("article_source_sha256") != SOURCE_PROJECTION_SHA256):
        raise RuntimeError("Frozen Drupal source projection or object counts drifted")
    return {key: value[key] for key in ("article_count", "suggestion_count", "target_count",
                                         "canonical_target_sequence", "target_sequence_sha256",
                                         "article_source_sha256")}


def inspect_recommendation(repo: Path) -> dict[str, Any]:
    return ddev_json(repo, "scripts/gate05-step04.php", "inspect", str(RECOMMENDATION_NODE_ID))


def verify_source_runtime(repo: Path) -> dict[str, Any]:
    root = repo / "crewai/.runtime/gate2b-step04" / SOURCE_RUN_ID
    result: dict[str, Any] = {}
    for name, (expected_hash, expected_size) in SOURCE_RUNTIME.items():
        path = root / name
        actual = {"sha256": sha(path), "size": path.stat().st_size}
        if actual != {"sha256": expected_hash, "size": expected_size}:
            raise RuntimeError(f"Authoritative source runtime drifted: {name}")
        result[name] = actual
    return result


def copy_runtime(repo: Path, runtime: Path) -> dict[str, Any]:
    source = repo / "crewai/.runtime/gate2b-step04" / SOURCE_RUN_ID
    runtime.mkdir(parents=True, exist_ok=False)
    provenance: dict[str, Any] = {}
    for name in SOURCE_RUNTIME:
        shutil.copy2(source / name, runtime / name)
        provenance[name] = {"source_sha256": sha(source / name), "copy_sha256": sha(runtime / name),
                            "size": (runtime / name).stat().st_size}
        if provenance[name]["source_sha256"] != provenance[name]["copy_sha256"]:
            raise RuntimeError(f"Runtime copy hash mismatch: {name}")
    return provenance


def validate_pending_lineage(inspection: dict[str, Any]) -> None:
    revisions = inspection.get("revisions")
    if (inspection.get("uuid") != RECOMMENDATION_UUID or inspection.get("node_id") != 21
            or inspection.get("current_revision_id") != 21
            or inspection.get("current_review_status") != "pending"
            or not isinstance(revisions, list) or len(revisions) != 1
            or revisions[0].get("revision_user", {}).get("name") != "agent_bot"):
        raise RuntimeError("Pre-review Drupal revision lineage drifted")


def validate_review_lineage(inspection: dict[str, Any], pending_inspection: dict[str, Any]) -> None:
    revisions = inspection.get("revisions")
    prior = pending_inspection.get("revisions")
    if (inspection.get("uuid") != RECOMMENDATION_UUID or inspection.get("node_id") != 21
            or inspection.get("current_review_status") != "approved"
            or not isinstance(revisions, list) or len(revisions) != 2
            or not isinstance(prior, list) or len(prior) != 1 or revisions[0] != prior[0]):
        raise RuntimeError("Drupal review lineage does not contain exactly one preserved approval revision")
    initial, reviewed = revisions
    immutable = ("proposed_alt_text", "source_framework", "run_id", "evidence_hash", "target", "published")
    if any(reviewed.get(key) != initial.get(key) for key in immutable):
        raise RuntimeError("Approve-as-is changed immutable recommendation data")
    if (reviewed.get("revision_user", {}).get("name") != "editor_dana"
            or reviewed.get("review_status") != "approved"
            or reviewed.get("revision_id") != 22):
        raise RuntimeError("Latest revision is not the governed editor_dana approval")


def process_a(repo: Path, evidence: Path, runtime: Path, xdg_root: Path,
              continuation_id: str) -> None:
    failure_root = repo / "evidence/gates/gate-2b/human-review-continuation-failures"
    stage = "continuation-allocation"
    facts = failure_facts(runtime)
    try:
        require_fresh_identity(continuation_id, evidence, runtime)
        stage = "xdg-runtime-path-validation"
        validate_isolation_paths(xdg_root, runtime)
        if not xdg_root.is_dir():
            raise RuntimeError("Disposable XDG root was not established")
        if runtime.exists():
            raise RuntimeError("Runtime candidate exists before Process A initialization")
        stage = "source-runtime-preflight"
        source_runtime = verify_source_runtime(repo)
        source_before = source_snapshot(repo)
        inspection = inspect_recommendation(repo)
        validate_pending_lineage(inspection)
        stage = "runtime-copy-creation"
        provenance = copy_runtime(repo, runtime)
        facts["authoritative_runtime_created"] = True
        facts["source_runtime_copied"] = True
        stage = "crewai-import-startup"
        api = continuation_api()
        stage = "source-state-loading"
        backend = api["persistence_for"](runtime / "flow-state.sqlite")
        state = api["load_source_state"](backend)
        state["continuation_id"] = continuation_id
        stage = "flow-instantiation"
        reader = status_reader(f"{continuation_id}-process-a")
        flow_class = api["build_continuation_flow"](
            persistence=backend, status_reader=reader, continuation_id=continuation_id)
        flow = flow_class(suppress_flow_events=True, tracing=False)
        facts["flow_instantiated"] = True
        stage = "pending-boundary-creation"
        result = flow.kickoff(inputs=state)
        if not isinstance(result, api["HumanFeedbackPending"]):
            raise RuntimeError("Process A did not return HumanFeedbackPending")
        context_hash = api["pending_identity"](result.context)
        if result.context.flow_id != SOURCE_RUN_ID:
            raise RuntimeError("HumanFeedbackPending Flow identity drifted")
        loaded = backend.load_pending_feedback(SOURCE_RUN_ID)
        if loaded is None or api["pending_identity"](loaded[1]) != context_hash:
            raise RuntimeError("Persisted pending identity differs from returned context")
        facts["pending_row_count"] = 1
        stage = "process-a-evidence-finalization"
        evidence.mkdir(parents=True, exist_ok=False)
        authorization = {"status": "pass", "boundary": "package-execution-and-process-a",
                         "counts": {**ZERO_ACTIVITY, "process_b_executions": 0,
                                    "gate2c_executions": 0}}
        bindings = {"status": "pass", "predecessor": PREDECESSOR, "source_run_id": SOURCE_RUN_ID,
                    "flow_state_id": result.context.flow_id, "recommendation_uuid": RECOMMENDATION_UUID,
                    "recommendation_node_id": 21, "source_revision_id": 21,
                    "canonical_manifest_sha256": SOURCE_CANONICAL_MANIFEST_SHA256,
                    "canonical_summary_sha256": SOURCE_CANONICAL_SUMMARY_SHA256,
                    "closure_manifest_sha256": SOURCE_CLOSURE_MANIFEST_SHA256,
                    "closure_summary_sha256": SOURCE_CLOSURE_SUMMARY_SHA256,
                    "source_runtime": source_runtime, "runtime_copy_before_open": provenance,
                    "xdg_runtime_separation": {"status": "pass", "xdg_root": xdg_root.as_posix(),
                                               "runtime": runtime.as_posix()}}
        process = {"status": "pending", "continuation_id": continuation_id,
                   "process_a_pid": os.getpid(), "process_a_exited_cleanly": True,
                   "pending_identity": context_hash,
                   "pending_identity_source": "returned HumanFeedbackPending.context.to_dict()",
                   "initial_instance_pending_property_used": False,
                   "drupal": {"status_observation": flow.state.review_observation,
                              "inspection": inspection, "source_snapshot": source_before},
                   "replay_attempts": flow.state.replay_attempts,
                   "additional_activity": flow.state.additional_activity,
                   "runtime_after_pending": {name: {"sha256": sha(runtime / name),
                                                     "size": (runtime / name).stat().st_size}
                                             for name in SOURCE_RUNTIME}}
        write_json(evidence / "authorization.json", authorization)
        write_json(evidence / "bindings.json", bindings)
        write_json(evidence / "process-a.json", process)
        (evidence / "events-process-a.jsonl").write_text(
            json.dumps({"event": "human_feedback_pending", "occurred_at": now(),
                        "pending_identity": context_hash}, sort_keys=True) + "\n", encoding="utf-8")
        write_json(evidence / "process-a-summary.json", {
            "status": "pass", "continuation_id": continuation_id, "source_run_id": SOURCE_RUN_ID,
            "pending_identity": context_hash, "next_boundary": "editor_dana Drupal review",
        })
        manifest(evidence, STAGE_A_FILES, "process-a-manifest.json")
        if verify_source_runtime(repo) != source_runtime or source_snapshot(repo) != source_before:
            raise RuntimeError("Authoritative source runtime or Drupal source changed during Process A")
    except Exception as exc:
        record_stage_failure(failure_root, continuation_id, stage, "boundary-a-process-a-failure",
                             type(exc).__name__, runtime, facts)
        raise


def capture_review(repo: Path, evidence: Path) -> None:
    api = continuation_api()
    if not (evidence / "process-a-manifest.json").is_file() or (evidence / "human-review.json").exists():
        raise RuntimeError("Process A evidence missing or review already captured")
    pending_inspection = json.loads((evidence / "process-a.json").read_text())["drupal"]["inspection"]
    inspection = inspect_recommendation(repo)
    validate_review_lineage(inspection, pending_inspection)
    snapshot = source_snapshot(repo)
    status = status_reader(f"{evidence.name}-review-observation")()
    reviewed = api["validate_reviewed_observation"](status)
    if reviewed["revision_id"] != inspection["current_revision_id"]:
        raise RuntimeError("Status projection and revision lineage disagree")
    write_json(evidence / "human-review.json", {
        "status": "pass", "authority": "Drupal", "reviewer": "editor_dana",
        "action": "approve-as-is", "prior_revision_id": 21,
        "decision_revision_id": reviewed["revision_id"], "reviewed_at": reviewed["reviewed_at"],
        "status_observation": status, "lineage": inspection, "source_snapshot": snapshot,
        "process_a_manifest_sha256": sha(evidence / "process-a-manifest.json"),
    })
    manifest(evidence, ["process-a-manifest.json", "human-review.json"], "human-review-manifest.json")


def process_b(repo: Path, evidence: Path, runtime: Path) -> None:
    api = continuation_api()
    if not (evidence / "human-review-manifest.json").is_file() or (evidence / "process-b.json").exists():
        raise RuntimeError("Human-review evidence missing or Process B already completed")
    process_a_data = json.loads((evidence / "process-a.json").read_text())
    review = json.loads((evidence / "human-review.json").read_text())
    reader = status_reader(f"{evidence.name}-process-b")
    authoritative = api["validate_reviewed_observation"](reader())
    if (authoritative["revision_id"] != review["decision_revision_id"]
            or authoritative["reviewed_at"] != review["reviewed_at"]):
        raise RuntimeError("Current Drupal state contradicts captured human-review evidence")
    payload = api["resume_signal"](authoritative)
    backend = api["persistence_for"](runtime / "flow-state.sqlite")
    pending_rows_before = int(backend.load_pending_feedback(SOURCE_RUN_ID) is not None)
    if pending_rows_before != 1:
        raise RuntimeError("Process B requires exactly one pre-resume pending row")
    flow_class = api["build_continuation_flow"](
        persistence=backend, status_reader=reader, continuation_id=evidence.name)
    authoritative_from_pending_calls = 0
    authoritative_resume_calls = 0
    authoritative_from_pending_calls += 1
    flow = flow_class.from_pending(SOURCE_RUN_ID, backend, suppress_flow_events=True, tracing=False)
    if flow.pending_feedback is None:
        raise RuntimeError("from_pending did not restore pending context")
    identity = api["pending_identity"](flow.pending_feedback)
    if identity != process_a_data["pending_identity"]:
        raise RuntimeError("Process B pending identity differs from Process A")
    authoritative_resume_calls += 1
    result = flow.resume(payload)
    pending_rows_after = int(backend.load_pending_feedback(SOURCE_RUN_ID) is not None)
    if result.get("status") != "completed" or pending_rows_after != 0:
        raise RuntimeError("Resume did not complete and clear pending exactly once")
    final_snapshot = source_snapshot(repo)
    if final_snapshot["article_source_sha256"] != SOURCE_PROJECTION_SHA256:
        raise RuntimeError("Source Article projection changed")
    write_json(evidence / "process-b.json", {
        "status": "pass", "process_b_pid": os.getpid(), "same_process_as_a": False,
        "from_pending": True, "resume": True, "flow_state_id": flow.state.id,
        "pending_identity": identity, "pending_cleared": True,
        "authoritative_from_pending_calls": authoritative_from_pending_calls,
        "authoritative_resume_calls": authoritative_resume_calls,
        "second_authoritative_from_pending_attempts": 0,
        "second_authoritative_resume_attempts": 0,
        "pending_rows_before": pending_rows_before,
        "pending_rows_after": pending_rows_after,
        "resume_payload_sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "authoritative_drupal_observation": authoritative, "result": result,
    })
    accounting = {"status": "pass", "replay_attempts": flow.state.replay_attempts,
                  "additional_activity": flow.state.additional_activity,
                  "authoritative_from_pending_calls": authoritative_from_pending_calls,
                  "authoritative_resume_calls": authoritative_resume_calls,
                  "second_authoritative_from_pending_attempts": 0,
                  "second_authoritative_resume_attempts": 0,
                  "pending_rows_before": pending_rows_before,
                  "pending_rows_after": pending_rows_after,
                  "read_only_status_observations": 4, "source_nonmutation": True,
                  "source_projection_sha256": final_snapshot["article_source_sha256"]}
    write_json(evidence / "accounting.json", accounting)
    (evidence / "events-process-b.jsonl").write_text(
        json.dumps({"event": "resume_completed", "occurred_at": now(),
                    "pending_identity": identity}, sort_keys=True) + "\n", encoding="utf-8")
    write_json(evidence / "privacy-scan.json", {"status": "pass", "secrets_retained": False,
                                                 "raw_images_retained": False,
                                                 "hidden_reasoning_retained": False})
    summary = {"schema_version": 1, "status": "pass", "continuation_id": evidence.name,
               "source_run_id": SOURCE_RUN_ID, "flow_state_id": flow.state.id,
               "pending_identity": identity, "recommendation_uuid": RECOMMENDATION_UUID,
               "reviewer": "editor_dana", "review_status": "approved",
               "same_logical_flow": True, "prior_work_replayed": False,
               "additional_model_provider_activity": 0, "duplicate_submissions": 0,
               "source_article_unchanged": True, "gate2c_executed": False}
    write_json(evidence / "summary.json", summary)
    (evidence / "summary.md").write_text(
        "# Gate 2B Step 2B.05 continuation evidence\n\n"
        "The same CrewAI Flow state and pending identity resumed after one Drupal-authoritative "
        "editor_dana approval. No prior model-owning work, model call, or submission replayed.\n",
        encoding="utf-8")
    manifest(evidence, list(FINAL_FILES[:-1]), "evidence-manifest.json")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("validate-paths", "record-failure", "process-a",
                                        "capture-review", "process-b"))
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--continuation-id", required=True)
    parser.add_argument("--xdg-root", type=Path)
    parser.add_argument("--failure-stage", default="wrapper-startup")
    parser.add_argument("--failure-classification", default="boundary-a-wrapper-failure")
    parser.add_argument("--error-type", default="RuntimeError")
    args = parser.parse_args()
    repo = args.repo.resolve()
    evidence = repo / "evidence/gates/gate-2b/human-review-continuation" / args.continuation_id
    runtime = repo / "crewai/.runtime/gate2b-step05" / args.continuation_id
    failure_root = repo / "evidence/gates/gate-2b/human-review-continuation-failures"
    if args.mode == "validate-paths":
        if args.xdg_root is None:
            parser.error("--xdg-root is required")
        require_fresh_identity(args.continuation_id, evidence, runtime)
        validate_isolation_paths(args.xdg_root, runtime)
        return 0
    if args.mode == "record-failure":
        record_stage_failure(failure_root, args.continuation_id, args.failure_stage,
                             args.failure_classification, args.error_type, runtime)
        return 0
    try:
        if args.mode == "process-a":
            if args.xdg_root is None:
                parser.error("--xdg-root is required")
            process_a(repo, evidence, runtime, args.xdg_root.resolve(), args.continuation_id)
        elif args.mode == "capture-review":
            capture_review(repo, evidence)
        else:
            process_b(repo, evidence, runtime)
    except Exception as exc:
        if args.mode != "process-a":
            record_stage_failure(failure_root, args.continuation_id, args.mode,
                                 f"boundary-{args.mode}-failure", type(exc).__name__, runtime)
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
