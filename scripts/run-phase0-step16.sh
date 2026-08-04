#!/usr/bin/env bash
set -Eeuo pipefail

STEP16_SCRIPT_VERSION="1.0.1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATES_DIR="$SCRIPT_DIR/phase0-step16-templates"
FINALIZE_TEMPLATES="$SCRIPT_DIR/phase0-step16-finalize-templates"
EVIDENCE_HELPER="$SCRIPT_DIR/step16_evidence.py"
AUDIT_HELPER="$SCRIPT_DIR/step16_audit.py"
FINALIZE_HELPER="$SCRIPT_DIR/step16_finalize.py"
EVIDENCE_ROOT="$PROJECT_ROOT/evidence/logs/preflight/vision"
LATEST_FILE="$EVIDENCE_ROOT/STEP16-LATEST.txt"
LAST_RUN_FILE="$EVIDENCE_ROOT/STEP16-LAST-RUN.txt"
RUNTIME_HOST="$PROJECT_ROOT/drupal/.phase0-step16-runtime"
RUNTIME_CONTAINER="/var/www/html/.phase0-step16-runtime"
MODEL_ID="gpt-4.1-mini-2025-04-14"

log_info() { printf '[INFO] %s\n' "$*"; }
log_ok() { printf '[OK] %s\n' "$*"; }
log_warn() { printf '[WARNING] %s\n' "$*" >&2; }
fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'USAGE'
Phase 0 Step 16 — image-plus-page-context capability spike

Usage:
  bash scripts/run-phase0-step16.sh preview
  bash scripts/run-phase0-step16.sh setup
  bash scripts/run-phase0-step16.sh inspect
  bash scripts/run-phase0-step16.sh extract-fixture
  bash scripts/run-phase0-step16.sh run
  bash scripts/run-phase0-step16.sh run-interactive
  bash scripts/run-phase0-step16.sh audit
  bash scripts/run-phase0-step16.sh finalize confirm
  bash scripts/run-phase0-step16.sh record-fallback two-stage confirm
  bash scripts/run-phase0-step16.sh status

The package does not implement Step 17, create recommendation records, alter Article fields, stage
Git files, commit, or push. The model is frozen only by finalize after a passing 9/9 direct run.
USAGE
}

assert_package() {
  [[ -d "$PROJECT_ROOT/drupal" ]] || fail "Expected project root with drupal/: $PROJECT_ROOT"
  [[ -d "$TEMPLATES_DIR" && -d "$FINALIZE_TEMPLATES" ]] || fail "Step 16 templates are missing. Re-run install-step16.sh."
  [[ -x "$EVIDENCE_HELPER" && -x "$AUDIT_HELPER" && -x "$FINALIZE_HELPER" ]] || fail "Step 16 helpers are missing or not executable."
  command -v python3 >/dev/null || fail "python3 is required"
  command -v sha256sum >/dev/null || fail "sha256sum is required"
}

assert_step15() {
  [[ -x "$SCRIPT_DIR/run-phase0-step15.sh" ]] || fail "Step 15 runner is missing"
  bash "$SCRIPT_DIR/run-phase0-step15.sh" audit >/dev/null
  log_ok "Step 15 finalized preflight audit passed."
}

assert_step10() {
  [[ -x "$PROJECT_ROOT/drupal/scripts/run-phase0-step10.sh" ]] || fail "Step 10 runner is missing"
  (cd "$PROJECT_ROOT/drupal" && bash scripts/run-phase0-step10.sh audit >/dev/null)
  log_ok "Drupal matches the seeded-clean baseline."
}

managed_files() {
  cat <<'FILES'
drupal/scripts/phase0-step16.php
langchain/preflight/step16_capability.py
crewai/preflight/step16_capability.py
shared/schemas/vision-spike-output.schema.json
shared/prompts/STEP16_VISION_PROMPT.md
FILES
}

template_for() {
  printf '%s/%s\n' "$TEMPLATES_DIR" "$1"
}

same_file() {
  [[ -f "$1" && -f "$2" ]] || return 1
  cmp -s "$1" "$2"
}

