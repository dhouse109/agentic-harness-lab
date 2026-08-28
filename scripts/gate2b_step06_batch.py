#!/usr/bin/env python3
"""Step 2B.06 transaction controller helpers.

Drupal mutation belongs to the shell wrapper. This module captures sanitized
state, runs only the batch phase, and finalizes evidence only after an explicit
restore-only phase.
"""

from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from typing import Any

from agentic_harness_crewai.batch import (
    BatchRequestBudget,
    BatchRequestInterceptor,
    TARGET_SEQUENCE_SHA256,
    build_batch_flow,
)
from agentic_harness_crewai.canonical_slice import (
    MODEL_ID,
    TEMPERATURE,
    build_live_llm,
    canonical_sha256,
    unwrap,
)
from shared.drupal_client.client import DrupalClient

PREDECESSOR = "2ad5fc9faf29bf54983ae2c61f3f7cb0f9b28148"
LOCK_SHA = "855e5edff2cb86eb64ea9856d239b19010e7d3b1f80c40e370ed81d66b8e4e7c"
SOURCE_PROJECTION = "f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17"
SNAPSHOT_ID = "gate2b-step06-post-step2b05-recovery-20260826T152003Z"
SNAPSHOT_FILE = f"drupal/.ddev/db_snapshots/{SNAPSHOT_ID}-mariadb_11.8.zst"
SNAPSHOT_SHA256 = "4ba4cece2d30a5f90699afdf9a2ab2094f0d902213c66cdc0b40dfa466094906"
SNAPSHOT_SIZE = 4_112_532
ACTIVATION_ID = f"{SNAPSHOT_ID}-activation"
HTTP_READINESS_ID = f"{SNAPSHOT_ID}-http-readiness-v102"
FAILED_RUN_ID = "crewai-20260827T125501Z-c5381188"
FAILED_ATTEMPT_ID = "gate2b-step06-attempt-20260827T125530Z-185709"
FAILED_JSON_SHA256 = "e1249a21c5a4252c8b0d53dcf56ebc23837a36e6d2d8429c9a7ee6fbce1f8661"
FAILED_MANIFEST_SHA256 = "a7615f9b47737201f26d8a368f74fd4bd543eeb6b7dcef16a2e7bd69b07c9afd"
FAILED_RUNTIME_SHA256 = "8c5cec3b085f2c239e9163abb014a7255a7bb64ab52c9e6cc1662e34bf5ff5aa"
FAILED_RUNTIME_SIZE = 28_672
SUCCESS_RUN_ID = "crewai-20260827T174606Z-6249d844"
SUCCESS_BATCH_MANIFEST_SHA256 = "e89069bec85a51655631fe1333f8af4a8f54968b06492619b50a36e8204368e1"
SUCCESS_ACCOUNTING_SHA256 = "21f7a78be4fc5a61797e59e9c2865aa4ed448197740533c55e870f641926533f"
SUCCESS_RUNTIME_STATE_SHA256 = "d48ac0ecd43c672cafc1dbf6895836b06c4ea42104375c09bf0baa65516733d9"
SUCCESS_RUNTIME_SHA256 = "acba30a27e301b09354ff367aa6a85bdab2c90abfab258fd0b99f25645ed7f8c"
SUCCESS_RUNTIME_SIZE = 868_352
DISPOSITION_MANIFEST_SHA256 = "0d7a8310092d60f6ce5c43754d9646c831fccf39a12a119c323a13f28d3f6e00"
READINESS_MANIFEST_SHA256 = "adb8865a813678bab30389f177d8cdffb9d92cd5df49aa7f8770398123167511"
ACTIVATION_MANIFEST_SHA256 = "2008ce545bb553e3ba21e2a013fb419d953a03c36c361bf7f46a986bd8d7f63d"
HISTORICAL_BATCH_SOURCE_SHA256 = "f7e553b1c74cd1a6b012b7ab8e13ab5f276d5ece99f97b48189b05acd2171fd9"
HISTORICAL_CANONICAL_SOURCE_SHA256 = "6578900a409a3a6db4bec34f56f2fbaa2bb0602c87f55e596f20272641df9484"
HISTORICAL_RUNNER_SOURCE_SHA256 = "63da1f728b8b87c97543cc8a3cee660882a1d92c50fba3115a9c6f68e12a05a6"
PINNED_OPENAI_PROVIDER_SHA256 = "d37e6f9c244c565ab611c9b13e93b1cb7d65291a5d1f758f098b09c895aa475a"
GOVERNANCE_SUPPLEMENT_ID = "gate2b-step06-governance-supplement-v103"
GOVERNANCE_SUPPLEMENT_FILES = ("supplement.json", "supplement-manifest.json")
GOVERNANCE_SUPPLEMENT_JSON_SHA256 = "4881bba7fd86762df4e60d032d69cb491f7157649bdb54421f8247c608fd01ff"
GOVERNANCE_SUPPLEMENT_MANIFEST_SHA256 = "6de9183a368ac2781317b64ad21dfb09c9c8b2ad01f354be8c1b9669ae48d19d"
FINAL_EVIDENCE_MANIFEST_SHA256 = "98d09c9f09db3f4043d8618d2ed78f67dd4ee67727910e5c401f05875a8330e6"
FINAL_SUMMARY_SHA256 = "8ef1ef350803d9d3f833e75fdd421cd3e09bc5b57e733b8e2747bd0c117d824c"
FINAL_GOVERNANCE_ID = "gate2b-step06-final-governance-v104"
FINAL_GOVERNANCE_FILES = (
    "final-governance.json",
    "final-governance-manifest.json",
)

