#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

TEST_IDS = [
    "S17-AUTH-001",
    "S17-AUTH-002",
    "S17-AUTH-003",
    "S17-COUNT-001",
    "S17-STATE-001",
    "S17-SCHEMA-001",
    "S17-SCHEMA-002",
    "S17-ORDER-001",
    "S17-IDENTITY-001",
    "S17-DUPLICATE-001",
    "S17-REPEAT-001",
    "S17-NOAI-001",
    "S17-MUTATION-001",
]

TARGET_KEYS = {
    "schema_version",
    "sequence",
    "node_uuid",
    "revision_id",
    "field_name",
    "delta",
    "file_uuid",
    "target_state",
    "existing_alt",
}
ENVELOPE_KEYS = {
    "schema_version",
    "tool_name",
    "ok",
    "timestamp",
    "correlation_id",
    "data",
    "error",
}
GENERIC_ALT_VALUES = {
    "image",
    "photo",
    "picture",
    "graphic",
    "illustration",
    "icon",
    "placeholder",
    "test image",
    "article image",
    "supporting image",
    "primary image",
    "phase 0 image",
    "phase0 image",
}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"Missing JSON file: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from None


def dump_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def parse_timestamp(value: str) -> None:
    if not value.endswith("Z"):
        raise ValueError("timestamp must end in Z")
    datetime.fromisoformat(value[:-1] + "+00:00")


