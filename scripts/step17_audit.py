#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

EXPECTED_TESTS = {
    "S17-AUTH-001",
    "S17-AUTH-002",
    "S17-AUTH-003",
    "S17-COUNT-001",
    "S17-STATE-001",
    "S17-SCHEMA-001",
    "S17-SCHEMA-002",
    "S17-ORDER-001",
    "S17-IDENTITY-001",
    "S17-DUPLICATE-001",
    "S17-REPEAT-001",
    "S17-NOAI-001",
    "S17-MUTATION-001",
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


def run(root: Path, command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd or root, text=True, capture_output=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()

    required = [
        root / "drupal/web/modules/custom/agentic_harness_tools/agentic_harness_tools.info.yml",
        root / "drupal/web/modules/custom/agentic_harness_tools/agentic_harness_tools.permissions.yml",
        root / "drupal/web/modules/custom/agentic_harness_tools/agentic_harness_tools.routing.yml",
        root / "drupal/web/modules/custom/agentic_harness_tools/agentic_harness_tools.services.yml",
        root / "drupal/web/modules/custom/agentic_harness_tools/src/Controller/ToolController.php",
        root / "drupal/web/modules/custom/agentic_harness_tools/src/Service/ImageReviewFinder.php",
        root / "drupal/scripts/phase0-step17.php",
        root / "shared/drupal_client/client.py",
        root / "shared/drupal_client/README.md",
        root / "scripts/step17_evidence.py",
    ]
    for path in required:
        if not path.is_file() or path.stat().st_size == 0:
            fail(f"Missing Step 17 implementation file: {path}")
    ok("Step 17 Drupal route, helper, shared client, and evidence validator are installed.")

    # Evidence-alignment corrections from the Step 16 review.
    spec = (root / "EXPERIMENT_SPEC.md").read_text(encoding="utf-8")
    adr2 = (root / "docs/decisions/ADR-0002-freeze-model-after-vision-preflight.md").read_text(encoding="utf-8")
    versions = (root / "VERSIONS.md").read_text(encoding="utf-8")
    step16_audit = (root / "scripts/step16_audit.py").read_text(encoding="utf-8")
    for needle in (
        "`ai_agent:html_to_markdown` without executing the plugin",
        "`calculate_probe` and returned `140`",
    ):
        if needle not in spec:
            fail(f"EXPERIMENT_SPEC.md is missing the exact Step 16 tool-probe correction: {needle}")
    if "ai_agent:html_to_markdown" not in adr2 or "returning `140`" not in adr2:
        fail("ADR-0002 is missing the exact framework-specific tool-probe correction")
    if "Ubuntu 24.04.4 LTS\nunknown" in versions:
        fail("VERSIONS.md still contains the unresolved Ubuntu codename line")
    if "Step 16 tool evidence matches the exact observed" not in step16_audit:
        fail("Step 16 audit was not strengthened to assert the exact observed tool probes")
    ok("Step 16 records now match the retained Drupal, LangChain, and CrewAI evidence.")

    contract = run(root, ["sha256sum", "-c", "docs/decisions/step14-contract-sha256.txt"])
    if contract.returncode != 0:
        fail("Contract hash manifest failed after the Step 16 record repair: " + contract.stdout + contract.stderr)
    ok("Frozen contract hash manifest verifies after the evidence-alignment correction.")

    inspect = run(
        root,
        ["ddev", "drush", "--quiet", "php:script", "scripts/phase0-step17.php", "--", "inspect"],
        cwd=root / "drupal",
    )
    if inspect.returncode != 0:
        fail("Drupal Step 17 inspection failed: " + inspect.stdout + inspect.stderr)
    try:
        inspect_json = json.loads(inspect.stdout)
    except json.JSONDecodeError as exc:
        fail(f"Drupal Step 17 inspection returned invalid JSON: {exc}")
    if inspect_json.get("status") != "pass" or inspect_json.get("editor_permission_denied") is not True:
        fail("Drupal Step 17 route or permission scope did not pass inspection")
    ok("Drupal route is enabled, agent-scoped, and denied to editor_dana.")

    latest_file = root / "evidence/logs/tools/find-images/STEP17-LATEST.txt"
    if not latest_file.is_file():
        fail("No passing Step 17 run is recorded. Run Step 17 first.")
    run_rel = latest_file.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"evidence/logs/tools/find-images/step17-[A-Za-z0-9._-]+", run_rel):
        fail(f"STEP17-LATEST contains an unexpected path: {run_rel}")
    run_dir = root / run_rel
    summary = load_json(run_dir / "summary.json")
    passing = {row.get("test_id") for row in summary.get("tests", []) if row.get("status") == "pass"}
    if summary.get("status") != "pass" or summary.get("passed") != 13 or summary.get("total") != 13:
        fail("Latest Step 17 run is not a 13/13 pass")
    if passing != EXPECTED_TESTS:
        fail(f"Unexpected Step 17 passing test set: {sorted(passing)}")
    ok("Latest Step 17 evidence contains all thirteen passing controls.")

    response = load_json(run_dir / "response.json")
    targets = response.get("data", {}).get("targets", [])
    if response.get("tool_name") != "find_images_needing_review" or len(targets) != 12:
        fail("Latest response does not contain the exact 12-target discovery result")
    missing = sum(1 for target in targets if target.get("target_state") == "missing")
    poor = sum(1 for target in targets if target.get("target_state") == "poor")
    if (missing, poor) != (9, 3):
        fail(f"Unexpected target distribution: missing={missing}, poor={poor}")
    ok("Discovery result is exactly 12 targets: 9 missing and 3 poor.")

    secret_patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
        re.compile(r"(?i)authorization\s*:\s*(?:bearer|basic)\s+(?!<redacted>)\S+"),
        re.compile(r"(?i)(?:password|OPENAI_API_KEY)\s*[=:]\s*(?!<redacted>)\S+"),
        re.compile(r"(?i)user\s*=\s*[\"'][^\"']+:[^\"']+[\"']"),
    ]
    for path in run_dir.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in secret_patterns:
            if pattern.search(text):
                fail(f"Potential unredacted credential in Step 17 evidence: {path}")
    ok("Step 17 evidence contains no recognized credential or Authorization-header pattern.")

    environment = load_json(run_dir / "environment.json")
    if environment.get("model_call_performed") is not False:
        fail("Step 17 environment evidence does not affirm a model-free run")
    for key in ("openai_api_key_present", "openai_candidate_model_present", "crewai_candidate_model_present"):
        if environment.get(key) is not False:
            fail(f"Step 17 environment evidence shows a model variable present: {key}")
    before = load_json(run_dir / "mutation-before.json")
    after = load_json(run_dir / "mutation-after.json")
    if (
        before.get("source_sha256") != after.get("source_sha256")
        or before.get("suggestion_count") != 0
        or after.get("suggestion_count") != 0
    ):
        fail("Step 17 did not preserve source state and zero suggestions")
    ok("Step 17 ran without model variables and without source mutation.")

    gitignore = (root / ".gitignore").read_text(encoding="utf-8")
    for rule in (
        "/drupal/.phase0-step17-runtime/",
        "/.phase0-step17-backups/",
        "/.phase0-step17-package-backups/",
    ):
        if rule not in gitignore:
            fail(f"Missing Step 17 ignore rule: {rule}")
    ok("Step 17 runtime and backup material is ignored by Git.")

    plan = (root / "PLAN.md").read_text(encoding="utf-8")
    finalized = "- [x] Step 17 non-AI `find_images_needing_review()` returns exactly 12 targets." in plan
    if finalized:
        readme = (root / "README.md").read_text(encoding="utf-8")
        claims = (root / "CLAIMS_REGISTER.md").read_text(encoding="utf-8")
        sources = (root / "SOURCES.md").read_text(encoding="utf-8")
        adr3 = root / "docs/decisions/ADR-0003-use-permission-scoped-discovery-route.md"
        if "Phase 0 is complete" not in readme or "Gate 0.5 is next" not in readme:
            fail("README.md does not identify Phase 0 completion and Gate 0.5")
        if "CLM-SHARED-001" not in claims or run_rel not in claims:
            fail("CLAIMS_REGISTER.md does not record the observed Step 17 claim")
        if "## Step 17 deterministic Drupal tool sources" not in sources:
            fail("SOURCES.md does not record the Step 17 official source foundations")
        if not adr3.is_file() or "- **Status:** Accepted" not in adr3.read_text(encoding="utf-8"):
            fail("ADR-0003 is missing or not accepted")
        ok("Step 17 is finalized in the plan, README, claims register, sources, and ADR.")
        print("[OK] Step 17 audit passed in finalized state.")
    else:
        print("[OK] Step 17 audit passed in ready-to-finalize state.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
