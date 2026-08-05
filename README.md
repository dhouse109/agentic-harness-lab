# Agentic Harness Lab

A reproducible Drupal GovCon 2026 laboratory for building the same governance-sensitive alt-text
recommendation task in three harnesses:

- Drupal AI
- LangChain / LangGraph
- CrewAI

The purpose is not to prove a predetermined winner. The lab collects version-pinned, repeatable
evidence about six harness organs: context, tools, state and memory, verification, human review,
and lifecycle and recovery.

## Current status

- **Phase 0:** complete.
- **Gate 0.5:** complete and certified.
- **Next phase:** Gate 1 — Drupal AI full implementation.
- **Next package:** `gate-1-step01-drupal-ai-batch-contract-v1.0.0`.

For a new planning or implementation session, read `docs/CURRENT-STATUS.md` first. It is the
authoritative status snapshot and explains the boundary between the completed shared-substrate gate
and the framework-owned work that follows.

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

Gate 0.5 certified these four deterministic shared operations:

```text
find_images_needing_review()
get_image_context(target)
submit_recommendation(recommendation)
get_recommendation_status(recommendation_id)
```

The substrate proved exact target identity, permission-scoped context retrieval, deterministic
validation, recommendation-only mutation, idempotent submission, a real revisioned human decision,
read-only status observation, and seeded-clean restoration.

The hash-addressed handoff is stored at:

```text
shared/contracts/GATE05-SUBSTRATE-FREEZE.json
shared/contracts/GATE05-SUBSTRATE-FREEZE.sha256
```

Material changes to the frozen substrate require an ADR and a new Step 05 certification run.

The freeze manifest correctly records that Drupal AI, LangGraph, and CrewAI were not certified by
the controlled substrate preflight. That statement defines the proof boundary; it does not leave
Gate 0.5 open. Framework-owned execution starts after the handoff, beginning with Drupal AI in Gate
1.

## Private and public reproduction paths

Private local material includes database exports, DDEV snapshots, credentials, and raw recordings.
The intended public reproduction path is source code, Composer and uv lockfiles, Drupal config
export, schemas, fixtures, seed/reset scripts, test scripts, and sanitized evidence.

## Audit the completed Gate 0.5 substrate

```bash
bash scripts/run-gate05-step05.sh audit
```

Certification baseline:

```text
fb23e41f6fc8f8e070babbf9a0f593edb94f8c5c
Certify Gate 0.5 shared substrate
```
