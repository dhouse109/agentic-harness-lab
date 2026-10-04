# Codex Operating Instructions

> Gate 2C is terminally closed as `CLOSED_NON_CERTIFYING_WITH_INCOMPLETE_EVIDENCE`. Step 2C.02 is `TERMINAL_UNCERTIFIED`, never PASS or certified. Gate 2 remains `NOT_COMPLETE`. No further Gate 2C runtime, reset, certification, pointer, or identity activity is permitted.

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

Gate 1 Drupal AI, Gate 2A LangGraph, and Gate 2B CrewAI are certified and frozen. Gate 2 is the umbrella cross-framework milestone and remains incomplete. Gate 2C shared three-framework failure/recovery is terminally closed without certification and with incomplete evidence.

**Step 2B.01:** complete, merged, and post-merge audited.

**Completed Step 2B.02 package:** `gate-2b-step02-crewai-architecture-adr-and-closure-v1.0.0`.

**Step 2B.02:** complete, merged, resynchronized, and post-merge audited after retained model-free runtime evidence, permanent architecture audit, and explicit human architecture approval.

**Completed Step 2B.03 package:** `gate-2b-step03-crewai-shared-operation-adapters-v1.0.0`.

**Step 2B.03:** Package `gate-2b-step03-crewai-shared-operation-adapters-v1.0.0` is complete, committed, normally merged at `7629434b04d04154b9f219e1d93ed772401a1288`, resynchronized, and post-merge audited with accepted model-free evidence `gate2b-step03-20260818T163812Z-7a58ef58`.

**Completed Step 2B.04 packages:** `gate-2b-step04-crewai-canonical-vertical-slice-v1.0.0` and same-step repair `v1.0.1` are committed, normally merged at `c61d0b0213d754fcc40f18065836de6e0da70d2c`, resynchronized, and post-merge audited. Canonical evidence is `crewai-20260818T215017Z-8e03fc95`; closure evidence is `gate2b-step04-closure-20260819T195009Z-60344274`. Its recommendation was the frozen pending input to Step 2B.05 and is now approved in Drupal revision 22.

**Step 2B.05:** complete, normally merged at `2ad5fc9faf29bf54983ae2c61f3f7cb0f9b28148`, resynchronized, and post-merge audited. Final repair `gate-2b-step05-crewai-drupal-authoritative-human-review-continuation-v1.0.2` completed continuation `gate2b-step05-20260825T192434Z-ff4f89dd` for source/application/Flow `crewai-20260818T215017Z-8e03fc95`. Process A persisted one `HumanFeedbackPending`; `editor_dana` approved the existing recommendation as-is at unpublished Drupal revision 22; Process B called public `from_pending(...)` once and `resume(...)` once, cleared pending rows `1 -> 0`, and preserved the same Flow identity. Second authoritative reconstruction/resume attempts, prior-work replay, additional model/provider activity, submissions, Drupal writes from Process B, and source Article/image-alt writes were all zero. The successful 15-file evidence family has manifest `7f3294f75be9602d55c27f66a6c084784b9571d12ced26a2e08234af66d0dd24`; Process A manifest `154b2242bd0a8f37a8392c5d9c68071fef58790a3439a79f983c7d3b8e7a4f23` and review manifest `f58357f484bac5470ea826da4b3e64b92cddacc1d222544c21ea9aa519e891e8` remain immutable. The completed runtime is local-only, has zero pending rows, and must not be staged.

**Step 2B.06:** complete, normally merged at `78ba79165378ac2905801d994682aa385cdfb607`, resynchronized, and post-merge audited. Successful run `crewai-20260827T174606Z-6249d844` completed the frozen 12 targets with exactly 12 logical generations, provider requests/responses, and submissions; all retry/correction/repair/fallback/learning/feedback-collapse counts and source mutations were zero. The earlier zero-provider HTTP failure and disposition, authenticated-readiness repair, immutable batch stage, governance supplement, exactly-once restoration, 19-file final closure, and final-governance bridge remain preserved. The permanent composite auditor reports `STEP_2B_06_COMPLETE` / `RESTORE_VERIFIED` / `FINAL_GOVERNANCE_ACCEPTED` / `SNAPSHOT_RETAINED` on the normal-merge descendant.

