#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

MODEL_ID = "gpt-4.1-mini-2025-04-14"


def fail(message: str) -> None:
    print(f"[ERROR] {message}")
    raise SystemExit(1)


def backup(root: Path, paths: list[Path]) -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = root / ".phase0-step16-backups" / stamp
    counter = 0
    while target.exists():
        counter += 1
        target = root / ".phase0-step16-backups" / f"{stamp}-{counter}"
    for path in paths:
        if not path.exists():
            continue
        rel = path.relative_to(root)
        destination = target / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    return target


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"Expected JSON object: {path}")
    return value


def replace_required(text: str, old: str, new: str, path: Path) -> str:
    if old not in text:
        fail(f"Refusing to update {path}; expected text was not found: {old}")
    return text.replace(old, new, 1)


def replace_table_row(text: str, component: str, replacement: str, path: Path) -> str:
    pattern = re.compile(rf"^\| {re.escape(component)} \|.*$", re.M)
    if not pattern.search(text):
        fail(f"Missing {component} row in {path}")
    return pattern.sub(replacement, text, count=1)


def update_spec(root: Path, summary: dict[str, Any], evidence_rel: str) -> None:
    path = root / "EXPERIMENT_SPEC.md"
    text = path.read_text(encoding="utf-8")
    text = replace_required(text, "**Contract status:** frozen — version 1.0", "**Contract status:** frozen — version 1.1", path)
    text = replace_required(
        text,
        "**Model status:** candidate — pending Step 16 vision and tool-path preflight",
        "**Model status:** frozen for experiment after Step 16",
        path,
    )
    text = replace_required(
        text,
        "**Allowed deferred model fields:** exact model ID, confirmed structured-output mechanism, confirmed tool-calling mechanism, and image-input representation",
        f"**Step 16 decision:** direct image-plus-page-context capability passed; evidence `{evidence_rel}`",
        path,
    )
    controls = summary["controls"]
    mechanisms = controls["mechanisms"]
    structured = (
        "Drupal `ChatInput::setChatStructuredJsonSchema(strict=true)`; "
        "LangChain `ChatOpenAI.with_structured_output(method=json_schema, strict=true)`; "
        "CrewAI `LLM` response-format pathway recorded in Step 16 evidence"
    )
    tools = (
        "Drupal `ChatInput::setChatTools(ToolsInput)`; LangChain `ChatOpenAI.bind_tools(strict=true)`; "
        "CrewAI `LLM.call(tools=...)` — harmless calculator probe in every path"
    )
    image = (
        "Inline identical PNG bytes (same SHA-256): Base64 data URL with `detail=auto` in Python wrappers; "
        "Drupal AI `ImageFile` over the same bytes, normalized by the OpenAI provider"
    )
    text = replace_table_row(text, "Exact model ID", f"| Exact model ID | `{MODEL_ID}` — frozen snapshot |", path)
    text = replace_table_row(text, "Temperature", "| Temperature | `0.0` — frozen |", path)
    text = replace_table_row(text, "Structured-output mechanism", f"| Structured-output mechanism | {structured} |", path)
    text = replace_table_row(text, "Tool-calling mechanism", f"| Tool-calling mechanism | {tools} |", path)
    text = replace_table_row(text, "Image-input representation", f"| Image-input representation | {image} |", path)
    text = replace_table_row(text, "Model status", f"| Model status | frozen for experiment; Step 16 direct capability pass at `{evidence_rel}` |", path)
    marker = "A model-selection change after Step 16 is a material experiment change."
    addition = f"""### Step 16 freeze result

The direct capability spike passed through the pinned Drupal AI, LangChain, and CrewAI pathways using
one model snapshot, temperature `0.0`, the same synthetic PNG bytes, and the same page-context hash.
The full Base64 value and all credentials remained runtime-only. See `{evidence_rel}` and
`docs/decisions/ADR-0002-freeze-model-after-vision-preflight.md`.

{marker}"""
    text = replace_required(text, marker, addition, path)
    if "PENDING_STEP_16" in text:
        fail("EXPERIMENT_SPEC.md still contains PENDING_STEP_16 after update")
    path.write_text(text, encoding="utf-8")


