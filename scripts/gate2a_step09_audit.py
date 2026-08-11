#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

BASE = "28e8e93fc7805449debbb1df3336bf06e3959e7c"
PACKAGE = "gate-2a-step09-langgraph-evidence-claims-and-matrix-v1.0.4"
RUN08 = "evidence/results/langgraph/langgraph-20260810T231915Z-0027cd3e"
STEP03 = "evidence/gates/gate-2a/tool-adapters/gate2a-step03-20260809T233127Z-2375581"
STEP03V = "evidence/gates/gate-2a/tool-adapters/gate2a-step03-verification-20260810T020210Z-2410520"
STEP04 = "evidence/gates/gate-2a/checkpoint-proof/gate2a-step04-20260810T034027Z-00250b07"
STEP05 = "evidence/gates/gate-2a/canonical-slice/gate2a-step05-20260810T140133Z-0025b888"
STEP06 = "evidence/gates/gate-2a/human-interrupt/gate2a-step06-20260810T162448Z-002692eb"
FREEZES = {
    "shared/contracts/GATE05-SUBSTRATE-FREEZE.json": "99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a",
    "shared/contracts/GATE1-DRUPAL-AI-FREEZE.json": "2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd",
    "shared/contracts/GATE2A-LANGGRAPH-BATCH-CONTRACT.json": "1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b",
}


