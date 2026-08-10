#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

TARGET_HASH = "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728"
SOURCE_HASH = "f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17"
MODEL_ID = "gpt-4.1-mini-2025-04-14"
VALIDATOR_VERSION = "gate05-validator-1.0.0"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    evidence = Path(args.evidence).resolve()

    core = load(evidence / "core-summary.json")
    counters = load(evidence / "call-counters.json")
    model_output = load(evidence / "model-output.json")
    model_schema = load(evidence / "model-output-schema-validation.json")
    recommendation = load(evidence / "recommendation.json")
    recommendation_schema = load(evidence / "recommendation-schema-validation.json")
    validation = load(evidence / "validation.json")
    submission = load(evidence / "submission.json")
    status = load(evidence / "status.json")
    state = load(evidence / "state-after-slice.json")
    state_schema = load(evidence / "state-schema-validation.json")
    checkpoint_privacy = load(evidence / "checkpoint-privacy.json")
    before = load(evidence / "before-state.json")
    during = load(evidence / "during-state.json")
    after = load(evidence / "after-state.json")
    context_before = load(evidence / "context-before-model-summary.json")
    context_presubmit = load(evidence / "context-before-submit-summary.json")
    context_after = load(evidence / "context-after-submit-summary.json")

    require(core.get("status") == "pass", "Core vertical-slice summary is not pass")
    require(core.get("run_id") == args.run_id, "Core run_id differs")
    require(core.get("framework") == "langgraph", "Framework differs")
    require(core.get("canonical_target_sequence") == 1, "Canonical target sequence is not 1")
    require(core.get("target_sequence_sha256") == TARGET_HASH, "Target hash differs")
    require(core.get("model_id") == MODEL_ID, "Model differs")
    require(core.get("validator_version") == VALIDATOR_VERSION, "Validator differs")
    require(core.get("model_invocations_attempted") == 1, "Model invocation attempt count is not 1")
    require(core.get("model_invocations_succeeded") == 1, "Successful model invocation count is not 1")
    require(core.get("automatic_model_retries_configured") == 0, "Automatic model retries are not disabled")
    require(core.get("semantic_retry_loop_performed") is False, "Semantic retry loop occurred")
    require(core.get("drupal_semantic_call_count") == 6, "Drupal semantic call count is not 6")
    require(core.get("drupal_semantic_call_counts") == {
        "find_images_needing_review": 1,
        "get_image_context": 3,
        "submit_recommendation": 1,
        "get_recommendation_status": 1,
    }, "Drupal semantic call distribution differs")
    require(core.get("recommendation_write_count") == 1, "Recommendation write count is not 1")
    require(core.get("pending_status_observed") is True, "Pending status was not observed")
    require(core.get("source_context_stable_before_model_to_before_submit") is True, "Pre-submit freshness check failed")
    require(core.get("source_context_stable_before_model_to_after_submit") is True, "Post-submit source check failed")
    require(core.get("next_target_index") == 1, "Next target index is not 1")
    require(core.get("completed_sequences") == [1], "Completed sequences are not [1]")
    require(core.get("checkpoint_backend") == "sqlite", "Checkpoint backend is not sqlite")
    require(core.get("thread_id_equals_run_id") is True, "Thread identity differs from run ID")
    require(core.get("checkpoint_privacy_pass") is True, "Checkpoint privacy did not pass")
    require(core.get("human_review_performed") is False, "Human review should not occur in Step 2A.05")
    require(core.get("source_article_mutation_performed") is False, "Core claims source mutation")
    require(core.get("automatic_publication_performed") is False, "Core claims automatic publication")
    require(core.get("gate2c_failure_injection_fired") is False, "Gate 2C failure injection fired")
    require(core.get("continuation_boundary_armed") is False, "Continuation boundary armed unexpectedly")
    require(core.get("continuation_boundary_reached") is False, "Continuation boundary reached unexpectedly")

    require(counters.get("model_invocations_attempted") == 1, "Call counters model attempts differ")
    require(counters.get("model_invocations_succeeded") == 1, "Call counters model success differs")
    require(counters.get("automatic_model_retries_configured") == 0, "Call counters automatic retry configuration differs")
    require(counters.get("semantic_retry_loop_performed") is False, "Call counters show semantic retry loop")

    require(set(model_output) == {"proposed_alt_text"}, "Raw model output key set differs")
    require(isinstance(model_output["proposed_alt_text"], str) and model_output["proposed_alt_text"].strip(), "Model alt text is empty")
    require(len(model_output["proposed_alt_text"].strip()) <= 250, "Model alt text exceeds 250 characters")
    require(model_schema.get("status") == "pass", "Raw model-output schema validation failed")
    require(recommendation_schema.get("status") == "pass", "Recommendation schema validation failed")
    require(state_schema.get("status") == "pass", "LangGraph state schema validation failed")

    require(validation.get("sequence") == 1, "Validation sequence differs")
    require(validation.get("structured_output_schema_valid") is True, "Structured output schema not valid")
    require(validation.get("deterministic_validation_passed") is True, "Deterministic validation did not pass")
    require(validation.get("errors") == [], "Validation errors are not empty")
    require(validation.get("target") == recommendation.get("target"), "Validation target differs from recommendation target")

    require(recommendation.get("source_framework") == "langgraph", "Recommendation framework differs")
    require(recommendation.get("run_id") == args.run_id, "Recommendation run ID differs")
    require(recommendation.get("validator_version") == VALIDATOR_VERSION, "Recommendation validator differs")
    require(recommendation.get("proposed_alt_text") == model_output.get("proposed_alt_text").strip(), "Recommendation alt differs from raw model output")

    require(submission.get("status") == "pending", "Submission status is not pending")
    require(submission.get("run_id") == args.run_id, "Submission run ID differs")
    require(submission.get("source_framework") == "langgraph", "Submission framework differs")
    require(submission.get("target") == recommendation.get("target"), "Submission target differs")
    require(status.get("status") == "pending", "Observed recommendation status is not pending")
    require(status.get("uuid") == submission.get("uuid"), "Status UUID differs from submission UUID")
    require(status.get("reviewed_at") is None and status.get("reviewer_username") is None, "Pending status unexpectedly includes reviewer lineage")

    target = recommendation["target"]
    require(context_before.get("target") == target, "Initial context target differs")
    require(context_presubmit.get("target") == target, "Pre-submit context target differs")
    require(context_after.get("target") == target, "Post-submit context target differs")
    require(
        context_before.get("evidence_hash") == context_presubmit.get("evidence_hash") == context_after.get("evidence_hash"),
        "Context evidence hash changed across freshness checks",
    )
    require(context_before["article"].get("body_plain_retained") is False, "Article body retained in context evidence")
    require(context_before["image"].get("representation_value_retained") is False, "Image representation retained in context evidence")

    require(state.get("run_id") == args.run_id and state.get("thread_id") == args.run_id, "Checkpoint run/thread identity differs")
    require(state.get("status") == "running", "One-target slice state must remain running")
    require(state.get("next_target_index") == 1, "Checkpoint next target index differs")
    require([x.get("sequence") for x in state.get("completed_target_identities", [])] == [1], "Checkpoint completed target differs")
    require(len(state.get("recommendation_ids", [])) == 1, "Checkpoint recommendation count differs")
    require(len(state.get("validation_results", [])) == 1, "Checkpoint validation count differs")
    require(checkpoint_privacy.get("status") == "pass", "Checkpoint privacy file is not pass")
    for key in [
        "article_body_persisted",
        "image_representation_persisted",
        "drupal_password_persisted",
        "openai_api_key_persisted",
        "hidden_reasoning_persisted",
    ]:
        require(checkpoint_privacy.get(key) is False, f"Checkpoint privacy flag must be false: {key}")

    for label, snapshot in (("before", before), ("during", during), ("after", after)):
        require(snapshot.get("target_sequence_sha256") == TARGET_HASH, f"{label} target hash differs")
    require(before.get("article_source_sha256") == SOURCE_HASH, "Before Article source hash differs")
    require(during.get("article_source_sha256") == SOURCE_HASH, "During Article source hash changed")
    require(after.get("article_source_sha256") == SOURCE_HASH, "After Article source hash differs")
    require(before.get("suggestion_count") == 0, "Before suggestion count is not 0")
    require(during.get("suggestion_count") == 1, "During suggestion count is not 1")
    require(after.get("suggestion_count") == 0, "After restore suggestion count is not 0")
    require(after.get("seeded_clean") is True, "Drupal was not restored to seeded-clean")

    db_rel = core.get("runtime_db_relative_path")
    require(isinstance(db_rel, str) and db_rel.startswith("langchain/.gate2a-runtime/"), "Runtime DB path differs")
    db_path = repo / db_rel
    require(db_path.is_file(), "Runtime DB is missing during finalization")
    db_sha = sha256(db_path)
    require(db_sha == core.get("runtime_db_sha256"), "Runtime DB hash differs from core summary")
    (evidence / "runtime-db-sha256.txt").write_text(f"{db_sha}  {db_rel}\n", encoding="utf-8")

    # Evidence-value hygiene: model output and recommendation text are allowed;
    # raw image representations, credentials, authorization material, and hidden
    # reasoning are not. Scanner source code is outside the evidence directory.
    patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]{12,}", re.I),
        re.compile(r"Basic\s+[A-Za-z0-9+/=]{16,}", re.I),
        re.compile(r"data:image/[^;]+;base64,", re.I),
        re.compile(r"Authorization\s*:", re.I),
    ]
    hits: list[dict[str, str]] = []
    for path in sorted(evidence.iterdir()):
        if not path.is_file() or path.name in {"secret-scan.log", "package-files-sha256.txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                hits.append({"file": path.name, "pattern": pattern.pattern})
    require(not hits, f"Prohibited value pattern retained in evidence: {hits!r}")
    (evidence / "secret-scan.log").write_text(
        "PASS: no API key, bearer/basic credential value, authorization header, or raw image data URL retained.\n",
        encoding="utf-8",
    )

    summary = {
        "schema_version": 1,
        "status": "pass",
        "run_id": args.run_id,
        "framework": "langgraph",
        "proof_scope": "single-target-canonical-vertical-slice",
        "canonical_target_sequence": 1,
        "target_sequence_sha256": TARGET_HASH,
        "article_source_sha256": SOURCE_HASH,
        "model_id": MODEL_ID,
        "temperature": 0.0,
        "validator_version": VALIDATOR_VERSION,
        "model_call_count": 1,
        "automatic_model_retries": 0,
        "semantic_retry_loop_performed": False,
        "drupal_semantic_call_count": 6,
        "recommendation_write_count": 1,
        "recommendation_status": "pending",
        "source_article_mutation_performed": False,
        "automatic_publication_performed": False,
        "drupal_restored_to_seeded_clean": True,
        "source_context_stable_across_model_and_submission": True,
        "checkpoint_backend": "sqlite",
        "checkpoint_next_target_index": 1,
        "checkpoint_completed_sequences": [1],
        "checkpoint_privacy_pass": True,
        "human_review_performed": False,
        "continuation_boundary_exercised": False,
        "gate2c_failure_injection_exercised": False,
        "runtime_db_relative_path": db_rel,
        "runtime_db_sha256": db_sha,
    }
    write_json(evidence / "summary.json", summary)
    (evidence / "summary.md").write_text(
        "\n".join([
            "# Gate 2A Step 2A.05 Canonical Vertical Slice",
            "",
            "- **Status:** PASS candidate; not certified yet",
            f"- **Run ID / thread ID:** `{args.run_id}`",
            "- **Canonical target:** sequence `1`",
            "- **Model calls:** `1`",
            "- **Automatic model retries:** `0`",
            "- **Drupal semantic calls:** `6`",
            "- **Recommendation writes:** `1` temporary pending recommendation",
            "- **Source Article mutation:** none observed",
            "- **Automatic publication:** none",
            "- **Checkpoint next target index:** `1`",
            "- **Checkpoint persisted full Article body / image data URL / credentials:** no",
            "- **Drupal restored to seeded-clean:** yes",
            "- **Human review:** not exercised in this step",
            "- **Continuation / Gate 2C failure seam:** not exercised",
            "",
            "This candidate proves only the single-target LangGraph vertical slice. Step 2A.06 owns real human interrupt/review resume; Step 2A.08 owns the fresh 12-target continuation run.",
        ]) + "\n",
        encoding="utf-8",
    )

    rows = []
    for path in sorted(evidence.iterdir()):
        if path.is_file() and path.name != "package-files-sha256.txt":
            rows.append(f"{sha256(path)}  {path.name}\n")
    (evidence / "package-files-sha256.txt").write_text("".join(rows), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
