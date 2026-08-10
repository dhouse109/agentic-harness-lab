#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from agentic_harness_langgraph.state import (
    LangGraphRunState,
    advance_target,
    initial_state,
)

TARGETS_REL = (
    "evidence/gates/gate-2a/tool-adapters/"
    "gate2a-step03-20260809T233127Z-2375581/targets.json"
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_event(path: Path, value) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(value, sort_keys=True) + "\n")


def load_targets(repo: Path) -> list[dict]:
    value = json.loads((repo / TARGETS_REL).read_text(encoding="utf-8"))
    if not isinstance(value, list) or len(value) != 12:
        raise RuntimeError("Accepted Step 2A.03 target list must contain exactly 12 targets")
    sequences = [int(item["sequence"]) for item in value]
    if sequences != list(range(1, 13)):
        raise RuntimeError(f"Accepted target sequence is not canonical: {sequences!r}")
    return value


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--started-at", required=True)
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    evidence = Path(args.evidence).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    events = evidence / "process-1-events.jsonl"
    sqlite_path = repo / "langchain/.gate2a-runtime" / f"{args.run_id}.sqlite"
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    targets = load_targets(repo)

    state0 = initial_state(args.run_id, args.started_at)
    config = {"configurable": {"thread_id": args.run_id}}

    def make_node(target_index: int):
        def node(state: LangGraphRunState):
            before = int(state["next_target_index"])
            updated = advance_target(state, targets[target_index], now())
            append_event(events, {
                "event": "advance",
                "process": 1,
                "sequence": target_index + 1,
                "before_next_target_index": before,
                "after_next_target_index": updated["next_target_index"],
                "thread_id": args.run_id,
            })
            return updated
        return node

    builder = StateGraph(LangGraphRunState)
    builder.add_node("advance_1", make_node(0))
    builder.add_node("advance_2", make_node(1))
    builder.add_node("advance_3", make_node(2))
    builder.add_edge(START, "advance_1")
    builder.add_edge("advance_1", "advance_2")
    builder.add_edge("advance_2", "advance_3")
    builder.add_edge("advance_3", END)

    append_event(events, {
        "event": "process-start",
        "process": 1,
        "run_id": args.run_id,
        "thread_id": args.run_id,
        "sqlite_relative_path": str(sqlite_path.relative_to(repo)),
    })

    with SqliteSaver.from_conn_string(str(sqlite_path)) as saver:
        graph = builder.compile(checkpointer=saver)
        result = graph.invoke(state0, config)
        snapshot = graph.get_state(config)

    values = dict(snapshot.values)
    if values != result:
        raise RuntimeError("Process-1 checkpoint snapshot does not equal graph result")
    if int(values.get("next_target_index", -1)) != 3:
        raise RuntimeError(f"Process-1 next_target_index is not 3: {values.get('next_target_index')}")
    completed = [int(x["sequence"]) for x in values.get("completed_target_identities", [])]
    if completed != [1, 2, 3]:
        raise RuntimeError(f"Process-1 completed sequences are not [1,2,3]: {completed!r}")

    configurable = dict((snapshot.config or {}).get("configurable", {}))
    checkpoint_id = configurable.get("checkpoint_id")
    checkpoint_ns = configurable.get("checkpoint_ns", "")

    write_json(evidence / "state-before.json", values)
    write_json(evidence / "checkpoint-config.json", {
        "schema_version": 1,
        "run_id": args.run_id,
        "thread_id": args.run_id,
        "config_shape": {"configurable": {"thread_id": "<run-id>"}},
        "checkpointer": "langgraph.checkpoint.sqlite.SqliteSaver",
        "constructor": "SqliteSaver.from_conn_string(path)",
        "runtime_root": "langchain/.gate2a-runtime/",
        "sqlite_relative_path": str(sqlite_path.relative_to(repo)),
        "checkpoint_id": checkpoint_id,
        "checkpoint_namespace": checkpoint_ns,
        "process_boundary_required": True,
        "source_targets": TARGETS_REL,
        "model_call_performed": False,
        "drupal_call_performed": False,
        "drupal_mutation_performed": False,
    })
    append_event(events, {
        "event": "checkpoint-persisted",
        "process": 1,
        "next_target_index": values["next_target_index"],
        "completed_sequences": completed,
        "checkpoint_id": checkpoint_id,
        "checkpoint_namespace": checkpoint_ns,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
