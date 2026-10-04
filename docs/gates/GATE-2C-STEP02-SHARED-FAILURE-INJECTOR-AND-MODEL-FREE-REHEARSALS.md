# Gate 2C Step 2C.02 — Shared Failure Injector and Model-Free Rehearsals

## Status and proof boundary

Step 2C.02 is prepared and partially exercised; it is not completed or certified.
Installation does not complete the step.
Gate 2C remains `DEFERRED_UNCLAIMED`, Gate 2 remains `NOT_COMPLETE`, and no
Gate 2C.03 trial is authorized.

The corrected-environment full offline rehearsal
`gate2c-step02-offline-20260930T222029Z-24c7b158` is durably finalized `PASS`.
Its machine recommendation is `APPROVAL_READY`. The human operator separately
approved the public `SQLiteFlowPersistence.load_state(...)` plus
`Flow.kickoff(inputs={"id": same_flow_id})` candidate for the model-free CrewAI
recovery proof. That decision does not certify Step 2C.02, authorize another
rehearsal, update a final pointer, or authorize Step 2C.03.

The append-only
[`GATE-2C-STEP02-EXECUTION-ENVIRONMENT-FINDING.md`](GATE-2C-STEP02-EXECUTION-ENVIRONMENT-FINDING.md)
binds the subsequent restricted-environment finding and the corrected-environment
representative startup PASS. It changes no historical result or classification and
does not constitute the pending complete CrewAI recovery proof.

Package v1.0.0 correctly used the Gate 2C.01 permanent auditor at its
pre-installation boundary, but a later manual preflight invoked that predecessor
auditor again after the fourteen Step 2C.02 sources had been installed. The older
auditor rejected those legitimate untracked successor files because its protected
worktree inventory intentionally ends at Step 2C.01. No rehearsal began and no
runtime or evidence identity was created.

Repair package v1.0.1 leaves the Gate 2C.01 auditor, contract, and retained evidence
unchanged. It makes the installed Step 2C.02 successor audit the post-installation
authority and strengthens that audit to verify the complete retained Step 2C.01
certification family, exact predecessor freeze bindings, all fourteen installed
source hashes, all eleven protected Gate 2B path hashes, the retained snapshot, and
closed-world rejection of unexpected untracked paths. The original Gate 2C.01 audit
remains the package's pre-installation control and is not a valid post-installation
inventory validator for this successor overlay.

The first authorized v1.0.1 offline attempt,
`gate2c-step02-offline-20260922T174202Z-35a22675`, is retained as a quarantined
failed attempt. Its three files are hash-bound by the successor audit and are not an
accepted rehearsal family. LangGraph emitted a target-6 midpoint sidecar while the
pinned runtime's default asynchronous durability still had checkpoint writes in
flight. The supervisor delivered SIGKILL based on sidecar evidence, but public
`SqliteSaver.get_tuple(...)` later exposed a committed checkpoint at step 0 with an
empty completed sequence, next target 1, and pending writes. Recovery therefore
failed before target 7, CrewAI never started, and no replacement attempt was launched.

Repair package v1.0.2 uses the pinned LangGraph 1.2.10 public
`CompiledStateGraph.invoke(..., durability="sync")` control for the disposable
pre-kill invocation. In that runtime, `sync` persists changes before the next graph
step begins. A separate LangGraph-runtime verifier reads the latest committed
checkpoint through public `SqliteSaver.get_tuple(...)`; the external supervisor
requires its exact target-6 projection, run identity, checkpoint ID, step 6 metadata,
and zero pending writes before SIGKILL is permitted. A midpoint sidecar alone can no
longer authorize termination or produce PASS evidence.

The authorized v1.0.2 attempt,
`gate2c-step02-offline-20260922T213931Z-9f3c7a21`, is also retained as a
quarantined failed attempt rather than an accepted ten-file family. Its LangGraph
portion passed synchronous target-6 durability, actual-worker signal-9 termination,
and public recovery at target 7. CrewAI then failed before Flow construction because
its default unified-memory `LanceDBStorage` resolved through
`crewai_core.paths.db_storage_path()` to the read-only default user-data directory.
No replacement attempt was automatic, and the successful LangGraph partial
observation is preserved without rerun or promotion.

Repair package v1.0.3 binds both partial evidence families and all seventeen retained
run-scoped runtime artifacts by exact SHA-256. The second family's hashes are the
verified post-reboot baseline, not proof of pre-reboot byte identity. Pinned CrewAI
1.15.10 source delegates default storage to installed `appdirs`, whose Linux paths
honor `XDG_DATA_HOME`, `XDG_CONFIG_HOME`, and `XDG_CACHE_HOME`. Before the CrewAI
interpreter starts, the rehearsal parent binds all three to fresh writable directories
below that attempt's disposable CrewAI control path, removes any ambient
`CREWAI_STORAGE_DIR` override, and disables the public version check. The adapter
fails closed unless those bindings are run-scoped, writable, and separate from the
authoritative `SQLiteFlowPersistence` database. This storage-bootstrap repair does
not change the pending recovery candidate or constitute a rehearsal result.

