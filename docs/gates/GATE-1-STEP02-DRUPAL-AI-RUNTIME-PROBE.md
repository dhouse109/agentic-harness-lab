# Gate 1 Step 1.02 — Pinned Drupal AI Runtime Probe

## Decision boundary

This step proves the supported programmatic path exposed by the installed Drupal 11.4.4, Drupal AI
1.4.5, AI Agents 1.3.2, and OpenAI provider 1.2.3 code. It uses installed-source inspection,
reflection, service-container introspection, and read-only seeded-site checks.

It does not call a provider, create or save an agent definition, install an adapter, create a
recommendation, mutate source content or configuration, change a dependency, implement run state,
or begin Step 1.03.

## Authorized predecessor

- Branch: `main`
- Commit: `10a7f531bff1af8ea93ecbe1e447e98cb4834ac6`
- PR #4 merge commit: `10a7f531bff1af8ea93ecbe1e447e98cb4834ac6`
- Accepted Gate 0.5 evidence: `gate05-step05-20260805T184155Z-50124`
- Gate 0.5 freeze SHA-256: `99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a`
- Accepted Step 1.01 evidence: `gate1-step01-20260805T205448Z-103220`
- Step 1.01 contract SHA-256: `360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6`

## Chosen programmatic path

1. Load `plugin.manager.ai_agents`, whose concrete class is
   `Drupal\ai_agents\PluginManager\AiAgentManager`.
2. Load a repository-owned `ai_agent` configuration entity. The manager merges the entity into
   plugin discovery as `custom_type: config` and `createInstance()` returns
   `Drupal\ai_agents\PluginBase\AiAgentEntityWrapper`.
3. Treat `Drupal\ai_agents\PluginInterfaces\ConfigAiAgentInterface` as the programmatic contract.
   Supply a narrowly constructed `Drupal\ai_agents\Task\Task`, explicit provider, model,
   configuration, runner ID, and allowed functions.
4. Call `determineSolvability()`. For `JOB_SOLVABLE`, read the final response with `solve()`.
   Decode that text as the raw object defined by `drupal-ai-model-output.schema.json`; do not use
   `getStructuredOutput()` as the raw-model-output path.
5. Read framework traces through `getChatHistory()`, `getToolResults()`, and the AI Agents request,
   response, tool-pre, tool-finished, and finished-execution events.

## Context boundary

`Task::setDescription()`, `Task::setComments()`, and `Task::setFiles()` are the installed public
input surface. Later code must construct those values only from one verified shared-operation
result and must keep the image representation runtime-only. It must run as `agent_bot`, pass no
unrelated entities or configuration, and retain no raw Base64 or data URL.

The Step 1.03 function-call adapters are the only allowed bridge to the four certified services.
No adapter may duplicate validation, idempotency, target selection, or persistence logic.

## Tool boundary

Step 1.03 should add exactly four `#[Drupal\ai\Attribute\FunctionCall]` plugins under the Drupal AI
implementation module. Each extends `Drupal\ai\Base\FunctionCallBase`, implements
`Drupal\ai\Service\FunctionCalling\ExecutableFunctionCallInterface`, and delegates to the
corresponding frozen shared service:

| Adapter function | Frozen service boundary |
|---|---|
| `discover_targets` | `agentic_harness_tools.image_review_finder::find()` |
| `get_image_context` | `agentic_harness_tools.image_context_provider::get()` |
| `submit_recommendation` | `agentic_harness_tools.recommendation_submitter::submit()` |
| `get_recommendation_status` | `agentic_harness_tools.recommendation_status_provider::get()` |

The agent configuration `tools` map is the persistent allowlist. `overrideFunctions()` may narrow
that set per invocation. `tool_usage_limits` supports `only_allow` and `force_value`, including
`hide_property`; the constrained definitions are used by both tool-schema normalization and
runtime context validation. `tool_settings.require_usage` supplies the pinned runtime's
required-tool behavior by checking history and looping with a reminder. OpenAI provider 1.2.3 does
not set a provider-level `tool_choice`, so this is not a hard provider-enforced requirement.

## Provider and structured output

The site default for `chat_with_tools` is not an experiment constant and currently points to
`gpt-5.2`. Later code must therefore explicitly:

