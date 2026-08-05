# Gate 0.5 Step 05 — Shared Substrate Certification and Framework Handoff

## Decision

This step certifies and freezes the framework-neutral substrate. It does **not** certify Drupal AI,
LangGraph, CrewAI, or overall Gate 0.5.

## Runtime proof

One reset-bounded controlled preflight must:

1. call `find_images_needing_review()` as `agent_bot`
2. require the exact 12-target order and canonical target 1
3. call `get_image_context(target)` and retain no image representation
4. require the passing Step 02 image and context hashes
5. call `submit_recommendation(recommendation)` once
6. replay the same submission identity without duplication
7. call `get_recommendation_status()` by UUID, node ID, and repeat read
8. require one unpublished `pending` recommendation
9. prove discovery, context, and status reads are non-mutating
10. prove only the recommendation queue changed
11. restore `seeded-clean` with zero suggestions
12. prove the complete Article and queue baseline returned exactly

The preflight uses the `drupal_ai` provenance enum branch because the frozen schema has no test-only
origin. Evidence must state that no Drupal AI framework execution or model call occurred.

## Lineage proof

The Step 05 audit must preserve the independent evidence chain:

```text
Step 01 → canonical target and frozen contracts
Step 02 → exact permitted image context
Step 03 → deterministic validation and idempotent submission
Step 04 → real human approval and read-only status observation
Step 05 → all four operations together and substrate freeze
```

## Freeze proof

The run generates:

```text
shared/contracts/GATE05-SUBSTRATE-FREEZE.json
shared/contracts/GATE05-SUBSTRATE-FREEZE.sha256
```

The manifest records:

- exact semantic operations, routes, methods, permissions, and schemas
- exact model and deterministic validator settings
- canonical target, image, and context hashes
- human-review evidence lineage
- hashes of the frozen schemas, Drupal tool implementation, client, queue configuration, and reset
  substrate
- the strict shared-versus-framework-owned boundary
- the three framework slices as not yet certified

Any material change requires an ADR and a new Step 05 run.

## Exit

After the standalone audit passes, the next work is the Drupal AI one-image vertical slice. Overall
Gate 0.5 remains open until Drupal AI, LangGraph, and CrewAI each use the frozen model and substrate
to produce one real reviewed recommendation.
