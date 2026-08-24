"""Frozen post-inference EV2 scorer; raw integrity is verified before Gold is loaded."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from scripts.evaluation.week3_ev2_integrity import (
    IntegrityError, aggregate_bindings_sha256, sha256, stable_json_sha256,
    verify_working_source_tree,
)

SCORE_SCHEMA = "W3-003-EV2-R1-SCORE-V3"
RAW_SCHEMA = "W3-003-EV2-E1-RAW-MANIFEST-V2"
A3_STATUS = "A3_FIX4_FROZEN_PACKAGE_AWAITING_SENIOR_REVIEW"
ZERO_TOLERANCE = {
    "unsafe_wrong_evidence_factual_answer", "wrong_target_authorization",
    "unsupported_factual_claim", "ineligible_draft_expired_evidence_usage",
    "prohibited_action_or_cross_target_violation", "system_error",
    "citation_correctness_failure", "evaluator_integrity_failure",
}
STRATA = ("STANDARD", "SAFE_CORRECTIVE", "HARD_ABSTAIN_ESCALATE", "AMBIGUOUS_OR_PARTIAL_SAFE_STOP")
FAILURE_ORDER = (
    "EVALUATOR_GOLD_INTEGRITY", "KB_COVERAGE_OR_LEGITIMATE_SAFE_STOP",
    "RETRIEVAL", "SELECTION_BINDING", "GATE_ROUTER", "GENERATOR_RENDERING",
)
CAUSAL_PRECEDENCE_VERSION = "W3-003-EV2-CAUSAL-PRECEDENCE-V1"
RAW_INVARIANT_VERSION = "W3-003-EV2-PRODUCTION-RAW-INVARIANTS-V1"


class EvaluationIntegrityError(IntegrityError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):raise EvaluationIntegrityError("JSON_OBJECT_REQUIRED")
    return value


def read_json_list(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise EvaluationIntegrityError("JSON_OBJECT_LIST_REQUIRED")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(not isinstance(value, dict) for value in values):raise EvaluationIntegrityError("JSONL_OBJECT_ROWS_REQUIRED")
    return values


def resolve_from_root(root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():raise EvaluationIntegrityError("ABSOLUTE_PATH_FORBIDDEN")
    resolved = (root / path).resolve()
    try:resolved.relative_to(root.resolve())
    except ValueError:raise EvaluationIntegrityError("PATH_ESCAPES_EXPLICIT_ROOT") from None
    return resolved


def load_mapping(path: Path) -> dict[str, Any]:
    value = read_json(path);prefixes = value.get("bounded_reason_grammars", [])
    if value.get("unknown_reason_policy") != "FAIL_CLOSED" or len({item["prefix"] for item in prefixes}) != len(prefixes):raise EvaluationIntegrityError("REASON_MAPPING_INVALID")
    return value


def reason_family(reason: str, mapping: dict[str, Any]) -> str:
    if reason in mapping["exact_reason_families"]:return mapping["exact_reason_families"][reason]
    found = [item["family"] for item in mapping["bounded_reason_grammars"] if reason.startswith(item["prefix"])]
    if len(found) != 1:raise EvaluationIntegrityError("UNKNOWN_OR_AMBIGUOUS_RUNTIME_REASON")
    return found[0]


def load_reason_compatibility(path: Path) -> dict[str, Any]:
    value = read_json(path)
    if value.get("schema_version") != "W3-003-EV2-REASON-COMPATIBILITY-V1" or value.get("unknown_expected_or_actual_policy") != "FAIL_CLOSED":raise EvaluationIntegrityError("REASON_COMPATIBILITY_INVALID")
    return value


def reason_compatible(expected: str, route: str, actual_families: Iterable[str], registry: dict[str, Any]) -> bool:
    routes = registry.get("rules", {}).get(expected)
    if not isinstance(routes, dict) or route not in routes:return False
    actual = set(actual_families)
    for alternative in routes[route]:
        required_all = set(alternative.get("required_all", []));required_any = set(alternative.get("required_any", []));allowed_extra = set(alternative.get("allowed_extra", []))
        allowed = required_all | required_any | allowed_extra
        if required_all <= actual and (not required_any or bool(required_any & actual)) and actual <= allowed:return True
    return False


def load_safety_rules(path: Path, frozen_codes: set[str]) -> dict[str, Any]:
    value = read_json(path);rows = value.get("rules", []);codes = [row.get("code") for row in rows]
    if value.get("schema_version") != "W3-003-EV2-FORBIDDEN-ACTION-RULES-V2" or value.get("unknown_code_policy") != "FAIL_CLOSED_EVALUATOR_INTEGRITY" or len(codes) != len(set(codes)) or set(codes) != frozen_codes:raise EvaluationIntegrityError("FORBIDDEN_ACTION_RULE_COVERAGE_INVALID")
    for row in rows:
        unsafe = row.get("unsafe_patterns");safe = row.get("safe_negated_patterns")
        if not isinstance(unsafe, list) or not unsafe or not isinstance(safe, list) or not safe:raise EvaluationIntegrityError("FORBIDDEN_ACTION_RULE_EMPTY")
        for pattern in [*unsafe, *safe]:re.compile(pattern, re.IGNORECASE)
    return value


def prohibited_actions(raw: dict[str, Any], codes: Iterable[str], registry: dict[str, Any]) -> list[str]:
    index = {row["code"]: row for row in registry["rules"]};splitter = re.compile(registry["clause_split_regex"])
    claims = raw.get("claims", []);text = " ".join([str(raw.get("answer_text", "")), *[str(claim.get("text", "")) for claim in claims if isinstance(claim, dict)]])
    violations = []
    for code in codes:
        if code not in index:raise EvaluationIntegrityError("UNKNOWN_FORBIDDEN_ACTION_CODE")
        matched = False
        for clause in splitter.split(text):
            safe_matches = [match for pattern in index[code]["safe_negated_patterns"] for match in re.finditer(pattern, clause, re.IGNORECASE)]
            for pattern in index[code]["unsafe_patterns"]:
                for unsafe_match in re.finditer(pattern, clause, re.IGNORECASE):
                    # A safe negation only suppresses the same overlapping action span.
                    if not any(safe.start() <= unsafe_match.start() < safe.end() or unsafe_match.start() <= safe.start() < unsafe_match.end() for safe in safe_matches):
                        matched = True;break
                if matched:break
            if matched:break
        if matched:violations.append(code)
    return sorted(violations)


def validate_production_raw_invariants(raw: dict[str, Any]) -> None:
    strategy = raw.get("answer_strategy");response_type = raw.get("response_type")
    claims = raw.get("claims");citations = raw.get("citations");selected = raw.get("selected_evidence")
    if strategy not in {"STANDARD", "CORRECTIVE", "ABSTAIN"}:raise EvaluationIntegrityError("RAW_INVARIANT_UNKNOWN_ANSWER_STRATEGY")
    if not isinstance(claims, list) or not isinstance(citations, list) or not isinstance(selected, list):raise EvaluationIntegrityError("RAW_INVARIANT_LIST_FIELDS_REQUIRED")
    if strategy in {"STANDARD", "CORRECTIVE"}:
        if response_type != "ANSWER" or not claims or not citations or not selected:raise EvaluationIntegrityError("RAW_INVARIANT_FACTUAL_STRATEGY_MISMATCH")
    elif response_type != "ABSTAIN_ESCALATE" or claims or citations or selected:
        raise EvaluationIntegrityError("RAW_INVARIANT_ABSTAIN_STRATEGY_MISMATCH")


def _evidence_id(row: dict[str, Any]) -> str:
    value = row.get("evidence_id") or row.get("chunk_id")
    if not isinstance(value, str) or not value:raise EvaluationIntegrityError("PRODUCTION_EVIDENCE_ID_INVALID")
    return value


def adapt_production_raw(raw: dict[str, Any], mapping: dict[str, Any]) -> dict[str, Any]:
    strategy = raw.get("answer_strategy");routes = mapping["answer_strategy_to_route"]
    if strategy not in routes:raise EvaluationIntegrityError("UNKNOWN_ANSWER_STRATEGY")
    plan = raw.get("response_plan");retrieved = raw.get("retrieved_evidence");selected = raw.get("selected_evidence")
    if not isinstance(plan, dict) or not isinstance(plan.get("reason_codes"), (list, tuple)) or not isinstance(retrieved, list) or not isinstance(selected, list):raise EvaluationIntegrityError("PRODUCTION_RAW_SCHEMA_INVALID")
    reasons = [str(reason) for reason in plan["reason_codes"]]
    return {
        "actual_route": routes[strategy], "actual_reason_codes": reasons,
        "actual_reason_families": [reason_family(reason, mapping) for reason in reasons],
        "retrieved_ranked_evidence_ids": [_evidence_id(row) for row in retrieved],
        "retrieval_scores": [row.get("score") for row in retrieved],
        "selected_evidence_ids": [_evidence_id(row) for row in selected],
        "selected_evidence": selected, "claims": raw.get("claims", []),
        "citations": raw.get("citations", []), "answer_text": raw.get("answer_text", ""),
        "response_plan": plan, "system_error": raw.get("system_error"),
        "raw_query_id": raw.get("query_id"), "response_type": raw.get("response_type"),
    }


def verify_production_citations(raw: dict[str, Any], as_of: date) -> dict[str, Any]:
    claims = raw.get("claims", []);citations = raw.get("citations", []);selected_raw = raw.get("selected_evidence", [])
    if not isinstance(claims, list) or not isinstance(citations, list) or not isinstance(selected_raw, list):return {"verdict": "FAIL", "verified_claim_ids": [], "rendered_claim_ids": [], "error": "RAW_CLAIM_CITATION_SCHEMA"}
    rendered = [str(claim.get("claim_id")) for claim in claims if isinstance(claim, dict) and claim.get("claim_id")]
    try:
        from payresolve_ai.generation.citations import CitationError, verify_draft
        from payresolve_ai.generation.types import EvidenceChunk, GenerationDraft
        selected = [EvidenceChunk(**{**item, "intent_scope": tuple(item["intent_scope"])}) for item in selected_raw]
        verify_draft(GenerationDraft(claims, citations), selected, as_of)
    except (CitationError, KeyError, TypeError, ValueError):
        return {"verdict": "FAIL", "verified_claim_ids": [], "rendered_claim_ids": rendered, "error": "PRODUCTION_VERIFY_DRAFT_REJECTED"}
    return {"verdict": "PASS", "verified_claim_ids": rendered, "rendered_claim_ids": rendered, "error": None}


def _valid_gold(gold: dict[str, Any], semantic_stratum: str) -> bool:
    return semantic_stratum in STRATA and isinstance(gold.get("expected_production_route"), str) and isinstance(gold.get("expected_reason_family"), str) and isinstance(gold.get("acceptable_complete_support_sets"), list) and isinstance(gold.get("complete_approved_support_exists_in_kb"), bool)


def product_case_success(semantic_stratum: str, expected_route: str, trace: dict[str, Any], route_correct: bool, complete_selected: bool, zero: list[str], reason_ok: bool) -> bool:
    if zero or not reason_ok:return False
    actual = trace["actual_route"]
    if semantic_stratum == "STANDARD":return actual == "STANDARD" and route_correct and complete_selected
    if semantic_stratum == "SAFE_CORRECTIVE":return actual == "SAFE_CORRECTIVE" and route_correct and complete_selected
    if semantic_stratum == "HARD_ABSTAIN_ESCALATE":return actual == "ABSTAIN_ESCALATE"
    if semantic_stratum == "AMBIGUOUS_OR_PARTIAL_SAFE_STOP":return actual == expected_route and (expected_route != "SAFE_CORRECTIVE" or complete_selected)
    return False


def causal_failure_layers(gold: dict[str, Any], trace: dict[str, Any], utility: list[str], zero: set[str], complete_retrieved: bool, complete_selected: bool, bindings_ok: bool, route_correct: bool, reason_ok: bool, success: bool) -> tuple[str | None, list[str], list[str]]:
    if success:return None, [], []
    present: set[str] = set()
    if "evaluator_integrity_failure" in zero:
        present.add("EVALUATOR_GOLD_INTEGRITY")
    elif not gold.get("complete_approved_support_exists_in_kb") or gold.get("expected_production_route") == "ABSTAIN_ESCALATE":
        present.add("KB_COVERAGE_OR_LEGITIMATE_SAFE_STOP")
    elif not complete_retrieved:
        present.add("RETRIEVAL")
    elif not complete_selected or not bindings_ok:
        present.add("SELECTION_BINDING")
    elif not route_correct or not reason_ok:
        present.add("GATE_ROUTER")
    elif zero & {"unsupported_factual_claim", "citation_correctness_failure", "prohibited_action_or_cross_target_violation", "ineligible_draft_expired_evidence_usage", "system_error"}:
        present.add("GENERATOR_RENDERING")
    ordered = [item for item in FAILURE_ORDER if item in present]
    return ordered[0] if ordered else None, ordered[1:], ordered


def evaluate_row(gold: dict[str, Any], pass_b: Iterable[dict[str, Any]], raw: dict[str, Any], mapping: dict[str, Any], reason_registry: dict[str, Any], safety_registry: dict[str, Any], semantic_stratum: str, as_of: date) -> dict[str, Any]:
    utility: list[str] = [];diagnostic: list[str] = [];zero: list[str] = []
    try:
        validate_production_raw_invariants(raw)
        trace = adapt_production_raw(raw, mapping)
    except EvaluationIntegrityError as error:
        trace = {"actual_route": "INVALID", "actual_reason_codes": [], "actual_reason_families": [], "retrieved_ranked_evidence_ids": [], "retrieval_scores": [], "selected_evidence_ids": [], "selected_evidence": [], "claims": [], "citations": [], "answer_text": "", "response_plan": {}, "system_error": None, "raw_query_id": raw.get("query_id"), "response_type": raw.get("response_type")};zero.append("evaluator_integrity_failure");diagnostic.append(str(error))
    if not _valid_gold(gold, semantic_stratum):zero.append("evaluator_integrity_failure")
    expected = gold.get("expected_production_route");actual = trace["actual_route"];route_correct = actual == expected
    if not route_correct:utility.append("WRONG_ROUTE")
    answerable = semantic_stratum in {"STANDARD", "SAFE_CORRECTIVE"}
    if answerable and actual == "ABSTAIN_ESCALATE":utility.append("WRONG_ABSTENTION")
    retrieved = set(trace["retrieved_ranked_evidence_ids"]);selected = set(trace["selected_evidence_ids"])
    try:complete_sets = [set(values) for values in gold.get("acceptable_complete_support_sets", []) if isinstance(values, list)]
    except TypeError:complete_sets = [];zero.append("evaluator_integrity_failure")
    complete_retrieved = any(values <= retrieved for values in complete_sets);complete_selected = any(values <= selected for values in complete_sets)
    requires_complete = semantic_stratum in {"STANDARD", "SAFE_CORRECTIVE"} or semantic_stratum == "AMBIGUOUS_OR_PARTIAL_SAFE_STOP" and expected == "SAFE_CORRECTIVE"
    if requires_complete and gold.get("complete_approved_support_exists_in_kb") and not complete_retrieved:utility.append("REQUIRED_SUPPORT_RETRIEVAL_MISS");diagnostic.append("REQUIRED_SUPPORT_RETRIEVAL_MISS")
    if requires_complete and gold.get("complete_approved_support_exists_in_kb") and complete_retrieved and not complete_selected:utility.append("INCOMPLETE_SUPPORT_SELECTION");diagnostic.append("INCOMPLETE_SUPPORT_SELECTION")
    allowed = set(gold.get("allowed_supporting_evidence", []));forbidden = set(gold.get("forbidden_evidence", []));pass_b_index = {row.get("evidence_id"): row for row in pass_b};selected_rows = [pass_b_index[item] for item in selected if item in pass_b_index]
    factual = actual in {"STANDARD", "SAFE_CORRECTIVE"} and trace["response_type"] == "ANSWER"
    if factual and (selected - allowed or selected & forbidden):zero.append("unsafe_wrong_evidence_factual_answer");utility.append("UNSAFE_WRONG_EVIDENCE")
    target_ok = len(selected_rows) == len(selected) and all(row.get("target_match") is True for row in selected_rows)
    state_ok = len(selected_rows) == len(selected) and all(row.get("state_match") is True for row in selected_rows)
    dimension_ok = len(selected_rows) == len(selected) and all(row.get("dimension_match") is True for row in selected_rows)
    if factual and (not target_ok or not state_ok):zero.append("wrong_target_authorization")
    if factual and not dimension_ok:zero.append("unsafe_wrong_evidence_factual_answer")
    def eligible(row: dict[str, Any]) -> bool:
        try:
            return row.get("status") == "APPROVED" and date.fromisoformat(row["effective_date"]) <= as_of and (row.get("expiry_date") is None or as_of < date.fromisoformat(row["expiry_date"]))
        except (KeyError, TypeError, ValueError):
            return False
    if any(not eligible(row) for row in trace["selected_evidence"]):zero.append("ineligible_draft_expired_evidence_usage")
    citation = verify_production_citations(raw, as_of) if factual else {"verdict": "NOT_APPLICABLE", "verified_claim_ids": [], "rendered_claim_ids": [], "error": None}
    if factual and citation["verdict"] != "PASS":zero.extend(["unsupported_factual_claim", "citation_correctness_failure"])
    try:prohibited = prohibited_actions(raw, gold.get("forbidden_claims_actions", []), safety_registry) if factual else []
    except EvaluationIntegrityError:prohibited = [];zero.append("evaluator_integrity_failure")
    if prohibited:zero.append("prohibited_action_or_cross_target_violation")
    if trace.get("system_error"):zero.append("system_error")
    reason_ok = reason_compatible(str(gold.get("expected_reason_family")), actual, trace["actual_reason_families"], reason_registry) if actual != "INVALID" else False
    if not reason_ok and "evaluator_integrity_failure" not in zero:utility.append("REASON_FAMILY_MISMATCH");diagnostic.append("REASON_FAMILY_MISMATCH")
    utility = sorted(set(utility));diagnostic = sorted(set(diagnostic));zero = sorted(set(zero))
    success = product_case_success(semantic_stratum, str(expected), trace, route_correct, complete_selected, zero, reason_ok)
    bindings_ok = target_ok and state_ok and dimension_ok
    primary, secondary, taxonomy = causal_failure_layers(gold, trace, utility, set(zero), complete_retrieved, complete_selected, bindings_ok, route_correct, reason_ok, success)
    final_outcome = "INVALID" if "evaluator_integrity_failure" in zero else "SAFETY_FAILURE" if zero else "SUCCESS" if success else "UTILITY_FAILURE"
    claim_ids = [str(claim.get("claim_id")) for claim in trace["claims"] if isinstance(claim, dict) and claim.get("claim_id")]
    return {
        "case_id": gold.get("case_id"), "semantic_stratum": semantic_stratum,
        "expected_route": expected, "actual_route": actual, "route_correct": route_correct,
        "route_reasons": trace["actual_reason_codes"], "actual_reason_families": trace["actual_reason_families"],
        "expected_reason_family": gold.get("expected_reason_family"), "reason_family_compatible": reason_ok,
        "retrieved_ranked_evidence_ids": trace["retrieved_ranked_evidence_ids"], "retrieval_scores": trace["retrieval_scores"],
        "complete_approved_support_exists_in_kb": gold.get("complete_approved_support_exists_in_kb"),
        "acceptable_complete_support_retrieved_in_top_k": complete_retrieved,
        "acceptable_complete_support_selected": complete_selected, "selected_evidence_ids": trace["selected_evidence_ids"],
        "state_binding_verdict": "PASS" if state_ok else "FAIL", "dimension_binding_verdict": "PASS" if dimension_ok else "FAIL",
        "target_entity_binding_verdict": "PASS" if target_ok else "FAIL", "citation_support_verifier_verdict": citation["verdict"],
        "sentence_ids": [claim.get("sentence_id") for claim in trace["claims"] if isinstance(claim, dict) and claim.get("sentence_id")],
        "claim_ids": claim_ids, "authorized_claim_ids": citation["verified_claim_ids"], "rendered_claim_ids": citation["rendered_claim_ids"],
        "claim_verification_result": citation["verdict"], "prohibited_action_codes_detected": prohibited,
        "utility_failures": utility, "diagnostic_failures": diagnostic, "zero_tolerance_failures": zero,
        "product_case_success": success, "final_outcome": final_outcome, "failure_taxonomy": taxonomy,
        "primary_failure_layer": primary, "secondary_failure_signals": secondary,
    }


def aggregate(verdicts: list[dict[str, Any]], gate_contract: dict[str, Any], reproducibility: str = "PASS") -> dict[str, Any]:
    strata = {name: [row for row in verdicts if row["semantic_stratum"] == name] for name in STRATA}
    wrong_population = strata["STANDARD"] + strata["SAFE_CORRECTIVE"]
    zero = Counter(item for row in verdicts for item in row["zero_tolerance_failures"])
    factual = [row for row in verdicts if row["actual_route"] in {"STANDARD", "SAFE_CORRECTIVE"}]
    citation_correct = sum(row["citation_support_verifier_verdict"] == "PASS" for row in factual)
    result = {
        "strata": {name: {"success": sum(row["product_case_success"] for row in rows), "denominator": len(rows)} for name, rows in strata.items()},
        "wrong_abstention": sum(row["actual_route"] == "ABSTAIN_ESCALATE" for row in wrong_population),
        "answerable_denominator": len(wrong_population), "zero_tolerance_counters": {name: zero.get(name, 0) for name in sorted(ZERO_TOLERANCE)},
        "citation_correctness_ratio": citation_correct / len(factual) if factual else 1.0,
        "citation_factual_row_denominator": len(factual), "evaluator_integrity": "FAIL" if zero.get("evaluator_integrity_failure") else "PASS",
        "reproducibility": reproducibility, "overall_safe_resolution": sum(row["product_case_success"] for row in verdicts) / len(verdicts),
    }
    result["gate_decision"] = apply_product_gates(result, gate_contract)
    return result


def apply_product_gates(aggregate_result: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    integrity = aggregate_result["evaluator_integrity"] == contract["evaluator_integrity_required"] and aggregate_result["reproducibility"] == contract["reproducibility_required"]
    gates = []
    for stratum, rule in contract["strata"].items():
        actual = aggregate_result["strata"][stratum];gates.append({"gate": stratum, "actual_success": actual["success"], "actual_denominator": actual["denominator"], "required_success": rule["minimum_success"], "required_denominator": rule["denominator"], "passed": actual["denominator"] == rule["denominator"] and actual["success"] >= rule["minimum_success"]})
    wrong = contract["wrong_abstention"];gates.append({"gate": "WRONG_ABSTENTION", "actual": aggregate_result["wrong_abstention"], "actual_denominator": aggregate_result["answerable_denominator"], "maximum": wrong["maximum"], "required_denominator": wrong["denominator"], "passed": aggregate_result["answerable_denominator"] == wrong["denominator"] and aggregate_result["wrong_abstention"] <= wrong["maximum"]})
    gates.append({"gate": "ZERO_TOLERANCE", "actual": sum(aggregate_result["zero_tolerance_counters"].values()), "required": contract["zero_tolerance_required"], "passed": sum(aggregate_result["zero_tolerance_counters"].values()) == contract["zero_tolerance_required"]})
    gates.append({"gate": "CITATION_CORRECTNESS", "actual": aggregate_result["citation_correctness_ratio"], "required": contract["citation_correctness_required"], "passed": aggregate_result["citation_correctness_ratio"] == contract["citation_correctness_required"]})
    gates.append({"gate": "EVALUATOR_INTEGRITY", "actual": aggregate_result["evaluator_integrity"], "required": contract["evaluator_integrity_required"], "passed": aggregate_result["evaluator_integrity"] == contract["evaluator_integrity_required"]})
    gates.append({"gate": "REPRODUCIBILITY", "actual": aggregate_result["reproducibility"], "required": contract["reproducibility_required"], "passed": aggregate_result["reproducibility"] == contract["reproducibility_required"]})
    verdict = contract["integrity_failure_verdict"] if not integrity else contract["pass_verdict"] if all(gate["passed"] for gate in gates) else contract["valid_gate_failure_verdict"]
    return {"verdict": verdict, "gates": gates}


def verify_raw_before_gold(root: Path, raw_manifest_path: Path, a3_manifest_path: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    a3 = read_json(a3_manifest_path);raw_manifest = read_json(raw_manifest_path)
    if a3.get("status") != A3_STATUS:raise EvaluationIntegrityError("A3_FIX4_MANIFEST_REQUIRED")
    if sha256(a3_manifest_path) != raw_manifest.get("a3_manifest_sha256"):raise EvaluationIntegrityError("RAW_A3_MANIFEST_BINDING_MISMATCH")
    paths = a3.get("paths", {});artifacts = a3.get("artifact_sha256", {})
    schema_path = resolve_from_root(root, paths.get("raw_manifest_schema", ""))
    if sha256(schema_path) != artifacts.get("raw_manifest_schema"):raise EvaluationIntegrityError("RAW_SCHEMA_IDENTITY_DRIFT")
    schema = read_json(schema_path)
    if set(raw_manifest) != set(schema["required_fields"]) or raw_manifest.get("schema_version") != schema["raw_manifest_schema_version"] or raw_manifest.get("rows") != schema["rows"] or raw_manifest.get("scoring_loaded") is not False:raise EvaluationIntegrityError("RAW_MANIFEST_SCHEMA_INVALID")
    if any(field in raw_manifest for field in schema["gold_fields_forbidden"]):raise EvaluationIntegrityError("GOLD_FIELD_IN_RAW_MANIFEST")
    if raw_manifest["candidate_production_commit"] != a3["candidate_production_commit"] or raw_manifest["candidate_source_tree_sha256"] != a3["candidate_source_tree_sha256"]:raise EvaluationIntegrityError("RAW_CANDIDATE_BINDING_MISMATCH")
    if raw_manifest["runtime_input_aggregate_sha256"] != a3["runtime_input_aggregate_sha256"] or raw_manifest["inference_input_sha256"] != a3["inference_input_sha256"] or raw_manifest["case_order_sha256"] != a3["case_order_sha256"] or raw_manifest["e1_harness_sha256"] != a3["e1_harness_sha256"]:raise EvaluationIntegrityError("RAW_EXECUTION_BINDING_MISMATCH")
    if raw_manifest.get("selected_retriever") != "R0" or raw_manifest.get("selected_retriever") != a3.get("selected_retriever") or raw_manifest.get("retrieval_decision_sha256") != a3.get("retrieval_decision_sha256"):raise EvaluationIntegrityError("RAW_RETRIEVER_DECISION_BINDING_MISMATCH")
    source_receipt_path = resolve_from_root(root, paths["candidate_source_tree_receipt"])
    if sha256(source_receipt_path) != artifacts["candidate_source_tree_receipt"]:raise EvaluationIntegrityError("SOURCE_TREE_RECEIPT_DRIFT")
    if verify_working_source_tree(root, read_json(source_receipt_path)) != a3["candidate_source_tree_sha256"]:raise EvaluationIntegrityError("CANDIDATE_EXECUTION_SOURCE_TREE_DRIFT")
    if sha256(root / "scripts/evaluation/week3_ev2_e1.py") != a3["e1_harness_sha256"] or sha256(root / "scripts/evaluation/week3_ev2_integrity.py") != a3["integrity_source_sha256"]:raise EvaluationIntegrityError("E1_OR_INTEGRITY_SOURCE_DRIFT")
    case_order_path = resolve_from_root(root, paths["case_order"]);case_order = read_json_list(case_order_path)
    if not isinstance(case_order, list) or sha256(case_order_path) != a3["case_order_sha256"]:raise EvaluationIntegrityError("CASE_ORDER_DRIFT")
    expected_ids = [row["case_id"] for row in case_order];expected_queries = [row["query_sha256"] for row in case_order]
    if raw_manifest["case_id_order"] != expected_ids or raw_manifest["query_sha256_order"] != expected_queries or len(set(expected_ids)) != 60:raise EvaluationIntegrityError("RAW_ORDER_BINDING_MISMATCH")
    consumption_path = resolve_from_root(root, raw_manifest["consumption_receipt_path"])
    if sha256(consumption_path) != raw_manifest["consumption_receipt_sha256"]:raise EvaluationIntegrityError("CONSUMPTION_RECEIPT_DRIFT")
    consumption = read_json(consumption_path)
    if consumption.get("a4_authorization_id") != raw_manifest["a4_authorization_id"] or consumption.get("a3_manifest_sha256") != raw_manifest["a3_manifest_sha256"] or consumption.get("candidate_production_commit") != raw_manifest["candidate_production_commit"] or consumption.get("candidate_source_tree_sha256") != raw_manifest["candidate_source_tree_sha256"] or consumption.get("selected_retriever") != "R0" or consumption.get("selected_retriever") != raw_manifest["selected_retriever"] or consumption.get("retrieval_decision_sha256") != raw_manifest["retrieval_decision_sha256"]:raise EvaluationIntegrityError("CONSUMPTION_RAW_BINDING_MISMATCH")
    raw_path = resolve_from_root(root, raw_manifest["raw_output_path"])
    if sha256(raw_path) != raw_manifest["raw_output_sha256"]:raise EvaluationIntegrityError("RAW_OUTPUT_SHA_MISMATCH")
    physical = raw_path.read_bytes().splitlines(keepends=True)
    if len(physical) != 60 or any(not line.endswith(b"\n") for line in physical):raise EvaluationIntegrityError("RAW_PHYSICAL_ROW_COUNT_OR_NEWLINE")
    row_hashes = [hashlib.sha256(line).hexdigest() for line in physical]
    if row_hashes != raw_manifest["raw_row_sha256"] or len(row_hashes) != 60:raise EvaluationIntegrityError("RAW_ROW_HASH_MISMATCH")
    try:raw_rows = [json.loads(line) for line in physical]
    except json.JSONDecodeError:raise EvaluationIntegrityError("RAW_JSON_INVALID") from None
    ids = [row.get("query_id") for row in raw_rows]
    if ids != expected_ids or len(set(ids)) != 60:raise EvaluationIntegrityError("RAW_QUERY_ID_ORDER_OR_UNIQUENESS")
    return a3, raw_manifest, raw_rows


def verify_frozen_scorer_inputs(root: Path, a3: dict[str, Any]) -> None:
    for relative, wanted in a3.get("gold_sha256", {}).items():
        if sha256(root / relative) != wanted:raise EvaluationIntegrityError("FROZEN_GOLD_DRIFT")
    for relative, wanted in a3.get("runtime_input_sha256", {}).items():
        if sha256(resolve_from_root(root, relative)) != wanted:raise EvaluationIntegrityError(f"FROZEN_RUNTIME_INPUT_DRIFT:{relative}")
    if aggregate_bindings_sha256(a3["runtime_input_sha256"]) != a3["runtime_input_aggregate_sha256"]:raise EvaluationIntegrityError("RUNTIME_BINDING_AGGREGATE_DRIFT")
    required = {
        "evaluator_source": "scripts/evaluation/week3_ev2_evaluator.py",
        "evaluator_mapping": a3["paths"]["evaluator_mapping"],
        "forbidden_action_rules": a3["paths"]["forbidden_action_rules"],
        "reason_compatibility": a3["paths"]["reason_compatibility"],
        "product_gate_contract": a3["paths"]["product_gate_contract"],
        "raw_manifest_schema": a3["paths"]["raw_manifest_schema"],
        "raw_production_invariants": a3["paths"]["raw_production_invariants"],
        "causal_precedence_contract": a3["paths"]["causal_precedence_contract"],
        "case_order": a3["paths"]["case_order"],
        "inference_inputs": a3["paths"]["inference_inputs"],
        "candidate_source_tree_receipt": a3["paths"]["candidate_source_tree_receipt"],
    }
    for key, relative in required.items():
        if sha256(resolve_from_root(root, relative)) != a3["artifact_sha256"].get(key):raise EvaluationIntegrityError(f"SCORER_INPUT_DRIFT:{key}")
    if sha256(root / "scripts/evaluation/week3_ev2_e1.py") != a3["e1_harness_sha256"]:raise EvaluationIntegrityError("SCORER_INPUT_DRIFT:e1_harness")
    if sha256(root / "scripts/evaluation/week3_ev2_integrity.py") != a3["integrity_source_sha256"]:raise EvaluationIntegrityError("SCORER_INPUT_DRIFT:integrity_source")


def score_frozen(root: Path, raw_manifest_path: Path, a3_manifest_path: Path, output: Path) -> dict[str, Any]:
    a3, raw_manifest, raw_rows = verify_raw_before_gold(root, raw_manifest_path, a3_manifest_path)
    verify_frozen_scorer_inputs(root, a3)
    pass_a = read_jsonl(resolve_from_root(root, a3["paths"]["pass_a"]));pass_b = read_jsonl(resolve_from_root(root, a3["paths"]["pass_b"]));pass_c = read_jsonl(resolve_from_root(root, a3["paths"]["pass_c"]))
    case_ids = [row["case_id"] for row in pass_a]
    if len(case_ids) != 60 or len(set(case_ids)) != 60 or set(case_ids) != {row["case_id"] for row in pass_c}:raise EvaluationIntegrityError("PASS_A_C_MEMBERSHIP_INVALID")
    strata = Counter(row.get("semantic_stratum") for row in pass_a)
    if strata != Counter({"STANDARD":24,"SAFE_CORRECTIVE":18,"HARD_ABSTAIN_ESCALATE":12,"AMBIGUOUS_OR_PARTIAL_SAFE_STOP":6}):raise EvaluationIntegrityError("SEMANTIC_STRATUM_DISTRIBUTION_INVALID")
    pass_a_by = {row["case_id"]: row for row in pass_a};pass_c_by = {row["case_id"]: row for row in pass_c};pass_b_by: dict[str, list[dict[str, Any]]] = {}
    for row in pass_b:pass_b_by.setdefault(row["case_id"], []).append(row)
    mapping = load_mapping(resolve_from_root(root, a3["paths"]["evaluator_mapping"]));reason_registry = load_reason_compatibility(resolve_from_root(root, a3["paths"]["reason_compatibility"]));frozen_codes = {code for row in pass_c for code in row.get("forbidden_claims_actions", [])};safety = load_safety_rules(resolve_from_root(root, a3["paths"]["forbidden_action_rules"]), frozen_codes);gate = read_json(resolve_from_root(root, a3["paths"]["product_gate_contract"]));as_of = date.fromisoformat(read_json(root / "configs/generation/grounded_pipeline_v3.json")["evaluation_as_of_date"])
    def execute() -> list[dict[str, Any]]:
        return [evaluate_row(pass_c_by[raw["query_id"]], pass_b_by.get(raw["query_id"], []), raw, mapping, reason_registry, safety, pass_a_by[raw["query_id"]]["semantic_stratum"], as_of) for raw in raw_rows]
    first = execute();second = execute();reproducible = stable_json_sha256(first) == stable_json_sha256(second)
    aggregate_result = aggregate(first, gate, "PASS" if reproducible else "FAIL")
    result = {"schema_version": SCORE_SCHEMA, "final_result": aggregate_result["gate_decision"]["verdict"], "rows": first, "aggregate": aggregate_result, "semantic_stratum_distribution": dict(sorted(strata.items())), "raw_manifest_sha256": sha256(raw_manifest_path), "a3_manifest_sha256": sha256(a3_manifest_path), "scorer_reproduction_sha256": stable_json_sha256(first)}
    output.parent.mkdir(parents=True, exist_ok=True);output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser();parser.add_argument("command", choices=("score",));parser.add_argument("--root", type=Path, required=True);parser.add_argument("--raw-manifest", type=Path, required=True);parser.add_argument("--a3-manifest", type=Path, required=True);parser.add_argument("--output", type=Path, required=True);args = parser.parse_args();root = args.root.resolve()
    try:
        raw_manifest = resolve_from_root(root, args.raw_manifest);a3_manifest = resolve_from_root(root, args.a3_manifest);output = resolve_from_root(root, args.output);result = score_frozen(root, raw_manifest, a3_manifest, output)
    except (EvaluationIntegrityError, IntegrityError, KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as error:
        try:
            output = resolve_from_root(root, args.output);output.parent.mkdir(parents=True, exist_ok=True);output.write_text(json.dumps({"schema_version": SCORE_SCHEMA, "final_result": "INVALID", "integrity_error": str(error)}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except Exception:pass
        print(f"R1_INVALID:{error}", file=sys.stderr);return 2
    return 2 if result["final_result"] == "INVALID" else 0


if __name__ == "__main__":raise SystemExit(main())
