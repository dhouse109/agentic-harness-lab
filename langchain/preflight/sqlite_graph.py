from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class PersistentState(TypedDict):
    counter: int
    trace: list[str]


def persist_one_step(state: PersistentState) -> PersistentState:
    return {"counter": state["counter"] + 1, "trace": [*state["trace"], "persist_one_step"]}


def build_graph(checkpointer):
    builder = StateGraph(PersistentState)
    builder.add_node("persist_one_step", persist_one_step)
    builder.add_edge(START, "persist_one_step")
    builder.add_edge("persist_one_step", END)
    return builder.compile(checkpointer=checkpointer)
