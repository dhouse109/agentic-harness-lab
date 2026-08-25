#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)" || exit 1
REPO="$(cd -- "$SCRIPT_DIR/.." && pwd -P)" || exit 1
PYTHON="$REPO/crewai/.venv/bin/python"
PREDECESSOR="c61d0b0213d754fcc40f18065836de6e0da70d2c"
FEATURE_BRANCH="gate-2b-step05-crewai-drupal-authoritative-human-review-continuation"
FAILED_V100_ID="gate2b-step05-20260820T151225Z-8b7fa221"

fail() { echo "[ERROR] $*" >&2; exit 1; }
repo_python() { PYTHONPATH="$REPO/crewai:$REPO${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" "$@"; }

normal_local_environment() {
  local xdg_root="$1"
  export CREWAI_DISABLE_VERSION_CHECK=true CREWAI_DISABLE_TELEMETRY=true
  export CREWAI_DISABLE_TRACKING=true CREWAI_TRACING_ENABLED=false OTEL_SDK_DISABLED=true
  export PYTHONDONTWRITEBYTECODE=1
  mkdir -p -- "$xdg_root/data" "$xdg_root/config" "$xdg_root/cache"
  export XDG_DATA_HOME="$xdg_root/data"
  export XDG_CONFIG_HOME="$xdg_root/config"
  export XDG_CACHE_HOME="$xdg_root/cache"
}

require_ancestry() {
  git -C "$REPO" merge-base --is-ancestor "$PREDECESSOR" HEAD || fail "Step 2B.04 predecessor is not an ancestor."
  [[ "$(git -C "$REPO" rev-parse origin/main)" == "$PREDECESSOR" ]] || fail "origin/main moved."
}

run_rehearsal() {
  local work
  work="$(mktemp -d)" || fail "Unable to create disposable rehearsal root."
  trap 'rm -rf -- "$work"' RETURN
  normal_local_environment "$work"
  export CREWAI_TESTING=true
  repo_python "$REPO/scripts/gate2b_step05_rehearsal.py" --repo "$REPO" --work-root "$work"
  echo "[PASS] Normal-local, model-free Step 2B.05 disposable rehearsal passed."
}

run_process_a() {
  require_ancestry
  [[ "$(git -C "$REPO" branch --show-current)" == "$FEATURE_BRANCH" ]] || fail "Process A requires the Step 2B.05 feature branch."
  [[ "${GATE2B_STEP05_PROCESS_A_AUTHORIZED:-}" == "copy-source-runtime-and-create-supported-pending-boundary" ]] || \
    fail "Exact Process A authorization token is required."
  local continuation_id runtime evidence xdg_root rc
  continuation_id="${1:-$(repo_python -c 'from datetime import datetime,timezone; import secrets; print("gate2b-step05-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")+secrets.token_hex(4))')}"
  [[ "$continuation_id" =~ ^gate2b-step05-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}$ ]] || \
    fail "Continuation ID format is invalid."
  [[ "$continuation_id" != "$FAILED_V100_ID" ]] || fail "The consumed v1.0.0 continuation ID may not be reused."
  runtime="$REPO/crewai/.runtime/gate2b-step05/$continuation_id"
  evidence="$REPO/evidence/gates/gate-2b/human-review-continuation/$continuation_id"
  [[ ! -e "$runtime" && ! -e "$evidence" ]] || fail "Fresh continuation runtime/evidence identity is required."
  xdg_root="$(mktemp -d "/tmp/gate2b-step05-xdg-${continuation_id}.XXXXXX")" || \
    fail "Unable to allocate disposable XDG storage."
  trap 'rm -rf -- "$xdg_root"' RETURN
  normal_local_environment "$xdg_root"
  unset CREWAI_TESTING
  set +e
  repo_python "$REPO/scripts/gate2b_step05_continuation.py" validate-paths --repo "$REPO" \
    --continuation-id "$continuation_id" --xdg-root "$xdg_root"
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    repo_python "$REPO/scripts/gate2b_step05_continuation.py" record-failure --repo "$REPO" \
      --continuation-id "$continuation_id" --failure-stage xdg-runtime-path-validation \
      --failure-classification boundary-a-wrapper-preflight-failure --error-type RuntimeError
    fail "XDG/runtime canonical-path validation failed; immutable failure evidence retained."
  fi
  [[ ! -e "$runtime" ]] || fail "Runtime candidate appeared before Process A initialization."
  set +e
  repo_python "$REPO/scripts/gate2b_step05_continuation.py" process-a --repo "$REPO" \
    --continuation-id "$continuation_id" --xdg-root "$xdg_root"
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    rm -rf -- "$xdg_root"
    trap - RETURN
    fail "Process A failed; its continuation identity is consumed and failure evidence was retained."
  fi
  repo_python "$REPO/scripts/gate2b_step05_audit.py" --repo "$REPO" --phase stage-a \
    --evidence "$REPO/evidence/gates/gate-2b/human-review-continuation/$continuation_id"
  rm -rf -- "$xdg_root"
  trap - RETURN
  echo "[PASS] Process A retained: $continuation_id"
  echo "[STOP] No human review or Process B was performed."
}

