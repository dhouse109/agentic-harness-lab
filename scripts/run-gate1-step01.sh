#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-audit}"
REPO="$(git rev-parse --show-toplevel)"
EVIDENCE_ROOT="$REPO/evidence/gates/gate-1/drupal-ai-batch-contract"
EXPECTED_COMMIT="3016819f738a7db39fef0a6ccbb9cff0c8ec5fa0"
EXPECTED_BRANCH="main"
SUPERSEDED_RUN_ID="gate1-step01-20260805T200619Z-87483"
SUPERSEDED_MANIFEST_SHA256="b25ede2a20b8c94a2986806362df6b5b2b5b574c3a80953d175578985bdc9b06"
PYTHON="$REPO/crewai/.venv/bin/python"
AUDITOR="$REPO/scripts/gate1_step01_audit.py"
CURRENT_BRANCH=""

fail() {
  printf '[ERROR] %s\n' "$*" >&2
  exit 1
}

verify_repository() {
  CURRENT_BRANCH="$(git -C "$REPO" branch --show-current)"
  case "$MODE" in
    run)
      [[ "$CURRENT_BRANCH" == "$EXPECTED_BRANCH" ]] || fail "Run mode requires branch $EXPECTED_BRANCH."
      [[ "$(git -C "$REPO" rev-parse HEAD)" == "$EXPECTED_COMMIT" ]] || fail "Run mode requires predecessor commit $EXPECTED_COMMIT."
      ;;
    audit)
      git -C "$REPO" merge-base --is-ancestor "$EXPECTED_COMMIT" HEAD || fail "Audit mode requires predecessor commit $EXPECTED_COMMIT in HEAD ancestry."
      printf '[INFO] Audit branch: %s\n' "$CURRENT_BRANCH"
      ;;
  esac
  [[ -x "$PYTHON" ]] || fail "Missing locked CrewAI Python environment."
  [[ -f "$AUDITOR" ]] || fail "Missing Step 1.01 auditor."
}

verify_superseded_evidence() {
  local run_dir="$EVIDENCE_ROOT/$SUPERSEDED_RUN_ID"
  [[ -d "$run_dir" ]] || fail "Missing immutable superseded v1.0.0 evidence run."
  [[ "$(sha256sum "$run_dir/package-files-sha256.txt" | awk '{print $1}')" == "$SUPERSEDED_MANIFEST_SHA256" ]] || fail "Superseded v1.0.0 evidence manifest changed."
  (
    cd "$run_dir"
    sha256sum -c package-files-sha256.txt >/dev/null
  ) || fail "Superseded v1.0.0 evidence content changed."
}

run_checks() {
  local output_dir="$1" document_state="$2"
  bash "$REPO/scripts/run-gate05-step05.sh" audit >"$output_dir/predecessor-audit.log"
  "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state "$document_state" >"$output_dir/contract-audit.json"
}

