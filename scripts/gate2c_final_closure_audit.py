#!/usr/bin/env python3
"""Permanent audit for the terminal, non-certifying Gate 2C disposition."""
from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


EXPECTED_HEAD = "03816e141f77820e42486fcbad9db244939cd7a8"
PREDECESSOR_SOURCE_MANIFEST_SHA = "c6427eb6f1f78e102a56a117da02e903cf719214d2a2506a08fe3cbabec7ae1b"
PREDECESSOR_AUDIT_SHA = "36404648cccb434c7d56ce6e575db1ec92fee17ec45e358c74a5dd8efe861dd9"
CONTRACT_SHA = "3c4801e6eb35d40d94e066c70017d3acebca95183e7e544646be6e2b40aa5ec6"
CLOSURE_STATUS = "CLOSED_NON_CERTIFYING_WITH_INCOMPLETE_EVIDENCE"
STEP_STATUS = "TERMINAL_UNCERTIFIED"
EVIDENCE_COUNT = 84
EVIDENCE_INVENTORY_SHA = "a6f20ab3e45105d74bba13c21fdd51878435e4bc803febe98df7e55a2648c28c"
OBSERVATION_SHA = "2aab5b97540ed8efd79eb11e487ad8011977c758c54977b9dfcc8cdf49eae3f8"

CLOSURE_CONTRACT = "shared/contracts/GATE2C-CLOSURE-AND-DISPOSITION.json"
CLOSURE_SIDECAR = "shared/contracts/GATE2C-CLOSURE-AND-DISPOSITION.sha256"
CLOSURE_SCHEMA = "shared/schemas/gate2c-closure-and-disposition.schema.json"
CLOSURE_SOURCE_MANIFEST = "shared/contracts/GATE2C-CLOSURE-INSTALLED-SOURCE-SHA256.txt"
PREDECESSOR_SOURCE_MANIFEST = "shared/contracts/GATE2C-STEP02-INSTALLED-SOURCE-SHA256.txt"
PREDECESSOR_AUDIT = "scripts/gate2c_step02_audit.py"
OBSERVATION = "evidence/gates/gate-2c/drupal-post-expiry-partial-observations/gate2c-step02-drupal-20261002T132121Z-a54c7a7a/observation.json"
FINAL_DRUPAL_ROOT = "evidence/gates/gate-2c/model-free-rehearsals/gate2c-step02-drupal-20261002T132121Z-a54c7a7a"
CORRECTED_ROOT = "evidence/gates/gate-2c/model-free-rehearsals/gate2c-step02-offline-20260930T222029Z-24c7b158"
DECISION = "evidence/gates/gate-2c/crewai-recovery-decisions/gate2c-step02-crewai-recovery-architecture-decision-20260930T224649Z-24c7b158.json"

DOCUMENTS = {
    "AGENTS.md",
    "PLAN.md",
    "README.md",
    "CLAIMS_REGISTER.md",
    "COMPARISON_MATRIX.md",
    "docs/CURRENT-STATUS.md",
    "docs/gates/GATE-2-STRUCTURE.md",
    "docs/gates/GATE-2C-CLOSURE-AND-DISPOSITION.md",
}

CREATE_PATHS = {
    "docs/gates/GATE-2C-CLOSURE-AND-DISPOSITION.md",
    CLOSURE_CONTRACT,
    CLOSURE_SIDECAR,
    CLOSURE_SCHEMA,
    CLOSURE_SOURCE_MANIFEST,
    "scripts/gate2c_final_closure_audit.py",
    "scripts/run-gate2c-final-closure-audit.sh",
}

GATE2B_POINTERS = {
    "evidence/gates/gate-2b/frozen-batch-activation/LATEST",
    "evidence/gates/gate-2b/frozen-batch-http-readiness/LATEST",
    "evidence/gates/gate-2b/frozen-batch/LATEST",
}

LOCAL_ONLY_PREFIXES = (
    "crewai/.runtime/",
    ".cache/",
    "drupal/.cache/",
    "crewai/.venv/",
    "drupal/.ddev/db_snapshots/",
)
LOCAL_ONLY_ROOTS = {"crewai/.runtime", ".cache", "drupal/.cache", "crewai/.venv", "drupal/.ddev/db_snapshots"}
EXPECTED_CANONICAL_PATH_COUNT = 141
EXPECTED_CLOSEOUT_DELTA_COUNT = 134
CANONICAL_REPOSITORY_ROOT = Path("/home/dhouse109/projects/agentic-harness-lab")

