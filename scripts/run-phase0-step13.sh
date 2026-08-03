#!/usr/bin/env bash
set -euo pipefail

STEP13_SCRIPT_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATES_DIR="$SCRIPT_DIR/phase0-step13-templates"
GITIGNORE_BEGIN="# BEGIN PHASE0-STEP13 MANAGED IGNORE RULES"
GITIGNORE_END="# END PHASE0-STEP13 MANAGED IGNORE RULES"

log_info() { printf '[INFO] %s\n' "$*"; }
log_ok() { printf '[OK] %s\n' "$*"; }
log_warn() { printf '[WARNING] %s\n' "$*" >&2; }
fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'USAGE'
Phase 0 Step 13 — repository structure and evidence scaffolding

Usage:
  bash scripts/run-phase0-step13.sh preview
  bash scripts/run-phase0-step13.sh apply
  bash scripts/run-phase0-step13.sh audit
  bash scripts/run-phase0-step13.sh git-init confirm
  bash scripts/run-phase0-step13.sh secret-scan

Modes:
  preview           Show what would be created without changing the project.
  apply             Create missing directories and seed missing documents. Never overwrite.
  audit             Verify the scaffold, shared-boundary rules, and hypothesis-only claim seed.
  git-init confirm  Initialize a local Git repository on branch main. Does not commit or add remote.
  secret-scan       List files with likely secret-shaped text; never print matching values.
USAGE
}

required_dirs=(
  "docs/architecture"
  "docs/decisions"
  "docs/research"
  "shared/drupal_client"
  "shared/schemas"
  "shared/fixtures"
  "shared/prompts"
  "shared/validators"
  "shared/evaluations"
  "shared/failure_injector"
  "drupal"
  "langchain"
  "crewai"
  "db"
  "scripts"
  "evidence/tests"
  "evidence/logs"
  "evidence/screenshots"
  "evidence/results"
  "recordings/raw"
  "recordings/edited"
  "recordings/stills"
)

root_templates=(
  "README.md"
  "PLAN.md"
  "EXPERIMENT_SPEC.md"
  "VERSIONS.md"
  "SOURCES.md"
  "CLAIMS_REGISTER.md"
  "COMPARISON_MATRIX.md"
  "DEMO_SCRIPT.md"
  "RECORDING_SHOT_LIST.md"
)

extra_templates=(
  "shared/README.md"
  "docs/decisions/ADR_TEMPLATE.md"
  "docs/research/SOURCE_NOTE_TEMPLATE.md"
  "evidence/README.md"
)

assert_installation() {
  [[ -d "$PROJECT_ROOT/drupal" ]] || fail "Expected Drupal directory is missing: $PROJECT_ROOT/drupal"
  [[ -d "$TEMPLATES_DIR" ]] || fail "Step 13 templates are missing. Re-run install-step13.sh."
}

print_preview() {
  assert_installation
  log_info "Phase 0 Step 13 runner version: $STEP13_SCRIPT_VERSION"
  printf '\nDirectories:\n'
  local rel
  for rel in "${required_dirs[@]}"; do
    if [[ -d "$PROJECT_ROOT/$rel" ]]; then
      printf '  KEEP    %s/\n' "$rel"
    else
      printf '  CREATE  %s/\n' "$rel"
    fi
  done

  printf '\nStarter documents:\n'
  for rel in "${root_templates[@]}" "${extra_templates[@]}"; do
    if [[ -e "$PROJECT_ROOT/$rel" ]]; then
      printf '  KEEP    %s\n' "$rel"
    else
      printf '  CREATE  %s\n' "$rel"
    fi
  done

  printf '\nGit ignore rules:\n'
  if [[ -f "$PROJECT_ROOT/.gitignore" ]] && grep -Fq "$GITIGNORE_BEGIN" "$PROJECT_ROOT/.gitignore"; then
    printf '  KEEP    .gitignore managed Step 13 block\n'
  elif [[ -f "$PROJECT_ROOT/.gitignore" ]]; then
    printf '  APPEND  .gitignore managed Step 13 block\n'
  else
    printf '  CREATE  .gitignore\n'
  fi

  printf '\nNo existing project file will be overwritten.\n'
}

