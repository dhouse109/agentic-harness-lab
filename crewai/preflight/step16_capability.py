from __future__ import annotations

import argparse
import base64
import hashlib
import inspect
import json
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from crewai import LLM
from pydantic import BaseModel, ConfigDict, Field


class VisionSpikeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_purpose: str = Field(min_length=1, max_length=500)
    proposed_alt_text: str = Field(min_length=1, max_length=250)
    context_alignment: str = Field(min_length=1, max_length=500)


def load_fixture(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data


def data_url(path: Path, mime_type: str) -> tuple[str, int, str]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    return f"data:{mime_type};base64,{base64.b64encode(raw).decode('ascii')}", len(raw), digest


def canonical_model() -> tuple[str, str]:
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required")
    canonical = os.environ.get("OPENAI_CANDIDATE_MODEL", "")
    if not canonical:
        raise SystemExit("OPENAI_CANDIDATE_MODEL is required")
    adapter = os.environ.get("CREWAI_CANDIDATE_MODEL", canonical)
    if adapter.removeprefix("openai/") != canonical:
        raise SystemExit("CREWAI_CANDIDATE_MODEL must identify the same underlying model")
    return canonical, adapter


def normalize_output(value: Any) -> dict[str, Any]:
    if isinstance(value, VisionSpikeOutput):
        return value.model_dump()
    if isinstance(value, BaseModel):
        return VisionSpikeOutput.model_validate(value.model_dump()).model_dump()
    if isinstance(value, dict):
        return VisionSpikeOutput.model_validate(value).model_dump()
    text = str(value).strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    return VisionSpikeOutput.model_validate_json(text).model_dump()


def prompt(fixture: dict[str, Any]) -> str:
    return f"""PAGE CONTEXT
Title: {fixture['article_title']}
Body: {fixture['article_body_plain']}

IMAGE METADATA
Filename: {fixture['filename']}
MIME type: {fixture['mime_type']}
Dimensions: {fixture['width']} x {fixture['height']}

TASK
Inspect the attached image with the page context. Return image_purpose, proposed_alt_text, and
context_alignment. Keep proposed_alt_text at 250 characters or fewer, do not repeat the filename,
and return no extra properties."""


def build_llm(adapter: str, *, response_format: Any | None = None) -> tuple[LLM, str]:
    kwargs: dict[str, Any] = {"model": adapter, "temperature": 0.0}
    mechanism = "none"
    if response_format is not None:
        # CrewAI 1.15.x exposes response_format as an LLM configuration field.
        # Passing the Pydantic model here keeps the multimodal request and the
        # structured response on the genuine CrewAI provider path.
        kwargs["response_format"] = response_format
        mechanism = "CrewAI LLM(response_format=Pydantic model)"
    return LLM(**kwargs), mechanism


def vision(args: argparse.Namespace) -> None:
    fixture = load_fixture(args.fixture)
    image_url, byte_length, digest = data_url(args.image, fixture["mime_type"])
    if digest != fixture["image_sha256"]:
        raise SystemExit("Fixture image hash mismatch")
    canonical, adapter = canonical_model()
    llm, mechanism = build_llm(adapter, response_format=VisionSpikeOutput)
    messages = [
        {
            "role": "system",
            "content": (
                "You are performing a bounded capability check for an accessibility workflow. "
                "Use only the supplied synthetic image and page context and return only the requested object."
            ),
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt(fixture)},
                {"type": "image_url", "image_url": {"url": image_url, "detail": "auto"}},
            ],
        },
    ]
    if mechanism == "none":
        raise SystemExit("CrewAI response-format configuration was not installed")
    response = llm.call(messages=messages)
    output = normalize_output(response)
    print(
        json.dumps(
            {
                "test_id": "VISION-CR-001",
                "status": "pass",
                "framework": "crewai",
                "model_id": canonical,
                "adapter_model": adapter,
                "temperature": 0.0,
                "image_representation": "base64_data_url",
                "image_detail": "auto",
                "image_byte_length": byte_length,
                "image_sha256": digest,
                "context_sha256": fixture["context_sha256"],
                "structured_output_mechanism": mechanism,
                "output": output,
                "base64_retained": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def extract_tool_calls(response: Any) -> list[dict[str, Any]]:
    if isinstance(response, dict):
        if isinstance(response.get("tool_calls"), list):
            return response["tool_calls"]
        message = response.get("message")
        if isinstance(message, dict) and isinstance(message.get("tool_calls"), list):
            return message["tool_calls"]
    for attr in ("tool_calls", "tools"):
        value = getattr(response, attr, None)
        if isinstance(value, list):
            return [item if isinstance(item, dict) else vars(item) for item in value]
    return []


def tool_check(args: argparse.Namespace) -> None:
    del args
    canonical, adapter = canonical_model()
    llm, _ = build_llm(adapter)
    signature = inspect.signature(llm.call)
    for required in ("tools", "available_functions"):
        if required not in signature.parameters:
            raise SystemExit(f"Pinned CrewAI LLM.call path does not expose {required}")

    tool_schema = {
        "type": "function",
        "function": {
            "name": "calculate_probe",
            "description": "Evaluate the single frozen Step 16 arithmetic expression.",
            "strict": True,
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "required": ["expression"],
                "properties": {
                    "expression": {
                        "type": "string",
                        "enum": ["20*(4+3)"],
                    }
                },
            },
        },
    }

    executions: list[str] = []

    def calculate_probe(expression: str) -> str:
        executions.append(expression)
        if expression != "20*(4+3)":
            raise ValueError("Unexpected Step 16 expression")
        return "140"

    response = llm.call(
        messages=[
            {
                "role": "user",
                "content": "Call calculate_probe exactly once with expression 20*(4+3). Do not answer directly.",
            }
        ],
        tools=[tool_schema],
        available_functions={"calculate_probe": calculate_probe},
    )
    if executions != ["20*(4+3)"]:
        raise SystemExit(f"CrewAI did not execute exactly one required tool call: {executions!r}")
    if str(response).strip() != "140":
        raise SystemExit(f"CrewAI tool returned an unexpected result: {response!r}")

    print(
        json.dumps(
            {
                "test_id": "TOOL-CR-001",
                "status": "pass",
                "framework": "crewai",
                "model_id": canonical,
                "adapter_model": adapter,
                "temperature": 0.0,
                "tool_name": "calculate_probe",
                "tool_call_count": 1,
                "tool_call_detected": True,
                "tool_function_executed": True,
                "tool_result": "140",
                "tool_mechanism": "CrewAI LLM.call(tools=..., available_functions=...)",
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
