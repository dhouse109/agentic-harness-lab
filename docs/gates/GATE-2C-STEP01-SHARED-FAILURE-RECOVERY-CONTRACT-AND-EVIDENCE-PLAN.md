# Gate 2C Step 2C.01 — Shared Failure/Recovery Contract and Evidence Plan

## Status

Step 2C.01 is complete only after its model-free certification family is accepted.
It creates no Gate 2C trial or runtime. Gate 2C remains `DEFERRED_UNCLAIMED`, Gate 2
remains `NOT_COMPLETE`, and `CLM-CMP-002` remains `gate-2c-deferred`.

The machine contract is
`shared/contracts/GATE2C-SHARED-FAILURE-RECOVERY-CONTRACT.json`; its sidecar binds the
exact digest. Gate 1 Drupal AI, Gate 2A LangGraph, and Gate 2B CrewAI remain unchanged
and are bound by their certified freeze SHA-256 values.

Package v1.0.0 installed the approved files but failed before certification evidence
creation because its repository-wide privacy scan treated deliberate detector/test
sentinels in frozen predecessor audit source as leaked data. It created no
certification identity or evidence. Package v1.0.1 installed the correct two-scope
privacy repair and its permanent auditor passed, but its installed rehearsal inferred
an external package root from `__file__`, traversed the repository and `.venv`, and
failed before certification evidence creation. It also created no certification
identity or evidence. Package v1.0.2 is a repair candidate that removes external
delivery-package discovery from installed rehearsal; it is not passing certification
evidence unless and until its separately approved execution and permanent audit pass.

## Frozen semantic boundary and failure class

The common boundary is exactly:

```text
after target 6 is fully persisted and before target 7 begins
```

The Gate 2C.02 proof candidate is an external supervisor delivering `SIGKILL` to the
actual framework worker only after an independently verifiable seam-ready signal. A
clean stop, returned command, native interrupt, internal exception, killed wrapper, or
container termination is not equivalent. The supervisor owns only seam verification,
worker identification, sanitized trigger evidence, signal delivery, and wait-status
capture. Framework orchestration, persistence, restart/re-entry, recovery,
continuation, replay/duplicate behavior, and errors remain framework-owned.

The signal/rendezvous implementation does not exist in Step 2C.01. Gate 2C.02 must
prove it model-free before any authoritative model-backed run.

## Framework implementation mappings

These are proposed mappings, not Gate 2C observations.

- Drupal AI: signal only after the second target-6 persistence in the frozen batch
  state and before the target-7 loop body; kill the PHP/Drush worker inside DDEV;
  recovery uses the frozen same-run resume surface over Drupal key/value state.
- LangGraph: signal only after `SqliteSaver` durably checkpoints target 6 and before a
  target-7 node begins; kill the host Python worker; recovery re-enters the same
  database/thread through the public compiled-graph invocation surface.
- CrewAI: signal only after `SQLiteFlowPersistence` saves `target_finalized` for
  target 6 and before the serial loop selects target 7; kill the host Python Flow
  worker; the candidate recovery adapter loads and hydrates the same fresh Gate 2C
  Flow identity through supported public APIs.

Framework-specific rendezvous mechanics are allowed. They may not weaken or move the
common semantic boundary or transfer recovery ownership to the supervisor.

## CrewAI decision remains pending

The CrewAI candidate is public `SQLiteFlowPersistence.load_state(...)` plus supported
Flow construction/hydration with the same Gate 2C Flow identity and persisted state.
The frozen Gate 2B batch is intentionally one-pass, so the candidate is neither
experimentally proven nor human-approved.

Gate 2C.02 must prove public-API provenance, fresh runtime isolation, target-6 state
readback, second-process load/hydration, target 7 as first post-restart work, zero
replay for targets 1–6, zero duplicate submission, zero hidden provider activity,
deterministic error propagation, and privacy. Its machine recommendation must remain
separate from the user's approve/reject decision.

Runtime `CheckpointConfig`, private `_skip_auto_memory`, private/monkeypatched APIs,
human-feedback pending/resume APIs used as a substitute for process recovery,
historical Gate 2B runtime reuse, and manual state edits are prohibited.

## Drupal persistent-lock policy proposed for approval

The existing persistent lock has an 1,800-second lease. Gate 2C may not shorten,
clear, delete, bypass, or replace it.

The proposed authoritative policy permits at most two Drupal recovery invocations:

1. After midpoint evidence is inspected, one separately authorized immediate
   post-kill resume invocation observes whether the retained lock denies recovery.
2. Only if attempt 1 is a verified denial by the expected persistent lock, wait for
   natural lease expiry, re-verify the unchanged policy and timestamps, then obtain a
   second explicit authorization for one final resume invocation.

No second invocation is allowed when attempt 1 began framework recovery, failed for a
non-lock reason, or when seam, kill, runner, environment, credential, or injector
validity is unresolved. A correctly bound lock denial is retained as valid Drupal
behavior, not relabeled as a runner defect. Wrong-process termination, absent signal-9
proof, incomplete seam evidence, wrong resume command, an unbound denial, or bootstrap
failure is invalid pending disposition, not a framework recovery failure.

## Baseline, reset, and runtime isolation

Each later authoritative framework trial starts from the canonical 20-Article,
12-target, zero-suggestion baseline and frozen target order. Source Article/image
fields remain unchanged and automatic publication remains prohibited. Reset and
restoration require separate authorization and do not occur in Step 2C.01.

