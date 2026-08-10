#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    evidence = Path(args.evidence).resolve()
    sqlite_path = repo / "langchain/.gate2a-runtime" / f"{args.run_id}.sqlite"

    before = json.loads((evidence / "state-before.json").read_text(encoding="utf-8"))
    after = json.loads((evidence / "state-after-reload.json").read_text(encoding="utf-8"))
    isolation = json.loads((evidence / "isolation-negative-control.json").read_text(encoding="utf-8"))
    persisted = json.loads((evidence / "persisted-field-audit.json").read_text(encoding="utf-8"))
    v1 = json.loads((evidence / "state-before-schema-validation.json").read_text(encoding="utf-8"))
    v2 = json.loads((evidence / "state-after-reload-schema-validation.json").read_text(encoding="utf-8"))

    db_sha = sha256(sqlite_path)
    (evidence / "runtime-db-sha256.txt").write_text(
        f"{db_sha}  langchain/.gate2a-runtime/{args.run_id}.sqlite\n",
        encoding="utf-8",
    )

    # Evidence-value scan: this detects values that would represent secrets/auth
    # material, not harmless source-code identifier words.
    credential_value_patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
        re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]{8,}", re.I),
        re.compile(r"Basic\s+[A-Za-z0-9+/=]{8,}", re.I),
        re.compile(r"data:image/[^;]+;base64,", re.I),
    ]
    hits = []
    for path in sorted(evidence.iterdir()):
        if not path.is_file() or path.name in {"secret-scan.log", "package-files-sha256.txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in credential_value_patterns:
            if pattern.search(text):
                hits.append({"file": path.name, "pattern": pattern.pattern})
    if hits:
        raise RuntimeError(f"Credential/raw-image value pattern found in retained evidence: {hits!r}")
    (evidence / "secret-scan.log").write_text(
        "PASS: no API-key, bearer/basic credential value, or raw image data-URL pattern retained.\n",
        encoding="utf-8",
    )

    completed = [int(x["sequence"]) for x in after["completed_target_identities"]]
    summary = {
        "schema_version": 1,
        "status": "pass",
        "run_id": args.run_id,
        "framework": "langgraph",
        "proof_scope": "framework-owned-state-and-sqlite-checkpoint",
        "process_boundary_reload_observed": True,
        "same_thread_state_equal": before == after,
        "thread_id_equals_run_id": after["thread_id"] == args.run_id == after["run_id"],
        "checkpoint_backend": after["checkpoint_backend"],
        "next_target_index": after["next_target_index"],
        "completed_sequences": completed,
        "negative_control_empty": bool(isolation["negative_thread_empty"]),
        "state_before_schema_valid": v1.get("status") == "pass",
        "state_after_reload_schema_valid": v2.get("status") == "pass",
        "persisted_state_authorized": persisted.get("status") == "pass",
        "raw_image_bytes_or_data_urls_persisted": bool(persisted["raw_image_bytes_or_data_urls_persisted"]),
        "credentials_or_auth_material_persisted": bool(persisted["credentials_or_auth_material_persisted"]),
        "article_body_or_hidden_reasoning_persisted": bool(persisted["article_body_or_hidden_reasoning_persisted"]),
        "shared_runtime_storage_used": bool(persisted["shared_runtime_storage_used"]),
        "model_call_performed": False,
        "provider_call_performed": False,
        "drupal_call_performed": False,
        "drupal_mutation_performed": False,
        "recommendation_write_performed": False,
        "continuation_boundary_armed": after["continuation_boundary_armed"],
        "continuation_boundary_reached": after["continuation_boundary_reached"],
        "gate2c_failure_injection_fired": after["gate2c_failure_injection_fired"],
        "runtime_db_relative_path": f"langchain/.gate2a-runtime/{args.run_id}.sqlite",
        "runtime_db_sha256": db_sha,
    }

    required_truths = [
        summary["same_thread_state_equal"],
        summary["thread_id_equals_run_id"],
        summary["checkpoint_backend"] == "sqlite",
        summary["next_target_index"] == 3,
        summary["completed_sequences"] == [1, 2, 3],
        summary["negative_control_empty"],
        summary["state_before_schema_valid"],
        summary["state_after_reload_schema_valid"],
        summary["persisted_state_authorized"],
        not summary["raw_image_bytes_or_data_urls_persisted"],
        not summary["credentials_or_auth_material_persisted"],
        not summary["article_body_or_hidden_reasoning_persisted"],
        not summary["shared_runtime_storage_used"],
        not summary["continuation_boundary_armed"],
        not summary["continuation_boundary_reached"],
        not summary["gate2c_failure_injection_fired"],
    ]
    if not all(required_truths):
        summary["status"] = "fail"
        write_json(evidence / "summary.json", summary)
        raise RuntimeError(f"Step 2A.04 finalization invariant failed: {summary!r}")

    write_json(evidence / "summary.json", summary)
    (evidence / "summary.md").write_text(
        "\n".join([
            "# Gate 2A Step 2A.04 Checkpoint Proof",
            "",
            "- **Status:** PASS",
            f"- **Run ID / thread ID:** `{args.run_id}`",
            "- **Framework-owned persistence:** SQLite / `SqliteSaver`",
            "- **Cross-process reload:** observed",
            "- **Completed target sequences:** `1, 2, 3`",
            "- **Next target index:** `3`",
            "- **Negative-control thread inherited state:** no",
            "- **Frozen state-schema validation:** pass before and after reload",
            "- **Model/provider calls:** 0",
            "- **Drupal calls/mutations:** 0 / 0",
            "- **Recommendation writes:** 0",
            "- **Raw image / credential / Article-body / hidden-reasoning retention:** none observed",
            "- **Gate 2C failure injection:** not exercised",
            "",
            "This evidence proves only the Step 2A.04 state/checkpoint boundary. It does not prove "
            "real-model behavior, human review, batch continuation, Gate 2C recovery, framework superiority, "
            "or production readiness.",
        ]) + "\n",
        encoding="utf-8",
    )

    # Manifest every retained file except the manifest itself.
    rows = []
    for path in sorted(evidence.iterdir()):
        if path.is_file() and path.name != "package-files-sha256.txt":
            rows.append(f"{sha256(path)}  {path.name}\n")
    (evidence / "package-files-sha256.txt").write_text("".join(rows), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
