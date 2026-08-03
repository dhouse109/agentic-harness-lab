#!/usr/bin/env python3
"""Helpers for Phase 0 Step 11 permission evidence.

This file never reads account passwords. Authentication stays in temporary curl
config files owned by the shell runner.
"""

from __future__ import annotations

import argparse
import copy
import html
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
SENSITIVE_KEYS = {
    "password",
    "pass",
    "authorization",
    "cookie",
    "set-cookie",
    "csrf_token",
    "logout_token",
    "access_token",
    "refresh_token",
    "client_secret",
    "api_key",
    "openai_api_key",
    "mail",
    "email",
}


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, value: Any) -> None:
    Path(path).write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def manifest_targets(manifest: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if manifest.get("target_count") != 12:
        raise ValueError(f"Expected target_count=12; found {manifest.get('target_count')!r}")
    targets = manifest.get("targets")
    if not isinstance(targets, list) or len(targets) != 12:
        raise ValueError("Manifest does not contain exactly 12 targets")

    by_number = {int(item["article_number"]): item for item in targets}
    for number in (1, 2):
        if number not in by_number:
            raise ValueError(f"Manifest is missing Article {number:02d}")
    return by_number[1], by_number[2]


def cmd_shell_targets(args: argparse.Namespace) -> int:
    target1, target2 = manifest_targets(load_json(args.manifest))
    values = {
        "TARGET1_NODE_UUID": target1["node_uuid"],
        "TARGET1_REVISION_ID": str(target1["node_revision_id"]),
        "TARGET1_FIELD_NAME": target1["field_name"],
        "TARGET1_DELTA": str(target1["delta"]),
        "TARGET1_FILE_UUID": target1["file_uuid"],
        "TARGET1_FILE_URI": target1["file_uri"],
        "TARGET2_FILE_UUID": target2["file_uuid"],
    }
    for key, value in values.items():
        print(f"{key}={shlex.quote(str(value))}")
    return 0


def relationship_items(document: dict[str, Any]) -> list[dict[str, Any]]:
    data = (
        document.get("data", {})
        .get("relationships", {})
        .get("field_image", {})
        .get("data")
    )
    if isinstance(data, dict):
        return [copy.deepcopy(data)]
    if isinstance(data, list):
        return copy.deepcopy(data)
    raise ValueError("JSON:API response has no field_image relationship data")


def cmd_build_base_payloads(args: argparse.Namespace) -> int:
    manifest = load_json(args.manifest)
    target1, target2 = manifest_targets(manifest)
    context = load_json(args.context)

    data = context.get("data")
    if not isinstance(data, dict) or data.get("id") != target1["node_uuid"]:
        raise ValueError("Context response does not describe the expected Article 01 UUID")

    items = relationship_items(context)
    delta = int(target1["delta"])
    if delta >= len(items):
        raise ValueError("Target delta is outside the field_image relationship")
    if items[delta].get("id") != target1["file_uuid"]:
        raise ValueError("Target file UUID does not match the Article relationship")

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    suggestion = {
        "data": {
            "type": "node--alt_text_suggestion",
            "attributes": {
                "title": f"Step 11 permission probe {args.run_id}",
                "field_target_revision": int(target1["node_revision_id"]),
                "field_target_field": target1["field_name"],
                "field_target_delta": int(target1["delta"]),
                "field_proposed_alt": "Large numeral 01 identifying the emergency preparedness checklist demonstration image.",
                "field_review_status": "pending",
                "field_source_framework": "phase0_fixture",
                "field_run_id": args.run_id,
                "field_evidence_hash": "step11-permission-probe",
            },
            "relationships": {
                "field_target_node": {
                    "data": {"type": "node--article", "id": target1["node_uuid"]}
                },
                "field_target_file": {
                    "data": {"type": "file--file", "id": target1["file_uuid"]}
                },
            },
        }
    }
    write_json(out / "suggestion-create.json", suggestion)

    alt_items = copy.deepcopy(items)
    alt_meta = alt_items[delta].setdefault("meta", {})
    alt_meta["alt"] = "STEP 11 DENIED ALT MUTATION PROBE"
    alt_patch = {
        "data": {
            "type": "node--article",
            "id": target1["node_uuid"],
            "relationships": {"field_image": {"data": alt_items}},
        }
    }
    write_json(out / "article-alt-patch.json", alt_patch)

    item_items = copy.deepcopy(items)
    item_items[delta]["type"] = "file--file"
    item_items[delta]["id"] = target2["file_uuid"]
    replacement_meta = item_items[delta].setdefault("meta", {})
    replacement_meta["alt"] = "STEP 11 DENIED FILE-ITEM REPLACEMENT PROBE"
    item_patch = {
        "data": {
            "type": "node--article",
            "id": target1["node_uuid"],
            "relationships": {"field_image": {"data": item_items}},
        }
    }
    write_json(out / "article-item-patch.json", item_patch)
    return 0


def cmd_build_suggestion_patches(args: argparse.Namespace) -> int:
    response = load_json(args.response)
    data = response.get("data")
    if not isinstance(data, dict) or data.get("type") != "node--alt_text_suggestion":
        raise ValueError("POST response is not an alt_text_suggestion resource")
    suggestion_uuid = data.get("id")
    if not isinstance(suggestion_uuid, str) or not UUID_RE.match(suggestion_uuid):
        raise ValueError("POST response has no valid suggestion UUID")

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    payloads = {
        "suggestion-approve-patch.json": {"field_review_status": "approved"},
        "suggestion-reject-patch.json": {"field_review_status": "rejected"},
        "suggestion-edit-patch.json": {
            "field_proposed_alt": "STEP 11 DENIED SELF-EDIT PROBE"
        },
    }
    for filename, attributes in payloads.items():
        write_json(
            out / filename,
            {
                "data": {
                    "type": "node--alt_text_suggestion",
                    "id": suggestion_uuid,
                    "attributes": attributes,
                }
            },
        )
    print(suggestion_uuid)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    if args.kind == "none":
        return 0

    try:
        document = load_json(args.body)
    except Exception as exc:  # noqa: BLE001
        print(f"Response is not valid JSON: {exc}", file=sys.stderr)
        return 1

    try:
        if args.kind == "article_collection":
            data = document.get("data")
            if not isinstance(data, list) or not data:
                raise ValueError("Article collection is empty")
            if not all(item.get("type") == "node--article" for item in data):
                raise ValueError("Collection contains a non-Article resource")

        elif args.kind == "article_context":
            data = document.get("data")
            if not isinstance(data, dict):
                raise ValueError("Context response has no primary data object")
            if data.get("type") != "node--article" or data.get("id") != args.node_uuid:
                raise ValueError("Context response identifies the wrong Article")
            attrs = data.get("attributes", {})
            if "title" not in attrs or "body" not in attrs:
                raise ValueError("Context response does not expose both title and body")
            items = relationship_items(document)
            if args.delta is None or args.delta >= len(items):
                raise ValueError("Expected image-field delta is unavailable")
            if items[args.delta].get("id") != args.file_uuid:
                raise ValueError("Expected file UUID is not present at the target delta")
            included = document.get("included", [])
            if not isinstance(included, list) or not any(
                item.get("type") == "file--file" and item.get("id") == args.file_uuid
                for item in included
            ):
                raise ValueError("Included File resource is missing from page context")

        elif args.kind == "suggestion_created":
            data = document.get("data")
            if not isinstance(data, dict) or data.get("type") != "node--alt_text_suggestion":
                raise ValueError("Response is not an alt_text_suggestion")
            resource_id = data.get("id")
            if not isinstance(resource_id, str) or not UUID_RE.match(resource_id):
                raise ValueError("Created suggestion has no valid UUID")
            attrs = data.get("attributes", {})
            if attrs.get("field_review_status") != "pending":
                raise ValueError("Created suggestion is not pending")
            if attrs.get("field_source_framework") != "phase0_fixture":
                raise ValueError("Created suggestion does not use the neutral Phase 0 fixture origin")

        else:
            raise ValueError(f"Unknown validator kind: {args.kind}")
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1
    return 0


def sanitize_value(value: Any, site_url: str) -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in SENSITIVE_KEYS:
                clean[key] = "<REDACTED>"
            else:
                clean[key] = sanitize_value(item, site_url)
        return clean
    if isinstance(value, list):
        return [sanitize_value(item, site_url) for item in value]
    if isinstance(value, str):
        result = value.replace(site_url, "<SITE_URL>") if site_url else value
        result = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "<REDACTED_EMAIL>", result)
        return result
    return value


