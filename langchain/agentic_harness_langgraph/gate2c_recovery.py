"""Model-free Gate 2C LangGraph process-recovery rehearsal adapter."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

SEAM = "after target 6 is fully persisted and before target 7 begins"


class RehearsalState(TypedDict):
    schema_version: int
    trial_id: str
    run_id: str
    framework_origin: str
    completed_sequences: list[int]
    next_target: int
    target_7_started: bool
    synthetic_recommendation_identities: list[str]
    first_post_restart_target: int | None
    model_generations: int
    provider_requests: int
    recommendation_writes: int
    source_mutations: int


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def identity(run_id: str, sequence: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"gate2c-model-free:{run_id}:{sequence}"))


def initial(trial_id: str, run_id: str) -> RehearsalState:
    return {
        "schema_version": 1,
        "trial_id": trial_id,
        "run_id": run_id,
        "framework_origin": "langgraph",
        "completed_sequences": [],
        "next_target": 1,
        "target_7_started": False,
        "synthetic_recommendation_identities": [],
        "first_post_restart_target": None,
        "model_generations": 0,
        "provider_requests": 0,
        "recommendation_writes": 0,
        "source_mutations": 0,
    }


def build_graph(*, recovery: bool, control: Path, checkpointer: Any) -> Any:
    builder = StateGraph(RehearsalState)
    for sequence in range(1, 13):
        def target(state: RehearsalState, seq: int = sequence) -> RehearsalState:
            require(state["next_target"] == seq, f"target order drift at {seq}")
            require(seq not in state["completed_sequences"], f"target replay at {seq}")
            if recovery and state["first_post_restart_target"] is None:
                require(seq == 7, "target 7 was not first post-restart work")
            completed = [*state["completed_sequences"], seq]
            ids = [*state["synthetic_recommendation_identities"], identity(state["run_id"], seq)]
            return {
                **state,
                "completed_sequences": completed,
                "next_target": seq + 1,
                "target_7_started": state["target_7_started"] or seq == 7,
                "synthetic_recommendation_identities": ids,
                "first_post_restart_target": 7 if recovery and state["first_post_restart_target"] is None else state["first_post_restart_target"],
            }
        builder.add_node(f"target_{sequence:02d}", target)

    def seam(state: RehearsalState) -> RehearsalState:
        require(state["completed_sequences"] == [1, 2, 3, 4, 5, 6], "LangGraph midpoint sequence")
        require(state["next_target"] == 7 and state["target_7_started"] is False, "LangGraph midpoint boundary")
        if recovery:
            return state
        midpoint = dict(state)
        midpoint_path = control / "midpoint.json"
        write_json(midpoint_path, midpoint)
        write_json(control / "seam-ready.json", {
            "schema_version": 1,
            "semantic_boundary": SEAM,
            "framework_origin": "langgraph",
            "trial_id": state["trial_id"],
            "run_id": state["run_id"],
            "completed_sequences": [1, 2, 3, 4, 5, 6],
            "next_target": 7,
            "target_7_started": False,
            "midpoint_sha256": file_sha(midpoint_path),
            "independently_verifiable": True,
            "host_worker_pid": os.getpid(),
            "actual_worker_pid": os.getpid(),
        })
        while True:
            time.sleep(1)

    builder.add_node("seam", seam)
    builder.add_edge(START, "target_01")
    for sequence in range(1, 6):
        builder.add_edge(f"target_{sequence:02d}", f"target_{sequence + 1:02d}")
    builder.add_edge("target_06", "seam")
    builder.add_edge("seam", "target_07")
    for sequence in range(7, 12):
        builder.add_edge(f"target_{sequence:02d}", f"target_{sequence + 1:02d}")
    builder.add_edge("target_12", END)
    return builder.compile(checkpointer=checkpointer)


def worker(args: argparse.Namespace) -> int:
    require(not os.environ.get("OPENAI_API_KEY"), "OPENAI_API_KEY must be unset")
    control = args.control_dir.resolve()
    runtime = args.runtime_db.resolve()
    require("/.cache/gate2c-step02/" in runtime.as_posix(), "disposable runtime root required")
    runtime.parent.mkdir(parents=True, exist_ok=True)
    config = {"configurable": {"thread_id": args.run_id}}
    with SqliteSaver.from_conn_string(str(runtime)) as saver:
        if args.mode == "verify-checkpoint":
            checkpoint_tuple = saver.get_tuple(config)
            require(checkpoint_tuple is not None, "durable LangGraph checkpoint missing")
            state = dict(checkpoint_tuple.checkpoint.get("channel_values") or {})
            require(state.get("trial_id") == args.trial_id, "durable checkpoint trial identity")
            require(state.get("run_id") == args.run_id, "durable checkpoint run identity")
            require(state.get("framework_origin") == "langgraph", "durable checkpoint framework identity")
            require(state.get("completed_sequences") == [1, 2, 3, 4, 5, 6], "durable target-6 state missing")
            require(state.get("next_target") == 7 and state.get("target_7_started") is False, "durable target-7 boundary")
            identities = state.get("synthetic_recommendation_identities")
            require(isinstance(identities, list) and len(identities) == 6 and len(set(identities)) == 6, "durable identity set")
            require(all(state.get(key) == 0 for key in ("model_generations", "provider_requests", "recommendation_writes", "source_mutations")), "durable zero-operation boundary")
            require(not checkpoint_tuple.pending_writes, "durable checkpoint has pending writes")
            durable_config = checkpoint_tuple.config.get("configurable", {})
            checkpoint_id = durable_config.get("checkpoint_id")
            require(durable_config.get("thread_id") == args.run_id, "durable checkpoint thread identity")
            require(durable_config.get("checkpoint_ns", "") == "", "durable checkpoint namespace")
            require(isinstance(checkpoint_id, str) and checkpoint_id, "durable checkpoint ID")
            require(checkpoint_tuple.metadata.get("source") == "loop" and checkpoint_tuple.metadata.get("step") == 6, "durable checkpoint step")
            projection = {
                key: state[key]
                for key in (
                    "schema_version", "trial_id", "run_id", "framework_origin",
                    "completed_sequences", "next_target", "target_7_started",
                    "synthetic_recommendation_identities", "first_post_restart_target",
                    "model_generations", "provider_requests", "recommendation_writes", "source_mutations",
                )
            }
            write_json(args.output, {
                "schema_version": 1,
                "status": "PASS_DURABLE_CHECKPOINT",
                "public_api": "SqliteSaver.get_tuple",
                "checkpoint_id": checkpoint_id,
                "checkpoint_namespace": "",
                "checkpoint_metadata_step": 6,
                "pending_write_count": 0,
                "state_sha256": canonical_sha(projection),
                **projection,
            })
            return 0
        graph = build_graph(recovery=args.mode == "recover", control=control, checkpointer=saver)
        if args.mode == "prekill":
            graph.invoke(initial(args.trial_id, args.run_id), config, durability="sync")
            raise RuntimeError("prekill worker escaped seam")
        before = graph.get_state(config)
        state = dict(before.values)
        require(state.get("completed_sequences") == [1, 2, 3, 4, 5, 6], "stored target-6 state missing")
        require(state.get("next_target") == 7, "stored next target differs")
        result = graph.invoke(None, config)
        require(result["completed_sequences"] == list(range(1, 13)), "recovery completion order")
        require(result["first_post_restart_target"] == 7, "first post-restart target")
        require(len(set(result["synthetic_recommendation_identities"])) == 12, "duplicate synthetic identity")
        require(all(result[key] == 0 for key in ("model_generations", "provider_requests", "recommendation_writes", "source_mutations")), "zero-operation boundary")
        write_json(args.output, {
            "schema_version": 1,
            "status": "PASS",
            "framework_origin": "langgraph",
            "trial_id": args.trial_id,
            "run_id": args.run_id,
            "persistence": "SqliteSaver",
            "thread_id": args.run_id,
            "completed_sequences": result["completed_sequences"],
            "first_post_restart_target": 7,
            "replay_count": 0,
            "duplicate_count": 0,
            "model_generations": 0,
            "provider_requests": 0,
            "drupal_operations": 0,
        })
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["prekill", "recover", "verify-checkpoint"])
    parser.add_argument("--trial-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--control-dir", required=True, type=Path)
    parser.add_argument("--runtime-db", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode in {"recover", "verify-checkpoint"}:
        require(args.output is not None, f"{args.mode} output required")
    return worker(args)


if __name__ == "__main__":
    raise SystemExit(main())