def need(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[ERROR] {msg}")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contains(text: str, needle: str, label: str) -> None:
    need(needle in text, f"{label} missing: {needle}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--document-state", choices=["complete"], default="complete")
    ap.add_argument("--run-dir")
    ap.add_argument("--phase", choices=["candidate", "permanent"], default="permanent")
    args = ap.parse_args()
    repo = Path(args.repo).resolve()

    for rel, expected in FREEZES.items():
        p = repo / rel
        need(p.is_file(), f"frozen file missing: {rel}")
        need(sha(p) == expected, f"frozen hash drift: {rel}")

    latest = repo / "evidence/gates/gate-2a/fresh-batch/GATE2A-STEP08-LATEST.txt"
    failed = repo / "evidence/gates/gate-2a/fresh-batch/GATE2A-STEP08-FAILED-RUNS.txt"
    need(latest.read_text().strip() == RUN08, "Step 2A.08 accepted pointer drift")
    need(RUN08 in failed.read_text().splitlines(), "Step 2A.08 failed-run lineage missing")
    original_privacy_path = repo / RUN08 / "checkpoint-privacy-after-continuation.json"
    salvage_privacy_path = repo / RUN08 / "checkpoint-privacy-after-continuation-salvage.json"
    need(original_privacy_path.is_file(), "original Step 2A.08 privacy failure missing")
    need(salvage_privacy_path.is_file(), "Step 2A.08 salvage disposition missing")
    original_privacy = json.loads(original_privacy_path.read_text())
    salvage_privacy = json.loads(salvage_privacy_path.read_text())
    need(original_privacy.get("status") == "fail", "original Step 2A.08 privacy failure no longer failed")
    need(original_privacy.get("generic_prohibited_pattern_hits") == ["hidden_reasoning"], "original Step 2A.08 privacy failure changed")
    need(original_privacy.get("exact_ephemeral_value_hits") == [], "original Step 2A.08 exact privacy hits changed")
    need(salvage_privacy.get("status") == "pass", "Step 2A.08 salvage disposition not pass")
    need(salvage_privacy.get("diagnosis") == "privacy-report-self-match", "Step 2A.08 salvage diagnosis changed")
    need(salvage_privacy.get("original_failed_privacy_report_preserved") is True, "Step 2A.08 salvage no longer preserves original failure")
    need(salvage_privacy.get("actual_prohibited_content_found") is False, "Step 2A.08 salvage reports prohibited content")

    counters = json.loads((repo / RUN08 / "call-counters.json").read_text())
    need(counters.get("model_invocations_attempted") == 12, "Step 2A.08 attempted model-call count drift")
    need(counters.get("model_invocations_succeeded") == 12, "Step 2A.08 successful model-call count drift")
    need(counters.get("automatic_model_retries_configured") == 0, "Step 2A.08 retry policy drift")
    need(counters.get("semantic_retry_loop_performed") is False, "Step 2A.08 semantic retry drift")
    run08 = json.loads((repo / RUN08 / "run.json").read_text())
    rec_ids = [row["uuid"] for row in run08.get("recommendation_ids", [])]
    need(run08.get("status") == "completed", "Step 2A.08 run no longer completed")
    need(run08.get("run_id") == run08.get("thread_id"), "Step 2A.08 run/thread identity drift")
    need(run08.get("next_target_index") == 12, "Step 2A.08 next-target index drift")
    need([row["sequence"] for row in run08.get("completed_target_identities", [])] == list(range(1, 13)), "Step 2A.08 completed target sequence drift")
    need(len(rec_ids) == 12 and len(set(rec_ids)) == 12, "Step 2A.08 recommendation identity uniqueness drift")
    need(run08.get("continuation_boundary_reached") is True, "Step 2A.08 continuation boundary missing")
    need(run08.get("gate2c_failure_injection_fired") is False, "Step 2A.08 incorrectly exercised Gate 2C")

    step03 = json.loads((repo / STEP03 / "summary.json").read_text())
    need(step03.get("status") == "pass", "Step 2A.03 accepted summary not pass")
    need(step03.get("tool_count") == 4, "Step 2A.03 tool count drift")
    need(step03.get("tool_names") == ["find_images_needing_review", "get_image_context", "submit_recommendation", "get_recommendation_status"], "Step 2A.03 tool names drift")
    need(step03.get("model_call_performed") is False and step03.get("provider_call_performed") is False, "Step 2A.03 unexpectedly records model/provider use")
    step03v = json.loads((repo / STEP03V / "summary.json").read_text())
    need(step03v.get("status") == "pass", "Step 2A.03 verification summary not pass")
    need(step03v.get("agent_allowed_all_four") is True, "Step 2A.03 verification agent permission drift")
    need(step03v.get("editor_denied_all_four") is True, "Step 2A.03 verification reviewer permission drift")
    need(step03v.get("all_correlation_ids_exact") is True, "Step 2A.03 correlation-ID proof drift")
    need(step03v.get("tool_result_schema_conformance") is True, "Step 2A.03 tool-result schema proof drift")

    step04 = json.loads((repo / STEP04 / "summary.json").read_text())
    need(step04.get("status") == "pass", "Step 2A.04 accepted summary not pass")
    need(step04.get("checkpoint_backend") == "sqlite", "Step 2A.04 checkpoint backend drift")
    need(step04.get("process_boundary_reload_observed") is True, "Step 2A.04 process-boundary reload proof missing")
    need(step04.get("same_thread_state_equal") is True, "Step 2A.04 same-thread state equality drift")
    need(step04.get("negative_control_empty") is True, "Step 2A.04 isolation negative control drift")

    step05 = json.loads((repo / STEP05 / "summary.json").read_text())
    need(step05.get("status") == "pass", "Step 2A.05 accepted summary not pass")
    need(step05.get("model_call_count") == 1, "Step 2A.05 model-call count drift")
    need(step05.get("automatic_model_retries") == 0, "Step 2A.05 retry policy drift")
    need(step05.get("semantic_retry_loop_performed") is False, "Step 2A.05 semantic retry drift")
    need(step05.get("source_context_stable_across_model_and_submission") is True, "Step 2A.05 context-stability proof drift")
    need(step05.get("checkpoint_privacy_pass") is True, "Step 2A.05 checkpoint privacy proof drift")
    need(step05.get("validator_version") == "gate05-validator-1.0.0", "Step 2A.05 validator version drift")

    step06 = json.loads((repo / STEP06 / "summary.json").read_text())
    need(step06.get("status") == "pass", "Step 2A.06 accepted summary not pass")
    need(step06.get("model_call_count") == 0, "Step 2A.06 model-call count drift")
    need(step06.get("interrupt_persisted") is True, "Step 2A.06 interrupt persistence proof missing")
    need(step06.get("human_review_performed") is True and step06.get("human_reviewer") == "editor_dana", "Step 2A.06 human-review lineage drift")
    need(step06.get("human_action") == "edit-and-approve" and step06.get("post_review_status") == "approved", "Step 2A.06 review disposition drift")
    need(step06.get("same_run_thread_resumed") is True, "Step 2A.06 same-run/thread resume proof missing")
    need(step06.get("gate2c_failure_injection_exercised") is False, "Step 2A.06 incorrectly exercised Gate 2C")

    sources = (repo / "SOURCES.md").read_text()
    for src, url in {
        "SRC-LG-001": "https://docs.langchain.com/oss/python/langgraph/persistence",
        "SRC-LG-002": "https://docs.langchain.com/oss/python/langgraph/interrupts",
        "SRC-LG-003": "https://docs.langchain.com/oss/python/langchain/tools",
    }.items():
        contains(sources, f"| {src} |", "SOURCES.md")
        contains(sources, url, "SOURCES.md")
    need("TODO — verify current official URL" not in "\n".join(line for line in sources.splitlines() if "SRC-LG-00" in line), "LangGraph source placeholder remains")

    claims = (repo / "CLAIMS_REGISTER.md").read_text()
    contains(claims, "| CLM-LG-001 |", "CLAIMS_REGISTER.md")
    need("| CLM-LG-001 | LangChain / LangGraph provides the broadest code-first tool and integration surface of the three specimens. | LangChain / LangGraph | TODO | Not run | hypothesis |" in claims, "CLM-LG-001 must remain hypothesis")
    need("| CLM-LG-003 | Without a configured persistence path, a code-first LangGraph specimen may repeat completed work after termination. | LangGraph | TODO | Failure test not run | hypothesis |" in claims, "CLM-LG-003 must remain hypothesis")
    for cid in ["CLM-LG-002", "CLM-LG-004", "CLM-LG-005", "CLM-LG-006", "CLM-LG-007"]:
        line = next((x for x in claims.splitlines() if f"| {cid} |" in x), "")
        need("| verified |" in line, f"{cid} not verified")
    line8 = next((x for x in claims.splitlines() if "| CLM-LG-008 |" in x), "")
    need("| observed |" in line8, "CLM-LG-008 must remain observed")
    for cid in ["CLM-CR-001", "CLM-CR-002", "CLM-CR-003", "CLM-CMP-001", "CLM-CMP-002", "CLM-CMP-003"]:
        line = next((x for x in claims.splitlines() if f"| {cid} |" in x), "")
        need("| hypothesis |" in line, f"{cid} was prematurely promoted")

    matrix = (repo / "COMPARISON_MATRIX.md").read_text()
    contains(matrix, "Drupal AI and LangGraph evidence populated; CrewAI remains unobserved", "COMPARISON_MATRIX.md")
    for cid in ["CLM-LG-008", "CLM-LG-004", "CLM-LG-002", "CLM-LG-007", "CLM-LG-005", "CLM-LG-006"]:
        contains(matrix, cid, "COMPARISON_MATRIX.md")
    langgraph_rows = [x for x in matrix.splitlines() if "| LangChain / LangGraph |" in x]
    need(len(langgraph_rows) == 6, f"expected 6 LangGraph matrix rows, got {len(langgraph_rows)}")
    need(all("TODO" not in x and "not observed" not in x for x in langgraph_rows), "LangGraph matrix still contains TODO/unobserved row")
    crew_rows = [x for x in matrix.splitlines() if "| CrewAI |" in x]
    need(len(crew_rows) == 6, f"expected 6 CrewAI matrix rows, got {len(crew_rows)}")
    need(all("TODO" in x and "not observed" in x for x in crew_rows), "CrewAI row changed prematurely")

    for rel in ["AGENTS.md", "PLAN.md", "README.md", "docs/CURRENT-STATUS.md"]:
        text = (repo / rel).read_text()
        contains(text, "Step 2A.09", rel)
        contains(text, PACKAGE, rel)
        contains(text, "gate-2a-step10-langgraph-certification-freeze-and-crewai-handoff-v1.0.0", rel)
    current_status = (repo / "docs/CURRENT-STATUS.md").read_text()
    contains(current_status, "Step 2A.01 through Step 2A.09 are complete. Step 2A.10 is next but remains locked until Step 2A.09 is committed and merged, local `main` is resynchronized, and the post-merge audit passes.", "docs/CURRENT-STATUS.md")
    need("Step 2A.01through Step 2A.09" not in current_status, "stale missing-space Step 2A.09 lifecycle sentence present")

    run_dir = args.run_dir
    if run_dir is None:
        ptr = repo / "evidence/gates/gate-2a/evidence-claims/GATE2A-STEP09-LATEST.txt"
        need(ptr.is_file(), "Step 2A.09 latest pointer missing")
        run_dir = ptr.read_text().strip()
    run = repo / run_dir
    need(run.is_dir(), f"Step 2A.09 evidence missing: {run_dir}")
    for name in ["summary.json", "claim-evidence-map.json", "source-pairing.json", "repair-v1.0.4.json", "package-files-sha256.txt"]:
        need((run / name).is_file(), f"Step 2A.09 evidence file missing: {name}")
    summary = json.loads((run / "summary.json").read_text())
    need(summary.get("package") == PACKAGE, "Step 2A.09 summary package mismatch")
    need(summary.get("status") == "pass", "Step 2A.09 summary not pass")
    need(summary.get("model_provider_calls") == 0, "Step 2A.09 model call count not zero")
    need(summary.get("drupal_semantic_calls") == 0, "Step 2A.09 Drupal semantic call count not zero")
    need(summary.get("drupal_mutations") == 0, "Step 2A.09 Drupal mutation count not zero")
    need(summary.get("gate2c_failure_injection") is False, "Step 2A.09 incorrectly claims Gate 2C")
    need(summary.get("accepted_step08_run") == RUN08, "Step 2A.09 summary Step08 pointer mismatch")
    need(summary.get("cross_framework_claims_promoted") == [], "cross-framework claim promotion detected")
    need(summary.get("verified_langgraph_claims") == ["CLM-LG-002", "CLM-LG-004", "CLM-LG-005", "CLM-LG-006", "CLM-LG-007"], "verified LangGraph claim set drift")
    need(summary.get("observed_langgraph_claims") == ["CLM-LG-008"], "observed LangGraph claim set drift")
    need(summary.get("langgraph_claims_left_hypothesis") == ["CLM-LG-001", "CLM-LG-003"], "LangGraph hypothesis set drift")

    claim_map = json.loads((run / "claim-evidence-map.json").read_text())
    claim_rows = {row["claim_id"]: row for row in claim_map.get("claims", [])}
    expected_claim_status = {
        "CLM-LG-002": "verified",
        "CLM-LG-004": "verified",
        "CLM-LG-005": "verified",
        "CLM-LG-006": "verified",
        "CLM-LG-007": "verified",
        "CLM-LG-008": "observed",
    }
    need(set(claim_rows) == set(expected_claim_status), "claim-evidence map claim set drift")
    for cid, status in expected_claim_status.items():
        need(claim_rows[cid].get("status") == status, f"claim-evidence map status drift: {cid}")
        need(bool(claim_rows[cid].get("local_evidence")), f"claim-evidence map missing local evidence: {cid}")

    source_pairing = json.loads((run / "source-pairing.json").read_text())
    source_rows = {row["source_id"]: row for row in source_pairing.get("sources", [])}
    expected_urls = {
        "SRC-LG-001": "https://docs.langchain.com/oss/python/langgraph/persistence",
        "SRC-LG-002": "https://docs.langchain.com/oss/python/langgraph/interrupts",
        "SRC-LG-003": "https://docs.langchain.com/oss/python/langchain/tools",
        "SRC-S16-004": "https://docs.langchain.com/oss/python/integrations/chat/openai",
    }
    need(set(source_rows) == set(expected_urls), "source-pairing source set drift")
    for sid, url in expected_urls.items():
        need(source_rows[sid].get("url") == url, f"source-pairing URL drift: {sid}")
        need(source_rows[sid].get("official") is True, f"source-pairing official flag drift: {sid}")

    repair = json.loads((run / "repair-v1.0.4.json").read_text())
    need(repair.get("status") == "pass", "v1.0.4 repair record not pass")
    need(repair.get("package") == PACKAGE, "v1.0.4 repair package mismatch")
    need(repair.get("supersedes") == "gate-2a-step09-langgraph-evidence-claims-and-matrix-v1.0.2", "v1.0.4 supersedes marker mismatch")
    need(repair.get("model_provider_calls") == 0 and repair.get("drupal_semantic_calls") == 0 and repair.get("drupal_mutations") == 0, "v1.0.4 repair violated zero-call boundary")
    need(repair.get("claim_semantics_changed") is False and repair.get("source_pairings_changed") is False and repair.get("matrix_semantics_changed") is False, "v1.0.4 repair changed synthesis semantics")
    need(repair.get("lifecycle_variant_before") in ["canonical-spaced", "noncanonical-missing-space"], "v1.0.4 lifecycle-before marker invalid")
    need(repair.get("lifecycle_after") == "Step 2A.01 through Step 2A.09", "v1.0.4 lifecycle-after marker drift")

    manifest = {}
    for line in (run / "package-files-sha256.txt").read_text().splitlines():
        digest, name = line.split("  ", 1)
        manifest[name] = digest
    for name in ["summary.json", "claim-evidence-map.json", "source-pairing.json", "repair-v1.0.4.json"]:
        need(manifest.get(name) == sha(run / name), f"manifest mismatch: {name}")

    print("[PASS] Gate 2A Step 2A.09 audit passed.")
    print(f"[PASS] Evidence: {run_dir}")


if __name__ == "__main__":
    main()
