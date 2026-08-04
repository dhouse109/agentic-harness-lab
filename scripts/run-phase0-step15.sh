#!/usr/bin/env bash
set -euo pipefail

STEP15_SCRIPT_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATES_DIR="$SCRIPT_DIR/phase0-step15-templates"
EVIDENCE_HELPER="$SCRIPT_DIR/step15_evidence.py"
AUDIT_HELPER="$SCRIPT_DIR/step15_audit.py"
FINALIZE_HELPER="$SCRIPT_DIR/step15_finalize.py"
EVIDENCE_ROOT="$PROJECT_ROOT/evidence/logs/preflight"
LATEST_FILE="$EVIDENCE_ROOT/STEP15-LATEST.txt"
LAST_RUN_FILE="$EVIDENCE_ROOT/STEP15-LAST-RUN.txt"
BACKUP_ROOT="$PROJECT_ROOT/.phase0-step15-backups"

log_info() { printf '[INFO] %s\n' "$*"; }
log_ok() { printf '[OK] %s\n' "$*"; }
log_warn() { printf '[WARNING] %s\n' "$*" >&2; }
fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'USAGE'
Phase 0 Step 15 — isolated Python environment preflight

Usage:
  bash scripts/run-phase0-step15.sh preview
  bash scripts/run-phase0-step15.sh setup
  bash scripts/run-phase0-step15.sh run-offline
  bash scripts/run-phase0-step15.sh run
  bash scripts/run-phase0-step15.sh run-interactive
  bash scripts/run-phase0-step15.sh audit
  bash scripts/run-phase0-step15.sh finalize confirm
  bash scripts/run-phase0-step15.sh status

Modes:
  preview          Show files, dependencies, tests, and user-supplied values without changing anything.
  setup            Install Python 3.12 and sync two separate uv environments with lockfiles.
  run-offline      Run the eight model-free checks; no API key is needed and no canonical run is recorded.
  run              Run all ten checks using OPENAI_API_KEY and OPENAI_CANDIDATE_MODEL from the environment.
  run-interactive  Prompt for the API key without echoing or saving it, then run all ten checks.
  audit            Verify lockfiles, separate Python projects, and the latest 10/10 sanitized evidence.
  finalize confirm Update VERSIONS.md, PLAN.md, and README.md after a passing audit.
  status           Print setup, evidence, and finalized-state status.

This script does not create agent implementations, freeze the model, stage Git files, commit, or push.
USAGE
}

assert_package() {
  [[ -d "$PROJECT_ROOT/drupal" ]] || fail "Expected repository root with drupal/: $PROJECT_ROOT"
  [[ -d "$TEMPLATES_DIR/langchain" && -d "$TEMPLATES_DIR/crewai" ]] || fail "Step 15 templates are missing. Re-run install-step15.sh."
  [[ -x "$EVIDENCE_HELPER" && -x "$AUDIT_HELPER" && -x "$FINALIZE_HELPER" ]] || fail "Step 15 helper scripts are missing or not executable."
  command -v python3 >/dev/null 2>&1 || fail "python3 is required to run package helpers."
}

assert_uv() {
  command -v uv >/dev/null 2>&1 || fail "uv is not installed or not on PATH. Complete Phase 0 Step 3 first."
}

assert_step14() {
  [[ -x "$SCRIPT_DIR/run-phase0-step14.sh" ]] || fail "Step 14 runner is missing."
  bash "$SCRIPT_DIR/run-phase0-step14.sh" audit >/dev/null
  log_ok "Frozen Step 14 contract audit passed."
}

canonical_sha() {
  sed 's/\r$//' "$1" | sha256sum | awk '{print $1}'
}

same_file() {
  [[ -f "$1" && -f "$2" ]] || return 1
  [[ "$(canonical_sha "$1")" == "$(canonical_sha "$2")" ]]
}

managed_project_files() {
  local project="$1"
  find "$TEMPLATES_DIR/$project" -type f -printf '%P\n' | sort
}

check_project_conflicts() {
  local project="$1" rel source target
  while IFS= read -r rel; do
    source="$TEMPLATES_DIR/$project/$rel"
    target="$PROJECT_ROOT/$project/$rel"
    if [[ -e "$target" ]] && ! same_file "$target" "$source"; then
      fail "Refusing to overwrite unexpected existing file: $project/$rel"
    fi
  done < <(managed_project_files "$project")
}

