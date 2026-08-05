#!/usr/bin/env bash
set -Eeuo pipefail

RUNNER_VERSION="1.0.0"
MODE="${1:-help}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DRUPAL_ROOT="$LAB_ROOT/drupal"
LOG_ROOT="$LAB_ROOT/evidence/gates/gate-0.5/recommendation-status"
LATEST_FILE="$LOG_ROOT/GATE05-STEP04-LATEST.txt"
PENDING_FILE="$LOG_ROOT/GATE05-STEP04-PENDING.txt"
LAST_RUN_FILE="$LOG_ROOT/GATE05-STEP04-LAST-RUN.txt"
STEP01_LATEST="$LAB_ROOT/evidence/gates/gate-0.5/baseline/GATE05-STEP01-LATEST.txt"
STEP02_LATEST="$LAB_ROOT/evidence/gates/gate-0.5/image-context/GATE05-STEP02-LATEST.txt"
STEP03_LATEST="$LAB_ROOT/evidence/gates/gate-0.5/submit-recommendation/GATE05-STEP03-LATEST.txt"
CREDENTIALS_FILE="$DRUPAL_ROOT/.secrets/phase0-step7-accounts.txt"
TEMP_DIR=""
RESET_ON_EXIT=0

info() { printf '[INFO] %s\n' "$*"; }
ok() { printf '[OK] %s\n' "$*"; }
pass() { printf '[PASS] %s\n' "$*"; }
warn() { printf '[WARNING] %s\n' "$*" >&2; }
fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<EOF
Gate 0.5 Step 04 recommendation-status runner, version $RUNNER_VERSION

Usage:
  bash scripts/run-gate05-step04.sh preview
  bash scripts/run-gate05-step04.sh setup
  bash scripts/run-gate05-step04.sh run
  bash scripts/run-gate05-step04.sh certify
  bash scripts/run-gate05-step04.sh audit
  bash scripts/run-gate05-step04.sh status
  bash scripts/run-gate05-step04.sh abandon
EOF
}

