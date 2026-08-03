#!/usr/bin/env bash
set -Eeuo pipefail

STEP12_SCRIPT_VERSION="1.0.1"
MODE="${1:-prepare}"
CONFIRMATION="${2:-}"

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_ROOT="$(cd "$TEST_DIR/../.." && pwd)"
PROJECT_ROOT="$LAB_ROOT/drupal"
PHP_HELPER="$PROJECT_ROOT/scripts/phase0-step12.php"
REPORT_HELPER="$TEST_DIR/step12-evidence.py"
LOG_ROOT="$LAB_ROOT/evidence/logs/revisions"
SCREENSHOT_ROOT="$LAB_ROOT/evidence/screenshots/revision-history"
ACTIVE_LINK="$LOG_ROOT/active"
LATEST_LINK="$LOG_ROOT/latest"
SITE_URL=""
RUN_ID=""
RUN_DIR=""
SCREENSHOT_DIR=""
MUTATION_STARTED=0
PREPARE_COMPLETE=0

info() { printf '[INFO] %s\n' "$*"; }
ok() { printf '[OK] %s\n' "$*"; }
warn() { printf '[WARNING] %s\n' "$*" >&2; }
fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<EOF
Phase 0 Step 12 revision-inspectability package, version $STEP12_SCRIPT_VERSION

Usage from drupal/:
  bash scripts/run-phase0-step12.sh preflight
  bash scripts/run-phase0-step12.sh prepare
  bash scripts/run-phase0-step12.sh audit
  bash scripts/run-phase0-step12.sh finish confirm
  bash scripts/run-phase0-step12.sh reset confirm
  bash scripts/run-phase0-step12.sh status

Workflow:
  1. prepare creates three pending suggestions and leaves them in Drupal.
  2. Review all three manually as editor_dana.
  3. audit verifies identity, timestamps, text, status, origin, and target revision.
  4. Capture screenshots using the generated checklist.
  5. finish confirm verifies screenshots exist and restores seeded-clean.
EOF
}

case "$MODE" in
  preflight|prepare|audit|status) ;;
  finish|reset)
    [[ "$CONFIRMATION" == "confirm" ]] || fail "Destructive mode requires confirmation: $MODE confirm"
    ;;
  help|-h|--help) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

resolve_site_url() {
  local value
  value="$(cd "$PROJECT_ROOT" && ddev exec printenv DDEV_PRIMARY_URL 2>/dev/null \
    | tr -d '\r' | grep -Eo 'https?://[^[:space:]]+' | tail -n 1 || true)"
  [[ -n "$value" ]] || fail "Unable to resolve DDEV_PRIMARY_URL."
  printf '%s' "${value%/}"
}

active_run_id() {
  [[ -L "$ACTIVE_LINK" ]] || fail "No active Step 12 run. Start with: bash scripts/run-phase0-step12.sh prepare"
  basename "$(readlink "$ACTIVE_LINK")"
}

set_active_paths() {
  RUN_ID="$(active_run_id)"
  RUN_DIR="$LOG_ROOT/$RUN_ID"
  SCREENSHOT_DIR="$SCREENSHOT_ROOT/$RUN_ID"
  [[ -d "$RUN_DIR" ]] || fail "Active evidence directory is missing: $RUN_DIR"
}

cleanup() {
  local exit_code=$?
  set +e
  if [[ "$MUTATION_STARTED" -eq 1 && "$PREPARE_COMPLETE" -eq 0 ]]; then
    warn "Step 12 preparation stopped after mutation began; restoring seeded-clean."
    (cd "$PROJECT_ROOT" && bash scripts/run-phase0-step10.sh reset) \
      > "${RUN_DIR:-/tmp}/emergency-reset.log" 2>&1 \
      || warn "Emergency reset failed. Run Step 10 reset manually."
    [[ -L "$ACTIVE_LINK" ]] && rm -f "$ACTIVE_LINK"
  fi
  exit "$exit_code"
}
trap cleanup EXIT INT TERM

base_requirements() {
  require_command ddev
  require_command python3
  require_command grep
  require_command find
  [[ -d "$PROJECT_ROOT" ]] || fail "Expected Drupal project at: $PROJECT_ROOT"
  [[ -f "$PROJECT_ROOT/.ddev/config.yaml" ]] || fail "Missing DDEV configuration."
  [[ -f "$PHP_HELPER" ]] || fail "Missing Step 12 PHP helper: $PHP_HELPER"
  [[ -f "$REPORT_HELPER" ]] || fail "Missing Step 12 evidence helper: $REPORT_HELPER"
  for script in run-phase0-step7.sh run-phase0-step8.sh run-phase0-step9.sh run-phase0-step10.sh; do
    [[ -f "$PROJECT_ROOT/scripts/$script" ]] || fail "Missing prerequisite runner: scripts/$script"
  done
  mkdir -p "$LOG_ROOT" "$SCREENSHOT_ROOT"
}