The authorized v1.0.3 attempt,
`gate2c-step02-offline-20260923T105822Z-ba36ceed`, is a third quarantined failed
attempt. Its LangGraph portion again passed target-6 durable-checkpoint verification,
actual-worker signal-9 termination, and public recovery beginning at target 7. The
CrewAI worker remained alive until the fixed 30-second supervisor timeout. Its
authoritative SQLite database exists with the expected tables and zero Flow-state
rows, and its run-scoped memory directory exists but is empty. Given the v1.0.3
source order, those artifacts establish that CrewAI import, XDG validation, and
`SQLiteFlowPersistence` initialization completed and that default memory
initialization was entered. They do not establish whether `lancedb.connect(...)`
was merely slow or blocked, whether Flow construction later completed, or whether
kickoff began. The timeout is therefore classified as a startup failure before a
verified seam, not as proof that Flow construction failed and not as an experimental
SIGKILL. The SQLite WAL/SHM hashes in the retained inventory are the verified
post-failure inspection baseline and are not represented as at-timeout bytes.

Repair package v1.0.4 hash-binds the third family's four evidence files, twelve
runtime files, and exact runtime directory inventory without modifying or promoting
any failed family. It adds fixed-schema, timestamped phase markers at worker entry,
XDG validation, CrewAI import, SQLite initialization, Flow construction/memory
initialization, Flow invocation, method entry, target-6 persistence, public midpoint
readback, and seam emission. The supervisor retains only a bounded, redacted stderr
tail and records the last valid phase and cleanup termination classification. The
30-second limit and public recovery architecture are unchanged. A separately
authorized Flow-construction-only startup diagnostic is available when actual
runtime observation is needed; installation, self-check, and preview never invoke it.

That standalone diagnostic,
`gate2c-step02-startup-20260923T124207Z-930eee56`, is preserved as a fourth
quarantined failed identity. It proves CrewAI import completed in approximately
4.41 seconds, SQLite persistence initialized, and Flow construction/default memory
initialization was entered. No later completion marker appeared during at least
24.67 seconds before the fixed 30-second timeout caused diagnostic cleanup. No Flow
method, experimental SIGKILL, or recovery ran. Its two evidence files and three
runtime artifacts are exact-hash-bound as a verified post-failure baseline. The
SQLite hash does not claim pre-termination identity for mutable sidecars, which were
not present at post-failure inspection.

Repair package v1.0.5 follows the pinned construction path from
`Flow._flow_post_init()` to `Memory.model_post_init()`, then
`LanceDBStorage.__init__()`, where the actual public Python connection boundary is
`lancedb.connect(path)`. That function constructs `LanceDBConnection`, which reaches
the native LanceDB binding for a local database. Diagnostic mode uses the standard
library trace facility bound to the exact imported `lancedb.connect.__code__`
object. It records only entry, successful return, or exception class; it reads no
arguments, results, frame locals, environment, or exception message and never
replaces the function. The trace is armed only around Flow construction in
`diagnose-startup`; pre-kill and recovery paths are unchanged.

The separately authorized v1.0.5 diagnostic,
`gate2c-step02-startup-20260923T134027Z-e5acfebb`, is preserved as a fifth
quarantined failed identity. It entered the exact imported
`lancedb.connect.__code__` boundary approximately 6.384 seconds after worker
initialization. Neither a return nor an exception marker appeared before the exact
30-second timeout performed non-experimental cleanup. Its two evidence files and
three runtime artifacts are exact-hash-bound as a verified post-failure baseline.
It has no evidence manifest, and the retained SQLite hash is not represented as
proof of at-timeout byte identity.

Repair package v1.0.6 adds an optional diagnostic-only standard-library location
probe after that exact connection-entry marker. A daemon sampler may inspect the
worker thread through `sys._current_frames()` at 8 and 18 seconds after entry and
immediately reduces at most twelve frames to bounded module/function labels. It
retains no locals, arguments, results, exception text, raw path, environment,
payload, or traceback. If Python cannot schedule the sampler or expose a frame, the
parent finalizes an explicit `SNAPSHOT_UNAVAILABLE` status after cleanup; absence is
never interpreted as a native deadlock. The probe does not replace
`lancedb.connect`, runs only in `diagnose-startup`, and remains separate from
`SQLiteFlowPersistence` and normal rehearsal/recovery paths.

