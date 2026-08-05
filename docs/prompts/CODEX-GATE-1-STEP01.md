# Codex Prompt — Gate 1 Step 1.01

You are taking over local execution of Gate 1 for the `agentic-harness-lab` repository.

Operate as the implementation agent and evidence custodian. Work directly in the current WSL2
environment using the installed Docker CE, DDEV, Drupal site, Python environments, Git repository,
private local credentials, snapshots, and retained evidence.

Follow `AGENTS.md` as binding repository instructions.

Read these files before proposing or changing anything:

- `AGENTS.md`
- `docs/CURRENT-STATUS.md`
- `PLAN.md`
- `README.md`
- `EXPERIMENT_SPEC.md`
- `CLAIMS_REGISTER.md`
- `COMPARISON_MATRIX.md`
- `docs/gates/`
- `docs/decisions/`
- `docs/handoffs/`
- `shared/contracts/`
- `shared/schemas/`
- the Gate 0.5 certification and retained Step 05 evidence
- the Gate 1 Package Execution Plan if it is present in the repository

The Gate 1 workflow is package-driven and sequential:

1. Verify the clean working tree, current branch, expected commit lineage, pinned versions, and Gate
   0.5 certification.
2. Create only the next declared Gate 1 package.
3. Create the delivery package outside the Git repository under
   `~/projects/agentic-harness-lab-packages/`.
4. Inspect every proposed overwrite and predecessor requirement.
5. Run the package's `preview` mode.
6. Present the exact `KEEP`, `CREATE`, `UPDATE`, and `DELETE` plan and stop for my package-boundary
   approval.
7. After approval, run the package installation.
8. Run the installed runner's focused audit.
9. Inspect all generated evidence directly; do not ask me to paste terminal output that you can read
   yourself.
10. Run syntax, schema, configuration, source-non-mutation, Git, and secret-hygiene checks appropriate
    to the package.
11. Repair the same package and repeat preview/run/audit if its declared boundary does not pass.
12. Do not call the package successful merely because installation completed.
13. Prepare a concise evidence summary, Git diff summary, safe completion statement, and proposed
    commit message.
14. Stop before commit for my approval.
15. Do not generate the next package until the current package passes, is approved, and is committed.

Begin with only:

```text
gate-1-step01-drupal-ai-batch-contract-v1.0.0
```

Do not call a model, mutate Drupal state, change dependencies, recertify Gate 0.5, or begin Step 1.02
during this task.

Preserve all frozen experiment constants. Never expose API keys, Basic Auth credentials,
authorization headers, raw Base64 image data, private database exports, or hidden model reasoning.
Do not use unrestricted execution, patch contributed modules, silently upgrade packages, bypass the
certified Gate 0.5 operations, or directly mutate source Articles.

First report:

- Current branch and commit.
- Working-tree status.
- Gate 0.5 certification status.
- Expected Step 1 predecessor and output.
- Files you expect the delivery package to contain.
- Files you expect the package to create or update inside the repository.
- Any discrepancy between the repository and the Gate 1 plan.

Then build the package and run preview. Stop after preview for approval.
