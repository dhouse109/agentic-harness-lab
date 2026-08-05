# Claims Register

## Status rules

- `hypothesis`: prediction from the proposal or experiment design; do not present as a result.
- `observed`: reproduced locally with retained evidence, but not yet paired with an official source.
- `verified`: paired with current official documentation, pinned version, repeatable local test,
  and retained evidence.
- `unsupported`: evidence did not support the claim; do not use.

All rows below begin as hypotheses.

| ID | Claim | Framework | Official source | Local evidence | Status | Safe wording now |
|---|---|---|---|---|---|---|
| CLM-DR-001 | Drupal permissions can constrain the service account to read source content and create recommendations without editing source alt text or approving its own work. | Drupal AI / Drupal substrate | TODO | Step 11 candidate evidence | hypothesis | Do not present as a comparative result until evidence is reviewed and sourced. |
| CLM-DR-002 | Drupal recommendation revisions can retain reviewer identity, timestamps, text edits, and status transitions as an editor-facing audit trail. | Drupal AI / Drupal substrate | TODO | Step 12 candidate evidence | hypothesis | Do not use yet. |
| CLM-DR-003 | A Drupal implementation may resume batch work from persisted entity state rather than recomputing completed items. | Drupal AI | TODO | Not run | hypothesis | Do not use yet. |
| CLM-DR-004 | Drupal’s native content, permissions, and review UI reduce the amount of custom governance plumbing needed for this content-centric task. | Drupal AI | TODO | Not run | hypothesis | Do not use yet. |
| CLM-LG-001 | LangChain / LangGraph provides the broadest code-first tool and integration surface of the three specimens. | LangChain / LangGraph | TODO | Not run | hypothesis | Do not use yet. |
| CLM-LG-002 | A LangGraph implementation with the pinned SQLite checkpointer can reload persisted state after a process restart. | LangGraph | TODO | Step 15 planned test | hypothesis | Do not use yet. |
| CLM-LG-003 | Without a configured persistence path, a code-first LangGraph specimen may repeat completed work after termination. | LangGraph | TODO | Failure test not run | hypothesis | Do not use yet. |
| CLM-CR-001 | CrewAI makes role-oriented multi-agent decomposition more explicit than the other two specimens. | CrewAI | TODO | Not run | hypothesis | Do not use yet. |
| CLM-CR-002 | A CrewAI Flow using the pinned persistence mechanism can retain workflow state across a process restart. | CrewAI | TODO | Step 15/implementation test planned | hypothesis | Do not use yet. |
| CLM-CR-003 | A CrewAI human-feedback pathway can continue after a persisted reviewer response. | CrewAI | TODO | Human-feedback test not run | hypothesis | Do not use yet. |
| CLM-CMP-001 | All three implementations can produce a schema-valid recommendation for the same target and write it to the same Drupal review queue. | Cross-framework | TODO | Gate 0.5 shared substrate certified; framework implementations not run | hypothesis | Do not present as a cross-framework result; Gate 0.5 did not certify framework behavior. |
| CLM-CMP-002 | The three implementations expose meaningfully different state, review, and recovery mechanisms under the same failure trigger. | Cross-framework | TODO | Recovery tests not run | hypothesis | Do not use yet. |
| CLM-CMP-003 | The best fit depends on the task: governed content operations may favor Drupal, broad code-first prototyping may favor LangChain / LangGraph, and explicit role decomposition may favor CrewAI. | Cross-framework | TODO | Comparison incomplete | hypothesis | Present only as the question the experiment tests. |
| CLM-SHARED-001 | The permission-scoped Drupal discovery route returns the frozen 12 exact image-field usages after reset without a model call or source mutation. | Shared Drupal substrate | SRC-S17-001, SRC-S17-002, SRC-S17-003 | `evidence/logs/tools/find-images/step17-20260804T173030Z-851608` | observed | In the pinned Phase 0 lab, the model-free Drupal route returned the same 12 deterministic field usages as the Step 9 manifest; this does not yet prove any framework-owned agent behavior. |
