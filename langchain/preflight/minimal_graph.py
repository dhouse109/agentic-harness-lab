from __future__ import annotations

import json
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class GraphState(TypedDict):
    value: int
    trace: list[str]


def increment(state: GraphState) -> GraphState:
    return {"value": state["value"] + 1, "trace": [*state["trace"], "increment"]}


def double(state: GraphState) -> GraphState:
    return {"value": state["value"] * 2, "trace": [*state["trace"], "double"]}


builder = StateGraph(GraphState)
builder.add_node("increment", increment)
builder.add_node("double", double)
builder.add_edge(START, "increment")
builder.add_edge("increment", "double")
builder.add_edge("double", END)
graph = builder.compile()
result = graph.invoke({"value": 1, "trace": []})
expected = {"value": 4, "trace": ["increment", "double"]}
if result != expected:
    raise SystemExit(f"Unexpected graph result: {result!r}")
print(json.dumps({"test_id": "LG-GRAPH-001", "result": result, "status": "pass"}, sort_keys=True))
