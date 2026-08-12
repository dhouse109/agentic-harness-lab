#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-audit}"
EVIDENCE_INPUT="${2:-gate2b-step02-disposition-20260812T024610Z-00000001}"
SCRIPT_DIR=""
if ! SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"; then
  printf '[ERROR] Unable to resolve script directory.\n' >&2
  exit 1
fi
REPO=""
if ! REPO="$(realpath -e -- "$SCRIPT_DIR/..")"; then
  printf '[ERROR] Unable to resolve repository root.\n' >&2
  exit 1
fi

BASE="7bea4320c08670d8e9a0c71f88d10922fced8c1e"
FEATURE_BRANCH="gate-2b-step02-crewai-runtime-persistence-and-continuation-probe"
EVIDENCE_ID="gate2b-step02-disposition-20260812T024610Z-00000001"
EVIDENCE_ROOT="$REPO/evidence/gates/gate-2b/runtime-probe-disposition"
DIAGNOSTIC_ID="gate2b-step02-20260812T010531Z-00000001"
DIAGNOSTIC_MANIFEST="6bbb9619df39cfba939f09223bde9ce160b52476598d2b847a0591c3a0edb5f5"
DIAGNOSTIC_SUMMARY="e7c2bde43dcc30c8b912099ac2e6682684649ebbd0125a10b5fe0d3940494aee"
FRESH_ID="gate2b-step02-20260812T015108Z-00000001"
FRESH_MANIFEST="8339eca113dfb1bc5cfa15d2fcbc1f95e104d908852e0656024f299f4e2c2b66"
FRESH_SUMMARY="b03d7c8a787757b020f889faa8cb3f6393edfb0f477e2a39dd93dbbd868ef349"
FOLLOWUP_ID="gate2b-step02-followup-20260812T022947Z-00000001"
FOLLOWUP_MANIFEST="6654fd33e10efdf275f0aa9ea104293ed1f7ba3092d054718a9ac0a491b07a79"
FOLLOWUP_SUMMARY="48fa2e41db6089cf63d3f250b8a31c547c322dc8e72d8a25ae9dc1078a734a57"
INSTALL_PATHS=(
  AGENTS.md PLAN.md README.md docs/CURRENT-STATUS.md
  crewai/runtime_probe/__init__.py crewai/runtime_probe/step2b02_followup.py
  crewai/runtime_probe/step2b02_probe.py crewai/runtime_probe/step2b02_worker.py
  docs/gates/GATE-2B-STEP02-CREWAI-RUNTIME-PERSISTENCE-AND-CONTINUATION-PROBE.md
  scripts/gate2b_step02_audit.py scripts/gate2b_step02_version_disposition.py
  scripts/run-gate2b-step02-crewai-runtime-persistence-and-continuation-probe.sh
  scripts/run-gate2b-step02-hidden-network-retry-and-checkpoint-semantics-followup.sh
  scripts/run-gate2b-step02-version-check-path-classification-and-architecture-disposition.sh
  shared/schemas/gate2b-step02-runtime-probe-evidence.schema.json
  shared/schemas/gate2b-step02-followup-evidence.schema.json
  shared/schemas/gate2b-step02-network-disposition-evidence.schema.json
)
RUNTIME_FILES=(
  api-surface.json architecture-recommendation.json authorization.json evidence-manifest.json
  failure-propagation.json flow-persistence.json human-feedback-continuation.json predecessor.json
  probe-log.txt process-boundary.json retry-hidden-call-controls.json run-isolation.json
  runtime-checkpoint-json.json runtime-checkpoint-sqlite.json runtime-versions.json
  serialized-state-privacy.json storage-provenance.json summary.json
)
FOLLOWUP_FILES=(
  architecture-impact.json authorization.json checkpoint-network-provenance.json
  checkpoint-semantics.json evidence-manifest.json pinned-source-findings.json
  predecessor.json summary.json targeted-probe-log.txt
)

fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

hash_file() {
  local value
  if ! value="$(sha256sum -- "$1")"; then fail "Unable to hash $1"; fi
  printf '%s\n' "${value%% *}"
}

