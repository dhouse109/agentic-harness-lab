#!/usr/bin/env python3
"""Audit the static Gate 1 Step 1.01 contract without executing a framework."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import re
from pathlib import Path
from typing import Any

import jsonschema
from referencing import Registry, Resource


EXPECTED_JSONSCHEMA_VERSION = "4.26.0"
EXPECTED_COMMIT = "3016819f738a7db39fef0a6ccbb9cff0c8ec5fa0"
EXPECTED_GATE05_RUN = "gate05-step05-20260805T184155Z-50124"
EXPECTED_GATE05_SHA256 = "99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a"
EXPECTED_STEP01_RUN = "gate1-step01-20260805T205448Z-103220"
EXPECTED_SUPERSEDED_RUN = "gate1-step01-20260805T200619Z-87483"
EXPECTED_SUPERSEDED_MANIFEST_SHA256 = "b25ede2a20b8c94a2986806362df6b5b2b5b574c3a80953d175578985bdc9b06"
CONTRACT_RELATIVE = "shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json"
CONTRACT_SHA_RELATIVE = "shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.sha256"
NEW_SCHEMA_NAMES = (
    "drupal-ai-run-state.schema.json",
    "drupal-ai-model-output.schema.json",
    "batch-target-sequence.schema.json",
    "batch-event.schema.json",
    "batch-tool-traces.schema.json",
    "batch-model-outputs.schema.json",
    "batch-recommendations.schema.json",
    "batch-validation.schema.json",
    "batch-submissions.schema.json",
    "batch-statuses.schema.json",
    "batch-human-review.schema.json",
    "batch-recovery.schema.json",
    "batch-summary.schema.json",
)
BASE_SCHEMA_NAMES = (
    "target.schema.json",
    "image-context.schema.json",
    "recommendation.schema.json",
    "tool-result.schema.json",
    "run-state.schema.json",
)


class AuditError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AuditError(f"Missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AuditError(f"Invalid JSON: {path}") from exc


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_terminal_newline(path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise AuditError(f"File is not valid UTF-8: {path}") from exc
    if not text.endswith("\n") or text != text.rstrip(" \t\r\n") + "\n":
        raise AuditError(f"JSON file must end with exactly one terminal newline: {path}")


def verify_superseded_run(repo: Path) -> None:
    run_dir = repo / "evidence/gates/gate-1/drupal-ai-batch-contract" / EXPECTED_SUPERSEDED_RUN
    manifest = run_dir / "package-files-sha256.txt"
    if sha256(manifest) != EXPECTED_SUPERSEDED_MANIFEST_SHA256:
        raise AuditError("Superseded v1.0.0 evidence manifest changed")
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split(maxsplit=1)
        if sha256(run_dir / relative) != expected:
            raise AuditError(f"Superseded v1.0.0 evidence changed: {relative}")


def resolve(repo: Path, overlay: Path | None, relative: str) -> Path:
    if overlay is not None:
        candidate = overlay / relative
        if candidate.is_file():
            return candidate
    return repo / relative


def package_sequence(contract: dict[str, Any]) -> list[tuple[str, str]]:
    """Return the frozen Gate 1 step/name sequence from the machine contract."""
    raw_sequence = contract.get("package_sequence", [])
    sequence: list[tuple[str, str]] = []
    for item in raw_sequence:
        if not isinstance(item, dict) or not isinstance(item.get("step"), str) or not isinstance(item.get("name"), str):
            raise AuditError("Invalid repository-native Gate 1 package sequence entry")
        sequence.append((item["step"], item["name"]))
    if not sequence or len({step for step, _ in sequence}) != len(sequence):
        raise AuditError("Repository-native Gate 1 package sequence is empty or ambiguous")
    return sequence


def next_package_steps(document: str, label: str, allowed_steps: set[str]) -> set[str]:
    """Extract Gate 1 steps explicitly named as the next package."""
    pattern = re.compile(
        r"next\s+package(?:\s+after\s+commit)?(?:\s+is)?.{0,100}?"
        r"(gate-1-step(?P<number>[0-9]{2})-[a-z0-9-]+-v[0-9]+\.[0-9]+\.[0-9]+)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    steps = {f"1.{match.group('number')}" for match in pattern.finditer(document)}
    plain_pattern = re.compile(r"\bStep (1\.[0-9]{2})\s+(?:is\s+)?(?:the\s+)?next\b", flags=re.IGNORECASE)
    steps.update(match.group(1) for match in plain_pattern.finditer(document))
    unknown = sorted(steps - allowed_steps)
    if unknown:
        raise AuditError(f"{label} names a next package outside the frozen Gate 1 sequence: {unknown}")
    if len(steps) > 1:
        raise AuditError(f"{label} names contradictory Gate 1 next packages: {sorted(steps)}")
    return steps


def document_marks_step_complete(document: str, step: str) -> bool:
    """Recognize explicit same-line completion wording for one Gate 1 step."""
    token = re.escape(f"Step {step}")
    bare = re.escape(step)
    patterns = (
        rf"(?im)^.*\bcomplete(?:d)?\b[^\n]*{token}[^\n]*$",
        rf"(?im)^.*{token}[^\n]*\bcomplete(?:d)?\b[^\n]*$",
        rf"(?im)^.*\bpackages?\b[^\n]*{bare}[^\n]*\bcomplete(?:d)?\b[^\n]*$",
    )
    return any(re.search(pattern, document) for pattern in patterns)


def validate_completed_document_progression(
    contract: dict[str, Any],
    plan_document: str,
    readme_document: str,
    status_document: str,
    accepted_run: str,
    accepted_digest: str,
) -> dict[str, Any]:
    """Validate Step 1.01 completion while allowing only forward Gate 1 progression."""
    sequence = package_sequence(contract)
    allowed_steps = {step for step, _ in sequence}
    checklist_pattern = re.compile(r"^- \[([ xX])\] Step (1\.[0-9]{2}) — (.+)$", flags=re.MULTILINE)
    checklist = [(match.group(2), match.group(3), match.group(1).lower() == "x") for match in checklist_pattern.finditer(plan_document)]
    expected_checklist = [(step, name) for step, name in sequence]
    if [(step, name) for step, name, _ in checklist] != expected_checklist:
        raise AuditError("PLAN.md Gate 1 checklist differs from the frozen machine-readable package sequence")

    completed_flags = [completed for _, _, completed in checklist]
    first_incomplete = next((index for index, completed in enumerate(completed_flags) if not completed), len(completed_flags))
    if any(completed_flags[first_incomplete:]):
        raise AuditError("PLAN.md completed-step markers form an impossible Gate 1 sequence")
    if not completed_flags[0]:
        raise AuditError("PLAN.md does not record Step 1.01 as complete")

    stale_patterns = (
        r"Step 1\.01[^\n]{0,100}not yet run",
        r"Step 1\.01[^\n]{0,100}remains active",
        r"Package 1\.01[^\n]{0,100}active",
        r"Active package[^\n]{0,160}gate-1-step01",
        r"pending successful v1\.0\.1 runner",
    )
    for label, document in (
        ("PLAN.md", plan_document),
        ("README.md", readme_document),
        ("docs/CURRENT-STATUS.md", status_document),
    ):
        if accepted_run not in document:
            raise AuditError(f"Accepted Step 1.01 run missing from {label}")
        if accepted_digest not in document:
            raise AuditError(f"Accepted Step 1.01 contract digest missing from {label}")
        for pattern in stale_patterns:
            if re.search(pattern, document, flags=re.IGNORECASE):
                raise AuditError(f"{label} retains stale Step 1.01 active, pending, or not-yet-run prose")

    completed_steps = [step for step, _, completed in checklist if completed]
    incomplete_steps = [step for step, _, completed in checklist if not completed]
    for label, document in (("README.md", readme_document), ("docs/CURRENT-STATUS.md", status_document)):
        for step in completed_steps:
            if not document_marks_step_complete(document, step):
                raise AuditError(f"{label} disagrees with PLAN.md about completed {step}")
        for step in incomplete_steps:
            if document_marks_step_complete(document, step):
                raise AuditError(f"{label} marks incomplete {step} as complete")

    next_steps = {
        label: next_package_steps(document, label, allowed_steps)
        for label, document in (
            ("PLAN.md", plan_document),
            ("README.md", readme_document),
            ("docs/CURRENT-STATUS.md", status_document),
        )
    }
    expected_next = None if first_incomplete == len(sequence) else sequence[first_incomplete][0]
    if expected_next is None:
        if any(next_steps.values()):
            raise AuditError("A next Gate 1 package is named after all frozen Gate 1 steps are complete")
    else:
        for label, steps in next_steps.items():
            if steps != {expected_next}:
                raise AuditError(f"{label} does not name frozen progression step {expected_next} as next")

    return {
        "completed_steps": completed_steps,
        "next_step": expected_next,
        "sequence_source": CONTRACT_RELATIVE,
        "sequence_length": len(sequence),
    }


def validate_instance(validator: jsonschema.Draft202012Validator, value: Any, label: str) -> None:
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.path))
    if errors:
        path = ".".join(str(part) for part in errors[0].absolute_path) or "<root>"
        raise AuditError(f"Schema validation failed for {label} at {path}: {errors[0].validator}")


def expect_invalid(validator: jsonschema.Draft202012Validator, value: Any, label: str) -> None:
    if validator.is_valid(value):
        raise AuditError(f"Negative schema control unexpectedly passed: {label}")


def example_target(sequence: int) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "sequence": sequence,
        "node_uuid": f"00000000-0000-4000-8000-{sequence:012d}",
        "revision_id": 100 + sequence,
        "field_name": "field_image",
        "delta": 0,
        "file_uuid": f"10000000-0000-4000-8000-{sequence:012d}",
        "target_state": "missing" if sequence <= 9 else "poor",
        "existing_alt": None if sequence <= 9 else "image",
    }


def build_examples() -> dict[str, dict[str, Any]]:
    run_id = "drupal_ai-20260805T190000Z-a1b2"
    timestamp = "2026-08-05T19:00:00Z"
    targets = [example_target(sequence) for sequence in range(1, 13)]
    model_outputs = []
    recommendations = []
    validations = []
    submissions = []
    for sequence, target in enumerate(targets, start=1):
        model_output = {"proposed_alt_text": f"Descriptive alt text for target {sequence}"}
        model_outputs.append({"sequence": sequence, "target": target, "model_output": model_output})
        recommendations.append(
            {
                "sequence": sequence,
                "target": target,
                "recommendation": {
                    "schema_version": 1,
                    "target": target,
                    "proposed_alt_text": model_output["proposed_alt_text"],
                    "source_framework": "drupal_ai",
                    "run_id": run_id,
                    "evidence_hash": "sha256:" + f"{sequence:064x}",
                    "validator_version": "gate05-validator-1.0.0",
                },
            }
        )
        submissions.append(
            {
                "sequence": sequence,
                "target": target,
                "node_id": 200 + sequence,
                "uuid": f"20000000-0000-4000-8000-{sequence:012d}",
                "revision_id": 300 + sequence,
                "initial_status": "pending",
                "idempotent_replay_same_identity": True,
            }
        )
        validations.append(
            {
                "sequence": sequence,
                "target": target,
                "structured_output_schema_valid": True,
                "deterministic_validation_passed": True,
                "errors": [],
            }
        )

    run_state = {
        "schema_version": 1,
        "run_id": run_id,
        "framework_origin": "drupal_ai",
        "status": "completed",
        "target_sequence_hash": "sha256:1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728",
        "next_target_index": 12,
        "completed_target_identities": targets,
        "recommendation_ids": [
            {"sequence": item["sequence"], "node_id": item["node_id"], "uuid": item["uuid"], "revision_id": item["revision_id"]}
            for item in submissions
        ],
        "validation_results": validations,
        "started_at": timestamp,
        "updated_at": "2026-08-05T19:02:00Z",
        "completed_at": "2026-08-05T19:02:00Z",
        "interrupted_at": "2026-08-05T19:01:00Z",
        "resumed_at": "2026-08-05T19:01:30Z",
        "failure_injection_armed": True,
        "failure_injection_fired": True,
        "prompt_version": "drupal-ai-alt-text-v1.0.0",
        "model_id": "gpt-4.1-mini-2025-04-14",
    }

    return {
        "drupal-ai-model-output.schema.json": model_outputs[0]["model_output"],
        "drupal-ai-run-state.schema.json": run_state,
        "batch-target-sequence.schema.json": {
            "schema_version": 1,
            "target_sequence_sha256": "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728",
            "targets": targets,
        },
        "batch-event.schema.json": {
            "schema_version": 1,
            "event_index": 1,
            "event_type": "run_initialized",
            "run_id": run_id,
            "source_framework": "drupal_ai",
            "occurred_at": timestamp,
            "sequence": None,
            "correlation_id": "run-initialized",
            "target": None,
            "outcome": "started",
            "error_code": None,
        },
        "batch-tool-traces.schema.json": {
            "schema_version": 1,
            "run_id": run_id,
            "source_framework": "drupal_ai",
            "traces": [
                {
                    "operation": "find_images_needing_review",
                    "correlation_id": "find-1",
                    "started_at": timestamp,
                    "completed_at": timestamp,
                    "ok": True,
                    "sequence": None,
                    "target": None,
                    "result_sha256": "sha256:" + "a" * 64,
                    "recommendation_uuid": None,
                    "error": None,
                }
            ],
        },
        "batch-model-outputs.schema.json": {
            "schema_version": 1,
            "run_id": run_id,
            "framework_origin": "drupal_ai",
            "outputs": model_outputs,
        },
        "batch-recommendations.schema.json": {
            "schema_version": 1,
            "run_id": run_id,
            "source_framework": "drupal_ai",
            "recommendations": recommendations,
        },
        "batch-validation.schema.json": {
            "schema_version": 1,
            "run_id": run_id,
            "source_framework": "drupal_ai",
            "validator_version": "gate05-validator-1.0.0",
            "results": validations,
        },
        "batch-submissions.schema.json": {
            "schema_version": 1,
            "run_id": run_id,
            "framework_origin": "drupal_ai",
            "submissions": submissions,
        },
        "batch-statuses.schema.json": {
            "schema_version": 1,
            "run_id": run_id,
            "framework_origin": "drupal_ai",
            "observations": [{
                "recommendation_uuid": submissions[0]["uuid"],
                "revision_id": submissions[0]["revision_id"],
                "status": "pending",
                "observed_at": timestamp,
            }],
        },
        "batch-human-review.schema.json": {
            "schema_version": 1,
            "run_id": run_id,
            "framework_origin": "drupal_ai",
            "decisions": [{
                "recommendation_uuid": submissions[0]["uuid"],
                "prior_revision_id": submissions[0]["revision_id"],
                "decision_revision_id": submissions[0]["revision_id"] + 1,
                "reviewer": "editor_dana",
                "decision": "approved",
                "prior_text_sha256": "sha256:" + "b" * 64,
                "decided_text_sha256": "sha256:" + "b" * 64,
                "reviewed_at": timestamp,
                "source_article_unchanged": True,
            }],
        },
        "batch-recovery.schema.json": {
            "schema_version": 1,
            "run_id": run_id,
            "source_framework": "drupal_ai",
            "failure_after_sequence": 6,
            "failure_before_sequence": 7,
            "completed_before_failure": [1, 2, 3, 4, 5, 6],
            "interrupted_at": timestamp,
            "resumed_at": "2026-08-05T19:01:00Z",
            "resumed_with_run_id": run_id,
            "resumed_at_sequence": 7,
            "duplicate_count": 0,
            "completed_after_resume": [7, 8, 9, 10, 11, 12],
        },
        "batch-summary.schema.json": {
            "schema_version": 1,
            "status": "pass",
            "run_id": run_id,
            "source_framework": "drupal_ai",
            "provider": "OpenAI",
            "model": "gpt-4.1-mini-2025-04-14",
            "temperature": 0.0,
            "target_count": 12,
            "completed_count": 12,
            "failed_count": 0,
            "duplicate_count": 0,
            "validator_version": "gate05-validator-1.0.0",
            "review_destination": "alt_text_suggestion",
            "source_article_unchanged": True,
            "automatic_publication_performed": False,
            "failure_seam_observed": True,
            "resume_sequence": 7,
            "started_at": timestamp,
            "completed_at": "2026-08-05T19:02:00Z",
            "human_review_completed": True,
        },
    }


def verify_secret_hygiene(paths: list[Path]) -> None:
    patterns = (
        re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(r"data:" + r"image/", re.IGNORECASE),
        re.compile(r"Authorization" + r"\s*:", re.IGNORECASE),
        re.compile(r"Basic" + r"\s+[A-Za-z0-9+/]{16,}={0,2}"),
        re.compile(r"OPENAI_API_KEY" + r"\s*=\s*[^\s$<{]+"),
    )
    for path in paths:
        if path.name == "gate1_step01_audit.py":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(pattern.search(text) for pattern in patterns):
            raise AuditError(f"Potential secret-bearing content found: {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--overlay", type=Path)
    parser.add_argument("--document-state", choices=("active", "complete"), default="active")
    args = parser.parse_args()
    repo = args.repo.resolve()
    overlay = args.overlay.resolve() if args.overlay else None

    if importlib.metadata.version("jsonschema") != EXPECTED_JSONSCHEMA_VERSION:
        raise AuditError(f"Expected locked jsonschema {EXPECTED_JSONSCHEMA_VERSION}")

    gate05_sha = (repo / "shared/contracts/GATE05-SUBSTRATE-FREEZE.sha256").read_text(encoding="utf-8").split()[0]
    if gate05_sha != EXPECTED_GATE05_SHA256 or sha256(repo / "shared/contracts/GATE05-SUBSTRATE-FREEZE.json") != gate05_sha:
        raise AuditError("Gate 0.5 freeze digest does not match the authorized predecessor")
    latest = (repo / "evidence/gates/gate-0.5/substrate-certification/GATE05-STEP05-LATEST.txt").read_text(encoding="utf-8").strip()
    if Path(latest).name != EXPECTED_GATE05_RUN:
        raise AuditError("Gate 0.5 latest pointer is not the accepted predecessor run")
    gate05 = load_json(repo / "shared/contracts/GATE05-SUBSTRATE-FREEZE.json")
    if gate05.get("status") != "certified" or gate05.get("gate_0_5_complete") is not True:
        raise AuditError("Gate 0.5 freeze is not certified and complete")
    for relative, expected in gate05.get("frozen_files", {}).items():
        if sha256(repo / relative) != expected:
            raise AuditError(f"Frozen Gate 0.5 predecessor drift: {relative}")
    verify_superseded_run(repo)

    contract_path = resolve(repo, overlay, CONTRACT_RELATIVE)
    contract_sha_path = resolve(repo, overlay, CONTRACT_SHA_RELATIVE)
    expected_contract_sha, declared_relative = contract_sha_path.read_text(encoding="utf-8").split()
    if declared_relative != CONTRACT_RELATIVE or sha256(contract_path) != expected_contract_sha:
        raise AuditError("Gate 1 contract digest does not match")
    contract = load_json(contract_path)
    if contract.get("contract") != "gate1-drupal-ai-batch" or contract.get("contract_version") != "1.0.1":
        raise AuditError("Unexpected Gate 1 contract identity")
    if contract.get("predecessor", {}).get("commit") != EXPECTED_COMMIT:
        raise AuditError("Unexpected Gate 1 predecessor commit")
    if contract.get("predecessor", {}).get("gate05_freeze_sha256") != EXPECTED_GATE05_SHA256:
        raise AuditError("Unexpected Gate 1 predecessor freeze digest")
    if contract.get("publication_repair") != {
        "package_version": "1.0.1",
        "superseded_package_version": "1.0.0",
        "superseded_run_id": EXPECTED_SUPERSEDED_RUN,
        "superseded_run_preserved": True,
        "supersession_reasons": [
            "terminal blank-line errors in newly created schemas",
            "main-only installed audit mode blocked publication-branch validation",
        ],
        "contract_semantics_changed": False,
        "accepted_publication_baseline_set_by_passing_runner": True,
    }:
        raise AuditError("Unexpected Step 1.01 publication-repair metadata")
    expected_constants = {
        "provider": "OpenAI",
        "model": "gpt-4.1-mini-2025-04-14",
        "temperature": 0.0,
        "source_framework": "drupal_ai",
        "prompt_version": "drupal-ai-alt-text-v1.0.0",
        "validator_version": "gate05-validator-1.0.0",
        "review_destination": "alt_text_suggestion",
        "reviewer": "editor_dana",
        "source_article_mutation": "prohibited",
        "automatic_publication": "prohibited",
        "failure_after_sequence": 6,
        "failure_before_sequence": 7,
        "resume_at_sequence": 7,
        "expected_duplicate_count": 0,
    }
    if contract.get("frozen_constants") != expected_constants:
        raise AuditError("Frozen Gate 1 constants changed")
    if [item.get("name") for item in contract.get("shared_operations", [])] != [
        "find_images_needing_review", "get_image_context", "submit_recommendation", "get_recommendation_status"
    ]:
        raise AuditError("Shared operation order or identity changed")
    if contract.get("canonical_schemas") != {
        "framework_owned_run_state": "shared/schemas/drupal-ai-run-state.schema.json",
        "raw_structured_model_output": "shared/schemas/drupal-ai-model-output.schema.json",
    }:
        raise AuditError("Canonical Drupal AI schema entry points changed")
    state_ownership = contract.get("state_ownership", {})
    if state_ownership.get("runtime_storage_owner") != "drupal_ai" or state_ownership.get("runtime_storage_location") != "deferred_to_step_1_02" or state_ownership.get("shared_runtime_storage_prohibited") is not True:
        raise AuditError("Framework-owned state storage boundary changed")
    expected_stages = [
        "raw_structured_model_output",
        "assembled_recommendation",
        "deterministic_validator_result",
        "submitted_recommendation",
        "recommendation_status",
        "human_review_decision",
    ]
    if [item.get("stage") for item in contract.get("lifecycle_stages", [])] != expected_stages:
        raise AuditError("Lifecycle evidence stages are not distinct and ordered")
    if contract.get("lifecycle_stage_combination_prohibited") is not True or contract.get("hidden_reasoning_capture_prohibited") is not True:
        raise AuditError("Lifecycle separation or hidden-reasoning prohibition changed")
    expected_sequence = ["batch contract", "pinned Drupal AI runtime probe", "thin Drupal AI tool adapters", "canonical vertical slice", "12-target batch runner", "batch evidence and human review", "certification, freeze, and handoff"]
    if [item.get("name") for item in contract.get("package_sequence", [])] != expected_sequence:
        raise AuditError("Repository-native Gate 1 package sequence changed")
    adr_policy = contract.get("adr_policy", {})
    if adr_policy.get("currently_expected") != "ADR-0006" or adr_policy.get("overwrite_existing_adr") is not False:
        raise AuditError("Step 1.02 ADR numbering policy changed")

    inputs = contract.get("contract_inputs", {})
    if not isinstance(inputs, dict) or len(inputs) != 19:
        raise AuditError("Expected exactly 19 hash-addressed contract inputs")
    for relative, expected in inputs.items():
        if sha256(resolve(repo, overlay, relative)) != expected:
            raise AuditError(f"Contract input hash mismatch: {relative}")

    verify_terminal_newline(contract_path)
    for name in NEW_SCHEMA_NAMES:
        verify_terminal_newline(resolve(repo, overlay, f"shared/schemas/{name}"))

    schemas: dict[str, dict[str, Any]] = {}
    resources: list[tuple[str, Resource[Any]]] = []
    for name in BASE_SCHEMA_NAMES + NEW_SCHEMA_NAMES:
        schema = load_json(resolve(repo, overlay, f"shared/schemas/{name}"))
        if not isinstance(schema, dict) or schema.get("$id") != name:
            raise AuditError(f"Invalid schema identity: {name}")
        jsonschema.Draft202012Validator.check_schema(schema)
        schemas[name] = schema
        resources.append((name, Resource.from_contents(schema)))
    registry = Registry().with_resources(resources)
    validators = {
        name: jsonschema.Draft202012Validator(schema, registry=registry, format_checker=jsonschema.FormatChecker())
        for name, schema in schemas.items()
    }
    examples = build_examples()
    for name, example in examples.items():
        validate_instance(validators[name], example, name)

    negative_controls = {
        "drupal-ai-run-state.schema.json": ("model_id", "different-model"),
        "batch-target-sequence.schema.json": ("target_sequence_sha256", "0" * 64),
        "batch-event.schema.json": ("source_framework", "langgraph"),
        "batch-validation.schema.json": ("validator_version", "other-validator"),
        "batch-recovery.schema.json": ("duplicate_count", 1),
        "batch-summary.schema.json": ("model", "different-model"),
    }
    for name, (field, invalid_value) in negative_controls.items():
        bad = copy.deepcopy(examples[name])
        bad[field] = invalid_value
        expect_invalid(validators[name], bad, f"{name}:{field}")
    bad_model_output = copy.deepcopy(examples["drupal-ai-model-output.schema.json"])
    bad_model_output["chain_of_thought"] = "not allowed"
    expect_invalid(validators["drupal-ai-model-output.schema.json"], bad_model_output, "hidden reasoning")
    bad_model_collection = copy.deepcopy(examples["batch-model-outputs.schema.json"])
    bad_model_collection["outputs"][0]["model_output"]["validator_passed"] = True
    expect_invalid(validators["batch-model-outputs.schema.json"], bad_model_collection, "combined validator result")
    bad_recommendations = copy.deepcopy(examples["batch-recommendations.schema.json"])
    bad_recommendations["recommendations"][0]["node_id"] = 999
    expect_invalid(validators["batch-recommendations.schema.json"], bad_recommendations, "combined submission identity")
    bad_submission = copy.deepcopy(examples["batch-submissions.schema.json"])
    bad_submission["submissions"][0]["initial_status"] = "approved"
    expect_invalid(validators["batch-submissions.schema.json"], bad_submission, "non-pending submission")
    bad_status = copy.deepcopy(examples["batch-statuses.schema.json"])
    bad_status["observations"][0]["reviewer"] = "editor_dana"
    expect_invalid(validators["batch-statuses.schema.json"], bad_status, "combined human reviewer")
    bad_review = copy.deepcopy(examples["batch-human-review.schema.json"])
    bad_review["decisions"][0]["reviewer"] = "agent_bot"
    expect_invalid(validators["batch-human-review.schema.json"], bad_review, "wrong reviewer")
    bad_trace = copy.deepcopy(examples["batch-tool-traces.schema.json"])
    bad_trace["traces"][0]["operation"] = "private_write"
    expect_invalid(validators["batch-tool-traces.schema.json"], bad_trace, "private operation")

    gate_document = resolve(repo, overlay, "docs/gates/GATE-1-STEP01-DRUPAL-AI-BATCH-CONTRACT.md").read_text(encoding="utf-8")
    plan_document = resolve(repo, overlay, "PLAN.md").read_text(encoding="utf-8")
    readme_document = resolve(repo, overlay, "README.md").read_text(encoding="utf-8")
    status_document = resolve(repo, overlay, "docs/CURRENT-STATUS.md").read_text(encoding="utf-8")
    combined = "\n".join((gate_document, plan_document, readme_document, status_document))
    for required in (
        "drupal-ai-run-state.schema.json",
        "drupal-ai-model-output.schema.json",
        "Step 1.02 — pinned Drupal AI runtime probe",
        "Step 1.07 — certification, freeze, and handoff",
        "ADR-0006",
        EXPECTED_GATE05_RUN,
        EXPECTED_GATE05_SHA256,
    ):
        if required not in combined:
            raise AuditError(f"Required Gate 1 documentation control missing: {required}")
    document_progression: dict[str, Any] = {
        "completed_steps": [],
        "next_step": "1.01",
        "sequence_source": CONTRACT_RELATIVE,
        "sequence_length": len(package_sequence(contract)),
    }
    if args.document_state == "active":
        if "Step 1.01 execution:** not yet run" not in status_document or "Active package:** `gate-1-step01-drupal-ai-batch-contract-v1.0.1`" not in status_document:
            raise AuditError("CURRENT-STATUS.md is not in the required pre-run active state")
        if "- [ ] Step 1.01 — batch contract" not in plan_document or "not yet run" not in readme_document or "pending successful v1.0.1 runner" not in combined:
            raise AuditError("PLAN.md or README.md is not in the required pre-run active state")
    else:
        latest_step01 = (repo / "evidence/gates/gate-1/drupal-ai-batch-contract/GATE1-STEP01-LATEST.txt").read_text(encoding="utf-8").strip()
        accepted_run = Path(latest_step01).name
        if accepted_run != EXPECTED_STEP01_RUN:
            raise AuditError("Accepted Step 1.01 evidence pointer changed")
        accepted_digest = expected_contract_sha
        document_progression = validate_completed_document_progression(
            contract,
            plan_document,
            readme_document,
            status_document,
            accepted_run,
            accepted_digest,
        )

    audit_paths = [contract_path, contract_sha_path]
    audit_paths.extend(resolve(repo, overlay, f"shared/schemas/{name}") for name in NEW_SCHEMA_NAMES)
    audit_paths.extend(resolve(repo, overlay, relative) for relative in ("docs/gates/GATE-1-STEP01-DRUPAL-AI-BATCH-CONTRACT.md", "PLAN.md", "README.md", "docs/CURRENT-STATUS.md"))
    verify_secret_hygiene(audit_paths)

    print(json.dumps({
        "status": "pass",
        "package": "gate-1-step01-drupal-ai-batch-contract",
        "package_version": "1.0.1",
        "predecessor_commit": EXPECTED_COMMIT,
        "gate05_run_id": EXPECTED_GATE05_RUN,
        "gate05_freeze_sha256": EXPECTED_GATE05_SHA256,
        "contract_sha256": expected_contract_sha,
        "contract_inputs_verified": len(inputs),
        "schemas_validated": len(schemas),
        "positive_examples_validated": len(examples),
        "negative_controls_rejected": 13,
        "canonical_schemas_validated": 2,
        "lifecycle_stages_validated": 6,
        "json_terminal_formatting_validated": 14,
        "superseded_run_id": EXPECTED_SUPERSEDED_RUN,
        "superseded_run_preserved": True,
        "contract_semantics_changed": False,
        "document_state": args.document_state,
        "document_progression": document_progression,
        "jsonschema_version": EXPECTED_JSONSCHEMA_VERSION,
        "model_call_performed": False,
        "drupal_state_mutated": False,
        "dependency_change": False,
        "gate05_recertified": False,
        "step02_started_by_step01_package": False,
        "step02_started_scope": "historical Step 1.01 package action; not repository current state",
        "secret_hygiene": "pass",
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as exc:
        print(f"[ERROR] {exc}")
        raise SystemExit(1) from exc
