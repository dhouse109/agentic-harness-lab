#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def run(args: list[str], cwd: Path, ok: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for key in ("OPENAI_API_KEY", "OPENAI_CANDIDATE_MODEL", "CREWAI_CANDIDATE_MODEL"):
        env.pop(key, None)
    result = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    assert (result.returncode == 0) == ok, (args, result.stdout)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--payload", required=True)
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    payload = Path(args.payload).resolve()
    python = "python3"
    audit = payload / "scripts/gate2b_step08_audit.py"
    certify = payload / "scripts/gate2b_step08_certify.py"

    with tempfile.TemporaryDirectory(prefix="gate2b-step08-rehearsal-") as temp:
        parent = Path(temp)
        root = parent / "candidate"
        root.mkdir()
        run_id = "gate2b-step08-20990101T000000Z-rehearsal"
        runrel = f"evidence/gates/gate-2b/certification/{run_id}"
        run(
            [
                python,
                str(certify),
                "--repo",
                str(repo),
                "--run-id",
                run_id,
                "--output-root",
                str(root),
            ],
            repo,
        )
        run(
            [
                python,
                str(audit),
                "--repo",
                str(repo),
                "--mode",
                "candidate",
                "--root",
                str(root),
                "--run-rel",
                runrel,
                "--docs-root",
                str(payload),
            ],
            repo,
        )

        old_controls: list[str] = []
        lifecycle_controls: list[str] = []

        def audit_disposable(candidate: Path, docs: Path) -> None:
            run(
                [
                    python,
                    str(audit),
                    "--repo",
                    str(repo),
                    "--mode",
                    "rehearsal",
                    "--root",
                    str(candidate),
                    "--run-rel",
                    runrel,
                    "--docs-root",
                    str(docs),
                ],
                repo,
                False,
            )

        def reject_artifact(name: str, path: str, text: str) -> None:
            candidate = parent / ("artifact-" + name)
            shutil.copytree(root, candidate)
            (candidate / path).write_text(text)
            audit_disposable(candidate, payload)
            old_controls.append(name)

        def replace_artifact(name: str, path: str, old: str, new: str) -> None:
            source = (root / path).read_text()
            assert old in source, (name, old)
            reject_artifact(name, path, source.replace(old, new, 1))

        replace_artifact(
            "wrong-synthesis",
            f"{runrel}/certified-bindings.json",
            "gate2b-step07-20260828T135201Z-1ed07bea",
            "gate2b-step07-wrong",
        )
        replace_artifact(
            "wrong-batch-hash",
            f"{runrel}/certified-bindings.json",
            "e89069bec85a51655631fe1333f8af4a8f54968b06492619b50a36e8204368e1",
            "0" * 64,
        )
        replace_artifact(
            "unsupported-promoted",
            f"{runrel}/certified-bindings.json",
            '"unsupported": [',
            '"verified_extra": [',
        )
        replace_artifact(
            "architecture-promoted",
            f"{runrel}/certified-bindings.json",
            '"architecture_probe": [',
            '"observed_extra": [',
        )
        replace_artifact(
            "missing-claim-proof",
            f"{runrel}/certified-bindings.json",
            '"hashes": {',
            '"hashes_missing": {',
        )
        replace_artifact(
            "six-organ-drift",
            f"{runrel}/certified-bindings.json",
            '"lifecycle"',
            '"recovery-ranking"',
        )
        replace_artifact(
            "gate2c-complete",
            f"{runrel}/handoff-state.json",
            "DEFERRED_UNCLAIMED",
            "COMPLETE",
        )
        replace_artifact(
            "wrong-version",
            f"{runrel}/freeze-projection.json",
            '"crewai": "1.15.10"',
            '"crewai": "latest"',
        )
        replace_artifact(
            "source-projection-drift",
            "shared/contracts/GATE2B-CREWAI-FREEZE.json",
            "f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17",
            "0" * 64,
        )
        replace_artifact(
            "privacy-leak",
            f"{runrel}/certification.json",
            '"privacy": "pass"',
            '"privacy": "pass", "Authorization": "Bearer protected-value"',
        )
        reject_artifact("manifest-tamper", f"{runrel}/privacy-scan.json", "{}\n")
        reject_artifact("freeze-tamper", "shared/contracts/GATE2B-CREWAI-FREEZE.json", "{}\n")
        reject_artifact("handoff-unbound", "docs/handoffs/GATE-2B-CREWAI-HANDOFF.md", "unbound\n")
        run(
            [
                python,
                str(certify),
                "--repo",
                str(repo),
                "--run-id",
                run_id,
                "--output-root",
                str(root),
            ],
            repo,
            False,
        )
        old_controls.append("second-certification-attempt")

        def reject_doc(name: str, relative: str, old: str, new: str) -> None:
            docs = parent / ("docs-" + name)
            shutil.copytree(payload, docs)
            path = docs / relative
            source = path.read_text()
            assert old in source, (name, old)
            path.write_text(source.replace(old, new, 1))
            audit_disposable(root, docs)
            lifecycle_controls.append(name)

        reject_doc(
            "stale-step2b06-awaiting-restore",
            "PLAN.md",
            "Step 2B.06 — complete, normally merged",
            "Step 2B.06 — BATCH_COMPLETE_AWAITING_RESTORE; normally merged",
        )
        reject_doc(
            "stale-restore-not-executed",
            "PLAN.md",
            "restored exactly once",
            "restore not executed",
        )
        reject_doc(
            "stale-step2b07-current",
            "docs/CURRENT-STATUS.md",
            "**Step 2B.07:** complete",
            "**Step 2B.07:** current feature work",
        )
        reject_doc(
            "rerun-step2b07-synthesis",
            "docs/CODEX-GATE-2B-RUNBOOK.md",
            "Never invoke its disabled synthesis mode or allocate another synthesis identity.",
            "Run `scripts/run-gate2b-step07-crewai-evidence-synthesis-and-comparison.sh` run again.",
        )
        reject_doc(
            "step2b08-not-started",
            "PLAN.md",
            "Step 2B.08 — certification, freeze, and Gate 2C handoff complete",
            "Step 2B.08 — not started",
        )
        unbound = parent / "artifact-gate2b-certification-unbound"
        shutil.copytree(root, unbound)
        (unbound / "shared/contracts/GATE2B-CREWAI-FREEZE.json").unlink()
        audit_disposable(unbound, payload)
        lifecycle_controls.append("gate2b-certification-without-freeze-evidence-binding")
        reject_doc(
            "docs-gate2c-complete",
            "docs/CURRENT-STATUS.md",
            "Gate 2C remains `DEFERRED_UNCLAIMED`",
            "Gate 2C is `COMPLETE`",
        )
        reject_doc(
            "gate2-overall-complete-before-gate2c",
            "docs/CURRENT-STATUS.md",
            "Gate 2 overall is `NOT_COMPLETE`",
            "Gate 2 overall is complete",
        )
        reject_doc(
            "wrong-current-predecessor-main",
            "docs/CURRENT-STATUS.md",
            "`main` at normal Step 2B.07 merge `50e7296406a39de23b20bdfb1b45960dca13d3a1`",
            "`gate-2b-step07-crewai-evidence-synthesis-and-comparison`; predecessor `main` at `78ba79165378ac2905801d994682aa385cdfb607`",
        )

        print(
            "[PASS] real Step 2B.01-Step 2B.07/Gate 2A predecessor composition "
            "and positive certification rehearsal"
        )
        print("[PASS] v1.0.0 negative controls:", ", ".join(old_controls))
        print("[PASS] v1.0.1 lifecycle negative controls:", ", ".join(lifecycle_controls))
        print(
            "[PASS] static guards: identity/hash/claim-strength/six-organ/Gate2C/version/"
            "source/snapshot/privacy/lifecycle-documents/operational reachability"
        )


if __name__ == "__main__":
    main()
