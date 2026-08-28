#!/usr/bin/env python3
"""Permanent lifecycle auditor for Gate 2B Step 2B.06."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from jsonschema import Draft202012Validator

from gate2b_step06_batch import (
    ACTIVATION_FILES,
    BATCH_STAGE_FILES,
    FAILED_JSON_SHA256,
    FAILED_ATTEMPT_ID,
    FAILED_MANIFEST_SHA256,
    FAILED_RUN_ID,
    FAILED_RUNTIME_SHA256,
    FAILED_RUNTIME_SIZE,
    FAILURE_DISPOSITION_FILES,
    FINAL_FILES,
    FINAL_GOVERNANCE_FILES,
    FINAL_EVIDENCE_MANIFEST_SHA256,
    FINAL_SUMMARY_SHA256,
    HTTP_READINESS_FILES,
    GOVERNANCE_SUPPLEMENT_FILES,
    GOVERNANCE_SUPPLEMENT_JSON_SHA256,
    GOVERNANCE_SUPPLEMENT_MANIFEST_SHA256,
    SUCCESS_RUN_ID,
    SUCCESS_BATCH_MANIFEST_SHA256,
    SUCCESS_ACCOUNTING_SHA256,
    SUCCESS_RUNTIME_STATE_SHA256,
    SUCCESS_RUNTIME_SHA256,
    SUCCESS_RUNTIME_SIZE,
    DISPOSITION_MANIFEST_SHA256,
    READINESS_MANIFEST_SHA256,
    ACTIVATION_MANIFEST_SHA256,
    ACTIVATION_ID,
    HTTP_READINESS_ID,
    SOURCE_PROJECTION,
    PREDECESSOR,
    SNAPSHOT_ID,
    SNAPSHOT_SHA256,
    SNAPSHOT_SIZE,
    TARGET_SEQUENCE_SHA256,
    canonical,
    drupal_capture,
    feedback_collapse_zero_proof,
    snapshot_integrity,
    verify_batch_stage_within_final,
    verify_exact_batch_stage,
)

EXPECTED_AGENT = {
    "access content",
    "create alt_text_suggestion content",
    "use agentic harness discovery tools",
    "view own unpublished content",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def exact_files(evidence: Path, expected: tuple[str, ...]) -> None:
    actual = tuple(sorted(path.name for path in evidence.iterdir() if path.is_file()))
    require(actual == tuple(sorted(expected)), "Evidence file set is not exact")


def verify_manifest(
    evidence: Path, name: str, expected_files: tuple[str, ...]
) -> str:
    manifest = json.loads((evidence / name).read_text())
    entries = manifest.get("entries")
    require(
        isinstance(entries, list) and len(entries) == len(expected_files) - 1,
        f"{name} entry count mismatch",
    )
    require(
        {item["path"] for item in entries} == set(expected_files) - {name},
        f"{name} path set mismatch",
    )
    for entry in entries:
        require(
            sha(evidence / entry["path"]) == entry["sha256"],
            f"{name} mismatch: {entry['path']}",
        )
    return sha(evidence / name)


def verify_snapshot_binding(bindings: dict[str, object]) -> None:
    snapshot = bindings.get("snapshot")
    require(isinstance(snapshot, dict), "Snapshot binding is absent")
    require(snapshot.get("id") == SNAPSHOT_ID, "Snapshot ID drifted")
    require(snapshot.get("sha256") == SNAPSHOT_SHA256, "Snapshot hash drifted")


def audit_activation(evidence: Path) -> dict[str, object]:
    exact_files(evidence, ACTIVATION_FILES)
    manifest_sha = verify_manifest(
        evidence, "activation-manifest.json", ACTIVATION_FILES
    )
    summary = json.loads((evidence / "summary.json").read_text())
    require(
        summary.get("status") == "pass"
        and summary.get("lifecycle") == "ACTIVATION_COMPLETE_MODEL_READY",
        "Activation lifecycle is not MODEL_READY",
    )
    require(
        (
            summary.get("model_provider_activity"),
            summary.get("snapshot_create_count"),
            summary.get("reset_count"),
            summary.get("restore_count"),
        )
        == (0, 0, 0, 0),
        "Activation activity budget changed",
    )
    before = json.loads((evidence / "before.json").read_text())
    after = json.loads((evidence / "after.json").read_text())
    require(before.get("modules") == {
        "agentic_harness_tools": False,
        "agentic_harness_drupal_ai": False,
    }, "Activation before-state modules drifted")
    require(after.get("modules") == {
        "agentic_harness_tools": True,
        "agentic_harness_drupal_ai": True,
    }, "Activation after-state modules drifted")
    require(set(after.get("agent_service_permissions", [])) == EXPECTED_AGENT,
            "Active least-privilege boundary failed")
    require(after.get("suggestion_count") == 0, "Activation created suggestions")
    bindings = json.loads((evidence / "bindings.json").read_text())
    verify_snapshot_binding(bindings)
    return {
        "status": "PASS",
        "lifecycle": "ACTIVATION_COMPLETE_MODEL_READY",
        "files": len(ACTIVATION_FILES),
        "manifest_entries": len(ACTIVATION_FILES) - 1,
        "manifest_sha256": manifest_sha,
    }


def audit_http_readiness(repo: Path, evidence: Path) -> dict[str, object]:
    exact_files(evidence, HTTP_READINESS_FILES)
    manifest_sha = verify_manifest(
        evidence, "http-readiness-manifest.json", HTTP_READINESS_FILES
    )
    summary = json.loads((evidence / "summary.json").read_text())
    require(
        summary.get("status") == "pass"
        and summary.get("lifecycle")
        == "AUTHENTICATED_HTTP_PREFLIGHT_PASS_MODEL_READY",
        "HTTP readiness lifecycle is not MODEL_READY",
    )
    require(
        (
            summary.get("authenticated_http_requests"),
            summary.get("authoritative_run_ids_allocated"),
            summary.get("authoritative_runtimes_created"),
            summary.get("model_provider_activity"),
            summary.get("drupal_writes"),
        )
        == (1, 0, 0, 0, 0),
        "HTTP readiness activity budget changed",
    )
    auth = json.loads((evidence / "authorization.json").read_text())
    require(
        auth.get("authoritative_run_ids_allocated") == 0
        and auth.get("authoritative_runtimes_created") == 0
        and auth.get("provider_requests") == 0
        and auth.get("submissions") == 0
        and auth.get("drupal_writes") == 0,
        "HTTP readiness crossed a forbidden boundary",
    )
    observed = json.loads((evidence / "authenticated-http.json").read_text())
    require(
        observed.get("client") == "shared.drupal_client.DrupalClient"
        and observed.get("operation") == "find_images_needing_review"
        and observed.get("http_status") == 200
        and observed.get("result") == "PASS"
        and observed.get("principal") == "agent_bot"
        and observed.get("principal_binding_matches_expected") is True
        and observed.get("credential_resynchronization_required") is False,
        "Authenticated HTTP discovery proof failed",
    )
    live = json.loads((evidence / "live-state.json").read_text())
    require(
        (
            live.get("article_count"),
            live.get("target_count"),
            live.get("suggestion_count"),
            live.get("target_sequence_sha256"),
            live.get("source_projection"),
        )
        == (20, 12, 0, TARGET_SEQUENCE_SHA256,
            "f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17"),
        "HTTP readiness live state drifted",
    )
    bindings = json.loads((evidence / "bindings.json").read_text())
    verify_snapshot_binding(bindings)
    failure = (
        repo
        / "evidence/gates/gate-2b/frozen-batch-failures"
        / FAILED_RUN_ID
        / "gate2b-step06-attempt-20260827T125530Z-185709"
    )
    runtime = repo / "crewai/.runtime/gate2b-step06" / FAILED_RUN_ID / "flow-state.sqlite"
    require(sha(failure / "failure.json") == FAILED_JSON_SHA256,
            "Historical failure.json drifted")
    require(sha(failure / "failure-manifest.json") == FAILED_MANIFEST_SHA256,
            "Historical failure manifest drifted")
    require(runtime.stat().st_size == FAILED_RUNTIME_SIZE
            and sha(runtime) == FAILED_RUNTIME_SHA256,
            "Historical failed runtime drifted")
    return {
        "status": "PASS",
        "lifecycle": "AUTHENTICATED_HTTP_PREFLIGHT_PASS_MODEL_READY",
        "files": len(HTTP_READINESS_FILES),
        "manifest_entries": len(HTTP_READINESS_FILES) - 1,
        "manifest_sha256": manifest_sha,
        "authoritative_run_ids_allocated": 0,
    }


def audit_failure_disposition(evidence: Path) -> dict[str, object]:
    exact_files(evidence, FAILURE_DISPOSITION_FILES)
    manifest_sha = verify_manifest(
        evidence, "disposition-manifest.json", FAILURE_DISPOSITION_FILES
    )
    disposition = json.loads((evidence / "disposition.json").read_text())
    require(
        disposition.get("status") == "pass"
        and disposition.get("failed_run_id") == FAILED_RUN_ID
        and disposition.get("failure_json_sha256") == FAILED_JSON_SHA256
        and disposition.get("failure_manifest_sha256") == FAILED_MANIFEST_SHA256
        and disposition.get("failed_runtime", {}).get("sha256")
        == FAILED_RUNTIME_SHA256
        and disposition.get("failed_runtime", {}).get("size")
        == FAILED_RUNTIME_SIZE
        and disposition.get("root_cause")
        == "ambient_password_binding_differed_from_governed_agent_bot_credential"
        and disposition.get("privacy") == "PASS",
        "Historical failure disposition drifted",
    )
    return {
        "status": "PASS",
        "files": len(FAILURE_DISPOSITION_FILES),
        "manifest_entries": len(FAILURE_DISPOSITION_FILES) - 1,
        "manifest_sha256": manifest_sha,
    }


def audit_governance_supplement(
    repo: Path, batch: Path, evidence: Path, *, batch_shape: str = "batch-stage"
) -> dict[str, object]:
    require(batch_shape in {"batch-stage", "finalized"}, "Unknown batch shape")
    original_manifest = (
        verify_exact_batch_stage(batch)
        if batch_shape == "batch-stage"
        else verify_batch_stage_within_final(batch)
    )
    require(original_manifest == SUCCESS_BATCH_MANIFEST_SHA256,
            "Governance supplement does not bind the accepted batch")
    exact_files(evidence, GOVERNANCE_SUPPLEMENT_FILES)
    manifest_sha = verify_manifest(
        evidence, "supplement-manifest.json", GOVERNANCE_SUPPLEMENT_FILES
    )
    value = json.loads((evidence / "supplement.json").read_text())
    require(
        value.get("status") == "pass"
        and value.get("acceptance_status") == "BATCH_STAGE_ACCEPTED_AWAITING_RESTORE"
        and value.get("lifecycle") == "BATCH_COMPLETE_AWAITING_RESTORE"
        and value.get("successful_run_id") == SUCCESS_RUN_ID,
        "Supplement lifecycle or successful identity drifted",
    )
    stage = value.get("batch_stage", {})
    require(
        stage.get("manifest_sha256") == SUCCESS_BATCH_MANIFEST_SHA256
        and stage.get("files") == 15
        and stage.get("manifest_entries") == 14
        and stage.get("accounting_sha256") == SUCCESS_ACCOUNTING_SHA256
        and stage.get("runtime_state_sha256") == SUCCESS_RUNTIME_STATE_SHA256,
        "Supplement batch-stage binding failed",
    )
    historical = value.get("historical_failure", {})
    require(
        historical.get("run_id") == FAILED_RUN_ID
        and historical.get("failure_json_sha256") == FAILED_JSON_SHA256
        and historical.get("failure_manifest_sha256") == FAILED_MANIFEST_SHA256
        and historical.get("runtime_sha256") == FAILED_RUNTIME_SHA256
        and historical.get("disposition_manifest_sha256")
        == DISPOSITION_MANIFEST_SHA256,
        "Supplement historical failure/disposition binding failed",
    )
    require(
        value.get("readiness_manifest_sha256") == READINESS_MANIFEST_SHA256
        and value.get("activation_manifest_sha256") == ACTIVATION_MANIFEST_SHA256,
        "Supplement readiness/activation binding failed",
    )
    verify_snapshot_binding(value)
    runtime = value.get("successful_runtime", {})
    require(
        runtime.get("sha256") == SUCCESS_RUNTIME_SHA256
        and runtime.get("size") == SUCCESS_RUNTIME_SIZE
        and runtime.get("flow_state_rows") == 75
        and runtime.get("pending_feedback_rows") == 0,
        "Supplement successful runtime binding failed",
    )
    require(
        value.get("target_sequence_sha256") == TARGET_SEQUENCE_SHA256
        and value.get("source_projection") == SOURCE_PROJECTION,
        "Supplement source/target binding failed",
    )
    accounting = value.get("immutable_accounting", {})
    expected = {
        "logical_generations": 12,
        "actual_provider_requests": 12,
        "successful_provider_responses": 12,
        "recommendation_submissions": 12,
        "transport_retries": 0,
        "sdk_retries": 0,
        "guardrail_retries": 0,
        "structured_output_correction_calls": 0,
        "repair_calls": 0,
        "fallback_calls": 0,
        "learning_calls": 0,
        "feedback_collapse_calls": 0,
    }
    require(all(accounting.get(key) == count for key, count in expected.items()),
            "Supplement accounting drifted")
    proof = value.get("feedback_collapse_zero_proof", {})
    independently_proven = feedback_collapse_zero_proof(repo)
    require(
        proof == independently_proven
        and proof.get("classification")
        == "STRUCTURALLY_UNREACHABLE_AND_RUNTIME_CORROBORATED"
        and proof.get("feedback_collapse_calls") == 0,
        "Feedback-collapse zero is absent or unproven",
    )
    require(
        value.get("model_provider_activity_for_supplement") == 0
        and value.get("drupal_writes_for_supplement") == 0
        and value.get("restores_for_supplement") == 0
        and value.get("privacy") == "PASS",
        "Supplement crossed an operational or privacy boundary",
    )
    return {
        "status": "PASS",
        "acceptance_status": "BATCH_STAGE_ACCEPTED_AWAITING_RESTORE",
        "lifecycle": "BATCH_COMPLETE_AWAITING_RESTORE",
        "files": len(GOVERNANCE_SUPPLEMENT_FILES),
        "manifest_entries": 1,
        "manifest_sha256": manifest_sha,
        "batch_manifest_sha256": original_manifest,
        "feedback_collapse_calls": 0,
        "batch_validator_mode": batch_shape,
    }


def audit_batch(
    evidence: Path,
    *,
    rehearsal: bool,
    repo: Path | None = None,
    supplement: Path | None = None,
) -> dict[str, object]:
    exact_files(evidence, BATCH_STAGE_FILES)
    manifest_sha = verify_manifest(evidence, "batch-manifest.json", BATCH_STAGE_FILES)
    runtime = json.loads((evidence / "runtime-state.json").read_text())
    require(runtime.get("lifecycle") == "BATCH_COMPLETE_AWAITING_RESTORE",
            "Batch lifecycle is not awaiting restore")
    require(runtime.get("completed_sequences") == list(range(1, 13)),
            "Batch completion sequence drifted")
    accounting = json.loads((evidence / "model-provider-accounting.json").read_text())
    expected_provider = 0 if rehearsal else 12
    require(accounting.get("logical_generations") == 12, "Logical generation count drifted")
    require(accounting.get("actual_provider_requests") == expected_provider,
            "Provider request count drifted")
    require(accounting.get("successful_provider_responses") == expected_provider,
            "Provider response count drifted")
    for key in (
        "transport_retries",
        "sdk_retries",
        "guardrail_retries",
        "structured_output_correction_calls",
        "repair_calls",
        "fallback_calls",
        "learning_calls",
    ):
        require(accounting.get(key) == 0, f"Nonzero {key}")
    authorization = json.loads((evidence / "authorization.json").read_text())
    require(
        (
            authorization.get("snapshot_creates"),
            authorization.get("resets"),
            authorization.get("restores"),
        )
        == (0, 0, 0),
        "batch-only crossed another transaction phase",
    )
    idempotency = json.loads((evidence / "idempotency.json").read_text())
    for key in (
        "exact_order",
        "unique_targets",
        "unique_recommendations",
        "stale_runtime_blocked",
        "accepted_rerun_blocked",
        "target_order_drift_blocked",
    ):
        require(idempotency.get(key) is True, f"Idempotency predicate failed: {key}")
    bindings = json.loads((evidence / "bindings.json").read_text())
    verify_snapshot_binding(bindings)
    require(
        isinstance(bindings.get("http_readiness_manifest_sha256"), str)
        and len(bindings["http_readiness_manifest_sha256"]) == 64,
        "Batch evidence does not bind authenticated HTTP readiness",
    )
    governance: dict[str, object] | None = None
    if not rehearsal and bindings.get("run_id") == SUCCESS_RUN_ID:
        require(repo is not None and supplement is not None,
                "Accepted historical batch requires its governance supplement")
        governance = audit_governance_supplement(repo, evidence, supplement)
    elif not rehearsal:
        require(
            accounting.get("feedback_collapse_calls") == 0
            and bindings.get("historical_failed_run_id") == FAILED_RUN_ID
            and bindings.get("historical_disposition_manifest_sha256")
            == DISPOSITION_MANIFEST_SHA256,
            "Future batch family lacks direct governance accounting/binding",
        )
    result = {
        "status": "PASS",
        "lifecycle": "BATCH_COMPLETE_AWAITING_RESTORE",
        "files": len(BATCH_STAGE_FILES),
        "manifest_entries": len(BATCH_STAGE_FILES) - 1,
        "manifest_sha256": manifest_sha,
    }
    if governance is not None:
        result["governance_supplement"] = governance
    return result


def audit_final(repo: Path, evidence: Path, *, rehearsal: bool) -> dict[str, object]:
    exact_files(evidence, FINAL_FILES)
    batch_entries = json.loads((evidence / "batch-manifest.json").read_text())["entries"]
    for entry in batch_entries:
        require(sha(evidence / entry["path"]) == entry["sha256"],
                f"Immutable batch-stage evidence changed: {entry['path']}")
    final_sha = verify_manifest(evidence, "evidence-manifest.json", FINAL_FILES)
    summary = json.loads((evidence / "summary.json").read_text())
    schema = json.loads(
        (repo / "shared/schemas/gate2b-step06-batch-evidence.schema.json").read_text()
    )
    errors = sorted(
        Draft202012Validator(schema).iter_errors(summary),
        key=lambda item: list(item.path),
    )
    require(
        not errors,
        "Summary schema failed: " + "; ".join(error.message for error in errors),
    )
    require(summary.get("status") == "pass"
            and summary.get("lifecycle") == "STEP_2B_06_COMPLETE",
            "Final lifecycle is not complete")
    require(summary.get("completed_sequences") == list(range(1, 13)),
            "Final sequences drifted")
    require(summary.get("recommendation_count") == 12
            and summary.get("recommendation_submissions") == 12,
            "Final recommendation accounting drifted")
    require(summary.get("logical_generations") == 12, "Final generation count drifted")
    expected_provider = 0 if rehearsal else 12
    require(summary.get("provider_requests") == expected_provider
            and summary.get("provider_responses") == expected_provider,
            "Final provider accounting drifted")
    require(summary.get("duplicate_targets") == 0
            and summary.get("duplicate_recommendations") == 0,
            "Final duplicate accounting drifted")
    require(summary.get("source_mutations") == 0
            and summary.get("privacy") == "PASS"
            and summary.get("drupal_restored") is True
            and summary.get("gate2c_executed") is False,
            "Final governance assertions failed")
    baseline = json.loads((evidence / "baseline.json").read_text())
    require(baseline.get("batch_manifest_sha256") == sha(evidence / "batch-manifest.json"),
            "Final evidence does not bind immutable batch stage")
    require(
        (
            baseline.get("restore_count"),
            baseline.get("snapshot_deleted"),
            baseline.get("drupal_restored"),
        )
        == (1, False, True),
        "Restore-only accounting drifted",
    )
    if not rehearsal:
        result = subprocess.run(
            ["git", "-C", str(repo), "merge-base", "--is-ancestor", PREDECESSOR, "HEAD"]
        )
        require(result.returncode == 0, "Step 2B.05 merge is not an ancestor")
    return {
        "status": "PASS",
        "lifecycle": "STEP_2B_06_COMPLETE",
        "files": len(FINAL_FILES),
        "manifest_entries": len(FINAL_FILES) - 1,
        "manifest_sha256": final_sha,
        "batch_manifest_sha256": sha(evidence / "batch-manifest.json"),
    }


def audit_final_governance(
    repo: Path,
    final: Path,
    supplement: Path,
    evidence: Path,
    *,
    rehearsal: bool,
) -> dict[str, object]:
    """Compose stage-specific validators without flattening historical lifecycles."""
    final_audit = audit_final(repo, final, rehearsal=rehearsal)
    require(
        final_audit["manifest_sha256"] == FINAL_EVIDENCE_MANIFEST_SHA256,
        "Final evidence-manifest identity drifted",
    )
    require(sha(final / "summary.json") == FINAL_SUMMARY_SHA256,
            "Final summary identity drifted")
    batch_manifest = verify_batch_stage_within_final(final)
    supplement_audit = audit_governance_supplement(
        repo, final, supplement, batch_shape="finalized"
    )
    require(
        supplement_audit["manifest_sha256"]
        == GOVERNANCE_SUPPLEMENT_MANIFEST_SHA256
        and sha(supplement / "supplement.json")
        == GOVERNANCE_SUPPLEMENT_JSON_SHA256,
        "Governance supplement identity drifted",
    )
    exact_files(evidence, FINAL_GOVERNANCE_FILES)
    manifest_sha = verify_manifest(
        evidence, "final-governance-manifest.json", FINAL_GOVERNANCE_FILES
    )
    value = json.loads((evidence / "final-governance.json").read_text())
    require(
        value.get("status") == "pass"
        and value.get("acceptance_status") == "FINAL_GOVERNANCE_ACCEPTED"
        and value.get("successful_run_id") == SUCCESS_RUN_ID,
        "Final-governance identity or acceptance state drifted",
    )
    closure = value.get("finalized_closure", {})
    require(
        closure.get("files") == 19
        and closure.get("manifest_entries") == 18
        and closure.get("evidence_manifest_sha256")
        == FINAL_EVIDENCE_MANIFEST_SHA256
        and closure.get("summary_sha256") == FINAL_SUMMARY_SHA256
        and closure.get("batch_manifest_sha256") == batch_manifest,
        "Final closure cross-binding failed",
    )
    governance = value.get("governance_supplement", {})
    require(
        governance.get("files") == 2
        and governance.get("manifest_entries") == 1
        and governance.get("supplement_sha256")
        == GOVERNANCE_SUPPLEMENT_JSON_SHA256
        and governance.get("manifest_sha256")
        == GOVERNANCE_SUPPLEMENT_MANIFEST_SHA256
        and governance.get("feedback_collapse_classification")
        == "STRUCTURALLY_UNREACHABLE_AND_RUNTIME_CORROBORATED",
        "Supplement cross-binding failed",
    )
    runtime = value.get("successful_runtime", {})
    require(
        runtime.get("sha256") == SUCCESS_RUNTIME_SHA256
        and runtime.get("size") == SUCCESS_RUNTIME_SIZE
        and runtime.get("flow_state_rows") == 75
        and runtime.get("pending_feedback_rows") == 0,
        "Successful runtime cross-binding failed",
    )
    historical = value.get("historical_failure", {})
    require(
        historical.get("run_id") == FAILED_RUN_ID
        and historical.get("failure_json_sha256") == FAILED_JSON_SHA256
        and historical.get("failure_manifest_sha256") == FAILED_MANIFEST_SHA256
        and historical.get("runtime_sha256") == FAILED_RUNTIME_SHA256
        and historical.get("disposition_manifest_sha256")
        == DISPOSITION_MANIFEST_SHA256,
        "Historical failure/disposition cross-binding failed",
    )
    require(
        value.get("authenticated_readiness_manifest_sha256")
        == READINESS_MANIFEST_SHA256
        and value.get("activation_manifest_sha256")
        == ACTIVATION_MANIFEST_SHA256,
        "Readiness/activation cross-binding failed",
    )
    snapshot = value.get("snapshot", {})
    require(
        snapshot.get("id") == SNAPSHOT_ID
        and snapshot.get("sha256") == SNAPSHOT_SHA256
        and snapshot.get("size") == SNAPSHOT_SIZE
        and snapshot.get("restore_count") == 1
        and snapshot.get("retained") is True,
        "Snapshot/restoration cross-binding failed",
    )
    require(
        value.get("restoration_state") == "RESTORE_VERIFIED"
        and value.get("step_lifecycle") == "STEP_2B_06_COMPLETE"
        and value.get("snapshot_state") == "SNAPSHOT_RETAINED"
        and value.get("readiness")
        == "READY_FOR_SEPARATE_CLEANUP_AND_STAGING_DECISION",
        "Composite lifecycle drifted",
    )
    accounting = value.get("experimental_accounting", {})
    expected_accounting = {
        "logical_generations": 12,
        "provider_requests": 12,
        "provider_responses": 12,
        "recommendation_submissions": 12,
        "transport_retries": 0,
        "sdk_retries": 0,
        "guardrail_retries": 0,
        "correction_calls": 0,
        "repair_calls": 0,
        "fallback_calls": 0,
        "learning_calls": 0,
        "feedback_collapse_calls": 0,
    }
    require(accounting == expected_accounting, "Composite accounting drifted")
    restored = value.get("restored_state", {})
    baseline = json.loads((final / "baseline.json").read_text())
    current = drupal_capture(repo)
    require(
        restored.get("canonical_sha256") == baseline.get("post_restore_state_sha256")
        == canonical(current)
        and (
            restored.get("article_count"),
            restored.get("target_count"),
            restored.get("suggestion_count"),
        )
        == (20, 12, 1)
        and restored.get("suggestions") == current.get("suggestions")
        and restored.get("target_sequence_sha256") == TARGET_SEQUENCE_SHA256
        and restored.get("source_projection") == SOURCE_PROJECTION,
        "Canonical restored-state cross-binding failed",
    )
    expected_predicates = {
        "experiment_execution": "PASS",
        "batch_stage_governance": "PASS",
        "restoration": "PASS",
        "final_closure": "PASS",
        "final_supplement_binding": "PASS",
        "composite_privacy": "PASS",
    }
    require(value.get("acceptance_predicates") == expected_predicates,
            "Composite acceptance predicates drifted")
    require(value.get("privacy") == "PASS", "Composite privacy failed")
    forbidden = ("OPENAI_API_KEY", "Authorization", "Basic Auth", "data:image")
    artifact_text = (evidence / "final-governance.json").read_text()
    require(not any(token in artifact_text for token in forbidden),
            "Final-governance artifact contains forbidden private material")
    actual_snapshot = snapshot_integrity(repo)
    require(actual_snapshot["sha256"] == SNAPSHOT_SHA256,
            "Retained snapshot drifted")
    failure = repo / "evidence/gates/gate-2b/frozen-batch-failures" / FAILED_RUN_ID / FAILED_ATTEMPT_ID
    disposition = repo / "evidence/gates/gate-2b/frozen-batch-failure-disposition" / FAILED_RUN_ID / f"{FAILED_ATTEMPT_ID}-v102" / "disposition-manifest.json"
    readiness = repo / "evidence/gates/gate-2b/frozen-batch-http-readiness" / HTTP_READINESS_ID / "http-readiness-manifest.json"
    activation = repo / "evidence/gates/gate-2b/frozen-batch-activation" / ACTIVATION_ID / "activation-manifest.json"
    successful_runtime = repo / "crewai/.runtime/gate2b-step06" / SUCCESS_RUN_ID / "flow-state.sqlite"
    failed_runtime = repo / "crewai/.runtime/gate2b-step06" / FAILED_RUN_ID / "flow-state.sqlite"
    require(
        sha(failure / "failure.json") == FAILED_JSON_SHA256
        and sha(failure / "failure-manifest.json") == FAILED_MANIFEST_SHA256
        and sha(disposition) == DISPOSITION_MANIFEST_SHA256
        and sha(readiness) == READINESS_MANIFEST_SHA256
        and sha(activation) == ACTIVATION_MANIFEST_SHA256
        and sha(successful_runtime) == SUCCESS_RUNTIME_SHA256
        and sha(failed_runtime) == FAILED_RUNTIME_SHA256,
        "Bound predecessor chain drifted",
    )
    return {
        "status": "PASS",
        "experiment_execution": "PASS",
        "batch_stage_governance": "PASS",
        "restoration": "PASS",
        "final_closure": "PASS",
        "final_supplement_binding": "PASS",
        "composite_privacy": "PASS",
        "lifecycle": "STEP_2B_06_COMPLETE",
        "restoration_state": "RESTORE_VERIFIED",
        "final_governance": "FINAL_GOVERNANCE_ACCEPTED",
        "snapshot_state": "SNAPSHOT_RETAINED",
        "readiness": "READY_FOR_SEPARATE_CLEANUP_AND_STAGING_DECISION",
        "files": 2,
        "manifest_entries": 1,
        "manifest_sha256": manifest_sha,
        "final_evidence_manifest_sha256": FINAL_EVIDENCE_MANIFEST_SHA256,
        "supplement_manifest_sha256": GOVERNANCE_SUPPLEMENT_MANIFEST_SHA256,
        "batch_manifest_sha256": batch_manifest,
        "feedback_collapse_calls": 0,
        "batch_validator_mode": "embedded-batch-stage-within-finalized-19",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=(
            "activation", "http-readiness", "failure-disposition",
            "batch", "governance-supplement", "final", "final-composite",
        ),
        required=True,
    )
    parser.add_argument("--rehearsal", action="store_true")
    parser.add_argument("--batch", type=Path)
    parser.add_argument("--supplement", type=Path)
    parser.add_argument("--final-governance", type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "activation":
            result = audit_activation(args.evidence.resolve())
        elif args.mode == "http-readiness":
            result = audit_http_readiness(args.repo.resolve(), args.evidence.resolve())
        elif args.mode == "failure-disposition":
            result = audit_failure_disposition(args.evidence.resolve())
        elif args.mode == "batch":
            result = audit_batch(
                args.evidence.resolve(),
                rehearsal=args.rehearsal,
                repo=args.repo.resolve(),
                supplement=args.supplement.resolve() if args.supplement else None,
            )
        elif args.mode == "governance-supplement":
            if not args.batch:
                parser.error("governance-supplement requires --batch")
            result = audit_governance_supplement(
                args.repo.resolve(), args.batch.resolve(), args.evidence.resolve()
            )
        elif args.mode == "final":
            result = audit_final(
                args.repo.resolve(), args.evidence.resolve(), rehearsal=args.rehearsal
            )
        else:
            if not args.supplement or not args.final_governance:
                parser.error(
                    "final-composite requires --supplement and --final-governance"
                )
            result = audit_final_governance(
                args.repo.resolve(),
                args.evidence.resolve(),
                args.supplement.resolve(),
                args.final_governance.resolve(),
                rehearsal=args.rehearsal,
            )
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
