#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

EXPECTED_TESTS = [
    "INSPECT-DR-001",
    "FIXTURE-001",
    "VISION-DR-001",
    "TOOL-DR-001",
    "VISION-LG-001",
    "TOOL-LG-001",
    "VISION-CR-001",
    "TOOL-CR-001",
    "MUTATION-001",
]

SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9_-]{8,}"), "<redacted-openai-key>"),
    (re.compile(r"(?i)(authorization\s*:\s*(?:bearer|basic)\s+)\S+"), r"\1<redacted>"),
    (re.compile(r"(?i)(OPENAI_API_KEY\s*[=:]\s*)\S+"), r"\1<redacted>"),
    (re.compile(r"data:image/[A-Za-z0-9.+-]+;base64,[A-Za-z0-9+/=]+"), "<redacted-image-data-url>"),
]


def sanitize_text(text: str) -> str:
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def sanitize_file(path: Path) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    sanitized = sanitize_text(text)
    if sanitized != text:
        path.write_text(sanitized, encoding="utf-8")


def find_last_json(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    candidates: list[dict[str, Any]] = []
    for match in re.finditer(r"(?m)^\s*\{", text):
        try:
            value, _ = decoder.raw_decode(text[match.start() :].lstrip())
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            candidates.append(value)
    if not candidates:
        raise ValueError("No JSON object found in log")
    preferred = [value for value in candidates if "test_id" in value or "helper_version" in value]
    return preferred[-1] if preferred else candidates[-1]


def extract(log_path: Path, output_path: Path) -> None:
    sanitize_file(log_path)
    text = log_path.read_text(encoding="utf-8", errors="replace")
    value = find_last_json(text)
    serialized = sanitize_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialized, encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected object in {path}")
    return value


def mutation(before: Path, after: Path, output: Path) -> None:
    left = load_json(before)
    right = load_json(after)
    same = (
        left.get("source_sha256") == right.get("source_sha256")
        and left.get("suggestion_count") == right.get("suggestion_count")
        and left.get("revision_id") == right.get("revision_id")
        and left.get("image_sha256") == right.get("image_sha256")
    )
    result = {
        "test_id": "MUTATION-001",
        "status": "pass" if same else "fail",
        "source_unchanged": same,
        "before_source_sha256": left.get("source_sha256"),
        "after_source_sha256": right.get("source_sha256"),
        "before_suggestion_count": left.get("suggestion_count"),
        "after_suggestion_count": right.get("suggestion_count"),
        "before_revision_id": left.get("revision_id"),
        "after_revision_id": right.get("revision_id"),
        "image_sha256": right.get("image_sha256"),
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not same:
        raise SystemExit("Drupal source state changed during Step 16")


def parse_results(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 4:
            raise ValueError(f"Malformed results row: {line}")
        test_id, status, exit_code, evidence = parts
        rows.append(
            {
                "test_id": test_id,
                "status": status,
                "exit_code": int(exit_code),
                "evidence": evidence,
            }
        )
    return rows


def validate_shared_controls(run_dir: Path) -> dict[str, Any]:
    fixture = load_json(run_dir / "fixture.json")
    fixture_data = fixture.get("fixture", fixture)
    if not isinstance(fixture_data, dict):
        raise ValueError("fixture.json does not contain fixture metadata")
    expected_image = fixture_data.get("image_sha256")
    expected_context = fixture_data.get("context_sha256")
    expected_model: str | None = None
    mechanisms: dict[str, dict[str, Any]] = {}
    for test_id in ("VISION-DR-001", "VISION-LG-001", "VISION-CR-001"):
        value = load_json(run_dir / f"{test_id}.json")
        if value.get("status") != "pass":
            raise ValueError(f"{test_id} is not a pass")
        if value.get("image_sha256") != expected_image:
            raise ValueError(f"{test_id} did not receive the frozen image bytes")
        if value.get("context_sha256") != expected_context:
            raise ValueError(f"{test_id} did not receive the frozen page context")
        model_id = str(value.get("model_id", ""))
        if not model_id:
            raise ValueError(f"{test_id} did not record a model ID")
        if expected_model is None:
            expected_model = model_id
        elif model_id != expected_model:
            raise ValueError("Vision tests used different model IDs")
        output = value.get("output")
        if not isinstance(output, dict) or set(output) != {
            "image_purpose",
            "proposed_alt_text",
            "context_alignment",
        }:
            raise ValueError(f"{test_id} output does not match the Step 16 schema")
        alt = output.get("proposed_alt_text")
        if not isinstance(alt, str) or not alt.strip() or len(alt) > 250:
            raise ValueError(f"{test_id} produced invalid proposed_alt_text")
        mechanisms[test_id] = {
            "structured_output_mechanism": value.get("structured_output_mechanism"),
            "image_representation": value.get("image_representation"),
        }
    for test_id in ("TOOL-DR-001", "TOOL-LG-001", "TOOL-CR-001"):
        value = load_json(run_dir / f"{test_id}.json")
        if value.get("status") != "pass" or value.get("tool_call_detected") is not True:
            raise ValueError(f"{test_id} did not prove a tool call")
        if str(value.get("model_id", "")) != expected_model:
            raise ValueError(f"{test_id} used a different model")
        if test_id == "TOOL-DR-001" and value.get("tool_payload_present") is not True:
            raise ValueError("Drupal AI tool check did not retain a normalized tool payload")
        if test_id == "TOOL-LG-001":
            if value.get("tool_call_count") != 1 or value.get("tool_result") != "140" or value.get("tool_function_executed") is not True:
                raise ValueError("LangChain tool check did not execute the frozen tool exactly once")
        if test_id == "TOOL-CR-001":
            if value.get("tool_call_count") != 1 or value.get("tool_result") != "140" or value.get("tool_function_executed") is not True:
                raise ValueError("CrewAI tool check did not execute the frozen tool exactly once")
        mechanisms[test_id] = {"tool_mechanism": value.get("tool_mechanism")}
    return {
        "model_id": expected_model,
        "image_sha256": expected_image,
        "context_sha256": expected_context,
        "image_representation": "inline PNG bytes; Python wrappers use Base64 data URL and Drupal AI uses ImageFile over the identical bytes",
        "image_detail": "auto or provider default equivalent",
        "mechanisms": mechanisms,
    }


def secret_scan(run_dir: Path) -> None:
    for path in run_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            raise ValueError(f"Raw image should not be retained in evidence: {path}")
        text = path.read_text(encoding="utf-8", errors="replace")
        if "data:image/" in text and ";base64," in text:
            raise ValueError(f"Base64 image value retained in evidence: {path}")
        for pattern, _ in SECRET_PATTERNS[:3]:
            if pattern.search(text):
                raise ValueError(f"Potential unredacted credential in evidence: {path}")


def build_summary(run_dir: Path, run_id: str, started: str, finished: str) -> None:
    results = parse_results(run_dir / "results.tsv")
    by_id = {row["test_id"]: row for row in results}
    missing = [test for test in EXPECTED_TESTS if test not in by_id]
    extras = sorted(set(by_id) - set(EXPECTED_TESTS))
    passed = sum(1 for test in EXPECTED_TESTS if by_id.get(test, {}).get("status") == "pass")
    controls: dict[str, Any] = {}
    control_error: str | None = None
    if passed == len(EXPECTED_TESTS) and not missing and not extras:
        try:
            controls = validate_shared_controls(run_dir)
            secret_scan(run_dir)
        except Exception as exc:  # noqa: BLE001
            control_error = str(exc)
    status = "pass" if passed == len(EXPECTED_TESTS) and not missing and not extras and not control_error else "fail"
    summary = {
        "run_id": run_id,
        "mode": "direct",
        "started_at_utc": started,
        "finished_at_utc": finished,
        "status": status,
        "total": len(EXPECTED_TESTS),
        "passed": passed,
        "failed": len(EXPECTED_TESTS) - passed,
        "missing_tests": missing,
        "unexpected_tests": extras,
        "control_error": control_error,
        "controls": controls,
        "tests": [by_id[test] for test in EXPECTED_TESTS if test in by_id],
        "claims": {
            "proves": [
                "candidate model received the same synthetic image bytes and page context through all three pinned pathways",
                "all three pathways produced schema-valid structured output",
                "all three pathways exposed a harmless tool-call pathway",
                "the Drupal source Article and suggestion count were unchanged",
            ],
            "does_not_prove": [
                "alt-text quality",
                "framework superiority",
                "production readiness",
                "Step 17 target discovery",
            ],
        },
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Phase 0 Step 16 capability-spike summary",
        "",
        f"- Run ID: `{run_id}`",
        f"- Started: `{started}`",
        f"- Finished: `{finished}`",
        f"- Result: **{passed}/{len(EXPECTED_TESTS)} passed**",
        f"- Mode: direct image-plus-page-context",
        "",
        "| Test ID | Result | Evidence |",
        "|---|---:|---|",
    ]
    for test in EXPECTED_TESTS:
        row = by_id.get(test, {"status": "missing", "evidence": "—"})
        lines.append(f"| `{test}` | {row['status']} | `{row['evidence']}` |")
    lines.extend(
        [
            "",
            "This is a capability spike. It does not rank frameworks or evaluate production alt-text quality.",
        ]
    )
    if control_error:
        lines.extend(["", f"Control validation error: `{control_error}`"])
    (run_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if status != "pass":
        raise SystemExit("Step 16 direct capability spike did not pass all required controls")


def hash_file(path: Path) -> None:
    print(hashlib.sha256(path.read_bytes()).hexdigest())


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("sanitize")
    p.add_argument("path", type=Path)
    p = sub.add_parser("extract")
    p.add_argument("log", type=Path)
    p.add_argument("output", type=Path)
    p = sub.add_parser("mutation")
    p.add_argument("before", type=Path)
    p.add_argument("after", type=Path)
    p.add_argument("output", type=Path)
    p = sub.add_parser("summary")
    p.add_argument("run_dir", type=Path)
    p.add_argument("run_id")
    p.add_argument("started")
    p.add_argument("finished")
    p = sub.add_parser("hash")
    p.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.command == "sanitize":
        sanitize_file(args.path)
    elif args.command == "extract":
        extract(args.log, args.output)
    elif args.command == "mutation":
        mutation(args.before, args.after, args.output)
    elif args.command == "summary":
        build_summary(args.run_dir, args.run_id, args.started, args.finished)
    elif args.command == "hash":
        hash_file(args.path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
