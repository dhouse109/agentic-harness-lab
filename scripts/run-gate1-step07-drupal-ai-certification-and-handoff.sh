#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
DRUPAL="$REPO/drupal"
PYTHON="$REPO/crewai/.venv/bin/python"
BASELINE="75653ec21176173a8f4af1a1743f2e9286333492"
PRE_AUDITOR="$REPO/scripts/gate1_step07_predecessor_audit.py"
EVIDENCE_AUDITOR="$REPO/scripts/gate1_step07_evidence_audit.py"
FINALIZER="$REPO/scripts/gate1_step07_finalize.py"
CERT_HELPER="$DRUPAL/scripts/gate1-step07-certification.php"
STEP05_PHP="scripts/gate1-step05-drupal-ai-batch-runner.php"
STEP07_PHP="scripts/gate1-step07-certification.php"
PREFLIGHT_ROOT="$REPO/evidence/gates/gate-1/certification-preflight"
CERT_ROOT="$REPO/evidence/gates/gate-1/certification"
RESULT_ROOT="$REPO/evidence/results/drupal_ai"
PREFLIGHT_LATEST="$PREFLIGHT_ROOT/GATE1-STEP07-PREFLIGHT-LATEST.txt"
ACTIVE="$CERT_ROOT/.active-certification"
STEP06_RUN="gate1-step06-20260808T231216Z-2188911"
STEP06_DIR="$REPO/evidence/gates/gate-1/batch-evidence/$STEP06_RUN"

# Certification recovery state must remain available to the shell EXIT trap.
# Do not make these certify()-local: Bash runs EXIT after function-local scope unwinds.
CERT_GATE=""
CERT_RESULT=""
CERT_SNAPSHOT=""
CERT_SNAPSHOT_CREATED=0
CERT_RESTORED=0

fail(){ printf '[ERROR] %s\n' "$*" >&2; exit 1; }
pass(){ printf '[PASS] %s\n' "$*"; }
info(){ printf '[INFO] %s\n' "$*"; }

module_enabled(){ (cd "$DRUPAL" && ddev drush pm:list --type=module --status=enabled --format=list) | grep -Fx agentic_harness_drupal_ai >/dev/null; }
run05(){ local mode="$1"; shift || true; (cd "$DRUPAL" && ddev drush --quiet php:script "$STEP05_PHP" -- "$mode" "$@"); }
run07(){ local mode="$1"; (cd "$DRUPAL" && env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL ddev drush --quiet php:script "$STEP07_PHP" -- "$mode"); }
runfull(){ (cd "$DRUPAL" && ddev drush --quiet php:script scripts/gate05-step04.php -- snapshot); }

verify_installed(){
  [[ -x "$PYTHON" ]] || fail "Locked Python environment unavailable."
  for p in "$PRE_AUDITOR" "$EVIDENCE_AUDITOR" "$FINALIZER" "$CERT_HELPER"; do [[ -s "$p" ]] || fail "Missing Step 1.07 installed file: $p"; done
  git -C "$REPO" merge-base --is-ancestor "$BASELINE" HEAD || fail "Step 1.06 merged baseline is not in HEAD ancestry."
  bash -n "$0"
  "$PYTHON" - "$PRE_AUDITOR" "$EVIDENCE_AUDITOR" "$FINALIZER" <<'PY_SYNTAX'
from pathlib import Path
import sys
for name in sys.argv[1:]:
    path=Path(name)
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
PY_SYNTAX
  (cd "$DRUPAL" && ddev exec php -l scripts/gate1-step07-certification.php >/dev/null)
}

verify_preflight_scope(){
  "$PYTHON" - "$REPO" <<'PY'
import subprocess,sys
from pathlib import Path
repo=Path(sys.argv[1])
allowed={
 "docs/gates/GATE-1-STEP07-DRUPAL-AI-CERTIFICATION-AND-HANDOFF.md",
 "drupal/scripts/gate1-step07-certification.php",
 "scripts/gate1_step07_predecessor_audit.py",
 "scripts/gate1_step07_evidence_audit.py",
 "scripts/gate1_step07_finalize.py",
 "scripts/run-gate1-step07-drupal-ai-certification-and-handoff.sh",
}
out=subprocess.run(["git","-C",str(repo),"status","--porcelain=v1","--untracked-files=all"],check=True,capture_output=True,text=True).stdout
paths=set()
for line in out.splitlines():
    if not line: continue
    p=line[3:]
    if " -> " in p:p=p.split(" -> ",1)[1]
    paths.add(p)
unexpected={
    p for p in paths
    if (
        p not in allowed
        and not p.startswith("evidence/gates/gate-1/certification-preflight/")
        and not p.startswith("evidence/gates/gate-1/certification/")
        and not p.startswith("evidence/results/drupal_ai/drupal_ai-")
    )
}
if unexpected:
    raise SystemExit(f"[ERROR] Unexpected preflight working-tree paths: {sorted(unexpected)}")
PY
}

