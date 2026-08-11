# Gate 2A Step 2A.09 — LangGraph Evidence, Claims, and Comparison Matrix

**Package:** `gate-2a-step09-langgraph-evidence-claims-and-matrix-v1.0.4`
**Expected predecessor:** `28e8e93fc7805449debbb1df3336bf06e3959e7c`
**Gate 2A contract SHA-256:** `1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b`

## Purpose

Synthesize the already-accepted LangGraph evidence into claim-safe repository records and the
organ-by-organ comparison matrix. This step does not rerun LangGraph, call a model, create a
recommendation, touch Drupal semantic routes, perform human review, or exercise Gate 2C.

Step 2A.08 remains the certification-candidate batch. Step 2A.10 will perform the model-free
Gate 2A certification/freeze/handoff after this evidence synthesis is committed, merged, local
`main` is resynchronized, and the post-merge audit passes.

## Evidence sources

The synthesis is restricted to accepted retained evidence already named by merged `main`:

- Step 2A.03 tool adapters: `evidence/gates/gate-2a/tool-adapters/gate2a-step03-20260809T233127Z-2375581`
- Step 2A.03 compliance verification: `evidence/gates/gate-2a/tool-adapters/gate2a-step03-verification-20260810T020210Z-2410520`
- Step 2A.04 checkpoint proof: `evidence/gates/gate-2a/checkpoint-proof/gate2a-step04-20260810T034027Z-00250b07`
- Step 2A.05 canonical slice: `evidence/gates/gate-2a/canonical-slice/gate2a-step05-20260810T140133Z-0025b888`
- Step 2A.06 human interrupt/review: `evidence/gates/gate-2a/human-interrupt/gate2a-step06-20260810T162448Z-002692eb`
- Step 2A.08 accepted batch: `evidence/results/langgraph/langgraph-20260810T231915Z-0027cd3e`

The original Step 2A.08 failed-run/privacy-salvage lineage remains retained and is not rewritten.

## Official-source pairing

Step 2A.09 resolves the seeded LangGraph source placeholders in `SOURCES.md` against current
official LangChain/LangGraph documentation reviewed on 2026-08-10:

- `SRC-LG-001` — LangGraph persistence documentation:
  `https://docs.langchain.com/oss/python/langgraph/persistence`
- `SRC-LG-002` — LangGraph interrupts documentation:
  `https://docs.langchain.com/oss/python/langgraph/interrupts`
- `SRC-LG-003` — LangChain tools documentation:
  `https://docs.langchain.com/oss/python/langchain/tools`

The official documentation explains framework mechanisms. Local retained evidence remains the
proof of this repository's exact behavior.

## Claim disposition

Step 2A.09 does not promote broad superiority or untested failure claims.

- `CLM-LG-001` remains `hypothesis`: the experiment has not established that LangGraph has the
  broadest integration surface of the three specimens.
- `CLM-LG-003` remains `hypothesis`: the no-persistence-path termination behavior has not been run.
- Cross-framework and CrewAI claims remain unchanged because CrewAI has not been implemented yet.
- Gate 2C process-failure/recovery claims remain open.

The step may promote narrowly scoped LangGraph mechanism claims only when the repository's
`verified` rule is met: official source + pinned version + repeatable local test + retained evidence.
A local privacy/context-retention observation that does not need an external mechanism claim remains
`observed` rather than being overstated as `verified`.

## Comparison-matrix scope

Populate only the LangGraph rows for the six common organs:

1. Context
2. Tools
3. State and memory
4. Verification
5. Human review
6. Lifecycle and recovery

Each safe conclusion names a LangGraph claim ID. Drupal AI rows remain unchanged. CrewAI rows remain
`TODO` / `not observed`. Cross-framework conclusions remain prohibited until later gates.

## Model / Drupal budget

- model/provider calls: **0**
- Drupal semantic calls: **0**
- recommendation writes: **0**
- Drupal source mutations: **0**
- human-review actions: **0**
- Gate 2C failure injection: **0**

## Retained Step 2A.09 evidence

A model-free synthesis record is retained under:

`evidence/gates/gate-2a/evidence-claims/<run-id>/`

with:

- `summary.json`
- `claim-evidence-map.json`
- `source-pairing.json`
- `repair-v1.0.4.json`
- `package-files-sha256.txt`

`GATE2A-STEP09-LATEST.txt` points to the accepted synthesis run.

## Pass criteria

Step 2A.09 passes only when:

