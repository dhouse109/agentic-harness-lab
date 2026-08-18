# Gate 2B Step 2B.03 — CrewAI Shared-Operation Adapters

## Status

This step is installed but remains incomplete until its unique model-free evidence run passes the permanent audit. Step 2B.02 is complete, merged at `e11746138c77f03b71a93a52ce69d199e71f697f`, locally resynchronized, and post-merge audited.

## Purpose and claim boundary

Step 2B.03 implements the smallest supported CrewAI-facing layer over the certified shared Drupal operations. It may prove only that four deterministic CrewAI tools exist, preserve shared-operation ownership, invoke no model or persistence lifecycle, introduce no retry/business-logic layer, and propagate deterministic failures after one shared-boundary call.

It does not prove a model call, one-call inference budget, recommendation quality, canonical vertical slice, live Drupal submission, Drupal human review, pending/resume continuation, 12-target batch, Gate 2C recovery, production readiness, or framework superiority.

## Frozen operation boundary

The CrewAI-visible semantic signatures are:

```text
find_images_needing_review() -> dict[str, Any]
get_image_context(target: dict[str, Any]) -> dict[str, Any]
submit_recommendation(recommendation: dict[str, Any]) -> dict[str, Any]
get_recommendation_status(recommendation_id: str) -> dict[str, Any]
```

The live certified client adds transport correlation metadata:

```text
DrupalClient.find_images_needing_review(self, correlation_id: str) -> dict[str, Any]
DrupalClient.get_image_context(self, target: dict[str, Any], correlation_id: str) -> dict[str, Any]
DrupalClient.submit_recommendation(self, recommendation: dict[str, Any], correlation_id: str) -> dict[str, Any]
DrupalClient.get_recommendation_status(self, recommendation_id: str, correlation_id: str) -> dict[str, Any]
```

`build_tools(client, correlation_id=...)` binds the correlation ID. Each tool performs one direct call and returns the shared response envelope unchanged. Discovery, permission-scoped context, deterministic validation, idempotency, Drupal persistence, and read-only status observation remain owned by the shared substrate. The adapter contains no validation, retry, exception conversion, HTTP client, Drupal route, model, Flow, or persistence implementation.

## Pinned CrewAI surface

Pinned Python is `3.12.13`; `crewai` and `crewai-tools` are both `1.15.10`. The public `crewai.tools` package exports `tool` and `BaseTool`. The selected `@tool` decorator infers the public Pydantic argument schema from the deterministic function signature and returns a public CrewAI `Tool`. Direct `Tool.run(...)` validation invokes the wrapped function without an adapter-owned retry or exception-conversion layer.

Pinned installed-source provenance inspected before package creation:

| Source | SHA-256 |
|---|---|
| `crewai/tools/__init__.py` | `fda33a70254e62fc6443fb4f2559ed904ef5059c84b7ca2bc8c3933b94ce0551` |
| `crewai/tools/base_tool.py` | `5f2b8f7116a283e65403e84430819bd4d74d73e51187202a705603d6b1354abe` |
| `crewai/tools/structured_tool.py` | `c56dbf91a047924abc1b6c1a8ca2d324b50cb89eafaf71b8e453474ec3455c3f` |

This is a supported implementation detail within ADR-0012, not a new material architecture decision. The selected Flow/persistence/human-feedback lifecycle remains deliberately outside this adapter proof.

## Model-free proof

The runner constructs the four public tools against a non-mutating recording fake with the same four shared-client methods. It verifies explicit schemas, exact operation mapping, one call per invocation, correlation binding, response object identity, and exception type/message propagation. Submission uses only the fake and never constructs a live `DrupalClient`.

Socket connection entry points are denied before CrewAI imports and remain denied through all tool construction and invocation. Static inspection rejects adapter loops, exception handlers, private/runtime orchestration APIs, model/network imports, and any second write surface.

## Authorization

The evidence must retain zero for model calls, provider calls, successful outbound network connections, outbound network attempts, Drupal mutations, source-content mutations, authoritative human-review actions, dependency changes, live recommendation submissions, Gate 2C executions, Flow initializations, and persistence initializations.

## Evidence set

Each attempt receives a unique `gate2b-step03-<UTC>-<random>` directory. Failed attempts remain retained and are never overwritten. Only a passing run may update `LATEST`.

The exact run-local set is:

1. `adapter-inventory.json`
2. `authorization.json`
3. `delegation-proof.json`
4. `failure-propagation.json`
5. `pinned-source-provenance.json`
6. `predecessor.json`
7. `privacy-scan.json`
8. `proof-log.txt`
9. `summary.json`
10. `summary.md`
11. `evidence-manifest.json`

The manifest hashes every other intended file. The permanent audit verifies the exact file set, every manifest digest, the summary schema, the public API provenance, four adapter names and schemas, one-shot delegation, failure propagation, safety counts, privacy status, predecessor ancestry, contract digest, and unchanged lock digest.

## Lifecycle

Installation marks Step 2B.03 active without fabricating evidence. The installed runner creates one model-free evidence attempt and advances the lifecycle only after that proof passes. Permanent audit mode accepts legitimate feature commits, normal-merge descendants, and later descendants by requiring the merged Step 2B.02 predecessor as an ancestor rather than requiring `HEAD` to equal the predecessor.

No later Gate 2B package is named or begun by this boundary. Gate 2C remains deferred and unclaimed.
