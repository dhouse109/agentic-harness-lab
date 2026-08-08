#!/usr/bin/env python3
"""Static and retained-evidence audit for Gate 1 Step 1.05."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, RefResolver

BASELINE = "5e01aa49dcb253af429f984e46aa732656565c05"
TARGET_SHA = "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728"
SOURCE_SHA = "f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17"
CONTRACT_SHA = "360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6"
MODEL = "gpt-4.1-mini-2025-04-14"
PROVIDER = "OpenAI"
VALIDATOR = "gate05-validator-1.0.0"
RESULT_REQUIRED = [
    "run.json",
    "targets.json",
    "events.jsonl",
    "tool-traces.json",
    "model-outputs.json",
    "recommendations.json",
    "validation.json",
    "submissions.json",
    "statuses.json",
    "recovery.json",
    "summary.json",
    "summary.md",
]
SOURCE_PATHS = [
    "docs/gates/GATE-1-STEP05-DRUPAL-AI-BATCH-RUNNER.md",
    "drupal/scripts/gate1-step05-drupal-ai-batch-runner.php",
    "scripts/gate1_step05_batch_runner_audit.py",
    "scripts/gate1_step05_finalize.py",
    "scripts/run-gate1-step05-drupal-ai-batch-runner.sh",
]
STEP04_PROGRESSION = [
    "scripts/gate1_step04_boundary_reconciliation_audit.py",
    "scripts/gate1_step04_file_transport_clarification_audit.py",
    "scripts/gate1_step04_canonical_slice_audit.py",
    "scripts/run-gate1-step04-drupal-ai-canonical-vertical-slice.sh",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"[ERROR] {message}")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
        raise SystemExit(
            f"[ERROR] {label} schema validation failed at {location or '<root>'}: {first.message}"
        )


def audit_source(repo: Path, overlay: Path | None = None) -> dict[str, Any]:
    source_root = overlay.resolve() if overlay is not None else repo
    contract_path = repo / "shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json"
    require(contract_path.is_file(), "Batch contract is missing")
    require(sha(contract_path) == CONTRACT_SHA, "Frozen Gate 1 batch contract changed")
    contract = load(contract_path)
    require(contract.get("status") == "frozen", "Gate 1 batch contract is not frozen")
    for relative, expected in contract.get("contract_inputs", {}).items():
        path = repo / relative
        require(path.is_file(), f"Frozen contract input is missing: {relative}")
        require(sha(path) == expected, f"Frozen contract input changed: {relative}")
    constants = contract.get("frozen_constants", {})
    require(constants.get("provider") == "OpenAI", "Frozen provider differs")
    require(constants.get("model") == MODEL, "Frozen model differs")
    require(constants.get("temperature") == 0.0, "Frozen temperature differs")
    require(constants.get("failure_after_sequence") == 6, "Frozen failure-after seam differs")
    require(constants.get("failure_before_sequence") == 7, "Frozen failure-before seam differs")
    require(constants.get("resume_at_sequence") == 7, "Frozen resume seam differs")
    require(constants.get("expected_duplicate_count") == 0, "Frozen duplicate expectation differs")
    for rel in SOURCE_PATHS + STEP04_PROGRESSION:
        require((source_root / rel).is_file(), f"Missing Step 1.05/progression source: {rel}")

    runtime = (source_root / SOURCE_PATHS[1]).read_text(encoding="utf-8")
    runner = (source_root / SOURCE_PATHS[4]).read_text(encoding="utf-8")
    boundary = (source_root / STEP04_PROGRESSION[0]).read_text(encoding="utf-8")
    transport = (source_root / STEP04_PROGRESSION[1]).read_text(encoding="utf-8")
    canonical = (source_root / STEP04_PROGRESSION[2]).read_text(encoding="utf-8")
    step04_runner = (source_root / STEP04_PROGRESSION[3]).read_text(encoding="utf-8")

    runtime_tokens = (
        "GATE1_STEP05_MODEL = 'gpt-4.1-mini-2025-04-14'",
        "GATE1_STEP05_TEMPERATURE = 0.0",
        "GATE1_STEP05_FAILURE_AFTER_SEQUENCE = 6",
        "GATE1_STEP05_RESUME_SEQUENCE = 7",
        "GATE1_STEP05_TARGET_COUNT = 12",
        "GATE1_STEP05_MODERATION_PACING_SECONDS = 65",
        "batch.active",
        "batch.artifacts",
        "failure_injection_armed' => TRUE",
        "failure_injection_fired' => FALSE",
        "failure_injected",
        "run_resumed",
        "$task->setFiles([$file])",
        "$agent->determineSolvability()",
        "$agent->solve()",
        "Second provider request blocked for target sequence",
        "Second AI Agent request blocked for target sequence",
        "agentic_harness_tools.recommendation_validator",
        "submit_recommendation",
        "get_recommendation_status",
        "recommendation_id",
        "idempotent replay identity changed",
        "human_review_completed' => FALSE",
        "step_1_06_started' => FALSE",
        "proposed_alt_text_trimmed_length",
        "raw_output_retained' => FALSE",
        "StructuredOutputSchema",
        "ChatInput",
        "setChatStructuredJsonSchema",
        "gate1_step05_apply_provider_structured_output",
        "strict_provider_schema_preflight_verified",
        "raw_model_output_method' => 'solve'",
        "agent_structured_output_used_as_raw_model_output' => FALSE",
        "AgentResponseEvent",
        "getRawOutput",
        "gate1_step05_provider_response_metadata",
        "provider_response_metadata",
        "raw_provider_output_retained' => FALSE",
        "message_content_retained' => FALSE",
        "refusal_text_retained' => FALSE",
        "response_metadata_capture_preflight_verified",
        "AiExceptionEvent",
        "gate1_step05_provider_exception_diagnostic",
        "provider_exception_by_sequence",
        "provider_exception_diagnostic",
        "provider_exception_capture_preflight_verified",
        "provider_exception_message_retained' => FALSE",
        "provider_exception_input_retained' => FALSE",
        "RateLimitException",
        "ResponseInterface",
        "gate1_step05_rate_limit_response_diagnostic",
        "rate_limit_response_diagnostic",
        "rate_limit_response_diagnostics_preflight_verified",
        "rate_limit_response_body_retained' => FALSE",
        "rate_limit_response_headers_retained' => FALSE",
        "rate_limit_error_message_retained' => FALSE",
        "rate_limit_request_id_retained' => FALSE",
        "gate1_step05_apply_moderation_pacing",
        "sleep(GATE1_STEP05_MODERATION_PACING_SECONDS)",
        "moderation_rate_pacing_preflight_verified' => TRUE",
        "openai_moderation_enabled' => TRUE",
    )
    for token in runtime_tokens:
        require(token in runtime, f"Missing Step 1.05 runtime control: {token}")

    require("$agent->getStructuredOutput()" not in runtime,
            "Step 1.05 incorrectly uses AI Agents StructuredResultData as raw model output")
    require("gate1_step05_model_output($solved, $sequence, $provider_response_metadata)" in runtime,
            "Step 1.05 raw model output is not decoded from solve() with sanitized response metadata")
    require("$event->getResponse()->getRawOutput()" in runtime,
            "Step 1.05 does not capture provider response metadata through AgentResponseEvent")
    require("AiExceptionEvent::class" in runtime and "$event->getException()" in runtime,
            "Step 1.05 does not capture provider exceptions through AiExceptionEvent")
    require("provider_exception_diagnostic=" in runtime,
            "Step 1.05 provider-exception diagnostic seam is missing")
    require("$exception instanceof RateLimitException" in runtime and "$exception->response" in runtime,
            "Step 1.05 does not project the pinned openai-php 429 response")
    require("gate1_step05_apply_moderation_pacing($sequence);" in runtime,
            "Step 1.05 does not apply deterministic moderation pacing per target")
    require("disableModeration" not in runtime and "skip_moderation" not in runtime,
            "Step 1.05 must preserve the provider moderation pre-check")
    require("$response->getHeaderLine('x-ratelimit-limit-requests')" in runtime and
            "$response->getHeaderLine('x-ratelimit-limit-tokens')" in runtime,
            "Step 1.05 does not capture allowlisted OpenAI rate-limit headers")
    require("'raw_response_body_retained' => FALSE" in runtime and
            "'raw_response_headers_retained' => FALSE" in runtime and
            "'error_message_retained' => FALSE" in runtime and
            "'request_id_retained' => FALSE" in runtime,
            "Step 1.05 rate-limit projection does not preserve raw-response prohibitions")
    set_files_at = runtime.index("$task->setFiles([$file])")
    require("->toArray()" not in runtime[set_files_at:], "Post-image wrapper serialization is present")
    require(runtime.count("gate1_step05_process_target(") >= 3, "Batch target processor is not reused across start/resume")
    require("for ($index = 0; $index < GATE1_STEP05_FAILURE_AFTER_SEQUENCE; $index++)" in runtime,
            "Start phase does not stop at deterministic midpoint")
    require("for ($index = GATE1_STEP05_FAILURE_AFTER_SEQUENCE; $index < GATE1_STEP05_TARGET_COUNT; $index++)" in runtime,
            "Resume phase does not continue from sequence 7")

    for command in ("preflight", "start", "status", "resume", "promote", "restore", "audit"):
        require(f"  {command})" in runner, f"Step 1.05 runner command missing: {command}")
    require("evidence/results/drupal_ai" in runner, "Step 1.05 runner does not use frozen batch evidence root")
    require("human-review.json" in runner, "Step 1.05 runner does not explicitly guard the Step 1.06 review file")
    require("GATE1-STEP05-LATEST.txt" in runner and "GATE1-STEP05-LAST-RUN.txt" in runner,
            "Step 1.05 accepted evidence pointers are missing")
    for token in (
        "failure-status.json",
        "failure-summary.json",
        "after-failure-restore-state.json",
        "Sanitized failed-start diagnostic retained",
        "raw_model_output_retained",
        "provider_exception_diagnostic",
        "provider_exception_message_retained",
        "provider_input_retained",
        "rate_limit_response_body_retained",
        "rate_limit_response_headers_retained",
        "rate_limit_error_message_retained",
        "rate_limit_request_id_retained",
    ):
        require(token in runner, f"Step 1.05 failed-start diagnostic control missing: {token}")
    require("raw model output" not in runner.lower() or "never retain raw model output" in runner.lower(),
            "Step 1.05 failed-start path does not state raw-output retention prohibition")

    for text, label in (
        (boundary, "boundary reconciliation"),
        (transport, "file transport"),
        (canonical, "canonical slice"),
        (step04_runner, "Step 1.04 runner"),
    ):
        require("STEP 1.05 PROGRESSION" in text, f"{label} lacks explicit Step 1.05 progression marker")

    require(
        'EVIDENCE_ROOT="$REPO/evidence/gates/gate-1/drupal-ai-canonical-vertical-slice"' in step04_runner,
        "Step 1.04 runner canonical evidence root changed during Step 1.05 progression",
    )
    require(
        'EVIDENCE_ROOT="$REPO/evidence/results/drupal_ai"' not in step04_runner,
        "Step 1.04 runner was repointed to the Step 1.05 batch evidence root",
    )
    require(
        '"evidence/results/drupal_ai" not in runner' not in canonical,
        "Step 1.04 canonical audit still uses the over-broad batch-root substring guard",
    )
    require(
        'EVIDENCE_ROOT="$REPO/evidence/results/drupal_ai"' in canonical,
        "Step 1.04 canonical audit lacks the exact evidence-root assignment guard",
    )

    joined = "\n".join((source_root / rel).read_text(encoding="utf-8") for rel in SOURCE_PATHS + STEP04_PROGRESSION)
    for pattern in (
        r"curl\s",
        r"wget\s",
        r"api[_-]?key\s*[:=]\s*['\"][^'\"]+",
        r"Authorization\s*:\s*Bearer\s+[A-Za-z0-9._-]+",
        r"data:image/[^;]+;base64,[A-Za-z0-9+/=]{32,}",
    ):
        require(re.search(pattern, joined, re.I) is None, f"Prohibited retained source pattern: {pattern}")

    require(not (repo / "scripts/run-gate1-step06-drupal-ai-batch-evidence-and-human-review.sh").exists(),
            "Step 1.06 source exists")
    return {
        "status": "pass",
        "baseline": BASELINE,
        "target_count": 12,
        "target_sequence_sha256": TARGET_SHA,
        "article_source_sha256": SOURCE_SHA,
        "provider": "openai",
        "model": MODEL,
        "temperature": 0.0,
        "failure_after_sequence": 6,
        "failure_before_sequence": 7,
        "resume_at_sequence": 7,
        "expected_duplicate_count": 0,
        "human_review_in_step_1_05": False,
        "step_1_06_absent": True,
        "moderation_rate_pacing_seconds": 65,
    }


def read_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        require(line.strip() != "", f"Blank event line at {number}")
        value = json.loads(line)
        require(isinstance(value, dict), f"Event line {number} is not an object")
        events.append(value)
    return events


def audit_results(repo: Path, gate_run_dir: Path, result_dir: Path) -> dict[str, Any]:
    source = audit_source(repo, repo)
    for name in RESULT_REQUIRED:
        require((result_dir / name).is_file(), f"Missing Step 1.05 result evidence: {name}")
    require(not (result_dir / "human-review.json").exists(),
            "Step 1.05 must not retain human-review.json before Step 1.06")

    schemas = repo / "shared/schemas"
    store = list(schemas.glob("*.json"))
    run = load(result_dir / "run.json")
    targets = load(result_dir / "targets.json")
    traces = load(result_dir / "tool-traces.json")
    outputs = load(result_dir / "model-outputs.json")
    recommendations = load(result_dir / "recommendations.json")
    validation = load(result_dir / "validation.json")
    submissions = load(result_dir / "submissions.json")
    statuses = load(result_dir / "statuses.json")
    recovery = load(result_dir / "recovery.json")
    summary = load(result_dir / "summary.json")
    events = read_events(result_dir / "events.jsonl")

    validate(schema_validator(schemas / "drupal-ai-run-state.schema.json", store), run, "run")
    validate(schema_validator(schemas / "batch-target-sequence.schema.json", store), targets, "targets")
    validate(schema_validator(schemas / "batch-tool-traces.schema.json", store), traces, "tool traces")
    validate(schema_validator(schemas / "batch-model-outputs.schema.json", store), outputs, "model outputs")
    validate(schema_validator(schemas / "batch-recommendations.schema.json", store), recommendations, "recommendations")
    validate(schema_validator(schemas / "batch-validation.schema.json", store), validation, "validation")
    validate(schema_validator(schemas / "batch-submissions.schema.json", store), submissions, "submissions")
    validate(schema_validator(schemas / "batch-statuses.schema.json", store), statuses, "statuses")
    validate(schema_validator(schemas / "batch-recovery.schema.json", store), recovery, "recovery")
    validate(schema_validator(schemas / "batch-summary.schema.json", store), summary, "summary")
    event_validator = schema_validator(schemas / "batch-event.schema.json", store)
    for index, event in enumerate(events, 1):
        validate(event_validator, event, f"event {index}")

    model_invocations = [event for event in events if event["event_type"] == "model_invocation_started"]
    require([event["sequence"] for event in model_invocations] == list(range(1, 13)),
            "Model invocation evidence does not contain the frozen 1-12 sequence")
    invocation_times = [datetime.fromisoformat(event["occurred_at"].replace("Z", "+00:00")) for event in model_invocations]
    for previous, current in zip(invocation_times, invocation_times[1:]):
        require((current - previous).total_seconds() >= 65,
                "Adjacent model invocations violate the 65-second moderation pacing boundary")

    run_id = run["run_id"]
    require(result_dir.name == run_id, "Result directory name differs from run_id")
    require(run["status"] == "completed", "Run state is not completed")
    require(run["next_target_index"] == 12, "Completed run next_target_index differs from 12")
    require(run["failure_injection_armed"] is True and run["failure_injection_fired"] is True,
            "Failure seam was not armed and fired")
    require(len(run["completed_target_identities"]) == 12, "Run state target completion count differs")
    require(len(run["recommendation_ids"]) == 12, "Run state recommendation identity count differs")
    require(len(run["validation_results"]) == 12, "Run state validation count differs")

    expected_sequences = list(range(1, 13))
    require([v["sequence"] for v in targets["targets"]] == expected_sequences, "Target sequence differs")
    require([v["sequence"] for v in outputs["outputs"]] == expected_sequences, "Model-output sequence differs")
    require([v["sequence"] for v in recommendations["recommendations"]] == expected_sequences,
            "Recommendation sequence differs")
    require([v["sequence"] for v in validation["results"]] == expected_sequences, "Validation sequence differs")
    require([v["sequence"] for v in submissions["submissions"]] == expected_sequences, "Submission sequence differs")

    uuids = [v["uuid"] for v in submissions["submissions"]]
    require(len(set(uuids)) == 12, "Recommendation UUIDs are not unique")
    require(all(v["idempotent_replay_same_identity"] is True for v in submissions["submissions"]),
            "An idempotent replay changed identity")
    require(len(statuses["observations"]) == 12, "Step 1.05 must retain exactly twelve pending observations")
    require(all(v["status"] == "pending" for v in statuses["observations"]),
            "Step 1.05 status evidence includes a non-pending decision")
    require({v["recommendation_uuid"] for v in statuses["observations"]} == set(uuids),
            "Status observations do not match submitted recommendations")

    require(recovery["run_id"] == run_id == recovery["resumed_with_run_id"], "Recovery did not preserve run ID")
    require(recovery["completed_before_failure"] == [1, 2, 3, 4, 5, 6], "Pre-failure sequence differs")
    require(recovery["completed_after_resume"] == [7, 8, 9, 10, 11, 12], "Post-resume sequence differs")
    require(recovery["duplicate_count"] == 0, "Recovery duplicate count differs from zero")

    require(summary["status"] == "pass", "Summary status differs from pass")
    require(summary["run_id"] == run_id, "Summary run ID differs")
    require(summary["target_count"] == 12 and summary["completed_count"] == 12,
            "Summary completed cardinality differs")
    require(summary["failed_count"] == 0 and summary["duplicate_count"] == 0,
            "Summary failure/duplicate count differs")
    require(summary["failure_seam_observed"] is True and summary["resume_sequence"] == 7,
            "Summary recovery seam differs")
    require(summary["source_article_unchanged"] is True, "Summary reports source mutation")
    require(summary["automatic_publication_performed"] is False, "Summary reports automatic publication")
    require(summary["human_review_completed"] is False, "Step 1.05 must stop before human review")

    indexes = [event["event_index"] for event in events]
    require(indexes == list(range(1, len(events) + 1)), "Event indexes are not contiguous")
    failure_positions = [i for i, e in enumerate(events) if e["event_type"] == "failure_injected"]
    resume_positions = [i for i, e in enumerate(events) if e["event_type"] == "run_resumed"]
    completed_positions = [i for i, e in enumerate(events) if e["event_type"] == "run_completed"]
    require(len(failure_positions) == len(resume_positions) == len(completed_positions) == 1,
            "Failure/resume/completion event cardinality differs")
    failure_event = events[failure_positions[0]]
    resume_event = events[resume_positions[0]]
    require(failure_event["sequence"] == 6 and failure_event["outcome"] == "interrupted",
            "Failure event is not the frozen midpoint")
    require(resume_event["sequence"] == 7 and resume_event["outcome"] == "resumed",
            "Resume event is not sequence 7")
    require(failure_positions[0] < resume_positions[0] < completed_positions[0],
            "Failure/resume/completion event ordering differs")

    start = load(gate_run_dir / "start-result.json")
    resume = load(gate_run_dir / "resume-result.json")
    before = load(gate_run_dir / "before-state.json")
    interrupted = load(gate_run_dir / "interrupted-state.json")
    after = load(gate_run_dir / "after-batch-state.json")
    require(start["status"] == "interrupted" and start["provider_request_count"] == 6,
            "Start phase did not stop after six provider requests")
    require(start["agent_request_count"] == 6 and start["automatic_retries"] == 0,
            "Start agent/retry counts differ")
    require(resume["status"] == "completed" and resume["provider_request_count"] == 6,
            "Resume phase did not make exactly six provider requests")
    require(resume["agent_request_count"] == 6 and resume["model_call_count_total"] == 12,
            "Resume agent/total-model counts differ")
    require(resume["duplicate_count"] == 0 and resume["human_review_completed"] is False,
            "Resume duplicate/review boundary differs")
    require(before["seeded_clean"] is True and before["suggestion_count"] == 0,
            "Batch did not begin seeded-clean")
    require(interrupted["suggestion_count"] == 6 and interrupted["runtime_status"] == "interrupted",
            "Interrupted Drupal state does not contain exactly six persisted recommendations")
    require(after["batch_completed_pending_review"] is True and after["suggestion_count"] == 12,
            "Post-batch Drupal state is not twelve pending recommendations")
    require(after["temporary_agent_config_present"] is False,
            "Temporary batch AI Agent config remained after completion")
    require(before["article_source_sha256"] == SOURCE_SHA == interrupted["article_source_sha256"] == after["article_source_sha256"],
            "Source Article projection changed")

    result_manifest = gate_run_dir / "result-files-sha256.txt"
    if result_manifest.is_file():
        subprocess.run(["sha256sum", "-c", str(result_manifest)], cwd=repo, check=True,
                       stdout=subprocess.DEVNULL)
    installed_manifest = gate_run_dir / "installed-files-sha256.txt"
    if installed_manifest.is_file():
        subprocess.run(["sha256sum", "-c", str(installed_manifest)], cwd=repo, check=True,
                       stdout=subprocess.DEVNULL)
    package_manifest = gate_run_dir / "package-files-sha256.txt"
    if package_manifest.is_file():
        subprocess.run(["sha256sum", "-c", "package-files-sha256.txt"], cwd=gate_run_dir, check=True,
                       stdout=subprocess.DEVNULL)

    evidence_text = "\n".join(
        (result_dir / name).read_text(encoding="utf-8", errors="replace")
        for name in RESULT_REQUIRED
    )
    for pattern in (
        r"data:image/[^;]+;base64,[A-Za-z0-9+/=]{16,}",
        r"Authorization\s*:",
        r"Bearer\s+[A-Za-z0-9._-]{12,}",
        r"sk-[A-Za-z0-9_-]{20,}",
    ):
        require(re.search(pattern, evidence_text, re.I) is None, f"Prohibited evidence pattern: {pattern}")

    return source | {
        "evidence_status": "pass",
        "gate_run": gate_run_dir.name,
        "run_id": run_id,
        "provider_request_count_start": 6,
        "provider_request_count_resume": 6,
        "model_call_count_total": 12,
        "automatic_retries": 0,
        "duplicate_count": 0,
        "recommendation_count": 12,
        "pending_status_count": 12,
        "failure_seam_observed": True,
        "resume_sequence": 7,
        "source_article_unchanged": True,
        "human_review_completed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--gate-run-dir", type=Path)
    parser.add_argument("--result-dir", type=Path)
    parser.add_argument("--overlay", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    if args.gate_run_dir or args.result_dir:
        require(args.gate_run_dir is not None and args.result_dir is not None,
                "Both --gate-run-dir and --result-dir are required for evidence audit")
        result = audit_results(repo, args.gate_run_dir.resolve(), args.result_dir.resolve())
    else:
        result = audit_source(repo, args.overlay.resolve() if args.overlay else repo)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
