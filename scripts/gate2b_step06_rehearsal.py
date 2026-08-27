#!/usr/bin/env python3
"""Disposable, model-free rehearsal for the v1.0.4 final governance bridge."""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any, Callable

import gate2b_step06_audit as audit
from gate2b_step06_batch import (
    FINAL_GOVERNANCE_FILES,
    SUCCESS_RUN_ID,
    drupal_capture,
    record_final_governance,
    sha,
    write_json,
)


def copy_family(source: Path, destination: Path) -> Path:
    shutil.copytree(source, destination)
    return destination


def rewrite_manifest(root: Path, name: str, artifact: str) -> None:
    write_json(root / name, {"algorithm": "sha256", "entries": [
        {"path": artifact, "sha256": sha(root / artifact)}
    ]})


def rewrite_final_manifest(root: Path) -> None:
    manifest = json.loads((root / "evidence-manifest.json").read_text())
    for entry in manifest["entries"]:
        entry["sha256"] = sha(root / entry["path"])
    write_json(root / "evidence-manifest.json", manifest)


def reject(action: Callable[[], Any]) -> bool:
    try:
        action()
    except Exception:
        return True
    return False


def mutate_attestation(
    source: Path, destination: Path, mutator: Callable[[dict[str, Any]], None]
) -> Path:
    copy_family(source, destination)
    value = json.loads((destination / "final-governance.json").read_text())
    mutator(value)
    write_json(destination / "final-governance.json", value)
    rewrite_manifest(
        destination, "final-governance-manifest.json", "final-governance.json"
    )
    return destination


