#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

case "$MODE" in
  audit)
    "$ROOT/crewai/.venv/bin/python" "$ROOT/scripts/gate1_step04_file_transport_clarification_audit.py" --repo "$ROOT"
    ;;
  *)
    printf 'Usage: bash scripts/run-gate1-step04-file-transport-clarification.sh audit\n' >&2
    exit 1
    ;;
esac
