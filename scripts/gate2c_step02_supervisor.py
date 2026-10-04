#!/usr/bin/env python3
"""External Gate 2C supervisor with fail-closed bounded diagnostics."""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import os
import re
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SEAM = "after target 6 is fully persisted and before target 7 begins"
ORIGINS = {"drupal_ai", "langgraph", "crewai"}
DIAGNOSTIC_LIMIT = 4096
PHASE_LOG_LIMIT = 32768
PHASE_COUNT_LIMIT = 32
STACK_LOG_LIMIT = 16384
STACK_RECORD_LIMIT = 2
STACK_DEPTH_LIMIT = 12
STACK_SNAPSHOT_DELAYS_SECONDS = (8.0, 18.0)
STACK_ROLES = ("MAIN_WORKER", "LANCEDB_BACKGROUND_LOOP")
STACK_LOCATION = re.compile(r"^[A-Za-z0-9_.<>-]{1,160}$")
STACK_UNAVAILABLE_REASONS = {
    "BACKGROUND_FRAME_UNAVAILABLE",
    "BACKGROUND_THREAD_UNAVAILABLE",
    "CONNECTION_COMPLETED_BEFORE_SNAPSHOT",
    "CONNECTION_NOT_ENTERED",
    "PYTHON_FRAME_NOT_AVAILABLE",
    "SAMPLING_FAILURE",
    "WORKER_DID_NOT_EMIT_BEFORE_CLEANUP",
}
HOME_PATH = re.compile(r"/home/[^/\s]+")
DIAGNOSTIC_REDACTIONS = (
    re.compile(r"sk-(?:proj|live)-[A-Za-z0-9_-]+", re.I),
    re.compile(r"Authorization:\s*(?:Basic|Bearer)\s+\S+", re.I),
    re.compile(r"data:image/[^;\s]+;base64,[A-Za-z0-9+/=]+", re.I),
    re.compile(r"OPENAI_API_KEY\s*=\s*\S+", re.I),
)
CREWAI_PHASES = frozenset({
    "worker_process_initialized",
    "xdg_storage_validated",
    "crewai_import_started",
    "crewai_import_completed",
    "sqlite_persistence_initialization_started",
    "sqlite_persistence_initialized",
    "flow_construction_started_memory_initialization_pending",
    "lancedb_connection_trace_armed",
    "lancedb_connect_entered",
    "lancedb_connect_returned_memory_initialization_continues",
    "lancedb_connect_exception",
    "flow_construction_and_memory_initialization_completed",
    "flow_invocation_started",
    "flow_method_started",
    "target_6_sqlite_persisted",
    "target_6_midpoint_verified",
    "seam_ready_emitted",
    "startup_diagnostic_completed",
    "worker_failed",
})


