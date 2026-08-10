#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_TOOLS = [
    "find_images_needing_review",
    "get_image_context",
    "submit_recommendation",
    "get_recommendation_status",
]
EXPECTED_TARGET_HASH = "1f6132da02069f825cde52500242350e9ad6e85537c6c5407677e82d0e653728"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def repo_imports(repo: Path):
    sys.path.insert(0, str(repo))
    sys.path.insert(0, str(repo / "langchain"))
    from agentic_harness_langgraph.tools import build_tools
    from shared.drupal_client.client import DrupalClient
    return build_tools, DrupalClient


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any, str]] = []

    def find_images_needing_review(self, correlation_id: str):
        self.calls.append(("find_images_needing_review", None, correlation_id))
        return {"sentinel": "discovery"}

    def get_image_context(self, target, correlation_id: str):
        self.calls.append(("get_image_context", target, correlation_id))
        return {"sentinel": "context", "target": target}

    def submit_recommendation(self, recommendation, correlation_id: str):
        self.calls.append(("submit_recommendation", recommendation, correlation_id))
        return {"sentinel": "submission", "recommendation": recommendation}

    def get_recommendation_status(self, recommendation_id: str, correlation_id: str):
        self.calls.append(("get_recommendation_status", recommendation_id, correlation_id))
        return {"sentinel": "status", "recommendation_id": recommendation_id}


def static_proof(repo: Path) -> dict[str, Any]:
    build_tools, _ = repo_imports(repo)
    fake = FakeClient()
    tools = build_tools(fake, correlation_id="gate2a-step03-static")
    require(list(tools) == EXPECTED_TOOLS, "Tool order/name surface differs from frozen operations")

    target = {"synthetic": "target"}
    recommendation = {"synthetic": "recommendation"}
    outputs = [
        tools["find_images_needing_review"].invoke({}),
        tools["get_image_context"].invoke({"target": target}),
        tools["submit_recommendation"].invoke({"recommendation": recommendation}),
        tools["get_recommendation_status"].invoke({"recommendation_id": "synthetic-id"}),
    ]
    require(outputs[0] == {"sentinel": "discovery"}, "Discovery wrapper reshaped fake result")
    require(outputs[1] == {"sentinel": "context", "target": target}, "Context wrapper reshaped fake result")
    require(outputs[2] == {"sentinel": "submission", "recommendation": recommendation}, "Submission wrapper reshaped fake result")
    require(outputs[3] == {"sentinel": "status", "recommendation_id": "synthetic-id"}, "Status wrapper reshaped fake result")
    require([c[0] for c in fake.calls] == EXPECTED_TOOLS, "Delegation order differs from frozen operations")
    require(all(c[2] == "gate2a-step03-static" for c in fake.calls), "Correlation ID was not preserved")
    return {
        "status": "pass",
        "tool_names": list(tools),
        "tool_count": len(tools),
        "delegation_calls": [c[0] for c in fake.calls],
        "pass_through_results": True,
        "model_call_performed": False,
        "drupal_call_performed": False,
        "checkpoint_state_opened": False,
    }


def envelope(result: Any, tool_name: str) -> dict[str, Any]:
    require(isinstance(result, dict), f"{tool_name} result is not an object")
    required = {"schema_version","tool_name","ok","timestamp","correlation_id","data","error"}
    require(set(result) == required, f"{tool_name} envelope keys differ from frozen schema")
    require(result["schema_version"] == 1, f"{tool_name} schema_version is not 1")
    require(result["tool_name"] == tool_name, f"{tool_name} envelope tool_name mismatch")
    require(result["ok"] is True, f"{tool_name} did not return ok=true")
    require(result["error"] is None, f"{tool_name} returned an error")
    require(isinstance(result["data"], dict), f"{tool_name} data is not an object")
    return result["data"]


