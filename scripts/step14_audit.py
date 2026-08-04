#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REQUIRED_SCHEMAS = [
    "target.schema.json",
    "image-context.schema.json",
    "recommendation.schema.json",
    "tool-result.schema.json",
    "run-state.schema.json",
]


def fail(message: str) -> None:
    print(f"[ERROR] {message}", file=sys.stderr)
    raise SystemExit(1)


def ok(message: str) -> None:
    print(f"[OK] {message}")


def info(message: str) -> None:
    print(f"[INFO] {message}")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"Missing JSON Schema: {path}")
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON in {path}: {exc}")
    if not isinstance(data, dict):
        fail(f"Schema root must be an object: {path}")
    return data


def require_text(path: Path, needles: list[str]) -> str:
    if not path.is_file():
        fail(f"Missing required file: {path}")
    text = path.read_text(encoding="utf-8")
    normalized_text = re.sub(r"\s+", " ", text).strip()
    for needle in needles:
        normalized_needle = re.sub(r"\s+", " ", needle).strip()
        if needle not in text and normalized_needle not in normalized_text:
            fail(f"{path} is missing required text: {needle}")
    return text


def collect_refs(value: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref" and isinstance(child, str):
                refs.append(child)
            refs.extend(collect_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.extend(collect_refs(child))
    return refs


def audit(root: Path) -> None:
    spec_path = root / "EXPERIMENT_SPEC.md"
    plan_path = root / "PLAN.md"
    readme_path = root / "README.md"
    prompts_path = root / "shared/prompts/PROMPTS.md"
    adr_path = root / "docs/decisions/ADR-0001-freeze-experiment-contract.md"
    schema_dir = root / "shared/schemas"

    spec = require_text(
        spec_path,
        [
            "**Model status:** candidate — pending Step 16 vision and tool-path preflight",
            "identified by node UUID, Article revision ID",
            "field name, field delta, and file UUID.",
            "must not directly alter the source",
            "Approval records a human decision",
            "does not apply the alt text to the source Article",
            "after target **6**",
            "before target 7 begins",
            "20 deterministic seeded Article nodes",
            "12 deterministic target image-field usages",
            "`phase0_fixture` is reserved exclusively",
            "`drupal_ai`",
            "`langgraph`",
            "`crewai`",
            "250 Unicode characters",
            "shared/prompts/PROMPTS.md",
            "ADR-0002-freeze-model-after-vision-preflight.md",
        ],
    )

    ready = "**Contract status:** ready to freeze — version 1.0" in spec
    frozen = "**Contract status:** frozen — version 1.0" in spec
    if ready == frozen:
        fail("EXPERIMENT_SPEC.md must have exactly one recognized contract status.")
    state = "frozen" if frozen else "ready"
    info(f"Detected Step 14 contract state: {state}")

    if "TODO" in spec:
        fail("EXPERIMENT_SPEC.md still contains TODO text.")

    deferred_count = spec.count("PENDING_STEP_16")
    if deferred_count != 4:
        fail(f"Expected exactly 4 controlled PENDING_STEP_16 fields; found {deferred_count}.")
    ok("Experiment contract is complete with only the four controlled Step 16 deferrals.")

    plan = require_text(plan_path, ["Step 13 repository and evidence scaffold audited."])
    readme = require_text(readme_path, ["Agentic Harness Lab"])
    normalized_readme = re.sub(r"\s+", " ", readme).strip()
    if state == "ready":
        if "- [ ] Step 14 experiment specification written and frozen — contract installed; freeze pending." not in plan:
            fail("PLAN.md does not mark Step 14 as ready but not frozen.")
        if "ready for audit and freeze" not in normalized_readme:
            fail("README.md does not describe the ready-to-freeze state.")
    else:
        if "- [x] Step 14 experiment specification written and frozen." not in plan:
            fail("PLAN.md does not mark Step 14 complete.")
        if "experiment contract is frozen at version 1.0" not in normalized_readme:
            fail("README.md does not describe the frozen state.")
    ok("README.md and PLAN.md match the detected Step 14 state.")

    prompts = require_text(
        prompts_path,
        [
            "Frozen semantic system instruction",
            "Frozen semantic user template",
            "recommendation.schema.json#/$defs/model_output",
            "failure point after item 6",
            "Allowed framework-specific differences",
            "Prohibited prompt advantages",
        ],
    )
    if "TODO" in prompts:
        fail("PROMPTS.md contains TODO text.")
    ok("Semantic prompt-fairness contract is present.")

    adr = require_text(
        adr_path,
        [
            "- **Status:** Accepted",
            "failure-and-resume comparison",
            "step14-contract-sha256.txt",
            "ADR-0002-freeze-model-after-vision-preflight.md",
            "Make approval automatically update the Article",
        ],
    )
    if "TODO" in adr:
        fail("ADR-0001 contains TODO text.")
    ok("ADR-0001 records the freeze decision and planned Step 16 deferral.")

    schemas: dict[str, dict[str, Any]] = {}
    for name in REQUIRED_SCHEMAS:
        path = schema_dir / name
        schema = load_json(path)
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            fail(f"{name} does not declare JSON Schema 2020-12.")
        if schema.get("$id") != name:
            fail(f"{name} must use relative $id {name!r}.")
        schemas[name] = schema
    ok("All five JSON Schema files parse and declare draft 2020-12.")

    for source_name, schema in schemas.items():
        for ref in collect_refs(schema):
            local = ref.split("#", 1)[0]
            if local and "://" not in local and not (schema_dir / local).is_file():
                fail(f"{source_name} references missing local schema: {ref}")
    ok("All local JSON Schema references resolve to package files.")

    target = schemas["target.schema.json"]
    required_target = {
        "sequence", "node_uuid", "revision_id", "field_name", "delta", "file_uuid",
        "target_state", "existing_alt",
    }
    if not required_target.issubset(set(target.get("required", []))):
        fail("target.schema.json is missing exact field-usage identity requirements.")
    if target.get("properties", {}).get("field_name", {}).get("const") != "field_image":
        fail("target.schema.json must freeze field_name to field_image.")
    ok("Target schema preserves exact field-usage identity.")

    recommendation = schemas["recommendation.schema.json"]
    source_values = recommendation.get("properties", {}).get("source_framework", {}).get("enum")
    if source_values != ["drupal_ai", "langgraph", "crewai"]:
        fail("recommendation.schema.json must allow exactly the three comparative origins.")
    model_output = recommendation.get("$defs", {}).get("model_output", {})
    alt = model_output.get("properties", {}).get("proposed_alt_text", {})
    if alt.get("maxLength") != 250:
        fail("Model output must enforce the 250-character experiment limit.")
    ok("Recommendation schema separates model output from immutable provenance.")

    tool_result = schemas["tool-result.schema.json"]
    tools = tool_result.get("properties", {}).get("tool_name", {}).get("enum", [])
    expected_tools = [
        "find_images_needing_review",
        "get_image_context",
        "submit_recommendation",
        "get_recommendation_status",
    ]
    if tools != expected_tools:
        fail("tool-result.schema.json does not freeze the four semantic tool names in order.")
    tool_text = json.dumps(tool_result)
    if '"total_count": {"const": 12}' not in tool_text.replace(" ", ""):
        # Structural fallback because pretty/compact representation differs.
        found = False
        for branch in tool_result.get("allOf", []):
            props = branch.get("then", {}).get("properties", {}).get("data", {}).get("properties", {})
            if props.get("total_count", {}).get("const") == 12:
                found = True
        if not found:
            fail("find_images_needing_review result must freeze total_count to 12.")
    ok("Tool-result schema freezes the four tools and the 12-target result.")

    run_state = schemas["run-state.schema.json"]
    failure = run_state.get("properties", {}).get("failure_injection", {}).get("properties", {})
    if failure.get("after_item", {}).get("const") != 6:
        fail("run-state.schema.json must freeze failure injection after item 6.")
    if run_state.get("properties", {}).get("duplicate_count", {}).get("minimum") != 0:
        fail("run-state.schema.json must retain duplicate_count.")
    ok("Run-state schema freezes recovery state and failure point 6.")

    manifest = root / "docs/decisions/step14-contract-sha256.txt"
    if state == "frozen":
        if not manifest.is_file() or manifest.stat().st_size == 0:
            fail("Frozen state requires docs/decisions/step14-contract-sha256.txt.")
        ok("Frozen contract hash manifest exists.")
    elif manifest.exists():
        fail("Ready state must not retain a frozen contract hash manifest.")

    print(f"[OK] Step 14 audit passed in {state} state.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Phase 0 Step 14 contract files")
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    if not (root / "drupal").is_dir():
        fail(f"Not an agentic-harness-lab root: {root}")
    audit(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
