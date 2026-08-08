# Gate 1 Step 1.05 — Drupal AI 12-target batch runner

## Purpose

Step 1.05 scales the accepted Step 1.04 Drupal AI vertical slice to the frozen twelve-target Gate 1
batch contract. It proves framework-owned sequencing, persisted run state, a deterministic midpoint
interruption, same-run recovery, and duplicate-free recommendation submission. It stops before human
review; Step 1.06 owns reviewer decisions and completion of `human-review.json`.

The controlling batch contract remains unchanged:

```text
shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json
```

The frozen target count is 12 and the target-sequence SHA-256 is
`1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728`.

## Runtime path

Each target reuses the Step 1.04 runtime boundary:

```text
FunctionCall adapters for discovery/context/submission/status
→ ADR-0008 FileEntityResolver
→ repository-owned temporary ai_agent configuration
→ AiAgentEntityWrapper
→ Task with one verified FileInterface
→ determineSolvability()
→ solve()
→ structured model output
→ deterministic validator
→ pending recommendation
```

Provider `openai`, model `gpt-4.1-mini-2025-04-14`, temperature `0.0`, prompt version
`drupal-ai-alt-text-v1.0.0`, and validator `gate05-validator-1.0.0` remain frozen. The temporary agent
configuration exposes zero model-callable tools and permits one provider/agent request per target.
The harness implements no automatic model retry.

## State, interruption, and recovery

Framework-owned runtime state is persisted in Drupal key/value storage under the existing
`agentic_harness_drupal_ai.run_state` collection. Step 1.05 uses batch-specific keys and never moves
framework state into `shared/` runtime storage.

The execution seam is fixed by the Step 1.01 contract:

1. discover and persist the exact twelve-target sequence;
2. process sequences 1 through 6 in order;
3. persist target 6 completely, including its recommendation identity and validation result;
4. mark the run `interrupted` after sequence 6 and before sequence 7 begins;
5. resume the same run ID at sequence 7;
6. process sequences 7 through 12;
7. complete with exactly twelve unique pending recommendation UUIDs and duplicate count 0.

The intentional midpoint interruption is a successful Step 1.05 checkpoint, not a provider failure.
Unexpected failures do not trigger an automatic model retry; the pre-batch DDEV snapshot remains the
explicit abort/restore boundary.

## Evidence boundary

Batch result artifacts are written under the frozen result root:

```text
evidence/results/drupal_ai/<run-id>/
```

Step 1.05 writes the batch runner portions of the frozen evidence contract:

```text
run.json
targets.json
events.jsonl
tool-traces.json
model-outputs.json
recommendations.json
validation.json
submissions.json
statuses.json
recovery.json
summary.json
summary.md
```

`human-review.json` is deliberately absent in Step 1.05 because its frozen schema requires at least
one real `editor_dana` decision. Step 1.06 owns that lifecycle stage. Step 1.05 therefore does not
claim complete Gate 1 batch-evidence certification.

Operational gate evidence is retained separately under:

```text
evidence/gates/gate-1/drupal-ai-batch-runner/<gate-run-id>/
```

Retained evidence contains no API key, Authorization header, raw Base64 image, full data URL, local
file path, File entity, raw image bytes, or hidden model reasoning.

## Human-review handoff

A successful Step 1.05 batch leaves Drupal intentionally in a controlled intermediate state:

- 20 source Articles unchanged;
- 12 frozen targets unchanged;
- 12 `alt_text_suggestion` recommendations in `pending` status;
- batch run state marked `completed` with `next_target_index = 12`;
- temporary AI Agent configuration removed;
- `agentic_harness_drupal_ai` remains enabled for Step 1.06;
- the exact pre-batch DDEV snapshot remains available for final restoration after human review.

No recommendation is approved, rejected, or published automatically in Step 1.05.

## Runner lifecycle

The installed runner exposes:

```text
preflight  model-free, reset-bounded verification of all 12 target/File identities
start      process 1–6 and stop at the deterministic interruption seam
status     inspect persisted batch state without a provider call
resume     continue the same run at 7 and finish through 12
promote    validate/retain evidence and advance repository status without a model call
restore    abort an active/unpromoted run and restore the exact pre-batch snapshot
audit      verify the accepted post-batch handoff for Step 1.06
```

`promote` is intentionally separate from `resume`. Evidence/status publication can therefore be
repaired without repeating model calls if a repository-only promotion check fails.

## Progression compatibility

The accepted Step 1.04 permanent audits originally asserted that Step 1.05 source was absent. This
package updates only those progression assertions so the exact five-file Step 1.05 implementation is
authorized while all Step 1.04 ADR, File-transport, historical evidence, and serialization controls
remain enforceable. Partial Step 1.05 installation fails. Step 1.06 source remains prohibited.

The existing ADR-0007 boundary audit also rejects the standard external Step 1.05 package path.
Therefore this package must be previewed and installed from the separate staging root documented in
its README; that restriction is preserved rather than bypassed.

## Scope exclusions

Step 1.05 does not:

- perform human review;
- create `human-review.json`;
- mutate source Article image fields;
- automatically publish recommendations;
- alter frozen schemas, prompts, contracts, ADRs, contributed modules, or dependencies;
- start Step 1.06;
- claim final Drupal AI certification or freeze.
