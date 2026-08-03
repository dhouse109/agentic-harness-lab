#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LAB_ROOT="$(cd "$PROJECT_ROOT/.." && pwd)"
TEST_RUNNER="$LAB_ROOT/evidence/tests/run-step12-revisions.sh"

if [[ ! -f "$TEST_RUNNER" ]]; then
  echo "ERROR: Missing $TEST_RUNNER" >&2
  echo "Copy the Step 12 evidence/tests files into the lab root first." >&2
  exit 1
fi

exec bash "$TEST_RUNNER" "$@"
