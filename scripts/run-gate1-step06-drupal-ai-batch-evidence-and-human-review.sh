#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
DRUPAL="$REPO/drupal"
BASELINE="27029bdcd2eaf57146fca4f2f0358035c5c9008d"
STEP05_GATE_ID="gate1-step05-20260808T020222Z-2121689"
BATCH_RUN_ID="drupal_ai-20260808T020222Z-205fd9"
STEP05_SOURCE_SHA="f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17"
GATE05_SOURCE_SHA="877cd888fa41eb660b3e3cc0461bee04c0b92bef7e8f2f63fc56d9ec77adde32"
GATE_ROOT="$REPO/evidence/gates/gate-1/batch-evidence"
PENDING_FILE="$GATE_ROOT/GATE1-STEP06-PENDING.txt"
LAST_FILE="$GATE_ROOT/GATE1-STEP06-LAST-RUN.txt"
LATEST_FILE="$GATE_ROOT/GATE1-STEP06-LATEST.txt"
STEP05_GATE_ROOT="$REPO/evidence/gates/gate-1/drupal-ai-batch-runner/$STEP05_GATE_ID"
RESULT_DIR="$REPO/evidence/results/drupal_ai/$BATCH_RUN_ID"
AUDITOR="$REPO/scripts/gate1_step06_evidence_audit.py"
FINALIZER="$REPO/scripts/gate1_step06_finalize.py"
PHP_HELPER="$DRUPAL/scripts/gate1-step06-human-review.php"
STEP05_FINAL_AUDIT="$STEP05_GATE_ROOT/final-audit.json"
STEP05_PHP="$DRUPAL/scripts/gate1-step05-drupal-ai-batch-runner.php"
INSPECT_PHP="$DRUPAL/scripts/gate05-step04.php"

fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }
pass() { printf '[PASS] %s\n' "$*"; }
info() { printf '[INFO] %s\n' "$*"; }

require_repo_baseline() {
  [[ "$(git -C "$REPO" branch --show-current)" == "main" ]] || fail "Step 1.06 operational commands require branch main."
  git -C "$REPO" merge-base --is-ancestor "$BASELINE" HEAD || fail "Step 1.05 merge is not in ancestry."
  [[ "$(git -C "$REPO" rev-parse HEAD)" == "$BASELINE" ]] || fail "Step 1.06 requires merged Step 1.05 baseline at HEAD."
  [[ "$(git -C "$REPO" rev-parse origin/main)" == "$BASELINE" ]] || fail "origin/main is not synchronized to the Step 1.05 merge."
}

module_enabled() {
  (cd "$DRUPAL" && ddev drush pm:list --type=module --status=enabled --format=list) | grep -Fx 'agentic_harness_drupal_ai' >/dev/null
}

snapshot_exists() {
  local name="$1"
  (cd "$DRUPAL" && ddev snapshot --list 2>/dev/null || true) | grep -F "$name" >/dev/null
}

resolve_site_url() {
  local value
  value="$(cd "$DRUPAL" && ddev exec printenv DDEV_PRIMARY_URL 2>/dev/null | tr -d '\r' | grep -Eo 'https?://[^[:space:]]+' | tail -n 1 || true)"
  [[ -n "$value" ]] || fail "Unable to resolve DDEV_PRIMARY_URL."
  printf '%s' "${value%/}"
}

run_counts() {
  local output="$1"
  (cd "$DRUPAL" && ddev drush --quiet php:script scripts/gate1-step06-human-review.php -- counts "$BATCH_RUN_ID") >"$output"
}

run_reviewer() {
  local output="$1"
  (cd "$DRUPAL" && ddev drush --quiet php:script scripts/gate1-step06-human-review.php -- reviewer) >"$output"
}

run_source_snapshot() {
  local output="$1"
  (cd "$DRUPAL" && ddev drush --quiet php:script scripts/gate05-step04.php -- snapshot) >"$output"
}

run_inspect() {
  local nid="$1" output="$2"
  (cd "$DRUPAL" && ddev drush --quiet php:script scripts/gate05-step04.php -- inspect "$nid") >"$output"
}

