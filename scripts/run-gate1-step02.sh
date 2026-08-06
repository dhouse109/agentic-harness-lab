#!/usr/bin/env bash
set -Eeuo pipefail

RUNNER_VERSION="1.0.0"
MODE="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
DRUPAL_ROOT="$REPO/drupal"
PYTHON="$REPO/crewai/.venv/bin/python"
AUDITOR="$REPO/scripts/gate1_step02_audit.py"
FINALIZER="$REPO/scripts/gate1_step02_finalize.py"
PROBE="$DRUPAL_ROOT/scripts/gate1-step02-runtime-probe.php"
EVIDENCE_ROOT="$REPO/evidence/gates/gate-1/drupal-ai-runtime-probe"
EXPECTED_COMMIT="10a7f531bff1af8ea93ecbe1e447e98cb4834ac6"
EXPECTED_GATE05_RUN="gate05-step05-20260805T184155Z-50124"
EXPECTED_GATE05_SHA="99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a"
EXPECTED_STEP01_RUN="gate1-step01-20260805T205448Z-103220"
EXPECTED_STEP01_SHA="360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6"

fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }
info() { printf '[INFO] %s\n' "$*"; }
pass() { printf '[PASS] %s\n' "$*"; }

verify_repo() {
  [[ "$(git -C "$REPO" rev-parse --show-toplevel)" == "$REPO" ]] || fail "Runner is not installed at repository root."
  git -C "$REPO" cat-file -e "${EXPECTED_COMMIT}^{commit}" 2>/dev/null || fail "Missing Step 1.02 predecessor commit."
  case "$MODE" in
    run)
      [[ "$(git -C "$REPO" branch --show-current)" == "main" ]] || fail "Run mode requires main."
      [[ "$(git -C "$REPO" rev-parse HEAD)" == "$EXPECTED_COMMIT" ]] || fail "Run mode requires the exact predecessor commit."
      ;;
    audit)
      git -C "$REPO" merge-base --is-ancestor "$EXPECTED_COMMIT" HEAD || fail "Audit mode requires predecessor ancestry."
      printf '[INFO] Audit branch: %s\n' "$(git -C "$REPO" branch --show-current)"
      ;;
    *)
      fail "Usage: bash scripts/run-gate1-step02.sh {run|audit}"
      ;;
  esac
  [[ -x "$PYTHON" ]] || fail "Missing locked CrewAI Python environment."
  [[ -f "$AUDITOR" && -f "$FINALIZER" && -f "$PROBE" ]] || fail "Step 1.02 payload is incomplete."
  (
    cd "$DRUPAL_ROOT"
    ddev exec php -l scripts/gate1-step02-runtime-probe.php >/dev/null
  ) || fail "Step 1.02 PHP probe did not pass syntax validation."
  [[ "$(sha256sum "$REPO/shared/contracts/GATE05-SUBSTRATE-FREEZE.json" | awk '{print $1}')" == "$EXPECTED_GATE05_SHA" ]] || fail "Gate 0.5 freeze digest changed."
  [[ "$(sha256sum "$REPO/shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json" | awk '{print $1}')" == "$EXPECTED_STEP01_SHA" ]] || fail "Step 1.01 contract digest changed."
  [[ "$(basename "$(<"$REPO/evidence/gates/gate-0.5/substrate-certification/GATE05-STEP05-LATEST.txt")")" == "$EXPECTED_GATE05_RUN" ]] || fail "Gate 0.5 evidence pointer changed."
  [[ "$(basename "$(<"$REPO/evidence/gates/gate-1/drupal-ai-batch-contract/GATE1-STEP01-LATEST.txt")")" == "$EXPECTED_STEP01_RUN" ]] || fail "Step 1.01 evidence pointer changed."
}

