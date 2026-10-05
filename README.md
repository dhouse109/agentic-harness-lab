# Agentic Harness Lab

A reproducible comparative engineering lab built for the Drupal GovCon 2026 session:

**Anatomy of an Agentic Harness: Building the Same Agent in Drupal AI, LangChain, and CrewAI**

The lab implements the same governance-sensitive Drupal task three ways and compares the
infrastructure around the model—the **agentic harness**—rather than treating the model as the
whole system.

## Project state

**Engineering and evidence collection are finished.**

The immutable engineering checkpoint is commit
`15e50615f5c525d9c6ed937fe607b3f009898f10`.

The framework-specific implementation gates are complete:

| Implementation | Status |
|---|---|
| Drupal AI | Gate 1 certified and frozen |
| LangChain / LangGraph | Gate 2A certified and frozen |
| CrewAI | Gate 2B certified and frozen |

The shared recovery experiment reached a terminal evidence disposition:

- **Gate 2C:** `CLOSED_NON_CERTIFYING_WITH_INCOMPLETE_EVIDENCE`
- **Step 2C.02:** `TERMINAL_UNCERTIFIED`
- **Gate 2 umbrella:** `NOT_COMPLETE`

That wording is deliberate. LangGraph and CrewAI demonstrated qualified model-free recovery
mechanics. Drupal preserved useful evidence through the target-6/7 failure seam, but the experiment
did not establish the certifying termination and recovery-continuation evidence required for a valid
three-framework recovery comparison.

So the project is best described as **engineering complete / experiment concluded**, not as
"Gate 2 passed."

For the exact terminal disposition, see
[Gate 2C Final Closure and Disposition](docs/gates/GATE-2C-CLOSURE-AND-DISPOSITION.md).

For the boundary between the immutable engineering checkpoint and later documentation/presentation
work, see
[Post-Closure Documentation and Publication Boundary](docs/POST-CLOSURE-PUBLICATION-BOUNDARY.md).

## The shared task

Each implementation processes the same deterministic set of Drupal image-field usages:

> Find Drupal pages with missing or inadequate image alt text, assemble permitted image and page
> context, draft remediation recommendations, validate them, and send them to an editor for review.

The agent creates **recommendation records only**. It never directly changes the source image alt
text and never auto-publishes content.

The frozen experiment uses:

- 20 deterministic Drupal Articles;
- 12 frozen image-field targets;
- the same OpenAI model snapshot;
- temperature `0.0`;
- the same output schema;
- the same deterministic validator;
- the same Drupal review destination;
- the same target-6/7 lifecycle seam.

See [EXPERIMENT_SPEC.md](EXPERIMENT_SPEC.md) for the full contract.

## The six harness organs

The talk and repository organize the comparison around six capabilities every serious agentic system
has to solve:

1. **Context control** — what the model is allowed to see.
2. **Tools and integrations** — which actions the system can invoke and under what boundary.
3. **State and memory** — what persists across steps and process boundaries.
4. **Verification and guardrails** — how outputs and actions are checked before acceptance.
5. **Human review and approval** — where accountable people remain in the workflow.
6. **Lifecycle and recovery** — what happens when work is interrupted or the process fails.

The point is not to crown a framework winner. It is to make those responsibilities visible so
framework choices can be evaluated against the needs of a real system.

## Three implementations

### Drupal AI

Drupal AI uses Drupal itself as much of the harness substrate:

- Drupal content and permission boundaries provide governed source context;
- framework-native FunctionCall adapters delegate to the certified shared operations;
- Drupal key/value state tracks run progress;
- structured output and deterministic validation gate recommendation creation;
- a revision-enabled Drupal queue provides human review and audit lineage.

Gate 1 is independently certified and frozen.

### LangChain / LangGraph

The LangGraph specimen is deliberately code-first:

- LangChain `@tool` wrappers expose the same four shared semantic operations;
- `StateGraph` and `SqliteSaver` own workflow state/checkpointing;
- a persisted `interrupt()` bridges the graph to the authoritative Drupal review queue;
- `Command(resume=...)` continues the same run/thread after a real editor decision.

Gate 2A is independently certified and frozen.

### CrewAI

The CrewAI specimen uses a supported Flow-based architecture:

- CrewAI `BaseTool` adapters wrap the same shared semantic operations;
- Flow state plus `SQLiteFlowPersistence` provide framework-owned persistence;
- the selected human-review path uses persisted `HumanFeedbackPending`,
  `from_pending(...)`, and `resume(...)`;