- merged Step 2A.08 evidence remains the accepted LangGraph batch;
- all six LangGraph organ rows are populated from retained LangGraph evidence;
- every LangGraph matrix safe conclusion names a claim ID;
- `CLM-LG-001` and `CLM-LG-003` remain hypotheses;
- CrewAI and cross-framework claims are not promoted;
- Gate 2C is not represented as completed;
- `SRC-LG-001`, `SRC-LG-002`, and `SRC-LG-003` point to official documentation;
- promoted `verified` claims satisfy the repository's source + pinned-version + local-test + retained-evidence rule;
- the Step 2A.08 failed-run/privacy-salvage lineage remains preserved;
- Gate 0.5, Gate 1, and Gate 2A frozen digests remain unchanged;
- no model/provider call or Drupal semantic call/mutation occurs;
- lifecycle documents mark Step 2A.09 complete and keep Step 2A.10 locked until commit/merge/resync/post-merge audit.

**Next package after commit/merge/resync/post-merge audit:**

`gate-2a-step10-langgraph-certification-freeze-and-crewai-handoff-v1.0.0`


## v1.0.1 preventive hardening before first preview

v1.0.0 was reviewed before the user ran either `preview` or `run`; it therefore produced no repository mutation, evidence run, model/provider call, Drupal semantic call/mutation, or branch. v1.0.1 preserves the Step 2A.09 evidence/claim semantics while hardening package mechanics against failure classes observed in earlier gates:

- preview and install both fail closed if model/provider variables, Step 2A.08 live authorizations, or Drupal credential variables are set;
- repository validation performs `git fetch --prune origin` before trusting `origin/main` or remote-branch absence, preventing a stale tracking ref from authorizing work against an advanced remote;
- the package self-check enforces an exact source-file allowlist, rejects symlinks, and keeps bytecode/cache artifacts out of the archive;
- preview validates that the new `SRC-LG-003` source ID is absent and proves the repository remains unchanged afterward;
- rollback traps are armed before branch creation and use explicit signal exit codes; rollback verifies exact clean-main restoration;
- post-apply scope validation requires exactly the intended tracked and untracked paths and an empty staging area before candidate audits;
- the Step 2A.09 auditor validates the preserved Step 2A.08 privacy-failure/salvage semantics, 12/12 call counters, exact claim disposition set, and source-pairing map; and
- source-register wording distinguishes current official documentation from the locally pinned LangGraph/LangChain/checkpointer versions instead of implying that the unversioned documentation URL itself is pinned to those package versions.

These changes are package-safety/audit hardening only. The model/Drupal budget remains zero, CrewAI and cross-framework conclusions remain unobserved, and Gate 2C remains unopened.

## v1.0.2 canonical lifecycle-anchor repair

The first human-run v1.0.1 `preview` passed model-free environment checks, package self-checks,
syntax checks, the reviewed Step 2A.08 predecessor audit, clean-main validation, and frozen-contract
checks, then stopped before repository mutation because the package payload expected the stale text
`Step 2A.01through Step 2A.08` in `docs/CURRENT-STATUS.md`. The canonical merged Step 2A.08 file
contains `Step 2A.01 through Step 2A.08` with a space.

v1.0.2 changes only that lifecycle anchor/output wording and package-version bookkeeping. It also adds
a package self-check that requires the canonical spaced anchor and rejects the stale no-space variant.
The failed v1.0.1 preview created no branch, evidence run, model/provider call, Drupal semantic call or
mutation, staging change, or repository file modification.


## v1.0.4 lifecycle-normalization repair

The v1.0.3 repair preview was never installed. It stopped model-free before repository mutation because
its preflight required one exact noncanonical Step 2A.09 lifecycle sentence. That condition was too brittle
for the intentionally unstaged installed tree: the repair only needs to recognize the current lifecycle
form and guarantee the canonical result.

v1.0.4 accepts exactly one recognized Step 2A.09 lifecycle form (canonical spaced or the reviewed
missing-space variant), records which form was actually observed (`canonical-spaced`), and guarantees the final
canonical sentence `Step 2A.01 through Step 2A.09`. It also updates package-version/repair bookkeeping and
strengthens the permanent auditor to require the canonical spaced form and reject the stale missing-space
form. The exact accepted Step 2A.09 synthesis run, LangGraph claim semantics, source pairings, comparison
matrix observations, Step 2A.08 failed-run/privacy-salvage lineage, and frozen contracts are unchanged.
No model/provider call, Drupal semantic call/mutation, human review, recommendation write, or Gate 2C
action is performed by this repair.
