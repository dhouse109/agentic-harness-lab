#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
PYTHON="$REPO/crewai/.venv/bin/python"
ROOT="$REPO/evidence/gates/gate-2b/canonical-slice-closure"
BRANCH="gate-2b-step04-crewai-canonical-vertical-slice"
PREDECESSOR="7629434b04d04154b9f219e1d93ed772401a1288"

fail() { echo "[ERROR] $*" >&2; exit 1; }

capture() {
  [[ "$(git -C "$REPO" branch --show-current)" == "$BRANCH" ]] || fail "Closure capture requires the Step 2B.04 feature branch."
  [[ "$(git -C "$REPO" rev-parse HEAD)" == "$PREDECESSOR" ]] || fail "Closure capture requires the exact uncommitted Step 2B.04 predecessor HEAD."
  [[ "$(git -C "$REPO" rev-parse origin/main)" == "$PREDECESSOR" ]] || fail "origin/main moved since preview."
  [[ ! -e "$ROOT" ]] || fail "Step 2B.04 closure evidence already exists."
  local closure_id output pointer_tmp
  closure_id="$($PYTHON -c 'from datetime import datetime,timezone; import secrets; print("gate2b-step04-closure-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + secrets.token_hex(4))')"
  output="$ROOT/$closure_id"
  env -u OPENAI_API_KEY -u GATE2B_STEP04_LIVE_AUTHORIZED -u GATE2B_LIVE_AUTHORIZED \
    PYTHONDONTWRITEBYTECODE=1 "$PYTHON" "$REPO/scripts/gate2b_step04_capture_closure.py" \
      --repo "$REPO" --output "$output"
  "$PYTHON" -m jsonschema -i "$output/closure-provenance.json" \
    "$REPO/shared/schemas/gate2b-step04-closure-provenance.schema.json"
  pointer_tmp="$ROOT/.LATEST.$closure_id.tmp"
  printf '%s\n' "$closure_id" > "$pointer_tmp"
  mv -- "$pointer_tmp" "$ROOT/LATEST"
  "$PYTHON" "$REPO/scripts/gate2b_step04_audit.py" --repo "$REPO" --phase permanent
  echo "[PASS] Step 2B.04 evidence-preserving closure completed: $closure_id"
}

case "${1:-audit}" in
  capture) capture ;;
  audit) "$PYTHON" "$REPO/scripts/gate2b_step04_audit.py" --repo "$REPO" --phase permanent ;;
  *) fail "Usage: $0 {capture|audit}" ;;
esac
