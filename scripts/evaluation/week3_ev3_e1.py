"""One-shot EV3 raw-only harness with fail-closed pre-consumption bindings."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable

from scripts.evaluation.week3_ev2_integrity import atomic_write_json, sha256, stable_json_sha256

AUTHORIZATION_SCHEMA = "W3-003-EV3-AUTHORIZATION-V2"
CONSUMPTION_SCHEMA = "W3-003-EV3-CONSUMPTION-V2"
RAW_SCHEMA = "W3-003-EV3-E1-RAW-MANIFEST-V2"
PACKAGE_SCHEMA = "W3-003-EV3-EH1-FIX2-EXECUTION-PACKAGE-V1"
PACKAGE_STATUS = "EV3_EH1_FIX2_FROZEN_PREEXECUTION_PACKAGE"
RUNTIME_ATTESTATION_SCHEMA = "W3-003-EV3-RUNTIME-ATTESTATION-V1"
FROZEN_RETRIEVER_ERROR = "FROZEN_RETRIEVER_DECISION_MISMATCH_BEFORE_CONSUMPTION"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(not isinstance(value, dict) for value in values):
        raise RuntimeError("JSONL_OBJECT_ROWS_REQUIRED")
    return values


def relative_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        raise RuntimeError("E1_PATH_OUTSIDE_EXPLICIT_ROOT") from None


def resolve_from_root(root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise RuntimeError("ABSOLUTE_PATH_FORBIDDEN")
    result = (root / path).resolve()
    relative_path(root, result)
    return result


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise RuntimeError(code)


def _verify_bound_file(root: Path, relative: str, wanted: str, label: str) -> None:
    path = resolve_from_root(root, relative)
    if not path.is_file() or sha256(path) != wanted:
        raise RuntimeError(f"EV3_EXECUTION_ARTIFACT_IDENTITY_DRIFT:{label}")


def _require_exact_fields(value: Any, fields: list[str], code: str) -> dict[str, Any]:
    _require(isinstance(value, dict) and set(value) == set(fields), code)
    return value


def _runtime_expected(package: dict[str, Any], package_sha256: str) -> dict[str, Any]:
    contract = package["runtime_attestation_contract"]
    return {
        "execution_package_manifest_sha256": package_sha256,
        "candidate_production_commit": package["candidate_production_commit"],
        "candidate_tree_sha256": package["candidate_tree_sha256"],
        "candidate_source_config_aggregate_sha256": stable_json_sha256(package["candidate_source_sha256"]),
        "inference_input_sha256": package["inference_input_sha256"],
        "evaluator_source_sha256": package["evaluator_source_sha256"],
        "e1_harness_sha256": package["e1_harness_sha256"],
        "retriever_decision_identity": package["retriever_decision_identity"],
        "runtime_identity": package["runtime_identity"],
        "model_identity": contract["model_identity"],
        "environment_identity": contract["environment_identity"],
    }


def _validate_environment_fingerprint_binding(root: Path, receipt: dict[str, Any], package: dict[str, Any], package_sha256: str) -> None:
    """Bind the claimed runtime fingerprint digest to its canonical package path."""
    relative = package.get("paths", {}).get("runtime_environment_fingerprint")
    _require(isinstance(relative, str) and relative, "RUNTIME_ATTESTATION_ENVIRONMENT_FINGERPRINT_PATH_REQUIRED")
    path = resolve_from_root(root, relative)
    _require(path.is_file(), "RUNTIME_ATTESTATION_ENVIRONMENT_FINGERPRINT_MISSING")
    _require(sha256(path) == receipt["environment_fingerprint_sha256"], "RUNTIME_ATTESTATION_ENVIRONMENT_FINGERPRINT_SHA_MISMATCH")
    fingerprint = load_json(path)
    expected = _runtime_expected(package, package_sha256)
    for key, wanted in expected.items():
        _require(fingerprint.get(key) == wanted, f"RUNTIME_FINGERPRINT_BINDING_MISMATCH:{key}")
    for key in (
        "network_attempts", "query_encoding_calls", "ranking_calls", "production_inference_calls",
        "gold_semantic_loads", "official_scorer_calls",
    ):
        _require(fingerprint.get(key) == 0, f"RUNTIME_FINGERPRINT_ACTIVITY:{key}")


def validate_runtime_attestation(root: Path, receipt: Path | None, package: dict[str, Any], package_sha256: str) -> tuple[dict[str, Any], str]:
    """Validate a runtime-load-only receipt before authorization or row 1."""
    if receipt is None or not receipt.is_file():
        raise PermissionError("EV3_RUNTIME_ATTESTATION_REQUIRED_BEFORE_AUTHORIZATION")
    schema_path = resolve_from_root(root, package["paths"]["runtime_attestation_schema"])
    _require(sha256(schema_path) == package["artifact_sha256"]["runtime_attestation_schema"], "RUNTIME_ATTESTATION_SCHEMA_IDENTITY_DRIFT")
    schema = load_json(schema_path)
    fields = schema.get("required_fields")
    _require(schema.get("schema_version") == RUNTIME_ATTESTATION_SCHEMA and isinstance(fields, list), "RUNTIME_ATTESTATION_SCHEMA_INVALID")
    value = _require_exact_fields(load_json(receipt), fields, "RUNTIME_ATTESTATION_FIELDS_INVALID")
    _require(value.get("schema_version") == RUNTIME_ATTESTATION_SCHEMA, "RUNTIME_ATTESTATION_VERSION_INVALID")
    _require(value.get("status") == "RUNTIME_LOAD_ONLY_ATTESTED", "RUNTIME_ATTESTATION_STATUS_INVALID")
    for key, wanted in _runtime_expected(package, package_sha256).items():
        _require(value.get(key) == wanted, f"RUNTIME_ATTESTATION_BINDING_MISMATCH:{key}")
    _require(value.get("runtime_load_only_proof") is True, "RUNTIME_ATTESTATION_NOT_LOAD_ONLY")
    _require(value.get("query_encoding_calls") == 0 and value.get("ranking_calls") == 0, "RUNTIME_ATTESTATION_INFERENCE_ACTIVITY")
    _require(value.get("network_attempts") == 0, "RUNTIME_ATTESTATION_NETWORK_ACTIVITY")
    _require(isinstance(value.get("environment_fingerprint_sha256"), str) and len(value["environment_fingerprint_sha256"]) == 64, "RUNTIME_ATTESTATION_ENVIRONMENT_FINGERPRINT_INVALID")
    _validate_environment_fingerprint_binding(root, value, package, package_sha256)
    _require(isinstance(value.get("timestamp_utc"), str) and value["timestamp_utc"], "RUNTIME_ATTESTATION_TIMESTAMP_INVALID")
    return value, sha256(receipt)


def required_authorization(package: dict[str, Any], package_sha256: str, runtime_receipt_path: str, runtime_receipt_sha256: str, environment_fingerprint_sha256: str) -> dict[str, Any]:
    return {
        "schema_version": AUTHORIZATION_SCHEMA, "authorization": "EV3_AUTHORIZE_E1", "ev3_authorized": True,
        "execution_package_manifest_sha256": package_sha256, "candidate_production_commit": package["candidate_production_commit"],
        "candidate_tree_sha256": package["candidate_tree_sha256"], "inference_input_sha256": package["inference_input_sha256"],
        "evaluator_source_sha256": package["evaluator_source_sha256"], "e1_harness_sha256": package["e1_harness_sha256"],
        "raw_manifest_schema_sha256": package["raw_manifest_schema_sha256"], "retriever_decision_identity": package["retriever_decision_identity"],
        "runtime_attestation_receipt_path": runtime_receipt_path, "runtime_attestation_receipt_sha256": runtime_receipt_sha256,
        "environment_fingerprint_sha256": environment_fingerprint_sha256, "senior_approval_state": "SENIOR_EV3_PREEXEC_APPROVED",
    }


def validate_authorization(root: Path, receipt: Path | None, package: dict[str, Any], package_sha256: str, runtime_path: Path, runtime: dict[str, Any], runtime_sha256: str) -> dict[str, Any]:
    if receipt is None or not receipt.is_file():
        raise PermissionError("EV3_AUTHORIZATION_REQUIRED_BEFORE_ROW_1")
    value = load_json(receipt)
    if not isinstance(value, dict):
        raise PermissionError("EV3_AUTHORIZATION_OBJECT_REQUIRED")
    expected = required_authorization(package, package_sha256, relative_path(root, runtime_path), runtime_sha256, runtime["environment_fingerprint_sha256"])
    for key, wanted in expected.items():
        if value.get(key) != wanted:
            raise PermissionError(f"EV3_AUTHORIZATION_BINDING_MISMATCH:{key}")
    if not isinstance(value.get("authorization_nonce_or_id"), str) or not value["authorization_nonce_or_id"]:
        raise PermissionError("EV3_AUTHORIZATION_ID_REQUIRED")
    return value


def atomic_consumption_receipt(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise RuntimeError("EV3_ALREADY_CONSUMED_NO_RESUME_OR_RERUN")
    atomic_write_json(path, payload)


def validate_frozen_retriever_decision(root: Path, package: dict[str, Any]) -> None:
    try:
        binding = package["retriever_decision_identity"]
        _require(binding["selected_retriever"] == "R0", FROZEN_RETRIEVER_ERROR)
        path = resolve_from_root(root, binding["path"])
        _require(sha256(path) == binding["sha256"], FROZEN_RETRIEVER_ERROR)
        decision = load_json(path)
        _require(decision.get("selected_retriever") == "R0", FROZEN_RETRIEVER_ERROR)
        _require(decision.get("final_senior_review_verdict") == "APPROVE_COMMIT", FROZEN_RETRIEVER_ERROR)
        _require(decision.get("status") == "FINALIZED_REVIEW_CORRECTION", FROZEN_RETRIEVER_ERROR)
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError, RuntimeError):
        raise RuntimeError(FROZEN_RETRIEVER_ERROR) from None


def validate_static_runtime_identities(root: Path, package: dict[str, Any]) -> None:
    runtime = package.get("runtime_identity")
    _require(isinstance(runtime, dict), "RUNTIME_IDENTITY_REQUIRED")
    for label, path_key, sha_key in (("kb", "kb_path", "kb_sha256"), ("generation_config", "generation_config_path", "generation_config_sha256"), ("retrieval_config", "retrieval_config_path", "retrieval_config_sha256")):
        _verify_bound_file(root, runtime[path_key], runtime[sha_key], label)
    validate_frozen_retriever_decision(root, package)


def r0_execution_boost(package: dict[str, Any]) -> None:
    if package.get("retriever_decision_identity", {}).get("selected_retriever") != "R0":
        raise RuntimeError(FROZEN_RETRIEVER_ERROR)


def rank_with_frozen_retriever(rank_queries: Callable[[Path, dict[str, Any], list[dict[str, Any]], float | None], tuple[list[dict[str, Any]], Any]], root: Path, retrieval: dict[str, Any], query: dict[str, Any], package: dict[str, Any]) -> tuple[list[dict[str, Any]], Any]:
    return rank_queries(root, retrieval, [query], r0_execution_boost(package))


def _load_package(root: Path, package_path: Path) -> dict[str, Any]:
    package = load_json(package_path)
    _require(isinstance(package, dict), "EV3_PACKAGE_OBJECT_REQUIRED")
    _require(package.get("schema_version") == PACKAGE_SCHEMA, "EV3_PACKAGE_SCHEMA_INVALID")
    _require(package.get("status") == PACKAGE_STATUS, "EV3_PACKAGE_NOT_FROZEN")
    expected = {"evaluation_package_frozen": True, "evaluator_frozen": True, "harness_frozen": True, "runtime_attested": False, "execution_authorized": False, "ev3_consumed": False, "ev3_executed": False}
    _require(all(package.get("lifecycle", {}).get(key) is wanted for key, wanted in expected.items()), "EV3_PACKAGE_LIFECYCLE_INVALID")
    return package


def validate_pre_inference(root: Path, package_path: Path, inputs_path: Path, runtime_attestation_path: Path | None, authorization_path: Path | None, consumption_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """All checks preceding row 1; this function has no Gold/scorer references."""
    package = _load_package(root, package_path)
    _require(package.get("mid_run_resume_supported") is False and package.get("checkpoint_resume_explicitly_disabled") is True, "RESUME_NOT_DISABLED")
    _require(sha256(inputs_path) == package["inference_input_sha256"], "INFERENCE_INPUT_SHA_DRIFT")
    artifacts, paths = package.get("artifact_sha256"), package.get("paths")
    _require(isinstance(artifacts, dict) and isinstance(paths, dict), "EV3_PACKAGE_BINDINGS_REQUIRED")
    for label in ("inference_inputs", "raw_manifest_schema", "runtime_attestation_schema", "evaluator_source", "e1_harness"):
        _verify_bound_file(root, paths[label], artifacts[label], label)
    for relative, wanted in package.get("candidate_source_sha256", {}).items():
        _verify_bound_file(root, relative, wanted, f"candidate:{relative}")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    _require(head == package["candidate_production_commit"], "CANDIDATE_COMMIT_IDENTITY_DRIFT")
    tree = subprocess.check_output(["git", "show", "-s", "--format=%T", package["candidate_production_commit"]], cwd=root, text=True).strip()
    _require(tree == package["candidate_tree_sha256"], "CANDIDATE_GIT_TREE_IDENTITY_DRIFT")
    validate_static_runtime_identities(root, package)
    inputs = read_jsonl(inputs_path)
    _require(len(inputs) == 60 and [row.get("ordinal") for row in inputs] == list(range(1, 61)), "INFERENCE_INPUT_ORDER_OR_COUNT")
    _require(all(set(row) == {"ordinal", "case_id", "query", "query_sha256"} and isinstance(row.get("query"), str) and hashlib.sha256(row["query"].encode("utf-8")).hexdigest() == row.get("query_sha256") for row in inputs), "INFERENCE_INPUT_SCHEMA_OR_QUERY_HASH")
    _require(stable_json_sha256([row["case_id"] for row in inputs]) == package["case_id_order_sha256"], "CASE_ORDER_BINDING_MISMATCH")
    _require(stable_json_sha256([row["query_sha256"] for row in inputs]) == package["query_sha256_order_sha256"], "QUERY_ORDER_BINDING_MISMATCH")
    _require(not consumption_path.exists(), "EV3_ALREADY_CONSUMED_NO_RESUME_OR_RERUN")
    package_sha = sha256(package_path)
    runtime, runtime_sha = validate_runtime_attestation(root, runtime_attestation_path, package, package_sha)
    authorization = validate_authorization(root, authorization_path, package, package_sha, runtime_attestation_path, runtime, runtime_sha)
    package["_verified_package_sha256"] = package_sha; package["_verified_runtime_attestation_sha256"] = runtime_sha
    return package, runtime, authorization, inputs


def execute_raw_only(root: Path, package_path: Path, inputs_path: Path, runtime_attestation_path: Path | None, authorization_path: Path | None, consumption_path: Path, raw_path: Path, raw_manifest_path: Path, runner: Callable[[dict[str, Any]], dict[str, Any]] | None = None) -> dict[str, Any]:
    """Future one-shot lifecycle; FIX1 itself never invokes it."""
    root = root.resolve()
    for path in (package_path, inputs_path, consumption_path, raw_path, raw_manifest_path): relative_path(root, path)
    if runtime_attestation_path is not None: relative_path(root, runtime_attestation_path)
    if authorization_path is not None: relative_path(root, authorization_path)
    package, runtime, authorization, inputs = validate_pre_inference(root, package_path, inputs_path, runtime_attestation_path, authorization_path, consumption_path)
    if raw_path.exists() or raw_manifest_path.exists(): raise RuntimeError("RAW_OUTPUT_CONFLICT_NO_PARTIAL_RERUN")
    first = inputs[0]
    consumption = {"schema_version": CONSUMPTION_SCHEMA, "ev3_consumed": True, "started_ordinal": 1, "case_id": first["case_id"], "query_sha256": first["query_sha256"], "execution_package_manifest_sha256": package["_verified_package_sha256"], "authorization_id": authorization["authorization_nonce_or_id"], "runtime_attestation_receipt_path": relative_path(root, runtime_attestation_path), "runtime_attestation_receipt_sha256": package["_verified_runtime_attestation_sha256"], "environment_fingerprint_sha256": runtime["environment_fingerprint_sha256"], "candidate_production_commit": package["candidate_production_commit"], "candidate_tree_sha256": package["candidate_tree_sha256"], "inference_input_sha256": package["inference_input_sha256"], "retriever_decision_identity": package["retriever_decision_identity"], "runtime_identity": package["runtime_identity"], "start_state": "ROW_1_INFERENCE_BOUNDARY", "mid_run_resume_supported": False}
    atomic_consumption_receipt(consumption_path, consumption)
    if runner is None: runner = _load_production_runner(root, package)
    row_hashes: list[str] = []; raw_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with raw_path.open("x", encoding="utf-8", newline="\n") as handle:
            for item in inputs:
                raw = runner(item)
                if not isinstance(raw, dict) or raw.get("query_id") != item["case_id"]: raise RuntimeError("RAW_QUERY_ID_BINDING")
                payload = json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                handle.write(payload); handle.flush(); os.fsync(handle.fileno()); row_hashes.append(hashlib.sha256(payload.encode("utf-8")).hexdigest())
    except Exception as error:
        raise RuntimeError("EV3_CONSUMED_EXECUTION_FAILED_SENIOR_ADJUDICATION_REQUIRED") from error
    if len(row_hashes) != 60: raise RuntimeError("EV3_CONSUMED_INCOMPLETE_NO_RESUME")
    frozen = {"schema_version": RAW_SCHEMA, "rows": 60, "raw_output_path": relative_path(root, raw_path), "raw_output_sha256": sha256(raw_path), "raw_row_sha256": row_hashes, "case_id_order": [row["case_id"] for row in inputs], "query_sha256_order": [row["query_sha256"] for row in inputs], "execution_package_manifest_sha256": package["_verified_package_sha256"], "runtime_attestation_receipt_path": relative_path(root, runtime_attestation_path), "runtime_attestation_receipt_sha256": package["_verified_runtime_attestation_sha256"], "environment_fingerprint_sha256": runtime["environment_fingerprint_sha256"], "authorization_receipt_path": relative_path(root, authorization_path), "authorization_receipt_sha256": sha256(authorization_path), "consumption_receipt_path": relative_path(root, consumption_path), "consumption_receipt_sha256": sha256(consumption_path), "candidate_production_commit": package["candidate_production_commit"], "candidate_tree_sha256": package["candidate_tree_sha256"], "candidate_source_sha256": package["candidate_source_sha256"], "inference_input_sha256": package["inference_input_sha256"], "evaluator_source_sha256": package["evaluator_source_sha256"], "e1_harness_sha256": package["e1_harness_sha256"], "retriever_decision_identity": package["retriever_decision_identity"], "runtime_identity": package["runtime_identity"], "scoring_loaded": False}
    schema = load_json(resolve_from_root(root, package["paths"]["raw_manifest_schema"]))
    if set(frozen) != set(schema["required_fields"]): raise RuntimeError("RAW_MANIFEST_SCHEMA_EMISSION_MISMATCH")
    atomic_write_json(raw_manifest_path, frozen)
    return frozen


def _load_production_runner(root: Path, package: dict[str, Any]) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Production imports follow the durable consumption receipt, never precede it."""
    from payresolve_ai.generation.gate import build_idf
    from payresolve_ai.generation.pipeline_v3 import load_v3_configuration, run_case_v3
    from payresolve_ai.generation.support_v2 import build_canonical_idf
    from payresolve_ai.retrieval.benchmark import _load_runtime, _rank_queries, load_config
    runtime = package["runtime_identity"]
    retrieval = load_config(root, root / runtime["retrieval_config_path"], require_local_model=True); chunks, _ = _load_runtime(root, retrieval)
    generation, lexicon, _ = load_v3_configuration(root, root / runtime["generation_config_path"])
    raw_idf = build_idf(chunks, generation["tokenizer"]["stopwords"]); canonical_idf = build_canonical_idf(chunks, lexicon, generation["tokenizer"]["stopwords"])
    def candidate(item: dict[str, Any]) -> dict[str, Any]:
        query = {"query_id": item["case_id"], "query_text": item["query"], "split": "ev3", "gold_intent": "__NOT_AVAILABLE_TO_INFERENCE__"}
        ranked, _ = rank_with_frozen_retriever(_rank_queries, root, retrieval, query, package)
        return run_case_v3(query, ranked[0]["rankings"], chunks, raw_idf, canonical_idf, generation, lexicon)
    return candidate


def _resolve_cli_path(root: Path, value: Path) -> Path: return resolve_from_root(root, value)


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("command", choices=("run",)); parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--execution-package", type=Path, required=True); parser.add_argument("--runtime-attestation-receipt", type=Path, required=True); parser.add_argument("--authorization-receipt", type=Path, required=True); parser.add_argument("--inputs", type=Path, required=True); parser.add_argument("--consumption-receipt", type=Path, required=True); parser.add_argument("--raw-output", type=Path, required=True); parser.add_argument("--raw-manifest", type=Path, required=True)
    args = parser.parse_args(); root = args.root.resolve()
    execute_raw_only(root, _resolve_cli_path(root, args.execution_package), _resolve_cli_path(root, args.inputs), _resolve_cli_path(root, args.runtime_attestation_receipt), _resolve_cli_path(root, args.authorization_receipt), _resolve_cli_path(root, args.consumption_receipt), _resolve_cli_path(root, args.raw_output), _resolve_cli_path(root, args.raw_manifest)); return 0


if __name__ == "__main__": raise SystemExit(main())