def update_prompts(root: Path, decision_date: str) -> None:
    path = root / "shared/prompts/PROMPTS.md"
    text = path.read_text(encoding="utf-8")
    text = replace_required(text, "**Contract version:** 1.0", "**Contract version:** 1.1", path)
    text = replace_required(
        text,
        "**Status:** frozen with `EXPERIMENT_SPEC.md`; exact model transport remains the controlled Step 16 decision",
        "**Status:** frozen with `EXPERIMENT_SPEC.md`; model transport and inline-image representation were frozen by ADR-0002",
        path,
    )
    text = text.replace(
        "Image input: supplied using the single Step 16-approved representation",
        "Image input: identical PNG bytes, represented as a Base64-encoded PNG data URL with detail=auto or the Drupal AI ImageFile equivalent over the same bytes",
    )
    text = text.replace(
        "The image itself is attached or encoded using the one representation selected in Step 16. The\nsemantic facts above remain identical regardless of transport.",
        "The image itself uses the Step 16-frozen inline representation: identical PNG bytes and SHA-256,\nserialized as a Base64-encoded PNG data URL in the Python wrappers and as Drupal AI `ImageFile`\nover the same bytes. The semantic facts remain identical regardless of wrapper syntax.",
    )
    rows = {
        "| Drupal AI | pending implementation | pending | must be none | pending | pending |": f"| Drupal AI | `drupal/scripts/phase0-step16.php` | `ImageFile`, `setChatStructuredJsonSchema`, `setChatTools` | none; wrapper-only | Step 16 audit | {decision_date} |",
        "| LangChain / LangGraph | pending implementation | pending | must be none | pending | pending |": f"| LangChain / LangGraph | `langchain/preflight/step16_capability.py` | Base64 `image_url`, `with_structured_output`, `bind_tools` | none; wrapper-only | Step 16 audit | {decision_date} |",
        "| CrewAI | pending implementation | pending | must be none | pending | pending |": f"| CrewAI | `crewai/preflight/step16_capability.py` | Base64 `image_url`, `LLM` response format, `LLM.call(tools=...)` | none; wrapper-only | Step 16 audit | {decision_date} |",
    }
    for old, new in rows.items():
        text = replace_required(text, old, new, path)
    path.write_text(text, encoding="utf-8")


def update_versions(root: Path, environment: dict[str, Any], evidence_rel: str) -> None:
    path = root / "VERSIONS.md"
    text = path.read_text(encoding="utf-8")
    source_keys = {
        "Ubuntu": "ubuntu",
        "Docker": "docker",
        "DDEV": "ddev",
        "PHP": "php",
        "Drupal core": "drupal_core",
        "Drupal AI": "drupal_ai",
        "Drupal AI Agents": "drupal_ai_agents",
        "OpenAI provider": "drupal_openai_provider",
        "Drush": "drush",
    }
    values: dict[str, str] = {}
    for component, key in source_keys.items():
        value = str(environment.get(key, "")).strip()
        if not value:
            fail(f"Step 16 environment evidence is missing {key}; refusing to invent {component}")
        values[component] = value
    notes = {
        "Ubuntu": "WSL2 host distribution",
        "Docker": "Client/server captured locally",
        "DDEV": "Local Drupal runtime",
        "PHP": "DDEV web container",
        "Drupal core": "Composer lock and local command",
        "Drupal AI": "Pinned Composer release",
        "Drupal AI Agents": "Pinned patched supported release",
        "OpenAI provider": "Pinned Composer release used in Step 16",
        "Drush": "Pinned Composer release",
    }
    for component, value in values.items():
        replacement = f"| {component} | {value} | `{evidence_rel}/environment.json` | yes | {notes[component]} |"
        text = replace_table_row(text, component, replacement, path)
    text = replace_table_row(
        text,
        "Candidate/frozen model",
        f"| Candidate/frozen model | {MODEL_ID} — frozen | `{evidence_rel}` / ADR-0002 | yes | Direct image, strict structured-output, and tool-capability spike passed |",
        path,
    )
    path.write_text(text, encoding="utf-8")


def update_plan(root: Path) -> None:
    path = root / "PLAN.md"
    text = path.read_text(encoding="utf-8")
    text = replace_required(
        text,
        "- [ ] Step 16 image-plus-page-context capability passes or a fallback is recorded.",
        "- [x] Step 16 image-plus-page-context capability passes or a fallback is recorded.",
        path,
    )
    path.write_text(text, encoding="utf-8")


def update_readme(root: Path, evidence_rel: str) -> None:
    path = root / "README.md"
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r"## Current phase\n.*\Z", re.S)
    replacement = f"""## Current phase

Phase 0 Steps 13–15 are complete, and Step 16 is complete. The experiment model is frozen at
`{MODEL_ID}` with temperature `0.0`; the same synthetic PNG bytes and page-context hash passed the
Drupal AI, LangChain, and CrewAI capability paths. Step 17 is next: implement the first non-AI
`find_images_needing_review()` tool and prove that it returns exactly 12 field usages.

Verify Step 16 with:

```bash
bash scripts/run-phase0-step16.sh audit
```

Passing evidence: `{evidence_rel}`
"""
    if not pattern.search(text):
        fail("Could not locate README.md Current phase section")
    path.write_text(pattern.sub(replacement, text), encoding="utf-8")


