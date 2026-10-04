# Gate 2C Final Closure and Disposition

## Decision

Gate 2C is terminally closed as:

```text
CLOSED_NON_CERTIFYING_WITH_INCOMPLETE_EVIDENCE
```

Step 2C.02 is terminally:

```text
TERMINAL_UNCERTIFIED
```

Gate 2 remains:

```text
NOT_COMPLETE
```

This is an evidence disposition, not a PASS, completion, certification, freeze, or
successful three-framework recovery result. It expresses two facts together: no
useful or authorized Gate 2C runtime work remains, and the Drupal predicates needed
for Step 2C.02 certification were not established.

## Governing source epoch

- Repository branch and predecessor: `main` at
  `03816e141f77820e42486fcbad9db244939cd7a8`, equal to `origin/main` when this
  package was prepared.
- Gate 2C contract:
  `shared/contracts/GATE2C-SHARED-FAILURE-RECOVERY-CONTRACT.json`, SHA-256
  `3c4801e6eb35d40d94e066c70017d3acebca95183e7e544646be6e2b40aa5ec6`.
- Final Step 2C.02 installed-source manifest SHA-256:
  `c6427eb6f1f78e102a56a117da02e903cf719214d2a2506a08fe3cbabec7ae1b`.
- Final Step 2C.02 permanent-audit SHA-256:
  `36404648cccb434c7d56ce6e575db1ec92fee17ec45e358c74a5dd8efe861dd9`.
- Complete retained `evidence/gates/gate-2c/` inventory at closure: 84 files,
  canonical path/size/SHA-256 inventory digest
  `a6f20ab3e45105d74bba13c21fdd51878435e4bc803febe98df7e55a2648c28c`.

## Evidence inventory

### Step 2C.01 contract certification

- Identity: `gate2c-step01-20260922T113303Z-fd9cdb75`.
- Evidence manifest SHA-256:
  `ed4444d95412b1450784c09eba80817d532cf7ed6a8ad96cd1bbbef179dd6190`.
- Result: model-free contract certification PASS. It froze the target-6/7 seam,
  overlays, accounting rules, protected-tree policy, and approval ledger. It did not
  execute recovery.

### Corrected-environment model-free rehearsal

- Identity: `gate2c-step02-offline-20260930T222029Z-24c7b158`.
- Evidence manifest SHA-256:
  `730b892d232a3dea7e77e4391b7beec5d40e807b76f99b13bb0036ae00cf74ca`.
- Finalization SHA-256:
  `d882c8339025c1ba7e510abb19984fc4724e2a594a190760c07f95db034fd8d8`.
- Result: finalized model-free PASS for LangGraph and CrewAI recovery mechanics.
  This was not an authoritative model-backed Gate 2C comparison.

### LangGraph outcome

- Termination evidence SHA-256:
  `e84425a8b86cca7ff2d78415cd5ddd63caa7140cc374ff4eb7dce41579953586`.
- Recovery evidence SHA-256:
  `071b4706c9ee1e24ed84734b94ada1dde1dfbcc743ec022cfb23aca0de184e9a`.
- The fresh model-free `SqliteSaver` specimen durably reached target 6, the external
  supervisor terminated the actual worker with signal 9, and public same-thread
  recovery began with target 7 and completed through target 12 with zero synthetic
  replay or duplicate identities.
- Gate 2A remains separately certified and frozen at
  `a28361c34b9d1c2089eee786324ad34cffbf54e3495f59a276c489865e5630f0`.
- Final Gate 2C wording: model-free recovery mechanics passed; no authoritative
  model-backed Gate 2C LangGraph recovery claim.

### CrewAI outcome

- Termination evidence SHA-256:
  `bc50b5c582f72b2133f6186ee0eb39488d452e509490c2a68f6e0e7406f84f14`.
- Recovery evidence SHA-256:
  `feb2c31832e43027f58f5d772710e2768591436fd8b393e89e02e63299ae2236`.
- Human decision SHA-256:
  `9b46330e3f9dd47bd4c8b7835db928335bde2447ca8825673cef77b9df6e7d1e`.
- The fresh model-free `SQLiteFlowPersistence` specimen used public
  `load_state(...)` and same-ID `Flow.kickoff(...)` hydration, recovered first at
  target 7, and completed through target 12 with zero synthetic replay or duplicate
  identities.
- The architecture is explicitly human-approved for the model-free proof only.
  Machine `APPROVAL_READY` and the human decision remain distinct.
- Gate 2B remains separately certified and frozen at
  `74e2baad0cbe612dcd7e72ccdc264b01960ee12e09cfb0ae3154969b6055c206`.
- Final Gate 2C wording: model-free recovery mechanics passed and the architecture
  was approved; no authoritative model-backed Gate 2C CrewAI recovery claim.

### Drupal outcome

Three immutable Drupal families remain failed-preserved:

