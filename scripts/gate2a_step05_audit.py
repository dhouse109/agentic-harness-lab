#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

BASE = "c61a40003e4ef236a9c0e72afc0befc55608b153"
GATE05_SHA = "99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a"
GATE1_SHA = "2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd"
GATE2A_SHA = "1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b"
ACTIVE_PACKAGE = "gate-2a-step05-langgraph-canonical-vertical-slice-v1.0.0"
NEXT_PACKAGE = "gate-2a-step06-langgraph-human-interrupt-and-review-resume-v1.0.0"
STEP04_LATEST = "evidence/gates/gate-2a/checkpoint-proof/gate2a-step04-20260810T034027Z-00250b07"
EVIDENCE_ROOT = "evidence/gates/gate-2a/canonical-slice"

REQUIRED_PASS_FILES = {
    "run-id.txt",
    "before-state.json",
    "during-state.json",
    "after-state.json",
    "targets.json",
    "context-before-model-summary.json",
    "prompt-metadata.json",
    "call-counters.json",
    "model-output.json",
    "model-output-schema-validation.json",
    "context-before-submit-summary.json",
    "recommendation.json",
    "recommendation-schema-validation.json",
    "validation.json",
    "submission.json",
    "status.json",
    "context-after-submit-summary.json",
    "state-after-slice.json",
    "checkpoint-config.json",
    "checkpoint-privacy.json",
    "tool-traces.json",
    "events.jsonl",
    "core-summary.json",
    "state-schema-validation.json",
    "runtime-db-sha256.txt",
    "seeded-clean-before.log",
    "seeded-clean-after.log",
    "secret-scan.log",
    "summary.json",
    "summary.md",
    "package-files-sha256.txt",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"[ERROR] {message}")


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def check_frozen(repo: Path) -> None:
    require(sha256(repo / "shared/contracts/GATE05-SUBSTRATE-FREEZE.json") == GATE05_SHA, "Gate 0.5 freeze changed")
    require(sha256(repo / "shared/contracts/GATE1-DRUPAL-AI-FREEZE.json") == GATE1_SHA, "Gate 1 freeze changed")
    require(sha256(repo / "shared/contracts/GATE2A-LANGGRAPH-BATCH-CONTRACT.json") == GATE2A_SHA, "Gate 2A contract changed")


def check_sources(repo: Path) -> None:
    required = [
        "docs/gates/GATE-2A-STEP05-LANGGRAPH-CANONICAL-VERTICAL-SLICE.md",
        "langchain/agentic_harness_langgraph/vertical_slice.py",
        "scripts/gate2a_step05_audit.py",
        "scripts/gate2a_step05_finalize.py",
        "scripts/gate2a_step05_state.py",
        "scripts/run-gate2a-step05.sh",
    ]
    for rel in required:
        require((repo / rel).is_file(), f"Installed Step 2A.05 file missing: {rel}")

    vertical = (repo / "langchain/agentic_harness_langgraph/vertical_slice.py").read_text(encoding="utf-8")
    for needle in [
        'MODEL_ID = "gpt-4.1-mini-2025-04-14"',
        "TEMPERATURE = 0.0",
        'PROMPT_VERSION = "langgraph-alt-text-v1.0.0"',
        'VALIDATOR_VERSION = "gate05-validator-1.0.0"',
        "max_retries=0",
        'method="json_schema"',
        "strict=True",
        'StateGraph(LangGraphRunState)',
        "SqliteSaver.from_conn_string",
        'result = tools[name].invoke(payload)',
        '"submit_recommendation"',
        '"get_recommendation_status"',
    ]:
        require(needle in vertical, f"Vertical-slice implementation missing invariant: {needle}")
    require(vertical.count("model.invoke(") == 1, "Vertical-slice source must contain exactly one model.invoke call site")


