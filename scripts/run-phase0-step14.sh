#!/usr/bin/env bash
set -euo pipefail

STEP14_SCRIPT_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BASELINE_DIR="$SCRIPT_DIR/phase0-step14-baseline"
TEMPLATES_DIR="$SCRIPT_DIR/phase0-step14-templates"
AUDIT_PY="$SCRIPT_DIR/step14_audit.py"
BACKUP_ROOT="$PROJECT_ROOT/.phase0-step14-backups"
MANIFEST_REL="docs/decisions/step14-contract-sha256.txt"

ROOT_FILES=("README.md" "PLAN.md" "EXPERIMENT_SPEC.md")
CONTRACT_FILES=(
  "EXPERIMENT_SPEC.md"
  "shared/schemas/target.schema.json"
  "shared/schemas/image-context.schema.json"
  "shared/schemas/recommendation.schema.json"
  "shared/schemas/tool-result.schema.json"
  "shared/schemas/run-state.schema.json"
  "shared/prompts/PROMPTS.md"
  "docs/decisions/ADR-0001-freeze-experiment-contract.md"
)
NEW_TEMPLATE_FILES=(
  "shared/schemas/target.schema.json"
  "shared/schemas/image-context.schema.json"
  "shared/schemas/recommendation.schema.json"
  "shared/schemas/tool-result.schema.json"
  "shared/schemas/run-state.schema.json"
  "shared/prompts/PROMPTS.md"
  "docs/decisions/ADR-0001-freeze-experiment-contract.md"
)

log_info() { printf '[INFO] %s\n' "$*"; }
log_ok() { printf '[OK] %s\n' "$*"; }
log_warn() { printf '[WARNING] %s\n' "$*" >&2; }
fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'USAGE'
Phase 0 Step 14 — experiment contract and shared schemas

Usage:
  bash scripts/run-phase0-step14.sh preview
  bash scripts/run-phase0-step14.sh apply
  bash scripts/run-phase0-step14.sh audit
  bash scripts/run-phase0-step14.sh freeze confirm
  bash scripts/run-phase0-step14.sh status

Modes:
  preview         Show the recognized repository state and proposed changes.
  apply           Back up and replace the exact Step 13 draft with the ready-to-freeze contract.
  audit           Validate documents, schemas, fairness rules, and hashes when frozen.
  freeze confirm  Mark the contract frozen, update README/PLAN, and create SHA-256 manifest.
  status          Print the recognized Step 14 state and relevant paths.

The script never stages, commits, tags, or pushes Git content.
USAGE
}

assert_installation() {
  [[ -d "$PROJECT_ROOT/drupal" ]] || fail "Expected Drupal directory is missing: $PROJECT_ROOT/drupal"
  [[ -d "$BASELINE_DIR" ]] || fail "Step 14 baseline files are missing. Re-run install-step14.sh."
  [[ -d "$TEMPLATES_DIR" ]] || fail "Step 14 templates are missing. Re-run install-step14.sh."
  [[ -x "$AUDIT_PY" ]] || fail "Step 14 audit helper is missing or not executable: $AUDIT_PY"
  command -v python3 >/dev/null 2>&1 || fail "python3 is required."
  command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required."
}

canonical_sha() {
  local file="$1"
  [[ -f "$file" ]] || return 1
  sed 's/\r$//' "$file" | sha256sum | awk '{print $1}'
}

same_content() {
  local left="$1" right="$2"
  [[ -f "$left" && -f "$right" ]] || return 1
  [[ "$(canonical_sha "$left")" == "$(canonical_sha "$right")" ]]
}

root_variant_path() {
  local rel="$1" variant="$2"
  case "$rel" in
    README.md) printf '%s/README.%s.md\n' "$TEMPLATES_DIR" "$variant" ;;
    PLAN.md) printf '%s/PLAN.%s.md\n' "$TEMPLATES_DIR" "$variant" ;;
    EXPERIMENT_SPEC.md) printf '%s/EXPERIMENT_SPEC.%s.md\n' "$TEMPLATES_DIR" "$variant" ;;
    *) fail "Unknown root file: $rel" ;;
  esac
}

classify_root_file() {
  local rel="$1"
  local current="$PROJECT_ROOT/$rel"
  local baseline="$BASELINE_DIR/$rel"
  local ready frozen
  ready="$(root_variant_path "$rel" ready)"
  frozen="$(root_variant_path "$rel" frozen)"
  [[ -f "$current" ]] || { printf 'missing\n'; return; }
  if same_content "$current" "$baseline"; then
    printf 'baseline\n'
  elif same_content "$current" "$ready"; then
    printf 'ready\n'
  elif same_content "$current" "$frozen"; then
    printf 'frozen\n'
  else
    printf 'modified\n'
  fi
}

