# Codex Gate 2B Runbook

## Scope

Gate 2B builds and certifies the CrewAI specimen one approved external delivery package at a time. Gate 2C remains deferred and unclaimed.

Read `AGENTS.md`, `docs/CURRENT-STATUS.md`, the frozen predecessor artifacts, `docs/handoffs/GATE-2A-TO-CREWAI-HANDOFF.md`, the current Gate 2B document, applicable schemas/contracts, accepted evidence, `crewai/pyproject.toml`, and `crewai/uv.lock` before each boundary. Revisit the external Gate 2B lessons and preventive guardrails at every package boundary; the external reference files are not repository evidence.

## Package workflow

1. Establish repository identity, synchronized `main`, exact predecessor, clean tree, and permanent predecessor audits before mutation.
2. Inspect every overwrite and predecessor anchor against the actual current lifecycle state.
3. Create only the current delivery package under `~/projects/agentic-harness-package-staging/`.
4. Run package self-check and preview. Preview must report exact actions and finish with `No files were changed.`
5. Stop for human execution approval.
6. After approval, install only the previewed package and run its focused evidence runner.
7. Inspect evidence, exact manifests, hashes, logs, status pointers, Git status, and diffs directly.
8. Repair only the same package for bounded defects. Preserve failed evidence and valid model evidence.
9. Stop before commit; after approval, commit only intended repository artifacts and sanitized evidence.
10. Do not create the next package until merge/resync and its required post-merge audit pass.

## Preventive controls

- Validate before branch creation.
- Treat auditors as pre-activation, lifecycle-sensitive, permanent, post-certification, or post-merge; invoke only in the lifecycle they support.
- Propagate shell failures explicitly. Do not mask a required command failure in a declaration or unchecked command substitution.
- Resolve real paths, Git SHAs/refs, JSON fields, and hashes fail-closed.
- Limit rollback to the package's exact mutation allowlist.
- Distinguish terminal rendering from repository bytes before considering a repair.
- Preserve valid experiment evidence when tooling or lifecycle bookkeeping needs repair.
- Give important predecessor evidence immutable commit/freeze provenance.
- Require exact significant evidence sets and complete SHA-256 manifests.
- Support every later freeze claim with retained evidence and a permanent certification check.

## CrewAI-specific controls

- Use Python `3.12.13`, CrewAI `1.15.10`, and CrewAI Tools `1.15.10` from the lock; do not upgrade or patch them.
- Keep framework runtime state and storage CrewAI-owned, outside `shared/`, with explicit sanitized paths.
- Do not infer persistence, continuation, retry, isolation, or feedback behavior from LangGraph.
- Keep Drupal `alt_text_suggestion` review by `editor_dana` authoritative.
- Expose model-call and Drupal-mutation budgets during every later package preview and stop before crossing them.
- Keep raw structured output, assembly, deterministic validation, submission, state, review, and continuation evidence separate.
- Do not hide framework semantic retries or introduce retries in adapters.
- Label CrewAI-specific continuation accurately; it is not Gate 2C.

## Current boundary

Step 2B.02 is complete with four immutable model-free evidence boundaries, a governed machine recommendation, explicit human architecture approval, ADR-0012, and a permanent closure audit. Machine status `recommendation_ready` and human status `approved` are separate provenance facts.

The approved architecture uses supported CrewAI Flow, public `set_memory_storage_factory(...)`, `SQLiteFlowPersistence`, and `HumanFeedbackPending` / `from_pending()` / `resume()` while Drupal remains authoritative. Runtime `CheckpointConfig` and private `_skip_auto_memory` are nonselected. Later inference must use zero transport/guardrail retries, fail-closed structured output, explicit fallback accounting, `learn=False`, and complete SDK/provider request counting.

Step 2B.02 is committed, merged, locally resynchronized, and post-merge audited. Package `gate-2b-step03-crewai-shared-operation-adapters-v1.0.0` is complete, committed, normally merged at `7629434b04d04154b9f219e1d93ed772401a1288`, resynchronized, and post-merge audited with accepted model-free evidence `gate2b-step03-20260818T163812Z-7a58ef58`.

