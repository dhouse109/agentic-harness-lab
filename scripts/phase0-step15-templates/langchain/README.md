# LangChain / LangGraph preflight

This is an isolated Python 3.12 `uv` project for Phase 0 Step 15 environment verification.
It is not an agent implementation.

The preflight proves:

- required packages import
- a deterministic two-node LangGraph graph runs without a model
- SQLite checkpoint state can be written by one process and loaded by another
- the candidate OpenAI model can answer through `langchain-openai`

Runtime-only files under `.venv/` and `.preflight-state/` are not committed.
