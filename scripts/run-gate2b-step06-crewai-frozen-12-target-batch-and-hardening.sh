#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-}"
REPO="${2:-$(pwd)}"
RUN_ID="${3:-}"
PY="$REPO/crewai/.venv/bin/python"
export PYTHONPATH="$REPO/crewai:$REPO${PYTHONPATH:+:$PYTHONPATH}"

PREDECESSOR="2ad5fc9faf29bf54983ae2c61f3f7cb0f9b28148"
BRANCH="gate-2b-step06-crewai-frozen-12-target-batch-and-hardening"
SNAPSHOT_ID="gate2b-step06-post-step2b05-recovery-20260826T152003Z"
SNAPSHOT_REL="drupal/.ddev/db_snapshots/${SNAPSHOT_ID}-mariadb_11.8.zst"
SNAPSHOT_SHA="4ba4cece2d30a5f90699afdf9a2ab2094f0d902213c66cdc0b40dfa466094906"
SNAPSHOT_SIZE="4112532"
ACTIVATION_ROOT="$REPO/evidence/gates/gate-2b/frozen-batch-activation"
ACTIVATION_ID="${SNAPSHOT_ID}-activation"
ACTIVATION_DIR="$ACTIVATION_ROOT/$ACTIVATION_ID"
HTTP_READINESS_ROOT="$REPO/evidence/gates/gate-2b/frozen-batch-http-readiness"
HTTP_READINESS_ID="${SNAPSHOT_ID}-http-readiness-v102"
HTTP_READINESS_DIR="$HTTP_READINESS_ROOT/$HTTP_READINESS_ID"
DISPOSITION_ROOT="$REPO/evidence/gates/gate-2b/frozen-batch-failure-disposition"
FAILED_RUN_ID="crewai-20260827T125501Z-c5381188"
FAILED_ATTEMPT_ID="gate2b-step06-attempt-20260827T125530Z-185709"
DISPOSITION_DIR="$DISPOSITION_ROOT/$FAILED_RUN_ID/$FAILED_ATTEMPT_ID-v102"
RUNTIME_ROOT="$REPO/crewai/.runtime/gate2b-step06"
SUCCESS_ROOT="$REPO/evidence/results/crewai"
CONTROL_ROOT="$REPO/evidence/gates/gate-2b/frozen-batch"
SUCCESS_RUN_ID="crewai-20260827T174606Z-6249d844"
SUPPLEMENT_ROOT="$REPO/evidence/gates/gate-2b/frozen-batch-governance-supplement"
SUPPLEMENT_ID="gate2b-step06-governance-supplement-v103"
SUPPLEMENT_DIR="$SUPPLEMENT_ROOT/$SUCCESS_RUN_ID/$SUPPLEMENT_ID"
FINAL_GOVERNANCE_ROOT="$REPO/evidence/gates/gate-2b/frozen-batch-final-governance"
FINAL_GOVERNANCE_ID="gate2b-step06-final-governance-v104"
FINAL_GOVERNANCE_DIR="$FINAL_GOVERNANCE_ROOT/$SUCCESS_RUN_ID/$FINAL_GOVERNANCE_ID"

fail() { printf '[FAIL] %s\n' "$*" >&2; exit 1; }
pass() { printf '[PASS] %s\n' "$*"; }

require_repo() {
  [[ "$(git -C "$REPO" branch --show-current)" == "$BRANCH" ]] || fail "Expected Step 2B.06 feature branch"
  [[ "$(git -C "$REPO" rev-parse HEAD)" == "$PREDECESSOR" ]] || fail "HEAD drifted"
  [[ "$(git -C "$REPO" rev-parse origin/main)" == "$PREDECESSOR" ]] || fail "origin/main drifted"
  [[ -z "$(git -C "$REPO" diff --cached --name-only)" ]] || fail "Index is not clean"
  [[ "$(sha256sum "$REPO/crewai/uv.lock" | awk '{print $1}')" ==     "855e5edff2cb86eb64ea9856d239b19010e7d3b1f80c40e370ed81d66b8e4e7c" ]] || fail "CrewAI lock drifted"
}

require_snapshot() {
  local path="$REPO/$SNAPSHOT_REL"
  [[ -f "$path" && ! -L "$path" ]] || fail "Bound recovery snapshot is missing or unsafe"
  [[ "$(stat -c '%s' "$path")" == "$SNAPSHOT_SIZE" ]] || fail "Snapshot size drifted"
  [[ "$(sha256sum "$path" | awk '{print $1}')" == "$SNAPSHOT_SHA" ]] || fail "Snapshot hash drifted"
}