def sanitize_body(path: Path, site_url: str) -> tuple[Any, str]:
    raw = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        text = sanitize_value(raw, site_url)
        return str(text)[:8000], "text"
    return sanitize_value(parsed, site_url), "json"


def sanitize_headers(path: Path, site_url: str) -> list[str]:
    if not path.exists():
        return []
    result: list[str] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        lower = raw_line.lower()
        if lower.startswith(("set-cookie:", "authorization:", "x-debug-token:")):
            continue
        result.append(str(sanitize_value(raw_line, site_url)))
    return result


def cmd_record(args: argparse.Namespace) -> int:
    body, body_format = sanitize_body(Path(args.body), args.site_url)
    request: Any = None
    if args.request and Path(args.request).exists():
        request, _ = sanitize_body(Path(args.request), args.site_url)

    expected = [int(item) for item in args.expected.split(",") if item]
    actual = int(args.actual) if str(args.actual).isdigit() else 0
    passed = args.curl_exit == 0 and actual in expected and args.validator_passed
    record = {
        "test_id": args.test_id,
        "description": args.description,
        "timestamp_utc": args.timestamp,
        "account": args.account,
        "method": args.method,
        "path": args.path,
        "expected_http_status": expected,
        "actual_http_status": actual,
        "curl_exit_code": args.curl_exit,
        "semantic_validation_passed": args.validator_passed,
        "result": "PASS" if passed else "FAIL",
        "request_body": request,
        "response_headers": sanitize_headers(Path(args.headers), args.site_url),
        "response_body_format": body_format,
        "response_body": body,
    }
    write_json(args.output, record)
    print(record["result"])
    return 0 if passed else 1


