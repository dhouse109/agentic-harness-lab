"""Gate 2A Step 2A.05 canonical LangGraph vertical slice.

One canonical target crosses context, model, verification, recommendation
submission, status observation, and LangGraph checkpoint state. Full Article
body text and image representation values are ephemeral execution scratch and
are never returned as graph state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field

from agentic_harness_langgraph.state import LangGraphRunState, advance_target, initial_state
from agentic_harness_langgraph.tools import build_tools
from shared.drupal_client.client import DrupalClient

MODEL_ID = "gpt-4.1-mini-2025-04-14"
TEMPERATURE = 0.0
PROMPT_VERSION = "langgraph-alt-text-v1.0.0"
VALIDATOR_VERSION = "gate05-validator-1.0.0"
TARGET_HASH = "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728"
ACCEPTED_TARGETS_REL = (
    "evidence/gates/gate-2a/tool-adapters/"
    "gate2a-step03-20260809T233127Z-2375581/targets.json"
)

SYSTEM_PROMPT = """You draft one alt-text recommendation for one verified Drupal image-field usage.

Use only the supplied image and page context. Describe the image's meaningful content and purpose
in that context. Be concise and specific. Do not begin with \"image of\", \"photo of\", \"picture of\",
\"graphic of\", \"Here is\", or \"Alt text:\". Do not repeat the filename. Do not invent facts that are
not visible in the image or stated in the supplied page context.

