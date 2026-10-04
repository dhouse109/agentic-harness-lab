#!/usr/bin/env python3
"""One-shot public LanceDB in-memory async differential diagnostic worker.

This module deliberately has no CrewAI import and never calls synchronous
``lancedb.connect``.  The external orchestrator owns the exact 30-second hard
limit; this worker owns only validation, the single public async call, and
fixed-schema phase/result records.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import importlib
import inspect
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable


MEMORY_URI = "memory://"
PHASES = frozenset({
    "worker_process_initialized",
    "memory_backend_validated",
    "lancedb_import_started",
    "lancedb_import_completed",
    "public_connect_async_validated",
    "caller_owned_event_loop_started",
    "in_memory_async_connect_entered",
    "in_memory_async_connect_returned",
    "in_memory_async_connect_exception",
    "diagnostic_completed",
    "setup_failed",
})
MAX_RECORD_BYTES = 1024
REQUIRED_CONNECT_ASYNC_PARAMETERS = (
    "uri",
    "api_key",
    "region",
    "host_override",
    "read_consistency_interval",
    "client_config",
    "storage_options",
    "session",
)
REQUIRED_CONNECT_ASYNC_DEFAULTS = (
    inspect.Parameter.empty,
    None,
    "us-east-1",
    None,
    None,
    None,
    None,
    None,
)
PROHIBITED_CREDENTIAL_ENV = (
    "OPENAI_API_KEY",
    "LANCEDB_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "AZURE_STORAGE_ACCOUNT_KEY",
    "AZURE_STORAGE_SAS_TOKEN",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def safe_exception_class(exc: BaseException) -> str:
    value = type(exc).__name__
    return value if value.isidentifier() and len(value) <= 80 else "Exception"


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class PhaseReporter:
    """Append fixed-schema phase identifiers without payload or environment data."""

    def __init__(self, path: Path, *, trial_id: str, run_id: str) -> None:
        self.path = path.resolve()
        self.trial_id = trial_id
        self.run_id = run_id
        self.sequence = 0
        require("/.cache/gate2c-step02/" in self.path.as_posix(), "phase log must be run-scoped")
        require(self.path.name == "memory-async-connect-phases.jsonl", "unexpected phase log name")
        require(not self.path.exists(), "phase log must be fresh")
        require(self.path.parent.is_dir() and not self.path.parent.is_symlink(), "phase log parent")

    def record(self, phase: str, *, exception_class: str | None = None) -> None:
        require(phase in PHASES, "unapproved in-memory diagnostic phase")
        require(
            exception_class is None
            or (exception_class.isidentifier() and len(exception_class) <= 80),
            "unsafe exception class",
        )
        self.sequence += 1
        value: dict[str, Any] = {
            "schema_version": 1,
            "sequence": self.sequence,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "monotonic_ns": time.monotonic_ns(),
            "diagnostic": "lancedb_public_memory_async_connection",
            "trial_id": self.trial_id,
            "run_id": self.run_id,
            "phase": phase,
        }
        if exception_class is not None:
            value["exception_class"] = exception_class
        payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        require(len(payload) <= MAX_RECORD_BYTES, "in-memory diagnostic phase record too large")
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(self.path, flags, 0o600)
        try:
            os.write(fd, payload)
            os.fsync(fd)
        finally:
            os.close(fd)


def validate_public_connect_async(module: Any) -> Callable[..., Any]:
    connect_async = getattr(module, "connect_async", None)
    require(connect_async is not None, "public lancedb.connect_async is missing")
    require(inspect.iscoroutinefunction(connect_async), "public lancedb.connect_async is not async")
    signature = inspect.signature(connect_async)
    require(tuple(signature.parameters) == REQUIRED_CONNECT_ASYNC_PARAMETERS, "public connect_async signature drift")
    parameters = tuple(signature.parameters.values())
    require(parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD, "public connect_async uri kind drift")
    require(all(item.kind is inspect.Parameter.KEYWORD_ONLY for item in parameters[1:]), "public connect_async keyword-only drift")
    require(tuple(item.default for item in parameters) == REQUIRED_CONNECT_ASYNC_DEFAULTS, "public connect_async default drift")
    return connect_async


def validate_control(control: Path) -> None:
    control = control.resolve()
    require("/.cache/gate2c-step02/" in control.as_posix(), "control directory must be run-scoped")
    require(control.name == "lancedb-memory-async", "unexpected in-memory control directory")
    require(control.is_dir() and not control.is_symlink() and os.access(control, os.W_OK), "control directory invalid")
    require(
        {path.name for path in control.iterdir()} <= {"worker-command.json"},
        "in-memory control directory must be fresh",
    )


async def invoke_once(connect_async: Callable[..., Any], reporter: PhaseReporter) -> str:
    reporter.record("caller_owned_event_loop_started")
    reporter.record("in_memory_async_connect_entered")
    try:
        connection = await connect_async(MEMORY_URI)
    except Exception as exc:
        exception_class = safe_exception_class(exc)
        reporter.record("in_memory_async_connect_exception", exception_class=exception_class)
        return exception_class
    reporter.record("in_memory_async_connect_returned")
    close = getattr(connection, "close", None)
    if callable(close):
        close()
    return ""


def execute(
    args: argparse.Namespace,
    *,
    module_loader: Callable[[str], Any] = importlib.import_module,
    runner: Callable[[Any], Any] = asyncio.run,
) -> int:
    control = args.control_dir.resolve()
    validate_control(control)
    reporter = PhaseReporter(args.phase_log, trial_id=args.trial_id, run_id=args.run_id)
    reporter.record("worker_process_initialized")
    try:
        require(not any(os.environ.get(name) for name in PROHIBITED_CREDENTIAL_ENV), "provider/API credentials must be unset")
        require(not any(name == "crewai" or name.startswith("crewai.") for name in sys.modules), "CrewAI must not be imported")
        reporter.record("memory_backend_validated")
        reporter.record("lancedb_import_started")
        lancedb = module_loader("lancedb")
        reporter.record("lancedb_import_completed")
        require(not any(name == "crewai" or name.startswith("crewai.") for name in sys.modules), "LanceDB import loaded CrewAI")
        connect_async = validate_public_connect_async(lancedb)
        reporter.record("public_connect_async_validated")
        exception_class = runner(invoke_once(connect_async, reporter))
        status = "IN_MEMORY_ASYNC_CONNECT_EXCEPTION" if exception_class else "IN_MEMORY_ASYNC_CONNECT_RETURNED"
        reporter.record("diagnostic_completed")
        write_json(args.output, {
            "schema_version": 1,
            "status": status,
            "diagnostic_scope": "ONE_PUBLIC_LANCEDB_MEMORY_CONNECT_ASYNC_CALL",
            "trial_id": args.trial_id,
            "run_id": args.run_id,
            "model_free": True,
            "local_only": True,
            "in_memory": True,
            "storage_uri_scheme": "memory",
            "filesystem_storage_created": False,
            "caller_owned_event_loop": True,
            "public_connect_async_calls": 1,
            "synchronous_connect_calls": 0,
            "crewai_imported": False,
            "flow_constructed": False,
            "flow_invoked": False,
            "provider_requests": 0,
            "drupal_operations": 0,
            "experimental_sigkill_delivered": False,
            "exception_class": exception_class or None,
        })
        return 0
    except Exception as exc:
        reporter.record("setup_failed", exception_class=safe_exception_class(exc))
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--control-dir", required=True, type=Path)
    parser.add_argument("--phase-log", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    try:
        return execute(parser.parse_args())
    except BaseException as exc:
        print(safe_exception_class(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
