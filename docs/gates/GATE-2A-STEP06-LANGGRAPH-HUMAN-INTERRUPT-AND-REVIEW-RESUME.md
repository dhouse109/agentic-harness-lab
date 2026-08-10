# Gate 2A Step 2A.06 — LangGraph Human Interrupt and Drupal Review Resume

## Purpose

Prove LangGraph's persisted interrupt/resume mechanism around the existing authoritative Drupal human-review queue. This step does not introduce a second approval system and performs no model call.

## Frozen predecessor

- Main baseline: `2b61e5859a5474e8422b85e0108b89808c519208`
- Accepted Step 2A.05 evidence: `evidence/gates/gate-2a/canonical-slice/gate2a-step05-20260810T140133Z-0025b888`
- Gate 2A contract SHA-256: `1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b`

## Proof boundary

```text
accepted Step 2A.05 model output
→ fresh Step 2A.06 LangGraph run/thread
→ shared get_image_context freshness check
→ shared submit_recommendation
→ shared pending status confirmation
→ SQLite checkpoint
→ langgraph.types.interrupt("await Drupal review")
→ STOP for real editor_dana action in Drupal
→ edit proposed alt + approve + one reviewer revision
→ same SQLite run/thread + Command(resume=...)
→ shared get_recommendation_status observes approved/editor_dana
→ shared context freshness check
→ retain revision lineage and checkpoint evidence
→ restore exact pre-run Drupal snapshot
```

The reused model output is evidence provenance, not a second model invocation. The Step 2A.06 recommendation has its own LangGraph `run_id` so its Drupal record and checkpoint lineage are attributable to this proof.

## Human action

The reviewer must use Drupal as `editor_dana`:

1. open the exact recommendation edit URL printed by the runner;
2. change Proposed alt text to a meaningful, non-empty value different from the initial value and no longer than 250 characters;
3. set Review status to **Approved**;
4. save exactly once.

The package does not automate or impersonate the human decision.

## Evidence

`evidence/gates/gate-2a/human-interrupt/<run-id>/` retains:

- accepted Step 2A.05 provenance;
- before, pending, reviewed, and restored Drupal state projections;
- pending recommendation/submission/status;
- checkpoint-before-review and checkpoint-after-resume;
- observed interrupt metadata;
- reviewer revision lineage;
- resume event and post-review status;
- source before/after comparison and reset proof;
- call counters, checkpoint privacy scan, secret scan, summary, and manifest.

No API key, authorization header, Drupal password, raw image representation, full Article body, private DB export, or hidden reasoning may be retained.

## Pass criteria

- model/provider calls: exactly 0;
- one LangGraph-origin pending recommendation is created from accepted Step 2A.05 output;
- the graph is genuinely interrupted and the interrupted state is persisted in SQLite;
- the initial recommendation revision belongs to `agent_bot` and is pending;
- the latest review revision belongs to `editor_dana`, is approved, and has changed proposed alt text;
- immutable target, run, framework, and evidence fields do not change through review;
- the same `run_id == thread_id` resumes from the existing SQLite checkpoint;
- post-resume status read observes `approved`, `editor_dana`, and a review timestamp;
- source Article/image context remains unchanged;
- automatic publication remains absent;
- Drupal returns to seeded-clean after evidence capture;
- Gate 2C failure injection is not exercised.

Step 2A.07 remains locked until this step is committed, merged, local `main` is resynchronized, and the post-merge audit passes.

## v1.0.4 bookkeeping repair

The successful v1.0.3 installation was retained. Post-install inspection found only a contradictory stale fresh-session sentence in `docs/CURRENT-STATUS.md`: the top-level lifecycle correctly marked Step 2A.06 active while the later paragraph still described Step 2A.06 as next/locked. v1.0.4 repairs that lifecycle bookkeeping, records v1.0.4 as the active package, and strengthens the active/complete auditor so contradictory lifecycle text cannot pass. No Step 2A.06 live `start` or `resume` action, model/provider call, Drupal call, recommendation write, or human review is performed by this repair.

## v1.0.5 bookkeeping repair

v1.0.5 supersedes the v1.0.4 preview-only repair attempt. v1.0.4 stopped before changing the repository because its preflight looked for the prose substring `Step 2A.06 is active` instead of the exact installed Markdown lifecycle marker `- **Step 2A.06:** active — ...`. v1.0.5 preserves the successful v1.0.3 installation, applies the same lifecycle consistency repair intended by v1.0.4, records v1.0.5 as the active package, and directly self-tests the repair preflight against the observed v1.0.3 document shape. No Step 2A.06 live `start` or `resume`, model/provider call, Drupal call, recommendation write, or human review is performed by this repair.

## v1.0.6 bookkeeping repair

v1.0.6 supersedes the v1.0.5 preview-only repair attempt. v1.0.5 stopped before changing the repository because its preflight called `.strip()` on `git status --porcelain`, removing the semantic leading space from the first tracked-modification record (` M AGENTS.md`). The fixed-column parser then misread `AGENTS.md` as `GENTS.md`. v1.0.6 preserves porcelain leading status spaces, keeps the same narrow v1.0.3 in-place repair scope, and adds a regression test using the exact observed combination of tracked lifecycle modifications and untracked Step 2A.06 implementation files. No Step 2A.06 live `start` or `resume`, model/provider call, Drupal call, recommendation write, or human review is performed by this repair.

## v1.0.7 live-start repair

The first authorized Step 2A.06 `start` attempt was retained as a truthful failed run after Drupal rejected the generated `run_id` `langgraph-review-<timestamp>-<suffix>` with `INVALID_RUN_ID`. The frozen shared validator accepts `langgraph-<timestamp>-<suffix>` for `source_framework=langgraph`; the shared validator and frozen contract are unchanged. v1.0.7 repairs only the Step 2A.06 runner/core boundary: it generates and pre-validates the frozen `langgraph-...` form, preserves the failed run and FAILED-RUNS history, and creates a one-time retry authorization tied to that exact failed attempt. The authorization is consumed when the next `start` begins, so any subsequent failure again requires explicit human review/package repair before retry. No model/provider call, Drupal call/mutation, recommendation write, or human-review action is performed by the v1.0.7 repair itself.


## v1.0.8 post-resume schema recovery

The controlled v1.0.7 retry successfully created a pending LangGraph recommendation, persisted a genuine interrupt, received one real `editor_dana` edit-and-approve revision, resumed the same SQLite run/thread, observed the approved Drupal status, and restored the exact pre-run Drupal snapshot. Final acceptance then stopped because `checkpoint-before-review.json` retained the Step 2A.06-only status value `awaiting_human_review`, while the frozen `langgraph-run-state.schema.json` permits the canonical lifecycle value `interrupted`. The run is retained as a truthful failed attempt and is not normalized or promoted. v1.0.8 changes the persisted pre-review state to `interrupted`, validates the pre-review checkpoint before any human action is requested, validates the post-resume checkpoint before finalization, strengthens failed-finalization handling, and creates a one-time retry authorization tied to the retained post-resume schema failure. The frozen schema, shared Drupal validator, prior evidence, and model policy remain unchanged. The repair itself performs zero model/provider calls and zero Drupal calls/mutations.