The separately authorized v1.0.6 diagnostic,
`gate2c-step02-startup-20260923T144053Z-06d5f691`, is preserved as a sixth
quarantined failed identity. Both scheduled snapshots captured only the main worker
waiting through `concurrent.futures.Future.result()` and
`lancedb.background_loop.BackgroundEventLoop.run()` while
`LanceDBConnection.__init__()` awaited completion. No connection return or
exception occurred before the exact 30-second non-experimental cleanup. Its two
evidence files and five runtime artifacts are exact-hash-bound as a verified
post-failure baseline. It has no evidence manifest, and the retained SQLite hash is
not represented as proof of at-timeout byte identity. These Python locations do
not establish a native deadlock, I/O wait, lock condition, or other root cause.

Repair package v1.0.7 retains the exact 8- and 18-second schedule and extends only
the diagnostic sampler to two fixed roles: `MAIN_WORKER` and
`LANCEDB_BACKGROUND_LOOP`. It identifies the exact pinned
`lancedb.background_loop.LOOP.thread`, then requires a live daemon with a stable
identifier that independently matches exactly one enumerated
`LanceDBBackgroundEventLoop`. Each sampling point makes one
`sys._current_frames()` call and immediately reduces at most twelve locations per
role. Missing, dead, renamed, ambiguous, mismatched, unstable, or frameless
background observations become `BACKGROUND_THREAD_UNAVAILABLE` or
`BACKGROUND_FRAME_UNAVAILABLE`. No thread identifier, frame object, callback, task
introspection, raw path, local, argument, result, payload, or environment value is
retained. The diagnostic timeout, connection trace, CrewAI architecture,
pre-kill/recovery paths, and cleanup classification are unchanged.

The separately authorized v1.0.7 diagnostic,
`gate2c-step02-startup-20260923T184826Z-76fef1dc`, is preserved as a seventh
quarantined failed identity. At both sampling points, the main worker remained in
`concurrent.futures.Future.result()` through LanceDB's synchronous background-loop
bridge while the independently verified `LanceDBBackgroundEventLoop` thread was in
`EpollSelector.select()` through `run_forever()`. No connection return or exception
occurred before the exact 30-second non-experimental cleanup. Its two evidence files
and five runtime artifacts are exact-hash-bound as a verified post-failure baseline.
It has no evidence manifest, and the SQLite digest is not represented as proof of
at-timeout byte identity. Selector polling is consistent with an ordinarily
suspended asyncio task and does not establish a native deadlock, lost wakeup, I/O
wait, lock condition, filesystem defect, or other root cause.

Repair package v1.0.8 adds a distinct, separately authorized differential diagnostic
that calls the pinned LanceDB 0.30.0 public `lancedb.connect_async()` exactly once
through `asyncio.run()` and a caller-owned event loop. It uses a fresh writable
local-only database directory and does not import CrewAI, construct a Flow, use
synchronous `lancedb.connect()`, invoke the synchronous background-loop bridge, or
inspect asyncio tasks. The existing CrewAI startup, pre-kill, recovery, supervisor,
and persistence paths remain unchanged. Its external hard limit remains exactly 30
seconds, with no retry or fallback.

The differential result is restricted to four classifications:

- `DIRECT_ASYNC_CONNECT_RETURNED`: direct async connection completed in the
  caller-owned loop; this narrows the investigation but does not prove a synchronous
  bridge defect.
- `DIRECT_ASYNC_CONNECT_TIMEOUT`: direct async connection did not complete within
  the same 30-second bound; this does not prove a native cause.
- `DIRECT_ASYNC_CONNECT_EXCEPTION`: the public async call raised; retain only its
  exception class, never its message or traceback.
- `PREFLIGHT_OR_SETUP_FAILURE`: public API validation or isolated local setup failed;
  do not interpret this as connection behavior.

The separately authorized v1.0.8 diagnostic,
`gate2c-step02-async-20260923T235257Z-392b56a7`, is preserved as an eighth
quarantined failed identity. It entered exactly one public
`lancedb.connect_async()` call against a fresh empty local-only directory through
`asyncio.run()` and a caller-owned event loop. It neither returned nor raised an
observed Python exception before the exact 30-second non-experimental timeout
cleanup. Its four evidence files and two runtime artifacts are exact-hash-bound as
a verified post-failure baseline. It has no evidence manifest; the storage
directory remained empty. This reproduces bounded connection noncompletion without
CrewAI and without the synchronous bridge, but does not establish a native
deadlock, filesystem failure, lost wakeup, or other root cause.

Repair package v1.0.9 adds one distinct, separately authorized in-memory
differential mode. Pinned LanceDB 0.30.0 forwards the public async URI unchanged to
the same native async connection binding, and its installed native wheel contains
the built-in `memory:///` object-store route and `MemoryStoreProvider`; the pinned
Python package also documents an operational `memory:///` database. The new worker
therefore makes exactly one `lancedb.connect_async("memory://")` call in a fresh
subprocess and caller-owned event loop. It creates no filesystem database, imports
no CrewAI, uses no synchronous bridge, removes inherited provider/API credentials,
and retains the existing external 30-second bound without retry or fallback.

