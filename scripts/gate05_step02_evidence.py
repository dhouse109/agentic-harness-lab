#!/usr/bin/env python3
"""Evaluate and audit Gate 0.5 Step 02 image-context evidence."""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PACKAGE_VERSION = "1.0.1"
IMPLEMENTATION_FILES = [
    "drupal/web/modules/custom/agentic_harness_tools/agentic_harness_tools.routing.yml",
    "drupal/web/modules/custom/agentic_harness_tools/agentic_harness_tools.services.yml",
    "drupal/web/modules/custom/agentic_harness_tools/src/Controller/ToolController.php",
    "drupal/web/modules/custom/agentic_harness_tools/src/Exception/ImageContextException.php",
    "drupal/web/modules/custom/agentic_harness_tools/src/Service/ImageContextProvider.php",
    "shared/drupal_client/client.py",
    "shared/drupal_client/README.md",
    "shared/schemas/target.schema.json",
    "shared/schemas/image-context.schema.json",
]


class EvidenceError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"Missing required file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def validate_target(target: Any) -> dict[str, Any]:
    required = {
        "schema_version", "sequence", "node_uuid", "revision_id", "field_name",
        "delta", "file_uuid", "target_state", "existing_alt",
    }
    if not isinstance(target, dict) or set(target) != required:
        raise EvidenceError("Returned target does not match target.schema.json keys.")
    if target["schema_version"] != 1 or target["sequence"] != 1:
        raise EvidenceError("Step 02 must use canonical target sequence 1.")
    if target["field_name"] != "field_image":
        raise EvidenceError("Target field is not field_image.")
    if target["target_state"] not in {"missing", "poor"}:
        raise EvidenceError("Target state is invalid.")
    for key in ("node_uuid", "file_uuid"):
        if not isinstance(target[key], str) or not re.fullmatch(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}",
            target[key],
        ):
            raise EvidenceError(f"Target {key} is not a UUID.")
    if not isinstance(target["revision_id"], int) or target["revision_id"] < 1:
        raise EvidenceError("Target revision_id is invalid.")
    if not isinstance(target["delta"], int) or target["delta"] < 0:
        raise EvidenceError("Target delta is invalid.")
    if target["existing_alt"] is not None and not isinstance(target["existing_alt"], str):
        raise EvidenceError("Target existing_alt is invalid.")
    return target


def parse_iso8601(value: Any) -> None:
    if not isinstance(value, str):
        raise EvidenceError("collected_at must be a string.")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("collected_at is not ISO-8601.") from exc


