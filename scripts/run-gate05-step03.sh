#!/usr/bin/env bash
set -Eeuo pipefail

RUNNER_VERSION="1.0.2"
MODE="${1:-help}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DRUPAL_ROOT="$LAB_ROOT/drupal"
LOG_ROOT="$LAB_ROOT/evidence/gates/gate-0.5/submit-recommendation"
LATEST_FILE="$LOG_ROOT/GATE05-STEP03-LATEST.txt"
LAST_RUN_FILE="$LOG_ROOT/GATE05-STEP03-LAST-RUN.txt"
STEP01_LATEST="$LAB_ROOT/evidence/gates/gate-0.5/baseline/GATE05-STEP01-LATEST.txt"
STEP02_LATEST="$LAB_ROOT/evidence/gates/gate-0.5/image-context/GATE05-STEP02-LATEST.txt"
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
Gate 0.5 Step 03 submit-recommendation runner, version $RUNNER_VERSION

Usage:
  bash scripts/run-gate05-step03.sh preview
  bash scripts/run-gate05-step03.sh setup
  bash scripts/run-gate05-step03.sh run
  bash scripts/run-gate05-step03.sh audit
  bash scripts/run-gate05-step03.sh status
EOF
}

cleanup() {
  local exit_code=$?
  set +e
  if [[ "$RESET_REQUIRED" -eq 1 && "$RESET_COMPLETED" -eq 0 ]]; then
    warn "Step 03 exited after entering mutation scope; attempting seeded-clean restore."
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

check_prior_evidence() {
  python3 "$LAB_ROOT/scripts/gate05_step03_evidence.py" audit-prior-step02 \
    --repo "$LAB_ROOT"
}

check_prerequisites() {
  for command in bash python3 ddev curl git base64; do
    require_command "$command"
  done
  [[ -d "$DRUPAL_ROOT/.ddev" ]] || fail "Expected DDEV project at $DRUPAL_ROOT"
  [[ -f "$CREDENTIALS_FILE" ]] || fail "Missing local account credential file."
  [[ -x "$LAB_ROOT/scripts/gate05_step03_evidence.py" ]] || fail "Missing Step 03 evidence helper."
  [[ -f "$DRUPAL_ROOT/scripts/gate05-step03.php" ]] || fail "Missing Step 03 Drupal inspection helper."
  check_prior_evidence
}

preview() {
  cat <<EOF
Gate 0.5 Step 03 preview

Operation:
  submit_recommendation(recommendation)

Route:
  POST /api/agentic-harness/v1/recommendations

Mutation boundary:
  - creates one unpublished alt_text_suggestion in pending review state
  - never changes the source Article or image field
  - exact replay returns the same node and revision
  - conflicting replay fails closed
  - successful and failed test state is reset to seeded-clean

This is a controlled, model-free substrate preflight. It does not claim a Drupal AI framework run.
EOF
}

setup() {
  check_prerequisites
  info "Starting DDEV and rebuilding Drupal's container..."
  (
    cd "$DRUPAL_ROOT"
    ddev start -y
    ddev php -l web/modules/custom/agentic_harness_tools/src/Controller/ToolController.php
    ddev php -l web/modules/custom/agentic_harness_tools/src/Exception/RecommendationSubmissionException.php
    ddev php -l web/modules/custom/agentic_harness_tools/src/Service/RecommendationValidator.php
    ddev php -l web/modules/custom/agentic_harness_tools/src/Service/RecommendationSubmitter.php
    ddev php -l scripts/gate05-step03.php
    ddev drush cr
    ddev drush php:eval '
      $route = \Drupal::service("router.route_provider")
        ->getRouteByName("agentic_harness_tools.submit_recommendation");
      if ($route->getPath() !== "/api/agentic-harness/v1/recommendations") {
        throw new \RuntimeException("Unexpected recommendation route path.");
      }
      if ($route->getMethods() !== ["POST"]) {
        throw new \RuntimeException("Recommendation route must allow only POST.");
      }
      if ($route->getRequirement("_permission") !== "create alt_text_suggestion content") {
        throw new \RuntimeException("Recommendation route has the wrong permission.");
      }
      foreach ([
        "agentic_harness_tools.recommendation_validator",
        "agentic_harness_tools.recommendation_submitter",
        "lock"
      ] as $service_id) {
        \Drupal::service($service_id);
      }
      foreach ([
        "field_target_node",
        "field_target_revision",
        "field_target_field",
        "field_target_delta",
        "field_target_file",
        "field_proposed_alt",
        "field_review_status",
        "field_source_framework",
        "field_run_id",
        "field_evidence_hash"
      ] as $field_name) {
        if (!\Drupal\field\Entity\FieldConfig::loadByName(
          "node",
          "alt_text_suggestion",
          $field_name
        )) {
          throw new \RuntimeException("Missing queue field: " . $field_name);
        }
      }
      $role = \Drupal\user\Entity\Role::load("agent_service");
      if (!$role || !$role->hasPermission("create alt_text_suggestion content")) {
        throw new \RuntimeException("agent_service lacks recommendation create permission.");
      }
      $editor_role = \Drupal\user\Entity\Role::load("content_editor");
      if (!$editor_role || $editor_role->hasPermission("create alt_text_suggestion content")) {
        throw new \RuntimeException("content_editor unexpectedly has recommendation create permission.");
      }
      print json_encode([
        "status" => "pass",
        "route" => $route->getPath(),
        "methods" => $route->getMethods(),
        "permission" => $route->getRequirement("_permission"),
        "agent_can_create" => TRUE,
        "editor_cannot_create" => TRUE,
        "validator_version" => \Drupal\agentic_harness_tools\Service\RecommendationValidator::VERSION,
      ], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
    '
  )

  info "Confirming retained prior-gate summaries..."
  check_prior_evidence

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

  info "Confirming the additive Step 03 implementation preserves Step 02 semantics..."
  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:eval "
      \$target = json_decode(base64_decode('$target_b64'), TRUE, 512, JSON_THROW_ON_ERROR);
      \$result = \Drupal::service(
        'agentic_harness_tools.image_context_provider'
      )->get(\$target);
      if (\$result['evidence_hash'] !== '$expected_context_hash') {
        throw new \RuntimeException(
          'Current context evidence hash differs from the passing Step 02 hash.'
        );
      }
      if (\$result['image']['sha256'] !== '$expected_image_hash') {
        throw new \RuntimeException(
          'Current image hash differs from the passing Step 02 hash.'
        );
      }
      print json_encode([
        'status' => 'pass',
        'target_sequence' => \$result['target']['sequence'],
        'representation_kind' => \$result['image']['representation']['kind'],
        'representation_value_retained' => FALSE,
        'image_sha256' => \$result['image']['sha256'],
        'evidence_hash' => \$result['evidence_hash'],
        'matches_passing_step02_evidence' => TRUE,
      ], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
    "
  )
  ok "Gate 0.5 Step 03 setup passed."
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
    "operation": "submit_recommendation",
    "controlled_preflight": True,
    "framework_execution_claimed": False,
    "openai_api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
    "openai_candidate_model_present": bool(os.environ.get("OPENAI_CANDIDATE_MODEL")),
    "crewai_candidate_model_present": bool(os.environ.get("CREWAI_CANDIDATE_MODEL")),
    "model_call_performed": False,
}
json.dump(value, open(output, "w", encoding="utf-8"), indent=2, sort_keys=True)
open(output, "a", encoding="utf-8").write("\n")
PY
}

build_requests() {
  local step01_dir="$1" step02_dir="$2" run_id="$3" output_dir="$4"
  python3 - "$step01_dir" "$step02_dir" "$run_id" "$output_dir" <<'PY'
import copy, json, sys
from pathlib import Path

step01 = Path(sys.argv[1])
step02 = Path(sys.argv[2])
run_id = sys.argv[3]
out = Path(sys.argv[4])

canonical = json.load(open(step01 / "canonical-target.json", encoding="utf-8"))
targets = json.load(open(step01 / "targets.json", encoding="utf-8"))
step02_summary = json.load(open(step02 / "summary.json", encoding="utf-8"))
sanitized = json.load(open(step02 / "response-sanitized.json", encoding="utf-8"))
filename = sanitized["envelope"]["data"]["image"]["filename"]

base = {
    "schema_version": 1,
    "target": canonical,
    "proposed_alt_text": (
        "A blue geometric illustration accompanying the seeded Article 01 content."
    ),
    "source_framework": "drupal_ai",
    "run_id": run_id,
    "evidence_hash": step02_summary["context_evidence_hash"],
    "validator_version": "gate05-validator-1.0.0",
}

requests = {"submission-request.json": base}

invalid = copy.deepcopy(base)
invalid.pop("validator_version")
requests["invalid-recommendation-request.json"] = invalid

stale_revision = copy.deepcopy(base)
stale_revision["target"]["revision_id"] += 1_000_000
requests["stale-revision-request.json"] = stale_revision

stale_file = copy.deepcopy(base)
stale_file["target"]["file_uuid"] = "00000000-0000-4000-8000-000000000000"
requests["stale-file-request.json"] = stale_file

run_mismatch = copy.deepcopy(base)
run_mismatch["run_id"] = run_id.replace("drupal_ai-", "langgraph-", 1)
requests["run-id-mismatch-request.json"] = run_mismatch

unsupported = copy.deepcopy(base)
unsupported["source_framework"] = "phase0_fixture"
requests["unsupported-source-request.json"] = unsupported

empty = copy.deepcopy(base)
empty["proposed_alt_text"] = "   "
requests["empty-alt-request.json"] = empty

too_long = copy.deepcopy(base)
too_long["proposed_alt_text"] = "A" * 251
requests["too-long-request.json"] = too_long

preamble = copy.deepcopy(base)
preamble["proposed_alt_text"] = "Alt text: A blue geometric illustration."
requests["preamble-request.json"] = preamble

generic = copy.deepcopy(base)
generic["proposed_alt_text"] = "image"
requests["generic-request.json"] = generic

filename_echo = copy.deepcopy(base)
filename_echo["proposed_alt_text"] = filename
requests["filename-echo-request.json"] = filename_echo

duplicate = copy.deepcopy(base)
duplicate["target"] = targets[9]
duplicate["proposed_alt_text"] = targets[9]["existing_alt"]
requests["duplicate-current-alt-request.json"] = duplicate

conflict = copy.deepcopy(base)
conflict["proposed_alt_text"] = (
    "A different blue illustration for the same run and target identity."
)
requests["idempotency-conflict-request.json"] = conflict

for name, value in requests.items():
    json.dump(value, open(out / name, "w", encoding="utf-8"), indent=2, sort_keys=True)
    open(out / name, "a", encoding="utf-8").write("\n")

(out / "malformed-request.json").write_text("{not-valid-json", encoding="utf-8")
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
    "$site_url/api/agentic-harness/v1/recommendations"
}

run_step03() {
  unset OPENAI_API_KEY OPENAI_CANDIDATE_MODEL CREWAI_CANDIDATE_MODEL

  local run_id="gate05-step03-$(date -u +'%Y%m%dT%H%M%SZ')-$$"
  local run_rel="evidence/gates/gate-0.5/submit-recommendation/$run_id"
  local run_dir="$LOG_ROOT/$run_id"
  mkdir -p "$run_dir"
  printf '%s\n' "$run_rel" > "$LAST_RUN_FILE"

  setup > >(tee "$run_dir/setup.log") 2>&1

  TEMP_DIR="$(mktemp -d)"
  chmod 700 "$TEMP_DIR"

  local step01_dir step02_dir submission_run_id site_url agent_password editor_password
  step01_dir="$(resolve_step01_dir)"
  step02_dir="$(resolve_step02_dir)"
  submission_run_id="drupal_ai-$(date -u +'%Y%m%dT%H%M%SZ')-$(python3 - <<'PY'
import secrets
print(secrets.token_hex(3))
PY
)"
  build_requests "$step01_dir" "$step02_dir" "$submission_run_id" "$TEMP_DIR"
  cp -p "$TEMP_DIR/submission-request.json" "$run_dir/submission-request.json"
  printf '%s\n' "${step01_dir#"$LAB_ROOT/"}" > "$run_dir/step01-reference.txt"
  printf '%s\n' "${step02_dir#"$LAB_ROOT/"}" > "$run_dir/step02-reference.txt"
  write_environment "$run_dir/environment.json" "$run_id"

  info "Restoring seeded-clean before entering the recommendation mutation boundary..."
  RESET_REQUIRED=1
  (
    cd "$DRUPAL_ROOT"
    bash scripts/run-phase0-step10.sh reset
    ddev drush cim -y
    ddev drush cr
  ) > "$run_dir/reset-before.log" 2>&1
  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:script scripts/gate05-step03.php -- snapshot
  ) > "$run_dir/source-before.json"

  site_url="$(resolve_site_url)"
  agent_password="$(latest_secret agent_bot)"
  editor_password="$(latest_secret editor_dana)"
  [[ -n "$agent_password" && -n "$editor_password" ]] || \
    fail "Required local account credentials are missing."
  GATE05_AGENT_PASSWORD="$agent_password"
  GATE05_EDITOR_PASSWORD="$editor_password"

  umask 077
  printf 'user = "%s:%s"\n' "agent_bot" "$GATE05_AGENT_PASSWORD" > "$TEMP_DIR/agent.curlrc"
  printf 'user = "%s:%s"\n' "editor_dana" "$GATE05_EDITOR_PASSWORD" > "$TEMP_DIR/editor.curlrc"
  chmod 600 "$TEMP_DIR/agent.curlrc" "$TEMP_DIR/editor.curlrc"

  info "Submitting one controlled pending recommendation as agent_bot..."
  GATE05_AGENT_PASSWORD="$agent_password" \
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" submit-recommendation \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env GATE05_AGENT_PASSWORD \
      --correlation-id "$run_id-positive" \
      --recommendation-file "$TEMP_DIR/submission-request.json" \
      --insecure-local \
      > "$run_dir/submit-response.json" 2> "$run_dir/positive-client.log"
  local positive_status=200

  info "Replaying the exact same idempotency identity..."
  GATE05_AGENT_PASSWORD="$agent_password" \
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" submit-recommendation \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env GATE05_AGENT_PASSWORD \
      --correlation-id "$run_id-replay" \
      --recommendation-file "$TEMP_DIR/submission-request.json" \
      --insecure-local \
      > "$run_dir/submit-replay-response.json" 2> "$run_dir/replay-client.log"
  local replay_status=200

  info "Running authorization, validation, stale-target, and idempotency negative controls..."
  local anonymous_status editor_status malformed_status invalid_status
  local stale_revision_status stale_file_status run_mismatch_status unsupported_status
  local empty_status too_long_status preamble_status generic_status filename_status
  local duplicate_status conflict_status

  anonymous_status="$(curl --silent --show-error --insecure \
    --request POST \
    --header 'Accept: application/json' \
    --header 'Content-Type: application/json' \
    --data-binary "@$TEMP_DIR/submission-request.json" \
    --output "$run_dir/anonymous-response.txt" \
    --write-out '%{http_code}' \
    "$site_url/api/agentic-harness/v1/recommendations")"
  editor_status="$(curl_post "$TEMP_DIR/editor.curlrc" "$site_url" \
    "$TEMP_DIR/submission-request.json" "$run_dir/editor-response.txt" "$run_id-editor")"
  malformed_status="$(curl_post "$TEMP_DIR/agent.curlrc" "$site_url" \
    "$TEMP_DIR/malformed-request.json" "$run_dir/malformed-json.json" "$run_id-malformed")"
  invalid_status="$(curl_post "$TEMP_DIR/agent.curlrc" "$site_url" \
    "$TEMP_DIR/invalid-recommendation-request.json" "$run_dir/invalid-recommendation.json" "$run_id-invalid")"
  stale_revision_status="$(curl_post "$TEMP_DIR/agent.curlrc" "$site_url" \
    "$TEMP_DIR/stale-revision-request.json" "$run_dir/stale-revision.json" "$run_id-stale-revision")"
  stale_file_status="$(curl_post "$TEMP_DIR/agent.curlrc" "$site_url" \
    "$TEMP_DIR/stale-file-request.json" "$run_dir/stale-file.json" "$run_id-stale-file")"
  run_mismatch_status="$(curl_post "$TEMP_DIR/agent.curlrc" "$site_url" \
    "$TEMP_DIR/run-id-mismatch-request.json" "$run_dir/run-id-mismatch.json" "$run_id-run-mismatch")"
  unsupported_status="$(curl_post "$TEMP_DIR/agent.curlrc" "$site_url" \
    "$TEMP_DIR/unsupported-source-request.json" "$run_dir/unsupported-source.json" "$run_id-source")"
  empty_status="$(curl_post "$TEMP_DIR/agent.curlrc" "$site_url" \
    "$TEMP_DIR/empty-alt-request.json" "$run_dir/empty-alt.json" "$run_id-empty")"
  too_long_status="$(curl_post "$TEMP_DIR/agent.curlrc" "$site_url" \
    "$TEMP_DIR/too-long-request.json" "$run_dir/too-long.json" "$run_id-long")"
  preamble_status="$(curl_post "$TEMP_DIR/agent.curlrc" "$site_url" \
    "$TEMP_DIR/preamble-request.json" "$run_dir/preamble.json" "$run_id-preamble")"
  generic_status="$(curl_post "$TEMP_DIR/agent.curlrc" "$site_url" \
    "$TEMP_DIR/generic-request.json" "$run_dir/generic.json" "$run_id-generic")"
  filename_status="$(curl_post "$TEMP_DIR/agent.curlrc" "$site_url" \
    "$TEMP_DIR/filename-echo-request.json" "$run_dir/filename-echo.json" "$run_id-filename")"
  duplicate_status="$(curl_post "$TEMP_DIR/agent.curlrc" "$site_url" \
    "$TEMP_DIR/duplicate-current-alt-request.json" "$run_dir/duplicate-current-alt.json" "$run_id-duplicate")"
  conflict_status="$(curl_post "$TEMP_DIR/agent.curlrc" "$site_url" \
    "$TEMP_DIR/idempotency-conflict-request.json" "$run_dir/idempotency-conflict.json" "$run_id-conflict")"

  python3 - "$run_dir/http-statuses.json" \
    "$positive_status" "$replay_status" "$anonymous_status" "$editor_status" \
    "$malformed_status" "$invalid_status" "$stale_revision_status" \
    "$stale_file_status" "$run_mismatch_status" "$unsupported_status" \
    "$empty_status" "$too_long_status" "$preamble_status" "$generic_status" \
    "$filename_status" "$duplicate_status" "$conflict_status" <<'PY'
