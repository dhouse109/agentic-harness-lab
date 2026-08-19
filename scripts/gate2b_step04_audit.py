#!/usr/bin/env python3
"""Permanent fail-closed auditor for Gate 2B Step 2B.04 and its closure."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

import jsonschema


PREDECESSOR = "7629434b04d04154b9f219e1d93ed772401a1288"
LOCK_SHA = "855e5edff2cb86eb64ea9856d239b19010e7d3b1f80c40e370ed81d66b8e4e7c"
STEP03_MANIFEST = "6b76549c442d3f27eb7278a41c69dad4e7313bd673adf331012d9c02c2216dad"
STEP03_SUMMARY = "33d6bc403fe60556e4fc4d823eaf98d7d23b9c9973f66a1ccd283fce316c35ec"
SOURCE_RUN = "crewai-20260818T215017Z-8e03fc95"
SOURCE_MANIFEST_SHA = "c6115ffea4b7ceefb7858e6b482713fc92998dcf2bde7bc6de8831d583665aaf"
SOURCE_SUMMARY_SHA = "5cd324d26b866c83d9728e7634887bcf3ccc46c2df5f4fc6a9563069f71ef490"
SOURCE_TREE_SHA = "0d0e2c6af5e328a52aa867e4cbc3ade787e13833fece34009854212d2cda69be"
OPEN_MAIN_SHA = "9c0ca1e75def573857de1ecfcb7a392381848dcbd8e27eebf8288908f1b271f8"
SOURCE_PROJECTION_SHA = "f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17"
RECOMMENDATION_UUID = "1878ae86-834c-4813-9134-4c3b8d0833c9"
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
    "authorization.json", "closure-provenance.json", "drupal-observation.json",
    "sqlite-semantic-inspection.json", "privacy-scan.json", "summary.json",
    "summary.md", "evidence-manifest.json",
}
EXPECTED_METHODS = [
    "discover_target", "retrieve_context", "invoke_model",
    "assemble_recommendation", "submit_and_observe",
]
LIFECYCLE_DOCS = (
    "AGENTS.md", "PLAN.md", "README.md", "docs/CURRENT-STATUS.md",
    "docs/CODEX-GATE-2B-RUNBOOK.md",
)


def need(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_static(repo: Path) -> None:
    need(subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", PREDECESSOR, "HEAD"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode == 0, "Step 2B.03 merged predecessor is absent from ancestry")
    need(sha(repo / "crewai/uv.lock") == LOCK_SHA, "CrewAI lock changed")
    step03 = repo / "evidence/gates/gate-2b/shared-operation-adapters/gate2b-step03-20260818T163812Z-7a58ef58"
    need(sha(step03 / "evidence-manifest.json") == STEP03_MANIFEST, "Step 2B.03 manifest changed")
    need(sha(step03 / "summary.json") == STEP03_SUMMARY, "Step 2B.03 summary changed")
    source = (repo / "crewai/agentic_harness_crewai/canonical_slice.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    need('api="responses"' in source and "max_retries=0" in source, "Native Responses one-request controls missing")
    need("SingleRequestInterceptor" in source and "ProviderRequestBudgetExceeded" in source,
         "Physical request budget control missing")
    need("SQLiteFlowPersistence" in source and "set_memory_storage_factory" in source,
         "Accepted persistence/memory controls missing")
    need("_skip_auto_memory =" not in source and "._skip_auto_memory" not in source,
         "Private memory bypass was selected")
    need("CheckpointConfig" not in source and "HumanFeedbackPending" not in source and "from_pending" not in source,
         "Later lifecycle boundary leaked into Step 2B.04")
    need("Task(" not in source and "guardrail_max_retries" not in source,
         "Task/guardrail correction path is present")
    need("learn=" not in source, "Learning/distillation inference path is present")
    need(not [node for node in ast.walk(tree) if isinstance(node, ast.While)], "Hidden while-loop retry path present")
    llm_calls = [node for node in calls if isinstance(node.func, ast.Attribute) and node.func.attr == "call"]
    need(len(llm_calls) == 1, f"Expected one LLM call site, found {len(llm_calls)}")
    need("build_tools" in source and "submit_recommendation" in source, "Accepted adapter boundary is not used")
    runner = (repo / "scripts/gate2b_step04_canonical_slice.py").read_text(encoding="utf-8")
    need('CREWAI_DISABLE_VERSION_CHECK", "true"' in runner and 'CREWAI_TESTING", "true"' in runner,
         "Pinned no-version-check/no-first-run-tracing controls are missing")
    for doc in LIFECYCLE_DOCS:
        text = (repo / doc).read_text(encoding="utf-8")
        need("gate-2b-step03-crewai-shared-operation-adapters-v1.0.0" in text,
             f"Step 2B.03 compatibility marker missing from {doc}")
        need("Step 2B.04" in text and "Gate 2C" in text, f"Lifecycle boundary missing from {doc}")


def audit_original(repo: Path) -> Path:
    root = repo / "evidence/gates/gate-2b/canonical-slice"
    need((root / "LATEST").read_text(encoding="utf-8").strip() == SOURCE_RUN,
         "Canonical LATEST no longer points to the accepted live run")
    runs = sorted(path.name for path in root.iterdir() if path.is_dir() and path.name.startswith("crewai-"))
    need(runs == [SOURCE_RUN], "A new canonical model-backed Step 2B.04 run exists")
    run = root / SOURCE_RUN
    actual = {path.name for path in run.iterdir() if path.is_file()}
    need(actual == set(ORIGINAL_HASHES), f"Original evidence set differs: {sorted(actual ^ set(ORIGINAL_HASHES))}")
    for name, expected in ORIGINAL_HASHES.items():
        need(sha(run / name) == expected, f"Original evidence mutation: {name}")
    manifest = load(run / "evidence-manifest.json")
    need({entry.get("path") for entry in manifest.get("entries", [])} == set(ORIGINAL_HASHES) - {"evidence-manifest.json"},
         "Original manifest coverage differs")
    for entry in manifest["entries"]:
        need(sha(run / entry["path"]) == entry["sha256"], f"Original manifest entry differs: {entry['path']}")
    summary = load(run / "summary.json")
    authorization = load(run / "authorization.json")
    accounting = load(run / "provider-accounting.json")
    source = load(run / "source-nonmutation.json")
    submission = load(run / "submission.json")
    persistence = load(run / "persistence-provenance.json")
    need(summary == {
        "canonical_sequence": 1, "continuation_claimed": False, "gate2c": "deferred_unclaimed",
        "live_submissions": 1, "model": "gpt-4.1-mini-2025-04-14", "provider_requests": 1,
        "review_status": "pending", "run_id": SOURCE_RUN, "schema_version": "1.0.0",
        "status": "pass", "step": "2B.04", "temperature": 0.0,
    }, "Original summary facts differ")
    counts = authorization.get("counts", {})
    expected_counts = {
        "logical_model_generations": 1, "actual_provider_requests": 1,
        "successful_provider_responses": 1, "provider_retries": 0, "transport_retries": 0,
        "guardrail_correction_retries": 0, "structured_repair_calls": 0,
        "fallback_provider_calls": 0, "learning_distillation_calls": 0,
        "feedback_collapse_calls": 0, "drupal_recommendation_mutations": 1,
        "source_content_mutations": 0, "authoritative_human_review_actions": 0,
        "dependency_changes": 0, "live_recommendation_submissions": 1, "gate2c_executions": 0,
    }
    need(counts == expected_counts, "Historical live authorization accounting differs")
    need(accounting.get("actual_provider_requests") == 1 and accounting.get("successful_provider_responses") == 1,
         "Historical provider accounting differs")
    need(source.get("article_source_sha256_before") == source.get("article_source_sha256_after") == SOURCE_PROJECTION_SHA,
         "Historical source projection proof differs")
    need(source.get("suggestion_count_before") == 0 and source.get("suggestion_count_after") == 1,
         "Historical suggestion transition differs")
    result = submission.get("result", {})
    need(result.get("uuid") == RECOMMENDATION_UUID and result.get("node_id") == 21 and result.get("revision_id") == 21,
         "Historical recommendation identity differs")
    need(result.get("status") == "pending" and submission.get("review_action_performed") is False,
         "Historical pending/no-review fact differs")
    need(persistence.get("sqlite_sha256") == OPEN_MAIN_SHA, "Open/running persistence hash differs")
    need(persistence.get("continuation_claimed") is False, "Persistence claim boundary differs")
    return run


def audit_runtime(repo: Path, closure: dict[str, Any]) -> None:
    runtime = repo / "crewai/.runtime/gate2b-step04" / SOURCE_RUN
    need(runtime.is_dir(), "Authoritative runtime directory is missing")
    actual = {path.name for path in runtime.iterdir() if path.is_file()}
    need(actual == set(RUNTIME), f"Runtime component set differs: {sorted(actual ^ set(RUNTIME))}")
    recorded = {
        Path(entry["relative_path"]).name: (entry["sha256"], entry["byte_size"], entry["present"])
        for entry in closure["post_process_close_file_set_provenance"]["runtime_components"]
    }
    need(set(recorded) == set(RUNTIME), "Closure runtime-component coverage differs")
    for name, expected in RUNTIME.items():
        path = runtime / name
        observed = (sha(path), path.stat().st_size)
        need(observed == expected, f"Current authoritative runtime differs: {name}")
        need(recorded[name] == (expected[0], expected[1], True), f"Closure runtime binding differs: {name}")


def audit_closure(repo: Path) -> str:
    root = repo / "evidence/gates/gate-2b/canonical-slice-closure"
    latest = root / "LATEST"
    need(latest.is_file(), "Required Step 2B.04 closure provenance is absent")
    closure_id = latest.read_text(encoding="utf-8").strip()
    run = root / closure_id
    need(run.is_dir(), "Closure LATEST target is absent")
    actual = {path.name for path in run.iterdir() if path.is_file()}
    need(actual == CLOSURE_FILES, f"Closure evidence set differs: {sorted(actual ^ CLOSURE_FILES)}")
    manifest = load(run / "evidence-manifest.json")
    entries = manifest.get("entries", [])
    need(manifest.get("algorithm") == "sha256", "Closure manifest algorithm differs")
    need({entry.get("path") for entry in entries} == CLOSURE_FILES - {"evidence-manifest.json"},
         "Closure manifest coverage differs")
    for entry in entries:
        need(sha(run / entry["path"]) == entry["sha256"], f"Closure evidence hash mismatch: {entry['path']}")
    closure = load(run / "closure-provenance.json")
    schema = load(repo / "shared/schemas/gate2b-step04-closure-provenance.schema.json")
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(closure)
    need(closure.get("closure_id") == closure_id, "Closure ID does not match its directory")
    source = closure.get("source_run", {})
    need(source.get("run_id") == SOURCE_RUN, "Closure is bound to the wrong live run")
    need(source.get("manifest_sha256") == SOURCE_MANIFEST_SHA, "Closure is bound to the wrong original manifest")
    need(source.get("summary_sha256") == SOURCE_SUMMARY_SHA, "Closure is bound to the wrong original summary")
    need(source.get("whole_tree_sha256") == SOURCE_TREE_SHA and source.get("file_count") == 20,
         "Closure original-tree binding differs")
    open_state = closure.get("open_running_persistence_provenance", {})
    need(open_state.get("recorded_main_file_sha256") == OPEN_MAIN_SHA,
         "Closure open/running main-file binding differs")
    need(open_state.get("byte_identity_with_post_close_main_required") is False,
         "Closure incorrectly requires open/post-close byte identity")
    linked = closure.get("linked_artifacts", {})
    need(linked == {
        "authorization_sha256": sha(run / "authorization.json"),
        "drupal_observation_sha256": sha(run / "drupal-observation.json"),
        "sqlite_semantic_inspection_sha256": sha(run / "sqlite-semantic-inspection.json"),
    }, "Closure linked-artifact hashes differ")
    statements = closure.get("statements", {})
    need(all(statements.get(key) is False for key in (
        "model_or_provider_action_during_capture", "drupal_mutation_during_capture",
        "source_content_mutation_during_capture", "human_review_during_capture",
        "experiment_replayed", "original_evidence_rewritten", "authoritative_runtime_mutated",
    )), "Closure action/nonmutation statements differ")
    need(statements.get("semantic_inspection_used_disposable_copy_only") is True,
         "Closure semantic-inspection scope differs")
    audit_runtime(repo, closure)
    semantic = load(run / "sqlite-semantic-inspection.json")
    need(semantic.get("status") == "pass" and semantic.get("authoritative_database_opened") is False,
         "Disposable SQLite inspection boundary differs")
    need(semantic.get("sqlite_quick_check") == "ok", "Disposable SQLite quick_check differs")
    need(semantic.get("observed_flow_method_states") == EXPECTED_METHODS,
         "Persisted Flow method-state observations differ")
    need(semantic.get("flow_state_row_count") == 5 and semantic.get("flow_uuid") == SOURCE_RUN,
         "Persisted Flow identity/count differs")
    need(semantic.get("terminal_status") == "awaiting_human_review"
         and semantic.get("terminal_lifecycle_stage") == "awaiting_drupal_authoritative_review",
         "Persisted terminal Flow state differs")
    need(semantic.get("recommendation_uuid") == RECOMMENDATION_UUID
         and semantic.get("recommendation_revision_id") == 21
         and semantic.get("review_status") == "pending", "Persisted recommendation state differs")
    need(semantic.get("pending_feedback_row_count") == 0, "Unexpected pending-feedback persistence")
    drupal = load(run / "drupal-observation.json")
    recommendation = drupal.get("recommendation", {})
    need(drupal.get("article_count") == 20 and drupal.get("target_count") == 12
         and drupal.get("suggestion_count") == 1, "Closure Drupal counts differ")
    need(drupal.get("source_projection_sha256") == SOURCE_PROJECTION_SHA, "Closure source projection differs")
    need(recommendation.get("uuid") == RECOMMENDATION_UUID and recommendation.get("node_id") == 21
         and recommendation.get("revision_id") == 21 and recommendation.get("status") == "pending",
         "Closure Drupal recommendation differs")
    need(recommendation.get("reviewer_username") is None and recommendation.get("reviewed_at") is None,
         "Closure contains a human-review action")
    authorization = load(run / "authorization.json")
    need(authorization.get("historical_live_run_totals") == {
        "logical_model_generations": 1, "actual_provider_requests": 1,
        "successful_provider_responses": 1, "live_recommendation_submissions": 1,
        "drupal_recommendation_mutations": 1,
    }, "Closure historical totals differ")
    need(authorization.get("closure_repair_activity") == {
        "logical_model_generations": 0, "actual_provider_requests": 0,
        "successful_provider_responses": 0, "live_recommendation_submissions": 0,
        "drupal_mutations": 0, "source_content_mutations": 0, "human_review_actions": 0,
        "new_model_backed_step2b04_runs": 0, "gate2c_executions": 0,
    }, "Closure repair activity budget differs")
    privacy = load(run / "privacy-scan.json")
    need(privacy.get("status") == "pass" and privacy.get("findings") == [], "Closure privacy scan failed")
    summary = load(run / "summary.json")
    need(summary.get("status") == "pass" and summary.get("closure_id") == closure_id,
         "Closure summary differs")
    need(summary.get("model_free") is True and summary.get("inference_performed") is False
         and summary.get("drupal_mutation_performed") is False
         and summary.get("original_live_evidence_replaced") is False,
         "Closure classification differs")
    return closure_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--phase", choices=("active", "permanent"), default="permanent")
    args = parser.parse_args()
    repo = args.repo.resolve()
    audit_static(repo)
    if args.phase == "active":
        need(not (repo / "evidence/gates/gate-2b/canonical-slice").exists(),
             "Active package must not already have Step 2B.04 evidence")
        print("[PASS] Gate 2B Step 2B.04 active static audit passed.")
        return 0
    audit_original(repo)
    closure_id = audit_closure(repo)
    print(f"[PASS] Gate 2B Step 2B.04 permanent audit: {SOURCE_RUN} + {closure_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
