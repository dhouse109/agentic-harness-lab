# Gate 1 Step 1.06 — Drupal AI Batch Evidence and Human Review

## Purpose

Turn the accepted Step 1.05 Drupal AI batch into defensible Gate 1 review evidence while preserving the separation between model generation and human judgment.

Accepted predecessor:

- Step 1.05 gate run: `gate1-step05-20260808T020222Z-2121689`
- Drupal AI batch run: `drupal_ai-20260808T020222Z-205fd9`
- merged baseline: `27029bdcd2eaf57146fca4f2f0358035c5c9008d`

Step 1.06 makes no model/provider request. The twelve Step 1.05 recommendations already exist in Drupal and begin this step pending review.

## Representative review sample

Exactly three recommendations are used:

| Sequence | Node | Human action |
|---:|---:|---|
| 1 | 21 | Approve unchanged |
| 6 | 26 | Reject unchanged |
| 12 | 32 | Edit proposed alt text and approve |

The early/mid/late sample is an implementation choice for evidence coverage, not a new frozen experiment constant.

## Human boundary

`editor_dana` performs every decision through Drupal's real `alt_text_suggestion` edit form. The runner does not POST a decision, impersonate the reviewer, or automate the edit.

For each selected recommendation, certification requires:

- every new human-review revision is authored by `editor_dana`;
- immutable provenance/target fields are unchanged;
- sequences 1 and 6 each add exactly one reviewer revision and retain the original proposed alt text;
- sequence 12 has a non-empty proposed alt text different from its generated value and ends approved;
- sequence 12 may use either one combined edit-and-approve revision or the explicitly recorded two-save edit-then-approve lineage retained by the v1.0.4 recovery patch;
- when sequence 12 uses the two-save lineage, the first reviewer revision remains pending with the edited alt text and the second approves without changing that edited text.

## Source non-mutation

The canonical full-Article projection hash from the existing Gate 0.5 read-only snapshot helper must remain:

`877cd888fa41eb660b3e3cc0461bee04c0b92bef7e8f2f63fc56d9ec77adde32`

The Step 1.05 reduced Article projection hash remains
`f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17`;
the two hashes describe different named projections and are not evidence of source drift.

The Article count remains 20. Review decisions must not modify source Article bodies, revisions, image file references, alt values, titles, or publication state.

## Evidence

The package adds Step 1.06 result evidence to the accepted Step 1.05 result directory and retains a separate Gate evidence package under:

`evidence/gates/gate-1/batch-evidence/<run-id>/`

Required Gate evidence includes predecessor audit output, accepted batch pointer, recommendation counts, revision lineage, reviewer decisions, source before/after hashes, secret scan, and summary.

The full Step 1.05 auditor is executed by the delivery package before Step 1.06 installation, because that historical auditor intentionally requires Step 1.06 source to be absent. After installation, the Step 1.06 runner validates the retained accepted Step 1.05 `final-audit.json` together with the live handoff state instead of rerunning an incompatible historical absence assertion. The retained predecessor audit is copied unchanged into `prior-package-audits.log` when the review evidence run is prepared.

## End state

After all review evidence is captured, Step 1.06 restores the exact DDEV snapshot taken before Step 1.05. The Drupal sandbox must return to 20 Articles, zero suggestions, unchanged Article hash, and the custom Step 1.05 module-disabled seeded-clean state. Retained evidence remains in Git.

Step 1.07 is then authorized to perform the fresh certification batch, idempotent replay proof, freeze manifest, and handoff.