class SupervisorTimeout(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON object required: {path.name}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sanitize_diagnostic(value: str) -> tuple[str, bool]:
    sanitized = value.replace("\x00", "")
    sanitized = HOME_PATH.sub("[HOME]", sanitized)
    for pattern in DIAGNOSTIC_REDACTIONS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    truncated = len(sanitized) > DIAGNOSTIC_LIMIT
    if truncated:
        sanitized = sanitized[-DIAGNOSTIC_LIMIT:]
    return sanitized, truncated


class BoundedStderr:
    """Keep only a bounded stderr tail in memory; never persist raw stderr."""

    def __init__(self, limit: int = DIAGNOSTIC_LIMIT * 2) -> None:
        self.limit = limit
        self.parts: deque[bytes] = deque()
        self.size = 0
        self.observed = 0

    def feed(self, value: bytes) -> None:
        if not value:
            return
        self.observed += len(value)
        self.parts.append(value)
        self.size += len(value)
        while self.size > self.limit and self.parts:
            removed = self.parts.popleft()
            self.size -= len(removed)

    def sanitized(self) -> tuple[str, bool]:
        value = b"".join(self.parts).decode("utf-8", errors="replace")
        sanitized, truncated = sanitize_diagnostic(value)
        return sanitized, truncated or self.observed > self.limit


def drain_stderr(process: subprocess.Popen[bytes], captured: BoundedStderr) -> None:
    stream = process.stderr
    if stream is None:
        return
    while True:
        try:
            chunk = os.read(stream.fileno(), 4096)
        except BlockingIOError:
            return
        if not chunk:
            return
        captured.feed(chunk)


def validate_startup_phases(path: Path, *, trial_id: str, run_id: str) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    require(not path.is_symlink() and path.stat().st_size <= PHASE_LOG_LIMIT, "startup phase log bounds")
    records: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        require(index <= PHASE_COUNT_LIMIT, "too many startup phase records")
        value = json.loads(line)
        require(isinstance(value, dict), "startup phase record object")
        require(set(value) <= {"schema_version", "sequence", "recorded_at", "monotonic_ns", "framework_origin", "trial_id", "run_id", "phase", "error_type"}, "startup phase record fields")
        require(value.get("schema_version") == 1 and value.get("sequence") == index, "startup phase sequence")
        require(value.get("framework_origin") == "crewai", "startup phase framework")
        require(value.get("trial_id") == trial_id and value.get("run_id") == run_id, "startup phase identity")
        require(value.get("phase") in CREWAI_PHASES, "startup phase identifier")
        require(isinstance(value.get("recorded_at"), str) and isinstance(value.get("monotonic_ns"), int), "startup phase timestamps")
        error_type = value.get("error_type")
        require(error_type is None or (isinstance(error_type, str) and error_type.isidentifier() and len(error_type) <= 80), "startup phase error type")
        records.append(value)
    return records


def classify_connection_boundary(records: list[dict[str, Any]]) -> str:
    """Classify the last proven construction boundary without inferring a cause."""
    phases = [record["phase"] for record in records]
    armed = phases.count("lancedb_connection_trace_armed")
    entered = phases.count("lancedb_connect_entered")
    returned = phases.count("lancedb_connect_returned_memory_initialization_continues")
    failed = phases.count("lancedb_connect_exception")
    complete = phases.count("flow_construction_and_memory_initialization_completed")
    require(all(value <= 1 for value in (armed, entered, returned, failed, complete)), "duplicate connection boundary phase")
    require(not returned or entered, "LanceDB return without entry")
    require(not failed or entered, "LanceDB exception without entry")
    require(not (returned and failed), "LanceDB return and exception conflict")
    if not armed:
        return "NOT_INSTRUMENTED"
    if complete and not entered:
        return "FLOW_CONSTRUCTION_COMPLETED_WITHOUT_LANCEDB_CONNECT"
    require(not complete or returned, "Flow construction completed without LanceDB return")
    if not entered:
        return "TRACE_ARMED_BEFORE_CONNECT"
    if failed:
        return "LANCEDB_CONNECT_EXCEPTION"
    if not returned:
        return "LANCEDB_CONNECT_ENTERED_NO_RETURN"
    if not complete:
        return "LANCEDB_CONNECT_RETURNED_LATER_FLOW_CONSTRUCTION_INCOMPLETE"
    return "FLOW_CONSTRUCTION_COMPLETED"


def validate_stack_location_records(
    path: Path,
    *,
    trial_id: str,
    run_id: str,
) -> list[dict[str, Any]]:
    """Validate bounded function-location records without accepting raw traces."""
    if not path.is_file():
        return []
    require(not path.is_symlink() and path.stat().st_size <= STACK_LOG_LIMIT, "stack location log bounds")
    records: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        require(index <= STACK_RECORD_LIMIT, "too many stack location records")
        value = json.loads(line)
        require(isinstance(value, dict), "stack location record object")
        common_fields = {
            "schema_version", "snapshot_index", "scheduled_after_entry_seconds",
            "recorded_at", "monotonic_ns", "framework_origin", "trial_id",
            "run_id", "status",
        }
        schema_version = value.get("schema_version")
        require(schema_version in {1, 2}, "stack location schema version")
        allowed_fields = (
            common_fields | {"locations", "unavailable_reason"}
            if schema_version == 1
            else common_fields | {"observations"}
        )
        require(set(value) <= allowed_fields, "stack location record fields")
        require(value.get("snapshot_index") == index, "stack location sequence")
        require(
            value.get("scheduled_after_entry_seconds") == STACK_SNAPSHOT_DELAYS_SECONDS[index - 1],
            "stack location schedule drift",
        )
        require(value.get("framework_origin") == "crewai", "stack location framework")
        require(value.get("trial_id") == trial_id and value.get("run_id") == run_id, "stack location identity")
        require(isinstance(value.get("recorded_at"), str) and isinstance(value.get("monotonic_ns"), int), "stack location timestamps")
        if schema_version == 1:
            status = value.get("status")
            locations = value.get("locations")
            require(status in {"CAPTURED", "SNAPSHOT_UNAVAILABLE"}, "legacy stack location status")
            _validate_stack_locations(locations, "legacy stack location")
            if status == "CAPTURED":
                require(bool(locations) and "unavailable_reason" not in value, "captured legacy stack content")
            else:
                require(not locations and value.get("unavailable_reason") in STACK_UNAVAILABLE_REASONS, "legacy unavailable classification")
        else:
            observations = value.get("observations")
            require(isinstance(observations, list) and len(observations) == 2, "two stack role observations")
            require([item.get("role") for item in observations] == list(STACK_ROLES), "stack observation role order")
            captured = 0
            for observation in observations:
                require(isinstance(observation, dict), "stack role observation object")
                require(set(observation) <= {"role", "status", "locations", "unavailable_reason"}, "stack role observation fields")
                role = observation["role"]
                status = observation.get("status")
                locations = observation.get("locations")
                require(status in {"CAPTURED", "SNAPSHOT_UNAVAILABLE"}, "stack role status")
                _validate_stack_locations(locations, f"{role} stack location")
                if status == "CAPTURED":
                    captured += 1
                    require(bool(locations) and "unavailable_reason" not in observation, "captured role content")
                else:
                    reason = observation.get("unavailable_reason")
                    require(not locations and reason in STACK_UNAVAILABLE_REASONS, "role unavailable classification")
                    if role == "MAIN_WORKER":
                        require(reason not in {"BACKGROUND_THREAD_UNAVAILABLE", "BACKGROUND_FRAME_UNAVAILABLE"}, "main role background classification")
                    elif reason in {"PYTHON_FRAME_NOT_AVAILABLE", "SAMPLING_FAILURE"}:
                        raise RuntimeError("background role requires background-specific unavailable classification")
            expected_status = "CAPTURED" if captured == 2 else ("PARTIAL" if captured else "SNAPSHOT_UNAVAILABLE")
            require(value.get("status") == expected_status, "stack role aggregate status")
        serialized = json.dumps(value, sort_keys=True, separators=(",", ":"))
        require("/home/" not in serialized and "\\\\" not in serialized, "raw path in stack location record")
        records.append(value)
    return records


def _validate_stack_locations(locations: Any, label: str) -> None:
    require(isinstance(locations, list) and len(locations) <= STACK_DEPTH_LIMIT, f"{label} depth")
    for location in locations:
        require(isinstance(location, dict) and set(location) == {"module", "function"}, f"{label} fields")
        require(
            isinstance(location["module"], str)
            and isinstance(location["function"], str)
            and STACK_LOCATION.fullmatch(location["module"]) is not None
            and STACK_LOCATION.fullmatch(location["function"]) is not None,
            f"unsafe {label} label",
        )


def build_stack_location_summary(
    records: list[dict[str, Any]],
    *,
    trial_id: str,
    run_id: str,
    connection_boundary: str,
) -> dict[str, Any]:
    """Finalize two explicit statuses; missing worker records never imply a cause."""
    by_index = {record["snapshot_index"]: record for record in records}
    require(len(by_index) == len(records), "duplicate stack location snapshot")
    legacy = bool(records) and all(record.get("schema_version") == 1 for record in records)
    require(not records or legacy or all(record.get("schema_version") == 2 for record in records), "mixed stack record schemas")
    snapshots: list[dict[str, Any]] = []
    for index, delay in enumerate(STACK_SNAPSHOT_DELAYS_SECONDS, start=1):
        record = by_index.get(index)
        if record is None and legacy:
            reason = (
                "CONNECTION_NOT_ENTERED"
                if connection_boundary in {
                    "NOT_INSTRUMENTED",
                    "TRACE_ARMED_BEFORE_CONNECT",
                    "FLOW_CONSTRUCTION_COMPLETED_WITHOUT_LANCEDB_CONNECT",
                }
                else "WORKER_DID_NOT_EMIT_BEFORE_CLEANUP"
            )
            record = {
                "snapshot_index": index,
                "scheduled_after_entry_seconds": delay,
                "status": "SNAPSHOT_UNAVAILABLE",
                "locations": [],
                "unavailable_reason": reason,
            }
        if legacy:
            snapshots.append({
                key: record[key]
                for key in (
                    "snapshot_index", "scheduled_after_entry_seconds", "status",
                    "locations", "unavailable_reason",
                )
                if key in record
            })
            continue
        if record is None:
            main_reason = (
                "CONNECTION_NOT_ENTERED"
                if connection_boundary in {
                    "NOT_INSTRUMENTED",
                    "TRACE_ARMED_BEFORE_CONNECT",
                    "FLOW_CONSTRUCTION_COMPLETED_WITHOUT_LANCEDB_CONNECT",
                }
                else "WORKER_DID_NOT_EMIT_BEFORE_CLEANUP"
            )
            observations = [
                {"role": "MAIN_WORKER", "status": "SNAPSHOT_UNAVAILABLE", "locations": [], "unavailable_reason": main_reason},
                {"role": "LANCEDB_BACKGROUND_LOOP", "status": "SNAPSHOT_UNAVAILABLE", "locations": [], "unavailable_reason": "BACKGROUND_THREAD_UNAVAILABLE"},
            ]
            status = "SNAPSHOT_UNAVAILABLE"
        else:
            observations = record["observations"]
            status = record["status"]
        snapshots.append({
            "snapshot_index": index,
            "scheduled_after_entry_seconds": delay,
            "status": status,
            "observations": observations,
        })
    if legacy:
        captured = sum(item["status"] == "CAPTURED" for item in snapshots)
        return {
            "schema_version": 1,
            "framework_origin": "crewai",
            "trial_id": trial_id,
            "run_id": run_id,
            "status": "CAPTURED" if captured == 2 else ("PARTIAL" if captured else "SNAPSHOT_UNAVAILABLE"),
            "snapshot_count": 2,
            "captured_count": captured,
            "connection_boundary_classification": connection_boundary,
            "snapshots": snapshots,
            "native_cause_inference": "PROHIBITED",
        }
    captured = sum(
        observation["status"] == "CAPTURED"
        for snapshot in snapshots
        for observation in snapshot["observations"]
    )
    return {
        "schema_version": 2,
        "framework_origin": "crewai",
        "trial_id": trial_id,
        "run_id": run_id,
        "status": "CAPTURED" if captured == 4 else ("PARTIAL" if captured else "SNAPSHOT_UNAVAILABLE"),
        "snapshot_count": 2,
        "role_count": 2,
        "captured_observation_count": captured,
        "connection_boundary_classification": connection_boundary,
        "snapshots": snapshots,
        "native_cause_inference": "PROHIBITED",
    }


def validate_stack_location_summary(
    value: dict[str, Any],
    *,
    trial_id: str,
    run_id: str,
) -> None:
    schema_version = value.get("schema_version")
    require(schema_version in {1, 2}, "stack location summary schema version")
    expected_fields = {
        "schema_version", "framework_origin", "trial_id", "run_id", "status",
        "snapshot_count", "connection_boundary_classification",
        "snapshots", "native_cause_inference",
    }
    expected_fields.add("captured_count" if schema_version == 1 else "captured_observation_count")
    if schema_version == 2:
        expected_fields.add("role_count")
    require(set(value) == expected_fields, "stack location summary fields")
    require(value.get("framework_origin") == "crewai", "stack location summary framework")
    require(value.get("trial_id") == trial_id and value.get("run_id") == run_id, "stack location summary identity")
    require(value.get("status") in {"CAPTURED", "PARTIAL", "SNAPSHOT_UNAVAILABLE"}, "stack location summary status")
    require(value.get("snapshot_count") == 2, "stack location summary count")
    require(value.get("native_cause_inference") == "PROHIBITED", "stack location native inference")
    snapshots = value.get("snapshots")
    require(isinstance(snapshots, list) and len(snapshots) == 2, "stack location summary snapshots")
    captured = 0
    for index, snapshot in enumerate(snapshots, start=1):
        require(snapshot.get("snapshot_index") == index, "stack location summary sequence")
        require(snapshot.get("scheduled_after_entry_seconds") == STACK_SNAPSHOT_DELAYS_SECONDS[index - 1], "stack location summary schedule")
        if schema_version == 1:
            require(snapshot.get("status") in {"CAPTURED", "SNAPSHOT_UNAVAILABLE"}, "legacy summary snapshot status")
            locations = snapshot.get("locations")
            _validate_stack_locations(locations, "legacy summary location")
            if snapshot["status"] == "CAPTURED":
                captured += 1
                require(bool(locations) and "unavailable_reason" not in snapshot, "captured legacy summary content")
            else:
                require(not locations and snapshot.get("unavailable_reason") in STACK_UNAVAILABLE_REASONS, "legacy summary unavailable classification")
            continue
        require(set(snapshot) == {"snapshot_index", "scheduled_after_entry_seconds", "status", "observations"}, "dual-role summary snapshot fields")
        observations = snapshot["observations"]
        require(isinstance(observations, list) and len(observations) == 2, "dual-role summary observations")
        require([item.get("role") for item in observations] == list(STACK_ROLES), "dual-role summary order")
        snapshot_captured = 0
        for observation in observations:
            require(set(observation) <= {"role", "status", "locations", "unavailable_reason"}, "summary role fields")
            role = observation.get("role")
            _validate_stack_locations(observation.get("locations"), "summary role location")
            if observation.get("status") == "CAPTURED":
                snapshot_captured += 1
                require(bool(observation["locations"]) and "unavailable_reason" not in observation, "captured summary role")
            else:
                require(observation.get("status") == "SNAPSHOT_UNAVAILABLE", "summary role status")
                reason = observation.get("unavailable_reason")
                require(not observation["locations"] and reason in STACK_UNAVAILABLE_REASONS, "summary role unavailable")
                if role == "MAIN_WORKER":
                    require(reason not in {"BACKGROUND_THREAD_UNAVAILABLE", "BACKGROUND_FRAME_UNAVAILABLE"}, "summary main role background classification")
                elif reason in {"PYTHON_FRAME_NOT_AVAILABLE", "SAMPLING_FAILURE"}:
                    raise RuntimeError("summary background role requires background-specific unavailable classification")
        expected_snapshot_status = "CAPTURED" if snapshot_captured == 2 else ("PARTIAL" if snapshot_captured else "SNAPSHOT_UNAVAILABLE")
        require(snapshot["status"] == expected_snapshot_status, "summary snapshot aggregate status")
        captured += snapshot_captured
    if schema_version == 1:
        require(value.get("captured_count") == captured, "legacy stack location captured count")
        expected_status = "CAPTURED" if captured == 2 else ("PARTIAL" if captured else "SNAPSHOT_UNAVAILABLE")
    else:
        require(value.get("role_count") == 2, "stack location summary role count")
        require(value.get("captured_observation_count") == captured, "stack location captured observation count")
        expected_status = "CAPTURED" if captured == 4 else ("PARTIAL" if captured else "SNAPSHOT_UNAVAILABLE")
    require(value.get("status") == expected_status, "stack location aggregate status")


def build_failure_diagnostic(
    *, framework_origin: str, trial_id: str, run_id: str, reason: str, timeout_seconds: float,
    records: list[dict[str, Any]], stderr: str, stderr_truncated: bool,
    worker_returncode: int | None, cleanup_signal: int | None,
    host_wrapper_pid: int, worker_command_sha256: str,
    seam_ready_existed: bool, midpoint_existed: bool,
    process_scan_path: Path | None = None,
) -> dict[str, Any]:
    require(reason in {"timeout_waiting_for_seam", "worker_exit_before_seam", "supervisor_validation_failure"}, "diagnostic reason")
    require(framework_origin in {"crewai", "drupal_ai"}, "diagnostic framework")
    phases = [record["phase"] for record in records]
    value = {
        "schema_version": 1,
        "status": "FAILED_BEFORE_VERIFIED_SEAM",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "trial_id": trial_id,
        "run_id": run_id,
        "lifecycle_identity": run_id,
        "framework_origin": framework_origin,
        "failure_reason": reason,
        "timeout_seconds": timeout_seconds,
        "last_completed_phase": phases[-1] if phases else None,
        "completed_phase_count": len(phases),
        "completed_phases": phases,
        "worker_returncode": worker_returncode,
        "host_wrapper_pid": host_wrapper_pid,
        "worker_command_sha256": worker_command_sha256,
        "bounded_sanitized_stderr": stderr,
        "stderr_truncated": stderr_truncated,
        "stderr_limit_characters": DIAGNOSTIC_LIMIT,
        "stdout_capture": "DEVNULL_NOT_PERSISTED",
        "seam_ready_existed": seam_ready_existed,
        "midpoint_existed": midpoint_existed,
        "seam_ready_verified": False,
        "actual_worker_identity_verified": False,
        "experimental_sigkill_delivered": False,
        "cleanup_termination_required": cleanup_signal is not None,
        "cleanup_signal_observed": cleanup_signal,
        "cleanup_is_not_experimental_sigkill": True,
        "automatic_retry_count": 0,
    }
    if framework_origin == "crewai":
        value["connection_boundary_classification"] = classify_connection_boundary(records)
    if framework_origin == "drupal_ai":
        process_scan_exists = process_scan_path is not None and process_scan_path.is_file()
        value["pre_kill_process_scan_existed"] = process_scan_exists
        value["pre_kill_process_scan_sha256"] = sha256(process_scan_path) if process_scan_exists else None
        value["pre_kill_process_scan_decision"] = read_json(process_scan_path).get("decision") if process_scan_exists else None
    return value


def validate_midpoint(value: dict[str, Any], *, origin: str, trial_id: str, run_id: str) -> None:
    require(value.get("schema_version") == 1, "midpoint schema_version")
    require(value.get("framework_origin") == origin, "midpoint framework identity")
    require(value.get("trial_id") == trial_id and value.get("run_id") == run_id, "midpoint trial/run identity")
    require(value.get("completed_sequences") == [1, 2, 3, 4, 5, 6], "midpoint completed sequences")
    require(value.get("next_target") == 7, "midpoint next target")
    require(value.get("target_7_started") is False, "target 7 already started")
    require(value.get("model_generations") == 0, "model activity in rehearsal")
    require(value.get("provider_requests") == 0, "provider activity in rehearsal")
    require(value.get("recommendation_writes") == 0, "recommendation write in rehearsal")
    require(value.get("source_mutations") == 0, "source mutation in rehearsal")
    identities = value.get("synthetic_recommendation_identities")
    require(isinstance(identities, list) and len(identities) == 6 and len(set(identities)) == 6, "midpoint identity set")


def validate_seam(value: dict[str, Any], *, origin: str, trial_id: str, run_id: str, midpoint_sha256: str, launched_pid: int) -> int:
    require(value.get("schema_version") == 1, "seam schema_version")
    require(value.get("semantic_boundary") == SEAM, "semantic boundary drift")
    require(value.get("framework_origin") == origin, "seam framework identity")
    require(value.get("trial_id") == trial_id and value.get("run_id") == run_id, "seam trial/run identity")
    require(value.get("completed_sequences") == [1, 2, 3, 4, 5, 6], "seam completed sequences")
    require(value.get("next_target") == 7 and value.get("target_7_started") is False, "seam target boundary")
    require(value.get("midpoint_sha256") == midpoint_sha256, "seam midpoint hash")
    require(value.get("independently_verifiable") is True, "seam is not independently verifiable")
    actual_pid = value.get("actual_worker_pid")
    host_pid = value.get("host_worker_pid")
    require(isinstance(actual_pid, int) and actual_pid > 1, "actual worker PID")
    require(isinstance(host_pid, int) and host_pid == launched_pid, "host worker PID")
    if origin != "drupal_ai":
        require(actual_pid == launched_pid, "local actual worker differs from launched process")
    else:
        require(re.fullmatch(r"[0-9a-f]{64}", str(value.get("lock_name_sha256", ""))) is not None, "Drupal lock identity")
        acquired = value.get("lock_acquired_at_unix")
        expires = value.get("lock_expires_not_before_unix")
        require(isinstance(acquired, (int, float)) and isinstance(expires, (int, float)), "Drupal lock timestamps")
        require(abs((expires - acquired) - 1800.0) < 0.001, "Drupal lock lease chronology")
    return actual_pid


def validate_durable_checkpoint(value: dict[str, Any] | None, *, trial_id: str, run_id: str, midpoint: dict[str, Any]) -> str:
    require(value is not None, "LangGraph durable checkpoint proof missing")
    require(value.get("schema_version") == 1, "durable checkpoint schema_version")
    require(value.get("status") == "PASS_DURABLE_CHECKPOINT", "durable checkpoint status")
    require(value.get("public_api") == "SqliteSaver.get_tuple", "durable checkpoint public API")
    require(value.get("trial_id") == trial_id and value.get("run_id") == run_id, "durable checkpoint trial/run identity")
    require(value.get("framework_origin") == "langgraph", "durable checkpoint framework identity")
    require(value.get("completed_sequences") == [1, 2, 3, 4, 5, 6], "durable checkpoint completed sequences")
    require(value.get("next_target") == 7 and value.get("target_7_started") is False, "durable checkpoint target boundary")
    require(value.get("pending_write_count") == 0, "durable checkpoint is merely pending")
    require(value.get("checkpoint_namespace") == "" and value.get("checkpoint_metadata_step") == 6, "durable checkpoint location")
    checkpoint_id = value.get("checkpoint_id")
    require(isinstance(checkpoint_id, str) and checkpoint_id, "durable checkpoint ID")
    projected_keys = (
        "schema_version", "trial_id", "run_id", "framework_origin", "completed_sequences",
        "next_target", "target_7_started", "synthetic_recommendation_identities",
        "first_post_restart_target", "model_generations", "provider_requests",
        "recommendation_writes", "source_mutations",
    )
    projection = {key: value.get(key) for key in projected_keys}
    expected_projection = {key: midpoint.get(key) for key in projected_keys}
    require(projection == expected_projection, "durable checkpoint differs from midpoint state")
    require(value.get("state_sha256") == hashlib.sha256(canonical(projection)).hexdigest(), "durable checkpoint state hash")
    return checkpoint_id


def run_durable_checkpoint_verifier(args: argparse.Namespace, control: Path) -> dict[str, Any]:
    require(args.checkpoint_verifier_command_json is not None, "LangGraph checkpoint verifier command missing")
    command = json.loads(args.checkpoint_verifier_command_json.read_text(encoding="utf-8"))
    require(isinstance(command, list) and command and all(isinstance(x, str) and x for x in command), "checkpoint verifier command")
    output = control / "durable-checkpoint.json"
    require(not output.exists(), "stale durable checkpoint proof")
    completed = subprocess.run(command, cwd=args.repo, env=sanitize_env(), text=True, capture_output=True, check=False)
    require(completed.returncode == 0, f"LangGraph durable checkpoint verifier failed: {completed.returncode}")
    require(output.is_file(), "LangGraph durable checkpoint verifier produced no proof")
    return read_json(output)


def run_drupal_process_check(
    command_path: Path | None,
    *,
    repo: Path,
    actual_pid: int,
    run_id: str,
    expect_present: bool,
    durable_output: Path,
) -> dict[str, Any]:
    require(command_path is not None, "Drupal process-check command missing")
    command = json.loads(command_path.read_text(encoding="utf-8"))
    expected = [
        "ddev", "drush", "--quiet", "php:script",
        "scripts/gate2c-step02-drupal-rehearsal.php", "--",
        "process-check", run_id, "{pid}",
    ]
    require(command == expected, "Drupal process-check command drift")
    resolved = [item.replace("{pid}", str(actual_pid)) for item in command]
    completed = subprocess.run(
        resolved, cwd=repo, env=sanitize_env(), text=True,
        capture_output=True, check=False,
    )
    require(completed.returncode == 0, "Drupal process-check command failed")
    value = json.loads(completed.stdout)
    require(isinstance(value, dict), "Drupal process-check output")
    require(not durable_output.exists(), "stale durable Drupal process-scan evidence")
    write_json(durable_output, value)
    require(value.get("run_id") == run_id, "Drupal process-check run identity")
    require(value.get("expected_worker_pid") == actual_pid, "Drupal process-check PID binding")
    require(value.get("record_type") == "DRUPAL_PROCESS_IDENTITY_SCAN", "Drupal process-check record type")
    require(value.get("verification_method") == "CONTAINER_PROCFS_EXACT_SEAM_PID_AND_PHP_ARGV_WITH_WORKER_UNIQUENESS", "Drupal process-check method")
    require(re.fullmatch(r"[0-9a-f]{64}", str(value.get("configuration_sha256", ""))) is not None, "Drupal process-check configuration hash")
    require(isinstance(value.get("observer_pid"), int) and value["observer_pid"] > 1, "Drupal process-check observer PID")
    pids = value.get("matching_worker_pids")
    require(isinstance(pids, list) and all(isinstance(pid, int) and pid > 1 for pid in pids), "Drupal process-check PID list")
    require(value.get("matching_worker_count") == len(pids), "Drupal process-check count/list mismatch")
    candidates = value.get("candidates")
    require(isinstance(candidates, list) and len(candidates) <= 32, "Drupal bounded process-check candidates")
    allowed = {"pid", "observer", "executable", "script", "mode", "run_id", "argument_count", "argv_sha256", "pid_namespace_matches_observer", "exact_worker_identity"}
    for candidate in candidates:
        require(isinstance(candidate, dict) and set(candidate) == allowed, "Drupal normalized candidate fields")
        require(re.fullmatch(r"[0-9a-f]{64}", str(candidate.get("argv_sha256", ""))) is not None, "Drupal candidate argv hash")
        require(not any(key in candidate for key in ("environment", "raw_cmdline", "arguments")), "Drupal process-scan privacy")
    if expect_present:
        require(value.get("expected_pid_verified") is True, "Drupal seam PID command identity mismatch")
        require(value.get("worker_uniqueness_verified") is True, "Drupal worker-mode uniqueness failure")
        require(value.get("decision") == "EXACT_SINGLETON_VERIFIED", "Drupal pre-kill worker identity is ambiguous")
        require(value.get("matching_worker_count") == 1 and pids == [actual_pid], "Drupal pre-kill exact PID singleton")
    else:
        require(value.get("matching_worker_count") == 0 and pids == [], "Drupal replacement worker detected")
        require(value.get("decision") == "NO_MATCHING_WORKER", "Drupal post-kill worker check")
    return value


def wait_for(path: Path, process: subprocess.Popen[bytes], timeout: float, captured: BoundedStderr) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        drain_stderr(process, captured)
        if path.is_file():
            return
        code = process.poll()
        if code is not None:
            raise RuntimeError(f"worker exited before seam-ready: {code}")
        time.sleep(0.05)
    raise SupervisorTimeout("timed out waiting for seam-ready")


def signal_from_returncode(returncode: int) -> int | None:
    return -returncode if returncode < 0 else 9 if returncode in (137, 255) else None


def build_drupal_signal_dispatch_record(
    *, run_id: str, actual_pid: int, host_wrapper_pid: int,
    kill_command: list[str], kill_returncode: int, pre_kill_scan: Path,
) -> dict[str, Any]:
    """Bind the exact inner-worker signal command before wrapper interpretation."""
    require(kill_command == ["ddev", "exec", "kill", "-9", str(actual_pid)], "Drupal resolved kill command")
    require(pre_kill_scan.is_file(), "Drupal pre-kill process-scan evidence missing")
    return {
        "schema_version": 1,
        "record_type": "DRUPAL_EXACT_WORKER_SIGNAL_DISPATCH",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "expected_php_worker_pid": actual_pid,
        "host_wrapper_pid": host_wrapper_pid,
        "requested_signal": 9,
        "kill_command_scope": "EXACT_ACTUAL_PHP_WORKER_PID_ONLY",
        "kill_command_sha256": hashlib.sha256(canonical(kill_command)).hexdigest(),
        "kill_command_returncode": kill_returncode,
        "kill_command_succeeded": kill_returncode == 0,
        "pre_kill_process_scan_sha256": sha256(pre_kill_scan),
        "pre_kill_decision": read_json(pre_kill_scan).get("decision"),
        "persisted_before_wrapper_interpretation": True,
        "automatic_retry_count": 0,
    }


def validate_drupal_termination_evidence(
    *, actual_pid: int, signal_dispatch: dict[str, Any],
    pre_kill_check: dict[str, Any], post_kill_check: dict[str, Any],
    wrapper_returncode: int,
) -> dict[str, Any]:
    """Prove inner-worker termination independently of the outer wrapper status."""
    require(signal_dispatch.get("expected_php_worker_pid") == actual_pid, "Drupal signal target PID mismatch")
    require(signal_dispatch.get("requested_signal") == 9, "Drupal requested signal mismatch")
    require(signal_dispatch.get("kill_command_succeeded") is True, "Drupal SIGKILL delivery command failed")
    require(signal_dispatch.get("kill_command_returncode") == 0, "Drupal SIGKILL command return status")
    require(signal_dispatch.get("pre_kill_decision") == "EXACT_SINGLETON_VERIFIED", "Drupal pre-kill decision")
    require(pre_kill_check.get("decision") == "EXACT_SINGLETON_VERIFIED", "Drupal pre-kill verification")
    require(pre_kill_check.get("matching_worker_pids") == [actual_pid], "Drupal pre-kill exact PID singleton")
    require(post_kill_check.get("decision") == "NO_MATCHING_WORKER", "Drupal post-kill verification")
    require(post_kill_check.get("matching_worker_count") == 0, "Drupal replacement worker detected")
    require(post_kill_check.get("matching_worker_pids") == [], "Drupal post-kill PID list")
    require(isinstance(wrapper_returncode, int), "Drupal wrapper outcome missing")
    return {
        "inner_worker_signal_proof": "EXACT_SIGKILL_COMMAND_AND_POST_SIGNAL_ABSENCE",
        "outer_wrapper_returncode": wrapper_returncode,
        "outer_wrapper_signal_interpretation": signal_from_returncode(wrapper_returncode),
        "wrapper_status_is_not_inner_worker_signal_status": True,
        "supervisor_cleanup_status": "NOT_REQUIRED_EXACT_WORKER_ABSENT",
    }


def sanitize_env() -> dict[str, str]:
    env = dict(os.environ)
    for key in ("OPENAI_API_KEY", "OPENAI_CANDIDATE_MODEL", "CREWAI_CANDIDATE_MODEL"):
        env.pop(key, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run(args: argparse.Namespace) -> int:
    control = args.control_dir.resolve()
    require(control.is_dir() and not control.is_symlink(), "control directory")
    require(args.framework in ORIGINS, "framework origin")
    require(args.timeout == 30.0, "canonical timeout drift")
    if args.framework in {"crewai", "drupal_ai"}:
        require(args.diagnostic_output is not None, f"{args.framework} diagnostic output required")
    command_value = json.loads(args.worker_command_json.read_text(encoding="utf-8"))
    require(isinstance(command_value, list) and command_value and all(isinstance(x, str) and x for x in command_value), "worker command")
    seam_path = control / "seam-ready.json"
    midpoint_path = control / "midpoint.json"
    phase_path = control / "startup-phases.jsonl"
    require(not seam_path.exists() and not midpoint_path.exists(), "stale control artifact")
    process = subprocess.Popen(command_value, cwd=args.repo, env=sanitize_env(), start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert process.stderr is not None
    os.set_blocking(process.stderr.fileno(), False)
    captured = BoundedStderr()
    (control / "expected-host-pid.txt").write_text(f"{process.pid}\n", encoding="ascii")
    delivered = False
    try:
        wait_for(seam_path, process, args.timeout, captured)
        require(midpoint_path.is_file(), "midpoint missing at seam")
        midpoint = read_json(midpoint_path)
        validate_midpoint(midpoint, origin=args.framework, trial_id=args.trial_id, run_id=args.run_id)
        midpoint_hash = sha256(midpoint_path)
        seam = read_json(seam_path)
        actual_pid = validate_seam(seam, origin=args.framework, trial_id=args.trial_id, run_id=args.run_id, midpoint_sha256=midpoint_hash, launched_pid=process.pid)
        if args.framework == "crewai":
            phases = validate_startup_phases(phase_path, trial_id=args.trial_id, run_id=args.run_id)
            require(phases and phases[-1]["phase"] == "seam_ready_emitted", "CrewAI startup phases do not reach verified seam")
        durable_checkpoint_id = None
        if args.framework == "langgraph":
            durable = run_durable_checkpoint_verifier(args, control)
            durable_checkpoint_id = validate_durable_checkpoint(durable, trial_id=args.trial_id, run_id=args.run_id, midpoint=midpoint)
        else:
            require(args.checkpoint_verifier_command_json is None, "checkpoint verifier is LangGraph-only")
        if args.framework == "drupal_ai":
            require(args.kill_command_json is not None, "Drupal actual-worker kill command required")
            require(args.pre_kill_process_scan_output is not None, "Drupal pre-kill process-scan output required")
            require(args.post_kill_process_scan_output is not None, "Drupal post-kill process-scan output required")
            require(args.signal_dispatch_output is not None, "Drupal signal-dispatch output required")
            kill_command = json.loads(args.kill_command_json.read_text(encoding="utf-8"))
            require(kill_command == ["ddev", "exec", "kill", "-9", "{pid}"], "Drupal kill command drift")
            pre_kill_check = run_drupal_process_check(
                args.process_check_command_json,
                repo=args.repo,
                actual_pid=actual_pid,
                run_id=args.run_id,
                expect_present=True,
                durable_output=args.pre_kill_process_scan_output,
            )
            kill_command = [str(item).replace("{pid}", str(actual_pid)) for item in kill_command]
            signal_delivered_at = datetime.now(timezone.utc).isoformat()
            killed = subprocess.run(kill_command, cwd=args.repo, env=sanitize_env(), check=False)
            signal_dispatch = build_drupal_signal_dispatch_record(
                run_id=args.run_id,
                actual_pid=actual_pid,
                host_wrapper_pid=process.pid,
                kill_command=kill_command,
                kill_returncode=killed.returncode,
                pre_kill_scan=args.pre_kill_process_scan_output,
            )
            require(not args.signal_dispatch_output.exists(), "stale durable Drupal signal-dispatch evidence")
            write_json(args.signal_dispatch_output, signal_dispatch)
            require(killed.returncode == 0, "Drupal SIGKILL delivery command failed")
        else:
            signal_delivered_at = datetime.now(timezone.utc).isoformat()
            os.kill(actual_pid, signal.SIGKILL)
        delivered = True
        post_kill_check = None
        if args.framework == "drupal_ai":
            post_kill_check = run_drupal_process_check(
                args.process_check_command_json,
                repo=args.repo,
                actual_pid=actual_pid,
                run_id=args.run_id,
                expect_present=False,
                durable_output=args.post_kill_process_scan_output,
            )
            returncode = process.wait(timeout=10)
            drain_stderr(process, captured)
            signal_number = signal_from_returncode(returncode)
            termination_evidence = validate_drupal_termination_evidence(
                actual_pid=actual_pid,
                signal_dispatch=signal_dispatch,
                pre_kill_check=pre_kill_check,
                post_kill_check=post_kill_check,
                wrapper_returncode=returncode,
            )
        else:
            returncode = process.wait(timeout=10)
            drain_stderr(process, captured)
            signal_number = signal_from_returncode(returncode)
            require(signal_number == 9, f"worker termination was not signal 9: {returncode}")
        result = {
            "schema_version": 1, "status": "PASS", "trial_id": args.trial_id,
            "run_id": args.run_id, "framework_origin": args.framework,
            "semantic_boundary": SEAM, "midpoint_sha256": midpoint_hash,
            "actual_worker_pid_recorded": True, "requested_signal": "SIGKILL",
            "actual_worker_pid": actual_pid, "host_worker_pid": process.pid,
            "signal_delivered_at": signal_delivered_at,
            "observed_signal": 9, "actual_worker_terminated": True,
            "supervisor_only_trigger": True, "automatic_retry_count": 0,
            "model_generations": 0, "provider_requests": 0,
            "drupal_writes": 0 if args.framework != "drupal_ai" else None,
        }
        if args.framework == "langgraph":
            result.update({
                "durable_checkpoint_verified": True,
                "durable_checkpoint_public_api": "SqliteSaver.get_tuple",
                "durable_checkpoint_id": durable_checkpoint_id,
                "durable_checkpoint_pending_write_count": 0,
            })
        if args.framework == "drupal_ai":
            result.update({
                "pre_kill_worker_identity_verified": pre_kill_check["matching_worker_pids"] == [actual_pid],
                "post_kill_worker_absent": post_kill_check["matching_worker_count"] == 0,
                "replacement_worker_count": post_kill_check["matching_worker_count"],
                "worker_launch_count": 1,
                "signal_command_returncode": signal_dispatch["kill_command_returncode"],
                "signal_dispatch_sha256": sha256(args.signal_dispatch_output),
                "pre_kill_process_scan_sha256": sha256(args.pre_kill_process_scan_output),
                "post_kill_process_scan_sha256": sha256(args.post_kill_process_scan_output),
                "kill_command_scope": "EXACT_ACTUAL_PHP_WORKER_PID_ONLY",
                "lock_name_sha256": seam.get("lock_name_sha256"),
                "lock_acquired_at_unix": seam.get("lock_acquired_at_unix"),
                "lock_expires_not_before_unix": seam.get("lock_expires_not_before_unix"),
            })
            result.update(termination_evidence)
        write_json(args.output, result)
        return 0
    except Exception as exc:
        cleanup_signal = None
        if process.poll() is None:
            process.kill()
            cleanup_returncode = process.wait(timeout=10)
            cleanup_signal = signal_from_returncode(cleanup_returncode)
        drain_stderr(process, captured)
        if args.framework in {"crewai", "drupal_ai"} and not delivered:
            try:
                phases = validate_startup_phases(phase_path, trial_id=args.trial_id, run_id=args.run_id) if args.framework == "crewai" else []
            except Exception:
                phases = []
            stderr, truncated = captured.sanitized()
            reason = "timeout_waiting_for_seam" if isinstance(exc, SupervisorTimeout) else "worker_exit_before_seam" if process.returncode not in (None, -9) else "supervisor_validation_failure"
            write_json(args.diagnostic_output, build_failure_diagnostic(
                framework_origin=args.framework, trial_id=args.trial_id, run_id=args.run_id, reason=reason,
                timeout_seconds=args.timeout, records=phases, stderr=stderr,
                stderr_truncated=truncated, worker_returncode=process.returncode,
                cleanup_signal=cleanup_signal, host_wrapper_pid=process.pid,
                worker_command_sha256=hashlib.sha256(canonical(command_value)).hexdigest(),
                seam_ready_existed=seam_path.is_file(), midpoint_existed=midpoint_path.is_file(),
                process_scan_path=args.pre_kill_process_scan_output,
            ))
        raise
    finally:
        if process.stderr is not None:
            process.stderr.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--control-dir", required=True, type=Path)
    parser.add_argument("--framework", required=True, choices=sorted(ORIGINS))
    parser.add_argument("--trial-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--worker-command-json", required=True, type=Path)
    parser.add_argument("--checkpoint-verifier-command-json", type=Path)
    parser.add_argument("--kill-command-json", type=Path)
    parser.add_argument("--process-check-command-json", type=Path)
    parser.add_argument("--pre-kill-process-scan-output", type=Path)
    parser.add_argument("--post-kill-process-scan-output", type=Path)
    parser.add_argument("--signal-dispatch-output", type=Path)
    parser.add_argument("--diagnostic-output", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=30.0)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
