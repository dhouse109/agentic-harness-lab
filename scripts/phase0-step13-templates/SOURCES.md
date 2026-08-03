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
