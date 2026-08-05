# ADR-0005: Repair the get_image_context tool-result schema

- **Status:** Accepted
- **Decision date:** 2026-08-05
- **Decision owner:** Program lead
- **Supersedes:** only the incorrect `get_image_context` success branch in
  `shared/schemas/tool-result.schema.json`
- **Related decisions:** ADR-0001, ADR-0004

## Context

The documented and implemented `get_image_context(target)` success response is a shared tool-result
envelope whose `data` value directly conforms to `image-context.schema.json`:

```json
{
  "tool_name": "get_image_context",
  "ok": true,
  "data": {
    "schema_version": 1,
    "target": {},
    "article": {},
    "image": {},
    "existing_alt": "",
    "evidence_hash": "sha256:<digest>",
    "collected_at": "<date-time>"
  }
}
```

`docs/gates/GATE-0.5-STEP02-IMAGE-CONTEXT.md`, the Drupal route, the shared client, the Step 02
evaluator, both retained Step 05 success runs, and the Gate 0.5 handoff all use this direct-data
shape.

The `get_image_context` conditional branch in `tool-result.schema.json` incorrectly required an
additional `data.context` wrapper. Independent Draft 2020-12 validation exposed the mismatch after
the v1.0.0 Gate 0.5 boundary reconciliation run.

## Decision

Repair `tool-result.schema.json` so the successful `get_image_context` envelope's `data` property
references `image-context.schema.json` directly. Do not alter the certified operation, Drupal
response, shared client, or retained response bodies to introduce `data.context`.

Correct the active schema and every repository template that can recreate it. Add a permanent Step
05 audit regression using the already locked `jsonschema` 4.26.0 Draft 2020-12 validator in the
existing CrewAI uv environment. Using that validator for schema audit does not execute CrewAI or any
framework workflow.

The regression validates retained successful envelopes for all four shared operations and
specifically requires the direct `get_image_context.data` object to validate both through
`tool-result.schema.json` and independently through `image-context.schema.json`.

## Evidence and hash lineage

The committed historical run
`gate05-step05-20260805T010224Z-1100690` and the uncommitted boundary-reconciliation run
`gate05-step05-20260805T174126Z-18681` remain byte-for-byte unchanged. Their direct-data response
bodies are revalidated against the corrected schema.

The v1.0.0 reconciliation run is superseded and is not accepted as the final certification boundary
because its independent schema validation exposed this frozen-contract defect. A new Step 05 run is
required after the repair. It must regenerate the Step 05 freeze manifest and digest, update the
Step 14 contract hash registry, and retain the old and new hash lineage.

The affected contract hashes are:

- `shared/schemas/tool-result.schema.json`;
- `docs/decisions/step14-contract-sha256.txt`;
- the generated `shared/contracts/GATE05-SUBSTRATE-FREEZE.json` and digest;
- the new Step 05 run's frozen- and certification-file hash evidence.

## Unchanged experiment and operation boundary

This repair changes no provider, model, temperature, dataset, target identity or order, canonical
target, authentication, permission, deterministic validator behavior, idempotency identity, review
destination, failure seam, source-mutation prohibition, Drupal business logic, dependency version,
or observable shared-operation behavior.

No model call or framework-owned execution is introduced. Drupal AI, LangGraph, and CrewAI remain
uncertified by the substrate preflight. Gate 0.5 remains complete only at a passing, frozen shared
substrate handoff, and `gate-1-step01-drupal-ai-batch-contract-v1.0.0` remains the next package.

## Consequences

- The frozen contract schema matches the already documented and certified direct-data response.
- Historical evidence remains unchanged but becomes schema-valid under the repaired contract.
- A fresh Step 05 certification is mandatory before commit acceptance.
- ADR-0004 remains the controlling Gate 0.5 exit-boundary decision. Its earlier reservation of
  ADR-0005 for the Drupal AI runtime path is superseded only for numbering by this repair decision.
- The planned Drupal AI runtime-path ADR must use the next available number after ADR-0005,
  expected to be `ADR-0006`.
