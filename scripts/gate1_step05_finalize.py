#!/usr/bin/env python3
"""Advance repository status documents after accepted Step 1.05 batch evidence."""
from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"[ERROR] Expected exactly one {label} marker; found {count}")
    return text.replace(old, new, 1)


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--gate-run-id", required=True)
    parser.add_argument("--batch-run-id", required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    gate_run_id = args.gate_run_id
    batch_run_id = args.batch_run_id
    if not gate_run_id.startswith("gate1-step05-"):
        raise SystemExit("[ERROR] Unexpected Step 1.05 gate run ID")
    if not batch_run_id.startswith("drupal_ai-"):
        raise SystemExit("[ERROR] Unexpected Drupal AI batch run ID")

    plan_path = repo / "PLAN.md"
    readme_path = repo / "README.md"
    status_path = repo / "docs/CURRENT-STATUS.md"

    plan = plan_path.read_text(encoding="utf-8")
    plan = replace_once(
        plan,
        "> Phase 0 and Gate 0.5 are complete. Gate 1 Steps 1.01 through 1.04 are complete; Step 1.05 is next.",
        "> Phase 0 and Gate 0.5 are complete. Gate 1 Steps 1.01 through 1.05 are complete; Step 1.06 is next.",
        "PLAN current-status",
    )
    plan = replace_once(
        plan,
        "**Next package:**\n\n```text\ngate-1-step05-drupal-ai-batch-runner-v1.0.0\n```",
        "**Completed package:**\n\n```text\ngate-1-step05-drupal-ai-batch-runner-v1.0.0\n```\n\n**Next package:**\n\n```text\ngate-1-step06-drupal-ai-batch-evidence-and-human-review-v1.0.0\n```",
        "PLAN Step 1.05 package transition",
    )
    plan = replace_once(
        plan,
        "Accepted Step 1.04 evidence run: `gate1-step04-20260806T213954Z-156475`",
        "Accepted Step 1.04 evidence run: `gate1-step04-20260806T213954Z-156475`\n"
        f"Accepted Step 1.05 evidence run: `{gate_run_id}`\n"
        f"Accepted Drupal AI batch run: `{batch_run_id}`",
        "PLAN accepted Step 1.05 evidence",
    )
    plan = replace_once(
        plan,
        "- [ ] Step 1.05 — 12-target batch runner",
        "- [x] Step 1.05 — 12-target batch runner",
        "PLAN Step 1.05 checklist",
    )

    readme = readme_path.read_text(encoding="utf-8")
    readme = replace_once(
        readme,
        "- **Step 1.04:** complete.\n- **Next package:** `gate-1-step05-drupal-ai-batch-runner-v1.0.0`.",
        "- **Step 1.04:** complete.\n- **Step 1.05:** complete.\n- **Next package:** `gate-1-step06-drupal-ai-batch-evidence-and-human-review-v1.0.0`.",
        "README Step 1.05 status",
    )
    readme = replace_once(
        readme,
        "Accepted Step 1.04 evidence run: `gate1-step04-20260806T213954Z-156475`",
        "Accepted Step 1.04 evidence run: `gate1-step04-20260806T213954Z-156475`\n"
        f"Accepted Step 1.05 evidence run: `{gate_run_id}`\n"
        f"Accepted Drupal AI batch run: `{batch_run_id}`",
        "README accepted Step 1.05 evidence",
    )

    status = status_path.read_text(encoding="utf-8")
    status = replace_once(
        status,
        "- **Completed packages:** Step 1.01 batch contract, Step 1.02 Drupal AI runtime probe, Step 1.03 Drupal AI tool adapters, and Step 1.04 canonical vertical slice.\n"
        "- **Step 1.04 execution:** complete.\n"
        "- **Next package:** `gate-1-step05-drupal-ai-batch-runner-v1.0.0`.",
        "- **Completed packages:** Step 1.01 batch contract, Step 1.02 Drupal AI runtime probe, Step 1.03 Drupal AI tool adapters, Step 1.04 canonical vertical slice, and Step 1.05 12-target batch runner.\n"
        "- **Step 1.05 execution:** complete; 12 recommendations are pending Step 1.06 human review.\n"
        "- **Next package:** `gate-1-step06-drupal-ai-batch-evidence-and-human-review-v1.0.0`.",
        "CURRENT-STATUS Step 1.05 status",
    )
    status = replace_once(
        status,
        "Accepted Step 1.04 evidence run: `gate1-step04-20260806T213954Z-156475`",
        "Accepted Step 1.04 evidence run: `gate1-step04-20260806T213954Z-156475`\n"
        f"Accepted Step 1.05 evidence run: `{gate_run_id}`\n"
        f"Accepted Drupal AI batch run: `{batch_run_id}`",
        "CURRENT-STATUS accepted Step 1.05 evidence",
    )
    status = replace_once(
        status,
        "Packages 1.01 through 1.04 are complete. The next package is\n"
        "`gate-1-step05-drupal-ai-batch-runner-v1.0.0`. Do not commit extracted packages or reuse a package",
        "Packages 1.01 through 1.05 are complete. The next package is\n"
        "`gate-1-step06-drupal-ai-batch-evidence-and-human-review-v1.0.0`. Do not commit extracted packages or reuse a package",
        "CURRENT-STATUS local handoff",
    )

    write(plan_path, plan)
    write(readme_path, readme)
    write(status_path, status)
    print(
        f"[PASS] Status documents advanced to Step 1.06 after {gate_run_id} / {batch_run_id}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
