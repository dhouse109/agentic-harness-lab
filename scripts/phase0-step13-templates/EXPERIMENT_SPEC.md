# Experiment Specification

**Status:** draft — complete and freeze during Phase 0 Step 14  
**Model status:** candidate — pending vision and tool-path preflight

Do not implement framework-owned agent orchestration until this document is complete.

## 1. Task

Find target Drupal image-field usages with missing or inadequate alt text, assemble permitted image
and page context, draft a remediation recommendation, validate it, and submit it to the common
Drupal review queue.

## 2. Success criteria by harness organ

### Context

- TODO

### Tools

- TODO

### State and memory

- TODO

### Verification

- TODO

### Human review

- TODO

### Lifecycle and recovery

- TODO

## 3. Candidate model and settings

| Setting | Value |
|---|---|
| Provider | TODO |
| Exact model ID | TODO |
| Temperature | TODO |
| Structured-output mechanism | TODO |
| Tool-calling mechanism | TODO |
| Image-input representation | TODO — freeze only after Step 16 |
| Status | candidate — pending vision and tool-path preflight |

## 4. Shared tool contract

Target identities refer to exact field usages, not generic files.

```text
find_images_needing_review()
get_image_context(target)
submit_recommendation(target, proposed_alt_text, run_id)
get_recommendation_status(recommendation_id)
```

Store schemas under `shared/schemas/`.

## 5. Deterministic validators

The shared deterministic layer must validate:

- structured JSON
- existing content entity and exact revision
- existing field and valid delta
- existing file or media reference
- non-empty proposed alt text and maximum length
- no filename echo
- no generic placeholder
- no duplicate of existing alt text
- recommendation-record-only mutation
- explicit human decision before any later application step

## 6. Dataset

- 20 deterministic seeded Articles
- 12 deterministic image-field target usages
- reset to `seeded-clean` before every comparison run

## 7. Semantic prompt fairness

Keep constant across implementations:

- task
- input facts
- model and settings
- output schema
- deterministic validators
- Drupal review destination
- injected failure point

Framework-specific orchestration wording may differ only where required by the framework. Record
all prompts and material differences in `shared/prompts/PROMPTS.md`.

## 8. Failure definition

Inject the same deliberate process termination after target item **N = TODO**.

The trigger is shared. Each framework owns its own persisted state, recovery behavior,
duplicate-work avoidance, resume mechanism, and audit linkage.

## 9. Evidence rules

Every major claim requires:

1. current official documentation
2. pinned version or branch
3. repeatable local test ID
4. retained log, screenshot, clip, or code reference
5. safe wording in `CLAIMS_REGISTER.md`

## 10. Change control

After freeze, record any material change to task, model, schemas, validators, target dataset,
failure point, or review destination in `docs/decisions/` before continuing.