install_project_templates() {
  local project="$1" rel source target
  mkdir -p "$PROJECT_ROOT/$project"
  while IFS= read -r rel; do
    source="$TEMPLATES_DIR/$project/$rel"
    target="$PROJECT_ROOT/$project/$rel"
    mkdir -p "$(dirname "$target")"
    if [[ -e "$target" ]]; then
      log_info "Preserved matching file: $project/$rel"
    else
      cp "$source" "$target"
      sed -i 's/\r$//' "$target"
      log_ok "Created: $project/$rel"
    fi
  done < <(managed_project_files "$project")
  rm -f "$PROJECT_ROOT/$project/.gitkeep"
}

ensure_gitignore() {
  local file="$PROJECT_ROOT/.gitignore"
  local start="# BEGIN PHASE0 STEP15 PYTHON RUNTIME"
  if grep -Fq "$start" "$file" 2>/dev/null; then
    log_info "Step 15 .gitignore block already exists."
    return
  fi
  cat >> "$file" <<'BLOCK'

# BEGIN PHASE0 STEP15 PYTHON RUNTIME
/langchain/.venv/
/langchain/.preflight-state/
/crewai/.venv/
/crewai/.preflight-state/
# END PHASE0 STEP15 PYTHON RUNTIME
BLOCK
  log_ok "Appended Step 15 runtime exclusions to .gitignore."
}

print_preview() {
  assert_package
  log_info "Phase 0 Step 15 runner version: $STEP15_SCRIPT_VERSION"
  cat <<'TEXT'

Step 15 will create two independent Python 3.12 uv projects:

  langchain/  → LangChain, langchain-openai, LangGraph, SQLite checkpointer
  crewai/     → CrewAI and CrewAI Tools

Setup downloads or selects Python 3.12, resolves dependencies, creates separate .venv directories,
and writes one uv.lock file per project.

Ten checks are required:

  PY-LG-001       LangChain environment uses Python 3.12
  PY-LG-002       LangChain/LangGraph/checkpointer imports succeed
  LG-GRAPH-001    deterministic two-node LangGraph runs
  LG-SQLITE-001   process one writes fixed-thread checkpoint state
  LG-SQLITE-002   process two reloads the fixed-thread state
  LG-MODEL-001    candidate model responds through langchain-openai
  PY-CR-001       CrewAI environment uses Python 3.12
  PY-CR-002       CrewAI and CrewAI Tools imports succeed
  CR-FLOW-001     deterministic two-step CrewAI Flow runs
  CR-MODEL-001    same candidate model responds through CrewAI LLM

You supply only:

  OPENAI_API_KEY          secret; held in process memory and never retained
  OPENAI_CANDIDATE_MODEL  candidate identifier; recorded as not frozen

Optional adapter spelling:

  CREWAI_CANDIDATE_MODEL  may be openai/<same-model>; it cannot identify a different model

The package does not implement agents, test images, or freeze the model. Those remain later work.
TEXT
  printf '\nProject file preview:\n'
  local project rel target
  for project in langchain crewai; do
    while IFS= read -r rel; do
      target="$PROJECT_ROOT/$project/$rel"
      if [[ ! -e "$target" ]]; then
        printf '  CREATE   %s/%s\n' "$project" "$rel"
      elif same_file "$target" "$TEMPLATES_DIR/$project/$rel"; then
        printf '  KEEP     %s/%s\n' "$project" "$rel"
      else
        printf '  CONFLICT %s/%s\n' "$project" "$rel"
      fi
    done < <(managed_project_files "$project")
  done
}

setup_projects() {
  assert_package
  assert_uv
  assert_step14
  check_project_conflicts langchain
  check_project_conflicts crewai
  install_project_templates langchain
  install_project_templates crewai
  ensure_gitignore

  mkdir -p "$EVIDENCE_ROOT"
  local setup_log="$EVIDENCE_ROOT/step15-setup-$(date -u +%Y%m%dT%H%M%SZ)-$$.log"
  log_info "Installing/selecting Python 3.12 and syncing isolated environments."
  {
    printf 'Step 15 setup UTC: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    uv --version
    uv python install 3.12
    printf '\n=== langchain uv sync ===\n'
    (cd "$PROJECT_ROOT/langchain" && uv sync)
    (cd "$PROJECT_ROOT/langchain" && uv lock --check)
    printf '\n=== crewai uv sync ===\n'
    (cd "$PROJECT_ROOT/crewai" && uv sync)
    (cd "$PROJECT_ROOT/crewai" && uv lock --check)
  } 2>&1 | tee "$setup_log"
  python3 "$EVIDENCE_HELPER" sanitize "$setup_log"

  [[ -s "$PROJECT_ROOT/langchain/uv.lock" ]] || fail "langchain/uv.lock was not created"
  [[ -s "$PROJECT_ROOT/crewai/uv.lock" ]] || fail "crewai/uv.lock was not created"
  [[ -x "$PROJECT_ROOT/langchain/.venv/bin/python" ]] || fail "LangChain .venv was not created"
  [[ -x "$PROJECT_ROOT/crewai/.venv/bin/python" ]] || fail "CrewAI .venv was not created"
  local lg_venv cr_venv
  lg_venv="$(realpath "$PROJECT_ROOT/langchain/.venv")"
  cr_venv="$(realpath "$PROJECT_ROOT/crewai/.venv")"
  [[ "$lg_venv" != "$cr_venv" ]] || fail "The two projects unexpectedly share one virtual environment"
  log_ok "Step 15 setup complete with separate environments and lockfiles."
  printf 'Setup evidence: %s\n' "$setup_log"
  printf '\nNext: bash scripts/run-phase0-step15.sh run-offline\n'
}

