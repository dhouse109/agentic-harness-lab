#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path

EXPECTED_BASE="096c790ba1d87d960c6a99bd383e034c6d70e3e2"
EXPECTED_STEP02="gate2a-step02-20260809T224238Z-2361786"
GATE1_SHA="2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd"
GATE2A_SHA="1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b"
GATE05_SHA="99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a"
ACTIVE_PACKAGE="gate-2a-step03-langgraph-tool-adapters-v1.0.0"
VERIFICATION_POINTER="GATE2A-STEP03-VERIFICATION-LATEST.txt"
NEXT_PACKAGE="gate-2a-step04-langgraph-state-and-sqlite-checkpoint-proof-v1.0.0"
EVIDENCE_ROOT="evidence/gates/gate-2a/tool-adapters"

class AuditError(RuntimeError): pass
def need(c,m):
    if not c: raise AuditError(m)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))

def predecessor(repo):
    need(subprocess.run(["git","-C",str(repo),"merge-base","--is-ancestor",EXPECTED_BASE,"HEAD"]).returncode==0,
         "Step 2A.02 merge baseline missing from ancestry")
    need(sha(repo/"shared/contracts/GATE1-DRUPAL-AI-FREEZE.json")==GATE1_SHA,"Gate 1 freeze changed")
    need(sha(repo/"shared/contracts/GATE2A-LANGGRAPH-BATCH-CONTRACT.json")==GATE2A_SHA,"Gate 2A contract changed")
    need(sha(repo/"shared/contracts/GATE05-SUBSTRATE-FREEZE.json")==GATE05_SHA,"Gate 0.5 freeze changed")
    ptr=(repo/"evidence/gates/gate-2a/runtime-probe/GATE2A-STEP02-LATEST.txt").read_text().strip()
    need(ptr.endswith(EXPECTED_STEP02),"Accepted Step 2A.02 pointer changed")
    rd=repo/ptr
    for line in (rd/"package-files-sha256.txt").read_text().splitlines():
        h,rel=line.split(maxsplit=1); need(sha(rd/rel)==h,f"Step 2A.02 checksum mismatch: {rel}")
    need(subprocess.run([
        str(repo/"langchain/.venv/bin/python"),str(repo/"scripts/gate2a_step02_audit.py"),
        "--repo",str(repo),"--document-state","complete"]).returncode==0,
        "Step 2A.02 complete-state audit failed")

def protected_diffs(repo):
    changed=subprocess.run(["git","-C",str(repo),"diff","--name-only","HEAD"],
                           check=True,capture_output=True,text=True).stdout.splitlines()
    allowed={
      "AGENTS.md","PLAN.md","README.md","docs/CURRENT-STATUS.md",
      "docs/gates/GATE-2A-STEP03-LANGGRAPH-TOOL-ADAPTERS.md",
      "langchain/agentic_harness_langgraph/__init__.py",
      "langchain/agentic_harness_langgraph/tools.py",
      "scripts/gate2a_step03_state.py","scripts/gate2a_step03_exercise.py",
      "scripts/gate2a_step03_audit.py","scripts/gate2a_step03_schema_validate.py",
      "scripts/gate2a_step03_compliance_verify.py","scripts/gate2a_step03_compliance_state.py",
      "scripts/run-gate2a-step03.sh","scripts/run-gate2a-step03-compliance.sh",
    }
    bad=[p for p in changed if p not in allowed and not p.startswith("evidence/gates/gate-2a/tool-adapters/")]
    need(not bad,f"Unexpected tracked changes for Step 2A.03: {bad}")
    for p in ("langchain/pyproject.toml","langchain/uv.lock","crewai/pyproject.toml","crewai/uv.lock","composer.lock"):
        need(p not in changed,f"Dependency file changed: {p}")

def verify_live(repo,run_dir):
    s=load(run_dir/"summary.json")
    need(s.get("status")=="pass","Live summary not pass")
    need(s.get("tool_count")==4,"Live tool count differs")
    for k in ("model_call_performed","provider_call_performed","checkpoint_state_opened",
              "raw_image_representation_retained","article_body_retained","credentials_retained",
              "authorization_header_retained","source_article_mutation_performed","dependency_change"):
        need(s.get(k) is False,f"Unexpected live flag: {k}")
    need(s.get("same_identity_replay") is True,"Live idempotency missing")
    need(s.get("pending_status_observed") is True,"Live pending status missing")
    need(s.get("drupal_restored_to_seeded_clean") is True,"Live restore missing")
    b=load(run_dir/"before-state.json"); d=load(run_dir/"during-state.json"); a=load(run_dir/"after-state.json")
    need(b.get("article_source_sha256")==d.get("article_source_sha256")==a.get("article_source_sha256"),
         "Live Article source changed")
    need(b.get("target_sequence_sha256")==d.get("target_sequence_sha256")==a.get("target_sequence_sha256"),
         "Live target hash changed")
    need(b.get("suggestion_count")==0 and d.get("suggestion_count")==1 and a.get("suggestion_count")==0,
         "Live recommendation count transition differs")
    for line in (run_dir/"package-files-sha256.txt").read_text().splitlines():
        h,rel=line.split(maxsplit=1); need(sha(run_dir/rel)==h,f"Live evidence checksum mismatch: {rel}")

