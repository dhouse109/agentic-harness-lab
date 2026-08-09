# Gate 1 → LangGraph Handoff

Gate 1 Drupal AI is certified at freeze digest `2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd` using fresh batch run `drupal_ai-20260809T012559Z-22064c`.

## Constants LangGraph must preserve

- Dataset: 20 Articles / 12 frozen targets
- Target sequence SHA-256: `1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728`
- Provider/model: OpenAI `gpt-4.1-mini-2025-04-14`, temperature `0.0`
- Shared operations and deterministic validator remain unchanged
- Review destination: `alt_text_suggestion`
- Source mutation and automatic publication remain prohibited
- Shared comparison failure point remains after target 6 and before target 7

## Drupal AI evidence available for later comparison

- Context assembly and image identity are retained in sanitized hashes/facts.
- Four thin Drupal AI FunctionCall adapters delegate to the frozen shared substrate.
- Framework-owned Drupal key/value state tracks completed targets and next index.
- Validation and submission are lifecycle-separated.
- Step 1.06 retains real `editor_dana` revision lineage.
- The existing sequence-6/7 continuation is an implementation observation only; the later shared process-failure comparison is still open.

Do not infer any LangGraph result from Drupal AI evidence. Build and observe the LangGraph specimen independently.
