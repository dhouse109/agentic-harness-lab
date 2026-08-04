#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9_-]{12,}"), "<redacted-openai-key>"),
    (re.compile(r"(?i)(authorization\s*:\s*(?:bearer|basic)\s+)[^\s]+"), r"\1<redacted>"),
    (re.compile(r"(?i)(OPENAI_API_KEY\s*[=:]\s*)[^\s]+"), r"\1<redacted>"),
    (re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)['\"]?[^\s'\"]+"), r"\1<redacted>"),
]


def sanitize_text(text: str) -> str:
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def sanitize_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    path.write_text(sanitize_text(text), encoding="utf-8")


def parse_last_json(path: Path) -> dict[str, Any]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return {}


def build_summary(run_dir: Path, run_id: str, model: str, started: str, finished: str) -> int:
    result_file = run_dir / "results.tsv"
    rows: list[dict[str, str]] = []
    for line in result_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        test_id, status, exit_code, log_name = line.split("\t")
        rows.append({
            "test_id": test_id,
            "status": status,
            "exit_code": exit_code,
            "log": log_name,
        })
    passed = sum(row["status"] == "pass" for row in rows)
    failed = len(rows) - passed
    summary = {
        "candidate_model": model,
        "finished_at_utc": finished,
        "passed": passed,
        "failed": failed,
        "run_id": run_id,
        "started_at_utc": started,
        "status": "pass" if failed == 0 and len(rows) == 10 else "fail",
        "tests": rows,
        "total": len(rows),
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown = [
        "# Phase 0 Step 15 preflight summary",
        "",
        f"- Run ID: `{run_id}`",
        f"- Candidate model: `{model}` (not frozen)",
        f"- Started: `{started}`",
        f"- Finished: `{finished}`",
        f"- Result: **{passed}/{len(rows)} passed**",
        "",
        "| Test ID | Result | Evidence |",
        "|---|---:|---|",
    ]
    for row in rows:
        markdown.append(f"| `{row['test_id']}` | {row['status']} | `{row['log']}` |")
    markdown.extend([
        "",
        "This is environment verification only. It does not freeze the model, prove image capability, or implement agent behavior.",
        "",
    ])
    (run_dir / "summary.md").write_text("\n".join(markdown), encoding="utf-8")
    return 0 if summary["status"] == "pass" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sanitize = sub.add_parser("sanitize")
    sanitize.add_argument("files", nargs="+", type=Path)
    summary = sub.add_parser("summary")
    summary.add_argument("run_dir", type=Path)
    summary.add_argument("--run-id", required=True)
    summary.add_argument("--model", required=True)
    summary.add_argument("--started", required=True)
    summary.add_argument("--finished", required=True)
    args = parser.parse_args()
    if args.command == "sanitize":
        for path in args.files:
            sanitize_file(path)
        return 0
    return build_summary(args.run_dir, args.run_id, args.model, args.started, args.finished)


if __name__ == "__main__":
    raise SystemExit(main())
