#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRUPAL="$REPO/drupal"
PYTHON="$REPO/langchain/.venv/bin/python"
CORE="$REPO/langchain/agentic_harness_langgraph/batch_runner.py"
AUDITOR="$REPO/scripts/gate2a_step08_audit.py"
STATE="$REPO/scripts/gate2a_step08_state.py"
BRANCH="gate-2a-step08-langgraph-fresh-batch-and-continuation"
EXPECTED_HEAD="e80d8c726df5758b1b0e5bad02b5b5e75f4e612d"
RESULT_ROOT="$REPO/evidence/results/langgraph"
GATE_ROOT="$REPO/evidence/gates/gate-2a/fresh-batch"
RUNTIME_ROOT="$REPO/langchain/.gate2a-runtime"
CREDENTIALS="$DRUPAL/.secrets/phase0-step7-accounts.txt"
LAST="$GATE_ROOT/GATE2A-STEP08-LAST-RUN.txt"
MIDPOINT="$GATE_ROOT/GATE2A-STEP08-MIDPOINT.txt"
FAILED="$GATE_ROOT/GATE2A-STEP08-FAILED-RUNS.txt"
CANDIDATE="$GATE_ROOT/GATE2A-STEP08-CANDIDATE.txt"
LATEST="$GATE_ROOT/GATE2A-STEP08-LATEST.txt"
START_AUTH_VALUE="authorize-step2a08-calls-1-6"
RESUME_AUTH_PREFIX="authorize-step2a08-calls-7-12:"
SALVAGE_RUN_ID="langgraph-20260810T231915Z-0027cd3e"
LIVE_TRAP_ARMED=0
LIVE_RUN_REL=""
LIVE_RUN_ID=""
LIVE_PHASE=""
LIVE_SNAPSHOT=""
LIVE_BEFORE_SHA=""
RESTORE_ATTEMPTED=false
RESTORE_VERIFIED=false
SNAPSHOT_CLEANED=false
RESTORE_STATE_SHA=""
LIVE_RESTORED_ALREADY=false
LIVE_RUNTIME_DB_SHA=""
MARK_FAILURE_RC=1

fail(){ printf '[ERROR] %s\n' "$*" >&2; exit 1; }
pass(){ printf '[PASS] %s\n' "$*"; }
info(){ printf '[INFO] %s\n' "$*"; }

