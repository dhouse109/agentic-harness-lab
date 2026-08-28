# Gate 2B Step 2B.06 — CrewAI frozen 12-target batch and hardening

**Final prepared repair:** `gate-2b-step06-crewai-frozen-12-target-batch-and-hardening-v1.0.3`

## Current transaction state

The v1.0.1 implementation is installed but uncommitted. The governed snapshot
`gate2b-step06-post-step2b05-recovery-20260826T152003Z` remains retained with SHA-256
`4ba4cece2d30a5f90699afdf9a2ab2094f0d902213c66cdc0b40dfa466094906` and size
4,112,532 bytes. The protected reset and explicit activation are already complete. Live Drupal
contains 20 Articles, the frozen 12 targets, zero suggestions, target hash
`1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728`, and source projection
`f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17`. Both operational
modules are enabled, and activation evidence manifest
`2008ce545bb553e3ba21e2a013fb419d953a03c36c361bf7f46a986bd8d7f63d` is immutable.

The first authoritative batch attempt consumed run ID `crewai-20260827T125501Z-c5381188` and
failed before target selection when authenticated HTTP discovery returned 403. It consumed zero
logical generations, provider requests/responses, submissions, targets, source mutations, or
restores. Its two-file failure evidence and initialized local-only runtime are permanent and must
never be rewritten, reused, or deleted.

## v1.0.2 diagnosis and repair

The installed runner constructed `DrupalClient` from ambient `GATE2B_DRUPAL_*` values. The
principal and base URL bindings were correct, but the ambient password did not match the accepted
governed `agent_bot` credential source retained by Phase 0 Step 7. A single read-only diagnostic
through the exact client discovery method, using the governed credential source, returned HTTP 200.
The defect is therefore a stale/wrong ambient credential binding in Step 2B.06, not a Drupal
permission, route, Basic Auth construction, base-URL, CrewAI, or provider failure. No credential
resynchronization or least-privilege expansion is required.

v1.0.2 introduces one canonical credential loader for both authenticated readiness and batch-only.
It reads the governed `agent_bot` binding without retaining or reporting credential material,
requires the resolved DDEV base URL, and does not fall back to an unrelated ambient password.
Missing or invalid binding fails closed.

The repaired live lifecycle is:

`ACTIVATION_COMPLETE_MODEL_READY → AUTHENTICATED_HTTP_PREFLIGHT_PASS_MODEL_READY → allocate a fresh explicitly authorized run ID → BATCH_COMPLETE_AWAITING_RESTORE → RESTORE_VERIFIED → STEP_2B_06_COMPLETE`.

Authenticated HTTP readiness executes the exact read-only
`DrupalClient.find_images_needing_review()` path and proves the frozen 12-target order before any
run-ID allocation, authoritative runtime creation, target selection, provider credential use, or
provider request. A 401/403, wrong principal, missing credential, route denial, target drift, or
source drift leaves run-ID/runtime/provider counts at zero.

## Explicit authoritative modes

The package exposes non-overlapping modes:

1. `activate-only` — completed historical model-free module/permission activation;
2. `http-readiness-only` — the next separately authorized model-free authenticated discovery gate;
3. `batch-only` — one separately authorized fresh serial 12-target attempt after readiness;
4. `restore-only` — one separately authorized restore and equality proof after batch success;
5. `audit` — read-only lifecycle evidence validation.

`http-readiness-only` cannot allocate a run ID, create a runtime, invoke a provider, submit a
recommendation, create/reset/restore/delete a snapshot, or change Drupal. `batch-only` cannot
create/reset/restore/delete a snapshot or activate modules. `restore-only` cannot reach the model or
submission path. No mode silently invokes another.

## Batch-only contract and idempotency

Batch-only requires the exact retained snapshot, immutable activation and HTTP-readiness manifests,
20/12/0 Drupal state with frozen hashes, enabled modules/services, active Gate 0.5, no accepted
batch, and explicit fresh-run authorization. The historical failed run ID and runtime are rejected.
The presence of failure evidence alone never authorizes a new attempt. An accepted successful batch
continues to block all future authoritative reruns.

A separately authorized fresh run may retain the original successful budget because the failed run
consumed no model/provider/submission budget: 12 serial logical generations, 12 physical provider
requests and successful responses, and 12 submissions, with zero transport, SDK, guardrail,
correction, repair, fallback, feedback-collapse, or learning retries/calls. Batch success stops with
12 live suggestions at `BATCH_COMPLETE_AWAITING_RESTORE`; restoration is never automatic.

