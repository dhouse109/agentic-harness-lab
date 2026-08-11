#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-audit}"
REPO=""
if ! REPO="$(git rev-parse --show-toplevel)"; then
  printf '[ERROR] Unable to resolve repository root.\n' >&2
  exit 1
fi
PYTHON="$REPO/crewai/.venv/bin/python"
AUDITOR="$REPO/scripts/gate2b_step01_audit.py"
EVIDENCE_ROOT="$REPO/evidence/gates/gate-2b/contract"
EXPECTED_BASE="0477e882987501438ae07fbb51e741b4be800843"
EXPECTED_BRANCH="gate-2b-step01-crewai-contract-and-evidence-plan"
PACKAGE="gate-2b-step01-crewai-contract-and-evidence-plan"
PACKAGE_VERSION="1.0.0"
NEXT_PACKAGE="gate-2b-step02-crewai-runtime-persistence-and-continuation-probe-v1.0.0"

fail() {
  printf '[ERROR] %s\n' "$*" >&2
  exit 1
}

verify_repo() {
  local branch head
  if ! branch="$(git -C "$REPO" branch --show-current)"; then fail "Unable to resolve branch"; fi
  if ! head="$(git -C "$REPO" rev-parse HEAD)"; then fail "Unable to resolve HEAD"; fi
  [[ "$branch" == "$EXPECTED_BRANCH" ]] || fail "Expected branch $EXPECTED_BRANCH"
  [[ "$head" == "$EXPECTED_BASE" ]] || fail "Expected uncommitted package work on base $EXPECTED_BASE"
  [[ -x "$PYTHON" ]] || fail "Missing locked audit Python: $PYTHON"
  [[ -f "$AUDITOR" ]] || fail "Missing Step 2B.01 auditor"
}

transition_complete() {
  local run_id="$1" digest="$2"
  "$PYTHON" - "$REPO" "$run_id" "$digest" <<'PY'
from pathlib import Path
import sys

repo = Path(sys.argv[1])
run_id = sys.argv[2]
digest = sys.argv[3]
package = "gate-2b-step01-crewai-contract-and-evidence-plan-v1.0.0"
next_package = "gate-2b-step02-crewai-runtime-persistence-and-continuation-probe-v1.0.0"

def replace_once(rel, old, new):
    path = repo / rel
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"[ERROR] Completion anchor missing in {rel}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

accepted = f"Accepted Step 2B.01 evidence run: `{run_id}`\nAccepted Gate 2B contract digest: `{digest}`"
replace_once(
    "AGENTS.md",
    f"**Active package:** `{package}`.",
    f"**Step 2B.01:** complete.\n\n**Next package:** `{next_package}`.",
)
replace_once(
    "AGENTS.md",
    "Do not generate Step 2B.02 until Step 2B.01 is passing and committed.",
    "Do not generate Step 2B.02 until Step 2B.01 is committed, merged, local `main` is resynchronized, and the post-merge audit passes.\n\n" + accepted,
)
replace_once(
    "README.md",
    f"- **Active package:** `{package}`.\n- **Step 2B.01:** active — CrewAI contract and evidence plan only.\n- **Next evidence boundary after 2B.01:** model-free pinned-runtime persistence and continuation probe.",
    f"- **Step 2B.01:** complete.\n- **Next package:** `{next_package}`.\n" + accepted,
)
replace_once(
    "PLAN.md",
    f"**Active package:**\n\n```text\n{package}\n```",
    f"**Completed package:**\n\n```text\n{package}\n```\n\n**Next package:**\n\n```text\n{next_package}\n```\n\n" + accepted,
)
replace_once("PLAN.md", "- [ ] Step 2B.01 — CrewAI contract and evidence plan", "- [x] Step 2B.01 — CrewAI contract and evidence plan")
replace_once(
    "docs/CURRENT-STATUS.md",
    f"- **Active package:** `{package}`.",
    f"- **Step 2B.01:** complete.\n- **Next package:** `{next_package}`.\n" + accepted,
)
replace_once(
    "docs/CURRENT-STATUS.md",
    "Step 2B.01 is active. Do not generate Step 2B.02 until Step 2B.01 is passing and committed.",
    "Step 2B.01 is complete. Do not generate Step 2B.02 until Step 2B.01 is committed and merged, local `main` is resynchronized, and the post-merge audit passes.",
)
PY
}