cleanup() {
  local exit_code=$?
  set +e
  if [[ "$RESET_ON_EXIT" -eq 1 ]]; then
    warn "Step 04 exited inside a protected mutation scope; attempting seeded-clean restore."
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

resolve_gate_dir() {
  local pointer="$1" pattern="$2" label="$3"
  [[ -s "$pointer" ]] || fail "$label passing pointer is missing."
  local relative
  relative="$(tr -d '\r\n' < "$pointer")"
  [[ "$relative" =~ $pattern ]] || fail "Unexpected $label pointer: $relative"
  [[ -d "$LAB_ROOT/$relative" ]] || fail "$label evidence directory is missing: $relative"
  printf '%s' "$LAB_ROOT/$relative"
}

resolve_step01_dir() {
  resolve_gate_dir \
    "$STEP01_LATEST" \
    '^evidence/gates/gate-0\.5/baseline/gate05-step01-[A-Za-z0-9._-]+$' \
    'Gate 0.5 Step 01'
}

resolve_step02_dir() {
  resolve_gate_dir \
    "$STEP02_LATEST" \
    '^evidence/gates/gate-0\.5/image-context/gate05-step02-[A-Za-z0-9._-]+$' \
    'Gate 0.5 Step 02'
}

resolve_step03_dir() {
  resolve_gate_dir \
    "$STEP03_LATEST" \
    '^evidence/gates/gate-0\.5/submit-recommendation/gate05-step03-[A-Za-z0-9._-]+$' \
    'Gate 0.5 Step 03'
}

check_prior_evidence() {
  local step01_dir
  step01_dir="$(resolve_step01_dir)"
  python3 "$LAB_ROOT/scripts/gate05_step01_evidence.py" audit \
    --repo "$LAB_ROOT" \
    --run-dir "$step01_dir"
  python3 "$LAB_ROOT/scripts/gate05_step03_evidence.py" audit-prior-step02 \
    --repo "$LAB_ROOT"
  python3 "$LAB_ROOT/scripts/gate05_step04_evidence.py" audit-prior-step03 \
    --repo "$LAB_ROOT"
}

check_prerequisites() {
  for command in bash python3 ddev curl git base64; do
    require_command "$command"
  done
  [[ -d "$DRUPAL_ROOT/.ddev" ]] || fail "Expected DDEV project at $DRUPAL_ROOT"
  [[ -f "$CREDENTIALS_FILE" ]] || fail "Missing local account credential file."
  [[ -x "$LAB_ROOT/scripts/gate05_step04_evidence.py" ]] || \
    fail "Missing Step 04 evidence helper."
  [[ -f "$DRUPAL_ROOT/scripts/gate05-step04.php" ]] || \
    fail "Missing Step 04 Drupal helper."
  resolve_step01_dir >/dev/null
  resolve_step02_dir >/dev/null
  resolve_step03_dir >/dev/null
}

preview() {
  cat <<EOF
Gate 0.5 Step 04 preview

Semantic operation:
  get_recommendation_status(recommendation_id)

Route:
  GET /api/agentic-harness/v1/recommendations/{recommendation_id}/status

Two-stage proof:
  1. run creates one pending recommendation and observes pending status
  2. editor_dana approves it through Drupal's real edit form
  3. certify observes approved status, verifies revision provenance, and resets

The status operation is read-only. It cannot approve, reject, edit, publish, or apply content.
EOF
}

setup() {
  check_prerequisites
  info "Confirming retained Gate 0.5 evidence lineage..."
  check_prior_evidence

  info "Starting DDEV and rebuilding Drupal's container..."
  (
    cd "$DRUPAL_ROOT"
    ddev start -y
    ddev php -l web/modules/custom/agentic_harness_tools/src/Controller/ToolController.php
    ddev php -l web/modules/custom/agentic_harness_tools/src/Exception/RecommendationStatusException.php
    ddev php -l web/modules/custom/agentic_harness_tools/src/Service/RecommendationStatusProvider.php
    ddev php -l scripts/gate05-step04.php
    ddev drush cr
    ddev drush php:eval '
      $route = \Drupal::service("router.route_provider")
        ->getRouteByName("agentic_harness_tools.get_recommendation_status");
      if (
        $route->getPath()
          !== "/api/agentic-harness/v1/recommendations/{recommendation_id}/status"
        || $route->getMethods() !== ["GET"]
        || $route->getRequirement("_permission")
          !== "use agentic harness discovery tools"
        || $route->getOption("_auth") !== ["basic_auth"]
        || $route->getOption("no_cache") !== TRUE
      ) {
        throw new \RuntimeException("Recommendation status route contract failed.");
      }

      \Drupal::service("agentic_harness_tools.recommendation_status_provider");

      $agent_role = \Drupal\user\Entity\Role::load("agent_service");
      $editor_role = \Drupal\user\Entity\Role::load("content_editor");
      if (
        !$agent_role
        || !$agent_role->hasPermission("use agentic harness discovery tools")
        || !$editor_role
        || $editor_role->hasPermission("use agentic harness discovery tools")
      ) {
        throw new \RuntimeException("Recommendation status permission boundary failed.");
      }

      $type = \Drupal\node\Entity\NodeType::load("alt_text_suggestion");
      if (!$type || !$type->shouldCreateNewRevision()) {
        throw new \RuntimeException(
          "alt_text_suggestion must create a new revision on every review save."
        );
      }

      print json_encode([
        "status" => "pass",
        "route" => $route->getPath(),
        "methods" => $route->getMethods(),
        "permission" => $route->getRequirement("_permission"),
        "agent_can_read_status" => TRUE,
        "editor_cannot_read_agent_status_route" => TRUE,
        "review_saves_create_revisions" => TRUE,
      ], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
    '
  )

  local step01_dir step02_dir target_b64 expected_context_hash expected_image_hash
  step01_dir="$(resolve_step01_dir)"
  step02_dir="$(resolve_step02_dir)"
  target_b64="$(base64 -w0 "$step01_dir/canonical-target.json")"
  readarray -t expected_hashes < <(
    python3 - "$step02_dir/summary.json" <<'PY'
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
print(value["context_evidence_hash"])
print(value["image_sha256"])
PY
  )
  expected_context_hash="${expected_hashes[0]}"
  expected_image_hash="${expected_hashes[1]}"

  info "Confirming Step 04 preserves the passing Step 02 context semantics..."
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
        \$result['evidence_hash'] !== '$expected_context_hash'
        || \$result['image']['sha256'] !== '$expected_image_hash'
      ) {
        throw new \RuntimeException(
          'Current context result differs from the passing Step 02 evidence.'
        );
      }
      print json_encode([
        'status' => 'pass',
        'target_sequence' => \$result['target']['sequence'],
        'image_sha256' => \$result['image']['sha256'],
        'evidence_hash' => \$result['evidence_hash'],
        'matches_passing_step02_evidence' => TRUE,
        'representation_value_retained' => FALSE,
      ], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
    "
  )
  ok "Gate 0.5 Step 04 setup passed."
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
    "operations": [
        "submit_recommendation",
        "get_recommendation_status",
    ],
    "controlled_preflight": True,
    "framework_execution_claimed": False,
    "openai_api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
    "openai_candidate_model_present": bool(os.environ.get("OPENAI_CANDIDATE_MODEL")),
    "crewai_candidate_model_present": bool(os.environ.get("CREWAI_CANDIDATE_MODEL")),
    "model_call_performed": False,
    "human_review_required": True,
}
json.dump(value, open(output, "w", encoding="utf-8"), indent=2, sort_keys=True)
open(output, "a", encoding="utf-8").write("\n")
PY
}

