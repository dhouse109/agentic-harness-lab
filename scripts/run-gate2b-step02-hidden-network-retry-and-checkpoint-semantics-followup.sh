#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-audit}"
EVIDENCE_INPUT="${2:-}"
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
EVIDENCE_ROOT="$REPO/evidence/gates/gate-2b/runtime-probe-followup"
RUNTIME_PARENT="$REPO/crewai/.runtime/gate2b-step02-followup"
CLEANUP_RUNTIME_DIR=""
CLEANUP_ARMED=0
DIAGNOSTIC_ID="gate2b-step02-20260812T010531Z-00000001"
DIAGNOSTIC_MANIFEST="6bbb9619df39cfba939f09223bde9ce160b52476598d2b847a0591c3a0edb5f5"
DIAGNOSTIC_SUMMARY="e7c2bde43dcc30c8b912099ac2e6682684649ebbd0125a10b5fe0d3940494aee"
FRESH_ID="gate2b-step02-20260812T015108Z-00000001"
FRESH_MANIFEST="8339eca113dfb1bc5cfa15d2fcbc1f95e104d908852e0656024f299f4e2c2b66"
FRESH_SUMMARY="b03d7c8a787757b020f889faa8cb3f6393edfb0f477e2a39dd93dbbd868ef349"
INSTALL_PATHS=(
  AGENTS.md PLAN.md README.md docs/CURRENT-STATUS.md
  crewai/runtime_probe/__init__.py crewai/runtime_probe/step2b02_probe.py
  crewai/runtime_probe/step2b02_worker.py crewai/runtime_probe/step2b02_followup.py
  docs/gates/GATE-2B-STEP02-CREWAI-RUNTIME-PERSISTENCE-AND-CONTINUATION-PROBE.md
  shared/schemas/gate2b-step02-runtime-probe-evidence.schema.json
  shared/schemas/gate2b-step02-followup-evidence.schema.json
  scripts/gate2b_step02_audit.py
  scripts/run-gate2b-step02-crewai-runtime-persistence-and-continuation-probe.sh
  scripts/run-gate2b-step02-hidden-network-retry-and-checkpoint-semantics-followup.sh
)
RUNTIME_EVIDENCE_FILES=(
  api-surface.json architecture-recommendation.json authorization.json evidence-manifest.json
  failure-propagation.json flow-persistence.json human-feedback-continuation.json predecessor.json
  probe-log.txt process-boundary.json retry-hidden-call-controls.json run-isolation.json
  runtime-checkpoint-json.json runtime-checkpoint-sqlite.json runtime-versions.json
  serialized-state-privacy.json storage-provenance.json summary.json
)

fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }

hash_file() {
  local value
  if ! value="$(sha256sum -- "$1")"; then fail "Unable to hash $1"; fi
  printf '%s\n' "${value%% *}"
}

cleanup_runtime() {
  local primary_rc=$? cleanup_rc=0 parent target basename
  trap - EXIT
  if [[ "$CLEANUP_ARMED" == 1 && -n "$CLEANUP_RUNTIME_DIR" ]]; then
    if ! parent="$(realpath -e -- "$RUNTIME_PARENT")"; then
      printf '[CLEANUP ERROR] Unable to resolve exact runtime parent.\n' >&2
      cleanup_rc=1
    elif ! target="$(realpath -m -- "$CLEANUP_RUNTIME_DIR")"; then
      printf '[CLEANUP ERROR] Unable to resolve exact cleanup target.\n' >&2
      cleanup_rc=1
    else
      basename="${target##*/}"
      if [[ "${target%/*}" != "$parent" || ! "$basename" =~ ^gate2b-step02-followup-[0-9]{8}T[0-9]{6}Z-[0-9]{8}$ ]]; then
        printf '[CLEANUP ERROR] Refusing out-of-scope runtime target: %s\n' "$target" >&2
        cleanup_rc=1
      elif [[ -e "$target" ]]; then
        if rm -rf -- "$target" && [[ ! -e "$target" ]]; then
          printf '[CLEANUP PASS] Removed exact targeted-probe runtime path: %s\n' "$target"
        else
          printf '[CLEANUP ERROR] Exact runtime cleanup failed: %s\n' "$target" >&2
          cleanup_rc=1
        fi
      else
        printf '[CLEANUP PASS] Exact targeted-probe runtime path already absent: %s\n' "$target"
      fi
    fi
  fi
  if [[ "$primary_rc" -ne 0 ]]; then exit "$primary_rc"; fi
  exit "$cleanup_rc"
}
trap cleanup_runtime EXIT

resolve_git() {
  local top
  if ! top="$(git -C "$REPO" rev-parse --show-toplevel)"; then fail "Unable to resolve Git root"; fi
  [[ "$top" == "$REPO" ]] || fail "Script is not installed at repository root"
}

verify_retained() {
  local root="$REPO/evidence/gates/gate-2b/runtime-probe"
  [[ "$(hash_file "$root/$DIAGNOSTIC_ID/evidence-manifest.json")" == "$DIAGNOSTIC_MANIFEST" ]] || fail "Diagnostic manifest changed"
  [[ "$(hash_file "$root/$DIAGNOSTIC_ID/summary.json")" == "$DIAGNOSTIC_SUMMARY" ]] || fail "Diagnostic summary changed"
  [[ "$(hash_file "$root/$FRESH_ID/evidence-manifest.json")" == "$FRESH_MANIFEST" ]] || fail "Fresh-capture manifest changed"
  [[ "$(hash_file "$root/$FRESH_ID/summary.json")" == "$FRESH_SUMMARY" ]] || fail "Fresh-capture summary changed"
}

