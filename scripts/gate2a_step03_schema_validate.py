#!/usr/bin/env python3
"""Validate one JSON value from stdin against a frozen shared Draft 2020-12 schema."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema-dir", required=True)
    parser.add_argument("--schema", required=True)
    args = parser.parse_args()

    schema_dir = Path(args.schema_dir).resolve()
    root_path = schema_dir / args.schema
    instance = json.load(sys.stdin)
    root = json.loads(root_path.read_text(encoding="utf-8"))

    registry = Registry()
    for path in sorted(schema_dir.glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        resource = Resource.from_contents(value)
        identifiers = {path.name, path.resolve().as_uri()}
        schema_id = value.get("$id")
        if isinstance(schema_id, str) and schema_id:
            identifiers.add(schema_id)
        for identifier in identifiers:
            registry = registry.with_resource(identifier, resource)

    validator = Draft202012Validator(
        root,
        registry=registry,
        format_checker=FormatChecker(),
    )
    validator.validate(instance)
    print(json.dumps({"status": "pass", "schema": args.schema}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
