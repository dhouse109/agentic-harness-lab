#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

ACTIVE_PACKAGE = "gate-2a-step05-langgraph-canonical-vertical-slice-v1.0.0"
NEXT_PACKAGE = "gate-2a-step06-langgraph-human-interrupt-and-review-resume-v1.0.0"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"[ERROR] {label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def paths(repo: Path) -> dict[str, Path]:
    return {
        "AGENTS.md": repo / "AGENTS.md",
        "PLAN.md": repo / "PLAN.md",
        "README.md": repo / "README.md",
        "docs/CURRENT-STATUS.md": repo / "docs/CURRENT-STATUS.md",
    }


def activate(repo: Path) -> None:
    ps = paths(repo)
    texts = {rel: path.read_text(encoding="utf-8") for rel, path in ps.items()}

    t = texts["AGENTS.md"]
    t = replace_once(
        t,
        "**Step 2A.04:** complete.\n\n**Next package:** `gate-2a-step05-langgraph-canonical-vertical-slice-v1.0.0`.",
        "**Step 2A.04:** complete.\n\n"
        "**Step 2A.05:** active — one-target canonical LangGraph vertical slice.\n\n"
        f"**Active package:** `{ACTIVE_PACKAGE}`.",
        "AGENTS active package",
    )
    t = replace_once(
        t,
        "Do not generate Step 2A.05 until Step 2A.04 is passing, committed, merged, local `main` is resynchronized, and the post-merge audit passes.",
        "Do not generate Step 2A.06 until Step 2A.05 is passing, committed, merged, local `main` is resynchronized, and the post-merge audit passes.",
        "AGENTS next-step guard",
    )
    texts["AGENTS.md"] = t

    t = texts["PLAN.md"]
    t = replace_once(
        t,
        "**Next package:**\n\n```text\ngate-2a-step05-langgraph-canonical-vertical-slice-v1.0.0\n```",
        f"**Active package:**\n\n```text\n{ACTIVE_PACKAGE}\n```",
        "PLAN active package",
    )
    texts["PLAN.md"] = t

    t = texts["README.md"]
    t = replace_once(
        t,
        "- **Next package:** `gate-2a-step05-langgraph-canonical-vertical-slice-v1.0.0`.",
        "- **Step 2A.05:** active — one-target canonical LangGraph vertical slice.\n"
        f"- **Active package:** `{ACTIVE_PACKAGE}`.",
        "README active package",
    )
    texts["README.md"] = t

    t = texts["docs/CURRENT-STATUS.md"]
    t = replace_once(
        t,
        "- **Next package:** `gate-2a-step05-langgraph-canonical-vertical-slice-v1.0.0`.",
        "- **Step 2A.05:** active — one-target canonical LangGraph vertical slice.\n"
        f"- **Active package:** `{ACTIVE_PACKAGE}`.",
        "CURRENT active package",
    )
    t = replace_once(
        t,
        "Step 2A.01 through Step 2A.04 are complete. Step 2A.05 is next but remains locked until Step 2A.04 is committed and merged, local `main` is resynchronized, and the post-merge audit passes.",
        "Step 2A.01 through Step 2A.04 are complete. Step 2A.05 is the active one-target canonical LangGraph vertical slice. Do not generate Step 2A.06 until Step 2A.05 is committed and merged, local `main` is resynchronized, and the post-merge audit passes.",
        "CURRENT active fresh-session marker",
    )
    texts["docs/CURRENT-STATUS.md"] = t

    for rel, path in ps.items():
        tmp = path.with_name(path.name + ".gate2a-step05.tmp")
        tmp.write_text(texts[rel], encoding="utf-8")
        tmp.replace(path)


def complete(repo: Path, run_dir: str) -> None:
    ps = paths(repo)
    texts = {rel: path.read_text(encoding="utf-8") for rel, path in ps.items()}
    evidence_line = f"Accepted Step 2A.05 evidence run: `{run_dir}`"

    t = texts["AGENTS.md"]
    t = replace_once(
        t,
        "**Step 2A.05:** active — one-target canonical LangGraph vertical slice.\n\n"
        f"**Active package:** `{ACTIVE_PACKAGE}`.",
        f"**Step 2A.05:** complete.\n\n**Next package:** `{NEXT_PACKAGE}`.\n\n{evidence_line}",
        "AGENTS completion",
    )
    texts["AGENTS.md"] = t

    t = texts["PLAN.md"]
    t = replace_once(
        t,
        f"**Active package:**\n\n```text\n{ACTIVE_PACKAGE}\n```",
        f"**Completed Step 2A.05 package:**\n\n```text\n{ACTIVE_PACKAGE}\n```\n\n"
        f"**Next package:**\n\n```text\n{NEXT_PACKAGE}\n```\n\n{evidence_line}",
        "PLAN completion package",
    )
    t = replace_once(
        t,
        "- [ ] Step 2A.05 — LangGraph canonical vertical slice",
        "- [x] Step 2A.05 — LangGraph canonical vertical slice",
        "PLAN checkbox",
    )
    texts["PLAN.md"] = t

    t = texts["README.md"]
    t = replace_once(
        t,
        "- **Step 2A.05:** active — one-target canonical LangGraph vertical slice.\n"
        f"- **Active package:** `{ACTIVE_PACKAGE}`.",
        f"- **Step 2A.05:** complete.\n- **Next package:** `{NEXT_PACKAGE}`.\n{evidence_line}",
        "README completion",
    )
    texts["README.md"] = t

    t = texts["docs/CURRENT-STATUS.md"]
    t = replace_once(
        t,
        "- **Step 2A.05:** active — one-target canonical LangGraph vertical slice.\n"
        f"- **Active package:** `{ACTIVE_PACKAGE}`.",
        f"- **Step 2A.05:** complete.\n- **Next package:** `{NEXT_PACKAGE}`.\n{evidence_line}",
        "CURRENT completion",
    )
    t = replace_once(
        t,
        "Step 2A.01 through Step 2A.04 are complete. Step 2A.05 is the active one-target canonical LangGraph vertical slice. Do not generate Step 2A.06 until Step 2A.05 is committed and merged, local `main` is resynchronized, and the post-merge audit passes.",
        "Step 2A.01 through Step 2A.05 are complete. Step 2A.06 is next but remains locked until Step 2A.05 is committed and merged, local `main` is resynchronized, and the post-merge audit passes.",
        "CURRENT completion fresh-session marker",
    )
    texts["docs/CURRENT-STATUS.md"] = t

    for rel, path in ps.items():
        tmp = path.with_name(path.name + ".gate2a-step05.tmp")
        tmp.write_text(texts[rel], encoding="utf-8")
        tmp.replace(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--state", choices=["active", "complete"], required=True)
    ap.add_argument("--run-dir")
    args = ap.parse_args()
    repo = Path(args.repo).resolve()

    if args.state == "active":
        if args.run_dir:
            raise SystemExit("[ERROR] --run-dir is invalid for active state")
        activate(repo)
    else:
        if not args.run_dir:
            raise SystemExit("[ERROR] --run-dir is required for complete state")
        complete(repo, args.run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
