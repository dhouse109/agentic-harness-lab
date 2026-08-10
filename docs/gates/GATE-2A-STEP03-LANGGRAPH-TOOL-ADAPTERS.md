# Gate 2A Step 2A.03 — LangGraph Tool Adapters

**Package:** `gate-2a-step03-langgraph-tool-adapters-v1.0.0`
**Expected predecessor:** `096c790ba1d87d960c6a99bd383e034c6d70e3e2`
**Accepted Step 2A.02 evidence:** `gate2a-step02-20260809T224238Z-2361786`
**Gate 1 freeze:** `2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd`
**Gate 2A contract:** `1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b`

## Purpose

Implement and directly exercise the four frozen shared semantic operations as thin,
LangChain-native `@tool` wrappers for the LangGraph implementation.

This step proves the **tool organ only**. It does not bind tools to a model, compile a
LangGraph workflow, open framework checkpoint state, invoke OpenAI, or begin the canonical
vertical slice.

## Exact adapter surface

| LangChain tool name | Input | Delegation |
|---|---|---|
| `find_images_needing_review` | none | `shared.drupal_client.DrupalClient.find_images_needing_review()` |
| `get_image_context` | `target` object | `DrupalClient.get_image_context()` |
| `submit_recommendation` | `recommendation` object | `DrupalClient.submit_recommendation()` |
| `get_recommendation_status` | `recommendation_id` string | `DrupalClient.get_recommendation_status()` |

The wrappers return the shared Drupal tool-result envelope unchanged. They must not duplicate
validation, target lookup, persistence, status projection, retry policy, sequencing, or permission
logic.

## Runtime boundary

The approved live proof is model-free and uses only the local DDEV Drupal site.

The run:

1. passes Gate 0.5, Gate 1, Step 2A.02, frozen-hash, and seeded-clean preflight checks;
2. creates an exact named DDEV snapshot;
3. constructs the four `@tool` wrappers around the frozen shared client;
4. invokes discovery and selects canonical target sequence 1;
5. invokes image context while keeping the raw image representation in process memory only;
6. assembles one deterministic **test** recommendation with `source_framework=langgraph`;
7. invokes submission twice with the same idempotency identity and requires the same result;
8. invokes recommendation status and requires `pending`;
9. restores the exact DDEV snapshot and proves seeded-clean again;
10. retains only sanitized adapter/tool evidence.

The deterministic test alt text is evidence plumbing, not a model output and not an accessibility
quality claim.

## Frozen boundaries

- Model/provider calls: **0**.
- Dependency changes: **0**.
- LangGraph checkpoint/state proof: **not opened in this step**.
- Source Article/image-field mutation: prohibited.
- Automatic publication: prohibited.
- Review destination: `alt_text_suggestion`.
- Shared target-order SHA-256: `1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728`.
- Runtime write: one temporary recommendation record plus same-identity replay, restored afterward.
- Raw Base64/data URL retention: prohibited.
- Credentials/auth-header retention: prohibited.
- Hidden reasoning retention: prohibited.

## Evidence

Passing evidence is retained under:

```text
evidence/gates/gate-2a/tool-adapters/<run-id>/
```

The accepted run records tool metadata, targets, a sanitized context summary, submission/status
facts, predecessor audits, before/after seeded-clean audits, source/file hashes, and a checksum
manifest.

A failed live adapter run is retained as failed evidence and must not be silently rerun.

## Exit criteria

Step 2A.03 passes only when:

- all four exact native LangChain tools construct and invoke;
- static fake-client proof shows one-to-one pass-through delegation with no data reshaping;
- live discovery returns the frozen 12-target surface;
- live context is retrieved through the wrapper without retaining its representation value;
- deterministic test recommendation submission succeeds;
- same-identity replay is idempotent;
- status through the wrapper is `pending`;
- DDEV snapshot restore returns the sandbox to seeded-clean;
- Gate 1 and Gate 2A frozen digests remain unchanged;
- no model/provider call or dependency change occurs;
- retained evidence passes secret/raw-image scanning;
- next package is exactly
  `gate-2a-step04-langgraph-state-and-sqlite-checkpoint-proof-v1.0.0`.

A passing Step 2A.03 proves the model-free LangGraph **tool-adapter boundary only**. It does not
prove graph orchestration, checkpointing, model output, human interrupt/resume, batch execution,
continuation, recovery, framework superiority, or production readiness.


## v1.0.2 compliance verification supplement

The accepted v1.0.0 live run remains immutable and is **not rerun**. Final staged review found that
the original retained evidence did not explicitly prove every Step 2A.03 property in the approved
Gate 2A execution plan.

Before Step 2A.03 may be committed as complete, v1.0.2 must additionally prove, model-free and
without a successful recommendation write:

- every exercised result validates against the frozen Draft 2020-12 `tool-result.schema.json`;
- the caller-supplied correlation ID is preserved exactly;
- safe structured substrate error envelopes pass through unchanged;
- route/transport failures are converted to sanitized tool-result error envelopes without retaining
  response bodies, credentials, or authorization headers;
- `agent_bot` can reach all four intended shared routes;
- `editor_dana` is denied at all four agent-tool routes;
- an invalid recommendation submission creates no recommendation;
- Drupal source/recommendation state is identical before and after the supplement;
- the accepted v1.0.0 live run and its checksum manifest remain unchanged.

Supplemental evidence is retained in a separate
`evidence/gates/gate-2a/tool-adapters/gate2a-step03-verification-<run-id>/` directory. This repair
does not open LangGraph checkpoint state or begin Step 2A.04.
## v1.0.3 compliance-runner interpreter repair

The first v1.0.2 supplemental verification attempt is retained as failed evidence at
`evidence/gates/gate-2a/tool-adapters/gate2a-step03-verification-20260810T015510Z-2408431`.

Observed failure: the verifier called `Path.resolve()` on the configured
`crewai/.venv/bin/python` validator executable. Because the virtualenv executable is a
symlink, resolving it selected the base interpreter and lost the CrewAI environment's
`jsonschema==4.26.0` installation.

v1.0.3:

- preserves the configured virtualenv executable path instead of resolving the symlink;
- adds a no-network schema/interpreter smoke test before credentials are loaded or any
  compliance HTTP request is made;
- preserves the failed v1.0.2 evidence and the accepted v1.0.0 live run unchanged;
- makes no model/provider call, Drupal mutation, dependency change, or checkpoint change
  during package installation.

This is verification-infrastructure repair only; Step 2A.04 remains locked.
