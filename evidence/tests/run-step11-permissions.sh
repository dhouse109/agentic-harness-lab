#!/usr/bin/env bash
set -Eeuo pipefail

STEP11_SCRIPT_VERSION="1.0.2"
MODE="${1:-run}"

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_ROOT="$(cd "$TEST_DIR/../.." && pwd)"
PROJECT_ROOT="$LAB_ROOT/drupal"
HELPER="$TEST_DIR/step11-evidence.py"
LOG_ROOT="$LAB_ROOT/evidence/logs/permissions"
CREDENTIALS_FILE="$PROJECT_ROOT/.secrets/phase0-step7-accounts.txt"
RUN_ID="step11-$(date -u +'%Y%m%dT%H%M%SZ')-$$"
RUN_DIR="$LOG_ROOT/$RUN_ID"
TEMP_DIR=""
SITE_URL=""
AGENT_PASSWORD=""
EDITOR_PASSWORD=""
AGENT_CURL_CONFIG=""
EDITOR_CURL_CONFIG=""
RESET_REQUIRED=0
RESET_COMPLETED=0
TEST_FAILURES=0

info() { printf '[INFO] %s\n' "$*"; }
ok() { printf '[OK] %s\n' "$*"; }
warn() { printf '[WARNING] %s\n' "$*" >&2; }
fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<EOF
Phase 0 Step 11 permission tests, version $STEP11_SCRIPT_VERSION

Usage:
  bash evidence/tests/run-step11-permissions.sh run
  bash evidence/tests/run-step11-permissions.sh preflight

Convenience wrapper from drupal/:
  bash scripts/run-phase0-step11.sh run
EOF
}

case "$MODE" in
  run|preflight) ;;
  help|-h|--help) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac

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
  value="$(cd "$PROJECT_ROOT" && ddev exec printenv DDEV_PRIMARY_URL 2>/dev/null \
    | tr -d '\r' | grep -Eo 'https?://[^[:space:]]+' | tail -n 1 || true)"
  [[ -n "$value" ]] || fail "Unable to resolve DDEV_PRIMARY_URL. Run 'ddev describe' and set SITE_URL manually."
  printf '%s' "${value%/}"
}

write_curl_config() {
  local path="$1" username="$2" password="$3"
  umask 077
  printf 'user = "%s:%s"\n' "$username" "$password" > "$path"
  chmod 600 "$path"
}

cleanup() {
  local exit_code=$?
  set +e
  if [[ "$RESET_REQUIRED" -eq 1 && "$RESET_COMPLETED" -eq 0 && -d "$PROJECT_ROOT" ]]; then
    warn "The suite exited before its normal reset; attempting an emergency seeded-clean restore."
    (cd "$PROJECT_ROOT" && bash scripts/run-phase0-step10.sh reset) \
      > "${RUN_DIR:-/tmp}/emergency-reset.log" 2>&1 || warn "Emergency reset failed. Run Step 10 reset manually before continuing."
  fi
  [[ -n "$TEMP_DIR" ]] && rm -rf "$TEMP_DIR"
  unset AGENT_PASSWORD EDITOR_PASSWORD
  exit "$exit_code"
}
trap cleanup EXIT INT TERM