def cmd_record_blocked(args: argparse.Namespace) -> int:
    record = {
        "test_id": args.test_id,
        "description": args.description,
        "timestamp_utc": args.timestamp,
        "account": args.account,
        "method": args.method,
        "path": args.path,
        "expected_http_status": [int(item) for item in args.expected.split(",") if item],
        "actual_http_status": 0,
        "curl_exit_code": 0,
        "semantic_validation_passed": False,
        "result": "FAIL",
        "blocked_reason": args.reason,
        "request_body": None,
        "response_headers": [],
        "response_body_format": "text",
        "response_body": args.reason,
    }
    write_json(args.output, record)
    return 1


def response_excerpt(value: Any) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False)
    return text.replace("\n", " ")[:280]


def cmd_report(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    records = []
    for path in sorted(run_dir.glob("test-*.json")):
        records.append(load_json(path))
    if not records:
        print("No test result files found", file=sys.stderr)
        return 2

    passed = sum(1 for item in records if item.get("result") == "PASS")
    failed = len(records) - passed
    summary = {
        "run_id": args.run_id,
        "generated_at_utc": args.timestamp,
        "test_count": len(records),
        "passed": passed,
        "failed": failed,
        "result": "PASS" if failed == 0 else "FAIL",
        "tests": [
            {
                "test_id": item["test_id"],
                "description": item["description"],
                "account": item["account"],
                "method": item["method"],
                "path": item["path"],
                "expected_http_status": item["expected_http_status"],
                "actual_http_status": item["actual_http_status"],
                "result": item["result"],
            }
            for item in records
        ],
    }
    write_json(run_dir / "summary.json", summary)

    with (run_dir / "summary.tsv").open("w", encoding="utf-8") as handle:
        handle.write("test_id\tresult\taccount\tmethod\tpath\texpected\tactual\tdescription\n")
        for item in records:
            handle.write(
                "\t".join(
                    [
                        str(item["test_id"]),
                        str(item["result"]),
                        str(item["account"]),
                        str(item["method"]),
                        str(item["path"]),
                        ",".join(map(str, item["expected_http_status"])),
                        str(item["actual_http_status"]),
                        str(item["description"]).replace("\t", " "),
                    ]
                )
                + "\n"
            )

    negative = [item for item in records if str(item["test_id"]).startswith("N")]
    rows = []
    for item in negative:
        css_class = "pass" if item["result"] == "PASS" else "fail"
        rows.append(
            "<tr class='{css}'><td>{id}</td><td>{account}</td><td>{method}</td>"
            "<td><code>{path}</code></td><td>{expected}</td><td>{actual}</td>"
            "<td>{result}</td><td>{excerpt}</td></tr>".format(
                css=css_class,
                id=html.escape(str(item["test_id"])),
                account=html.escape(str(item["account"])),
                method=html.escape(str(item["method"])),
                path=html.escape(str(item["path"])),
                expected=html.escape(",".join(map(str, item["expected_http_status"]))),
                actual=html.escape(str(item["actual_http_status"])),
                result=html.escape(str(item["result"])),
                excerpt=html.escape(response_excerpt(item.get("response_body"))),
            )
        )
    report_html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Step 11 Organ 2 denial evidence</title>
<style>
body{{font-family:system-ui,sans-serif;margin:2rem;line-height:1.4}} table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #999;padding:.5rem;vertical-align:top}} th{{background:#eee}}
.pass{{background:#eef9ee}} .fail{{background:#fdecec}} code{{font-size:.9em}}
</style></head><body>
<h1>Step 11 — Permission-boundary evidence</h1>
<p>Run <code>{html.escape(args.run_id)}</code>. This report contains sanitized responses and no credentials.</p>
<table><thead><tr><th>ID</th><th>Account</th><th>Method</th><th>Path</th><th>Expected</th><th>Actual</th><th>Result</th><th>Response excerpt</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></body></html>
"""
    (run_dir / "403-organ2-summary.html").write_text(report_html, encoding="utf-8")

    checklist = """# Step 11 screenshot checklist

Open `403-organ2-summary.html` and capture a readable screenshot showing the denied operations.
For stronger Organ 2 evidence, also capture these individual test JSON files in an editor:

- `test-N01.json` — agent cannot change Article alt text
- `test-N03.json` — agent cannot approve its own suggestion
- `test-N07.json` — anonymous cannot open the review queue
- `test-N08.json` — editor cannot administer AI-provider configuration

Keep the browser/editor address bar or file path visible enough to identify the evidence, but do not display `.secrets/` or any credential file.
"""
    (run_dir / "SCREENSHOT-CHECKLIST.md").write_text(checklist, encoding="utf-8")

    print(f"Step 11 results: {passed}/{len(records)} passed; {failed} failed")
    return 0 if failed == 0 else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("shell-targets")
    p.add_argument("--manifest", required=True)
    p.set_defaults(func=cmd_shell_targets)

    p = sub.add_parser("build-base-payloads")
    p.add_argument("--manifest", required=True)
    p.add_argument("--context", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--run-id", required=True)
    p.set_defaults(func=cmd_build_base_payloads)

    p = sub.add_parser("build-suggestion-patches")
    p.add_argument("--response", required=True)
    p.add_argument("--output-dir", required=True)
    p.set_defaults(func=cmd_build_suggestion_patches)

    p = sub.add_parser("validate")
    p.add_argument("--kind", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--node-uuid")
    p.add_argument("--file-uuid")
    p.add_argument("--delta", type=int)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("record")
    p.add_argument("--test-id", required=True)
    p.add_argument("--description", required=True)
    p.add_argument("--timestamp", required=True)
    p.add_argument("--account", required=True)
    p.add_argument("--method", required=True)
    p.add_argument("--path", required=True)
    p.add_argument("--expected", required=True)
    p.add_argument("--actual", required=True)
    p.add_argument("--curl-exit", required=True, type=int)
    p.add_argument("--validator-passed", required=True, type=lambda x: x.lower() == "true")
    p.add_argument("--headers", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--request")
    p.add_argument("--site-url", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_record)

    p = sub.add_parser("record-blocked")
    p.add_argument("--test-id", required=True)
    p.add_argument("--description", required=True)
    p.add_argument("--timestamp", required=True)
    p.add_argument("--account", required=True)
    p.add_argument("--method", required=True)
    p.add_argument("--path", required=True)
    p.add_argument("--expected", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_record_blocked)

    p = sub.add_parser("report")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--timestamp", required=True)
    p.set_defaults(func=cmd_report)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
