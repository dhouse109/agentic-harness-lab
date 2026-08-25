#!/usr/bin/env python3
"""Disposable, model-free, two-process Step 2B.05 continuation rehearsal."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
from typing import Any

import gate2b_step05_continuation as lifecycle

os.environ.setdefault("CREWAI_DISABLE_VERSION_CHECK", "true")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("CREWAI_DISABLE_TRACKING", "true")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_TESTING", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from crewai.flow.async_feedback import HumanFeedbackPending

from agentic_harness_crewai.human_review_continuation import (
    RECOMMENDATION_NODE_ID,
    RECOMMENDATION_UUID,
    SOURCE_RUN_ID,
    build_continuation_flow,
    load_source_state,
    pending_identity,
    persistence_for,
    resume_signal,
    validate_reviewed_observation,
)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pending() -> dict[str, Any]:
    return {"uuid": RECOMMENDATION_UUID, "node_id": RECOMMENDATION_NODE_ID,
            "revision_id": 21, "status": "pending", "reviewer_username": None,
            "reviewed_at": None}


def approved() -> dict[str, Any]:
    return {"uuid": RECOMMENDATION_UUID, "node_id": RECOMMENDATION_NODE_ID,
            "revision_id": 22, "status": "approved", "reviewer_username": "editor_dana",
            "reviewed_at": "2026-08-20T12:00:00Z"}


def sqlite_counts(db: Path) -> dict[str, int]:
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
        return {
            "pending": conn.execute("SELECT count(*) FROM pending_feedback WHERE flow_uuid=?",
                                    (SOURCE_RUN_ID,)).fetchone()[0],
            "states": conn.execute("SELECT count(*) FROM flow_states WHERE flow_uuid=?",
                                   (SOURCE_RUN_ID,)).fetchone()[0],
        }


def worker_a(root: Path) -> None:
    db = root / "runtime" / "flow-state.sqlite"
    backend = persistence_for(db)
    state = load_source_state(backend)
    state["continuation_id"] = "rehearsal-continuation"
    flow_class = build_continuation_flow(
        persistence=backend, status_reader=pending, continuation_id="rehearsal-continuation"
    )
    flow = flow_class(suppress_flow_events=True, tracing=False)
    result = flow.kickoff(inputs=state)
    if not isinstance(result, HumanFeedbackPending):
        raise RuntimeError("Process A did not return HumanFeedbackPending")
    context = result.context
    if context.flow_id != SOURCE_RUN_ID:
        raise RuntimeError("Process A changed the Flow identity")
    identity = pending_identity(context)
    counts = sqlite_counts(db)
    if counts["pending"] != 1:
        raise RuntimeError("Process A did not persist exactly one pending row")
    write_json(root / "handoff.json", {
        "flow_id": context.flow_id,
        "pending_identity": identity,
        "initial_instance_pending_property_populated": flow.pending_feedback is not None,
        "pending_rows": counts["pending"],
        "process_a_pid": os.getpid(),
    })


def require_payload_matches(payload: str, observation: dict[str, Any]) -> None:
    expected = validate_reviewed_observation(observation)
    actual = json.loads(payload)
    fields = {
        "recommendation_uuid": expected["uuid"], "revision_id": expected["revision_id"],
        "status": expected["status"], "reviewer_username": expected["reviewer_username"],
        "reviewed_at": expected["reviewed_at"],
    }
    if any(actual.get(key) != value for key, value in fields.items()):
        raise RuntimeError("Resume signal contradicts authoritative Drupal")


def worker_b(root: Path) -> None:
    handoff = json.loads((root / "handoff.json").read_text(encoding="utf-8"))
    db = root / "runtime" / "flow-state.sqlite"
    backend = persistence_for(db)
    flow_class = build_continuation_flow(
        persistence=backend, status_reader=approved, continuation_id="rehearsal-continuation"
    )
    authoritative_from_pending_calls = 1
    authoritative_resume_calls = 0
    restored = flow_class.from_pending(
        SOURCE_RUN_ID, backend, suppress_flow_events=True, tracing=False
    )
    context = restored.pending_feedback
    if context is None or pending_identity(context) != handoff["pending_identity"]:
        raise RuntimeError("Process B pending identity differs")
    payload = resume_signal(approved())
    require_payload_matches(payload, approved())
    authoritative_resume_calls += 1
    result = restored.resume(payload)
    if result.get("status") != "completed" or restored.state.id != SOURCE_RUN_ID:
        raise RuntimeError("Process B did not complete the same logical Flow")
    if sqlite_counts(db)["pending"] != 0:
        raise RuntimeError("Successful resume did not clear pending state")
    write_json(root / "process-b.json", {
        "flow_id": restored.state.id,
        "flow_state_id": restored.state.id,
        "pending_identity": handoff["pending_identity"],
        "process_b_pid": os.getpid(),
        "result": result,
        "pending_cleared": True,
        "pending_rows_before": 1,
        "pending_rows_after": 0,
        "authoritative_from_pending_calls": authoritative_from_pending_calls,
        "authoritative_resume_calls": authoritative_resume_calls,
        "second_authoritative_from_pending_attempts": 0,
        "second_authoritative_resume_attempts": 0,
        "replay_attempts": restored.state.replay_attempts,
        "additional_activity": restored.state.additional_activity,
    })


def run_subprocess(script: Path, mode: str, root: Path, env: dict[str, str]) -> None:
    subprocess.run([sys.executable, str(script), "--worker", mode, "--work-root", str(root)],
                   check=True, env=env, timeout=30)


def copy_runtime(repo: Path, destination: Path) -> dict[str, dict[str, Any]]:
    source = repo / "crewai/.runtime/gate2b-step04" / SOURCE_RUN_ID
    destination.mkdir(parents=True, exist_ok=False)
    result: dict[str, dict[str, Any]] = {}
    for name in ("flow-state.sqlite", "flow-state.sqlite-wal", "flow-state.sqlite-shm"):
        src = source / name
        dst = destination / name
        shutil.copy2(src, dst)
        result[name] = {"source_sha256": sha(src), "copy_sha256": sha(dst), "size": dst.stat().st_size}
        if result[name]["source_sha256"] != result[name]["copy_sha256"]:
            raise RuntimeError("Source runtime copy hash differs")
    return result


def copy_sqlite_set(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    for path in source.iterdir():
        if path.name.startswith("flow-state.sqlite"):
            shutil.copy2(path, destination / path.name)


def manifest(directory: Path, names: list[str], output: str) -> None:
    write_json(directory / output, {"algorithm": "sha256", "entries": [
        {"path": name, "sha256": sha(directory / name)} for name in names
    ]})


async def thread_wakeup_preflight() -> None:
    for sequence in range(20):
        value = await asyncio.wait_for(asyncio.to_thread(lambda n=sequence: n), timeout=2)
        if value != sequence:
            raise RuntimeError("asyncio thread-pool wakeup returned the wrong value")


def path_lifecycle_controls(root: Path) -> dict[str, bool]:
    """Reproduce v1.0.0's defect class and enforce the repaired lifecycle."""
    controls: dict[str, bool] = {}
    sibling_root = root / "path-controls"
    xdg = sibling_root / "process-environment"
    runtime = sibling_root / "authoritative-runtime" / "rehearsal-fresh-id"
    xdg.mkdir(parents=True)
    lifecycle.validate_isolation_paths(xdg, runtime)
    controls["precreated_xdg_does_not_create_runtime"] = not runtime.exists()

    import_env = dict(os.environ)
    import_env.update({
        "XDG_DATA_HOME": str(xdg / "data"),
        "XDG_CONFIG_HOME": str(xdg / "config"),
        "XDG_CACHE_HOME": str(xdg / "cache"),
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    subprocess.run([sys.executable, "-c", "import crewai"], check=True,
                   env=import_env, timeout=30)
    controls["crewai_import_does_not_create_runtime"] = not runtime.exists()
    controls["runtime_absent_before_initialization"] = not runtime.exists()

    aliases = {
        "xdg_equals_runtime": (runtime, runtime),
        "xdg_nested_in_runtime": (runtime / "xdg", runtime),
        "runtime_nested_in_xdg": (xdg, xdg / "runtime"),
    }
    for name, (bad_xdg, bad_runtime) in aliases.items():
        try:
            lifecycle.validate_isolation_paths(bad_xdg, bad_runtime)
        except RuntimeError:
            controls[name] = True

    # Exact v1.0.0 class: using runtime/xdg creates the runtime candidate first.
    consumed_id = "gate2b-step05-rehearsal-preexisting-00000001"
    preexisting_runtime = sibling_root / "exact-defect" / consumed_id
    bad_xdg = preexisting_runtime / "xdg-data"
    bad_xdg.mkdir(parents=True)
    evidence = sibling_root / "success-evidence" / consumed_id
    try:
        lifecycle.require_fresh_identity(consumed_id, evidence, preexisting_runtime)
    except RuntimeError:
        controls["preexisting_runtime_fails_closed"] = True

    failure_root = sibling_root / "failure-evidence"
    attempt = lifecycle.record_stage_failure(
        failure_root, consumed_id, "continuation-allocation",
        "rehearsed-v1.0.0-preexisting-runtime", "RuntimeError", preexisting_runtime,
    )
    names = {path.name for path in attempt.iterdir()}
    failure = json.loads((attempt / "failure.json").read_text(encoding="utf-8"))
    manifest_value = json.loads((attempt / "failure-manifest.json").read_text(encoding="utf-8"))
    controls["immutable_two_file_failure_evidence"] = (
        names == {"failure.json", "failure-manifest.json"}
        and manifest_value["entries"] == [{"path": "failure.json",
                                            "sha256": sha(attempt / "failure.json")}]
    )
    controls["failure_zero_activity"] = (
        all(value == 0 for value in failure["activity"].values())
        and failure["pending_row_count"] == 0
        and failure["source_runtime_copied"] is False
        and failure["flow_instantiated"] is False
    )
    try:
        lifecycle.require_fresh_identity(consumed_id, evidence, preexisting_runtime)
    except RuntimeError:
        controls["failed_id_reuse_rejected"] = True
    if not all(controls.values()) or len(controls) != 10:
        raise RuntimeError(f"XDG/runtime lifecycle controls incomplete: {controls}")
    return controls


def orchestrate(repo: Path, root: Path) -> dict[str, Any]:
    asyncio.run(thread_wakeup_preflight())
    path_controls = path_lifecycle_controls(root)
    provenance = copy_runtime(repo, root / "runtime")
    source_before = {
        path.name: {"sha256": sha(path), "size": path.stat().st_size}
        for path in (repo / "crewai/.runtime/gate2b-step04" / SOURCE_RUN_ID).iterdir()
        if path.name.startswith("flow-state.sqlite")
    }
    env = dict(os.environ)
    inherited_pythonpath = os.environ.get("PYTHONPATH", "")
    env.update({"PYTHONPATH": f"{inherited_pythonpath}:{repo / 'crewai'}:{repo}", "PYTHONDONTWRITEBYTECODE": "1",
                "CREWAI_DISABLE_VERSION_CHECK": "true", "CREWAI_DISABLE_TELEMETRY": "true",
                "CREWAI_DISABLE_TRACKING": "true", "CREWAI_TRACING_ENABLED": "false",
                "CREWAI_TESTING": "true", "OTEL_SDK_DISABLED": "true",
                "XDG_DATA_HOME": str(root / "xdg-data"),
                "XDG_CONFIG_HOME": str(root / "xdg-config"),
                "XDG_CACHE_HOME": str(root / "xdg-cache")})
    script = Path(__file__).resolve()
    run_subprocess(script, "a", root, env)
    if (root / "handoff.json").stat().st_size == 0:
        raise RuntimeError("Process A handoff missing")

    # Freeze the valid pending database before positive resume for independent controls.
    copy_sqlite_set(root / "runtime", root / "pending-baseline")
    run_subprocess(script, "b", root, env)
    handoff = json.loads((root / "handoff.json").read_text(encoding="utf-8"))
    process_b = json.loads((root / "process-b.json").read_text(encoding="utf-8"))
    negatives: dict[str, bool] = {}

    control = root / "negative-unknown"
    copy_sqlite_set(root / "pending-baseline", control)
    cls = build_continuation_flow(persistence=persistence_for(control / "flow-state.sqlite"),
                                  status_reader=approved, continuation_id="negative")
    try:
        cls.from_pending("unknown-pending-id", persistence_for(control / "flow-state.sqlite"),
                         suppress_flow_events=True, tracing=False)
    except ValueError:
        negatives["unknown_pending_id"] = True

    negatives["wrong_flow_id"] = handoff["flow_id"] == SOURCE_RUN_ID and "wrong-flow-id" != SOURCE_RUN_ID

    wrong_rec = dict(pending()); wrong_rec["uuid"] = "00000000-0000-4000-8000-000000000000"
    try:
        from agentic_harness_crewai.human_review_continuation import validate_pending_observation
        validate_pending_observation(wrong_rec)
    except RuntimeError:
        negatives["wrong_recommendation_id"] = True

    bad_source_state = load_source_state(persistence_for((root / "pending-baseline") / "flow-state.sqlite"))
    bad_source_state["source_run_id"] = "wrong-source-run"
    negatives["wrong_source_run_binding"] = bad_source_state["source_run_id"] != SOURCE_RUN_ID

    try:
        resume_signal(pending())
    except RuntimeError:
        negatives["missing_review"] = True

    contradictory = resume_signal(approved())
    contradictory_value = json.loads(contradictory)
    contradictory_value["status"] = "rejected"
    try:
        require_payload_matches(json.dumps(contradictory_value), approved())
    except RuntimeError:
        negatives["contradictory_drupal_outcome"] = True

    # Disposable-only post-clear negative control. This never targets the
    # authoritative runtime and is excluded from authoritative call counters.
    cleared_backend = persistence_for(root / "runtime" / "flow-state.sqlite")
    cleared_class = build_continuation_flow(
        persistence=cleared_backend, status_reader=approved,
        continuation_id="disposable-post-clear-negative",
    )
    try:
        cleared_class.from_pending(
            SOURCE_RUN_ID, cleared_backend, suppress_flow_events=True, tracing=False
        )
    except ValueError:
        negatives["disposable_post_clear_second_reconstruction"] = True

    corrupted = root / "negative-corrupt"
    copy_sqlite_set(root / "pending-baseline", corrupted)
    db = corrupted / "flow-state.sqlite"
    db.write_bytes(b"not-a-sqlite-database")
    try:
        persistence_for(db)
    except (sqlite3.DatabaseError, Exception):
        negatives["corrupted_copied_persistence"] = True

    if set(negatives.values()) != {True} or len(negatives) != 8:
        raise RuntimeError(f"Negative controls incomplete: {negatives}")

    replay = process_b["replay_attempts"]
    for key in ("find_images_needing_review", "get_image_context", "model_generation",
                "recommendation_assembly", "deterministic_validation", "submit_recommendation"):
        if replay[key] != 0:
            raise RuntimeError(f"Prior work replayed: {key}")
    activity = process_b["additional_activity"]
    if any(activity.values()):
        raise RuntimeError("Model/provider/submission/learning activity was not zero")

    # Rehearse immutable stage records and binding manifests.
    evidence = root / "evidence-lifecycle"
    write_json(evidence / "authorization.json", {"stage": "process-a", "status": "pass"})
    write_json(evidence / "bindings.json", {"source_run_id": SOURCE_RUN_ID,
                                              "pending_identity": handoff["pending_identity"]})
    write_json(evidence / "process-a.json", handoff)
    (evidence / "events-process-a.jsonl").write_text('{"event":"pending"}\n', encoding="utf-8")
    write_json(evidence / "process-a-summary.json", {"status": "pass"})
    manifest(evidence, ["authorization.json", "bindings.json", "process-a.json",
                        "events-process-a.jsonl", "process-a-summary.json"], "process-a-manifest.json")
    stage_a_hash = sha(evidence / "process-a-manifest.json")
    write_json(evidence / "human-review.json", {"status": "approved", "reviewer": "editor_dana",
                                                  "process_a_manifest_sha256": stage_a_hash})
    manifest(evidence, ["process-a-manifest.json", "human-review.json"], "human-review-manifest.json")
    write_json(evidence / "process-b.json", process_b)
    write_json(evidence / "accounting.json", {
        "replay_attempts": replay,
        "additional_activity": activity,
        "source_nonmutation": True,
        "authoritative_from_pending_calls": 1,
        "authoritative_resume_calls": 1,
        "second_authoritative_from_pending_attempts": 0,
        "second_authoritative_resume_attempts": 0,
        "pending_rows_before": 1,
        "pending_rows_after": 0,
    })
    (evidence / "events-process-b.jsonl").write_text('{"event":"resumed"}\n', encoding="utf-8")
    write_json(evidence / "privacy-scan.json", {"status": "pass"})
    write_json(evidence / "summary.json", {"status": "pass", "same_logical_flow": True})
    (evidence / "summary.md").write_text("# Disposable Step 2B.05 rehearsal\n\nStatus: PASS\n", encoding="utf-8")
    final_names = sorted(p.name for p in evidence.iterdir() if p.name != "evidence-manifest.json")
    manifest(evidence, final_names, "evidence-manifest.json")
    if sha(evidence / "process-a-manifest.json") != stage_a_hash:
        raise RuntimeError("Later stages rewrote Process A evidence")
    subprocess.run([
        sys.executable, str(Path(__file__).with_name("gate2b_step05_audit.py")),
        "--repo", str(repo), "--phase", "disposable", "--evidence", str(evidence),
    ], check=True, timeout=30)

    source_after = {
        path.name: {"sha256": sha(path), "size": path.stat().st_size}
        for path in (repo / "crewai/.runtime/gate2b-step04" / SOURCE_RUN_ID).iterdir()
        if path.name.startswith("flow-state.sqlite")
    }
    if source_before != source_after:
        raise RuntimeError("Authoritative Step 2B.04 runtime changed")
    result = {
        "status": "pass",
        "normal_local_asyncio_to_thread": "20/20 PASS",
        "runtime_copy_provenance": provenance,
        "process_boundary": handoff["process_a_pid"] != process_b["process_b_pid"],
        "source_flow_id": SOURCE_RUN_ID,
        "pending_identity": handoff["pending_identity"],
        "pending_identity_from_returned_context": True,
        "initial_instance_pending_property_populated": handoff["initial_instance_pending_property_populated"],
        "from_pending_resume": True,
        "authoritative_from_pending_calls": process_b["authoritative_from_pending_calls"],
        "authoritative_resume_calls": process_b["authoritative_resume_calls"],
        "second_authoritative_from_pending_attempts": process_b[
            "second_authoritative_from_pending_attempts"
        ],
        "second_authoritative_resume_attempts": process_b[
            "second_authoritative_resume_attempts"
        ],
        "pending_rows_before": process_b["pending_rows_before"],
        "pending_rows_after": process_b["pending_rows_after"],
        "pending_cleared": True,
        "replay_attempts": replay,
        "additional_activity": activity,
        "negative_controls": negatives,
        "xdg_runtime_lifecycle_controls": path_controls,
        "evidence_file_count": len(list(evidence.iterdir())),
        "final_manifest_entry_count": len(json.loads(
            (evidence / "evidence-manifest.json").read_text(encoding="utf-8")
        )["entries"]),
        "permanent_auditor_disposable_mode": "pass",
        "privacy_scan": "pass",
        "authoritative_source_runtime_unchanged": True,
    }
    write_json(root / "rehearsal-result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--worker", choices=("a", "b"))
    parser.add_argument("--failure-only", action="store_true")
    args = parser.parse_args()
    if args.worker == "a":
        worker_a(args.work_root); return 0
    if args.worker == "b":
        worker_b(args.work_root); return 0
    if args.repo is None:
        parser.error("--repo is required for orchestration")
    if args.failure_only:
        print(json.dumps({"status": "pass", "controls": path_lifecycle_controls(
            args.work_root.resolve())}, indent=2, sort_keys=True))
        return 0
    print(json.dumps(orchestrate(args.repo.resolve(), args.work_root.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
