#!/usr/bin/env bash
set -Eeuo pipefail
MODE="${1:-}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRUPAL="$REPO/drupal"
PYTHON="$REPO/langchain/.venv/bin/python"
VALIDATOR_PYTHON="$REPO/crewai/.venv/bin/python"
CORE="$REPO/langchain/agentic_harness_langgraph/human_review.py"
AUDITOR="$REPO/scripts/gate2a_step06_audit.py"
FINALIZER="$REPO/scripts/gate2a_step06_finalize.py"
STATE="$REPO/scripts/gate2a_step06_state.py"
SCHEMA_VALIDATOR="$REPO/scripts/gate2a_step03_schema_validate.py"
PHP_HELPER="$DRUPAL/scripts/gate2a-step06-review-lineage.php"
BRANCH="gate-2a-step06-langgraph-human-interrupt-and-review-resume"
EXPECTED_HEAD="2b61e5859a5474e8422b85e0108b89808c519208"
ROOT="$REPO/evidence/gates/gate-2a/human-interrupt"
RUNTIME_ROOT="$REPO/langchain/.gate2a-runtime"
CREDENTIALS="$DRUPAL/.secrets/phase0-step7-accounts.txt"
LAST="$ROOT/GATE2A-STEP06-LAST-RUN.txt"
PENDING="$ROOT/GATE2A-STEP06-PENDING-REVIEW.txt"
FAILED="$ROOT/GATE2A-STEP06-FAILED-RUNS.txt"
LATEST="$ROOT/GATE2A-STEP06-LATEST.txt"
RETRY_AUTH="$ROOT/GATE2A-STEP06-RETRY-AUTHORIZED.txt"

fail(){ printf '[ERROR] %s\n' "$*" >&2; exit 1; }
pass(){ printf '[PASS] %s\n' "$*"; }
info(){ printf '[INFO] %s\n' "$*"; }
latest_secret(){ local key="$1"; awk -v key="$key" 'index($0,key "=")==1 {value=substr($0,length(key)+2)} END{if(value!="")print value}' "$CREDENTIALS"; }
resolve_site_url(){ local v; v="$(cd "$DRUPAL" && ddev exec printenv DDEV_PRIMARY_URL 2>/dev/null | tr -d '\r' | grep -Eo 'https?://[^[:space:]]+' | tail -n1 || true)"; [[ -n "$v" ]] || fail "Unable to resolve DDEV_PRIMARY_URL"; printf '%s' "${v%/}"; }
seeded_clean(){ (cd "$DRUPAL" && bash scripts/run-phase0-step10.sh audit) >"$1"; }
snapshot_state(){ (cd "$DRUPAL" && env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL ddev drush --quiet php:script scripts/gate1-step03-adapter-exercise.php -- snapshot) >"$1"; }
restore_snapshot(){ local name="$1"; (cd "$DRUPAL" && ddev snapshot restore "$name" >/dev/null && ddev drush cr >/dev/null && ddev snapshot --cleanup --name "$name" -y >/dev/null); }
append_failed(){ mkdir -p "$ROOT"; touch "$FAILED"; grep -Fx "$1" "$FAILED" >/dev/null 2>&1 || printf '%s\n' "$1" >>"$FAILED"; }

require_live_branch(){ [[ "$(git -C "$REPO" branch --show-current)" == "$BRANCH" ]] || fail "Expected branch $BRANCH."; [[ "$(git -C "$REPO" rev-parse HEAD)" == "$EXPECTED_HEAD" ]] || fail "Expected uncommitted Step 2A.06 install on $EXPECTED_HEAD."; }

