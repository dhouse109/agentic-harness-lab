#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import subprocess
import sys
from pathlib import Path

EXPECTED_BASE = "0477e882987501438ae07fbb51e741b4be800843"
EXPECTED_GATE05 = "99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a"
EXPECTED_GATE1 = "2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd"
EXPECTED_GATE2A_CONTRACT = "1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b"
EXPECTED_GATE2A = "a28361c34b9d1c2089eee786324ad34cffbf54e3495f59a276c489865e5630f0"
EXPECTED_TARGET = "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728"
EXPECTED_LOCK = "855e5edff2cb86eb64ea9856d239b19010e7d3b1f80c40e370ed81d66b8e4e7c"
PACKAGE = "gate-2b-step01-crewai-contract-and-evidence-plan-v1.0.0"
NEXT_PACKAGE = "gate-2b-step02-crewai-runtime-persistence-and-continuation-probe-v1.0.0"
CONTRACT = "shared/contracts/GATE2B-CREWAI-BATCH-CONTRACT.json"
CONTRACT_SHA = "shared/contracts/GATE2B-CREWAI-BATCH-CONTRACT.sha256"
FROZEN_INPUTS = {
    "shared/schemas/target.schema.json": "2bcb867c3b58a5f4bb20b29274434c153ad043e8c0dba3ce3d1e496a44a32469",
    "shared/schemas/image-context.schema.json": "b2e27b533551759d181c58330ebedcb26ca92c1a596dbb4aaf48a48422dffaee",
    "shared/schemas/recommendation.schema.json": "7b1cf9800d5c8d8df4cd0a718c721dd43013afa256f7814a365d4696e2cfe2bd",
    "shared/schemas/tool-result.schema.json": "ce04e938eb4e34e861c000b86fffeed4adc5e5c66167c52ebf5380b8cd3cd91b",
    "shared/schemas/run-state.schema.json": "ee5face3d81138cfa2d5de2e03d8fb2aded881743e2e0334129342bf95f3010b",
}
EVIDENCE_FILES = {
    "contract-audit.json",
    "contract.json",
    "contract.sha256",
    "environment.json",
    "gate2a-predecessor-audit.log",
    "git-metadata.json",
    "runtime-inspection.json",
    "summary.json",
    "summary.md",
    "package-files-sha256.txt",
}


class AuditError(RuntimeError):
    pass


def need(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def head_sha(repo: Path, rel: str) -> str:
    diff = subprocess.run(["git", "-C", str(repo), "diff", "--quiet", "HEAD", "--", rel])
    need(diff.returncode == 0, f"Frozen shared input has tracked drift: {rel}")
    proc = subprocess.run(
        ["git", "-C", str(repo), "show", f"HEAD:{rel}"],
        check=False,
        capture_output=True,
    )
    need(proc.returncode == 0, f"Frozen shared input is absent from HEAD: {rel}")
    return hashlib.sha256(proc.stdout).hexdigest()


def validate_manifest(run_dir: Path) -> None:
    actual = {p.name for p in run_dir.iterdir() if p.is_file()}
    need(actual == EVIDENCE_FILES, f"Evidence file set mismatch: expected {sorted(EVIDENCE_FILES)}, got {sorted(actual)}")
    manifest = run_dir / "package-files-sha256.txt"
    entries: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9._-]+)", line)
        need(match is not None, f"Malformed evidence manifest line: {line!r}")
        digest, name = match.groups()
        need(name != manifest.name, "Evidence manifest must not hash itself")
        need(name not in entries, f"Duplicate evidence manifest entry: {name}")
        entries[name] = digest
    expected_hashed = EVIDENCE_FILES - {manifest.name}
    need(set(entries) == expected_hashed, "Evidence manifest does not cover the exact evidence file set")
    for name, digest in entries.items():
        need(sha256(run_dir / name) == digest, f"Evidence hash mismatch: {name}")


