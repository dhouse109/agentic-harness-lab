#!/usr/bin/env bash
set -Eeuo pipefail

mode="${1:-audit}"
repo="${2:-}"
[[ -d "$repo/.git" ]] || { printf '[FAIL] repository required\n' >&2; exit 1; }
repo="$(cd "$repo" && pwd -P)"
audit="$repo/scripts/gate2c_final_closure_audit.py"
py="$repo/crewai/.venv/bin/python"

case "$mode" in
  audit)
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
      PYTHONDONTWRITEBYTECODE=1 "$py" "$audit" --repo "$repo" --mode installed
    ;;
  *)
    printf '[FAIL] usage: bash scripts/run-gate2c-final-closure-audit.sh audit REPO\n' >&2
    exit 1
    ;;
esac
