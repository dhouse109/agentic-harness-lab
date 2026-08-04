# Experiment Specification

**Contract status:** ready to freeze — version 1.0  
**Model status:** candidate — pending Step 16 vision and tool-path preflight  
**Allowed deferred model fields:** exact model ID, confirmed structured-output mechanism, confirmed tool-calling mechanism, and image-input representation

Do not implement framework-owned agent orchestration until this contract passes the Step 14 audit
and is frozen. After freeze, material changes require an ADR.

## 1. Task and boundary

Each implementation processes the same 12 deterministic Drupal image-field usages in the same
order. For every target, it must:

1. retrieve the exact authorized field usage
2. obtain the permitted image and page context
3. invoke the same frozen multimodal model
4. produce one structured alt-text recommendation
5. pass the same deterministic validators
6. create one pending `alt_text_suggestion` record in the shared Drupal review queue

The implementations create recommendation records only. They must not directly alter the source
Article's `field_image` item or any other production content field.

### Definitions

- **Target:** one exact Drupal image-field usage, identified by node UUID, Article revision ID,
  field name, field delta, and file UUID. A file by itself is not a target.
- **Recommendation:** a validated proposed alt-text value plus immutable target identity,
  framework origin, run ID, and evidence hash.
- **Approved:** a human reviewer accepted the recommendation record.
- **Applied:** a later operation copied an approved value into source content. Application is
  outside this experiment; approval does not imply application.

### Scope exclusions

- automatic source-field mutation
- production publishing
- general-purpose agent-platform features
- vector search
- multiple-model comparison
- cost or performance benchmarking
- custom dashboard development
- chain-of-thought capture

## 2. Success criteria by harness organ

### Context

Success means the implementation assembles only the context permitted for the current target:

- target identity and sequence number
- Article title
- Article body converted to plain text
- exact Article revision ID
- image bytes or the Step 16-approved equivalent representation
- image filename, MIME type, dimensions, byte length, and SHA-256 hash when available
- existing alt text

Before model invocation and again before submission, the implementation verifies that the Article
revision, field, delta, and file still match the frozen target. A stale or unauthorized target
fails closed. Unrelated content, configuration, credentials, and other runs' reviewer decisions are
not supplied to the model.

### Tools

Success means all four semantic tools conform to the shared contracts and schemas:

- `find_images_needing_review()`
- `get_image_context(target)`
- `submit_recommendation(target, proposed_alt_text, run_id)`
- `get_recommendation_status(recommendation_id)`

All Drupal calls use `agent_bot`. The tool layer must preserve exact field-usage identity, return
structured results, surface errors without leaking secrets, and enforce recommendation-record-only
mutation. Framework-specific wrappers may differ; semantic behavior may not.

### State and memory

Success means each implementation owns and persists enough state to identify one run and resume it:

- run ID and framework origin
- frozen ordered target sequence
- next target index
- completed target identities
- created recommendation identifiers
- validation outcomes
- failure-injection state
- start, update, interruption, and resume timestamps

Restarting the same run must retain the same run ID and must not create a duplicate recommendation
for an already completed target. A new run ID represents a separate experiment run.

### Verification

Success means every final recommendation validates against the shared JSON Schema and deterministic
rules. The validator must reject malformed JSON, stale targets, nonexistent fields or deltas,
changed file references, empty or overlong alt text, filename echoes, generic placeholders,
duplicates of the current alt text, and model preambles. The deliberately poor Step 9 values must
trip the relevant rules.

Validation must also prove that submission created only an `alt_text_suggestion` record in
`pending` state and did not mutate the source Article.

### Human review

Success means the recommendation arrives in the shared Drupal queue as `pending`, carries its real
framework origin and run ID, and can be approved, rejected, or edited and approved by
`editor_dana`. Drupal revision evidence must preserve reviewer identity, timestamp, prior and
edited text, status transition, target revision, and origin.

Approval records a human decision on the recommendation. It does not apply the alt text to the
source Article during this experiment.

### Lifecycle and recovery

Success means the same deliberate failure occurs after target 6 has been validated, submitted, and
persisted, but before target 7 begins. After process restart, the implementation retains the same
run ID, resumes with target 7, avoids duplicate recommendations for targets 1–6, completes targets
7–12, and emits inspectable recovery evidence.

