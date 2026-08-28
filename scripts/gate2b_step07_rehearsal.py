#!/usr/bin/env python3
"""Real-composition rehearsal for the Step 2B.07 v1.0.1 acceptance repair."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CONSUMED_RUN = "gate2b-step07-20260828T135201Z-1ed07bea"
CONSUMED_REL = f"evidence/gates/gate-2b/evidence-synthesis/{CONSUMED_RUN}"


def need(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"[FAIL] {message}")


def command(args: list[str], cwd: Path, *, expect_success: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = f"{cwd / 'scripts'}:{cwd / 'crewai'}:{cwd}" + (f":{env['PYTHONPATH']}" if env.get("PYTHONPATH") else "")
    for key in ["OPENAI_API_KEY", "OPENAI_CANDIDATE_MODEL", "CREWAI_CANDIDATE_MODEL"]:
        env.pop(key, None)
    result = subprocess.run(args, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if expect_success:
        need(result.returncode == 0, f"command failed: {' '.join(args)}\n{result.stdout[-3000:]}")
    else:
        need(result.returncode != 0, f"negative control unexpectedly passed: {' '.join(args)}")
    return result


def load_auditor(payload: Path, repo: Path):
    sys.path.insert(0, str(repo / "scripts"))
    spec = importlib.util.spec_from_file_location("gate2b_step07_audit_v101", payload / "scripts/gate2b_step07_audit.py")
    need(spec is not None and spec.loader is not None, "unable to load repaired auditor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_failure(label: str, fn) -> None:
    try:
        fn()
    except (ValueError, SystemExit, subprocess.CalledProcessError):
        print(f"[PASS] negative: {label}")
        return
    raise SystemExit(f"[FAIL] negative control unexpectedly passed: {label}")


def mutate_json(path: Path, callback) -> None:
    value = json.loads(path.read_text())
    callback(value)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--payload", required=True)
    args = ap.parse_args()
    repo = Path(args.repo).resolve()
    payload = Path(args.payload).resolve()
    audit_script = payload / "scripts/gate2b_step07_audit.py"
    family = repo / CONSUMED_REL
    pointer = repo / "evidence/gates/gate-2b/evidence-synthesis/GATE2B-STEP07-LATEST.txt"
    need(family.is_dir() and not pointer.exists(), "real recovery predecessor shape is not present")

    current = command(["python3", str(repo / "scripts/gate2a_step10_audit.py"), "--repo", str(repo)], repo, expect_success=False)
    need("Step 2A.10 changed CLAIMS_REGISTER.md" in current.stdout, "current historical-auditor failure classification drift")
    print("[PASS] lifecycle distinction: historical Gate 2A.10 auditor against CURRENT Step 2B.07 documents = expected FAIL")

    hist = command(["python3", str(audit_script), "--repo", str(repo), "--mode", "historical-gate2a"], repo)
    need("Historical Gate 2A certification is valid" in hist.stdout, "historical Gate 2A result absent")
    print("[PASS] lifecycle distinction: unchanged Gate 2A.10 auditor at certified merge 0477e882 = PASS")

    preservation = command(["python3", str(audit_script), "--repo", str(repo), "--mode", "gate2a-preservation"], repo)
    need("245 certified Gate 2A frozen paths" in preservation.stdout, "current Gate 2A preservation result absent")
    print("[PASS] lifecycle distinction: current descendant frozen-evidence preservation = PASS")

    candidate = command(["python3", str(audit_script), "--repo", str(repo), "--mode", "candidate", "--evidence", str(family)], repo)
    need("lifecycle-correct candidate audit passed" in candidate.stdout, "real repaired composition result absent")
    print("[PASS] real composition: existing family + Step 2B.06 + historical Gate 2A + current preservation")

    audit = load_auditor(payload, repo)
    with tempfile.TemporaryDirectory(prefix="gate2b-step07-v101-controls-") as temp_name:
        temp = Path(temp_name)
        fake_repo = temp / "repo"
        fake_family = fake_repo / CONSUMED_REL
        fake_family.parent.mkdir(parents=True)
        shutil.copytree(family, fake_family)

        changed = temp / "changed-byte"
        shutil.copytree(fake_repo, changed)
        (changed / CONSUMED_REL / "summary.json").write_text((changed / CONSUMED_REL / "summary.json").read_text() + " ")
        expect_failure("changed consumed synthesis byte rejected", lambda: audit.verify_consumed_identity(changed, changed / CONSUMED_REL))

        manifest = temp / "manifest-tamper"
        shutil.copytree(fake_repo, manifest)
        mutate_json(manifest / CONSUMED_REL / "evidence-manifest.json", lambda v: v["entries"][0].update({"sha256": "0" * 64}))
        expect_failure("changed synthesis manifest rejected", lambda: audit.verify_consumed_identity(manifest, manifest / CONSUMED_REL))

        expect_failure("different synthesis run ID rejected", lambda: audit.verify_consumed_identity(repo, repo / "evidence/gates/gate-2b/evidence-synthesis/different-run"))

        missing = temp / "missing-proof"
        shutil.copytree(fake_repo, missing)
        mutate_json(missing / CONSUMED_REL / "claim-proof-map.json", lambda v: v["claims"][0].update({"evidence": []}))
        expect_failure("missing synthesis proof rejected", lambda: audit.verify_consumed_identity(missing, missing / CONSUMED_REL))

        doc_repo = temp / "docs"
        doc_repo.mkdir()
        for name in ["CLAIMS_REGISTER.md", "COMPARISON_MATRIX.md", "SOURCES.md"]:
            shutil.copy2(repo / name, doc_repo / name)
        p = doc_repo / "CLAIMS_REGISTER.md"
        original = p.read_text()
        p.write_text(original.replace("| hypothesis | Keep as an experiment question", "| observed | Keep as an experiment question", 1))
        expect_failure("unsupported claim promotion rejected", lambda: audit.verify_documents(doc_repo))
        p.write_text(original.replace("| architecture/probe | This is an approved pinned architecture", "| observed | This is an approved pinned architecture"))
        expect_failure("architecture/probe promotion rejected", lambda: audit.verify_documents(doc_repo))

        comparison = temp / "comparison"
        shutil.copytree(fake_repo, comparison)
        mutate_json(comparison / CONSUMED_REL / "comparison-synthesis.json", lambda v: v.update({"gate2c_status": "COMPLETE"}))
        expect_failure("Gate 2C completion rejected", lambda: audit.verify_consumed_identity(comparison, comparison / CONSUMED_REL))
        comparison2 = temp / "winner"
        shutil.copytree(fake_repo, comparison2)
        mutate_json(comparison2 / CONSUMED_REL / "comparison-synthesis.json", lambda v: v.update({"recovery_winner_claimed": True}))
        expect_failure("recovery winner rejected", lambda: audit.verify_consumed_identity(comparison2, comparison2 / CONSUMED_REL))
        comparison3 = temp / "production"
        shutil.copytree(fake_repo, comparison3)
        mutate_json(comparison3 / CONSUMED_REL / "comparison-synthesis.json", lambda v: v.update({"production_readiness_claimed": True}))
        expect_failure("production-readiness claim rejected", lambda: audit.verify_consumed_identity(comparison3, comparison3 / CONSUMED_REL))

        privacy = temp / "privacy-leak"
        shutil.copytree(fake_repo, privacy)
        leak = "Author" + "ization: Bearer " + "test-only-protected-value"
        mutate_json(privacy / CONSUMED_REL / "privacy-scan.json", lambda v: v.update({"forbidden_probe": leak}))
        expect_failure("privacy leak rejected", lambda: audit.verify_consumed_identity(privacy, privacy / CONSUMED_REL))

        gate2a = temp / "gate2a"
        command(["git", "clone", "--shared", "--no-hardlinks", str(repo), str(gate2a)], temp)
        for name in audit.GATE2A_MUTABLE_LATER:
            shutil.copy2(repo / name, gate2a / name)
        (gate2a / audit.GATE2A_FREEZE).write_text((gate2a / audit.GATE2A_FREEZE).read_text() + " ")
        expect_failure("altered Gate 2A frozen evidence rejected", lambda: audit.current_gate2a_preservation(gate2a))
        expect_failure("wrong Gate 2A freeze SHA rejected", lambda: audit.need(audit.sha(gate2a / audit.GATE2A_FREEZE) == audit.GATE2A_FREEZE_SHA, "wrong freeze"))
        expect_failure("invalid historical Gate 2A certification rejected", lambda: audit.historical_gate2a_certification(repo, audit.GATE2A_STEP09_MERGE))

        wrong_head = temp / "wrong-head"
        command(["git", "clone", "--shared", "--no-hardlinks", str(repo), str(wrong_head)], temp)
        command(["git", "checkout", "--detach", audit.GATE2A_CERT_MERGE], wrong_head)
        expect_failure("Step 2B.06 predecessor drift rejected", lambda: audit.verify_ancestry(wrong_head))

        no_snapshot = temp / "no-snapshot"
        no_snapshot.mkdir()
        expect_failure("missing snapshot rejected", lambda: audit.verify_snapshot(no_snapshot))

        pointer_repo = temp / "early-pointer"
        shutil.copytree(fake_repo, pointer_repo)
        early = pointer_repo / audit.POINTER
        early.parent.mkdir(parents=True, exist_ok=True)
        early.write_text(CONSUMED_REL + "\n")
        expect_failure("pointer creation before acceptance rejected", lambda: audit.resolve_evidence(pointer_repo, str(pointer_repo / CONSUMED_REL), "candidate"))

    wrapper = payload / "scripts/run-gate2b-step07-crewai-evidence-synthesis-and-comparison.sh"
    second = command(["bash", str(wrapper), "run", str(repo), "gate2b-step07-20990101T000000Z-00000000"], repo, expect_success=False)
    need("Synthesis run mode is permanently disabled" in second.stdout, "second synthesis rejection marker absent")
    print("[PASS] negative: second synthesis attempt rejected")

    operational = "\n".join((payload / "scripts" / name).read_text() for name in [
        "gate2b_step07_audit.py", "gate2b_step07_rehearsal.py",
        "run-gate2b-step07-crewai-evidence-synthesis-and-comparison.sh",
    ])
    for marker in ["import " + "openai", "from " + "openai", "ddev " + "snapshot", "submit_" + "recommendation(", "git " + "add", "git " + "commit"]:
        need(marker not in operational, f"prohibited operational path reachable: {marker}")
    print("[PASS] static boundary: no synthesis/model/provider/Drupal-write/snapshot/stage path is reachable")
    need(not pointer.exists(), "rehearsal created authoritative pointer")
    print("[PASS] pointer remains absent after rehearsal")
    print("[PASS] Gate 2B Step 2B.07 v1.0.1 real-composition rehearsal passed.")


if __name__ == "__main__":
    main()