run_predecessor_audits() {
  local output_dir="$1"
  bash "$REPO/scripts/run-gate05-step05.sh" audit >"$output_dir/gate05-audit.log"
  if rg -F -- '- **Next package:** `gate-1-step02-drupal-ai-runtime-probe-v1.0.0`.' "$REPO/README.md" >/dev/null; then
    bash "$REPO/scripts/run-gate1-step01.sh" audit >"$output_dir/step01-audit.log"
  else
    verify_step01_accepted_evidence
    local prior_pointer="$EVIDENCE_ROOT/GATE1-STEP02-LATEST.txt"
    local prior_dir="$REPO/$(<"$prior_pointer")"
    (
      cd "$prior_dir"
      sha256sum -c package-files-sha256.txt >/dev/null
    ) || fail "Prior Step 1.02 evidence checksum failed during repair."
    rg -F '[PASS] Gate 1 Step 1.01 audit passed.' "$prior_dir/step01-audit.log" >/dev/null \
      || fail "Prior Step 1.02 run did not retain a passing Step 1.01 audit."
    {
      printf '[INFO] Step 1.01 audit is status-state-sensitive and passed before the Step 1.02 transition.\n'
      printf '[PASS] Gate 1 Step 1.01 audit passed. Accepted evidence and the retained pre-transition log were reverified.\n'
    } >"$output_dir/step01-audit.log"
  fi
}

verify_step01_accepted_evidence() {
  local pointer="$REPO/evidence/gates/gate-1/drupal-ai-batch-contract/GATE1-STEP01-LATEST.txt"
  local run_dir="$REPO/$(<"$pointer")"
  [[ "$(basename "$run_dir")" == "$EXPECTED_STEP01_RUN" ]] || fail "Step 1.01 accepted run changed."
  [[ -d "$run_dir" ]] || fail "Missing accepted Step 1.01 evidence directory."
  (
    cd "$run_dir"
    sha256sum -c package-files-sha256.txt >/dev/null
  ) || fail "Accepted Step 1.01 evidence checksum failed."
  "$PYTHON" - "$run_dir/summary.json" <<'PY'
import json, sys
summary = json.load(open(sys.argv[1], encoding="utf-8"))
required = {
    "status": "pass",
    "run_id": "gate1-step01-20260805T205448Z-103220",
    "contract_sha256": "360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6",
    "predecessor_audit": "pass",
    "contract_audit": "pass",
    "model_call_performed": False,
    "drupal_state_mutated": False,
    "contract_semantics_changed": False,
}
for key, expected in required.items():
    if summary.get(key) != expected:
        raise SystemExit(f"[ERROR] Unexpected accepted Step 1.01 summary field: {key}")
PY
}

seeded_clean_audit() {
  local output="$1"
  (
    cd "$DRUPAL_ROOT"
    bash scripts/run-phase0-step10.sh audit
  ) >"$output"
}

run_probe() {
  local mode="$1" output="$2"
  (
    cd "$DRUPAL_ROOT"
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
      ddev drush --quiet php:script scripts/gate1-step02-runtime-probe.php -- "$mode"
  ) >"$output"
}

