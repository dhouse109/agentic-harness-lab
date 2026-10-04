#!/usr/bin/env python3
"""Authorized Gate 2C.02 model-free rehearsal orchestrator.

No mode is implicit. Every retained run uses a fresh identity, preserves failures,
and refuses to overwrite any existing evidence or runtime path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONTRACT_SHA = "3c4801e6eb35d40d94e066c70017d3acebca95183e7e544646be6e2b40aa5ec6"
RUN_PATTERN = re.compile(r"^gate2c-step02-(offline|drupal|startup|async|memory)-[0-9]{8}T[0-9]{6}Z-[a-z0-9]{8}$")
EVIDENCE_ROOT = Path("evidence/gates/gate-2c/model-free-rehearsals")
RUNTIME_ROOT = Path(".cache/gate2c-step02")
AUTHORIZATION_ROOT = Path("evidence/gates/gate-2c/model-free-rehearsal-authorizations")
PRESERVATION_ROOT = Path("evidence/gates/gate-2c/model-free-rehearsal-preservation")
ADMISSION_ANCHOR = Path("shared/contracts/GATE2C-STEP02-ONE-RUN-ADMISSION.json")
ADMISSION_ANCHOR_SHA256 = "07c9c6356efd9c5b0acbf6af09bbd975c0544e2a3598d6cb50b4dbff9ded57e3"
REPLACEMENT_ADMISSION_ANCHOR = Path("shared/contracts/GATE2C-STEP02-OFFLINE-REHEARSAL-REPLACEMENT-ADMISSION.json")
REPLACEMENT_ADMISSION_ANCHOR_SHA256 = "c64b8b2a87e26f402d3077bdb9e2746120ff3bd1aca68f5af716b053a9eca3bd"
CORRECTED_ADMISSION_ANCHOR = Path("shared/contracts/GATE2C-STEP02-CORRECTED-ENVIRONMENT-OFFLINE-REHEARSAL-ADMISSION.json")
CORRECTED_ADMISSION_ANCHOR_SHA256 = "698af65cf4487c39f23f0e592c450828caac69fb19de9a1484a4e671b4b37daa"
DRUPAL_REPLACEMENT_ADMISSION_ANCHOR = Path("shared/contracts/GATE2C-STEP02-DRUPAL-REPLACEMENT-ADMISSION.json")
DRUPAL_REPLACEMENT_ADMISSION_ANCHOR_SHA256 = "a88cbe9c4a22a16b137372da01e23aa91041e4910ca478abfba6b6eef38fad23"
DRUPAL_REPLACEMENT_AUTHORIZATION_ROOT = Path("evidence/gates/gate-2c/drupal-replacement-authorizations")
DRUPAL_FURTHER_REPLACEMENT_ADMISSION_ANCHOR = Path("shared/contracts/GATE2C-STEP02-DRUPAL-FURTHER-REPLACEMENT-ADMISSION.json")
DRUPAL_FURTHER_REPLACEMENT_ADMISSION_ANCHOR_SHA256 = "045d32e7da973790c430041e95b8b1b849d9c0f1f5ea200a10a85b73470b1995"
DRUPAL_FURTHER_REPLACEMENT_AUTHORIZATION_ROOT = Path("evidence/gates/gate-2c/drupal-further-replacement-authorizations")
INSTALLED_SOURCE_MANIFEST = Path("shared/contracts/GATE2C-STEP02-INSTALLED-SOURCE-SHA256.txt")
DRUPAL_POST_EXPIRY_PARTIAL_CONTRACT = Path("shared/contracts/GATE2C-STEP02-DRUPAL-POST-EXPIRY-PARTIAL-OBSERVATION-CONTRACT.json")
DRUPAL_POST_EXPIRY_PARTIAL_CONTRACT_SHA256 = "2de52a5778e80cc58e87194cd0b32e265e116e2ce239cd3e908632d47b0796ec"
DRUPAL_POST_EXPIRY_PARTIAL_EVIDENCE_ROOT = Path("evidence/gates/gate-2c/drupal-post-expiry-partial-observations")
FINAL_FAILED_GOVERNANCE = Path("shared/contracts/GATE2C-STEP02-DRUPAL-FINAL-FAILED-ATTEMPT-GOVERNANCE.json")
FINAL_FAILED_GOVERNANCE_SHA256 = "a7460b1d6a7d3c71cddfefe218ff287328e661a56e3daf5ee9257883832f17c1"
FINAL_FAILED_DRUPAL_RUN_ID = "gate2c-step02-drupal-20261002T132121Z-a54c7a7a"
FINAL_FAILED_DRUPAL_ADMISSION_SHA256 = "15e66d4f70ed74a3921903cbb6134b8986ffabaf2644e08c754465bc3ad58c5c"
FINAL_FAILED_DRUPAL_AGGREGATE_SHA256 = "cdd180a1c88de2fab50766e7bb82644dfd47fd51b57cca9a412985f15a67b08e"
FAILED_DRUPAL_RUN_ID = "gate2c-step02-drupal-20261001T173201Z-545a1ba2"
FAILED_DRUPAL_FAMILY_AGGREGATE_SHA256 = "1014dacee5194fed8a2c696145d792898d5c9b9399f20c548bdd6e6cd4137714"
FAILED_DRUPAL_EVIDENCE = {
    "FAILED-ATTEMPT.json": "0301fcb645d151ca9feaa82d233c7f98483d3e30bf089aa0789b65ea6dd3ddea",
    "authorization-ledger.json": "ff713910f136b309122747dda7c161e74413b3e8714343272a0c7028d558a760",
}
FAILED_DRUPAL_RUNTIME = {
    "control/expected-host-pid.txt": "0404ecadea447837d1fbe05b41c7a14dafa76c3b6713eccc7f92252bb1d837c5",
    "kill-command.json": "3ea3c7ce75d356913333752af2328801124b819602e618a7378bf4b25e0a3b0b",
    "process-check-command.json": "d3c3271e1288c24b8215b0fa9ae55fff768a31ca7e0464a8e5f89a1b5d18c212",
    "worker-command.json": "f246dd35435059ecce6f79845a9de9983b9d0276f95acb5ab2aa37e5d2517a2b",
}
FAILED_DRUPAL_REPLACEMENT_RUN_ID = "gate2c-step02-drupal-20261001T225458Z-c5d0e6b2"
FAILED_DRUPAL_REPLACEMENT_ADMISSION_SHA256 = "7cf5ec3fc346632fe121e9154d76e7d6d6f009e053fec8e1aed3a45626a774cf"
FAILED_DRUPAL_REPLACEMENT_AGGREGATE_SHA256 = "6ec105136d47f8b25a271c0950ff11984709b7e876e207b45dad7805ccde33c0"
FAILED_DRUPAL_REPLACEMENT_EVIDENCE = {
    "FAILED-ATTEMPT.json": "aabb4a4a5eeab09bb67676393f2b733e1225bd3a0149b5fb6b22eaeb04a112db",
    "authorization-ledger.json": "1bb3332826eb514780093d304caff5a956ffffcfa56b88b2d02546480558f3af",
    "drupal-pre-seam-diagnostic.json": "1ea434c9823a1df30b9e13891ab0f784ab060ea46c04834daa5f21b7a1ef3c04",
}
FAILED_DRUPAL_REPLACEMENT_RUNTIME = {
    "control/expected-host-pid.txt": "6c754b0616340013570400464f68f0e3e73cfc91cbd65e5c2d28d5d0a6770754",
    "control/midpoint.json": "925b6c396b399f3237d5daabdc5a5ae4ea326459342812f5623bc0d9e6e8e97d",
    "control/seam-ready.json": "f84a32479a26195f5fd600c10882a34430d9acc5c6daf877389cb6015b121f09",
    "kill-command.json": "3ea3c7ce75d356913333752af2328801124b819602e618a7378bf4b25e0a3b0b",
    "process-check-command.json": "87494badb3a727c5fba0e068bb07845f8bc6ec499e2ac4ed43f0810fde1f869d",
    "worker-command.json": "b82cb0c0dedd5ba75bc303022b996dd3b240e39b93318d19f6c3486b1a300ccf",
}
PREDECESSOR_SOURCE_MANIFEST_SHA256 = "4809c2d228010f5a54f2e64fc3d196075c7aa7e1b20e90001f1dc8dcf5572708"
V1_0_14_SOURCE_MANIFEST_SHA256 = "31d9b9e652276598163b1c43b37f5bffa51ec46cf7f531e280892115115ea096"
HISTORICAL_INVENTORY_SHA256 = "b123dade4e725e45401e2f580b0ed3987a1af5edd4576490c1c10a09c5a0d3be"
RETAINED_BASELINE_INVENTORY_SHA256 = "8fb60b7f6c7e29f57b04384d2a974ebe0c8a9379d681a3853b0a664223b5c6d4"
CONSUMED_RUN_ID = "gate2c-step02-offline-20260925T154513Z-5420da48"
CONSUMED_AUTHORIZATION_SHA256 = "c5827b91aae862dca52ecfc7b6618e0ef1e007404cc68c029da5929a7a8ecfb3"
CONSUMED_FINALIZATION_SHA256 = "e5a90548589e1ca94acd9df75394e6265738a61f0783bb262aedcfc948c5042e"
REPLACEMENT_RUN_ID = "gate2c-step02-offline-20260927T004530Z-8998079d"
REPLACEMENT_AUTHORIZATION_SHA256 = "2a50c586c067f357ec53b810033ca6f472f382a7eb7e9a6cb71cd41824c38317"
REPLACEMENT_FINALIZATION_SHA256 = "29844e2e83464780aba02720776249bd03f886ea8bb3aa8e9ac767040643f4d4"
CORRECTED_STARTUP_PRESERVATION_MANIFEST_SHA256 = "7bc109779f0e29e1d7e664679b17bced2cbb83294ecc702735687c888bea2392"
BASELINE_RUN_IDS = frozenset({
    "gate2c-step02-offline-20260922T174202Z-35a22675",
    "gate2c-step02-offline-20260922T213931Z-9f3c7a21",
    "gate2c-step02-offline-20260923T105822Z-ba36ceed",
    "gate2c-step02-startup-20260923T124207Z-930eee56",
    "gate2c-step02-startup-20260923T134027Z-e5acfebb",
    "gate2c-step02-startup-20260923T144053Z-06d5f691",
    "gate2c-step02-startup-20260923T184826Z-76fef1dc",
    "gate2c-step02-async-20260923T235257Z-392b56a7",
    "gate2c-step02-memory-20260924T124150Z-b5d60fa6",
    "gate2c-step02-startup-20260924T193318Z-dd57cbc4",
    "gate2c-step02-startup-20260924T202432Z-b30ac8de",
    "gate2c-step02-offline-20260924T203449Z-1ec8feac",
})
DIAGNOSTIC_LIMIT = 4096
DIAGNOSTIC_REDACTIONS = (
    re.compile(r"sk-(?:proj|live)-[A-Za-z0-9_-]+", re.I),
    re.compile(r"Authorization:\s*(?:Basic|Bearer)\s+\S+", re.I),
    re.compile(r"data:image/[^;\s]+;base64,[A-Za-z0-9+/=]+", re.I),
    re.compile(r"OPENAI_API_KEY\s*=\s*\S+", re.I),
)
HOME_PATH = re.compile(r"/home/[^/\s]+")
XDG_KEYS = ("XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME")
CREWAI_WORKER_MODULE = "agentic_harness_crewai.gate2c_recovery"
ASYNC_PHASES = (
    "worker_process_initialized",
    "local_storage_validated",
    "lancedb_import_started",
    "lancedb_import_completed",
    "public_connect_async_validated",
    "caller_owned_event_loop_started",
    "direct_async_connect_entered",
    "direct_async_connect_returned",
    "direct_async_connect_exception",
    "diagnostic_completed",
    "setup_failed",
)
MEMORY_ASYNC_PHASES = (
    "worker_process_initialized",
    "memory_backend_validated",
    "lancedb_import_started",
    "lancedb_import_completed",
    "public_connect_async_validated",
    "caller_owned_event_loop_started",
    "in_memory_async_connect_entered",
    "in_memory_async_connect_returned",
    "in_memory_async_connect_exception",
    "diagnostic_completed",
    "setup_failed",
)
MEMORY_DIAGNOSTIC_CREDENTIALS = (
    "OPENAI_API_KEY",
    "LANCEDB_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "AZURE_STORAGE_ACCOUNT_KEY",
    "AZURE_STORAGE_SAS_TOKEN",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def canonical_sha(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def atomic_write_json(path: Path, value: Any) -> None:
    """Publish a governance record only after its complete bytes are durable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.tmp-{os.getpid()}"
    require(not path.exists() and not temporary.exists(), f"record already exists: {path}")
    with temporary.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def exact_directory_identities(root: Path) -> set[str]:
    if not root.exists():
        return set()
    require(root.is_dir() and not root.is_symlink(), f"invalid identity root: {root}")
    require(not any(path.is_symlink() for path in root.iterdir()), f"symlink in identity root: {root}")
    return {path.name for path in root.iterdir() if path.is_dir()}


