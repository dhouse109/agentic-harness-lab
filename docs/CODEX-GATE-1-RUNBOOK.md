# Local Codex Runbook for Gate 1

## Purpose

This runbook moves Gate 1 execution into Codex running locally inside WSL2 while preserving the
package-driven controls already used for Gate 0.5.

Codex performs local inspection, package creation, preview, approved execution, audit, evidence
review, repair, and commit preparation. The user retains approval at the package preview,
architecture-change, and commit boundaries.

## Prerequisites

- Repository checkout remains at `~/projects/agentic-harness-lab`.
- Docker CE, DDEV, Drupal, `uv`, Git, and GitHub CLI continue to work inside WSL2.
- The OpenAI API key and Drupal service credentials remain in their existing private local paths.
- The `main` branch includes `AGENTS.md` and this runbook.
- Gate 0.5 Step 05 audit passes.

## Install Codex inside WSL2

Follow the current official OpenAI Codex installation instructions for Linux/WSL2. After
installation, authenticate Codex with the intended ChatGPT account.

Verify from Ubuntu:

```bash
cd ~/projects/agentic-harness-lab
codex --version
git status --short
git branch --show-current
git rev-parse HEAD
bash scripts/run-gate05-step05.sh audit
```

Do not begin Gate 1 if the working tree is dirty for unexplained reasons or the Gate 0.5 audit fails.

## Package location

Delivery packages are intentionally external to Git:

```bash
mkdir -p ~/projects/agentic-harness-lab-packages
```

The first package should be created by Codex at:

```text
~/projects/agentic-harness-lab-packages/
  gate-1-step01-drupal-ai-batch-contract-v1.0.0/
```

Do not download, copy, or commit the previously generated chat package. Codex should construct the
first package locally from the merged repository state, current hashes, retained evidence, and the
approved Step 1 prompt. This ensures the package lineage begins from the exact local baseline.

## Start Codex

From the repository root:

```bash
cd ~/projects/agentic-harness-lab
codex
```

Codex should automatically read the repository-level `AGENTS.md`. Paste the prompt stored at:

```text
docs/prompts/CODEX-GATE-1-STEP01.md
```

## Step 1 interaction pattern

Codex should first report:

- Branch and current commit.
- Working-tree status.
- Gate 0.5 Step 05 audit result.
- Expected Step 1 predecessor and package output.
- Planned package and repository file changes.
- Any discrepancy between repository evidence and the Gate 1 plan.

Codex then creates the external package and runs:

```bash
bash ~/projects/agentic-harness-lab-packages/gate-1-step01-drupal-ai-batch-contract-v1.0.0/package.sh \
  preview ~/projects/agentic-harness-lab
```

Codex must stop after preview. Review its `KEEP`, `CREATE`, `UPDATE`, and `DELETE` plan. Approve only
when preview ends with `No files were changed.` and the scope matches Step 1.01.

After approval, Codex may run the package, installed runner, audits, evidence checks, Git diff, and
secret scan without asking the user to copy individual commands.

Codex then stops before commit and reports:

- Passing or failing package boundary.
- Evidence location and summary.
- Files changed.
- Secret scan result.
- Safe completion wording.
- Proposed commit message.

After commit approval, Codex may commit and push the Step 1 result. It must not begin Step 1.02 in the
same task.

## Continuing to later packages

For each later package, start a fresh Codex task or explicitly reset the task boundary. Tell Codex to
read:

- `AGENTS.md`.
- `docs/CURRENT-STATUS.md`.
- The latest package document, contract, evidence summary, and installed runner.
- The Gate 1 execution plan.

The next prompt should name exactly one package and preserve the same preview and commit stops.
Never ask Codex to "complete all of Gate 1" in one unattended run.

## Approval wording

A simple preview approval is enough:

```text
The preview scope is approved. Execute this package, run its installed audit and all declared checks,
repair the same package if necessary, and stop before commit with an evidence and diff summary. Do
not begin the next package.
```

A simple commit approval is enough:

```text
The package boundary and evidence are approved. Commit and push only the passing Step 1 changes using
the proposed commit message. Stop after push and report the commit SHA. Do not begin Step 2.
```

## Stop and return to planning when

- The pinned Drupal AI runtime contradicts the planned architecture.
- A frozen constant or shared semantic boundary needs to change.
- A dependency upgrade or contrib patch appears necessary.
- Credentials would need to be committed or exposed.
- The shared Gate 0.5 substrate would be bypassed or materially changed.
- Source Articles or image fields are mutated.
- The package cannot pass its declared boundary without changing scope.

These are architecture or experiment decisions, not routine debugging.