run_step05_state() {
  local output="$1"
  (cd "$DRUPAL" && ddev drush --quiet php:script scripts/gate1-step05-drupal-ai-batch-runner.php -- snapshot) >"$output"
}

python_json_check() {
  python3 - "$@" <<'PY_JSON_CHECK'
import json, sys
mode = sys.argv[1]
value = json.load(open(sys.argv[2], encoding='utf-8'))
if mode == 'source_pending':
    expected = {'article_count':20,'suggestion_count':12,'article_source_sha256':'877cd888fa41eb660b3e3cc0461bee04c0b92bef7e8f2f63fc56d9ec77adde32'}
    for key, exp in expected.items():
        if value.get(key) != exp:
            raise SystemExit(f'[ERROR] pending source state differs: {key}={value.get(key)!r}')
elif mode == 'source_clean':
    expected = {'article_count':20,'suggestion_count':0,'article_source_sha256':'877cd888fa41eb660b3e3cc0461bee04c0b92bef7e8f2f63fc56d9ec77adde32'}
    for key, exp in expected.items():
        if value.get(key) != exp:
            raise SystemExit(f'[ERROR] restored source state differs: {key}={value.get(key)!r}')
elif mode.startswith('counts:'):
    p,a,r = map(int, mode.split(':')[1:])
    if value.get('run_id') != 'drupal_ai-20260808T020222Z-205fd9' or value.get('total') != 12:
        raise SystemExit('[ERROR] recommendation run/count differs')
    expected = {'pending':p,'approved':a,'rejected':r}
    if value.get('counts') != expected:
        raise SystemExit(f"[ERROR] review counts differ: {value.get('counts')} != {expected}")
    if any(rec.get('source_framework') != 'drupal_ai' or rec.get('run_id') != 'drupal_ai-20260808T020222Z-205fd9' for rec in value.get('records', [])):
        raise SystemExit('[ERROR] recommendation provenance differs')
elif mode == 'reviewer':
    if value.get('username') != 'editor_dana' or value.get('active') is not True:
        raise SystemExit('[ERROR] editor_dana reviewer account is not active')
elif mode == 'step05':
    expected = {
        'article_count':20,'suggestion_count':12,'target_count':12,
        'article_source_sha256':'f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17','runtime_state_present':True,
        'runtime_artifacts_present':True,'runtime_status':'completed','next_target_index':12,
        'temporary_agent_config_present':False,'batch_completed_pending_review':True,
    }
    for key, exp in expected.items():
        if value.get(key) != exp:
            raise SystemExit(f'[ERROR] Step 1.05 handoff differs: {key}={value.get(key)!r}')
elif mode == 'step05_retained':
    expected = {
        'article_source_sha256':'f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17',
        'automatic_retries':0,
        'baseline':'5e01aa49dcb253af429f984e46aa732656565c05',
        'duplicate_count':0,'evidence_status':'pass','expected_duplicate_count':0,
        'failure_after_sequence':6,'failure_before_sequence':7,'failure_seam_observed':True,
        'gate_run':'gate1-step05-20260808T020222Z-2121689',
        'human_review_completed':False,'human_review_in_step_1_05':False,
        'model':'gpt-4.1-mini-2025-04-14','model_call_count_total':12,
        'moderation_rate_pacing_seconds':65,'pending_status_count':12,'provider':'openai',
        'provider_request_count_resume':6,'provider_request_count_start':6,
        'recommendation_count':12,'resume_at_sequence':7,'resume_sequence':7,
        'run_id':'drupal_ai-20260808T020222Z-205fd9','source_article_unchanged':True,
        'status':'pass','step_1_06_absent':True,'target_count':12,
        'target_sequence_sha256':'1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728',
        'temperature':0.0,
    }
    for key, exp in expected.items():
        if value.get(key) != exp:
            raise SystemExit(f'[ERROR] Retained Step 1.05 final audit differs: {key}={value.get(key)!r}')
else:
    raise SystemExit('[ERROR] unknown JSON check mode')
PY_JSON_CHECK
}

