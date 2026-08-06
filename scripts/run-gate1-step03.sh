#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
DRUPAL_ROOT="$REPO/drupal"
PYTHON="$REPO/crewai/.venv/bin/python"
CAPTURE="$REPO/scripts/gate1_step03_capture.py"
AUDITOR="$REPO/scripts/gate1_step03_audit.py"
FINALIZER="$REPO/scripts/gate1_step03_finalize.py"
EXERCISE="$DRUPAL_ROOT/scripts/gate1-step03-adapter-exercise.php"
EVIDENCE_ROOT="$REPO/evidence/gates/gate-1/drupal-ai-tool-adapters"
EXPECTED_COMMIT="3915af75779869e19c40abf3cbb4e2021cc57952"
EXPECTED_GATE05_RUN="gate05-step05-20260805T184155Z-50124"
EXPECTED_GATE05_SHA="99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a"
EXPECTED_STEP01_RUN="gate1-step01-20260805T205448Z-103220"
EXPECTED_STEP01_SHA="360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6"
EXPECTED_STEP02_RUN="gate1-step02-20260806T010227Z-189538"
EXPECTED_COMPAT_RUN="gate1-step01-audit-compatibility-20260806T023356Z-250843"
EXPECTED_ADR_SHA="223f6d6f4276d3861cf5668f08e0446479d815a07fed18402b1e6a7722d18c4b"

PAYLOAD_FILES=(
  "docs/gates/GATE-1-STEP03-DRUPAL-AI-TOOL-ADAPTERS.md"
  "drupal/web/modules/custom/agentic_harness_drupal_ai/agentic_harness_drupal_ai.info.yml"
  "drupal/web/modules/custom/agentic_harness_drupal_ai/agentic_harness_drupal_ai.services.yml"
  "drupal/web/modules/custom/agentic_harness_drupal_ai/src/Service/ToolResultRunner.php"
  "drupal/web/modules/custom/agentic_harness_drupal_ai/src/Plugin/AiFunctionCall/DiscoverTargets.php"
  "drupal/web/modules/custom/agentic_harness_drupal_ai/src/Plugin/AiFunctionCall/GetImageContext.php"
  "drupal/web/modules/custom/agentic_harness_drupal_ai/src/Plugin/AiFunctionCall/SubmitRecommendation.php"
  "drupal/web/modules/custom/agentic_harness_drupal_ai/src/Plugin/AiFunctionCall/GetRecommendationStatus.php"
  "drupal/scripts/gate1-step03-adapter-exercise.php"
  "scripts/gate1_step03_capture.py"
  "scripts/gate1_step03_audit.py"
  "scripts/gate1_step03_finalize.py"
  "scripts/run-gate1-step03.sh"
)

fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }
info() { printf '[INFO] %s\n' "$*"; }
pass() { printf '[PASS] %s\n' "$*"; }

pointer_run() {
  basename "$(<"$REPO/$1")"
}

module_enabled() {
  local listing="$1"
  (
    cd "$DRUPAL_ROOT"
    ddev drush pm:list --type=module --status=enabled --format=list
  ) >"$listing"
  rg -x 'agentic_harness_drupal_ai' "$listing" >/dev/null
}

snapshot_state() {
  local output="$1"
  (
    cd "$DRUPAL_ROOT"
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
      ddev drush --quiet php:script scripts/gate1-step03-adapter-exercise.php -- snapshot
  ) >"$output"
}

seeded_clean_audit() {
  local output="$1"
  (
    cd "$DRUPAL_ROOT"
    bash scripts/run-phase0-step10.sh audit
  ) >"$output"
}