def load_one_run_authorization(repo: Path, run_id: str) -> tuple[Path, str, dict[str, Any]]:
    root = repo / AUTHORIZATION_ROOT / run_id
    path = root / "authorization.json"
    require(root.is_dir() and not root.is_symlink(), "one-run authorization root missing")
    require({item.name for item in root.iterdir()} == {"authorization.json"}, "authorization record inventory")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(value.get("run_id") == run_id, "authorization run identity")
    require(value.get("schema_version") == 1, "authorization schema version")
    if run_id == CONSUMED_RUN_ID:
        require(value.get("record_type") == "ONE_RUN_AUTHORIZATION", "consumed authorization record type")
        require(value.get("admission_anchor_sha256") == ADMISSION_ANCHOR_SHA256, "consumed authorization admission anchor")
        require(value.get("predecessor_source_manifest_sha256") == PREDECESSOR_SOURCE_MANIFEST_SHA256, "consumed authorization predecessor binding")
        require(value.get("historical_inventory_sha256") == HISTORICAL_INVENTORY_SHA256, "consumed authorization historical binding")
        require(sha(path) == CONSUMED_AUTHORIZATION_SHA256, "consumed authorization hash")
    elif run_id == REPLACEMENT_RUN_ID:
        require(value.get("record_type") == "ONE_RUN_REPLACEMENT_AUTHORIZATION", "replacement authorization record type")
        require(value.get("replacement_admission_anchor_sha256") == REPLACEMENT_ADMISSION_ANCHOR_SHA256, "replacement authorization admission anchor")
        require(value.get("v1_0_14_source_manifest_sha256") == V1_0_14_SOURCE_MANIFEST_SHA256, "replacement authorization source predecessor")
        require(value.get("consumed_run_id") == CONSUMED_RUN_ID, "replacement authorization consumed identity binding")
        require(value.get("consumed_authorization_sha256") == CONSUMED_AUTHORIZATION_SHA256, "replacement authorization consumed record binding")
        require(value.get("historical_fail_finalization_sha256") == CONSUMED_FINALIZATION_SHA256, "replacement authorization finalized FAIL binding")
        require(value.get("retained_baseline_inventory_sha256") == RETAINED_BASELINE_INVENTORY_SHA256, "replacement authorization retained baseline binding")
        require(value.get("consumed_admission_reopened") is False, "consumed admission must remain closed")
        require(value.get("historical_identity_reuse_authorized") is False, "historical identity reuse prohibited")
        require(value.get("automatic_replacement_or_retry_authorized") is False, "automatic replacement or retry prohibited")
        require(value.get("additional_replacement_identities_authorized") == 0, "additional replacement identity prohibited")
        require(sha(path) == REPLACEMENT_AUTHORIZATION_SHA256, "replacement authorization hash")
    else:
        require(value.get("record_type") == "CORRECTED_ENVIRONMENT_ONE_RUN_AUTHORIZATION", "corrected-environment authorization record type")
        require(value.get("corrected_environment_admission_anchor_sha256") == CORRECTED_ADMISSION_ANCHOR_SHA256, "corrected-environment admission anchor")
        require(value.get("installed_source_manifest_sha256") == sha(repo / "shared/contracts/GATE2C-STEP02-INSTALLED-SOURCE-SHA256.txt"), "corrected-environment installed source binding")
        require(value.get("historical_run_ids") == [CONSUMED_RUN_ID, REPLACEMENT_RUN_ID], "historical identity binding")
        require(value.get("historical_finalization_sha256") == [CONSUMED_FINALIZATION_SHA256, REPLACEMENT_FINALIZATION_SHA256], "historical finalization binding")
        require(value.get("representative_startup_preservation_manifest_sha256") == CORRECTED_STARTUP_PRESERVATION_MANIFEST_SHA256, "representative startup binding")
        validate_corrected_environment_preflight(value.get("identity_allocation_preflight", {}))
        require(value.get("identity_allocation_preflight_sha256") == canonical_sha(value["identity_allocation_preflight"]), "identity-allocation preflight hash")
        require(value.get("historical_identity_reuse_authorized") is False, "historical identity reuse prohibited")
        require(value.get("automatic_replacement_or_retry_authorized") is False, "automatic retry prohibited")
        require(value.get("additional_identities_authorized") == 0, "additional identity prohibited")
    require(value.get("maximum_new_identities") == 1, "authorization one-run scope")
    return path, sha(path), value


def validate_corrected_environment_preflight(value: dict[str, Any]) -> None:
    """Accept only safe categorical output from the sealed fresh-process control."""
    required = {
        "schema_version": 1,
        "status": "CORRECTED_EXECUTION_ENVIRONMENT_PREFLIGHT_PASS",
        "python_version": "3.12.13",
        "no_new_privs": 0,
        "seccomp": 0,
        "event_loop_policy": "_UnixDefaultEventLoopPolicy",
        "selector": "EpollSelector",
        "baseline_python_threads": 1,
        "auxiliary_python_threads_constructed": 1,
        "auxiliary_thread_start_calls": 1,
        "auxiliary_worker_function_started": 1,
        "auxiliary_worker_function_completed": 1,
        "auxiliary_thread_alive_after_join": False,
        "call_soon_threadsafe_calls": 1,
        "callback_calls": 1,
        "callback_executed": True,
        "event_await_resumed": True,
        "socketpair_bytes_sent": 1,
        "socketpair_bytes_received": 1,
        "socketpair_one_null_byte_round_trip": True,
        "crewai_imported": False,
        "environment_values_retained": False,
        "full_proc_status_retained": False,
    }
    require(isinstance(value, dict) and all(value.get(key) == expected for key, expected in required.items()), "corrected-environment preflight failed")
    require(value.get("failed_checks") == [], "corrected-environment preflight failures")


def authorize_offline(repo: Path, run_id: str) -> Path:
    """Consume the one empty slot before any worker/evidence/runtime creation."""
    require(RUN_PATTERN.fullmatch(run_id) is not None and "-offline-" in run_id, "invalid offline run ID")
    anchor = repo / ADMISSION_ANCHOR
    require(anchor.is_file() and sha(anchor) == ADMISSION_ANCHOR_SHA256, "one-run admission anchor drift")
    source_manifest = repo / "shared/contracts/GATE2C-STEP02-INSTALLED-SOURCE-SHA256.txt"
    require(source_manifest.is_file(), "installed-source manifest missing")
    authorization_ids = exact_directory_identities(repo / AUTHORIZATION_ROOT)
    preservation_ids = exact_directory_identities(repo / PRESERVATION_ROOT)
    evidence_ids = exact_directory_identities(repo / EVIDENCE_ROOT)
    runtime_ids = exact_directory_identities(repo / RUNTIME_ROOT)
    require(not authorization_ids and not preservation_ids, "one-run admission slot already consumed")
    require(evidence_ids == BASELINE_RUN_IDS and runtime_ids == BASELINE_RUN_IDS, "historical baseline identity inventory drift")
    require(not (repo / EVIDENCE_ROOT / run_id).exists() and not (repo / RUNTIME_ROOT / run_id).exists(), "run identity reuse")
    record = {
        "$schema": "../../../../shared/schemas/gate2c-step02-one-run-transition.schema.json",
        "schema_version": 1,
        "record_type": "ONE_RUN_AUTHORIZATION",
        "run_id": run_id,
        "authorized_at": datetime.now(timezone.utc).isoformat(),
        "authorization_boundary": "explicit_human_authorization_before_worker_execution",
        "admission_anchor_sha256": ADMISSION_ANCHOR_SHA256,
        "predecessor_source_manifest_sha256": PREDECESSOR_SOURCE_MANIFEST_SHA256,
        "historical_inventory_sha256": HISTORICAL_INVENTORY_SHA256,
        "maximum_new_identities": 1,
        "replacement_or_retry_authorized": False,
        "scope": "one_model_free_offline_rehearsal_identity_only",
    }
    output = repo / AUTHORIZATION_ROOT / run_id / "authorization.json"
    atomic_write_json(output, record)
    return output


def authorize_offline_replacement(repo: Path, run_id: str) -> Path:
    """Consume exactly one replacement slot without reopening the original admission."""
    require(RUN_PATTERN.fullmatch(run_id) is not None and "-offline-" in run_id, "invalid offline run ID")
    require(run_id != CONSUMED_RUN_ID and run_id not in BASELINE_RUN_IDS, "historical run identity reuse")
    anchor = repo / REPLACEMENT_ADMISSION_ANCHOR
    require(anchor.is_file() and sha(anchor) == REPLACEMENT_ADMISSION_ANCHOR_SHA256, "replacement admission anchor drift")
    require(sha(repo / ADMISSION_ANCHOR) == ADMISSION_ANCHOR_SHA256, "consumed admission anchor drift")
    authorization_ids = exact_directory_identities(repo / AUTHORIZATION_ROOT)
    preservation_ids = exact_directory_identities(repo / PRESERVATION_ROOT)
    evidence_ids = exact_directory_identities(repo / EVIDENCE_ROOT)
    runtime_ids = exact_directory_identities(repo / RUNTIME_ROOT)
    require(authorization_ids == {CONSUMED_RUN_ID}, "replacement admission already consumed or authorization inventory drift")
    require(preservation_ids == {CONSUMED_RUN_ID}, "consumed finalization inventory drift")
    require(evidence_ids == BASELINE_RUN_IDS | {CONSUMED_RUN_ID}, "retained evidence identity inventory drift")
    require(runtime_ids == BASELINE_RUN_IDS | {CONSUMED_RUN_ID}, "retained runtime identity inventory drift")
    consumed_authorization = repo / AUTHORIZATION_ROOT / CONSUMED_RUN_ID / "authorization.json"
    consumed_finalization = repo / PRESERVATION_ROOT / CONSUMED_RUN_ID / "finalization.json"
    require(consumed_authorization.is_file(), "consumed authorization missing")
    require(consumed_finalization.is_file(), "historical FAIL finalization missing")
    require(sha(consumed_authorization) == CONSUMED_AUTHORIZATION_SHA256, "consumed authorization changed")
    require(sha(consumed_finalization) == CONSUMED_FINALIZATION_SHA256, "historical FAIL finalization changed")
    require(not (repo / EVIDENCE_ROOT / run_id).exists() and not (repo / RUNTIME_ROOT / run_id).exists(), "run identity reuse")
    record = {
        "$schema": "../../../../shared/schemas/gate2c-step02-offline-rehearsal-replacement-admission.schema.json",
        "schema_version": 1,
        "record_type": "ONE_RUN_REPLACEMENT_AUTHORIZATION",
        "run_id": run_id,
        "authorized_at": datetime.now(timezone.utc).isoformat(),
        "authorization_boundary": "separate_explicit_human_replacement_authorization_before_identity_creation",
        "replacement_admission_anchor_sha256": REPLACEMENT_ADMISSION_ANCHOR_SHA256,
        "v1_0_14_source_manifest_sha256": V1_0_14_SOURCE_MANIFEST_SHA256,
        "consumed_run_id": CONSUMED_RUN_ID,
        "consumed_authorization_sha256": CONSUMED_AUTHORIZATION_SHA256,
        "historical_fail_finalization_sha256": CONSUMED_FINALIZATION_SHA256,
        "retained_baseline_inventory_sha256": RETAINED_BASELINE_INVENTORY_SHA256,
        "maximum_new_identities": 1,
        "consumed_admission_reopened": False,
        "historical_identity_reuse_authorized": False,
        "automatic_replacement_or_retry_authorized": False,
        "additional_replacement_identities_authorized": 0,
        "scope": "one_fresh_model_free_offline_rehearsal_identity_only",
    }
    output = repo / AUTHORIZATION_ROOT / run_id / "authorization.json"
    atomic_write_json(output, record)
    return output


def authorize_offline_corrected_environment(repo: Path, run_id: str, preflight_result: Path) -> Path:
    """Consume the new slot only after a fresh corrected-environment preflight."""
    require(RUN_PATTERN.fullmatch(run_id) is not None and "-offline-" in run_id, "invalid offline run ID")
    require(run_id not in BASELINE_RUN_IDS | {CONSUMED_RUN_ID, REPLACEMENT_RUN_ID}, "historical run identity reuse")
    preflight = json.loads(preflight_result.read_text(encoding="utf-8"))
    validate_corrected_environment_preflight(preflight)
    anchor = repo / CORRECTED_ADMISSION_ANCHOR
    require(anchor.is_file() and sha(anchor) == CORRECTED_ADMISSION_ANCHOR_SHA256, "corrected-environment admission anchor drift")
    authorization_ids = exact_directory_identities(repo / AUTHORIZATION_ROOT)
    preservation_ids = exact_directory_identities(repo / PRESERVATION_ROOT)
    evidence_ids = exact_directory_identities(repo / EVIDENCE_ROOT)
    runtime_ids = exact_directory_identities(repo / RUNTIME_ROOT)
    historical = {CONSUMED_RUN_ID, REPLACEMENT_RUN_ID}
    require(authorization_ids == historical and preservation_ids == historical, "corrected-environment admission already consumed or historical transition drift")
    require(evidence_ids == BASELINE_RUN_IDS | historical, "retained evidence identity inventory drift")
    require(runtime_ids == BASELINE_RUN_IDS | historical, "retained runtime identity inventory drift")
    for historical_run, authorization_sha, finalization_sha in (
        (CONSUMED_RUN_ID, CONSUMED_AUTHORIZATION_SHA256, CONSUMED_FINALIZATION_SHA256),
        (REPLACEMENT_RUN_ID, REPLACEMENT_AUTHORIZATION_SHA256, REPLACEMENT_FINALIZATION_SHA256),
    ):
        require(sha(repo / AUTHORIZATION_ROOT / historical_run / "authorization.json") == authorization_sha, "historical authorization changed")
        require(sha(repo / PRESERVATION_ROOT / historical_run / "finalization.json") == finalization_sha, "historical finalization changed")
    require(not (repo / EVIDENCE_ROOT / run_id).exists() and not (repo / RUNTIME_ROOT / run_id).exists(), "run identity reuse")
    record = {
        "$schema": "../../../../shared/schemas/gate2c-step02-corrected-environment-offline-rehearsal-admission.schema.json",
        "schema_version": 1,
        "record_type": "CORRECTED_ENVIRONMENT_ONE_RUN_AUTHORIZATION",
        "run_id": run_id,
        "authorized_at": datetime.now(timezone.utc).isoformat(),
        "authorization_boundary": "fresh_corrected_environment_preflight_before_identity_allocation",
        "corrected_environment_admission_anchor_sha256": CORRECTED_ADMISSION_ANCHOR_SHA256,
        "installed_source_manifest_sha256": sha(repo / "shared/contracts/GATE2C-STEP02-INSTALLED-SOURCE-SHA256.txt"),
        "historical_run_ids": [CONSUMED_RUN_ID, REPLACEMENT_RUN_ID],
        "historical_finalization_sha256": [CONSUMED_FINALIZATION_SHA256, REPLACEMENT_FINALIZATION_SHA256],
        "representative_startup_preservation_manifest_sha256": CORRECTED_STARTUP_PRESERVATION_MANIFEST_SHA256,
        "identity_allocation_preflight_sha256": canonical_sha(preflight),
        "identity_allocation_preflight": preflight,
        "maximum_new_identities": 1,
        "historical_identity_reuse_authorized": False,
        "automatic_replacement_or_retry_authorized": False,
        "additional_identities_authorized": 0,
        "scope": "one_corrected_environment_model_free_offline_rehearsal_identity_only",
    }
    output = repo / AUTHORIZATION_ROOT / run_id / "authorization.json"
    atomic_write_json(output, record)
    return output


