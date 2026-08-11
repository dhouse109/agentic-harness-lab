# Gate 2A → CrewAI Handoff

Gate 2A LangGraph is certified and frozen at SHA-256 `a28361c34b9d1c2089eee786324ad34cffbf54e3495f59a276c489865e5630f0` using accepted batch `evidence/results/langgraph/langgraph-20260810T231915Z-0027cd3e`.

## Constants CrewAI must preserve

- Dataset: 20 Articles / 12 frozen targets
- Target sequence SHA-256: `1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728`
- Provider/model: OpenAI `gpt-4.1-mini-2025-04-14`, temperature `0.0`
- Shared semantic operations and deterministic validator remain unchanged
- Review destination: `alt_text_suggestion`; authoritative reviewer remains `editor_dana`
- Source mutation and automatic publication remain prohibited
- Shared comparison failure point remains after target 6 is fully persisted and before target 7 begins
- CrewAI must own its own orchestration/persistence state; do not centralize framework runtime state in `shared/`

## LangGraph evidence available for later comparison

- Four thin LangChain-native tool adapters exercised the shared semantic boundary.
- SQLite checkpoint state reloaded across a process boundary with thread isolation.
- Strict structured output and the shared deterministic validator preceded submission.
- A genuine LangGraph interrupt resumed the same run/thread after authoritative Drupal `editor_dana` review.
- The accepted 12-target batch crossed the controlled target-6/7 seam with 12 unique recommendations and no reprocessing of targets 1–6.
- Privacy evidence preserves the original Step 2A.08 self-match failure and separate model-free salvage disposition.

The controlled LangGraph continuation is not the shared Gate 2C process-failure/recovery result.

**Do not infer CrewAI behavior from LangGraph evidence.** Build and observe the CrewAI specimen independently.

## Next package

`gate-2b-step01-crewai-contract-and-evidence-plan-v1.0.0`

Gate 2B Step 2B.01 remains locked until Step 2A.10 is committed, merged, local `main` is resynchronized, and the post-merge audit passes.
