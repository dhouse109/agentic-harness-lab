#!/usr/bin/env python3
"""Successor-aware permanent audit for Gate 2C Step 2C.01."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

PREDECESSOR = "c022619e220715be17e541650c261ea0b568704b"
CONTRACT_SHA = "3c4801e6eb35d40d94e066c70017d3acebca95183e7e544646be6e2b40aa5ec6"
FREEZES = {
    "shared/contracts/GATE1-DRUPAL-AI-FREEZE.json": "2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd",
    "shared/contracts/GATE2A-LANGGRAPH-FREEZE.json": "a28361c34b9d1c2089eee786324ad34cffbf54e3495f59a276c489865e5630f0",
    "shared/contracts/GATE2B-CREWAI-FREEZE.json": "74e2baad0cbe612dcd7e72ccdc264b01960ee12e09cfb0ae3154969b6055c206",
}
CERTIFICATIONS = {
    "gate1": (
        "evidence/gates/gate-1/certification/GATE1-STEP07-LATEST.txt",
        "evidence/gates/gate-1/certification/gate1-step07-20260809T012559Z-2229836",
        "package-files-sha256.txt",
    ),
    "gate2a": (
        "evidence/gates/gate-2a/certification/GATE2A-STEP10-LATEST.txt",
        "evidence/gates/gate-2a/certification/gate2a-step10-20260811T034835Z-03f93652",
        "package-files-sha256.txt",
    ),
    "gate2b": (
        "evidence/gates/gate-2b/certification/GATE2B-STEP08-LATEST.txt",
        "evidence/gates/gate-2b/certification/gate2b-step08-20260828T200003Z-22f913f2",
        "evidence-manifest.json",
    ),
}
SNAPSHOT = "drupal/.ddev/db_snapshots/gate2b-step06-post-step2b05-recovery-20260826T152003Z-mariadb_11.8.zst"
SNAPSHOT_SHA = "4ba4cece2d30a5f90699afdf9a2ab2094f0d902213c66cdc0b40dfa466094906"
BASE_ALLOWED_UNTRACKED = {
    "crewai/.runtime/gate2b-step04/crewai-20260818T215017Z-8e03fc95/flow-state.sqlite",
    "crewai/.runtime/gate2b-step04/crewai-20260818T215017Z-8e03fc95/flow-state.sqlite-shm",
    "crewai/.runtime/gate2b-step04/crewai-20260818T215017Z-8e03fc95/flow-state.sqlite-wal",
    "crewai/.runtime/gate2b-step05/gate2b-step05-20260825T192434Z-ff4f89dd/flow-state.sqlite",
    "crewai/.runtime/gate2b-step05/gate2b-step05-20260825T192434Z-ff4f89dd/flow-state.sqlite-shm",
    "crewai/.runtime/gate2b-step05/gate2b-step05-20260825T192434Z-ff4f89dd/flow-state.sqlite-wal",
    "crewai/.runtime/gate2b-step06/crewai-20260827T125501Z-c5381188/flow-state.sqlite",
    "crewai/.runtime/gate2b-step06/crewai-20260827T174606Z-6249d844/flow-state.sqlite",
    "evidence/gates/gate-2b/frozen-batch-activation/LATEST",
    "evidence/gates/gate-2b/frozen-batch-http-readiness/LATEST",
    "evidence/gates/gate-2b/frozen-batch/LATEST",
}
UPDATES = {"AGENTS.md", "PLAN.md", "README.md", "docs/CURRENT-STATUS.md"}
CREATES = {
    "docs/gates/GATE-2C-STEP01-SHARED-FAILURE-RECOVERY-CONTRACT-AND-EVIDENCE-PLAN.md",
    "shared/contracts/GATE2C-SHARED-FAILURE-RECOVERY-CONTRACT.json",
    "shared/contracts/GATE2C-SHARED-FAILURE-RECOVERY-CONTRACT.sha256",
    "shared/schemas/gate2c-shared-failure-recovery-contract.schema.json",
    "shared/schemas/gate2c-trial-evidence.schema.json",
    "shared/schemas/gate2c-comparison-evidence.schema.json",
    "scripts/gate2c_step01_audit.py",
    "scripts/gate2c_step01_certify.py",
    "scripts/gate2c_step01_rehearsal.py",
    "scripts/run-gate2c-step01-shared-failure-recovery-contract-and-evidence-plan.sh",
}

# Retained evidence is data, not detector implementation. A bare sentinel in that
# scope is therefore enough to fail closed. Source/configuration is scanned with
# payload-aware patterns so detector definitions and negative-control fixtures do
# not become false positives while realistic credential-bearing values still fail.
STRICT_RETAINED_PRIVACY_PATTERNS = {
    "openai_key_sentinel": re.compile(r"sk-(?:proj|live)-", re.I),
    "authorization_header_sentinel": re.compile(r"Authorization:\s*(?:Basic|Bearer)(?:\s|$)", re.I),
    "image_data_url_sentinel": re.compile(r"data:image/", re.I),
    "openai_api_key_assignment_sentinel": re.compile(r"OPENAI_API_KEY\s*=", re.I),
}
SOURCE_CONFIG_PRIVACY_PATTERNS = {
    "openai_key_payload": re.compile(r"sk-(?:proj|live)-[A-Za-z0-9_-]{12,}", re.I),
    "authorization_header_payload": re.compile(
        r"Authorization:\s*(?:Basic|Bearer)\s+[A-Za-z0-9+/=_-]{8,}", re.I
    ),
    "image_data_url_payload": re.compile(
        r"data:image/[^;\s]+;base64,[A-Za-z0-9+/]{12,}={0,2}", re.I
    ),
    "openai_api_key_assignment_payload": re.compile(
        r"OPENAI_API_KEY\s*=\s*['\"]?[A-Za-z0-9_-]{12,}", re.I
    ),
}
SOURCE_CONFIG_SUFFIXES = {
    ".conf", ".env", ".ini", ".json", ".md", ".php", ".py", ".sh", ".toml", ".yaml", ".yml"
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def privacy_pattern_labels(text: str, patterns: dict[str, re.Pattern[str]]) -> list[str]:
    """Return detector labels only; never return or print matched values."""
    return sorted(label for label, pattern in patterns.items() if pattern.search(text))


def require_privacy_clean(path: Path, patterns: dict[str, re.Pattern[str]], scope: str) -> None:
    labels = privacy_pattern_labels(path.read_text(encoding="utf-8", errors="replace"), patterns)
    require(not labels, f"{scope} privacy pattern labels {labels}: {path}")


def scan_retained_artifacts(root: Path) -> None:
    """Strictly scan retained evidence/data where even a sentinel is prohibited."""
    if not root.exists():
        return
    for path in sorted(root.rglob("*")):
        if path.is_file():
            require_privacy_clean(path, STRICT_RETAINED_PRIVACY_PATTERNS, "retained-artifact")


def scan_managed_source_and_config(repo: Path) -> None:
    """Scan Gate 2C-managed source/config with payload-aware secret patterns."""
    for relative in sorted(UPDATES | CREATES):
        path = repo / relative
        if path.is_file() and (path.suffix in SOURCE_CONFIG_SUFFIXES or path.name == ".env"):
            require_privacy_clean(path, SOURCE_CONFIG_PRIVACY_PATTERNS, "source/config")


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def verify_sha_file(root: Path, name: str) -> None:
    for line in (root / name).read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        require(sha(root / relative) == expected, f"immutable evidence drift: {root / relative}")


def verify_manifest(root: Path, name: str) -> None:
    manifest = json.loads((root / name).read_text(encoding="utf-8"))
    for entry in manifest["entries"]:
        path = root / entry["path"]
        require(path.is_file(), f"immutable evidence missing: {path}")
        require(path.stat().st_size == entry["size"], f"immutable evidence size drift: {path}")
        require(sha(path) == entry["sha256"], f"immutable evidence hash drift: {path}")


def verify_predecessors(repo: Path) -> None:
    for relative, expected in FREEZES.items():
        require(sha(repo / relative) == expected, f"freeze drift: {relative}")
    for label, (pointer, expected_root, manifest) in CERTIFICATIONS.items():
        require((repo / pointer).read_text(encoding="utf-8").strip() == expected_root, f"{label} pointer drift")
        root = repo / expected_root
        require(root.is_dir(), f"{label} certification missing")
        if manifest.endswith(".txt"):
            verify_sha_file(root, manifest)
        else:
            verify_manifest(root, manifest)
    gate1 = json.loads((repo / CERTIFICATIONS["gate1"][1] / "finalize.json").read_text())
    gate2a = json.loads((repo / CERTIFICATIONS["gate2a"][1] / "certification.json").read_text())
    gate2b = json.loads((repo / CERTIFICATIONS["gate2b"][1] / "certification.json").read_text())
    require(gate1["status"] == "pass" and gate1["freeze_sha256"] == FREEZES["shared/contracts/GATE1-DRUPAL-AI-FREEZE.json"], "Gate 1 certification binding")
    require(gate2a["result"] == "certified" and gate2a["gate2a_freeze_sha256"] == FREEZES["shared/contracts/GATE2A-LANGGRAPH-FREEZE.json"], "Gate 2A certification binding")
    require(gate2b["status"] == "pass" and gate2b["candidate"]["gate_2c"] == "DEFERRED_UNCLAIMED", "Gate 2B certification binding")
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = ":".join([str(repo / "scripts"), str(repo / "crewai"), str(repo)])
    result = subprocess.run(
        [
            str(repo / "crewai/.venv/bin/python"),
            str(repo / "scripts/gate2b_step07_audit.py"),
            "--repo", str(repo), "--mode", "gate2a-preservation",
        ],
        cwd=repo,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    require(result.returncode == 0, "Gate 2A descendant-preservation audit failed:\n" + result.stdout[-4000:])


def validate_contract(contract: dict) -> None:
    require(contract["lifecycle"]["gate_2c"] == "DEFERRED_UNCLAIMED", "Gate 2C lifecycle")
    require(contract["lifecycle"]["gate_2"] == "NOT_COMPLETE", "Gate 2 lifecycle")
    require(contract["lifecycle"]["live_execution_authorized"] is False, "live execution authorization")
    require(contract["failure_protocol"]["semantic_boundary"] == "after target 6 is fully persisted and before target 7 begins", "semantic seam")
    require(contract["failure_protocol"]["mechanism_status"] == "PENDING_MODEL_FREE_PROOF_IN_2C_02", "failure mechanism status")
    require([row["origin"] for row in contract["framework_seam_map"]] == ["drupal_ai", "langgraph", "crewai"], "framework seam order")
    require(contract["crewai_recovery_architecture"]["decision_status"] == "PENDING_MODEL_FREE_PROOF_AND_HUMAN_DECISION", "CrewAI decision prematurely closed")
    lock = contract["drupal_persistent_lock_policy"]
    require(lock["lock_lease_seconds"] == 1800 and lock["maximum_authoritative_recovery_invocations"] == 2, "Drupal lock policy")
    require(contract["dataset_and_reset"]["expected_suggestion_count"] == 0, "zero-suggestion baseline")
    require(contract["dataset_and_reset"]["gate2b_snapshot_may_be_zero_baseline"] is False, "Gate 2B snapshot misuse")
    accounting = contract["model_call_accounting"]
    require((accounting["successful_generations_before_failure_per_framework"], accounting["maximum_successful_generations_after_recovery_per_framework"], accounting["maximum_successful_logical_generations_per_framework"], accounting["maximum_successful_logical_generations_experiment"]) == (6, 6, 12, 36), "model accounting ceiling")
    frozen_retry = accounting["existing_frozen_framework_retry_configuration"]
    require(frozen_retry["policy"] == "MUST_REMAIN_UNCHANGED_UNLESS_AN_ADR_AND_EVIDENCE_INVALIDATION_BOUNDARY_IS_CROSSED", "frozen retry configuration policy")
    require(set(frozen_retry) >= {"drupal_ai", "langgraph", "crewai", "ambiguity_rule"}, "framework retry bindings")
    new_retry = accounting["new_gate2c_retry_logic"]
    require(new_retry["policy"] == "PROHIBITED" and new_retry["supervisor_added_provider_transport_sdk_framework_semantic_repair_generation_or_fallback_loops"] == 0 and new_retry["framework_adapter_added_provider_transport_sdk_framework_semantic_repair_generation_or_fallback_loops"] == 0, "new Gate 2C retry logic")
    require(accounting["recovery_retries"]["silent_or_automatic"] == "PROHIBITED" and accounting["recovery_retries"]["each_authoritative_recovery_invocation_requires_explicit_authorization"] is True, "recovery retry authorization")
    require(accounting["observed_retry_accounting"]["policy"] == "COUNT_AND_RETAIN_TRUTHFULLY" and accounting["observed_retry_accounting"]["observed_underlying_retry_is_evidence"] is True and accounting["observed_retry_accounting"]["concealment_or_unaccounted_retry_invalidates_trial"] is True, "observed retry accounting")
    require("never hides" in accounting["successful_generation_ceiling_scope"], "successful-generation ceiling accounting guard")
    require([item["step"] for item in contract["package_sequence"]] == ["2C.01", "2C.02", "2C.03", "2C.04"], "four-package sequence")
    require([item["package"] for item in contract["package_sequence"]] == [
        "gate-2c-step01-shared-failure-recovery-contract-and-evidence-plan",
        "gate-2c-step02-shared-failure-injector-and-model-free-rehearsals",
        "gate-2c-step03-three-framework-failure-recovery-execution",
        "gate-2c-step04-evidence-synthesis-and-gate2-certification",
    ], "four-package identities")
    boundaries = {item["boundary"] for item in contract["authorization_ledger"]}
    required = {"2C.01_preview_to_execution", "2C.02_snapshot_reset_or_Drupal_rehearsal", "2C.02_CrewAI_recovery_architecture", "2C.02_to_2C.03", "2C.03_model_backed_prefailure_execution_each_framework", "2C.03_post_kill_recovery_each_framework", "2C.03_restoration", "unexpected_failure_or_invalid_trial_retry", "2C.03_evidence_acceptance", "2C.03_to_2C.04", "2C.04_claim_synthesis_and_Gate2_certification", "commit_push_merge"}
    require(required <= boundaries, "authorization ledger incomplete")


def check_frozen_sources(repo: Path) -> None:
    anchors = {
        "drupal/scripts/gate1-step05-drupal-ai-batch-runner.php": ["agentic_harness_drupal_ai.run_state", "next_target_index", "1800"],
        "langchain/agentic_harness_langgraph/batch_runner.py": ["SqliteSaver", "thread_id", "continuation_boundary"],
        "crewai/agentic_harness_crewai/batch.py": ["SQLiteFlowPersistence", "target_finalized", "target_selected"],
    }
    for relative, needles in anchors.items():
        text = (repo / relative).read_text(encoding="utf-8")
        for needle in needles:
            require(needle in text, f"frozen source anchor absent: {relative}: {needle}")


def validate_evidence(root: Path, contract_sha: str) -> None:
    required = {"contract-certification.json", "predecessor-bindings.json", "authorization-ledger.json", "privacy-scan.json", "summary.md", "evidence-manifest.json"}
    require({p.name for p in root.iterdir() if p.is_file()} == required, "Step 2C.01 evidence file set")
    scan_retained_artifacts(root)
    verify_manifest(root, "evidence-manifest.json")
    cert = json.loads((root / "contract-certification.json").read_text())
    require(cert["contract_sha256"] == contract_sha and cert["model_free"] is True and cert["drupal_read_only"] is True and cert["runtime_mutations"] == 0, "Step 2C.01 certification activity")
    require(cert["gate_2c"] == "DEFERRED_UNCLAIMED" and cert["gate_2"] == "NOT_COMPLETE", "Step 2C.01 evidence lifecycle")
    privacy = json.loads((root / "privacy-scan.json").read_text())
    require(privacy == {"credentials_retained": False, "hidden_reasoning_retained": False, "private_database_content_retained": False, "raw_image_or_data_url_retained": False, "status": "PASS"}, "privacy evidence")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--content-root", type=Path)
    parser.add_argument("--mode", choices=["candidate", "permanent"], default="permanent")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    content = (args.content_root or repo).resolve()
    require((repo / ".git").is_dir(), "repository missing")
    require(subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", PREDECESSOR, "HEAD"]).returncode == 0, "Gate 2B merge not an ancestor")
    if args.mode == "candidate":
        require(git(repo, "branch", "--show-current") == "main", "candidate branch differs from main")
        require(git(repo, "rev-parse", "HEAD") == PREDECESSOR and git(repo, "rev-parse", "origin/main") == PREDECESSOR, "candidate predecessor drift")
        require(not git(repo, "diff", "--cached", "--name-only") and not git(repo, "diff", "--name-only"), "candidate tracked tree not clean")
    else:
        changed = set(filter(None, git(repo, "diff", "--name-only").splitlines())) | set(filter(None, git(repo, "diff", "--cached", "--name-only").splitlines()))
        require(not changed or changed <= UPDATES, f"unexpected tracked paths: {sorted(changed - UPDATES)}")
    untracked = set(filter(None, git(repo, "ls-files", "--others", "--exclude-standard").splitlines()))
    allowed = set(BASE_ALLOWED_UNTRACKED)
    if args.mode == "permanent":
        allowed |= CREATES
        allowed |= {path for path in untracked if path.startswith("evidence/gates/gate-2c/contract/")}
    require(not (untracked - allowed), f"unexpected untracked paths: {sorted(untracked - allowed)}")
    verify_predecessors(repo)
    snapshot = repo / SNAPSHOT
    require(snapshot.is_file() and snapshot.stat().st_size == 4112532 and sha(snapshot) == SNAPSHOT_SHA, "retained Gate 2B snapshot drift")
    require(subprocess.run(["git", "-C", str(repo), "check-ignore", "-q", str(snapshot)]).returncode == 0, "retained snapshot not ignored")
    contract_path = content / "shared/contracts/GATE2C-SHARED-FAILURE-RECOVERY-CONTRACT.json"
    sidecar = content / "shared/contracts/GATE2C-SHARED-FAILURE-RECOVERY-CONTRACT.sha256"
    require(sha(contract_path) == CONTRACT_SHA, "Gate 2C contract digest drift")
    require(sidecar.read_text(encoding="utf-8").strip() == f"{CONTRACT_SHA}  GATE2C-SHARED-FAILURE-RECOVERY-CONTRACT.json", "Gate 2C digest sidecar drift")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    validate_contract(contract)
    try:
        import jsonschema
    except ImportError as exc:
        raise RuntimeError("jsonschema is required") from exc
    for name in ("gate2c-shared-failure-recovery-contract.schema.json", "gate2c-trial-evidence.schema.json", "gate2c-comparison-evidence.schema.json"):
        schema = json.loads((content / "shared/schemas" / name).read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
    schema = json.loads((content / "shared/schemas/gate2c-shared-failure-recovery-contract.schema.json").read_text())
    jsonschema.validate(contract, schema)
    check_frozen_sources(repo)
    claims = (repo / "CLAIMS_REGISTER.md").read_text(encoding="utf-8")
    matrix = (repo / "COMPARISON_MATRIX.md").read_text(encoding="utf-8")
    require("CLM-CMP-002" in claims and "gate-2c-deferred" in claims, "claim guard")
    require("Gate 2C remains deferred" in matrix, "comparison guard")
    if args.mode == "permanent":
        status = (repo / "docs/CURRENT-STATUS.md").read_text(encoding="utf-8")
        require("Gate 2C remains `DEFERRED_UNCLAIMED`" in status and "Gate 2 overall remains `NOT_COMPLETE`" in status, "current lifecycle guard")
    scan_managed_source_and_config(repo)
    scan_retained_artifacts(repo / "evidence/gates/gate-2c/contract")
    if args.evidence:
        validate_evidence(args.evidence.resolve(), CONTRACT_SHA)
    print("[PASS] successor-aware Gate 1/Gate 2A/Gate 2B immutable certification bindings")
    print("[PASS] Gate 2C contract digest, schemas, seam, pending decisions, accounting, approvals, and protected tree")
    print("[PASS] retained Gate 2B snapshot and frozen source anchors")
    print("STEP_2C_01_AUDIT_PASS")
    print("GATE_2C_DEFERRED_UNCLAIMED")
    print("GATE_2_NOT_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