The in-memory result is restricted to four classifications:

- `IN_MEMORY_ASYNC_CONNECT_RETURNED`: the native connection completed with this
  backend and execution context; this does not prove the filesystem is defective.
- `IN_MEMORY_ASYNC_CONNECT_TIMEOUT`: bounded noncompletion occurred with both the
  previously tested local-disk path and this in-memory path; this does not establish
  a native root cause.
- `IN_MEMORY_ASYNC_CONNECT_EXCEPTION`: the public in-memory call raised; retain only
  its exception class, never its message or traceback.
- `PREFLIGHT_OR_SETUP_FAILURE`: API validation or isolated setup failed; do not
  interpret this as connection behavior.

The separately authorized v1.0.9 diagnostic,
`gate2c-step02-memory-20260924T124150Z-b5d60fa6`, is preserved as a ninth
quarantined failed identity. It entered exactly one public
`lancedb.connect_async("memory://")` call through `asyncio.run()` and a caller-owned
event loop. It neither returned nor raised an observed Python exception before the
exact 30-second non-experimental timeout cleanup. Its four evidence files and two
runtime artifacts are exact-hash-bound without a retrospective evidence manifest.
This establishes bounded noncompletion with both tested backends in this execution
context; it does not establish a native deadlock, filesystem defect, lost wakeup,
lock contention, or other root cause.

Repair package v1.0.10 restores the accepted Gate 2B memory-storage configuration
that Gate 2C omitted. ADR-0012 and the frozen Gate 2B implementation select the
public CrewAI `set_memory_storage_factory(...)` hook with the existing
`RunScopedMemoryStorage` backend. The Gate 2C worker now imports that exact backend
and registers a fresh instance before every Gate 2C Flow construction. The factory
returns that backend for every string storage specification, so CrewAI's built-in
LanceDB/Qdrant/path selection cannot be reached. Each real Gate 2C worker is a fresh,
dedicated process; the process-wide public hook therefore cannot leak into unrelated
repository operations. Synthetic package tests use an isolated fake registry and
never import CrewAI or LanceDB.

This is a configuration correction, not runtime proof. It does not change
`SQLiteFlowPersistence`, the Flow-state schema, public `save_state`/`load_state`,
same-ID kickoff hydration, target ordering, the target-6 durability seam,
target-7-first recovery, human-review authority, or any frozen experiment constant.
It does not establish that Flow construction or recovery completes.

The separately authorized v1.0.10 startup proof,
`gate2c-step02-startup-20260924T193318Z-dd57cbc4`, is preserved as a tenth
quarantined failed identity. The canonical orchestrator launched
`crewai/agentic_harness_crewai/gate2c_recovery.py` directly by filesystem path, but
that adapter imports the accepted backend through the package-relative
`.canonical_slice` name. Python direct-file execution supplied no package parent, so
the worker raised `ImportError` during `crewai_import_started`, before SQLite
initialization, factory registration, connection tracing, or Flow construction. Its
two evidence files and three runtime artifacts are exact-hash-bound without a
retrospective evidence manifest. This is an invocation-context failure, not evidence
about the accepted backend, Flow construction, or LanceDB behavior.

Repair package v1.0.11 changes only the shared CrewAI worker launch prefix used by
startup, pre-kill, and recovery. It invokes the verified module
`agentic_harness_crewai.gate2c_recovery` through Python's `-m` option while retaining
the repository root as the working directory. A worker-subprocess-only `PYTHONPATH`
is set to the exact repository `crewai/` package root so both the package-
relative backend import and repository-level `shared` imports resolve. The caller's
environment is copied, the inherited import path is not extended, and no global
process environment is mutated. The LanceDB-only diagnostic workers remain direct,
isolated scripts and are unchanged.

Python module execution loads `agentic_harness_crewai/__init__.py` before the worker
module. The package binds that initializer by exact hash and statically verifies that
it contains only the accepted canonical-slice/tool imports and exports: it contains
no call that constructs or invokes a Flow, changes the memory factory, or enters
LanceDB. Run-scoped XDG and credential-isolation values are supplied in the child
environment before the interpreter starts.

The package-aware prefix is resolved before any worker starts and fails closed when
the pinned interpreter, package root, or module source is absent. The public memory
factory, accepted backend, SQLite persistence, Flow state, target-6/7 seam,
authorization guards, exact 30-second timeout, no-retry rule, XDG isolation, cleanup,
and all experiment constants remain unchanged. Static and inert synthetic module
tests do not import CrewAI or LanceDB and do not execute the real recovery adapter.