repository_state() {
  local expected="" rel state
  for rel in "${ROOT_FILES[@]}"; do
    state="$(classify_root_file "$rel")"
    if [[ "$state" == "missing" || "$state" == "modified" ]]; then
      printf '%s\n' "$state"
      return
    fi
    if [[ -z "$expected" ]]; then
      expected="$state"
    elif [[ "$expected" != "$state" ]]; then
      printf 'mixed\n'
      return
    fi
  done
  printf '%s\n' "$expected"
}

assert_expected_templates() {
  local rel source
  for rel in "${ROOT_FILES[@]}"; do
    [[ -s "$BASELINE_DIR/$rel" ]] || fail "Missing baseline: $BASELINE_DIR/$rel"
    for source in "$(root_variant_path "$rel" ready)" "$(root_variant_path "$rel" frozen)"; do
      [[ -s "$source" ]] || fail "Missing template: $source"
    done
  done
  for rel in "${NEW_TEMPLATE_FILES[@]}"; do
    [[ -s "$TEMPLATES_DIR/$rel" ]] || fail "Missing template: $TEMPLATES_DIR/$rel"
  done
}

new_backup_dir() {
  mkdir -p "$BACKUP_ROOT"
  local stamp
  stamp="$(date -u +%Y%m%dT%H%M%SZ)-$$"
  printf '%s/%s\n' "$BACKUP_ROOT" "$stamp"
}

backup_file() {
  local rel="$1" backup_dir="$2"
  local source="$PROJECT_ROOT/$rel"
  [[ -e "$source" ]] || return 0
  mkdir -p "$backup_dir/$(dirname "$rel")"
  cp -a "$source" "$backup_dir/$rel"
}

copy_template() {
  local source="$1" rel="$2"
  mkdir -p "$PROJECT_ROOT/$(dirname "$rel")"
  cp "$source" "$PROJECT_ROOT/$rel"
  sed -i 's/\r$//' "$PROJECT_ROOT/$rel"
}

check_new_files_safe() {
  local rel target source
  for rel in "${NEW_TEMPLATE_FILES[@]}"; do
    target="$PROJECT_ROOT/$rel"
    source="$TEMPLATES_DIR/$rel"
    if [[ -e "$target" ]] && ! same_content "$target" "$source"; then
      fail "Refusing to overwrite an unexpected existing file: $rel. Move or review it, then rerun."
    fi
  done
}

ensure_new_files() {
  local rel target source
  for rel in "${NEW_TEMPLATE_FILES[@]}"; do
    target="$PROJECT_ROOT/$rel"
    source="$TEMPLATES_DIR/$rel"
    if [[ -e "$target" ]]; then
      log_info "Preserved matching contract file: $rel"
    else
      copy_template "$source" "$rel"
      log_ok "Created: $rel"
    fi
  done
}

print_preview() {
  assert_installation
  assert_expected_templates
  local state rel target
  state="$(repository_state)"
  log_info "Phase 0 Step 14 runner version: $STEP14_SCRIPT_VERSION"
  printf 'Repository state: %s\n\n' "$state"
  case "$state" in
    baseline)
      printf 'Root documents:\n'
      for rel in "${ROOT_FILES[@]}"; do printf '  REPLACE  %s with ready-to-freeze version\n' "$rel"; done
      ;;
    ready)
      printf 'Root documents already match the ready-to-freeze package.\n'
      ;;
    frozen)
      printf 'Root documents already match the frozen package.\n'
      ;;
    mixed|modified|missing)
      printf 'The root documents are not in one recognized Step 13/14 state. Apply will refuse.\n'
      ;;
  esac
  printf '\nContract files:\n'
  for rel in "${NEW_TEMPLATE_FILES[@]}"; do
    target="$PROJECT_ROOT/$rel"
    if [[ ! -e "$target" ]]; then
      printf '  CREATE   %s\n' "$rel"
    elif same_content "$target" "$TEMPLATES_DIR/$rel"; then
      printf '  KEEP     %s\n' "$rel"
    else
      printf '  CONFLICT %s\n' "$rel"
    fi
  done
  printf '\nNo Git staging, commit, tag, or push will be performed.\n'
}