**Step 2B.07:** complete, normally merged at `50e7296406a39de23b20bdfb1b45960dca13d3a1`, and post-merge audited. Accepted synthesis `gate2b-step07-20260828T135201Z-1ed07bea` is immutable and must never be rerun or rewritten.

**Step 2B.08:** complete after permanent acceptance of its exactly-once certification family, `shared/contracts/GATE2B-CREWAI-FREEZE.json`, freeze-bound handoff, and exact pointer. Gate 2B is certified and frozen. Gate 2C is closed non-certifying; no shared recovery result or winner exists, and no production-readiness or framework-superiority claim is permitted.

**Step 2C.01:** complete after accepted model-free contract certification. It freezes the target-6/7 semantic seam, evidence overlays, accounting/classification rules, protected-tree policy, and approval ledger without executing Gate 2C. The corrected-environment Step 2C.02 offline rehearsal is finalized PASS, and the public `SQLiteFlowPersistence.load_state(...)` plus `Flow.kickoff(inputs={"id": same_flow_id})` CrewAI recovery candidate is explicitly human-approved for the model-free architecture proof only. Step 2C.02 remains uncertified. The Drupal persistent-lock policy is approved as contract policy only, not as authorization to execute recovery.

**Step 2C.02 terminal disposition:** `TERMINAL_UNCERTIFIED`. The corrected-environment LangGraph and CrewAI model-free recovery rehearsal passed, and the CrewAI architecture is human-approved for that model-free proof only. Three immutable Drupal starts remain failed-preserved. The final family retained the target-6 seam and exact signal-command/process boundary but lacks a certifying termination artifact and immediate pre-expiry lock-denial observation. The one post-expiry partial observation is useful but explicitly non-certifying. Reset was not performed because its existing eligibility predicate was never met.

**Gate 2C final disposition:** `CLOSED_NON_CERTIFYING_WITH_INCOMPLETE_EVIDENCE`. This means the authorized evidence record is final and no useful or permitted runtime work remains; it does not mean PASS, completion, certification, or a valid three-framework recovery comparison. Gate 2 remains `NOT_COMPLETE` because the umbrella exit criteria in `docs/gates/GATE-2-STRUCTURE.md` were not satisfied.

**No-more-runtime boundary:** additional worker identities `0`; replacement slots `0`; worker retry `false`; automatic retry `false`; partial-observation invocations `1` of maximum `1`. Do not invoke another worker, replacement, post-expiry observation, immediate observation, failed-start retry, reset, Step 2C.02 certification, Step 2C.03 activity, pointer update, or evidence identity allocation.

**Step 2B.05 historical lessons:** the v1.0.0 Boundary A attempt failed closed before runtime copy or Flow creation because import-time XDG storage pre-created the runtime candidate; consumed identity `gate2b-step05-20260820T151225Z-8b7fa221` remains local and is never reused. v1.0.1 separated disposable XDG and authoritative runtime paths. v1.0.2 removed the live post-clear reconstruction control so the authoritative path was exactly-once while retaining that negative control in disposable rehearsal. The restricted Codex sandbox asyncio/thread wakeup issue was environmental, not a CrewAI HITL defect; persistence alone is not continuation; Drupal remained the sole human-review authority.

**Retained diagnostic Step 2B.02 run:** `gate2b-step02-20260812T010531Z-00000001` is byte-valid diagnostic evidence but is superseded/unaccepted for architecture selection. Its original mechanical audit passed; later integrity review found unlabeled private Flow instrumentation and incomplete isolation/retry predicates. At that capture boundary, Step 2B.02 remained open.

**Retained superseding Step 2B.02 capture:** `gate2b-step02-20260812T015108Z-00000001` passed its v2 capture boundary and remains byte-identical, with architecture status `unresolved`.

