#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE_ROOT="$ROOT/evidence/gates/gate-1/step04-boundary-reconciliation"
RUN_ID="gate1-step04-boundary-reconciliation-$(date -u +%Y%m%dT%H%M%SZ)-$$"
umask 077
fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }
audit_static() {
  "$ROOT/crewai/.venv/bin/python" "$ROOT/scripts/gate1_step04_boundary_reconciliation_audit.py" --repo "$ROOT"
}
predecessors() {
  local out="$1"
  (cd "$ROOT" && bash scripts/run-gate05-step05.sh audit) >"$out/gate05-audit.log"
  (cd "$ROOT" && bash scripts/run-gate1-step01.sh audit) >"$out/step01-audit.log"
  (cd "$ROOT" && crewai/.venv/bin/python scripts/gate1_step01_progression_regression.py --repo "$ROOT" --auditor "$ROOT/scripts/gate1_step01_audit.py") >"$out/compatibility-audit.json"
  (cd "$ROOT" && crewai/.venv/bin/python scripts/gate1_step02_audit.py --repo "$ROOT" --run-dir "$ROOT/evidence/gates/gate-1/drupal-ai-runtime-probe/gate1-step02-20260806T010227Z-189538") >"$out/step02-audit.json"
  (cd "$ROOT" && crewai/.venv/bin/python scripts/gate1_step03_audit.py --repo "$ROOT" --run-dir "$ROOT/evidence/gates/gate-1/drupal-ai-tool-adapters/gate1-step03-20260806T050827Z-494925") >"$out/step03-audit.json"
}
case "$MODE" in
  audit)
    audit_static
    pointer="$EVIDENCE_ROOT/GATE1-STEP04-BOUNDARY-RECONCILIATION-LATEST.txt"
    [[ -s "$pointer" ]] || fail 'Missing accepted reconciliation evidence pointer.'
    run_dir="$ROOT/$(<"$pointer")"
    "$ROOT/crewai/.venv/bin/python" "$ROOT/scripts/gate1_step04_boundary_reconciliation_audit.py" --repo "$ROOT" --run-dir "$run_dir"
    ;;
  run)
    tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
    predecessors "$tmp"
    audit_static >"$tmp/boundary-audit.json"
    (cd "$ROOT/drupal" && ddev drush --quiet php:script scripts/gate1-step04-wrapper-boundary-probe.php) >"$tmp/wrapper-probe.json"
    rg -n 'public function determineSolvability|aiProvider->chat|public function solve|allRequiredToolsRan|setChatTools' "$ROOT/drupal/web/modules/contrib/ai_agents/src/PluginBase/AiAgentEntityWrapper.php" >"$tmp/provider-request-source.txt"
    cp "$ROOT/docs/gates/GATE-1-STEP04-BOUNDARY-RECONCILIATION.md" "$tmp/conflicts-and-boundary.md"
    "$ROOT/crewai/.venv/bin/python" - "$tmp" <<'PY'
import json, sys
from pathlib import Path
d=Path(sys.argv[1])
summary={'schema_version':1,'status':'pass','model_call_performed':False,'provider_request_count':0,'network_call_performed':False,'api_credit_used':False,'drupal_mutation':False,'one_provider_request_maximum':1,'automatic_retries':0,'wrapper_checkpoint':'pre_image_safe_and_restorable','step04_implementation_started':False,'step05_started':False,'status_documents_changed':False}
(d/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
(d/'summary.md').write_text('# Gate 1 Step 1.04 Boundary Reconciliation\n\n- Status: PASS\n- One-provider-request maximum: 1\n- Wrapper checkpoint: pre-image only, safe and restorable\n- Model/provider/network/API/Drupal mutation: none\n')
PY
    (cd "$ROOT" && sha256sum docs/decisions/ADR-0007-canonical-slice-evidence-image-and-state-boundary.md docs/gates/GATE-1-STEP04-BOUNDARY-RECONCILIATION.md shared/profiles/gate1-drupal-ai-canonical-slice-v1.0.0/* scripts/gate1_step04_boundary_reconciliation_audit.py scripts/run-gate1-step04-boundary-reconciliation.sh | sed 's#  #  ./#' >"$tmp/installed-files-sha256.txt")
    cp "$tmp/installed-files-sha256.txt" "$tmp/package-files-sha256.txt"
    (cd "$tmp" && find . -maxdepth 1 -type f ! -name retained-evidence-sha256.txt -print0 | sort -z | xargs -0 sha256sum > retained-evidence-sha256.txt)
    mkdir -p "$EVIDENCE_ROOT"
    final="$EVIDENCE_ROOT/$RUN_ID"; [[ ! -e "$final" ]] || fail 'Evidence path already exists.'
    mv "$tmp" "$final"; trap 'rm -rf "$final"' EXIT
    "$ROOT/crewai/.venv/bin/python" "$ROOT/scripts/gate1_step04_boundary_reconciliation_audit.py" --repo "$ROOT" --run-dir "$final" >/dev/null
    printf '%s\n' "${final#"$ROOT/"}" >"$EVIDENCE_ROOT/GATE1-STEP04-BOUNDARY-RECONCILIATION-LAST-RUN.txt"
    printf '%s\n' "${final#"$ROOT/"}" >"$EVIDENCE_ROOT/GATE1-STEP04-BOUNDARY-RECONCILIATION-LATEST.txt"
    trap - EXIT
    printf '[PASS] Reconciliation evidence promoted: %s\n' "${final#"$ROOT/"}"
    ;;
  *)
    echo 'Usage: bash scripts/run-gate1-step04-boundary-reconciliation.sh audit|run' >&2
    exit 1
    ;;
esac
