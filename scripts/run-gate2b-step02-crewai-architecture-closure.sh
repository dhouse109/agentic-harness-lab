#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-audit}"
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
DISPOSITION_ID="gate2b-step02-disposition-20260812T024610Z-00000001"
DIAGNOSTIC_ID="gate2b-step02-20260812T010531Z-00000001"
FRESH_ID="gate2b-step02-20260812T015108Z-00000001"
FOLLOWUP_ID="gate2b-step02-followup-20260812T022947Z-00000001"
EXPECTED_PATH_COUNT=73

INSTALL_PATHS=(
  AGENTS.md PLAN.md README.md docs/CURRENT-STATUS.md docs/CODEX-GATE-2B-RUNBOOK.md
  crewai/runtime_probe/__init__.py crewai/runtime_probe/step2b02_followup.py
  crewai/runtime_probe/step2b02_probe.py crewai/runtime_probe/step2b02_worker.py
  docs/gates/GATE-2B-STEP02-CREWAI-RUNTIME-PERSISTENCE-AND-CONTINUATION-PROBE.md
  docs/decisions/ADR-0012-crewai-flow-persistence-and-human-review-continuation.md
  scripts/gate2b_step02_audit.py scripts/gate2b_step02_version_disposition.py
  scripts/run-gate2b-step02-crewai-runtime-persistence-and-continuation-probe.sh
  scripts/run-gate2b-step02-hidden-network-retry-and-checkpoint-semantics-followup.sh
  scripts/run-gate2b-step02-version-check-path-classification-and-architecture-disposition.sh
  scripts/run-gate2b-step02-crewai-architecture-closure.sh
  shared/contracts/GATE2B-STEP02-CREWAI-ARCHITECTURE-CLOSURE.json
  shared/schemas/gate2b-step02-runtime-probe-evidence.schema.json
  shared/schemas/gate2b-step02-followup-evidence.schema.json
  shared/schemas/gate2b-step02-network-disposition-evidence.schema.json
  shared/schemas/gate2b-step02-architecture-closure.schema.json
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
  checkpoint-semantics.json evidence-manifest.json pinned-source-findings.json predecessor.json
  summary.json targeted-probe-log.txt
)
DISPOSITION_FILES=(
  architecture-disposition.json authorization.json evidence-manifest.json
  network-event-disposition.json provenance.json summary.json
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
  local disposition="$REPO/evidence/gates/gate-2b/runtime-probe-disposition"
  [[ "$(hash_file "$runtime/$DIAGNOSTIC_ID/evidence-manifest.json")" == "6bbb9619df39cfba939f09223bde9ce160b52476598d2b847a0591c3a0edb5f5" ]] || fail "Diagnostic manifest changed"
  [[ "$(hash_file "$runtime/$DIAGNOSTIC_ID/summary.json")" == "e7c2bde43dcc30c8b912099ac2e6682684649ebbd0125a10b5fe0d3940494aee" ]] || fail "Diagnostic summary changed"
  [[ "$(hash_file "$runtime/$FRESH_ID/evidence-manifest.json")" == "8339eca113dfb1bc5cfa15d2fcbc1f95e104d908852e0656024f299f4e2c2b66" ]] || fail "V2 manifest changed"
  [[ "$(hash_file "$runtime/$FRESH_ID/summary.json")" == "b03d7c8a787757b020f889faa8cb3f6393edfb0f477e2a39dd93dbbd868ef349" ]] || fail "V2 summary changed"
  [[ "$(hash_file "$followup/$FOLLOWUP_ID/evidence-manifest.json")" == "6654fd33e10efdf275f0aa9ea104293ed1f7ba3092d054718a9ac0a491b07a79" ]] || fail "Supplemental manifest changed"
  [[ "$(hash_file "$followup/$FOLLOWUP_ID/summary.json")" == "48fa2e41db6089cf63d3f250b8a31c547c322dc8e72d8a25ae9dc1078a734a57" ]] || fail "Supplemental summary changed"
  [[ "$(hash_file "$disposition/$DISPOSITION_ID/evidence-manifest.json")" == "8666c77d3fc7f6a82a88adec652ea30b59198a3ce700ea14069b2ea6496c0f7d" ]] || fail "Disposition manifest changed"
  [[ "$(hash_file "$disposition/$DISPOSITION_ID/summary.json")" == "77d56c2a9df0c3f6c269c1c9b3a5e9a4ec816541827aa5add74b570bcf15ad45" ]] || fail "Disposition summary changed"
  [[ "$(hash_file "$disposition/$DISPOSITION_ID/architecture-disposition.json")" == "ab23b6a78638b7c45346ba0b5419745779f37b56e0fe6c67faac8b49597040d8" ]] || fail "Architecture disposition changed"
}

