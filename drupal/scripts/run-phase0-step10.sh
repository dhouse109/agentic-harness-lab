#!/usr/bin/env bash
set -Eeuo pipefail

STEP10_SCRIPT_VERSION="1.0.3"
SNAPSHOT_NAME="seeded-clean"
MODE="${1:-audit}"
CONFIRMATION="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DB_DIR="$(cd "$PROJECT_ROOT/.." && pwd)/db"

DB_DUMP="$DB_DIR/seeded-clean.sql.gz"
FILES_ARCHIVE="$DB_DIR/seeded-clean-files.tar.gz"
BASELINE_MANIFEST="$DB_DIR/seeded-clean-manifest.json"
METADATA_FILE="$DB_DIR/seeded-clean-metadata.txt"
CHECKSUM_FILE="$DB_DIR/seeded-clean-checksums.sha256"
DB_GITIGNORE="$DB_DIR/.gitignore"

CREATE_TEMP_DIR=""
CREATED_SNAPSHOT=0
TEST_MUTATED=0

usage() {
  cat <<'EOF'
Usage:
  bash scripts/run-phase0-step10.sh create
  bash scripts/run-phase0-step10.sh audit
  bash scripts/run-phase0-step10.sh reset
  bash scripts/run-phase0-step10.sh test-reset
  bash scripts/run-phase0-step10.sh replace confirm

Modes:
  create       Create the protected seeded-clean database snapshot, SQL export,
               seed-files archive, manifest, metadata, and checksums.
  audit        Verify both the stored baseline artifacts and current Drupal state.
  reset        Restore the database snapshot and deterministic seed files, then
               verify the exact target manifest and clean suggestion state.
  test-reset   Create controlled database drift, prove it exists, restore the
               baseline, and prove the drift disappeared.
  replace      Destructively replace an existing baseline. Requires: confirm
EOF
}

info() { printf '[INFO] %s\n' "$*"; }
ok() { printf '[OK] %s\n' "$*"; }
warn() { printf '[WARNING] %s\n' "$*" >&2; }
fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

case "$MODE" in
  create|audit|reset|test-reset)
    [[ -z "$CONFIRMATION" ]] || { usage >&2; exit 2; }
    ;;
  replace)
    [[ "$CONFIRMATION" == "confirm" ]] || fail "Replacing the trusted baseline is destructive. Use: $0 replace confirm"
    ;;
  -h|--help|help)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

cd "$PROJECT_ROOT"

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

require_project() {
  require_command ddev
  require_command tar
  require_command sha256sum
  require_command cmp
  require_command find
  require_command diff
  require_command mktemp

  [[ -f ".ddev/config.yaml" ]] || fail "Run this from a DDEV project with .ddev/config.yaml."
  [[ -f "scripts/seed.php" ]] || fail "Missing scripts/seed.php. Complete/install Step 9 first."
  [[ -f "scripts/run-phase0-step9.sh" ]] || fail "Missing scripts/run-phase0-step9.sh. Complete/install Step 9 first."
  [[ -f "scripts/phase0-step10.php" ]] || fail "Missing scripts/phase0-step10.php. Copy the full Step 10 package into scripts/."

  ddev start -y >/dev/null
}

ensure_private_db_dir() {
  mkdir -p "$DB_DIR"
  chmod 700 "$DB_DIR" 2>/dev/null || true
  cat > "$DB_GITIGNORE" <<'EOF'
*
!.gitignore
EOF
}

snapshot_files() {
  local snapshot_dir="$PROJECT_ROOT/.ddev/db_snapshots"
  [[ -d "$snapshot_dir" ]] || return 0

  # DDEV 1.25+ creates zstd-compressed snapshots (.zst), while older
  # releases used gzip (.gz). Match the named snapshot independently of
  # compression format so future DDEV changes do not invalidate the audit.
  find "$snapshot_dir" -maxdepth 1 -type f \
    \( -name "${SNAPSHOT_NAME}-*" -o -name "${SNAPSHOT_NAME}_*" -o -name "${SNAPSHOT_NAME}.*" \) \
    -print 2>/dev/null | sort
}

snapshot_count() {
  snapshot_files | awk 'NF { count++ } END { print count + 0 }'
}

get_single_snapshot_file() {
  local count
  count="$(snapshot_count)"
  if [[ "$count" -ne 1 ]]; then
    warn "DDEV snapshot directory contents:"
    find "$PROJECT_ROOT/.ddev/db_snapshots" -maxdepth 1 -type f -printf '  %f\n' 2>/dev/null | sort >&2 || true
    fail "Expected exactly one '${SNAPSHOT_NAME}' snapshot file; found $count."
  fi
  snapshot_files
}