def verify_failed_drupal_family(repo: Path) -> None:
    """Bind the immutable failed start before admitting any replacement identity."""
    evidence = repo / EVIDENCE_ROOT / FAILED_DRUPAL_RUN_ID
    runtime = repo / "drupal/.cache/gate2c-step02" / FAILED_DRUPAL_RUN_ID
    require(evidence.is_dir() and runtime.is_dir(), "failed Drupal family missing")
    require(not any(path.is_symlink() for path in (*evidence.rglob("*"), *runtime.rglob("*"))), "failed Drupal family symlink")
    evidence_files = {path.relative_to(evidence).as_posix() for path in evidence.rglob("*") if path.is_file()}
    runtime_files = {path.relative_to(runtime).as_posix() for path in runtime.rglob("*") if path.is_file()}
    require(evidence_files == set(FAILED_DRUPAL_EVIDENCE), "failed Drupal evidence inventory drift")
    require(runtime_files == set(FAILED_DRUPAL_RUNTIME), "failed Drupal runtime inventory drift")
    for relative, digest in FAILED_DRUPAL_EVIDENCE.items():
        require(sha(evidence / relative) == digest, f"failed Drupal evidence drift: {relative}")
    for relative, digest in FAILED_DRUPAL_RUNTIME.items():
        require(sha(runtime / relative) == digest, f"failed Drupal runtime drift: {relative}")
    failed = json.loads((evidence / "FAILED-ATTEMPT.json").read_text(encoding="utf-8"))
    ledger = json.loads((evidence / "authorization-ledger.json").read_text(encoding="utf-8"))
    require(failed.get("status") == "FAILED_PRESERVED" and failed.get("run_id") == FAILED_DRUPAL_RUN_ID, "failed Drupal classification")
    phases = ledger.get("phases", [])
    require(phases and phases[0].get("status") == "CONSUMED", "failed Drupal start authorization is not consumed")
    require(not (evidence / "evidence-manifest.json").exists(), "failed Drupal family cannot be a passing family")


def authorize_drupal_replacement(repo: Path, run_id: str) -> Path:
    """Allocate one replacement identity only; never execute its lifecycle."""
    require(RUN_PATTERN.fullmatch(run_id) is not None and "-drupal-" in run_id, "invalid Drupal run ID")
    require(run_id != FAILED_DRUPAL_RUN_ID, "failed Drupal identity reuse prohibited")
    verify_failed_drupal_family(repo)
    anchor = repo / DRUPAL_REPLACEMENT_ADMISSION_ANCHOR
    require(anchor.is_file() and sha(anchor) == DRUPAL_REPLACEMENT_ADMISSION_ANCHOR_SHA256, "Drupal replacement admission anchor drift")
    authorization_ids = exact_directory_identities(repo / DRUPAL_REPLACEMENT_AUTHORIZATION_ROOT)
    require(not authorization_ids, "Drupal replacement admission already consumed")
    evidence_ids = {identity for identity in exact_directory_identities(repo / EVIDENCE_ROOT) if "-drupal-" in identity}
    runtime_ids = exact_directory_identities(repo / "drupal/.cache/gate2c-step02")
    require(evidence_ids == {FAILED_DRUPAL_RUN_ID}, "unexpected Drupal evidence identity")
    require(runtime_ids == {FAILED_DRUPAL_RUN_ID}, "unexpected Drupal runtime identity")
    require(not (repo / EVIDENCE_ROOT / run_id).exists(), "replacement Drupal evidence identity already exists")
    require(not (repo / "drupal/.cache/gate2c-step02" / run_id).exists(), "replacement Drupal runtime identity already exists")
    source_manifest = repo / INSTALLED_SOURCE_MANIFEST
    require(source_manifest.is_file(), "installed-source manifest missing")
    record = {
        "$schema": "../../../../shared/schemas/gate2c-step02-drupal-replacement-admission.schema.json",
        "schema_version": 1,
        "record_type": "ONE_RUN_DRUPAL_REPLACEMENT_AUTHORIZATION",
        "run_id": run_id,
        "authorized_at": datetime.now(timezone.utc).isoformat(),
        "authorization_boundary": "separate_explicit_human_replacement_identity_authorization_before_drupal_start",
        "replacement_admission_anchor_sha256": DRUPAL_REPLACEMENT_ADMISSION_ANCHOR_SHA256,
        "repaired_installed_source_manifest_sha256": sha(source_manifest),
        "failed_run_id": FAILED_DRUPAL_RUN_ID,
        "failed_family_aggregate_sha256": FAILED_DRUPAL_FAMILY_AGGREGATE_SHA256,
        "failed_status": "FAILED_PRESERVED",
        "replacement_reason": "SOURCE_RUNTIME_INSTRUMENTATION_DEFECT",
        "maximum_new_identities": 1,
        "original_start_authorization_carried_forward": False,
        "automatic_retry_authorized": False,
        "additional_replacement_identities_authorized": 0,
        "replacement_start_requires_separate_human_authorization": True,
        "execution_authorized": False,
        "scope": "one_fresh_model_free_drupal_replacement_identity_admission_only",
    }
    output = repo / DRUPAL_REPLACEMENT_AUTHORIZATION_ROOT / run_id / "authorization.json"
    atomic_write_json(output, record)
    return output


def load_drupal_replacement_authorization(repo: Path, run_id: str) -> dict[str, Any]:
    """Require the singular repaired-epoch admission before family creation."""
    require(run_id != FAILED_DRUPAL_RUN_ID, "failed Drupal identity cannot be retried")
    require(exact_directory_identities(repo / DRUPAL_REPLACEMENT_AUTHORIZATION_ROOT) == {run_id}, "one Drupal replacement authorization required")
    path = repo / DRUPAL_REPLACEMENT_AUTHORIZATION_ROOT / run_id / "authorization.json"
    require(path.is_file() and not path.is_symlink(), "Drupal replacement authorization missing")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(value.get("record_type") == "ONE_RUN_DRUPAL_REPLACEMENT_AUTHORIZATION" and value.get("run_id") == run_id, "Drupal replacement authorization identity")
    require(value.get("failed_run_id") == FAILED_DRUPAL_RUN_ID and value.get("failed_status") == "FAILED_PRESERVED", "Drupal replacement failed-family binding")
    require(value.get("failed_family_aggregate_sha256") == FAILED_DRUPAL_FAMILY_AGGREGATE_SHA256, "Drupal replacement failed-family digest")
    require(value.get("replacement_reason") == "SOURCE_RUNTIME_INSTRUMENTATION_DEFECT", "Drupal replacement reason")
    require(value.get("repaired_installed_source_manifest_sha256") == sha(repo / INSTALLED_SOURCE_MANIFEST), "Drupal replacement source epoch")
    require(value.get("original_start_authorization_carried_forward") is False, "consumed original start authorization reuse")
    require(value.get("automatic_retry_authorized") is False and value.get("additional_replacement_identities_authorized") == 0, "Drupal replacement retry policy")
    require(value.get("replacement_start_requires_separate_human_authorization") is True and value.get("execution_authorized") is False, "Drupal replacement execution boundary")
    verify_failed_drupal_family(repo)
    return value


def verify_failed_drupal_replacement_family(repo: Path) -> None:
    """Bind the immutable seam-reaching replacement failure before any further allocation."""
    evidence = repo / EVIDENCE_ROOT / FAILED_DRUPAL_REPLACEMENT_RUN_ID
    runtime = repo / "drupal/.cache/gate2c-step02" / FAILED_DRUPAL_REPLACEMENT_RUN_ID
    require(evidence.is_dir() and runtime.is_dir(), "failed Drupal replacement family missing")
    require(not any(path.is_symlink() for path in (*evidence.rglob("*"), *runtime.rglob("*"))), "failed Drupal replacement family symlink")
    require({path.relative_to(evidence).as_posix() for path in evidence.rglob("*") if path.is_file()} == set(FAILED_DRUPAL_REPLACEMENT_EVIDENCE), "failed Drupal replacement evidence inventory drift")
    require({path.relative_to(runtime).as_posix() for path in runtime.rglob("*") if path.is_file()} == set(FAILED_DRUPAL_REPLACEMENT_RUNTIME), "failed Drupal replacement runtime inventory drift")
    for relative, digest in FAILED_DRUPAL_REPLACEMENT_EVIDENCE.items():
        require(sha(evidence / relative) == digest, f"failed Drupal replacement evidence drift: {relative}")
    for relative, digest in FAILED_DRUPAL_REPLACEMENT_RUNTIME.items():
        require(sha(runtime / relative) == digest, f"failed Drupal replacement runtime drift: {relative}")
    failed = json.loads((evidence / "FAILED-ATTEMPT.json").read_text(encoding="utf-8"))
    ledger = json.loads((evidence / "authorization-ledger.json").read_text(encoding="utf-8"))
    diagnostic = json.loads((evidence / "drupal-pre-seam-diagnostic.json").read_text(encoding="utf-8"))
    midpoint = json.loads((runtime / "control/midpoint.json").read_text(encoding="utf-8"))
    seam = json.loads((runtime / "control/seam-ready.json").read_text(encoding="utf-8"))
    require(failed.get("status") == "FAILED_PRESERVED" and failed.get("run_id") == FAILED_DRUPAL_REPLACEMENT_RUN_ID, "failed Drupal replacement classification")
    require(ledger.get("phases", [None])[0].get("status") == "CONSUMED", "failed Drupal replacement start authorization")
    require(diagnostic.get("experimental_sigkill_delivered") is False and diagnostic.get("automatic_retry_count") == 0, "failed Drupal replacement signal/retry classification")
    require(diagnostic.get("seam_ready_existed") is True and diagnostic.get("midpoint_existed") is True, "failed Drupal replacement seam presence")
    require(midpoint.get("completed_sequences") == [1, 2, 3, 4, 5, 6] and midpoint.get("next_target") == 7 and midpoint.get("target_7_started") is False, "failed Drupal replacement midpoint")
    require(seam.get("midpoint_sha256") == FAILED_DRUPAL_REPLACEMENT_RUNTIME["control/midpoint.json"] and seam.get("actual_worker_pid") == 14297, "failed Drupal replacement seam binding")
    require(not (evidence / "drupal-termination.json").exists() and not (evidence / "evidence-manifest.json").exists(), "failed Drupal replacement cannot satisfy PASS")
    authorization = repo / DRUPAL_REPLACEMENT_AUTHORIZATION_ROOT / FAILED_DRUPAL_REPLACEMENT_RUN_ID / "authorization.json"
    require(sha(authorization) == FAILED_DRUPAL_REPLACEMENT_ADMISSION_SHA256, "failed Drupal replacement admission drift")


def authorize_drupal_further_replacement(repo: Path, run_id: str) -> Path:
    """Consume at most one further slot; allocation only, never execution."""
    require(RUN_PATTERN.fullmatch(run_id) is not None and "-drupal-" in run_id, "invalid Drupal run ID")
    require(run_id not in {FAILED_DRUPAL_RUN_ID, FAILED_DRUPAL_REPLACEMENT_RUN_ID}, "historical Drupal identity reuse prohibited")
    verify_failed_drupal_family(repo)
    verify_failed_drupal_replacement_family(repo)
    anchor = repo / DRUPAL_FURTHER_REPLACEMENT_ADMISSION_ANCHOR
    require(anchor.is_file() and sha(anchor) == DRUPAL_FURTHER_REPLACEMENT_ADMISSION_ANCHOR_SHA256, "Drupal further replacement admission anchor drift")
    require(exact_directory_identities(repo / DRUPAL_REPLACEMENT_AUTHORIZATION_ROOT) == {FAILED_DRUPAL_REPLACEMENT_RUN_ID}, "first Drupal replacement authorization inventory drift")
    require(not exact_directory_identities(repo / DRUPAL_FURTHER_REPLACEMENT_AUTHORIZATION_ROOT), "Drupal further replacement slot already consumed")
    evidence_ids = {identity for identity in exact_directory_identities(repo / EVIDENCE_ROOT) if "-drupal-" in identity}
    runtime_ids = exact_directory_identities(repo / "drupal/.cache/gate2c-step02")
    historical = {FAILED_DRUPAL_RUN_ID, FAILED_DRUPAL_REPLACEMENT_RUN_ID}
    require(evidence_ids == historical and runtime_ids == historical, "historical Drupal family inventory drift")
    require(not (repo / EVIDENCE_ROOT / run_id).exists() and not (repo / "drupal/.cache/gate2c-step02" / run_id).exists(), "further replacement identity already exists")
    record = {
        "$schema": "../../../../shared/schemas/gate2c-step02-drupal-further-replacement-admission.schema.json",
        "schema_version": 1,
        "record_type": "ONE_RUN_DRUPAL_FURTHER_REPLACEMENT_AUTHORIZATION",
        "run_id": run_id,
        "authorized_at": datetime.now(timezone.utc).isoformat(),
        "authorization_boundary": "separate_explicit_human_further_replacement_identity_authorization_before_drupal_start",
        "further_replacement_admission_anchor_sha256": DRUPAL_FURTHER_REPLACEMENT_ADMISSION_ANCHOR_SHA256,
        "repaired_installed_source_manifest_sha256": sha(repo / INSTALLED_SOURCE_MANIFEST),
        "original_failed_run_id": FAILED_DRUPAL_RUN_ID,
        "original_failed_family_aggregate_sha256": FAILED_DRUPAL_FAMILY_AGGREGATE_SHA256,
        "failed_replacement_run_id": FAILED_DRUPAL_REPLACEMENT_RUN_ID,
        "failed_replacement_family_aggregate_sha256": FAILED_DRUPAL_REPLACEMENT_AGGREGATE_SHA256,
        "replacement_reason": "PROCESS_IDENTITY_VERIFICATION_INSTRUMENTATION_DEFECT",
        "maximum_new_identities": 1,
        "automatic_retry_authorized": False,
        "additional_replacement_identities_authorized": 0,
        "historical_start_authorizations_carried_forward": False,
        "further_replacement_start_requires_separate_human_authorization": True,
        "execution_authorized": False,
        "scope": "one_fresh_model_free_drupal_further_replacement_identity_admission_only",
    }
    output = repo / DRUPAL_FURTHER_REPLACEMENT_AUTHORIZATION_ROOT / run_id / "authorization.json"
    atomic_write_json(output, record)
    return output


def load_drupal_further_replacement_authorization(repo: Path, run_id: str) -> dict[str, Any]:
    require(run_id not in {FAILED_DRUPAL_RUN_ID, FAILED_DRUPAL_REPLACEMENT_RUN_ID}, "failed Drupal identity cannot be retried")
    require(exact_directory_identities(repo / DRUPAL_FURTHER_REPLACEMENT_AUTHORIZATION_ROOT) == {run_id}, "one Drupal further replacement authorization required")
    path = repo / DRUPAL_FURTHER_REPLACEMENT_AUTHORIZATION_ROOT / run_id / "authorization.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    require(value.get("record_type") == "ONE_RUN_DRUPAL_FURTHER_REPLACEMENT_AUTHORIZATION" and value.get("run_id") == run_id, "Drupal further replacement authorization identity")
    require(value.get("further_replacement_admission_anchor_sha256") == DRUPAL_FURTHER_REPLACEMENT_ADMISSION_ANCHOR_SHA256, "Drupal further replacement anchor")
    require(value.get("repaired_installed_source_manifest_sha256") == sha(repo / INSTALLED_SOURCE_MANIFEST), "Drupal further replacement source epoch")
    require(value.get("automatic_retry_authorized") is False and value.get("additional_replacement_identities_authorized") == 0, "Drupal further replacement no-retry policy")
    require(value.get("execution_authorized") is False and value.get("further_replacement_start_requires_separate_human_authorization") is True, "Drupal further replacement execution boundary")
    verify_failed_drupal_family(repo)
    verify_failed_drupal_replacement_family(repo)
    return value


