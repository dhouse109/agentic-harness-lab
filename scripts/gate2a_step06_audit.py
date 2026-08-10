#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

BASE="2b61e5859a5474e8422b85e0108b89808c519208"
STEP05="evidence/gates/gate-2a/canonical-slice/gate2a-step05-20260810T140133Z-0025b888"
PACKAGE="gate-2a-step06-langgraph-human-interrupt-and-review-resume-v1.0.8"
STEP07="gate-2a-step07-langgraph-batch-runner-v1.0.0"
FREEZES={
"shared/contracts/GATE05-SUBSTRATE-FREEZE.json":"99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a",
"shared/contracts/GATE1-DRUPAL-AI-FREEZE.json":"2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd",
"shared/contracts/GATE2A-LANGGRAPH-BATCH-CONTRACT.json":"1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b"}
REQUIRED=["docs/gates/GATE-2A-STEP06-LANGGRAPH-HUMAN-INTERRUPT-AND-REVIEW-RESUME.md","langchain/agentic_harness_langgraph/human_review.py","drupal/scripts/gate2a-step06-review-lineage.php","scripts/gate2a_step06_finalize.py","scripts/gate2a_step06_state.py","scripts/gate2a_step06_audit.py","scripts/run-gate2a-step06.sh"]

def req(ok:bool,msg:str)->None:
    if not ok: raise SystemExit(f"[ERROR] {msg}")
def sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p:Path): return json.loads(p.read_text(encoding="utf-8"))

