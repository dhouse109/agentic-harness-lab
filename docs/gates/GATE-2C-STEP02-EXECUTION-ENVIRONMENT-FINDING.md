# Gate 2C Step 2C.02 — Execution-Environment Finding

## Subsequent execution-environment finding — September 30, 2026

The retained Step 2C.02 rehearsal FAIL families and focused diagnostic
classifications remain immutable historical observations.

In the original restricted execution environment, CrewAI completed Flow
construction and reached public kickoff but did not progress to the representative
`flow_method_started` reporter.

Subsequent model-free diagnostics showed that a CrewAI-independent CPython
`loop.call_soon_threadsafe()` control could return without executing its scheduled
event-loop callback in that restricted environment.

The equivalent CPython wakeup and Unix socketpair controls passed in ordinary WSL
and in Codex launched with `--sandbox danger-full-access`, where the tested process
reported `Seccomp: 0` and `NoNewPrivs: 0`.

A subsequent corrected-environment representative CrewAI startup verification then
passed using normal installed import order, one public kickoff, no tracing or
trace-specific pre-imports, and the real installed `flow_method_started` reporter.

Therefore, the historical result remains that CrewAI failed to progress in the
tested restricted environment. It must not be interpreted as evidence that the
candidate CrewAI recovery architecture is defective.

The candidate architecture remains
`PENDING_MODEL_FREE_PROOF_AND_HUMAN_DECISION` until the complete target-6
termination/recovery rehearsal passes in the corrected execution environment.

No historical classification, evidence file, manifest, or immutable result is
changed by this addendum.

The corrected-environment representative result proves representative startup
only. It does not prove target-6 durability, experimental termination, recovery at
target 7, replay exclusion, duplicate exclusion, or completion through target 12.