preflight(){
  require_live_branch
  [[ -x "$PYTHON" && -x "$VALIDATOR_PYTHON" ]] || fail "Locked Python environments missing."
  for f in "$CORE" "$AUDITOR" "$FINALIZER" "$STATE" "$PHP_HELPER"; do [[ -f "$f" ]] || fail "Missing Step 2A.06 file: $f"; done
  (cd "$DRUPAL" && ddev exec php -l /var/www/html/scripts/gate2a-step06-review-lineage.php >/dev/null) || fail "Step 2A.06 PHP helper syntax check failed inside DDEV."
  pass "Step 2A.06 PHP helper syntax passed inside DDEV."
  "$PYTHON" - <<'PY'
import importlib.metadata as md
for n,w in {"langgraph":"1.2.10","langgraph-checkpoint-sqlite":"3.1.1"}.items():
    g=md.version(n)
    assert g==w,(n,g,w)
from langgraph.types import Command, interrupt
from langgraph.checkpoint.sqlite import SqliteSaver
print("[PASS] Pinned LangGraph interrupt/resume/SQLite imports and versions passed.")
PY
  [[ -z "${OPENAI_API_KEY:-}" ]] || fail "Step 2A.06 requires OPENAI_API_KEY to be unset; model calls are prohibited."
  mkdir -p "$RUNTIME_ROOT"
  local p="$RUNTIME_ROOT/.gate2a-step06-ignore-probe.sqlite"; : >"$p"; git -C "$REPO" check-ignore -q "langchain/.gate2a-runtime/.gate2a-step06-ignore-probe.sqlite" || { rm -f "$p"; fail "Runtime root is not gitignored."; }; rm -f "$p"
  "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state active
  pass "Gate 2A Step 2A.06 static preflight passed with model access blocked."
}

export_agent_env(){
  [[ -f "$CREDENTIALS" ]] || fail "Local Drupal credentials file is missing."
  local pw; pw="$(latest_secret agent_bot)"; [[ -n "$pw" ]] || fail "agent_bot credential is empty."
  export GATE2A_DRUPAL_USERNAME="agent_bot" GATE2A_DRUPAL_PASSWORD="$pw" GATE2A_DRUPAL_BASE_URL="$(resolve_site_url)"
}
unset_agent_env(){ unset GATE2A_DRUPAL_USERNAME GATE2A_DRUPAL_PASSWORD GATE2A_DRUPAL_BASE_URL || true; }

