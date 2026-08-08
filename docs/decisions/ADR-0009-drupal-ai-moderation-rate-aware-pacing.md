# ADR-0009: Preserve OpenAI Moderation and Add Deterministic Rate-Aware Pacing

- **Status:** Accepted for Gate 1 Step 1.05 repair
- **Date:** 2026-08-07
- **Scope:** Drupal AI specimen only; no shared-contract/schema changes

## Context

The pinned Drupal AI/OpenAI provider performs `omni-moderation-latest` moderation before each chat request. Repeated controlled Step 1.05 starts completed sequences 1 and 2, then failed on sequence 3 with `OpenAI\Exceptions\RateLimitException` and HTTP 429. The retained allowlisted response identified `api_error_type=invalid_request_error` but exposed no numeric rate-limit headers or retry interval.

A zero-network local measurement of the exact seeded image data URLs showed the following image-only token lower bounds:

| Sequence | cl100k_base | o200k_base |
|---:|---:|---:|
| 1 | 3,300 | 3,213 |
| 2 cumulative | 6,627 | 6,463 |
| 3 cumulative | 9,948 | 9,715 |

These are lower bounds because Drupal serializes the entire multimodal chat to JSON text before the moderation call; prompt text and JSON structure are excluded from the table. The OpenAI Platform account view for the experiment showed a Tier-1 moderation limit of 10,000 TPM. This combination strongly supports moderation-window accumulation as the sequence-3 failure mechanism, while not claiming that OpenAI directly returned a `tokens_per_minute` classification.

## Decision

Keep moderation enabled and add a conservative **65-second deterministic wait before provider invocation for sequences 2 through 12**.

The pacing rule:

1. Is applied before the target's AI Agent/provider invocation, after target/context/file identity checks succeed.
2. Does not retry a failed request.
3. Does not change the model, temperature, prompt, target order, output schema, validator, review destination, source-mutation prohibition, or deterministic 6→7 interruption seam.
4. Does not add new run-state or evidence-schema properties.
5. Is auditable from the existing `model_invocation_started` event timestamps; accepted evidence must show at least 65 seconds between adjacent model invocations.
6. Remains framework-specific implementation behavior and is not a performance benchmark or framework-comparison conclusion.

## Rationale

A single moderation request is known to succeed. Spacing adjacent target invocations beyond one nominal 60-second window avoids relying on an unpublished exact moderation tokenizer or guessing a smaller throughput-optimized delay. The five waits before the deterministic midpoint add 325 seconds; the complete 12-target run contains eleven waits (715 seconds) plus normal model latency. Gate 1 prioritizes reproducibility and evidence over throughput.

## Rejected alternatives

- **Disable moderation:** rejected because it changes the pinned provider safety behavior to make the experiment pass.
- **Automatic retry/backoff:** rejected because the frozen Gate 1 contract requires zero automatic retries.
- **Change model/provider/tier:** rejected because those are frozen experiment constants or external account changes.
- **Loosen schemas/parser/validator:** rejected because the failure occurs before a normal provider response and those controls are not causal.
- **Shorter guessed delay:** rejected until a later experiment explicitly measures safe throughput; Gate 1 does not benchmark speed.

## Evidence wording

Safe wording after a passing paced batch: **The pinned Drupal AI/OpenAI provider required framework-specific pacing because its enabled moderation pre-check hit an opaque HTTP 429 under rapid serial image requests. A conservative 65-second inter-target boundary preserved moderation and zero-retry semantics.**

Do not claim that OpenAI explicitly reported a 10,000-TPM overage; that classification was inferred from the account limit, source inspection, repeated sequence-3 failures, and local token lower bounds.
