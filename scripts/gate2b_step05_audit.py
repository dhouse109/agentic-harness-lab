#!/usr/bin/env python3
"""Permanent auditor for Gate 2B Step 2B.05."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


PREDECESSOR = "c61d0b0213d754fcc40f18065836de6e0da70d2c"
SOURCE_RUN_ID = "crewai-20260818T215017Z-8e03fc95"
RECOMMENDATION_UUID = "1878ae86-834c-4813-9134-4c3b8d0833c9"
FAILED_V100_ID = "gate2b-step05-20260820T151225Z-8b7fa221"
LOCK_SHA = "855e5edff2cb86eb64ea9856d239b19010e7d3b1f80c40e370ed81d66b8e4e7c"
CANONICAL = {
    "evidence-manifest.json": "c6115ffea4b7ceefb7858e6b482713fc92998dcf2bde7bc6de8831d583665aaf",
    "summary.json": "5cd324d26b866c83d9728e7634887bcf3ccc46c2df5f4fc6a9563069f71ef490",
}
CLOSURE = {
    "evidence-manifest.json": "d62ababa96b223643ab23e3d67c75b3fcc2bb325a8a3e69787fff870cc56583b",
    "summary.json": "e482aa166485ea97c0698b82dade0cfdadbe9947fb06aa2ce0d59c9a3cc87f01",
}
SOURCE_RUNTIME = {
    "flow-state.sqlite": ("d0fd3ac373b6af0aace07b7eed6813ebea28ceab37ab47265da2da94a24acff2", 45056),
    "flow-state.sqlite-wal": ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", 0),
    "flow-state.sqlite-shm": ("fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb", 32768),
}
REQUIRED = (
    "crewai/agentic_harness_crewai/human_review_continuation.py",
    "docs/gates/GATE-2B-STEP05-CREWAI-DRUPAL-AUTHORITATIVE-HUMAN-REVIEW-CONTINUATION.md",
    "shared/schemas/gate2b-step05-continuation-evidence.schema.json",
    "scripts/gate2b_step05_continuation.py", "scripts/gate2b_step05_rehearsal.py",
    "scripts/gate2b_step05_audit.py",
    "scripts/run-gate2b-step05-crewai-drupal-authoritative-human-review-continuation.sh",
)
FINAL_FILES = {
    "authorization.json", "bindings.json", "process-a.json", "events-process-a.jsonl",
    "process-a-summary.json", "process-a-manifest.json", "human-review.json",
    "human-review-manifest.json", "process-b.json", "accounting.json",
    "events-process-b.jsonl", "privacy-scan.json", "summary.json", "summary.md",
    "evidence-manifest.json",
}


def need(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_manifest(root: Path, name: str) -> None:
    value = load(root / name)
    need(value.get("algorithm") == "sha256", f"{name} algorithm differs")
    for entry in value.get("entries", []):
        path = root / entry["path"]
        need(path.is_file() and sha(path) == entry["sha256"], f"{name} entry differs: {entry['path']}")


def audit_failure_attempts(repo: Path) -> None:
    root = repo / "evidence/gates/gate-2b/human-review-continuation-failures"
    if not root.exists():
        return
    for attempt in sorted(path for path in root.glob("*/*") if path.is_dir()):
        need({path.name for path in attempt.iterdir()} == {"failure.json", "failure-manifest.json"},
             f"Failure-attempt file set differs: {attempt}")
        verify_manifest(attempt, "failure-manifest.json")
        failure = load(attempt / "failure.json")
        required = {"schema_version", "status", "retrospective", "continuation_id",
                    "stage_attempt_id", "stage", "captured_at", "predecessor_sha",
                    "source_run_id", "recommendation", "failure_classification",
                    "failure_point", "error_type", "authoritative_runtime_created",
                    "source_runtime_copied", "flow_instantiated", "pending_row_count",
                    "activity", "source_or_drupal_authoritative_state_mutation_claimed",
                    "cleanup_or_rollback", "retained_runtime", "privacy"}
        need(set(failure) == required, f"Failure-attempt schema differs: {attempt}")
        need(failure.get("status") == "failed"
             and failure.get("predecessor_sha") == PREDECESSOR
             and failure.get("source_run_id") == SOURCE_RUN_ID
             and failure.get("source_or_drupal_authoritative_state_mutation_claimed") is False
             and failure.get("privacy", {}).get("status") == "pass"
             and failure.get("privacy", {}).get("secrets_retained") is False,
             f"Failure-attempt privacy/boundary fields differ: {attempt}")
        need(all(value == 0 for value in failure.get("activity", {}).values()),
             f"Failure attempt contains prohibited activity: {attempt}")


def audit_historical_failed_runtime(repo: Path) -> None:
    root = repo / "crewai/.runtime/gate2b-step05" / FAILED_V100_ID
    need(root.is_dir(), "Retained v1.0.0 failed continuation path is missing")
    relative = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
    need(relative == ["xdg-data", "xdg-data/gate-2b-step05-crewai-drupal-authoritative-human-review-continuation-v1.0.0"],
         "Retained v1.0.0 failed continuation path contents drifted")
    need(not any(path.is_file() or path.is_symlink() for path in root.rglob("*")),
         "Retained v1.0.0 failed continuation unexpectedly contains files")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, text=True,
                          capture_output=True).stdout.strip()


def audit_static(repo: Path) -> None:
    need(git(repo, "merge-base", "--is-ancestor", PREDECESSOR, "HEAD") == "",
         "Step 2B.04 predecessor is not an ancestor")
    need(sha(repo / "crewai/uv.lock") == LOCK_SHA, "CrewAI lock drifted")
    for path in REQUIRED:
        need((repo / path).is_file(), f"Required Step 2B.05 path missing: {path}")
    canonical = repo / "evidence/gates/gate-2b/canonical-slice" / SOURCE_RUN_ID
    closure = repo / "evidence/gates/gate-2b/canonical-slice-closure/gate2b-step04-closure-20260819T195009Z-60344274"
    for name, expected in CANONICAL.items():
        need(sha(canonical / name) == expected, f"Step 2B.04 canonical {name} drifted")
    for name, expected in CLOSURE.items():
        need(sha(closure / name) == expected, f"Step 2B.04 closure {name} drifted")
    source = repo / "crewai/.runtime/gate2b-step04" / SOURCE_RUN_ID
    for name, (digest, size) in SOURCE_RUNTIME.items():
        need(sha(source / name) == digest and (source / name).stat().st_size == size,
             f"Authoritative runtime drifted: {name}")
    text = (repo / REQUIRED[0]).read_text(encoding="utf-8")
    for prohibited in ("CheckpointConfig", "_skip_auto_memory", "submit_recommendation(",
                       "find_images_needing_review(", "get_image_context(", "LLM("):
        need(prohibited not in text, f"Continuation-only source contains prohibited path: {prohibited}")
    for required in ("@human_feedback", "HumanFeedbackPending", "from_pending", "resume"):
        combined = text + (repo / "scripts/gate2b_step05_continuation.py").read_text(encoding="utf-8")
        need(required in combined, f"Supported public continuation token missing: {required}")
    runner = (repo / "scripts/gate2b_step05_continuation.py").read_text(encoding="utf-8")
    wrapper = (repo / REQUIRED[-1]).read_text(encoding="utf-8")
    for token in ("validate_isolation_paths", "FAILED_V100_CONTINUATION_ID",
                  "human-review-continuation-failures", "record_stage_failure"):
        need(token in runner, f"Repair lifecycle token missing: {token}")
    need("/tmp/gate2b-step05-xdg-" in wrapper
         and 'normal_local_environment "$runtime"' not in wrapper,
         "Wrapper does not separate disposable XDG from continuation runtime")
    tree = ast.parse(runner)
    process_b = next(node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name == "process_b")
    from_pending_calls = sum(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and node.func.attr == "from_pending" for node in ast.walk(process_b)
    )
    resume_calls = sum(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and node.func.attr == "resume" for node in ast.walk(process_b)
    )
    need(from_pending_calls == 1, "Authoritative Process B must contain one from_pending call")
    need(resume_calls == 1, "Authoritative Process B must contain one resume call")
    need("second_resume_rejected" not in runner,
         "Authoritative Process B retains the disposable-only negative control")
    audit_historical_failed_runtime(repo)
    audit_failure_attempts(repo)


def audit_stage_a(repo: Path, evidence: Path) -> None:
    audit_static(repo)
    verify_manifest(evidence, "process-a-manifest.json")
    bindings = load(evidence / "bindings.json")
    process = load(evidence / "process-a.json")
    auth = load(evidence / "authorization.json")
    need(bindings.get("source_run_id") == SOURCE_RUN_ID
         and bindings.get("flow_state_id") == SOURCE_RUN_ID
         and bindings.get("recommendation_uuid") == RECOMMENDATION_UUID,
         "Process A source/Flow/recommendation binding differs")
    need(process.get("status") == "pending" and process.get("process_a_exited_cleanly") is True,
         "Process A pending boundary is invalid")
    need(process.get("pending_identity_source") == "returned HumanFeedbackPending.context.to_dict()",
         "Pending identity did not come from returned public context")
    zero = auth.get("counts", {})
    need(all(value == 0 for value in zero.values()), "Process A authorization counts are not zero")
    replay = process.get("replay_attempts", {})
    for key in ("find_images_needing_review", "get_image_context", "model_generation",
                "recommendation_assembly", "deterministic_validation", "submit_recommendation"):
        need(replay.get(key) == 0, f"Prior work replayed during Process A: {key}")


def audit_final(repo: Path, evidence: Path) -> None:
    audit_stage_a(repo, evidence)
    need({p.name for p in evidence.iterdir()} == FINAL_FILES, "Final evidence file set differs")
    verify_manifest(evidence, "human-review-manifest.json")
    verify_manifest(evidence, "evidence-manifest.json")
    review, process_b, accounting, summary = [load(evidence / name) for name in
        ("human-review.json", "process-b.json", "accounting.json", "summary.json")]
    need(review.get("authority") == "Drupal" and review.get("reviewer") == "editor_dana"
         and review.get("action") == "approve-as-is"
         and review.get("prior_revision_id") == 21
         and review.get("decision_revision_id") == 22,
         "Drupal reviewer/revision lineage differs")
    need(process_b.get("from_pending") is True and process_b.get("resume") is True
         and process_b.get("flow_state_id") == SOURCE_RUN_ID
         and process_b.get("pending_identity") == load(evidence / "process-a.json")["pending_identity"]
         and process_b.get("pending_cleared") is True
         and process_b.get("authoritative_from_pending_calls") == 1
         and process_b.get("authoritative_resume_calls") == 1
         and process_b.get("second_authoritative_from_pending_attempts") == 0
         and process_b.get("second_authoritative_resume_attempts") == 0
         and process_b.get("pending_rows_before") == 1
         and process_b.get("pending_rows_after") == 0,
         "Process B same-identity resume proof differs")
    for key, expected in {
        "authoritative_from_pending_calls": 1,
        "authoritative_resume_calls": 1,
        "second_authoritative_from_pending_attempts": 0,
        "second_authoritative_resume_attempts": 0,
        "pending_rows_before": 1,
        "pending_rows_after": 0,
    }.items():
        need(accounting.get(key) == expected, f"Process B accounting differs: {key}")
    for key in ("find_images_needing_review", "get_image_context", "model_generation",
                "recommendation_assembly", "deterministic_validation", "submit_recommendation"):
        need(accounting["replay_attempts"].get(key) == 0, f"Prior work replayed: {key}")
    need(all(value == 0 for value in accounting["additional_activity"].values()),
         "Additional model/provider/submission/learning activity is nonzero")
    need(accounting.get("source_nonmutation") is True, "Source nonmutation proof missing")
    need(load(evidence / "privacy-scan.json").get("status") == "pass", "Privacy scan failed")
    need(summary.get("status") == "pass" and summary.get("same_logical_flow") is True
         and summary.get("gate2c_executed") is False, "Final summary overclaims or differs")


def audit_disposable(evidence: Path) -> None:
    """Validate a disposable 15-file completion family without repository claims."""
    need({p.name for p in evidence.iterdir()} == FINAL_FILES,
         "Disposable final evidence file set differs")
    verify_manifest(evidence, "process-a-manifest.json")
    verify_manifest(evidence, "human-review-manifest.json")
    verify_manifest(evidence, "evidence-manifest.json")
    final_manifest = load(evidence / "evidence-manifest.json")
    need(len(final_manifest.get("entries", [])) == 14,
         "Disposable final manifest must hash exactly 14 files")
    process_b = load(evidence / "process-b.json")
    accounting = load(evidence / "accounting.json")
    for key, expected in {
        "authoritative_from_pending_calls": 1,
        "authoritative_resume_calls": 1,
        "second_authoritative_from_pending_attempts": 0,
        "second_authoritative_resume_attempts": 0,
        "pending_rows_before": 1,
        "pending_rows_after": 0,
    }.items():
        need(process_b.get(key) == expected, f"Disposable Process B differs: {key}")
        need(accounting.get(key) == expected, f"Disposable accounting differs: {key}")
    need(process_b.get("flow_state_id") == SOURCE_RUN_ID
         and process_b.get("pending_cleared") is True,
         "Disposable same-Flow pending clear proof differs")
    for key in ("find_images_needing_review", "get_image_context", "model_generation",
                "recommendation_assembly", "deterministic_validation", "submit_recommendation"):
        need(accounting["replay_attempts"].get(key) == 0, f"Disposable prior work replayed: {key}")
    need(all(value == 0 for value in accounting["additional_activity"].values()),
         "Disposable activity is nonzero")
    need(load(evidence / "privacy-scan.json").get("status") == "pass",
         "Disposable privacy scan failed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--phase", choices=("active", "stage-a", "permanent", "disposable"), required=True)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    try:
        if args.phase == "active":
            audit_static(args.repo.resolve())
        elif args.phase == "stage-a":
            need(args.evidence is not None, "--evidence is required")
            audit_stage_a(args.repo.resolve(), args.evidence.resolve())
        elif args.phase == "permanent":
            if args.evidence is None:
                latest = args.repo / "evidence/gates/gate-2b/human-review-continuation/LATEST"
                need(latest.is_file(), "Final Step 2B.05 LATEST pointer missing")
                evidence = latest.parent / latest.read_text().strip()
            else:
                evidence = args.evidence.resolve()
            audit_final(args.repo.resolve(), evidence)
        else:
            need(args.evidence is not None, "--evidence is required")
            audit_disposable(args.evidence.resolve())
    except Exception as exc:
        print(f"[FAIL] {exc}", file=sys.stderr); return 1
    print(f"[PASS] Gate 2B Step 2B.05 {args.phase} audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