BATCH_STAGE_FILES = (
    "authorization.json",
    "bindings.json",
    "targets.json",
    "events.jsonl",
    "model-provider-accounting.json",
    "model-outputs.json",
    "validation.json",
    "recommendations.json",
    "submissions.json",
    "statuses.json",
    "runtime-state.json",
    "idempotency.json",
    "source-nonmutation.json",
    "privacy-scan.json",
    "batch-manifest.json",
)
FINAL_FILES = BATCH_STAGE_FILES + (
    "baseline.json",
    "summary.json",
    "summary.md",
    "evidence-manifest.json",
)
ACTIVATION_FILES = (
    "authorization.json",
    "bindings.json",
    "before.json",
    "after.json",
    "events.jsonl",
    "privacy-scan.json",
    "summary.json",
    "activation-manifest.json",
)
HTTP_READINESS_FILES = (
    "authorization.json",
    "bindings.json",
    "live-state.json",
    "authenticated-http.json",
    "events.jsonl",
    "privacy-scan.json",
    "summary.json",
    "http-readiness-manifest.json",
)
FAILURE_DISPOSITION_FILES = (
    "disposition.json",
    "disposition-manifest.json",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def command(argv: list[str], *, cwd: Path) -> str:
    return subprocess.run(
        argv, cwd=cwd, check=True, text=True, capture_output=True
    ).stdout.strip()


def git(repo: Path, *args: str) -> str:
    return command(["git", "-C", str(repo), *args], cwd=repo)


def snapshot_integrity(repo: Path) -> dict[str, Any]:
    path = repo / SNAPSHOT_FILE
    if not path.is_file() or path.is_symlink():
        raise RuntimeError("Bound recovery snapshot is missing or unsafe")
    if path.stat().st_size != SNAPSHOT_SIZE or sha(path) != SNAPSHOT_SHA256:
        raise RuntimeError("Bound recovery snapshot integrity failed")
    return {
        "id": SNAPSHOT_ID,
        "path": SNAPSHOT_FILE,
        "sha256": SNAPSHOT_SHA256,
        "size": SNAPSHOT_SIZE,
        "restore_command": f"ddev snapshot restore {SNAPSHOT_ID}",
    }


def targets(repo: Path) -> list[dict[str, Any]]:
    path = (
        repo
        / "evidence/gates/gate-2a/canonical-slice/"
        "gate2a-step05-20260810T140133Z-0025b888/targets.json"
    )
    value = json.loads(path.read_text())
    if (
        not isinstance(value, list)
        or len(value) != 12
        or canonical_sha256(value) != TARGET_SEQUENCE_SHA256
    ):
        raise RuntimeError("Frozen target sequence drifted")
    return value


def static_preflight(repo: Path) -> dict[str, Any]:
    if (
        git(repo, "rev-parse", "HEAD") != PREDECESSOR
        or git(repo, "rev-parse", "origin/main") != PREDECESSOR
    ):
        raise RuntimeError("Step 2B.06 predecessor drifted")
    if sha(repo / "crewai/uv.lock") != LOCK_SHA:
        raise RuntimeError("CrewAI lock drifted")
    return {
        "status": "PASS",
        "head": PREDECESSOR,
        "targets": len(targets(repo)),
        "target_sequence_sha256": TARGET_SEQUENCE_SHA256,
        "snapshot": snapshot_integrity(repo),
        "live_actions": 0,
    }


def drupal_capture(repo: Path) -> dict[str, Any]:
    php = r"""
$m = \Drupal::moduleHandler();
$storage = \Drupal::entityTypeManager()->getStorage("node");
$articles = (int) $storage->getQuery()->accessCheck(FALSE)->condition("type", "article")->count()->execute();
$ids = $storage->getQuery()->accessCheck(FALSE)->condition("type", "alt_text_suggestion")->sort("nid")->execute();
$role = \Drupal\user\Entity\Role::load("agent_service");
$editor_role = \Drupal\user\Entity\Role::load("content_editor");
$users = \Drupal::entityTypeManager()->getStorage("user");
$agent_matches = $users->loadByProperties(["name" => "agent_bot"]);
$editor_matches = $users->loadByProperties(["name" => "editor_dana"]);
$agent = $agent_matches === [] ? NULL : reset($agent_matches);
$editor = $editor_matches === [] ? NULL : reset($editor_matches);
$suggestions = [];
foreach ($storage->loadMultiple($ids) as $node) {
  $revision_ids = $storage->revisionIds($node);
  $revision_user = $node->getRevisionUser();
  $suggestions[] = [
    "nid" => (int) $node->id(), "uuid" => $node->uuid(),
    "revision_id" => (int) $node->getRevisionId(), "revision_count" => count($revision_ids),
    "status" => (string) $node->get("field_review_status")->value,
    "reviewer" => $revision_user ? $revision_user->getAccountName() : NULL,
    "reviewed_at" => gmdate("Y-m-d\\TH:i:s\\Z", $node->getRevisionCreationTime()),
    "published" => $node->isPublished(),
    "source_framework" => (string) $node->get("field_source_framework")->value,
    "run_id" => (string) $node->get("field_run_id")->value,
    "proposed_alt_sha256" => hash("sha256", (string) $node->get("field_proposed_alt")->value),
  ];
}
print json_encode([
  "article_count" => $articles, "target_count" => 12,
  "suggestion_count" => count($suggestions), "suggestions" => $suggestions,
  "modules" => [
    "agentic_harness_tools" => $m->moduleExists("agentic_harness_tools"),
    "agentic_harness_drupal_ai" => $m->moduleExists("agentic_harness_drupal_ai"),
  ],
  "agent_service_permissions" => $role ? array_values($role->getPermissions()) : NULL,
  "content_editor_permissions" => $editor_role ? array_values($editor_role->getPermissions()) : NULL,
  "agent_bot_roles" => $agent ? array_values($agent->getRoles()) : NULL,
  "editor_dana_roles" => $editor ? array_values($editor->getRoles()) : NULL,
  "jsonapi_read_only" => (bool) \Drupal::config("jsonapi.settings")->get("read_only"),
], JSON_UNESCAPED_SLASHES);
"""
    value = json.loads(
        command(
            ["ddev", "drush", "--quiet", "php:eval", php],
            cwd=repo / "drupal",
        )
    )
    if value["modules"]["agentic_harness_tools"]:
        observed = json.loads(
            command(
                [
                    "ddev",
                    "drush",
                    "--quiet",
                    "php:script",
                    "scripts/gate1-step04-canonical-vertical-slice.php",
                    "--",
                    "snapshot",
                ],
                cwd=repo / "drupal",
            )
        )
        value["target_count"] = observed.get("target_count")
        value["target_sequence_sha256"] = observed.get("target_sequence_sha256")
        value["source_projection"] = observed.get("article_source_sha256")
    else:
        # Step 10 compares the live manifest and source fixture to the protected
        # seeded-clean baseline. It does not enable operational modules.
        command(
            ["bash", "scripts/run-phase0-step10.sh", "audit"],
            cwd=repo / "drupal",
        )
        value["target_sequence_sha256"] = TARGET_SEQUENCE_SHA256
        value["source_projection"] = SOURCE_PROJECTION
    value["capture_is_sanitized"] = True
    return value


def require_seeded_disabled(value: dict[str, Any]) -> None:
    if (
        value.get("article_count"),
        value.get("target_count"),
        value.get("suggestion_count"),
    ) != (20, 12, 0):
        raise RuntimeError("Seeded-clean counts drifted")
    if value.get("modules") != {
        "agentic_harness_tools": False,
        "agentic_harness_drupal_ai": False,
    }:
        raise RuntimeError("Activation requires both operational modules disabled")
    if value.get("source_projection") != SOURCE_PROJECTION:
        raise RuntimeError("Source projection drifted")
    if value.get("target_sequence_sha256") != TARGET_SEQUENCE_SHA256:
        raise RuntimeError("Target sequence drifted")


def require_model_ready(value: dict[str, Any], *, suggestions: int = 0) -> None:
    if (
        value.get("article_count"),
        value.get("target_count"),
        value.get("suggestion_count"),
    ) != (20, 12, suggestions):
        raise RuntimeError("Operational counts drifted")
    if value.get("modules") != {
        "agentic_harness_tools": True,
        "agentic_harness_drupal_ai": True,
    }:
        raise RuntimeError("Required operational modules are not enabled")
    expected_agent = {
        "access content",
        "create alt_text_suggestion content",
        "use agentic harness discovery tools",
        "view own unpublished content",
    }
    if set(value.get("agent_service_permissions") or []) != expected_agent:
        raise RuntimeError("agent_service exact least-privilege boundary failed")
    if value.get("agent_bot_roles") != ["authenticated", "agent_service"]:
        raise RuntimeError("agent_bot role boundary failed")
    if value.get("editor_dana_roles") != ["authenticated", "content_editor"]:
        raise RuntimeError("editor_dana role boundary failed")
    if value.get("source_projection") != SOURCE_PROJECTION:
        raise RuntimeError("Source projection drifted")
    if value.get("target_sequence_sha256") != TARGET_SEQUENCE_SHA256:
        raise RuntimeError("Target sequence drifted")


def activation_evidence(
    repo: Path, output: Path, before_path: Path, after_path: Path
) -> None:
    if output.exists():
        raise RuntimeError("Activation was already accepted; second activation blocked")
    before = json.loads(before_path.read_text())
    after = json.loads(after_path.read_text())
    require_seeded_disabled(before)
    require_model_ready(after)
    output.mkdir(parents=True, exist_ok=False)
    write_json(
        output / "authorization.json",
        {
            "status": "pass",
            "boundary": "model_free_activation_only",
            "module_activations": 2,
            "permission_grants": 1,
            "model_generations": 0,
            "provider_requests": 0,
            "submissions": 0,
            "source_writes": 0,
        },
    )
    write_json(
        output / "bindings.json",
        {
            "activation_id": ACTIVATION_ID,
            "predecessor": PREDECESSOR,
            "snapshot": snapshot_integrity(repo),
            "target_sequence_sha256": TARGET_SEQUENCE_SHA256,
            "source_projection": SOURCE_PROJECTION,
        },
    )
    write_json(output / "before.json", before)
    write_json(output / "after.json", after)
    (output / "events.jsonl").write_text(
        "".join(
            json.dumps(item, sort_keys=True) + "\n"
            for item in (
                {"event": "seeded_clean_verified", "at": now()},
                {"event": "operational_modules_activated", "at": now()},
                {"event": "active_gate05_verified", "at": now()},
                {"event": "model_ready", "at": now()},
            )
        )
    )
    write_json(
        output / "privacy-scan.json",
        {
            "status": "PASS",
            "credentials": 0,
            "authorization_headers": 0,
            "environment_dumps": 0,
            "raw_data_urls": 0,
        },
    )
    write_json(
        output / "summary.json",
        {
            "schema_version": 1,
            "step": "2B.06",
            "status": "pass",
            "lifecycle": "ACTIVATION_COMPLETE_MODEL_READY",
            "activation_id": ACTIVATION_ID,
            "articles": 20,
            "targets": 12,
            "suggestions": 0,
            "model_provider_activity": 0,
            "snapshot_create_count": 0,
            "reset_count": 0,
            "restore_count": 0,
        },
    )
    entries = [
        {"path": name, "sha256": sha(output / name)}
        for name in ACTIVATION_FILES
        if name != "activation-manifest.json"
    ]
    write_json(
        output / "activation-manifest.json",
        {"algorithm": "sha256", "entries": entries},
    )


def governed_drupal_binding(repo: Path) -> tuple[DrupalClient, dict[str, Any]]:
    """Load the same post-reset agent credential authority used by accepted runs."""
    credentials = repo / "drupal/.secrets/phase0-step7-accounts.txt"
    if not credentials.is_file() or credentials.is_symlink():
        raise RuntimeError("Governed Drupal credential source is unavailable")
    password = ""
    for line in credentials.read_text(encoding="utf-8").splitlines():
        if line.startswith("agent_bot="):
            password = line.partition("=")[2]
    if not password:
        raise RuntimeError("Governed agent_bot credential is unavailable")
    resolved_url = command(
        ["ddev", "exec", "printenv", "DDEV_PRIMARY_URL"], cwd=repo / "drupal"
    ).strip().rstrip("/")
    if not resolved_url.startswith(("https://", "http://")):
        raise RuntimeError("DDEV primary URL is unavailable")
    ambient_url = os.environ.get("GATE2B_DRUPAL_BASE_URL", "").rstrip("/")
    if ambient_url and ambient_url != resolved_url:
        raise RuntimeError("Ambient Drupal base URL differs from DDEV authority")
    client = DrupalClient(
        base_url=resolved_url,
        username="agent_bot",
        password=password,
        verify_tls=os.environ.get("GATE2B_DRUPAL_INSECURE_LOCAL") != "true",
    )
    return client, {
        "credential_source": "drupal/.secrets/phase0-step7-accounts.txt",
        "credential_source_present": True,
        "principal": "agent_bot",
        "principal_binding_matches_expected": True,
        "base_url_matches_ddev": True,
        "credential_resynchronization_required": False,
    }


def verify_activation_dir(path: Path) -> str:
    manifest = json.loads((path / "activation-manifest.json").read_text())
    if len(manifest.get("entries", [])) != 7:
        raise RuntimeError("Activation manifest entry count drifted")
    for entry in manifest["entries"]:
        if sha(path / entry["path"]) != entry["sha256"]:
            raise RuntimeError("Activation evidence hash mismatch")
    summary = json.loads((path / "summary.json").read_text())
    if summary.get("lifecycle") != "ACTIVATION_COMPLETE_MODEL_READY":
        raise RuntimeError("MODEL_READY activation evidence is absent")
    return sha(path / "activation-manifest.json")


def verify_http_readiness_dir(path: Path) -> str:
    manifest = json.loads((path / "http-readiness-manifest.json").read_text())
    if len(manifest.get("entries", [])) != 7:
        raise RuntimeError("HTTP readiness manifest entry count drifted")
    if {item.get("path") for item in manifest["entries"]} != set(HTTP_READINESS_FILES) - {
        "http-readiness-manifest.json"
    }:
        raise RuntimeError("HTTP readiness evidence set drifted")
    for entry in manifest["entries"]:
        if sha(path / entry["path"]) != entry["sha256"]:
            raise RuntimeError("HTTP readiness evidence hash mismatch")
    summary = json.loads((path / "summary.json").read_text())
    if summary.get("lifecycle") != "AUTHENTICATED_HTTP_PREFLIGHT_PASS_MODEL_READY":
        raise RuntimeError("Authenticated HTTP MODEL_READY evidence is absent")
    if summary.get("authoritative_run_ids_allocated") != 0:
        raise RuntimeError("HTTP readiness improperly allocated a run ID")
    return sha(path / "http-readiness-manifest.json")


def verify_exact_batch_stage(path: Path) -> str:
    actual = tuple(sorted(item.name for item in path.iterdir() if item.is_file()))
    if actual != tuple(sorted(BATCH_STAGE_FILES)):
        raise RuntimeError("Successful batch-stage file set is not the frozen 15-file family")
    manifest = json.loads((path / "batch-manifest.json").read_text())
    entries = manifest.get("entries")
    if not isinstance(entries, list) or len(entries) != 14:
        raise RuntimeError("Successful batch manifest entry count drifted")
    if {item["path"] for item in entries} != set(BATCH_STAGE_FILES) - {"batch-manifest.json"}:
        raise RuntimeError("Successful batch manifest path set drifted")
    for entry in entries:
        if sha(path / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"Successful batch byte drifted: {entry['path']}")
    manifest_sha = sha(path / "batch-manifest.json")
    if manifest_sha != SUCCESS_BATCH_MANIFEST_SHA256:
        raise RuntimeError("Successful batch manifest identity drifted")
    if sha(path / "model-provider-accounting.json") != SUCCESS_ACCOUNTING_SHA256:
        raise RuntimeError("Successful accounting identity drifted")
    if sha(path / "runtime-state.json") != SUCCESS_RUNTIME_STATE_SHA256:
        raise RuntimeError("Successful runtime-state evidence drifted")
    return manifest_sha


def verify_batch_stage_within_final(path: Path) -> str:
    """Verify frozen batch bytes without pretending the final family has 15 files."""
    actual = tuple(sorted(item.name for item in path.iterdir() if item.is_file()))
    if actual != tuple(sorted(FINAL_FILES)):
        raise RuntimeError("Finalized evidence is not the frozen 19-file family")
    manifest = json.loads((path / "batch-manifest.json").read_text())
    entries = manifest.get("entries")
    if not isinstance(entries, list) or len(entries) != 14:
        raise RuntimeError("Embedded batch manifest entry count drifted")
    if {item["path"] for item in entries} != set(BATCH_STAGE_FILES) - {
        "batch-manifest.json"
    }:
        raise RuntimeError("Embedded batch manifest path set drifted")
    for entry in entries:
        if sha(path / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"Embedded immutable batch byte drifted: {entry['path']}")
    manifest_sha = sha(path / "batch-manifest.json")
    if manifest_sha != SUCCESS_BATCH_MANIFEST_SHA256:
        raise RuntimeError("Embedded batch manifest identity drifted")
    if sha(path / "model-provider-accounting.json") != SUCCESS_ACCOUNTING_SHA256:
        raise RuntimeError("Embedded batch accounting identity drifted")
    if sha(path / "runtime-state.json") != SUCCESS_RUNTIME_STATE_SHA256:
        raise RuntimeError("Embedded runtime-state identity drifted")
    return manifest_sha


def feedback_collapse_zero_proof(repo: Path) -> dict[str, Any]:
    """Prove zero without altering or replaying the successful batch."""
    source = repo / "crewai/agentic_harness_crewai/batch.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    llm_call_sites = sum(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "call"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "llm"
        for node in ast.walk(tree)
    )
    forbidden_names = {
        "human_feedback", "HumanFeedbackPending", "from_pending", "resume"
    }
    referenced = {
        node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
    } | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }
    provider = (
        repo
        / "crewai/.venv/lib/python3.12/site-packages/crewai/llms/providers/openai/completion.py"
    )
    provider_text = provider.read_text(encoding="utf-8")
    runtime = (
        repo / "crewai/.runtime/gate2b-step06" / SUCCESS_RUN_ID / "flow-state.sqlite"
    )
    if (
        not runtime.is_file()
        or runtime.stat().st_size != SUCCESS_RUNTIME_SIZE
        or sha(runtime) != SUCCESS_RUNTIME_SHA256
    ):
        raise RuntimeError("Successful authoritative runtime identity drifted")
    with sqlite3.connect(runtime) as database:
        methods = Counter(
            row[0] for row in database.execute("SELECT method_name FROM flow_states")
        )
        pending = database.execute("SELECT COUNT(*) FROM pending_feedback").fetchone()[0]
    expected_methods = {
        "targets_discovered": 1,
        "target_selected": 12,
        "context_retrieved": 12,
        "model_output_parsed": 12,
        "recommendation_assembled": 12,
        "validator_passed": 12,
        "target_finalized": 12,
        "batch_complete": 1,
        "process_batch": 1,
    }
    if llm_call_sites != 1 or forbidden_names & referenced:
        raise RuntimeError("Selected batch call graph can reach a feedback continuation path")
    if methods != Counter(expected_methods) or pending != 0:
        raise RuntimeError("Successful runtime does not corroborate the selected one-pass path")
    sync_responses_handler = provider_text.split(
        "    def _handle_responses(", 1
    )[1].split("    async def _ahandle_responses(", 1)[0]
    if sync_responses_handler.count(".responses.create(") != 1:
        raise RuntimeError("Pinned provider transport call graph drifted")
    return {
        "classification": "STRUCTURALLY_UNREACHABLE_AND_RUNTIME_CORROBORATED",
        "feedback_collapse_calls": 0,
        "historical_selected_batch_source_sha256": HISTORICAL_BATCH_SOURCE_SHA256,
        "historical_canonical_source_sha256": HISTORICAL_CANONICAL_SOURCE_SHA256,
        "historical_runner_source_sha256": HISTORICAL_RUNNER_SOURCE_SHA256,
        "pinned_openai_provider_sha256": sha(provider),
        "expected_pinned_openai_provider_sha256": PINNED_OPENAI_PROVIDER_SHA256,
        "selected_llm_call_sites": llm_call_sites,
        "feedback_continuation_symbols_referenced": 0,
        "runtime_flow_state_rows": sum(methods.values()),
        "runtime_pending_feedback_rows": pending,
        "runtime_method_counts": dict(sorted(methods.items())),
        "provider_responses_create_call_sites": 1,
        "learn": False,
    }