def validate_uuid(value: Any, field: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a UUID string")
    try:
        parsed = uuid.UUID(value)
    except ValueError:
        raise ValueError(f"{field} is not a valid UUID") from None
    if str(parsed) != value.lower():
        raise ValueError(f"{field} must use canonical UUID formatting")


def validate_target(target: Any, schema: dict[str, Any]) -> None:
    if not isinstance(target, dict):
        raise ValueError("target must be an object")
    if set(target) != TARGET_KEYS:
        raise ValueError(f"target keys differ from frozen schema: {sorted(set(target) ^ TARGET_KEYS)}")
    if target["schema_version"] != schema["properties"]["schema_version"]["const"]:
        raise ValueError("schema_version must equal 1")
    sequence = target["sequence"]
    if not isinstance(sequence, int) or isinstance(sequence, bool) or not 1 <= sequence <= 12:
        raise ValueError("sequence must be an integer from 1 through 12")
    validate_uuid(target["node_uuid"], "node_uuid")
    if not isinstance(target["revision_id"], int) or isinstance(target["revision_id"], bool) or target["revision_id"] < 1:
        raise ValueError("revision_id must be a positive integer")
    if target["field_name"] != "field_image":
        raise ValueError("field_name must equal field_image")
    if not isinstance(target["delta"], int) or isinstance(target["delta"], bool) or target["delta"] < 0:
        raise ValueError("delta must be a nonnegative integer")
    validate_uuid(target["file_uuid"], "file_uuid")
    if target["target_state"] not in {"missing", "poor"}:
        raise ValueError("target_state must be missing or poor")
    if target["existing_alt"] is not None and not isinstance(target["existing_alt"], str):
        raise ValueError("existing_alt must be a string or null")


def validate_envelope(value: Any, target_schema: dict[str, Any], envelope_schema: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(value, dict) or set(value) != ENVELOPE_KEYS:
        raise ValueError("response envelope does not match the frozen top-level key set")
    if value["schema_version"] != 1:
        raise ValueError("envelope schema_version must equal 1")
    if value["tool_name"] != "find_images_needing_review":
        raise ValueError("unexpected tool_name")
    if value["ok"] is not True or value["error"] is not None:
        raise ValueError("successful response must set ok=true and error=null")
    parse_timestamp(value["timestamp"])
    correlation = value["correlation_id"]
    if not isinstance(correlation, str) or not 1 <= len(correlation) <= 128:
        raise ValueError("invalid correlation_id")
    data = value["data"]
    if not isinstance(data, dict) or set(data) != {"targets", "total_count"}:
        raise ValueError("data must contain only targets and total_count")
    if data["total_count"] != 12:
        raise ValueError("total_count must equal 12")
    targets = data["targets"]
    if not isinstance(targets, list) or len(targets) != 12:
        raise ValueError("targets must contain exactly 12 items")
    for target in targets:
        validate_target(target, target_schema)
    if envelope_schema.get("additionalProperties") is not False:
        raise ValueError("frozen envelope schema unexpectedly permits additional properties")
    return targets


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def classify_alt(alt: str, filename: str = "") -> str | None:
    normalized = normalize_text(alt)
    if not normalized:
        return "missing"
    stem = Path(filename).stem
    filename_values = {
        normalize_text(filename),
        normalize_text(stem),
        normalize_text(stem.replace("-", " ").replace("_", " ")),
    } - {""}
    if normalized in GENERIC_ALT_VALUES or normalized in filename_values:
        return "poor"
    if re.fullmatch(r"(image|photo|picture|graphic|illustration)( \d+)?(?:\.(?:png|jpe?g|gif|webp))?", normalized):
        return "poor"
    if len(normalized) <= 3:
        return "poor"
    return None


def walk_lists(value: Any) -> Iterable[list[Any]]:
    if isinstance(value, list):
        yield value
        for item in value:
            yield from walk_lists(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from walk_lists(item)


def first(row: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in row:
            return row[key]
    return default


def normalize_state(row: dict[str, Any], alt: str) -> str | None:
    raw = first(row, "target_state", "reason", "state", "expected_state", "alt_state", default="")
    text = normalize_text(str(raw))
    if "missing" in text or text in {"blank", "empty"}:
        return "missing"
    if "poor" in text or "inadequate" in text or "weak" in text:
        return "poor"
    filename = str(first(row, "filename", "file_name", default=""))
    return classify_alt(alt, filename)


def normalize_manifest_row(row: dict[str, Any], inferred_sequence: int) -> dict[str, Any] | None:
    node_uuid = first(row, "node_uuid", "article_uuid", "source_node_uuid")
    revision = first(row, "revision_id", "node_revision_id", "article_revision_id")
    field_name = first(row, "field_name", default="field_image")
    delta = first(row, "delta", "field_delta", default=0)
    file_uuid = first(row, "file_uuid", "image_file_uuid")
    alt = first(row, "existing_alt", "current_alt", "alt", default="")
    if not isinstance(alt, str) and alt is not None:
        alt = str(alt)
    state = normalize_state(row, alt or "")
    if not all([node_uuid, revision, file_uuid]) or field_name != "field_image" or state not in {"missing", "poor"}:
        return None
    sequence = first(row, "sequence", "target_sequence", default=inferred_sequence)
    return {
        "schema_version": 1,
        "sequence": int(sequence),
        "node_uuid": str(node_uuid),
        "revision_id": int(revision),
        "field_name": "field_image",
        "delta": int(delta),
        "file_uuid": str(file_uuid),
        "target_state": state,
        "existing_alt": alt,
    }


def extract_manifest_targets(manifest: Any) -> list[dict[str, Any]]:
    candidates: list[list[dict[str, Any]]] = []
    for rows in walk_lists(manifest):
        normalized: list[dict[str, Any]] = []
        for index, row in enumerate(rows, start=1):
            if isinstance(row, dict):
                item = normalize_manifest_row(row, index)
                if item is not None:
                    normalized.append(item)
        if normalized:
            candidates.append(normalized)
    if isinstance(manifest, dict):
        root_item = normalize_manifest_row(manifest, 1)
        if root_item:
            candidates.append([root_item])
    if not candidates:
        raise ValueError("Could not locate target-like records in the Step 9 manifest")
    exact = [rows for rows in candidates if len(rows) == 12]
    selected = exact[0] if exact else max(candidates, key=len)
    if len(selected) != 12:
        raise ValueError(f"Step 9 manifest normalization produced {len(selected)} targets, expected 12")
    selected.sort(key=lambda row: (row["sequence"], row["node_uuid"], row["delta"], row["file_uuid"]))
    for index, row in enumerate(selected, start=1):
        row["sequence"] = index
    return selected


def identity_key(target: dict[str, Any]) -> tuple[Any, ...]:
    return (
        target["node_uuid"],
        target["revision_id"],
        target["field_name"],
        target["delta"],
        target["file_uuid"],
    )


def add_result(results: list[dict[str, Any]], test_id: str, passed: bool, evidence: str, detail: str) -> None:
    results.append({
        "test_id": test_id,
        "status": "pass" if passed else "fail",
        "evidence": evidence,
        "detail": detail,
    })


def evaluate(root: Path, run_dir: Path, run_id: str) -> int:
    target_schema = load_json(root / "shared/schemas/target.schema.json")
    envelope_schema = load_json(root / "shared/schemas/tool-result.schema.json")
    response = load_json(run_dir / "response.json")
    repeat = load_json(run_dir / "repeat-response.json")
    manifest = load_json(run_dir / "step9-manifest.json")
    auth = load_json(run_dir / "authorization.json")
    identity = load_json(run_dir / "identity-validation.json")
    before = load_json(run_dir / "mutation-before.json")
    after = load_json(run_dir / "mutation-after.json")
    environment = load_json(run_dir / "environment.json")

    results: list[dict[str, Any]] = []

    add_result(results, "S17-AUTH-001", auth.get("agent") == 200, "authorization.json", f"agent HTTP {auth.get('agent')}")
    add_result(results, "S17-AUTH-002", auth.get("anonymous") in {401, 403}, "authorization.json", f"anonymous HTTP {auth.get('anonymous')}")
    add_result(results, "S17-AUTH-003", auth.get("editor") == 403, "authorization.json", f"editor HTTP {auth.get('editor')}")

    try:
        targets = validate_envelope(response, target_schema, envelope_schema)
        envelope_valid = True
        envelope_detail = "strict frozen envelope constraints passed"
    except ValueError as exc:
        targets = []
        envelope_valid = False
        envelope_detail = str(exc)

    add_result(results, "S17-COUNT-001", len(targets) == 12, "response.json", f"target count {len(targets)}")
    missing = sum(1 for target in targets if target.get("target_state") == "missing")
    poor = sum(1 for target in targets if target.get("target_state") == "poor")
    add_result(results, "S17-STATE-001", (missing, poor) == (9, 3), "response.json", f"missing={missing}, poor={poor}")

    target_schema_valid = envelope_valid and all(set(target) == TARGET_KEYS for target in targets)
    add_result(results, "S17-SCHEMA-001", target_schema_valid, "target-schema-validation.json", "all targets match target.schema.json constraints")
    add_result(results, "S17-SCHEMA-002", envelope_valid, "envelope-schema-validation.json", envelope_detail)

    try:
        expected = extract_manifest_targets(manifest)
        actual_sorted = sorted(targets, key=lambda row: row["sequence"])
        order_match = actual_sorted == expected
        manifest_error = ""
    except ValueError as exc:
        expected = []
        order_match = False
        manifest_error = str(exc)
    add_result(results, "S17-ORDER-001", order_match, "step9-manifest.json", manifest_error or "discovery exactly matches normalized Step 9 manifest")

    identity_pass = identity.get("status") == "pass" and identity.get("validated_count") == 12
    add_result(results, "S17-IDENTITY-001", identity_pass, "identity-validation.json", f"validated_count={identity.get('validated_count')}")

    keys = [identity_key(target) for target in targets]
    no_duplicates = len(keys) == 12 and len(set(keys)) == 12
    add_result(results, "S17-DUPLICATE-001", no_duplicates, "response.json", f"unique identities={len(set(keys))}")

    try:
        repeat_targets = validate_envelope(repeat, target_schema, envelope_schema)
        repeat_hash = sha256_value(repeat_targets)
        target_hash = sha256_value(targets)
        repeat_pass = repeat_hash == target_hash
        repeat_detail = f"first={target_hash}, second={repeat_hash}"
    except ValueError as exc:
        repeat_hash = ""
        target_hash = sha256_value(targets)
        repeat_pass = False
        repeat_detail = str(exc)
    add_result(results, "S17-REPEAT-001", repeat_pass, "repeatability.json", repeat_detail)

    no_ai = all(environment.get(key) is False for key in (
        "openai_api_key_present",
        "openai_candidate_model_present",
        "crewai_candidate_model_present",
    )) and environment.get("model_call_performed") is False
    add_result(results, "S17-NOAI-001", no_ai, "environment.json", "model variables absent and no model call performed")

    mutation_pass = (
        before.get("status") == "pass"
        and after.get("status") == "pass"
        and before.get("source_sha256") == after.get("source_sha256")
        and before.get("suggestion_count") == after.get("suggestion_count") == 0
    )
    add_result(results, "S17-MUTATION-001", mutation_pass, "mutation-before.json, mutation-after.json", "source hash and suggestion count unchanged")

    # Derived sanitized artifacts.
    dump_json(run_dir / "targets.json", targets)
    dump_json(run_dir / "target-schema-validation.json", {
        "schema": "shared/schemas/target.schema.json",
        "status": "pass" if target_schema_valid else "fail",
        "validated_count": len(targets) if target_schema_valid else 0,
        "validator": "strict contract-specific validator in scripts/step17_evidence.py",
    })
    dump_json(run_dir / "envelope-schema-validation.json", {
        "schema": "shared/schemas/tool-result.schema.json",
        "status": "pass" if envelope_valid else "fail",
        "detail": envelope_detail,
        "validator": "strict contract-specific validator in scripts/step17_evidence.py",
    })
    dump_json(run_dir / "repeatability.json", {
        "status": "pass" if repeat_pass else "fail",
        "canonical_scope": "data.targets only; dynamic timestamp and correlation_id excluded",
        "first_targets_sha256": target_hash,
        "second_targets_sha256": repeat_hash,
    })
    dump_json(run_dir / "manifest-comparison.json", {
        "status": "pass" if order_match else "fail",
        "normalized_expected_count": len(expected),
        "actual_count": len(targets),
        "expected_targets_sha256": sha256_value(expected),
        "actual_targets_sha256": sha256_value(targets),
        "detail": manifest_error or "exact ordered match",
    })

    failed = [row for row in results if row["status"] != "pass"]
    summary = {
        "run_id": run_id,
        "status": "pass" if not failed else "fail",
        "tool_name": "find_images_needing_review",
        "mode": "model-free",
        "total": len(results),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "expected_tests": TEST_IDS,
        "tests": results,
        "controls": {
            "expected_total_count": 12,
            "expected_missing_count": 9,
            "expected_poor_count": 3,
            "target_schema": "shared/schemas/target.schema.json",
            "envelope_schema": "shared/schemas/tool-result.schema.json",
            "source_mutation_allowed": False,
            "model_call_allowed": False,
        },
        "claims": {
            "proves": [
                "the permission-scoped Drupal route discovered exactly 12 current image-field usages",
                "the discovered targets matched the Step 9 manifest in deterministic order",
                "the operation ran without model credentials or a model call",
                "the source Article state and suggestion count were unchanged",
            ],
            "does_not_prove": [
                "alt-text recommendation quality",
                "framework orchestration",
                "framework superiority",
                "Gate 0.5 completion",
                "production readiness",
            ],
        },
    }
    dump_json(run_dir / "summary.json", summary)

    with (run_dir / "results.tsv").open("w", encoding="utf-8") as handle:
        handle.write("test_id\tstatus\tevidence\tdetail\n")
        for row in results:
            detail = str(row["detail"]).replace("\t", " ").replace("\n", " ")
            handle.write(f"{row['test_id']}\t{row['status']}\t{row['evidence']}\t{detail}\n")

    lines = [
        "# Step 17 discovery result",
        "",
        f"- Run: `{run_id}`",
        f"- Status: **{summary['status']}**",
        f"- Tests: **{summary['passed']}/{summary['total']} passed**",
        "- Operation: `find_images_needing_review()`",
        "- Mode: model-free",
        "- Expected fixture result: 12 targets — 9 missing, 3 poor",
        "",
        "## Results",
        "",
        "| Test | Status | Evidence |",
        "|---|---|---|",
    ]
    lines.extend(f"| `{row['test_id']}` | {row['status']} | `{row['evidence']}` |" for row in results)
    lines.extend([
        "",
        "## Interpretation",
        "",
        "This run proves deterministic, permission-scoped target discovery only. It does not call the frozen model, generate alt text, create a recommendation, or exercise any framework-owned orchestration.",
        "",
    ])
    (run_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"[{'OK' if not failed else 'ERROR'}] Step 17 evidence: {summary['passed']}/{summary['total']} passed.")
    for row in failed:
        print(f"[ERROR] {row['test_id']}: {row['detail']}")
    return 0 if not failed else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    evaluate_parser = sub.add_parser("evaluate")
    evaluate_parser.add_argument("--root", type=Path, required=True)
    evaluate_parser.add_argument("--run-dir", type=Path, required=True)
    evaluate_parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if args.command == "evaluate":
        return evaluate(args.root.resolve(), args.run_dir.resolve(), args.run_id)
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
