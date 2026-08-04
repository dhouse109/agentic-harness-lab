#!/usr/bin/env bash
set -Eeuo pipefail

STEP17_RUNNER_VERSION="1.0.0"
MODE="${1:-help}"
CONFIRMATION="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DRUPAL_ROOT="$LAB_ROOT/drupal"
TEMPLATE_ROOT="$SCRIPT_DIR/phase0-step17-templates"
LOG_ROOT="$LAB_ROOT/evidence/logs/tools/find-images"
RUNTIME_DIR="$DRUPAL_ROOT/.phase0-step17-runtime"
CREDENTIALS_FILE="$DRUPAL_ROOT/.secrets/phase0-step7-accounts.txt"
LATEST_FILE="$LOG_ROOT/STEP17-LATEST.txt"
LAST_RUN_FILE="$LOG_ROOT/STEP17-LAST-RUN.txt"
TEMP_DIR=""
RESET_REQUIRED=0
RESET_COMPLETED=0

info() { printf '[INFO] %s\n' "$*"; }
ok() { printf '[OK] %s\n' "$*"; }
warn() { printf '[WARNING] %s\n' "$*" >&2; }
fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<EOF
Phase 0 Step 17 guarded discovery package, version $STEP17_RUNNER_VERSION

Usage:
  bash scripts/run-phase0-step17.sh preview
  bash scripts/run-phase0-step17.sh setup
  bash scripts/run-phase0-step17.sh run
  bash scripts/run-phase0-step17.sh audit
  bash scripts/run-phase0-step17.sh finalize confirm
  bash scripts/run-phase0-step17.sh status

Step 17 is model-free. It implements and proves only:
  find_images_needing_review() -> exactly 12 deterministic field usages
EOF
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

cleanup() {
  local exit_code=$?
  set +e
  if [[ "$RESET_REQUIRED" -eq 1 && "$RESET_COMPLETED" -eq 0 && -d "$DRUPAL_ROOT" ]]; then
    warn "Step 17 exited before its normal cleanup; attempting a seeded-clean restore."
    (
      cd "$DRUPAL_ROOT"
      bash scripts/run-phase0-step10.sh reset
      ddev drush cim -y
      ddev drush cr
    ) >/dev/null 2>&1 || warn "Emergency reset failed. Run Step 10 reset and config import manually."
  fi
  [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]] && rm -rf "$TEMP_DIR"
  unset AGENT_PASSWORD EDITOR_PASSWORD STEP17_AGENT_PASSWORD STEP17_EDITOR_PASSWORD
  exit "$exit_code"
}
trap cleanup EXIT INT TERM

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

append_gitignore_block() {
  local marker_begin="# BEGIN PHASE0 STEP17 RUNTIME"
  if grep -Fq "$marker_begin" "$LAB_ROOT/.gitignore"; then
    ok "Step 17 .gitignore block already present."
    return
  fi
  cat >> "$LAB_ROOT/.gitignore" <<'EOF'

# BEGIN PHASE0 STEP17 RUNTIME
/drupal/.phase0-step17-runtime/
/.phase0-step17-backups/
/.phase0-step17-package-backups/
# END PHASE0 STEP17 RUNTIME
EOF
  ok "Added Step 17 runtime and backup ignore rules."
}

relative_template_files() {
  (
    cd "$TEMPLATE_ROOT"
    find . -type f -print | sed 's#^./##' | LC_ALL=C sort
  )
}

preview() {
  [[ -d "$TEMPLATE_ROOT" ]] || fail "Missing Step 17 template directory: $TEMPLATE_ROOT"
  printf 'Step 17 guarded package preview\n\n'
  while IFS= read -r relative; do
    local source="$TEMPLATE_ROOT/$relative" target="$LAB_ROOT/$relative" state
    if [[ ! -e "$target" ]]; then
      state="CREATE"
    elif cmp -s "$source" "$target"; then
      state="KEEP"
    else
      state="CONFLICT"
    fi
    printf '%-9s %s\n' "$state" "$relative"
  done < <(relative_template_files)
  printf '\nAdditional guarded actions during setup:\n'
  printf '  - correct the Step 16 tool-probe record and Ubuntu row\n'
  printf '  - strengthen the Step 16 audit and regenerate contract hashes\n'
  printf '  - enable agentic_harness_tools and grant its permission only to agent_service\n'
  printf '  - export Drupal configuration\n'
  printf '\nNo model call, recommendation creation, Article mutation, commit, or push occurs.\n'
}