def check_step04_integrity(repo: Path) -> None:
    protected = [
        "docs/gates/GATE-2A-STEP04-LANGGRAPH-STATE-AND-SQLITE-CHECKPOINT-PROOF.md",
        "langchain/agentic_harness_langgraph/state.py",
        "scripts/gate2a_step04_audit.py",
        "scripts/gate2a_step04_finalize.py",
        "scripts/gate2a_step04_process1.py",
        "scripts/gate2a_step04_process2.py",
        "scripts/gate2a_step04_state.py",
        "scripts/run-gate2a-step04.sh",
    ]
    for rel in protected:
        require(git(repo, "diff", "--quiet", BASE, "--", rel).returncode == 0, f"Step 2A.04 protected file changed: {rel}")

    root = repo / "evidence/gates/gate-2a/checkpoint-proof"
    latest = root / "GATE2A-STEP04-LATEST.txt"
    require(latest.is_file(), "Step 2A.04 LATEST pointer missing")
    require(latest.read_text(encoding="utf-8").strip() == STEP04_LATEST, "Step 2A.04 LATEST pointer changed")
    run_dir = repo / STEP04_LATEST
    manifest = run_dir / "package-files-sha256.txt"
    require(manifest.is_file(), "Step 2A.04 evidence manifest missing")
    for row in manifest.read_text(encoding="utf-8").splitlines():
        digest, name = row.split("  ", 1)
        path = run_dir / name
        require(path.is_file(), f"Step 2A.04 evidence file missing: {name}")
        require(sha256(path) == digest, f"Step 2A.04 evidence checksum changed: {name}")


def check_docs(repo: Path, state: str, run_rel: str | None) -> None:
    docs = {
        "AGENTS": (repo / "AGENTS.md").read_text(encoding="utf-8"),
        "PLAN": (repo / "PLAN.md").read_text(encoding="utf-8"),
        "README": (repo / "README.md").read_text(encoding="utf-8"),
        "CURRENT": (repo / "docs/CURRENT-STATUS.md").read_text(encoding="utf-8"),
    }
    if state == "active":
        require(f"**Active package:** `{ACTIVE_PACKAGE}`." in docs["AGENTS"], "AGENTS active package missing")
        require(f"```text\n{ACTIVE_PACKAGE}\n```" in docs["PLAN"], "PLAN active package missing")
        require(f"- **Active package:** `{ACTIVE_PACKAGE}`." in docs["README"], "README active package missing")
        require(f"- **Active package:** `{ACTIVE_PACKAGE}`." in docs["CURRENT"], "CURRENT active package missing")
        require("- [ ] Step 2A.05 — LangGraph canonical vertical slice" in docs["PLAN"], "PLAN Step 2A.05 must remain unchecked while active")
        require("Step 2A.06" in docs["AGENTS"] and "Do not generate Step 2A.06" in docs["AGENTS"], "AGENTS Step 2A.06 guard missing")
    else:
        require(run_rel is not None, "Complete state requires accepted run path")
        line = f"Accepted Step 2A.05 evidence run: `{run_rel}`"
        require("**Step 2A.05:** complete." in docs["AGENTS"] and line in docs["AGENTS"], "AGENTS Step 2A.05 completion missing")
        require("**Completed Step 2A.05 package:**" in docs["PLAN"] and line in docs["PLAN"], "PLAN Step 2A.05 completion missing")
        require("- [x] Step 2A.05 — LangGraph canonical vertical slice" in docs["PLAN"], "PLAN Step 2A.05 checkbox not complete")
        require(f"`{NEXT_PACKAGE}`" in docs["AGENTS"] and f"`{NEXT_PACKAGE}`" in docs["README"] and f"`{NEXT_PACKAGE}`" in docs["CURRENT"], "Step 2A.06 next-package marker missing")
        require(line in docs["README"] and line in docs["CURRENT"], "Accepted Step 2A.05 evidence marker missing")


def check_manifest(run_dir: Path) -> None:
    manifest = run_dir / "package-files-sha256.txt"
    require(manifest.is_file(), "Candidate evidence manifest missing")
    seen: set[str] = set()
    for row in manifest.read_text(encoding="utf-8").splitlines():
        digest, name = row.split("  ", 1)
        path = run_dir / name
        require(path.is_file(), f"Candidate manifest file missing: {name}")
        require(sha256(path) == digest, f"Candidate evidence checksum mismatch: {name}")
        seen.add(name)
    expected = REQUIRED_PASS_FILES - {"package-files-sha256.txt"}
    actual = {p.name for p in run_dir.iterdir() if p.is_file() and p.name != "package-files-sha256.txt"}
    require(seen == expected, f"Candidate manifest coverage differs: expected={sorted(expected)} observed={sorted(seen)}")
    require(actual == expected, f"Candidate retained-file set differs: expected={sorted(expected)} actual={sorted(actual)}")