resolve_git() {
  local top
  if ! top="$(git -C "$REPO" rev-parse --show-toplevel)"; then fail "Unable to resolve Git root"; fi
  [[ "$top" == "$REPO" ]] || fail "Script is not installed at repository root"
}

verify_retained() {
  local runtime="$REPO/evidence/gates/gate-2b/runtime-probe"
  local followup="$REPO/evidence/gates/gate-2b/runtime-probe-followup"
  [[ "$(hash_file "$runtime/$DIAGNOSTIC_ID/evidence-manifest.json")" == "$DIAGNOSTIC_MANIFEST" ]] || fail "Diagnostic manifest changed"
  [[ "$(hash_file "$runtime/$DIAGNOSTIC_ID/summary.json")" == "$DIAGNOSTIC_SUMMARY" ]] || fail "Diagnostic summary changed"
  [[ "$(hash_file "$runtime/$FRESH_ID/evidence-manifest.json")" == "$FRESH_MANIFEST" ]] || fail "V2 manifest changed"
  [[ "$(hash_file "$runtime/$FRESH_ID/summary.json")" == "$FRESH_SUMMARY" ]] || fail "V2 summary changed"
  [[ "$(hash_file "$followup/$FOLLOWUP_ID/evidence-manifest.json")" == "$FOLLOWUP_MANIFEST" ]] || fail "Supplemental manifest changed"
  [[ "$(hash_file "$followup/$FOLLOWUP_ID/summary.json")" == "$FOLLOWUP_SUMMARY" ]] || fail "Supplemental summary changed"
}

permanent_predecessor_audits() {
  (cd "$REPO" && bash scripts/run-gate2a-step10-langgraph-certification-freeze-and-crewai-handoff.sh audit)
  (cd "$REPO" && bash scripts/run-gate2b-step01-crewai-contract-and-evidence-plan.sh audit)
  "$REPO/crewai/.venv/bin/python" "$REPO/scripts/gate2b_step01_audit.py" --repo "$REPO" --evidence-required
  (cd "$REPO" && bash scripts/run-gate05-step05.sh audit)
  "$REPO/crewai/.venv/bin/python" "$REPO/scripts/gate2b_step02_audit.py" --repo "$REPO" --evidence "$REPO/evidence/gates/gate-2b/runtime-probe/$FRESH_ID"
  "$REPO/crewai/.venv/bin/python" "$REPO/scripts/gate2b_step02_audit.py" --repo "$REPO" --supplemental "$REPO/evidence/gates/gate-2b/runtime-probe-followup/$FOLLOWUP_ID"
}

verify_run_lifecycle() {
  resolve_git
  local branch head origin_main status path expected allowed count=0 name
  if ! branch="$(git -C "$REPO" branch --show-current)"; then fail "Unable to resolve branch"; fi
  if ! head="$(git -C "$REPO" rev-parse HEAD)"; then fail "Unable to resolve HEAD"; fi
  if ! origin_main="$(git -C "$REPO" rev-parse origin/main)"; then fail "Unable to resolve origin/main"; fi
  [[ "$branch" == "$FEATURE_BRANCH" ]] || fail "Run requires exact Step 2B.02 feature branch"
  [[ "$head" == "$BASE" ]] || fail "Run requires exact merged predecessor HEAD"
  [[ "$origin_main" == "$BASE" ]] || fail "Run requires unchanged predecessor origin/main"
  if ! status="$(git -C "$REPO" status --porcelain=v1 --untracked-files=all)"; then fail "Unable to inspect working tree"; fi
  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    path="${line:3}"
    allowed=0
    count=$((count + 1))
    for expected in "${INSTALL_PATHS[@]}"; do
      if [[ "$path" == "$expected" ]]; then allowed=1; break; fi
    done
    if [[ "$allowed" == 0 ]]; then
      for name in "${RUNTIME_FILES[@]}"; do
        if [[ "$path" == "evidence/gates/gate-2b/runtime-probe/$DIAGNOSTIC_ID/$name" || "$path" == "evidence/gates/gate-2b/runtime-probe/$FRESH_ID/$name" ]]; then allowed=1; break; fi
      done
    fi
    if [[ "$allowed" == 0 ]]; then
      for name in "${FOLLOWUP_FILES[@]}"; do
        if [[ "$path" == "evidence/gates/gate-2b/runtime-probe-followup/$FOLLOWUP_ID/$name" ]]; then allowed=1; break; fi
      done
    fi
    [[ "$allowed" == 1 ]] || fail "Unexpected pre-disposition working-tree path: $path"
  done <<< "$status"
  [[ "$count" -eq 62 ]] || fail "Expected exact 62-path installed baseline, found $count"
  [[ ! -e "$EVIDENCE_ROOT" ]] || fail "Disposition evidence root must be absent before first run"
  if [[ -d "$REPO/crewai/.runtime/gate2b-step02" ]] && [[ -n "$(find "$REPO/crewai/.runtime/gate2b-step02" -mindepth 1 -print -quit)" ]]; then
    fail "Step 2B.02 run-owned runtime storage must remain absent"
  fi
  if [[ -d "$REPO/crewai/.runtime/gate2b-step02-followup" ]] && [[ -n "$(find "$REPO/crewai/.runtime/gate2b-step02-followup" -mindepth 1 -print -quit)" ]]; then
    fail "Step 2B.02 follow-up runtime storage must remain absent"
  fi
  verify_retained
  permanent_predecessor_audits
}

