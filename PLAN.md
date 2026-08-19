# Implementation Plan

## Current status

> Phase 0, Gate 0.5, and Gate 1 are complete. Drupal AI is certified and frozen; LangGraph implementation is next.

See `docs/CURRENT-STATUS.md` for the authoritative fresh-session status snapshot and reading order.

## Governing program milestone

> One image, one recommendation, one human decision, three implementations.

This remains the comparative program objective. Under the current execution plan, Gate 0.5 exits
when the framework-neutral shared substrate is certified and frozen. Framework-specific execution
begins after that handoff, starting with Drupal AI in Gate 1.

The completed substrate does not prove framework-specific recovery or production readiness.

## Phase 0 status

- [x] Drupal roles and service accounts established and audited.
- [x] Revision-enabled recommendation type and review queue established.
- [x] Deterministic 20-Article fixture with 12 target usages established.
- [x] `seeded-clean` database and generated-file reset proven.
- [x] Positive and negative permission suite retained.
- [x] Approve, reject, and edit-and-approve revision evidence retained.
- [x] Step 13 repository and evidence scaffold audited.
- [x] Step 14 experiment specification written and frozen.
- [x] Step 15 separate LangChain/LangGraph and CrewAI environments pass preflight.
- [x] Step 16 image-plus-page-context capability passes or a fallback is recorded.
- [x] Step 17 non-AI `find_images_needing_review()` returns exactly 12 targets.

**Phase 0 status:** complete.

## Gate 0.5 — shared substrate certification

Gate 0.5 established the deterministic, permission-aware Drupal boundary that every framework
implementation must use. It certified:

- [x] Canonical target 1 frozen and independently auditable.
- [x] Permission-scoped image context operation certified.
- [x] Deterministic recommendation validation and idempotent submission certified.
- [x] Real `editor_dana` approval preserved as Drupal revision evidence.
- [x] Read-only recommendation status operation certified.
- [x] All four operations exercised together in one reset-bounded path.
- [x] Source Article non-mutation and final zero-suggestion reset certified.
- [x] Frozen substrate manifest and framework handoff generated.

**Gate 0.5 status:** complete and certified.

Accepted certification evidence:

```text
evidence/gates/gate-0.5/substrate-certification/gate05-step05-20260805T184155Z-50124/
```

Freeze digest:

```text
99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a
```

Certification baseline:

```text
fb23e41f6fc8f8e070babbf9a0f593edb94f8c5c
Certify Gate 0.5 shared substrate
```

The frozen manifest records the framework implementations as not certified by the substrate
preflight. That is an intentional proof boundary, not an unfinished Gate 0.5 checklist.

## Gate 1 — Drupal AI full implementation

Gate 1 is complete and certified. The frozen Drupal AI result remains the baseline while
owning its model invocation, prompt orchestration, state, sequencing, evidence, and lifecycle
behavior.

The implementation progresses from one canonical target to the deterministic 12-target batch. Gate
1 must prove a real Drupal AI model call, schema-valid output, shared-validator acceptance,
recommendation submission and review routing, repeatable evidence, and batch execution without
manual per-target steps. Step 1.01 itself makes none of those runtime claims.

**Completed package:**

```text
gate-1-step01-drupal-ai-batch-contract-v1.0.1
```

**Completed package:**

```text
gate-1-step02-drupal-ai-runtime-probe-v1.0.0
```

**Completed package:**

```text
gate-1-step03-drupal-ai-tool-adapters-v1.0.0
```

**Completed package:**

```text
gate-1-step04-drupal-ai-canonical-vertical-slice-v1.0.0
```

**Completed package:**

```text
gate-1-step05-drupal-ai-batch-runner-v1.0.0
```

**Completed package:**

```text
gate-1-step06-drupal-ai-batch-evidence-and-human-review-v1.0.3
```

**Completed package:**

```text
gate-1-step07-drupal-ai-certification-and-handoff-v1.0.6
```

