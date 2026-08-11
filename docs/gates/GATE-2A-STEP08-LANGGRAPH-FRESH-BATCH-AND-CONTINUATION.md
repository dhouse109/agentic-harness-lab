# Gate 2A Step 2A.08 — LangGraph fresh batch and same-run continuation

**Package:** `gate-2a-step08-langgraph-fresh-batch-and-continuation-v1.0.7`

## Purpose

Execute the already-installed Step 2A.07 live batch path against the frozen 12-target dataset, using exactly
12 successful OpenAI model calls and the real Drupal semantic-operation boundary. Step 2A.08 is the
certification-candidate batch for Gate 2A; Step 2A.10 will promote this accepted run model-free by default
rather than silently performing a second 12-call batch.

Step 2A.08 does not introduce a second batch engine. It wraps the merged
`langchain/agentic_harness_langgraph/batch_runner.py` live `start`/`resume` entrypoints with execution
authorization, midpoint inspection, failure retention, exact Drupal snapshot restoration, evidence
promotion, and lifecycle controls.

## Frozen live sequence

For each target, the merged LangGraph runner performs:

```text
fresh get_image_context
→ one structured model invocation
→ fresh pre-submit get_image_context
→ deterministic validation
→ submit one pending recommendation
→ observe pending recommendation status
→ post-submit get_image_context
→ checkpoint
```

The wrapper enforces the frozen continuation boundary as two human-authorized commands:

1. `start` spends successful model calls 1–6 only.
2. Target 6 is fully persisted.
3. LangGraph enters a genuine `interrupt()` before target 7.
4. The command stops for human inspection with Drupal intentionally left at the six-pending-recommendation midpoint.
5. `resume` first proves the Drupal midpoint has not changed.
6. The same `run_id == thread_id` resumes with `Command(resume=...)`.
7. Successful model calls 7–12 complete the batch.
8. The wrapper restores the exact pre-run DDEV snapshot after evidence capture.

The midpoint is controlled continuation, **not** the later Gate 2C failure/recovery injection.

## Model and retry budget

Frozen settings:

- provider: OpenAI
- model: `gpt-4.1-mini-2025-04-14`
- temperature: `0.0`
- total successful Step 2A.08 calls: **12**
- successful calls before midpoint: **6**
- successful calls after resume: **6**
- automatic model retries: **0**
- semantic retry loop: **prohibited**
- any transport/model/validation failure is retained and blocks an unreviewed rerun

## Exact semantic-operation counts

At the six-target midpoint:

- `find_images_needing_review`: 1
- `get_image_context`: 18
- `submit_recommendation`: 6
- `get_recommendation_status`: 6

At completion:

- `find_images_needing_review`: 1
- `get_image_context`: 36
- `submit_recommendation`: 12
- `get_recommendation_status`: 12

The batch creates 12 real pending recommendation records during live execution. It does not mutate or
publish source Articles. The wrapper restores Drupal to the exact pre-run snapshot after successful
completion, while retaining the truthful recommendation/submission/status evidence.

## Evidence

Framework result evidence is written under:

`evidence/results/langgraph/<run-id>/`

The accepted result includes the frozen batch collections plus checkpoint, continuation, privacy, call-counter,
and summary artifacts. `human-review.json` is deliberately absent because Step 2A.08 does not fabricate a
second review system; authoritative Drupal human review was already proven in Step 2A.06.

Wrapper/restore evidence is written under:

`evidence/gates/gate-2a/fresh-batch/<run-id>/`

It retains hashes and booleans rather than raw Drupal snapshots, including:

- pre-run Drupal-state hash;
- controlled-midpoint Drupal-state hash;
- proof the midpoint did not change before resume;
- completed-live-state hash;
- exact post-restore Drupal-state hash;
- runtime SQLite SHA-256 before disposal;
- proof the runtime database was not retained.

## Human gates

The intended execution sequence is:

