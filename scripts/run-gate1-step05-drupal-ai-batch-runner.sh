#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
DRUPAL="$REPO/drupal"
PYTHON="$REPO/crewai/.venv/bin/python"
PHP_SCRIPT="$DRUPAL/scripts/gate1-step05-drupal-ai-batch-runner.php"
AUDITOR="$REPO/scripts/gate1_step05_batch_runner_audit.py"
FINALIZER="$REPO/scripts/gate1_step05_finalize.py"
GATE_ROOT="$REPO/evidence/gates/gate-1/drupal-ai-batch-runner"
RESULT_ROOT="$REPO/evidence/results/drupal_ai"
ACTIVE_FILE="$GATE_ROOT/.active-run"
LAST_FILE="$GATE_ROOT/GATE1-STEP05-LAST-RUN.txt"
LATEST_FILE="$GATE_ROOT/GATE1-STEP05-LATEST.txt"
EXPECTED_BASELINE="5e01aa49dcb253af429f984e46aa732656565c05"
TARGET_SHA="1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728"
SOURCE_SHA="f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17"

fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }
pass() { printf '[PASS] %s\n' "$*"; }
info() { printf '[INFO] %s\n' "$*"; }

run_drupal() {
  local mode="$1"; shift || true
  (
    cd "$DRUPAL"
    ddev drush --quiet php:script scripts/gate1-step05-drupal-ai-batch-runner.php -- "$mode" "$@"
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

snapshot_exists() {
  local snapshot="$1"
  (
    cd "$DRUPAL"
    ddev snapshot --list 2>/dev/null || true
  ) | grep -F "$snapshot" >/dev/null
}

active_run_dir() {
  [[ -s "$ACTIVE_FILE" ]] || fail "No active Step 1.05 run."
  local rel
  rel="$(<"$ACTIVE_FILE")"
  [[ "$rel" == evidence/gates/gate-1/drupal-ai-batch-runner/* ]] || fail "Active Step 1.05 pointer is invalid."
  [[ -d "$REPO/$rel" ]] || fail "Active Step 1.05 run directory is unavailable."
  printf '%s\n' "$REPO/$rel"
}

verify_worktree_scope() {
  "$PYTHON" - "$REPO" <<'PY_SCOPE'
import subprocess, sys
from pathlib import Path
repo = Path(sys.argv[1])
allowed_exact = {
    "PLAN.md",
    "README.md",
    "docs/CURRENT-STATUS.md",
    "scripts/gate1_step04_boundary_reconciliation_audit.py",
    "scripts/gate1_step04_file_transport_clarification_audit.py",
    "scripts/gate1_step04_canonical_slice_audit.py",
    "scripts/run-gate1-step04-drupal-ai-canonical-vertical-slice.sh",
    "docs/gates/GATE-1-STEP05-DRUPAL-AI-BATCH-RUNNER.md",
    "docs/decisions/ADR-0009-drupal-ai-moderation-rate-aware-pacing.md",
    "drupal/scripts/gate1-step05-drupal-ai-batch-runner.php",
    "scripts/gate1_step05_batch_runner_audit.py",
    "scripts/gate1_step05_finalize.py",
    "scripts/run-gate1-step05-drupal-ai-batch-runner.sh",
}
allowed_prefixes = (
    "evidence/gates/gate-1/drupal-ai-batch-runner/",
    "evidence/results/drupal_ai/",
)
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
    raise SystemExit(f"[ERROR] Unexpected Step 1.05 working-tree paths: {sorted(unexpected)}")
PY_SCOPE
}

verify_installed() {
  [[ -x "$PYTHON" ]] || fail "Locked Python environment is unavailable."
  [[ -f "$PHP_SCRIPT" && -f "$AUDITOR" && -f "$FINALIZER" ]] || fail "Step 1.05 implementation is incomplete."
  git -C "$REPO" merge-base --is-ancestor "$EXPECTED_BASELINE" HEAD || fail "PR #10 merge is not in ancestry."
  if [[ "$MODE" != "audit" ]]; then
    [[ "$(git -C "$REPO" branch --show-current)" == "main" ]] || fail "Operational Step 1.05 commands require branch main."
    [[ "$(git -C "$REPO" rev-parse HEAD)" == "$EXPECTED_BASELINE" ]] || fail "Operational Step 1.05 commands require PR #10 merge at HEAD."
    [[ "$(git -C "$REPO" rev-parse origin/main)" == "$EXPECTED_BASELINE" ]] || fail "origin/main is not synchronized to PR #10."
  fi
  verify_worktree_scope
  bash -n "$0"
  "$PYTHON" - "$AUDITOR" "$FINALIZER" <<'PY_SYNTAX'
from pathlib import Path
import sys
for name in sys.argv[1:]:
    compile(Path(name).read_text(encoding="utf-8"), name, "exec")
PY_SYNTAX
  (
    cd "$DRUPAL"
    ddev exec php -l scripts/gate1-step05-drupal-ai-batch-runner.php >/dev/null
  )
  "$PYTHON" "$AUDITOR" --repo "$REPO" >/dev/null
}

run_predecessors() {
  local output="$1"
  mkdir -p "$output"
  local names=(
    gate05 step01 step01-compatibility step02 step03
    step04-boundary-reconciliation step04-file-transport step04-canonical-slice
  )
  local commands=(
    "scripts/run-gate05-step05.sh audit"
    "scripts/run-gate1-step01.sh audit"
    "scripts/run-gate1-step01-audit-compatibility.sh audit"
    "scripts/run-gate1-step02.sh audit"
    "scripts/run-gate1-step03.sh audit"
    "scripts/run-gate1-step04-boundary-reconciliation.sh audit"
    "scripts/run-gate1-step04-file-transport-clarification.sh audit"
    "scripts/run-gate1-step04-drupal-ai-canonical-vertical-slice.sh audit"
  )
  local i
  for i in "${!names[@]}"; do
    info "Auditing ${names[$i]}..."
    if ! (cd "$REPO" && bash -lc "${commands[$i]}") >"$output/${names[$i]}.log" 2>&1; then
      tail -n 100 "$output/${names[$i]}.log" >&2
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
    "runtime_artifacts_present": False,
    "temporary_agent_config_present": False,
}
for key, expected_value in expected.items():
    if value.get(key) != expected_value:
        raise SystemExit(f"[ERROR] {sys.argv[2]} differs: {key}")
PY
}

require_interrupted_state() {
  local file="$1"
  "$PYTHON" - "$file" <<'PY'
import json, sys
value=json.load(open(sys.argv[1], encoding="utf-8"))
expected={
    "article_count":20,
    "suggestion_count":6,
    "target_count":12,
    "target_sequence_sha256":"1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728",
    "article_source_sha256":"f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17",
    "runtime_state_present":True,
    "runtime_artifacts_present":True,
    "runtime_status":"interrupted",
    "next_target_index":6,
    "temporary_agent_config_present":True,
}
for key, expected_value in expected.items():
    if value.get(key) != expected_value:
        raise SystemExit(f"[ERROR] Interrupted state differs: {key}: {value.get(key)!r}")
PY
}

require_completed_pending_state() {
  local file="$1"
  "$PYTHON" - "$file" <<'PY'
import json, sys
value=json.load(open(sys.argv[1], encoding="utf-8"))
if value.get("batch_completed_pending_review") is not True:
    raise SystemExit("[ERROR] Post-batch state is not completed/pending-review")
expected={
    "article_count":20,
    "suggestion_count":12,
    "target_count":12,
    "target_sequence_sha256":"1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728",
    "article_source_sha256":"f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17",
    "runtime_state_present":True,
    "runtime_artifacts_present":True,
    "runtime_status":"completed",
    "next_target_index":12,
    "temporary_agent_config_present":False,
}
for key, expected_value in expected.items():
    if value.get(key) != expected_value:
        raise SystemExit(f"[ERROR] Post-batch state differs: {key}: {value.get(key)!r}")
PY
}

compare_seeded_states() {
  local before="$1" after="$2"
  "$PYTHON" - "$before" "$after" <<'PY'
import json, sys
before=json.load(open(sys.argv[1], encoding="utf-8"))
after=json.load(open(sys.argv[2], encoding="utf-8"))
keys=(
    "article_count", "suggestion_count", "target_count", "canonical_target_sequence",
    "target_sequence_sha256", "article_source_sha256", "runtime_state_present",
    "runtime_artifacts_present", "temporary_agent_config_present", "seeded_clean",
)
for key in keys:
    if before.get(key) != after.get(key):
        raise SystemExit(f"[ERROR] Reset-bounded state differs: {key}: {before.get(key)!r} != {after.get(key)!r}")
PY
}

write_results() {
  local gate_run_dir="$1" result_dir="$2"
  "$PYTHON" - "$gate_run_dir" "$result_dir" <<'PY'
import json, sys
from pathlib import Path

gate = Path(sys.argv[1])
result = Path(sys.argv[2])
export = json.loads((gate / "runtime-export.json").read_text(encoding="utf-8"))
state = export["state"]
a = export["artifacts"]
run_id = state["run_id"]
if result.name != run_id:
    raise SystemExit("[ERROR] Result directory differs from runtime run_id")
result.mkdir(parents=True, exist_ok=True)

def dump(name, value):
    (result / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

dump("run.json", state)
dump("targets.json", {
    "schema_version": 1,
    "target_sequence_sha256": "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728",
    "targets": a["targets"],
})
with (result / "events.jsonl").open("w", encoding="utf-8") as fh:
    for event in a["events"]:
        fh.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
dump("tool-traces.json", {
    "schema_version": 1,
    "run_id": run_id,
    "source_framework": "drupal_ai",
    "traces": a["traces"],
})
dump("model-outputs.json", {
    "schema_version": 1,
    "run_id": run_id,
    "framework_origin": "drupal_ai",
    "outputs": a["model_outputs"],
})
dump("recommendations.json", {
    "schema_version": 1,
    "run_id": run_id,
    "source_framework": "drupal_ai",
    "recommendations": a["recommendations"],
})
dump("validation.json", {
    "schema_version": 1,
    "run_id": run_id,
    "source_framework": "drupal_ai",
    "validator_version": "gate05-validator-1.0.0",
    "results": a["validation_results"],
})
dump("submissions.json", {
    "schema_version": 1,
    "run_id": run_id,
    "framework_origin": "drupal_ai",
    "submissions": a["submissions"],
})
dump("statuses.json", {
    "schema_version": 1,
    "run_id": run_id,
    "framework_origin": "drupal_ai",
    "observations": a["statuses"],
})
dump("recovery.json", {
    "schema_version": 1,
    "run_id": run_id,
    "source_framework": "drupal_ai",
    "failure_after_sequence": 6,
    "failure_before_sequence": 7,
    "completed_before_failure": [1,2,3,4,5,6],
    "interrupted_at": state["interrupted_at"],
    "resumed_at": state["resumed_at"],
    "resumed_with_run_id": run_id,
    "resumed_at_sequence": 7,
    "duplicate_count": 0,
    "completed_after_resume": [7,8,9,10,11,12],
})
dump("summary.json", {
    "schema_version": 1,
    "status": "pass",
    "run_id": run_id,
    "source_framework": "drupal_ai",
    "provider": "OpenAI",
    "model": "gpt-4.1-mini-2025-04-14",
    "temperature": 0.0,
    "target_count": 12,
    "completed_count": 12,
    "failed_count": 0,
    "duplicate_count": 0,
    "validator_version": "gate05-validator-1.0.0",
    "review_destination": "alt_text_suggestion",
    "source_article_unchanged": a["source_article_sha256_before"] == a["source_article_sha256_after"],
    "automatic_publication_performed": False,
    "failure_seam_observed": True,
    "resume_sequence": 7,
    "started_at": state["started_at"],
    "completed_at": state["completed_at"],
    "human_review_completed": False,
})
(result / "summary.md").write_text(
    "# Gate 1 Step 1.05 Drupal AI Batch Runner\n\n"
    f"- **Status:** PASS\n- **Run ID:** `{run_id}`\n"
    "- **Targets:** 12 in frozen order\n"
    "- **Provider/model:** `OpenAI` / `gpt-4.1-mini-2025-04-14`\n"
    "- **Provider requests:** 6 before interruption + 6 after resume = 12\n"
    "- **Automatic retries:** 0\n"
    "- **Failure seam:** after sequence 6, before sequence 7\n"
    "- **Resume:** same run ID at sequence 7\n"
    "- **Duplicate recommendations:** 0\n"
    "- **Review state:** 12 recommendations pending; Step 1.06 human review not started\n"
    "- **Source Articles:** unchanged\n",
    encoding="utf-8",
)
# Step 1.06 owns human-review.json.
(result / "human-review.json").unlink(missing_ok=True)
PY
}

write_gate_manifests() {
  local gate_run_dir="$1" result_dir="$2"
  (
    cd "$REPO"
    sha256sum \
      PLAN.md \
      README.md \
      docs/CURRENT-STATUS.md \
      scripts/gate1_step04_boundary_reconciliation_audit.py \
      scripts/gate1_step04_file_transport_clarification_audit.py \
      scripts/gate1_step04_canonical_slice_audit.py \
      scripts/run-gate1-step04-drupal-ai-canonical-vertical-slice.sh \
      docs/gates/GATE-1-STEP05-DRUPAL-AI-BATCH-RUNNER.md \
      drupal/scripts/gate1-step05-drupal-ai-batch-runner.php \
      scripts/gate1_step05_batch_runner_audit.py \
      scripts/gate1_step05_finalize.py \
      scripts/run-gate1-step05-drupal-ai-batch-runner.sh \
      >"$gate_run_dir/installed-files-sha256.txt"
    find "${result_dir#"$REPO/"}" -maxdepth 1 -type f -printf '%p\n' \
      | sort | xargs sha256sum >"$gate_run_dir/result-files-sha256.txt"
  )
  (
    cd "$gate_run_dir"
    find . -type f \
      ! -name package-files-sha256.txt \
      ! -name final-audit.json \
      -printf '%P\n' | sort | xargs sha256sum >package-files-sha256.txt
  )
}

verify_installed

case "$MODE" in
  preflight)
    [[ ! -e "$ACTIVE_FILE" ]] || fail "An active Step 1.05 run already exists."
    module_enabled && fail "Preflight requires the restored module-disabled state."
    temp="$(mktemp -d)"
    snapshot="gate1-step05-preflight-$(date -u +%Y%m%dT%H%M%SZ)-$$"
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
value=json.load(open(sys.argv[1], encoding="utf-8"))
required={
    "status":"pass",
    "target_count":12,
    "file_identity_verified_count":12,
    "failure_after_sequence":6,
    "resume_at_sequence":7,
    "model_callable_tool_count":0,
    "strict_provider_schema_preflight_verified":True,
    "raw_model_output_method":"solve",
    "agent_structured_output_used_as_raw_model_output":False,
    "response_metadata_capture_preflight_verified":True,
    "response_event":"ai_agents.response",
    "response_raw_output_accessor":"getRawOutput",
    "provider_response_content_retained":False,
    "provider_refusal_text_retained":False,
    "provider_exception_capture_preflight_verified":True,
    "provider_exception_event":"Drupal\\ai\\Event\\AiExceptionEvent",
    "provider_exception_accessor":"getException",
    "provider_exception_message_retained":False,
    "provider_exception_input_retained":False,
    "rate_limit_response_diagnostics_preflight_verified":True,
    "rate_limit_exception_class":"OpenAI\\Exceptions\\RateLimitException",
    "rate_limit_response_property":"response",
    "rate_limit_http_status_code":429,
    "rate_limit_response_body_retained":False,
    "rate_limit_response_headers_retained":False,
    "rate_limit_error_message_retained":False,
    "rate_limit_request_id_retained":False,
    "moderation_rate_pacing_preflight_verified":True,
    "moderation_rate_pacing_seconds":65,
    "openai_moderation_enabled":True,
    "configured_key_reference_present":True,
    "configured_key_value_retained":False,
    "provider_request_count":0,
    "agent_request_count":0,
    "model_call_performed":False,
    "network_call_performed":False,
    "raw_image_retained":False,
    "post_image_wrapper_serialization_performed":False,
}
for key, expected in required.items():
    if value.get(key) != expected:
        raise SystemExit(f"[ERROR] Step 1.05 preflight differs: {key}: {value.get(key)!r}")
if value.get("file_negative_controls_rejected", 0) < 6:
    raise SystemExit("[ERROR] Step 1.05 File resolver negative controls are incomplete")
PY
    restore_snapshot "$snapshot"
    restored=1
    module_enabled && fail "Preflight restoration left the custom module enabled."
    run_drupal snapshot >"$temp/after-state.json"
    require_seeded_clean "$temp/after-state.json" "preflight after-state"
    compare_seeded_states "$temp/before-state.json" "$temp/after-state.json"
    cat "$temp/preflight.json"
    trap - EXIT INT TERM
    rm -rf "$temp"
    pass "Step 1.05 reset-bounded preflight passed with zero agent/provider requests."
    ;;

  start)
    [[ ! -e "$ACTIVE_FILE" ]] || fail "An active Step 1.05 run already exists."
    module_enabled && fail "Start requires the restored module-disabled state."
    run_id="drupal_ai-$(date -u +%Y%m%dT%H%M%SZ)-$(printf '%04x' "$$")"
    gate_id="gate1-step05-$(date -u +%Y%m%dT%H%M%SZ)-$$"
    gate_run_dir="$GATE_ROOT/$gate_id"
    result_dir="$RESULT_ROOT/$run_id"
    snapshot="gate1-step05-pre-$gate_id"
    [[ ! -e "$result_dir" ]] || fail "Result path already exists: ${result_dir#"$REPO/"}"
    mkdir -p "$gate_run_dir" "$RESULT_ROOT"
    start_succeeded=0
    failure_diagnostic_preserved=0
    snapshot_created=0
    cleanup_start() {
      local rc=$?
      if [[ "$start_succeeded" -eq 0 && "$failure_diagnostic_preserved" -eq 0 ]]; then
        if [[ "$snapshot_created" -eq 1 ]]; then
          restore_snapshot "$snapshot" || rc=1
        fi
        rm -f "$ACTIVE_FILE"
        rm -rf "$gate_run_dir" "$result_dir"
      elif [[ "$start_succeeded" -eq 1 && "$rc" -ne 0 ]]; then
        printf '[ERROR] Six-call interrupted runtime was preserved after a shell-side failure. Do not rerun start; inspect status/evidence first.\n' >&2
      fi
      exit "$rc"
    }
    trap cleanup_start EXIT INT TERM
    run_predecessors "$gate_run_dir/predecessors"
    run_drupal snapshot >"$gate_run_dir/before-state.json"
    require_seeded_clean "$gate_run_dir/before-state.json" "start before-state"
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
    mkdir -p "$GATE_ROOT"
    printf '%s\n' "${gate_run_dir#"$REPO/"}" >"$ACTIVE_FILE"
    printf '%s\n' "$snapshot" >"$gate_run_dir/snapshot-name.txt"
    printf '%s\n' "$run_id" >"$gate_run_dir/model-run-id.txt"
    printf '%s\n' "${result_dir#"$REPO/"}" >"$gate_run_dir/result-path.txt"
    start_rc=0
    if run_drupal start "$run_id" >"$gate_run_dir/start-result.json" 2>"$gate_run_dir/start-error.log"; then
      :
    else
      start_rc=$?
      # The PHP runtime marks failed state before exiting. Capture only the
      # sanitized status/count projection; never retain raw model output here.
      run_drupal status >"$gate_run_dir/failure-status.json" 2>"$gate_run_dir/failure-status-error.log" || true
      "$PYTHON" - "$gate_run_dir" "$run_id" <<'PY_FAILURE'
import json, re, sys
from pathlib import Path
run_dir = Path(sys.argv[1])
run_id = sys.argv[2]
status_path = run_dir / "failure-status.json"
status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.is_file() and status_path.stat().st_size else {}
error_text = (run_dir / "start-error.log").read_text(encoding="utf-8", errors="replace")
provider_match = re.search(r"provider_exception_diagnostic=(\{.*\})", error_text)
model_match = re.search(r"(?<!provider_exception_)diagnostic=(\{.*\})", error_text)
provider_diagnostic = json.loads(provider_match.group(1)) if provider_match else None
model_diagnostic = json.loads(model_match.group(1)) if model_match else None
summary = {
    "schema_version": 1,
    "status": "failed_start_diagnostic",
    "run_id": run_id,
    "runtime_status": status.get("status"),
    "next_target_index": status.get("next_target_index"),
    "completed_target_count": status.get("completed_target_count"),
    "recommendation_count": status.get("recommendation_count"),
    "pending_status_count": status.get("pending_status_count"),
    "failure_injection_fired": status.get("failure_injection_fired"),
    "model_output_diagnostic": model_diagnostic,
    "provider_exception_diagnostic": provider_diagnostic,
    "raw_model_output_retained": False,
    "provider_exception_message_retained": False,
    "provider_input_retained": False,
    "rate_limit_response_body_retained": False,
    "rate_limit_response_headers_retained": False,
    "rate_limit_error_message_retained": False,
    "rate_limit_request_id_retained": False,
    "result_evidence_promoted": False,
    "step_1_06_started": False,
}
(run_dir / "failure-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY_FAILURE
      restore_snapshot "$snapshot"
      snapshot_created=0
      module_enabled && fail "Failed-start restoration left the custom module enabled."
      run_drupal snapshot >"$gate_run_dir/after-failure-restore-state.json"
      require_seeded_clean "$gate_run_dir/after-failure-restore-state.json" "failed-start restored state"
      rm -f "$ACTIVE_FILE"
      rm -rf "$result_dir"
      failure_root="$GATE_ROOT/failures"
      mkdir -p "$failure_root"
      failure_dir="$failure_root/$gate_id"
      [[ ! -e "$failure_dir" ]] || fail "Failure diagnostic path already exists: ${failure_dir#"$REPO/"}"
      mv "$gate_run_dir" "$failure_dir"
      failure_diagnostic_preserved=1
      printf '[ERROR] Step 1.05 runtime failed before the deterministic midpoint.\n' >&2
      printf '[INFO] Sanitized failed-start diagnostic retained at %s\n' "${failure_dir#"$REPO/"}" >&2
      printf '[INFO] Snapshot restored; do not rerun start until the diagnostic is reviewed.\n' >&2
      exit "$start_rc"
    fi
    # From this point forward the six model calls and interrupted runtime state are
    # preserved for diagnosis/recovery even if a shell-side evidence check fails.
    start_succeeded=1
    "$PYTHON" - "$gate_run_dir/start-result.json" <<'PY'
import json, sys
value=json.load(open(sys.argv[1], encoding="utf-8"))
required={
    "status":"interrupted",
    "failure_injection_fired":True,
    "failure_after_sequence":6,
    "failure_before_sequence":7,
    "resume_at_sequence":7,
    "next_target_index":6,
    "provider_request_count":6,
    "agent_request_count":6,
    "automatic_retries":0,
    "recommendation_count":6,
    "pending_status_count":6,
    "raw_image_retained":False,
    "post_image_wrapper_serialization_performed":False,
    "human_review_started":False,
    "step_1_06_started":False,
}
for key, expected in required.items():
    if value.get(key) != expected:
        raise SystemExit(f"[ERROR] Step 1.05 start differs: {key}: {value.get(key)!r}")
if value.get("completed_sequences") != [1,2,3,4,5,6]:
    raise SystemExit("[ERROR] Step 1.05 start completed sequence differs")
PY
    run_drupal snapshot >"$gate_run_dir/interrupted-state.json"
    require_interrupted_state "$gate_run_dir/interrupted-state.json"
    trap - EXIT INT TERM
    cat "$gate_run_dir/start-result.json"
    pass "Step 1.05 intentionally interrupted after sequence 6 with six persisted recommendations."
    info "Resume the same run with: bash scripts/run-gate1-step05-drupal-ai-batch-runner.sh resume"
    ;;

  status)
    gate_run_dir="$(active_run_dir)"
    run_drupal status | tee "$gate_run_dir/status-current.json"
    ;;

  resume)
    gate_run_dir="$(active_run_dir)"
    module_enabled || fail "Resume requires agentic_harness_drupal_ai to remain enabled."
    run_id="$(<"$gate_run_dir/model-run-id.txt")"
    result_dir="$REPO/$(<"$gate_run_dir/result-path.txt")"
    snapshot="$(<"$gate_run_dir/snapshot-name.txt")"
    snapshot_exists "$snapshot" || fail "Required pre-batch DDEV snapshot is unavailable: $snapshot"

    # Recovery-safe shell boundary: if Drupal already completed sequences 7-12 but
    # the shell was interrupted after PHP returned, do not invoke the model again.
    run_drupal status >"$gate_run_dir/status-before-resume.json"
    runtime_status="$($PYTHON - "$gate_run_dir/status-before-resume.json" <<'PY_STATUS'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8")).get("status", "unknown"))
PY_STATUS
)"
    case "$runtime_status" in
      interrupted)
        run_drupal resume >"$gate_run_dir/resume-result.json"
        ;;
      completed)
        [[ -s "$gate_run_dir/resume-result.json" ]] || fail \
          "Drupal reports a completed batch but resume-result.json is unavailable; stop for evidence repair rather than repeating model calls."
        info "Batch runtime is already completed; reusing retained resume-result.json with zero additional model calls."
        ;;
      *)
        fail "Resume requires runtime status interrupted or a recoverable completed state; found: $runtime_status"
        ;;
    esac

    "$PYTHON" - "$gate_run_dir/resume-result.json" <<'PY_RESUME'
import json, sys
value=json.load(open(sys.argv[1], encoding="utf-8"))
required={
    "status":"completed",
    "resumed_at_sequence":7,
    "provider_request_count":6,
    "agent_request_count":6,
    "model_call_count_total":12,
    "automatic_retries":0,
    "duplicate_count":0,
    "recommendation_count":12,
    "pending_status_count":12,
    "source_article_unchanged":True,
    "human_review_completed":False,
    "raw_image_retained":False,
    "post_image_wrapper_serialization_performed":False,
    "step_1_06_started":False,
}
for key, expected in required.items():
    if value.get(key) != expected:
        raise SystemExit(f"[ERROR] Step 1.05 resume differs: {key}: {value.get(key)!r}")
if value.get("completed_sequences_after_resume") != [7,8,9,10,11,12]:
    raise SystemExit("[ERROR] Step 1.05 resume sequence differs")
PY_RESUME
    run_drupal export >"$gate_run_dir/runtime-export.json"
    run_drupal snapshot >"$gate_run_dir/after-batch-state.json"
    require_completed_pending_state "$gate_run_dir/after-batch-state.json"
    cat "$gate_run_dir/resume-result.json"
    pass "Step 1.05 batch runtime completed with twelve pending recommendations and zero duplicates."
    pass "No Step 1.06 human review has been performed."
    info "Retain and promote the derived evidence without another model call: bash scripts/run-gate1-step05-drupal-ai-batch-runner.sh promote"
    ;;

  promote)
    gate_run_dir="$(active_run_dir)"
    module_enabled || fail "Promotion requires the completed Step 1.05 post-batch state."
    run_id="$(<"$gate_run_dir/model-run-id.txt")"
    result_dir="$REPO/$(<"$gate_run_dir/result-path.txt")"
    snapshot="$(<"$gate_run_dir/snapshot-name.txt")"
    snapshot_exists "$snapshot" || fail "Required Step 1.06 restoration snapshot is unavailable: $snapshot"
    [[ -s "$gate_run_dir/resume-result.json" && -s "$gate_run_dir/runtime-export.json" && -s "$gate_run_dir/after-batch-state.json" ]] \
      || fail "Completed Step 1.05 runtime evidence is unavailable."
    run_drupal snapshot >"$gate_run_dir/promotion-state.json"
    require_completed_pending_state "$gate_run_dir/promotion-state.json"

    # Result files are deterministic derivatives of the retained sanitized runtime
    # export. Rebuild them on every promotion attempt so a repository-only failure
    # never requires repeating model execution.
    rm -rf "$result_dir"
    write_results "$gate_run_dir" "$result_dir"
    "$PYTHON" "$AUDITOR" --repo "$REPO" --gate-run-dir "$gate_run_dir" --result-dir "$result_dir" \
      >"$gate_run_dir/execution-audit.json"

    backup="$(mktemp -d)"
    cp "$REPO/PLAN.md" "$backup/PLAN.md"
    cp "$REPO/README.md" "$backup/README.md"
    cp "$REPO/docs/CURRENT-STATUS.md" "$backup/CURRENT-STATUS.md"
    promotion_complete=0
    cleanup_promote() {
      local rc=$?
      if [[ "$promotion_complete" -eq 0 ]]; then
        cp "$backup/PLAN.md" "$REPO/PLAN.md"
        cp "$backup/README.md" "$REPO/README.md"
        cp "$backup/CURRENT-STATUS.md" "$REPO/docs/CURRENT-STATUS.md"
        rm -f "$LAST_FILE" "$LATEST_FILE"
        rm -f \
          "$gate_run_dir/installed-files-sha256.txt" \
          "$gate_run_dir/result-files-sha256.txt" \
          "$gate_run_dir/package-files-sha256.txt" \
          "$gate_run_dir/final-audit.json"
        printf '[ERROR] Step 1.05 promotion failed; status documents and promotion manifests were restored/removed. Completed run retained at %s\n' "${gate_run_dir#"$REPO/"}" >&2
      fi
      rm -rf "$backup"
      exit "$rc"
    }
    trap cleanup_promote EXIT INT TERM

    "$PYTHON" "$FINALIZER" --repo "$REPO" --gate-run-id "$(basename "$gate_run_dir")" --batch-run-id "$run_id"
    git -C "$REPO" diff --check
    write_gate_manifests "$gate_run_dir" "$result_dir"
    "$PYTHON" "$AUDITOR" --repo "$REPO" --gate-run-dir "$gate_run_dir" --result-dir "$result_dir" >"$gate_run_dir/final-audit.json"
    (
      cd "$gate_run_dir"
      sha256sum -c package-files-sha256.txt >/dev/null
    )
    (
      cd "$REPO"
      sha256sum -c "$gate_run_dir/installed-files-sha256.txt" >/dev/null
      sha256sum -c "$gate_run_dir/result-files-sha256.txt" >/dev/null
    )
    printf '%s\n' "${gate_run_dir#"$REPO/"}" >"$LAST_FILE"
    printf '%s\n' "${gate_run_dir#"$REPO/"}" >"$LATEST_FILE"
    rm -f "$ACTIVE_FILE"
    promotion_complete=1
    trap - EXIT INT TERM
    rm -rf "$backup"
    pass "Step 1.05 execution/evidence promoted; twelve recommendations remain pending for Step 1.06."
    pass "Gate evidence: ${gate_run_dir#"$REPO/"}"
    pass "Batch results: ${result_dir#"$REPO/"}"
    pass "Next package: gate-1-step06-drupal-ai-batch-evidence-and-human-review-v1.0.0"
    ;;

  restore)
    gate_run_dir="$(active_run_dir)"
    snapshot="$(<"$gate_run_dir/snapshot-name.txt")"
    result_dir="$REPO/$(<"$gate_run_dir/result-path.txt")"
    restore_snapshot "$snapshot"
    module_enabled && fail "Restore left agentic_harness_drupal_ai enabled."
    rm -f "$ACTIVE_FILE"
    rm -rf "$gate_run_dir" "$result_dir"
    pass "Active Step 1.05 run aborted and exact pre-batch state restored."
    ;;

  audit)
    [[ ! -e "$ACTIVE_FILE" ]] || fail "Cannot audit while a Step 1.05 run is active/unpromoted."
    module_enabled || fail "Accepted Step 1.05 audit requires the post-batch module-enabled state for Step 1.06 handoff."
    [[ -s "$LATEST_FILE" && -s "$LAST_FILE" ]] || fail "Accepted Step 1.05 evidence pointers are missing."
    [[ "$(<"$LATEST_FILE")" == "$(<"$LAST_FILE")" ]] || fail "Step 1.05 LAST/LATEST pointers differ."
    gate_run_dir="$REPO/$(<"$LATEST_FILE")"
    [[ -d "$gate_run_dir" ]] || fail "Accepted Step 1.05 gate evidence directory is missing."
    result_dir="$REPO/$(<"$gate_run_dir/result-path.txt")"
    snapshot="$(<"$gate_run_dir/snapshot-name.txt")"
    snapshot_exists "$snapshot" || fail "Step 1.06 restoration snapshot is unavailable."
    temporary="$(mktemp -d)"
    trap 'rm -rf "$temporary"' EXIT
    run_drupal snapshot >"$temporary/current-state.json"
    require_completed_pending_state "$temporary/current-state.json"
    "$PYTHON" "$AUDITOR" --repo "$REPO" --gate-run-dir "$gate_run_dir" --result-dir "$result_dir"
    pass "Gate 1 Step 1.05 audit passed."
    pass "Twelve pending recommendations are preserved for Step 1.06 human review."
    pass "Evidence: ${gate_run_dir#"$REPO/"}"
    pass "Results: ${result_dir#"$REPO/"}"
    ;;

  *)
    fail "Usage: bash scripts/run-gate1-step05-drupal-ai-batch-runner.sh {preflight|start|status|resume|promote|restore|audit}"
    ;;
esac
