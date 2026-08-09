#!/usr/bin/env bash
set -Eeuo pipefail
MODE="${1:-audit}"
REPO="$(git rev-parse --show-toplevel)"
EXPECTED_BASE="d87c66a8a342109253e906e7e29ce2c15f7ddbef"
EXPECTED_BRANCH="gate-2a-step01-langgraph-contract-and-evidence-plan"
EXPECTED_GATE1_SHA="2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd"
EVIDENCE_ROOT="$REPO/evidence/gates/gate-2a/contract"
PYTHON="$REPO/crewai/.venv/bin/python"
AUDITOR="$REPO/scripts/gate2a_step01_audit.py"
fail(){ printf '[ERROR] %s\n' "$*" >&2; exit 1; }
verify_repo(){
  local branch head
  branch="$(git -C "$REPO" branch --show-current)"
  head="$(git -C "$REPO" rev-parse HEAD)"
  case "$MODE" in
    run)
      [[ "$branch" == "$EXPECTED_BRANCH" ]] || fail "Run mode requires branch $EXPECTED_BRANCH"
      [[ "$head" == "$EXPECTED_BASE" ]] || fail "Run mode requires uncommitted package work on base $EXPECTED_BASE"
      ;;
    audit)
      case "$branch" in
        "$EXPECTED_BRANCH"|main) ;;
        *) fail "Audit mode requires branch $EXPECTED_BRANCH or main" ;;
      esac
      git -C "$REPO" merge-base --is-ancestor "$EXPECTED_BASE" "$head" || fail "Audit mode requires predecessor $EXPECTED_BASE in HEAD ancestry"
      ;;
    *) fail "Usage: bash scripts/run-gate2a-step01.sh {run|audit}" ;;
  esac
  [[ -x "$PYTHON" ]] || fail "Missing locked audit Python: $PYTHON"
  [[ -f "$AUDITOR" ]] || fail "Missing Step 2A.01 auditor"
  [[ "$(sha256sum "$REPO/shared/contracts/GATE1-DRUPAL-AI-FREEZE.json" | awk '{print $1}')" == "$EXPECTED_GATE1_SHA" ]] || fail "Gate 1 freeze changed"
}
transition_complete(){
  local run_id="$1" digest="$2"
  "$PYTHON" - "$REPO" "$run_id" "$digest" <<'PY'
from pathlib import Path
import sys
repo=Path(sys.argv[1]); run_id=sys.argv[2]; digest=sys.argv[3]
def rep(rel,old,new):
    p=repo/rel; t=p.read_text(encoding='utf-8')
    if old not in t: raise SystemExit(f'[ERROR] Completion anchor missing: {rel}: {old[:70]}')
    p.write_text(t.replace(old,new,1),encoding='utf-8')
accepted=f"Accepted Step 2A.01 evidence run: `{run_id}`\nAccepted Gate 2A contract digest: `{digest}`"
rep('AGENTS.md','**Active package:** `gate-2a-step01-langgraph-contract-and-evidence-plan-v1.0.3`.','**Step 2A.01:** complete.\n\n**Next package:** `gate-2a-step02-langgraph-runtime-and-checkpoint-probe-v1.0.0`.')
rep('AGENTS.md','Do not generate Step 2A.02 until Step 2A.01 is passing and committed.', 'Do not generate Step 2A.02 until Step 2A.01 is committed, merged, local `main` is resynchronized, and the post-merge audit passes.\n\n'+accepted)
rep('README.md','- **Active package:** `gate-2a-step01-langgraph-contract-and-evidence-plan-v1.0.3`.\n- **Step 2A.01:** active — contract and evidence plan only.\n- **Next implementation boundary after 2A.01:** pinned LangGraph runtime/checkpoint probe.', '- **Step 2A.01:** complete.\n- **Next package:** `gate-2a-step02-langgraph-runtime-and-checkpoint-probe-v1.0.0`.\n'+accepted)
rep('PLAN.md','**Active package:**\n\n```text\ngate-2a-step01-langgraph-contract-and-evidence-plan-v1.0.3\n```','**Completed package:**\n\n```text\ngate-2a-step01-langgraph-contract-and-evidence-plan-v1.0.3\n```\n\n**Next package:**\n\n```text\ngate-2a-step02-langgraph-runtime-and-checkpoint-probe-v1.0.0\n```\n\n'+accepted)
rep('PLAN.md','- [ ] Step 2A.01 — LangGraph contract and evidence plan','- [x] Step 2A.01 — LangGraph contract and evidence plan')
rep('docs/CURRENT-STATUS.md','- **Active package:** `gate-2a-step01-langgraph-contract-and-evidence-plan-v1.0.3`.','- **Step 2A.01:** complete.\n- **Next package:** `gate-2a-step02-langgraph-runtime-and-checkpoint-probe-v1.0.0`.\n'+accepted)
rep('docs/CURRENT-STATUS.md','Step 2A.01 is the active contract/evidence package. Do not generate Step 2A.02 until 2A.01 passes, is committed and merged, local `main` is resynchronized, and the post-merge audit passes.','Step 2A.01 is complete. Do not generate Step 2A.02 until 2A.01 is committed and merged, local `main` is resynchronized, and the post-merge audit passes.')
PY
}
verify_evidence(){
  local ptr="$EVIDENCE_ROOT/GATE2A-STEP01-LATEST.txt" run_dir
  [[ -f "$ptr" ]] || fail "Missing Step 2A.01 latest pointer"
  run_dir="$REPO/$(<"$ptr")"; [[ -d "$run_dir" ]] || fail "Missing evidence directory"
  (cd "$run_dir" && sha256sum -c package-files-sha256.txt >/dev/null) || fail "Evidence checksum failed"
  "$PYTHON" - "$run_dir/summary.json" <<'PY'
import json,sys
s=json.load(open(sys.argv[1]))
for k,v in {'status':'pass','package':'gate-2a-step01-langgraph-contract-and-evidence-plan','package_version':'1.0.3','model_call_performed':False,'drupal_state_mutated':False,'gate1_artifacts_changed':False,'next_package':'gate-2a-step02-langgraph-runtime-and-checkpoint-probe-v1.0.0'}.items():
    if s.get(k)!=v: raise SystemExit(f'[ERROR] Unexpected summary field {k}: {s.get(k)!r}')
PY
  if rg -n -i 'sk-[A-Za-z0-9_-]{20,}|data:image/|Authorization[[:space:]]*:|Basic[[:space:]]+[A-Za-z0-9+/]{16,}={0,2}' "$run_dir" >/dev/null; then fail "Potential secret-bearing evidence"; fi
  printf '[PASS] Gate 2A Step 2A.01 retained evidence audit passed.\n'
  printf '[PASS] Evidence: %s\n' "${run_dir#"$REPO/"}"
}
verify_repo
case "$MODE" in
  run)
    run_id="gate2a-step01-$(date -u +%Y%m%dT%H%M%SZ)-$$"; run_dir="$EVIDENCE_ROOT/$run_id"; mkdir -p "$run_dir"
    bash "$REPO/scripts/run-gate1-step07-drupal-ai-certification-and-handoff.sh" audit >"$run_dir/gate1-predecessor-audit.log"
    "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state active --json >"$run_dir/contract-audit.json"
    cp "$REPO/shared/contracts/GATE2A-LANGGRAPH-BATCH-CONTRACT.json" "$run_dir/contract.json"
    cp "$REPO/shared/contracts/GATE2A-LANGGRAPH-BATCH-CONTRACT.sha256" "$run_dir/contract.sha256"
    { codex --version 2>/dev/null || true; codex features list 2>/dev/null | grep -E '^(multi_agent|multi_agent_v2)[[:space:]]' || true; git -C "$REPO" worktree list --porcelain; } >"$run_dir/codex-capability.txt"
    digest="$(sha256sum "$REPO/shared/contracts/GATE2A-LANGGRAPH-BATCH-CONTRACT.json" | awk '{print $1}')"
    "$PYTHON" - "$REPO" "$run_dir" "$run_id" "$digest" <<'PY'