verify_scope() {
  python3 - "$REPO" <<'PY_SCOPE'
import subprocess, sys
from pathlib import Path
repo=Path(sys.argv[1])
allowed_exact={
 'docs/gates/GATE-1-STEP06-DRUPAL-AI-BATCH-EVIDENCE-AND-HUMAN-REVIEW.md',
 'drupal/scripts/gate1-step06-human-review.php',
 'scripts/gate1_step06_evidence_audit.py',
 'scripts/gate1_step06_finalize.py',
 'scripts/run-gate1-step06-drupal-ai-batch-evidence-and-human-review.sh',
 'PLAN.md','README.md','docs/CURRENT-STATUS.md',
 'evidence/results/drupal_ai/drupal_ai-20260808T020222Z-205fd9/human-review.json',
 'evidence/results/drupal_ai/drupal_ai-20260808T020222Z-205fd9/source-non-mutation.json',
 'evidence/results/drupal_ai/drupal_ai-20260808T020222Z-205fd9/duplicate-check.json',
 'evidence/results/drupal_ai/drupal_ai-20260808T020222Z-205fd9/environment.json',
}
allowed_prefix='evidence/gates/gate-1/batch-evidence/'
out=subprocess.run(['git','-C',str(repo),'status','--porcelain=v1','--untracked-files=all'],check=True,capture_output=True,text=True).stdout
bad=[]
for line in out.splitlines():
    if not line: continue
    path=line[3:]
    if ' -> ' in path: path=path.split(' -> ',1)[1]
    if path in allowed_exact or path.startswith(allowed_prefix): continue
    bad.append(path)
if bad:
    raise SystemExit(f'[ERROR] Unexpected Step 1.06 working-tree paths: {sorted(bad)}')
PY_SCOPE
}

resolve_pending_dir() {
  [[ -s "$PENDING_FILE" ]] || fail "No Step 1.06 review run is pending."
  local rel
  rel="$(tr -d '\r\n' < "$PENDING_FILE")"
  [[ "$rel" =~ ^evidence/gates/gate-1/batch-evidence/gate1-step06-[A-Za-z0-9._-]+$ ]] || fail "Invalid Step 1.06 pending pointer."
  [[ -d "$REPO/$rel" ]] || fail "Step 1.06 pending evidence directory is missing."
  printf '%s' "$REPO/$rel"
}

stage_value() {
  local dir="$1"
  [[ -s "$dir/review-stage.txt" ]] || fail "Review stage file is missing."
  tr -d '\r\n' < "$dir/review-stage.txt"
}

write_stage() { printf '%s\n' "$2" > "$1/review-stage.txt"; }

print_review_instruction() {
  local nid="$1" action="$2"
  local site
  site="$(resolve_site_url)"
  printf '\n=== HUMAN ACTION REQUIRED ===\n'
  printf 'Open: %s/node/%s/edit\n' "$site" "$nid"
  printf 'Sign in as editor_dana using the existing local Step 7 credential file.\n'
  case "$action" in
    approve)
      printf 'Change ONLY Review status to Approved. Leave Proposed alt text unchanged. Save exactly once.\n'
      printf 'Then run: bash scripts/run-gate1-step06-drupal-ai-batch-evidence-and-human-review.sh verify-approve\n'
      ;;
    reject)
      printf 'Change ONLY Review status to Rejected. Leave Proposed alt text unchanged. Save exactly once.\n'
      printf 'Then run: bash scripts/run-gate1-step06-drupal-ai-batch-evidence-and-human-review.sh verify-reject\n'
      ;;
    edit-approve)
      printf 'Edit Proposed alt text to a meaningful, non-empty wording of your choice AND set Review status to Approved.\n'
      printf 'Change no other fields. Save exactly once.\n'
      printf 'Then run: bash scripts/run-gate1-step06-drupal-ai-batch-evidence-and-human-review.sh certify\n'
      ;;
  esac
  printf 'Do not reset Drupal and do not make another recommendation save before verification.\n\n'
}

