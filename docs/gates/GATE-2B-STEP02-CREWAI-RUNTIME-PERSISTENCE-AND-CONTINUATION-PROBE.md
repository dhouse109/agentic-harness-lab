# Gate 2B Step 2B.02 — CrewAI runtime, persistence, and continuation probe

## Boundary

This boundary observes pinned CrewAI 1.15.10 and CrewAI Tools 1.15.10 behavior
without model/provider calls or Drupal mutation. It is an architecture-selection
probe, not the CrewAI specimen, adapter implementation, batch, or Gate 2C recovery
experiment.

The exact merged predecessor is `7bea4320c08670d8e9a0c71f88d10922fced8c1e`.
Step 2B.01 evidence and the Gate 2A/Gate 0.5 freezes remain controlling.

## Candidate families

The probe compares these independent pinned-runtime facilities:

1. Flow state persistence with `@persist`, `FlowPersistence`, and
   `SQLiteFlowPersistence`;
2. runtime checkpoints with `CheckpointConfig`, `JsonProvider`, and
   `SqliteProvider`;
3. nonblocking Flow human feedback with `HumanFeedbackPending`,
   `from_pending()`, and `resume()`.

Persistence, checkpoint restore, continuation, replay, and re-execution are reported
separately. A mechanism is not called resume merely because it reloads state.

## Controlled runtime storage

Each evidence run binds XDG data/config/cache paths and all candidate storage beneath
`crewai/.runtime/gate2b-step02/<evidence-id>/`. That path is CrewAI-owned and outside
`shared/`. The probe hashes and inspects every runtime artifact, records sanitized
storage provenance, then removes only that exact run directory. Runtime binaries are
not accepted as evidence; sanitized inspection reports are.

Flow 1.15.10 auto-creates unified memory when `memory` is `None`. The superseding
probe retains three separately classified paths: an unmodified/default phase, a
supported-public-extension phase using the pinned
`set_memory_storage_factory(...)` application-startup extension point, and a
private `_skip_auto_memory = True` probe-isolated diagnostic. The private path is
never accepted as sole architecture support. A default timeout states only that the
tested lifecycle did not reach the intended boundary within the declared timeout.

The first retained run,
`gate2b-step02-20260812T010531Z-00000001`, remains byte-identical. Its mechanical
capture originally passed, but a later evidence-integrity review found its
architecture conclusion unsupported because all Flow phases used an unlabeled
private bypass and isolation/retry controls were incomplete. It is retained as
diagnostic, superseded for architecture acceptance, and is not corrupted evidence.
Step 2B.02 remains open. The byte-identical v2 capture,
`gate2b-step02-20260812T015108Z-00000001`, passed its capture boundary but retained
architecture status `unresolved`. Four blocked socket attempts associated with the
JSON/SQLite checkpoint write/restore phases lacked call-site provenance, its native
structured-output fallback finding was a false negative, and its checkpoint wording
overstated terminal-output recovery. A separately retained targeted follow-up corrects
those interpretation and acceptance gaps without rewriting either run.

## Targeted closure follow-up

The targeted follow-up repeats only the JSON and SQLite runtime-checkpoint write and
restore phases. A fail-closed socket guard records sanitized stack frames before any
connection and retains no headers, keys, bodies, prompts, query strings, cookies, or
environment dump. It traces each event into pinned installed source and classifies
whether the behavior belongs to the runtime-checkpoint path, another optional
facility, or an unresolved selected-path dependency.

Pinned source inspection corrects the structured-output predicate: the native OpenAI
path can proceed from `beta.chat.completions.parse(...)` to
`chat.completions.create(...)` when parsed output is absent. Those are potentially
separate provider requests, so a later one-call boundary must fail closed before or
explicitly count the fallback. Learning remains disabled with `learn=False` because
the pinned pre-review and lesson-distillation paths can add inference.

The runtime-checkpoint finding is limited to: terminal-output reconstruction was
observed across processes; live Flow state restoration or workflow continuation was
not demonstrated. Runtime `CheckpointConfig` is an investigated candidate, not a
mandatory experiment requirement. The follow-up tests whether it can be explicitly
excluded while selecting supported Flow persistence, the public
`set_memory_storage_factory(...)` extension, and
`HumanFeedbackPending`/`from_pending()`/`resume()` for the Drupal-authoritative review
lifecycle.