def update_sources(root: Path, decision_date: str) -> None:
    path = root / "SOURCES.md"
    text = path.read_text(encoding="utf-8")
    marker = "## Step 16 verified capability sources"
    if marker in text:
        return
    appendix = f"""

{marker}

Retrieved {decision_date}. These official sources support the capability design; local Step 16 evidence
is still required to establish behavior in this repository.

| ID | Source title | Official? | URL | Version / branch | Capability supported | Caveat | Status |
|---|---|---:|---|---|---|---|---|
| SRC-S16-001 | GPT-4.1 mini model documentation | yes | https://platform.openai.com/docs/models/gpt-4.1-mini | `{MODEL_ID}` | Image input, function calling, structured outputs, snapshot pinning | Documentation does not prove wrapper behavior | verified source |
| SRC-S16-002 | Drupal AI provider testing | yes | https://project.pages.drupalcode.org/ai/1.4.x/developers/testing_an_ai_provider/ | AI 1.4.x | Vision, structured-data, and tool-use provider tests | Pair with pinned provider and local evidence | verified source |
| SRC-S16-003 | Drupal AI chat API | yes | https://project.pages.drupalcode.org/ai/developers/call_chat/ | provider API | `ChatInput`, `ChatMessage`, normalized output, image attachments | Wrapper specifics are version-sensitive | verified source |
| SRC-S16-004 | LangChain ChatOpenAI integration | yes | https://docs.langchain.com/oss/python/integrations/chat/openai | pinned lockfile | Image input, strict tool binding, native structured output | Pair with local locked version | verified source |
| SRC-S16-005 | CrewAI documentation | yes | https://docs.crewai.com/ | pinned lockfile | CrewAI LLM, agents, tools, and structured outputs | Exact low-level wrapper shape must be proven locally | verified source |
"""
    path.write_text(text.rstrip() + appendix + "\n", encoding="utf-8")


def write_adr(root: Path, template_root: Path, evidence_rel: str, decision_date: str) -> None:
    template = (template_root / "docs/decisions/ADR-0002-freeze-model-after-vision-preflight.md.template").read_text(encoding="utf-8")
    text = template.replace("{{decision_date}}", decision_date).replace("{{evidence_path}}", evidence_rel).replace("{{model_id}}", MODEL_ID)
    path = root / "docs/decisions/ADR-0002-freeze-model-after-vision-preflight.md"
    if path.exists() and path.read_text(encoding="utf-8") != text:
        fail(f"Refusing to overwrite unexpected ADR-0002: {path}")
    path.write_text(text, encoding="utf-8")


def install_post_step16_auditors(root: Path, finalize_templates: Path) -> None:
    for name in ("run-phase0-step14.sh", "step14_audit.py"):
        source = finalize_templates / name
        target = root / "scripts" / name
        shutil.copy2(source, target)
        target.chmod(0o755)


def write_manifest(root: Path) -> None:
    paths = [
        "EXPERIMENT_SPEC.md",
        "shared/schemas/target.schema.json",
        "shared/schemas/image-context.schema.json",
        "shared/schemas/recommendation.schema.json",
        "shared/schemas/tool-result.schema.json",
        "shared/schemas/run-state.schema.json",
        "shared/schemas/vision-spike-output.schema.json",
        "shared/prompts/PROMPTS.md",
        "shared/prompts/STEP16_VISION_PROMPT.md",
        "docs/decisions/ADR-0001-freeze-experiment-contract.md",
        "docs/decisions/ADR-0002-freeze-model-after-vision-preflight.md",
    ]
    lines = []
    for rel in paths:
        path = root / rel
        if not path.is_file():
            fail(f"Cannot hash missing contract file: {rel}")
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {rel}")
    manifest = root / "docs/decisions/step14-contract-sha256.txt"
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("template_root", type=Path)
    parser.add_argument("finalize_templates", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    run_dir = args.run_dir.resolve()
    summary = read_json(run_dir / "summary.json")
    if summary.get("status") != "pass" or summary.get("passed") != 9 or summary.get("total") != 9:
        fail("Finalize requires a passing 9/9 Step 16 direct run")
    if summary.get("controls", {}).get("model_id") != MODEL_ID:
        fail("Finalize requires the approved dated candidate model")
    environment = read_json(run_dir / "environment.json")
    evidence_rel = str(run_dir.relative_to(root))
    finished_at = str(summary.get("finished_at_utc", ""))
    decision_date = finished_at[:10] if re.fullmatch(r"\d{4}-\d{2}-\d{2}T.*", finished_at) else dt.datetime.now(dt.timezone.utc).date().isoformat()

    paths = [
        root / "EXPERIMENT_SPEC.md",
        root / "shared/prompts/PROMPTS.md",
        root / "VERSIONS.md",
        root / "PLAN.md",
        root / "README.md",
        root / "SOURCES.md",
        root / "scripts/run-phase0-step14.sh",
        root / "scripts/step14_audit.py",
        root / "docs/decisions/step14-contract-sha256.txt",
        root / "docs/decisions/ADR-0002-freeze-model-after-vision-preflight.md",
    ]
    backup_dir = backup(root, paths)
    update_spec(root, summary, evidence_rel)
    update_prompts(root, decision_date)
    update_versions(root, environment, evidence_rel)
    update_plan(root)
    update_readme(root, evidence_rel)
    update_sources(root, decision_date)
    write_adr(root, args.template_root.resolve(), evidence_rel, decision_date)
    install_post_step16_auditors(root, args.finalize_templates.resolve())
    write_manifest(root)
    print(f"[OK] Step 16 documents finalized. Backup: {backup_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