preflight() {
  require_repo_baseline
  verify_scope
  [[ -f "$AUDITOR" && -f "$FINALIZER" && -f "$PHP_HELPER" ]] || fail "Step 1.06 implementation is incomplete."
  [[ -d "$STEP05_GATE_ROOT" && -d "$RESULT_DIR" ]] || fail "Accepted Step 1.05 evidence is missing."
  [[ -f "$STEP05_FINAL_AUDIT" ]] || fail "Accepted Step 1.05 final audit is missing."
  [[ "$(tr -d '\r\n' < "$REPO/evidence/gates/gate-1/drupal-ai-batch-runner/GATE1-STEP05-LATEST.txt")" == "evidence/gates/gate-1/drupal-ai-batch-runner/$STEP05_GATE_ID" ]] || fail "Step 1.05 latest pointer differs."
  [[ "$(tr -d '\r\n' < "$STEP05_GATE_ROOT/model-run-id.txt")" == "$BATCH_RUN_ID" ]] || fail "Step 1.05 model run pointer differs."
  snapshot="$(tr -d '\r\n' < "$STEP05_GATE_ROOT/snapshot-name.txt")"
  snapshot_exists "$snapshot" || fail "Step 1.05 pre-batch restoration snapshot is unavailable."
  module_enabled || fail "Step 1.06 requires the preserved Step 1.05 module-enabled handoff state."
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' RETURN
  python_json_check step05_retained "$STEP05_FINAL_AUDIT"
  run_step05_state "$tmp/step05-state.json"
  python_json_check step05 "$tmp/step05-state.json"
  run_source_snapshot "$tmp/source.json"
  python_json_check source_pending "$tmp/source.json"
  run_counts "$tmp/counts.json"
  python_json_check counts:12:0:0 "$tmp/counts.json"
  run_reviewer "$tmp/reviewer.json"
  python_json_check reviewer "$tmp/reviewer.json"
  run_inspect 21 "$tmp/seq1.json"
  python3 - "$tmp/seq1.json" <<'PY_ACCESS'
import json,sys
v=json.load(open(sys.argv[1],encoding='utf-8'))
if v.get('access',{}).get('editor_can_update') is not True or v.get('access',{}).get('agent_can_update') is not False:
    raise SystemExit('[ERROR] Reviewer/agent update boundary differs')
if v.get('current_review_status') != 'pending' or v.get('current_run_id') != 'drupal_ai-20260808T020222Z-205fd9':
    raise SystemExit('[ERROR] Sequence 1 is not the accepted pending recommendation')
PY_ACCESS
  rm -rf "$tmp"
  trap - RETURN
  pass "Step 1.06 preflight passed: accepted Step 1.05 batch is intact with 12 pending recommendations."
  pass "No model/provider call and no human-review mutation was performed."
}

prepare() {
  preflight
  [[ ! -e "$PENDING_FILE" ]] || fail "A Step 1.06 review run is already pending."
  for name in human-review.json source-non-mutation.json duplicate-check.json environment.json; do
    [[ ! -e "$RESULT_DIR/$name" ]] || fail "Step 1.06 result file already exists: $name"
  done
  gate_id="gate1-step06-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  gate_dir="$GATE_ROOT/$gate_id"
  mkdir -p "$gate_dir"
  printf '%s\n' "evidence/gates/gate-1/batch-evidence/$gate_id" > "$LAST_FILE"
  printf '%s\n' "evidence/gates/gate-1/batch-evidence/$gate_id" > "$PENDING_FILE"
  printf '%s\n' "$BATCH_RUN_ID" > "$gate_dir/batch-run-pointer.txt"
  cp "$STEP05_FINAL_AUDIT" "$gate_dir/prior-package-audits.log"
  python_json_check step05_retained "$gate_dir/prior-package-audits.log"
  run_source_snapshot "$gate_dir/source-before-review.json"
  python_json_check source_pending "$gate_dir/source-before-review.json"
  run_counts "$gate_dir/counts-before-review.json"
  python_json_check counts:12:0:0 "$gate_dir/counts-before-review.json"
  run_reviewer "$gate_dir/reviewer.json"
  python_json_check reviewer "$gate_dir/reviewer.json"
  run_inspect 21 "$gate_dir/baseline-seq1.json"
  run_inspect 26 "$gate_dir/baseline-seq6.json"
  run_inspect 32 "$gate_dir/baseline-seq12.json"
  python3 - "$RESULT_DIR/submissions.json" "$gate_dir" <<'PY_PLAN'
import json,sys
from pathlib import Path
sub=json.load(open(sys.argv[1],encoding='utf-8'))['submissions']
selected={1:21,6:26,12:32}
by={int(x['sequence']):x for x in sub}
for seq,nid in selected.items():
    if by.get(seq,{}).get('node_id') != nid or by[seq].get('initial_status') != 'pending':
        raise SystemExit(f'[ERROR] Accepted submission identity differs for sequence {seq}')
plan={
 'schema_version':1,'run_id':'drupal_ai-20260808T020222Z-205fd9','reviewer_username':'editor_dana',
 'decisions':[
  {'sequence':1,'node_id':21,'action':'approve_unchanged'},
  {'sequence':6,'node_id':26,'action':'reject_unchanged'},
  {'sequence':12,'node_id':32,'action':'edit_and_approve'},
 ],
 'human_ui_required':True,'automated_decision_performed':False,
}
Path(sys.argv[2],'review-plan.json').write_text(json.dumps(plan,indent=2,sort_keys=True)+'\n',encoding='utf-8')
PY_PLAN
  write_stage "$gate_dir" awaiting_approve
  pass "Step 1.06 review evidence run prepared: $gate_id"
  print_review_instruction 21 approve
}

