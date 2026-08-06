# ADR-0007: Canonical-slice evidence, image, and state boundary

- **Status:** Accepted for package execution only; effective only with passing reconciliation evidence
- **Decision date:** 2026-08-06
- **Qualifies:** ADR-0006; it does not replace its selected AI Agents runtime path
- **Predecessors:** Gate 0.5 certification, Step 1.01 contract, Step 1.02 runtime probe, and Step 1.03 adapters

## Context

The frozen Gate 1 contract is a 12-target batch contract. Its target, model-output,
recommendation, validation, and submission collections require exactly 12 entries; its completed
Drupal AI run state requires `next_target_index: 12`. Step 1.04 is deliberately one target and
therefore cannot truthfully validate as, or be retained as, a completed batch run.

Pinned AI Agents source also establishes that `Task::setFiles()` receives Drupal `File` entities.
`AiAgentEntityWrapper::setChatMessages()` converts each one to Drupal AI `ImageFile`, and the
OpenAI provider serializes that image as the frozen inline PNG representation. `ChatMessage::toArray()`
serializes attached image files to Base64, so a post-image wrapper dump is prohibited evidence.

## Decision

### Additive canonical-slice profile

Keep every existing shared contract and schema byte-for-byte unchanged. Add only
`shared/profiles/gate1-drupal-ai-canonical-slice-v1.0.0/` with:

- `canonical-slice-profile.json`
- `canonical-slice-evidence.schema.json`
- `canonical-slice-run-state.schema.json`

Step 1.04 is a one-target implementation proof, not a 12-target batch result. It validates each
individual target, raw model-output, assembled recommendation, validator result, submission,
status observation, and human-review decision against the existing frozen item schemas or their
existing `$defs`; it does not copy or weaken those semantics. It requires exactly canonical sequence
1, retains the frozen 12-target hash, requires one raw output/recommendation/validation/submission,
and records separate pending and approved observations. Failure injection and batch recovery are
explicitly not exercised.

`evidence/results/drupal_ai/<run-id>/` remains reserved for a complete, contract-conforming
12-target batch run beginning in Step 1.05. Step 1.04 retains only profile-identified evidence under
`evidence/gates/gate-1/drupal-ai-canonical-vertical-slice/<gate-run-id>/`; it cannot claim batch
contract conformance.

The profile run state permits `initialized`, `running`, `awaiting_human_review`, `resuming`,
`completed`, `failed`, and `aborted`. It retains the frozen provenance constants, canonical target,
one-call counter, recommendation identity, human pause/resume, and terminal timestamps. The frozen
`drupal-ai-run-state.schema.json` remains authoritative for Step 1.05 and later batch runs.

### File-entity transport bridge

The supported transport is:

```text
authorized get_image_context adapter result
-> exact read-only File-entity resolution
-> Task::setFiles(array<FileInterface>)
-> AiAgentEntityWrapper creates ImageFile
-> OpenAI provider receives frozen inline PNG representation
```

Step 1.04 may add one framework-owned resolver after the permission-checked context adapter succeeds
as `agent_bot`. It must resolve only `file` storage by the authorized `file_uuid` through
`entity_type.manager->getStorage('file')->loadByProperties(['uuid' => ...])`; select exactly one
result; and reverify the UUID, URI identity, MIME type, byte length, and SHA-256 against the
authorized context before returning the read-only `FileInterface`. It may not query an Article or
recommendation, write any entity, accept model-supplied file identity, expose the entity in
evidence, or replace the shared context authorization operation.

### Wrapper serialization

`AiAgentEntityWrapper::toArray()` must not be retained after `Task::setFiles()`, image attachment,
provider invocation, or image-bearing chat history. No redacted post-image transformation may be
claimed as a restorable checkpoint.

This package's model-free runtime probe evaluates only a pre-task, pre-image, pre-provider wrapper
checkpoint. It records keys, safe provider/model/config metadata, chat-history absence, absence of
files/image data/Base64/data URLs/authorization/secrets, and `fromArray()` restoration. If that probe
passes, Step 1.04 may retain only that pre-invocation configuration checkpoint and use `fromArray()`
during human-review resume; resume performs no model invocation. Post-model checkpointing and
agent-memory recovery are not claimed.

### One-call agent boundary

For the Step 1.04 agent configuration, expose no model-callable tools and no `require_usage`
settings. Installed `getFunctions()` then returns no normalized tools, so no tool schema is supplied;
`allRequiredToolsRan()` is empty; `determineSolvability()` dispatches one `ai_agents.request` and
calls provider `chat()` once; a no-tool response reaches finished execution. `solve()` only returns
the stored question and makes no provider request. Thus the supported expected maximum is exactly
one provider request. The later runner must install a run-scoped request listener that fails closed
before a second provider call if any unexpected recursive request is attempted. Automatic retries
remain zero.

## Consequences

This decision authorizes only additive profile, probe, and audit work. It does not authorize the
Step 1.04 vertical slice, a model call, an AI Agent config entity, a File resolver implementation,
runtime state persistence, a batch runner, Step 1.05, dependency changes, contrib patches, or shared
contract changes.
