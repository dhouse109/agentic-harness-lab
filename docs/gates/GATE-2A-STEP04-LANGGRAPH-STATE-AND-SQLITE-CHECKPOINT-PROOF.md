# Gate 2A Step 2A.04 — LangGraph State and SQLite Checkpoint Proof

**Package:** `gate-2a-step04-langgraph-state-and-sqlite-checkpoint-proof-v1.0.6`

## Purpose

Prove the LangGraph framework-owned state/checkpoint design through a real
cross-process SQLite persistence and isolation observation, without model
execution or Drupal access.

Step 2A.02 established that the pinned runtime supports `StateGraph`,
`SqliteSaver`, stable `thread_id`, and reload. Step 2A.04 is the stronger proof:
it exercises the frozen LangGraph run-state shape, deterministic target progress,
a real process boundary, and a negative-control thread.

## Frozen runtime path

Per ADR-0010:

- graph: `langgraph.graph.StateGraph`;
- checkpointer: `langgraph.checkpoint.sqlite.SqliteSaver`;
- runtime root: `langchain/.gate2a-runtime/`;
- per-run DB: `langchain/.gate2a-runtime/<run-id>.sqlite`;
- stable identity: Gate 2A `run_id` as `configurable.thread_id`;
- checkpoint namespace: observed empty string (`""`).

Runtime DB files are gitignored and are evidence sources, not Git artifacts.

## State contract

The persisted object must validate against
`shared/schemas/langgraph-run-state.schema.json`.

The optional frozen-schema properties `checkpoint_id` and `checkpoint_namespace` are not LangGraph StateGraph channels. LangGraph reserves checkpoint metadata names for its own checkpoint/configuration machinery; Step 2A.04 records observed checkpoint metadata separately in `checkpoint-config.json`.

The proof retains the schema-required lifecycle/state fields, including:

- `run_id`, `thread_id`, `framework_origin`, `checkpoint_backend`;
- frozen `target_sequence_hash`;
- `next_target_index`;
- `completed_target_identities`;
- `recommendation_ids`;
- `validation_results`;
- lifecycle timestamps;
- `continuation_boundary_armed`;
- `continuation_boundary_reached`;
- `gate2c_failure_injection_fired`;
- frozen `prompt_version`;
- frozen `model_id`.

For this proof:

- recommendation IDs remain empty;
- validation results remain empty;
- continuation boundary flags remain false;
- Gate 2C failure injection remains false.

## Read-only target identity input

Step 2A.04 reads the accepted Step 2A.03 retained target list:

`evidence/gates/gate-2a/tool-adapters/gate2a-step03-20260809T233127Z-2375581/targets.json`

This is read-only retained evidence. No Drupal route is called.

## Proof sequence

1. process 1 creates one run state with the frozen run/thread identity;
2. a deterministic model-free graph advances canonical target identities 1–3;
3. LangGraph checkpoints the resulting state into the per-run SQLite DB;
4. process 1 exits;
5. process 2 opens a new interpreter and the same DB;
6. process 2 reloads the same run/thread state and compares it exactly;
7. process 2 queries a distinct negative-control thread ID and observes no inherited state;
8. both retained state snapshots validate against the frozen Draft 2020-12 schema;
9. the SQLite/state privacy audit finds no credential, auth-header, raw-image/data-URL,
   hidden-reasoning, Article-body, or shared-runtime-storage material.

## Evidence

Accepted proof evidence is retained under:

`evidence/gates/gate-2a/checkpoint-proof/<run-id>/`

Required retained files:

- `run-id.txt`
- `checkpoint-config.json`
- `process-1-events.jsonl`
- `process-2-events.jsonl`
- `state-before.json`
- `state-after-reload.json`
- `isolation-negative-control.json`
- `persisted-field-audit.json`
- `state-before-schema-validation.json`
- `state-after-reload-schema-validation.json`
- `runtime-db-sha256.txt`
- `secret-scan.log`
- `summary.json`
- `summary.md`
- `package-files-sha256.txt`

## Attempt #3 bookkeeping repair

The retained attempt `evidence/gates/gate-2a/checkpoint-proof/gate2a-step04-20260810T034027Z-00250b07` completed the model-free LangGraph checkpoint
mechanics and produced a PASS `summary.json`, but the wrapper stopped during the
post-proof audit because the auditor's required-file set omitted `run-id.txt`
even though the finalizer correctly included that file in
`package-files-sha256.txt`.

The runner then retained `run-failure.txt`. v1.0.6 preserves that wrapper-failure
history, records the repair in `bookkeeping-repair.json`, makes the evidence
manifest exhaustive, and allows the already-produced attempt to be certified
without executing LangGraph again.

## Pass criteria

Step 2A.04 passes only when:

- the real SQLite DB is under the gitignored LangGraph runtime root;
- process 2 is a new Python process;
- same `run_id/thread_id` reloads state identical to the process-1 retained state;
- `next_target_index == 3`;
- completed target sequences are exactly `[1, 2, 3]`;
- a different thread has empty state;
- both state snapshots validate against the frozen LangGraph run-state schema;
- persisted state contains only allowed schema fields;
- no prohibited privacy/security material is retained;
- no model/provider call occurs;
- no Drupal call or mutation occurs;
- Gate 0.5, Gate 1, and Gate 2A frozen digests remain unchanged.

A passing Step 2A.04 proves only framework-owned state persistence/reload and
thread isolation. It does not prove real model output, recommendation submission,
human review, batch continuation, Gate 2C failure/recovery, framework superiority,
or production readiness.

**Next package after merge/post-merge audit:**

`gate-2a-step05-langgraph-canonical-vertical-slice-v1.0.0`