latest_secret(){
  local key="$1"
  awk -v key="$key" 'index($0,key "=")==1 { value=substr($0,length(key)+2) } END { if(value!="") print value }' "$CREDENTIALS"
}
resolve_site_url(){
  local value
  value="$(cd "$DRUPAL" && ddev exec printenv DDEV_PRIMARY_URL 2>/dev/null | tr -d '\r' | grep -Eo 'https?://[^[:space:]]+' | tail -n 1 || true)"
  [[ -n "$value" ]] || fail "Unable to resolve DDEV_PRIMARY_URL"
  printf '%s' "${value%/}"
}
seeded_clean(){
  (cd "$DRUPAL" && bash scripts/run-phase0-step10.sh audit >/dev/null)
}
snapshot_json(){
  local out="$1"
  (
    cd "$DRUPAL"
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
      ddev drush --quiet php:script scripts/gate1-step03-adapter-exercise.php -- snapshot
  ) >"$out"
}
canonical_json_sha(){
  "$PYTHON" - "$1" <<'PY'
import hashlib,json,sys
p=sys.argv[1]
v=json.load(open(p,encoding="utf-8"))
b=json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
print(hashlib.sha256(b).hexdigest())
PY
}
current_drupal_sha(){
  local tmp sha
  tmp="$(mktemp)"
  if ! snapshot_json "$tmp"; then
    rm -f "$tmp"
    return 1
  fi
  sha="$(canonical_json_sha "$tmp")" || { rm -f "$tmp"; return 1; }
  rm -f "$tmp"
  printf '%s' "$sha"
}
restore_snapshot_only(){
  local name="$1"
  (
    cd "$DRUPAL"
    ddev snapshot restore "$name" >/dev/null &&
    ddev drush cr >/dev/null
  )
}
cleanup_snapshot(){
  local name="$1"
  (cd "$DRUPAL" && ddev snapshot --cleanup --name "$name" -y >/dev/null)
}
attempt_verified_restore(){
  local name="$1" expected_sha="$2" got_sha=""
  RESTORE_ATTEMPTED=true
  RESTORE_VERIFIED=false
  SNAPSHOT_CLEANED=false
  RESTORE_STATE_SHA=""
  [[ -n "$name" && -n "$expected_sha" ]] || return 1
  if ! restore_snapshot_only "$name"; then
    return 1
  fi
  if ! seeded_clean; then
    return 1
  fi
  got_sha="$(current_drupal_sha)" || return 1
  [[ "$got_sha" == "$expected_sha" ]] || return 1
  RESTORE_STATE_SHA="$got_sha"
  RESTORE_VERIFIED=true
  if ! cleanup_snapshot "$name"; then
    return 1
  fi
  SNAPSHOT_CLEANED=true
  return 0
}
write_manifest(){
  local dir="$1"
  (
    cd "$dir"
    find . -maxdepth 1 -type f ! -name package-files-sha256.txt -printf '%f\n' |
      sort | xargs -r sha256sum > package-files-sha256.txt
  )
}
append_failed(){
  local rel="$1"
  mkdir -p "$GATE_ROOT"; touch "$FAILED"
  grep -Fxq "$rel" "$FAILED" || printf '%s\n' "$rel" >>"$FAILED"
}
validate_worktree_scope(){
  local p
  git -C "$REPO" diff --cached --quiet || fail "Step 2A.08 must not have staged changes before certification."
  while IFS= read -r p; do
    [[ -n "$p" ]] || continue
    case "$p" in
      AGENTS.md|PLAN.md|README.md|docs/CURRENT-STATUS.md|langchain/agentic_harness_langgraph/batch_runner.py) ;;
      *) fail "Unexpected tracked modification during Step 2A.08: $p" ;;
    esac
  done < <(git -C "$REPO" diff --name-only "$EXPECTED_HEAD" --)
  while IFS= read -r p; do
    [[ -n "$p" ]] || continue
    case "$p" in
      docs/gates/GATE-2A-STEP08-LANGGRAPH-FRESH-BATCH-AND-CONTINUATION.md|      scripts/gate2a_step08_audit.py|scripts/gate2a_step08_state.py|      scripts/run-gate2a-step08-langgraph-fresh-batch-and-continuation.sh|      evidence/results/langgraph/langgraph-*|evidence/gates/gate-2a/fresh-batch/*) ;;
      *) fail "Unexpected untracked Step 2A.08 path: $p" ;;
    esac
  done < <(git -C "$REPO" ls-files --others --exclude-standard)
}
critical_source_valid(){
  local rel
  for rel in     langchain/agentic_harness_langgraph/state.py     langchain/agentic_harness_langgraph/tools.py     langchain/agentic_harness_langgraph/vertical_slice.py     scripts/gate2a_step07_schema_validate.py     shared/contracts/GATE2A-LANGGRAPH-EVIDENCE-SCHEMA-MAP.json
  do
    git -C "$REPO" diff --quiet "$EXPECTED_HEAD" -- "$rel" || fail "Merged Step 2A.07 source changed outside the reviewed Step 2A.08 repair: $rel"
  done
}
require_branch_head(){
  [[ "$(git -C "$REPO" branch --show-current)" == "$BRANCH" ]] || fail "Expected branch $BRANCH."
  [[ "$(git -C "$REPO" rev-parse HEAD)" == "$EXPECTED_HEAD" ]] || fail "Expected uncommitted Step 2A.08 install on $EXPECTED_HEAD."
}
preflight_static_core(){
  require_branch_head
  git -C "$REPO" fetch origin main >/dev/null 2>&1 || fail "Unable to refresh origin/main before Step 2A.08 boundary."
  [[ "$(git -C "$REPO" rev-parse origin/main)" == "$EXPECTED_HEAD" ]] || fail "origin/main advanced from the reviewed Step 2A.07 base; re-review required before spending calls."
  validate_worktree_scope
  critical_source_valid
  [[ -x "$PYTHON" && -f "$CORE" && -f "$AUDITOR" && -f "$STATE" ]] || fail "Step 2A.08 implementation/runtime incomplete."
  PYTHONPATH="$REPO/langchain:$REPO${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" - <<'PY'
import importlib.metadata as md
expected={"langchain":"1.3.14","langgraph":"1.2.10","langgraph-checkpoint-sqlite":"3.1.1"}
for name,want in expected.items():
    got=md.version(name)
    assert got==want,(name,got,want)
from agentic_harness_langgraph.batch_runner import TARGET_COUNT,BOUNDARY_AFTER_SEQUENCE,RESUME_AT_SEQUENCE,MODEL_ID,TEMPERATURE
assert TARGET_COUNT==12
assert BOUNDARY_AFTER_SEQUENCE == 6
assert RESUME_AT_SEQUENCE == 7
assert MODEL_ID=="gpt-4.1-mini-2025-04-14"
assert TEMPERATURE==0.0
print("[PASS] Pinned Step 2A.08 runtime and live-path constants passed.")
PY
  "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state active
  pass "Step 2A.08 static invariant preflight passed."
}
require_gate1_restored_state(){
  bash "$REPO/scripts/run-gate1-step07-drupal-ai-certification-and-handoff.sh" audit >/dev/null \
    || fail "Gate 1 restored-state regression audit failed."
  pass "Gate 1 restored-state regression audit passed."
}
preflight_static(){
  preflight_static_core
  pass "Step 2A.08 static preflight passed (lifecycle-neutral; no restored-state Gate 1 audit)."
}
preflight_live(){
  preflight_static_core
  [[ -f "$CREDENTIALS" ]] || fail "Local Drupal credentials file is missing."
  [[ -n "${OPENAI_API_KEY:-}" ]] || fail "OPENAI_API_KEY is required for Step 2A.08 live execution."
  [[ -z "${OPENAI_CANDIDATE_MODEL:-}" && -z "${CREWAI_CANDIDATE_MODEL:-}" ]] || fail "Candidate-model override variables must remain unset; Step 2A.08 uses the frozen model internally."
  [[ ! -e "$LATEST" ]] || fail "Step 2A.08 is already certified."
}
export_drupal_env(){
  local pw
  pw="$(latest_secret agent_bot)"
  [[ -n "$pw" ]] || fail "agent_bot credential is empty."
  export GATE2A_DRUPAL_USERNAME="agent_bot"
  export GATE2A_DRUPAL_PASSWORD="$pw"
  export GATE2A_DRUPAL_BASE_URL="$(resolve_site_url)"
}
clear_drupal_env(){
  unset GATE2A_DRUPAL_PASSWORD GATE2A_DRUPAL_USERNAME GATE2A_DRUPAL_BASE_URL
}
mark_failure(){
  local run_rel="$1" run_id="$2" phase="$3" rc="$4" message="$5" snapshot_name="${6:-}" before_sha="${7:-}" restored_already="${8:-false}"
  local run_dir="$REPO/$run_rel" gate_dir="$GATE_ROOT/$run_id" sqlite="$RUNTIME_ROOT/$run_id.sqlite" control="$RUNTIME_ROOT/$run_id.step08-control.json"
  local db_sha="" final_rc="$rc" control_retained=false
  disarm_live_trap
  set +e
  clear_drupal_env
  mkdir -p "$gate_dir" "$run_dir"
  [[ -f "$sqlite" ]] && db_sha="$(sha256sum "$sqlite" | awk '{print $1}')"
  [[ -n "$db_sha" ]] || db_sha="$LIVE_RUNTIME_DB_SHA"
  if [[ -z "$snapshot_name" || -z "$before_sha" ]] && [[ -s "$control" ]]; then
    read -r snapshot_name before_sha < <("$PYTHON" - "$control" <<'PY'
import json,sys
v=json.load(open(sys.argv[1]))
print(v.get("snapshot_name", ""), v.get("before_state_sha256", ""))
PY
)
  fi
  RESTORE_ATTEMPTED=false; RESTORE_VERIFIED=false; SNAPSHOT_CLEANED=false
  if [[ "$restored_already" == true ]]; then
    RESTORE_ATTEMPTED=true; RESTORE_VERIFIED=true; SNAPSHOT_CLEANED=true
  elif [[ -n "$snapshot_name" ]]; then
    if ! attempt_verified_restore "$snapshot_name" "$before_sha"; then
      final_rc=90
      control_retained=true
    fi
  fi
  rm -f "$sqlite"
  if [[ "$RESTORE_VERIFIED" == true && "$SNAPSHOT_CLEANED" == true ]]; then
    rm -f "$control"
    control_retained=false
  elif [[ -s "$control" ]]; then
    control_retained=true
  fi
  "$PYTHON" - "$gate_dir/failure.json" "$run_id" "$run_rel" "$phase" "$rc" "$message" "$db_sha" "$snapshot_name" "$RESTORE_ATTEMPTED" "$RESTORE_VERIFIED" "$SNAPSHOT_CLEANED" "$control_retained" <<'PY'
import json,sys
(path,run_id,rel,phase,rc,msg,dbsha,snap,attempted,verified,cleaned,control)=sys.argv[1:]
b=lambda x: x.lower()=="true"
json.dump({"schema_version":1,"status":"failed","run_id":run_id,"result_path":rel,
           "phase":phase,"trigger_exit_code":int(rc),"message":msg,
           "runtime_db_sha256_before_disposal":dbsha or None,"runtime_db_retained":False,
           "snapshot_name":snap or None,"restore_attempted":b(attempted),
           "restore_verified":b(verified),"snapshot_cleaned":b(cleaned),
           "recovery_control_retained":b(control),"model_or_semantic_retry_authorized":False},
          open(path,"w"),indent=2,sort_keys=True)
open(path,"a").write("\n")
PY
  write_manifest "$gate_dir"
  append_failed "$run_rel"
  write_manifest "$run_dir"
  if [[ "$RESTORE_VERIFIED" != true ]]; then
    printf '[ERROR] Drupal exact pre-run restoration was NOT verified. Snapshot/control are preserved when available; manual recovery is required before any further live action.\n' >&2
  fi
  printf '[STOP] Step 2A.08 failed during %s; retained evidence at %s. Do not rerun or resume without human review/package repair.\n' "$phase" "$run_rel" >&2
  MARK_FAILURE_RC="$final_rc"
  set -e
  return 0
}
arm_live_trap(){
  LIVE_RUN_REL="$1"; LIVE_RUN_ID="$2"; LIVE_PHASE="$3"; LIVE_SNAPSHOT="$4"; LIVE_BEFORE_SHA="$5"
  LIVE_RESTORED_ALREADY=false
  LIVE_RUNTIME_DB_SHA=""
  LIVE_TRAP_ARMED=1
  trap 'live_abort ERR $?' ERR
  trap 'live_abort INT 130' INT
  trap 'live_abort TERM 143' TERM
}
disarm_live_trap(){
  LIVE_TRAP_ARMED=0
  trap - ERR INT TERM
}
live_abort(){
  local kind="$1" rc="$2" final_rc
  final_rc="$rc"
  trap - ERR INT TERM
  if [[ "$LIVE_TRAP_ARMED" -eq 1 && -n "$LIVE_RUN_REL" ]]; then
    mark_failure "$LIVE_RUN_REL" "$LIVE_RUN_ID" "${LIVE_PHASE,,}-${kind,,}" "$rc" "Unexpected wrapper ${kind} during ${LIVE_PHASE}." "$LIVE_SNAPSHOT" "$LIVE_BEFORE_SHA" "$LIVE_RESTORED_ALREADY"
    final_rc="$MARK_FAILURE_RC"
  fi
  exit "$final_rc"
}

start_live(){
  preflight_live
  require_gate1_restored_state
  [[ "${GATE2A_STEP08_START_AUTHORIZATION:-}" == "$START_AUTH_VALUE" ]] || fail "Explicit human authorization for Step 2A.08 calls 1-6 is missing."
  [[ ! -e "$LAST" && ! -e "$MIDPOINT" && ! -e "$CANDIDATE" ]] || fail "A Step 2A.08 attempt already exists."
  [[ ! -s "$FAILED" ]] || fail "Retained Step 2A.08 failure exists; reviewed repair required."
  mkdir -p "$RESULT_ROOT" "$GATE_ROOT" "$RUNTIME_ROOT"
  seeded_clean
  local stamp suffix run_id run_rel run_dir gate_dir control snapshot_name before_tmp midpoint_tmp before_sha midpoint_sha rc
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  suffix="$(printf '%08x' "$$")"
  run_id="langgraph-${stamp}-${suffix}"
  run_rel="evidence/results/langgraph/$run_id"
  run_dir="$REPO/$run_rel"
  gate_dir="$GATE_ROOT/$run_id"
  control="$RUNTIME_ROOT/$run_id.step08-control.json"
  snapshot_name="gate2a-step08-pre-${stamp}-${suffix}"
  mkdir -p "$gate_dir"
  before_tmp="$(mktemp)"
  snapshot_json "$before_tmp"
  before_sha="$(canonical_json_sha "$before_tmp")"
  rm -f "$before_tmp"
  info "Creating exact pre-run DDEV snapshot..."
  if ! (cd "$DRUPAL" && ddev snapshot --name "$snapshot_name" >/dev/null); then
    fail "Unable to create exact pre-run DDEV snapshot; no Step 2A.08 model call was started."
  fi
  # From this point forward any unexpected wrapper failure must restore and retain evidence.
  arm_live_trap "$run_rel" "$run_id" "START" "$snapshot_name" "$before_sha"
  "$PYTHON" - "$control" "$run_id" "$snapshot_name" "$before_sha" <<'PY'
import json,sys
p,run_id,snap,before=sys.argv[1:]
json.dump({"run_id":run_id,"snapshot_name":snap,"before_state_sha256":before},open(p,"w"),indent=2,sort_keys=True)
open(p,"a").write("\n")
PY
  printf '%s\n' "$run_rel" >"$LAST"
  export_drupal_env
  info "Executing authorized Step 2A.08 calls 1-6; the genuine LangGraph continuation interrupt must stop before target 7..."
  if PYTHONPATH="$REPO/langchain:$REPO${PYTHONPATH:+:$PYTHONPATH}" \
    "$PYTHON" "$CORE" --repo "$REPO" --evidence "$run_dir" --run-id "$run_id" --mode start; then
    rc=0
  else
    rc=$?
  fi
  clear_drupal_env
  if [[ "$rc" -ne 0 ]]; then
    mark_failure "$run_rel" "$run_id" "start" "$rc" "Live start core exited nonzero." "$snapshot_name" "$before_sha"
    return "$MARK_FAILURE_RC"
  fi
  if ! "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state active --run-dir "$run_rel" --phase midpoint; then
    mark_failure "$run_rel" "$run_id" "midpoint-audit" 41 "Midpoint candidate audit failed." "$snapshot_name" "$before_sha"
    return "$MARK_FAILURE_RC"
  fi
  midpoint_tmp="$(mktemp)"
  snapshot_json "$midpoint_tmp"
  midpoint_sha="$(canonical_json_sha "$midpoint_tmp")"
  rm -f "$midpoint_tmp"
  "$PYTHON" - "$control" "$midpoint_sha" <<'PY'
import json,sys
p,mid=sys.argv[1:]
v=json.load(open(p)); v["midpoint_state_sha256"]=mid
json.dump(v,open(p,"w"),indent=2,sort_keys=True); open(p,"a").write("\n")
PY
  "$PYTHON" - "$gate_dir/midpoint-summary.json" "$run_id" "$run_rel" "$before_sha" "$midpoint_sha" <<'PY'
import json,sys
p,run_id,rel,before,mid=sys.argv[1:]
json.dump({"schema_version":1,"status":"pass","phase":"midpoint","run_id":run_id,
           "result_path":rel,"completed_before_stop":[1,2,3,4,5,6],"resume_at_sequence":7,
           "model_calls_succeeded":6,"drupal_semantic_calls":{"find_images_needing_review":1,
           "get_image_context":18,"submit_recommendation":6,"get_recommendation_status":6},
           "before_state_sha256":before,"midpoint_state_sha256":mid,
           "snapshot_restored":False,"gate2c_failure_injection":False},open(p,"w"),indent=2,sort_keys=True)
open(p,"a").write("\n")
PY
  printf '%s\n' "$run_rel" >"$MIDPOINT"
  pass "Step 2A.08 midpoint passed after exactly 6 successful model calls."
  pass "Midpoint evidence: $run_rel"
  pass "Same run/thread is persisted and interrupted before sequence 7."
  printf '[STOP] Inspect midpoint evidence and Drupal stability before authorizing calls 7-12. Do not run start again.\n'
}
resume_live(){
  preflight_live
  [[ -s "$MIDPOINT" && -s "$LAST" ]] || fail "No passing Step 2A.08 midpoint exists."
  [[ ! -e "$CANDIDATE" ]] || fail "A passing Step 2A.08 candidate already exists."
  [[ ! -s "$FAILED" ]] || fail "Retained Step 2A.08 failure exists; reviewed repair required."
  local run_rel run_id run_dir gate_dir control snapshot_name before_sha midpoint_sha current_tmp current_sha rc completed_tmp completed_sha after_tmp after_sha sqlite db_sha
  run_rel="$(<"$MIDPOINT")"
  [[ "$run_rel" == evidence/results/langgraph/langgraph-* ]] || fail "Midpoint pointer is invalid."
  [[ "$(<"$LAST")" == "$run_rel" ]] || fail "LAST and MIDPOINT pointers differ."
  run_id="${run_rel##*/}"
  [[ "${GATE2A_STEP08_RESUME_AUTHORIZATION:-}" == "${RESUME_AUTH_PREFIX}${run_id}" ]] || fail "Explicit run-bound human authorization for Step 2A.08 calls 7-12 is missing."
  run_dir="$REPO/$run_rel"
  gate_dir="$GATE_ROOT/$run_id"
  control="$RUNTIME_ROOT/$run_id.step08-control.json"
  sqlite="$RUNTIME_ROOT/$run_id.sqlite"
  [[ -s "$control" && -s "$sqlite" ]] || fail "Step 2A.08 continuation runtime state is missing."
  read -r snapshot_name before_sha midpoint_sha < <("$PYTHON" - "$control" <<'PY'
import json,sys
v=json.load(open(sys.argv[1]))
print(v["snapshot_name"],v["before_state_sha256"],v["midpoint_state_sha256"])
PY
)
  arm_live_trap "$run_rel" "$run_id" "RESUME" "$snapshot_name" "$before_sha"
  current_tmp="$(mktemp)"
  snapshot_json "$current_tmp"
  current_sha="$(canonical_json_sha "$current_tmp")"
  rm -f "$current_tmp"
  if [[ "$current_sha" != "$midpoint_sha" ]]; then
    mark_failure "$run_rel" "$run_id" "pre-resume-state-drift" 43 "Drupal state changed after the controlled midpoint." "$snapshot_name" "$before_sha"
    return "$MARK_FAILURE_RC"
  fi
  if ! "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state active --run-dir "$run_rel" --phase midpoint; then
    mark_failure "$run_rel" "$run_id" "pre-resume-midpoint-audit" 44 "Stored midpoint audit failed before resume." "$snapshot_name" "$before_sha"
    return "$MARK_FAILURE_RC"
  fi
  export_drupal_env
  info "Executing authorized Step 2A.08 calls 7-12 on the same run/thread..."
  if PYTHONPATH="$REPO/langchain:$REPO${PYTHONPATH:+:$PYTHONPATH}" \
    "$PYTHON" "$CORE" --repo "$REPO" --evidence "$run_dir" --run-id "$run_id" --mode resume; then
    rc=0
  else
    rc=$?
  fi
  clear_drupal_env
  if [[ "$rc" -ne 0 ]]; then
    mark_failure "$run_rel" "$run_id" "resume" "$rc" "Live resume core exited nonzero." "$snapshot_name" "$before_sha"
    return "$MARK_FAILURE_RC"
  fi
  completed_tmp="$(mktemp)"
  snapshot_json "$completed_tmp"
  completed_sha="$(canonical_json_sha "$completed_tmp")"
  rm -f "$completed_tmp"
  db_sha="$(sha256sum "$sqlite" | awk '{print $1}')"
  LIVE_RUNTIME_DB_SHA="$db_sha"
  info "Restoring and verifying exact pre-run DDEV snapshot after successful 12-target evidence capture..."
  if ! attempt_verified_restore "$snapshot_name" "$before_sha"; then
    mark_failure "$run_rel" "$run_id" "post-completion-restore" 45 "Exact pre-run DDEV snapshot restoration/verification failed." "$snapshot_name" "$before_sha"
    return "$MARK_FAILURE_RC"
  fi
  after_sha="$RESTORE_STATE_SHA"
  if [[ "$after_sha" != "$before_sha" ]]; then
    mark_failure "$run_rel" "$run_id" "post-completion-restore-hash" 47 "Post-run Drupal state does not match exact pre-run snapshot." "$snapshot_name" "$before_sha" true
    return "$MARK_FAILURE_RC"
  fi
  LIVE_RESTORED_ALREADY=true
  if ! bash "$REPO/scripts/run-gate1-step07-drupal-ai-certification-and-handoff.sh" audit >/dev/null; then
    mark_failure "$run_rel" "$run_id" "post-restore-gate1-regression" 48 "Gate 1 restored-state regression audit failed after exact Step 2A.08 restoration." "" "" true
    return "$MARK_FAILURE_RC"
  fi
  pass "Gate 1 restored-state regression audit passed after exact Drupal restoration."
  rm -f "$sqlite" "$control"
  "$PYTHON" - "$gate_dir/wrapper-summary.json" "$run_id" "$run_rel" "$before_sha" "$midpoint_sha" "$current_sha" "$completed_sha" "$after_sha" "$db_sha" <<'PY'