install_templates() {
  local conflicts=0
  while IFS= read -r relative; do
    local source="$TEMPLATE_ROOT/$relative" target="$LAB_ROOT/$relative"
    if [[ -e "$target" ]] && ! cmp -s "$source" "$target"; then
      warn "Unexpected existing file differs: $relative"
      conflicts=$((conflicts + 1))
    fi
  done < <(relative_template_files)
  [[ "$conflicts" -eq 0 ]] || fail "Refusing setup because $conflicts target file(s) conflict."

  while IFS= read -r relative; do
    local source="$TEMPLATE_ROOT/$relative" target="$LAB_ROOT/$relative"
    mkdir -p "$(dirname "$target")"
    if [[ -e "$target" ]]; then
      ok "Kept identical file: $relative"
    else
      cp -p "$source" "$target"
      ok "Installed: $relative"
    fi
  done < <(relative_template_files)
}

check_prerequisites() {
  require_command bash
  require_command python3
  require_command ddev
  require_command curl
  require_command awk
  require_command sha256sum
  require_command git
  [[ -d "$DRUPAL_ROOT/.ddev" ]] || fail "Expected Drupal DDEV project at $DRUPAL_ROOT"
  [[ -f "$LAB_ROOT/scripts/run-phase0-step16.sh" ]] || fail "Missing Step 16 runner."
  [[ -f "$DRUPAL_ROOT/scripts/run-phase0-step9.sh" ]] || fail "Missing Step 9 runner."
  [[ -f "$DRUPAL_ROOT/scripts/run-phase0-step10.sh" ]] || fail "Missing Step 10 runner."
  [[ -f "$CREDENTIALS_FILE" ]] || fail "Missing local account credential file: $CREDENTIALS_FILE"
}

setup() {
  check_prerequisites
  info "Verifying finalized Step 16 before applying Step 17..."
  bash "$LAB_ROOT/scripts/run-phase0-step16.sh" audit

  install_templates
  append_gitignore_block

  info "Applying guarded Step 16 evidence-alignment corrections..."
  python3 "$SCRIPT_DIR/step17_contract_repair.py" "$LAB_ROOT"
  python3 - \
    "$SCRIPT_DIR/step16_audit.py" \
    "$SCRIPT_DIR/step17_evidence.py" \
    "$SCRIPT_DIR/step17_audit.py" \
    "$SCRIPT_DIR/step17_finalize.py" \
    "$LAB_ROOT/shared/drupal_client/client.py" <<'PY_VALIDATE'
from pathlib import Path
import sys
for raw in sys.argv[1:]:
    path = Path(raw)
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
PY_VALIDATE

  info "Starting DDEV and validating PHP through the project runtime..."
  (
    cd "$DRUPAL_ROOT"
    ddev start -y
    ddev php -l web/modules/custom/agentic_harness_tools/src/Controller/ToolController.php
    ddev php -l web/modules/custom/agentic_harness_tools/src/Service/ImageReviewFinder.php
    ddev php -l scripts/phase0-step17.php
    ddev drush en agentic_harness_tools -y
    ddev drush php:eval '
      $role = \Drupal\user\Entity\Role::load("agent_service");
      if (!$role) { throw new \RuntimeException("agent_service role not found"); }
      $role->grantPermission("use agentic harness discovery tools");
      $role->save();
      $accounts = \Drupal::entityTypeManager()->getStorage("user")->loadByProperties(["name" => "editor_dana"]);
      $editor = reset($accounts);
      if (!$editor instanceof \Drupal\user\UserInterface) { throw new \RuntimeException("editor_dana not found"); }
      if ($editor->hasPermission("use agentic harness discovery tools")) {
        throw new \RuntimeException("editor_dana unexpectedly has discovery permission");
      }
    '
    ddev drush cr
    ddev drush cex -y
    ddev drush --quiet php:script scripts/phase0-step17.php -- inspect
  )

  info "Re-running the strengthened finalized Step 16 audit..."
  bash "$LAB_ROOT/scripts/run-phase0-step16.sh" audit
  ok "Step 17 setup complete. No model call or content mutation was performed."
}

restore_with_step17_config() {
  (
    cd "$DRUPAL_ROOT"
    bash scripts/run-phase0-step10.sh reset
    ddev drush cim -y
    ddev drush cr
  )
}

