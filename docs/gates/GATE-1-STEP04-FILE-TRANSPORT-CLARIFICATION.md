# Gate 1 Step 1.04 — File transport clarification

## Scope

This decision-only package qualifies ADR-0007 through ADR-0008. It records the permitted
File-entity identity and URI-locator boundary required by a later Step 1.04 resolver. It is not the
Step 1.04 canonical vertical slice and does not begin Step 1.05.

## Frozen boundary preserved

`shared/schemas/image-context.schema.json` remains byte-for-byte unchanged. Its image object has no
URI field and rejects additional properties. `ImageContextProvider` continues to use the
entity-owned URI internally for byte access while returning no URI. ADR-0007 remains unchanged.

## Later resolver contract

Only an authorized `get_image_context` result under `agent_bot` may supply the five authoritative
identity fields: `file_uuid`, `filename`, `mime_type`, `byte_length`, and `sha256`. A later resolver
must load only File storage by exact authorized UUID, require exactly one `FileInterface`, compare
UUID/filename/MIME exactly, then use only the resolved entity-owned URI as a `public` or `private`
local Drupal transport locator. It must resolve through `FileSystemInterface`, require a readable
local path, read current bytes, and compare exact byte length and SHA-256.

It rejects remote HTTP(S) URIs, empty or unapproved stream wrappers, zero/multiple results,
identity and byte mismatches, and all model-supplied URI/path/UUID/File selection. It retains no
URI, path, entity, bytes, Base64, or data URL in evidence. URI relocation alone is allowed only
when the authorized identity and current bytes remain exact and the new entity-owned URI is an
approved local locator.

## Permanent regression controls

The permanent clarification audit verifies the frozen schema checksum and no-URI shape, the
provider's internal-only URI handling, ADR-0007 checksum, all required identity fields, local-only
URI rules, prohibited model inputs and evidence artifacts, negative mismatch controls, and absence
of Step 1.04 implementation and Step 1.05.

This decision-only package retains no clarification evidence run or pointers. Its durable proof is
the merged ADR, profile, permanent audit, and a passing audit on the merged commit.
