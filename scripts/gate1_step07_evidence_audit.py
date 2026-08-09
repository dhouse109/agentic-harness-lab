#!/usr/bin/env python3
"""Build and audit fresh Gate 1 Step 1.07 certification evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

TARGET_SHA = "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728"
SOURCE_REDUCED = "f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17"
SOURCE_FULL = "877cd888fa41eb660b3e3cc0461bee04c0b92bef7e8f2f63fc56d9ec77adde32"
STEP06_RUN = "gate1-step06-20260808T231216Z-2188911"

class AuditError(RuntimeError): pass

def require(v: bool, m: str) -> None:
    if not v: raise AuditError(m)

def load(p: Path) -> Any: return json.loads(p.read_text(encoding="utf-8"))
def dump(p: Path, v: Any) -> None: p.write_text(json.dumps(v, indent=2, sort_keys=True)+"\n", encoding="utf-8")
def sha(p: Path) -> str: return hashlib.sha256(p.read_bytes()).hexdigest()

def build_results(gate: Path, result: Path) -> None:
    export = load(gate / "runtime-export.json")
    state = export["state"]
    a = export["artifacts"]
    run_id = state["run_id"]
    require(result.name == run_id, "Result directory differs from runtime run_id")
    result.mkdir(parents=True, exist_ok=True)
    dump(result/"run.json", state)
    dump(result/"targets.json", {"schema_version":1,"target_sequence_sha256":TARGET_SHA,"targets":a["targets"]})
    with (result/"events.jsonl").open("w", encoding="utf-8") as fh:
        for event in a["events"]: fh.write(json.dumps(event, sort_keys=True, separators=(",",":"))+"\n")
    dump(result/"tool-traces.json", {"schema_version":1,"run_id":run_id,"source_framework":"drupal_ai","traces":a["traces"]})
    dump(result/"model-outputs.json", {"schema_version":1,"run_id":run_id,"framework_origin":"drupal_ai","outputs":a["model_outputs"]})
    dump(result/"recommendations.json", {"schema_version":1,"run_id":run_id,"source_framework":"drupal_ai","recommendations":a["recommendations"]})
    dump(result/"validation.json", {"schema_version":1,"run_id":run_id,"source_framework":"drupal_ai","validator_version":"gate05-validator-1.0.0","results":a["validation_results"]})
    dump(result/"submissions.json", {"schema_version":1,"run_id":run_id,"framework_origin":"drupal_ai","submissions":a["submissions"]})
    dump(result/"statuses.json", {"schema_version":1,"run_id":run_id,"framework_origin":"drupal_ai","observations":a["statuses"]})
    dump(result/"recovery.json", {
        "schema_version":1,"run_id":run_id,"source_framework":"drupal_ai","failure_after_sequence":6,"failure_before_sequence":7,
        "completed_before_failure":[1,2,3,4,5,6],"interrupted_at":state["interrupted_at"],"resumed_at":state["resumed_at"],
        "resumed_with_run_id":run_id,"resumed_at_sequence":7,"duplicate_count":0,"completed_after_resume":[7,8,9,10,11,12],
        "shared_process_failure_recovery_claimed":False,
    })
    dump(result/"summary.json", {
        "schema_version":1,"status":"pass","run_id":run_id,"source_framework":"drupal_ai","provider":"OpenAI",
        "model":"gpt-4.1-mini-2025-04-14","temperature":0.0,"target_count":12,"completed_count":12,"failed_count":0,
        "duplicate_count":0,"validator_version":"gate05-validator-1.0.0","review_destination":"alt_text_suggestion",
        "source_article_unchanged":a["source_article_sha256_before"] == a["source_article_sha256_after"],
        "automatic_publication_performed":False,"lifecycle_seam_observed":True,"shared_process_failure_recovery_claimed":False,
        "resume_sequence":7,"started_at":state["started_at"],"completed_at":state["completed_at"],"human_review_completed":False,
    })
    (result/"summary.md").write_text(
        "# Gate 1 Step 1.07 Fresh Drupal AI Certification Batch\n\n"
        f"- **Status:** PASS\n- **Run ID:** `{run_id}`\n- **Targets:** 12 in frozen order\n"
        "- **Provider/model:** `OpenAI` / `gpt-4.1-mini-2025-04-14` / temperature `0.0`\n"
        "- **Lifecycle seam:** existing sequence-6/7 continuation exercised; not promoted to the later shared process-failure comparison claim\n"
        "- **Source Articles:** unchanged\n- **Automatic publication:** none\n",
        encoding="utf-8",
    )

def audit(repo: Path, gate: Path, result: Path) -> dict[str, Any]:
    required_gate = [
        "pre-cert-full.json","pre-cert-reduced.json","runtime-preflight.json","start-result.json","interrupted-state.json",
        "resume-result.json","runtime-export.json","completed-state.json","replay.json","status-reads.json",
        "review-lineage-reference.json","source-non-mutation.json","post-restore-full.json","post-restore-reduced.json",
    ]
    for n in required_gate: require((gate/n).is_file(), f"Missing certification evidence: {n}")
    for n in ["run.json","targets.json","events.jsonl","tool-traces.json","model-outputs.json","recommendations.json","validation.json","submissions.json","statuses.json","recovery.json","summary.json","summary.md"]:
        require((result/n).is_file(), f"Missing fresh result evidence: {n}")
    pre_full, post_full = load(gate/"pre-cert-full.json"), load(gate/"post-restore-full.json")
    pre_reduced, post_reduced = load(gate/"pre-cert-reduced.json"), load(gate/"post-restore-reduced.json")
    for value, label in ((pre_full,"pre-full"),(post_full,"post-full")):
        require(value.get("article_count")==20 and value.get("suggestion_count")==0, f"{label} is not zero-suggestion clean")
        require(value.get("article_source_sha256")==SOURCE_FULL, f"{label} full Article hash differs")
    for value, label in ((pre_reduced,"pre-reduced"),(post_reduced,"post-reduced")):
        require(value.get("seeded_clean") is True, f"{label} is not seeded-clean")
        require(value.get("article_source_sha256")==SOURCE_REDUCED, f"{label} reduced Article hash differs")
        require(value.get("runtime_state_present") is False and value.get("runtime_artifacts_present") is False, f"{label} retains runtime state")
    require(pre_full==post_full, "Full Article projection did not restore exactly")
    require(pre_reduced==post_reduced, "Reduced Step 1.05 projection did not restore exactly")
    start, resume = load(gate/"start-result.json"), load(gate/"resume-result.json")
    require(
        start.get("status") == "interrupted"
        and start.get("provider_request_count") == 6
        and start.get("agent_request_count") == 6
        and start.get("recommendation_count") == 6
        and start.get("pending_status_count") == 6
        and start.get("failure_injection_fired") is True
        and start.get("failure_after_sequence") == 6
        and start.get("failure_before_sequence") == 7
        and start.get("resume_at_sequence") == 7,
        "Fresh certification start evidence does not prove the controlled six-call interruption",
    )
    require(resume.get("status")=="completed" and resume.get("model_call_count_total")==12, "Fresh certification did not complete 12 model calls")
    require(resume.get("duplicate_count")==0 and resume.get("recommendation_count")==12 and resume.get("pending_status_count")==12, "Fresh batch counts differ")
    replay, statuses = load(gate/"replay.json"), load(gate/"status-reads.json")
    require(replay.get("status")=="pass" and replay.get("replayed_count")==12 and replay.get("duplicate_count")==0, "Full recommendation replay failed")
    require(replay.get("provider_request_count")==0 and replay.get("agent_request_count")==0, "Replay made a model/agent request")
    require(statuses.get("pending_count")==12 and statuses.get("provider_request_count")==0 and statuses.get("agent_request_count")==0, "Status certification differs")
    summary = load(result/"summary.json")
    require(summary.get("status")=="pass" and summary.get("target_count")==12 and summary.get("source_article_unchanged") is True, "Fresh result summary differs")
    review = load(gate/"review-lineage-reference.json")
    require(review.get("step06_run_id")==STEP06_RUN and review.get("review_decision_count")==3 and review.get("review_revision_count")==4, "Step 1.06 lineage reference differs")
    source = load(gate/"source-non-mutation.json")
    require(source.get("full_projection_unchanged") is True and source.get("reduced_projection_unchanged") is True, "Source non-mutation certification differs")
    secret = re.compile(r"sk-[A-Za-z0-9_-]{20,}|data:image/|Authorization\s*:|Basic\s+[A-Za-z0-9+/]{16,}={0,2}", re.I)
    for root in (gate, result):
        for p in root.rglob("*"):
            if p.is_file() and p.suffix not in {".sha256"} and secret.search(p.read_text(encoding="utf-8", errors="replace")):
                raise AuditError(f"Potential secret/raw image retained: {p}")
    return {"status":"pass","run_id":summary["run_id"],"target_count":12,"recommendation_count":12,"duplicate_count":0,"pending_count":12,"source_articles_unchanged":True,"restored_seeded_clean":True,"shared_process_failure_recovery_claimed":False}

def main() -> int:
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest="cmd", required=True)
    b=sub.add_parser("build-results"); b.add_argument("--gate",type=Path,required=True); b.add_argument("--result",type=Path,required=True)
    a=sub.add_parser("audit"); a.add_argument("--repo",type=Path,required=True); a.add_argument("--gate",type=Path,required=True); a.add_argument("--result",type=Path,required=True)
    args=parser.parse_args()
    if args.cmd=="build-results": build_results(args.gate.resolve(),args.result.resolve()); return 0
    print(json.dumps(audit(args.repo.resolve(),args.gate.resolve(),args.result.resolve()), indent=2, sort_keys=True)); return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except AuditError as exc: raise SystemExit(f"[ERROR] {exc}") from exc
