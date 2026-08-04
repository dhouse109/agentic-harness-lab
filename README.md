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

## Private and public reproduction paths

Private local material includes database exports, DDEV snapshots, credentials, and raw recordings.
The intended public reproduction path is source code, Composer and uv lockfiles, Drupal config
export, schemas, fixtures, seed/reset scripts, test scripts, and sanitized evidence.

## Current phase

Phase 0 is complete. The frozen model and image representation passed Step 16, and the model-free,
permission-scoped Drupal `find_images_needing_review()` route returned the same 12 exact image-field
usages as the Step 9 manifest without changing Article state or creating suggestions.

Gate 0.5 is next:

> One image, one recommendation, one human decision, three implementations.

Verify Step 17 with:

```bash
bash scripts/run-phase0-step17.sh audit
```

Passing evidence: `evidence/logs/tools/find-images/step17-20260804T173030Z-851608`
