# ADR-0001: Freeze the Shared Experiment Contract

- **Status:** Accepted
- **Decision date:** 2026-08-03
- **Contract version:** 1.0
- **Supersedes:** the Step 13 draft `EXPERIMENT_SPEC.md`

## Context

The Drupal AI, LangChain/LangGraph, and CrewAI specimens must perform the same bounded task under
comparable conditions. Without a written contract, implementation convenience could silently alter
target identity, context facts, prompts, validation rules, review semantics, or the injected failure
point. That would turn the exercise into three demonstrations rather than a controlled comparison.

Phase 0 has already established the shared Drupal substrate: deterministic content, 12 exact target
field usages, least-privilege accounts, a revisioned recommendation queue, permission evidence, and
a proven `seeded-clean` reset. Step 14 freezes the contract that all later framework work must obey.

## Decision

Freeze version 1.0 of:

- the task and source-mutation boundary
- six-organ success criteria
- exact field-usage target identity
- four semantic tool contracts
- deterministic validator rules
- the 20-Article / 12-target dataset and manifest order
- comparative provenance and run-ID rules
- idempotency identity
- human-review semantics
- semantic prompt-fairness rules
- deliberate termination after completed item 6 and before item 7
- evidence paths and claim discipline

The frozen contract files are:

```text
EXPERIMENT_SPEC.md
shared/schemas/target.schema.json
shared/schemas/image-context.schema.json
shared/schemas/recommendation.schema.json
shared/schemas/tool-result.schema.json
shared/schemas/run-state.schema.json
shared/prompts/PROMPTS.md
docs/decisions/ADR-0001-freeze-experiment-contract.md
```

Their hashes are generated locally by:

```bash
bash scripts/run-phase0-step14.sh freeze confirm
```

and stored in:

```text
docs/decisions/step14-contract-sha256.txt
```

## Planned deferred decision

The exact model ID, confirmed structured-output mechanism, confirmed tool-calling mechanism, and
one image-input representation remain pending Step 16 capability testing. This is a controlled
deferral, not permission to change the semantic task.

Step 16 must record the result in:

```text
docs/decisions/ADR-0002-freeze-model-after-vision-preflight.md
```

and regenerate the contract hashes. All frameworks must then use the same selected model and
settings.

## Consequences

### Positive

- Later code can be reviewed against a stable fairness contract.
- Target drift and source mutation are explicit failures.
- The failure-and-resume comparison has one unambiguous midpoint.
- Framework-specific idioms remain visible without centralizing their behavior.
- Claims can point to stable schemas, prompts, and evidence rules.

### Trade-offs

- Convenience changes now require an ADR.
- Some implementation APIs may need thin adapters around the shared schemas.
- Model-specific transport details cannot be finalized until Step 16.
- Existing evidence must be rerun when a material contract change invalidates it.

## Rejected alternatives

### Let each framework define its own tool and output shapes

Rejected because differences in input and validation would prevent a fair comparison.

### Treat an image file as the target

Rejected because Drupal alt text belongs to a specific field item and can differ by content usage,
revision, and delta.

### Make approval automatically update the Article

Rejected because the experiment evaluates recommendation governance and human decision evidence.
Automatic application is a separate lifecycle capability and is outside scope.

### Choose the model before the image-plus-context spike

Rejected because an untested model path could force a late experiment redesign. The selection
protocol is frozen now; the exact model is frozen after Step 16 evidence.

## Change control

A material change requires a new ADR that identifies:

1. the changed contract element
2. the reason
3. the fairness impact
4. the evidence invalidated
5. the reruns required
6. the regenerated contract hash manifest
