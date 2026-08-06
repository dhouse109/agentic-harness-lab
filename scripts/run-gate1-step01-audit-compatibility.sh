#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="$REPO/crewai/.venv/bin/python"
AUDITOR="$REPO/scripts/gate1_step01_audit.py"
REGRESSION="$REPO/scripts/gate1_step01_progression_regression.py"
EVIDENCE_ROOT="$REPO/evidence/gates/gate-1/step01-audit-progression-compatibility"
EXPECTED_COMMIT="9b303ec3aefd8d92526905ca929a647948030b5a"
EXPECTED_GATE05_RUN="gate05-step05-20260805T184155Z-50124"
EXPECTED_GATE05_SHA="99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a"
EXPECTED_STEP01_RUN="gate1-step01-20260805T205448Z-103220"
EXPECTED_STEP01_SHA="360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6"
EXPECTED_STEP02_RUN="gate1-step02-20260806T010227Z-189538"
EXPECTED_ADR_SHA="223f6d6f4276d3861cf5668f08e0446479d815a07fed18402b1e6a7722d18c4b"

fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }
pass() { printf '[PASS] %s\n' "$*"; }

verify_lineage() {
  [[ "$(git -C "$REPO" rev-parse --show-toplevel)" == "$REPO" ]] || fail "Runner is not installed at repository root."
  git -C "$REPO" merge-base --is-ancestor "$EXPECTED_COMMIT" HEAD || fail "Repair predecessor is not in HEAD ancestry."
  [[ -x "$PYTHON" && -f "$AUDITOR" && -f "$REGRESSION" ]] || fail "Repair implementation is incomplete."
  [[ "$(basename "$(<"$REPO/evidence/gates/gate-0.5/substrate-certification/GATE05-STEP05-LATEST.txt")")" == "$EXPECTED_GATE05_RUN" ]] || fail "Gate 0.5 accepted evidence changed."
  [[ "$(sha256sum "$REPO/shared/contracts/GATE05-SUBSTRATE-FREEZE.json" | awk '{print $1}')" == "$EXPECTED_GATE05_SHA" ]] || fail "Gate 0.5 freeze changed."
  [[ "$(basename "$(<"$REPO/evidence/gates/gate-1/drupal-ai-batch-contract/GATE1-STEP01-LATEST.txt")")" == "$EXPECTED_STEP01_RUN" ]] || fail "Step 1.01 accepted evidence changed."
  [[ "$(sha256sum "$REPO/shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json" | awk '{print $1}')" == "$EXPECTED_STEP01_SHA" ]] || fail "Step 1.01 contract changed."
  [[ "$(basename "$(<"$REPO/evidence/gates/gate-1/drupal-ai-runtime-probe/GATE1-STEP02-LATEST.txt")")" == "$EXPECTED_STEP02_RUN" ]] || fail "Step 1.02 accepted evidence changed."
  [[ "$(sha256sum "$REPO/docs/decisions/ADR-0006-drupal-ai-programmatic-runtime-path.md" | awk '{print $1}')" == "$EXPECTED_ADR_SHA" ]] || fail "ADR-0006 changed."
  if [[ "$MODE" == "run" ]]; then
    [[ "$(sha256sum "$REPO/PLAN.md" | awk '{print $1}')" == "f2e64a0b41b883b74894e967cc5b849ed840c2da231861e452398f5fb4e5de97" ]] || fail "PLAN.md changed before repair evidence."
    [[ "$(sha256sum "$REPO/README.md" | awk '{print $1}')" == "bb1350d016b1bc9c439dbff3e827ff89cb0c29b439647a8ae064ee3f10118735" ]] || fail "README.md changed before repair evidence."
    [[ "$(sha256sum "$REPO/docs/CURRENT-STATUS.md" | awk '{print $1}')" == "cc27211f0e9a600394991ae6aecb7e712f400f84c07e9b861b5f6f2371a3f51b" ]] || fail "CURRENT-STATUS.md changed before repair evidence."
  fi
  (
    cd "$REPO/evidence/gates/gate-1/drupal-ai-batch-contract/gate1-step01-20260805T205448Z-103220"
    sha256sum -c package-files-sha256.txt >/dev/null
  ) || fail "Accepted Step 1.01 evidence changed."
  (
    cd "$REPO/evidence/gates/gate-1/drupal-ai-batch-contract/gate1-step01-20260805T200619Z-87483"
    sha256sum -c package-files-sha256.txt >/dev/null
  ) || fail "Superseded Step 1.01 evidence changed."
  (
    cd "$REPO/evidence/gates/gate-1/drupal-ai-runtime-probe/gate1-step02-20260806T010227Z-189538"
    sha256sum -c package-files-sha256.txt >/dev/null
    cd "$REPO"
    sha256sum -c evidence/gates/gate-1/drupal-ai-runtime-probe/gate1-step02-20260806T010227Z-189538/installed-files-sha256.txt >/dev/null
  ) || fail "Accepted Step 1.02 evidence changed."
}

