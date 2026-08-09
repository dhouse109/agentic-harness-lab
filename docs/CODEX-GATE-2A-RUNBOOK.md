# Codex Gate 2A Runbook

## Scope

This runbook governs package-driven LangGraph execution for Gate 2A. The repository, frozen contracts/hashes, retained evidence, and `docs/CURRENT-STATUS.md` remain authoritative.

## Package workspace

Use the external package root:

```text
~/projects/agentic-harness-package-staging/
```

Never commit extracted delivery packages, package archives, backups, or temporary package-install state.

## One-package-at-a-time workflow

```text
sync main
→ verify branch / HEAD / clean tree
→ verify Gate 1 permanent audit and freeze
→ create one step branch
→ generate only the next external package
→ package self-check
→ package preview
→ human package-boundary approval
→ package install/run
→ installed runner setup/preflight
→ explicit live-run approval before model calls or bounded Drupal writes
→ execute
→ audit
→ inspect retained evidence and hashes
→ inspect diff
→ exact-scope stage
→ staged diff + secret scan
→ human commit approval
→ commit / push / PR / merge
→ sync main
→ post-merge audit
→ next package only
```

Step 2A.01 has no model or Drupal mutation boundary, but the package preview approval and commit approval remain mandatory.

## Codex capability disposition at Gate 2A kickoff

Local preflight on August 9, 2026 reported:

- `codex-cli 0.146.1`
- `multi_agent`: stable / enabled
- `multi_agent_v2`: stable / disabled
- no relevant multi-agent/worktree configuration lines returned
- one Git worktree at the authoritative checkout

This is **Disposition B**: multi-agent is available, but no proven worktree isolation exists. Same-checkout subagents are read-only only. They may scout installed source, review contracts, review tests, or audit evidence; they must not concurrently write repository files, mutate Drupal, write authoritative checkpoint state, finalize the same evidence directory, or stage/commit.

If explicit Git worktree isolation is later established, isolated agents may draft model-free changes, but the coordinator remains the sole integrator and all shared Drupal/evidence mutation remains serial.

## Gate 2A frozen boundaries

Preserve the frozen dataset, target order/hash, model/settings, validator, four shared semantic operations, review destination, source nonmutation rule, and target-6/7 seam. A material change requires an ADR plus invalidated-evidence review.

Framework-owned LangGraph state/checkpointing must not be placed in `shared/`. Prefer a per-run SQLite checkpoint database under a gitignored LangGraph runtime root, with exact API/path finalized by Step 2A.02.

## Human review

Do not add a second approval system. LangGraph checkpoints/interrupts around the real Drupal `alt_text_suggestion` review boundary and resumes the same run/thread after `editor_dana` acts.

## Evidence/privacy

Never retain or print credentials, authorization headers, raw Base64/data URLs, private database exports, hidden reasoning, or unrelated private config. Do not request chain of thought.

## Current boundary

Step 2A.01 freezes the contract only. Do not draft or execute Step 2A.02 until Step 2A.01 is applied, audited, committed, merged, local `main` is resynchronized, and the post-merge audit passes.