def context_summary(data: dict[str, Any]) -> dict[str, Any]:
    image = data.get("image")
    article = data.get("article")
    target = data.get("target")
    require(isinstance(image, dict), "Context image is missing")
    require(isinstance(article, dict), "Context article is missing")
    require(isinstance(target, dict), "Context target is missing")
    rep = image.get("representation")
    require(isinstance(rep, dict), "Context representation is missing")
    value = rep.get("value")
    require(isinstance(value, str) and value, "Context representation value is missing")
    return {
        "schema_version": data.get("schema_version"),
        "target": target,
        "article": {
            "title": article.get("title"),
            "revision_id": article.get("revision_id"),
            "content_language": article.get("content_language"),
            "body_plain_sha256": hashlib.sha256(str(article.get("body_plain","")).encode("utf-8")).hexdigest(),
            "body_plain_retained": False,
        },
        "image": {
            "file_uuid": image.get("file_uuid"),
            "filename": image.get("filename"),
            "mime_type": image.get("mime_type"),
            "width": image.get("width"),
            "height": image.get("height"),
            "byte_length": image.get("byte_length"),
            "sha256": image.get("sha256"),
            "representation_kind": rep.get("kind"),
            "representation_value_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
            "representation_value_length": len(value),
            "representation_value_retained": False,
        },
        "existing_alt": data.get("existing_alt"),
        "evidence_hash": data.get("evidence_hash"),
        "collected_at": data.get("collected_at"),
    }