The separately authorized v1.0.11 offline rehearsal,
`gate2c-step02-offline-20260924T203449Z-1ec8feac`, is preserved as an eleventh
quarantined failed identity. LangGraph passed its synchronous target-6 durability,
actual-worker signal-9 termination, and public target-7-first recovery path. The
CrewAI package import, `SQLiteFlowPersistence` initialization, accepted memory-backed
Flow construction, and kickoff entry completed, but no Flow method or target began
before the exact 30-second seam timeout. Cleanup signal 9 was non-experimental and no
CrewAI recovery worker was launched. Bounded stderr retained repeated failed exports
to `telemetry.crewai.com`; this is a concrete telemetry-configuration defect and a
plausible contributor, not an established cause of kickoff noncompletion.

The failed family originally retained five evidence files and eleven runtime
artifacts. A later preservation inspection opened both retained SQLite databases with
SQLite `mode=ro`; SQLite nevertheless created one 32,768-byte shared-memory sidecar
and one empty WAL sidecar beside each database. Those four files are separately bound
as post-inspection artifacts. They are not at-timeout experimental evidence and do not
alter the failed classification. The corrected physical inventory is twelve families,
thirty-nine evidence files, seventy-one runtime artifacts, and 110 files total. The
previous 106-file report was an inventory-order error: it counted before the SQL-level
inspection and did not recount afterward.

Repair package v1.0.12 adds the eleventh failed-family hashes, the accepted startup
family hashes, and separate size/hash bindings for the four post-inspection sidecars
to the successor audit. Preservation verification uses directory inventory and raw
file bytes only; it neither imports `sqlite3` nor opens retained databases. Synthetic
tamper checks operate on disposable copies and reject missing, modified, or additional
runtime files.

Repair package v1.0.13 creates one source-bound admission slot without changing the
fixed historical baseline. The admission anchor binds the twelve families, thirty-nine
evidence files, sixty-seven original runtime artifacts, four separately classified
post-inspection sidecars, and their canonical 110-file inventory digest. An explicit
authorization command must consume that slot for one fresh offline identity before
any family evidence, runtime directory, or worker is created. The authorization
record is outside the worker-owned family, and the runtime receives its digest in a
pre-launch binding. Identity reuse, a second authorization, an unrelated thirteenth
identity, and automatic replacement or retry all fail closed.

After the authorized attempt, the surviving canonical orchestrator waits for worker
exit and cleanup, verifies that no process retains an open descriptor into the new
evidence or runtime roots, and atomically publishes a separate finalization record.
That record inventories every evidence and runtime file by relative path, size, and
SHA-256, including SQLite databases and any WAL/SHM sidecars present at finalization.
`PASS`, `FAIL`, and `TIMEOUT` are preserved distinctly. A successful outcome must
retain and validate the canonical evidence manifest; failed and timed-out outcomes
must retain `FAILED-ATTEMPT.json` and may not fabricate that success manifest.
Experimental signal-9 records remain separate from non-experimental timeout/failure
cleanup. An interrupted finalization leaves no published finalization record and the
permanent audit rejects the family as incomplete.

The permanent audit independently recomputes the finalized inventories from raw bytes
and does not trust the orchestrator's declaration alone. A later inspection-created
artifact is rejected unless a separately authorized post-inspection addendum binds it
as `POST_INSPECTION_NOT_EXPERIMENTAL_STATE`; the original finalized inventory is never
rewritten. A mechanically passing finalization proves integrity and provenance only.
It is not experimental correctness, human evidence acceptance, CrewAI architecture
approval, or Gate 2C certification.

Repair package v1.0.14 corrects preservation classification only. The v1.0.13
orchestrator classified the outer supervisor command's nonzero exit as an overall
`FAIL`, but the finalizer consulted only that outer command diagnostic for cleanup.
When the supervisor's own fixed 30-second seam wait expired, the supervisor killed
the stalled worker with non-experimental signal 9, retained that fact in
`crewai-startup-diagnostic.json`, and exited 1. The outer command did not itself time
out, so its diagnostic correctly said `timed_out=false` and carried no cleanup
signal; the finalizer consequently and incorrectly emitted
`non_experimental_cleanup.classification=NONE`.

Future finalization independently binds the cleanup source and distinguishes an
outer-process timeout from a handled supervisor-internal timeout. A supervisor
diagnostic that reports cleanup must be hash-bound by `FAILED-ATTEMPT.json`; its
identity, seam status, fixed timeout, experimental/non-experimental flags, observed
signal, and negative worker return code must agree. The finalized cleanup record
then identifies `SUPERVISOR_DIAGNOSTIC` or `OUTER_COMMAND_DIAGNOSTIC`, records both
timeout booleans, and binds the source path and SHA-256. An overall `FAIL` does not
suppress an observed cleanup. Missing or contradictory source evidence fails closed.
Experimental termination remains derived separately from the canonical termination
records and is never inferred from timeout cleanup.

