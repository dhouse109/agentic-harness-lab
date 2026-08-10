# Codex Operating Instructions

## Purpose

This repository is a version-pinned comparative engineering experiment for Drupal GovCon 2026.
Codex may implement and execute work locally, but it must preserve the experiment boundary,
evidence discipline, package controls, and human approval points defined here.

The objective is not to force the conference proposal's predicted conclusions. The implementation
must report what the pinned frameworks actually do.

## Authoritative reading order

Before planning or changing anything, read these files in order:

1. `docs/CURRENT-STATUS.md`
2. `PLAN.md`
3. `README.md`
4. `EXPERIMENT_SPEC.md`
5. `CLAIMS_REGISTER.md`
6. `COMPARISON_MATRIX.md`
7. The current gate and predecessor documents in `docs/gates/` and `docs/handoffs/`
8. The applicable contracts and schemas in `shared/contracts/` and `shared/schemas/`
9. The retained evidence and summary from the immediately preceding package

When documents disagree, the current status file, frozen contract hashes, retained evidence, and
latest passing package audit control. Do not silently reconcile a conflict. Report it and stop at the
relevant decision boundary.

## Local environment

- Work from the WSL2 checkout under `/home/...`, normally
  `~/projects/agentic-harness-lab`.
- Use the installed Docker CE, DDEV, Drupal site, `uv` environments, Git, and local private
  credentials.
- Do not relocate the checkout to `/mnt/c/...`.
- Do not expose secrets while inspecting the local environment.

## Delivery-package workspace

Delivery packages are build artifacts and must remain outside this Git repository.

Use this default local package root unless the user explicitly supplies another path:

```text
~/projects/agentic-harness-package-staging/
```

A package therefore lives at a path such as:

```text
~/projects/agentic-harness-package-staging/gate-1-step01-drupal-ai-batch-contract-v1.0.0/
```

Do not add package archives, extracted delivery-package directories, package backups, or temporary
package-installation state to the repository. Commit only the package's intended installed repository
changes and sanitized retained evidence.

## Package-driven workflow

Gate 2A is executed one package at a time. Never generate later packages in advance.

For each package:

1. Verify the repository root, branch, current commit, predecessor lineage, and clean working tree.
2. Audit the declared predecessor before crossing a mutation boundary.
3. Read the predecessor's retained evidence and summary directly.
4. Create only the next declared delivery package under the external package root.
5. Inspect every proposed overwrite and exact predecessor requirement.
6. Run `package.sh preview <repo-path>`.
7. Confirm preview reports explicit `KEEP`, `CREATE`, `UPDATE`, or `DELETE` actions and ends with
   `No files were changed.`
8. Present the preview plan and stop for human package-boundary approval.
9. After approval, run `package.sh run <repo-path>`.
10. Run the installed repository runner's focused audit.
11. Inspect generated evidence, logs, hashes, summaries, Git status, and diffs directly. Do not ask
    the user to paste output that is already available locally.
12. Run applicable syntax, schema, configuration, source-non-mutation, idempotency, reset, and
    secret-hygiene checks.
13. If the package does not pass its declared boundary, repair that same package and repeat its
    preview/run/audit cycle. Do not describe an installation-only success as a passing package.
14. Present a concise evidence summary, diff summary, safe completion statement, and proposed commit
    message.
15. Stop for commit approval. Do not push or generate the next package until the current package is
    passing and committed.

## Human approval boundaries

Always stop for the user at these boundaries:

- After package preview and before package execution.
- Before a material architecture decision, experiment-constant change, dependency change, contrib
  patch, credential-handling change, or evidence invalidation.
- Before committing or pushing a passing package result.
- When an observed framework behavior contradicts the current plan or proposal prediction.

Normal commands inside an approved package boundary may be executed without asking the user to copy
and run them manually.

## Frozen comparative experiment rules

Preserve the frozen values and semantics recorded in the repository, including:

- Provider: OpenAI.
- Model: `gpt-4.1-mini-2025-04-14`.
- Temperature: `0.0`.
- Dataset: 20 Articles and the frozen 12-target sequence.
- Certified Gate 1 origin: `drupal_ai` (frozen and immutable).
- Current Gate 2A origin: `langgraph`.
- Shared semantic operations:
  - `find_images_needing_review()`
  - `get_image_context(target)`
  - `submit_recommendation(recommendation)`
  - `get_recommendation_status(recommendation_id)`
- Shared deterministic validator and schemas.
- Review destination: revision-enabled `alt_text_suggestion` records.
- Reviewer: `editor_dana`.
- Source Article and image-field mutation: prohibited.
- Automatic publication: prohibited.
- Later failure seam: after target 6 is fully persisted and before target 7 begins.