verify_approve() {
  require_repo_baseline
  verify_scope
  gate_dir="$(resolve_pending_dir)"
  [[ "$(stage_value "$gate_dir")" == "awaiting_approve" ]] || fail "Step 1.06 is not awaiting the sequence 1 approval."
  run_inspect 21 "$gate_dir/current-seq1.json"
  python3 "$AUDITOR" verify-review --baseline "$gate_dir/baseline-seq1.json" --current "$gate_dir/current-seq1.json" --sequence 1 --expected-status approved --alt-policy unchanged --output "$gate_dir/decision-seq1.json" >/dev/null
  run_counts "$gate_dir/counts-after-seq1.json"
  python_json_check counts:11:1:0 "$gate_dir/counts-after-seq1.json"
  write_stage "$gate_dir" awaiting_reject
  pass "Sequence 1 approval is tied to exactly one editor_dana revision with unchanged proposed alt text."
  print_review_instruction 26 reject
}

verify_reject() {
  require_repo_baseline
  verify_scope
  gate_dir="$(resolve_pending_dir)"
  [[ "$(stage_value "$gate_dir")" == "awaiting_reject" ]] || fail "Step 1.06 is not awaiting the sequence 6 rejection."
  run_inspect 26 "$gate_dir/current-seq6.json"
  python3 "$AUDITOR" verify-review --baseline "$gate_dir/baseline-seq6.json" --current "$gate_dir/current-seq6.json" --sequence 6 --expected-status rejected --alt-policy unchanged --output "$gate_dir/decision-seq6.json" >/dev/null
  run_counts "$gate_dir/counts-after-seq6.json"
  python_json_check counts:10:1:1 "$gate_dir/counts-after-seq6.json"
  write_stage "$gate_dir" awaiting_edit_approve
  pass "Sequence 6 rejection is tied to exactly one editor_dana revision with unchanged proposed alt text."
  print_review_instruction 32 edit-approve
}