```text
package preview
→ package install
→ active-boundary inspection
→ authorize start (calls 1–6)
→ midpoint evidence + Drupal-stability inspection
→ authorize resume (calls 7–12)
→ candidate evidence inspection
→ model-free certify
→ exact-scope stage
→ staged audit
→ human commit approval
→ commit
→ post-commit audit
→ push
→ PR
→ human merge approval
→ merge
→ resync main
→ post-merge audit
```

Step 2A.09 remains locked until the entire Step 2A.08 merge/resync/post-merge sequence passes.

## v1.0.1 preventive review hardening

v1.0.1 supersedes v1.0.0 before preview/install. The preventive review was performed specifically
against failure classes already observed in earlier Gate 2A packages. No v1.0.0 repository mutation,
evidence run, model/provider call, or Drupal semantic call occurred.

The repair:

- removes packaged `__pycache__` / `.pyc` artifacts and compiles Python source in-memory during
  self-check so the archive remains source-only and interpreter-neutral;
- preserves the historical repository `Next package` anchor at v1.0.0 while recording v1.0.1 as the
  installed active package, preventing repair-version lifecycle-anchor drift;
- requires preview/install to run with OpenAI/candidate-model access unset and rejects pre-existing
  local or remote Step 2A.08 branches;
- retains `set -E` rollback semantics and self-tests function-scope `ERR` propagation;
- adds explicit human authorization guards for the calls-1–6 `start` and a run-bound calls-7–12
  `resume`, so an API key alone cannot accidentally spend the model budget;
- requires the merged Step 2A.07 batch engine and supporting source files to remain unchanged from the
  reviewed merge base before live execution;
- fails closed if `origin/main` advances from the reviewed Step 2A.07 base before a live boundary;
- constrains the uncommitted working-tree scope before live actions and rejects staged or unrelated
  tracked/untracked changes;
- arms `ERR`/`INT`/`TERM` live guards once the pre-run DDEV snapshot/control record exists, so an
  unexpected wrapper failure is retained and routed through recovery rather than leaving silent state;
- separates snapshot restore from cleanup, verifies seeded-clean plus an exact canonical Drupal-state
  hash before deleting the DDEV snapshot, and preserves recovery control when restore cannot be proven;
- records restore-attempt/verification/cleanup truth in failure and candidate wrapper evidence;
- makes certification rollback signal/error-safe and removes temporary `LATEST` state on rollback;
- strengthens midpoint audit coverage for frozen targets, recommendation identity linkage, continuation
  metadata, event schemas, and privacy flags before calls 7–12 can be authorized;
- strengthens candidate audit coverage for retained midpoint/final checkpoints, first-six identity
  immutability, duplicate detection, and wrapper restore evidence.

## v1.0.2 canonical-anchor and failure-path hardening

v1.0.1 preview stopped before repository mutation because the lifecycle helper encoded a displayed
historical typo, `Step 2A.01through`, while canonical merged `docs/CURRENT-STATUS.md` at the reviewed
Step 2A.07 merge contains `Step 2A.01 through`. Preview therefore found zero exact replacements and
stopped before branch creation, evidence creation, model/provider access, or Drupal activity.

v1.0.2:

- derives the active/complete CURRENT-STATUS transition from the canonical merged wording and adds a
  source-only lifecycle fixture that exercises the exact v1.0.0 historical package anchor through
  v1.0.2 active state and then through complete state;
- explicitly rejects reintroduction of the `Step 2A.01through` typo in the lifecycle helper;
- arms live recovery immediately after a successful DDEV snapshot and before writing the control/LAST
  attempt state, preventing a setup error from leaving a blocked but unretained attempt;
- keeps recovery armed after successful Drupal restoration until wrapper evidence, manifests,
  candidate audit, and the candidate pointer are safely written;
- remembers the runtime SQLite digest across post-restore bookkeeping so a late retained failure still
  records the pre-disposal database hash;
- makes failure recording restore `errexit` deterministically and return its intended caller exit code
  through an explicit `MARK_FAILURE_RC`, rather than leaving the shell globally in `set +e` mode;