The already finalized family
`gate2c-step02-offline-20260925T154513Z-5420da48` remains byte-for-byte immutable and
retains outcome `FAIL`. The permanent audit admits its old three-field `NONE` value
only as `KNOWN_HISTORICAL_CLASSIFICATION_INCONSISTENCY`, and only when the run ID,
finalization, failure record, and CrewAI diagnostic match their exact source-bound
hashes and the diagnostic still proves supervisor-internal timeout cleanup signal 9.
The exception cannot match another family and cannot establish CrewAI durability,
recovery, human certification, or any Gate 2C claim. Every later family must satisfy
the corrected cross-record classification rule.

This repair does not change either framework adapter, the supervisor, runner,
telemetry environment, memory factory, SQLite persistence, public hydration,
LangGraph checkpoint behavior, deterministic ordering, target-6/target-7 seam,
30-second timeouts, or the one-attempt/no-retry rule. In particular, it neither
diagnoses nor resolves the observed CrewAI kickoff stall.

Governance successor package
`gate-2c-step02-offline-rehearsal-replacement-authorization-v1.0.0` adds one
new, separately consumed replacement admission without reopening the v1.0.13
admission or changing the v1.0.14 execution implementation. Its predecessor is
the exact finalized `FAIL` family
`gate2c-step02-offline-20260925T154513Z-5420da48`, including the immutable
authorization, finalization, failure record, CrewAI supervisor diagnostic, and
the narrowly source-bound `KNOWN_HISTORICAL_CLASSIFICATION_INCONSISTENCY`.

The replacement admission permits exactly one fresh offline run identity. The
authorization record must be created by a separate governance command before
any evidence directory, runtime directory, or worker exists. It records that the
consumed admission remains closed, historical identity reuse is prohibited, no
automatic retry or replacement is authorized, and zero further replacement
identities are available. Any `PASS`, `FAIL`, or `TIMEOUT` result is finalized
and retained under v1.0.14's corrected source-bound cleanup classification; a
failure or timeout does not create another slot.

The complete LangGraph/CrewAI family remains mandatory. Acceptance still
requires independently verified target-6 durability, experimental termination
of each actual worker, public recovery interfaces, target 7 as the first
post-restart work, zero replay, and zero duplicate identities. The governance
successor changes no worker adapter, supervisor, persistence or recovery path,
timeout, failure injection, experiment control, validator, or frozen contract.

The successful auxiliary v1.0.4 kickoff-location diagnostic is bound through
its byte-exact result-preservation manifest. Its source package directory is
not a predecessor: an authorized supervisor import created undeclared
`diagnostic/__pycache__/stack_sanitizer.cpython-312.pyc`, so the directory must
not be represented as passing its closed-world 19-file package self-check. The
package, cache, result, and preserved workspaces remain unchanged.

Pinned CrewAI 1.15.10 and `crewai_core` both test
`CREWAI_DISABLE_TELEMETRY`, `CREWAI_DISABLE_TRACKING`, or `OTEL_SDK_DISABLED` before
constructing the OTLP exporter, and any one value equal to `true` disables their
telemetry singleton. Gate 2C selects the narrow CrewAI-specific control
`CREWAI_DISABLE_TELEMETRY=true`. `crewai_bootstrap_env(...)` places it in the copied
child environment before the package-aware Python process starts. The caller
environment and LangGraph path are unchanged. This controls telemetry only; it does
not change Flow processing, memory, SQLite persistence, target ordering, recovery,
failure injection, or timeout semantics, and it does not prove that kickoff will
complete.

This package implements the external supervisor, model-free framework rehearsal
adapters, evidence validators, and phase-specific authorization guards required by
the certified Gate 2C.01 contract. It does not modify the frozen Gate 1, Gate 2A, or
Gate 2B implementations. It does not claim that any framework recovers from the
authoritative process failure.

The controlling contract remains
`shared/contracts/GATE2C-SHARED-FAILURE-RECOVERY-CONTRACT.json` at SHA-256
`3c4801e6eb35d40d94e066c70017d3acebca95183e7e544646be6e2b40aa5ec6`.

## Exact seam and failure class

The common semantic seam is exactly:

```text
after target 6 is fully persisted and before target 7 begins
```

The supervisor may deliver `SIGKILL` only after it independently validates a
framework-owned midpoint projection and a seam-ready record bound to the same trial,
run, runtime, and actual worker identity. A clean exit, exception, framework
interrupt, killed wrapper, or container termination is not equivalent.