run_structural_preflight() {
  local log_path="$1"
  info "Starting DDEV and running prerequisite audits..."
  (
    cd "$PROJECT_ROOT"
    ddev start -y
    bash scripts/run-phase0-step7.sh audit
    bash scripts/run-phase0-step8.sh audit
    bash scripts/run-phase0-step10.sh audit
    ddev drush php:script scripts/phase0-step12.php -- preflight
  ) > "$log_path" 2>&1 || {
    cat "$log_path" >&2
    fail "Step 12 preflight failed. No Step 12 fixture was created."
  }
  SITE_URL="${SITE_URL:-$(resolve_site_url)}"
  ok "Preflight passed. Site URL: $SITE_URL"
}

mode_preflight() {
  base_requirements
  local temp_log
  temp_log="$(mktemp)"
  info "Phase 0 Step 12 runner version: $STEP12_SCRIPT_VERSION"
  run_structural_preflight "$temp_log"
  rm -f "$temp_log"
  ok "Preflight-only mode complete."
}

mode_prepare() {
  base_requirements
  [[ ! -L "$ACTIVE_LINK" ]] || fail "An active Step 12 run already exists: $(active_run_id). Finish or reset it first."

  RUN_ID="step12-$(date -u +'%Y%m%dT%H%M%SZ')-$$"
  RUN_DIR="$LOG_ROOT/$RUN_ID"
  SCREENSHOT_DIR="$SCREENSHOT_ROOT/$RUN_ID"
  mkdir -p "$RUN_DIR" "$SCREENSHOT_DIR"
  ln -sfn "$RUN_ID" "$ACTIVE_LINK"

  info "Phase 0 Step 12 runner version: $STEP12_SCRIPT_VERSION"
  run_structural_preflight "$RUN_DIR/preflight.log"

  info "Restoring seeded-clean immediately before fixture creation..."
  (cd "$PROJECT_ROOT" && bash scripts/run-phase0-step10.sh reset) \
    > "$RUN_DIR/reset-before-prepare.log" 2>&1 \
    || { cat "$RUN_DIR/reset-before-prepare.log" >&2; fail "Step 10 reset failed."; }

  MUTATION_STARTED=1
  info "Creating three pending suggestions as agent_bot..."
  (cd "$PROJECT_ROOT" && ddev drush php:script scripts/phase0-step12.php -- prepare) \
    > "$RUN_DIR/prepare.log" 2>&1 \
    || { cat "$RUN_DIR/prepare.log" >&2; fail "Step 12 fixture preparation failed."; }

  (cd "$PROJECT_ROOT" && ddev drush php:script scripts/phase0-step12.php -- json-pending) \
    > "$RUN_DIR/revision-evidence.json"

  python3 "$REPORT_HELPER" report \
    --evidence "$RUN_DIR/revision-evidence.json" \
    --site-url "$SITE_URL" \
    --run-dir "$RUN_DIR" \
    --screenshot-dir "$SCREENSHOT_DIR" \
    | tee "$RUN_DIR/report-output.txt"

  PREPARE_COMPLETE=1
  ok "Step 12 fixtures are ready and intentionally remain in Drupal for manual review."
  printf '\nReview as editor_dana:\n'
  printf '  1. Log in: %s/user/login\n' "$SITE_URL"
  printf '  2. Open instructions: %s\n' "$RUN_DIR/revision-evidence.html"
  printf '  3. Complete Cases A, B, and C exactly as shown.\n'
  printf '  4. Run: bash scripts/run-phase0-step12.sh audit\n'
  printf '\nDo not run Step 10 reset until the screenshots are captured.\n'
}

