#!/usr/bin/env python3
"""Apply exact, fail-closed Step 2B.03 lifecycle transitions."""

from __future__ import annotations

import argparse
from pathlib import Path


FILES = (
    "AGENTS.md",
    "docs/CURRENT-STATUS.md",
    "PLAN.md",
    "README.md",
    "docs/CODEX-GATE-2B-RUNBOOK.md",
)

STEP03_PACKAGE = "gate-2b-step03-crewai-shared-operation-adapters-v1.0.0"

ACTIVE_REPLACEMENTS: dict[str, tuple[tuple[str, str], ...]] = {
    "AGENTS.md": (
        (
            "**Step 2B.02:** complete after retained model-free runtime evidence, permanent architecture audit, and explicit human architecture approval.",
            "**Step 2B.02:** complete, merged, resynchronized, and post-merge audited after retained model-free runtime evidence, permanent architecture audit, and explicit human architecture approval.",
        ),
        (
            "**Next package:** `gate-2b-step03-crewai-shared-operation-adapters-v1.0.0` is named but locked and unbegun pending Step 2B.02 commit, merge, local `main` resynchronization, and post-merge audit.",
            "**Current package:** `gate-2b-step03-crewai-shared-operation-adapters-v1.0.0` is installed and active. Its model-free adapter evidence has not yet been captured or accepted.",
        ),
        (
            "**Gate 2B Step 2B.02 authorization:** zero model/provider calls, zero CrewAI-origin Drupal mutations, zero source-content mutations, zero authoritative human-review actions, zero dependency changes, zero live recommendation submissions, and zero Gate 2C executions.",
            "**Gate 2B Step 2B.03 authorization:** zero model/provider calls, zero successful outbound network connections, zero CrewAI-origin Drupal mutations, zero source-content mutations, zero authoritative human-review actions, zero dependency changes, zero live recommendation submissions, and zero Gate 2C executions.",
        ),
        (
            "Step 2B.02 created only model-free CrewAI-specific runtime and governed-disposition evidence. Step 2B.03 remains locked until the completed Step 2B.02 boundary is committed, merged, resynchronized to local `main`, and passes its permanent post-merge audit. Do not generate or begin Step 2B.03 before that approval boundary.",
            "Step 2B.02 created only model-free CrewAI-specific runtime and governed-disposition evidence and is merged, resynchronized, and post-merge audited. Step 2B.03 is the active model-free shared-operation adapter boundary. Do not begin a later package until Step 2B.03 passes, is committed, merged, resynchronized, and post-merge audited.",
        ),
    ),
    "docs/CURRENT-STATUS.md": (
        (
            "- **Step 2B.02:** complete with retained model-free evidence, all 25 permanent architecture predicates passing, and explicit human architecture approval.",
            "- **Step 2B.02:** complete, merged, resynchronized, and post-merge audited with retained model-free evidence, all 25 permanent architecture predicates passing, and explicit human architecture approval.",
        ),
        (
            "- **Next package:** `gate-2b-step03-crewai-shared-operation-adapters-v1.0.0` is named but locked and unbegun pending Step 2B.02 commit, merge, local `main` resynchronization, and post-merge audit.",
            "- **Current package:** `gate-2b-step03-crewai-shared-operation-adapters-v1.0.0` is installed and active; its model-free adapter evidence has not yet been captured or accepted.",
        ),
        (
            "Use `docs/handoffs/GATE-2A-TO-CREWAI-HANDOFF.md`, the Step 2B.01 contract, the Step 2B.02 runtime-probe document, and `docs/CODEX-GATE-2B-RUNBOOK.md`. Step 2B.01 is closed and Step 2B.02 is active. Do not create an ADR or begin Step 2B.03 without evidence-supported architecture approval. Gate 2C remains deferred and unclaimed.",
            "Use `docs/handoffs/GATE-2A-TO-CREWAI-HANDOFF.md`, the Step 2B.01 contract, the Step 2B.02 runtime-probe document, ADR-0012, and `docs/CODEX-GATE-2B-RUNBOOK.md`. Steps 2B.01 and 2B.02 are closed; Step 2B.03 is the active model-free shared-operation adapter boundary. Gate 2C remains deferred and unclaimed.",
        ),
    ),
    "PLAN.md": (
        (
            "- [ ] Step 2B.03 — CrewAI shared-operation adapters (named, locked, and unbegun)",
            "- [ ] Step 2B.03 — CrewAI shared-operation adapters (active; model-free evidence not yet accepted)",
        ),
        (
            "The next proposed package is `gate-2b-step03-crewai-shared-operation-adapters-v1.0.0`. It remains locked and unbegun until Step 2B.02 is committed, merged, resynchronized, and post-merge audited.",
            "Step 2B.02 is committed, merged, resynchronized, and post-merge audited. The current package is `gate-2b-step03-crewai-shared-operation-adapters-v1.0.0`; it installs the model-free adapter boundary before evidence capture. No later Gate 2B package is named or begun.",
        ),
    ),
    "README.md": (
        (
            "- **Step 2B.02:** complete with retained model-free evidence, permanent architecture audit, and explicit human architecture approval.",
            "- **Step 2B.02:** complete, merged, resynchronized, and post-merge audited with retained model-free evidence, permanent architecture audit, and explicit human architecture approval.",
        ),
        (
            "- **Next package:** `gate-2b-step03-crewai-shared-operation-adapters-v1.0.0` is named but locked and unbegun pending commit, merge, resynchronization, and post-merge audit.",
            "- **Current package:** `gate-2b-step03-crewai-shared-operation-adapters-v1.0.0` is installed and active; its model-free adapter evidence has not yet been captured or accepted.",
        ),
        (
            "Delivery packages remain outside Git under `~/projects/agentic-harness-package-staging/`. Step 2B.02 observes pinned CrewAI runtime behavior model-free and mutation-free. Its evidence must distinguish state persistence, checkpoint restoration, continuation, replay, and re-execution; it does not establish Gate 2C recovery evidence.",
            "Delivery packages remain outside Git under `~/projects/agentic-harness-package-staging/`. Step 2B.02 is complete, merged, resynchronized, and post-merge audited. Step 2B.03 proves only the model-free CrewAI shared-operation adapter boundary; it does not establish model, lifecycle, Drupal-mutation, human-review, batch, or Gate 2C evidence.",
        ),
    ),
    "docs/CODEX-GATE-2B-RUNBOOK.md": (
        (
            "The next proposed package is `gate-2b-step03-crewai-shared-operation-adapters-v1.0.0`. It is named but locked and unbegun. Do not prepare it until Step 2B.02 is committed and merged, local `main` is resynchronized, and the lifecycle-compatible Step 2B.02 closure audit passes on merged `main`.",
            "Step 2B.02 is committed, merged, locally resynchronized, and post-merge audited. The current package is `gate-2b-step03-crewai-shared-operation-adapters-v1.0.0`. It installs a model-free CrewAI tool layer over the frozen shared operations; no adapter evidence is accepted until the installed runner creates a passing immutable run.",
        ),
    ),
}


