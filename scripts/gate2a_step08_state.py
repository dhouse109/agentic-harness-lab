#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path

PKG = "gate-2a-step08-langgraph-fresh-batch-and-continuation-v1.0.7"
NEXT = "gate-2a-step09-langgraph-evidence-claims-and-matrix-v1.0.0"

def req(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[ERROR] {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    req(count == 1, f"{label}: expected exactly one replacement anchor, found {count}")
    return text.replace(old, new, 1)

def active(repo: Path) -> None:
    # AGENTS
    p = repo/"AGENTS.md"; t=p.read_text()
    anchor = (
        "**Step 2A.07:** complete.\n\n"
        "**Completed package:** `gate-2a-step07-langgraph-batch-runner-v1.0.5`.\n\n"
        "**Next package:** `gate-2a-step08-langgraph-fresh-batch-and-continuation-v1.0.0`."
    )
    repl = (
        "**Step 2A.07:** complete.\n\n"
        "**Step 2A.08:** active — fresh 12-target LangGraph batch and same-run continuation.\n\n"
        f"**Active package:** `{PKG}`.\n\n"
        f"**Next package:** `{NEXT}` — locked."
    )
    t=replace_once(t, anchor, repl, "AGENTS lifecycle")
    old="Do not generate or execute Step 2A.08 until Step 2A.07 is committed, merged, local `main` is resynchronized, and the post-merge audit passes."
    new="Step 2A.08 is active. Do not generate or execute Step 2A.09 until Step 2A.08 is verified, certified, committed, merged, local `main` is resynchronized, and the post-merge audit passes."
    t=replace_once(t, old, new, "AGENTS lock")
    p.write_text(t)

    # README
    p=repo/"README.md"; t=p.read_text()
    anchor=(
        "- **Step 2A.07:** complete.\n"
        "- **Completed package:** `gate-2a-step07-langgraph-batch-runner-v1.0.5`.\n"
        "- **Next package:** `gate-2a-step08-langgraph-fresh-batch-and-continuation-v1.0.0`."
    )
    repl=(
        "- **Step 2A.07:** complete.\n"
        "- **Step 2A.08:** active — fresh 12-target LangGraph batch and same-run continuation.\n"
        f"- **Active package:** `{PKG}`.\n"
        f"- **Next package:** `{NEXT}` — locked."
    )
    t=replace_once(t, anchor, repl, "README lifecycle")
    p.write_text(t)

    # CURRENT-STATUS
    p=repo/"docs/CURRENT-STATUS.md"; t=p.read_text()
    anchor=(
        "- **Step 2A.07:** complete.\n"
        "- **Completed package:** `gate-2a-step07-langgraph-batch-runner-v1.0.5`.\n"
        "- **Next package:** `gate-2a-step08-langgraph-fresh-batch-and-continuation-v1.0.0`."
    )
    repl=(
        "- **Step 2A.07:** complete.\n"
        "- **Step 2A.08:** active — fresh 12-target LangGraph batch and same-run continuation.\n"
        f"- **Active package:** `{PKG}`.\n"
        f"- **Next package:** `{NEXT}` — locked."
    )
    t=replace_once(t, anchor, repl, "CURRENT lifecycle")
    old="Step 2A.01 through Step 2A.07 are complete. Step 2A.08 is next but remains locked until Step 2A.07 is committed and merged, local `main` is resynchronized, and the post-merge audit passes."
    new="Step 2A.01 through Step 2A.07 are complete. Step 2A.08 is active. Step 2A.09 remains locked until Step 2A.08 is verified, certified, committed and merged, local `main` is resynchronized, and the post-merge audit passes."
    t=replace_once(t,old,new,"CURRENT active status line")
    p.write_text(t)

    # PLAN: preserve completed Step07 package, turn Step08 from Next into Active and add Step09 next.
    p=repo/"PLAN.md"; t=p.read_text()
    anchor=(
        "**Next package:**\n\n"
        "```text\n"
        "gate-2a-step08-langgraph-fresh-batch-and-continuation-v1.0.0\n"
        "```"
    )
    repl=(
        "**Active Step 2A.08 package:**\n\n"
        "```text\n"
        f"{PKG}\n"
        "```\n\n"
        "**Next package:**\n\n"
        "```text\n"
        f"{NEXT}\n"
        "```\n\n"
        "Step 2A.09 is locked until Step 2A.08 is verified, certified, committed, merged, local `main` is resynchronized, and the post-merge audit passes."
    )
    t=replace_once(t,anchor,repl,"PLAN package")
    p.write_text(t)

def complete(repo: Path, run_rel: str) -> None:
    req(run_rel.startswith("evidence/results/langgraph/langgraph-"), "Accepted run path is invalid")
    # AGENTS
    p=repo/"AGENTS.md"; t=p.read_text()
    t=replace_once(t,
        "**Step 2A.08:** active — fresh 12-target LangGraph batch and same-run continuation.",
        "**Step 2A.08:** complete.","AGENTS step")
    t=replace_once(t,f"**Active package:** `{PKG}`.",f"**Completed package:** `{PKG}`.","AGENTS package")
    t=replace_once(t,f"**Next package:** `{NEXT}` — locked.",f"**Next package:** `{NEXT}`.","AGENTS next")
    marker="Accepted Step 2A.07 construction evidence run:"
    req(marker in t,"AGENTS evidence anchor missing")
    t=t.replace(marker, f"Accepted Step 2A.08 batch evidence run: `{run_rel}`\n\n{marker}",1)
    old="Step 2A.08 is active. Do not generate or execute Step 2A.09 until Step 2A.08 is verified, certified, committed, merged, local `main` is resynchronized, and the post-merge audit passes."
    new="Do not generate or execute Step 2A.09 until Step 2A.08 is committed, merged, local `main` is resynchronized, and the post-merge audit passes."
    t=replace_once(t,old,new,"AGENTS lock complete")
    p.write_text(t)

    # README
    p=repo/"README.md"; t=p.read_text()
    t=replace_once(t,"- **Step 2A.08:** active — fresh 12-target LangGraph batch and same-run continuation.","- **Step 2A.08:** complete.","README step")
    t=replace_once(t,f"- **Active package:** `{PKG}`.",f"- **Completed package:** `{PKG}`.","README package")
    t=replace_once(t,f"- **Next package:** `{NEXT}` — locked.",f"- **Next package:** `{NEXT}`.","README next")
    marker="Accepted Step 2A.07 construction evidence run:"
    req(marker in t,"README evidence anchor missing")
    t=t.replace(marker, f"Accepted Step 2A.08 batch evidence run: `{run_rel}`\n{marker}",1)
    p.write_text(t)

    # CURRENT
    p=repo/"docs/CURRENT-STATUS.md"; t=p.read_text()
    t=replace_once(t,"- **Step 2A.08:** active — fresh 12-target LangGraph batch and same-run continuation.","- **Step 2A.08:** complete.","CURRENT step")
    t=replace_once(t,f"- **Active package:** `{PKG}`.",f"- **Completed package:** `{PKG}`.","CURRENT package")
    t=replace_once(t,f"- **Next package:** `{NEXT}` — locked.",f"- **Next package:** `{NEXT}`.","CURRENT next")
    marker="Accepted Step 2A.07 construction evidence run:"
    req(marker in t,"CURRENT evidence anchor missing")
    t=t.replace(marker, f"Accepted Step 2A.08 batch evidence run: `{run_rel}`\n{marker}",1)
    old="Step 2A.01 through Step 2A.07 are complete. Step 2A.08 is active. Step 2A.09 remains locked until Step 2A.08 is verified, certified, committed and merged, local `main` is resynchronized, and the post-merge audit passes."
    new="Step 2A.01 through Step 2A.08 are complete. Step 2A.09 is next but remains locked until Step 2A.08 is committed and merged, local `main` is resynchronized, and the post-merge audit passes."
    t=replace_once(t,old,new,"CURRENT complete status line")
    p.write_text(t)

    # PLAN
    p=repo/"PLAN.md"; t=p.read_text()
    t=replace_once(t,"**Active Step 2A.08 package:**","**Completed Step 2A.08 package:**","PLAN package")
    t=replace_once(t,"\n\nStep 2A.09 is locked until Step 2A.08 is verified, certified, committed, merged, local `main` is resynchronized, and the post-merge audit passes.","","PLAN lock complete")
    t=replace_once(t,"- [ ] Step 2A.08 — LangGraph fresh batch and continuation","- [x] Step 2A.08 — LangGraph fresh batch and continuation","PLAN checkbox")
    marker="Accepted Step 2A.07 construction evidence run:"
    req(marker in t,"PLAN evidence anchor missing")
    t=t.replace(marker, f"Accepted Step 2A.08 batch evidence run: `{run_rel}`\n\n{marker}",1)
    p.write_text(t)

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo",required=True)
    ap.add_argument("--state",choices=("active","complete"),required=True)
    ap.add_argument("--run-dir")
    a=ap.parse_args()
    repo=Path(a.repo).resolve()
    if a.state=="active":
        active(repo)
    else:
        req(bool(a.run_dir),"--run-dir required for complete state")
        complete(repo,a.run_dir)
    print(f"[PASS] Step 2A.08 lifecycle documents set to {a.state}.")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
