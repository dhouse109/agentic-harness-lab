# Gate 1 Step 1.01 Audit Progression Compatibility Repair

## Scope

This narrow repair changes only the installed Step 1.01 audit implementation so completed/audit
mode validates the immutable Step 1.01 completion boundary across legitimate later Gate 1 states.
It is not a Step 1.01 contract revision, a Step 1.02 revision, a new implementation step, a Gate
0.5 recertification, or Step 1.03 work.

## Reproduced predecessor defect

At predecessor commit `9b303ec3aefd8d92526905ca929a647948030b5a`, completed/audit mode
requires `gate-1-step02-drupal-ai-runtime-probe-v1.0.0` to remain the next package in all status
documents. After Step 1.02 legitimately completed, the installed audit failed with:

```text
[ERROR] CURRENT-STATUS.md was not advanced by the passing runner
```

The frozen Step 1.01 contract, accepted evidence, and current status documents were correct. The
progression-sensitive assertion in the auditor was the defect.

## Repaired behavior

Active/pre-run mode retains its exact historical checks. Completed/audit mode now:

- reads the seven-step sequence from
  `shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json`;
- requires the PLAN checklist to match that sequence and form a contiguous completed prefix;
- requires Step 1.01 completion, its accepted run ID, and its accepted digest in `PLAN.md`,
  `README.md`, and `docs/CURRENT-STATUS.md`;
- rejects stale active, pending, or not-yet-run Step 1.01 prose;
- requires the status documents to agree on completed steps and the next frozen step;
- rejects unknown next packages, gaps, contradictory next packages, and regressions;
- no longer requires Step 1.02 to remain next after later steps complete.

The audit JSON field `step02_started` is replaced by
`step02_started_by_step01_package: false` plus an explicit scope string. This describes the
historical Step 1.01 package action and does not assert that Step 1.02 is unstarted now. Repository
search found no installed consumer of the old auditor-output field. Immutable retained Step 1.01
evidence keeps its original historical field unchanged.

## Regression boundary

The focused regression runner uses temporary overlays and proves acceptance of:

1. the strict Step 1.01 active/pre-run controls;
2. Step 1.02 next immediately after Step 1.01;
3. the current Step 1.02-complete / Step 1.03-next state;
4. a consistent Step 1.04-next state;
5. a consistent Step 1.07-next state.

It rejects incomplete Step 1.01 state, missing accepted lineage, stale pre-run prose, regression to
Step 1.01, an unknown next package, impossible completed-step ordering, inconsistent documents, and
a missing strict pre-run control.

## Evidence and non-mutation

Approved execution writes a separate evidence run under:

```text
evidence/gates/gate-1/step01-audit-progression-compatibility/<run-id>/
```

It does not alter or repoint Step 1.01 contract evidence. It retains the reproduced predecessor
failure, progression regression result, predecessor audit logs, seeded-clean before/after snapshots,
repair installed-file checksums, summary, and evidence checksums. It verifies unchanged status
documents, contracts, schemas, accepted evidence, ADR-0006, dependencies, Drupal content, and source
hashes.

No model, provider, outbound network, API credit, Drupal mutation, configuration change, dependency
change, contract change, schema change, ADR, adapter, or Step 1.03 implementation is included.