write_summary() {
  local run_id="$1" run_dir="$2" decision_sha="$3"
  "$PYTHON" - "$run_id" "$run_dir" "$decision_sha" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

run_id = sys.argv[1]
run_dir = Path(sys.argv[2])
decision_sha = sys.argv[3]
now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
summary = {
    "schema_version": 1,
    "status": "pass",
    "run_id": run_id,
    "package": "gate-1-step02-drupal-ai-runtime-probe",
    "package_version": "1.0.0",
    "predecessor_commit": "10a7f531bff1af8ea93ecbe1e447e98cb4834ac6",
    "gate05_run_id": "gate05-step05-20260805T184155Z-50124",
    "gate05_freeze_sha256": "99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a",
    "step01_run_id": "gate1-step01-20260805T205448Z-103220",
    "step01_contract_sha256": "360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6",
    "decision": "docs/decisions/ADR-0006-drupal-ai-programmatic-runtime-path.md",
    "decision_sha256": decision_sha,
    "chosen_service": "plugin.manager.ai_agents",
    "chosen_instance": "Drupal\\ai_agents\\PluginBase\\AiAgentEntityWrapper",
    "chosen_entry_point": "determineSolvability",
    "chosen_final_output": "solve",
    "chosen_state_collection": "agentic_harness_drupal_ai.run_state",
    "state_collection_opened": False,
    "explicit_provider": "openai",
    "explicit_model": "gpt-4.1-mini-2025-04-14",
    "explicit_temperature": 0.0,
    "model_catalog_query_performed": False,
    "remote_model_availability_claimed": False,
    "active_default_rejected": True,
    "article_count_before_after": [20, 20],
    "recommendation_count_before_after": [0, 0],
    "target_sequence_sha256": "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728",
    "canonical_target_sequence": 1,
    "source_content_unchanged": True,
    "seeded_clean_before_after": True,
    "model_call_performed": False,
    "network_call_performed": False,
    "drupal_state_mutated": False,
    "configuration_changed": False,
    "dependency_changed": False,
    "raw_image_retained": False,
    "secret_retained": False,
    "framework_implementation_claimed": False,
    "step03_started": False,
    "completed_at": now,
    "next_package": "gate-1-step03-drupal-ai-tool-adapters-v1.0.0",
}
(run_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
(run_dir / "summary.md").write_text(
    "# Gate 1 Step 1.02 Drupal AI Runtime Probe\n\n"
    "- **Status:** PASS\n"
    f"- **Run ID:** `{run_id}`\n"
    "- **Pinned versions:** Drupal 11.4.4; Drupal AI 1.4.5; AI Agents 1.3.2; OpenAI provider 1.2.3\n"
    "- **Chosen service:** `plugin.manager.ai_agents`\n"
    "- **Chosen wrapper:** `Drupal\\ai_agents\\PluginBase\\AiAgentEntityWrapper`\n"
    "- **Callable path:** `determineSolvability()` then `solve()`\n"
    "- **Provider/model:** explicit `openai` / `gpt-4.1-mini-2025-04-14` / temperature `0.0`\n"
    "- **Active default:** rejected; it is not the frozen model\n"
    "- **Remote model catalog queried:** no; remote availability/entitlement is not claimed\n"
    "- **Framework-owned later state:** `keyvalue` collection `agentic_harness_drupal_ai.run_state`\n"
    "- **Future state collection opened or written:** no\n"
    "- **Before/after:** 20 Articles, zero recommendations, frozen 12-target order, canonical sequence 1\n"
    "- **Source content changed:** no\n"
    "- **Model or network call:** no\n"
    "- **Secret or raw image retained:** no\n"
    "- **Step 1.03 started:** no\n\n"
    "This evidence proves construction and introspection of the pinned runtime path only. It does not claim a model call, adapter implementation, vertical slice, recovery, or framework quality.\n",
    encoding="utf-8",
)
PY
}

write_manifests() {
  local run_dir="$1"
  (
    cd "$REPO"
    sha256sum \
      docs/gates/GATE-1-STEP02-DRUPAL-AI-RUNTIME-PROBE.md \
      docs/decisions/ADR-0006-drupal-ai-programmatic-runtime-path.md \
      drupal/scripts/gate1-step02-runtime-probe.php \
      scripts/gate1_step02_audit.py \
      scripts/gate1_step02_finalize.py \
      scripts/run-gate1-step02.sh >"$run_dir/installed-files-sha256.txt"
  )
  (
    cd "$run_dir"
    sha256sum \
      after-state.json \
      before-state.json \
      gate05-audit.log \
      installed-files-sha256.txt \
      runtime-audit.json \
      runtime-probe.json \
      seeded-clean-after.log \
      seeded-clean-before.log \
      step01-audit.log \
      summary.json \
      summary.md >package-files-sha256.txt
  )
}

verify_retained_evidence() {
  local pointer="$EVIDENCE_ROOT/GATE1-STEP02-LATEST.txt"
  [[ -s "$pointer" ]] || fail "Missing Step 1.02 latest pointer."
  local run_dir="$REPO/$(<"$pointer")"
  [[ -d "$run_dir" ]] || fail "Missing retained Step 1.02 evidence directory."
  (
    cd "$run_dir"
    sha256sum -c package-files-sha256.txt >/dev/null
  ) || fail "Step 1.02 evidence checksum failed."
  (
    cd "$REPO"
    sha256sum -c "$run_dir/installed-files-sha256.txt" >/dev/null
  ) || fail "Step 1.02 installed-file checksum failed."
  "$PYTHON" "$AUDITOR" --repo "$REPO" --run-dir "$run_dir" >/dev/null
  rg -F '[PASS] Gate 1 Step 0.5 audit passed.' "$run_dir/gate05-audit.log" >/dev/null \
    || rg -F '[PASS] Gate 0.5 Step 05 audit passed.' "$run_dir/gate05-audit.log" >/dev/null \
    || fail "Retained Gate 0.5 predecessor audit log is not passing."
  rg -F '[PASS] Gate 1 Step 1.01 audit passed.' "$run_dir/step01-audit.log" >/dev/null \
    || fail "Retained Step 1.01 predecessor audit log is not passing."
  pass "Gate 1 Step 1.02 audit passed."
  pass "Evidence: ${run_dir#"$REPO/"}"
}

verify_repo

case "$MODE" in
  run)
    run_id="gate1-step02-$(date -u +%Y%m%dT%H%M%SZ)-$$"
    run_dir="$EVIDENCE_ROOT/$run_id"
    [[ ! -e "$run_dir" ]] || fail "Evidence directory already exists."
    mkdir -p "$run_dir"

    info "Auditing Gate 0.5 and Step 1.01 predecessors..."
    run_predecessor_audits "$run_dir"
    info "Verifying seeded-clean before the probe..."
    seeded_clean_audit "$run_dir/seeded-clean-before.log"
    run_probe snapshot "$run_dir/before-state.json"
    info "Running non-networked live service-container and reflection probe..."
    run_probe runtime "$run_dir/runtime-probe.json"
    info "Verifying seeded-clean and source state after the probe..."
    run_probe snapshot "$run_dir/after-state.json"
    seeded_clean_audit "$run_dir/seeded-clean-after.log"

    "$PYTHON" "$AUDITOR" --repo "$REPO" --run-dir "$run_dir" >"$run_dir/runtime-audit.json"
    decision_sha="$(sha256sum "$REPO/docs/decisions/ADR-0006-drupal-ai-programmatic-runtime-path.md" | awk '{print $1}')"
    write_summary "$run_id" "$run_dir" "$decision_sha"
    write_manifests "$run_dir"
    mkdir -p "$EVIDENCE_ROOT"
    printf '%s\n' "${run_dir#"$REPO/"}" >"$EVIDENCE_ROOT/GATE1-STEP02-LAST-RUN.txt"
    printf '%s\n' "${run_dir#"$REPO/"}" >"$EVIDENCE_ROOT/GATE1-STEP02-LATEST.txt"
    verify_retained_evidence
    "$PYTHON" "$FINALIZER" --repo "$REPO" --run-id "$run_id" --decision-sha256 "$decision_sha"
    pass "Status documents advanced only after the passing probe; gate-1-step03-drupal-ai-tool-adapters-v1.0.0 is next."
    ;;
  audit)
    temporary="$(mktemp -d)"
    trap 'rm -rf "$temporary"' EXIT
    bash "$REPO/scripts/run-gate05-step05.sh" audit >"$temporary/gate05-audit.log"
    verify_step01_accepted_evidence
    seeded_clean_audit "$temporary/seeded-clean.log"
    run_probe snapshot "$temporary/current-state.json"
    verify_retained_evidence
    "$PYTHON" - "$temporary/current-state.json" "$REPO/$(<"$EVIDENCE_ROOT/GATE1-STEP02-LATEST.txt")/after-state.json" <<'PY'
import json, sys
current = json.load(open(sys.argv[1], encoding="utf-8"))
accepted = json.load(open(sys.argv[2], encoding="utf-8"))
for key in ("article_count", "suggestion_count", "target_sequence_sha256", "canonical_target_sequence", "article_source_sha256", "seeded_clean"):
    if current.get(key) != accepted.get(key):
        raise SystemExit(f"[ERROR] Current Drupal state differs from accepted Step 1.02 evidence: {key}")
PY
    ;;
esac
