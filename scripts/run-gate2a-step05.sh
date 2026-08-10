#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRUPAL="$REPO/drupal"
PYTHON="$REPO/langchain/.venv/bin/python"
VALIDATOR_PYTHON="$REPO/crewai/.venv/bin/python"
VERTICAL="$REPO/langchain/agentic_harness_langgraph/vertical_slice.py"
AUDITOR="$REPO/scripts/gate2a_step05_audit.py"
FINALIZER="$REPO/scripts/gate2a_step05_finalize.py"
STATE="$REPO/scripts/gate2a_step05_state.py"
SCHEMA_VALIDATOR="$REPO/scripts/gate2a_step03_schema_validate.py"
BRANCH="gate-2a-step05-langgraph-canonical-vertical-slice"
EXPECTED_HEAD="c61a40003e4ef236a9c0e72afc0befc55608b153"
EVIDENCE_ROOT="$REPO/evidence/gates/gate-2a/canonical-slice"
RUNTIME_ROOT="$REPO/langchain/.gate2a-runtime"
CREDENTIALS="$DRUPAL/.secrets/phase0-step7-accounts.txt"
LAST="$EVIDENCE_ROOT/GATE2A-STEP05-LAST-RUN.txt"
FAILED="$EVIDENCE_ROOT/GATE2A-STEP05-FAILED-RUNS.txt"
CANDIDATE="$EVIDENCE_ROOT/GATE2A-STEP05-CANDIDATE.txt"
LATEST="$EVIDENCE_ROOT/GATE2A-STEP05-LATEST.txt"

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
  local out="$1"
  (cd "$DRUPAL" && bash scripts/run-phase0-step10.sh audit) >"$out"
}

snapshot_state(){
  local out="$1"
  (
    cd "$DRUPAL"
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
      ddev drush --quiet php:script scripts/gate1-step03-adapter-exercise.php -- snapshot
  ) >"$out"
}

restore_snapshot(){
  local name="$1"
  (
    cd "$DRUPAL"
    ddev snapshot restore "$name" >/dev/null
    ddev drush cr >/dev/null
    ddev snapshot --cleanup --name "$name" -y >/dev/null
  )
}

write_manifest(){
  local dir="$1"
  (
    cd "$dir"
    find . -maxdepth 1 -type f ! -name package-files-sha256.txt -printf '%f\n' \
      | sort | xargs -r sha256sum > package-files-sha256.txt
  )
}

append_failed(){
  local rel="$1"
  mkdir -p "$EVIDENCE_ROOT"
  touch "$FAILED"
  grep -Fx "$rel" "$FAILED" >/dev/null 2>&1 || printf '%s\n' "$rel" >>"$FAILED"
}

require_branch_head(){
  [[ "$(git -C "$REPO" branch --show-current)" == "$BRANCH" ]] || fail "Expected branch $BRANCH."
  [[ "$(git -C "$REPO" rev-parse HEAD)" == "$EXPECTED_HEAD" ]] || fail "Expected uncommitted Step 2A.05 install on $EXPECTED_HEAD."
}

preflight_static(){
  require_branch_head
  [[ -x "$PYTHON" ]] || fail "LangGraph virtualenv Python missing."
  [[ -x "$VALIDATOR_PYTHON" ]] || fail "Schema-validator interpreter missing."
  [[ -f "$VERTICAL" && -f "$AUDITOR" && -f "$FINALIZER" && -f "$STATE" ]] || fail "Step 2A.05 implementation incomplete."

  "$PYTHON" - <<'PY'
import importlib.metadata as md
expected={"langchain":"1.3.14","langgraph":"1.2.10","langgraph-checkpoint-sqlite":"3.1.1"}
for name,want in expected.items():
    got=md.version(name)
    if got != want:
        raise SystemExit(f"[ERROR] {name}={got}, expected {want}")
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
print("[PASS] Pinned LangGraph/model-wrapper imports and versions passed.")
PY

  "$VALIDATOR_PYTHON" - <<'PY'
import jsonschema, referencing
print("[PASS] Frozen-schema validator interpreter preflight passed.")
PY

  PYTHONPATH="$REPO/langchain:$REPO${PYTHONPATH:+:$PYTHONPATH}" \
    "$PYTHON" - <<'PY'
from agentic_harness_langgraph.vertical_slice import ModelOutput, MODEL_ID, TEMPERATURE
assert MODEL_ID == "gpt-4.1-mini-2025-04-14"
assert TEMPERATURE == 0.0
assert ModelOutput.model_json_schema()["additionalProperties"] is False
print("[PASS] Repository-local Step 2A.05 import and raw-output schema smoke passed.")
PY

  mkdir -p "$RUNTIME_ROOT"
  local probe="$RUNTIME_ROOT/.gate2a-step05-ignore-probe.sqlite"
  : >"$probe"
  git -C "$REPO" check-ignore -q "langchain/.gate2a-runtime/.gate2a-step05-ignore-probe.sqlite" \
    || { rm -f "$probe"; fail "LangGraph runtime root is not gitignored."; }
  rm -f "$probe"

  "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state active
  pass "Gate 2A Step 2A.05 static preflight passed."
}

