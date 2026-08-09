#!/usr/bin/env python3
"""Generate Gate 1 freeze/handoff and advance repository status after passing Step 1.07 evidence."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any

GATE05_SHA="99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a"
CONTRACT_SHA="360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6"
TARGET_SHA="1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728"
SOURCE_FULL="877cd888fa41eb660b3e3cc0461bee04c0b92bef7e8f2f63fc56d9ec77adde32"
SOURCE_REDUCED="f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17"
STEP06_RUN="gate1-step06-20260808T231216Z-2188911"

def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p:Path)->Any:return json.loads(p.read_text(encoding="utf-8"))
def write(p:Path,text:str)->None:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding="utf-8")
def replace_once(text:str,before:str,after:str,label:str)->str:
    if before not in text: raise SystemExit(f"[ERROR] Finalizer anchor missing: {label}")
    return text.replace(before,after,1)

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--repo",type=Path,required=True);ap.add_argument("--gate",type=Path,required=True);ap.add_argument("--result",type=Path,required=True);args=ap.parse_args()
    repo=args.repo.resolve();gate=args.gate.resolve();result=args.result.resolve();summary=load(result/"summary.json")
    if summary.get("status")!="pass": raise SystemExit("[ERROR] Cannot finalize a non-passing certification")
    run_id=summary["run_id"]
    freeze={
      "schema_version":1,"status":"certified","framework":"drupal_ai","certification_run_id":gate.name,"batch_run_id":run_id,
      "provider":"OpenAI","model":"gpt-4.1-mini-2025-04-14","temperature":0.0,"target_count":12,"target_sequence_sha256":TARGET_SHA,
      "gate05_freeze_sha256":GATE05_SHA,"gate1_batch_contract_sha256":CONTRACT_SHA,"validator_version":"gate05-validator-1.0.0",
      "review_destination":"alt_text_suggestion","source_framework":"drupal_ai","source_article_mutation":"prohibited","automatic_publication":"prohibited",
      "source_article_full_projection_sha256":SOURCE_FULL,"source_article_reduced_projection_sha256":SOURCE_REDUCED,
      "recommendation_count":12,"pending_count_before_restore":12,"duplicate_count_on_replay":0,"framework_state_complete":True,
      "review_lineage_reference":{"step06_run_id":STEP06_RUN,"review_decisions":3,"review_revisions":4},
      "lifecycle_seam":{"after_sequence":6,"before_sequence":7,"present":True,"shared_process_failure_recovery_claimed":False},
      "non_claims":["production readiness","accessibility quality of every generated alt text","autonomous publishing safety","shared injected-failure recovery","superiority over LangGraph or CrewAI","cost/speed/token efficiency","general security beyond tested boundaries"],
    }
    freeze_path=repo/"shared/contracts/GATE1-DRUPAL-AI-FREEZE.json";write(freeze_path,json.dumps(freeze,indent=2,sort_keys=True)+"\n")
    digest=sha(freeze_path);write(repo/"shared/contracts/GATE1-DRUPAL-AI-FREEZE.sha256",f"{digest}  shared/contracts/GATE1-DRUPAL-AI-FREEZE.json\n")
    cert_doc=f"""# Gate 1 Certification — Drupal AI\n\n**Status:** PASS  \n**Certification evidence:** `{gate.relative_to(repo)}`  \n**Fresh batch run:** `{run_id}`  \n**Freeze SHA-256:** `{digest}`\n\nThe pinned Drupal AI implementation processed the frozen 12-target dataset through a real model-backed batch, created exactly 12 schema-valid and validator-approved pending recommendations through the certified shared substrate, preserved framework origin and run state, routed recommendations into Drupal revisioned human review, produced no duplicate recommendations on replay, and did not mutate source Articles. Deliberate process-failure recovery remains to be tested in the later shared comparison phase.\n\n## Evidence boundary\n\n- Fresh model-backed certification: 12 targets, 12 recommendations, zero duplicate identities on model-free replay.\n- Human review lineage: references accepted Step 1.06 evidence `{STEP06_RUN}`; it is not recreated here.\n- Source non-mutation: full projection `{SOURCE_FULL}` and reduced projection `{SOURCE_REDUCED}` restored exactly.\n- Sequence-6/7 lifecycle seam: observed as part of the existing batch implementation, not promoted into the later shared failure/recovery comparison claim.\n\n## Not proven\n\nProduction readiness, universal alt-text accessibility quality, autonomous publishing safety, shared injected-failure recovery, framework superiority, performance/cost/token efficiency, and general security beyond the tested boundary are not claimed.\n"""
    write(repo/"docs/gates/GATE-1-CERTIFICATION.md",cert_doc)
    handoff=f"""# Gate 1 → LangGraph Handoff\n\nGate 1 Drupal AI is certified at freeze digest `{digest}` using fresh batch run `{run_id}`.\n\n## Constants LangGraph must preserve\n\n- Dataset: 20 Articles / 12 frozen targets\n- Target sequence SHA-256: `{TARGET_SHA}`\n- Provider/model: OpenAI `gpt-4.1-mini-2025-04-14`, temperature `0.0`\n- Shared operations and deterministic validator remain unchanged\n- Review destination: `alt_text_suggestion`\n- Source mutation and automatic publication remain prohibited\n- Shared comparison failure point remains after target 6 and before target 7\n\n## Drupal AI evidence available for later comparison\n\n- Context assembly and image identity are retained in sanitized hashes/facts.\n- Four thin Drupal AI FunctionCall adapters delegate to the frozen shared substrate.\n- Framework-owned Drupal key/value state tracks completed targets and next index.\n- Validation and submission are lifecycle-separated.\n- Step 1.06 retains real `editor_dana` revision lineage.\n- The existing sequence-6/7 continuation is an implementation observation only; the later shared process-failure comparison is still open.\n\nDo not infer any LangGraph result from Drupal AI evidence. Build and observe the LangGraph specimen independently.\n"""
    write(repo/"docs/handoffs/GATE-1-TO-LANGGRAPH-HANDOFF.md",handoff)

    # Advance status documents. Current status/PLAN control over the stale AGENTS immediate-task footer.
    p=repo/"PLAN.md";t=p.read_text(encoding="utf-8")
    t=replace_once(t,"> Phase 0 and Gate 0.5 are complete. Gate 1 Steps 1.01 through 1.06 are complete; Step 1.07 is next.","> Phase 0, Gate 0.5, and Gate 1 are complete. Drupal AI is certified and frozen; LangGraph implementation is next.","PLAN status")
    t=replace_once(t,"**Next package:**\n\n```text\ngate-1-step07-drupal-ai-certification-and-handoff-v1.0.0\n```",f"**Completed package:**\n\n```text\ngate-1-step07-drupal-ai-certification-and-handoff-v1.0.3\n```\n\nAccepted Step 1.07 certification evidence: `{gate.relative_to(repo)}`\nAccepted Drupal AI certification batch: `{run_id}`\nAccepted Gate 1 freeze digest: `{digest}`","PLAN next package")
    t=replace_once(t,"- [ ] Step 1.07 — certification, freeze, and handoff","- [x] Step 1.07 — certification, freeze, and handoff","PLAN checklist")
    p.write_text(t,encoding="utf-8")

    for rel in ("README.md","docs/CURRENT-STATUS.md"):
        p=repo/rel;t=p.read_text(encoding="utf-8")
        t=t.replace("- **Next package:** `gate-1-step07-drupal-ai-certification-and-handoff-v1.0.0`.","- **Step 1.07:** complete; Gate 1 Drupal AI is certified and frozen.\n- **Next implementation:** LangGraph.",1)
        t=t.replace("Packages 1.01 through 1.06 are complete. The next package is\n`gate-1-step07-drupal-ai-certification-and-handoff-v1.0.0`.","Packages 1.01 through 1.07 are complete. Gate 1 Drupal AI is certified and frozen; LangGraph implementation is next.",1)
        marker="Step 1.06 reviewer-lineage recovery patch: `gate-1-step06-drupal-ai-batch-evidence-and-human-review-v1.0.4`"
        if marker in t:
            t=t.replace(marker,marker+f"\nAccepted Step 1.07 certification evidence: `{gate.relative_to(repo)}`\nAccepted Drupal AI certification batch: `{run_id}`\nAccepted Gate 1 freeze digest: `{digest}`",1)
        p.write_text(t,encoding="utf-8")

    # Replace the stale Gate 1 Step 1.01 immediate-task footer in AGENTS.md only after Gate 1 passes.
    p=repo/"AGENTS.md";t=p.read_text(encoding="utf-8")
    old="""## Immediate task boundary

The current next package is:

```text
gate-1-step01-drupal-ai-batch-contract-v1.0.0
```

Step 1.01 freezes the Gate 1 execution contract and evidence schemas. It must not call a model,
mutate Drupal state, change dependencies, recertify Gate 0.5, or begin Step 1.02.
"""
    new=f"""## Immediate task boundary

Gate 1 Drupal AI is complete and frozen at `{digest}`. The next implementation is LangGraph.

Before LangGraph work, read `docs/handoffs/GATE-1-TO-LANGGRAPH-HANDOFF.md`, the Gate 1 freeze manifest,
and the accepted Step 1.07 certification evidence. Preserve the frozen dataset, model/settings, shared
operations, validator, review destination, source-mutation rule, and later shared failure point. Do not
infer LangGraph behavior from Drupal AI evidence.
"""
    if old in t:
        t=t.replace(old,new,1)
    else:
        raise SystemExit("[ERROR] AGENTS.md stale immediate-task footer anchor changed")
    p.write_text(t,encoding="utf-8")

    # Promote only Drupal-local evidence claims to observed; official sources remain TODO, so not verified.
    p=repo/"CLAIMS_REGISTER.md";t=p.read_text(encoding="utf-8")
    old="| CLM-DR-002 | Drupal recommendation revisions can retain reviewer identity, timestamps, text edits, and status transitions as an editor-facing audit trail. | Drupal AI / Drupal substrate | TODO | Step 12 candidate evidence | hypothesis | Do not use yet. |"
    new=f"| CLM-DR-002 | Drupal recommendation revisions can retain reviewer identity, timestamps, text edits, and status transitions as an editor-facing audit trail. | Drupal AI / Drupal substrate | TODO | `evidence/gates/gate-1/batch-evidence/{STEP06_RUN}` | observed | In this pinned lab, three representative human decisions produced four retained `editor_dana` review revisions, including the recorded two-save edit-then-approve lineage. Official-source pairing is still pending. |"
    if old in t:t=t.replace(old,new,1)
    old="| CLM-DR-003 | A Drupal implementation may resume batch work from persisted entity state rather than recomputing completed items. | Drupal AI | TODO | Not run | hypothesis | Do not use yet. |"
    new=f"| CLM-DR-003 | A Drupal implementation may resume batch work from persisted entity state rather than recomputing completed items. | Drupal AI | TODO | `{gate.relative_to(repo)}` | observed | In this pinned implementation, framework-owned Drupal state preserved completion through sequence 6 and continued the same run at sequence 7 without duplicate recommendations. This is not yet the later shared process-failure recovery result. |"
    if old in t:t=t.replace(old,new,1)
    p.write_text(t,encoding="utf-8")

    p=repo/"COMPARISON_MATRIX.md";t=p.read_text(encoding="utf-8")
    replacements={
      "| Context | Drupal AI | TODO | TODO | TODO | not observed | Do not use yet |":f"| Context | Drupal AI | Drupal entity/page facts + verified image File entity passed to the pinned AI Agent task | Gate 1 certification | `{gate.relative_to(repo)}` | observed | Drupal AI assembled the permitted content/image context for the frozen 12 targets in this pinned lab. |",
      "| Tools | Drupal AI | TODO | TODO | TODO | not observed | Do not use yet |":f"| Tools | Drupal AI | Four FunctionCall adapters delegate to the certified shared Drupal services; model call itself exposes zero callable tools | Gate 1 certification | `{gate.relative_to(repo)}` | observed | Drupal AI used thin framework-native adapters around the frozen shared substrate without a private write path. |",
      "| State and memory | Drupal AI | TODO | TODO | TODO | not observed | Do not use yet |":f"| State and memory | Drupal AI | Drupal key/value collection `agentic_harness_drupal_ai.run_state` + sanitized artifacts | Gate 1 certification | `{gate.relative_to(repo)}` | observed | Framework-owned state records completed targets, recommendation identities, and the next index. |",
      "| Verification | Drupal AI | TODO | TODO | TODO | not observed | Do not use yet |":f"| Verification | Drupal AI | Strict structured output + shared deterministic validator + idempotent submit/status checks | Gate 1 certification | `{gate.relative_to(repo)}` | observed | All 12 fresh outputs passed the frozen schema/validator and model-free replay produced zero duplicate identities. |",
      "| Human review | Drupal AI | TODO | TODO | TODO | not observed | Do not use yet |":f"| Human review | Drupal AI | Revision-enabled `alt_text_suggestion` queue with real `editor_dana` decisions | Step 1.06 lineage | `evidence/gates/gate-1/batch-evidence/{STEP06_RUN}` | observed | Approve, reject, and edit-then-approve were retained as real Drupal revision lineage; generated recommendations were not auto-applied. |",
      "| Lifecycle and recovery | Drupal AI | TODO | TODO | TODO | not observed | Do not use yet |":f"| Lifecycle and recovery | Drupal AI | Persist-after-target state; controlled sequence-6/7 continuation in the same run | Gate 1 certification | `{gate.relative_to(repo)}` | observed | Same-run continuation from sequence 7 was observed without duplicate recommendations; the later shared process-failure recovery comparison remains open. |",
    }
    for old,new in replacements.items():
        if old in t:t=t.replace(old,new,1)
    t=t.replace("**Status:** empty evidence matrix — do not fill from expectations alone.","**Status:** Drupal AI Gate 1 evidence populated; LangGraph and CrewAI remain unobserved. Do not infer cross-framework conclusions.",1)
    p.write_text(t,encoding="utf-8")
    print(json.dumps({"status":"pass","freeze_sha256":digest,"batch_run_id":run_id},indent=2))
    return 0
if __name__=="__main__":raise SystemExit(main())
