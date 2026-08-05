# Gate 0.5 Framework Implementation Handoff

## Status at handoff

Gate 0.5 is complete. The common Drupal substrate is certified and frozen for framework-owned
implementation work.

The handoff itself does not claim that any framework behavior has been executed or certified:

```text
Drupal AI   — not certified by substrate preflight
LangGraph   — not certified by substrate preflight
CrewAI      — not certified by substrate preflight
```

These are proof-boundary statements, not open Gate 0.5 checklist items. Drupal AI implementation
begins next in Gate 1; LangGraph and CrewAI follow in subsequent implementation phases.

## Frozen constants

| Constant | Value |
|---|---|
| Provider | OpenAI |
| Model | `gpt-4.1-mini-2025-04-14` |
| Temperature | `0.0` |
| Target | Canonical target sequence 1 |
| Review destination | Drupal `alt_text_suggestion` queue |
| Reviewer | `editor_dana` |
| Validator | `gate05-validator-1.0.0` |
| Source mutation | Prohibited |
| Comparative origins | `drupal_ai`, `langgraph`, `crewai` |

The generated freeze manifest is the machine-readable source of truth:

```text
shared/contracts/GATE05-SUBSTRATE-FREEZE.json
```

## Shared operation sequence

Each framework implementation independently performs:

```text
find_images_needing_review()
  → select canonical target 1
get_image_context(target)
  → framework-owned model call and structured output
  → framework-owned orchestration/state
submit_recommendation(recommendation)
get_recommendation_status(recommendation_id)
```

The framework must not bypass the shared Drupal operations with a private write path.

## Shared substrate owns

- HTTP transport and Basic Auth as `agent_bot`
- exact target and context contracts
- permission checks and stale-target rejection
- deterministic recommendation validators
- idempotent recommendation creation
- Drupal review queue and revisions
- read-only status projection
- seed/reset and sanitized evidence conventions

## Each framework owns

- context assembly around the returned facts
- actual model invocation
- framework-native structured output
- prompt orchestration
- tool selection and binding
- state and memory
- checkpointing
- human-interrupt behavior
- recovery logic
- workflow sequencing

Moving one of these into a common helper would erase part of the comparison.

## Required evidence for each framework implementation

Retain, without credentials, raw Base64, or chain of thought:

1. framework and exact package versions
2. real framework origin and matching run ID
3. frozen model ID and temperature
4. canonical target identity
5. permitted context evidence hash and image SHA-256
6. exact prompt or orchestration version
7. schema-conforming structured model output
8. deterministic validator result
9. recommendation node ID, UUID, and pending revision
10. idempotent replay result
11. source Article before/after hash
12. one `editor_dana` decision and revision evidence
13. final seeded-clean reset
14. explicit list of framework-owned behavior exercised

## Fairness guardrails

- Use the same target, facts, model, settings, output schema, validators, review destination, and
  failure point.
- Framework-specific orchestration wording may differ only where the framework API requires it.
- Record those differences instead of hiding them.
- Do not add richer context, retries, thresholds, or hidden tools to one implementation.
- Do not present the controlled substrate preflight as a framework result.

## Implementation order after Gate 0.5

1. Gate 1 — Drupal AI full implementation, progressing from the canonical target to the 12-target
   batch.
2. LangGraph full implementation.
3. CrewAI full implementation.
4. Shared failure and recovery comparison.

The next package is:

```text
gate-1-step01-drupal-ai-batch-contract-v1.0.0
```