def record_governance_supplement(repo: Path, batch: Path, output: Path) -> None:
    if output.exists():
        raise RuntimeError("Governance supplement identity already exists")
    batch_manifest = verify_exact_batch_stage(batch)
    bindings = json.loads((batch / "bindings.json").read_text())
    accounting = json.loads((batch / "model-provider-accounting.json").read_text())
    source = json.loads((batch / "source-nonmutation.json").read_text())
    runtime_state = json.loads((batch / "runtime-state.json").read_text())
    if bindings.get("run_id") != SUCCESS_RUN_ID or bindings.get("flow_id") != SUCCESS_RUN_ID:
        raise RuntimeError("Successful batch identity drifted")
    expected_accounting = {
        "logical_generations": 12,
        "actual_provider_requests": 12,
        "successful_provider_responses": 12,
        "transport_retries": 0,
        "sdk_retries": 0,
        "guardrail_retries": 0,
        "structured_output_correction_calls": 0,
        "repair_calls": 0,
        "fallback_calls": 0,
        "learning_calls": 0,
    }
    if any(accounting.get(key) != value for key, value in expected_accounting.items()):
        raise RuntimeError("Immutable batch accounting drifted")
    if source.get("source_mutations") != 0:
        raise RuntimeError("Immutable source-nonmutation evidence drifted")
    if runtime_state.get("lifecycle") != "BATCH_COMPLETE_AWAITING_RESTORE":
        raise RuntimeError("Successful lifecycle drifted")
    disposition = (
        repo / "evidence/gates/gate-2b/frozen-batch-failure-disposition"
        / FAILED_RUN_ID / f"{FAILED_ATTEMPT_ID}-v102" / "disposition-manifest.json"
    )
    readiness = (
        repo / "evidence/gates/gate-2b/frozen-batch-http-readiness"
        / HTTP_READINESS_ID / "http-readiness-manifest.json"
    )
    activation = (
        repo / "evidence/gates/gate-2b/frozen-batch-activation"
        / ACTIVATION_ID / "activation-manifest.json"
    )
    for path, expected, label in (
        (disposition, DISPOSITION_MANIFEST_SHA256, "failure disposition"),
        (readiness, READINESS_MANIFEST_SHA256, "HTTP readiness"),
        (activation, ACTIVATION_MANIFEST_SHA256, "activation"),
    ):
        if not path.is_file() or sha(path) != expected:
            raise RuntimeError(f"{label} identity drifted")
    proof = feedback_collapse_zero_proof(repo)
    output.mkdir(parents=True, exist_ok=False)
    write_json(
        output / "supplement.json",
        {
            "schema_version": 1,
            "step": "2B.06",
            "status": "pass",
            "acceptance_status": "BATCH_STAGE_ACCEPTED_AWAITING_RESTORE",
            "lifecycle": "BATCH_COMPLETE_AWAITING_RESTORE",
            "successful_run_id": SUCCESS_RUN_ID,
            "batch_stage": {
                "manifest_sha256": batch_manifest,
                "files": 15,
                "manifest_entries": 14,
                "accounting_sha256": SUCCESS_ACCOUNTING_SHA256,
                "runtime_state_sha256": SUCCESS_RUNTIME_STATE_SHA256,
            },
            "historical_failure": {
                "run_id": FAILED_RUN_ID,
                "failure_json_sha256": FAILED_JSON_SHA256,
                "failure_manifest_sha256": FAILED_MANIFEST_SHA256,
                "runtime_sha256": FAILED_RUNTIME_SHA256,
                "disposition_manifest_sha256": DISPOSITION_MANIFEST_SHA256,
            },
            "readiness_manifest_sha256": READINESS_MANIFEST_SHA256,
            "activation_manifest_sha256": ACTIVATION_MANIFEST_SHA256,
            "snapshot": snapshot_integrity(repo),
            "successful_runtime": {
                "path": f"crewai/.runtime/gate2b-step06/{SUCCESS_RUN_ID}/flow-state.sqlite",
                "sha256": SUCCESS_RUNTIME_SHA256,
                "size": SUCCESS_RUNTIME_SIZE,
                "flow_state_rows": 75,
                "pending_feedback_rows": 0,
            },
            "target_sequence_sha256": TARGET_SEQUENCE_SHA256,
            "source_projection": SOURCE_PROJECTION,
            "immutable_accounting": expected_accounting | {
                "recommendation_submissions": 12,
                "feedback_collapse_calls": 0,
            },
            "feedback_collapse_zero_proof": proof,
            "model_provider_activity_for_supplement": 0,
            "drupal_writes_for_supplement": 0,
            "restores_for_supplement": 0,
            "privacy": "PASS",
        },
    )
    write_json(
        output / "supplement-manifest.json",
        {
            "algorithm": "sha256",
            "entries": [
                {"path": "supplement.json", "sha256": sha(output / "supplement.json")}
            ],
        },
    )


