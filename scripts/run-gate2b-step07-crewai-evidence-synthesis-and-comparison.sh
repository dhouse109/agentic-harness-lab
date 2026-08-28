#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-}"
REPO="${2:-$(pwd)}"
RUN_ID="${3:-}"
PYTHON="${REPO}/crewai/.venv/bin/python"
ROOT="${REPO}/evidence/gates/gate-2b/evidence-synthesis"
CONSUMED_RUN="gate2b-step07-20260828T135201Z-1ed07bea"
CONSUMED_REL="evidence/gates/gate-2b/evidence-synthesis/${CONSUMED_RUN}"
POINTER="${ROOT}/GATE2B-STEP07-LATEST.txt"

fail() { printf '[FAIL] %s\n' "$*" >&2; exit 1; }

unset OPENAI_API_KEY OPENAI_CANDIDATE_MODEL CREWAI_CANDIDATE_MODEL
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$REPO/scripts:$REPO/crewai:$REPO${PYTHONPATH:+:$PYTHONPATH}"

case "$MODE" in
  rehearse)
    [[ -n "${GATE2B_STEP07_PACKAGE_PAYLOAD:-}" ]] || fail "Set GATE2B_STEP07_PACKAGE_PAYLOAD to the package payload."
    exec python3 "$GATE2B_STEP07_PACKAGE_PAYLOAD/scripts/gate2b_step07_rehearsal.py" \
      --repo "$REPO" --payload "$GATE2B_STEP07_PACKAGE_PAYLOAD"
    ;;
  recover-acceptance)
    [[ "${GATE2B_STEP07_RECOVERY_AUTHORIZED:-}" == "accept-existing-consumed-synthesis-v101" ]] ||
      fail "Exact Step 2B.07 recovery/acceptance authorization token is required."
    [[ "$RUN_ID" == "$CONSUMED_RUN" ]] || fail "Only the consumed v1.0.0 synthesis identity may be accepted."
    [[ -d "$REPO/$CONSUMED_REL" ]] || fail "Consumed synthesis family is missing."
    [[ ! -e "$POINTER" ]] || fail "Authoritative pointer exists before repaired acceptance."
    "$PYTHON" "$REPO/scripts/gate2b_step07_audit.py" --repo "$REPO" \
      --mode recovery --evidence "$REPO/$CONSUMED_REL"
    pointer_tmp="$ROOT/.GATE2B-STEP07-LATEST.${CONSUMED_RUN}.tmp"
    printf '%s\n' "$CONSUMED_REL" >"$pointer_tmp"
    mv -- "$pointer_tmp" "$POINTER"
    "$PYTHON" "$REPO/scripts/gate2b_step07_audit.py" --repo "$REPO" --mode permanent
    printf '[PASS] STEP_2B_07_COMPLETE / EVIDENCE_SYNTHESIS_ACCEPTED / CLAIM_PROOF_COVERAGE_PASS\n'
    printf '[STOP] Step 2B.08, Gate 2C, snapshot cleanup, and Git staging remain unauthorized.\n'
    ;;
  audit)
    exec "$PYTHON" "$REPO/scripts/gate2b_step07_audit.py" --repo "$REPO" --mode permanent
    ;;
  historical-gate2a)
    exec "$PYTHON" "$REPO/scripts/gate2b_step07_audit.py" --repo "$REPO" --mode historical-gate2a
    ;;
  gate2a-preservation)
    exec "$PYTHON" "$REPO/scripts/gate2b_step07_audit.py" --repo "$REPO" --mode gate2a-preservation
    ;;
  run)
    fail "Synthesis run mode is permanently disabled; v1.0.0 consumed the one authorized identity."
    ;;
  *)
    fail "Usage: $0 {rehearse|recover-acceptance|audit|historical-gate2a|gate2a-preservation} REPO [consumed-run-id]"
    ;;
esac