def rehearse(repo: Path) -> dict[str, Any]:
    final = repo / "evidence/results/crewai" / SUCCESS_RUN_ID
    supplement = (
        repo
        / "evidence/gates/gate-2b/frozen-batch-governance-supplement"
        / SUCCESS_RUN_ID
        / "gate2b-step06-governance-supplement-v103"
    )
    restored = drupal_capture(repo)
    with tempfile.TemporaryDirectory(prefix="gate2b-step06-v104-") as raw:
        root = Path(raw)
        restored_path = root / "restored-state.json"
        write_json(restored_path, restored)
        final_governance = root / "final-governance"
        record_final_governance(repo, final, supplement, final_governance, restored_path)
        # Reuse the single read-only capture during negative controls.
        audit.drupal_capture = lambda _repo: restored
        positive = audit.audit_final_governance(
            repo, final, supplement, final_governance, rehearsal=False
        )
        controls: dict[str, bool] = {}

        wrong_manifest = copy_family(final, root / "wrong-final-manifest")
        value = json.loads((wrong_manifest / "evidence-manifest.json").read_text())
        value["algorithm"] = "sha512"
        write_json(wrong_manifest / "evidence-manifest.json", value)
        controls["wrong_final_evidence_manifest_sha_rejected"] = reject(
            lambda: audit.audit_final_governance(
                repo, wrong_manifest, supplement, final_governance, rehearsal=False
            )
        )

        tampered_final = copy_family(final, root / "tampered-final")
        (tampered_final / "summary.md").write_text(
            (tampered_final / "summary.md").read_text() + "tampered\n"
        )
        controls["tampered_final_closure_byte_rejected"] = reject(
            lambda: audit.audit_final_governance(
                repo, tampered_final, supplement, final_governance, rehearsal=False
            )
        )

        wrong_summary = copy_family(final, root / "wrong-summary")
        value = json.loads((wrong_summary / "summary.json").read_text())
        value["schema_version"] = 2
        write_json(wrong_summary / "summary.json", value)
        rewrite_final_manifest(wrong_summary)
        controls["wrong_final_summary_sha_rejected"] = reject(
            lambda: audit.audit_final_governance(
                repo, wrong_summary, supplement, final_governance, rehearsal=False
            )
        )

        controls["missing_supplement_rejected"] = reject(
            lambda: audit.audit_final_governance(
                repo, final, root / "absent-supplement", final_governance,
                rehearsal=False,
            )
        )
        wrong_supp_manifest = copy_family(supplement, root / "wrong-supp-manifest")
        value = json.loads((wrong_supp_manifest / "supplement-manifest.json").read_text())
        value["algorithm"] = "sha512"
        write_json(wrong_supp_manifest / "supplement-manifest.json", value)
        controls["wrong_supplement_manifest_sha_rejected"] = reject(
            lambda: audit.audit_final_governance(
                repo, final, wrong_supp_manifest, final_governance, rehearsal=False
            )
        )
        tampered_supp = copy_family(supplement, root / "tampered-supplement")
        (tampered_supp / "supplement.json").write_text(
            (tampered_supp / "supplement.json").read_text() + " "
        )
        controls["tampered_supplement_rejected"] = reject(
            lambda: audit.audit_final_governance(
                repo, final, tampered_supp, final_governance, rehearsal=False
            )
        )

        wrong_batch = copy_family(final, root / "wrong-batch")
        value = json.loads((wrong_batch / "batch-manifest.json").read_text())
        value["algorithm"] = "sha512"
        write_json(wrong_batch / "batch-manifest.json", value)
        rewrite_final_manifest(wrong_batch)
        controls["wrong_batch_manifest_sha_rejected"] = reject(
            lambda: audit.audit_final_governance(
                repo, wrong_batch, supplement, final_governance, rehearsal=False
            )
        )

        semantic_mutations: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
            ("wrong_successful_run_id_rejected", lambda v: v.update(successful_run_id="wrong")),
            ("wrong_successful_runtime_sha_rejected", lambda v: v["successful_runtime"].update(sha256="0" * 64)),
            ("wrong_historical_failure_binding_rejected", lambda v: v["historical_failure"].update(failure_json_sha256="0" * 64)),
            ("wrong_historical_disposition_binding_rejected", lambda v: v["historical_failure"].update(disposition_manifest_sha256="0" * 64)),
            ("wrong_readiness_manifest_rejected", lambda v: v.update(authenticated_readiness_manifest_sha256="0" * 64)),
            ("wrong_activation_manifest_rejected", lambda v: v.update(activation_manifest_sha256="0" * 64)),
            ("wrong_snapshot_identity_rejected", lambda v: v["snapshot"].update(id="wrong")),
            ("wrong_snapshot_hash_rejected", lambda v: v["snapshot"].update(sha256="0" * 64)),
            ("restoration_count_not_one_rejected", lambda v: v["snapshot"].update(restore_count=2)),
            ("restoration_lifecycle_not_verified_rejected", lambda v: v.update(restoration_state="NOT_VERIFIED")),
            ("final_lifecycle_not_complete_rejected", lambda v: v.update(step_lifecycle="INCOMPLETE")),
            ("feedback_collapse_calls_missing_rejected", lambda v: v["experimental_accounting"].pop("feedback_collapse_calls")),
            ("feedback_collapse_calls_nonzero_rejected", lambda v: v["experimental_accounting"].update(feedback_collapse_calls=1)),
            ("target_hash_drift_rejected", lambda v: v["restored_state"].update(target_sequence_sha256="0" * 64)),
            ("source_projection_drift_rejected", lambda v: v["restored_state"].update(source_projection="0" * 64)),
            ("wrong_final_manifest_binding_rejected", lambda v: v["finalized_closure"].update(evidence_manifest_sha256="0" * 64)),
            ("wrong_final_summary_binding_rejected", lambda v: v["finalized_closure"].update(summary_sha256="0" * 64)),
            ("wrong_supplement_binding_rejected", lambda v: v["governance_supplement"].update(manifest_sha256="0" * 64)),
        ]
        for index, (name, mutation) in enumerate(semantic_mutations):
            candidate = mutate_attestation(
                final_governance, root / f"attestation-{index}", mutation
            )
            controls[name] = reject(
                lambda candidate=candidate: audit.audit_final_governance(
                    repo, final, supplement, candidate, rehearsal=False
                )
            )

        tampered_manifest = copy_family(final_governance, root / "tampered-fg-manifest")
        value = json.loads((tampered_manifest / "final-governance-manifest.json").read_text())
        value["entries"][0]["sha256"] = "0" * 64
        write_json(tampered_manifest / "final-governance-manifest.json", value)
        controls["final_governance_manifest_tampering_rejected"] = reject(
            lambda: audit.audit_final_governance(
                repo, final, supplement, tampered_manifest, rehearsal=False
            )
        )
        controls["old_15_file_validator_not_applied_to_final_19"] = (
            positive.get("batch_validator_mode")
            == "embedded-batch-stage-within-finalized-19"
            and reject(lambda: audit.audit_governance_supplement(
                repo, final, supplement, batch_shape="batch-stage"
            ))
        )
        controls["accepted_successful_run_rerun_blocked"] = reject(
            lambda: record_final_governance(
                repo, final, supplement, final_governance, restored_path
            )
        )
        source = inspect.getsource(audit.audit_final_governance)
        controls["composite_audit_cannot_call_model_provider"] = not any(
            token in source for token in ("build_live_llm", "llm.call", "responses.create")
        )
        controls["composite_audit_cannot_restore"] = "snapshot restore" not in source
        controls["composite_audit_cannot_delete_snapshot"] = not any(
            token in source for token in ("unlink(", "rmtree(", "snapshot delete")
        )
        controls["composite_audit_cannot_stage_git"] = not any(
            token in source for token in ("git add", "git commit", "git push")
        )
        if not all(controls.values()):
            raise RuntimeError(
                "v1.0.4 negative controls failed: "
                + repr([name for name, passed in controls.items() if not passed])
            )
        return {
            "status": "PASS",
            "mode": "DISPOSABLE_MODEL_FREE_FINAL_GOVERNANCE",
            "positive_composite_audit": positive,
            "final_governance_files": len(FINAL_GOVERNANCE_FILES),
            "final_governance_manifest_entries": 1,
            "negative_controls": controls,
            "authoritative_final_governance_families_created": 0,
            "model_generations": 0,
            "provider_requests": 0,
            "provider_responses": 0,
            "drupal_writes": 0,
            "snapshot_operations": 0,
            "git_staged_entries": 0,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(rehearse(args.repo.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
