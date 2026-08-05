#!/usr/bin/env python3
"""Evaluate and audit Gate 0.5 Step 03 submission evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

PACKAGE_VERSION = "1.0.2"
IMPLEMENTATION_FILES = [
    "drupal/web/modules/custom/agentic_harness_tools/agentic_harness_tools.routing.yml",
    "drupal/web/modules/custom/agentic_harness_tools/agentic_harness_tools.services.yml",
    "drupal/web/modules/custom/agentic_harness_tools/src/Controller/ToolController.php",
    "drupal/web/modules/custom/agentic_harness_tools/src/Exception/RecommendationSubmissionException.php",
    "drupal/web/modules/custom/agentic_harness_tools/src/Service/RecommendationValidator.php",
    "drupal/web/modules/custom/agentic_harness_tools/src/Service/RecommendationSubmitter.php",
    "drupal/scripts/gate05-step03.php",
    "shared/drupal_client/client.py",
    "shared/drupal_client/README.md",
    "shared/schemas/target.schema.json",
    "shared/schemas/recommendation.schema.json",
    "shared/schemas/tool-result.schema.json",
]

EXPECTED_STATUSES = {
    "positive": 200,
    "replay": 200,
    "editor": 403,
    "malformed_json": 400,
    "invalid_recommendation": 422,
    "stale_revision": 409,
    "stale_file": 409,
    "run_id_mismatch": 422,
    "unsupported_source": 422,
    "empty_alt": 422,
    "too_long": 422,
    "preamble": 422,
    "generic": 422,
    "filename_echo": 422,
    "duplicate_current_alt": 422,
    "idempotency_conflict": 409,
}

EXPECTED_CODES = {
    "malformed-json.json": "MALFORMED_JSON",
    "invalid-recommendation.json": "INVALID_RECOMMENDATION",
    "stale-revision.json": "TARGET_STALE",
    "stale-file.json": "TARGET_STALE",
    "run-id-mismatch.json": "RUN_ID_MISMATCH",
    "unsupported-source.json": "INVALID_SOURCE_FRAMEWORK",
    "empty-alt.json": "ALT_TEXT_EMPTY",
    "too-long.json": "ALT_TEXT_TOO_LONG",
    "preamble.json": "ALT_TEXT_PREAMBLE",
    "generic.json": "ALT_TEXT_GENERIC",
    "filename-echo.json": "ALT_TEXT_FILENAME_ECHO",
    "duplicate-current-alt.json": "ALT_TEXT_DUPLICATE",
    "idempotency-conflict.json": "IDEMPOTENCY_CONFLICT",
}


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


def validate_target(target: Any) -> dict[str, Any]:
    required = {
        "schema_version", "sequence", "node_uuid", "revision_id", "field_name",
        "delta", "file_uuid", "target_state", "existing_alt",
    }
    if not isinstance(target, dict) or set(target) != required:
        raise EvidenceError("Target does not match target.schema.json keys.")
    return target


def validate_success_envelope(
    envelope: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    required_envelope = {
        "schema_version", "tool_name", "ok", "timestamp",
        "correlation_id", "data", "error",
    }
    if not isinstance(envelope, dict) or set(envelope) != required_envelope:
        raise EvidenceError("Submission response envelope keys are invalid.")
    if (
        envelope["schema_version"] != 1
        or envelope["tool_name"] != "submit_recommendation"
        or envelope["ok"] is not True
        or envelope["error"] is not None
    ):
        raise EvidenceError("Submission response is not a successful tool envelope.")

    data = envelope["data"]
    required_data = {
        "node_id", "uuid", "revision_id", "status",
        "source_framework", "run_id", "target",
    }
    if not isinstance(data, dict) or set(data) != required_data:
        raise EvidenceError("Submission result does not match tool-result.schema.json.")
    if not isinstance(data["node_id"], int) or data["node_id"] < 1:
        raise EvidenceError("Submission result node_id is invalid.")
    if not isinstance(data["revision_id"], int) or data["revision_id"] < 1:
        raise EvidenceError("Submission result revision_id is invalid.")
    if data["status"] != "pending":
        raise EvidenceError("Submission result is not pending.")
    if data["source_framework"] != payload["source_framework"]:
        raise EvidenceError("Submission source framework differs from payload.")
    if data["run_id"] != payload["run_id"]:
        raise EvidenceError("Submission run ID differs from payload.")
    if validate_target(data["target"]) != payload["target"]:
        raise EvidenceError("Submission target differs from payload.")
    if not isinstance(data["uuid"], str) or not re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
        r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}",
        data["uuid"],
    ):
        raise EvidenceError("Submission result UUID is invalid.")
    return data


def error_code(path: Path) -> str:
    value = load_json(path)
    if not isinstance(value, dict):
        raise EvidenceError(f"Negative response is not an object: {path.name}")
    error = value.get("error")
    if not isinstance(error, dict):
        raise EvidenceError(f"Negative response lacks error data: {path.name}")
    return str(error.get("code", ""))


def implementation_hashes(repo: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative in IMPLEMENTATION_FILES:
        path = repo / relative
        if not path.is_file():
            raise EvidenceError(f"Missing implementation file: {relative}")
        hashes[relative] = sha256_bytes(path.read_bytes())
    return hashes


def assert_clean_source(before: dict[str, Any], after: dict[str, Any], final: dict[str, Any]) -> None:
    required = {
        "article_count",
        "article_source_sha256",
        "suggestion_count",
        "combined_state_sha256",
    }
    for label, value in (("before", before), ("after", after), ("final", final)):
        if not isinstance(value, dict) or not required.issubset(value):
            raise EvidenceError(
                f"Step 03 {label} snapshot lacks the Article-only evidence fields."
            )
        if value.get("article_count") != 20:
            raise EvidenceError(
                f"Step 03 {label} snapshot does not contain exactly 20 Articles."
            )

    article_hash = before["article_source_sha256"]
    if (
        article_hash != after["article_source_sha256"]
        or article_hash != final["article_source_sha256"]
    ):
        raise EvidenceError("Article-only source hash changed during submission testing.")

    if before["suggestion_count"] != 0:
        raise EvidenceError("Step 03 did not start from zero suggestions.")
    if after["suggestion_count"] != 1:
        raise EvidenceError("Step 03 did not create exactly one transient suggestion.")
    if final["suggestion_count"] != 0:
        raise EvidenceError("Step 03 final reset did not restore zero suggestions.")

    if before["combined_state_sha256"] == after["combined_state_sha256"]:
        raise EvidenceError(
            "Combined state hash did not reflect the expected transient queue mutation."
        )
    if before["combined_state_sha256"] != final["combined_state_sha256"]:
        raise EvidenceError(
            "Final reset did not restore the original combined Article-and-queue state."
        )


def scan_retained_evidence(run_dir: Path) -> None:
    secret_patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
        re.compile(r"(?i)authorization\s*:\s*(?:bearer|basic)\s+(?!<redacted>)\S+"),
        re.compile(r"(?i)(?:password|OPENAI_API_KEY)\s*[=:]\s*(?!<redacted>)\S+"),
        re.compile(r"(?i)user\s*=\s*[\"'][^\"']+:[^\"']+[\"']"),
    ]
    for path in run_dir.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in secret_patterns:
            if pattern.search(text):
                raise EvidenceError(f"Potential credential retained in evidence: {path.name}")



def audit_prior_step02(repo: Path) -> None:
    step01_pointer = (
        repo / "evidence/gates/gate-0.5/baseline/GATE05-STEP01-LATEST.txt"
    )
    step02_pointer = (
        repo / "evidence/gates/gate-0.5/image-context/GATE05-STEP02-LATEST.txt"
    )
    if not step01_pointer.is_file() or not step02_pointer.is_file():
        raise EvidenceError("Passing Step 01 or Step 02 pointer is missing.")

    step01_rel = step01_pointer.read_text(encoding="utf-8").strip()
    step02_rel = step02_pointer.read_text(encoding="utf-8").strip()
    if not re.fullmatch(
        r"evidence/gates/gate-0\.5/baseline/gate05-step01-[A-Za-z0-9._-]+",
        step01_rel,
    ):
        raise EvidenceError("Unexpected Step 01 evidence pointer.")
    if not re.fullmatch(
        r"evidence/gates/gate-0\.5/image-context/gate05-step02-[A-Za-z0-9._-]+",
        step02_rel,
    ):
        raise EvidenceError("Unexpected Step 02 evidence pointer.")

    step01_dir = repo / step01_rel
    step02_dir = repo / step02_rel
    required = [
        "summary.json",
        "summary.md",
        "canonical-target.json",
        "response-sanitized.json",
        "hash-payload.json",
        "http-statuses.json",
        "authorization.json",
        "environment.json",
        "source-before.json",
        "source-after.json",
        "malformed-json.json",
        "invalid-target.json",
        "stale-revision.json",
        "stale-file.json",
        "implementation-sha256.txt",
        "setup.log",
        "positive-client.log",
        "repeat-client.log",
    ]
    for filename in required:
        if not (step02_dir / filename).is_file():
            raise EvidenceError(
                f"Missing retained Step 02 evidence: {filename}"
            )

    step01_target = load_json(step01_dir / "canonical-target.json")
    summary = load_json(step02_dir / "summary.json")
    if (
        not isinstance(summary, dict)
        or summary.get("status") != "pass"
        or summary.get("operation") != "get_image_context"
    ):
        raise EvidenceError("Retained Step 02 summary is not a passing context run.")
    if summary.get("canonical_target") != step01_target:
        raise EvidenceError(
            "Retained Step 02 target differs from the Step 01 canonical target."
        )
    if step01_target.get("sequence") != 1:
        raise EvidenceError("The retained canonical target is not sequence 1.")

    context_hash = summary.get("context_evidence_hash")
    image_hash = summary.get("image_sha256")
    if not isinstance(context_hash, str) or not re.fullmatch(
        r"sha256:[a-f0-9]{64}",
        context_hash,
    ):
        raise EvidenceError("Retained Step 02 context evidence hash is invalid.")
    if not isinstance(image_hash, str) or not re.fullmatch(
        r"[a-f0-9]{64}",
        image_hash,
    ):
        raise EvidenceError("Retained Step 02 image hash is invalid.")

    hash_payload = load_json(step02_dir / "hash-payload.json")
    recomputed = "sha256:" + sha256_bytes(
        json.dumps(
            hash_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    if recomputed != context_hash:
        raise EvidenceError("Retained Step 02 evidence hash does not recompute.")

    sanitized = load_json(step02_dir / "response-sanitized.json")
    try:
        envelope = sanitized["envelope"]
        retention = sanitized["retention"]
        representation = envelope["data"]["image"]["representation"]
    except (KeyError, TypeError) as exc:
        raise EvidenceError("Retained Step 02 sanitized response is incomplete.") from exc

    if (
        envelope.get("tool_name") != "get_image_context"
        or envelope.get("ok") is not True
        or envelope.get("data", {}).get("evidence_hash") != context_hash
        or envelope.get("data", {}).get("image", {}).get("sha256") != image_hash
        or representation.get("kind") != "data_url"
        or representation.get("value") != "<runtime-only-data-url>"
        or retention.get("representation_value_retained") is not False
        or retention.get("raw_image_bytes_retained") is not False
    ):
        raise EvidenceError("Retained Step 02 sanitized response controls failed.")

    retained_text = (step02_dir / "response-sanitized.json").read_text(
        encoding="utf-8",
        errors="replace",
    )
    if "data:image/" in retained_text and ";base64," in retained_text:
        raise EvidenceError("Retained Step 02 evidence contains a raw data URL.")
    if re.search(r"sk-[A-Za-z0-9_-]{8,}", retained_text):
        raise EvidenceError("Retained Step 02 evidence contains a possible API key.")

    statuses = load_json(step02_dir / "http-statuses.json")
    expected_statuses = {
        "positive": 200,
        "repeat": 200,
        "editor": 403,
        "malformed_json": 400,
        "invalid_target": 422,
        "stale_revision": 409,
        "stale_file": 409,
    }
    for key, expected in expected_statuses.items():
        if statuses.get(key) != expected:
            raise EvidenceError(
                f"Retained Step 02 HTTP control failed for {key}."
            )
    if statuses.get("anonymous") not in {401, 403}:
        raise EvidenceError("Retained Step 02 anonymous denial is missing.")

    before = load_json(step02_dir / "source-before.json")
    after = load_json(step02_dir / "source-after.json")
    if (
        before.get("source_sha256") != after.get("source_sha256")
        or before.get("suggestion_count") != 0
        or after.get("suggestion_count") != 0
    ):
        raise EvidenceError("Retained Step 02 source-mutation control failed.")

    environment = load_json(step02_dir / "environment.json")
    for key in (
        "openai_api_key_present",
        "openai_candidate_model_present",
        "crewai_candidate_model_present",
        "model_call_performed",
    ):
        if environment.get(key) is not False:
            raise EvidenceError(
                f"Retained Step 02 model-free control failed: {key}"
            )

    print(json.dumps({
        "status": "pass",
        "step01_run_id": step01_dir.name,
        "step02_run_id": step02_dir.name,
        "operation": "get_image_context",
        "canonical_target_sequence": 1,
        "context_evidence_hash": context_hash,
        "image_sha256": image_hash,
        "retained_evidence_integrity": True,
        "raw_image_retained": False,
        "historical_implementation_hashes_used_as_current_gate": False,
    }, indent=2, sort_keys=True))

def evaluate(repo: Path, run_dir: Path) -> None:
    payload = load_json(run_dir / "submission-request.json")
    if not isinstance(payload, dict):
        raise EvidenceError("Submission request is not an object.")
    target = validate_target(payload.get("target"))
    if target.get("sequence") != 1:
        raise EvidenceError("Step 03 positive submission did not use canonical target 1.")
    if payload.get("source_framework") != "drupal_ai":
        raise EvidenceError("Controlled preflight source must exercise the drupal_ai enum branch.")
    if payload.get("validator_version") != "gate05-validator-1.0.0":
        raise EvidenceError("Unexpected validator version.")

    positive = load_json(run_dir / "submit-response.json")
    replay = load_json(run_dir / "submit-replay-response.json")
    positive_data = validate_success_envelope(positive, payload)
    replay_data = validate_success_envelope(replay, payload)
    if replay_data != positive_data:
        raise EvidenceError("Idempotent replay did not return the same recommendation identity.")

    statuses = load_json(run_dir / "http-statuses.json")
    if not isinstance(statuses, dict):
        raise EvidenceError("HTTP status evidence is not an object.")
    for key, expected in EXPECTED_STATUSES.items():
        if statuses.get(key) != expected:
            raise EvidenceError(
                f"Unexpected HTTP status for {key}: expected {expected}, got {statuses.get(key)}."
            )
    if statuses.get("anonymous") not in {401, 403}:
        raise EvidenceError("Anonymous submission was not denied.")

    for filename, expected in EXPECTED_CODES.items():
        actual = error_code(run_dir / filename)
        if actual != expected:
            raise EvidenceError(
                f"Unexpected error code in {filename}: expected {expected}, got {actual}."
            )

    inspection = load_json(run_dir / "recommendation-inspection.json")
    if not isinstance(inspection, dict):
        raise EvidenceError("Recommendation inspection is not an object.")
    expected_revision_log = (
        f"submit_recommendation validator={payload['validator_version']} "
        f"evidence={payload['evidence_hash']}"
    )
    required_inspection = {
        "node_id": positive_data["node_id"],
        "uuid": positive_data["uuid"],
        "revision_id": positive_data["revision_id"],
        "published": False,
        "owner_username": "agent_bot",
        "review_status": "pending",
        "source_framework": payload["source_framework"],
        "run_id": payload["run_id"],
        "evidence_hash": payload["evidence_hash"],
        "proposed_alt_text": payload["proposed_alt_text"],
        "revision_log": expected_revision_log,
        "identity_count": 1,
        "total_suggestion_count": 1,
    }
    for key, expected in required_inspection.items():
        if inspection.get(key) != expected:
            raise EvidenceError(
                f"Recommendation inspection mismatch for {key}: "
                f"expected {expected!r}, got {inspection.get(key)!r}."
            )

    inspected_target = inspection.get("target")
    if not isinstance(inspected_target, dict):
        raise EvidenceError("Inspection target is missing.")
    for key in ("node_uuid", "revision_id", "field_name", "delta", "file_uuid"):
        if inspected_target.get(key) != payload["target"].get(key):
            raise EvidenceError(f"Inspection target mismatch for {key}.")

    before = load_json(run_dir / "source-before.json")
    after = load_json(run_dir / "source-after.json")
    final = load_json(run_dir / "source-final-clean.json")
    assert_clean_source(before, after, final)

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
    if environment.get("controlled_preflight") is not True:
        raise EvidenceError("Step 03 is not labeled as a controlled preflight.")

    hashes = implementation_hashes(repo)
    (run_dir / "implementation-sha256.txt").write_text(
        "".join(f"{digest}  {relative}\n" for relative, digest in hashes.items()),
        encoding="utf-8",
    )

    scan_retained_evidence(run_dir)

    step01 = (repo / "evidence/gates/gate-0.5/baseline/GATE05-STEP01-LATEST.txt").read_text(
        encoding="utf-8"
    ).strip()
    step02 = (repo / "evidence/gates/gate-0.5/image-context/GATE05-STEP02-LATEST.txt").read_text(
        encoding="utf-8"
    ).strip()

    summary = {
        "schema_version": 1,
        "package": "gate-0.5-step03-submit-recommendation",
        "package_version": PACKAGE_VERSION,
        "run_id": run_dir.name,
        "status": "pass",
        "operation": "submit_recommendation",
        "prior_evidence": {
            "step01": step01,
            "step02": step02,
        },
        "controlled_preflight": True,
        "framework_execution_claimed": False,
        "model_call_performed": False,
        "canonical_target_sequence": 1,
        "transient_recommendation": positive_data,
        "idempotent_replay_same_identity": True,
        "source_article_unchanged": True,
        "article_source_sha256": before["article_source_sha256"],
        "combined_state_changed_during_transient_submission": True,
        "combined_state_restored_after_reset": True,
        "transient_suggestion_count": 1,
        "final_suggestion_count": 0,
        "final_reset_clean": True,
        "implementation_files": hashes,
        "http_statuses": statuses,
        "next_step": "Gate 0.5 Step 04 — get_recommendation_status and human decision preflight",
    }
    write_json(run_dir / "summary.json", summary)

    (run_dir / "summary.md").write_text(
        f"""# Gate 0.5 Step 03 Submit Recommendation Summary