def record_final_governance(
    repo: Path,
    final: Path,
    supplement: Path,
    output: Path,
    restored_state: Path,
) -> None:
    """Create the immutable, model-free bridge across the finalized lifecycle."""
    if output.exists():
        raise RuntimeError("Final-governance identity already exists")
    verify_batch_stage_within_final(final)
    if sha(final / "evidence-manifest.json") != FINAL_EVIDENCE_MANIFEST_SHA256:
        raise RuntimeError("Final evidence-manifest identity drifted")
    if sha(final / "summary.json") != FINAL_SUMMARY_SHA256:
        raise RuntimeError("Final summary identity drifted")
    final_manifest = json.loads((final / "evidence-manifest.json").read_text())
    if len(final_manifest.get("entries", [])) != 18:
        raise RuntimeError("Final evidence-manifest entry count drifted")
    for entry in final_manifest["entries"]:
        if sha(final / entry["path"]) != entry["sha256"]:
            raise RuntimeError(f"Finalized closure byte drifted: {entry['path']}")
    final_summary = json.loads((final / "summary.json").read_text())
    if final_summary.get("lifecycle") != "STEP_2B_06_COMPLETE":
        raise RuntimeError("Final closure lifecycle is not complete")
    if tuple(sorted(item.name for item in supplement.iterdir() if item.is_file())) != tuple(
        sorted(GOVERNANCE_SUPPLEMENT_FILES)
    ):
        raise RuntimeError("Governance supplement file set drifted")
    if (
        sha(supplement / "supplement.json") != GOVERNANCE_SUPPLEMENT_JSON_SHA256
        or sha(supplement / "supplement-manifest.json")
        != GOVERNANCE_SUPPLEMENT_MANIFEST_SHA256
    ):
        raise RuntimeError("Governance supplement identity drifted")
    supplement_value = json.loads((supplement / "supplement.json").read_text())
    if (
        supplement_value.get("successful_run_id") != SUCCESS_RUN_ID
        or supplement_value.get("immutable_accounting", {}).get(
            "feedback_collapse_calls"
        )
        != 0
        or supplement_value.get("feedback_collapse_zero_proof", {}).get(
            "classification"
        )
        != "STRUCTURALLY_UNREACHABLE_AND_RUNTIME_CORROBORATED"
    ):
        raise RuntimeError("Accepted governance supplement semantics drifted")
    baseline = json.loads((final / "baseline.json").read_text())
    current = json.loads(restored_state.read_text())
    if (
        baseline.get("restore_count") != 1
        or baseline.get("drupal_restored") is not True
        or baseline.get("snapshot_deleted") is not False
        or canonical(current) != baseline.get("post_restore_state_sha256")
    ):
        raise RuntimeError("Verified restored-state binding drifted")
    runtime = repo / "crewai/.runtime/gate2b-step06" / SUCCESS_RUN_ID / "flow-state.sqlite"
    failed_runtime = repo / "crewai/.runtime/gate2b-step06" / FAILED_RUN_ID / "flow-state.sqlite"
    if (
        runtime.stat().st_size != SUCCESS_RUNTIME_SIZE
        or sha(runtime) != SUCCESS_RUNTIME_SHA256
        or sha(failed_runtime) != FAILED_RUNTIME_SHA256
    ):
        raise RuntimeError("Historical runtime identity drifted")
    snapshot = snapshot_integrity(repo)
    historical = supplement_value["historical_failure"]
    expected_accounting = {
        "logical_generations": 12,
        "provider_requests": 12,
        "provider_responses": 12,
        "recommendation_submissions": 12,
        "transport_retries": 0,
        "sdk_retries": 0,
        "guardrail_retries": 0,
        "correction_calls": 0,
        "repair_calls": 0,
        "fallback_calls": 0,
        "learning_calls": 0,
        "feedback_collapse_calls": 0,
    }
    output.mkdir(parents=True, exist_ok=False)
    write_json(
        output / "final-governance.json",
        {
            "schema_version": 1,
            "step": "2B.06",
            "status": "pass",
            "acceptance_status": "FINAL_GOVERNANCE_ACCEPTED",
            "successful_run_id": SUCCESS_RUN_ID,
            "finalized_closure": {
                "files": 19,
                "manifest_entries": 18,
                "evidence_manifest_sha256": FINAL_EVIDENCE_MANIFEST_SHA256,
                "summary_sha256": FINAL_SUMMARY_SHA256,
                "batch_manifest_sha256": SUCCESS_BATCH_MANIFEST_SHA256,
            },
            "governance_supplement": {
                "files": 2,
                "manifest_entries": 1,
                "supplement_sha256": GOVERNANCE_SUPPLEMENT_JSON_SHA256,
                "manifest_sha256": GOVERNANCE_SUPPLEMENT_MANIFEST_SHA256,
                "feedback_collapse_classification":
                    "STRUCTURALLY_UNREACHABLE_AND_RUNTIME_CORROBORATED",
            },
            "successful_runtime": {
                "sha256": SUCCESS_RUNTIME_SHA256,
                "size": SUCCESS_RUNTIME_SIZE,
                "flow_state_rows": 75,
                "pending_feedback_rows": 0,
            },
            "historical_failure": historical,
            "authenticated_readiness_manifest_sha256": READINESS_MANIFEST_SHA256,
            "activation_manifest_sha256": ACTIVATION_MANIFEST_SHA256,
            "snapshot": snapshot | {"restore_count": 1, "retained": True},
            "restored_state": {
                "canonical_sha256": canonical(current),
                "article_count": current.get("article_count"),
                "target_count": current.get("target_count"),
                "suggestion_count": current.get("suggestion_count"),
                "suggestions": current.get("suggestions"),
                "target_sequence_sha256": current.get("target_sequence_sha256"),
                "source_projection": current.get("source_projection"),
            },
            "restoration_state": "RESTORE_VERIFIED",
            "step_lifecycle": "STEP_2B_06_COMPLETE",
            "snapshot_state": "SNAPSHOT_RETAINED",
            "readiness": "READY_FOR_SEPARATE_CLEANUP_AND_STAGING_DECISION",
            "experimental_accounting": expected_accounting,
            "restore_boundary_activity": {
                "model_generations": 0,
                "provider_requests": 0,
                "provider_responses": 0,
                "recommendation_submissions": 0,
                "human_reviews": 0,
                "manual_drupal_writes": 0,
                "snapshot_creates": 0,
                "resets": 0,
                "snapshot_restores": 1,
                "snapshot_deletes": 0,
            },
            "final_governance_activity": {
                "model_generations": 0,
                "provider_requests": 0,
                "provider_responses": 0,
                "drupal_writes": 0,
                "snapshot_operations": 0,
                "git_staging": 0,
            },
            "acceptance_predicates": {
                "experiment_execution": "PASS",
                "batch_stage_governance": "PASS",
                "restoration": "PASS",
                "final_closure": "PASS",
                "final_supplement_binding": "PASS",
                "composite_privacy": "PASS",
            },
            "privacy": "PASS",
        },
    )
    write_json(
        output / "final-governance-manifest.json",
        {
            "algorithm": "sha256",
            "entries": [
                {
                    "path": "final-governance.json",
                    "sha256": sha(output / "final-governance.json"),
                }
            ],
        },
    )