- gives certification ERR/INT/TERM rollback explicit exit-code handling; and
- adds structural self-checks for setup-trap ordering, post-restore retention ordering, failure-handler
  error-mode restoration, and certification signal traps.

The v1.0.1 preview failure produced no repository changes, no branch, no evidence run, no model/provider
call, and no Drupal semantic call or mutation.
## v1.0.3 predecessor-audit lifecycle repair

v1.0.2 preview passed. Installation then set Step 2A.08 active and its active audit passed, but the
installer reran the Step 2A.07 permanent complete-state audit. That predecessor audit requires the
top-level `Completed package` marker to still name the Step 2A.07 package. Step 2A.08 activation
truthfully supersedes that marker with the Step 2A.08 active package, so the predecessor audit reported
`AGENTS completed package marker missing`. The installation rollback fired. No model/provider call,
Drupal semantic call/mutation, Step 2A.08 result run, or recommendation write occurred.

v1.0.3 keeps the Step 2A.07 permanent audit at the pre-activation boundary only. After activation,
Step 2A.08's own auditor is authoritative for predecessor invariants: it verifies the exact accepted
Step 2A.07 pointer, frozen hashes, and reviewed Step 2A.07 source directly. The same lifecycle-sensitive
Step 2A.07 audit is removed from the Step 2A.08 live preflight so a later authorized `start` cannot fail
for the same false lifecycle reason before model call 1. Gate 1's regression audit remains after
activation. A package self-check asserts one predecessor-audit invocation in installer preflight and
zero in the active/live wrapper.



## v1.0.4 midpoint-aware Gate 1 audit repair

The first authorized Step 2A.08 half completed successfully under v1.0.3 for run
`langgraph-20260810T231915Z-0027cd3e`, using exactly six successful model calls and stopping at the
genuine LangGraph continuation boundary before sequence 7. The subsequent human-authorized `resume`
command stopped during preflight before any second-half model call because the common live preflight
re-ran the Gate 1 post-certification audit while Drupal was intentionally at the six-recommendation
midpoint. That Gate 1 audit is state-sensitive and correctly expects certified restored Drupal state,
so it is not valid at the intentional Step 2A.08 midpoint.

v1.0.4 changes wrapper orchestration only; it does not change `batch_runner.py`, the frozen target
sequence, model/settings, prompt, validator, semantic operations, checkpoint semantics, continuation
boundary, or evidence schemas. The repair:

- preserves the exact accepted midpoint run/thread and six-call evidence;
- requires the Gate 1 restored-state audit before the initial live start;
- deliberately omits that state-sensitive Gate 1 audit from pre-resume preflight;
- independently requires the stored midpoint audit plus exact current-Drupal midpoint SHA before call 7;
- reruns the Gate 1 audit immediately after exact pre-run Drupal restoration and before candidate promotion;
- requires Gate 1 again before model-free certification; and
- records this package repair in the existing Step 2A.08 wrapper-evidence directory.

The rejected v1.0.3 resume preflight made zero second-half model calls and no Step 2A.08 semantic
mutation. It did not create a failure record because it stopped before the live recovery trap was armed.


## v1.0.5 lifecycle-neutral static-preflight repair

After the v1.0.4 midpoint-preserving repair was installed, a model-free inspection invoked the
public `preflight` command while Drupal intentionally remained at the six-recommendation midpoint.
The command still called the Gate 1 restored-state regression audit and therefore reported
`Current full Drupal projection differs from certified restored state.` The dedicated Step 2A.08
midpoint audit passed, the current Drupal projection exactly matched the recorded midpoint SHA-256,
the run remained interrupted after six successful calls, and the recovery snapshot remained present.
No second-half model call, Drupal semantic call, restore, or resume was performed by that inspection.