assemble_evidence() {
  local gate_dir="$1"
  run_inspect 32 "$gate_dir/current-seq12.json"
  python3 "$AUDITOR" verify-review --baseline "$gate_dir/baseline-seq12.json" --current "$gate_dir/current-seq12.json" --sequence 12 --expected-status approved --alt-policy changed --output "$gate_dir/decision-seq12.json" >/dev/null
  run_counts "$gate_dir/counts-after-seq12.json"
  python_json_check counts:9:2:1 "$gate_dir/counts-after-seq12.json"
  run_source_snapshot "$gate_dir/source-after-review.json"
  python_json_check source_pending "$gate_dir/source-after-review.json"

  python3 - "$gate_dir" "$RESULT_DIR" <<'PY_EVIDENCE'
import json,sys
from pathlib import Path
g=Path(sys.argv[1]); r=Path(sys.argv[2])
load=lambda p: json.load(open(p,encoding='utf-8'))
decisions=[load(g/f'decision-seq{s}.json') for s in (1,6,12)]
counts={
 'before_review':load(g/'counts-before-review.json'),
 'after_sequence_1':load(g/'counts-after-seq1.json'),
 'after_sequence_6':load(g/'counts-after-seq6.json'),
 'after_sequence_12':load(g/'counts-after-seq12.json'),
}
(g/'recommendation-counts.json').write_text(json.dumps(counts,indent=2,sort_keys=True)+'\n',encoding='utf-8')
review={'schema_version':1,'run_id':'drupal_ai-20260808T020222Z-205fd9','reviewer_username':'editor_dana','decisions':decisions,'automated_decision_performed':False}
(g/'reviewer-decisions.json').write_text(json.dumps(review,indent=2,sort_keys=True)+'\n',encoding='utf-8')
lineage={'schema_version':1,'run_id':'drupal_ai-20260808T020222Z-205fd9','selected_sequences':[1,6,12],'decisions':[{k:v for k,v in d.items() if k not in ('proposed_alt_before','proposed_alt_after')} for d in decisions]}
(g/'revision-lineage.json').write_text(json.dumps(lineage,indent=2,sort_keys=True)+'\n',encoding='utf-8')
d12=next(d for d in decisions if int(d.get('sequence',-1))==12)
deviation={
 'schema_version':1,
 'run_id':'drupal_ai-20260808T020222Z-205fd9',
 'sequence':12,
 'planned_workflow':'single_save_edit_and_approve',
 'review_workflow':d12.get('review_workflow'),
 'deviation_observed':bool(d12.get('instruction_deviation',False)),
 'review_revision_count':d12.get('review_revision_count'),
 'review_revision_ids':d12.get('review_revision_ids'),
 'edit_revision_id':d12.get('edit_revision_id'),
 'decision_revision_id':d12.get('decision_revision_id'),
 'final_status':d12.get('status_after'),
 'edited_alt_preserved_into_approval':bool(
   d12.get('review_workflow')!='two_save_edit_then_approve'
   or d12.get('proposed_alt_changed') is True
 ),
 'impact':'Observed reviewer workflow is retained explicitly; no revision was deleted or rewritten.',
}
(g/'review-workflow-deviation.json').write_text(json.dumps(deviation,indent=2,sort_keys=True)+'\n',encoding='utf-8')
before=load(g/'source-before-review.json'); after=load(g/'source-after-review.json')
source={
 'schema_version':1,'run_id':'drupal_ai-20260808T020222Z-205fd9','before_review':before,'after_review':after,
 'source_articles_unchanged':before.get('article_source_sha256')==after.get('article_source_sha256')=='877cd888fa41eb660b3e3cc0461bee04c0b92bef7e8f2f63fc56d9ec77adde32',
 'approved_recommendation_applied_to_source':False,
}
(g/'source-before-after.json').write_text(json.dumps(source,indent=2,sort_keys=True)+'\n',encoding='utf-8')
# Step 1.06 result additions. Existing Step 1.05 evidence is not rewritten.
(r/'human-review.json').write_text(json.dumps(review,indent=2,sort_keys=True)+'\n',encoding='utf-8')
(r/'duplicate-check.json').write_text(json.dumps({'schema_version':1,'run_id':'drupal_ai-20260808T020222Z-205fd9','recommendation_count':12,'duplicate_count':0,'review_decisions_create_new_recommendations':False},indent=2,sort_keys=True)+'\n',encoding='utf-8')
(r/'environment.json').write_text(json.dumps({'schema_version':1,'run_id':'drupal_ai-20260808T020222Z-205fd9','step':'1.06','framework_origin':'drupal_ai','reviewer_username':'editor_dana','human_ui_review':True,'model_call_performed':False,'credentials_retained':False,'authorization_headers_retained':False,'raw_image_retained':False},indent=2,sort_keys=True)+'\n',encoding='utf-8')
PY_EVIDENCE
}

