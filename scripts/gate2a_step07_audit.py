#!/usr/bin/env python3
"""Permanent/static audit for Gate 2A Step 2A.07."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

BASELINE = "f6abc3ea40926a32dfc154fc7828ac75656d2e4f"
PACKAGE = "gate-2a-step07-langgraph-batch-runner-v1.0.5"
NEXT = "gate-2a-step08-langgraph-fresh-batch-and-continuation-v1.0.0"
CONTRACT_SHA = "1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b"
GATE1_SHA = "2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd"
GATE05_SHA = "99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a"
STEP06 = "evidence/gates/gate-2a/human-interrupt/gate2a-step06-20260810T162448Z-002692eb"
ROOT_REL = "evidence/gates/gate-2a/batch-runner"
RETAINED_IMPORT_FAILURE = "evidence/gates/gate-2a/batch-runner/gate2a-step07-20260810T184229Z-00271f73"
SOURCE_PATHS = [
    "docs/gates/GATE-2A-STEP07-LANGGRAPH-BATCH-RUNNER.md",
    "docs/decisions/ADR-0011-langgraph-batch-evidence-schema-instantiation.md",
    "langchain/agentic_harness_langgraph/batch_runner.py",
    "scripts/gate2a_step07_schema_instantiations.py",
    "scripts/gate2a_step07_schema_validate.py",
    "scripts/gate2a_step07_audit.py",
    "scripts/gate2a_step07_state.py",
    "scripts/run-gate2a-step07-langgraph-batch-runner.sh",
]


def require(ok: bool, message: str) -> None:
    if not ok:
        raise SystemExit(f"[ERROR] {message}")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=repo, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def audit_source(repo: Path, document_state: str) -> None:
    require(sha(repo / "shared/contracts/GATE05-SUBSTRATE-FREEZE.json") == GATE05_SHA, "Gate 0.5 freeze changed")
    require(sha(repo / "shared/contracts/GATE1-DRUPAL-AI-FREEZE.json") == GATE1_SHA, "Gate 1 freeze changed")
    require(sha(repo / "shared/contracts/GATE2A-LANGGRAPH-BATCH-CONTRACT.json") == CONTRACT_SHA, "Gate 2A frozen contract changed")

    version_check = run(repo, str(repo / "langchain/.venv/bin/python"), "-c",
        'import importlib.metadata as m,sys,json; print(json.dumps({"python":".".join(map(str,sys.version_info[:3])),"langchain":m.version("langchain"),"langgraph":m.version("langgraph"),"langgraph-checkpoint-sqlite":m.version("langgraph-checkpoint-sqlite")},sort_keys=True))')
    require(version_check.returncode == 0, f"Pinned runtime version probe failed:\n{version_check.stdout}")
    require(json.loads(version_check.stdout) == {"python":"3.12.13","langchain":"1.3.14","langgraph":"1.2.10","langgraph-checkpoint-sqlite":"3.1.1"}, "Pinned LangGraph runtime versions differ")
    schema_probe = subprocess.run(
        [
            str(repo / "crewai/.venv/bin/python"),
            "-c",
            'import importlib.metadata as m,json,sys; from jsonschema import Draft202012Validator,FormatChecker; print(json.dumps({"python":".".join(map(str,sys.version_info[:3])),"jsonschema":m.version("jsonschema")},sort_keys=True))',
        ],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(
        schema_probe.returncode == 0,
        f"Repository schema-validation Python probe failed:\nstdout={schema_probe.stdout}\nstderr={schema_probe.stderr}",
    )
    try:
        schema_info = json.loads(schema_probe.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"[ERROR] Repository schema-validation Python probe emitted non-JSON stdout: {schema_probe.stdout!r}; stderr={schema_probe.stderr!r}"
        ) from exc
    require(schema_info.get("python") == "3.12.13", "Repository schema-validation Python version differs")
    require(isinstance(schema_info.get("jsonschema"), str) and schema_info["jsonschema"], "Repository jsonschema version is unavailable")

    contract = load(repo / "shared/contracts/GATE2A-LANGGRAPH-BATCH-CONTRACT.json")
    require(contract.get("status") == "frozen", "Gate 2A contract is not frozen")
    constants = contract.get("frozen_constants", {})
    require(constants.get("failure_after_sequence") == 6, "Frozen continuation-after seam differs")
    require(constants.get("failure_before_sequence") == 7, "Frozen continuation-before seam differs")
    require(constants.get("resume_at_sequence") == 7, "Frozen resume sequence differs")
    require(constants.get("expected_duplicate_count") == 0, "Frozen duplicate expectation differs")
    calls = contract.get("model_call_policy", {})
    require(calls.get("step_2A_07") == 0 and calls.get("step_2A_08") == 12, "Step 2A.07/2A.08 model-call policy differs")
    require(contract.get("continuation_policy", {}).get("do_not_conflate_gate2a_with_gate2c") is True, "Gate 2A/Gate 2C boundary differs")

    for rel in SOURCE_PATHS:
        require((repo / rel).is_file(), f"Missing Step 2A.07 source: {rel}")

    latest06 = repo / "evidence/gates/gate-2a/human-interrupt/GATE2A-STEP06-LATEST.txt"
    require(latest06.is_file() and latest06.read_text(encoding="utf-8").strip() == STEP06, "Accepted Step 2A.06 pointer differs")
    summary06 = load(repo / STEP06 / "summary.json")
    require(summary06.get("status") == "pass", "Accepted Step 2A.06 summary is not pass")
    require(summary06.get("same_run_thread_resumed") is True and summary06.get("model_call_count") == 0, "Accepted Step 2A.06 resume/model proof differs")

    schema_check = run(repo, str(repo / "crewai/.venv/bin/python"), "scripts/gate2a_step07_schema_instantiations.py", "--repo", str(repo), "--check")
    require(schema_check.returncode == 0, f"Derived schema audit failed:\n{schema_check.stdout}")
    mapping = load(repo / "shared/contracts/GATE2A-LANGGRAPH-EVIDENCE-SCHEMA-MAP.json")
    require(mapping.get("frozen_contract_changed") is False and mapping.get("prior_evidence_invalidated") is False, "Schema map changes frozen contract or invalidates evidence")
    require(mapping.get("controlled_continuation_semantics_preserved") is True, "Schema map does not preserve controlled continuation semantics")
    require(mapping.get("gate2c_failure_semantics_introduced") is False, "Schema map conflates Gate 2A continuation with Gate 2C failure")
    require(mapping.get("frozen_gate2a_contract_sha256") == CONTRACT_SHA, "Schema map contract digest differs")
    require(len(mapping.get("schemas", [])) == 11, "Derived schema map must contain exactly 11 frozen batch schema instantiations")
    kinds = {item.get("transformation_kind") for item in mapping.get("schemas", [])}
    require("controlled-continuation-event-adaptation" in kinds, "Event schema lacks controlled-continuation adaptation")
    require("controlled-continuation-recovery-adaptation" in kinds, "Recovery schema lacks controlled-continuation adaptation")

    batch = (repo / "langchain/agentic_harness_langgraph/batch_runner.py").read_text(encoding="utf-8")
    for token in (
        "TARGET_COUNT = 12",
        "BOUNDARY_AFTER_SEQUENCE = 6",
        "RESUME_AT_SEQUENCE = 7",
        "StateGraph(LangGraphRunState)",
        "SqliteSaver",
        "interrupt({",
        "Command(resume={\"continue_after_sequence\": 6})",
        "max_retries=0",
        "semantic_retry_loop_performed",
        "find_images_needing_review",
        "get_image_context",
        "submit_recommendation",
        "get_recommendation_status",
        "gate2c_failure_injection_fired",
        "construction_test",
        "live_run",
        "validate_events",
        "checkpoint_privacy",
        "continuation_interrupted",
        "controlled_stop_after_sequence",
        "validate_resume_boundary",
        "midpoint call counters differ",
        "Live midpoint Drupal semantic call counters differ",
        "Live completed Drupal semantic call counters differ",
        'write_json(evidence / "run.json", state)',
    ):
        require(token in batch, f"Batch runner control missing: {token}")
    require("for sequence in range(1, TARGET_COUNT + 1)" in batch, "12-node deterministic graph construction is missing")
    require("builder.add_edge(\"target_06\", \"continuation_boundary\")" in batch, "Target 6 does not lead to continuation boundary")
    require("builder.add_edge(\"continuation_boundary\", \"target_07\")" in batch, "Continuation boundary does not resume at target 7")
    require('"failure_seam_observed": True' not in batch, "Live runner falsely labels controlled continuation as a failure seam")
    require('"failure_after_sequence"' not in batch and '"completed_before_failure"' not in batch, "Live runner retains Gate 1 failure-only recovery vocabulary")
    require('append_event(events_path, {"event":' not in batch, "Live events use the old non-schema event shape")

    shell = (repo / "scripts/run-gate2a-step07-langgraph-batch-runner.sh").read_text(encoding="utf-8")
    for command in ("verify)", "certify)", "audit)"):
        require(command in shell, f"Step 2A.07 shell command missing: {command}")
    require("OPENAI_API_KEY" in shell and "must be unset" in shell, "Step 2A.07 shell does not block model access")
    require("--mode construction-test" in shell, "Step 2A.07 shell does not use construction-test mode")
    require("--mode start" not in shell and "--mode resume" not in shell, "Step 2A.07 shell exposes live batch execution")
    require("GATE2A-STEP07-LAST-RUN.txt" in shell and "GATE2A-STEP07-FAILED-RUNS.txt" in shell, "Step 2A.07 failure-history controls are missing")
    require("GATE2A-STEP07-RETRY-AUTHORIZED.txt" in shell, "Step 2A.07 one-shot retry authorization control is missing")
    require("A prior Step 2A.07 verification failed" in shell, "Step 2A.07 does not block an unreviewed rerun after failure")
    require('PYTHONPATH="$REPO/langchain:$REPO' in shell, "Step 2A.07 wrapper does not expose repository-local package imports")
    require("Consumed one-shot retry authorization" in shell, "Step 2A.07 wrapper does not consume retry authorization")

    joined = "\n".join((repo / rel).read_text(encoding="utf-8") for rel in SOURCE_PATHS)
    for pattern in (
        r"api[_-]?key\s*[:=]\s*['\"][^'\"]+",
        r"Authorization\s*:\s*Bearer\s+[A-Za-z0-9._-]+",
        r"data:image/[^;]+;base64,[A-Za-z0-9+/=]{32,}",
    ):
        require(re.search(pattern, joined, re.I) is None, f"Prohibited retained source pattern: {pattern}")


    # Preserve and verify the reviewed model-free import-path failure that triggered v1.0.5.
    retained = repo / RETAINED_IMPORT_FAILURE
    require(retained.is_dir(), f"Retained Step 2A.07 import-path failure missing: {RETAINED_IMPORT_FAILURE}")
    failed_state = load(retained / "failed-state.json")
    require(failed_state.get("status") == "failed", "Retained Step 2A.07 failure status differs")
    require(failed_state.get("model_call_count") == 0, "Retained Step 2A.07 failure unexpectedly used model calls")
    require(failed_state.get("drupal_semantic_call_count") == 0, "Retained Step 2A.07 failure unexpectedly used Drupal")
    require(failed_state.get("recommendation_write_count") == 0, "Retained Step 2A.07 failure unexpectedly wrote recommendations")
    manifest = retained / "package-files-sha256.txt"
    require(manifest.is_file(), "Retained Step 2A.07 failure manifest missing")
    manifest_check = subprocess.run(["sha256sum", "-c", manifest.name], cwd=retained, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    require(manifest_check.returncode == 0, f"Retained Step 2A.07 failure manifest failed:\n{manifest_check.stdout}")

    docs = {
        "AGENTS.md": (repo / "AGENTS.md").read_text(encoding="utf-8"),
        "PLAN.md": (repo / "PLAN.md").read_text(encoding="utf-8"),
        "README.md": (repo / "README.md").read_text(encoding="utf-8"),
        "docs/CURRENT-STATUS.md": (repo / "docs/CURRENT-STATUS.md").read_text(encoding="utf-8"),
    }
    if document_state == "active":
        require(f"**Active package:** `{PACKAGE}`" in docs["AGENTS.md"], "AGENTS active package marker missing")
        require("**Step 2A.07:** active" in docs["AGENTS.md"], "AGENTS Step 2A.07 active marker missing")
        require(f"**Active Step 2A.07 package:**" in docs["PLAN.md"] and PACKAGE in docs["PLAN.md"], "PLAN active Step 2A.07 marker missing")
        require(f"- **Active package:** `{PACKAGE}`." in docs["README.md"], "README active package marker missing")
        require(f"- **Active package:** `{PACKAGE}`." in docs["docs/CURRENT-STATUS.md"], "CURRENT active package marker missing")
        require("Step 2A.08 remains locked" in docs["docs/CURRENT-STATUS.md"], "CURRENT does not keep Step 2A.08 locked")
    else:
        require("**Step 2A.07:** complete." in docs["AGENTS.md"], "AGENTS Step 2A.07 complete marker missing")
        require(f"**Completed package:** `{PACKAGE}`" in docs["AGENTS.md"], "AGENTS completed package marker missing")
        require("- [x] Step 2A.07 — LangGraph batch runner" in docs["PLAN.md"], "PLAN checklist does not complete Step 2A.07")
        require(f"- **Completed package:** `{PACKAGE}`." in docs["README.md"], "README completed package marker missing")
        require(f"- **Completed package:** `{PACKAGE}`." in docs["docs/CURRENT-STATUS.md"], "CURRENT completed package marker missing")


def audit_candidate(repo: Path, rel: str) -> None:
    path = repo / rel
    require(path.is_dir(), f"Step 2A.07 candidate directory missing: {rel}")
    summary = load(path / "summary.json")
    require(summary.get("status") == "pass", "Construction summary is not pass")
    require(summary.get("proof_scope") == "step2a07-model-free-batch-runner-construction", "Construction proof scope differs")
    require(summary.get("target_count") == 12, "Construction target count differs")
    require(summary.get("target_sequence_sha256") == "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728", "Construction target hash differs")
    require(summary.get("completed_before_continuation") == [1, 2, 3, 4, 5, 6], "Construction first half differs")
    require(summary.get("resumed_at_sequence") == 7, "Construction resume sequence differs")
    require(summary.get("completed_after_resume") == [7, 8, 9, 10, 11, 12], "Construction second half differs")
    require(summary.get("completed_sequences") == list(range(1, 13)), "Construction completed sequence differs")
    require(summary.get("duplicate_count") == 0, "Construction duplicate count differs")
    require(summary.get("same_run_thread_resumed") is True, "Construction same-thread resume is false")
    require(summary.get("genuine_langgraph_interrupt_persisted") is True, "Construction genuine interrupt is false")
    require(summary.get("checkpoint_schema_validation_pass") is True, "Construction state schema validation is false")
    require(summary.get("derived_collection_schema_validation", {}).get("langgraph-batch-event.schema.json") == "pass", "Construction event schema validation is missing")
    require(summary.get("derived_collection_schema_validation", {}).get("langgraph-batch-recovery.schema.json") == "pass", "Construction continuation/recovery schema validation is missing")
    require(summary.get("model_call_count") == 0, "Step 2A.07 construction used a model call")
    require(summary.get("drupal_semantic_call_count") == 0 and summary.get("recommendation_write_count") == 0, "Step 2A.07 construction used Drupal")
    require(summary.get("gate2c_failure_injection_exercised") is False, "Construction exercised Gate 2C")
    require(summary.get("live_step2a08_batch_executed") is False, "Construction executed Step 2A.08 live batch")
    manifest = path / "package-files-sha256.txt"
    require(manifest.is_file(), "Construction evidence manifest missing")
    check = subprocess.run(["sha256sum", "-c", manifest.name], cwd=path, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    require(check.returncode == 0, f"Construction evidence manifest failed:\n{check.stdout}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--document-state", choices=("active", "complete"), required=True)
    args = ap.parse_args()
    repo = Path(args.repo).resolve()
    audit_source(repo, args.document_state)

    root = repo / ROOT_REL
    candidate_ptr = root / "GATE2A-STEP07-CANDIDATE.txt"
    latest_ptr = root / "GATE2A-STEP07-LATEST.txt"
    if candidate_ptr.exists():
        audit_candidate(repo, candidate_ptr.read_text(encoding="utf-8").strip())
    if args.document_state == "complete":
        require(latest_ptr.is_file(), "Step 2A.07 LATEST pointer missing")
        latest = latest_ptr.read_text(encoding="utf-8").strip()
        audit_candidate(repo, latest)
        require(candidate_ptr.is_file() and candidate_ptr.read_text(encoding="utf-8").strip() == latest, "Candidate/LATEST pointers differ")
    print("[PASS] Gate 2A Step 2A.07 audit passed.")
    if latest_ptr.exists():
        print(f"[PASS] Evidence: {latest_ptr.read_text(encoding='utf-8').strip()}")
    elif candidate_ptr.exists():
        print(f"[PASS] Candidate: {candidate_ptr.read_text(encoding='utf-8').strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
