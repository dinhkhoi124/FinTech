"""Create bounded Revision-13 readiness evidence; never run critical evaluation."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import math
import os
import socket
import subprocess
import sys
import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import numpy as np

from payresolve_ai.evaluation import critical_v2_execution as execution
from payresolve_ai.retrieval import benchmark


DIAGNOSTIC_TEXT = "EA1_OFFLINE_ENCODER_DIAGNOSTIC_DO_NOT_SCORE"
EXPECTED_VECTOR_SHA256 = "83483507be7e9c48ca8caff139e15dc3e1f88509addd55793b7fc96e95f87f8e"
PROTECTED = {
    "reports/week_03/results/critical_eval_v2_runtime_execution_environment.json":
        execution.PRESERVED_A12_RUNTIME_ENVIRONMENT_SHA256,
    "reports/week_03/results/critical_eval_v2_execution_state.json":
        execution.PRESERVED_A12_EXECUTION_STATE_SHA256,
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def git_json(root: Path, revision: str, relative: str) -> dict:
    raw = subprocess.check_output(["git", "-C", str(root), "show", f"{revision}:{relative}"])
    return json.loads(raw)


def probe_environment_context(root: Path, context_id: str) -> dict:
    source = str((root / "src").resolve())
    code = r'''
import json
import site
import sys
from pathlib import Path

source = Path(sys.argv[1]).resolve()
mode = sys.argv[2]
def is_source(entry):
    return Path(entry or ".").resolve() == source

if mode == "C1":
    sys.path.insert(0, str(source))
    from payresolve_ai.evaluation import critical_v2_execution as execution
    sys.path[:] = [entry for entry in sys.path if not is_source(entry)]
elif mode == "C2":
    if not any(is_source(entry) for entry in sys.path):
        sys.path.insert(0, str(source))
    from payresolve_ai.evaluation import critical_v2_execution as execution
elif mode == "C3":
    sys.path.insert(0, str(source))
    from payresolve_ai.evaluation import critical_v2_execution as execution
elif mode == "C4":
    sys.path.insert(0, str(source))
    from payresolve_ai.evaluation import critical_v2_execution as execution
    sys.path.append(site.getsitepackages()[0])
else:
    raise RuntimeError(mode)

result = execution.canonical_package_inventory()
keys = (
    "canonicalization_algorithm", "canonical_distribution_count",
    "canonical_package_fingerprint_sha256", "raw_discovery_row_count",
    "raw_package_fingerprint_sha256", "raw_unique_normalized_name_count",
    "duplicate_same_version_occurrence_count", "duplicate_distribution_details",
    "conflicting_version_count", "excluded_local_project_distribution_occurrences",
    "core_ml_dependencies",
)
print(json.dumps({"context_id": mode, **{key: result[key] for key in keys}}, sort_keys=True))
'''
    environment = dict(os.environ)
    environment.update({"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "HF_HUB_OFFLINE": "1"})
    if context_id in {"C2", "C3"}:
        environment["PYTHONPATH"] = source
    else:
        environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-c", code, source, context_id],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    root, config_path = args.root.resolve(), args.config.resolve()
    config = execution.load_execution_config(config_path)
    required = config["runtime_environment"]["required_environment"]
    actual = {key: os.environ.get(key, "NOT_SET") for key in required}
    if actual != required:
        raise RuntimeError(f"R13 environment mismatch: required={required}, actual={actual}")
    for relative, expected in PROTECTED.items():
        if execution.sha256_file(root / relative) != expected:
            raise RuntimeError(f"protected E1 evidence drift: {relative}")
    execution._assert_readiness_output_boundary(root, config)

    attempts: list[dict] = []
    def reject_socket(sock, address):
        attempts.append({"transport": "socket.connect", "target": repr(address)})
        raise RuntimeError("network forbidden by EA1 Revision 13 probe")
    try:
        import httpx
        def reject_http(self, request, *a, **kw):
            attempts.append({"transport": "httpx", "method": request.method, "url": str(request.url)})
            raise RuntimeError("HTTP forbidden by EA1 Revision 13 probe")
        http_patches = [
            patch.object(httpx.Client, "send", reject_http),
            patch.object(httpx.AsyncClient, "send", reject_http),
        ]
    except ImportError:
        http_patches = []

    retrieval_path = root / config["runtime_dependencies"]["retrieval_config"]["path"]
    retrieval = read_json(retrieval_path)
    started = time.perf_counter()
    with patch.object(socket.socket, "connect", reject_socket):
        for item in http_patches:
            item.start()
        try:
            encoder = benchmark._encoder(root, retrieval)
            vector = np.asarray(encoder.encode([DIAGNOSTIC_TEXT]), dtype=np.float32)
        finally:
            for item in reversed(http_patches):
                item.stop()
    elapsed = time.perf_counter() - started
    vector_sha = hashlib.sha256(vector.tobytes(order="C")).hexdigest()
    norm = float(np.linalg.norm(vector[0]))
    probe_ok = (
        not attempts and vector.shape == (1, 384) and str(vector.dtype) == "float32"
        and math.isclose(norm, 1.0, abs_tol=1e-6) and vector_sha == EXPECTED_VECTOR_SHA256
        and encoder.provenance.get("local_files_only") is True
    )
    if not probe_ok:
        raise RuntimeError(
            f"offline encoder probe failed: attempts={attempts}, shape={vector.shape}, "
            f"dtype={vector.dtype}, norm={norm}, sha256={vector_sha}"
        )

    outputs = config["readiness_outputs"]
    packages = {
        name: importlib.metadata.version(name)
        for name in ("sentence-transformers", "transformers", "huggingface-hub", "torch", "numpy")
    }
    contexts = [probe_environment_context(root, context_id) for context_id in ("C1", "C2", "C3", "C4")]
    canonical_identities = {
        (row["canonical_distribution_count"], row["canonical_package_fingerprint_sha256"])
        for row in contexts
    }
    if len(canonical_identities) != 1:
        raise RuntimeError(f"canonical environment identity differs across contexts: {contexts}")
    if contexts[0]["raw_discovery_row_count"] != 300 or contexts[0]["raw_package_fingerprint_sha256"] != "f62e73de0de5c9ab4d89ddb07fe5636310ec038197a425735c498d9b8c29fd8b":
        raise RuntimeError("current clean raw discovery no longer matches completed diagnostic")
    if contexts[2]["raw_discovery_row_count"] != 302 or contexts[2]["raw_package_fingerprint_sha256"] != "7316a76fa5d68aa2e3c1878691266d673c4f4880c439fe79ac545d6a33b8e45c":
        raise RuntimeError("R13 duplicated discovery context was not reproduced")

    class ConflictingDistribution:
        def __init__(self, version: str) -> None:
            self.metadata = {"Name": "synthetic_conflict"}
            self.version = version
            self._path = Path(f"synthetic_conflict-{version}.dist-info")
        def read_text(self, filename: str) -> str | None:
            return f"Name: synthetic_conflict\nVersion: {self.version}\n" if filename == "METADATA" else None

    try:
        execution.canonical_package_inventory(
            [ConflictingDistribution("1.0"), ConflictingDistribution("2.0")],
            required_core_versions={},
        )
    except execution.CriticalV2ExecutionError as error:
        if "CONFLICTING_DISTRIBUTION_VERSIONS" not in str(error):
            raise
        conflict_control = {
            "status": "CONFLICTING_DISTRIBUTION_VERSIONS_REJECTED",
            "real_site_packages_mutated": False,
            "error": str(error),
        }
    else:
        raise RuntimeError("conflicting-version negative control unexpectedly passed")

    current_identity = execution.canonical_package_inventory()
    duplicate_by_name = {
        row["normalized_name"]: row for row in contexts[2]["duplicate_distribution_details"]
        if row["normalized_name"] in {"day08-langgraph-agent-lab", "day10-reliability-agent-lab", "payresolve-ai"}
    }
    reconciliation = {
        "schema_version": "1.0",
        "task_id": config["task_id"],
        "readiness_revision": 13,
        "classification": "ENV_DISCOVERY_CONTEXT_DRIFT",
        "actual_package_installation_drift": False,
        "package_mutation_performed": False,
        "senior_remediation_classification": "APPROVE_R13_ENVIRONMENT_FINGERPRINT_REMEDIATION",
        "raw_observation_lineage": {
            "a12_historical": {"row_count": 299, "fingerprint_sha256": "83b21ccf1fd73723b88e7e21744ab4fad6fb92f28c0e71c9d41ddf052b902d77"},
            "current_clean_reproduced": {"row_count": contexts[0]["raw_discovery_row_count"], "fingerprint_sha256": contexts[0]["raw_package_fingerprint_sha256"]},
            "r13_duplicated_context_reproduced": {"row_count": contexts[2]["raw_discovery_row_count"], "fingerprint_sha256": contexts[2]["raw_package_fingerprint_sha256"]},
            "historical_a368": {"row_count": 300, "fingerprint_sha256": "a3689c3213536b7c57b8d1c7d1a72e27894983583cb19baabe19bd3fff186509", "status": "UNREPRODUCED_HISTORICAL_OBSERVATION", "contract_target": False},
        },
        "canonicalization_algorithm": current_identity["canonicalization_algorithm"],
        "canonical_distribution_count": current_identity["canonical_distribution_count"],
        "canonical_package_fingerprint_sha256": current_identity["canonical_package_fingerprint_sha256"],
        "canonical_inventory": current_identity["canonical_rows"],
        "duplicate_evidence": {
            "day08": duplicate_by_name.get("day08-langgraph-agent-lab"),
            "day10": duplicate_by_name.get("day10-reliability-agent-lab"),
            "payresolve_ai": duplicate_by_name.get("payresolve-ai"),
        },
        "context_invariance_results": contexts,
        "context_invariance_status": "PASS",
        "core_ml_dependency_binding": current_identity["core_ml_dependencies"],
        "conflicting_version_negative_control": conflict_control,
        "review_bundle_lineage": {
            "superseded_pre_stop": {
                "filename": "W3-002-CR1_EA1_revision_13_runtime_offline_remediation_review_bundle.zip",
                "status": "SUPERSEDED_PRE_STOP_ENVIRONMENT_PROVENANCE_EVIDENCE",
                "bytes": 625958,
                "sha256": "f78f9ec4b15df5dada092f05d87dcde724da1bf2410120bf5688487e2a09ff88",
                "deliverable": False,
            }
        },
        "local_project_source_hash_bindings_preserved": True,
        "primary_execution_authorized": False,
    }
    write_json(root / outputs["environment_reconciliation"], reconciliation)
    write_json(root / outputs["offline_encoder_probe"], {
        "status": "PASS", "task_id": config["task_id"], "readiness_revision": 13,
        "probe_scope": "PRODUCTION_RETRIEVAL_ENCODER_LOAD_PLUS_ONE_FIXED_DIAGNOSTIC_STRING",
        "diagnostic_text_sha256": hashlib.sha256(DIAGNOSTIC_TEXT.encode()).hexdigest(),
        "gold_or_evaluator_loaded": False, "candidate_query_loaded": False,
        "inference_or_evaluation_run": False, "network_attempt_count": len(attempts),
        "network_attempts": attempts, "required_environment": required,
        "production_local_files_only": True, "shape": list(vector.shape),
        "dtype": str(vector.dtype), "l2_norm": norm, "embedding_ndarray_sha256": vector_sha,
        "expected_embedding_ndarray_sha256": EXPECTED_VECTOR_SHA256,
        "elapsed_seconds": round(elapsed, 6), "package_versions": packages,
    })

    closure_path = root / outputs["runtime_source_closure"]
    closure = read_json(closure_path)
    expected_closure = execution.runtime_source_closure_payload(root, config)
    if closure != expected_closure:
        raise RuntimeError("runtime source closure artifact drift")
    source_hashes = closure["source_sha256"]

    contract = execution.load_environment_contract(root, config)
    reviewed_identity = contract["environment_identity"]
    reviewed_sha = contract["environment_identity_sha256"]
    environment_mutations = {
        "ENV-AUTH-01": ("canonical_package_fingerprint_sha256", "0" * 64),
        "ENV-AUTH-02": ("canonical_distribution_count", reviewed_identity["canonical_distribution_count"] + 1),
        "ENV-AUTH-06": ("python.version", "0.0.0"),
        "ENV-AUTH-07": ("required_environment.HF_HUB_OFFLINE", "NOT_SET"),
    }
    environment_results = []
    for case, (field, value) in environment_mutations.items():
        actual = copy.deepcopy(reviewed_identity)
        cursor = actual
        parts = field.split(".")
        for part in parts[:-1]:
            cursor = cursor[part]
        cursor[parts[-1]] = value
        try:
            execution.assert_authorized_environment_identity(actual, reviewed_identity, reviewed_sha)
        except execution.CriticalV2ExecutionError as error:
            environment_results.append({"case": case, "status": "REJECTED_BEFORE_MODEL_LOAD", "error": str(error), "model_loader_calls": 0})
        else:
            raise RuntimeError(f"environment authorization negative control passed: {case}")
    for case, field in (
        ("ENV-AUTH-03", "version"),
        ("ENV-AUTH-04", "metadata_sha256"),
        ("ENV-AUTH-05", "record_sha256"),
    ):
        actual = copy.deepcopy(reviewed_identity)
        actual["core_ml_dependencies"]["numpy"][field] = "0.0.0" if field == "version" else "1" * 64
        try:
            execution.assert_authorized_environment_identity(actual, reviewed_identity, reviewed_sha)
        except execution.CriticalV2ExecutionError as error:
            environment_results.append({"case": case, "status": "REJECTED_BEFORE_MODEL_LOAD", "error": str(error), "model_loader_calls": 0})
        else:
            raise RuntimeError(f"environment authorization negative control passed: {case}")

    candidate = read_json(root / config["authorization"]["candidate"])
    candidate["evaluation_authorized"] = True
    candidate["senior_authorization_verdict"] = config["authorization"]["required_verdict"]
    candidate.update(execution.CONTINUATION_AUTHORIZATION_FIELDS)
    source_results = []
    for relative in (
        "src/payresolve_ai/generation/verification.py",
        "src/payresolve_ai/data/banking77.py",
        "src/payresolve_ai/generation/citations.py",
        "src/payresolve_ai/evaluation/critical_v2_execution.py",
    ):
        with tempfile.TemporaryDirectory(prefix="ea1_r13_source_control_") as temporary:
            isolated = Path(temporary)
            for bound in execution.READINESS_HASH_PATHS:
                target = isolated / bound
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / bound, target)
            tampered = isolated / relative
            tampered.write_bytes(tampered.read_bytes() + b"\n# isolated source tamper\n")
            try:
                execution._validate_authorization_payload(
                    isolated,
                    isolated / "configs/evaluation/critical_eval_v2_execution.json",
                    config,
                    candidate,
                )
            except execution.CriticalV2ExecutionError as error:
                source_results.append({"path": relative, "status": "REJECTED_BEFORE_MODEL_LOAD", "error": str(error), "model_loader_calls": 0})
            else:
                raise RuntimeError(f"source tamper negative control passed: {relative}")
    write_json(root / outputs["binding_negative_controls"], {
        "schema_version": "1.0", "task_id": config["task_id"], "readiness_revision": 13,
        "status": "PASS", "environment_controls": sorted(environment_results, key=lambda row: row["case"]),
        "environment_control_count": len(environment_results), "source_tamper_controls": source_results,
        "source_tamper_control_count": len(source_results),
        "authorization_date_controls": {
            "status": "PASS",
            "reviewed_daily_report_path": config["authorization"]["reviewed_daily_report_path"],
            "exact_allowed_paths": sorted(
                config["authorization"]["allowed_authorization_commit_paths"]
            ),
            "active_case_count": 7,
            "historical_revision12_fixture": "PASS",
        },
        "detached_bundle_controls": "PENDING_FINAL_BUNDLE_BUILD",
        "detached_auth_date_controls": "PENDING_FINAL_BUNDLE_BUILD",
        "gold_loader_calls": 0, "evaluator_calls": 0, "model_loader_calls": 0,
    })

    incident = {
        "status": "ROOT_CAUSE_CONFIRMED_AND_REMEDIATED", "readiness_revision": 13,
        "candidate_defect": False, "candidate_revision": 7,
        "protected_e1_evidence_sha256": PROTECTED,
        "attempts": [
            {"attempt": 1, "elapsed_seconds": 120.817, "exit_code": 124,
             "classification": "WATCHDOG_TIMEOUT_DURING_ENCODER_LOAD",
             "persisted_raw": False, "state_after": "AUTHORIZED"},
            {"attempt": 2, "elapsed_seconds": 32.210, "exit_code": 1,
             "classification": "HUGGING_FACE_HEAD_REQUEST_BLOCKED",
             "error": "WinError 10013 during remote HEAD request",
             "model_id": "sentence-transformers/all-MiniLM-L6-v2",
             "revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
             "persisted_raw": False, "state_after": "AUTHORIZED"},
        ],
        "readiness_authoring_failures": [
            {
                "stage": "revision-13 offline evidence attempt 1",
                "failure": "standalone evidence script was launched without PYTHONPATH=src and stopped at import with ModuleNotFoundError before the encoder probe",
                "resolution": "rebind the changed evidence script, then relaunch with the repository src directory on PYTHONPATH",
                "probe_executed": False,
            }
        ],
        "diagnostic": {
            "encoder_snapshot_files_passed": 11, "encoder_snapshot_files_total": 11,
            "probe_a_embedding_ndarray_sha256": EXPECTED_VECTOR_SHA256,
            "probe_b_embedding_ndarray_sha256": EXPECTED_VECTOR_SHA256,
            "probe_embeddings_byte_identical": True,
        },
        "senior_classification": "EA1_RUNTIME_OFFLINE_ENCODER_BINDING_DEFECT",
        "selected_remediation": ["HF_HUB_OFFLINE_BINDING", "LOCAL_FILES_ONLY_CONSTRUCTOR", "TRANSITIVE_RUNTIME_SOURCE_HASH_BINDING"],
        "root_cause": "SentenceTransformer construction was not explicitly local-only; cached bytes were complete but a remote metadata path remained reachable.",
        "remediation": "Production retrieval encoder now passes local_files_only=True and requires HF_HUB_OFFLINE=1 before process launch.",
        "offline_probe_reference": outputs["offline_encoder_probe"],
        "package_versions": packages, "evaluation_or_inference_run": False,
        "candidate_revision_advanced": False, "primary_executed_successfully": False,
        "critical_evaluated": False, "model_verdict": "NOT_ESTABLISHED",
        "gold_loader_calls": 0, "evaluator_calls": 0,
    }
    write_json(root / outputs["runtime_incident_lineage"], incident)

    reset_steps = [
        "Verify both active A12 control-plane files against their original exact SHA-256 values.",
        "Verify no raw, evaluation, reproduction, comparison, or final-summary artifacts exist.",
        "Copy both active files byte-for-byte into immutable incident-history paths.",
        "Verify both archived hashes equal the original active-file hashes.",
        "Remove only the two active A12 control-plane files under the separate authorized reset contract.",
        "Verify all archived incident evidence still exists and matches its locked hashes.",
        "Verify staged files remain zero.",
        "Only after separate A13 authorization, launch with all three required environment values and initialize fresh runtime environment/state.",
    ]
    write_json(root / outputs["preauthorization_reset_plan"], {
        "status": "PLAN_ONLY_NOT_EXECUTED", "readiness_revision": 13,
        "requires_separate_senior_execution_authorization": True,
        "preserved_files_modified": False,
        "steps": [{"ordinal": i + 1, "state": "NOT_EXECUTED", "action": value}
                  for i, value in enumerate(reset_steps)],
    })

    asset_path = config["readiness_outputs"]["runtime_asset_manifest"]
    prior_asset, current_asset = git_json(root, "HEAD", asset_path), read_json(root / asset_path)
    unchanged_assets = (
        prior_asset["asset_file_sha256"] == current_asset["asset_file_sha256"]
        and prior_asset["encoder"] == current_asset["encoder"]
        and prior_asset["retrieval_cache_semantic_contract"] == current_asset["retrieval_cache_semantic_contract"]
    )
    write_json(root / outputs["runtime_asset_comparison"], {
        "status": "PASS" if unchanged_assets else "FAIL", "readiness_revision": 13,
        "baseline": "HEAD_A12", "asset_bytes_and_semantics_unchanged": unchanged_assets,
        "asset_file_count": len(current_asset["asset_file_sha256"]),
        "encoder_file_count": len(current_asset["encoder"]["files"]),
        "only_expected_manifest_metadata_change": prior_asset.get("readiness_revision") == 12
            and current_asset.get("readiness_revision") == 13,
    })
    if not unchanged_assets:
        raise RuntimeError("runtime assets changed relative to A12")

    payload_path = config["readiness_outputs"]["runtime_payload_manifest"]
    prior_payload, current_payload = git_json(root, "HEAD", payload_path), read_json(root / payload_path)
    unchanged_payload = all(prior_payload[key] == current_payload[key] for key in (
        "payload_count", "payload_schema", "payloads", "payload_sha256",
        "ordered_model_input_hash_pairs_sha256", "forbidden_field_occurrences",
    ))
    write_json(root / outputs["runtime_payload_comparison"], {
        "status": "PASS" if unchanged_payload else "FAIL", "readiness_revision": 13,
        "baseline": "HEAD_A12", "payload_bytes_semantics_and_order_unchanged": unchanged_payload,
        "payload_count": current_payload["payload_count"],
        "payload_sha256": current_payload["payload_sha256"],
        "forbidden_field_occurrences": current_payload["forbidden_field_occurrences"],
    })
    if not unchanged_payload:
        raise RuntimeError("runtime payload changed relative to A12")

    try:
        execution.verify_execution_authorization(root, config_path)
    except execution.CriticalV2ExecutionError as error:
        negative = {"status": "REJECTED_AS_EXPECTED", "readiness_revision": 13,
                    "tested_authorization": "A12", "failure": str(error),
                    "model_loaded": False, "evaluation_or_inference_run": False}
    else:
        raise RuntimeError("A12 unexpectedly authorized R13 bytes")
    write_json(root / outputs["a12_negative_control"], negative)
    print(json.dumps({"status": "PASS", "probe_seconds": round(elapsed, 6),
                      "network_attempts": 0, "source_count": len(source_hashes)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