ensure_gitignore() {
  local file="$PROJECT_ROOT/.gitignore"
  local marker="# BEGIN PHASE0 STEP16 RUNTIME"
  if grep -Fq "$marker" "$file"; then
    log_info "Step 16 .gitignore block already exists."
    return
  fi
  cat >> "$file" <<'BLOCK'

# BEGIN PHASE0 STEP16 RUNTIME
/drupal/.phase0-step16-runtime/
/langchain/.phase0-step16-runtime/
/crewai/.phase0-step16-runtime/
/.phase0-step16-backups/
/.phase0-step16-package-backups/
# END PHASE0 STEP16 RUNTIME
BLOCK
  log_ok "Added Step 16 runtime and backup exclusions to .gitignore."
}

preview() {
  assert_package
  printf 'Phase 0 Step 16 runner version: %s\n\n' "$STEP16_SCRIPT_VERSION"
  cat <<TEXT
This package will use the already-pinned Step 15 environments and Drupal modules. It adds no new
Python or Composer dependency. It installs one Drupal helper, two Python capability scripts, one
strict JSON Schema, one controlled prompt, and the Step 16 audit/finalize workflow.

Required passing tests:
  INSPECT-DR-001  Drupal AI/provider APIs and deterministic FunctionCall probe are present
  FIXTURE-001     the first deterministic Step 9 target is extracted and hashed
  VISION-DR-001   Drupal AI receives image + page context and returns strict structured output
  TOOL-DR-001     Drupal AI exposes the deterministic non-mutating tool path
  VISION-LG-001   LangChain receives the same bytes/context and returns strict structured output
  TOOL-LG-001     LangChain exposes the deterministic non-mutating tool path
  VISION-CR-001   CrewAI receives the same bytes/context and returns structured output
  TOOL-CR-001     CrewAI exposes the deterministic non-mutating tool path
  MUTATION-001    Drupal Article state and suggestion count are unchanged

Candidate model: $MODEL_ID
Image control: identical synthetic PNG bytes; the full Base64 value is never retained.
TEXT
  printf '\nFile preview:\n'
  local rel source target state
  while IFS= read -r rel; do
    source="$(template_for "$rel")"; target="$PROJECT_ROOT/$rel"
    if [[ ! -e "$target" ]]; then state="CREATE";
    elif same_file "$source" "$target"; then state="KEEP";
    else state="CONFLICT"; fi
    printf '  %-8s %s\n' "$state" "$rel"
  done < <(managed_files)
}

setup() {
  assert_package
  assert_step15
  local rel source target
  while IFS= read -r rel; do
    source="$(template_for "$rel")"; target="$PROJECT_ROOT/$rel"
    [[ -f "$source" ]] || fail "Missing package template: $source"
    if [[ -e "$target" ]] && ! same_file "$source" "$target"; then
      fail "Refusing to overwrite unexpected existing file: $rel"
    fi
  done < <(managed_files)
  while IFS= read -r rel; do
    source="$(template_for "$rel")"; target="$PROJECT_ROOT/$rel"
    mkdir -p "$(dirname "$target")"
    if [[ -e "$target" ]]; then
      log_info "Preserved matching file: $rel"
    else
      cp "$source" "$target"
      chmod 0644 "$target"
      case "$target" in *.py|*.php) chmod 0755 "$target" ;; esac
      log_ok "Created: $rel"
    fi
  done < <(managed_files)
  ensure_gitignore
  rm -f "$PROJECT_ROOT/shared/schemas/.gitkeep" "$PROJECT_ROOT/shared/prompts/.gitkeep"
  mkdir -p "$EVIDENCE_ROOT"
  log_ok "Step 16 capability files installed. No dependency upgrade was performed."
  printf '\nNext: bash scripts/run-phase0-step16.sh inspect\n'
}

assert_setup() {
  assert_package
  local rel
  while IFS= read -r rel; do
    [[ -s "$PROJECT_ROOT/$rel" ]] || fail "Missing Step 16 file: $rel. Run setup."
  done < <(managed_files)
  [[ -x "$PROJECT_ROOT/langchain/.venv/bin/python" ]] || fail "LangChain environment is missing; rerun Step 15 setup"
  [[ -x "$PROJECT_ROOT/crewai/.venv/bin/python" ]] || fail "CrewAI environment is missing; rerun Step 15 setup"
}

sanitize_log() {
  python3 "$EVIDENCE_HELPER" sanitize "$1"
}

extract_log_json() {
  python3 "$EVIDENCE_HELPER" extract "$1" "$2"
}

