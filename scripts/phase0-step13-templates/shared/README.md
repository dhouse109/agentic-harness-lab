# Shared Substrate Boundary

The shared directory exists to keep the comparison controlled. It may contain only behavior that
is genuinely common and deterministic across all three implementations.

## Allowed in `shared/`

- Drupal client and authentication helpers
- JSON Schemas and typed data contracts
- Deterministic fixtures
- Deterministic validators
- Common evidence and sanitized log formats
- Common evaluation fixtures and scoring rules
- The common failure trigger

## Framework-owned behavior must stay outside shared/

The following belong independently inside `drupal/`, `langchain/`, or `crewai/`:

- Context assembly
- Model calls
- Prompt orchestration
- Tool selection
- Framework state
- Checkpointing
- Human-interrupt behavior
- Recovery logic
- Workflow sequencing

A helper that merely renames framework-owned behavior is still framework-owned and must not move
into `shared/`.

## Review question

Before adding shared code, ask:

> Would centralizing this erase a meaningful difference in how the harness works?

If yes, keep it inside each framework implementation.
