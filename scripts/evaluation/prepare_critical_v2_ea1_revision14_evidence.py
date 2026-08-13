"""Prepare bounded R14 authorization-verifier evidence without running evaluation."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import numpy as np

from payresolve_ai.evaluation import critical_v2_execution as execution
from payresolve_ai.retrieval import benchmark


R13_COMMIT = "5d862e708f972b2fa73403fef390f2ac7b432435"
EXPECTED_ENVIRONMENT_SHA = "17cd6dcf9d20d8b17d14369a10ba915f3047e27fffb7eec5771738442923fd97"
EXPECTED_PACKAGE_SHA = "39c1c4a09994f3ea0b7691c796b39085f95fb985efa73207057fa5f7c187f25a"
EXPECTED_VECTOR_SHA = "83483507be7e9c48ca8caff139e15dc3e1f88509addd55793b7fc96e95f87f8e"
DIAGNOSTIC_TEXT = "EA1_OFFLINE_ENCODER_DIAGNOSTIC_DO_NOT_SCORE"
ALLOWED_A14_PATHS = {
    "reports/week_03/results/critical_eval_v2_evaluation_authorization.json",
    "PROJECT_STATE.md",
    "TASKS.md",
    "reports/week_03/week_03_summary.md",
    "reports/week_03/daily/2026-08-13.md",
}
R14_OVERLAY_PATHS = {
    "configs/evaluation/critical_eval_v2_authorization_topology.json",
    "configs/evaluation/critical_eval_v2_execution.json",
    "configs/evaluation/critical_eval_v2_execution_state_machine.json",
    "configs/evaluation/critical_eval_v2_metric_contract.json",
    "reports/week_03/results/critical_eval_v2_evaluation_authorization_candidate.json",
    "src/payresolve_ai/evaluation/critical_v2_execution.py",
    "tests/test_critical_v2_execution_readiness.py",
    "tests/test_critical_v2_execution_revision14.py",
}


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git(root: Path, *args: str, env: dict[str, str] | None = None) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, stderr=subprocess.STDOUT, env=env
    ).strip()


def final_authorization(candidate: dict, readiness: str) -> dict:
    payload = copy.deepcopy(candidate)
    payload.update(
        {
            "authorization_status": "AUTHORIZED_FOR_PRIMARY_EXECUTION",
            "evaluation_authorized": True,
            "readiness_commit_binding": "BOUND_TO_REVIEWED_READINESS_IMPLEMENTATION_COMMIT",
            "readiness_implementation_commit": readiness,
            "senior_authorization_claimed": True,
            "senior_authorization_verdict": "APPROVE_EXECUTION",
        }
    )
    return payload


def field_controls(root: Path, config_path: Path, config: dict, candidate: dict) -> dict:
    exact = final_authorization(candidate, "1" * 40)
    execution._validate_authorization_payload(root, config_path, config, exact)
    cases = {
        "AUTH-FIELD-01": ("readiness_revision", 13),
        "AUTH-FIELD-02": ("readiness_revision", 12),
        "AUTH-FIELD-03": ("authorization_status", "WRONG"),
        "AUTH-FIELD-04": ("readiness_commit_binding", "WRONG"),
        "AUTH-FIELD-05": ("senior_authorization_claimed", False),
        "AUTH-FIELD-06": ("semantic_review_approved", False),
        "AUTH-FIELD-07": ("candidate_revision", 8),
        "AUTH-FIELD-08": ("task_id", "WRONG"),
        "AUTH-FIELD-09": ("authorization_topology", "WRONG"),
        "AUTH-FIELD-10": ("senior_authorization_verdict", "REJECT"),
        "AUTH-FIELD-11": ("evaluation_authorized", False),
    }
    results = []
    for case, (field, value) in cases.items():
        mutated = copy.deepcopy(exact)
        mutated[field] = value
        try:
            execution._validate_authorization_payload(root, config_path, config, mutated)
        except execution.CriticalV2ExecutionError as error:
            results.append(
                {"case": case, "field": field, "status": "REJECTED_BEFORE_MODEL_LOAD", "error": str(error)}
            )
        else:
            raise RuntimeError(f"final authorization field mutation passed: {case}")
    return {"status": "PASS", "positive": "PASS", "case_count": len(results), "cases": results,
            "model_loader_calls": 0, "gold_loader_calls": 0, "evaluator_calls": 0}


def _topology_repo(changed: set[str], wrong_parent: bool) -> tuple[tempfile.TemporaryDirectory, Path, dict, dict]:
    temporary = tempfile.TemporaryDirectory(prefix="ea1_r14_topology_evidence_")
    repo = Path(temporary.name)
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    for key, value in (("user.email", "r14@example.com"), ("user.name", "R14 Evidence"), ("core.autocrlf", "false")):
        subprocess.run(["git", "config", key, value], cwd=repo, check=True)
    for relative in ALLOWED_A14_PATHS | changed | {"exec.py"}:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("R14 readiness\n", encoding="utf-8", newline="\n")
    subprocess.run(["git", "add", "--all"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "R14"], cwd=repo, check=True, capture_output=True)
    readiness = git(repo, "rev-parse", "HEAD")
    for relative in changed:
        (repo / relative).write_text("A14 authorization\n", encoding="utf-8", newline="\n")
    subprocess.run(["git", "add", "--all"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "A14"], cwd=repo, check=True, capture_output=True)
    authorization = {
        "readiness_implementation_commit": "0" * 40 if wrong_parent else readiness,
        "execution_artifact_sha256": {"exec.py": execution.sha256_file(repo / "exec.py")},
    }
    config = {"authorization": {"allowed_authorization_commit_paths": sorted(ALLOWED_A14_PATHS)}}
    return temporary, repo, authorization, config


def topology_controls() -> dict:
    auth = "reports/week_03/results/critical_eval_v2_evaluation_authorization.json"
    exact = set(ALLOWED_A14_PATHS)
    cases = {
        "AUTH-TOPO-01": (exact, False, True),
        "AUTH-TOPO-02": ({auth}, False, False),
        "AUTH-TOPO-03": (exact - {"PROJECT_STATE.md"}, False, False),
        "AUTH-TOPO-04": (exact - {"TASKS.md"}, False, False),
        "AUTH-TOPO-05": (exact - {"reports/week_03/week_03_summary.md"}, False, False),
        "AUTH-TOPO-06": (exact - {"reports/week_03/daily/2026-08-13.md"}, False, False),
        "AUTH-TOPO-07": (exact | {"src/payresolve_ai/extra.py"}, False, False),
        "AUTH-TOPO-08": (exact | {"configs/evaluation/extra.json"}, False, False),
        "AUTH-TOPO-09": ((exact - {"reports/week_03/daily/2026-08-13.md"}) | {"reports/week_03/daily/2026-08-12.md"}, False, False),
        "AUTH-TOPO-10": (exact | {"reports/week_03/daily/2026-08-12.md"}, False, False),
        "AUTH-TOPO-11": ((exact - {"reports/week_03/daily/2026-08-13.md"}) | {"reports/week_03/daily/2026-08-14.md"}, False, False),
        "AUTH-TOPO-12": (exact, True, False),
    }
    results = []
    for case, (changed, wrong_parent, should_pass) in cases.items():
        temporary, repo, authorization, config = _topology_repo(changed, wrong_parent)
        try:
            try:
                execution._verify_authorization_topology(repo, config, authorization, auth)
            except execution.CriticalV2ExecutionError as error:
                if should_pass:
                    raise
                results.append({"case": case, "status": "REJECTED_BEFORE_MODEL_LOAD", "error": str(error)})
            else:
                if not should_pass:
                    raise RuntimeError(f"topology mutation passed: {case}")
                results.append({"case": case, "status": "PASS"})
        finally:
            temporary.cleanup()
    return {"status": "PASS", "case_count": len(results), "cases": results,
            "model_loader_calls": 0, "gold_loader_calls": 0, "evaluator_calls": 0}


def synthetic_positive(root: Path, config: dict, candidate: dict) -> dict:
    with tempfile.TemporaryDirectory(prefix="ea1_r14_synthetic_") as directory:
        worktree = Path(directory) / "repo"
        subprocess.run(["git", "-C", str(root), "worktree", "add", "--detach", str(worktree), R13_COMMIT], check=True, capture_output=True)
        try:
            subprocess.run(["git", "config", "user.email", "r14@example.com"], cwd=worktree, check=True)
            subprocess.run(["git", "config", "user.name", "R14 Synthetic"], cwd=worktree, check=True)
            subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=worktree, check=True)
            candidate_manifest = read_json(root / config["candidate"]["manifest"])
            exact_byte_paths = (
                set(execution.READINESS_HASH_PATHS)
                | set(candidate_manifest["artifact_sha256"])
                | {config["candidate"]["manifest"]}
                | R14_OVERLAY_PATHS
            )
            for relative in exact_byte_paths:
                target = worktree / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / relative, target)
            subprocess.run(["git", "add", "--all"], cwd=worktree, check=True)
            commit_env = dict(os.environ, GIT_AUTHOR_DATE="2026-08-13T08:00:00+07:00", GIT_COMMITTER_DATE="2026-08-13T08:00:00+07:00")
            subprocess.run(["git", "commit", "-m", "synthetic R14 readiness"], cwd=worktree, check=True, capture_output=True, env=commit_env)
            readiness = git(worktree, "rev-parse", "HEAD")
            authorization = final_authorization(candidate, readiness)
            auth_path = worktree / config["authorization"]["committed_record"]
            write_json(auth_path, authorization)
            for relative in ALLOWED_A14_PATHS - {config["authorization"]["committed_record"]}:
                path = worktree / relative
                path.write_bytes(path.read_bytes() + b"\nSynthetic A14 authorization lifecycle transition.\n")
            subprocess.run(["git", "add", "--", *sorted(ALLOWED_A14_PATHS)], cwd=worktree, check=True)
            subprocess.run(["git", "commit", "-m", "synthetic A14 authorization"], cwd=worktree, check=True, capture_output=True, env=commit_env)
            authorization_commit = git(worktree, "rev-parse", "HEAD")
            changed = sorted(git(worktree, "diff", "--name-only", f"{readiness}..{authorization_commit}").splitlines())
            for relative in ("artifacts/cache/w1-003", "artifacts/cache/w2-003"):
                shutil.copytree(root / relative, worktree / relative, dirs_exist_ok=True)
            asset_manifest = read_json(
                root / config["readiness_outputs"]["runtime_asset_manifest"]
            )
            for relative in asset_manifest["asset_file_sha256"]:
                target = worktree / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / relative, target)
            environment = dict(os.environ)
            environment.update({"PYTHONPATH": str(worktree / "src"), "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "HF_HUB_OFFLINE": "1"})
            code = """import json,sys; from pathlib import Path; from payresolve_ai.evaluation import critical_v2_execution as e; r=Path(sys.argv[1]); print(json.dumps(e.verify_execution_authorization(r,r/'configs/evaluation/critical_eval_v2_execution.json'),sort_keys=True))"""
            verified = json.loads(subprocess.check_output([os.sys.executable, "-c", code, str(worktree)], cwd=worktree, env=environment, text=True))
            return {"status": "PASS", "synthetic_readiness_commit": readiness,
                    "synthetic_authorization_commit": authorization_commit,
                    "synthetic_parent": git(worktree, "rev-parse", "HEAD^"),
                    "changed_paths": changed, "changed_path_count": len(changed),
                    "production_verifier": verified, "model_loader_calls": 0,
                    "gold_loader_calls": 0, "evaluator_calls": 0}
        finally:
            subprocess.run(["git", "-C", str(root), "worktree", "remove", "--force", str(worktree)], check=True, capture_output=True)


def offline_probe(root: Path, config: dict) -> dict:
    attempts: list[dict] = []
    def reject_socket(sock, address):
        attempts.append({"transport": "socket.connect", "target": repr(address)})
        raise RuntimeError("network forbidden by R14 probe")
    retrieval = read_json(root / config["runtime_dependencies"]["retrieval_config"]["path"])
    started = time.perf_counter()
    with patch.object(socket.socket, "connect", reject_socket):
        encoder = benchmark._encoder(root, retrieval)
        vector = np.asarray(encoder.encode([DIAGNOSTIC_TEXT]), dtype=np.float32)
    elapsed = time.perf_counter() - started
    digest = hashlib.sha256(vector.tobytes(order="C")).hexdigest()
    norm = float(np.linalg.norm(vector[0]))
    if attempts or vector.shape != (1, 384) or str(vector.dtype) != "float32" or not math.isclose(norm, 1.0, abs_tol=1e-6) or digest != EXPECTED_VECTOR_SHA or encoder.provenance.get("local_files_only") is not True:
        raise RuntimeError("R14 offline encoder probe failed")
    return {"status": "PASS", "diagnostic_text": DIAGNOSTIC_TEXT, "elapsed_seconds": elapsed,
            "network_attempts": attempts, "local_files_only": True, "shape": [1, 384],
            "dtype": "float32", "l2_norm": norm, "embedding_sha256": digest,
            "candidate_inference": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    config_path = root / "configs/evaluation/critical_eval_v2_execution.json"
    config = execution.load_execution_config(config_path)
    candidate_path = root / config["authorization"]["candidate"]
    candidate = read_json(candidate_path)
    candidate["execution_contract_sha256"] = execution.sha256_file(config_path)
    candidate["execution_artifact_sha256"] = execution._readiness_artifact_hashes(root)
    write_json(candidate_path, candidate)
    results = root / "reports/week_03/results"
    if any((results / name).exists() for name in ("critical_eval_v2_runtime_execution_environment.json", "critical_eval_v2_execution_state.json")):
        raise RuntimeError("active control plane must remain absent")
    field = field_controls(root, config_path, config, candidate)
    topology = topology_controls()
    positive = synthetic_positive(root, config, candidate)
    packages = execution.canonical_package_inventory()
    identity = execution.stable_environment_identity(config, packages)
    identity_sha = execution.stable_sha256(identity)
    if packages["canonical_distribution_count"] != 298 or packages["canonical_package_fingerprint_sha256"] != EXPECTED_PACKAGE_SHA or identity_sha != EXPECTED_ENVIRONMENT_SHA:
        raise RuntimeError("R14 live environment identity drift")
    closure = execution.runtime_source_closure_payload(root, config)
    hashes = execution._readiness_artifact_hashes(root)
    if candidate["execution_artifact_sha256"] != hashes:
        raise RuntimeError("R14 candidate readiness hash map drift")
    evidence = {
        "critical_eval_v2_ea1_revision14_verifier_gap_lineage.json": {
            "status": "REMEDIATED", "readiness_revision": 14, "r13_commit": R13_COMMIT,
            "reason": "PRODUCTION_AUTHORIZATION_VERIFIER_HARDENING",
            "gaps": ["FINAL_AUTHORIZATION_LIFECYCLE_FIELDS_NOT_COMPLETE", "AUTHORIZATION_COMMIT_SUBSET_ACCEPTED"],
            "a13_created": False, "future_authorization": "A14"},
        "critical_eval_v2_ea1_revision14_authorization_field_enforcement.json": field,
        "critical_eval_v2_ea1_revision14_exact_five_topology_enforcement.json": topology,
        "critical_eval_v2_ea1_revision14_synthetic_authorization.json": positive,
        "critical_eval_v2_ea1_revision14_runtime_source_closure.json": closure,
        "critical_eval_v2_ea1_revision14_hash_rebinding.json": {
            "status": "PASS", "readiness_revision": 14, "readiness_hash_path_count": len(execution.READINESS_HASH_PATHS),
            "candidate_hash_count": len(candidate["execution_artifact_sha256"]), "exact_map_equality": True,
            "execution_contract_sha256": execution.sha256_file(config_path), "hashes": hashes},
        "critical_eval_v2_ea1_revision14_environment_recheck.json": {
            "status": "PASS", "canonical_distribution_count": packages["canonical_distribution_count"],
            "canonical_package_fingerprint_sha256": packages["canonical_package_fingerprint_sha256"],
            "environment_identity_sha256": identity_sha, "required_environment": config["runtime_environment"]["required_environment"]},
        "critical_eval_v2_ea1_revision14_active_control_plane_absence.json": {
            "status": "PASS", "active_runtime_environment_absent": True, "active_execution_state_absent": True,
            "primary_artifacts_present": False, "a14_created": False},
        "critical_eval_v2_ea1_revision14_offline_encoder_probe.json": offline_probe(root, config),
    }
    for name, payload in evidence.items():
        write_json(results / name, payload)
    print(json.dumps({"status": "PASS", "evidence_count": len(evidence), "hash_count": len(hashes),
                      "runtime_source_count": closure["source_count"], "synthetic_authorization_commit": positive["synthetic_authorization_commit"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