**Retained targeted Step 2B.02 supplemental capture:** `gate2b-step02-followup-20260812T022947Z-00000001` remains byte-identical. It corrected native structured-output fallback and checkpoint semantics, while its immutable classifier retained four version-check events as `unresolved_path`.

**Accepted governed Step 2B.02 disposition:** `gate2b-step02-disposition-20260812T024610Z-00000001` separately binds the immutable call stacks to pinned-source version-check provenance, verifies the public disable control, and passes all 25 permanent architecture predicates with machine status `recommendation_ready`.

**Accepted CrewAI architecture:** `docs/decisions/ADR-0012-crewai-flow-persistence-and-human-review-continuation.md`. The human approval decision is distinct from the machine recommendation. The selected path uses supported Flow, public `set_memory_storage_factory(...)`, `SQLiteFlowPersistence`, and `HumanFeedbackPending` / `from_pending()` / `resume()` while Drupal remains authoritative. Runtime `CheckpointConfig` and private `_skip_auto_memory` are nonselected.

**Gate 1 freeze:** `shared/contracts/GATE1-DRUPAL-AI-FREEZE.json` (`2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd`).

**Gate 2A freeze:** `shared/contracts/GATE2A-LANGGRAPH-FREEZE.json` (`a28361c34b9d1c2089eee786324ad34cffbf54e3495f59a276c489865e5630f0`).

**Completed Gate 2A package:** `gate-2a-step10-langgraph-certification-freeze-and-crewai-handoff-v1.0.1`.

**Gate 2A handoff package (historical next package):** `gate-2b-step01-crewai-contract-and-evidence-plan-v1.0.0`.

**Gate 2B Step 2B.04 observed authorization:** exactly one logical generation, one physical provider request, one successful provider response, and one shared-operation recommendation mutation occurred. Provider/transport/guardrail/repair/fallback/learning retries or calls, source-content mutations, human-review actions, dependency changes, and Gate 2C executions remained zero.

Read `docs/gates/GATE-2B-STEP02-CREWAI-RUNTIME-PERSISTENCE-AND-CONTINUATION-PROBE.md`, `docs/gates/GATE-2B-STEP01-CREWAI-CONTRACT-AND-EVIDENCE-PLAN.md`, `docs/CODEX-GATE-2B-RUNBOOK.md`, and `docs/handoffs/GATE-2A-TO-CREWAI-HANDOFF.md`. Preserve the frozen dataset, model/settings, shared operations, validator, review destination and authority, source-mutation rule, idempotency identity, and reserved Gate 2C target-6/7 seam. Do not infer CrewAI behavior from LangGraph evidence.

Package `gate-2b-step03-crewai-shared-operation-adapters-v1.0.0` is complete, committed, normally merged at `7629434b04d04154b9f219e1d93ed772401a1288`, resynchronized, and post-merge audited with accepted model-free evidence `gate2b-step03-20260818T163812Z-7a58ef58`. Steps 2B.05–2B.08 are complete. Never rerun the consumed Step 2B.05 continuation, either Step 2B.06 run identity, the Step 2B.06 restoration, the accepted Step 2B.07 synthesis, or the Step 2B.08 certification identity; never modify their evidence or runtimes. Retain the Step 2B.06 recovery snapshot because permanent audit still proves `SNAPSHOT_RETAINED`. Gate 2C is terminally closed without certification; Gate 2 remains incomplete.

Accepted Step 2B.01 evidence run: `gate2b-step01-20260811T231020Z-00000002`
Accepted Gate 2B contract digest: `c734ad98f23c311e2141e6a50a876a6f5c9abf343e45884843848af1ef40ac77`

Accepted Step 2A.10 certification evidence: `evidence/gates/gate-2a/certification/gate2a-step10-20260811T034835Z-03f93652`

Accepted LangGraph batch: `evidence/results/langgraph/langgraph-20260810T231915Z-0027cd3e`

Accepted Gate 2A contract digest: `1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b`
