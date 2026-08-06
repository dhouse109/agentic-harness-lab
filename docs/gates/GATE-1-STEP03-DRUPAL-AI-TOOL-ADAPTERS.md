# Gate 1 Step 1.03 — Drupal AI FunctionCall Tool Adapters

## Decision boundary

This step implements and directly exercises four thin Drupal AI `FunctionCall` plugins around the
already certified shared operations. It proves plugin discovery, container construction, input
mapping, direct service delegation, shared tool-result envelope mapping, permission preservation,
deterministic sanitized errors, and model-free execution.

It does not create an AI Agent configuration entity, call `determineSolvability()`, call `solve()`,
invoke a provider, open runtime-state storage, contact a network endpoint, or begin Step 1.04.

## Authorized predecessor

- Branch: `main`
- Commit and PR #6 merge commit: `3915af75779869e19c40abf3cbb4e2021cc57952`
- Accepted Gate 0.5 evidence: `gate05-step05-20260805T184155Z-50124`
- Gate 0.5 freeze SHA-256: `99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a`
- Accepted Step 1.01 evidence: `gate1-step01-20260805T205448Z-103220`
- Step 1.01 contract SHA-256: `360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6`
- Accepted Step 1.02 evidence: `gate1-step02-20260806T010227Z-189538`
- ADR-0006 SHA-256: `223f6d6f4276d3861cf5668f08e0446479d815a07fed18402b1e6a7722d18c4b`
- Accepted Step 1.01 audit compatibility evidence:
  `gate1-step01-audit-compatibility-20260806T023356Z-250843`

## Installed extension point

The pinned Drupal AI 1.4.5 source provides:

```text
Attribute    Drupal\ai\Attribute\FunctionCall
Base         Drupal\ai\Base\FunctionCallBase
Interface    Drupal\ai\Service\FunctionCalling\ExecutableFunctionCallInterface
Manager      plugin.manager.ai.function_calls
Construction FunctionCallPluginManager::createInstance() through
             FunctionCallBase's ContainerFactoryPluginInterface contract
```

Every adapter overrides `create()` and injects both base-class services, the current account, the
one certified service it delegates to, and the shared envelope runner. No adapter calls
`\Drupal::service()` or another global service locator.

The installed attribute warns that a plugin ID must equal its group or use the group as a prefix.
The required exact IDs are preserved by setting each plugin's group equal to its exact ID.

The enabled dependency machine names verified before authoring the module info file are `ai`,
`ai_agents`, and `agentic_harness_tools`. Composer manifests and lockfiles remain unchanged.

## Exact adapter map

| Plugin ID and function name | Business input | Direct delegation | Frozen envelope tool name |
|---|---|---|---|
| `discover_targets` | none | `agentic_harness_tools.image_review_finder::find()` | `find_images_needing_review` |
| `get_image_context` | one `target` object | `agentic_harness_tools.image_context_provider::get(array $target)` | `get_image_context` |
| `submit_recommendation` | one `recommendation` object | `agentic_harness_tools.recommendation_submitter::submit(array $recommendation)` | `submit_recommendation` |
| `get_recommendation_status` | one positive node ID or UUID string | `agentic_harness_tools.recommendation_status_provider::get(string $identifier)` | `get_recommendation_status` |

Object parameters are normalized as one outer object property. Exact field validation, unexpected
property rejection, stale-target checks, deterministic recommendation validation, idempotency,
sorting, persistence, and status projection remain exclusively in the certified shared services.

## Permission boundary

The direct adapters preserve the permissions that guard the certified HTTP boundary:

- discovery, context, and status require `use agentic harness discovery tools`;
- submission requires `create alt_text_suggestion content`;
- the shared services continue to perform their own entity and field access checks under the
  current account.

The exercise switches only among `agent_bot`, anonymous, and `editor_dana`. It never substitutes an
administrative account. All four successful operations run as `agent_bot`; anonymous and
`editor_dana` are denied before direct delegation.

