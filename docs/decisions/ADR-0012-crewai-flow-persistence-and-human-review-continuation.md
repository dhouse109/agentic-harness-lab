# ADR-0012: CrewAI Flow persistence and human-review continuation

- **Status:** Accepted
- **Decision date:** 2026-08-11
- **Decision authority:** Human approval authority
- **Machine recommendation:** `recommendation_ready`
- **Governing evidence:** `evidence/gates/gate-2b/runtime-probe-disposition/gate2b-step02-disposition-20260812T024610Z-00000001`

## Context

Gate 2A LangGraph is certified and frozen. Gate 2B must implement a CrewAI-owned
orchestration, persistence, and continuation lifecycle while preserving the frozen
cross-framework experiment. Drupal remains the authoritative human-review system.
Gate 2C's identical three-framework failure/recovery comparison remains deferred and
unclaimed.

Step 2B.02 retained four model-free evidence boundaries. Its permanent auditor
independently recomputed 25 architecture predicates and produced the machine status
`recommendation_ready`. The human approval authority subsequently approved the
architecture below. The machine recommendation and human decision are distinct
provenance events.

## Decision

Use this Gate 2B CrewAI architecture:

- supported CrewAI `Flow` as the orchestration and lifecycle basis;
- public `set_memory_storage_factory(...)` for controlled CrewAI memory storage;
- `SQLiteFlowPersistence` for CrewAI-owned Flow persistence;
- `HumanFeedbackPending` with `from_pending()` / `resume()` for the explicit
  human-review continuation boundary;
- Drupal `alt_text_suggestion` review by `editor_dana` as the authoritative decision;
- `learn=False`;
- `CREWAI_DISABLE_VERSION_CHECK=true`;
- later transport retries configured to zero;
- guardrail retries set to zero or avoided;
- invalid structured output fails closed;
- structured-output correction/fallback calls are prevented or separately budgeted;
- every SDK/provider request is counted.

Runtime `CheckpointConfig` is excluded as investigated optional/nonselected
functionality. Private `_skip_auto_memory` instrumentation is also nonselected and
must not become an architecture dependency.

The accepted checkpoint characterization is exactly:

> terminal-output reconstruction observed; live Flow state restoration/continuation not demonstrated

## Why this path was selected

- Default unmodified Flow construction and kickoff completed in the pinned runtime.
- The supported public memory-storage extension completed without depending on a
  private bypass.
- Flow run A and run B persisted across separate processes and remained isolated.
- The pending / `from_pending()` / `resume()` path preserved the logical run identity.
- Prior model-owning work did not replay across the selected human-review
  continuation boundary.
- Storage ownership, path provenance, serialization, and privacy checks passed.
- The selected architecture uses pinned supported public APIs and does not depend on
  private `_skip_auto_memory` instrumentation.

## Alternatives and observations

### Private `_skip_auto_memory` probe

The private override was useful as probe-isolated diagnostic instrumentation for
separating persistence mechanics from automatic memory initialization. It is not an
acceptable dependency for the selected specimen and cannot independently support an
architecture decision.

### Ordinary Flow state restoration or forking

The tested ordinary state restoration/fork path hydrated prior state and re-executed
prior execution units. That is hydration plus re-execution, not continuation.

### Runtime `CheckpointConfig` JSON and SQLite providers

Both providers persisted checkpoint payloads across processes and recovered captured
terminal output. Live Flow execution state restoration and workflow continuation were
not demonstrated. The subsystem was investigated but is not required by the selected
Flow persistence and pending/resume lifecycle, so it is explicitly nonselected.

## Network and version-check finding

The immutable supplemental capture originally classified four blocked outbound
attempts as `unresolved_path`. A later governed, pinned-source-backed disposition
identified their call path as `crewai_version_availability_check`, reached through
CrewAI's Flow-start console formatter and `crewai_core.version` before
`urllib.request.urlopen()`.