## Governed version-check disposition

The immutable targeted supplemental capture
`gate2b-step02-followup-20260812T022947Z-00000001` retained four blocked events with
raw classification `unresolved_path`. Those bytes and that historical classifier are
not rewritten. Their retained call stacks enter the Flow-start console handler,
`_show_version_update_message_if_needed()`, `crewai_core.version`, and finally
`urllib.request.urlopen()`. Later direct review of the pinned CrewAI 1.15.10 and
CrewAI Core 1.15.10 source identifies that exact path as the console
version-availability check rather than model/provider, checkpoint-persistence,
memory-initialization, or telemetry traffic.

The governed disposition is retained separately under
`evidence/gates/gate-2b/runtime-probe-disposition/`. It binds every interpreted event
to the immutable supplemental manifest, exact canonical event hash, full retained
sanitized stack, pinned source hashes, and package versions. It also verifies the
public `CREWAI_DISABLE_VERSION_CHECK=true` guard model-free: helper counters are
reached with the guard absent and are not reached with it enabled, with no successful
network connection. This layer records subsequent evidence-backed interpretation; it
does not pretend that the original classifier recognized the path.

The selected candidate excludes runtime `CheckpointConfig` as an investigated
optional facility and applies the public version-check disable control. Network
behavior remains architecture-blocking if it is unexplained or belongs to the
selected Flow/pending-resume path. A separately governed, publicly suppressible
console check does not by itself block a candidate whose selected-path evidence
independently records zero network attempts.

## Process boundary and isolation

Every write, restore, pending, resume, and negative-control phase runs in a separate
process session with a recorded PID/process-group ID and a hard timeout. Timeout
cleanup terminates only the exact probe-owned process group, escalating boundedly.
Run A and run B are independently persisted and reloaded; unknown identity and
wrong/cross-identity controls are distinct from explicit state forking/hydration.

## Human-review boundary

The pending probe uses a deterministic provider that raises
`HumanFeedbackPending`. It performs no notification and no external mutation. Resume
uses no `emit` outcomes, so no outcome-collapse LLM call is required. Source and
runtime guards fail if any BaseLLM call occurs. Drupal remains the later authoritative
review record; the string supplied to the model-free resume phase is only a lifecycle
stand-in.

Pinned source inspection is retained to show that non-empty free-form feedback with
`emit` configured calls `_collapse_to_outcome()` and can attempt a structured LLM call
plus a fallback LLM call. `learn=True` can add pre-review and lesson-distillation
calls. Those paths remain prohibited unless a later package declares their budgets.

## Failure and privacy controls

The probe observes deterministic method failures, persistence-provider failures, and
unknown checkpoint identities. It does not use the reserved target-6/7 Gate 2C seam.
Serialized data and captured output are scanned for credentials, authorization
headers, image bytes/data URLs, Base64-like payloads, hidden reasoning markers, full
Article bodies, and unrelated environment data.

## Architecture decision rule

`architecture-recommendation.json` is `recommendation_ready` only if machine-enforced
predicates prove a supported public candidate, default/private classification,
process-boundary semantics, independent A/B isolation, wrong and unknown identities,
privacy/storage provenance, feedback implications, transport retry controls,
validation/task/guardrail retry controls, failures, and zero authorization budgets.
The permanent auditor independently recomputes those predicates. Runner output is not
self-authenticating. Otherwise status is `unresolved`, no ADR is created, and the
material architecture decision remains blocked.

For a supplemental `recommendation_ready` result, the auditor also requires exact
call-site attribution for hidden network activity, corrected native parse fallback
and learning controls, the narrow terminal-output checkpoint characterization, and
an evidence-backed distinction between the selected required path and an explicitly
excluded optional checkpoint path. Hidden behavior in a selected path remains
blocking; an attributed behavior confined to a nonselected optional path does not
automatically invalidate an otherwise independently supported candidate.

The governed disposition auditor independently recomputes the full selected-path
decision. In addition to retained evidence integrity, it requires supported public
Flow APIs; no private-instrumentation dependency; passing default/public Flow
lifecycle, process-boundary persistence, independent A/B, wrong/unknown identity,
and pending/resume identity/no-replay controls; Drupal authority; privacy and storage
provenance; the terminal-output-only checkpoint wording; explicit nonselection of
runtime checkpoints; native parse-to-create fallback awareness; later
`max_retries=0`, guardrail/correction, `learn=False`, feedback-collapse, and complete
provider-request accounting controls; the source-bound version-check disposition and
public disable proof; zero authorization counts; and deferred/unexecuted Gate 2C.
The generated recommendation field is not self-authenticating.