| Identity | Aggregate SHA-256 | Disposition |
|---|---|---|
| `gate2c-step02-drupal-20261001T173201Z-545a1ba2` | `1014dacee5194fed8a2c696145d792898d5c9b9399f20c548bdd6e6cd4137714` | original start failed before valid lifecycle proof |
| `gate2c-step02-drupal-20261001T225458Z-c5d0e6b2` | `6ec105136d47f8b25a271c0950ff11984709b7e876e207b45dad7805ccde33c0` | replacement process-identity proof failed |
| `gate2c-step02-drupal-20261002T132121Z-a54c7a7a` | `cdd180a1c88de2fab50766e7bb82644dfd47fd51b57cca9a412985f15a67b08e` | final start crossed the signal-command boundary but failed the durable termination-proof gate |

The final family supports only these narrow observations:

- dedicated durable state contained sequences `[1,2,3,4,5,6]`;
- next target was 7 and target 7 had not started;
- exactly one expected PHP worker identity was verified before signaling;
- the exact-PID `SIGKILL` command returned success;
- the host wrapper returned and the worker was subsequently absent;
- no retry or replacement followed;
- the state persisted unchanged and processed identities remained unique.

It does not contain a certifying Drupal termination artifact or an immediate
post-kill observation. Therefore it does not establish historical durable
termination PASS, immediate lock denial, continuous lock retention to expiry,
post-kill recovery, target 7 as first actual restart work, replay-free continuation,
or completion through targets 7–12.

The single post-expiry partial observation is:

```text
evidence/gates/gate-2c/drupal-post-expiry-partial-observations/
  gate2c-step02-drupal-20261002T132121Z-a54c7a7a/observation.json
```

Its SHA-256 is
`2aab5b97540ed8efd79eb11e487ad8011977c758c54977b9dfcc8cdf49eae3f8`.
At `2026-10-03T15:41:01Z`, after the recorded natural expiry
`2026-10-02T14:19:31.691621Z`, the named lock was
`ACQUIRED_AFTER_RECORDED_EXPIRY`. Sequences remained `[1,2,3,4,5,6]`,
next target remained 7, target 7 remained unstarted and unprocessed, identities
remained unique, and before/after state SHA-256 remained
`3221a191c4be27649c9990ecbec18f12797db74616e59e8c7e47c0dd29a17e8c`.
Worker launches and target processing were zero. The record explicitly says
`certifying_evidence=false`, `immediate_lock_denial_reconstructed=false`, and
`historical_termination_proof_reconstructed=false`.

## Reset disposition

`RESET_NOT_PERFORMED` is terminally retained. Existing governance required a full
passing Drupal rehearsal before reset eligibility. That predicate was never met.
Closure does not create reset authority, and a cosmetic reset would not repair the
missing historical proof.

## No-more-runtime boundary

- additional worker identities permitted: `0`;
- replacement slots permitted: `0`;
- worker retry permitted: `false`;
- automatic retry permitted: `false`;
- partial-observation invocation count: `1`;
- maximum partial-observation invocations: `1`;
- Step 2C.03 activity: prohibited;
- Step 2C.02 certification: prohibited by the retained evidence gaps;
- pointer updates and new evidence identities: prohibited;
- Drupal reset: not authorized.

No worker, replacement, retry, second observation, replayed immediate observation,
failed-start retry, fabricated evidence, reset, certification, or pointer action is
authorized by this closure.

## Claims disposition

Permitted final claims are limited to the qualified statements in
`CLAIMS_REGISTER.md`, especially `CLM-G2C-001` through `CLM-G2C-004` and the
administrative closure statement `CLM-G2C-008`.

The following claims are prohibited:

- all three harnesses successfully recovered after SIGKILL;
- Drupal recovered or resumed at target 7;
- Drupal avoided replay after restart;
- Drupal completed targets 7–12;
- immediate post-failure lock denial was observed;
- continuous lock retention until natural expiry was proven;
- the post-expiry observation repairs historical termination or immediate evidence;
- Step 2C.02 passed or was certified;
- Gate 2C passed, completed successfully, or was certified;
- Gate 2 completed or passed;
- any recovery winner, framework superiority, or production-readiness conclusion.

## Gate 2 implication

The repository's Gate 2 umbrella contract requires the same controlled failure to
produce valid comparable evidence across all three frozen specimens. Drupal did not
produce a valid comparable recovery family. Closing Gate 2C administratively cannot
satisfy that missing evidence predicate. Gate 2 therefore remains `NOT_COMPLETE`.

## Permanent audit semantics

The final closure auditor must first execute the predecessor Step 2C.02 permanent
audit with a narrowly scoped successor-inventory compatibility layer. It then binds
the closure contract, source manifest, evidence tree, framework outcomes, three
Drupal aggregates, partial-observation SHA, claims register, comparison matrix,
documentation state, reset disposition, and no-more-runtime limits.

Its terminal markers are:

```text
STEP_2C_02_TERMINAL_UNCERTIFIED
GATE_2C_CLOSED_NON_CERTIFYING_WITH_INCOMPLETE_EVIDENCE
GATE_2_NOT_COMPLETE
RESET_NOT_PERFORMED
NO_MORE_GATE_2C_RUNTIME_AUTHORIZED
GATE_2C_FINAL_CLOSURE_AUDIT_PASS
```

The closure marker is explicitly non-certifying and cannot coexist with a Drupal
PASS, Step 2C.02 certification, Gate 2C PASS/certification, or Gate 2 completion
marker.
