# Gate 1 Step 1.04 — Drupal AI canonical vertical slice

## Purpose

This package implements one canonical target through the pinned Drupal AI / AI Agents runtime. It
is an implementation proof under the ADR-0007 one-target profile, not a conforming 12-target batch
run. `evidence/results/drupal_ai/` remains reserved for Step 1.05.

## Progression compatibility

The PR #9 clarification audit originally required the Step 1.04 implementation package and source to
be absent. That assertion was correct for the decision-only clarification boundary but cannot remain
a permanent predecessor condition once the authorized next step begins. This package updates only
that audit's progression logic: all ADR-0008 identity and URI controls remain mandatory, partial or
unknown Step 1.04 installations fail, and Step 1.05 remains prohibited.

Preview must run from a staging path until that update is installed. This avoids weakening or
silently bypassing the accepted clarification audit.

## Runtime

The model call uses:

```text
plugin.manager.ai_agents
→ repository-owned temporary ai_agent configuration
→ AiAgentEntityWrapper
→ Task with one reverified FileInterface
→ determineSolvability()
→ solve()
```

Provider `openai`, model `gpt-4.1-mini-2025-04-14`, and temperature `0.0` are fixed. The agent
configuration exposes zero model-callable tools, has no required-tool loop, and permits a maximum
of one provider request. A run-scoped high-priority `PreGenerateResponseEvent` listener throws
before a second provider request. The harness implements no automatic retry.

The harness invokes the four Step 1.03 adapters directly. Discovery, authorization, submission,
status, persistence, and human review never become model responsibilities. The deterministic shared
validator is also called directly before submission so structured-output and deterministic-validation
evidence remain separate.

## File transport

`FileEntityResolver` implements ADR-0008. To preserve the checksum-certified Step 1.03 service
definitions, the Step 1.04 harness constructs this additive resolver from the container-provided
entity manager and file system; it does not modify the Step 1.03 services manifest. It accepts only the exact authorized image-context shape,
rejects caller-supplied URI/path/File selectors, resolves File storage only by authorized UUID,
requires exactly one `FileInterface`, rechecks UUID/filename/MIME, permits only `public://` or
`private://`, resolves a readable local path through `FileSystemInterface`, and rechecks current
byte length and SHA-256. It returns the File entity only to the runtime process.

Evidence retains no URI, local path, File entity, bytes, Base64, or data URL. Wrapper serialization
is retained only at the pre-task/pre-image/pre-provider checkpoint.

## Human review lifecycle

The installed runner separates execution:

1. `preflight`: model-free, reset-bounded compatibility and negative-control proof.
2. `start`: exact snapshot, one provider request, one pending recommendation, then a successful pause.
3. `status`: read-only review observation.
4. `resume`: require approval by `editor_dana`, prohibit provider requests, finalize evidence,
   restore the exact pre-run snapshot, and advance status documents.
5. `restore`: abort an active run and restore the exact snapshot.
6. `audit`: verify promoted evidence and current seeded-clean state.

The start phase does not simulate approval. The resume phase refuses pending, rejected, wrong-user,
or changed-identity recommendations. It remains retryable while the recommendation is still pending;
the stored state is not advanced to `resuming` until the approved decision is observed.

## Evidence

Evidence is retained only under:

```text
evidence/gates/gate-1/drupal-ai-canonical-vertical-slice/<gate-run-id>/
```

The canonical lifecycle document validates exactly one target, one model output, one recommendation,
one validation result, one submission, pending and approved status observations, and one human-review
decision against the ADR-0007 profile and existing frozen item schemas. Supplemental implementation
evidence is separated from the canonical lifecycle document.

After the approved status is retained, the runner restores:

- 20 Articles;
- zero recommendations;
- 12 frozen targets;
- canonical sequence 1;
- the frozen target-order and Article-source hashes;
- no framework runtime state;
- no temporary AI Agent configuration;
- the custom module disabled;
- seeded-clean true.

## Scope exclusions

This package does not claim batch-contract conformance, batch recovery, failure injection,
production readiness, or Step 1.05 completion. It does not modify frozen contracts, schemas,
prompts, ADRs, contributed modules, dependency files, or source Articles.