The failure trigger is shared. Persistence, checkpointing, recovery orchestration, and audit linkage
remain framework-owned behavior.

## 3. Candidate model and settings

| Setting | Frozen or deferred value |
|---|---|
| Provider | OpenAI |
| Exact model ID | `PENDING_STEP_16` — select only after image-plus-page-context preflight |
| Temperature | `0.0` candidate; Step 16 must confirm support and identical use in all three paths |
| Structured-output mechanism | `PENDING_STEP_16` — prefer native strict JSON Schema support; document any deterministic fallback |
| Tool-calling mechanism | `PENDING_STEP_16` — record the exact provider/framework binding used by each path |
| Image-input representation | `PENDING_STEP_16` — one representation must be selected and reused in all three paths |
| Model status | candidate — pending Step 16 vision and tool-path preflight |

### Model-freeze protocol

Step 16 must prove that one exact model can accept the selected image representation plus page
context and return schema-conforming output through every required provider path. Once selected:

- record the exact model ID and settings in `VERSIONS.md`
- record the selected image representation and mechanisms in a new ADR
- update this table through that ADR
- use the identical model and generation settings in every comparison run
- do not switch models between framework runs

A model-selection change after Step 16 is a material experiment change.

## 4. Shared tool contract

JSON Schemas are stored under `shared/schemas/`.

### `find_images_needing_review()`

**Input:** no model-generated input. Optional harness metadata may include run ID and correlation ID.

**Output:** exactly the 12 deterministic targets, in the byte-stable Step 9 manifest order, each
conforming to `target.schema.json`.

**Rules:**

- no model call anywhere in the path
- permission-aware Drupal retrieval as `agent_bot`
- no framework-specific reordering
- target identity refers to field usage, not generic file ID

### `get_image_context(target)`

**Input:** one object conforming to `target.schema.json`.

**Output:** one object conforming to `image-context.schema.json`.

**Rules:**

- verify node UUID, exact revision, field, delta, and file before returning context
- return only the permitted Article and image facts listed in Section 2
- fail closed on drift, missing access, or malformed identity
- compute a sanitized evidence hash without storing credentials or chain of thought

### `submit_recommendation(target, proposed_alt_text, run_id)`

**Input:** exact target identity, model-produced alt text, real framework origin, run ID, and
evidence hash. The assembled record conforms to `recommendation.schema.json`.

**Output:** recommendation node ID, UUID, revision ID, status, origin, run ID, and target identity
inside the appropriate `tool-result.schema.json` envelope.

**Rules:**

- run deterministic validation before mutation
- create one `pending` `alt_text_suggestion`
- never update the source Article
- refuse stale targets
- be idempotent within one run and target identity

### `get_recommendation_status(recommendation_id)`

**Input:** Drupal recommendation UUID or node ID plus run correlation data.

**Output:** current `pending`, `approved`, or `rejected` status, current recommendation revision,
and permitted reviewer metadata inside `tool-result.schema.json`.

**Rules:**

- read-only
- does not approve, reject, edit, or apply anything
- does not expose credentials or unrelated reviewer data

## 5. Deterministic validators

A recommendation passes only when all checks succeed:

1. final object is valid structured JSON
2. object conforms to `recommendation.schema.json`
3. source framework is one of `drupal_ai`, `langgraph`, or `crewai`
4. run ID conforms to `<framework>-<UTC timestamp>-<short suffix>`
5. node UUID and exact Article revision exist
6. target field exists and is an image field
7. target delta exists
8. recorded file UUID still occupies that delta
9. proposed alt text is nonempty after trimming
10. proposed alt text is no more than 250 Unicode characters
11. proposed alt text is not a filename or filename echo
12. proposed alt text is not a generic placeholder such as `image`, `photo`, `picture`, or `graphic`
13. proposed alt text does not duplicate the current alt text after normalized comparison
14. proposed alt text does not contain an obvious model preamble such as `Here is` or `Alt text:`
15. submission creates only a recommendation record
16. initial review status is `pending`
17. source Article revision and image-field value remain unchanged
18. an explicit human decision is required before any later application step

