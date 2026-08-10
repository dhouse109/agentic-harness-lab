#!/usr/bin/env python3
"""Reproducibly instantiate LangGraph batch evidence schemas from frozen Gate 1 templates.

Most collection schemas require provenance-only substitution. Two Gate 1 shapes are
failure-specific (batch-event and batch-recovery), while the frozen Gate 2A contract
requires a controlled continuation rather than Gate 2C failure injection. Those two
schemas receive explicit, narrowly-scoped continuation adaptations recorded in the map.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

MAP_REL = "shared/contracts/GATE2A-LANGGRAPH-EVIDENCE-SCHEMA-MAP.json"
SOURCE_GLOB = "batch-*.schema.json"
EXPECTED_SOURCE_NAMES = {
    "batch-event.schema.json",
    "batch-human-review.schema.json",
    "batch-model-outputs.schema.json",
    "batch-recommendations.schema.json",
    "batch-recovery.schema.json",
    "batch-statuses.schema.json",
    "batch-submissions.schema.json",
    "batch-summary.schema.json",
    "batch-target-sequence.schema.json",
    "batch-tool-traces.schema.json",
    "batch-validation.schema.json",
}
CONTRACT_SHA = "1ccd44e7b42f0001a134f83e4b368856bd2504a80b89735ac1296404776e289b"


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def transform_string(value: str) -> str:
    if value == "drupal_ai":
        return "langgraph"
    value = value.replace("^drupal_ai-", "^langgraph-")
    value = value.replace("drupal-ai-model-output.schema.json", "langgraph-model-output.schema.json")
    value = value.replace("drupal-ai-run-state.schema.json", "langgraph-run-state.schema.json")
    value = value.replace("Drupal AI", "LangGraph")
    return value


def transform(value: Any) -> Any:
    if isinstance(value, str):
        return transform_string(value)
    if isinstance(value, list):
        return [transform(item) for item in value]
    if isinstance(value, dict):
        return {key: transform(item) for key, item in value.items()}
    return value


def adapt_controlled_continuation(source_name: str, derived: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Apply only the semantic adaptations required by frozen Gate 2A continuation policy."""
    if source_name == "batch-event.schema.json":
        enum = derived["properties"]["event_type"]["enum"]
        if "continuation_interrupted" not in enum:
            # Do not remove the historical failure event; add the truthful Gate 2A event.
            enum.insert(enum.index("failure_injected"), "continuation_interrupted")
        return derived, "controlled-continuation-event-adaptation"

    if source_name == "batch-recovery.schema.json":
        # Gate 1's recovery schema requires a failure-injected narrative. Gate 2A's frozen
        # continuation policy explicitly says target-6/7 is a controlled stop and must not
        # be conflated with Gate 2C failure/recovery. Preserve the result filename/recovery
        # lifecycle slot, but instantiate a truthful controlled-continuation shape.
        run_pattern = "^langgraph-[0-9]{8}T[0-9]{6}Z-[a-z0-9]{4,12}$"
        derived = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "langgraph-batch-recovery.schema.json",
            "title": "LangGraph controlled same-run continuation evidence",
            "type": "object",
            "required": [
                "schema_version", "run_id", "source_framework",
                "controlled_stop_after_sequence", "resume_at_sequence",
                "completed_before_stop", "interrupted_at", "resumed_at",
                "resumed_with_run_id", "duplicate_count", "completed_after_resume",
                "gate2c_failure_injection_fired",
            ],
            "properties": {
                "schema_version": {"const": 1},
                "run_id": {"type": "string", "pattern": run_pattern},
                "source_framework": {"const": "langgraph"},
                "controlled_stop_after_sequence": {"const": 6},
                "resume_at_sequence": {"const": 7},
                "completed_before_stop": {
                    "type": "array",
                    "prefixItems": [{"const": n} for n in range(1, 7)],
                    "items": False,
                    "minItems": 6,
                    "maxItems": 6,
                },
                "interrupted_at": {"type": "string", "format": "date-time"},
                "resumed_at": {"type": "string", "format": "date-time"},
                "resumed_with_run_id": {"type": "string", "pattern": run_pattern},
                "duplicate_count": {"const": 0},
                "completed_after_resume": {
                    "type": "array",
                    "prefixItems": [{"const": n} for n in range(7, 13)],
                    "items": False,
                    "minItems": 6,
                    "maxItems": 6,
                },
                "gate2c_failure_injection_fired": {"const": False},
            },
            "additionalProperties": False,
        }
        return derived, "controlled-continuation-recovery-adaptation"

    return derived, "provenance-only"


