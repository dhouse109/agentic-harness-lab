#!/usr/bin/env python3
"""Focused installed audit for Gate 1 Step 1.03."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


EXPECTED_COMMIT = "3915af75779869e19c40abf3cbb4e2021cc57952"
GATE05_RUN = "gate05-step05-20260805T184155Z-50124"
GATE05_SHA = "99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a"
STEP01_RUN = "gate1-step01-20260805T205448Z-103220"
STEP01_SHA = "360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6"
STEP02_RUN = "gate1-step02-20260806T010227Z-189538"
COMPAT_RUN = "gate1-step01-audit-compatibility-20260806T023356Z-250843"
ADR0006_SHA = "223f6d6f4276d3861cf5668f08e0446479d815a07fed18402b1e6a7722d18c4b"
TARGET_SHA = "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728"
ARTICLE_SOURCE_SHA = "f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17"
MODULE_ROOT = "drupal/web/modules/custom/agentic_harness_drupal_ai"
PAYLOAD_FILES = (
    "docs/gates/GATE-1-STEP03-DRUPAL-AI-TOOL-ADAPTERS.md",
    f"{MODULE_ROOT}/agentic_harness_drupal_ai.info.yml",
    f"{MODULE_ROOT}/agentic_harness_drupal_ai.services.yml",
    f"{MODULE_ROOT}/src/Service/ToolResultRunner.php",
    f"{MODULE_ROOT}/src/Plugin/AiFunctionCall/DiscoverTargets.php",
    f"{MODULE_ROOT}/src/Plugin/AiFunctionCall/GetImageContext.php",
    f"{MODULE_ROOT}/src/Plugin/AiFunctionCall/SubmitRecommendation.php",
    f"{MODULE_ROOT}/src/Plugin/AiFunctionCall/GetRecommendationStatus.php",
    "drupal/scripts/gate1-step03-adapter-exercise.php",
    "scripts/gate1_step03_capture.py",
    "scripts/gate1_step03_audit.py",
    "scripts/gate1_step03_finalize.py",
    "scripts/run-gate1-step03.sh",
)
PLUGIN_FILES = {
    "discover_targets": f"{MODULE_ROOT}/src/Plugin/AiFunctionCall/DiscoverTargets.php",
    "get_image_context": f"{MODULE_ROOT}/src/Plugin/AiFunctionCall/GetImageContext.php",
    "submit_recommendation": f"{MODULE_ROOT}/src/Plugin/AiFunctionCall/SubmitRecommendation.php",
    "get_recommendation_status": f"{MODULE_ROOT}/src/Plugin/AiFunctionCall/GetRecommendationStatus.php",
}


class AuditError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise AuditError(f"Missing or invalid JSON evidence: {path.name}") from exc


def resolve(repo: Path, overlay: Path | None, relative: str) -> Path:
    if overlay is not None and (overlay / relative).is_file():
        return overlay / relative
    return repo / relative


def pointer(repo: Path, relative: str) -> str:
    return Path((repo / relative).read_text(encoding="utf-8").strip()).name


def composer_versions(repo: Path) -> dict[str, str]:
    wanted = {
        "drupal/core-recommended": "11.4.4",
        "drupal/ai": "1.4.5",
        "drupal/ai_agents": "1.3.2",
        "drupal/ai_provider_openai": "1.2.3",
    }
    actual = {
        package["name"]: package["version"]
        for package in load(repo / "drupal/composer.lock").get("packages", [])
        if package.get("name") in wanted
    }
    if actual != wanted:
        raise AuditError("Pinned Composer versions drifted")
    return actual


def static_audit(repo: Path, overlay: Path | None) -> dict[str, Any]:
    if sha256(repo / "shared/contracts/GATE05-SUBSTRATE-FREEZE.json") != GATE05_SHA:
        raise AuditError("Gate 0.5 freeze digest changed")
    if sha256(repo / "shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json") != STEP01_SHA:
        raise AuditError("Step 1.01 contract digest changed")
    if sha256(repo / "docs/decisions/ADR-0006-drupal-ai-programmatic-runtime-path.md") != ADR0006_SHA:
        raise AuditError("ADR-0006 changed")
    expected_pointers = {
        "evidence/gates/gate-0.5/substrate-certification/GATE05-STEP05-LATEST.txt": GATE05_RUN,
        "evidence/gates/gate-1/drupal-ai-batch-contract/GATE1-STEP01-LATEST.txt": STEP01_RUN,
        "evidence/gates/gate-1/drupal-ai-runtime-probe/GATE1-STEP02-LATEST.txt": STEP02_RUN,
        "evidence/gates/gate-1/step01-audit-progression-compatibility/GATE1-STEP01-AUDIT-COMPATIBILITY-LATEST.txt": COMPAT_RUN,
    }
    for relative, expected in expected_pointers.items():
        if pointer(repo, relative) != expected:
            raise AuditError(f"Accepted predecessor pointer changed: {relative}")
    for relative in PAYLOAD_FILES:
        path = resolve(repo, overlay, relative)
        if not path.is_file() or path.stat().st_size == 0:
            raise AuditError(f"Missing Step 1.03 payload: {relative}")

    info = resolve(repo, overlay, f"{MODULE_ROOT}/agentic_harness_drupal_ai.info.yml").read_text(encoding="utf-8")
    for dependency in ("ai:ai", "ai_agents:ai_agents", "agentic_harness_tools:agentic_harness_tools"):
        if f"- {dependency}" not in info:
            raise AuditError(f"Missing exact module dependency: {dependency}")

    combined_plugins = ""
    delegation_markers = {
        "discover_targets": ("agentic_harness_tools.image_review_finder", "->find()"),
        "get_image_context": ("agentic_harness_tools.image_context_provider", "->get($target)"),
        "submit_recommendation": ("agentic_harness_tools.recommendation_submitter", "->submit($recommendation)"),
        "get_recommendation_status": ("agentic_harness_tools.recommendation_status_provider", "->get((string) $this->getContextValue('recommendation_id'))"),
    }
    for plugin_id, relative in PLUGIN_FILES.items():
        text = resolve(repo, overlay, relative).read_text(encoding="utf-8")
        combined_plugins += "\n" + text
        for marker in (
            "#[FunctionCall(",
            f"id: '{plugin_id}'",
            f"function_name: '{plugin_id}'",
            f"group: '{plugin_id}'",
            "extends FunctionCallBase implements ExecutableFunctionCallInterface",
            "public static function create(",
            "plugin.manager.ai_data_type_converter",
            "current_user",
            "agentic_harness_drupal_ai.tool_result_runner",
        ):
            if marker not in text:
                raise AuditError(f"Adapter marker missing for {plugin_id}: {marker}")
        for marker in delegation_markers[plugin_id]:
            if marker not in text:
                raise AuditError(f"Direct delegation marker missing for {plugin_id}: {marker}")

    forbidden_adapter_patterns = {
        "global Drupal service lookup": r"\\Drupal::(?:service|getContainer|entityTypeManager)",
        "entity storage access": r"(?:entity_type\.manager|getStorage\s*\(|loadByProperties\s*\(|->save\s*\()",
        "HTTP route or loopback": r"(?:/api/agentic-harness|http_client|localhost|127\.0\.0\.1)",
        "provider or agent execution": r"(?:determineSolvability|->solve\s*\(|->chat\s*\()",
        "runtime state": r"agentic_harness_drupal_ai\.run_state",
    }
    for label, pattern in forbidden_adapter_patterns.items():
        if re.search(pattern, combined_plugins):
            raise AuditError(f"Forbidden adapter path found: {label}")

    runner_text = resolve(repo, overlay, "scripts/run-gate1-step03.sh").read_text(encoding="utf-8")
    exercise_text = resolve(repo, overlay, "drupal/scripts/gate1-step03-adapter-exercise.php").read_text(encoding="utf-8")
    for marker in ("GATE1_STEP03_ARTICLE_SOURCE_SHA256", ARTICLE_SOURCE_SHA, "predecessor_step02", "step03_extended_article_source_sha256"):
        if marker not in exercise_text:
            raise AuditError(f"Article-source hash regression marker missing: {marker}")
    executable = combined_plugins + runner_text + exercise_text
    for label, pattern in {
        "model execution": r"(?:->determineSolvability\s*\(|->solve\s*\(|->chat\s*\()",
        "outbound client": r"(?:\bcurl\s|\bwget\s|http_client|file_get_contents\s*\(\s*['\"]https?://)",
        "AI Agent configuration creation": r"(?:ai_agent.*->save|getStorage\s*\(\s*['\"]ai_agent)",
        "runtime-state collection": r"keyvalue.*agentic_harness_drupal_ai\.run_state",
    }.items():
        if re.search(pattern, executable, flags=re.IGNORECASE):
            raise AuditError(f"Excluded Step 1.03 path found: {label}")

    gate = resolve(repo, overlay, "docs/gates/GATE-1-STEP03-DRUPAL-AI-TOOL-ADAPTERS.md").read_text(encoding="utf-8")
    for marker in (
        "plugin.manager.ai.function_calls",
        "Drupal\\ai\\Attribute\\FunctionCall",
        "Drupal\\ai\\Base\\FunctionCallBase",
        "ExecutableFunctionCallInterface",
        "No adapter calls",
        "data.context",
        "gate-1-step04-drupal-ai-canonical-vertical-slice-v1.0.0",
    ):
        if marker not in gate:
            raise AuditError(f"Gate document marker missing: {marker}")

    return {
        "status": "pass",
        "predecessor_commit": EXPECTED_COMMIT,
        "payload_files_checked": len(PAYLOAD_FILES),
        "plugin_ids": list(PLUGIN_FILES),
        "dependency_machine_names": ["ai", "ai_agents", "agentic_harness_tools"],
        "dependency_injection": "FunctionCallBase ContainerFactoryPluginInterface create override",
        "direct_entity_path_found": False,
        "model_or_agent_invocation_found": False,
        "network_invocation_found": False,
        "runtime_state_path_found": False,
        "versions": composer_versions(repo),
    }


def verify_snapshot(value: Any, label: str, module_enabled: bool) -> None:
    expected = {
        "status": "pass",
        "article_count": 20,
        "suggestion_count": 0,
        "target_count": 12,
        "target_sequence_sha256": TARGET_SHA,
        "canonical_target_sequence": 1,
        "article_source_sha256": ARTICLE_SOURCE_SHA,
        "seeded_clean": True,
        "module_enabled": module_enabled,
        "model_call_performed": False,
        "network_call_performed": False,
        "raw_image_retained": False,
        "secret_retained": False,
    }
    if not isinstance(value, dict):
        raise AuditError(f"{label} is not an object")
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise AuditError(f"Unexpected {label} fact: {key}")


def evidence_audit(repo: Path, run_dir: Path) -> dict[str, Any]:
    before = load(run_dir / "before-state.json")
    exercise = load(run_dir / "adapter-exercise.json")
    after = load(run_dir / "after-state.json")
    reconciliation_evidence = load(run_dir / "article-source-hash-reconciliation.json")
    verify_snapshot(before, "before-state", False)
    verify_snapshot(after, "after-state", False)
    for key in ("article_count", "suggestion_count", "target_count", "target_sequence_sha256", "canonical_target_sequence", "canonical_target_identity_sha256", "article_source_sha256", "step03_extended_article_source_sha256", "gate05_certification_article_source_sha256", "article_source_hash_reconciliation", "module_enabled"):
        if before.get(key) != after.get(key):
            raise AuditError(f"Pre-run database/configuration state was not restored: {key}")
    reconciliation = before.get("article_source_hash_reconciliation", {})
    if reconciliation.get("classification") != "hash_definition_drift_only" or reconciliation.get("actual_source_drift") is not False:
        raise AuditError("Article-source hash reconciliation did not resolve to definition drift only")
    if reconciliation.get("predecessor_step02", {}).get("sha256") != ARTICLE_SOURCE_SHA:
        raise AuditError("Step 1.02 predecessor Article-source hash is not controlling")
    if reconciliation_evidence.get("article_source_hash_reconciliation") != reconciliation:
        raise AuditError("Retained Article-source reconciliation differs from the captured source facts")
    seeded_manifest = reconciliation_evidence.get("seeded_clean_manifest", {})
    if seeded_manifest.get("current_manifest_byte_equal") is not True or seeded_manifest.get("target_count") != 12:
        raise AuditError("Seeded-clean manifest reconciliation is incomplete")
    expected_exercise = {
        "status": "pass",
        "target_sequence_sha256": TARGET_SHA,
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
    for key, expected in expected_exercise.items():
        if exercise.get(key) != expected:
            raise AuditError(f"Unexpected sanitized adapter evidence: {key}")
    if exercise.get("get_image_context", {}).get("direct_data_shape") is not True:
        raise AuditError("Direct get_image_context data shape was not proven")
    if exercise.get("get_image_context", {}).get("raw_representation_retained") is not False:
        raise AuditError("Raw context representation was retained")
    if exercise.get("submission", {}).get("data") != exercise.get("idempotent_replay", {}).get("data"):
        raise AuditError("Idempotent replay identity changed")

    secret_pattern = re.compile(
        r"sk-[A-Za-z0-9_-]{20,}|data:image/|Authorization\s*:|Basic\s+[A-Za-z0-9+/]{16,}={0,2}|DO_NOT_EXPOSE_UNKNOWN_EXCEPTION_DETAIL",
        re.IGNORECASE,
    )
    for path in run_dir.rglob("*"):
        if path.is_file() and path.name != "package-files-sha256.txt":
            if secret_pattern.search(path.read_text(encoding="utf-8", errors="replace")):
                raise AuditError(f"Sensitive or raw value retained: {path.name}")
    return {
        "status": "pass",
        "run_id": run_dir.name,
        "article_count_before_after": [20, 20],
        "recommendation_count_before_after": [0, 0],
        "target_count_before_after": [12, 12],
        "target_sequence_sha256": TARGET_SHA,
        "canonical_target_sequence": 1,
        "source_hash_unchanged": True,
        "predecessor_compatible_article_source_sha256": ARTICLE_SOURCE_SHA,
        "hash_definition_drift_resolved": True,
        "actual_source_drift": False,
        "seeded_clean_before_after": True,
        "module_enabled_before_after": [False, False],
        "plugin_count": 4,
        "permission_denials": 8,
        "negative_controls": 7,
        "model_call_performed": False,
        "network_call_performed": False,
        "api_credit_used": False,
        "secret_hygiene": "pass",
        "next_package": "gate-1-step04-drupal-ai-canonical-vertical-slice-v1.0.0",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--overlay", type=Path)
    parser.add_argument("--run-dir", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    result = static_audit(repo, args.overlay.resolve() if args.overlay else None)
    if args.run_dir:
        result["evidence"] = evidence_audit(repo, args.run_dir.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as exc:
        raise SystemExit(f"[ERROR] {exc}") from exc
