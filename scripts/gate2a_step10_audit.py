#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, subprocess
from pathlib import Path

BASE = "f3daab20509c72aebf8536bcb7742f1a3e9f504f"
RUN08 = "evidence/results/langgraph/langgraph-20260810T231915Z-0027cd3e"
STEP09 = "evidence/gates/gate-2a/evidence-claims/gate2a-step09-20260811T025248Z-7e9c1f5f"
STEP02 = "evidence/gates/gate-2a/runtime-probe/gate2a-step02-20260809T224238Z-2361786"
STEP03 = "evidence/gates/gate-2a/tool-adapters/gate2a-step03-20260809T233127Z-2375581"
STEP03V = "evidence/gates/gate-2a/tool-adapters/gate2a-step03-verification-20260810T020210Z-2410520"
STEP04 = "evidence/gates/gate-2a/checkpoint-proof/gate2a-step04-20260810T034027Z-00250b07"
STEP05 = "evidence/gates/gate-2a/canonical-slice/gate2a-step05-20260810T140133Z-0025b888"
STEP06 = "evidence/gates/gate-2a/human-interrupt/gate2a-step06-20260810T162448Z-002692eb"
STEP07 = "evidence/gates/gate-2a/batch-runner/gate2a-step07-20260810T185629Z-00272cd1"
STEP08_GATE = "evidence/gates/gate-2a/fresh-batch/langgraph-20260810T231915Z-0027cd3e"
FREEZE_REL = "shared/contracts/GATE2A-LANGGRAPH-FREEZE.json"
PACKAGE = "gate-2a-step10-langgraph-certification-freeze-and-crewai-handoff-v1.0.1"
NEXT = "gate-2b-step01-crewai-contract-and-evidence-plan-v1.0.0"
OLD_FREEZES = {
    "shared/contracts/GATE05-SUBSTRATE-FREEZE.json": "99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a",
    "shared/contracts/GATE1-DRUPAL-AI-FREEZE.json": "2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd",
    "shared/contracts/GATE2A-LANGGRAPH-BATCH-CONTRACT.json": "1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b",
}

def need(cond, msg):
    if not cond:
        raise SystemExit(f"[ERROR] {msg}")

def sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load(p: Path):
    return json.loads(p.read_text())

def git_show(repo: Path, ref: str, rel: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), "show", f"{ref}:{rel}"])

def verify_manifest(run: Path, expected_names: list[str]) -> None:
    manifest_path = run / "package-files-sha256.txt"
    need(manifest_path.is_file(), f"evidence manifest missing: {manifest_path}")
    rows = {}
    for line in manifest_path.read_text().splitlines():
        if not line.strip():
            continue
        digest, name = line.split("  ", 1)
        need(name not in rows, f"duplicate manifest entry: {name}")
        rows[name] = digest
    need(set(rows) == set(expected_names), f"manifest file set drift: {manifest_path}")
    for name in expected_names:
        q = run / name
        need(q.is_file(), f"manifest target missing: {q}")
        need(rows[name] == sha(q), f"manifest checksum mismatch: {q}")