def audit_documents(r:Path,state:str)->None:
    docs={n:(r/n).read_text(encoding="utf-8") for n in ("AGENTS.md","PLAN.md","README.md","docs/CURRENT-STATUS.md")}
    if state=="active":
        req(f"**Step 2A.06:** active — LangGraph persisted interrupt + Drupal human-review resume proof." in docs["AGENTS.md"],"AGENTS active Step 2A.06 marker missing")
        req(f"**Active package:** `{PACKAGE}`." in docs["AGENTS.md"],"AGENTS active package marker missing")
        req(f"```text\n{PACKAGE}\n```" in docs["PLAN.md"],"PLAN active package marker missing")
        req("- [ ] Step 2A.06 — LangGraph human interrupt and review resume" in docs["PLAN.md"],"PLAN Step 2A.06 checkbox should remain open while active")
        req(f"- **Step 2A.06:** active — LangGraph persisted interrupt + Drupal human-review resume proof." in docs["README.md"],"README active Step 2A.06 marker missing")
        req(f"- **Active package:** `{PACKAGE}`." in docs["README.md"],"README active package marker missing")
        req(f"- **Step 2A.06:** active — LangGraph persisted interrupt + Drupal human-review resume proof." in docs["docs/CURRENT-STATUS.md"],"CURRENT active Step 2A.06 marker missing")
        req(f"- **Active package:** `{PACKAGE}`." in docs["docs/CURRENT-STATUS.md"],"CURRENT active package marker missing")
        req("Step 2A.06 is active. Step 2A.07 remains locked until Step 2A.06 is committed and merged" in docs["docs/CURRENT-STATUS.md"],"CURRENT active fresh-session marker missing")
        for name,text in docs.items():
            req("Step 2A.06 is next but remains locked" not in text,f"Contradictory stale Step 2A.06-next marker remains in {name}")
            req("gate-2a-step06-langgraph-human-interrupt-and-review-resume-v1.0.3" not in text,f"Superseded v1.0.3 active package marker remains in {name}")
    else:
        req("**Step 2A.06:** complete." in docs["AGENTS.md"] and f"**Next package:** `{STEP07}`." in docs["AGENTS.md"],"AGENTS complete/next marker missing")
        req("- [x] Step 2A.06 — LangGraph human interrupt and review resume" in docs["PLAN.md"] and STEP07 in docs["PLAN.md"],"PLAN complete/next marker missing")
        req("- **Step 2A.06:** complete." in docs["README.md"] and f"- **Next package:** `{STEP07}`." in docs["README.md"],"README complete/next marker missing")
        req("- **Step 2A.06:** complete." in docs["docs/CURRENT-STATUS.md"] and f"- **Next package:** `{STEP07}`." in docs["docs/CURRENT-STATUS.md"],"CURRENT complete/next marker missing")
        req("Step 2A.01 through Step 2A.06 are complete. Step 2A.07 is next but remains locked" in docs["docs/CURRENT-STATUS.md"],"CURRENT complete fresh-session marker missing")
        for name,text in docs.items():
            req("Step 2A.06 is active" not in text,f"Stale Step 2A.06-active marker remains in {name}")
            req("Step 2A.06 is next but remains locked" not in text,f"Stale Step 2A.06-next marker remains in {name}")

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--repo",required=True); ap.add_argument("--document-state",choices=("active","complete"),required=True); ap.add_argument("--run-dir")
    a=ap.parse_args(); r=Path(a.repo).resolve()
    for rel,want in FREEZES.items(): req(sha(r/rel)==want,f"Frozen hash changed: {rel}")
    req((r/"evidence/gates/gate-2a/canonical-slice/GATE2A-STEP05-LATEST.txt").read_text(encoding="utf-8").strip()==STEP05,"Accepted Step 2A.05 pointer changed")
    for rel in REQUIRED: req((r/rel).is_file(),f"Missing Step 2A.06 installed file: {rel}")
    audit_documents(r,a.document_state)
    run_rel=a.run_dir
    if a.document_state=="complete" and not run_rel:
        latest=r/"evidence/gates/gate-2a/human-interrupt/GATE2A-STEP06-LATEST.txt"; req(latest.is_file(),"Accepted Step 2A.06 LATEST pointer missing"); run_rel=latest.read_text(encoding="utf-8").strip()
    if run_rel:
        ev=r/run_rel; req(ev.is_dir(),"Step 2A.06 run directory missing")
        required=["run-id.txt","before-state.json","pending-state.json","reviewed-state.json","after-state.json","accepted-step05-provenance.json","call-counters.json","pending-recommendation.json","checkpoint-before-review.json","interrupt-event.json","checkpoint-config.json","reviewer-revision-lineage.json","resume-event.json","post-review-status.json","post-review-context-summary.json","checkpoint-after-resume.json","checkpoint-before-review-schema-validation.json","checkpoint-after-resume-schema-validation.json","source-before-after.json","reset.json","checkpoint-privacy.json","secret-scan.log","summary.json","summary.md","package-files-sha256.txt"]
        for f in required: req((ev/f).is_file(),f"Missing Step 2A.06 evidence file: {f}")
        run_id=(ev/"run-id.txt").read_text(encoding="utf-8").strip(); import re; req(re.fullmatch(r"langgraph-[0-9]{8}T[0-9]{6}Z-[a-z0-9]{4,12}",run_id) is not None,"Accepted Step 2A.06 run_id violates frozen format")
        s=load(ev/"summary.json"); req(s.get("status")=="pass","Step 2A.06 summary is not pass"); req(s.get("model_call_count")==0,"Step 2A.06 model call count is not zero"); req(s.get("interrupt_persisted") is True and s.get("same_run_thread_resumed") is True,"Interrupt/resume proof missing"); req(s.get("human_reviewer")=="editor_dana" and s.get("post_review_status")=="approved","Human review proof differs"); req(s.get("source_article_mutation_performed") is False and s.get("automatic_publication_performed") is False,"Source mutation/publication observed"); req(s.get("drupal_restored_to_seeded_clean") is True,"Drupal reset proof failed"); req(s.get("gate2c_failure_injection_exercised") is False,"Gate 2C seam exercised too early")
        cpb=load(ev/"checkpoint-before-review.json"); cpa=load(ev/"checkpoint-after-resume.json"); req(cpb.get("status")=="interrupted","Accepted pre-review checkpoint status is not frozen interrupted"); req(cpb.get("run_id")==run_id and cpb.get("thread_id")==run_id,"Accepted pre-review run/thread identity differs"); req(cpa.get("run_id")==run_id and cpa.get("thread_id")==run_id and cpa.get("resumed_at"),"Accepted post-resume run/thread proof differs")
        for vf in ("checkpoint-before-review-schema-validation.json","checkpoint-after-resume-schema-validation.json"):
            v=load(ev/vf); req(v.get("status")=="pass" and v.get("schema")=="langgraph-run-state.schema.json",f"Schema validation evidence is not pass: {vf}")
        for line in (ev/"package-files-sha256.txt").read_text(encoding="utf-8").splitlines():
            digest,filename=line.split("  ",1); req(sha(ev/filename)==digest,f"Evidence checksum mismatch: {filename}")
    print("[PASS] Gate 2A Step 2A.06 audit passed.")
    if run_rel: print(f"[PASS] Evidence: {run_rel}")
    return 0
if __name__=="__main__": raise SystemExit(main())
