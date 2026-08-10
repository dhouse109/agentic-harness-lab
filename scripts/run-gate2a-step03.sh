#!/usr/bin/env bash
set -Eeuo pipefail
MODE="${1:-audit}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
DRUPAL="$REPO/drupal"
PYTHON="$REPO/langchain/.venv/bin/python"
AUDITOR="$REPO/scripts/gate2a_step03_audit.py"
EXERCISE="$REPO/scripts/gate2a_step03_exercise.py"
STATE="$REPO/scripts/gate2a_step03_state.py"
EVIDENCE_ROOT="$REPO/evidence/gates/gate-2a/tool-adapters"
EXPECTED_BASE="096c790ba1d87d960c6a99bd383e034c6d70e3e2"
EXPECTED_BRANCH="gate-2a-step03-langgraph-tool-adapters"
CREDENTIALS="$DRUPAL/.secrets/phase0-step7-accounts.txt"

fail(){ printf '[ERROR] %s\n' "$*" >&2; exit 1; }
pass(){ printf '[PASS] %s\n' "$*"; }
info(){ printf '[INFO] %s\n' "$*"; }

latest_secret(){
  local key="$1"
  awk -v key="$key" 'index($0,key "=")==1 { value=substr($0,length(key)+2) } END { if(value!="") print value }' "$CREDENTIALS"
}

resolve_site_url(){
  local value
  value="$(cd "$DRUPAL" && ddev exec printenv DDEV_PRIMARY_URL 2>/dev/null | tr -d '\r' | grep -Eo 'https?://[^[:space:]]+' | tail -n 1 || true)"
  [[ -n "$value" ]] || fail "Unable to resolve DDEV_PRIMARY_URL"
  printf '%s' "${value%/}"
}

seeded_clean(){
  local out="$1"
  (cd "$DRUPAL" && bash scripts/run-phase0-step10.sh audit) >"$out"
}

snapshot_state(){
  local out="$1"
  (
    cd "$DRUPAL"
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
      ddev drush --quiet php:script scripts/gate1-step03-adapter-exercise.php -- snapshot
  ) >"$out"
}

preflight(){
  [[ "$(git -C "$REPO" branch --show-current)" == "$EXPECTED_BRANCH" ]] || fail "Run requires branch $EXPECTED_BRANCH"
  [[ "$(git -C "$REPO" rev-parse HEAD)" == "$EXPECTED_BASE" ]] || fail "Run requires uncommitted Step 2A.03 install on base $EXPECTED_BASE"
  "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state active >/dev/null
  bash "$REPO/scripts/run-gate1-step07-drupal-ai-certification-and-handoff.sh" audit >/dev/null
  bash "$REPO/scripts/run-gate05-step05.sh" audit >/dev/null
  [[ -f "$CREDENTIALS" ]] || fail "Local Drupal credentials file is missing"
  [[ ! -e "$EVIDENCE_ROOT/GATE2A-STEP03-LATEST.txt" ]] || fail "Accepted Step 2A.03 evidence already exists; run mode is closed"
}

restore_snapshot(){
  local name="$1"
  (cd "$DRUPAL" && ddev snapshot restore "$name" >/dev/null && ddev drush cr >/dev/null && ddev snapshot --cleanup --name "$name" -y >/dev/null)
}

write_manifest(){
  local dir="$1"
  (cd "$dir" && find . -maxdepth 1 -type f ! -name package-files-sha256.txt -printf '%f\n' | sort | xargs -r sha256sum > package-files-sha256.txt)
}

