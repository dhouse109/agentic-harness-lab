#!/usr/bin/env python3
"""Permanent static audit for ADR-0008's File identity and URI locator boundary."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

FROZEN = {
    "shared/schemas/image-context.schema.json": "b2e27b533551759d181c58330ebedcb26ca92c1a596dbb4aaf48a48422dffaee",
    "drupal/web/modules/custom/agentic_harness_tools/src/Service/ImageContextProvider.php": "20ffc39c6e5c3e9c10a9ae6f80954eff32626dd96d7cca2da04f3f0ebb5e30b1",
    "docs/decisions/ADR-0007-canonical-slice-evidence-image-and-state-boundary.md": "7a50db44fe626d10012a03f1bfa942f3592552f44397d57cb11af47a02f506bf",
}
PROFILE = "shared/profiles/gate1-drupal-ai-file-transport-clarification-v1.0.0/file-transport-clarification-profile.json"
IDENTITY = ["file_uuid", "filename", "mime_type", "byte_length", "sha256"]
EVIDENCE_PROHIBITED = ["uri", "resolved_path", "file_entity", "raw_bytes", "base64", "data_url"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"[ERROR] {message}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--overlay", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    overlay = args.overlay.resolve() if args.overlay else repo

    for relative, expected in FROZEN.items():
        require(sha256(repo / relative) == expected, f"Frozen file changed: {relative}")

    image = load(repo / "shared/schemas/image-context.schema.json")["properties"]["image"]
    require(image.get("additionalProperties") is False, "image-context image object accepts additional properties")
    require("uri" not in image["properties"], "image-context schema authorizes a URI field")
    require(all(field in image["required"] for field in IDENTITY), "image-context identity fields are not all required")

    provider = (repo / "drupal/web/modules/custom/agentic_harness_tools/src/Service/ImageContextProvider.php").read_text(encoding="utf-8")
    require("$uri = $file->getFileUri();" in provider, "ImageContextProvider no longer obtains an internal URI")
    require("$this->fileSystem->realpath($uri);" in provider, "ImageContextProvider no longer resolves URI internally")
    require("file_get_contents($realpath)" in provider, "ImageContextProvider no longer reads bytes through its internal path")
    metadata = re.search(r"\$image_metadata\s*=\s*\[(.*?)\n\s*\];", provider, re.S)
    require(metadata is not None and "uri" not in metadata.group(1).lower(), "ImageContextProvider returns URI metadata")
    require(not re.search(r"['\"]uri['\"]\s*=>", provider), "ImageContextProvider returns a URI field")

    profile = load(overlay / PROFILE)
    require(profile.get("authoritative_identity_fields") == IDENTITY, "authoritative identity fields changed")
    expected = {
        "uri_role": "internal_transport_locator",
        "uri_authorized_context_field": False,
        "uri_retained": False,
        "local_stream_wrapper_required": True,
        "remote_uri_prohibited": True,
        "exact_uuid_resolution_required": True,
        "exactly_one_file_entity_required": True,
        "byte_reverification_required": True,
        "model_supplied_identity_prohibited": True,
        "source_mutation_prohibited": True,
        "file_system_resolution_required": True,
        "readable_local_path_required": True,
        "canonical_slice_profile_modified": False,
        "step_1_04_implementation_included": False,
        "step_1_05_included": False,
    }
    for key, value in expected.items():
        require(profile.get(key) == value, f"clarification profile field is invalid: {key}")
    require(profile.get("approved_local_stream_wrapper_schemes") == ["public", "private"], "approved local schemes changed")
    require(profile.get("entity_identity_reverification_required") == IDENTITY[:3], "entity identity re-verification changed")
    require(profile.get("prohibited_evidence_artifacts") == EVIDENCE_PROHIBITED, "evidence prohibition changed")
    require(profile.get("model_supplied_uri_path_or_file_selection_prohibited") is True, "model input prohibition missing")
    required_failures = {"uuid_mismatch", "filename_mismatch", "mime_type_mismatch", "byte_length_mismatch", "sha256_mismatch", "file_resolution_failure", "file_readability_failure", "zero_or_multiple_file_entities", "stream_wrapper_mismatch"}
    require(required_failures == set(profile.get("fail_closed_on", [])), "fail-closed regression controls changed")
    require(profile.get("uri_change_identity_failure") is False, "URI relocation rule changed")
    require(set(profile.get("uri_change_allowed_only_when", [])) == {"same_authorized_file_uuid_resolves", "filename_exact", "mime_type_exact", "byte_length_exact", "sha256_exact", "permitted_local_drupal_locator"}, "URI relocation safeguards changed")

    package_root = repo.parent / "agentic-harness-lab-packages"
    prohibited_packages = [
        package_root / "gate-1-step04-drupal-ai-canonical-vertical-slice-v1.0.0",
        package_root / "gate-1-step05-drupal-ai-batch-runner-v1.0.0",
    ]
    require(not any(path.exists() for path in prohibited_packages), "Step 1.04 implementation or Step 1.05 package exists")
    prohibited_repo_paths = [
        repo / "drupal/scripts/gate1-step04-canonical-vertical-slice.php",
        repo / "scripts/run-gate1-step04-drupal-ai-canonical-vertical-slice.sh",
        repo / "scripts/run-gate1-step05-drupal-ai-batch-runner.sh",
    ]
    require(not any(path.exists() for path in prohibited_repo_paths), "Step 1.04 implementation or Step 1.05 source exists")

    print(json.dumps({
        "status": "pass",
        "image_context_uri_field": False,
        "image_context_checksum_unchanged": True,
        "provider_uri_internal_only": True,
        "adr0007_unchanged": True,
        "authoritative_identity_fields": IDENTITY,
        "local_uri_role": "internal_transport_locator",
        "remote_uri_rejected": True,
        "model_supplied_identity_rejected": True,
        "zero_or_multiple_file_results_rejected": True,
        "entity_and_byte_mismatches_rejected": True,
        "evidence_artifacts_prohibited": EVIDENCE_PROHIBITED,
        "step_1_04_implementation_absent": True,
        "step_1_05_absent": True,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