preflight() {
  require_command ddev
  require_command curl
  require_command python3
  require_command awk
  require_command grep

  [[ -d "$PROJECT_ROOT" ]] || fail "Expected Drupal project at: $PROJECT_ROOT"
  [[ -f "$PROJECT_ROOT/.ddev/config.yaml" ]] || fail "Missing Drupal DDEV config."
  [[ -x "$HELPER" || -f "$HELPER" ]] || fail "Missing Step 11 helper: $HELPER"
  [[ -f "$PROJECT_ROOT/scripts/run-phase0-step7.sh" ]] || fail "Missing Step 7 runner."
  [[ -f "$PROJECT_ROOT/scripts/run-phase0-step8.sh" ]] || fail "Missing Step 8 runner."
  [[ -f "$PROJECT_ROOT/scripts/run-phase0-step9.sh" ]] || fail "Missing Step 9 runner."
  [[ -f "$PROJECT_ROOT/scripts/run-phase0-step10.sh" ]] || fail "Missing Step 10 runner."
  [[ -f "$CREDENTIALS_FILE" ]] || fail "Missing credentials file: $CREDENTIALS_FILE"

  mkdir -p "$RUN_DIR"
  TEMP_DIR="$(mktemp -d)"
  chmod 700 "$TEMP_DIR"

  info "Phase 0 Step 11 runner version: $STEP11_SCRIPT_VERSION"
  info "Starting DDEV and running structural audits..."
  (
    cd "$PROJECT_ROOT"
    ddev start -y
    bash scripts/run-phase0-step7.sh audit
    bash scripts/run-phase0-step8.sh audit
    bash scripts/run-phase0-step10.sh audit
  ) > "$RUN_DIR/preflight.log" 2>&1 || {
    cat "$RUN_DIR/preflight.log" >&2
    fail "A prerequisite audit failed. Step 11 did not send any HTTP mutation requests."
  }

  AGENT_PASSWORD="$(latest_secret agent_bot)"
  EDITOR_PASSWORD="$(latest_secret editor_dana)"
  [[ -n "$AGENT_PASSWORD" ]] || fail "No agent_bot password found in $CREDENTIALS_FILE"
  [[ -n "$EDITOR_PASSWORD" ]] || fail "No editor_dana password found in $CREDENTIALS_FILE"

  AGENT_CURL_CONFIG="$TEMP_DIR/agent.curlrc"
  EDITOR_CURL_CONFIG="$TEMP_DIR/editor.curlrc"
  write_curl_config "$AGENT_CURL_CONFIG" "agent_bot" "$AGENT_PASSWORD"
  write_curl_config "$EDITOR_CURL_CONFIG" "editor_dana" "$EDITOR_PASSWORD"

  SITE_URL="${SITE_URL:-$(resolve_site_url)}"
  info "Resolved local site URL: $SITE_URL"

  local health_status
  health_status="$(curl --silent --show-error --insecure --output /dev/null --write-out '%{http_code}' "$SITE_URL/")" \
    || fail "Unable to reach $SITE_URL"
  [[ "$health_status" =~ ^(200|301|302|403)$ ]] || fail "Unexpected site health status: $health_status"

  (cd "$PROJECT_ROOT" && bash scripts/run-phase0-step9.sh manifest) > "$TEMP_DIR/manifest.json"
  python3 "$HELPER" shell-targets --manifest "$TEMP_DIR/manifest.json" > "$TEMP_DIR/targets.env"
  # shellcheck disable=SC1090
  source "$TEMP_DIR/targets.env"

  ok "Preflight passed: audits, credentials, site URL, and 12-target manifest are available."
}

record_blocked() {
  local test_id="$1" description="$2" account="$3" method="$4" path="$5" expected="$6" reason="$7"
  python3 "$HELPER" record-blocked \
    --test-id "$test_id" --description "$description" \
    --timestamp "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    --account "$account" --method "$method" --path "$path" \
    --expected "$expected" --reason "$reason" \
    --output "$RUN_DIR/test-$test_id.json" >/dev/null || true
  TEST_FAILURES=$((TEST_FAILURES + 1))
  warn "$test_id FAIL (blocked): $reason"
}