start_run(){
  preflight
  [[ ! -e "$LATEST" ]] || fail "Step 2A.06 is already complete."
  [[ ! -e "$PENDING" ]] || fail "A Step 2A.06 run is already awaiting human review; do not start another."
  if [[ -e "$LAST" ]]; then
    local prior_rel
    prior_rel="$(<"$LAST")"
    [[ -s "$RETRY_AUTH" ]] || fail "A Step 2A.06 attempt already exists. Human review/package repair is required before another start."
    [[ "$(<"$RETRY_AUTH")" == "$prior_rel" ]] || fail "Step 2A.06 retry authorization does not match the retained failed attempt."
    [[ -s "$FAILED" ]] && grep -Fx "$prior_rel" "$FAILED" >/dev/null || fail "Retry authorization does not reference a retained failed run."
  fi
  bash "$REPO/scripts/run-gate1-step07-drupal-ai-certification-and-handoff.sh" audit >/dev/null
  mkdir -p "$ROOT" "$RUNTIME_ROOT"
  local stamp suffix run_id name rel dir snap rc site node_id
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"; suffix="$(printf '%08x' "$$")"; run_id="langgraph-${stamp}-${suffix}"; name="gate2a-step06-${stamp}-${suffix}"; rel="evidence/gates/gate-2a/human-interrupt/$name"; dir="$REPO/$rel"
  [[ "$run_id" =~ ^langgraph-[0-9]{8}T[0-9]{6}Z-[a-z0-9]{4,12}$ ]] || fail "Generated Step 2A.06 run_id violates the frozen experiment format."
  mkdir -p "$dir"
  printf '%s\n' "$rel" >"$LAST"; rm -f "$RETRY_AUTH"; printf '%s\n' "$run_id" >"$dir/run-id.txt"
  seeded_clean "$dir/seeded-clean-before.log"; snapshot_state "$dir/before-state.json"
  snap="gate2a-step06-pre-${stamp}-${suffix}"; printf '%s\n' "$snap" >"$dir/snapshot-name.txt"; info "Creating exact pre-run DDEV snapshot..."; (cd "$DRUPAL" && ddev snapshot --name "$snap" >/dev/null)
  export_agent_env
  info "Creating one pending recommendation from accepted Step 2A.05 output, then entering a genuine LangGraph interrupt..."
  set +e
  env -u OPENAI_API_KEY PYTHONPATH="$REPO/langchain:$REPO${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" "$CORE" --repo "$REPO" --evidence "$dir" --run-id "$run_id" --mode start
  rc=$?
  set -e
  unset_agent_env
  if [[ "$rc" -ne 0 ]]; then
    snapshot_state "$dir/failed-state.json" || true; restore_snapshot "$snap" || true; seeded_clean "$dir/seeded-clean-after-failure.log" || true; append_failed "$rel"; fail "Step 2A.06 start failed and Drupal was restored. Retained: $rel"
  fi
  set +e
  "$VALIDATOR_PYTHON" "$SCHEMA_VALIDATOR" --schema-dir "$REPO/shared/schemas" --schema langgraph-run-state.schema.json <"$dir/checkpoint-before-review.json" >"$dir/checkpoint-before-review-schema-validation.json" 2>"$dir/checkpoint-before-review-schema-validation.err"
  rc=$?
  set -e
  if [[ "$rc" -ne 0 ]]; then
    snapshot_state "$dir/failed-state.json" || true; restore_snapshot "$snap" || true; seeded_clean "$dir/seeded-clean-after-failure.log" || true; append_failed "$rel"; fail "Step 2A.06 interrupted checkpoint failed frozen schema validation before human review. Drupal was restored; retained: $rel"
  fi
  rm -f "$dir/checkpoint-before-review-schema-validation.err"
  snapshot_state "$dir/pending-state.json"
  (cd "$DRUPAL" && ddev drush --quiet php:script scripts/gate2a-step06-review-lineage.php -- pending "$run_id") >"$dir/reviewer-revision-lineage-before.json"
  printf '%s\n' "$rel" >"$PENDING"
  site="$(resolve_site_url)"; node_id="$($PYTHON -c 'import json,sys; print(json.load(open(sys.argv[1]))["submission"]["node_id"])' "$dir/pending-recommendation.json")"
  cat >"$dir/review-instructions.txt" <<EOF
Human action required in Drupal as editor_dana.
Edit URL: ${site}/node/${node_id}/edit
1. Change Proposed alt text to a meaningful non-empty value different from the current value (max 250 characters).
2. Set Review status to Approved.
3. Save exactly once.
Then run: bash scripts/run-gate2a-step06.sh resume
EOF
  pass "LangGraph persisted a genuine interrupt and is awaiting Drupal review."
  pass "Pending evidence: $rel"
  printf '[HUMAN] Log into Drupal as editor_dana and open: %s/node/%s/edit\n' "$site" "$node_id"
  printf '[HUMAN] Edit Proposed alt text, set Review status to Approved, and save exactly once.\n'
  printf '[STOP] Do not start another run. After the human save, run: bash scripts/run-gate2a-step06.sh resume\n'
}

