#!/usr/bin/env python3
"""Validate retained Gate 0.5 success envelopes against the frozen schemas."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path
from typing import Any

import jsonschema
from referencing import Registry, Resource


EXPECTED_JSONSCHEMA_VERSION = "4.26.0"
SCHEMA_NAMES = (
    "target.schema.json",
    "image-context.schema.json",
    "recommendation.schema.json",
    "tool-result.schema.json",
)
ENVELOPE_FILES = (
    "find-response.json",
    "context-sanitized.json",
    "submit-response.json",
    "submit-replay-response.json",
    "status-uuid.json",
    "status-nid.json",
    "status-repeat.json",
)
EXPECTED_TOOLS = {
    "find-response.json": "find_images_needing_review",
    "context-sanitized.json": "get_image_context",
    "submit-response.json": "submit_recommendation",
    "submit-replay-response.json": "submit_recommendation",
    "status-uuid.json": "get_recommendation_status",
    "status-nid.json": "get_recommendation_status",
    "status-repeat.json": "get_recommendation_status",
}


class RegressionError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegressionError(f"Missing retained schema evidence: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RegressionError(f"Invalid retained JSON: {path.name}") from exc


def build_validators(
    repo: Path,
    tool_result_schema: Path | None,
) -> tuple[jsonschema.Draft202012Validator, jsonschema.Draft202012Validator]:
    version = importlib.metadata.version("jsonschema")
    if version != EXPECTED_JSONSCHEMA_VERSION:
        raise RegressionError(
            f"Expected locked jsonschema {EXPECTED_JSONSCHEMA_VERSION}; found {version}."
        )

    schemas: dict[str, dict[str, Any]] = {}
    resources: list[tuple[str, Resource[Any]]] = []
    for name in SCHEMA_NAMES:
        path = (
            tool_result_schema
            if name == "tool-result.schema.json" and tool_result_schema is not None
            else repo / "shared/schemas" / name
        )
        schema = load_json(path)
        if not isinstance(schema, dict) or schema.get("$id") != name:
            raise RegressionError(f"Invalid schema identity: {name}")
        schemas[name] = schema
        resources.append((name, Resource.from_contents(schema)))

    registry = Registry().with_resources(resources)
    format_checker = jsonschema.FormatChecker()
    tool_validator = jsonschema.Draft202012Validator(
        schemas["tool-result.schema.json"],
        registry=registry,
        format_checker=format_checker,
    )
    context_validator = jsonschema.Draft202012Validator(
        schemas["image-context.schema.json"],
        registry=registry,
        format_checker=format_checker,
    )
    return tool_validator, context_validator


def validate_instance(
    validator: jsonschema.Draft202012Validator,
    value: Any,
    label: str,
) -> None:
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.path))
    if errors:
        path = ".".join(str(part) for part in errors[0].absolute_path) or "<root>"
        raise RegressionError(
            f"Schema regression failed for {label} at {path}: {errors[0].validator}."
        )


def passing_run_dirs(evidence_root: Path) -> list[Path]:
    result: list[Path] = []
    for run_dir in sorted(evidence_root.glob("gate05-step05-*")):
        summary_path = run_dir / "summary.json"
        if not summary_path.is_file():
            continue
        summary = load_json(summary_path)
        if isinstance(summary, dict) and summary.get("status") == "pass":
            result.append(run_dir)
    if not result:
        raise RegressionError("No passing retained Step 05 runs were found.")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--require-run", action="append", default=[])
    parser.add_argument("--tool-result-schema", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    evidence_root = args.evidence_root.resolve()
    tool_result_schema = (
        args.tool_result_schema.resolve()
        if args.tool_result_schema is not None
        else None
    )
    tool_validator, context_validator = build_validators(
        repo,
        tool_result_schema,
    )
    run_dirs = passing_run_dirs(evidence_root)
    run_names = {run_dir.name for run_dir in run_dirs}
    missing = sorted(set(args.require_run) - run_names)
    if missing:
        raise RegressionError(
            "Required passing Step 05 runs are missing: " + ", ".join(missing)
        )

    validated_envelopes = 0
    direct_context_envelopes = 0
    for run_dir in run_dirs:
        observed_tools: set[str] = set()
        for filename in ENVELOPE_FILES:
            envelope = load_json(run_dir / filename)
            if not isinstance(envelope, dict):
                raise RegressionError(f"Malformed retained envelope: {run_dir.name}/{filename}")
            expected_tool = EXPECTED_TOOLS[filename]
            if envelope.get("tool_name") != expected_tool or envelope.get("ok") is not True:
                raise RegressionError(
                    f"Unexpected retained success envelope: {run_dir.name}/{filename}"
                )
            validate_instance(
                tool_validator,
                envelope,
                f"{run_dir.name}/{filename}",
            )
            observed_tools.add(expected_tool)
            validated_envelopes += 1

            if expected_tool == "get_image_context":
                data = envelope.get("data")
                if not isinstance(data, dict) or "context" in data:
                    raise RegressionError(
                        f"get_image_context is not direct-data in {run_dir.name}."
                    )
                validate_instance(
                    context_validator,
                    data,
                    f"{run_dir.name}/{filename}:data",
                )
                direct_context_envelopes += 1

        if observed_tools != set(EXPECTED_TOOLS.values()):
            raise RegressionError(
                f"Not all four operations were schema-validated for {run_dir.name}."
            )

    print(
        json.dumps(
            {
                "status": "pass",
                "jsonschema_version": EXPECTED_JSONSCHEMA_VERSION,
                "draft": "2020-12",
                "passing_runs_validated": [run_dir.name for run_dir in run_dirs],
                "success_envelopes_validated": validated_envelopes,
                "all_four_operations_validated_per_run": True,
                "direct_get_image_context_envelopes_validated": direct_context_envelopes,
                "nested_data_context_observed": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RegressionError as exc:
        print(f"[ERROR] {exc}")
        raise SystemExit(1) from exc
