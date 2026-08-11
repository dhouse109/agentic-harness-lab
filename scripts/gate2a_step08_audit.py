#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
from typing import Any

PKG="gate-2a-step08-langgraph-fresh-batch-and-continuation-v1.0.7"
NEXT="gate-2a-step09-langgraph-evidence-claims-and-matrix-v1.0.0"
FROZEN={
 "shared/contracts/GATE05-SUBSTRATE-FREEZE.json":"99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a",
 "shared/contracts/GATE1-DRUPAL-AI-FREEZE.json":"2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd",
 "shared/contracts/GATE2A-LANGGRAPH-BATCH-CONTRACT.json":"1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b",
}
RUN_RE=re.compile(r"^evidence/results/langgraph/(langgraph-[0-9]{8}T[0-9]{6}Z-[a-z0-9]{4,12})$")
STEP07_BASE="e80d8c726df5758b1b0e5bad02b5b5e75f4e612d"
TARGET_HASH="1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728"

def req(cond: bool,msg: str)->None:
    if not cond: raise SystemExit(f"[ERROR] {msg}")
def load(p:Path)->Any:
    return json.loads(p.read_text(encoding="utf-8"))
def sha_file(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()
def validate_manifest(d:Path)->None:
    p=d/"package-files-sha256.txt"; req(p.is_file(),"result manifest missing")
    for line in p.read_text().splitlines():
        if not line.strip(): continue
        digest,name=line.split(None,1); name=name.strip()
        q=d/name
        req(q.is_file(),f"manifest file missing: {name}")
        req(sha_file(q)==digest,f"manifest checksum differs: {name}")
def schema_validate(repo:Path, schema:str, value:Any,label:str)->None:
    py=repo/"crewai/.venv/bin/python"; helper=repo/"scripts/gate2a_step07_schema_validate.py"
    proc=subprocess.run([str(py),str(helper),"--repo",str(repo),"--schema",schema,"--label",label],
                        input=json.dumps(value),text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    req(proc.returncode==0,proc.stdout.strip() or f"{label} schema validation failed")
def safety_scan(d:Path)->None:
    secret=re.compile(r"sk-[A-Za-z0-9_-]{20,}|Authorization\s*:\s*(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{16,}|data:image/[^;\s]+;base64,[A-Za-z0-9+/=]{64,}",re.I)
    for p in d.iterdir():
        if not p.is_file(): continue
        try: text=p.read_text(encoding="utf-8")
        except UnicodeDecodeError: continue
        req(secret.search(text) is None,f"concrete credential/raw-image payload in {p.name}")

def validate_batch_runner_patch(repo:Path)->None:
    rel="langchain/agentic_harness_langgraph/batch_runner.py"
    source=(repo/rel).read_text(encoding="utf-8")
    old='        if path.is_file() and path != sqlite_path:\n            evidence_bytes += path.read_bytes()'
    new='    privacy_report_names = {\n        "checkpoint-privacy-before-continuation.json",\n        "checkpoint-privacy-after-continuation.json",\n    }\n    for path in evidence.iterdir():\n        if path.is_file() and path != sqlite_path and path.name not in privacy_report_names:\n            evidence_bytes += path.read_bytes()'
    req(old not in source,"obsolete privacy evidence scan remains in batch_runner.py")
    req(source.count(new)==1,"reviewed Step 2A.08 privacy self-report exclusion patch missing or duplicated")
    proc=subprocess.run(["git","-C",str(repo),"diff","--unified=0",STEP07_BASE,"--",rel],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    req(proc.returncode==0,"unable to inspect batch_runner.py repair diff")
    changed=[]
    for line in proc.stdout.splitlines():
        if line.startswith(("+++","---","@@")): continue
        if line.startswith(("+","-")): changed.append(line)
    expected=[
      '+    privacy_report_names = {',
      '+        "checkpoint-privacy-before-continuation.json",',
      '+        "checkpoint-privacy-after-continuation.json",',
      '+    }',
      '-        if path.is_file() and path != sqlite_path:',
      '+        if path.is_file() and path != sqlite_path and path.name not in privacy_report_names:',
    ]
    req(changed==expected,f"batch_runner.py repair diff differs: {changed!r}")

def docs(repo:Path,state:str,run_rel:str|None)->None:
    files=[repo/"AGENTS.md",repo/"PLAN.md",repo/"README.md",repo/"docs/CURRENT-STATUS.md"]
    texts={str(p):p.read_text() for p in files}
    for name,t in texts.items():
        req("Step 2A.07" in t and "complete" in t,f"{name}: Step 2A.07 completion missing")
        req(PKG in t,f"{name}: Step 2A.08 package marker missing")
        req(NEXT in t,f"{name}: Step 2A.09 next-package marker missing")
    if state=="active":
        req("**Step 2A.08:** active" in texts[str(repo/"AGENTS.md")],"AGENTS Step 2A.08 active marker missing")
        req("- **Step 2A.08:** active" in texts[str(repo/"README.md")],"README Step 2A.08 active marker missing")
        req("- **Step 2A.08:** active" in texts[str(repo/"docs/CURRENT-STATUS.md")],"CURRENT Step 2A.08 active marker missing")
        req("**Active Step 2A.08 package:**" in texts[str(repo/"PLAN.md")],"PLAN Step 2A.08 active package marker missing")
    else:
        req(run_rel is not None,"complete audit requires accepted run")
        for name,t in texts.items():
            req(run_rel in t,f"{name}: accepted Step 2A.08 run missing")
        req("**Step 2A.08:** complete" in texts[str(repo/"AGENTS.md")],"AGENTS Step 2A.08 complete marker missing")
        req("- **Step 2A.08:** complete" in texts[str(repo/"README.md")],"README Step 2A.08 complete marker missing")
        req("- **Step 2A.08:** complete" in texts[str(repo/"docs/CURRENT-STATUS.md")],"CURRENT Step 2A.08 complete marker missing")
        req("- [x] Step 2A.08 — LangGraph fresh batch and continuation" in texts[str(repo/"PLAN.md")],"PLAN Step 2A.08 checkbox missing")
def static(repo:Path,state:str,run_rel:str|None)->None:
    docs(repo,state,run_rel)
    for rel,want in FROZEN.items():
        req(sha_file(repo/rel)==want,f"frozen hash differs: {rel}")
    latest7=(repo/"evidence/gates/gate-2a/batch-runner/GATE2A-STEP07-LATEST.txt")
    req(latest7.is_file(),"Step 2A.07 accepted pointer missing")
    req(latest7.read_text().strip()=="evidence/gates/gate-2a/batch-runner/gate2a-step07-20260810T185629Z-00272cd1","Step 2A.07 accepted pointer differs")
    validate_batch_runner_patch(repo)
    critical=[
      "langchain/agentic_harness_langgraph/state.py",
      "langchain/agentic_harness_langgraph/tools.py",
      "langchain/agentic_harness_langgraph/vertical_slice.py",
      "scripts/gate2a_step07_schema_validate.py",
      "shared/contracts/GATE2A-LANGGRAPH-EVIDENCE-SCHEMA-MAP.json",
    ]
    for rel in critical:
        proc=subprocess.run(["git","-C",str(repo),"diff","--quiet",STEP07_BASE,"--",rel])
        req(proc.returncode==0,f"merged Step 2A.07 source changed: {rel}")
def midpoint(repo:Path,run_rel:str)->None:
    m=RUN_RE.fullmatch(run_rel); req(m is not None,"midpoint run path invalid")
    run_id=m.group(1); d=repo/run_rel
    req(d.is_dir(),"midpoint result directory missing")
    counters=load(d/"call-counters.json")
    expected={
      "model_invocations_attempted":6,"model_invocations_succeeded":6,
      "automatic_model_retries_configured":0,"semantic_retry_loop_performed":False,
      "find_images_needing_review":1,"get_image_context":18,
      "submit_recommendation":6,"get_recommendation_status":6,
    }
    req(counters==expected,f"midpoint counters differ: {counters!r}")
    state=load(d/"run.json"); chk=load(d/"checkpoint-before-continuation.json")
    req(state==chk,"midpoint run.json/checkpoint differ")
    req(state.get("run_id")==run_id and state.get("thread_id")==run_id,"midpoint run/thread differs")
    req(state.get("status")=="interrupted" and state.get("next_target_index")==6,"midpoint lifecycle differs")
    req(state.get("continuation_boundary_reached") is True,"continuation boundary not reached")
    req(state.get("gate2c_failure_injection_fired") is False,"Gate2C failure flag set")
    req([x.get("sequence") for x in state.get("completed_target_identities",[])]==list(range(1,7)),"midpoint completed-target sequence differs")
    req(len(state.get("recommendation_ids",[]))==6 and len(state.get("validation_results",[]))==6,"midpoint checkpoint collection counts differ")
    schema_validate(repo,"langgraph-run-state.schema.json",state,"Step08 midpoint run-state")
    targets=load(d/"targets.json")
    req(targets.get("target_sequence_sha256")==TARGET_HASH,"midpoint target hash differs")
    req([x.get("sequence") for x in targets.get("targets",[])]==list(range(1,13)),"midpoint frozen target order differs")
    schema_validate(repo,"langgraph-batch-target-sequence.schema.json",targets,"Step08 midpoint targets")
    priv=load(d/"checkpoint-privacy-before-continuation.json")
    req(priv.get("status")=="pass","midpoint privacy proof failed")
    for key in ("raw_image_or_data_url_persisted","article_body_persisted","credential_persisted","hidden_reasoning_persisted"):
        req(priv.get(key) is False,f"midpoint privacy flag set: {key}")
    for filename,key in [("model-outputs.json","outputs"),("recommendations.json","recommendations"),
                         ("validation.json","results"),("submissions.json","submissions")]:
        items=load(d/filename)[key]
        req(len(items)==6 and [x.get("sequence") for x in items]==list(range(1,7)),f"{filename} midpoint sequence differs")
    submissions=load(d/"submissions.json")["submissions"]
    statuses=load(d/"statuses.json")["observations"]
    req(len(statuses)==6 and all(x.get("status")=="pending" for x in statuses),"midpoint statuses differ")
    submission_ids=[x.get("uuid") for x in submissions]
    state_ids=[x.get("uuid") for x in state.get("recommendation_ids",[])]
    status_ids=[x.get("recommendation_uuid") for x in statuses]
    req(len(set(submission_ids))==6,"midpoint submission UUIDs contain duplicates")
    req(submission_ids==state_ids==status_ids,"midpoint submission/status/checkpoint identities differ")
    ce=load(d/"continuation-event.json")
    req(ce.get("run_id")==run_id and ce.get("thread_id")==run_id,"continuation event run/thread differs")
    req(ce.get("completed_before_stop")==list(range(1,7)) and ce.get("resume_at_sequence")==7,"continuation event boundary differs")
    req(ce.get("controlled_stop") is True and ce.get("gate2c_failure_injection") is False and int(ce.get("interrupt_count",0))>0,"continuation event semantics differ")
    events=(d/"events.jsonl").read_text(encoding="utf-8").splitlines()
    req(bool(events),"midpoint event stream empty")
    for idx,line in enumerate(events,1):
        e=json.loads(line); req(e.get("event_index")==idx,f"midpoint event index differs at {idx}")
        schema_validate(repo,"langgraph-batch-event.schema.json",e,f"Step08 midpoint event {idx}")
    req(not (d/"human-review.json").exists(),"human-review.json must not be fabricated by Step 2A.08")
    req(not (d/"summary.json").exists(),"summary.json must not exist at midpoint")
    req(not (d/"recovery.json").exists(),"recovery.json must not exist at midpoint")
    safety_scan(d)
def _completed_common(repo:Path,run_rel:str)->tuple[str,Path,dict[str,Any],dict[str,Any],Path]:
    m=RUN_RE.fullmatch(run_rel); req(m is not None,"candidate run path invalid")
    run_id=m.group(1); d=repo/run_rel
    req(d.is_dir(),"candidate result directory missing")
    validate_manifest(d)
    counters=load(d/"call-counters.json")
    expected={
      "model_invocations_attempted":12,"model_invocations_succeeded":12,
      "automatic_model_retries_configured":0,"semantic_retry_loop_performed":False,
      "find_images_needing_review":1,"get_image_context":36,
      "submit_recommendation":12,"get_recommendation_status":12,
    }
    req(counters==expected,f"candidate counters differ: {counters!r}")
    state=load(d/"run.json")
    before=load(d/"checkpoint-before-continuation.json")
    after=load(d/"checkpoint-after-continuation.json")
    req(state==after,"candidate run.json differs from completed checkpoint")
    req(before.get("run_id")==run_id and before.get("thread_id")==run_id,"candidate midpoint run/thread differs")
    req(before.get("status")=="interrupted" and before.get("next_target_index")==6,"candidate midpoint lifecycle differs")
    req([x.get("sequence") for x in before.get("completed_target_identities",[])]==list(range(1,7)),"candidate midpoint completed sequence differs")
    schema_validate(repo,"langgraph-run-state.schema.json",before,"Step08 retained midpoint run-state")
    req(state.get("run_id")==run_id and state.get("thread_id")==run_id,"candidate run/thread differs")
    req(state.get("status")=="completed" and state.get("next_target_index")==12,"candidate lifecycle differs")
    req([x.get("sequence") for x in state.get("completed_target_identities",[])]==list(range(1,13)),"completed sequence differs")
    req(state.get("recommendation_ids",[])[:6]==before.get("recommendation_ids",[]),"first-six recommendation identities changed across continuation")
    all_ids=[x.get("uuid") for x in state.get("recommendation_ids",[])]
    req(len(all_ids)==12 and len(set(all_ids))==12,"candidate recommendation identities contain duplicates")
    req(state.get("gate2c_failure_injection_fired") is False,"Gate2C failure flag set")
    schema_validate(repo,"langgraph-run-state.schema.json",state,"Step08 completed run-state")
    summary=load(d/"summary.json")
    req(summary.get("status")=="pass" and summary.get("completed_count")==12 and summary.get("duplicate_count")==0,"summary differs")
    req(summary.get("human_review_completed") is False and summary.get("failure_seam_observed") is False,"summary crosses frozen boundary")
    recovery=load(d/"recovery.json")
    req(recovery.get("completed_before_stop")==list(range(1,7)),"recovery first half differs")
    req(recovery.get("completed_after_resume")==list(range(7,13)),"recovery second half differs")
    req(recovery.get("resume_at_sequence")==7 and recovery.get("duplicate_count")==0,"recovery resume/duplicate differs")
    req(recovery.get("gate2c_failure_injection_fired") is False,"recovery mislabels Gate2C failure")
    req(not (d/"human-review.json").exists(),"human-review.json must not be fabricated by Step 2A.08")
    schemas=[
      ("targets.json","langgraph-batch-target-sequence.schema.json"),
      ("model-outputs.json","langgraph-batch-model-outputs.schema.json"),
      ("recommendations.json","langgraph-batch-recommendations.schema.json"),
      ("validation.json","langgraph-batch-validation.schema.json"),
      ("submissions.json","langgraph-batch-submissions.schema.json"),
      ("statuses.json","langgraph-batch-statuses.schema.json"),
      ("tool-traces.json","langgraph-batch-tool-traces.schema.json"),
      ("recovery.json","langgraph-batch-recovery.schema.json"),
      ("summary.json","langgraph-batch-summary.schema.json"),
    ]
    for filename,schema in schemas: schema_validate(repo,schema,load(d/filename),f"Step08 {filename}")
    gate=repo/"evidence/gates/gate-2a/fresh-batch"/run_id
    req(gate.is_dir(),"Step08 wrapper evidence missing")
    validate_manifest(gate)
    safety_scan(d); safety_scan(gate)
    return run_id,d,state,before,gate

def _require_original_privacy_self_match(d:Path)->None:
    before_priv=load(d/"checkpoint-privacy-before-continuation.json")
    req(before_priv.get("status")=="pass","midpoint privacy proof failed")
    req(before_priv.get("generic_prohibited_pattern_hits")==[],"midpoint generic privacy hits differ")
    req(before_priv.get("exact_ephemeral_value_hits")==[],"midpoint exact privacy hits differ")
    for key in ("raw_image_or_data_url_persisted","article_body_persisted","credential_persisted","hidden_reasoning_persisted"):
        req(before_priv.get(key) is False,f"midpoint privacy flag set: {key}")
    final_priv=load(d/"checkpoint-privacy-after-continuation.json")
    req(final_priv.get("status")=="fail","original final privacy report is not retained as failed")
    req(final_priv.get("generic_prohibited_pattern_hits")==["hidden_reasoning"],"original final privacy failure differs from reviewed self-match")
    req(final_priv.get("exact_ephemeral_value_hits")==[],"original final privacy exact-hit set differs")
    req(final_priv.get("raw_image_or_data_url_persisted") is False,"original final privacy unexpectedly found raw image")
    req(final_priv.get("article_body_persisted") is False,"original final privacy unexpectedly found article body")
    req(final_priv.get("credential_persisted") is False,"original final privacy unexpectedly found credential")
    req(final_priv.get("hidden_reasoning_persisted") is True,"original final privacy self-match flag missing")

def _raw_generic_hits_excluding_privacy_reports(d:Path)->list[tuple[str,str]]:
    exclude={"checkpoint-privacy-before-continuation.json","checkpoint-privacy-after-continuation.json","checkpoint-privacy-after-continuation-salvage.json"}
    patterns=[b"data:image/",b"Authorization:",b"Bearer ",b"Basic ",b"OPENAI_API_KEY",b"GATE2A_DRUPAL_PASSWORD",b"hidden_reasoning",b"chain_of_thought"]
    hits=[]
    for p in sorted(d.iterdir()):
        if not p.is_file() or p.name in exclude: continue
        data=p.read_bytes()
        for pat in patterns:
            if pat in data: hits.append((p.name,pat.decode("ascii")))
    return hits

def salvage_source(repo:Path,run_rel:str)->None:
    run_id,d,state,before,gate=_completed_common(repo,run_rel)
    _require_original_privacy_self_match(d)
    req(_raw_generic_hits_excluding_privacy_reports(d)==[],"prohibited generic pattern exists outside self-reporting privacy artifacts")
    req(not (d/"checkpoint-privacy-after-continuation-salvage.json").exists(),"salvage privacy proof already exists")
    req(not (gate/"salvage-wrapper-summary.json").exists(),"salvage wrapper summary already exists")
    failed=repo/"evidence/gates/gate-2a/fresh-batch/GATE2A-STEP08-FAILED-RUNS.txt"
    req(failed.is_file() and run_rel in failed.read_text().splitlines(),"reviewed failed-run registration missing")
    failure=load(gate/"failure.json")
    req(failure.get("status")=="failed" and failure.get("phase")=="resume","reviewed failure lineage differs")
    req(failure.get("message")=="Live resume core exited nonzero.","reviewed failure message differs")
    req(failure.get("restore_attempted") is True and failure.get("restore_verified") is True and failure.get("snapshot_cleaned") is True,"failure recovery was not fully verified")
    req(failure.get("runtime_db_retained") is False and failure.get("recovery_control_retained") is False,"failure runtime/control disposal differs")
    req(re.fullmatch(r"[0-9a-f]{64}",str(failure.get("runtime_db_sha256_before_disposal",""))) is not None,"failure runtime DB digest missing")
    req(not (repo/f"langchain/.gate2a-runtime/{run_id}.sqlite").exists(),"failed runtime SQLite unexpectedly retained")
    req(not (repo/f"langchain/.gate2a-runtime/{run_id}.step08-control.json").exists(),"failed runtime control unexpectedly retained")
    req(not (repo/"evidence/gates/gate-2a/fresh-batch/GATE2A-STEP08-CANDIDATE.txt").exists(),"candidate pointer already exists")
    req(not (repo/"evidence/gates/gate-2a/fresh-batch/GATE2A-STEP08-LATEST.txt").exists(),"accepted pointer already exists")

def candidate(repo:Path,run_rel:str)->None:
    run_id,d,state,before,gate=_completed_common(repo,run_rel)
    salvage=d/"checkpoint-privacy-after-continuation-salvage.json"
    if salvage.exists():
        _require_original_privacy_self_match(d)
        req(_raw_generic_hits_excluding_privacy_reports(d)==[],"candidate contains prohibited generic pattern outside privacy reports")
        sv=load(salvage)
        req(sv.get("schema_version")==1 and sv.get("status")=="pass","salvage privacy disposition failed")
        req(sv.get("run_id")==run_id and sv.get("diagnosis")=="privacy-report-self-match","salvage privacy identity/diagnosis differs")
        req(sv.get("original_failed_privacy_report_preserved") is True,"original failed privacy report was not preserved")
        req(sv.get("actual_prohibited_content_found") is False,"salvage proof reports actual prohibited content")
        req(sv.get("raw_evidence_scan_excluding_privacy_reports_passed") is True,"salvage raw-evidence scan did not pass")
        req(sv.get("original_exact_ephemeral_value_hits_empty") is True,"salvage exact-probe result differs")
        req(sv.get("runtime_db_rescan_performed") is False and sv.get("runtime_db_disposed_by_verified_recovery") is True,"salvage DB disposition differs")
        failed=repo/"evidence/gates/gate-2a/fresh-batch/GATE2A-STEP08-FAILED-RUNS.txt"
        req(run_rel in failed.read_text().splitlines(),"salvaged candidate must retain failed-run history")
        failure=load(gate/"failure.json")
        sw=load(gate/"salvage-wrapper-summary.json")
        req(not (gate/"wrapper-summary.json").exists(),"salvaged run must not fabricate original wrapper-summary.json")
        req(sw.get("status")=="pass" and sw.get("salvaged_candidate") is True,"salvage wrapper summary differs")
        req(sw.get("run_id")==run_id and sw.get("result_path")==run_rel,"salvage wrapper identity differs")
        req(sw.get("original_live_execution_status")=="failed-after-completion-privacy-check","salvage wrapper original status differs")
        req(sw.get("restore_attempted") is True and sw.get("restore_verified") is True and sw.get("snapshot_cleaned") is True,"salvage restore proof differs")
        req(sw.get("before_state_sha256")==sw.get("after_restore_state_sha256"),"salvage Drupal restore hash differs")
        req(sw.get("runtime_db_retained") is False and sw.get("runtime_db_sha256_before_disposal")==failure.get("runtime_db_sha256_before_disposal"),"salvage runtime DB lineage differs")
        mid=load(gate/"midpoint-summary.json")
        req(mid.get("status")=="pass" and mid.get("run_id")==run_id,"salvage midpoint wrapper evidence differs")
        req(mid.get("before_state_sha256")==sw.get("before_state_sha256"),"salvage before-state hash differs")
        req(mid.get("midpoint_state_sha256")==sw.get("midpoint_state_sha256"),"salvage midpoint-state hash differs")
    else:
        for p in (d/"checkpoint-privacy-before-continuation.json",d/"checkpoint-privacy-after-continuation.json"):
            v=load(p); req(v.get("status")=="pass",f"{p.name} privacy proof failed")
            req(not v.get("raw_image_or_data_url_persisted"),f"{p.name} raw image persisted")
            req(not v.get("article_body_persisted"),f"{p.name} article body persisted")
            req(not v.get("credential_persisted"),f"{p.name} credential persisted")
        w=load(gate/"wrapper-summary.json")
        req(w.get("status")=="pass" and w.get("snapshot_restored") is True,"wrapper restore summary differs")
        req(w.get("restore_attempted") is True and w.get("restore_verified") is True and w.get("snapshot_cleaned") is True,"wrapper verified-restore lifecycle differs")
        req(w.get("before_state_sha256")==w.get("after_restore_state_sha256"),"Drupal post-restore state differs from pre-run state")
        mid=load(gate/"midpoint-summary.json")
        req(mid.get("status")=="pass" and mid.get("run_id")==run_id and mid.get("result_path")==run_rel,"wrapper midpoint summary identity differs")
        req(mid.get("completed_before_stop")==list(range(1,7)) and mid.get("resume_at_sequence")==7 and mid.get("model_calls_succeeded")==6,"wrapper midpoint summary boundary differs")
        req(mid.get("before_state_sha256")==w.get("before_state_sha256") and mid.get("midpoint_state_sha256")==w.get("midpoint_state_sha256"),"wrapper midpoint hashes differ from candidate wrapper summary")
        req(w.get("midpoint_state_unchanged_before_resume") is True,"Drupal midpoint state changed before resume")
        req(w.get("runtime_db_retained") is False and re.fullmatch(r"[0-9a-f]{64}",str(w.get("runtime_db_sha256_before_disposal",""))),"runtime DB disposal proof differs")

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo",required=True)
    ap.add_argument("--document-state",choices=("active","complete"),required=True)
    ap.add_argument("--run-dir")
    ap.add_argument("--phase",choices=("midpoint","salvage-source","candidate"))
    a=ap.parse_args()
    repo=Path(a.repo).resolve()
    run_rel=a.run_dir
    static(repo,a.document_state,run_rel if a.document_state=="complete" else None)
    if a.phase:
        req(bool(run_rel),"--run-dir required with --phase")
        midpoint(repo,run_rel) if a.phase=="midpoint" else salvage_source(repo,run_rel) if a.phase=="salvage-source" else candidate(repo,run_rel)
    print("[PASS] Gate 2A Step 2A.08 audit passed.")
    if run_rel: print(f"[PASS] Evidence: {run_rel}")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