verify_preflight_retained(){
  [[ -s "$PREFLIGHT_LATEST" ]] || fail "No passing Step 1.07 preflight pointer exists."
  local dir="$REPO/$(<"$PREFLIGHT_LATEST")"
  [[ -d "$dir" ]] || fail "Passing Step 1.07 preflight directory missing."
  "$PYTHON" - "$dir/summary.json" <<'PY'
import json,sys
v=json.load(open(sys.argv[1],encoding='utf-8'))
expected={"status":"pass","model_call_performed":False,"drupal_mutation_performed":False,"ordered_boundary_count":8}
for k,e in expected.items():
    if v.get(k)!=e:raise SystemExit(f"[ERROR] Preflight summary differs: {k}")
PY
  (cd "$dir" && sha256sum -c package-files-sha256.txt >/dev/null) || fail "Preflight evidence checksum failed."
}

write_preflight_summary(){
  local dir="$1" run_id="$2"
  "$PYTHON" - "$dir" "$run_id" <<'PY'
import json,sys
from datetime import datetime,timezone
from pathlib import Path
dir=Path(sys.argv[1]);rid=sys.argv[2]
summary={"schema_version":1,"status":"pass","run_id":rid,"package":"gate-1-step07-drupal-ai-certification-and-handoff","package_version":"1.0.3","ordered_boundary_count":8,"model_call_performed":False,"drupal_mutation_performed":False,"certification_started":False,"next_boundary":"explicit certification approval","completed_at":datetime.now(timezone.utc).isoformat().replace('+00:00','Z')}
(dir/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
(dir/'summary.md').write_text(f"# Gate 1 Step 1.07 Compatibility-Aware Preflight\n\n- **Status:** PASS\n- **Run ID:** `{rid}`\n- **Ordered boundaries:** Gate 0.5 Step 05, Gate 1 Steps 1.01–1.06, then pins/contracts/hashes\n- **Model/provider calls:** none\n- **Drupal mutation:** none\n- **Certification batch started:** no\n- **Next boundary:** explicit approval to run `certify`\n",encoding='utf-8')
PY
  (cd "$dir" && find . -maxdepth 1 -type f ! -name package-files-sha256.txt -printf '%f\n' | sort | xargs sha256sum >package-files-sha256.txt)
}

preflight(){
  [[ "$(git -C "$REPO" branch --show-current)" == "main" ]] || fail "Initial Step 1.07 preflight requires branch main."
  [[ "$(git -C "$REPO" rev-parse HEAD)" == "$BASELINE" ]] || fail "Initial Step 1.07 preflight requires exact merged Step 1.06 baseline."
  [[ "$(git -C "$REPO" rev-parse origin/main)" == "$BASELINE" ]] || fail "origin/main is not synchronized to the merged Step 1.06 baseline."
  verify_preflight_scope
  [[ ! -e "$ACTIVE" ]] || fail "A Step 1.07 certification run is active."
  local run_id="gate1-step07-preflight-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  local dir="$PREFLIGHT_ROOT/$run_id"
  mkdir -p "$dir"
  cleanup(){ local rc=$?; if [[ $rc -ne 0 ]]; then rm -rf "$dir"; fi; exit $rc; }
  trap cleanup EXIT INT TERM
  info "Running compatibility-aware ordered Gate 0.5/Gate 1 audit chain..."
  "$PYTHON" "$PRE_AUDITOR" "$REPO" "$dir" >"$dir/predecessor-audit-summary.json"
  git -C "$REPO" status --porcelain=v1 >"$dir/git-status.txt"
  git -C "$REPO" rev-parse HEAD >"$dir/head.txt"
  write_preflight_summary "$dir" "$run_id"
  if rg -n -i 'sk-[A-Za-z0-9_-]{20,}|data:image/|Authorization[[:space:]]*:|Basic[[:space:]]+[A-Za-z0-9+/]{16,}={0,2}' "$dir" >/dev/null; then fail "Potential secret/raw image found in preflight evidence."; fi
  mkdir -p "$PREFLIGHT_ROOT"
  printf '%s\n' "${dir#"$REPO/"}" >"$PREFLIGHT_ROOT/GATE1-STEP07-PREFLIGHT-LAST-RUN.txt"
  printf '%s\n' "${dir#"$REPO/"}" >"$PREFLIGHT_LATEST"
  trap - EXIT INT TERM
  pass "Step 1.07 compatibility-aware preflight passed."
  pass "Evidence: ${dir#"$REPO/"}"
  pass "No model/provider call occurred and certification has not started."
}

restore_snapshot(){
  local snapshot="$1"
  (cd "$DRUPAL" && ddev snapshot restore "$snapshot" >/dev/null && ddev drush cr >/dev/null && ddev snapshot --cleanup --name "$snapshot" -y >/dev/null)
}

cleanup_certification(){
  local rc=$?
  # Avoid recursive EXIT handling while recovery executes.
  trap - EXIT INT TERM
  if [[ "$CERT_SNAPSHOT_CREATED" -eq 1 && "$CERT_RESTORED" -eq 0 ]]; then
    if restore_snapshot "$CERT_SNAPSHOT"; then
      CERT_RESTORED=1
    else
      rc=1
    fi
  fi
  if [[ "$CERT_SNAPSHOT_CREATED" -eq 0 || "$CERT_RESTORED" -eq 1 ]]; then
    rm -f "$ACTIVE"
  else
    printf '[ERROR] Automatic certification restore failed; active recovery pointer retained at %s\n' "${ACTIVE#"$REPO/"}" >&2
    printf '[ERROR] Recovery snapshot remains recorded in %s\n' "${CERT_GATE#"$REPO/"}/snapshot-name.txt" >&2
  fi
  if [[ $rc -ne 0 ]]; then
    printf '[ERROR] Failed certification retained at %s\n' "${CERT_GATE#"$REPO/"}" >&2
  fi
  exit "$rc"
}

certify(){
  verify_preflight_retained
  [[ ! -e "$ACTIVE" ]] || fail "A Step 1.07 certification run is already active."
  module_enabled && fail "Certification must begin from module-disabled seeded-clean state."
  local gate_id="gate1-step07-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  # Reuse the exact frozen Step 1.05 run-id shape; Step 1.05 rejects extra segments.
  local run_id="drupal_ai-$(date -u +%Y%m%dT%H%M%SZ)-$(printf '%04x' "$$")"
  [[ "$run_id" =~ ^drupal_ai-[0-9]{8}T[0-9]{6}Z-[a-z0-9]{4,12}$ ]] || fail "Generated certification run ID violates the frozen Drupal AI pattern."
  local gate="$CERT_ROOT/$gate_id" result="$RESULT_ROOT/$run_id" snapshot="gate1-step07-pre-$gate_id"
  CERT_GATE="$gate"
  CERT_RESULT="$result"
  CERT_SNAPSHOT="$snapshot"
  CERT_SNAPSHOT_CREATED=0
  CERT_RESTORED=0
  mkdir -p "$gate" "$RESULT_ROOT"; printf '%s\n' "${gate#"$REPO/"}" >"$ACTIVE"
  trap cleanup_certification EXIT INT TERM
  runfull >"$gate/pre-cert-full.json"; run05 snapshot >"$gate/pre-cert-reduced.json"
  "$PYTHON" - "$gate/pre-cert-full.json" "$gate/pre-cert-reduced.json" <<'PY'
import json,sys
f=json.load(open(sys.argv[1]));r=json.load(open(sys.argv[2]))
if f.get('article_count')!=20 or f.get('suggestion_count')!=0 or f.get('article_source_sha256')!='877cd888fa41eb660b3e3cc0461bee04c0b92bef7e8f2f63fc56d9ec77adde32':raise SystemExit('[ERROR] pre-cert full state differs')
if r.get('seeded_clean') is not True or r.get('article_source_sha256')!='f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17':raise SystemExit('[ERROR] pre-cert reduced state differs')
PY
  (cd "$DRUPAL" && ddev snapshot --name "$snapshot" >/dev/null); CERT_SNAPSHOT_CREATED=1
  printf '%s\n' "$snapshot" >"$gate/snapshot-name.txt"
  (cd "$DRUPAL" && ddev drush en agentic_harness_drupal_ai -y >/dev/null && ddev drush cr >/dev/null)
  info "Running existing Step 1.05 model-free runtime preflight..."; run05 preflight >"$gate/runtime-preflight.json"
  info "Starting fresh certification batch (first six model calls)..."; run05 start "$run_id" >"$gate/start-result.json"
  run05 snapshot >"$gate/interrupted-state.json"
  info "Continuing same fresh certification run at sequence 7..."; run05 resume >"$gate/resume-result.json"
  run05 export >"$gate/runtime-export.json"; run05 snapshot >"$gate/completed-state.json"
  "$PYTHON" "$EVIDENCE_AUDITOR" build-results --gate "$gate" --result "$result"
  info "Replaying all 12 recommendations through the certified submit adapter with model calls blocked..."; run07 replay >"$gate/replay.json"
  info "Reading all 12 recommendation statuses with model calls blocked..."; run07 status-all >"$gate/status-reads.json"
  runfull >"$gate/post-batch-full.json"; run05 snapshot >"$gate/post-batch-reduced.json"
  "$PYTHON" - "$gate/pre-cert-full.json" "$gate/post-batch-full.json" "$gate/pre-cert-reduced.json" "$gate/post-batch-reduced.json" "$gate/source-non-mutation.json" <<'PY'
import json,sys
bf,af,br,ar,out=map(str,sys.argv[1:])
a=json.load(open(bf));b=json.load(open(af));c=json.load(open(br));d=json.load(open(ar))
v={"schema_version":1,"full_projection_before":a.get('article_source_sha256'),"full_projection_after":b.get('article_source_sha256'),"full_projection_unchanged":a.get('article_source_sha256')==b.get('article_source_sha256')=='877cd888fa41eb660b3e3cc0461bee04c0b92bef7e8f2f63fc56d9ec77adde32',"reduced_projection_before":c.get('article_source_sha256'),"reduced_projection_after":d.get('article_source_sha256'),"reduced_projection_unchanged":c.get('article_source_sha256')==d.get('article_source_sha256')=='f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17'}
if not v['full_projection_unchanged'] or not v['reduced_projection_unchanged']:raise SystemExit('[ERROR] source projection changed during fresh certification')
open(out,'w').write(json.dumps(v,indent=2,sort_keys=True)+'\n')
PY
  "$PYTHON" - "$STEP06_DIR/summary.json" "$STEP06_DIR/reviewer-decisions.json" "$gate/review-lineage-reference.json" <<'PY'
import hashlib,json,sys
s=json.load(open(sys.argv[1]));d=json.load(open(sys.argv[2]));out=sys.argv[3]
v={"schema_version":1,"step06_run_id":"gate1-step06-20260808T231216Z-2188911","review_decision_count":s.get('review_decision_count'),"review_revision_count":s.get('review_revision_count'),"sequence_12_review_workflow":s.get('sequence_12_review_workflow'),"reviewer_decisions_sha256":hashlib.sha256(open(sys.argv[2],'rb').read()).hexdigest(),"human_review_recreated_in_step07":False}
open(out,'w').write(json.dumps(v,indent=2,sort_keys=True)+'\n')
PY
  restore_snapshot "$snapshot"; CERT_RESTORED=1
  runfull >"$gate/post-restore-full.json"; run05 snapshot >"$gate/post-restore-reduced.json"
  module_enabled && fail "Snapshot restoration left custom Drupal AI module enabled."
  "$PYTHON" "$EVIDENCE_AUDITOR" audit --repo "$REPO" --gate "$gate" --result "$result" >"$gate/certification-audit.json"
  "$PYTHON" "$FINALIZER" --repo "$REPO" --gate "$gate" --result "$result" >"$gate/finalize.json"
  # Re-run audit after finalizer writes freeze/handoff/status artifacts.
  "$PYTHON" "$EVIDENCE_AUDITOR" audit --repo "$REPO" --gate "$gate" --result "$result" >"$gate/final-audit.json"
  if rg -n -i 'sk-[A-Za-z0-9_-]{20,}|data:image/|Authorization[[:space:]]*:|Basic[[:space:]]+[A-Za-z0-9+/]{16,}={0,2}' "$gate" "$result" >/dev/null; then fail "Potential secret/raw image found in certification evidence."; fi
  (cd "$gate" && find . -type f ! -name package-files-sha256.txt -printf '%P\n' | sort | xargs sha256sum >package-files-sha256.txt)
  (cd "$result" && find . -type f -printf '%P\n' | sort | xargs sha256sum >result-files-sha256.txt)
  printf '%s\n' "${gate#"$REPO/"}" >"$CERT_ROOT/GATE1-STEP07-LAST-RUN.txt"
  printf '%s\n' "${gate#"$REPO/"}" >"$CERT_ROOT/GATE1-STEP07-LATEST.txt"
  rm -f "$ACTIVE"; trap - EXIT INT TERM
  pass "Gate 1 Step 1.07 certification completed and restored seeded-clean."
  pass "Certification evidence: ${gate#"$REPO/"}"
  pass "Fresh results: ${result#"$REPO/"}"
  pass "Stop before commit/push for evidence and diff review."
}

salvage(){
  local gate_id="${2:-}"
  [[ -n "$gate_id" ]] || fail "Usage: salvage GATE_RUN_ID"
  verify_preflight_retained
  [[ ! -e "$ACTIVE" ]] || fail "Cannot salvage while an active certification pointer exists."
  module_enabled && fail "Salvage requires the already-restored module-disabled state."
  [[ "$gate_id" =~ ^gate1-step07-[0-9]{8}T[0-9]{6}Z-[0-9]+$ ]] || fail "Salvage gate ID has unexpected shape."
  local gate="$CERT_ROOT/$gate_id"
  [[ -d "$gate" ]] || fail "Failed certification gate directory is unavailable: $gate_id"
  [[ ! -s "$CERT_ROOT/GATE1-STEP07-LATEST.txt" ]] || fail "A passing Step 1.07 certification is already promoted."
  local run_id
  run_id="$($PYTHON - "$gate/runtime-export.json" <<'PY_SALVAGE_RUNID'
import json,sys
v=json.load(open(sys.argv[1],encoding='utf-8'))
print(v['state']['run_id'])
PY_SALVAGE_RUNID
)"
  [[ "$run_id" =~ ^drupal_ai-[0-9]{8}T[0-9]{6}Z-[a-z0-9]{4,12}$ ]] || fail "Retained runtime run ID violates the frozen Drupal AI pattern."
  local result="$RESULT_ROOT/$run_id"
  [[ -d "$result" ]] || fail "Fresh result directory is unavailable: ${result#"$REPO/"}"

  local tmp
  tmp="$(mktemp -d)"
  runfull >"$tmp/full.json"
  run05 snapshot >"$tmp/reduced.json"
  cmp -s "$tmp/full.json" "$gate/post-restore-full.json" || { rm -rf "$tmp"; fail "Current full Drupal projection differs from the failed run's restored state."; }
  cmp -s "$tmp/reduced.json" "$gate/post-restore-reduced.json" || { rm -rf "$tmp"; fail "Current reduced Drupal projection differs from the failed run's restored state."; }
  rm -rf "$tmp"

  "$PYTHON" - "$gate/audit-repair-v1.0.3.json" "$gate_id" "$run_id" <<'PY_SALVAGE_NOTE'
import json,sys
from datetime import datetime,timezone
out,gate_id,run_id=sys.argv[1:]
v={
  "schema_version":1,
  "status":"audit_repair",
  "gate_run_id":gate_id,
  "batch_run_id":run_id,
  "failed_package_version":"1.0.2",
  "repair_package_version":"1.0.3",
  "original_terminal_error":"Fresh certification start did not stop after six calls",
  "classification":"auditor_field_mismatch",
  "incorrect_v1_0_2_assertion":"start-result.json.model_call_count_total == 6",
  "corrected_start_evidence_fields":["provider_request_count","agent_request_count","recommendation_count","pending_status_count","failure_injection_fired","failure_after_sequence","failure_before_sequence","resume_at_sequence"],
  "model_rerun_performed":False,
  "runtime_artifacts_rewritten":False,
  "recorded_at":datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
}
open(out,'w',encoding='utf-8').write(json.dumps(v,indent=2,sort_keys=True)+'\n')
PY_SALVAGE_NOTE

  info "Re-auditing retained certification evidence with corrected v1.0.3 assertions; no model calls..."
  "$PYTHON" "$EVIDENCE_AUDITOR" audit --repo "$REPO" --gate "$gate" --result "$result" >"$gate/certification-audit.json"
  info "Retained model-backed evidence passed corrected audit. Finalizing Gate 1 without re-running the model..."
  "$PYTHON" "$FINALIZER" --repo "$REPO" --gate "$gate" --result "$result" >"$gate/finalize.json"
  "$PYTHON" "$EVIDENCE_AUDITOR" audit --repo "$REPO" --gate "$gate" --result "$result" >"$gate/final-audit.json"
  if rg -n -i 'sk-[A-Za-z0-9_-]{20,}|data:image/|Authorization[[:space:]]*:|Basic[[:space:]]+[A-Za-z0-9+/]{16,}={0,2}' "$gate" "$result" >/dev/null; then fail "Potential secret/raw image found in salvaged certification evidence."; fi
  (cd "$gate" && find . -type f ! -name package-files-sha256.txt -printf '%P\n' | sort | xargs sha256sum >package-files-sha256.txt)
  (cd "$result" && find . -type f ! -name result-files-sha256.txt -printf '%P\n' | sort | xargs sha256sum >result-files-sha256.txt)
  printf '%s\n' "${gate#"$REPO/"}" >"$CERT_ROOT/GATE1-STEP07-LAST-RUN.txt"
  printf '%s\n' "${gate#"$REPO/"}" >"$CERT_ROOT/GATE1-STEP07-LATEST.txt"
  pass "Gate 1 Step 1.07 retained certification was salvaged without new model calls."
  pass "Certification evidence: ${gate#"$REPO/"}"
  pass "Fresh results: ${result#"$REPO/"}"
  pass "v1.0.2 audit failure preserved in audit-repair-v1.0.3.json. Stop before commit/push for evidence review."
}

