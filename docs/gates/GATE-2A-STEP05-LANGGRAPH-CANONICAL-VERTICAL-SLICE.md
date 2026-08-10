# Gate 2A Step 2A.05 — LangGraph Canonical Vertical Slice

**Package:** `gate-2a-step05-langgraph-canonical-vertical-slice-v1.0.0`

## Purpose

Prove one real canonical target through the LangGraph specimen end to end across
context retrieval, one frozen model invocation, deterministic verification,
recommendation submission, pending-status observation, and framework-owned
SQLite checkpoint state.

This is deliberately **not** the 12-target batch and **not** the human-review
interrupt/resume step.

## Frozen boundary

Step 2A.05 preserves:

- canonical target sequence SHA-256
  `1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728`;
- Article source SHA-256
  `f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17`;
- model `gpt-4.1-mini-2025-04-14`;
- temperature `0.0`;
- LangGraph prompt version `langgraph-alt-text-v1.0.0`;
- validator `gate05-validator-1.0.0`;
- source framework `langgraph`;
- review destination `alt_text_suggestion`;
- recommendation-only mutation;
- no source Article/image-field mutation;
- no automatic publication.

The successful Step 2A.05 call budget is exactly one model invocation with
`ChatOpenAI(max_retries=0)` and no semantic retry loop.

## Canonical sequence

One successful candidate performs these semantic operations in order:

1. `find_images_needing_review()` and require the exact accepted 12-target list;
2. select canonical target sequence `1`;
3. `get_image_context(target)` immediately before the model call;
4. call the frozen multimodal model exactly once using strict JSON-schema output;
5. `get_image_context(target)` again immediately before submission and require
   the same stable evidence hash;
6. run deterministic pre-submit validation;
7. `submit_recommendation(...)` exactly once;
8. `get_recommendation_status(...)` and require `pending` with no reviewer yet;
9. `get_image_context(target)` after submission and require the same source
   context evidence hash;
10. persist only the frozen LangGraph run-state fields to SQLite.

Expected successful Drupal semantic call counts are therefore:

- discovery: `1`;
- image context: `3`;
- recommendation submission: `1`;
- recommendation status: `1`;
- total: `6`.

## Prompt and structured output

The system/user semantics mirror the frozen Gate 1 specimen. The model produces
only:

```json
{"proposed_alt_text": "..."}
```

The raw object must validate against
`shared/schemas/langgraph-model-output.schema.json`. The assembled recommendation
must validate against `shared/schemas/recommendation.schema.json` and then pass
the deterministic rules before the authoritative Drupal submit operation is
called.

## Ephemeral context and checkpoint privacy

The permitted Article body and image data URL are available to the model only as
ephemeral node-local values. They are not LangGraph state channels.

The checkpoint privacy proof scans both the serialized state and the SQLite file
for:

- the exact Article body value;
- the exact image representation value;
- the exact runtime Drupal password;
- the exact runtime OpenAI API key;
- generic credential/data-URL/hidden-reasoning patterns.

Only sanitized context hashes/lengths are retained as evidence. Raw Base64/data
URLs, credentials, authorization headers, and hidden reasoning are prohibited.

## State after one target

The specimen state remains `running`, not `completed`, because the frozen run
contains twelve targets. After the slice it must show:

- `next_target_index == 1`;
- completed target sequence `[1]`;
- one recommendation identifier;
- one deterministic validation result;
- `continuation_boundary_armed == false`;
- `continuation_boundary_reached == false`;
- `gate2c_failure_injection_fired == false`.

Step-package completion and full specimen-run completion are intentionally
distinct concepts.

## Reset-bounded Drupal evidence

The live runner begins from the seeded-clean substrate, creates an exact DDEV
snapshot, runs the single-target slice, captures the during-run Drupal
projection, and restores the exact snapshot before candidate acceptance.

A successful candidate requires:

- recommendation count transition `0 -> 1 -> 0`;
- Article source SHA unchanged before/during/after;
- target-sequence SHA unchanged before/during/after;
- final seeded-clean audit pass.

The recommendation is real during the observation but temporary after the exact
snapshot restore. Human review is therefore deferred to Step 2A.06.

## Evidence lifecycle

Evidence root:

`evidence/gates/gate-2a/canonical-slice/`

Pointers:

- `GATE2A-STEP05-LAST-RUN.txt` — every attempted live run;
- `GATE2A-STEP05-FAILED-RUNS.txt` — retained failed attempts;
- `GATE2A-STEP05-CANDIDATE.txt` — passing inspected candidate;
- `GATE2A-STEP05-LATEST.txt` — created only by later model-free certification.

A failed live attempt is retained and the same package refuses another live run.
Human review/package repair is required before any retry, matching the frozen
model-call policy.

A passing live run stops at candidate state. Certification is a separate human
gate and makes zero model, Drupal, or recommendation-write calls.

## Pass criteria

Step 2A.05 passes only when the retained candidate proves:

- exactly one successful model invocation;
- zero configured automatic model retries;
- no semantic retry loop;
- the exact canonical target sequence `1`;
- both pre-model and pre-submit target freshness;
- raw model-output schema validity;
- deterministic validation pass;
- exactly one pending recommendation submission;
- pending status observed read-only;
- source context unchanged after submission;
- SQLite checkpoint state at next target index `1`;
- no raw Article body/image data URL/credentials/hidden reasoning in checkpoint;
- source Article projection unchanged;
- no automatic publication;
- Drupal restored to seeded-clean after the observation.

This step does **not** prove human review/resume, 12-target continuation,
Gate 2C failure/recovery, framework superiority, or production readiness.

**Next package after commit/merge/resync/post-merge audit:**

`gate-2a-step06-langgraph-human-interrupt-and-review-resume-v1.0.0`