write_environment() {
  local output="$1" site_url="$2" run_id="$3"
  python3 - "$output" "$site_url" "$run_id" <<'PY'
import json, platform, sys
from datetime import datetime, timezone
path, site_url, run_id = sys.argv[1:]
value = {
    "run_id": run_id,
    "captured_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "python": platform.python_version(),
    "site_url_origin": site_url.split("://", 1)[0] + "://<local-ddev-host>",
    "openai_api_key_present": False,
    "openai_candidate_model_present": False,
    "crewai_candidate_model_present": False,
    "model_call_performed": False,
    "operation": "find_images_needing_review",
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(value, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY
}

write_authorization() {
  local output="$1" agent="$2" anonymous="$3" editor="$4"
  python3 - "$output" "$agent" "$anonymous" "$editor" <<'PY'
import json, sys
path, agent, anonymous, editor = sys.argv[1:]
with open(path, "w", encoding="utf-8") as handle:
    json.dump({
        "agent": int(agent),
        "anonymous": int(anonymous),
        "editor": int(editor),
        "credentials_retained": False,
        "authorization_headers_retained": False,
    }, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY
}

run_step17() {
  check_prerequisites
  [[ -f "$LAB_ROOT/shared/drupal_client/client.py" ]] || fail "Step 17 is not set up. Run setup first."
  [[ -f "$DRUPAL_ROOT/scripts/phase0-step17.php" ]] || fail "Step 17 Drupal helper is missing."

  # The operation is deliberately model-free even if the parent shell has model variables.
  unset OPENAI_API_KEY OPENAI_CANDIDATE_MODEL CREWAI_CANDIDATE_MODEL

  local run_id="step17-$(date -u +'%Y%m%dT%H%M%SZ')-$$"
  local run_dir="$LOG_ROOT/$run_id"
  local run_rel="evidence/logs/tools/find-images/$run_id"
  mkdir -p "$run_dir" "$RUNTIME_DIR" "$LOG_ROOT"
  TEMP_DIR="$(mktemp -d)"
  chmod 700 "$TEMP_DIR"
  printf '%s\n' "$run_rel" > "$LAST_RUN_FILE"

  info "Verifying Step 16 and restoring the deterministic baseline..."
  bash "$LAB_ROOT/scripts/run-phase0-step16.sh" audit
  RESET_REQUIRED=1
  restore_with_step17_config > "$run_dir/reset-before.log" 2>&1 || {
    cat "$run_dir/reset-before.log" >&2
    fail "Unable to restore seeded-clean and import Step 17 configuration."
  }

  (
    cd "$DRUPAL_ROOT"
    bash scripts/run-phase0-step9.sh audit
    bash scripts/run-phase0-step9.sh manifest > "$run_dir/step9-manifest.json"
    ddev drush --quiet php:script scripts/phase0-step17.php -- inspect > "$run_dir/inspect.json"
    ddev drush --quiet php:script scripts/phase0-step17.php -- snapshot > "$run_dir/mutation-before.json"
  )

  local site_url agent_password editor_password endpoint correlation_id
  site_url="$(resolve_site_url)"
  agent_password="$(latest_secret agent_bot)"
  editor_password="$(latest_secret editor_dana)"
  [[ -n "$agent_password" ]] || fail "No agent_bot password found."
  [[ -n "$editor_password" ]] || fail "No editor_dana password found."
  AGENT_PASSWORD="$agent_password"
  EDITOR_PASSWORD="$editor_password"
  endpoint="/api/agentic-harness/v1/images-needing-review"
  correlation_id="$run_id"

  write_environment "$run_dir/environment.json" "$site_url" "$run_id"
  cat > "$run_dir/request-shape.json" <<EOF
{
  "method": "GET",
  "path": "$endpoint",
  "authentication": "Drupal HTTP Basic via runtime-only agent_bot credential",
  "correlation_id": "$correlation_id",
  "authorization_header_retained": false,
  "password_retained": false,
  "model_call": false
}
EOF

  info "Calling the deterministic route as agent_bot with all model variables removed..."
  set +e
  STEP17_AGENT_PASSWORD="$AGENT_PASSWORD" \
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" find-images \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env STEP17_AGENT_PASSWORD \
      --correlation-id "$correlation_id" \
      --insecure-local \
      > "$run_dir/response.json" 2> "$run_dir/agent-client.log"
  local agent_exit=$?
  set -e
  [[ "$agent_exit" -eq 0 ]] || {
    cat "$run_dir/agent-client.log" >&2
    fail "agent_bot discovery call failed."
  }
  local agent_status=200

  info "Running anonymous and editor_dana negative authorization checks..."
  local anonymous_status editor_status editor_curlrc="$TEMP_DIR/editor.curlrc"
  anonymous_status="$(curl --silent --show-error --insecure --output /dev/null --write-out '%{http_code}' \
    --header 'Accept: application/json' "$site_url$endpoint")"
  umask 077
  printf 'user = "%s:%s"\n' "editor_dana" "$EDITOR_PASSWORD" > "$editor_curlrc"
  chmod 600 "$editor_curlrc"
  editor_status="$(curl --silent --show-error --insecure --output /dev/null --write-out '%{http_code}' \
    --config "$editor_curlrc" --header 'Accept: application/json' "$site_url$endpoint")"
  write_authorization "$run_dir/authorization.json" "$agent_status" "$anonymous_status" "$editor_status"

  info "Repeating the same model-free call for deterministic target hashing..."
  STEP17_AGENT_PASSWORD="$AGENT_PASSWORD" \
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" find-images \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env STEP17_AGENT_PASSWORD \
      --correlation-id "$run_id-repeat" \
      --insecure-local \
      > "$run_dir/repeat-response.json" 2> "$run_dir/repeat-client.log" || {
        cat "$run_dir/repeat-client.log" >&2
        fail "Repeat discovery call failed."
      }

  cp "$run_dir/response.json" "$RUNTIME_DIR/agent-response.json"
  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:script scripts/phase0-step17.php -- \
      validate-identities /var/www/html/.phase0-step17-runtime/agent-response.json \
      > "$run_dir/identity-validation.json"
    ddev drush --quiet php:script scripts/phase0-step17.php -- snapshot \
      > "$run_dir/mutation-after.json"
  )

  info "Evaluating the thirteen Step 17 controls..."
  set +e
  python3 "$SCRIPT_DIR/step17_evidence.py" evaluate \
    --root "$LAB_ROOT" --run-dir "$run_dir" --run-id "$run_id"
  local evaluate_exit=$?
  set -e

  info "Restoring seeded-clean after the read-only test run..."
  restore_with_step17_config > "$run_dir/reset-after.log" 2>&1 || {
    cat "$run_dir/reset-after.log" >&2
    fail "Step 17 evidence was retained, but final seeded-clean restore failed."
  }
  RESET_COMPLETED=1

  if [[ "$evaluate_exit" -ne 0 ]]; then
    fail "Step 17 controls did not all pass. Review $run_rel/summary.md"
  fi

  printf '%s\n' "$run_rel" > "$LATEST_FILE"
  ok "Step 17 passed 13/13. Evidence: $run_rel"
}

resolve_latest_run() {
  [[ -f "$LATEST_FILE" ]] || fail "No passing Step 17 run is recorded."
  local relative
  relative="$(tr -d '\r\n' < "$LATEST_FILE")"
  [[ "$relative" =~ ^evidence/logs/tools/find-images/step17-[A-Za-z0-9._-]+$ ]] \
    || fail "STEP17-LATEST contains an unexpected path: $relative"
  [[ -d "$LAB_ROOT/$relative" ]] || fail "STEP17-LATEST points to a missing run: $relative"
  printf '%s' "$LAB_ROOT/$relative"
}

audit() {
  check_prerequisites
  bash "$LAB_ROOT/scripts/run-phase0-step16.sh" audit
  python3 "$SCRIPT_DIR/step17_audit.py" "$LAB_ROOT"
}

finalize() {
  [[ "$CONFIRMATION" == "confirm" ]] || fail "Finalization requires: finalize confirm"
  audit
  local run_dir
  run_dir="$(resolve_latest_run)"
  python3 "$SCRIPT_DIR/step17_finalize.py" "$LAB_ROOT" "$run_dir"
  audit
  ok "Step 17 finalized. Phase 0 now exits into Gate 0.5."
}

status() {
  printf 'Step 17 runner version: %s\n' "$STEP17_RUNNER_VERSION"
  if [[ -f "$LAST_RUN_FILE" ]]; then
    printf 'Last attempted run: %s\n' "$(cat "$LAST_RUN_FILE")"
  else
    printf 'Last attempted run: none\n'
  fi
  if [[ -f "$LATEST_FILE" ]]; then
    printf 'Latest passing run: %s\n' "$(cat "$LATEST_FILE")"
  else
    printf 'Latest passing run: none\n'
  fi
  set +e
  audit
  local code=$?
  set -e
  return "$code"
}

case "$MODE" in
  preview) preview ;;
  setup) setup ;;
  run) run_step17 ;;
  audit) audit ;;
  finalize) finalize ;;
  status) status ;;
  help|-h|--help) usage ;;
  *) usage >&2; exit 2 ;;
esac