status(){
  if [[ -s "$CERT_ROOT/GATE1-STEP07-LATEST.txt" ]]; then cat "$REPO/$(<"$CERT_ROOT/GATE1-STEP07-LATEST.txt")/final-audit.json"; return; fi
  if [[ -s "$PREFLIGHT_LATEST" ]]; then cat "$REPO/$(<"$PREFLIGHT_LATEST")/summary.md"; return; fi
  printf 'Step 1.07 has no retained preflight or certification yet.\n'
}

audit(){
  verify_installed
  [[ -s "$CERT_ROOT/GATE1-STEP07-LATEST.txt" ]] || fail "No passing Step 1.07 certification pointer exists."
  local gate="$REPO/$(<"$CERT_ROOT/GATE1-STEP07-LATEST.txt")"
  local run_id; run_id="$($PYTHON - "$gate/certification-audit.json" <<'PY'
import json,sys;print(json.load(open(sys.argv[1]))['run_id'])
PY
)"
  local result="$RESULT_ROOT/$run_id"
  (cd "$gate" && sha256sum -c package-files-sha256.txt >/dev/null) || fail "Certification evidence checksum failed."
  (cd "$result" && sha256sum -c result-files-sha256.txt >/dev/null) || fail "Fresh result checksum failed."
  local tmp; tmp="$(mktemp -d)"; trap "rm -rf -- $(printf '%q' "$tmp")" EXIT
  runfull >"$tmp/full.json"; run05 snapshot >"$tmp/reduced.json"
  cmp -s "$tmp/full.json" "$gate/post-restore-full.json" || fail "Current full Drupal projection differs from certified restored state."
  cmp -s "$tmp/reduced.json" "$gate/post-restore-reduced.json" || fail "Current reduced Drupal projection differs from certified restored state."
  "$PYTHON" "$EVIDENCE_AUDITOR" audit --repo "$REPO" --gate "$gate" --result "$result" >/dev/null
  [[ "$(sha256sum "$REPO/shared/contracts/GATE1-DRUPAL-AI-FREEZE.json" | awk '{print $1}')" == "$(awk '{print $1}' "$REPO/shared/contracts/GATE1-DRUPAL-AI-FREEZE.sha256")" ]] || fail "Gate 1 freeze digest changed."
  pass "Gate 1 Step 1.07 post-certification audit passed."
}

restore(){
  [[ -s "$ACTIVE" ]] || fail "No active Step 1.07 certification pointer exists."
  local gate="$REPO/$(<"$ACTIVE")" snapshot_file="$REPO/$(<"$ACTIVE")/snapshot-name.txt"
  [[ -s "$snapshot_file" ]] || fail "Active certification snapshot pointer unavailable; inspect manually."
  restore_snapshot "$(<"$snapshot_file")"; rm -f "$ACTIVE"; pass "Active Step 1.07 certification restored to its pre-run snapshot."
}

verify_installed
case "$MODE" in
 preflight) preflight ;;
 certify) certify ;;
 status) status ;;
 audit) audit ;;
 salvage) salvage "$@" ;;
 restore) restore ;;
 *) fail "Usage: bash scripts/run-gate1-step07-drupal-ai-certification-and-handoff.sh {preflight|certify|status|audit|salvage GATE_RUN_ID|restore}" ;;
esac
