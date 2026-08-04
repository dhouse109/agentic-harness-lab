#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

EXPECTED_TESTS = {
    "PY-LG-001", "PY-LG-002", "LG-GRAPH-001", "LG-SQLITE-001", "LG-SQLITE-002",
    "LG-MODEL-001", "PY-CR-001", "PY-CR-002", "CR-FLOW-001", "CR-MODEL-001",
}
EXPECTED_DEPS = {
    "langchain": {"langchain", "langchain-openai", "langgraph", "langgraph-checkpoint-sqlite", "requests", "python-dotenv"},
    "crewai": {"crewai", "crewai-tools", "requests", "python-dotenv"},
}


def fail(message: str) -> None:
    print(f"[ERROR] {message}")
    raise SystemExit(1)


def ok(message: str) -> None:
    print(f"[OK] {message}")


def parse_dependencies(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"dependencies\s*=\s*\[(.*?)\]", text, re.S)
    if not match:
        fail(f"No dependency array found in {path}")
    return set(re.findall(r'"([A-Za-z0-9_.-]+)(?:[^"\n]*)"', match.group(1)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    for project in ("langchain", "crewai"):
        project_dir = root / project
        if (project_dir / ".python-version").read_text(encoding="utf-8").strip() != "3.12":
            fail(f"{project}/.python-version is not 3.12")
        if not (project_dir / "uv.lock").is_file() or (project_dir / "uv.lock").stat().st_size == 0:
            fail(f"Missing nonempty {project}/uv.lock")
        deps = parse_dependencies(project_dir / "pyproject.toml")
        if not EXPECTED_DEPS[project].issubset(deps):
            fail(f"{project}/pyproject.toml is missing dependencies: {sorted(EXPECTED_DEPS[project] - deps)}")
    ok("Separate Python 3.12 uv projects and lockfiles are present.")

    latest_file = root / "evidence/logs/preflight/STEP15-LATEST.txt"
    if not latest_file.is_file():
        fail("Missing STEP15-LATEST.txt; run the Step 15 preflight")
    run_rel = latest_file.read_text(encoding="utf-8").strip()
    run_dir = root / run_rel
    summary_path = run_dir / "summary.json"
    if not summary_path.is_file():
        fail(f"Missing Step 15 summary: {summary_path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    tests = {row["test_id"] for row in summary.get("tests", []) if row.get("status") == "pass"}
    if summary.get("status") != "pass" or summary.get("total") != 10 or summary.get("passed") != 10:
        fail("Latest Step 15 run is not a 10/10 pass")
    if tests != EXPECTED_TESTS:
        fail(f"Unexpected passing test set: {sorted(tests)}")
    ok("Latest sanitized Step 15 evidence contains all 10 passing tests.")

    secret_patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
        re.compile(r"(?i)authorization\s*:\s*(?:bearer|basic)\s+(?!<redacted>)\S+"),
        re.compile(r"(?i)OPENAI_API_KEY\s*[=:]\s*(?!<redacted>)\S+"),
    ]
    for path in run_dir.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in secret_patterns:
            if pattern.search(text):
                fail(f"Potential unredacted secret in Step 15 evidence: {path}")
    ok("Latest Step 15 evidence contains no recognized unredacted credential pattern.")

    gitignore = (root / ".gitignore").read_text(encoding="utf-8")
    for required in ("/langchain/.venv/", "/langchain/.preflight-state/", "/crewai/.venv/", "/crewai/.preflight-state/"):
        if required not in gitignore:
            fail(f".gitignore is missing Step 15 runtime exclusion: {required}")
    ok("Step 15 virtual environments and SQLite runtime state are ignored by Git.")

    plan = (root / "PLAN.md").read_text(encoding="utf-8")
    complete = "- [x] Step 15 separate LangChain/LangGraph and CrewAI environments pass preflight." in plan
    if complete:
        readme = (root / "README.md").read_text(encoding="utf-8")
        versions = (root / "VERSIONS.md").read_text(encoding="utf-8")
        for required in ("Steps 13–15 are complete", "Step 16"):
            if required not in readme:
                fail(f"README.md missing finalized Step 15 text: {required}")
        for required in ("| LangChain |", "| LangGraph |", "| LangGraph SQLite checkpointer |", "| CrewAI |", "| CrewAI Tools |"):
            if required not in versions or f"{required} TODO" in versions:
                fail(f"VERSIONS.md missing finalized value for {required}")
        ok("Step 15 is finalized in PLAN.md, README.md, and VERSIONS.md.")
        print("[OK] Step 15 audit passed in finalized state.")
    else:
        print("[OK] Step 15 audit passed in ready-to-finalize state.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