def derive(source_name: str, source: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
    target_name = "langgraph-" + source_name
    derived = transform(deepcopy(source))
    if isinstance(derived.get("$id"), str):
        derived["$id"] = target_name
    derived, kind = adapt_controlled_continuation(source_name, derived)
    Draft202012Validator.check_schema(derived)
    return target_name, derived, kind


def expected(repo: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    schema_dir = repo / "shared/schemas"
    sources = sorted(p for p in schema_dir.glob(SOURCE_GLOB) if not p.name.startswith("langgraph-"))
    names = {p.name for p in sources}
    if names != EXPECTED_SOURCE_NAMES:
        raise SystemExit(f"[ERROR] Frozen batch schema template set differs: {sorted(names)!r}")
    rendered: dict[str, bytes] = {}
    entries: list[dict[str, Any]] = []
    for source_path in sources:
        source = json.loads(source_path.read_text(encoding="utf-8"))
        target_name, derived, kind = derive(source_path.name, source)
        target_rel = f"shared/schemas/{target_name}"
        data = canonical_bytes(derived)
        rendered[target_rel] = data
        entries.append({
            "source_schema": f"shared/schemas/{source_path.name}",
            "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "derived_schema": target_rel,
            "derived_sha256": sha_bytes(data),
            "transformation_kind": kind,
        })
    mapping = {
        "schema_version": 1,
        "status": "active",
        "purpose": "langgraph-instantiation-of-frozen-batch-collection-evidence-shapes",
        "adr": "docs/decisions/ADR-0011-langgraph-batch-evidence-schema-instantiation.md",
        "frozen_gate2a_contract_sha256": CONTRACT_SHA,
        "frozen_contract_changed": False,
        "prior_evidence_invalidated": False,
        "controlled_continuation_semantics_preserved": True,
        "gate2c_failure_semantics_introduced": False,
        "allowed_provenance_transformations": [
            "$id batch-* -> langgraph-batch-*",
            "exact provenance constant drupal_ai -> langgraph",
            "run-id regex prefix ^drupal_ai- -> ^langgraph-",
            "drupal-ai-model-output.schema.json -> langgraph-model-output.schema.json",
            "drupal-ai-run-state.schema.json -> langgraph-run-state.schema.json",
            "human-readable title Drupal AI -> LangGraph",
        ],
        "controlled_continuation_adaptations": [
            "batch-event adds continuation_interrupted without removing historical failure_injected",
            "batch-recovery failure-only fields are instantiated as controlled stop/resume fields required by Gate 2A continuation_policy",
        ],
        "schemas": entries,
    }
    rendered[MAP_REL] = canonical_bytes(mapping)
    return rendered, mapping


def write(repo: Path) -> None:
    rendered, mapping = expected(repo)
    for rel, data in rendered.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print(f"[PASS] Wrote {len(mapping['schemas'])} reproducible LangGraph batch schema instantiations.")
    print(f"[PASS] Mapping: {MAP_REL}")


def check(repo: Path) -> None:
    rendered, mapping = expected(repo)
    for rel, data in rendered.items():
        path = repo / rel
        if not path.is_file():
            raise SystemExit(f"[ERROR] Missing derived schema/mapping: {rel}")
        if path.read_bytes() != data:
            raise SystemExit(f"[ERROR] Derived schema/mapping is not reproducible: {rel}")
    kinds: set[str] = set()
    for entry in mapping["schemas"]:
        source = repo / entry["source_schema"]
        derived = repo / entry["derived_schema"]
        kinds.add(entry["transformation_kind"])
        if hashlib.sha256(source.read_bytes()).hexdigest() != entry["source_sha256"]:
            raise SystemExit(f"[ERROR] Source batch schema changed: {entry['source_schema']}")
        if hashlib.sha256(derived.read_bytes()).hexdigest() != entry["derived_sha256"]:
            raise SystemExit(f"[ERROR] Derived batch schema hash differs: {entry['derived_schema']}")
        text = derived.read_text(encoding="utf-8")
        if "drupal_ai" in text or "drupal-ai-model-output.schema.json" in text:
            raise SystemExit(f"[ERROR] Drupal-AI provenance leaked into LangGraph schema: {entry['derived_schema']}")
    expected_kinds = {
        "provenance-only",
        "controlled-continuation-event-adaptation",
        "controlled-continuation-recovery-adaptation",
    }
    if not expected_kinds.issubset(kinds):
        raise SystemExit(f"[ERROR] Derived schema transformation classes differ: {sorted(kinds)}")
    if mapping["frozen_contract_changed"] is not False or mapping["prior_evidence_invalidated"] is not False:
        raise SystemExit("[ERROR] Schema map incorrectly changes frozen contract or invalidates prior evidence")
    if mapping["controlled_continuation_semantics_preserved"] is not True or mapping["gate2c_failure_semantics_introduced"] is not False:
        raise SystemExit("[ERROR] Schema map does not preserve Gate 2A/Gate 2C semantic boundary")
    print(f"[PASS] {len(mapping['schemas'])} LangGraph batch schema instantiations are reproducible and mapped by transformation class.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = ap.parse_args()
    repo = Path(args.repo).resolve()
    if args.write:
        write(repo)
    else:
        check(repo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
