# Gate 2A Step 2A.07 — LangGraph 12-target batch runner

**Package:** `gate-2a-step07-langgraph-batch-runner-v1.0.4`

## Purpose

Install and prove, model-free, the LangGraph-owned 12-target batch runner that Step 2A.08 will execute
with the frozen 12-call model budget. Step 2A.07 must not make a model/provider call, Drupal semantic
call, recommendation write, or human-review mutation.

The runner is constructed around the already accepted LangGraph seams:

```text
frozen target discovery/order
→ per-target fresh context
→ one frozen structured model call
→ fresh pre-submit context
→ deterministic validator
→ one pending recommendation submission
→ pending status observation
→ post-submit source-context check
→ LangGraph SQLite checkpoint
```

## Frozen continuation seam

The batch graph is deterministic:

1. process sequences 1–6 exactly once and in order;
2. fully persist sequence 6;
3. mark the framework state `interrupted` with the continuation boundary reached;
4. enter a genuine LangGraph `interrupt()` after sequence 6 and before sequence 7;
5. resume the same `run_id == thread_id` with `Command(resume=...)`;
6. continue at sequence 7 without reprocessing sequences 1–6;
7. finish sequences 7–12 with duplicate count 0;
8. never arm or fire the separate Gate 2C failure-injection flag.

Step 2A.07 proves this wiring only with a local construction test over the frozen target identities.
The live observation is reserved for Step 2A.08.

## Model-call boundary

Step 2A.07 successful model calls: **0**.

The installed live runner contains the Step 2A.08 execution path with:

- provider OpenAI;
- model `gpt-4.1-mini-2025-04-14`;
- temperature `0.0`;
- `ChatOpenAI(max_retries=0)`;
- strict JSON-schema structured output;
- no semantic retry loop;
- one model invocation per target.

The Step 2A.07 shell entrypoint exposes only model-free `verify`, `certify`, and `audit`; it cannot
start the live batch. Step 2A.08 owns the live start/resume wrapper and the 12-call authorization.

## Evidence-schema compatibility

The frozen Gate 1 `batch-*.schema.json` files cannot truthfully validate LangGraph provenance because
they hard-code Drupal-AI run IDs/framework constants. Their event/recovery shapes also contain Gate 1
failure-only vocabulary that conflicts with Gate 2A's frozen controlled-continuation policy. ADR-0011
preserves those frozen files and the Gate 2A contract digest while reproducibly deriving
`langgraph-batch-*.schema.json` validation instantiations. The schema map distinguishes provenance-only
transformations from the narrow event/recovery controlled-continuation adaptations.

## Step 2A.07 construction evidence

Model-free construction evidence is retained under:

`evidence/gates/gate-2a/batch-runner/<gate-run-id>/`

It records:

- frozen target hash and all 12 target identities;
- a real local `StateGraph` + `SqliteSaver` construction test;
- checkpoint projection after sequences 1–6;
- genuine LangGraph interrupt metadata;
- same-thread `Command(resume=...)` continuation to sequences 7–12;
- checkpoint projection after completion;
- derived-schema reproducibility checks;
- zero model and zero Drupal call counters;
- summary and SHA-256 manifest.

The construction test uses no OpenAI client, Drupal client, credentials, image bytes, Article body, or
recommendation mutation.

## Step 2A.08 result boundary

The installed live runner writes the batch-runner portion of the frozen result contract under:

`evidence/results/langgraph/<langgraph-run-id>/`

including `run.json`, `targets.json`, `events.jsonl`, `tool-traces.json`, `model-outputs.json`,
`recommendations.json`, `validation.json`, `submissions.json`, `statuses.json`, `recovery.json`,
`summary.json`, and `summary.md`.

`human-review.json` is not fabricated by the Step 2A.07 construction test or by the batch runner.
The authoritative review system remains Drupal and `editor_dana`, already proven in Step 2A.06.

## Pass criteria

Step 2A.07 passes only when:

- Step 2A.06 accepted evidence remains present and unchanged;
- Gate 0.5, Gate 1, and Gate 2A frozen digests remain exact;
- the Gate 1 permanent regression audit passes;
- derived LangGraph batch schemas are reproducible mapped instantiations of the frozen Gate 1
  collection schemas, with only the ADR-0011 controlled-continuation adaptations;
- the construction test uses the exact 12-target hash and target identities;
- sequences 1–6 are persisted before the continuation interrupt;
- the same synthetic run/thread resumes at 7 and completes through 12 without duplicates;
- both checkpoint projections validate against `langgraph-run-state.schema.json`;
- model/provider calls are 0;
- Drupal semantic calls/mutations are 0;
- Gate 2C failure injection remains false;
- no Step 2A.08 live batch is executed.

Step 2A.08 remains locked until Step 2A.07 is verified, certified model-free, committed, merged, local
`main` is resynchronized, and the post-merge audit passes.

