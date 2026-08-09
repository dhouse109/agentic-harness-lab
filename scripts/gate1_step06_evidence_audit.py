#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

BASELINE = "27029bdcd2eaf57146fca4f2f0358035c5c9008d"
STEP05_GATE = "gate1-step05-20260808T020222Z-2121689"
BATCH_RUN = "drupal_ai-20260808T020222Z-205fd9"
STEP05_SOURCE_SHA = "f26227dfd17df97fe51d4e4c1c4c612032d0701fcbeaffc8aa816e1efc221c17"
GATE05_SOURCE_SHA = "877cd888fa41eb660b3e3cc0461bee04c0b92bef7e8f2f63fc56d9ec77adde32"
SELECTED = {1: 21, 6: 26, 12: 32}


def fail(message: str) -> None:
    raise SystemExit(f"[ERROR] {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"Unable to read JSON {path}: {exc}")


def dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def immutable_projection(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "node_id": value.get("node_id"),
        "uuid": value.get("uuid"),
        "title": value.get("title"),
        "owner_username": value.get("owner_username"),
        "published": value.get("published"),
        "source_framework": value.get("current_source_framework"),
        "run_id": value.get("current_run_id"),
        "evidence_hash": value.get("current_evidence_hash"),
        "target": value.get("current_target"),
    }


def revision_immutable_projection(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "published": value.get("published"),
        "source_framework": value.get("source_framework"),
        "run_id": value.get("run_id"),
        "evidence_hash": value.get("evidence_hash"),
        "target": value.get("target"),
    }


def verify_review(args: argparse.Namespace) -> None:
    before = load(Path(args.baseline))
    after = load(Path(args.current))
    sequence = int(args.sequence)
    expected_node = SELECTED.get(sequence)
    require(expected_node is not None, f"Unsupported review sequence: {sequence}")
    require(before.get("node_id") == expected_node, f"Baseline node differs for sequence {sequence}")
    require(after.get("node_id") == expected_node, f"Current node differs for sequence {sequence}")
    require(before.get("uuid") == after.get("uuid"), "Recommendation UUID changed")
    require(before.get("current_review_status") == "pending", "Baseline review status is not pending")
    require(after.get("current_review_status") == args.expected_status, "Review status differs")
    require(before.get("current_source_framework") == "drupal_ai", "Baseline framework differs")
    require(before.get("current_run_id") == BATCH_RUN, "Baseline run ID differs")
    require(immutable_projection(before) == immutable_projection(after), "Immutable recommendation fields changed")

    before_count = int(before.get("revision_count", -1))
    after_count = int(after.get("revision_count", -1))
    before_revision = int(before.get("current_revision_id", -1))
    after_revision = int(after.get("current_revision_id", -1))
    require(after_revision != before_revision, "Current revision ID did not change")

    before_revisions = before.get("revisions")
    revisions = after.get("revisions")
    require(isinstance(before_revisions, list) and before_revisions, "Baseline inspection lacks revisions")
    require(isinstance(revisions, list) and revisions, "Current inspection lacks revisions")
    require(len(before_revisions) == before_count, "Baseline revision list/count differs")
    require(len(revisions) == after_count, "Current revision list/count differs")
    require(revisions[:before_count] == before_revisions, "Pre-review revision history changed")

    revision_delta = after_count - before_count
    new_revisions = revisions[before_count:]
    require(len(new_revisions) == revision_delta, "New revision slice differs")
    baseline_latest = before_revisions[-1]
    for revision in new_revisions:
        user = revision.get("revision_user") if isinstance(revision, dict) else None
        require(isinstance(user, dict) and user.get("name") == "editor_dana",
                "A new review revision is not authored by editor_dana")
        require(revision_immutable_projection(revision) == revision_immutable_projection(baseline_latest),
                "Immutable recommendation fields changed in review revision")

    latest = revisions[-1]
    require(latest.get("review_status") == args.expected_status, "Latest revision status differs")

    before_alt = str(before.get("current_proposed_alt_text", ""))
    after_alt = str(after.get("current_proposed_alt_text", ""))
    review_workflow = None
    instruction_deviation = False
    edit_revision_id = None

    if args.alt_policy == "unchanged":
        require(revision_delta == 1,
                f"Expected exactly one new revision; found {before_count} -> {after_count}")
        require(after_alt == before_alt, "Proposed alt text changed when it must remain unchanged")
        action = "approve_unchanged" if args.expected_status == "approved" else "reject_unchanged"
        review_workflow = "single_save_status_decision"
    elif args.alt_policy == "changed":
        require(args.expected_status == "approved", "Changed-alt review must end approved")
        require(after_alt.strip() != "", "Edited proposed alt text is empty")
        require(after_alt != before_alt, "Edited proposed alt text did not change")
        require(revision_delta in (1, 2),
                f"Expected one combined edit/approve revision or a two-revision edit-then-approve lineage; found {before_count} -> {after_count}")
        action = "edit_and_approve"
        if revision_delta == 1:
            review_workflow = "single_save_edit_and_approve"
            edit_revision_id = int(latest.get("revision_id", -1))
        else:
            edit_revision, decision_revision = new_revisions
            require(edit_revision.get("review_status") == "pending",
                    "First sequence-12 review revision must remain pending")
            require(decision_revision.get("review_status") == "approved",
                    "Second sequence-12 review revision must approve")
            edited_alt = str(edit_revision.get("proposed_alt_text", ""))
            decided_alt = str(decision_revision.get("proposed_alt_text", ""))
            require(edited_alt.strip() != "" and edited_alt != before_alt,
                    "First sequence-12 review revision did not contain the human alt-text edit")
            require(decided_alt == edited_alt,
                    "Approval revision changed the human-edited alt text")
            review_workflow = "two_save_edit_then_approve"
            instruction_deviation = True
            edit_revision_id = int(edit_revision.get("revision_id", -1))
    else:
        fail(f"Unknown alt policy: {args.alt_policy}")

    result = {
        "schema_version": 1,
        "sequence": sequence,
        "node_id": expected_node,
        "uuid": after.get("uuid"),
        "action": action,
        "reviewer_username": "editor_dana",
        "status_before": "pending",
        "status_after": args.expected_status,
        "pending_revision_id": before_revision,
        "decision_revision_id": after_revision,
        "edit_revision_id": edit_revision_id,
        "revision_count_before": before_count,
        "revision_count_after": after_count,
        "revision_delta": revision_delta,
        "review_revision_count": revision_delta,
        "review_revision_ids": [int(v.get("revision_id", -1)) for v in new_revisions],
        "review_workflow": review_workflow,
        "instruction_deviation": instruction_deviation,
        "review_timestamp_utc": latest.get("timestamp_utc"),
        "proposed_alt_before": before_alt,
        "proposed_alt_after": after_alt,
        "proposed_alt_changed": after_alt != before_alt,
        "immutable_fields_unchanged": True,
        "immutable_projection": immutable_projection(after),
    }
    dump(Path(args.output), result)
    print(json.dumps(result, indent=2, sort_keys=True))


def audit_final(args: argparse.Namespace) -> None:
    repo = Path(args.repo).resolve()
    gate = Path(args.gate_run_dir).resolve()
    result = Path(args.result_dir).resolve()

    required_gate = [
        "prior-package-audits.log", "batch-run-pointer.txt", "recommendation-counts.json",
        "revision-lineage.json", "reviewer-decisions.json", "source-before-after.json",
        "secrets-scan.log", "summary.json", "summary.md", "post-restore-state.json",
        "decision-seq1.json", "decision-seq6.json", "decision-seq12.json",
        "review-workflow-deviation.json",
    ]
    for name in required_gate:
        require((gate / name).is_file(), f"Missing Step 1.06 Gate evidence: {name}")

    expected_result = ["human-review.json", "source-non-mutation.json", "duplicate-check.json", "environment.json"]
    for name in expected_result:
        require((result / name).is_file(), f"Missing Step 1.06 result addition: {name}")

    pointer = (gate / "batch-run-pointer.txt").read_text(encoding="utf-8").strip()
    require(pointer == BATCH_RUN, "Batch run pointer differs")

    decisions = load(gate / "reviewer-decisions.json")
    require(decisions.get("run_id") == BATCH_RUN, "Reviewer decisions run ID differs")
    items = decisions.get("decisions")
    require(isinstance(items, list) and len(items) == 3, "Expected exactly three reviewer decisions")
    by_seq = {int(item.get("sequence", -1)): item for item in items if isinstance(item, dict)}
    require(set(by_seq) == {1, 6, 12}, "Reviewer decision sequences differ")
    require(by_seq[1].get("action") == "approve_unchanged", "Sequence 1 action differs")
    require(by_seq[6].get("action") == "reject_unchanged", "Sequence 6 action differs")
    require(by_seq[12].get("action") == "edit_and_approve", "Sequence 12 action differs")
    for seq, item in by_seq.items():
        require(item.get("reviewer_username") == "editor_dana", f"Sequence {seq} reviewer differs")
        require(item.get("immutable_fields_unchanged") is True, f"Sequence {seq} immutables changed")
    require(by_seq[1].get("revision_delta") == 1, "Sequence 1 revision delta differs")
    require(by_seq[6].get("revision_delta") == 1, "Sequence 6 revision delta differs")
    require(by_seq[12].get("revision_delta") in (1, 2), "Sequence 12 revision delta differs")
    require(by_seq[1].get("proposed_alt_changed") is False, "Sequence 1 alt text changed")
    require(by_seq[6].get("proposed_alt_changed") is False, "Sequence 6 alt text changed")
    require(by_seq[12].get("proposed_alt_changed") is True, "Sequence 12 alt text did not change")
    if by_seq[12].get("revision_delta") == 2:
        require(by_seq[12].get("review_workflow") == "two_save_edit_then_approve",
                "Sequence 12 two-revision workflow differs")
        require(by_seq[12].get("instruction_deviation") is True,
                "Sequence 12 instruction deviation was not recorded")
        require(by_seq[12].get("review_revision_count") == 2,
                "Sequence 12 review revision count differs")
        require(len(by_seq[12].get("review_revision_ids", [])) == 2,
                "Sequence 12 review revision IDs differ")

    deviation = load(gate / "review-workflow-deviation.json")
    observed_two_save = by_seq[12].get("revision_delta") == 2
    require(deviation.get("deviation_observed") is observed_two_save,
            "Review workflow deviation flag differs")
    require(deviation.get("sequence") == 12, "Review workflow deviation sequence differs")
    require(deviation.get("review_workflow") == by_seq[12].get("review_workflow"),
            "Review workflow deviation lineage differs")

    counts = load(gate / "recommendation-counts.json")
    final_counts = counts.get("after_sequence_12", {}).get("counts")
    require(final_counts == {"approved": 2, "pending": 9, "rejected": 1}, "Final review counts differ")

    source = load(gate / "source-before-after.json")
    for key in ("before_review", "after_review", "after_restore"):
        value = source.get(key)
        require(isinstance(value, dict), f"Source evidence missing {key}")
        require(value.get("article_count") == 20, f"Article count differs at {key}")
        require(value.get("article_source_sha256") == GATE05_SOURCE_SHA, f"Article source hash differs at {key}")
    require(source["before_review"].get("suggestion_count") == 12, "Before-review suggestion count differs")
    require(source["after_review"].get("suggestion_count") == 12, "After-review suggestion count differs")
    require(source["after_restore"].get("suggestion_count") == 0, "Post-restore suggestion count is not zero")
    require(source.get("source_articles_unchanged") is True, "Source non-mutation flag is not true")
    require(source.get("approved_recommendation_applied_to_source") is False, "Automatic source application flag differs")

    post = load(gate / "post-restore-state.json")
    require(post.get("article_count") == 20, "Post-restore Article count differs")
    require(post.get("suggestion_count") == 0, "Post-restore suggestion count differs")
    require(post.get("article_source_sha256") == GATE05_SOURCE_SHA, "Post-restore source hash differs")
    require(post.get("module_enabled") is False, "Custom Drupal AI module remains enabled after restore")

    original_summary = load(result / "summary.json")
    require(original_summary.get("status") == "pass", "Step 1.05 summary is not pass")
    require(original_summary.get("run_id") == BATCH_RUN, "Step 1.05 summary run ID differs")
    require(original_summary.get("target_count") == 12, "Step 1.05 target count differs")
    require(original_summary.get("duplicate_count") == 0, "Step 1.05 duplicate count differs")
    human = load(result / "human-review.json")
    require(human.get("run_id") == BATCH_RUN and len(human.get("decisions", [])) == 3, "Result human-review evidence differs")
    duplicate = load(result / "duplicate-check.json")
    require(duplicate.get("duplicate_count") == 0, "Result duplicate check differs")
    require(duplicate.get("recommendation_count") == 12, "Result recommendation count differs")

    plan = (repo / "PLAN.md").read_text(encoding="utf-8")
    readme = (repo / "README.md").read_text(encoding="utf-8")
    status = (repo / "docs/CURRENT-STATUS.md").read_text(encoding="utf-8")
    for text, label in ((plan, "PLAN.md"), (readme, "README.md"), (status, "CURRENT-STATUS.md")):
        require("gate-1-step07-drupal-ai-certification-and-handoff-v1.0.0" in text, f"{label} does not declare Step 1.07 next")
    require("- [x] Step 1.06 — batch evidence and human review" in plan, "PLAN.md does not mark Step 1.06 complete")

    # Evidence-specific secret / raw-image scan. Do not scan unrelated historical files.
    patterns = [
        re.compile(r"authorization:\s*(?:basic|bearer)", re.I),
        re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
        re.compile(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]{16,}", re.I),
    ]
    scan_paths = list(gate.rglob("*")) + [result / name for name in expected_result]
    for path in scan_paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in patterns:
            require(pattern.search(text) is None, f"Sensitive pattern detected in {path}")

    summary = load(gate / "summary.json")
    require(summary.get("status") == "pass", "Step 1.06 summary is not pass")
    require(summary.get("step_1_07_authorized") is True, "Step 1.07 authorization flag differs")
    expected_review_revisions = 2 + int(by_seq[12].get("revision_delta", 0))
    require(summary.get("review_revision_count") == expected_review_revisions,
            "Summary review revision count differs")
    require(summary.get("sequence_12_review_workflow") == by_seq[12].get("review_workflow"),
            "Summary sequence-12 workflow differs")

    print(json.dumps({
        "status": "pass",
        "step": "1.06",
        "batch_run_id": BATCH_RUN,
        "review_decisions": 3,
        "final_review_counts": final_counts,
        "source_articles_unchanged": True,
        "restored_seeded_clean": True,
        "step_1_07_authorized": True,
    }, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    review = sub.add_parser("verify-review")
    review.add_argument("--baseline", required=True)
    review.add_argument("--current", required=True)
    review.add_argument("--sequence", required=True, type=int)
    review.add_argument("--expected-status", required=True, choices=["approved", "rejected"])
    review.add_argument("--alt-policy", required=True, choices=["unchanged", "changed"])
    review.add_argument("--output", required=True)
    final = sub.add_parser("final-audit")
    final.add_argument("--repo", required=True)
    final.add_argument("--gate-run-dir", required=True)
    final.add_argument("--result-dir", required=True)
    args = parser.parse_args()
    if args.command == "verify-review":
        verify_review(args)
    else:
        audit_final(args)


if __name__ == "__main__":
    main()
