# Agentic Harness Lab — Project Plan

## Current phase

**Engineering and evidence collection are complete.**

The project has moved from implementation to **conference production and publication**.

Immutable engineering checkpoint:

```text
15e50615f5c525d9c6ed937fe607b3f009898f10
Close Gate 2C with terminal non-certifying evidence
```

Formal terminal status:

- Gate 1 / Drupal AI: certified and frozen.
- Gate 2A / LangGraph: certified and frozen.
- Gate 2B / CrewAI: certified and frozen.
- Gate 2C: `CLOSED_NON_CERTIFYING_WITH_INCOMPLETE_EVIDENCE`.
- Step 2C.02: `TERMINAL_UNCERTIFIED`.
- Gate 2 umbrella: `NOT_COMPLETE`.
- Gate 2C runtime: closed; no further runtime authorized.

The engineering phase is therefore **finished**, while the Gate 2 umbrella remains formally
incomplete because its three-framework recovery exit criterion was not satisfied.

See `docs/CURRENT-STATUS.md` for the authoritative concise status and
`docs/POST-CLOSURE-PUBLICATION-BOUNDARY.md` for the post-closure editing rules.

## Project objective

Build the same governance-sensitive Drupal task in three agentic harnesses and compare the
infrastructure around the model.

Shared task:

> Find Drupal pages with missing or inadequate image alt text and create validated remediation
> recommendations for editor review.

The comparison is organized around six harness organs:

1. context control;
2. tools and integrations;
3. state and memory;
4. verification and guardrails;
5. human review and approval;
6. lifecycle and recovery.

The project is a comparative engineering experiment, not a framework contest. Evidence controls
the conclusions.

## Frozen comparison boundary

The implementations share:

- the same 20-Article deterministic Drupal fixture;
- the same 12 frozen target usages and order;
- the same OpenAI model snapshot and temperature;
- the same output schema and deterministic validator;
- the same four semantic Drupal operations;
- the same revision-enabled Drupal review queue;
- the same source-nonmutation rule;
- the same target-6/7 lifecycle seam.

Framework-owned behavior remains framework-owned: context assembly, orchestration, state,
checkpointing/persistence, interruption, recovery, and sequencing.

See `EXPERIMENT_SPEC.md`.

## Completed engineering milestones

### Phase 0 — platform and experiment substrate

Complete.

Established:

- Drupal roles/service accounts;
- deterministic fixture and reset;
- recommendation review queue;
- permission tests;
- model and image-input freeze;
- shared schemas and validators;
- reproducible evidence structure.

### Gate 0.5 — shared Drupal substrate

Complete and certified.

Certified operations:

```text
find_images_needing_review()
get_image_context(target)
submit_recommendation(recommendation)
get_recommendation_status(recommendation_id)
```

The substrate provides the common Drupal boundary used by all three specimens.

### Gate 1 — Drupal AI

Complete, certified, and frozen.

The Drupal AI specimen demonstrated the full 12-target model-backed path, framework-owned run state,
validation/submission, and real Drupal human-review lineage.

### Gate 2A — LangGraph

Complete, certified, and frozen.

The LangGraph specimen demonstrated code-first tool wrappers, `SqliteSaver` checkpoint state,
model-backed batch execution, and persisted interrupt/resume around the authoritative Drupal review
queue.

### Gate 2B — CrewAI

Complete, certified, and frozen.

The CrewAI specimen demonstrated supported Flow persistence, CrewAI-native tool adapters,
model-backed batch execution, and public pending-flow reconstruction/resume around the authoritative
Drupal review queue.

### Gate 2C — shared failure and recovery

Terminally closed, non-certifying.

The corrected-environment model-free recovery rehearsal supported the selected LangGraph and CrewAI
recovery mechanics.

The Drupal run retained valuable partial evidence at the same seam but did not establish the full
certifying termination and recovery-continuation predicates.

Therefore Gate 2C did not pass and Gate 2 did not meet its umbrella exit criteria.

The final engineering decision is **not** to retry or rewrite the experiment for a cleaner result.

## Current production plan

### Phase A — evidence-to-slide map

For each of the six organs, identify:

- the teaching point;
- Drupal AI evidence;
- LangGraph evidence;
- CrewAI evidence;
- genuinely comparable behavior;
- framework-specific behavior;
- strongest safe claim;
- required qualification;
- best presentation medium;
- exact repository source/evidence paths.

Output: a single evidence-to-slide map that controls the deck.

### Phase B — presentation asset extraction

Collect read-only presentation assets from existing repository evidence:

- architecture diagrams;
- short code excerpts;
- terminal/evidence screenshots;
- state and lifecycle diagrams;
- human-review examples;
- comparison tables;
- screen-recording clips where useful.

Do not alter engineering evidence to create cleaner visuals.

### Phase C — story architecture

Build the talk around this sequence:

1. agent demos hide the harness;
2. define the six organs;
3. introduce one frozen Drupal task;
4. show how each harness implements the same responsibilities;
5. compare organ by organ;
6. examine failure/recovery honestly;
7. explain what the incomplete Drupal recovery taught us about experiment and harness design;
8. end with a reusable evaluation framework rather than a framework winner.

### Phase D — deck and speaker material

Produce:

- final slide outline;
- final deck;
- speaker notes;
- code callouts;
- demo/clip cues;
- transitions;
- backup slides;
- Q&A preparation.

### Phase E — rehearsal and fallback

Produce:

- timed rehearsal plan;
- shortened talk path;
- no-network/no-demo fallback;
- static replacement visual for every critical clip/demo;
- presenter checklist;
- final claims/evidence review.

## Claim discipline for production

Use `CLAIMS_REGISTER.md` and `COMPARISON_MATRIX.md` as the default source for language.

Safe framing includes:

- "In this implementation…"
- "The retained evidence shows…"
- "Our model-free rehearsal demonstrated…"
- "Drupal reached the recovery seam, but we did not demonstrate continuation."
- "This exposed a harness/experiment problem rather than proving a framework deficiency."

Do not claim:

- all three frameworks recovered successfully;
- Drupal resumed at target 7;
- Drupal demonstrated replay-free recovery;
- Gate 2C passed or was certified;
- Gate 2 completed;
- a recovery winner;
- production readiness;
- general framework superiority.

## Historical execution model

Engineering was performed with a package-driven evidence-first workflow: frozen contracts,
one-package-at-a-time changes, explicit approvals, retained evidence, audits, exact-scope Git
changes, certification, and freezes.

Those historical gate/package documents remain in the repository because they are part of the
proof trail. They are no longer the active work queue.

The full historical sequence can be reconstructed from:

- `docs/gates/`
- `docs/handoffs/`
- `docs/decisions/`
- `scripts/`
- `shared/contracts/`
- `evidence/`
- Git history through the engineering checkpoint.

## Scope that remains out

The conference project does not expand into:

- automatic source-field application;
- general-purpose agent platform features;
- vector/RAG expansion;
- multiple-model comparison;
- cost/speed benchmarking;
- production-readiness benchmarking;
- custom dashboard development;
- cloud deployment of all three specimens;
- new Gate 2C recovery trials.

If future research explores any of those areas, create a new experiment boundary rather than
silently extending this one.