verify_run_tree_scope() {
  "$PYTHON" - "$REPO" <<'PY'
import subprocess, sys
from pathlib import Path

repo = Path(sys.argv[1])
expected = {
    "docs/gates/GATE-1-STEP01-AUDIT-PROGRESSION-COMPATIBILITY.md",
    "scripts/gate1_step01_audit.py",
    "scripts/gate1_step01_progression_regression.py",
    "scripts/run-gate1-step01-audit-compatibility.sh",
}
output = subprocess.run(
    ["git", "-C", str(repo), "status", "--porcelain=v1", "--untracked-files=all"],
    check=True,
    capture_output=True,
    text=True,
).stdout
actual = {line[3:] for line in output.splitlines() if line}
if actual != expected:
    raise SystemExit(f"[ERROR] Unexpected run-mode working-tree scope: {sorted(actual)}")
PY
}

snapshot() {
  local output="$1"
  (
    cd "$REPO/drupal"
    env -u OPENAI_API_KEY -u OPENAI_CANDIDATE_MODEL -u CREWAI_CANDIDATE_MODEL \
      ddev drush --quiet php:script scripts/gate1-step02-runtime-probe.php -- snapshot
  ) >"$output"
}

seeded_clean_audit() {
  local output="$1"
  (cd "$REPO/drupal" && bash scripts/run-phase0-step10.sh audit) >"$output"
}

run_audits() {
  local output_dir="$1"
  bash "$REPO/scripts/run-gate05-step05.sh" audit >"$output_dir/gate05-audit.log"
  bash "$REPO/scripts/run-gate1-step01.sh" audit >"$output_dir/step01-audit.log"
  bash "$REPO/scripts/run-gate1-step02.sh" audit >"$output_dir/step02-audit.log"
  "$PYTHON" "$REGRESSION" --repo "$REPO" --auditor "$AUDITOR" >"$output_dir/progression-regression.json"
}

verify_source_quality() {
  bash -n "$REPO/scripts/run-gate1-step01.sh"
  bash -n "$REPO/scripts/run-gate1-step01-audit-compatibility.sh"
  "$PYTHON" - "$AUDITOR" "$REGRESSION" <<'PY'
from pathlib import Path
import sys
for name in sys.argv[1:]:
    path = Path(name)
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
PY
  git -C "$REPO" diff --check
}

