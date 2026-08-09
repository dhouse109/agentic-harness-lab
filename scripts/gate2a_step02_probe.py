#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as md
import inspect
import json
import os
import sys
import traceback
from pathlib import Path
from typing import TypedDict

EXPECTED = {
    "python": "3.12.13",
    "langchain": "1.3.14",
    "langgraph": "1.2.10",
    "langgraph-checkpoint-sqlite": "3.1.1",
}

PROHIBITED_KEYS = {
    "api_key", "authorization", "password", "secret", "base64",
    "image_bytes", "data_url", "raw_image", "credentials",
}

def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def version(name: str) -> str:
    try:
        return md.version(name)
    except md.PackageNotFoundError:
        return "NOT_INSTALLED"

def rel_source(obj, venv: Path) -> str:
    try:
        p = Path(inspect.getsourcefile(obj) or inspect.getfile(obj)).resolve()
        try:
            return str(p.relative_to(venv.resolve()))
        except ValueError:
            return str(p)
    except Exception as exc:
        return f"<unavailable:{type(exc).__name__}>"

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    evidence = Path(args.evidence).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    runtime_root = repo / "langchain/.gate2a-runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    venv = repo / "langchain/.venv"

    observed = {
        "python": ".".join(map(str, sys.version_info[:3])),
        "langchain": version("langchain"),
        "langchain-openai": version("langchain-openai"),
        "langgraph": version("langgraph"),
        "langgraph-checkpoint": version("langgraph-checkpoint"),
        "langgraph-checkpoint-sqlite": version("langgraph-checkpoint-sqlite"),
        "openai": version("openai"),
    }
    env = {
        "schema_version": 1,
        "run_id": args.run_id,
        "expected": EXPECTED,
        "observed": observed,
        "versions_match": all(observed.get(k) == v for k, v in EXPECTED.items()),
        "model_call_performed": False,
        "drupal_state_mutated": False,
        "runtime_root": "langchain/.gate2a-runtime",
    }
    write_json(evidence / "environment.json", env)
    (evidence / "imports-and-versions.txt").write_text(
        "\n".join(f"{k}={v}" for k, v in sorted(observed.items())) + "\n",
        encoding="utf-8",
    )

    result = {
        "status": "fail",
        "run_id": args.run_id,
        "model_call_performed": False,
        "drupal_state_mutated": False,
        "dependency_change": False,
        "checks": {},
        "errors": [],
    }

    try:
        if not env["versions_match"]:
            raise RuntimeError(f"Pinned version mismatch: {observed!r}")

        from langgraph.graph import START, END, StateGraph
        from langgraph.checkpoint.sqlite import SqliteSaver
        from langgraph.types import Command, interrupt
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage
        from langchain_core.tools import tool

        source_map = {
            "StateGraph": rel_source(StateGraph, venv),
            "SqliteSaver": rel_source(SqliteSaver, venv),
            "interrupt": rel_source(interrupt, venv),
            "Command": rel_source(Command, venv),
            "ChatOpenAI": rel_source(ChatOpenAI, venv),
            "HumanMessage": rel_source(HumanMessage, venv),
            "tool": rel_source(tool, venv),
        }
        (evidence / "installed-source-map.md").write_text(
            "# Installed source map\n\n" +
            "\n".join(f"- `{k}`: `{v}`" for k, v in source_map.items()) + "\n",
            encoding="utf-8",
        )

        class SimpleState(TypedDict):
            value: int
            trace: list[str]

        def inc(state: SimpleState):
            return {"value": state["value"] + 1, "trace": [*state["trace"], "inc"]}

        b = StateGraph(SimpleState)
        b.add_node("inc", inc)
        b.add_edge(START, "inc")
        b.add_edge("inc", END)
        simple = b.compile()
        simple_result = simple.invoke({"value": 1, "trace": []})
        if simple_result != {"value": 2, "trace": ["inc"]}:
            raise RuntimeError(f"Unexpected model-free graph result: {simple_result!r}")
        result["checks"]["stategraph_model_free"] = True

        # SQLite checkpoint write + connection-reload using synthetic state.
        sqlite_path = runtime_root / f"{args.run_id}.sqlite"
        thread_id = args.run_id
        config = {"configurable": {"thread_id": thread_id}}

        class CheckState(TypedDict):
            counter: int
            trace: list[str]

        def bump(state: CheckState):
            return {"counter": state["counter"] + 1, "trace": [*state["trace"], "bump"]}

        def build(cp):
            bb = StateGraph(CheckState)
            bb.add_node("bump", bump)
            bb.add_edge(START, "bump")
            bb.add_edge("bump", END)
            return bb.compile(checkpointer=cp)

        with SqliteSaver.from_conn_string(str(sqlite_path)) as cp:
            graph = build(cp)
            first = graph.invoke({"counter": 0, "trace": []}, config)
            snap1 = graph.get_state(config)
        with SqliteSaver.from_conn_string(str(sqlite_path)) as cp:
            graph2 = build(cp)
            snap2 = graph2.get_state(config)

        checkpoint_ok = (
            first == {"counter": 1, "trace": ["bump"]}
            and snap1.values == snap2.values == first
            and sqlite_path.is_file() and sqlite_path.stat().st_size > 0
        )
        checkpoint_probe = {
            "status": "pass" if checkpoint_ok else "fail",
            "checkpointer": "langgraph.checkpoint.sqlite.SqliteSaver",
            "constructor": "SqliteSaver.from_conn_string(path)",
            "thread_id": thread_id,
            "config_shape": {"configurable": {"thread_id": "<run-id>"}},
            "checkpoint_namespace": (
                snap2.config.get("configurable", {}).get("checkpoint_ns")
                if getattr(snap2, "config", None) else None
            ),
            "state_after_reload": snap2.values,
            "db_relative_path": str(sqlite_path.relative_to(repo)),
            "db_sha256": hashlib.sha256(sqlite_path.read_bytes()).hexdigest(),
            "raw_image_bytes_persisted": False,
            "credentials_persisted": False,
        }
        write_json(evidence / "checkpointer-probe.json", checkpoint_probe)
        if not checkpoint_ok:
            raise RuntimeError("SQLite checkpoint creation/reload probe failed")
        result["checks"]["sqlite_checkpoint_reload"] = True

        # interrupt/resume against the same SQLite checkpointer.
        interrupt_db = runtime_root / f"{args.run_id}-interrupt.sqlite"
        interrupt_thread = args.run_id + "-interrupt"
        iconfig = {"configurable": {"thread_id": interrupt_thread}}

        class IState(TypedDict, total=False):
            value: int
            review: str

        def pause(state: IState):
            decision = interrupt({"kind": "gate2a-runtime-probe", "value": state["value"]})
            return {"review": str(decision)}

        ib = StateGraph(IState)
        ib.add_node("pause", pause)
        ib.add_edge(START, "pause")
        ib.add_edge("pause", END)

        with SqliteSaver.from_conn_string(str(interrupt_db)) as cp:
            igraph = ib.compile(checkpointer=cp)
            interrupted = igraph.invoke({"value": 7}, iconfig)
            ints = interrupted.get("__interrupt__", ()) if isinstance(interrupted, dict) else ()
            if not ints:
                raise RuntimeError(f"Interrupt was not surfaced: {interrupted!r}")
        with SqliteSaver.from_conn_string(str(interrupt_db)) as cp:
            igraph2 = ib.compile(checkpointer=cp)
            resumed = igraph2.invoke(Command(resume="synthetic-review-complete"), iconfig)
        interrupt_ok = resumed.get("review") == "synthetic-review-complete"
        write_json(evidence / "interrupt-api-probe.json", {
            "status": "pass" if interrupt_ok else "fail",
            "interrupt_symbol": "langgraph.types.interrupt",
            "resume_symbol": "langgraph.types.Command",
            "resume_call": "graph.invoke(Command(resume=<value>), config)",
            "thread_id": interrupt_thread,
            "interrupt_count": len(ints),
            "resume_observed": resumed.get("review"),
        })
        if not interrupt_ok:
            raise RuntimeError(f"Interrupt/resume probe failed: {resumed!r}")
        result["checks"]["interrupt_resume"] = True

        # Strict structured output API surface without a request.
        structured_sig = str(inspect.signature(ChatOpenAI.with_structured_output))
        strict_supported = "strict" in inspect.signature(ChatOpenAI.with_structured_output).parameters
        method_supported = "method" in inspect.signature(ChatOpenAI.with_structured_output).parameters
        write_json(evidence / "structured-output-api.json", {
            "status": "pass" if strict_supported else "fail",
            "method": "ChatOpenAI.with_structured_output",
            "signature": structured_sig,
            "strict_parameter_supported": strict_supported,
            "method_parameter_supported": method_supported,
            "model_call_performed": False,
        })
        if not strict_supported:
            raise RuntimeError("Pinned ChatOpenAI.with_structured_output lacks strict parameter")
        result["checks"]["strict_structured_output_api"] = True

        # Image message shape only; no image bytes/data URL retained.
        msg = HumanMessage(content=[
            {"type": "text", "text": "probe"},
            {"type": "image_url", "image_url": {"url": "https://example.invalid/probe.png"}},
        ])
        image_ok = isinstance(msg.content, list) and msg.content[1].get("type") == "image_url"
        if not image_ok:
            raise RuntimeError("Pinned HumanMessage image_url content block construction failed")
        result["checks"]["image_message_shape"] = True

        # Retry policy: inspect default and prove explicit zero can be represented locally.
        fields = getattr(ChatOpenAI, "model_fields", {})
        retry_field = fields.get("max_retries")
        retry_default = getattr(retry_field, "default", None) if retry_field else None
        explicit_zero_supported = retry_field is not None
        if explicit_zero_supported:
            # Construction only; no request. Dummy token is never written to evidence.
            llm = ChatOpenAI(
                model="gpt-4.1-mini-2025-04-14",
                temperature=0.0,
                max_retries=0,
                api_key="probe-not-used",
            )
            explicit_zero_supported = getattr(llm, "max_retries", None) == 0
        write_json(evidence / "retry-policy.json", {
            "status": "pass" if explicit_zero_supported else "fail",
            "field": "max_retries",
            "observed_default_repr": repr(retry_default),
            "explicit_zero_supported": explicit_zero_supported,
            "experiment_setting": 0 if explicit_zero_supported else None,
            "model_call_performed": False,
        })
        if not explicit_zero_supported:
            raise RuntimeError("Pinned ChatOpenAI does not support explicit max_retries=0")
        result["checks"]["explicit_zero_transport_retries"] = True

        @tool
        def synthetic_shared_operation(value: int) -> int:
            """Return a deterministic synthetic value without Drupal access."""
            return value + 1

        tool_ok = synthetic_shared_operation.invoke({"value": 4}) == 5
        if not tool_ok:
            raise RuntimeError("LangChain @tool deterministic invocation failed")
        result["checks"]["native_tool_wrapper"] = True

        # Persistent-state privacy design check (synthetic state keys only).
        persisted_keys = set(snap2.values.keys())
        unsafe = sorted(k for k in persisted_keys if k.lower() in PROHIBITED_KEYS)
        if unsafe:
            raise RuntimeError(f"Unsafe synthetic persisted keys: {unsafe}")
        result["checks"]["persisted_state_privacy"] = True

        architecture = {
            "schema_version": 1,
            "status": "selected",
            "graph": "langgraph.graph.StateGraph",
            "routing": "deterministic graph nodes control workflow/write decisions",
            "tool_wrappers": "langchain_core.tools.tool thin wrappers; deterministic nodes invoke them",
            "checkpointer": "langgraph.checkpoint.sqlite.SqliteSaver",
            "runtime_root": "langchain/.gate2a-runtime/",
            "per_run_checkpoint_path": "langchain/.gate2a-runtime/<run-id>.sqlite",
            "thread_identity": "Gate 2A run_id used as configurable.thread_id",
            "checkpoint_namespace": checkpoint_probe["checkpoint_namespace"],
            "interrupt": "langgraph.types.interrupt",
            "resume": "graph.invoke(langgraph.types.Command(resume=<value>), same thread config)",
            "structured_output": "ChatOpenAI.with_structured_output(..., strict=True)",
            "image_message": "HumanMessage content block type=image_url; image bytes remain ephemeral",
            "transport_retries": "ChatOpenAI(max_retries=0) for experiment model path",
            "shared_runtime_storage": False,
            "raw_image_bytes_in_checkpoint": False,
            "credentials_in_checkpoint": False,
            "model_call_performed": False,
            "drupal_state_mutated": False,
        }
        write_json(evidence / "architecture-decision.json", architecture)

        result["status"] = "pass"
    except Exception as exc:
        result["errors"].append({
            "type": type(exc).__name__,
            "message": str(exc),
        })
        # Keep traceback sanitized to local code/module paths; no env dump or secrets.
        (evidence / "probe-error.txt").write_text(
            "".join(traceback.format_exception_only(type(exc), exc)),
            encoding="utf-8",
        )
    finally:
        write_json(evidence / "summary.json", result)
        lines = [
            "# Gate 2A Step 2A.02 Runtime Probe",
            "",
            f"- **Status:** {result['status'].upper()}",
            f"- **Run ID:** `{args.run_id}`",
            "- **Model calls:** 0",
            "- **Drupal mutation:** 0",
            "- **Dependency changes:** 0",
            f"- **Checks passed:** {sum(1 for v in result['checks'].values() if v)}",
        ]
        if result["errors"]:
            lines += ["", "## Stop reason", "", f"`{result['errors'][0]['type']}: {result['errors'][0]['message']}`"]
        else:
            lines += [
                "",
                "The pinned runtime supports the selected model-free LangGraph architecture. "
                "This does not prove live model behavior, Drupal tool behavior, or Gate 2C recovery.",
            ]
        (evidence / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if result["status"] == "pass" else 2

if __name__ == "__main__":
    raise SystemExit(main())
