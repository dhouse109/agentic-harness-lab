#!/usr/bin/env bash
set -Eeuo pipefail

RUNNER_VERSION="1.0.1"
MODE="${1:-help}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DRUPAL_ROOT="$LAB_ROOT/drupal"
LOG_ROOT="$LAB_ROOT/evidence/gates/gate-0.5/image-context"
LATEST_FILE="$LOG_ROOT/GATE05-STEP02-LATEST.txt"
LAST_RUN_FILE="$LOG_ROOT/GATE05-STEP02-LAST-RUN.txt"
STEP01_LATEST="$LAB_ROOT/evidence/gates/gate-0.5/baseline/GATE05-STEP01-LATEST.txt"
CREDENTIALS_FILE="$DRUPAL_ROOT/.secrets/phase0-step7-accounts.txt"
TEMP_DIR=""
RESET_REQUIRED=0
RESET_COMPLETED=0

info() { printf '[INFO] %s\n' "$*"; }
ok() { printf '[OK] %s\n' "$*"; }
pass() { printf '[PASS] %s\n' "$*"; }
warn() { printf '[WARNING] %s\n' "$*" >&2; }
fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<EOF
Gate 0.5 Step 02 image-context runner, version $RUNNER_VERSION

Usage:
  bash scripts/run-gate05-step02.sh preview
  bash scripts/run-gate05-step02.sh setup
  bash scripts/run-gate05-step02.sh run
  bash scripts/run-gate05-step02.sh audit
  bash scripts/run-gate05-step02.sh status
EOF
}

cleanup() {
  local exit_code=$?
  set +e
  if [[ "$RESET_REQUIRED" -eq 1 && "$RESET_COMPLETED" -eq 0 ]]; then
    warn "Step 02 exited early; attempting a seeded-clean restore."
    (
      cd "$DRUPAL_ROOT"
      bash scripts/run-phase0-step10.sh reset
      ddev drush cim -y
      ddev drush cr
    ) >/dev/null 2>&1 || warn "Emergency reset failed. Restore seeded-clean manually."
  fi
  [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]] && rm -rf "$TEMP_DIR"
  unset GATE05_AGENT_PASSWORD GATE05_EDITOR_PASSWORD
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

resolve_step01_dir() {
  [[ -s "$STEP01_LATEST" ]] || fail "Gate 0.5 Step 01 passing pointer is missing."
  local relative
  relative="$(tr -d '\r\n' < "$STEP01_LATEST")"
  [[ "$relative" =~ ^evidence/gates/gate-0\.5/baseline/gate05-step01-[A-Za-z0-9._-]+$ ]] || \
    fail "Unexpected Gate 0.5 Step 01 pointer: $relative"
  [[ -d "$LAB_ROOT/$relative" ]] || fail "Gate 0.5 Step 01 evidence is missing: $relative"
  printf '%s' "$LAB_ROOT/$relative"
}

check_prerequisites() {
  require_command bash
  require_command python3
  require_command ddev
  require_command curl
  require_command git
  require_command base64
  [[ -d "$DRUPAL_ROOT/.ddev" ]] || fail "Expected DDEV project at $DRUPAL_ROOT"
  [[ -f "$CREDENTIALS_FILE" ]] || fail "Missing local account credential file."
  [[ -x "$LAB_ROOT/scripts/run-gate05-step01.sh" ]] || fail "Missing Gate 0.5 Step 01 runner."
  [[ -x "$LAB_ROOT/scripts/gate05_step01_evidence.py" ]] || fail "Missing Gate 0.5 Step 01 evidence helper."
  [[ -x "$LAB_ROOT/scripts/gate05_step02_evidence.py" ]] || fail "Missing Step 02 evidence helper."
  [[ -f "$DRUPAL_ROOT/scripts/phase0-step17.php" ]] || fail "Missing source snapshot helper."
}

preview() {
  cat <<EOF
Gate 0.5 Step 02 preview

Operation:
  get_image_context(target)

Route:
  POST /api/agentic-harness/v1/image-context

Controls:
  - exact canonical sequence-1 target
  - agent_bot succeeds
  - anonymous and editor_dana are denied
  - malformed JSON and target identity fail closed
  - stale revision and changed file UUID fail closed
  - Base64 data URL remains runtime-only
  - source Article and suggestion count remain unchanged
  - no model variables or model calls

No recommendation is created and no Article field is changed.
EOF
}

