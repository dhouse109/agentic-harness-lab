# Implementation Plan

## Governing milestone

> One image, one recommendation, one human decision, three implementations.

Phase 0 exits into Gate 0.5. It does not yet prove complete framework-specific recovery or
production readiness.

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

## Gate 0.5

Each implementation must independently:

1. Retrieve one exact image-field usage.
2. Obtain permitted image and page context.
3. Invoke the frozen model.
4. Produce a schema-valid recommendation.
5. Write the recommendation to the shared Drupal review queue.
6. Preserve implementation origin and run ID.
7. Allow `editor_dana` to record a decision.

## Full implementation milestones

1. Foundation and frozen experiment contract.
2. Shared Drupal substrate and deterministic tools.
3. One-image vertical slices in all three implementations.
4. Batch processing and framework-owned state.
5. Human-review continuation behavior.
6. Shared failure injection and recovery evidence.
7. Comparison matrix, clips, screenshots, and claim review.
8. Deck, notes, rehearsal, and fallback package.

## Explicit conference-scope exclusions

- Automatic writes to production image fields
- General-purpose agent platform
- Vector database or semantic-search expansion
- Multiple-model comparison
- Performance or cost benchmarking
- Custom React dashboards
- Cloud deployment of all three implementations
- Complex multi-agent organization beyond the minimum CrewAI specimen
