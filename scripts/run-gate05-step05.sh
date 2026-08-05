#!/usr/bin/env bash
set -Eeuo pipefail

RUNNER_VERSION="1.1.0"
MODE="${1:-help}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DRUPAL_ROOT="$LAB_ROOT/drupal"
LOG_ROOT="$LAB_ROOT/evidence/gates/gate-0.5/substrate-certification"
LATEST_FILE="$LOG_ROOT/GATE05-STEP05-LATEST.txt"
LAST_RUN_FILE="$LOG_ROOT/GATE05-STEP05-LAST-RUN.txt"
STEP01_LATEST="$LAB_ROOT/evidence/gates/gate-0.5/baseline/GATE05-STEP01-LATEST.txt"
STEP02_LATEST="$LAB_ROOT/evidence/gates/gate-0.5/image-context/GATE05-STEP02-LATEST.txt"
STEP03_LATEST="$LAB_ROOT/evidence/gates/gate-0.5/submit-recommendation/GATE05-STEP03-LATEST.txt"
STEP04_LATEST="$LAB_ROOT/evidence/gates/gate-0.5/recommendation-status/GATE05-STEP04-LATEST.txt"
STEP04_PENDING="$LAB_ROOT/evidence/gates/gate-0.5/recommendation-status/GATE05-STEP04-PENDING.txt"
SCHEMA_REGRESSION="$LAB_ROOT/scripts/gate05_schema_regression.py"
SCHEMA_PYTHON="$LAB_ROOT/crewai/.venv/bin/python"
HISTORICAL_STEP05_RUN="gate05-step05-20260805T010224Z-1100690"
SUPERSEDED_STEP05_RUN="gate05-step05-20260805T174126Z-18681"
BASELINE_TOOL_RESULT_SCHEMA_SHA256="ce29b82eaf9e3ddba9cf92b28f76a522a3438c743aa0955611bad2f16fd569d8"
REPAIRED_TOOL_RESULT_SCHEMA_SHA256="ce04e938eb4e34e861c000b86fffeed4adc5e5c66167c52ebf5380b8cd3cd91b"
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
Gate 0.5 Step 05 substrate-certification runner, version $RUNNER_VERSION

Usage:
  bash scripts/run-gate05-step05.sh preview
  bash scripts/run-gate05-step05.sh setup
  bash scripts/run-gate05-step05.sh run
  bash scripts/run-gate05-step05.sh resume
  bash scripts/run-gate05-step05.sh audit
  bash scripts/run-gate05-step05.sh status
EOF
}

cleanup() {
  local exit_code=$?
  set +e
  if [[ "$RESET_REQUIRED" -eq 1 && "$RESET_COMPLETED" -eq 0 ]]; then
    warn "Step 05 exited inside the mutation boundary; attempting seeded-clean restore."
    (
      cd "$DRUPAL_ROOT"
      bash scripts/run-phase0-step10.sh reset
      ddev drush cim -y
      ddev drush cr
    ) >/dev/null 2>&1 || warn "Emergency reset failed. Restore seeded-clean manually."
  fi
  [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]] && rm -rf "$TEMP_DIR"
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

resolve_step04_dir() {
  resolve_gate_dir \
    "$STEP04_LATEST" \
    '^evidence/gates/gate-0\.5/recommendation-status/gate05-step04-[A-Za-z0-9._-]+$' \
    'Gate 0.5 Step 04'
}

