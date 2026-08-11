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

Step 2B.01 freezes the contract and evidence plan with zero model calls, zero CrewAI-origin Drupal mutations, zero dependency changes, and zero Gate 2C executions.

The next model-free question is defined in `docs/gates/GATE-2B-STEP01-CREWAI-CONTRACT-AND-EVIDENCE-PLAN.md`. Do not implement it until Step 2B.01 passes, is committed and merged, local `main` is resynchronized, and the post-merge audit passes.
