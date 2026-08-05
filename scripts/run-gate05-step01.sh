#!/usr/bin/env bash
set -Eeuo pipefail

RUNNER_VERSION="1.0.2"
MODE="${1:-help}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DRUPAL_ROOT="$LAB_ROOT/drupal"
LOG_ROOT="$LAB_ROOT/evidence/gates/gate-0.5/baseline"
LATEST_FILE="$LOG_ROOT/GATE05-STEP01-LATEST.txt"
LAST_RUN_FILE="$LOG_ROOT/GATE05-STEP01-LAST-RUN.txt"
CREDENTIALS_FILE="$DRUPAL_ROOT/.secrets/phase0-step7-accounts.txt"
EXPECTED_BASE_COMMIT="177e6a7baaaebded35a11c3140026aadcb71c503"
EXPECTED_REPO_FRAGMENT="dhouse109/agentic-harness-lab"
RESET_REQUIRED=0
RESET_COMPLETED=0

info() { printf '[INFO] %s\n' "$*"; }
ok() { printf '[OK] %s\n' "$*"; }
pass() { printf '[PASS] %s\n' "$*"; }
warn() { printf '[WARNING] %s\n' "$*" >&2; }
fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<EOF
Gate 0.5 Step 01 baseline runner, version $RUNNER_VERSION

Usage:
  bash scripts/run-gate05-step01.sh preview
  bash scripts/run-gate05-step01.sh run
  bash scripts/run-gate05-step01.sh audit
  bash scripts/run-gate05-step01.sh status
EOF
}

cleanup() {
  local exit_code=$?
  set +e
  if [[ "$RESET_REQUIRED" -eq 1 && "$RESET_COMPLETED" -eq 0 && -d "$DRUPAL_ROOT" ]]; then
    warn "Step 01 exited early; attempting a seeded-clean restore."
    (
      cd "$DRUPAL_ROOT"
      bash scripts/run-phase0-step10.sh reset
      ddev drush cim -y
      ddev drush cr
    ) >/dev/null 2>&1 || warn "Emergency reset failed. Restore seeded-clean manually."
  fi
  unset GATE05_AGENT_PASSWORD
  exit "$exit_code"
}
trap cleanup EXIT INT TERM

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

latest_secret() {
  local key="$1"
  awk -v key="$key" '
    index($0, key "=") == 1 { value = substr($0, length(key) + 2) }
    END { if (value != "") print value }
  ' "$CREDENTIALS_FILE"
}

resolve_site_url() {
  local value
  value="$(cd "$DRUPAL_ROOT" && ddev exec printenv DDEV_PRIMARY_URL 2>/dev/null \
    | tr -d '\r' | grep -Eo 'https?://[^[:space:]]+' | tail -n 1 || true)"
  [[ -n "$value" ]] || fail "Unable to resolve DDEV_PRIMARY_URL."
  printf '%s' "${value%/}"
}

check_repo_identity() {
  local top origin
  top="$(git -C "$LAB_ROOT" rev-parse --show-toplevel 2>/dev/null || true)"
  [[ "$top" == "$LAB_ROOT" ]] || fail "Runner is not installed in the repository root."
  origin="$(git -C "$LAB_ROOT" remote get-url origin 2>/dev/null || true)"
  [[ "$origin" == *"$EXPECTED_REPO_FRAGMENT"* ]] || fail "Unexpected Git origin: ${origin:-<missing>}"
  git -C "$LAB_ROOT" cat-file -e "${EXPECTED_BASE_COMMIT}^{commit}" 2>/dev/null || \
    fail "Required base commit is not present locally: $EXPECTED_BASE_COMMIT"
  git -C "$LAB_ROOT" merge-base --is-ancestor "$EXPECTED_BASE_COMMIT" HEAD || \
    fail "HEAD does not contain the completed Phase 0 base commit."
}

check_tracked_tree_clean() {
  git -C "$LAB_ROOT" diff --quiet || fail "Tracked working-tree changes exist."
  git -C "$LAB_ROOT" diff --cached --quiet || fail "Staged changes exist."
}

