# Current Implementation Status

**Status date:** August 5, 2026  
**Authoritative branch:** `main` after this status-update PR is merged

## Current position

- **Phase 0:** complete.
- **Gate 0.5:** complete and certified.
- **Gate 1:** active.
- **Completed packages:** Step 1.01 batch contract and Step 1.02 Drupal AI runtime probe.
- **Step 1.02 execution:** complete.
- **Next package:** `gate-1-step03-drupal-ai-tool-adapters-v1.0.0`.
- **Execution environment:** Codex running locally inside WSL2, governed by `AGENTS.md`.

Gate 0.5 completed when the framework-neutral Drupal substrate passed its standalone certification,
was frozen, and was handed off for framework-specific implementation. The certification baseline is
commit `fb23e41f6fc8f8e070babbf9a0f593edb94f8c5c` (`Certify Gate 0.5 shared substrate`).

Step 1.01 freezes the Drupal AI batch execution contract, canonical run-state and raw model-output
schemas, lifecycle-separated evidence requirements, and the repository-native Gate 1 package
sequence. It does not call a model, mutate Drupal, alter dependencies, recertify Gate 0.5, or begin
Step 1.02.

Accepted Step 1.01 evidence run: `gate1-step01-20260805T205448Z-103220`
Accepted Gate 1 contract digest: `360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6`
Accepted Step 1.02 evidence run: `gate1-step02-20260806T010227Z-189538`
Accepted ADR-0006 SHA-256: `223f6d6f4276d3861cf5668f08e0446479d815a07fed18402b1e6a7722d18c4b`

The v1.0.0 evidence run `gate1-step01-20260805T200619Z-87483` remains immutable. It is superseded
for publication only because later checks found terminal schema blank lines and a main-only installed
audit restriction. The v1.0.1 repair does not change contract semantics.

## What Gate 0.5 proved

The certified substrate provides and audits these four deterministic operations:

```text
find_images_needing_review()
get_image_context(target)
submit_recommendation(recommendation)
get_recommendation_status(recommendation_id)
```

The retained evidence proves exact target identity, permission-scoped context retrieval,
deterministic validation, idempotent recommendation submission, a real revisioned human decision,
read-only status observation, source non-mutation, and restoration to `seeded-clean`.

Audit the completed gate with:

```bash
bash scripts/run-gate05-step05.sh audit
```

Primary retained evidence:

```text
evidence/gates/gate-0.5/substrate-certification/
  gate05-step05-20260805T184155Z-50124/
```

Frozen substrate digest:

```text
99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a
```

Frozen handoff artifacts:

```text
shared/contracts/GATE05-SUBSTRATE-FREEZE.json
shared/contracts/GATE05-SUBSTRATE-FREEZE.sha256
docs/handoffs/GATE-0.5-FRAMEWORK-HANDOFF.md
```

## Gate 1 local execution handoff

Gate 1 will use Codex locally in WSL2. Codex creates delivery packages outside the repository,
previews them, stops for package-boundary approval, executes approved packages, audits retained
evidence, and stops again before commit.

The governing files are:

```text
AGENTS.md
docs/CODEX-GATE-1-RUNBOOK.md
docs/prompts/CODEX-GATE-1-STEP01.md
```

The external delivery-package root is:

```text
~/projects/agentic-harness-lab-packages/
```

Packages 1.01 and 1.02 are complete. The next package is
`gate-1-step03-drupal-ai-tool-adapters-v1.0.0`. Do not commit extracted packages or reuse a package
generated against a different repository baseline.

## Important interpretation

The freeze manifest and handoff correctly record that Drupal AI, LangGraph, and CrewAI were **not
certified by the substrate preflight**. That statement describes the boundary of the Gate 0.5 proof;
it does **not** mean Gate 0.5 remains open under the current execution plan.

Framework-owned model calls, orchestration, state, checkpointing, human-interrupt behavior, and
recovery begin after the frozen substrate handoff. Drupal AI is addressed first in Gate 1, followed
by the LangGraph and CrewAI implementations and then shared failure/recovery comparison work.

The original conference master plan used the broader phrase "one image, one recommendation, one
human decision, three implementations" as the Gate 0.5 milestone. During implementation, the gate
boundary was narrowed so the independently certified shared substrate became the Gate 0.5 exit and
the framework implementations became subsequent work. This repository's current status documents
and retained evidence control when assessing what is complete and what comes next.

## Gate 1 package sequence

The repository-native sequence is:

1. Step 1.01 — batch contract
2. Step 1.02 — pinned Drupal AI runtime probe
3. Step 1.03 — thin Drupal AI tool adapters
4. Step 1.04 — canonical vertical slice
5. Step 1.05 — 12-target batch runner
6. Step 1.06 — batch evidence and human review
7. Step 1.07 — certification, freeze, and handoff

This sequence and `shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json` govern later package
generation. The Step 1.02 runtime-path decision is recorded in `ADR-0006`; ADR-0004 and ADR-0005 remain
unchanged.

## Canonical Step 1.01 schemas

```text
shared/schemas/drupal-ai-run-state.schema.json
shared/schemas/drupal-ai-model-output.schema.json
```

The run-state schema defines framework-owned comparison state without selecting or authorizing a
shared runtime storage location. The model-output schema describes raw structured model output only;
recommendation assembly, deterministic validation, submission, status, and human review remain
separate evidence stages.

## Fresh-session reading order

A new planning or implementation session should read these files in order:

1. `AGENTS.md`
2. `docs/CURRENT-STATUS.md`
3. `PLAN.md`
4. `README.md`
5. `EXPERIMENT_SPEC.md`
6. `docs/CODEX-GATE-1-RUNBOOK.md`
7. `docs/gates/GATE-0.5-STEP05-SUBSTRATE-CERTIFICATION-AND-HANDOFF.md`
8. `docs/handoffs/GATE-0.5-FRAMEWORK-HANDOFF.md`
9. `shared/contracts/GATE05-SUBSTRATE-FREEZE.json`
10. `docs/gates/GATE-1-STEP01-DRUPAL-AI-BATCH-CONTRACT.md`
11. `shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json`

Do not add a Gate 0.5 reconciliation package before Gate 1 unless an audit fails or the frozen
substrate is intentionally changed. Do not generate Step 1.03 until Step 1.02 is committed.
