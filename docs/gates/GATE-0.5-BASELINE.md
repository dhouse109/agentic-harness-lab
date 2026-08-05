# Gate 0.5 Step 01 — Baseline and Preflight

## Governing milestone

> One image, one recommendation, one human decision, three implementations.

Step 01 establishes the baseline only.

## Completed-state audit decision

The legacy Step 17 shell wrapper chains through the Step 16 and Step 15 shell audits. Those older
auditors require the historical README phrase `Steps 13–15 are complete`, while the finalized
Phase 0 README correctly says `Phase 0 is complete` and `Gate 0.5 is next`.

Gate 0.5 therefore invokes `scripts/step17_audit.py` directly. This is not a relaxation of the
Step 17 controls. The dedicated auditor verifies the finalized Step 17 implementation, Drupal
inspection, 13/13 retained controls, target counts, permissions, contract hashes, secret hygiene,
source immutability, claims, sources, ADR, plan, and current README transition.

## Baseline method

1. Run the dedicated finalized-state Step 17 auditor.
2. Restore deterministic `seeded-clean`.
3. Audit the Phase 0 fixture.
4. Call `find_images_needing_review()` directly as `agent_bot`.
5. Confirm 12 targets in frozen order: 9 missing and 3 poor.
6. Confirm 20 Articles and zero `alt_text_suggestion` records.
7. Freeze sequence 1 as the canonical Gate 0.5 target.
8. Record Git, contract, schema, model, and target-sequence hashes.

## Evidence produced

```text
evidence/gates/gate-0.5/baseline/<run-id>/
  phase0-step17-finalized-audit.log
  reset.log
  phase0-step9-audit.log
  discovery-request.json
  discovery-response.json
  discovery-client.log
  targets.json
  canonical-target.json
  target-sequence-sha256.txt
  drupal-state.json
  retained-step17-evidence.txt
  contract-sha256.txt
  git-metadata.json
  summary.json
  summary.md
```

## Next step

Gate 0.5 Step 02 adds the deterministic `get_image_context(target)` operation.
