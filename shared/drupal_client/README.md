# Shared Drupal client

This directory contains the framework-neutral HTTP boundary for the lab's shared Drupal substrate.

It may own:

- Drupal URL and HTTP Basic authentication handling
- correlation IDs
- request/response envelope transport
- sanitized HTTP errors

It must not own:

- prompts or model calls
- LangGraph graphs or checkpoints
- CrewAI crews, flows, or role decomposition
- Drupal AI agent orchestration
- framework retry, recovery, sequencing, or persistence behavior

Implemented deterministic operations:

- `find_images_needing_review()` — returns the frozen ordered 12-target sequence
- `get_image_context(target)` — verifies one exact field usage and returns only permitted Article
  and image facts, including the runtime-only Step 16-approved image representation
- `submit_recommendation(recommendation)` — validates provenance, target freshness, alt-text rules,
  and idempotency before creating one unpublished recommendation in `pending` review state
- `get_recommendation_status(recommendation_id)` — returns only the current recommendation
  revision, review status, and permitted reviewer metadata; it never performs a review action

The three framework implementations may use this client for transport. Each framework still owns
its context assembly for the model, model invocation, orchestration, state, verification,
human-continuation behavior, and recovery.
