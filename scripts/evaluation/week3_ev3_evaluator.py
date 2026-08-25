"""Frozen EV3 evaluator: EV2 scorer semantics plus the approved complete-Gold merge."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from scripts.evaluation import week3_ev2_evaluator as ev2
from scripts.evaluation.week3_ev2_integrity import sha256, stable_json_sha256


SCORE_SCHEMA = "W3-003-EV3-R1-SCORE-V1"
RAW_SCHEMA = "W3-003-EV3-E1-RAW-MANIFEST-V2"
PACKAGE_SCHEMA = "W3-003-EV3-EH1-FIX2-EXECUTION-PACKAGE-V1"
PACKAGE_STATUS = "EV3_EH1_FIX2_FROZEN_PREEXECUTION_PACKAGE"
RUNTIME_ATTESTATION_SCHEMA = "W3-003-EV3-RUNTIME-ATTESTATION-V1"
EVALUATOR_BINDING_SCHEMA = "W3-003-EV3-EVALUATOR-BINDING-CONTRACT-V1"
EXPECTED_REASON_FAMILIES = {
    "STANDARD_COMPLETE_APPROVED_SUPPORT",
    "SAFE_CORRECTIVE_COMPLETE_APPROVED_FACTUAL_SUPPORT",
    "NO_APPROVED_COMPLETE_SUPPORT",
    "PURE_CLARIFICATION_ONLY_SAFE_STOP",
}
ROUTE_BY_STRATEGY = {
    "STANDARD": "STANDARD",
    "CORRECTIVE": "SAFE_CORRECTIVE",
    "ABSTAIN": "ABSTAIN_ESCALATE",
}


EvaluationIntegrityError = ev2.EvaluationIntegrityError
read_json = ev2.read_json
read_jsonl = ev2.read_jsonl
resolve_from_root = ev2.resolve_from_root
evaluate_row = ev2.evaluate_row
aggregate = ev2.aggregate
load_mapping = ev2.load_mapping
load_reason_compatibility = ev2.load_reason_compatibility


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise EvaluationIntegrityError(code)


def _read_frozen_jsonl(root: Path, relative: str, wanted: str, rows: int) -> list[dict[str, Any]]:
    path = resolve_from_root(root, relative)
    _require(sha256(path) == wanted, f"COMPLETE_GOLD_DRIFT:{relative}")
    value = read_jsonl(path)
    _require(len(value) == rows, f"COMPLETE_GOLD_ROW_COUNT:{relative}")
    return value


def load_complete_gold(root: Path, complete_gold_manifest_path: Path, binding_contract_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Fail-closed deterministic Pass-C + companion merge in frozen Pass-C order."""
    manifest = read_json(complete_gold_manifest_path)
    binding = read_json(binding_contract_path)
    _require(manifest.get("status") == "FROZEN", "COMPLETE_GOLD_MANIFEST_NOT_FROZEN")
    flags = manifest.get("flags", {})
    _require(all(flags.get(key) is value for key, value in {
        "base_gold_unchanged": True,
        "semantic_bindings_complete": True,
        "complete_gold_package_frozen": True,
        "candidate_output_seen": False,
        "production_inference_started": False,
        "ev3_consumed": False,
    }.items()), "COMPLETE_GOLD_FLAGS_INVALID")
    _require(binding.get("schema_version") == EVALUATOR_BINDING_SCHEMA, "EVALUATOR_BINDING_SCHEMA_INVALID")
    _require(binding.get("all_other_frozen_ev2_semantics_must_remain_identical") is True, "EV2_SEMANTICS_UNBOUND")
    left = binding.get("future_deterministic_companion_merge", {}).get("left", {})
    right = binding.get("future_deterministic_companion_merge", {}).get("right", {})
    base = manifest.get("base_gold_artifacts", [])
    semantic = manifest.get("semantic_binding_artifacts", [])
    _require(len(base) == 3 and len(semantic) >= 1, "COMPLETE_GOLD_ARTIFACTS_INVALID")
    pass_a = _read_frozen_jsonl(root, base[0]["path"], base[0]["sha256"], 60)
    pass_b = _read_frozen_jsonl(root, base[1]["path"], base[1]["sha256"], 4320)
    pass_c = _read_frozen_jsonl(root, base[2]["path"], base[2]["sha256"], 60)
    addendum = _read_frozen_jsonl(root, semantic[0]["path"], semantic[0]["sha256"], 60)
    _require(left.get("path") == base[2]["path"] and left.get("sha256") == base[2]["sha256"], "PASS_C_BINDING_CONTRACT_DRIFT")
    _require(right.get("path") == semantic[0]["path"] and right.get("sha256") == semantic[0]["sha256"], "ADDENDUM_BINDING_CONTRACT_DRIFT")
    pass_a_ids = [row.get("case_id") for row in pass_a]
    pass_c_ids = [row.get("query_id") for row in pass_c]
    _require(len(set(pass_a_ids)) == 60 and pass_a_ids == pass_c_ids, "PASS_A_PASS_C_ORDER_OR_ID_INVALID")
    addendum_by = {row.get("case_id"): row for row in addendum}
    _require(len(addendum_by) == 60 and len(addendum_by) == len(addendum), "ADDENDUM_ID_UNIQUENESS_INVALID")
    merged: list[dict[str, Any]] = []
    for base_row in pass_c:
        case_id = base_row.get("query_id")
        companion = addendum_by.get(case_id)
        _require(isinstance(companion, dict), "COMPANION_ROW_MISSING")
        _require(companion.get("query_sha256") == base_row.get("query_sha256"), "COMPANION_QUERY_SHA_MISMATCH")
        family = companion.get("expected_reason_family")
        codes = companion.get("forbidden_claims_actions")
        sets = companion.get("acceptable_complete_support_sets")
        _require(family in EXPECTED_REASON_FAMILIES, "UNKNOWN_EXPECTED_REASON_FAMILY")
        _require(isinstance(codes, list) and all(isinstance(code, str) for code in codes), "FORBIDDEN_CODE_SCHEMA_INVALID")
        _require(isinstance(sets, list) and all(isinstance(item, list) for item in sets), "COMPLETE_SUPPORT_SET_SCHEMA_INVALID")
        strategy = base_row.get("expected_answer_strategy")
        _require(strategy in ROUTE_BY_STRATEGY, "EXPECTED_STRATEGY_INVALID")
        merged.append({
            **base_row,
            "case_id": case_id,
            "expected_production_route": ROUTE_BY_STRATEGY[strategy],
            "expected_reason_family": family,
            "acceptable_complete_support_sets": sets,
            "complete_approved_support_exists_in_kb": companion.get("complete_approved_support_exists_in_kb"),
            "allowed_supporting_evidence": base_row.get("eligible_supporting_evidence"),
            "forbidden_evidence": base_row.get("forbidden_evidence_ids"),
            "forbidden_claims_actions": codes,
        })
    _require([row["case_id"] for row in merged] == pass_a_ids, "MERGED_CASE_ORDER_INVALID")
    _require([row["query_sha256"] for row in merged] == [row["query_sha256"] for row in pass_a], "MERGED_QUERY_ORDER_INVALID")
    return pass_a, pass_b, merged, manifest


