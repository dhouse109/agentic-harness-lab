#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(f"[ERROR] {message}")


def replace_exact(text: str, old: str, new: str, path: Path) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"Expected exactly one matching block in {path}; found {count}")
    return text.replace(old, new)


def package_versions(root: Path) -> tuple[dict, dict]:
    import subprocess

    def run(project: str) -> dict:
        proc = subprocess.run(
            ["uv", "run", "--locked", "python", str(root / "scripts/step15_versions.py"), project],
            cwd=root / project,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            fail(f"Could not read {project} versions: {proc.stderr.strip()}")
        try:
            return json.loads(proc.stdout.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError) as exc:
            fail(f"Invalid {project} version output: {exc}")
    return run("langchain"), run("crewai")


def update_versions(root: Path, evidence_rel: str, model: str, uv_version: str) -> None:
    path = root / "VERSIONS.md"
    text = path.read_text(encoding="utf-8")
    lg, cr = package_versions(root)
    rows = {
        "Python": f"3.12 ({lg['python']} LangChain; {cr['python']} CrewAI)",
        "uv": uv_version,
        "LangChain": lg["packages"]["langchain"],
        "LangGraph": lg["packages"]["langgraph"],
        "LangGraph SQLite checkpointer": lg["packages"]["langgraph-checkpoint-sqlite"],
        "CrewAI": cr["packages"]["crewai"],
    }
    lines = text.splitlines()
    updated: list[str] = []
    seen: set[str] = set()
    crewai_index: int | None = None
    for line in lines:
        matched = False
        for component, value in rows.items():
            if line.startswith(f"| {component} |"):
                frozen = "yes"
                note = "Separate Python 3.12 uv environments" if component == "Python" else "Resolved by Step 15 lockfile"
                updated.append(f"| {component} | {value} | `{evidence_rel}` / project `uv.lock` | {frozen} | {note} |")
                seen.add(component)
                matched = True
                if component == "CrewAI":
                    crewai_index = len(updated)
                break
        if not matched and line.startswith("| Candidate/frozen model |"):
            updated.append(f"| Candidate/frozen model | {model} — candidate only | `{evidence_rel}` | no | Text-only pings passed; freeze only after Step 16 |")
            matched = True
        if not matched:
            updated.append(line)
    missing = set(rows) - seen
    if missing:
        fail(f"VERSIONS.md is missing expected rows: {sorted(missing)}")
    if not any(line.startswith("| CrewAI Tools |") for line in updated):
        if crewai_index is None:
            fail("Could not place CrewAI Tools row")
        updated.insert(
            crewai_index,
            f"| CrewAI Tools | {cr['packages']['crewai-tools']} | `{evidence_rel}` / `crewai/uv.lock` | yes | Resolved by Step 15 lockfile |",
        )
    path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def update_plan(root: Path) -> None:
    path = root / "PLAN.md"
    text = path.read_text(encoding="utf-8")
    old = "- [ ] Step 15 separate LangChain/LangGraph and CrewAI environments pass preflight."
    new = "- [x] Step 15 separate LangChain/LangGraph and CrewAI environments pass preflight."
    path.write_text(replace_exact(text, old, new, path), encoding="utf-8")


def update_readme(root: Path) -> None:
    path = root / "README.md"
    text = path.read_text(encoding="utf-8")
    old = """Phase 0 Steps 13 and 14 are complete. The experiment contract is frozen at version 1.0, while the
exact model and image representation remain the explicitly controlled Step 16 decision. The next
step is separate LangChain/LangGraph and CrewAI environment preflight.

Verify the freeze with:

```bash
bash scripts/run-phase0-step14.sh audit
```
"""
    new = """Phase 0 Steps 13–15 are complete. The experiment contract is frozen at version 1.0, and
separate Python 3.12 environments now pass the LangGraph, CrewAI, model-connectivity, and SQLite
restart preflights. The candidate model is not frozen. Step 16 must still prove image-plus-page-
context capability and record the final model and representation decision.

Verify Step 15 with:

```bash
bash scripts/run-phase0-step15.sh audit
```
"""
    path.write_text(replace_exact(text, old, new, path), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--evidence-rel", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--uv-version", required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    args.backup_dir.mkdir(parents=True, exist_ok=True)
    for rel in ("README.md", "PLAN.md", "VERSIONS.md"):
        shutil.copy2(root / rel, args.backup_dir / rel)
    update_versions(root, args.evidence_rel, args.model, args.uv_version)
    update_plan(root)
    update_readme(root)
    print("[OK] Updated VERSIONS.md, PLAN.md, and README.md for completed Step 15.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
