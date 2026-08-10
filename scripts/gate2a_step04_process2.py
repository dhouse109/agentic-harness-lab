#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from agentic_harness_langgraph.state import LangGraphRunState

PROHIBITED_KEY_FRAGMENTS = (
    "api_key", "authorization", "password", "secret", "credential",
    "raw_image", "image_bytes", "data_url", "base64", "article_body",
    "hidden_reasoning", "chain_of_thought",
)
PROHIBITED_BYTE_PATTERNS = (
    b"data:image/",
    b"Authorization:",
    b"Bearer ",
    b"Basic ",
    b"OPENAI_API_KEY",
    b"article_body",
    b"hidden_reasoning",
    b"chain_of_thought",
)


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_event(path: Path, value) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(value, sort_keys=True) + "\n")


def walk_keys(value, prefix=""):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            found.append((path, str(key)))
            found.extend(walk_keys(child, path))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            found.extend(walk_keys(child, f"{prefix}[{idx}]"))
    return found


def build_graph():
    # Same graph channel/node definitions as process 1. It is compiled only so
    # SqliteSaver can hydrate the persisted checkpoint; nodes are not invoked.
    def passthrough(state: LangGraphRunState):
        return dict(state)

    builder = StateGraph(LangGraphRunState)
    builder.add_node("advance_1", passthrough)
    builder.add_node("advance_2", passthrough)
    builder.add_node("advance_3", passthrough)
    builder.add_edge(START, "advance_1")
    builder.add_edge("advance_1", "advance_2")
    builder.add_edge("advance_2", "advance_3")
    builder.add_edge("advance_3", END)
    return builder


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    evidence = Path(args.evidence).resolve()
    events = evidence / "process-2-events.jsonl"
    sqlite_path = repo / "langchain/.gate2a-runtime" / f"{args.run_id}.sqlite"
    before = json.loads((evidence / "state-before.json").read_text(encoding="utf-8"))
    schema = json.loads((repo / "shared/schemas/langgraph-run-state.schema.json").read_text(encoding="utf-8"))

    config = {"configurable": {"thread_id": args.run_id}}
    negative_thread = args.run_id + "-isolation-negative"
    negative_config = {"configurable": {"thread_id": negative_thread}}

    append_event(events, {
        "event": "process-start",
        "process": 2,
        "run_id": args.run_id,
        "thread_id": args.run_id,
        "fresh_python_process": True,
    })

    with SqliteSaver.from_conn_string(str(sqlite_path)) as saver:
        graph = build_graph().compile(checkpointer=saver)
        same_snapshot = graph.get_state(config)
        negative_snapshot = graph.get_state(negative_config)

    after = dict(same_snapshot.values)
    negative_values = dict(negative_snapshot.values)
    write_json(evidence / "state-after-reload.json", after)

    same_equal = after == before
    next_index = int(after.get("next_target_index", -1))
    completed = [int(x["sequence"]) for x in after.get("completed_target_identities", [])]
    negative_empty = negative_values == {}

    if not same_equal:
        raise RuntimeError("Reloaded state is not identical to process-1 retained state")
    if next_index != 3:
        raise RuntimeError(f"Reloaded next_target_index is not 3: {next_index}")
    if completed != [1, 2, 3]:
        raise RuntimeError(f"Reloaded completed sequences are not [1,2,3]: {completed!r}")
    if not negative_empty:
        raise RuntimeError(f"Negative-control thread inherited state: {negative_values!r}")

    write_json(evidence / "isolation-negative-control.json", {
        "schema_version": 1,
        "primary_thread_id": args.run_id,
        "negative_thread_id": negative_thread,
        "primary_state_reloaded": True,
        "primary_state_equal_to_process_1": same_equal,
        "negative_thread_state": negative_values,
        "negative_thread_empty": negative_empty,
        "status": "pass",
    })

    allowed = set(schema.get("properties", {}).keys())
    required = set(schema.get("required", []))
    observed = set(after.keys())
    missing = sorted(required - observed)
    unexpected = sorted(observed - allowed)

    bad_keys = []
    for path, key in walk_keys(after):
        lower = key.lower()
        if any(fragment in lower for fragment in PROHIBITED_KEY_FRAGMENTS):
            bad_keys.append(path)

    encoded = json.dumps(after, sort_keys=True).encode("utf-8")
    db_bytes = sqlite_path.read_bytes()
    state_pattern_hits = [
        p.decode("ascii", errors="replace")
        for p in PROHIBITED_BYTE_PATTERNS
        if p in encoded
    ]
    db_pattern_hits = [
        p.decode("ascii", errors="replace")
        for p in PROHIBITED_BYTE_PATTERNS
        if p in db_bytes
    ]

    audit_ok = not missing and not unexpected and not bad_keys and not state_pattern_hits and not db_pattern_hits
    persisted = {
        "schema_version": 1,
        "status": "pass" if audit_ok else "fail",
        "observed_top_level_keys": sorted(observed),
        "required_keys_missing": missing,
        "unexpected_top_level_keys": unexpected,
        "prohibited_key_paths": bad_keys,
        "prohibited_state_value_patterns": state_pattern_hits,
        "prohibited_sqlite_byte_patterns": db_pattern_hits,
        "raw_image_bytes_or_data_urls_persisted": False if not state_pattern_hits and not db_pattern_hits else True,
        "credentials_or_auth_material_persisted": False if not bad_keys and not state_pattern_hits and not db_pattern_hits else True,
        "article_body_or_hidden_reasoning_persisted": False if not bad_keys and not state_pattern_hits and not db_pattern_hits else True,
        "shared_runtime_storage_used": False,
        "model_call_performed": False,
        "drupal_call_performed": False,
        "drupal_mutation_performed": False,
    }
    write_json(evidence / "persisted-field-audit.json", persisted)
    if not audit_ok:
        raise RuntimeError(f"Persisted-field/privacy audit failed: {persisted!r}")

    append_event(events, {
        "event": "reload-observed",
        "process": 2,
        "same_thread_state_equal": same_equal,
        "next_target_index": next_index,
        "completed_sequences": completed,
    })
    append_event(events, {
        "event": "isolation-negative-control",
        "process": 2,
        "negative_thread_id": negative_thread,
        "negative_thread_empty": negative_empty,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