run_http_test() {
  local test_id="$1" description="$2" account="$3" auth_mode="$4"
  local method="$5" path="$6" expected="$7" validator="$8" request_file="${9:-}"
  local body="$TEMP_DIR/$test_id-body" headers="$TEMP_DIR/$test_id-headers"
  local actual="000" curl_exit=0 validator_passed=true
  local -a curl_args=(
    --silent --show-error --insecure --globoff
    --connect-timeout 10 --max-time 60
    --request "$method"
    --header 'Accept: application/vnd.api+json'
    --dump-header "$headers"
    --output "$body"
    --write-out '%{http_code}'
  )

  case "$auth_mode" in
    agent) curl_args+=(--config "$AGENT_CURL_CONFIG") ;;
    editor) curl_args+=(--config "$EDITOR_CURL_CONFIG") ;;
    anonymous) ;;
    *) fail "Unknown auth mode: $auth_mode" ;;
  esac

  if [[ -n "$request_file" ]]; then
    curl_args+=(--header 'Content-Type: application/vnd.api+json' --data-binary "@$request_file")
  fi

  set +e
  actual="$(curl "${curl_args[@]}" "$SITE_URL$path")"
  curl_exit=$?
  set -e

  if [[ "$curl_exit" -eq 0 && "$validator" != "none" ]]; then
    local -a validation=(python3 "$HELPER" validate --kind "$validator" --body "$body")
    if [[ "$validator" == "article_context" ]]; then
      validation+=(--node-uuid "$TARGET1_NODE_UUID" --file-uuid "$TARGET1_FILE_UUID" --delta "$TARGET1_DELTA")
    fi
    if ! "${validation[@]}" > "$TEMP_DIR/$test_id-validator.log" 2>&1; then
      validator_passed=false
    fi
  fi

  local -a record_args=(
    python3 "$HELPER" record
    --test-id "$test_id" --description "$description"
    --timestamp "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    --account "$account" --method "$method" --path "$path"
    --expected "$expected" --actual "$actual" --curl-exit "$curl_exit"
    --validator-passed "$validator_passed" --headers "$headers" --body "$body"
    --site-url "$SITE_URL" --output "$RUN_DIR/test-$test_id.json"
  )
  if [[ -n "$request_file" ]]; then
    record_args+=(--request "$request_file")
  fi

  set +e
  "${record_args[@]}" >/dev/null
  local record_exit=$?
  set -e

  if [[ "$record_exit" -eq 0 ]]; then
    ok "$test_id PASS — $description (HTTP $actual)"
  else
    TEST_FAILURES=$((TEST_FAILURES + 1))
    warn "$test_id FAIL — $description (expected $expected, received $actual)"
    if [[ -s "$TEMP_DIR/$test_id-validator.log" ]]; then
      sed 's/^/  validator: /' "$TEMP_DIR/$test_id-validator.log" >&2
    fi
  fi
}

run_suite() {
  local article_path="/jsonapi/node/article/$TARGET1_NODE_UUID?include=field_image"
  local suggestion_collection="/jsonapi/node/alt_text_suggestion"
  local context_ready=0 suggestion_uuid=""

  # Read-only checks.
  run_http_test P01 "agent_bot reads the allowed Article collection" agent_bot agent \
    GET '/jsonapi/node/article?page[limit]=1' '200' article_collection

  run_http_test P02 "agent_bot reads page and image context for an allowed target usage" agent_bot agent \
    GET "$article_path" '200' article_context

  if [[ -f "$TEMP_DIR/P02-body" ]] && python3 "$HELPER" validate \
      --kind article_context --body "$TEMP_DIR/P02-body" \
      --node-uuid "$TARGET1_NODE_UUID" --file-uuid "$TARGET1_FILE_UUID" --delta "$TARGET1_DELTA" \
      >/dev/null 2>&1; then
    python3 "$HELPER" build-base-payloads \
      --manifest "$TEMP_DIR/manifest.json" --context "$TEMP_DIR/P02-body" \
      --output-dir "$TEMP_DIR/payloads" --run-id "$RUN_ID"
    context_ready=1
  fi

  # From this point forward, a surprising permission success can mutate Drupal.
  RESET_REQUIRED=1

  if [[ "$context_ready" -eq 1 ]]; then
    run_http_test P03 "agent_bot creates a pending alt_text_suggestion" agent_bot agent \
      POST "$suggestion_collection" '201' suggestion_created "$TEMP_DIR/payloads/suggestion-create.json"
  else
    record_blocked P03 "agent_bot creates a pending alt_text_suggestion" agent_bot POST \
      "$suggestion_collection" '201' "P02 context validation failed; a safe create payload could not be built."
  fi

  if [[ -f "$TEMP_DIR/P03-body" ]]; then
    set +e
    suggestion_uuid="$(python3 "$HELPER" build-suggestion-patches \
      --response "$TEMP_DIR/P03-body" --output-dir "$TEMP_DIR/payloads" 2>/dev/null)"
    set -e
  fi

  if [[ "$context_ready" -eq 1 ]]; then
    run_http_test N01 "agent_bot cannot change Article image alt text" agent_bot agent \
      PATCH "/jsonapi/node/article/$TARGET1_NODE_UUID" '403' none "$TEMP_DIR/payloads/article-alt-patch.json"
    run_http_test N02 "agent_bot cannot replace the target image-field item" agent_bot agent \
      PATCH "/jsonapi/node/article/$TARGET1_NODE_UUID" '403' none "$TEMP_DIR/payloads/article-item-patch.json"
  else
    record_blocked N01 "agent_bot cannot change Article image alt text" agent_bot PATCH \
      "/jsonapi/node/article/$TARGET1_NODE_UUID" '403' "P02 context validation failed; no valid PATCH payload was available."
    record_blocked N02 "agent_bot cannot replace the target image-field item" agent_bot PATCH \
      "/jsonapi/node/article/$TARGET1_NODE_UUID" '403' "P02 context validation failed; no valid PATCH payload was available."
  fi

  if [[ -n "$suggestion_uuid" ]]; then
    run_http_test N03 "agent_bot cannot approve its own suggestion" agent_bot agent \
      PATCH "/jsonapi/node/alt_text_suggestion/$suggestion_uuid" '403' none "$TEMP_DIR/payloads/suggestion-approve-patch.json"
    run_http_test N04 "agent_bot cannot reject its own suggestion" agent_bot agent \
      PATCH "/jsonapi/node/alt_text_suggestion/$suggestion_uuid" '403' none "$TEMP_DIR/payloads/suggestion-reject-patch.json"
    run_http_test N05 "agent_bot cannot edit its own proposed alt text" agent_bot agent \
      PATCH "/jsonapi/node/alt_text_suggestion/$suggestion_uuid" '403' none "$TEMP_DIR/payloads/suggestion-edit-patch.json"
  else
    local reason="P03 did not return a valid created-suggestion UUID."
    record_blocked N03 "agent_bot cannot approve its own suggestion" agent_bot PATCH \
      '/jsonapi/node/alt_text_suggestion/<created-uuid>' '403' "$reason"
    record_blocked N04 "agent_bot cannot reject its own suggestion" agent_bot PATCH \
      '/jsonapi/node/alt_text_suggestion/<created-uuid>' '403' "$reason"
    record_blocked N05 "agent_bot cannot edit its own proposed alt text" agent_bot PATCH \
      '/jsonapi/node/alt_text_suggestion/<created-uuid>' '403' "$reason"
  fi

  if [[ "$context_ready" -eq 1 ]]; then
    run_http_test N06 "anonymous cannot create an alt_text_suggestion" anonymous anonymous \
      POST "$suggestion_collection" '401,403' none "$TEMP_DIR/payloads/suggestion-create.json"
  else
    record_blocked N06 "anonymous cannot create an alt_text_suggestion" anonymous POST \
      "$suggestion_collection" '401,403' "P02 context validation failed; no safe create payload was available."
  fi

  run_http_test N07 "anonymous cannot open the administrative review queue" anonymous anonymous \
    GET '/admin/review-queue' '403' none
  run_http_test N08 "editor_dana cannot administer AI-provider configuration" editor_dana editor \
    GET '/admin/config/ai/providers' '403' none
  run_http_test N09 "editor_dana cannot administer module configuration" editor_dana editor \
    GET '/admin/modules' '403' none
}

