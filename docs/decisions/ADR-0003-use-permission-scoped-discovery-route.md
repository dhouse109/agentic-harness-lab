# ADR-0003: Use a permission-scoped Drupal discovery route for the shared target tool

- **Status:** Accepted
- **Decision date:** 2026-08-04
- **Evidence:** `evidence/logs/tools/find-images/step17-20260804T173030Z-851608`

## Context

The three framework specimens need the same deterministic target-discovery semantics before their
framework-owned orchestration diverges. Raw JSON:API reconstruction in each specimen would duplicate
Drupal access, image-field delta, file-reference, classification, ordering, and envelope behavior.
It would also make differences in client plumbing look like differences in the harnesses.

## Decision

Expose `find_images_needing_review()` through one custom, read-only Drupal route:

- `GET /api/agentic-harness/v1/images-needing-review`
- HTTP Basic authentication through Drupal core
- permission `use agentic harness discovery tools`
- granted to `agent_service` and denied to `editor_dana` and anonymous users
- entity-query, entity, field, and referenced-file access checks
- exact target identity: node UUID, current revision ID, field name, delta, and file UUID
- frozen shared tool envelope and target schema
- no model call and no source-content mutation

The shared Python client owns only HTTP/auth/envelope transport. Prompts, context assembly, model
calls, state, retries, interruption, recovery, human continuation, and sequencing remain framework-owned.

## Consequences

- All three later vertical slices start from the same 12-target Drupal projection.
- Step 17 can be tested independently of OpenAI availability or credit.
- The custom route is intentionally lab-specific: it fails closed if the seeded fixture no longer
  contains exactly 12 targets in the frozen 9-missing/3-poor distribution.
- This decision does not prove recommendation quality, framework behavior, or production readiness.
