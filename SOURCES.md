# Source Register

Use current official documentation whenever a framework or security claim depends on changing
behavior. A source entry alone does not verify local behavior.

| ID | Source title | Official? | URL | Retrieved | Version / branch | Claim supported | Caveat | Status |
|---|---|---:|---|---|---|---|---|---|
| SRC-DR-001 | Drupal AI project page | yes | TODO — verify current official URL | TODO | pinned release | Installed project scope and supported release | Project pages do not prove local behavior | seeded |
| SRC-DR-002 | Drupal AI Agents project page | yes | TODO — verify current official URL | TODO | pinned release | Agent package scope and supported release | Pair with Composer lock and local tests | seeded |
| SRC-DR-003 | OpenAI provider documentation | yes | TODO — verify current official URL | TODO | pinned release | Provider configuration and supported pathways | Pair with sanitized capability tests | seeded |
| SRC-SEC-001 | SA-CONTRIB-2026-057 | yes | TODO — official advisory URL | TODO | affected and patched versions | Tool parameters and dependencies require review; patched release required | Not proof that Drupal AI is generally less secure | seeded |
| SRC-LG-001 | LangGraph checkpointing documentation | yes | TODO — verify current official URL | TODO | pinned package version | Persistence and checkpoint behavior | Pair with SQLite restart smoke test | seeded |
| SRC-LG-002 | LangGraph interrupt documentation | yes | TODO — verify current official URL | TODO | pinned package version | Human interruption and continuation APIs | Pair with local implementation evidence | seeded |
| SRC-CR-001 | CrewAI Flow persistence documentation | yes | TODO — verify current official URL | TODO | pinned package version | Flow state persistence | Pair with local process-restart evidence | seeded |
| SRC-CR-002 | CrewAI human-feedback documentation | yes | TODO — verify current official URL | TODO | pinned package version | Human-feedback behavior | Pair with local review/resume evidence | seeded |

## Security-advisory interpretation

Safe statement to test and retain:

> Version governance and review of agent tools, parameters, and dependencies are part of harness
> lifecycle management. The demonstration uses a patched supported release.

Do not use the advisory by itself to rank the frameworks’ overall security or verification quality.

## Step 16 verified capability sources

Retrieved 2026-08-04. These official sources support the capability design; local Step 16 evidence
is still required to establish behavior in this repository.

| ID | Source title | Official? | URL | Version / branch | Capability supported | Caveat | Status |
|---|---|---:|---|---|---|---|---|
| SRC-S16-001 | GPT-4.1 mini model documentation | yes | https://platform.openai.com/docs/models/gpt-4.1-mini | `gpt-4.1-mini-2025-04-14` | Image input, function calling, structured outputs, snapshot pinning | Documentation does not prove wrapper behavior | verified source |
| SRC-S16-002 | Drupal AI provider testing | yes | https://project.pages.drupalcode.org/ai/1.4.x/developers/testing_an_ai_provider/ | AI 1.4.x | Vision, structured-data, and tool-use provider tests | Pair with pinned provider and local evidence | verified source |
| SRC-S16-003 | Drupal AI chat API | yes | https://project.pages.drupalcode.org/ai/developers/call_chat/ | provider API | `ChatInput`, `ChatMessage`, normalized output, image attachments | Wrapper specifics are version-sensitive | verified source |
| SRC-S16-004 | LangChain ChatOpenAI integration | yes | https://docs.langchain.com/oss/python/integrations/chat/openai | pinned lockfile | Image input, strict tool binding, native structured output | Pair with local locked version | verified source |
| SRC-S16-005 | CrewAI documentation | yes | https://docs.crewai.com/ | pinned lockfile | CrewAI LLM, agents, tools, and structured outputs | Exact low-level wrapper shape must be proven locally | verified source |

## Step 17 deterministic Drupal tool sources

Retrieved 2026-08-04. These official sources explain the Drupal mechanisms used by the custom route;
the retained local run remains the evidence for this repository's exact 12-target result.

| ID | Source title | Official? | URL | Mechanism supported | Caveat | Status |
|---|---|---:|---|---|---|---|
| SRC-S17-001 | Structure of routes | yes | https://www.drupal.org/docs/drupal-apis/routing-system/structure-of-routes | Route permission requirements, `_auth`, and `no_cache` options | General routing documentation does not prove this custom route's behavior | verified source |
| SRC-S17-002 | HTTP Basic Authentication overview | yes | https://www.drupal.org/docs/8/core/modules/basic_auth/overview | Core `basic_auth` authenticates a Drupal username/password for a permission-gated route | Use only over protected transport; local credentials remain runtime-only | verified source |
| SRC-S17-003 | Entity Query `accessCheck()` | yes | https://api.drupal.org/api/drupal/core%21lib%21Drupal%21Core%21Entity%21Query%21QueryInterface.php/function/QueryInterface%3A%3AaccessCheck/11.x | Entity queries can explicitly request access checking | Entity, field, and file checks are also retained in the local implementation | verified source |
