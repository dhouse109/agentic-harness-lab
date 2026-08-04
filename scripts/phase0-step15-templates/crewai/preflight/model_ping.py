from __future__ import annotations

import json
import os

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from crewai import LLM

TOKEN = "STEP15_CREWAI_OK"
api_key = os.environ.get("OPENAI_API_KEY", "")
canonical_model = os.environ.get("OPENAI_CANDIDATE_MODEL", "")
adapter_model = os.environ.get("CREWAI_CANDIDATE_MODEL", canonical_model)
if not api_key:
    raise SystemExit("OPENAI_API_KEY is required")
if not canonical_model:
    raise SystemExit("OPENAI_CANDIDATE_MODEL is required")

normalized_adapter = adapter_model.removeprefix("openai/")
if normalized_adapter != canonical_model:
    raise SystemExit(
        "CREWAI_CANDIDATE_MODEL must identify the same underlying model as OPENAI_CANDIDATE_MODEL"
    )

llm = LLM(model=adapter_model, temperature=0.0)
response = llm.call(messages=[
    {"role": "user", "content": f"Reply with exactly this token and nothing else: {TOKEN}"},
])
text = str(response)
if TOKEN not in text:
    raise SystemExit("Candidate model response did not contain the required verification token")
print(json.dumps({
    "adapter_model": adapter_model,
    "canonical_model": canonical_model,
    "response_characters": len(text),
    "status": "pass",
    "temperature": 0.0,
    "test_id": "CR-MODEL-001",
    "verification_token_seen": True,
}, sort_keys=True))
