#!/usr/bin/env bash
set -euo pipefail

STEP14_SCRIPT_VERSION="1.1.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AUDIT_PY="$SCRIPT_DIR/step14_audit.py"
MANIFEST_REL="docs/decisions/step14-contract-sha256.txt"

usage() {
  cat <<'USAGE'
Phase 0 Step 14/16 — frozen experiment contract audit

Usage:
  bash scripts/run-phase0-step14.sh audit
  bash scripts/run-phase0-step14.sh status

The original Step 14 apply/freeze workflow is complete and retained in Git history. ADR-0002
amended the frozen contract to version 1.1 after the Step 16 capability spike.
USAGE
}

case "${1:-}" in
  audit)
    python3 "$AUDIT_PY" "$PROJECT_ROOT"
    (cd "$PROJECT_ROOT" && sha256sum -c "$MANIFEST_REL")
    echo "[OK] Frozen experiment contract SHA-256 manifest is valid."
    ;;
  status)
    echo "Phase 0 contract runner version: $STEP14_SCRIPT_VERSION"
    echo "Contract state: frozen version 1.1, amended by ADR-0002 after Step 16"
    echo "Manifest: $PROJECT_ROOT/$MANIFEST_REL"
    ;;
  apply|freeze)
    echo "[ERROR] The version 1.1 contract is already frozen. Restore an earlier Git commit to repeat the Step 14 apply/freeze workflow." >&2
    exit 1
    ;;
  -h|--help|help|"") usage ;;
  *) usage; exit 2 ;;
esac
