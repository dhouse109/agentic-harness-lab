from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from sqlite_graph import build_graph

THREAD_ID = "phase0-step15-fixed-thread"
root = Path(__file__).resolve().parents[1]
db_path = root / ".preflight-state" / "checkpoints.sqlite"
db_path.parent.mkdir(parents=True, exist_ok=True)
config = {"configurable": {"thread_id": THREAD_ID}}

with SqliteSaver.from_conn_string(str(db_path)) as checkpointer:
    graph = build_graph(checkpointer)
    result = graph.invoke({"counter": 0, "trace": []}, config)
    snapshot = graph.get_state(config)

expected = {"counter": 1, "trace": ["persist_one_step"]}
if result != expected or snapshot.values != expected:
    raise SystemExit(f"Unexpected persisted state: result={result!r} snapshot={snapshot.values!r}")
if not db_path.is_file() or db_path.stat().st_size == 0:
    raise SystemExit("SQLite checkpoint database was not created")

digest = hashlib.sha256(db_path.read_bytes()).hexdigest()
print(json.dumps({
    "test_id": "LG-SQLITE-001",
    "db_relative_path": ".preflight-state/checkpoints.sqlite",
    "db_sha256_after_write": digest,
    "state": expected,
    "status": "pass",
    "strict_msgpack": os.environ.get("LANGGRAPH_STRICT_MSGPACK") == "true",
    "thread_id": THREAD_ID,
}, sort_keys=True))
