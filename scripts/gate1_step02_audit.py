#!/usr/bin/env python3
"""Audit Gate 1 Step 1.02 without making a network or model call."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


EXPECTED_COMMIT = "10a7f531bff1af8ea93ecbe1e447e98cb4834ac6"
EXPECTED_GATE05_RUN = "gate05-step05-20260805T184155Z-50124"
EXPECTED_GATE05_SHA = "99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a"
EXPECTED_STEP01_RUN = "gate1-step01-20260805T205448Z-103220"
EXPECTED_STEP01_SHA = "360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6"
EXPECTED_TARGET_SHA = "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728"
EXPECTED_VERSIONS = {
    "drupal/core-recommended": "11.4.4",
    "drupal/ai": "1.4.5",
    "drupal/ai_agents": "1.3.2",
    "drupal/ai_provider_openai": "1.2.3",
}
PAYLOAD_FILES = (
    "docs/gates/GATE-1-STEP02-DRUPAL-AI-RUNTIME-PROBE.md",
    "docs/decisions/ADR-0006-drupal-ai-programmatic-runtime-path.md",
    "drupal/scripts/gate1-step02-runtime-probe.php",
    "scripts/gate1_step02_audit.py",
    "scripts/gate1_step02_finalize.py",
    "scripts/run-gate1-step02.sh",
)


class AuditError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AuditError(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AuditError(f"Invalid JSON: {path}: {exc}") from exc


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve(repo: Path, overlay: Path | None, relative: str) -> Path:
    if overlay is not None:
        candidate = overlay / relative
        if candidate.is_file():
            return candidate
    return repo / relative


def composer_versions(repo: Path) -> dict[str, str]:
    lock = load_json(repo / "drupal/composer.lock")
    result: dict[str, str] = {}
    for package in lock.get("packages", []):
        name = package.get("name")
        if name in EXPECTED_VERSIONS:
            result[name] = package.get("version")
    if result != EXPECTED_VERSIONS:
        raise AuditError(f"Pinned Composer version drift: {result}")
    return result


def pointer_run(repo: Path, relative: str) -> str:
    value = (repo / relative).read_text(encoding="utf-8").strip()
    return Path(value).name


def static_audit(repo: Path, overlay: Path | None) -> dict[str, Any]:
    if sha256(repo / "shared/contracts/GATE05-SUBSTRATE-FREEZE.json") != EXPECTED_GATE05_SHA:
        raise AuditError("Gate 0.5 freeze digest changed")
    if sha256(repo / "shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json") != EXPECTED_STEP01_SHA:
        raise AuditError("Step 1.01 contract digest changed")
    if pointer_run(repo, "evidence/gates/gate-0.5/substrate-certification/GATE05-STEP05-LATEST.txt") != EXPECTED_GATE05_RUN:
        raise AuditError("Accepted Gate 0.5 evidence pointer changed")
    if pointer_run(repo, "evidence/gates/gate-1/drupal-ai-batch-contract/GATE1-STEP01-LATEST.txt") != EXPECTED_STEP01_RUN:
        raise AuditError("Accepted Step 1.01 evidence pointer changed")

    for relative in PAYLOAD_FILES:
        path = resolve(repo, overlay, relative)
        if not path.is_file() or path.stat().st_size == 0:
            raise AuditError(f"Missing Step 1.02 payload file: {relative}")

    php = resolve(repo, overlay, "drupal/scripts/gate1-step02-runtime-probe.php").read_text(encoding="utf-8")
    shell = resolve(repo, overlay, "scripts/run-gate1-step02.sh").read_text(encoding="utf-8")
    combined_exec = php + "\n" + shell
    forbidden = {
        "provider chat invocation": r"->chat\s*\(",
        "agent execution invocation": r"->determineSolvability\s*\(",
        "provider model-catalog query": r"->getConfiguredModels\s*\(",
        "curl invocation": r"(^|[\s;])curl\s",
        "wget invocation": r"(^|[\s;])wget\s",
        "Drupal config import": r"\bdrush\s+cim\b",
        "Drupal entity save": r"->save\s*\(",
    }
    for label, pattern in forbidden.items():
        if re.search(pattern, combined_exec, flags=re.MULTILINE):
            raise AuditError(f"Forbidden Step 1.02 executable path found: {label}")
    for required in (
        "plugin.manager.ai_agents",
        "determineSolvability",
        "overrideFunctions",
        "setChatStructuredJsonSchema",
        "agentic_harness_drupal_ai.run_state",
        "gate1_step02_reflection_surface",
        "'collection_opened' => FALSE",
        "model_call_performed' => FALSE",
        "network_call_performed' => FALSE",
    ):
        if required not in php:
            raise AuditError(f"Runtime probe is missing required marker: {required}")

    adr = resolve(repo, overlay, "docs/decisions/ADR-0006-drupal-ai-programmatic-runtime-path.md").read_text(encoding="utf-8")
    gate = resolve(repo, overlay, "docs/gates/GATE-1-STEP02-DRUPAL-AI-RUNTIME-PROBE.md").read_text(encoding="utf-8")
    for required in (
        "Drupal 11.4.4",
        "Drupal AI 1.4.5",
        "AI Agents 1.3.2",
        "OpenAI provider 1.2.3",
        "plugin.manager.ai_agents",
        "gpt-4.1-mini-2025-04-14",
        "temperature: 0.0",
        "agentic_harness_drupal_ai.run_state",
        "no model call",
    ):
        if required.lower() not in (adr + gate).lower():
            raise AuditError(f"Decision documentation is missing: {required}")

    return {
        "status": "pass",
        "predecessor_commit": EXPECTED_COMMIT,
        "gate05_run_id": EXPECTED_GATE05_RUN,
        "gate05_freeze_sha256": EXPECTED_GATE05_SHA,
        "step01_run_id": EXPECTED_STEP01_RUN,
        "step01_contract_sha256": EXPECTED_STEP01_SHA,
        "versions": composer_versions(repo),
        "payload_files_checked": len(PAYLOAD_FILES),
        "model_invocation_found": False,
        "network_invocation_found": False,
        "drupal_mutation_invocation_found": False,
    }


def verify_snapshot(value: Any, label: str) -> None:
    expected = {
        "status": "pass",
        "article_count": 20,
        "suggestion_count": 0,
        "target_count": 12,
        "target_sequence_sha256": EXPECTED_TARGET_SHA,
        "canonical_target_sequence": 1,
        "seeded_clean": True,
        "model_call_performed": False,
        "raw_image_retained": False,
        "secret_retained": False,
    }
    if not isinstance(value, dict):
        raise AuditError(f"{label} is not an object")
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise AuditError(f"Unexpected {label} field {key}: {value.get(key)!r}")


def evidence_audit(repo: Path, run_dir: Path) -> dict[str, Any]:
    before = load_json(run_dir / "before-state.json")
    runtime = load_json(run_dir / "runtime-probe.json")
    after = load_json(run_dir / "after-state.json")
    verify_snapshot(before, "before-state")
    verify_snapshot(after, "after-state")
    for key in ("article_source_sha256", "target_sequence_sha256", "canonical_target_identity_sha256"):
        if before.get(key) != after.get(key):
            raise AuditError(f"Before/after state changed: {key}")

    expected_runtime = {
        "status": "pass",
        "model_call_performed": False,
        "network_call_performed": False,
        "drupal_write_performed": False,
        "raw_image_retained": False,
        "secret_retained": False,
        "framework_implementation_claimed": False,
        "provider_pre_request_events_observed": 0,
        "agent_request_events_observed": 0,
    }
    for key, expected in expected_runtime.items():
        if runtime.get(key) != expected:
            raise AuditError(f"Unexpected runtime probe field {key}: {runtime.get(key)!r}")
    if runtime.get("versions") != EXPECTED_VERSIONS:
        raise AuditError("Runtime version evidence does not match Composer lock")
    chosen = runtime.get("chosen_runtime", {})
    if chosen.get("service_id") != "plugin.manager.ai_agents":
        raise AuditError("Unexpected chosen agent service")
    if chosen.get("instance_class") != "Drupal\\ai_agents\\PluginBase\\AiAgentEntityWrapper":
        raise AuditError("Unexpected config-agent wrapper class")
    if chosen.get("callable_entry_point") != "determineSolvability" or chosen.get("final_output_method") != "solve":
        raise AuditError("Unexpected programmatic callable path")
    provider = runtime.get("provider", {})
    if provider.get("plugin_id") != "openai" or provider.get("pinned_model_id") != "gpt-4.1-mini-2025-04-14":
        raise AuditError("Pinned provider/model path was not proven")
    if provider.get("agent_model_id") != "gpt-4.1-mini-2025-04-14" or provider.get("pinned_model_bound_to_agent") is not True:
        raise AuditError("Pinned model was not explicitly bound to the agent")
    if provider.get("model_catalog_query_performed") is not False:
        raise AuditError("Provider model catalog was queried")
    if provider.get("explicit_configuration") != {"temperature": 0}:
        raise AuditError("Pinned temperature was not configured explicitly")
    if provider.get("active_chat_with_tools_default", {}).get("model_id") == "gpt-4.1-mini-2025-04-14":
        raise AuditError("Expected the probe to document why default lookup is rejected")
    structured = runtime.get("structured_output", {}).get("normalized_schema", {})
    if structured.get("strict") is not True:
        raise AuditError("Strict structured output was not constructed")
    tool_surface = runtime.get("tool_surface", {})
    if tool_surface.get("selection_allowlist") is not True or tool_surface.get("provider_level_hard_tool_choice_supported") is not False:
        raise AuditError("Tool selection/requirement boundary is incomplete")
    if runtime.get("future_adapters") != [
        "discover_targets", "get_image_context", "submit_recommendation", "get_recommendation_status"
    ]:
        raise AuditError("Future adapter extension points drifted")
    config_entity = runtime.get("config_entity", {})
    if config_entity.get("entity_type_id") != "ai_agent" or config_entity.get("class") != "Drupal\\ai_agents\\Entity\\AiAgent":
        raise AuditError("AI Agent configuration-entity evidence is incomplete")
    if config_entity.get("loaded_id") != runtime.get("chosen_runtime", {}).get("plugin_definition_id"):
        raise AuditError("Configuration entity was not loaded by the selected plugin ID")
    services = runtime.get("service_definitions", {})
    expected_services = {
        "plugin.manager.ai_agents": "Drupal\\ai_agents\\PluginManager\\AiAgentManager",
        "ai.provider": "Drupal\\ai\\AiProviderPluginManager",
        "plugin.manager.ai.function_calls": "Drupal\\ai\\Service\\FunctionCalling\\FunctionCallPluginManager",
    }
    for service_id, class_name in expected_services.items():
        if services.get(service_id, {}).get("class") != class_name:
            raise AuditError(f"Installed service definition drifted: {service_id}")
    if services["plugin.manager.ai_agents"].get("arguments") != [
        "@entity_type.manager", "@current_user", "@plugin.manager.ai.function_calls",
        "@ai_agents.agent_helper", "@token", "@event_dispatcher", "@ai.provider",
        "@ai_agents.artifact_helper", "@uuid", "@ai_agents.override_applier",
        "@ai.guardrail_helper", "@logger.channel.ai_agents",
    ]:
        raise AuditError("AI Agent manager service dependencies drifted")
    reflection = runtime.get("reflection_surface", {})
    required_signatures = {
        "Drupal\\ai_agents\\PluginManager\\AiAgentManager": ("__construct", "createInstance", "getDefinition"),
        "Drupal\\ai_agents\\PluginBase\\AiAgentEntityWrapper": (
            "__construct", "setTask", "setAiProvider", "setModelName", "setAiConfiguration",
            "overrideFunctions", "getFunctions", "determineSolvability", "solve",
            "getChatHistory", "getToolResults", "getStructuredOutput", "toArray", "fromArray",
        ),
        "Drupal\\ai_agents\\Task\\Task": ("__construct", "setDescription", "setComments", "setFiles"),
        "Drupal\\ai\\AiProviderPluginManager": ("__construct", "createInstance", "getDefaultProviderForOperationType"),
        "Drupal\\ai\\Service\\FunctionCalling\\FunctionCallPluginManager": ("__construct", "createInstance"),
        "Drupal\\ai\\Base\\FunctionCallBase": ("__construct", "create", "populateValues", "normalize", "getReadableOutput", "getStructuredOutput"),
        "Drupal\\ai\\OperationType\\Chat\\ChatInput": ("__construct", "setChatStructuredJsonSchema", "getChatStructuredJsonSchema", "setChatTools", "getChatTools"),
    }
    for class_name, methods in required_signatures.items():
        class_evidence = reflection.get(class_name, {})
        signatures = class_evidence.get("relevant_method_signatures", {})
        if not class_evidence.get("public_method_names") or any(method not in signatures for method in methods):
            raise AuditError(f"Reflection evidence is incomplete: {class_name}")
        for method in methods:
            if not signatures[method].get("signature") or "return_type_declared" not in signatures[method]:
                raise AuditError(f"Method signature evidence is incomplete: {class_name}::{method}")
    state = runtime.get("state_surface", {})
    if state.get("collection") != "agentic_harness_drupal_ai.run_state" or state.get("write_performed") is not False:
        raise AuditError("Framework-owned state location was not safely proven")
    if state.get("shared_runtime_storage") is not False:
        raise AuditError("Shared runtime storage was selected")
    if state.get("collection_opened") is not False:
        raise AuditError("Future state collection was opened during Step 1.02")
    if len(runtime.get("rejected_paths", {})) < 8:
        raise AuditError("Rejected path matrix is incomplete")

    for relative, expected in runtime.get("inspected_source_sha256", {}).items():
        path = repo / "drupal" / relative
        if not path.is_file() or sha256(path) != expected:
            raise AuditError(f"Inspected installed source changed: {relative}")

    secret_pattern = re.compile(
        r"sk-[A-Za-z0-9_-]{20,}|data:image/|Authorization\s*:|Basic\s+[A-Za-z0-9+/]{16,}={0,2}",
        re.IGNORECASE,
    )
    for path in run_dir.rglob("*"):
        if path.is_file() and path.name != "package-files-sha256.txt":
            text = path.read_text(encoding="utf-8", errors="replace")
            if secret_pattern.search(text):
                raise AuditError(f"Potential secret or raw image payload retained: {path.name}")

    return {
        "status": "pass",
        "run_id": run_dir.name,
        "article_count_before_after": [20, 20],
        "suggestion_count_before_after": [0, 0],
        "target_sequence_sha256": EXPECTED_TARGET_SHA,
        "canonical_target_sequence": 1,
        "source_hash_unchanged": True,
        "seeded_clean_before_after": True,
        "chosen_service": "plugin.manager.ai_agents",
        "chosen_entry_point": "determineSolvability",
        "chosen_state_collection": "agentic_harness_drupal_ai.run_state",
        "rejected_path_count": len(runtime["rejected_paths"]),
        "provider_default_rejected": True,
        "explicit_model": "gpt-4.1-mini-2025-04-14",
        "explicit_temperature": 0.0,
        "provider_request_events": 0,
        "model_call_performed": False,
        "network_call_performed": False,
        "drupal_state_mutated": False,
        "secret_hygiene": "pass",
        "step03_started": False,
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
