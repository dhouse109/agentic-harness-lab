#!/usr/bin/env python3
"""Isolated one-process phases for the Gate 2B Step 2B.02 model-free probe."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
import socket
import sys
import traceback
from typing import Any

os.environ.update({
    "CREWAI_DISABLE_TELEMETRY": "true",
    "CREWAI_DISABLE_TRACKING": "true",
    "CREWAI_TRACING_ENABLED": "false",
    "OTEL_SDK_DISABLED": "true",
})

MODEL_CALLS = 0
PROVIDER_NETWORK_ATTEMPTS = 0
BLOCKED_NETWORK_EVENTS: list[dict[str, Any]] = []
CURRENT_PHASE = "unassigned"


def marker(value: str) -> None:
    print(f"GATE2B_PHASE_MARKER={value}", file=sys.stderr, flush=True)


PROFILE_MARKERS: set[str] = set()


def lifecycle_profile(frame: Any, event: str, arg: Any) -> None:
    del arg
    if event != "call":
        return
    filename = frame.f_code.co_filename.replace("\\", "/")
    name = frame.f_code.co_name
    value = None
    if filename.endswith("/crewai/memory/unified_memory.py") and name == "model_post_init":
        value = "unified_memory_initialization_entered"
    elif "/crewai/memory/storage/lancedb_storage.py" in filename:
        value = "lancedb_initialization_entered"
    if value and value not in PROFILE_MARKERS:
        PROFILE_MARKERS.add(value)
        marker(value)


marker("worker_started")

from pydantic import BaseModel, Field  # noqa: E402
from crewai.flow import Flow, human_feedback, listen, start  # noqa: E402
from crewai.flow.async_feedback import HumanFeedbackPending  # noqa: E402
from crewai.flow.persistence import SQLiteFlowPersistence, persist  # noqa: E402
from crewai.llm import LLM  # noqa: E402
from crewai.llms.base_llm import BaseLLM  # noqa: E402
from crewai.memory.storage.backend import StorageBackend  # noqa: E402
from crewai.memory.storage.factory import set_memory_storage_factory  # noqa: E402
from crewai.state import CheckpointConfig  # noqa: E402
from crewai.state.provider.json_provider import JsonProvider  # noqa: E402
from crewai.state.provider.sqlite_provider import SqliteProvider  # noqa: E402

marker("crewai_import_completed")


def _blocked_call(*args: Any, **kwargs: Any) -> Any:
    del args, kwargs
    global MODEL_CALLS
    MODEL_CALLS += 1
    raise RuntimeError("Gate 2B Step 2B.02 model-call guard fired")


BaseLLM.call = _blocked_call  # type: ignore[method-assign]
LLM.call = _blocked_call  # type: ignore[method-assign]


def _safe_destination(address: Any) -> dict[str, Any]:
    if isinstance(address, tuple) and len(address) >= 2:
        raw_host, raw_port = str(address[0]), address[1]
        host = raw_host.lower()
        if host in {"localhost", "127.0.0.1", "::1"}:
            safe_host = host
        elif re.fullmatch(r"[a-z0-9.-]+", host) and not any(token in host for token in ("@", "/", "?", "#")):
            safe_host = host
        else:
            safe_host = "[redacted-host]"
        return {"host": safe_host, "port": raw_port if isinstance(raw_port, int) else "[redacted-port]"}
    return {"host": "[non-inet-or-redacted]", "port": None}


def _safe_frame(frame: traceback.FrameSummary) -> dict[str, Any]:
    value = frame.filename.replace("\\", "/")
    if "/site-packages/" in value:
        path = value.split("/site-packages/", 1)[1]
    elif "/crewai/runtime_probe/" in value:
        path = "crewai/runtime_probe/" + value.split("/crewai/runtime_probe/", 1)[1]
    else:
        path = "[stdlib-or-runner]/" + Path(value).name
    return {"source": path, "function": frame.name, "line": frame.lineno}


def _record_blocked_network(operation: str, address: Any) -> None:
    global PROVIDER_NETWORK_ATTEMPTS
    PROVIDER_NETWORK_ATTEMPTS += 1
    frames = [_safe_frame(frame) for frame in traceback.extract_stack(limit=24)[:-2]]
    BLOCKED_NETWORK_EVENTS.append({
        "order": PROVIDER_NETWORK_ATTEMPTS,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "phase": CURRENT_PHASE,
        "pid": os.getpid(),
        "process_group_id": os.getpgid(0),
        "operation": operation,
        "destination": _safe_destination(address),
        "frames": frames,
        "blocked_before_connect": True,
    })


def _blocked_connect(self: Any, address: Any) -> Any:
    del self
    _record_blocked_network("socket.connect", address)
    raise RuntimeError("Gate 2B Step 2B.02 provider-network guard fired")


def _blocked_connect_ex(self: Any, address: Any) -> Any:
    del self
    _record_blocked_network("socket.connect_ex", address)
    raise RuntimeError("Gate 2B Step 2B.02 provider-network guard fired")


socket.socket.connect = _blocked_connect  # type: ignore[method-assign]
socket.socket.connect_ex = _blocked_connect_ex  # type: ignore[method-assign]


class ProbeState(BaseModel):
    id: str = "unset"
    payload: str = "unset"
    counter: int = 0
    trace: list[str] = Field(default_factory=list)
    review_status: str = "not_requested"


class ProbeMemoryStorage(StorageBackend):
    """Probe-owned deterministic backend installed through CrewAI's public factory."""

    def __init__(self) -> None:
        self.items: dict[str, Any] = {}

    def save(self, records: list[Any]) -> None:
        for record in records:
            self.items[str(record.id)] = record

    def search(self, query_embedding: list[float], scope_prefix: str | None = None, categories: list[str] | None = None, metadata_filter: dict[str, Any] | None = None, limit: int = 10, min_score: float = 0.0) -> list[Any]:
        del query_embedding, scope_prefix, categories, metadata_filter, limit, min_score
        return []

    def delete(self, scope_prefix: str | None = None, categories: list[str] | None = None, record_ids: list[str] | None = None, older_than: Any = None, metadata_filter: dict[str, Any] | None = None) -> int:
        del scope_prefix, categories, older_than, metadata_filter
        ids = record_ids or list(self.items)
        before = len(self.items)
        for key in ids:
            self.items.pop(key, None)
        return before - len(self.items)

    def update(self, record: Any) -> None:
        self.items[str(record.id)] = record

    def get_record(self, record_id: str) -> Any:
        return self.items.get(record_id)

    def list_records(self, scope_prefix: str | None = None, limit: int = 200, offset: int = 0) -> list[Any]:
        del scope_prefix
        return list(self.items.values())[offset : offset + limit]

    def get_scope_info(self, scope: str) -> Any:
        from crewai.memory.types import ScopeInfo
        return ScopeInfo(scope=scope, record_count=len(self.items), categories={}, date_range=None, child_scopes=[])

    def list_scopes(self, parent: str = "/") -> list[str]:
        del parent
        return []

    def list_categories(self, scope_prefix: str | None = None) -> dict[str, int]:
        del scope_prefix
        return {}

    def count(self, scope_prefix: str | None = None) -> int:
        del scope_prefix
        return len(self.items)

    def reset(self, scope_prefix: str | None = None) -> None:
        del scope_prefix
        self.items.clear()

    async def asave(self, records: list[Any]) -> None:
        self.save(records)

    async def asearch(self, query_embedding: list[float], scope_prefix: str | None = None, categories: list[str] | None = None, metadata_filter: dict[str, Any] | None = None, limit: int = 10, min_score: float = 0.0) -> list[Any]:
        return self.search(query_embedding, scope_prefix, categories, metadata_filter, limit, min_score)

    async def adelete(self, scope_prefix: str | None = None, categories: list[str] | None = None, record_ids: list[str] | None = None, older_than: Any = None, metadata_filter: dict[str, Any] | None = None) -> int:
        return self.delete(scope_prefix, categories, record_ids, older_than, metadata_filter)