The current approved CrewAI suggestion and retained Gate 2B recovery snapshot remain
untouched. That snapshot contains post-Step-2B.05 state, is not a zero-suggestion
baseline, may never substitute for the Gate 2C baseline, and may not be deleted.

Every framework receives a fresh Gate 2C trial ID, run ID, and framework-owned runtime
path. The run ID remains the same across kill and recovery. Historical Gate 1, Gate
2A, and Gate 2B runtimes are evidence/context only and may not be resumed or reused.

## Call accounting and result classification

Each authoritative framework trial must record exactly six successful logical
generations before the failure, no more than six successful generations after
recovery, no more than 12 total, and no more than 36 successful logical generations
across the three specimens. These are successful-generation ceilings, not provider-
request ceilings and not permission to omit calls, retries, or failures from evidence.

Each specimen's already-frozen retry configuration and resulting behavior must remain
unchanged unless an ADR and evidence-invalidation boundary is crossed. Gate 2C may not
normalize one specimen to resemble another. The supervisor and Gate 2C adapters may
add no provider, transport, SDK, framework, semantic, repair, generation, fallback, or
other retry loop. If a frozen configuration makes the successful-generation ceiling
ambiguous, execution stops for a material decision rather than changing the runtime.

Every provider, framework, SDK, transport, semantic, repair/correction, generation,
and recovery retry that actually occurs is counted and retained truthfully. An
observed underlying retry is evidence. Concealment or an unaccounted retry invalidates
the trial. Recovery is never retried silently or automatically: every authoritative
recovery invocation needs ledger authorization, including Drupal's separately
authorized immediate and conditional post-natural-expiry invocations.

A provider/transport failure, invalid output, credential failure, environment defect,
runner defect, supervisor/injector defect, invalid seam, or other unexpected failure
is retained and classified. The run stops; no replacement authoritative attempt is
started without explicit authorization. A replayed post-restart generation counts
against the six-generation recovery ceiling and is a valid observed replay failure.

Gate 2C succeeds when it produces three valid comparable evidence families and an
audited synthesis. It does not require all frameworks to recover. A genuine framework
recovery failure or operator-wait-required result is acceptable evidence when the
seam, termination, frozen constants, environment, accounting, and evidence are valid.

## Evidence schemas and permanent audit

The smallest sufficient overlay family is three schemas:

- the Step 2C.01 contract schema;
- one authoritative trial schema covering metadata, Drupal pre/mid/post/restore
  projections, seam-ready signal, termination, persisted midpoint, recovery attempts,
  call accounting, and outcome classification;
- one cross-framework comparison schema containing hash-bound references to exactly
  the Drupal AI, LangGraph, and CrewAI trial families.

Historical schemas and evidence remain immutable. The Step 2C.01 permanent auditor is
successor-aware: it binds the three freeze artifacts and immutable certification
families, runs the retained Gate 2A descendant-preservation audit, validates current
lifecycle semantics, and does not require old standalone auditors' superseded live
Drupal or historical documentation state.

## Protected worktree policy

The exact eleven known untracked Gate 2B runtime/pointer paths are allowlisted by the
contract and package. They remain local-only and must not be staged. Before install,
any staged entry, tracked change, or untracked path outside that exact allowlist fails
closed. After install, only the previewed path set and the Step 2C.01 evidence family
are additionally permitted.

## Authorization ledger and four-package sequence

Package preview approval grants only Step 2C.01 installation and model-free
certification. It grants no later reset, snapshot, rehearsal, model call, termination,
recovery, restoration, retry, claim update, commit, push, or merge.

The frozen Gate 2C sequence is:

1. **2C.01** — this model-free, Drupal-read-only contract, schema, auditor, and
   sanitized planning evidence boundary.
2. **2C.02 — shared failure injector and model-free rehearsals.** Implement the
   external supervisor and thin framework adapters; prove signal-9 termination,
   persisted midpoint state, recovery routing without provider activity, persistent-
   lock behavior where possible, and reset/restoration mechanics. This is the human
   CrewAI recovery-architecture decision boundary. No authoritative model-backed
   comparison is allowed.
3. **2C.03 — three-framework failure/recovery execution.** Run the separately
   authorized Drupal AI, LangGraph, and CrewAI trials; retain actual recovery outcomes;
   complete resets, accounting, source-nonmutation proof, exact final restoration, and
   accepted immutable experimental evidence. Factual per-run summaries are allowed.
   `CLAIMS_REGISTER.md` and `COMPARISON_MATRIX.md` remain unchanged.
4. **2C.04 — evidence synthesis and Gate 2 certification.** Model-free and Drupal-
   read-only consumption of accepted immutable Step 2C.03 evidence; update claims and
   comparison conclusions accurately; create the Gate 2C freeze/certification and
   final handoff; certify Gate 2 only if every umbrella exit criterion passes. It may
   not make a new authoritative run or unsupported winner, superiority, production-
   readiness, speed, or cost claim.

Each framework's pre-failure execution and recovery require separate approvals. A
failed or invalid observation never triggers a second authoritative attempt. Retry,
restoration, Step 2C.03 evidence acceptance, transition to Step 2C.04, Step 2C.04 claim
and certification acceptance, and Git commit/push/merge remain distinct human
boundaries.

## Exit guard

Step 2C.01 passes only when the contract digest, three schemas, permanent auditor,
disposable negative controls, protected-tree policy, and sanitized model-free evidence
all pass with zero model/provider, Drupal-write, runtime, failure-injection, and
snapshot activity. Gate 2C then remains `DEFERRED_UNCLAIMED`; Step 2C.02 is merely the
next package eligible for separate construction and preview.
