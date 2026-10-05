# Agent / Codex Operating Instructions

## Current operating mode

This repository has completed its engineering and evidence-collection phase.

Immutable engineering checkpoint:

```text
15e50615f5c525d9c6ed937fe607b3f009898f10
Close Gate 2C with terminal non-certifying evidence
```

Current terminal status:

- Gate 1 / Drupal AI: certified and frozen.
- Gate 2A / LangGraph: certified and frozen.
- Gate 2B / CrewAI: certified and frozen.
- Gate 2C: `CLOSED_NON_CERTIFYING_WITH_INCOMPLETE_EVIDENCE`.
- Step 2C.02: `TERMINAL_UNCERTIFIED`.
- Gate 2: `NOT_COMPLETE`.
- No further Gate 2C runtime is authorized.

The active mode is now **documentation, evidence interpretation, conference production, and
publication**.

## Authoritative reading order

Before changing current documentation or producing presentation material, read:

1. `docs/CURRENT-STATUS.md`
2. `README.md`
3. `docs/POST-CLOSURE-PUBLICATION-BOUNDARY.md`
4. `EXPERIMENT_SPEC.md`
5. `CLAIMS_REGISTER.md`
6. `COMPARISON_MATRIX.md`
7. `docs/gates/GATE-2C-CLOSURE-AND-DISPOSITION.md`
8. the relevant certification/freeze documents for the framework being discussed
9. retained evidence supporting the exact claim or visual

When evidence sources disagree, do not silently reconcile them. Report the conflict and use the
narrowest claim supported by the authoritative retained evidence.

## Historical closure audit boundary

The final Gate 2C closure audit is hash-bound to the engineering checkpoint.

Post-closure documentation edits intentionally change some files that were included in that
historical source manifest. Do not update the historical manifest or closure contract merely to make
current prose pass the old audit.

To reproduce the final closure audit, use a detached checkout/worktree at commit
`15e50615f5c525d9c6ed937fe607b3f009898f10` as documented in
`docs/POST-CLOSURE-PUBLICATION-BOUNDARY.md`.

## Allowed work

Agents may:

- improve current explanatory documentation;
- maintain repository navigation;
- summarize retained evidence;
- create evidence-to-slide maps;
- select and quote short presentation-safe code excerpts;
- identify terminal/screenshot/video evidence for slides;
- draft diagrams based on retained architecture;
- draft slide content, speaker notes, transitions, backup slides, and Q&A;
- prepare rehearsal/fallback material;
- make documentation-only corrections that do not alter experiment facts;
- create new publication or conference-production docs.

## Runtime and evidence prohibition

Do not:

- execute a new Gate 2C worker;
- allocate a replacement identity;
- retry the Drupal failure/recovery path;
- reconstruct the missed immediate observation;
- execute another post-expiry observation;
- reset the terminal Drupal experiment;
- certify Step 2C.02;
- create new Gate 2C evidence identities or pointers;
- mutate historical evidence;
- rewrite frozen Gate 1, Gate 2A, or Gate 2B evidence;
- rerun valid model evidence only to obtain prettier output;
- make current docs claim that Gate 2C passed or Gate 2 completed.

A new runtime experiment requires an explicit new experiment/governance boundary. Do not infer
authorization from a documentation or presentation request.

## Claim discipline

Use the status vocabulary in `CLAIMS_REGISTER.md`.

Prefer:

- "In this pinned implementation…"
- "The retained evidence shows…"
- "The model-free rehearsal demonstrated…"
- "Supported with qualification…"
- "Not demonstrated…"

Never upgrade a claim because it makes a slide cleaner.

Especially prohibited unless a new evidence boundary exists:

- "all three recovered";
- "Drupal recovered from target 7";
- "Drupal avoided replay after restart";
- "Gate 2C passed";
- "Gate 2 is complete";
- "framework X is more reliable";
- "production ready";
- unmeasured claims about quality, cost, speed, safety, or security.

## Presentation-production rule

If desired presentation material cannot be supported by current evidence:

1. soften the claim;
2. use a different visual;
3. move the material to a clearly qualified backup slide; or
4. omit it.

Do **not** reopen the historical experiment merely for presentation convenience.

## Repository mutation rules

For post-closure documentation work:

- use a dedicated documentation/publication branch;
- keep evidence, frozen contracts, closure contracts, and audit code unchanged unless the user
  explicitly authorizes a new governance action;
- keep commits narrowly scoped and descriptive;
- review diffs before merge;
- preserve the engineering checkpoint in Git history;
- do not force-update `main`.

For code or runtime requests that go beyond documentation/presentation work, stop and determine
whether the request creates a new experiment boundary before making changes.

## Historical engineering instructions

Older gate documents, Codex runbooks, package scripts, and handoffs remain intentionally preserved.
They describe how the experiment was executed and audited.

Do not treat historical lines such as "next package" or "Gate 2B is active" as the current work
queue. Current status is controlled by `docs/CURRENT-STATUS.md`.

## Privacy

Never expose or retain:

- API keys;
- Basic Auth credentials or authorization headers;
- raw Base64 image data/data URLs;
- private database exports;
- hidden model reasoning or chain of thought;
- unrelated private configuration or user data.

Presentation artifacts should use already-sanitized retained evidence wherever possible.