capture() {
  "$PY" "$REPO/scripts/gate2b_step06_batch.py" capture --repo "$REPO"
}

require_no_batch_runtime() {
  [[ ! -d "$RUNTIME_ROOT" || -z "$(find "$RUNTIME_ROOT" -mindepth 1 -maxdepth 1 -print -quit)" ]] ||
    fail "An authoritative Step 2B.06 runtime already exists"
}

case "$MODE" in
  preflight)
    require_repo
    require_snapshot
    exec "$PY" "$REPO/scripts/gate2b_step06_batch.py" preflight --repo "$REPO"
    ;;
  rehearse)
    exec "$PY" "$REPO/scripts/gate2b_step06_rehearsal.py" --repo "$REPO"
    ;;
  audit)
    case "${RUN_ID:-activation}" in
      activation)
        exec "$PY" "$REPO/scripts/gate2b_step06_audit.py" --repo "$REPO"           --mode activation --evidence "$ACTIVATION_DIR"
        ;;
      http-readiness)
        exec "$PY" "$REPO/scripts/gate2b_step06_audit.py" --repo "$REPO" \
          --mode http-readiness --evidence "$HTTP_READINESS_DIR"
        ;;
      failure-disposition)
        exec "$PY" "$REPO/scripts/gate2b_step06_audit.py" --repo "$REPO" \
          --mode failure-disposition --evidence "$DISPOSITION_DIR"
        ;;
      governance-supplement)
        exec "$PY" "$REPO/scripts/gate2b_step06_audit.py" --repo "$REPO" \
          --mode governance-supplement --evidence "$SUPPLEMENT_DIR" \
          --batch "$SUCCESS_ROOT/$SUCCESS_RUN_ID"
        ;;
      final-composite)
        exec "$PY" "$REPO/scripts/gate2b_step06_audit.py" --repo "$REPO" \
          --mode final-composite --evidence "$SUCCESS_ROOT/$SUCCESS_RUN_ID" \
          --supplement "$SUPPLEMENT_DIR" \
          --final-governance "$FINAL_GOVERNANCE_DIR"
        ;;
      *)
        exec "$PY" "$REPO/scripts/gate2b_step06_audit.py" --repo "$REPO"           --mode final --evidence "$SUCCESS_ROOT/$RUN_ID"
        ;;
    esac
    ;;
  final-governance-only)
    require_repo
    require_snapshot
    [[ "${GATE2B_STEP06_FINAL_GOVERNANCE_AUTHORIZED:-}" == \
      "model-free-post-finalization-governance-v104" ]] ||
      fail "Explicit model-free final-governance authorization is required"
    [[ -d "$SUCCESS_ROOT/$SUCCESS_RUN_ID" ]] || fail "Finalized closure is absent"
    [[ -d "$SUPPLEMENT_DIR" ]] || fail "Accepted governance supplement is absent"
    [[ ! -e "$FINAL_GOVERNANCE_DIR" ]] || fail "Final governance already exists"
    [[ -s "$CONTROL_ROOT/LATEST" && "$(<"$CONTROL_ROOT/LATEST")" == "$SUCCESS_RUN_ID" ]] ||
      fail "Finalized successful identity differs"
    [[ ! -e "$CONTROL_ROOT/BATCH-AWAITING-RESTORE" ]] ||
      fail "Batch-stage lifecycle has not been finalized"
    "$PY" "$REPO/scripts/gate2b_step06_audit.py" --repo "$REPO" \
      --mode final --evidence "$SUCCESS_ROOT/$SUCCESS_RUN_ID"
    temp="$(mktemp -d -t gate2b-step06-final-governance.XXXXXX)"
    trap 'rm -rf -- "$temp"' EXIT
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
      "$PY" "$REPO/scripts/gate2b_step06_batch.py" capture --repo "$REPO" \
      >"$temp/restored-state.json"
    mkdir -p "$(dirname "$FINAL_GOVERNANCE_DIR")"
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
      "$PY" "$REPO/scripts/gate2b_step06_batch.py" record-final-governance \
      --repo "$REPO" --batch "$SUCCESS_ROOT/$SUCCESS_RUN_ID" \
      --supplement "$SUPPLEMENT_DIR" --output "$FINAL_GOVERNANCE_DIR" \
      --restored-state "$temp/restored-state.json"
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
      "$PY" "$REPO/scripts/gate2b_step06_audit.py" --repo "$REPO" \
      --mode final-composite --evidence "$SUCCESS_ROOT/$SUCCESS_RUN_ID" \
      --supplement "$SUPPLEMENT_DIR" \
      --final-governance "$FINAL_GOVERNANCE_DIR"
    pass "STEP_2B_06_COMPLETE / RESTORE_VERIFIED / FINAL_GOVERNANCE_ACCEPTED / SNAPSHOT_RETAINED"
    ;;
  governance-supplement-only)
    require_repo
    require_snapshot
    [[ "${GATE2B_STEP06_SUPPLEMENT_AUTHORIZED:-}" == \
      "model-free-batch-governance-supplement-v103" ]] ||
      fail "Explicit model-free governance-supplement authorization is required"
    [[ -d "$SUCCESS_ROOT/$SUCCESS_RUN_ID" ]] || fail "Successful batch-stage family is absent"
    [[ ! -e "$SUPPLEMENT_DIR" ]] || fail "Governance supplement already exists"
    [[ -s "$CONTROL_ROOT/BATCH-AWAITING-RESTORE" ]] || fail "No accepted batch awaits restoration"
    [[ "$(<"$CONTROL_ROOT/BATCH-AWAITING-RESTORE")" == "$SUCCESS_RUN_ID" ]] ||
      fail "Awaiting-restore identity differs"
    mkdir -p "$(dirname "$SUPPLEMENT_DIR")"
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
      "$PY" "$REPO/scripts/gate2b_step06_batch.py" record-governance-supplement \
      --repo "$REPO" --batch "$SUCCESS_ROOT/$SUCCESS_RUN_ID" --output "$SUPPLEMENT_DIR"
    "$PY" "$REPO/scripts/gate2b_step06_audit.py" --repo "$REPO" \
      --mode batch --evidence "$SUCCESS_ROOT/$SUCCESS_RUN_ID" \
      --supplement "$SUPPLEMENT_DIR"
    "$PY" "$REPO/scripts/gate2b_step06_audit.py" --repo "$REPO" \
      --mode governance-supplement --evidence "$SUPPLEMENT_DIR" \
      --batch "$SUCCESS_ROOT/$SUCCESS_RUN_ID"
    pass "BATCH_STAGE_ACCEPTED / BATCH_COMPLETE / AWAITING_RESTORE"
    ;;
  activate-only)
    require_repo
    require_snapshot
    require_no_batch_runtime
    [[ "${GATE2B_STEP06_ACTIVATION_AUTHORIZED:-}" == "model-free-post-reset-activation" ]] ||
      fail "Explicit model-free activation authorization is required"
    [[ ! -e "$ACTIVATION_DIR" ]] || fail "Activation was already accepted; second activation blocked"
    temp="$(mktemp -d -t gate2b-step06-activation.XXXXXX)"
    trap 'rm -rf -- "$temp"' EXIT
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL       "$PY" "$REPO/scripts/gate2b_step06_batch.py" capture --repo "$REPO" >"$temp/before.json"
    (
      cd "$REPO/drupal"
      env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL         ddev drush en agentic_harness_tools -y >/dev/null
      ddev drush --quiet php:eval '
        $role = \Drupal\user\Entity\Role::load("agent_service");
        if (!$role) { throw new \RuntimeException("agent_service role missing"); }
        $role->grantPermission("use agentic harness discovery tools");
        $role->save();
        $editor = \Drupal\user\Entity\Role::load("content_editor");
        if (!$editor || $editor->hasPermission("use agentic harness discovery tools")) {
          throw new \RuntimeException("content_editor discovery boundary failed");
        }
      '
      ddev drush en agentic_harness_drupal_ai -y >/dev/null
      ddev drush cr >/dev/null
      env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL         bash scripts/run-phase0-step7.sh audit >/dev/null
    )
    (cd "$REPO" && env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL       bash scripts/run-gate05-step05.sh audit >/dev/null)
    "$PY" "$REPO/scripts/gate2b_step06_batch.py" capture --repo "$REPO" >"$temp/after.json"
    "$PY" "$REPO/scripts/gate2b_step06_batch.py" record-activation --repo "$REPO"       --output "$ACTIVATION_DIR" --before "$temp/before.json" --after "$temp/after.json"
    mkdir -p "$ACTIVATION_ROOT"
    printf '%s\n' "$ACTIVATION_ID" >"$ACTIVATION_ROOT/LATEST"
    "$PY" "$REPO/scripts/gate2b_step06_audit.py" --repo "$REPO"       --mode activation --evidence "$ACTIVATION_DIR"
    pass "ACTIVATION_COMPLETE / MODEL_READY"
    ;;
  http-readiness-only)
    require_repo
    require_snapshot
    [[ "${GATE2B_STEP06_HTTP_READINESS_AUTHORIZED:-}" == \
      "model-free-authenticated-discovery-preflight" ]] ||
      fail "Explicit authenticated HTTP readiness authorization is required"
    [[ -d "$ACTIVATION_DIR" ]] || fail "MODEL_READY activation evidence is absent"
    [[ ! -e "$HTTP_READINESS_DIR" ]] ||
      fail "Authenticated HTTP readiness was already accepted"
    [[ ! -e "$DISPOSITION_DIR" ]] || fail "Failure disposition already exists"
    [[ -d "$RUNTIME_ROOT/$FAILED_RUN_ID" ]] || fail "Historical failed runtime is absent"
    if [[ -d "$RUNTIME_ROOT" ]]; then
      while IFS= read -r runtime_dir; do
        [[ "$(basename "$runtime_dir")" == "$FAILED_RUN_ID" ]] ||
          fail "Unexpected authoritative Step 2B.06 runtime exists"
      done < <(find "$RUNTIME_ROOT" -mindepth 1 -maxdepth 1 -type d -print)
    fi
    [[ ! -e "$CONTROL_ROOT/BATCH-AWAITING-RESTORE" ]] ||
      fail "An accepted batch already awaits restoration"
    (cd "$REPO" && env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL \
      -u CREWAI_CANDIDATE_MODEL bash scripts/run-gate05-step05.sh audit >/dev/null)
    mkdir -p "$HTTP_READINESS_ROOT" "$(dirname "$DISPOSITION_DIR")"
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
      "$PY" "$REPO/scripts/gate2b_step06_batch.py" record-http-readiness \
      --repo "$REPO" --output "$HTTP_READINESS_DIR" \
      --activation "$ACTIVATION_DIR" --disposition-output "$DISPOSITION_DIR"
    printf '%s\n' "$HTTP_READINESS_ID" >"$HTTP_READINESS_ROOT/LATEST"
    "$PY" "$REPO/scripts/gate2b_step06_audit.py" --repo "$REPO" \
      --mode http-readiness --evidence "$HTTP_READINESS_DIR"
    "$PY" "$REPO/scripts/gate2b_step06_audit.py" --repo "$REPO" \
      --mode failure-disposition --evidence "$DISPOSITION_DIR"
    pass "AUTHENTICATED_HTTP_PREFLIGHT_PASS / MODEL_READY / ZERO_RUN_IDS"
    ;;
  batch-only)
    require_repo
    require_snapshot
    [[ "$RUN_ID" =~ ^crewai-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$ ]] ||
      fail "batch-only requires a fresh CrewAI run ID"
    [[ "${GATE2B_STEP06_BATCH_AUTHORIZED:-}" == "one-serial-12-target-attempt" ]] ||
      fail "Explicit batch-only authorization is required"
    [[ "$RUN_ID" != "$FAILED_RUN_ID" ]] || fail "Historical failed run ID is consumed"
    [[ -d "$ACTIVATION_DIR" ]] || fail "MODEL_READY activation evidence is absent"
    [[ -d "$HTTP_READINESS_DIR" ]] ||
      fail "Authenticated HTTP readiness evidence is absent"
    [[ ! -e "$RUNTIME_ROOT/$RUN_ID" && ! -e "$SUCCESS_ROOT/$RUN_ID" ]] ||
      fail "Stale or consumed authoritative identity"
    [[ ! -e "$CONTROL_ROOT/BATCH-AWAITING-RESTORE" ]] ||
      fail "Another accepted batch already awaits restoration"
    (cd "$REPO" && env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
      bash scripts/run-gate05-step05.sh audit >/dev/null)
    "$PY" "$REPO/scripts/gate2b_step06_audit.py" --repo "$REPO" \
      --mode http-readiness --evidence "$HTTP_READINESS_DIR" >/dev/null
    attempt="$REPO/evidence/gates/gate-2b/frozen-batch-failures/$RUN_ID/gate2b-step06-attempt-$(date -u +%Y%m%dT%H%M%SZ)-$$"
    mkdir -p "$(dirname "$attempt")"
    control="$(mktemp -d -t gate2b-step06-control.XXXXXX)"
    trap 'rm -rf -- "$control"' EXIT
    mkdir -p "$control/xdg/data" "$control/xdg/config" "$control/xdg/cache"
    export XDG_DATA_HOME="$control/xdg/data" XDG_CONFIG_HOME="$control/xdg/config" XDG_CACHE_HOME="$control/xdg/cache"
    "$PY" "$REPO/scripts/gate2b_step06_batch.py" run-batch --repo "$REPO" \
      --output "$attempt" --run-id "$RUN_ID" --runtime-root "$RUNTIME_ROOT" \
      --activation "$ACTIVATION_DIR" --readiness "$HTTP_READINESS_DIR"
    "$PY" "$REPO/scripts/gate2b_step06_audit.py" --repo "$REPO"       --mode batch --evidence "$attempt"
    mkdir -p "$SUCCESS_ROOT" "$CONTROL_ROOT"
    mv "$attempt" "$SUCCESS_ROOT/$RUN_ID"
    printf '%s\n' "$RUN_ID" >"$CONTROL_ROOT/BATCH-AWAITING-RESTORE"
    pass "BATCH_COMPLETE / AWAITING_RESTORE"
    ;;
  restore-only)
    require_repo
    require_snapshot
    [[ "$RUN_ID" =~ ^crewai-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$ ]] ||
      fail "restore-only requires the completed batch run ID"
    [[ "${GATE2B_STEP06_RESTORE_AUTHORIZED:-}" == "restore-retained-step2b05-snapshot-once" ]] ||
      fail "Explicit restore-only authorization is required"
    [[ -s "$CONTROL_ROOT/BATCH-AWAITING-RESTORE" ]] || fail "No completed batch awaits restoration"
    [[ "$(<"$CONTROL_ROOT/BATCH-AWAITING-RESTORE")" == "$RUN_ID" ]] ||
      fail "Completed batch identity differs"
    evidence="$SUCCESS_ROOT/$RUN_ID"
    [[ -d "$SUPPLEMENT_DIR" ]] || fail "Accepted governance supplement is absent"
    "$PY" "$REPO/scripts/gate2b_step06_audit.py" --repo "$REPO" \
      --mode batch --evidence "$evidence" --supplement "$SUPPLEMENT_DIR"
    "$PY" "$REPO/scripts/gate2b_step06_audit.py" --repo "$REPO" \
      --mode governance-supplement --evidence "$SUPPLEMENT_DIR" --batch "$evidence"
    temp="$(mktemp -d -t gate2b-step06-restore.XXXXXX)"
    trap 'rm -rf -- "$temp"' EXIT
    "$PY" "$REPO/scripts/gate2b_step06_batch.py" capture --repo "$REPO" >"$temp/pre-restore.json"
    (
      cd "$REPO/drupal"
      ddev snapshot restore "$SNAPSHOT_ID" >/dev/null
      ddev drush cr >/dev/null
    )
    "$PY" "$REPO/scripts/gate2b_step06_batch.py" capture --repo "$REPO" >"$temp/post-restore.json"
    "$PY" "$REPO/scripts/gate2b_step06_batch.py" finalize-restore --repo "$REPO"       --output "$evidence" --before "$temp/pre-restore.json" --after "$temp/post-restore.json"
    "$PY" "$REPO/scripts/gate2b_step06_audit.py" --repo "$REPO"       --mode final --evidence "$evidence"
    mkdir -p "$(dirname "$FINAL_GOVERNANCE_DIR")"
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
      "$PY" "$REPO/scripts/gate2b_step06_batch.py" record-final-governance \
      --repo "$REPO" --batch "$evidence" --supplement "$SUPPLEMENT_DIR" \
      --output "$FINAL_GOVERNANCE_DIR" --restored-state "$temp/post-restore.json"
    "$PY" "$REPO/scripts/gate2b_step06_audit.py" --repo "$REPO" \
      --mode final-composite --evidence "$evidence" \
      --supplement "$SUPPLEMENT_DIR" --final-governance "$FINAL_GOVERNANCE_DIR"
    printf '%s\n' "$RUN_ID" >"$CONTROL_ROOT/LATEST"
    rm -f "$CONTROL_ROOT/BATCH-AWAITING-RESTORE"
    pass "RESTORE_VERIFIED / STEP_2B_06_COMPLETE"
    ;;
  *)
    echo "usage: $0 {preflight|rehearse|activate-only|http-readiness-only|batch-only|governance-supplement-only|restore-only|final-governance-only|audit} REPO [RUN_ID]" >&2
    exit 2
    ;;
esac
