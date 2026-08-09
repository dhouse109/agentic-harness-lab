# Gate 2A Step 2A.01 — LangGraph Contract and Evidence Plan

**Package:** `gate-2a-step01-langgraph-contract-and-evidence-plan-v1.0.3`
**Expected predecessor:** `d87c66a8a342109253e906e7e29ce2c15f7ddbef`
**Gate 1 freeze:** `2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd`
**Contract SHA-256:** `1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b`

## Purpose

This step formalizes Gate 2 / Gate 2A naming, freezes LangGraph-specific pass/fail criteria, defines LangGraph state and raw model-output schemas, defines the evidence boundary, and generalizes the package/Codex operating instructions from completed Gate 1 to the current gate.

This is a **model-free, Drupal-mutation-free contract package**. It does not implement LangGraph runtime behavior and does not make a LangGraph claim observed.

## Frozen constants

| Constant | Value |
|---|---|
| Dataset | 20 Articles / 12 targets |
| Target sequence SHA-256 | `1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728` |
| Framework origin | `langgraph` |
| Provider / model | OpenAI `gpt-4.1-mini-2025-04-14` |
| Temperature | `0.0` |
| Validator | `gate05-validator-1.0.0` |
| Review destination | `alt_text_suggestion` |
| Reviewer | `editor_dana` |
| Source mutation / automatic publication | prohibited / prohibited |
| Shared comparison seam | after target 6 persisted, before target 7 begins |
| Python | 3.12.13 |
| LangChain | 1.3.14 |
| LangGraph | 1.2.10 |
| SQLite checkpointer | 3.1.1 |

The four shared semantic operations remain `find_images_needing_review()`, `get_image_context(target)`, `submit_recommendation(target, proposed_alt_text, run_id)`, and `get_recommendation_status(recommendation_id)`.

## State ownership

LangGraph owns orchestration, workflow state, thread/run identity, checkpointing, interruption, continuation, and recovery behavior. The comparison schema is shared only as an audit contract; runtime state must not be centralized in `shared/`.

Gate 2A uses a framework-owned SQLite checkpoint backend. The exact pinned API, checkpoint namespace behavior, thread identity wiring, and runtime path are deliberately deferred to Step 2A.02, where the installed versions are probed without upgrading them.

Raw image bytes/data URLs, credentials, private database exports, and hidden reasoning must never be written into checkpoint state or retained evidence.

## Human review boundary

Do not invent a second approval system in LangGraph. The authoritative human decision remains the revision-enabled Drupal `alt_text_suggestion` queue and `editor_dana`.

Preferred proof:

```text
LangGraph creates pending recommendation
→ pending state confirmed
→ LangGraph checkpoint / interrupt at "await Drupal review"
→ editor_dana reviews in Drupal
→ resume same LangGraph run/thread
→ get_recommendation_status() observes the real Drupal revision/status
```

Use edit-and-approve for the representative lineage when practical. Approval does not apply alt text to source content.

## Continuation versus Gate 2C

Gate 2A must prove a controlled same-run continuation at the target-6/7 seam: target 6 is fully persisted, execution stops, and the same run/thread resumes at target 7 without reprocessing 1–6 or creating duplicates.

That is **not** the shared Gate 2C comparison. Gate 2C later applies the same defined process failure comparably to all three frozen specimens.

## Model-call and certification policy

- Steps 2A.01–2A.04: zero model calls.
- Step 2A.05: one successful canonical target call.
- Step 2A.06: zero preferred; reuse the canonical evidence where valid.
- Step 2A.08: 12 successful calls total across the stop/resume boundary.
- Step 2A.10: zero by default; promote the accepted 2A.08 batch through a model-free certification audit.
- Expected successful Gate 2A calls: **13**.
- No semantic retry loop. A provider/transport failure is retained and requires a human-reviewed retry decision.
- Do not silently create a second 12-call certification batch merely to make evidence cleaner.

## Evidence boundary

Contract evidence is retained under `evidence/gates/gate-2a/contract/<run-id>/`. Later LangGraph run evidence belongs under `evidence/results/langgraph/<run-id>/` and remains lifecycle-separated.

Evidence may retain exact versions/hashes, sanitized fixture/context facts, raw structured model output, sanitized shared-operation traces, validator outcomes, recommendation/revision IDs, checkpoint/state transitions, human review lineage, and sanitized errors.

Evidence must not retain secrets, authorization headers, raw Base64/data URLs, private database exports, hidden reasoning, or unrelated private configuration.

## Package sequence

1. 2A.01 — LangGraph contract and evidence plan
2. 2A.02 — runtime and checkpoint probe
3. 2A.03 — tool adapters
4. 2A.04 — state and SQLite checkpoint proof
5. 2A.05 — canonical vertical slice
6. 2A.06 — human interrupt and review resume
7. 2A.07 — batch runner
8. 2A.08 — fresh batch and continuation
9. 2A.09 — evidence, claims, and matrix
10. 2A.10 — certification, freeze, and CrewAI handoff

## Exit criteria

Step 2A.01 passes only when:

- the Gate 1 permanent audit passes and the Gate 1 freeze digest matches;
- the Gate 2A contract digest is reproducible;
- frozen constants reconcile with repository evidence;
- LangGraph state ownership, SQLite checkpointing, and evidence stages are explicit;
- the 2A.08-as-certification-candidate policy is frozen;
- no second approval system is introduced;
- no Gate 1 artifact or dependency changes;
- no model call or Drupal mutation occurs;
- the next package is declared as `gate-2a-step02-langgraph-runtime-and-checkpoint-probe-v1.0.0`.
