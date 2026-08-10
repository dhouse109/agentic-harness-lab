#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path

NEXT_PACKAGE="gate-2a-step04-langgraph-state-and-sqlite-checkpoint-proof-v1.0.0"
LIVE_RUN="gate2a-step03-20260809T233127Z-2375581"

def replace_once(text, old, new, label):
    count=text.count(old)
    if count != 1:
        raise SystemExit(f"[ERROR] {label} anchor count is {count}; expected 1")
    return text.replace(old,new,1)

def pending(repo):
    paths={r:repo/r for r in ["AGENTS.md","PLAN.md","README.md","docs/CURRENT-STATUS.md"]}
    texts={r:p.read_text(encoding="utf-8") for r,p in paths.items()}
    texts["AGENTS.md"]=replace_once(
        texts["AGENTS.md"],
        f"**Step 2A.03:** complete.\n\n**Next package:** `{NEXT_PACKAGE}`.\n\nAccepted Step 2A.03 evidence run: `{LIVE_RUN}`",
        f"**Step 2A.03 compliance verification:** pending; accepted live run `{LIVE_RUN}` remains valid.\n\n**Step 2A.04:** locked until the same-step compliance supplement passes.",
        "AGENTS pending")
    texts["PLAN.md"]=replace_once(
        texts["PLAN.md"],
        f"**Completed package:**\n\n```text\ngate-2a-step03-langgraph-tool-adapters-v1.0.0\n```\n\n**Next package:**\n\n```text\n{NEXT_PACKAGE}\n```\n\nAccepted Step 2A.03 evidence run: `{LIVE_RUN}`",
        f"**Step 2A.03 compliance verification:** pending.\n\n**Step 2A.03 live package:**\n\n```text\ngate-2a-step03-langgraph-tool-adapters-v1.0.0\n```\n\n**Step 2A.03 compliance repair:**\n\n```text\ngate-2a-step03-langgraph-tool-adapters-v1.0.2\ngate-2a-step03-langgraph-tool-adapters-v1.0.3\n```\n\nAccepted Step 2A.03 evidence run: `{LIVE_RUN}`\n\n**Step 2A.04 remains locked until the compliance supplement passes.**",
        "PLAN pending package")
    texts["PLAN.md"]=replace_once(
        texts["PLAN.md"],"- [x] Step 2A.03 — LangGraph tool adapters",
        "- [ ] Step 2A.03 — LangGraph tool adapters (compliance verification pending)",
        "PLAN pending checkbox")
    for rel in ["README.md","docs/CURRENT-STATUS.md"]:
        texts[rel]=replace_once(
            texts[rel],
            f"- **Step 2A.03:** complete.\n- **Next package:** `{NEXT_PACKAGE}`.\nAccepted Step 2A.03 evidence run: `{LIVE_RUN}`",
            f"- **Step 2A.03 compliance verification:** pending; accepted live run `{LIVE_RUN}` remains valid.\n- **Step 2A.04:** locked until the same-step compliance supplement passes.",
            rel+" pending")
    texts["docs/CURRENT-STATUS.md"]=replace_once(
        texts["docs/CURRENT-STATUS.md"],
        "Step 2A.01 through Step 2A.03 are complete. Step 2A.04 is next but remains locked until Step 2A.03 is committed and merged, local `main` is resynchronized, and the post-merge audit passes.",
        "Step 2A.01 and Step 2A.02 are complete. Step 2A.03 has a valid accepted live run but remains open for same-step compliance verification. Step 2A.04 remains locked.",
        "CURRENT pending tail")
    for rel,p in paths.items():
        tmp=p.with_name(p.name+".step03-compliance.tmp")
        tmp.write_text(texts[rel],encoding="utf-8"); tmp.replace(p)

