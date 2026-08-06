# ADR-0008: File-entity identity and URI locator boundary

- **Status:** Accepted for package execution only; effective when the permanent clarification audit passes
- **Decision date:** 2026-08-06
- **Qualifies:** ADR-0007; it does not replace ADR-0007's canonical-slice, image,
  serialization, state, human-review, or one-provider-request decisions
- **Predecessors:** Gate 0.5 certification; Steps 1.01, 1.02, and 1.03; and the Step 1.04
  boundary reconciliation

## Context

The frozen `image-context.schema.json` authorizes exactly the image facts `file_uuid`, `filename`,
`mime_type`, `byte_length`, `sha256`, and a runtime-only representation. It intentionally has no
File URI field and rejects additional properties. The certified `ImageContextProvider` obtains the
entity-owned URI internally only to resolve and read bytes; it omits the URI from its returned
authorized context.

ADR-0007's File-entity transport bridge incorrectly says that the later resolver must compare URI
identity against the authorized context. No expected URI exists in that context, so that comparison
cannot be made without changing a frozen contract or accepting an unauthorized input.

## Decision

### Authorized File identity

The later framework-owned resolver accepts only the authorized context returned by the
`get_image_context` adapter while the call is authorized as `agent_bot`. It establishes File identity
by exact equality of every authorized identity field:

```text
file_uuid
filename
mime_type
byte_length
sha256
```

It resolves File storage only from the authorized `file_uuid` using:

```text
entity_type.manager
  -> getStorage('file')
  -> loadByProperties(['uuid' => $authorized_uuid])
```

Exactly one result must be a `FileInterface`. The resolver must compare that entity's UUID,
filename, and MIME type exactly to the authorized context.

### URI locator boundary

The resolved entity's URI is only an internal Drupal transport locator. It is not an authorized
identity field, is not supplied by the model or another request field, and is never compared to an
expected URI. The resolver must require the entity-owned URI to be non-empty, use one explicitly
approved local Drupal stream-wrapper scheme (`public` or `private`), reject `http` and `https`,
resolve through `FileSystemInterface`, and produce a readable local path.

The resolver must read the current bytes at that local path and compare their byte length and
SHA-256 exactly to the authorized context. It fails closed for a UUID, filename, MIME type, byte
length, hash, resolution, readability, multiplicity, or stream-wrapper mismatch.

A URI change alone is not an identity failure only if the same authorized `file_uuid` resolves,
filename and MIME type remain exact, the current byte length and SHA-256 remain exact, and the new
URI remains a permitted local Drupal locator.

### Evidence and scope

Evidence must never retain the URI, resolved local path, File entity, raw bytes, Base64, or a data
URL. Model-supplied URI, path, UUID, or File selection is prohibited. Source Article and image-field
mutation remain prohibited.

This decision changes no frozen schema, shared contract, shared prompt, `ImageContextProvider`,
Step 1.03 adapter, tool implementation, ADR-0007 text, dependency, lock file, status document, or
accepted predecessor evidence. It authorizes no resolver implementation, canonical vertical slice,
model/provider request, evidence run, Step 1.05 work, or source mutation.

## Consequences

ADR-0007 remains authoritative for its canonical-slice evidence, image transport,
serialization/checkpoint, state, human-review, and one-provider-request boundaries. This ADR only
corrects the impossible URI-identity comparison by separating authorized File identity from the
entity-owned URI transport locator.
