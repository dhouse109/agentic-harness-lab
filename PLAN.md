# Implementation Plan

## Current status

> Phase 0 and Gate 0.5 are complete. Gate 1 Steps 1.01 and 1.02 are complete; Step 1.03 is next.

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

Gate 1 is the active phase. Drupal AI must use the frozen shared operations and constants while
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

**Next package:**

```text
gate-1-step03-drupal-ai-tool-adapters-v1.0.0
```

Accepted Step 1.01 evidence run: `gate1-step01-20260805T205448Z-103220`
Accepted Gate 1 contract digest: `360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6`
Accepted Step 1.02 evidence run: `gate1-step02-20260806T010227Z-189538`
Accepted ADR-0006 SHA-256: `223f6d6f4276d3861cf5668f08e0446479d815a07fed18402b1e6a7722d18c4b`

Step 1.01 freezes the machine-readable execution contract, canonical Drupal AI run-state and raw
model-output schemas, lifecycle-separated evidence schemas, and the repository-native package
sequence. It does not execute Drupal AI.

The retained v1.0.0 run `gate1-step01-20260805T200619Z-87483` remains immutable but is superseded
for publication because later checks found terminal schema blank lines and a main-only installed
audit restriction. The v1.0.1 repair changes formatting and audit policy only, not contract semantics.

### Repository-native package sequence

- [x] Step 1.01 — batch contract
- [x] Step 1.02 — pinned Drupal AI runtime probe
- [ ] Step 1.03 — thin Drupal AI tool adapters
- [ ] Step 1.04 — canonical vertical slice
- [ ] Step 1.05 — 12-target batch runner
- [ ] Step 1.06 — batch evidence and human review
- [ ] Step 1.07 — certification, freeze, and handoff

This sequence and `shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json` govern later package
generation. The Step 1.02 runtime-path decision is recorded in `ADR-0006`; ADR-0004 and ADR-0005 remain
unchanged.

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