copy_if_missing() {
  local rel="$1"
  local source="$TEMPLATES_DIR/$rel"
  local target="$PROJECT_ROOT/$rel"
  [[ -f "$source" ]] || fail "Template is missing: $source"
  if [[ -e "$target" ]]; then
    log_info "Preserved existing file: $rel"
    return 0
  fi
  mkdir -p "$(dirname "$target")"
  cp "$source" "$target"
  log_ok "Created: $rel"
}

ensure_gitignore() {
  local template="$TEMPLATES_DIR/.gitignore.block"
  local target="$PROJECT_ROOT/.gitignore"
  [[ -f "$template" ]] || fail "Git-ignore template is missing."

  if [[ -f "$target" ]] && grep -Fq "$GITIGNORE_BEGIN" "$target"; then
    log_info "Preserved existing Step 13 block in .gitignore."
    return 0
  fi

  if [[ -s "$target" ]]; then
    printf '\n' >> "$target"
  fi
  cat "$template" >> "$target"
  log_ok "Added managed Step 13 rules to .gitignore."
}

ensure_empty_dir_marker() {
  local rel="$1"
  local dir="$PROJECT_ROOT/$rel"
  local marker="$dir/.gitkeep"
  if find "$dir" -mindepth 1 -maxdepth 1 ! -name '.gitkeep' -print -quit | grep -q .; then
    return 0
  fi
  [[ -e "$marker" ]] || : > "$marker"
}

apply_scaffold() {
  assert_installation
  log_info "Phase 0 Step 13 runner version: $STEP13_SCRIPT_VERSION"
  local rel
  for rel in "${required_dirs[@]}"; do
    if [[ -d "$PROJECT_ROOT/$rel" ]]; then
      log_info "Preserved existing directory: $rel/"
    else
      mkdir -p "$PROJECT_ROOT/$rel"
      log_ok "Created directory: $rel/"
    fi
  done

  for rel in "${root_templates[@]}" "${extra_templates[@]}"; do
    copy_if_missing "$rel"
  done

  ensure_gitignore

  for rel in "${required_dirs[@]}"; do
    case "$rel" in
      db|recordings/*) ;; # Intentionally private/ignored; no Git marker required.
      *) ensure_empty_dir_marker "$rel" ;;
    esac
  done

  audit_scaffold
  log_ok "Step 13 apply completed without overwriting existing project content."
}

check_file_contains() {
  local rel="$1"
  local pattern="$2"
  grep -Fq "$pattern" "$PROJECT_ROOT/$rel" || fail "$rel is missing required marker: $pattern"
}

check_hypothesis_seed() {
  local file="$PROJECT_ROOT/CLAIMS_REGISTER.md"
  local rows
  rows="$(awk -F'|' '
    /^[|]/ {
      status=$7; gsub(/^[ \t]+|[ \t]+$/, "", status);
      if (status == "hypothesis") count++;
      if (status == "observed" || status == "verified") bad++;
    }
    END { print count+0 ":" bad+0 }
  ' "$file")"
  local hypothesis_count="${rows%%:*}"
  local bad_count="${rows##*:}"
  (( hypothesis_count >= 3 )) || fail "CLAIMS_REGISTER.md must seed at least three hypothesis rows."
  (( bad_count == 0 )) || fail "CLAIMS_REGISTER.md seed contains observed/verified rows before experiments."
  log_ok "Claims register contains $hypothesis_count hypothesis rows and no premature observed/verified rows."
}

check_gitignore() {
  local target="$PROJECT_ROOT/.gitignore"
  [[ -f "$target" ]] || fail ".gitignore is missing."
  grep -Fq "$GITIGNORE_BEGIN" "$target" || fail ".gitignore is missing the managed Step 13 block."
  grep -Fq '/db/' "$target" || fail ".gitignore does not protect db/."
  grep -Fq '/recordings/' "$target" || fail ".gitignore does not protect recordings/."
  grep -Fq '**/.secrets/' "$target" || fail ".gitignore does not protect local .secrets directories."
  log_ok "Git-ignore protections are present."
}