A change to a frozen constant, shared operation semantic, idempotency identity, target ordering,
review destination, prompt-fairness boundary, failure point, source-mutation rule, model, temperature,
or pinned dependency requires an ADR and an invalidated-evidence review.

## Implementation boundaries

- Framework-owned model invocation, orchestration, state, sequencing, persistence, interruption,
  recovery, and lifecycle behavior must remain framework-owned.
- Do not duplicate the frozen shared business logic inside a framework adapter.
- Do not bypass the certified Gate 0.5 operations with a private write path.
- Do not patch contributed packages or silently upgrade dependencies.
- Do not substitute a direct OpenAI script merely to preserve the proposed Drupal AI conclusion.
- Prefer supported public APIs in the pinned runtime. Record any necessary architecture decision in
  an ADR before deep implementation.
- Do not build excluded scope: dashboards, vector search, MCP expansion, ECA expansion, cloud
  deployment, multiple agents, cost/speed benchmarks, automatic source-field application, or
  presentation polish during Gate 1 execution.

## Evidence and privacy

Evidence may retain versions, hashes, sanitized fixture facts, structured model outputs, tool names,
sanitized arguments/results, validator outcomes, recommendation IDs, revision lineage, state
transitions, reviewer decisions, and sanitized errors.

Never retain or print:

- OpenAI API keys.
- Basic Auth passwords or authorization headers.
- Raw Base64 image data or full data URLs.
- Private database exports.
- Hidden model reasoning or chain of thought.
- Unrelated private configuration or user data.
- Full environment dumps containing secrets.

Do not request chain of thought from a model. Retain only structured output, tool traces, state,
evaluation results, and human decisions needed to audit the experiment.

## Evidence wording

- A proposal prediction begins as `hypothesis`.
- Local repeatable evidence may promote it to `observed`.
- Only official sources plus retained local evidence may promote it to `verified`.
- Unsupported claims must be marked `unsupported` with safe wording such as `do not use`.
- Never claim production readiness, framework superiority, accessibility quality, autonomous
  publishing safety, recovery behavior, cost, speed, or security beyond the tested boundary.

## Git rules

- Start a package from a clean working tree unless its package contract explicitly permits otherwise.
- Do not use `git add -A` when unrelated changes are present.
- Stage only intended installed files and sanitized evidence.
- Do not rewrite or force-update `main`.
- Do not commit package workspace files or credentials.
- Use a concise commit message that names the completed package boundary.
- A passing package commit must include the evidence summary and updated status pointers required by
  that package.

## Immediate task boundary

Gate 1 Drupal AI is complete and frozen at `2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd`. Gate 2 is the umbrella cross-framework milestone; Gate 2A LangGraph is current.

**Step 2A.01:** complete.

**Step 2A.02:** complete.

**Step 2A.03:** complete.

**Step 2A.04:** complete.

**Step 2A.05:** complete.

**Step 2A.06:** complete.

**Completed package:** `gate-2a-step06-langgraph-human-interrupt-and-review-resume-v1.0.8`.

**Next package:** `gate-2a-step07-langgraph-batch-runner-v1.0.0`.

Accepted Step 2A.06 evidence run: `evidence/gates/gate-2a/human-interrupt/gate2a-step06-20260810T162448Z-002692eb`

Accepted Step 2A.05 evidence run: `evidence/gates/gate-2a/canonical-slice/gate2a-step05-20260810T140133Z-0025b888`

Accepted Step 2A.04 evidence run: `evidence/gates/gate-2a/checkpoint-proof/gate2a-step04-20260810T034027Z-00250b07`

Accepted Step 2A.03 evidence run: `gate2a-step03-20260809T233127Z-2375581`
Accepted Step 2A.03 compliance verification: `gate2a-step03-verification-20260810T020210Z-2410520`

Read `docs/gates/GATE-2-STRUCTURE.md`, `docs/gates/GATE-2A-STEP01-LANGGRAPH-CONTRACT.md`, `docs/CODEX-GATE-2A-RUNBOOK.md`, `docs/handoffs/GATE-1-TO-LANGGRAPH-HANDOFF.md`, the Gate 1 freeze manifest, and accepted Step 1.07 evidence. Preserve the frozen dataset, model/settings, shared operations, validator, review destination, source-mutation rule, and later shared failure point. Do not infer LangGraph behavior from Drupal AI evidence.

Do not generate Step 2A.07 until Step 2A.06 is passing, committed, merged, local `main` is resynchronized, and the post-merge audit passes.

Accepted Step 2A.02 evidence run: `gate2a-step02-20260809T224238Z-2361786`
Accepted runtime ADR: `docs/decisions/ADR-0010-langgraph-runtime-and-checkpoint-path.md`

Accepted Step 2A.01 evidence run: `gate2a-step01-20260809T202418Z-2334327`
Accepted Gate 2A contract digest: `1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b`
