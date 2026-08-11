# Comparison Matrix

**Status:** Drupal AI and LangGraph evidence populated; CrewAI remains unobserved. Do not infer cross-framework conclusions.

Use one row per framework and organ. Every conclusion must link to a claim ID and retained evidence.

| Organ | Framework | Implementation mechanism | Local test ID | Evidence path | Observation status | Safe conclusion |
|---|---|---|---|---|---|---|
| Context | Drupal AI | Drupal entity/page facts + verified image File entity passed to the pinned AI Agent task | Gate 1 certification | `evidence/gates/gate-1/certification/gate1-step07-20260809T012559Z-2229836` | observed | Drupal AI assembled the permitted content/image context for the frozen 12 targets in this pinned lab. |
| Context | LangChain / LangGraph | Fresh shared Drupal context immediately before the model and pre-submit validation; raw Article/image material remains node-local while sanitized hashes/lengths are retained | Steps 2A.05 / 2A.08 | `evidence/gates/gate-2a/canonical-slice/gate2a-step05-20260810T140133Z-0025b888`; `evidence/results/langgraph/langgraph-20260810T231915Z-0027cd3e` | observed | CLM-LG-008 — Fresh permitted context was used without retaining raw Article bodies/image data URLs in checkpoint/evidence state; the privacy-salvage lineage remains explicit. |
| Context | CrewAI | TODO | TODO | TODO | not observed | Do not use yet |
| Tools | Drupal AI | Four FunctionCall adapters delegate to the certified shared Drupal services; model call itself exposes zero callable tools | Gate 1 certification | `evidence/gates/gate-1/certification/gate1-step07-20260809T012559Z-2229836` | observed | Drupal AI used thin framework-native adapters around the frozen shared substrate without a private write path. |
| Tools | LangChain / LangGraph | Four LangChain-native `@tool` wrappers delegate one-to-one to the frozen shared Drupal client operations | Step 2A.03 + compliance verification | `evidence/gates/gate-2a/tool-adapters/gate2a-step03-20260809T233127Z-2375581`; `evidence/gates/gate-2a/tool-adapters/gate2a-step03-verification-20260810T020210Z-2410520` | observed | CLM-LG-004 — Thin framework-native adapters exercised the shared semantic boundary without a private write path. |
| Tools | CrewAI | TODO | TODO | TODO | not observed | Do not use yet |
| State and memory | Drupal AI | Drupal key/value collection `agentic_harness_drupal_ai.run_state` + sanitized artifacts | Gate 1 certification | `evidence/gates/gate-1/certification/gate1-step07-20260809T012559Z-2229836` | observed | Framework-owned state records completed targets, recommendation identities, and the next index. |
| State and memory | LangChain / LangGraph | `StateGraph` + `SqliteSaver`; per-run SQLite DB; `run_id` as configurable `thread_id`; schema-bounded run state | Step 2A.04 | `evidence/gates/gate-2a/checkpoint-proof/gate2a-step04-20260810T034027Z-00250b07` | observed | CLM-LG-002 — A second process reloaded the same persisted run/thread state exactly, while a distinct thread inherited no state. |
| State and memory | CrewAI | TODO | TODO | TODO | not observed | Do not use yet |
| Verification | Drupal AI | Strict structured output + shared deterministic validator + idempotent submit/status checks | Gate 1 certification | `evidence/gates/gate-1/certification/gate1-step07-20260809T012559Z-2229836` | observed | All 12 fresh outputs passed the frozen schema/validator and model-free replay produced zero duplicate identities. |
| Verification | LangChain / LangGraph | Strict structured model output + frozen recommendation schema + shared deterministic validator + submit/status checks; automatic model retries disabled | Steps 2A.05 / 2A.08 | `evidence/gates/gate-2a/canonical-slice/gate2a-step05-20260810T140133Z-0025b888`; `evidence/results/langgraph/langgraph-20260810T231915Z-0027cd3e` | observed | CLM-LG-007 — The accepted batch validated before submit and completed 12/12 successful model calls with zero automatic retries and no semantic retry loop. |
| Verification | CrewAI | TODO | TODO | TODO | not observed | Do not use yet |
| Human review | Drupal AI | Revision-enabled `alt_text_suggestion` queue with real `editor_dana` decisions | Step 1.06 lineage | `evidence/gates/gate-1/batch-evidence/gate1-step06-20260808T231216Z-2188911` | observed | Approve, reject, and edit-then-approve were retained as real Drupal revision lineage; generated recommendations were not auto-applied. |
| Human review | LangChain / LangGraph | Persisted `interrupt()` around the authoritative Drupal `alt_text_suggestion` queue; same thread resumes with `Command(resume=...)` after `editor_dana` review | Step 2A.06 | `evidence/gates/gate-2a/human-interrupt/gate2a-step06-20260810T162448Z-002692eb` | observed | CLM-LG-005 — A real Drupal edit-and-approve revision was observed after a genuine LangGraph interrupt, then the same run/thread resumed to read the reviewed status. |
| Human review | CrewAI | TODO | TODO | TODO | not observed | Do not use yet |
| Lifecycle and recovery | Drupal AI | Persist-after-target state; controlled sequence-6/7 continuation in the same run | Gate 1 certification | `evidence/gates/gate-1/certification/gate1-step07-20260809T012559Z-2229836` | observed | Same-run continuation from sequence 7 was observed without duplicate recommendations; the later shared process-failure recovery comparison remains open. |
| Lifecycle and recovery | LangChain / LangGraph | Target 6 fully checkpointed → genuine interrupt → human inspection → same run/thread resumes at target 7; no duplicate recommendation identities | Step 2A.08 | `evidence/results/langgraph/langgraph-20260810T231915Z-0027cd3e` | observed | CLM-LG-006 — Controlled same-run continuation completed all 12 targets without reprocessing 1–6; later Gate 2C process-failure recovery remains open. |
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
