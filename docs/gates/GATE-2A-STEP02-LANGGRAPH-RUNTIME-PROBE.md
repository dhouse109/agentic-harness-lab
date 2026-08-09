# Gate 2A Step 2A.02 — Pinned LangGraph Runtime and Checkpoint Capability Probe

**Package:** `gate-2a-step02-langgraph-runtime-and-checkpoint-probe-v1.0.4`
**Expected predecessor:** `c48c49c53bcf11b33db7f62aedc06dbcbb85d045`
**Gate 2A contract:** `1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b`

## Purpose

Resolve the implementation path from the **installed pinned environment**, not from examples targeting other releases.

This step is model-free and Drupal-mutation-free. It may create synthetic LangGraph SQLite checkpoint state only under the gitignored `langchain/.gate2a-runtime/` root.

## Questions this step must answer

1. Exact `StateGraph` compile/invoke path in LangGraph `1.2.10`.
2. Exact SQLite checkpointer API in `langgraph-checkpoint-sqlite 3.1.1`.
3. Thread/run identity and checkpoint namespace behavior.
4. Pinned interrupt/resume API.
5. State serialization boundary and prohibited persisted fields.
6. `ChatOpenAI.with_structured_output(..., strict=True)` support without making a model call.
7. Pinned image-message representation.
8. Transport retry default and whether explicit `max_retries=0` is supported.
9. Whether thin LangChain-native `@tool` wrappers can be invoked deterministically.
10. Narrowest graph architecture that keeps write decisions deterministic.

## Runtime path under test

```text
langchain/.gate2a-runtime/
```

This path is framework-owned and gitignored. The probe uses synthetic state only. Step 2A.04 remains the stronger cross-process state/checkpoint proof.

## Evidence

```text
evidence/gates/gate-2a/runtime-probe/<run-id>/
  environment.json
  imports-and-versions.txt
  installed-source-map.md
  checkpointer-probe.json
  interrupt-api-probe.json
  structured-output-api.json
  retry-policy.json
  architecture-decision.json
  summary.json
  summary.md
  predecessor-audits.log
  package-files-sha256.txt
```

## Pass criteria

- installed pinned APIs identified with no dependency changes;
- deterministic model-free graph runs;
- synthetic SQLite checkpoint creation and reload succeeds;
- synthetic interrupt/resume succeeds;
- persisted-state design excludes raw image bytes/data URLs/credentials;
- strict structured-output path is identified without a model request;
- image message shape is identified without retaining image bytes;
- transport retries can be explicitly configured to zero, or the inability is recorded as a stop condition;
- thin `@tool` wrapper path works model-free;
- ADR-0010 records the observed runtime/checkpoint architecture;
- zero model calls and zero Drupal mutation.

## Stop condition

If the pinned packages require an upgrade, undocumented patch, shared runtime storage, or unsafe persisted fields to achieve required continuation behavior, do not advance to 2A.03.
