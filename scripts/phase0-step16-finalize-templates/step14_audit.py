#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def fail(message: str) -> None:
    print(f"[ERROR] {message}")
    raise SystemExit(1)


def require(path: Path, needles: list[str]) -> str:
    if not path.is_file():
        fail(f"Missing contract file: {path}")
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            fail(f"{path} is missing required text: {needle}")
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    root = parser.parse_args().root.resolve()
    spec = require(
        root / "EXPERIMENT_SPEC.md",
        [
            "**Contract status:** frozen — version 1.1",
            "**Model status:** frozen for experiment after Step 16",
            "gpt-4.1-mini-2025-04-14",
            "ChatInput::setChatStructuredJsonSchema",
            "ChatOpenAI.with_structured_output",
            "CrewAI `LLM`",
            "Base64",
            "after target **6**",
            "phase0_fixture",
        ],
    )
    if "PENDING_STEP_16" in spec:
        fail("The amended contract still contains PENDING_STEP_16")
    require(root / "PLAN.md", ["- [x] Step 14", "- [x] Step 16", "- [ ] Step 17"])
    require(root / "README.md", ["Steps 13–15 are complete", "Step 16 is complete", "Step 17"])
    require(root / "shared/prompts/PROMPTS.md", ["Contract version:** 1.1", "Base64-encoded PNG"])
    require(root / "docs/decisions/ADR-0001-freeze-experiment-contract.md", ["- **Status:** Accepted"])
    require(root / "docs/decisions/ADR-0002-freeze-model-after-vision-preflight.md", ["- **Status:** Accepted"])
    require(
        root / "docs/decisions/ADR-0005-repair-get-image-context-tool-result-schema.md",
        ["- **Status:** Accepted", "data` property", "image-context.schema.json"],
    )
    schemas = [
        "target.schema.json",
        "image-context.schema.json",
        "recommendation.schema.json",
        "tool-result.schema.json",
        "run-state.schema.json",
        "vision-spike-output.schema.json",
    ]
    for name in schemas:
        path = root / "shared/schemas" / name
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            fail(f"Invalid schema {path}: {exc}")
        if value.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            fail(f"Schema does not declare draft 2020-12: {path}")
    tool_result = json.loads(
        (root / "shared/schemas/tool-result.schema.json").read_text(encoding="utf-8")
    )
    context_branches = [
        branch
        for branch in tool_result.get("allOf", [])
        if branch.get("if", {}).get("properties", {}).get("tool_name", {}).get("const")
        == "get_image_context"
    ]
    if len(context_branches) != 1:
        fail("tool-result schema must have exactly one get_image_context branch")
    context_data = (
        context_branches[0]
        .get("then", {})
        .get("properties", {})
        .get("data")
    )
    if context_data != {"$ref": "image-context.schema.json"}:
        fail("get_image_context data must directly reference image-context.schema.json")
    manifest = root / "docs/decisions/step14-contract-sha256.txt"
    if not manifest.is_file() or manifest.stat().st_size == 0:
        fail("Frozen contract manifest is missing")
    print("[OK] Step 14/16 amended experiment contract audit passed in frozen version 1.1 state.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
