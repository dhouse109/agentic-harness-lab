#!/usr/bin/env python3
"""Record the human CrewAI decision and bind accepted Step 2C.02 evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

CONTRACT_SHA = "3c4801e6eb35d40d94e066c70017d3acebca95183e7e544646be6e2b40aa5ec6"
CERT_PATTERN = re.compile(r"^gate2c-step02-certification-[0-9]{8}T[0-9]{6}Z-[a-z0-9]{8}$")
STRICT = (b"sk-proj-", b"Authorization: Basic ", b"Authorization: Bearer ", b"data:image/", b"OPENAI_API_KEY=")


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_manifest(root: Path) -> None:
    manifest = load(root / "evidence-manifest.json")
    for entry in manifest["files"]:
        path = root / entry["path"]
        require(path.is_file() and path.stat().st_size == entry["size"] and sha(path) == entry["sha256"], f"evidence drift: {path}")
    for path in root.rglob("*"):
        if path.is_file():
            content = path.read_bytes()
            require(not any(token in content for token in STRICT), f"strict retained-evidence privacy failure: {path.name}")


def validate_offline(root: Path) -> None:
    verify_manifest(root)
    for origin in ("langgraph", "crewai"):
        termination = load(root / f"{origin}-termination.json")
        recovery = load(root / f"{origin}-recovery.json")
        require(termination.get("status") == "PASS" and termination.get("observed_signal") == 9, f"{origin} signal-9 proof")
        require(termination.get("actual_worker_terminated") is True and termination.get("automatic_retry_count") == 0, f"{origin} termination/retry proof")
        require(recovery.get("status") == "PASS" and recovery.get("completed_sequences") == list(range(1, 13)), f"{origin} recovery completion")
        require(recovery.get("first_post_restart_target") == 7 and recovery.get("replay_count") == 0 and recovery.get("duplicate_count") == 0, f"{origin} recovery routing")
        require(all(recovery.get(key) == 0 for key in ("model_generations", "provider_requests", "drupal_operations")), f"{origin} zero-operation accounting")
    crewai = load(root / "crewai-recovery.json")
    require(crewai.get("public_load_state_used") is True and crewai.get("public_kickoff_inputs_id_hydration_used") is True, "CrewAI public API proof")
    require(all(crewai.get(key) is False for key in ("private_restore_used", "checkpoint_config_used", "human_feedback_recovery_used")), "CrewAI prohibited mechanism")
    bootstrap = crewai.get("bootstrap_storage", {})
    require(bootstrap.get("mechanism") == ["XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME"], "CrewAI bootstrap mechanism")
    require(all(bootstrap.get(key) is True for key in ("configured_before_worker_import", "fresh_run_scoped", "writable", "separate_from_sqlite_flow_persistence", "default_home_storage_avoided")), "CrewAI bootstrap storage proof")
    provenance = load(root / "public-api-provenance.json").get("crewai_bootstrap_storage", {})
    require(provenance == bootstrap, "CrewAI bootstrap provenance differs from recovery evidence")
    controls = load(root / "negative-controls.json").get("controls", {})
    required = {"wrong_worker_pid", "wrong_run_identity", "incomplete_midpoint", "missing_signal_9", "replay", "duplicate_identity", "unapproved_invocation"}
    require(set(controls) == required and all(value == "REJECTED" for value in controls.values()), "offline negative controls")


def validate_drupal(root: Path) -> None:
    verify_manifest(root)
    termination = load(root / "drupal-termination.json")
    immediate = load(root / "drupal-immediate.json")
    post = load(root / "drupal-post-expiry.json")
    zero = load(root / "zero-operation-accounting.json")
    require(termination.get("status") == "PASS" and termination.get("observed_signal") == 9 and termination.get("automatic_retry_count") == 0, "Drupal termination proof")
    require(termination.get("pre_kill_worker_identity_verified") is True and termination.get("post_kill_worker_absent") is True, "Drupal exact worker identity/absence proof")
    require(termination.get("replacement_worker_count") == 0 and termination.get("kill_command_scope") == "EXACT_ACTUAL_PHP_WORKER_PID_ONLY", "Drupal no-replacement/exact-signal scope")
    require(isinstance(termination.get("actual_worker_pid"), int) and termination.get("actual_worker_pid") > 1, "Drupal actual worker PID")
    acquired = termination.get("lock_acquired_at_unix")
    expires = termination.get("lock_expires_not_before_unix")
    require(isinstance(acquired, (int, float)) and isinstance(expires, (int, float)), "Drupal termination lock timestamps")
    require(abs((expires - acquired) - 1800.0) < 0.001, "Drupal termination lock chronology")
    require(immediate.get("status") == "PASS_LOCK_DENIED" and immediate.get("lock_lease_seconds") == 1800 and immediate.get("lock_mutation") == "NONE", "Drupal immediate lock proof")
    require(immediate.get("termination_sha256") == sha(root / "drupal-termination.json"), "Drupal immediate termination binding")
    require(immediate.get("lock_owner_actual_worker_pid") == termination.get("actual_worker_pid"), "Drupal immediate lock owner")
    require(immediate.get("observed_before_natural_expiry") is True and immediate.get("observed_at_unix") < immediate.get("lock_expires_not_before_unix"), "Drupal immediate chronology")
    require(immediate.get("state_sha256_before") == immediate.get("state_sha256_after"), "Drupal immediate read-only state proof")
    require(post.get("status") == "PASS_POST_NATURAL_EXPIRY" and post.get("first_post_restart_target") == 7, "Drupal post-expiry proof")
    require(post.get("replay_count") == 0 and post.get("duplicate_count") == 0 and post.get("lock_mutation") == "NONE", "Drupal post-expiry accounting")
    require(post.get("termination_sha256") == sha(root / "drupal-termination.json") and post.get("immediate_sha256") == sha(root / "drupal-immediate.json"), "Drupal post-expiry chain binding")
    require(post.get("lock_owner_actual_worker_pid") == termination.get("actual_worker_pid"), "Drupal post-expiry lock owner")
    require(post.get("natural_expiry_elapsed") is True and post.get("elapsed_since_lock_acquired_seconds", 0) >= 1800, "Drupal natural expiry duration")
    require(post.get("observed_at_unix") >= post.get("lock_expires_not_before_unix"), "Drupal post-expiry chronology")
    require(post.get("state_sha256_before") == immediate.get("state_sha256_after"), "Drupal observation state continuity")
    require(all(zero.get(key) == 0 for key in ("model_generations", "provider_requests", "recommendation_writes", "source_mutations", "snapshot_operations", "lock_clear_shorten_delete_bypass_or_replacement", "replacement_workers", "automatic_retries", "wait_operation_mutations")), "Drupal zero-operation accounting")


def validate_reset(root: Path, drupal: Path | None = None) -> None:
    verify_manifest(root)
    value = load(root / "reset-restoration.json")
    require(value.get("status") == "PASS" and value.get("seeded_clean_verified") is True, "reset baseline proof")
    require(value.get("restored_exactly_once") is True and value.get("anchor_cleaned") is True, "reset restoration lifecycle")
    require(value.get("before_projection_sha256") == value.get("after_projection_sha256"), "reset exact restoration")
    require(value.get("retained_gate2b_snapshot_used_as_baseline") is False, "retained Gate 2B snapshot misuse")
    require((value.get("snapshot_creates"), value.get("seeded_clean_resets"), value.get("snapshot_restores"), value.get("temporary_snapshot_deletes")) == (1, 1, 1, 1), "reset operation accounting")
    require(value.get("forbidden_mutations_retained") == 0 and value.get("source_mutations_retained") == 0, "reset forbidden mutation accounting")
    if drupal is not None:
        require(value.get("bound_drupal_run_id") == drupal.name, "reset Drupal run binding")
        require(value.get("bound_drupal_manifest_sha256") == sha(drupal / "evidence-manifest.json"), "reset Drupal manifest binding")


def validate_decision(repo: Path, decision: Path) -> dict[str, Any]:
    schema = load(repo / "shared/schemas/gate2c-step02-crewai-decision.schema.json")
    Draft202012Validator.check_schema(schema)
    value = load(decision)
    Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(value)
    require(value.get("schema_version") == 2, "CrewAI decision schema version")
    require(value.get("rehearsal_run_id") == "gate2c-step02-offline-20260930T222029Z-24c7b158", "CrewAI decision rehearsal identity")
    require(value.get("contract_sha256") == CONTRACT_SHA, "CrewAI decision contract binding")
    require(value.get("machine_recommendation") == "APPROVAL_READY", "CrewAI machine recommendation")
    require(value.get("human_decision") == "APPROVED" and value.get("decided_by") == "human_operator", "CrewAI human decision")
    require(value.get("pass_family_binding", {}).get("evidence_manifest_sha256") == "730b892d232a3dea7e77e4391b7beec5d40e807b76f99b13bb0036ae00cf74ca", "CrewAI decision evidence binding")
    require(value.get("pass_family_binding", {}).get("finalization_sha256") == "d882c8339025c1ba7e510abb19984fc4724e2a594a190760c07f95db034fd8d8", "CrewAI decision finalization binding")
    require(value.get("lifecycle_boundary") == {
        "step_2c02_certification": "NOT_PERFORMED",
        "gate_2c": "DEFERRED_UNCLAIMED",
        "gate_2": "NOT_COMPLETE",
        "additional_rehearsal_authorized": False,
        "step_2c03_authorized": False,
        "latest_pointer_update_authorized": False,
    }, "CrewAI decision lifecycle separation")
    return value


def lifecycle_updates(repo: Path) -> dict[Path, str]:
    replacements = {
        "AGENTS.md": [
            ("> Gate 2C Step 2C.01 is complete. Step 2C.02 remains incomplete and uncertified after a finalized model-free rehearsal PASS and explicit human approval of the CrewAI recovery architecture only. Gate 2C remains `DEFERRED_UNCLAIMED`, Gate 2 remains `NOT_COMPLETE`, and all remaining Step 2C.02 work requires separate approval.",
             "> Gate 2C Steps 2C.01 and 2C.02 are complete after accepted model-free contract certification and model-free injector/recovery rehearsals. Gate 2C remains `DEFERRED_UNCLAIMED`, Gate 2 remains `NOT_COMPLETE`, and Step 2C.03 preparation is the next separately approved boundary; no live execution is authorized."),
            ("**Step 2C.01:** complete after accepted model-free contract certification. It freezes the target-6/7 semantic seam, evidence overlays, accounting/classification rules, protected-tree policy, and approval ledger without executing Gate 2C. The corrected-environment Step 2C.02 offline rehearsal is finalized PASS, and the public `SQLiteFlowPersistence.load_state(...)` plus `Flow.kickoff(inputs={\"id\": same_flow_id})` CrewAI recovery candidate is explicitly human-approved for the model-free architecture proof only. Step 2C.02 remains uncertified. The Drupal persistent-lock policy is approved as contract policy only, not as authorization to execute recovery.",
             "**Step 2C.01:** complete after accepted model-free contract certification. It freezes the target-6/7 semantic seam, evidence overlays, accounting/classification rules, protected-tree policy, and approval ledger without executing Gate 2C.\n\n**Step 2C.02:** complete after accepted model-free external-supervisor, framework-routing, persistent-lock, reset/restoration, and CrewAI public-recovery architecture evidence. This proves rehearsal mechanics only, not authoritative framework recovery behavior."),
            ("**Current package boundary:** remaining Step 2C.02 model-free Drupal/reset proof and later certification remain separately authorized. Gate 2C remains `DEFERRED_UNCLAIMED`; no model-backed execution, Drupal reset, snapshot operation, Step 2C.02 certification, or Step 2C.03 activity is authorized by the architecture decision.",
             "**Next package:** `gate-2c-step03-three-framework-failure-recovery-execution` may be prepared and previewed only after separate authorization. Gate 2C remains `DEFERRED_UNCLAIMED`; no model-backed execution is authorized by Step 2C.02."),
        ],
        "PLAN.md": [
            ("> Gate 2C Step 2C.01 is complete. Step 2C.02 remains incomplete and uncertified; its corrected-environment offline rehearsal is finalized PASS and its CrewAI recovery architecture is human-approved only for the model-free proof. Gate 2C remains `DEFERRED_UNCLAIMED` and Gate 2 remains `NOT_COMPLETE`.",
             "> Gate 2C Steps 2C.01 and 2C.02 are complete at model-free boundaries. Gate 2C remains `DEFERRED_UNCLAIMED`; Gate 2 remains `NOT_COMPLETE`; Step 2C.03 preparation is next but separately authorized, and live execution remains unauthorized."),
            ("> Phase 0, Gate 0.5, and Gate 1 are complete. Drupal AI, LangGraph, and CrewAI are certified and frozen. Steps 2B.01–2B.08 and the model-free Step 2C.01 contract boundary are complete. One model-free Step 2C.02 rehearsal is finalized PASS; no authoritative Gate 2C failure trial has run.",
             "> Phase 0, Gate 0.5, and Gate 1 are complete. Drupal AI, LangGraph, and CrewAI are certified and frozen. Steps 2B.01–2B.08 and model-free Steps 2C.01–2C.02 are complete. No authoritative Gate 2C failure trial has run."),
            ("- [ ] Step 2C.02 — shared failure injector and model-free rehearsals; corrected-environment offline PASS and explicit CrewAI architecture approval are recorded, while Drupal/reset proof and certification remain open; no authoritative comparison.",
             "- [x] Step 2C.02 — shared failure injector and model-free rehearsals; explicit CrewAI architecture approval; no authoritative comparison."),
            ("**Current package boundary:** complete the remaining separately authorized Step 2C.02 model-free Drupal/reset proof before any separately authorized certification package.",
             "**Next package:** `gate-2c-step03-three-framework-failure-recovery-execution` (preparation/preview only until separately approved; no live execution authorization)."),
        ],
        "README.md": [
            ("> Gate 2C Step 2C.01 is complete. Step 2C.02 remains incomplete and uncertified after one finalized model-free rehearsal PASS and explicit human approval of the CrewAI recovery architecture only. Gate 2C remains `DEFERRED_UNCLAIMED`, no authoritative shared failure/recovery trial has run, and Gate 2 remains `NOT_COMPLETE`.",
             "> Gate 2C Steps 2C.01 and 2C.02 are complete at model-free boundaries. Gate 2C remains `DEFERRED_UNCLAIMED`; no authoritative shared failure/recovery trial has run, and Gate 2 remains `NOT_COMPLETE`."),
            ("- **Step 2C.01:** complete after model-free contract certification. Step 2C.02 has a finalized corrected-environment offline PASS and a human-approved public-only CrewAI recovery architecture, but remains uncertified; remaining Drupal/reset proof and every later lifecycle action require separate authorization.",
             "- **Steps 2C.01–2C.02:** complete after model-free contract certification and accepted injector/recovery rehearsals; the public-only CrewAI recovery architecture is human-approved for Gate 2C, and `gate-2c-step03-three-framework-failure-recovery-execution` preparation is next but separately authorized. No live execution is authorized."),
        ],
        "docs/CURRENT-STATUS.md": [
            ("> **Current authoritative state:** Step 2C.01 is complete. Step 2C.02 remains incomplete and uncertified after a finalized corrected-environment model-free rehearsal PASS and explicit human approval of the CrewAI recovery architecture only. Gate 2C remains `DEFERRED_UNCLAIMED`, and Gate 2 overall remains `NOT_COMPLETE`.",
             "> **Current authoritative state:** Steps 2C.01 and 2C.02 are complete after accepted model-free contract certification and injector/recovery rehearsals. Gate 2C remains `DEFERRED_UNCLAIMED`, no authoritative experiment has run, and Gate 2 overall remains `NOT_COMPLETE`."),
            ("**Gate 2C.01 predecessor:** `main` at normal Step 2B.08 merge `c022619e220715be17e541650c261ea0b568704b`",
             "**Gate 2C.02 predecessor:** `main` at merged Step 2C.01 `03816e141f77820e42486fcbad9db244939cd7a8`"),
            ("- **Gate 2C — shared three-framework failure/recovery:** `DEFERRED_UNCLAIMED`; a model-free injector/recovery rehearsal is finalized PASS, but no authoritative run or recovery result exists.",
             "- **Gate 2C — shared three-framework failure/recovery:** `DEFERRED_UNCLAIMED`; the injector and mappings are proven model-free, but no authoritative run or recovery result exists."),
            ("- **Step 2C.02:** incomplete and uncertified; corrected-environment offline rehearsal `gate2c-step02-offline-20260930T222029Z-24c7b158` is finalized PASS, while required Drupal/reset proof and final certification remain open.\n- **CrewAI Gate 2C recovery architecture:** explicitly human-approved for the model-free recovery proof, with machine recommendation `APPROVAL_READY` kept distinct from the human decision.\n- **Current package boundary:** remaining Step 2C.02 model-free Drupal/reset proof requires separate authorization; Step 2C.02 certification and Step 2C.03 are not authorized.",
             "- **Step 2C.02:** complete after accepted model-free hard-termination, framework-routing, persistent-lock, reset/restoration, and privacy evidence.\n- **CrewAI Gate 2C recovery architecture:** public-only same-Flow-identity candidate explicitly human-approved after model-free proof.\n- **Next package:** `gate-2c-step03-three-framework-failure-recovery-execution`; preparation requires separate authorization and live execution remains unauthorized."),
        ],
    }
    updated: dict[Path, str] = {}
    for relative, pairs in replacements.items():
        path = repo / relative
        text = path.read_text(encoding="utf-8")
        for old, new in pairs:
            require(text.count(old) == 1, f"lifecycle predecessor text drift: {relative}")
            text = text.replace(old, new)
        updated[path] = text
    return updated


def record_decision(repo: Path, rehearsal: Path, decision: str, decision_id: str) -> Path:
    raise RuntimeError(
        "CrewAI architecture decision is package-governed and already singular; "
        "a second direct decision record is prohibited"
    )


def certify(repo: Path, run_id: str, offline: Path, drupal: Path, reset: Path, decision: Path) -> Path:
    require(CERT_PATTERN.fullmatch(run_id) is not None, "certification run ID")
    validate_offline(offline)
    validate_drupal(drupal)
    validate_reset(reset, drupal)
    decision_value = validate_decision(repo, decision)
    updated_docs = lifecycle_updates(repo)
    root = repo / "evidence/gates/gate-2c/step02-certification" / run_id
    pointer = repo / "evidence/gates/gate-2c/step02-certification/GATE2C-STEP02-LATEST.txt"
    require(not root.exists() and not pointer.exists(), "certification identity/pointer already exists")
    root.mkdir(parents=True)
    bindings = []
    for label, source in (("offline", offline), ("drupal", drupal), ("reset", reset)):
        bindings.append({"label": label, "path": source.relative_to(repo).as_posix(), "manifest_sha256": sha(source / "evidence-manifest.json")})
    bindings.append({"label": "crewai_human_decision", "path": decision.relative_to(repo).as_posix(), "sha256": sha(decision)})
    write(root / "certification.json", {
        "schema_version": 1, "status": "PASS", "run_id": run_id, "step": "2C.02",
        "contract_sha256": CONTRACT_SHA, "model_free": True, "authoritative_experiment_executed": False,
        "external_supervisor_proven": True, "all_three_recovery_mappings_accepted": True,
        "crewai_human_decision": "APPROVED", "gate_2c": "DEFERRED_UNCLAIMED", "gate_2": "NOT_COMPLETE",
        "step_2c03_live_execution_authorized": False,
    })
    write(root / "predecessor-bindings.json", {
        "schema_version": 1, "gate2c_contract_sha256": CONTRACT_SHA,
        "gate1_freeze_sha256": "2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd",
        "gate2a_freeze_sha256": "a28361c34b9d1c2089eee786324ad34cffbf54e3495f59a276c489865e5630f0",
        "gate2b_freeze_sha256": "74e2baad0cbe612dcd7e72ccdc264b01960ee12e09cfb0ae3154969b6055c206",
        "retained_snapshot_sha256": "4ba4cece2d30a5f90699afdf9a2ab2094f0d902213c66cdc0b40dfa466094906",
    })
    write(root / "rehearsal-bindings.json", {"schema_version": 1, "bindings": bindings})
    write(root / "authorization-ledger.json", {
        "schema_version": 1, "package_installation": "AUTHORIZED_SEPARATELY",
        "offline_SIGKILL_rehearsal": "AUTHORIZED_SEPARATELY",
        "Drupal_and_reset_rehearsal": "AUTHORIZED_SEPARATELY",
        "CrewAI_architecture_decision": "EXPLICIT_HUMAN_APPROVED",
        "certification": "AUTHORIZED_SEPARATELY", "Gate_2C_03_live_execution": "NOT_AUTHORIZED",
    })
    write(root / "privacy-scan.json", {
        "status": "PASS", "credentials_retained": False, "authorization_headers_retained": False,
        "raw_image_or_data_url_retained": False, "hidden_reasoning_retained": False,
    })
    (root / "summary.md").write_text(
        "# Gate 2C.02 certification\n\n"
        "Step 2C.02 passed model-free injector, routing, persistent-lock, and reset/restoration mechanics. "
        "The human operator approved the public-only CrewAI recovery candidate. No authoritative model-backed "
        "recovery comparison ran, Gate 2C remains deferred and unclaimed, and Gate 2 remains incomplete.\n",
        encoding="utf-8",
    )
    names = sorted(p.name for p in root.iterdir() if p.is_file())
    write(root / "evidence-manifest.json", {
        "schema_version": 1,
        "files": [{"path": name, "sha256": sha(root / name), "size": (root / name).stat().st_size} for name in names],
    })
    pointer.write_text(root.relative_to(repo).as_posix() + "\n", encoding="utf-8")
    for path, text in updated_docs.items():
        path.write_text(text, encoding="utf-8")
    return root


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    decision = sub.add_parser("decision")
    decision.add_argument("--repo", required=True, type=Path)
    decision.add_argument("--rehearsal", required=True, type=Path)
    decision.add_argument("--human-decision", required=True, choices=["APPROVED", "REJECTED"])
    decision.add_argument("--decision-id", required=True)
    cert = sub.add_parser("certify")
    cert.add_argument("--repo", required=True, type=Path)
    cert.add_argument("--run-id", required=True)
    cert.add_argument("--offline", required=True, type=Path)
    cert.add_argument("--drupal", required=True, type=Path)
    cert.add_argument("--reset", required=True, type=Path)
    cert.add_argument("--decision", required=True, type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    if args.mode == "decision":
        result = record_decision(repo, args.rehearsal.resolve(), args.human_decision, args.decision_id)
    else:
        result = certify(repo, args.run_id, args.offline.resolve(), args.drupal.resolve(), args.reset.resolve(), args.decision.resolve())
    print(result.relative_to(repo).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
