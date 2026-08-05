# Gate 0.5 Step 02 — Deterministic Image Context

## Purpose

Implement and prove the shared semantic operation:

```text
get_image_context(target)
```

The operation accepts one exact object conforming to `target.schema.json` and returns a
`tool-result` envelope whose `data` conforms to `image-context.schema.json`.

## Boundary

This step is deterministic and model-free.

It may:

- verify the exact current Article revision, image field, delta, and file UUID
- read permitted Article title and plain body text
- read permitted image metadata and bytes
- return the Step 16-approved Base64 data URL at runtime
- calculate a sanitized evidence hash

It may not:

- call a model
- create a recommendation
- alter Article or image-field values
- expose unrelated content, configuration, credentials, or reviewer data
- persist the Base64 image value in evidence

## Authorization

The route reuses the existing restricted read-only permission:

```text
use agentic harness discovery tools
```

`agent_bot` has this permission. Anonymous users and `editor_dana` do not.

## Required evidence

- Gate 0.5 Step 01 baseline remains passing
- canonical sequence-1 target succeeds
- output structure and image bytes validate
- evidence hash recomputes
- repeated collection is stable except timestamps/correlation IDs
- anonymous and editor requests are denied
- malformed JSON is rejected
- malformed target identity is rejected
- changed revision and file UUID are rejected as stale
- source Article hash and suggestion count remain unchanged
- model-related environment variables are absent
