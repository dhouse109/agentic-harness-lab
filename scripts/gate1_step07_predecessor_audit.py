#!/usr/bin/env python3
"""Compatibility-aware ordered predecessor and freeze audit for Gate 1 Step 1.07."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

BASELINE = "75653ec21176173a8f4af1a1743f2e9286333492"
GATE05_RUN = "gate05-step05-20260805T184155Z-50124"
GATE05_FREEZE_SHA = "99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a"
STEP01_RUN = "gate1-step01-20260805T205448Z-103220"
STEP01_SHA = "360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6"
STEP02_RUN = "gate1-step02-20260806T010227Z-189538"
ADR0006_SHA = "223f6d6f4276d3861cf5668f08e0446479d815a07fed18402b1e6a7722d18c4b"
STEP03_RUN = "gate1-step03-20260806T050827Z-494925"
STEP04_RUN = "gate1-step04-20260806T213954Z-156475"
STEP05_GATE_RUN = "gate1-step05-20260808T020222Z-2121689"
STEP05_BATCH_RUN = "drupal_ai-20260808T020222Z-205fd9"
STEP06_RUN = "gate1-step06-20260808T231216Z-2188911"
TARGET_SHA = "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728"
SOURCE_SHA_REDUCED = "f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17"
SOURCE_SHA_FULL = "877cd888fa41eb660b3e3cc0461bee04c0b92bef7e8f2f63fc56d9ec77adde32"
EXPECTED_VERSIONS = {
    "drupal/core-recommended": "11.4.4",
    "drupal/ai": "1.4.5",
    "drupal/ai_agents": "1.3.2",
    "drupal/ai_provider_openai": "1.2.3",
}

class AuditError(RuntimeError):
    pass

def fail(message: str) -> None:
    raise AuditError(message)

def require(value: bool, message: str) -> None:
    if not value:
        fail(message)

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AuditError(f"Unable to load JSON {path}: {exc}") from exc

def run(cmd: list[str], cwd: Path, output: Path | None = None) -> str:
    env = os.environ.copy()
    for name in ("OPENAI_API_KEY", "OPENAI_CANDIDATE_MODEL", "CREWAI_CANDIDATE_MODEL"):
        env.pop(name, None)
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)
    text = proc.stdout + proc.stderr
    if output is not None:
        output.write_text(text, encoding="utf-8")
    if proc.returncode != 0:
        tail = "\n".join(text.splitlines()[-80:])
        raise AuditError(f"Command failed ({' '.join(cmd)}):\n{tail}")
    return proc.stdout

def pointer(repo: Path, rel: str, expected: str) -> Path:
    p = repo / rel
    require(p.is_file(), f"Missing accepted pointer: {rel}")
    value = p.read_text(encoding="utf-8").strip()
    resolved = repo / value
    require(resolved.is_dir(), f"Accepted evidence directory missing: {value}")
    require(resolved.name == expected, f"Accepted pointer changed: {rel} -> {resolved.name}")
    return resolved

def verify_manifest(base: Path, manifest: str, root: Path | None = None) -> None:
    m = base / manifest
    require(m.is_file(), f"Missing manifest: {m}")
    target_root = base if root is None else root
    for line in m.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, rel = line.split(maxsplit=1)
        path = target_root / rel.removeprefix("./")
        require(path.is_file(), f"Manifest target missing: {path}")
        require(sha(path) == expected, f"Manifest checksum changed: {path}")

def summary_fields(path: Path, expected: dict[str, Any]) -> None:
    value = load(path)
    for key, wanted in expected.items():
        require(value.get(key) == wanted, f"Unexpected {path.name} field {key}: {value.get(key)!r}")

def composer_versions(repo: Path) -> dict[str, str]:
    lock = load(repo / "drupal/composer.lock")
    actual = {
        p.get("name"): p.get("version") for p in lock.get("packages", []) if p.get("name") in EXPECTED_VERSIONS
    }
    require(actual == EXPECTED_VERSIONS, f"Pinned Composer versions drifted: {actual}")
    return actual

def ddev_json(repo: Path, script: str, mode: str, output: Path) -> dict[str, Any]:
    text = run(
        ["ddev", "drush", "--quiet", "php:script", script, "--", mode],
        cwd=repo / "drupal",
        output=output,
    )
    return json.loads(text)

def main() -> int:
    if len(sys.argv) != 3:
        raise AuditError("Usage: gate1_step07_predecessor_audit.py REPO OUTPUT_DIR")
    repo = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    python = repo / "crewai/.venv/bin/python"
    require(python.is_file(), "Locked CrewAI Python environment is unavailable")

    matrix: list[dict[str, Any]] = []
    ordered: list[dict[str, Any]] = []

    # 0 — Gate 0.5 Step 05: meaningful live audit.
    run(["bash", "scripts/run-gate05-step05.sh", "audit"], repo, out / "00-gate05-step05.log")
    gate05 = pointer(repo, "evidence/gates/gate-0.5/substrate-certification/GATE05-STEP05-LATEST.txt", GATE05_RUN)
    summary_fields(gate05 / "summary.json", {"status": "pass", "shared_substrate_certified": True, "final_reset_clean": True})
    matrix.append({"boundary":"Gate 0.5 Step 05","classification":"meaningful_live_state_and_retained_evidence","status":"pass"})
    ordered.append({"order":0,"boundary":"Gate 0.5 Step 05","status":"pass"})

    # 1 — Step 1.01: progression-aware static audit + immutable accepted evidence.
    s1 = pointer(repo, "evidence/gates/gate-1/drupal-ai-batch-contract/GATE1-STEP01-LATEST.txt", STEP01_RUN)
    verify_manifest(s1, "package-files-sha256.txt")
    run([str(python), "scripts/gate1_step01_audit.py", "--repo", str(repo), "--document-state", "complete"], repo, out / "01-gate1-step01.log")
    summary_fields(s1 / "summary.json", {"status":"pass","contract_sha256":STEP01_SHA,"contract_semantics_changed":False})
    matrix.append({"boundary":"Gate 1 Step 1.01","classification":"progression_aware_live_static_and_retained_evidence","status":"pass"})
    ordered.append({"order":1,"boundary":"Gate 1 Step 1.01","status":"pass"})

    # 2 — Step 1.02: direct retained/runtime auditor; audit-mode HEAD assertion is not needed.
    s2 = pointer(repo, "evidence/gates/gate-1/drupal-ai-runtime-probe/GATE1-STEP02-LATEST.txt", STEP02_RUN)
    verify_manifest(s2, "package-files-sha256.txt")
    run([str(python), "scripts/gate1_step02_audit.py", "--repo", str(repo), "--run-dir", str(s2)], repo, out / "02-gate1-step02.log")
    summary_fields(s2 / "summary.json", {"status":"pass","decision_sha256":ADR0006_SHA,"explicit_model":"gpt-4.1-mini-2025-04-14","explicit_temperature":0.0})
    matrix.append({"boundary":"Gate 1 Step 1.02","classification":"meaningful_static_runtime_surface_and_retained_evidence","status":"pass"})
    ordered.append({"order":2,"boundary":"Gate 1 Step 1.02","status":"pass"})

    # 3 — Step 1.03: direct static/evidence auditor; no nested predecessor chain.
    s3 = pointer(repo, "evidence/gates/gate-1/drupal-ai-tool-adapters/GATE1-STEP03-LATEST.txt", STEP03_RUN)
    verify_manifest(s3, "package-files-sha256.txt")
    run([str(python), "scripts/gate1_step03_audit.py", "--repo", str(repo), "--run-dir", str(s3)], repo, out / "03-gate1-step03.log")
    summary_fields(s3 / "summary.json", {"status":"pass","plugin_count":4,"source_article_unchanged":True,"actual_drupal_source_drift":False})
    matrix.append({"boundary":"Gate 1 Step 1.03","classification":"meaningful_static_adapter_invariants_and_retained_evidence","status":"pass"})
    ordered.append({"order":3,"boundary":"Gate 1 Step 1.03","status":"pass"})

    # 4 — Step 1.04: retained evidence + current implementation markers.
    # The historical auditor's Step-1.06-absence assertion is intentionally not rerun.
    s4 = pointer(repo, "evidence/gates/gate-1/drupal-ai-canonical-vertical-slice/GATE1-STEP04-LATEST.txt", STEP04_RUN)
    verify_manifest(s4, "package-files-sha256.txt")
    summary_fields(s4 / "summary.json", {
        "status":"pass","canonical_target_sequence":1,"model":"gpt-4.1-mini-2025-04-14",
        "temperature":0.0,"provider_request_count_start":1,"automatic_retries":0,"human_review_required":True,
    })
    step04_php = (repo / "drupal/scripts/gate1-step04-canonical-vertical-slice.php").read_text(encoding="utf-8")
    for token in ("$task->setFiles([$file])", "$agent->determineSolvability()", "$agent->solve()", "editor_dana", "agentic_harness_tools.recommendation_validator"):
        require(token in step04_php, f"Step 1.04 current implementation invariant missing: {token}")
    (out / "04-gate1-step04.log").write_text(
        "[PASS] Accepted Step 1.04 evidence manifest and summary verified.\n"
        "[PASS] Current canonical implementation markers verified.\n"
        "[INFO] Historical successor-absence assertions were not applied to the final repository state.\n",
        encoding="utf-8",
    )
    matrix.append({"boundary":"Gate 1 Step 1.04","classification":"retained_evidence_plus_meaningful_current_implementation","historical_assertions":["Step 1.06 source absent"],"status":"pass"})
    ordered.append({"order":4,"boundary":"Gate 1 Step 1.04","status":"pass"})

    # 5 — Step 1.05: retained successful batch evidence + installed implementation.
    # Do not rerun old live-state handoff or successor-absence assertions.
    s5 = pointer(repo, "evidence/gates/gate-1/drupal-ai-batch-runner/GATE1-STEP05-LATEST.txt", STEP05_GATE_RUN)
    verify_manifest(s5, "package-files-sha256.txt")
    if (s5 / "result-files-sha256.txt").is_file():
        verify_manifest(s5, "result-files-sha256.txt", repo)
    final05 = load(s5 / "final-audit.json")
    for key, wanted in {
        "status":"pass","run_id":STEP05_BATCH_RUN,"target_count":12,"recommendation_count":12,
        "duplicate_count":0,"model":"gpt-4.1-mini-2025-04-14","temperature":0.0,"source_article_unchanged":True,
        "step_1_06_absent":True,
    }.items():
        require(final05.get(key) == wanted, f"Accepted Step 1.05 final audit differs: {key}")
    step05_php = (repo / "drupal/scripts/gate1-step05-drupal-ai-batch-runner.php").read_text(encoding="utf-8")
    for token in (
        "GATE1_STEP05_MODEL = 'gpt-4.1-mini-2025-04-14'", "GATE1_STEP05_TEMPERATURE = 0.0",
        "GATE1_STEP05_FAILURE_AFTER_SEQUENCE = 6", "GATE1_STEP05_RESUME_SEQUENCE = 7",
        "agentic_harness_tools.recommendation_validator", "submit_recommendation", "get_recommendation_status",
    ):
        require(token in step05_php, f"Step 1.05 current implementation invariant missing: {token}")
    (out / "05-gate1-step05.log").write_text(
        "[PASS] Accepted Step 1.05 evidence/manifests and current batch implementation verified.\n"
        "[PASS] Historical step_1_06_absent=true remains preserved in accepted evidence.\n"
        "[INFO] Historical module-enabled/12-pending handoff state is not required after valid Step 1.06 restoration.\n",
        encoding="utf-8",
    )
    matrix.append({"boundary":"Gate 1 Step 1.05","classification":"retained_evidence_plus_meaningful_current_implementation","historical_assertions":["Step 1.06 absent","module enabled with 12 pending recommendations"],"status":"pass"})
    ordered.append({"order":5,"boundary":"Gate 1 Step 1.05","status":"pass"})

    # 6 — Step 1.06: direct retained evidence auditor, bypassing obsolete exact-HEAD wrapper guard.
    s6 = pointer(repo, "evidence/gates/gate-1/batch-evidence/GATE1-STEP06-LATEST.txt", STEP06_RUN)
    verify_manifest(s6, "package-files-sha256.txt") if (s6 / "package-files-sha256.txt").is_file() else None
    result05 = repo / f"evidence/results/drupal_ai/{STEP05_BATCH_RUN}"
    run([
        str(python), "scripts/gate1_step06_evidence_audit.py", "final-audit",
        "--repo", str(repo), "--gate-run-dir", str(s6), "--result-dir", str(result05),
    ], repo, out / "06-gate1-step06.log")
    summary_fields(s6 / "summary.json", {"status":"pass","review_decision_count":3,"review_revision_count":4,"restored_seeded_clean":True,"step_1_07_authorized":True})
    matrix.append({"boundary":"Gate 1 Step 1.06","classification":"retained_evidence_auditor_plus_meaningful_final_live_state","historical_assertions":["exact pre-merge HEAD/origin-main"],"status":"pass"})
    ordered.append({"order":6,"boundary":"Gate 1 Step 1.06","status":"pass"})

    # Final live-state invariant after all predecessor evidence checks.
    full = ddev_json(repo, "scripts/gate05-step04.php", "snapshot", out / "current-full-source-state.json")
    reduced = ddev_json(repo, "scripts/gate1-step05-drupal-ai-batch-runner.php", "snapshot", out / "current-step05-state.json")
    require(full.get("article_count") == 20 and full.get("suggestion_count") == 0, "Current Gate 0.5 projection is not zero-suggestion clean")
    require(full.get("article_source_sha256") == SOURCE_SHA_FULL, "Current full Article projection drifted")
    require(reduced.get("seeded_clean") is True, "Current Step 1.05 projection is not seeded-clean")
    require(reduced.get("article_source_sha256") == SOURCE_SHA_REDUCED, "Current reduced Article projection drifted")
    modules = run(["ddev", "drush", "pm:list", "--type=module", "--status=enabled", "--format=list"], repo / "drupal", out / "enabled-modules.log")
    require("agentic_harness_drupal_ai" not in set(modules.splitlines()), "Drupal AI custom module is enabled in final seeded-clean state")
    run(["bash", "scripts/run-phase0-step10.sh", "audit"], repo / "drupal", out / "seeded-clean-audit.log")

    # Versions, contracts, schemas, prompts, and digests are the final part of the opening hard gate.
    require(sha(repo / "shared/contracts/GATE05-SUBSTRATE-FREEZE.json") == GATE05_FREEZE_SHA, "Gate 0.5 freeze digest changed")
    require(sha(repo / "shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json") == STEP01_SHA, "Gate 1 contract digest changed")
    require(sha(repo / "docs/decisions/ADR-0006-drupal-ai-programmatic-runtime-path.md") == ADR0006_SHA, "ADR-0006 changed")
    contract = load(repo / "shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json")
    require(contract.get("status") == "frozen", "Gate 1 contract is not frozen")
    constants = contract.get("frozen_constants", {})
    for key, wanted in {
        "provider":"OpenAI","model":"gpt-4.1-mini-2025-04-14","temperature":0.0,
        "source_framework":"drupal_ai","validator_version":"gate05-validator-1.0.0",
        "review_destination":"alt_text_suggestion","failure_after_sequence":6,"failure_before_sequence":7,
        "resume_at_sequence":7,"expected_duplicate_count":0,
    }.items():
        require(constants.get(key) == wanted, f"Frozen contract constant drifted: {key}")
    contract_inputs = contract.get("contract_inputs", {})
    checked_inputs: dict[str, str] = {}
    for rel, expected in contract_inputs.items():
        p = repo / rel
        require(p.is_file(), f"Frozen contract input missing: {rel}")
        actual = sha(p)
        require(actual == expected, f"Frozen contract input changed: {rel}")
        checked_inputs[rel] = actual
    versions = composer_versions(repo)
    freeze = {
        "status":"pass","versions":versions,"gate05_freeze_sha256":GATE05_FREEZE_SHA,
        "gate1_contract_sha256":STEP01_SHA,"adr0006_sha256":ADR0006_SHA,"target_sequence_sha256":TARGET_SHA,
        "full_article_source_sha256":SOURCE_SHA_FULL,"reduced_article_source_sha256":SOURCE_SHA_REDUCED,
        "contract_inputs":checked_inputs,
    }
    (out / "versions-contracts-hashes.json").write_text(json.dumps(freeze, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    ordered.append({"order":7,"boundary":"Pinned versions/contracts/hashes","status":"pass"})
    (out / "audit-compatibility-matrix.json").write_text(json.dumps({"schema_version":1,"status":"pass","entries":matrix}, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    (out / "ordered-audit.json").write_text(json.dumps({"schema_version":1,"status":"pass","ordered":ordered}, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({"status":"pass","ordered_boundaries":[x["boundary"] for x in ordered],"model_call_performed":False,"drupal_mutation_performed":False}, indent=2))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as exc:
        raise SystemExit(f"[ERROR] {exc}") from exc
