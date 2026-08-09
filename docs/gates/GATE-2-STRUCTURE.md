# Gate 2 — Cross-Framework Implementation and Recovery Milestone

## Decision

Gate 2 preserves the original master-plan meaning: it closes only when the remaining framework implementations are complete and the same controlled failure/recovery comparison has been observed across all three frozen specimens.

- **Gate 2A — LangGraph:** full implementation, SQLite checkpointing, same-run continuation, Drupal human-review continuation, evidence, certification, and freeze.
- **Gate 2B — CrewAI:** equivalent full implementation, framework-owned persistence/continuation, evidence, certification, and freeze.
- **Gate 2C — Shared failure/recovery:** the same process failure after target 6 is fully persisted and before target 7 begins, applied comparably to the frozen Drupal AI, LangGraph, and CrewAI specimens.

**Gate 2 is not complete when Gate 2A or Gate 2B finishes. Gate 2 closes only after Gate 2C.**

## Repository precedence

When documents disagree, use this order:

1. `docs/CURRENT-STATUS.md`
2. frozen contracts and hashes
3. retained evidence
4. latest passing package audit
5. broader planning documents

Do not silently reconcile a conflict. Stop at the relevant decision boundary.

## Umbrella exit criteria

Gate 2 closes only when:

1. Gate 1 Drupal AI remains frozen and auditable.
2. Gate 2A LangGraph is certified and frozen.
3. Gate 2B CrewAI is certified and frozen.
4. Gate 2C applies the same defined failure at the target-6/7 seam to all three frozen implementations.
5. Recovery evidence is retained without forcing any framework to match a proposal prediction.
6. `CLAIMS_REGISTER.md` and `COMPARISON_MATRIX.md` contain only evidence-supported cross-framework conclusions.
7. Source Articles remain unchanged throughout the comparative experiment.

## Interpretation guardrail

A controlled continuation inside Gate 2A or Gate 2B proves only that implementation's continuation mechanism. It must not be labeled as the shared Gate 2C recovery comparison.