audit_step01_with_approved_schema_repair() {
  local step01_dir="$1" audit_dir
  audit_dir="$(mktemp -d)"
  chmod 700 "$audit_dir"
  cp -a "$step01_dir/." "$audit_dir/"

  python3 - \
    "$LAB_ROOT" \
    "$step01_dir/summary.json" \
    "$audit_dir/summary.json" \
    "$audit_dir/contract-sha256.txt" \
    "$BASELINE_TOOL_RESULT_SCHEMA_SHA256" \
    "$REPAIRED_TOOL_RESULT_SCHEMA_SHA256" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

repo = Path(sys.argv[1])
source_summary_path = Path(sys.argv[2])
audit_summary_path = Path(sys.argv[3])
audit_manifest_path = Path(sys.argv[4])
baseline_hash = sys.argv[5]
repaired_hash = sys.argv[6]
schema_relative = "shared/schemas/tool-result.schema.json"

summary = json.loads(source_summary_path.read_text(encoding="utf-8"))
expected = summary.get("contract_files")
if not isinstance(expected, dict) or expected.get(schema_relative) != baseline_hash:
    raise SystemExit("[ERROR] Step 01 does not carry the approved baseline schema hash.")

current = {}
for relative in expected:
    path = repo / relative
    if not path.is_file():
        raise SystemExit(f"[ERROR] Missing Step 01 contract file: {relative}")
    current[relative] = hashlib.sha256(path.read_bytes()).hexdigest()

unexpected = {
    relative: {"baseline": expected_hash, "current": current[relative]}
    for relative, expected_hash in expected.items()
    if relative != schema_relative and current[relative] != expected_hash
}
if unexpected:
    raise SystemExit(
        "[ERROR] Step 01 contract drift exceeds the approved schema repair: "
        + ", ".join(sorted(unexpected))
    )
if current.get(schema_relative) != repaired_hash:
    raise SystemExit("[ERROR] Current tool-result schema is not the approved repaired hash.")

audit_summary = dict(summary)
audit_summary["contract_files"] = dict(expected)
audit_summary["contract_files"][schema_relative] = repaired_hash
audit_summary_path.write_text(
    json.dumps(audit_summary, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

lines = []
for line in audit_manifest_path.read_text(encoding="utf-8").splitlines():
    digest, relative = line.split(maxsplit=1)
    if relative == schema_relative:
        digest = repaired_hash
    lines.append(f"{digest}  {relative}")
audit_manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(json.dumps({
    "status": "pass",
    "approved_transition": schema_relative,
    "baseline_sha256": baseline_hash,
    "repaired_sha256": repaired_hash,
    "other_step01_contract_hashes_changed": [],
}, indent=2, sort_keys=True))
PY

  python3 "$LAB_ROOT/scripts/gate05_step01_evidence.py" audit \
    --repo "$LAB_ROOT" \
    --run-dir "$audit_dir"
  rm -rf "$audit_dir"
}

audit_step04_with_approved_schema_repair() {
  local step04_dir="$1" audit_dir
  audit_dir="$(mktemp -d)"
  chmod 700 "$audit_dir"
  cp -a "$step04_dir/." "$audit_dir/"

  python3 - \
    "$LAB_ROOT" \
    "$step04_dir/summary.json" \
    "$audit_dir/summary.json" \
    "$audit_dir/implementation-sha256.txt" \
    "$BASELINE_TOOL_RESULT_SCHEMA_SHA256" \
    "$REPAIRED_TOOL_RESULT_SCHEMA_SHA256" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

repo = Path(sys.argv[1])
source_summary_path = Path(sys.argv[2])
audit_summary_path = Path(sys.argv[3])
audit_manifest_path = Path(sys.argv[4])
baseline_hash = sys.argv[5]
repaired_hash = sys.argv[6]
schema_relative = "shared/schemas/tool-result.schema.json"

summary = json.loads(source_summary_path.read_text(encoding="utf-8"))
expected = summary.get("implementation_files")
if not isinstance(expected, dict) or expected.get(schema_relative) != baseline_hash:
    raise SystemExit("[ERROR] Step 04 does not carry the approved baseline schema hash.")

current = {}
for relative in expected:
    path = repo / relative
    if not path.is_file():
        raise SystemExit(f"[ERROR] Missing Step 04 implementation file: {relative}")
    current[relative] = hashlib.sha256(path.read_bytes()).hexdigest()

unexpected = {
    relative: {"baseline": expected_hash, "current": current[relative]}
    for relative, expected_hash in expected.items()
    if relative != schema_relative and current[relative] != expected_hash
}
if unexpected:
    raise SystemExit(
        "[ERROR] Step 04 implementation drift exceeds the approved schema repair: "
        + ", ".join(sorted(unexpected))
    )
if current.get(schema_relative) != repaired_hash:
    raise SystemExit("[ERROR] Current tool-result schema is not the approved repaired hash.")

audit_summary = dict(summary)
audit_summary["implementation_files"] = dict(expected)
audit_summary["implementation_files"][schema_relative] = repaired_hash
audit_summary_path.write_text(
    json.dumps(audit_summary, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

lines = []
for line in audit_manifest_path.read_text(encoding="utf-8").splitlines():
    digest, relative = line.split(maxsplit=1)
    if relative == schema_relative:
        digest = repaired_hash
    lines.append(f"{digest}  {relative}")
audit_manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(json.dumps({
    "status": "pass",
    "approved_transition": schema_relative,
    "baseline_sha256": baseline_hash,
    "repaired_sha256": repaired_hash,
    "other_step04_implementation_hashes_changed": [],
}, indent=2, sort_keys=True))
PY

  python3 "$LAB_ROOT/scripts/gate05_step04_evidence.py" audit \
    --repo "$LAB_ROOT" \
    --run-dir "$audit_dir"
  rm -rf "$audit_dir"
}

check_prior_evidence() {
  [[ ! -s "$STEP04_PENDING" ]] || \
    fail "A Step 04 run is still awaiting human review. Certify or abandon it first."

  local step01_dir step04_dir
  step01_dir="$(resolve_step01_dir)"
  step04_dir="$(resolve_step04_dir)"

  audit_step01_with_approved_schema_repair "$step01_dir"

  python3 "$LAB_ROOT/scripts/gate05_step03_evidence.py" audit-prior-step02 \
    --repo "$LAB_ROOT"

  python3 "$LAB_ROOT/scripts/gate05_step04_evidence.py" audit-prior-step03 \
    --repo "$LAB_ROOT"

  audit_step04_with_approved_schema_repair "$step04_dir"
}

check_prerequisites() {
  for command in bash python3 ddev git base64; do
    require_command "$command"
  done
  [[ -d "$DRUPAL_ROOT/.ddev" ]] || fail "Expected DDEV project at $DRUPAL_ROOT"
  [[ -f "$CREDENTIALS_FILE" ]] || fail "Missing local account credential file."
  [[ -x "$LAB_ROOT/scripts/gate05_step05_evidence.py" ]] || \
    fail "Missing Step 05 evidence helper."
  [[ -x "$SCHEMA_REGRESSION" ]] || \
    fail "Missing Step 05 JSON Schema regression helper."
  [[ -x "$SCHEMA_PYTHON" ]] || \
    fail "Missing locked CrewAI Python environment for JSON Schema validation."
  [[ -f "$DRUPAL_ROOT/scripts/gate05-step04.php" ]] || \
    fail "Missing Step 04 snapshot and inspection helper."
  [[ -x "$LAB_ROOT/shared/drupal_client/client.py" ]] || \
    fail "Missing shared Drupal client."
  [[ -f "$DRUPAL_ROOT/scripts/gate05-step05-config.php" ]] || \
    fail "Missing Step 05 active-configuration helper."
  resolve_step01_dir >/dev/null
  resolve_step02_dir >/dev/null
  resolve_step03_dir >/dev/null
  resolve_step04_dir >/dev/null
}

audit_retained_success_schemas() {
  "$SCHEMA_PYTHON" "$SCHEMA_REGRESSION" \
    --repo "$LAB_ROOT" \
    --evidence-root "$LOG_ROOT" \
    --require-run "$HISTORICAL_STEP05_RUN" \
    --require-run "$SUPERSEDED_STEP05_RUN"
}

preview() {
  cat <<EOF
Gate 0.5 Step 05 preview

This step adds no Drupal route and no framework behavior.

It will:
  - audit Steps 01 through 04
  - exercise all four shared operations in one reset-bounded path
  - prove read-only and recommendation-only mutation boundaries
  - restore the exact seeded-clean baseline
  - generate a hash-addressed shared substrate freeze manifest
  - validate retained success envelopes for all four operations against the
    Draft 2020-12 tool-result schema using locked jsonschema 4.26.0
  - require get_image_context to validate with image-context fields directly under data
  - mark Gate 0.5 complete at the certified shared-substrate handoff
  - keep Drupal AI, LangGraph, and CrewAI explicitly uncertified
  - hand off next to gate-1-step01-drupal-ai-batch-contract-v1.0.0
EOF
}

capture_route_matrix() {
  local output="$1"
  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:eval '
      $provider = \Drupal::service("router.route_provider");
      $definitions = [
        "find_images_needing_review" => [
          "name" => "agentic_harness_tools.find_images_needing_review",
          "path" => "/api/agentic-harness/v1/images-needing-review",
          "methods" => ["GET"],
          "permission" => "use agentic harness discovery tools",
        ],
        "get_image_context" => [
          "name" => "agentic_harness_tools.get_image_context",
          "path" => "/api/agentic-harness/v1/image-context",
          "methods" => ["POST"],
          "permission" => "use agentic harness discovery tools",
        ],
        "submit_recommendation" => [
          "name" => "agentic_harness_tools.submit_recommendation",
          "path" => "/api/agentic-harness/v1/recommendations",
          "methods" => ["POST"],
          "permission" => "create alt_text_suggestion content",
        ],
        "get_recommendation_status" => [
          "name" => "agentic_harness_tools.get_recommendation_status",
          "path" => "/api/agentic-harness/v1/recommendations/{recommendation_id}/status",
          "methods" => ["GET"],
          "permission" => "use agentic harness discovery tools",
        ],
      ];

      $routes = [];
      foreach ($definitions as $tool => $expected) {
        $route = $provider->getRouteByName($expected["name"]);
        if (
          $route->getPath() !== $expected["path"]
          || $route->getMethods() !== $expected["methods"]
          || $route->getRequirement("_permission") !== $expected["permission"]
          || $route->getOption("_auth") !== ["basic_auth"]
          || $route->getOption("no_cache") !== TRUE
        ) {
          throw new \RuntimeException("Route matrix mismatch for " . $tool);
        }
        $routes[$tool] = [
          "path" => $route->getPath(),
          "methods" => $route->getMethods(),
          "permission" => $route->getRequirement("_permission"),
        ];
      }

      foreach ([
        "agentic_harness_tools.image_review_finder",
        "agentic_harness_tools.image_context_provider",
        "agentic_harness_tools.recommendation_validator",
        "agentic_harness_tools.recommendation_submitter",
        "agentic_harness_tools.recommendation_status_provider",
      ] as $service_id) {
        \Drupal::service($service_id);
      }

      $user_storage = \Drupal::entityTypeManager()->getStorage("user");
      $agent_matches = $user_storage->loadByProperties(["name" => "agent_bot"]);
      $editor_matches = $user_storage->loadByProperties(["name" => "editor_dana"]);
      $agent = $agent_matches === [] ? NULL : reset($agent_matches);
      $editor = $editor_matches === [] ? NULL : reset($editor_matches);
      if (
        !$agent instanceof \Drupal\user\UserInterface
        || !$editor instanceof \Drupal\user\UserInterface
        || !$agent->hasPermission("use agentic harness discovery tools")
        || !$agent->hasPermission("create alt_text_suggestion content")
        || $editor->hasPermission("use agentic harness discovery tools")
        || $editor->hasPermission("create alt_text_suggestion content")
        || !$editor->hasPermission("edit any alt_text_suggestion content")
      ) {
        throw new \RuntimeException("Principal permission matrix failed.");
      }

      print json_encode([
        "status" => "pass",
        "routes" => $routes,
        "agent_bot_principals" => TRUE,
        "editor_dana_review_only" => TRUE,
        "basic_auth_only" => TRUE,
        "all_routes_no_cache" => TRUE,
      ], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
    '
  ) > "$output"
}

capture_active_config() {
  local output="$1"
  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:script scripts/gate05-step05-config.php -- snapshot
  ) > "$output"
}

setup() {
  check_prerequisites
  info "Confirming the complete retained Gate 0.5 substrate lineage..."
  check_prior_evidence

  info "Validating all retained Step 05 success envelopes against the frozen schemas..."
  audit_retained_success_schemas

  info "Starting DDEV and rebuilding Drupal's container..."
  (
    cd "$DRUPAL_ROOT"
    ddev start -y
    ddev php -l web/modules/custom/agentic_harness_tools/src/Controller/ToolController.php
    ddev php -l web/modules/custom/agentic_harness_tools/src/Service/ImageReviewFinder.php
    ddev php -l web/modules/custom/agentic_harness_tools/src/Service/ImageContextProvider.php
    ddev php -l web/modules/custom/agentic_harness_tools/src/Service/RecommendationValidator.php
    ddev php -l web/modules/custom/agentic_harness_tools/src/Service/RecommendationSubmitter.php
    ddev php -l web/modules/custom/agentic_harness_tools/src/Service/RecommendationStatusProvider.php
    ddev php -l scripts/gate05-step05-config.php
    ddev drush cr
  )

  local temp_matrix
  temp_matrix="$(mktemp)"
  capture_route_matrix "$temp_matrix"
  cat "$temp_matrix"
  rm -f "$temp_matrix"

  local temp_config
  temp_config="$(mktemp)"
  capture_active_config "$temp_config"
  cat "$temp_config"
  rm -f "$temp_config"

  ok "Gate 0.5 Step 05 setup passed."
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
    "controlled_preflight": True,
    "shared_substrate_certification": True,
    "gate_0_5_complete": True,
    "framework_execution_claimed": False,
    "model_call_performed": False,
    "openai_api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
    "openai_candidate_model_present": bool(os.environ.get("OPENAI_CANDIDATE_MODEL")),
    "crewai_candidate_model_present": bool(os.environ.get("CREWAI_CANDIDATE_MODEL")),
}
json.dump(value, open(output, "w", encoding="utf-8"), indent=2, sort_keys=True)
open(output, "a", encoding="utf-8").write("\n")
PY
}

sanitize_context() {
  local raw="$1" sanitized="$2" runtime="$3"
  python3 - "$raw" "$sanitized" "$runtime" <<'PY'
import base64, hashlib, json, sys
raw_path, sanitized_path, runtime_path = sys.argv[1:]
value = json.load(open(raw_path, encoding="utf-8"))
data = value.get("data")
if not isinstance(data, dict):
    raise SystemExit("Context response lacks data.")
image = data.get("image")
representation = image.get("representation") if isinstance(image, dict) else None
if not isinstance(representation, dict) or representation.get("kind") != "data_url":
    raise SystemExit("Context response lacks the approved data_url representation.")
encoded = representation.get("value")
if not isinstance(encoded, str) or ";base64," not in encoded:
    raise SystemExit("Context response contains an invalid data URL.")
header, payload = encoded.split(";base64,", 1)
if not header.startswith("data:image/"):
    raise SystemExit("Context response is not an image data URL.")
decoded = base64.b64decode(payload, validate=True)
digest = hashlib.sha256(decoded).hexdigest()
if digest != image.get("sha256"):
    raise SystemExit("Decoded context image hash does not match metadata.")
if len(decoded) != image.get("byte_length"):
    raise SystemExit("Decoded context image length does not match metadata.")

representation["value"] = "<runtime-only-data-url>"
json.dump(value, open(sanitized_path, "w", encoding="utf-8"), indent=2, sort_keys=True)
open(sanitized_path, "a", encoding="utf-8").write("\n")

runtime = {
    "status": "pass",
    "representation_kind": "data_url",
    "representation_value_retained": False,
    "raw_image_bytes_retained": False,
    "decoded_byte_length": len(decoded),
    "image_sha256": digest,
    "context_evidence_hash": data.get("evidence_hash"),
}
json.dump(runtime, open(runtime_path, "w", encoding="utf-8"), indent=2, sort_keys=True)
open(runtime_path, "a", encoding="utf-8").write("\n")
PY
}

build_submission() {
  local target="$1" context="$2" run_id="$3" output="$4"
  python3 - "$target" "$context" "$run_id" "$output" <<'PY'
import json, sys
target_path, context_path, run_id, output = sys.argv[1:]
target = json.load(open(target_path, encoding="utf-8"))
context = json.load(open(context_path, encoding="utf-8"))
value = {
    "schema_version": 1,
    "target": target,
    "proposed_alt_text": (
        "A blue geometric illustration accompanying the seeded Article 01 content."
    ),
    "source_framework": "drupal_ai",
    "run_id": run_id,
    "evidence_hash": context["data"]["evidence_hash"],
    "validator_version": "gate05-validator-1.0.0",
}
json.dump(value, open(output, "w", encoding="utf-8"), indent=2, sort_keys=True)
open(output, "a", encoding="utf-8").write("\n")
PY
}

run_step05() {
  check_prerequisites
  unset OPENAI_API_KEY OPENAI_CANDIDATE_MODEL CREWAI_CANDIDATE_MODEL

  local run_id="gate05-step05-$(date -u +'%Y%m%dT%H%M%SZ')-$$"
  local run_rel="evidence/gates/gate-0.5/substrate-certification/$run_id"
  local run_dir="$LOG_ROOT/$run_id"
  mkdir -p "$run_dir"
  printf '%s\n' "$run_rel" > "$LAST_RUN_FILE"

  setup > >(tee "$run_dir/setup.log") 2>&1

  TEMP_DIR="$(mktemp -d)"
  chmod 700 "$TEMP_DIR"

  write_environment "$run_dir/environment.json" "$run_id"
  capture_route_matrix "$run_dir/route-matrix.json"

  info "Restoring seeded-clean before the four-operation certification path..."
  RESET_REQUIRED=1
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
  capture_active_config "$run_dir/active-config.json"

  local site_url agent_password
  site_url="$(resolve_site_url)"
  agent_password="$(latest_secret agent_bot)"
  [[ -n "$agent_password" ]] || fail "agent_bot credential is missing."
  GATE05_AGENT_PASSWORD="$agent_password"

  info "1/4 Calling find_images_needing_review()..."
  GATE05_AGENT_PASSWORD="$agent_password" \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" find-images \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env GATE05_AGENT_PASSWORD \
      --correlation-id "$run_id-find" \
      --insecure-local \
      > "$run_dir/find-response.json" \
      2> "$run_dir/find-client.log"

  python3 - "$run_dir/find-response.json" "$run_dir/target-1.json" <<'PY'
import json, sys
source, output = sys.argv[1:]
value = json.load(open(source, encoding="utf-8"))
targets = value["data"]["targets"]
json.dump(targets[0], open(output, "w", encoding="utf-8"), indent=2, sort_keys=True)
open(output, "a", encoding="utf-8").write("\n")
PY

  info "2/4 Calling get_image_context(target) with runtime-only image bytes..."
  GATE05_AGENT_PASSWORD="$agent_password" \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" get-image-context \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env GATE05_AGENT_PASSWORD \
      --correlation-id "$run_id-context" \
      --target-file "$run_dir/target-1.json" \
      --insecure-local \
      > "$TEMP_DIR/context-raw.json" \
      2> "$run_dir/context-client.log"

  sanitize_context \
    "$TEMP_DIR/context-raw.json" \
    "$run_dir/context-sanitized.json" \
    "$run_dir/context-runtime-verification.json"
  rm -f "$TEMP_DIR/context-raw.json"

  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:script scripts/gate05-step04.php -- snapshot
  ) > "$run_dir/source-after-reads.json"

  local submission_run_id
  submission_run_id="drupal_ai-$(date -u +'%Y%m%dT%H%M%SZ')-$(python3 - <<'PY'
import secrets
print(secrets.token_hex(3))
PY
)"
  build_submission \
    "$run_dir/target-1.json" \
    "$run_dir/context-sanitized.json" \
    "$submission_run_id" \
    "$run_dir/submission-request.json"

  info "3/4 Calling submit_recommendation() and its exact replay..."
  GATE05_AGENT_PASSWORD="$agent_password" \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" submit-recommendation \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env GATE05_AGENT_PASSWORD \
      --correlation-id "$run_id-submit" \
      --recommendation-file "$run_dir/submission-request.json" \
      --insecure-local \
      > "$run_dir/submit-response.json" \
      2> "$run_dir/submit-client.log"

  GATE05_AGENT_PASSWORD="$agent_password" \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" submit-recommendation \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env GATE05_AGENT_PASSWORD \
      --correlation-id "$run_id-replay" \
      --recommendation-file "$run_dir/submission-request.json" \
      --insecure-local \
      > "$run_dir/submit-replay-response.json" \
      2> "$run_dir/replay-client.log"

  local recommendation_id recommendation_uuid
  readarray -t recommendation_values < <(
    python3 - "$run_dir/submit-response.json" <<'PY'
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))["data"]
print(value["node_id"])
print(value["uuid"])
PY
  )
  recommendation_id="${recommendation_values[0]}"
  recommendation_uuid="${recommendation_values[1]}"

  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:script scripts/gate05-step04.php -- inspect "$recommendation_id"
  ) > "$run_dir/recommendation-inspection.json"
  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:script scripts/gate05-step04.php -- snapshot
  ) > "$run_dir/source-after-submit.json"

  info "4/4 Calling get_recommendation_status() by UUID, node ID, and repeat..."
  GATE05_AGENT_PASSWORD="$agent_password" \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" get-recommendation-status \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env GATE05_AGENT_PASSWORD \
      --correlation-id "$run_id-status-uuid" \
      --recommendation-id "$recommendation_uuid" \
      --insecure-local \
      > "$run_dir/status-uuid.json" \
      2> "$run_dir/status-client.log"

  GATE05_AGENT_PASSWORD="$agent_password" \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" get-recommendation-status \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env GATE05_AGENT_PASSWORD \
      --correlation-id "$run_id-status-nid" \
      --recommendation-id "$recommendation_id" \
      --insecure-local \
      > "$run_dir/status-nid.json" \
      2> "$run_dir/status-nid-client.log"

  GATE05_AGENT_PASSWORD="$agent_password" \
    python3 "$LAB_ROOT/shared/drupal_client/client.py" get-recommendation-status \
      --base-url "$site_url" \
      --username agent_bot \
      --password-env GATE05_AGENT_PASSWORD \
      --correlation-id "$run_id-status-repeat" \
      --recommendation-id "$recommendation_uuid" \
      --insecure-local \
      > "$run_dir/status-repeat.json" \
      2> "$run_dir/status-repeat-client.log"

  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:script scripts/gate05-step04.php -- snapshot
  ) > "$run_dir/source-after-status.json"

  info "Restoring the exact seeded-clean baseline..."
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
  RESET_COMPLETED=1

  info "Evaluating the complete substrate path and generating the freeze manifest..."
  python3 "$LAB_ROOT/scripts/gate05_step05_evidence.py" evaluate \
    --repo "$LAB_ROOT" \
    --run-dir "$run_dir"

  printf '%s\n' "$run_rel" > "$LATEST_FILE"

  info "Auditing retained Step 05 evidence and the frozen file hashes..."
  capture_active_config "$TEMP_DIR/active-config-audit.json"
  python3 "$LAB_ROOT/scripts/gate05_step05_evidence.py" audit \
    --repo "$LAB_ROOT" \
    --run-dir "$run_dir" \
    --active-config "$TEMP_DIR/active-config-audit.json"

  info "Revalidating all retained Step 05 success envelopes, including this run..."
  audit_retained_success_schemas

  pass "Gate 0.5 Step 05 shared substrate certification passed."
  pass "Evidence: $run_rel"
  pass "Freeze: shared/contracts/GATE05-SUBSTRATE-FREEZE.json"
  printf '\nGate 0.5 is complete at the certified shared-substrate handoff.\n'
  printf 'Next package: gate-1-step01-drupal-ai-batch-contract-v1.0.0\n'
  printf 'Inspect retained evidence and do not commit until approved.\n'
}