setup() {
  check_prerequisites
  info "Starting DDEV and rebuilding Drupal's container..."
  (
    cd "$DRUPAL_ROOT"
    ddev start -y
    ddev php -l web/modules/custom/agentic_harness_tools/src/Controller/ToolController.php
    ddev php -l web/modules/custom/agentic_harness_tools/src/Exception/ImageContextException.php
    ddev php -l web/modules/custom/agentic_harness_tools/src/Service/ImageContextProvider.php
    ddev drush cr
    ddev drush php:eval '
      $route = \Drupal::service("router.route_provider")
        ->getRouteByName("agentic_harness_tools.get_image_context");
      if ($route->getPath() !== "/api/agentic-harness/v1/image-context") {
        throw new \RuntimeException("Unexpected image-context route path.");
      }
      $methods = $route->getMethods();
      if ($methods !== ["POST"]) {
        throw new \RuntimeException("Image-context route must allow only POST.");
      }
      $role = \Drupal\user\Entity\Role::load("agent_service");
      if (!$role || !$role->hasPermission("use agentic harness discovery tools")) {
        throw new \RuntimeException("agent_service lacks the shared read-only permission.");
      }
      $users = \Drupal::entityTypeManager()->getStorage("user")
        ->loadByProperties(["name" => "editor_dana"]);
      $editor = reset($users);
      if (!$editor instanceof \Drupal\user\UserInterface) {
        throw new \RuntimeException("editor_dana is missing.");
      }
      if ($editor->hasPermission("use agentic harness discovery tools")) {
        throw new \RuntimeException("editor_dana unexpectedly has the shared tool permission.");
      }
      print json_encode([
        "status" => "pass",
        "route" => $route->getPath(),
        "methods" => $methods,
        "permission" => "use agentic harness discovery tools",
        "agent_allowed" => TRUE,
        "editor_denied" => TRUE,
      ], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
    '
  )
  info "Confirming retained Gate 0.5 Step 01 evidence remains valid..."
  local step01_dir target_b64
  step01_dir="$(resolve_step01_dir)"
  python3 "$LAB_ROOT/scripts/gate05_step01_evidence.py" audit \
    --repo "$LAB_ROOT" --run-dir "$step01_dir"

  target_b64="$(base64 -w0 "$step01_dir/canonical-target.json")"
  info "Running a direct redacted provider smoke test..."
  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:eval "
      \$target = json_decode(
        base64_decode('$target_b64'),
        TRUE,
        512,
        JSON_THROW_ON_ERROR
      );
      \$result = \Drupal::service(
        'agentic_harness_tools.image_context_provider'
      )->get(\$target);
      if (
        (\$result['schema_version'] ?? NULL) !== 1
        || (\$result['target']['sequence'] ?? NULL) !== 1
        || (\$result['image']['representation']['kind'] ?? NULL) !== 'data_url'
        || !isset(\$result['image']['sha256'])
        || !isset(\$result['evidence_hash'])
      ) {
        throw new \RuntimeException(
          'Direct provider smoke test returned an unexpected shape.'
        );
      }
      print json_encode([
        'status' => 'pass',
        'target_sequence' => \$result['target']['sequence'],
        'representation_kind' => \$result['image']['representation']['kind'],
        'representation_value_retained' => FALSE,
        'image_sha256' => \$result['image']['sha256'],
        'image_byte_length' => \$result['image']['byte_length'],
        'evidence_hash' => \$result['evidence_hash'],
      ], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
    "
  )
  ok "Gate 0.5 Step 02 setup passed."
}

write_environment() {
  local output="$1" run_id="$2"
  python3 - "$output" "$run_id" <<'PY'
import json, os, platform, sys
from datetime import datetime, timezone
output, run_id = sys.argv[1:]
value = {
    "run_id": run_id,
    "captured_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "python": platform.python_version(),
    "operation": "get_image_context",
    "openai_api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
    "openai_candidate_model_present": bool(os.environ.get("OPENAI_CANDIDATE_MODEL")),
    "crewai_candidate_model_present": bool(os.environ.get("CREWAI_CANDIDATE_MODEL")),
    "model_call_performed": False,
}
json.dump(value, open(output, "w", encoding="utf-8"), indent=2, sort_keys=True)
open(output, "a", encoding="utf-8").write("\n")
PY
}

make_negative_targets() {
  local source="$1" output_dir="$2"
  python3 - "$source" "$output_dir" <<'PY'
import copy, json, sys
from pathlib import Path
source = json.load(open(sys.argv[1], encoding="utf-8"))
out = Path(sys.argv[2])
invalid = copy.deepcopy(source)
invalid.pop("file_uuid")
stale_revision = copy.deepcopy(source)
stale_revision["revision_id"] += 1000000
stale_file = copy.deepcopy(source)
stale_file["file_uuid"] = "00000000-0000-4000-8000-000000000000"
for name, value in (
    ("invalid-target-request.json", invalid),
    ("stale-revision-request.json", stale_revision),
    ("stale-file-request.json", stale_file),
):
    json.dump(value, open(out / name, "w", encoding="utf-8"), indent=2, sort_keys=True)
    open(out / name, "a", encoding="utf-8").write("\n")
PY
}

curl_post() {
  local config="$1" site_url="$2" input="$3" output="$4" correlation="$5"
  curl --silent --show-error --insecure \
    --config "$config" \
    --request POST \
    --header 'Accept: application/json' \
    --header 'Content-Type: application/json' \
    --header "X-Correlation-ID: $correlation" \
    --data-binary "@$input" \
    --output "$output" \
    --write-out '%{http_code}' \
    "$site_url/api/agentic-harness/v1/image-context"
}

run_step02() {
  check_prerequisites
  unset OPENAI_API_KEY OPENAI_CANDIDATE_MODEL CREWAI_CANDIDATE_MODEL

  local run_id="gate05-step02-$(date -u +'%Y%m%dT%H%M%SZ')-$$"
  local run_dir="$LOG_ROOT/$run_id"
  local run_rel="evidence/gates/gate-0.5/image-context/$run_id"
  mkdir -p "$run_dir"
  printf '%s\n' "$run_rel" > "$LAST_RUN_FILE"

  setup > >(tee "$run_dir/setup.log") 2>&1

  TEMP_DIR="$(mktemp -d)"
  chmod 700 "$TEMP_DIR"

  local step01_dir canonical_target site_url agent_password editor_password
  step01_dir="$(resolve_step01_dir)"
  canonical_target="$step01_dir/canonical-target.json"
  [[ -f "$canonical_target" ]] || fail "Step 01 canonical target is missing."
  cp -p "$canonical_target" "$run_dir/canonical-target-source.json"
  printf '%s\n' "${step01_dir#"$LAB_ROOT/"}" > "$run_dir/baseline-reference.txt"

  info "Restoring seeded-clean and importing the finalized Drupal configuration..."
  RESET_REQUIRED=1
  (
    cd "$DRUPAL_ROOT"
    bash scripts/run-phase0-step10.sh reset
    ddev drush cim -y
    ddev drush cr
    ddev drush --quiet php:script scripts/phase0-step17.php -- snapshot
  ) > "$run_dir/reset-and-source-before.log" 2>&1
  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:script scripts/phase0-step17.php -- snapshot
  ) > "$run_dir/source-before.json"

  site_url="$(resolve_site_url)"
  agent_password="$(latest_secret agent_bot)"
  editor_password="$(latest_secret editor_dana)"
  [[ -n "$agent_password" && -n "$editor_password" ]] || fail "Required local account credentials are missing."
  GATE05_AGENT_PASSWORD="$agent_password"
  GATE05_EDITOR_PASSWORD="$editor_password"

  umask 077
  printf 'user = "%s:%s"\n' "agent_bot" "$GATE05_AGENT_PASSWORD" > "$TEMP_DIR/agent.curlrc"
  printf 'user = "%s:%s"\n' "editor_dana" "$GATE05_EDITOR_PASSWORD" > "$TEMP_DIR/editor.curlrc"
  chmod 600 "$TEMP_DIR/agent.curlrc" "$TEMP_DIR/editor.curlrc"

  write_environment "$run_dir/environment.json" "$run_id"
  make_negative_targets "$canonical_target" "$TEMP_DIR"
  printf '{not-valid-json' > "$TEMP_DIR/malformed-request.json"

  info "Calling get_image_context() as agent_bot..."
  GATE05_AGENT_PASSWORD="$agent_password" \
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" get-image-context \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env GATE05_AGENT_PASSWORD \
      --correlation-id "$run_id-positive" \
      --target-file "$canonical_target" \
      --insecure-local \
      > "$TEMP_DIR/positive.json" 2> "$run_dir/positive-client.log"
  local positive_status=200

  info "Repeating the same context collection for stability..."
  GATE05_AGENT_PASSWORD="$agent_password" \
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" get-image-context \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env GATE05_AGENT_PASSWORD \
      --correlation-id "$run_id-repeat" \
      --target-file "$canonical_target" \
      --insecure-local \
      > "$TEMP_DIR/repeat.json" 2> "$run_dir/repeat-client.log"
  local repeat_status=200

  info "Running authorization and fail-closed negative controls..."
  local anonymous_status editor_status malformed_status invalid_status stale_revision_status stale_file_status
  anonymous_status="$(curl --silent --show-error --insecure \
    --request POST \
    --header 'Accept: application/json' \
    --header 'Content-Type: application/json' \
    --data-binary "@$canonical_target" \
    --output "$run_dir/anonymous-response.txt" \
    --write-out '%{http_code}' \
    "$site_url/api/agentic-harness/v1/image-context")"
  editor_status="$(curl_post "$TEMP_DIR/editor.curlrc" "$site_url" "$canonical_target" "$run_dir/editor-response.txt" "$run_id-editor")"
  malformed_status="$(curl_post "$TEMP_DIR/agent.curlrc" "$site_url" "$TEMP_DIR/malformed-request.json" "$run_dir/malformed-json.json" "$run_id-malformed")"
  invalid_status="$(curl_post "$TEMP_DIR/agent.curlrc" "$site_url" "$TEMP_DIR/invalid-target-request.json" "$run_dir/invalid-target.json" "$run_id-invalid")"
  stale_revision_status="$(curl_post "$TEMP_DIR/agent.curlrc" "$site_url" "$TEMP_DIR/stale-revision-request.json" "$run_dir/stale-revision.json" "$run_id-stale-revision")"
  stale_file_status="$(curl_post "$TEMP_DIR/agent.curlrc" "$site_url" "$TEMP_DIR/stale-file-request.json" "$run_dir/stale-file.json" "$run_id-stale-file")"

  python3 - "$run_dir/http-statuses.json" \
    "$positive_status" "$repeat_status" "$anonymous_status" "$editor_status" \
    "$malformed_status" "$invalid_status" "$stale_revision_status" "$stale_file_status" <<'PY'
import json, sys
path = sys.argv[1]
keys = (
    "positive", "repeat", "anonymous", "editor", "malformed_json",
    "invalid_target", "stale_revision", "stale_file",
)
values = [int(value) for value in sys.argv[2:]]
json.dump(dict(zip(keys, values)), open(path, "w", encoding="utf-8"), indent=2, sort_keys=True)
open(path, "a", encoding="utf-8").write("\n")
PY

  python3 - "$run_dir/authorization.json" "$anonymous_status" "$editor_status" <<'PY'
import json, sys
json.dump({
    "agent": 200,
    "anonymous": int(sys.argv[2]),
    "editor_dana": int(sys.argv[3]),
    "credentials_retained": False,
    "authorization_headers_retained": False,
}, open(sys.argv[1], "w", encoding="utf-8"), indent=2, sort_keys=True)
open(sys.argv[1], "a", encoding="utf-8").write("\n")
PY

  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:script scripts/phase0-step17.php -- snapshot
  ) > "$run_dir/source-after.json"
  RESET_COMPLETED=1

  info "Evaluating Step 02 controls and sanitizing retained evidence..."
  python3 "$LAB_ROOT/scripts/gate05_step02_evidence.py" evaluate \
    --repo "$LAB_ROOT" \
    --run-dir "$run_dir" \
    --raw-positive "$TEMP_DIR/positive.json" \
    --raw-repeat "$TEMP_DIR/repeat.json" \
    --canonical-target "$canonical_target"

  printf '%s\n' "$run_rel" > "$LATEST_FILE"

  info "Auditing retained Step 02 evidence..."
  python3 "$LAB_ROOT/scripts/gate05_step02_evidence.py" audit \
    --repo "$LAB_ROOT" \
    --run-dir "$run_dir"

  pass "Gate 0.5 Step 02 image-context operation passed."
  pass "Evidence: $run_rel"
  printf '\nDo not commit yet. Paste the complete terminal output into the program-lead chat.\n'
}