Accepted Step 1.07 certification evidence: `evidence/gates/gate-1/certification/gate1-step07-20260809T012559Z-2229836`
Accepted Drupal AI certification batch: `drupal_ai-20260809T012559Z-22064c`
Accepted Gate 1 freeze digest: `2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd`
Step 1.07 certification salvage: v1.0.3 corrected the v1.0.2 auditor-field mismatch and promoted the retained model-backed run without a model rerun.
Step 1.07 v1.0.4 documentation repair was rolled back after exposing an audit-shell cleanup defect; certification evidence remained valid and unchanged.
Step 1.07 v1.0.5 repaired the post-certification audit cleanup trap and reapplied the documentation-coherence edits; certification evidence and freeze remained unchanged.
Final Step 1.07 documentation cleanup: v1.0.6 (model-free; residual stale-status/word-boundary defects only; certification evidence and freeze unchanged).

Accepted Step 1.01 evidence run: `gate1-step01-20260805T205448Z-103220`
Accepted Gate 1 contract digest: `360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6`
Accepted Step 1.02 evidence run: `gate1-step02-20260806T010227Z-189538`
Accepted ADR-0006 SHA-256: `223f6d6f4276d3861cf5668f08e0446479d815a07fed18402b1e6a7722d18c4b`
Accepted Step 1.03 evidence run: `gate1-step03-20260806T050827Z-494925`
Accepted Step 1.04 evidence run: `gate1-step04-20260806T213954Z-156475`
Accepted Step 1.05 evidence run: `gate1-step05-20260808T020222Z-2121689`
Accepted Drupal AI batch run: `drupal_ai-20260808T020222Z-205fd9`
Accepted Step 1.06 evidence run: `gate1-step06-20260808T231216Z-2188911`
Accepted Step 1.06 implementation package: `gate-1-step06-drupal-ai-batch-evidence-and-human-review-v1.0.3`
Step 1.06 reviewer-lineage recovery patch: `gate-1-step06-drupal-ai-batch-evidence-and-human-review-v1.0.4`


Step 1.03 directly exercises exactly four model-free Drupal AI FunctionCall adapters: `discover_targets`, `get_image_context`, `submit_recommendation`, and `get_recommendation_status`. It does not execute an AI Agent and makes no model or provider call. Its predecessor-compatible Article-source SHA-256 is `f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17`; the original Step 1.03 hash discrepancy was definition drift only, with no Drupal source drift.

Step 1.01 freezes the machine-readable execution contract, canonical Drupal AI run-state and raw
model-output schemas, lifecycle-separated evidence schemas, and the repository-native package
sequence. It does not execute Drupal AI.

The retained v1.0.0 run `gate1-step01-20260805T200619Z-87483` remains immutable but is superseded
for publication because later checks found terminal schema blank lines and a main-only installed
audit restriction. The v1.0.1 repair changes formatting and audit policy only, not contract semantics.

### Repository-native package sequence

- [x] Step 1.01 — batch contract
- [x] Step 1.02 — pinned Drupal AI runtime probe
- [x] Step 1.03 — thin Drupal AI tool adapters
- [x] Step 1.04 — canonical vertical slice
- [x] Step 1.05 — 12-target batch runner
- [x] Step 1.06 — batch evidence and human review
- [x] Step 1.07 — certification, freeze, and handoff

This sequence and `shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json` govern later package
generation. The Step 1.02 runtime-path decision is recorded in `ADR-0006`; ADR-0004 and ADR-0005 remain
unchanged.

## Gate 2 — cross-framework implementation and recovery

Gate 2 preserves the original umbrella milestone and closes only after Gate 2C shared failure/recovery.

- **Gate 2A — LangGraph:** certified and frozen.
- **Gate 2B — CrewAI:** current.
- **Gate 2C — shared failure/recovery:** deferred and unclaimed.

### Gate 2A — LangGraph

**Completed package:**

```text
gate-2a-step01-langgraph-contract-and-evidence-plan-v1.0.3
```

**Completed package:**

```text
gate-2a-step02-langgraph-runtime-and-checkpoint-probe-v1.0.4
```

**Completed Step 2A.03 packages:**