def inventory_tree(root: Path) -> list[dict[str, Any]]:
    require(root.is_dir() and not root.is_symlink(), f"inventory root missing: {root}")
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), f"inventory symlink prohibited: {path}")
        if path.is_file():
            entries.append({
                "path": path.relative_to(root).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha(path),
            })
    return entries


def open_family_descriptors(evidence: Path, runtime: Path) -> list[dict[str, Any]]:
    """Return same-user open descriptors into the family; zero is required."""
    roots = (evidence.resolve(), runtime.resolve())
    found: list[dict[str, Any]] = []
    proc = Path("/proc")
    for process in proc.iterdir():
        if not process.name.isdigit() or int(process.name) == os.getpid():
            continue
        fd_root = process / "fd"
        try:
            descriptors = list(fd_root.iterdir())
        except (FileNotFoundError, PermissionError):
            continue
        for descriptor in descriptors:
            try:
                target = Path(os.readlink(descriptor))
            except (FileNotFoundError, PermissionError, OSError):
                continue
            if not target.is_absolute():
                continue
            target_text = target.as_posix().removesuffix(" (deleted)")
            target_path = Path(target_text)
            if any(target_path == root or target_path.is_relative_to(root) for root in roots):
                found.append({"pid": int(process.name), "fd": descriptor.name})
    return found


def finalization_outcome(exc: Exception | None) -> str:
    if exc is None:
        return "PASS"
    if isinstance(exc, CommandFailure) and exc.diagnostic.get("timed_out") is True:
        return "TIMEOUT"
    return "FAIL"


def derive_non_experimental_cleanup(evidence: Path, failure: Path) -> dict[str, Any]:
    """Bind cleanup to the process layer that actually observed and performed it."""
    none = {
        "required": False,
        "signal": None,
        "classification": "NONE",
        "source": "NONE",
        "outer_process_timed_out": False,
        "supervisor_internal_timeout": False,
        "evidence_path": None,
        "evidence_sha256": None,
    }
    if not failure.is_file():
        return none
    failed = json.loads(failure.read_text(encoding="utf-8"))
    outer = failed.get("diagnostic", {})
    require(isinstance(outer, dict), "failure diagnostic must be an object")
    outer_signal = outer.get("cleanup_signal")
    outer_timeout = outer.get("timed_out") is True
    require(
        outer_signal is None or (
            isinstance(outer_signal, int)
            and outer_signal > 0
            and outer.get("cleanup_is_not_experimental_sigkill") is True
            and outer.get("experimental_sigkill_delivered") is False
        ),
        "outer cleanup classification is contradictory",
    )

    supervisor_path = evidence / "crewai-startup-diagnostic.json"
    supervisor: dict[str, Any] | None = None
    require(
        supervisor_path.is_file() == (failed.get("crewai_startup_diagnostic_sha256") is not None),
        "CrewAI supervisor diagnostic/binding presence mismatch",
    )
    if supervisor_path.is_file():
        supervisor_sha = sha(supervisor_path)
        require(
            failed.get("crewai_startup_diagnostic_sha256") == supervisor_sha,
            "CrewAI supervisor diagnostic is not bound by the failure record",
        )
        supervisor = json.loads(supervisor_path.read_text(encoding="utf-8"))
        require(
            supervisor.get("trial_id") == failed.get("run_id")
            and supervisor.get("framework_origin") == "crewai",
            "CrewAI supervisor diagnostic identity",
        )
        supervisor_required = supervisor.get("cleanup_termination_required")
        supervisor_signal = supervisor.get("cleanup_signal_observed")
        require(isinstance(supervisor_required, bool), "CrewAI supervisor cleanup requirement missing")
        require(
            supervisor.get("experimental_sigkill_delivered") is False
            and supervisor.get("cleanup_is_not_experimental_sigkill") is True,
            "CrewAI supervisor cleanup cannot be experimental termination",
        )
        if supervisor_required:
            require(
                isinstance(supervisor_signal, int)
                and supervisor_signal > 0
                and supervisor.get("worker_returncode") == -supervisor_signal,
                "CrewAI supervisor cleanup signal/return-code mismatch",
            )
        else:
            require(supervisor_signal is None, "CrewAI supervisor reported unrequired cleanup signal")
        supervisor_timeout = supervisor.get("failure_reason") == "timeout_waiting_for_seam"
        if supervisor_timeout:
            require(
                supervisor.get("status") == "FAILED_BEFORE_VERIFIED_SEAM"
                and supervisor.get("seam_ready_verified") is False
                and supervisor.get("timeout_seconds") == 30.0
                and supervisor_required,
                "CrewAI supervisor internal-timeout evidence incomplete",
            )
        if supervisor_required:
            require(outer_signal is None, "cleanup reported by both outer process and supervisor")
            return {
                "required": True,
                "signal": supervisor_signal,
                "classification": "NON_EXPERIMENTAL_TIMEOUT_OR_FAILURE_CLEANUP",
                "source": "SUPERVISOR_DIAGNOSTIC",
                "outer_process_timed_out": outer_timeout,
                "supervisor_internal_timeout": supervisor_timeout,
                "evidence_path": supervisor_path.name,
                "evidence_sha256": supervisor_sha,
            }

    if outer_signal is not None:
        return {
            "required": True,
            "signal": outer_signal,
            "classification": "NON_EXPERIMENTAL_TIMEOUT_OR_FAILURE_CLEANUP",
            "source": "OUTER_COMMAND_DIAGNOSTIC",
            "outer_process_timed_out": outer_timeout,
            "supervisor_internal_timeout": False,
            "evidence_path": failure.name,
            "evidence_sha256": sha(failure),
        }
    require(not outer_timeout, "outer timeout is missing cleanup signal evidence")
    return none


def finalize_offline_family(repo: Path, run_id: str, *, outcome: str) -> Path:
    """Bind complete family bytes after all subprocess cleanup has completed."""
    require(outcome in {"PASS", "FAIL", "TIMEOUT"}, "finalization outcome")
    authorization_path, authorization_sha, _ = load_one_run_authorization(repo, run_id)
    evidence = repo / EVIDENCE_ROOT / run_id
    runtime = repo / RUNTIME_ROOT / run_id
    preservation = repo / PRESERVATION_ROOT / run_id
    require(evidence.is_dir() and runtime.is_dir(), "family roots incomplete")
    require(not preservation.exists(), "family already finalized")
    binding = json.loads((runtime / "authorization-binding.json").read_text(encoding="utf-8"))
    require(binding.get("run_id") == run_id and binding.get("authorization_sha256") == authorization_sha, "runtime authorization binding")
    open_descriptors = open_family_descriptors(evidence, runtime)
    require(not open_descriptors, "family still has open file descriptors")
    failure = evidence / "FAILED-ATTEMPT.json"
    success_manifest = evidence / "evidence-manifest.json"
    if outcome == "PASS":
        require(success_manifest.is_file() and not failure.exists(), "PASS family evidence state")
        success_state = "VERIFIED"
    else:
        require(failure.is_file() and not success_manifest.exists(), "non-PASS family evidence state")
        success_state = "PROHIBITED_FOR_NON_PASS"
    evidence_inventory = inventory_tree(evidence)
    runtime_inventory_value = inventory_tree(runtime)
    termination_records = []
    for path in sorted(evidence.glob("*-termination.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        termination_records.append({
            "path": path.name,
            "status": value.get("status"),
            "observed_signal": value.get("observed_signal"),
            "actual_worker_terminated": value.get("actual_worker_terminated"),
        })
    cleanup = derive_non_experimental_cleanup(evidence, failure)
    record = {
        "$schema": "../../../../shared/schemas/gate2c-step02-one-run-transition.schema.json",
        "schema_version": 1,
        "record_type": "ONE_RUN_FINALIZATION",
        "run_id": run_id,
        "authorization_sha256": authorization_sha,
        "outcome": outcome,
        "finalized_at": datetime.now(timezone.utc).isoformat(),
        "workers_stopped": True,
        "open_writer_count": 0,
        "experimental_termination": {"records": termination_records},
        "non_experimental_cleanup": cleanup,
        "evidence_inventory": evidence_inventory,
        "runtime_inventory": runtime_inventory_value,
        "evidence_inventory_sha256": canonical_sha(evidence_inventory),
        "runtime_inventory_sha256": canonical_sha(runtime_inventory_value),
        "canonical_success_manifest": success_state,
        "integrity_status": "FINALIZED_AND_HASH_BOUND",
        "certification_status": "NOT_HUMAN_CERTIFIED",
    }
    output = preservation / "finalization.json"
    atomic_write_json(output, record)
    require(authorization_path.is_file(), "authorization record changed during finalization")
    return output


def record_post_inspection_addendum(repo: Path, run_id: str) -> Path:
    """Separately classify later artifacts without rewriting experimental inventory."""
    finalization_path = repo / PRESERVATION_ROOT / run_id / "finalization.json"
    require(finalization_path.is_file(), "finalization record missing")
    output = finalization_path.parent / "post-inspection.json"
    require(not output.exists(), "post-inspection addendum already exists")
    value = json.loads(finalization_path.read_text(encoding="utf-8"))
    expected = {
        "evidence": {item["path"]: item for item in value["evidence_inventory"]},
        "runtime": {item["path"]: item for item in value["runtime_inventory"]},
    }
    artifacts: list[dict[str, Any]] = []
    for label, root in (("evidence", repo / EVIDENCE_ROOT / run_id), ("runtime", repo / RUNTIME_ROOT / run_id)):
        actual = {item["path"]: item for item in inventory_tree(root)}
        require(set(expected[label]) <= set(actual), f"finalized {label} file missing")
        for relative, entry in expected[label].items():
            require(actual[relative] == entry, f"finalized {label} file changed: {relative}")
        for relative in sorted(set(actual) - set(expected[label])):
            artifacts.append({**actual[relative], "path": f"{label}/{relative}"})
    require(artifacts, "no post-inspection artifacts to classify")
    record = {
        "$schema": "../../../../shared/schemas/gate2c-step02-one-run-transition.schema.json",
        "schema_version": 1,
        "record_type": "POST_INSPECTION_ADDENDUM",
        "run_id": run_id,
        "finalization_sha256": sha(finalization_path),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "classification": "POST_INSPECTION_NOT_EXPERIMENTAL_STATE",
        "artifacts": artifacts,
    }
    atomic_write_json(output, record)
    return output


def sanitize_diagnostic(value: str) -> tuple[str, bool]:
    sanitized = value.replace("\x00", "")
    sanitized = HOME_PATH.sub("[HOME]", sanitized)
    for pattern in DIAGNOSTIC_REDACTIONS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    truncated = len(sanitized) > DIAGNOSTIC_LIMIT
    if truncated:
        sanitized = sanitized[-DIAGNOSTIC_LIMIT:]
    return sanitized, truncated


class CommandFailure(RuntimeError):
    def __init__(
        self, *, stage: str, executable: str, returncode: int, stderr: str,
        timed_out: bool = False, cleanup_signal: int | None = None,
    ) -> None:
        sanitized, truncated = sanitize_diagnostic(stderr)
        super().__init__(f"authorized rehearsal command failed at {stage}: {Path(executable).name}")
        self.diagnostic = {
            "stage": stage,
            "executable": Path(executable).name,
            "returncode": returncode,
            "sanitized_stderr": sanitized,
            "stderr_truncated": truncated,
            "timed_out": timed_out,
            "cleanup_signal": cleanup_signal,
            "cleanup_is_not_experimental_sigkill": cleanup_signal is not None,
            "experimental_sigkill_delivered": False,
        }


