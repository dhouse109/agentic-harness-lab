#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

STEP06_PACKAGE = "gate-1-step06-drupal-ai-batch-evidence-and-human-review-v1.0.0"
STEP07_PACKAGE = "gate-1-step07-drupal-ai-certification-and-handoff-v1.0.0"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        if text.count(old) != 1:
            raise SystemExit(f"[ERROR] Expected one {label} anchor; found {text.count(old)}")
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise SystemExit(f"[ERROR] {label} anchor not found")


def update_plan(path: Path, evidence_run: str) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "> Phase 0 and Gate 0.5 are complete. Gate 1 Steps 1.01 through 1.05 are complete; Step 1.06 is next.",
        "> Phase 0 and Gate 0.5 are complete. Gate 1 Steps 1.01 through 1.06 are complete; Step 1.07 is next.",
        "PLAN current status",
    )
    old = f'''**Next package:**

```text
{STEP06_PACKAGE}
```'''
    new = f'''**Completed package:**

```text
{STEP06_PACKAGE}
```

**Next package:**

```text
{STEP07_PACKAGE}
```'''
    text = replace_once(text, old, new, "PLAN package progression")
    marker = "Accepted Drupal AI batch run: `drupal_ai-20260808T020222Z-205fd9`"
    accepted = f"Accepted Step 1.06 evidence run: `{evidence_run}`"
    if accepted not in text:
        text = replace_once(text, marker, marker + "\n" + accepted, "PLAN accepted evidence")
    text = replace_once(
        text,
        "- [ ] Step 1.06 — batch evidence and human review",
        "- [x] Step 1.06 — batch evidence and human review",
        "PLAN Step 1.06 checkbox",
    )
    path.write_text(text, encoding="utf-8")


def update_readme(path: Path, evidence_run: str) -> None:
    text = path.read_text(encoding="utf-8")
    old = f'''- **Step 1.05:** complete.
- **Next package:** `{STEP06_PACKAGE}`.'''
    new = f'''- **Step 1.05:** complete.
- **Step 1.06:** complete.
- **Next package:** `{STEP07_PACKAGE}`.'''
    text = replace_once(text, old, new, "README progression")
    marker = "Accepted Drupal AI batch run: `drupal_ai-20260808T020222Z-205fd9`"
    accepted = f"Accepted Step 1.06 evidence run: `{evidence_run}`"
    if accepted not in text:
        text = replace_once(text, marker, marker + "\n" + accepted, "README accepted evidence")
    path.write_text(text, encoding="utf-8")


def update_status(path: Path, evidence_run: str) -> None:
    text = path.read_text(encoding="utf-8")
    today = datetime.now(timezone.utc).strftime("%B %-d, %Y")
    # Linux/WSL strftime supports %-d; keep prior date if platform does not.
    first_line = next((line for line in text.splitlines() if line.startswith("**Status date:**")), None)
    if first_line:
        text = text.replace(first_line, f"**Status date:** {today}", 1)
    old = f'''- **Completed packages:** Step 1.01 batch contract, Step 1.02 Drupal AI runtime probe, Step 1.03 Drupal AI tool adapters, Step 1.04 canonical vertical slice, and Step 1.05 12-target batch runner.
- **Step 1.05 execution:** complete; 12 recommendations are pending Step 1.06 human review.
- **Next package:** `{STEP06_PACKAGE}`.'''
    new = f'''- **Completed packages:** Step 1.01 batch contract, Step 1.02 Drupal AI runtime probe, Step 1.03 Drupal AI tool adapters, Step 1.04 canonical vertical slice, Step 1.05 12-target batch runner, and Step 1.06 batch evidence and human review.
- **Step 1.06 execution:** complete; three representative reviewer decisions are retained and the Drupal sandbox is restored to seeded-clean.
- **Next package:** `{STEP07_PACKAGE}`.'''
    text = replace_once(text, old, new, "CURRENT-STATUS progression")
    marker = "Accepted Drupal AI batch run: `drupal_ai-20260808T020222Z-205fd9`"
    accepted = f"Accepted Step 1.06 evidence run: `{evidence_run}`"
    if accepted not in text:
        text = replace_once(text, marker, marker + "\n" + accepted, "CURRENT-STATUS accepted evidence")
    old_packages = f'''Packages 1.01 through 1.05 are complete. The next package is
`{STEP06_PACKAGE}`.'''
    new_packages = f'''Packages 1.01 through 1.06 are complete. The next package is
`{STEP07_PACKAGE}`.'''
    text = replace_once(text, old_packages, new_packages, "CURRENT-STATUS package handoff")
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--evidence-run-id", required=True)
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    update_plan(repo / "PLAN.md", args.evidence_run_id)
    update_readme(repo / "README.md", args.evidence_run_id)
    update_status(repo / "docs/CURRENT-STATUS.md", args.evidence_run_id)
    print(f"[PASS] Status documents advanced to Step 1.07 using evidence {args.evidence_run_id}.")


if __name__ == "__main__":
    main()