The governed machine recommendation passed all 25 permanent predicates with status
`recommendation_ready`. The human architecture authority then separately approved
the selected path. ADR-0012 records that approval, and
`shared/contracts/GATE2B-STEP02-CREWAI-ARCHITECTURE-CLOSURE.json` preserves the
machine-recommendation versus human-decision distinction. Tradeoffs remain
observations, never framework superiority or inferiority.

## Accepted architecture and closure

The accepted architecture uses supported CrewAI Flow, public
`set_memory_storage_factory(...)`, `SQLiteFlowPersistence`, and
`HumanFeedbackPending` / `from_pending()` / `resume()`. Drupal remains the
authoritative review system. The specimen must set `learn=False`, disable the console
version check with `CREWAI_DISABLE_VERSION_CHECK=true`, configure later transport
retries to zero, avoid guardrail retries, fail closed on invalid structured output,
prevent or separately budget structured-output correction/fallback calls, and count
every SDK/provider request.

Runtime `CheckpointConfig` is investigated optional/nonselected functionality.
Private `_skip_auto_memory` instrumentation is nonselected and cannot become an
architecture dependency. The accepted checkpoint characterization remains:

> terminal-output reconstruction observed; live Flow state restoration/continuation not demonstrated

Step 2B.02 is complete only when the permanent closure audit verifies ADR-0012,
the machine/human closure contract, all four immutable evidence boundaries, all 25
architecture predicates, zero authorization counts, deferred/unexecuted Gate 2C,
and lifecycle agreement. Step 2B.03 is named but remains unbegun until the completed
boundary is committed, merged, resynchronized, and post-merge audited.

## Exact evidence set

Each retained run contains exactly these 18 files:

1. `api-surface.json`
2. `architecture-recommendation.json`
3. `authorization.json`
4. `evidence-manifest.json`
5. `failure-propagation.json`
6. `flow-persistence.json`
7. `human-feedback-continuation.json`
8. `predecessor.json`
9. `probe-log.txt`
10. `process-boundary.json`
11. `retry-hidden-call-controls.json`
12. `run-isolation.json`
13. `runtime-checkpoint-json.json`
14. `runtime-checkpoint-sqlite.json`
15. `runtime-versions.json`
16. `serialized-state-privacy.json`
17. `storage-provenance.json`
18. `summary.json`

Fresh superseding summaries and manifests use schema version 2. The same 18 filenames
remain sufficient because default/instrumented classification, isolation controls,
retry layers, and lifecycle provenance are structured within their existing semantic
reports. The manifest hashes the other 17 files. Failed runs use the same exact set and are
retained under `evidence/gates/gate-2b/runtime-probe/` without overwrite.

Targeted follow-up runs are supplemental rather than fake full probes. Each contains
exactly nine significant files under
`evidence/gates/gate-2b/runtime-probe-followup/`: `architecture-impact.json`,
`authorization.json`, `checkpoint-network-provenance.json`,
`checkpoint-semantics.json`, `evidence-manifest.json`,
`pinned-source-findings.json`, `predecessor.json`, `summary.json`, and
`targeted-probe-log.txt`. The manifest hashes exactly the other eight files. Failed
targeted runs remain uniquely retained and never overwrite either prior capture.

Governed interpretation runs are neither runtime probes nor rewritten supplemental
evidence. Each contains exactly six significant files under
`evidence/gates/gate-2b/runtime-probe-disposition/`:
`architecture-disposition.json`, `authorization.json`,
`evidence-manifest.json`, `network-event-disposition.json`, `provenance.json`, and
`summary.json`. The manifest hashes exactly the other five files. The network
disposition has its own Draft 2020-12 schema and binds all three immutable Step 2B.02
captures by exact manifest/summary hashes and lifecycle disposition.

## Authorization

- model/provider calls: 0
- CrewAI-origin Drupal mutations: 0
- source-content mutations: 0
- authoritative human-review actions: 0
- dependency changes: 0
- Gate 2C executions: 0
- live recommendation submissions: 0