def live_proof(repo: Path, evidence: Path, run_id: str) -> None:
    build_tools, DrupalClient = repo_imports(repo)
    base_url = os.environ.get("GATE2A_DRUPAL_BASE_URL","")
    username = os.environ.get("GATE2A_DRUPAL_USERNAME","")
    password = os.environ.get("GATE2A_DRUPAL_PASSWORD","")
    require(base_url and username and password, "Drupal live-proof environment is incomplete")

    correlation_id = f"{run_id}-tools"
    client = DrupalClient(
        base_url=base_url,
        username=username,
        password=password,
        verify_tls=False,
        timeout_seconds=60,
    )
    tools = build_tools(client, correlation_id=correlation_id)

    surface = {
        "status":"pass",
        "tool_names": list(tools),
        "tool_count": len(tools),
        "tools": {
            name: {
                "name": t.name,
                "description": t.description,
                "args_schema": t.args_schema.model_json_schema() if t.args_schema else None,
            }
            for name,t in tools.items()
        },
        "native_tool_type": {name: type(t).__name__ for name,t in tools.items()},
        "model_call_performed": False,
        "checkpoint_state_opened": False,
    }
    (evidence/"tool-surface.json").write_text(json.dumps(surface, indent=2, sort_keys=True)+"\n", encoding="utf-8")

    discovery = tools["find_images_needing_review"].invoke({})
    discovery_data = envelope(discovery, "find_images_needing_review")
    targets = discovery_data.get("targets")
    require(isinstance(targets, list) and len(targets)==12, "Discovery did not return exactly 12 targets")
    require(discovery_data.get("total_count")==12, "Discovery total_count is not 12")
    sequences = [t.get("sequence") for t in targets if isinstance(t, dict)]
    require(sequences == list(range(1,13)), "Target sequence is not exactly 1..12")
    # Retain targets: fixture identities are allowed evidence.
    (evidence/"targets.json").write_text(json.dumps(targets, indent=2, sort_keys=True)+"\n", encoding="utf-8")

    target = targets[0]
    context = tools["get_image_context"].invoke({"target": target})
    context_data = envelope(context, "get_image_context")
    require(context_data.get("target") == target, "Context target differs from discovery target")
    safe_context = context_summary(context_data)
    (evidence/"context-summary.json").write_text(json.dumps(safe_context, indent=2, sort_keys=True)+"\n", encoding="utf-8")

    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    recommendation_run_id = f"langgraph-{now}-step03"
    evidence_hash = context_data.get("evidence_hash")
    require(isinstance(evidence_hash, str) and evidence_hash.startswith("sha256:"), "Context evidence_hash is invalid")
    recommendation = {
        "schema_version": 1,
        "target": target,
        "proposed_alt_text": "Synthetic adapter proof description for deterministic editor review",
        "source_framework": "langgraph",
        "run_id": recommendation_run_id,
        "evidence_hash": evidence_hash,
        "validator_version": "gate05-validator-1.0.0",
    }

    first = tools["submit_recommendation"].invoke({"recommendation": recommendation})
    first_data = envelope(first, "submit_recommendation")
    second = tools["submit_recommendation"].invoke({"recommendation": recommendation})
    second_data = envelope(second, "submit_recommendation")
    require(first_data == second_data, "Same-identity recommendation replay was not idempotent")
    require(first_data.get("source_framework")=="langgraph", "Submission source_framework is not langgraph")
    require(first_data.get("run_id")==recommendation_run_id, "Submission run_id differs")
    require(first_data.get("status")=="pending", "Submission status is not pending")
    rec_id = first_data.get("uuid")
    require(isinstance(rec_id,str) and rec_id, "Submission UUID is missing")
    (evidence/"submission.json").write_text(json.dumps({
        "status":"pass",
        "recommendation": recommendation,
        "first": first_data,
        "same_identity_replay": second_data,
        "idempotent_replay": True,
    }, indent=2, sort_keys=True)+"\n", encoding="utf-8")

    status_result = tools["get_recommendation_status"].invoke({"recommendation_id": rec_id})
    status_data = envelope(status_result, "get_recommendation_status")
    require(status_data.get("status")=="pending", "Recommendation status is not pending")
    require(status_data.get("uuid")==rec_id, "Status UUID differs from submission UUID")
    (evidence/"status.json").write_text(json.dumps({
        "status":"pass",
        "recommendation_id": rec_id,
        "data": status_data,
    }, indent=2, sort_keys=True)+"\n", encoding="utf-8")

    summary = {
        "schema_version":1,
        "status":"pass",
        "run_id":run_id,
        "framework":"langgraph",
        "tool_count":4,
        "tool_names":list(tools),
        "target_count":12,
        "canonical_target_sequence":1,
        "same_identity_replay":True,
        "pending_status_observed":True,
        "raw_image_representation_retained":False,
        "article_body_retained":False,
        "credentials_retained":False,
        "authorization_header_retained":False,
        "model_call_performed":False,
        "provider_call_performed":False,
        "checkpoint_state_opened":False,
        "local_drupal_http_calls_performed":True,
        "temporary_recommendation_mutation_performed":True,
        "source_article_mutation_proof": "deferred_to_runner_before_during_after_state",
        "dependency_change":False,
    }
    (evidence/"summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    (evidence/"summary.md").write_text(
        "# Gate 2A Step 2A.03 LangGraph Tool Adapters\n\n"
        "- **Status:** PASS\n"
        f"- **Run ID:** `{run_id}`\n"
        "- **Tools:** four exact LangChain-native `@tool` wrappers\n"
        "- **Delegation:** frozen shared `DrupalClient` only\n"
        "- **Discovery:** 12 targets; canonical target sequence 1 exercised\n"
        "- **Context:** representation value and article body not retained\n"
        "- **Submission:** one deterministic test recommendation; same-identity replay idempotent\n"
        "- **Status:** pending observed through the fourth wrapper\n"
        "- **Model/provider calls:** 0\n"
        "- **Checkpoint state:** not opened\n"
        "- **Drupal mutation:** temporary recommendation only; runner must restore exact DDEV snapshot\n",
        encoding="utf-8"
    )


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--mode", choices=["static","live"], required=True)
    ap.add_argument("--evidence")
    ap.add_argument("--run-id")
    args=ap.parse_args()
    repo=Path(args.repo).resolve()
    if args.mode=="static":
        print(json.dumps(static_proof(repo), indent=2, sort_keys=True))
        return
    if not args.evidence or not args.run_id:
        raise SystemExit("[ERROR] live mode requires --evidence and --run-id")
    evidence=Path(args.evidence).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    try:
        live_proof(repo,evidence,args.run_id)
    except Exception as exc:
        failure={
            "schema_version":1,
            "status":"fail",
            "run_id":args.run_id,
            "error_type":type(exc).__name__,
            "error":str(exc)[:500],
            "model_call_performed":False,
            "provider_call_performed":False,
        }
        (evidence/"summary.json").write_text(json.dumps(failure,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        raise

if __name__=="__main__":
    main()