baseline_artifacts_exist() {
  [[ "$(snapshot_count)" -gt 0 ]] || [[ -e "$DB_DUMP" ]] || [[ -e "$FILES_ARCHIVE" ]] \
    || [[ -e "$BASELINE_MANIFEST" ]] || [[ -e "$METADATA_FILE" ]] || [[ -e "$CHECKSUM_FILE" ]]
}

get_seed_files_dir() {
  local container_path
  container_path="$(ddev drush --quiet php:eval 'echo \Drupal::service("file_system")->realpath("public://phase0-step9-seed");')"
  [[ -n "$container_path" ]] || fail "Drupal did not resolve public://phase0-step9-seed."

  case "$container_path" in
    /var/www/html/*)
      printf '%s/%s\n' "$PROJECT_ROOT" "${container_path#/var/www/html/}"
      ;;
    *)
      fail "Unexpected DDEV public-files path: $container_path"
      ;;
  esac
}

validate_seed_archive() {
  [[ -s "$FILES_ARCHIVE" ]] || fail "Missing or empty seed-files archive: $FILES_ARCHIVE"

  local bad_entry
  bad_entry="$(tar -tzf "$FILES_ARCHIVE" | awk '
    $0 != "phase0-step9-seed" && $0 !~ /^phase0-step9-seed\// { print; exit }
  ')"
  [[ -z "$bad_entry" ]] || fail "Unsafe or unexpected archive entry: $bad_entry"
}

run_step9_audit() {
  bash scripts/run-phase0-step9.sh audit
}

run_clean_drupal_audit() {
  ddev drush php:script scripts/phase0-step10.php -- audit-clean
}

write_current_manifest() {
  local destination="$1"
  bash scripts/run-phase0-step9.sh manifest > "$destination"
  [[ -s "$destination" ]] || fail "Step 9 produced an empty target manifest."
}

compare_current_manifest() {
  [[ -s "$BASELINE_MANIFEST" ]] || fail "Missing baseline manifest: $BASELINE_MANIFEST"
  local current
  current="$(mktemp)"
  write_current_manifest "$current"
  if ! cmp -s "$BASELINE_MANIFEST" "$current"; then
    warn "Current target manifest differs from the seeded-clean baseline."
    diff -u "$BASELINE_MANIFEST" "$current" || true
    rm -f "$current"
    fail "Manifest comparison failed. Run reset to restore the baseline."
  fi
  rm -f "$current"
  ok "Current 12-target manifest matches the baseline byte-for-byte."
}

verify_checksums() {
  [[ -s "$CHECKSUM_FILE" ]] || fail "Missing checksum file: $CHECKSUM_FILE"
  (cd "$PROJECT_ROOT" && sha256sum -c "../db/$(basename "$CHECKSUM_FILE")")
  ok "Stored snapshot, SQL export, files archive, manifest, and metadata checksums are valid."
}

write_checksums() {
  local snapshot_file="$1"
  local snapshot_rel="${snapshot_file#$PROJECT_ROOT/}"

  (
    cd "$PROJECT_ROOT"
    sha256sum \
      "$snapshot_rel" \
      "../db/$(basename "$DB_DUMP")" \
      "../db/$(basename "$FILES_ARCHIVE")" \
      "../db/$(basename "$BASELINE_MANIFEST")" \
      "../db/$(basename "$METADATA_FILE")" \
      > "../db/$(basename "$CHECKSUM_FILE")"
  )
}

write_metadata() {
  local snapshot_file="$1"
  local seed_dir="$2"
  local ddev_version drush_version drupal_version

  ddev_version="$(ddev version 2>/dev/null | head -n 1 || true)"
  drush_version="$(ddev drush --version 2>/dev/null | head -n 1 || true)"
  drupal_version="$(ddev drush status --field=drupal-version 2>/dev/null | head -n 1 || true)"

  cat > "$METADATA_FILE" <<EOF
step10_script_version=$STEP10_SCRIPT_VERSION
created_at_utc=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
snapshot_name=$SNAPSHOT_NAME
snapshot_file=${snapshot_file#$PROJECT_ROOT/}
database_export=../db/$(basename "$DB_DUMP")
seed_files_archive=../db/$(basename "$FILES_ARCHIVE")
baseline_manifest=../db/$(basename "$BASELINE_MANIFEST")
seed_files_directory=${seed_dir#$PROJECT_ROOT/}
ddev_version=$ddev_version
drush_version=$drush_version
drupal_version=$drupal_version
expected_articles=20
expected_files=30
expected_targets=12
expected_missing_targets=9
expected_poor_targets=3
expected_suggestion_nodes=0
EOF
}

cleanup_failed_create() {
  local exit_code=$?
  set +e
  [[ -n "$CREATE_TEMP_DIR" ]] && rm -rf "$CREATE_TEMP_DIR"
  if [[ "$CREATED_SNAPSHOT" -eq 1 ]]; then
    warn "Create failed after snapshot creation; removing incomplete '${SNAPSHOT_NAME}' snapshot."
    ddev snapshot --cleanup --name "$SNAPSHOT_NAME" >/dev/null 2>&1 || true
  fi
  rm -f "$DB_DUMP.tmp" "$FILES_ARCHIVE.tmp" "$BASELINE_MANIFEST.tmp" "$METADATA_FILE.tmp" "$CHECKSUM_FILE.tmp"
  exit "$exit_code"
}

remove_baseline() {
  info "Removing existing '${SNAPSHOT_NAME}' baseline and private artifacts..."
  if [[ "$(snapshot_count)" -gt 0 ]]; then
    ddev snapshot --cleanup --name "$SNAPSHOT_NAME"
  fi
  rm -f "$DB_DUMP" "$FILES_ARCHIVE" "$BASELINE_MANIFEST" "$METADATA_FILE" "$CHECKSUM_FILE"
  ok "Existing Step 10 baseline removed."
}

create_baseline() {
  require_project
  ensure_private_db_dir

  if baseline_artifacts_exist; then
    fail "A Step 10 baseline or partial artifacts already exist. Use '$0 audit', or intentionally replace them with '$0 replace confirm'."
  fi

  trap cleanup_failed_create ERR INT TERM
  CREATE_TEMP_DIR="$(mktemp -d)"

  info "Running Step 9 deterministic dataset audit..."
  run_step9_audit
  info "Confirming the database contains no suggestion records..."
  run_clean_drupal_audit

  local seed_dir
  seed_dir="$(get_seed_files_dir)"
  [[ -d "$seed_dir" ]] || fail "Missing generated seed directory: $seed_dir"

  write_current_manifest "$CREATE_TEMP_DIR/manifest.json"

  info "Creating DDEV database snapshot '${SNAPSHOT_NAME}'..."
  ddev snapshot --name="$SNAPSHOT_NAME"
  CREATED_SNAPSHOT=1

  local snapshot_file
  snapshot_file="$(get_single_snapshot_file)"
  [[ -s "$snapshot_file" ]] || fail "DDEV created an empty snapshot file: $snapshot_file"

  info "Exporting a portable private database backup..."
  ddev export-db --file="$CREATE_TEMP_DIR/seeded-clean.sql.gz"
  [[ -s "$CREATE_TEMP_DIR/seeded-clean.sql.gz" ]] || fail "DDEV database export is empty."

  info "Archiving deterministic Step 9 public files..."
  tar -C "$(dirname "$seed_dir")" -czf "$CREATE_TEMP_DIR/seeded-clean-files.tar.gz" "$(basename "$seed_dir")"
  [[ -s "$CREATE_TEMP_DIR/seeded-clean-files.tar.gz" ]] || fail "Seed-files archive is empty."

  mv "$CREATE_TEMP_DIR/seeded-clean.sql.gz" "$DB_DUMP"
  mv "$CREATE_TEMP_DIR/seeded-clean-files.tar.gz" "$FILES_ARCHIVE"
  mv "$CREATE_TEMP_DIR/manifest.json" "$BASELINE_MANIFEST"
  write_metadata "$snapshot_file" "$seed_dir"
  write_checksums "$snapshot_file"

  CREATE_TEMP_DIR=""
  CREATED_SNAPSHOT=0
  trap - ERR INT TERM

  audit_baseline
  ok "Step 10 seeded-clean baseline created and verified."
}

audit_stored_artifacts() {
  require_project
  ensure_private_db_dir

  [[ "$(snapshot_count)" -eq 1 ]] || fail "Expected one '${SNAPSHOT_NAME}' DDEV snapshot; found $(snapshot_count)."
  [[ -s "$DB_DUMP" ]] || fail "Missing or empty database export: $DB_DUMP"
  [[ -s "$FILES_ARCHIVE" ]] || fail "Missing or empty seed-files archive: $FILES_ARCHIVE"
  [[ -s "$BASELINE_MANIFEST" ]] || fail "Missing or empty baseline manifest: $BASELINE_MANIFEST"
  [[ -s "$METADATA_FILE" ]] || fail "Missing or empty metadata file: $METADATA_FILE"
  [[ -s "$CHECKSUM_FILE" ]] || fail "Missing or empty checksum file: $CHECKSUM_FILE"

  validate_seed_archive
  verify_checksums
  ok "Stored Step 10 baseline artifacts are complete."
}

audit_baseline() {
  audit_stored_artifacts
  info "Auditing current Drupal state against the stored baseline..."
  run_step9_audit
  run_clean_drupal_audit
  compare_current_manifest
  ok "Step 10 audit passed. Current Drupal state is seeded-clean."
}

restore_seed_files() {
  local seed_dir
  seed_dir="$(get_seed_files_dir)"
  case "$seed_dir" in
    *"/phase0-step9-seed") ;;
    *) fail "Refusing to replace unexpected files directory: $seed_dir" ;;
  esac

  validate_seed_archive
  rm -rf "$seed_dir"
  mkdir -p "$(dirname "$seed_dir")"
  tar -C "$(dirname "$seed_dir")" -xzf "$FILES_ARCHIVE"
  [[ -d "$seed_dir" ]] || fail "Seed-files directory was not restored: $seed_dir"
  ok "Deterministic Step 9 public files restored."
}

reset_baseline() {
  audit_stored_artifacts

  info "Restoring DDEV snapshot '${SNAPSHOT_NAME}'..."
  ddev snapshot restore "$SNAPSHOT_NAME"

  restore_seed_files

  info "Rebuilding Drupal caches..."
  ddev drush cache:rebuild

  info "Verifying restored Drupal state..."
  run_step9_audit
  run_clean_drupal_audit
  compare_current_manifest
  ok "Step 10 reset completed. Database and seed files match seeded-clean."
}

recover_after_failed_test() {
  local exit_code=$?
  trap - ERR INT TERM
  if [[ "$TEST_MUTATED" -eq 1 ]]; then
    warn "Reset test failed after creating drift. Attempting automatic baseline restoration."
    set +e
    reset_baseline
    set -e
  fi
  exit "$exit_code"
}

test_reset() {
  audit_baseline

  trap recover_after_failed_test ERR INT TERM

  info "Creating controlled drift in Article 01, the suggestion queue, and the generated files..."
  ddev drush php:script scripts/phase0-step10.php -- mutate-test
  TEST_MUTATED=1
  ddev drush cache:rebuild >/dev/null
  ddev drush php:script scripts/phase0-step10.php -- assert-mutated

  local seed_dir drift_file
  seed_dir="$(get_seed_files_dir)"
  drift_file="$(find "$seed_dir" -maxdepth 1 -type f -name '*.png' -print -quit)"
  [[ -n "$drift_file" ]] || fail "No generated PNG was available for the reset test."
  rm -f "$drift_file"
  [[ ! -e "$drift_file" ]] || fail "Unable to delete the temporary reset-test file: $drift_file"
  ok "Controlled file drift is present: $(basename "$drift_file") was temporarily removed."

  local drift_log
  drift_log="$(mktemp)"
  if bash scripts/run-phase0-step9.sh audit >"$drift_log" 2>&1; then
    cat "$drift_log"
    rm -f "$drift_log"
    fail "Step 9 audit unexpectedly passed after deliberate drift."
  fi
  rm -f "$drift_log"
  ok "Controlled drift is detectable: the Step 9 audit fails before reset, as expected."

  reset_baseline
  [[ -f "$drift_file" ]] || fail "The deleted generated PNG was not restored: $drift_file"
  ok "The temporarily deleted generated PNG was restored."
  TEST_MUTATED=0
  trap - ERR INT TERM

  audit_baseline
  ok "Step 10 test-reset passed: temporary Article and suggestion changes disappeared."
}

info "Phase 0 Step 10 runner version: $STEP10_SCRIPT_VERSION"

case "$MODE" in
  create)
    create_baseline
    ;;
  audit)
    audit_baseline
    ;;
  reset)
    reset_baseline
    ;;
  test-reset)
    test_reset
    ;;
  replace)
    require_project
    ensure_private_db_dir
    remove_baseline
    create_baseline
    ;;
esac

cat <<EOF

Useful commands:
  bash scripts/run-phase0-step10.sh audit
  bash scripts/run-phase0-step10.sh reset
  bash scripts/run-phase0-step10.sh test-reset

Private baseline artifacts:
  $DB_DUMP
  $FILES_ARCHIVE
  $BASELINE_MANIFEST
  $METADATA_FILE
  $CHECKSUM_FILE
EOF