resolve_last_run() {
  [[ -s "$LAST_RUN_FILE" ]] || fail "No Step 05 last-run pointer exists."
  local relative
  relative="$(tr -d '\r\n' < "$LAST_RUN_FILE")"
  [[ "$relative" =~ ^evidence/gates/gate-0\.5/substrate-certification/gate05-step05-[A-Za-z0-9._-]+$ ]] || \
    fail "Unexpected Step 05 last-run pointer: $relative"
  [[ -d "$LAB_ROOT/$relative" ]] || fail "Step 05 last-run evidence directory is missing."
  printf '%s' "$relative"
}

resume_step05() {
  check_prerequisites
  unset OPENAI_API_KEY OPENAI_CANDIDATE_MODEL CREWAI_CANDIDATE_MODEL

  local run_rel run_dir
  run_rel="$(resolve_last_run)"
  run_dir="$LAB_ROOT/$run_rel"

  if [[ -f "$run_dir/summary.json" ]]; then
    fail "The last Step 05 run already has a summary. Use audit instead of resume."
  fi

  info "Reopening the completed Step 05 runtime evidence after evaluator correction..."
  setup > >(tee "$run_dir/resume-setup.log") 2>&1

  TEMP_DIR="$(mktemp -d)"
  chmod 700 "$TEMP_DIR"

  info "Confirming current Drupal state still matches the retained final seeded-clean snapshot..."
  (
    cd "$DRUPAL_ROOT"
    ddev drush --quiet php:script scripts/gate05-step04.php -- snapshot
  ) > "$run_dir/resume-current-clean.json"

  python3 - \
    "$run_dir/source-final-clean.json" \
    "$run_dir/resume-current-clean.json" <<'PY'
import json, sys
expected = json.load(open(sys.argv[1], encoding="utf-8"))
current = json.load(open(sys.argv[2], encoding="utf-8"))
if expected != current:
    raise SystemExit(
        "[ERROR] Current Drupal state differs from the failed run's "
        "retained final clean snapshot."
    )
if current.get("suggestion_count") != 0:
    raise SystemExit("[ERROR] Current Drupal state is not zero-suggestion clean.")
print(json.dumps({
    "status": "pass",
    "current_state_matches_retained_final_clean": True,
    "suggestion_count": 0,
    "article_source_sha256": current.get("article_source_sha256"),
}, indent=2, sort_keys=True))
PY

  capture_active_config "$run_dir/resume-active-config.json"

  info "Running the corrected evaluator against the completed four-operation evidence..."
  python3 "$LAB_ROOT/scripts/gate05_step05_evidence.py" evaluate \
    --repo "$LAB_ROOT" \
    --run-dir "$run_dir"

  printf '%s\n' "$run_rel" > "$LATEST_FILE"

  info "Auditing the resumed Step 05 evidence and current active configuration..."
  python3 "$LAB_ROOT/scripts/gate05_step05_evidence.py" audit \
    --repo "$LAB_ROOT" \
    --run-dir "$run_dir" \
    --active-config "$run_dir/resume-active-config.json"

  info "Revalidating all retained Step 05 success envelopes, including this run..."
  audit_retained_success_schemas

  pass "Gate 0.5 Step 05 shared substrate certification passed."
  pass "Evidence: $run_rel"
  pass "Freeze: shared/contracts/GATE05-SUBSTRATE-FREEZE.json"
  printf '\nGate 0.5 is complete at the certified shared-substrate handoff.\n'
  printf 'Next package: gate-1-step01-drupal-ai-batch-contract-v1.0.0\n'
  printf 'Inspect retained evidence and do not commit until approved.\n'
}

