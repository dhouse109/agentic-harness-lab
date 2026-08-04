from __future__ import annotations

import importlib.metadata
import json

import langchain
import langchain_openai
import langgraph
from langgraph.checkpoint.sqlite import SqliteSaver

packages = {
    name: importlib.metadata.version(name)
    for name in (
        "langchain",
        "langchain-openai",
        "langgraph",
        "langgraph-checkpoint-sqlite",
    )
}
assert SqliteSaver is not None
print(json.dumps({"test_id": "PY-LG-002", "packages": packages, "status": "pass"}, sort_keys=True))
