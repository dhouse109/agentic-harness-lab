# Gate 2B Step 2B.07 — CrewAI Evidence Synthesis and Comparison

## Status

Packages: original synthesis `gate-2b-step07-crewai-evidence-synthesis-and-comparison-v1.0.0`;
audit-composition repair `gate-2b-step07-crewai-evidence-synthesis-and-comparison-v1.0.1`.

This is a model-free, Drupal-read-only synthesis boundary. It reads accepted evidence and updates
claim/comparison wording; it does not rerun framework behavior. Step 2B.08 certification/freeze and
Gate 2C shared failure/recovery remain separate and unstarted.

The v1.0.0 synthesis executed exactly once as
`gate2b-step07-20260828T135201Z-1ed07bea` and created its immutable five-file family. Acceptance
failed closed because the Step 2B.07 auditor invoked the historical Gate 2A.10 mutable-document
equality predicate against intentionally evolved Step 2B.07 claim/comparison/source documents. The
failure was `Step 2A.10 changed CLAIMS_REGISTER.md`. This is a lifecycle-composition incompatibility,
not Gate 2A evidence corruption or synthesis corruption. No pointer was created.

## Predecessor

The required predecessor is normal merge `78ba79165378ac2905801d994682aa385cdfb607`, with parents:

1. `2ad5fc9faf29bf54983ae2c61f3f7cb0f9b28148`
2. `715aebd42d759f14bc71aac8cff12cec7725b595`

Before acceptance, the permanent Step 2B.06 composite audit and lifecycle-correct Gate 2A
certification/preservation composition must pass. The retained Step 2B.06 snapshot remains present and byte-identical because
`SNAPSHOT_RETAINED` is still a predecessor predicate.

## Gate 2A lifecycle composition

The unchanged Gate 2A.10 auditor is valid at its own certification lifecycle. It intentionally
freezes `CLAIMS_REGISTER.md`, `COMPARISON_MATRIX.md`, and `SOURCES.md` to Step 2A.09 merge
`f3daab20509c72aebf8536bcb7742f1a3e9f504f`. Gate 2A.10 feature commit
`1a32f8584a75dc59533f48dfb0b7636da94d5a00` was normally merged as
`0477e882987501438ae07fbb51e741b4be800843`.

The repaired audit asks two separate questions:

1. Historical validity: a disposable detached checkout at `0477e882...` runs the unchanged
   historical auditor and must pass.
2. Current preservation: the current descendant must retain the exact Gate 2A freeze SHA
   `a28361c34b9d1c2089eee786324ad34cffbf54e3495f59a276c489865e5630f0`, the exact certification
   ancestry, and all 245 certified frozen paths byte-for-byte.

The three later-mutable synthesis documents are deliberately excluded from current-byte equality.
Running the historical auditor directly against current Step 2B.07 documents remains an expected
failure and is retained as a rehearsal control. No Gate 2A auditor, evidence, contract, or freeze is
modified.

## Claim strengths

- `verified`: official pinned-version source plus retained local behavior evidence.
- `observed`: retained authoritative local behavior evidence without a complete official-source
  pairing for the exact claim.
- `architecture/probe`: pinned source/runtime inspection or model-free probing; not promoted to
  live-experiment behavior.
- `documented`: code or contract exists, but the behavior was not independently observed.
- `hypothesis`: experiment question or proposal prediction.
- `unsupported`: retained evidence does not support the claim; do not use.
- `gate-2c-deferred`: the shared three-framework failure/recovery experiment has not run.

Every non-hypothesis material CrewAI claim in the synthesis family records its claim ID, text,
strength, framework, six-organ category, exact evidence path/hash bindings, official source IDs when
required, permanent-auditor predicate, comparison-safe wording, and prohibited overstatement.

## Six-organ comparison

The comparison holds the frozen task and constants fixed and distinguishes:

- context;
- tools;
- state;
- verification;
- human review;
- lifecycle.

Each organ identifies the shared semantic boundary, framework-owned mechanism, evidence strength,
material observed difference, and remaining uncertainty. Evidence history is not flattened: the
LangGraph privacy self-match failure and separate salvage remain explicit, as do the CrewAI failed
HTTP attempt and disposition. Framework-specific continuation, persistence, and restoration are not
the identical shared Gate 2C experiment.

## Evidence family

The already-consumed v1.0.0 execution created exactly one family below:

`evidence/gates/gate-2b/evidence-synthesis/gate2b-step07-20260828T135201Z-1ed07bea/`

with exactly five files:

1. `claim-proof-map.json`
2. `comparison-synthesis.json`
3. `privacy-scan.json`
4. `summary.json`
5. `evidence-manifest.json`

The manifest contains exact hashes and sizes for the other four files. v1.0.1 never invokes the
synthesis generator and rejects every other synthesis identity. Only after the repaired recovery
audit accepts this exact family may the package create
`evidence/gates/gate-2b/evidence-synthesis/GATE2B-STEP07-LATEST.txt`; permanent mode then requires
that exact pointer. No predecessor or synthesis evidence is rewritten.

## Activity boundary

The synthesis performs zero model generations, provider requests/responses, recommendation
submissions, human reviews, Drupal writes, source mutations, snapshot operations, or new CrewAI
experiment runtimes. The permanent audit may repeat the already-authorized read-only predecessor
verification; it cannot invoke a model, write Drupal, restore/delete a snapshot, or stage Git.

## Permanent acceptance

`scripts/gate2b_step07_audit.py` provides `candidate`, `recovery`, `permanent`,
`historical-gate2a`, and `gate2a-preservation` modes and fails closed unless:

- the Step 2B.06 merge is an ancestor and retains the exact two parents;
- every frozen predecessor manifest/hash is exact;
- Step 2B.06 composite passes;
- the unchanged Gate 2A auditor passes at its certified historical merge;
- the same historical mutable-document predicate is observed to reject the current descendant;
- all 245 current Gate 2A frozen paths equal the certified merge while later mutable documents may evolve;
- the retained snapshot remains exact;
- all promoted claims map to exact proof;
- verified claims include official source pairings;
- all six CrewAI organ rows are complete;
- Gate 2C remains deferred and no recovery winner is claimed;
- production readiness and framework superiority remain unclaimed;
- Step 2B.08 has not started;
- synthesis activity counts and privacy pass.

Permanent mode uses ancestry, not `HEAD == predecessor`, so it supports an installed/uncommitted
transaction, feature commit descendants, normal merge descendants, and later descendants.

The recovery wrapper mode is `recover-acceptance`. It performs no synthesis and accepts only
`gate2b-step07-20260828T135201Z-1ed07bea`. It first runs `recovery` with the pointer absent, creates
the pointer atomically only after that pass, and then runs `permanent`. The old `run` synthesis mode
is permanently disabled.

## Stop boundary

After execution and audit, stop before Git staging. Do not certify/freeze Gate 2B, create the final
CrewAI freeze artifact, delete the retained Step 2B.06 snapshot, begin Step 2B.08, or execute Gate 2C.