resume_run(){
  preflight
  [[ -s "$PENDING" ]] || fail "No Step 2A.06 run is awaiting human review."
  [[ ! -e "$LATEST" ]] || fail "Step 2A.06 is already complete."
  local rel dir run_id snap rc backup tmp
  rel="$(<"$PENDING")"; dir="$REPO/$rel"; [[ -d "$dir" ]] || fail "Pending run directory missing."; run_id="$(<"$dir/run-id.txt")"; snap="$(<"$dir/snapshot-name.txt")"
  # This is a read-only assertion. If human review is not complete, stop without restoring or changing the interrupted run.
  if ! (cd "$DRUPAL" && ddev drush --quiet php:script scripts/gate2a-step06-review-lineage.php -- reviewed "$run_id") >"$dir/reviewer-revision-lineage.json"; then
    rm -f "$dir/reviewer-revision-lineage.json"
    fail "The required editor_dana edit-and-approve revision is not complete. The interrupted run remains intact."
  fi
  snapshot_state "$dir/reviewed-state.json"
  export_agent_env
  info "Resuming the same LangGraph run/thread from SQLite and observing Drupal review status..."
  set +e
  env -u OPENAI_API_KEY PYTHONPATH="$REPO/langchain:$REPO${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" "$CORE" --repo "$REPO" --evidence "$dir" --run-id "$run_id" --mode resume
  rc=$?
  set -e
  unset_agent_env
  if [[ "$rc" -ne 0 ]]; then append_failed "$rel"; fail "Step 2A.06 graph resume failed. Drupal and the retained interrupted/reviewed state were not erased. Do not retry without review."; fi
  set +e
  "$VALIDATOR_PYTHON" "$SCHEMA_VALIDATOR" --schema-dir "$REPO/shared/schemas" --schema langgraph-run-state.schema.json <"$dir/checkpoint-after-resume.json" >"$dir/checkpoint-after-resume-schema-validation.json" 2>"$dir/checkpoint-after-resume-schema-validation.err"
  rc=$?
  set -e
  if [[ "$rc" -ne 0 ]]; then
    snapshot_state "$dir/post-resume-invalid-state.json" || true
    restore_snapshot "$snap" || true
    seeded_clean "$dir/seeded-clean-after-failure.log" || true
    snapshot_state "$dir/after-state.json" || true
    append_failed "$rel"
    rm -f "$PENDING"
    fail "Step 2A.06 post-resume checkpoint failed frozen schema validation. Drupal was restored; retained: $rel"
  fi
  rm -f "$dir/checkpoint-after-resume-schema-validation.err"
  info "Restoring exact pre-run DDEV snapshot after successful resume evidence capture..."
  restore_snapshot "$snap"; seeded_clean "$dir/seeded-clean-after.log"; snapshot_state "$dir/after-state.json"
  "$PYTHON" "$FINALIZER" --repo "$REPO" --evidence "$dir" --run-id "$run_id"
  "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state active --run-dir "$rel"
  backup="$(mktemp -d)"; mkdir -p "$backup/docs"; cp "$REPO/AGENTS.md" "$backup/AGENTS.md"; cp "$REPO/PLAN.md" "$backup/PLAN.md"; cp "$REPO/README.md" "$backup/README.md"; cp "$REPO/docs/CURRENT-STATUS.md" "$backup/docs/CURRENT-STATUS.md"
  rollback(){ set +e; cp "$backup/AGENTS.md" "$REPO/AGENTS.md"; cp "$backup/PLAN.md" "$REPO/PLAN.md"; cp "$backup/README.md" "$REPO/README.md"; cp "$backup/docs/CURRENT-STATUS.md" "$REPO/docs/CURRENT-STATUS.md"; rm -f "$LATEST"; set -e; }
  "$PYTHON" "$STATE" --repo "$REPO" --state complete --run-dir "$rel" || { rollback; rm -rf "$backup"; fail "Step 2A.06 evidence passed but lifecycle finalization failed."; }
  tmp="${LATEST}.tmp"; printf '%s\n' "$rel" >"$tmp"; mv "$tmp" "$LATEST"
  "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state complete || { rollback; rm -rf "$backup"; fail "Step 2A.06 complete audit failed; lifecycle promotion rolled back."; }
  rm -rf "$backup"; rm -f "$PENDING"; git -C "$REPO" diff --check
  pass "Gate 2A Step 2A.06 human interrupt/review/resume proof passed."
  pass "Accepted evidence: $rel"
  pass "Model/provider calls: 0; human reviewer: editor_dana; source mutation/publication: 0/0; Drupal restored to seeded-clean."
  printf '[STOP] Inspect evidence and diff before exact-scope staging or commit. Step 2A.07 remains locked.\n'
}

case "$MODE" in
  preflight) preflight ;;
  start) start_run ;;
  resume) resume_run ;;
  audit) "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state complete ;;
  *) fail "Usage: bash scripts/run-gate2a-step06.sh {preflight|start|resume|audit}" ;;
esac