build_submission() {
  local step01_dir="$1" step02_dir="$2" submission_run_id="$3" output="$4"
  python3 - "$step01_dir" "$step02_dir" "$submission_run_id" "$output" <<'PY'
import json, sys
from pathlib import Path
step01 = Path(sys.argv[1])
step02 = Path(sys.argv[2])
run_id = sys.argv[3]
output = Path(sys.argv[4])

target = json.load(open(step01 / "canonical-target.json", encoding="utf-8"))
step02_summary = json.load(open(step02 / "summary.json", encoding="utf-8"))
value = {
    "schema_version": 1,
    "target": target,
    "proposed_alt_text": (
        "A blue geometric illustration accompanying the seeded Article 01 content."
    ),
    "source_framework": "drupal_ai",
    "run_id": run_id,
    "evidence_hash": step02_summary["context_evidence_hash"],
    "validator_version": "gate05-validator-1.0.0",
}
json.dump(value, open(output, "w", encoding="utf-8"), indent=2, sort_keys=True)
open(output, "a", encoding="utf-8").write("\n")
PY
}

curl_status() {
  local config="$1" site_url="$2" identifier="$3" output="$4" correlation="$5"
  curl --silent --show-error --insecure \
    --config "$config" \
    --request GET \
    --header 'Accept: application/json' \
    --header "X-Correlation-ID: $correlation" \
    --output "$output" \
    --write-out '%{http_code}' \
    "$site_url/api/agentic-harness/v1/recommendations/$identifier/status"
}

resolve_pending_run() {
  [[ -s "$PENDING_FILE" ]] || \
    fail "No pending Step 04 human-review run exists. Run Package 0.5-04 first."
  local relative
  relative="$(tr -d '\r\n' < "$PENDING_FILE")"
  [[ "$relative" =~ ^evidence/gates/gate-0\.5/recommendation-status/gate05-step04-[A-Za-z0-9._-]+$ ]] || \
    fail "Unexpected Step 04 pending pointer: $relative"
  [[ -d "$LAB_ROOT/$relative" ]] || fail "Pending Step 04 evidence directory is missing."
  printf '%s' "$relative"
}

