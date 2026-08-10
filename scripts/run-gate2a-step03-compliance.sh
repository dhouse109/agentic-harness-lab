#!/usr/bin/env bash
set -Eeuo pipefail
MODE="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
DRUPAL="$REPO/drupal"
PYTHON="$REPO/langchain/.venv/bin/python"
VALIDATOR_PYTHON="$REPO/crewai/.venv/bin/python"
VERIFY="$REPO/scripts/gate2a_step03_compliance_verify.py"
AUDITOR="$REPO/scripts/gate2a_step03_audit.py"
STATE="$REPO/scripts/gate2a_step03_compliance_state.py"
EVIDENCE_ROOT="$REPO/evidence/gates/gate-2a/tool-adapters"
CREDENTIALS="$DRUPAL/.secrets/phase0-step7-accounts.txt"
LIVE_PTR="evidence/gates/gate-2a/tool-adapters/gate2a-step03-20260809T233127Z-2375581"

fail(){ printf '[ERROR] %s\n' "$*" >&2; exit 1; }
pass(){ printf '[PASS] %s\n' "$*"; }
info(){ printf '[INFO] %s\n' "$*"; }

latest_secret(){
  local key="$1"
  awk -v key="$key" 'index($0,key "=")==1 {v=substr($0,length(key)+2)} END{if(v!="")print v}' "$CREDENTIALS"
}
resolve_site_url(){
  local v
  v="$(cd "$DRUPAL" && ddev exec printenv DDEV_PRIMARY_URL 2>/dev/null | tr -d '\r' | grep -Eo 'https?://[^[:space:]]+' | tail -n1 || true)"
  [[ -n "$v" ]] || fail "Unable to resolve DDEV_PRIMARY_URL"
  printf '%s' "${v%/}"
}
snapshot_state(){
  local out="$1"
  (cd "$DRUPAL" && env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
    ddev drush --quiet php:script scripts/gate1-step03-adapter-exercise.php -- snapshot) >"$out"
}
write_manifest(){
  local d="$1"
  (cd "$d" && find . -maxdepth 1 -type f ! -name package-files-sha256.txt -printf '%f\n' | sort | xargs -r sha256sum >package-files-sha256.txt)
}

case "$MODE" in
  run)
    [[ "$(tr -d '\r\n' < "$EVIDENCE_ROOT/GATE2A-STEP03-LATEST.txt")" == "$LIVE_PTR" ]] || fail "Accepted live run pointer changed"
    [[ ! -e "$EVIDENCE_ROOT/GATE2A-STEP03-VERIFICATION-LATEST.txt" ]] || fail "Accepted compliance verification already exists"
    "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state verification >/dev/null
    bash "$REPO/scripts/run-gate1-step07-drupal-ai-certification-and-handoff.sh" audit >/dev/null
    bash "$REPO/scripts/run-gate05-step05.sh" audit >/dev/null

    # Fail before credentials or HTTP calls if the dedicated schema-validator
    # interpreter cannot import jsonschema or validate the frozen tool-result schema.
    printf '%s\n' '{"schema_version":1,"tool_name":"find_images_needing_review","ok":false,"timestamp":"2026-08-10T00:00:00Z","correlation_id":"gate2a-step03-schema-smoke","data":null,"error":{"code":"SMOKE","message":"Synthetic schema smoke test.","retryable":false}}' \
      | "$VALIDATOR_PYTHON" "$REPO/scripts/gate2a_step03_schema_validate.py" \
          --schema-dir "$REPO/shared/schemas" \
          --schema tool-result.schema.json \
          >/dev/null \
      || fail "Schema-validator interpreter/preflight failed before HTTP activity"
    info "Schema-validator interpreter and frozen tool-result schema preflight passed."

    [[ -f "$CREDENTIALS" ]] || fail "Credentials file missing"
    agent="$(latest_secret agent_bot)"; editor="$(latest_secret editor_dana)"
    [[ -n "$agent" && -n "$editor" ]] || fail "Required local account credential missing"

    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"; unset GATE2A_AGENT_PASSWORD GATE2A_EDITOR_PASSWORD GATE2A_DRUPAL_BASE_URL' EXIT
    snapshot_state "$tmp/before.json"
    "$PYTHON" - "$tmp/before.json" <<'PY'
import json,sys
v=json.load(open(sys.argv[1],encoding="utf-8"))
if v.get("seeded_clean") is not True or v.get("suggestion_count") != 0:
    raise SystemExit("[ERROR] Compliance verification requires seeded-clean with zero suggestions")
PY

    run_id="gate2a-step03-verification-$(date -u +%Y%m%dT%H%M%SZ)-$$"
    run_dir="$EVIDENCE_ROOT/$run_id"
    mkdir -p "$run_dir"
    export GATE2A_DRUPAL_BASE_URL="$(resolve_site_url)"
    export GATE2A_AGENT_PASSWORD="$agent"
    export GATE2A_EDITOR_PASSWORD="$editor"

    set +e
    "$PYTHON" "$VERIFY" --repo "$REPO" --evidence "$run_dir" --run-id "$run_id" --validator-python "$VALIDATOR_PYTHON"
    rc=$?
    set -e
    unset GATE2A_AGENT_PASSWORD GATE2A_EDITOR_PASSWORD GATE2A_DRUPAL_BASE_URL
    snapshot_state "$tmp/after.json"

    if [[ "$rc" -ne 0 ]]; then
      printf '%s\n' "${run_dir#"$REPO/"}" >"$EVIDENCE_ROOT/GATE2A-STEP03-VERIFICATION-LAST-RUN.txt"
      printf '[STOP] Compliance verification failed; evidence retained at %s. Do not rerun without review.\n' "${run_dir#"$REPO/"}"
      exit "$rc"
    fi

    "$PYTHON" - "$tmp/before.json" "$tmp/after.json" "$run_dir/source-before-after.json" "$run_dir/summary.json" <<'PY'