resolve_latest_run() {
  [[ -s "$LATEST_FILE" ]] || fail "No passing Gate 0.5 Step 02 run is recorded."
  local relative
  relative="$(tr -d '\r\n' < "$LATEST_FILE")"
  [[ "$relative" =~ ^evidence/gates/gate-0\.5/image-context/gate05-step02-[A-Za-z0-9._-]+$ ]] || \
    fail "Unexpected Step 02 latest pointer: $relative"
  [[ -d "$LAB_ROOT/$relative" ]] || fail "Step 02 evidence directory is missing: $relative"
  printf '%s' "$relative"
}

audit_latest() {
  check_prerequisites
  local step01_dir
  step01_dir="$(resolve_step01_dir)"
  python3 "$LAB_ROOT/scripts/gate05_step01_evidence.py" audit \
    --repo "$LAB_ROOT" --run-dir "$step01_dir"
  local relative
  relative="$(resolve_latest_run)"
  python3 "$LAB_ROOT/scripts/gate05_step02_evidence.py" audit \
    --repo "$LAB_ROOT" \
    --run-dir "$LAB_ROOT/$relative"
  pass "Gate 0.5 Step 02 audit passed."
  pass "Evidence: $relative"
}

status_latest() {
  local relative
  relative="$(resolve_latest_run)"
  cat "$LAB_ROOT/$relative/summary.md"
}

case "$MODE" in
  preview) preview ;;
  setup) setup ;;
  run) run_step02 ;;
  audit) audit_latest ;;
  status) status_latest ;;
  help|-h|--help) usage ;;
  *) usage; fail "Unknown mode: $MODE" ;;
esac
