# Version Register

Record exact installed versions. Do not substitute “latest.”

| Component | Exact version / commit | Evidence command or file | Frozen? | Notes |
|---|---|---|---|---|
| Ubuntu | TODO | `lsb_release -a` | yes | WSL2 |
| Docker | TODO | `docker version` | yes | Docker CE in WSL2 |
| DDEV | TODO | `ddev version` | yes | |
| PHP | TODO | `ddev php -v` | yes | |
| Drupal core | TODO | `ddev drush status` | yes | Major 11 required |
| Drupal AI | TODO | Composer lock / versions file | yes | |
| Drupal AI Agents | TODO | Composer lock / versions file | yes | Patched supported release required |
| OpenAI provider | TODO | Composer lock / versions file | yes | |
| Drush | TODO | Composer lock / `ddev drush --version` | yes | |
| Python | 3.12 (3.12.13 LangChain; 3.12.13 CrewAI) | `evidence/logs/preflight/step15-20260804T142613Z-790398` / project `uv.lock` | yes | Separate Python 3.12 uv environments |
| uv | 0.11.33 | `evidence/logs/preflight/step15-20260804T142613Z-790398` / project `uv.lock` | yes | Resolved by Step 15 lockfile |
| LangChain | 1.3.14 | `evidence/logs/preflight/step15-20260804T142613Z-790398` / project `uv.lock` | yes | Resolved by Step 15 lockfile |
| LangGraph | 1.2.10 | `evidence/logs/preflight/step15-20260804T142613Z-790398` / project `uv.lock` | yes | Resolved by Step 15 lockfile |
| LangGraph SQLite checkpointer | 3.1.1 | `evidence/logs/preflight/step15-20260804T142613Z-790398` / project `uv.lock` | yes | Resolved by Step 15 lockfile |
| CrewAI | 1.15.10 | `evidence/logs/preflight/step15-20260804T142613Z-790398` / project `uv.lock` | yes | Resolved by Step 15 lockfile |
| CrewAI Tools | 1.15.10 | `evidence/logs/preflight/step15-20260804T142613Z-790398` / `crewai/uv.lock` | yes | Resolved by Step 15 lockfile |
| Candidate/frozen model | gpt-4.1-mini-2025-04-14 — candidate only | `evidence/logs/preflight/step15-20260804T142613Z-790398` | no | Text-only pings passed; freeze only after Step 16 |

## Captured version evidence

Store command output under `docs/versions-YYYY-MM-DD.txt` or an appropriately named file under
`evidence/logs/preflight/`.
