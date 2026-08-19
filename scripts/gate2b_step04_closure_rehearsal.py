#!/usr/bin/env python3
"""Disposable full rehearsal and negative controls for the Step 2B.04 closure."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Callable


SOURCE_RUN = "crewai-20260818T215017Z-8e03fc95"
CLOSURE_ID = "gate2b-step04-closure-20260819T120000Z-deadbeef"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def snapshot(repo: Path) -> dict[str, str]:
    roots = [
        repo / "evidence/gates/gate-2b/canonical-slice" / SOURCE_RUN,
        repo / "crewai/.runtime/gate2b-step04" / SOURCE_RUN,
    ]
    result: dict[str, str] = {}
    for root in roots:
        for path in sorted(root.iterdir()):
            if path.is_file():
                result[path.relative_to(repo).as_posix()] = sha(path)
    return result


def copy_dirty(source: Path, destination: Path) -> None:
    output = subprocess.run(
        ["git", "-C", str(source), "status", "--porcelain=v1", "--untracked-files=all"],
        check=True, text=True, capture_output=True,
    ).stdout
    for line in output.splitlines():
        relative = line[3:]
        if " -> " in relative:
            relative = relative.split(" -> ", 1)[1]
        src = source / relative
        dst = destination / relative
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def overlay_package(package: Path, repo: Path) -> None:
    templates = package / "templates"
    for path in templates.rglob("*"):
        if path.is_file():
            relative = path.relative_to(templates)
            destination = repo / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)


def rehash_manifest(closure: Path) -> None:
    manifest = load(closure / "evidence-manifest.json")
    for entry in manifest["entries"]:
        entry["sha256"] = sha(closure / entry["path"])
    write_json(closure / "evidence-manifest.json", manifest)


def audit(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(repo / "scripts/gate2b_step04_audit.py"), "--repo", str(repo), "--phase", "permanent"],
        text=True, capture_output=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    args = parser.parse_args()
    source = args.repo.resolve()
    package = args.package.resolve()
    work = args.work_root.resolve()
    clone = work / "repo"
    subprocess.run(["git", "clone", "--quiet", "--shared", str(source), str(clone)], check=True)
    copy_dirty(source, clone)
    overlay_package(package, clone)
    baseline = snapshot(clone)
    fixture = work / "drupal-observation.json"
    write_json(fixture, {
        "status": "pass",
        "inspection": "read_only_Drupal_snapshot_and_recommendation_status_provider",
        "article_count": 20,
        "target_count": 12,
        "suggestion_count": 1,
        "source_projection_sha256": "f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17",
        "recommendation": {
            "uuid": "1878ae86-834c-4813-9134-4c3b8d0833c9",
            "node_id": 21,
            "revision_id": 21,
            "status": "pending",
            "reviewer_username": None,
            "reviewed_at": None,
            "bundle": "alt_text_suggestion",
        },
        "drupal_write_performed": False,
    })
    closure_root = clone / "evidence/gates/gate-2b/canonical-slice-closure"
    closure = closure_root / CLOSURE_ID
    subprocess.run([
        sys.executable, str(clone / "scripts/gate2b_step04_capture_closure.py"),
        "--repo", str(clone), "--output", str(closure),
        "--drupal-observation-file", str(fixture),
    ], check=True, stdout=subprocess.DEVNULL)
    (closure_root / "LATEST").write_text(CLOSURE_ID + "\n", encoding="utf-8")
    valid = audit(clone)
    if valid.returncode != 0:
        raise RuntimeError(f"Valid closure audit failed: {valid.stderr}")
    if snapshot(clone) != baseline:
        raise RuntimeError("Valid closure rehearsal changed original evidence or authoritative runtime")

    closure_backup = work / "closure-valid"
    runtime = clone / "crewai/.runtime/gate2b-step04" / SOURCE_RUN
    runtime_backup = work / "runtime-valid"
    original = clone / "evidence/gates/gate-2b/canonical-slice" / SOURCE_RUN
    original_backup = work / "original-valid"
    shutil.copytree(closure, closure_backup)
    shutil.copytree(runtime, runtime_backup)
    shutil.copytree(original, original_backup)

    results: dict[str, bool] = {"valid_closure_passes": True}

    def restore() -> None:
        shutil.rmtree(closure)
        shutil.copytree(closure_backup, closure)
        shutil.rmtree(runtime)
        shutil.copytree(runtime_backup, runtime)
        shutil.rmtree(original)
        shutil.copytree(original_backup, original)
        (closure_root / "LATEST").write_text(CLOSURE_ID + "\n", encoding="utf-8")

    def expect_failure(name: str, mutate: Callable[[], None]) -> None:
        restore()
        mutate()
        results[name] = audit(clone).returncode != 0
        if not results[name]:
            raise RuntimeError(f"Negative control unexpectedly passed: {name}")

    def alter(path: Path) -> None:
        path.write_bytes(path.read_bytes() + b"negative-control")

    expect_failure("main_hash_altered_fails", lambda: alter(runtime / "flow-state.sqlite"))
    expect_failure("wal_hash_altered_fails", lambda: alter(runtime / "flow-state.sqlite-wal"))
    expect_failure("shm_hash_altered_fails", lambda: alter(runtime / "flow-state.sqlite-shm"))

    def change_closure(field: str, value: str) -> None:
        data = load(closure / "closure-provenance.json")
        data["source_run"][field] = value
        write_json(closure / "closure-provenance.json", data)
        rehash_manifest(closure)

    expect_failure("wrong_run_id_fails", lambda: change_closure("run_id", "crewai-20260818T215017Z-00000000"))
    expect_failure("wrong_original_manifest_fails", lambda: change_closure("manifest_sha256", "0" * 64))
    expect_failure("wrong_original_summary_fails", lambda: change_closure("summary_sha256", "0" * 64))

    def absent() -> None:
        (closure_root / "LATEST").unlink()

    expect_failure("closure_absent_fails", absent)

    def missing_runtime() -> None:
        (runtime / "flow-state.sqlite-wal").unlink()

    expect_failure("missing_runtime_component_fails", missing_runtime)

    def extra_runtime() -> None:
        (runtime / "flow-state.sqlite-journal").write_bytes(b"")

    expect_failure("extra_runtime_component_fails", extra_runtime)
    expect_failure("original_evidence_mutation_fails", lambda: alter(original / "summary.md"))

    def invalid_schema() -> None:
        data = load(closure / "closure-provenance.json")
        del data["classification"]
        write_json(closure / "closure-provenance.json", data)
        rehash_manifest(closure)

    expect_failure("invalid_closure_schema_fails", invalid_schema)

    def privacy_failure() -> None:
        data = load(closure / "privacy-scan.json")
        data["status"] = "fail"
        data["findings"] = ["negative-control"]
        write_json(closure / "privacy-scan.json", data)
        rehash_manifest(closure)

    expect_failure("privacy_failure_fails", privacy_failure)

    def count_failure() -> None:
        authorization = load(closure / "authorization.json")
        authorization["closure_repair_activity"]["actual_provider_requests"] = 1
        write_json(closure / "authorization.json", authorization)
        provenance = load(closure / "closure-provenance.json")
        provenance["linked_artifacts"]["authorization_sha256"] = sha(closure / "authorization.json")
        write_json(closure / "closure-provenance.json", provenance)
        rehash_manifest(closure)

    expect_failure("repair_request_count_inconsistent_fails", count_failure)

    def manifest_failure() -> None:
        manifest = load(closure / "evidence-manifest.json")
        manifest["entries"][0]["sha256"] = "0" * 64
        write_json(closure / "evidence-manifest.json", manifest)

    expect_failure("closure_manifest_mismatch_fails", manifest_failure)
    restore()
    if snapshot(clone) != baseline:
        raise RuntimeError("Negative-control rehearsal changed original evidence or authoritative runtime")
    print(json.dumps({
        "status": "pass",
        "model_free": True,
        "provider_requests": 0,
        "drupal_mutations": 0,
        "original_evidence_unchanged": True,
        "authoritative_runtime_unchanged": True,
        "semantic_sqlite_inspection": "pass_on_disposable_copy",
        "negative_controls": results,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
