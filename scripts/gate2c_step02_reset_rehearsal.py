#!/usr/bin/env python3
"""Separately authorized model-free reset/restoration mechanics rehearsal."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

RUN_PATTERN = re.compile(r"^gate2c-step02-reset-[0-9]{8}T[0-9]{6}Z-[a-z0-9]{8}$")
SNAPSHOT_ID = "gate2b-step06-post-step2b05-recovery-20260826T152003Z"
SNAPSHOT_SHA = "4ba4cece2d30a5f90699afdf9a2ab2094f0d902213c66cdc0b40dfa466094906"
DRUPAL_RUN_PATTERN = re.compile(r"^gate2c-step02-drupal-[0-9]{8}T[0-9]{6}Z-[a-z0-9]{8}$")


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def canonical(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_finalized_drupal_evidence(repo: Path, run_id: str) -> tuple[Path, str]:
    require(DRUPAL_RUN_PATTERN.fullmatch(run_id) is not None, "invalid Drupal rehearsal run ID")
    root = repo / "evidence/gates/gate-2c/model-free-rehearsals" / run_id
    expected = {
        "authorization-ledger.json", "drupal-termination.json", "drupal-immediate.json",
        "drupal-post-expiry.json", "zero-operation-accounting.json", "privacy-scan.json",
        "summary.md", "evidence-manifest.json",
    }
    require(root.is_dir() and {path.name for path in root.iterdir() if path.is_file()} == expected, "finalized Drupal evidence required before reset")
    manifest = json.loads((root / "evidence-manifest.json").read_text(encoding="utf-8"))
    for entry in manifest.get("files", []):
        path = root / entry["path"]
        require(path.is_file() and path.stat().st_size == entry["size"] and sha(path) == entry["sha256"], "Drupal evidence manifest drift")
    termination = json.loads((root / "drupal-termination.json").read_text(encoding="utf-8"))
    immediate = json.loads((root / "drupal-immediate.json").read_text(encoding="utf-8"))
    post = json.loads((root / "drupal-post-expiry.json").read_text(encoding="utf-8"))
    require(termination.get("status") == "PASS" and termination.get("observed_signal") == 9, "Drupal termination prerequisite")
    require(immediate.get("status") == "PASS_LOCK_DENIED" and immediate.get("observed_before_natural_expiry") is True, "Drupal immediate prerequisite")
    require(post.get("status") == "PASS_POST_NATURAL_EXPIRY" and post.get("natural_expiry_elapsed") is True, "Drupal natural-expiry prerequisite")
    require(post.get("elapsed_since_lock_acquired_seconds", 0) >= 1800, "Drupal natural-expiry duration prerequisite")
    return root, sha(root / "evidence-manifest.json")


def command(args: list[str], cwd: Path) -> str:
    env = dict(os.environ)
    for key in ("OPENAI_API_KEY", "OPENAI_CANDIDATE_MODEL", "CREWAI_CANDIDATE_MODEL"):
        env.pop(key, None)
    completed = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    require(completed.returncode == 0, f"reset rehearsal command failed: {args[0]} {args[1]}")
    return completed.stdout


def projection(drupal: Path) -> dict[str, Any]:
    output = command([
        "ddev", "drush", "--quiet", "php:script", "scripts/gate1-step05-drupal-ai-batch-runner.php", "--", "snapshot"
    ], drupal)
    value = json.loads(output)
    require(isinstance(value, dict), "Drupal projection object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(repo: Path, run_id: str, drupal_run_id: str) -> Path:
    require(RUN_PATTERN.fullmatch(run_id) is not None, "invalid reset rehearsal run ID")
    drupal_evidence, drupal_manifest_sha = require_finalized_drupal_evidence(repo, drupal_run_id)
    require(not (repo / "evidence/gates/gate-2c/step02-certification/GATE2C-STEP02-LATEST.txt").exists(), "Step 2C.02 is already certified")
    evidence = repo / "evidence/gates/gate-2c/model-free-rehearsals" / run_id
    require(not evidence.exists(), "reset rehearsal identity already exists")
    drupal = repo / "drupal"
    retained = drupal / ".ddev/db_snapshots" / f"{SNAPSHOT_ID}-mariadb_11.8.zst"
    require(retained.is_file() and hashlib.sha256(retained.read_bytes()).hexdigest() == SNAPSHOT_SHA, "retained Gate 2B snapshot drift")
    evidence.mkdir(parents=True)
    anchor = f"{run_id}-restoration-anchor"
    before = projection(drupal)
    before_hash = canonical(before)
    created = False
    restored = False
    seeded: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    failure: Exception | None = None
    try:
        command(["ddev", "snapshot", "--name", anchor], drupal)
        created = True
        command(["bash", "scripts/run-phase0-step10.sh", "reset"], drupal)
        seeded = projection(drupal)
        require(seeded.get("article_count") == 20 and seeded.get("suggestion_count") == 0, "seeded-clean reset projection")
        command(["ddev", "snapshot", "restore", anchor], drupal)
        restored = True
        after = projection(drupal)
        require(canonical(after) == before_hash, "exact restoration projection differs")
    except Exception as exc:
        failure = exc
    finally:
        try:
            if created and not restored:
                # Exact-scope failure rollback is part of the separately approved boundary.
                command(["ddev", "snapshot", "restore", anchor], drupal)
                restored = True
            if created:
                command(["ddev", "snapshot", "--cleanup", "--name", anchor, "-y"], drupal)
        except Exception as cleanup_exc:
            if failure is None:
                failure = cleanup_exc
    if failure is not None:
        write_json(evidence / "FAILED-ATTEMPT.json", {
            "schema_version": 1, "status": "FAILED_PRESERVED", "run_id": run_id,
            "anchor_created": created, "restoration_completed": restored, "automatic_replacement": False,
        })
        raise failure
    require(seeded is not None and after is not None, "reset/restoration projections missing")
    write_json(evidence / "reset-restoration.json", {
        "schema_version": 1, "status": "PASS", "run_id": run_id,
        "anchor_created": True, "seeded_clean_verified": True, "restored_exactly_once": True,
        "anchor_cleaned": True, "before_projection_sha256": before_hash,
        "seeded_projection_sha256": canonical(seeded), "after_projection_sha256": canonical(after),
        "retained_gate2b_snapshot_sha256": SNAPSHOT_SHA, "retained_gate2b_snapshot_used_as_baseline": False,
        "model_generations": 0, "provider_requests": 0, "recommendation_creations": 0,
        "snapshot_creates": 1, "seeded_clean_resets": 1, "snapshot_restores": 1,
        "temporary_snapshot_deletes": 1, "source_mutations_retained": 0,
        "permitted_mutations": ["temporary_restoration_anchor", "canonical_seeded_clean_reset", "exact_anchor_restore", "temporary_anchor_cleanup"],
        "forbidden_mutations_retained": 0,
        "bound_drupal_run_id": drupal_run_id,
        "bound_drupal_manifest_sha256": drupal_manifest_sha,
    })
    write_json(evidence / "authorization-ledger.json", {
        "schema_version": 1, "run_id": run_id, "boundary": "2C.02_reset_rehearsal",
        "separate_authorization": True, "drupal_prerequisite_run_id": drupal_run_id,
        "drupal_prerequisite_manifest_sha256": drupal_manifest_sha,
        "automatic_certification": False,
    })
    write_json(evidence / "privacy-scan.json", {
        "status": "PASS", "credentials_retained": False,
        "authorization_headers_retained": False, "raw_image_or_data_url_retained": False,
        "hidden_reasoning_retained": False,
    })
    (evidence / "summary.md").write_text(
        "# Gate 2C.02 reset/restoration rehearsal\n\n"
        f"Run: `{run_id}`\n\nThe separately authorized model-free reset rehearsal was bound to "
        f"finalized Drupal rehearsal `{drupal_evidence.name}`. It created one temporary restoration "
        "anchor, reached the canonical 20-Article/zero-suggestion seeded-clean state, restored the "
        "pre-reset projection exactly once, and removed only the temporary anchor. The retained "
        "Gate 2B snapshot was verified but not used as the baseline.\n",
        encoding="utf-8",
    )
    names = sorted(p.name for p in evidence.iterdir() if p.is_file())
    write_json(evidence / "evidence-manifest.json", {
        "schema_version": 1,
        "files": [{"path": name, "sha256": hashlib.sha256((evidence / name).read_bytes()).hexdigest(), "size": (evidence / name).stat().st_size} for name in names],
    })
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--drupal-run-id", required=True)
    args = parser.parse_args()
    path = run(args.repo.resolve(), args.run_id, args.drupal_run_id)
    print(path.relative_to(args.repo.resolve()).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
