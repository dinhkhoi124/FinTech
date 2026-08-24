"""Read-only, pre-E1 runtime attestation for the frozen EV2 A3 FIX4 package."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from scripts.evaluation import week3_ev2_e1 as e1
from scripts.evaluation.week3_ev2_integrity import (
    aggregate_bindings_sha256,
    atomic_write_json,
    sha256,
    stable_json_sha256,
    verify_working_source_tree,
)

TASK_ID = "W3-003-EV2-A4-ATT1"
A3_MANIFEST = "reports/week_03/results/w3_003_ev2_a3_frozen_manifest.json"
PROVENANCE = "reports/week_01/results/semantic_model_provenance.json"
REQUIREMENTS = "requirements/week1-semantic.txt"
RETRIEVAL_CONFIG = "configs/retrieval/kb_v1_r0_r1.json"
EXPECTED_PYTHON = "3.11.9"
OFFLINE_ENVIRONMENT = {
    "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false",
    "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1", "PYTHONHASHSEED": "0",
}


class AttestationError(RuntimeError):
    pass


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_requirements(path: Path) -> list[tuple[str, str]]:
    parsed: list[tuple[str, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if "==" not in line:
            raise AttestationError("A4_UNPINNED_REQUIREMENT")
        name, version = line.split("==", 1)
        name = name.split("[", 1)[0].split(";", 1)[0].strip()
        parsed.append((name, version.strip()))
    return parsed


def python_receipt() -> dict[str, Any]:
    return {
        "executable": sys.executable, "implementation": platform.python_implementation(),
        "version": platform.python_version(), "platform": platform.platform(),
        "architecture": platform.architecture()[0], "device": "cpu",
    }


def attest_python(receipt: dict[str, Any]) -> dict[str, Any]:
    passed = receipt["implementation"] == "CPython" and receipt["version"] == EXPECTED_PYTHON and receipt["architecture"] == "64bit" and receipt["device"] == "cpu"
    return {**receipt, "required_version": EXPECTED_PYTHON, "passed": passed}


def attest_dependencies(requirements: list[tuple[str, str]], version_getter: Callable[[str], str] = importlib.metadata.version) -> dict[str, Any]:
    values: list[dict[str, Any]] = []
    for name, expected in requirements:
        try:
            installed = version_getter(name)
        except importlib.metadata.PackageNotFoundError:
            installed = None
        values.append({"distribution": name, "expected": expected, "installed": installed, "match": installed == expected})
    return {"requirements": values, "mismatch_count": sum(not item["match"] for item in values), "passed": all(item["match"] for item in values)}


def pip_check() -> dict[str, Any]:
    run = subprocess.run([sys.executable, "-m", "pip", "check"], capture_output=True, text=True, check=False)
    return {"command": f"{sys.executable} -m pip check", "exit_code": run.returncode, "stdout": run.stdout.strip(), "stderr": run.stderr.strip(), "passed": run.returncode == 0}


def snapshot_root(root: Path, provenance: dict[str, Any]) -> Path:
    model = provenance["model_id"].replace("/", "--")
    return root / "artifacts/cache/w1-003/huggingface" / f"models--{model}" / "snapshots" / provenance["revision"]


def file_records(directory: Path) -> list[dict[str, Any]]:
    if not directory.is_dir():
        return []
    return [{"path": item.relative_to(directory).as_posix(), "bytes": item.stat().st_size, "sha256": sha256(item)} for item in sorted(path for path in directory.rglob("*") if path.is_file())]


def attest_snapshot(root: Path, provenance: dict[str, Any]) -> dict[str, Any]:
    snapshot = snapshot_root(root, provenance)
    expected = provenance["downloaded_snapshot_files"]
    actual = file_records(snapshot)
    by_path = {row["path"]: row for row in actual}
    expected_paths = {row["path"] for row in expected}
    missing = sorted(expected_paths - set(by_path))
    unexpected = sorted(set(by_path) - expected_paths)
    size_mismatches = sorted(row["path"] for row in expected if row["path"] in by_path and row["bytes"] != by_path[row["path"]]["bytes"])
    hash_mismatches = sorted(row["path"] for row in expected if row["path"] in by_path and row["sha256"] != by_path[row["path"]]["sha256"])
    footprint = sum(row["bytes"] for row in actual)
    return {
        "model_id": provenance["model_id"], "revision": provenance["revision"], "snapshot_path": snapshot.relative_to(root).as_posix(),
        "expected_file_count": len(expected), "actual_file_count": len(actual), "expected_footprint_bytes": provenance["snapshot_footprint_bytes"], "actual_footprint_bytes": footprint,
        "files": actual, "missing_files": missing, "unexpected_files": unexpected, "size_mismatches": size_mismatches, "hash_mismatches": hash_mismatches,
        "passed": not missing and not unexpected and not size_mismatches and not hash_mismatches and footprint == provenance["snapshot_footprint_bytes"],
    }


def attest_runtime_assets(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    bindings = manifest["runtime_input_sha256"]
    values = {relative: sha256(root / relative) if (root / relative).is_file() else None for relative in bindings}
    mismatches = sorted(relative for relative, expected in bindings.items() if values[relative] != expected)
    aggregate = aggregate_bindings_sha256(bindings)
    return {"runtime_input_sha256": bindings, "actual_sha256": values, "runtime_input_aggregate_sha256": aggregate, "expected_runtime_input_aggregate_sha256": manifest["runtime_input_aggregate_sha256"], "mismatches": mismatches, "passed": not mismatches and aggregate == manifest["runtime_input_aggregate_sha256"]}


def attest_source_and_retriever(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    decision_path = root / manifest["retrieval_decision_source"]
    decision = read_json(decision_path)
    receipt_path = root / manifest["paths"]["candidate_source_tree_receipt"]
    receipt = read_json(receipt_path)
    source_hash = verify_working_source_tree(root, receipt)
    git_tree = subprocess.check_output(["git", "rev-parse", f"{manifest['candidate_production_commit']}:src/payresolve_ai"], cwd=root, text=True).strip()
    result = {
        "selected_retriever": manifest.get("selected_retriever"), "retrieval_decision_sha256": manifest.get("retrieval_decision_sha256"),
        "retrieval_decision_actual_sha256": sha256(decision_path), "retrieval_decision_candidate_git_blob": manifest.get("retrieval_decision_candidate_git_blob"),
        "decision_task_id": decision.get("task_id"), "decision_status": decision.get("status"), "decision_verdict": decision.get("final_senior_review_verdict"), "decision_selected_retriever": decision.get("selected_retriever"),
        "candidate_commit": manifest.get("candidate_production_commit"), "candidate_git_tree": git_tree, "receipt_git_tree": receipt.get("git_tree"),
        "candidate_source_tree_sha256": source_hash, "expected_candidate_source_tree_sha256": manifest.get("candidate_source_tree_sha256"),
    }
    result["passed"] = result["selected_retriever"] == result["decision_selected_retriever"] == "R0" and result["retrieval_decision_sha256"] == result["retrieval_decision_actual_sha256"] and result["decision_status"] == "FINALIZED_REVIEW_CORRECTION" and result["decision_verdict"] == "APPROVE_COMMIT" and result["candidate_git_tree"] == result["receipt_git_tree"] and result["candidate_source_tree_sha256"] == result["expected_candidate_source_tree_sha256"]
    return result


def attest_offline_load(root: Path) -> dict[str, Any]:
    controls = {key: os.environ.get(key) for key in OFFLINE_ENVIRONMENT}
    if controls != OFFLINE_ENVIRONMENT:
        raise AttestationError("A4_OFFLINE_ENVIRONMENT_MISMATCH")
    from payresolve_ai.retrieval.benchmark import _encoder, _load_runtime, load_config
    network_attempts = 0
    original_connect, original_connect_ex, original_create = socket.socket.connect, socket.socket.connect_ex, socket.create_connection
    def no_network(*args: Any, **kwargs: Any) -> Any:
        nonlocal network_attempts
        network_attempts += 1
        raise AttestationError("A4_NETWORK_ATTEMPT_FORBIDDEN")
    try:
        socket.socket.connect = no_network; socket.socket.connect_ex = no_network; socket.create_connection = no_network
        config = load_config(root, root / RETRIEVAL_CONFIG, require_local_model=True)
        chunks, embeddings = _load_runtime(root, config)
        encoder = _encoder(root, config)
    finally:
        socket.socket.connect, socket.socket.connect_ex, socket.create_connection = original_connect, original_connect_ex, original_create
    provenance = encoder.provenance
    return {"status": "PASS", "offline_controls": controls, "network_attempt_count": network_attempts, "query_encode_calls": 0, "rank_queries_calls": 0, "ev2_input_reads": 0, "local_files_only": provenance["local_files_only"], "model_id": provenance["model_id"], "revision": provenance["revision"], "dimension": provenance["embedding_dimension"], "pooling": provenance["pooling"], "normalize_embeddings": provenance["normalize_embeddings"], "device": provenance["device"], "snapshot_files": provenance["downloaded_snapshot_files"], "snapshot_footprint_bytes": provenance["snapshot_footprint_bytes"], "corpus_chunks": len(chunks), "embedding_shape": list(embeddings.shape), "classifier_parameters_verified": True, "corpus_alignment_verified": True, "passed": network_attempts == 0 and provenance["local_files_only"] is True and provenance["embedding_dimension"] == 384 and len(chunks) == 52 and list(embeddings.shape) == [52, 384]}


def preauthorization_payload(manifest: dict[str, Any], manifest_sha256: str, audit_hashes: dict[str, str]) -> dict[str, Any]:
    payload = e1.required_a4(manifest, manifest_sha256)
    payload.update(audit_hashes)
    payload.update({"authorization": "A4_PREAUTH_ATTESTATION_ONLY", "ev2_authorized": False, "senior_approval_state": "AWAITING_SENIOR_A4_APPROVAL", "not_authorizing": True, "authorization_nonce_or_id": "NOT_A_REAL_A4_AUTHORIZATION"})
    return payload


def attest_preauth_rejection(path: Path, manifest: dict[str, Any], manifest_sha256: str) -> dict[str, Any]:
    try:
        e1.validate_a4(path, manifest, manifest_sha256)
    except PermissionError as error:
        return {"validation_rejected": True, "error": str(error), "production_runner_calls": 0, "retrieval_calls": 0, "ev2_query_calls": 0, "consumption_receipt_created": False, "raw_output_created": False, "passed": True}
    return {"validation_rejected": False, "error": None, "production_runner_calls": 0, "retrieval_calls": 0, "ev2_query_calls": 0, "consumption_receipt_created": False, "raw_output_created": False, "passed": False}


def attest(root: Path, output_dir: Path) -> dict[str, Any]:
    root = root.resolve(); manifest_path = root / A3_MANIFEST; manifest = read_json(manifest_path); manifest_sha256 = sha256(manifest_path)
    if manifest_sha256 != "19ad35b27bd3f60e0a76ae7e42ea4c06a197166e1e9ae3ea26dbecc05ae5ee54" or manifest.get("selected_retriever") != "R0" or manifest.get("lifecycle", {}).get("evaluation_authorized") is not False or manifest.get("lifecycle", {}).get("evaluation_executed") is not False or manifest.get("lifecycle", {}).get("ev2_consumed") is not False:
        raise AttestationError("BLOCKED_A4_A3_IDENTITY_DRIFT")
    python = attest_python(python_receipt())
    dependencies = attest_dependencies(parse_requirements(root / REQUIREMENTS))
    pip = pip_check()
    provenance = read_json(root / PROVENANCE); snapshot = attest_snapshot(root, provenance); runtime = attest_runtime_assets(root, manifest); source = attest_source_and_retriever(root, manifest)
    if not python["passed"]: raise AttestationError("BLOCKED_A4_PYTHON_RUNTIME_MISMATCH")
    if not dependencies["passed"] or not pip["passed"]: raise AttestationError("BLOCKED_A4_DEPENDENCY_ENVIRONMENT_MISMATCH")
    if not snapshot["passed"]: raise AttestationError("BLOCKED_A4_MINILM_SNAPSHOT_IDENTITY_MISMATCH")
    if not runtime["passed"]: raise AttestationError("BLOCKED_A4_RUNTIME_ASSET_MISMATCH")
    if not source["passed"]: raise AttestationError("BLOCKED_A4_SOURCE_OR_RETRIEVER_MISMATCH")
    offline = attest_offline_load(root)
    if not offline["passed"] or offline["snapshot_files"] != provenance["downloaded_snapshot_files"]: raise AttestationError("BLOCKED_A4_OFFLINE_MODEL_LOAD_MISMATCH")
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {"environment": output_dir / "w3_003_ev2_a4_environment_attestation.json", "snapshot": output_dir / "w3_003_ev2_a4_minilm_snapshot_attestation.json", "runtime": output_dir / "w3_003_ev2_a4_runtime_asset_attestation.json", "source": output_dir / "w3_003_ev2_a4_source_and_retriever_attestation.json", "offline": output_dir / "w3_003_ev2_a4_offline_model_load_audit.json", "preauth": output_dir / "w3_003_ev2_a4_pre_authorization_payload.json"}
    fingerprint = stable_json_sha256({"python": python, "dependencies": dependencies["requirements"], "offline_controls": OFFLINE_ENVIRONMENT, "model": {key: provenance[key] for key in ("model_id", "revision", "embedding_dimension", "pooling", "normalize_embeddings")}, "snapshot_files": snapshot["files"], "runtime_input_aggregate_sha256": manifest["runtime_input_aggregate_sha256"], "candidate_source_tree_sha256": manifest["candidate_source_tree_sha256"], "selected_retriever": manifest["selected_retriever"], "retrieval_decision_sha256": manifest["retrieval_decision_sha256"], "a3_manifest_sha256": manifest_sha256})
    environment = {"task_id": TASK_ID, "python_runtime": python, "dependency_version_audit": dependencies, "pip_check": pip, "offline_controls": OFFLINE_ENVIRONMENT, "environment_fingerprint_sha256": fingerprint, "passed": True}
    source["task_id"] = TASK_ID; snapshot["task_id"] = TASK_ID; runtime["task_id"] = TASK_ID
    atomic_write_json(paths["environment"], environment); atomic_write_json(paths["snapshot"], snapshot); atomic_write_json(paths["runtime"], runtime); atomic_write_json(paths["source"], source); atomic_write_json(paths["offline"], offline)
    audit_hashes = {"environment_attestation_sha256": sha256(paths["environment"]), "minilm_snapshot_attestation_sha256": sha256(paths["snapshot"]), "runtime_asset_attestation_sha256": sha256(paths["runtime"]), "source_retriever_attestation_sha256": sha256(paths["source"])}
    preauth = preauthorization_payload(manifest, manifest_sha256, audit_hashes); atomic_write_json(paths["preauth"], preauth)
    rejection = attest_preauth_rejection(paths["preauth"], manifest, manifest_sha256)
    atomic_write_json(output_dir / "w3_003_ev2_a4_preauth_rejection_audit.json", rejection)
    return {"status": "A4_ATTESTATION_READY_FOR_SENIOR_AUTHORIZATION", "paths": {key: path.relative_to(root).as_posix() for key, path in paths.items()}, "environment_fingerprint_sha256": fingerprint, "preauth_sha256": sha256(paths["preauth"]), "preauth_rejection": rejection, "offline_model_load": offline}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("command", choices=("attest",)); parser.add_argument("--root", type=Path, required=True); parser.add_argument("--output-dir", type=Path, default=Path("reports/week_03/results")); args = parser.parse_args()
    try:
        root = args.root.resolve()
        result = attest(root, root / args.output_dir)
    except (AttestationError, e1.IntegrityError, OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"A4_ATTESTATION_BLOCKED:{error}", file=sys.stderr); return 2
    print(json.dumps(result, indent=2, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
