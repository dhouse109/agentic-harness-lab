# Gate 2B Step 2B.04 — CrewAI canonical vertical slice

**Package:** `gate-2b-step04-crewai-canonical-vertical-slice-v1.0.0`

**Same-step closure repair:** `gate-2b-step04-crewai-canonical-vertical-slice-v1.0.1`

## Purpose

Prove frozen canonical target 1 through accepted CrewAI adapters, one real pinned-model generation,
the authoritative shared validation/submission boundary, pending Drupal review, and CrewAI-owned
`SQLiteFlowPersistence` state. This step does not perform human review or prove pending/resume
continuation.

## Canonical boundary

The canonical identity is sequence 1, node UUID `344eb273-ac74-5be8-85fb-6c2efd1f93a6`, Article
revision `1`, `field_image` delta `0`, and file UUID
`07af2dce-7bfd-5de6-b291-e090669eda25`. The full frozen target sequence SHA-256 remains
`1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728`.

The frozen model is OpenAI `gpt-4.1-mini-2025-04-14` at temperature `0.0`. Prompt semantics are
byte-equivalent to `shared/prompts/PROMPTS.md`; CrewAI wrapper syntax is the only difference. Raw
model output contains exactly `proposed_alt_text`. Target/run/provenance fields are assembled
deterministically afterward.

## One physical request

Pinned CrewAI 1.15.10 routes `LLM(model="openai/gpt-4.1-mini-2025-04-14", ...)` to its native
`OpenAICompletion`. The selected public path explicitly sets `api="responses"`, so the native
chat-completions-to-Responses fallback cannot execute. `response_format=ModelOutput` becomes the
single Responses request's strict `text.format` JSON Schema. The call does not pass CrewAI's
`response_model`, and Pydantic parses the returned string locally; invalid JSON fails closed with no
repair request.

The OpenAI SDK is constructed with `max_retries=0`. CrewAI's public `BaseInterceptor` transport
hook counts every outbound SDK HTTP attempt and raises before a second request. A separate logical
permit blocks a second `LLM.call`. The Flow uses no `Task`, `Crew`, guardrail, tool-calling model
loop, application callback capable of inference, learning, distillation, feedback collapse,
auto-chain, or replay path. Streaming is off. `CREWAI_DISABLE_VERSION_CHECK=true` is required.
Telemetry/tracing are disabled. Pinned-source inspection found that first-execution trace collection
does not honor the general telemetry switch before listener registration, so this process also sets
the pinned `CREWAI_TESTING=true` trace-suppression environment control. In 1.15.10 that variable is
read only by the tracing first-execution check (and surfaced by the installed CrewAI CLI); it does
not replace or alter Flow, LLM, adapter, or persistence behavior.

This remains a genuine CrewAI specimen: supported CrewAI Flow owns the lifecycle and sequencing,
the public CrewAI `LLM` owns native provider construction/invocation, the public interceptor owns
transport accounting, and CrewAI `SQLiteFlowPersistence` saves state after each Flow method.

## Shared-operation and Drupal boundary

The accepted Step 2B.03 tools perform discovery, context retrieval, submission, and status
observation. The Flow neither duplicates validation nor introduces a Drupal client/write path.
`submit_recommendation` atomically reruns the authoritative deterministic validator and, on pass,
creates one unpublished, revision-enabled `alt_text_suggestion` node with one initial revision in
`pending` state. It does not mutate the source Article or image alt value. A status read confirms
pending state; no `editor_dana` action occurs.

The semantic mutation budget is one successful shared submission, producing one recommendation
entity/initial revision. Drupal may write multiple internal database rows to realize that entity;
those are one governed recommendation mutation, not source-content mutations.

## Persistence and continuation nonclaim

Flow state retains the logical run and Flow IDs, canonical target, sanitized context provenance,
prompt identity, raw structured output, assembled recommendation, shared-validation disposition,
recommendation/revision IDs, pending lifecycle state, persistence provenance, and physical request
accounting. Raw Article body, image data URL, credentials, headers, hidden reasoning, and unrelated
configuration are excluded.