def check_evidence(repo: Path, run_dir: Path) -> None:
    for name in REQUIRED_PASS_FILES:
        require((run_dir / name).is_file(), f"Required candidate evidence missing: {name}")
    check_manifest(run_dir)

    summary = load(run_dir / "summary.json")
    require(summary.get("status") == "pass", "Candidate summary is not pass")
    require(summary.get("framework") == "langgraph", "Candidate framework differs")
    require(summary.get("canonical_target_sequence") == 1, "Candidate target sequence differs")
    require(summary.get("model_call_count") == 1, "Candidate model call count differs")
    require(summary.get("automatic_model_retries") == 0, "Candidate automatic retry count differs")
    require(summary.get("semantic_retry_loop_performed") is False, "Candidate semantic retry loop occurred")
    require(summary.get("drupal_semantic_call_count") == 6, "Candidate Drupal semantic call count differs")
    require(summary.get("recommendation_write_count") == 1, "Candidate recommendation write count differs")
    require(summary.get("recommendation_status") == "pending", "Candidate recommendation status differs")
    require(summary.get("source_article_mutation_performed") is False, "Candidate source mutation flag differs")
    require(summary.get("automatic_publication_performed") is False, "Candidate publication flag differs")
    require(summary.get("drupal_restored_to_seeded_clean") is True, "Candidate did not restore seeded clean")
    require(summary.get("source_context_stable_across_model_and_submission") is True, "Candidate source freshness proof differs")
    require(summary.get("checkpoint_backend") == "sqlite", "Candidate checkpoint backend differs")
    require(summary.get("checkpoint_next_target_index") == 1, "Candidate checkpoint next index differs")
    require(summary.get("checkpoint_completed_sequences") == [1], "Candidate checkpoint completed sequence differs")
    require(summary.get("checkpoint_privacy_pass") is True, "Candidate checkpoint privacy differs")
    require(summary.get("human_review_performed") is False, "Human review occurred in Step 2A.05")
    require(summary.get("continuation_boundary_exercised") is False, "Continuation boundary exercised in Step 2A.05")
    require(summary.get("gate2c_failure_injection_exercised") is False, "Gate2C seam exercised in Step 2A.05")

    state = load(run_dir / "state-after-slice.json")
    require(state.get("status") == "running", "One-target specimen state must remain running")
    require(state.get("next_target_index") == 1, "Specimen next target index differs")
    require([x.get("sequence") for x in state.get("completed_target_identities", [])] == [1], "Specimen completed sequence differs")

    runtime_rel = summary.get("runtime_db_relative_path")
    if isinstance(runtime_rel, str):
        runtime = repo / runtime_rel
        if runtime.is_file():
            require(sha256(runtime) == summary.get("runtime_db_sha256"), "Present runtime DB hash differs from retained evidence")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--document-state", choices=["active", "complete"], required=True)
    ap.add_argument("--run-dir")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    require(git(repo, "merge-base", "--is-ancestor", BASE, "HEAD").returncode == 0, "Merged Step 2A.04 baseline is not in ancestry")
    check_frozen(repo)
    check_sources(repo)
    check_step04_integrity(repo)

    run_dir: Path | None = None
    run_rel: str | None = None
    if args.run_dir:
        run_dir = Path(args.run_dir)
        if not run_dir.is_absolute():
            run_dir = repo / run_dir
        run_dir = run_dir.resolve()
        run_rel = str(run_dir.relative_to(repo))
    elif args.document_state == "complete":
        pointer = repo / EVIDENCE_ROOT / "GATE2A-STEP05-LATEST.txt"
        require(pointer.is_file(), "Accepted Step 2A.05 LATEST pointer missing")
        run_rel = pointer.read_text(encoding="utf-8").strip()
        run_dir = (repo / run_rel).resolve()

    check_docs(repo, args.document_state, run_rel if args.document_state == "complete" else None)
    if run_dir is not None:
        check_evidence(repo, run_dir)

    print("[PASS] Gate 2A Step 2A.05 audit passed.")
    if run_rel:
        print(f"[PASS] Evidence: {run_rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
