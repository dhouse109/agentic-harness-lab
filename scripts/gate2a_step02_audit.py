#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path

EXPECTED_BASE="c48c49c53bcf11b33db7f62aedc06dbcbb85d045"
EXPECTED_GATE1="2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd"
EXPECTED_GATE2A="1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b"
STEP02_PACKAGE="gate-2a-step02-langgraph-runtime-and-checkpoint-probe-v1.0.4"
STEP03_PACKAGE="gate-2a-step03-langgraph-tool-adapters-v1.0.0"
ACCEPTED_STEP01="gate2a-step01-20260809T202418Z-2334327"
RUNTIME_EVIDENCE_ROOT="evidence/gates/gate-2a/runtime-probe"

class AuditError(RuntimeError): pass

def need(c,m):
    if not c:
        raise AuditError(m)

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def text(repo: Path, rel: str) -> str:
    return (repo/rel).read_text(encoding="utf-8")

def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

def validate_run_evidence(repo: Path, run_dir: Path) -> None:
    root=(repo/RUNTIME_EVIDENCE_ROOT).resolve()
    rd=run_dir.resolve()
    need(rd.parent == root, "Step 2A.02 run directory is outside runtime-probe evidence root")
    need(rd.is_dir(), "Step 2A.02 evidence directory missing")

    summary=load(rd/"summary.json")
    need(summary.get("status")=="pass", "Step 2A.02 summary is not pass")
    for flag in ("model_call_performed","drupal_state_mutated","dependency_change"):
        need(summary.get(flag) is False, f"Unexpected Step 2A.02 {flag}")

    arch=load(rd/"architecture-decision.json")
    need(arch.get("checkpointer")=="langgraph.checkpoint.sqlite.SqliteSaver",
         "Unexpected checkpointer architecture")
    need(arch.get("runtime_root")=="langchain/.gate2a-runtime/",
         "Unexpected runtime root")
    need(arch.get("model_call_performed") is False, "Architecture evidence claims a model call")
    need(arch.get("drupal_state_mutated") is False, "Architecture evidence claims Drupal mutation")

    retry=load(rd/"retry-policy.json")
    need(retry.get("explicit_zero_supported") is True,
         "Explicit zero retry policy not proven")
    need(retry.get("experiment_setting")==0, "Experiment retry setting is not zero")
    need(retry.get("model_call_performed") is False, "Retry probe claims a model call")

    cp=load(rd/"checkpointer-probe.json")
    need(cp.get("status")=="pass", "SQLite checkpointer probe did not pass")
    need(cp.get("raw_image_bytes_persisted") is False, "Raw image bytes persisted")
    need(cp.get("credentials_persisted") is False, "Credentials persisted")

    interrupt=load(rd/"interrupt-api-probe.json")
    need(interrupt.get("status")=="pass", "Interrupt/resume probe did not pass")

    structured=load(rd/"structured-output-api.json")
    need(structured.get("status")=="pass", "Structured-output API probe did not pass")
    need(structured.get("strict_parameter_supported") is True,
         "Strict structured-output parameter not proven")
    need(structured.get("model_call_performed") is False,
         "Structured-output API probe claims a model call")

    manifest=rd/"package-files-sha256.txt"
    need(manifest.is_file(), "Evidence checksum manifest missing")
    for line in manifest.read_text(encoding="utf-8").splitlines():
        h, rel=line.split(maxsplit=1)
        need(sha(rd/rel)==h, f"Evidence checksum mismatch: {rel}")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--document-state",
                    choices=["active","candidate","complete","progressed"],
                    required=True)
    ap.add_argument("--candidate-run-dir")
    args=ap.parse_args()
    repo=Path(args.repo).resolve()

    need(subprocess.run(
        ["git","-C",str(repo),"merge-base","--is-ancestor",EXPECTED_BASE,"HEAD"]
    ).returncode==0, "Step 2A.01 merge commit is not in HEAD ancestry")
    need(sha(repo/"shared/contracts/GATE1-DRUPAL-AI-FREEZE.json")==EXPECTED_GATE1,
         "Gate 1 freeze changed")
    need(sha(repo/"shared/contracts/GATE2A-LANGGRAPH-BATCH-CONTRACT.json")==EXPECTED_GATE2A,
         "Gate 2A contract changed")
    need(text(repo,"evidence/gates/gate-2a/contract/GATE2A-STEP01-LATEST.txt").strip().endswith(ACCEPTED_STEP01),
         "Accepted Step 2A.01 pointer changed")
    need((repo/"langchain/.venv/bin/python").is_file(),
         "Missing pinned langchain/.venv Python")
    need(subprocess.run(
        ["git","-C",str(repo),"check-ignore","-q","langchain/.gate2a-runtime/probe.sqlite"]
    ).returncode==0, "LangGraph Gate 2A runtime root is not gitignored")

    changed=subprocess.run(
        ["git","-C",str(repo),"diff","--name-only","HEAD"],
        check=True,capture_output=True,text=True
    ).stdout.splitlines()
    forbidden=[
        p for p in changed
        if p.startswith("evidence/gates/gate-1/")
        or p.startswith("shared/contracts/GATE1-")
        or p=="shared/contracts/GATE2A-LANGGRAPH-BATCH-CONTRACT.json"
        or p=="shared/contracts/GATE2A-LANGGRAPH-BATCH-CONTRACT.sha256"
        or p in (
            "langchain/pyproject.toml","langchain/uv.lock",
            "crewai/pyproject.toml","crewai/uv.lock","composer.lock"
        )
    ]
    need(not forbidden, f"Protected/frozen paths modified: {forbidden}")

    docs={
        r:text(repo,r)
        for r in ["AGENTS.md","PLAN.md","README.md","docs/CURRENT-STATUS.md"]
    }

    if args.document_state in ("active","candidate"):
        for r,t in docs.items():
            need(STEP02_PACKAGE in t, f"Active 2A.02 marker missing in {r}")
        need("- [ ] Step 2A.02 — LangGraph runtime and checkpoint probe" in docs["PLAN.md"],
             "PLAN does not keep 2A.02 active")
        if args.document_state=="active":
            need(args.candidate_run_dir is None,
                 "--candidate-run-dir is not valid for active audit")
        else:
            need(args.candidate_run_dir is not None,
                 "Candidate audit requires --candidate-run-dir")
            need((repo/"docs/decisions/ADR-0010-langgraph-runtime-and-checkpoint-path.md").is_file(),
                 "ADR-0010 missing for candidate audit")
            validate_run_evidence(repo, repo/args.candidate_run_dir)
    else:
        need("- [x] Step 2A.02 — LangGraph runtime and checkpoint probe" in docs["PLAN.md"],
             "PLAN does not mark 2A.02 complete")
        need((repo/"docs/decisions/ADR-0010-langgraph-runtime-and-checkpoint-path.md").is_file(),
             "ADR-0010 missing")
        pointer=repo/RUNTIME_EVIDENCE_ROOT/"GATE2A-STEP02-LATEST.txt"
        need(pointer.is_file(), "Step 2A.02 latest pointer missing")
        run_dir=repo/pointer.read_text(encoding="utf-8").strip()
        validate_run_evidence(repo, run_dir)
        if args.document_state=="progressed":
            for r,t in docs.items():
                need(STEP03_PACKAGE in t, f"Next Step 2A.03 marker missing in {r}")

    print(f"[PASS] Gate 2A Step 2A.02 {args.document_state} audit passed.")

if __name__=="__main__":
    try:
        main()
    except AuditError as exc:
        raise SystemExit(f"[ERROR] {exc}")
