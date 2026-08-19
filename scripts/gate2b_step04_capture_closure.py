#!/usr/bin/env python3
"""Capture model-free post-process-close provenance for accepted Step 2B.04."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tempfile
from typing import Any


SOURCE_RUN = "crewai-20260818T215017Z-8e03fc95"
SOURCE_MANIFEST_SHA = "c6115ffea4b7ceefb7858e6b482713fc92998dcf2bde7bc6de8831d583665aaf"
SOURCE_SUMMARY_SHA = "5cd324d26b866c83d9728e7634887bcf3ccc46c2df5f4fc6a9563069f71ef490"
SOURCE_TREE_SHA = "0d0e2c6af5e328a52aa867e4cbc3ade787e13833fece34009854212d2cda69be"
OPEN_MAIN_SHA = "9c0ca1e75def573857de1ecfcb7a392381848dcbd8e27eebf8288908f1b271f8"
SOURCE_PROJECTION_SHA = "f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17"
RECOMMENDATION_UUID = "1878ae86-834c-4813-9134-4c3b8d0833c9"
EXPECTED_METHODS = [
    "discover_target",
    "retrieve_context",
    "invoke_model",
    "assemble_recommendation",
    "submit_and_observe",
]
ORIGINAL_HASHES = {
    "authorization.json": "3c70575b2ba611d6fbde86d820655683651f991e7416cdfc3c406200be6ee204",
    "canonical-target.json": "76f76543a2bd84f7bd40fd0b8647ef265eb1b2bf67687e020d4f2d9caee9d97b",
    "context-provenance.json": "84eb726c6bab38752c8553acde343198731ee0ebed7c393a1122cb7a7128a1d3",
    "events.jsonl": "2b883bb0f726ca74c61f925c1ed969eadde72acc84f4e32e198b552718882a7d",
    "evidence-manifest.json": SOURCE_MANIFEST_SHA,
    "flow-state.json": "fe0f0635b0ca9a6aa88e36ab554365048df7ef47fd410a6a1f56bcfa7b89b3f7",
    "persistence-provenance.json": "4048d5daed9b30a0d2702f5530dafaeafb5bb13e5bdba30117397de0ff5823a1",
    "pinned-source-provenance.json": "b867271da4d3db4cad4a9153349a72427e5704d39de3ca65b8227e3081d3e611",
    "predecessor.json": "4a68694af35861f3cd4a46797e8f8f88e1dd40113deedfb93ae077fb5748e5b4",
    "privacy-scan.json": "b61286924dfca1a79446ef780ee713119a74865bfcc1dfa998f4b264f848e3ba",
    "prompt-provenance.json": "f5a1b4459071ae72cc5248ccfe66faf750fbe53a10ee8581369c7b2598e01d5e",
    "provider-accounting.json": "450b5f433f2ccb94fbb37040e98e57a32b63ef4f5dc453f7d5d25f7ba4f658eb",
    "provider-metadata.json": "888bebe59df222505e330c0942cee1165190d10b860ee0f8504144a3c8545c81",
    "raw-model-output.json": "2fbba6603b327b7a507d7936e91394b7ce3ce1fa141c1513b4276529734db433",
    "recommendation.json": "40d1d685059618e2bb74dc2c830a44b8fbc4de96d9d7d6090ec6b4bc810171c6",
    "source-nonmutation.json": "be5c79fd36fa6638a9a35577aa5f9b87db5acc34e185ff254d8255701a8da781",
    "stage-results.json": "2dfcab1154891a866c5dc16c12bce1f0020e534686e8719eacfeff162b6b7c23",
    "submission.json": "5ae568ff5c11ef8668f2b313053881ed7fbc37d3fe6566f99d0276d5cea7a48b",
    "summary.json": SOURCE_SUMMARY_SHA,
    "summary.md": "19a5d015d19131ff4af55212ea7107eaef4dfa3df2ebb1d4db5cfb4fffb6b02d",
}
RUNTIME = {
    "flow-state.sqlite": ("d0fd3ac373b6af0aace07b7eed6813ebea28ceab37ab47265da2da94a24acff2", 45056),
    "flow-state.sqlite-wal": ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", 0),
    "flow-state.sqlite-shm": ("fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb", 32768),
}
CLOSURE_FILES = {
    "authorization.json",
    "closure-provenance.json",
    "drupal-observation.json",
    "sqlite-semantic-inspection.json",
    "privacy-scan.json",
    "summary.json",
    "summary.md",
    "evidence-manifest.json",
}


def need(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_original(run: Path) -> None:
    actual = {path.name for path in run.iterdir() if path.is_file()}
    need(actual == set(ORIGINAL_HASHES), f"Original evidence set differs: {sorted(actual ^ set(ORIGINAL_HASHES))}")
    for name, expected in ORIGINAL_HASHES.items():
        need(sha(run / name) == expected, f"Original evidence changed: {name}")
    persistence = load(run / "persistence-provenance.json")
    need(persistence.get("sqlite_sha256") == OPEN_MAIN_SHA, "Original open-state persistence hash differs")


def verify_runtime(runtime: Path) -> list[dict[str, Any]]:
    actual = {path.name for path in runtime.iterdir() if path.is_file()}
    need(actual == set(RUNTIME), f"Runtime component set differs: {sorted(actual ^ set(RUNTIME))}")
    result = []
    for name, (expected_sha, expected_size) in RUNTIME.items():
        path = runtime / name
        observed_sha = sha(path)
        observed_size = path.stat().st_size
        need(observed_sha == expected_sha, f"Authoritative runtime hash changed: {name}")
        need(observed_size == expected_size, f"Authoritative runtime size changed: {name}")
        result.append({
            "relative_path": f"crewai/.runtime/gate2b-step04/{SOURCE_RUN}/{name}",
            "sha256": observed_sha,
            "byte_size": observed_size,
            "present": True,
        })
    return result


def process_closure(runtime: Path) -> dict[str, Any]:
    targets = {path.resolve() for path in runtime.iterdir() if path.is_file()}
    open_matches = 0
    runner_matches = 0
    checked_processes = 0
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            checked_processes += 1
            cmdline = (proc / "cmdline").read_bytes()
            if b"gate2b_step04_canonical_slice.py" in cmdline and b"--mode\x00run" in cmdline:
                runner_matches += 1
            for fd in (proc / "fd").iterdir():
                try:
                    if fd.resolve() in targets:
                        open_matches += 1
                except (FileNotFoundError, PermissionError, OSError):
                    continue
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
    need(open_matches == 0, "An authoritative runtime component is open by a live process")
    need(runner_matches == 0, "A live Step 2B.04 model runner process is present")
    return {
        "method": "Linux /proc process scan plus exact open-file-descriptor scan",
        "checked_process_count": checked_processes,
        "matching_live_runner_processes": runner_matches,
        "matching_open_runtime_file_descriptors": open_matches,
        "process_closed": True,
    }


def inspect_disposable(runtime: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="gate2b-step04-closure-sqlite-") as temp_name:
        temp = Path(temp_name)
        for name in RUNTIME:
            shutil.copy2(runtime / name, temp / name)
            need(sha(temp / name) == RUNTIME[name][0], f"Disposable copy differs: {name}")
        database = temp / "flow-state.sqlite"
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        try:
            quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
            tables = [row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )]
            rows = connection.execute(
                "SELECT flow_uuid, method_name, state_json FROM flow_states ORDER BY id"
            ).fetchall()
            pending_count = connection.execute("SELECT COUNT(*) FROM pending_feedback").fetchone()[0]
        finally:
            connection.close()
        need(quick_check == "ok", "Disposable SQLite quick_check failed")
        need(tables == ["flow_states", "pending_feedback", "sqlite_sequence"], "SQLite table set differs")
        need([row[1] for row in rows] == EXPECTED_METHODS, "Persisted Flow method sequence differs")
        need(all(row[0] == SOURCE_RUN for row in rows), "Persisted Flow UUID differs")
        states = [json.loads(row[2]) for row in rows]
        terminal = states[-1]
        need(terminal.get("run_id") == SOURCE_RUN, "Terminal persisted run ID differs")
        need(terminal.get("lifecycle_stage") == "awaiting_drupal_authoritative_review", "Terminal lifecycle differs")
        need(terminal.get("status") == "awaiting_human_review", "Terminal Flow status differs")
        need(terminal.get("recommendation_id") == RECOMMENDATION_UUID, "Persisted recommendation differs")
        need(terminal.get("recommendation_revision_id") == 21, "Persisted recommendation revision differs")
        need(terminal.get("review_status") == "pending", "Persisted review status differs")
        need(pending_count == 0, "Unexpected pending_feedback rows")
        return {
            "status": "pass",
            "inspection_scope": "exact disposable copy of complete SQLite/WAL/SHM file-set",
            "authoritative_database_opened": False,
            "sqlite_quick_check": quick_check,
            "tables": tables,
            "flow_state_row_count": len(rows),
            "expected_flow_method_states": EXPECTED_METHODS,
            "observed_flow_method_states": [row[1] for row in rows],
            "flow_uuid": SOURCE_RUN,
            "terminal_lifecycle_stage": terminal["lifecycle_stage"],
            "terminal_status": terminal["status"],
            "recommendation_uuid": terminal["recommendation_id"],
            "recommendation_revision_id": terminal["recommendation_revision_id"],
            "review_status": terminal["review_status"],
            "pending_feedback_row_count": pending_count,
            "raw_state_retained": False,
        }


def read_drupal(repo: Path) -> dict[str, Any]:
    snapshot_result = subprocess.run(
        ["ddev", "drush", "--quiet", "php:script", "scripts/gate1-step04-canonical-vertical-slice.php", "--", "snapshot"],
        cwd=repo / "drupal", check=True, text=True, capture_output=True,
    )
    snapshot = json.loads(snapshot_result.stdout)
    php = r'''$c=\Drupal::getContainer(); $u=$c->get("entity_type.manager")->getStorage("user")->loadByProperties(["name"=>"agent_bot"]); $a=reset($u); $cu=$c->get("current_user"); $o=$cu->getAccount(); try {$cu->setAccount($a); $s=$c->get("agentic_harness_tools.recommendation_status_provider")->get("1878ae86-834c-4813-9134-4c3b8d0833c9"); $s["node_id"]=21; $n=$c->get("entity_type.manager")->getStorage("node")->load(21); $s["bundle"]=$n?->bundle(); print json_encode($s, JSON_UNESCAPED_SLASHES).PHP_EOL;} finally {$cu->setAccount($o);}'''
    status_result = subprocess.run(
        ["ddev", "drush", "--quiet", "php:eval", php],
        cwd=repo / "drupal", check=True, text=True, capture_output=True,
    )
    status = json.loads(status_result.stdout)
    return {
        "status": "pass",
        "inspection": "read_only_Drupal_snapshot_and_recommendation_status_provider",
        "article_count": snapshot.get("article_count"),
        "target_count": snapshot.get("target_count"),
        "suggestion_count": snapshot.get("suggestion_count"),
        "source_projection_sha256": snapshot.get("article_source_sha256"),
        "recommendation": status,
        "drupal_write_performed": False,
    }


def validate_drupal(value: dict[str, Any]) -> None:
    recommendation = value.get("recommendation", {})
    need(value.get("article_count") == 20 and value.get("target_count") == 12, "Drupal dataset differs")
    need(value.get("suggestion_count") == 1, "Drupal suggestion count differs")
    need(value.get("source_projection_sha256") == SOURCE_PROJECTION_SHA, "Drupal source projection differs")
    need(recommendation.get("uuid") == RECOMMENDATION_UUID, "Drupal recommendation UUID differs")
    need(recommendation.get("node_id") == 21 and recommendation.get("revision_id") == 21, "Drupal recommendation identity differs")
    need(recommendation.get("status") == "pending", "Drupal recommendation is no longer pending")
    need(recommendation.get("reviewer_username") is None and recommendation.get("reviewed_at") is None,
         "Drupal recommendation has human-review metadata")
    need(recommendation.get("bundle") == "alt_text_suggestion", "Drupal recommendation bundle differs")
    need(value.get("drupal_write_performed") is False, "Drupal observation claims a write")


def privacy_scan(root: Path) -> dict[str, Any]:
    patterns = [
        re.compile(rb"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(rb"(?:Basic|Bearer) [A-Za-z0-9+/=_-]{16,}"),
        re.compile(rb"data:image/[^;]+;base64,"),
        re.compile(rb"(?i)chain[-_ ]of[-_ ]thought|hidden reasoning"),
    ]
    findings = []
    scanned = []
    for path in sorted(root.iterdir()):
        if not path.is_file() or path.name in {"privacy-scan.json", "evidence-manifest.json"}:
            continue
        scanned.append(path.name)
        data = path.read_bytes()
        if any(pattern.search(data) for pattern in patterns):
            findings.append(path.name)
    return {"status": "pass" if not findings else "fail", "files_scanned": scanned, "findings": findings}


def capture(repo: Path, output: Path, drupal_fixture: Path | None) -> None:
    closure_root = repo / "evidence/gates/gate-2b/canonical-slice-closure"
    need(output.parent.resolve() == closure_root.resolve(), "Closure output is outside the separate closure root")
    need(re.fullmatch(r"gate2b-step04-closure-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}", output.name) is not None,
         "Closure ID has an invalid shape")
    need(not output.exists(), "Closure output already exists")
    source = repo / "evidence/gates/gate-2b/canonical-slice" / SOURCE_RUN
    runtime = repo / "crewai/.runtime/gate2b-step04" / SOURCE_RUN
    verify_original(source)
    runtime_components = verify_runtime(runtime)
    closure_method = process_closure(runtime)
    drupal_before = load(drupal_fixture) if drupal_fixture else read_drupal(repo)
    validate_drupal(drupal_before)
    semantic = inspect_disposable(runtime)
    drupal_after = load(drupal_fixture) if drupal_fixture else read_drupal(repo)
    validate_drupal(drupal_after)
    need(drupal_before == drupal_after, "Drupal read-only observations changed during closure capture")
    verify_original(source)
    need(verify_runtime(runtime) == runtime_components, "Authoritative runtime changed during closure capture")

    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.parent / f".{output.name}.tmp-{os.getpid()}"
    need(not temp.exists(), "Closure temporary path already exists")
    temp.mkdir()
    try:
        authorization = {
            "status": "pass",
            "historical_live_run_totals": {
                "logical_model_generations": 1,
                "actual_provider_requests": 1,
                "successful_provider_responses": 1,
                "live_recommendation_submissions": 1,
                "drupal_recommendation_mutations": 1,
            },
            "closure_repair_activity": {
                "logical_model_generations": 0,
                "actual_provider_requests": 0,
                "successful_provider_responses": 0,
                "live_recommendation_submissions": 0,
                "drupal_mutations": 0,
                "source_content_mutations": 0,
                "human_review_actions": 0,
                "new_model_backed_step2b04_runs": 0,
                "gate2c_executions": 0,
            },
        }
        write_json(temp / "authorization.json", authorization)
        write_json(temp / "drupal-observation.json", drupal_before)
        write_json(temp / "sqlite-semantic-inspection.json", semantic)
        captured_at = now()
        closure = {
            "schema_version": "1.0.0",
            "step": "2B.04",
            "closure_id": output.name,
            "status": "pass",
            "classification": "post_close_provenance_model_free_evidence_closure",
            "source_run": {
                "run_id": SOURCE_RUN,
                "relative_path": f"evidence/gates/gate-2b/canonical-slice/{SOURCE_RUN}",
                "file_count": 20,
                "manifest_sha256": SOURCE_MANIFEST_SHA,
                "summary_sha256": SOURCE_SUMMARY_SHA,
                "whole_tree_sha256": SOURCE_TREE_SHA,
            },
            "open_running_persistence_provenance": {
                "lifecycle_state": "open_running_wal_backed_capture",
                "artifact_relative_path": f"evidence/gates/gate-2b/canonical-slice/{SOURCE_RUN}/persistence-provenance.json",
                "artifact_sha256": ORIGINAL_HASHES["persistence-provenance.json"],
                "recorded_main_file_sha256": OPEN_MAIN_SHA,
                "byte_identity_with_post_close_main_required": False,
            },
            "post_process_close_file_set_provenance": {
                "captured_at": captured_at,
                "lifecycle_state": "post_process_close_file_set",
                "process_closure": closure_method,
                "authoritative_files_hashed_as_files_without_mutation": True,
                "authoritative_sqlite_opened": False,
                "runtime_components": runtime_components,
            },
            "linked_artifacts": {
                "authorization_sha256": sha(temp / "authorization.json"),
                "drupal_observation_sha256": sha(temp / "drupal-observation.json"),
                "sqlite_semantic_inspection_sha256": sha(temp / "sqlite-semantic-inspection.json"),
            },
            "statements": {
                "model_or_provider_action_during_capture": False,
                "drupal_mutation_during_capture": False,
                "source_content_mutation_during_capture": False,
                "human_review_during_capture": False,
                "experiment_replayed": False,
                "original_evidence_rewritten": False,
                "authoritative_runtime_mutated": False,
                "semantic_inspection_used_disposable_copy_only": True,
            },
        }
        write_json(temp / "closure-provenance.json", closure)
        summary = {
            "schema_version": "1.0.0",
            "step": "2B.04",
            "closure_id": output.name,
            "source_run_id": SOURCE_RUN,
            "status": "pass",
            "classification": "post_close_provenance",
            "model_free": True,
            "inference_performed": False,
            "drupal_mutation_performed": False,
            "original_live_evidence_replaced": False,
        }
        write_json(temp / "summary.json", summary)
        (temp / "summary.md").write_text(
            "# Gate 2B Step 2B.04 post-close provenance\n\n"
            f"Closure: `{output.name}`\n\nSource live run: `{SOURCE_RUN}`\n\n"
            "Status: **PASS**\n\nThis model-free evidence closure binds the immutable open/WAL-state live evidence "
            "to the distinct post-process-close SQLite/WAL/SHM file-set. It does not replay the experiment, "
            "call a provider, submit or review a recommendation, or mutate Drupal source content.\n",
            encoding="utf-8",
        )
        scan = privacy_scan(temp)
        write_json(temp / "privacy-scan.json", scan)
        need(scan["status"] == "pass", "Closure privacy scan failed")
        entries = [
            {"path": name, "sha256": sha(temp / name)}
            for name in sorted(CLOSURE_FILES - {"evidence-manifest.json"})
        ]
        write_json(temp / "evidence-manifest.json", {"algorithm": "sha256", "entries": entries})
        need({path.name for path in temp.iterdir() if path.is_file()} == CLOSURE_FILES,
             "Closure evidence set differs before promotion")
        temp.rename(output)
    except Exception:
        shutil.rmtree(temp, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--drupal-observation-file", type=Path)
    args = parser.parse_args()
    capture(args.repo.resolve(), args.output.resolve(),
            args.drupal_observation_file.resolve() if args.drupal_observation_file else None)
    print(f"[PASS] Model-free Step 2B.04 post-close provenance captured: {args.output.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
