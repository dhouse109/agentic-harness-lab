#!/usr/bin/env python3
from __future__ import annotations
import argparse, re
from pathlib import Path

STEP06_NEXT="gate-2a-step06-langgraph-human-interrupt-and-review-resume-v1.0.0"
STEP06_PREVIOUS="gate-2a-step06-langgraph-human-interrupt-and-review-resume-v1.0.7"
STEP06_PACKAGE="gate-2a-step06-langgraph-human-interrupt-and-review-resume-v1.0.8"
STEP07="gate-2a-step07-langgraph-batch-runner-v1.0.0"
ACTIVE_DESC="LangGraph persisted interrupt + Drupal human-review resume proof."


def once(text:str, old:str, new:str, label:str)->str:
    count=text.count(old)
    if count!=1:
        raise SystemExit(f"[ERROR] {label}: expected one lifecycle anchor, found {count}: {old!r}")
    return text.replace(old,new,1)


def regex_once(text:str, pattern:str, new:str, label:str)->str:
    out,count=re.subn(pattern,new,text,count=1,flags=re.MULTILINE)
    if count!=1:
        raise SystemExit(f"[ERROR] {label}: expected one regex lifecycle anchor, found {count}")
    return out


def paths(repo:Path):
    return {name:(repo/name) for name in ("AGENTS.md","PLAN.md","README.md","docs/CURRENT-STATUS.md")}


def activate(texts:dict[str,str])->dict[str,str]:
    # Support both a fresh install from the originally planned v1.0.0 marker and
    # the v1.0.7 active state repaired in-place by v1.0.8.
    if f"**Next package:** `{STEP06_NEXT}`." in texts["AGENTS.md"]:
        texts["AGENTS.md"]=once(
            texts["AGENTS.md"],
            f"**Next package:** `{STEP06_NEXT}`.",
            f"**Step 2A.06:** active — {ACTIVE_DESC}\n\n**Active package:** `{STEP06_PACKAGE}`.",
            "AGENTS fresh active package",
        )
        texts["AGENTS.md"]=once(
            texts["AGENTS.md"],
            "Do not generate Step 2A.06 until Step 2A.05 is passing, committed, merged, local `main` is resynchronized, and the post-merge audit passes.",
            "Do not generate Step 2A.07 until Step 2A.06 is passing, committed, merged, local `main` is resynchronized, and the post-merge audit passes.",
            "AGENTS fresh next-step guard",
        )
        texts["PLAN.md"]=once(
            texts["PLAN.md"],
            f"**Next package:**\n\n```text\n{STEP06_NEXT}\n```",
            f"**Active package:**\n\n```text\n{STEP06_PACKAGE}\n```",
            "PLAN fresh active package",
        )
        texts["README.md"]=once(
            texts["README.md"],
            f"- **Next package:** `{STEP06_NEXT}`.",
            f"- **Step 2A.06:** active — {ACTIVE_DESC}\n- **Active package:** `{STEP06_PACKAGE}`.",
            "README fresh active package",
        )
        texts["docs/CURRENT-STATUS.md"]=once(
            texts["docs/CURRENT-STATUS.md"],
            f"- **Next package:** `{STEP06_NEXT}`.",
            f"- **Step 2A.06:** active — {ACTIVE_DESC}\n- **Active package:** `{STEP06_PACKAGE}`.",
            "CURRENT fresh active package",
        )
    elif f"**Active package:** `{STEP06_PREVIOUS}`." in texts["AGENTS.md"]:
        texts["AGENTS.md"]=once(texts["AGENTS.md"],f"**Active package:** `{STEP06_PREVIOUS}`.",f"**Active package:** `{STEP06_PACKAGE}`.","AGENTS repair package")
        texts["PLAN.md"]=once(texts["PLAN.md"],f"```text\n{STEP06_PREVIOUS}\n```",f"```text\n{STEP06_PACKAGE}\n```","PLAN repair package")
        texts["README.md"]=once(texts["README.md"],f"- **Active package:** `{STEP06_PREVIOUS}`.",f"- **Active package:** `{STEP06_PACKAGE}`.","README repair package")
        texts["docs/CURRENT-STATUS.md"]=once(texts["docs/CURRENT-STATUS.md"],f"- **Active package:** `{STEP06_PREVIOUS}`.",f"- **Active package:** `{STEP06_PACKAGE}`.","CURRENT repair package")
    elif f"**Active package:** `{STEP06_PACKAGE}`." not in texts["AGENTS.md"]:
        raise SystemExit("[ERROR] Step 2A.06 active lifecycle is neither fresh-install nor v1.0.7 repair state")

    # Robustly replace the stale fresh-session sentence. Tolerate the historic
    # missing space in "2A.01through" while normalizing it in the replacement.
    current=texts["docs/CURRENT-STATUS.md"]
    if "Step 2A.06 is next but remains locked" in current:
        current=regex_once(
            current,
            r"Step 2A\.01\s*through Step 2A\.05 are complete\. Step 2A\.06 is next but remains locked until Step 2A\.05 is committed and merged, local `main` is resynchronized, and the post-merge audit passes\.",
            "Step 2A.01 through Step 2A.05 are complete. Step 2A.06 is active. Step 2A.07 remains locked until Step 2A.06 is committed and merged, local `main` is resynchronized, and the post-merge audit passes.",
            "CURRENT active fresh-session marker",
        )
    elif "Step 2A.06 is active. Step 2A.07 remains locked" not in current:
        raise SystemExit("[ERROR] CURRENT active fresh-session lifecycle marker is unavailable")
    texts["docs/CURRENT-STATUS.md"]=current
    return texts


