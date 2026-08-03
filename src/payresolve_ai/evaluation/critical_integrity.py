"""Independent post-evaluation integrity audit for invalidated critical_eval_v1."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date
from itertools import combinations
from pathlib import Path
from typing import Any

from payresolve_ai.evaluation.gold_mapping import canonical_rows_sha256, load_jsonl
from payresolve_ai.kb.validation import is_document_eligible

from .critical import CriticalEvaluationError, eligible_section_ids, load_config, mapping_sha256, membership_sha256, sha256_file


JUDGMENT_PATH = Path("data/evaluation/critical_eval_v1_posthoc_support_judgments.jsonl")
POSITIVE_AUDIT_PATH = Path("reports/week_03/results/critical_eval_v1_posthoc_positive_integrity_audit.csv")
NEGATIVE_AUDIT_PATH = Path("reports/week_03/results/critical_eval_v1_posthoc_negative_integrity_audit.csv")
SUMMARY_PATH = Path("reports/week_03/results/critical_eval_v1_integrity_incident_summary.json")
INTEGRITY_CONFIG_PATH = Path("configs/evaluation/critical_eval_v1_integrity_audit.json")
ORIGINAL_HASHES = {
    "scenario_raw_sha256": "9e0249a9fd6e2c1bf6d28013189228a5809d6c8bbbfa366e4747918632b8e370",
    "query_sha256": "c8d8ab91adf277da8485ee2c57df6bdf1010c511b68e18adc94a4d10abd32104",
    "dataset_raw_sha256": "4d99a272dcb3a8fa0c6d860c0fd244dbaf35a9c190d7d194466f1f3d38c1f54d",
    "dataset_canonical_sha256": "aa169c4e60d10defb70a88ab7b03c79306c2e37e109c6c78e9505acfd832b800",
    "mapping_sha256": "3689dc801c4deb20ecdb93c4a4da0a5f3c871f83c196ecb215aa89d8f5fa0205",
    "membership_sha256": "d52e3f35fbe0287c2045a26e57db05a784e247fd72fb14304b2c3b7915ada4cb",
    "pre_evaluation_manifest_sha256": "b9183f41aed54c343da54f0bd97b8196c9c2788333ba8fcce4a1447843ce6c22",
}


def _query_hash(rows: list[dict[str, Any]]) -> str:
    fields = ("query_id", "query_text", "expected_response_type", "gold_intent", "intent_family", "requested_dimension", "case_type", "case_tags")
    return canonical_rows_sha256([{key: row.get(key) for key in fields} for row in rows])


def verify_original_hashes(root: Path, config_path: Path) -> dict[str, str]:
    config = load_config(config_path); rows = load_jsonl(root / config["dataset_path"])
    actual = {
        "scenario_raw_sha256": sha256_file(root / config["scenario_path"]),
        "query_sha256": _query_hash(rows),
        "dataset_raw_sha256": sha256_file(root / config["dataset_path"]),
        "dataset_canonical_sha256": canonical_rows_sha256(rows),
        "mapping_sha256": mapping_sha256(rows),
        "membership_sha256": membership_sha256(rows),
        "pre_evaluation_manifest_sha256": sha256_file(root / config["outputs"]["pre_evaluation_manifest"]),
    }
    if actual != ORIGINAL_HASHES:
        raise CriticalEvaluationError("original W3-002 input/output reference hash changed")
    return actual


def _section_judgments(sections: list[str], direct: set[str], hard_support: set[str], corrective: set[str]) -> str:
    rows = []
    for evidence_id in sections:
        judgment = "HARD_NEGATIVE_DIRECT_SUPPORT" if evidence_id in hard_support else "DIRECT_SUPPORT" if evidence_id in direct else "CORRECTIVE_SUPPORT" if evidence_id in corrective else "NOT_DIRECT_SUPPORT"
        rows.append({"evidence_id": evidence_id, "judgment": judgment})
    return json.dumps(rows, separators=(",", ":"), sort_keys=True)


def _unique_non_empty_strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and bool(item.strip()) for item in value)
        and len(value) == len(set(value))
    )


def parse_evidence_identity(evidence_id: Any) -> tuple[str, str]:
    if not isinstance(evidence_id, str) or "#" not in evidence_id:
        raise CriticalEvaluationError("invalid-evidence-identity: expected DOCUMENT_ID#SECTION_ID")
    document_id, section_id = evidence_id.split("#", 1)
    if not document_id or not section_id:
        raise CriticalEvaluationError("invalid-evidence-identity: document and section IDs must be non-empty")
    return document_id, section_id


def eligible_evidence_catalog(root: Path, config: dict[str, Any]) -> dict[str, str]:
    """Return eligible section identity -> metadata document identity."""
    as_of = date.fromisoformat(config["evaluation_as_of_date"])
    catalog: dict[str, str] = {}
    for document in load_jsonl(root / config["kb_documents"]):
        if not is_document_eligible(document, as_of):
            continue
        metadata_document_id = document["document_id"]
        for section in document["content_sections"]:
            evidence_id = f"{metadata_document_id}#{section['section_id']}"
            parsed_document_id, _ = parse_evidence_identity(evidence_id)
            if parsed_document_id != metadata_document_id:
                raise CriticalEvaluationError("invalid-evidence-identity: parsed document differs from metadata")
            if evidence_id in catalog:
                raise CriticalEvaluationError("invalid-evidence-identity: duplicate eligible evidence identity")
            catalog[evidence_id] = metadata_document_id
    return catalog


def analyze_positive_obligations(
    query: dict[str, Any], review: dict[str, Any], eligible_evidence: dict[str, str]
) -> dict[str, Any]:
    """Validate an independent judgment and derive its obligation-cover properties."""
    direct_list = review.get("direct_supporting_evidence_ids")
    if not _unique_non_empty_strings(direct_list):
        raise CriticalEvaluationError("invalid-obligation-contract: direct support must be non-empty and unique")
    direct = set(direct_list)
    for evidence_id in direct:
        parsed_document_id, _ = parse_evidence_identity(evidence_id)
        if evidence_id in eligible_evidence and eligible_evidence[evidence_id] != parsed_document_id:
            raise CriticalEvaluationError("invalid-evidence-identity: reported document differs from evidence metadata")
    if not direct <= set(eligible_evidence):
        raise CriticalEvaluationError("obligation-evidence-not-eligible: direct support includes ineligible evidence")

    hard_list = review.get("hard_negatives_that_support")
    if not isinstance(hard_list, list) or any(not isinstance(item, str) or not item.strip() for item in hard_list) or len(hard_list) != len(set(hard_list)):
        raise CriticalEvaluationError("hard-negative-support-mismatch: support IDs must be unique strings")
    hard_support = set(hard_list)
    expected_hard_support = set(query["hard_negative_evidence_ids"]) & direct
    if hard_support != expected_hard_support:
        raise CriticalEvaluationError("hard-negative-support-mismatch: reviewed set differs from original-hard-negative intersection")

    obligations = review.get("required_obligations")
    if not isinstance(obligations, list) or not obligations:
        raise CriticalEvaluationError("invalid-obligation-contract: required_obligations must be non-empty")
    obligation_ids: list[str] = []
    acceptable_by_obligation: list[set[str]] = []
    for obligation in obligations:
        if not isinstance(obligation, dict):
            raise CriticalEvaluationError("invalid-obligation-contract: obligation must be an object")
        obligation_id = obligation.get("obligation_id")
        if not isinstance(obligation_id, str) or not obligation_id.strip():
            raise CriticalEvaluationError("invalid-obligation-contract: obligation_id must be non-empty")
        obligation_ids.append(obligation_id)
        acceptable = obligation.get("acceptable_evidence_ids")
        if not _unique_non_empty_strings(acceptable):
            raise CriticalEvaluationError("invalid-obligation-contract: acceptable evidence must be non-empty and unique")
        acceptable_set = set(acceptable)
        for evidence_id in acceptable_set:
            parsed_document_id, _ = parse_evidence_identity(evidence_id)
            if evidence_id in eligible_evidence and eligible_evidence[evidence_id] != parsed_document_id:
                raise CriticalEvaluationError("invalid-evidence-identity: obligation document differs from evidence metadata")
        if not acceptable_set <= set(eligible_evidence):
            raise CriticalEvaluationError("obligation-evidence-not-eligible: obligation includes ineligible evidence")
        if not acceptable_set <= direct:
            raise CriticalEvaluationError("obligation-evidence-not-direct: obligation evidence is outside direct support")
        acceptable_by_obligation.append(acceptable_set)
    if len(obligation_ids) != len(set(obligation_ids)):
        raise CriticalEvaluationError("invalid-obligation-contract: obligation IDs must be unique")

    valid_covers: list[dict[str, Any]] = []
    ordered_direct = sorted(direct)
    for size in range(1, len(ordered_direct) + 1):
        for candidate in combinations(ordered_direct, size):
            candidate_set = set(candidate)
            if all(candidate_set & acceptable for acceptable in acceptable_by_obligation):
                document_ids = sorted({eligible_evidence[evidence_id] for evidence_id in candidate})
                valid_covers.append({
                    "evidence_ids": list(candidate),
                    "section_count": len(candidate),
                    "document_ids": document_ids,
                    "distinct_document_count": len(document_ids),
                })
    if not valid_covers:
        raise CriticalEvaluationError("invalid-obligation-contract: no valid evidence cover")

    minimum_section_cover_size = min(cover["section_count"] for cover in valid_covers)
    minimum_document_cover_size = min(cover["distinct_document_count"] for cover in valid_covers)
    minimum_section_covers = [cover for cover in valid_covers if cover["section_count"] == minimum_section_cover_size]
    minimum_document_covers = [cover for cover in valid_covers if cover["distinct_document_count"] == minimum_document_cover_size]
    recomputed_multi_section = minimum_section_cover_size >= 2
    recomputed_multi_document = minimum_document_cover_size >= 2
    reviewed_multi = review.get("multi_document_semantically_necessary")
    if type(reviewed_multi) is not bool or reviewed_multi != recomputed_multi_document:
        raise CriticalEvaluationError("multi-section-document-conflation: reviewed multi-document flag disagrees with document cover")

    original_gold = set(query["gold_evidence_ids"])
    mandatory_gold = sorted(
        evidence_id for evidence_id in original_gold if all(evidence_id in cover["evidence_ids"] for cover in valid_covers)
    )
    replaceable_gold = sorted(original_gold - set(mandatory_gold))
    strict_replaceability = bool(replaceable_gold)
    original_exact_gold_overconstrained = query["evidence_requirement"] == "multi_document" and strict_replaceability
    original_multi_document_label_overconstrained = query["evidence_requirement"] == "multi_document" and not recomputed_multi_document
    exact_id_overconstrained = original_exact_gold_overconstrained or original_multi_document_label_overconstrained
    reason_codes: list[str] = []
    if query["evidence_requirement"] == "multi_document":
        if minimum_section_cover_size == 1:
            reason_codes.append("SINGLE_SECTION_SUFFICIENT")
        elif minimum_document_cover_size == 1:
            reason_codes.append("MULTI_SECTION_SINGLE_DOCUMENT_SUFFICIENT")
        elif strict_replaceability:
            reason_codes.append("MULTI_DOCUMENT_NECESSARY_STRICT_ID_REPLACEABLE")
    return {
        "direct": direct,
        "hard_support": hard_support,
        "semantic_obligation_count": len(obligations),
        "minimum_evidence_section_cover_size": minimum_section_cover_size,
        "minimum_distinct_document_cover_size": minimum_document_cover_size,
        "valid_evidence_covers": valid_covers,
        "minimum_section_covers": minimum_section_covers,
        "minimum_document_covers": minimum_document_covers,
        "multi_section_semantically_necessary": recomputed_multi_section,
        "multi_document_semantically_necessary": recomputed_multi_document,
        "single_section_sufficient": minimum_section_cover_size == 1,
        "multi_section_single_document_sufficient": recomputed_multi_section and minimum_document_cover_size == 1,
        "strict_gold_ids_required_in_every_valid_cover": mandatory_gold,
        "strict_gold_ids_replaceable_by_equivalent_evidence": replaceable_gold,
        "strict_gold_id_replaceability_detected": strict_replaceability,
        "original_exact_gold_contract_overconstrained": original_exact_gold_overconstrained,
        "original_multi_document_label_overconstrained": original_multi_document_label_overconstrained,
        "exact_id_overconstrained": exact_id_overconstrained,
        "overconstraint_reason_codes": reason_codes,
    }


def _positive_defect_details(query: dict[str, Any], direct: set[str], exact_id_overconstrained: bool) -> dict[str, Any]:
    original_gold = set(query["gold_evidence_ids"])
    original_acceptable = set(query["acceptable_evidence_ids"])
    original_hard = set(query["hard_negative_evidence_ids"])
    missing = direct - original_gold - original_acceptable
    hard_answers = direct & original_hard
    mapped_not_direct = (original_gold | original_acceptable) - direct
    reasons: list[str] = []
    if missing:
        reasons.append("MISSING_DIRECT_SUPPORT")
    if hard_answers:
        reasons.append("HARD_NEGATIVE_DIRECTLY_SUPPORTS")
    if mapped_not_direct:
        reasons.append("MAPPED_ROLE_NOT_DIRECT")
    if exact_id_overconstrained:
        reasons.append("EXACT_ID_MULTI_DOCUMENT_OVERCONSTRAINED")
    return {
        "missing": missing,
        "hard_answers": hard_answers,
        "mapped_not_direct": mapped_not_direct,
        "reasons": reasons,
    }


def build_integrity_audits(root: Path, config_path: Path) -> dict[str, Any]:
    """Materialize reviewed judgments; never infer support from original mapping roles."""
    config = load_config(config_path); verify_original_hashes(root, config_path)
    queries = {row["query_id"]: row for row in load_jsonl(root / config["dataset_path"])}
    reviews = load_jsonl(root / JUDGMENT_PATH); sections = eligible_section_ids(root, config); section_set = set(sections)
    evidence_catalog = eligible_evidence_catalog(root, config)
    if set(evidence_catalog) != section_set:
        raise CriticalEvaluationError("invalid-evidence-identity: eligible catalog membership mismatch")
    if len(reviews) != 60 or len({row["query_id"] for row in reviews}) != 60 or set(queries) != {row["query_id"] for row in reviews}:
        raise CriticalEvaluationError("independent support-judgment membership mismatch")
    positive_rows: list[dict[str, Any]] = []; negative_rows: list[dict[str, Any]] = []
    for review in reviews:
        query = queries[review["query_id"]]
        if len(review.get("rationale", "").split()) < 12:
            raise CriticalEvaluationError(f"non-specific integrity rationale: {review['query_id']}")
        if review["judgment_type"] == "POSITIVE":
            obligation_analysis = analyze_positive_obligations(query, review, evidence_catalog)
            direct = obligation_analysis["direct"]
            overconstrained = obligation_analysis["exact_id_overconstrained"]
            defect = _positive_defect_details(query, direct, overconstrained)
            missing = defect["missing"]; hard_answers = defect["hard_answers"]; mapped_not_direct = defect["mapped_not_direct"]
            defect_reasons = defect["reasons"]
            positive_rows.append({
                "query_id": query["query_id"], "query_text": query["query_text"], "requested_dimension": query["requested_dimension"], "evidence_requirement": query["evidence_requirement"],
                "reviewed_section_ids": ";".join(sections), "section_judgments_json": _section_judgments(sections, direct, hard_answers, set()),
                "independently_direct_supporting_section_ids": ";".join(sorted(direct)), "original_gold_ids": ";".join(query["gold_evidence_ids"]),
                "original_acceptable_ids": ";".join(query["acceptable_evidence_ids"]), "original_hard_negative_ids": ";".join(query["hard_negative_evidence_ids"]),
                "missing_direct_support_ids": ";".join(sorted(missing)), "hard_negatives_that_actually_support": ";".join(sorted(hard_answers)),
                "mapped_gold_or_acceptable_not_direct": ";".join(sorted(mapped_not_direct)), "reviewed_multi_document_semantically_necessary": str(bool(review["multi_document_semantically_necessary"])).lower(),
                "required_obligations_json": json.dumps(review["required_obligations"], separators=(",", ":"), sort_keys=True),
                "semantic_obligation_count": obligation_analysis["semantic_obligation_count"],
                "valid_evidence_covers_json": json.dumps(obligation_analysis["valid_evidence_covers"], separators=(",", ":")),
                "minimum_evidence_section_cover_size": obligation_analysis["minimum_evidence_section_cover_size"],
                "minimum_distinct_document_cover_size": obligation_analysis["minimum_distinct_document_cover_size"],
                "minimum_section_covers_json": json.dumps(obligation_analysis["minimum_section_covers"], separators=(",", ":")),
                "minimum_document_covers_json": json.dumps(obligation_analysis["minimum_document_covers"], separators=(",", ":")),
                "multi_section_semantically_necessary": str(obligation_analysis["multi_section_semantically_necessary"]).lower(),
                "multi_document_semantically_necessary": str(obligation_analysis["multi_document_semantically_necessary"]).lower(),
                "single_section_sufficient": str(obligation_analysis["single_section_sufficient"]).lower(),
                "multi_section_single_document_sufficient": str(obligation_analysis["multi_section_single_document_sufficient"]).lower(),
                "strict_gold_ids_required_in_every_valid_cover": ";".join(obligation_analysis["strict_gold_ids_required_in_every_valid_cover"]),
                "strict_gold_ids_replaceable_by_equivalent_evidence": ";".join(obligation_analysis["strict_gold_ids_replaceable_by_equivalent_evidence"]),
                "strict_gold_id_replaceability_detected": str(obligation_analysis["strict_gold_id_replaceability_detected"]).lower(),
                "original_exact_gold_contract_overconstrained": str(obligation_analysis["original_exact_gold_contract_overconstrained"]).lower(),
                "original_multi_document_label_overconstrained": str(obligation_analysis["original_multi_document_label_overconstrained"]).lower(),
                "exact_id_overconstrained": str(overconstrained).lower(),
                "overconstraint_reason_codes": ";".join(obligation_analysis["overconstraint_reason_codes"]),
                "independent_reviewer_rationale": review["rationale"], "integrity_verdict": "DEFECT" if defect_reasons else "NO_DEFECT_FOUND",
                "defect_reasons": ";".join(defect_reasons),
            })
        elif review["judgment_type"] == "NEGATIVE":
            corrective = set(review["corrective_evidence_ids"])
            if not corrective <= section_set:
                raise CriticalEvaluationError(f"invalid negative corrective support: {review['query_id']}")
            false_label = bool(review["complete_safe_corrective_answer"])
            negative_rows.append({
                "query_id": query["query_id"], "query_text": query["query_text"], "case_type": query["case_type"],
                "reviewed_section_ids": ";".join(sections), "section_judgments_json": _section_judgments(sections, set(), set(), corrective),
                "approved_corrective_evidence_ids": ";".join(sorted(corrective)), "complete_safe_corrective_answer": str(false_label).lower(),
                "original_expected_response_type": query["expected_response_type"], "false_abstain_label": str(false_label).lower(),
                "independent_reviewer_rationale": review["rationale"], "integrity_verdict": "FALSE_ABSTAIN_LABEL" if false_label else "NO_FALSE_LABEL_FOUND",
            })
        else:
            raise CriticalEvaluationError(f"invalid judgment type: {review['query_id']}")
    for path, rows in ((root / POSITIVE_AUDIT_PATH, positive_rows), (root / NEGATIVE_AUDIT_PATH, negative_rows)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=list(rows[0]), lineterminator="\n"); writer.writeheader(); writer.writerows(rows)
    defect_ids = [row["query_id"] for row in positive_rows if row["integrity_verdict"] == "DEFECT"]
    hard_ids = [row["query_id"] for row in positive_rows if row["hard_negatives_that_actually_support"]]
    over_ids = [row["query_id"] for row in positive_rows if "EXACT_ID_MULTI_DOCUMENT_OVERCONSTRAINED" in row["defect_reasons"]]
    single_section_ids = [row["query_id"] for row in positive_rows if row["single_section_sufficient"] == "true" and row["evidence_requirement"] == "multi_document"]
    single_document_ids = [row["query_id"] for row in positive_rows if row["multi_section_single_document_sufficient"] == "true" and row["evidence_requirement"] == "multi_document"]
    semantic_multi_document_ids = [row["query_id"] for row in positive_rows if row["multi_document_semantically_necessary"] == "true"]
    false_ids = [row["query_id"] for row in negative_rows if row["false_abstain_label"] == "true"]
    original_runtime = {key: sha256_file(root / config["outputs"][key]) for key in ("r0_rankings", "r1_rankings", "v0_outputs", "v1_outputs", "v2_outputs", "reproduction", "variant_metrics", "claim_audit", "outcome_classes")}
    summary = {
        "task_id": "W3-002", "status": "BLOCKED_CRITICAL_SET_INVALIDATED", "runtime_artifacts_internally_consistent": True,
        "critical_mapping_integrity": "INVALID", "invalid_reason": "PRE_EVALUATION_MAPPING_AUDIT_WAS_SELF_REFERENTIAL", "final_model_verdict": "NOT_ESTABLISHED",
        "positive_queries_reviewed": len(positive_rows), "negative_queries_reviewed": len(negative_rows), "eligible_sections_judged_per_query": len(sections),
        "positive_mapping_defect_count": len(defect_ids), "positive_mapping_defect_query_ids": defect_ids,
        "hard_negative_direct_support_count": len(hard_ids), "hard_negative_direct_support_query_ids": hard_ids,
        "exact_id_or_document_overconstrained_count": len(over_ids), "exact_id_or_document_overconstrained_query_ids": over_ids,
        "single_section_sufficient_count": len(single_section_ids), "single_section_sufficient_query_ids": single_section_ids,
        "multi_section_single_document_sufficient_count": len(single_document_ids), "multi_section_single_document_sufficient_query_ids": single_document_ids,
        "semantically_multi_document_necessary_count": len(semantic_multi_document_ids), "semantically_multi_document_necessary_query_ids": semantic_multi_document_ids,
        "false_abstain_label_count": len(false_ids), "false_abstain_label_query_ids": false_ids,
        "original_hashes": ORIGINAL_HASHES, "original_runtime_artifact_sha256": original_runtime,
        "support_judgments_sha256": sha256_file(root / JUDGMENT_PATH), "positive_audit_sha256": sha256_file(root / POSITIVE_AUDIT_PATH),
        "negative_audit_sha256": sha256_file(root / NEGATIVE_AUDIT_PATH),
        "evidence_obligation_recommendation": "Future evaluation should require every semantic obligation to be satisfied by any independently reviewed acceptable evidence ID; never require exact preselected IDs when equivalent evidence satisfies the same obligation.",
        "replacement_critical_evaluation_created": False, "encoder_or_pipeline_rerun": False,
    }
    (root / SUMMARY_PATH).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    integrity_config_path = root / INTEGRITY_CONFIG_PATH
    integrity_config = json.loads(integrity_config_path.read_text(encoding="utf-8"))
    integrity_config["support_judgment_source_sha256"] = sha256_file(root / JUDGMENT_PATH)
    integrity_config["positive_audit_sha256"] = summary["positive_audit_sha256"]
    integrity_config["negative_audit_sha256"] = summary["negative_audit_sha256"]
    integrity_config_path.write_text(json.dumps(integrity_config, indent=2) + "\n", encoding="utf-8")
    return summary


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as source:
        return list(csv.DictReader(source))


def verify_integrity_incident(root: Path, config_path: Path) -> dict[str, Any]:
    original = verify_original_hashes(root, config_path); config = load_config(config_path); sections = set(eligible_section_ids(root, config))
    evidence_catalog = eligible_evidence_catalog(root, config)
    if set(evidence_catalog) != sections:
        raise CriticalEvaluationError("invalid-evidence-identity: eligible catalog membership mismatch")
    queries = {row["query_id"]: row for row in load_jsonl(root / config["dataset_path"])}
    reviews = {row["query_id"]: row for row in load_jsonl(root / JUDGMENT_PATH)}
    integrity_config = json.loads((root / INTEGRITY_CONFIG_PATH).read_text(encoding="utf-8"))
    section_hash = hashlib.sha256(("\n".join(sorted(sections)) + "\n").encode()).hexdigest()
    if integrity_config.get("support_source_independent_of_original_mapping") is not True or integrity_config.get("retrieval_or_model_outputs_used_for_support_judgments") is not False:
        raise CriticalEvaluationError("support-judgment independence contract mismatch")
    if integrity_config["support_judgment_source_sha256"] != sha256_file(root / JUDGMENT_PATH) or integrity_config["eligible_section_ids_sha256"] != section_hash:
        raise CriticalEvaluationError("frozen independent support-judgment source drift")
    positives = _read_csv(root / POSITIVE_AUDIT_PATH); negatives = _read_csv(root / NEGATIVE_AUDIT_PATH)
    if len(positives) != integrity_config["expected_positive_rows"] or len(negatives) != integrity_config["expected_negative_rows"]:
        raise CriticalEvaluationError("integrity audit row count mismatch")
    if set(queries) != set(reviews) or len(reviews) != len(queries):
        raise CriticalEvaluationError("independent support-judgment membership mismatch")
    rationales = set()
    for row in positives + negatives:
        reviewed = row["reviewed_section_ids"].split(";"); judgments = json.loads(row["section_judgments_json"])
        judged_ids = [item["evidence_id"] for item in judgments]
        if len(reviewed) != 52 or len(set(reviewed)) != 52 or set(reviewed) != sections:
            raise CriticalEvaluationError(f"audit lacks 52 unique reviewed sections: {row['query_id']}")
        if len(judged_ids) != 52 or len(set(judged_ids)) != 52 or set(judged_ids) != sections:
            raise CriticalEvaluationError(f"audit lacks 52 unique section judgments: {row['query_id']}")
        rationale = row["independent_reviewer_rationale"]
        if len(rationale.split()) < 12 or rationale in rationales:
            raise CriticalEvaluationError(f"audit rationale is absent or reused: {row['query_id']}")
        rationales.add(rationale)

    recomputed_defect_ids: list[str] = []
    recomputed_hard_ids: list[str] = []
    recomputed_over_ids: list[str] = []
    recomputed_single_section_ids: list[str] = []
    recomputed_single_document_ids: list[str] = []
    recomputed_semantic_multi_document_ids: list[str] = []
    positive_by_id = {row["query_id"]: row for row in positives}
    negative_by_id = {row["query_id"]: row for row in negatives}
    for query_id, review in reviews.items():
        query = queries[query_id]
        if review["judgment_type"] == "POSITIVE":
            if query_id not in positive_by_id:
                raise CriticalEvaluationError(f"integrity audit row missing: {query_id}")
            analysis = analyze_positive_obligations(query, review, evidence_catalog)
            defect = _positive_defect_details(query, analysis["direct"], analysis["exact_id_overconstrained"])
            row = positive_by_id[query_id]
            if set(filter(None, row["independently_direct_supporting_section_ids"].split(";"))) != analysis["direct"]:
                raise CriticalEvaluationError(f"obligation-evidence-not-direct: audit/source mismatch for {query_id}")
            if set(filter(None, row["hard_negatives_that_actually_support"].split(";"))) != analysis["hard_support"]:
                raise CriticalEvaluationError(f"hard-negative-support-mismatch: audit/source mismatch for {query_id}")
            expected_obligations = json.dumps(review["required_obligations"], separators=(",", ":"), sort_keys=True)
            if row["required_obligations_json"] != expected_obligations:
                raise CriticalEvaluationError(f"invalid-obligation-contract: audit/source mismatch for {query_id}")
            if int(row["semantic_obligation_count"]) != analysis["semantic_obligation_count"] or int(row["minimum_evidence_section_cover_size"]) != analysis["minimum_evidence_section_cover_size"]:
                raise CriticalEvaluationError(f"section-cover-mismatch: stale section-cover metrics for {query_id}")
            if int(row["minimum_distinct_document_cover_size"]) != analysis["minimum_distinct_document_cover_size"]:
                raise CriticalEvaluationError(f"document-cover-mismatch: stale document-cover metrics for {query_id}")
            if json.loads(row["valid_evidence_covers_json"]) != analysis["valid_evidence_covers"]:
                raise CriticalEvaluationError(f"exact-id-overconstraint-mismatch: valid cover enumeration drift for {query_id}")
            if json.loads(row["minimum_section_covers_json"]) != analysis["minimum_section_covers"]:
                raise CriticalEvaluationError(f"section-cover-mismatch: minimum section covers drift for {query_id}")
            if json.loads(row["minimum_document_covers_json"]) != analysis["minimum_document_covers"]:
                raise CriticalEvaluationError(f"document-cover-mismatch: minimum document covers drift for {query_id}")
            if row["multi_section_semantically_necessary"] != str(analysis["multi_section_semantically_necessary"]).lower():
                raise CriticalEvaluationError(f"section-cover-mismatch: multi-section flag drift for {query_id}")
            if row["multi_document_semantically_necessary"] != str(analysis["multi_document_semantically_necessary"]).lower():
                raise CriticalEvaluationError(f"multi-section-document-conflation: multi-document flag drift for {query_id}")
            if analysis["minimum_distinct_document_cover_size"] == 1 and row["multi_document_semantically_necessary"] == "true":
                raise CriticalEvaluationError(f"same-document-cover-ignored: {query_id}")
            if set(filter(None, row["strict_gold_ids_required_in_every_valid_cover"].split(";"))) != set(analysis["strict_gold_ids_required_in_every_valid_cover"]):
                raise CriticalEvaluationError(f"exact-id-overconstraint-mismatch: mandatory strict gold drift for {query_id}")
            if set(filter(None, row["strict_gold_ids_replaceable_by_equivalent_evidence"].split(";"))) != set(analysis["strict_gold_ids_replaceable_by_equivalent_evidence"]):
                raise CriticalEvaluationError(f"exact-id-overconstraint-mismatch: replaceable strict gold drift for {query_id}")
            boolean_fields = ("single_section_sufficient", "multi_section_single_document_sufficient", "strict_gold_id_replaceability_detected", "original_exact_gold_contract_overconstrained", "original_multi_document_label_overconstrained", "exact_id_overconstrained")
            if any(row[field] != str(analysis[field]).lower() for field in boolean_fields):
                raise CriticalEvaluationError(f"exact-id-overconstraint-mismatch: classification drift for {query_id}")
            reported_reason_codes = row["overconstraint_reason_codes"].split(";") if row["overconstraint_reason_codes"] else []
            if reported_reason_codes != analysis["overconstraint_reason_codes"]:
                raise CriticalEvaluationError(f"overconstraint-reason-mismatch: {query_id}")
            reported_reasons = row["defect_reasons"].split(";") if row["defect_reasons"] else []
            if reported_reasons != defect["reasons"]:
                raise CriticalEvaluationError(f"exact-id-overconstraint-mismatch: defect classification drift for {query_id}")
            if defect["reasons"]:
                recomputed_defect_ids.append(query_id)
            if defect["hard_answers"]:
                recomputed_hard_ids.append(query_id)
            if analysis["exact_id_overconstrained"]:
                recomputed_over_ids.append(query_id)
            if query["evidence_requirement"] == "multi_document" and analysis["single_section_sufficient"]:
                recomputed_single_section_ids.append(query_id)
            if query["evidence_requirement"] == "multi_document" and analysis["multi_section_single_document_sufficient"]:
                recomputed_single_document_ids.append(query_id)
            if analysis["multi_document_semantically_necessary"]:
                recomputed_semantic_multi_document_ids.append(query_id)
        elif review["judgment_type"] == "NEGATIVE":
            if query_id not in negative_by_id:
                raise CriticalEvaluationError(f"integrity audit row missing: {query_id}")
            corrective = review.get("corrective_evidence_ids")
            if not isinstance(corrective, list) or len(corrective) != len(set(corrective)) or not set(corrective) <= sections:
                raise CriticalEvaluationError(f"obligation-evidence-not-eligible: invalid corrective evidence for {query_id}")
            row = negative_by_id[query_id]
            if set(filter(None, row["approved_corrective_evidence_ids"].split(";"))) != set(corrective) or row["false_abstain_label"] != str(bool(review["complete_safe_corrective_answer"])).lower():
                raise CriticalEvaluationError(f"negative integrity judgment drift: {query_id}")
        else:
            raise CriticalEvaluationError(f"invalid judgment type: {query_id}")

    summary = json.loads((root / SUMMARY_PATH).read_text(encoding="utf-8"))
    if summary["original_hashes"] != original or summary["critical_mapping_integrity"] != "INVALID" or summary["final_model_verdict"] != "NOT_ESTABLISHED":
        raise CriticalEvaluationError("integrity incident lifecycle mismatch")
    if summary["positive_audit_sha256"] != sha256_file(root / POSITIVE_AUDIT_PATH) or summary["negative_audit_sha256"] != sha256_file(root / NEGATIVE_AUDIT_PATH):
        raise CriticalEvaluationError("integrity audit artifact drift")
    if integrity_config["positive_audit_sha256"] != summary["positive_audit_sha256"] or integrity_config["negative_audit_sha256"] != summary["negative_audit_sha256"]:
        raise CriticalEvaluationError("frozen integrity-audit hash mismatch")
    false_ids = [query_id for query_id, review in reviews.items() if review["judgment_type"] == "NEGATIVE" and bool(review["complete_safe_corrective_answer"])]
    expected_summary = {
        "positive_mapping_defect_query_ids": recomputed_defect_ids,
        "hard_negative_direct_support_query_ids": recomputed_hard_ids,
        "exact_id_or_document_overconstrained_query_ids": recomputed_over_ids,
        "single_section_sufficient_query_ids": recomputed_single_section_ids,
        "multi_section_single_document_sufficient_query_ids": recomputed_single_document_ids,
        "semantically_multi_document_necessary_query_ids": recomputed_semantic_multi_document_ids,
        "false_abstain_label_query_ids": false_ids,
    }
    for key, expected_ids in expected_summary.items():
        count_key = key.replace("_query_ids", "_count")
        if summary.get(key) != expected_ids or summary.get(count_key) != len(expected_ids):
            raise CriticalEvaluationError(f"exact-id-overconstraint-mismatch: stale summary field {key}")
    return {"status": "PASS", "runtime_artifacts_internally_consistent": True, "critical_mapping_integrity": "INVALID",
            "final_model_verdict": "NOT_ESTABLISHED", "positive_mapping_defects": summary["positive_mapping_defect_count"],
            "hard_negative_direct_support": summary["hard_negative_direct_support_count"], "exact_id_or_document_overconstrained": summary["exact_id_or_document_overconstrained_count"],
            "false_abstain_labels": summary["false_abstain_label_count"], "original_hashes_preserved": True}
