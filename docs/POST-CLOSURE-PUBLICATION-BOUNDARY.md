# Post-Closure Documentation and Publication Boundary

**Established:** October 5, 2026  
**Repository:** `dhouse109/agentic-harness-lab`  
**Immutable engineering checkpoint:** `15e50615f5c525d9c6ed937fe607b3f009898f10`  
**Checkpoint subject:** `Close Gate 2C with terminal non-certifying evidence`

## Purpose

The engineering and evidence-collection phase is finished. This document separates the immutable
Gate 2C closure record from later documentation, publication, and conference-production work.

The repository may continue to improve explanatory documentation after the engineering checkpoint,
but those changes must not be interpreted as changing the experiment, its retained evidence, its
certifications, or its terminal Gate 2C disposition.

## Immutable closure checkpoint

Commit `15e50615f5c525d9c6ed937fe607b3f009898f10` is the durable engineering checkpoint for the
completed runtime/evidence phase.

At that checkpoint:

- Gate 1 / Drupal AI was certified and frozen.
- Gate 2A / LangGraph was certified and frozen.
- Gate 2B / CrewAI was certified and frozen.
- Gate 2C was terminally `CLOSED_NON_CERTIFYING_WITH_INCOMPLETE_EVIDENCE`.
- Step 2C.02 was `TERMINAL_UNCERTIFIED`.
- Gate 2 remained `NOT_COMPLETE`.
- `RESET_NOT_PERFORMED` was retained.
- No further Gate 2C runtime, replacement, retry, observation, reset, certification, pointer, or
  identity activity was authorized.
- The final Gate 2C closure audit passed.

The distinction is intentional: **the engineering phase is finished, but the Gate 2 umbrella did
not satisfy its cross-framework recovery exit criteria.**

## Why current documentation may differ from the checkpoint

The final closure audit is hash-bound to the documentation and closure sources that existed at the
engineering checkpoint. Its installed-source manifest includes files such as:

- `AGENTS.md`
- `PLAN.md`
- `README.md`
- `docs/CURRENT-STATUS.md`
- `CLAIMS_REGISTER.md`
- `COMPARISON_MATRIX.md`
- the Gate 2 / Gate 2C closure documents and audit code

Post-closure edits to public-facing documentation therefore intentionally change hashes relative to
that historical manifest. This does **not** invalidate the historical closure. It means the final
closure audit must be reproduced against the immutable checkpoint, not against a later publication
commit.

## Reproducing the final closure audit

Use a detached checkout or worktree at the engineering checkpoint:

```bash
git fetch origin
git worktree add --detach ../agentic-harness-gate2c-closure \
  15e50615f5c525d9c6ed937fe607b3f009898f10

cd ../agentic-harness-gate2c-closure
bash scripts/run-gate2c-final-closure-audit.sh audit "$(pwd)"
```

Expected terminal marker:

```text
GATE_2C_FINAL_CLOSURE_AUDIT_PASS
```

Do not update the closure manifest merely to make later prose changes pass the historical audit.

## Allowed post-closure work

Post-closure work may include:

- improving the public README and repository navigation;
- maintaining a concise current-status page;
- converting the implementation plan into a historical/current-phase plan;
- updating agent instructions for documentation and conference-production work;
- building an evidence-to-slide map;
- extracting read-only code, terminal, screenshot, diagram, and video assets from retained evidence;
- writing slides, speaker notes, backup slides, demo cues, Q&A material, and rehearsal plans;
- correcting explanatory prose when the correction does not alter retained experiment evidence.

## Prohibited without a new explicit governance decision

Do not:

- execute new Gate 2C runtime experiments;
- allocate another Drupal worker or replacement identity;
- retry the Drupal recovery path;
- reconstruct the missed immediate lock observation;
- perform another post-expiry observation;
- reset the terminal Drupal experiment;
- certify Step 2C.02;
- mark Gate 2C as passed, successful, complete, or certified;
- mark Gate 2 as complete or passed;
- rewrite, delete, or manufacture historical evidence;
- modify frozen Gate 1, Gate 2A, or Gate 2B results to make the comparison more symmetrical;
- present model-free recovery evidence as equivalent to authoritative model-backed Gate 2C
  certification.

A future experiment may be created only as a new explicitly governed experiment boundary. It must
not overwrite or retroactively repair this one.

## Required status language

Safe summary language for the repository and presentation is:

> The engineering/evidence phase is finished. Drupal AI, LangGraph, and CrewAI each have certified
> framework-specific implementation gates. Gate 2C is closed non-certifying with incomplete
> evidence: qualified model-free recovery mechanics were demonstrated for LangGraph and CrewAI,
> while Drupal retained useful partial failure evidence but no recovery continuation. Because the
> shared three-framework recovery criterion was not satisfied, Gate 2 remains formally incomplete.

Shorter public wording may say **"engineering complete"** or **"experiment concluded"**, provided it
does not imply Gate 2 passed or that all three frameworks recovered successfully.

## Evidence remains authoritative

For technical claims, use:

1. `CLAIMS_REGISTER.md`
2. `COMPARISON_MATRIX.md`
3. the relevant frozen contracts and certification records
4. retained evidence under `evidence/`
5. `docs/gates/GATE-2C-CLOSURE-AND-DISPOSITION.md`

Publication prose may simplify the explanation. It may not strengthen a claim beyond those sources.
