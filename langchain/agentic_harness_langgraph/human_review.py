"""Gate 2A Step 2A.06 persisted LangGraph interrupt + Drupal review resume.

No model is instantiated or invoked here. The accepted Step 2A.05 structured
output is reused as provenance for a fresh Step 2A.06 recommendation run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from agentic_harness_langgraph.state import LangGraphRunState, advance_target, initial_state
from agentic_harness_langgraph.tools import build_tools
from shared.drupal_client.client import DrupalClient

ACCEPTED_STEP05_REL = "evidence/gates/gate-2a/canonical-slice/gate2a-step05-20260810T140133Z-0025b888"
TARGET_HASH = "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728"
VALIDATOR_VERSION = "gate05-validator-1.0.0"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError(message)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def envelope(value: Any, expected_name: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{expected_name} result is not an object")
    expected = {"schema_version", "tool_name", "ok", "timestamp", "correlation_id", "data", "error"}
    require(set(value) == expected, f"{expected_name} envelope keys differ from frozen schema")
    require(value["schema_version"] == 1 and value["tool_name"] == expected_name, f"{expected_name} envelope mismatch")
    require(value["ok"] is True and value["error"] is None, f"{expected_name} failed: {value.get('error')!r}")
    require(isinstance(value["data"], dict), f"{expected_name} data is not an object")
    return value["data"]


def load_counters(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "model_invocations_attempted": 0,
        "model_invocations_succeeded": 0,
        "automatic_model_retries_configured": 0,
        "semantic_retry_loop_performed": False,
        "get_image_context": 0,
        "submit_recommendation": 0,
        "get_recommendation_status": 0,
    }


def task_interrupt_count(snapshot: Any) -> int:
    total = 0
    for task in getattr(snapshot, "tasks", ()) or ():
        total += len(getattr(task, "interrupts", ()) or ())
    return total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--mode", choices=("start", "resume"), required=True)
    args = ap.parse_args()

    require(
        re.fullmatch(r"langgraph-[0-9]{8}T[0-9]{6}Z-[a-z0-9]{4,12}", args.run_id) is not None,
        "Step 2A.06 run_id does not match the frozen langgraph experiment format",
    )

    repo = Path(args.repo).resolve()
    evidence = Path(args.evidence).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    accepted = repo / ACCEPTED_STEP05_REL
    require(accepted.is_dir(), "Accepted Step 2A.05 evidence directory is missing")

    base_url = os.environ.get("GATE2A_DRUPAL_BASE_URL", "")
    username = os.environ.get("GATE2A_DRUPAL_USERNAME", "")
    password = os.environ.get("GATE2A_DRUPAL_PASSWORD", "")
    require(base_url and username and password, "Drupal live environment is incomplete")
    require(username == "agent_bot", "Step 2A.06 semantic operations must run as agent_bot")
    require(not os.environ.get("OPENAI_API_KEY"), "Step 2A.06 must run with OPENAI_API_KEY unset")

    accepted_rec = json.loads((accepted / "recommendation.json").read_text(encoding="utf-8"))
    accepted_model = json.loads((accepted / "model-output.json").read_text(encoding="utf-8"))
    accepted_validation = json.loads((accepted / "validation.json").read_text(encoding="utf-8"))
    target = accepted_rec["target"]
    require(target.get("sequence") == 1, "Accepted Step 2A.05 recommendation is not canonical target 1")
    require(accepted_rec.get("proposed_alt_text") == accepted_model.get("proposed_alt_text"), "Accepted model/recommendation output differs")
    require(accepted_rec.get("validator_version") == VALIDATOR_VERSION, "Accepted validator version differs")

    if not (evidence / "accepted-step05-provenance.json").exists():
        write_json(evidence / "accepted-step05-provenance.json", {
            "schema_version": 1,
            "accepted_evidence": ACCEPTED_STEP05_REL,
            "accepted_run_id": accepted_rec.get("run_id"),
            "accepted_recommendation_sha256": hashlib.sha256(canonical(accepted_rec)).hexdigest(),
            "accepted_model_output_sha256": hashlib.sha256(canonical(accepted_model)).hexdigest(),
            "model_output_reused": True,
            "new_model_call_performed": False,
        })

    client = DrupalClient(base_url=base_url, username=username, password=password, verify_tls=False, timeout_seconds=60)
    tools = build_tools(client, correlation_id=f"{args.run_id}-human-review")
    counters_path = evidence / "call-counters.json"
    counters = load_counters(counters_path)
    write_json(counters_path, counters)

    def invoke_tool(name: str, payload: dict[str, Any]) -> dict[str, Any]:
        counters[name] += 1
        write_json(counters_path, counters)
        return envelope(tools[name].invoke(payload), name)

    sqlite_path = repo / "langchain/.gate2a-runtime" / f"{args.run_id}.sqlite"
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    config = {"configurable": {"thread_id": args.run_id}}

    def prepare_pending(state: LangGraphRunState) -> LangGraphRunState:
        require(int(state["next_target_index"]) == 0, "Human-review proof must begin at canonical target index 0")
        context = invoke_tool("get_image_context", {"target": target})
        require(context.get("target") == target, "Current target differs from accepted Step 2A.05 target")
        require(context.get("evidence_hash") == accepted_rec.get("evidence_hash"), "Current source/image evidence differs from accepted Step 2A.05 evidence")

        recommendation = deepcopy(accepted_rec)
        recommendation["run_id"] = args.run_id
        recommendation["source_framework"] = "langgraph"
        recommendation["validator_version"] = VALIDATOR_VERSION
        submission = invoke_tool("submit_recommendation", {"recommendation": recommendation})
        require(submission.get("run_id") == args.run_id, "Submitted run_id differs")
        require(submission.get("source_framework") == "langgraph", "Submitted framework differs")
        require(submission.get("target") == target, "Submitted target differs")
        require(submission.get("status") == "pending", "Submitted recommendation is not pending")
        rec_uuid = submission.get("uuid")
        require(isinstance(rec_uuid, str) and rec_uuid, "Submitted UUID missing")
        pending_status = invoke_tool("get_recommendation_status", {"recommendation_id": rec_uuid})
        require(pending_status.get("status") == "pending", "Pre-interrupt recommendation is not pending")
        require(pending_status.get("reviewer_username") is None and pending_status.get("reviewed_at") is None, "Pending recommendation already has reviewer metadata")

        write_json(evidence / "pending-recommendation.json", {
            "schema_version": 1,
            "accepted_model_output_reused": True,
            "new_model_call_performed": False,
            "recommendation": recommendation,
            "submission": submission,
            "pending_status": pending_status,
        })

        updated = advance_target(state, target, now())
        updated["recommendation_ids"] = [{
            "sequence": 1,
            "node_id": submission.get("node_id"),
            "uuid": rec_uuid,
            "revision_id": submission.get("revision_id"),
        }]
        updated["validation_results"] = [accepted_validation]
        updated["status"] = "interrupted"
        updated["interrupted_at"] = now()
        updated["updated_at"] = now()
        return updated

    def await_review(state: LangGraphRunState) -> LangGraphRunState:
        rec = state["recommendation_ids"][0]
        signal = interrupt({
            "kind": "await_drupal_review",
            "run_id": args.run_id,
            "recommendation_uuid": rec["uuid"],
            "reviewer": "editor_dana",
            "required_action": "edit-and-approve",
        })
        require(isinstance(signal, dict) and signal.get("review_complete") is True, "Resume signal is invalid")
        updated = deepcopy(dict(state))
        updated["resumed_at"] = now()
        updated["updated_at"] = now()
        updated["status"] = "running"
        write_json(evidence / "resume-event.json", {
            "schema_version": 1,
            "event": "langgraph-resume",
            "run_id": args.run_id,
            "thread_id": args.run_id,
            "resumed_at": updated["resumed_at"],
            "resume_signal": {"review_complete": True},
        })
        return updated  # type: ignore[return-value]

    def observe_review(state: LangGraphRunState) -> LangGraphRunState:
        rec_uuid = state["recommendation_ids"][0]["uuid"]
        status = invoke_tool("get_recommendation_status", {"recommendation_id": rec_uuid})
        require(status.get("uuid") == rec_uuid, "Post-review status UUID differs")
        require(status.get("status") == "approved", "Post-review status is not approved")
        require(status.get("reviewer_username") == "editor_dana", "Post-review reviewer is not editor_dana")
        require(isinstance(status.get("reviewed_at"), str) and status.get("reviewed_at"), "Post-review timestamp is missing")
        write_json(evidence / "post-review-status.json", status)

        context = invoke_tool("get_image_context", {"target": target})
        require(context.get("target") == target, "Post-review source target differs")
        require(context.get("evidence_hash") == accepted_rec.get("evidence_hash"), "Source/image evidence changed through human review")
        write_json(evidence / "post-review-context-summary.json", {
            "schema_version": 1,
            "target": target,
            "evidence_hash": context.get("evidence_hash"),
            "source_context_matches_accepted_step05": True,
            "article_body_retained": False,
            "image_representation_retained": False,
        })
        updated = deepcopy(dict(state))
        updated["updated_at"] = now()
        updated["status"] = "running"
        return updated  # type: ignore[return-value]

    builder = StateGraph(LangGraphRunState)
    builder.add_node("prepare_pending", prepare_pending)
    builder.add_node("await_review", await_review)
    builder.add_node("observe_review", observe_review)
    builder.add_edge(START, "prepare_pending")
    builder.add_edge("prepare_pending", "await_review")
    builder.add_edge("await_review", "observe_review")
    builder.add_edge("observe_review", END)

    if args.mode == "start":
        require(not sqlite_path.exists(), "Step 2A.06 runtime DB already exists before start")
    else:
        require(sqlite_path.exists() and sqlite_path.stat().st_size > 0, "Step 2A.06 runtime DB is missing for resume")

    with SqliteSaver.from_conn_string(str(sqlite_path)) as saver:
        graph = builder.compile(checkpointer=saver)
        if args.mode == "start":
            state0 = initial_state(args.run_id, now())
            graph.invoke(state0, config)
            snapshot = graph.get_state(config)
            persisted = dict(snapshot.values)
            count = task_interrupt_count(snapshot)
            require(count > 0, "No genuine LangGraph interrupt is present in the checkpoint")
            require(persisted.get("status") == "interrupted", "Checkpoint status is not the frozen interrupted state")
            require(persisted.get("interrupted_at") is not None, "Checkpoint interrupted_at is missing")
            require(persisted.get("run_id") == args.run_id and persisted.get("thread_id") == args.run_id, "Run/thread identity differs")
            write_json(evidence / "checkpoint-before-review.json", persisted)
            write_json(evidence / "interrupt-event.json", {
                "schema_version": 1,
                "event": "langgraph-interrupt",
                "run_id": args.run_id,
                "thread_id": args.run_id,
                "interrupt_count": count,
                "next_nodes": list(getattr(snapshot, "next", ()) or ()),
                "interrupted_at": persisted["interrupted_at"],
                "authoritative_reviewer": "editor_dana",
                "approval_system": "Drupal alt_text_suggestion revision workflow",
            })
            configurable = dict((snapshot.config or {}).get("configurable", {}))
            write_json(evidence / "checkpoint-config.json", {
                "schema_version": 1,
                "run_id": args.run_id,
                "thread_id": args.run_id,
                "checkpoint_id": configurable.get("checkpoint_id"),
                "checkpoint_namespace": configurable.get("checkpoint_ns", ""),
                "runtime_relative_path": str(sqlite_path.relative_to(repo)),
                "checkpointer": "langgraph.checkpoint.sqlite.SqliteSaver",
            })
        else:
            before = graph.get_state(config)
            require(task_interrupt_count(before) > 0, "Stored checkpoint is not genuinely interrupted")
            require(dict(before.values).get("run_id") == args.run_id, "Stored run_id differs before resume")
            result = graph.invoke(Command(resume={"review_complete": True}), config)
            after = graph.get_state(config)
            persisted = dict(after.values)
            require(persisted == result, "Post-resume checkpoint differs from graph result")
            require(task_interrupt_count(after) == 0, "Interrupt remains after successful resume")
            require(persisted.get("resumed_at") is not None, "resumed_at is missing")
            require(persisted.get("run_id") == args.run_id and persisted.get("thread_id") == args.run_id, "Run/thread identity changed on resume")
            write_json(evidence / "checkpoint-after-resume.json", persisted)

    counters = load_counters(counters_path)
    require(counters["model_invocations_attempted"] == 0 and counters["model_invocations_succeeded"] == 0, "Step 2A.06 model-call counter changed")
    require(counters["automatic_model_retries_configured"] == 0 and counters["semantic_retry_loop_performed"] is False, "Step 2A.06 retry policy changed")
    write_json(counters_path, counters)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
