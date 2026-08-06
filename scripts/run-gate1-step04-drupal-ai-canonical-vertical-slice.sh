#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
DRUPAL="$REPO/drupal"
PYTHON="$REPO/crewai/.venv/bin/python"
PHP_SCRIPT="$DRUPAL/scripts/gate1-step04-canonical-vertical-slice.php"
AUDITOR="$REPO/scripts/gate1_step04_canonical_slice_audit.py"
FINALIZER="$REPO/scripts/gate1_step04_finalize.py"
EVIDENCE_ROOT="$REPO/evidence/gates/gate-1/drupal-ai-canonical-vertical-slice"
ACTIVE_FILE="$EVIDENCE_ROOT/.active-run"
EXPECTED_BASELINE="da08ef1f41dc480d7bcdcba08d020f9d3aae2387"

fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }
pass() { printf '[PASS] %s\n' "$*"; }
info() { printf '[INFO] %s\n' "$*"; }

run_drupal() {
  local mode="$1"; shift || true
  (
    cd "$DRUPAL"
    ddev drush --quiet php:script scripts/gate1-step04-canonical-vertical-slice.php -- "$mode" "$@"
  )
}

module_enabled() {
  (
    cd "$DRUPAL"
    ddev drush pm:list --type=module --status=enabled --format=list
  ) | grep -Fx 'agentic_harness_drupal_ai' >/dev/null
}

restore_snapshot() {
  local snapshot="$1"
  (
    cd "$DRUPAL"
    ddev snapshot restore "$snapshot" >/dev/null
    ddev drush cr >/dev/null
    ddev snapshot --cleanup --name "$snapshot" -y >/dev/null
  )
}

