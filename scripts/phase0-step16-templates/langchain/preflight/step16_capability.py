from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ConfigDict, Field


class VisionSpikeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_purpose: str = Field(min_length=1, max_length=500)
    proposed_alt_text: str = Field(min_length=1, max_length=250)
    context_alignment: str = Field(min_length=1, max_length=500)


@tool

def calculate_probe(expression: str) -> str:
    """Evaluate the single allowed Step 16 arithmetic expression."""
    normalized = "".join(expression.split())
    if normalized not in {"20*(4+3)", "20*(3+4)"}:
        raise ValueError("Only the frozen Step 16 expression is allowed")
    return "140"


def load_fixture(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "article_title",
        "article_body_plain",
        "filename",
        "mime_type",
        "width",
        "height",
        "image_sha256",
        "context_sha256",
    }
    missing = sorted(required - data.keys())
    if missing:
        raise SystemExit(f"Fixture is missing fields: {missing}")
    return data


def image_data_url(path: Path, mime_type: str) -> tuple[str, int, str]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    return f"data:{mime_type};base64,{base64.b64encode(raw).decode('ascii')}", len(raw), digest


def prompt_text(fixture: dict[str, Any]) -> str:
    return f"""PAGE CONTEXT
Title: {fixture['article_title']}
Body: {fixture['article_body_plain']}

IMAGE METADATA
Filename: {fixture['filename']}
MIME type: {fixture['mime_type']}
Dimensions: {fixture['width']} x {fixture['height']}

TASK
Inspect the attached image together with the page context. Return image_purpose, proposed_alt_text,
and context_alignment. The proposed_alt_text must be concise, contextual, no more than 250
characters, must not repeat the filename, and must not begin with image of, photo of, picture of,
graphic of, Here is, or Alt text:. Return no properties beyond the schema."""


def model() -> ChatOpenAI:
    model_id = os.environ.get("OPENAI_CANDIDATE_MODEL", "")
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required")
    if not model_id:
        raise SystemExit("OPENAI_CANDIDATE_MODEL is required")
    return ChatOpenAI(model=model_id, temperature=0.0)


def vision(args: argparse.Namespace) -> None:
    fixture = load_fixture(args.fixture)
    data_url, byte_length, digest = image_data_url(args.image, fixture["mime_type"])
    if digest != fixture["image_sha256"]:
        raise SystemExit("Fixture image hash does not match extracted metadata")

    structured = model().with_structured_output(
        VisionSpikeOutput,
        method="json_schema",
        strict=True,
    )
    result = structured.invoke(
        [
            SystemMessage(
                content=(
                    "You are performing a bounded capability check for an accessibility workflow. "
                    "Use only the supplied synthetic image and page context. Do not infer real-world "
                    "facts. Return only the requested structured object."
                )
            ),
            HumanMessage(
                content=[
                    {"type": "text", "text": prompt_text(fixture)},
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url, "detail": "auto"},
                    },
                ]
            ),
        ]
    )
    parsed = result if isinstance(result, VisionSpikeOutput) else VisionSpikeOutput.model_validate(result)
    print(
        json.dumps(
            {
                "test_id": "VISION-LG-001",
                "status": "pass",
                "framework": "langchain",
                "model_id": os.environ["OPENAI_CANDIDATE_MODEL"],
                "temperature": 0.0,
                "image_representation": "base64_data_url",
                "image_detail": "auto",
                "image_byte_length": byte_length,
                "image_sha256": digest,
                "context_sha256": fixture["context_sha256"],
                "structured_output_mechanism": "ChatOpenAI.with_structured_output(method=json_schema, strict=true)",
                "output": parsed.model_dump(),
                "base64_retained": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def tool_check(args: argparse.Namespace) -> None:
    del args
    bound = model().bind_tools([calculate_probe], strict=True, tool_choice="calculate_probe")
    response = bound.invoke(
        "Use the calculate_probe tool exactly once to calculate 20 * (4 + 3). Do not answer without the tool."
    )
    calls = list(response.tool_calls or [])
    if len(calls) != 1 or calls[0].get("name") != "calculate_probe":
        raise SystemExit(f"Expected one calculate_probe call, received: {calls!r}")
    output = calculate_probe.invoke(calls[0].get("args", {}))
    if str(output) != "140":
        raise SystemExit(f"Unexpected tool output: {output!r}")
    print(
        json.dumps(
            {
                "test_id": "TOOL-LG-001",
                "status": "pass",
                "framework": "langchain",
                "model_id": os.environ["OPENAI_CANDIDATE_MODEL"],
                "temperature": 0.0,
                "tool_name": "calculate_probe",
                "tool_call_count": 1,
                "tool_call_detected": True,
                "tool_function_executed": True,
                "tool_result": "140",
                "tool_mechanism": "ChatOpenAI.bind_tools(strict=true, forced tool choice)",
            },
            sort_keys=True,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["vision", "tool"])
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--image", type=Path)
    args = parser.parse_args()
    if args.mode == "vision":
        if args.fixture is None or args.image is None:
            parser.error("vision requires --fixture and --image")
        vision(args)
    else:
        tool_check(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