capture_review() {
  require_ancestry
  [[ "${GATE2B_STEP05_REVIEW_OBSERVATION_AUTHORIZED:-}" == "observe-separately-approved-editor-dana-review" ]] || \
    fail "Exact post-review observation authorization token is required."
  [[ -n "${1:-}" ]] || fail "Continuation ID is required."
  repo_python "$REPO/scripts/gate2b_step05_continuation.py" capture-review --repo "$REPO" --continuation-id "$1"
  echo "[PASS] Existing Drupal review was observed read-only; this command did not perform it."
  echo "[STOP] Process B remains separately unauthorized."
}

run_process_b() {
  require_ancestry
  [[ "${GATE2B_STEP05_PROCESS_B_AUTHORIZED:-}" == "from-pending-resume-after-authoritative-review" ]] || \
    fail "Exact Process B authorization token is required."
  [[ -n "${1:-}" ]] || fail "Continuation ID is required."
  local runtime="$REPO/crewai/.runtime/gate2b-step05/$1" xdg_root
  xdg_root="$(mktemp -d "/tmp/gate2b-step05-xdg-$1.XXXXXX")" || \
    fail "Unable to allocate disposable XDG storage."
  trap 'rm -rf -- "$xdg_root"' RETURN
  normal_local_environment "$xdg_root"
  unset CREWAI_TESTING
  local rc
  set +e
  repo_python "$REPO/scripts/gate2b_step05_continuation.py" process-b --repo "$REPO" --continuation-id "$1"
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    rm -rf -- "$xdg_root"
    trap - RETURN
    fail "Process B failed; immutable failure evidence was retained."
  fi
  printf '%s\n' "$1" > "$REPO/evidence/gates/gate-2b/human-review-continuation/LATEST"
  repo_python "$REPO/scripts/gate2b_step05_audit.py" --repo "$REPO" --phase permanent
  rm -rf -- "$xdg_root"
  trap - RETURN
  echo "[PASS] Process B same-Flow continuation retained: $1"
}

mode="${1:-audit}"
case "$mode" in
  rehearse) [[ $# -eq 1 ]] || fail "Usage: $0 rehearse"; run_rehearsal ;;
  process-a) [[ $# -le 2 ]] || fail "Usage: $0 process-a [continuation-id]"; run_process_a "${2:-}" ;;
  capture-review) [[ $# -eq 2 ]] || fail "Usage: $0 capture-review <continuation-id>"; capture_review "$2" ;;
  process-b) [[ $# -eq 2 ]] || fail "Usage: $0 process-b <continuation-id>"; run_process_b "$2" ;;
  active-audit) repo_python "$REPO/scripts/gate2b_step05_audit.py" --repo "$REPO" --phase active ;;
  stage-a-audit) [[ $# -eq 2 ]] || fail "Usage: $0 stage-a-audit <continuation-id>"; \
    repo_python "$REPO/scripts/gate2b_step05_audit.py" --repo "$REPO" --phase stage-a \
      --evidence "$REPO/evidence/gates/gate-2b/human-review-continuation/$2" ;;
  audit) repo_python "$REPO/scripts/gate2b_step05_audit.py" --repo "$REPO" --phase permanent ;;
  *) fail "Usage: $0 {rehearse|process-a [id]|capture-review id|process-b id|active-audit|stage-a-audit id|audit}" ;;
esac
