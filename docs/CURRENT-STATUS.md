# Current Implementation Status

**Status date:** August 5, 2026  
**Authoritative branch:** `main` after this status-update PR is merged

## Current position

- **Phase 0:** complete.
- **Gate 0.5:** complete and certified.
- **Next phase:** Gate 1 — Drupal AI full implementation.
- **Next package:** `gate-1-step01-drupal-ai-batch-contract-v1.0.0`.

Gate 0.5 completed when the framework-neutral Drupal substrate passed its standalone certification,
was frozen, and was handed off for framework-specific implementation. The certification baseline is
commit `fb23e41f6fc8f8e070babbf9a0f593edb94f8c5c` (`Certify Gate 0.5 shared substrate`).

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
  gate05-step05-20260805T010224Z-1100690/
```

Frozen handoff artifacts:

```text
shared/contracts/GATE05-SUBSTRATE-FREEZE.json
shared/contracts/GATE05-SUBSTRATE-FREEZE.sha256
docs/handoffs/GATE-0.5-FRAMEWORK-HANDOFF.md
```

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

## Fresh-session reading order

A new planning or implementation session should read these files in order:

1. `docs/CURRENT-STATUS.md`
2. `PLAN.md`
3. `README.md`
4. `docs/gates/GATE-0.5-STEP05-SUBSTRATE-CERTIFICATION-AND-HANDOFF.md`
5. `docs/handoffs/GATE-0.5-FRAMEWORK-HANDOFF.md`
6. `shared/contracts/GATE05-SUBSTRATE-FREEZE.json`

Do not add a Gate 0.5 reconciliation package before Gate 1 unless an audit fails or the frozen
substrate is intentionally changed. The next planned work is the first Gate 1 package.