prepare_run() {
  check_prerequisites
  if [[ -s "$PENDING_FILE" ]]; then
    fail "A Step 04 run is already awaiting human review. Use certify, status, or abandon."
  fi

  unset OPENAI_API_KEY OPENAI_CANDIDATE_MODEL CREWAI_CANDIDATE_MODEL

  local run_id="gate05-step04-$(date -u +'%Y%m%dT%H%M%SZ')-$$"
  local run_rel="evidence/gates/gate-0.5/recommendation-status/$run_id"
  local run_dir="$LOG_ROOT/$run_id"
  mkdir -p "$run_dir"
  printf '%s\n' "$run_rel" > "$LAST_RUN_FILE"

  setup > >(tee "$run_dir/setup.log") 2>&1

  TEMP_DIR="$(mktemp -d)"
  chmod 700 "$TEMP_DIR"

  local step01_dir step02_dir step03_dir submission_run_id
  local site_url agent_password editor_password
  step01_dir="$(resolve_step01_dir)"
  step02_dir="$(resolve_step02_dir)"
  step03_dir="$(resolve_step03_dir)"
  submission_run_id="drupal_ai-$(date -u +'%Y%m%dT%H%M%SZ')-$(python3 - <<'PY'
import secrets
print(secrets.token_hex(3))
PY
)"

  build_submission \
    "$step01_dir" \
    "$step02_dir" \
    "$submission_run_id" \
    "$TEMP_DIR/submission-request.json"
  cp -p "$TEMP_DIR/submission-request.json" "$run_dir/submission-request.json"
  printf '%s\n' "${step01_dir#"$LAB_ROOT/"}" > "$run_dir/step01-reference.txt"
  printf '%s\n' "${step02_dir#"$LAB_ROOT/"}" > "$run_dir/step02-reference.txt"
  printf '%s\n' "${step03_dir#"$LAB_ROOT/"}" > "$run_dir/step03-reference.txt"
  write_environment "$run_dir/environment.json" "$run_id"

  info "Restoring seeded-clean before creating the human-review record..."
  RESET_ON_EXIT=1
  (
    cd "$DRUPAL_ROOT"
    bash scripts/run-phase0-step10.sh reset
    ddev drush cim -y
    ddev drush cr
  ) > "$run_dir/reset-before.log" 2>&1
  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:script scripts/gate05-step04.php -- snapshot
  ) > "$run_dir/source-before.json"

  site_url="$(resolve_site_url)"
  agent_password="$(latest_secret agent_bot)"
  editor_password="$(latest_secret editor_dana)"
  [[ -n "$agent_password" && -n "$editor_password" ]] || \
    fail "Required local account credentials are missing."
  GATE05_AGENT_PASSWORD="$agent_password"
  GATE05_EDITOR_PASSWORD="$editor_password"

  umask 077
  printf 'user = "%s:%s"\n' "agent_bot" "$GATE05_AGENT_PASSWORD" \
    > "$TEMP_DIR/agent.curlrc"
  printf 'user = "%s:%s"\n' "editor_dana" "$GATE05_EDITOR_PASSWORD" \
    > "$TEMP_DIR/editor.curlrc"
  chmod 600 "$TEMP_DIR/agent.curlrc" "$TEMP_DIR/editor.curlrc"

  info "Creating one pending recommendation as agent_bot..."
  GATE05_AGENT_PASSWORD="$agent_password" \
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" submit-recommendation \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env GATE05_AGENT_PASSWORD \
      --correlation-id "$run_id-submit" \
      --recommendation-file "$TEMP_DIR/submission-request.json" \
      --insecure-local \
      > "$run_dir/submit-response.json" \
      2> "$run_dir/submit-client.log"

  info "Replaying the exact submission identity..."
  GATE05_AGENT_PASSWORD="$agent_password" \
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" submit-recommendation \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env GATE05_AGENT_PASSWORD \
      --correlation-id "$run_id-replay" \
      --recommendation-file "$TEMP_DIR/submission-request.json" \
      --insecure-local \
      > "$run_dir/submit-replay-response.json" \
      2> "$run_dir/replay-client.log"

  local recommendation_id recommendation_uuid recommendation_revision article_id
  readarray -t recommendation_values < <(
    python3 - "$run_dir/submit-response.json" <<'PY'
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))["data"]
print(value["node_id"])
print(value["uuid"])
print(value["revision_id"])
PY
  )
  recommendation_id="${recommendation_values[0]}"
  recommendation_uuid="${recommendation_values[1]}"
  recommendation_revision="${recommendation_values[2]}"

  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:script scripts/gate05-step04.php -- inspect "$recommendation_id"
  ) > "$run_dir/pending-inspection.json"
  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:script scripts/gate05-step04.php -- snapshot
  ) > "$run_dir/source-pending.json"

  article_id="$(python3 - "$run_dir/pending-inspection.json" <<'PY'
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
print(value["current_target"]["node_id"])
PY
)"

  info "Observing pending status by UUID, node ID, and repeat read..."
  GATE05_AGENT_PASSWORD="$agent_password" \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" get-recommendation-status \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env GATE05_AGENT_PASSWORD \
      --correlation-id "$run_id-pending-uuid" \
      --recommendation-id "$recommendation_uuid" \
      --insecure-local \
      > "$run_dir/pending-status-uuid.json" \
      2> "$run_dir/pending-status-client.log"
  GATE05_AGENT_PASSWORD="$agent_password" \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" get-recommendation-status \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env GATE05_AGENT_PASSWORD \
      --correlation-id "$run_id-pending-nid" \
      --recommendation-id "$recommendation_id" \
      --insecure-local \
      > "$run_dir/pending-status-nid.json" \
      2> "$run_dir/pending-status-nid-client.log"
  GATE05_AGENT_PASSWORD="$agent_password" \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" get-recommendation-status \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env GATE05_AGENT_PASSWORD \
      --correlation-id "$run_id-pending-repeat" \
      --recommendation-id "$recommendation_uuid" \
      --insecure-local \
      > "$run_dir/pending-status-repeat.json" \
      2> "$run_dir/pending-status-repeat-client.log"

  info "Running status-route authorization and identifier negative controls..."
  local anonymous_status editor_status invalid_status unknown_status wrong_bundle_status
  anonymous_status="$(curl --silent --show-error --insecure \
    --request GET \
    --header 'Accept: application/json' \
    --output "$run_dir/anonymous-response.txt" \
    --write-out '%{http_code}' \
    "$site_url/api/agentic-harness/v1/recommendations/$recommendation_uuid/status")"
  editor_status="$(curl_status \
    "$TEMP_DIR/editor.curlrc" \
    "$site_url" \
    "$recommendation_uuid" \
    "$run_dir/editor-response.txt" \
    "$run_id-editor")"
  invalid_status="$(curl_status \
    "$TEMP_DIR/agent.curlrc" \
    "$site_url" \
    "not-an-id" \
    "$run_dir/invalid-id.json" \
    "$run_id-invalid")"
  unknown_status="$(curl_status \
    "$TEMP_DIR/agent.curlrc" \
    "$site_url" \
    "00000000-0000-4000-8000-000000000000" \
    "$run_dir/unknown-uuid.json" \
    "$run_id-unknown")"
  wrong_bundle_status="$(curl_status \
    "$TEMP_DIR/agent.curlrc" \
    "$site_url" \
    "$article_id" \
    "$run_dir/wrong-bundle.json" \
    "$run_id-wrong-bundle")"

  python3 - "$run_dir/status-http-statuses.json" \
    "$anonymous_status" "$editor_status" "$invalid_status" \
    "$unknown_status" "$wrong_bundle_status" <<'PY'