preflight_live(){
  preflight_static
  [[ -f "$CREDENTIALS" ]] || fail "Local Drupal credentials file is missing."
  [[ -n "${OPENAI_API_KEY:-}" ]] || fail "OPENAI_API_KEY is required for the single authorized model call."
  [[ ! -e "$LATEST" ]] || fail "Step 2A.05 is already certified; live run is closed."
  [[ ! -e "$CANDIDATE" ]] || fail "A passing Step 2A.05 candidate already exists; do not rerun it."
  [[ ! -e "$LAST" ]] || fail "A Step 2A.05 attempt already exists. Human review/package repair is required before any retry."

  bash "$REPO/scripts/run-gate1-step07-drupal-ai-certification-and-handoff.sh" audit >/dev/null
  bash "$REPO/scripts/run-gate05-step05.sh" audit >/dev/null
  pass "Frozen Gate 1 and Gate 0.5 audits passed before live execution."
}

retain_failure(){
  local run_dir="$1" run_rel="$2" message="$3" rc="$4"
  printf 'FAIL: %s Retained run: %s\n' "$message" "$run_rel" >"$run_dir/run-failure.txt"
  append_failed "$run_rel"
  write_manifest "$run_dir"
  printf '[STOP] Step 2A.05 failed; retained evidence at %s. Do not rerun without human review.\n' "$run_rel" >&2
  return "$rc"
}

run_live(){
  preflight_live

  mkdir -p "$EVIDENCE_ROOT" "$RUNTIME_ROOT"
  local stamp suffix run_id evidence_name run_rel run_dir snapshot_name agent_password
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  suffix="$(printf '%08x' "$$")"
  run_id="langgraph-${stamp}-${suffix}"
  evidence_name="gate2a-step05-${stamp}-${suffix}"
  run_rel="evidence/gates/gate-2a/canonical-slice/${evidence_name}"
  run_dir="$REPO/$run_rel"
  mkdir -p "$run_dir"
  printf '%s\n' "$run_rel" >"$LAST"
  printf '%s\n' "$run_id" >"$run_dir/run-id.txt"

  seeded_clean "$run_dir/seeded-clean-before.log"
  snapshot_state "$run_dir/before-state.json"

  snapshot_name="gate2a-step05-pre-${stamp}-${suffix}"
  info "Creating exact pre-run DDEV snapshot..."
  (cd "$DRUPAL" && ddev snapshot --name "$snapshot_name" >/dev/null)

  local restored=0
  cleanup_snapshot(){
    local status=$?
    set +e
    unset GATE2A_DRUPAL_PASSWORD GATE2A_DRUPAL_USERNAME GATE2A_DRUPAL_BASE_URL
    if [[ "$restored" -eq 0 ]]; then
      restore_snapshot "$snapshot_name" || status=1
    fi
    exit "$status"
  }
  trap cleanup_snapshot EXIT INT TERM

  agent_password="$(latest_secret agent_bot)"
  [[ -n "$agent_password" ]] || fail "agent_bot credential is empty."
  export GATE2A_DRUPAL_USERNAME="agent_bot"
  export GATE2A_DRUPAL_PASSWORD="$agent_password"
  export GATE2A_DRUPAL_BASE_URL="$(resolve_site_url)"

  info "Executing one authorized model call for canonical target sequence 1..."
  set +e
  PYTHONPATH="$REPO/langchain:$REPO${PYTHONPATH:+:$PYTHONPATH}" \
    "$PYTHON" "$VERTICAL" --repo "$REPO" --evidence "$run_dir" --run-id "$run_id"
  local core_rc=$?
  set -e

  # Preserve the actual Drupal state reached by the attempt, even when the core
  # stopped after a write. This is evidence only; restoration follows next.
  snapshot_state "$run_dir/during-state.json" || true

  unset GATE2A_DRUPAL_PASSWORD GATE2A_DRUPAL_USERNAME GATE2A_DRUPAL_BASE_URL
  info "Restoring exact pre-run DDEV snapshot..."
  restore_snapshot "$snapshot_name"
  restored=1
  seeded_clean "$run_dir/seeded-clean-after.log"
  snapshot_state "$run_dir/after-state.json"

  trap - EXIT INT TERM

  if [[ "$core_rc" -ne 0 ]]; then
    retain_failure "$run_dir" "$run_rel" "Canonical vertical-slice core exited with code $core_rc." "$core_rc"
    return "$core_rc"
  fi

  "$VALIDATOR_PYTHON" "$SCHEMA_VALIDATOR" \
    --schema-dir "$REPO/shared/schemas" --schema langgraph-model-output.schema.json \
    <"$run_dir/model-output.json" >"$run_dir/model-output-schema-validation.json" \
    || { retain_failure "$run_dir" "$run_rel" "Raw model-output schema validation failed." 20; return 20; }

  "$VALIDATOR_PYTHON" "$SCHEMA_VALIDATOR" \
    --schema-dir "$REPO/shared/schemas" --schema recommendation.schema.json \
    <"$run_dir/recommendation.json" >"$run_dir/recommendation-schema-validation.json" \
    || { retain_failure "$run_dir" "$run_rel" "Recommendation schema validation failed." 21; return 21; }

  "$VALIDATOR_PYTHON" "$SCHEMA_VALIDATOR" \
    --schema-dir "$REPO/shared/schemas" --schema langgraph-run-state.schema.json \
    <"$run_dir/state-after-slice.json" >"$run_dir/state-schema-validation.json" \
    || { retain_failure "$run_dir" "$run_rel" "LangGraph state schema validation failed." 22; return 22; }

  if ! "$PYTHON" "$FINALIZER" --repo "$REPO" --evidence "$run_dir" --run-id "$run_id"; then
    retain_failure "$run_dir" "$run_rel" "Post-run evidence finalization failed." 23
    return 23
  fi

  if ! "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state active --run-dir "$run_rel"; then
    retain_failure "$run_dir" "$run_rel" "Post-run candidate audit failed." 24
    return 24
  fi

  printf '%s\n' "$run_rel" >"$CANDIDATE"
  pass "Gate 2A Step 2A.05 canonical vertical-slice candidate passed."
  pass "Candidate evidence: $run_rel"
  pass "Model calls: 1; automatic retries: 0; Drupal semantic calls: 6; temporary recommendation writes: 1."
  pass "Source Article mutation/publication: 0/0; Drupal restored to seeded-clean."
  printf '[STOP] Inspect the candidate evidence before running package.sh certify. Do not rerun the model call.\n'
}