1. call `ai.provider::createInstance('openai')`;
2. call the returned `Drupal\ai\Plugin\ProviderProxy::setConfiguration(['temperature' => 0.0])`;
3. set the same configuration on the agent for state and trace visibility;
4. call `setAiProvider()`, `setModelName('gpt-4.1-mini-2025-04-14')`, and
   `setAiConfiguration(['temperature' => 0.0])`.

The config entity's `structured_output_schema` must contain the outer `name`, `description`,
`strict`, and `schema` shape accepted by `ChatInput::setChatStructuredJsonSchema()`. Use `strict:
true`; the OpenAI provider maps it to `response_format.type = json_schema`.

The pinned `AiAgentEntityWrapper` does not apply its `aiConfiguration` property to the top-level
provider immediately before `chat()`. Setting configuration directly on the provider proxy is
therefore mandatory; recording the same array on the agent remains necessary for serialization and
trace metadata.

The probe must not call `OpenAiProvider::getConfiguredModels()`: installed source shows that a cache
miss invokes the remote OpenAI models endpoint. It proves only the explicit local model binding and
locally declared temperature support. Remote model availability and account entitlement remain
outside Step 1.02 because proving them would require network access.

## Output, traces, and errors

- Final structured model text: `solve()`, then strict JSON decode and schema validation.
- Normalized messages and model-selected calls: `getChatHistory()` / `ChatMessage::getTools()`.
- Executed tools and readable/structured results: `getToolResults()`,
  `ExecutableFunctionCallInterface::getReadableOutput()`, and, for Step 1.03 adapters,
  `FunctionCallBase::getStructuredOutput()`.
- Per-loop requests and responses: `ai_agents.request`, `ai_agents.response`, and
  `ai_agents.finished_execution` events.
- Tool lifecycle: `ai_agents.tool_pre_executed` and `ai_agents.tool_finished_executed` events.
- Provider errors: `Drupal\ai\Event\AiExceptionEvent` and sanitized Drupal logging.

Provider exceptions are caught by the wrapper and returned to the caller as
`JOB_NOT_SOLVABLE`; the original exception is not returned by `determineSolvability()`. Step 1.04
must attach a narrowly scoped event subscriber/capture path before claiming complete error evidence.
This limitation does not prevent Step 1.03 adapter work.

## Framework-owned state location

Later packages should use the persistent Drupal `keyvalue` service, concrete database backend
`Drupal\Core\KeyValueStore\DatabaseStorage`, with the dedicated collection
`agentic_harness_drupal_ai.run_state` and run ID keys. The stored value will contain canonical
`drupal-ai-run-state.schema.json` data plus the wrapper's `toArray()` dump needed by `fromArray()`.
The implementation must use a run-scoped persistent lock when it begins writing state.

This is a Drupal AI implementation namespace, not shared runtime storage. Step 1.02 only verifies
the factory and storage class; it does not open the proposed collection or write a key. The AI Agents private temp status store
is session-bound, expirable, and skipped in CLI contexts. The artifact store is in-memory. Neither
is suitable for the later restart boundary.

## Rejected alternatives

- Direct `ai.provider::chat()` — bypasses AI Agents execution and lifecycle.
- `ai_agents.agent_helper::runAiProvider()` — lower-level provider helper, not the config-agent
  execution entry point.
- AI Agents Explorer controllers/forms — HTTP/UI and session-oriented, not the batch API.
- Existing code-defined content, field, or taxonomy agents — wrong domain and tool surface.
- Direct OpenAI SDK or an external script — bypasses the pinned Drupal AI stack.
- Private service or entity writes around the shared substrate — violate the frozen boundary.
- `ai_agents.private_temp_status_storage` — private session tempstore, expirable and absent in CLI.
- `ai_agents.artifact_storage` — in-memory only.
- Shared runtime state — prohibited by the Step 1.01 contract.

## Required run evidence

The approved runner must retain source and live-container results, before/after source hashes,
target-order hash, version proof, path and rejection matrices, predecessor-audit logs, sanitized
summary files, and checksum manifests. Before and after it must prove 20 Articles, zero
recommendations, the frozen 12-target order, canonical sequence 1, identical source hashes,
seeded-clean, zero provider request events, and no retained secret or raw image payload.

## Exit

A passing Step 1.02 proves only that the pinned runtime path and extension points were inspected and
can be constructed without execution. It makes no model-call, adapter-implementation, vertical-slice,
recovery, or framework-quality claim. Step 1.03 is the next package; Step 1.03 is not included here.