import json, sys
keys = (
    "positive", "replay", "anonymous", "editor", "malformed_json",
    "invalid_recommendation", "stale_revision", "stale_file",
    "run_id_mismatch", "unsupported_source", "empty_alt", "too_long",
    "preamble", "generic", "filename_echo", "duplicate_current_alt",
    "idempotency_conflict",
)
values = [int(value) for value in sys.argv[2:]]
json.dump(dict(zip(keys, values)), open(sys.argv[1], "w", encoding="utf-8"), indent=2, sort_keys=True)
open(sys.argv[1], "a", encoding="utf-8").write("\n")
PY

  python3 - "$run_dir/authorization.json" "$anonymous_status" "$editor_status" <<'PY'
import json, sys
json.dump({
    "agent_bot": 200,
    "anonymous": int(sys.argv[2]),
    "editor_dana": int(sys.argv[3]),
    "permission": "create alt_text_suggestion content",
    "credentials_retained": False,
    "authorization_headers_retained": False,
}, open(sys.argv[1], "w", encoding="utf-8"), indent=2, sort_keys=True)
open(sys.argv[1], "a", encoding="utf-8").write("\n")
PY

  local recommendation_id
  recommendation_id="$(python3 - "$run_dir/submit-response.json" <<'PY'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["data"]["node_id"])