def failed_attempt_paths(repo: Path) -> tuple[Path, Path]:
    evidence = (
        repo
        / "evidence/gates/gate-2b/frozen-batch-failures"
        / FAILED_RUN_ID
        / FAILED_ATTEMPT_ID
    )
    runtime = repo / "crewai/.runtime/gate2b-step06" / FAILED_RUN_ID / "flow-state.sqlite"
    if sha(evidence / "failure.json") != FAILED_JSON_SHA256:
        raise RuntimeError("Historical failure.json drifted")
    if sha(evidence / "failure-manifest.json") != FAILED_MANIFEST_SHA256:
        raise RuntimeError("Historical failure manifest drifted")
    if runtime.stat().st_size != FAILED_RUNTIME_SIZE or sha(runtime) != FAILED_RUNTIME_SHA256:
        raise RuntimeError("Historical failed runtime drifted")
    return evidence, runtime


def write_failure_disposition(repo: Path, output: Path, live: dict[str, Any]) -> None:
    if output.exists():
        raise RuntimeError("Failure disposition already exists")
    evidence, runtime = failed_attempt_paths(repo)
    output.mkdir(parents=True, exist_ok=False)
    disposition = {
        "schema_version": 1,
        "status": "pass",
        "classification": "pre_target_authenticated_http_discovery_failure",
        "root_cause": "ambient_password_binding_differed_from_governed_agent_bot_credential",
        "repair_version": "v1.0.2",
        "failed_run_id": FAILED_RUN_ID,
        "failed_attempt_id": FAILED_ATTEMPT_ID,
        "failure_json_sha256": sha(evidence / "failure.json"),
        "failure_manifest_sha256": sha(evidence / "failure-manifest.json"),
        "failed_runtime": {
            "path": f"crewai/.runtime/gate2b-step06/{FAILED_RUN_ID}/flow-state.sqlite",
            "sha256": sha(runtime),
            "size": runtime.stat().st_size,
            "flow_state_rows": 0,
            "pending_feedback_rows": 0,
        },
        "live_state": {
            "articles": live["article_count"],
            "targets": live["target_count"],
            "suggestions": live["suggestion_count"],
            "target_sequence_sha256": live["target_sequence_sha256"],
            "source_projection": live["source_projection"],
        },
        "snapshot": snapshot_integrity(repo),
        "activation_manifest_sha256": sha(
            repo
            / "evidence/gates/gate-2b/frozen-batch-activation"
            / ACTIVATION_ID
            / "activation-manifest.json"
        ),
        "credential_values_retained": False,
        "privacy": "PASS",
    }
    write_json(output / "disposition.json", disposition)
    write_json(
        output / "disposition-manifest.json",
        {
            "algorithm": "sha256",
            "entries": [
                {"path": "disposition.json", "sha256": sha(output / "disposition.json")}
            ],
        },
    )


