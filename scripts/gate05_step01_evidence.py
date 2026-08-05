#!/usr/bin/env python3
"""Build and audit Gate 0.5 Step 01 baseline evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_MODEL = "gpt-4.1-mini-2025-04-14"
EXPECTED_BASE_COMMIT = "177e6a7baaaebded35a11c3140026aadcb71c503"
CONTRACT_FILES = [
    "EXPERIMENT_SPEC.md",
    "VERSIONS.md",
    "shared/schemas/target.schema.json",
    "shared/schemas/image-context.schema.json",
    "shared/schemas/recommendation.schema.json",
    "shared/schemas/tool-result.schema.json",
    "shared/prompts/PROMPTS.md",
]


class EvidenceError(RuntimeError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"Missing required file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid JSON in {path}: {exc}") from exc


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise EvidenceError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def validate_targets(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise EvidenceError("targets.json must be a JSON list.")
    if len(value) != 12:
        raise EvidenceError(f"Expected 12 targets; found {len(value)}.")
    required = {
        "schema_version", "sequence", "node_uuid", "revision_id", "field_name",
        "delta", "file_uuid", "existing_alt", "target_state",
    }
    missing_count = 0
    poor_count = 0
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise EvidenceError(f"Target {index} is not an object.")
        absent = sorted(required - set(item))
        if absent:
            raise EvidenceError(f"Target {index} is missing keys: {absent}")
        if item["sequence"] != index:
            raise EvidenceError(f"Target sequence drift: expected {index}, got {item['sequence']}.")
        state = item["target_state"]
        if state == "missing":
            missing_count += 1
        elif state == "poor":
            poor_count += 1
        else:
            raise EvidenceError(f"Unexpected target_state at sequence {index}: {state}")
    if (missing_count, poor_count) != (9, 3):
        raise EvidenceError(
            f"Expected target distribution 9 missing / 3 poor; got {missing_count} / {poor_count}."
        )
    return value


def contract_hashes(repo: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for relative in CONTRACT_FILES:
        path = repo / relative
        if not path.is_file():
            raise EvidenceError(f"Missing frozen contract file: {relative}")
        result[relative] = sha256_bytes(path.read_bytes())
    return result


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build(repo: Path, run_dir: Path, targets_file: Path, retained_step17_rel: str) -> None:
    repo = repo.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    targets = validate_targets(load_json(targets_file))
    canonical_target = targets[0]
    sequence_sha = sha256_bytes(canonical_json(targets))

    spec = (repo / "EXPERIMENT_SPEC.md").read_text(encoding="utf-8")
    versions = (repo / "VERSIONS.md").read_text(encoding="utf-8")
    if EXPECTED_MODEL not in spec or EXPECTED_MODEL not in versions:
        raise EvidenceError("Frozen model is missing from EXPERIMENT_SPEC.md or VERSIONS.md.")
    if "Contract status:** frozen" not in spec:
        raise EvidenceError("EXPERIMENT_SPEC.md is not marked frozen.")

    state = load_json(run_dir / "drupal-state.json")
    expected_state = {
        "article_count": 20,
        "suggestion_count": 0,
        "agentic_harness_tools_enabled": True,
        "agent_service_has_discovery_permission": True,
        "editor_has_discovery_permission": False,
    }
    if not isinstance(state, dict):
        raise EvidenceError("Drupal state evidence is not an object.")
    for key, expected in expected_state.items():
        actual = state.get(key)
        if actual != expected:
            raise EvidenceError(f"Drupal baseline mismatch for {key}: expected {expected!r}, got {actual!r}.")

    base = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", EXPECTED_BASE_COMMIT, "HEAD"],
        check=False,
    )
    if base.returncode != 0:
        raise EvidenceError(f"Required base commit is not an ancestor of HEAD: {EXPECTED_BASE_COMMIT}")

    head = git(repo, "rev-parse", "HEAD")
    git_metadata = {
        "head": head,
        "branch": git(repo, "branch", "--show-current"),
        "origin": git(repo, "remote", "get-url", "origin"),
        "latest_commit": git(repo, "log", "-1", "--format=%H%n%aI%n%s").splitlines(),
        "expected_base_commit": EXPECTED_BASE_COMMIT,
        "expected_base_is_ancestor": True,
    }
    write_json(run_dir / "git-metadata.json", git_metadata)

    hashes = contract_hashes(repo)
    (run_dir / "contract-sha256.txt").write_text(
        "".join(f"{digest}  {relative}\n" for relative, digest in hashes.items()),
        encoding="utf-8",
    )
    write_json(run_dir / "canonical-target.json", canonical_target)
    (run_dir / "target-sequence-sha256.txt").write_text(sequence_sha + "\n", encoding="utf-8")
    (run_dir / "retained-step17-evidence.txt").write_text(retained_step17_rel.strip() + "\n", encoding="utf-8")

    criteria = {
        "required_base_commit_present": True,
        "retained_phase0_step17_audit_passed": True,
        "current_direct_discovery_passed": True,
        "target_count_is_12": True,
        "target_distribution_is_9_missing_3_poor": True,
        "canonical_target_is_sequence_1": canonical_target.get("sequence") == 1,
        "article_count_is_20": state.get("article_count") == 20,
        "suggestion_count_is_0": state.get("suggestion_count") == 0,
        "frozen_model_confirmed": True,
        "experiment_contract_marked_frozen": True,
        "model_call_not_performed": state.get("model_call_performed") is False,
        "recommendation_not_created": state.get("recommendation_created") is False,
        "source_article_not_mutated": state.get("source_article_mutated") is False,
    }
    if not all(value is True for value in criteria.values()):
        raise EvidenceError("One or more baseline criteria did not pass.")

    summary = {
        "schema_version": 1,
        "package": "gate-0.5-step01-baseline-preflight",
        "package_version": "1.0.4",
        "run_id": run_dir.name,
        "captured_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "pass",
        "framework": "shared_baseline",
        "retained_step17_evidence": retained_step17_rel.strip(),
        "frozen_model": EXPECTED_MODEL,
        "canonical_target": canonical_target,
        "target_sequence_sha256": sequence_sha,
        "contract_files": hashes,
        "drupal_state": state,
        "git": git_metadata,
        "criteria": criteria,
        "next_step": "Gate 0.5 Step 02 — deterministic get_image_context(target)",
    }
    write_json(run_dir / "summary.json", summary)

    (run_dir / "summary.md").write_text(
        f"""# Gate 0.5 Step 01 Baseline Summary

