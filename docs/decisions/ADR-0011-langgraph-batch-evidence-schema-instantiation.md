# ADR-0011 — LangGraph batch evidence schema instantiation

- **Status:** accepted for Gate 2A Step 2A.07
- **Date:** 2026-08-10
- **Scope:** evidence-schema compatibility; frozen Gate 0.5, Gate 1, and Gate 2A artifacts remain unchanged

## Context

The frozen Gate 2A contract fixes LangGraph provenance to `source_framework=langgraph`, uses
`langgraph-...` run IDs, names `langgraph-model-output.schema.json` as the raw structured model-output
schema, and explicitly separates its target-6/7 **controlled same-run continuation** from the later
Gate 2C shared process-failure/recovery comparison.

The same contract names the pre-existing Gate 1 `batch-*.schema.json` collection schemas as lifecycle
collection shapes. Those files are immutable Gate 1 artifacts. Most hard-code Drupal-AI provenance.
Two also carry Gate 1 failure-only vocabulary:

- `batch-event.schema.json` has `failure_injected` but no controlled-continuation event type;
- `batch-recovery.schema.json` requires `failure_after_sequence`, `failure_before_sequence`, and
  `completed_before_failure`.

Literal use would either falsify LangGraph provenance or incorrectly describe the Gate 2A controlled
stop as a Gate 2C-style failure.

## Decision

Do not modify the frozen Gate 2A contract and do not modify any Gate 1 `batch-*.schema.json` file.
Step 2A.07 reproducibly instantiates `shared/schemas/langgraph-batch-*.schema.json` and records every
source/derived hash and transformation class in
`shared/contracts/GATE2A-LANGGRAPH-EVIDENCE-SCHEMA-MAP.json`.

### Provenance-only transformations

For schemas that are semantically portable:

1. `$id` `batch-*.schema.json` becomes `langgraph-batch-*.schema.json`;
2. exact provenance constant `drupal_ai` becomes `langgraph`;
3. run-ID regex prefix `^drupal_ai-` becomes `^langgraph-`;
4. `drupal-ai-model-output.schema.json` becomes `langgraph-model-output.schema.json`;
5. `drupal-ai-run-state.schema.json` becomes `langgraph-run-state.schema.json` if encountered;
6. human-readable title text may replace `Drupal AI` with `LangGraph`.

### Controlled-continuation adaptations

Two schemas require a narrow semantic adaptation to obey the *already frozen* Gate 2A continuation
policy rather than importing Gate 1 failure semantics:

- `langgraph-batch-event.schema.json` adds `continuation_interrupted` while retaining the historical
  `failure_injected` event for lineage/comparison compatibility;
- `langgraph-batch-recovery.schema.json` keeps the frozen `recovery.json` lifecycle slot but validates
  a controlled stop/resume projection: stop after 6, resume at 7, same run ID, duplicate count 0, and
  `gate2c_failure_injection_fired=false`.

This is a schema **instantiation/interpretation**, not a change to the frozen Gate 2A contract. The
mapping explicitly records which files are provenance-only and which contain the controlled-
continuation adaptation.

## Invalidated-evidence review

No accepted Step 2A.01–2A.06 evidence is invalidated. Those steps do not claim a completed 12-target
LangGraph batch collection validated against the Gate 1 batch collection schemas. The frozen target
sequence, shared operations, model/settings, validator, review destination, state schema,
source-mutation prohibition, and target-6/7 seam are unchanged.

The first live batch dependent on these instantiated collection schemas is Step 2A.08.

## Consequences

- Gate 1 frozen artifacts remain byte-for-byte unchanged.
- The Gate 2A frozen contract digest remains unchanged.
- LangGraph evidence retains truthful `langgraph` provenance.
- Step 2A.07/2A.08 do not mislabel the controlled continuation as Gate 2C failure injection.
- `events.jsonl` can represent `continuation_interrupted` and is schema-validated.
- `recovery.json` records the controlled stop/resume without failure-only field names.
- Any additional transformation requires a new ADR and invalidated-evidence review.