v1.0.5 makes `preflight` lifecycle-neutral/static-only. The state-sensitive Gate 1 audit remains
mandatory at the boundaries where restored Drupal is actually expected: before the initial `start`,
immediately after exact final restoration, and again before model-free certification. `resume` instead
requires the exact persisted midpoint audit and exact current-Drupal-to-midpoint hash equality before
call 7. The core `batch_runner.py`, frozen experiment semantics, existing run/thread, six-call evidence,
and recovery snapshot are unchanged.

## v1.0.6 privacy self-report repair and model-free salvage path

The human-authorized v1.0.5 resume for run `langgraph-20260810T231915Z-0027cd3e` completed targets
7–12 successfully. The retained call counters prove exactly 12 attempted and 12 successful model calls,
with zero automatic retries and no semantic retry loop. The completed checkpoint contains sequences 1–12
and 12 unique recommendation UUIDs. The live core then failed at its final privacy assertion because
`checkpoint_privacy()` scanned every evidence file already present in the result directory. The midpoint
privacy report itself contains the reporting field name `hidden_reasoning_persisted`, so the final scan
matched the literal substring `hidden_reasoning` in its own prior report and produced a false positive.

The wrapper truthfully retained the run as failed, restored Drupal exactly to the recorded pre-run state,
verified the Gate 1 restored-state regression, disposed the runtime SQLite/control files, and cleaned the
pre-run DDEV snapshot. The original failed privacy report and failed-run registration remain immutable
historical evidence.

v1.0.6 makes two narrowly scoped repairs:

- `batch_runner.py` excludes `checkpoint-privacy-before-continuation.json` and
  `checkpoint-privacy-after-continuation.json` from the evidence-byte corpus scanned by
  `checkpoint_privacy()`, preventing privacy-report self-detection while leaving SQLite, current state,
  all other evidence files, generic prohibited patterns, and exact ephemeral probes in scope;
- the Step 2A.08 wrapper/auditor gains a model-free `salvage` path for this exact retained run. Salvage
  requires the original failed report to remain failed with only the reviewed `hidden_reasoning` generic
  hit, requires the original live exact-ephemeral hit set to be empty, requires no generic prohibited
  patterns anywhere outside the privacy-report artifacts, requires 12/12 completed call counters,
  12 unique recommendations, the frozen continuation semantics, verified failure recovery, exact restored
  Drupal state, Gate 1 restored-state regression, disposed runtime/control state, and no existing candidate
  or accepted pointer.

Salvage does not rewrite the failed privacy report and does not fabricate the deleted runtime database.
Instead it adds a separate salvage privacy disposition that explicitly records the limitation that the final
SQLite database was disposed by the verified failure-recovery path after its SHA-256 was captured and cannot
be re-scanned. It also adds a separate salvage wrapper summary; it does not fabricate the normal
`wrapper-summary.json` that the failed live path never reached. The failed-run entry remains present even if
the evidence is later promoted as a model-free salvaged candidate.

No new model/provider call, Drupal semantic call/mutation, live resume, source-Article mutation, human review,
or Gate 2C failure injection is authorized by the v1.0.6 package install or salvage path.


## v1.0.7 package-preview shell repair

The v1.0.6 package was never installed. Its first human-run `preview` completed the archive checksum
and structural self-checks, then exited before repository validation with `package.sh: line 130: gate:
unbound variable`. Under `set -u`, the declaration assigned `gate`, `run`, and `gdir` on one `local`
command while `gdir` expanded `$gate`; Bash expanded the right-hand sides before the new local value was
available. The preview therefore made no repository changes, no model/provider calls, no Drupal semantic
calls or mutations, no restore, no live resume, and no salvage promotion.

v1.0.7 preserves the v1.0.6 privacy self-report repair and model-free salvage design unchanged, but splits
that declaration into declaration-plus-assignment statements so the reviewed failed-run validation can execute
under `set -Eeuo pipefail`. A structural regression check requires the safe split form. The active repository
package remains v1.0.5 until v1.0.7 is explicitly installed after preview and human review.
