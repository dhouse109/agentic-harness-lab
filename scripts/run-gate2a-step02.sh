#!/usr/bin/env bash
set -Eeuo pipefail
MODE="${1:-audit}"
REPO="$(git rev-parse --show-toplevel)"
EXPECTED_BASE="c48c49c53bcf11b33db7f62aedc06dbcbb85d045"
EXPECTED_BRANCH="gate-2a-step02-langgraph-runtime-and-checkpoint-probe"
EVIDENCE_ROOT="$REPO/evidence/gates/gate-2a/runtime-probe"
PYTHON="$REPO/langchain/.venv/bin/python"
PROBE="$REPO/scripts/gate2a_step02_probe.py"
AUDITOR="$REPO/scripts/gate2a_step02_audit.py"
fail(){ printf '[ERROR] %s\n' "$*" >&2; exit 1; }

verify_repo(){
  local branch head
  branch="$(git -C "$REPO" branch --show-current)"
  head="$(git -C "$REPO" rev-parse HEAD)"
  case "$MODE" in
    run)
      [[ "$branch" == "$EXPECTED_BRANCH" ]] || fail "Run mode requires branch $EXPECTED_BRANCH"
      [[ "$head" == "$EXPECTED_BASE" ]] || fail "Run mode requires uncommitted Step 2A.02 work on base $EXPECTED_BASE"
      ;;
    audit)
      case "$branch" in
        "$EXPECTED_BRANCH"|main) ;;
        *) fail "Audit mode requires Step 2A.02 branch or main" ;;
      esac
      git -C "$REPO" merge-base --is-ancestor "$EXPECTED_BASE" "$head" \
        || fail "Step 2A.01 merge baseline missing from ancestry"
      ;;
    *) fail "Usage: bash scripts/run-gate2a-step02.sh {run|audit}" ;;
  esac
  [[ -x "$PYTHON" ]] || fail "Missing pinned LangGraph Python: $PYTHON"
  [[ -f "$PROBE" && -f "$AUDITOR" ]] || fail "Missing Step 2A.02 scripts"
}

verify_step01_evidence(){
  local step01_ptr step01_run_dir
  step01_ptr="$REPO/evidence/gates/gate-2a/contract/GATE2A-STEP01-LATEST.txt"
  [[ -f "$step01_ptr" ]] || fail "Missing Step 2A.01 latest evidence pointer"
  step01_run_dir="$REPO/$(<"$step01_ptr")"
  [[ -d "$step01_run_dir" ]] || fail "Missing retained Step 2A.01 evidence directory"
  (cd "$step01_run_dir" && sha256sum -c package-files-sha256.txt >/dev/null) \
    || fail "Step 2A.01 retained evidence checksum failed"
  printf '[PASS] Gate 2A Step 2A.01 retained evidence checksum passed.\n'
}

preflight_to_file(){
  local out="$1"
  {
    "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state active
    bash "$REPO/scripts/run-gate1-step07-drupal-ai-certification-and-handoff.sh" audit
    verify_step01_evidence
  } >"$out"
}

write_adr(){
  local run_dir="$1"
  "$PYTHON" - "$REPO" "$run_dir" <<'PY'
from pathlib import Path
import json, sys
repo=Path(sys.argv[1]); rd=Path(sys.argv[2])
a=json.loads((rd/"architecture-decision.json").read_text())
retry=json.loads((rd/"retry-policy.json").read_text())
cp=json.loads((rd/"checkpointer-probe.json").read_text())
p=repo/"docs/decisions/ADR-0010-langgraph-runtime-and-checkpoint-path.md"
body=f"""# ADR-0010: LangGraph runtime and checkpoint path

- **Status:** Accepted
- **Decision date:** 2026-08-09
- **Decision owner:** Program lead
- **Evidence:** `{rd.relative_to(repo)}`

## Context

Gate 2A Step 2A.01 intentionally deferred the exact pinned LangGraph runtime/checkpoint API and runtime path to Step 2A.02. This ADR records only model-free observations from the installed locked environment.

## Decision

Use:

- graph runtime: `{a["graph"]}`;
- deterministic graph routing for workflow/write decisions;
- checkpointer: `{a["checkpointer"]}`;
- runtime root: `{a["runtime_root"]}`;
- per-run SQLite path: `{a["per_run_checkpoint_path"]}`;
- stable Gate 2A `run_id` as `configurable.thread_id`;
- checkpoint namespace observed by the probe: `{cp.get("checkpoint_namespace")}`;
- interrupt: `{a["interrupt"]}`;
- resume: `{a["resume"]}`;
- structured output: `{a["structured_output"]}`;
- image input representation: `{a["image_message"]}`;
- transport retry policy: explicit `max_retries=0` (supported: `{retry["explicit_zero_supported"]}`);
- thin LangChain-native tool wrappers invoked by deterministic graph nodes.

Runtime/checkpoint state remains framework-owned under `langchain/.gate2a-runtime/` and must not contain raw image bytes/data URLs, credentials, hidden reasoning, or shared Drupal runtime state.

## Boundaries

This decision makes no model call and no Drupal mutation. It does not prove live tool behavior, live model behavior, or Gate 2C recovery. Step 2A.04 remains the stronger persistence/isolation proof.

## Consequences

Step 2A.03 may implement thin shared-operation wrappers without changing the frozen substrate. A future need for dependency upgrades or undocumented framework patches is a stop condition and requires planning review rather than silent version drift.
"""
p.write_text(body, encoding="utf-8")
PY
}