preflight
if [[ "$MODE" == "preflight" ]]; then
  ok "Preflight-only mode complete. No mutation requests were sent."
  RESET_REQUIRED=0
  exit 0
fi

run_suite

set +e
python3 "$HELPER" report --run-dir "$RUN_DIR" --run-id "$RUN_ID" \
  --timestamp "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
REPORT_EXIT=$?
set -e

info "Restoring seeded-clean after permission testing..."
if (cd "$PROJECT_ROOT" && bash scripts/run-phase0-step10.sh reset) > "$RUN_DIR/reset-after-tests.log" 2>&1; then
  RESET_COMPLETED=1
  ok "Seeded-clean restored after Step 11."
else
  cat "$RUN_DIR/reset-after-tests.log" >&2
  fail "Step 11 tests finished, but the mandatory Step 10 reset failed."
fi

ln -sfn "$RUN_ID" "$LOG_ROOT/latest"

printf '\nEvidence directory:\n  %s\n' "$RUN_DIR"
printf 'Summary:\n  %s\n' "$RUN_DIR/summary.json"
printf 'Organ 2 HTML evidence:\n  %s\n' "$RUN_DIR/403-organ2-summary.html"
printf 'Reset log:\n  %s\n\n' "$RUN_DIR/reset-after-tests.log"

if [[ "$REPORT_EXIT" -ne 0 || "$TEST_FAILURES" -ne 0 ]]; then
  fail "Step 11 did not pass all permission tests. Drupal was reset; inspect summary.json and the individual test files."
fi

ok "Step 11 passed: all positive operations succeeded, all forbidden operations were denied, sanitized evidence was saved, and Drupal was reset."