def audit_evidence(repo: Path) -> str:
    root = repo / "evidence/gates/gate-2b/contract"
    pointer = root / "GATE2B-STEP01-LATEST.txt"
    need(pointer.is_file(), "Missing Gate 2B Step 2B.01 latest evidence pointer")
    relative = pointer.read_text(encoding="utf-8").strip()
    need(relative.startswith("evidence/gates/gate-2b/contract/gate2b-step01-"), "Unsafe or unexpected evidence pointer")
    run_dir = (repo / relative).resolve()
    need(run_dir.parent == root.resolve(), "Evidence pointer escapes the contract evidence root")
    need(run_dir.is_dir(), "Pointed evidence directory is missing")
    validate_manifest(run_dir)
    summary = load(run_dir / "summary.json")
    expected = {
        "status": "pass",
        "package": "gate-2b-step01-crewai-contract-and-evidence-plan",
        "package_version": "1.0.0",
        "model_calls": 0,
        "crewai_origin_drupal_mutations": 0,
        "source_content_mutations": 0,
        "dependency_changes": 0,
        "gate2c_executions": 0,
        "gate2c_status": "deferred_unclaimed",
        "next_package": NEXT_PACKAGE,
    }
    for key, value in expected.items():
        need(summary.get(key) == value, f"Unexpected evidence summary field {key}: {summary.get(key)!r}")
    return relative


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--activation", action="store_true")
    parser.add_argument("--evidence-required", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()

    contract = load(repo / CONTRACT)
    digest_line = (repo / CONTRACT_SHA).read_text(encoding="utf-8").strip().split()
    need(len(digest_line) == 2 and digest_line[1] == "GATE2B-CREWAI-BATCH-CONTRACT.json", "Malformed contract digest file")
    contract_digest = sha256(repo / CONTRACT)
    need(contract_digest == digest_line[0], "Gate 2B contract digest mismatch")

    predecessor = contract["predecessor"]
    need(predecessor["merged_commit"] == EXPECTED_BASE, "Unexpected merged predecessor")
    required_hashes = {
        "shared/contracts/GATE05-SUBSTRATE-FREEZE.json": EXPECTED_GATE05,
        "shared/contracts/GATE1-DRUPAL-AI-FREEZE.json": EXPECTED_GATE1,
        "shared/contracts/GATE2A-LANGGRAPH-BATCH-CONTRACT.json": EXPECTED_GATE2A_CONTRACT,
        "shared/contracts/GATE2A-LANGGRAPH-FREEZE.json": EXPECTED_GATE2A,
        "crewai/uv.lock": EXPECTED_LOCK,
    }
    for rel, digest in required_hashes.items():
        need(sha256(repo / rel) == digest, f"Required predecessor changed: {rel}")
    need((repo / predecessor["accepted_gate2a_certification_evidence"]).is_dir(), "Accepted Gate 2A certification evidence is missing")
    need((repo / predecessor["accepted_langgraph_batch"]).is_dir(), "Accepted LangGraph batch is missing")
    for rel, digest in FROZEN_INPUTS.items():
        need(head_sha(repo, rel) == digest, f"Frozen shared input changed: {rel}")

    authorization = contract["authorization"]
    need(authorization == {
        "model_calls": 0,
        "crewai_origin_drupal_mutations": 0,
        "source_content_mutations": 0,
        "dependency_changes": 0,
        "gate2c_executions": 0,
    }, "Step 2B.01 authorization budget changed")
    frozen = contract["frozen_constants"]
    expected_constants = {
        "provider": "OpenAI",
        "model": "gpt-4.1-mini-2025-04-14",
        "temperature": 0.0,
        "dataset_article_count": 20,
        "target_count": 12,
        "target_sequence_sha256": EXPECTED_TARGET,
        "framework_origin": "crewai",
        "validator_version": "gate05-validator-1.0.0",
        "review_destination": "alt_text_suggestion",
        "reviewer": "editor_dana",
        "source_article_mutation": "prohibited",
        "automatic_publication": "prohibited",
        "gate2c_failure_seam": "after_target_6_fully_persisted_before_target_7_begins",
    }
    need(frozen == expected_constants, "Frozen comparison constants changed")
    need(contract["architecture"]["status"] == "deferred_to_step_2B_02", "Architecture choice was not deferred")
    need(contract["runtime_capability_inspection"]["status"] == "inspected_not_yet_gate2b_observed", "Inspected capabilities are misclassified")
    need(contract["ownership"]["shared_runtime_storage_prohibited"] is True, "Shared runtime storage is not prohibited")
    need(contract["human_review"]["second_authoritative_approval_system_prohibited"] is True, "Second approval authority is not prohibited")
    need(contract["next_evidence_boundary"]["package"] == NEXT_PACKAGE, "Unexpected next evidence boundary")
    need(contract["next_evidence_boundary"]["model_calls"] == 0, "Next probe unexpectedly authorizes model calls")
    need(contract["next_evidence_boundary"]["drupal_mutations"] == 0, "Next probe unexpectedly authorizes Drupal mutation")

    need(sys.version_info[:3] == (3, 12, 13), f"Unexpected Python runtime: {sys.version.split()[0]}")
    need(importlib.metadata.version("crewai") == "1.15.10", "Installed CrewAI version mismatch")
    need(importlib.metadata.version("crewai-tools") == "1.15.10", "Installed CrewAI Tools version mismatch")

    try:
        import jsonschema
        from referencing import Registry, Resource
    except Exception as exc:
        raise AuditError(f"Schema tooling unavailable: {exc}") from exc
    schema_dir = repo / "shared/schemas"
    registry = Registry()
    for path in schema_dir.glob("*.schema.json"):
        schema = load(path)
        if "$id" in schema:
            registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    model_schema = load(schema_dir / "crewai-model-output.schema.json")
    state_schema = load(schema_dir / "crewai-run-state.schema.json")
    jsonschema.Draft202012Validator.check_schema(model_schema)
    jsonschema.Draft202012Validator.check_schema(state_schema)
    model_validator = jsonschema.Draft202012Validator(model_schema, registry=registry)
    need(model_validator.is_valid({"proposed_alt_text": "A concise description"}), "Positive model-output schema control failed")
    need(not model_validator.is_valid({"proposed_alt_text": "", "reasoning": "private"}), "Negative model-output schema control passed")
    state = {
        "schema_version": 1,
        "run_id": "crewai-20260811T180000Z-a1b2c3d4",
        "framework_origin": "crewai",
        "framework_state_id": None,
        "runtime_state_mechanism": "unselected",
        "runtime_storage_location": None,
        "status": "planned",
        "continuation_status": "untested",
        "target_sequence_hash": f"sha256:{EXPECTED_TARGET}",
        "next_target_index": 0,
        "completed_target_identities": [],
        "recommendation_ids": [],
        "validation_results": [],
        "started_at": "2026-08-11T18:00:00Z",
        "updated_at": "2026-08-11T18:00:00Z",
        "completed_at": None,
        "gate2c_failure_injection_fired": False,
        "prompt_version": "crewai-alt-text-v1.0.0",
        "model_id": "gpt-4.1-mini-2025-04-14",
    }
    state_validator = jsonschema.Draft202012Validator(state_schema, registry=registry)
    need(state_validator.is_valid(state), "Positive CrewAI run-state schema control failed")
    bad = dict(state)
    bad["framework_origin"] = "langgraph"
    need(not state_validator.is_valid(bad), "Wrong-origin run-state negative control passed")

    if args.activation:
        for rel in ["AGENTS.md", "PLAN.md", "README.md", "docs/CURRENT-STATUS.md"]:
            need(PACKAGE in (repo / rel).read_text(encoding="utf-8"), f"Activation marker missing in {rel}")

    evidence = None
    if args.evidence_required:
        evidence = audit_evidence(repo)

    result = {
        "status": "pass",
        "contract_sha256": contract_digest,
        "predecessor_commit": EXPECTED_BASE,
        "gate2a_freeze_sha256": EXPECTED_GATE2A,
        "python": sys.version.split()[0],
        "crewai": importlib.metadata.version("crewai"),
        "crewai_tools": importlib.metadata.version("crewai-tools"),
        "architecture_status": "deferred_to_step_2B_02",
        "model_calls": 0,
        "crewai_origin_drupal_mutations": 0,
        "dependency_changes": 0,
        "gate2c_status": "deferred_unclaimed",
        "evidence": evidence,
        "next_package": NEXT_PACKAGE,
    }
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else "[PASS] Gate 2B Step 2B.01 permanent contract audit passed.")


if __name__ == "__main__":
    try:
        main()
    except AuditError as exc:
        raise SystemExit(f"[ERROR] {exc}")