transition_complete(){
  local run_id="$1"
  "$PYTHON" - "$REPO" "$run_id" <<'PY'
from pathlib import Path
import os, sys
repo=Path(sys.argv[1]); rid=sys.argv[2]
accepted=f"Accepted Step 2A.02 evidence run: `{rid}`\nAccepted runtime ADR: `docs/decisions/ADR-0010-langgraph-runtime-and-checkpoint-path.md`"
docs={
    rel:(repo/rel).read_text(encoding="utf-8")
    for rel in ["AGENTS.md","README.md","PLAN.md","docs/CURRENT-STATUS.md"]
}
ops={
    "AGENTS.md":[
        ("**Active package:** `gate-2a-step02-langgraph-runtime-and-checkpoint-probe-v1.0.4`.",
         "**Step 2A.02:** complete.\n\n**Next package:** `gate-2a-step03-langgraph-tool-adapters-v1.0.0`."),
        ("Do not generate Step 2A.03 until Step 2A.02 is passing and committed.",
         "Do not generate Step 2A.03 until Step 2A.02 is committed, merged, local `main` is resynchronized, and the post-merge audit passes.\n\n"+accepted),
    ],
    "README.md":[
        ("- **Active package:** `gate-2a-step02-langgraph-runtime-and-checkpoint-probe-v1.0.4`.\n- **Step 2A.02:** active — pinned runtime/checkpoint capability probe only.",
         "- **Step 2A.02:** complete.\n- **Next package:** `gate-2a-step03-langgraph-tool-adapters-v1.0.0`.\n"+accepted),
    ],
    "PLAN.md":[
        ("**Active package:**\n\n```text\ngate-2a-step02-langgraph-runtime-and-checkpoint-probe-v1.0.4\n```",
         "**Completed package:**\n\n```text\ngate-2a-step02-langgraph-runtime-and-checkpoint-probe-v1.0.4\n```\n\n**Next package:**\n\n```text\ngate-2a-step03-langgraph-tool-adapters-v1.0.0\n```\n\n"+accepted),
        ("- [ ] Step 2A.02 — LangGraph runtime and checkpoint probe",
         "- [x] Step 2A.02 — LangGraph runtime and checkpoint probe"),
    ],
    "docs/CURRENT-STATUS.md":[
        ("- **Active package:** `gate-2a-step02-langgraph-runtime-and-checkpoint-probe-v1.0.4`.",
         "- **Step 2A.02:** complete.\n- **Next package:** `gate-2a-step03-langgraph-tool-adapters-v1.0.0`.\n"+accepted),
        ("Do not generate Step 2A.03 until Step 2A.02 is passing and committed.",
         "Do not generate Step 2A.03 until Step 2A.02 is committed and merged, local `main` is resynchronized, and the post-merge audit passes."),
    ],
}
new_docs={}
for rel,t in docs.items():
    for old,new in ops[rel]:
        if old not in t:
            raise SystemExit(f"[ERROR] Completion anchor missing in {rel}: {old[:90]}")
        t=t.replace(old,new,1)
    new_docs[rel]=t

temps=[]
try:
    for rel,t in new_docs.items():
        p=repo/rel
        tmp=p.with_name(p.name+".gate2a-step02.tmp")
        tmp.write_text(t,encoding="utf-8")
        temps.append((p,tmp))
    for p,tmp in temps:
        os.replace(tmp,p)
except Exception:
    for _,tmp in temps:
        try: tmp.unlink()
        except FileNotFoundError: pass
    raise
PY
}

verify_evidence(){
  local pointer="$EVIDENCE_ROOT/GATE2A-STEP02-LATEST.txt" run_dir
  [[ -f "$pointer" ]] || fail "Missing Step 2A.02 latest pointer"
  run_dir="$REPO/$(<"$pointer")"
  [[ -d "$run_dir" ]] || fail "Missing Step 2A.02 evidence directory"
  (cd "$run_dir" && sha256sum -c package-files-sha256.txt >/dev/null) \
    || fail "Step 2A.02 evidence checksum failed"
  if rg -n -i 'sk-[A-Za-z0-9_-]{20,}|data:image/|Authorization[[:space:]]*:|Basic[[:space:]]+[A-Za-z0-9+/]{16,}={0,2}|probe-not-used' "$run_dir" >/dev/null; then
    fail "Potential secret-bearing or dummy credential content found in Step 2A.02 evidence"
  fi
  printf '[PASS] Gate 2A Step 2A.02 retained evidence audit passed.\n'
  printf '[PASS] Evidence: %s\n' "${run_dir#"$REPO/"}"
}