certify(){
  preflight_static
  [[ -s "$CANDIDATE" ]] || fail "No passing Step 2A.05 candidate exists."
  [[ ! -e "$LATEST" ]] || fail "Step 2A.05 is already certified."
  local run_rel run_dir
  run_rel="$(<"$CANDIDATE")"
  [[ "$run_rel" == evidence/gates/gate-2a/canonical-slice/gate2a-step05-* ]] || fail "Candidate pointer is invalid."
  run_dir="$REPO/$run_rel"
  [[ -d "$run_dir" ]] || fail "Candidate directory is unavailable."

  "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state active --run-dir "$run_rel"

  local backup
  backup="$(mktemp -d)"
  mkdir -p "$backup/docs"
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
    rm -f "$LATEST"
    set -e
  }

  if ! "$PYTHON" "$STATE" --repo "$REPO" --state complete --run-dir "$run_rel"; then
    rollback
    rm -rf "$backup"
    fail "Step 2A.05 candidate passed but document-state certification failed."
  fi

  local tmp_latest="${LATEST}.tmp"
  printf '%s\n' "$run_rel" >"$tmp_latest"
  mv "$tmp_latest" "$LATEST"

  if ! "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state complete; then
    rollback
    rm -rf "$backup"
    fail "Step 2A.05 complete-state audit failed; certification rolled back."
  fi
  rm -rf "$backup"

  git -C "$REPO" diff --check
  pass "Gate 2A Step 2A.05 candidate certified without another model or Drupal call."
  pass "Accepted evidence: $run_rel"
  pass "Certification calls: model/provider 0; Drupal 0; recommendation writes 0."
  printf '[STOP] Review accepted evidence and repository diff before staging or committing.\n'
}

case "$MODE" in
  preflight) preflight_static ;;
  run) run_live ;;
  certify) certify ;;
  audit) "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state complete ;;
  *) fail "Usage: bash scripts/run-gate2a-step05.sh {preflight|run|certify|audit}" ;;
esac