Runtime SQLite lives at `crewai/.runtime/gate2b-step04/<logical-run-id>/flow-state.sqlite`, never
under `shared/`. Automatic Flow memory construction is routed through the public
`set_memory_storage_factory(...)` extension to a deterministic run-scoped backend; private
`_skip_auto_memory` is not used. Runtime `CheckpointConfig` is not selected.

The precise retained claim is: **terminal-output reconstruction observed; live Flow state
restoration/continuation not demonstrated**. `HumanFeedbackPending`, `from_pending()`, and
`resume()` remain for a later approved boundary.

## Rerun and failure policy

The evidence directory is allocated before the real call. A failed model-backed attempt remains
unique and is never overwritten. Any existing Step 2B.04 attempt blocks an automatic second live
run. A second logical provider call is blocked before invocation; a second physical HTTP attempt is
blocked before transport. Once submission occurs, the same logical run/target replay remains
idempotent in the shared substrate, but tooling must preserve the retained run instead of replaying
it automatically.

Failures are labeled separately for predecessor, discovery, context retrieval, Flow construction,
provider request, structured parsing, recommendation assembly, shared deterministic validation,
submission, persistence, source-nonmutation, privacy, and evidence serialization. No generic
failure is promoted to a different stage.

## Evidence

Each passing run contains exactly 20 files. `evidence-manifest.json` hashes the other 19:

- `authorization.json`
- `canonical-target.json`
- `context-provenance.json`
- `events.jsonl`
- `flow-state.json`
- `persistence-provenance.json`
- `pinned-source-provenance.json`
- `predecessor.json`
- `privacy-scan.json`
- `prompt-provenance.json`
- `provider-accounting.json`
- `provider-metadata.json`
- `raw-model-output.json`
- `recommendation.json`
- `source-nonmutation.json`
- `stage-results.json`
- `submission.json`
- `summary.json`
- `summary.md`
- `evidence-manifest.json`

Only a passing independently audited run may update `LATEST`.

## Post-process-close provenance repair

The successful live run remains immutable and primary. Its `persistence-provenance.json` records
the main SQLite file while persistence was open and WAL-backed. Process closure/checkpoint later
changed the main-file bytes legitimately; that lifecycle transition is not an integrity failure and
does not require the open-state and post-close main-file hashes to match.

The v1.0.1 same-step repair adds a separate, model-free evidence family under
`evidence/gates/gate-2b/canonical-slice-closure/`. Each passing closure contains exactly eight files:

- `authorization.json`
- `closure-provenance.json`
- `drupal-observation.json`
- `sqlite-semantic-inspection.json`
- `privacy-scan.json`
- `summary.json`
- `summary.md`
- `evidence-manifest.json`

The closure binds the original 20-file evidence tree, original manifest and summary, original
open/WAL-state main-file hash, and the distinct post-process-close SQLite/WAL/SHM hashes and sizes.
Semantic SQLite inspection operates only on an exact disposable copy of the complete file-set.
The authoritative files are hashed as ordinary files and are never opened as a database by the
capture utility.

The permanent auditor fails closed if closure provenance is absent or incorrectly bound, if any
original evidence byte changes, if any current runtime component is missing, extra, or mismatched,
if the closure schema or privacy scan fails, or if historical live-run counts are confused with the
zero-action repair boundary. It accepts installed/uncommitted state and legitimate commit or normal-
merge descendants by requiring predecessor ancestry instead of exact `HEAD` equality.

## Eventual execution budget

- logical model generations: exactly 1
- actual SDK/provider requests: exactly 1
- successful provider responses: exactly 1
- provider, transport, guardrail, repair, fallback, learning, and feedback-collapse retries/calls: 0
- live shared-operation recommendation submissions: exactly 1 after all preconditions pass
- recommendation mutations: exactly 1 pending recommendation entity/initial revision
- source-content mutations, human-review actions, dependency changes, and Gate 2C executions: 0

## Nonclaims

This step does not prove recommendation quality, human-review continuation, 12-target completion,
the target-6/7 seam, Gate 2C recovery, production readiness, framework superiority, cost, or speed.
