#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)" || {
  echo "[ERROR] Unable to resolve script directory." >&2
  exit 1
}
REPO="$(cd -- "$SCRIPT_DIR/.." && pwd -P)" || {
  echo "[ERROR] Unable to resolve repository root." >&2
  exit 1
}
PYTHON="$REPO/crewai/.venv/bin/python"
EVIDENCE_ROOT="$REPO/evidence/gates/gate-2b/canonical-slice"
RUNTIME_ROOT="$REPO/crewai/.runtime/gate2b-step04"
PREDECESSOR="7629434b04d04154b9f219e1d93ed772401a1288"
FEATURE_BRANCH="gate-2b-step04-crewai-canonical-vertical-slice"

fail() { echo "[ERROR] $*" >&2; exit 1; }

repo_python() {
  PYTHONPATH="$REPO/crewai:$REPO${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" "$@"
}

verify_active_lifecycle() {
  [[ "$(git -C "$REPO" branch --show-current)" == "$FEATURE_BRANCH" ]] || fail "Live run requires the exact Step 2B.04 feature branch."
  [[ "$(git -C "$REPO" rev-parse HEAD)" == "$PREDECESSOR" ]] || fail "Live run requires the exact merged Step 2B.03 predecessor."
  [[ "$(git -C "$REPO" rev-parse origin/main)" == "$PREDECESSOR" ]] || fail "origin/main moved."
  repo_python "$REPO/scripts/gate2b_step04_audit.py" --repo "$REPO" --phase active
  [[ ! -e "$EVIDENCE_ROOT" ]] || fail "A Step 2B.04 evidence attempt already exists; automatic rerun is prohibited."
  [[ ! -e "$RUNTIME_ROOT" ]] || fail "Step 2B.04 runtime storage already exists."
}

run_rehearsal() {
  local temp
  temp="$(mktemp -d)" || fail "Unable to allocate rehearsal directory."
  trap 'rm -rf -- "$temp"' RETURN
  CREWAI_DISABLE_VERSION_CHECK=true PYTHONDONTWRITEBYTECODE=1 \
    repo_python "$REPO/scripts/gate2b_step04_canonical_slice.py" \
      --repo "$REPO" --mode rehearse --work-root "$temp"
  echo "[PASS] Step 2B.04 disposable model-free rehearsal passed."
}

run_live() {
  verify_active_lifecycle
  [[ "${GATE2B_STEP04_LIVE_AUTHORIZED:-}" == "one-provider-request-one-live-submission" ]] || \
    fail "Set the exact approved Step 2B.04 live authorization token."
  local run_id run_dir
  run_id="$(repo_python -c 'from datetime import datetime,timezone; import secrets; print("crewai-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + secrets.token_hex(4))')" || \
    fail "Unable to allocate logical run ID."
  run_dir="$EVIDENCE_ROOT/$run_id"
  mkdir -p -- "$EVIDENCE_ROOT" "$RUNTIME_ROOT"
  CREWAI_DISABLE_VERSION_CHECK=true CREWAI_DISABLE_TELEMETRY=true CREWAI_DISABLE_TRACKING=true \
    CREWAI_TRACING_ENABLED=false OTEL_SDK_DISABLED=true PYTHONDONTWRITEBYTECODE=1 \
    repo_python "$REPO/scripts/gate2b_step04_canonical_slice.py" --repo "$REPO" --mode run \
      --output "$run_dir" --run-id "$run_id" --runtime-root "$RUNTIME_ROOT"
  repo_python -m jsonschema -i "$run_dir/summary.json" \
    "$REPO/shared/schemas/gate2b-step04-canonical-slice-evidence.schema.json"
  repo_python "$REPO/scripts/gate2b_step04_audit.py" --repo "$REPO" --phase permanent --evidence "$run_dir"
  repo_python "$REPO/scripts/gate2b_step04_state.py" --repo "$REPO" --state complete --run-id "$run_id"
  printf '%s\n' "$run_id" > "$EVIDENCE_ROOT/.LATEST.$run_id.tmp"
  mv -- "$EVIDENCE_ROOT/.LATEST.$run_id.tmp" "$EVIDENCE_ROOT/LATEST"
  repo_python "$REPO/scripts/gate2b_step04_audit.py" --repo "$REPO" --phase permanent
  echo "[PASS] Step 2B.04 canonical slice retained: $run_id"
  echo "[STOP] Recommendation awaits Drupal-authoritative review; continuation remains unbegun."
}

mode="${1:-audit}"
case "$mode" in
  rehearse) run_rehearsal ;;
  run) run_live ;;
  active-audit) repo_python "$REPO/scripts/gate2b_step04_audit.py" --repo "$REPO" --phase active ;;
  audit) repo_python "$REPO/scripts/gate2b_step04_audit.py" --repo "$REPO" --phase permanent ;;
  *) fail "Usage: $0 {rehearse|run|active-audit|audit}" ;;
esac
