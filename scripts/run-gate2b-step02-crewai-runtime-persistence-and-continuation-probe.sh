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
STEP01_EVIDENCE="$REPO/evidence/gates/gate-2b/contract/gate2b-step01-20260811T231020Z-00000002"
EVIDENCE_ROOT="$REPO/evidence/gates/gate-2b/runtime-probe"
RUNTIME_PARENT="$REPO/crewai/.runtime/gate2b-step02"
CLEANUP_RUNTIME_DIR=""
CLEANUP_ARMED=0
DIAGNOSTIC_ID="gate2b-step02-20260812T010531Z-00000001"
DIAGNOSTIC_MANIFEST_SHA256="6bbb9619df39cfba939f09223bde9ce160b52476598d2b847a0591c3a0edb5f5"
DIAGNOSTIC_SUMMARY_SHA256="e7c2bde43dcc30c8b912099ac2e6682684649ebbd0125a10b5fe0d3940494aee"
INSTALL_PATHS=(
  AGENTS.md
  PLAN.md
  README.md
  docs/CURRENT-STATUS.md
  crewai/runtime_probe/__init__.py
  crewai/runtime_probe/step2b02_probe.py
  crewai/runtime_probe/step2b02_worker.py
  docs/gates/GATE-2B-STEP02-CREWAI-RUNTIME-PERSISTENCE-AND-CONTINUATION-PROBE.md
  shared/schemas/gate2b-step02-runtime-probe-evidence.schema.json
  scripts/gate2b_step02_audit.py
  scripts/run-gate2b-step02-crewai-runtime-persistence-and-continuation-probe.sh
)
EVIDENCE_FILES=(
  api-surface.json architecture-recommendation.json authorization.json evidence-manifest.json
  failure-propagation.json flow-persistence.json human-feedback-continuation.json predecessor.json
  probe-log.txt process-boundary.json retry-hidden-call-controls.json run-isolation.json
  runtime-checkpoint-json.json runtime-checkpoint-sqlite.json runtime-versions.json
  serialized-state-privacy.json storage-provenance.json summary.json
)

fail() {
  printf '[ERROR] %s\n' "$*" >&2
  exit 1
}

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
      printf '[CLEANUP ERROR] Unable to resolve runtime parent.\n' >&2
      cleanup_rc=1
    elif ! target="$(realpath -m -- "$CLEANUP_RUNTIME_DIR")"; then
      printf '[CLEANUP ERROR] Unable to resolve cleanup target.\n' >&2
      cleanup_rc=1
    else
      basename="${target##*/}"
      if [[ "${target%/*}" != "$parent" || ! "$basename" =~ ^gate2b-step02-[0-9]{8}T[0-9]{6}Z-[0-9]{8}$ ]]; then
        printf '[CLEANUP ERROR] Refusing out-of-scope runtime target: %s\n' "$target" >&2
        cleanup_rc=1
      elif [[ -e "$target" ]]; then
        if rm -rf -- "$target" && [[ ! -e "$target" ]]; then
          printf '[CLEANUP PASS] Removed exact probe runtime path: %s\n' "$target"
        else
          printf '[CLEANUP ERROR] Exact runtime cleanup failed: %s\n' "$target" >&2
          cleanup_rc=1
        fi
      else
        printf '[CLEANUP PASS] Exact probe runtime path already absent: %s\n' "$target"
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
  [[ "$top" == "$REPO" ]] || fail "Script is not running from the repository root"
}

permanent_predecessor_audits() {
  (cd "$REPO" && bash scripts/run-gate2a-step10-langgraph-certification-freeze-and-crewai-handoff.sh audit)
  (cd "$REPO" && bash scripts/run-gate2b-step01-crewai-contract-and-evidence-plan.sh audit)
  "$REPO/crewai/.venv/bin/python" "$REPO/scripts/gate2b_step01_audit.py" \
    --repo "$REPO" --evidence-required
  (cd "$REPO" && bash scripts/run-gate05-step05.sh audit)
}

verify_run_lifecycle() {
  resolve_git
  local branch head origin_main status path allowed evidence_name
  if ! branch="$(git -C "$REPO" branch --show-current)"; then fail "Unable to resolve branch"; fi
  if ! head="$(git -C "$REPO" rev-parse HEAD)"; then fail "Unable to resolve HEAD"; fi
  if ! origin_main="$(git -C "$REPO" rev-parse origin/main)"; then fail "Unable to resolve origin/main"; fi
  [[ "$branch" == "$FEATURE_BRANCH" ]] || fail "Run requires exact feature branch"
  [[ "$head" == "$BASE" ]] || fail "Run requires exact predecessor HEAD"
  [[ "$origin_main" == "$BASE" ]] || fail "Run requires unchanged predecessor origin/main"
  if ! status="$(git -C "$REPO" status --porcelain=v1 --untracked-files=all)"; then fail "Unable to inspect working tree"; fi
  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    path="${line:3}"
    allowed=0
    local expected
    for expected in "${INSTALL_PATHS[@]}"; do
      if [[ "$path" == "$expected" ]]; then allowed=1; break; fi
    done
    if [[ "$allowed" == 0 ]]; then
      for evidence_name in "${EVIDENCE_FILES[@]}"; do
        if [[ "$path" == "evidence/gates/gate-2b/runtime-probe/$DIAGNOSTIC_ID/$evidence_name" ]]; then allowed=1; break; fi
      done
    fi
    [[ "$allowed" == 1 ]] || fail "Unexpected pre-run working-tree path: $path"
  done <<< "$status"
  [[ "$(hash_file "$EVIDENCE_ROOT/$DIAGNOSTIC_ID/evidence-manifest.json")" == "$DIAGNOSTIC_MANIFEST_SHA256" ]] || fail "Retained diagnostic manifest changed"
  [[ "$(hash_file "$EVIDENCE_ROOT/$DIAGNOSTIC_ID/summary.json")" == "$DIAGNOSTIC_SUMMARY_SHA256" ]] || fail "Retained diagnostic summary changed"
  permanent_predecessor_audits
}

