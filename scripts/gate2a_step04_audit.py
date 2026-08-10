#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

EXPECTED_GATE05 = "99c9fdcbec87476e3dc61c3f9d81532b6b9629f6222f5ac262e62f56e984a87a"
EXPECTED_GATE1 = "2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd"
EXPECTED_GATE2A = "1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b"
EXPECTED_PREDECESSOR_MERGE = "aae7f1e1dea5b30e51a304bf975ec313b96d9605"
EXPECTED_STEP03_LIVE = "evidence/gates/gate-2a/tool-adapters/gate2a-step03-20260809T233127Z-2375581"
EXPECTED_STEP03_VERIFICATION = "evidence/gates/gate-2a/tool-adapters/gate2a-step03-verification-20260810T020210Z-2410520"
ACTIVE_PACKAGE = "gate-2a-step04-langgraph-state-and-sqlite-checkpoint-proof-v1.0.6"
NEXT_PACKAGE = "gate-2a-step05-langgraph-canonical-vertical-slice-v1.0.0"
REQUIRED_FILES = {
    "run-id.txt",
    "checkpoint-config.json",
    "process-1-events.jsonl",
    "process-2-events.jsonl",
    "state-before.json",
    "state-after-reload.json",
    "isolation-negative-control.json",
    "persisted-field-audit.json",
    "state-before-schema-validation.json",
    "state-after-reload-schema-validation.json",
    "runtime-db-sha256.txt",
    "secret-scan.log",
    "summary.json",
    "summary.md",
    "package-files-sha256.txt",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(ok: bool, message: str) -> None:
    if not ok:
        raise SystemExit(f"[ERROR] {message}")


def check_manifest(run_dir: Path) -> None:
    rows = (run_dir / "package-files-sha256.txt").read_text(encoding="utf-8").splitlines()
    seen = set()
    for row in rows:
        digest, name = row.split("  ", 1)
        path = run_dir / name
        require(path.is_file(), f"Evidence manifest file missing: {name}")
        require(sha256(path) == digest, f"Evidence checksum mismatch: {name}")
        seen.add(name)

    base = REQUIRED_FILES - {"package-files-sha256.txt"}
    repair_files = {"run-failure.txt", "bookkeeping-repair.json"}
    actual = {
        p.name for p in run_dir.iterdir()
        if p.is_file() and p.name != "package-files-sha256.txt"
    }

    if "bookkeeping-repair.json" in actual:
        require("run-failure.txt" in actual, "Bookkeeping repair exists without retained wrapper failure marker")
        expected = base | repair_files
        require(seen == expected, f"Repaired evidence manifest coverage mismatch: expected={sorted(expected)} observed={sorted(seen)}")
        require(actual == expected, f"Repaired retained-file coverage mismatch: expected={sorted(expected)} actual={sorted(actual)}")
        repair = json.loads((run_dir / "bookkeeping-repair.json").read_text(encoding="utf-8"))
        require(repair.get("schema_version") == 1, "Bookkeeping repair schema version differs")
        require(repair.get("status") == "pass", "Bookkeeping repair is not pass")
        require(repair.get("repair_type") == "post-proof-manifest-auditor-mismatch", "Bookkeeping repair type differs")
        require(repair.get("langgraph_rerun_performed") is False, "Bookkeeping repair claims a LangGraph rerun")
        require(repair.get("underlying_proof_summary_status") == "pass", "Bookkeeping repair does not preserve PASS proof summary")
        require(repair.get("original_manifest_omitted_by_auditor") == "run-id.txt", "Bookkeeping repair root cause differs")
    else:
        require(seen == base, f"Evidence manifest coverage mismatch: expected={sorted(base)} observed={sorted(seen)}")
        require(actual == base, f"Retained-file coverage mismatch: expected={sorted(base)} actual={sorted(actual)}")


def check_docs(repo: Path, state: str, run_rel: str | None) -> None:
    agents = (repo / "AGENTS.md").read_text(encoding="utf-8")
    plan = (repo / "PLAN.md").read_text(encoding="utf-8")
    readme = (repo / "README.md").read_text(encoding="utf-8")
    status = (repo / "docs/CURRENT-STATUS.md").read_text(encoding="utf-8")
    if state == "active":
        require(f"**Active package:** `{ACTIVE_PACKAGE}`." in agents, "AGENTS active package missing")
        require(f"```text\n{ACTIVE_PACKAGE}\n```" in plan, "PLAN active package missing")
        require(f"- **Active package:** `{ACTIVE_PACKAGE}`." in readme, "README active package missing")
        require(f"- **Active package:** `{ACTIVE_PACKAGE}`." in status, "CURRENT active package missing")
        require("- [ ] Step 2A.04 — LangGraph state and SQLite checkpoint proof" in plan, "PLAN Step 2A.04 must remain unchecked before proof")
    else:
        require(run_rel is not None, "Complete document audit requires run path")
        evidence_line = f"Accepted Step 2A.04 evidence run: `{run_rel}`"
        require("**Step 2A.04:** complete." in agents and evidence_line in agents, "AGENTS completion missing")
        require("**Completed Step 2A.04 package:**" in plan and evidence_line in plan, "PLAN completion missing")
        require("- [x] Step 2A.04 — LangGraph state and SQLite checkpoint proof" in plan, "PLAN Step 2A.04 checkbox not complete")
        require(f"`{NEXT_PACKAGE}`" in agents and f"`{NEXT_PACKAGE}`" in readme and f"`{NEXT_PACKAGE}`" in status, "Step 2A.05 next-package marker missing")
        require(evidence_line in readme and evidence_line in status, "Accepted Step 2A.04 evidence marker missing")


def check_sources(repo: Path) -> None:
    required = [
        "docs/gates/GATE-2A-STEP04-LANGGRAPH-STATE-AND-SQLITE-CHECKPOINT-PROOF.md",
        "langchain/agentic_harness_langgraph/state.py",
        "scripts/gate2a_step04_process1.py",
        "scripts/gate2a_step04_process2.py",
        "scripts/gate2a_step04_finalize.py",
        "scripts/gate2a_step04_state.py",
        "scripts/gate2a_step04_audit.py",
        "scripts/run-gate2a-step04.sh",
    ]
    for rel in required:
        require((repo / rel).is_file(), f"Installed Step 2A.04 file missing: {rel}")

    # Scan only the executable state/checkpoint implementation surface.
    # The auditor itself necessarily names the forbidden tokens below and must
    # not be included in the source corpus it evaluates.
    boundary_scan_files = [
        "langchain/agentic_harness_langgraph/state.py",
        "scripts/gate2a_step04_process1.py",
        "scripts/gate2a_step04_process2.py",
        "scripts/gate2a_step04_finalize.py",
        "scripts/run-gate2a-step04.sh",
    ]
    source_text = "\n".join(
        (repo / rel).read_text(encoding="utf-8")
        for rel in boundary_scan_files
    )
    forbidden = [
        "ChatOpenAI(",
        "from langchain_openai",
        "DrupalClient(",
        "from shared.drupal_client",
        "submit_recommendation(",
    ]
    for needle in forbidden:
        require(
            needle not in source_text,
            f"Step 2A.04 implementation crosses model/Drupal boundary: {needle}",
        )


def check_frozen(repo: Path) -> None:
    require(sha256(repo / "shared/contracts/GATE05-SUBSTRATE-FREEZE.json") == EXPECTED_GATE05, "Gate 0.5 freeze changed")
    require(sha256(repo / "shared/contracts/GATE1-DRUPAL-AI-FREEZE.json") == EXPECTED_GATE1, "Gate 1 freeze changed")
    require(sha256(repo / "shared/contracts/GATE2A-LANGGRAPH-BATCH-CONTRACT.json") == EXPECTED_GATE2A, "Gate 2A contract changed")



def check_step03_predecessor(repo: Path) -> None:
    """Verify the accepted Step 2A.03 boundary without re-entering its lifecycle audit.

    The complete-state Step 2A.03 auditor intentionally requires the old
    Step 2A.04 next-package marker. Once Step 2A.04 is active, that document
    lifecycle assertion is no longer true. We therefore preserve the historical
    auditor unchanged and verify predecessor integrity directly here.
    """
    protected = [
        "docs/gates/GATE-2A-STEP03-LANGGRAPH-TOOL-ADAPTERS.md",
        "langchain/agentic_harness_langgraph/__init__.py",
        "langchain/agentic_harness_langgraph/tools.py",
        "scripts/gate2a_step03_audit.py",
        "scripts/gate2a_step03_compliance_state.py",
        "scripts/gate2a_step03_compliance_verify.py",
        "scripts/gate2a_step03_exercise.py",
        "scripts/gate2a_step03_schema_validate.py",
        "scripts/gate2a_step03_state.py",
        "scripts/run-gate2a-step03.sh",
        "scripts/run-gate2a-step03-compliance.sh",
    ]
    for rel in protected:
        require(
            subprocess.run(
                ["git", "-C", str(repo), "diff", "--quiet", EXPECTED_PREDECESSOR_MERGE, "--", rel]
            ).returncode == 0,
            f"Accepted Step 2A.03 implementation changed from predecessor merge: {rel}",
        )

    evidence_root = repo / "evidence/gates/gate-2a/tool-adapters"
    live_ptr = evidence_root / "GATE2A-STEP03-LATEST.txt"
    verify_ptr = evidence_root / "GATE2A-STEP03-VERIFICATION-LATEST.txt"
    require(live_ptr.is_file(), "Accepted Step 2A.03 live pointer missing")
    require(verify_ptr.is_file(), "Accepted Step 2A.03 verification pointer missing")
    require(live_ptr.read_text(encoding="utf-8").strip() == EXPECTED_STEP03_LIVE,
            "Accepted Step 2A.03 live pointer changed")
    require(verify_ptr.read_text(encoding="utf-8").strip() == EXPECTED_STEP03_VERIFICATION,
            "Accepted Step 2A.03 verification pointer changed")

    for rel in [EXPECTED_STEP03_LIVE, EXPECTED_STEP03_VERIFICATION]:
        run_dir = repo / rel
        manifest = run_dir / "package-files-sha256.txt"
        require(manifest.is_file(), f"Step 2A.03 evidence manifest missing: {rel}")
        for row in manifest.read_text(encoding="utf-8").splitlines():
            digest, name = row.split("  ", 1)
            path = run_dir / name
            require(path.is_file(), f"Step 2A.03 evidence file missing: {rel}/{name}")
            require(sha256(path) == digest, f"Step 2A.03 evidence checksum mismatch: {rel}/{name}")

    for rel in ["AGENTS.md", "PLAN.md", "README.md", "docs/CURRENT-STATUS.md"]:
        value = (repo / rel).read_text(encoding="utf-8")
        require("Accepted Step 2A.03 evidence run:" in value,
                f"Step 2A.03 accepted-live marker missing in {rel}")
        require("Accepted Step 2A.03 compliance verification:" in value,
                f"Step 2A.03 accepted-verification marker missing in {rel}")

def check_schema_and_adr(repo: Path) -> None:
    schema = json.loads((repo / "shared/schemas/langgraph-run-state.schema.json").read_text(encoding="utf-8"))
    required = set(schema.get("required", []))
    for key in [
        "run_id", "framework_origin", "thread_id", "checkpoint_backend",
        "target_sequence_hash", "next_target_index", "completed_target_identities",
        "recommendation_ids", "validation_results", "continuation_boundary_armed",
        "continuation_boundary_reached", "gate2c_failure_injection_fired",
        "prompt_version", "model_id",
    ]:
        require(key in required, f"Frozen LangGraph state schema required field missing: {key}")
    require(schema["properties"]["checkpoint_backend"].get("const") == "sqlite", "Frozen checkpoint backend is not sqlite")
    adr = (repo / "docs/decisions/ADR-0010-langgraph-runtime-and-checkpoint-path.md").read_text(encoding="utf-8")
    for needle in [
        "langgraph.checkpoint.sqlite.SqliteSaver",
        "langchain/.gate2a-runtime/<run-id>.sqlite",
        "run_id` as `configurable.thread_id",
    ]:
        require(needle in adr, f"ADR-0010 runtime decision missing: {needle}")


def check_evidence(repo: Path, run_dir: Path) -> None:
    for name in REQUIRED_FILES:
        require((run_dir / name).is_file(), f"Required Step 2A.04 evidence missing: {name}")
    check_manifest(run_dir)

    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    require(summary.get("status") == "pass", "Step 2A.04 summary is not pass")
    require(summary.get("framework") == "langgraph", "Framework mismatch")
    require(summary.get("process_boundary_reload_observed") is True, "Cross-process reload not proven")
    require(summary.get("same_thread_state_equal") is True, "Same-thread state equality not proven")
    require(summary.get("thread_id_equals_run_id") is True, "run_id/thread_id identity not proven")
    require(summary.get("checkpoint_backend") == "sqlite", "SQLite checkpoint backend not proven")
    require(summary.get("next_target_index") == 3, "Deterministic next_target_index is not 3")
    require(summary.get("completed_sequences") == [1, 2, 3], "Completed target order is not [1,2,3]")
    require(summary.get("negative_control_empty") is True, "Thread isolation negative control failed")
    require(summary.get("state_before_schema_valid") is True, "Pre-reload state schema validation failed")
    require(summary.get("state_after_reload_schema_valid") is True, "Reloaded state schema validation failed")
    require(summary.get("persisted_state_authorized") is True, "Persisted state authorization/privacy audit failed")
    for flag in [
        "raw_image_bytes_or_data_urls_persisted",
        "credentials_or_auth_material_persisted",
        "article_body_or_hidden_reasoning_persisted",
        "shared_runtime_storage_used",
        "model_call_performed",
        "provider_call_performed",
        "drupal_call_performed",
        "drupal_mutation_performed",
        "recommendation_write_performed",
        "continuation_boundary_armed",
        "continuation_boundary_reached",
        "gate2c_failure_injection_fired",
    ]:
        require(summary.get(flag) is False, f"Boundary flag must be false: {flag}")

    before = json.loads((run_dir / "state-before.json").read_text(encoding="utf-8"))
    after = json.loads((run_dir / "state-after-reload.json").read_text(encoding="utf-8"))
    require(before == after, "Retained pre/reload state differs")
    require(before.get("run_id") == before.get("thread_id"), "Retained run_id/thread_id differ")
    require(before.get("next_target_index") == 3, "Retained next_target_index differs")
    require([x["sequence"] for x in before.get("completed_target_identities", [])] == [1,2,3], "Retained completed target order differs")

    # Runtime DB is intentionally gitignored and may be absent in another clone.
    db_rel = summary["runtime_db_relative_path"]
    db_path = repo / db_rel
    if db_path.is_file():
        require(sha256(db_path) == summary["runtime_db_sha256"], "Present runtime DB hash differs from retained evidence")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--document-state", choices=["active", "complete"], required=True)
    ap.add_argument("--run-dir")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    check_frozen(repo)
    check_schema_and_adr(repo)
    check_sources(repo)

    # Step 2A.03 lifecycle audit already passed before installation. Once
    # Step 2A.04 is active, re-running that historical complete-state lifecycle
    # audit would be invalid because it requires the old successor marker.
    check_step03_predecessor(repo)

    run_dir = None
    run_rel = None
    if args.run_dir:
        run_dir = Path(args.run_dir)
        if not run_dir.is_absolute():
            run_dir = repo / run_dir
        run_dir = run_dir.resolve()
        run_rel = str(run_dir.relative_to(repo))
    elif args.document_state == "complete":
        pointer = repo / "evidence/gates/gate-2a/checkpoint-proof/GATE2A-STEP04-LATEST.txt"
        require(pointer.is_file(), "Step 2A.04 accepted evidence pointer missing")
        run_rel = pointer.read_text(encoding="utf-8").strip()
        run_dir = (repo / run_rel).resolve()

    check_docs(repo, args.document_state, run_rel if args.document_state == "complete" else None)
    if run_dir is not None:
        check_evidence(repo, run_dir)

    print("[PASS] Gate 2A Step 2A.04 audit passed.")
    if run_rel:
        print(f"[PASS] Evidence: {run_rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