- **Status:** PASS
- **Run ID:** `{run_dir.name}`
- **Operation:** `submit_recommendation(recommendation)`
- **Canonical target:** sequence 1
- **Transient recommendation node:** `{positive_data['node_id']}`
- **Transient recommendation UUID:** `{positive_data['uuid']}`
- **Review status:** `pending`
- **Idempotent replay:** same node and revision
- **Transient queue count:** 1
- **Final queue count after reset:** 0
- **Source Article changed:** no
- **Model call performed:** no
- **Framework execution claimed:** no
- **Controlled preflight:** yes

The preflight exercises the frozen `drupal_ai` provenance enum branch because
`recommendation.schema.json` intentionally excludes test-only origins. It is not evidence that the
Drupal AI harness generated this recommendation.

## Negative controls

- anonymous denied
- `editor_dana` denied
- malformed recommendation rejected
- stale revision and changed file rejected
- source/run mismatch rejected
- unsupported source rejected
- empty, overlong, preamble, generic, filename-echo, and duplicate-current-alt text rejected
- same idempotency identity with different payload rejected

## Next step

Gate 0.5 Step 04 adds `get_recommendation_status()` and proves one explicit human review decision.
""",
        encoding="utf-8",
    )


def audit(repo: Path, run_dir: Path) -> None:
    summary = load_json(run_dir / "summary.json")
    if not isinstance(summary, dict) or summary.get("status") != "pass":
        raise EvidenceError("Latest Step 03 summary is not passing.")
    if summary.get("controlled_preflight") is not True:
        raise EvidenceError("Latest Step 03 run lacks the controlled-preflight label.")
    if summary.get("framework_execution_claimed") is not False:
        raise EvidenceError("Latest Step 03 run overclaims framework execution.")
    if summary.get("final_reset_clean") is not True:
        raise EvidenceError("Latest Step 03 run did not restore clean state.")

    required = [
        "summary.json", "summary.md", "submission-request.json",
        "submit-response.json", "submit-replay-response.json",
        "recommendation-inspection.json", "http-statuses.json",
        "environment.json", "authorization.json",
        "source-before.json", "source-after.json", "source-final-clean.json",
        "malformed-json.json", "invalid-recommendation.json",
        "stale-revision.json", "stale-file.json", "run-id-mismatch.json",
        "unsupported-source.json", "empty-alt.json", "too-long.json",
        "preamble.json", "generic.json", "filename-echo.json",
        "duplicate-current-alt.json", "idempotency-conflict.json",
        "implementation-sha256.txt", "setup.log", "reset-before.log",
        "reset-after.log", "positive-client.log", "replay-client.log",
    ]
    for filename in required:
        if not (run_dir / filename).is_file():
            raise EvidenceError(f"Missing retained Step 03 evidence: {filename}")

    current_hashes = implementation_hashes(repo)
    if current_hashes != summary.get("implementation_files"):
        raise EvidenceError("Step 03 implementation files changed after the passing run.")

    before = load_json(run_dir / "source-before.json")
    after = load_json(run_dir / "source-after.json")
    final = load_json(run_dir / "source-final-clean.json")
    assert_clean_source(before, after, final)
    scan_retained_evidence(run_dir)

    print(json.dumps({
        "status": "pass",
        "run_id": run_dir.name,
        "operation": "submit_recommendation",
        "canonical_target_sequence": summary.get("canonical_target_sequence"),
        "transient_recommendation_node_id": summary.get(
            "transient_recommendation", {}
        ).get("node_id"),
        "idempotent_replay_same_identity": True,
        "source_article_unchanged": True,
        "article_source_sha256": summary.get("article_source_sha256"),
        "combined_state_restored_after_reset": True,
        "final_suggestion_count": 0,
        "controlled_preflight": True,
        "framework_execution_claimed": False,
        "implementation_hashes_match": True,
        "next_step": summary.get("next_step"),
    }, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    evaluate_parser = sub.add_parser("evaluate")
    evaluate_parser.add_argument("--repo", required=True)
    evaluate_parser.add_argument("--run-dir", required=True)

    audit_parser = sub.add_parser("audit")
    audit_parser.add_argument("--repo", required=True)
    audit_parser.add_argument("--run-dir", required=True)

    prior_parser = sub.add_parser("audit-prior-step02")
    prior_parser.add_argument("--repo", required=True)

    args = parser.parse_args()
    try:
        if args.command == "evaluate":
            evaluate(Path(args.repo).resolve(), Path(args.run_dir).resolve())
        elif args.command == "audit":
            audit(Path(args.repo).resolve(), Path(args.run_dir).resolve())
        else:
            audit_prior_step02(Path(args.repo).resolve())
    except EvidenceError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