inspect() {
  assert_setup
  assert_step15
  local tmp
  tmp="$(mktemp)"
  set +e
  (cd "$PROJECT_ROOT/drupal" && ddev drush --quiet php:script scripts/phase0-step16.php -- inspect "$RUNTIME_CONTAINER" "$MODEL_ID") >"$tmp" 2>&1
  local code=$?
  set -e
  sanitize_log "$tmp"
  cat "$tmp"
  [[ $code -eq 0 ]] || fail "Drupal Step 16 API inspection failed"
  rm -f "$tmp"
}

extract_fixture() {
  assert_setup
  assert_step10
  rm -rf "$RUNTIME_HOST"
  mkdir -p "$RUNTIME_HOST"
  chmod 0700 "$RUNTIME_HOST"
  local tmp
  tmp="$(mktemp)"
  set +e
  (cd "$PROJECT_ROOT/drupal" && ddev drush --quiet php:script scripts/phase0-step16.php -- extract "$RUNTIME_CONTAINER" "$MODEL_ID") >"$tmp" 2>&1
  local code=$?
  set -e
  sanitize_log "$tmp"
  cat "$tmp"
  [[ $code -eq 0 ]] || fail "Fixture extraction failed"
  if [[ ! -s "$RUNTIME_HOST/fixture.json" || ! -s "$RUNTIME_HOST/fixture.png" ]]; then
    local legacy_runtime="$PROJECT_ROOT/drupal/web/.phase0-step16-runtime"
    if [[ -s "$legacy_runtime/fixture.json" && -s "$legacy_runtime/fixture.png" ]]; then
      fail "Runtime fixture files were written under the Drupal docroot instead of the DDEV project root. Apply the Step 16 runtime-path hotfix."
    fi
    fail "Runtime fixture files were not created at $RUNTIME_HOST"
  fi
  local expected actual
  expected="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["image_sha256"])' "$RUNTIME_HOST/fixture.json")"
  actual="$(sha256sum "$RUNTIME_HOST/fixture.png" | awk '{print $1}')"
  [[ "$expected" == "$actual" ]] || fail "Runtime fixture image hash mismatch"
  rm -f "$tmp"
  log_ok "Deterministic Step 16 fixture extracted to ignored runtime storage."
}

prepare_run_dir() {
  local run_id="step16-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  local run_dir="$EVIDENCE_ROOT/$run_id"
  mkdir -p "$run_dir"
  printf '%s\n%s\n' "$run_id" "$run_dir"
}

record_result() {
  local results="$1" test_id="$2" status="$3" code="$4" evidence="$5"
  printf '%s\t%s\t%s\t%s\n' "$test_id" "$status" "$code" "$evidence" >> "$results"
}

run_logged_test() {
  local results="$1" test_id="$2" log_file="$3" json_file="$4"
  shift 4
  local code status
  set +e
  "$@" >"$log_file" 2>&1
  code=$?
  set -e
  sanitize_log "$log_file"
  if [[ $code -eq 0 ]] && extract_log_json "$log_file" "$json_file"; then
    local recorded_status recorded_id
    recorded_status="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("status",""))' "$json_file")"
    recorded_id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("test_id",""))' "$json_file")"
    if [[ "$recorded_status" == "pass" && "$recorded_id" == "$test_id" ]]; then
      status="pass"
      log_ok "$test_id PASS"
    else
      status="fail"; code=1
      log_warn "$test_id returned unexpected JSON"
    fi
  else
    status="fail"
    log_warn "$test_id FAIL — inspect $log_file"
  fi
  record_result "$results" "$test_id" "$status" "$code" "$(basename "$json_file")"
}

run_drupal_mode() {
  local mode="$1"
  (cd "$PROJECT_ROOT/drupal" && ddev drush --quiet php:script scripts/phase0-step16.php -- "$mode" "$RUNTIME_CONTAINER" "$MODEL_ID")
}

run_langchain_mode() {
  local mode="$1"
  (
    cd "$PROJECT_ROOT/langchain"
    export OPENAI_API_KEY OPENAI_CANDIDATE_MODEL="$MODEL_ID"
    uv run --locked python preflight/step16_capability.py "$mode" \
      --fixture ../drupal/.phase0-step16-runtime/fixture.json \
      --image ../drupal/.phase0-step16-runtime/fixture.png
  )
}

