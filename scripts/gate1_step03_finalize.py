#!/usr/bin/env python3
"""Advance status documents only after a passing Step 1.03 run."""

from __future__ import annotations

import argparse
from pathlib import Path


NEXT_PACKAGE = "gate-1-step04-drupal-ai-canonical-vertical-slice-v1.0.0"
OLD_STEP03_DETAIL = (
    "Step 1.03 directly exercises exactly four model-free Drupal AI FunctionCall adapters: "
    "`discover_targets`, `get_image_context`, `submit_recommendation`, and "
    "`get_recommendation_status`. It does not execute an AI Agent and makes no model or "
    "provider call."
)
STEP03_RECONCILIATION = (
    " Its predecessor-compatible Article-source SHA-256 is "
    "`f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17`; the original "
    "Step 1.03 hash discrepancy was definition drift only, with no Drupal source drift."
)
STEP03_DETAIL = OLD_STEP03_DETAIL + STEP03_RECONCILIATION


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"[ERROR] Expected one status marker for {label}; found {text.count(old)}")
    return text.replace(old, new, 1)


def transition_once(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        return replace_once(text, old, new, label)
    if text.count(new) != 1:
        raise SystemExit(f"[ERROR] Missing completed status marker for {label}")
    return text


def set_step03_evidence(text: str, run_id: str, label: str) -> str:
    prefix = "Accepted Step 1.03 evidence run: `"
    matches = [line for line in text.splitlines() if line.startswith(prefix)]
    desired = f"{prefix}{run_id}`"
    if len(matches) > 1:
        raise SystemExit(f"[ERROR] Multiple Step 1.03 evidence markers in {label}")
    if matches:
        text = replace_once(text, matches[0], desired, f"{label} accepted evidence")
    else:
        adr = "Accepted ADR-0006 SHA-256: `223f6d6f4276d3861cf5668f08e0446479d815a07fed18402b1e6a7722d18c4b`"
        text = replace_once(text, adr, adr + "\n" + desired, f"{label} accepted evidence")
    duplicated = STEP03_DETAIL + STEP03_RECONCILIATION
    if duplicated in text:
        text = replace_once(text, duplicated, STEP03_DETAIL, f"{label} duplicate reconciliation detail")
    elif STEP03_DETAIL in text:
        pass
    elif OLD_STEP03_DETAIL in text:
        text = replace_once(text, OLD_STEP03_DETAIL, STEP03_DETAIL, f"{label} Step 1.03 reconciliation detail")
    else:
        text = replace_once(text, desired, desired + "\n\n" + STEP03_DETAIL, f"{label} Step 1.03 detail")
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    run_id = args.run_id

    plan_path = repo / "PLAN.md"
    plan = plan_path.read_text(encoding="utf-8")
    plan = transition_once(
        plan,
        "> Phase 0 and Gate 0.5 are complete. Gate 1 Steps 1.01 and 1.02 are complete; Step 1.03 is next.",
        "> Phase 0 and Gate 0.5 are complete. Gate 1 Steps 1.01 through 1.03 are complete; Step 1.04 is next.",
        "PLAN current status",
    )
    plan = transition_once(
        plan,
        "**Next package:**\n\n```text\ngate-1-step03-drupal-ai-tool-adapters-v1.0.0\n```",
        "**Completed package:**\n\n```text\ngate-1-step03-drupal-ai-tool-adapters-v1.0.0\n```\n\n**Next package:**\n\n```text\n" + NEXT_PACKAGE + "\n```",
        "PLAN package boundary",
    )
    plan = set_step03_evidence(plan, run_id, "PLAN")
    plan = transition_once(plan, "- [ ] Step 1.03 — thin Drupal AI tool adapters", "- [x] Step 1.03 — thin Drupal AI tool adapters", "PLAN checklist")

    readme_path = repo / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    readme = transition_once(readme, "- **Step 1.02:** complete.\n- **Next package:** `gate-1-step03-drupal-ai-tool-adapters-v1.0.0`.", "- **Step 1.02:** complete.\n- **Step 1.03:** complete.\n- **Next package:** `" + NEXT_PACKAGE + "`.", "README status")
    readme = set_step03_evidence(readme, run_id, "README")

    current_path = repo / "docs/CURRENT-STATUS.md"
    current = current_path.read_text(encoding="utf-8")
    current = transition_once(current, "- **Completed packages:** Step 1.01 batch contract and Step 1.02 Drupal AI runtime probe.\n- **Step 1.02 execution:** complete.\n- **Next package:** `gate-1-step03-drupal-ai-tool-adapters-v1.0.0`.", "- **Completed packages:** Step 1.01 batch contract, Step 1.02 Drupal AI runtime probe, and Step 1.03 Drupal AI tool adapters.\n- **Step 1.03 execution:** complete.\n- **Next package:** `" + NEXT_PACKAGE + "`.", "CURRENT-STATUS position")
    current = set_step03_evidence(current, run_id, "CURRENT-STATUS")
    current = transition_once(current, "Packages 1.01 and 1.02 are complete. The next package is\n`gate-1-step03-drupal-ai-tool-adapters-v1.0.0`.", "Packages 1.01 through 1.03 are complete. The next package is\n`" + NEXT_PACKAGE + "`.", "CURRENT-STATUS handoff")

    plan_path.write_text(plan, encoding="utf-8")
    readme_path.write_text(readme, encoding="utf-8")
    current_path.write_text(current, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
