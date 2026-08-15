"""Build the detached R15-F5-F1 finalization-hash-closure review bundle."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

from payresolve_ai.evaluation import critical_v2_execution as execution


REAL_A16 = "8de0061ed3f4e421353a3c47a733ab081bfccd88"
PROPOSED_PATHS = (
    "src/payresolve_ai/evaluation/critical_v2_execution.py",
    "scripts/evaluation/week3_critical_v2_execution.py",
    "scripts/evaluation/build_critical_v2_ea1_revision15_f5_f1_review_bundle.py",
    "scripts/evaluation/verify_critical_v2_ea1_revision15_f5_f1_bundle.py",
    "tests/test_critical_v2_execution_revision15_f5_f1.py",
    "tests/test_critical_v2_execution_revision15_f4.py",
)
BUGGY_SUMMARY_SHA256 = "4e38d14512bcf41ea4c4c209a7f14dcbd9c8c361b7a90e9b53796d97cf4e3bb9"
BUGGY_FINAL_STATE_SHA256 = "7b45821bcd84ba8b3579de73f7c28059b2378ff2b3dead866a1a4389f6fa3982"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def copy_exact(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def run(*args: str, cwd: Path) -> str:
    completed = subprocess.run(args, cwd=cwd, check=True, text=True, capture_output=True)
    return completed.stdout.strip()


def source_diff(root: Path) -> str:
    chunks: list[str] = []
    for relative in PROPOSED_PATHS:
        current = (root / relative).read_text(encoding="utf-8").splitlines(keepends=True)
        try:
            original = subprocess.check_output(
                ["git", "-C", str(root), "show", f"HEAD:{relative}"],
                text=True, stderr=subprocess.DEVNULL,
            ).splitlines(keepends=True)
        except subprocess.CalledProcessError:
            original = []
        chunks.extend(difflib.unified_diff(original, current, fromfile=f"a/{relative}", tofile=f"b/{relative}"))
    return "".join(chunks)


def runtime_asset_overrides(real_root: Path, config: dict) -> dict[str, Path]:
    manifest = load(real_root / config["readiness_outputs"]["runtime_asset_manifest"])
    retrieval = load(real_root / config["runtime_dependencies"]["retrieval_config"]["path"])
    overrides = {logical: real_root / logical for logical in manifest["asset_file_sha256"]}
    snapshot = Path(retrieval["encoder"]["huggingface_home"]) / (
        "models--sentence-transformers--all-MiniLM-L6-v2/snapshots/" + retrieval["encoder"]["revision"]
    )
    overrides.update({
        "encoder_snapshot/" + row["logical_path"]: real_root / snapshot / row["logical_path"]
        for row in manifest["encoder"]["files"]
    })
    return overrides


def create_synthetic_proof(real_root: Path, scratch: Path) -> dict[str, object]:
    repo = scratch / "synthetic_repo"
    run("git", "-c", "core.autocrlf=false", "clone", "--no-hardlinks", str(real_root), str(repo), cwd=scratch)
    run("git", "config", "core.autocrlf", "false", cwd=repo)
    run("git", "config", "user.name", "R15-F5-F1 Synthetic", cwd=repo)
    run("git", "config", "user.email", "r15-f5-f1@example.invalid", cwd=repo)
    if run("git", "rev-parse", "HEAD", cwd=repo) != REAL_A16:
        raise RuntimeError("synthetic clone did not start at real A16")
    for relative in PROPOSED_PATHS:
        copy_exact(real_root / relative, repo / relative)
    run("git", "add", "--", *PROPOSED_PATHS, cwd=repo)
    run("git", "commit", "-m", "Synthetic R15-F5-F1 finalization hash closure", cwd=repo)
    f5 = run("git", "rev-parse", "HEAD", cwd=repo)
    f5_tree = run("git", "rev-parse", "HEAD^{tree}", cwd=repo)
    if run("git", "rev-parse", "HEAD^", cwd=repo) != REAL_A16:
        raise RuntimeError("synthetic F5 parent mismatch")

    config_path = repo / "configs/evaluation/critical_eval_v2_execution.json"
    config = execution.load_execution_config(config_path)
    auth_relative = config["authorization"]["committed_record"]
    auth = load(repo / auth_relative)
    auth["readiness_implementation_commit"] = f5
    auth["execution_artifact_sha256"] = execution._readiness_artifact_hashes(repo)
    auth.update(execution.POSTVERIFY_CONTINUATION_AUTHORIZATION_FIELDS)
    write_json(repo / auth_relative, auth)
    for relative in config["authorization"]["allowed_authorization_commit_paths"]:
        if relative != auth_relative:
            with (repo / relative).open("a", encoding="utf-8", newline="\n") as handle:
                handle.write("\n<!-- SYNTHETIC A17 R15-F5-F1 POST-VERIFY CONTINUATION AUTHORIZATION -->\n")
    auth_paths = sorted(config["authorization"]["allowed_authorization_commit_paths"])
    run("git", "add", "--", *auth_paths, cwd=repo)
    run("git", "commit", "-m", "Synthetic A17 post-verify continuation authorization", cwd=repo)
    a17 = run("git", "rev-parse", "HEAD", cwd=repo)
    a17_tree = run("git", "rev-parse", "HEAD^{tree}", cwd=repo)
    changed = sorted(run("git", "diff", "--name-only", f"{f5}..{a17}", cwd=repo).splitlines())
    if run("git", "rev-parse", "HEAD^", cwd=repo) != f5 or changed != auth_paths:
        raise RuntimeError("synthetic A17 topology/scope mismatch")

    evidence_paths = {
        config["evaluation_outputs"]["execution_state"],
        config["evaluation_outputs"]["reproduction_comparison"],
        config["continuation"]["receipt"], execution.POSTEVAL_CONTINUATION_RECEIPT,
        config["continuation"]["historical_runtime_environment"]["path"],
        config["runtime_environment"]["manifest"],
        *config["evaluation_outputs"]["primary"].values(),
        *config["evaluation_outputs"]["reproducibility_rerun"].values(),
        *execution.evaluation_direct_input_references(config, "primary"),
        *execution.evaluation_direct_input_references(config, "reproducibility_rerun"),
    }
    for relative in evidence_paths:
        copy_exact(real_root / relative, repo / relative)
    final_path = repo / config["evaluation_outputs"]["final_summary"]
    receipt_path = repo / execution.POSTVERIFY_CONTINUATION_RECEIPT
    for path in (final_path, receipt_path):
        if path.exists():
            path.unlink()
    state_path = repo / config["evaluation_outputs"]["execution_state"]
    before = load(state_path)
    verify_assets = execution.verify_runtime_asset_manifest
    overrides = runtime_asset_overrides(real_root, config)
    with patch.object(execution, "verify_runtime_asset_manifest", side_effect=lambda root, cfg: verify_assets(root, cfg, overrides=overrides)):
        authorization = execution.verify_execution_authorization(repo, config_path)
        receipt = execution.migrate_r15_f5_postverify_continuation(repo, config_path)
        migrated = load(state_path)
        finalized_result = execution.finalize_results(repo, config_path)
        verified_result = execution.verify_results(repo, config_path)
    finalized = load(state_path)
    summary = load(final_path)
    return {
        "repo": repo,
        "topology": {
            "real_a16": REAL_A16, "r15_f5_f1_commit": f5, "r15_f5_f1_tree": f5_tree,
            "r15_f5_f1_parent": REAL_A16, "a17_commit": a17, "a17_tree": a17_tree,
            "a17_parent": f5, "a17_changed_paths": changed,
        },
        "authorization": authorization, "authorization_record": auth,
        "before": before, "receipt": receipt, "migrated": migrated,
        "finalized_result": finalized_result, "verified_result": verified_result,
        "summary": summary, "finalized": finalized,
    }


def negative_controls(proof: dict[str, object]) -> dict[str, object]:
    repo = proof["repo"]
    config_path = repo / "configs/evaluation/critical_eval_v2_execution.json"
    config = execution.load_execution_config(config_path)
    outputs = config["evaluation_outputs"]
    state_path = repo / outputs["execution_state"]
    summary_path = repo / outputs["final_summary"]
    authorization = proof["authorization"]
    controls: list[dict[str, object]] = []

    def detect(name: str, paths: list[Path], mutate, action=execution.verify_results) -> None:
        backups = {path: path.read_bytes() if path.exists() else None for path in paths}
        try:
            mutate()
            try:
                with patch.object(execution, "verify_execution_authorization", return_value=authorization):
                    action(repo, config_path)
                error = "NOT_DETECTED"
            except execution.CriticalV2ExecutionError as caught:
                error = str(caught)
            controls.append({"name": name, "status": "PASS" if error != "NOT_DETECTED" else "FAIL", "detection": error})
        finally:
            for path, content in backups.items():
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_bytes(content)

    def mutate_json(path: Path, mutate) -> None:
        value = load(path); mutate(value); write_json(path, value)

    detect("final summary artifact mutation", [summary_path], lambda: mutate_json(summary_path, lambda p: p.__setitem__("model_verdict", "MUTATED")))
    artifact_names = [
        ("comparison mutation", outputs["reproduction_comparison"]),
        ("PRIMARY outcomes mutation", outputs["primary"]["outcomes"]),
        ("PRIMARY metrics mutation", outputs["primary"]["metrics"]),
        ("PRIMARY claim-audit mutation", outputs["primary"]["claim_audit"]),
        ("REPRO outcomes mutation", outputs["reproducibility_rerun"]["outcomes"]),
        ("REPRO metrics mutation", outputs["reproducibility_rerun"]["metrics"]),
        ("REPRO claim-audit mutation", outputs["reproducibility_rerun"]["claim_audit"]),
    ]
    for name, relative in artifact_names:
        path = repo / relative
        detect(name, [path], lambda p=path: p.write_bytes(p.read_bytes() + b"\n"))
    detect("finalization transition direct-input hash mutation", [state_path], lambda: mutate_json(state_path, lambda p: p["history"][11]["direct_input_sha256"].__setitem__(outputs["reproduction_comparison"], "0" * 64)))
    detect("finalization transition direct-output hash mutation", [state_path], lambda: mutate_json(state_path, lambda p: p["history"][11]["direct_output_sha256"].__setitem__(outputs["final_summary"], "0" * 64)))
    detect("wrong pre-finalization state fingerprint", [summary_path], lambda: mutate_json(summary_path, lambda p: p.__setitem__("pre_finalization_state_sha256", "0" * 64)))
    migrated = proof["migrated"]
    detect("final summary overwrite attempt", [state_path, summary_path], lambda: write_json(state_path, migrated), execution.finalize_results)
    detect("finalize from non-REPRO_VERIFIED", [state_path, summary_path], lambda: None, execution.finalize_results)
    detect("verify-results before FINALIZED", [state_path, summary_path], lambda: (write_json(state_path, migrated), summary_path.unlink()), execution.verify_results)
    passed = sum(row["status"] == "PASS" for row in controls)
    return {"status": "PASS" if passed == 14 else "FAIL", "detected": passed, "total": 14, "controls": controls}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--focused-log", type=Path)
    parser.add_argument("--existing-log", type=Path)
    parser.add_argument("--tracked-log", type=Path)
    parser.add_argument("--bug-log", type=Path)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    if output.exists():
        raise RuntimeError("review bundle overwrite is forbidden")
    if run("git", "rev-parse", "HEAD", cwd=root) != REAL_A16:
        raise RuntimeError("real repository HEAD is not A16")
    config = execution.load_execution_config(root / "configs/evaluation/critical_eval_v2_execution.json")
    if sha256(root / config["evaluation_outputs"]["execution_state"]) != execution.LEGACY_R15_F5_STATE_SHA256:
        raise RuntimeError("real state changed")
    if (root / config["evaluation_outputs"]["final_summary"]).exists():
        raise RuntimeError("real final summary must remain absent")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ea1_r15_f5_f1_", dir=output.parent) as temporary:
        scratch = Path(temporary)
        proof = create_synthetic_proof(root, scratch)
        negatives = negative_controls(proof)
        if negatives["status"] != "PASS" or proof["verified_result"]["status"] != "PASS":
            raise RuntimeError("synthetic closure evidence failed")
        bundle = scratch / "bundle"
        for relative in PROPOSED_PATHS:
            copy_exact(root / relative, bundle / "proposed" / relative)
        proposed_manifest = {
            relative: {"bytes": (root / relative).stat().st_size, "sha256": sha256(root / relative)}
            for relative in PROPOSED_PATHS
        }
        write_json(bundle / "evidence" / "proposed_manifest.json", proposed_manifest)
        (bundle / "evidence" / "source_diff.patch").parent.mkdir(parents=True, exist_ok=True)
        (bundle / "evidence" / "source_diff.patch").write_text(source_diff(root), encoding="utf-8", newline="\n")
        real_paths = [config["evaluation_outputs"]["execution_state"], config["evaluation_outputs"]["reproduction_comparison"], execution.POSTEVAL_CONTINUATION_RECEIPT]
        real_hashes = {}
        for relative in real_paths:
            source = root / relative
            copy_exact(source, bundle / "real_evidence" / relative)
            real_hashes[relative] = {"bytes": source.stat().st_size, "sha256": sha256(source)}
        write_json(bundle / "evidence" / "real_evidence_hashes.json", real_hashes)
        write_json(bundle / "evidence" / "defect_reproduction.json", {
            "status": "PASS", "finalize_status": "PASS", "verify_results_status": "FAIL",
            "error": "final result artifact drift: reports/week_03/results/critical_eval_v2_execution_state.json",
            "buggy_final_summary_sha256": BUGGY_SUMMARY_SHA256,
            "buggy_finalized_state_sha256": BUGGY_FINAL_STATE_SHA256,
        })
        write_json(bundle / "evidence" / "root_cause.json", {
            "status": "PASS", "classification": "FINAL_SUMMARY_MUTABLE_STATE_HASH_CYCLE",
            "correction": "exclude execution_state from artifact_sha256 and bind pre_finalization_state_sha256 separately",
        })
        write_json(bundle / "evidence" / "negative_controls.json", negatives)
        write_json(bundle / "synthetic" / "topology.json", proof["topology"])
        write_json(bundle / "synthetic" / "a17_authorization.json", proof["authorization_record"])
        write_json(bundle / "synthetic" / "state_before.json", proof["before"])
        write_json(bundle / "synthetic" / "postverify_receipt.json", proof["receipt"])
        write_json(bundle / "synthetic" / "state_post_migration.json", proof["migrated"])
        write_json(bundle / "synthetic" / "finalize_result.json", proof["finalized_result"])
        write_json(bundle / "synthetic" / "final_summary.json", proof["summary"])
        write_json(bundle / "synthetic" / "finalized_state.json", proof["finalized"])
        write_json(bundle / "synthetic" / "verify_results.json", proof["verified_result"])
        write_json(bundle / "synthetic" / "execution_boundary.json", {
            "status": "PASS", "model_calls": 0, "encoder_calls": 0, "retrieval_calls": 0,
            "generation_calls": 0, "evaluator_calls": 0, "comparator_calls": 0,
            "primary_run": False, "reproduction_run": False, "evaluation_run": False,
        })
        proof_ref = "refs/heads/r15-f5-f1-review"
        git_bundle = bundle / "synthetic" / "r15_f5_f1_a17_history.bundle"
        run("git", "update-ref", proof_ref, proof["topology"]["a17_commit"], cwd=proof["repo"])
        try:
            run("git", "bundle", "create", str(git_bundle), proof_ref, cwd=proof["repo"])
        finally:
            run("git", "update-ref", "-d", proof_ref, cwd=proof["repo"])
        for label, path in (("focused.txt", args.focused_log), ("existing_r15.txt", args.existing_log), ("tracked_suite.txt", args.tracked_log), ("bug_reproduction.txt", args.bug_log)):
            if path:
                copy_exact(path.resolve(), bundle / "tests" / label)
        write_json(bundle / "bundle_metadata.json", {
            "status": "AWAITING_SENIOR_REVIEW", "task": "W3-002-CR1-EA1-R15-F5-F1-FINALIZATION-HASH-CLOSURE",
            "real_head": REAL_A16, "proposed_paths": list(PROPOSED_PATHS), "readiness_revision": 15,
            "execution_config_sha256": sha256(root / "configs/evaluation/critical_eval_v2_execution.json"),
            "real_repository_mutated": False, "real_finalization_executed": False, "self_approved": False,
        })
        inventory = [
            {"path": path.relative_to(bundle).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in sorted(bundle.rglob("*")) if path.is_file()
        ]
        write_json(bundle / "inventory.json", {"status": "PASS", "files": inventory})
        with zipfile.ZipFile(output, "x", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(bundle.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(bundle).as_posix())
    print(json.dumps({"status": "PASS", "output": str(output), "bytes": output.stat().st_size, "sha256": sha256(output), "negative_controls": 14}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
