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

- **Gate 2A — LangGraph:** current.
- **Gate 2B — CrewAI:** follows the LangGraph freeze.
- **Gate 2C — shared failure/recovery:** follows both frozen framework specimens.

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

**Next package:**

```text
gate-2a-step07-langgraph-batch-runner-v1.0.0
```

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
- [ ] Step 2A.07 — LangGraph batch runner
- [ ] Step 2A.08 — LangGraph fresh batch and continuation
- [ ] Step 2A.09 — LangGraph evidence, claims, and matrix
- [ ] Step 2A.10 — LangGraph certification, freeze, and CrewAI handoff

Step 2A.01 makes zero model calls and performs zero Drupal mutation. The accepted 2A.08 batch is designed to be the certification candidate; Step 2A.10 promotes it model-free by default rather than silently running a second 12-call batch.

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