import json,sys
p,run_id,rel,before,mid,current,completed,after,dbsha=sys.argv[1:]
json.dump({"schema_version":1,"status":"pass","run_id":run_id,"result_path":rel,
           "before_state_sha256":before,"midpoint_state_sha256":mid,
           "pre_resume_state_sha256":current,"midpoint_state_unchanged_before_resume":current==mid,
           "completed_live_state_sha256":completed,"after_restore_state_sha256":after,
           "snapshot_restored":after==before,"restore_attempted":True,"restore_verified":True,
           "snapshot_cleaned":True,"runtime_db_sha256_before_disposal":dbsha,
           "runtime_db_retained":False,"model_calls_succeeded":12,
           "gate2c_failure_injection":False,"human_review_performed":False},open(p,"w"),indent=2,sort_keys=True)
open(p,"a").write("\n")
PY
  write_manifest "$run_dir"
  write_manifest "$gate_dir"
  if ! "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state active --run-dir "$run_rel" --phase candidate; then
    mark_failure "$run_rel" "$run_id" "candidate-audit" 42 "Completed-run candidate audit failed after verified Drupal restoration." "" "" true
    return "$MARK_FAILURE_RC"
  fi
  printf '%s\n' "$run_rel" >"$CANDIDATE"
  disarm_live_trap
  pass "Gate 2A Step 2A.08 12-target candidate passed."
  pass "Candidate evidence: $run_rel"
  pass "Successful model calls: 12 total; automatic/semantic retries: 0/0."
  pass "Controlled continuation: stop after 6, same run/thread resume at 7, duplicate count 0."
  pass "Drupal restored exactly to the pre-run snapshot after evidence capture."
  printf '[STOP] Inspect the candidate evidence before model-free certification. Do not run start/resume again.\n'
}
salvage(){
  preflight_static
  require_gate1_restored_state
  [[ -z "${OPENAI_API_KEY:-}" ]] || fail "Model-free salvage requires OPENAI_API_KEY unset."
  [[ -z "${GATE2A_STEP08_START_AUTHORIZATION:-}" && -z "${GATE2A_STEP08_RESUME_AUTHORIZATION:-}" ]] || fail "Model-free salvage requires live authorizations unset."
  local run_id="$SALVAGE_RUN_ID" run_rel="evidence/results/langgraph/$SALVAGE_RUN_ID"
  local run_dir="$RESULT_ROOT/$run_id" gate_dir="$GATE_ROOT/$run_id"
  [[ -s "$LAST" && "$(<"$LAST")" == "$run_rel" ]] || fail "LAST pointer differs from reviewed failed run."
  [[ -s "$MIDPOINT" && "$(<"$MIDPOINT")" == "$run_rel" ]] || fail "MIDPOINT pointer differs from reviewed failed run."
  [[ -s "$FAILED" ]] && grep -Fxq "$run_rel" "$FAILED" || fail "Reviewed failed-run registration is missing."
  [[ ! -e "$CANDIDATE" && ! -e "$LATEST" ]] || fail "Candidate/accepted pointer already exists."
  [[ ! -e "$RUNTIME_ROOT/$run_id.sqlite" && ! -e "$RUNTIME_ROOT/$run_id.step08-control.json" ]] || fail "Failed runtime artifacts unexpectedly remain."
  [[ -s "$gate_dir/failure.json" ]] || fail "Failure record missing."
  [[ ! -e "$run_dir/checkpoint-privacy-after-continuation-salvage.json" ]] || fail "Salvage privacy proof already exists."
  [[ ! -e "$gate_dir/salvage-wrapper-summary.json" ]] || fail "Salvage wrapper summary already exists."
  "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state active --run-dir "$run_rel" --phase salvage-source
  local before_sha midpoint_sha current_sha db_sha
  before_sha="$("$PYTHON" - "$gate_dir/midpoint-summary.json" <<'PY'
import json,sys
v=json.load(open(sys.argv[1])); print(v["before_state_sha256"])
PY
)"
  midpoint_sha="$("$PYTHON" - "$gate_dir/midpoint-summary.json" <<'PY'
