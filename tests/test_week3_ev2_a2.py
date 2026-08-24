"""Integrity tests for independent semantic Pass B and mechanical Pass C."""

from __future__ import annotations

import copy
import inspect
import json
from collections import Counter
from pathlib import Path

import pytest

from scripts.evaluation import week3_ev2_a2 as a2
from scripts.evaluation import week3_ev2_a2_fix2b as fix2b


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def pass_a() -> list[dict]:
    return a2.read_jsonl(ROOT / a2.PASS_A)


@pytest.fixture(scope="module")
def pass_a_rev1() -> list[dict]:
    return a2.read_jsonl(ROOT / a2.PASS_A_REV1)


@pytest.fixture(scope="module")
def pass_a_v2() -> list[dict]:
    return a2.read_jsonl(ROOT / a2.PASS_A_V2)


@pytest.fixture(scope="module")
def neutral_matrix(pass_a: list[dict]) -> list[dict]:
    eligible, _ = a2.eligible_section_index(ROOT)
    rows = []
    for case in pass_a:
        for section in eligible.values():
            rows.append({
                "case_id": case["case_id"],
                "evidence_id": section["evidence_id"],
                "document_id": section["document_id"],
                "section_id": section["section_id"],
                "evidence_content_sha256": section["content_sha256"],
                "eligibility": "ELIGIBLE",
                "target_match": False,
                "state_match": False,
                "dimension_match": False,
                "obligations_covered": [],
                "obligations_not_covered": list(case["required_semantic_obligations"]),
                "obligation_support_quotes": {},
                "support_class": "IRRELEVANT",
                "support_rationale": "Manually reviewed clause does not materially bear on this case's required semantics.",
                "semantic_mismatch_reason": f"The clause does not address {', '.join(case['required_semantic_obligations'])} for the required target/state/dimension.",
                "review_provenance": "FIX1_INDEPENDENT_CONTENT_GROUNDED_SEMANTIC_REVIEW",
            })
    return rows


@pytest.fixture(scope="module")
def fix1b_judgments() -> list[dict]:
    return a2.read_jsonl(ROOT / a2.FIX1B_JUDGMENTS)