check_prerequisites() {
  require_command bash
  require_command python3
  require_command git
  require_command ddev
  require_command curl
  check_repo_identity
  check_tracked_tree_clean
  [[ -d "$DRUPAL_ROOT/.ddev" ]] || fail "Expected DDEV project at $DRUPAL_ROOT"
  [[ -f "$LAB_ROOT/scripts/step17_audit.py" ]] || fail "Missing dedicated Step 17 auditor."
  [[ -f "$DRUPAL_ROOT/scripts/run-phase0-step9.sh" ]] || fail "Missing Phase 0 Step 9 runner."
  [[ -f "$DRUPAL_ROOT/scripts/run-phase0-step10.sh" ]] || fail "Missing Phase 0 Step 10 runner."
  [[ -f "$LAB_ROOT/shared/drupal_client/client.py" ]] || fail "Missing shared Drupal client."
  [[ -f "$LAB_ROOT/scripts/gate05_step01_evidence.py" ]] || fail "Missing Step 01 evidence helper."
  [[ -f "$CREDENTIALS_FILE" ]] || fail "Missing local account credential file."
}

preview() {
  check_repo_identity
  cat <<EOF
Gate 0.5 Step 01 preview, runner v$RUNNER_VERSION

Actions:
  - run the dedicated finalized-state Step 17 auditor directly
  - restore seeded-clean
  - directly call find_images_needing_review() as agent_bot
  - record 12 current targets and freeze sequence 1
  - retain Git, contract, model, fixture, and target hashes

The obsolete Step 15/16 README compatibility assertions are not invoked.
No model call, recommendation creation, Article mutation, commit, or push occurs.
EOF
}

resolve_retained_step17() {
  local pointer_file="$LAB_ROOT/evidence/logs/tools/find-images/STEP17-LATEST.txt"
  [[ -s "$pointer_file" ]] || fail "Missing finalized Step 17 latest pointer."
  local relative
  relative="$(tr -d '\r\n' < "$pointer_file")"
  [[ "$relative" =~ ^evidence/logs/tools/find-images/step17-[A-Za-z0-9._-]+$ ]] || \
    fail "Unexpected Step 17 pointer: $relative"
  [[ -d "$LAB_ROOT/$relative" ]] || fail "Retained Step 17 evidence directory is missing: $relative"
  printf '%s' "$relative"
}

capture_drupal_state() {
  local output="$1"
  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:eval '
      $storage = \Drupal::entityTypeManager()->getStorage("node");
      $articles = (int) $storage->getQuery()->accessCheck(FALSE)->condition("type", "article")->count()->execute();
      $suggestions = (int) $storage->getQuery()->accessCheck(FALSE)->condition("type", "alt_text_suggestion")->count()->execute();
      $module_enabled = \Drupal::moduleHandler()->moduleExists("agentic_harness_tools");
      $role = \Drupal\user\Entity\Role::load("agent_service");
      $agent_permission = $role ? $role->hasPermission("use agentic harness discovery tools") : FALSE;
      $accounts = \Drupal::entityTypeManager()->getStorage("user")->loadByProperties(["name" => "editor_dana"]);
      $editor = reset($accounts);
      $editor_permission = $editor instanceof \Drupal\user\UserInterface
        ? $editor->hasPermission("use agentic harness discovery tools")
        : NULL;
      print json_encode([
        "article_count" => $articles,
        "suggestion_count" => $suggestions,
        "agentic_harness_tools_enabled" => $module_enabled,
        "agent_service_has_discovery_permission" => $agent_permission,
        "editor_has_discovery_permission" => $editor_permission,
        "model_call_performed" => FALSE,
        "recommendation_created" => FALSE,
        "source_article_mutated" => FALSE
      ], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
    '
  ) > "$output"
}

extract_targets() {
  local response="$1" output="$2"
  python3 - "$response" "$output" <<'PY'
import json, sys
response = json.load(open(sys.argv[1], encoding="utf-8"))
if not isinstance(response, dict) or response.get("ok") is not True:
    raise SystemExit("Discovery response is not a successful tool envelope.")
data = response.get("data")
targets = data.get("targets") if isinstance(data, dict) else None
if not isinstance(targets, list):
    raise SystemExit("Discovery response lacks data.targets.")
json.dump(targets, open(sys.argv[2], "w", encoding="utf-8"), indent=2, sort_keys=True)
open(sys.argv[2], "a", encoding="utf-8").write("\n")
PY
}

run_finalized_step17_audit() {
  python3 "$LAB_ROOT/scripts/step17_audit.py" "$LAB_ROOT"
}

