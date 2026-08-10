#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path

ACTIVE_PACKAGE = "gate-2a-step03-langgraph-tool-adapters-v1.0.0"
NEXT_PACKAGE = "gate-2a-step04-langgraph-state-and-sqlite-checkpoint-proof-v1.0.0"

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"[ERROR] {label} anchor count is {text.count(old)}; expected 1")
    return text.replace(old, new, 1)

def activate(repo: Path) -> None:
    paths = {
        "AGENTS.md": repo/"AGENTS.md",
        "PLAN.md": repo/"PLAN.md",
        "README.md": repo/"README.md",
        "docs/CURRENT-STATUS.md": repo/"docs/CURRENT-STATUS.md",
    }
    texts = {k:p.read_text(encoding="utf-8") for k,p in paths.items()}

    t = texts["AGENTS.md"]
    t = replace_once(t,
        "**Next package:** `gate-2a-step03-langgraph-tool-adapters-v1.0.0`.\n\n**Step 2A.02:** active — pinned runtime/checkpoint capability probe only.",
        f"**Active package:** `{ACTIVE_PACKAGE}`.\n\n**Step 2A.03:** active — model-free thin LangChain tool adapters only.",
        "AGENTS active package")
    t = replace_once(t,
        "Do not generate Step 2A.03 until Step 2A.02 is committed, merged, local `main` is resynchronized, and the post-merge audit passes.",
        "Do not generate Step 2A.04 until Step 2A.03 is passing, committed, merged, local `main` is resynchronized, and the post-merge audit passes.",
        "AGENTS next-step guard")
    texts["AGENTS.md"] = t

    t = texts["PLAN.md"]
    t = replace_once(t,
        "**Next package:**\n\n```text\ngate-2a-step03-langgraph-tool-adapters-v1.0.0\n```",
        f"**Active package:**\n\n```text\n{ACTIVE_PACKAGE}\n```",
        "PLAN active package")
    texts["PLAN.md"] = t

    t = texts["README.md"]
    t = replace_once(t,
        "- **Next package:** `gate-2a-step03-langgraph-tool-adapters-v1.0.0`.",
        f"- **Step 2A.03:** active — model-free LangChain tool adapters.\n- **Active package:** `{ACTIVE_PACKAGE}`.",
        "README active package")
    texts["README.md"] = t

    t = texts["docs/CURRENT-STATUS.md"]
    t = replace_once(t,
        "- **Next package:** `gate-2a-step03-langgraph-tool-adapters-v1.0.0`.",
        f"- **Step 2A.03:** active — model-free LangChain tool adapters.\n- **Active package:** `{ACTIVE_PACKAGE}`.",
        "CURRENT active package")
    t = replace_once(t,
        "Step 2A.01 is complete. Step 2A.02 is the active model-free runtime/checkpoint probe. Do not generate Step 2A.03 until Step 2A.02 is committed and merged, local `main` is resynchronized, and the post-merge audit passes.",
        "Step 2A.01 and Step 2A.02 are complete. Step 2A.03 is the active model-free LangChain tool-adapter proof. Do not generate Step 2A.04 until Step 2A.03 is committed and merged, local `main` is resynchronized, and the post-merge audit passes.",
        "CURRENT fresh-session marker")
    texts["docs/CURRENT-STATUS.md"] = t

    for rel, p in paths.items():
        tmp = p.with_name(p.name + ".gate2a-step03.tmp")
        tmp.write_text(texts[rel], encoding="utf-8")
        tmp.replace(p)

def complete(repo: Path, run_id: str) -> None:
    paths = {
        "AGENTS.md": repo/"AGENTS.md",
        "PLAN.md": repo/"PLAN.md",
        "README.md": repo/"README.md",
        "docs/CURRENT-STATUS.md": repo/"docs/CURRENT-STATUS.md",
    }
    texts = {k:p.read_text(encoding="utf-8") for k,p in paths.items()}
    evidence = f"Accepted Step 2A.03 evidence run: `{run_id}`"

    t = texts["AGENTS.md"]
    t = replace_once(t,
        f"**Active package:** `{ACTIVE_PACKAGE}`.\n\n**Step 2A.03:** active — model-free thin LangChain tool adapters only.",
        f"**Step 2A.03:** complete.\n\n**Next package:** `{NEXT_PACKAGE}`.\n\n{evidence}",
        "AGENTS completion")
    texts["AGENTS.md"] = t

    t = texts["PLAN.md"]
    t = replace_once(t,
        f"**Active package:**\n\n```text\n{ACTIVE_PACKAGE}\n```",
        f"**Completed package:**\n\n```text\n{ACTIVE_PACKAGE}\n```\n\n**Next package:**\n\n```text\n{NEXT_PACKAGE}\n```\n\n{evidence}",
        "PLAN completion package")
    t = replace_once(t,
        "- [ ] Step 2A.03 — LangGraph tool adapters",
        "- [x] Step 2A.03 — LangGraph tool adapters",
        "PLAN checkbox")
    texts["PLAN.md"] = t

    t = texts["README.md"]
    t = replace_once(t,
        f"- **Step 2A.03:** active — model-free LangChain tool adapters.\n- **Active package:** `{ACTIVE_PACKAGE}`.",
        f"- **Step 2A.03:** complete.\n- **Next package:** `{NEXT_PACKAGE}`.\n{evidence}",
        "README completion")
    texts["README.md"] = t

    t = texts["docs/CURRENT-STATUS.md"]
    t = replace_once(t,
        f"- **Step 2A.03:** active — model-free LangChain tool adapters.\n- **Active package:** `{ACTIVE_PACKAGE}`.",
        f"- **Step 2A.03:** complete.\n- **Next package:** `{NEXT_PACKAGE}`.\n{evidence}",
        "CURRENT completion")
    t = replace_once(t,
        "Step 2A.01 and Step 2A.02 are complete. Step 2A.03 is the active model-free LangChain tool-adapter proof. Do not generate Step 2A.04 until Step 2A.03 is committed and merged, local `main` is resynchronized, and the post-merge audit passes.",
        "Step 2A.01 through Step 2A.03 are complete. Step 2A.04 is next but remains locked until Step 2A.03 is committed and merged, local `main` is resynchronized, and the post-merge audit passes.",
        "CURRENT completion fresh-session marker")
    texts["docs/CURRENT-STATUS.md"] = t

    for rel, p in paths.items():
        tmp = p.with_name(p.name + ".gate2a-step03.tmp")
        tmp.write_text(texts[rel], encoding="utf-8")
        tmp.replace(p)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--state", choices=["active","complete"], required=True)
    ap.add_argument("--run-id")
    args=ap.parse_args()
    repo=Path(args.repo).resolve()
    if args.state=="active":
        if args.run_id:
            raise SystemExit("[ERROR] --run-id is invalid for active state")
        activate(repo)
    else:
        if not args.run_id:
            raise SystemExit("[ERROR] --run-id is required for complete state")
        complete(repo,args.run_id)

if __name__=="__main__":
    main()