## v1.0.1 preventive review hardening

v1.0.1 supersedes v1.0.0 before preview/install after a static review against prior package failures
and the frozen Step 2A.08 evidence contract. The repair:

- preserves the repository's historical pre-install `Next package` anchor at v1.0.0 while recording
  v1.0.1 as the installed package, avoiding the Step 2A.06 repair-version anchor failure;
- makes `events.jsonl` conform to the instantiated batch-event schema and validates it at the midpoint
  and final boundary;
- makes `run.json` the schema-valid LangGraph run-state projection, rather than leaving a stale
  start-only metadata object;
- validates the live midpoint checkpoint immediately after six calls, before any Step 2A.08 resume;
- scans the SQLite checkpoint and retained evidence for exact ephemeral bodies/images/credentials and
  generic prohibited patterns at midpoint and completion;
- flushes model output, validation, recommendation, submission, and status evidence stage-by-stage so
  a later failure does not erase already-observed truth;
- records controlled target-6/7 continuation without Gate 2C failure-only vocabulary;
- retains failed model-free construction attempts and blocks an unreviewed rerun;
- reruns the permanent Gate 1 regression audit after installation.

The v1.0.1 repair itself performs zero model/provider calls and no live Step 2A.08 execution.


## v1.0.2 preview-anchor and resume-boundary hardening

v1.0.2 supersedes v1.0.1 before installation. The v1.0.1 preview stopped without repository mutation because three Bash preflight expressions placed Markdown backticks inside double-quoted strings; Bash attempted to execute the literal historical package name as command substitution and then reported a misleading lifecycle-anchor mismatch.

v1.0.2:

- constructs the historical next-package marker with `printf -v` so Markdown backticks are inert data;
- exercises the exact pre-install lifecycle assertion in the package self-check fixture;
- adds package-shell syntax checking and exact pinned-runtime version verification;
- rejects an already-existing local Step 2A.07 feature branch before installation;
- rolls back installation on ordinary errors, `INT`, or `TERM`;
- requires the frozen batch-schema source set to be exactly the expected 11 files;
- revalidates the persisted six-target checkpoint, `run.json`, target evidence, first-half collections, recommendation/status identities, event stream, midpoint privacy proof, and exact call counters before Step 2A.08 may spend calls 7–12;
- verifies exact Drupal semantic call counts at both the six-target and twelve-target boundaries.

The v1.0.1 preview failure produced no repository changes, no evidence run, no model/provider call, and no Drupal call/mutation.


## v1.0.3 interpreter-boundary and rollback recovery

v1.0.2 preview passed, but installation stopped immediately after creating the feature branch because `gate2a_step07_schema_instantiations.py` imported `jsonschema` while the frozen LangGraph runtime venv intentionally did not contain that package. The install made zero model/provider calls and zero Drupal calls/mutations. Its intended `ERR` rollback did not propagate through the `install_files()` function because the package used `set -euo pipefail` without Bash errtrace (`-E`), leaving the new branch and copied untracked files for explicit cleanup.

v1.0.3 makes the interpreter boundary explicit without changing dependencies: `langchain/.venv/bin/python` owns LangGraph runtime execution, while the already-existing `crewai/.venv/bin/python` owns Draft 2020-12 schema derivation/validation. The LangGraph batch core delegates schema validation to a model-free repository helper executed by that audit/schema interpreter. v1.0.3 also enables `set -Eeuo pipefail` and self-tests an `ERR` trap raised inside a function so installation rollback cannot silently miss the same failure class.

## v1.0.4 audit-probe repair

v1.0.3 installed far enough to derive schemas and activate lifecycle state, then its permanent audit falsely reported `Repository schema-validation Python version differs`. The schema interpreter was actually Python 3.12.13; the audit merged stderr into stdout, and importing deprecated `jsonschema.RefResolver` emitted a warning before the version line. v1.0.4 keeps schema-probe stdout/stderr separate, avoids importing `RefResolver` for capability-only probes, suppresses the known deprecation warning inside the actual compatibility helper, and adds a regression fixture for warning-isolated version parsing. No model/provider or Drupal call is performed by this repair.

## Repair lineage

The first model-free construction verification attempt after the v1.0.4 install is retained at `evidence/gates/gate-2a/batch-runner/gate2a-step07-20260810T184229Z-00271f73`. It failed before LangGraph graph execution because the wrapper invoked `batch_runner.py` without the repository-local `langchain/` package root on `PYTHONPATH`, so `agentic_harness_langgraph.state` could not resolve. No model/provider call, Drupal semantic call, recommendation write, or Step 2A.08 live execution occurred.

v1.0.5 aligns the Step 2A.07 invocation boundary with the accepted Step 2A.05 repository-local import pattern, adds an import smoke test to static preflight, and authorizes exactly one reviewed retry tied to that retained failed attempt.
