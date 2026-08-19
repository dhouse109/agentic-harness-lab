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

**Completed Step 2B.04 package:** `gate-2b-step04-crewai-canonical-vertical-slice-v1.0.0` completed the successful live run with immutable canonical evidence `crewai-20260818T215017Z-8e03fc95`. Same-step repair `gate-2b-step04-crewai-canonical-vertical-slice-v1.0.1` added model-free post-process-close provenance `gate2b-step04-closure-20260819T195009Z-60344274` and strengthened permanent-audit coverage without replaying the experiment. The result is not yet committed or merged. The recommendation remains pending Drupal-authoritative review; human-feedback continuation and later batch work remain unbegun.

Use `bash scripts/run-gate2b-step02-crewai-architecture-closure.sh audit` for the permanent closure check. Its `run` mode is restricted to the exact Step 2B.02 feature lifecycle; its `audit` mode validates retained evidence, hashes, ADR/closure provenance, and lifecycle state on legitimate commit and merge descendants without requiring `HEAD` to remain the pre-install predecessor.
