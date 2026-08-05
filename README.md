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
- **Gate 1:** active.
- **Step 1.01:** complete.
- **Next package:** `gate-1-step02-drupal-ai-runtime-probe-v1.0.0`.

Accepted Gate 0.5 certification evidence is
`evidence/gates/gate-0.5/substrate-certification/gate05-step05-20260805T184155Z-50124/`.
The frozen substrate digest is
`99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a`.

Accepted Step 1.01 evidence run: `gate1-step01-20260805T205448Z-103220`
Accepted Gate 1 contract digest: `360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6`

The v1.0.0 evidence run `gate1-step01-20260805T200619Z-87483` is preserved unchanged and superseded
for publication only because later checks exposed terminal schema blank lines and a main-only audit
restriction. Contract semantics remain unchanged.

For a new planning or implementation session, read `docs/CURRENT-STATUS.md` first. It is the
authoritative status snapshot and explains the boundary between the completed shared-substrate gate
and the framework-owned work that follows.

## Gate 1 contract

Step 1.01 freezes the Drupal AI batch boundary in:

```text
shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json
shared/schemas/drupal-ai-run-state.schema.json
shared/schemas/drupal-ai-model-output.schema.json
```

The shared run-state schema is a comparison contract only. The Drupal AI implementation owns its
runtime state and persistence location; shared runtime storage is prohibited. Raw structured model
output remains distinct from recommendation assembly, deterministic validation, submission,
status observation, and human review evidence.

The repository-native Gate 1 package sequence is:

1. Step 1.01 — batch contract
2. Step 1.02 — pinned Drupal AI runtime probe
3. Step 1.03 — thin Drupal AI tool adapters
4. Step 1.04 — canonical vertical slice
5. Step 1.05 — 12-target batch runner
6. Step 1.06 — batch evidence and human review
7. Step 1.07 — certification, freeze, and handoff

This sequence and the machine-readable Gate 1 contract govern later package generation. The Step
1.02 runtime-path decision is expected to use `ADR-0006`, subject to confirming it remains the next
available number.

## Local Codex execution

Gate 1 is designed to run through Codex locally inside WSL2 while preserving one-package-at-a-time
preview, audit, evidence, and commit controls.

Read:

```text
AGENTS.md
docs/CODEX-GATE-1-RUNBOOK.md
docs/prompts/CODEX-GATE-1-STEP01.md
```

Delivery packages are generated outside Git under:

```text
~/projects/agentic-harness-lab-packages/
```

Do not commit extracted packages or package archives. Commit only their intended installed repository
changes and sanitized retained evidence.

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
