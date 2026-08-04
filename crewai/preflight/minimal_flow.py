from __future__ import annotations

import json
import os

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from crewai.flow import Flow, listen, start
from pydantic import BaseModel, Field


class PreflightState(BaseModel):
    value: int = 0
    trace: list[str] = Field(default_factory=list)


class MinimalFlow(Flow[PreflightState]):
    @start()
    def first(self) -> int:
        self.state.value = 1
        self.state.trace.append("first")
        return self.state.value

    @listen(first)
    def second(self, value: int) -> dict[str, object]:
        self.state.value = value + 1
        self.state.trace.append("second")
        return {"value": self.state.value, "trace": list(self.state.trace)}


flow = MinimalFlow()
result = flow.kickoff()
expected = {"value": 2, "trace": ["first", "second"]}
if result != expected:
    raise SystemExit(f"Unexpected Flow result: {result!r}")
print(json.dumps({"test_id": "CR-FLOW-001", "result": result, "status": "pass"}, sort_keys=True))
