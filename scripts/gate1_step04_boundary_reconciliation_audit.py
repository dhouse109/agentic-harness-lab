#!/usr/bin/env python3
"""Permanent static audit for ADR-0007's additive canonical-slice boundary."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

FREEZE = {
    "shared/contracts/GATE05-SUBSTRATE-FREEZE.json": "99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a",
    "shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json": "360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6",
    "docs/decisions/ADR-0006-drupal-ai-programmatic-runtime-path.md": "223f6d6f4276d3861cf5668f08e0446479d815a07fed18402b1e6a7722d18c4b",
}
PROFILE = "shared/profiles/gate1-drupal-ai-canonical-slice-v1.0.0"

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(manifest_dir: Path, name: str, content_root: Path) -> None:
    manifest = manifest_dir / name
    if not manifest.is_file() or not manifest.read_text(encoding="utf-8").strip():
        raise SystemExit(f"[ERROR] Missing or empty evidence manifest: {name}")
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split(maxsplit=1)
        path = (content_root / relative.removeprefix("./")).resolve()
        if content_root.resolve() not in path.parents or not path.is_file() or sha(path) != digest:
            raise SystemExit(f"[ERROR] Evidence manifest mismatch: {name}: {relative}")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--overlay", type=Path)
    parser.add_argument("--run-dir", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    overlay = args.overlay.resolve() if args.overlay else repo
    for relative, expected in FREEZE.items():
        if sha(repo / relative) != expected:
            raise SystemExit(f"[ERROR] Frozen input changed: {relative}")
    batch_files = {
        "shared/schemas/batch-target-sequence.schema.json": "targets",
        "shared/schemas/batch-model-outputs.schema.json": "outputs",
        "shared/schemas/batch-recommendations.schema.json": "recommendations",
        "shared/schemas/batch-validation.schema.json": "results",
        "shared/schemas/batch-submissions.schema.json": "submissions",
    }
    for relative, key in batch_files.items():
        values = load(repo / relative)["properties"][key]
        if values.get("minItems") != 12 or values.get("maxItems") != 12:
            raise SystemExit(f"[ERROR] Batch cardinality changed: {relative}")
    completed = load(repo / "shared/schemas/drupal-ai-run-state.schema.json")["allOf"][0]["then"]["properties"]["next_target_index"]
    if completed != {"const": 12}:
        raise SystemExit("[ERROR] Completed batch run-state changed")
    profile = load(overlay / PROFILE / "canonical-slice-profile.json")
    if profile["target_cardinality"] != 1 or profile["canonical_sequence"] != 1 or profile["batch_contract_conformance"] is not False:
        raise SystemExit("[ERROR] Canonical-slice cardinality or batch exclusion is invalid")
    if profile["gate_evidence_root"].startswith("evidence/results/") or profile["maximum_provider_requests"] != 1:
        raise SystemExit("[ERROR] Canonical-slice evidence root or one-call boundary is invalid")
    if profile["post_image_wrapper_serialization_prohibited"] is not True or profile["raw_image_retention_prohibited"] is not True:
        raise SystemExit("[ERROR] Serialization/image retention prohibition missing")
    evidence = load(overlay / PROFILE / "canonical-slice-evidence.schema.json")["properties"]
    for key in ("canonical_targets", "model_outputs", "recommendations", "validation_results", "submissions", "human_review"):
        if evidence[key].get("minItems") != 1 or evidence[key].get("maxItems") != 1:
            raise SystemExit(f"[ERROR] Canonical-slice cardinality is not exactly one: {key}")
    if evidence["statuses"].get("minItems") != 2 or evidence["statuses"].get("maxItems") != 2:
        raise SystemExit("[ERROR] Pending/approved status observations are not distinct")
    package_root = repo.parent / "agentic-harness-lab-packages"
    if (package_root / "gate-1-step04-drupal-ai-canonical-vertical-slice-v1.0.0").exists() or (package_root / "gate-1-step05-drupal-ai-batch-runner-v1.0.0").exists():
        raise SystemExit("[ERROR] Package workspace contains prohibited later package")
    result={"status": "pass", "batch_cardinality": 12, "slice_cardinality": 1, "zero_or_two_slice_targets_rejected": True, "canonical_sequence": 1, "batch_root_excluded": True, "post_image_wrapper_serialization_prohibited": True, "step_1_05_absent": True}
    if args.run_dir:
        summary=load(args.run_dir/"summary.json")
        if summary.get("status") != "pass" or summary.get("provider_request_count") != 0 or summary.get("one_provider_request_maximum") != 1:
            raise SystemExit("[ERROR] Reconciliation evidence summary is invalid")
        for manifest in ("installed-files-sha256.txt", "package-files-sha256.txt"):
            verify_manifest(args.run_dir, manifest, repo)
        verify_manifest(args.run_dir, "retained-evidence-sha256.txt", args.run_dir)
        result["evidence_run"]=args.run_dir.name
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
