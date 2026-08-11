#!/usr/bin/env bash
set -Eeuo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cmd="${1:-audit}"
case "$cmd" in
  audit)
    exec python3 "$repo/scripts/gate2a_step09_audit.py" \
      --repo "$repo" --document-state complete --phase permanent
    ;;
  *)
    echo "usage: $0 audit" >&2
    exit 2
    ;;
esac