## Evidence lifecycle

The immutable v1.0.1 activation family remains unchanged. v1.0.2 adds a separate eight-file
authenticated-readiness family with seven manifest entries. It records only sanitized bindings,
the exact discovery result, frozen live-state hashes/counts, zero run/runtime/model/provider/write
accounting, privacy, and lifecycle `AUTHENTICATED_HTTP_PREFLIGHT_PASS_MODEL_READY`.

A separate two-file failure-disposition family is recommended for the consumed first run. It binds
the immutable failure JSON/manifest, failed runtime hash/size, retained snapshot, activation
manifest, verified live-state hashes/counts, root-cause class, and repair version. It supplements
but never alters the historical failure evidence.

Future failure evidence is hardened to retain sanitized runtime and live-state provenance, snapshot
and activation/readiness bindings, exact stop stage/sequence, accounting, last completed target,
and privacy status. It never includes credentials, headers, environment dumps, raw database/image
data, or hidden reasoning.

Batch-only still creates 15 immutable stage files including `batch-manifest.json`. Restore-only
preserves those bytes and adds the four final closure files, producing the established 19-file
successful family. The existing final schema remains valid; no schema change is required.

## Nonclaims

v1.0.2 preparation, self-check, and rehearsal are model-free. They do not alter Drupal, synchronize
credentials, allocate a live run ID, create a live runtime, process target 1, call OpenAI, submit a
recommendation, restore/delete the retained snapshot, complete Step 2B.06, begin Step 2B.07/2B.08,
or execute Gate 2C. A future run requires separate explicit authorization after the live
authenticated-readiness boundary passes.

## v1.0.3 immutable batch-stage governance supplement

Fresh run `crewai-20260827T174606Z-6249d844` operationally completed the frozen 12-target
batch and stopped at `BATCH_COMPLETE_AWAITING_RESTORE`. Its original 15-file family (14 manifest
entries, manifest `e89069bec85a51655631fe1333f8af4a8f54968b06492619b50a36e8204368e1`)
is immutable. It is never regenerated or extended in place.

The authorization-level audit found two recording omissions: the family did not directly bind the
historical failed run/disposition, and its accounting omitted an explicit
`feedback_collapse_calls` field. v1.0.3 resolves both with exactly two separate files under
`frozen-batch-governance-supplement/<successful-run>/<supplement-id>/`. The supplement references
the original batch manifest, historical failure and disposition, activation/readiness chain,
snapshot, runtime, and frozen source/target identities. Its explicit zero feedback-collapse value
is established model-free from the selected one-pass Flow call graph, single Responses transport
site, zero pending-feedback rows, exact 75-row runtime lifecycle, and retained 12/12 request/response
accounting. The human-review continuation module is not imported or reachable by this batch path.

`governance-supplement-only` removes provider credentials, cannot execute the Flow, cannot write to
Drupal, and cannot restore. The strict batch-stage auditor first validates every original batch byte
and then validates the supplement. Only this accepted historical Step 2B.06 batch requires the
bridge. Future generated families record direct historical/disposition binding when applicable and
an explicit `feedback_collapse_calls` field. Accepted supplementation changes evidence acceptance
to `BATCH_STAGE_ACCEPTED_AWAITING_RESTORE`; it does not advance the operational lifecycle, restore
Drupal, or claim `STEP_2B_06_COMPLETE`.

## v1.0.4 post-finalization governance composition

Restoration later occurred exactly once and the immutable 19-file closure records
`RESTORE_VERIFIED` and `STEP_2B_06_COMPLETE`. That final validator did not directly bind the
separate v1.0.3 supplement, while the historical supplement validator correctly required the
earlier exact 15-file shape. Neither validator is weakened and no predecessor artifact is rewritten.

v1.0.4 adds a separate two-file family under
`frozen-batch-final-governance/<successful-run>/gate2b-step06-final-governance-v104/`. The artifact
is a strict local hash/provenance bridge, not duplicated experiment evidence. `final-composite`
validates the embedded immutable batch stage within the finalized 19-file shape, the supplement in
its own root, the final closure, the retained runtimes/snapshot and restored canonical Drupal state,
then requires exact cross-binding. Acceptance adds `FINAL_GOVERNANCE_ACCEPTED` while preserving the
historical lifecycle strings. Future finalization creates this same separate attestation after the
19-file closure; it never edits that closure in place. No shared schema or frozen contract changes.
