#!/usr/bin/env python3
"""Apply evidence-alignment corrections discovered during Step 16 review.

This does not change the frozen model, temperature, image representation, or
capability result. It corrects the written tool-probe description, strengthens
the Step 16 audit, and removes a stray unresolved Ubuntu codename line.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


SPEC_OLD = "| Tool-calling mechanism | Drupal `ChatInput::setChatTools(ToolsInput)`; LangChain `ChatOpenAI.bind_tools(strict=true)`; CrewAI `LLM.call(tools=...)` — harmless calculator probe in every path |"
SPEC_NEW = "| Tool-calling mechanism | Drupal `ChatInput::setChatTools(ToolsInput)` detected a normalized call to installed `ai_agent:html_to_markdown` without executing the plugin; LangChain `ChatOpenAI.bind_tools(strict=true)` and CrewAI `LLM.call(tools=..., available_functions=...)` each executed deterministic `calculate_probe` and returned `140` |"

ADR_OLD = "- Tool capability: the pinned Drupal AI, LangChain, and CrewAI provider wrappers each completed the\n  harmless calculator probe"
ADR_NEW = "- Tool capability: Drupal AI detected a normalized call to the installed, non-mutating\n  `ai_agent:html_to_markdown` FunctionCall plugin without executing it; LangChain and CrewAI each\n  exposed and executed deterministic `calculate_probe`, returning `140`"

AUDIT_MARKER = "    controls = summary.get(\"controls\", {})\n"
AUDIT_INSERT = '''    drupal_tool = load_json(run_dir / "TOOL-DR-001.json")
    if (
        drupal_tool.get("status") != "pass"
        or drupal_tool.get("tool_plugin_id") != "ai_agent:html_to_markdown"
        or drupal_tool.get("tool_call_detected") is not True
    ):
        fail("Drupal Step 16 tool evidence does not record ai_agent:html_to_markdown call detection")
    langchain_tool = load_json(run_dir / "TOOL-LG-001.json")
    if (
        langchain_tool.get("status") != "pass"
        or langchain_tool.get("tool_name") != "calculate_probe"
        or str(langchain_tool.get("tool_result")) != "140"
        or langchain_tool.get("tool_function_executed") is not True
    ):
        fail("LangChain Step 16 tool evidence does not record calculate_probe execution to 140")
    crewai_tool = load_json(run_dir / "TOOL-CR-001.json")
    if (
        crewai_tool.get("status") != "pass"
        or crewai_tool.get("tool_name") != "calculate_probe"
        or str(crewai_tool.get("tool_result")) != "140"
        or crewai_tool.get("tool_function_executed") is not True
    ):
        fail("CrewAI Step 16 tool evidence does not record calculate_probe execution to 140")
    ok("Step 16 tool evidence matches the exact observed Drupal, LangChain, and CrewAI probes.")

'''


def replace_once(text: str, old: str, new: str, label: str) -> tuple[str, str]:
    if new in text:
        return text, "already-correct"
    if old not in text:
        raise RuntimeError(f"Could not find expected {label} text; refusing an unguarded edit.")
    if text.count(old) != 1:
        raise RuntimeError(f"Expected exactly one {label} occurrence; found {text.count(old)}.")
    return text.replace(old, new, 1), "patched"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def regenerate_manifest(root: Path) -> None:
    manifest = root / "docs/decisions/step14-contract-sha256.txt"
    if not manifest.is_file():
        raise RuntimeError(f"Missing contract hash manifest: {manifest}")
    paths: list[str] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise RuntimeError(f"Malformed contract manifest line: {line}")
        paths.append(parts[1].strip())
    output = []
    for relative in paths:
        path = root / relative
        if not path.is_file():
            raise RuntimeError(f"Contract manifest path is missing: {relative}")
        output.append(f"{sha256_file(path)}  {relative}")
    manifest.write_text("\n".join(output) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()

    files = {
        "spec": root / "EXPERIMENT_SPEC.md",
        "adr": root / "docs/decisions/ADR-0002-freeze-model-after-vision-preflight.md",
        "versions": root / "VERSIONS.md",
        "audit": root / "scripts/step16_audit.py",
        "manifest": root / "docs/decisions/step14-contract-sha256.txt",
    }
    for label, path in files.items():
        if not path.is_file():
            raise SystemExit(f"[ERROR] Missing {label} file: {path}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = root / ".phase0-step17-backups" / f"step16-record-repair-{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    for path in files.values():
        destination = backup_dir / path.relative_to(root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)

    changes: dict[str, str] = {}
    try:
        spec_text, changes["EXPERIMENT_SPEC.md"] = replace_once(
            files["spec"].read_text(encoding="utf-8"), SPEC_OLD, SPEC_NEW, "experiment-spec tool mechanism"
        )
        files["spec"].write_text(spec_text, encoding="utf-8")

        adr_text, changes["ADR-0002"] = replace_once(
            files["adr"].read_text(encoding="utf-8"), ADR_OLD, ADR_NEW, "ADR tool capability"
        )
        files["adr"].write_text(adr_text, encoding="utf-8")

        versions_text = files["versions"].read_text(encoding="utf-8")
        if "Ubuntu 24.04.4 LTS\nunknown" in versions_text:
            versions_text = versions_text.replace("Ubuntu 24.04.4 LTS\nunknown", "Ubuntu 24.04.4 LTS", 1)
            changes["VERSIONS.md"] = "patched"
        elif "Ubuntu 24.04.4 LTS" in versions_text and "\nunknown |" not in versions_text:
            changes["VERSIONS.md"] = "already-correct"
        else:
            raise RuntimeError("Unexpected Ubuntu version row; refusing an unguarded edit.")
        files["versions"].write_text(versions_text, encoding="utf-8")

        audit_text = files["audit"].read_text(encoding="utf-8")
        if "Step 16 tool evidence matches the exact observed" in audit_text:
            changes["scripts/step16_audit.py"] = "already-correct"
        else:
            if audit_text.count(AUDIT_MARKER) != 1:
                raise RuntimeError("Could not locate the unique Step 16 controls marker for audit strengthening.")
            audit_text = audit_text.replace(AUDIT_MARKER, AUDIT_INSERT + AUDIT_MARKER, 1)
            files["audit"].write_text(audit_text, encoding="utf-8")
            changes["scripts/step16_audit.py"] = "patched"

        regenerate_manifest(root)
        changes["contract-hash-manifest"] = "regenerated"
    except Exception:
        # Restore every guarded file before surfacing the failure.
        for path in files.values():
            source = backup_dir / path.relative_to(root)
            if source.is_file():
                shutil.copy2(source, path)
        raise

    report = {
        "status": "pass",
        "backup_dir": str(backup_dir.relative_to(root)),
        "changes": changes,
        "frozen_controls_changed": False,
        "corrections": [
            "record exact Step 16 framework-specific tool probes",
            "assert exact tool evidence in Step 16 audit",
            "remove unresolved Ubuntu codename line",
        ],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
