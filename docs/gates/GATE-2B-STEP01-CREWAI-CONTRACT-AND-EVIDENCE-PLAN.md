# Gate 2B Step 2B.01 — CrewAI Contract and Evidence Plan

## Boundary

Step 2B.01 freezes the comparison contract and evidence rules for the CrewAI specimen. It is a model-free, mutation-free planning boundary. It does not select the final CrewAI architecture, implement adapters, submit a recommendation, or prove persistence or continuation behavior.

Gate 2A LangGraph is certified and frozen. Gate 2B CrewAI is current. Gate 2C remains formally open but deferred from the pre-presentation critical path; no CrewAI-specific continuation evidence may be described as the shared three-framework Gate 2C result.

## Predecessor

The contract is based on merged `main` commit `0477e882987501438ae07fbb51e741b4be800843`, containing Gate 2A feature commit `1a32f8584a75dc59533f48dfb0b7636da94d5a00`.

Required frozen predecessor digests:

- Gate 0.5 substrate: `99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a`
- Gate 1 Drupal AI: `2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd`
- Gate 2A batch contract: `1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b`
- Gate 2A LangGraph freeze: `a28361c34b9d1c2089eee786324ad34cffbf54e3495f59a276c489865e5630f0`

The accepted Gate 2A certification evidence remains `evidence/gates/gate-2a/certification/gate2a-step10-20260811T034835Z-03f93652`. These artifacts establish lineage and comparison constants, not CrewAI behavior.

## Authorization

This step authorizes exactly zero model calls, zero CrewAI-origin Drupal mutations, zero source-content mutations, zero dependency changes, and zero Gate 2C executions. Ambient credentials do not expand this budget.

## Pinned runtime

The lock, installed distribution metadata, and retained Phase 0 evidence agree on:

- Python `3.12.13`
- CrewAI `1.15.10`
- CrewAI Tools `1.15.10`
- `crewai/uv.lock` SHA-256 `855e5edff2cb86eb64ea9856d239b19010e7d3b1f80c40e370ed81d66b8e4e7c`

Model-free installed-source inspection found two separate persistence families: Flow persistence through `@persist` and `SQLiteFlowPersistence`, and runtime checkpointing through `CheckpointConfig` with JSON or SQLite providers plus checkpoint restore surfaces. Nonblocking human-feedback pending/resume surfaces also exist. Those findings are classified as inspected capabilities, not observed Gate 2B behavior.

Import resolves application data through the platform/XDG data location. Any adopted storage path must therefore be bound explicitly to a CrewAI-owned, sanitized location and must not be placed under `shared/`.

## Frozen comparison contract

The machine-readable authority is `shared/contracts/GATE2B-CREWAI-BATCH-CONTRACT.json`. It preserves the frozen dataset, 12-target order, provider/model/temperature, validator, four operation semantics, reviewer and revisioned review destination, source non-mutation, automatic-publication prohibition, prompt-fairness boundary, and reserved target-6/7 Gate 2C seam.

The shared schemas are comparison and evidence contracts only. CrewAI must own its actual runtime state and persistence. The shared layer must not become a private state store or a replacement write path.

## Run and recommendation identity

A CrewAI logical run uses a unique `crewai-<UTC>-<8hex>` run ID. Supported continuation must preserve that logical run. After the runtime path is selected, the framework state/checkpoint identifier and storage provenance must be bound to the run ID in evidence.

Recommendation idempotency is defined by framework origin, logical run ID, frozen target identity, prompt version, and model ID. Restore, continuation, retry, or replay must not create a second recommendation for the same identity.

## Evidence stages

Evidence must keep these stages distinct:

1. frozen target discovery and ordering;
2. permission-scoped context retrieval;
3. raw structured model output;
4. recommendation assembly;
5. deterministic validation;
6. submission through the frozen shared operation;
7. CrewAI-owned state persistence;
8. authoritative Drupal review by `editor_dana`;
9. status observation through the frozen read operation;
10. supported CrewAI continuation;
11. completion and certification.

Raw model output contains only `proposed_alt_text`. Recommendation assembly, deterministic validation, submission, review status, and lifecycle state are separate artifacts. Hidden reasoning is never retained.

## Human review

Drupal remains the source of truth for review. A CrewAI human-feedback facility may orchestrate a pending boundary only if pinned-runtime evidence shows a clean, budget-explicit path. It may not create a second authoritative approval system. Any feedback outcome-collapse path that would perform an additional LLM call must remain disabled unless a later package declares and receives approval for that call.

## Evidence and privacy rules

Every significant run must have a unique evidence ID, an exact declared file set, a SHA-256 manifest covering that set, predecessor commit/freeze provenance, sanitized logs, and a secret scan. Failed runs remain retained with `status: fail`; they are not overwritten by later successes.

Evidence must not contain credentials, authorization headers, raw Base64 or full data URLs, private database dumps, hidden model reasoning, or unrelated private configuration. Permanent certification must check every material freeze claim against retained evidence; a freeze may not be stronger than its permanent auditor.

## What this step does not prove

Step 2B.01 does not prove model quality, persistence, checkpoint completeness, process-boundary continuation, isolation, retry behavior, human-feedback behavior, Drupal integration, idempotency, batch completion, recovery, security, cost, speed, accessibility quality, production readiness, or framework superiority.

## Next evidence boundary

The next authorized package after this step passes, is committed and merged, local `main` is resynchronized, and the post-merge audit passes is:

`gate-2b-step02-crewai-runtime-persistence-and-continuation-probe-v1.0.0`

That package remains model-free and mutation-free. It must compare the pinned supported persistence paths, demonstrate process-boundary restore/re-execution behavior and run isolation, inspect serialization/privacy and failure propagation, probe a Drupal-authoritative nonblocking continuation shape without replacing Drupal, and determine the retry controls required before any model call. It should produce an ADR only if the evidence supports a material architecture choice.

No later Gate 2B package is created by Step 2B.01. The eventual sequence follows observed CrewAI evidence questions rather than LangGraph package symmetry.
