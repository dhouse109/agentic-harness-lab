#!/usr/bin/env python3
"""Promote Step 2A.07 lifecycle documents from active to complete."""
from __future__ import annotations

import argparse
from pathlib import Path

PACKAGE = "gate-2a-step07-langgraph-batch-runner-v1.0.5"
NEXT = "gate-2a-step08-langgraph-fresh-batch-and-continuation-v1.0.0"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"[ERROR] Expected exactly one lifecycle anchor in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def complete(repo: Path, run_dir: str) -> None:
    accepted = f"Accepted Step 2A.07 construction evidence run: `{run_dir}`"

    replace_once(
        repo / "AGENTS.md",
        f"**Step 2A.07:** active — model-free LangGraph batch-runner construction and continuation wiring.\n\n**Active package:** `{PACKAGE}`.\n\n**Next package:** `{NEXT}` — locked.\n",
        f"**Step 2A.07:** complete.\n\n**Completed package:** `{PACKAGE}`.\n\n**Next package:** `{NEXT}`.\n\n{accepted}\n",
    )
    replace_once(
        repo / "AGENTS.md",
        "Step 2A.07 is active. Do not generate or execute Step 2A.08 until Step 2A.07 is verified, certified model-free, committed, merged, local `main` is resynchronized, and the post-merge audit passes.",
        "Do not generate or execute Step 2A.08 until Step 2A.07 is committed, merged, local `main` is resynchronized, and the post-merge audit passes.",
    )

    replace_once(
        repo / "README.md",
        f"- **Step 2A.07:** active — model-free batch-runner construction and continuation wiring.\n- **Active package:** `{PACKAGE}`.\n- **Next package:** `{NEXT}` — locked.\n",
        f"- **Step 2A.07:** complete.\n- **Completed package:** `{PACKAGE}`.\n- **Next package:** `{NEXT}`.\n{accepted}\n",
    )

    replace_once(
        repo / "docs/CURRENT-STATUS.md",
        f"- **Step 2A.07:** active — model-free batch-runner construction and continuation wiring.\n- **Active package:** `{PACKAGE}`.\n- **Next package:** `{NEXT}` — locked.\n",
        f"- **Step 2A.07:** complete.\n- **Completed package:** `{PACKAGE}`.\n- **Next package:** `{NEXT}`.\n{accepted}\n",
    )
    replace_once(
        repo / "docs/CURRENT-STATUS.md",
        "Step 2A.01 through Step 2A.06 are complete. Step 2A.07 is active. Step 2A.08 remains locked until Step 2A.07 is verified, certified model-free, committed, merged, local `main` is resynchronized, and the post-merge audit passes.",
        "Step 2A.01 through Step 2A.07 are complete. Step 2A.08 is next but remains locked until Step 2A.07 is committed and merged, local `main` is resynchronized, and the post-merge audit passes.",
    )

    replace_once(
        repo / "PLAN.md",
        f"**Active Step 2A.07 package:**\n\n```text\n{PACKAGE}\n```\n\n**Next package (locked):**\n\n```text\n{NEXT}\n```\n",
        f"**Completed Step 2A.07 package:**\n\n```text\n{PACKAGE}\n```\n\n**Next package:**\n\n```text\n{NEXT}\n```\n\n{accepted}\n",
    )
    replace_once(repo / "PLAN.md", "- [ ] Step 2A.07 — LangGraph batch runner", "- [x] Step 2A.07 — LangGraph batch runner")
    print("[PASS] Step 2A.07 lifecycle documents set to complete.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--state", choices=("complete",), required=True)
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    complete(Path(args.repo).resolve(), args.run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