class PendingProvider:
    def request_feedback(self, context: Any, flow: Any) -> str:
        del flow
        raise HumanFeedbackPending(
            context=context,
            callback_info={"kind": "deterministic_external_review_stand_in"},
        )


def _classification(kind: str) -> dict[str, Any]:
    if kind == "default":
        return {
            "execution_classification": "default-unmodified",
            "private_override": None,
            "public_extension": None,
            "normal_behavior_bypassed": [],
            "observation_instrumentation": "sys.setprofile lifecycle markers; no configuration or behavior bypass",
            "architecture_evidence": "default pinned lifecycle observation",
        }
    if kind == "public-extension":
        return {
            "execution_classification": "supported-public-extension",
            "private_override": None,
            "public_extension": "crewai.memory.storage.factory.set_memory_storage_factory",
            "normal_behavior_bypassed": ["default LanceDB storage backend"],
            "observation_instrumentation": "sys.setprofile lifecycle markers; no private behavior bypass",
            "architecture_evidence": "supported public extension candidate",
        }
    return {
        "execution_classification": "probe-isolated",
        "private_override": "_skip_auto_memory = True",
        "public_extension": None,
        "normal_behavior_bypassed": ["automatic Flow unified-memory construction"],
        "diagnostic_question": "isolate Flow persistence mechanics from automatic memory startup",
        "architecture_evidence": "diagnostic only; cannot independently establish supported viability",
    }