`250` characters is an experiment limit for consistent validation. It is not presented as a
universal accessibility rule.

## 6. Dataset and ordering

- 20 deterministic seeded Article nodes
- 30 generated PNG files
- 12 deterministic target image-field usages
- 9 missing-alt targets
- 3 deliberately poor-alt targets
- 8 Articles with acceptable alt coverage
- reset to `seeded-clean` before every comparison run
- process targets in the exact order returned by the stored Step 9 manifest

No implementation may reorder targets by file ID, confidence, framework preference, or model
output. Dataset changes require a new baseline, updated schemas or fixtures as needed, and an ADR.

## 7. Provenance and idempotency

Comparative runs use only these origins:

- `drupal_ai`
- `langgraph`
- `crewai`

`phase0_fixture` is reserved exclusively for setup, reset, permission, and revision tests. It must
not appear in comparative framework-run evidence.

Run IDs use:

```text
<framework>-<UTC timestamp>-<short random suffix>
```

Example:

```text
langgraph-20260805T013015Z-a91f
```

The idempotency identity is:

```text
framework origin
+ run ID
+ node UUID
+ Article revision ID
+ field name
+ field delta
+ file UUID
```

A resumed run retains its original run ID. A separate execution with a new run ID may create a new
recommendation for the same target.

## 8. Semantic prompt fairness

These remain constant across implementations:

- task and success criteria
- target sequence and input facts
- candidate/frozen model and generation settings
- model-output contract
- final recommendation schema
- deterministic validators
- Drupal review destination
- failure point after item 6

Framework-specific orchestration wording may differ only where the framework's API or execution
model requires it. Every prompt, wrapper, and material difference is recorded in
`shared/prompts/PROMPTS.md` before comparative runs.

No implementation receives a richer semantic prompt, additional content facts, hidden retry
instructions, or a different validation threshold.

## 9. Failure definition

The shared failure injector terminates the process immediately after target **6** has:

1. received permitted context
2. produced a model result
3. passed deterministic validation
4. created its recommendation
5. persisted completion state

Termination occurs before target 7 begins.

Expected recovery evidence:

- targets 1–6 are already complete
- the same run ID is retained
- restart begins with target 7
- no recommendation for targets 1–6 is duplicated
- targets 7–12 complete
- interruption and resume timestamps are retained
- framework-owned persistence and resume mechanism are visible

The trigger itself may be shared. Framework persistence and recovery logic may not be centralized in
`shared/`.

## 10. Evidence contract

Each run retains:

- framework origin and run ID
- UTC start, interruption, restart, and completion times
- exact package, Drupal, provider, and model versions
- frozen target sequence
- sanitized tool inputs and outputs
- validation outcomes
- created recommendation identifiers
- failure point and persisted state before termination
- resumed target
- duplicate count
- final completed and failed counts
- sanitized errors

Store comparative evidence under:

```text
evidence/results/<framework>/<run-id>/
```

Recommended files:

```text
run.json
events.jsonl
targets.json
recommendations.json
validation.json
recovery.json
summary.md
```

Do not record credentials, authorization headers, raw private configuration, chain of thought, or
unrelated Drupal content. Do not present elapsed time, token usage, or cost as comparative findings
without a future scoped amendment.

## 11. Claims and version discipline

Every major claim requires:

1. current official documentation
2. exact pinned version or commit
3. repeatable local test ID
4. retained log, screenshot, clip, or code reference
5. safe wording in `CLAIMS_REGISTER.md`

A claim remains a hypothesis until local evidence exists. It becomes verified only when local
evidence is paired with a current official source. Unsupported claims are marked `unsupported` and
must not appear in the talk as findings.

## 12. Change control

After freeze, any material change to the task, target identity, dataset, ordering, schemas,
validators, model, settings, context facts, prompt contract, review destination, failure point, or
idempotency rule requires:

1. an ADR under `docs/decisions/`
2. an explanation of fairness impact
3. regenerated Step 14 contract hashes
4. rerun of any invalidated evidence

The expected Step 16 model completion is the single planned deferred update. Record it in
`ADR-0002-freeze-model-after-vision-preflight.md`; do not silently edit the contract.
