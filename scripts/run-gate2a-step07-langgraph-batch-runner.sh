#!/usr/bin/env bash
set -Eeuo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$REPO/langchain/.venv/bin/python"
SCHEMA_PYTHON="$REPO/crewai/.venv/bin/python"
AUDITOR="$REPO/scripts/gate2a_step07_audit.py"
STATE="$REPO/scripts/gate2a_step07_state.py"
CORE="$REPO/langchain/agentic_harness_langgraph/batch_runner.py"
ROOT="$REPO/evidence/gates/gate-2a/batch-runner"
LAST="$ROOT/GATE2A-STEP07-LAST-RUN.txt"
CANDIDATE="$ROOT/GATE2A-STEP07-CANDIDATE.txt"
LATEST="$ROOT/GATE2A-STEP07-LATEST.txt"
FAILED="$ROOT/GATE2A-STEP07-FAILED-RUNS.txt"
RETRY_AUTH="$ROOT/GATE2A-STEP07-RETRY-AUTHORIZED.txt"

fail(){ printf '[ERROR] %s\n' "$*" >&2; exit 1; }

static_preflight(){
  [[ -x "$PYTHON" ]] || fail "Pinned LangGraph Python is missing: $PYTHON"
  [[ -x "$SCHEMA_PYTHON" ]] || fail "Repository schema-validation Python is missing: $SCHEMA_PYTHON"
  "$SCHEMA_PYTHON" -c 'from jsonschema import Draft202012Validator,FormatChecker' >/dev/null || fail "Repository schema-validation Python lacks jsonschema Draft 2020-12 support."
  [[ ! -n "${OPENAI_API_KEY:-}" ]] || fail "OPENAI_API_KEY must be unset for Step 2A.07 model-free verification."
  PYTHONPATH="$REPO/langchain:$REPO${PYTHONPATH:+:$PYTHONPATH}" \
    "$PYTHON" - <<'PY_IMPORT'
from agentic_harness_langgraph.state import LangGraphRunState, advance_target, initial_state
from agentic_harness_langgraph.batch_runner import TARGET_COUNT, BOUNDARY_AFTER_SEQUENCE, RESUME_AT_SEQUENCE
assert TARGET_COUNT == 12
assert BOUNDARY_AFTER_SEQUENCE == 6
assert RESUME_AT_SEQUENCE == 7
print("[PASS] Repository-local Step 2A.07 package imports resolved.")
PY_IMPORT
  "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state active
  printf '[PASS] Step 2A.07 static preflight passed with model access blocked.\n'
}

append_failed_once(){
  local rel="$1"
  mkdir -p "$ROOT"
  touch "$FAILED"
  if ! grep -Fxq "$rel" "$FAILED"; then
    printf '%s\n' "$rel" >> "$FAILED"
  fi
}

classify_failed(){
  local rel="$1" reason="$2"
  local dir="$REPO/$rel"
  mkdir -p "$dir"
  "$PYTHON" - "$dir/failed-state.json" "$rel" "$reason" <<'PY'
import json,sys
from datetime import datetime,timezone
out,rel,reason=sys.argv[1:]
value={
  "schema_version":1,
  "status":"failed",
  "evidence_path":rel,
  "failure_class":"step2a07-model-free-construction-verification",
  "reason":reason[:500],
  "model_call_count":0,
  "drupal_semantic_call_count":0,
  "recommendation_write_count":0,
  "failed_at":datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
}
open(out,'w',encoding='utf-8').write(json.dumps(value,indent=2,sort_keys=True)+'\n')
PY
  (
    cd "$dir"
    find . -maxdepth 1 -type f ! -name package-files-sha256.txt -printf '%f\n' | sort | xargs -r sha256sum > package-files-sha256.txt
  )
  append_failed_once "$rel"
  rm -f "$CANDIDATE"
}

