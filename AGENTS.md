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

Gate 2B is executed one package at a time. Never generate later packages in advance.

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
- Certified Gate 2A origin: `langgraph` (frozen and immutable).
- Current Gate 2B origin: `crewai`.
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

Gate 1 Drupal AI and Gate 2A LangGraph are certified and frozen. Gate 2 is the umbrella cross-framework milestone; Gate 2B CrewAI is current. Gate 2C shared three-framework failure/recovery remains deferred and unclaimed.

**Step 2B.01:** complete, merged, and post-merge audited.

**Completed Step 2B.02 package:** `gate-2b-step02-crewai-architecture-adr-and-closure-v1.0.0`.

**Step 2B.02:** complete, merged, resynchronized, and post-merge audited after retained model-free runtime evidence, permanent architecture audit, and explicit human architecture approval.

**Completed Step 2B.03 package:** `gate-2b-step03-crewai-shared-operation-adapters-v1.0.0`.

**Step 2B.03:** complete locally with accepted model-free adapter evidence `gate2b-step03-20260818T163812Z-7a58ef58` and a passing permanent audit. It has not been committed or merged. Step 2B.04 remains unbegun; no later Gate 2B package is named or begun.

**Retained diagnostic Step 2B.02 run:** `gate2b-step02-20260812T010531Z-00000001` is byte-valid diagnostic evidence but is superseded/unaccepted for architecture selection. Its original mechanical audit passed; later integrity review found unlabeled private Flow instrumentation and incomplete isolation/retry predicates. At that capture boundary, Step 2B.02 remained open.

**Retained superseding Step 2B.02 capture:** `gate2b-step02-20260812T015108Z-00000001` passed its v2 capture boundary and remains byte-identical, with architecture status `unresolved`.

**Retained targeted Step 2B.02 supplemental capture:** `gate2b-step02-followup-20260812T022947Z-00000001` remains byte-identical. It corrected native structured-output fallback and checkpoint semantics, while its immutable classifier retained four version-check events as `unresolved_path`.

**Accepted governed Step 2B.02 disposition:** `gate2b-step02-disposition-20260812T024610Z-00000001` separately binds the immutable call stacks to pinned-source version-check provenance, verifies the public disable control, and passes all 25 permanent architecture predicates with machine status `recommendation_ready`.

**Accepted CrewAI architecture:** `docs/decisions/ADR-0012-crewai-flow-persistence-and-human-review-continuation.md`. The human approval decision is distinct from the machine recommendation. The selected path uses supported Flow, public `set_memory_storage_factory(...)`, `SQLiteFlowPersistence`, and `HumanFeedbackPending` / `from_pending()` / `resume()` while Drupal remains authoritative. Runtime `CheckpointConfig` and private `_skip_auto_memory` are nonselected.

**Gate 1 freeze:** `shared/contracts/GATE1-DRUPAL-AI-FREEZE.json` (`2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd`).

**Gate 2A freeze:** `shared/contracts/GATE2A-LANGGRAPH-FREEZE.json` (`a28361c34b9d1c2089eee786324ad34cffbf54e3495f59a276c489865e5630f0`).

**Completed Gate 2A package:** `gate-2a-step10-langgraph-certification-freeze-and-crewai-handoff-v1.0.1`.

**Gate 2A handoff package (historical next package):** `gate-2b-step01-crewai-contract-and-evidence-plan-v1.0.0`.

**Gate 2B Step 2B.03 authorization:** zero model/provider calls, zero successful outbound network connections, zero CrewAI-origin Drupal mutations, zero source-content mutations, zero authoritative human-review actions, zero dependency changes, zero live recommendation submissions, and zero Gate 2C executions.

Read `docs/gates/GATE-2B-STEP02-CREWAI-RUNTIME-PERSISTENCE-AND-CONTINUATION-PROBE.md`, `docs/gates/GATE-2B-STEP01-CREWAI-CONTRACT-AND-EVIDENCE-PLAN.md`, `docs/CODEX-GATE-2B-RUNBOOK.md`, and `docs/handoffs/GATE-2A-TO-CREWAI-HANDOFF.md`. Preserve the frozen dataset, model/settings, shared operations, validator, review destination and authority, source-mutation rule, idempotency identity, and reserved Gate 2C target-6/7 seam. Do not infer CrewAI behavior from LangGraph evidence.

Step 2B.03 completed its model-free shared-operation adapter boundary with accepted evidence `gate2b-step03-20260818T163812Z-7a58ef58`. Do not begin a later package until Step 2B.03 is committed, merged, resynchronized, and post-merge audited.

Accepted Step 2B.01 evidence run: `gate2b-step01-20260811T231020Z-00000002`
Accepted Gate 2B contract digest: `c734ad98f23c311e2141e6a50a876a6f5c9abf343e45884843848af1ef40ac77`

Accepted Step 2A.10 certification evidence: `evidence/gates/gate-2a/certification/gate2a-step10-20260811T034835Z-03f93652`

Accepted LangGraph batch: `evidence/results/langgraph/langgraph-20260810T231915Z-0027cd3e`

Accepted Gate 2A contract digest: `1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b`