def verify_compliance(repo,run_dir):
    s=load(run_dir/"summary.json")
    need(s.get("status")=="pass","Compliance summary not pass")
    for k in ("model_call_performed","provider_call_performed","checkpoint_state_opened",
              "successful_recommendation_submission_performed","drupal_mutation_performed",
              "raw_image_representation_retained","article_body_retained","credentials_retained",
              "authorization_headers_retained","raw_error_body_retained","dependency_change"):
        need(s.get(k) is False,f"Unexpected compliance flag: {k}")
    for k in ("tool_result_schema_conformance","all_correlation_ids_exact",
              "structured_error_behavior_proven","permission_matrix_proven",
              "editor_denied_all_four","agent_allowed_all_four","source_state_unchanged"):
        need(s.get(k) is True,f"Missing compliance proof: {k}")
    need(s.get("accepted_live_run_unchanged")=="gate2a-step03-20260809T233127Z-2375581",
         "Compliance verification references different live run")
    m=load(run_dir/"permission-matrix.json")
    need(m.get("editor_denied_all_four") is True and m.get("agent_allowed_all_four") is True,
         "Permission matrix incomplete")
    c=load(run_dir/"schema-conformance.json")
    need(c.get("status")=="pass" and c.get("all_correlation_ids_exact") is True,
         "Schema/correlation conformance failed")
    e=load(run_dir/"structured-errors.json")
    need(e.get("safe_substrate_error_preserved_exactly_static") is True,
         "Substrate error preservation not proven")
    need(e.get("route_denial_sanitized_static") is True,"Route denial sanitization not proven")
    src=load(run_dir/"source-before-after.json")
    need(src.get("status")=="pass" and src.get("source_state_unchanged") is True,
         "Compliance source-state proof failed")
    need(src.get("suggestion_count_before")==0 and src.get("suggestion_count_after")==0,
         "Compliance verification changed recommendation count")
    for line in (run_dir/"package-files-sha256.txt").read_text().splitlines():
        h,rel=line.split(maxsplit=1); need(sha(run_dir/rel)==h,f"Compliance checksum mismatch: {rel}")
    joined="\n".join(p.read_text(encoding="utf-8",errors="ignore") for p in run_dir.iterdir() if p.is_file())
    secret=re.compile(r"sk-[A-Za-z0-9_-]{20,}|data:image/|Authorization\s*:|Basic\s+[A-Za-z0-9+/]{16,}={0,2}",re.I)
    need(secret.search(joined) is None,"Potential secret/raw image in compliance evidence")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo",required=True)
    ap.add_argument("--document-state",choices=["active","verification","complete"],required=True)
    args=ap.parse_args(); repo=Path(args.repo).resolve()
    predecessor(repo); protected_diffs(repo)
    required=[
      "docs/gates/GATE-2A-STEP03-LANGGRAPH-TOOL-ADAPTERS.md",
      "langchain/agentic_harness_langgraph/tools.py",
      "scripts/gate2a_step03_exercise.py","scripts/gate2a_step03_audit.py",
      "scripts/gate2a_step03_schema_validate.py","scripts/gate2a_step03_compliance_verify.py",
      "scripts/gate2a_step03_compliance_state.py","scripts/run-gate2a-step03.sh",
      "scripts/run-gate2a-step03-compliance.sh",
    ]
    for rel in required: need((repo/rel).is_file(),f"Missing Step 2A.03 file: {rel}")

    static=subprocess.run([
      str(repo/"langchain/.venv/bin/python"),str(repo/"scripts/gate2a_step03_exercise.py"),
      "--repo",str(repo),"--mode","static"],capture_output=True,text=True)
    need(static.returncode==0,f"Static tool proof failed: {static.stderr[-500:]}")
    sv=json.loads(static.stdout)
    need(sv.get("status")=="pass" and sv.get("tool_count")==4 and sv.get("pass_through_results") is True,
         "Static tool proof not pass")

    docs={r:(repo/r).read_text(encoding="utf-8") for r in ["AGENTS.md","PLAN.md","README.md","docs/CURRENT-STATUS.md"]}
    live_ptr=repo/EVIDENCE_ROOT/"GATE2A-STEP03-LATEST.txt"
    if args.document_state=="active":
        for r,t in docs.items(): need(ACTIVE_PACKAGE in t,f"Active package marker missing in {r}")
        need("- [ ] Step 2A.03 — LangGraph tool adapters" in docs["PLAN.md"],"PLAN does not keep Step 2A.03 active")
        need(not live_ptr.exists(),"Live LATEST exists in active state")
    else:
        need(live_ptr.is_file(),"Live LATEST missing")
        live_dir=repo/live_ptr.read_text().strip()
        need(live_dir.parent.resolve()==(repo/EVIDENCE_ROOT).resolve(),"Live pointer escapes evidence root")
        verify_live(repo,live_dir)
        verify_ptr=repo/EVIDENCE_ROOT/VERIFICATION_POINTER
        if args.document_state=="verification":
            for r,t in docs.items(): need("Step 2A.03 compliance verification" in t,f"Pending marker missing in {r}")
            need("- [ ] Step 2A.03 — LangGraph tool adapters (compliance verification pending)" in docs["PLAN.md"],
                 "PLAN does not mark compliance pending")
            need(not verify_ptr.exists(),"Verification pointer already exists")
        else:
            need("- [x] Step 2A.03 — LangGraph tool adapters" in docs["PLAN.md"],"PLAN does not mark Step 2A.03 complete")
            for r,t in docs.items():
                need(NEXT_PACKAGE in t,f"Next 2A.04 marker missing in {r}")
                need("Accepted Step 2A.03 compliance verification:" in t,f"Compliance acceptance missing in {r}")
            need(verify_ptr.is_file(),"Verification pointer missing")
            verify_dir=repo/verify_ptr.read_text().strip()
            need(verify_dir.parent.resolve()==(repo/EVIDENCE_ROOT).resolve(),"Verification pointer escapes evidence root")
            verify_compliance(repo,verify_dir)
    print(f"[PASS] Gate 2A Step 2A.03 {args.document_state} audit passed.")

if __name__=="__main__":
    try: main()
    except AuditError as exc: raise SystemExit(f"[ERROR] {exc}")
