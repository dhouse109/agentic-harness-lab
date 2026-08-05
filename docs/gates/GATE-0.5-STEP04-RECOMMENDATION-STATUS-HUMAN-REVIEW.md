# Gate 0.5 Step 04 — Recommendation Status and Human Review

## Purpose

Implement and prove:

```text
get_recommendation_status(recommendation_id)
```

The operation reads one recommendation by UUID or node ID and returns only:

- recommendation UUID
- current recommendation revision ID
- `pending`, `approved`, or `rejected`
- permitted reviewer username
- permitted review timestamp

It does not approve, reject, edit, publish, or apply content.

## Route and authorization

```text
GET /api/agentic-harness/v1/recommendations/{recommendation_id}/status
```

The route requires the existing `use agentic harness discovery tools` permission. `agent_bot` can
read status. Anonymous users and `editor_dana` cannot use the agent-facing status route.

The separation is intentional:

- `editor_dana` makes a decision through Drupal's editorial form.
- `agent_bot` observes the resulting status through the shared semantic tool.

## Human-review proof

Step 04 is two-stage:

1. Create one controlled pending recommendation for canonical target 1.
2. Observe `pending` by recommendation UUID and node ID.
3. Pause for a real Drupal save by `editor_dana`.
4. Require exactly one new recommendation revision.
5. Require the latest revision user to be `editor_dana`.
6. Require the transition `pending → approved`.
7. Require proposed alt text, target identity, framework origin, run ID, and evidence hash to remain
   unchanged.
8. Observe `approved`, reviewer username, timestamp, and current revision through the read-only
   status operation.
9. Restore `seeded-clean`.

Approval remains separate from application. The source Article is never changed.