@pytest.fixture(scope="module")
def fix1b_case_review() -> dict:
    return json.loads((ROOT / a2.FIX1B_CASE_REVIEW).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fix1b_summary() -> dict:
    return json.loads((ROOT / a2.FIX1B_CONFLICT_SUMMARY).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fix2_judgments() -> list[dict]:
    return a2.read_jsonl(ROOT / a2.FIX2_JUDGMENTS)


@pytest.fixture(scope="module")
def fix2_case_review() -> dict:
    return json.loads((ROOT / a2.FIX2_CASE_REVIEW).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fix2_ledger() -> dict:
    return json.loads((ROOT / a2.FIX2_LEDGER).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fix2_audit() -> dict:
    return json.loads((ROOT / a2.FIX2_PASS_A_AUDIT).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fix2a_classification() -> dict:
    return json.loads((ROOT / a2.FIX2A_OBLIGATION_CLASSIFICATION).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fix2a_review() -> dict:
    return json.loads((ROOT / a2.FIX2A_CONSISTENCY_REVIEW).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fix2a_summary() -> dict:
    return json.loads((ROOT / a2.FIX2A_CONFLICT_SUMMARY).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fix3_judgments() -> list[dict]:
    return a2.read_jsonl(ROOT / a2.FIX3_JUDGMENTS)


@pytest.fixture(scope="module")
def fix3_case_review() -> dict:
    return json.loads((ROOT / a2.FIX3_CASE_REVIEW).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fix3_ledger() -> dict:
    return json.loads((ROOT / a2.FIX3_LEDGER).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fix3_audit() -> dict:
    return json.loads((ROOT / a2.FIX3_PASS_A_AUDIT).read_text(encoding="utf-8"))


def mutate(rows: list[dict], index: int = 0, **changes) -> list[dict]:
    result = list(rows)
    result[index] = {**rows[index], **changes}
    return result


def row_index(rows: list[dict], case_id: str) -> int:
    return next(index for index, row in enumerate(rows) if row["case_id"] == case_id)


def test_pass_a_rev1_bytes_and_distribution_are_preserved(pass_a_rev1) -> None:
    result = a2.validate_pass_a(ROOT, pass_a_rev1, source_path=a2.PASS_A_REV1)
    assert result["passed"], result["errors"]
    assert result["sha256"] == a2.PASS_A_EXPECTED_SHA256


def test_pass_a_v2_exact_replacement_boundary(fix2_audit) -> None:
    result = a2.validate_pass_a_v2(ROOT, fix2_audit)
    assert result["passed"], result["errors"]
    assert result["audit"]["unchanged_row_count"] == 57
    assert result["audit"]["all_57_unchanged_rows_canonical_and_raw_equal"] is True
    assert result["audit"]["retired_ids"] == sorted(a2.FIX2_RETIRED_IDS)
    assert result["audit"]["replacement_ids"] == sorted(a2.FIX2_REPLACEMENT_IDS)
    assert result["audit"]["distribution"] == a2.EXPECTED_DISTRIBUTION


def test_validator_accepts_structurally_complete_neutral_matrix(pass_a, neutral_matrix) -> None:
    result = a2.validate_pass_b(ROOT, pass_a, neutral_matrix)
    assert result["passed"], result["errors"][:10]
    assert result["row_count"] == result["unique_pairs"] == 3120


def test_rev1_active_pass_b_is_rejected_as_new_semantic_proof(pass_a) -> None:
    rev1 = a2.read_jsonl(ROOT / a2.REV1_PASS_B_HISTORY)
    result = a2.validate_pass_b(ROOT, pass_a, rev1)
    assert not result["passed"]
    assert any("missing_fields" in error for error in result["errors"])


def test_nonverbatim_support_quote_fails(pass_a, neutral_matrix) -> None:
    index = row_index(neutral_matrix, "EV2-A2-S01")
    obligation = pass_a[0]["required_semantic_obligations"][0]
    rows = mutate(neutral_matrix, index, target_match=True, state_match=True, dimension_match=True,
                  obligations_covered=[obligation], obligations_not_covered=[], support_class="COMPLETE_SUPPORT",
                  obligation_support_quotes={obligation: ["not present in the frozen clause"]})
    result = a2.validate_pass_b(ROOT, pass_a, rows)
    assert any("nonverbatim_support_quote" in error for error in result["errors"])


def test_covered_obligation_without_quote_fails(pass_a, neutral_matrix) -> None:
    index = row_index(neutral_matrix, "EV2-A2-S01")
    obligation = pass_a[0]["required_semantic_obligations"][0]
    rows = mutate(neutral_matrix, index, target_match=True, state_match=True, dimension_match=True,
                  obligations_covered=[obligation], obligations_not_covered=[], support_class="COMPLETE_SUPPORT",
                  obligation_support_quotes={})
    result = a2.validate_pass_b(ROOT, pass_a, rows)
    assert any("covered_obligation_quote_keys" in error for error in result["errors"])


def test_quote_from_different_section_fails(pass_a, neutral_matrix) -> None:
    index = row_index(neutral_matrix, "EV2-A2-S01")
    obligation = pass_a[0]["required_semantic_obligations"][0]
    rows = mutate(neutral_matrix, index, target_match=True, state_match=True, dimension_match=True,
                  obligations_covered=[obligation], obligations_not_covered=[], support_class="COMPLETE_SUPPORT",
                  obligation_support_quotes={obligation: ["A pending transfer is accepted for processing but has not completed."]})
    result = a2.validate_pass_b(ROOT, pass_a, rows)
    assert any("nonverbatim_support_quote" in error for error in result["errors"])


def test_target_match_with_target_contradiction_fails(pass_a, neutral_matrix) -> None:
    section = a2.eligible_section_index(ROOT)[0][neutral_matrix[0]["evidence_id"]]
    rows = mutate(neutral_matrix, 0, target_match=True, support_class="CONTRADICTION",
                  contradiction_basis_quote=section["content"], contradicted_constraint="TARGET:MERCHANT_CARD_PAYMENT")
    result = a2.validate_pass_b(ROOT, pass_a, rows)
    assert any("target_match_with_target_contradiction" in error for error in result["errors"])


def test_state_match_with_state_contradiction_fails(pass_a, neutral_matrix) -> None:
    section = a2.eligible_section_index(ROOT)[0][neutral_matrix[0]["evidence_id"]]
    rows = mutate(neutral_matrix, 0, state_match=True, support_class="CONTRADICTION",
                  contradiction_basis_quote=section["content"], contradicted_constraint="STATE:DECLINED")
    result = a2.validate_pass_b(ROOT, pass_a, rows)
    assert any("state_match_with_state_contradiction" in error for error in result["errors"])


def test_complete_support_omitting_obligation_fails(pass_a, neutral_matrix) -> None:
    index = row_index(neutral_matrix, "EV2-A2-S02")
    case = next(row for row in pass_a if row["case_id"] == "EV2-A2-S02")
    covered, missing = case["required_semantic_obligations"]
    section = a2.eligible_section_index(ROOT)[0][neutral_matrix[index]["evidence_id"]]
    rows = mutate(neutral_matrix, index, target_match=True, state_match=True, dimension_match=True,
                  obligations_covered=[covered], obligations_not_covered=[missing], support_class="COMPLETE_SUPPORT",
                  obligation_support_quotes={covered: [section["content"]]})
    result = a2.validate_pass_b(ROOT, pass_a, rows)
    assert any("invalid_complete_support" in error for error in result["errors"])


def test_same_domain_cannot_be_auto_contradiction_without_quote(pass_a, neutral_matrix) -> None:
    rows = mutate(neutral_matrix, 0, support_class="CONTRADICTION")
    result = a2.validate_pass_b(ROOT, pass_a, rows)
    assert any("nonverbatim_or_missing_contradiction_quote" in error for error in result["errors"])


@pytest.mark.parametrize("field", ["semantic_stratum", "expected_production_route", "candidate_output"])
def test_forbidden_desired_or_candidate_field_in_pass_b_fails(pass_a, neutral_matrix, field) -> None:
    rows = mutate(neutral_matrix, 0, **{field: "forbidden"})
    result = a2.validate_pass_b(ROOT, pass_a, rows)
    assert any("forbidden_fields" in error for error in result["errors"])


def test_content_hash_drift_fails(pass_a, neutral_matrix) -> None:
    rows = mutate(neutral_matrix, 0, evidence_content_sha256="0" * 64)
    result = a2.validate_pass_b(ROOT, pass_a, rows)
    assert any("evidence_content_sha256_mismatch" in error for error in result["errors"])


def test_pass_c_preselected_evidence_is_not_accepted(pass_a, neutral_matrix) -> None:
    derived, _ = a2.derive_pass_c(ROOT, pass_a, neutral_matrix)
    forged = [dict(row) for row in derived]
    forged[0]["acceptable_complete_support_sets"] = [[neutral_matrix[0]["evidence_id"]]]
    result = a2.validate_pass_c_exact(ROOT, pass_a, neutral_matrix, forged)
    assert not result["passed"]
    assert "pass_c_not_exact_mechanical_derivation" in result["errors"]


def test_hard_abstain_is_not_proved_by_absent_plan() -> None:
    case = {"required_semantic_obligations": ["O1"]}
    judgment = {"evidence_id": "E1", "support_class": "COMPLETE_SUPPORT", "target_match": True,
                "state_match": True, "dimension_match": True, "obligations_covered": ["O1"]}
    assert a2.derive_minimal_complete_sets(case, [judgment]) == [["E1"]]


def test_minimal_derivation_removes_supersets() -> None:
    case = {"required_semantic_obligations": ["O1", "O2"]}
    rows = [
        {"evidence_id": "E1", "support_class": "COMPLETE_SUPPORT", "target_match": True, "state_match": True, "dimension_match": True, "obligations_covered": ["O1", "O2"]},
        {"evidence_id": "E2", "support_class": "PARTIAL_SUPPORT", "target_match": True, "state_match": True, "dimension_match": True, "obligations_covered": ["O1"]},
        {"evidence_id": "E3", "support_class": "PARTIAL_SUPPORT", "target_match": True, "state_match": True, "dimension_match": True, "obligations_covered": ["O2"]},
    ]
    assert a2.derive_minimal_complete_sets(case, rows) == [["E1"], ["E2", "E3"]]


def test_lineage_zero_consumed_collision_without_source_fails() -> None:
    audit = {"consumed_per_query_collision_status": {"status": "ESTABLISHED", "value": 0}}
    result = a2.validate_lineage_audit(audit)
    assert not result["passed"]
    assert "unsupported_zero_consumed_collision_claim" in result["errors"]


def test_lineage_audit_uses_evidence_or_not_established(pass_a) -> None:
    audit = a2.compute_lineage_audit(ROOT, pass_a)
    assert audit["a1_dev_family_collisions"]["status"] == "ESTABLISHED"
    assert audit["a1_dev_family_collisions"]["value"] == 0
    assert audit["rm2_dev_template_reuse"]["status"] == "NOT_ESTABLISHED"
    assert audit["consumed_per_query_collision_status"]["status"] == "NOT_ESTABLISHED_PENDING_A3_FINGERPRINT_ONLY_AUDIT"
    assert a2.validate_lineage_audit(audit)["passed"]


def test_script_has_no_semantic_authoring_or_candidate_execution_path() -> None:
    source = (ROOT / "scripts/evaluation/week3_ev2_a2.py").read_text(encoding="utf-8").lower()
    assert "support_plans" not in source
    assert "preselected_support_sets" not in source
    assert "run_case_v3" not in source
    assert "routing_v3" not in source
    assert "pipeline_v3" not in source
    assert source.count("write_jsonl(root / pass_b, post_fix_rows)") == 1
    assert source.count("write_jsonl(root / pass_b, current)") == 1
    assert source.count("write_jsonl(root / pass_b, final_rows)") == 1
    stripped = source.replace("write_jsonl(root / pass_b, post_fix_rows)", "")
    stripped = stripped.replace("write_jsonl(root / pass_b, current)", "")
    stripped = stripped.replace("write_jsonl(root / pass_b, final_rows)", "")
    assert "write_jsonl(root / pass_b," not in stripped


def test_fix1b_exact_artifacts_validate(pass_a_rev1, fix1b_judgments, fix1b_case_review, fix1b_summary) -> None:
    result = a2.validate_fix1b_artifacts(ROOT, pass_a_rev1, fix1b_judgments, fix1b_case_review, fix1b_summary)
    assert result["passed"], result["errors"]
    assert result["matrix"]["row_count"] == result["matrix"]["unique_pairs"] == 624
    assert set(result["matrix"]["per_case_counts"].values()) == {52}
    assert result["conflicted_hard_cases"] == ["EV2-A2-H05", "EV2-A2-H06", "EV2-A2-H08"]


def test_fix1b_fake_safe_alternative_quote_fails(pass_a_rev1, fix1b_judgments) -> None:
    rows = copy.deepcopy(fix1b_judgments)
    index = next(i for i, row in enumerate(rows) if row["case_id"] == "EV2-A2-H05" and row["safe_alternative_quotes"])
    rows[index]["safe_alternative_quotes"] = ["fabricated safe alternative quote"]
    result = a2.validate_fix1b_judgments(ROOT, pass_a_rev1, rows)
    assert any("nonverbatim_safe_alternative_quote" in error for error in result["errors"])


def test_fix1b_missing_section_fails(pass_a_rev1, fix1b_judgments) -> None:
    result = a2.validate_fix1b_judgments(ROOT, pass_a_rev1, fix1b_judgments[:-1])
    assert "case_evidence_pair_set_not_exact" in result["errors"]
    assert "not_exactly_52_judgments_per_hard_case" in result["errors"]


def test_fix1b_duplicate_pair_fails(pass_a_rev1, fix1b_judgments) -> None:
    rows = [*fix1b_judgments, copy.deepcopy(fix1b_judgments[0])]
    result = a2.validate_fix1b_judgments(ROOT, pass_a_rev1, rows)
    assert "duplicate_case_evidence_pair" in result["errors"]


def test_fix1b_unsupported_complete_set_fails(pass_a_rev1, fix1b_judgments, fix1b_case_review, fix1b_summary) -> None:
    review = copy.deepcopy(fix1b_case_review)
    case = next(row for row in review["cases"] if row["case_id"] == "EV2-A2-H04")
    case["minimal_complete_safe_alternative_sets"] = [["FAQ_TRANSFER_PENDING_001#answer"]]
    case["complete_safe_alternative_exists"] = True
    result = a2.validate_fix1b_artifacts(ROOT, pass_a_rev1, fix1b_judgments, review, fix1b_summary)
    assert "case_level_conclusions_not_exact_derivation" in result["errors"]


def test_fix1b_inconsistent_conflict_flag_fails(pass_a_rev1, fix1b_judgments, fix1b_case_review, fix1b_summary) -> None:
    review = copy.deepcopy(fix1b_case_review)
    case = next(row for row in review["cases"] if row["case_id"] == "EV2-A2-H05")
    case["stratum_conflict"] = False
    case["frozen_reason_valid"] = True
    result = a2.validate_fix1b_artifacts(ROOT, pass_a_rev1, fix1b_judgments, review, fix1b_summary)
    assert "case_level_conclusions_not_exact_derivation" in result["errors"]


def test_fix1b_frozen_reason_rewrite_fails(pass_a_rev1, fix1b_judgments, fix1b_case_review) -> None:
    review = copy.deepcopy(fix1b_case_review)
    case = next(row for row in review["cases"] if row["case_id"] == "EV2-A2-H05")
    case["frozen_reason_family"] = "NO_APPROVED_COMPLETE_SUPPORT"
    with pytest.raises(ValueError, match="frozen_reason_silently_rewritten"):
        a2.derive_fix1b_case_reviews(pass_a_rev1, fix1b_judgments, review)


def test_fix1b_candidate_field_leakage_fails(pass_a_rev1, fix1b_judgments) -> None:
    rows = copy.deepcopy(fix1b_judgments)
    rows[0]["candidate_output"] = "forbidden"
    result = a2.validate_fix1b_judgments(ROOT, pass_a_rev1, rows)
    assert any("forbidden_fields" in error for error in result["errors"])


def test_fix2_exact_artifacts_validate(pass_a_v2, fix2_ledger, fix2_judgments, fix2_case_review, fix2_audit) -> None:
    pass_a_result = a2.validate_pass_a_v2(ROOT, fix2_audit)
    ledger_result = a2.validate_fix2_ledger(ROOT, fix2_ledger)
    matrix = a2.validate_fix2_judgments(ROOT, pass_a_v2, fix2_judgments)
    derived = a2.derive_fix2_case_reviews(pass_a_v2, fix2_judgments, fix2_case_review)
    assert pass_a_result["passed"], pass_a_result["errors"]
    assert ledger_result["passed"], ledger_result["errors"]
    assert matrix["passed"], matrix["errors"]
    assert matrix["row_count"] == matrix["unique_pairs"] == 156
    assert set(matrix["per_case_counts"].values()) == {52}
    assert fix2_case_review["cases"] == derived
    assert {row["replacement_verdict"] for row in derived} == {"PASS"}


def test_fix2_fake_safe_quote_fails(pass_a_v2, fix2_judgments) -> None:
    rows = copy.deepcopy(fix2_judgments)
    index = next(i for i, row in enumerate(rows) if row["safe_alternative_quotes"])
    rows[index]["safe_alternative_quotes"] = ["fabricated FIX2 quote"]
    result = a2.validate_fix2_judgments(ROOT, pass_a_v2, rows)
    assert any("nonverbatim_safe_alternative_quote" in error for error in result["errors"])


def test_fix2_missing_section_fails(pass_a_v2, fix2_judgments) -> None:
    result = a2.validate_fix2_judgments(ROOT, pass_a_v2, fix2_judgments[:-1])
    assert "replacement_case_evidence_pair_set_not_exact" in result["errors"]
    assert "not_exactly_52_judgments_per_replacement" in result["errors"]


def test_fix2_duplicate_pair_fails(pass_a_v2, fix2_judgments) -> None:
    rows = [*fix2_judgments, copy.deepcopy(fix2_judgments[0])]
    result = a2.validate_fix2_judgments(ROOT, pass_a_v2, rows)
    assert "duplicate_case_evidence_pair" in result["errors"]


def test_fix2_evidence_hash_drift_fails(pass_a_v2, fix2_judgments) -> None:
    rows = copy.deepcopy(fix2_judgments)
    rows[0]["evidence_content_sha256"] = "0" * 64
    result = a2.validate_fix2_judgments(ROOT, pass_a_v2, rows)
    assert any("evidence_content_sha256_mismatch" in error for error in result["errors"])


def test_fix2_candidate_field_leakage_fails(pass_a_v2, fix2_judgments) -> None:
    rows = copy.deepcopy(fix2_judgments)
    rows[0]["candidate_prediction"] = "forbidden"
    result = a2.validate_fix2_judgments(ROOT, pass_a_v2, rows)
    assert any("forbidden_fields" in error for error in result["errors"])


def test_fix2_failed_replacement_cannot_be_silently_rewritten(
    pass_a_v2, fix2_ledger, fix2_judgments, fix2_case_review, fix2_audit,
) -> None:
    review = copy.deepcopy(fix2_case_review)
    case = next(row for row in review["cases"] if row["case_id"] == "EV2-A2-H05-R1")
    case["replacement_verdict"] = "FAIL"
    case["hard_reason_valid"] = False
    derived = a2.derive_fix2_case_reviews(pass_a_v2, fix2_judgments, review)
    assert review["cases"] != derived


def test_fix2_hard_reason_family_cannot_change_after_review(pass_a_v2, fix2_judgments, fix2_case_review) -> None:
    review = copy.deepcopy(fix2_case_review)
    case = next(row for row in review["cases"] if row["case_id"] == "EV2-A2-H06-R1")
    case["frozen_reason_family"] = "NO_APPROVED_COMPLETE_SUPPORT"
    with pytest.raises(ValueError, match="hard_reason_family_changed_after_review_began"):
        a2.derive_fix2_case_reviews(pass_a_v2, fix2_judgments, review)


def test_fix2_replacement_row_cannot_change_after_review(pass_a_v2, fix2_judgments, fix2_case_review) -> None:
    rows = copy.deepcopy(pass_a_v2)
    case = next(row for row in rows if row["case_id"] == "EV2-A2-H08-R1")
    case["query"] += " changed"
    with pytest.raises(ValueError, match="replacement_row_changed_after_review_began"):
        a2.derive_fix2_case_reviews(rows, fix2_judgments, fix2_case_review)


def test_fix2_pass_a_has_no_support_membership_or_candidate_data(pass_a_v2) -> None:
    forbidden = {"evidence_id", "support_set", "support_sets", "selected_evidence", "candidate_output", "candidate_route"}
    replacements = [row for row in pass_a_v2 if row["case_id"] in a2.FIX2_REPLACEMENT_IDS]
    assert len(replacements) == 3
    assert all(not (forbidden & set(row)) for row in replacements)


def test_fix2_does_not_emit_full_pass_b_or_pass_c() -> None:
    assert a2.file_sha256(ROOT / a2.REV1_PASS_B_HISTORY) == a2.REV1_PASS_B_SHA256
    assert a2.file_sha256(ROOT / a2.REV1_PASS_C_HISTORY) == a2.REV1_PASS_C_SHA256


def test_fix2_preserves_fix1b_artifact_hashes() -> None:
    assert a2.file_sha256(ROOT / a2.FIX1B_JUDGMENTS) == "8dc263538c3822b45a4809d6204b1ce3a14880a8972096bf874bc0e281f2ee9b"
    assert a2.file_sha256(ROOT / a2.FIX1B_CASE_REVIEW) == "86fa10ba21f619257926a3f6c89b92168d7ea25319c69a5077dcbde8af395099"
    assert a2.file_sha256(ROOT / a2.FIX1B_CONFLICT_SUMMARY) == "d51c1af63a9746c4f7536e192a03fbcc1da7f6985cdc132a1fc79d9cf4f2523f"


def test_fix2_consumed_case_level_and_candidate_execution_paths_absent() -> None:
    source = (ROOT / "scripts/evaluation/week3_ev2_a2.py").read_text(encoding="utf-8").lower()
    assert "critical_eval_v2_cases" not in source
    assert "grounded_generation_eval_cases" not in source
    assert "run_case_v3" not in source
    assert "from payresolve_ai" not in source
    assert "import payresolve_ai" not in source


def test_fix2a_exact_artifacts_validate(
    pass_a_v2, fix2a_classification, fix2a_review, fix2a_summary,
) -> None:
    result = a2.validate_fix2a_artifacts(
        ROOT, pass_a_v2, fix2a_classification, fix2a_review, fix2a_summary,
    )
    assert result["passed"], result["errors"]
    assert result["reviewed_hard_cases"] == 12
    assert result["reused_judgments"] == 624
    assert result["conflicted_current_hard_cases"] == [
        "EV2-A2-H03", "EV2-A2-H04", "EV2-A2-H07", "EV2-A2-H08-R1", "EV2-A2-H09",
    ]
    assert result["replacement_count_required"] == 5


def test_fix2a_control_plane_boundary_must_not_require_kb_quote(
    pass_a_v2, fix2a_classification, fix2a_review, fix2a_summary,
) -> None:
    classification = copy.deepcopy(fix2a_classification)
    entry = next(
        row for row in classification["classifications"]
        if row["classification"] == "CONTROL_PLANE_BOUNDARY"
    )
    entry["requires_eligible_kb_support"] = True
    result = a2.validate_fix2a_artifacts(ROOT, pass_a_v2, classification, fix2a_review, fix2a_summary)
    assert any("control_plane_incorrectly_requires_kb_quote" in error for error in result["errors"])


def test_fix2a_factual_objective_cannot_be_accepted_without_exact_kb_support(
    pass_a_v2, fix2a_classification, fix2a_review, fix2a_summary,
) -> None:
    review = copy.deepcopy(fix2a_review)
    case = next(row for row in review["cases"] if row["case_id"] == "EV2-A2-H03")
    case["minimal_factual_corrective_support_sets"] = [["FAQ_TRANSFER_FAILED_001#answer"]]
    result = a2.validate_fix2a_artifacts(ROOT, pass_a_v2, fix2a_classification, review, fix2a_summary)
    assert any("factual_objective_accepted_without_exact_kb_support" in error for error in result["errors"])


def test_fix2a_one_case_cannot_use_different_rule_to_preserve_hard(
    pass_a_v2, fix2a_classification, fix2a_review, fix2a_summary,
) -> None:
    review = copy.deepcopy(fix2a_review)
    case = next(row for row in review["cases"] if row["case_id"] == "EV2-A2-H01")
    case["completeness_rule_id"] = "KEEP_HARD_12_DISTRIBUTION_RULE"
    result = a2.validate_fix2a_artifacts(ROOT, pass_a_v2, fix2a_classification, review, fix2a_summary)
    assert any("different_completeness_rule" in error for error in result["errors"])


def test_fix2a_unsupported_live_fact_cannot_be_treated_as_known(
    pass_a_v2, fix2a_classification, fix2a_review, fix2a_summary,
) -> None:
    review = copy.deepcopy(fix2a_review)
    case = next(row for row in review["cases"] if row["case_id"] == "EV2-A2-H08-R1")
    case["live_fact_treated_as_observed"] = True
    result = a2.validate_fix2a_artifacts(ROOT, pass_a_v2, fix2a_classification, review, fix2a_summary)
    assert any("unsupported_live_fact_treated_as_known" in error for error in result["errors"])


def test_fix2a_candidate_output_cannot_enter_audit(
    pass_a_v2, fix2a_classification, fix2a_review, fix2a_summary,
) -> None:
    review = copy.deepcopy(fix2a_review)
    review["cases"][0]["candidate_output"] = "forbidden"
    result = a2.validate_fix2a_artifacts(ROOT, pass_a_v2, fix2a_classification, review, fix2a_summary)
    assert any("forbidden_candidate_or_ranking_fields" in error for error in result["errors"])


def test_fix2a_evidence_cannot_reference_outside_fix1b_fix2(
    pass_a_v2, fix2a_classification, fix2a_review, fix2a_summary,
) -> None:
    review = copy.deepcopy(fix2a_review)
    case = next(row for row in review["cases"] if row["case_id"] == "EV2-A2-H03")
    case["source_judgment_artifact"]["path"] = "reports/week_03/results/unauthorized.jsonl"
    result = a2.validate_fix2a_artifacts(ROOT, pass_a_v2, fix2a_classification, review, fix2a_summary)
    assert any("evidence_referenced_outside_fix1b_fix2" in error for error in result["errors"])


def test_fix2a_pass_a_v2_change_fails(
    pass_a_v2, fix2a_classification, fix2a_review, fix2a_summary,
) -> None:
    changed = copy.deepcopy(pass_a_v2)
    case = next(row for row in changed if row["case_id"] == "EV2-A2-H03")
    case["query"] += " changed"
    result = a2.validate_fix2a_artifacts(
        ROOT, changed, fix2a_classification, fix2a_review, fix2a_summary,
    )
    assert any("current_hard_case_hash_mismatch" in error for error in result["errors"])


def test_fix2a_preserves_all_semantic_evidence_and_evaluation_bytes() -> None:
    expected = {
        a2.PASS_A_V2: a2.PASS_A_V2_EXPECTED_SHA256,
        a2.PASS_A_REV1: a2.PASS_A_EXPECTED_SHA256,
        a2.FIX1B_JUDGMENTS: a2.FIX1B_JUDGMENTS_SHA256,
        a2.FIX1B_CASE_REVIEW: a2.FIX1B_CASE_REVIEW_SHA256,
        a2.FIX1B_CONFLICT_SUMMARY: a2.FIX1B_CONFLICT_SUMMARY_SHA256,
        a2.FIX2_JUDGMENTS: a2.FIX2_JUDGMENTS_SHA256,
        a2.FIX2_CASE_REVIEW: a2.FIX2_CASE_REVIEW_SHA256,
        a2.FIX2_LEDGER: a2.FIX2_LEDGER_SHA256,
        a2.FIX2_PASS_A_AUDIT: a2.FIX2_PASS_A_AUDIT_SHA256,
        a2.REV1_PASS_B_HISTORY: a2.REV1_PASS_B_SHA256,
        a2.REV1_PASS_C_HISTORY: a2.REV1_PASS_C_SHA256,
    }
    assert {path: a2.file_sha256(ROOT / path) for path in expected} == expected


def _fix3_safe_seed(
    prerequisites: list[str] | None = None,
    correctives: list[str] | None = None,
) -> dict:
    return {
        "control_plane_boundary_allowed": True,
        "control_plane_boundary_requires_kb_support": False,
        "control_plane_boundary_makes_banking_factual_claim": False,
        "safe_alternative_prerequisite_objectives": prerequisites or ["P"],
        "safe_alternative_corrective_objectives": correctives or ["C"],
    }


def _fix3_safe_row(
    evidence_id: str,
    prerequisites: list[str] | None = None,
    correctives: list[str] | None = None,
    **changes,
) -> dict:
    row = {
        "evidence_id": evidence_id,
        "support_class": "CONTEXTUAL_INSUFFICIENT",
        "safe_alternative_prerequisite_obligations_supported": prerequisites or [],
        "safe_alternative_corrective_obligations_supported": correctives or [],
        "safe_alternative_target_compatible": True,
        "safe_alternative_state_compatible": True,
        "safe_alternative_prerequisite_contradicts_user_facts": False,
        "safe_alternative_silent_state_assumption": False,
        "safe_alternative_asserts_account_specific_fact": False,
        "evidence_supports_account_specific_fact": False,
        "forbidden_action_or_promise_introduced": False,
    }
    row.update(changes)
    return row


def test_fix3_exact_artifacts_validate(
    pass_a, fix3_ledger, fix3_judgments, fix3_case_review, fix3_audit,
) -> None:
    result = a2.validate_fix3_artifacts(
        ROOT, pass_a, fix3_ledger, fix3_judgments, fix3_case_review, fix3_audit,
    )
    assert result["passed"], result["errors"]
    assert result["status"] == a2.FIX3_INTERNAL_STATUS
    assert result["matrix"]["row_count"] == result["matrix"]["unique_pairs"] == 260
    assert set(result["matrix"]["per_case_counts"].values()) == {52}
    assert {row["replacement_verdict"] for row in result["derived_cases"]} == {"PASS"}


def test_fix3_pass_a_v3_exact_five_replacement_and_55_row_immutability(fix3_audit) -> None:
    result = a2.validate_pass_a_v3(ROOT, fix3_audit)
    assert result["passed"], result["errors"]
    assert result["audit"]["unchanged_row_count"] == 55
    assert result["audit"]["all_55_unchanged_rows_canonical_and_raw_equal"] is True
    assert result["audit"]["retired_ids"] == sorted(a2.FIX3_RETIRED_IDS)
    assert result["audit"]["replacement_ids"] == sorted(a2.FIX3_REPLACEMENT_IDS)
    assert min(result["audit"]["hard_reason_family_counts"].values()) >= 2


def test_fix3_missing_section_fails(pass_a, fix3_judgments, fix3_case_review) -> None:
    result = a2.validate_fix3_judgments(ROOT, pass_a, fix3_judgments[:-1], fix3_case_review)
    assert "fix3_case_evidence_pair_set_not_exact" in result["errors"]
    assert "fix3_not_exactly_52_judgments_per_replacement" in result["errors"]


def test_fix3_duplicate_pair_fails(pass_a, fix3_judgments, fix3_case_review) -> None:
    rows = [*fix3_judgments, copy.deepcopy(fix3_judgments[0])]
    result = a2.validate_fix3_judgments(ROOT, pass_a, rows, fix3_case_review)
    assert "duplicate_case_evidence_pair" in result["errors"]


def test_fix3_evidence_hash_drift_fails(pass_a, fix3_judgments, fix3_case_review) -> None:
    rows = copy.deepcopy(fix3_judgments)
    rows[0]["evidence_content_sha256"] = "0" * 64
    result = a2.validate_fix3_judgments(ROOT, pass_a, rows, fix3_case_review)
    assert any("evidence_content_sha256_mismatch" in error for error in result["errors"])


def test_fix3_action_objective_without_eligibility_prerequisite_is_incomplete() -> None:
    rows = [_fix3_safe_row("ACTION", correctives=["C"])]
    assert a2.derive_prerequisite_complete_safe_sets(_fix3_safe_seed(), rows) == []


def test_fix3_timing_objective_without_required_state_prerequisite_is_incomplete() -> None:
    seed = _fix3_safe_seed(["ELIGIBILITY", "REQUIRED_STATE"], ["TIMING"])
    rows = [_fix3_safe_row("TIMING", ["ELIGIBILITY"], ["TIMING"])]
    assert a2.derive_prerequisite_complete_safe_sets(seed, rows) == []


def test_fix3_same_domain_evidence_is_not_automatically_target_compatible() -> None:
    rows = [_fix3_safe_row(
        "SAME_DOMAIN", ["P"], ["C"], safe_alternative_target_compatible=False,
    )]
    assert a2.derive_prerequisite_complete_safe_sets(_fix3_safe_seed(), rows) == []


def test_fix3_generic_evidence_cannot_prove_account_specific_fact() -> None:
    rows = [_fix3_safe_row(
        "GENERIC", ["P"], ["C"],
        safe_alternative_asserts_account_specific_fact=True,
        evidence_supports_account_specific_fact=False,
    )]
    assert a2.derive_prerequisite_complete_safe_sets(_fix3_safe_seed(), rows) == []


def test_fix3_control_plane_boundary_must_not_require_kb_quote() -> None:
    seed = _fix3_safe_seed()
    seed["control_plane_boundary_requires_kb_support"] = True
    rows = [_fix3_safe_row("COMPLETE", ["P"], ["C"])]
    assert a2.derive_prerequisite_complete_safe_sets(seed, rows) == []


def test_fix3_factual_prerequisite_cannot_be_reclassified_as_control_plane(
    pass_a, fix3_judgments, fix3_case_review,
) -> None:
    review = copy.deepcopy(fix3_case_review)
    case = next(row for row in review["cases"] if row["case_id"] == "EV2-A2-H07-R1")
    prerequisite = case["safe_alternative_prerequisite_objectives"].pop()
    case["control_plane_boundary_obligations"].append(prerequisite)
    with pytest.raises(ValueError, match="factual_prerequisite_treated_as_control_plane_or_changed"):
        a2.derive_fix3_case_reviews(pass_a, fix3_judgments, review)


def test_fix3_contradictory_prerequisite_evidence_cannot_enter_complete_set() -> None:
    rows = [_fix3_safe_row(
        "CONTRADICTION", ["P"], ["C"], support_class="CONTRADICTION",
        safe_alternative_prerequisite_contradicts_user_facts=True,
    )]
    assert a2.derive_prerequisite_complete_safe_sets(_fix3_safe_seed(), rows) == []


def test_fix3_minimal_complete_sets_do_not_return_supersets() -> None:
    rows = [
        _fix3_safe_row("E1", ["P"], ["C"]),
        _fix3_safe_row("E2", ["P"], []),
    ]
    assert a2.derive_prerequisite_complete_safe_sets(_fix3_safe_seed(), rows) == [["E1"]]


def test_fix3_candidate_output_cannot_influence_completeness(
    pass_a, fix3_judgments, fix3_case_review,
) -> None:
    rows = copy.deepcopy(fix3_judgments)
    rows[0]["candidate_output"] = "forbidden"
    result = a2.validate_fix3_judgments(ROOT, pass_a, rows, fix3_case_review)
    assert any("forbidden_fields" in error for error in result["errors"])


def test_fix3_does_not_emit_full_pass_b_or_pass_c() -> None:
    assert a2.file_sha256(ROOT / a2.REV1_PASS_B_HISTORY) == a2.REV1_PASS_B_SHA256
    assert a2.file_sha256(ROOT / a2.REV1_PASS_C_HISTORY) == a2.REV1_PASS_C_SHA256


@pytest.fixture(scope="module")
def pb1_classification() -> list[dict]:
    return a2.read_jsonl(ROOT / a2.OBLIGATION_CLASSIFICATION)


@pytest.fixture(scope="module")
def pb1_pass_b() -> list[dict]:
    return a2.read_jsonl(ROOT / a2.PASS_B)


@pytest.fixture(scope="module")
def pb1_pass_c() -> list[dict]:
    return a2.read_jsonl(ROOT / a2.PASS_C)


def _pb1_json(path: Path) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_pb1_exact_package_validates() -> None:
    result = fix2b.validate_fix2b(ROOT)
    assert result["passed"], result["errors"][:20]
    assert result["pass_b_rows"] == 3120
    assert result["pass_c_rows"] == 60


def test_pb1_pass_a_v3_exact_sha_and_distribution(pass_a) -> None:
    assert a2.file_sha256(ROOT / a2.PASS_A) == a2.PASS_A_V3_EXPECTED_SHA256
    assert Counter(row["semantic_stratum"] for row in pass_a) == Counter(a2.EXPECTED_DISTRIBUTION)


def test_pb1_obligation_classification_is_complete(pass_a, pb1_classification) -> None:
    result = a2.validate_pb1_obligation_classification(pass_a, pb1_classification)
    assert result["passed"], result["errors"]
    assert result["row_count"] == sum(len(row["required_semantic_obligations"]) for row in pass_a) == 104


def test_pb1_factual_obligation_cannot_be_reclassified_as_control_plane(pass_a, pb1_classification) -> None:
    rows = copy.deepcopy(pb1_classification)
    entry = next(row for row in rows if row["classification"] == "KB_FACTUAL_PREREQUISITE")
    entry["classification"] = "CONTROL_PLANE_BOUNDARY"
    entry["kb_support_required"] = False
    result = a2.validate_pb1_obligation_classification(pass_a, rows)
    assert any("classification_not_semantically_frozen" in error for error in result["errors"])


def test_pb1_matrix_exact_pairs_hashes_quotes_and_no_leakage(pass_a, pb1_classification, pb1_pass_b) -> None:
    result = a2.validate_pb1_pass_b(ROOT, pass_a, pb1_classification, pb1_pass_b)
    assert result["passed"], result["errors"][:20]
    assert set(result["per_case_counts"].values()) == {52}
    assert result["reused_semantic_rows"] == 624
    assert result["new_semantic_rows"] == 2496


def test_pb1_reuse_sources_are_exact_and_zero_semantic_mutation(pb1_pass_b) -> None:
    imports = [row for row in pb1_pass_b if row["review_provenance"] == a2.PB1_IMPORT_PROVENANCE]
    assert len(imports) == 624
    assert all(row["canonical_import_semantic_mutation"] is False for row in imports)
    assert Counter(row["canonical_import_source"] for row in imports) == Counter({
        str(a2.FIX1B_JUDGMENTS).replace("\\", "/"): 260,
        str(a2.FIX2_JUDGMENTS).replace("\\", "/"): 104,
        str(a2.FIX3_JUDGMENTS).replace("\\", "/"): 260,
    })


def test_pb1_reused_artifact_hashes_remain_frozen() -> None:
    assert a2.file_sha256(ROOT / a2.FIX1B_JUDGMENTS) == a2.FIX1B_JUDGMENTS_SHA256
    assert a2.file_sha256(ROOT / a2.FIX2_JUDGMENTS) == a2.FIX2_JUDGMENTS_SHA256
    assert a2.file_sha256(ROOT / a2.FIX3_JUDGMENTS) == "2f96d89bf70cef4d3e084a1a1844640ca11a11fbf562fdcc6a5220a493323ebb"


def test_pb1_complete_single_section_requires_full_factual_coverage(pass_a, pb1_classification, pb1_pass_b) -> None:
    rows = copy.deepcopy(pb1_pass_b)
    index = next(i for i, row in enumerate(rows) if row["case_id"] == "EV2-A2-S02" and row["support_class"] == "PARTIAL_SUPPORT")
    rows[index]["support_class"] = "COMPLETE_SUPPORT"
    result = a2.validate_pb1_pass_b(ROOT, pass_a, pb1_classification, rows)
    assert any("invalid_complete_support" in error for error in result["errors"])


def test_pb1_partial_support_requires_genuine_strict_subset(pass_a, pb1_classification, pb1_pass_b) -> None:
    rows = copy.deepcopy(pb1_pass_b)
    index = next(i for i, row in enumerate(rows) if row["case_id"] == "EV2-A2-S02" and row["support_class"] == "PARTIAL_SUPPORT")
    rows[index]["obligations_covered"] = list(rows[index]["kb_support_required_obligations"])
    rows[index]["obligations_not_covered"] = []
    section = a2.eligible_section_index(ROOT)[0][rows[index]["evidence_id"]]["content"]
    rows[index]["support_quotes_by_obligation"] = {item: [section] for item in rows[index]["obligations_covered"]}
    result = a2.validate_pb1_pass_b(ROOT, pass_a, pb1_classification, rows)
    assert any("invalid_partial_support" in error for error in result["errors"])


def test_pb1_contradiction_requires_exact_quote(pass_a, pb1_classification, pb1_pass_b) -> None:
    rows = copy.deepcopy(pb1_pass_b)
    index = next(i for i, row in enumerate(rows) if row["support_class"] == "CONTRADICTION")
    rows[index]["contradiction_basis_quote"] = "fabricated conflict"
    result = a2.validate_pb1_pass_b(ROOT, pass_a, pb1_classification, rows)
    assert any("nonverbatim_or_missing_contradiction_quote" in error for error in result["errors"])


def test_pb1_minimal_sets_remove_strict_supersets() -> None:
    rows = [
        {"evidence_id": "A", "support_class": "COMPLETE_SUPPORT", "target_match": True, "state_match": True, "dimension_match": True, "obligations_covered": ["O1", "O2"]},
        {"evidence_id": "B", "support_class": "PARTIAL_SUPPORT", "target_match": True, "state_match": True, "dimension_match": True, "obligations_covered": ["O1"]},
        {"evidence_id": "C", "support_class": "PARTIAL_SUPPORT", "target_match": True, "state_match": True, "dimension_match": True, "obligations_covered": ["O2"]},
    ]
    assert a2.derive_pb1_minimal_complete_sets(["O1", "O2"], rows) == [["A"], ["B", "C"]]


def test_pb1_target_or_state_mismatch_cannot_complete_support() -> None:
    row = {"evidence_id": "SAME_DOMAIN", "support_class": "COMPLETE_SUPPORT", "target_match": False, "state_match": True, "dimension_match": True, "obligations_covered": ["O"]}
    assert a2.derive_pb1_minimal_complete_sets(["O"], [row]) == []
    row["target_match"] = True
    row["state_match"] = False
    assert a2.derive_pb1_minimal_complete_sets(["O"], [row]) == []


def test_pb1_prerequisite_precedes_action_or_retry(pb1_pass_c) -> None:
    case = next(row for row in pb1_pass_c if row["case_id"] == "EV2-A2-S16")
    assert ["POL_TRANSFER_FAILED_001#retry_rule"] in case["acceptable_complete_support_sets"]
    assert ["RUN_TRANSFER_FAILED_001#action", "RUN_TRANSFER_FAILED_001#checks"] in case["acceptable_complete_support_sets"]


def test_pb1_generic_evidence_never_proves_account_specific_hard_fact(pb1_pass_b, pb1_pass_c) -> None:
    hard = [row for row in pb1_pass_c if row["expected_production_route"] == "ABSTAIN_ESCALATE" and row["case_id"].startswith("EV2-A2-H")]
    assert len(hard) == 12
    assert all(not row["acceptable_complete_support_sets"] and not row["complete_approved_support_exists_in_kb"] for row in hard)
    assert not any(row["support_class"] in {"COMPLETE_SUPPORT", "PARTIAL_SUPPORT"} for row in pb1_pass_b if row["case_id"].startswith("EV2-A2-H"))


def test_pb1_all_stratum_proof_counts_are_exact() -> None:
    result = a2.validate_pb1_package(ROOT)["stratum_proofs"]
    assert result["passed"], result["errors"]
    assert (result["standard_valid"], result["safe_corrective_valid"], result["hard_valid"], result["ambiguous_valid"]) == (24, 18, 12, 6)


def test_pb1_ambiguous_routes_are_semantically_derived(pb1_pass_c) -> None:
    routes = {row["case_id"]: row["expected_production_route"] for row in pb1_pass_c if row["case_id"].startswith("EV2-A2-A")}
    assert routes == {
        "EV2-A2-A01": "ABSTAIN_ESCALATE", "EV2-A2-A02": "ABSTAIN_ESCALATE",
        "EV2-A2-A03": "SAFE_CORRECTIVE", "EV2-A2-A04": "ABSTAIN_ESCALATE",
        "EV2-A2-A05": "ABSTAIN_ESCALATE", "EV2-A2-A06": "SAFE_CORRECTIVE",
    }
    assert "CLARIFY" not in routes.values()


def test_pb1_ineligible_draft_expired_never_supports(pb1_pass_c) -> None:
    ineligible = set(a2.eligible_section_index(ROOT)[1])
    assert ineligible
    assert all(not (set(row["allowed_supporting_evidence"]) & ineligible) for row in pb1_pass_c)


def test_pb1_pass_c_is_exact_deterministic_regeneration(pass_a, pb1_classification, pb1_pass_b, pb1_pass_c) -> None:
    derived = a2.derive_pb1_pass_c(
        ROOT, pass_a, pb1_classification, pb1_pass_b,
        _pb1_json(a2.INELIGIBLE_EVIDENCE_AUDIT),
    )
    assert derived == pb1_pass_c


def test_pb1_pass_c_derivation_fails_closed_on_invalid_pass_b(pass_a, pb1_classification, pb1_pass_b) -> None:
    rows = copy.deepcopy(pb1_pass_b)
    rows.pop()
    with pytest.raises(ValueError, match="A2_PB1_PASS_A_V3_STRATUM_CONFLICT"):
        a2.derive_pb1_pass_c_fail_closed(
            ROOT, pass_a, pb1_classification, rows,
            _pb1_json(a2.INELIGIBLE_EVIDENCE_AUDIT),
            _pb1_json(a2.POSITIVE_SUPPORT_AUDIT), _pb1_json(a2.SAFE_CORRECTIVE_PROOFS),
            _pb1_json(a2.HARD_ABSTAIN_PROOFS), _pb1_json(a2.AMBIGUOUS_DERIVATION),
        )


def test_pb1_no_candidate_inference_or_consumed_case_access_path() -> None:
    source = (ROOT / "scripts/evaluation/week3_ev2_a2.py").read_text(encoding="utf-8").lower()
    assert "run_case_v3" not in source
    assert "from payresolve_ai" not in source
    assert "import payresolve_ai" not in source
    assert "critical_eval_v2_cases" not in source
    assert "grounded_generation_eval_cases" not in source


def test_pb1_rev1_invalid_history_is_byte_preserved() -> None:
    assert a2.file_sha256(ROOT / a2.REV1_PASS_B_HISTORY) == a2.REV1_PASS_B_SHA256
    assert a2.file_sha256(ROOT / a2.REV1_PASS_C_HISTORY) == a2.REV1_PASS_C_SHA256


def _validate_fix1_rows(rows: list[dict], *, ledger: dict | None = None) -> dict:
    return a2.validate_pb1_fix1_semantic_audit(
        ROOT, rows, ledger or _pb1_json(a2.PB1_FIX1_LEDGER),
        _pb1_json(a2.PB1_FIX1_AUDIT_SUMMARY),
    )


def test_pb1_fix1_rejects_s19_checks_false_route_entailment(pb1_pass_b) -> None:
    rows = copy.deepcopy(pb1_pass_b)
    row = next(item for item in rows if item["case_id"] == "EV2-A2-S19" and item["evidence_id"] == "RUN_TRANSFER_PENDING_001#checks")
    row["support_class"] = "PARTIAL_SUPPORT"
    row["dimension_match"] = True
    row["obligations_covered"] = ["ROUTE_MASKED_PENDING_REVIEW"]
    row["obligations_not_covered"] = ["STATE_PENDING_WINDOW"]
    row["support_quotes_by_obligation"] = {"ROUTE_MASKED_PENDING_REVIEW": [a2.eligible_section_index(ROOT)[0][row["evidence_id"]]["content"]]}
    result = _validate_fix1_rows(rows)
    assert any("s19_checks_false_route_entailment" in error for error in result["errors"])


def test_pb1_fix1_rejects_verbatim_quote_without_semantic_entailment(pb1_pass_b) -> None:
    rows = copy.deepcopy(pb1_pass_b)
    row = next(item for item in rows if item["case_id"] == "EV2-A2-S14" and item["evidence_id"] == "RUN_TRANSFER_DECLINED_001#action")
    row["support_class"] = "COMPLETE_SUPPORT"
    row["obligations_covered"] = ["PROVIDE_SAFE_DECLINE_MESSAGE"]
    row["obligations_not_covered"] = []
    row["support_quotes_by_obligation"] = {"PROVIDE_SAFE_DECLINE_MESSAGE": [a2.eligible_section_index(ROOT)[0][row["evidence_id"]]["content"]]}
    result = _validate_fix1_rows(rows)
    assert "pb1_fix1_semantic_audit_decision_hash_mismatch" in result["errors"]


def test_pb1_fix1_masked_review_does_not_satisfy_safe_message(pb1_pass_b) -> None:
    rows = copy.deepcopy(pb1_pass_b)
    row = next(item for item in rows if item["case_id"] == "EV2-A2-C09" and item["evidence_id"] == "POL_TRANSFER_DECLINED_001#review_rule")
    row["support_class"] = "COMPLETE_SUPPORT"
    row["obligations_covered"] = ["PROVIDE_SAFE_DECLINE_MESSAGE", "PROVIDE_MASKED_REVIEW"]
    row["obligations_not_covered"] = []
    quote = a2.eligible_section_index(ROOT)[0][row["evidence_id"]]["content"]
    row["support_quotes_by_obligation"] = {item: [quote] for item in row["obligations_covered"]}
    result = _validate_fix1_rows(rows)
    assert "c09_masked_review_false_safe_message_entailment" in result["errors"]


def test_pb1_fix1_topic_relevance_cannot_promote_contextual_to_partial(pb1_pass_b) -> None:
    rows = copy.deepcopy(pb1_pass_b)
    row = next(item for item in rows if item["case_id"] == "EV2-A2-S19" and item["evidence_id"] == "FAQ_TRANSFER_PENDING_001#answer")
    row["support_class"] = "PARTIAL_SUPPORT"
    row["dimension_match"] = True
    row["obligations_covered"] = ["STATE_PENDING_WINDOW"]
    row["obligations_not_covered"] = ["ROUTE_MASKED_PENDING_REVIEW"]
    row["support_quotes_by_obligation"] = {"STATE_PENDING_WINDOW": [a2.eligible_section_index(ROOT)[0][row["evidence_id"]]["content"]]}
    result = _validate_fix1_rows(rows)
    assert "pb1_fix1_semantic_audit_decision_hash_mismatch" in result["errors"]


def test_pb1_fix1_same_domain_different_state_is_not_automatic_contradiction(pb1_pass_b) -> None:
    rows = copy.deepcopy(pb1_pass_b)
    row = next(item for item in rows if item["case_id"] == "EV2-A2-S14" and item["evidence_id"] == "POL_TRANSFER_DECLINED_001#review_rule")
    row["support_class"] = "CONTRADICTION"
    row["state_match"] = False
    row["contradiction_basis_quote"] = a2.eligible_section_index(ROOT)[0][row["evidence_id"]]["content"]
    row["contradicted_constraint"] = "STATE:DECLINED"
    result = _validate_fix1_rows(rows)
    assert "pb1_fix1_semantic_audit_decision_hash_mismatch" in result["errors"]


def test_pb1_fix1_rejects_correction_ledger_mismatch(pb1_pass_b) -> None:
    ledger = copy.deepcopy(_pb1_json(a2.PB1_FIX1_LEDGER))
    ledger["corrections"].pop()
    ledger["correction_count"] -= 1
    result = _validate_fix1_rows(pb1_pass_b, ledger=ledger)
    assert "pb1_fix1_correction_ledger_pair_mismatch" in result["errors"]


def test_pb1_fix1_rejects_manual_pass_c_support_set_patch(pass_a, pb1_classification, pb1_pass_b, pb1_pass_c) -> None:
    patched = copy.deepcopy(pb1_pass_c)
    next(row for row in patched if row["case_id"] == "EV2-A2-S19")["acceptable_complete_support_sets"].append(
        ["FAQ_TRANSFER_PENDING_001#customer_boundary", "RUN_TRANSFER_PENDING_001#checks"]
    )
    derived = a2.derive_pb1_pass_c(ROOT, pass_a, pb1_classification, pb1_pass_b, _pb1_json(a2.INELIGIBLE_EVIDENCE_AUDIT))
    assert patched != derived


def test_pb1_fix1_downgraded_s19_checks_is_not_stale_allowed(pb1_pass_c) -> None:
    row = next(item for item in pb1_pass_c if item["case_id"] == "EV2-A2-S19")
    assert "RUN_TRANSFER_PENDING_001#checks" not in row["allowed_supporting_evidence"]
    assert row["acceptable_complete_support_sets"] == [["RUN_TRANSFER_PENDING_001#action"]]


def test_pb1_fix1_removed_contradiction_is_not_stale_forbidden(pb1_pass_c) -> None:
    row = next(item for item in pb1_pass_c if item["case_id"] == "EV2-A2-C08")
    assert "FAQ_CASH_PENDING_001#answer" in row["allowed_supporting_evidence"]
    assert "FAQ_CASH_PENDING_001#answer" not in row["forbidden_evidence"]


def test_pb1_fix1_imported_hard_mutation_triggers_explicit_stop(pb1_pass_b) -> None:
    rows = copy.deepcopy(pb1_pass_b)
    row = next(item for item in rows if item["review_provenance"] == a2.PB1_IMPORT_PROVENANCE and item["support_class"] != "IRRELEVANT")
    row["support_rationale"] += " mutated"
    result = _validate_fix1_rows(rows)
    assert "A2_PB1_FIX1_IMPORTED_HARD_SEMANTIC_CONFLICT" in result["errors"]


@pytest.fixture(scope="module")
def fix2_packet() -> list[dict]:
    return a2.read_jsonl(ROOT / a2.PB1_FIX2_BLIND_PACKET)


@pytest.fixture(scope="module")
def fix2_decisions() -> list[dict]:
    return a2.read_jsonl(ROOT / a2.PB1_FIX2_BLIND_DECISIONS)


def test_pb1_fix2_blind_packet_exact_514_and_sanitized(fix2_packet) -> None:
    result = a2.validate_pb1_fix2_blind_packet(ROOT, fix2_packet)
    assert result["passed"], result["errors"][:20]
    assert result["rows"] == result["unique_pairs"] == result["unique_review_ids"] == 514
    forbidden = {
        "support_class", "obligations_covered", "obligations_not_covered",
        "target_match", "state_match", "dimension_match", "support_rationale",
        "expected_route", "expected_production_route", "semantic_stratum",
        "current_label", "old_label", "changed",
    }
    assert not any(forbidden & set(row) for row in fix2_packet)
    assert all(set(row) == a2.PB1_FIX2_PACKET_FIELDS for row in fix2_packet)


def test_pb1_fix2_blind_decisions_exact_514_and_valid(fix2_decisions) -> None:
    result = a2.validate_pb1_fix2_blind_decisions(ROOT, fix2_decisions)
    assert result["passed"], result["errors"][:20]
    assert result["rows"] == result["unique_pairs"] == 514
    assert sum(result["support_class_counts"].values()) == 514


def test_pb1_fix2_every_decision_has_exact_review_basis(fix2_packet, fix2_decisions) -> None:
    packet = {row["review_id"]: row for row in fix2_packet}
    assert all(
        row["review_basis_quotes"]
        and all(quote and quote in packet[row["review_id"]]["frozen_section_text"] for quote in row["review_basis_quotes"])
        for row in fix2_decisions
    )


def test_pb1_fix2_positive_coverage_has_quote_and_entailment(fix2_packet, fix2_decisions) -> None:
    packet = {row["review_id"]: row for row in fix2_packet}
    for row in fix2_decisions:
        if row["support_class"] not in {"COMPLETE_SUPPORT", "PARTIAL_SUPPORT"}:
            continue
        assert set(row["support_quotes_by_obligation"]) == set(row["obligations_covered"])
        assert set(row["semantic_entailment_explanation_by_obligation"]) == set(row["obligations_covered"])
        for quotes in row["support_quotes_by_obligation"].values():
            assert all(quote in packet[row["review_id"]]["frozen_section_text"] for quote in quotes)


def test_pb1_fix2_contradiction_has_exact_explicit_proof(fix2_packet, fix2_decisions) -> None:
    packet = {row["review_id"]: row for row in fix2_packet}
    contradictions = [row for row in fix2_decisions if row["support_class"] == "CONTRADICTION"]
    assert contradictions
    assert all(row["contradiction_basis_quote"] in packet[row["review_id"]]["frozen_section_text"] for row in contradictions)
    assert all(row["contradicted_constraint"] and row["contradiction_semantic_explanation"] for row in contradictions)


def test_pb1_fix2_validator_rejects_nonverbatim_basis(fix2_decisions) -> None:
    rows = copy.deepcopy(fix2_decisions)
    rows[0]["review_basis_quotes"] = ["fabricated blind-review quote"]
    result = a2.validate_pb1_fix2_blind_decisions(ROOT, rows)
    assert any("review_basis_not_exact_quote" in error for error in result["errors"])


def test_pb1_fix2_validator_rejects_missing_positive_explanation(fix2_decisions) -> None:
    rows = copy.deepcopy(fix2_decisions)
    row = next(item for item in rows if item["support_class"] in {"COMPLETE_SUPPORT", "PARTIAL_SUPPORT"})
    row["semantic_entailment_explanation_by_obligation"] = {}
    result = a2.validate_pb1_fix2_blind_decisions(ROOT, rows)
    assert any("positive_trace_key_mismatch" in error for error in result["errors"])


def test_pb1_fix2_validator_rejects_fabricated_contradiction(fix2_decisions) -> None:
    rows = copy.deepcopy(fix2_decisions)
    row = next(item for item in rows if item["support_class"] == "CONTRADICTION")
    row["contradiction_basis_quote"] = "fabricated contradiction"
    result = a2.validate_pb1_fix2_blind_decisions(ROOT, rows)
    assert any("contradiction_proof_invalid" in error for error in result["errors"])


def test_pb1_fix2_false_previous_label_declaration_without_phase_evidence_fails(monkeypatch, fix2_decisions) -> None:
    monkeypatch.setattr(a2, "_fix2_read_phase_log", lambda: {
        "events": [], "parent_authored_blind_decisions": False,
        "subagent_received_previous_labels": False,
        "subagent_received_fix1_corrections": False,
        "subagent_received_senior_case_findings": False,
    })
    result = a2.validate_pb1_fix2_blind_decisions(ROOT, fix2_decisions)
    assert "false_previous_label_declaration_without_phase_evidence" in result["errors"]


def test_pb1_fix2_validator_cannot_author_semantic_labels() -> None:
    source = inspect.getsource(a2.validate_pb1_fix2_blind_decisions)
    assert "PB1_FIX1_CORRECTIONS" not in source
    assert "write_jsonl" not in source
    assert "support_class\"] =" not in source
    build_source = inspect.getsource(a2.build_pb1_fix2_blind_packet)
    assert "PB1_FIX1_CORRECTIONS" not in build_source
    assert "obligations_covered" not in build_source


def test_pb1_fix2_decisions_frozen_before_comparison_and_unchanged() -> None:
    log = a2._fix2_read_phase_log()
    events = [row["event"] for row in log["events"]]
    assert events.index("BLIND_DECISIONS_FROZEN") < events.index("CURRENT_PASS_B_COMPARISON_OPENED")
    frozen = next(row for row in log["events"] if row["event"] == "BLIND_DECISIONS_FROZEN")
    assert frozen["blind_decisions_sha256"] == a2.file_sha256(ROOT / a2.PB1_FIX2_BLIND_DECISIONS)
    assert "PB1_FIX2_BLIND_DECISIONS" not in inspect.getsource(a2.apply_pb1_fix2_after_freeze).split("read_jsonl", 1)[-1].split("write_jsonl")[-1]


def test_pb1_fix2_comparison_ledger_exactly_equals_differences() -> None:
    comparison = _pb1_json(a2.PB1_FIX2_COMPARISON)
    ledger = _pb1_json(a2.PB1_FIX2_LEDGER)
    assert comparison["semantic_differences"] == ledger["correction_count"] == len(comparison["differences"])
    assert ledger["corrections"] == comparison["differences"]


def test_pb1_fix2_imported_hard_discrepancy_triggers_stop_without_gold_mutation() -> None:
    comparison = _pb1_json(a2.PB1_FIX2_COMPARISON)
    assert any(row["imported_hard"] for row in comparison["differences"])
    assert a2.file_sha256(ROOT / fix2b.PRE_FIX2B_PASS_B) == a2.PB1_FIX1_PRE_FIX2_PASS_B_SHA256
    assert a2.file_sha256(ROOT / fix2b.PRE_FIX2B_PASS_C) == a2.PB1_FIX1_PRE_FIX2_PASS_C_SHA256


def _fix2a_row(support_class: str, *, covered=None, target=True, state=True, dimension=True) -> dict:
    return {
        "support_class": support_class, "obligations_covered": covered or [],
        "target_match": target, "state_match": state, "dimension_match": dimension,
    }


def test_fix2a_equivalent_contradiction_wording_and_quote_span_do_not_conflict() -> None:
    left = {**_fix2a_row("CONTRADICTION", target=True, state=False, dimension=True), "contradiction_basis_quote":"short", "contradicted_constraint":"STATE:X"}
    right = {**_fix2a_row("CONTRADICTION", target=False, state=False, dimension=False), "contradiction_basis_quote":"a longer equivalent short quote", "contradicted_constraint":"prose equivalent"}
    assert a2.semantic_decision_projection_v2(left) == a2.semantic_decision_projection_v2(right)


def test_fix2a_dimension_difference_on_contradiction_does_not_conflict() -> None:
    left = _fix2a_row("CONTRADICTION", dimension=True)
    right = _fix2a_row("CONTRADICTION", dimension=False)
    assert a2.semantic_decision_projection_v2(left) == a2.semantic_decision_projection_v2(right)


def test_fix2a_positive_obligation_and_compatibility_differences_trigger_conflict() -> None:
    base = _fix2a_row("PARTIAL_SUPPORT", covered=["O1"])
    assert a2.semantic_decision_projection_v2(base) != a2.semantic_decision_projection_v2(_fix2a_row("PARTIAL_SUPPORT", covered=["O2"]))
    for key in ("target_match", "state_match", "dimension_match"):
        changed = dict(base); changed[key] = False
        assert a2.semantic_decision_projection_v2(base) != a2.semantic_decision_projection_v2(changed)


def test_fix2a_contextual_irrelevant_and_target_state_differences_trigger_conflict() -> None:
    contextual = _fix2a_row("CONTEXTUAL_INSUFFICIENT")
    assert a2.semantic_decision_projection_v2(contextual) != a2.semantic_decision_projection_v2(_fix2a_row("IRRELEVANT"))
    assert a2.semantic_decision_projection_v2(contextual) != a2.semantic_decision_projection_v2(_fix2a_row("CONTEXTUAL_INSUFFICIENT", target=False))
    assert a2.semantic_decision_projection_v2(contextual) != a2.semantic_decision_projection_v2(_fix2a_row("CONTEXTUAL_INSUFFICIENT", state=False))
    assert a2.semantic_decision_projection_v2(contextual) == a2.semantic_decision_projection_v2(_fix2a_row("CONTEXTUAL_INSUFFICIENT", dimension=False))


def test_fix2a_gold_impact_projection_mirrors_derivation_logic() -> None:
    assert a2.gold_impact_projection_v1(_fix2a_row("PARTIAL_SUPPORT", covered=["O1"])) == {"usable_coverage":["O1"],"forbidden":False}
    assert a2.gold_impact_projection_v1(_fix2a_row("PARTIAL_SUPPORT", covered=["O1"], dimension=False)) == {"usable_coverage":[],"forbidden":False}
    assert a2.gold_impact_projection_v1(_fix2a_row("CONTEXTUAL_INSUFFICIENT", state=False)) == {"usable_coverage":[],"forbidden":True}
    assert a2.gold_impact_projection_v1(_fix2a_row("CONTRADICTION")) == {"usable_coverage":[],"forbidden":True}


@pytest.fixture(scope="module")
def fix2a_tiebreak_packet() -> list[dict]:
    return a2.read_jsonl(ROOT / a2.PB1_FIX2A_TIEBREAK_PACKET)


@pytest.fixture(scope="module")
def fix2a_tiebreak_decisions() -> list[dict]:
    return a2.read_jsonl(ROOT / a2.PB1_FIX2A_TIEBREAK_DECISIONS)


def test_fix2a_tiebreak_packet_exact_65_sanitized_and_nonhard(fix2a_tiebreak_packet, pb1_pass_b) -> None:
    result = a2.validate_pb1_fix2a_tiebreak_packet(ROOT, fix2a_tiebreak_packet)
    assert result["passed"], result["errors"]
    assert result["rows"] == result["unique_pairs"] == result["unique_review_ids"] == 65
    current = {(row["case_id"],row["evidence_id"]):row for row in pb1_pass_b}
    assert all(current[(row["case_id"],row["evidence_id"])]["review_provenance"] != a2.PB1_IMPORT_PROVENANCE for row in fix2a_tiebreak_packet)
    forbidden = {"support_class","obligations_covered","target_match","state_match","dimension_match","current_label","blind1_label","difference_type","expected_winner","semantic_stratum","expected_route"}
    assert not any(forbidden & set(row) for row in fix2a_tiebreak_packet)


def test_fix2a_tiebreak_decisions_validate_and_have_second_isolation(fix2a_tiebreak_decisions) -> None:
    result = a2.validate_pb1_fix2a_tiebreak_decisions(ROOT, fix2a_tiebreak_decisions)
    assert result["passed"], result["errors"][:20]
    assert result["rows"] == result["unique_pairs"] == 65
    assert all(row["previous_labels_visible_to_reviewer"] is False for row in fix2a_tiebreak_decisions)
    log = a2._fix2a_read_phase_log()
    assert log["parent_authored_tiebreak_decisions"] is False
    assert log["second_subagent_received_previous_labels"] is False
    assert log["second_subagent_received_blind1_decisions"] is False
    assert log["second_subagent_received_senior_findings"] is False


def test_fix2a_tiebreak_freezes_before_three_way_comparison() -> None:
    log = a2._fix2a_read_phase_log()
    events = [row["event"] for row in log["events"]]
    assert events.index("TIEBREAK_DECISIONS_FROZEN") < events.index("THREE_WAY_COMPARISON_OPENED")
    frozen = next(row for row in log["events"] if row["event"] == "TIEBREAK_DECISIONS_FROZEN")
    assert frozen["tiebreak_decisions_sha256"] == a2.file_sha256(ROOT / a2.PB1_FIX2A_TIEBREAK_DECISIONS)


def test_fix2a_third_projection_mismatch_triggers_exact_stop_without_gold_mutation() -> None:
    matrix = json.loads((a2.fix2a_external_review_dir() / "three_way_resolution_matrix.json").read_text(encoding="utf-8"))
    assert matrix["rows"] == 65
    assert (matrix["current_wins"],matrix["blind1_wins_tiebreak_selected"],matrix["unresolved"]) == (26,22,17)
    assert all(row["reason"] == "THIRD_PROJECTION_MISMATCH" for row in matrix["matrix"] if row["winner"] == "UNRESOLVED")
    assert a2.file_sha256(ROOT / fix2b.PRE_FIX2B_PASS_B) == a2.PB1_FIX1_PRE_FIX2_PASS_B_SHA256
    assert a2.file_sha256(ROOT / fix2b.PRE_FIX2B_PASS_C) == a2.PB1_FIX1_PRE_FIX2_PASS_C_SHA256
    assert not (ROOT / a2.PB1_FIX2A_FINAL_LEDGER).exists()


def test_fix2a_only_h01_h02_are_authorized_imported_hard_mutations() -> None:
    artifact = _pb1_json(a2.PB1_FIX2A_HARD_ADJUDICATION)
    assert artifact["imported_hard_senior_adjudicated"] == 33
    assert artifact["imported_hard_active_row_changes"] == 2
    changed = {(row["case_id"],row["evidence_id"]) for row in artifact["adjudications"] if row["authorized_active_change"]}
    assert changed == {("EV2-A2-H01","RUN_CARD_DECLINED_001#action"),("EV2-A2-H02","ESC_CASH_DECLINED_001#handoff")}
    assert all(row["before"] == row["after"] for row in artifact["adjudications"] if not row["authorized_active_change"])


def test_fix2a_final_writer_is_guarded_by_zero_unresolved_and_rederives_pass_c() -> None:
    source = inspect.getsource(a2.resolve_and_apply_pb1_fix2a)
    assert source.index("if unresolved:") < source.index("write_jsonl(root / PASS_B, final_rows)")
    assert source.count("derive_pb1_pass_c_fail_closed") == 2
    assert source.index("write_jsonl(root / PASS_B, final_rows)") < source.index("derive_pb1_pass_c_fail_closed")