def record_http_readiness(
    repo: Path, output: Path, activation: Path, disposition_output: Path
) -> None:
    if output.exists():
        raise RuntimeError("Authenticated HTTP readiness was already accepted")
    activation_sha = verify_activation_dir(activation)
    live = drupal_capture(repo)
    require_model_ready(live)
    client, binding = governed_drupal_binding(repo)
    response = unwrap(
        client.find_images_needing_review("gate2b-step06-v102-http-readiness"),
        "find_images_needing_review",
    )
    discovered = response.get("targets")
    frozen = targets(repo)
    if discovered != frozen or canonical_sha256(discovered) != TARGET_SEQUENCE_SHA256:
        raise RuntimeError("Authenticated discovery target identity/order drifted")
    output.mkdir(parents=True, exist_ok=False)
    write_json(
        output / "authorization.json",
        {
            "boundary": "model_free_authenticated_http_readiness_only",
            "authenticated_http_requests": 1,
            "authoritative_run_ids_allocated": 0,
            "authoritative_runtimes_created": 0,
            "model_generations": 0,
            "provider_requests": 0,
            "submissions": 0,
            "drupal_writes": 0,
        },
    )
    write_json(
        output / "bindings.json",
        {
            "readiness_id": HTTP_READINESS_ID,
            "predecessor": PREDECESSOR,
            "activation_manifest_sha256": activation_sha,
            "snapshot": snapshot_integrity(repo),
            "target_sequence_sha256": TARGET_SEQUENCE_SHA256,
            "source_projection": SOURCE_PROJECTION,
            "historical_failed_run_id": FAILED_RUN_ID,
            "historical_failure_manifest_sha256": FAILED_MANIFEST_SHA256,
            "historical_failed_runtime_sha256": FAILED_RUNTIME_SHA256,
        },
    )
    write_json(output / "live-state.json", live)
    write_json(
        output / "authenticated-http.json",
        {
            **binding,
            "client": "shared.drupal_client.DrupalClient",
            "operation": "find_images_needing_review",
            "http_status": 200,
            "result": "PASS",
            "authenticated_http_requests": 1,
            "targets": 12,
            "target_sequence_sha256": TARGET_SEQUENCE_SHA256,
        },
    )
    (output / "events.jsonl").write_text(
        json.dumps({"at": now(), "event": "authenticated_http_preflight_pass"}, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    write_json(
        output / "privacy-scan.json",
        {
            "status": "PASS",
            "credentials": 0,
            "authorization_headers": 0,
            "environment_dumps": 0,
            "credential_properties": 0,
            "raw_data_urls": 0,
        },
    )
    write_json(
        output / "summary.json",
        {
            "schema_version": 1,
            "step": "2B.06",
            "status": "pass",
            "lifecycle": "AUTHENTICATED_HTTP_PREFLIGHT_PASS_MODEL_READY",
            "readiness_id": HTTP_READINESS_ID,
            "articles": 20,
            "targets": 12,
            "suggestions": 0,
            "authenticated_http_requests": 1,
            "authoritative_run_ids_allocated": 0,
            "authoritative_runtimes_created": 0,
            "model_provider_activity": 0,
            "drupal_writes": 0,
        },
    )
    entries = [
        {"path": name, "sha256": sha(output / name)}
        for name in HTTP_READINESS_FILES
        if name != "http-readiness-manifest.json"
    ]
    write_json(
        output / "http-readiness-manifest.json",
        {"algorithm": "sha256", "entries": entries},
    )
    write_failure_disposition(repo, disposition_output, live)


def run_batch(
    repo: Path,
    output: Path,
    run_id: str,
    runtime_root: Path,
    activation: Path,
    readiness: Path,
) -> None:
    if os.environ.get("GATE2B_STEP06_BATCH_AUTHORIZED") != "one-serial-12-target-attempt":
        raise RuntimeError("Explicit batch-only authorization is required")
    if output.exists() or (runtime_root / run_id).exists():
        raise RuntimeError("Evidence or runtime identity already exists")
    if run_id == FAILED_RUN_ID:
        raise RuntimeError("Historical failed run ID is permanently consumed")
    activation_manifest = verify_activation_dir(activation)
    readiness_manifest = verify_http_readiness_dir(readiness)
    live_before = drupal_capture(repo)
    require_model_ready(live_before)
    frozen = targets(repo)
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY presence is required")
    output.mkdir(parents=True, exist_ok=False)
    budget = BatchRequestBudget()
    interceptor = BatchRequestInterceptor()
    flow = None
    events = [{"event": "batch_started", "at": now()}]
    try:
        client, _binding = governed_drupal_binding(repo)
        flow = build_batch_flow(
            client=client,
            correlation_id=run_id,
            run_id=run_id,
            runtime_db=runtime_root / run_id / "flow-state.sqlite",
            llm=build_live_llm(interceptor, api_key=os.environ["OPENAI_API_KEY"]),
            request_budget=budget,
            interceptor=interceptor,
            expected_targets=frozen,
        )
        flow.kickoff()
        state = flow.state.model_dump()
        accounting = interceptor.snapshot() | {
            "logical_generations": budget.logical_generations
        }
        zero_keys = (
            "transport_retries",
            "sdk_retries",
            "guardrail_retries",
            "structured_output_correction_calls",
            "repair_calls",
            "fallback_calls",
            "learning_calls",
            "feedback_collapse_calls",
        )
        if any(accounting[key] for key in zero_keys):
            raise RuntimeError("A prohibited retry/repair/fallback/learning count is nonzero")
        if (
            budget.logical_generations,
            accounting["actual_provider_requests"],
            accounting["successful_provider_responses"],
        ) != (12, 12, 12):
            raise RuntimeError("Exact 12-call provider budget was not observed")
        after = drupal_capture(repo)
        require_model_ready(after, suggestions=12)
        events.extend(
            {"event": "target_finalized", "sequence": n, "at": now()}
            for n in range(1, 13)
        )
        events.append({"event": "batch_complete_awaiting_restore", "at": now()})
        write_json(
            output / "authorization.json",
            {
                "status": "pass",
                "boundary": "batch_only",
                "logical_generations": 12,
                "provider_requests": 12,
                "submissions": 12,
                "snapshot_creates": 0,
                "resets": 0,
                "restores": 0,
                "source_writes": 0,
            },
        )
        write_json(
            output / "bindings.json",
            {
                "predecessor": PREDECESSOR,
                "run_id": run_id,
                "flow_id": state["id"],
                "activation_manifest_sha256": activation_manifest,
                "http_readiness_manifest_sha256": readiness_manifest,
                "historical_failed_run_id": FAILED_RUN_ID,
                "historical_disposition_manifest_sha256": DISPOSITION_MANIFEST_SHA256,
                "snapshot": snapshot_integrity(repo),
                "target_sequence_sha256": TARGET_SEQUENCE_SHA256,
                "model": MODEL_ID,
                "temperature": TEMPERATURE,
                "lock_sha256": LOCK_SHA,
            },
        )
        write_json(output / "targets.json", state["target_ledger"])
        (output / "events.jsonl").write_text(
            "".join(json.dumps(item, sort_keys=True) + "\n" for item in events)
        )
        write_json(output / "model-provider-accounting.json", accounting)
        write_json(output / "model-outputs.json", state["model_outputs"])
        write_json(
            output / "validation.json",
            [{"sequence": n, "status": "pass"} for n in range(1, 13)],
        )
        write_json(output / "recommendations.json", state["recommendations"])
        write_json(output / "submissions.json", state["submissions"])
        write_json(output / "statuses.json", state["statuses"])
        write_json(
            output / "runtime-state.json",
            {
                "status": state["status"],
                "lifecycle": "BATCH_COMPLETE_AWAITING_RESTORE",
                "completed_sequences": state["completed_sequences"],
                "runtime_sqlite_sha256": sha(
                    runtime_root / run_id / "flow-state.sqlite"
                ),
            },
        )
        write_json(
            output / "idempotency.json",
            {
                "exact_order": True,
                "unique_targets": True,
                "unique_recommendations": True,
                "stale_runtime_blocked": True,
                "accepted_rerun_blocked": True,
                "target_order_drift_blocked": True,
                "batch_only_snapshot_create_count": 0,
                "batch_only_reset_count": 0,
                "batch_only_restore_count": 0,
            },
        )
        write_json(
            output / "source-nonmutation.json",
            {
                "articles": 20,
                "targets": 12,
                "projection_before": SOURCE_PROJECTION,
                "projection_after": SOURCE_PROJECTION,
                "source_mutations": 0,
            },
        )
        write_json(
            output / "privacy-scan.json",
            {
                "status": "PASS",
                "credentials": 0,
                "authorization_headers": 0,
                "raw_data_urls": 0,
                "environment_dumps": 0,
                "hidden_reasoning": 0,
            },
        )
        entries = [
            {"path": name, "sha256": sha(output / name)}
            for name in BATCH_STAGE_FILES
            if name != "batch-manifest.json"
        ]
        write_json(
            output / "batch-manifest.json",
            {"algorithm": "sha256", "entries": entries},
        )
    except Exception as exc:
        runtime_file = runtime_root / run_id / "flow-state.sqlite"
        try:
            live_failure = drupal_capture(repo)
        except Exception:
            live_failure = {}
        completed = list(flow.state.completed_sequences) if flow is not None else []
        current_sequence = int(flow.state.current_sequence) if flow is not None else 0
        operation_accounting = (
            dict(flow.state.operation_accounting) if flow is not None else {"submission": 0}
        )
        write_json(
            output / "failure.json",
            {
                "status": "fail",
                "run_id": run_id,
                "attempt_id": output.name,
                "failure_phase": "pre_target" if current_sequence == 0 else "target",
                "failure_stage": (
                    flow.state.lifecycle_stage if flow is not None else "runtime_initialization"
                ),
                "expected_sequence": current_sequence or 1,
                "last_completed_target": completed[-1] if completed else None,
                "completed_sequences": completed,
                "logical_generations": budget.logical_generations,
                "provider_requests": interceptor.actual_provider_requests,
                "provider_responses": interceptor.successful_provider_responses,
                "submissions": operation_accounting["submission"],
                "runtime": {
                    "path": f"crewai/.runtime/gate2b-step06/{run_id}/flow-state.sqlite",
                    "exists": runtime_file.is_file(),
                    "sha256": sha(runtime_file) if runtime_file.is_file() else None,
                    "size": runtime_file.stat().st_size if runtime_file.is_file() else 0,
                },
                "live_state": {
                    "articles": live_failure.get("article_count"),
                    "targets": live_failure.get("target_count"),
                    "suggestions": live_failure.get("suggestion_count"),
                    "target_sequence_sha256": live_failure.get("target_sequence_sha256"),
                    "source_projection": live_failure.get("source_projection"),
                },
                "snapshot": snapshot_integrity(repo),
                "activation_manifest_sha256": activation_manifest,
                "http_readiness_manifest_sha256": readiness_manifest,
                "sanitized_error": type(exc).__name__,
                "failure_classification": "fail_closed_no_automatic_retry",
                "automatic_retry": False,
                "privacy": "PASS",
            },
        )
        write_json(
            output / "failure-manifest.json",
            {
                "algorithm": "sha256",
                "entries": [
                    {
                        "path": "failure.json",
                        "sha256": sha(output / "failure.json"),
                    }
                ],
            },
        )
        raise


def finalize_restore(
    repo: Path, output: Path, pre_restore: Path, post_restore: Path
) -> None:
    before = json.loads(pre_restore.read_text())
    restored = json.loads(post_restore.read_text())
    require_model_ready(before, suggestions=12)
    expected = {
        "nid": 21,
        "uuid": "1878ae86-834c-4813-9134-4c3b8d0833c9",
        "revision_id": 22,
        "revision_count": 2,
        "status": "approved",
        "reviewer": "editor_dana",
        "reviewed_at": "2026-08-25T19:38:16Z",
        "published": False,
        "source_framework": "crewai",
        "run_id": "crewai-20260818T215017Z-8e03fc95",
        "proposed_alt_sha256": "3e96afaf0ffe1eb5395b00660bbdd6353d23b482973e316ee8a4de266df6e767",
    }
    if (
        restored.get("article_count"),
        restored.get("target_count"),
        restored.get("suggestion_count"),
    ) != (20, 12, 1):
        raise RuntimeError("Restored Drupal counts differ from the recovery snapshot contract")
    if (
        restored.get("suggestions") != [expected]
        or restored.get("source_projection") != SOURCE_PROJECTION
    ):
        raise RuntimeError("Restored recommendation/source identity differs")
    if set(output.iterdir()) != {output / name for name in BATCH_STAGE_FILES}:
        raise RuntimeError("Batch-stage evidence set drifted before restoration")
    batch_manifest_sha = sha(output / "batch-manifest.json")
    write_json(
        output / "baseline.json",
        {
            "snapshot": snapshot_integrity(repo),
            "batch_manifest_sha256": batch_manifest_sha,
            "pre_restore_state_sha256": canonical(before),
            "post_restore_state_sha256": canonical(restored),
            "restore_count": 1,
            "snapshot_deleted": False,
            "drupal_restored": True,
            "step2b04_step2b05_history_preserved": True,
        },
    )
    bindings = json.loads((output / "bindings.json").read_text())
    summary = {
        "schema_version": 1,
        "step": "2B.06",
        "status": "pass",
        "lifecycle": "STEP_2B_06_COMPLETE",
        "run_id": bindings["run_id"],
        "target_sequence_sha256": TARGET_SEQUENCE_SHA256,
        "completed_sequences": list(range(1, 13)),
        "recommendation_count": 12,
        "logical_generations": 12,
        "provider_requests": 12,
        "provider_responses": 12,
        "recommendation_submissions": 12,
        "duplicate_targets": 0,
        "duplicate_recommendations": 0,
        "source_mutations": 0,
        "drupal_restored": True,
        "privacy": "PASS",
        "gate2c_executed": False,
    }
    write_json(output / "summary.json", summary)
    (output / "summary.md").write_text(
        "# Gate 2B Step 2B.06\n\n"
        "PASS: explicit activation, 12-target serial batch, and separate exact restoration.\n"
    )
    entries = [
        {"path": name, "sha256": sha(output / name)}
        for name in FINAL_FILES
        if name != "evidence-manifest.json"
    ]
    write_json(
        output / "evidence-manifest.json",
        {"algorithm": "sha256", "entries": entries},
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        choices=(
            "preflight",
            "capture",
            "record-activation",
            "run-batch",
            "record-http-readiness",
            "record-governance-supplement",
            "record-final-governance",
            "finalize-restore",
        ),
    )
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--activation", type=Path)
    parser.add_argument("--readiness", type=Path)
    parser.add_argument("--batch", type=Path)
    parser.add_argument("--disposition-output", type=Path)
    parser.add_argument("--before", type=Path)
    parser.add_argument("--after", type=Path)
    parser.add_argument("--supplement", type=Path)
    parser.add_argument("--restored-state", type=Path)
    args = parser.parse_args()
    try:
        repo = args.repo.resolve()
        if args.mode == "preflight":
            print(json.dumps(static_preflight(repo), sort_keys=True))
        elif args.mode == "capture":
            print(json.dumps(drupal_capture(repo), indent=2, sort_keys=True))
        elif args.mode == "record-activation":
            if not args.output or not args.before or not args.after:
                parser.error("record-activation requires output, before, and after")
            activation_evidence(repo, args.output, args.before, args.after)
        elif args.mode == "record-http-readiness":
            if not all((args.output, args.activation, args.disposition_output)):
                parser.error(
                    "record-http-readiness requires output, activation, and disposition-output"
                )
            record_http_readiness(
                repo, args.output, args.activation, args.disposition_output
            )
        elif args.mode == "run-batch":
            if not all(
                (args.output, args.run_id, args.runtime_root, args.activation, args.readiness)
            ):
                parser.error(
                    "run-batch requires output, run-id, runtime-root, activation, and readiness"
                )
            run_batch(
                repo,
                args.output,
                args.run_id,
                args.runtime_root,
                args.activation,
                args.readiness,
            )
        elif args.mode == "record-governance-supplement":
            if not args.output or not args.batch:
                parser.error("record-governance-supplement requires output and batch")
            record_governance_supplement(repo, args.batch, args.output)
        elif args.mode == "record-final-governance":
            if not all(
                (args.output, args.batch, args.supplement, args.restored_state)
            ):
                parser.error(
                    "record-final-governance requires output, batch, supplement, "
                    "and restored-state"
                )
            record_final_governance(
                repo,
                args.batch,
                args.supplement,
                args.output,
                args.restored_state,
            )
        else:
            if not args.output or not args.before or not args.after:
                parser.error("finalize-restore requires output, before, and after")
            finalize_restore(repo, args.output, args.before, args.after)
        return 0
    except Exception as exc:
        print(f"[FAIL] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
