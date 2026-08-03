#!/usr/bin/env python3
"""Generate human-readable Phase 0 Step 12 review and revision evidence."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

SOURCE_LABELS = {
    "phase0_fixture": "Phase 0 test fixture",
    "drupal_ai": "Drupal AI",
    "langgraph": "LangGraph",
    "crewai": "CrewAI",
}
STATUS_LABELS = {
    "pending": "Pending",
    "approved": "Approved",
    "rejected": "Rejected",
}


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def full_url(site_url: str, path: str) -> str:
    return site_url.rstrip("/") + path


def write_markdown(data: dict[str, Any], site_url: str, output: Path) -> None:
    state = data["audit_state"]
    lines = [
        "# Phase 0 Step 12 — Revision Inspectability Evidence",
        "",
        f"Audit state: **{state}**  ",
        f"Generated: `{data['generated_at']}`  ",
        f"Fixture run ID: `{data['fixture_run_id']}`",
        "",
    ]

    for case in data["cases"]:
        first = case["revisions"][0]
        latest = case["revisions"][-1]
        lines += [
            f"## Case {case['case_id']} — {case['action']}",
            "",
            f"- Suggestion: [{case['title']}]({full_url(site_url, case['paths']['view'])})",
            f"- Revision history: {full_url(site_url, case['paths']['history'])}",
            f"- Source / test origin: `{SOURCE_LABELS.get(case['source_framework'], case['source_framework'])}`",
            f"- Target: `{case['target']['node_title']}` revision `{case['target']['content_revision']}`, "
            f"`{case['target']['field_name']}[{case['target']['delta']}]`",
            f"- Revision count: `{case['revision_count']}`",
            f"- Initial revision: `{first['revision_id']}` by `{first['revision_user']['name']}` at `{first['timestamp_utc']}`",
            f"- Initial status: `{first['review_status']}`",
            f"- Initial proposed alt: {first['proposed_alt']}",
            f"- Latest revision: `{latest['revision_id']}` by `{latest['revision_user']['name']}` at `{latest['timestamp_utc']}`",
            f"- Latest status: `{latest['review_status']}`",
            f"- Status transition: `{first['review_status']}` → `{latest['review_status']}`",
            f"- Latest proposed alt: {latest['proposed_alt']}",
            "",
        ]

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_html(data: dict[str, Any], site_url: str, output: Path) -> None:
    state = data["audit_state"]
    cards = []
    for case in data["cases"]:
        first = case["revisions"][0]
        latest = case["revisions"][-1]
        changed = first["proposed_alt"] != latest["proposed_alt"]
        history_url = full_url(site_url, case["paths"]["history"])
        edit_url = full_url(site_url, case["paths"]["edit"])
        view_url = full_url(site_url, case["paths"]["view"])
        initial_url = full_url(site_url, case["paths"]["initial_revision"])
        action_panel = ""
        if state == "pending":
            expected_alt = case["expected"]["alt"]
            action_panel = f"""
              <section class="action">
                <h3>Reviewer action</h3>
                <p>{escape(case['review_instruction'])}</p>
                <p><strong>Expected final status:</strong> {escape(STATUS_LABELS.get(case['expected']['status'], case['expected']['status']))}</p>
                <p><strong>Expected final alt:</strong> {escape(expected_alt)}</p>
                <p><a class="button" href="{escape(edit_url)}">Open edit form</a></p>
              </section>
            """
        else:
            action_panel = f"""
              <section class="result">
                <h3>Verified result</h3>
                <p><strong>Status transition:</strong> {escape(first['review_status'])} → {escape(latest['review_status'])}</p>
                <p><strong>Latest reviewer:</strong> {escape(latest['revision_user']['name'])}</p>
                <p><strong>Text changed:</strong> {'Yes' if changed else 'No'}</p>
              </section>
            """

        revision_rows = "".join(
            f"""
              <tr>
                <td>{escape(rev['revision_id'])}</td>
                <td>{escape(rev['revision_user']['name'])}</td>
                <td>{escape(rev['timestamp_utc'])}</td>
                <td>{escape(STATUS_LABELS.get(rev['review_status'], rev['review_status']))}</td>
                <td>{escape(rev['proposed_alt'])}</td>
                <td>{escape(rev['revision_log'])}</td>
              </tr>
            """
            for rev in case["revisions"]
        )

        cards.append(
            f"""
            <article class="card" id="case-{escape(case['case_id'])}">
              <header>
                <div class="case-id">Case {escape(case['case_id'])}</div>
                <h2>{escape(case['action'])}</h2>
                <p>{escape(case['title'])}</p>
              </header>
              <dl>
                <dt>Source / test origin</dt><dd>{escape(SOURCE_LABELS.get(case['source_framework'], case['source_framework']))}</dd>
                <dt>Target content revision</dt><dd>{escape(case['target']['content_revision'])}</dd>
                <dt>Target usage</dt><dd>{escape(case['target']['field_name'])}[{escape(case['target']['delta'])}] · file UUID {escape(case['target']['file_uuid'])}</dd>
                <dt>Suggestion owner</dt><dd>{escape(case['owner']['name'])}</dd>
                <dt>Revision count</dt><dd>{escape(case['revision_count'])}</dd>
              </dl>
              {action_panel}
              <nav>
                <a href="{escape(view_url)}">Current suggestion</a>
                <a href="{escape(history_url)}">Revision history</a>
                <a href="{escape(initial_url)}">Initial revision</a>
              </nav>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Revision</th><th>User</th><th>Timestamp (UTC)</th><th>Status</th><th>Proposed alt</th><th>Revision log</th></tr></thead>
                  <tbody>{revision_rows}</tbody>
                </table>
              </div>
            </article>
            """
        )

    output.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Phase 0 Step 12 Revision Evidence</title>
<style>
:root {{ color-scheme: light dark; font-family: system-ui, sans-serif; }}
body {{ max-width: 1180px; margin: 0 auto; padding: 2rem; line-height: 1.5; }}
h1 {{ margin-bottom: .25rem; }}
.summary {{ padding: 1rem; border: 2px solid currentColor; border-radius: .5rem; margin: 1rem 0 2rem; }}
.card {{ border: 1px solid #8888; border-radius: .75rem; padding: 1.25rem; margin: 1.5rem 0; }}
.case-id {{ font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }}
dl {{ display: grid; grid-template-columns: minmax(12rem, 16rem) 1fr; gap: .35rem 1rem; }}
dt {{ font-weight: 700; }} dd {{ margin: 0; overflow-wrap: anywhere; }}
.action, .result {{ border-left: .35rem solid currentColor; padding: .5rem 1rem; margin: 1rem 0; }}
nav {{ display: flex; gap: 1rem; flex-wrap: wrap; margin: 1rem 0; }}
a.button {{ display: inline-block; padding: .55rem .8rem; border: 2px solid currentColor; border-radius: .35rem; text-decoration: none; font-weight: 700; }}
.table-wrap {{ overflow-x: auto; }} table {{ width: 100%; border-collapse: collapse; }}
th, td {{ text-align: left; vertical-align: top; border: 1px solid #8888; padding: .55rem; }}
th {{ font-weight: 700; }}
code {{ overflow-wrap: anywhere; }}
</style>
</head>
<body>
<h1>Phase 0 Step 12 — Revision Inspectability</h1>
<div class="summary">
  <strong>Audit state:</strong> {escape(state)}<br>
  <strong>Generated:</strong> {escape(data['generated_at'])}<br>
  <strong>Fixture run ID:</strong> <code>{escape(data['fixture_run_id'])}</code>
</div>
{''.join(cards)}
</body>
</html>
""",
        encoding="utf-8",
    )


