#!/usr/bin/env python3
"""Advance status documents only after a passing Step 1.02 evidence audit."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def transition_once(path: Path, before: str, after: str) -> None:
    text = path.read_text(encoding="utf-8")
    if after in text:
        return
    if before not in text:
        raise RuntimeError(f"Status transition anchor missing: {path}")
    path.write_text(text.replace(before, after, 1), encoding="utf-8")


def replace_if_present(path: Path, before: str, after: str) -> None:
    text = path.read_text(encoding="utf-8")
    if before in text:
        path.write_text(text.replace(before, after), encoding="utf-8")


def set_step02_evidence(path: Path, marker: str, run_id: str, digest: str) -> None:
    text = path.read_text(encoding="utf-8")
    pattern = re.escape(marker) + r"(?:\nAccepted Step 1\.02 evidence run: `[^`]+`\nAccepted ADR-0006 SHA-256: `[0-9a-f]{64}`)?"
    replacement = marker + f"\nAccepted Step 1.02 evidence run: `{run_id}`\nAccepted ADR-0006 SHA-256: `{digest}`"
    updated, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise RuntimeError(f"Step 1.02 evidence anchor missing: {path}")
    path.write_text(updated, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--decision-sha256", required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    run_id = args.run_id
    digest = args.decision_sha256

    plan = repo / "PLAN.md"
    replace_if_present(plan, "gate-1-step03-drupal-ai-tool-adapters\n```", "gate-1-step03-drupal-ai-tool-adapters-v1.0.0\n```")
    transition_once(plan, "Gate 1 Step 1.01 is complete; Step 1.02 is next.", "Gate 1 Steps 1.01 and 1.02 are complete; Step 1.03 is next.")
    transition_once(plan, "**Next package:**\n\n```text\ngate-1-step02-drupal-ai-runtime-probe-v1.0.0\n```", "**Completed package:**\n\n```text\ngate-1-step02-drupal-ai-runtime-probe-v1.0.0\n```\n\n**Next package:**\n\n```text\ngate-1-step03-drupal-ai-tool-adapters-v1.0.0\n```")
    transition_once(plan, "- [ ] Step 1.02 — pinned Drupal AI runtime probe", "- [x] Step 1.02 — pinned Drupal AI runtime probe")
    replace_if_present(
        plan,
        "The Step 1.02 runtime-path decision must use the next available ADR number, currently\nexpected to be `ADR-0006`; it must not overwrite ADR-0004 or ADR-0005.",
        "The Step 1.02 runtime-path decision is recorded in `ADR-0006`; ADR-0004 and ADR-0005 remain\nunchanged.",
    )
    marker = "Accepted Step 1.01 evidence run: `gate1-step01-20260805T205448Z-103220`\nAccepted Gate 1 contract digest: `360aa46f5b0f0e1df9f09a70ff790add36c6acedccccbe6880b8021ae44e07e6`"
    set_step02_evidence(plan, marker, run_id, digest)

    readme = repo / "README.md"
    replace_if_present(readme, "- **Next package:** Step 1.03 thin Drupal AI tool adapters.", "- **Next package:** `gate-1-step03-drupal-ai-tool-adapters-v1.0.0`.")
    transition_once(readme, "- **Step 1.01:** complete.\n- **Next package:** `gate-1-step02-drupal-ai-runtime-probe-v1.0.0`.", "- **Step 1.01:** complete.\n- **Step 1.02:** complete.\n- **Next package:** `gate-1-step03-drupal-ai-tool-adapters-v1.0.0`.")
    replace_if_present(
        readme,
        "The Step\n1.02 runtime-path decision is expected to use `ADR-0006`, subject to confirming it remains the next\navailable number.",
        "The Step 1.02 runtime-path decision is recorded in `ADR-0006`.",
    )
    set_step02_evidence(readme, marker, run_id, digest)

    status = repo / "docs/CURRENT-STATUS.md"
    replace_if_present(status, "- **Next package:** Step 1.03 thin Drupal AI tool adapters.", "- **Next package:** `gate-1-step03-drupal-ai-tool-adapters-v1.0.0`.")
    replace_if_present(status, "Packages 1.01 and 1.02 are complete. The next package is Step 1.03 thin Drupal AI tool adapters.", "Packages 1.01 and 1.02 are complete. The next package is\n`gate-1-step03-drupal-ai-tool-adapters-v1.0.0`.")
    transition_once(status, "- **Completed package:** `gate-1-step01-drupal-ai-batch-contract-v1.0.1`.\n- **Step 1.01 execution:** complete.\n- **Next package:** `gate-1-step02-drupal-ai-runtime-probe-v1.0.0`.", "- **Completed packages:** Step 1.01 batch contract and Step 1.02 Drupal AI runtime probe.\n- **Step 1.02 execution:** complete.\n- **Next package:** `gate-1-step03-drupal-ai-tool-adapters-v1.0.0`.")
    set_step02_evidence(status, marker, run_id, digest)
    transition_once(status, "Package 1.01 is complete. The next package is\n`gate-1-step02-drupal-ai-runtime-probe-v1.0.0`.", "Packages 1.01 and 1.02 are complete. The next package is\n`gate-1-step03-drupal-ai-tool-adapters-v1.0.0`.")
    replace_if_present(
        status,
        "Because ADR-0004 and ADR-0005 exist, the Step 1.02 runtime-path decision is currently\nexpected to use `ADR-0006`; no existing ADR may be recreated or overwritten.",
        "The Step 1.02 runtime-path decision is recorded in `ADR-0006`; ADR-0004 and ADR-0005 remain\nunchanged.",
    )
    replace_if_present(
        status,
        "Do not generate Step 1.02 until Step 1.01 is committed.",
        "Do not generate Step 1.03 until Step 1.02 is committed.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
