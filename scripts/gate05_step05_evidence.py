#!/usr/bin/env python3
"""Evaluate, freeze, and audit Gate 0.5 Step 05 substrate evidence."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

PACKAGE_VERSION = "1.0.5"
FREEZE_MANIFEST = "shared/contracts/GATE05-SUBSTRATE-FREEZE.json"
FREEZE_DIGEST = "shared/contracts/GATE05-SUBSTRATE-FREEZE.sha256"

REQUIRED_FREEZE_FILES = [
    "EXPERIMENT_SPEC.md",
    "shared/README.md",
    "shared/schemas/target.schema.json",
    "shared/schemas/image-context.schema.json",
    "shared/schemas/recommendation.schema.json",
    "shared/schemas/tool-result.schema.json",
    "shared/drupal_client/README.md",
    "shared/drupal_client/client.py",
    "drupal/web/modules/custom/agentic_harness_tools/agentic_harness_tools.permissions.yml",
    "drupal/web/modules/custom/agentic_harness_tools/agentic_harness_tools.routing.yml",
    "drupal/web/modules/custom/agentic_harness_tools/agentic_harness_tools.services.yml",
    "drupal/web/modules/custom/agentic_harness_tools/src/Controller/ToolController.php",
    "drupal/web/modules/custom/agentic_harness_tools/src/Exception/ImageContextException.php",
    "drupal/web/modules/custom/agentic_harness_tools/src/Exception/RecommendationSubmissionException.php",
    "drupal/web/modules/custom/agentic_harness_tools/src/Exception/RecommendationStatusException.php",
    "drupal/web/modules/custom/agentic_harness_tools/src/Service/ImageReviewFinder.php",
    "drupal/web/modules/custom/agentic_harness_tools/src/Service/ImageContextProvider.php",
    "drupal/web/modules/custom/agentic_harness_tools/src/Service/RecommendationValidator.php",
    "drupal/web/modules/custom/agentic_harness_tools/src/Service/RecommendationSubmitter.php",
    "drupal/web/modules/custom/agentic_harness_tools/src/Service/RecommendationStatusProvider.php",
    "drupal/scripts/phase0-step7.php",
    "drupal/scripts/phase0-step8.php",
    "drupal/scripts/run-phase0-step9.sh",
    "drupal/scripts/manifest.json",
    "drupal/scripts/seed.php",
    "drupal/scripts/phase0-step10.php",
    "drupal/scripts/run-phase0-step10.sh",
    "drupal/scripts/phase0-step17.php",
    "scripts/run-phase0-step17.sh",
]

CERTIFICATION_FILES = [
    "docs/gates/GATE-0.5-STEP05-SUBSTRATE-CERTIFICATION-AND-HANDOFF.md",
    "docs/handoffs/GATE-0.5-FRAMEWORK-HANDOFF.md",
    "shared/contracts/README.md",
    "drupal/scripts/gate05-step05-config.php",
    "scripts/gate05_step05_evidence.py",
    "scripts/run-gate05-step05.sh",
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_hashes(repo: Path, paths: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for relative in paths:
        path = repo / relative
        if not path.is_file():
            raise EvidenceError(f"Required frozen file is missing: {relative}")
        result[relative] = sha256_bytes(path.read_bytes())
    return result


def expand_freeze_files(repo: Path) -> list[str]:
    paths = sorted(set(REQUIRED_FREEZE_FILES))
    for relative in paths:
        if not (repo / relative).is_file():
            raise EvidenceError(f"Required frozen file is missing: {relative}")
    return paths


def git_head(repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise EvidenceError("Unable to resolve Git HEAD.")
    return result.stdout.strip()


def validate_envelope(value: Any, tool_name: str) -> dict[str, Any]:
    keys = {
        "schema_version",
        "tool_name",
        "ok",
        "timestamp",
        "correlation_id",
        "data",
        "error",
    }
    if not isinstance(value, dict) or set(value) != keys:
        raise EvidenceError(f"{tool_name} envelope keys are invalid.")
    if (
        value["schema_version"] != 1
        or value["tool_name"] != tool_name
        or value["ok"] is not True
        or value["error"] is not None
        or not isinstance(value["data"], dict)
    ):
        raise EvidenceError(f"{tool_name} envelope is not successful.")
    return value["data"]


def validate_target(value: Any) -> dict[str, Any]:
    keys = {
        "schema_version",
        "sequence",
        "node_uuid",
        "revision_id",
        "field_name",
        "delta",
        "file_uuid",
        "target_state",
        "existing_alt",
    }
    if not isinstance(value, dict) or set(value) != keys:
        raise EvidenceError("Target does not match target.schema.json.")
    return value


def validate_snapshot(value: Any, label: str) -> dict[str, Any]:
    keys = {
        "article_count",
        "article_source_sha256",
        "suggestion_count",
        "recommendation_state_sha256",
        "combined_state_sha256",
    }
    if not isinstance(value, dict) or not keys.issubset(value):
        raise EvidenceError(f"{label} snapshot is incomplete.")
    if value["article_count"] != 20:
        raise EvidenceError(f"{label} snapshot does not contain 20 Articles.")
    return value


def scan_for_secrets(path: Path) -> None:
    patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
        re.compile(r"(?i)authorization\s*:\s*(?:bearer|basic)\s+(?!<redacted>)\S+"),
        re.compile(r"(?i)(?:password|OPENAI_API_KEY)\s*[=:]\s*(?!<redacted>)\S+"),
        re.compile(r"(?i)user\s*=\s*[\"'][^\"']+:[^\"']+[\"']"),
        re.compile(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]{40,}"),
    ]
    for candidate in path.rglob("*"):
        if not candidate.is_file():
            continue
        text = candidate.read_text(encoding="utf-8", errors="replace")
        for pattern in patterns:
            if pattern.search(text):
                raise EvidenceError(
                    f"Potential secret or raw image retained: {candidate.name}"
                )



def canonical_json_sha256(value: Any) -> str:
    return sha256_bytes(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def validate_active_config(value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != 1
        or value.get("status") != "pass"
    ):
        raise EvidenceError("Active Drupal configuration snapshot is invalid.")

    content_type = value.get("content_type")
    if content_type != {
        "bundle": "alt_text_suggestion",
        "new_revision": True,
    }:
        raise EvidenceError("Recommendation content-type semantics changed.")

    expected_fields = {
        "field_target_node": ("entity_reference", 1, True),
        "field_target_revision": ("integer", 1, True),
        "field_target_field": ("string", 1, True),
        "field_target_delta": ("integer", 1, True),
        "field_target_file": ("entity_reference", 1, True),
        "field_proposed_alt": ("string_long", 1, True),
        "field_review_status": ("list_string", 1, True),
        "field_source_framework": ("list_string", 1, True),
        "field_run_id": ("string", 1, True),
        "field_evidence_hash": ("string", 1, False),
    }
    fields = value.get("fields")
    if not isinstance(fields, dict) or set(fields) != set(expected_fields):
        raise EvidenceError("Recommendation field inventory changed.")

    for field_name, expected in expected_fields.items():
        field = fields.get(field_name)
        if (
            not isinstance(field, dict)
            or field.get("type") != expected[0]
            or field.get("cardinality") != expected[1]
            or field.get("required") is not expected[2]
        ):
            raise EvidenceError(
                f"Recommendation field semantics changed: {field_name}"
            )

    if (
        fields["field_target_node"]
        .get("storage_settings", {})
        .get("target_type") != "node"
        or fields["field_target_file"]
        .get("storage_settings", {})
        .get("target_type") != "file"
    ):
        raise EvidenceError("Recommendation target-reference semantics changed.")

    review_values = (
        fields["field_review_status"]
        .get("storage_settings", {})
        .get("allowed_values")
    )
    if review_values != {
        "pending": "Pending",
        "approved": "Approved",
        "rejected": "Rejected",
    }:
        raise EvidenceError("Review-status vocabulary changed.")

    framework_values = (
        fields["field_source_framework"]
        .get("storage_settings", {})
        .get("allowed_values")
    )
    if framework_values != {
        "phase0_fixture": "Phase 0 test fixture",
        "drupal_ai": "Drupal AI",
        "langgraph": "LangGraph",
        "crewai": "CrewAI",
    }:
        raise EvidenceError("Source-framework vocabulary changed.")

    if (
        fields["field_run_id"]
        .get("storage_settings", {})
        .get("max_length") != 128
        or fields["field_evidence_hash"]
        .get("storage_settings", {})
        .get("max_length") != 128
    ):
        raise EvidenceError("Run or evidence identifier limits changed.")

    widgets = value.get("form_widgets")
    if (
        not isinstance(widgets, dict)
        or widgets.get("field_proposed_alt") != "string_textarea"
        or widgets.get("field_review_status") != "options_select"
    ):
        raise EvidenceError("Human-review form widgets changed.")

    formatters = value.get("view_formatters")
    if not isinstance(formatters, dict) or set(formatters) != set(expected_fields):
        raise EvidenceError("Recommendation view formatter inventory changed.")

    queue = value.get("review_queue")
    if queue != {
        "view_id": "alt_text_review_queue",
        "path": "admin/review-queue",
    }:
        raise EvidenceError("Review queue identity or path changed.")

    roles = value.get("roles")
    if not isinstance(roles, dict):
        raise EvidenceError("Role configuration is missing.")
    agent = roles.get("agent_service")
    editor = roles.get("content_editor")
    if not isinstance(agent, list) or not isinstance(editor, list):
        raise EvidenceError("Role permissions are malformed.")

    expected_agent = {
        "access content",
        "create alt_text_suggestion content",
        "use agentic harness discovery tools",
        "view own unpublished content",
    }
    if set(agent) != expected_agent:
        raise EvidenceError(
            "agent_service exact least-privilege boundary changed."
        )

    editor_base = {
        "access administration pages",
        "access content",
        "access content overview",
        "access contextual links",
        "edit any alt_text_suggestion content",
        "view alt_text_suggestion revisions",
        "view the administration theme",
    }
    editor_navigation = {
        "access navigation",
        "access toolbar",
    }
    editor_permissions = set(editor)
    navigation_permissions = editor_permissions.intersection(
        editor_navigation
    )
    if (
        not editor_base.issubset(editor_permissions)
        or not navigation_permissions
        or editor_permissions
        != editor_base.union(navigation_permissions)
    ):
        raise EvidenceError(
            "content_editor exact review-only boundary changed."
        )

    return value

def prior_evidence(repo: Path) -> dict[str, Any]:
    pointers = {
        "step01": (
            "evidence/gates/gate-0.5/baseline/GATE05-STEP01-LATEST.txt"
        ),
        "step02": (
            "evidence/gates/gate-0.5/image-context/GATE05-STEP02-LATEST.txt"
        ),
        "step03": (
            "evidence/gates/gate-0.5/submit-recommendation/"
            "GATE05-STEP03-LATEST.txt"
        ),
        "step04": (
            "evidence/gates/gate-0.5/recommendation-status/"
            "GATE05-STEP04-LATEST.txt"
        ),
    }
    result: dict[str, Any] = {}
    for key, relative_pointer in pointers.items():
        pointer = repo / relative_pointer
        if not pointer.is_file():
            raise EvidenceError(f"Missing {key} passing pointer.")
        relative = pointer.read_text(encoding="utf-8").strip()
        run_dir = repo / relative
        summary = load_json(run_dir / "summary.json")
        if summary.get("status") != "pass":
            raise EvidenceError(f"{key} retained summary is not passing.")
        result[key] = {
            "path": relative,
            "run_id": run_dir.name,
        }

    step01_dir = repo / result["step01"]["path"]
    step01 = load_json(step01_dir / "summary.json")
    step02 = load_json(repo / result["step02"]["path"] / "summary.json")
    step03 = load_json(repo / result["step03"]["path"] / "summary.json")
    step04 = load_json(repo / result["step04"]["path"] / "summary.json")

    canonical_target = validate_target(
        load_json(step01_dir / "canonical-target.json")
    )
    if canonical_target["sequence"] != 1:
        raise EvidenceError(
            "Retained Step 01 canonical target is not sequence 1."
        )
    target_sequence_sha256 = step01.get("target_sequence_sha256")
    if not isinstance(target_sequence_sha256, str) or not re.fullmatch(
        r"[a-f0-9]{64}",
        target_sequence_sha256,
    ):
        raise EvidenceError(
            "Retained Step 01 target-sequence hash is missing or invalid."
        )

    result["step01"].update({
        "canonical_target_sequence": canonical_target["sequence"],
        "target_sequence_sha256": target_sequence_sha256,
    })
    result["step02"].update({
        "context_evidence_hash": step02["context_evidence_hash"],
        "image_sha256": step02["image_sha256"],
    })
    result["step03"].update({
        "idempotent_replay_same_identity": (
            step03["idempotent_replay_same_identity"]
        ),
        "source_article_unchanged": step03["source_article_unchanged"],
    })
    result["step04"].update({
        "human_decision": step04["human_decision"]["status"],
        "reviewer_username": step04["human_decision"]["reviewer_username"],
        "status_operation_read_only": step04["status_operation_read_only"],
        "source_article_unchanged": step04["source_article_unchanged"],
    })
    return result


def evaluate(repo: Path, run_dir: Path) -> None:
    lineage = prior_evidence(repo)
    canonical = load_json(
        repo / lineage["step01"]["path"] / "canonical-target.json"
    )
    validate_target(canonical)

    active_config = validate_active_config(
        load_json(run_dir / "active-config.json")
    )
    active_config_sha256 = canonical_json_sha256(active_config)

    route_matrix = load_json(run_dir / "route-matrix.json")
    expected_routes = {
        "find_images_needing_review": {
            "path": "/api/agentic-harness/v1/images-needing-review",
            "methods": ["GET"],
            "permission": "use agentic harness discovery tools",
        },
        "get_image_context": {
            "path": "/api/agentic-harness/v1/image-context",
            "methods": ["POST"],
            "permission": "use agentic harness discovery tools",
        },
        "submit_recommendation": {
            "path": "/api/agentic-harness/v1/recommendations",
            "methods": ["POST"],
            "permission": "create alt_text_suggestion content",
        },
        "get_recommendation_status": {
            "path": (
                "/api/agentic-harness/v1/recommendations/"
                "{recommendation_id}/status"
            ),
            "methods": ["GET"],
            "permission": "use agentic harness discovery tools",
        },
    }
    if (
        not isinstance(route_matrix, dict)
        or route_matrix.get("status") != "pass"
        or route_matrix.get("routes") != expected_routes
        or route_matrix.get("agent_bot_principals") is not True
        or route_matrix.get("editor_dana_review_only") is not True
        or route_matrix.get("basic_auth_only") is not True
        or route_matrix.get("all_routes_no_cache") is not True
    ):
        raise EvidenceError("Four-operation route matrix failed.")

    find_data = validate_envelope(
        load_json(run_dir / "find-response.json"),
        "find_images_needing_review",
    )
    targets = find_data.get("targets")
    if (
        not isinstance(targets, list)
        or len(targets) != 12
        or find_data.get("total_count") != 12
    ):
        raise EvidenceError("Discovery did not return exactly 12 targets.")
    targets = [validate_target(target) for target in targets]
    if targets[0] != canonical or [t["sequence"] for t in targets] != list(
        range(1, 13)
    ):
        raise EvidenceError("Discovery order or canonical target changed.")

    retained_target = load_json(run_dir / "target-1.json")
    if retained_target != canonical:
        raise EvidenceError("Retained target 1 differs from the frozen canonical target.")

    context_envelope = load_json(run_dir / "context-sanitized.json")
    context_data = validate_envelope(context_envelope, "get_image_context")
    if context_data.get("target") != canonical:
        raise EvidenceError("Context operation returned the wrong target.")

    image = context_data.get("image")
    representation = image.get("representation") if isinstance(image, dict) else None
    if (
        not isinstance(image, dict)
        or not isinstance(representation, dict)
        or representation.get("kind") != "data_url"
        or representation.get("value") != "<runtime-only-data-url>"
        or image.get("sha256") != lineage["step02"]["image_sha256"]
        or context_data.get("evidence_hash")
        != lineage["step02"]["context_evidence_hash"]
    ):
        raise EvidenceError("Sanitized context does not match passing Step 02 evidence.")

    runtime = load_json(run_dir / "context-runtime-verification.json")
    if (
        runtime.get("status") != "pass"
        or runtime.get("representation_kind") != "data_url"
        or runtime.get("representation_value_retained") is not False
        or runtime.get("raw_image_bytes_retained") is not False
        or runtime.get("image_sha256") != lineage["step02"]["image_sha256"]
        or runtime.get("context_evidence_hash")
        != lineage["step02"]["context_evidence_hash"]
        or runtime.get("decoded_byte_length") != image.get("byte_length")
    ):
        raise EvidenceError("Runtime-only context verification failed.")

    request = load_json(run_dir / "submission-request.json")
    if (
        request.get("schema_version") != 1
        or request.get("target") != canonical
        or request.get("source_framework") != "drupal_ai"
        or request.get("evidence_hash")
        != lineage["step02"]["context_evidence_hash"]
        or request.get("validator_version") != "gate05-validator-1.0.0"
    ):
        raise EvidenceError("Controlled recommendation request is invalid.")

    submit_data = validate_envelope(
        load_json(run_dir / "submit-response.json"),
        "submit_recommendation",
    )
    replay_data = validate_envelope(
        load_json(run_dir / "submit-replay-response.json"),
        "submit_recommendation",
    )
    expected_submit_keys = {
        "node_id",
        "uuid",
        "revision_id",
        "status",
        "source_framework",
        "run_id",
        "target",
    }
    if (
        set(submit_data) != expected_submit_keys
        or submit_data != replay_data
        or submit_data["status"] != "pending"
        or submit_data["source_framework"] != request["source_framework"]
        or submit_data["run_id"] != request["run_id"]
        or submit_data["target"] != canonical
    ):
        raise EvidenceError("Submission or idempotent replay failed.")

    status_values = []
    for filename in (
        "status-uuid.json",
        "status-nid.json",
        "status-repeat.json",
    ):
        data = validate_envelope(
            load_json(run_dir / filename),
            "get_recommendation_status",
        )
        if set(data) != {
            "uuid",
            "revision_id",
            "status",
            "reviewer_username",
            "reviewed_at",
        }:
            raise EvidenceError("Status result keys are invalid.")
        status_values.append(data)
    if not (
        status_values[0] == status_values[1] == status_values[2]
        and status_values[0]["uuid"] == submit_data["uuid"]
        and status_values[0]["revision_id"] == submit_data["revision_id"]
        and status_values[0]["status"] == "pending"
        and status_values[0]["reviewer_username"] is None
        and status_values[0]["reviewed_at"] is None
    ):
        raise EvidenceError("Pending status reads are inconsistent.")

    inspection = load_json(run_dir / "recommendation-inspection.json")
    if (
        inspection.get("node_id") != submit_data["node_id"]
        or inspection.get("uuid") != submit_data["uuid"]
        or inspection.get("owner_username") != "agent_bot"
        or inspection.get("published") is not False
        or inspection.get("revision_count") != 1
        or inspection.get("current_review_status") != "pending"
        or inspection.get("current_proposed_alt_text")
        != request["proposed_alt_text"]
        or inspection.get("current_source_framework") != "drupal_ai"
        or inspection.get("current_run_id") != request["run_id"]
        or inspection.get("current_evidence_hash")
        != request["evidence_hash"]
        or inspection.get("current_target", {}).get("node_uuid")
        != canonical["node_uuid"]
        or inspection.get("current_target", {}).get("revision_id")
        != canonical["revision_id"]
        or inspection.get("current_target", {}).get("field_name")
        != canonical["field_name"]
        or inspection.get("current_target", {}).get("delta")
        != canonical["delta"]
        or inspection.get("current_target", {}).get("file_uuid")
        != canonical["file_uuid"]
    ):
        raise EvidenceError("Pending recommendation inspection failed.")

    access = inspection.get("access")
    if (
        not isinstance(access, dict)
        or access.get("agent_can_view") is not True
        or access.get("agent_can_update") is not False
        or access.get("editor_can_update") is not True
    ):
        raise EvidenceError("Recommendation access boundary failed.")

    before = validate_snapshot(
        load_json(run_dir / "source-before.json"),
        "before",
    )
    after_reads = validate_snapshot(
        load_json(run_dir / "source-after-reads.json"),
        "after reads",
    )
    after_submit = validate_snapshot(
        load_json(run_dir / "source-after-submit.json"),
        "after submit",
    )
    after_status = validate_snapshot(
        load_json(run_dir / "source-after-status.json"),
        "after status",
    )
    final = validate_snapshot(
        load_json(run_dir / "source-final-clean.json"),
        "final",
    )

    if (
        before != after_reads
        or before["suggestion_count"] != 0
        or after_submit["article_source_sha256"]
        != before["article_source_sha256"]
        or after_submit["suggestion_count"] != 1
        or after_status != after_submit
        or final != before
    ):
        raise EvidenceError(
            "Read-only, recommendation-only mutation, or final reset controls failed."
        )

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
        or environment.get("gate_0_5_complete") is not False
        or environment.get("shared_substrate_certification") is not True
    ):
        raise EvidenceError("Step 05 scope labels are invalid.")

    freeze_paths = expand_freeze_files(repo)
    frozen_hashes = file_hashes(repo, freeze_paths)
    certification_hashes = file_hashes(repo, CERTIFICATION_FILES)

    manifest = {
        "schema_version": 1,
        "manifest": "gate05-shared-substrate-freeze",
        "manifest_version": "1.0.0",
        "status": "certified",
        "git_base_commit": git_head(repo),
        "shared_substrate_certified": True,
        "gate_0_5_complete": False,
        "controlled_preflight": True,
        "framework_execution_claimed": False,
        "model_call_performed": False,
        "tool_surface": expected_routes,
        "active_runtime_config": {
            "source": "drupal/scripts/gate05-step05-config.php",
            "evidence": (
                run_dir.relative_to(repo).as_posix()
                + "/active-config.json"
            ),
            "sha256": active_config_sha256,
        },
        "contracts": {
            "target": "shared/schemas/target.schema.json",
            "image_context": "shared/schemas/image-context.schema.json",
            "recommendation": "shared/schemas/recommendation.schema.json",
            "tool_result": "shared/schemas/tool-result.schema.json",
        },
        "fairness_constants": {
            "provider": "OpenAI",
            "model": "gpt-4.1-mini-2025-04-14",
            "temperature": 0.0,
            "canonical_target_sequence": 1,
            "target_sequence_sha256": (
                lineage["step01"]["target_sequence_sha256"]
            ),
            "image_sha256": lineage["step02"]["image_sha256"],
            "context_evidence_hash": (
                lineage["step02"]["context_evidence_hash"]
            ),
            "validator_version": "gate05-validator-1.0.0",
            "review_destination": "alt_text_suggestion",
            "reviewer": "editor_dana",
            "source_article_mutation": "prohibited",
        },
        "shared_substrate_owns": [
            "Drupal HTTP transport and Basic Auth",
            "target and context schemas",
            "permission and stale-target checks",
            "deterministic recommendation validators",
            "idempotent recommendation creation",
            "Drupal review queue and revisions",
            "read-only recommendation status projection",
            "seed/reset and sanitized evidence conventions",
        ],
        "framework_owned": [
            "context assembly",
            "model invocation",
            "structured-output integration",
            "prompt orchestration",
            "tool selection and binding",
            "state and memory",
            "checkpointing",
            "human-interrupt behavior",
            "recovery logic",
            "workflow sequencing",
        ],
        "framework_vertical_slices": {
            "drupal_ai": {
                "directory": "drupal/",
                "run_id_prefix": "drupal_ai",
                "certified": False,
            },
            "langgraph": {
                "directory": "langchain/",
                "run_id_prefix": "langgraph",
                "certified": False,
            },
            "crewai": {
                "directory": "crewai/",
                "run_id_prefix": "crewai",
                "certified": False,
            },
        },
        "material_change_policy": (
            "Create an ADR, rerun Gate 0.5 Step 05, regenerate this "
            "manifest, and update all framework wrappers."
        ),
        "evidence_lineage": lineage,
        "step05_evidence": {
            "path": run_dir.relative_to(repo).as_posix(),
            "run_id": run_dir.name,
        },
        "frozen_files": frozen_hashes,
    }

    manifest_path = repo / FREEZE_MANIFEST
    write_json(manifest_path, manifest)
    manifest_bytes = manifest_path.read_bytes()
    manifest_sha = sha256_bytes(manifest_bytes)
    digest_line = f"{manifest_sha}  {FREEZE_MANIFEST}\n"
    digest_path = repo / FREEZE_DIGEST
    digest_path.write_text(digest_line, encoding="utf-8")

    (run_dir / "GATE05-SUBSTRATE-FREEZE.json").write_bytes(manifest_bytes)
    (run_dir / "GATE05-SUBSTRATE-FREEZE.sha256").write_text(
        digest_line,
        encoding="utf-8",
    )
    (run_dir / "frozen-files-sha256.txt").write_text(
        "".join(
            f"{digest}  {relative}\n"
            for relative, digest in frozen_hashes.items()
        ),
        encoding="utf-8",
    )
    (run_dir / "certification-files-sha256.txt").write_text(
        "".join(
            f"{digest}  {relative}\n"
            for relative, digest in certification_hashes.items()
        ),
        encoding="utf-8",
    )

    summary = {
        "schema_version": 1,
        "package": "gate-0.5-step05-substrate-certification-handoff",
        "package_version": PACKAGE_VERSION,
        "run_id": run_dir.name,
        "status": "pass",
        "shared_substrate_certified": True,
        "gate_0_5_complete": False,
        "controlled_preflight": True,
        "framework_execution_claimed": False,
        "model_call_performed": False,
        "operations_exercised": [
            "find_images_needing_review",
            "get_image_context",
            "submit_recommendation",
            "get_recommendation_status",
        ],
        "canonical_target_sequence": 1,
        "target_sequence_sha256": (
            lineage["step01"]["target_sequence_sha256"]
        ),
        "image_sha256": lineage["step02"]["image_sha256"],
        "context_evidence_hash": lineage["step02"]["context_evidence_hash"],
        "idempotent_replay_same_identity": True,
        "pending_status_reads_match": True,
        "discovery_and_context_read_only": True,
        "status_operation_read_only": True,
        "recommendation_only_mutation": True,
        "source_article_unchanged": True,
        "article_source_sha256": before["article_source_sha256"],
        "final_suggestion_count": 0,
        "final_reset_clean": True,
        "prior_evidence": lineage,
        "active_runtime_config_sha256": active_config_sha256,
        "freeze_manifest": FREEZE_MANIFEST,
        "freeze_manifest_sha256": manifest_sha,
        "frozen_files": frozen_hashes,
        "certification_files": certification_hashes,
        "framework_vertical_slices": {
            "drupal_ai": "not certified",
            "langgraph": "not certified",
            "crewai": "not certified",
        },
        "next_step": "Drupal AI Gate 0.5 one-image vertical slice",
    }
    write_json(run_dir / "summary.json", summary)

    (run_dir / "summary.md").write_text(
        f"""# Gate 0.5 Step 05 Shared Substrate Certification