def complete(repo, verification_run):
    paths={r:repo/r for r in ["AGENTS.md","PLAN.md","README.md","docs/CURRENT-STATUS.md"]}
    texts={r:p.read_text(encoding="utf-8") for r,p in paths.items()}
    accepted=f"Accepted Step 2A.03 compliance verification: `{verification_run}`"
    texts["AGENTS.md"]=replace_once(
        texts["AGENTS.md"],
        f"**Step 2A.03 compliance verification:** pending; accepted live run `{LIVE_RUN}` remains valid.\n\n**Step 2A.04:** locked until the same-step compliance supplement passes.",
        f"**Step 2A.03:** complete.\n\n**Next package:** `{NEXT_PACKAGE}`.\n\nAccepted Step 2A.03 evidence run: `{LIVE_RUN}`\n{accepted}",
        "AGENTS complete")
    texts["PLAN.md"]=replace_once(
        texts["PLAN.md"],
        f"**Step 2A.03 compliance verification:** pending.\n\n**Step 2A.03 live package:**\n\n```text\ngate-2a-step03-langgraph-tool-adapters-v1.0.0\n```\n\n**Step 2A.03 compliance repair:**\n\n```text\ngate-2a-step03-langgraph-tool-adapters-v1.0.2\ngate-2a-step03-langgraph-tool-adapters-v1.0.3\n```\n\nAccepted Step 2A.03 evidence run: `{LIVE_RUN}`\n\n**Step 2A.04 remains locked until the compliance supplement passes.**",
        f"**Completed Step 2A.03 packages:**\n\n```text\ngate-2a-step03-langgraph-tool-adapters-v1.0.0\ngate-2a-step03-langgraph-tool-adapters-v1.0.2\ngate-2a-step03-langgraph-tool-adapters-v1.0.3\n```\n\n**Next package:**\n\n```text\n{NEXT_PACKAGE}\n```\n\nAccepted Step 2A.03 evidence run: `{LIVE_RUN}`\n{accepted}",
        "PLAN complete package")
    texts["PLAN.md"]=replace_once(
        texts["PLAN.md"],
        "- [ ] Step 2A.03 — LangGraph tool adapters (compliance verification pending)",
        "- [x] Step 2A.03 — LangGraph tool adapters",
        "PLAN complete checkbox")
    for rel in ["README.md","docs/CURRENT-STATUS.md"]:
        texts[rel]=replace_once(
            texts[rel],
            f"- **Step 2A.03 compliance verification:** pending; accepted live run `{LIVE_RUN}` remains valid.\n- **Step 2A.04:** locked until the same-step compliance supplement passes.",
            f"- **Step 2A.03:** complete.\n- **Next package:** `{NEXT_PACKAGE}`.\nAccepted Step 2A.03 evidence run: `{LIVE_RUN}`\n{accepted}",
            rel+" complete")
    texts["docs/CURRENT-STATUS.md"]=replace_once(
        texts["docs/CURRENT-STATUS.md"],
        "Step 2A.01 and Step 2A.02 are complete. Step 2A.03 has a valid accepted live run but remains open for same-step compliance verification. Step 2A.04 remains locked.",
        "Step 2A.01 through Step 2A.03 are complete. Step 2A.04 is next but remains locked until Step 2A.03 is committed and merged, local `main` is resynchronized, and the post-merge audit passes.",
        "CURRENT complete tail")
    for rel,p in paths.items():
        tmp=p.with_name(p.name+".step03-compliance.tmp")
        tmp.write_text(texts[rel],encoding="utf-8"); tmp.replace(p)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo",required=True)
    ap.add_argument("--state",choices=["pending","complete"],required=True)
    ap.add_argument("--verification-run")
    args=ap.parse_args(); repo=Path(args.repo).resolve()
    if args.state=="pending":
        if args.verification_run: raise SystemExit("[ERROR] --verification-run invalid for pending")
        pending(repo)
    else:
        if not args.verification_run: raise SystemExit("[ERROR] --verification-run required")
        complete(repo,args.verification_run)

if __name__=="__main__": main()
