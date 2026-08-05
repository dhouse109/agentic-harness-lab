#!/usr/bin/env python3
"""Evaluate and audit Gate 0.5 Step 04 human-review evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

PACKAGE_VERSION = "1.0.0"

IMPLEMENTATION_FILES = [
    "drupal/web/modules/custom/agentic_harness_tools/agentic_harness_tools.routing.yml",
    "drupal/web/modules/custom/agentic_harness_tools/agentic_harness_tools.services.yml",
    "drupal/web/modules/custom/agentic_harness_tools/src/Controller/ToolController.php",
    "drupal/web/modules/custom/agentic_harness_tools/src/Exception/RecommendationStatusException.php",
    "drupal/web/modules/custom/agentic_harness_tools/src/Exception/RecommendationSubmissionException.php",
    "drupal/web/modules/custom/agentic_harness_tools/src/Service/RecommendationStatusProvider.php",
    "drupal/web/modules/custom/agentic_harness_tools/src/Service/RecommendationSubmitter.php",
    "drupal/web/modules/custom/agentic_harness_tools/src/Service/RecommendationValidator.php",
    "drupal/scripts/gate05-step04.php",
    "scripts/gate05_step04_evidence.py",
    "scripts/run-gate05-step04.sh",
    "shared/drupal_client/client.py",
    "shared/drupal_client/README.md",
    "shared/schemas/target.schema.json",
    "shared/schemas/recommendation.schema.json",
    "shared/schemas/tool-result.schema.json",
]


class EvidenceError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"Missing required file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def implementation_hashes(repo: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative in IMPLEMENTATION_FILES:
        path = repo / relative
        if not path.is_file():
            raise EvidenceError(f"Missing Step 04 implementation file: {relative}")
        hashes[relative] = sha256_bytes(path.read_bytes())
    return hashes


def scan_retained_evidence(run_dir: Path) -> None:
    patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
        re.compile(r"(?i)authorization\s*:\s*(?:bearer|basic)\s+(?!<redacted>)\S+"),
        re.compile(r"(?i)(?:password|OPENAI_API_KEY)\s*[=:]\s*(?!<redacted>)\S+"),
        re.compile(r"(?i)user\s*=\s*[\"'][^\"']+:[^\"']+[\"']"),
    ]
    for path in run_dir.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in patterns:
            if pattern.search(text):
                raise EvidenceError(
                    f"Potential credential retained in evidence: {path.name}"
                )


def validate_submit_envelope(
    envelope: Any,
    request: dict[str, Any],
) -> dict[str, Any]:
    expected_envelope = {
        "schema_version",
        "tool_name",
        "ok",
        "timestamp",
        "correlation_id",
        "data",
        "error",
    }
    if not isinstance(envelope, dict) or set(envelope) != expected_envelope:
        raise EvidenceError("Submission envelope keys are invalid.")
    if (
        envelope["schema_version"] != 1
        or envelope["tool_name"] != "submit_recommendation"
        or envelope["ok"] is not True
        or envelope["error"] is not None
    ):
        raise EvidenceError("Submission response is not successful.")

    data = envelope["data"]
    expected_data = {
        "node_id",
        "uuid",
        "revision_id",
        "status",
        "source_framework",
        "run_id",
        "target",
    }
    if not isinstance(data, dict) or set(data) != expected_data:
        raise EvidenceError("Submission result does not match the frozen tool result.")
    if (
        not isinstance(data["node_id"], int)
        or data["node_id"] < 1
        or not isinstance(data["revision_id"], int)
        or data["revision_id"] < 1
        or data["status"] != "pending"
        or data["source_framework"] != request["source_framework"]
        or data["run_id"] != request["run_id"]
        or data["target"] != request["target"]
    ):
        raise EvidenceError("Submission result values are invalid.")
    if not isinstance(data["uuid"], str) or not re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
        r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}",
        data["uuid"],
    ):
        raise EvidenceError("Submission UUID is invalid.")
    return data


def validate_status_envelope(
    envelope: Any,
    *,
    expected_uuid: str,
    expected_status: str,
) -> dict[str, Any]:
    expected_envelope = {
        "schema_version",
        "tool_name",
        "ok",
        "timestamp",
        "correlation_id",
        "data",
        "error",
    }
    if not isinstance(envelope, dict) or set(envelope) != expected_envelope:
        raise EvidenceError("Status envelope keys are invalid.")
    if (
        envelope["schema_version"] != 1
        or envelope["tool_name"] != "get_recommendation_status"
        or envelope["ok"] is not True
        or envelope["error"] is not None
    ):
        raise EvidenceError("Status response is not successful.")

    data = envelope["data"]
    expected_data = {
        "uuid",
        "revision_id",
        "status",
        "reviewer_username",
        "reviewed_at",
    }
    if not isinstance(data, dict) or set(data) != expected_data:
        raise EvidenceError("Status result does not match tool-result.schema.json.")
    if (
        data["uuid"] != expected_uuid
        or not isinstance(data["revision_id"], int)
        or data["revision_id"] < 1
        or data["status"] != expected_status
    ):
        raise EvidenceError("Status result identity or state is invalid.")

    if expected_status == "pending":
        if data["reviewer_username"] is not None or data["reviewed_at"] is not None:
            raise EvidenceError("Pending status exposed reviewer metadata.")
    else:
        if not isinstance(data["reviewer_username"], str) or not data["reviewer_username"]:
            raise EvidenceError("Reviewed status lacks reviewer_username.")
        if not isinstance(data["reviewed_at"], str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
            data["reviewed_at"],
        ):
            raise EvidenceError("Reviewed status lacks a valid reviewed_at value.")
    return data


def error_code(path: Path) -> str:
    value = load_json(path)
    if not isinstance(value, dict) or not isinstance(value.get("error"), dict):
        raise EvidenceError(f"Invalid negative response: {path.name}")
    return str(value["error"].get("code", ""))


def assert_snapshot(value: Any, label: str) -> dict[str, Any]:
    required = {
        "article_count",
        "article_source_sha256",
        "suggestion_count",
        "recommendation_state_sha256",
        "combined_state_sha256",
    }
    if not isinstance(value, dict) or not required.issubset(value):
        raise EvidenceError(f"{label} snapshot is incomplete.")
    if value["article_count"] != 20:
        raise EvidenceError(f"{label} snapshot does not contain 20 Articles.")
    return value


def audit_prior_step03(repo: Path) -> None:
    pointer = (
        repo
        / "evidence/gates/gate-0.5/submit-recommendation/GATE05-STEP03-LATEST.txt"
    )
    if not pointer.is_file():
        raise EvidenceError("Passing Step 03 pointer is missing.")

    relative = pointer.read_text(encoding="utf-8").strip()
    if not re.fullmatch(
        r"evidence/gates/gate-0\.5/submit-recommendation/"
        r"gate05-step03-[A-Za-z0-9._-]+",
        relative,
    ):
        raise EvidenceError("Unexpected Step 03 evidence pointer.")

    run_dir = repo / relative
    required = [
        "summary.json",
        "summary.md",
        "submission-request.json",
        "submit-response.json",
        "submit-replay-response.json",
        "recommendation-inspection.json",
        "http-statuses.json",
        "authorization.json",
        "environment.json",
        "source-before.json",
        "source-after.json",
        "source-final-clean.json",
        "implementation-sha256.txt",
        "setup.log",
        "reset-before.log",
        "reset-after.log",
        "positive-client.log",
        "replay-client.log",
    ]
    for filename in required:
        if not (run_dir / filename).is_file():
            raise EvidenceError(f"Missing retained Step 03 evidence: {filename}")

    summary = load_json(run_dir / "summary.json")
    if (
        not isinstance(summary, dict)
        or summary.get("status") != "pass"
        or summary.get("operation") != "submit_recommendation"
        or summary.get("controlled_preflight") is not True
        or summary.get("framework_execution_claimed") is not False
        or summary.get("model_call_performed") is not False
        or summary.get("idempotent_replay_same_identity") is not True
        or summary.get("source_article_unchanged") is not True
        or summary.get("final_reset_clean") is not True
        or summary.get("transient_suggestion_count") != 1
        or summary.get("final_suggestion_count") != 0
    ):
        raise EvidenceError("Retained Step 03 summary controls failed.")

    request = load_json(run_dir / "submission-request.json")
    positive = validate_submit_envelope(
        load_json(run_dir / "submit-response.json"),
        request,
    )
    replay = validate_submit_envelope(
        load_json(run_dir / "submit-replay-response.json"),
        request,
    )
    if positive != replay or positive != summary.get("transient_recommendation"):
        raise EvidenceError("Retained Step 03 idempotency identity is inconsistent.")

    before = load_json(run_dir / "source-before.json")
    transient = load_json(run_dir / "source-after.json")
    final = load_json(run_dir / "source-final-clean.json")
    for label, value in (
        ("Step 03 before", before),
        ("Step 03 transient", transient),
        ("Step 03 final", final),
    ):
        if not isinstance(value, dict):
            raise EvidenceError(f"{label} snapshot is missing.")

    article_hash = before.get("article_source_sha256")
    if (
        not isinstance(article_hash, str)
        or article_hash != transient.get("article_source_sha256")
        or article_hash != final.get("article_source_sha256")
        or before.get("suggestion_count") != 0
        or transient.get("suggestion_count") != 1
        or final.get("suggestion_count") != 0
        or before.get("combined_state_sha256")
        == transient.get("combined_state_sha256")
        or before.get("combined_state_sha256")
        != final.get("combined_state_sha256")
    ):
        raise EvidenceError("Retained Step 03 source and reset controls failed.")

    environment = load_json(run_dir / "environment.json")
    if (
        environment.get("controlled_preflight") is not True
        or environment.get("framework_execution_claimed") is not False
        or environment.get("model_call_performed") is not False
    ):
        raise EvidenceError("Retained Step 03 environment labels failed.")

    scan_retained_evidence(run_dir)

    print(json.dumps({
        "status": "pass",
        "run_id": run_dir.name,
        "operation": "submit_recommendation",
        "canonical_target_sequence": summary.get("canonical_target_sequence"),
        "article_source_sha256": article_hash,
        "idempotent_replay_same_identity": True,
        "final_suggestion_count": 0,
        "retained_evidence_integrity": True,
        "historical_implementation_hashes_used_as_current_gate": False,
        "controlled_preflight": True,
        "framework_execution_claimed": False,
    }, indent=2, sort_keys=True))


def evaluate_prepare(repo: Path, run_dir: Path) -> None:
    request = load_json(run_dir / "submission-request.json")
    if (
        not isinstance(request, dict)
        or request.get("schema_version") != 1
        or request.get("source_framework") != "drupal_ai"
        or request.get("validator_version") != "gate05-validator-1.0.0"
        or request.get("target", {}).get("sequence") != 1
    ):
        raise EvidenceError("Step 04 controlled submission request is invalid.")

    submit = validate_submit_envelope(
        load_json(run_dir / "submit-response.json"),
        request,
    )
    replay = validate_submit_envelope(
        load_json(run_dir / "submit-replay-response.json"),
        request,
    )
    if submit != replay:
        raise EvidenceError("Step 04 submission replay changed identity.")

    pending_uuid = validate_status_envelope(
        load_json(run_dir / "pending-status-uuid.json"),
        expected_uuid=submit["uuid"],
        expected_status="pending",
    )
    pending_nid = validate_status_envelope(
        load_json(run_dir / "pending-status-nid.json"),
        expected_uuid=submit["uuid"],
        expected_status="pending",
    )
    pending_repeat = validate_status_envelope(
        load_json(run_dir / "pending-status-repeat.json"),
        expected_uuid=submit["uuid"],
        expected_status="pending",
    )
    if pending_uuid != pending_nid or pending_uuid != pending_repeat:
        raise EvidenceError("Pending status reads did not return identical state.")
    if pending_uuid["revision_id"] != submit["revision_id"]:
        raise EvidenceError("Pending status revision differs from submission revision.")

    inspection = load_json(run_dir / "pending-inspection.json")
    if (
        not isinstance(inspection, dict)
        or inspection.get("node_id") != submit["node_id"]
        or inspection.get("uuid") != submit["uuid"]
        or inspection.get("owner_username") != "agent_bot"
        or inspection.get("published") is not False
        or inspection.get("revision_count") != 1
        or inspection.get("current_revision_id") != submit["revision_id"]
        or inspection.get("current_review_status") != "pending"
        or inspection.get("current_proposed_alt_text")
        != request["proposed_alt_text"]
        or inspection.get("current_source_framework")
        != request["source_framework"]
        or inspection.get("current_run_id") != request["run_id"]
        or inspection.get("current_evidence_hash")
        != request["evidence_hash"]
    ):
        raise EvidenceError("Pending recommendation inspection failed.")

    access = inspection.get("access")
    if (
        not isinstance(access, dict)
        or access.get("agent_can_view") is not True
        or access.get("agent_can_update") is not False
        or access.get("editor_can_update") is not True
    ):
        raise EvidenceError("Pending recommendation access boundary failed.")

    revisions = inspection.get("revisions")
    if not isinstance(revisions, list) or len(revisions) != 1:
        raise EvidenceError("Pending recommendation revision evidence is invalid.")
    initial = revisions[0]
    if (
        initial.get("revision_user", {}).get("name") != "agent_bot"
        or initial.get("review_status") != "pending"
        or initial.get("proposed_alt_text") != request["proposed_alt_text"]
        or initial.get("source_framework") != request["source_framework"]
        or initial.get("run_id") != request["run_id"]
        or initial.get("evidence_hash") != request["evidence_hash"]
    ):
        raise EvidenceError("Initial recommendation revision is invalid.")

    before = assert_snapshot(
        load_json(run_dir / "source-before.json"),
        "Step 04 before",
    )
    pending = assert_snapshot(
        load_json(run_dir / "source-pending.json"),
        "Step 04 pending",
    )
    if (
        before["article_source_sha256"] != pending["article_source_sha256"]
        or before["suggestion_count"] != 0
        or pending["suggestion_count"] != 1
        or before["recommendation_state_sha256"]
        == pending["recommendation_state_sha256"]
        or before["combined_state_sha256"] == pending["combined_state_sha256"]
    ):
        raise EvidenceError("Pending-state mutation boundary failed.")

    statuses = load_json(run_dir / "status-http-statuses.json")
    expected_statuses = {
        "positive_uuid": 200,
        "positive_nid": 200,
        "positive_repeat": 200,
        "editor": 403,
        "invalid_id": 422,
        "unknown_uuid": 404,
        "wrong_bundle": 404,
    }
    for key, expected in expected_statuses.items():
        if statuses.get(key) != expected:
            raise EvidenceError(
                f"Unexpected status-route HTTP result for {key}: "
                f"{statuses.get(key)}"
            )
    if statuses.get("anonymous") not in {401, 403}:
        raise EvidenceError("Anonymous status access was not denied.")

    expected_codes = {
        "invalid-id.json": "INVALID_RECOMMENDATION_ID",
        "unknown-uuid.json": "RECOMMENDATION_NOT_FOUND",
        "wrong-bundle.json": "RECOMMENDATION_NOT_FOUND",
    }
    for filename, expected in expected_codes.items():
        if error_code(run_dir / filename) != expected:
            raise EvidenceError(f"Unexpected error code in {filename}.")

    environment = load_json(run_dir / "environment.json")
    for key in (
        "openai_api_key_present",
        "openai_candidate_model_present",
        "crewai_candidate_model_present",
        "model_call_performed",
        "framework_execution_claimed",
    ):
        if environment.get(key) is not False:
            raise EvidenceError(f"Controlled preflight environment failed: {key}")
    if (
        environment.get("controlled_preflight") is not True
        or environment.get("human_review_required") is not True
    ):
        raise EvidenceError("Step 04 human-review labels are missing.")

    prepare_summary = {
        "schema_version": 1,
        "package": "gate-0.5-step04-recommendation-status-human-review",
        "package_version": PACKAGE_VERSION,
        "run_id": run_dir.name,
        "status": "awaiting_human_review",
        "operation": "get_recommendation_status",
        "controlled_preflight": True,
        "framework_execution_claimed": False,
        "model_call_performed": False,
        "human_review_required": True,
        "canonical_target_sequence": 1,
        "recommendation": submit,
        "pending_status": pending_uuid,
        "article_source_sha256": before["article_source_sha256"],
        "pending_recommendation_state_sha256": pending[
            "recommendation_state_sha256"
        ],
        "source_article_unchanged": True,
        "idempotent_submission_replay": True,
        "next_action": (
            "editor_dana must set Review status to Approved in Drupal "
            "without changing Proposed alt text, then run certify."
        ),
    }
    write_json(run_dir / "prepare-summary.json", prepare_summary)
    scan_retained_evidence(run_dir)

    print(json.dumps({
        "status": "awaiting_human_review",
        "run_id": run_dir.name,
        "recommendation_node_id": submit["node_id"],
        "recommendation_uuid": submit["uuid"],
        "pending_revision_id": submit["revision_id"],
        "pending_status_reads_match": True,
        "source_article_unchanged": True,
        "human_review_required": True,
        "reviewer_username_required": "editor_dana",
    }, indent=2, sort_keys=True))


def evaluate_reviewed_precheck(repo: Path, run_dir: Path) -> None:
    prepare = load_json(run_dir / "prepare-summary.json")
    if prepare.get("status") != "awaiting_human_review":
        raise EvidenceError("Step 04 prepare summary is not awaiting review.")

    request = load_json(run_dir / "submission-request.json")
    pending_inspection = load_json(run_dir / "pending-inspection.json")
    reviewed = load_json(run_dir / "reviewed-inspection.json")
    recommendation = prepare["recommendation"]

    if (
        not isinstance(reviewed, dict)
        or reviewed.get("node_id") != recommendation["node_id"]
        or reviewed.get("uuid") != recommendation["uuid"]
        or reviewed.get("owner_username") != "agent_bot"
        or reviewed.get("title") != pending_inspection.get("title")
        or reviewed.get("published") is not False
        or reviewed.get("revision_count") != 2
        or reviewed.get("current_review_status") != "approved"
        or reviewed.get("current_proposed_alt_text")
        != request["proposed_alt_text"]
        or reviewed.get("current_source_framework")
        != request["source_framework"]
        or reviewed.get("current_run_id") != request["run_id"]
        or reviewed.get("current_evidence_hash")
        != request["evidence_hash"]
        or reviewed.get("current_target")
        != pending_inspection.get("current_target")
    ):
        raise EvidenceError(
            "The recommendation was not approved exactly once without "
            "changing immutable submission data."
        )

    revisions = reviewed.get("revisions")
    pending_revisions = pending_inspection.get("revisions")
    if (
        not isinstance(revisions, list)
        or len(revisions) != 2
        or not isinstance(pending_revisions, list)
        or len(pending_revisions) != 1
    ):
        raise EvidenceError("Reviewed revision history is invalid.")

    initial, latest = revisions
    if initial != pending_revisions[0]:
        raise EvidenceError("The initial recommendation revision changed.")
    if (
        latest.get("revision_user", {}).get("name") != "editor_dana"
        or latest.get("review_status") != "approved"
        or latest.get("proposed_alt_text") != initial.get("proposed_alt_text")
        or latest.get("source_framework") != initial.get("source_framework")
        or latest.get("run_id") != initial.get("run_id")
        or latest.get("evidence_hash") != initial.get("evidence_hash")
        or latest.get("target") != initial.get("target")
        or latest.get("published") is not False
        or latest.get("revision_id", 0) <= initial.get("revision_id", 0)
        or latest.get("timestamp_unix", 0) < initial.get("timestamp_unix", 0)
    ):
        raise EvidenceError("Latest revision is not a valid editor_dana approval.")

    access = reviewed.get("access")
    if (
        not isinstance(access, dict)
        or access.get("agent_can_view") is not True
        or access.get("agent_can_update") is not False
        or access.get("editor_can_update") is not True
    ):
        raise EvidenceError("Reviewed recommendation access boundary changed.")

    approved_uuid = validate_status_envelope(
        load_json(run_dir / "approved-status-uuid.json"),
        expected_uuid=recommendation["uuid"],
        expected_status="approved",
    )
    approved_nid = validate_status_envelope(
        load_json(run_dir / "approved-status-nid.json"),
        expected_uuid=recommendation["uuid"],
        expected_status="approved",
    )
    approved_repeat = validate_status_envelope(
        load_json(run_dir / "approved-status-repeat.json"),
        expected_uuid=recommendation["uuid"],
        expected_status="approved",
    )
    if approved_uuid != approved_nid or approved_uuid != approved_repeat:
        raise EvidenceError("Approved status reads did not return identical state.")
    if (
        approved_uuid["revision_id"] != latest["revision_id"]
        or approved_uuid["reviewer_username"] != "editor_dana"
        or approved_uuid["reviewed_at"] != latest["timestamp_utc"]
    ):
        raise EvidenceError("Status projection does not match Drupal revision evidence.")

    pending_snapshot = assert_snapshot(
        load_json(run_dir / "source-pending.json"),
        "Step 04 pending",
    )
    reviewed_before = assert_snapshot(
        load_json(run_dir / "source-reviewed-before-status.json"),
        "Step 04 reviewed-before-status",
    )
    reviewed_after = assert_snapshot(
        load_json(run_dir / "source-reviewed-after-status.json"),
        "Step 04 reviewed-after-status",
    )

    article_hash = prepare["article_source_sha256"]
    if (
        pending_snapshot["article_source_sha256"] != article_hash
        or reviewed_before["article_source_sha256"] != article_hash
        or reviewed_after["article_source_sha256"] != article_hash
        or pending_snapshot["suggestion_count"] != 1
        or reviewed_before["suggestion_count"] != 1
        or reviewed_after["suggestion_count"] != 1
        or pending_snapshot["recommendation_state_sha256"]
        == reviewed_before["recommendation_state_sha256"]
        or reviewed_before["recommendation_state_sha256"]
        != reviewed_after["recommendation_state_sha256"]
        or reviewed_before["combined_state_sha256"]
        != reviewed_after["combined_state_sha256"]
    ):
        raise EvidenceError(
            "Human-review transition or read-only status boundary failed."
        )

    precheck = {
        "status": "pass",
        "run_id": run_dir.name,
        "human_decision": "approved",
        "reviewer_username": "editor_dana",
        "reviewed_at": approved_uuid["reviewed_at"],
        "initial_revision_id": initial["revision_id"],
        "reviewed_revision_id": latest["revision_id"],
        "proposed_alt_edited": False,
        "revision_count": 2,
        "status_reads_match": True,
        "status_operation_read_only": True,
        "source_article_unchanged": True,
        "reviewed_recommendation_state_sha256": reviewed_before[
            "recommendation_state_sha256"
        ],
    }
    write_json(run_dir / "reviewed-precheck.json", precheck)
    scan_retained_evidence(run_dir)

    print(json.dumps(precheck, indent=2, sort_keys=True))


def finalize(repo: Path, run_dir: Path) -> None:
    prepare = load_json(run_dir / "prepare-summary.json")
    precheck = load_json(run_dir / "reviewed-precheck.json")
    before = assert_snapshot(
        load_json(run_dir / "source-before.json"),
        "Step 04 before",
    )
    final = assert_snapshot(
        load_json(run_dir / "source-final-clean.json"),
        "Step 04 final",
    )

    if precheck.get("status") != "pass":
        raise EvidenceError("Reviewed precheck is not passing.")
    if (
        final["article_source_sha256"] != before["article_source_sha256"]
        or final["suggestion_count"] != 0
        or final["recommendation_state_sha256"]
        != before["recommendation_state_sha256"]
        or final["combined_state_sha256"] != before["combined_state_sha256"]
    ):
        raise EvidenceError("Final seeded-clean reset did not restore baseline state.")

    hashes = implementation_hashes(repo)
    (run_dir / "implementation-sha256.txt").write_text(
        "".join(
            f"{digest}  {relative}\n"
            for relative, digest in hashes.items()
        ),
        encoding="utf-8",
    )

    summary = {
        "schema_version": 1,
        "package": "gate-0.5-step04-recommendation-status-human-review",
        "package_version": PACKAGE_VERSION,
        "run_id": run_dir.name,
        "status": "pass",
        "operations": [
            "submit_recommendation",
            "get_recommendation_status",
        ],
        "controlled_preflight": True,
        "framework_execution_claimed": False,
        "model_call_performed": False,
        "canonical_target_sequence": 1,
        "recommendation": prepare["recommendation"],
        "human_decision": {
            "status": "approved",
            "reviewer_username": precheck["reviewer_username"],
            "reviewed_at": precheck["reviewed_at"],
            "initial_revision_id": precheck["initial_revision_id"],
            "reviewed_revision_id": precheck["reviewed_revision_id"],
            "revision_count": precheck["revision_count"],
            "proposed_alt_edited": False,
        },
        "pending_status_observed": True,
        "approved_status_observed": True,
        "status_reads_match": True,
        "status_operation_read_only": True,
        "source_article_unchanged": True,
        "article_source_sha256": before["article_source_sha256"],
        "final_suggestion_count": 0,
        "final_reset_clean": True,
        "implementation_files": hashes,
        "next_step": (
            "Gate 0.5 Step 05 — end-to-end shared substrate certification "
            "and framework handoff"
        ),
    }
    write_json(run_dir / "summary.json", summary)

    (run_dir / "summary.md").write_text(
        f"""# Gate 0.5 Step 04 Human Review Summary

