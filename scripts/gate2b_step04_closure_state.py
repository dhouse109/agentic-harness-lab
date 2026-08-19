#!/usr/bin/env python3
"""Render Step 2B.04 closure lifecycle text without hiding the original live run."""

from __future__ import annotations

import argparse
from pathlib import Path


FILES = (
    "AGENTS.md",
    "PLAN.md",
    "README.md",
    "docs/CURRENT-STATUS.md",
    "docs/CODEX-GATE-2B-RUNBOOK.md",
)
OLD = (
    "**Completed Step 2B.04 package:** `gate-2b-step04-crewai-canonical-vertical-slice-v1.0.0` "
    "completed locally with accepted canonical-slice evidence `crewai-20260818T215017Z-8e03fc95`. "
    "It is not yet committed or merged. The recommendation remains pending Drupal-authoritative review; "
    "human-feedback continuation and later batch work remain unbegun."
)


def replacement(closure_id: str) -> str:
    return (
        "**Completed Step 2B.04 package:** `gate-2b-step04-crewai-canonical-vertical-slice-v1.0.0` "
        "completed the successful live run with immutable canonical evidence "
        "`crewai-20260818T215017Z-8e03fc95`. Same-step repair "
        "`gate-2b-step04-crewai-canonical-vertical-slice-v1.0.1` added model-free post-process-close "
        f"provenance `{closure_id}` and strengthened permanent-audit coverage without replaying the experiment. "
        "The result is not yet committed or merged. The recommendation remains pending Drupal-authoritative "
        "review; human-feedback continuation and later batch work remain unbegun."
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--closure-id", required=True)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    output = args.output_root.resolve() if args.output_root else repo
    new = replacement(args.closure_id)
    for relative in FILES:
        source = repo / relative
        text = source.read_text(encoding="utf-8")
        marker = "- " + OLD if relative in {"README.md", "docs/CURRENT-STATUS.md"} else OLD
        rendered = "- " + new if marker.startswith("- ") else new
        if text.count(marker) != 1:
            raise RuntimeError(f"Expected one closure lifecycle anchor in {relative}, found {text.count(marker)}")
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text.replace(marker, rendered, 1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
