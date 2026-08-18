#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)" || {
  echo "[ERROR] Unable to resolve script directory." >&2
  exit 1
}
REPO="$(cd -- "$SCRIPT_DIR/.." && pwd -P)" || {
  echo "[ERROR] Unable to resolve repository root." >&2
  exit 1
}
PYTHON="$REPO/crewai/.venv/bin/python"
EVIDENCE_ROOT="$REPO/evidence/gates/gate-2b/shared-operation-adapters"

mode="${1:-audit}"
case "$mode" in
  run)
    forbidden=(
      OPENAI_API_KEY GATE2B_LIVE_AUTHORIZED GATE2B_DRUPAL_BASE_URL
      GATE2B_DRUPAL_BASIC_AUTH_USER GATE2B_DRUPAL_BASIC_AUTH_PASSWORD
      DRUPAL_BASE_URL DRUPAL_BASIC_AUTH_USER DRUPAL_BASIC_AUTH_PASSWORD
    )
    for name in "${forbidden[@]}"; do
      if [[ -n "${!name:-}" ]]; then
        echo "[ERROR] Refusing model-free proof while $name is set." >&2
        exit 1
      fi
    done
    if [[ ! -x "$PYTHON" ]]; then
      echo "[ERROR] Pinned CrewAI Python is unavailable: $PYTHON" >&2
      exit 1
    fi
    mkdir -p -- "$EVIDENCE_ROOT"
    run_id="$($PYTHON -c 'from datetime import datetime, timezone; import uuid; print("gate2b-step03-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8])')" || {
      echo "[ERROR] Unable to generate a unique run id." >&2
      exit 1
    }
    run_dir="$EVIDENCE_ROOT/$run_id"
    CREWAI_DISABLE_VERSION_CHECK=true "$PYTHON" "$REPO/scripts/gate2b_step03_adapter_proof.py" \
      --repo "$REPO" --output "$run_dir" --run-id "$run_id"
    "$PYTHON" -m jsonschema \
      -i "$run_dir/summary.json" \
      "$REPO/shared/schemas/gate2b-step03-adapter-evidence.schema.json"
    "$PYTHON" "$REPO/scripts/gate2b_step03_state.py" \
      --repo "$REPO" --state complete --run-id "$run_id"
    pointer_tmp="$EVIDENCE_ROOT/.LATEST.$run_id.tmp"
    printf '%s\n' "$run_id" > "$pointer_tmp"
    mv -- "$pointer_tmp" "$EVIDENCE_ROOT/LATEST"
    "$PYTHON" "$REPO/scripts/gate2b_step03_audit.py" --repo "$REPO" --phase permanent
    echo "[PASS] Step 2B.03 model-free evidence run complete: $run_id"
    ;;
  audit)
    "$PYTHON" "$REPO/scripts/gate2b_step03_audit.py" --repo "$REPO" --phase permanent
    ;;
  active-audit)
    "$PYTHON" "$REPO/scripts/gate2b_step03_audit.py" --repo "$REPO" --phase active
    ;;
  *)
    echo "Usage: $0 {run|audit|active-audit}" >&2
    exit 2
    ;;
esac
