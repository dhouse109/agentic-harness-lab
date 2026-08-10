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
- **Gate 1:** complete and certified.
- **Step 1.01:** complete.
- **Step 1.02:** complete.
- **Step 1.03:** complete.
- **Step 1.04:** complete.
- **Step 1.05:** complete.
- **Step 1.06:** complete.
- **Step 1.07:** complete; Gate 1 Drupal AI is certified and frozen.
- **Gate 2:** in progress; Gate 2A LangGraph is current.
- **Step 2A.01:** complete.
- **Step 2A.02:** complete.
- **Step 2A.03:** complete.
- **Step 2A.04:** complete.
- **Step 2A.05:** complete.
- **Step 2A.06:** complete.
- **Step 2A.07:** complete.
- **Completed package:** `gate-2a-step07-langgraph-batch-runner-v1.0.5`.
- **Next package:** `gate-2a-step08-langgraph-fresh-batch-and-continuation-v1.0.0`.
Accepted Step 2A.07 construction evidence run: `evidence/gates/gate-2a/batch-runner/gate2a-step07-20260810T185629Z-00272cd1`
Accepted Step 2A.06 evidence run: `evidence/gates/gate-2a/human-interrupt/gate2a-step06-20260810T162448Z-002692eb`
Accepted Step 2A.05 evidence run: `evidence/gates/gate-2a/canonical-slice/gate2a-step05-20260810T140133Z-0025b888`
Accepted Step 2A.04 evidence run: `evidence/gates/gate-2a/checkpoint-proof/gate2a-step04-20260810T034027Z-00250b07`
Accepted Step 2A.03 evidence run: `gate2a-step03-20260809T233127Z-2375581`
Accepted Step 2A.03 compliance verification: `gate2a-step03-verification-20260810T020210Z-2410520`
Accepted Step 2A.02 evidence run: `gate2a-step02-20260809T224238Z-2361786`
Accepted runtime ADR: `docs/decisions/ADR-0010-langgraph-runtime-and-checkpoint-path.md`
Accepted Step 2A.01 evidence run: `gate2a-step01-20260809T202418Z-2334327`
Accepted Gate 2A contract digest: `1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b`

Accepted Gate 0.5 certification evidence is
`evidence/gates/gate-0.5/substrate-certification/gate05-step05-20260805T184155Z-50124/`.
The frozen substrate digest is
`99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a`.

Accepted Step 1.01 evidence run: `gate1-step01-20260805T205448Z-103220`
Accepted Gate 1 contract digest: `360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6`
Accepted Step 1.02 evidence run: `gate1-step02-20260806T010227Z-189538`
Accepted ADR-0006 SHA-256: `223f6d6f4276d3861cf5668f08e0446479d815a07fed18402b1e6a7722d18c4b`
Accepted Step 1.03 evidence run: `gate1-step03-20260806T050827Z-494925`
Accepted Step 1.04 evidence run: `gate1-step04-20260806T213954Z-156475`
Accepted Step 1.05 evidence run: `gate1-step05-20260808T020222Z-2121689`
Accepted Drupal AI batch run: `drupal_ai-20260808T020222Z-205fd9`
Accepted Step 1.06 evidence run: `gate1-step06-20260808T231216Z-2188911`
Accepted Step 1.06 implementation package: `gate-1-step06-drupal-ai-batch-evidence-and-human-review-v1.0.3`
Step 1.06 reviewer-lineage recovery patch: `gate-1-step06-drupal-ai-batch-evidence-and-human-review-v1.0.4`
Accepted Step 1.07 certification evidence: `evidence/gates/gate-1/certification/gate1-step07-20260809T012559Z-2229836`
Accepted Drupal AI certification batch: `drupal_ai-20260809T012559Z-22064c`
Accepted Gate 1 freeze digest: `2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd`


Step 1.03 directly exercises exactly four model-free Drupal AI FunctionCall adapters: `discover_targets`, `get_image_context`, `submit_recommendation`, and `get_recommendation_status`. It does not execute an AI Agent and makes no model or provider call. Its predecessor-compatible Article-source SHA-256 is `f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17`; the original Step 1.03 hash discrepancy was definition drift only, with no Drupal source drift.

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

This sequence and the machine-readable Gate 1 contract govern later package generation. The Step 1.02 runtime-path decision is recorded in `ADR-0006`.

## Local Codex execution

Gate 2A continues the package-driven local workflow inside WSL2. Read:

```text
AGENTS.md
docs/CODEX-GATE-2A-RUNBOOK.md
docs/gates/GATE-2-STRUCTURE.md
docs/gates/GATE-2A-STEP01-LANGGRAPH-CONTRACT.md
```

Delivery packages are generated outside Git under:

```text
~/projects/agentic-harness-package-staging/
```

Do not commit extracted packages or archives. Step 2A.01 is model-free and Drupal-mutation-free; it freezes the LangGraph contract and evidence boundary only.

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