- **Status:** PASS
- **Run ID:** `{run_dir.name}`
- **Recommendation node:** `{prepare['recommendation']['node_id']}`
- **Recommendation UUID:** `{prepare['recommendation']['uuid']}`
- **Initial state:** `pending`
- **Human decision:** `approved`
- **Reviewer:** `editor_dana`
- **Reviewed at:** `{precheck['reviewed_at']}`
- **Revision transition:** `{precheck['initial_revision_id']} → {precheck['reviewed_revision_id']}`
- **Proposed alt edited:** no
- **Status route read-only:** yes
- **Source Article changed:** no
- **Final suggestion count:** 0
- **Model call performed:** no
- **Framework execution claimed:** no
- **Controlled preflight:** yes

The approval was created through Drupal's real editorial save path. The status operation only
observed the current recommendation revision and permitted reviewer metadata. It did not approve,
reject, edit, publish, or apply anything.

## Next step

Gate 0.5 Step 05 performs end-to-end shared substrate certification before framework-owned
implementation begins.
""",
        encoding="utf-8",
    )

    scan_retained_evidence(run_dir)


def audit(repo: Path, run_dir: Path) -> None:
    summary = load_json(run_dir / "summary.json")
    if (
        not isinstance(summary, dict)
        or summary.get("status") != "pass"
        or summary.get("controlled_preflight") is not True
        or summary.get("framework_execution_claimed") is not False
        or summary.get("model_call_performed") is not False
        or summary.get("pending_status_observed") is not True
        or summary.get("approved_status_observed") is not True
        or summary.get("status_operation_read_only") is not True
        or summary.get("source_article_unchanged") is not True
        or summary.get("final_reset_clean") is not True
        or summary.get("final_suggestion_count") != 0
    ):
        raise EvidenceError("Latest Step 04 summary controls failed.")

    required = [
        "summary.json",
        "summary.md",
        "prepare-summary.json",
        "reviewed-precheck.json",
        "submission-request.json",
        "submit-response.json",
        "submit-replay-response.json",
        "pending-status-uuid.json",
        "pending-status-nid.json",
        "pending-status-repeat.json",
        "approved-status-uuid.json",
        "approved-status-nid.json",
        "approved-status-repeat.json",
        "pending-inspection.json",
        "reviewed-inspection.json",
        "status-http-statuses.json",
        "authorization.json",
        "environment.json",
        "source-before.json",
        "source-pending.json",
        "source-reviewed-before-status.json",
        "source-reviewed-after-status.json",
        "source-final-clean.json",
        "invalid-id.json",
        "unknown-uuid.json",
        "wrong-bundle.json",
        "setup.log",
        "certify-setup.log",
        "reset-before.log",
        "reset-after.log",
        "submit-client.log",
        "replay-client.log",
        "pending-status-client.log",
        "approved-status-client.log",
        "implementation-sha256.txt",
    ]
    for filename in required:
        if not (run_dir / filename).is_file():
            raise EvidenceError(f"Missing retained Step 04 evidence: {filename}")

    current = implementation_hashes(repo)
    if current != summary.get("implementation_files"):
        raise EvidenceError("Step 04 implementation files changed after the passing run.")

    before = assert_snapshot(
        load_json(run_dir / "source-before.json"),
        "Step 04 before",
    )
    final = assert_snapshot(
        load_json(run_dir / "source-final-clean.json"),
        "Step 04 final",
    )
    if (
        before["article_source_sha256"] != final["article_source_sha256"]
        or final["suggestion_count"] != 0
        or before["recommendation_state_sha256"]
        != final["recommendation_state_sha256"]
        or before["combined_state_sha256"] != final["combined_state_sha256"]
    ):
        raise EvidenceError("Step 04 retained reset evidence is invalid.")

    scan_retained_evidence(run_dir)

    human = summary["human_decision"]
    print(json.dumps({
        "status": "pass",
        "run_id": run_dir.name,
        "operations": summary["operations"],
        "canonical_target_sequence": 1,
        "human_decision": human["status"],
        "reviewer_username": human["reviewer_username"],
        "initial_revision_id": human["initial_revision_id"],
        "reviewed_revision_id": human["reviewed_revision_id"],
        "status_operation_read_only": True,
        "source_article_unchanged": True,
        "article_source_sha256": summary["article_source_sha256"],
        "final_suggestion_count": 0,
        "implementation_hashes_match": True,
        "controlled_preflight": True,
        "framework_execution_claimed": False,
        "next_step": summary["next_step"],
    }, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    prior = sub.add_parser("audit-prior-step03")
    prior.add_argument("--repo", required=True)

    prepare = sub.add_parser("prepare")
    prepare.add_argument("--repo", required=True)
    prepare.add_argument("--run-dir", required=True)

    reviewed = sub.add_parser("reviewed-precheck")
    reviewed.add_argument("--repo", required=True)
    reviewed.add_argument("--run-dir", required=True)

    final = sub.add_parser("finalize")
    final.add_argument("--repo", required=True)
    final.add_argument("--run-dir", required=True)

    audit_parser = sub.add_parser("audit")
    audit_parser.add_argument("--repo", required=True)
    audit_parser.add_argument("--run-dir", required=True)

    args = parser.parse_args()
    try:
        repo = Path(args.repo).resolve()
        if args.command == "audit-prior-step03":
            audit_prior_step03(repo)
        else:
            run_dir = Path(args.run_dir).resolve()
            if args.command == "prepare":
                evaluate_prepare(repo, run_dir)
            elif args.command == "reviewed-precheck":
                evaluate_reviewed_precheck(repo, run_dir)
            elif args.command == "finalize":
                finalize(repo, run_dir)
            else:
                audit(repo, run_dir)
    except EvidenceError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