import json, sys
value = {
    "positive_uuid": 200,
    "positive_nid": 200,
    "positive_repeat": 200,
    "anonymous": int(sys.argv[2]),
    "editor": int(sys.argv[3]),
    "invalid_id": int(sys.argv[4]),
    "unknown_uuid": int(sys.argv[5]),
    "wrong_bundle": int(sys.argv[6]),
}
json.dump(value, open(sys.argv[1], "w", encoding="utf-8"), indent=2, sort_keys=True)
open(sys.argv[1], "a", encoding="utf-8").write("\n")
PY

  python3 - "$run_dir/authorization.json" \
    "$anonymous_status" "$editor_status" <<'PY'
import json, sys
value = {
    "agent_bot_status_access": 200,
    "anonymous_status_access": int(sys.argv[2]),
    "editor_dana_status_access": int(sys.argv[3]),
    "status_route_permission": "use agentic harness discovery tools",
    "editor_review_access_via_drupal_form": True,
    "credentials_retained": False,
    "authorization_headers_retained": False,
}
json.dump(value, open(sys.argv[1], "w", encoding="utf-8"), indent=2, sort_keys=True)
open(sys.argv[1], "a", encoding="utf-8").write("\n")
PY

  info "Evaluating the pending human-review checkpoint..."
  python3 "$LAB_ROOT/scripts/gate05_step04_evidence.py" prepare \
    --repo "$LAB_ROOT" \
    --run-dir "$run_dir"

  local review_url="$site_url/node/$recommendation_id/edit"
  python3 - "$run_dir/human-review-instructions.json" \
    "$review_url" "$recommendation_id" "$recommendation_uuid" \
    "$recommendation_revision" <<'PY'