HISTORICAL_AGGREGATES = [
    ("gate2c-step02-drupal-20261001T173201Z-545a1ba2", "1014dacee5194fed8a2c696145d792898d5c9b9399f20c548bdd6e6cd4137714"),
    ("gate2c-step02-drupal-20261001T225458Z-c5d0e6b2", "6ec105136d47f8b25a271c0950ff11984709b7e876e207b45dad7805ccde33c0"),
    ("gate2c-step02-drupal-20261002T132121Z-a54c7a7a", "cdd180a1c88de2fab50766e7bb82644dfd47fd51b57cca9a412985f15a67b08e"),
]

EXPECTED_HASHES = {
    "shared/contracts/GATE1-DRUPAL-AI-FREEZE.json": "2af9870aed1ea2ce15cf16f848cc1eb41573e9f9f8cc21bcaa9d80bd9c9a8cdd",
    "shared/contracts/GATE2A-LANGGRAPH-FREEZE.json": "a28361c34b9d1c2089eee786324ad34cffbf54e3495f59a276c489865e5630f0",
    "shared/contracts/GATE2B-CREWAI-FREEZE.json": "74e2baad0cbe612dcd7e72ccdc264b01960ee12e09cfb0ae3154969b6055c206",
    "evidence/gates/gate-2c/contract/gate2c-step01-20260922T113303Z-fd9cdb75/evidence-manifest.json": "ed4444d95412b1450784c09eba80817d532cf7ed6a8ad96cd1bbbef179dd6190",
    f"{CORRECTED_ROOT}/evidence-manifest.json": "730b892d232a3dea7e77e4391b7beec5d40e807b76f99b13bb0036ae00cf74ca",
    "evidence/gates/gate-2c/model-free-rehearsal-preservation/gate2c-step02-offline-20260930T222029Z-24c7b158/finalization.json": "d882c8339025c1ba7e510abb19984fc4724e2a594a190760c07f95db034fd8d8",
    f"{CORRECTED_ROOT}/langgraph-termination.json": "e84425a8b86cca7ff2d78415cd5ddd63caa7140cc374ff4eb7dce41579953586",
    f"{CORRECTED_ROOT}/langgraph-recovery.json": "071b4706c9ee1e24ed84734b94ada1dde1dfbcc743ec022cfb23aca0de184e9a",
    f"{CORRECTED_ROOT}/crewai-termination.json": "bc50b5c582f72b2133f6186ee0eb39488d452e509490c2a68f6e0e7406f84f14",
    f"{CORRECTED_ROOT}/crewai-recovery.json": "feb2c31832e43027f58f5d772710e2768591436fd8b393e89e02e63299ae2236",
    DECISION: "9b46330e3f9dd47bd4c8b7835db928335bde2447ca8825673cef77b9df6e7d1e",
    OBSERVATION: OBSERVATION_SHA,
    f"{FINAL_DRUPAL_ROOT}/FAILED-ATTEMPT.json": "c405e0cdab7b20f2ab19fb8234b839984929fd7934bdb0589ea4c9b4b4d80ba9",
}


class AuditFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditFailure(message)


