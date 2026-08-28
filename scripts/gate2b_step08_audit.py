#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from gate2b_step08_certify import (
    BATCH,
    CLAIMS,
    FREEZE,
    HANDOFF,
    HASHES,
    POINTER,
    PREDECESSOR,
    ROOT,
    SYNTH,
)

STEP06_MERGE = "78ba79165378ac2905801d994682aa385cdfb607"
STEP07_SECOND_PARENT = "e45e90d8f03f86c28f9f01e8fae764cd67d5c9b3"
SNAPSHOT = (
    "drupal/.ddev/db_snapshots/"
    "gate2b-step06-post-step2b05-recovery-20260826T152003Z-mariadb_11.8.zst"
)
SNAPSHOT_SHA256 = "4ba4cece2d30a5f90699afdf9a2ab2094f0d902213c66cdc0b40dfa466094906"
SNAPSHOT_SIZE = 4_112_532
FINAL_DOCS = (
    "AGENTS.md",
    "PLAN.md",
    "README.md",
    "docs/CURRENT-STATUS.md",
    "docs/CODEX-GATE-2B-RUNBOOK.md",
)


def need(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("[ERROR] " + message)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(args: list[str], repo: Path) -> str:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = ":".join(
        [str(repo / "scripts"), str(repo / "crewai"), str(repo)]
    )
    for key in ("OPENAI_API_KEY", "OPENAI_CANDIDATE_MODEL", "CREWAI_CANDIDATE_MODEL"):
        env.pop(key, None)
    with tempfile.TemporaryDirectory(prefix="gate2b-step08-audit-xdg-") as temp:
        xdg = Path(temp)
        env.update(
            {
                "XDG_DATA_HOME": str(xdg / "data"),
                "XDG_CONFIG_HOME": str(xdg / "config"),
                "XDG_CACHE_HOME": str(xdg / "cache"),
            }
        )
        result = subprocess.run(
            args,
            cwd=repo,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    need(result.returncode == 0, "predecessor audit failed:\n" + result.stdout[-4000:])
    return result.stdout


def predecessor(repo: Path) -> None:
    parents = subprocess.check_output(
        ["git", "-C", str(repo), "show", "-s", "--format=%P", PREDECESSOR],
        text=True,
    ).split()
    need(parents == [STEP06_MERGE, STEP07_SECOND_PARENT], "Step 2B.07 merge parents drift")
    need(
        subprocess.run(
            ["git", "-C", str(repo), "merge-base", "--is-ancestor", PREDECESSOR, "HEAD"]
        ).returncode
        == 0,
        "Step 2B.07 merge ancestry absent",
    )
    py = str(repo / "crewai/.venv/bin/python")
    command(
        [py, str(repo / "scripts/gate2b_step01_audit.py"), "--repo", str(repo), "--evidence-required"],
        repo,
    )
    command(
        [py, str(repo / "scripts/gate2b_step02_audit.py"), "--repo", str(repo), "--closure"],
        repo,
    )
    for step in ("03", "04", "05"):
        command(
            [
                py,
                str(repo / f"scripts/gate2b_step{step}_audit.py"),
                "--repo",
                str(repo),
                "--phase",
                "permanent",
            ],
            repo,
        )
    batch = repo / f"evidence/results/crewai/{BATCH}"
    supplement = repo / (
        f"evidence/gates/gate-2b/frozen-batch-governance-supplement/{BATCH}/"
        "gate2b-step06-governance-supplement-v103"
    )
    final_governance = repo / (
        f"evidence/gates/gate-2b/frozen-batch-final-governance/{BATCH}/"
        "gate2b-step06-final-governance-v104"
    )
    command(
        [
            py,
            str(repo / "scripts/gate2b_step06_audit.py"),
            "--repo",
            str(repo),
            "--mode",
            "final-composite",
            "--evidence",
            str(batch),
            "--supplement",
            str(supplement),
            "--final-governance",
            str(final_governance),
        ],
        repo,
    )
    for mode in ("historical-gate2a", "gate2a-preservation", "permanent"):
        command(
            [
                py,
                str(repo / "scripts/gate2b_step07_audit.py"),
                "--repo",
                str(repo),
                "--mode",
                mode,
            ],
            repo,
        )
    need(
        sha(repo / "shared/contracts/GATE2A-LANGGRAPH-FREEZE.json")
        == "a28361c34b9d1c2089eee786324ad34cffbf54e3495f59a276c489865e5630f0",
        "Gate 2A freeze drift",
    )
    need(
        sha(repo / "crewai/uv.lock")
        == "855e5edff2cb86eb64ea9856d239b19010e7d3b1f80c40e370ed81d66b8e4e7c",
        "lock drift",
    )
    snapshot = repo / SNAPSHOT
    need(
        snapshot.is_file()
        and not snapshot.is_symlink()
        and snapshot.stat().st_size == SNAPSHOT_SIZE
        and sha(snapshot) == SNAPSHOT_SHA256,
        "snapshot drift",
    )
    need(
        subprocess.run(
            ["git", "-C", str(repo), "check-ignore", "-q", str(snapshot)]
        ).returncode
        == 0,
        "snapshot is not ignored/local-only",
    )
    synth = repo / f"evidence/gates/gate-2b/evidence-synthesis/{SYNTH}"
    expected = {
        "claim-proof-map.json": HASHES["step2b07_claim_map"],
        "comparison-synthesis.json": HASHES["step2b07_comparison"],
        "privacy-scan.json": HASHES["step2b07_privacy"],
        "summary.json": HASHES["step2b07_summary"],
        "evidence-manifest.json": HASHES["step2b07_manifest"],
    }
    for name, digest in expected.items():
        need(sha(synth / name) == digest, "Step 2B.07 synthesis drift: " + name)
    print("[PASS] Steps 2B.01-2B.05 retained proof passed")
    print("[PASS] Step 2B.06 permanent composite passed")
    print("[PASS] Step 2B.07 permanent audit passed")
    print("[PASS] Gate 2A historical certification and 245-path preservation passed")
    print("[PASS] retained snapshot is present, byte-identical, local-only, and ignored")


def family(root: Path, runrel: str) -> None:
    run = root / runrel
    need(run.is_dir() and not run.is_symlink(), "certification family missing")
    expected_files = {
        "certification.json",
        "certified-bindings.json",
        "freeze-projection.json",
        "privacy-scan.json",
        "handoff-state.json",
        "evidence-manifest.json",
    }
    children = list(run.iterdir())
    need(
        all(path.is_file() and not path.is_symlink() for path in children)
        and {path.name for path in children} == expected_files,
        "certification file set drift or unsafe entry",
    )
    manifest = json.loads((run / "evidence-manifest.json").read_text())
    need(len(manifest.get("entries", [])) == 5, "manifest entry count drift")
    for row in manifest["entries"]:
        path = run / row["path"]
        need(
            path.is_file()
            and not path.is_symlink()
            and row["sha256"] == sha(path)
            and row["size"] == path.stat().st_size,
            "manifest integrity drift: " + row["path"],
        )
    cert = json.loads((run / "certification.json").read_text())
    bind = json.loads((run / "certified-bindings.json").read_text())
    projection = json.loads((run / "freeze-projection.json").read_text())
    freeze_path = root / FREEZE
    handoff_path = root / HANDOFF
    need(freeze_path.is_file() and not freeze_path.is_symlink(), "freeze missing or unsafe")
    need(handoff_path.is_file() and not handoff_path.is_symlink(), "handoff missing or unsafe")
    freeze = json.loads(freeze_path.read_text())
    privacy = json.loads((run / "privacy-scan.json").read_text())
    handoff = json.loads((run / "handoff-state.json").read_text())
    need(
        cert["status"] == "pass"
        and cert["model_free"]
        and cert["drupal_read_only"]
        and not cert["synthesis_rerun"]
        and not cert["batch_rerun"],
        "certification boundary drift",
    )
    need(
        bind["accepted_batch"] == BATCH
        and bind["accepted_synthesis"] == SYNTH
        and bind["claims"] == CLAIMS
        and bind["organs"]
        == ["context", "tools", "state", "verification", "human-review", "lifecycle"],
        "candidate binding drift",
    )
    need(
        bind["hashes"] == HASHES
        and bind["false_symmetry_guard"] == "pass"
        and bind["gate_2c"] == "DEFERRED_UNCLAIMED"
        and bind["gate_2_overall"] == "NOT_COMPLETE",
        "hash/six-organ/Gate 2C binding drift",
    )
    need(
        not {
            "framework_superiority",
            "production_readiness",
            "recovery_winner",
            "gate_2c_complete",
        }.intersection(freeze),
        "prohibited freeze claim present",
    )
    projection["certification_evidence_manifest_sha256"] = sha(run / "evidence-manifest.json")
    need(freeze == projection, "freeze projection drift")
    need(
        freeze["status"] == "certified"
        and freeze["certification_run_id"] == run.name
        and freeze["python"] == "3.12.13"
        and freeze["crewai"] == "1.15.10"
        and freeze["crewai_tools"] == "1.15.10",
        "freeze identity/version drift",
    )
    need(
        privacy["status"] == "pass"
        and privacy["prohibited_value_hits"] == 0
        and handoff["gate_2c"] == "DEFERRED_UNCLAIMED"
        and handoff["gate_2_overall"] == "NOT_COMPLETE",
        "privacy/handoff state drift",
    )
    handoff_text = handoff_path.read_text()
    need(
        sha(freeze_path) in handoff_text
        and "Gate 2 overall is not complete" in handoff_text
        and "No identical three-framework" in handoff_text,
        "handoff binding drift",
    )
    combined = "\n".join(path.read_text() for path in run.iterdir() if path.is_file())
    combined += handoff_text
    for token in (
        "sk-proj-",
        "Authorization: Basic ",
        "Authorization: Bearer ",
        "data:image/",
        "OPENAI_API_KEY=",
    ):
        need(token not in combined, "privacy pattern found")


def lifecycle_documents(docs_root: Path, artifact_root: Path, runrel: str) -> None:
    documents: dict[str, str] = {}
    for relative in FINAL_DOCS:
        path = docs_root / relative
        need(path.is_file() and not path.is_symlink(), "lifecycle document missing or unsafe: " + relative)
        documents[relative] = path.read_text()
    required = {
        "PLAN.md": (
            "Gate 2B is certified and frozen.",
            "Step 2B.06 — complete, normally merged at `78ba79165378ac2905801d994682aa385cdfb607`",
            "Step 2B.07 — evidence synthesis and comparison update (model-free claim/proof mapping; merged and post-merge audited)",
            "Step 2B.08 — certification, freeze, and Gate 2C handoff complete",
            "Gate 2C shared failure/recovery remains deferred and unclaimed.",
        ),
        "docs/CURRENT-STATUS.md": (
            "**Certification predecessor:** `main` at normal Step 2B.07 merge `50e7296406a39de23b20bdfb1b45960dca13d3a1`",
            "**Gate 2B — CrewAI:** certified and frozen",
            "**Step 2B.07:** complete, normally merged at `50e7296406a39de23b20bdfb1b45960dca13d3a1`",
            "**Step 2B.08:** complete.",
            "Gate 2 overall is `NOT_COMPLETE`",
        ),
        "docs/CODEX-GATE-2B-RUNBOOK.md": (
            "Accepted synthesis `gate2b-step07-20260828T135201Z-1ed07bea` is immutable.",
            "Never invoke its disabled synthesis mode or allocate another synthesis identity.",
            "**Step 2B.08 certification:** complete and permanently accepted.",
            "Gate 2C remains `DEFERRED_UNCLAIMED`; Gate 2 overall remains `NOT_COMPLETE`.",
        ),
        "AGENTS.md": (
            "**Step 2B.07:** complete, normally merged at `50e7296406a39de23b20bdfb1b45960dca13d3a1`",
            "**Step 2B.08:** complete after permanent acceptance",
            "Gate 2B is certified and frozen.",
            "Gate 2C remains deferred",
        ),
        "README.md": (
            "**Step 2B.08:** complete; permanent audit binds its exactly-once certification family",
            "Gate 2B CrewAI is certified and frozen.",
            "Gate 2 overall remains incomplete.",
        ),
    }
    for relative, snippets in required.items():
        for snippet in snippets:
            need(snippet in documents[relative], f"lifecycle assertion missing in {relative}: {snippet}")
    stale_patterns = (
        "BATCH_COMPLETE_AWAITING_RESTORE",
        "restore not executed",
        "gate-2b-step07-crewai-evidence-synthesis-and-comparison`; predecessor",
        "run-gate2b-step07-crewai-evidence-synthesis-and-comparison.sh` run",
        "Step 2B.08 — not started",
        "Step 2B.08 remains deferred",
        "Step 2B.08 certification/freeze and Gate 2C remain deferred",
        "Gate 2B is not certified",
        "Gate 2B — CrewAI:** current",
        "Gate 2C is `COMPLETE`",
        "Gate 2 overall is complete",
    )
    for relative, text in documents.items():
        for line in text.splitlines():
            lowered = line.casefold()
            if any(marker in lowered for marker in ("historical", "rejected preview", "at that boundary")):
                continue
            for pattern in stale_patterns:
                need(pattern.casefold() not in lowered, f"lifecycle contradiction in {relative}: {pattern}")
    pointer = artifact_root / POINTER
    freeze_path = artifact_root / FREEZE
    handoff_path = artifact_root / HANDOFF
    run = artifact_root / runrel
    need(pointer.is_file() and not pointer.is_symlink(), "certified lifecycle text lacks exact pointer")
    need(pointer.read_text().strip() == runrel, "lifecycle certification pointer drift")
    need(
        run.is_dir() and freeze_path.is_file() and handoff_path.is_file(),
        "certified lifecycle text lacks evidence/freeze/handoff",
    )
    freeze = json.loads(freeze_path.read_text())
    need(
        freeze.get("status") == "certified"
        and freeze.get("certification_run_id") == Path(runrel).name,
        "certified lifecycle text is not bound to accepted freeze identity",
    )
    need(sha(freeze_path) in handoff_path.read_text(), "certified lifecycle handoff is not freeze-bound")
    print("[PASS] lifecycle-document semantic coherence and certification binding passed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument(
        "--mode",
        choices=("predecessor", "candidate", "rehearsal", "permanent"),
        default="permanent",
    )
    parser.add_argument("--root")
    parser.add_argument("--run-rel")
    parser.add_argument("--docs-root")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    if args.mode != "rehearsal":
        predecessor(repo)
    if args.mode == "predecessor":
        print("[PASS] Step 2B.08 lifecycle-correct predecessor audit passed")
        return
    root = Path(args.root).resolve() if args.root else repo
    docs_root = Path(args.docs_root).resolve() if args.docs_root else root
    if args.mode == "rehearsal":
        need(root != repo, "rehearsal mode cannot audit authoritative repository output")
        need(
            args.run_rel is not None and args.docs_root is not None,
            "rehearsal mode requires explicit disposable roots",
        )
    if args.run_rel:
        runrel = args.run_rel
    else:
        pointer = root / POINTER
        need(pointer.is_file() and not pointer.is_symlink(), "certification pointer missing")
        runrel = pointer.read_text().strip()
    need(
        runrel.startswith(ROOT + "/gate2b-step08-")
        and ".." not in runrel
        and not runrel.startswith("/"),
        "pointer/run identity unsafe",
    )
    family(root, runrel)
    lifecycle_documents(docs_root, root, runrel)
    print("[PASS] Gate 2B Step 2B.08 certification/freeze/handoff audit passed")
    print(
        "STEP_2B_08_COMPLETE\nGATE_2B_CERTIFIED\nGATE_2B_FROZEN\n"
        "GATE_2C_DEFERRED_UNCLAIMED\nGATE_2_NOT_COMPLETE\nSNAPSHOT_RETAINED"
    )


if __name__ == "__main__":
    main()