def load_safety_rules_subset(path: Path, referenced_codes: Iterable[str]) -> dict[str, Any]:
    """The sole approved EV3 semantic rebind: references are a known registry subset."""
    value = read_json(path)
    rows = value.get("rules", [])
    registry_codes = {row.get("code") for row in rows}
    _require(value.get("schema_version") == "W3-003-EV2-FORBIDDEN-ACTION-RULES-V2", "FORBIDDEN_ACTION_RULE_SCHEMA_INVALID")
    _require(value.get("unknown_code_policy") == "FAIL_CLOSED_EVALUATOR_INTEGRITY", "FORBIDDEN_ACTION_POLICY_INVALID")
    _require(len(rows) == len(registry_codes) == 27, "FORBIDDEN_ACTION_REGISTRY_INVALID")
    unknown = set(referenced_codes) - registry_codes
    _require(not unknown, "UNKNOWN_FORBIDDEN_ACTION_CODE")
    # Reuse the frozen parser/regex validation without retaining EV2's historical full-coverage invariant.
    for row in rows:
        _require(isinstance(row.get("unsafe_patterns"), list) and row["unsafe_patterns"], "FORBIDDEN_ACTION_RULE_EMPTY")
        _require(isinstance(row.get("safe_negated_patterns"), list) and row["safe_negated_patterns"], "FORBIDDEN_ACTION_RULE_EMPTY")
    return value


