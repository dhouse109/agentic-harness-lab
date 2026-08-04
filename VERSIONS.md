# Version Register

Record exact installed versions. Do not substitute “latest.”

| Component | Exact version / commit | Evidence command or file | Frozen? | Notes |
|---|---|---|---|---|
| Ubuntu | Ubuntu 24.04.4 LTS | `evidence/logs/preflight/vision/step16-20260804T164330Z-832871/environment.json` | yes | WSL2 host distribution |
| Docker | client=29.6.2 server=29.6.2 | `evidence/logs/preflight/vision/step16-20260804T164330Z-832871/environment.json` | yes | Client/server captured locally |
| DDEV | ddev version v1.25.3 | `evidence/logs/preflight/vision/step16-20260804T164330Z-832871/environment.json` | yes | Local Drupal runtime |
| PHP | 8.3.31 | `evidence/logs/preflight/vision/step16-20260804T164330Z-832871/environment.json` | yes | DDEV web container |
| Drupal core | 11.4.4 | `evidence/logs/preflight/vision/step16-20260804T164330Z-832871/environment.json` | yes | Composer lock and local command |
| Drupal AI | 1.4.5 | `evidence/logs/preflight/vision/step16-20260804T164330Z-832871/environment.json` | yes | Pinned Composer release |
| Drupal AI Agents | 1.3.2 | `evidence/logs/preflight/vision/step16-20260804T164330Z-832871/environment.json` | yes | Pinned patched supported release |
| OpenAI provider | 1.2.3 | `evidence/logs/preflight/vision/step16-20260804T164330Z-832871/environment.json` | yes | Pinned Composer release used in Step 16 |
| Drush | 13.7.6.0 | `evidence/logs/preflight/vision/step16-20260804T164330Z-832871/environment.json` | yes | Pinned Composer release |
| Python | 3.12 (3.12.13 LangChain; 3.12.13 CrewAI) | `evidence/logs/preflight/step15-20260804T142613Z-790398` / project `uv.lock` | yes | Separate Python 3.12 uv environments |
| uv | 0.11.33 | `evidence/logs/preflight/step15-20260804T142613Z-790398` / project `uv.lock` | yes | Resolved by Step 15 lockfile |
| LangChain | 1.3.14 | `evidence/logs/preflight/step15-20260804T142613Z-790398` / project `uv.lock` | yes | Resolved by Step 15 lockfile |
| LangGraph | 1.2.10 | `evidence/logs/preflight/step15-20260804T142613Z-790398` / project `uv.lock` | yes | Resolved by Step 15 lockfile |
| LangGraph SQLite checkpointer | 3.1.1 | `evidence/logs/preflight/step15-20260804T142613Z-790398` / project `uv.lock` | yes | Resolved by Step 15 lockfile |
| CrewAI | 1.15.10 | `evidence/logs/preflight/step15-20260804T142613Z-790398` / project `uv.lock` | yes | Resolved by Step 15 lockfile |
| CrewAI Tools | 1.15.10 | `evidence/logs/preflight/step15-20260804T142613Z-790398` / `crewai/uv.lock` | yes | Resolved by Step 15 lockfile |
| Candidate/frozen model | gpt-4.1-mini-2025-04-14 — frozen | `evidence/logs/preflight/vision/step16-20260804T164330Z-832871` / ADR-0002 | yes | Direct image, strict structured-output, and tool-capability spike passed |

## Captured version evidence

Store command output under `docs/versions-YYYY-MM-DD.txt` or an appropriately named file under
`evidence/logs/preflight/`.
