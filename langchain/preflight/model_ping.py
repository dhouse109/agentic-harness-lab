from __future__ import annotations

import json
import os

from langchain_openai import ChatOpenAI

TOKEN = "STEP15_LANGCHAIN_OK"
api_key = os.environ.get("OPENAI_API_KEY", "")
model = os.environ.get("OPENAI_CANDIDATE_MODEL", "")
if not api_key:
    raise SystemExit("OPENAI_API_KEY is required")
if not model:
    raise SystemExit("OPENAI_CANDIDATE_MODEL is required")

llm = ChatOpenAI(model=model, api_key=api_key, temperature=0.0)
response = llm.invoke(f"Reply with exactly this token and nothing else: {TOKEN}")
content = response.content
if isinstance(content, list):
    text = json.dumps(content, ensure_ascii=False)
else:
    text = str(content)
if TOKEN not in text:
    raise SystemExit("Candidate model response did not contain the required verification token")
print(json.dumps({
    "canonical_model": model,
    "response_characters": len(text),
    "status": "pass",
    "temperature": 0.0,
    "test_id": "LG-MODEL-001",
    "verification_token_seen": True,
}, sort_keys=True))