def write_checklist(data: dict[str, Any], site_url: str, screenshot_dir: str, output: Path) -> None:
    lines = [
        "# Step 12 Screenshot Checklist",
        "",
        "Log in as `editor_dana` before opening these links.",
        "",
        f"Save screenshots under: `{screenshot_dir}`",
        "",
        "Minimum required: one revision-history screenshot for each case. Recommended: also capture Case C's initial and current revision views so the editorial text change is visible.",
        "",
    ]
    for case in data["cases"]:
        lines += [
            f"## Case {case['case_id']} — {case['action']}",
            "",
            f"- Revision history: {full_url(site_url, case['paths']['history'])}",
            f"- Initial revision: {full_url(site_url, case['paths']['initial_revision'])}",
            f"- Current suggestion: {full_url(site_url, case['paths']['view'])}",
            f"- Suggested filename: `step12-case-{case['case_id'].lower()}-revision-history.png`",
            "",
        ]
    lines += [
        "## Recommended Case C detail captures",
        "",
        "- `step12-case-c-initial-alt.png` — initial revision showing the prior proposed alt text.",
        "- `step12-case-c-edited-approved.png` — current revision showing edited alt text and Approved status.",
        "",
        "After saving at least three screenshots, run:",
        "",
        "```bash",
        "bash scripts/run-phase0-step12.sh finish confirm",
        "```",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_report(args: argparse.Namespace) -> int:
    data = load_json(args.evidence)
    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_markdown(data, args.site_url, run_dir / "revision-evidence.md")
    write_html(data, args.site_url, run_dir / "revision-evidence.html")
    write_checklist(
        data,
        args.site_url,
        args.screenshot_dir,
        run_dir / "SCREENSHOT-CHECKLIST.md",
    )

    print(f"Evidence HTML: {run_dir / 'revision-evidence.html'}")
    print(f"Evidence Markdown: {run_dir / 'revision-evidence.md'}")
    print(f"Screenshot checklist: {run_dir / 'SCREENSHOT-CHECKLIST.md'}")
    for case in data["cases"]:
        print(
            f"Case {case['case_id']} edit: "
            f"{full_url(args.site_url, case['paths']['edit'])}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    report = sub.add_parser("report")
    report.add_argument("--evidence", required=True)
    report.add_argument("--site-url", required=True)
    report.add_argument("--run-dir", required=True)
    report.add_argument("--screenshot-dir", required=True)
    report.set_defaults(func=cmd_report)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
