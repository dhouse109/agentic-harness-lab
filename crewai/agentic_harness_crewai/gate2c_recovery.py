"""Model-free Gate 2C CrewAI recovery candidate with bounded startup phases."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field


SEAM = "after target 6 is fully persisted and before target 7 begins"
XDG_SUBDIRS = {
    "XDG_DATA_HOME": "data",
    "XDG_CONFIG_HOME": "config",
    "XDG_CACHE_HOME": "cache",
}
STARTUP_PHASES = frozenset({
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
MAX_PHASE_RECORD_BYTES = 1024
STACK_SNAPSHOT_DELAYS_SECONDS = (8.0, 18.0)
STACK_SNAPSHOT_COUNT = 2
STACK_DEPTH_LIMIT = 12
MAX_STACK_RECORD_BYTES = 8192
STACK_ROLES = ("MAIN_WORKER", "LANCEDB_BACKGROUND_LOOP")
BACKGROUND_THREAD_NAME = "LanceDBBackgroundEventLoop"
SAFE_LOCATION = re.compile(r"^[A-Za-z0-9_.<>-]{1,160}$")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def synthetic_identity(run_id: str, sequence: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"gate2c-model-free:{run_id}:{sequence}"))


class StartupPhaseReporter:
    """Append only fixed-schema phase records; never accepts payload text."""

    def __init__(self, path: Path, *, trial_id: str, run_id: str) -> None:
        self.path = path.resolve()
        self.trial_id = trial_id
        self.run_id = run_id
        self.sequence = 0
        require("/.cache/gate2c-step02/" in self.path.as_posix(), "phase log must be run-scoped")
        require(
            self.path.name in {"startup-phases.jsonl", "recovery-phases.jsonl"},
            "unexpected phase log name",
        )
        require(not self.path.exists(), "startup phase log must be fresh")
        require(self.path.parent.is_dir() and not self.path.parent.is_symlink(), "phase log parent")

    def record(self, phase: str, *, error_type: str | None = None) -> None:
        require(phase in STARTUP_PHASES, "unapproved startup phase")
        require(error_type is None or (error_type.isidentifier() and len(error_type) <= 80), "unsafe error type")
        self.sequence += 1
        value: dict[str, Any] = {
            "schema_version": 1,
            "sequence": self.sequence,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "monotonic_ns": time.monotonic_ns(),
            "framework_origin": "crewai",
            "trial_id": self.trial_id,
            "run_id": self.run_id,
            "phase": phase,
        }
        if error_type is not None:
            value["error_type"] = error_type
        payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        require(len(payload) <= MAX_PHASE_RECORD_BYTES, "startup phase record too large")
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(self.path, flags, 0o600)
        try:
            os.write(fd, payload)
            os.fsync(fd)
        finally:
            os.close(fd)


def sanitized_module_location(filename: str) -> str:
    """Map a code filename to a bounded module label without retaining a path."""
    normalized = filename.replace("\\", "/")
    relative: str | None = None
    if "/site-packages/" in normalized:
        relative = normalized.rsplit("/site-packages/", 1)[1]
    elif "/crewai/agentic_harness_crewai/" in normalized:
        relative = "agentic_harness_crewai/" + normalized.rsplit(
            "/crewai/agentic_harness_crewai/", 1
        )[1]
    else:
        match = re.search(r"/lib/python[0-9.]+/(.+)$", normalized)
        if match and not match.group(1).startswith("site-packages/"):
            relative = "stdlib/" + match.group(1)
    if relative is None:
        return "unclassified"
    if relative.endswith(".py"):
        relative = relative[:-3]
    parts = [part for part in relative.split("/") if part and part != "__init__"]
    module = ".".join(parts)
    return module if SAFE_LOCATION.fullmatch(module) else "unclassified"


def sanitized_function_location(code: Any) -> str:
    """Return only a bounded function label from a code object."""
    value = getattr(code, "co_qualname", None) or getattr(code, "co_name", "")
    return value if isinstance(value, str) and SAFE_LOCATION.fullmatch(value) else "unclassified"


def bounded_stack_locations(frame: Any, *, depth_limit: int = STACK_DEPTH_LIMIT) -> list[dict[str, str]]:
    """Reduce a Python frame chain immediately to module/function labels only."""
    require(1 <= depth_limit <= STACK_DEPTH_LIMIT, "stack depth limit")
    locations: list[dict[str, str]] = []
    current = frame
    try:
        while current is not None and len(locations) < depth_limit:
            code = current.f_code
            locations.append({
                "module": sanitized_module_location(code.co_filename),
                "function": sanitized_function_location(code),
            })
            current = current.f_back
    finally:
        del current
        del frame
    return locations


def identify_lancedb_background_thread(
    loop_thread: Any,
    *,
    worker_thread_id: int,
    enumerate_threads: Callable[[], list[Any]] = threading.enumerate,
) -> tuple[int | None, str | None]:
    """Identify the exact pinned LOOP.thread without retaining its identifier."""
    try:
        first_ident = getattr(loop_thread, "ident", None)
        if (
            loop_thread is None
            or not loop_thread.is_alive()
            or loop_thread.daemon is not True
            or loop_thread.name != BACKGROUND_THREAD_NAME
            or not isinstance(first_ident, int)
            or first_ident == worker_thread_id
        ):
            return None, "BACKGROUND_THREAD_UNAVAILABLE"
        matches = [
            thread
            for thread in enumerate_threads()
            if getattr(thread, "name", None) == BACKGROUND_THREAD_NAME
        ]
        second_ident = getattr(loop_thread, "ident", None)
        if (
            len(matches) != 1
            or matches[0] is not loop_thread
            or not loop_thread.is_alive()
            or second_ident != first_ident
        ):
            return None, "BACKGROUND_THREAD_UNAVAILABLE"
        return first_ident, None
    except Exception:
        return None, "BACKGROUND_THREAD_UNAVAILABLE"


class StackLocationProbe:
    """Take two bounded main/background function-location snapshots."""

    def __init__(
        self,
        path: Path,
        *,
        trial_id: str,
        run_id: str,
        worker_thread_id: int,
        background_thread_id: int | None,
        background_thread_unavailable_reason: str | None,
        delays: tuple[float, ...] = STACK_SNAPSHOT_DELAYS_SECONDS,
        frame_provider: Callable[[], dict[int, Any]] = sys._current_frames,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.path = path.resolve()
        self.trial_id = trial_id
        self.run_id = run_id
        self.worker_thread_id = worker_thread_id
        self.background_thread_id = background_thread_id
        self.background_thread_unavailable_reason = background_thread_unavailable_reason
        self.delays = delays
        self.frame_provider = frame_provider
        self.sleeper = sleeper
        self.connection_completed = threading.Event()
        self.started = False
        self.thread: threading.Thread | None = None
        require("/.cache/gate2c-step02/" in self.path.as_posix(), "stack log must be run-scoped")
        require(self.path.name == "stack-locations.jsonl", "unexpected stack log name")
        require(not self.path.exists(), "stack log must be fresh")
        require(self.path.parent.is_dir() and not self.path.parent.is_symlink(), "stack log parent")
        require(
            1 <= len(delays) <= STACK_SNAPSHOT_COUNT
            and all(isinstance(delay, float) and delay > 0 for delay in delays)
            and list(delays) == sorted(delays),
            "bounded deterministic stack delays",
        )
        require(
            (background_thread_id is not None and background_thread_unavailable_reason is None)
            or (
                background_thread_id is None
                and background_thread_unavailable_reason == "BACKGROUND_THREAD_UNAVAILABLE"
            ),
            "background thread availability classification",
        )
        require(background_thread_id != worker_thread_id, "background thread must differ from main worker")

    def start_after_connection_entry(self) -> None:
        require(not self.started, "stack probe already started")
        self.started = True
        self.thread = threading.Thread(
            target=self._sample,
            name="gate2c-stack-location-probe",
            daemon=True,
        )
        self.thread.start()

    def mark_connection_completed(self) -> None:
        self.connection_completed.set()

    def join(self, timeout: float = 1.0) -> None:
        if self.thread is not None:
            self.thread.join(timeout)

    def _record(
        self,
        index: int,
        delay: float,
        observations: list[dict[str, Any]],
    ) -> None:
        require(
            [observation.get("role") for observation in observations] == list(STACK_ROLES),
            "stack observation roles",
        )
        captured = sum(observation.get("status") == "CAPTURED" for observation in observations)
        status = "CAPTURED" if captured == 2 else ("PARTIAL" if captured else "SNAPSHOT_UNAVAILABLE")
        value: dict[str, Any] = {
            "schema_version": 2,
            "snapshot_index": index,
            "scheduled_after_entry_seconds": delay,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "monotonic_ns": time.monotonic_ns(),
            "framework_origin": "crewai",
            "trial_id": self.trial_id,
            "run_id": self.run_id,
            "status": status,
            "observations": observations,
        }
        payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        require(len(payload) <= MAX_STACK_RECORD_BYTES, "stack location record too large")
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(self.path, flags, 0o600)
        try:
            os.write(fd, payload)
            os.fsync(fd)
        finally:
            os.close(fd)

    @staticmethod
    def _unavailable(role: str, reason: str) -> dict[str, Any]:
        return {
            "role": role,
            "status": "SNAPSHOT_UNAVAILABLE",
            "locations": [],
            "unavailable_reason": reason,
        }

    @staticmethod
    def _capture(role: str, frame: Any, missing_reason: str) -> dict[str, Any]:
        if frame is None:
            return StackLocationProbe._unavailable(role, missing_reason)
        try:
            locations = bounded_stack_locations(frame)
            if not locations:
                return StackLocationProbe._unavailable(role, missing_reason)
            return {"role": role, "status": "CAPTURED", "locations": locations}
        except Exception:
            return StackLocationProbe._unavailable(role, missing_reason)
        finally:
            del frame

    def _sample(self) -> None:
        started = time.monotonic()
        for index, delay in enumerate(self.delays, start=1):
            self.sleeper(max(0.0, started + delay - time.monotonic()))
            if self.connection_completed.is_set():
                self._record(
                    index,
                    delay,
                    [
                        self._unavailable("MAIN_WORKER", "CONNECTION_COMPLETED_BEFORE_SNAPSHOT"),
                        self._unavailable(
                            "LANCEDB_BACKGROUND_LOOP",
                            "CONNECTION_COMPLETED_BEFORE_SNAPSHOT",
                        ),
                    ],
                )
                continue
            frames: dict[int, Any] | None = None
            main_frame: Any = None
            background_frame: Any = None
            try:
                # Exactly one all-thread snapshot per scheduled sampling point.
                frames = self.frame_provider()
                main_frame = frames.get(self.worker_thread_id)
                if self.background_thread_id is not None:
                    background_frame = frames.get(self.background_thread_id)
                frames.clear()
                del frames
                frames = None
                main = self._capture(
                    "MAIN_WORKER",
                    main_frame,
                    "PYTHON_FRAME_NOT_AVAILABLE",
                )
                main_frame = None
                if self.background_thread_id is None:
                    background = self._unavailable(
                        "LANCEDB_BACKGROUND_LOOP",
                        self.background_thread_unavailable_reason
                        or "BACKGROUND_THREAD_UNAVAILABLE",
                    )
                else:
                    background = self._capture(
                        "LANCEDB_BACKGROUND_LOOP",
                        background_frame,
                        "BACKGROUND_FRAME_UNAVAILABLE",
                    )
                background_frame = None
                self._record(index, delay, [main, background])
            except Exception:
                self._record(
                    index,
                    delay,
                    [
                        self._unavailable("MAIN_WORKER", "SAMPLING_FAILURE"),
                        self._unavailable(
                            "LANCEDB_BACKGROUND_LOOP",
                            "BACKGROUND_THREAD_UNAVAILABLE"
                            if self.background_thread_id is None
                            else "BACKGROUND_FRAME_UNAVAILABLE",
                        ),
                    ],
                )
            finally:
                if frames is not None:
                    frames.clear()
                del main_frame
                del background_frame
                del frames


class ConnectionBoundaryTrace:
    """Observe only the pinned Python ``lancedb.connect`` call boundary.

    The diagnostic trace delegates execution to the original function unchanged.
    It never reads arguments, return values, frame locals, or exception text.
    """

    def __init__(
        self,
        reporter: StartupPhaseReporter,
        target_code: Any,
        stack_probe: StackLocationProbe | None = None,
    ) -> None:
        require(hasattr(target_code, "co_filename"), "LanceDB connect code object required")
        self.reporter = reporter
        self.target_code = target_code
        self.previous_trace: Any = None
        self.target_frame_id: int | None = None
        self.entered = False
        self.returned = False
        self.exception_seen = False
        self.stack_probe = stack_probe

    def arm(self) -> None:
        self.previous_trace = sys.gettrace()
        require(self.previous_trace is None, "pre-existing Python trace is unsupported")
        self.reporter.record("lancedb_connection_trace_armed")
        sys.settrace(self)

    def disarm(self) -> None:
        sys.settrace(self.previous_trace)

    def __call__(self, frame: Any, event: str, arg: Any) -> Any:
        if event == "call" and frame.f_code is self.target_code:
            if self.entered:
                return None
            self.entered = True
            self.target_frame_id = id(frame)
            self.reporter.record("lancedb_connect_entered")
            if self.stack_probe is not None:
                self.stack_probe.start_after_connection_entry()
            return self._trace_target
        return None

    def _trace_target(self, frame: Any, event: str, arg: Any) -> Any:
        if id(frame) != self.target_frame_id:
            return None
        if event == "exception" and not self.exception_seen:
            if self.stack_probe is not None:
                self.stack_probe.mark_connection_completed()
            error_type = arg[0].__name__ if isinstance(arg, tuple) and isinstance(arg[0], type) else "Exception"
            self.exception_seen = True
            self.reporter.record("lancedb_connect_exception", error_type=error_type)
        elif event == "return" and not self.exception_seen:
            if self.stack_probe is not None:
                self.stack_probe.mark_connection_completed()
            self.returned = True
            self.reporter.record("lancedb_connect_returned_memory_initialization_continues")
        return self._trace_target


def diagnostic_connection_trace(
    reporter: StartupPhaseReporter,
    stack_log: Path,
) -> ConnectionBoundaryTrace:
    """Bind the diagnostic trace to the imported, pinned public connect function."""
    import lancedb
    from lancedb.background_loop import LOOP

    connect = lancedb.connect
    require(callable(connect) and hasattr(connect, "__code__"), "Python lancedb.connect boundary unavailable")
    worker_thread_id = threading.get_ident()
    background_thread_id, background_unavailable = identify_lancedb_background_thread(
        LOOP.thread,
        worker_thread_id=worker_thread_id,
    )
    probe = StackLocationProbe(
        stack_log,
        trial_id=reporter.trial_id,
        run_id=reporter.run_id,
        worker_thread_id=worker_thread_id,
        background_thread_id=background_thread_id,
        background_thread_unavailable_reason=background_unavailable,
    )
    return ConnectionBoundaryTrace(reporter, connect.__code__, stack_probe=probe)


def validate_bootstrap_storage(runtime: Path) -> dict[str, Any]:
    """Fail closed unless CrewAI bootstrap storage is fresh-run scoped and separate."""
    bootstrap = (runtime.parent / "bootstrap").resolve()
    roots: dict[str, Path] = {}
    for key, subdir in XDG_SUBDIRS.items():
        raw = os.environ.get(key)
        require(bool(raw), f"{key} is required before CrewAI import")
        value = Path(raw).resolve()
        require(value == bootstrap / subdir, f"{key} is not bound to the run-scoped bootstrap root")
        require(value.is_dir() and os.access(value, os.W_OK), f"{key} is not writable")
        roots[key] = value
    require(not os.environ.get("CREWAI_STORAGE_DIR"), "CREWAI_STORAGE_DIR override is prohibited")
    require(os.environ.get("CREWAI_DISABLE_VERSION_CHECK") == "true", "CrewAI version check must be disabled")
    require(all(runtime != root and root not in runtime.parents for root in roots.values()), "bootstrap storage overlaps SQLiteFlowPersistence")
    return {
        "mechanism": list(XDG_SUBDIRS),
        "configured_before_worker_import": True,
        "fresh_run_scoped": True,
        "writable": True,
        "separate_from_sqlite_flow_persistence": True,
        "default_home_storage_avoided": True,
    }


class RehearsalState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = "unset"
    trial_id: str = "unset"
    run_id: str = "unset"
    framework_origin: str = "crewai"
    lifecycle_stage: str = "initialized"
    completed_sequences: list[int] = Field(default_factory=list)
    next_target: int = 1
    target_7_started: bool = False
    synthetic_recommendation_identities: list[str] = Field(default_factory=list)
    first_post_restart_target: int | None = None
    model_generations: int = 0
    provider_requests: int = 0
    recommendation_writes: int = 0
    source_mutations: int = 0


def midpoint(state: RehearsalState) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "trial_id": state.trial_id,
        "run_id": state.run_id,
        "framework_origin": "crewai",
        "completed_sequences": list(state.completed_sequences),
        "next_target": state.next_target,
        "target_7_started": state.target_7_started,
        "synthetic_recommendation_identities": list(state.synthetic_recommendation_identities),
        "model_generations": state.model_generations,
        "provider_requests": state.provider_requests,
        "recommendation_writes": state.recommendation_writes,
        "source_mutations": state.source_mutations,
    }


def validate_persisted_midpoint(persistence: Any, state: RehearsalState) -> None:
    loaded = persistence.load_state(state.id)
    require(isinstance(loaded, dict), "public load_state returned no target-6 midpoint")
    require(loaded.get("trial_id") == state.trial_id and loaded.get("run_id") == state.run_id, "persisted midpoint identity")
    require(loaded.get("completed_sequences") == [1, 2, 3, 4, 5, 6], "persisted midpoint sequence")
    require(loaded.get("next_target") == 7 and loaded.get("target_7_started") is False, "persisted midpoint boundary")
    require(all(loaded.get(key) == 0 for key in ("model_generations", "provider_requests", "recommendation_writes", "source_mutations")), "persisted midpoint zero-operation boundary")


def import_crewai_runtime() -> tuple[Any, Any, Any, Any, Any, Any]:
    from crewai.flow import Flow, start
    from crewai.flow.persistence import SQLiteFlowPersistence, persist
    from crewai.memory.storage.factory import set_memory_storage_factory

    from .canonical_slice import RunScopedMemoryStorage

    return (
        Flow,
        start,
        SQLiteFlowPersistence,
        persist,
        set_memory_storage_factory,
        RunScopedMemoryStorage,
    )


def build_flow(*, persistence: Any, mode: str, control: Path, reporter: StartupPhaseReporter, runtime: tuple[Any, Any, Any, Any, Any, Any]) -> Any:
    Flow, start, _, persist, set_memory_storage_factory, RunScopedMemoryStorage = runtime
    memory_backend = RunScopedMemoryStorage()
    set_memory_storage_factory(lambda spec: memory_backend)

    @persist(persistence)
    class Gate2CRehearsalFlow(Flow[RehearsalState]):
        @start()
        def process(self) -> dict[str, Any]:
            reporter.record("flow_method_started")
            require(self.state.next_target == len(self.state.completed_sequences) + 1, "state sequence mismatch")
            if mode == "recover":
                require(self.state.completed_sequences == [1, 2, 3, 4, 5, 6], "CrewAI target-6 state missing")
                require(self.state.next_target == 7, "CrewAI next target differs")
            for sequence in range(self.state.next_target, 13):
                require(sequence not in self.state.completed_sequences, f"CrewAI replay at {sequence}")
                if mode == "recover" and self.state.first_post_restart_target is None:
                    require(sequence == 7, "CrewAI target 7 was not first post-restart work")
                    self.state.first_post_restart_target = sequence
                self.state.target_7_started = self.state.target_7_started or sequence == 7
                self.state.completed_sequences.append(sequence)
                self.state.synthetic_recommendation_identities.append(synthetic_identity(self.state.run_id, sequence))
                self.state.next_target = sequence + 1
                self.state.lifecycle_stage = "target_finalized"
                persistence.save_state(self.state.id, "target_finalized", self.state)
                if sequence == 6 and mode == "prekill":
                    reporter.record("target_6_sqlite_persisted")
                    validate_persisted_midpoint(persistence, self.state)
                    reporter.record("target_6_midpoint_verified")
                    value = midpoint(self.state)
                    midpoint_path = control / "midpoint.json"
                    write_json(midpoint_path, value)
                    write_json(control / "seam-ready.json", {
                        "schema_version": 1,
                        "semantic_boundary": SEAM,
                        "framework_origin": "crewai",
                        "trial_id": self.state.trial_id,
                        "run_id": self.state.run_id,
                        "completed_sequences": [1, 2, 3, 4, 5, 6],
                        "next_target": 7,
                        "target_7_started": False,
                        "midpoint_sha256": file_sha(midpoint_path),
                        "independently_verifiable": True,
                        "host_worker_pid": os.getpid(),
                        "actual_worker_pid": os.getpid(),
                    })
                    reporter.record("seam_ready_emitted")
                    while True:
                        time.sleep(1)
            self.state.lifecycle_stage = "complete"
            persistence.save_state(self.state.id, "complete", self.state)
            return {"status": "complete", "completed_sequences": list(self.state.completed_sequences)}

    return Gate2CRehearsalFlow(suppress_flow_events=True, tracing=False)


def worker(args: argparse.Namespace) -> int:
    require(not os.environ.get("OPENAI_API_KEY"), "OPENAI_API_KEY must be unset")
    runtime_db = args.runtime_db.resolve()
    control = args.control_dir.resolve()
    require("/.cache/gate2c-step02/" in runtime_db.as_posix(), "disposable runtime root required")
    require(control == runtime_db.parent and not control.is_symlink(), "control/runtime isolation")
    reporter = StartupPhaseReporter(args.phase_log, trial_id=args.trial_id, run_id=args.run_id)
    reporter.record("worker_process_initialized")
    try:
        runtime_db.parent.mkdir(parents=True, exist_ok=True)
        bootstrap_storage = validate_bootstrap_storage(runtime_db)
        reporter.record("xdg_storage_validated")
        reporter.record("crewai_import_started")
        crewai_runtime = import_crewai_runtime()
        reporter.record("crewai_import_completed")
        _, _, SQLiteFlowPersistence, _, _, _ = crewai_runtime
        reporter.record("sqlite_persistence_initialization_started")
        persistence = SQLiteFlowPersistence(str(runtime_db))
        reporter.record("sqlite_persistence_initialized")
        reporter.record("flow_construction_started_memory_initialization_pending")
        connection_trace = (
            diagnostic_connection_trace(reporter, args.stack_log)
            if args.mode == "diagnose-startup"
            else None
        )
        if connection_trace is not None:
            connection_trace.arm()
        try:
            flow = build_flow(persistence=persistence, mode=args.mode, control=control, reporter=reporter, runtime=crewai_runtime)
        finally:
            if connection_trace is not None:
                connection_trace.disarm()
        if connection_trace is not None:
            require(not connection_trace.entered, "accepted memory factory fell back to lancedb.connect")
            require(not connection_trace.returned and not connection_trace.exception_seen, "unexpected lancedb.connect completion state")
        reporter.record("flow_construction_and_memory_initialization_completed")

        if args.mode == "diagnose-startup":
            reporter.record("startup_diagnostic_completed")
            write_json(args.output, {
                "schema_version": 1,
                "status": "PASS",
                "diagnostic_scope": "FLOW_CONSTRUCTION_ONLY",
                "model_free": True,
                "framework_origin": "crewai",
                "trial_id": args.trial_id,
                "run_id": args.run_id,
                "flow_constructed": True,
                "flow_invoked": False,
                "memory_storage_backend": "RunScopedMemoryStorage",
                "lancedb_connect_entered": False,
                "sigkill_delivered": False,
                "model_generations": 0,
                "provider_requests": 0,
                "drupal_operations": 0,
                "bootstrap_storage": bootstrap_storage,
            })
            return 0

        if args.mode == "prekill":
            flow.state.id = args.run_id
            flow.state.run_id = args.run_id
            flow.state.trial_id = args.trial_id
            reporter.record("flow_invocation_started")
            flow.kickoff()
            raise RuntimeError("prekill CrewAI worker escaped seam")

        loaded = persistence.load_state(args.run_id)
        require(isinstance(loaded, dict), "public load_state returned no state")
        loaded_hash = hashlib.sha256(json.dumps(loaded, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        require(loaded.get("completed_sequences") == [1, 2, 3, 4, 5, 6], "public load_state target-6 projection")
        require(loaded.get("next_target") == 7, "public load_state next target")
        reporter.record("flow_invocation_started")
        result = flow.kickoff(inputs={"id": args.run_id})
        state = flow.state
        require(result["status"] == "complete", "CrewAI recovery did not complete")
        require(state.id == args.run_id and state.run_id == args.run_id, "CrewAI run/Flow identity changed")
        require(state.completed_sequences == list(range(1, 13)), "CrewAI recovery order")
        require(state.first_post_restart_target == 7, "CrewAI first post-restart target")
        require(len(set(state.synthetic_recommendation_identities)) == 12, "CrewAI duplicate synthetic identity")
        require(all(getattr(state, key) == 0 for key in ("model_generations", "provider_requests", "recommendation_writes", "source_mutations")), "zero-operation boundary")
        write_json(args.output, {
            "schema_version": 1,
            "status": "PASS",
            "framework_origin": "crewai",
            "trial_id": args.trial_id,
            "run_id": args.run_id,
            "flow_id": state.id,
            "persistence": "SQLiteFlowPersistence",
            "public_load_state_used": True,
            "public_kickoff_inputs_id_hydration_used": True,
            "private_restore_used": False,
            "checkpoint_config_used": False,
            "human_feedback_recovery_used": False,
            "loaded_state_sha256": loaded_hash,
            "completed_sequences": state.completed_sequences,
            "first_post_restart_target": 7,
            "replay_count": 0,
            "duplicate_count": 0,
            "model_generations": 0,
            "provider_requests": 0,
            "drupal_operations": 0,
            "machine_recommendation": "APPROVAL_READY",
            "bootstrap_storage": bootstrap_storage,
        })
        return 0
    except Exception as exc:
        reporter.record("worker_failed", error_type=type(exc).__name__)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["prekill", "recover", "diagnose-startup"])
    parser.add_argument("--trial-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--control-dir", required=True, type=Path)
    parser.add_argument("--runtime-db", required=True, type=Path)
    parser.add_argument("--phase-log", required=True, type=Path)
    parser.add_argument("--stack-log", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode in {"recover", "diagnose-startup"}:
        require(args.output is not None, f"{args.mode} output required")
    if args.mode == "diagnose-startup":
        require(args.stack_log is not None, "diagnose-startup stack log required")
    else:
        require(args.stack_log is None, "stack log is diagnostic-only")
    return worker(args)


if __name__ == "__main__":
    raise SystemExit(main())