run_crewai_mode() {
  local mode="$1"
  local adapter="${CREWAI_CANDIDATE_MODEL:-$MODEL_ID}"
  [[ "${adapter#openai/}" == "$MODEL_ID" ]] || fail "CREWAI_CANDIDATE_MODEL must identify $MODEL_ID"
  (
    cd "$PROJECT_ROOT/crewai"
    export OPENAI_API_KEY OPENAI_CANDIDATE_MODEL="$MODEL_ID" CREWAI_CANDIDATE_MODEL="$adapter"
    export CREWAI_DISABLE_TELEMETRY=true OTEL_SDK_DISABLED=true
    uv run --locked python preflight/step16_capability.py "$mode" \
      --fixture ../drupal/.phase0-step16-runtime/fixture.json \
      --image ../drupal/.phase0-step16-runtime/fixture.png
  )
}

collect_environment() {
  local output="$1" composer_json="$2"
  local ubuntu docker ddev php drupal_core drush
  ubuntu="$(lsb_release -ds 2>/dev/null || . /etc/os-release && printf '%s' "${PRETTY_NAME:-unknown}")"
  docker="$(docker version --format 'client={{.Client.Version}} server={{.Server.Version}}' 2>/dev/null || docker --version 2>/dev/null || printf 'unavailable')"
  ddev="$(ddev --version 2>/dev/null | sed 's/[[:space:]]*$//' || true)"
  php="$(cd "$PROJECT_ROOT/drupal" && ddev php -r 'echo PHP_VERSION;' 2>/dev/null || true)"
  drupal_core="$(cd "$PROJECT_ROOT/drupal" && ddev drush status --field=drupal-version 2>/dev/null || true)"
  drush="$(cd "$PROJECT_ROOT/drupal" && ddev drush --version 2>/dev/null | sed -E 's/^Drush Commandline Tool //' || true)"
  (cd "$PROJECT_ROOT/drupal" && ddev composer show --locked --format=json --no-ansi > "$composer_json")
  python3 - "$output" "$composer_json" "$ubuntu" "$docker" "$ddev" "$php" "$drupal_core" "$drush" <<'PY'
import json, sys
out, composer_path, ubuntu, docker, ddev, php, core, drush = sys.argv[1:]
data = json.load(open(composer_path, encoding='utf-8'))
versions = {}
for package in data.get('locked', data.get('installed', [])):
    name = package.get('name')
    if name:
        versions[name] = str(package.get('version', '')).lstrip('v')
result = {
    'ubuntu': ubuntu,
    'docker': docker,
    'ddev': ddev,
    'php': php,
    'drupal_core': core or versions.get('drupal/core', ''),
    'drupal_ai': versions.get('drupal/ai', ''),
    'drupal_ai_agents': versions.get('drupal/ai_agents', ''),
    'drupal_openai_provider': versions.get('drupal/ai_provider_openai', ''),
    'drush': drush or versions.get('drush/drush', ''),
    'openai_php_client': versions.get('openai-php/client', ''),
    'candidate_model': 'gpt-4.1-mini-2025-04-14',
}
required = ('ubuntu','docker','ddev','php','drupal_core','drupal_ai','drupal_ai_agents','drupal_openai_provider','drush')
missing = [key for key in required if not str(result.get(key, '')).strip()]
if missing:
    raise SystemExit('Could not capture required Step 16 versions: ' + ', '.join(missing))
with open(out, 'w', encoding='utf-8') as fh:
    json.dump(result, fh, indent=2, sort_keys=True)
    fh.write('\n')
PY
  rm -f "$composer_json"
}