## Output and error boundary

`ToolResultRunner` adds only the frozen envelope fields around direct service data. The discovery
adapter maps its ID to the frozen `find_images_needing_review` tool name. The context adapter places
the direct image-context object at `data`; it does not introduce `data.context`.

The runner preserves the code, safe message, and retryable flag from the three certified shared
exception types. Permission failures map to `ACCESS_DENIED`. Unknown exceptions map by operation to
the same safe deterministic generic codes used at the HTTP boundary and do not expose exception
messages, stack traces, SQL, paths, credentials, or service configuration.

Raw image representation exists only in process and pipe memory. The capture process validates the
complete context result against the Draft 2020-12 shared schemas before retaining only metadata,
representation kind, byte/hash facts, and an explicit `representation_value_retained: false` fact.

## Approved-run proof

### Article-source hash compatibility

The controlling Article-source integrity metric is the accepted Step 1.02 projection and SHA-256:
`f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17`. It hashes all 20
Articles in node-ID query order using `node_uuid`, `revision_id`, `title`, `status`, and `images`;
each image contains `delta`, `file_uuid`, `alt`, and `title`. Associative keys are recursively
sorted, list order is preserved, and JSON uses `JSON_UNESCAPED_SLASHES`,
`JSON_UNESCAPED_UNICODE`, and `JSON_THROW_ON_ERROR`.

The original Step 1.03 projection produced
`ecef88e5f60714319e46ec2061e7022f9e5a984b4e96f39c97917c6e927ecf66` because it added the
numeric node ID, scalar body value, and numeric file target ID, renamed `node_uuid` to `uuid`, and
omitted `status`. That projection may be retained only as
`step03_extended_article_source_sha256`; it is not the predecessor integrity metric. The capture,
runner, audit, and finalizer fail unless the controlling Step 1.02-compatible hash is exact. The
retained reconciliation includes only schemas, sizes, aggregate hashes, and safe per-record hashes;
it excludes Article body content.

The runner must:

1. pass Gate 0.5, Step 1.01, Step 1.02, and Step 1.01 compatibility audits;
2. prove seeded-clean, 20 Articles, zero recommendations, 12 targets, canonical sequence 1, the
   frozen target-order hash, and the Article-source hash before execution;
3. create an exact named DDEV database snapshot while the new module remains disabled;
4. enable only `agentic_harness_drupal_ai`, rebuild discovery, and directly instantiate and execute
   the four adapters;
5. validate plugin definitions, normalized inputs, shared envelopes, all negative controls,
   permission denial, direct data shape, deterministic fixture submission, same-identity replay,
   pending status, and source non-mutation;
6. stream the raw context result directly into the locked Draft 2020-12 validator and sanitizer so
   no raw representation reaches retained evidence;
7. restore the exact database snapshot even on failure, rebuild caches, remove the named snapshot,
   and prove the module is again disabled;
8. prove seeded-clean and the complete before/after state again, including zero recommendations,
   identical target and Article hashes, no provider event, and no retained sensitive material.

Only after all checks pass may the runner create accepted Step 1.03 evidence and advance status
documents to name exactly `gate-1-step04-drupal-ai-canonical-vertical-slice-v1.0.0`.

## Prohibited implementation paths

The installed adapter source and runner are audited to reject direct entity query/write code in an
adapter, HTTP routes or web-server loopback, provider chat, `determineSolvability()`, `solve()`, AI
Agent configuration creation, runtime-state storage, curl/wget, dependency changes, contributed
source changes, source Article mutation, alternate recommendation persistence, and Step 1.04 work.

## Exit

A passing Step 1.03 proves only the model-free four-adapter boundary on the pinned local runtime. It
does not prove agent orchestration, model output, provider behavior, the canonical vertical slice,
batch execution, recovery, framework quality, or production readiness.

The next package after a passing committed result is exactly:

```text
gate-1-step04-drupal-ai-canonical-vertical-slice-v1.0.0
```
