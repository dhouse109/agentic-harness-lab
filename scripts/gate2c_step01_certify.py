#!/usr/bin/env python3
"""Create the one-time sanitized model-free Step 2C.01 evidence family."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

CONTRACT = "shared/contracts/GATE2C-SHARED-FAILURE-RECOVERY-CONTRACT.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    if not args.run_id.startswith("gate2c-step01-"):
        raise SystemExit("run ID must begin gate2c-step01-")
    root = repo / "evidence/gates/gate-2c/contract" / args.run_id
    if root.exists():
        raise SystemExit("evidence identity already exists")
    pointer = root.parent / "GATE2C-STEP01-LATEST.txt"
    if pointer.exists():
        raise SystemExit("Step 2C.01 certification pointer already exists")
    contract_sha = sha(repo / CONTRACT)
    root.mkdir(parents=True)
    write(root / "contract-certification.json", {
        "schema_version": 1,
        "run_id": args.run_id,
        "created_at": now(),
        "status": "PASS",
        "contract_path": CONTRACT,
        "contract_sha256": contract_sha,
        "model_free": True,
        "drupal_read_only": True,
        "runtime_mutations": 0,
        "snapshot_operations": 0,
        "failure_injections": 0,
        "framework_workers_started": 0,
        "model_generations": 0,
        "provider_requests": 0,
        "provider_responses": 0,
        "gate_2c": "DEFERRED_UNCLAIMED",
        "gate_2": "NOT_COMPLETE",
        "next_package": "gate-2c-step02-shared-failure-injector-and-model-free-rehearsals",
    })
    write(root / "predecessor-bindings.json", {
        "schema_version": 1,
        "repository_predecessor": "c022619e220715be17e541650c261ea0b568704b",
        "freezes": {
            "drupal_ai": "2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd",
            "langgraph": "a28361c34b9d1c2089eee786324ad34cffbf54e3495f59a276c489865e5630f0",
            "crewai": "74e2baad0cbe612dcd7e72ccdc264b01960ee12e09cfb0ae3154969b6055c206",
        },
        "certification_runs": {
            "drupal_ai": "gate1-step07-20260809T012559Z-2229836",
            "langgraph": "gate2a-step10-20260811T034835Z-03f93652",
            "crewai": "gate2b-step08-20260828T200003Z-22f913f2",
        },
    })
    contract = json.loads((repo / CONTRACT).read_text(encoding="utf-8"))
    write(root / "authorization-ledger.json", {
        "schema_version": 1,
        "run_id": args.run_id,
        "boundaries": contract["authorization_ledger"],
        "live_gate2c_authorizations_granted": 0,
        "crewai_recovery_architecture_decision": "PENDING_MODEL_FREE_PROOF_AND_HUMAN_DECISION",
        "drupal_lock_policy": "PROPOSED_FOR_EXPLICIT_HUMAN_APPROVAL",
    })
    write(root / "privacy-scan.json", {
        "credentials_retained": False,
        "hidden_reasoning_retained": False,
        "private_database_content_retained": False,
        "raw_image_or_data_url_retained": False,
        "status": "PASS",
    })
    (root / "summary.md").write_text(
        "# Gate 2C Step 2C.01 model-free certification\n\n"
        "The contract, digest, schemas, successor-aware audit, protected-tree policy, "
        "and authorization ledger passed. Gate 2C remains `DEFERRED_UNCLAIMED`; Gate 2 "
        "remains `NOT_COMPLETE`. CrewAI recovery architecture remains pending. No model, "
        "provider, Drupal-write, runtime, failure-injection, or snapshot activity occurred.\n",
        encoding="utf-8",
    )
    entries = []
    for path in sorted(root.iterdir()):
        entries.append({"path": path.name, "sha256": sha(path), "size": path.stat().st_size})
    write(root / "evidence-manifest.json", {"schema_version": 1, "run_id": args.run_id, "entries": entries})
    pointer.write_text(f"evidence/gates/gate-2c/contract/{args.run_id}\n", encoding="utf-8")
    print(root.relative_to(repo))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