case "$MODE" in
  run)
    preflight
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    seeded_clean "$tmp/seeded-clean-preflight.log"

    run_id="gate2a-step03-$(date -u +%Y%m%dT%H%M%SZ)-$$"
    run_dir="$EVIDENCE_ROOT/$run_id"
    mkdir -p "$run_dir"
    cp "$tmp/seeded-clean-preflight.log" "$run_dir/seeded-clean-before.log"
    printf '%s\n' "$run_id" >"$run_dir/run-id.txt"
    snapshot_state "$run_dir/before-state.json"

    info "Recording predecessor audits before Drupal mutation..."
    "$PYTHON" "$REPO/scripts/gate2a_step02_audit.py" --repo "$REPO" --document-state complete >"$run_dir/step02-audit.log"
    bash "$REPO/scripts/run-gate1-step07-drupal-ai-certification-and-handoff.sh" audit >"$run_dir/gate1-audit.log"
    bash "$REPO/scripts/run-gate05-step05.sh" audit >"$run_dir/gate05-audit.log"
    "$PYTHON" "$EXERCISE" --repo "$REPO" --mode static >"$run_dir/static-tool-proof.json"

    snapshot_name="gate2a-step03-pre-${run_id}"
    snapshot_created=0
    restored=0
    cleanup_live(){
      local status=$?
      set +e
      if [[ "$snapshot_created" -eq 1 && "$restored" -eq 0 ]]; then
        restore_snapshot "$snapshot_name" || status=1
      fi
      unset GATE2A_DRUPAL_PASSWORD GATE2A_DRUPAL_USERNAME GATE2A_DRUPAL_BASE_URL
      rm -rf "$tmp"
      exit "$status"
    }
    trap cleanup_live EXIT INT TERM

    info "Creating exact pre-run DDEV snapshot..."
    (cd "$DRUPAL" && ddev snapshot --name "$snapshot_name" >/dev/null)
    snapshot_created=1

    agent_password="$(latest_secret agent_bot)"
    [[ -n "$agent_password" ]] || fail "agent_bot credential is empty"
    export GATE2A_DRUPAL_USERNAME="agent_bot"
    export GATE2A_DRUPAL_PASSWORD="$agent_password"
    export GATE2A_DRUPAL_BASE_URL="$(resolve_site_url)"

    set +e
    "$PYTHON" "$EXERCISE" --repo "$REPO" --mode live --evidence "$run_dir" --run-id "$run_id"
    exercise_status=$?
    set -e
    unset GATE2A_DRUPAL_PASSWORD GATE2A_DRUPAL_USERNAME GATE2A_DRUPAL_BASE_URL

    if [[ "$exercise_status" -eq 0 ]]; then
      snapshot_state "$run_dir/during-state.json"
    fi

    info "Restoring exact pre-run DDEV snapshot..."
    restore_snapshot "$snapshot_name"
    restored=1
    seeded_clean "$run_dir/seeded-clean-after.log"
    snapshot_state "$run_dir/after-state.json"

    if [[ "$exercise_status" -ne 0 ]]; then
      write_manifest "$run_dir"
      mkdir -p "$EVIDENCE_ROOT"
      printf '%s\n' "${run_dir#"$REPO/"}" >"$EVIDENCE_ROOT/GATE2A-STEP03-LAST-RUN.txt"
      trap - EXIT INT TERM
      rm -rf "$tmp"
      printf '[STOP] Step 2A.03 live adapter proof failed. Evidence retained at %s\n' "${run_dir#"$REPO/"}"
      exit "$exercise_status"
    fi

    "$PYTHON" - "$run_dir/summary.json" "$run_dir/before-state.json" "$run_dir/during-state.json" "$run_dir/after-state.json" <<'PY'
import json,sys
summary_p,before_p,during_p,after_p=sys.argv[1:]
d=json.load(open(summary_p,encoding="utf-8"))
before=json.load(open(before_p,encoding="utf-8"))
during=json.load(open(during_p,encoding="utf-8"))
after=json.load(open(after_p,encoding="utf-8"))
expected="1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728"
for label,state in (("before",before),("during",during),("after",after)):
    if state.get("target_sequence_sha256") != expected:
        raise SystemExit(f"[ERROR] {label} target sequence hash differs")
if not (before.get("article_source_sha256")==during.get("article_source_sha256")==after.get("article_source_sha256")):
    raise SystemExit("[ERROR] Article source hash changed during Step 2A.03")
if not (before.get("suggestion_count")==0 and during.get("suggestion_count")==1 and after.get("suggestion_count")==0):
    raise SystemExit("[ERROR] Expected recommendation count transition 0->1->0 was not observed")