def validate_context(
    envelope: Any,
    canonical_target: dict[str, Any],
) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    if not isinstance(envelope, dict):
        raise EvidenceError("Image-context response envelope must be an object.")
    expected_envelope = {
        "schema_version", "tool_name", "ok", "timestamp",
        "correlation_id", "data", "error",
    }
    if set(envelope) != expected_envelope:
        raise EvidenceError("Image-context envelope keys are invalid.")
    if (
        envelope["schema_version"] != 1
        or envelope["tool_name"] != "get_image_context"
        or envelope["ok"] is not True
        or envelope["error"] is not None
    ):
        raise EvidenceError("Image-context envelope is not a successful result.")

    context = envelope["data"]
    required_context = {
        "schema_version", "target", "article", "image",
        "existing_alt", "evidence_hash", "collected_at",
    }
    if not isinstance(context, dict) or set(context) != required_context:
        raise EvidenceError("Context does not match image-context.schema.json keys.")
    if context["schema_version"] != 1:
        raise EvidenceError("Context schema_version is invalid.")

    target = validate_target(context["target"])
    if target != canonical_target:
        raise EvidenceError("Returned context target differs from the Gate 0.5 canonical target.")
    if context["existing_alt"] != target["existing_alt"]:
        raise EvidenceError("Context existing_alt differs from target identity.")

    article = context["article"]
    required_article = {"title", "body_plain", "revision_id", "content_language"}
    if not isinstance(article, dict) or set(article) != required_article:
        raise EvidenceError("Article context keys are invalid.")
    if not isinstance(article["title"], str) or not article["title"]:
        raise EvidenceError("Article title is missing.")
    if not isinstance(article["body_plain"], str):
        raise EvidenceError("Article body_plain is invalid.")
    if article["revision_id"] != target["revision_id"]:
        raise EvidenceError("Article revision does not match target.")
    if not isinstance(article["content_language"], str) or not article["content_language"]:
        raise EvidenceError("Article content language is invalid.")

    image = context["image"]
    required_image = {
        "file_uuid", "filename", "mime_type", "width", "height",
        "byte_length", "sha256", "representation",
    }
    if not isinstance(image, dict) or set(image) != required_image:
        raise EvidenceError("Image context keys are invalid.")
    if image["file_uuid"] != target["file_uuid"]:
        raise EvidenceError("Image UUID does not match target.")
    if not isinstance(image["filename"], str) or not image["filename"]:
        raise EvidenceError("Image filename is missing.")
    if not isinstance(image["mime_type"], str) or not image["mime_type"].startswith("image/"):
        raise EvidenceError("Image MIME type is invalid.")
    if not isinstance(image["byte_length"], int) or image["byte_length"] < 1:
        raise EvidenceError("Image byte length is invalid.")
    if not isinstance(image["sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", image["sha256"]):
        raise EvidenceError("Image SHA-256 is invalid.")
    for key in ("width", "height"):
        if image[key] is not None and (
            not isinstance(image[key], int) or image[key] < 1
        ):
            raise EvidenceError(f"Image {key} is invalid.")

    representation = image["representation"]
    if (
        not isinstance(representation, dict)
        or set(representation) != {"kind", "value"}
        or representation["kind"] != "data_url"
        or not isinstance(representation["value"], str)
    ):
        raise EvidenceError("Image representation is not the approved data_url shape.")
    prefix = f"data:{image['mime_type']};base64,"
    if not representation["value"].startswith(prefix):
        raise EvidenceError("Image data URL MIME prefix does not match metadata.")
    try:
        image_bytes = base64.b64decode(
            representation["value"][len(prefix):],
            validate=True,
        )
    except Exception as exc:
        raise EvidenceError("Image data URL contains invalid Base64.") from exc
    if len(image_bytes) != image["byte_length"]:
        raise EvidenceError("Decoded image length does not match metadata.")
    if sha256_bytes(image_bytes) != image["sha256"]:
        raise EvidenceError("Decoded image hash does not match metadata.")

    hash_payload = {
        "schema_version": 1,
        "target": target,
        "article": article,
        "image": {
            "file_uuid": image["file_uuid"],
            "filename": image["filename"],
            "mime_type": image["mime_type"],
            "width": image["width"],
            "height": image["height"],
            "byte_length": image["byte_length"],
            "sha256": image["sha256"],
            "representation_kind": "data_url",
        },
        "existing_alt": context["existing_alt"],
    }
    expected_hash = "sha256:" + sha256_bytes(canonical_bytes(hash_payload))
    if context["evidence_hash"] != expected_hash:
        raise EvidenceError("Context evidence_hash does not recompute.")
    parse_iso8601(context["collected_at"])

    return context, image_bytes, hash_payload


def sanitize_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(envelope)
    representation = value["data"]["image"]["representation"]
    raw = representation["value"].encode("utf-8")
    representation["value"] = "<runtime-only-data-url>"
    return {
        "envelope": value,
        "retention": {
            "representation_value_retained": False,
            "runtime_data_url_length": len(raw),
            "runtime_data_url_sha256": sha256_bytes(raw),
            "raw_image_bytes_retained": False,
        },
    }


def error_code(path: Path) -> str:
    value = load_json(path)
    if not isinstance(value, dict):
        raise EvidenceError(f"Negative response is not an object: {path.name}")
    error = value.get("error")
    if not isinstance(error, dict):
        raise EvidenceError(f"Negative response lacks an error object: {path.name}")
    return str(error.get("code", ""))


def implementation_hashes(repo: Path) -> dict[str, str]:
    hashes = {}
    for relative in IMPLEMENTATION_FILES:
        path = repo / relative
        if not path.is_file():
            raise EvidenceError(f"Missing implementation file: {relative}")
        hashes[relative] = sha256_bytes(path.read_bytes())
    return hashes


def evaluate(
    repo: Path,
    run_dir: Path,
    raw_positive: Path,
    raw_repeat: Path,
    canonical_target_path: Path,
) -> None:
    canonical_target = validate_target(load_json(canonical_target_path))
    positive = load_json(raw_positive)
    repeat = load_json(raw_repeat)

    context, image_bytes, hash_payload = validate_context(positive, canonical_target)
    repeat_context, repeat_bytes, repeat_hash_payload = validate_context(repeat, canonical_target)

    first_stable = copy.deepcopy(context)
    second_stable = copy.deepcopy(repeat_context)
    first_stable.pop("collected_at", None)
    second_stable.pop("collected_at", None)
    if first_stable != second_stable:
        raise EvidenceError("Repeated image-context collection is not stable.")
    if image_bytes != repeat_bytes or hash_payload != repeat_hash_payload:
        raise EvidenceError("Repeated image bytes or hash payload differ.")

    statuses = load_json(run_dir / "http-statuses.json")
    expected_statuses = {
        "positive": 200,
        "repeat": 200,
        "editor": 403,
        "malformed_json": 400,
        "invalid_target": 422,
        "stale_revision": 409,
        "stale_file": 409,
    }
    if not isinstance(statuses, dict):
        raise EvidenceError("HTTP status evidence is not an object.")
    for key, expected in expected_statuses.items():
        if statuses.get(key) != expected:
            raise EvidenceError(
                f"Unexpected HTTP status for {key}: "
                f"expected {expected}, got {statuses.get(key)}."
            )
    if statuses.get("anonymous") not in {401, 403}:
        raise EvidenceError("Anonymous request was not denied.")

    expected_codes = {
        "malformed-json.json": "MALFORMED_JSON",
        "invalid-target.json": "INVALID_TARGET",
        "stale-revision.json": "TARGET_STALE",
        "stale-file.json": "TARGET_STALE",
    }
    for filename, expected in expected_codes.items():
        actual = error_code(run_dir / filename)
        if actual != expected:
            raise EvidenceError(
                f"Unexpected error code in {filename}: expected {expected}, got {actual}."
            )

    before = load_json(run_dir / "source-before.json")
    after = load_json(run_dir / "source-after.json")
    if (
        not isinstance(before, dict)
        or not isinstance(after, dict)
        or before.get("source_sha256") != after.get("source_sha256")
        or before.get("suggestion_count") != 0
        or after.get("suggestion_count") != 0
    ):
        raise EvidenceError("Source Article state or suggestion count changed.")

    environment = load_json(run_dir / "environment.json")
    for key in (
        "openai_api_key_present",
        "openai_candidate_model_present",
        "crewai_candidate_model_present",
        "model_call_performed",
    ):
        if environment.get(key) is not False:
            raise EvidenceError(f"Model-free environment control failed: {key}")

    sanitized = sanitize_envelope(positive)
    write_json(run_dir / "response-sanitized.json", sanitized)
    write_json(run_dir / "canonical-target.json", canonical_target)
    write_json(run_dir / "hash-payload.json", hash_payload)

    hashes = implementation_hashes(repo)
    (run_dir / "implementation-sha256.txt").write_text(
        "".join(f"{digest}  {relative}\n" for relative, digest in hashes.items()),
        encoding="utf-8",
    )

    baseline_rel = (repo / "evidence/gates/gate-0.5/baseline/GATE05-STEP01-LATEST.txt").read_text(
        encoding="utf-8"
    ).strip()
    criteria = {
        "gate01_baseline_present": True,
        "canonical_target_sequence_1": True,
        "agent_context_http_200": True,
        "image_context_shape_valid": True,
        "runtime_data_url_valid": True,
        "evidence_hash_recomputed": True,
        "repeat_context_stable": True,
        "anonymous_denied": True,
        "editor_denied": True,
        "malformed_json_rejected": True,
        "invalid_target_rejected": True,
        "stale_revision_rejected": True,
        "changed_file_rejected": True,
        "source_article_unchanged": True,
        "suggestion_count_remains_zero": True,
        "model_variables_absent": True,
        "raw_image_not_retained": True,
    }

    summary = {
        "schema_version": 1,
        "package": "gate-0.5-step02-image-context",
        "package_version": PACKAGE_VERSION,
        "run_id": run_dir.name,
        "status": "pass",
        "operation": "get_image_context",
        "baseline_evidence": baseline_rel,
        "canonical_target": canonical_target,
        "context_evidence_hash": context["evidence_hash"],
        "image_sha256": context["image"]["sha256"],
        "image_byte_length": context["image"]["byte_length"],
        "implementation_files": hashes,
        "http_statuses": statuses,
        "criteria": criteria,
        "next_step": "Gate 0.5 Step 03 — submit_recommendation deterministic shared operation",
    }
    write_json(run_dir / "summary.json", summary)
    (run_dir / "summary.md").write_text(
        f"""# Gate 0.5 Step 02 Image Context Summary

- **Status:** PASS
- **Run ID:** `{run_dir.name}`
- **Operation:** `get_image_context(target)`
- **Canonical target:** sequence 1
- **Context evidence hash:** `{context['evidence_hash']}`
- **Image SHA-256:** `{context['image']['sha256']}`
- **Image byte length:** `{context['image']['byte_length']}`
- **Runtime representation:** Base64 data URL
- **Raw representation retained:** no
- **Source Article changed:** no
- **Suggestions created:** 0
- **Model call performed:** no

## Negative controls

- anonymous denied
- `editor_dana` denied
- malformed JSON rejected
- malformed target rejected
- stale revision rejected
- changed file UUID rejected

## Next step

Gate 0.5 Step 03 adds deterministic recommendation validation and submission.
""",
        encoding="utf-8",
    )


def audit(repo: Path, run_dir: Path) -> None:
    summary = load_json(run_dir / "summary.json")
    if not isinstance(summary, dict) or summary.get("status") != "pass":
        raise EvidenceError("Latest Step 02 summary is not passing.")

    required = [
        "summary.json", "summary.md", "canonical-target.json",
        "response-sanitized.json", "hash-payload.json", "http-statuses.json",
        "authorization.json", "environment.json", "source-before.json",
        "source-after.json", "malformed-json.json", "invalid-target.json",
        "stale-revision.json", "stale-file.json", "implementation-sha256.txt",
        "setup.log", "positive-client.log", "repeat-client.log",
    ]
    for filename in required:
        if not (run_dir / filename).is_file():
            raise EvidenceError(f"Missing retained Step 02 evidence: {filename}")

    current_hashes = implementation_hashes(repo)
    if current_hashes != summary.get("implementation_files"):
        raise EvidenceError("Step 02 implementation files changed after the passing run.")

    retained = (run_dir / "response-sanitized.json").read_text(
        encoding="utf-8", errors="replace"
    )
    if "data:image/" in retained and ";base64," in retained:
        raise EvidenceError("Retained evidence contains a raw image data URL.")
    if re.search(r"sk-[A-Za-z0-9_-]{8,}", retained):
        raise EvidenceError("Retained evidence contains a possible API key.")

    statuses = load_json(run_dir / "http-statuses.json")
    if statuses.get("positive") != 200 or statuses.get("repeat") != 200:
        raise EvidenceError("Passing positive HTTP status evidence is missing.")

    before = load_json(run_dir / "source-before.json")
    after = load_json(run_dir / "source-after.json")
    if before.get("source_sha256") != after.get("source_sha256"):
        raise EvidenceError("Source hash changed after the passing Step 02 run.")

    print(json.dumps({
        "status": "pass",
        "run_id": run_dir.name,
        "operation": "get_image_context",
        "canonical_target_sequence": 1,
        "context_evidence_hash": summary.get("context_evidence_hash"),
        "implementation_hashes_match": True,
        "raw_image_retained": False,
        "next_step": summary.get("next_step"),
    }, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    evaluate_parser = sub.add_parser("evaluate")
    evaluate_parser.add_argument("--repo", required=True)
    evaluate_parser.add_argument("--run-dir", required=True)
    evaluate_parser.add_argument("--raw-positive", required=True)
    evaluate_parser.add_argument("--raw-repeat", required=True)
    evaluate_parser.add_argument("--canonical-target", required=True)

    audit_parser = sub.add_parser("audit")
    audit_parser.add_argument("--repo", required=True)
    audit_parser.add_argument("--run-dir", required=True)

    args = parser.parse_args()
    try:
        if args.command == "evaluate":
            evaluate(
                Path(args.repo).resolve(),
                Path(args.run_dir).resolve(),
                Path(args.raw_positive).resolve(),
                Path(args.raw_repeat).resolve(),
                Path(args.canonical_target).resolve(),
            )
        else:
            audit(Path(args.repo).resolve(), Path(args.run_dir).resolve())
    except EvidenceError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