**Completed Step 2B.04 packages:** `gate-2b-step04-crewai-canonical-vertical-slice-v1.0.0` and repair `v1.0.1` are committed, normally merged at `c61d0b0213d754fcc40f18065836de6e0da70d2c`, resynchronized, and post-merge audited. Its recommendation was the frozen pending input to Step 2B.05 and is now approved at unpublished Drupal revision 22.

**Completed Step 2B.05:** final repair v1.0.2 completed `gate2b-step05-20260825T192434Z-ff4f89dd` for source/application/Flow `crewai-20260818T215017Z-8e03fc95`. Boundary A persisted one public pending context, Boundary B captured one real `editor_dana` approve-as-is Drupal review at revision 22, and Boundary C called public `from_pending(...)` once and `resume(...)` once, then cleared pending rows `1 -> 0`. Second authoritative attempts, prior-work replay, additional model/provider activity, submissions, Process B Drupal writes, and source writes were zero. The permanent audit and privacy scan pass; the 15-file final evidence manifest is `7f3294f75be9602d55c27f66a6c084784b9571d12ced26a2e08234af66d0dd24`. It is normally merged at `2ad5fc9faf29bf54983ae2c61f3f7cb0f9b28148`, resynchronized, and post-merge audited.

The live continuation is consumed and complete. Never call `from_pending(...)` or `resume(...)` again for `gate2b-step05-20260825T192434Z-ff4f89dd`, never reuse that continuation ID, and never treat the local-only terminal runtime as tracked evidence.

**Step 2B.06 transaction:** consumed run `crewai-20260827T125501Z-c5381188` remains a permanent zero-provider pre-target failure. Distinct run `crewai-20260827T174606Z-6249d844` completed all 12 frozen targets with exact 12/12 accounting and zero retry/correction/repair/fallback/learning/feedback-collapse/source mutation. Restore-only ran exactly once; the immutable 19-file closure and final-governance bridge record `RESTORE_VERIFIED` / `STEP_2B_06_COMPLETE` / `FINAL_GOVERNANCE_ACCEPTED`. Normal merge `78ba79165378ac2905801d994682aa385cdfb607` preserves the feature commit and passes the permanent composite audit. Never rerun either batch identity, restore again, alter historical evidence, or delete the retained snapshot while `SNAPSHOT_RETAINED` remains an audit predicate.

**Step 2B.07 synthesis:** run only `scripts/run-gate2b-step07-crewai-evidence-synthesis-and-comparison.sh run <repo> <run-id>` after the package boundary is approved. It reads accepted evidence, writes one five-file model-free synthesis family plus a package-defined pointer, and runs the permanent auditor. It must not call a provider, write Drupal, create a CrewAI experiment runtime, operate on snapshots, or modify predecessor evidence. Every promoted claim needs an exact claim/proof record; `architecture/probe`, `hypothesis`, `unsupported`, and `gate-2c-deferred` remain distinct. Step 2B.08 alone may certify/freeze Gate 2B.

Historical lessons remain controlling: the consumed v1.0.0 identity `gate2b-step05-20260820T151225Z-8b7fa221` failed closed because XDG storage was placed below the candidate runtime; v1.0.1 separated those namespaces. The restricted Codex sandbox asyncio/thread wakeup issue was environmental, not a CrewAI HITL defect. v1.0.2 moved the post-clear second-reconstruction negative control to disposable rehearsal so live continuation stayed exactly-once. Persistence is not continuation, and Drupal remains the sole human-review authority.

Use `bash scripts/run-gate2b-step02-crewai-architecture-closure.sh audit` for the permanent closure check. Its `run` mode is restricted to the exact Step 2B.02 feature lifecycle; its `audit` mode validates retained evidence, hashes, ADR/closure provenance, and lifecycle state on legitimate commit and merge descendants without requiring `HEAD` to remain the pre-install predecessor.
