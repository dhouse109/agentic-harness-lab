#!/usr/bin/env python3
"""Fresh-process categorical preflight for corrected-environment Gate 2C work.

This module deliberately imports no project package and no CrewAI module.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import socket
import threading
from pathlib import Path
from typing import Any


EXPECTED_PYTHON = "3.12.13"
EXPECTED_POLICY = "_UnixDefaultEventLoopPolicy"
EXPECTED_SELECTOR = "EpollSelector"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        require(os.write(fd, payload) == len(payload), "partial preflight result write")
        os.fsync(fd)
    finally:
        os.close(fd)


def safe_process_controls(status_path: Path = Path("/proc/self/status")) -> dict[str, int]:
    selected: dict[str, int] = {}
    for line in status_path.read_text(encoding="ascii").splitlines():
        name, separator, value = line.partition(":")
        if separator and name in {"NoNewPrivs", "Seccomp"}:
            selected[name] = int(value.strip())
    require(set(selected) == {"NoNewPrivs", "Seccomp"}, "required process controls unavailable")
    return selected


async def cross_thread_wakeup() -> dict[str, Any]:
    loop = asyncio.get_running_loop()
    event = asyncio.Event()
    counts = {
        "auxiliary_python_threads_constructed": 0,
        "auxiliary_thread_start_calls": 0,
        "auxiliary_worker_function_started": 0,
        "auxiliary_worker_function_completed": 0,
        "call_soon_threadsafe_calls": 0,
        "callback_calls": 0,
    }

    def callback() -> None:
        counts["callback_calls"] += 1
        event.set()

    def auxiliary() -> None:
        counts["auxiliary_worker_function_started"] += 1
        try:
            counts["call_soon_threadsafe_calls"] += 1
            loop.call_soon_threadsafe(callback)
        finally:
            counts["auxiliary_worker_function_completed"] += 1

    baseline = threading.active_count()
    thread = threading.Thread(target=auxiliary, name="gate2c-corrected-environment-preflight", daemon=False)
    counts["auxiliary_python_threads_constructed"] += 1
    counts["auxiliary_thread_start_calls"] += 1
    thread.start()
    sampled = threading.active_count()
    resumed = False
    try:
        await asyncio.wait_for(event.wait(), timeout=5.0)
        resumed = True
    finally:
        thread.join(timeout=5.0)
    return {
        **counts,
        "baseline_python_threads": baseline,
        "sampled_python_threads_after_start": sampled,
        "sampled_python_threads_after_start_is_informational": True,
        "auxiliary_thread_alive_after_join": thread.is_alive(),
        "callback_executed": counts["callback_calls"] == 1,
        "event_await_resumed": resumed,
        "wait_bound_seconds": 5.0,
        "event_loop_policy": type(asyncio.get_event_loop_policy()).__name__,
        "selector": type(loop._selector).__name__,
    }


def socketpair_control() -> dict[str, Any]:
    left, right = socket.socketpair()
    try:
        sent = left.send(b"\x00")
        received = right.recv(1)
    finally:
        left.close()
        right.close()
    return {
        "socketpair_bytes_sent": sent,
        "socketpair_bytes_received": len(received),
        "socketpair_one_null_byte_round_trip": sent == 1 and received == b"\x00",
    }


def evaluate(value: dict[str, Any]) -> list[str]:
    required = {
        "python_version": EXPECTED_PYTHON,
        "no_new_privs": 0,
        "seccomp": 0,
        "event_loop_policy": EXPECTED_POLICY,
        "selector": EXPECTED_SELECTOR,
        "baseline_python_threads": 1,
        "auxiliary_python_threads_constructed": 1,
        "auxiliary_thread_start_calls": 1,
        "auxiliary_worker_function_started": 1,
        "auxiliary_worker_function_completed": 1,
        "auxiliary_thread_alive_after_join": False,
        "call_soon_threadsafe_calls": 1,
        "callback_calls": 1,
        "callback_executed": True,
        "event_await_resumed": True,
        "socketpair_bytes_sent": 1,
        "socketpair_bytes_received": 1,
        "socketpair_one_null_byte_round_trip": True,
    }
    return [name for name, expected in required.items() if value.get(name) != expected]


def collect() -> dict[str, Any]:
    controls = safe_process_controls()
    value: dict[str, Any] = {
        "schema_version": 1,
        "python_version": platform.python_version(),
        "no_new_privs": controls["NoNewPrivs"],
        "seccomp": controls["Seccomp"],
        **asyncio.run(cross_thread_wakeup()),
        **socketpair_control(),
        "environment_values_retained": False,
        "full_proc_status_retained": False,
        "credentials_retained": False,
        "file_descriptors_retained": False,
        "object_ids_retained": False,
        "private_state_retained": False,
        "crewai_imported": False,
    }
    failures = evaluate(value)
    value["status"] = "CORRECTED_EXECUTION_ENVIRONMENT_PREFLIGHT_PASS" if not failures else "INVALID_EXECUTION_ENVIRONMENT_PREFLIGHT"
    value["failed_checks"] = failures
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True, type=Path)
    args = parser.parse_args()
    try:
        value = collect()
    except BaseException as exc:
        value = {
            "schema_version": 1,
            "status": "INVALID_EXECUTION_ENVIRONMENT_PREFLIGHT",
            "error_type": type(exc).__name__,
            "environment_values_retained": False,
            "full_proc_status_retained": False,
            "crewai_imported": False,
        }
    write_json_exclusive(args.result, value)
    return 0 if value["status"] == "CORRECTED_EXECUTION_ENVIRONMENT_PREFLIGHT_PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