verify_evidence() {
  "$PYTHON" "$AUDITOR" --repo "$REPO" --evidence-required >/dev/null
  local pointer run_dir
  pointer="$EVIDENCE_ROOT/GATE2B-STEP01-LATEST.txt"
  if ! run_dir="$(<"$pointer")"; then fail "Unable to read evidence pointer"; fi
  printf '[PASS] Gate 2B Step 2B.01 retained evidence audit passed.\n'
  printf '[PASS] Evidence: %s\n' "$run_dir"
}

verify_repo

case "$MODE" in
  run)
    run_id="gate2b-step01-$(date -u +%Y%m%dT%H%M%SZ)-$(printf '%08x' "$$")"
    run_dir="$EVIDENCE_ROOT/$run_id"
    mkdir -p "$run_dir"
    printf '%s\n' "${run_dir#"$REPO/"}" >"$EVIDENCE_ROOT/GATE2B-STEP01-LAST-RUN.txt"
    run_complete=0
    retain_failure() {
      local rc=$?
      if [[ "$run_complete" != 1 ]]; then
        "$PYTHON" - "$run_dir" "$run_id" "$PACKAGE" "$PACKAGE_VERSION" "$rc" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

run_dir = Path(sys.argv[1])
run_dir.mkdir(parents=True, exist_ok=True)
summary = {
    "schema_version": 1,
    "status": "fail",
    "run_id": sys.argv[2],
    "package": sys.argv[3],
    "package_version": sys.argv[4],
    "exit_code": int(sys.argv[5]),
    "model_calls": 0,
    "crewai_origin_drupal_mutations": 0,
    "source_content_mutations": 0,
    "dependency_changes": 0,
    "gate2c_executions": 0,
    "gate2c_status": "deferred_unclaimed",
    "failed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
}
(run_dir / "failure-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
        printf '[RETAINED] Failed Step 2B.01 evidence: %s\n' "${run_dir#"$REPO/"}" >&2
      fi
      exit "$rc"
    }
    trap retain_failure EXIT

    bash "$REPO/scripts/run-gate2a-step10-langgraph-certification-freeze-and-crewai-handoff.sh" audit >"$run_dir/gate2a-predecessor-audit.log"
    "$PYTHON" "$AUDITOR" --repo "$REPO" --activation --json >"$run_dir/contract-audit.json"
    cp "$REPO/shared/contracts/GATE2B-CREWAI-BATCH-CONTRACT.json" "$run_dir/contract.json"
    cp "$REPO/shared/contracts/GATE2B-CREWAI-BATCH-CONTRACT.sha256" "$run_dir/contract.sha256"
    digest=""
    if ! digest="$(sha256sum "$REPO/shared/contracts/GATE2B-CREWAI-BATCH-CONTRACT.json" | awk '{print $1}')"; then
      fail "Unable to compute Gate 2B contract digest"
    fi
    "$PYTHON" - "$REPO" "$run_dir" "$run_id" "$digest" <<'PY'
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

repo = Path(sys.argv[1])
run_dir = Path(sys.argv[2])
run_id = sys.argv[3]
digest = sys.argv[4]
now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def git(*args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()

metadata = {
    "captured_at": now,
    "branch": git("branch", "--show-current"),
    "commit": git("rev-parse", "HEAD"),
    "origin_main": git("rev-parse", "origin/main"),
    "gate2a_feature_commit": "1a32f8584a75dc59533f48dfb0b7636da94d5a00",
}
environment = {
    "captured_at": now,
    "python": sys.version.split()[0],
    "crewai": importlib.metadata.version("crewai"),
    "crewai_tools": importlib.metadata.version("crewai-tools"),
    "uv_lock_sha256": hashlib.sha256((repo / "crewai/uv.lock").read_bytes()).hexdigest(),
    "version_sources": ["crewai/uv.lock", "installed distribution metadata", "retained Phase 0 evidence"],
    "dependency_change": False,
}
inspection = {
    "schema_version": 1,
    "status": "inspected_not_yet_gate2b_observed",
    "model_calls": 0,
    "drupal_mutations": 0,
    "findings": [
        {"surface": "FlowPersistence/@persist/SQLiteFlowPersistence", "classification": "inspected", "unresolved": "process-boundary restore, re-execution, isolation, specimen fitness"},
        {"surface": "CheckpointConfig with JSON/SQLite providers and Flow/Crew restore", "classification": "inspected", "unresolved": "checkpoint completeness and continuation semantics"},
        {"surface": "HumanFeedbackPending/custom provider/Flow.from_pending", "classification": "inspected", "unresolved": "Drupal-authoritative no-extra-model-call continuation"},
        {"surface": "LLM/task/guardrail retry controls", "classification": "inspected", "unresolved": "explicit zero-hidden-retry configuration"},
        {"surface": "platform/XDG application data resolution", "classification": "inspected", "unresolved": "selected CrewAI-owned runtime path"},
    ],
    "architecture_status": "deferred_to_step_2B_02",
}
summary = {
    "schema_version": 1,
    "status": "pass",
    "run_id": run_id,
    "package": "gate-2b-step01-crewai-contract-and-evidence-plan",
    "package_version": "1.0.0",
    "contract_sha256": digest,
    "predecessor_commit": "0477e882987501438ae07fbb51e741b4be800843",
    "gate2a_permanent_audit": "pass",
    "gate2a_freeze_sha256": "a28361c34b9d1c2089eee786324ad34cffbf54e3495f59a276c489865e5630f0",
    "architecture_status": "deferred_to_step_2B_02",
    "model_calls": 0,
    "crewai_origin_drupal_mutations": 0,
    "source_content_mutations": 0,
    "dependency_changes": 0,
    "gate2c_executions": 0,
    "gate2c_status": "deferred_unclaimed",
    "step_2B_02_started": False,
    "completed_at": now,
    "next_boundary": "human commit approval",
    "next_package": "gate-2b-step02-crewai-runtime-persistence-and-continuation-probe-v1.0.0",
}
(run_dir / "git-metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
(run_dir / "environment.json").write_text(json.dumps(environment, indent=2, sort_keys=True) + "\n", encoding="utf-8")
(run_dir / "runtime-inspection.json").write_text(json.dumps(inspection, indent=2, sort_keys=True) + "\n", encoding="utf-8")
(run_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
(run_dir / "summary.md").write_text(f"""# Gate 2B Step 2B.01 Contract Evidence

- **Status:** PASS
- **Run ID:** `{run_id}`
- **Contract SHA-256:** `{digest}`
- **Gate 2A permanent audit:** pass
- **Python / CrewAI / CrewAI Tools:** `{environment['python']}` / `{environment['crewai']}` / `{environment['crewai_tools']}`
- **Architecture:** deferred to the model-free Step 2B.02 evidence boundary
- **Model calls:** 0
- **CrewAI-origin Drupal mutations:** 0
- **Source-content mutations:** 0
- **Dependency changes:** 0
- **Gate 2C executions:** 0
- **Gate 2C:** deferred and unclaimed
- **Next package after commit/merge/resync/audit:** `gate-2b-step02-crewai-runtime-persistence-and-continuation-probe-v1.0.0`

This evidence certifies only the CrewAI contract and evidence-plan boundary. It does not claim observed CrewAI persistence, continuation, retry, human-feedback, model, Drupal-integration, batch, or Gate 2C behavior.
""", encoding="utf-8")
PY
    (
      cd "$run_dir"
      sha256sum contract-audit.json contract.json contract.sha256 environment.json gate2a-predecessor-audit.log git-metadata.json runtime-inspection.json summary.json summary.md >package-files-sha256.txt
    )
    if rg -n -i 'sk-[A-Za-z0-9_-]{20,}|data:image/|Authorization[[:space:]]*:|Basic[[:space:]]+[A-Za-z0-9+/]{16,}={0,2}' "$run_dir" >/dev/null; then
      fail "Potential secret-bearing evidence"
    fi
    printf '%s\n' "${run_dir#"$REPO/"}" >"$EVIDENCE_ROOT/GATE2B-STEP01-LATEST.txt"
    transition_complete "$run_id" "$digest"
    verify_evidence
    run_complete=1
    trap - EXIT
    printf '[PASS] Gate 2B Step 2B.01 contract/evidence boundary passed.\n'
    printf '[STOP] Review evidence and diff; human commit approval is required.\n'
    ;;
  audit)
    bash "$REPO/scripts/run-gate2a-step10-langgraph-certification-freeze-and-crewai-handoff.sh" audit >/dev/null
    verify_evidence
    printf '[PASS] Gate 2B Step 2B.01 permanent post-run audit passed.\n'
    ;;
  *)
    fail "Usage: bash scripts/run-gate2b-step01-crewai-contract-and-evidence-plan.sh {run|audit}"
    ;;
esac