def _configure_memory(kind: str) -> None:
    if kind == "public-extension":
        backend = ProbeMemoryStorage()
        set_memory_storage_factory(lambda spec: backend)
        marker("public_memory_storage_factory_registered")


def _flow_class(backend: SQLiteFlowPersistence, kind: str) -> type[Flow[ProbeState]]:
    class PersistenceProbeFlow(Flow[ProbeState]):
        @start()
        @persist(backend)
        def first(self) -> dict[str, Any]:
            self.state.counter += 1
            self.state.trace.append(f"{self.state.id}:first")
            return self.state.model_dump()

        @listen(first)
        @persist(backend)
        def second(self, previous: Any) -> dict[str, Any]:
            del previous
            self.state.counter += 1
            self.state.trace.append(f"{self.state.id}:second")
            return self.state.model_dump()

    if kind == "probe-isolated":
        PersistenceProbeFlow._skip_auto_memory = True  # type: ignore[attr-defined]
    return PersistenceProbeFlow


def _checkpoint_flow_class() -> type[Flow[ProbeState]]:
    class CheckpointProbeFlow(Flow[ProbeState]):
        _skip_auto_memory = True

        @start()
        def first(self) -> dict[str, Any]:
            self.state.counter += 1
            self.state.trace.append(f"{self.state.id}:first")
            return self.state.model_dump()

        @listen(first)
        def second(self, previous: Any) -> dict[str, Any]:
            del previous
            self.state.counter += 1
            self.state.trace.append(f"{self.state.id}:second")
            return self.state.model_dump()

    return CheckpointProbeFlow