That pathway is not a model/provider request, checkpoint persistence/provider logic,
memory initialization, or telemetry export. Pinned CrewAI exposes the public
`CREWAI_DISABLE_VERSION_CHECK=true` control, which suppressed the pathway in a
model-free blocked-network control. The original classification remains immutable;
the governed disposition records the later evidence-backed interpretation.

## Required inference controls

Later model-backed packages must:

- set transport `max_retries=0` where supported by the pinned provider/client path;
- count every SDK/provider request, including requests below a framework-level
  counter;
- recognize that native OpenAI structured parsing can fall through from
  `beta.chat.completions.parse(...)` to `chat.completions.create(...)` when parsed
  output is absent;
- prevent or separately budget structured-output correction and fallback calls;
- set guardrail retries to zero or avoid retrying guardrails;
- fail closed on invalid structured output;
- keep `learn=False`;
- disable feedback-collapse calls unless they receive a separately declared budget;
- prove that the selected pending/resume lifecycle does not replay a model-owning
  execution unit.

## Consequences

- Step 2B.03 must implement thin CrewAI adapters and lifecycle code that conform to
  this architecture without duplicating frozen shared business semantics.
- The canonical real-model vertical slice must prove its declared one-call boundary
  under the controls above.
- Later human-review continuation must keep Drupal as the authoritative review record.
- Runtime `CheckpointConfig` may not enter the selected specimen without a separately
  governed architecture change that reopens this decision.
- CrewAI-owned persistence remains outside `shared/`.

## Evidence references

The decision binds, without copying or rewriting, these retained boundaries:

1. Diagnostic runtime capture
   `evidence/gates/gate-2b/runtime-probe/gate2b-step02-20260812T010531Z-00000001`
   - manifest SHA-256: `6bbb9619df39cfba939f09223bde9ce160b52476598d2b847a0591c3a0edb5f5`
   - summary SHA-256: `e7c2bde43dcc30c8b912099ac2e6682684649ebbd0125a10b5fe0d3940494aee`
   - disposition: diagnostic; superseded/unaccepted for architecture selection.
2. V2 runtime capture
   `evidence/gates/gate-2b/runtime-probe/gate2b-step02-20260812T015108Z-00000001`
   - manifest SHA-256: `8339eca113dfb1bc5cfa15d2fcbc1f95e104d908852e0656024f299f4e2c2b66`
   - summary SHA-256: `b03d7c8a787757b020f889faa8cb3f6393edfb0f477e2a39dd93dbbd868ef349`
   - disposition: completed runtime capture; initially architecture unresolved.
3. Targeted supplemental capture
   `evidence/gates/gate-2b/runtime-probe-followup/gate2b-step02-followup-20260812T022947Z-00000001`
   - manifest SHA-256: `6654fd33e10efdf275f0aa9ea104293ed1f7ba3092d054718a9ac0a491b07a79`
   - summary SHA-256: `48fa2e41db6089cf63d3f250b8a31c547c322dc8e72d8a25ae9dc1078a734a57`
   - disposition: completed supplemental capture; source attribution initially unresolved.
4. Governed architecture disposition
   `evidence/gates/gate-2b/runtime-probe-disposition/gate2b-step02-disposition-20260812T024610Z-00000001`
   - manifest SHA-256: `8666c77d3fc7f6a82a88adec652ea30b59198a3ce700ea14069b2ea6496c0f7d`
   - summary SHA-256: `77d56c2a9df0c3f6c269c1c9b3a5e9a4ec816541827aa5add74b570bcf15ad45`
   - architecture-disposition SHA-256: `ab23b6a78638b7c45346ba0b5419745779f37b56e0fe6c67faac8b49597040d8`
   - machine status: `recommendation_ready`; all 25 permanent predicates passed.

## Nonclaims

Step 2B.02 made no real model/provider call and demonstrates no model-output quality.
It performed no live Drupal recommendation, review, or mutation. It did not complete
the frozen 12-target CrewAI batch. Its CrewAI-specific continuation evidence is not
Gate 2C failure/recovery evidence. This decision makes no production-readiness,
security, accessibility-quality, cost, speed, or framework-superiority claim.