run_full() {
  assert_setup
  assert_step15
  assert_step10
  [[ -n "${OPENAI_API_KEY:-}" ]] || fail "OPENAI_API_KEY is required. Use run-interactive to enter it without echo."
  if [[ -n "${OPENAI_CANDIDATE_MODEL:-}" && "$OPENAI_CANDIDATE_MODEL" != "$MODEL_ID" ]]; then
    fail "Step 16 is controlled to the Step 15 candidate: $MODEL_ID"
  fi
  export OPENAI_CANDIDATE_MODEL="$MODEL_ID"

  local info run_id run_dir results started finished summary_code tmp_composer
  mapfile -t info < <(prepare_run_dir)
  run_id="${info[0]}"; run_dir="${info[1]}"; results="$run_dir/results.tsv"
  : > "$results"
  printf '%s\n' "evidence/logs/preflight/vision/$run_id" > "$LAST_RUN_FILE"
  started="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  rm -rf "$RUNTIME_HOST"
  mkdir -p "$RUNTIME_HOST"
  chmod 0700 "$RUNTIME_HOST"

  run_logged_test "$results" INSPECT-DR-001 "$run_dir/INSPECT-DR-001.log" "$run_dir/INSPECT-DR-001.json" run_drupal_mode inspect

  local before_log after_log
  before_log="$run_dir/source-content-before.log"
  run_drupal_mode snapshot > "$before_log" 2>&1
  sanitize_log "$before_log"
  extract_log_json "$before_log" "$run_dir/source-content-before.json"

  run_logged_test "$results" FIXTURE-001 "$run_dir/FIXTURE-001.log" "$run_dir/FIXTURE-001.json" run_drupal_mode extract
  cp "$run_dir/FIXTURE-001.json" "$run_dir/fixture.json"
  python3 - "$RUNTIME_HOST/fixture.json" "$run_dir/image-metadata.json" <<'PY'
import json, sys
fixture = json.load(open(sys.argv[1], encoding='utf-8'))
keep = {key: fixture[key] for key in ('filename','mime_type','width','height','image_byte_length','image_sha256','context_sha256','source_sha256')}
keep.update({'image_representation_candidate':'inline_png_base64_data_url','image_detail':'auto','encoded_value_retained':False})
json.dump(keep, open(sys.argv[2], 'w', encoding='utf-8'), indent=2, sort_keys=True)
open(sys.argv[2], 'a', encoding='utf-8').write('\n')
PY

  run_logged_test "$results" VISION-DR-001 "$run_dir/VISION-DR-001.log" "$run_dir/VISION-DR-001.json" run_drupal_mode vision
  run_logged_test "$results" TOOL-DR-001 "$run_dir/TOOL-DR-001.log" "$run_dir/TOOL-DR-001.json" run_drupal_mode tool
  run_logged_test "$results" VISION-LG-001 "$run_dir/VISION-LG-001.log" "$run_dir/VISION-LG-001.json" run_langchain_mode vision
  run_logged_test "$results" TOOL-LG-001 "$run_dir/TOOL-LG-001.log" "$run_dir/TOOL-LG-001.json" run_langchain_mode tool
  run_logged_test "$results" VISION-CR-001 "$run_dir/VISION-CR-001.log" "$run_dir/VISION-CR-001.json" run_crewai_mode vision
  run_logged_test "$results" TOOL-CR-001 "$run_dir/TOOL-CR-001.log" "$run_dir/TOOL-CR-001.json" run_crewai_mode tool

  after_log="$run_dir/source-content-after.log"
  run_drupal_mode snapshot > "$after_log" 2>&1
  sanitize_log "$after_log"
  extract_log_json "$after_log" "$run_dir/source-content-after.json"
  set +e
  python3 "$EVIDENCE_HELPER" mutation "$run_dir/source-content-before.json" "$run_dir/source-content-after.json" "$run_dir/MUTATION-001.json"
  local mutation_code=$?
  set -e
  if [[ $mutation_code -eq 0 ]]; then
    record_result "$results" MUTATION-001 pass 0 MUTATION-001.json
    log_ok "MUTATION-001 PASS"
  else
    record_result "$results" MUTATION-001 fail "$mutation_code" MUTATION-001.json
    log_warn "MUTATION-001 FAIL"
  fi

  tmp_composer="$(mktemp)"
  collect_environment "$run_dir/environment.json" "$tmp_composer"
  finished="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  set +e
  python3 "$EVIDENCE_HELPER" summary "$run_dir" "$run_id" "$started" "$finished"
  summary_code=$?
  set -e
  find "$run_dir" -type f -print0 | while IFS= read -r -d '' file; do sanitize_log "$file"; done

  if [[ $summary_code -eq 0 ]]; then
    printf '%s\n' "evidence/logs/preflight/vision/$run_id" > "$LATEST_FILE"
    log_ok "Step 16 direct capability spike passed 9/9."
    printf 'Evidence: %s\n' "$run_dir"
    printf '\nNext: bash scripts/run-phase0-step16.sh audit\n'
    printf 'Then: bash scripts/run-phase0-step16.sh finalize confirm\n'
  else
    log_warn "Step 16 direct capability spike did not pass. Evidence: $run_dir"
    printf '\nReview summary.md and failed logs. Do not freeze the model.\n'
    printf 'To document the runbook fallback decision: bash scripts/run-phase0-step16.sh record-fallback two-stage confirm\n'
    return 1
  fi
}