audit_scaffold() {
  assert_installation
  log_info "Auditing Step 13 scaffold..."
  local rel
  for rel in "${required_dirs[@]}"; do
    [[ -d "$PROJECT_ROOT/$rel" ]] || fail "Required directory is missing: $rel/"
  done
  log_ok "All required directories exist."

  for rel in "${root_templates[@]}" "${extra_templates[@]}"; do
    [[ -s "$PROJECT_ROOT/$rel" ]] || fail "Required starter document is missing or empty: $rel"
  done
  log_ok "All required starter documents exist."

  check_file_contains "shared/README.md" "Framework-owned behavior must stay outside shared/"
  check_file_contains "shared/README.md" "Context assembly"
  check_file_contains "shared/README.md" "Workflow sequencing"
  log_ok "Shared-substrate boundary is documented."

  check_file_contains "SOURCES.md" "SA-CONTRIB-2026-057"
  check_file_contains "SOURCES.md" "LangGraph checkpointing documentation"
  check_file_contains "SOURCES.md" "CrewAI human-feedback documentation"
  log_ok "Required source-register entries are seeded."

  check_hypothesis_seed
  check_gitignore

  if [[ -d "$PROJECT_ROOT/.git" ]]; then
    log_ok "Local Git repository exists."
  else
    log_warn "Local Git repository is not initialized yet. Use: bash scripts/run-phase0-step13.sh git-init confirm"
  fi

  log_ok "Step 13 audit passed."
}

init_git() {
  [[ "${1:-}" == "confirm" ]] || fail "Git initialization requires: git-init confirm"
  assert_installation
  if [[ -d "$PROJECT_ROOT/.git" ]]; then
    log_info "Git repository already exists; no initialization performed."
  else
    git -C "$PROJECT_ROOT" init -b main
    log_ok "Initialized local Git repository on branch main."
  fi
  git -C "$PROJECT_ROOT" status --short
  printf '\n[INFO] This command did not stage, commit, push, or create a GitHub remote.\n'
}

secret_scan() {
  assert_installation
  log_info "Scanning filenames for likely secret-shaped text. Matching values are never printed."
  local output
  output="$(mktemp)"
  trap 'rm -f "$output"' RETURN

  grep -RIlE \
    '(api[_-]?key|client[_-]?secret|authorization:[[:space:]]*(bearer|basic)|password[[:space:]]*[:=]|sk-[A-Za-z0-9_-]{12,})' \
    "$PROJECT_ROOT" \
    --exclude-dir=.git \
    --exclude-dir=.phase0-step13-backups \
    --exclude-dir=vendor \
    --exclude-dir=core \
    --exclude-dir=contrib \
    --exclude-dir=files \
    --exclude-dir=db \
    --exclude-dir=recordings \
    --exclude='*.png' \
    --exclude='*.jpg' \
    --exclude='*.jpeg' \
    --exclude='*.gif' \
    --exclude='*.webp' \
    --exclude='*.zip' \
    --exclude='*.zst' \
    --exclude='*.gz' \
    2>/dev/null | sort -u > "$output" || true

  if [[ ! -s "$output" ]]; then
    log_ok "No likely secret-bearing files were detected by the heuristic scan."
    return 0
  fi

  log_warn "Review these files before staging. The scan is heuristic and may include documentation/examples:"
  sed "s#^$PROJECT_ROOT/##; s#^#  #" "$output"
  printf '\n[WARNING] Do not stage until every listed file has been reviewed.\n' >&2
  return 3
}

mode="${1:-}"
case "$mode" in
  preview) print_preview ;;
  apply) apply_scaffold ;;
  audit) audit_scaffold ;;
  git-init) init_git "${2:-}" ;;
  secret-scan) secret_scan ;;
  -h|--help|help|'') usage ;;
  *) usage >&2; fail "Unknown mode: $mode" ;;
esac