restore_finalization(){
  local backup="$1"
  set +e
  for rel in AGENTS.md README.md PLAN.md docs/CURRENT-STATUS.md; do
    mkdir -p "$REPO/$(dirname "$rel")"
    cp "$backup/$rel" "$REPO/$rel"
  done
  rm -f "$EVIDENCE_ROOT/GATE2A-STEP02-LATEST.txt"
  rm -f "$REPO/docs/decisions/ADR-0010-langgraph-runtime-and-checkpoint-path.md"
  set -e
}

verify_repo
case "$MODE" in
  run)
    [[ ! -e "$EVIDENCE_ROOT/GATE2A-STEP02-LATEST.txt" ]] \
      || fail "Accepted Step 2A.02 evidence already exists; run mode is closed"
    [[ ! -e "$EVIDENCE_ROOT/GATE2A-STEP02-LAST-RUN.txt" ]] \
      || fail "A prior Step 2A.02 attempt exists; inspect it before any rerun"
    [[ ! -e "$REPO/docs/decisions/ADR-0010-langgraph-runtime-and-checkpoint-path.md" ]] \
      || fail "ADR-0010 already exists before the Step 2A.02 run"

    preflight_tmp="$(mktemp)"
    if ! preflight_to_file "$preflight_tmp"; then
      cat "$preflight_tmp" >&2 || true
      rm -f "$preflight_tmp"
      fail "Step 2A.02 preflight failed before evidence creation"
    fi

    mkdir -p "$EVIDENCE_ROOT"
    run_id="gate2a-step02-$(date -u +%Y%m%dT%H%M%SZ)-$$"
    run_dir="$EVIDENCE_ROOT/$run_id"
    mkdir "$run_dir"
    mv "$preflight_tmp" "$run_dir/predecessor-audits.log"
    printf '%s\n' "${run_dir#"$REPO/"}" > "$EVIDENCE_ROOT/GATE2A-STEP02-LAST-RUN.txt"

    set +e
    "$PYTHON" "$PROBE" --repo "$REPO" --evidence "$run_dir" --run-id "$run_id"
    probe_status=$?
    set -e

    [[ -f "$run_dir/summary.json" ]] || fail "Probe failed without summary evidence"

    if [[ "$probe_status" -ne 0 ]]; then
      (
        cd "$run_dir"
        find . -maxdepth 1 -type f ! -name package-files-sha256.txt -printf '%f\n' \
          | sort | xargs -r sha256sum > package-files-sha256.txt
      )
      printf '[STOP] Step 2A.02 pinned-runtime probe failed. Evidence retained at %s\n' \
        "${run_dir#"$REPO/"}"
      exit "$probe_status"
    fi

    write_adr "$run_dir"
    (
      cd "$run_dir"
      find . -maxdepth 1 -type f ! -name package-files-sha256.txt -printf '%f\n' \
        | sort | xargs -r sha256sum > package-files-sha256.txt
    )

    if ! "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state candidate \
      --candidate-run-dir "${run_dir#"$REPO/"}" >/dev/null; then
      rm -f "$REPO/docs/decisions/ADR-0010-langgraph-runtime-and-checkpoint-path.md"
      printf '[STOP] Step 2A.02 probe passed but candidate evidence/finalization audit failed. Evidence retained at %s\n' \
        "${run_dir#"$REPO/"}"
      exit 3
    fi

    final_backup="$(mktemp -d)"
    mkdir -p "$final_backup/docs"
    cp "$REPO/AGENTS.md" "$final_backup/AGENTS.md"
    cp "$REPO/README.md" "$final_backup/README.md"
    cp "$REPO/PLAN.md" "$final_backup/PLAN.md"
    cp "$REPO/docs/CURRENT-STATUS.md" "$final_backup/docs/CURRENT-STATUS.md"

    if ! transition_complete "$run_id"; then
      restore_finalization "$final_backup"
      rm -rf "$final_backup"
      printf '[STOP] Step 2A.02 probe passed but document finalization failed. Evidence retained at %s\n' \
        "${run_dir#"$REPO/"}"
      exit 4
    fi

    latest_tmp="$EVIDENCE_ROOT/.GATE2A-STEP02-LATEST.txt.tmp"
    printf '%s\n' "${run_dir#"$REPO/"}" > "$latest_tmp"
    mv "$latest_tmp" "$EVIDENCE_ROOT/GATE2A-STEP02-LATEST.txt"

    if ! "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state complete >/dev/null; then
      restore_finalization "$final_backup"
      rm -rf "$final_backup"
      printf '[STOP] Step 2A.02 probe passed but final complete-state audit failed. Evidence retained at %s\n' \
        "${run_dir#"$REPO/"}"
      exit 5
    fi

    rm -rf "$final_backup"
    verify_evidence
    printf '[PASS] Gate 2A Step 2A.02 runtime/checkpoint capability boundary passed.\n'
    printf '[STOP] Review evidence and diff; human commit approval is required.\n'
    ;;
  audit)
    "$PYTHON" "$AUDITOR" --repo "$REPO" --document-state complete >/dev/null
    verify_evidence
    printf '[PASS] Gate 2A Step 2A.02 post-run audit passed.\n'
    ;;
esac
