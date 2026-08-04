#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


ADR_TEXT = """# ADR-0003: Use a permission-scoped Drupal discovery route for the shared target tool

- **Status:** Accepted
- **Decision date:** {date}
- **Evidence:** `{evidence}`

## Context

The three framework specimens need the same deterministic target-discovery semantics before their
framework-owned orchestration diverges. Raw JSON:API reconstruction in each specimen would duplicate
Drupal access, image-field delta, file-reference, classification, ordering, and envelope behavior.
It would also make differences in client plumbing look like differences in the harnesses.

## Decision

Expose `find_images_needing_review()` through one custom, read-only Drupal route:

- `GET /api/agentic-harness/v1/images-needing-review`
- HTTP Basic authentication through Drupal core
- permission `use agentic harness discovery tools`
- granted to `agent_service` and denied to `editor_dana` and anonymous users
- entity-query, entity, field, and referenced-file access checks
- exact target identity: node UUID, current revision ID, field name, delta, and file UUID
- frozen shared tool envelope and target schema
- no model call and no source-content mutation

The shared Python client owns only HTTP/auth/envelope transport. Prompts, context assembly, model
calls, state, retries, interruption, recovery, human continuation, and sequencing remain framework-owned.

## Consequences

- All three later vertical slices start from the same 12-target Drupal projection.
- Step 17 can be tested independently of OpenAI availability or credit.
- The custom route is intentionally lab-specific: it fails closed if the seeded fixture no longer
  contains exactly 12 targets in the frozen 9-missing/3-poor distribution.
- This decision does not prove recommendation quality, framework behavior, or production readiness.
"""

SOURCES_SECTION = """
## Step 17 deterministic Drupal tool sources

Retrieved 2026-08-04. These official sources explain the Drupal mechanisms used by the custom route;
the retained local run remains the evidence for this repository's exact 12-target result.

| ID | Source title | Official? | URL | Mechanism supported | Caveat | Status |
|---|---|---:|---|---|---|---|
| SRC-S17-001 | Structure of routes | yes | https://www.drupal.org/docs/drupal-apis/routing-system/structure-of-routes | Route permission requirements, `_auth`, and `no_cache` options | General routing documentation does not prove this custom route's behavior | verified source |
| SRC-S17-002 | HTTP Basic Authentication overview | yes | https://www.drupal.org/docs/8/core/modules/basic_auth/overview | Core `basic_auth` authenticates a Drupal username/password for a permission-gated route | Use only over protected transport; local credentials remain runtime-only | verified source |
| SRC-S17-003 | Entity Query `accessCheck()` | yes | https://api.drupal.org/api/drupal/core%21lib%21Drupal%21Core%21Entity%21Query%21QueryInterface.php/function/QueryInterface%3A%3AaccessCheck/11.x | Entity queries can explicitly request access checking | Entity, field, and file checks are also retained in the local implementation | verified source |
"""


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return value


def replace_exact(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"Could not find expected {label}; refusing an unguarded edit.")
    if text.count(old) != 1:
        raise RuntimeError(f"Expected one {label}, found {text.count(old)}.")
    return text.replace(old, new, 1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    run_dir = args.run_dir.resolve()

    summary = load_json(run_dir / "summary.json")
    if summary.get("status") != "pass" or summary.get("passed") != 13 or summary.get("total") != 13:
        raise SystemExit("[ERROR] Step 17 finalization requires a passing 13/13 run.")
    evidence = str(run_dir.relative_to(root))

    paths = {
        "plan": root / "PLAN.md",
        "readme": root / "README.md",
        "claims": root / "CLAIMS_REGISTER.md",
        "sources": root / "SOURCES.md",
    }
    for path in paths.values():
        if not path.is_file():
            raise SystemExit(f"[ERROR] Missing finalization file: {path}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = root / ".phase0-step17-backups" / f"finalize-{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    for path in paths.values():
        destination = backup_dir / path.relative_to(root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)

    adr = root / "docs/decisions/ADR-0003-use-permission-scoped-discovery-route.md"
    try:
        plan = paths["plan"].read_text(encoding="utf-8")
        plan = replace_exact(
            plan,
            "- [ ] Step 17 non-AI `find_images_needing_review()` returns exactly 12 targets.",
            "- [x] Step 17 non-AI `find_images_needing_review()` returns exactly 12 targets.",
            "Step 17 plan checkbox",
        )
        paths["plan"].write_text(plan, encoding="utf-8")

        readme = paths["readme"].read_text(encoding="utf-8")
        current_phase = f"""## Current phase

Phase 0 is complete. The frozen model and image representation passed Step 16, and the model-free,
permission-scoped Drupal `find_images_needing_review()` route returned the same 12 exact image-field
usages as the Step 9 manifest without changing Article state or creating suggestions.

Gate 0.5 is next:

> One image, one recommendation, one human decision, three implementations.

Verify Step 17 with:

```bash
bash scripts/run-phase0-step17.sh audit
```

Passing evidence: `{evidence}`
"""
        if "## Current phase" not in readme:
            raise RuntimeError("README.md does not contain the Current phase heading.")
        readme = re.sub(r"## Current phase\n.*\Z", current_phase, readme, count=1, flags=re.S)
        paths["readme"].write_text(readme, encoding="utf-8")

        claims = paths["claims"].read_text(encoding="utf-8")
        if "CLM-SHARED-001" not in claims:
            row = (
                "\n| CLM-SHARED-001 | The permission-scoped Drupal discovery route returns the frozen 12 exact image-field usages after reset without a model call or source mutation. "
                f"| Shared Drupal substrate | SRC-S17-001, SRC-S17-002, SRC-S17-003 | `{evidence}` | observed | "
                "In the pinned Phase 0 lab, the model-free Drupal route returned the same 12 deterministic field usages as the Step 9 manifest; this does not yet prove any framework-owned agent behavior. |\n"
            )
            claims = claims.rstrip() + "\n" + row.lstrip("\n")
            paths["claims"].write_text(claims, encoding="utf-8")

        sources = paths["sources"].read_text(encoding="utf-8")
        if "## Step 17 deterministic Drupal tool sources" not in sources:
            paths["sources"].write_text(sources.rstrip() + "\n" + SOURCES_SECTION, encoding="utf-8")

        if adr.exists():
            existing = adr.read_text(encoding="utf-8")
            if "# ADR-0003: Use a permission-scoped Drupal discovery route" not in existing:
                raise RuntimeError(f"Unexpected pre-existing ADR: {adr}")
        else:
            adr.parent.mkdir(parents=True, exist_ok=True)
            adr.write_text(
                ADR_TEXT.format(
                    date=datetime.now(timezone.utc).date().isoformat(),
                    evidence=evidence,
                ),
                encoding="utf-8",
            )
    except Exception:
        for path in paths.values():
            source = backup_dir / path.relative_to(root)
            if source.is_file():
                shutil.copy2(source, path)
        if adr.exists() and not (backup_dir / adr.relative_to(root)).exists():
            adr.unlink()
        raise

    print(json.dumps({
        "status": "pass",
        "evidence": evidence,
        "backup_dir": str(backup_dir.relative_to(root)),
        "phase": "Gate 0.5",
        "next_milestone": "one-image vertical slice in Drupal AI, LangGraph, and CrewAI",
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