verify_exact_working_scope() {
  local status line path expected name allowed count=0
  if ! status="$(git -C "$REPO" status --porcelain=v1 --untracked-files=all)"; then fail "Unable to inspect working tree"; fi
  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    path="${line:3}"
    allowed=0
    count=$((count + 1))
    for expected in "${INSTALL_PATHS[@]}"; do [[ "$path" == "$expected" ]] && allowed=1; done
    if [[ "$allowed" == 0 ]]; then
      for name in "${RUNTIME_FILES[@]}"; do
        [[ "$path" == "evidence/gates/gate-2b/runtime-probe/$DIAGNOSTIC_ID/$name" ]] && allowed=1
        [[ "$path" == "evidence/gates/gate-2b/runtime-probe/$FRESH_ID/$name" ]] && allowed=1
      done
    fi
    if [[ "$allowed" == 0 ]]; then
      for name in "${FOLLOWUP_FILES[@]}"; do [[ "$path" == "evidence/gates/gate-2b/runtime-probe-followup/$FOLLOWUP_ID/$name" ]] && allowed=1; done
    fi
    if [[ "$allowed" == 0 ]]; then
      for name in "${DISPOSITION_FILES[@]}"; do [[ "$path" == "evidence/gates/gate-2b/runtime-probe-disposition/$DISPOSITION_ID/$name" ]] && allowed=1; done
    fi
    [[ "$allowed" == 1 ]] || fail "Unexpected Step 2B.02 working-tree path: $path"
  done <<< "$status"
  [[ "$count" -eq "$EXPECTED_PATH_COUNT" ]] || fail "Expected exact $EXPECTED_PATH_COUNT-path closure scope, found $count"
}

verify_run_lifecycle() {
  resolve_git
  local branch head origin_main
  if ! branch="$(git -C "$REPO" branch --show-current)"; then fail "Unable to resolve branch"; fi
  if ! head="$(git -C "$REPO" rev-parse HEAD)"; then fail "Unable to resolve HEAD"; fi
  if ! origin_main="$(git -C "$REPO" rev-parse origin/main)"; then fail "Unable to resolve origin/main"; fi
  [[ "$branch" == "$FEATURE_BRANCH" ]] || fail "Run requires the exact Step 2B.02 feature branch"
  [[ "$head" == "$BASE" ]] || fail "Run requires the exact merged predecessor HEAD"
  [[ "$origin_main" == "$BASE" ]] || fail "Run requires unchanged predecessor origin/main"
  verify_exact_working_scope
  verify_retained
}

verify_audit_lifecycle() {
  resolve_git
  local head
  if ! head="$(git -C "$REPO" rev-parse HEAD)"; then fail "Unable to resolve HEAD"; fi
  git -C "$REPO" merge-base --is-ancestor "$BASE" "$head" || fail "Step 2B.02 merged predecessor is absent from current ancestry"
  verify_retained
}

permanent_audit() {
  (cd "$REPO" && bash scripts/run-gate2b-step02-version-check-path-classification-and-architecture-disposition.sh audit "$DISPOSITION_ID")
  (cd "$REPO" && "$REPO/crewai/.venv/bin/python" scripts/gate2b_step02_audit.py --repo "$REPO" --closure)
}

case "$MODE" in
  run)
    verify_run_lifecycle
    permanent_audit
    printf '[PASS] Gate 2B Step 2B.02 ADR/architecture closure boundary passed.\n'
    printf '[STOP] Step 2B.03 is named but remains unbegun pending commit, merge, resynchronization, post-merge audit, and human approval.\n'
    ;;
  audit)
    verify_audit_lifecycle
    permanent_audit
    ;;
  *) fail "Usage: bash scripts/run-gate2b-step02-crewai-architecture-closure.sh {run|audit}" ;;
esac
