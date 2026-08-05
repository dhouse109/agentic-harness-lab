# ADR-0004: Define the Gate 0.5 exit at the certified substrate handoff

- **Status:** Accepted
- **Decision date:** 2026-08-05
- **Decision owner:** Program lead
- **Related evidence:** `evidence/gates/gate-0.5/substrate-certification/`

## Context

The original Step 05 implementation used a broader Gate 0.5 exit interpretation. It certified the
framework-neutral shared substrate but recorded overall Gate 0.5 as still in progress until Drupal
AI, LangGraph, and CrewAI each completed a one-image framework slice.

The implementation sequence was subsequently clarified: Gate 0.5 owns certification and freeze of
the shared Drupal substrate, while framework-owned execution belongs to later implementation
phases. Status and handoff documents were updated to reflect that sequence, but the Step 05
generator and auditor retained the old status semantics. Because those documents are part of the
certification-integrity boundary, the retained Step 05 audit correctly detected their changed
hashes.

## Decision

Gate 0.5 is complete when the framework-neutral shared substrate:

1. passes the Step 05 certification path;
2. is frozen in the hash-addressed substrate manifest; and
3. is handed off for framework-owned implementation.

A passing Step 05 run therefore records:

```text
shared_substrate_certified: true
gate_0_5_complete: true
controlled_preflight: true
framework_execution_claimed: false
model_call_performed: false
```

The Step 05 substrate preflight does not certify Drupal AI, LangGraph, or CrewAI behavior. Each
framework entry remains `certified: false` until its own framework-owned execution and evidence are
completed after the handoff. The next implementation begins in Gate 1 with:

```text
gate-1-step01-drupal-ai-batch-contract-v1.0.0
```

## Certification reconciliation

The historical run
`gate05-step05-20260805T010224Z-1100690` remains immutable evidence of the old status
interpretation. It is not edited, overwritten, or retroactively reinterpreted.

A fresh Step 05 certification run is required because certification-controlled documents and the
meaning of the generated Gate 0.5 completion field changed. The fresh run must exercise the same
four shared operations, preserve all frozen substrate hashes and semantics, restore
`seeded-clean`, generate a new retained evidence directory, and regenerate the freeze manifest and
digest.

This ADR is itself part of the Step 05 certification-integrity file set so later edits are detected
by the audit.

## Unchanged experiment boundary

This decision changes no frozen experiment constant or shared operation semantic. It does not
change the provider, model, temperature, dataset, ordering, canonical target, schemas, validators,
authentication, permissions, review destination, source-mutation prohibition, idempotency
identity, failure seam, shared Drupal logic, or dependency versions.

No model call or framework-owned execution is introduced by this reconciliation.

## Consequences

- Gate 0.5 completion means only that the shared substrate is certified, frozen, and handed off.
- Framework claims remain hypotheses until their separate implementation evidence exists.
- The prior Step 05 evidence remains historically accurate for the implementation that produced it.
- Current Step 05 audits require the new reconciliation evidence rather than silently accepting the
  changed certification documents.
- The planned Drupal AI runtime architecture decision must use the next available number,
  `ADR-0005`.
