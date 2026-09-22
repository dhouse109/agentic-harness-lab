#!/usr/bin/env python3
"""Disposable model-free policy rehearsal for Gate 2C Step 2C.01."""
from __future__ import annotations

import argparse
import copy
import json
import tempfile
from pathlib import Path

import jsonschema

from gate2c_step01_audit import (
    CREATES,
    SOURCE_CONFIG_PRIVACY_PATTERNS,
    STRICT_RETAINED_PRIVACY_PATTERNS,
    UPDATES,
    privacy_pattern_labels,
    require_privacy_clean,
    scan_managed_source_and_config,
    scan_retained_artifacts,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def classify(case: dict) -> str:
    if not case["frozen_constants"]:
        return "INVALID_FROZEN_CONSTANT_DRIFT"
    if not case["seam_valid"]:
        return "INVALID_SEAM"
    if not case["actual_worker_sigkill"]:
        return "INVALID_SUPERVISOR_OR_INJECTOR"
    if case["runner_defect"]:
        return "INVALID_RUNNER"
    if case["environment_defect"]:
        return "INVALID_ENVIRONMENT"
    if case["credential_defect"]:
        return "INVALID_CREDENTIAL"
    if case["gate2c_added_retry_logic"]:
        return "INVALID_RUNNER"
    if case["provider_failure"]:
        return "INVALID_PROVIDER_OR_TRANSPORT"
    if case["unaccounted_retry"]:
        return "INVALID_ACCOUNTING"
    if case["privacy_failure"]:
        return "INVALID_EVIDENCE_OR_PRIVACY"
    if case["lock_denied"] and case["framework"] == "drupal_ai":
        return "VALID_OPERATOR_WAIT_OR_ACTION_REQUIRED"
    if not case["same_run"] or case["replay"] or case["duplicate"] or case["first_target"] != 7 or not case["completed"]:
        return "VALID_FRAMEWORK_RECOVERY_FAILURE"
    return "VALID_RECOVERY_SUCCESS"


def expect_privacy_failure(action, message: str) -> None:
    try:
        action()
    except RuntimeError:
        return
    raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--payload", required=True, type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    content_root = args.payload.resolve()
    require(content_root == repo, "installed rehearsal content root must be the governed repository")
    contract = json.loads((content_root / "shared/contracts/GATE2C-SHARED-FAILURE-RECOVERY-CONTRACT.json").read_text())
    base = {
        "framework": "langgraph", "frozen_constants": True, "seam_valid": True,
        "actual_worker_sigkill": True, "runner_defect": False, "environment_defect": False,
        "credential_defect": False, "provider_failure": False,
        "gate2c_added_retry_logic": False, "observed_underlying_retry": 0,
        "unaccounted_retry": False,
        "privacy_failure": False, "lock_denied": False, "same_run": True, "replay": False,
        "duplicate": False, "first_target": 7, "completed": True,
    }
    cases = [
        ("success", {}, "VALID_RECOVERY_SUCCESS"),
        ("wrong_seam", {"seam_valid": False}, "INVALID_SEAM"),
        ("clean_exit", {"actual_worker_sigkill": False}, "INVALID_SUPERVISOR_OR_INJECTOR"),
        ("runner", {"runner_defect": True}, "INVALID_RUNNER"),
        ("environment", {"environment_defect": True}, "INVALID_ENVIRONMENT"),
        ("credential", {"credential_defect": True}, "INVALID_CREDENTIAL"),
        ("provider", {"provider_failure": True}, "INVALID_PROVIDER_OR_TRANSPORT"),
        ("gate2c_retry", {"gate2c_added_retry_logic": True}, "INVALID_RUNNER"),
        ("observed_counted_retry", {"observed_underlying_retry": 1}, "VALID_RECOVERY_SUCCESS"),
        ("unaccounted_retry", {"unaccounted_retry": True}, "INVALID_ACCOUNTING"),
        ("privacy", {"privacy_failure": True}, "INVALID_EVIDENCE_OR_PRIVACY"),
        ("constant_drift", {"frozen_constants": False}, "INVALID_FROZEN_CONSTANT_DRIFT"),
        ("new_run", {"same_run": False}, "VALID_FRAMEWORK_RECOVERY_FAILURE"),
        ("replay", {"replay": True}, "VALID_FRAMEWORK_RECOVERY_FAILURE"),
        ("duplicate", {"duplicate": True}, "VALID_FRAMEWORK_RECOVERY_FAILURE"),
        ("skip_target7", {"first_target": 8}, "VALID_FRAMEWORK_RECOVERY_FAILURE"),
        ("cannot_complete", {"completed": False}, "VALID_FRAMEWORK_RECOVERY_FAILURE"),
        ("drupal_lock", {"framework": "drupal_ai", "lock_denied": True, "completed": False}, "VALID_OPERATOR_WAIT_OR_ACTION_REQUIRED"),
    ]
    with tempfile.TemporaryDirectory(prefix="gate2c-step01-rehearsal-") as raw:
        root = Path(raw)
        for name, updates, expected in cases:
            case = dict(base)
            case.update(updates)
            result = classify(case)
            require(result == expected, f"{name}: {result} != {expected}")
            (root / f"{name}.json").write_text(json.dumps({"input": case, "classification": result}, sort_keys=True))

        # Legitimate detector/test literals are source, not retained evidence.
        detector = root / "privacy_detector_test.py"
        detector.write_text(
            'SENTINELS = ["sk-proj-", "Authorization: Basic ", '
            '"Authorization: Bearer ", "data:image/", "OPENAI_API_KEY="]\n',
            encoding="utf-8",
        )
        require_privacy_clean(detector, SOURCE_CONFIG_PRIVACY_PATTERNS, "source/config")

        # The same sentinel is prohibited when it is retained as evidence data.
        retained_sentinel = root / "retained-sentinel"
        retained_sentinel.mkdir()
        (retained_sentinel / "summary.md").write_text("synthetic leak: sk-proj-\n", encoding="utf-8")
        expect_privacy_failure(
            lambda: scan_retained_artifacts(retained_sentinel),
            "retained-evidence sentinel negative control unexpectedly passed",
        )

        # Synthetic credential/header/data payloads must all classify as prohibited
        # in retained artifacts, without logging or retaining the matched values.
        synthetic_payload = (
            "sk-" + "live-" + "SYNTHETIC00000001\n"
            + "Author" + "ization: Bearer " + "SYNTHETIC_TOKEN_123\n"
            + "data:" + "image/png;base64," + "U1lOVEhFVElDX0RBVEE=\n"
            + "OPENAI_API" + "_KEY=" + "SYNTHETIC_VALUE_123\n"
        )
        labels = set(privacy_pattern_labels(synthetic_payload, STRICT_RETAINED_PRIVACY_PATTERNS))
        require(labels == set(STRICT_RETAINED_PRIVACY_PATTERNS), "retained payload pattern coverage")
        retained_payload = root / "retained-payload"
        retained_payload.mkdir()
        (retained_payload / "generated-output.json").write_text(synthetic_payload, encoding="utf-8")
        expect_privacy_failure(
            lambda: scan_retained_artifacts(retained_payload),
            "retained synthetic payload negative control unexpectedly passed",
        )

        # Payload-aware source/config scanning still rejects realistic values.
        source_payload = root / "gate2c.env"
        source_payload.write_text("OPENAI_API" + "_KEY=" + "SYNTHETIC_VALUE_123\n", encoding="utf-8")
        expect_privacy_failure(
            lambda: require_privacy_clean(source_payload, SOURCE_CONFIG_PRIVACY_PATTERNS, "source/config"),
            "source/config synthetic credential negative control unexpectedly passed",
        )

        # Installed certification owns an explicit durable repository inventory.
        # External delivery-package discovery and recursive repository traversal are
        # both prohibited here; package-payload validation belongs to package tooling.
        managed_relatives = sorted(UPDATES | CREATES)
        managed_paths = [repo / relative for relative in managed_relatives]
        prohibited_parts = {".venv", ".runtime", "__pycache__", "site-packages", "vendor"}
        require(all(path.is_file() for path in managed_paths), "installed managed-source inventory incomplete")
        require(all(path.is_relative_to(repo) for path in managed_paths), "managed source escaped repository")
        require(
            all(not (set(path.relative_to(repo).parts) & prohibited_parts) for path in managed_paths),
            "managed source inventory entered a dependency/runtime tree",
        )
        scan_managed_source_and_config(repo)
    require(contract["lifecycle"]["gate_2c"] == "DEFERRED_UNCLAIMED", "Gate 2C lifecycle")
    require(contract["crewai_recovery_architecture"]["decision_status"] == "PENDING_MODEL_FREE_PROOF_AND_HUMAN_DECISION", "CrewAI decision")
    require(contract["drupal_persistent_lock_policy"]["maximum_authoritative_recovery_invocations"] == 2, "Drupal lock attempts")
    require(contract["model_call_accounting"]["maximum_successful_logical_generations_experiment"] == 36, "model ceiling")
    schemas = content_root / "shared/schemas"
    contract_schema = json.loads((schemas / "gate2c-shared-failure-recovery-contract.schema.json").read_text())
    trial_schema = json.loads((schemas / "gate2c-trial-evidence.schema.json").read_text())
    comparison_schema = json.loads((schemas / "gate2c-comparison-evidence.schema.json").read_text())
    jsonschema.validate(contract, contract_schema)
    bad_contract = copy.deepcopy(contract)
    bad_contract["package_sequence"] = bad_contract["package_sequence"][:3]
    try:
        jsonschema.validate(bad_contract, contract_schema)
        raise RuntimeError("three-package contract negative control unexpectedly passed")
    except jsonschema.ValidationError:
        pass
    digest = "0" * 64
    projection = {"article_count": 20, "target_count": 12, "suggestion_count": 6, "source_projection_sha256": digest}
    trial = {
        "schema_version": 1, "contract_sha256": digest, "framework_origin": "langgraph",
        "trial_id": "gate2c-trial-test", "run_id": "langgraph-test",
        "runtime_identity": {"fresh": True, "framework_owned": True, "historical_runtime_reused": False},
        "predecessor_freeze_sha256": digest,
        "timestamps": {"started": "2026-09-21T00:00:00Z", "seam_ready": "2026-09-21T00:01:00Z", "terminated": "2026-09-21T00:01:01Z", "recovery_authorized": "2026-09-21T00:02:00Z", "completed_or_stopped": "2026-09-21T00:03:00Z"},
        "drupal_state": {"pre_run": dict(projection, suggestion_count=0), "midpoint": projection, "post_recovery": dict(projection, suggestion_count=12), "post_restore": dict(projection, suggestion_count=0)},
        "seam_ready": {"signal_id": "signal-test", "run_id": "langgraph-test", "worker_identity": "sanitized-worker", "target_6_fully_persisted": True, "next_target": 7, "target_7_started": False, "independently_verified": True},
        "termination": {"requested_signal": "SIGKILL", "observed_signal": 9, "actual_worker_terminated": True, "supervisor_only_trigger": True},
        "persisted_midpoint": {"run_id": "langgraph-test", "completed_sequences": [1, 2, 3, 4, 5, 6], "next_target": 7, "recommendation_identities": ["r1", "r2", "r3", "r4", "r5", "r6"], "framework_state_sha256": digest},
        "recovery_attempts": [{"ordinal": 1, "authorization_id": "auth-test", "started": "2026-09-21T00:02:00Z", "result": "completed", "lock_observation": None, "first_framework_target": 7}],
        "call_accounting": {"existing_frozen_retry_configuration_preserved": True, "gate2c_added_retry_loops": 0, "successful_generations_before_failure": 6, "successful_generations_after_recovery": 6, "provider_requests": 13, "provider_responses": 12, "provider_failures": 0, "framework_retries": 0, "sdk_retries": 1, "transport_retries": 0, "provider_retries": 0, "semantic_retries": 0, "repair_or_correction_calls": 0, "generation_retries": 0, "recovery_invocations": 1, "replayed_generations": 0, "unaccounted_retry_events": 0},
        "outcome": {"experiment_validity": "VALID", "classification": "VALID_RECOVERY_SUCCESS", "framework_recovery_succeeded": True, "same_run_id": True, "first_post_restart_target": 7, "replay_count": 0, "duplicate_count": 0, "completed_sequences": list(range(1, 13))},
        "source_nonmutation": {"passed": True, "before_sha256": digest, "after_sha256": digest},
        "privacy": "PASS", "sanitized_errors": []
    }
    jsonschema.validate(trial, trial_schema)
    for field, value in (("gate2c_added_retry_loops", 1), ("unaccounted_retry_events", 1), ("successful_generations_after_recovery", 7)):
        bad = copy.deepcopy(trial)
        bad["call_accounting"][field] = value
        try:
            jsonschema.validate(bad, trial_schema)
            raise RuntimeError(f"trial negative control unexpectedly passed: {field}")
        except jsonschema.ValidationError:
            pass
    comparison = {
        "schema_version": 1, "comparison_id": "comparison-test", "contract_sha256": digest,
        "framework_trials": [
            {"framework_origin": origin, "trial_id": f"{origin}-test", "evidence_path": f"evidence/{origin}", "evidence_sha256": digest, "experiment_validity": "VALID", "classification": "VALID_RECOVERY_SUCCESS"}
            for origin in ("drupal_ai", "langgraph", "crewai")
        ],
        "comparability": {"same_semantic_seam": True, "same_failure_class": True, "frozen_constants_preserved": True, "valid_evidence_count": 3},
        "gate_2c_result": "COMPLETE_COMPARABLE_EVIDENCE",
        "claim_policy": {"winner_claim": False, "production_readiness_claim": False, "framework_superiority_claim": False},
        "restoration": {"authorized": True, "completed": True, "post_restore_audit": "PASS"},
        "privacy": "PASS"
    }
    jsonschema.validate(comparison, comparison_schema)
    bad_comparison = copy.deepcopy(comparison)
    bad_comparison["claim_policy"]["winner_claim"] = True
    try:
        jsonschema.validate(bad_comparison, comparison_schema)
        raise RuntimeError("winner-claim negative control unexpectedly passed")
    except jsonschema.ValidationError:
        pass
    print(f"[PASS] {len(cases)} disposable outcome-classification controls")
    print("[PASS] contract/trial/comparison positive controls and 5 negative schema controls")
    print("[PASS] privacy scope: detector literals allowed in source; retained sentinels and synthetic payloads rejected; governed installed source clean")
    print(f"[PASS] installed location/staging independence: repository-only content root and explicit {len(managed_paths)}-file managed inventory")
    print("[PASS] no virtualenv, dependency/vendor, cache, or local-runtime traversal")
    print("[PASS] frozen retry preservation, counted underlying retry, pending CrewAI decision, Drupal lock policy, model ceiling, and lifecycle guards")
    print("[PASS] zero authoritative evidence, model/provider, Drupal, runtime, injector, or snapshot activity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