def _verify_static_scorer_identities(root: Path, package: dict[str, Any]) -> None:
    """Bind every scorer input before Gold is opened or scorer code is invoked."""
    paths = package.get("paths", {})
    artifacts = package.get("artifact_sha256", {})
    labels = (
        "raw_manifest_schema", "runtime_attestation_schema", "evaluator_source", "e1_harness",
        "evaluator_mapping", "reason_compatibility", "forbidden_action_rules", "product_gate_contract",
    )
    for label in labels:
        relative, wanted = paths.get(label), artifacts.get(label)
        _require(isinstance(relative, str) and isinstance(wanted, str), f"SCORER_BINDING_MISSING:{label}")
        path = resolve_from_root(root, relative)
        _require(path.is_file() and sha256(path) == wanted, f"SCORER_IDENTITY_DRIFT:{label}")
    _require(artifacts["evaluator_source"] == package.get("evaluator_source_sha256"), "EVALUATOR_PACKAGE_BINDING_INVALID")
    _require(artifacts["e1_harness"] == package.get("e1_harness_sha256"), "HARNESS_PACKAGE_BINDING_INVALID")


def _verify_environment_fingerprint_binding(root: Path, raw_manifest: dict[str, Any], package: dict[str, Any], package_sha: str, receipt: dict[str, Any]) -> None:
    """Bind the raw/runtime fingerprint claim to the canonical package file before Gold."""
    relative = package.get("paths", {}).get("runtime_environment_fingerprint")
    _require(isinstance(relative, str) and relative, "RUNTIME_ATTESTATION_ENVIRONMENT_FINGERPRINT_PATH_REQUIRED")
    path = resolve_from_root(root, relative)
    _require(path.is_file(), "RUNTIME_ATTESTATION_ENVIRONMENT_FINGERPRINT_MISSING")
    actual_sha = sha256(path)
    _require(actual_sha == receipt.get("environment_fingerprint_sha256"), "RUNTIME_ATTESTATION_ENVIRONMENT_FINGERPRINT_SHA_MISMATCH")
    _require(actual_sha == raw_manifest.get("environment_fingerprint_sha256"), "RAW_RUNTIME_ENVIRONMENT_FINGERPRINT_SHA_MISMATCH")
    fingerprint = read_json(path)
    expected = {
        "execution_package_manifest_sha256": package_sha,
        "candidate_production_commit": package["candidate_production_commit"],
        "candidate_tree_sha256": package["candidate_tree_sha256"],
        "inference_input_sha256": package["inference_input_sha256"],
        "evaluator_source_sha256": package["evaluator_source_sha256"],
        "e1_harness_sha256": package["e1_harness_sha256"],
        "runtime_identity": package["runtime_identity"],
        "model_identity": package["runtime_attestation_contract"]["model_identity"],
        "environment_identity": package["runtime_attestation_contract"]["environment_identity"],
    }
    for key, wanted in expected.items():
        _require(fingerprint.get(key) == wanted, f"RUNTIME_FINGERPRINT_BINDING_MISMATCH:{key}")
    for key in (
        "network_attempts", "query_encoding_calls", "ranking_calls", "production_inference_calls",
        "gold_semantic_loads", "official_scorer_calls",
    ):
        _require(fingerprint.get(key) == 0, f"RUNTIME_FINGERPRINT_ACTIVITY:{key}")


