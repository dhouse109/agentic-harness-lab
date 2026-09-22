#!/usr/bin/env bash
set -Eeuo pipefail

mode="${1:-}"
repo="${2:-}"
run_id="${3:-}"
[[ -d "$repo/.git" ]] || { echo '[FAIL] repository required' >&2; exit 1; }
repo="$(cd "$repo" && pwd -P)"
py="$repo/crewai/.venv/bin/python"
audit="$repo/scripts/gate2c_step01_audit.py"
rehearsal="$repo/scripts/gate2c_step01_rehearsal.py"
certify="$repo/scripts/gate2c_step01_certify.py"

case "$mode" in
  rehearse)
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
      PYTHONDONTWRITEBYTECODE=1 "$py" "$rehearsal" --repo "$repo" --payload "$repo"
    ;;
  certify)
    [[ "${GATE2C_STEP01_MODEL_FREE_AUTHORIZED:-}" == "certify-planning-contract-once" ]] || {
      echo '[FAIL] explicit model-free certification authorization token required' >&2; exit 1;
    }
    [[ -n "$run_id" ]] || { echo '[FAIL] certification run ID required' >&2; exit 1; }
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
      PYTHONDONTWRITEBYTECODE=1 "$py" "$audit" --repo "$repo" --mode permanent
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
      PYTHONDONTWRITEBYTECODE=1 "$py" "$rehearsal" --repo "$repo" --payload "$repo"
    evidence_rel="$(PYTHONDONTWRITEBYTECODE=1 "$py" "$certify" --repo "$repo" --run-id "$run_id")"
    PYTHONDONTWRITEBYTECODE=1 "$py" "$audit" --repo "$repo" --mode permanent --evidence "$repo/$evidence_rel"
    echo '[STOP] Step 2C.01 certified model-free; Gate 2C remains DEFERRED_UNCLAIMED; nothing staged.'
    ;;
  audit)
    pointer="$repo/evidence/gates/gate-2c/contract/GATE2C-STEP01-LATEST.txt"
    if [[ -f "$pointer" ]]; then
      evidence_rel="$(<"$pointer")"
      PYTHONDONTWRITEBYTECODE=1 "$py" "$audit" --repo "$repo" --mode permanent --evidence "$repo/$evidence_rel"
    else
      PYTHONDONTWRITEBYTECODE=1 "$py" "$audit" --repo "$repo" --mode permanent
    fi
    ;;
  *)
    echo "usage: $0 {rehearse|certify|audit} REPO [RUN_ID]" >&2
    exit 1
    ;;
esac