mode_audit() {
  base_requirements
  set_active_paths
  info "Phase 0 Step 12 runner version: $STEP12_SCRIPT_VERSION"
  (cd "$PROJECT_ROOT" && ddev start -y) >/dev/null
  SITE_URL="${SITE_URL:-$(resolve_site_url)}"

  info "Auditing the three reviewer decisions and revision histories..."
  (cd "$PROJECT_ROOT" && ddev drush php:script scripts/phase0-step12.php -- audit-reviewed) \
    | tee "$RUN_DIR/audit-reviewed.log"

  (cd "$PROJECT_ROOT" && ddev drush php:script scripts/phase0-step12.php -- json-reviewed) \
    > "$RUN_DIR/revision-evidence.json"

  python3 "$REPORT_HELPER" report \
    --evidence "$RUN_DIR/revision-evidence.json" \
    --site-url "$SITE_URL" \
    --run-dir "$RUN_DIR" \
    --screenshot-dir "$SCREENSHOT_DIR" \
    | tee "$RUN_DIR/report-output-reviewed.txt"

  ln -sfn "$RUN_ID" "$LATEST_LINK"
  ok "Step 12 revision audit passed. Drupal remains in reviewed state for screenshots."
  printf '\nScreenshot directory:\n  %s\n' "$SCREENSHOT_DIR"
  printf 'Checklist:\n  %s/SCREENSHOT-CHECKLIST.md\n' "$RUN_DIR"
  printf 'After screenshots: bash scripts/run-phase0-step12.sh finish confirm\n'
}

screenshot_count() {
  find "$SCREENSHOT_DIR" -maxdepth 1 -type f \
    \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.webp' \) \
    -printf '.' | wc -c | tr -d ' '
}

mode_finish() {
  base_requirements
  set_active_paths
  (cd "$PROJECT_ROOT" && ddev start -y) >/dev/null
  info "Revalidating Step 12 before reset..."
  (cd "$PROJECT_ROOT" && ddev drush php:script scripts/phase0-step12.php -- audit-reviewed) \
    > "$RUN_DIR/final-audit.log" 2>&1 \
    || { cat "$RUN_DIR/final-audit.log" >&2; fail "Final Step 12 audit failed; Drupal was not reset."; }

  local count
  count="$(screenshot_count)"
  if (( count < 3 )); then
    fail "Found $count screenshot(s) in $SCREENSHOT_DIR; save at least three, one revision-history capture per case. Drupal was not reset."
  fi
  ok "Found $count Step 12 screenshot(s)."

  info "Restoring seeded-clean after revision evidence capture..."
  (cd "$PROJECT_ROOT" && bash scripts/run-phase0-step10.sh reset) \
    > "$RUN_DIR/reset-after-step12.log" 2>&1 \
    || { cat "$RUN_DIR/reset-after-step12.log" >&2; fail "Step 12 evidence is valid, but the mandatory reset failed."; }

  rm -f "$ACTIVE_LINK"
  ln -sfn "$RUN_ID" "$LATEST_LINK"
  ok "Step 12 complete: revision evidence retained and Drupal restored to seeded-clean."
  printf '\nEvidence directory:\n  %s\n' "$RUN_DIR"
  printf 'Screenshots:\n  %s\n' "$SCREENSHOT_DIR"
}

mode_reset() {
  base_requirements
  if [[ -L "$ACTIVE_LINK" ]]; then
    set_active_paths
    warn "Aborting active Step 12 run $RUN_ID without requiring screenshot evidence."
    (cd "$PROJECT_ROOT" && bash scripts/run-phase0-step10.sh reset) \
      > "$RUN_DIR/reset-abort.log" 2>&1 \
      || { cat "$RUN_DIR/reset-abort.log" >&2; fail "Step 10 reset failed."; }
    rm -f "$ACTIVE_LINK"
  else
    (cd "$PROJECT_ROOT" && bash scripts/run-phase0-step10.sh reset)
  fi
  ok "Drupal restored to seeded-clean."
}

mode_status() {
  base_requirements
  info "Phase 0 Step 12 runner version: $STEP12_SCRIPT_VERSION"
  if [[ -L "$ACTIVE_LINK" ]]; then
    set_active_paths
    printf 'Active run: %s\n' "$RUN_ID"
    printf 'Evidence: %s\n' "$RUN_DIR"
    printf 'Screenshots: %s\n' "$SCREENSHOT_DIR"
    printf 'Screenshot count: %s\n' "$(screenshot_count)"
  else
    printf 'No active Step 12 run.\n'
  fi
  if [[ -L "$LATEST_LINK" ]]; then
    printf 'Latest audited run: %s\n' "$(basename "$(readlink "$LATEST_LINK")")"
  fi
}

case "$MODE" in
  preflight) mode_preflight ;;
  prepare) mode_prepare ;;
  audit) mode_audit ;;
  finish) mode_finish ;;
  reset) mode_reset ;;
  status) mode_status ;;
esac