def _verify_runtime_attestation_binding(root: Path, raw_manifest: dict[str, Any], package: dict[str, Any], package_sha: str) -> dict[str, Any]:
    """Evaluator-side duplicate check: raw receipt and runtime identity must be package-bound."""
    schema_path = resolve_from_root(root, package["paths"]["runtime_attestation_schema"])
    _require(sha256(schema_path) == package["artifact_sha256"]["runtime_attestation_schema"], "RUNTIME_ATTESTATION_SCHEMA_IDENTITY_DRIFT")
    schema = read_json(schema_path)
    fields = schema.get("required_fields")
    _require(schema.get("schema_version") == RUNTIME_ATTESTATION_SCHEMA and isinstance(fields, list), "RUNTIME_ATTESTATION_SCHEMA_INVALID")
    receipt_path = resolve_from_root(root, raw_manifest["runtime_attestation_receipt_path"])
    _require(sha256(receipt_path) == raw_manifest["runtime_attestation_receipt_sha256"], "RAW_RUNTIME_RECEIPT_SHA_MISMATCH")
    receipt = read_json(receipt_path)
    _require(isinstance(receipt, dict) and set(receipt) == set(fields), "RUNTIME_ATTESTATION_FIELDS_INVALID")
    _require(receipt.get("schema_version") == RUNTIME_ATTESTATION_SCHEMA and receipt.get("status") == "RUNTIME_LOAD_ONLY_ATTESTED", "RUNTIME_ATTESTATION_STATUS_INVALID")
    expected = {
        "execution_package_manifest_sha256": package_sha,
        "candidate_production_commit": package["candidate_production_commit"],
        "candidate_tree_sha256": package["candidate_tree_sha256"],
        "candidate_source_config_aggregate_sha256": stable_json_sha256(package["candidate_source_sha256"]),
        "inference_input_sha256": package["inference_input_sha256"],
        "evaluator_source_sha256": package["evaluator_source_sha256"],
        "e1_harness_sha256": package["e1_harness_sha256"],
        "retriever_decision_identity": package["retriever_decision_identity"],
        "runtime_identity": package["runtime_identity"],
        "model_identity": package["runtime_attestation_contract"]["model_identity"],
        "environment_identity": package["runtime_attestation_contract"]["environment_identity"],
    }
    for key, wanted in expected.items():
        _require(receipt.get(key) == wanted, f"RUNTIME_ATTESTATION_BINDING_MISMATCH:{key}")
    _require(receipt.get("runtime_load_only_proof") is True and receipt.get("query_encoding_calls") == 0 and receipt.get("ranking_calls") == 0 and receipt.get("network_attempts") == 0, "RUNTIME_ATTESTATION_RUNTIME_ACTIVITY")
    _verify_environment_fingerprint_binding(root, raw_manifest, package, package_sha, receipt)
    _require(raw_manifest.get("runtime_identity") == package["runtime_identity"], "RAW_RUNTIME_IDENTITY_MISMATCH")
    return receipt