run_interactive() {
  assert_setup
  local entered_model
  if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    read -r -s -p "OpenAI API key (input hidden; not saved): " OPENAI_API_KEY
    printf '\n'
    export OPENAI_API_KEY
  fi
  read -r -p "Candidate OpenAI model ID [$MODEL_ID]: " entered_model
  entered_model="${entered_model:-$MODEL_ID}"
  [[ "$entered_model" == "$MODEL_ID" ]] || fail "Step 16 must use the Step 15 candidate: $MODEL_ID"
  export OPENAI_CANDIDATE_MODEL="$MODEL_ID"
  run_full
  unset OPENAI_API_KEY
}

run_audit() {
  assert_setup
  assert_step15
  python3 "$AUDIT_HELPER" "$PROJECT_ROOT"
}

finalize() {
  [[ "${1:-}" == "confirm" ]] || fail "Finalize requires: finalize confirm"
  run_audit
  local run_rel run_dir
  run_rel="$(cat "$LATEST_FILE")"
  run_dir="$PROJECT_ROOT/$run_rel"
  python3 "$FINALIZE_HELPER" "$PROJECT_ROOT" "$run_dir" "$TEMPLATES_DIR" "$FINALIZE_TEMPLATES"
  bash "$SCRIPT_DIR/run-phase0-step14.sh" audit
  bash "$SCRIPT_DIR/run-phase0-step15.sh" audit
  python3 "$AUDIT_HELPER" "$PROJECT_ROOT"
  log_ok "Step 16 finalized. Step 17 is next."
}

record_fallback() {
  [[ "${1:-}" == "two-stage" && "${2:-}" == "confirm" ]] || fail "Use: record-fallback two-stage confirm"
  [[ -f "$LAST_RUN_FILE" ]] || fail "No Step 16 run exists to support a fallback decision"
  local run_rel run_dir output
  run_rel="$(cat "$LAST_RUN_FILE")"; run_dir="$PROJECT_ROOT/$run_rel"
  output="$run_dir/fallback-selection.json"
  cat > "$output" <<EOF
{
  "status": "selected_not_yet_proven",
  "fallback": "two-stage",
  "stage_1": "image to structured image description",
  "stage_2": "image description plus page context to recommendation",
  "selected_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "source_run": "$run_rel",
  "model_frozen": false,
  "step16_complete": false,
  "note": "The direct spike did not pass all three paths. This selection follows the final runbook and must be implemented and tested consistently across all three pathways before Step 16 can be finalized."
}
EOF
  log_ok "Recorded the preferred two-stage fallback without marking Step 16 complete."
  printf 'Decision evidence: %s\n' "$output"
}

status() {
  assert_package
  printf 'Step 16 runner: %s\n' "$STEP16_SCRIPT_VERSION"
  printf 'Project root: %s\n' "$PROJECT_ROOT"
  printf 'Candidate model: %s\n' "$MODEL_ID"
  printf 'Latest passing evidence: %s\n' "$(cat "$LATEST_FILE" 2>/dev/null || printf 'none')"
  printf 'Last attempted run: %s\n' "$(cat "$LAST_RUN_FILE" 2>/dev/null || printf 'none')"
  if grep -Fq -- '- [x] Step 16 image-plus-page-context capability passes or a fallback is recorded.' "$PROJECT_ROOT/PLAN.md" 2>/dev/null; then
    printf 'Finalized: yes\nNext: Step 17\n'
  else
    printf 'Finalized: no\n'
  fi
}

mode="${1:-}"
case "$mode" in
  preview) preview ;;
  setup) setup ;;
  inspect) inspect ;;
  extract-fixture) extract_fixture ;;
  run) run_full ;;
  run-interactive) run_interactive ;;
  audit) run_audit ;;
  finalize) finalize "${2:-}" ;;
  record-fallback) record_fallback "${2:-}" "${3:-}" ;;
  status) status ;;
  -h|--help|help|"") usage ;;
  *) usage; fail "Unknown mode: $mode" ;;
esac
