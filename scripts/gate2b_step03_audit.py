#!/usr/bin/env python3
"""Permanent auditor for Gate 2B Step 2B.03."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import jsonschema


PREDECESSOR = "e11746138c77f03b71a93a52ce69d199e71f697f"
LOCK_SHA = "855e5edff2cb86eb64ea9856d239b19010e7d3b1f80c40e370ed81d66b8e4e7c"
CONTRACT_SHA = "c734ad98f23c311e2141e6a50a876a6f5c9abf343e45884843848af1ef40ac77"
EVIDENCE_FILES = {
    "adapter-inventory.json", "authorization.json", "delegation-proof.json",
    "failure-propagation.json", "pinned-source-provenance.json", "predecessor.json",
    "privacy-scan.json", "proof-log.txt", "summary.json", "summary.md", "evidence-manifest.json",
}
CREATED = (
    "crewai/agentic_harness_crewai/__init__.py",
    "crewai/agentic_harness_crewai/tools.py",
    "docs/gates/GATE-2B-STEP03-CREWAI-SHARED-OPERATION-ADAPTERS.md",
    "shared/schemas/gate2b-step03-adapter-evidence.schema.json",
    "scripts/gate2b_step03_adapter_proof.py",
    "scripts/gate2b_step03_audit.py",
    "scripts/gate2b_step03_state.py",
    "scripts/run-gate2b-step03-crewai-shared-operation-adapters.sh",
)


def fail(message: str) -> None:
    print(f"[FAIL] {message}", file=sys.stderr)
    raise SystemExit(1)


def check(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"invalid JSON {path}: {exc}")


def audit_source(repo: Path) -> None:
    for relative in CREATED:
        check((repo / relative).is_file(), f"missing installed file: {relative}")
    check(sha256(repo / "crewai/uv.lock") == LOCK_SHA, "CrewAI dependency lock changed")
    check(sha256(repo / "shared/contracts/GATE2B-CREWAI-BATCH-CONTRACT.json") == CONTRACT_SHA, "Gate 2B contract changed")
    ancestor = git(repo, "merge-base", "--is-ancestor", PREDECESSOR, "HEAD")
    check(ancestor.returncode == 0, "expected merged predecessor is not an ancestor of HEAD")
    source = (repo / "crewai/agentic_harness_crewai/tools.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    check(source.count('@tool("') == 4, "exactly four public @tool adapters are required")
    check("from crewai.tools import BaseTool, tool" in source, "public CrewAI tool import missing")
    check("from shared.drupal_client.client import DrupalClient" in source, "shared client import missing")
    check(not any(isinstance(node, (ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler)) for node in ast.walk(tree)), "adapter contains loop or exception conversion")
    prohibited = (
        "from crewai import Agent", "from crewai import Crew", "from crewai.flow", "from crewai.llm",
        "SQLiteFlowPersistence", "set_memory_storage_factory", "import requests", "import httpx",
        "import openai", "import litellm",
    )
    check(not any(token in source for token in prohibited), "adapter contains prohibited lifecycle/model/network surface")


def audit_evidence(repo: Path) -> str:
    root = repo / "evidence/gates/gate-2b/shared-operation-adapters"
    pointer = root / "LATEST"
    check(pointer.is_file(), "LATEST Step 2B.03 evidence pointer missing")
    run_id = pointer.read_text(encoding="utf-8").strip()
    check(run_id.startswith("gate2b-step03-"), "invalid Step 2B.03 run id")
    run = root / run_id
    check(run.is_dir(), "accepted evidence directory missing")
    check({path.name for path in run.iterdir()} == EVIDENCE_FILES, "evidence file set is not exact")
    manifest = load(run / "evidence-manifest.json")
    entries = manifest.get("entries", [])
    check(len(entries) == len(EVIDENCE_FILES) - 1, "manifest entry count mismatch")
    check({entry.get("path") for entry in entries} == EVIDENCE_FILES - {"evidence-manifest.json"}, "manifest path set mismatch")
    for entry in entries:
        check(sha256(run / entry["path"]) == entry.get("sha256"), f"manifest hash mismatch: {entry['path']}")
    summary = load(run / "summary.json")
    schema = load(repo / "shared/schemas/gate2b-step03-adapter-evidence.schema.json")
    try:
        jsonschema.validate(summary, schema)
    except jsonschema.ValidationError as exc:
        fail(f"summary schema validation failed: {exc.message}")
    check(summary.get("status") == "pass" and summary.get("run_id") == run_id, "summary is not accepted/pass")
    inventory = load(run / "adapter-inventory.json")
    expected_names = ["find_images_needing_review", "get_image_context", "submit_recommendation", "get_recommendation_status"]
    check(inventory.get("status") == "pass", "adapter inventory failed")
    check([item.get("name") for item in inventory.get("tools", [])] == expected_names, "adapter inventory names/order mismatch")
    delegation = load(run / "delegation-proof.json")
    check(delegation.get("status") == "pass", "delegation proof failed")
    check(all(row.get("call_delta") == 1 and row.get("return_identity_preserved") for row in delegation.get("rows", [])), "delegation is not one-shot/pass-through")
    failures = load(run / "failure-propagation.json")
    check(failures.get("status") == "pass", "failure propagation proof failed")
    check(all(row.get("propagated") and row.get("retry_count") == 0 and row.get("call_count") == 1 for row in failures.get("rows", [])), "failure propagation/retry proof mismatch")
    authorization = load(run / "authorization.json")
    zero_keys = (
        "model_calls", "provider_calls", "successful_outbound_network_connections", "outbound_network_attempts",
        "drupal_mutations", "source_content_mutations", "authoritative_human_review_actions", "dependency_changes",
        "live_recommendation_submissions", "gate2c_executions", "flow_initializations", "persistence_initializations",
    )
    check(authorization.get("status") == "pass", "authorization evidence failed")
    check(all(authorization.get("counts", {}).get(key) == 0 for key in zero_keys), "one or more authorization counts are nonzero")
    check(load(run / "privacy-scan.json").get("status") == "pass", "privacy scan failed")
    provenance = load(run / "pinned-source-provenance.json")
    check(provenance.get("crewai") == "1.15.10" and provenance.get("crewai_tools") == "1.15.10", "pinned CrewAI versions drifted")
    check(provenance.get("selected_api") == "crewai.tools.tool", "unsupported tool API selected")
    return run_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--phase", choices=("active", "permanent"), default="permanent")
    args = parser.parse_args()
    repo = args.repo.resolve()
    audit_source(repo)
    if args.phase == "active":
        check("model-free adapter evidence has not yet been captured or accepted" in (repo / "AGENTS.md").read_text(encoding="utf-8"), "active lifecycle marker missing")
        print("[PASS] Gate 2B Step 2B.03 active installation audit")
        return 0
    run_id = audit_evidence(repo)
    check(run_id in (repo / "AGENTS.md").read_text(encoding="utf-8"), "accepted run missing from lifecycle authority")
    print(f"[PASS] Gate 2B Step 2B.03 permanent audit: {run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