d["source_article_mutation_performed"]=False
d["drupal_restored_to_seeded_clean"]=True
d["before_during_after_state_proof"]=True
d.pop("source_article_mutation_proof",None)
open(summary_p,"w",encoding="utf-8").write(json.dumps(d,indent=2,sort_keys=True)+"\n")
PY
    write_manifest "$run_dir"

    # Candidate evidence audit without publishing LATEST yet.
    "$PYTHON" - "$REPO" "$run_dir" <<'PY'
from pathlib import Path
import json,re,sys,hashlib
repo=Path(sys.argv[1]); rd=Path(sys.argv[2])
s=json.load(open(rd/"summary.json",encoding="utf-8"))
assert s["status"]=="pass"
assert s["drupal_restored_to_seeded_clean"] is True
for line in (rd/"package-files-sha256.txt").read_text().splitlines():
    h,rel=line.split(maxsplit=1)
    assert hashlib.sha256((rd/rel).read_bytes()).hexdigest()==h
joined="\n".join(p.read_text(encoding="utf-8",errors="ignore") for p in rd.iterdir() if p.is_file())
assert re.search(r"sk-[A-Za-z0-9_-]{20,}|data:image/|Authorization\s*:|Basic\s+[A-Za-z0-9+/]{16,}={0,2}",joined,re.I) is None
PY

    final_backup="$(mktemp -d)"
    mkdir -p "$final_backup/docs"
    cp "$REPO/AGENTS.md" "$final_backup/AGENTS.md"
    cp "$REPO/PLAN.md" "$final_backup/PLAN.md"
    cp "$REPO/README.md" "$final_backup/README.md"
    cp "$REPO/docs/CURRENT-STATUS.md" "$final_backup/docs/CURRENT-STATUS.md"

    restore_finalization(){
      set +e
      cp "$final_backup/AGENTS.md" "$REPO/AGENTS.md"
      cp "$final_backup/PLAN.md" "$REPO/PLAN.md"
      cp "$final_backup/README.md" "$REPO/README.md"
      cp "$final_backup/docs/CURRENT-STATUS.md" "$REPO/docs/CURRENT-STATUS.md"
      rm -f "$EVIDENCE_ROOT/GATE2A-STEP03-LATEST.txt"
      set -e
    }

    mkdir -p "$EVIDENCE_ROOT"
    printf '%s\n' "${run_dir#"$REPO/"}" >"$EVIDENCE_ROOT/GATE2A-STEP03-LAST-RUN.txt"

    if ! "$PYTHON" "$STATE" --repo "$REPO" --state complete --run-id "$run_id"; then
      restore_finalization
      rm -rf "$final_backup"
      trap - EXIT INT TERM
      rm -rf "$tmp"
      printf '[STOP] Step 2A.03 evidence passed but status finalization failed. Evidence retained at %s\n' "${run_dir#"$REPO/"}"
      exit 4
    fi

    latest_tmp="$EVIDENCE_ROOT/.GATE2A-STEP03-LATEST.txt.tmp"
    printf '%s\n' "${run_dir#"$REPO/"}" >"$latest_tmp"
    mv "$latest_tmp" "$EVIDENCE_ROOT/GATE2A-STEP03-LATEST.txt"

    if ! "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state complete >/dev/null; then
      restore_finalization
      rm -rf "$final_backup"
      trap - EXIT INT TERM
      rm -rf "$tmp"
      printf '[STOP] Step 2A.03 evidence passed but complete-state audit failed. Evidence retained at %s\n' "${run_dir#"$REPO/"}"
      exit 5
    fi
    rm -rf "$final_backup"

    trap - EXIT INT TERM
    rm -rf "$tmp"
    pass "Gate 2A Step 2A.03 tool-adapter boundary passed."
    pass "Evidence: ${run_dir#"$REPO/"}"
    printf '[STOP] Review retained evidence and diff; human commit approval is required.\n'
    ;;
  audit)
    "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state complete
    ;;
  *)
    fail "Usage: bash scripts/run-gate2a-step03.sh {run|audit}"
    ;;
esac