def _feedback_flow_class(backend: SQLiteFlowPersistence, kind: str) -> type[Flow[ProbeState]]:
    provider = PendingProvider()

    class FeedbackProbeFlow(Flow[ProbeState]):

        @start()
        @human_feedback(
            message="Observe external authoritative review status",
            emit=None,
            llm=None,
            provider=provider,
        )
        def await_review(self) -> dict[str, str]:
            self.state.counter += 1
            self.state.trace.append("await_review")
            self.state.review_status = "pending_external_authority"
            return {"status": self.state.review_status}

        @listen(await_review)
        @persist(backend)
        def observe_review(self, feedback: Any) -> dict[str, Any]:
            self.state.counter += 1
            self.state.trace.append("observe_review")
            self.state.review_status = getattr(feedback, "feedback", str(feedback))
            return self.state.model_dump()

    if kind == "probe-isolated":
        FeedbackProbeFlow._skip_auto_memory = True  # type: ignore[attr-defined]
    return FeedbackProbeFlow


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = args.storage_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    flow_db = root / "flow-persistence.sqlite3"
    backend = SQLiteFlowPersistence(str(flow_db))
    logical_id = args.logical_run_id
    result: dict[str, Any] = {
        "mode": args.mode,
        "pid": os.getpid(),
        "pgid": os.getpgid(0),
        "logical_run_id": logical_id,
        "storage_root": str(root),
    }

    if args.mode in {"flow-default", "flow-public-extension", "flow-persist-write", "flow-persist-restore"}:
        kind = {
            "flow-default": "default",
            "flow-public-extension": "public-extension",
            "flow-persist-write": "probe-isolated",
            "flow-persist-restore": "probe-isolated",
        }[args.mode]
        result.update(_classification(kind))
        _configure_memory(kind)
        marker("flow_class_definition_started")
        flow_type = _flow_class(backend, kind)
        marker("flow_class_definition_completed")
        if kind in {"default", "public-extension"}:
            sys.setprofile(lifecycle_profile)
        marker("flow_construction_started")
        try:
            flow = flow_type(persistence=backend, tracing=False, suppress_flow_events=True)
            marker("flow_construction_completed")
            inputs = {"id": logical_id, "payload": args.payload or logical_id}
            marker("flow_kickoff_started")
            if args.mode == "flow-persist-restore":
                output = flow.kickoff(inputs=inputs, restore_from_state_id=args.source_identity)
            else:
                output = flow.kickoff(inputs=inputs)
            marker("flow_kickoff_completed")
        finally:
            sys.setprofile(None)
        result.update(output=output, state=flow.state.model_dump())
    elif args.mode == "flow-load-state":
        result["loaded"] = backend.load_state(args.source_identity)
        result["requested_identity"] = args.source_identity
        result["caller_identity"] = logical_id
    elif args.mode in {"checkpoint-json-write", "checkpoint-sqlite-write"}:
        result.update(_classification("probe-isolated"))
        if args.mode == "checkpoint-json-write":
            location = root / "runtime-checkpoints-json"
            provider: JsonProvider | SqliteProvider = JsonProvider()
        else:
            location = root / "runtime-checkpoints.sqlite3"
            provider = SqliteProvider()
        config = CheckpointConfig(location=str(location), on_events=["method_execution_finished"], provider=provider)
        flow_type = _checkpoint_flow_class()
        flow = flow_type(checkpoint=config, tracing=False, suppress_flow_events=False)
        output = flow.kickoff(inputs={"id": logical_id, "payload": args.payload or logical_id})
        if isinstance(provider, JsonProvider):
            locations = [str(path) for path in sorted(location.rglob("*.json"))]
        else:
            with sqlite3.connect(location) as conn:
                ids = [row[0] for row in conn.execute("SELECT id FROM checkpoints ORDER BY rowid")]
            locations = [f"{location}#{item}" for item in ids]
        result.update(output=output, state=flow.state.model_dump(), checkpoints=locations)
    elif args.mode == "checkpoint-restore":
        result.update(_classification("probe-isolated"))
        flow = _checkpoint_flow_class()(tracing=False, suppress_flow_events=False)
        output = flow.kickoff(from_checkpoint=CheckpointConfig(restore_from=args.checkpoint_location))
        result.update(output=output, state=flow.state.model_dump())
    elif args.mode in {"feedback-pause", "feedback-pause-public"}:
        kind = "public-extension" if args.mode.endswith("public") else "probe-isolated"
        result.update(_classification(kind))
        _configure_memory(kind)
        flow = _feedback_flow_class(backend, kind)(persistence=backend, tracing=False, suppress_flow_events=True)
        output = flow.kickoff(inputs={"id": logical_id})
        result.update(pending=isinstance(output, HumanFeedbackPending), state=flow.state.model_dump(), callback_info=getattr(output, "callback_info", None))
    elif args.mode in {"feedback-resume", "feedback-resume-public"}:
        kind = "public-extension" if args.mode.endswith("public") else "probe-isolated"
        result.update(_classification(kind))
        _configure_memory(kind)
        flow = _feedback_flow_class(backend, kind).from_pending(logical_id, backend, tracing=False, suppress_flow_events=True)
        output = flow.resume("approved_in_drupal_stand_in")
        result.update(output=output, state=flow.state.model_dump())
    elif args.mode == "method-failure":
        result.update(_classification("probe-isolated"))
        class FailureFlow(Flow[ProbeState]):
            _skip_auto_memory = True

            @start()
            @persist(backend)
            def fail(self) -> None:
                self.state.trace.append("before_failure")
                raise RuntimeError("deterministic-probe-failure")

        try:
            FailureFlow(persistence=backend, tracing=False, suppress_flow_events=True).kickoff(inputs={"id": logical_id})
        except Exception as exc:
            result.update(exception_type=type(exc).__name__, exception=str(exc))
        result["loaded_after_failure"] = backend.load_state(logical_id)
    elif args.mode.startswith("provider-"):
        provider = JsonProvider() if "json" in args.mode else SqliteProvider()
        if args.mode.endswith("write"):
            location = root / ("provider-json" if "json" in args.mode else "provider.sqlite3")
            result["checkpoint_location"] = provider.checkpoint(json.dumps({"logical_run_id": logical_id, "trace": ["provider"]}), str(location), branch=logical_id)
        elif args.mode.endswith("read") and args.mode != "provider-invalid-read":
            result["payload"] = json.loads(provider.from_checkpoint(args.checkpoint_location))
        else:
            try:
                provider.from_checkpoint(str(root / "provider.sqlite3") + "#missing")
            except Exception as exc:
                result.update(exception_type=type(exc).__name__, exception=str(exc))
    else:
        raise ValueError(f"Unknown mode: {args.mode}")

    result["model_calls"] = MODEL_CALLS
    result["provider_calls"] = 0
    result["blocked_provider_network_attempts"] = PROVIDER_NETWORK_ATTEMPTS
    result["blocked_network_events"] = BLOCKED_NETWORK_EVENTS
    result["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--logical-run-id", required=True)
    parser.add_argument("--source-identity", default="")
    parser.add_argument("--checkpoint-location", default="")
    parser.add_argument("--payload", default="")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    global CURRENT_PHASE
    CURRENT_PHASE = args.mode
    try:
        value = run(args)
    except BaseException as exc:
        marker(f"worker_exception:{type(exc).__name__}")
        raise
    args.output.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
