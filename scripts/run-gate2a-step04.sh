#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$REPO/langchain/.venv/bin/python"
VALIDATOR_PYTHON="$REPO/crewai/.venv/bin/python"
BRANCH="gate-2a-step04-langgraph-state-and-sqlite-checkpoint-proof"
EXPECTED_HEAD="aae7f1e1dea5b30e51a304bf975ec313b96d9605"
EVIDENCE_ROOT="$REPO/evidence/gates/gate-2a/checkpoint-proof"
RUNTIME_ROOT="$REPO/langchain/.gate2a-runtime"

fail() { printf '[ERROR] %s\n' "$*" >&2; exit 1; }
pass() { printf '[PASS] %s\n' "$*"; }

require_branch_head() {
  [[ "$(git -C "$REPO" branch --show-current)" == "$BRANCH" ]] || fail "Expected branch $BRANCH."
  [[ "$(git -C "$REPO" rev-parse HEAD)" == "$EXPECTED_HEAD" ]] || fail "Expected predecessor HEAD $EXPECTED_HEAD."
}

preflight() {
  require_branch_head
  [[ -x "$PYTHON" ]] || fail "LangGraph virtualenv Python missing."
  [[ -x "$VALIDATOR_PYTHON" ]] || fail "Schema-validator interpreter missing."

  "$PYTHON" - <<'PY'
import importlib.metadata as md
expected={"langchain":"1.3.14","langgraph":"1.2.10","langgraph-checkpoint-sqlite":"3.1.1"}
for name, want in expected.items():
    got=md.version(name)
    if got != want:
        raise SystemExit(f"[ERROR] {name}={got}, expected {want}")
from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
print("[PASS] Pinned LangGraph/SQLite imports and versions passed.")
PY

  "$VALIDATOR_PYTHON" - <<'PY'
import jsonschema, referencing
print("[PASS] Frozen-schema validator interpreter preflight passed.")
PY

  # Import the repository-local specimen using the exact module path and
  # PYTHONPATH that process 1 and process 2 will use. This must pass before
  # a new run ID or evidence directory is created.
  PYTHONPATH="$REPO/langchain:$REPO${PYTHONPATH:+:$PYTHONPATH}"     "$PYTHON" - <<'PY'
from agentic_harness_langgraph.state import LangGraphRunState, advance_target, initial_state
assert LangGraphRunState is not None
assert callable(advance_target)
assert callable(initial_state)
print("[PASS] Repository-local LangGraph state import smoke passed.")
PY

  # Compile a StateGraph using the exact repository-local state channel schema.
  # This catches framework-reserved channel names before a new run ID or
  # evidence directory is created.
  PYTHONPATH="$REPO/langchain:$REPO${PYTHONPATH:+:$PYTHONPATH}"     "$PYTHON" - <<'PY'
from langgraph.graph import END, START, StateGraph
from agentic_harness_langgraph.state import LangGraphRunState

def noop(state: LangGraphRunState):
    return {}

builder = StateGraph(LangGraphRunState)
builder.add_node("compile_smoke", noop)
builder.add_edge(START, "compile_smoke")
builder.add_edge("compile_smoke", END)
builder.compile()
print("[PASS] Repository-local LangGraph StateGraph compilation smoke passed.")
PY

  mkdir -p "$RUNTIME_ROOT"
  probe="$RUNTIME_ROOT/.gate2a-step04-ignore-probe.sqlite"
  : > "$probe"
  git -C "$REPO" check-ignore -q "langchain/.gate2a-runtime/.gate2a-step04-ignore-probe.sqlite"     || { rm -f "$probe"; fail "LangGraph runtime root is not gitignored."; }
  rm -f "$probe"

  "$PYTHON" "$REPO/scripts/gate2a_step04_audit.py"     --repo "$REPO" --document-state active
  pass "Gate 2A Step 2A.04 preflight passed."
}