import json,sys
before=json.load(open(sys.argv[1],encoding="utf-8"))
after=json.load(open(sys.argv[2],encoding="utf-8"))
keys=["article_count","suggestion_count","target_count","target_sequence_sha256",
      "canonical_target_sequence","canonical_target_identity_sha256",
      "article_source_sha256","step03_extended_article_source_sha256",
      "gate05_certification_article_source_sha256","seeded_clean","module_enabled"]
same=all(before.get(k)==after.get(k) for k in keys)
proof={
  "schema_version":1,"status":"pass" if same else "fail",
  "source_state_unchanged":same,
  "suggestion_count_before":before.get("suggestion_count"),
  "suggestion_count_after":after.get("suggestion_count"),
  "target_sequence_sha256_before":before.get("target_sequence_sha256"),
  "target_sequence_sha256_after":after.get("target_sequence_sha256"),
  "article_source_sha256_before":before.get("article_source_sha256"),
  "article_source_sha256_after":after.get("article_source_sha256"),
  "raw_state_retained":False,
}
if not same or proof["suggestion_count_before"]!=0 or proof["suggestion_count_after"]!=0:
    raise SystemExit("[ERROR] Compliance verification changed Drupal source/recommendation state")
open(sys.argv[3],"w",encoding="utf-8").write(json.dumps(proof,indent=2,sort_keys=True)+"\n")
summary=json.load(open(sys.argv[4],encoding="utf-8"))
summary["source_state_unchanged"]=True
summary["drupal_mutation_performed"]=False
open(sys.argv[4],"w",encoding="utf-8").write(json.dumps(summary,indent=2,sort_keys=True)+"\n")
PY

    if rg -n -i 'sk-[A-Za-z0-9_-]{20,}|data:image/|Authorization[[:space:]]*:|Basic[[:space:]]+[A-Za-z0-9+/]{16,}={0,2}' "$run_dir" >/dev/null; then
      printf '%s\n' "${run_dir#"$REPO/"}" >"$EVIDENCE_ROOT/GATE2A-STEP03-VERIFICATION-LAST-RUN.txt"
      fail "Potential secret/raw-image content found in compliance evidence"
    fi
    printf '[PASS] No secret/raw-image material retained.\n' >"$run_dir/secret-scan.log"
    write_manifest "$run_dir"
    printf '%s\n' "${run_dir#"$REPO/"}" >"$EVIDENCE_ROOT/GATE2A-STEP03-VERIFICATION-LAST-RUN.txt"

    # Validate supplement structurally before status promotion.
    "$PYTHON" - "$run_dir" <<'PY'
import hashlib,json,sys
from pathlib import Path
r=Path(sys.argv[1]); s=json.load(open(r/"summary.json",encoding="utf-8"))
assert s["status"]=="pass" and s["source_state_unchanged"] is True
assert s["drupal_mutation_performed"] is False
for line in (r/"package-files-sha256.txt").read_text().splitlines():
    h,rel=line.split(maxsplit=1)
    assert hashlib.sha256((r/rel).read_bytes()).hexdigest()==h
PY

    backup="$(mktemp -d)"; mkdir -p "$backup/docs"
    cp "$REPO/AGENTS.md" "$backup/AGENTS.md"; cp "$REPO/PLAN.md" "$backup/PLAN.md"
    cp "$REPO/README.md" "$backup/README.md"; cp "$REPO/docs/CURRENT-STATUS.md" "$backup/docs/CURRENT-STATUS.md"
    rollback(){
      set +e
      cp "$backup/AGENTS.md" "$REPO/AGENTS.md"; cp "$backup/PLAN.md" "$REPO/PLAN.md"
      cp "$backup/README.md" "$REPO/README.md"; cp "$backup/docs/CURRENT-STATUS.md" "$REPO/docs/CURRENT-STATUS.md"
      rm -f "$EVIDENCE_ROOT/GATE2A-STEP03-VERIFICATION-LATEST.txt"
      set -e
    }
    if ! "$PYTHON" "$STATE" --repo "$REPO" --state complete --verification-run "$run_id"; then
      rollback; rm -rf "$backup"; fail "Compliance status promotion failed"
    fi
    printf '%s\n' "${run_dir#"$REPO/"}" >"$EVIDENCE_ROOT/.verify-latest.tmp"
    mv "$EVIDENCE_ROOT/.verify-latest.tmp" "$EVIDENCE_ROOT/GATE2A-STEP03-VERIFICATION-LATEST.txt"
    if ! "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state complete; then
      rollback; rm -rf "$backup"; fail "Post-verification complete audit failed"
    fi
    rm -rf "$backup"
    pass "Gate 2A Step 2A.03 compliance verification passed."
    pass "Supplemental evidence: ${run_dir#"$REPO/"}"
    printf '[STOP] Review supplement and restage the complete Step 2A.03 boundary; do not rerun the accepted live proof.\n'
    ;;
  audit)
    "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state complete
    ;;
  *)
    fail "Usage: bash scripts/run-gate2a-step03-compliance.sh {run|audit}"
    ;;
esac