active_run_dir() {
  [[ -s "$ACTIVE_FILE" ]] || fail "No active Step 1.04 run."
  local rel
  rel="$(<"$ACTIVE_FILE")"
  [[ "$rel" == evidence/gates/gate-1/drupal-ai-canonical-vertical-slice/* ]] || fail "Active-run pointer is invalid."
  [[ -d "$REPO/$rel" ]] || fail "Active-run directory is unavailable."
  printf '%s\n' "$REPO/$rel"
}

verify_worktree_scope() {
  "$PYTHON" - "$REPO" "$MODE" <<'PY_SCOPE'
import subprocess, sys
from pathlib import Path
repo = Path(sys.argv[1])
mode = sys.argv[2]
allowed_exact = {
    "docs/gates/GATE-1-STEP04-DRUPAL-AI-CANONICAL-VERTICAL-SLICE.md",
    "drupal/scripts/gate1-step04-canonical-vertical-slice.php",
    "drupal/web/modules/custom/agentic_harness_drupal_ai/src/Service/FileEntityResolver.php",
    "scripts/gate1_step04_file_transport_clarification_audit.py",
    "scripts/gate1_step04_canonical_slice_audit.py",
    "scripts/gate1_step04_finalize.py",
    "scripts/run-gate1-step04-drupal-ai-canonical-vertical-slice.sh",
}
if mode == "audit":
    allowed_exact |= {"PLAN.md", "README.md", "docs/CURRENT-STATUS.md"}
allowed_prefixes = ("evidence/gates/gate-1/drupal-ai-canonical-vertical-slice/",)
output = subprocess.run(
    ["git", "-C", str(repo), "status", "--porcelain=v1", "--untracked-files=all"],
    check=True, capture_output=True, text=True,
).stdout
unexpected = []
for line in output.splitlines():
    if not line:
        continue
    path = line[3:]
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    if path in allowed_exact or path.startswith(allowed_prefixes):
        continue
    unexpected.append(path)
if unexpected:
    raise SystemExit(f"[ERROR] Unexpected working-tree paths: {sorted(unexpected)}")
PY_SCOPE
}

verify_installed() {
  [[ -x "$PYTHON" ]] || fail "Locked Python environment is unavailable."
  [[ -f "$PHP_SCRIPT" && -f "$AUDITOR" && -f "$FINALIZER" ]] || fail "Step 1.04 implementation is incomplete."
  git -C "$REPO" merge-base --is-ancestor "$EXPECTED_BASELINE" HEAD || fail "PR #9 merge is not in ancestry."
  if [[ "$MODE" != "audit" ]]; then
    [[ "$(git -C "$REPO" branch --show-current)" == "main" ]] || fail "Operational Step 1.04 commands require branch main."
    [[ "$(git -C "$REPO" rev-parse HEAD)" == "$EXPECTED_BASELINE" ]] || fail "Operational Step 1.04 commands require the PR #9 merge commit at HEAD."
    [[ "$(git -C "$REPO" rev-parse origin/main)" == "$EXPECTED_BASELINE" ]] || fail "origin/main is not synchronized to the PR #9 baseline."
  fi
  verify_worktree_scope
  bash -n "$0"
  "$PYTHON" -m py_compile "$AUDITOR" "$FINALIZER" "$REPO/scripts/gate1_step04_file_transport_clarification_audit.py"
  "$PYTHON" "$AUDITOR" --repo "$REPO" >/dev/null
}

run_predecessors() {
  local output="$1"
  mkdir -p "$output"
  local names=(
    gate05 step01 step01-compatibility step02 step03
    step04-boundary-reconciliation step04-file-transport
  )
  local commands=(
    "scripts/run-gate05-step05.sh audit"
    "scripts/run-gate1-step01.sh audit"
    "scripts/run-gate1-step01-audit-compatibility.sh audit"
    "scripts/run-gate1-step02.sh audit"
    "scripts/run-gate1-step03.sh audit"
    "scripts/run-gate1-step04-boundary-reconciliation.sh audit"
    "scripts/run-gate1-step04-file-transport-clarification.sh audit"
  )
  local i
  for i in "${!names[@]}"; do
    info "Auditing ${names[$i]}..."
    if ! (cd "$REPO" && bash -lc "${commands[$i]}") >"$output/${names[$i]}.log" 2>&1; then
      tail -n 80 "$output/${names[$i]}.log" >&2
      fail "Predecessor audit failed: ${names[$i]}"
    fi
  done
}

require_seeded_clean() {
  local file="$1" label="$2"
  "$PYTHON" - "$file" "$label" <<'PY'
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
if value.get("seeded_clean") is not True:
    raise SystemExit(f"[ERROR] {sys.argv[2]} is not seeded-clean")
expected = {
    "article_count": 20,
    "suggestion_count": 0,
    "target_count": 12,
    "canonical_target_sequence": 1,
    "target_sequence_sha256": "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728",
    "article_source_sha256": "f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17",
    "runtime_state_present": False,
    "temporary_agent_config_present": False,
}
for key, expected_value in expected.items():
    if value.get(key) != expected_value:
        raise SystemExit(f"[ERROR] {sys.argv[2]} differs: {key}")
PY
}

compare_states() {
  local before="$1" after="$2"
  "$PYTHON" - "$before" "$after" <<'PY'
import json, sys
before = json.load(open(sys.argv[1], encoding="utf-8"))
after = json.load(open(sys.argv[2], encoding="utf-8"))
keys = (
    "article_count", "suggestion_count", "target_count", "canonical_target_sequence",
    "target_sequence_sha256", "article_source_sha256", "runtime_state_present",
    "temporary_agent_config_present", "seeded_clean",
)
for key in keys:
    if before.get(key) != after.get(key):
        raise SystemExit(f"[ERROR] Reset-bounded state differs: {key}")
PY
}

write_retained_documents() {
  local run_dir="$1"
  "$PYTHON" - "$run_dir" <<'PY'
import json, sys
from datetime import datetime, timezone
from pathlib import Path

run_dir = Path(sys.argv[1])
start = json.loads((run_dir / "start-result.json").read_text(encoding="utf-8"))
resume = json.loads((run_dir / "resume-result.json").read_text(encoding="utf-8"))
before = json.loads((run_dir / "before-state.json").read_text(encoding="utf-8"))
after = json.loads((run_dir / "after-state.json").read_text(encoding="utf-8"))

(run_dir / "lifecycle-evidence.json").write_text(
    json.dumps(resume["lifecycle"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
(run_dir / "implementation-evidence.json").write_text(
    json.dumps(resume["supplemental"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
(run_dir / "completed-state.json").write_text(
    json.dumps(resume["state"], indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
summary = {
    "schema_version": 1,
    "status": "pass",
    "gate_run_id": run_dir.name,
    "run_id": start["run_id"],
    "package": "gate-1-step04-drupal-ai-canonical-vertical-slice",
    "package_version": "1.0.0",
    "baseline_commit": "da08ef1f41dc480d7bcdcba08d020f9d3aae2387",
    "canonical_target_sequence": 1,
    "target_sequence_sha256": "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728",
    "article_source_sha256": "f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17",
    "provider": "openai",
    "model": "gpt-4.1-mini-2025-04-14",
    "temperature": 0.0,
    "provider_request_count_start": start["provider_request_count"],
    "provider_request_count_resume": resume["provider_request_count"],
    "agent_request_count_start": start["agent_request_count"],
    "agent_request_count_resume": resume["agent_request_count"],
    "automatic_retries": start["automatic_retries"],
    "model_callable_tools": 0,
    "human_review_required": True,
    "reviewer_username": resume["approved_status"]["reviewer_username"],
    "raw_image_retained": False,
    "post_image_wrapper_serialization_performed": False,
    "batch_contract_conformance": False,
    "batch_evidence_root_used": False,
    "seeded_clean_before": before["seeded_clean"],
    "seeded_clean_after": after["seeded_clean"],
    "status_documents_advanced_to_step_1_05": True,
    "step_1_05_started": False,
    "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
}
(run_dir / "summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
(run_dir / "summary.md").write_text(
    "# Gate 1 Step 1.04 Drupal AI Canonical Vertical Slice\n\n"
    f"- **Status:** PASS\n- **Gate run ID:** `{run_dir.name}`\n"
    f"- **Model run ID:** `{start['run_id']}`\n"
    "- **Canonical targets:** 1 (sequence 1)\n"
    "- **Provider/model:** `openai` / `gpt-4.1-mini-2025-04-14`\n"
    "- **Provider requests:** 1 during start; 0 during resume\n"
    "- **Automatic retries:** 0\n- **Model-callable tools:** 0\n"
    "- **Human review:** real approval by `editor_dana`\n"
    "- **Image evidence:** metadata/hash only; no URI, path, entity, bytes, Base64, or data URL retained\n"
    "- **Restoration:** 20 Articles, 0 recommendations, 12 targets, no runtime state or temporary config\n"
    "- **Batch conformance / Step 1.05:** not claimed; not started\n",
    encoding="utf-8",
)
PY
}

write_manifests() {
  local run_dir="$1"
  (
    cd "$REPO"
    sha256sum \
      PLAN.md \
      README.md \
      docs/CURRENT-STATUS.md \
      docs/gates/GATE-1-STEP04-DRUPAL-AI-CANONICAL-VERTICAL-SLICE.md \
      drupal/web/modules/custom/agentic_harness_drupal_ai/src/Service/FileEntityResolver.php \
      drupal/scripts/gate1-step04-canonical-vertical-slice.php \
      scripts/gate1_step04_file_transport_clarification_audit.py \
      scripts/gate1_step04_canonical_slice_audit.py \
      scripts/gate1_step04_finalize.py \
      scripts/run-gate1-step04-drupal-ai-canonical-vertical-slice.sh \
      >"$run_dir/installed-files-sha256.txt"
  )
  (
    cd "$run_dir"
    find . -type f \
      ! -name package-files-sha256.txt \
      ! -name final-audit.json \
      -printf '%P\n' | sort | xargs sha256sum >package-files-sha256.txt
  )
}

verify_installed

case "$MODE" in
  preflight)
    [[ ! -e "$ACTIVE_FILE" ]] || fail "An active Step 1.04 run already exists."
    module_enabled && fail "Preflight requires the restored module-disabled state."
    temp="$(mktemp -d)"
    snapshot="gate1-step04-preflight-$(date -u +%Y%m%dT%H%M%SZ)-$$"
    snapshot_created=0
    restored=0
    cleanup_preflight() {
      local rc=$?
      if [[ "$snapshot_created" -eq 1 && "$restored" -eq 0 ]]; then
        restore_snapshot "$snapshot" || rc=1
      fi
      rm -rf "$temp"
      exit "$rc"
    }
    trap cleanup_preflight EXIT INT TERM
    run_predecessors "$temp/predecessors"
    run_drupal snapshot >"$temp/before-state.json"
    require_seeded_clean "$temp/before-state.json" "preflight before-state"
    (
      cd "$DRUPAL"
      ddev exec php -l scripts/gate1-step04-canonical-vertical-slice.php >/dev/null
      ddev exec php -l web/modules/custom/agentic_harness_drupal_ai/src/Service/FileEntityResolver.php >/dev/null
      ddev snapshot --name "$snapshot" >/dev/null
    )
    snapshot_created=1
    (
      cd "$DRUPAL"
      ddev drush en agentic_harness_drupal_ai -y >/dev/null
      ddev drush cr >/dev/null
    )
    run_drupal preflight >"$temp/preflight.json"
    "$PYTHON" - "$temp/preflight.json" <<'PY'
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
required = {
    "status": "pass",
    "provider_request_count": 0,
    "agent_request_count": 0,
    "model_call_performed": False,
    "network_call_performed": False,
    "file_identity_verified": True,
    "raw_image_retained": False,
    "uri_or_path_retained": False,
    "model_callable_tool_count": 0,
    "configured_key_reference_present": True,
    "configured_key_value_retained": False,
}
for key, expected in required.items():
    if value.get(key) != expected:
        raise SystemExit(f"[ERROR] Preflight field differs: {key}")
if value.get("file_negative_controls_rejected", 0) < 6:
    raise SystemExit("[ERROR] File resolver negative controls are incomplete")
PY
    restore_snapshot "$snapshot"
    restored=1
    module_enabled && fail "Preflight snapshot restoration left the custom module enabled."
    run_drupal snapshot >"$temp/after-state.json"
    require_seeded_clean "$temp/after-state.json" "preflight after-state"
    compare_states "$temp/before-state.json" "$temp/after-state.json"
    cat "$temp/preflight.json"
    trap - EXIT INT TERM
    rm -rf "$temp"
    pass "Step 1.04 reset-bounded preflight passed with zero agent/provider requests."
    ;;

  start)
    [[ ! -e "$ACTIVE_FILE" ]] || fail "An active Step 1.04 run already exists."
    module_enabled && fail "Start requires the restored module-disabled state."
    run_id="drupal_ai-$(date -u +%Y%m%dT%H%M%SZ)-$(printf '%04x' "$$")"
    gate_id="gate1-step04-$(date -u +%Y%m%dT%H%M%SZ)-$$"
    run_dir="$EVIDENCE_ROOT/$gate_id"
    snapshot="gate1-step04-pre-$gate_id"
    mkdir -p "$run_dir"
    start_succeeded=0
    snapshot_created=0
    cleanup_start() {
      local rc=$?
      if [[ "$start_succeeded" -eq 0 ]]; then
        if [[ "$snapshot_created" -eq 1 ]]; then
          restore_snapshot "$snapshot" || rc=1
        fi
        rm -f "$ACTIVE_FILE"
        rm -rf "$run_dir"
      fi
      exit "$rc"
    }
    trap cleanup_start EXIT INT TERM
    run_predecessors "$run_dir/predecessors"
    run_drupal snapshot >"$run_dir/before-state.json"
    require_seeded_clean "$run_dir/before-state.json" "start before-state"
    (
      cd "$DRUPAL"
      ddev snapshot --name "$snapshot" >/dev/null
    )
    snapshot_created=1
    (
      cd "$DRUPAL"
      ddev drush en agentic_harness_drupal_ai -y >/dev/null
      ddev drush cr >/dev/null
    )
    mkdir -p "$EVIDENCE_ROOT"
    printf '%s\n' "${run_dir#"$REPO/"}" >"$ACTIVE_FILE"
    printf '%s\n' "$snapshot" >"$run_dir/snapshot-name.txt"
    printf '%s\n' "$run_id" >"$run_dir/model-run-id.txt"
    run_drupal start "$run_id" >"$run_dir/start-result.json"
    "$PYTHON" - "$run_dir/start-result.json" <<'PY'
import json, re, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
required = {
    "status": "awaiting_human_review",
    "provider_request_count": 1,
    "agent_request_count": 1,
    "automatic_retries": 0,
    "raw_image_retained": False,
    "post_image_wrapper_serialization_performed": False,
    "step_1_05_started": False,
}
for key, expected in required.items():
    if value.get(key) != expected:
        raise SystemExit(f"[ERROR] Start field differs: {key}")
encoded = json.dumps(value, sort_keys=True)
if re.search(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]{16,}", encoded, re.I):
    raise SystemExit("[ERROR] Start result retained an image data URL")
if len(value.get("lifecycle", {}).get("human_review", [])) != 0:
    raise SystemExit("[ERROR] Start simulated human review")
PY
    start_succeeded=1
    trap - EXIT INT TERM
    cat "$run_dir/start-result.json"
    pass "One provider request completed and the run is awaiting real human review."
    info "Approve the displayed recommendation as editor_dana, then run: bash scripts/run-gate1-step04-drupal-ai-canonical-vertical-slice.sh resume"
    ;;

  status)
    run_dir="$(active_run_dir)"
    run_drupal status | tee "$run_dir/status-current.json"
    ;;

  resume)
    run_dir="$(active_run_dir)"
    snapshot="$(<"$run_dir/snapshot-name.txt")"
    if ! run_drupal resume >"$run_dir/resume-result.json"; then
      fail "Resume did not observe an approved editor_dana decision. State remains awaiting review; run status and retry after approval."
    fi
    "$PYTHON" - "$run_dir/resume-result.json" <<'PY'
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
required = {
    "status": "completed",
    "provider_request_count": 0,
    "agent_request_count": 0,
    "model_call_count_total": 1,
    "step_1_05_started": False,
}
for key, expected in required.items():
    if value.get(key) != expected:
        raise SystemExit(f"[ERROR] Resume field differs: {key}")
if value.get("approved_status", {}).get("reviewer_username") != "editor_dana":
    raise SystemExit("[ERROR] Resume reviewer differs")
PY
    restore_snapshot "$snapshot"
    module_enabled && fail "Resume restoration left the custom module enabled."
    run_drupal snapshot >"$run_dir/after-state.json"
    require_seeded_clean "$run_dir/after-state.json" "resume after-state"
    compare_states "$run_dir/before-state.json" "$run_dir/after-state.json"
    write_retained_documents "$run_dir"

    backup="$(mktemp -d)"
    cp "$REPO/PLAN.md" "$backup/PLAN.md"
    cp "$REPO/README.md" "$backup/README.md"
    cp "$REPO/docs/CURRENT-STATUS.md" "$backup/CURRENT-STATUS.md"
    promotion_complete=0
    cleanup_resume() {
      local rc=$?
      if [[ "$promotion_complete" -eq 0 ]]; then
        cp "$backup/PLAN.md" "$REPO/PLAN.md"
        cp "$backup/README.md" "$REPO/README.md"
        cp "$backup/CURRENT-STATUS.md" "$REPO/docs/CURRENT-STATUS.md"
        rm -f "$EVIDENCE_ROOT/GATE1-STEP04-LAST-RUN.txt" "$EVIDENCE_ROOT/GATE1-STEP04-LATEST.txt"
        rm -f "$ACTIVE_FILE"
        printf '[ERROR] Step 1.04 evidence was not promoted; status documents were restored. Unpromoted run retained at %s\n' "${run_dir#"$REPO/"}" >&2
      fi
      rm -rf "$backup"
      exit "$rc"
    }
    trap cleanup_resume EXIT INT TERM

    "$PYTHON" "$FINALIZER" --repo "$REPO" --run-id "$(basename "$run_dir")"
    run_predecessors "$run_dir/predecessors-final"
    write_manifests "$run_dir"
    "$PYTHON" "$AUDITOR" --repo "$REPO" --run-dir "$run_dir" >"$run_dir/final-audit.json"
    (
      cd "$run_dir"
      sha256sum -c package-files-sha256.txt >/dev/null
    )
    printf '%s\n' "${run_dir#"$REPO/"}" >"$EVIDENCE_ROOT/GATE1-STEP04-LAST-RUN.txt"
    printf '%s\n' "${run_dir#"$REPO/"}" >"$EVIDENCE_ROOT/GATE1-STEP04-LATEST.txt"
    rm -f "$ACTIVE_FILE"
    promotion_complete=1
    trap - EXIT INT TERM
    rm -rf "$backup"
    pass "Step 1.04 completed, retained, status-advanced, and restored to seeded-clean state."
    pass "Evidence: ${run_dir#"$REPO/"}"
    pass "Next package: gate-1-step05-drupal-ai-batch-runner-v1.0.0"
    ;;

  restore)
    run_dir="$(active_run_dir)"
    snapshot="$(<"$run_dir/snapshot-name.txt")"
    restore_snapshot "$snapshot"
    module_enabled && fail "Abort restoration left the custom module enabled."
    rm -f "$ACTIVE_FILE"
    rm -rf "$run_dir"
    pass "Active Step 1.04 run was aborted and exact pre-run state restored."
    ;;

  audit)
    [[ ! -e "$ACTIVE_FILE" ]] || fail "Cannot audit while a Step 1.04 run is active."
    module_enabled && fail "Audit requires the restored module-disabled state."
    latest="$EVIDENCE_ROOT/GATE1-STEP04-LATEST.txt"
    last="$EVIDENCE_ROOT/GATE1-STEP04-LAST-RUN.txt"
    [[ -s "$latest" && -s "$last" ]] || fail "Accepted Step 1.04 evidence pointers are missing."
    [[ "$(<"$latest")" == "$(<"$last")" ]] || fail "Step 1.04 LAST and LATEST pointers differ."
    run_dir="$REPO/$(<"$latest")"
    [[ -d "$run_dir" ]] || fail "Accepted Step 1.04 evidence directory is missing."
    temporary="$(mktemp -d)"
    trap 'rm -rf "$temporary"' EXIT
    run_predecessors "$temporary/predecessors"
    run_drupal snapshot >"$temporary/current-state.json"
    require_seeded_clean "$temporary/current-state.json" "audit current-state"
    compare_states "$run_dir/after-state.json" "$temporary/current-state.json"
    "$PYTHON" "$AUDITOR" --repo "$REPO" --run-dir "$run_dir"
    pass "Gate 1 Step 1.04 audit passed."
    pass "Evidence: ${run_dir#"$REPO/"}"
    ;;

  *)
    fail "Usage: bash scripts/run-gate1-step04-drupal-ai-canonical-vertical-slice.sh {preflight|start|status|resume|restore|audit}"
    ;;
esac