import json,sys
v=json.load(open(sys.argv[1])); print(v["midpoint_state_sha256"])
PY
)"
  current_sha="$(current_drupal_sha)"
  [[ "$current_sha" == "$before_sha" ]] || fail "Drupal no longer equals the verified pre-run restored state."
  db_sha="$("$PYTHON" - "$gate_dir/failure.json" <<'PY'
import json,sys
v=json.load(open(sys.argv[1])); print(v["runtime_db_sha256_before_disposal"])
PY
)"
  "$PYTHON" - "$run_dir/checkpoint-privacy-after-continuation-salvage.json" "$run_id" "$db_sha" <<'PY'
import datetime,json,sys
p,run_id,dbsha=sys.argv[1:]
json.dump({
  "schema_version":1,
  "status":"pass",
  "run_id":run_id,
  "diagnosis":"privacy-report-self-match",
  "original_failed_privacy_report_preserved":True,
  "original_failed_pattern":"hidden_reasoning",
  "original_exact_ephemeral_value_hits_empty":True,
  "raw_evidence_scan_excluding_privacy_reports_passed":True,
  "actual_prohibited_content_found":False,
  "midpoint_sqlite_privacy_scan_passed":True,
  "runtime_db_sha256_before_disposal":dbsha,
  "runtime_db_rescan_performed":False,
  "runtime_db_disposed_by_verified_recovery":True,
  "runtime_db_rescan_limitation":"The verified failure-recovery path disposed the final SQLite runtime after recording its SHA-256; salvage therefore preserves that limitation rather than fabricating a rescan.",
  "scanner_repair":"checkpoint_privacy excludes its own checkpoint-privacy report files from evidence_bytes",
  "salvage_is_model_free":True,
  "recorded_at":datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00","Z"),
},open(p,"w"),indent=2,sort_keys=True); open(p,"a").write("\n")
PY
  "$PYTHON" - "$gate_dir/salvage-wrapper-summary.json" "$run_id" "$run_rel" "$before_sha" "$midpoint_sha" "$current_sha" "$db_sha" <<'PY'
