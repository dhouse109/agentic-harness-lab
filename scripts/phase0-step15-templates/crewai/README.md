# CrewAI preflight

This is an isolated Python 3.12 `uv` project for Phase 0 Step 15 environment verification.
It is not an agent implementation.

The preflight proves:

- required packages import
- a deterministic two-step CrewAI Flow runs without a model
- the candidate OpenAI model can answer through CrewAI's LLM provider path

Runtime-only files under `.venv/` and `.preflight-state/` are not committed.
