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
| Python | TODO | `python3 --version` | pending | 3.12 required |
| uv | TODO | `uv --version` | pending | |
| LangChain | TODO | `langchain/uv.lock` | pending | Separate environment |
| LangGraph | TODO | `langchain/uv.lock` | pending | |
| LangGraph SQLite checkpointer | TODO | `langchain/uv.lock` | pending | |
| CrewAI | TODO | `crewai/uv.lock` | pending | Separate environment |
| Candidate/frozen model | TODO | Vision preflight evidence | no | Freeze after Step 16 only |

## Captured version evidence

Store command output under `docs/versions-YYYY-MM-DD.txt` or an appropriately named file under
`evidence/logs/preflight/`.
