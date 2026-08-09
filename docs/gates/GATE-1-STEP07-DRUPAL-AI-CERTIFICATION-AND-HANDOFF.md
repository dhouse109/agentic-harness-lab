# Gate 1 Step 1.07 — Drupal AI Certification, Freeze, and Handoff

## Purpose

Certify the completed Drupal AI Gate 1 implementation without weakening historical evidence or overstating recovery behavior that belongs to the later cross-framework comparison.

## Opening hard gate

Before any fresh model-backed certification run, Step 1.07 performs a compatibility-aware ordered audit of:

1. Gate 0.5 Step 05
2. Gate 1 Step 1.01
3. Gate 1 Step 1.02
4. Gate 1 Step 1.03
5. Gate 1 Step 1.04
6. Gate 1 Step 1.05
7. Gate 1 Step 1.06
8. pinned versions, contracts, schemas, prompts, ADRs, and hashes

Each predecessor assertion is classified as one of:

- **retained-evidence verification** — verify immutable evidence/manifests from the original boundary;
- **meaningful live-state invariant** — verify a property that must still hold in the final repository/runtime;
- **historical-boundary assertion** — preserve and verify that the assertion was true at its original package boundary, but do not require it to remain true after valid successor work.

Historical boundary assertions are never deleted or rewritten merely to make old wrappers pass.

## Known compatibility cases

- Step 1.04/1.05 source auditors contain successor-absence assertions that were meaningful before Step 1.06 existed.
- Step 1.05's wrapper audit requires its historical handoff state: module enabled and 12 pending recommendations.
- Step 1.06 restored the sandbox to module-disabled, zero-suggestion seeded-clean, so that historical Step 1.05 live state is no longer a final invariant.
- Step 1.06's operational wrapper pins exact HEAD/origin/main to its pre-merge boundary. Step 1.07 uses its retained evidence auditor directly instead.

## Frozen certification constants

- Framework: `drupal_ai`
- Provider: `OpenAI`
- Model: `gpt-4.1-mini-2025-04-14`
- Temperature: `0.0`
- Target count: `12`
- Target sequence SHA-256: `1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728`
- Validator: `gate05-validator-1.0.0`
- Review destination: `alt_text_suggestion`
- Source Article mutation: prohibited
- Automatic publication: prohibited
- Installed lifecycle seam: after sequence 6, before sequence 7

The sequence-6/7 seam is retained as an implementation fact. Step 1.07 does not promote it into the later shared process-failure recovery comparison claim.

## Preflight boundary

`preflight` is model-free. It must leave Drupal byte/field equivalent to the accepted seeded-clean state, with 20 Articles, zero recommendations, the custom Drupal AI module disabled, no temporary agent config, and no framework runtime state/artifacts.

## Certification boundary

After explicit preflight approval, `certify`:

1. captures a fresh seeded-clean baseline;
2. creates an exact restoration snapshot;
3. enables the already-built Drupal AI module;
4. runs the existing Step 1.05 model-free runtime preflight;
5. starts a fresh 12-target run using the existing Step 1.05 runtime;
6. crosses the existing controlled sequence-6/7 lifecycle seam and resumes the same run;
7. exports sanitized framework-owned state/evidence;
8. performs a model-free full recommendation replay through the certified submit adapter;
9. performs model-free status reads for all 12 recommendations;
10. confirms source non-mutation;
11. retains a cryptographic/reference link to the accepted Step 1.06 human-review lineage;
12. restores the exact pre-certification snapshot;
13. re-audits zero suggestions and the exact Article baselines;
14. generates the Gate 1 freeze manifest, certification document, and LangGraph handoff;
15. advances status/claims/matrix only after all checks pass.

## Safe completion statement

The pinned Drupal AI implementation processed the frozen 12-target dataset through a real model-backed batch, created exactly 12 schema-valid and validator-approved pending recommendations through the certified shared substrate, preserved framework origin and run state, routed recommendations into Drupal revisioned human review, produced no duplicate recommendations on replay, and did not mutate source Articles. Deliberate process-failure recovery remains to be tested in the later shared comparison phase.

## Gate 1 does not prove

- production readiness;
- accessibility quality of every generated alt text;
- autonomous publishing safety;
- recovery behavior under the later shared injected-failure comparison;
- superiority over LangGraph or CrewAI;
- cost, speed, or token efficiency;
- general security quality beyond the tested boundaries.