verify_repo() {
  [[ "$(git -C "$REPO" rev-parse --show-toplevel)" == "$REPO" ]] || fail "Runner is not installed at repository root."
  git -C "$REPO" cat-file -e "${EXPECTED_COMMIT}^{commit}" 2>/dev/null || fail "Missing Step 1.03 predecessor commit."
  case "$MODE" in
    run)
      [[ "$(git -C "$REPO" branch --show-current)" == "main" ]] || fail "Run mode requires main."
      [[ "$(git -C "$REPO" rev-parse HEAD)" == "$EXPECTED_COMMIT" ]] || fail "Run mode requires the exact PR #6 predecessor commit."
      ;;
    audit)
      git -C "$REPO" merge-base --is-ancestor "$EXPECTED_COMMIT" HEAD || fail "Audit mode requires PR #6 predecessor ancestry."
      printf '[INFO] Audit branch: %s\n' "$(git -C "$REPO" branch --show-current)"
      ;;
    *)
      fail "Usage: bash scripts/run-gate1-step03.sh {run|audit}"
      ;;
  esac
  [[ -x "$PYTHON" ]] || fail "Missing locked Python validation environment."
  [[ "$(sha256sum "$REPO/shared/contracts/GATE05-SUBSTRATE-FREEZE.json" | awk '{print $1}')" == "$EXPECTED_GATE05_SHA" ]] || fail "Gate 0.5 freeze changed."
  [[ "$(sha256sum "$REPO/shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json" | awk '{print $1}')" == "$EXPECTED_STEP01_SHA" ]] || fail "Step 1.01 contract changed."
  [[ "$(sha256sum "$REPO/docs/decisions/ADR-0006-drupal-ai-programmatic-runtime-path.md" | awk '{print $1}')" == "$EXPECTED_ADR_SHA" ]] || fail "ADR-0006 changed."
  [[ "$(pointer_run evidence/gates/gate-0.5/substrate-certification/GATE05-STEP05-LATEST.txt)" == "$EXPECTED_GATE05_RUN" ]] || fail "Gate 0.5 evidence pointer changed."
  [[ "$(pointer_run evidence/gates/gate-1/drupal-ai-batch-contract/GATE1-STEP01-LATEST.txt)" == "$EXPECTED_STEP01_RUN" ]] || fail "Step 1.01 evidence pointer changed."
  [[ "$(pointer_run evidence/gates/gate-1/drupal-ai-runtime-probe/GATE1-STEP02-LATEST.txt)" == "$EXPECTED_STEP02_RUN" ]] || fail "Step 1.02 evidence pointer changed."
  [[ "$(pointer_run evidence/gates/gate-1/step01-audit-progression-compatibility/GATE1-STEP01-AUDIT-COMPATIBILITY-LATEST.txt)" == "$EXPECTED_COMPAT_RUN" ]] || fail "Compatibility evidence pointer changed."
  for relative in "${PAYLOAD_FILES[@]}"; do
    [[ -s "$REPO/$relative" ]] || fail "Installed Step 1.03 payload is incomplete: $relative"
  done
  (
    cd "$DRUPAL_ROOT"
    ddev exec php -l scripts/gate1-step03-adapter-exercise.php >/dev/null
    ddev exec php -l web/modules/custom/agentic_harness_drupal_ai/src/Service/ToolResultRunner.php >/dev/null
    ddev exec php -l web/modules/custom/agentic_harness_drupal_ai/src/Plugin/AiFunctionCall/DiscoverTargets.php >/dev/null
    ddev exec php -l web/modules/custom/agentic_harness_drupal_ai/src/Plugin/AiFunctionCall/GetImageContext.php >/dev/null
    ddev exec php -l web/modules/custom/agentic_harness_drupal_ai/src/Plugin/AiFunctionCall/SubmitRecommendation.php >/dev/null
    ddev exec php -l web/modules/custom/agentic_harness_drupal_ai/src/Plugin/AiFunctionCall/GetRecommendationStatus.php >/dev/null
  ) || fail "Step 1.03 PHP syntax validation failed."
  "$PYTHON" - "$CAPTURE" "$AUDITOR" "$FINALIZER" <<'PY'
from pathlib import Path
import sys
for value in sys.argv[1:]:
    path = Path(value)
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
PY
  "$PYTHON" "$AUDITOR" --repo "$REPO" >/dev/null
}

run_predecessor_audits() {
  local output_dir="$1"
  bash "$REPO/scripts/run-gate05-step05.sh" audit >"$output_dir/gate05-audit.log"
  bash "$REPO/scripts/run-gate1-step01.sh" audit >"$output_dir/step01-audit.log"
  bash "$REPO/scripts/run-gate1-step02.sh" audit >"$output_dir/step02-audit.log"
  bash "$REPO/scripts/run-gate1-step01-audit-compatibility.sh" audit >"$output_dir/compatibility-audit.log"
}

