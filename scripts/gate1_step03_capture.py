#!/usr/bin/env python3
"""Validate raw adapter output in memory and emit sanitized Step 1.03 evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


TARGET_SHA256 = "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728"
ARTICLE_SOURCE_SHA256 = "f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17"
PLUGIN_CLASSES = {
    "discover_targets": "Drupal\\agentic_harness_drupal_ai\\Plugin\\AiFunctionCall\\DiscoverTargets",
    "get_image_context": "Drupal\\agentic_harness_drupal_ai\\Plugin\\AiFunctionCall\\GetImageContext",
    "submit_recommendation": "Drupal\\agentic_harness_drupal_ai\\Plugin\\AiFunctionCall\\SubmitRecommendation",
    "get_recommendation_status": "Drupal\\agentic_harness_drupal_ai\\Plugin\\AiFunctionCall\\GetRecommendationStatus",
}


class CaptureError(RuntimeError):
    pass


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validators(repo: Path) -> tuple[Draft202012Validator, Draft202012Validator, Draft202012Validator]:
    schema_dir = repo / "shared/schemas"
    schemas = {
        name: load(schema_dir / name)
        for name in (
            "target.schema.json",
            "image-context.schema.json",
            "recommendation.schema.json",
            "tool-result.schema.json",
        )
    }
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()
    )
    checker = FormatChecker()
    return (
        Draft202012Validator(schemas["tool-result.schema.json"], registry=registry, format_checker=checker),
        Draft202012Validator(schemas["image-context.schema.json"], registry=registry, format_checker=checker),
        Draft202012Validator(schemas["recommendation.schema.json"], registry=registry, format_checker=checker),
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CaptureError(message)


def validate_envelope(validator: Draft202012Validator, envelope: Any, label: str) -> None:
    errors = sorted(validator.iter_errors(envelope), key=lambda item: list(item.path))
    if errors:
        raise CaptureError(f"Shared tool-result validation failed for {label}")


def validate_instance(validator: Draft202012Validator, instance: Any, label: str) -> None:
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
    if errors:
        raise CaptureError(f"Shared schema validation failed for {label}")


def input_property(raw: dict[str, Any], plugin_id: str, name: str, expected_type: str) -> dict[str, Any]:
    params = raw["normalized_inputs"].get(plugin_id)
    require(isinstance(params, dict), f"Missing normalized parameters for {plugin_id}")
    require(params.get("type") == "object", f"Unexpected outer parameter type for {plugin_id}")
    require(params.get("required") == [name], f"Unexpected required input for {plugin_id}")
    properties = params.get("properties", {})
    require(list(properties) == [name], f"Unexpected input inventory for {plugin_id}")
    prop = properties[name]
    require(prop.get("type") == expected_type, f"Unexpected input type for {plugin_id}")
    return prop


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    try:
        raw = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        raise CaptureError("Direct exercise did not emit one JSON object") from exc

    tool_validator, context_validator, recommendation_validator = validators(repo)
    require(raw.get("status") == "pass", "Direct exercise did not pass")
    require(
        raw.get("plugin_manager") == "Drupal\\ai\\Service\\FunctionCalling\\FunctionCallPluginManager",
        "Unexpected FunctionCall plugin manager",
    )
    require(set(raw.get("discovery", {})) == set(PLUGIN_CLASSES), "Exact plugin ID inventory was not discovered")
    for plugin_id, class_name in PLUGIN_CLASSES.items():
        proof = raw["discovery"][plugin_id]
        require(proof.get("definition_class") == class_name, f"Definition class mismatch: {plugin_id}")
        require(proof.get("instance_class") == class_name, f"Container instance mismatch: {plugin_id}")
        require(proof.get("function_name") == plugin_id, f"Function name mismatch: {plugin_id}")
        require(proof.get("group") == plugin_id, f"Installed ID/group compatibility mismatch: {plugin_id}")

    require(raw["normalized_inputs"].get("discover_targets") is None, "Discovery accepted business input")
    input_property(raw, "get_image_context", "target", "object")
    input_property(raw, "submit_recommendation", "recommendation", "object")
    status_input = input_property(raw, "get_recommendation_status", "recommendation_id", "string")
    require(bool(status_input.get("pattern")), "Status identifier pattern was not normalized")

    expected_services = {
        "discover_targets": "Drupal\\agentic_harness_tools\\Service\\ImageReviewFinder",
        "get_image_context": "Drupal\\agentic_harness_tools\\Service\\ImageContextProvider",
        "submit_recommendation": "Drupal\\agentic_harness_tools\\Service\\RecommendationSubmitter",
        "get_recommendation_status": "Drupal\\agentic_harness_tools\\Service\\RecommendationStatusProvider",
    }
    require(raw.get("delegation_services") == expected_services, "Direct shared-service delegation map drifted")
    require(raw.get("accounts", {}).get("success_account") == "agent_bot", "Successful account was not agent_bot")
    require(raw.get("accounts", {}).get("administrative_account_substituted") is False, "Administrative account was substituted")

    operations = raw.get("operations", {})
    for label, envelope in operations.items():
        validate_envelope(tool_validator, envelope, label)
        require(envelope.get("ok") is True, f"Successful operation failed: {label}")

    discover = operations["discover_targets"]
    targets = discover["data"]["targets"]
    require(len(targets) == 12 and discover["data"]["total_count"] == 12, "Discovery cardinality drifted")
    require(targets[0]["sequence"] == 1, "Canonical sequence 1 drifted")
    require(canonical_hash(targets) == TARGET_SHA256, "Frozen target order hash drifted")

    context_envelope = operations["get_image_context"]
    context = context_envelope["data"]
    validate_instance(context_validator, context, "image context")
    require("context" not in context, "ADR-0005 direct context data shape was not preserved")
    representation = context["image"]["representation"]
    require(representation["kind"] == "data_url", "Unexpected image representation kind")
    require(representation["value"].startswith("data:image/"), "Runtime representation is not an image data URL")

    recommendation = raw.get("fixture_recommendation")
    validate_instance(recommendation_validator, recommendation, "fixture recommendation")
    require(recommendation["source_framework"] == "drupal_ai", "Fixture origin drifted")
    submission = operations["submit_recommendation"]["data"]
    replay = operations["submit_recommendation_replay"]["data"]
    require(submission == replay, "Idempotent replay returned a different persisted identity")
    require(submission["status"] == "pending", "Submission did not create pending recommendation")
    status = operations["get_recommendation_status"]["data"]
    require(status["uuid"] == submission["uuid"] and status["status"] == "pending", "Status adapter did not read pending identity")

    denials = raw.get("permission_denials", {})
    require(set(denials) == {"anonymous", "editor_dana"}, "Permission account inventory drifted")
    for account, account_results in denials.items():
        require(set(account_results) == set(PLUGIN_CLASSES), f"Incomplete permission proof for {account}")
        for plugin_id, envelope in account_results.items():
            validate_envelope(tool_validator, envelope, f"permission:{account}:{plugin_id}")
            require(envelope.get("ok") is False, f"Permission denial succeeded: {account}:{plugin_id}")
            require(envelope["error"]["code"] == "ACCESS_DENIED", f"Wrong permission error: {account}:{plugin_id}")

    expected_negative_codes = {
        "malformed_target": "INVALID_TARGET",
        "stale_target_identity": "TARGET_STALE",
        "unexpected_target_property": "INVALID_TARGET",
        "malformed_recommendation": "INVALID_RECOMMENDATION",
        "unexpected_recommendation_property": "INVALID_RECOMMENDATION",
        "invalid_status_identifier": "INVALID_RECOMMENDATION_ID",
    }
    negative = raw.get("negative_controls", {})
    require(set(negative) == set(expected_negative_codes), "Negative control inventory drifted")
    for label, expected_code in expected_negative_codes.items():
        envelope = negative[label]
        validate_envelope(tool_validator, envelope, f"negative:{label}")
        require(envelope.get("ok") is False, f"Negative control succeeded: {label}")
        require(envelope["error"]["code"] == expected_code, f"Wrong negative code: {label}")

    unknown = raw.get("unknown_exception", {})
    unknown_envelope = unknown.get("envelope")
    validate_envelope(tool_validator, unknown_envelope, "unknown_exception")
    require(unknown_envelope["error"]["code"] == "CONTEXT_FAILED", "Unknown exception did not fail closed")
    require(unknown.get("marker_exposed") is False, "Unknown exception detail escaped into envelope")
    require(unknown.get("marker") not in json.dumps(unknown_envelope), "Unknown exception marker was exposed")

    before = raw.get("state_before_submission", {})
    after = raw.get("state_after_submission", {})
    require(before.get("article_count") == 20 and after.get("article_count") == 20, "Article count changed")
    require(before.get("suggestion_count") == 0 and after.get("suggestion_count") == 1, "Fixture recommendation count was not exactly one")
    require(before.get("article_source_sha256") == ARTICLE_SOURCE_SHA256, "Predecessor-compatible Article-source hash drifted")
    require(after.get("article_source_sha256") == ARTICLE_SOURCE_SHA256, "Post-submission predecessor Article-source hash drifted")
    reconciliation = before.get("article_source_hash_reconciliation", {})
    require(reconciliation.get("classification") == "hash_definition_drift_only", "Hash reconciliation classification drifted")
    require(reconciliation.get("actual_source_drift") is False, "Hash reconciliation reports source drift")
    require(reconciliation.get("predecessor_step02", {}).get("sha256") == ARTICLE_SOURCE_SHA256, "Step 1.02 hash definition was not controlling")
    for key in (
        "target_count",
        "target_sequence_sha256",
        "canonical_target_sequence",
        "article_source_sha256",
        "step03_extended_article_source_sha256",
        "gate05_certification_article_source_sha256",
        "article_source_hash_reconciliation",
    ):
        require(before.get(key) == after.get(key), f"Source state changed during submission: {key}")
    require(raw.get("provider_pre_request_events_observed") == 0, "Provider request event was observed")
    require(raw.get("agent_request_events_observed") == 0, "AI Agent request event was observed")
    for key in ("model_call_performed", "network_call_performed", "api_credit_used", "runtime_state_storage_opened", "ai_agent_configuration_created"):
        require(raw.get(key) is False, f"Excluded execution occurred: {key}")

    sanitized_context = copy.deepcopy(context)
    raw_value = sanitized_context["image"]["representation"].pop("value")
    sanitized_context["image"]["representation"].update({
        "value_retained": False,
        "value_sha256": hashlib.sha256(raw_value.encode("utf-8")).hexdigest(),
    })
    sanitized = {
        "schema_version": 1,
        "status": "pass",
        "plugin_manager": raw["plugin_manager"],
        "plugin_discovery": raw["discovery"],
        "normalized_inputs": raw["normalized_inputs"],
        "delegation_services": raw["delegation_services"],
        "accounts": raw["accounts"],
        "discover_targets": discover,
        "get_image_context": {
            "tool_result_schema_valid": True,
            "image_context_schema_valid": True,
            "direct_data_shape": True,
            "sanitized_data": sanitized_context,
            "raw_representation_retained": False,
        },
        "fixture_recommendation": recommendation,
        "submission": operations["submit_recommendation"],
        "idempotent_replay": operations["submit_recommendation_replay"],
        "status_observation": operations["get_recommendation_status"],
        "permission_denials": denials,
        "negative_controls": negative,
        "unknown_exception": {
            "envelope": unknown_envelope,
            "detail_marker_exposed": False,
        },
        "state_before_submission": before,
        "state_after_submission": after,
        "target_sequence_sha256": TARGET_SHA256,
        "source_article_unchanged": True,
        "recommendation_count_during_fixture": 1,
        "provider_pre_request_events_observed": 0,
        "agent_request_events_observed": 0,
        "model_call_performed": False,
        "network_call_performed": False,
        "api_credit_used": False,
        "runtime_state_storage_opened": False,
        "ai_agent_configuration_created": False,
        "raw_image_retained": False,
        "secret_retained": False,
    }
    encoded = json.dumps(sanitized, indent=2, sort_keys=True) + "\n"
    require("data:image/" not in encoded, "Raw data URL survived sanitization")
    require(unknown.get("marker") not in encoded, "Unknown exception marker survived sanitization")
    sys.stdout.write(encoded)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CaptureError as exc:
        raise SystemExit(f"[ERROR] {exc}") from exc
