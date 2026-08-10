#!/usr/bin/env python3
"""Validate one JSON instance against a repository schema using Draft 2020-12.

This helper intentionally runs in the repository's schema/audit Python, separate
from the frozen LangGraph runtime Python. It reads the instance from stdin and
prints nothing on success.
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore", category=DeprecationWarning)
from jsonschema import Draft202012Validator, FormatChecker, RefResolver


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--schema", required=True)
    ap.add_argument("--label", default="instance")
    args=ap.parse_args()
    repo=Path(args.repo).resolve()
    schema_dir=repo/"shared/schemas"
    schema_path=schema_dir/args.schema
    if not schema_path.is_file():
        raise SystemExit(f"[ERROR] schema missing: {args.schema}")
    schema=load(schema_path)
    store: dict[str, Any]={}
    for path in schema_dir.glob("*.schema.json"):
        value=load(path)
        store[path.name]=value
        store[path.as_uri()]=value
        if isinstance(value.get("$id"), str):
            store[value["$id"]]=value
    resolver=RefResolver(base_uri=schema_path.as_uri(), referrer=schema, store=store)
    validator=Draft202012Validator(schema, resolver=resolver, format_checker=FormatChecker())
    value=json.load(sys.stdin)
    errors=sorted(validator.iter_errors(value), key=lambda err: list(err.path))
    if errors:
        err=errors[0]
        loc="/".join(str(x) for x in err.path) or "<root>"
        raise SystemExit(f"[ERROR] {args.label} failed {args.schema} at {loc}: {err.message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