write_evidence() {
  local run_id="$1" run_dir="$2" contract_sha
  contract_sha="$(sha256sum "$REPO/shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json" | awk '{print $1}')"
  install -m 0644 "$REPO/shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json" "$run_dir/contract.json"
  install -m 0644 "$REPO/shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.sha256" "$run_dir/contract.sha256"

  "$PYTHON" - "$REPO" "$run_dir" "$run_id" "$contract_sha" <<'PY'
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

repo = Path(sys.argv[1])
run_dir = Path(sys.argv[2])
run_id = sys.argv[3]
contract_sha = sys.argv[4]
now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
git_metadata = {
    "branch": subprocess.run(["git", "-C", str(repo), "branch", "--show-current"], check=True, capture_output=True, text=True).stdout.strip(),
    "commit": subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip(),
    "captured_at": now,
}
summary = {
    "schema_version": 1,
    "status": "pass",
    "run_id": run_id,
    "package": "gate-1-step01-drupal-ai-batch-contract",
    "package_version": "1.0.1",
    "contract_sha256": contract_sha,
    "predecessor_run_id": "gate05-step05-20260805T184155Z-50124",
    "predecessor_audit": "pass",
    "contract_audit": "pass",
    "model_call_performed": False,
    "drupal_state_mutated": False,
    "dependency_change": False,
    "gate05_recertified": False,
    "step02_started": False,
    "superseded_run_id": "gate1-step01-20260805T200619Z-87483",
    "superseded_run_preserved": True,
    "supersession_reasons": [
        "terminal blank-line errors in newly created schemas",
        "main-only installed audit mode blocked publication-branch validation",
    ],
    "contract_semantics_changed": False,
    "accepted_step01_publication_baseline": True,
    "completed_at": now,
    "next_boundary": "human commit approval",
    "next_package": "gate-1-step02-drupal-ai-runtime-probe-v1.0.0",
}
(run_dir / "git-metadata.json").write_text(json.dumps(git_metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
(run_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
(run_dir / "summary.md").write_text(
    "# Gate 1 Step 1.01 Contract Audit\n\n"
    "- **Status:** PASS\n"
    f"- **Run ID:** `{run_id}`\n"
    f"- **Contract SHA-256:** `{contract_sha}`\n"
    "- **Package version:** `1.0.1`\n"
    "- **Superseded v1.0.0 run preserved:** `gate1-step01-20260805T200619Z-87483`\n"
    "- **Supersession reason:** publication checks exposed terminal schema blank lines and a main-only audit-mode restriction\n"
    "- **Contract semantics changed:** no\n"
    "- **Accepted Step 1.01 publication baseline:** yes\n"
    "- **Gate 0.5 predecessor audit:** pass\n"
    "- **Contract and schema audit:** pass\n"
    "- **Model call performed:** no\n"
    "- **Drupal state mutated:** no\n"
    "- **Dependency change:** no\n"
    "- **Gate 0.5 recertified:** no\n"
    "- **Step 1.02 started:** no\n\n"
    "- **Next package after commit:** `gate-1-step02-drupal-ai-runtime-probe-v1.0.0`\n\n"
    "This evidence certifies only the Step 1.01 contract and evidence-schema boundary. It does not claim Drupal AI framework execution or batch behavior.\n",
    encoding="utf-8",
)
PY

  (
    cd "$run_dir"
    sha256sum contract-audit.json contract.json contract.sha256 git-metadata.json predecessor-audit.log summary.json summary.md > package-files-sha256.txt
  )
}

transition_status_documents() {
  local run_id="$1" contract_sha="$2"
  "$PYTHON" - "$REPO" "$run_id" "$contract_sha" <<'PY'
import sys
from pathlib import Path

repo = Path(sys.argv[1])
run_id = sys.argv[2]
contract_sha = sys.argv[3]
pending = "Accepted Step 1.01 publication baseline: pending successful v1.0.1 runner."
accepted = f"Accepted Step 1.01 evidence run: `{run_id}`\nAccepted Gate 1 contract digest: `{contract_sha}`"
replacements = {
    "PLAN.md": [
        (
            "> Phase 0 and Gate 0.5 are complete. Gate 1 Step 1.01 is the active package and has not yet run.",
            "> Phase 0 and Gate 0.5 are complete. Gate 1 Step 1.01 is complete; Step 1.02 is next.",
        ),
        (
            "**Active package:**\n\n```text\ngate-1-step01-drupal-ai-batch-contract-v1.0.1\n```",
            "**Completed package:**\n\n```text\ngate-1-step01-drupal-ai-batch-contract-v1.0.1\n```\n\n**Next package:**\n\n```text\ngate-1-step02-drupal-ai-runtime-probe-v1.0.0\n```",
        ),
        ("- [ ] Step 1.01 — batch contract", "- [x] Step 1.01 — batch contract"),
        (pending, accepted),
    ],
    "README.md": [
        (
            "- **Active package:** `gate-1-step01-drupal-ai-batch-contract-v1.0.1` — not yet run.",
            "- **Step 1.01:** complete.\n- **Next package:** `gate-1-step02-drupal-ai-runtime-probe-v1.0.0`.",
        ),
        (pending, accepted),
    ],
    "docs/CURRENT-STATUS.md": [
        ("- **Active package:** `gate-1-step01-drupal-ai-batch-contract-v1.0.1`.", "- **Completed package:** `gate-1-step01-drupal-ai-batch-contract-v1.0.1`."),
        ("- **Step 1.01 execution:** not yet run.", "- **Step 1.01 execution:** complete.\n- **Next package:** `gate-1-step02-drupal-ai-runtime-probe-v1.0.0`."),
        (
            "Package 1.01 is the active package and has not yet run. Do not commit the extracted package or\nreuse a package generated against a different repository baseline.",
            "Package 1.01 is complete. The next package is\n`gate-1-step02-drupal-ai-runtime-probe-v1.0.0`. Do not commit extracted packages or reuse a package\ngenerated against a different repository baseline.",
        ),
        (
            "Do not generate Step 1.02 while Step 1.01 remains active.",
            "Do not generate Step 1.02 until Step 1.01 is committed.",
        ),
        (pending, accepted),
    ],
}
for relative, changes in replacements.items():
    path = repo / relative
    text = path.read_text(encoding="utf-8")
    for before, after in changes:
        if before not in text:
            raise SystemExit(f"[ERROR] Status transition anchor missing: {relative}")
        text = text.replace(before, after, 1)
    path.write_text(text, encoding="utf-8")
PY
}

verify_evidence() {
  local pointer run_dir
  pointer="$EVIDENCE_ROOT/GATE1-STEP01-LATEST.txt"
  [[ -f "$pointer" ]] || fail "Missing Step 1.01 latest pointer."
  run_dir="$REPO/$(<"$pointer")"
  [[ -d "$run_dir" ]] || fail "Missing retained Step 1.01 evidence directory."
  (
    cd "$run_dir"
    sha256sum -c package-files-sha256.txt >/dev/null
  ) || fail "Retained Step 1.01 evidence checksum failed."
  "$PYTHON" - "$run_dir/summary.json" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
required = {
    "status": "pass",
    "package": "gate-1-step01-drupal-ai-batch-contract",
    "package_version": "1.0.1",
    "predecessor_run_id": "gate05-step05-20260805T184155Z-50124",
    "predecessor_audit": "pass",
    "contract_audit": "pass",
    "model_call_performed": False,
    "drupal_state_mutated": False,
    "dependency_change": False,
    "gate05_recertified": False,
    "step02_started": False,
    "superseded_run_id": "gate1-step01-20260805T200619Z-87483",
    "superseded_run_preserved": True,
    "contract_semantics_changed": False,
    "accepted_step01_publication_baseline": True,
}
for key, expected in required.items():
    if summary.get(key) != expected:
        raise SystemExit(f"[ERROR] Unexpected Step 1.01 summary field: {key}")
PY
  if rg -n -i 'sk-[A-Za-z0-9_-]{20,}|data:image/|Authorization[[:space:]]*:|Basic[[:space:]]+[A-Za-z0-9+/]{16,}={0,2}' "$run_dir" >/dev/null; then
    fail "Potential secret-bearing content found in retained Step 1.01 evidence."
  fi
  printf '[PASS] Gate 1 Step 1.01 audit passed.\n'
  printf '[PASS] Evidence: %s\n' "${run_dir#"$REPO/"}"
}

verify_repository
verify_superseded_evidence

case "$MODE" in
  run)
    run_id="gate1-step01-$(date -u +%Y%m%dT%H%M%SZ)-$$"
    run_dir="$EVIDENCE_ROOT/$run_id"
    [[ ! -e "$run_dir" ]] || fail "Evidence directory already exists: $run_dir"
    mkdir -p "$run_dir"
    run_checks "$run_dir" active
    write_evidence "$run_id" "$run_dir"
    mkdir -p "$EVIDENCE_ROOT"
    printf '%s\n' "${run_dir#"$REPO/"}" >"$EVIDENCE_ROOT/GATE1-STEP01-LAST-RUN.txt"
    printf '%s\n' "${run_dir#"$REPO/"}" >"$EVIDENCE_ROOT/GATE1-STEP01-LATEST.txt"
    verify_evidence
    contract_sha="$(sha256sum "$REPO/shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json" | awk '{print $1}')"
    transition_status_documents "$run_id" "$contract_sha"
    "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state complete >/dev/null
    printf '[PASS] Status documents advanced to Step 1.02 as the next package.\n'
    ;;
  audit)
    temporary="$(mktemp -d)"
    trap 'rm -rf "$temporary"' EXIT
    run_checks "$temporary" complete
    verify_evidence
    ;;
  *)
    fail "Usage: bash scripts/run-gate1-step01.sh {run|audit}"
    ;;
esac
