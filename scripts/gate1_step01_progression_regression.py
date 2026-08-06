#!/usr/bin/env python3
"""Regression-test Step 1.01 audit progression with temporary document overlays."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable


PREDECESSOR_COMMIT = "9b303ec3aefd8d92526905ca929a647948030b5a"
POST_STEP01_COMMIT = "0b52011c8baa5c8a61035c36f0f189bee255f72f"
EXPECTED_FAILURE = "CURRENT-STATUS.md was not advanced by the passing runner"
EXPECTED_STEP01_RUN = "gate1-step01-20260805T205448Z-103220"
EXPECTED_STEP01_SHA = "360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6"
CURRENT_NEXT_PACKAGE = "gate-1-step03-drupal-ai-tool-adapters-v1.0.0"
POST_STEP01_NEXT_PACKAGE = "gate-1-step02-drupal-ai-runtime-probe-v1.0.0"
DOCUMENTS = ("PLAN.md", "README.md", "docs/CURRENT-STATUS.md")


class RegressionError(RuntimeError):
    pass


def git_file(repo: Path, commit: str, relative: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{relative}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RegressionError(f"Unable to read {relative} from {commit}")
    return result.stdout


def write_overlay(root: Path, documents: dict[str, str]) -> None:
    for relative, text in documents.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def invoke(
    auditor: Path,
    repo: Path,
    document_state: str,
    documents: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="gate1-step01-progression-") as temporary:
        command = [sys.executable, str(auditor), "--repo", str(repo), "--document-state", document_state]
        if documents is not None:
            overlay = Path(temporary)
            write_overlay(overlay, documents)
            command.extend(("--overlay", str(overlay)))
        return subprocess.run(command, check=False, capture_output=True, text=True)


def require_pass(name: str, result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    if result.returncode != 0:
        raise RegressionError(f"Positive fixture {name} failed: {result.stdout.strip()} {result.stderr.strip()}")
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RegressionError(f"Positive fixture {name} emitted invalid JSON") from exc
    if value.get("status") != "pass":
        raise RegressionError(f"Positive fixture {name} did not report pass")
    return value


def require_reject(name: str, result: subprocess.CompletedProcess[str]) -> None:
    if result.returncode == 0 or "[ERROR]" not in result.stdout:
        raise RegressionError(f"Negative fixture {name} was not rejected")


def current_documents(repo: Path) -> dict[str, str]:
    return {relative: (repo / relative).read_text(encoding="utf-8") for relative in DOCUMENTS}


def historical_documents(repo: Path) -> dict[str, str]:
    return {relative: git_file(repo, POST_STEP01_COMMIT, relative) for relative in DOCUMENTS}


def active_documents(repo: Path) -> dict[str, str]:
    documents = historical_documents(repo)
    documents["PLAN.md"] = documents["PLAN.md"].replace(
        "- [x] Step 1.01 — batch contract",
        "- [ ] Step 1.01 — batch contract",
        1,
    ) + "\nAccepted Step 1.01 publication baseline: pending successful v1.0.1 runner.\n"
    documents["README.md"] += "\nStep 1.01 is not yet run.\n"
    documents["docs/CURRENT-STATUS.md"] += (
        "\n- **Active package:** `gate-1-step01-drupal-ai-batch-contract-v1.0.1`.\n"
        "- **Step 1.01 execution:** not yet run.\n"
    )
    return documents


def progression_documents(repo: Path, completed_through: int, next_step: int, next_package: str) -> dict[str, str]:
    documents = historical_documents(repo)
    for relative in DOCUMENTS:
        documents[relative] = documents[relative].replace(POST_STEP01_NEXT_PACKAGE, next_package)
        documents[relative] = documents[relative].replace("Step 1.02 is next", f"Step 1.{next_step:02d} is next")
        documents[relative] = documents[relative].replace("Step 1.02 is the next", f"Step 1.{next_step:02d} is the next")
    for number in range(2, completed_through + 1):
        step = f"1.{number:02d}"
        marker = f"- [ ] Step {step} —"
        replacement = f"- [x] Step {step} —"
        if marker not in documents["PLAN.md"]:
            raise RegressionError(f"Missing PLAN.md checklist marker for {step}")
        documents["PLAN.md"] = documents["PLAN.md"].replace(marker, replacement, 1)
        documents["README.md"] += f"\n- **Step {step}:** complete.\n"
        documents["docs/CURRENT-STATUS.md"] += f"\n- **Step {step}:** complete.\n"
    return documents


def changed(base: dict[str, str], relative: str, transform: Callable[[str], str]) -> dict[str, str]:
    documents = dict(base)
    documents[relative] = transform(documents[relative])
    return documents


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--auditor", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    auditor = (args.auditor or repo / "scripts/gate1_step01_audit.py").resolve()

    if subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", PREDECESSOR_COMMIT, "HEAD"],
        check=False,
    ).returncode != 0:
        raise RegressionError("Required repair predecessor is not in HEAD ancestry")

    with tempfile.TemporaryDirectory(prefix="gate1-step01-predecessor-") as temporary:
        predecessor_auditor = Path(temporary) / "gate1_step01_audit.py"
        predecessor_auditor.write_text(git_file(repo, PREDECESSOR_COMMIT, "scripts/gate1_step01_audit.py"), encoding="utf-8")
        predecessor_result = invoke(predecessor_auditor, repo, "complete")
    if predecessor_result.returncode == 0 or EXPECTED_FAILURE not in predecessor_result.stdout:
        raise RegressionError("Known predecessor progression defect was not reproduced")

    positive_results: dict[str, dict[str, object]] = {}
    positive_results["strict_active_pre_run"] = require_pass(
        "strict_active_pre_run", invoke(auditor, repo, "active", active_documents(repo))
    )
    positive_results["step_1_02_next"] = require_pass(
        "step_1_02_next", invoke(auditor, repo, "complete", historical_documents(repo))
    )
    positive_results["current_repository_state"] = require_pass(
        "current_repository_state", invoke(auditor, repo, "complete")
    )
    positive_results["step_1_03_next_current"] = require_pass(
        "step_1_03_next_current",
        invoke(auditor, repo, "complete", progression_documents(repo, 2, 3, CURRENT_NEXT_PACKAGE)),
    )
    positive_results["step_1_04_next"] = require_pass(
        "step_1_04_next",
        invoke(
            auditor,
            repo,
            "complete",
            progression_documents(repo, 3, 4, "gate-1-step04-drupal-ai-canonical-vertical-slice-v1.0.0"),
        ),
    )
    positive_results["step_1_07_next"] = require_pass(
        "step_1_07_next",
        invoke(
            auditor,
            repo,
            "complete",
            progression_documents(repo, 6, 7, "gate-1-step07-drupal-ai-certification-freeze-handoff-v1.0.0"),
        ),
    )

    current = progression_documents(repo, 2, 3, CURRENT_NEXT_PACKAGE)
    negatives: dict[str, dict[str, str]] = {
        "step_1_01_incomplete": changed(
            current,
            "PLAN.md",
            lambda text: text.replace("- [x] Step 1.01 — batch contract", "- [ ] Step 1.01 — batch contract", 1),
        ),
        "accepted_run_missing": changed(
            current,
            "README.md",
            lambda text: text.replace(EXPECTED_STEP01_RUN, "missing-step01-run"),
        ),
        "accepted_digest_missing": changed(
            current,
            "docs/CURRENT-STATUS.md",
            lambda text: text.replace(EXPECTED_STEP01_SHA, "0" * 64),
        ),
        "stale_not_yet_run": changed(
            current,
            "README.md",
            lambda text: text + "\nStep 1.01 is not yet run.\n",
        ),
        "status_regressed_to_step_1_01": changed(
            current,
            "docs/CURRENT-STATUS.md",
            lambda text: text.replace(CURRENT_NEXT_PACKAGE, "gate-1-step01-drupal-ai-batch-contract-v1.0.1")
            + "\n- **Active package:** `gate-1-step01-drupal-ai-batch-contract-v1.0.1`.\n",
        ),
        "unknown_next_package": {
            relative: text.replace(CURRENT_NEXT_PACKAGE, "gate-1-step99-unknown-v1.0.0")
            for relative, text in current.items()
        },
        "impossible_completed_sequence": changed(
            current,
            "PLAN.md",
            lambda text: text.replace(
                "- [ ] Step 1.04 — canonical vertical slice",
                "- [x] Step 1.04 — canonical vertical slice",
                1,
            ),
        ),
        "status_documents_disagree": changed(
            current,
            "README.md",
            lambda text: text.replace("- **Step 1.01:** complete.", "- **Step 1.01:** recorded.", 1),
        ),
    }
    for name, documents in negatives.items():
        require_reject(name, invoke(auditor, repo, "complete", documents))

    active_missing_control = active_documents(repo)
    active_missing_control["docs/CURRENT-STATUS.md"] = active_missing_control["docs/CURRENT-STATUS.md"].replace(
        "- **Step 1.01 execution:** not yet run.\n", "", 1
    )
    require_reject("strict_active_missing_control", invoke(auditor, repo, "active", active_missing_control))

    current_output = positive_results["current_repository_state"]
    if "step02_started" in current_output:
        raise RegressionError("Auditor retained the ambiguous step02_started field")
    if current_output.get("step02_started_by_step01_package") is not False or not current_output.get("step02_started_scope"):
        raise RegressionError("Auditor did not scope the historical Step 1.02 field")

    print(json.dumps({
        "status": "pass",
        "predecessor_defect": {
            "commit": PREDECESSOR_COMMIT,
            "exit_code": predecessor_result.returncode,
            "message": EXPECTED_FAILURE,
        },
        "positive_progression_fixtures": list(positive_results),
        "negative_regression_fixtures": list(negatives) + ["strict_active_missing_control"],
        "positive_count": len(positive_results),
        "negative_count": len(negatives) + 1,
        "sequence_source": "shared/contracts/GATE1-DRUPAL-AI-BATCH-CONTRACT.json",
        "accepted_step01_run": EXPECTED_STEP01_RUN,
        "accepted_step01_digest": EXPECTED_STEP01_SHA,
        "ambiguous_step02_started_field_removed": True,
        "scoped_historical_step02_field_present": True,
        "temporary_overlays_only": True,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RegressionError as exc:
        print(f"[ERROR] {exc}")
        raise SystemExit(1) from exc
