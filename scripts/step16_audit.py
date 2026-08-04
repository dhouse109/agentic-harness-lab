#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

EXPECTED_TESTS = {
    "INSPECT-DR-001",
    "FIXTURE-001",
    "VISION-DR-001",
    "TOOL-DR-001",
    "VISION-LG-001",
    "TOOL-LG-001",
    "VISION-CR-001",
    "TOOL-CR-001",
    "MUTATION-001",
}


def fail(message: str) -> None:
    print(f"[ERROR] {message}")
    raise SystemExit(1)


def ok(message: str) -> None:
    print(f"[OK] {message}")


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        fail(f"Missing JSON evidence: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON in {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"Expected JSON object in {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()

    required_files = [
        root / "shared/schemas/vision-spike-output.schema.json",
        root / "shared/prompts/STEP16_VISION_PROMPT.md",
        root / "drupal/scripts/phase0-step16.php",
        root / "langchain/preflight/step16_capability.py",
        root / "crewai/preflight/step16_capability.py",
    ]
    for path in required_files:
        if not path.is_file() or path.stat().st_size == 0:
            fail(f"Missing Step 16 implementation file: {path}")
    schema = load_json(root / "shared/schemas/vision-spike-output.schema.json")
    if schema.get("additionalProperties") is not False:
        fail("Step 16 schema must prohibit additional properties")
    if schema.get("required") != ["image_purpose", "proposed_alt_text", "context_alignment"]:
        fail("Step 16 schema does not freeze the three output properties")
    if schema.get("properties", {}).get("proposed_alt_text", {}).get("maxLength") != 250:
        fail("Step 16 schema must retain the 250-character experiment limit")
    ok("Step 16 capability files and strict output schema are installed.")

    latest_file = root / "evidence/logs/preflight/vision/STEP16-LATEST.txt"
    if not latest_file.is_file():
        fail("No passing Step 16 run is recorded. Run the capability spike first.")
    run_rel = latest_file.read_text(encoding="utf-8").strip()
    run_dir = root / run_rel
    summary = load_json(run_dir / "summary.json")
    passing = {row.get("test_id") for row in summary.get("tests", []) if row.get("status") == "pass"}
    if summary.get("status") != "pass" or summary.get("passed") != 9 or summary.get("total") != 9:
        fail("Latest Step 16 run is not a 9/9 direct pass")
    if passing != EXPECTED_TESTS:
        fail(f"Unexpected Step 16 passing test set: {sorted(passing)}")
    controls = summary.get("controls", {})
    if controls.get("model_id") != "gpt-4.1-mini-2025-04-14":
        fail("Step 16 did not use the approved dated candidate model")
    if not controls.get("image_sha256") or not controls.get("context_sha256"):
        fail("Step 16 summary is missing image or context hashes")
    ok("Latest Step 16 evidence contains all nine passing direct-capability checks.")

    secret_patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
        re.compile(r"(?i)authorization\s*:\s*(?:bearer|basic)\s+(?!<redacted>)\S+"),
        re.compile(r"(?i)OPENAI_API_KEY\s*[=:]\s*(?!<redacted>)\S+"),
    ]
    for path in run_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            fail(f"Raw image retained in evidence: {path}")
        text = path.read_text(encoding="utf-8", errors="replace")
        if "data:image/" in text and ";base64," in text:
            fail(f"Base64 image value retained in evidence: {path}")
        for pattern in secret_patterns:
            if pattern.search(text):
                fail(f"Potential unredacted credential in Step 16 evidence: {path}")
    ok("Step 16 evidence contains no retained Base64 image or recognized credential pattern.")

    mutation = load_json(run_dir / "MUTATION-001.json")
    if mutation.get("status") != "pass" or mutation.get("source_unchanged") is not True:
        fail("Step 16 did not prove Drupal source immutability")
    ok("Drupal Article state and suggestion count were unchanged by the capability spike.")

    gitignore = (root / ".gitignore").read_text(encoding="utf-8")
    for rule in (
        "/drupal/.phase0-step16-runtime/",
        "/langchain/.phase0-step16-runtime/",
        "/crewai/.phase0-step16-runtime/",
    ):
        if rule not in gitignore:
            fail(f"Missing Step 16 runtime ignore rule: {rule}")
    ok("Step 16 runtime images, fixture copies, and temporary responses are ignored by Git.")

    plan = (root / "PLAN.md").read_text(encoding="utf-8")
    finalized = "- [x] Step 16 image-plus-page-context capability passes or a fallback is recorded." in plan
    if finalized:
        spec = (root / "EXPERIMENT_SPEC.md").read_text(encoding="utf-8")
        versions = (root / "VERSIONS.md").read_text(encoding="utf-8")
        readme = (root / "README.md").read_text(encoding="utf-8")
        adr = root / "docs/decisions/ADR-0002-freeze-model-after-vision-preflight.md"
        if "**Contract status:** frozen — version 1.1" not in spec:
            fail("Finalized Step 16 requires experiment contract version 1.1")
        if "PENDING_STEP_16" in spec:
            fail("Finalized Step 16 still contains PENDING_STEP_16 fields")
        for needle in (
            "gpt-4.1-mini-2025-04-14",
            "frozen for experiment",
            "Base64",
            "ChatInput::setChatStructuredJsonSchema",
        ):
            if needle not in spec:
                fail(f"EXPERIMENT_SPEC.md is missing finalized Step 16 text: {needle}")
        if "| Candidate/frozen model | gpt-4.1-mini-2025-04-14 — frozen" not in versions:
            fail("VERSIONS.md does not mark the model frozen")
        if "Steps 13–15 are complete" not in readme or "Step 16 is complete" not in readme or "Step 17" not in readme:
            fail("README.md does not preserve Step 15 audit compatibility and identify Step 17")
        if not adr.is_file() or "- **Status:** Accepted" not in adr.read_text(encoding="utf-8"):
            fail("ADR-0002 is missing or not accepted")
        manifest = root / "docs/decisions/step14-contract-sha256.txt"
        if not manifest.is_file():
            fail("Updated contract hash manifest is missing")
        result = subprocess.run(
            ["sha256sum", "-c", str(manifest.relative_to(root))],
            cwd=root,
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            fail("Updated contract hash manifest failed verification: " + result.stdout + result.stderr)
        ok("Step 16 is finalized in the contract, ADR, versions, plan, README, and hash manifest.")
        print("[OK] Step 16 audit passed in finalized state.")
    else:
        print("[OK] Step 16 audit passed in ready-to-finalize state.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