PY
)"
  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:script scripts/gate05-step03.php -- inspect "$recommendation_id"
  ) > "$run_dir/recommendation-inspection.json"
  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:script scripts/gate05-step03.php -- snapshot
  ) > "$run_dir/source-after.json"

  info "Restoring seeded-clean after the transient recommendation test..."
  (
    cd "$DRUPAL_ROOT"
    bash scripts/run-phase0-step10.sh reset
    ddev drush cim -y
    ddev drush cr
  ) > "$run_dir/reset-after.log" 2>&1
  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:script scripts/gate05-step03.php -- snapshot
  ) > "$run_dir/source-final-clean.json"
  RESET_COMPLETED=1

  info "Evaluating Step 03 controls..."
  python3 "$LAB_ROOT/scripts/gate05_step03_evidence.py" evaluate \
    --repo "$LAB_ROOT" \
    --run-dir "$run_dir"

  printf '%s\n' "$run_rel" > "$LATEST_FILE"

  info "Auditing retained Step 03 evidence..."
  python3 "$LAB_ROOT/scripts/gate05_step03_evidence.py" audit \
    --repo "$LAB_ROOT" \
    --run-dir "$run_dir"

  pass "Gate 0.5 Step 03 recommendation submission passed."
  pass "Evidence: $run_rel"
  printf '\nDo not commit yet. Paste the complete terminal output into the program-lead chat.\n'
}

resolve_latest_run() {
  [[ -s "$LATEST_FILE" ]] || fail "No passing Gate 0.5 Step 03 run is recorded."
  local relative
  relative="$(tr -d '\r\n' < "$LATEST_FILE")"
  [[ "$relative" =~ ^evidence/gates/gate-0\.5/submit-recommendation/gate05-step03-[A-Za-z0-9._-]+$ ]] || \
    fail "Unexpected Step 03 latest pointer: $relative"
  [[ -d "$LAB_ROOT/$relative" ]] || fail "Step 03 evidence directory is missing: $relative"
  printf '%s' "$relative"
}

audit_latest() {
  check_prerequisites
  local relative
  relative="$(resolve_latest_run)"
  python3 "$LAB_ROOT/scripts/gate05_step03_evidence.py" audit \
    --repo "$LAB_ROOT" \
    --run-dir "$LAB_ROOT/$relative"
  pass "Gate 0.5 Step 03 audit passed."
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
  run) run_step03 ;;
  audit) audit_latest ;;
  status) status_latest ;;
  help|-h|--help) usage ;;
  *) usage; fail "Unknown mode: $MODE" ;;
esac
