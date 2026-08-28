#!/usr/bin/env python3
"""Lifecycle-correct permanent audit for Gate 2B Step 2B.07."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from gate2b_step07_synthesis import (
    BASE, CLAIMS, FEATURE, HASHES, PACKAGE, POINTER, PREDECESSOR,
    SUCCESS_RUN, need, sha, verify_documents, verify_predecessor_hashes,
)

CONSUMED_RUN = "gate2b-step07-20260828T135201Z-1ed07bea"
CONSUMED_REL = f"evidence/gates/gate-2b/evidence-synthesis/{CONSUMED_RUN}"
CONSUMED_HASHES = {
    "claim-proof-map.json": "ac2595be175c19dc8d7c5adae77289bc1f452cce8418bc4ff30d2e5c2d5ff0aa",
    "comparison-synthesis.json": "4f51548da036d74db4cab939bbfe2c417b453fb6f3bcf93453334e8330cddb1d",
    "evidence-manifest.json": "1b0e55e7ba32130b18d2756135125b82b2994274c2743a73acb73839f92be708",
    "privacy-scan.json": "3c4180e2068351828b3010aa580f11a7a5a7e398153762fc49e59cf0f6c3f635",
    "summary.json": "b9517af014e247d415fecb74ecccc0654b7b854d8b635662a4c30c011a5f82bb",
}

GATE2A_STEP09_MERGE = "f3daab20509c72aebf8536bcb7742f1a3e9f504f"
GATE2A_FEATURE = "1a32f8584a75dc59533f48dfb0b7636da94d5a00"
GATE2A_CERT_MERGE = "0477e882987501438ae07fbb51e741b4be800843"
GATE2A_FREEZE = "shared/contracts/GATE2A-LANGGRAPH-FREEZE.json"
GATE2A_FREEZE_SHA = "a28361c34b9d1c2089eee786324ad34cffbf54e3495f59a276c489865e5630f0"
GATE2A_MUTABLE_LATER = ["CLAIMS_REGISTER.md", "COMPARISON_MATRIX.md", "SOURCES.md"]
GATE2A_FROZEN_ROOTS = [
    "evidence/gates/gate-2a",
    "evidence/results/langgraph/langgraph-20260810T231915Z-0027cd3e",
]
GATE2A_FROZEN_FILES = [
    "shared/contracts/GATE05-SUBSTRATE-FREEZE.json",
    "shared/contracts/GATE1-DRUPAL-AI-FREEZE.json",
    "shared/contracts/GATE2A-LANGGRAPH-BATCH-CONTRACT.json",
    GATE2A_FREEZE,
    "scripts/gate2a_step10_audit.py",
    "docs/gates/GATE-2A-STEP10-LANGGRAPH-CERTIFICATION-FREEZE-AND-CREWAI-HANDOFF.md",
    "docs/handoffs/GATE-2A-TO-CREWAI-HANDOFF.md",
]

SNAPSHOT = "drupal/.ddev/db_snapshots/gate2b-step06-post-step2b05-recovery-20260826T152003Z-mariadb_11.8.zst"
SNAPSHOT_SHA = "4ba4cece2d30a5f90699afdf9a2ab2094f0d902213c66cdc0b40dfa466094906"
SNAPSHOT_SIZE = 4_112_532
LOCK_SHA = "855e5edff2cb86eb64ea9856d239b19010e7d3b1f80c40e370ed81d66b8e4e7c"


def command(command_line: list[str], repo: Path, *, expect_success: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{repo / 'scripts'}:{repo / 'crewai'}:{repo}" + (f":{existing}" if existing else "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for key in ["OPENAI_API_KEY", "OPENAI_CANDIDATE_MODEL", "CREWAI_CANDIDATE_MODEL"]:
        env.pop(key, None)
    with tempfile.TemporaryDirectory(prefix="gate2b-step07-xdg-") as temp:
        for name in ["data", "cache"]:
            (Path(temp) / name).mkdir()
        env["XDG_DATA_HOME"] = str(Path(temp) / "data")
        env["XDG_CACHE_HOME"] = str(Path(temp) / "cache")
        completed = subprocess.run(
            command_line, cwd=repo, env=env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    if expect_success:
        need(completed.returncode == 0, f"command failed: {' '.join(command_line)}\n{completed.stdout[-3000:]}")
    return completed


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def git_bytes(repo: Path, commit: str, rel: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{rel}"])


def verify_ancestry(repo: Path) -> None:
    parents = git(repo, "show", "-s", "--format=%P", BASE).split()
    need(parents == [PREDECESSOR, FEATURE], "Step 2B.06 normal-merge parent binding drift")
    need(subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", BASE, "HEAD"]).returncode == 0,
         "Step 2B.06 merge is not an ancestor of HEAD")


def verify_snapshot(repo: Path) -> None:
    path = repo / SNAPSHOT
    need(path.is_file() and not path.is_symlink(), "retained Step 2B.06 snapshot missing or unsafe")
    need(path.stat().st_size == SNAPSHOT_SIZE, "retained snapshot size drift")
    need(sha(path) == SNAPSHOT_SHA, "retained snapshot hash drift")


def verify_dependency(repo: Path) -> None:
    need(sha(repo / "crewai/uv.lock") == LOCK_SHA, "CrewAI lock drift")
    versions = (repo / "VERSIONS.md").read_text()
    for needle in ["3.12.13", "1.15.10"]:
        need(needle in versions, f"version pin absent: {needle}")


def verify_consumed_identity(repo: Path, evidence: Path) -> None:
    expected = (repo / CONSUMED_REL).resolve()
    need(evidence.resolve() == expected, "different Step 2B.07 synthesis identity rejected")
    need(evidence.is_dir() and not evidence.is_symlink(), "consumed synthesis family missing or unsafe")
    names = {p.name for p in evidence.iterdir() if p.is_file()}
    need(names == set(CONSUMED_HASHES), f"consumed synthesis file set drift: {sorted(names)}")
    for name, expected_sha in CONSUMED_HASHES.items():
        need(sha(evidence / name) == expected_sha, f"consumed synthesis byte drift: {name}")


def verify_manifest(run: Path) -> None:
    manifest = json.loads((run / "evidence-manifest.json").read_text())
    entries = manifest.get("entries", [])
    expected = set(CONSUMED_HASHES) - {"evidence-manifest.json"}
    need(len(entries) == 4 and {row.get("path") for row in entries} == expected, "evidence manifest shape drift")
    for row in entries:
        path = run / row["path"]
        need(row.get("sha256") == sha(path), f"manifest hash mismatch: {row['path']}")
        need(row.get("size") == path.stat().st_size, f"manifest size mismatch: {row['path']}")


def verify_family(repo: Path, run: Path) -> None:
    verify_manifest(run)
    summary = json.loads((run / "summary.json").read_text())
    expected_status = {row[0]: row[1] for row in CLAIMS}
    need(summary.get("package") == PACKAGE and summary.get("status") == "pass", "summary package/status drift")
    need(summary.get("run_id") == CONSUMED_RUN and summary.get("predecessor_merge") == BASE, "summary identity/predecessor drift")
    need(summary.get("successful_crewai_run") == SUCCESS_RUN, "summary successful run drift")
    for field in ["model_generations", "provider_requests", "provider_responses", "drupal_writes",
                  "recommendation_submissions", "human_reviews", "snapshot_operations", "new_crewai_runtimes"]:
        need(summary.get(field) == 0, f"nonzero Step 2B.07 activity: {field}")
    need(summary.get("predecessor_evidence_rewritten") is False, "predecessor rewrite recorded")
    need(summary.get("gate2b_certified") is False and summary.get("step2b08_started") is False, "Step 2B.08 boundary crossed")
    need(summary.get("gate2c_executed") is False and summary.get("privacy") == "pass", "Gate 2C/privacy status drift")

    claim_map = json.loads((run / "claim-proof-map.json").read_text())
    rows = {row.get("claim_id"): row for row in claim_map.get("claims", [])}
    need(set(rows) == set(expected_status), "claim/proof map claim set drift")
    for claim_id, status in expected_status.items():
        row = rows[claim_id]
        need(row.get("claim_strength") == status, f"claim strength drift: {claim_id}")
        need(row.get("comparison_safe_wording") and row.get("prohibited_overstatement"), f"claim guard absent: {claim_id}")
        proof = row.get("evidence", [])
        need(proof, f"claim proof missing: {claim_id}")
        for binding in proof:
            rel = binding.get("path")
            need(rel in HASHES and binding.get("sha256") == HASHES[rel], f"claim proof binding drift: {claim_id}")
            need(sha(repo / rel) == HASHES[rel], f"retained claim proof byte drift: {claim_id}")
        if status == "verified":
            need(row.get("official_source_ids"), f"verified claim source missing: {claim_id}")
        if status == "architecture/probe":
            need("Do not promote" in row.get("prohibited_overstatement", ""), "architecture/probe promotion guard absent")
        if status == "gate-2c-deferred":
            need("No shared recovery conclusion" in row.get("prohibited_overstatement", ""), "Gate 2C guard absent")

    synthesis = json.loads((run / "comparison-synthesis.json").read_text())
    need(synthesis.get("organs") == ["context", "tools", "state", "verification", "human-review", "lifecycle"], "six-organ set drift")
    need(synthesis.get("shared_controls_held") is True and synthesis.get("false_symmetry_avoided") is True, "comparison controls drift")
    need(synthesis.get("gate2c_status") == "DEFERRED_UNCLAIMED", "Gate 2C status drift")
    for field in ["recovery_winner_claimed", "production_readiness_claimed", "framework_superiority_claimed"]:
        need(synthesis.get(field) is False, f"prohibited comparison claim: {field}")
    need(synthesis.get("langgraph_privacy_failure_and_salvage_preserved") is True, "LangGraph privacy history flattened")
    need(synthesis.get("crewai_http_failure_and_disposition_preserved") is True, "CrewAI failure history flattened")

    privacy = json.loads((run / "privacy-scan.json").read_text())
    need(privacy.get("status") == "pass" and privacy.get("prohibited_value_hits") == 0, "privacy result failed")
    for field in ["credentials_retained", "raw_image_or_data_url_retained", "private_database_content_retained", "hidden_reasoning_retained"]:
        need(privacy.get(field) is False, f"privacy field failed: {field}")
    combined = "\n".join((run / name).read_text() for name in sorted(CONSUMED_HASHES))
    for marker in ["sk-proj-", "Authorization: Basic ", "Authorization: Bearer ", "data:image/", "OPENAI_API_KEY="]:
        need(marker not in combined, "protected value pattern in synthesis family")


def expected_current_gate2a_document_failure(repo: Path) -> None:
    completed = command(["python3", str(repo / "scripts/gate2a_step10_audit.py"), "--repo", str(repo)], repo, expect_success=False)
    need(completed.returncode != 0, "historical Gate 2A.10 auditor unexpectedly accepted current mutable documents")
    need("Step 2A.10 changed CLAIMS_REGISTER.md" in completed.stdout, "unexpected current Gate 2A.10 failure classification")


def historical_gate2a_certification(repo: Path, commit: str = GATE2A_CERT_MERGE) -> None:
    with tempfile.TemporaryDirectory(prefix="gate2a-certified-boundary-") as temp_name:
        temp = Path(temp_name)
        checkout = temp / "repo"
        command(["git", "clone", "--shared", "--no-hardlinks", str(repo), str(checkout)], temp)
        command(["git", "checkout", "--detach", commit], checkout)
        need(git(checkout, "rev-parse", "HEAD") == commit, "historical Gate 2A checkout drift")
        if commit == GATE2A_CERT_MERGE:
            need(git(checkout, "show", "-s", "--format=%P", commit).split() == [GATE2A_STEP09_MERGE, GATE2A_FEATURE],
                 "Gate 2A certification merge parents drift")
        completed = command(["python3", str(checkout / "scripts/gate2a_step10_audit.py"), "--repo", str(checkout)], checkout, expect_success=False)
        need(completed.returncode == 0, f"historical Gate 2A certification invalid at {commit}:\n{completed.stdout[-3000:]}")
        need("Gate 2A Step 2A.10 certification/freeze audit passed" in completed.stdout, "historical Gate 2A PASS marker absent")


def frozen_paths(repo: Path) -> list[str]:
    listed = git(repo, "ls-tree", "-r", "--name-only", GATE2A_CERT_MERGE, "--", *GATE2A_FROZEN_ROOTS, *GATE2A_FROZEN_FILES)
    return [line for line in listed.splitlines() if line]


def current_gate2a_preservation(repo: Path) -> None:
    need(subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", GATE2A_CERT_MERGE, "HEAD"]).returncode == 0,
         "Gate 2A certification merge is not an ancestor")
    need(sha(repo / GATE2A_FREEZE) == GATE2A_FREEZE_SHA, "Gate 2A freeze SHA drift")
    paths = frozen_paths(repo)
    need(len(paths) == 245, f"Gate 2A certified frozen path count drift: {len(paths)}")
    for rel in paths:
        path = repo / rel
        need(path.is_file() and not path.is_symlink(), f"Gate 2A frozen path missing or unsafe: {rel}")
        need(path.read_bytes() == git_bytes(repo, GATE2A_CERT_MERGE, rel), f"Gate 2A frozen evidence drift: {rel}")
    for root in GATE2A_FROZEN_ROOTS:
        current = {p.relative_to(repo).as_posix() for p in (repo / root).rglob("*") if p.is_file()}
        historical = {p for p in paths if p == root or p.startswith(root + "/")}
        need(current == historical, f"Gate 2A frozen root file-set drift: {root}")
    for rel in GATE2A_MUTABLE_LATER:
        need((repo / rel).read_bytes() != git_bytes(repo, GATE2A_STEP09_MERGE, rel), f"later mutable document did not evolve: {rel}")


def step2b06_composite(repo: Path) -> None:
    py = repo / "crewai/.venv/bin/python"
    success = repo / f"evidence/results/crewai/{SUCCESS_RUN}"
    supplement = repo / f"evidence/gates/gate-2b/frozen-batch-governance-supplement/{SUCCESS_RUN}/gate2b-step06-governance-supplement-v103"
    final_governance = repo / f"evidence/gates/gate-2b/frozen-batch-final-governance/{SUCCESS_RUN}/gate2b-step06-final-governance-v104"
    command([str(py), str(repo / "scripts/gate2b_step06_audit.py"), "--repo", str(repo), "--mode", "final-composite",
             "--evidence", str(success), "--supplement", str(supplement), "--final-governance", str(final_governance)], repo)


def resolve_evidence(repo: Path, evidence_arg: str | None, mode: str) -> Path:
    pointer = repo / POINTER
    if mode in {"candidate", "recovery"}:
        need(not pointer.exists(), "authoritative Step 2B.07 pointer exists before repaired acceptance")
        need(evidence_arg is not None, "existing consumed synthesis evidence is required")
        evidence = Path(evidence_arg)
    else:
        need(pointer.is_file() and not pointer.is_symlink(), "accepted Step 2B.07 pointer missing")
        need(pointer.read_text().strip() == CONSUMED_REL, "Step 2B.07 pointer identity drift")
        evidence = repo / pointer.read_text().strip()
        if evidence_arg is not None:
            need(Path(evidence_arg).resolve() == evidence.resolve(), "explicit evidence differs from accepted pointer")
    if not evidence.is_absolute():
        evidence = repo / evidence
    verify_consumed_identity(repo, evidence)
    return evidence


def full_audit(repo: Path, evidence: Path) -> None:
    verify_ancestry(repo)
    verify_predecessor_hashes(repo)
    verify_snapshot(repo)
    verify_dependency(repo)
    verify_documents(repo)
    verify_family(repo, evidence)
    expected_current_gate2a_document_failure(repo)
    historical_gate2a_certification(repo)
    current_gate2a_preservation(repo)
    step2b06_composite(repo)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--evidence")
    ap.add_argument("--mode", choices=["candidate", "recovery", "permanent", "historical-gate2a", "gate2a-preservation"], default="permanent")
    args = ap.parse_args()
    repo = Path(args.repo).resolve()
    if args.mode == "historical-gate2a":
        expected_current_gate2a_document_failure(repo)
        historical_gate2a_certification(repo)
        print("[PASS] Historical Gate 2A certification is valid at its own lifecycle boundary.")
        print("[PASS] Its mutable-document predicate correctly rejects the current Step 2B.07 descendant.")
        return
    if args.mode == "gate2a-preservation":
        current_gate2a_preservation(repo)
        print("[PASS] Current descendant preserves all 245 certified Gate 2A frozen paths.")
        return
    evidence = resolve_evidence(repo, args.evidence, args.mode)
    full_audit(repo, evidence)
    label = args.mode
    print(f"[PASS] Gate 2B Step 2B.07 lifecycle-correct {label} audit passed.")
    print("[PASS] Existing synthesis accepted without rerun; every promoted claim has exact retained proof.")
    print("[PASS] Gate 2C remains DEFERRED_UNCLAIMED.")
    print(f"[PASS] Evidence: {CONSUMED_REL}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"[FAIL] {exc}")
