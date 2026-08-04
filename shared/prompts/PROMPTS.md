# Shared Semantic Prompt Contract

**Contract version:** 1.1  
**Status:** frozen with `EXPERIMENT_SPEC.md`; model transport and inline-image representation were frozen by ADR-0002

This file records the semantic instructions that must remain equivalent across Drupal AI,
LangChain/LangGraph, and CrewAI. Framework APIs may require different wrappers, message roles, or
serialization, but no implementation may receive richer task instructions or additional facts.

## 1. Model responsibility

The model performs one bounded task:

> Draft one concise, contextual alt-text recommendation for the supplied image-field usage.

The harness, not the model, owns target discovery, authorization, exact target identity, run ID,
framework provenance, evidence hashing, deterministic validation, submission, persistence,
review-state polling, failure injection, and recovery.

The model must not choose tools, mutate Drupal, approve work, apply alt text, or infer access to
facts that were not supplied.

## 2. Frozen semantic system instruction

```text
You draft one alt-text recommendation for one verified Drupal image-field usage.

Use only the supplied image and page context. Describe the image's meaningful content and purpose
in that context. Be concise and specific. Do not begin with "image of", "photo of", "picture of",
"graphic of", "Here is", or "Alt text:". Do not repeat the filename. Do not invent facts that are
not visible in the image or stated in the supplied page context.

Return only the structured model-output object required by
recommendation.schema.json#/$defs/model_output. The proposed_alt_text value must be nonempty and no
more than 250 Unicode characters.
```

## 3. Frozen semantic user template

Every implementation supplies the same facts under equivalent labels:

```text
TARGET
- Sequence: {{sequence}}
- Node UUID: {{node_uuid}}
- Article revision: {{revision_id}}
- Field: {{field_name}}
- Delta: {{delta}}
- File UUID: {{file_uuid}}
- Existing alt text: {{existing_alt_or_null}}

PAGE CONTEXT
- Article title: {{article_title}}
- Article body: {{article_body_plain}}

IMAGE CONTEXT
- Filename: {{filename}}
- MIME type: {{mime_type}}
- Dimensions: {{width_or_unknown}} x {{height_or_unknown}}
- Image input: identical PNG bytes, represented as a Base64-encoded PNG data URL with detail=auto or the Drupal AI ImageFile equivalent over the same bytes

Produce the model-output object only.
```

The image itself uses the Step 16-frozen inline representation: identical PNG bytes and SHA-256,
serialized as a Base64-encoded PNG data URL in the Python wrappers and as Drupal AI `ImageFile`
over the same bytes. The semantic facts remain identical regardless of wrapper syntax.

## 4. Structured output

The model-produced object contains only:

```json
{
  "proposed_alt_text": "..."
}
```

The object must validate against:

```text
shared/schemas/recommendation.schema.json#/$defs/model_output
```

The harness adds immutable target identity, real framework origin, run ID, evidence hash, and
validator version before validating the final recommendation object.

## 5. Required constants

The following may not differ between implementations:

- semantic system instruction
- supplied target and content facts
- selected model and generation settings
- selected image representation
- model-output contract
- 250-character experiment limit
- prohibited generic prefixes and filename echoes
- deterministic validators
- Drupal review destination
- failure point after item 6

## 6. Allowed framework-specific differences

Record a difference only when required by the framework's public API or execution model. Examples:

- system/user message object construction
- tool or task wrapper syntax
- JSON Schema registration syntax
- image-part serialization
- retry callback wiring
- state-key names
- graph, agent, Crew, or Flow wrapper instructions that do not add semantic task guidance

Allowed differences must not add content facts, quality hints, hidden retries, alternate length
limits, different examples, or framework-specific answers.

## 7. Prohibited prompt advantages

No implementation may receive:

- additional Drupal fields or unrelated content
- a prewritten answer pattern derived from another framework's run
- extra examples of acceptable output
- a different description of the image
- a different generic-text blacklist
- a different maximum length
- framework-specific encouragement to be more detailed, cautious, or creative
- hidden reviewer feedback from another run

## 8. Retry rule

A framework may retry only after a transport error, schema parse failure, or deterministic
validation failure. A retry receives the same semantic facts and may add only a machine-readable
statement of the failed deterministic rule. Retrying may not reveal another framework's output or a
human-authored replacement.

Record every retry and reason in `events.jsonl` and `validation.json`.

## 9. Prompt-difference register

Complete this table before comparative runs. `none` is a valid entry only after review.

| Framework | File or code path | Wrapper/API difference | Semantic effect | Approved by | Date |
|---|---|---|---|---|---|
| Drupal AI | `drupal/scripts/phase0-step16.php` | `ImageFile`, `setChatStructuredJsonSchema`, `setChatTools` | none; wrapper-only | Step 16 audit | 2026-08-04 |
| LangChain / LangGraph | `langchain/preflight/step16_capability.py` | Base64 `image_url`, `with_structured_output`, `bind_tools` | none; wrapper-only | Step 16 audit | 2026-08-04 |
| CrewAI | `crewai/preflight/step16_capability.py` | Base64 `image_url`, `LLM` response format, `LLM.call(tools=...)` | none; wrapper-only | Step 16 audit | 2026-08-04 |

Any material semantic effect requires an ADR and may invalidate prior comparison evidence.
