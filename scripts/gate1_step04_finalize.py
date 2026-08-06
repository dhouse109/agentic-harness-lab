#!/usr/bin/env python3
"""Advance repository status only after accepted Step 1.04 evidence passes."""
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
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    run_id = args.run_id
    if not run_id.startswith("gate1-step04-"):
        raise SystemExit("[ERROR] Unexpected Step 1.04 gate run ID")

    plan_path = repo / "PLAN.md"
    readme_path = repo / "README.md"
    status_path = repo / "docs/CURRENT-STATUS.md"

    plan = plan_path.read_text(encoding="utf-8")
    plan = replace_once(
        plan,
        "> Phase 0 and Gate 0.5 are complete. Gate 1 Steps 1.01 through 1.03 are complete; Step 1.04 is next.",
        "> Phase 0 and Gate 0.5 are complete. Gate 1 Steps 1.01 through 1.04 are complete; Step 1.05 is next.",
        "PLAN current-status",
    )
    plan = replace_once(
        plan,
        "**Next package:**\n\n```text\ngate-1-step04-drupal-ai-canonical-vertical-slice-v1.0.0\n```",
        "**Completed package:**\n\n```text\ngate-1-step04-drupal-ai-canonical-vertical-slice-v1.0.0\n```\n\n**Next package:**\n\n```text\ngate-1-step05-drupal-ai-batch-runner-v1.0.0\n```",
        "PLAN package transition",
    )
    plan = replace_once(
        plan,
        "Accepted Step 1.03 evidence run: `gate1-step03-20260806T050827Z-494925`",
        "Accepted Step 1.03 evidence run: `gate1-step03-20260806T050827Z-494925`\n"
        f"Accepted Step 1.04 evidence run: `{run_id}`",
        "PLAN accepted evidence",
    )
    plan = replace_once(
        plan,
        "- [ ] Step 1.04 — canonical vertical slice\n- [ ] Step 1.05 — 12-target batch runner",
        "- [x] Step 1.04 — canonical vertical slice\n- [ ] Step 1.05 — 12-target batch runner",
        "PLAN checklist",
    )

    readme = readme_path.read_text(encoding="utf-8")
    readme = replace_once(
        readme,
        "- **Step 1.03:** complete.\n- **Next package:** `gate-1-step04-drupal-ai-canonical-vertical-slice-v1.0.0`.",
        "- **Step 1.03:** complete.\n- **Step 1.04:** complete.\n- **Next package:** `gate-1-step05-drupal-ai-batch-runner-v1.0.0`.",
        "README current-status",
    )
    readme = replace_once(
        readme,
        "Accepted Step 1.03 evidence run: `gate1-step03-20260806T050827Z-494925`",
        "Accepted Step 1.03 evidence run: `gate1-step03-20260806T050827Z-494925`\n"
        f"Accepted Step 1.04 evidence run: `{run_id}`",
        "README accepted evidence",
    )

    status = status_path.read_text(encoding="utf-8")
    status = replace_once(
        status,
        "**Status date:** August 5, 2026  \n",
        "**Status date:** August 6, 2026\n",
        "CURRENT-STATUS date",
    )
    status = replace_once(
        status,
        "- **Completed packages:** Step 1.01 batch contract, Step 1.02 Drupal AI runtime probe, and Step 1.03 Drupal AI tool adapters.\n"
        "- **Step 1.03 execution:** complete.\n"
        "- **Next package:** `gate-1-step04-drupal-ai-canonical-vertical-slice-v1.0.0`.\n"
        "- **Execution environment:** Codex running locally inside WSL2, governed by `AGENTS.md`.",
        "- **Completed packages:** Step 1.01 batch contract, Step 1.02 Drupal AI runtime probe, Step 1.03 Drupal AI tool adapters, and Step 1.04 canonical vertical slice.\n"
        "- **Step 1.04 execution:** complete.\n"
        "- **Next package:** `gate-1-step05-drupal-ai-batch-runner-v1.0.0`.\n"
        "- **Execution environment:** package-driven local execution inside WSL2, governed by `AGENTS.md`.",
        "CURRENT-STATUS position",
    )
    status = replace_once(
        status,
        "Accepted Step 1.03 evidence run: `gate1-step03-20260806T050827Z-494925`",
        "Accepted Step 1.03 evidence run: `gate1-step03-20260806T050827Z-494925`\n"
        f"Accepted Step 1.04 evidence run: `{run_id}`",
        "CURRENT-STATUS accepted evidence",
    )
    status = replace_once(
        status,
        "Packages 1.01 through 1.03 are complete. The next package is\n"
        "`gate-1-step04-drupal-ai-canonical-vertical-slice-v1.0.0`.",
        "Packages 1.01 through 1.04 are complete. The next package is\n"
        "`gate-1-step05-drupal-ai-batch-runner-v1.0.0`.",
        "CURRENT-STATUS local handoff",
    )

    write(plan_path, plan)
    write(readme_path, readme)
    write(status_path, status)
    print(f"[PASS] Status documents advanced to Step 1.05 after {run_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