import json, sys
value = {
    "status": "human_action_required",
    "review_url": sys.argv[2],
    "recommendation_node_id": int(sys.argv[3]),
    "recommendation_uuid": sys.argv[4],
    "pending_revision_id": int(sys.argv[5]),
    "reviewer_username": "editor_dana",
    "required_action": "approved",
    "proposed_alt_text_must_remain_unchanged": True,
    "save_count_required": 1,
    "credential_file": "drupal/.secrets/phase0-step7-accounts.txt",
    "credentials_retained_in_evidence": False,
}
json.dump(value, open(sys.argv[1], "w", encoding="utf-8"), indent=2, sort_keys=True)
open(sys.argv[1], "a", encoding="utf-8").write("\n")
PY

  printf '%s\n' "$run_rel" > "$PENDING_FILE"
  RESET_ON_EXIT=0

  printf '\n'
  printf '=== HUMAN ACTION REQUIRED ===\n'
  printf '1. Open: %s\n' "$review_url"
  printf '2. Sign in as editor_dana using the existing local Step 7 credential file.\n'
  printf '3. Change no fields except Review status.\n'
  printf '4. Set Review status to Approved.\n'
  printf '5. Save exactly once.\n'
  printf '6. Return to this package directory and run:\n'
  printf '   bash package.sh certify %s\n' "$LAB_ROOT"
  printf '\n'
  printf 'The pending recommendation is intentionally retained until certification.\n'
  printf 'Do not commit and do not run the seeded-clean reset manually.\n'
}

certify_run() {
  check_prerequisites
  local run_rel run_dir
  run_rel="$(resolve_pending_run)"
  run_dir="$LAB_ROOT/$run_rel"

  setup > >(tee "$run_dir/certify-setup.log") 2>&1

  TEMP_DIR="$(mktemp -d)"
  chmod 700 "$TEMP_DIR"

  local recommendation_id recommendation_uuid
  readarray -t recommendation_values < <(
    python3 - "$run_dir/prepare-summary.json" <<'PY'
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))["recommendation"]
print(value["node_id"])
print(value["uuid"])
PY
  )
  recommendation_id="${recommendation_values[0]}"
  recommendation_uuid="${recommendation_values[1]}"

  local site_url agent_password
  site_url="$(resolve_site_url)"
  agent_password="$(latest_secret agent_bot)"
  [[ -n "$agent_password" ]] || fail "agent_bot credential is missing."
  GATE05_AGENT_PASSWORD="$agent_password"

  info "Inspecting the Drupal revision created by the human reviewer..."
  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:script scripts/gate05-step04.php -- snapshot
  ) > "$run_dir/source-reviewed-before-status.json"
  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:script scripts/gate05-step04.php -- inspect "$recommendation_id"
  ) > "$run_dir/reviewed-inspection.json"

  info "Observing approved status by UUID, node ID, and repeat read..."
  GATE05_AGENT_PASSWORD="$agent_password" \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" get-recommendation-status \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env GATE05_AGENT_PASSWORD \
      --correlation-id "$(basename "$run_dir")-approved-uuid" \
      --recommendation-id "$recommendation_uuid" \
      --insecure-local \
      > "$run_dir/approved-status-uuid.json" \
      2> "$run_dir/approved-status-client.log"
  GATE05_AGENT_PASSWORD="$agent_password" \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" get-recommendation-status \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env GATE05_AGENT_PASSWORD \
      --correlation-id "$(basename "$run_dir")-approved-nid" \
      --recommendation-id "$recommendation_id" \
      --insecure-local \
      > "$run_dir/approved-status-nid.json" \
      2> "$run_dir/approved-status-nid-client.log"
  GATE05_AGENT_PASSWORD="$agent_password" \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" get-recommendation-status \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env GATE05_AGENT_PASSWORD \
      --correlation-id "$(basename "$run_dir")-approved-repeat" \
      --recommendation-id "$recommendation_uuid" \
      --insecure-local \
      > "$run_dir/approved-status-repeat.json" \
      2> "$run_dir/approved-status-repeat-client.log"

  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:script scripts/gate05-step04.php -- snapshot
  ) > "$run_dir/source-reviewed-after-status.json"

  info "Validating the human decision before resetting any state..."
  python3 "$LAB_ROOT/scripts/gate05_step04_evidence.py" reviewed-precheck \
    --repo "$LAB_ROOT" \
    --run-dir "$run_dir"

  info "Restoring seeded-clean after the certified human decision..."
  RESET_ON_EXIT=1
  (
    cd "$DRUPAL_ROOT"
    bash scripts/run-phase0-step10.sh reset
    ddev drush cim -y
    ddev drush cr
  ) > "$run_dir/reset-after.log" 2>&1
  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:script scripts/gate05-step04.php -- snapshot
  ) > "$run_dir/source-final-clean.json"

  info "Finalizing retained Step 04 evidence..."
  python3 "$LAB_ROOT/scripts/gate05_step04_evidence.py" finalize \
    --repo "$LAB_ROOT" \
    --run-dir "$run_dir"

  printf '%s\n' "$run_rel" > "$LATEST_FILE"
  rm -f "$PENDING_FILE"
  RESET_ON_EXIT=0

  info "Auditing retained Step 04 evidence..."
  python3 "$LAB_ROOT/scripts/gate05_step04_evidence.py" audit \
    --repo "$LAB_ROOT" \
    --run-dir "$run_dir"

  pass "Gate 0.5 Step 04 recommendation status and human review passed."
  pass "Evidence: $run_rel"
  printf '\nDo not commit yet. Paste the complete terminal output into the program-lead chat.\n'
}