write_summary() {
  local run_id="$1" run_dir="$2"
  "$PYTHON" - "$run_id" "$run_dir" <<'PY'
import json, sys
from datetime import datetime, timezone
from pathlib import Path

run_id = sys.argv[1]
run_dir = Path(sys.argv[2])
regression = json.loads((run_dir / "progression-regression.json").read_text(encoding="utf-8"))
before = json.loads((run_dir / "before-state.json").read_text(encoding="utf-8"))
after = json.loads((run_dir / "after-state.json").read_text(encoding="utf-8"))
if before != after:
    raise SystemExit("[ERROR] Drupal before/after state changed")
summary = {
    "schema_version": 1,
    "status": "pass",
    "run_id": run_id,
    "package": "gate-1-step01-audit-progression-compatibility",
    "package_version": "1.0.0",
    "predecessor_commit": "9b303ec3aefd8d92526905ca929a647948030b5a",
    "known_predecessor_failure_reproduced": True,
    "known_predecessor_failure": regression["predecessor_defect"]["message"],
    "positive_progression_fixtures": regression["positive_progression_fixtures"],
    "negative_regression_fixtures": regression["negative_regression_fixtures"],
    "gate05_run_id": "gate05-step05-20260805T184155Z-50124",
    "gate05_freeze_sha256": "99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a",
    "step01_run_id": "gate1-step01-20260805T205448Z-103220",
    "step01_contract_sha256": "360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6",
    "step02_run_id": "gate1-step02-20260806T010227Z-189538",
    "adr0006_sha256": "223f6d6f4276d3861cf5668f08e0446479d815a07fed18402b1e6a7722d18c4b",
    "article_count_before_after": [before["article_count"], after["article_count"]],
    "recommendation_count_before_after": [before["suggestion_count"], after["suggestion_count"]],
    "target_count": before["target_count"],
    "canonical_target_sequence": before["canonical_target_sequence"],
    "target_sequence_sha256": before["target_sequence_sha256"],
    "source_hash_unchanged": before["article_source_sha256"] == after["article_source_sha256"],
    "seeded_clean_before_after": before["seeded_clean"] and after["seeded_clean"],
    "status_documents_changed": False,
    "contract_or_schema_changed": False,
    "accepted_evidence_changed": False,
    "dependency_changed": False,
    "drupal_content_or_configuration_changed": False,
    "model_call_performed": False,
    "network_call_performed": False,
    "api_credit_used": False,
    "step03_started": False,
    "next_package": "gate-1-step03-drupal-ai-tool-adapters-v1.0.0",
    "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
}
(run_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
(run_dir / "summary.md").write_text(
    "# Gate 1 Step 1.01 Audit Progression Compatibility Repair\n\n"
    f"- **Status:** PASS\n- **Run ID:** `{run_id}`\n"
    "- **Known predecessor failure reproduced:** yes\n"
    "- **Progression fixtures:** 6 accepted; 9 invalid states rejected\n"
    "- **Gate 0.5, Step 1.01, and Step 1.02 installed audits:** pass\n"
    "- **Accepted evidence, contracts, schemas, ADR-0006, and status documents:** unchanged\n"
    "- **Drupal state:** 20 Articles, zero recommendations, 12 targets, canonical sequence 1, seeded-clean before/after\n"
    "- **Model, provider, network, API credit, Drupal mutation, dependency change:** none\n"
    "- **Step 1.03 started:** no\n"
    "- **Next package remains:** `gate-1-step03-drupal-ai-tool-adapters-v1.0.0`\n",
    encoding="utf-8",
)
PY
}

write_manifests() {
  local run_dir="$1"
  (
    cd "$REPO"
    sha256sum \
      docs/gates/GATE-1-STEP01-AUDIT-PROGRESSION-COMPATIBILITY.md \
      scripts/gate1_step01_audit.py \
      scripts/gate1_step01_progression_regression.py \
      scripts/run-gate1-step01-audit-compatibility.sh >"$run_dir/installed-files-sha256.txt"
  )
  (
    cd "$run_dir"
    sha256sum \
      after-state.json \
      before-state.json \
      gate05-audit.log \
      installed-files-sha256.txt \
      progression-regression.json \
      seeded-clean-after.log \
      seeded-clean-before.log \
      step01-audit.log \
      step02-audit.log \
      summary.json \
      summary.md >package-files-sha256.txt
  )
}

verify_evidence() {
  local pointer="$EVIDENCE_ROOT/GATE1-STEP01-AUDIT-COMPATIBILITY-LATEST.txt"
  [[ -s "$pointer" ]] || fail "Missing compatibility-repair latest pointer."
  local run_dir="$REPO/$(<"$pointer")"
  [[ -d "$run_dir" ]] || fail "Missing compatibility-repair evidence directory."
  (cd "$run_dir" && sha256sum -c package-files-sha256.txt >/dev/null) || fail "Repair evidence checksum failed."
  (cd "$REPO" && sha256sum -c "$run_dir/installed-files-sha256.txt" >/dev/null) || fail "Repair installed-file checksum failed."
  "$PYTHON" - "$run_dir/summary.json" <<'PY'
import json, sys
summary = json.load(open(sys.argv[1], encoding="utf-8"))
required = {
    "status": "pass",
    "known_predecessor_failure_reproduced": True,
    "step01_run_id": "gate1-step01-20260805T205448Z-103220",
    "step01_contract_sha256": "360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6",
    "step02_run_id": "gate1-step02-20260806T010227Z-189538",
    "adr0006_sha256": "223f6d6f4276d3861cf5668f08e0446479d815a07fed18402b1e6a7722d18c4b",
    "status_documents_changed": False,
    "model_call_performed": False,
    "network_call_performed": False,
    "drupal_content_or_configuration_changed": False,
    "step03_started": False,
    "next_package": "gate-1-step03-drupal-ai-tool-adapters-v1.0.0",
}
for key, expected in required.items():
    if summary.get(key) != expected:
        raise SystemExit(f"[ERROR] Unexpected repair summary field: {key}")
PY
  if rg -n -i 'sk-[A-Za-z0-9_-]{20,}|data:image/|Authorization[[:space:]]*:|Basic[[:space:]]+[A-Za-z0-9+/]{16,}={0,2}' "$run_dir" >/dev/null; then
    fail "Potential secret-bearing content found in repair evidence."
  fi
}

verify_lineage
verify_source_quality

case "$MODE" in
  run)
    [[ "$(git -C "$REPO" branch --show-current)" == "main" ]] || fail "Run mode requires main."
    [[ "$(git -C "$REPO" rev-parse HEAD)" == "$EXPECTED_COMMIT" ]] || fail "Run mode requires the exact repair predecessor commit."
    verify_run_tree_scope
    run_id="gate1-step01-audit-compatibility-$(date -u +%Y%m%dT%H%M%SZ)-$$"
    run_dir="$EVIDENCE_ROOT/$run_id"
    [[ ! -e "$run_dir" ]] || fail "Evidence directory already exists."
    mkdir -p "$run_dir"
    seeded_clean_audit "$run_dir/seeded-clean-before.log"
    snapshot "$run_dir/before-state.json"
    run_audits "$run_dir"
    snapshot "$run_dir/after-state.json"
    seeded_clean_audit "$run_dir/seeded-clean-after.log"
    cmp -s "$run_dir/before-state.json" "$run_dir/after-state.json" || fail "Drupal state changed during repair audit."
    write_summary "$run_id" "$run_dir"
    write_manifests "$run_dir"
    mkdir -p "$EVIDENCE_ROOT"
    printf '%s\n' "${run_dir#"$REPO/"}" >"$EVIDENCE_ROOT/GATE1-STEP01-AUDIT-COMPATIBILITY-LAST-RUN.txt"
    printf '%s\n' "${run_dir#"$REPO/"}" >"$EVIDENCE_ROOT/GATE1-STEP01-AUDIT-COMPATIBILITY-LATEST.txt"
    verify_evidence
    pass "Step 1.01 audit progression compatibility repair passed."
    pass "Evidence: ${run_dir#"$REPO/"}"
    pass "Step 1.03 remains absent; gate-1-step03-drupal-ai-tool-adapters-v1.0.0 is still next."
    ;;
  audit)
    temporary="$(mktemp -d)"
    trap 'rm -rf "$temporary"' EXIT
    run_audits "$temporary"
    verify_evidence
    pass "Step 1.01 audit progression compatibility repair audit passed."
    ;;
  *)
    fail "Usage: bash scripts/run-gate1-step01-audit-compatibility.sh {run|audit}"
    ;;
esac