def _load_raw_receipt(root: Path, raw_manifest: dict[str, Any], path_key: str, sha_key: str, label: str) -> dict[str, Any]:
    """Resolve, hash, and parse an execution receipt before any Gold access."""
    try:
        path = resolve_from_root(root, raw_manifest[path_key])
        _require(path.is_file(), f"RAW_{label}_RECEIPT_MISSING")
        _require(sha256(path) == raw_manifest[sha_key], f"RAW_{label}_RECEIPT_SHA_MISMATCH")
        value = read_json(path)
    except (KeyError, OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise EvaluationIntegrityError(f"RAW_{label}_RECEIPT_INVALID") from error
    _require(isinstance(value, dict), f"RAW_{label}_RECEIPT_OBJECT_REQUIRED")
    return value


def _verify_authorization_and_consumption_binding(root: Path, raw_manifest: dict[str, Any], package: dict[str, Any], runtime: dict[str, Any]) -> None:
    """Establish package -> runtime -> authorization -> consumption -> raw provenance."""
    authorization = _load_raw_receipt(root, raw_manifest, "authorization_receipt_path", "authorization_receipt_sha256", "AUTHORIZATION")
    package_sha = raw_manifest["execution_package_manifest_sha256"]
    authorization_expected = {
        "execution_package_manifest_sha256": package_sha,
        "candidate_production_commit": package["candidate_production_commit"],
        "candidate_tree_sha256": package["candidate_tree_sha256"],
        "inference_input_sha256": package["inference_input_sha256"],
        "evaluator_source_sha256": package["evaluator_source_sha256"],
        "e1_harness_sha256": package["e1_harness_sha256"],
        "raw_manifest_schema_sha256": package["raw_manifest_schema_sha256"],
        "retriever_decision_identity": package["retriever_decision_identity"],
        "runtime_attestation_receipt_path": raw_manifest["runtime_attestation_receipt_path"],
        "runtime_attestation_receipt_sha256": raw_manifest["runtime_attestation_receipt_sha256"],
        "environment_fingerprint_sha256": raw_manifest["environment_fingerprint_sha256"],
    }
    for key, wanted in authorization_expected.items():
        _require(authorization.get(key) == wanted, f"AUTHORIZATION_BINDING_MISMATCH:{key}")
    _require(authorization.get("authorization") == "EV3_AUTHORIZE_E1", "AUTHORIZATION_TYPE_INVALID")
    _require(authorization.get("ev3_authorized") is True, "AUTHORIZATION_NOT_GRANTED")
    _require(authorization.get("senior_approval_state") == "SENIOR_EV3_PREEXEC_APPROVED", "AUTHORIZATION_SENIOR_STATE_INVALID")
    authorization_id = authorization.get("authorization_nonce_or_id")
    _require(isinstance(authorization_id, str) and authorization_id, "AUTHORIZATION_ID_INVALID")
    _require(authorization["runtime_attestation_receipt_sha256"] == raw_manifest["runtime_attestation_receipt_sha256"], "AUTHORIZATION_RAW_RUNTIME_SHA_MISMATCH")
    _require(authorization["environment_fingerprint_sha256"] == runtime["environment_fingerprint_sha256"], "AUTHORIZATION_RUNTIME_ENVIRONMENT_MISMATCH")

    consumption = _load_raw_receipt(root, raw_manifest, "consumption_receipt_path", "consumption_receipt_sha256", "CONSUMPTION")
    consumption_expected = {
        "schema_version": "W3-003-EV3-CONSUMPTION-V2",
        "ev3_consumed": True,
        "started_ordinal": 1,
        "execution_package_manifest_sha256": package_sha,
        "authorization_id": authorization_id,
        "runtime_attestation_receipt_path": authorization["runtime_attestation_receipt_path"],
        "runtime_attestation_receipt_sha256": authorization["runtime_attestation_receipt_sha256"],
        "environment_fingerprint_sha256": authorization["environment_fingerprint_sha256"],
        "candidate_production_commit": package["candidate_production_commit"],
        "candidate_tree_sha256": package["candidate_tree_sha256"],
        "inference_input_sha256": package["inference_input_sha256"],
        "retriever_decision_identity": package["retriever_decision_identity"],
        "runtime_identity": package["runtime_identity"],
        "mid_run_resume_supported": False,
    }
    for key, wanted in consumption_expected.items():
        _require(consumption.get(key) == wanted, f"CONSUMPTION_BINDING_MISMATCH:{key}")
    _require(consumption["runtime_attestation_receipt_path"] == raw_manifest["runtime_attestation_receipt_path"], "CONSUMPTION_RAW_RUNTIME_PATH_MISMATCH")
    _require(consumption["runtime_attestation_receipt_sha256"] == raw_manifest["runtime_attestation_receipt_sha256"], "CONSUMPTION_RAW_RUNTIME_SHA_MISMATCH")
    _require(consumption["environment_fingerprint_sha256"] == runtime["environment_fingerprint_sha256"], "CONSUMPTION_RUNTIME_ENVIRONMENT_MISMATCH")


def _load_package(root: Path, package_path: Path) -> dict[str, Any]:
    package = read_json(package_path)
    _require(package.get("schema_version") == PACKAGE_SCHEMA, "EV3_PACKAGE_SCHEMA_INVALID")
    _require(package.get("status") == PACKAGE_STATUS, "EV3_PACKAGE_NOT_FROZEN")
    flags = package.get("lifecycle", {})
    _require(all(flags.get(key) is value for key, value in {
        "evaluation_package_frozen": True, "evaluator_frozen": True, "harness_frozen": True,
        "runtime_attested": False, "execution_authorized": False, "ev3_consumed": False,
        "ev3_executed": False,
    }.items()), "EV3_PACKAGE_LIFECYCLE_INVALID")
    return package


def verify_raw_before_gold(root: Path, raw_manifest_path: Path, package_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate raw-only execution material before opening any complete-Gold artifact."""
    package = _load_package(root, package_path)
    raw_manifest = read_json(raw_manifest_path)
    schema_path = resolve_from_root(root, package["paths"]["raw_manifest_schema"])
    schema = read_json(schema_path)
    _require(sha256(schema_path) == package["artifact_sha256"]["raw_manifest_schema"], "RAW_SCHEMA_IDENTITY_DRIFT")
    _require(set(raw_manifest) == set(schema["required_fields"]), "RAW_MANIFEST_SCHEMA_INVALID")
    _require(raw_manifest.get("schema_version") == schema["raw_manifest_schema_version"], "RAW_MANIFEST_VERSION_INVALID")
    _require(raw_manifest.get("rows") == 60 and raw_manifest.get("scoring_loaded") is False, "RAW_MANIFEST_LIFECYCLE_INVALID")
    _require(not (set(raw_manifest) & set(schema["gold_fields_forbidden"])), "GOLD_FIELD_IN_RAW_MANIFEST")
    _require(raw_manifest.get("execution_package_manifest_sha256") == sha256(package_path), "RAW_PACKAGE_BINDING_MISMATCH")
    for key in ("candidate_production_commit", "candidate_tree_sha256", "candidate_source_sha256", "inference_input_sha256", "evaluator_source_sha256", "e1_harness_sha256", "retriever_decision_identity", "runtime_identity"):
        _require(raw_manifest.get(key) == package.get(key), f"RAW_EXECUTION_BINDING_MISMATCH:{key}")
    runtime = _verify_runtime_attestation_binding(root, raw_manifest, package, sha256(package_path))
    _verify_authorization_and_consumption_binding(root, raw_manifest, package, runtime)
    raw_path = resolve_from_root(root, raw_manifest["raw_output_path"])
    _require(sha256(raw_path) == raw_manifest["raw_output_sha256"], "RAW_OUTPUT_SHA_MISMATCH")
    physical = raw_path.read_bytes().splitlines(keepends=True)
    _require(len(physical) == 60 and all(line.endswith(b"\n") for line in physical), "RAW_PHYSICAL_ROW_COUNT_OR_NEWLINE")
    _require([hashlib.sha256(line).hexdigest() for line in physical] == raw_manifest["raw_row_sha256"], "RAW_ROW_HASH_MISMATCH")
    try:
        rows = [json.loads(line) for line in physical]
    except json.JSONDecodeError as error:
        raise EvaluationIntegrityError("RAW_JSON_INVALID") from error
    inputs = read_jsonl(resolve_from_root(root, package["paths"]["inference_inputs"]))
    _require([row.get("query_id") for row in rows] == [row.get("case_id") for row in inputs], "RAW_QUERY_ID_ORDER_OR_UNIQUENESS")
    _require(raw_manifest.get("query_sha256_order") == [row.get("query_sha256") for row in inputs], "RAW_QUERY_HASH_ORDER_MISMATCH")
    return package, rows


def score_frozen(root: Path, raw_manifest_path: Path, package_path: Path, output: Path) -> dict[str, Any]:
    package, raw_rows = verify_raw_before_gold(root, raw_manifest_path, package_path)
    _verify_static_scorer_identities(root, package)
    complete_path = resolve_from_root(root, package["paths"]["complete_gold_manifest"])
    binding_path = resolve_from_root(root, package["paths"]["evaluator_binding_contract"])
    _require(sha256(complete_path) == package["artifact_sha256"]["complete_gold_manifest"], "COMPLETE_GOLD_MANIFEST_DRIFT")
    _require(sha256(binding_path) == package["artifact_sha256"]["evaluator_binding_contract"], "EVALUATOR_BINDING_CONTRACT_DRIFT")
    pass_a, pass_b, gold, manifest = load_complete_gold(root, complete_path, binding_path)
    mapping = load_mapping(resolve_from_root(root, package["paths"]["evaluator_mapping"]))
    reason = load_reason_compatibility(resolve_from_root(root, package["paths"]["reason_compatibility"]))
    referenced_codes = {code for row in gold for code in row["forbidden_claims_actions"]}
    safety = load_safety_rules_subset(resolve_from_root(root, package["paths"]["forbidden_action_rules"]), referenced_codes)
    gate = read_json(resolve_from_root(root, package["paths"]["product_gate_contract"]))
    as_of = date.fromisoformat(manifest["evaluation_as_of_date"])
    pass_a_by = {row["case_id"]: row for row in pass_a}
    gold_by = {row["case_id"]: row for row in gold}
    pass_b_by: dict[str, list[dict[str, Any]]] = {}
    for row in pass_b:
        pass_b_by.setdefault(row["case_id"], []).append(row)
    _require([row.get("query_id") for row in raw_rows] == [row["case_id"] for row in pass_a], "RAW_GOLD_ORDER_MISMATCH")
    def execute() -> list[dict[str, Any]]:
        return [evaluate_row(gold_by[row["query_id"]], pass_b_by[row["query_id"]], row, mapping, reason, safety, pass_a_by[row["query_id"]]["semantic_stratum"], as_of) for row in raw_rows]
    first, second = execute(), execute()
    reproducibility = stable_json_sha256(first) == stable_json_sha256(second)
    aggregate_result = aggregate(first, gate, "PASS" if reproducibility else "FAIL")
    result = {
        "schema_version": SCORE_SCHEMA, "final_result": aggregate_result["gate_decision"]["verdict"],
        "rows": first, "aggregate": aggregate_result,
        "semantic_stratum_distribution": dict(sorted(Counter(row["semantic_stratum"] for row in pass_a).items())),
        "raw_manifest_sha256": sha256(raw_manifest_path), "execution_package_manifest_sha256": sha256(package_path),
        "scorer_reproduction_sha256": stable_json_sha256(first),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("score",))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--raw-manifest", type=Path, required=True)
    parser.add_argument("--execution-package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        result = score_frozen(root, resolve_from_root(root, args.raw_manifest), resolve_from_root(root, args.execution_package), resolve_from_root(root, args.output))
    except (EvaluationIntegrityError, KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as error:
        print(f"EV3_R1_INVALID:{error}", file=sys.stderr)
        return 2
    return 2 if result["final_result"] == "INVALID" else 0


if __name__ == "__main__":
    raise SystemExit(main())