resolve_latest_run() {
  [[ -s "$LATEST_FILE" ]] || fail "No passing Gate 0.5 Step 04 run is recorded."
  local relative
  relative="$(tr -d '\r\n' < "$LATEST_FILE")"
  [[ "$relative" =~ ^evidence/gates/gate-0\.5/recommendation-status/gate05-step04-[A-Za-z0-9._-]+$ ]] || \
    fail "Unexpected Step 04 latest pointer: $relative"
  [[ -d "$LAB_ROOT/$relative" ]] || fail "Step 04 evidence directory is missing."
  printf '%s' "$relative"
}

audit_latest() {
  check_prerequisites
  check_prior_evidence
  local relative
  relative="$(resolve_latest_run)"
  python3 "$LAB_ROOT/scripts/gate05_step04_evidence.py" audit \
    --repo "$LAB_ROOT" \
    --run-dir "$LAB_ROOT/$relative"
  pass "Gate 0.5 Step 04 audit passed."
  pass "Evidence: $relative"
}

status_run() {
  if [[ -s "$PENDING_FILE" ]]; then
    local relative
    relative="$(resolve_pending_run)"
    cat "$LAB_ROOT/$relative/prepare-summary.json"
    printf '\nHuman review instructions:\n'
    cat "$LAB_ROOT/$relative/human-review-instructions.json"
    return
  fi

  local relative
  relative="$(resolve_latest_run)"
  cat "$LAB_ROOT/$relative/summary.md"
}

abandon_run() {
  local relative run_dir
  relative="$(resolve_pending_run)"
  run_dir="$LAB_ROOT/$relative"

  warn "Abandoning the pending Step 04 run and restoring seeded-clean."
  (
    cd "$DRUPAL_ROOT"
    bash scripts/run-phase0-step10.sh reset
    ddev drush cim -y
    ddev drush cr
  )

  python3 - "$run_dir/abandoned.json" <<'PY'
import json, sys
from datetime import datetime, timezone
value = {
    "status": "abandoned",
    "abandoned_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "evidence_retained": True,
    "final_state": "seeded-clean",
}
json.dump(value, open(sys.argv[1], "w", encoding="utf-8"), indent=2, sort_keys=True)
open(sys.argv[1], "a", encoding="utf-8").write("\n")
PY
  rm -f "$PENDING_FILE"
  ok "Pending Step 04 run abandoned; evidence retained at $relative."
}

case "$MODE" in
  preview) preview ;;
  setup) setup ;;
  run) prepare_run ;;
  certify) certify_run ;;
  audit) audit_latest ;;
  status) status_run ;;
  abandon) abandon_run ;;
  help|-h|--help) usage ;;
  *) usage; fail "Unknown mode: $MODE" ;;
esac
