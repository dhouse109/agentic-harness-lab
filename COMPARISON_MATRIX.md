# Comparison Matrix

**Status:** empty evidence matrix — do not fill from expectations alone.

Use one row per framework and organ. Every conclusion must link to a claim ID and retained evidence.

| Organ | Framework | Implementation mechanism | Local test ID | Evidence path | Observation status | Safe conclusion |
|---|---|---|---|---|---|---|
| Context | Drupal AI | TODO | TODO | TODO | not observed | Do not use yet |
| Context | LangChain / LangGraph | TODO | TODO | TODO | not observed | Do not use yet |
| Context | CrewAI | TODO | TODO | TODO | not observed | Do not use yet |
| Tools | Drupal AI | TODO | TODO | TODO | not observed | Do not use yet |
| Tools | LangChain / LangGraph | TODO | TODO | TODO | not observed | Do not use yet |
| Tools | CrewAI | TODO | TODO | TODO | not observed | Do not use yet |
| State and memory | Drupal AI | TODO | TODO | TODO | not observed | Do not use yet |
| State and memory | LangChain / LangGraph | TODO | TODO | TODO | not observed | Do not use yet |
| State and memory | CrewAI | TODO | TODO | TODO | not observed | Do not use yet |
| Verification | Drupal AI | TODO | TODO | TODO | not observed | Do not use yet |
| Verification | LangChain / LangGraph | TODO | TODO | TODO | not observed | Do not use yet |
| Verification | CrewAI | TODO | TODO | TODO | not observed | Do not use yet |
| Human review | Drupal AI | TODO | TODO | TODO | not observed | Do not use yet |
| Human review | LangChain / LangGraph | TODO | TODO | TODO | not observed | Do not use yet |
| Human review | CrewAI | TODO | TODO | TODO | not observed | Do not use yet |
| Lifecycle and recovery | Drupal AI | TODO | TODO | TODO | not observed | Do not use yet |
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