permanent_predecessor_audits() {
  (cd "$REPO" && bash scripts/run-gate2a-step10-langgraph-certification-freeze-and-crewai-handoff.sh audit)
  (cd "$REPO" && bash scripts/run-gate2b-step01-crewai-contract-and-evidence-plan.sh audit)
  "$REPO/crewai/.venv/bin/python" "$REPO/scripts/gate2b_step01_audit.py" --repo "$REPO" --evidence-required
  (cd "$REPO" && bash scripts/run-gate05-step05.sh audit)
  "$REPO/crewai/.venv/bin/python" "$REPO/scripts/gate2b_step02_audit.py" \
    --repo "$REPO" --evidence "$REPO/evidence/gates/gate-2b/runtime-probe/$FRESH_ID"
}

verify_run_lifecycle() {
  resolve_git
  local branch head origin_main status path expected evidence_name allowed count=0
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
      for evidence_name in "${RUNTIME_EVIDENCE_FILES[@]}"; do
        if [[ "$path" == "evidence/gates/gate-2b/runtime-probe/$DIAGNOSTIC_ID/$evidence_name" || "$path" == "evidence/gates/gate-2b/runtime-probe/$FRESH_ID/$evidence_name" ]]; then
          allowed=1
          break
        fi
      done
    fi
    [[ "$allowed" == 1 ]] || fail "Unexpected pre-run working-tree path: $path"
  done <<< "$status"
  [[ "$count" -eq 50 ]] || fail "Expected exact 50-path installed/prior-evidence baseline, found $count"
  [[ ! -e "$EVIDENCE_ROOT" ]] || fail "Targeted follow-up evidence root must be absent before first run"
  [[ ! -e "$RUNTIME_PARENT" ]] || fail "Targeted follow-up runtime parent must be absent before first run"
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

next_evidence_id() {
  local timestamp attempt candidate
  if ! timestamp="$(date -u +%Y%m%dT%H%M%SZ)"; then return 1; fi
  for attempt in $(seq 1 99999999); do
    candidate="gate2b-step02-followup-${timestamp}-$(printf '%08d' "$attempt")"
    if [[ ! -e "$EVIDENCE_ROOT/$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

run_followup() {
  verify_run_lifecycle
  local evidence_id evidence_dir architecture_status
  if ! evidence_id="$(next_evidence_id)"; then fail "Unable to allocate unique targeted evidence ID"; fi
  evidence_dir="$EVIDENCE_ROOT/$evidence_id"
  CLEANUP_RUNTIME_DIR="$RUNTIME_PARENT/$evidence_id"
  [[ ! -e "$evidence_dir" && ! -e "$CLEANUP_RUNTIME_DIR" ]] || fail "Targeted run paths already exist"
  mkdir -p "$EVIDENCE_ROOT" "$RUNTIME_PARENT"
  CLEANUP_ARMED=1
  (
    unset OPENAI_API_KEY OPENAI_ORG_ID OPENAI_PROJECT_ID
    unset DRUPAL_BASIC_AUTH_USERNAME DRUPAL_BASIC_AUTH_PASSWORD DRUPAL_AUTHORIZATION
    export CREWAI_DISABLE_TELEMETRY=true CREWAI_DISABLE_TRACKING=true
    export CREWAI_TRACING_ENABLED=false OTEL_SDK_DISABLED=true PYTHONDONTWRITEBYTECODE=1
    "$REPO/crewai/.venv/bin/python" "$REPO/crewai/runtime_probe/step2b02_followup.py" \
      --repo "$REPO" --evidence "$evidence_dir" --storage "$CLEANUP_RUNTIME_DIR" \
      --evidence-id "$evidence_id" --timeout 15
  )
  "$REPO/crewai/.venv/bin/python" "$REPO/scripts/gate2b_step02_audit.py" \
    --repo "$REPO" --supplemental "$evidence_dir"
  if ! architecture_status="$($REPO/crewai/.venv/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["status"])' "$evidence_dir/architecture-impact.json")"; then
    fail "Unable to read targeted architecture status"
  fi
  printf '[PASS] Retained model-free Step 2B.02 targeted evidence: %s\n' "$evidence_id"
  printf '[PASS] No model/provider call, Drupal/source mutation, human review, dependency change, recommendation submission, or Gate 2C execution occurred.\n'
  if [[ "$architecture_status" != recommendation_ready ]]; then
    printf '[STOP] Step 2B.02 architecture remains unresolved; no ADR or later package is authorized.\n' >&2
    exit 3
  fi
  printf '[STOP] Architecture recommendation is ready for human review; no ADR was created automatically.\n'
}

audit_followup() {
  verify_audit_lifecycle
  [[ -n "$EVIDENCE_INPUT" ]] || fail "Audit requires explicit supplemental evidence directory or ID"
  local evidence_dir
  if [[ "$EVIDENCE_INPUT" == /* ]]; then
    if ! evidence_dir="$(realpath -e -- "$EVIDENCE_INPUT")"; then fail "Unable to resolve evidence path"; fi
  else
    if ! evidence_dir="$(realpath -e -- "$EVIDENCE_ROOT/$EVIDENCE_INPUT")"; then fail "Unable to resolve evidence ID"; fi
  fi
  permanent_predecessor_audits
  "$REPO/crewai/.venv/bin/python" "$REPO/scripts/gate2b_step02_audit.py" \
    --repo "$REPO" --supplemental "$evidence_dir"
}

case "$MODE" in
  run) run_followup ;;
  audit) audit_followup ;;
  *) fail "Usage: bash scripts/run-gate2b-step02-hidden-network-retry-and-checkpoint-semantics-followup.sh {run|audit} [evidence-id-or-path]" ;;
esac
