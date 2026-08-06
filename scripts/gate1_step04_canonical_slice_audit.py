#!/usr/bin/env python3
"""Static and retained-evidence audit for Gate 1 Step 1.04."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, RefResolver

EXPECTED_BASELINE = "da08ef1f41dc480d7bcdcba08d020f9d3aae2387"
TARGET_SHA = "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728"
SOURCE_SHA = "f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17"
ADR_HASHES = {
    "docs/decisions/ADR-0006-drupal-ai-programmatic-runtime-path.md": "223f6d6f4276d3861cf5668f08e0446479d815a07fed18402b1e6a7722d18c4b",
    "docs/decisions/ADR-0007-canonical-slice-evidence-image-and-state-boundary.md": "7a50db44fe626d10012a03f1bfa942f3592552f44397d57cb11af47a02f506bf",
    "docs/decisions/ADR-0008-file-entity-identity-and-uri-locator-boundary.md": "a759816304a9247dc8515cd7971569d37d42a960377696eaca27aa2df8828b3a",
}
PROFILE_HASHES = {
    "shared/profiles/gate1-drupal-ai-canonical-slice-v1.0.0/canonical-slice-profile.json": "fa7fabde016eef008c0be6bd7a166faa0e611a51dc9527d8e42dc45df0b0a306",
    "shared/profiles/gate1-drupal-ai-file-transport-clarification-v1.0.0/file-transport-clarification-profile.json": "54a074964b0aa36c3d8a05a1c8278aab4f67b5072846dd20d453234f19b479c4",
}
PAYLOAD = [
    "docs/gates/GATE-1-STEP04-DRUPAL-AI-CANONICAL-VERTICAL-SLICE.md",
    "drupal/web/modules/custom/agentic_harness_drupal_ai/src/Service/FileEntityResolver.php",
    "drupal/scripts/gate1-step04-canonical-vertical-slice.php",
    "scripts/gate1_step04_file_transport_clarification_audit.py",
    "scripts/gate1_step04_canonical_slice_audit.py",
    "scripts/gate1_step04_finalize.py",
    "scripts/run-gate1-step04-drupal-ai-canonical-vertical-slice.sh",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(f"[ERROR] {message}")


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def schema_validator(schema_path: Path, store_paths: list[Path]) -> Draft202012Validator:
    schema = load(schema_path)
    store: dict[str, Any] = {}
    for path in store_paths:
        value = load(path)
        store[path.name] = value
        store[path.as_uri()] = value
        if isinstance(value.get("$id"), str):
            store[value["$id"]] = value
    resolver = RefResolver(base_uri=schema_path.as_uri(), referrer=schema, store=store)
    return Draft202012Validator(schema, resolver=resolver, format_checker=FormatChecker())


def validate(validator: Draft202012Validator, value: Any, label: str) -> None:
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.path))
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.path)
        raise SystemExit(f"[ERROR] {label} schema validation failed at {location or '<root>'}: {first.message}")


def audit_source(repo: Path, overlay: Path) -> dict[str, Any]:
    for rel, expected in {**ADR_HASHES, **PROFILE_HASHES}.items():
        require(sha(repo / rel) == expected, f"Controlling file changed: {rel}")
    for rel in PAYLOAD:
        require((overlay / rel).is_file(), f"Missing Step 1.04 payload: {rel}")

    resolver = (overlay / PAYLOAD[1]).read_text(encoding="utf-8")
    runtime = (overlay / PAYLOAD[2]).read_text(encoding="utf-8")
    clarification = (overlay / PAYLOAD[3]).read_text(encoding="utf-8")
    runner = (overlay / PAYLOAD[6]).read_text(encoding="utf-8")
    for token in (
        "loadByProperties(['uuid' => $uuid])",
        "count($matches) !== 1",
        "getFilename() !== $image['filename']",
        "getMimeType() !== $image['mime_type']",
        "strlen($bytes) !== $image['byte_length']",
        "hash_equals($image['sha256']",
        "APPROVED_SCHEMES = ['public', 'private']",
        "Caller-supplied File locator or selector is prohibited",
    ):
        require(token in resolver, f"Missing File resolver control: {token}")

    for token in (
        "GATE1_STEP04_MODEL = 'gpt-4.1-mini-2025-04-14'",
        "GATE1_STEP04_TEMPERATURE = 0.0",
        "PreGenerateResponseEvent::EVENT_NAME",
        "Second provider request blocked",
        "'tools' => []",
        "'tool_usage_limits' => []",
        "'tool_settings' => []",
        "new Task(gate1_step04_user_prompt",
        "$task->setFiles([$file])",
        "$agent->determineSolvability()",
        "$agent->solve()",
        "awaiting_human_review",
        "editor_dana",
        "gate1_step04_delete_agent_config",
        "new FileEntityResolver(",
        "agentic_harness_tools.recommendation_validator",
        "idempotent_replay_same_identity",
    ):
        require(token in runtime, f"Missing runtime boundary: {token}")

    status_inputs = re.findall(
        r"gate1_step04_adapter\(\s*['\"]get_recommendation_status['\"]\s*,\s*['\"]([^'\"]+)['\"]",
        runtime,
    )
    require(
        status_inputs == ["recommendation_id", "recommendation_id", "recommendation_id"],
        f"Status adapter context names differ: {status_inputs}",
    )

    require(
        runtime.count("$targets = gate1_step04_discover_targets();") == 2,
        "Discovery adapter envelope is not unwrapped in preflight and start",
    )
    require(
        "$targets = gate1_step04_adapter('discover_targets')['data'];" not in runtime,
        "Broken direct discovery assignment remains",
    )
    for token in (
        "function gate1_step04_discover_targets(): array",
        "$data['targets']",
        "$data['total_count']",
        "$data['total_count'] !== count($targets)",
        "Discovery adapter data does not match the frozen envelope.",
    ):
        require(token in runtime, f"Missing discovery-envelope control: {token}")

    set_files_at = runtime.index("$task->setFiles([$file])")
    require("->toArray()" not in runtime[set_files_at:], "Post-image wrapper serialization is present")
    require("evidence/results/drupal_ai" not in runner, "Step 1.04 runner writes to batch evidence root")
    require("run-gate1-step05" not in runner, "Step 1.05 source is present in Step 1.04 runner")
    for command in ("preflight", "start", "status", "resume", "restore", "audit"):
        require(f"  {command})" in runner, f"Runner command missing: {command}")
    require("STEP04_PATHS" in clarification and "step_1_04_implementation_authorized" in clarification,
            "ADR-0008 audit is not progression-compatible")

    joined = "\n".join((overlay / rel).read_text(encoding="utf-8") for rel in PAYLOAD)
    for pattern in (
        r"curl\s", r"wget\s", r"api[_-]?key\s*[:=]\s*['\"][^'\"]+",
        r"data:image/[^;]+;base64,[A-Za-z0-9+/=]{32,}",
    ):
        require(re.search(pattern, joined, re.I) is None, f"Prohibited retained source pattern: {pattern}")

    require(not (repo / "scripts/run-gate1-step05-drupal-ai-batch-runner.sh").exists(), "Step 1.05 source exists")
    return {
        "status": "pass",
        "baseline": EXPECTED_BASELINE,
        "provider": "openai",
        "model": "gpt-4.1-mini-2025-04-14",
        "temperature": 0.0,
        "maximum_provider_requests": 1,
        "automatic_retries": 0,
        "model_callable_tools": 0,
        "canonical_target_sequence": 1,
        "target_sequence_sha256": TARGET_SHA,
        "article_source_sha256": SOURCE_SHA,
        "file_identity_fields": ["file_uuid", "filename", "mime_type", "byte_length", "sha256"],
        "local_stream_wrappers": ["public", "private"],
        "human_review_required": True,
        "step_1_05_absent": True,
    }


def audit_checksums(repo: Path, run_dir: Path) -> None:
    subprocess.run(["sha256sum", "-c", str(run_dir / "installed-files-sha256.txt")], cwd=repo, check=True,
                   stdout=subprocess.DEVNULL)
    subprocess.run(["sha256sum", "-c", "package-files-sha256.txt"], cwd=run_dir, check=True,
                   stdout=subprocess.DEVNULL)


def audit_lifecycle(repo: Path, lifecycle: dict[str, Any], state: dict[str, Any]) -> None:
    schemas = repo / "shared/schemas"
    profile = repo / "shared/profiles/gate1-drupal-ai-canonical-slice-v1.0.0"
    target_path = schemas / "target.schema.json"
    store = list(schemas.glob("*.json")) + list(profile.glob("*.json"))

    expected_keys = {
        "canonical_targets", "model_outputs", "recommendations", "validation_results",
        "submissions", "statuses", "human_review",
    }
    require(set(lifecycle) == expected_keys, "Lifecycle evidence properties differ from canonical profile")

    counts = {
        "canonical_targets": 1,
        "model_outputs": 1,
        "recommendations": 1,
        "validation_results": 1,
        "submissions": 1,
        "statuses": 2,
        "human_review": 1,
    }
    for key, expected in counts.items():
        require(isinstance(lifecycle[key], list) and len(lifecycle[key]) == expected,
                f"Lifecycle cardinality differs: {key}")

    validate(schema_validator(target_path, store), lifecycle["canonical_targets"][0], "canonical target")
    validate(schema_validator(schemas / "drupal-ai-model-output.schema.json", store),
             lifecycle["model_outputs"][0], "model output")
    validate(schema_validator(schemas / "recommendation.schema.json", store),
             lifecycle["recommendations"][0], "recommendation")

    validation_schema = load(schemas / "batch-validation.schema.json")["$defs"]["result"]
    validation_schema["properties"]["target"] = load(target_path)
    validate(Draft202012Validator(validation_schema, format_checker=FormatChecker()),
             lifecycle["validation_results"][0], "validation result")

    submission_schema = load(schemas / "batch-submissions.schema.json")["properties"]["submissions"]["items"]
    submission_schema["properties"]["target"] = load(target_path)
    validate(Draft202012Validator(submission_schema, format_checker=FormatChecker()),
             lifecycle["submissions"][0], "submission")

    status_schema = load(schemas / "batch-statuses.schema.json")["properties"]["observations"]["items"]
    for index, value in enumerate(lifecycle["statuses"]):
        validate(Draft202012Validator(status_schema, format_checker=FormatChecker()), value, f"status {index}")
    review_schema = load(schemas / "batch-human-review.schema.json")["properties"]["decisions"]["items"]
    validate(Draft202012Validator(review_schema, format_checker=FormatChecker()),
             lifecycle["human_review"][0], "human review")

    state_schema = load(profile / "canonical-slice-run-state.schema.json")
    state_schema["properties"]["canonical_target"] = load(target_path)
    validate(Draft202012Validator(state_schema, format_checker=FormatChecker()), state, "completed run state")


def audit_run(repo: Path, run_dir: Path) -> dict[str, Any]:
    source = audit_source(repo, repo)
    required = [
        "before-state.json", "start-result.json", "resume-result.json", "after-state.json",
        "lifecycle-evidence.json", "implementation-evidence.json", "completed-state.json",
        "summary.json", "summary.md", "installed-files-sha256.txt", "package-files-sha256.txt",
    ]
    for name in required:
        require((run_dir / name).is_file(), f"Missing retained evidence: {name}")

    audit_checksums(repo, run_dir)
    summary = load(run_dir / "summary.json")
    before = load(run_dir / "before-state.json")
    after = load(run_dir / "after-state.json")
    start = load(run_dir / "start-result.json")
    resume = load(run_dir / "resume-result.json")
    lifecycle = load(run_dir / "lifecycle-evidence.json")
    supplemental = load(run_dir / "implementation-evidence.json")
    state = load(run_dir / "completed-state.json")

    require(summary.get("status") == "pass", "Summary did not pass")
    require(start.get("provider_request_count") == 1, "Start did not make exactly one provider request")
    require(start.get("agent_request_count") == 1, "Start did not make exactly one AI Agent request")
    require(start.get("automatic_retries") == 0, "Automatic retry count changed")
    require(start.get("status") == "awaiting_human_review", "Start did not pause for human review")
    require(resume.get("provider_request_count") == 0, "Resume made a provider request")
    require(resume.get("agent_request_count") == 0, "Resume made an AI Agent request")
    require(resume.get("model_call_count_total") == 1, "Total model-call count changed")
    require(resume.get("approved_status", {}).get("reviewer_username") == "editor_dana", "Approval reviewer differs")
    require(before.get("seeded_clean") is True, "Before state was not seeded-clean")
    require(after.get("seeded_clean") is True, "After state was not seeded-clean")
    require(before.get("article_source_sha256") == SOURCE_SHA == after.get("article_source_sha256"),
            "Article source hash changed")
    require(before.get("target_sequence_sha256") == TARGET_SHA == after.get("target_sequence_sha256"),
            "Target sequence hash changed")
    require(after.get("suggestion_count") == 0, "Recommendation remained after restoration")
    require(after.get("runtime_state_present") is False, "Runtime state remained after restoration")
    require(after.get("temporary_agent_config_present") is False, "Temporary agent config remained after restoration")
    require(lifecycle["statuses"][0]["status"] == "pending", "First status was not pending")
    require(lifecycle["statuses"][1]["status"] == "approved", "Second status was not approved")
    require(lifecycle["human_review"][0]["reviewer"] == "editor_dana", "Human reviewer differs")
    require(lifecycle["human_review"][0]["source_article_unchanged"] is True, "Source mutation claim differs")
    require(supplemental.get("raw_image_retained") is False, "Raw image retention differs")
    require(supplemental.get("post_image_wrapper_serialization_performed") is False,
            "Post-image wrapper serialization was performed")
    encoded = json.dumps(supplemental, sort_keys=True)
    require(re.search(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]{16,}", encoded, re.I) is None,
            "Retained implementation evidence contains an image data URL")
    require(not any(key in supplemental.get("authorized_context", {}) for key in ("uri", "path", "resolved_path")),
            "Retained context contains a File locator")

    audit_lifecycle(repo, lifecycle, state)
    require("Step 1.04" in (repo / "README.md").read_text(encoding="utf-8"), "README status missing Step 1.04")
    require("gate-1-step05-drupal-ai-batch-runner-v1.0.0" in (repo / "PLAN.md").read_text(encoding="utf-8"),
            "PLAN did not advance to Step 1.05")
    require("gate-1-step05-drupal-ai-batch-runner-v1.0.0" in
            (repo / "docs/CURRENT-STATUS.md").read_text(encoding="utf-8"),
            "CURRENT-STATUS did not advance to Step 1.05")

    return source | {
        "evidence_run": run_dir.name,
        "retained_evidence_status": "pass",
        "seeded_clean_restored": True,
        "provider_request_count_start": 1,
        "provider_request_count_resume": 0,
        "reviewer_username": "editor_dana",
        "canonical_lifecycle_schema_valid": True,
        "completed_state_schema_valid": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--overlay", type=Path)
    parser.add_argument("--run-dir", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    overlay = args.overlay.resolve() if args.overlay else repo
    result = audit_run(repo, args.run_dir.resolve()) if args.run_dir else audit_source(repo, overlay)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
