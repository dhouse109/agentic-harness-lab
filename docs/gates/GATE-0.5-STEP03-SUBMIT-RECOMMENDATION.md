# Gate 0.5 Step 03 — Deterministic Recommendation Submission

## Purpose

Implement and prove:

```text
submit_recommendation(recommendation)
```

The route accepts one assembled object conforming to `recommendation.schema.json`. It performs
deterministic validation, verifies the exact current field usage, and creates one unpublished
`alt_text_suggestion` in `pending` review state.

## Authorization

The route requires Drupal's existing bundle permission:

```text
create alt_text_suggestion content
```

`agent_bot` has this permission. Anonymous users and `editor_dana` do not.

## Validation boundary

The shared validator rejects:

- malformed recommendation and target shapes
- unsupported framework provenance
- malformed or source-mismatched run IDs
- malformed evidence hashes and validator versions
- stale Article revisions, fields, deltas, or file references
- empty or overlong text
- filename echoes
- generic placeholders
- duplicates of the current alt text
- obvious model preambles

## Idempotency

The identity is:

```text
source framework
+ run ID
+ node UUID
+ Article revision
+ field
+ delta
+ file UUID
```

An exact replay returns the same recommendation node and revision. The same identity with different
submission data fails closed.

## Mutation boundary

The operation creates only a recommendation record. It never edits the Article or image field.

The Step 03 package uses one controlled, model-free payload, inspects the pending node, and then
restores `seeded-clean`. Retained evidence explicitly states that this is not a framework result.