assert_setup() {
  assert_package
  assert_uv
  for project in langchain crewai; do
    [[ "$(cat "$PROJECT_ROOT/$project/.python-version" 2>/dev/null)" == "3.12" ]] || fail "$project/.python-version must be 3.12"
    [[ -s "$PROJECT_ROOT/$project/pyproject.toml" ]] || fail "Missing $project/pyproject.toml; run setup"
    [[ -s "$PROJECT_ROOT/$project/uv.lock" ]] || fail "Missing $project/uv.lock; run setup"
    [[ -x "$PROJECT_ROOT/$project/.venv/bin/python" ]] || fail "Missing $project/.venv; run setup"
    (cd "$PROJECT_ROOT/$project" && uv lock --check >/dev/null)
  done
  [[ "$(realpath "$PROJECT_ROOT/langchain/.venv")" != "$(realpath "$PROJECT_ROOT/crewai/.venv")" ]] || fail "Projects share a virtual environment"
}

run_command_test() {
  local results_file="$1" test_id="$2" log_file="$3" project="$4" script="$5"
  shift 5
  local status exit_code
  set +e
  (
    cd "$PROJECT_ROOT/$project"
    env \
      CREWAI_DISABLE_TELEMETRY=true \
      OTEL_SDK_DISABLED=true \
      LANGGRAPH_STRICT_MSGPACK=true \
      uv run --locked python "$script" "$@"
  ) >"$log_file" 2>&1
  exit_code=$?
  set -e
  python3 "$EVIDENCE_HELPER" sanitize "$log_file"
  if [[ $exit_code -eq 0 ]]; then
    status="pass"
    log_ok "$test_id PASS"
  else
    status="fail"
    log_warn "$test_id FAIL — inspect $log_file"
  fi
  printf '%s\t%s\t%s\t%s\n' "$test_id" "$status" "$exit_code" "$(basename "$log_file")" >> "$results_file"
  return 0
}

prepare_run_dir() {
  local prefix="$1"
  local run_id="${prefix}-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  local run_dir="$EVIDENCE_ROOT/$run_id"
  mkdir -p "$run_dir"
  printf '%s\n%s\n' "$run_id" "$run_dir"
}

run_offline() {
  assert_setup
  assert_step14
  local info run_id run_dir results
  mapfile -t info < <(prepare_run_dir "step15-offline")
  run_id="${info[0]}"; run_dir="${info[1]}"; results="$run_dir/results.tsv"
  : > "$results"
  rm -rf "$PROJECT_ROOT/langchain/.preflight-state"
  mkdir -p "$PROJECT_ROOT/langchain/.preflight-state"
  log_info "Running eight model-free checks in $run_id"
  run_command_test "$results" PY-LG-001 "$run_dir/PY-LG-001.log" langchain preflight/python_version.py
  run_command_test "$results" PY-LG-002 "$run_dir/PY-LG-002.log" langchain preflight/imports.py
  run_command_test "$results" LG-GRAPH-001 "$run_dir/LG-GRAPH-001.log" langchain preflight/minimal_graph.py
  run_command_test "$results" LG-SQLITE-001 "$run_dir/LG-SQLITE-001.log" langchain preflight/sqlite_write.py
  run_command_test "$results" LG-SQLITE-002 "$run_dir/LG-SQLITE-002.log" langchain preflight/sqlite_reload.py
  run_command_test "$results" PY-CR-001 "$run_dir/PY-CR-001.log" crewai preflight/python_version.py
  run_command_test "$results" PY-CR-002 "$run_dir/PY-CR-002.log" crewai preflight/imports.py
  run_command_test "$results" CR-FLOW-001 "$run_dir/CR-FLOW-001.log" crewai preflight/minimal_flow.py
  local failed
  failed="$(awk -F '\t' '$2 != "pass" {count++} END {print count+0}' "$results")"
  if [[ "$failed" -ne 0 ]]; then
    fail "Offline preflight had $failed failure(s). Evidence: $run_dir"
  fi
  log_ok "All eight model-free checks passed."
  printf 'Offline evidence: %s\n' "$run_dir"
  printf '\nNext: bash scripts/run-phase0-step15.sh run-interactive\n'
}