def require_base_immutable(repo: Path, paths: list[str]) -> None:
    for rel in paths:
        need((repo / rel).is_file(), f"retained predecessor file missing: {rel}")
        need((repo / rel).read_bytes() == git_show(repo, BASE, rel), f"retained predecessor drift from Step 2A.09 merge: {rel}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--run-dir")
    args = ap.parse_args()
    repo = Path(args.repo).resolve()

    for rel, expected in OLD_FREEZES.items():
        p = repo / rel
        need(p.is_file(), f"missing frozen predecessor: {rel}")
        need(sha(p) == expected, f"frozen predecessor drift: {rel}")

    # Claim/matrix/source semantics are frozen at the Step 2A.09 merge boundary.
    for rel in ["CLAIMS_REGISTER.md", "COMPARISON_MATRIX.md", "SOURCES.md"]:
        need((repo / rel).read_bytes() == git_show(repo, BASE, rel), f"Step 2A.10 changed {rel}")

    # Re-verify each retained predecessor fact that the Gate 2A freeze will certify.
    require_base_immutable(repo, [
        f"{STEP02}/summary.json", f"{STEP02}/environment.json",
        f"{STEP03}/summary.json", f"{STEP03V}/summary.json", f"{STEP04}/summary.json",
        f"{STEP05}/summary.json", f"{STEP06}/summary.json", f"{STEP07}/summary.json",
        f"{RUN08}/package-files-sha256.txt", f"{STEP08_GATE}/salvage-wrapper-summary.json",
        f"{STEP09}/package-files-sha256.txt",
    ])
    step02 = load(repo / STEP02 / "summary.json")
    env02 = load(repo / STEP02 / "environment.json")
    need(step02.get("status") == "pass", "Step 2A.02 summary not pass")
    need(step02.get("model_call_performed") is False and step02.get("drupal_state_mutated") is False and step02.get("dependency_change") is False, "Step 2A.02 model/Drupal/dependency boundary drift")
    checks02 = step02.get("checks", {})
    for key in ["explicit_zero_transport_retries","image_message_shape","interrupt_resume","native_tool_wrapper","persisted_state_privacy","sqlite_checkpoint_reload","stategraph_model_free","strict_structured_output_api"]:
        need(checks02.get(key) is True, f"Step 2A.02 capability proof drift: {key}")
    expected_versions = {"langchain":"1.3.14","langgraph":"1.2.10","langgraph-checkpoint-sqlite":"3.1.1","python":"3.12.13"}
    need(env02.get("versions_match") is True and env02.get("expected") == expected_versions, "Step 2A.02 pinned-version expectation drift")
    observed02 = env02.get("observed", {})
    for key, value in expected_versions.items():
        need(observed02.get(key) == value, f"Step 2A.02 observed runtime version drift: {key}")

    step03 = load(repo / STEP03 / "summary.json")
    need(step03.get("status") == "pass" and step03.get("framework") == "langgraph", "Step 2A.03 accepted summary drift")
    need(step03.get("tool_count") == 4 and step03.get("tool_names") == ["find_images_needing_review","get_image_context","submit_recommendation","get_recommendation_status"], "Step 2A.03 tool surface drift")
    need(step03.get("model_call_performed") is False and step03.get("provider_call_performed") is False, "Step 2A.03 model/provider boundary drift")
    need(step03.get("pending_status_observed") is True and step03.get("same_identity_replay") is True and step03.get("source_article_mutation_performed") is False and step03.get("drupal_restored_to_seeded_clean") is True, "Step 2A.03 shared-boundary proof drift")

    step03v = load(repo / STEP03V / "summary.json")
    need(step03v.get("status") == "pass" and step03v.get("supplemental_verification_only") is True, "Step 2A.03 compliance verification drift")
    need(step03v.get("agent_allowed_all_four") is True and step03v.get("editor_denied_all_four") is True, "Step 2A.03 permission-boundary drift")
    need(step03v.get("all_correlation_ids_exact") is True and step03v.get("tool_result_schema_conformance") is True and step03v.get("structured_error_behavior_proven") is True, "Step 2A.03 adapter compliance drift")
    need(step03v.get("model_call_performed") is False and step03v.get("provider_call_performed") is False and step03v.get("drupal_mutation_performed") is False, "Step 2A.03 compliance side-effect drift")

    step04 = load(repo / STEP04 / "summary.json")
    need(step04.get("status") == "pass" and step04.get("checkpoint_backend") == "sqlite", "Step 2A.04 checkpoint proof drift")
    need(step04.get("process_boundary_reload_observed") is True and step04.get("same_thread_state_equal") is True and step04.get("negative_control_empty") is True and step04.get("thread_id_equals_run_id") is True, "Step 2A.04 reload/isolation proof drift")
    need(step04.get("model_call_performed") is False and step04.get("provider_call_performed") is False and step04.get("drupal_call_performed") is False and step04.get("drupal_mutation_performed") is False, "Step 2A.04 side-effect boundary drift")
    need(step04.get("raw_image_bytes_or_data_urls_persisted") is False and step04.get("article_body_or_hidden_reasoning_persisted") is False and step04.get("credentials_or_auth_material_persisted") is False, "Step 2A.04 checkpoint privacy drift")

    step05 = load(repo / STEP05 / "summary.json")
    need(step05.get("status") == "pass" and step05.get("model_call_count") == 1, "Step 2A.05 canonical model-call proof drift")
    need(step05.get("model_id") == "gpt-4.1-mini-2025-04-14" and step05.get("temperature") == 0.0 and step05.get("validator_version") == "gate05-validator-1.0.0", "Step 2A.05 model/validator constant drift")
    need(step05.get("target_sequence_sha256") == "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728", "Step 2A.05 target sequence hash drift")
    need(step05.get("automatic_model_retries") == 0 and step05.get("semantic_retry_loop_performed") is False, "Step 2A.05 retry-policy drift")
    need(step05.get("source_context_stable_across_model_and_submission") is True and step05.get("checkpoint_privacy_pass") is True and step05.get("source_article_mutation_performed") is False and step05.get("drupal_restored_to_seeded_clean") is True, "Step 2A.05 safety/restoration proof drift")

    step06 = load(repo / STEP06 / "summary.json")
    need(step06.get("status") == "pass" and step06.get("model_call_count") == 0 and step06.get("accepted_step05_model_output_reused") is True, "Step 2A.06 model-reuse boundary drift")
    need(step06.get("interrupt_persisted") is True and step06.get("human_review_performed") is True and step06.get("human_reviewer") == "editor_dana", "Step 2A.06 human-interrupt lineage drift")
    need(step06.get("human_action") == "edit-and-approve" and step06.get("post_review_status") == "approved" and step06.get("same_run_thread_resumed") is True, "Step 2A.06 review/resume disposition drift")
    need(step06.get("source_article_mutation_performed") is False and step06.get("drupal_restored_to_seeded_clean") is True and step06.get("gate2c_failure_injection_exercised") is False, "Step 2A.06 safety/Gate2C boundary drift")

    step07 = load(repo / STEP07 / "summary.json")
    need(step07.get("status") == "pass" and step07.get("proof_scope") == "step2a07-model-free-batch-runner-construction", "Step 2A.07 construction proof drift")
    need(step07.get("model_call_count") == 0 and step07.get("drupal_semantic_call_count") == 0 and step07.get("live_step2a08_batch_executed") is False, "Step 2A.07 live/model/Drupal boundary drift")
    need(step07.get("completed_before_continuation") == list(range(1,7)) and step07.get("completed_after_resume") == list(range(7,13)) and step07.get("duplicate_count") == 0, "Step 2A.07 continuation construction drift")
    need(step07.get("target_count") == 12 and step07.get("target_sequence_sha256") == "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728", "Step 2A.07 target contract drift")
    need(step07.get("genuine_langgraph_interrupt_persisted") is True and step07.get("same_run_thread_resumed") is True and step07.get("gate2c_failure_injection_exercised") is False, "Step 2A.07 interrupt/Gate2C boundary drift")

    verify_manifest(repo / STEP09, ["summary.json","claim-evidence-map.json","source-pairing.json","repair-v1.0.4.json"])
    step09 = load(repo / STEP09 / "summary.json")
    need(step09.get("status") == "pass", "Step 2A.09 summary not pass")
    need(step09.get("accepted_step08_run") == RUN08, "Step 2A.09 accepted run drift")
    need(step09.get("model_provider_calls") == 0, "Step 2A.09 model budget drift")
    need(step09.get("drupal_semantic_calls") == 0 and step09.get("drupal_mutations") == 0, "Step 2A.09 Drupal budget drift")
    need(step09.get("gate2c_failure_injection") is False, "Step 2A.09 Gate 2C drift")

    verify_manifest(repo / RUN08, ['call-counters.json','checkpoint-after-continuation.json','checkpoint-before-continuation.json','checkpoint-privacy-after-continuation-salvage.json','checkpoint-privacy-after-continuation.json','checkpoint-privacy-before-continuation.json','continuation-event.json','events.jsonl','model-outputs.json','recommendations.json','recovery.json','run-metadata.json','run.json','statuses.json','submissions.json','summary.json','targets.json','tool-traces.json','validation.json'])
    run08 = load(repo / RUN08 / "run.json")
    batch08 = load(repo / RUN08 / "summary.json")
    calls = load(repo / RUN08 / "call-counters.json")
    need(batch08.get("status") == "pass" and batch08.get("completed_count") == 12 and batch08.get("duplicate_count") == 0 and batch08.get("failed_count") == 0, "Step 2A.08 batch summary drift")
    need(batch08.get("source_article_unchanged") is True and batch08.get("automatic_publication_performed") is False, "Step 2A.08 source/publication safety drift")
    need(batch08.get("provider") == "OpenAI" and batch08.get("model") == "gpt-4.1-mini-2025-04-14" and batch08.get("temperature") == 0.0 and batch08.get("validator_version") == "gate05-validator-1.0.0", "Step 2A.08 model/validator constant drift")
    need(batch08.get("review_destination") == "alt_text_suggestion" and batch08.get("resume_sequence") == 7 and batch08.get("failure_seam_observed") is False, "Step 2A.08 review/continuation boundary drift")
    need(run08.get("status") == "completed", "Step 2A.08 run not completed")
    need(run08.get("framework_origin") == "langgraph", "Step 2A.08 framework drift")
    need(run08.get("run_id") == run08.get("thread_id"), "Step 2A.08 run/thread drift")
    need(run08.get("next_target_index") == 12, "Step 2A.08 next index drift")
    need([x.get("sequence") for x in run08.get("completed_target_identities", [])] == list(range(1, 13)), "Step 2A.08 target sequence drift")
    recs = [x.get("uuid") for x in run08.get("recommendation_ids", [])]
    need(len(recs) == 12 and len(set(recs)) == 12, "Step 2A.08 recommendation uniqueness drift")
    need(run08.get("continuation_boundary_reached") is True, "Step 2A.08 continuation boundary missing")
    need(run08.get("gate2c_failure_injection_fired") is False, "Step 2A.08 incorrectly exercised Gate 2C")
    vals = run08.get("validation_results", [])
    need(len(vals) == 12 and [x.get("sequence") for x in vals] == list(range(1,13)), "Step 2A.08 validation sequence/count drift")
    need(all(x.get("structured_output_schema_valid") is True and x.get("deterministic_validation_passed") is True for x in vals), "Step 2A.08 validation drift")
    need(calls.get("model_invocations_attempted") == 12 and calls.get("model_invocations_succeeded") == 12, "Step 2A.08 model counts drift")
    need(calls.get("automatic_model_retries_configured") == 0 and calls.get("semantic_retry_loop_performed") is False, "Step 2A.08 retry policy drift")

    orig = load(repo / RUN08 / "checkpoint-privacy-after-continuation.json")
    salvage = load(repo / RUN08 / "checkpoint-privacy-after-continuation-salvage.json")
    need(orig.get("status") == "fail" and orig.get("generic_prohibited_pattern_hits") == ["hidden_reasoning"], "original Step 2A.08 privacy lineage drift")
    need(salvage.get("status") == "pass" and salvage.get("diagnosis") == "privacy-report-self-match", "Step 2A.08 salvage drift")
    need(salvage.get("actual_prohibited_content_found") is False, "Step 2A.08 salvage reports prohibited content")
    sw = load(repo / STEP08_GATE / "salvage-wrapper-summary.json")
    need(sw.get("status") == "pass" and sw.get("restore_attempted") is True and sw.get("restore_verified") is True and sw.get("snapshot_restored") is True and sw.get("snapshot_cleaned") is True, "Step 2A.08 restore lifecycle drift")
    need(sw.get("before_state_sha256") == sw.get("after_restore_state_sha256"), "Step 2A.08 Drupal restore hash drift")
    need(sw.get("additional_model_calls_for_salvage") == 0, "Step 2A.08 salvage added model calls")

    freeze_p = repo / FREEZE_REL
    need(freeze_p.is_file(), "Gate 2A freeze missing")
    freeze = load(freeze_p)
    need(freeze.get("status") == "certified", "Gate 2A freeze not certified")
    need(freeze.get("framework") == "langgraph" and freeze.get("source_framework") == "langgraph", "Gate 2A freeze framework mismatch")
    need(freeze.get("provider") == "OpenAI" and freeze.get("model") == "gpt-4.1-mini-2025-04-14" and freeze.get("temperature") == 0.0, "Gate 2A freeze model/settings mismatch")
    need(freeze.get("validator_version") == "gate05-validator-1.0.0" and freeze.get("review_destination") == "alt_text_suggestion", "Gate 2A freeze validator/review destination mismatch")
    need(freeze.get("source_article_mutation") == "prohibited" and freeze.get("automatic_publication") == "prohibited", "Gate 2A freeze publication/source-mutation policy mismatch")
    need(freeze.get("checkpoint_backend") == "sqlite", "Gate 2A freeze checkpoint backend mismatch")
    need(freeze.get("accepted_batch_run") == RUN08, "Gate 2A freeze accepted batch mismatch")
    need(freeze.get("step09_synthesis_run") == STEP09, "Gate 2A freeze Step09 mismatch")
    expected_predecessors = {
        "step02_runtime_probe": STEP02,
        "step03_tool_adapters": STEP03,
        "step03_compliance": STEP03V,
        "step04_checkpoint_proof": STEP04,
        "step05_canonical_slice": STEP05,
        "step06_human_interrupt": STEP06,
        "step07_batch_runner": STEP07,
        "step08_batch": RUN08,
        "step09_claims_synthesis": STEP09,
    }
    need(freeze.get("predecessor_evidence") == expected_predecessors, "Gate 2A freeze predecessor-evidence map drift")
    need(freeze.get("runtime_versions") == {"python":"3.12.13","langchain":"1.3.14","langgraph":"1.2.10","sqlite_checkpointer":"3.1.1"}, "Gate 2A freeze runtime-version map drift")
    need(freeze.get("target_count") == 12 and freeze.get("target_sequence_sha256") == "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728", "Gate 2A freeze target contract mismatch")
    need(freeze.get("recommendation_count") == 12 and freeze.get("duplicate_recommendation_count") == 0, "Gate 2A freeze recommendation counts mismatch")
    need(freeze.get("model_call_total_gate2a") == 13 and freeze.get("step08_model_calls") == 12, "Gate 2A successful model-call total mismatch")
    need(freeze.get("automatic_model_retries") == 0 and freeze.get("semantic_retry_loop") is False, "Gate 2A freeze retry policy mismatch")
    need(freeze.get("controlled_continuation") == {"after_sequence":6,"before_sequence":7,"same_run_thread":True,"reprocessed_prior_targets":0}, "Gate 2A freeze continuation record mismatch")
    need(freeze.get("human_review_lineage") == {"step06_run":STEP06,"reviewer":"editor_dana","action":"edit-and-approve","same_run_thread_resumed":True}, "Gate 2A freeze human-review lineage mismatch")
    need(freeze.get("privacy_lineage") == {"original_step08_failure_preserved":True,"salvage_diagnosis":"privacy-report-self-match","actual_prohibited_content_found":False}, "Gate 2A freeze privacy lineage mismatch")
    need(freeze.get("step10_model_provider_calls") == 0, "Step 2A.10 model budget mismatch")
    need(freeze.get("step10_drupal_semantic_calls") == 0 and freeze.get("step10_drupal_mutations") == 0, "Step 2A.10 Drupal budget mismatch")
    need(freeze.get("shared_process_failure_recovery_claimed") is False, "Gate 2A freeze overclaims Gate 2C")
    need(freeze.get("drupal_snapshot_restore_verified") is True, "Gate 2A freeze missing Drupal restore proof")
    need(freeze.get("drupal_state_before_run_sha256") == sw.get("before_state_sha256") == freeze.get("drupal_state_after_restore_sha256"), "Gate 2A freeze Drupal state hash mismatch")
    need(freeze.get("verified_claims") == ["CLM-LG-002","CLM-LG-004","CLM-LG-005","CLM-LG-006","CLM-LG-007"], "verified claim set drift")
    need(freeze.get("observed_claims") == ["CLM-LG-008"], "observed claim set drift")
    need(freeze.get("hypothesis_claims") == ["CLM-LG-001","CLM-LG-003"], "hypothesis claim set drift")
    need(freeze.get("cross_framework_claims_promoted") == [], "Gate 2A freeze promoted cross-framework claims")
    need(freeze.get("step10_human_review_actions") == 0 and freeze.get("step10_gate2c_failure_injection") is False, "Step 2A.10 human-review/Gate2C budget mismatch")

    if args.run_dir:
        run_rel = args.run_dir
    else:
        ptr = repo / "evidence/gates/gate-2a/certification/GATE2A-STEP10-LATEST.txt"
        need(ptr.is_file(), "Step 2A.10 latest pointer missing")
        run_rel = ptr.read_text().strip()
    run = repo / run_rel
    need(run.is_dir(), f"certification evidence missing: {run_rel}")
    for name in ["summary.json", "certification.json", "package-files-sha256.txt"]:
        need((run / name).is_file(), f"certification evidence file missing: {name}")
    summary = load(run / "summary.json")
    cert = load(run / "certification.json")
    freeze_digest = sha(freeze_p)
    need(summary.get("status") == "pass" and summary.get("package") == PACKAGE, "Step 2A.10 summary mismatch")
    need(summary.get("gate2a_freeze_sha256") == freeze_digest, "Step 2A.10 freeze digest mismatch")
    need(summary.get("model_provider_calls") == 0 and summary.get("drupal_semantic_calls") == 0 and summary.get("drupal_mutations") == 0, "Step 2A.10 summary budget mismatch")
    need(summary.get("gate2c_failure_injection") is False, "Step 2A.10 summary overclaims Gate 2C")
    need(summary.get("predecessor_evidence_verified") is True, "Step 2A.10 summary missing predecessor verification")
    need(summary.get("successful_gate2a_model_calls") == 13 and summary.get("second_certification_batch") is False and summary.get("next_package") == NEXT, "Step 2A.10 summary certification-policy drift")
    need(cert.get("certification_candidate") == RUN08 and cert.get("result") == "certified", "certification record mismatch")
    need(cert.get("predecessor_evidence_verified") is True and cert.get("model_free_promotion") is True and cert.get("second_batch_run") is False and cert.get("gate2c_failure_recovery_exercised") is False, "certification policy record mismatch")
    need(cert.get("gate2a_freeze_sha256") == freeze_digest and cert.get("step09_synthesis") == STEP09, "certification linkage mismatch")

    verify_manifest(run, ["summary.json", "certification.json"])

    handoff = (repo / "docs/handoffs/GATE-2A-TO-CREWAI-HANDOFF.md").read_text()
    need(freeze_digest in handoff, "CrewAI handoff missing freeze digest")
    need(NEXT in handoff, "CrewAI handoff missing next package")
    need("Do not infer CrewAI behavior" in handoff, "CrewAI handoff inference guardrail missing")

    gate_doc = (repo / "docs/gates/GATE-2A-STEP10-LANGGRAPH-CERTIFICATION-FREEZE-AND-CREWAI-HANDOFF.md").read_text()
    need(freeze_digest in gate_doc and "__FREEZE_SHA256__" not in gate_doc, "Step 2A.10 gate doc freeze digest missing")

    for rel in ["AGENTS.md", "PLAN.md", "README.md", "docs/CURRENT-STATUS.md"]:
        text = (repo / rel).read_text()
        need("Step 2A.10" in text, f"{rel} missing Step 2A.10")
        need(PACKAGE in text, f"{rel} missing completed package")
        need(freeze_digest in text, f"{rel} missing Gate 2A freeze digest")
        need(NEXT in text, f"{rel} missing next package")
    current = (repo / "docs/CURRENT-STATUS.md").read_text()
    need("Step 2A.01 through Step 2A.10 are complete" in current, "canonical Gate 2A lifecycle sentence missing")
    need("Step 2A.01through" not in current, "stale no-space lifecycle form present")

    print("[PASS] Gate 2A Step 2A.10 certification/freeze audit passed.")
    print(f"[PASS] Gate 2A freeze SHA-256: {freeze_digest}")
    print(f"[PASS] Evidence: {run_rel}")

if __name__ == "__main__":
    main()