- Drupal remains the sole authoritative human-review system.

Gate 2B is independently certified and frozen.

## What the comparison actually demonstrated

The evidence is intentionally asymmetric because the implementations are different.

Across the accepted framework runs, all three specimens:

- operated on the same frozen task and target order;
- used the same model/settings and deterministic validation boundary;
- created recommendations in the same Drupal review destination;
- preserved source non-mutation;
- maintained framework-owned state;
- connected to a real human-review path.

For lifecycle/recovery specifically:

- **LangGraph:** the corrected-environment model-free rehearsal terminated the worker at the common
  seam and recovered first at target 7 through target 12 without synthetic replay or duplicate
  identities.
- **CrewAI:** the corrected-environment model-free rehearsal used public Flow persistence/re-entry
  mechanics and recovered first at target 7 through target 12 without synthetic replay or duplicate
  identities; that architecture was explicitly human-approved for the proof.
- **Drupal AI:** the experiment durably reached sequences 1–6, preserved the target-6/7 seam,
  verified the worker identity and SIGKILL command boundary, and later observed unchanged state.
  It did **not** establish the certifying termination/immediate-lock evidence or recovery
  continuation needed to claim Drupal resumed at target 7.

That incomplete result is part of the experiment, not something the repository hides or repairs
after the fact.

## Evidence discipline

Claims are separated by strength:

- **hypothesis** — proposed or expected;
- **observed** — reproduced locally with retained evidence;
- **verified** — paired with the relevant source/runtime support and retained evidence;
- **supported-qualified / partial-evidence** — only the stated narrow conclusion is supported;
- **not-demonstrated / prohibited** — do not present the broader claim.

Start with:

- [CLAIMS_REGISTER.md](CLAIMS_REGISTER.md)
- [COMPARISON_MATRIX.md](COMPARISON_MATRIX.md)
- [docs/CURRENT-STATUS.md](docs/CURRENT-STATUS.md)

The repository does **not** support claims that all three frameworks recovered successfully, that
one framework is inherently more reliable, or that these experiments establish production
readiness.

## Repository map

```text
drupal/                 Drupal project and Drupal AI implementation
langchain/              LangChain / LangGraph implementation
crewai/                 CrewAI implementation
shared/                 Frozen cross-framework contracts, schemas, fixtures, validators
evidence/               Sanitized retained experiment evidence
docs/decisions/         Architecture Decision Records
docs/gates/             Gate contracts, certification, and closure documents
docs/handoffs/          Gate-to-gate engineering handoffs
scripts/                Setup, execution, evidence, and audit tooling
EXPERIMENT_SPEC.md      Frozen comparative experiment contract
CLAIMS_REGISTER.md      Claim status and safe wording
COMPARISON_MATRIX.md    Six-organ evidence comparison
PLAN.md                 Historical implementation plan and current production phase
```

## Shared semantic operations

Every framework works through the same certified Drupal substrate:

```text
find_images_needing_review()
get_image_context(target)
submit_recommendation(recommendation)
get_recommendation_status(recommendation_id)
```

Framework adapters may differ. The business semantics do not.

## Reproducing the historical closure

The final Gate 2C closure audit is hash-bound to the immutable engineering checkpoint. Current
publication-oriented documentation intentionally differs from those historical hashes.

To reproduce the final closure audit, use commit
`15e50615f5c525d9c6ed937fe607b3f009898f10` as described in
[docs/POST-CLOSURE-PUBLICATION-BOUNDARY.md](docs/POST-CLOSURE-PUBLICATION-BOUNDARY.md).

Do not regenerate the historical closure manifest merely to make later documentation pass it.

## Current phase

Runtime experimentation is over. The project is now in **conference-production and publication
mode**:

- map retained evidence to the six organs;
- extract presentation-safe code, diagrams, screenshots, terminal excerpts, and clips;
- build the final talk narrative and slides;
- prepare speaker notes, backup slides, Q&A, and no-demo fallbacks.

If presentation material cannot be supported by retained evidence, change the presentation rather
than reopen the experiment.

## Why this repository exists

AI agent demos tend to emphasize prompts and model output. Production systems live or die on the
less glamorous layers around them: permissions, context assembly, tools, durable state,
verification, human accountability, and recovery.

This lab makes those layers inspectable by holding the task constant and changing the harness.
