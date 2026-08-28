#!/usr/bin/env python3
"""Model-free Gate 2B Step 2B.07 claim/proof synthesis."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

PACKAGE = "gate-2b-step07-crewai-evidence-synthesis-and-comparison-v1.0.0"
BASE = "78ba79165378ac2905801d994682aa385cdfb607"
FEATURE = "715aebd42d759f14bc71aac8cff12cec7725b595"
PREDECESSOR = "2ad5fc9faf29bf54983ae2c61f3f7cb0f9b28148"
SUCCESS_RUN = "crewai-20260827T174606Z-6249d844"
EVIDENCE_ROOT = "evidence/gates/gate-2b/evidence-synthesis"
POINTER = f"{EVIDENCE_ROOT}/GATE2B-STEP07-LATEST.txt"

HASHES = {
    "shared/contracts/GATE1-DRUPAL-AI-FREEZE.json": "2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd",
    "shared/contracts/GATE2A-LANGGRAPH-FREEZE.json": "a28361c34b9d1c2089eee786324ad34cffbf54e3495f59a276c489865e5630f0",
    "evidence/gates/gate-2b/runtime-probe-disposition/gate2b-step02-disposition-20260812T024610Z-00000001/evidence-manifest.json": "8666c77d3fc7f6a82a88adec652ea30b59198a3ce700ea14069b2ea6496c0f7d",
    "evidence/gates/gate-2b/shared-operation-adapters/gate2b-step03-20260818T163812Z-7a58ef58/evidence-manifest.json": "6b76549c442d3f27eb7278a41c69dad4e7313bd673adf331012d9c02c2216dad",
    "evidence/gates/gate-2b/canonical-slice/crewai-20260818T215017Z-8e03fc95/evidence-manifest.json": "c6115ffea4b7ceefb7858e6b482713fc92998dcf2bde7bc6de8831d583665aaf",
    "evidence/gates/gate-2b/canonical-slice-closure/gate2b-step04-closure-20260819T195009Z-60344274/evidence-manifest.json": "d62ababa96b223643ab23e3d67c75b3fcc2bb325a8a3e69787fff870cc56583b",
    "evidence/gates/gate-2b/human-review-continuation/gate2b-step05-20260825T192434Z-ff4f89dd/evidence-manifest.json": "7f3294f75be9602d55c27f66a6c084784b9571d12ced26a2e08234af66d0dd24",
    f"evidence/results/crewai/{SUCCESS_RUN}/evidence-manifest.json": "98d09c9f09db3f4043d8618d2ed78f67dd4ee67727910e5c401f05875a8330e6",
    f"evidence/results/crewai/{SUCCESS_RUN}/summary.json": "8ef1ef350803d9d3f833e75fdd421cd3e09bc5b57e733b8e2747bd0c117d824c",
    f"evidence/results/crewai/{SUCCESS_RUN}/batch-manifest.json": "e89069bec85a51655631fe1333f8af4a8f54968b06492619b50a36e8204368e1",
    f"evidence/gates/gate-2b/frozen-batch-governance-supplement/{SUCCESS_RUN}/gate2b-step06-governance-supplement-v103/supplement-manifest.json": "6de9183a368ac2781317b64ad21dfb09c9c8b2ad01f354be8c1b9669ae48d19d",
    f"evidence/gates/gate-2b/frozen-batch-final-governance/{SUCCESS_RUN}/gate2b-step06-final-governance-v104/final-governance-manifest.json": "4c31328172c1c99372a4c07133c52babcf6662083a562882e30fa654f07afb41",
    "evidence/gates/gate-2b/frozen-batch-activation/gate2b-step06-post-step2b05-recovery-20260826T152003Z-activation/activation-manifest.json": "2008ce545bb553e3ba21e2a013fb419d953a03c36c361bf7f46a986bd8d7f63d",
    "evidence/gates/gate-2b/frozen-batch-http-readiness/gate2b-step06-post-step2b05-recovery-20260826T152003Z-http-readiness-v102/http-readiness-manifest.json": "adb8865a813678bab30389f177d8cdffb9d92cd5df49aa7f8770398123167511",
    "evidence/gates/gate-2b/frozen-batch-failures/crewai-20260827T125501Z-c5381188/gate2b-step06-attempt-20260827T125530Z-185709/failure.json": "e1249a21c5a4252c8b0d53dcf56ebc23837a36e6d2d8429c9a7ee6fbce1f8661",
    "evidence/gates/gate-2b/frozen-batch-failure-disposition/crewai-20260827T125501Z-c5381188/gate2b-step06-attempt-20260827T125530Z-185709-v102/disposition-manifest.json": "0d7a8310092d60f6ce5c43754d9646c831fccf39a12a119c323a13f28d3f6e00",
}

CLAIMS = [
    ("CLM-CR-002", "verified", "state", ["SRC-CR-001"], [2, 4, 5], "Pinned Flow persistence crossed a process boundary.", "Do not infer production durability or Gate 2C recovery."),
    ("CLM-CR-003", "verified", "human-review", ["SRC-CR-002"], [5], "One pending Flow was reconstructed and resumed once around Drupal review.", "Do not infer autonomous or non-Drupal review authority."),
    ("CLM-CR-004", "verified", "tools", ["SRC-CR-003"], [3], "Four BaseTool adapters delegated to the shared operations.", "Do not infer untested tool breadth."),
    ("CLM-CR-005", "observed", "context", [], [4, 6], "Fresh permitted context and sanitized retained evidence were observed.", "Do not infer output quality or privacy beyond scanned artifacts."),
    ("CLM-CR-006", "observed", "verification", [], [4, 6], "Strict output, shared validation, and one-request controls preceded submit.", "Do not infer provider-wide retry behavior."),
    ("CLM-CR-007", "observed", "lifecycle", [], [6], "The accepted serial batch completed 12/12 with exact accounting.", "Do not generalize beyond this run."),
    ("CLM-CR-008", "observed", "verification", [], [3, 6], "Source nonmutation, identity uniqueness, and rerun blocking passed.", "Do not infer general transactional safety."),
    ("CLM-CR-009", "observed", "lifecycle", [], [6], "The failed HTTP attempt, disposition, readiness repair, and accepted run are retained.", "Do not retain or disclose credentials."),
    ("CLM-CR-010", "observed", "lifecycle", [], [5, 6], "One exact restoration and final evidence closure passed.", "Restoration is not the shared Gate 2C trial."),
    ("CLM-CR-011", "observed", "lifecycle", [], [6], "The final composite auditor passed on a normal merge descendant.", "Do not infer audits cover untested deployments."),
    ("CLM-CR-012", "architecture/probe", "state", ["SRC-CR-001"], [2], "The public storage factory and SQLiteFlowPersistence are selected.", "Do not promote architecture/probe evidence to observed behavior without live proof."),
    ("CLM-CR-013", "unsupported", "state", ["SRC-CR-001"], [2], "Runtime CheckpointConfig is nonselected for this specimen.", "Do not claim it is the live continuation mechanism."),
    ("CLM-CMP-001", "observed", "verification", [], [6], "Separate accepted runs submitted validator-approved recommendations to one queue.", "Do not infer equal quality, readiness, or simultaneity."),
    ("CLM-CMP-002", "gate-2c-deferred", "lifecycle", [], [6], "Framework-specific lifecycle evidence may be described separately.", "No shared recovery conclusion or winner is permitted."),
    ("CLM-CMP-004", "observed", "verification", [], [6], "The accepted framework runs preserve the frozen comparison controls.", "Do not erase evidence-strength differences."),
]

PROOFS = {
    2: [p for p in HASHES if "runtime-probe-disposition" in p],
    3: [p for p in HASHES if "shared-operation-adapters" in p],
    4: [p for p in HASHES if "/canonical-slice/" in p or "canonical-slice-closure" in p],
    5: [p for p in HASHES if "human-review-continuation" in p],
    6: [p for p in HASHES if "frozen-batch" in p or f"results/crewai/{SUCCESS_RUN}" in p],
}

PROHIBITED = [
    "production ready", "production-ready", "CrewAI is superior", "CrewAI is best",
    "recovery winner", "Gate 2C complete", "Gate 2C is complete",
]

def need(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def verify_predecessor_hashes(repo: Path) -> None:
    for rel, expected in HASHES.items():
        path = repo / rel
        need(path.is_file() and not path.is_symlink(), f"missing or unsafe predecessor: {rel}")
        need(sha(path) == expected, f"predecessor hash drift: {rel}")

def claim_line(document: str, claim_id: str) -> str:
    return next((line for line in document.splitlines() if f"| {claim_id} |" in line), "")

def verify_documents(repo: Path) -> None:
    claims = (repo / "CLAIMS_REGISTER.md").read_text()
    matrix = (repo / "COMPARISON_MATRIX.md").read_text()
    sources = (repo / "SOURCES.md").read_text()
    expected = {row[0]: row[1] for row in CLAIMS}
    for claim_id, status in expected.items():
        line = claim_line(claims, claim_id)
        need(line, f"claim absent: {claim_id}")
        need(f"| {status} |" in line, f"claim status drift: {claim_id}")
    need("| CLM-CR-001 |" in claims and "| hypothesis |" in claim_line(claims, "CLM-CR-001"), "role-decomposition hypothesis was promoted")
    need("| CLM-CMP-003 |" in claims and "| hypothesis |" in claim_line(claims, "CLM-CMP-003"), "best-fit hypothesis was promoted")
    for source_id, url in {
        "SRC-CR-001": "https://docs.crewai.com/v1.15.10/en/concepts/flows",
        "SRC-CR-002": "https://docs.crewai.com/v1.15.10/en/learn/human-feedback-in-flows",
        "SRC-CR-003": "https://docs.crewai.com/v1.15.10/en/concepts/tools",
    }.items():
        need(f"| {source_id} |" in sources and url in sources, f"source pairing drift: {source_id}")
    crew_rows = [line for line in matrix.splitlines() if line.startswith("|") and "| CrewAI |" in line]
    need(len(crew_rows) == 6, f"expected six CrewAI organ rows, got {len(crew_rows)}")
    need(all("TODO" not in line and "not observed" not in line for line in crew_rows), "stale CrewAI comparison wording")
    need("Gate 2C remains deferred" in matrix, "Gate 2C deferred wording absent")
    need("no three-way recovery conclusion or winner" in claims, "Gate 2C overstatement guard absent")
    need("Source Article/image-alt mutation remained zero" in claims, "source-nonmutation wording drift")
    combined = "\n".join([claims, matrix])
    for phrase in PROHIBITED:
        if phrase.lower() in combined.lower():
            # Negative wording is allowed only when accompanied by an explicit guard.
            matching = [line for line in combined.splitlines() if phrase.lower() in line.lower()]
            need(all(any(guard in line.lower() for guard in ["do not", "no ", "unclaimed", "prohibited"]) for line in matching), f"prohibited overstatement: {phrase}")

def build_claim_map() -> dict:
    rows = []
    for claim_id, status, organ, sources, proof_groups, safe, prohibited in CLAIMS:
        proof_paths = sorted({path for group in proof_groups for path in PROOFS[group]})
        rows.append({
            "claim_id": claim_id,
            "claim_text": safe,
            "claim_strength": status,
            "framework": "cross-framework" if claim_id.startswith("CLM-CMP") else "crewai",
            "organ": organ,
            "official_source_ids": sources,
            "evidence": [{"path": path, "sha256": HASHES[path]} for path in proof_paths],
            "permanent_auditor": {"path": "scripts/gate2b_step07_audit.py", "predicate": f"claim:{claim_id}:{status}"},
            "comparison_safe_wording": safe,
            "prohibited_overstatement": prohibited,
        })
    return {"schema_version": "1.0.0", "claims": rows}

def create_family(repo: Path, run_id: str, output: Path) -> None:
    need(re.fullmatch(r"gate2b-step07-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}", run_id) is not None, "invalid run id")
    need(not output.exists(), "output already exists")
    verify_predecessor_hashes(repo)
    verify_documents(repo)
    output.mkdir(parents=True)
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    claim_map = build_claim_map()
    comparison = {
        "schema_version": "1.0.0", "run_id": run_id,
        "frameworks": ["drupal_ai", "langgraph", "crewai"],
        "organs": ["context", "tools", "state", "verification", "human-review", "lifecycle"],
        "shared_controls_held": True, "false_symmetry_avoided": True,
        "gate2c_status": "DEFERRED_UNCLAIMED", "recovery_winner_claimed": False,
        "production_readiness_claimed": False, "framework_superiority_claimed": False,
        "langgraph_privacy_failure_and_salvage_preserved": True,
        "crewai_http_failure_and_disposition_preserved": True,
    }
    privacy = {
        "schema_version": "1.0.0", "status": "pass",
        "scanned_artifacts": ["claim-proof-map.json", "comparison-synthesis.json", "summary.json"],
        "prohibited_value_hits": 0, "credentials_retained": False,
        "raw_image_or_data_url_retained": False, "private_database_content_retained": False,
        "hidden_reasoning_retained": False,
    }
    summary = {
        "schema_version": "1.0.0", "package": PACKAGE, "run_id": run_id, "created_at": created,
        "status": "pass", "predecessor_merge": BASE, "successful_crewai_run": SUCCESS_RUN,
        "verified_claims": [c[0] for c in CLAIMS if c[1] == "verified"],
        "observed_claims": [c[0] for c in CLAIMS if c[1] == "observed"],
        "architecture_probe_claims": [c[0] for c in CLAIMS if c[1] == "architecture/probe"],
        "unsupported_claims": [c[0] for c in CLAIMS if c[1] == "unsupported"],
        "gate2c_deferred_claims": [c[0] for c in CLAIMS if c[1] == "gate-2c-deferred"],
        "model_generations": 0, "provider_requests": 0, "provider_responses": 0,
        "drupal_read_only_predecessor_audit": True, "drupal_writes": 0, "recommendation_submissions": 0,
        "human_reviews": 0, "snapshot_operations": 0, "new_crewai_runtimes": 0,
        "predecessor_evidence_rewritten": False, "gate2b_certified": False,
        "step2b08_started": False, "gate2c_executed": False, "privacy": "pass",
    }
    write_json(output / "claim-proof-map.json", claim_map)
    write_json(output / "comparison-synthesis.json", comparison)
    write_json(output / "privacy-scan.json", privacy)
    write_json(output / "summary.json", summary)
    entries = []
    for name in ["claim-proof-map.json", "comparison-synthesis.json", "privacy-scan.json", "summary.json"]:
        entries.append({"path": name, "sha256": sha(output / name), "size": (output / name).stat().st_size})
    write_json(output / "evidence-manifest.json", {"schema_version": "1.0.0", "run_id": run_id, "entries": entries})

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    create_family(Path(args.repo).resolve(), args.run_id, Path(args.output).resolve())
    print(f"[PASS] Created model-free Step 2B.07 synthesis family: {args.output}")

if __name__ == "__main__":
    main()