Return only the structured model-output object required by
recommendation.schema.json#/$defs/model_output. The proposed_alt_text value must be nonempty and no
more than 250 Unicode characters."""

GENERIC_ALT_VALUES = {
    "image", "photo", "picture", "graphic", "illustration", "icon",
    "placeholder", "test image", "article image", "supporting image", "primary image",
}


class ModelOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proposed_alt_text: str = Field(min_length=1, max_length=250)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def append_event(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def envelope(result: Any, tool_name: str) -> dict[str, Any]:
    require(isinstance(result, dict), f"{tool_name} result is not an object")
    expected = {"schema_version", "tool_name", "ok", "timestamp", "correlation_id", "data", "error"}
    require(set(result) == expected, f"{tool_name} envelope keys differ from frozen schema")
    require(result["schema_version"] == 1, f"{tool_name} schema_version is not 1")
    require(result["tool_name"] == tool_name, f"{tool_name} tool_name mismatch")
    require(result["ok"] is True, f"{tool_name} returned ok=false: {result.get('error')!r}")
    require(result["error"] is None, f"{tool_name} returned an error")
    require(isinstance(result["data"], dict), f"{tool_name} data is not an object")
    return result["data"]


def context_summary(data: dict[str, Any]) -> dict[str, Any]:
    article = data.get("article")
    image = data.get("image")
    target = data.get("target")
    require(isinstance(article, dict), "Context article is missing")
    require(isinstance(image, dict), "Context image is missing")
    require(isinstance(target, dict), "Context target is missing")
    rep = image.get("representation")
    require(isinstance(rep, dict), "Context representation is missing")
    value = rep.get("value")
    body = article.get("body_plain")
    require(isinstance(value, str) and value, "Context representation value is missing")
    require(isinstance(body, str), "Context Article body_plain is not a string")
    return {
        "schema_version": data.get("schema_version"),
        "target": target,
        "article": {
            "title": article.get("title"),
            "revision_id": article.get("revision_id"),
            "content_language": article.get("content_language"),
            "body_plain_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "body_plain_length": len(body),
            "body_plain_retained": False,
        },
        "image": {
            "file_uuid": image.get("file_uuid"),
            "filename": image.get("filename"),
            "mime_type": image.get("mime_type"),
            "width": image.get("width"),
            "height": image.get("height"),
            "byte_length": image.get("byte_length"),
            "sha256": image.get("sha256"),
            "representation_kind": rep.get("kind"),
            "representation_value_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
            "representation_value_length": len(value),
            "representation_value_retained": False,
        },
        "existing_alt": data.get("existing_alt"),
        "evidence_hash": data.get("evidence_hash"),
        "collected_at": data.get("collected_at"),
    }


def user_prompt(target: dict[str, Any], context: dict[str, Any]) -> str:
    article = context["article"]
    image = context["image"]
    existing_alt = context.get("existing_alt")
    width = image.get("width") if image.get("width") is not None else "unknown"
    height = image.get("height") if image.get("height") is not None else "unknown"
    return (
        "TARGET\n"
        f"- Sequence: {target['sequence']}\n"
        f"- Node UUID: {target['node_uuid']}\n"
        f"- Article revision: {target['revision_id']}\n"
        f"- Field: {target['field_name']}\n"
        f"- Delta: {target['delta']}\n"
        f"- File UUID: {target['file_uuid']}\n"
        f"- Existing alt text: {'null' if existing_alt is None else existing_alt}\n\n"
        "PAGE CONTEXT\n"
        f"- Article title: {article['title']}\n"
        f"- Article body: {article['body_plain']}\n\n"
        "IMAGE CONTEXT\n"
        f"- Filename: {image['filename']}\n"
        f"- MIME type: {image['mime_type']}\n"
        f"- Dimensions: {width} x {height}\n"
        "- Image input: identical PNG bytes, represented as a Base64-encoded PNG data URL "
        "with detail=auto or the Drupal AI ImageFile equivalent over the same bytes\n\n"
        "Produce the model-output object only."
    )


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).lower()


def filename_echo(normalized_alt: str, filename: str) -> bool:
    stem = Path(filename).stem
    variants = {
        normalize(filename),
        normalize(stem),
        normalize(stem.replace("-", " ").replace("_", " ")),
    }
    if normalized_alt in variants:
        return True
    for variant in variants:
        if not variant:
            continue
        if re.fullmatch(
            r"(?:image|photo|picture|graphic|illustration)(?:\s+of)?\s+" + re.escape(variant),
            normalized_alt,
            flags=re.I,
        ):
            return True
    return False


def deterministic_validate(alt: str, context: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    proposed = alt.strip()
    if not proposed:
        errors.append("ALT_TEXT_EMPTY")
        return errors
    if len(proposed) > 250:
        errors.append("ALT_TEXT_TOO_LONG")
    if re.match(r"^(?:here(?:['’]s| is)\b|alt\s*text\s*:|proposed\s+alt\s*text\s*:)", proposed, re.I):
        errors.append("ALT_TEXT_PREAMBLE")
    if re.match(r"^(?:image|photo|picture|graphic)\s+of\b", proposed, re.I):
        errors.append("ALT_TEXT_FORBIDDEN_LEAD")

    normalized = normalize(proposed)
    current = normalize(str(context.get("existing_alt") or ""))
    if current and normalized == current:
        errors.append("ALT_TEXT_DUPLICATE")

    filename = str(context["image"]["filename"])
    if filename_echo(normalized, filename):
        errors.append("ALT_TEXT_FILENAME_ECHO")
    if normalized in GENERIC_ALT_VALUES or re.fullmatch(
        r"(?:image|photo|picture|graphic|illustration)(?:\s+\d+)?(?:\.(?:png|jpe?g|gif|webp))?",
        normalized,
        flags=re.I,
    ):
        errors.append("ALT_TEXT_GENERIC")
    return errors


def trace(
    traces: list[dict[str, Any]],
    *,
    operation: str,
    correlation_id: str,
    started_at: str,
    completed_at: str,
    data: dict[str, Any],
    target: dict[str, Any] | None = None,
) -> None:
    item: dict[str, Any] = {
        "operation": operation,
        "correlation_id": correlation_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "ok": True,
        "result_data_sha256": "sha256:" + sha(data),
    }
    if target is not None:
        item["target"] = target
    traces.append(item)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    evidence = Path(args.evidence).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    events_path = evidence / "events.jsonl"

    require(os.environ.get("OPENAI_API_KEY", "") != "", "OPENAI_API_KEY is required")
    base_url = os.environ.get("GATE2A_DRUPAL_BASE_URL", "")
    username = os.environ.get("GATE2A_DRUPAL_USERNAME", "")
    password = os.environ.get("GATE2A_DRUPAL_PASSWORD", "")
    require(base_url and username and password, "Drupal live environment is incomplete")
    require(username == "agent_bot", "Step 2A.05 Drupal caller must be agent_bot")

    accepted_targets = json.loads((repo / ACCEPTED_TARGETS_REL).read_text(encoding="utf-8"))
    require(isinstance(accepted_targets, list) and len(accepted_targets) == 12, "Accepted target evidence is invalid")

    client = DrupalClient(
        base_url=base_url,
        username=username,
        password=password,
        verify_tls=False,
        timeout_seconds=60,
    )
    correlation_id = f"{args.run_id}-slice"
    tools = build_tools(client, correlation_id=correlation_id)
    expected_tools = [
        "find_images_needing_review",
        "get_image_context",
        "submit_recommendation",
        "get_recommendation_status",
    ]
    require(list(tools) == expected_tools, "LangGraph tool surface differs from frozen operation set")

    traces: list[dict[str, Any]] = []
    privacy_probes: dict[str, str] = {
        "drupal_password": password,
        "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
    }
    call_counters = {
        "model_invocations_attempted": 0,
        "model_invocations_succeeded": 0,
        "automatic_model_retries_configured": 0,
        "semantic_retry_loop_performed": False,
        "find_images_needing_review": 0,
        "get_image_context": 0,
        "submit_recommendation": 0,
        "get_recommendation_status": 0,
    }
    write_json(evidence / "call-counters.json", call_counters)

    sqlite_path = repo / "langchain/.gate2a-runtime" / f"{args.run_id}.sqlite"
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    started_at = now()
    state0 = initial_state(args.run_id, started_at)
    config = {"configurable": {"thread_id": args.run_id}}

    def invoke_tool(name: str, payload: dict[str, Any], target: dict[str, Any] | None = None) -> dict[str, Any]:
        started = now()
        call_counters[name] += 1
        write_json(evidence / "call-counters.json", call_counters)
        result = tools[name].invoke(payload)
        data = envelope(result, name)
        completed = now()
        trace(
            traces,
            operation=name,
            correlation_id=correlation_id,
            started_at=started,
            completed_at=completed,
            data=data,
            target=target,
        )
        append_event(events_path, {
            "event": "tool-call",
            "operation": name,
            "occurred_at": completed,
            "run_id": args.run_id,
            "sequence": target.get("sequence") if target else None,
            "outcome": "pass",
        })
        return data

    def canonical_slice_node(state: LangGraphRunState) -> LangGraphRunState:
        require(int(state["next_target_index"]) == 0, "Canonical slice must begin at target index 0")

        discovery = invoke_tool("find_images_needing_review", {})
        targets = discovery.get("targets")
        require(isinstance(targets, list), "Discovery targets are missing")
        require(discovery.get("total_count") == 12 and len(targets) == 12, "Discovery did not return exactly 12 targets")
        require(targets == accepted_targets, "Discovery target list differs from accepted Step 2A.03 target evidence")
        require(hashlib.sha256(canonical(targets)).hexdigest() == TARGET_HASH, "Discovery target hash differs from frozen contract")
        write_json(evidence / "targets.json", targets)
        target = targets[0]
        require(target.get("sequence") == 1, "Canonical target is not sequence 1")

        before_model = invoke_tool("get_image_context", {"target": target}, target)
        require(before_model.get("target") == target, "Pre-model context target differs")
        write_json(evidence / "context-before-model-summary.json", context_summary(before_model))
        article_body = str(before_model["article"]["body_plain"])
        representation = str(before_model["image"]["representation"]["value"])
        privacy_probes["article_body"] = article_body
        privacy_probes["image_representation"] = representation

        prompt = user_prompt(target, before_model)
        write_json(evidence / "prompt-metadata.json", {
            "schema_version": 1,
            "prompt_version": PROMPT_VERSION,
            "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
            "system_prompt_length": len(SYSTEM_PROMPT),
            "user_prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "user_prompt_length": len(prompt),
            "article_body_retained": False,
            "image_representation_retained": False,
            "model_id": MODEL_ID,
            "temperature": TEMPERATURE,
            "max_retries": 0,
            "structured_output_mechanism": "ChatOpenAI.with_structured_output(method=json_schema, strict=true)",
        })

        model = ChatOpenAI(
            model=MODEL_ID,
            temperature=TEMPERATURE,
            max_retries=0,
        ).with_structured_output(
            ModelOutput,
            method="json_schema",
            strict=True,
        )
        call_counters["model_invocations_attempted"] = 1
        write_json(evidence / "call-counters.json", call_counters)
        append_event(events_path, {
            "event": "model-call-start",
            "occurred_at": now(),
            "run_id": args.run_id,
            "sequence": 1,
            "model_id": MODEL_ID,
        })
        result = model.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": representation, "detail": "auto"}},
            ]),
        ])
        parsed = result if isinstance(result, ModelOutput) else ModelOutput.model_validate(result)
        call_counters["model_invocations_succeeded"] = 1
        write_json(evidence / "call-counters.json", call_counters)
        model_output = parsed.model_dump()
        write_json(evidence / "model-output.json", model_output)
        append_event(events_path, {
            "event": "model-call-complete",
            "occurred_at": now(),
            "run_id": args.run_id,
            "sequence": 1,
            "outcome": "pass",
            "model_output_sha256": "sha256:" + sha(model_output),
        })

        before_submit = invoke_tool("get_image_context", {"target": target}, target)
        require(before_submit.get("target") == target, "Pre-submit context target differs")
        require(
            before_submit.get("evidence_hash") == before_model.get("evidence_hash"),
            "Target/page/image context changed between model call and submission",
        )
        write_json(evidence / "context-before-submit-summary.json", context_summary(before_submit))

        errors = deterministic_validate(model_output["proposed_alt_text"], before_submit)
        validation = {
            "sequence": 1,
            "target": target,
            "structured_output_schema_valid": True,
            "deterministic_validation_passed": len(errors) == 0,
            "errors": errors,
        }
        write_json(evidence / "validation.json", validation)
        require(not errors, f"Deterministic validation failed: {errors!r}")
        append_event(events_path, {
            "event": "deterministic-validation",
            "occurred_at": now(),
            "run_id": args.run_id,
            "sequence": 1,
            "outcome": "pass",
        })

        recommendation = {
            "schema_version": 1,
            "target": target,
            "proposed_alt_text": model_output["proposed_alt_text"].strip(),
            "source_framework": "langgraph",
            "run_id": args.run_id,
            "evidence_hash": before_submit["evidence_hash"],
            "validator_version": VALIDATOR_VERSION,
        }
        write_json(evidence / "recommendation.json", recommendation)

        submission = invoke_tool("submit_recommendation", {"recommendation": recommendation}, target)
        require(submission.get("source_framework") == "langgraph", "Submission framework differs")
        require(submission.get("run_id") == args.run_id, "Submission run_id differs")
        require(submission.get("target") == target, "Submission target differs")
        require(submission.get("status") == "pending", "Submitted recommendation is not pending")
        node_id = submission.get("node_id")
        rec_uuid = submission.get("uuid")
        revision_id = submission.get("revision_id")
        require(isinstance(node_id, int) and node_id > 0, "Submission node_id is missing")
        require(isinstance(rec_uuid, str) and rec_uuid, "Submission UUID is missing")
        require(isinstance(revision_id, int) and revision_id > 0, "Submission revision_id is missing")
        write_json(evidence / "submission.json", submission)

        status_data = invoke_tool("get_recommendation_status", {"recommendation_id": rec_uuid}, target)
        require(status_data.get("uuid") == rec_uuid, "Status UUID differs")
        require(status_data.get("status") == "pending", "Recommendation status is not pending")
        require(status_data.get("reviewed_at") is None, "Pending recommendation unexpectedly has reviewed_at")
        require(status_data.get("reviewer_username") is None, "Pending recommendation unexpectedly has reviewer")
        write_json(evidence / "status.json", status_data)

        after_submit = invoke_tool("get_image_context", {"target": target}, target)
        require(after_submit.get("target") == target, "Post-submit context target differs")
        require(
            after_submit.get("evidence_hash") == before_model.get("evidence_hash"),
            "Source context changed after recommendation submission",
        )
        write_json(evidence / "context-after-submit-summary.json", context_summary(after_submit))

        updated = advance_target(state, target, now())
        updated["recommendation_ids"] = [
            *state["recommendation_ids"],
            {
                "sequence": 1,
                "node_id": node_id,
                "uuid": rec_uuid,
                "revision_id": revision_id,
            },
        ]
        updated["validation_results"] = [*state["validation_results"], validation]
        updated["status"] = "running"
        updated["updated_at"] = now()
        return updated

    builder = StateGraph(LangGraphRunState)
    builder.add_node("canonical_slice", canonical_slice_node)
    builder.add_edge(START, "canonical_slice")
    builder.add_edge("canonical_slice", END)

    with SqliteSaver.from_conn_string(str(sqlite_path)) as saver:
        graph = builder.compile(checkpointer=saver)
        result_state = graph.invoke(state0, config)
        snapshot = graph.get_state(config)

    persisted_state = dict(snapshot.values)
    require(persisted_state == result_state, "Checkpoint state differs from graph result")
    require(persisted_state.get("next_target_index") == 1, "Canonical slice next_target_index is not 1")
    require([x["sequence"] for x in persisted_state.get("completed_target_identities", [])] == [1], "Completed sequence is not [1]")
    require(len(persisted_state.get("recommendation_ids", [])) == 1, "Checkpoint recommendation id count is not 1")
    require(len(persisted_state.get("validation_results", [])) == 1, "Checkpoint validation result count is not 1")
    write_json(evidence / "state-after-slice.json", persisted_state)

    configurable = dict((snapshot.config or {}).get("configurable", {}))
    write_json(evidence / "checkpoint-config.json", {
        "schema_version": 1,
        "run_id": args.run_id,
        "thread_id": args.run_id,
        "checkpointer": "langgraph.checkpoint.sqlite.SqliteSaver",
        "runtime_relative_path": str(sqlite_path.relative_to(repo)),
        "checkpoint_id": configurable.get("checkpoint_id"),
        "checkpoint_namespace": configurable.get("checkpoint_ns", ""),
    })

    db_bytes = sqlite_path.read_bytes()
    state_bytes = canonical(persisted_state)
    generic_patterns = [
        b"data:image/",
        b"Authorization:",
        b"Bearer ",
        b"Basic ",
        b"OPENAI_API_KEY",
        b"GATE2A_DRUPAL_PASSWORD",
        b"hidden_reasoning",
        b"chain_of_thought",
    ]
    pattern_hits = [p.decode("ascii", errors="replace") for p in generic_patterns if p in db_bytes or p in state_bytes]
    exact_hits: list[str] = []
    for label, value in privacy_probes.items():
        if not value:
            continue
        encoded = value.encode("utf-8")
        if encoded in db_bytes or encoded in state_bytes:
            exact_hits.append(label)
    privacy = {
        "schema_version": 1,
        "status": "pass" if not pattern_hits and not exact_hits else "fail",
        "generic_prohibited_pattern_hits": pattern_hits,
        "exact_ephemeral_value_hits": exact_hits,
        "article_body_persisted": "article_body" in exact_hits,
        "image_representation_persisted": "image_representation" in exact_hits,
        "drupal_password_persisted": "drupal_password" in exact_hits,
        "openai_api_key_persisted": "openai_api_key" in exact_hits,
        "hidden_reasoning_persisted": False if "hidden_reasoning" not in pattern_hits and "chain_of_thought" not in pattern_hits else True,
    }
    write_json(evidence / "checkpoint-privacy.json", privacy)
    require(privacy["status"] == "pass", f"Checkpoint privacy audit failed: {privacy!r}")

    write_json(evidence / "tool-traces.json", {
        "schema_version": 1,
        "run_id": args.run_id,
        "source_framework": "langgraph",
        "traces": traces,
    })
    write_json(evidence / "core-summary.json", {
        "schema_version": 1,
        "status": "pass",
        "run_id": args.run_id,
        "framework": "langgraph",
        "canonical_target_sequence": 1,
        "target_sequence_sha256": TARGET_HASH,
        "model_id": MODEL_ID,
        "temperature": TEMPERATURE,
        "prompt_version": PROMPT_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "model_invocations_attempted": call_counters["model_invocations_attempted"],
        "model_invocations_succeeded": call_counters["model_invocations_succeeded"],
        "automatic_model_retries_configured": 0,
        "semantic_retry_loop_performed": False,
        "drupal_semantic_call_count": sum(call_counters[name] for name in expected_tools),
        "drupal_semantic_call_counts": {name: call_counters[name] for name in expected_tools},
        "recommendation_write_count": call_counters["submit_recommendation"],
        "pending_status_observed": True,
        "source_context_stable_before_model_to_before_submit": True,
        "source_context_stable_before_model_to_after_submit": True,
        "next_target_index": persisted_state["next_target_index"],
        "completed_sequences": [x["sequence"] for x in persisted_state["completed_target_identities"]],
        "checkpoint_backend": persisted_state["checkpoint_backend"],
        "thread_id_equals_run_id": persisted_state["thread_id"] == args.run_id,
        "checkpoint_privacy_pass": privacy["status"] == "pass",
        "human_review_performed": False,
        "source_article_mutation_performed": False,
        "automatic_publication_performed": False,
        "gate2c_failure_injection_fired": persisted_state["gate2c_failure_injection_fired"],
        "continuation_boundary_armed": persisted_state["continuation_boundary_armed"],
        "continuation_boundary_reached": persisted_state["continuation_boundary_reached"],
        "runtime_db_relative_path": str(sqlite_path.relative_to(repo)),
        "runtime_db_sha256": hashlib.sha256(db_bytes).hexdigest(),
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