restore_seeded_clean() {
  local gate_dir="$1"
  snapshot="$(tr -d '\r\n' < "$STEP05_GATE_ROOT/snapshot-name.txt")"
  snapshot_exists "$snapshot" || fail "Step 1.05 restoration snapshot is unavailable."
  info "Restoring the exact pre-Step-1.05 Drupal snapshot..."
  (cd "$DRUPAL" && ddev snapshot restore "$snapshot" >/dev/null && ddev drush cr >/dev/null)
  module_enabled && fail "Restoration left agentic_harness_drupal_ai enabled."
  run_source_snapshot "$gate_dir/source-after-restore.json"
  python_json_check source_clean "$gate_dir/source-after-restore.json"
  python3 - "$gate_dir" <<'PY_POST'
import json,sys
from pathlib import Path
g=Path(sys.argv[1]); load=lambda p: json.load(open(p,encoding='utf-8'))
source=load(g/'source-before-after.json'); after=load(g/'source-after-restore.json')
source['after_restore']=after
source['restored_seeded_clean']=True
(g/'source-before-after.json').write_text(json.dumps(source,indent=2,sort_keys=True)+'\n',encoding='utf-8')
post=dict(after); post['module_enabled']=False; post['restored_seeded_clean']=True
(g/'post-restore-state.json').write_text(json.dumps(post,indent=2,sort_keys=True)+'\n',encoding='utf-8')
PY_POST
  cp "$gate_dir/source-before-after.json" "$RESULT_DIR/source-non-mutation.json"
  write_stage "$gate_dir" reviews_verified_restored
}

