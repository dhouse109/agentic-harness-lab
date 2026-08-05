# Agentic Harness Lab

A reproducible Drupal GovCon 2026 laboratory for building the same governance-sensitive alt-text
recommendation task in three harnesses:

- Drupal AI
- LangChain / LangGraph
- CrewAI

The purpose is not to prove a predetermined winner. The lab collects version-pinned, repeatable
evidence about six harness organs: context, tools, state and memory, verification, human review,
and lifecycle and recovery.

## Shared task

Find Drupal image-field usages with missing or inadequate alt text, assemble permitted image and
page context, draft a remediation recommendation, validate it, and submit it to a common Drupal
review queue. Agents create recommendation records; they do not mutate production image fields.

## Evidence discipline

A framework claim begins as a **hypothesis**. It becomes **observed** after a repeatable local run
and **verified** only when the observation is paired with an official source and retained evidence.
See `CLAIMS_REGISTER.md`, `SOURCES.md`, and `evidence/README.md`.

## Repository boundaries

`shared/` contains contracts and deterministic substrate only. Framework-owned context assembly,
model calls, orchestration, persistence, interruption, recovery, and sequencing remain inside the
three implementation directories. See `shared/README.md`.

## Certified shared tool surface

The Gate 0.5 shared substrate now exposes four deterministic operations:

```text
find_images_needing_review()
get_image_context(target)
submit_recommendation(recommendation)
get_recommendation_status(recommendation_id)
```

The substrate has proven exact target identity, permission-scoped context retrieval, deterministic
validation, recommendation-only mutation, idempotent submission, a real revisioned human decision,
read-only status observation, and seeded-clean restoration.

The hash-addressed handoff is stored at:

```text
shared/contracts/GATE05-SUBSTRATE-FREEZE.json
shared/contracts/GATE05-SUBSTRATE-FREEZE.sha256
```

Material changes to the frozen substrate require an ADR and a new Step 05 certification run.

## Private and public reproduction paths

Private local material includes database exports, DDEV snapshots, credentials, and raw recordings.
The intended public reproduction path is source code, Composer and uv lockfiles, Drupal config
export, schemas, fixtures, seed/reset scripts, test scripts, and sanitized evidence.

## Current phase

Phase 0 is complete and the Gate 0.5 **shared substrate** is certified. Overall Gate 0.5 remains in
progress: Drupal AI, LangGraph, and CrewAI must still complete their own model-backed one-image
vertical slices using the frozen shared boundary.

Next implementation:

```text
Drupal AI vertical slice
```

Audit the shared substrate with:

```bash
bash scripts/run-gate05-step05.sh audit
```
