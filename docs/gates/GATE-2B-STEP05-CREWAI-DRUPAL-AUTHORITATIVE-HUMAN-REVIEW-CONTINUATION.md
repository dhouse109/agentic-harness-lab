# Gate 2B Step 2B.05 — CrewAI Drupal-authoritative human-review continuation

## Status and claim

This package installs the smallest continuation-only CrewAI Flow around the accepted Step 2B.04
recommendation. It does not recreate the canonical generation pipeline. Completion may establish
only that the same logical CrewAI Flow continued across one real Drupal-authoritative review
boundary without replaying prior model-owning work or submitting another recommendation. It is not
Gate 2C failure/recovery evidence.

Package v1.0.1 repairs only the Boundary A runner lifecycle. The v1.0.0 wrapper placed XDG storage
inside its proposed continuation-runtime directory; CrewAI import-time initialization therefore
created that directory before Process A's exclusivity check. The attempt failed closed before source
runtime copy, Flow creation, pending persistence, model/provider activity, or Drupal mutation.
Consumed identity `gate2b-step05-20260820T151225Z-8b7fa221` remains retained and must never be reused.

## Frozen source binding

- Step 2B.04 source/Flow/application run: `crewai-20260818T215017Z-8e03fc95`
- recommendation: `1878ae86-834c-4813-9134-4c3b8d0833c9`, node/revision `21/21`, pending
- canonical manifest/summary: `c6115ffea4b7ceefb7858e6b482713fc92998dcf2bde7bc6de8831d583665aaf` /
  `5cd324d26b866c83d9728e7634887bcf3ccc46c2df5f4fc6a9563069f71ef490`
- closure manifest/summary: `d62ababa96b223643ab23e3d67c75b3fcc2bb325a8a3e69787fff870cc56583b` /
  `e482aa166485ea97c0698b82dade0cfdadbe9947fb06aa2ce0d59c9a3cc87f01`
- source Article projection: `f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17`

The three accepted SQLite/WAL/SHM files are hashed as filesystem objects, copied byte-for-byte into
`crewai/.runtime/gate2b-step05/<continuation-id>/`, and never opened through SQLite at the source
path. The copied runtime is CrewAI-owned, local-only, and outside `shared/`.

## Supported continuation mechanism

The implementation uses public CrewAI 1.15.10 APIs only: `Flow`,
`set_memory_storage_factory(...)`, `SQLiteFlowPersistence`, `@human_feedback(emit=None, llm=None,
learn=False)`, `HumanFeedbackPending`, `from_pending(...)`, and `resume(...)`. The continuation-only
Flow has no executable discovery, context, model, recommendation assembly, validation, or submission
methods. Runtime `CheckpointConfig`, private `_skip_auto_memory`, handler manipulation, manual pending
rows, source patches, and replacement workflow engines are prohibited.

The pending identity is SHA-256 of the canonical serialization of the returned
`HumanFeedbackPending.context.to_dict()`. The initial Flow instance's `pending_feedback` property is
not treated as authoritative. Process B recomputes the hash from the context restored by
`from_pending(source_flow_id, persistence)` before calling `resume(...)`.

## Three approval boundaries

### A — package execution and Process A

Package execution installs the previewed sources, copies the frozen source runtime, loads the latest
accepted state into the continuation-only Flow while preserving `state.id` and `run_id`, reads the
pending Drupal recommendation, reaches the public async feedback boundary, persists exactly one
pending row, retains immutable Process A evidence, and exits. Budget: zero model/provider calls,
zero Drupal writes, zero review actions, and zero submissions. It stops.

### B — real Drupal review

Only separately authorized `editor_dana` acts in Drupal. The recommended minimal action is
approve-as-is: node and UUID remain unchanged, revision `21` gains exactly one unpublished revision
`22`, status becomes `approved`, reviewer
is `editor_dana`, review timestamp is populated, and proposed alt text and all target/run/evidence
fields remain unchanged. The package's `capture-review` mode is read-only and cannot perform review.
It captures and binds the two-revision lineage, then stops.

### C — Process B

Only separately authorized Process B re-observes Drupal, constructs a deterministic JSON transport
signal from that observation, restores through public `from_pending(...)`, verifies the same pending
identity, and calls `resume(...)`. The listener re-reads Drupal. Any missing review or disagreement
between signal and Drupal fails closed; the signal cannot approve or override anything. A successful
resume clears the one pending row. The authoritative path calls `from_pending(...)` exactly once and
`resume(...)` exactly once; it makes zero post-clear reconstruction or resume attempts. Rejection of
a post-clear second reconstruction remains a disposable-rehearsal control only.

## Normal-local execution requirement

The diagnostic proved a Codex command-sandbox defect: after completed thread-pool work, the
restricted sandbox may fail to wake Python's asyncio loop. The same pinned environment passed
`await asyncio.to_thread(...)` 20/20 and all CrewAI controls in normal local subprocess execution.
Static checks are sandbox-independent. CrewAI rehearsal and future lifecycle processes must be
invoked as normal local subprocesses; the wrapper proves 20 thread-pool wakeups before its disposable
rehearsal. For authoritative stages it allocates XDG under a disposable
`/tmp/gate2b-step05-xdg-<continuation-id>.*` root. Canonical-path guards require XDG and the
authoritative runtime to be unequal, non-nested siblings. Only Process A may create
`crewai/.runtime/gate2b-step05/<continuation-id>/`. This is an
execution-context rule, not a CrewAI patch or a supported-API exception.

## Evidence lifecycle

Successful evidence lives at
`evidence/gates/gate-2b/human-review-continuation/<continuation-id>/` with exactly 15 files:

1. Process A: `authorization.json`, `bindings.json`, `process-a.json`,
   `events-process-a.jsonl`, `process-a-summary.json`, and `process-a-manifest.json`.
2. Review: `human-review.json` and `human-review-manifest.json`, which binds the unchanged Process A
   manifest.
3. Process B/final: `process-b.json`, `accounting.json`, `events-process-b.jsonl`,
   `privacy-scan.json`, `summary.json`, `summary.md`, and `evidence-manifest.json`.

The final manifest hashes every other successful evidence file. Process A files are never rewritten
after their manifest is created. The review manifest binds that manifest rather than replacing it.
A failed lifecycle stage retains sanitized `failure.json` and `failure-manifest.json` separately under
`evidence/gates/gate-2b/human-review-continuation-failures/<continuation-id>/<stage-attempt-id>/`
so it never rewrites a successful earlier stage. The record includes the failure point, runtime/copy/
Flow/pending disposition, zero-activity accounting, retained-path disposition, and privacy result.
It is available from continuation allocation through pending-boundary creation, before the six-file
successful Process A family exists. The permanent auditor validates every retained failure manifest
and privacy boundary.

The v1.0.0 failure predates this mechanism. No artifact is retroactively claimed. A later separately
authorized, model-free historical disposition may record its later capture timestamp and explicit
retrospective status, bound to the unchanged empty local directory and observed execution report.

## Permanent-audit boundary

The auditor accepts installed/uncommitted, feature-commit, and ordinary merge-descendant states by
requiring the Step 2B.04 merge commit to be an ancestor, not equal to `HEAD`. It verifies immutable
Step 2B.04 canonical/closure evidence and source runtime; pinned versions and lock; public API source
shape; source/Flow/pending/recommendation relationships; exact review lineage and reviewer;
exactly one authoritative `from_pending` and `resume`; pending rows `1 -> 0`; zero second
authoritative attempts; the separate disposable post-clear rejection control; zero
replay/model/provider/submission/learning;
source nonmutation; stage and final manifests; privacy; and absence of any Gate 2C claim.