write_summary_and_scan() {
  local gate_dir="$1"
  python3 - "$gate_dir" <<'PY_SUMMARY'
import json,sys
from pathlib import Path
g=Path(sys.argv[1]); run=g.name
d12=json.load(open(g/'decision-seq12.json',encoding='utf-8'))
review_revision_count=2+int(d12.get('revision_delta',0))
workflow=d12.get('review_workflow')
deviation=bool(d12.get('instruction_deviation',False))
summary={
 'schema_version':1,'status':'pass','step':'1.06','evidence_run_id':run,'batch_run_id':'drupal_ai-20260808T020222Z-205fd9',
 'reviewer_username':'editor_dana','review_decision_count':3,
 'review_revision_count':review_revision_count,
 'sequence_12_review_workflow':workflow,
 'instruction_deviation_recorded':deviation,
 'review_counts_after_decisions':{'pending':9,'approved':2,'rejected':1},
 'source_articles_unchanged':True,'approved_recommendation_applied_to_source':False,
 'restored_seeded_clean':True,'model_call_performed':False,'step_1_07_authorized':True,
}
lineage_note=(
 "- **Sequence 12 lineage:** alt text was edited while pending, then approved in a second `editor_dana` revision; this workflow deviation is retained explicitly.\n"
 if deviation else
 "- **Sequence 12 lineage:** edit and approval were saved together in one `editor_dana` revision.\n"
)
(g/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
(g/'summary.md').write_text(
 f"# Gate 1 Step 1.06 Drupal AI Batch Evidence and Human Review\n\n"
 f"- **Status:** PASS\n- **Evidence run:** `{run}`\n- **Batch run:** `{summary['batch_run_id']}`\n"
 "- **Human decisions:** sequence 1 approved unchanged; sequence 6 rejected unchanged; sequence 12 edited and approved\n"
 f"- **Reviewer revisions retained:** {review_revision_count}\n"
 + lineage_note +
 "- **Reviewer:** `editor_dana` through Drupal editorial forms\n"
 "- **Final review counts before restore:** 9 pending / 2 approved / 1 rejected\n"
 "- **Source Articles:** unchanged\n- **Automatic source application:** none\n"
 "- **Post-review sandbox:** restored to seeded-clean\n- **Model/provider calls in Step 1.06:** 0\n"
 "- **Next:** Gate 1 Step 1.07 certification, freeze, and handoff\n",
 encoding='utf-8')
PY_SUMMARY
  : > "$gate_dir/secrets-scan.log"
  local found=0
  while IFS= read -r path; do
    if grep -nEi '(authorization:[[:space:]]*(basic|bearer)|sk-[A-Za-z0-9_-]{12,}|data:image/[^;]+;base64,[A-Za-z0-9+/=]{16,})' "$path" >> "$gate_dir/secrets-scan.log" 2>/dev/null; then
      found=1
    fi
  done < <(find "$gate_dir" -type f ! -name secrets-scan.log -print; printf '%s\n' "$RESULT_DIR/human-review.json" "$RESULT_DIR/source-non-mutation.json" "$RESULT_DIR/duplicate-check.json" "$RESULT_DIR/environment.json")
  [[ "$found" -eq 0 ]] || fail "Sensitive-data pattern detected in Step 1.06 evidence."
  printf '[PASS] No authorization token, OpenAI-style secret, or retained image data URL detected.\n' > "$gate_dir/secrets-scan.log"
}

finalize_from_evidence() {
  local gate_dir="$1"
  [[ "$(stage_value "$gate_dir")" == "reviews_verified_restored" || "$(stage_value "$gate_dir")" == "certified" ]] || fail "Step 1.06 retained evidence is not ready for finalization."
  run_source_snapshot "$gate_dir/post-restore-current.json"
  python_json_check source_clean "$gate_dir/post-restore-current.json"
  module_enabled && fail "Finalization requires seeded-clean module-disabled state."
  write_summary_and_scan "$gate_dir"
  evidence_run="$(basename "$gate_dir")"
  python3 "$FINALIZER" --repo "$REPO" --evidence-run-id "$evidence_run"
  git -C "$REPO" diff --check -- . ':(exclude,glob)evidence/gates/**/*.log'
  python3 "$AUDITOR" final-audit --repo "$REPO" --gate-run-dir "$gate_dir" --result-dir "$RESULT_DIR" > "$gate_dir/final-audit.json"
  printf '%s\n' "evidence/gates/gate-1/batch-evidence/$evidence_run" > "$LATEST_FILE"
  rm -f "$PENDING_FILE"
  write_stage "$gate_dir" certified
  pass "Gate 1 Step 1.06 certified with three human reviewer decisions, retained Drupal revision lineage, and unchanged source Articles."
  pass "Step 1.06 evidence: evidence/gates/gate-1/batch-evidence/$evidence_run"
  pass "Step 1.07 is the next package."
}

certify() {
  require_repo_baseline
  verify_scope
  gate_dir="$(resolve_pending_dir)"
  [[ "$(stage_value "$gate_dir")" == "awaiting_edit_approve" ]] || fail "Step 1.06 is not awaiting the sequence 12 edit-and-approve decision."
  assemble_evidence "$gate_dir"
  restore_seeded_clean "$gate_dir"
  finalize_from_evidence "$gate_dir"
}

finalize_mode() {
  require_repo_baseline
  verify_scope
  gate_dir="$(resolve_pending_dir)"
  finalize_from_evidence "$gate_dir"
}

audit() {
  require_repo_baseline
  verify_scope
  [[ ! -e "$PENDING_FILE" ]] || fail "Step 1.06 review run is still pending."
  [[ -s "$LATEST_FILE" ]] || fail "Step 1.06 passing pointer is missing."
  rel="$(tr -d '\r\n' < "$LATEST_FILE")"
  gate_dir="$REPO/$rel"
  [[ -d "$gate_dir" ]] || fail "Step 1.06 evidence directory is missing."
  run_source_snapshot "$gate_dir/audit-current-seeded-clean.json"
  python_json_check source_clean "$gate_dir/audit-current-seeded-clean.json"
  module_enabled && fail "Step 1.06 audit requires the restored module-disabled state."
  python3 "$AUDITOR" final-audit --repo "$REPO" --gate-run-dir "$gate_dir" --result-dir "$RESULT_DIR"
  pass "Gate 1 Step 1.06 audit passed."
}

case "$MODE" in
  preflight) preflight ;;
  prepare) prepare ;;
  verify-approve) verify_approve ;;
  verify-reject) verify_reject ;;
  certify) certify ;;
  finalize) finalize_mode ;;
  audit) audit ;;
  *) fail "Usage: bash scripts/run-gate1-step06-drupal-ai-batch-evidence-and-human-review.sh {preflight|prepare|verify-approve|verify-reject|certify|finalize|audit}" ;;
esac
