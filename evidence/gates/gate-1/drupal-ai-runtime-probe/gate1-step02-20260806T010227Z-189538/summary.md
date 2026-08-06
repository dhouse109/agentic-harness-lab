# Gate 1 Step 1.02 Drupal AI Runtime Probe

- **Status:** PASS
- **Run ID:** `gate1-step02-20260806T010227Z-189538`
- **Pinned versions:** Drupal 11.4.4; Drupal AI 1.4.5; AI Agents 1.3.2; OpenAI provider 1.2.3
- **Chosen service:** `plugin.manager.ai_agents`
- **Chosen wrapper:** `Drupal\ai_agents\PluginBase\AiAgentEntityWrapper`
- **Callable path:** `determineSolvability()` then `solve()`
- **Provider/model:** explicit `openai` / `gpt-4.1-mini-2025-04-14` / temperature `0.0`
- **Active default:** rejected; it is not the frozen model
- **Remote model catalog queried:** no; remote availability/entitlement is not claimed
- **Framework-owned later state:** `keyvalue` collection `agentic_harness_drupal_ai.run_state`
- **Future state collection opened or written:** no
- **Before/after:** 20 Articles, zero recommendations, frozen 12-target order, canonical sequence 1
- **Source content changed:** no
- **Model or network call:** no
- **Secret or raw image retained:** no
- **Step 1.03 started:** no

This evidence proves construction and introspection of the pinned runtime path only. It does not claim a model call, adapter implementation, vertical slice, recovery, or framework quality.