run_proof() {
  preflight

  mkdir -p "$EVIDENCE_ROOT" "$RUNTIME_ROOT"
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  suffix="$(printf '%08x' "$$")"
  run_id="langgraph-${stamp}-${suffix}"
  evidence_name="gate2a-step04-${stamp}-${suffix}"
  evidence_rel="evidence/gates/gate-2a/checkpoint-proof/${evidence_name}"
  evidence="$REPO/$evidence_rel"
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  mkdir -p "$evidence"

  printf '%s\n' "$evidence_rel" > "$EVIDENCE_ROOT/GATE2A-STEP04-LAST-RUN.txt"
  printf '%s\n' "$run_id" > "$evidence/run-id.txt"

  failure_note() {
    rc=$?
    if [[ $rc -ne 0 ]]; then
      printf 'FAIL: Step 2A.04 run stopped with exit code %s. Retained run: %s\n' "$rc" "$evidence_rel"         > "$evidence/run-failure.txt" || true
      printf '[STOP] Step 2A.04 failed; retained evidence at %s. Do not silently rerun.\n' "$evidence_rel" >&2
    fi
    exit "$rc"
  }
  trap failure_note ERR INT TERM

  PYTHONPATH="$REPO/langchain:$REPO${PYTHONPATH:+:$PYTHONPATH}"     "$PYTHON" "$REPO/scripts/gate2a_step04_process1.py"       --repo "$REPO" --evidence "$evidence" --run-id "$run_id" --started-at "$started_at"

  # This second invocation is the required fresh Python process.
  PYTHONPATH="$REPO/langchain:$REPO${PYTHONPATH:+:$PYTHONPATH}"     "$PYTHON" "$REPO/scripts/gate2a_step04_process2.py"       --repo "$REPO" --evidence "$evidence" --run-id "$run_id"

  "$VALIDATOR_PYTHON" "$REPO/scripts/gate2a_step03_schema_validate.py"     --schema-dir "$REPO/shared/schemas"     --schema langgraph-run-state.schema.json     < "$evidence/state-before.json"     > "$evidence/state-before-schema-validation.json"

  "$VALIDATOR_PYTHON" "$REPO/scripts/gate2a_step03_schema_validate.py"     --schema-dir "$REPO/shared/schemas"     --schema langgraph-run-state.schema.json     < "$evidence/state-after-reload.json"     > "$evidence/state-after-reload-schema-validation.json"

  "$PYTHON" "$REPO/scripts/gate2a_step04_finalize.py"     --repo "$REPO" --evidence "$evidence" --run-id "$run_id"

  "$PYTHON" "$REPO/scripts/gate2a_step04_audit.py"     --repo "$REPO" --document-state active --run-dir "$evidence_rel"

  # Completion promotion is transactional for docs + accepted pointer.
  backup="$(mktemp -d)"
  cp "$REPO/AGENTS.md" "$backup/AGENTS.md"
  cp "$REPO/PLAN.md" "$backup/PLAN.md"
  cp "$REPO/README.md" "$backup/README.md"
  mkdir -p "$backup/docs"
  cp "$REPO/docs/CURRENT-STATUS.md" "$backup/docs/CURRENT-STATUS.md"
  latest="$EVIDENCE_ROOT/GATE2A-STEP04-LATEST.txt"
  if [[ -f "$latest" ]]; then cp "$latest" "$backup/LATEST.txt"; fi

  rollback_completion() {
    cp "$backup/AGENTS.md" "$REPO/AGENTS.md"
    cp "$backup/PLAN.md" "$REPO/PLAN.md"
    cp "$backup/README.md" "$REPO/README.md"
    cp "$backup/docs/CURRENT-STATUS.md" "$REPO/docs/CURRENT-STATUS.md"
    if [[ -f "$backup/LATEST.txt" ]]; then
      cp "$backup/LATEST.txt" "$latest"
    else
      rm -f "$latest"
    fi
  }

  set +e
  "$PYTHON" "$REPO/scripts/gate2a_step04_state.py"     --repo "$REPO" --state complete --run-dir "$evidence_rel"
  promote_rc=$?
  if [[ $promote_rc -eq 0 ]]; then
    tmp_latest="${latest}.tmp"
    printf '%s\n' "$evidence_rel" > "$tmp_latest"
    mv "$tmp_latest" "$latest"
    "$PYTHON" "$REPO/scripts/gate2a_step04_audit.py"       --repo "$REPO" --document-state complete
    promote_rc=$?
  fi
  if [[ $promote_rc -ne 0 ]]; then
    rollback_completion
    rm -rf "$backup"
    set -e
    fail "Step 2A.04 evidence passed pre-promotion checks but completion promotion failed; evidence retained and not accepted."
  fi
  set -e
  rm -rf "$backup"

  trap - ERR INT TERM
  pass "Gate 2A Step 2A.04 checkpoint proof passed."
  pass "Accepted evidence: $evidence_rel"
  pass "Model/provider calls: 0; Drupal calls/mutations: 0/0; recommendation writes: 0."
  printf '[STOP] Review retained checkpoint evidence and repository diff before staging or committing.\n'
}

case "$MODE" in
  preflight) preflight ;;
  run) run_proof ;;
  audit)
    "$PYTHON" "$REPO/scripts/gate2a_step04_audit.py"       --repo "$REPO" --document-state complete
    ;;
  *)
    fail "Usage: bash scripts/run-gate2a-step04.sh {preflight|run|audit}"
    ;;
esac