The supervisor owns signal verification, actual-worker identification, sanitized
trigger evidence, signal delivery, and wait-status capture only. It may not persist
framework state, select the next target, recover a framework, suppress replay or
duplicates, write Drupal recommendations, or retry work.

## Phased authorization

The package is deliberately multi-boundary:

1. `install` installs only the previewed source, schemas, plan, runner, and ignored
   disposable-runtime locations. It makes no model/provider call, Drupal write,
   snapshot operation, framework-worker execution, or failure injection.
2. `crewai-startup-diagnostic` requires its own authorization. It may construct a
   Flow under fresh run-scoped XDG storage within the 30-second bound, but may not
   invoke the Flow, persist synthetic target work, deliver an experimental signal,
   exercise recovery, access Drupal, or satisfy the offline evidence contract.
3. `lancedb-async-diagnostic` requires its own authorization. It may make exactly
   one local-only public `lancedb.connect_async()` call in a caller-owned event loop
   within the external 30-second bound. It may not import CrewAI, use synchronous
   connect, retry, fall back, inspect tasks, access Drupal or a provider, or satisfy
   the offline evidence contract.
4. `offline-rehearsal` requires explicit authorization for disposable local
   `SIGKILL`. It exercises the supervisor plus real pinned LangGraph and CrewAI
   persistence surfaces with synthetic target facts and zero Drupal access.
5. `lancedb-memory-async-diagnostic` requires its own authorization. It may make
   exactly one public `lancedb.connect_async("memory://")` call in a fresh process
   and caller-owned event loop within the external 30-second bound. It may not
   import CrewAI, create filesystem storage, use synchronous connect, retry, fall
   back, access Drupal or a provider, or satisfy the offline evidence contract.
6. `drupal-rehearsal` requires the separate Gate 2C.01 ledger authorization for
   model-free Drupal/reset rehearsal. It may use only a dedicated rehearsal state and
   lock namespace, must preserve the 1,800-second policy, and may not clear, shorten,
   delete, bypass, or replace the lock.
7. `record-crewai-decision` is available only after accepted model-free evidence.
   It records an explicit human `APPROVED` or `REJECTED` decision. The machine
   recommendation never becomes the decision automatically.
8. `finalize` requires separate evidence-acceptance authorization. It may certify
   only accepted model-free evidence and the explicit human decision. It performs no
   rehearsal, Drupal, snapshot, model/provider, or failure-injection activity.

Failed attempts are immutable and never reused. A failed or invalid rehearsal stops
without starting a replacement identity.

## Framework mappings

### Drupal AI

The frozen source is bound read-only to the production key/value persistence surface,
the `agentic_harness_drupal_ai.batch` persistent lock, the 1,800-second lease, and
the frozen resume command. The model-free rehearsal uses a dedicated state and lock
namespace so it cannot be mistaken for authoritative Gate 2C behavior. Killing the
actual PHP worker must be proven separately from killing the host `ddev` wrapper.

An immediate lock denial and any later post-natural-expiry invocation remain
separately authorized. Step 2C.02 may prove mechanics; it may not turn a dedicated
rehearsal lock observation into a Drupal recovery result.

### LangGraph

The adapter uses a fresh per-rehearsal `SqliteSaver` database and `thread_id` equal to
the run ID. The real host Python worker uses synchronous checkpoint durability for
the pre-kill graph invocation, persists target 6, enters a boundary node, emits the
seam-ready record, and waits. Before signaling, the supervisor launches a separate
read-only verifier in the pinned LangGraph environment and requires public
`SqliteSaver.get_tuple(...)` to return the committed target-6 state with zero pending
writes. Recovery rebuilds the same graph and invokes the public compiled-graph
surface against the same database/thread. Synthetic target work records order and
identity only; it makes no model or Drupal call.

### CrewAI

Pinned CrewAI 1.15.10 consults its public process-wide memory-storage factory for
every string storage specification before its built-in LanceDB/Qdrant/path
selection. Gate 2B's accepted implementation registers one fresh
`RunScopedMemoryStorage` instance through `set_memory_storage_factory(...)` before
Flow construction. Gate 2C now performs that same registration inside every fresh
worker process before constructing `Gate2CRehearsalFlow`; returning the accepted
backend for every specification prevents silent fallback to `LanceDBStorage`.
Run-scoped `XDG_DATA_HOME`, `XDG_CONFIG_HOME`, and `XDG_CACHE_HOME` bootstrap
isolation and `CREWAI_STORAGE_DIR` removal remain unchanged. That disposable
bootstrap storage remains separate from authoritative `SQLiteFlowPersistence` at
`crewai/state.sqlite`.