verify_audit_lifecycle() {
  resolve_git
  local head
  if ! head="$(git -C "$REPO" rev-parse HEAD)"; then fail "Unable to resolve HEAD"; fi
  git -C "$REPO" merge-base --is-ancestor "$BASE" "$head" || fail "Step 2B.02 predecessor is not in current ancestry"
}

next_evidence_id() {
  local timestamp attempt candidate
  if ! timestamp="$(date -u +%Y%m%dT%H%M%SZ)"; then return 1; fi
  for attempt in $(seq 1 99999999); do
    candidate="gate2b-step02-${timestamp}-$(printf '%08d' "$attempt")"
    if [[ ! -e "$EVIDENCE_ROOT/$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

run_probe() {
  verify_run_lifecycle
  local evidence_id evidence_dir architecture_status
  if ! evidence_id="$(next_evidence_id)"; then fail "Unable to allocate unique evidence ID"; fi
  evidence_dir="$EVIDENCE_ROOT/$evidence_id"
  CLEANUP_RUNTIME_DIR="$RUNTIME_PARENT/$evidence_id"
  [[ ! -e "$evidence_dir" && ! -e "$CLEANUP_RUNTIME_DIR" ]] || fail "Run paths already exist"
  mkdir -p "$EVIDENCE_ROOT" "$RUNTIME_PARENT"
  CLEANUP_ARMED=1
  (
    unset OPENAI_API_KEY OPENAI_ORG_ID OPENAI_PROJECT_ID
    unset DRUPAL_BASIC_AUTH_USERNAME DRUPAL_BASIC_AUTH_PASSWORD DRUPAL_AUTHORIZATION
    export CREWAI_DISABLE_TELEMETRY=true CREWAI_DISABLE_TRACKING=true
    export CREWAI_TRACING_ENABLED=false OTEL_SDK_DISABLED=true PYTHONDONTWRITEBYTECODE=1
    "$REPO/crewai/.venv/bin/python" "$REPO/crewai/runtime_probe/step2b02_probe.py" \
      --repo "$REPO" --evidence "$evidence_dir" --storage "$CLEANUP_RUNTIME_DIR" \
      --evidence-id "$evidence_id" --timeout 15
  )
  "$REPO/crewai/.venv/bin/python" "$REPO/scripts/gate2b_step02_audit.py" \
    --repo "$REPO" --evidence "$evidence_dir"
  if ! architecture_status="$($REPO/crewai/.venv/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["status"])' "$evidence_dir/architecture-recommendation.json")"; then
    fail "Unable to read architecture status"
  fi
  printf '[PASS] Retained model-free Step 2B.02 evidence: %s\n' "$evidence_id"
  printf '[PASS] No model call, Drupal mutation, source mutation, human review, dependency change, recommendation submission, or Gate 2C execution occurred.\n'
  if [[ "$architecture_status" != recommendation_ready ]]; then
    printf '[STOP] Architecture evidence remains unresolved; no ADR or later package is authorized.\n' >&2
    exit 3
  fi
  printf '[STOP] Architecture recommendation is ready for human review; no ADR was created automatically.\n'
}

audit_probe() {
  verify_audit_lifecycle
  [[ -n "$EVIDENCE_INPUT" ]] || fail "Audit requires an explicit evidence directory or evidence ID"
  local evidence_dir
  if [[ "$EVIDENCE_INPUT" == /* ]]; then
    if ! evidence_dir="$(realpath -e -- "$EVIDENCE_INPUT")"; then fail "Unable to resolve evidence path"; fi
  else
    if ! evidence_dir="$(realpath -e -- "$EVIDENCE_ROOT/$EVIDENCE_INPUT")"; then fail "Unable to resolve evidence ID"; fi
  fi
  permanent_predecessor_audits
  "$REPO/crewai/.venv/bin/python" "$REPO/scripts/gate2b_step02_audit.py" \
    --repo "$REPO" --evidence "$evidence_dir"
}

case "$MODE" in
  run) run_probe ;;
  audit) audit_probe ;;
  *) fail "Usage: bash scripts/run-gate2b-step02-crewai-runtime-persistence-and-continuation-probe.sh {run|audit} [evidence-id-or-path]" ;;
esac