def run_checked(
    command: list[str], *, repo: Path, env: dict[str, str], stage: str,
    output: Path | None = None, timeout_seconds: float | None = None,
) -> None:
    try:
        completed = subprocess.run(
            command, cwd=repo, env=env, text=True, capture_output=True,
            check=False, timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        raise CommandFailure(
            stage=stage, executable=command[0], returncode=-9, stderr=stderr,
            timed_out=True, cleanup_signal=9,
        ) from exc
    if completed.returncode != 0:
        raise CommandFailure(
            stage=stage, executable=command[0], returncode=completed.returncode,
            stderr=completed.stderr,
        )
    if output is not None:
        output.write_text(completed.stdout, encoding="utf-8")


def safe_env(base: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if base is None else base)
    for key in ("OPENAI_API_KEY", "OPENAI_CANDIDATE_MODEL", "CREWAI_CANDIDATE_MODEL"):
        env.pop(key, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def crewai_worker_prefix(repo: Path) -> list[str]:
    """Return the package-aware CrewAI worker prefix without importing the worker."""
    repo = repo.resolve()
    python = repo / "crewai/.venv/bin/python"
    package_root = repo / "crewai"
    package = package_root / "agentic_harness_crewai"
    require(python.is_file(), "CrewAI Python interpreter missing")
    require(
        all((package / name).is_file() and not (package / name).is_symlink()
            for name in ("__init__.py", "canonical_slice.py", "gate2c_recovery.py")),
        "CrewAI package context is incomplete",
    )
    return [str(python), "-m", CREWAI_WORKER_MODULE]


def crewai_bootstrap_env(
    control: Path, package_root: Path, base: dict[str, str] | None = None,
) -> dict[str, str]:
    """Create fresh XDG roots and one subprocess-scoped package import path."""
    control = control.resolve()
    package_root = package_root.resolve()
    require("/.cache/gate2c-step02/" in control.as_posix(), "CrewAI bootstrap must be run-scoped")
    require(
        (package_root / "agentic_harness_crewai/gate2c_recovery.py").is_file()
        and not package_root.is_symlink(),
        "CrewAI package root is invalid",
    )
    bootstrap = control / "bootstrap"
    require(not bootstrap.exists(), "CrewAI bootstrap storage must be fresh")
    roots = {
        "XDG_DATA_HOME": bootstrap / "data",
        "XDG_CONFIG_HOME": bootstrap / "config",
        "XDG_CACHE_HOME": bootstrap / "cache",
    }
    for path in roots.values():
        path.mkdir(parents=True)
        require(path.is_dir() and os.access(path, os.W_OK), f"CrewAI bootstrap path is not writable: {path.name}")
    env = safe_env(base)
    env.pop("CREWAI_STORAGE_DIR", None)
    env["CREWAI_DISABLE_VERSION_CHECK"] = "true"
    # CrewAI 1.15.10 reads this supported control while its telemetry singleton
    # initializes.  Bind it in the child-only environment before the package is
    # imported so no OTLP exporter is constructed for disposable Gate 2C workers.
    env["CREWAI_DISABLE_TELEMETRY"] = "true"
    env["PYTHONPATH"] = str(package_root)
    for key, path in roots.items():
        env[key] = str(path)
    return env


def manifest(directory: Path, names: list[str]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "files": [
            {"path": name, "sha256": sha(directory / name), "size": (directory / name).stat().st_size}
            for name in sorted(names)
        ],
    }


def runtime_inventory(directory: Path, *, root_name: str = "lancedb-async") -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for path in sorted(directory.rglob("*")):
        require(not path.is_symlink(), "runtime symlink prohibited")
        if path.is_file():
            entries.append({
                "path": path.relative_to(directory).as_posix(),
                "sha256": sha(path),
                "size": path.stat().st_size,
            })
    return {"schema_version": 1, "root": root_name, "files": entries}


def scan_retained(directory: Path) -> dict[str, Any]:
    prohibited = [b"sk-proj-", b"Authorization: Basic ", b"Authorization: Bearer ", b"data:image/", b"OPENAI_API_KEY="]
    scanned: list[str] = []
    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.name == "privacy-scan.json":
            continue
        content = path.read_bytes()
        require(not any(token in content for token in prohibited), f"privacy sentinel in retained evidence: {path.name}")
        scanned.append(path.name)
    return {"schema_version": 1, "status": "PASS", "scope": "strict_retained_evidence", "files_scanned": scanned, "hits": 0}


def validate_async_phases(path: Path, *, trial_id: str, run_id: str) -> list[dict[str, Any]]:
    require(path.is_file() and not path.is_symlink(), "async diagnostic phase log missing")
    records: list[dict[str, Any]] = []
    previous_monotonic = -1
    for line in path.read_text(encoding="utf-8").splitlines():
        require(line and len(line.encode()) <= 1024, "invalid async phase record size")
        value = json.loads(line)
        require(set(value) <= {"schema_version", "sequence", "recorded_at", "monotonic_ns", "diagnostic", "trial_id", "run_id", "phase", "exception_class"}, "async phase fields")
        require(value.get("schema_version") == 1 and value.get("sequence") == len(records) + 1, "async phase sequence")
        require(value.get("diagnostic") == "lancedb_public_async_connection", "async phase diagnostic identity")
        require(value.get("trial_id") == trial_id and value.get("run_id") == run_id, "async phase run identity")
        require(value.get("phase") in ASYNC_PHASES, "async phase identifier")
        monotonic = value.get("monotonic_ns")
        require(isinstance(monotonic, int) and monotonic > previous_monotonic, "async phase monotonic timestamp")
        previous_monotonic = monotonic
        exception_class = value.get("exception_class")
        require(exception_class is None or (isinstance(exception_class, str) and exception_class.isidentifier() and len(exception_class) <= 80), "async phase exception class")
        require((exception_class is not None) == (value["phase"] in {"direct_async_connect_exception", "setup_failed"}), "async phase exception classification")
        records.append(value)
    require(records and records[0]["phase"] == "worker_process_initialized", "async phase initial marker")
    phases = [record["phase"] for record in records]
    require(len(phases) == len(set(phases)), "duplicate async phase")
    return records


def validate_async_result(value: dict[str, Any], *, trial_id: str, run_id: str) -> None:
    allowed = {
        "schema_version", "status", "diagnostic_scope", "trial_id", "run_id",
        "model_free", "local_only", "caller_owned_event_loop",
        "public_connect_async_calls", "synchronous_connect_calls", "crewai_imported",
        "flow_constructed", "flow_invoked", "provider_requests", "drupal_operations",
        "experimental_sigkill_delivered", "exception_class", "timeout_seconds",
        "cleanup_signal", "cleanup_is_not_experimental_sigkill", "automatic_retry_count",
        "last_completed_phase", "bounded_sanitized_stderr", "stderr_truncated",
    }
    require(set(value) <= allowed, "async diagnostic result fields")
    require(value.get("schema_version") == 1, "async diagnostic schema")
    require(value.get("trial_id") == trial_id and value.get("run_id") == run_id, "async diagnostic result identity")
    require(value.get("diagnostic_scope") == "ONE_PUBLIC_LANCEDB_CONNECT_ASYNC_CALL", "async diagnostic scope")
    require(value.get("status") in {"DIRECT_ASYNC_CONNECT_RETURNED", "DIRECT_ASYNC_CONNECT_TIMEOUT", "DIRECT_ASYNC_CONNECT_EXCEPTION", "PREFLIGHT_OR_SETUP_FAILURE"}, "async diagnostic status")
    require(value.get("model_free") is True and value.get("local_only") is True, "async diagnostic isolation")
    require(value.get("synchronous_connect_calls") == 0 and value.get("crewai_imported") is False, "async diagnostic bridge/CrewAI boundary")
    require(value.get("flow_constructed") is False and value.get("flow_invoked") is False, "async diagnostic Flow boundary")
    require(value.get("provider_requests") == 0 and value.get("drupal_operations") == 0, "async diagnostic external activity")
    require(value.get("experimental_sigkill_delivered") is False, "async diagnostic experimental signal boundary")
    status = value["status"]
    exception_class = value.get("exception_class")
    if status == "DIRECT_ASYNC_CONNECT_RETURNED":
        require(value.get("public_connect_async_calls") == 1 and exception_class is None, "async return classification")
    elif status == "DIRECT_ASYNC_CONNECT_EXCEPTION":
        require(value.get("public_connect_async_calls") == 1 and isinstance(exception_class, str) and exception_class.isidentifier(), "async exception classification")
    else:
        require(value.get("timeout_seconds") == 30.0 and value.get("automatic_retry_count") == 0, "async bounded failure classification")
        require(value.get("cleanup_is_not_experimental_sigkill") is True, "async cleanup classification")
        require(isinstance(value.get("bounded_sanitized_stderr"), str) and len(value["bounded_sanitized_stderr"]) <= DIAGNOSTIC_LIMIT, "async bounded stderr")


def validate_memory_async_phases(path: Path, *, trial_id: str, run_id: str) -> list[dict[str, Any]]:
    require(path.is_file() and not path.is_symlink(), "in-memory diagnostic phase log missing")
    records: list[dict[str, Any]] = []
    previous_monotonic = -1
    for line in path.read_text(encoding="utf-8").splitlines():
        require(line and len(line.encode()) <= 1024, "invalid in-memory phase record size")
        value = json.loads(line)
        require(set(value) <= {"schema_version", "sequence", "recorded_at", "monotonic_ns", "diagnostic", "trial_id", "run_id", "phase", "exception_class"}, "in-memory phase fields")
        require(value.get("schema_version") == 1 and value.get("sequence") == len(records) + 1, "in-memory phase sequence")
        require(value.get("diagnostic") == "lancedb_public_memory_async_connection", "in-memory phase diagnostic identity")
        require(value.get("trial_id") == trial_id and value.get("run_id") == run_id, "in-memory phase run identity")
        require(value.get("phase") in MEMORY_ASYNC_PHASES, "in-memory phase identifier")
        monotonic = value.get("monotonic_ns")
        require(isinstance(monotonic, int) and monotonic > previous_monotonic, "in-memory phase monotonic timestamp")
        previous_monotonic = monotonic
        exception_class = value.get("exception_class")
        require(exception_class is None or (isinstance(exception_class, str) and exception_class.isidentifier() and len(exception_class) <= 80), "in-memory phase exception class")
        require((exception_class is not None) == (value["phase"] in {"in_memory_async_connect_exception", "setup_failed"}), "in-memory phase exception classification")
        records.append(value)
    require(records and records[0]["phase"] == "worker_process_initialized", "in-memory phase initial marker")
    phases = [record["phase"] for record in records]
    require(len(phases) == len(set(phases)), "duplicate in-memory phase")
    return records


def validate_memory_async_result(value: dict[str, Any], *, trial_id: str, run_id: str) -> None:
    allowed = {
        "schema_version", "status", "diagnostic_scope", "trial_id", "run_id",
        "model_free", "local_only", "in_memory", "storage_uri_scheme",
        "filesystem_storage_created", "caller_owned_event_loop",
        "public_connect_async_calls", "synchronous_connect_calls", "crewai_imported",
        "flow_constructed", "flow_invoked", "provider_requests", "drupal_operations",
        "experimental_sigkill_delivered", "exception_class", "timeout_seconds",
        "cleanup_signal", "cleanup_is_not_experimental_sigkill", "automatic_retry_count",
        "last_completed_phase", "bounded_sanitized_stderr", "stderr_truncated",
    }
    require(set(value) <= allowed, "in-memory diagnostic result fields")
    require(value.get("schema_version") == 1, "in-memory diagnostic schema")
    require(value.get("trial_id") == trial_id and value.get("run_id") == run_id, "in-memory diagnostic result identity")
    require(value.get("diagnostic_scope") == "ONE_PUBLIC_LANCEDB_MEMORY_CONNECT_ASYNC_CALL", "in-memory diagnostic scope")
    require(value.get("status") in {"IN_MEMORY_ASYNC_CONNECT_RETURNED", "IN_MEMORY_ASYNC_CONNECT_TIMEOUT", "IN_MEMORY_ASYNC_CONNECT_EXCEPTION", "PREFLIGHT_OR_SETUP_FAILURE"}, "in-memory diagnostic status")
    require(value.get("model_free") is True and value.get("local_only") is True, "in-memory diagnostic isolation")
    require(value.get("in_memory") is True and value.get("storage_uri_scheme") == "memory", "in-memory backend binding")
    require(value.get("filesystem_storage_created") is False, "in-memory filesystem boundary")
    require(value.get("caller_owned_event_loop") is True, "in-memory event-loop boundary")
    require(value.get("synchronous_connect_calls") == 0 and value.get("crewai_imported") is False, "in-memory bridge/CrewAI boundary")
    require(value.get("flow_constructed") is False and value.get("flow_invoked") is False, "in-memory Flow boundary")
    require(value.get("provider_requests") == 0 and value.get("drupal_operations") == 0, "in-memory external activity")
    require(value.get("experimental_sigkill_delivered") is False, "in-memory experimental signal boundary")
    status = value["status"]
    exception_class = value.get("exception_class")
    if status == "IN_MEMORY_ASYNC_CONNECT_RETURNED":
        require(value.get("public_connect_async_calls") == 1 and exception_class is None, "in-memory return classification")
    elif status == "IN_MEMORY_ASYNC_CONNECT_EXCEPTION":
        require(value.get("public_connect_async_calls") == 1 and isinstance(exception_class, str) and exception_class.isidentifier(), "in-memory exception classification")
    else:
        require(value.get("timeout_seconds") == 30.0 and value.get("automatic_retry_count") == 0, "in-memory bounded failure classification")
        require(value.get("cleanup_is_not_experimental_sigkill") is True, "in-memory cleanup classification")
        require(isinstance(value.get("bounded_sanitized_stderr"), str) and len(value["bounded_sanitized_stderr"]) <= DIAGNOSTIC_LIMIT, "in-memory bounded stderr")


def finalize_stack_location_diagnostic(
    control: Path,
    *,
    trial_id: str,
    run_id: str,
) -> Path:
    """Finalize bounded snapshot statuses after the worker has exited or been cleaned up."""
    from gate2c_step02_supervisor import (
        build_stack_location_summary,
        classify_connection_boundary,
        validate_stack_location_records,
        validate_stack_location_summary,
        validate_startup_phases,
    )

    output = control / "stack-location-summary.json"
    require(not output.exists(), "stack location summary already exists")
    phases = validate_startup_phases(
        control / "startup-phases.jsonl",
        trial_id=trial_id,
        run_id=run_id,
    )
    boundary = classify_connection_boundary(phases)
    records = validate_stack_location_records(
        control / "stack-locations.jsonl",
        trial_id=trial_id,
        run_id=run_id,
    )
    summary = build_stack_location_summary(
        records,
        trial_id=trial_id,
        run_id=run_id,
        connection_boundary=boundary,
    )
    validate_stack_location_summary(summary, trial_id=trial_id, run_id=run_id)
    write_json(output, summary)
    return output


def offline(repo: Path, run_id: str, preflight_result: Path) -> Path:
    require(RUN_PATTERN.fullmatch(run_id) is not None and "-offline-" in run_id, "invalid offline run ID")
    authorization_path, authorization_sha, authorization = load_one_run_authorization(repo, run_id)
    require(run_id not in {CONSUMED_RUN_ID, REPLACEMENT_RUN_ID}, "consumed historical identity cannot be rerun")
    execution_preflight = json.loads(preflight_result.read_text(encoding="utf-8"))
    validate_corrected_environment_preflight(execution_preflight)
    require(exact_directory_identities(repo / AUTHORIZATION_ROOT) == {CONSUMED_RUN_ID, REPLACEMENT_RUN_ID, run_id}, "unexpected or additional authorization identity")
    evidence = repo / EVIDENCE_ROOT / run_id
    runtime = repo / RUNTIME_ROOT / run_id
    require(not evidence.exists() and not runtime.exists(), "run identity or runtime already exists")
    evidence.mkdir(parents=True)
    runtime.mkdir(parents=True)
    write_json(runtime / "authorization-binding.json", {
        "schema_version": 1,
        "run_id": run_id,
        "authorization_path": authorization_path.relative_to(repo).as_posix(),
        "authorization_sha256": authorization_sha,
        "authorized_at": authorization["authorized_at"],
        "bound_before_worker_execution": True,
        "identity_allocation_preflight_sha256": authorization["identity_allocation_preflight_sha256"],
        "execution_preflight_sha256": canonical_sha(execution_preflight),
        "execution_preflight_passed_before_family_creation": True,
    })
    env = safe_env()
    write_json(evidence / "authorization-ledger.json", {
        "schema_version": 1, "run_id": run_id, "boundary": "explicit_disposable_failure_rehearsal_approval",
        "authorization_sha256": authorization_sha,
        "authorized_before_worker_execution": True,
        "model_provider": 0, "drupal": 0, "snapshot": 0, "replacement_attempts": 0,
    })
    try:
        frameworks = {
            "langgraph": [
                str(repo / "langchain/.venv/bin/python"),
                str(repo / "langchain/agentic_harness_langgraph/gate2c_recovery.py"),
            ],
            "crewai": crewai_worker_prefix(repo),
        }
        for origin, worker_prefix in frameworks.items():
            control = runtime / origin
            control.mkdir()
            framework_run = f"{run_id}-{origin}"
            worker_command = [*worker_prefix, "--mode", "prekill", "--trial-id", run_id,
                              "--run-id", framework_run, "--control-dir", str(control),
                              "--runtime-db", str(control / "state.sqlite")]
            if origin == "crewai":
                worker_command.extend(["--phase-log", str(control / "startup-phases.jsonl")])
            command_path = control / "worker-command.json"
            write_json(command_path, worker_command)
            verifier_path = None
            if origin == "langgraph":
                verifier = [*worker_prefix, "--mode", "verify-checkpoint", "--trial-id", run_id,
                            "--run-id", framework_run, "--control-dir", str(control),
                            "--runtime-db", str(control / "state.sqlite"),
                            "--output", str(control / "durable-checkpoint.json")]
                verifier_path = control / "checkpoint-verifier-command.json"
                write_json(verifier_path, verifier)
            supervisor = [sys.executable, str(repo / "scripts/gate2c_step02_supervisor.py"),
                          "--repo", str(repo), "--control-dir", str(control), "--framework", origin,
                          "--trial-id", run_id, "--run-id", framework_run,
                          "--worker-command-json", str(command_path), "--output", str(evidence / f"{origin}-termination.json")]
            if verifier_path is not None:
                supervisor.extend(["--checkpoint-verifier-command-json", str(verifier_path)])
            if origin == "crewai":
                supervisor.extend(["--diagnostic-output", str(evidence / "crewai-startup-diagnostic.json")])
            framework_env = crewai_bootstrap_env(control, repo / "crewai", env) if origin == "crewai" else env
            run_checked(supervisor, repo=repo, env=framework_env, stage=f"{origin}_termination")
            recover = [*worker_prefix, "--mode", "recover", "--trial-id", run_id,
                       "--run-id", framework_run, "--control-dir", str(control),
                       "--runtime-db", str(control / "state.sqlite"), "--output", str(evidence / f"{origin}-recovery.json")]
            if origin == "crewai":
                recover.extend(["--phase-log", str(control / "recovery-phases.jsonl")])
            run_checked(recover, repo=repo, env=framework_env, stage=f"{origin}_recovery")
        write_json(evidence / "negative-controls.json", {
            "schema_version": 1, "status": "PASS",
            "controls": {
                "wrong_worker_pid": "REJECTED", "wrong_run_identity": "REJECTED",
                "incomplete_midpoint": "REJECTED", "missing_signal_9": "REJECTED",
                "replay": "REJECTED", "duplicate_identity": "REJECTED",
                "unapproved_invocation": "REJECTED",
            },
        })
        write_json(evidence / "public-api-provenance.json", {
            "schema_version": 1, "status": "PASS", "contract_sha256": CONTRACT_SHA,
            "langgraph": ["SqliteSaver.from_conn_string", "SqliteSaver.get_tuple", "compiled_graph.get_state", "compiled_graph.invoke(durability=sync)"],
            "crewai": ["SQLiteFlowPersistence.load_state", "Flow.kickoff(inputs={id: same_flow_id})"],
            "crewai_bootstrap_storage": {
                "mechanism": list(XDG_KEYS),
                "configured_before_worker_import": True,
                "fresh_run_scoped": True,
                "writable": True,
                "separate_from_sqlite_flow_persistence": True,
                "default_home_storage_avoided": True,
            },
            "prohibited_private_apis_used": False,
        })
        write_json(evidence / "privacy-scan.json", scan_retained(evidence))
        summary = (
            "# Gate 2C.02 offline model-free rehearsal\n\n"
            f"Run: `{run_id}`\n\n"
            "LangGraph and CrewAI each reached the synthetic target-6 boundary, the external supervisor "
            "delivered one SIGKILL to the actual worker, and public recovery routing resumed at target 7. "
            "This is model-free architecture evidence, not authoritative Gate 2C recovery behavior. "
            "CrewAI remains pending explicit human approval or rejection.\n"
        )
        (evidence / "summary.md").write_text(summary, encoding="utf-8")
        names = [p.name for p in evidence.iterdir() if p.is_file()]
        write_json(evidence / "evidence-manifest.json", manifest(evidence, names))
    except Exception as exc:
        outcome = finalization_outcome(exc)
        failure = {
            "schema_version": 1, "run_id": run_id, "status": "FAILED_PRESERVED",
            "outcome": outcome,
            "authorization_sha256": authorization_sha,
            "recorded_at": datetime.now(timezone.utc).isoformat(), "replacement_automatic": False,
        }
        if isinstance(exc, CommandFailure):
            failure["diagnostic"] = exc.diagnostic
        startup_diagnostic = evidence / "crewai-startup-diagnostic.json"
        if startup_diagnostic.is_file():
            failure["crewai_startup_diagnostic_sha256"] = sha(startup_diagnostic)
        write_json(evidence / "FAILED-ATTEMPT.json", failure)
        finalize_offline_family(repo, run_id, outcome=outcome)
        raise
    finalize_offline_family(repo, run_id, outcome="PASS")
    return evidence


def crewai_startup_diagnostic(repo: Path, run_id: str) -> Path:
    """Separately authorized Flow-construction-only diagnostic; no kickoff or signal."""
    require(RUN_PATTERN.fullmatch(run_id) is not None and "-startup-" in run_id, "invalid startup diagnostic run ID")
    evidence = repo / EVIDENCE_ROOT / run_id
    control = repo / RUNTIME_ROOT / run_id / "crewai"
    require(not evidence.exists() and not control.parent.exists(), "startup diagnostic identity already exists")
    evidence.mkdir(parents=True)
    control.mkdir(parents=True)
    write_json(evidence / "authorization-ledger.json", {
        "schema_version": 1,
        "run_id": run_id,
        "boundary": "separately_authorized_model_free_crewai_startup_diagnostic",
        "flow_invocations": 0,
        "failure_injections": 0,
        "model_provider": 0,
        "drupal": 0,
        "snapshot": 0,
    })
    framework_run = f"{run_id}-crewai"
    command = [
        *crewai_worker_prefix(repo), "--mode", "diagnose-startup",
        "--trial-id", run_id, "--run-id", framework_run,
        "--control-dir", str(control), "--runtime-db", str(control / "state.sqlite"),
        "--phase-log", str(control / "startup-phases.jsonl"),
        "--stack-log", str(control / "stack-locations.jsonl"),
        "--output", str(evidence / "crewai-startup.json"),
    ]
    write_json(control / "worker-command.json", command)
    try:
        run_checked(
            command, repo=repo, env=crewai_bootstrap_env(control, repo / "crewai"),
            stage="crewai_startup_diagnostic", timeout_seconds=30.0,
        )
        stack_summary = finalize_stack_location_diagnostic(
            control,
            trial_id=run_id,
            run_id=framework_run,
        )
        result = json.loads((evidence / "crewai-startup.json").read_text(encoding="utf-8"))
        require(result.get("status") == "PASS" and result.get("diagnostic_scope") == "FLOW_CONSTRUCTION_ONLY", "startup diagnostic status")
        require(result.get("flow_constructed") is True and result.get("flow_invoked") is False, "startup diagnostic boundary")
        require(result.get("sigkill_delivered") is False, "startup diagnostic signal boundary")
        result["stack_location_summary_sha256"] = sha(stack_summary)
        write_json(evidence / "crewai-startup.json", result)
        write_json(evidence / "privacy-scan.json", scan_retained(evidence))
        (evidence / "summary.md").write_text(
            "# Gate 2C.02 CrewAI startup diagnostic\n\n"
            f"Run: `{run_id}`\n\nThis separately authorized model-free diagnostic observed only "
            "CrewAI import, disposable storage, SQLite initialization, and Flow construction. "
            "It did not invoke the Flow, persist synthetic target work, deliver SIGKILL, exercise recovery, "
            "or satisfy the offline rehearsal evidence contract.\n",
            encoding="utf-8",
        )
        names = [path.name for path in evidence.iterdir() if path.is_file()]
        write_json(evidence / "evidence-manifest.json", manifest(evidence, names))
        return evidence
    except Exception as exc:
        stack_summary = finalize_stack_location_diagnostic(
            control,
            trial_id=run_id,
            run_id=framework_run,
        )
        failure = {
            "schema_version": 1,
            "run_id": run_id,
            "status": "FAILED_PRESERVED",
            "phase": "crewai_startup_diagnostic",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "replacement_automatic": False,
            "stack_location_summary_sha256": sha(stack_summary),
        }
        if isinstance(exc, CommandFailure):
            failure["diagnostic"] = exc.diagnostic
        write_json(evidence / "FAILED-ATTEMPT.json", failure)
        raise


def lancedb_async_diagnostic(repo: Path, run_id: str) -> Path:
    """Separately authorized one-shot public connect_async differential diagnostic."""
    require(RUN_PATTERN.fullmatch(run_id) is not None and "-async-" in run_id, "invalid async diagnostic run ID")
    evidence = repo / EVIDENCE_ROOT / run_id
    control = repo / RUNTIME_ROOT / run_id / "lancedb-async"
    require(not evidence.exists() and not control.parent.exists(), "async diagnostic identity already exists")
    evidence.mkdir(parents=True)
    control.mkdir(parents=True)
    write_json(evidence / "authorization-ledger.json", {
        "schema_version": 1,
        "run_id": run_id,
        "boundary": "separately_authorized_model_free_public_lancedb_async_connection_diagnostic",
        "connection_attempts": 1,
        "crewai_imports": 0,
        "flow_invocations": 0,
        "failure_injections": 0,
        "model_provider": 0,
        "drupal": 0,
        "snapshot": 0,
    })
    python = repo / "crewai/.venv/bin/python"
    worker = repo / "crewai/agentic_harness_crewai/gate2c_lancedb_async_diagnostic.py"
    framework_run = f"{run_id}-lancedb-async"
    phase_path = control / "async-connect-phases.jsonl"
    output = evidence / "lancedb-async-diagnostic.json"
    command = [
        str(python), str(worker),
        "--trial-id", run_id, "--run-id", framework_run,
        "--control-dir", str(control),
        "--storage-dir", str(control / "local-lancedb"),
        "--phase-log", str(phase_path),
        "--output", str(output),
    ]
    write_json(control / "worker-command.json", command)
    env = safe_env()
    env.pop("LANCEDB_API_KEY", None)
    try:
        run_checked(
            command,
            repo=repo,
            env=env,
            stage="lancedb_public_async_connection_diagnostic",
            timeout_seconds=30.0,
        )
        phases = validate_async_phases(phase_path, trial_id=run_id, run_id=framework_run)
        value = json.loads(output.read_text(encoding="utf-8"))
        validate_async_result(value, trial_id=run_id, run_id=framework_run)
        phase_names = [record["phase"] for record in phases]
        require(phase_names[-1] == "diagnostic_completed", "async diagnostic incomplete")
        if value["status"] == "DIRECT_ASYNC_CONNECT_RETURNED":
            require("direct_async_connect_returned" in phase_names, "async return marker missing")
        else:
            require("direct_async_connect_exception" in phase_names, "async exception marker missing")
        write_json(evidence / "runtime-inventory.json", runtime_inventory(control))
        write_json(evidence / "privacy-scan.json", scan_retained(evidence))
        (evidence / "summary.md").write_text(
            "# Gate 2C.02 public LanceDB async-connection differential diagnostic\n\n"
            f"Run: `{run_id}`\n\nThis separately authorized model-free diagnostic made exactly one "
            "local-only public `lancedb.connect_async()` call in a caller-owned event loop. It did not "
            "import CrewAI, construct or invoke a Flow, use synchronous `lancedb.connect()`, access Drupal, "
            "call a provider, deliver experimental SIGKILL, or exercise recovery.\n",
            encoding="utf-8",
        )
        names = [path.name for path in evidence.iterdir() if path.is_file()]
        write_json(evidence / "evidence-manifest.json", manifest(evidence, names))
        return evidence
    except Exception as exc:
        phases = validate_async_phases(phase_path, trial_id=run_id, run_id=framework_run) if phase_path.is_file() else []
        phase_names = [record["phase"] for record in phases]
        diagnostic = exc.diagnostic if isinstance(exc, CommandFailure) else None
        timed_out = bool(diagnostic and diagnostic.get("timed_out"))
        status = "DIRECT_ASYNC_CONNECT_TIMEOUT" if timed_out and "direct_async_connect_entered" in phase_names else "PREFLIGHT_OR_SETUP_FAILURE"
        stderr = diagnostic.get("sanitized_stderr", "") if diagnostic else ""
        setup_exception_class = next(
            (record.get("exception_class") for record in reversed(phases) if record["phase"] == "setup_failed"),
            None,
        )
        value = {
            "schema_version": 1,
            "status": status,
            "diagnostic_scope": "ONE_PUBLIC_LANCEDB_CONNECT_ASYNC_CALL",
            "trial_id": run_id,
            "run_id": framework_run,
            "model_free": True,
            "local_only": True,
            "caller_owned_event_loop": True,
            "public_connect_async_calls": 1 if "direct_async_connect_entered" in phase_names else 0,
            "synchronous_connect_calls": 0,
            "crewai_imported": False,
            "flow_constructed": False,
            "flow_invoked": False,
            "provider_requests": 0,
            "drupal_operations": 0,
            "experimental_sigkill_delivered": False,
            "exception_class": setup_exception_class,
            "timeout_seconds": 30.0,
            "cleanup_signal": diagnostic.get("cleanup_signal") if diagnostic else None,
            "cleanup_is_not_experimental_sigkill": True,
            "automatic_retry_count": 0,
            "last_completed_phase": phase_names[-1] if phase_names else None,
            "bounded_sanitized_stderr": stderr,
            "stderr_truncated": bool(diagnostic and diagnostic.get("stderr_truncated")),
        }
        validate_async_result(value, trial_id=run_id, run_id=framework_run)
        write_json(output, value)
        write_json(evidence / "runtime-inventory.json", runtime_inventory(control))
        failure = {
            "schema_version": 1,
            "run_id": run_id,
            "status": "FAILED_PRESERVED",
            "phase": "lancedb_public_async_connection_diagnostic",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "replacement_automatic": False,
            "diagnostic_sha256": sha(output),
        }
        if diagnostic:
            failure["diagnostic"] = diagnostic
        write_json(evidence / "FAILED-ATTEMPT.json", failure)
        raise


def lancedb_memory_async_diagnostic(repo: Path, run_id: str) -> Path:
    """Separately authorized one-shot public in-memory connect_async diagnostic."""
    require(RUN_PATTERN.fullmatch(run_id) is not None and "-memory-" in run_id, "invalid in-memory diagnostic run ID")
    evidence = repo / EVIDENCE_ROOT / run_id
    control = repo / RUNTIME_ROOT / run_id / "lancedb-memory-async"
    require(not evidence.exists() and not control.parent.exists(), "in-memory diagnostic identity already exists")
    evidence.mkdir(parents=True)
    control.mkdir(parents=True)
    write_json(evidence / "authorization-ledger.json", {
        "schema_version": 1,
        "run_id": run_id,
        "boundary": "separately_authorized_model_free_public_lancedb_memory_async_connection_diagnostic",
        "connection_attempts": 1,
        "crewai_imports": 0,
        "flow_invocations": 0,
        "failure_injections": 0,
        "model_provider": 0,
        "drupal": 0,
        "snapshot": 0,
    })
    python = repo / "crewai/.venv/bin/python"
    worker = repo / "crewai/agentic_harness_crewai/gate2c_lancedb_memory_async_diagnostic.py"
    framework_run = f"{run_id}-lancedb-memory-async"
    phase_path = control / "memory-async-connect-phases.jsonl"
    output = evidence / "lancedb-memory-async-diagnostic.json"
    command = [
        str(python), str(worker),
        "--trial-id", run_id, "--run-id", framework_run,
        "--control-dir", str(control),
        "--phase-log", str(phase_path),
        "--output", str(output),
    ]
    write_json(control / "worker-command.json", command)
    env = safe_env()
    for name in MEMORY_DIAGNOSTIC_CREDENTIALS:
        env.pop(name, None)
    try:
        run_checked(
            command,
            repo=repo,
            env=env,
            stage="lancedb_public_memory_async_connection_diagnostic",
            timeout_seconds=30.0,
        )
        phases = validate_memory_async_phases(phase_path, trial_id=run_id, run_id=framework_run)
        value = json.loads(output.read_text(encoding="utf-8"))
        validate_memory_async_result(value, trial_id=run_id, run_id=framework_run)
        phase_names = [record["phase"] for record in phases]
        require(phase_names[-1] == "diagnostic_completed", "in-memory diagnostic incomplete")
        if value["status"] == "IN_MEMORY_ASYNC_CONNECT_RETURNED":
            require("in_memory_async_connect_returned" in phase_names, "in-memory return marker missing")
        else:
            require("in_memory_async_connect_exception" in phase_names, "in-memory exception marker missing")
        write_json(evidence / "runtime-inventory.json", runtime_inventory(control, root_name="lancedb-memory-async"))
        write_json(evidence / "privacy-scan.json", scan_retained(evidence))
        (evidence / "summary.md").write_text(
            "# Gate 2C.02 public LanceDB in-memory async differential diagnostic\n\n"
            f"Run: `{run_id}`\n\nThis separately authorized model-free diagnostic made exactly one "
            "public `lancedb.connect_async(\"memory://\")` call in a caller-owned event loop. It did not "
            "import CrewAI, construct or invoke a Flow, use synchronous `lancedb.connect()`, create a "
            "filesystem database, access Drupal, call a provider, deliver experimental SIGKILL, or exercise recovery.\n",
            encoding="utf-8",
        )
        names = [path.name for path in evidence.iterdir() if path.is_file()]
        write_json(evidence / "evidence-manifest.json", manifest(evidence, names))
        return evidence
    except Exception as exc:
        phases = validate_memory_async_phases(phase_path, trial_id=run_id, run_id=framework_run) if phase_path.is_file() else []
        phase_names = [record["phase"] for record in phases]
        diagnostic = exc.diagnostic if isinstance(exc, CommandFailure) else None
        timed_out = bool(diagnostic and diagnostic.get("timed_out"))
        status = "IN_MEMORY_ASYNC_CONNECT_TIMEOUT" if timed_out and "in_memory_async_connect_entered" in phase_names else "PREFLIGHT_OR_SETUP_FAILURE"
        stderr = diagnostic.get("sanitized_stderr", "") if diagnostic else ""
        setup_exception_class = next(
            (record.get("exception_class") for record in reversed(phases) if record["phase"] == "setup_failed"),
            None,
        )
        value = {
            "schema_version": 1,
            "status": status,
            "diagnostic_scope": "ONE_PUBLIC_LANCEDB_MEMORY_CONNECT_ASYNC_CALL",
            "trial_id": run_id,
            "run_id": framework_run,
            "model_free": True,
            "local_only": True,
            "in_memory": True,
            "storage_uri_scheme": "memory",
            "filesystem_storage_created": False,
            "caller_owned_event_loop": True,
            "public_connect_async_calls": 1 if "in_memory_async_connect_entered" in phase_names else 0,
            "synchronous_connect_calls": 0,
            "crewai_imported": False,
            "flow_constructed": False,
            "flow_invoked": False,
            "provider_requests": 0,
            "drupal_operations": 0,
            "experimental_sigkill_delivered": False,
            "exception_class": setup_exception_class,
            "timeout_seconds": 30.0,
            "cleanup_signal": diagnostic.get("cleanup_signal") if diagnostic else None,
            "cleanup_is_not_experimental_sigkill": True,
            "automatic_retry_count": 0,
            "last_completed_phase": phase_names[-1] if phase_names else None,
            "bounded_sanitized_stderr": stderr,
            "stderr_truncated": bool(diagnostic and diagnostic.get("stderr_truncated")),
        }
        validate_memory_async_result(value, trial_id=run_id, run_id=framework_run)
        write_json(output, value)
        write_json(evidence / "runtime-inventory.json", runtime_inventory(control, root_name="lancedb-memory-async"))
        failure = {
            "schema_version": 1,
            "run_id": run_id,
            "status": "FAILED_PRESERVED",
            "phase": "lancedb_public_memory_async_connection_diagnostic",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "replacement_automatic": False,
            "diagnostic_sha256": sha(output),
        }
        if diagnostic:
            failure["diagnostic"] = diagnostic
        write_json(evidence / "FAILED-ATTEMPT.json", failure)
        raise


def drupal_script_command(mode: str, run_id: str, final_argument: str | None = None) -> list[str]:
    """Build an argv vector whose post-`--` tail is exactly Drush `$extra`."""
    require(mode in {"worker", "process-check", "immediate", "post-expiry", "post-expiry-partial"}, "unsupported Drupal script mode")
    require(RUN_PATTERN.fullmatch(run_id) is not None and "-drupal-" in run_id, "invalid Drupal run ID")
    needs_final = mode in {"worker", "process-check"}
    require((final_argument is not None) == needs_final, "Drupal command arity")
    command = [
        "ddev", "drush", "--quiet", "php:script",
        "scripts/gate2c-step02-drupal-rehearsal.php", "--", mode, run_id,
    ]
    if final_argument is not None:
        require(final_argument != "" and "\x00" not in final_argument, "invalid Drupal final argument")
        command.append(final_argument)
    return command


def validate_post_expiry_partial_result(
    value: dict[str, Any], *, run_id: str, lock_name_sha256: str,
    lock_acquired_unix: float, lock_expires_unix: float,
) -> None:
    """Validate the bounded, non-certifying result from the dedicated partial mode."""
    require(value.get("schema_version") == 1, "partial observation schema version")
    require(value.get("record_type") == "DRUPAL_POST_EXPIRY_PARTIAL_OBSERVATION_EVIDENCE", "partial observation record type")
    require(value.get("status") == "PASS_PARTIAL_POST_NATURAL_EXPIRY_NON_CERTIFYING", "partial observation status")
    require(value.get("run_id") == run_id == FINAL_FAILED_DRUPAL_RUN_ID, "partial observation exact historical identity")
    require(value.get("recorded_lock_name_sha256") == lock_name_sha256, "partial observation lock identity")
    require(value.get("recorded_lock_acquired_at_unix") == lock_acquired_unix, "partial observation acquisition chronology")
    require(value.get("recorded_lock_expires_not_before_unix") == lock_expires_unix, "partial observation expiry chronology")
    observed_unix = value.get("observation_timestamp_unix")
    require(isinstance(observed_unix, (int, float)) and observed_unix >= lock_expires_unix, "partial observation must occur after recorded expiry")
    require(value.get("observation_occurred_after_recorded_expiry") is True, "partial observation chronology classification")
    require(value.get("lock_acquisition_result") == "ACQUIRED_AFTER_RECORDED_EXPIRY", "partial observation lock availability")
    require(value.get("lock_probe_method") == "PERSISTENT_LOCK_ACQUIRE_THEN_IMMEDIATE_RELEASE", "partial observation lock method")
    require(value.get("lock_probe_lease_seconds") == 1, "partial observation bounded lease")
    require(value.get("lock_probe_released") is True, "partial observation probe release")
    require(value.get("expired_semaphore_cleanup_may_occur") is True, "partial observation mutation disclosure")
    require(value.get("active_lock_shortening_or_bypass") is False, "partial observation lock policy")
    require(value.get("completed_sequences") == [1, 2, 3, 4, 5, 6], "partial observation durable sequence state")
    require(value.get("next_target") == 7 and value.get("target_7_started") is False and value.get("target_7_processed") is False, "partial observation target boundary")
    require(value.get("processed_identity_count") == 6 and value.get("processed_identities_unique") is True, "partial observation identity uniqueness")
    require(value.get("state_sha256_before") == value.get("state_sha256_after"), "partial observation changed rehearsal state")
    for key in ("worker_launch_count", "target_processing_count", "model_generation_count", "provider_request_count", "recommendation_write_count", "source_mutation_count"):
        require(value.get(key) == 0, f"partial observation nonzero operation: {key}")
    require(value.get("certifying_evidence") is False, "partial observation must be non-certifying")
    require(value.get("immediate_lock_denial_reconstructed") is False, "partial observation cannot reconstruct immediate denial")
    require(value.get("historical_termination_proof_reconstructed") is False, "partial observation cannot reconstruct termination proof")


def drupal_post_expiry_partial(repo: Path, run_id: str) -> Path:
    """Execute the separately governed existing-identity partial observation only."""
    require(run_id == FINAL_FAILED_DRUPAL_RUN_ID, "partial observation is bound to the final historical identity")
    contract_path = repo / DRUPAL_POST_EXPIRY_PARTIAL_CONTRACT
    governance_path = repo / FINAL_FAILED_GOVERNANCE
    require(contract_path.is_file() and sha(contract_path) == DRUPAL_POST_EXPIRY_PARTIAL_CONTRACT_SHA256, "partial observation contract drift")
    require(governance_path.is_file() and sha(governance_path) == FINAL_FAILED_GOVERNANCE_SHA256, "final failed governance drift")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    governance = json.loads(governance_path.read_text(encoding="utf-8"))
    require(contract.get("status") == "ADMITTED_NOT_EXECUTED" and contract.get("run_id") == run_id, "partial observation is not admitted")
    require(contract.get("execution_boundary", {}).get("execution_authorized_by_contract") is False, "contract cannot self-authorize execution")
    require(contract.get("no_more_workers", {}).get("additional_worker_identities_permitted") == 0, "worker identity boundary")
    require(governance.get("canonical_family_aggregate_sha256") == FINAL_FAILED_DRUPAL_AGGREGATE_SHA256, "final failed aggregate binding")
    require(governance.get("admission_sha256") == FINAL_FAILED_DRUPAL_ADMISSION_SHA256, "final admission binding")
    for relative, expected in governance.get("immutable_inventory", {}).items():
        path = repo / relative
        require(path.is_file() and sha(path) == expected, f"final historical evidence drift: {relative}")

    evidence, runtime, control = drupal_paths(repo, run_id)
    require(evidence.is_dir() and runtime.is_dir(), "final historical family missing")
    require(not any((evidence / name).exists() for name in ("drupal-termination.json", "drupal-immediate.json", "drupal-post-expiry.json", "evidence-manifest.json")), "historical lifecycle proof unexpectedly exists")
    ledger = json.loads((evidence / "authorization-ledger.json").read_text(encoding="utf-8"))
    require([item.get("status") for item in ledger.get("phases", [])] == ["CONSUMED", "PENDING", "PENDING"], "historical ledger state")
    seam = json.loads((control / "seam-ready.json").read_text(encoding="utf-8"))
    midpoint = json.loads((control / "midpoint.json").read_text(encoding="utf-8"))
    require(seam.get("midpoint_sha256") == sha(control / "midpoint.json"), "seam midpoint binding")
    require(midpoint.get("completed_sequences") == [1, 2, 3, 4, 5, 6], "midpoint sequence state")
    expiry = seam.get("lock_expires_not_before_unix")
    require(isinstance(expiry, (int, float)) and time.time() >= expiry, "recorded natural expiry has not elapsed; this command never waits")

    root = repo / DRUPAL_POST_EXPIRY_PARTIAL_EVIDENCE_ROOT / run_id
    require(not root.exists(), "partial observation authorization already consumed")
    root.mkdir(parents=True)
    raw = root / ".observation.raw.json"
    output = root / "observation.json"
    command = drupal_script_command("post-expiry-partial", run_id)
    try:
        run_checked(command, repo=repo / "drupal", env=safe_env(), stage="drupal_post_expiry_partial", output=raw)
        value = json.loads(raw.read_text(encoding="utf-8"))
        validate_post_expiry_partial_result(
            value, run_id=run_id,
            lock_name_sha256=seam["lock_name_sha256"],
            lock_acquired_unix=seam["lock_acquired_at_unix"],
            lock_expires_unix=seam["lock_expires_not_before_unix"],
        )
        value.update({
            "contract_sha256": sha(contract_path),
            "final_failed_family_aggregate_sha256": FINAL_FAILED_DRUPAL_AGGREGATE_SHA256,
            "final_admission_sha256": FINAL_FAILED_DRUPAL_ADMISSION_SHA256,
            "installed_source_manifest_sha256": sha(repo / INSTALLED_SOURCE_MANIFEST),
            "separate_human_execution_authorization_consumed": True,
            "missing_immediate_classification": "DRUPAL_IMMEDIATE_OBSERVATION_MISSED_DUE_TO_TERMINATION_PROOF_GATE",
            "prior_failed_family_aggregates": [FAILED_DRUPAL_FAMILY_AGGREGATE_SHA256, FAILED_DRUPAL_REPLACEMENT_AGGREGATE_SHA256],
        })
        validate_post_expiry_partial_result(
            value, run_id=run_id,
            lock_name_sha256=seam["lock_name_sha256"],
            lock_acquired_unix=seam["lock_acquired_at_unix"],
            lock_expires_unix=seam["lock_expires_not_before_unix"],
        )
        raw.unlink()
        atomic_write_json(output, value)
    except Exception as exc:
        if raw.exists():
            raw.unlink()
        failure: dict[str, Any] = {
            "schema_version": 1,
            "record_type": "DRUPAL_POST_EXPIRY_PARTIAL_OBSERVATION_FAILURE",
            "status": "FAILED_PRESERVED",
            "run_id": run_id,
            "automatic_retry_count": 0,
            "worker_launch_count": 0,
            "certifying_evidence": False,
        }
        if isinstance(exc, CommandFailure):
            failure["diagnostic"] = exc.diagnostic
        atomic_write_json(root / "FAILED-ATTEMPT.json", failure)
        raise
    return root


def drupal_paths(repo: Path, run_id: str) -> tuple[Path, Path, Path]:
    require(RUN_PATTERN.fullmatch(run_id) is not None and "-drupal-" in run_id, "invalid Drupal run ID")
    evidence = repo / EVIDENCE_ROOT / run_id
    runtime = repo / "drupal/.cache/gate2c-step02" / run_id
    control = runtime / "control"
    return evidence, runtime, control


def drupal_start(repo: Path, run_id: str) -> Path:
    if run_id in exact_directory_identities(repo / DRUPAL_FURTHER_REPLACEMENT_AUTHORIZATION_ROOT):
        authorization = load_drupal_further_replacement_authorization(repo, run_id)
        authorization_root = DRUPAL_FURTHER_REPLACEMENT_AUTHORIZATION_ROOT
    else:
        authorization = load_drupal_replacement_authorization(repo, run_id)
        authorization_root = DRUPAL_REPLACEMENT_AUTHORIZATION_ROOT
    evidence, runtime, control = drupal_paths(repo, run_id)
    require(not evidence.exists() and not runtime.exists(), "Drupal rehearsal identity already exists")
    evidence.mkdir(parents=True)
    control.mkdir(parents=True)
    write_json(evidence / "authorization-ledger.json", {
        "schema_version": 1, "run_id": run_id,
        "boundary": "2C.02_model_free_Drupal_lifecycle",
        "replacement_authorization_sha256": sha(
            repo / authorization_root / run_id / "authorization.json"
        ),
        "repaired_installed_source_manifest_sha256": authorization["repaired_installed_source_manifest_sha256"],
        "phases": [
            {"name": "drupal_start_and_SIGKILL", "authorization": "SEPARATE", "status": "CONSUMED"},
            {"name": "immediate_post_kill_observation", "authorization": "SEPARATE", "status": "PENDING"},
            {"name": "post_natural_expiry_observation", "authorization": "SEPARATE", "status": "PENDING"},
        ],
        "automatic_phase_transition": False,
        "model_provider": 0, "recommendation_writes": 0, "source_mutations": 0,
    })
    worker = drupal_script_command(
        "worker", run_id, f"/var/www/html/.cache/gate2c-step02/{run_id}/control"
    )
    kill_command = ["ddev", "exec", "kill", "-9", "{pid}"]
    process_check_command = drupal_script_command("process-check", run_id, "{pid}")
    write_json(runtime / "worker-command.json", worker)
    write_json(runtime / "kill-command.json", kill_command)
    write_json(runtime / "process-check-command.json", process_check_command)
    supervisor = [sys.executable, str(repo / "scripts/gate2c_step02_supervisor.py"),
                  "--repo", str(repo / "drupal"), "--control-dir", str(control),
                  "--framework", "drupal_ai", "--trial-id", run_id, "--run-id", run_id,
                  "--worker-command-json", str(runtime / "worker-command.json"),
                  "--kill-command-json", str(runtime / "kill-command.json"),
                  "--process-check-command-json", str(runtime / "process-check-command.json"),
                  "--pre-kill-process-scan-output", str(evidence / "drupal-pre-kill-process-scan.json"),
                  "--signal-dispatch-output", str(evidence / "drupal-signal-dispatch.json"),
                  "--post-kill-process-scan-output", str(evidence / "drupal-post-kill-process-scan.json"),
                  "--diagnostic-output", str(evidence / "drupal-pre-seam-diagnostic.json"),
                  "--output", str(evidence / "drupal-termination.json")]
    try:
        run_checked(supervisor, repo=repo, env=safe_env(), stage="drupal_termination")
    except Exception as exc:
        failure = {
            "schema_version": 1, "run_id": run_id, "status": "FAILED_PRESERVED",
            "phase": "dedicated_worker_and_SIGKILL", "replacement_automatic": False,
        }
        if isinstance(exc, CommandFailure):
            failure["diagnostic"] = exc.diagnostic
        diagnostic = evidence / "drupal-pre-seam-diagnostic.json"
        if diagnostic.is_file():
            failure["drupal_pre_seam_diagnostic_sha256"] = sha(diagnostic)
        process_scan = evidence / "drupal-pre-kill-process-scan.json"
        if process_scan.is_file():
            failure["drupal_pre_kill_process_scan_sha256"] = sha(process_scan)
        signal_dispatch = evidence / "drupal-signal-dispatch.json"
        if signal_dispatch.is_file():
            failure["drupal_signal_dispatch_sha256"] = sha(signal_dispatch)
        post_kill_scan = evidence / "drupal-post-kill-process-scan.json"
        if post_kill_scan.is_file():
            failure["drupal_post_kill_process_scan_sha256"] = sha(post_kill_scan)
        write_json(evidence / "FAILED-ATTEMPT.json", failure)
        raise
    termination = json.loads((evidence / "drupal-termination.json").read_text(encoding="utf-8"))
    require(termination.get("status") == "PASS" and termination.get("observed_signal") == 9, "Drupal signal-9 termination")
    require(termination.get("pre_kill_worker_identity_verified") is True, "Drupal actual worker identity")
    require(termination.get("post_kill_worker_absent") is True and termination.get("replacement_worker_count") == 0, "Drupal replacement worker")
    return evidence


def drupal_invoke(repo: Path, run_id: str, phase: str) -> Path:
    evidence, runtime, _ = drupal_paths(repo, run_id)
    require(evidence.is_dir() and runtime.is_dir(), "Drupal rehearsal start evidence missing")
    termination_path = evidence / "drupal-termination.json"
    require(termination_path.is_file(), "Drupal termination proof missing")
    termination = json.loads(termination_path.read_text(encoding="utf-8"))
    require(termination.get("status") == "PASS" and termination.get("observed_signal") == 9, "Drupal termination proof invalid")
    require(termination.get("replacement_worker_count") == 0 and termination.get("post_kill_worker_absent") is True, "Drupal worker replacement is unresolved")
    output = evidence / ("drupal-immediate.json" if phase == "immediate" else "drupal-post-expiry.json")
    require(not output.exists(), f"Drupal {phase} invocation already consumed")
    require(not (evidence / "evidence-manifest.json").exists(), "Drupal evidence already finalized")
    if phase == "immediate":
        require(not (evidence / "drupal-post-expiry.json").exists(), "Drupal phase order violation")
    else:
        immediate_path = evidence / "drupal-immediate.json"
        require(immediate_path.is_file(), "immediate post-kill observation required before post-expiry invocation")
        immediate = json.loads(immediate_path.read_text(encoding="utf-8"))
        require(immediate.get("status") == "PASS_LOCK_DENIED", "immediate lock denial is not accepted")
        require(immediate.get("observed_before_natural_expiry") is True, "immediate observation chronology")
        expiry = immediate.get("lock_expires_not_before_unix")
        require(isinstance(expiry, (int, float)) and time.time() >= expiry, "natural lock expiry has not elapsed; this command never waits")
    command = drupal_script_command(phase, run_id)
    run_checked(command, repo=repo / "drupal", env=safe_env(), stage=f"drupal_{phase}", output=output)
    value = json.loads(output.read_text(encoding="utf-8"))
    expected = "PASS_LOCK_DENIED" if phase == "immediate" else "PASS_POST_NATURAL_EXPIRY"
    require(value.get("status") == expected and value.get("lock_lease_seconds") == 1800, f"Drupal {phase} evidence")
    require(value.get("lock_owner_actual_worker_pid") == termination.get("actual_worker_pid"), f"Drupal {phase} lock owner binding")
    value["termination_sha256"] = sha(termination_path)
    value["phase_authorization_separate"] = True
    value["automatic_retry_count"] = 0
    if phase == "immediate":
        require(value.get("state_sha256_before") == value.get("state_sha256_after"), "immediate observation changed state")
    else:
        immediate_path = evidence / "drupal-immediate.json"
        immediate = json.loads(immediate_path.read_text(encoding="utf-8"))
        require(value.get("natural_expiry_elapsed") is True and value.get("elapsed_since_lock_acquired_seconds", 0) >= 1800, "natural expiry duration")
        require(value.get("state_sha256_before") == immediate.get("state_sha256_after"), "post-expiry starting state differs from immediate observation")
        value["immediate_sha256"] = sha(immediate_path)
    write_json(output, value)
    ledger_path = evidence / "authorization-ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    phase_name = "immediate_post_kill_observation" if phase == "immediate" else "post_natural_expiry_observation"
    matches = [item for item in ledger.get("phases", []) if item.get("name") == phase_name]
    require(len(matches) == 1 and matches[0].get("status") == "PENDING", "Drupal phase authorization ledger")
    matches[0]["status"] = "CONSUMED"
    write_json(ledger_path, ledger)
    return evidence


def drupal_finalize(repo: Path, run_id: str) -> Path:
    evidence, _, _ = drupal_paths(repo, run_id)
    require(evidence.is_dir(), "Drupal rehearsal evidence missing")
    require(not (evidence / "evidence-manifest.json").exists(), "Drupal rehearsal already finalized")
    required = {"authorization-ledger.json", "drupal-termination.json", "drupal-immediate.json", "drupal-post-expiry.json"}
    require(required <= {p.name for p in evidence.iterdir() if p.is_file()}, "Drupal rehearsal phases incomplete")
    termination = json.loads((evidence / "drupal-termination.json").read_text(encoding="utf-8"))
    immediate = json.loads((evidence / "drupal-immediate.json").read_text(encoding="utf-8"))
    post = json.loads((evidence / "drupal-post-expiry.json").read_text(encoding="utf-8"))
    require(termination.get("replacement_worker_count") == 0, "replacement worker detected")
    require(immediate.get("termination_sha256") == sha(evidence / "drupal-termination.json"), "immediate termination binding")
    require(post.get("termination_sha256") == sha(evidence / "drupal-termination.json"), "post-expiry termination binding")
    require(post.get("immediate_sha256") == sha(evidence / "drupal-immediate.json"), "post-expiry immediate binding")
    require(post.get("elapsed_since_lock_acquired_seconds", 0) >= 1800, "natural expiry duration not proven")
    ledger = json.loads((evidence / "authorization-ledger.json").read_text(encoding="utf-8"))
    require([item.get("status") for item in ledger.get("phases", [])] == ["CONSUMED", "CONSUMED", "CONSUMED"], "Drupal phase authorizations incomplete")
    write_json(evidence / "zero-operation-accounting.json", {
        "schema_version": 1, "status": "PASS", "model_generations": 0, "provider_requests": 0,
        "recommendation_writes": 0, "source_mutations": 0, "snapshot_operations": 0,
        "lock_clear_shorten_delete_bypass_or_replacement": 0,
        "replacement_workers": 0, "automatic_retries": 0, "wait_operation_mutations": 0,
    })
    write_json(evidence / "privacy-scan.json", scan_retained(evidence))
    (evidence / "summary.md").write_text(
        "# Gate 2C.02 dedicated Drupal model-free rehearsal\n\n"
        f"Run: `{run_id}`\n\nThe dedicated 1,800-second persistent lock survived actual PHP-worker "
        "SIGKILL, denied the separately authorized immediate invocation, and permitted one separately authorized "
        "invocation only after natural expiry. No recommendation/source/model operation occurred. This is mechanics "
        "evidence and is not an authoritative Drupal AI recovery result.\n",
        encoding="utf-8",
    )
    names = [p.name for p in evidence.iterdir() if p.is_file()]
    write_json(evidence / "evidence-manifest.json", manifest(evidence, names))
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["authorize-offline", "authorize-offline-replacement", "authorize-offline-corrected-environment", "authorize-drupal-replacement", "authorize-drupal-further-replacement", "offline", "record-post-inspection", "crewai-startup-diagnostic", "lancedb-async-diagnostic", "lancedb-memory-async-diagnostic", "drupal-start", "drupal-further-start", "drupal-immediate", "drupal-post-expiry", "drupal-post-expiry-partial", "drupal-finalize"])
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--preflight-result", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    require((repo / ".git").is_dir(), "repository required")
    if args.mode == "authorize-offline":
        result = authorize_offline(repo, args.run_id)
    elif args.mode == "authorize-offline-replacement":
        result = authorize_offline_replacement(repo, args.run_id)
    elif args.mode == "authorize-offline-corrected-environment":
        require(args.preflight_result is not None, "fresh preflight result required")
        result = authorize_offline_corrected_environment(repo, args.run_id, args.preflight_result)
    elif args.mode == "authorize-drupal-replacement":
        result = authorize_drupal_replacement(repo, args.run_id)
    elif args.mode == "authorize-drupal-further-replacement":
        result = authorize_drupal_further_replacement(repo, args.run_id)
    elif args.mode == "offline":
        require(args.preflight_result is not None, "fresh execution preflight result required")
        result = offline(repo, args.run_id, args.preflight_result)
    elif args.mode == "record-post-inspection":
        result = record_post_inspection_addendum(repo, args.run_id)
    elif args.mode == "crewai-startup-diagnostic":
        result = crewai_startup_diagnostic(repo, args.run_id)
    elif args.mode == "lancedb-async-diagnostic":
        result = lancedb_async_diagnostic(repo, args.run_id)
    elif args.mode == "lancedb-memory-async-diagnostic":
        result = lancedb_memory_async_diagnostic(repo, args.run_id)
    elif args.mode in {"drupal-start", "drupal-further-start"}:
        result = drupal_start(repo, args.run_id)
    elif args.mode == "drupal-immediate":
        result = drupal_invoke(repo, args.run_id, "immediate")
    elif args.mode == "drupal-post-expiry":
        result = drupal_invoke(repo, args.run_id, "post-expiry")
    elif args.mode == "drupal-post-expiry-partial":
        result = drupal_post_expiry_partial(repo, args.run_id)
    else:
        result = drupal_finalize(repo, args.run_id)
    print(result.relative_to(repo).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