resolve_latest_run() {
  [[ -s "$LATEST_FILE" ]] || fail "No passing Gate 0.5 Step 05 run is recorded."
  local relative
  relative="$(tr -d '\r\n' < "$LATEST_FILE")"
  [[ "$relative" =~ ^evidence/gates/gate-0\.5/substrate-certification/gate05-step05-[A-Za-z0-9._-]+$ ]] || \
    fail "Unexpected Step 05 latest pointer: $relative"
  [[ -d "$LAB_ROOT/$relative" ]] || fail "Step 05 evidence directory is missing."
  printf '%s' "$relative"
}

audit_latest() {
  check_prerequisites
  check_prior_evidence
  local relative audit_config
  relative="$(resolve_latest_run)"
  audit_config="$(mktemp)"
  capture_active_config "$audit_config"
  python3 "$LAB_ROOT/scripts/gate05_step05_evidence.py" audit \
    --repo "$LAB_ROOT" \
    --run-dir "$LAB_ROOT/$relative" \
    --active-config "$audit_config"
  audit_retained_success_schemas
  rm -f "$audit_config"
  pass "Gate 0.5 Step 05 audit passed."
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
  run) run_step05 ;;
  resume) resume_step05 ;;
  audit) audit_latest ;;
  status) status_latest ;;
  help|-h|--help) usage ;;
  *) usage; fail "Unknown mode: $MODE" ;;
esac