- **Status:** PASS
- **Run ID:** `{run_dir.name}`
- **Shared substrate:** certified
- **Overall Gate 0.5:** in progress
- **Operations exercised:** all four
- **Canonical target:** sequence 1
- **Source Article changed:** no
- **Final suggestion count:** 0
- **Model call performed:** no
- **Framework execution claimed:** no
- **Freeze manifest SHA-256:** `{manifest_sha}`

## Framework status

- Drupal AI: not certified
- LangGraph: not certified
- CrewAI: not certified

## Frozen handoff

- `{FREEZE_MANIFEST}`
- `{FREEZE_DIGEST}`
- `docs/handoffs/GATE-0.5-FRAMEWORK-HANDOFF.md`

## Next step

Implement the Drupal AI one-image vertical slice against the frozen substrate.
""",
        encoding="utf-8",
    )

    scan_for_secrets(run_dir)
    scan_for_secrets(repo / "shared/contracts")


def audit(repo: Path, run_dir: Path, active_config_path: Path) -> None:
    summary = load_json(run_dir / "summary.json")
    if (
        not isinstance(summary, dict)
        or summary.get("status") != "pass"
        or summary.get("shared_substrate_certified") is not True
        or summary.get("gate_0_5_complete") is not False
        or summary.get("controlled_preflight") is not True
        or summary.get("framework_execution_claimed") is not False
        or summary.get("model_call_performed") is not False
        or summary.get("operations_exercised") != [
            "find_images_needing_review",
            "get_image_context",
            "submit_recommendation",
            "get_recommendation_status",
        ]
        or summary.get("final_suggestion_count") != 0
        or summary.get("final_reset_clean") is not True
    ):
        raise EvidenceError("Latest Step 05 summary controls failed.")

    required = [
        "summary.json",
        "summary.md",
        "route-matrix.json",
        "active-config.json",
        "environment.json",
        "find-response.json",
        "target-1.json",
        "context-sanitized.json",
        "context-runtime-verification.json",
        "submission-request.json",
        "submit-response.json",
        "submit-replay-response.json",
        "status-uuid.json",
        "status-nid.json",
        "status-repeat.json",
        "recommendation-inspection.json",
        "source-before.json",
        "source-after-reads.json",
        "source-after-submit.json",
        "source-after-status.json",
        "source-final-clean.json",
        "setup.log",
        "reset-before.log",
        "reset-after.log",
        "find-client.log",
        "context-client.log",
        "submit-client.log",
        "replay-client.log",
        "status-client.log",
        "GATE05-SUBSTRATE-FREEZE.json",
        "GATE05-SUBSTRATE-FREEZE.sha256",
        "frozen-files-sha256.txt",
        "certification-files-sha256.txt",
    ]
    for filename in required:
        if not (run_dir / filename).is_file():
            raise EvidenceError(f"Missing retained Step 05 evidence: {filename}")

    retained_active_config = validate_active_config(
        load_json(run_dir / "active-config.json")
    )
    current_active_config = validate_active_config(
        load_json(active_config_path)
    )
    active_config_sha256 = canonical_json_sha256(current_active_config)
    if (
        current_active_config != retained_active_config
        or active_config_sha256
        != summary.get("active_runtime_config_sha256")
    ):
        raise EvidenceError(
            "Active Drupal queue configuration changed after certification."
        )

    manifest_path = repo / FREEZE_MANIFEST
    digest_path = repo / FREEZE_DIGEST
    manifest = load_json(manifest_path)
    digest_line = digest_path.read_text(encoding="utf-8").strip()
    current_manifest_sha = sha256_bytes(manifest_path.read_bytes())
    expected_digest = f"{current_manifest_sha}  {FREEZE_MANIFEST}"
    if (
        digest_line != expected_digest
        or current_manifest_sha != summary.get("freeze_manifest_sha256")
        or manifest != load_json(run_dir / "GATE05-SUBSTRATE-FREEZE.json")
    ):
        raise EvidenceError("Freeze manifest digest or retained copy is invalid.")

    freeze_paths = expand_freeze_files(repo)
    current_hashes = file_hashes(repo, freeze_paths)
    if (
        current_hashes != manifest.get("frozen_files")
        or current_hashes != summary.get("frozen_files")
    ):
        raise EvidenceError(
            "A frozen shared-substrate file changed after certification."
        )

    certification_hashes = file_hashes(repo, CERTIFICATION_FILES)
    if certification_hashes != summary.get("certification_files"):
        raise EvidenceError(
            "A Step 05 certification script or handoff document changed."
        )

    before = validate_snapshot(
        load_json(run_dir / "source-before.json"),
        "before",
    )
    final = validate_snapshot(
        load_json(run_dir / "source-final-clean.json"),
        "final",
    )
    if before != final or final["suggestion_count"] != 0:
        raise EvidenceError("Retained final reset evidence is invalid.")

    manifest_active = manifest.get("active_runtime_config")
    if (
        not isinstance(manifest_active, dict)
        or manifest_active.get("sha256") != active_config_sha256
        or manifest_active.get("source")
        != "drupal/scripts/gate05-step05-config.php"
    ):
        raise EvidenceError("Freeze manifest active configuration is invalid.")

    if manifest.get("gate_0_5_complete") is not False:
        raise EvidenceError("Freeze manifest overclaims overall Gate 0.5.")
    slices = manifest.get("framework_vertical_slices")
    if (
        not isinstance(slices, dict)
        or set(slices) != {"drupal_ai", "langgraph", "crewai"}
        or any(
            not isinstance(entry, dict)
            or entry.get("certified") is not False
            for entry in slices.values()
        )
    ):
        raise EvidenceError("Freeze manifest overclaims or malforms a framework slice.")

    scan_for_secrets(run_dir)
    scan_for_secrets(repo / "shared/contracts")

    print(json.dumps({
        "status": "pass",
        "run_id": run_dir.name,
        "shared_substrate_certified": True,
        "gate_0_5_complete": False,
        "operations_exercised": summary["operations_exercised"],
        "canonical_target_sequence": 1,
        "source_article_unchanged": True,
        "final_suggestion_count": 0,
        "freeze_manifest_sha256": current_manifest_sha,
        "frozen_files_match": True,
        "active_runtime_config_sha256": active_config_sha256,
        "active_runtime_config_matches": True,
        "framework_vertical_slices": summary["framework_vertical_slices"],
        "next_step": summary["next_step"],
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
    audit_parser.add_argument("--active-config", required=True)

    args = parser.parse_args()
    try:
        repo = Path(args.repo).resolve()
        run_dir = Path(args.run_dir).resolve()
        if args.command == "evaluate":
            evaluate(repo, run_dir)
        else:
            audit(
                repo,
                run_dir,
                Path(args.active_config).resolve(),
            )
    except EvidenceError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
