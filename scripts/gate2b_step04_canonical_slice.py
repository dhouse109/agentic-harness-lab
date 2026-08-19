#!/usr/bin/env python3
"""Run or rehearse the Gate 2B Step 2B.04 canonical CrewAI slice."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
from typing import Any

os.environ.setdefault("CREWAI_DISABLE_VERSION_CHECK", "true")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("CREWAI_DISABLE_TRACKING", "true")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_TESTING", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import httpx

from agentic_harness_crewai.canonical_slice import (
    CANONICAL_TARGET,
    MODEL_ID,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    TEMPERATURE,
    ModelOutput,
    ProviderRequestBudgetExceeded,
    SingleRequestBudget,
    SingleRequestInterceptor,
    build_flow,
    build_live_llm,
    canonical_sha256,
)
from shared.drupal_client.client import DrupalClient, DrupalClientError


PREDECESSOR = "7629434b04d04154b9f219e1d93ed772401a1288"
LOCK_SHA = "855e5edff2cb86eb64ea9856d239b19010e7d3b1f80c40e370ed81d66b8e4e7c"
STEP03_MANIFEST = "6b76549c442d3f27eb7278a41c69dad4e7313bd673adf331012d9c02c2216dad"
STEP03_SUMMARY = "33d6bc403fe60556e4fc4d823eaf98d7d23b9c9973f66a1ccd283fce316c35ec"
EVIDENCE_FILES = (
    "authorization.json", "canonical-target.json", "context-provenance.json",
    "events.jsonl", "flow-state.json", "persistence-provenance.json",
    "pinned-source-provenance.json", "predecessor.json", "privacy-scan.json",
    "prompt-provenance.json", "provider-accounting.json", "provider-metadata.json",
    "raw-model-output.json", "recommendation.json", "source-nonmutation.json",
    "stage-results.json", "submission.json", "summary.json", "summary.md",
    "evidence-manifest.json",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, text=True,
                          capture_output=True).stdout.strip()


def drupal_snapshot(repo: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["ddev", "drush", "--quiet", "php:script", "scripts/gate1-step04-canonical-vertical-slice.php", "--", "snapshot"],
        cwd=repo / "drupal", check=True, text=True, capture_output=True,
    )
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise RuntimeError("Drupal snapshot did not return an object")
    return value


class FakeLLM:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def call(self, *, messages: list[dict[str, Any]]) -> str:
        if not messages:
            raise RuntimeError("Fake LLM requires messages")
        self.calls += 1
        return self.response


class RecordingFakeClient:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.submit_calls = 0
        self.context = {
            "schema_version": 1,
            "target": CANONICAL_TARGET,
            "article": {"title": "Phase 0 01 — Emergency Preparedness Checklist", "revision_id": 1,
                        "content_language": "en", "body_plain": "Deterministic rehearsal body."},
            "image": {"file_uuid": CANONICAL_TARGET["file_uuid"], "filename": "phase0-article-01-image-1.png",
                      "mime_type": "image/png", "width": 1200, "height": 675, "byte_length": 16,
                      "sha256": "0" * 64,
                      "representation": {"kind": "data_url", "value": "data:image/png;base64,REHEARSAL_ONLY"}},
            "existing_alt": "", "evidence_hash": "sha256:" + "1" * 64, "collected_at": now(),
        }

    def envelope(self, name: str, data: dict[str, Any], correlation_id: str) -> dict[str, Any]:
        return {"schema_version": 1, "tool_name": name, "ok": True, "timestamp": now(),
                "correlation_id": correlation_id, "data": data, "error": None}

    def find_images_needing_review(self, correlation_id: str) -> dict[str, Any]:
        self.calls.append("find_images_needing_review")
        targets = [dict(CANONICAL_TARGET)]
        for sequence in range(2, 13):
            target = dict(CANONICAL_TARGET)
            target.update({"sequence": sequence, "revision_id": sequence,
                           "node_uuid": f"00000000-0000-4000-8000-{sequence:012d}",
                           "file_uuid": f"10000000-0000-4000-8000-{sequence:012d}"})
            targets.append(target)
        # The Flow requires the real frozen hash. Rehearsal replaces discovery below.
        return self.envelope("find_images_needing_review", {"targets": targets, "total_count": 12}, correlation_id)

    def get_image_context(self, target: dict[str, Any], correlation_id: str) -> dict[str, Any]:
        self.calls.append("get_image_context")
        if target != CANONICAL_TARGET:
            raise RuntimeError("Rehearsal target drifted")
        return self.envelope("get_image_context", self.context, correlation_id)

    def submit_recommendation(self, recommendation: dict[str, Any], correlation_id: str) -> dict[str, Any]:
        self.calls.append("submit_recommendation")
        self.submit_calls += 1
        data = {"node_id": 999, "uuid": "00000000-0000-4000-8000-000000000999", "revision_id": 1001,
                "status": "pending", "source_framework": "crewai", "run_id": recommendation["run_id"],
                "target": recommendation["target"]}
        return self.envelope("submit_recommendation", data, correlation_id)

    def get_recommendation_status(self, recommendation_id: str, correlation_id: str) -> dict[str, Any]:
        self.calls.append("get_recommendation_status")
        return self.envelope("get_recommendation_status",
                             {"uuid": recommendation_id, "revision_id": 1001, "status": "pending",
                              "reviewer_username": None, "reviewed_at": None}, correlation_id)


def frozen_targets(repo: Path) -> list[dict[str, Any]]:
    path = repo / "evidence/gates/gate-2a/canonical-slice/gate2a-step05-20260810T140133Z-0025b888/targets.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise RuntimeError("Frozen target evidence is not a list")
    return value


def rehearse(repo: Path, work_root: Path) -> dict[str, Any]:
    os.environ["CREWAI_DISABLE_VERSION_CHECK"] = "true"
    targets = frozen_targets(repo)
    if targets[0] != CANONICAL_TARGET or canonical_sha256(targets) != "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728":
        raise RuntimeError("Frozen canonical target or sequence drifted")

    fake = RecordingFakeClient()
    original_discovery = fake.find_images_needing_review
    fake.find_images_needing_review = lambda cid: fake.envelope(
        "find_images_needing_review", {"targets": targets, "total_count": 12}, cid)  # type: ignore[method-assign]
    del original_discovery
    budget = SingleRequestBudget()
    llm = FakeLLM('{"proposed_alt_text":"White block number 1 on a navy emergency-preparedness graphic."}')
    runtime_db = work_root / "success" / "crewai-20260818T190000Z-deadbeef" / "flow-state.sqlite"
    flow = build_flow(client=fake, correlation_id="rehearsal", run_id="crewai-20260818T190000Z-deadbeef",
                      runtime_db=runtime_db, llm=llm, request_budget=budget)
    flow.kickoff()
    state = flow.state.model_dump()
    if state["status"] != "awaiting_human_review" or fake.submit_calls != 1 or llm.calls != 1:
        raise RuntimeError("Model-free Flow rehearsal did not reach the expected pending state")

    invalid_fake = RecordingFakeClient()
    invalid_fake.find_images_needing_review = lambda cid: invalid_fake.envelope(
        "find_images_needing_review", {"targets": targets, "total_count": 12}, cid)  # type: ignore[method-assign]
    invalid_flow = build_flow(client=invalid_fake, correlation_id="invalid-rehearsal",
                              run_id="crewai-20260818T190001Z-deadbeef",
                              runtime_db=work_root / "invalid" / "crewai-20260818T190001Z-deadbeef" / "flow-state.sqlite",
                              llm=FakeLLM('{"unexpected":"field"}'), request_budget=SingleRequestBudget())
    invalid_failed_closed = False
    try:
        invalid_flow.kickoff()
    except Exception:
        invalid_failed_closed = invalid_fake.submit_calls == 0
    if not invalid_failed_closed:
        raise RuntimeError("Invalid structured output did not fail closed before submission")

    budget_control = SingleRequestBudget()
    budget_control.claim()
    second_logical_blocked = False
    try:
        budget_control.claim()
    except ProviderRequestBudgetExceeded:
        second_logical_blocked = True

    interceptor = SingleRequestInterceptor()
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    interceptor.on_outbound(request)
    second_physical_blocked = False
    try:
        interceptor.on_outbound(request)
    except ProviderRequestBudgetExceeded:
        second_physical_blocked = True
    if not second_logical_blocked or not second_physical_blocked:
        raise RuntimeError("One-request budget controls did not block a second request")

    probe_interceptor = SingleRequestInterceptor()
    provider_probe = build_live_llm(probe_interceptor, api_key="model-free-rehearsal-placeholder")
    provider_source = inspect.getsource(type(provider_probe))
    responses_source = inspect.getsource(type(provider_probe)._handle_responses)
    serialization_root = work_root / "serialization-rehearsal"
    serialization_root.mkdir(parents=True, exist_ok=False)
    write_json(serialization_root / "control.json", {"proof_mode": "model-free-disposable", "status": "pass"})
    (serialization_root / "control-log.txt").write_text("model-free disposable serialization\n", encoding="utf-8")
    serialization_manifest = {
        "algorithm": "sha256",
        "entries": [
            {"path": path.name, "sha256": sha_file(path)}
            for path in sorted(serialization_root.iterdir())
        ],
    }
    write_json(serialization_root / "manifest.json", serialization_manifest)
    manifest_round_trip = json.loads((serialization_root / "manifest.json").read_text(encoding="utf-8"))
    manifest_valid = all(
        sha_file(serialization_root / entry["path"]) == entry["sha256"]
        for entry in manifest_round_trip["entries"]
    )
    source = inspect.getsource(sys.modules["agentic_harness_crewai.canonical_slice"])
    assertions = {
        "invalid_output_failed_closed": invalid_failed_closed,
        "second_logical_request_blocked": second_logical_blocked,
        "second_physical_request_blocked": second_physical_blocked,
        "runtime_outside_shared": "/shared/" not in runtime_db.resolve().as_posix(),
        "sqlite_flow_persistence_created": runtime_db.is_file(),
        "private_skip_auto_memory_absent": (
            "_skip_auto_memory =" not in source and "._skip_auto_memory" not in source
        ),
        "human_feedback_absent": "HumanFeedbackPending" not in source and "from_pending" not in source,
        "task_guardrail_absent": "Task(" not in source and "guardrail_max_retries" not in source,
        "learning_absent": "learn=" not in source,
        "version_check_disabled": os.environ.get("CREWAI_DISABLE_VERSION_CHECK") == "true",
        "evidence_serialization_rehearsed": manifest_valid,
        "native_responses_selected": provider_probe.api == "responses",
        "single_responses_create_callsite": responses_source.count(".responses.create(") == 1,
        "crewai_retry_setting_zero": provider_probe.max_retries == 0,
        "sdk_retry_setting_zero": (
            'config["max_retries"] = self.max_retries' in provider_source
            and "return OpenAI(**client_config)" in provider_source
        ),
        "intercepting_transport_selected": provider_probe.interceptor is probe_interceptor,
        "streaming_disabled": provider_probe.stream is False,
        "provider_store_disabled": provider_probe.store is False,
        "auto_chain_disabled": provider_probe.auto_chain is False and provider_probe.auto_chain_reasoning is False,
    }
    if not all(assertions.values()):
        raise RuntimeError(f"Model-free control rehearsal failed: {assertions!r}")
    controls = {
        "status": "pass",
        "canonical_target": CANONICAL_TARGET,
        "flow_pending_state": state["status"],
        "fake_model_calls": llm.calls,
        "fake_submission_calls": fake.submit_calls,
        "provider_class": f"{type(provider_probe).__module__}.{type(provider_probe).__name__}",
        **assertions,
    }
    return controls


def source_provenance(repo: Path) -> dict[str, Any]:
    site = repo / "crewai/.venv/lib/python3.12/site-packages"
    files = [
        "crewai/llm.py", "crewai/llms/providers/openai/completion.py",
        "crewai/llms/hooks/base.py", "crewai/llms/hooks/transport.py",
        "crewai/flow/persistence/sqlite.py", "crewai/flow/persistence/decorators.py",
    ]
    return {
        "status": "pass", "python": ".".join(map(str, sys.version_info[:3])),
        "crewai": importlib.metadata.version("crewai"),
        "crewai_tools": importlib.metadata.version("crewai-tools"),
        "selected_path": "CrewAI Flow -> native OpenAICompletion(api=responses) -> OpenAI.responses.create",
        "public_transport_counter": "crewai.llms.hooks.base.BaseInterceptor",
        "source_sha256": {name: sha_file(site / name) for name in files},
    }


def privacy_scan(output: Path, secrets: list[str]) -> dict[str, Any]:
    findings: list[str] = []
    patterns = [re.compile(rb"(?:Basic|Bearer) [A-Za-z0-9+/=_-]{12,}"),
                re.compile(rb"sk-[A-Za-z0-9_-]{20,}"), re.compile(rb"data:image/[^;]+;base64,")]
    scanned: list[str] = []
    for path in sorted(output.iterdir()):
        if not path.is_file() or path.name in {"privacy-scan.json", "evidence-manifest.json"}:
            continue
        scanned.append(path.name)
        data = path.read_bytes()
        if any(pattern.search(data) for pattern in patterns):
            findings.append(f"credential-or-data-url-pattern:{path.name}")
        for secret in secrets:
            if secret and secret.encode("utf-8") in data:
                findings.append(f"exact-runtime-secret:{path.name}")
    return {"status": "pass" if not findings else "fail", "files_scanned": scanned, "findings": findings}


def write_manifest(output: Path) -> None:
    entries = [{"path": name, "sha256": sha_file(output / name)}
               for name in EVIDENCE_FILES if name != "evidence-manifest.json"]
    write_json(output / "evidence-manifest.json", {"algorithm": "sha256", "entries": entries})


def write_failed_manifest(output: Path) -> None:
    entries = [
        {"path": path.name, "sha256": sha_file(path)}
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "evidence-manifest.json"
    ]
    write_json(output / "evidence-manifest.json", {
        "algorithm": "sha256", "status": "failed-run-partial", "entries": entries,
    })


def run_live(repo: Path, output: Path, run_id: str, runtime_root: Path) -> None:
    if os.environ.get("GATE2B_STEP04_LIVE_AUTHORIZED") != "one-provider-request-one-live-submission":
        raise SystemExit("Explicit Step 2B.04 live authorization is required")
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("GATE2B_DRUPAL_BASE_URL", "")
    username = os.environ.get("GATE2B_DRUPAL_BASIC_AUTH_USER", "")
    password = os.environ.get("GATE2B_DRUPAL_BASIC_AUTH_PASSWORD", "")
    if not all((api_key, base_url, username, password)):
        raise SystemExit("Required live credentials are unavailable")
    if output.exists():
        raise SystemExit("Evidence run directory already exists")
    output.mkdir(parents=True)
    events: list[dict[str, Any]] = []
    stage = "predecessor"
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    flow: Any = None
    interceptor = SingleRequestInterceptor()
    budget = SingleRequestBudget()
    try:
        if git(repo, "rev-parse", "HEAD") != PREDECESSOR:
            raise RuntimeError("Live run requires exact Step 2B.03 merged predecessor")
        before = drupal_snapshot(repo)
        if not before.get("seeded_clean") or before.get("suggestion_count") != 0:
            raise RuntimeError("Live run requires seeded-clean Drupal with zero recommendations")
        stage = "flow_construction"
        client = DrupalClient(base_url=base_url, username=username, password=password,
                              verify_tls=os.environ.get("GATE2B_DRUPAL_INSECURE_LOCAL") != "true")
        llm = build_live_llm(interceptor, api_key=api_key)
        runtime_db = runtime_root / run_id / "flow-state.sqlite"
        flow = build_flow(client=client, correlation_id=f"{run_id}-canonical-1", run_id=run_id,
                          runtime_db=runtime_db, llm=llm, request_budget=budget, interceptor=interceptor)
        stage = "flow_execution"
        events.append({"stage": stage, "status": "started", "occurred_at": now()})
        result = flow.kickoff()
        events.append({"stage": stage, "status": "pass", "occurred_at": now()})
        state = flow.state.model_dump()
        accounting = interceptor.snapshot() | {"logical_generations": budget.logical_generations}
        if accounting["actual_provider_requests"] != 1 or accounting["successful_provider_responses"] != 1:
            raise RuntimeError("Exactly-one successful physical provider request was not observed")
        after = drupal_snapshot(repo)
        if before.get("article_source_sha256") != after.get("article_source_sha256"):
            raise RuntimeError("Source Article projection changed")
        if after.get("suggestion_count") != 1:
            raise RuntimeError("Exactly one recommendation record was not observed")
        recommendation = state["assembled_recommendation"]
        submission = result["submission"]
        context = state["context_provenance"]
        write_json(output / "authorization.json", {"status": "pass", "counts": {
            "logical_model_generations": 1, "actual_provider_requests": 1,
            "successful_provider_responses": 1, "provider_retries": 0, "transport_retries": 0,
            "guardrail_correction_retries": 0, "structured_repair_calls": 0,
            "fallback_provider_calls": 0, "learning_distillation_calls": 0,
            "feedback_collapse_calls": 0, "drupal_recommendation_mutations": 1,
            "source_content_mutations": 0, "authoritative_human_review_actions": 0,
            "dependency_changes": 0, "live_recommendation_submissions": 1,
            "gate2c_executions": 0}})
        write_json(output / "canonical-target.json", {"status": "pass", "target": CANONICAL_TARGET,
                   "target_sequence_sha256": state["target_sequence_hash"]})
        write_json(output / "context-provenance.json", context)
        (output / "events.jsonl").write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in events), encoding="utf-8")
        write_json(output / "flow-state.json", state)
        write_json(output / "persistence-provenance.json", state["persistence_provenance"] | {
            "sqlite_sha256": sha_file(runtime_db),
            "wording": "terminal-output reconstruction observed; live Flow state restoration/continuation not demonstrated"})
        write_json(output / "pinned-source-provenance.json", source_provenance(repo))
        write_json(output / "predecessor.json", {"status": "pass", "head": PREDECESSOR,
                   "lock_sha256": sha_file(repo / "crewai/uv.lock"), "step03_manifest_sha256": STEP03_MANIFEST,
                   "step03_summary_sha256": STEP03_SUMMARY})
        write_json(output / "prompt-provenance.json", {"status": "pass", "prompt_version": PROMPT_VERSION,
                   "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
                   "system_prompt_length": len(SYSTEM_PROMPT), "user_prompt_semantics": "frozen shared template",
                   "user_prompt_sha256": state["prompt_sha256"],
                   "raw_prompt_retained": False, "model": MODEL_ID, "temperature": TEMPERATURE})
        write_json(output / "provider-accounting.json", {"status": "pass"} | accounting)
        write_json(output / "provider-metadata.json", {"status": "pass", "provider": "OpenAI", "model": MODEL_ID,
                   "temperature": TEMPERATURE, "api": "responses", "stream": False, "store": False,
                   "max_retries": 0, "response_format": "strict json_schema", "response_body_retained": False})
        write_json(output / "raw-model-output.json", state["raw_model_output"])
        write_json(output / "recommendation.json", recommendation)
        write_json(output / "source-nonmutation.json", {"status": "pass",
                   "article_source_sha256_before": before["article_source_sha256"],
                   "article_source_sha256_after": after["article_source_sha256"],
                   "suggestion_count_before": 0, "suggestion_count_after": 1,
                   "mutation_effect": "one unpublished revision-enabled alt_text_suggestion initial revision in pending state"})
        write_json(output / "stage-results.json", {"status": "pass", "stages": [
            {"name": name, "status": "pass"} for name in (
                "target_discovery", "context_retrieval", "provider_request", "structured_parsing",
                "recommendation_assembly", "shared_deterministic_validation", "submission",
                "flow_state_persistence", "evidence_serialization")], "failed_stage": None})
        write_json(output / "submission.json", {"status": "pass", "result": submission,
                   "shared_validation": "passed atomically inside authoritative submit_recommendation",
                   "review_action_performed": False})
        summary = {"schema_version": "1.0.0", "step": "2B.04", "status": "pass", "run_id": run_id,
                   "canonical_sequence": 1, "model": MODEL_ID, "temperature": TEMPERATURE,
                   "provider_requests": 1, "live_submissions": 1, "review_status": "pending",
                   "continuation_claimed": False, "gate2c": "deferred_unclaimed"}
        write_json(output / "summary.json", summary)
        (output / "summary.md").write_text(
            f"# Gate 2B Step 2B.04 canonical slice\n\nRun: `{run_id}`\n\nStatus: **PASS**\n\n"
            "One CrewAI-owned Flow generation used one physical OpenAI Responses request and created one pending "
            "recommendation through the frozen shared operation. No human review or continuation was performed.\n",
            encoding="utf-8")
        scan = privacy_scan(output, [api_key, password])
        write_json(output / "privacy-scan.json", scan)
        if scan["status"] != "pass":
            raise RuntimeError("Evidence privacy scan failed")
        write_manifest(output)
    except Exception as exc:
        failed_stage = stage
        if flow is not None:
            failed_stage = getattr(flow, "_current_stage", failed_stage)
        if isinstance(exc, DrupalClientError) and exc.status == 422 and failed_stage == "submission":
            failed_stage = "deterministic_validation"
        if "State persistence failed" in str(exc):
            failed_stage = "state_persistence"
        events.append({"stage": failed_stage, "status": "fail", "error_type": type(exc).__name__,
                       "error": str(exc)[:500], "occurred_at": now()})
        (output / "events.jsonl").write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in events), encoding="utf-8")
        write_json(output / "stage-results.json", {"status": "fail", "failed_stage": failed_stage,
                   "error_type": type(exc).__name__, "error": str(exc)[:500]})
        write_json(output / "summary.json", {"schema_version": "1.0.0", "step": "2B.04", "status": "fail",
                   "run_id": run_id, "failed_stage": failed_stage, "provider_accounting": interceptor.snapshot(),
                   "evidence_retained": True})
        (output / "summary.md").write_text(f"# Gate 2B Step 2B.04 failed run\n\nFailed stage: `{failed_stage}`.\n", encoding="utf-8")
        write_json(output / "authorization.json", {"status": "failed-run-observed", "counts": {
            **interceptor.snapshot(), "logical_model_generations": budget.logical_generations,
            "live_recommendation_submissions": 1 if getattr(flow, "state", None)
            and getattr(flow.state, "recommendation_id", None) else 0,
            "authoritative_human_review_actions": 0, "source_content_mutations": 0,
            "dependency_changes": 0, "gate2c_executions": 0,
        }})
        write_json(output / "provider-accounting.json", interceptor.snapshot() | {
            "logical_generations": budget.logical_generations, "status": "failed-run-observed",
        })
        write_json(output / "privacy-scan.json", privacy_scan(output, [api_key, password]))
        write_failed_manifest(output)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--mode", choices=("rehearse", "run"), required=True)
    parser.add_argument("--work-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--runtime-root", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    if args.mode == "rehearse":
        work_root = args.work_root or Path(tempfile.mkdtemp(prefix="gate2b-step04-rehearsal-"))
        network_attempts: list[str] = []
        original_connect = socket.socket.connect
        original_create_connection = socket.create_connection

        def blocked_connect(self: Any, address: Any) -> Any:
            if getattr(self, "family", None) == socket.AF_UNIX:
                return original_connect(self, address)
            network_attempts.append(str(address)[:200])
            raise RuntimeError("Model-free rehearsal network guard fired")

        def blocked_create_connection(address: Any, *positional: Any, **kwargs: Any) -> Any:
            del positional, kwargs
            network_attempts.append(str(address)[:200])
            raise RuntimeError("Model-free rehearsal network guard fired")

        socket.socket.connect = blocked_connect  # type: ignore[method-assign]
        socket.create_connection = blocked_create_connection  # type: ignore[assignment]
        try:
            result = rehearse(repo, work_root)
        finally:
            socket.socket.connect = original_connect
            socket.create_connection = original_create_connection
        if network_attempts:
            raise RuntimeError(f"Model-free rehearsal attempted network: {network_attempts!r}")
        result["network_attempts"] = 0
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if not args.output or not args.run_id or not args.runtime_root:
        parser.error("run requires --output, --run-id, and --runtime-root")
    run_live(repo, args.output, args.run_id, args.runtime_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
