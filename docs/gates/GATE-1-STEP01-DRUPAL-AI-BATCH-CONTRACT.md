# Gate 1 Step 1.01 — Drupal AI Batch Contract

## Decision

This step freezes the execution and evidence boundary for the Drupal AI 12-target batch. It adds no
framework implementation and makes no runtime claim.

The machine-readable contract is:

```text
shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json
```

Its digest is stored beside it in `GATE1-DRUPAL-AI-BATCH-CONTRACT.sha256`.

## Publication repair v1.0.1

The retained v1.0.0 evidence run `gate1-step01-20260805T200619Z-87483` is immutable and remains
auditable. It is superseded for publication because subsequent required checks found terminal blank
lines in ten newly introduced schemas and found that installed audit mode incorrectly required the
current branch to be `main`.

Version 1.0.1 normalizes every Step 1.01 JSON contract and schema to valid UTF-8 with exactly one
terminal newline. It also keeps run and package installation restricted to the exact `main`
predecessor while allowing installed audit mode on any branch that contains the approved predecessor
commit in its ancestry. Audit mode records the branch it evaluates. No schema, lifecycle, target,
framework-ownership, operation, frozen-constant, or package-sequence semantic changes are included.

## Authorized predecessor

- Branch: `main`
- Commit: `3016819f738a7db39fef0a6ccbb9cff0c8ec5fa0`
- Accepted Gate 0.5 evidence: `gate05-step05-20260805T184155Z-50124`
- Gate 0.5 freeze SHA-256: `99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a`

## Canonical entry-point schemas

The authoritative Drupal AI schemas are:

```text
shared/schemas/drupal-ai-run-state.schema.json
shared/schemas/drupal-ai-model-output.schema.json
```

`drupal-ai-run-state.schema.json` defines only the comparison-visible state the Drupal AI
implementation must own. It does not choose a Drupal storage API or location. No framework-owned
state may be placed in shared runtime storage. The runtime location and supported persistence path
remain a Step 1.02 decision.

`drupal-ai-model-output.schema.json` defines only the raw structured object returned by the model.
It contains the proposed alt text and no target metadata, validator outcome, submission result,
status observation, human decision, or chain of thought.

## Lifecycle-stage separation

Evidence must preserve these distinct stages and must not collapse them into one object:

1. Raw structured model output — `drupal-ai-model-output.schema.json`, collected by
   `batch-model-outputs.schema.json`.
2. Assembled recommendation — `recommendation.schema.json`, collected by
   `batch-recommendations.schema.json`.
3. Deterministic validator result — `batch-validation.schema.json`.
4. Submitted recommendation identifiers and initial state — `batch-submissions.schema.json`.
5. Read-only recommendation status observation — `batch-statuses.schema.json`.
6. Human review decision and revision lineage — `batch-human-review.schema.json`.

The summary may report whether a stage completed, but must not embed another stage's evidence.

## Frozen execution boundary

The Drupal AI implementation must own its model invocation, structured output, orchestration,
state, sequencing, interruption, persistence, and recovery. It must use the four certified shared
operations without a private read or write path.

The batch contract preserves:

- OpenAI `gpt-4.1-mini-2025-04-14` at temperature `0.0`
- framework origin `drupal_ai`
- exactly 12 targets in the certified sequence
- `gate05-validator-1.0.0`
- recommendation-only writes to revision-enabled `alt_text_suggestion` records
- human review by `editor_dana`
- no source Article or image-field mutation
- no automatic publication or application
- failure after target 6 is fully persisted and before target 7 begins
- same-run resume at target 7 with zero duplicate recommendations

## Required evidence files

Every later Drupal AI batch run must retain these sanitized artifacts under
`evidence/results/drupal_ai/<run-id>/`:

| Artifact | Authoritative schema |
|---|---|
| `run.json` | `shared/schemas/drupal-ai-run-state.schema.json` |
| `targets.json` | `shared/schemas/batch-target-sequence.schema.json` |
| `events.jsonl` | one `shared/schemas/batch-event.schema.json` object per line |
| `tool-traces.json` | `shared/schemas/batch-tool-traces.schema.json` |
| `model-outputs.json` | `shared/schemas/batch-model-outputs.schema.json` |
| `recommendations.json` | `shared/schemas/batch-recommendations.schema.json` |
| `validation.json` | `shared/schemas/batch-validation.schema.json` |
| `submissions.json` | `shared/schemas/batch-submissions.schema.json` |
| `statuses.json` | `shared/schemas/batch-statuses.schema.json` |
| `human-review.json` | `shared/schemas/batch-human-review.schema.json` |
| `recovery.json` | `shared/schemas/batch-recovery.schema.json` |
| `summary.json` | `shared/schemas/batch-summary.schema.json` |
| `summary.md` | concise human-readable summary |

Retained evidence may include structured model output, sanitized tool facts, validation outcomes,
recommendation and revision identifiers, state transitions, and reviewer decisions. It must not
include credentials, authorization headers, raw Base64 or data URLs, private configuration, hidden
reasoning, unrelated content, or private database exports.

## Repository-native Gate 1 package sequence

This sequence governs all later package generation together with the machine-readable Gate 1
contract:

1. Step 1.01 — batch contract
2. Step 1.02 — pinned Drupal AI runtime probe
3. Step 1.03 — thin Drupal AI tool adapters
4. Step 1.04 — canonical vertical slice
5. Step 1.05 — 12-target batch runner
6. Step 1.06 — batch evidence and human review
7. Step 1.07 — certification, freeze, and handoff

The Step 1.02 runtime-path decision must use the next available ADR number without overwriting any
existing decision. Because ADR-0004 and ADR-0005 exist, the number is currently expected to be
`ADR-0006`.

## Step boundary

Step 1.01 may create and audit only this contract, its schemas, documentation, and contract
evidence. It must not call a model, mutate Drupal state, change dependencies, recertify Gate 0.5,
change the frozen substrate, or implement Step 1.02.
