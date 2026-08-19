#!/usr/bin/env python3
"""Render truthful Step 2B.04 lifecycle documents, optionally without mutation."""

from __future__ import annotations

import argparse
from pathlib import Path


PACKAGE = "gate-2b-step04-crewai-canonical-vertical-slice-v1.0.0"
STEP03_PACKAGE = "gate-2b-step03-crewai-shared-operation-adapters-v1.0.0"
STEP03_EVIDENCE = "gate2b-step03-20260818T163812Z-7a58ef58"
STEP03_MERGE = "7629434b04d04154b9f219e1d93ed772401a1288"
FILES = ("AGENTS.md", "PLAN.md", "README.md", "docs/CURRENT-STATUS.md", "docs/CODEX-GATE-2B-RUNBOOK.md")


def replace_once(text: str, old: str, new: str, path: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one lifecycle anchor in {path}, found {count}: {old[:80]!r}")
    return text.replace(old, new, 1)


def step04_text(state: str, run_id: str | None) -> str:
    if state == "active":
        return (
            f"**Current Step 2B.04 package:** `{PACKAGE}` is installed locally and active. "
            "No Step 2B.04 evidence exists; no model/provider request or Drupal mutation has occurred. "
            "Step 2B.04 is uncommitted and unmerged. Later continuation/batch work remains unbegun."
        )
    if not run_id:
        raise RuntimeError("Complete state requires --run-id")
    return (
        f"**Completed Step 2B.04 package:** `{PACKAGE}` completed locally with accepted canonical-slice evidence "
        f"`{run_id}`. It is not yet committed or merged. The recommendation remains pending Drupal-authoritative "
        "review; human-feedback continuation and later batch work remain unbegun."
    )


def authorization_text(state: str) -> str:
    if state == "active":
        return (
            "**Gate 2B Step 2B.04 active authorization:** installation and disposable rehearsal use zero "
            "model/provider calls, successful outbound model connections, Drupal/source mutations, human-review "
            "actions, dependency changes, live submissions, and Gate 2C executions. Live execution requires "
            "separate explicit authorization for exactly one logical generation, one physical provider request, "
            "and at most one shared-operation recommendation submission."
        )
    return (
        "**Gate 2B Step 2B.04 observed authorization:** exactly one logical generation, one physical provider "
        "request, one successful provider response, and one shared-operation recommendation mutation occurred. "
        "Provider/transport/guardrail/repair/fallback/learning retries or calls, source-content mutations, "
        "human-review actions, dependency changes, and Gate 2C executions remained zero."
    )


def render(path: str, text: str, state: str, run_id: str | None) -> str:
    step03_truth = (
        f"Package `{STEP03_PACKAGE}` is complete, committed, normally merged at `{STEP03_MERGE}`, "
        f"resynchronized, and post-merge audited with accepted model-free evidence `{STEP03_EVIDENCE}`."
    )
    current = step04_text(state, run_id)
    if current in text:
        return text
    active = step04_text("active", None)
    if state == "complete" and active in text:
        text = replace_once(text, active, current, path)
        if path == "AGENTS.md":
            text = replace_once(text, authorization_text("active"), authorization_text("complete"), path)
        return text
    if path == "AGENTS.md":
        text = replace_once(text,
            f"**Step 2B.03:** complete locally with accepted model-free adapter evidence `{STEP03_EVIDENCE}` and a passing permanent audit. It has not been committed or merged. Step 2B.04 remains unbegun; no later Gate 2B package is named or begun.",
            f"**Step 2B.03:** {step03_truth}\n\n{current}", path)
        text = replace_once(text,
            f"**Gate 2B Step 2B.03 authorization:** zero model/provider calls, zero successful outbound network connections, zero CrewAI-origin Drupal mutations, zero source-content mutations, zero authoritative human-review actions, zero dependency changes, zero live recommendation submissions, and zero Gate 2C executions.",
            authorization_text(state), path)
        text = replace_once(text,
            f"Step 2B.03 completed its model-free shared-operation adapter boundary with accepted evidence `{STEP03_EVIDENCE}`. Do not begin a later package until Step 2B.03 is committed, merged, resynchronized, and post-merge audited.",
            f"{step03_truth} Step 2B.04 is the only active boundary; do not begin later continuation, batch, or Gate 2C work.", path)
    elif path == "README.md":
        text = replace_once(text,
            f"- **Step 2B.03:** complete locally with accepted model-free adapter evidence `{STEP03_EVIDENCE}` and a passing permanent audit. It has not been committed or merged. Step 2B.04 remains unbegun; no later Gate 2B package is named or begun.",
            f"- **Step 2B.03:** {step03_truth}\n- {current}", path)
        text = replace_once(text,
            "Delivery packages remain outside Git under `~/projects/agentic-harness-package-staging/`. Step 2B.02 is complete, merged, resynchronized, and post-merge audited. Step 2B.03 proves only the model-free CrewAI shared-operation adapter boundary; it does not establish model, lifecycle, Drupal-mutation, human-review, batch, or Gate 2C evidence.",
            f"Delivery packages remain outside Git under `~/projects/agentic-harness-package-staging/`. {step03_truth} Step 2B.04 is limited to the canonical target-1 Flow/model/submission/persistence boundary and does not claim human-review continuation, batch completion, Gate 2C recovery, production readiness, or framework superiority.", path)
    elif path == "docs/CURRENT-STATUS.md":
        text = replace_once(text,
            f"- **Step 2B.03:** complete locally with accepted model-free adapter evidence `{STEP03_EVIDENCE}` and a passing permanent audit. It has not been committed or merged. Step 2B.04 remains unbegun; no later Gate 2B package is named or begun.",
            f"- **Step 2B.03:** {step03_truth}\n- {current}", path)
        text = replace_once(text,
            f"Use `docs/handoffs/GATE-2A-TO-CREWAI-HANDOFF.md`, the Step 2B.01 contract, the Step 2B.02 runtime-probe document, ADR-0012, and `docs/CODEX-GATE-2B-RUNBOOK.md`. Steps 2B.01 through 2B.03 have completed their current evidence boundaries; Step 2B.03 evidence `{STEP03_EVIDENCE}` awaits commit, merge, resynchronization, and post-merge audit. Gate 2C remains deferred and unclaimed.",
            f"Use `docs/handoffs/GATE-2A-TO-CREWAI-HANDOFF.md`, the Step 2B.01 contract, the Step 2B.02 runtime-probe document, ADR-0012, and `docs/CODEX-GATE-2B-RUNBOOK.md`. {step03_truth} Step 2B.04 is the current bounded canonical-slice lifecycle. Gate 2C remains deferred and unclaimed.", path)
    elif path == "PLAN.md":
        text = replace_once(text,
            f"Step 2B.02 is committed, merged, resynchronized, and post-merge audited. Package `{STEP03_PACKAGE}` completed with accepted model-free evidence `{STEP03_EVIDENCE}`. No later Gate 2B package is named or begun.",
            f"Step 2B.02 is committed, merged, resynchronized, and post-merge audited. {step03_truth}\n\n{current}", path)
    elif path == "docs/CODEX-GATE-2B-RUNBOOK.md":
        text = replace_once(text,
            f"Step 2B.02 is committed, merged, locally resynchronized, and post-merge audited. The current package is `{STEP03_PACKAGE}`. Its model-free CrewAI tool layer over the frozen shared operations is accepted in `{STEP03_EVIDENCE}`. No later Gate 2B package is named or begun.",
            f"Step 2B.02 is committed, merged, locally resynchronized, and post-merge audited. {step03_truth}\n\n{current}", path)
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--state", choices=("active", "complete"), required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    output = args.output_root.resolve() if args.output_root else repo
    for relative in FILES:
        source = repo / relative
        target = output / relative
        rendered = render(relative, source.read_text(encoding="utf-8"), args.state, args.run_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