run_baseline() {
  check_prerequisites
  local run_id="gate05-step01-$(date -u +'%Y%m%dT%H%M%SZ')-$$"
  local run_dir="$LOG_ROOT/$run_id"
  local run_rel="evidence/gates/gate-0.5/baseline/$run_id"
  mkdir -p "$run_dir"
  printf '%s\n' "$run_rel" > "$LAST_RUN_FILE"

  info "Auditing the finalized Phase 0 Step 17 state directly..."
  run_finalized_step17_audit \
    > >(tee "$run_dir/phase0-step17-finalized-audit.log") 2>&1

  local retained_step17_rel
  retained_step17_rel="$(resolve_retained_step17)"
  printf '%s\n' "$retained_step17_rel" > "$run_dir/retained-step17-evidence.txt"

  info "Restoring the deterministic seeded-clean fixture..."
  RESET_REQUIRED=1
  (
    cd "$DRUPAL_ROOT"
    bash scripts/run-phase0-step10.sh reset
    ddev drush cim -y
    ddev drush cr
  ) > >(tee "$run_dir/reset.log") 2>&1
  RESET_COMPLETED=1

  info "Auditing the Phase 0 fixture..."
  (
    cd "$DRUPAL_ROOT"
    bash scripts/run-phase0-step9.sh audit
  ) > >(tee "$run_dir/phase0-step9-audit.log") 2>&1

  capture_drupal_state "$run_dir/drupal-state.json"

  local site_url agent_password correlation_id
  site_url="$(resolve_site_url)"
  agent_password="$(latest_secret agent_bot)"
  [[ -n "$agent_password" ]] || fail "No agent_bot password found."
  correlation_id="$run_id-direct-discovery"

  cat > "$run_dir/discovery-request.json" <<EOF
{
  "method": "GET",
  "path": "/api/agentic-harness/v1/images-needing-review",
  "authentication": "Drupal HTTP Basic with runtime-only agent_bot credential",
  "correlation_id": "$correlation_id",
  "model_call": false,
  "password_retained": false,
  "authorization_header_retained": false
}
EOF

  info "Calling the current model-free discovery route directly..."
  GATE05_AGENT_PASSWORD="$agent_password" \
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" find-images \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env GATE05_AGENT_PASSWORD \
      --correlation-id "$correlation_id" \
      --insecure-local \
      > "$run_dir/discovery-response.json" 2> "$run_dir/discovery-client.log"

  extract_targets "$run_dir/discovery-response.json" "$run_dir/targets.json"

  info "Building Gate 0.5 baseline evidence..."
  python3 "$LAB_ROOT/scripts/gate05_step01_evidence.py" build \
    --repo "$LAB_ROOT" \
    --run-dir "$run_dir" \
    --targets-file "$run_dir/targets.json" \
    --retained-step17-rel "$retained_step17_rel"

  printf '%s\n' "$run_rel" > "$LATEST_FILE"

  info "Auditing retained Gate 0.5 baseline evidence..."
  python3 "$LAB_ROOT/scripts/gate05_step01_evidence.py" audit \
    --repo "$LAB_ROOT" \
    --run-dir "$run_dir"

  pass "Gate 0.5 Step 01 baseline established."
  pass "Evidence: $run_rel"
  printf '\nDo not commit yet. Paste the complete terminal output into the program-lead chat.\n'
}

resolve_latest_gate_run() {
  [[ -s "$LATEST_FILE" ]] || fail "No passing Gate 0.5 Step 01 baseline is recorded."
  local relative
  relative="$(tr -d '\r\n' < "$LATEST_FILE")"
  [[ "$relative" =~ ^evidence/gates/gate-0\.5/baseline/gate05-step01-[A-Za-z0-9._-]+$ ]] || \
    fail "Unexpected latest baseline pointer: $relative"
  [[ -d "$LAB_ROOT/$relative" ]] || fail "Latest baseline directory is missing: $relative"
  printf '%s' "$relative"
}

audit_latest() {
  check_prerequisites
  local relative
  relative="$(resolve_latest_gate_run)"

  info "Auditing the finalized Phase 0 Step 17 state directly..."
  run_finalized_step17_audit

  info "Auditing Gate 0.5 Step 01 evidence..."
  python3 "$LAB_ROOT/scripts/gate05_step01_evidence.py" audit \
    --repo "$LAB_ROOT" \
    --run-dir "$LAB_ROOT/$relative"

  pass "Gate 0.5 Step 01 audit passed."
  pass "Evidence: $relative"
}

status_latest() {
  local relative
  relative="$(resolve_latest_gate_run)"
  cat "$LAB_ROOT/$relative/summary.md"
}

case "$MODE" in
  preview) preview ;;
  run) run_baseline ;;
  audit) audit_latest ;;
  status) status_latest ;;
  help|-h|--help) usage ;;
  *) usage; fail "Unknown mode: $MODE" ;;
esac