```text
gate-2a-step03-langgraph-tool-adapters-v1.0.0
gate-2a-step03-langgraph-tool-adapters-v1.0.2
gate-2a-step03-langgraph-tool-adapters-v1.0.3
```

**Completed Step 2A.04 package:**

```text
gate-2a-step04-langgraph-state-and-sqlite-checkpoint-proof-v1.0.6
```

**Completed Step 2A.05 package:**

```text
gate-2a-step05-langgraph-canonical-vertical-slice-v1.0.0
```

**Completed Step 2A.06 package:**

```text
gate-2a-step06-langgraph-human-interrupt-and-review-resume-v1.0.8
```

**Completed Step 2A.07 package:**

```text
gate-2a-step07-langgraph-batch-runner-v1.0.5
```

**Completed Step 2A.08 package:**

```text
gate-2a-step08-langgraph-fresh-batch-and-continuation-v1.0.7
```

**Completed Step 2A.09 package:**

```text
gate-2a-step09-langgraph-evidence-claims-and-matrix-v1.0.4
```

**Completed Step 2A.10 package:**

```text
gate-2a-step10-langgraph-certification-freeze-and-crewai-handoff-v1.0.1
```

Gate 2A LangGraph freeze SHA-256: `a28361c34b9d1c2089eee786324ad34cffbf54e3495f59a276c489865e5630f0`

Accepted Step 2A.10 certification evidence: `evidence/gates/gate-2a/certification/gate2a-step10-20260811T034835Z-03f93652`

**Next package:**

```text
gate-2b-step01-crewai-contract-and-evidence-plan-v1.0.0
```

Accepted Step 2A.09 evidence synthesis: `evidence/gates/gate-2a/evidence-claims/gate2a-step09-20260811T025248Z-7e9c1f5f`

Accepted Step 2A.08 batch evidence run: `evidence/results/langgraph/langgraph-20260810T231915Z-0027cd3e`

Accepted Step 2A.07 construction evidence run: `evidence/gates/gate-2a/batch-runner/gate2a-step07-20260810T185629Z-00272cd1`

Accepted Step 2A.06 evidence run: `evidence/gates/gate-2a/human-interrupt/gate2a-step06-20260810T162448Z-002692eb`

Accepted Step 2A.05 evidence run: `evidence/gates/gate-2a/canonical-slice/gate2a-step05-20260810T140133Z-0025b888`

Accepted Step 2A.04 evidence run: `evidence/gates/gate-2a/checkpoint-proof/gate2a-step04-20260810T034027Z-00250b07`

Accepted Step 2A.03 evidence run: `gate2a-step03-20260809T233127Z-2375581`
Accepted Step 2A.03 compliance verification: `gate2a-step03-verification-20260810T020210Z-2410520`

Accepted Step 2A.02 evidence run: `gate2a-step02-20260809T224238Z-2361786`
Accepted runtime ADR: `docs/decisions/ADR-0010-langgraph-runtime-and-checkpoint-path.md`

Accepted Step 2A.01 evidence run: `gate2a-step01-20260809T202418Z-2334327`
Accepted Gate 2A contract digest: `1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b`

- [x] Step 2A.01 — LangGraph contract and evidence plan
- [x] Step 2A.02 — LangGraph runtime and checkpoint probe
- [x] Step 2A.03 — LangGraph tool adapters
- [x] Step 2A.04 — LangGraph state and SQLite checkpoint proof
- [x] Step 2A.05 — LangGraph canonical vertical slice
- [x] Step 2A.06 — LangGraph human interrupt and review resume
- [x] Step 2A.07 — LangGraph batch runner
- [x] Step 2A.08 — LangGraph fresh batch and continuation
- [x] Step 2A.09 — LangGraph evidence, claims, and matrix
- [x] Step 2A.10 — LangGraph certification, freeze, and CrewAI handoff

Step 2A.01 makes zero model calls and performs zero Drupal mutation. The accepted 2A.08 batch is designed to be the certification candidate; Step 2A.10 promotes it model-free by default rather than silently running a second 12-call batch.

### Gate 2B — CrewAI

