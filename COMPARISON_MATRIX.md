# Comparison Matrix

**Status:** Drupal AI Gate 1 evidence populated; LangGraph and CrewAI remain unobserved. Do not infer cross-framework conclusions.

Use one row per framework and organ. Every conclusion must link to a claim ID and retained evidence.

| Organ | Framework | Implementation mechanism | Local test ID | Evidence path | Observation status | Safe conclusion |
|---|---|---|---|---|---|---|
| Context | Drupal AI | Drupal entity/page facts + verified image File entity passed to the pinned AI Agent task | Gate 1 certification | `evidence/gates/gate-1/certification/gate1-step07-20260809T012559Z-2229836` | observed | Drupal AI assembled the permitted content/image context for the frozen 12 targets in this pinned lab. |
| Context | LangChain / LangGraph | TODO | TODO | TODO | not observed | Do not use yet |
| Context | CrewAI | TODO | TODO | TODO | not observed | Do not use yet |
| Tools | Drupal AI | Four FunctionCall adapters delegate to the certified shared Drupal services; model call itself exposes zero callable tools | Gate 1 certification | `evidence/gates/gate-1/certification/gate1-step07-20260809T012559Z-2229836` | observed | Drupal AI used thin framework-native adapters around the frozen shared substrate without a private write path. |
| Tools | LangChain / LangGraph | TODO | TODO | TODO | not observed | Do not use yet |
| Tools | CrewAI | TODO | TODO | TODO | not observed | Do not use yet |
| State and memory | Drupal AI | Drupal key/value collection `agentic_harness_drupal_ai.run_state` + sanitized artifacts | Gate 1 certification | `evidence/gates/gate-1/certification/gate1-step07-20260809T012559Z-2229836` | observed | Framework-owned state records completed targets, recommendation identities, and the next index. |
| State and memory | LangChain / LangGraph | TODO | TODO | TODO | not observed | Do not use yet |
| State and memory | CrewAI | TODO | TODO | TODO | not observed | Do not use yet |
| Verification | Drupal AI | Strict structured output + shared deterministic validator + idempotent submit/status checks | Gate 1 certification | `evidence/gates/gate-1/certification/gate1-step07-20260809T012559Z-2229836` | observed | All 12 fresh outputs passed the frozen schema/validator and model-free replay produced zero duplicate identities. |
| Verification | LangChain / LangGraph | TODO | TODO | TODO | not observed | Do not use yet |
| Verification | CrewAI | TODO | TODO | TODO | not observed | Do not use yet |
| Human review | Drupal AI | Revision-enabled `alt_text_suggestion` queue with real `editor_dana` decisions | Step 1.06 lineage | `evidence/gates/gate-1/batch-evidence/gate1-step06-20260808T231216Z-2188911` | observed | Approve, reject, and edit-then-approve were retained as real Drupal revision lineage; generated recommendations were not auto-applied. |
| Human review | LangChain / LangGraph | TODO | TODO | TODO | not observed | Do not use yet |
| Human review | CrewAI | TODO | TODO | TODO | not observed | Do not use yet |
| Lifecycle and recovery | Drupal AI | Persist-after-target state; controlled sequence-6/7 continuation in the same run | Gate 1 certification | `evidence/gates/gate-1/certification/gate1-step07-20260809T012559Z-2229836` | observed | Same-run continuation from sequence 7 was observed without duplicate recommendations; the later shared process-failure recovery comparison remains open. |
| Lifecycle and recovery | LangChain / LangGraph | TODO | TODO | TODO | not observed | Do not use yet |
| Lifecycle and recovery | CrewAI | TODO | TODO | TODO | not observed | Do not use yet |

## Cross-framework controls

| Control | Frozen value or evidence |
|---|---|
| Shared task | Frozen in `EXPERIMENT_SPEC.md` version 1.1 |
| Dataset | 20 Articles / 12 deterministic target usages |
| Reset | `seeded-clean` before each comparison run |
| Model and settings | OpenAI `gpt-4.1-mini-2025-04-14`, temperature `0.0`; frozen by Step 16 and ADR-0002 |
| Output schema | `shared/schemas/recommendation.schema.json` |
| Validators | `gate05-validator-1.0.0`; frozen shared deterministic validation semantics |
| Review destination | Drupal `alt_text_suggestion` queue |
| Failure trigger | After target 6 is fully persisted and before target 7 begins |