import datetime,json,sys
p,run_id,rel,before,mid,after,dbsha=sys.argv[1:]
json.dump({
  "schema_version":1,"status":"pass","salvaged_candidate":True,
  "run_id":run_id,"result_path":rel,
  "original_live_execution_status":"failed-after-completion-privacy-check",
  "original_failure_preserved":True,
  "before_state_sha256":before,"midpoint_state_sha256":mid,
  "after_restore_state_sha256":after,
  "snapshot_restored":after==before,"restore_attempted":True,"restore_verified":after==before,
  "snapshot_cleaned":True,
  "runtime_db_sha256_before_disposal":dbsha,"runtime_db_retained":False,
  "model_calls_succeeded":12,"additional_model_calls_for_salvage":0,
  "gate2c_failure_injection":False,"human_review_performed":False,
  "recorded_at":datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00","Z"),
},open(p,"w"),indent=2,sort_keys=True); open(p,"a").write("\n")
PY
  write_manifest "$run_dir"
  write_manifest "$gate_dir"
  if ! "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state active --run-dir "$run_rel" --phase candidate; then
    rm -f "$run_dir/checkpoint-privacy-after-continuation-salvage.json" "$gate_dir/salvage-wrapper-summary.json"
    write_manifest "$run_dir"; write_manifest "$gate_dir"
    fail "Model-free salvage candidate audit failed; salvage artifacts rolled back."
  fi
  printf '%s\n' "$run_rel" >"${CANDIDATE}.tmp"; mv "${CANDIDATE}.tmp" "$CANDIDATE"
  pass "Gate 2A Step 2A.08 failed execution was truthfully retained and model-free evidence salvage passed."
  pass "Candidate evidence: $run_rel"
  pass "Successful model calls remain exactly 12; salvage added 0 model/provider calls and 0 Drupal semantic calls/mutations."
  pass "Drupal remains exactly restored to the pre-run state; original failed privacy report and FAILED-RUNS entry are preserved."
  printf '[STOP] Inspect the salvaged candidate evidence before model-free certification. Do not run start/resume.\n'
}
certify(){
  preflight_static
  require_gate1_restored_state
  [[ -s "$CANDIDATE" ]] || fail "No passing Step 2A.08 candidate exists."
  [[ ! -e "$LATEST" ]] || fail "Step 2A.08 is already certified."
  local run_rel
  run_rel="$(<"$CANDIDATE")"
  "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state active --run-dir "$run_rel" --phase candidate
  local backup
  backup="$(mktemp -d)"; mkdir -p "$backup/docs"
  cp "$REPO/AGENTS.md" "$backup/AGENTS.md"
  cp "$REPO/PLAN.md" "$backup/PLAN.md"
  cp "$REPO/README.md" "$backup/README.md"
  cp "$REPO/docs/CURRENT-STATUS.md" "$backup/docs/CURRENT-STATUS.md"
  rollback(){
    set +e
    cp "$backup/AGENTS.md" "$REPO/AGENTS.md"
    cp "$backup/PLAN.md" "$REPO/PLAN.md"
    cp "$backup/README.md" "$REPO/README.md"
    cp "$backup/docs/CURRENT-STATUS.md" "$REPO/docs/CURRENT-STATUS.md"
    rm -f "$LATEST" "${LATEST}.tmp"
    set -e
  }
  certify_abort(){
    local rc="$1"
    trap - ERR INT TERM
    rollback
    rm -rf "$backup"
    exit "$rc"
  }
  trap 'certify_abort $?' ERR
  trap 'certify_abort 130' INT
  trap 'certify_abort 143' TERM
  if ! "$PYTHON" "$STATE" --repo "$REPO" --state complete --run-dir "$run_rel"; then
    rollback; rm -rf "$backup"; fail "Step 2A.08 document-state certification failed."
  fi
  printf '%s\n' "$run_rel" >"${LATEST}.tmp"; mv "${LATEST}.tmp" "$LATEST"
  if ! "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state complete --run-dir "$run_rel" --phase candidate; then
    rollback; rm -rf "$backup"; fail "Step 2A.08 complete-state audit failed; certification rolled back."
  fi
  trap - ERR INT TERM
  rm -rf "$backup"
  git -C "$REPO" diff --check
  pass "Gate 2A Step 2A.08 certification passed without another model or Drupal semantic call."
  pass "Accepted evidence: $run_rel"
  printf '[STOP] Inspect evidence and diff before exact-scope staging or commit. Step 2A.09 remains locked.\n'
}
audit_complete(){
  [[ -s "$LATEST" ]] || fail "Step 2A.08 accepted pointer missing."
  local run_rel; run_rel="$(<"$LATEST")"
  "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state complete --run-dir "$run_rel" --phase candidate
}
case "$MODE" in
  preflight) preflight_static ;;
  start) start_live ;;
  resume) resume_live ;;
  salvage) salvage ;;
  certify) certify ;;
  audit) audit_complete ;;
  *) fail "Usage: bash scripts/run-gate2a-step08-langgraph-fresh-batch-and-continuation.sh {preflight|start|resume|salvage|certify|audit}" ;;
esac
