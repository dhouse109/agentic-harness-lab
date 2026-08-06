# ADR-0006: Select the pinned Drupal AI programmatic runtime path

- **Status:** Accepted for packaging; effective only with passing Step 1.02 retained evidence
- **Decision date:** 2026-08-05
- **Decision owner:** Program lead
- **Related evidence:** `evidence/gates/gate-1/drupal-ai-runtime-probe/`
- **Predecessor:** Gate 1 Step 1.01 contract digest
  `360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6`

## Context

Gate 1 needs an installed-version decision before thin adapters or a vertical slice are built. The
decision must come from Drupal 11.4.4, Drupal AI 1.4.5, AI Agents 1.3.2, and OpenAI provider 1.2.3,
not assumptions based on later documentation. The probe must be executable without contacting a
provider or changing Drupal state.

## Decision

Use the `plugin.manager.ai_agents` service
(`Drupal\ai_agents\PluginManager\AiAgentManager`) to discover and instantiate a repository-owned
`ai_agent` config entity (`Drupal\ai_agents\Entity\AiAgent`). For a config definition,
`AiAgentManager::createInstance()` returns
`Drupal\ai_agents\PluginBase\AiAgentEntityWrapper`, implementing
`Drupal\ai_agents\PluginInterfaces\ConfigAiAgentInterface`.

Construct a minimal `Drupal\ai_agents\Task\Task`, explicitly bind the provider/model/configuration,
apply an exact function allowlist and parameter restrictions, then use
`AiAgentInterface::determineSolvability()` as the execution entry point. When it returns
`JOB_SOLVABLE`, use `AiAgentInterface::solve()` to obtain the final text. Strictly decode and
validate that text against `shared/schemas/drupal-ai-model-output.schema.json`.

Do not use `getStructuredOutput()` for raw model output. In this pinned wrapper it returns a
`StructuredResultData` object describing created, edited, or deleted Drupal objects.

## Context and tools

Permitted context enters through `Task::setDescription()`, `Task::setComments()`, and
`Task::setFiles()`. It must be assembled from exactly one permission-checked shared-operation
result under `agent_bot`; raw image representation remains runtime-only.

Step 1.03 will implement four thin `#[Drupal\ai\Attribute\FunctionCall]` plugins extending
`Drupal\ai\Base\FunctionCallBase` and implementing
`Drupal\ai\Service\FunctionCalling\ExecutableFunctionCallInterface`: `discover_targets`,
`get_image_context`, `submit_recommendation`, and `get_recommendation_status`. Each delegates to
the corresponding existing `agentic_harness_tools` service and may format only its own framework
input/output envelope.

The config entity's `tools` map is the persistent allowlist. `AiAgentEntityWrapper::overrideFunctions()`
may narrow it per run. `tool_usage_limits` supplies `only_allow`, `force_value`, and
`hide_property`; `tool_settings.require_usage` supplies AI Agents' loop-and-reminder requirement.
The pinned OpenAI provider does not expose a hard `tool_choice` through this wrapper.

## Provider and model

Create `openai` through `ai.provider` (`Drupal\ai\AiProviderPluginManager`), yielding
`Drupal\ai\Plugin\ProviderProxy` around
`Drupal\ai_provider_openai\Plugin\AiProvider\OpenAiProvider`. Explicitly set provider
configuration `temperature: 0.0`, and set the agent provider, model
`gpt-4.1-mini-2025-04-14`, and matching agent configuration.

The active `chat_with_tools` default is currently `gpt-5.2`, so default-provider lookup is rejected
for experiment execution. Also, `AiAgentEntityWrapper` retains `aiConfiguration` but does not apply
it to its top-level provider immediately before `chat()`. The provider proxy must be configured
directly and the agent copy retained for serialization and trace metadata.

Do not call `OpenAiProvider::getConfiguredModels()` in the probe. Installed source shows that a
cache miss calls the remote OpenAI models endpoint. Step 1.02 instead proves that the frozen model
identifier is explicitly bound through `setModelName()` and that the installed local provider API
definition exposes temperature configuration. It does not claim remote model availability,
account entitlement, or successful provider execution.

Strict structured output uses `ChatInput::setChatStructuredJsonSchema()` with the outer
`name`/`description`/`strict`/`schema` shape and `strict: true`. OpenAI provider 1.2.3 maps that to
the provider `json_schema` response format.

## Results, traces, and errors

Use `solve()` for the final response, `getChatHistory()` for normalized model messages and tool
calls, and `getToolResults()` for executed tool objects. Retain sanitized facts from
`ai_agents.request`, `ai_agents.response`, `ai_agents.tool_pre_executed`,
`ai_agents.tool_finished_executed`, and `ai_agents.finished_execution` events.

Provider failures dispatch `Drupal\ai\Event\AiExceptionEvent` and are logged. The wrapper catches
the exception and returns `JOB_NOT_SOLVABLE`, so Step 1.04 must install a run-scoped event capture
before making an error-evidence claim. Tool exceptions become sanitized tool messages during the
loop.

## State location

Use the persistent Drupal `keyvalue` service with collection
`agentic_harness_drupal_ai.run_state`, keyed by run ID. Store canonical run-state data and the
wrapper `toArray()` dump; restore with `fromArray()`. Add a run-scoped persistent lock when writes
are implemented.

This collection belongs to the Drupal AI implementation and is not shared runtime storage. Reject
`ai_agents.private_temp_status_storage` because it is session-bound, expirable, and skipped by CLI.
Reject `ai_agents.artifact_storage` because its installed implementation is in-memory.

Step 1.02 does not open the proposed collection, performs no key-value write, and implements no
state. It inspects only the `keyvalue` factory class and installed `DatabaseStorage` source.

## Rejected alternatives

- Direct provider `chat()` and `ai_agents.agent_helper::runAiProvider()` bypass the selected AI
  Agents entry point.
- AI Agents Explorer is UI/session-oriented.
- Existing content, field, and taxonomy agents expose unrelated behavior.
- Direct OpenAI SDK use bypasses Drupal AI.
- Direct recommendation or source-entity writes bypass the frozen shared operations.
- Private tempstore, in-memory artifacts, and shared runtime state do not satisfy the persistence
  boundary.

## Limitations and unresolved implementation checks

- Provider exceptions require event capture because the wrapper does not return their detail.
- Required-tool behavior is agent-loop enforcement, not provider-level hard selection.
- Remote availability or account entitlement for the pinned model is deliberately untested because
  proving it would require a network request; the probe proves the local binding path only.
- Step 1.04 must prove that the runtime-only image assembled from the certified context is passed
  through `Task::setFiles()` without retention.
- `toArray()`/`fromArray()` are supported serialization surfaces, but restart and duplicate
  prevention are not claimed until their later failure/recovery packages run.

These are bounded implementation checks, not competing runtime paths. They do not require a
dependency or contract change.

## Adequacy for Steps 1.03 and 1.04

Step 1.03 has one exact plugin extension point, four exact adapter functions, a supported allowlist,
and supported parameter constraints. Step 1.04 has one exact AI Agents instantiation/execution path,
an explicit provider/model/temperature path, strict output plumbing, inspectable events and tool
objects, and a justified later persistence location.

Step 1.02 makes no model call and no framework implementation claim. It proves construction and
introspection only.