def complete_replacements(run_id: str) -> dict[str, tuple[tuple[str, str], ...]]:
    pending = "its model-free adapter evidence has not yet been captured or accepted"
    accepted = f"accepted model-free adapter evidence `{run_id}` and a passing permanent audit"
    return {
        "AGENTS.md": (
            (
                "**Current package:** `gate-2b-step03-crewai-shared-operation-adapters-v1.0.0` is installed and active. Its model-free adapter evidence has not yet been captured or accepted.",
                f"**Completed Step 2B.03 package:** `{STEP03_PACKAGE}`.\n\n"
                f"**Step 2B.03:** complete locally with {accepted}. It has not been committed or merged. "
                "Step 2B.04 remains unbegun; no later Gate 2B package is named or begun.",
            ),
            (
                "Step 2B.02 created only model-free CrewAI-specific runtime and governed-disposition evidence and is merged, resynchronized, and post-merge audited. Step 2B.03 is the active model-free shared-operation adapter boundary. Do not begin a later package until Step 2B.03 passes, is committed, merged, resynchronized, and post-merge audited.",
                f"Step 2B.03 completed its model-free shared-operation adapter boundary with accepted evidence `{run_id}`. Do not begin a later package until Step 2B.03 is committed, merged, resynchronized, and post-merge audited.",
            ),
        ),
        "docs/CURRENT-STATUS.md": (
            (
                f"- **Current package:** `gate-2b-step03-crewai-shared-operation-adapters-v1.0.0` is installed and active; {pending}.",
                f"- **Completed Step 2B.03 package:** `{STEP03_PACKAGE}`.\n"
                f"- **Step 2B.03:** complete locally with {accepted}. It has not been committed or merged. "
                "Step 2B.04 remains unbegun; no later Gate 2B package is named or begun.",
            ),
            (
                "Use `docs/handoffs/GATE-2A-TO-CREWAI-HANDOFF.md`, the Step 2B.01 contract, the Step 2B.02 runtime-probe document, ADR-0012, and `docs/CODEX-GATE-2B-RUNBOOK.md`. Steps 2B.01 and 2B.02 are closed; Step 2B.03 is the active model-free shared-operation adapter boundary. Gate 2C remains deferred and unclaimed.",
                f"Use `docs/handoffs/GATE-2A-TO-CREWAI-HANDOFF.md`, the Step 2B.01 contract, the Step 2B.02 runtime-probe document, ADR-0012, and `docs/CODEX-GATE-2B-RUNBOOK.md`. Steps 2B.01 through 2B.03 have completed their current evidence boundaries; Step 2B.03 evidence `{run_id}` awaits commit, merge, resynchronization, and post-merge audit. Gate 2C remains deferred and unclaimed.",
            ),
        ),
        "PLAN.md": (
            (
                "- [ ] Step 2B.03 — CrewAI shared-operation adapters (active; model-free evidence not yet accepted)",
                f"- [x] Step 2B.03 — CrewAI shared-operation adapters (accepted evidence `{run_id}`)",
            ),
            (
                "The current package is `gate-2b-step03-crewai-shared-operation-adapters-v1.0.0`; it installs the model-free adapter boundary before evidence capture. No later Gate 2B package is named or begun.",
                f"Package `gate-2b-step03-crewai-shared-operation-adapters-v1.0.0` completed with accepted model-free evidence `{run_id}`. No later Gate 2B package is named or begun.",
            ),
        ),
        "README.md": (
            (
                f"- **Current package:** `gate-2b-step03-crewai-shared-operation-adapters-v1.0.0` is installed and active; {pending}.",
                f"- **Completed Step 2B.03 package:** `{STEP03_PACKAGE}`.\n"
                f"- **Step 2B.03:** complete locally with {accepted}. It has not been committed or merged. "
                "Step 2B.04 remains unbegun; no later Gate 2B package is named or begun.",
            ),
        ),
        "docs/CODEX-GATE-2B-RUNBOOK.md": (
            (
                "It installs a model-free CrewAI tool layer over the frozen shared operations; no adapter evidence is accepted until the installed runner creates a passing immutable run.",
                f"Its model-free CrewAI tool layer over the frozen shared operations is accepted in `{run_id}`. No later Gate 2B package is named or begun.",
            ),
        ),
    }


def apply_exact(text: str, old: str, new: str, path: str) -> str:
    old_count = text.count(old)
    new_count = text.count(new)
    if old_count == 1 and new_count == 0:
        return text.replace(old, new)
    if old_count == 0 and new_count == 1:
        return text
    raise SystemExit(
        f"[ERROR] {path}: lifecycle anchor is neither exact source nor exact rendered state: "
        f"old={old_count} new={new_count}: {old}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--state", required=True, choices=("active", "complete"))
    parser.add_argument("--run-id")
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    if args.state == "complete" and not args.run_id:
        parser.error("--run-id is required for complete state")
    replacements = ACTIVE_REPLACEMENTS if args.state == "active" else complete_replacements(args.run_id)
    output_root = args.output_root or args.repo
    rendered: dict[str, str] = {}
    for relative in FILES:
        source = args.repo / relative
        text = source.read_text(encoding="utf-8")
        for old, new in replacements.get(relative, ()):
            text = apply_exact(text, old, new, relative)
        rendered[relative] = text
    for relative, text in rendered.items():
        destination = output_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")
    print(f"[PASS] Step 2B.03 lifecycle state rendered: {args.state}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