def sha(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def evidence_inventory(root: Path) -> tuple[int, str, dict[str, int]]:
    entries: list[dict[str, Any]] = []
    categories: dict[str, int] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        entries.append({"path": relative, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        category = relative.split("/", 1)[0]
        categories[category] = categories.get(category, 0) + 1
    encoded = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return len(entries), hashlib.sha256(encoded).hexdigest(), categories


def manifest_paths(root: Path, relative: str) -> set[str]:
    paths: set[str] = set()
    for line in (root / relative).read_text(encoding="utf-8").splitlines():
        digest, path = line.split("  ", 1)
        require(len(digest) == 64 and path not in paths, f"invalid source-manifest entry: {path}")
        paths.add(path)
    return paths


def git_blob(repo: Path, commit: str, relative: str) -> bytes | None:
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{relative}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.stdout if result.returncode == 0 else None


def is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    return subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", ancestor, descendant],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def is_local_only(relative: str) -> bool:
    return relative in LOCAL_ONLY_ROOTS or relative.startswith(LOCAL_ONLY_PREFIXES)


def canonical_closeout_bytes(repo: Path, content: Path) -> dict[str, bytes]:
    closure_paths = manifest_paths(content, CLOSURE_SOURCE_MANIFEST) | {CLOSURE_SOURCE_MANIFEST}
    predecessor_paths = manifest_paths(repo, PREDECESSOR_SOURCE_MANIFEST) | {PREDECESSOR_SOURCE_MANIFEST}
    evidence_paths = {
        path.relative_to(repo).as_posix()
        for path in (repo / "evidence/gates/gate-2c").rglob("*")
        if path.is_file()
    }
    canonical = closure_paths | predecessor_paths | evidence_paths | GATE2B_POINTERS
    require(len(canonical) == EXPECTED_CANONICAL_PATH_COUNT, "canonical closeout path inventory")
    values: dict[str, bytes] = {}
    for relative in sorted(canonical):
        source = content / relative if relative in closure_paths else repo / relative
        require(source.is_file() and not source.is_symlink(), f"missing or unsafe canonical closeout path: {relative}")
        values[relative] = source.read_bytes()
    return values


def expected_closeout_delta(repo: Path, content: Path) -> tuple[dict[str, bytes], set[str]]:
    canonical = canonical_closeout_bytes(repo, content)
    delta = {
        relative
        for relative, data in canonical.items()
        if git_blob(repo, EXPECTED_HEAD, relative) != data
    }
    require(len(delta) == EXPECTED_CLOSEOUT_DELTA_COUNT, "exact atomic closeout delta inventory")
    return canonical, delta


def validate_repository_lineage(repo: Path, content: Path) -> str:
    require(git(repo, "branch", "--show-current") == "main", "branch must be main")
    require(not git(repo, "diff", "--cached", "--name-only"), "staged paths prohibited")
    head = git(repo, "rev-parse", "HEAD")
    origin = git(repo, "rev-parse", "origin/main")
    require(is_ancestor(repo, EXPECTED_HEAD, head), "closure predecessor is not in HEAD ancestry")
    require(is_ancestor(repo, EXPECTED_HEAD, origin), "closure predecessor is not in origin/main ancestry")
    require(is_ancestor(repo, head, origin) or is_ancestor(repo, origin, head), "HEAD and origin/main diverged")
    canonical, expected_delta = expected_closeout_delta(repo, content)

    if head == EXPECTED_HEAD:
        require(origin == EXPECTED_HEAD, "pre-commit origin/main drift")
        modified = set(filter(None, git(repo, "diff", "--name-only").splitlines()))
        untracked = {
            relative
            for relative in filter(None, git(repo, "ls-files", "--others", "--exclude-standard").splitlines())
            if not is_local_only(relative)
        }
        require(modified | untracked == expected_delta, "pre-commit closeout working-tree inventory")
        return "PREDECESSOR_WORKTREE"

    introduction = list(filter(None, git(
        repo,
        "log",
        "--format=%H",
        "--diff-filter=A",
        f"{EXPECTED_HEAD}..{head}",
        "--",
        CLOSURE_SOURCE_MANIFEST,
    ).splitlines()))
    require(len(introduction) == 1, "exactly one closure-manifest introduction commit required")
    closeout_commit = introduction[0]
    parents = git(repo, "rev-list", "--parents", "-n", "1", closeout_commit).split()[1:]
    require(EXPECTED_HEAD in parents, "closeout commit must descend directly from the immutable predecessor")
    committed_delta = set(filter(None, git(repo, "diff", "--name-only", EXPECTED_HEAD, closeout_commit).splitlines()))
    require(committed_delta == expected_delta, "atomic closeout commit path inventory")
    for relative, data in canonical.items():
        require(git_blob(repo, closeout_commit, relative) == data, f"closeout commit canonical bytes: {relative}")
        require(git(repo, "ls-files", "--error-unmatch", "--", relative) == relative, f"canonical path is not tracked: {relative}")
    require(not git(repo, "diff", "--name-only"), "committed successor tracked working tree must be clean")
    successor_untracked = {
        relative
        for relative in filter(None, git(repo, "ls-files", "--others", "--exclude-standard").splitlines())
        if not is_local_only(relative)
    }
    require(not successor_untracked, f"unexpected non-runtime successor untracked paths: {sorted(successor_untracked)}")
    return f"COMMITTED_SUCCESSOR:{closeout_commit}"


def validate_contract_value(value: dict[str, Any]) -> None:
    require(value.get("status") == CLOSURE_STATUS, "closure status")
    source = value.get("source_epoch", {})
    require(source.get("head") == EXPECTED_HEAD and source.get("origin_main") == EXPECTED_HEAD, "source epoch commit")
    require(source.get("gate2c_contract_sha256") == CONTRACT_SHA, "Gate 2C contract binding")
    require(source.get("step2c02_installed_source_manifest_sha256") == PREDECESSOR_SOURCE_MANIFEST_SHA, "Step 2C.02 source epoch")
    require(source.get("step2c02_permanent_audit_sha256") == PREDECESSOR_AUDIT_SHA, "Step 2C.02 audit binding")

    inventory = value.get("retained_evidence_inventory", {})
    require(inventory.get("file_count") == EVIDENCE_COUNT, "evidence inventory count")
    require(inventory.get("canonical_path_size_sha256_inventory_digest") == EVIDENCE_INVENTORY_SHA, "evidence inventory digest")

    rehearsal = value.get("corrected_environment_model_free_rehearsal", {})
    require(rehearsal.get("outcome") == "PASS", "corrected-environment rehearsal result")
    require(rehearsal.get("scope") == "MODEL_FREE_ARCHITECTURE_MECHANICS_NOT_AUTHORITATIVE_GATE_2C_RECOVERY", "rehearsal qualification")

    frameworks = value.get("framework_outcomes", {})
    langgraph = frameworks.get("langgraph", {})
    crewai = frameworks.get("crewai", {})
    drupal = frameworks.get("drupal_ai", {})
    require(langgraph.get("gate2c_status") == "MODEL_FREE_RECOVERY_REHEARSAL_PASS_NOT_AUTHORITATIVE", "LangGraph qualification")
    require(crewai.get("gate2c_status") == "MODEL_FREE_RECOVERY_REHEARSAL_PASS_HUMAN_APPROVED_ARCHITECTURE_NOT_AUTHORITATIVE", "CrewAI qualification")
    require(crewai.get("human_decision") == "APPROVED_FOR_MODEL_FREE_ARCHITECTURE_PROOF_ONLY", "CrewAI human decision scope")
    require(drupal.get("gate2c_status") == "PARTIAL_NON_CERTIFYING_EVIDENCE_NO_RECOVERY_CONTINUATION", "Drupal qualification")
    require([(item.get("run_id"), item.get("aggregate_sha256")) for item in drupal.get("historical_families", [])] == HISTORICAL_AGGREGATES, "Drupal historical aggregates")
    partial = drupal.get("partial_observation", {})
    require(partial.get("sha256") == OBSERVATION_SHA and partial.get("certifying_evidence") is False, "partial observation non-certifying binding")
    require(partial.get("immediate_lock_denial_reconstructed") is False, "immediate proof remains missing")
    require(partial.get("historical_termination_proof_reconstructed") is False, "termination proof remains missing")
    require(partial.get("state_sha256_before") == partial.get("state_sha256_after"), "Drupal state unchanged")
    require(partial.get("completed_sequences_before") == [1, 2, 3, 4, 5, 6] == partial.get("completed_sequences_after"), "Drupal durable sequences")
    require(partial.get("target_7_started") is False and partial.get("target_7_processed") is False, "target 7 remains unprocessed")

    lifecycle = value.get("lifecycle", {})
    require(lifecycle.get("step_2c02") == STEP_STATUS, "Step 2C.02 terminal status")
    require(lifecycle.get("step_2c02_pass") is False and lifecycle.get("step_2c02_certified") is False, "Step 2C.02 cannot pass or certify")
    require(lifecycle.get("gate_2c") == CLOSURE_STATUS, "Gate 2C closure status")
    require(lifecycle.get("gate_2c_pass") is False and lifecycle.get("gate_2c_certified") is False, "closure cannot imply Gate 2C certification")
    require(lifecycle.get("gate_2") == "NOT_COMPLETE" and lifecycle.get("gate_2_pass") is False, "Gate 2 remains incomplete")
    require(lifecycle.get("gate_2_exit_criteria_satisfied") is False, "Gate 2 exit criteria")
    require(lifecycle.get("authoritative_three_framework_comparison_completed") is False, "no authoritative three-framework comparison")
    require(lifecycle.get("step_2c03_performed") is False, "Step 2C.03 not performed")

    reset = value.get("reset_disposition", {})
    require(reset.get("status") == "RESET_NOT_PERFORMED", "reset status")
    require(reset.get("eligibility") == "BLOCKED_MISSING_FULL_PASSING_DRUPAL_REHEARSAL", "reset eligibility")
    require(reset.get("closure_grants_reset_authority") is False, "closure cannot authorize reset")

    runtime = value.get("no_more_runtime", {})
    require(runtime.get("additional_worker_identities_permitted") == 0, "no additional worker identities")
    require(runtime.get("replacement_slots_permitted") == 0, "no replacement slots")
    require(runtime.get("worker_retry_permitted") is False and runtime.get("automatic_retry_permitted") is False, "no retries")
    require(runtime.get("partial_observation_invocation_count") == 1 == runtime.get("maximum_partial_observation_invocations"), "one consumed partial observation")
    for key in (
        "additional_observation_permitted",
        "immediate_observation_replay_permitted",
        "failed_final_start_retry_permitted",
        "step_2c03_activity_permitted",
        "step_2c02_certification_permitted",
        "pointer_update_permitted",
        "identity_allocation_permitted",
        "drupal_reset_permitted",
    ):
        require(runtime.get(key) is False, f"no-more-runtime guard: {key}")

    guards = value.get("claim_guards", {})
    require(set(guards.get("permitted_claim_ids", [])) == {"CLM-G2C-001", "CLM-G2C-002", "CLM-G2C-003", "CLM-G2C-004", "CLM-G2C-008"}, "permitted claim set")
    require(set(guards.get("prohibited_claim_ids", [])) == {"CLM-G2C-005", "CLM-G2C-006", "CLM-G2C-007"}, "prohibited claim set")
    prohibited = set(guards.get("prohibited_meanings", []))
    for meaning in (
        "ALL_THREE_HARNESSES_RECOVERED_AFTER_SIGKILL",
        "DRUPAL_RECOVERED_AT_TARGET_7_WITHOUT_REPLAY",
        "DRUPAL_IMMEDIATE_LOCK_DENIAL_OBSERVED",
        "STEP_2C_02_PASS_OR_CERTIFIED",
        "GATE_2C_PASS_COMPLETE_OR_CERTIFIED",
        "GATE_2_COMPLETE_OR_PASS",
    ):
        require(meaning in prohibited, f"prohibited meaning: {meaning}")

    activity = value.get("closure_activity", {})
    require(activity and all(count == 0 for count in activity.values()), "closure must perform zero runtime/certification/pointer activity")


def run_predecessor_audit(repo: Path) -> None:
    require(sha(repo / PREDECESSOR_SOURCE_MANIFEST) == PREDECESSOR_SOURCE_MANIFEST_SHA, "predecessor installed-source manifest drift")
    require(sha(repo / PREDECESSOR_AUDIT) == PREDECESSOR_AUDIT_SHA, "predecessor permanent audit drift")
    spec = importlib.util.spec_from_file_location("gate2c_step02_audit", repo / PREDECESSOR_AUDIT)
    require(spec is not None and spec.loader is not None, "cannot load predecessor auditor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original_inventory = module.validate_untracked_inventory
    original_git = module.git

    def canonical_protected_state_fingerprint(repo_path: Path) -> tuple[int, str]:
        """Reproduce the sealed predecessor digest without binding to a fixture path."""
        roots = (
            ".cache/gate2c-step02",
            "evidence/gates/gate-2c/model-free-rehearsal-authorizations",
            "evidence/gates/gate-2c/model-free-rehearsal-preservation",
            "evidence/gates/gate-2c/model-free-rehearsals",
            "crewai/.runtime",
            "evidence/gates/gate-2b",
        )
        fixed = (
            "crewai/agentic_harness_crewai/gate2c_recovery.py",
            "langchain/agentic_harness_langgraph/gate2c_recovery.py",
            "scripts/gate2c_step02_supervisor.py",
            "drupal/scripts/gate2c-step02-drupal-rehearsal.php",
        )
        paths: set[Path] = set()
        for relative in roots:
            paths.update(path for path in (repo_path / relative).rglob("*") if path.is_file())
        paths.update(
            repo_path / relative
            for relative in fixed
            if relative not in module.HISTORICAL_PROTECTED_SOURCE_PATHS
        )
        entries = [
            (
                str(CANONICAL_REPOSITORY_ROOT / path.relative_to(repo_path)),
                path.stat().st_size,
                module.sha(path),
            )
            for path in sorted(paths, key=lambda value: str(value))
        ]
        entries.extend(
            (str(path.resolve()), path.stat().st_size, module.sha(path))
            for path in module.EXTERNAL_PACKAGE_ROOT.glob(
                "gate-2c-step02-*-result-preservation-v1.0.0/preservation-manifest.json"
            )
        )
        predecessor_payload = module.EXTERNAL_PACKAGE_ROOT / module.HUMAN_DECISION_REPAIR_PACKAGE / "payload"
        for relative in sorted(module.HISTORICAL_PROTECTED_SOURCE_PATHS):
            historical = predecessor_payload / relative
            current = repo_path / relative
            require(historical.is_file() and current.is_file(), f"historical protected source missing: {relative}")
            entries.append(
                (
                    str(CANONICAL_REPOSITORY_ROOT / relative),
                    historical.stat().st_size,
                    module.sha(historical),
                )
            )
        entries.sort(key=lambda value: value[0])
        digest = hashlib.sha256(json.dumps(entries, separators=(",", ":")).encode()).hexdigest()
        return len(entries), digest

    evidence_roots = (
        module.REHEARSAL_EVIDENCE_ROOT,
        module.AUTHORIZATION_ROOT,
        module.PRESERVATION_ROOT,
        module.DECISION_ROOT,
        module.DRUPAL_REPLACEMENT_AUTHORIZATION_ROOT,
        module.DRUPAL_FURTHER_REPLACEMENT_AUTHORIZATION_ROOT,
        module.POST_EXPIRY_PARTIAL_EVIDENCE_ROOT,
    )
    logical_evidence = {
        path.relative_to(repo).as_posix()
        for root in evidence_roots
        for path in (repo / root).rglob("*")
        if path.is_file()
    }
    actual_untracked = {
        relative
        for relative in filter(None, original_git(repo, "ls-files", "--others", "--exclude-standard").splitlines())
        if not is_local_only(relative)
    }
    logical_untracked = (
        actual_untracked
        | set(module.PROTECTED)
        | set(module.INSTALLED_SOURCES)
        | {module.SOURCE_MANIFEST}
        | logical_evidence
        | CREATE_PATHS
    )

    def successor_git(repo_path: Path, *args: str) -> str:
        if args == ("ls-files", "--others", "--exclude-standard"):
            return "\n".join(sorted(logical_untracked))
        return original_git(repo_path, *args)

    def successor_inventory(untracked: set[str], evidence: set[str], transition: set[str]) -> None:
        original_inventory(untracked - CREATE_PATHS, evidence, transition)

    module.git = successor_git
    module.protected_state_fingerprint = canonical_protected_state_fingerprint
    module.validate_untracked_inventory = successor_inventory
    module.validate_architecture_decision_lifecycle_docs = lambda _content: None
    prior_argv = sys.argv[:]
    prior_path = sys.path[:]
    output = io.StringIO()
    try:
        sys.path.insert(0, str(repo / "scripts"))
        sys.argv = [PREDECESSOR_AUDIT, "--repo", str(repo), "--mode", "installed"]
        with contextlib.redirect_stdout(output):
            result = module.main()
    finally:
        sys.argv = prior_argv
        sys.path[:] = prior_path
    require(result == 0, "predecessor permanent audit failed")
    text = output.getvalue()
    for marker in (
        "DRUPAL_START_FAILED_PRESERVED",
        "DRUPAL_REPLACEMENT_START_PROCESS_IDENTITY_FAILED_PRESERVED",
        "DRUPAL_FURTHER_REPLACEMENT_START_POST_SIGKILL_TERMINATION_PROOF_FAILED_PRESERVED",
        "DRUPAL_IMMEDIATE_OBSERVATION_MISSED_DUE_TO_TERMINATION_PROOF_GATE",
        "DRUPAL_POST_EXPIRY_PARTIAL_OBSERVATION_PERFORMED_NON_CERTIFYING",
        "RESET_NOT_PERFORMED",
        "STEP_2C_02_UNCERTIFIED",
        "GATE_2_NOT_COMPLETE",
    ):
        require(marker in text, f"predecessor audit marker missing: {marker}")


def validate_source_manifest(content: Path) -> None:
    manifest = content / CLOSURE_SOURCE_MANIFEST
    require(manifest.is_file(), "closure installed-source manifest missing")
    seen: set[str] = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        require(len(digest) == 64 and relative not in seen, f"invalid source manifest entry: {relative}")
        seen.add(relative)
        require(sha(content / relative) == digest, f"closure source drift: {relative}")
    require(seen == (DOCUMENTS | CREATE_PATHS) - {CLOSURE_SOURCE_MANIFEST}, "closure source manifest inventory")


def validate_documents(content: Path, contract: dict[str, Any]) -> None:
    for relative, expected in contract["documentation_bindings"].items():
        require(sha(content / relative) == expected, f"documentation binding: {relative}")
    required = {
        "AGENTS.md": (CLOSURE_STATUS, STEP_STATUS, "Gate 2 remains `NOT_COMPLETE`", "additional worker identities `0`"),
        "PLAN.md": (CLOSURE_STATUS, "terminally `UNCERTIFIED`", "Gate 2 remains `NOT_COMPLETE`"),
        "README.md": (CLOSURE_STATUS, "`TERMINAL_UNCERTIFIED`", "no additional worker"),
        "docs/CURRENT-STATUS.md": (CLOSURE_STATUS, "`TERMINAL_UNCERTIFIED`", "`RESET_NOT_PERFORMED`", "zero further worker identities"),
        "docs/gates/GATE-2-STRUCTURE.md": (CLOSURE_STATUS, "Gate 2 remains `NOT_COMPLETE`"),
        "docs/gates/GATE-2C-CLOSURE-AND-DISPOSITION.md": (CLOSURE_STATUS, STEP_STATUS, "RESET_NOT_PERFORMED", "all three harnesses successfully recovered after SIGKILL"),
    }
    for relative, phrases in required.items():
        text = (content / relative).read_text(encoding="utf-8")
        require(all(phrase in text for phrase in phrases), f"closure wording: {relative}")

    claims = (content / "CLAIMS_REGISTER.md").read_text(encoding="utf-8")
    for claim_id, status in (
        ("CLM-G2C-001", "supported-qualified"),
        ("CLM-G2C-002", "supported-qualified"),
        ("CLM-G2C-003", "partial-evidence"),
        ("CLM-G2C-004", "supported-qualified"),
        ("CLM-G2C-005", "not-demonstrated"),
        ("CLM-G2C-006", "prohibited"),
        ("CLM-G2C-007", "prohibited"),
        ("CLM-G2C-008", "documented"),
    ):
        require(f"| {claim_id} |" in claims and f"| {status} |" in next(line for line in claims.splitlines() if f"| {claim_id} |" in line), f"claim classification: {claim_id}")
    require("Do not claim Drupal recovery or continuation" in claims, "Drupal recovery claim guard")
    require("Do not claim immediate lock denial" in claims, "immediate denial claim guard")
    require("Do not use. Drupal recovery was not demonstrated" in claims, "three-way recovery claim guard")

    matrix = (content / "COMPARISON_MATRIX.md").read_text(encoding="utf-8")
    for phrase in (
        "termination-proof harness failed",
        "post-expiry read/lock observation",
        "full recovery continuation not demonstrated" if "full recovery continuation not demonstrated" in matrix else "replay-free completion were not demonstrated",
        "MODEL_FREE" if "MODEL_FREE" in matrix else "Model-free recovery mechanics passed",
        "no shared recovery conclusion or winner",
    ):
        require(phrase in matrix, f"comparison-matrix qualification: {phrase}")


def validate_evidence(repo: Path, contract: dict[str, Any]) -> None:
    count, digest, categories = evidence_inventory(repo / "evidence/gates/gate-2c")
    require(count == EVIDENCE_COUNT and digest == EVIDENCE_INVENTORY_SHA, "complete Gate 2C evidence inventory drift")
    require(categories == contract["retained_evidence_inventory"]["category_file_counts"], "evidence category counts")
    for relative, expected in EXPECTED_HASHES.items():
        require(sha(repo / relative) == expected, f"evidence/freeze drift: {relative}")

    observation = load_json(repo / OBSERVATION)
    require(observation.get("certifying_evidence") is False, "partial observation became certifying")
    require(observation.get("immediate_lock_denial_reconstructed") is False, "immediate proof fabricated")
    require(observation.get("historical_termination_proof_reconstructed") is False, "termination proof fabricated")
    require(observation.get("worker_launch_count") == 0 and observation.get("target_processing_count") == 0, "partial observation runtime boundary")
    require(observation.get("state_sha256_before") == observation.get("state_sha256_after"), "observed Drupal state mutation")

    final_names = {path.name for path in (repo / FINAL_DRUPAL_ROOT).iterdir() if path.is_file()}
    require(final_names == {"FAILED-ATTEMPT.json", "authorization-ledger.json", "drupal-pre-kill-process-scan.json"}, "final Drupal family gained fabricated evidence")
    require(not any((repo / FINAL_DRUPAL_ROOT / name).exists() for name in ("drupal-termination.json", "drupal-immediate.json", "drupal-recovery.json", "evidence-manifest.json")), "fabricated final Drupal proof")

    drupal_ids = sorted(path.name for path in (repo / "evidence/gates/gate-2c/model-free-rehearsals").iterdir() if path.is_dir() and path.name.startswith("gate2c-step02-drupal-"))
    require(drupal_ids == sorted(run_id for run_id, _digest in HISTORICAL_AGGREGATES), "new Drupal worker identity admitted")
    partial_root = repo / "evidence/gates/gate-2c/drupal-post-expiry-partial-observations"
    partial_files = [path for path in partial_root.rglob("*") if path.is_file()]
    require(len(partial_files) == 1 and partial_files[0].relative_to(repo).as_posix() == OBSERVATION, "second partial observation admitted")
    require(not (repo / "evidence/gates/gate-2c/step02-certification").exists(), "Step 2C.02 certification evidence exists")
    require(not any(path.name.startswith("GATE2C") and "LATEST" in path.name for path in (repo / "evidence/gates/gate-2c").glob("*LATEST*")), "new Gate 2C closure/certification pointer")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--content-root", type=Path)
    parser.add_argument("--mode", choices=["candidate", "synthetic-installed", "installed"], default="installed")
    args = parser.parse_args()
    repo = args.repo.resolve()
    content = (args.content_root or repo).resolve()
    require((repo / ".git").is_dir(), "repository required")
    provenance_state = validate_repository_lineage(repo, content)
    require(sha(repo / "shared/contracts/GATE2C-SHARED-FAILURE-RECOVERY-CONTRACT.json") == CONTRACT_SHA, "Gate 2C contract drift")

    run_predecessor_audit(repo)
    validate_source_manifest(content)
    schema = load_json(content / CLOSURE_SCHEMA)
    Draft202012Validator.check_schema(schema)
    contract = load_json(content / CLOSURE_CONTRACT)
    Draft202012Validator(schema).validate(contract)
    validate_contract_value(contract)
    contract_sha = sha(content / CLOSURE_CONTRACT)
    require((content / CLOSURE_SIDECAR).read_text(encoding="utf-8").strip() == f"{contract_sha}  GATE2C-CLOSURE-AND-DISPOSITION.json", "closure sidecar")
    validate_evidence(repo, contract)
    validate_documents(content, contract)

    if args.mode == "candidate":
        require(content != repo, "candidate audit requires sealed payload content")
    elif args.mode == "installed":
        require(content == repo, "installed audit must use repository content")
    else:
        require(content != repo, "synthetic-installed audit requires sealed payload content")

    print("[PASS] predecessor Step 2C.02 permanent audit and all immutable historical families")
    print("[PASS] exact three Drupal aggregates and exact non-certifying post-expiry observation")
    print("[PASS] LangGraph and CrewAI model-free outcomes remain qualified; Drupal outcome remains partial")
    print("[PASS] claims register, comparison matrix, closure contract, documentation, reset, and Gate 2 semantics are internally consistent")
    print(f"GATE_2C_CLOSURE_PROVENANCE_{provenance_state}")
    print("STEP_2C_02_TERMINAL_UNCERTIFIED")
    print("GATE_2C_CLOSED_NON_CERTIFYING_WITH_INCOMPLETE_EVIDENCE")
    print("GATE_2_NOT_COMPLETE")
    print("RESET_NOT_PERFORMED")
    print("NO_MORE_GATE_2C_RUNTIME_AUTHORIZED")
    if args.mode == "synthetic-installed":
        print("SYNTHETIC_INSTALLED_GATE_2C_FINAL_CLOSURE_AUDIT_PASS")
    print("GATE_2C_FINAL_CLOSURE_AUDIT_PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditFailure as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        raise SystemExit(1)