def complete(texts:dict[str,str], run:str)->dict[str,str]:
    texts["AGENTS.md"]=once(texts["AGENTS.md"],f"**Step 2A.06:** active — {ACTIVE_DESC}\n\n**Active package:** `{STEP06_PACKAGE}`.",f"**Step 2A.06:** complete.\n\n**Completed package:** `{STEP06_PACKAGE}`.\n\n**Next package:** `{STEP07}`.\n\nAccepted Step 2A.06 evidence run: `{run}`","AGENTS complete")
    texts["PLAN.md"]=once(texts["PLAN.md"],f"**Active package:**\n\n```text\n{STEP06_PACKAGE}\n```",f"**Completed Step 2A.06 package:**\n\n```text\n{STEP06_PACKAGE}\n```\n\n**Next package:**\n\n```text\n{STEP07}\n```\n\nAccepted Step 2A.06 evidence run: `{run}`","PLAN complete package")
    texts["PLAN.md"]=once(texts["PLAN.md"],"- [ ] Step 2A.06 — LangGraph human interrupt and review resume","- [x] Step 2A.06 — LangGraph human interrupt and review resume","PLAN checkbox")
    texts["README.md"]=once(texts["README.md"],f"- **Step 2A.06:** active — {ACTIVE_DESC}\n- **Active package:** `{STEP06_PACKAGE}`.",f"- **Step 2A.06:** complete.\n- **Completed package:** `{STEP06_PACKAGE}`.\n- **Next package:** `{STEP07}`.\nAccepted Step 2A.06 evidence run: `{run}`","README complete")
    texts["docs/CURRENT-STATUS.md"]=once(texts["docs/CURRENT-STATUS.md"],f"- **Step 2A.06:** active — {ACTIVE_DESC}\n- **Active package:** `{STEP06_PACKAGE}`.",f"- **Step 2A.06:** complete.\n- **Completed package:** `{STEP06_PACKAGE}`.\n- **Next package:** `{STEP07}`.\nAccepted Step 2A.06 evidence run: `{run}`","CURRENT complete")
    texts["docs/CURRENT-STATUS.md"]=regex_once(
        texts["docs/CURRENT-STATUS.md"],
        r"Step 2A\.01\s*through Step 2A\.05 are complete\. Step 2A\.06 is active\. Step 2A\.07 remains locked until Step 2A\.06 is committed and merged, local `main` is resynchronized, and the post-merge audit passes\.",
        "Step 2A.01 through Step 2A.06 are complete. Step 2A.07 is next but remains locked until Step 2A.06 is committed and merged, local `main` is resynchronized, and the post-merge audit passes.",
        "CURRENT complete fresh-session marker",
    )
    return texts


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--repo",required=True); ap.add_argument("--state",choices=("active","complete"),required=True); ap.add_argument("--run-dir")
    a=ap.parse_args(); r=Path(a.repo).resolve(); ps=paths(r); texts={n:p.read_text(encoding="utf-8") for n,p in ps.items()}
    if a.state=="active":
        texts=activate(texts)
    else:
        if not a.run_dir: raise SystemExit("[ERROR] --run-dir required for complete state")
        texts=complete(texts,a.run_dir)
    for n,p in ps.items(): p.write_text(texts[n],encoding="utf-8")
    print(f"[PASS] Step 2A.06 lifecycle documents set to {a.state}.")
    return 0
if __name__=="__main__": raise SystemExit(main())