apply_contract() {
  assert_installation
  assert_expected_templates
  check_new_files_safe
  local state backup_dir rel
  state="$(repository_state)"
  case "$state" in
    baseline)
      backup_dir="$(new_backup_dir)"
      for rel in "${ROOT_FILES[@]}"; do backup_file "$rel" "$backup_dir"; done
      for rel in "${ROOT_FILES[@]}"; do copy_template "$(root_variant_path "$rel" ready)" "$rel"; done
      log_ok "Installed ready-to-freeze root documents."
      log_info "Backup: $backup_dir"
      ;;
    ready)
      log_info "Ready-to-freeze root documents are already installed."
      ;;
    frozen)
      log_info "Contract is already frozen; apply made no root-document changes."
      ;;
    mixed)
      fail "README.md, PLAN.md, and EXPERIMENT_SPEC.md are in mixed recognized states. Restore consistency before applying."
      ;;
    modified)
      fail "At least one root document differs from both the Step 13 baseline and Step 14 templates. Refusing to overwrite local work."
      ;;
    missing)
      fail "At least one required root document is missing. Restore the Step 13 scaffold before applying."
      ;;
    *) fail "Unknown repository state: $state" ;;
  esac

  ensure_new_files

  if [[ "$state" != "frozen" && -e "$PROJECT_ROOT/$MANIFEST_REL" ]]; then
    fail "A frozen hash manifest exists while root documents are not frozen: $MANIFEST_REL"
  fi

  run_audit
  log_ok "Step 14 package applied. Review the contract, then run: bash scripts/run-phase0-step14.sh freeze confirm"
}

verify_hash_manifest() {
  local manifest="$PROJECT_ROOT/$MANIFEST_REL"
  [[ -s "$manifest" ]] || fail "Missing frozen contract hash manifest: $MANIFEST_REL"
  (cd "$PROJECT_ROOT" && sha256sum -c "$MANIFEST_REL")
  log_ok "Frozen contract SHA-256 manifest is valid."
}

run_audit() {
  assert_installation
  python3 "$AUDIT_PY" "$PROJECT_ROOT"
  if [[ "$(repository_state)" == "frozen" ]]; then
    verify_hash_manifest
  fi
}

freeze_contract() {
  [[ "${1:-}" == "confirm" ]] || fail "Freezing requires: freeze confirm"
  assert_installation
  assert_expected_templates
  check_new_files_safe
  local state backup_dir rel manifest
  state="$(repository_state)"
  if [[ "$state" == "frozen" ]]; then
    log_info "Contract is already frozen."
    run_audit
    return 0
  fi
  [[ "$state" == "ready" ]] || fail "Freeze requires the ready-to-freeze state. Current state: $state. Run apply first."

  run_audit
  backup_dir="$(new_backup_dir)"
  for rel in "${ROOT_FILES[@]}"; do backup_file "$rel" "$backup_dir"; done
  backup_file "$MANIFEST_REL" "$backup_dir"

  for rel in "${ROOT_FILES[@]}"; do copy_template "$(root_variant_path "$rel" frozen)" "$rel"; done

  manifest="$PROJECT_ROOT/$MANIFEST_REL"
  mkdir -p "$(dirname "$manifest")"
  (
    cd "$PROJECT_ROOT"
    sha256sum "${CONTRACT_FILES[@]}"
  ) > "$manifest"
  chmod 0644 "$manifest"

  log_ok "Marked the Step 14 contract frozen and generated its SHA-256 manifest."
  log_info "Backup: $backup_dir"
  run_audit
  log_ok "Step 14 is complete. The next implementation activity is Step 15 environment preflight."
}

print_status() {
  assert_installation
  local state
  state="$(repository_state)"
  log_info "Phase 0 Step 14 runner version: $STEP14_SCRIPT_VERSION"
  printf 'Project root: %s\n' "$PROJECT_ROOT"
  printf 'Repository state: %s\n' "$state"
  printf 'Contract manifest: %s\n' "$PROJECT_ROOT/$MANIFEST_REL"
  printf 'Backup root: %s\n' "$BACKUP_ROOT"
  if [[ "$state" == "ready" ]]; then
    printf 'Next command: bash scripts/run-phase0-step14.sh audit\n'
    printf 'Then: bash scripts/run-phase0-step14.sh freeze confirm\n'
  elif [[ "$state" == "frozen" ]]; then
    printf 'Next command: bash scripts/run-phase0-step14.sh audit\n'
    printf 'Then proceed to Step 15.\n'
  else
    printf 'Run preview and resolve the reported state before applying.\n'
  fi
}

mode="${1:-}"
case "$mode" in
  preview) print_preview ;;
  apply) apply_contract ;;
  audit) run_audit ;;
  freeze) freeze_contract "${2:-}" ;;
  status) print_status ;;
  -h|--help|help|"") usage ;;
  *) usage; fail "Unknown mode: $mode" ;;
esac