Gate 2B is current. Its later package count is not frozen; evidence boundaries follow observed CrewAI behavior rather than LangGraph symmetry.

**Completed package:**

```text
gate-2b-step01-crewai-contract-and-evidence-plan-v1.0.0
```

**Completed Step 2B.02 package:**

```text
gate-2b-step02-crewai-architecture-adr-and-closure-v1.0.0
```

Accepted Step 2B.01 evidence run: `gate2b-step01-20260811T231020Z-00000002`
Accepted Gate 2B contract digest: `c734ad98f23c311e2141e6a50a876a6f5c9abf343e45884843848af1ef40ac77`

- [x] Step 2B.01 — CrewAI contract and evidence plan
- [x] Step 2B.02 — model-free pinned-runtime persistence, continuation, architecture selection, and human-approved ADR
- [x] Step 2B.03 — CrewAI shared-operation adapters (accepted evidence `gate2b-step03-20260818T163812Z-7a58ef58`)

Step 2B.02 compared supported persistence families, process-boundary semantics, storage ownership, serialization privacy, run isolation, Drupal-authoritative pending-continuation compatibility, hidden-call controls, and deterministic failure propagation. Its accepted architecture is recorded in `docs/decisions/ADR-0012-crewai-flow-persistence-and-human-review-continuation.md` and its machine/human closure provenance is retained in `shared/contracts/GATE2B-STEP02-CREWAI-ARCHITECTURE-CLOSURE.json`.

The retained first run `gate2b-step02-20260812T010531Z-00000001` remains immutable diagnostic evidence and superseded/unaccepted for architecture selection. The byte-identical v2 capture `gate2b-step02-20260812T015108Z-00000001` passed its capture boundary but initially left architecture unresolved. The byte-identical targeted supplemental capture `gate2b-step02-followup-20260812T022947Z-00000001` corrected native fallback and checkpoint semantics while preserving its raw `unresolved_path` classifications. The separate governed disposition `gate2b-step02-disposition-20260812T024610Z-00000001` source-attributed those paths, verified the public version-check disable control, and passed all 25 permanent predicates. Human approval selected supported Flow persistence plus the public memory extension plus `HumanFeedbackPending` / `from_pending()` / `resume()`, with runtime checkpoints excluded.

Step 2B.02 is committed, merged, resynchronized, and post-merge audited. Package `gate-2b-step03-crewai-shared-operation-adapters-v1.0.0` is complete, committed, normally merged at `7629434b04d04154b9f219e1d93ed772401a1288`, resynchronized, and post-merge audited with accepted model-free evidence `gate2b-step03-20260818T163812Z-7a58ef58`.

**Completed Step 2B.04 package:** `gate-2b-step04-crewai-canonical-vertical-slice-v1.0.0` completed the successful live run with immutable canonical evidence `crewai-20260818T215017Z-8e03fc95`. Same-step repair `gate-2b-step04-crewai-canonical-vertical-slice-v1.0.1` added model-free post-process-close provenance `gate2b-step04-closure-20260819T195009Z-60344274` and strengthened permanent-audit coverage without replaying the experiment. The result is not yet committed or merged. The recommendation remains pending Drupal-authoritative review; human-feedback continuation and later batch work remain unbegun.

Gate 2C shared failure/recovery remains deferred and unclaimed. CrewAI-specific continuation evidence must remain labeled Gate 2B.

## Subsequent implementation milestones

1. Gate 1 — Drupal AI full implementation and batch evidence.
2. LangGraph full implementation with framework-owned checkpointing and continuation evidence.
3. CrewAI full implementation with framework-owned persistence and continuation evidence.
4. Shared failure injection and recovery comparison.
5. Comparison matrix, clips, screenshots, and claim review.
6. Deck, notes, rehearsal, and fallback package.

## Explicit conference-scope exclusions

- Automatic writes to production image fields
- General-purpose agent platform
- Vector database or semantic-search expansion
- Multiple-model comparison
- Performance or cost benchmarking
- Custom React dashboards
- Cloud deployment of all three implementations
- Complex multi-agent organization beyond the minimum CrewAI specimen