The candidate uses a fresh `SQLiteFlowPersistence` database and the same Flow/run
identity. Process one persists `target_finalized` for target 6 and waits at the seam.
Process two first inspects the public `load_state(...)` result and then uses public
`Flow.kickoff(inputs={"id": flow_id})` hydration. Runtime `CheckpointConfig`, private
`_restore_state`, private `_skip_auto_memory`, human-feedback pending/resume, monkey
patching, historical runtime reuse, and manual state editing are prohibited.

Startup phase records use only approved identifiers, run/trial identity, a sequence,
UTC and monotonic timestamps, and an optional exception class name. They contain no
environment dump, payload, credential, model content, hidden reasoning, or raw
traceback. Missing, malformed, oversized, cross-run, or out-of-order phase records
cannot authorize a signal. Timeout cleanup may terminate an unready worker, but that
cleanup is recorded separately and cannot be classified as the contracted
post-seam experimental `SIGKILL`.

The retained diagnostic-only connection phases are
`lancedb_connection_trace_armed`, `lancedb_connect_entered`,
`lancedb_connect_returned_memory_initialization_continues`, and
`lancedb_connect_exception`. A connection entry without return or exception before
timeout proves only that execution remained within that call boundary when cleanup
occurred; it does not establish why. A successful return without the existing Flow
completion marker isolates later memory/Flow construction. After the v1.0.10
correction, a startup diagnostic must complete Flow construction without entering
`lancedb.connect`; any entry fails closed as an unintended fallback. The total
canonical timeout remains exactly 30 seconds and no automatic retry is permitted.

This is an architecture candidate only. It remains
`PENDING_MODEL_FREE_PROOF_AND_HUMAN_DECISION` until the model-free evidence passes
and the user explicitly approves or rejects it.

## Acceptance criteria

The step cannot finalize unless all of the following pass:

- exact predecessor commit, Gate 2C.01 contract/certification, and three framework
  freeze bindings;
- exact eleven protected Gate 2B local-only paths and retained snapshot integrity;
- one actual worker `SIGKILL` per authorized disposable rehearsal, signal 9 wait
  status, and zero automatic retry;
- target-6 midpoint with completed sequences `[1,2,3,4,5,6]`, next target 7, and no
  target-7 work before termination;
- same run/runtime identity across recovery, target 7 first after restart, zero
  target-1-through-6 replay, and zero duplicate synthetic identities;
- zero model generations, provider traffic, Drupal recommendation/source mutation,
  and hidden retry/repair/fallback/learning activity;
- strict privacy checks over retained evidence and payload-aware checks over managed
  source/configuration;
- deterministic negative controls for wrong PID, wrong run/runtime identity,
  incomplete seam, sidecar-only or pending-write checkpoint claims, invalid durable
  checkpoint identity, missing signal-9 proof, replay, duplicate identity, and
  unapproved recovery invocation;
- separately authorized Drupal/reset rehearsal evidence or an explicit stop at that
  boundary;
- a machine CrewAI recommendation kept separate from an explicit human decision;
- lifecycle remains Gate 2C `DEFERRED_UNCLAIMED` and Gate 2 `NOT_COMPLETE`.

## Evidence plan

Rehearsal evidence is sanitized and run-addressed. Expected retained records include
the authorization ledger, supervisor termination proof, framework-specific midpoint
and recovery projections, retry/provider zero-accounting, privacy scan, negative
controls, machine CrewAI recommendation, summary, and complete SHA-256 manifest.

The Drupal/reset rehearsal and the final human decision are distinct evidence
boundaries. The final Step 2C.02 certification binds, rather than rewrites, those
immutable inputs. No Gate 2C trial schema or cross-framework result is populated in
Step 2C.02.

Failed-attempt evidence remains separate from accepted evidence. The successor audit
binds eleven failed identities and the accepted startup identity: thirty-nine evidence
files and sixty-seven original runtime artifacts. The latest failed offline family
contributes five evidence files and eleven original runtime artifacts; its four later
SQLite sidecars are separately size/hash-bound as post-inspection artifacts, bringing
the physical runtime count to seventy-one and the complete retained count to 110.
Failed identities require `FAILED_PRESERVED` classification and cannot satisfy an
accepted evidence contract. The accepted startup family retains its generated
manifest and successful startup status without promotion to recovery evidence.
Successful LangGraph termination/recovery observations remain preserved within failed
offline families without rerun or promotion. No retrospective manifest is created for
a failed family, and future command failures retain only bounded, redacted stderr
diagnostics.
Credential, authorization-header, data-URL, API-key, sensitive payload, and
hidden-reasoning material remain prohibited.

## Exit

Step 2C.02 is complete only after all model-free proofs pass, required Drupal/reset
mechanics are accepted, the CrewAI candidate is explicitly approved or rejected, and
the permanent successor-aware audit accepts the final evidence family. An approved
Step 2C.02 permits only preparation and preview of Step 2C.03; it does not authorize
any live experiment phase.