verify_audit_lifecycle() {
  resolve_git
  local head
  if ! head="$(git -C "$REPO" rev-parse HEAD)"; then fail "Unable to resolve HEAD"; fi
  git -C "$REPO" merge-base --is-ancestor "$BASE" "$head" || fail "Step 2B.02 predecessor is absent from current ancestry"
  verify_retained
}

run_disposition() {
  verify_run_lifecycle
  local evidence_dir="$EVIDENCE_ROOT/$EVIDENCE_ID"
  [[ ! -e "$evidence_dir" ]] || fail "Governed disposition already exists"
  mkdir -p "$EVIDENCE_ROOT"
  (
    unset OPENAI_API_KEY OPENAI_ORG_ID OPENAI_PROJECT_ID ANTHROPIC_API_KEY
    unset DRUPAL_BASIC_AUTH_USERNAME DRUPAL_BASIC_AUTH_PASSWORD DRUPAL_AUTHORIZATION
    export CREWAI_DISABLE_VERSION_CHECK=true CREWAI_DISABLE_TELEMETRY=true
    export CREWAI_DISABLE_TRACKING=true CREWAI_TRACING_ENABLED=false OTEL_SDK_DISABLED=true
    export PYTHONDONTWRITEBYTECODE=1
    "$REPO/crewai/.venv/bin/python" "$REPO/scripts/gate2b_step02_version_disposition.py" --repo "$REPO" --evidence "$evidence_dir" --evidence-id "$EVIDENCE_ID"
  )
  "$REPO/crewai/.venv/bin/python" "$REPO/scripts/gate2b_step02_audit.py" --repo "$REPO" --disposition "$evidence_dir"
  printf '[PASS] Retained governed Step 2B.02 disposition: %s\n' "$EVIDENCE_ID"
  printf '[PASS] No runtime/checkpoint probe, model/provider call, outbound connection, Drupal/source mutation, human review, dependency change, recommendation submission, or Gate 2C execution occurred.\n'
  printf '[STOP] Recommendation is ready only for explicit human architecture/ADR review; no ADR was created.\n'
}

audit_disposition() {
  verify_audit_lifecycle
  local evidence_dir
  if [[ "$EVIDENCE_INPUT" == /* ]]; then
    if ! evidence_dir="$(realpath -e -- "$EVIDENCE_INPUT")"; then fail "Unable to resolve evidence path"; fi
  else
    if ! evidence_dir="$(realpath -e -- "$EVIDENCE_ROOT/$EVIDENCE_INPUT")"; then fail "Unable to resolve evidence ID"; fi
  fi
  permanent_predecessor_audits
  "$REPO/crewai/.venv/bin/python" "$REPO/scripts/gate2b_step02_audit.py" --repo "$REPO" --disposition "$evidence_dir"
}

case "$MODE" in
  run) run_disposition ;;
  audit) audit_disposition ;;
  *) fail "Usage: bash scripts/run-gate2b-step02-version-check-path-classification-and-architecture-disposition.sh {run|audit} [evidence-id-or-path]" ;;
esac
