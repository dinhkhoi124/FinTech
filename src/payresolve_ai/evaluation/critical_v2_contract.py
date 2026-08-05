"""Fail-closed validation for the Senior-approved W3-002-CR1 amendment.

This module validates contract and preservation evidence only. It intentionally
does not import candidate evaluation, retrieval, generation, or model code.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class ContractValidationError(RuntimeError):
    """Raised when Option A contract evidence is inconsistent."""


DECISION_BUNDLE_SHA256 = "bc7317000005859f2e4b215cf0c4f687e5e284a4a004270d81f9f5abd0074786"
REVISION_MANIFEST_HASHES = {
    2: "668992392f3e0f4addeb017a0028f6bc676614910d0e1c03fb8f3e3c51a20834",
    3: "650a8a5847d83211c96941e549bc4379df89e1ae91c857a59c65160a6ed0f688",
    4: "b2b021c78f11ff4cf5d023044b464b43d806f0c0217fd8e3b196dfc736bb52af",
}
SAFE_CORRECTIVE_IDS = {
    "Q_V4_N_ID01", "Q_V4_N_ID02", "Q_V4_N_ID03", "Q_V4_N_ID04",
    "Q_V4_N_AM01", "Q_V4_N_AM02", "Q_V4_N_AM03",
    "Q_V4_N_DR01", "Q_V4_N_DR02", "Q_V4_N_DR03",
    "Q_V4_N_EX01", "Q_V4_N_EX02", "Q_V4_N_EX03",
    "Q_V4_N_IN01", "Q_V4_N_IN02",
}
ABSTAIN_IDS = {"Q_V4_N_CF01", "Q_V4_N_CF02", "Q_V4_N_OS01", "Q_V4_N_AB01", "Q_V4_N_AB02"}
OUTCOMES = {
    "SAFE_STANDARD_ANSWER", "SAFE_CORRECTIVE_ANSWER", "SAFE_ABSTAIN_ESCALATE",
    "WRONG_ABSTAIN_ON_STANDARD", "WRONG_ABSTAIN_ON_SAFE_CORRECTIVE",
    "WRONG_OR_INCOMPLETE_STANDARD_ANSWER", "WRONG_OR_INCOMPLETE_CORRECTIVE_ANSWER",
    "UNSAFE_PROHIBITED_REQUEST_COMPLIANCE", "UNSUPPORTED_OR_WRONG_EVIDENCE_ANSWER",
    "FORBIDDEN_EVIDENCE_USAGE", "SYSTEM_ERROR",
}
CASE_DENOMINATORS = {
    "standard_answer_success_rate": 40,
    "safe_corrective_success_rate": 15,
    "true_abstain_success_rate": 5,
    "overall_safe_resolution_rate": 60,
    "unsafe_answer_rate": 60,
    "prohibited_request_compliance_rate": 15,
    "wrong_abstain_rate_on_answerable_cases": 55,
    "draft_expired_future_effective_usage_rate": 60,
    "result_counts_by_response_type_and_answer_subtype": 60,
}
HARD_NEGATIVE_PAIRS = {
    ("Q_V2_A_TRP02", "FAQ_TRANSFER_RECIPIENT_002#current_window"),
    ("Q_V2_A_TRR02", "POL_TRANSFER_PENDING_002#current_window"),
    ("Q_V2_A_CAR02", "POL_CARD_PENDING_001#review_window"),
    ("Q_V2_A_CAP02", "POL_CARD_REVERT_002#return_window"),
    ("Q_V2_A_TRF02", "POL_TRANSFER_DECLINED_001#review_rule"),
}


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractValidationError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractValidationError(f"expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ContractValidationError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("artifact_type") != "CONTRACT_AMENDMENT_ONLY":
        raise ContractValidationError("artifact must be contract-only")
    if contract.get("senior_verdict") != "APPROVE_CONTRACT_AMENDMENT — OPTION A":
        raise ContractValidationError("Senior verdict mismatch")
    if contract.get("senior_contract_amendment_approved") is not True:
        raise ContractValidationError("contract amendment is not recorded as approved")
    if contract.get("contract_amendment_option") != "OPTION_A":
        raise ContractValidationError("only Option A is approved")
    decision = contract.get("contract_decision_bundle", {})
    if decision.get("sha256") != DECISION_BUNDLE_SHA256:
        raise ContractValidationError("decision bundle SHA mismatch")
    if (decision.get("inventoried_payload_files"), decision.get("detached_inventory_files"), decision.get("zip_entries")) != (67, 1, 68):
        raise ContractValidationError("decision bundle entry counts must be 67 + 1 = 68")
    taxonomy = contract.get("response_taxonomy", {})
    if taxonomy.get("response_types") != ["ANSWER", "ABSTAIN_ESCALATE"]:
        raise ContractValidationError("top-level response taxonomy mismatch")
    if taxonomy.get("answer_subtypes") != ["STANDARD", "SAFE_CORRECTIVE"]:
        raise ContractValidationError("answer subtype taxonomy mismatch")
    if taxonomy.get("ask_clarification_top_level_enabled") is not False:
        raise ContractValidationError("ASK_CLARIFICATION cannot be introduced at P0")
    distribution = contract.get("distribution", {})
    expected = {"ANSWER/STANDARD": 40, "ANSWER/SAFE_CORRECTIVE": 15, "ABSTAIN_ESCALATE": 5, "total": 60, "answerable_total": 55, "safety_challenge_total": 20}
    if distribution != expected:
        raise ContractValidationError("distribution must be exact 40/15/5")
    if set(contract.get("safe_corrective_ids", [])) != SAFE_CORRECTIVE_IDS:
        raise ContractValidationError("SAFE_CORRECTIVE ID set mismatch")
    if set(contract.get("abstain_escalate_ids", [])) != ABSTAIN_IDS:
        raise ContractValidationError("ABSTAIN_ESCALATE ID set mismatch")
    if len(contract.get("safe_corrective_success_requirements", [])) != 7:
        raise ContractValidationError("SAFE_CORRECTIVE must retain all seven success requirements")
    planes = contract.get("claim_planes", {})
    if planes.get("control_plane", {}).get("requires_literal_kb_nonexistence_statement") is not False:
        raise ContractValidationError("control-plane claims cannot require a literal KB nonexistence statement")
    if set(contract.get("outcome_classes", [])) != OUTCOMES:
        raise ContractValidationError("outcome class contract mismatch")
    metric_map = {item.get("name"): item.get("denominator") for item in contract.get("metrics", [])}
    for name, denominator in CASE_DENOMINATORS.items():
        if metric_map.get(name) != denominator:
            raise ContractValidationError(f"metric denominator mismatch: {name}")
    if metric_map.get("citation_correctness", "missing") is not None or metric_map.get("unsupported_claim_rate", "missing") is not None:
        raise ContractValidationError("dynamic metric denominators must remain output/claim based")
    invariants = contract.get("variant_invariants", {})
    if invariants.get("selected_retriever") != "R0" or invariants.get("r1_hard_filter") is not False:
        raise ContractValidationError("retriever isolation mismatch")
    if invariants.get("answer_subtype_is_tuning_signal") is not False:
        raise ContractValidationError("answer_subtype cannot be a tuning signal")
    lifecycle = contract.get("lifecycle", {})
    required_false = ("candidate_revision_5_created", "senior_semantic_review_approved", "evaluation_authorized", "critical_evaluated")
    if any(lifecycle.get(key) is not False for key in required_false):
        raise ContractValidationError("contract approval cannot advance candidate/evaluation lifecycle")
    if lifecycle.get("model_verdict") != "NOT_ESTABLISHED":
        raise ContractValidationError("model verdict must remain NOT_ESTABLISHED")


def validate_metric_spec(spec: dict[str, Any]) -> None:
    if set(spec.get("outcome_classes", [])) != OUTCOMES:
        raise ContractValidationError("metric spec outcome classes mismatch")
    if spec.get("case_metrics") != CASE_DENOMINATORS:
        raise ContractValidationError("metric spec denominators mismatch")
    if spec.get("dynamic_metrics") != {"citation_correctness": "answered_outputs", "unsupported_claim_rate": "claims"}:
        raise ContractValidationError("dynamic metric units mismatch")
    if spec.get("evaluation_authorized") is not False:
        raise ContractValidationError("metric specification cannot authorize evaluation")


def validate_revision_5_checklist(checklist: dict[str, Any]) -> None:
    if checklist.get("artifact_type") != "FUTURE_ACCEPTANCE_CHECKLIST_ONLY" or checklist.get("candidate_revision_5_created") is not False:
        raise ContractValidationError("revision-5 checklist must not create a candidate")
    pass_b = checklist.get("pass_b", {})
    required_fields = {
        "reviewer_status", "reviewer_method", "candidate_revision", "review_input_sha256",
        "support_class", "reason_code", "supported_requested_obligation_ids",
        "supported_corrective_obligation_ids", "rationale",
    }
    if pass_b.get("required_rows") != 3120 or set(pass_b.get("required_fields", [])) != required_fields:
        raise ContractValidationError("Pass B acceptance schema mismatch")
    corrections = {(item.get("query_id"), item.get("evidence_id")) for item in checklist.get("positive_support_corrections", [])}
    expected_corrections = {
        ("Q_V2_A_TRD04", "RUN_TRANSFER_DECLINED_001#action"),
        ("Q_V2_A_TRR04", "FAQ_TRANSFER_RECIPIENT_002#current_window"),
        ("Q_V2_A_TRR04", "POL_TRANSFER_RECIPIENT_001#trace_window"),
    }
    if corrections != expected_corrections:
        raise ContractValidationError("positive-support checklist mismatch")
    if {item.get("query_id") for item in checklist.get("corrective_cover_wording", [])} != {"Q_V4_N_EX01", "Q_V4_N_ID04"}:
        raise ContractValidationError("corrective-cover wording checklist mismatch")
    if {tuple(pair) for pair in checklist.get("hard_negative_proposals", [])} != HARD_NEGATIVE_PAIRS:
        raise ContractValidationError("hard-negative proposal set mismatch")
    if checklist.get("hard_negative_failure_action") != "STOP_AND_REQUEST_SENIOR_REVIEW_WITH_NO_SUBSTITUTION":
        raise ContractValidationError("hard-negative failure action mismatch")
    if checklist.get("senior_semantic_review_approved") is not False or checklist.get("evaluation_authorized") is not False:
        raise ContractValidationError("checklist cannot imply semantic/evaluation approval")


def validate_decision_bundle(path: Path) -> None:
    if sha256(path) != DECISION_BUNDLE_SHA256:
        raise ContractValidationError("approved decision bundle bytes changed")


def _validate_hash_mapping(root: Path, mapping: dict[str, str]) -> int:
    for relative, expected in mapping.items():
        if sha256(root / relative) != expected:
            raise ContractValidationError(f"preserved artifact changed: {relative}")
    return len(mapping)


def validate_rejected_revisions(root: Path) -> dict[int, int]:
    results = root / "reports/week_03/results"
    rev2 = _json(results / "critical_eval_v2_revision_2_rejected_inventory.json")
    rev3 = _json(results / "critical_eval_v2_revision_3_rejected_inventory.json")
    rev4 = _json(results / "critical_eval_v2_revision_4_rejected_inventory.json")
    counts = {2: _validate_hash_mapping(root, rev2.get("artifact_sha256", {}))}
    counts[3] = _validate_hash_mapping(root, {item["path"]: item["sha256"] for item in rev3.get("artifacts", [])})
    rev4_root = root / "reports/week_03/rejected/critical_eval_v2_revision_4"
    counts[4] = _validate_hash_mapping(rev4_root, {item["path"]: item["sha256"] for item in rev4.get("artifacts", [])})
    recorded = {
        2: rev2.get("revision_2_manifest_sha256"),
        3: rev3.get("manifest_sha256"),
        4: rev4.get("revision_4_manifest_sha256"),
    }
    if recorded != REVISION_MANIFEST_HASHES or counts != {2: 17, 3: 18, 4: 19}:
        raise ContractValidationError("rejected revision inventory metadata mismatch")
    return counts


def validate_historical_artifacts(root: Path) -> int:
    expected = _json(root / "reports/week_03/results/critical_eval_v2_historical_hash_verification.json")
    count = _validate_hash_mapping(root, expected)
    if count != 18:
        raise ContractValidationError("historical W3-002 inventory must contain 18 files")
    return count


def validate_contract_package(root: Path, decision_bundle: Path | None = None) -> dict[str, Any]:
    contract = _json(root / "configs/evaluation/critical_eval_v2_contract_option_a.json")
    metric_spec = _json(root / "reports/week_03/results/critical_eval_v2_contract_metric_spec.json")
    checklist = _json(root / "reports/week_03/results/critical_eval_v2_revision_5_acceptance_checklist.json")
    validate_contract(contract)
    validate_metric_spec(metric_spec)
    validate_revision_5_checklist(checklist)
    if decision_bundle is not None:
        validate_decision_bundle(decision_bundle)
    revision_counts = validate_rejected_revisions(root)
    historical_count = validate_historical_artifacts(root)
    return {
        "status": "PASS",
        "distribution": "40_STANDARD_15_SAFE_CORRECTIVE_5_ABSTAIN",
        "decision_bundle_sha256": DECISION_BUNDLE_SHA256,
        "rejected_revision_file_counts": {str(key): value for key, value in revision_counts.items()},
        "historical_hash_count": historical_count,
        "candidate_revision_5_created": False,
        "senior_semantic_review_approved": False,
        "evaluation_authorized": False,
        "critical_evaluated": False,
    }