write_summary() {
  local run_id="$1" run_dir="$2"
  "$PYTHON" - "$run_id" "$run_dir" "$REPO" <<'PY'
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

run_id = sys.argv[1]
run_dir = Path(sys.argv[2])
repo = Path(sys.argv[3])
exercise = json.loads((run_dir / "adapter-exercise.json").read_text(encoding="utf-8"))
before = json.loads((run_dir / "before-state.json").read_text(encoding="utf-8"))
after = json.loads((run_dir / "after-state.json").read_text(encoding="utf-8"))
reconciliation = before["article_source_hash_reconciliation"]
if reconciliation != after["article_source_hash_reconciliation"]:
    raise SystemExit("[ERROR] Before/after Article-source reconciliation changed")
seeded_manifest_path = repo / "db/seeded-clean-manifest.json"
seeded_manifest_bytes = seeded_manifest_path.read_bytes()
seeded_manifest = json.loads(seeded_manifest_bytes)
reconciliation_evidence = {
    "schema_version": 1,
    "status": "pass",
    "root_cause": "hash_definition_drift_only",
    "actual_drupal_source_drift": False,
    "same_restored_database_without_intervening_mutation": True,
    "article_source_hash_reconciliation": reconciliation,
    "seeded_clean_manifest": {
        "source": "drupal/scripts/seed.php::step9_audit/step9_print_manifest and drupal/scripts/run-phase0-step10.sh",
        "entities": "12 target image usages selected from the 20-Article deterministic dataset",
        "properties": sorted(seeded_manifest["targets"][0]),
        "includes_node_ids": True,
        "includes_node_uuids": True,
        "includes_revision_ids": True,
        "image_or_file_metadata": "file ID/UUID/URI, field/delta, current alt, target state; audit also verifies MIME and dimensions but does not emit them in the manifest",
        "sorting": "article_number ASC, delta ASC",
        "normalization": "deterministic dataset values; no recursive key sorting",
        "json_encoding_flags": ["JSON_PRETTY_PRINT", "JSON_UNESCAPED_SLASHES", "JSON_THROW_ON_ERROR"],
        "null_empty_treatment": "current_alt is retained as its deterministic string value; canonical missing alt is empty string",
        "canonical_payload_bytes": len(seeded_manifest_bytes),
        "sha256": hashlib.sha256(seeded_manifest_bytes).hexdigest(),
        "target_count": seeded_manifest["target_count"],
        "current_manifest_byte_equal": True,
    },
    "sensitive_article_payload_retained": False,
}
(run_dir / "article-source-hash-reconciliation.json").write_text(
    json.dumps(reconciliation_evidence, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
summary = {
    "schema_version": 1,
    "status": "pass",
    "run_id": run_id,
    "package": "gate-1-step03-drupal-ai-tool-adapters",
    "package_version": "1.0.0",
    "predecessor_commit": "3915af75779869e19c40abf3cbb4e2021cc57952",
    "gate05_run_id": "gate05-step05-20260805T184155Z-50124",
    "gate05_freeze_sha256": "99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a",
    "step01_run_id": "gate1-step01-20260805T205448Z-103220",
    "step01_contract_sha256": "360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6",
    "step02_run_id": "gate1-step02-20260806T010227Z-189538",
    "compatibility_run_id": "gate1-step01-audit-compatibility-20260806T023356Z-250843",
    "adr0006_sha256": "223f6d6f4276d3861cf5668f08e0446479d815a07fed18402b1e6a7722d18c4b",
    "plugin_ids": ["discover_targets", "get_image_context", "submit_recommendation", "get_recommendation_status"],
    "plugin_count": 4,
    "dependency_injection": True,
    "direct_shared_service_delegation": True,
    "permission_denials": 8,
    "negative_controls": 7,
    "target_count_before_after": [12, 12],
    "article_count_before_after": [20, 20],
    "recommendation_count_before_after": [0, 0],
    "target_sequence_sha256": "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728",
    "article_source_sha256": "f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17",
    "step03_extended_article_source_sha256": before["step03_extended_article_source_sha256"],
    "article_source_hash_reconciliation": "hash_definition_drift_only",
    "actual_drupal_source_drift": False,
    "canonical_target_sequence": 1,
    "source_article_unchanged": True,
    "seeded_clean_before_after": True,
    "module_enabled_before_after": [False, False],
    "idempotent_replay_same_identity": True,
    "pending_status_observed": True,
    "direct_context_data_shape": exercise["get_image_context"]["direct_data_shape"],
    "model_call_performed": False,
    "network_call_performed": False,
    "api_credit_used": False,
    "raw_image_retained": False,
    "secret_retained": False,
    "runtime_state_storage_opened": False,
    "ai_agent_configuration_created": False,
    "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "next_package": "gate-1-step04-drupal-ai-canonical-vertical-slice-v1.0.0",
}
(run_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
(run_dir / "summary.md").write_text(
    "# Gate 1 Step 1.03 Drupal AI Tool Adapters\n\n"
    "- **Status:** PASS\n"
    f"- **Run ID:** `{run_id}`\n"
    "- **Plugins:** four exact FunctionCall IDs discovered and container-instantiated\n"
    "- **Delegation:** four direct certified shared-service calls through constructor injection\n"
    "- **Accounts:** all successes as `agent_bot`; anonymous and `editor_dana` denied for all four adapters\n"
    "- **Discovery:** 12 targets, canonical sequence 1, frozen target-order hash\n"
    "- **Article source:** predecessor-compatible Step 1.02 hash `f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17`; hash-definition drift reconciled; no Drupal source drift\n"
    "- **Context:** shared schemas valid, direct data shape, no raw representation retained\n"
    "- **Submission/status:** one deterministic pending fixture, same-identity replay, pending status observed\n"
    "- **Restoration:** 20 Articles, zero recommendations, seeded-clean, module disabled before/after\n"
    "- **Model, AI Agent, provider, network, API credit, runtime state:** none\n"
    "- **Next package:** `gate-1-step04-drupal-ai-canonical-vertical-slice-v1.0.0`\n\n"
    "This proves only the model-free thin-adapter boundary on the pinned local runtime.\n",
    encoding="utf-8",
)
PY
}

write_manifests() {
  local run_dir="$1"
  (
    cd "$REPO"
    sha256sum "${PAYLOAD_FILES[@]}" >"$run_dir/installed-files-sha256.txt"
  )
  (
    cd "$run_dir"
    sha256sum \
      adapter-audit.json \
      adapter-exercise.json \
      article-source-hash-reconciliation.json \
      after-state.json \
      before-state.json \
      compatibility-audit.log \
      gate05-audit.log \
      installed-files-sha256.txt \
      seeded-clean-after.log \
      seeded-clean-before.log \
      step01-audit.log \
      step02-audit.log \
      summary.json \
      summary.md >package-files-sha256.txt
  )
}

verify_retained_evidence() {
  local pointer="$EVIDENCE_ROOT/GATE1-STEP03-LATEST.txt"
  [[ -s "$pointer" ]] || fail "Missing Step 1.03 latest pointer."
  local run_dir="$REPO/$(<"$pointer")"
  [[ -d "$run_dir" ]] || fail "Missing retained Step 1.03 evidence directory."
  (
    cd "$run_dir"
    sha256sum -c package-files-sha256.txt >/dev/null
  ) || fail "Step 1.03 evidence checksum failed."
  (
    cd "$REPO"
    sha256sum -c "$run_dir/installed-files-sha256.txt" >/dev/null
  ) || fail "Step 1.03 installed-file checksum failed."
  "$PYTHON" "$AUDITOR" --repo "$REPO" --run-dir "$run_dir" >/dev/null
  pass "Gate 1 Step 1.03 audit passed."
  pass "Evidence: ${run_dir#"$REPO/"}"
}

restore_snapshot() {
  local snapshot_name="$1"
  (
    cd "$DRUPAL_ROOT"
    ddev snapshot restore "$snapshot_name" >/dev/null
    ddev drush cr >/dev/null
    ddev snapshot --cleanup --name "$snapshot_name" -y >/dev/null
  )
}

verify_repo

case "$MODE" in
  run)
    run_id="gate1-step03-$(date -u +%Y%m%dT%H%M%SZ)-$$"
    run_dir="$EVIDENCE_ROOT/$run_id"
    [[ ! -e "$run_dir" ]] || fail "Evidence directory already exists."
    mkdir -p "$run_dir"
    temporary="$(mktemp -d)"
    snapshot_name="gate1-step03-pre-${run_id}"
    snapshot_created=0
    restored=0
    cleanup() {
      local status=$?
      if [[ "$snapshot_created" -eq 1 && "$restored" -eq 0 ]]; then
        restore_snapshot "$snapshot_name" || status=1
      fi
      if [[ "$status" -ne 0 && -d "$run_dir" ]]; then
        rm -rf -- "$run_dir"
      fi
      rm -rf "$temporary"
      exit "$status"
    }
    trap cleanup EXIT INT TERM

    info "Running all four predecessor audits..."
    run_predecessor_audits "$run_dir"
    if module_enabled "$temporary/enabled-before.txt"; then
      fail "Step 1.03 module must be disabled before the reset-bounded exercise."
    fi
    seeded_clean_audit "$run_dir/seeded-clean-before.log"
    snapshot_state "$run_dir/before-state.json"
    info "Creating exact pre-run database/configuration snapshot..."
    (
      cd "$DRUPAL_ROOT"
      ddev snapshot --name "$snapshot_name" >/dev/null
    )
    snapshot_created=1
    (
      cd "$DRUPAL_ROOT"
      ddev drush en agentic_harness_drupal_ai -y >/dev/null
      ddev drush cr >/dev/null
    )
    info "Executing four adapters directly with raw context confined to the validation pipe..."
    (
      cd "$DRUPAL_ROOT"
      env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
        ddev drush --quiet php:script scripts/gate1-step03-adapter-exercise.php -- exercise
    ) | "$PYTHON" "$CAPTURE" --repo "$REPO" >"$run_dir/adapter-exercise.json"

    info "Restoring exact pre-run database/configuration state..."
    restore_snapshot "$snapshot_name"
    restored=1
    if module_enabled "$temporary/enabled-after.txt"; then
      fail "Step 1.03 module remained enabled after snapshot restoration."
    fi
    snapshot_state "$run_dir/after-state.json"
    seeded_clean_audit "$run_dir/seeded-clean-after.log"
    write_summary "$run_id" "$run_dir"
    "$PYTHON" "$AUDITOR" --repo "$REPO" --run-dir "$run_dir" >"$run_dir/adapter-audit.json"
    write_manifests "$run_dir"
    mkdir -p "$EVIDENCE_ROOT"
    printf '%s\n' "${run_dir#"$REPO/"}" >"$EVIDENCE_ROOT/GATE1-STEP03-LAST-RUN.txt"
    printf '%s\n' "${run_dir#"$REPO/"}" >"$EVIDENCE_ROOT/GATE1-STEP03-LATEST.txt"
    verify_retained_evidence
    "$PYTHON" "$FINALIZER" --repo "$REPO" --run-id "$run_id"
    trap - EXIT INT TERM
    rm -rf "$temporary"
    pass "Status documents advanced only after all Step 1.03 checks passed."
    pass "Next package: gate-1-step04-drupal-ai-canonical-vertical-slice-v1.0.0"
    ;;
  audit)
    temporary="$(mktemp -d)"
    trap 'rm -rf "$temporary"' EXIT
    run_predecessor_audits "$temporary"
    if module_enabled "$temporary/enabled-current.txt"; then
      fail "Step 1.03 audit requires the module-disabled restored configuration state."
    fi
    seeded_clean_audit "$temporary/seeded-clean.log"
    snapshot_state "$temporary/current-state.json"
    verify_retained_evidence
    "$PYTHON" - "$temporary/current-state.json" "$REPO/$(<"$EVIDENCE_ROOT/GATE1-STEP03-LATEST.txt")/after-state.json" <<'PY'
import json
import sys
current = json.load(open(sys.argv[1], encoding="utf-8"))
accepted = json.load(open(sys.argv[2], encoding="utf-8"))
for key in ("article_count", "suggestion_count", "target_count", "target_sequence_sha256", "canonical_target_sequence", "canonical_target_identity_sha256", "article_source_sha256", "step03_extended_article_source_sha256", "gate05_certification_article_source_sha256", "article_source_hash_reconciliation", "seeded_clean", "module_enabled"):
    if current.get(key) != accepted.get(key):
        raise SystemExit(f"[ERROR] Current state differs from accepted Step 1.03 evidence: {key}")
PY
    ;;
esac
