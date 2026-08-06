# Gate 1 Step 1.04 Boundary Reconciliation

## Purpose

This package resolves the compatibility boundary before the canonical vertical slice is implemented.
It adds ADR-0007, a profile-only one-target evidence/state contract, a model-free wrapper checkpoint
probe, and a permanent regression audit. It does not install or execute the vertical slice.

## Reproduced conflicts

The frozen `batch-target-sequence`, `batch-model-outputs`, `batch-recommendations`,
`batch-validation`, and `batch-submissions` collections each require exactly 12 entries. The frozen
`drupal-ai-run-state` completed state requires `next_target_index: 12`, and the frozen batch contract
maps `evidence/results/drupal_ai/<run-id>` to those batch schemas. A one-target slice cannot claim
batch conformance.

Pinned AI Agents source accepts Drupal File entities in `Task::setFiles()`. The entity wrapper then
creates `ImageFile`; the OpenAI provider serializes its inline PNG transport. `ChatMessage::toArray()`
uses each file `toArray()`, which includes Base64. Therefore post-image wrapper serialization cannot
be evidence or persisted state.

## Profile and transport decision

ADR-0007 creates an additive canonical-slice profile. Gate evidence is retained only under
`evidence/gates/gate-1/drupal-ai-canonical-vertical-slice/<gate-run-id>/`; the batch evidence root
is excluded until Step 1.05. Existing item schemas/$defs are reused per item, and the local state
profile represents exactly sequence 1 with one model call and mandatory human review.

The only supported image bridge is authorized adapter context followed by read-only `file` storage
resolution through `loadByProperties(['uuid' => $uuid])`, exact metadata/hash revalidation, and
`Task::setFiles(array<FileInterface>)`. It is framework-owned transport only, not a substitute for
the certified authorization or persistence operations.

## One-call conclusion

With no model-callable functions and no required-tool settings, the installed wrapper supplies no
tools, `determineSolvability()` issues one provider `chat()` request for the no-tool response, and
`solve()` returns stored text only. Step 1.04 may fix the expected maximum at one provider request,
with zero retries and a listener that fails closed before a second request.

## Wrapper checkpoint probe

The later runner probes an existing configuration wrapper before task, image, or provider use. It
sets only explicit non-secret `openai`/model/temperature metadata, calls `toArray()`, checks for no
chat history/image/Base64/data URL/authorization/credential value, restores a fresh wrapper with
`fromArray()`, and verifies provider/model/configuration metadata. The probe neither calls a provider
nor creates/saves configuration. Passing this probe authorizes only a pre-invocation checkpoint;
post-image checkpointing remains prohibited.

## Exit

After a later approved execution produces passing reconciliation evidence, status documents may name
`gate-1-step04-drupal-ai-canonical-vertical-slice-v1.0.0` as the next implementation package.
