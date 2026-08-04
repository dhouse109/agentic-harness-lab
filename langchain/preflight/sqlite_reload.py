from __future__ import annotations

import hashlib
import json
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from sqlite_graph import build_graph

THREAD_ID = "phase0-step15-fixed-thread"
root = Path(__file__).resolve().parents[1]
db_path = root / ".preflight-state" / "checkpoints.sqlite"
if not db_path.is_file():
    raise SystemExit("SQLite checkpoint database is missing")
config = {"configurable": {"thread_id": THREAD_ID}}

with SqliteSaver.from_conn_string(str(db_path)) as checkpointer:
    graph = build_graph(checkpointer)
    snapshot = graph.get_state(config)

expected = {"counter": 1, "trace": ["persist_one_step"]}
if snapshot.values != expected:
    raise SystemExit(f"Second process did not reload expected state: {snapshot.values!r}")

digest = hashlib.sha256(db_path.read_bytes()).hexdigest()
print(json.dumps({
    "test_id": "LG-SQLITE-002",
    "db_relative_path": ".preflight-state/checkpoints.sqlite",
    "db_sha256_on_reload": digest,
    "reloaded_state": expected,
    "status": "pass",
    "thread_id": THREAD_ID,
}, sort_keys=True))
