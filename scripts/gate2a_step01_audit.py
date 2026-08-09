#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path

EXPECTED_BASE='d87c66a8a342109253e906e7e29ce2c15f7ddbef'
EXPECTED_GATE1_SHA='2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd'
EXPECTED_TARGET_SHA='1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728'
CONTRACT='shared/contracts/GATE2A-LANGGRAPH-BATCH-CONTRACT.json'
CONTRACT_SHA='shared/contracts/GATE2A-LANGGRAPH-BATCH-CONTRACT.sha256'
FROZEN_INPUTS={
 'shared/schemas/target.schema.json':'2bcb867c3b58a5f4bb20b29274434c153ad043e8c0dba3ce3d1e496a44a32469',
 'shared/schemas/image-context.schema.json':'b2e27b533551759d181c58330ebedcb26ca92c1a596dbb4aaf48a48422dffaee',
 'shared/schemas/recommendation.schema.json':'7b1cf9800d5c8d8df4cd0a718c721dd43013afa256f7814a365d4696e2cfe2bd',
 'shared/schemas/tool-result.schema.json':'ce04e938eb4e34e861c000b86fffeed4adc5e5c66167c52ebf5380b8cd3cd91b',
 'shared/schemas/run-state.schema.json':'ee5face3d81138cfa2d5de2e03d8fb2aded881743e2e0334129342bf95f3010b',
}
class AuditError(RuntimeError): pass

def sha(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path:Path): return json.loads(path.read_text(encoding='utf-8'))
def need(cond,msg):
    if not cond: raise AuditError(msg)

