#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
from typing import Any

EXPECTED_ARTICLE_SHA = "f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17"

def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)+"\n", encoding="utf-8")

def req(ok: bool, msg: str) -> None:
    if not ok: raise SystemExit(f"[ERROR] {msg}")

def article_sha(state: dict[str, Any]) -> str:
    value = state.get("article_source_sha256")
    req(isinstance(value, str) and value, "Drupal state lacks article_source_sha256")
    return value

def suggestion_count(state: dict[str, Any]) -> int:
    value = state.get("suggestion_count")
    req(isinstance(value, int), "Drupal state lacks integer suggestion_count")
    return value

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--repo", required=True); ap.add_argument("--evidence", required=True); ap.add_argument("--run-id", required=True)
    a=ap.parse_args(); repo=Path(a.repo).resolve(); ev=Path(a.evidence).resolve()
    before=load(ev/"before-state.json"); pending=load(ev/"pending-state.json"); reviewed=load(ev/"reviewed-state.json"); after=load(ev/"after-state.json")
    lineage=load(ev/"reviewer-revision-lineage.json"); status=load(ev/"post-review-status.json"); counters=load(ev/"call-counters.json")
    cp_before=load(ev/"checkpoint-before-review.json"); cp_after=load(ev/"checkpoint-after-resume.json")
    for label,state in (("before",before),("pending",pending),("reviewed",reviewed),("after",after)):
        req(article_sha(state)==EXPECTED_ARTICLE_SHA, f"{label} Article source hash changed")
    req(before.get("seeded_clean") is True and after.get("seeded_clean") is True, "before/after Drupal state is not seeded-clean")
    req(suggestion_count(before)==0 and suggestion_count(after)==0, "before/after suggestion count is not zero")
    req(suggestion_count(pending)==1 and suggestion_count(reviewed)==1, "pending/reviewed suggestion count is not one")
    req(lineage.get("status")=="pass" and lineage.get("audit_state")=="reviewed", "review lineage is not passing reviewed state")
    revs=lineage.get("revisions"); req(isinstance(revs,list) and len(revs)==2, "review lineage does not contain exactly two revisions")
    first,last=revs[0],revs[-1]
    req(first["revision_user"]["name"]=="agent_bot" and first["review_status"]=="pending", "initial revision provenance differs")
    req(last["revision_user"]["name"]=="editor_dana" and last["review_status"]=="approved", "reviewer revision provenance differs")
    req(last["proposed_alt"] != first["proposed_alt"], "edit-and-approve did not change proposed alt")
    req(status.get("status")=="approved" and status.get("reviewer_username")=="editor_dana" and status.get("reviewed_at"), "post-resume status did not observe editor_dana approval")
    req(counters.get("model_invocations_attempted")==0 and counters.get("model_invocations_succeeded")==0, "Step 2A.06 performed a model call")
    req(counters.get("automatic_model_retries_configured")==0 and counters.get("semantic_retry_loop_performed") is False, "Step 2A.06 retry boundary changed")
    req(cp_before.get("run_id")==a.run_id and cp_before.get("thread_id")==a.run_id, "pre-review run/thread identity differs")
    req(cp_after.get("run_id")==a.run_id and cp_after.get("thread_id")==a.run_id, "post-resume run/thread identity differs")
    req(cp_before.get("status")=="interrupted" and cp_before.get("interrupted_at"), "pre-review checkpoint is not interrupted")
    req(cp_after.get("resumed_at"), "post-resume checkpoint lacks resumed_at")
    req(cp_before.get("gate2c_failure_injection_fired") is False and cp_after.get("gate2c_failure_injection_fired") is False, "Gate 2C failure seam was exercised")
    dump(ev/"source-before-after.json", {
        "schema_version":1,"status":"pass","article_source_sha256_before":article_sha(before),"article_source_sha256_pending":article_sha(pending),"article_source_sha256_reviewed":article_sha(reviewed),"article_source_sha256_after":article_sha(after),"source_article_mutation_performed":False,"automatic_publication_performed":False})
    dump(ev/"reset.json", {"schema_version":1,"status":"pass","seeded_clean_before":True,"seeded_clean_after":True,"suggestion_count_before":0,"suggestion_count_after":0})
    runtime_rel=f"langchain/.gate2a-runtime/{a.run_id}.sqlite"; runtime=repo/runtime_rel
    req(runtime.exists(), "LangGraph runtime SQLite DB is missing")
    db=runtime.read_bytes(); cpbytes=json.dumps(cp_after,sort_keys=True,separators=(",",":")).encode()
    forbidden=[b"data:image/",b"Authorization:",b"Bearer ",b"Basic ",b"OPENAI_API_KEY",b"GATE2A_DRUPAL_PASSWORD",b"chain_of_thought",b"hidden_reasoning"]
    hits=[p.decode("ascii",errors="replace") for p in forbidden if p in db or p in cpbytes]
    dump(ev/"checkpoint-privacy.json", {"schema_version":1,"status":"pass" if not hits else "fail","prohibited_pattern_hits":hits,"raw_image_persisted":False,"credentials_persisted":False,"hidden_reasoning_persisted":False})
    req(not hits, f"Checkpoint privacy scan found prohibited pattern(s): {hits}")
    summary={
      "schema_version":1,"status":"pass","proof_scope":"langgraph-human-interrupt-drupal-review-resume","run_id":a.run_id,"thread_id":a.run_id,"framework":"langgraph",
      "accepted_step05_model_output_reused":True,"model_call_count":0,"automatic_model_retries":0,"semantic_retry_loop_performed":False,
      "recommendation_write_count":counters.get("submit_recommendation"),"drupal_semantic_call_count":sum(int(counters.get(k,0)) for k in ("get_image_context","submit_recommendation","get_recommendation_status")),
      "interrupt_persisted":True,"same_run_thread_resumed":True,"human_review_performed":True,"human_reviewer":"editor_dana","human_action":"edit-and-approve","review_revision_count":2,
      "post_review_status":"approved","source_article_mutation_performed":False,"automatic_publication_performed":False,"drupal_restored_to_seeded_clean":True,
      "gate2c_failure_injection_exercised":False,"runtime_db_relative_path":runtime_rel,"runtime_db_sha256":hashlib.sha256(db).hexdigest(),"checkpoint_privacy_pass":True}
    dump(ev/"summary.json",summary)
    (ev/"summary.md").write_text(
      "# Gate 2A Step 2A.06 Human Interrupt + Drupal Review Resume\n\n"
      f"- **Status:** PASS\n- **Run/thread:** `{a.run_id}`\n- **Model calls:** `0` (accepted Step 2A.05 model output reused)\n"
      "- **LangGraph interrupt:** genuinely persisted to SQLite\n- **Human decision:** `editor_dana` edited proposed alt text and approved in Drupal\n"
      "- **Resume:** same LangGraph run/thread resumed and observed the approved Drupal status\n- **Source Article mutation/publication:** none\n- **Drupal restored to seeded-clean:** yes\n- **Gate 2C failure seam:** not exercised\n",
      encoding="utf-8")
    # Scan retained text evidence for high-confidence credential/raw-image signatures.
    patterns=[re.compile(r"sk-[A-Za-z0-9_-]{20,}"),re.compile(r"data:image/",re.I),re.compile(r"Authorization\s*:",re.I),re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{16,}",re.I)]
    found=[]
    for p in sorted(ev.iterdir()):
        if not p.is_file() or p.name in {"secret-scan.log","package-files-sha256.txt"}: continue
        try: text=p.read_text(encoding="utf-8")
        except UnicodeDecodeError: continue
        if any(rx.search(text) for rx in patterns): found.append(p.name)
    req(not found, f"Retained evidence contains secret/raw-image-like material in {found}")
    (ev/"secret-scan.log").write_text("PASS: no API key, bearer credential value, authorization header, or raw image data URL retained.\n",encoding="utf-8")
    # exhaustive top-level manifest except itself
    files=sorted(p for p in ev.iterdir() if p.is_file() and p.name!="package-files-sha256.txt")
    lines=[f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}" for p in files]
    (ev/"package-files-sha256.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("[PASS] Gate 2A Step 2A.06 evidence finalization passed.")
    return 0
if __name__=="__main__": raise SystemExit(main())
