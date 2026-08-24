"""A4-guarded raw-only EV2 E1 harness with pre-row-1 source-tree binding."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable

from scripts.evaluation.week3_ev2_integrity import (
    IntegrityError,
    aggregate_bindings_sha256,
    atomic_write_json,
    sha256,
    verify_working_source_tree,
)

A4_SCHEMA_VERSION = "W3-003-EV2-A4-AUTHORIZATION-V3"
CONSUMPTION_SCHEMA_VERSION = "W3-003-EV2-CONSUMPTION-V3"
A3_STATUS = "A3_FIX4_FROZEN_PACKAGE_AWAITING_SENIOR_REVIEW"
RAW_SCHEMA = "W3-003-EV2-E1-RAW-MANIFEST-V2"
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


def required_a4(manifest: dict[str, Any], manifest_sha256: str) -> dict[str, Any]:
    artifacts = manifest["artifact_sha256"]
    return {
        "schema_version": A4_SCHEMA_VERSION,
        "authorization": "A4_AUTHORIZE_E1",
        "ev2_authorized": True,
        "a3_manifest_sha256": manifest_sha256,
        "candidate_production_commit": manifest["candidate_production_commit"],
        "evaluation_package_source_commit": manifest["evaluation_package_source_commit"],
        "candidate_source_tree_sha256": manifest["candidate_source_tree_sha256"],
        "candidate_source_tree_receipt_sha256": artifacts["candidate_source_tree_receipt"],
        "runtime_input_aggregate_sha256": manifest["runtime_input_aggregate_sha256"],
        "selected_retriever": manifest["selected_retriever"],
        "retrieval_decision_sha256": manifest["retrieval_decision_sha256"],
        "case_order_sha256": manifest["case_order_sha256"],
        "inference_input_sha256": manifest["inference_input_sha256"],
        "evaluator_source_sha256": manifest["evaluator_source_sha256"],
        "evaluator_mapping_sha256": manifest["evaluator_mapping_sha256"],
        "reason_compatibility_sha256": artifacts["reason_compatibility"],
        "forbidden_action_rules_sha256": artifacts["forbidden_action_rules"],
        "product_gate_contract_sha256": artifacts["product_gate_contract"],
        "raw_manifest_schema_sha256": artifacts["raw_manifest_schema"],
        "e1_harness_sha256": manifest["e1_harness_sha256"],
        "integrity_source_sha256": manifest["integrity_source_sha256"],
        "senior_approval_state": "SENIOR_A4_APPROVED",
    }


def validate_a4(receipt: Path | None, manifest: dict[str, Any], manifest_sha256: str) -> dict[str, Any]:
    if receipt is None or not receipt.is_file():
        raise PermissionError("A4_AUTHORIZATION_REQUIRED_BEFORE_EV2_ROW_1")
    value = load_json(receipt)
    if not isinstance(value, dict):
        raise PermissionError("A4_AUTHORIZATION_OBJECT_REQUIRED")
    for key, wanted in required_a4(manifest, manifest_sha256).items():
        if value.get(key) != wanted:
            raise PermissionError(f"A4_BINDING_MISMATCH:{key}")
    if not isinstance(value.get("authorization_nonce_or_id"), str) or not value["authorization_nonce_or_id"]:
        raise PermissionError("A4_AUTHORIZATION_ID_REQUIRED")
    return value


def atomic_consumption_receipt(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise RuntimeError("EV2_ALREADY_CONSUMED_NO_RESUME_OR_RERUN")
    atomic_write_json(path, payload)


def _verify_bound_file(root: Path, relative: str, wanted: str, label: str) -> None:
    path = root / relative
    if not path.is_file() or sha256(path) != wanted:
        raise RuntimeError(f"A3_EXECUTION_ARTIFACT_IDENTITY_DRIFT:{label}")


def validate_frozen_retriever_decision(root: Path, manifest: dict[str, Any]) -> None:
    """Validate the final Week-2 control-plane decision before row-1 consumption."""
    try:
        source = manifest["retrieval_decision_source"]
        wanted_sha = manifest["retrieval_decision_sha256"]
        if manifest["selected_retriever"] != "R0" or not isinstance(source, str) or not isinstance(wanted_sha, str):
            raise ValueError
        path = root / source
        if not path.is_file() or sha256(path) != wanted_sha:
            raise ValueError
        decision = load_json(path)
        if not isinstance(decision, dict) or decision.get("selected_retriever") != "R0":
            raise ValueError
        if decision.get("final_senior_review_verdict") != "APPROVE_COMMIT":
            raise ValueError
        if decision.get("status") != "FINALIZED_REVIEW_CORRECTION":
            raise ValueError
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
        raise RuntimeError(FROZEN_RETRIEVER_ERROR) from None


def r0_execution_boost(manifest: dict[str, Any]) -> None:
    """The FIX4 package admits only the frozen R0 branch (``boost is None``)."""
    if manifest.get("selected_retriever") != "R0":
        raise RuntimeError(FROZEN_RETRIEVER_ERROR)
    return None


def rank_with_frozen_retriever(
    rank_queries: Callable[[Path, dict[str, Any], list[dict[str, Any]], float | None], tuple[list[dict[str, Any]], Any]],
    root: Path,
    retrieval: dict[str, Any],
    query: dict[str, Any],
    manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], Any]:
    """Injection seam proving that R0 never receives the R1 development boost."""
    return rank_queries(root, retrieval, [query], r0_execution_boost(manifest))


def validate_pre_inference(
    root: Path,
    manifest_path: Path,
    inputs_path: Path,
    a4_path: Path | None,
    consumption_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("status") != A3_STATUS:
        raise RuntimeError("A3_FIX4_MANIFEST_REQUIRED")
    if manifest.get("mid_run_resume_supported") is not False or manifest.get("checkpoint_resume_explicitly_disabled") is not True:
        raise RuntimeError("RESUME_NOT_DISABLED")
    if sha256(inputs_path) != manifest["inference_input_sha256"]:
        raise RuntimeError("INFERENCE_INPUT_SHA_DRIFT")

    for group in ("production_sha256", "runtime_input_sha256"):
        bindings = manifest.get(group)
        if not isinstance(bindings, dict) or not bindings:
            raise RuntimeError(f"MISSING_IDENTITY_BINDING:{group}")
        for relative, wanted in bindings.items():
            _verify_bound_file(root, relative, wanted, relative)
    if aggregate_bindings_sha256(manifest["runtime_input_sha256"]) != manifest["runtime_input_aggregate_sha256"]:
        raise RuntimeError("RUNTIME_BINDING_AGGREGATE_DRIFT")
    validate_frozen_retriever_decision(root, manifest)

    paths = manifest.get("paths")
    artifacts = manifest.get("artifact_sha256")
    if not isinstance(paths, dict) or not isinstance(artifacts, dict):
        raise RuntimeError("A3_BOUND_PATHS_REQUIRED")
    bound = {
        "evaluator_source": "scripts/evaluation/week3_ev2_evaluator.py",
        "evaluator_mapping": paths["evaluator_mapping"],
        "reason_compatibility": paths["reason_compatibility"],
        "forbidden_action_rules": paths["forbidden_action_rules"],
        "product_gate_contract": paths["product_gate_contract"],
        "raw_manifest_schema": paths["raw_manifest_schema"],
        "case_order": paths["case_order"],
        "candidate_source_tree_receipt": paths["candidate_source_tree_receipt"],
    }
    direct = {
        "evaluator_source": manifest["evaluator_source_sha256"],
        "evaluator_mapping": manifest["evaluator_mapping_sha256"],
        "case_order": manifest["case_order_sha256"],
    }
    for label, relative in bound.items():
        _verify_bound_file(root, relative, direct.get(label, artifacts.get(label)), label)
    _verify_bound_file(root, "scripts/evaluation/week3_ev2_e1.py", manifest["e1_harness_sha256"], "e1_harness")
    _verify_bound_file(root, "scripts/evaluation/week3_ev2_integrity.py", manifest["integrity_source_sha256"], "integrity_source")

    source_receipt = load_json(root / paths["candidate_source_tree_receipt"])
    if not isinstance(source_receipt, dict) or source_receipt.get("candidate_commit") != manifest["candidate_production_commit"]:
        raise RuntimeError("CANDIDATE_SOURCE_TREE_RECEIPT_BINDING")
    git_tree = subprocess.check_output(
        ["git", "rev-parse", f"{manifest['candidate_production_commit']}:src/payresolve_ai"], cwd=root, text=True
    ).strip()
    if git_tree != source_receipt.get("git_tree"):
        raise RuntimeError("CANDIDATE_GIT_TREE_IDENTITY_DRIFT")
    try:
        actual_source_sha = verify_working_source_tree(root, source_receipt)
    except IntegrityError as error:
        raise RuntimeError(str(error)) from error
    if actual_source_sha != manifest["candidate_source_tree_sha256"]:
        raise RuntimeError("CANDIDATE_EXECUTION_SOURCE_TREE_DRIFT")

    manifest_sha256 = sha256(manifest_path)
    inputs = read_jsonl(inputs_path)
    if len(inputs) != 60 or [row.get("ordinal") for row in inputs] != list(range(1, 61)):
        raise RuntimeError("INFERENCE_INPUT_ORDER_OR_COUNT")
    if any(
        set(row) != {"ordinal", "case_id", "query", "query_sha256"}
        or not isinstance(row["query"], str)
        or hashlib.sha256(row["query"].encode("utf-8")).hexdigest() != row["query_sha256"]
        for row in inputs
    ):
        raise RuntimeError("INFERENCE_INPUT_SCHEMA_OR_QUERY_HASH")
    order = load_json(root / paths["case_order"])
    expected = [(row["ordinal"], row["case_id"], row["query_sha256"]) for row in inputs]
    if not isinstance(order, list) or [(row.get("ordinal"), row.get("case_id"), row.get("query_sha256")) for row in order] != expected:
        raise RuntimeError("CASE_ORDER_BINDING_MISMATCH")
    if consumption_path.exists():
        raise RuntimeError("EV2_ALREADY_CONSUMED_NO_RESUME_OR_RERUN")
    receipt = validate_a4(a4_path, manifest, manifest_sha256)
    manifest["_verified_manifest_sha256"] = manifest_sha256
    return manifest, receipt, inputs


def execute_raw_only(
    root: Path,
    manifest_path: Path,
    inputs_path: Path,
    a4_path: Path | None,
    consumption_path: Path,
    raw_path: Path,
    raw_manifest_path: Path,
    runner: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    for path in (manifest_path, inputs_path, consumption_path, raw_path, raw_manifest_path):
        relative_path(root, path)
    if a4_path is not None:
        relative_path(root, a4_path)
    manifest, a4, inputs = validate_pre_inference(root, manifest_path, inputs_path, a4_path, consumption_path)
    if raw_path.exists() or raw_manifest_path.exists():
        raise RuntimeError("RAW_OUTPUT_CONFLICT_NO_PARTIAL_RERUN")
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    first = inputs[0]
    consumption = {
        "schema_version": CONSUMPTION_SCHEMA_VERSION,
        "ev2_consumed": True,
        "started_ordinal": 1,
        "case_id": first["case_id"],
        "query_sha256": first["query_sha256"],
        "a3_manifest_sha256": manifest["_verified_manifest_sha256"],
        "a4_authorization_id": a4["authorization_nonce_or_id"],
        "candidate_production_commit": manifest["candidate_production_commit"],
        "candidate_source_tree_sha256": manifest["candidate_source_tree_sha256"],
        "runtime_input_aggregate_sha256": manifest["runtime_input_aggregate_sha256"],
        "selected_retriever": manifest["selected_retriever"],
        "retrieval_decision_sha256": manifest["retrieval_decision_sha256"],
        "start_state": "ROW_1_INFERENCE_BOUNDARY",
        "mid_run_resume_supported": False,
    }
    atomic_consumption_receipt(consumption_path, consumption)
    if runner is None:
        runner = _load_production_runner(root, manifest)
    row_hashes: list[str] = []
    try:
        with raw_path.open("x", encoding="utf-8", newline="\n") as handle:
            for item in inputs:
                raw = runner(item)
                if not isinstance(raw, dict) or raw.get("query_id") != item["case_id"]:
                    raise RuntimeError("RAW_QUERY_ID_BINDING")
                payload = json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                handle.write(payload); handle.flush(); os.fsync(handle.fileno())
                row_hashes.append(hashlib.sha256(payload.encode("utf-8")).hexdigest())
    except Exception as error:
        raise RuntimeError("EV2_CONSUMED_EXECUTION_FAILED_SENIOR_ADJUDICATION_REQUIRED") from error
    if len(row_hashes) != 60:
        raise RuntimeError("EV2_CONSUMED_INCOMPLETE_NO_RESUME")
    frozen = {
        "schema_version": RAW_SCHEMA,
        "rows": 60,
        "raw_output_path": relative_path(root, raw_path),
        "raw_output_sha256": sha256(raw_path),
        "raw_row_sha256": row_hashes,
        "case_id_order": [row["case_id"] for row in inputs],
        "query_sha256_order": [row["query_sha256"] for row in inputs],
        "case_order_sha256": manifest["case_order_sha256"],
        "a3_manifest_sha256": manifest["_verified_manifest_sha256"],
        "a4_authorization_id": a4["authorization_nonce_or_id"],
        "candidate_production_commit": manifest["candidate_production_commit"],
        "candidate_source_tree_sha256": manifest["candidate_source_tree_sha256"],
        "runtime_input_aggregate_sha256": manifest["runtime_input_aggregate_sha256"],
        "selected_retriever": manifest["selected_retriever"],
        "retrieval_decision_sha256": manifest["retrieval_decision_sha256"],
        "inference_input_sha256": manifest["inference_input_sha256"],
        "consumption_receipt_path": relative_path(root, consumption_path),
        "consumption_receipt_sha256": sha256(consumption_path),
        "e1_harness_sha256": manifest["e1_harness_sha256"],
        "scoring_loaded": False,
    }
    schema = load_json(root / manifest["paths"]["raw_manifest_schema"])
    if set(frozen) != set(schema["required_fields"]):
        raise RuntimeError("RAW_MANIFEST_SCHEMA_EMISSION_MISMATCH")
    atomic_write_json(raw_manifest_path, frozen)
    return frozen


def _load_production_runner(root: Path, manifest: dict[str, Any]) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Production imports occur only after A4 and the atomic consumption receipt."""
    from payresolve_ai.generation.gate import build_idf
    from payresolve_ai.generation.pipeline_v3 import load_v3_configuration, run_case_v3
    from payresolve_ai.generation.support_v2 import build_canonical_idf
    from payresolve_ai.retrieval.benchmark import _load_runtime, _rank_queries, load_config

    retrieval_path = root / "configs/retrieval/kb_v1_r0_r1.json"
    retrieval = load_config(root, retrieval_path, require_local_model=True)
    chunks, _ = _load_runtime(root, retrieval)
    generation, lexicon, _ = load_v3_configuration(root, root / "configs/generation/grounded_pipeline_v3.json")
    raw_idf = build_idf(chunks, generation["tokenizer"]["stopwords"])
    canonical_idf = build_canonical_idf(chunks, lexicon, generation["tokenizer"]["stopwords"])

    def candidate(item: dict[str, Any]) -> dict[str, Any]:
        query = {"query_id": item["case_id"], "query_text": item["query"], "split": "ev2", "gold_intent": "__NOT_AVAILABLE_TO_INFERENCE__"}
        ranked, _ = rank_with_frozen_retriever(_rank_queries, root, retrieval, query, manifest)
        return run_case_v3(query, ranked[0]["rankings"], chunks, raw_idf, canonical_idf, generation, lexicon)

    return candidate


def _resolve_cli_path(root: Path, value: Path) -> Path:
    if value.is_absolute():
        raise RuntimeError("ABSOLUTE_PATH_FORBIDDEN")
    path = (root / value).resolve()
    relative_path(root, path)
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("run",))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--a3-manifest", type=Path, required=True)
    parser.add_argument("--a4-receipt", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--consumption-receipt", type=Path, required=True)
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--raw-manifest", type=Path, required=True)
    args = parser.parse_args(); root = args.root.resolve()
    execute_raw_only(
        root,
        _resolve_cli_path(root, args.a3_manifest),
        _resolve_cli_path(root, args.inputs),
        _resolve_cli_path(root, args.a4_receipt),
        _resolve_cli_path(root, args.consumption_receipt),
        _resolve_cli_path(root, args.raw_output),
        _resolve_cli_path(root, args.raw_manifest),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