assert_model_environment() {
  [[ -n "${OPENAI_API_KEY:-}" ]] || fail "OPENAI_API_KEY is required. Use run-interactive to enter it without echo."
  [[ -n "${OPENAI_CANDIDATE_MODEL:-}" ]] || fail "OPENAI_CANDIDATE_MODEL is required. The candidate remains unfrozen until Step 16."
  local adapter="${CREWAI_CANDIDATE_MODEL:-$OPENAI_CANDIDATE_MODEL}"
  [[ "${adapter#openai/}" == "$OPENAI_CANDIDATE_MODEL" ]] || fail "CREWAI_CANDIDATE_MODEL must refer to the same underlying model."
}

run_full() {
  assert_setup
  assert_step14
  assert_model_environment
  local info run_id run_dir results started finished summary_status model
  model="$OPENAI_CANDIDATE_MODEL"
  mapfile -t info < <(prepare_run_dir "step15")
  run_id="${info[0]}"; run_dir="${info[1]}"; results="$run_dir/results.tsv"
  : > "$results"
  mkdir -p "$EVIDENCE_ROOT"
  printf '%s\n' "evidence/logs/preflight/$run_id" > "$LAST_RUN_FILE"
  started="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  rm -rf "$PROJECT_ROOT/langchain/.preflight-state"
  mkdir -p "$PROJECT_ROOT/langchain/.preflight-state"

  {
    printf 'run_id=%s\n' "$run_id"
    printf 'started_at_utc=%s\n' "$started"
    printf 'candidate_model=%s\n' "$model"
    printf 'candidate_status=not frozen; pending Step 16\n'
    uv --version
  } > "$run_dir/environment.txt"

  log_info "Running ten Step 15 checks in $run_id"
  run_command_test "$results" PY-LG-001 "$run_dir/PY-LG-001.log" langchain preflight/python_version.py
  run_command_test "$results" PY-LG-002 "$run_dir/PY-LG-002.log" langchain preflight/imports.py
  run_command_test "$results" LG-GRAPH-001 "$run_dir/LG-GRAPH-001.log" langchain preflight/minimal_graph.py
  run_command_test "$results" LG-SQLITE-001 "$run_dir/LG-SQLITE-001.log" langchain preflight/sqlite_write.py
  run_command_test "$results" LG-SQLITE-002 "$run_dir/LG-SQLITE-002.log" langchain preflight/sqlite_reload.py
  run_command_test "$results" LG-MODEL-001 "$run_dir/LG-MODEL-001.log" langchain preflight/model_ping.py
  run_command_test "$results" PY-CR-001 "$run_dir/PY-CR-001.log" crewai preflight/python_version.py
  run_command_test "$results" PY-CR-002 "$run_dir/PY-CR-002.log" crewai preflight/imports.py
  run_command_test "$results" CR-FLOW-001 "$run_dir/CR-FLOW-001.log" crewai preflight/minimal_flow.py
  run_command_test "$results" CR-MODEL-001 "$run_dir/CR-MODEL-001.log" crewai preflight/model_ping.py

  (
    cd "$PROJECT_ROOT/langchain"
    uv run --locked python "$SCRIPT_DIR/step15_versions.py" langchain
  ) > "$run_dir/langchain-package-versions.json"
  (
    cd "$PROJECT_ROOT/crewai"
    uv run --locked python "$SCRIPT_DIR/step15_versions.py" crewai
  ) > "$run_dir/crewai-package-versions.json"
  sha256sum "$PROJECT_ROOT/langchain/uv.lock" "$PROJECT_ROOT/crewai/uv.lock" > "$run_dir/lockfiles-sha256.txt"
  printf 'Relative SQLite path: langchain/.preflight-state/checkpoints.sqlite\nThe SQLite database is runtime-only and is not retained in Git.\n' > "$run_dir/langgraph-sqlite-path.txt"

  finished="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  set +e
  python3 "$EVIDENCE_HELPER" summary "$run_dir" --run-id "$run_id" --model "$model" --started "$started" --finished "$finished"
  summary_status=$?
  set -e
  python3 "$EVIDENCE_HELPER" sanitize "$run_dir"/*.log "$run_dir/environment.txt" "$run_dir"/*.json "$run_dir"/*.txt

  if [[ $summary_status -eq 0 ]]; then
    printf '%s\n' "evidence/logs/preflight/$run_id" > "$LATEST_FILE"
    log_ok "Step 15 preflight passed: 10/10 tests."
    printf '\nEvidence directory:\n  %s\n' "$run_dir"
    printf 'Summary:\n  %s\n' "$run_dir/summary.md"
    printf '\nNext: bash scripts/run-phase0-step15.sh finalize confirm\n'
  else
    fail "Step 15 preflight failed. Evidence was retained at: $run_dir"
  fi
}

run_interactive() {
  local entered_key="${OPENAI_API_KEY:-}" entered_model="${OPENAI_CANDIDATE_MODEL:-}"
  if [[ -z "$entered_key" ]]; then
    read -r -s -p "OpenAI API key (input hidden; not saved): " entered_key
    printf '\n'
  fi
  if [[ -z "$entered_model" ]]; then
    read -r -p "Candidate OpenAI model ID (not frozen until Step 16): " entered_model
  fi
  [[ -n "$entered_key" && -n "$entered_model" ]] || fail "API key and candidate model are required"
  export OPENAI_API_KEY="$entered_key"
  export OPENAI_CANDIDATE_MODEL="$entered_model"
  export CREWAI_CANDIDATE_MODEL="${CREWAI_CANDIDATE_MODEL:-$entered_model}"
  run_full
  unset OPENAI_API_KEY
}

run_audit() {
  assert_setup
  python3 "$AUDIT_HELPER" "$PROJECT_ROOT"
}

finalize_step() {
  [[ "${1:-}" == "confirm" ]] || fail "Finalization requires: finalize confirm"
  assert_setup
  python3 "$AUDIT_HELPER" "$PROJECT_ROOT"
  if grep -Fq -- "- [x] Step 15 separate LangChain/LangGraph and CrewAI environments pass preflight." "$PROJECT_ROOT/PLAN.md"; then
    log_info "Step 15 is already finalized."
    return 0
  fi
  local evidence_rel summary model uv_version backup_dir
  evidence_rel="$(cat "$LATEST_FILE")"
  summary="$PROJECT_ROOT/$evidence_rel/summary.json"
  model="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["candidate_model"])' "$summary")"
  uv_version="$(uv --version | awk '{print $2}')"
  backup_dir="$BACKUP_ROOT/finalize-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  python3 "$FINALIZE_HELPER" "$PROJECT_ROOT" \
    --evidence-rel "$evidence_rel" \
    --model "$model" \
    --uv-version "$uv_version" \
    --backup-dir "$backup_dir"
  python3 "$AUDIT_HELPER" "$PROJECT_ROOT"
  log_ok "Step 15 finalized. Candidate model remains explicitly unfrozen pending Step 16."
  printf 'Document backup: %s\n' "$backup_dir"
}

show_status() {
  assert_package
  log_info "Phase 0 Step 15 runner version: $STEP15_SCRIPT_VERSION"
  for project in langchain crewai; do
    if [[ -s "$PROJECT_ROOT/$project/uv.lock" && -x "$PROJECT_ROOT/$project/.venv/bin/python" ]]; then
      printf '%-10s setup: ready\n' "$project"
    else
      printf '%-10s setup: incomplete\n' "$project"
    fi
  done
  if [[ -f "$LAST_RUN_FILE" ]]; then printf 'Last run:       %s\n' "$(cat "$LAST_RUN_FILE")"; else printf 'Last run:       none\n'; fi
  if [[ -f "$LATEST_FILE" ]]; then printf 'Latest pass:    %s\n' "$(cat "$LATEST_FILE")"; else printf 'Latest pass:    none\n'; fi
  if grep -Fq -- "- [x] Step 15 separate LangChain/LangGraph and CrewAI environments pass preflight." "$PROJECT_ROOT/PLAN.md" 2>/dev/null; then
    printf 'Finalized:      yes\n'
  else
    printf 'Finalized:      no\n'
  fi
}

main() {
  local mode="${1:-}"
  case "$mode" in
    preview) print_preview ;;
    setup) setup_projects ;;
    run-offline) run_offline ;;
    run) run_full ;;
    run-interactive) run_interactive ;;
    audit) run_audit ;;
    finalize) finalize_step "${2:-}" ;;
    status) show_status ;;
    -h|--help|help|"") usage ;;
    *) usage; fail "Unknown mode: $mode" ;;
  esac
}

main "$@"
