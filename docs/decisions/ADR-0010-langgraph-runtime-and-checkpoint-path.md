# ADR-0010: LangGraph runtime and checkpoint path

- **Status:** Accepted
- **Decision date:** 2026-08-09
- **Decision owner:** Program lead
- **Evidence:** `evidence/gates/gate-2a/runtime-probe/gate2a-step02-20260809T224238Z-2361786`

## Context

Gate 2A Step 2A.01 intentionally deferred the exact pinned LangGraph runtime/checkpoint API and runtime path to Step 2A.02. This ADR records only model-free observations from the installed locked environment.

## Decision

Use:

- graph runtime: `langgraph.graph.StateGraph`;
- deterministic graph routing for workflow/write decisions;
- checkpointer: `langgraph.checkpoint.sqlite.SqliteSaver`;
- runtime root: `langchain/.gate2a-runtime/`;
- per-run SQLite path: `langchain/.gate2a-runtime/<run-id>.sqlite`;
- stable Gate 2A `run_id` as `configurable.thread_id`;
- checkpoint namespace observed by the probe: empty string (`""`);
- interrupt: `langgraph.types.interrupt`;
- resume: `graph.invoke(langgraph.types.Command(resume=<value>), same thread config)`;
- structured output: `ChatOpenAI.with_structured_output(..., strict=True)`;
- image input representation: `HumanMessage content block type=image_url; image bytes remain ephemeral`;
- transport retry policy: explicit `max_retries=0` (supported: `True`);
- thin LangChain-native tool wrappers invoked by deterministic graph nodes.

Runtime/checkpoint state remains framework-owned under `langchain/.gate2a-runtime/` and must not contain raw image bytes/data URLs, credentials, hidden reasoning, or shared Drupal runtime state.

## Boundaries

This decision makes no model call and no Drupal mutation. It does not prove live tool behavior, live model behavior, or Gate 2C recovery. Step 2A.04 remains the stronger persistence/isolation proof.

## Consequences

Step 2A.03 may implement thin shared-operation wrappers without changing the frozen substrate. A future need for dependency upgrades or undocumented framework patches is a stop condition and requires planning review rather than silent version drift.