import json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
repo=Path(sys.argv[1]); rd=Path(sys.argv[2]); rid=sys.argv[3]; digest=sys.argv[4]; now=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
meta={'branch':subprocess.run(['git','-C',str(repo),'branch','--show-current'],capture_output=True,text=True,check=True).stdout.strip(),'commit':subprocess.run(['git','-C',str(repo),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip(),'captured_at':now}
summary={'schema_version':1,'status':'pass','run_id':rid,'package':'gate-2a-step01-langgraph-contract-and-evidence-plan','package_version':'1.0.3','contract_sha256':digest,'gate1_predecessor_audit':'pass','gate1_freeze_sha256':'2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd','codex_disposition':'B','model_call_performed':False,'drupal_state_mutated':False,'dependency_change':False,'gate1_artifacts_changed':False,'step02_started':False,'completed_at':now,'next_boundary':'human commit approval','next_package':'gate-2a-step02-langgraph-runtime-and-checkpoint-probe-v1.0.0'}
(rd/'git-metadata.json').write_text(json.dumps(meta,indent=2,sort_keys=True)+'\n')
(rd/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
(rd/'summary.md').write_text(f'''# Gate 2A Step 2A.01 Contract Evidence\n\n- **Status:** PASS\n- **Run ID:** `{rid}`\n- **Contract SHA-256:** `{digest}`\n- **Gate 1 predecessor audit:** pass\n- **Gate 1 freeze unchanged:** yes\n- **Codex disposition:** B (multi-agent available; no proven worktree isolation)\n- **Model calls:** 0\n- **Drupal mutation:** 0\n- **Dependency changes:** 0\n- **Gate 1 artifacts changed:** no\n- **Step 2A.02 started:** no\n- **Next package after merge/resync:** `gate-2a-step02-langgraph-runtime-and-checkpoint-probe-v1.0.0`\n\nThis evidence certifies only the Gate 2A contract/evidence boundary. It does not claim observed LangGraph runtime, checkpoint, model, human-review, or recovery behavior.\n''')
PY
    (cd "$run_dir" && sha256sum codex-capability.txt contract-audit.json contract.json contract.sha256 gate1-predecessor-audit.log git-metadata.json summary.json summary.md > package-files-sha256.txt)
    mkdir -p "$EVIDENCE_ROOT"; printf '%s\n' "${run_dir#"$REPO/"}" >"$EVIDENCE_ROOT/GATE2A-STEP01-LAST-RUN.txt"
    (cd "$run_dir" && sha256sum -c package-files-sha256.txt >/dev/null) || fail "New evidence checksum failed"
    printf '%s\n' "${run_dir#"$REPO/"}" >"$EVIDENCE_ROOT/GATE2A-STEP01-LATEST.txt"
    transition_complete "$run_id" "$digest"
    "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state complete >/dev/null
    verify_evidence
    printf '[PASS] Gate 2A Step 2A.01 contract/evidence boundary passed.\n'
    printf '[STOP] Review evidence and diff; human commit approval is required.\n'
    ;;
  audit)
    bash "$REPO/scripts/run-gate1-step07-drupal-ai-certification-and-handoff.sh" audit >/dev/null
    "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state complete >/dev/null
    verify_evidence
    printf '[PASS] Gate 2A Step 2A.01 post-run audit passed.\n'
    ;;
  *) fail "Usage: bash scripts/run-gate2a-step01.sh {run|audit}";;
esac