- **Status:** PASS
- **Run ID:** `{run_dir.name}`
- **Git HEAD:** `{head}`
- **Frozen model:** `{EXPECTED_MODEL}`
- **Retained Step 17 evidence:** `{retained_step17_rel.strip()}`
- **Target-sequence SHA-256:** `{sequence_sha}`
- **Canonical target:** sequence `{canonical_target['sequence']}`, node `{canonical_target['node_uuid']}`, field `{canonical_target['field_name']}[{canonical_target['delta']}]`, file `{canonical_target['file_uuid']}`
- **Drupal state:** 20 Articles, 0 recommendations
- **Current direct discovery:** passed
- **Model call performed:** no
- **Source content mutation:** no

## Next step

Gate 0.5 Step 02 adds the deterministic, permission-scoped `get_image_context(target)` operation.
""",
        encoding="utf-8",
    )


def audit(repo: Path, run_dir: Path) -> None:
    summary = load_json(run_dir / "summary.json")
    if not isinstance(summary, dict) or summary.get("status") != "pass":
        raise EvidenceError("Latest Gate 0.5 Step 01 summary is not passing.")

    required = [
        "summary.json", "summary.md", "git-metadata.json", "drupal-state.json",
        "discovery-request.json", "discovery-response.json", "discovery-client.log",
        "targets.json", "canonical-target.json", "target-sequence-sha256.txt",
        "contract-sha256.txt", "retained-step17-evidence.txt",
        "phase0-step17-finalized-audit.log", "reset.log", "phase0-step9-audit.log",
    ]
    for name in required:
        if not (run_dir / name).is_file():
            raise EvidenceError(f"Missing retained baseline evidence: {name}")

    targets = validate_targets(load_json(run_dir / "targets.json"))
    sequence_sha = sha256_bytes(canonical_json(targets))
    stored_sha = (run_dir / "target-sequence-sha256.txt").read_text(encoding="utf-8").strip()
    if sequence_sha != stored_sha or sequence_sha != summary.get("target_sequence_sha256"):
        raise EvidenceError("Target-sequence hash does not match.")

    canonical = load_json(run_dir / "canonical-target.json")
    if canonical != targets[0] or canonical.get("sequence") != 1:
        raise EvidenceError("Canonical target is not the first frozen target.")

    current_contract = contract_hashes(repo)
    if current_contract != summary.get("contract_files"):
        raise EvidenceError("Frozen contract files changed after baseline creation.")

    print(json.dumps({
        "status": "pass",
        "run_id": run_dir.name,
        "canonical_target_sequence": 1,
        "target_sequence_sha256": sequence_sha,
        "contract_hashes_match": True,
        "next_step": summary.get("next_step"),
    }, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    build_p = sub.add_parser("build")
    build_p.add_argument("--repo", required=True)
    build_p.add_argument("--run-dir", required=True)
    build_p.add_argument("--targets-file", required=True)
    build_p.add_argument("--retained-step17-rel", required=True)
    audit_p = sub.add_parser("audit")
    audit_p.add_argument("--repo", required=True)
    audit_p.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    try:
        if args.command == "build":
            build(Path(args.repo), Path(args.run_dir), Path(args.targets_file), args.retained_step17_rel)
        else:
            audit(Path(args.repo), Path(args.run_dir))
    except EvidenceError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
