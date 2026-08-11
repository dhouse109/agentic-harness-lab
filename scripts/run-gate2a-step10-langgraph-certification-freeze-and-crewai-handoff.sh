#!/usr/bin/env bash
set -Eeuo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cmd="${1:-audit}"
case "$cmd" in
  audit)
    exec python3 "$repo/scripts/gate2a_step10_audit.py" --repo "$repo"
    ;;
  *)
    echo "usage: $0 audit" >&2
    exit 2
    ;;
esac
