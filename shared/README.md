# Shared Substrate Boundary

The shared directory exists to keep the comparison controlled. It may contain only behavior that
is genuinely common and deterministic across all three implementations.

## Certified semantic operations

```text
find_images_needing_review()
get_image_context(target)
submit_recommendation(recommendation)
get_recommendation_status(recommendation_id)
```

Their exact routes, permissions, schemas, validator version, implementation hashes, and retained
evidence lineage are recorded in:

```text
shared/contracts/GATE05-SUBSTRATE-FREEZE.json
shared/contracts/GATE05-SUBSTRATE-FREEZE.sha256
```

A material change to a frozen contract or substrate implementation requires:

1. an ADR explaining why comparison fairness remains intact
2. a new Gate 0.5 Step 05 certification run
3. a regenerated freeze manifest
4. framework wrappers updated against the new manifest

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
- Tool selection and binding
- Framework state
- Checkpointing
- Human-interrupt behavior
- Recovery logic
- Workflow sequencing

The shared client is transport, authentication, schema, validation, and Drupal queue infrastructure.
It is not an agentic harness. A helper that merely renames framework-owned behavior is still
framework-owned and must not move into `shared/`.

## Review question

Before adding shared code, ask:

> Would centralizing this erase a meaningful difference in how the harness works?

If yes, keep it inside each framework implementation.