def canonical_head_sha(repo:Path, rel:str)->str:
    # Frozen tracked inputs are compared to the canonical bytes committed in HEAD.
    # A clean checkout may legitimately have CRLF/LF or other Git worktree
    # normalization while still representing the exact same tracked content.
    diff=subprocess.run(['git','-C',str(repo),'diff','--quiet','HEAD','--',rel])
    need(diff.returncode==0,f'Frozen shared input has tracked content drift: {rel}')
    proc=subprocess.run(['git','-C',str(repo),'show',f'HEAD:{rel}'],check=False,capture_output=True)
    need(proc.returncode==0,f'Frozen shared input missing from HEAD: {rel}')
    return hashlib.sha256(proc.stdout).hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',required=True); ap.add_argument('--document-state',choices=['active','complete'],required=True); ap.add_argument('--json',action='store_true'); a=ap.parse_args()
    repo=Path(a.repo).resolve()
    c=load(repo/CONTRACT)
    expected_line=(repo/CONTRACT_SHA).read_text(encoding='utf-8').strip().split()[0]
    need(sha(repo/CONTRACT)==expected_line,'Gate 2A contract digest mismatch')
    need(c['predecessor']['commit']==EXPECTED_BASE,'Unexpected predecessor commit in contract')
    need(c['predecessor']['gate1_freeze_sha256']==EXPECTED_GATE1_SHA,'Unexpected Gate 1 freeze in contract')
    gate1=repo/'shared/contracts/GATE1-DRUPAL-AI-FREEZE.json'
    need(sha(gate1)==EXPECTED_GATE1_SHA,'Gate 1 freeze manifest changed')
    gate1_obj=load(gate1)
    need(gate1_obj['status']=='certified','Gate 1 is not certified')
    need(gate1_obj['target_sequence_sha256']==EXPECTED_TARGET_SHA,'Target sequence drift')
    for rel,h in FROZEN_INPUTS.items(): need(canonical_head_sha(repo,rel)==h,f'Frozen shared input changed: {rel}')
    f=c['frozen_constants']
    expected={'provider':'OpenAI','model':'gpt-4.1-mini-2025-04-14','temperature':0.0,'source_framework':'langgraph','validator_version':'gate05-validator-1.0.0','review_destination':'alt_text_suggestion','reviewer':'editor_dana','source_article_mutation':'prohibited','automatic_publication':'prohibited','python':'3.12.13','langchain':'1.3.14','langgraph':'1.2.10','langgraph_sqlite_checkpointer':'3.1.1'}
    for k,v in expected.items(): need(f.get(k)==v,f'Frozen constant mismatch: {k}')
    need(c['state_ownership']['owner']=='langgraph','LangGraph does not own state')
    need(c['state_ownership']['checkpoint_backend']=='sqlite','SQLite checkpointer not frozen')
    need(c['state_ownership']['runtime_storage_location']=='deferred_to_step_2A_02','Runtime location not deferred to Step 2A.02')
    need(c['human_review_boundary']['second_approval_system_prohibited'] is True,'Second approval system is not prohibited')
    need(c['model_call_policy']['step_2A_08_is_certification_candidate'] is True,'2A.08 certification-candidate policy missing')
    need(c['model_call_policy']['second_12_call_certification_batch_required_by_default'] is False,'Second certification batch incorrectly required')
    need(c['acceptance']['next_package']=='gate-2a-step02-langgraph-runtime-and-checkpoint-probe-v1.0.0','Wrong next package')
    # version register textual reconciliation
    versions=(repo/'VERSIONS.md').read_text(encoding='utf-8')
    for token in ['3.12.13','LangChain | 1.3.14','LangGraph | 1.2.10','LangGraph SQLite checkpointer | 3.1.1','gpt-4.1-mini-2025-04-14']:
        need(token in versions,f'VERSIONS.md missing pinned token: {token}')
    spec=(repo/'EXPERIMENT_SPEC.md').read_text(encoding='utf-8')
    for token in ['20 deterministic seeded Article nodes','12 deterministic target image-field usages','after target **6**','before target 7 begins']:
        need(token in spec,f'EXPERIMENT_SPEC.md missing contract token: {token}')
    # schema meta-validation + examples
    try:
        import jsonschema
        from referencing import Registry, Resource
    except Exception as e: raise AuditError(f'jsonschema tooling unavailable: {e}')
    schema_dir=repo/'shared/schemas'; reg=Registry()
    for p in schema_dir.glob('*.schema.json'):
        s=load(p)
        if '$id' in s: reg=reg.with_resource(s['$id'], Resource.from_contents(s))
    for name in ['langgraph-run-state.schema.json','langgraph-model-output.schema.json']:
        s=load(schema_dir/name); jsonschema.Draft202012Validator.check_schema(s)
    mo=jsonschema.Draft202012Validator(load(schema_dir/'langgraph-model-output.schema.json'), registry=reg)
    need(mo.is_valid({'proposed_alt_text':'A descriptive alt text'}),'Positive model-output schema example failed')
    need(not mo.is_valid({'proposed_alt_text':''}),'Empty model-output negative control passed')
    need(not mo.is_valid({'proposed_alt_text':'ok','reasoning':'secret'}),'Additional-field model-output negative control passed')
    target={'schema_version':1,'sequence':1,'node_uuid':'00000000-0000-4000-8000-000000000001','revision_id':101,'field_name':'field_image','delta':0,'file_uuid':'10000000-0000-4000-8000-000000000001','target_state':'missing','existing_alt':None}
    state={'schema_version':1,'run_id':'langgraph-20260809T190000Z-a1b2','framework_origin':'langgraph','thread_id':'langgraph-20260809T190000Z-a1b2','checkpoint_backend':'sqlite','checkpoint_id':None,'checkpoint_namespace':None,'status':'running','target_sequence_hash':'sha256:'+EXPECTED_TARGET_SHA,'next_target_index':0,'completed_target_identities':[],'recommendation_ids':[],'validation_results':[],'started_at':'2026-08-09T19:00:00Z','updated_at':'2026-08-09T19:00:00Z','completed_at':None,'interrupted_at':None,'resumed_at':None,'continuation_boundary_armed':False,'continuation_boundary_reached':False,'gate2c_failure_injection_fired':False,'prompt_version':'langgraph-alt-text-v1.0.0','model_id':'gpt-4.1-mini-2025-04-14'}
    rs=jsonschema.Draft202012Validator(load(schema_dir/'langgraph-run-state.schema.json'), registry=reg)
    need(rs.is_valid(state),'Positive LangGraph run-state schema example failed')
    bad=dict(state); bad['framework_origin']='drupal_ai'; need(not rs.is_valid(bad),'Wrong-origin run-state negative control passed')
    # docs and no stale package root
    docs={rel:(repo/rel).read_text(encoding='utf-8') for rel in ['AGENTS.md','README.md','PLAN.md','docs/CURRENT-STATUS.md']}
    for rel,t in docs.items(): need('~/projects/agentic-harness-lab-packages/' not in t,f'Old package root remains in {rel}')
    if a.document_state=='active':
        for rel in ['AGENTS.md','README.md','PLAN.md','docs/CURRENT-STATUS.md']: need('gate-2a-step01-langgraph-contract-and-evidence-plan-v1.0.3' in docs[rel],f'Active 2A.01 marker missing in {rel}')
    else:
        for rel in ['AGENTS.md','README.md','PLAN.md','docs/CURRENT-STATUS.md']:
            need('gate-2a-step02-langgraph-runtime-and-checkpoint-probe-v1.0.0' in docs[rel],f'Next 2A.02 marker missing in {rel}')
        need('- [x] Step 2A.01 — LangGraph contract and evidence plan' in docs['PLAN.md'],'PLAN.md does not mark 2A.01 complete')
    # Gate 1 protected paths must not be modified in working tree
    changed=subprocess.run(['git','-C',str(repo),'diff','--name-only','HEAD'],check=True,capture_output=True,text=True).stdout.splitlines()
    protected=[p for p in changed if p.startswith('evidence/gates/gate-1/') or p.startswith('shared/contracts/GATE1-') or p.startswith('scripts/run-gate1-')]
    need(not protected,f'Protected Gate 1 path modified: {protected}')
    result={'status':'pass','contract_sha256':sha(repo/CONTRACT),'document_state':a.document_state,'gate1_freeze_sha256':EXPECTED_GATE1_SHA,'target_sequence_sha256':EXPECTED_TARGET_SHA,'new_schemas':['langgraph-run-state.schema.json','langgraph-model-output.schema.json'],'model_call_performed':False,'drupal_state_mutated':False,'gate1_protected_path_changes':[],'next_package':'gate-2a-step02-langgraph-runtime-and-checkpoint-probe-v1.0.0'}
    print(json.dumps(result,indent=2,sort_keys=True) if a.json else '[PASS] Gate 2A Step 2A.01 static audit passed.')
if __name__=='__main__':
    try: main()
    except AuditError as e:
        raise SystemExit(f'[ERROR] {e}')
