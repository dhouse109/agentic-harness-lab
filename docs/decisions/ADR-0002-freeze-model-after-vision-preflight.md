# ADR-0002: Freeze model and image representation after the vision preflight

- **Status:** Accepted
- **Decision date:** 2026-08-04
- **Evidence:** `evidence/logs/preflight/vision/step16-20260804T164330Z-832871`
- **Supersedes:** the four controlled `PENDING_STEP_16` fields in `EXPERIMENT_SPEC.md` version 1.0

## Context

Phase 0 required one candidate model to pass an image-plus-page-context capability check through
Drupal AI, LangChain/LangGraph, and CrewAI before the model or image transport could be frozen.
The check also required schema-valid structured output, a harmless tool-call pathway, identical
synthetic input facts, and proof that Drupal source content was not mutated.

## Decision

Freeze the following experiment controls:

- Provider: OpenAI
- Exact model: `gpt-4.1-mini-2025-04-14`
- Temperature: `0.0`
- Image representation: identical inline PNG bytes and SHA-256 in every path; serialized as a
  Base64-encoded PNG data URL with `detail=auto` by the Python wrappers and as Drupal AI `ImageFile`
  over the same bytes by the Drupal provider wrapper
- Structured-output contract: strict JSON Schema where the wrapper exposes it; the exact observed
  wrapper mechanism is recorded in the Step 16 evidence
- Tool capability: Drupal AI detected a normalized call to the installed, non-mutating
  `ai_agent:html_to_markdown` FunctionCall plugin without executing it; LangChain and CrewAI each
  exposed and executed deterministic `calculate_probe`, returning `140`
- Fixture: the first deterministic Step 9 target, with identical image SHA-256 and page-context hash
  across all three pathways

The full Base64 image value and all credentials are runtime-only and are not retained in evidence.

## Consequences

- Comparative runs must use the same model snapshot, temperature, image bytes, page facts, and image
  representation.
- A later model or transport change requires another ADR and may invalidate prior comparison evidence.
- Step 16 proves capability only. It does not prove alt-text quality, comparative superiority,
  production readiness, or Step 17 target discovery.
- Approval and application remain separate; this spike creates no recommendation and changes no
  Article field.

## Fallback status

Direct image-plus-page-context capability passed through all three pinned pathways. The two-stage
fallback was not selected. The context-only fallback was not selected.