verify(){
  static_preflight
  [[ ! -e "$CANDIDATE" ]] || fail "A Step 2A.07 candidate already exists; inspect/certify instead of rerunning."
  [[ ! -e "$LATEST" ]] || fail "Step 2A.07 is already complete."
  if [[ -s "$FAILED" ]]; then
    [[ -s "$RETRY_AUTH" ]] || fail "A prior Step 2A.07 verification failed. A reviewed repair package must authorize a new attempt."
    [[ -s "$LAST" ]] || fail "Failed-attempt history exists but LAST pointer is missing."
    prior_rel="$(<"$LAST")"
    [[ "$(<"$RETRY_AUTH")" == "$prior_rel" ]] || fail "Step 2A.07 retry authorization does not match the retained failed attempt."
    grep -Fxq "$prior_rel" "$FAILED" || fail "Retry authorization does not reference a retained failed run."
    rm -f "$RETRY_AUTH"
    printf '[PASS] Consumed one-shot retry authorization for retained failed attempt: %s\n' "$prior_rel"
  fi
  mkdir -p "$ROOT"
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  suffix="$(printf '%08x' "$$")"
  gate_id="gate2a-step07-${stamp}-${suffix}"
  graph_id="langgraph-${stamp}-${suffix}"
  [[ "$graph_id" =~ ^langgraph-[0-9]{8}T[0-9]{6}Z-[a-z0-9]{4,12}$ ]] || fail "Generated construction run ID violates the frozen LangGraph run-id format."
  rel="evidence/gates/gate-2a/batch-runner/${gate_id}"
  dir="$REPO/$rel"
  printf '%s\n' "$rel" > "$LAST"

  set +e
  PYTHONPATH="$REPO/langchain:$REPO${PYTHONPATH:+:$PYTHONPATH}" \
    "$PYTHON" "$CORE" --repo "$REPO" --evidence "$dir" --run-id "$graph_id" --mode construction-test
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    classify_failed "$rel" "construction-test core exited nonzero"
    fail "Step 2A.07 construction verification failed; retained and retry-blocked: $rel"
  fi

  printf '%s\n' "$rel" > "$CANDIDATE"
  set +e
  audit_output="$("$PYTHON" "$AUDITOR" --repo "$REPO" --document-state active 2>&1)"
  rc=$?
  set -e
  printf '%s\n' "$audit_output"
  if [[ $rc -ne 0 ]]; then
    classify_failed "$rel" "post-construction candidate audit exited nonzero"
    fail "Step 2A.07 candidate audit failed; retained and retry-blocked: $rel"
  fi

  printf '[PASS] Step 2A.07 model-free construction verification passed.\n'
  printf '[PASS] Candidate evidence: %s\n' "$rel"
  printf '[PASS] Model/provider calls: 0; Drupal semantic calls/mutations: 0/0.\n'
  printf '[STOP] Inspect candidate evidence before model-free certification. Step 2A.08 remains locked.\n'
}

certify(){
  static_preflight
  [[ -s "$CANDIDATE" ]] || fail "No Step 2A.07 candidate exists."
  [[ ! -e "$LATEST" ]] || fail "Step 2A.07 is already certified."
  rel="$(<"$CANDIDATE")"
  [[ -d "$REPO/$rel" ]] || fail "Candidate evidence directory is missing: $rel"
  "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state active

  backup="$(mktemp -d)"
  cp "$REPO/AGENTS.md" "$backup/AGENTS.md"
  cp "$REPO/PLAN.md" "$backup/PLAN.md"
  cp "$REPO/README.md" "$backup/README.md"
  mkdir -p "$backup/docs"
  cp "$REPO/docs/CURRENT-STATUS.md" "$backup/docs/CURRENT-STATUS.md"
  rollback(){
    set +e
    cp "$backup/AGENTS.md" "$REPO/AGENTS.md"
    cp "$backup/PLAN.md" "$REPO/PLAN.md"
    cp "$backup/README.md" "$REPO/README.md"
    cp "$backup/docs/CURRENT-STATUS.md" "$REPO/docs/CURRENT-STATUS.md"
    rm -f "$LATEST"
    rm -rf "$backup"
    set -e
  }
  trap rollback ERR
  "$PYTHON" "$STATE" --repo "$REPO" --state complete --run-dir "$rel"
  printf '%s\n' "$rel" > "$LATEST"
  "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state complete
  git -C "$REPO" diff --check
  trap - ERR
  rm -rf "$backup"
  printf '[PASS] Gate 2A Step 2A.07 model-free certification passed.\n'
  printf '[PASS] Accepted evidence: %s\n' "$rel"
  printf '[PASS] Model/provider calls: 0; Drupal semantic calls/mutations: 0/0.\n'
  printf '[STOP] Inspect evidence and diff before exact-scope staging or commit. Step 2A.08 remains locked.\n'
}

case "${1:-}" in
  verify) verify ;;
  certify) certify ;;
  audit) "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state complete ;;
  *)
    cat >&2 <<'EOF'
Usage: bash scripts/run-gate2a-step07-langgraph-batch-runner.sh {verify|certify|audit}

Step 2A.07 is intentionally model-free. This shell wrapper does not expose the
batch_runner.py live start/resume modes; Step 2A.08 owns that authorization.
EOF
    exit 2
    ;;
esac
