"""Fail-closed validation for the W3-002-CR1 contract-decision package.

This module validates reporting evidence only. It does not import or execute the
critical evaluator, retrieval, generation, or model code.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


class FeasibilityValidationError(RuntimeError):
    """Raised when the contract-decision evidence is incomplete or inconsistent."""


EXPECTED_NEGATIVE_IDS = {
    "Q_V4_N_ID01", "Q_V4_N_ID02", "Q_V4_N_ID03", "Q_V4_N_ID04",
    "Q_V4_N_AM01", "Q_V4_N_AM02", "Q_V4_N_AM03",
    "Q_V4_N_DR01", "Q_V4_N_DR02", "Q_V4_N_DR03",
    "Q_V4_N_EX01", "Q_V4_N_EX02", "Q_V4_N_EX03",
    "Q_V4_N_CF01", "Q_V4_N_CF02", "Q_V4_N_IN01", "Q_V4_N_IN02",
    "Q_V4_N_OS01", "Q_V4_N_AB01", "Q_V4_N_AB02",
}
EXPECTED_ANSWER_SAFE_CORRECTIVE_IDS = EXPECTED_NEGATIVE_IDS - {
    "Q_V4_N_CF01", "Q_V4_N_CF02", "Q_V4_N_OS01", "Q_V4_N_AB01", "Q_V4_N_AB02"
}
EXPECTED_REV4_MANIFEST_SHA256 = "b2b021c78f11ff4cf5d023044b464b43d806f0c0217fd8e3b196dfc736bb52af"
EXPECTED_REV4_BUNDLE_SHA256 = "a081e909113a682e7790b758f2b90bea3eea26025103e7209dc1c32e8f04fa5e"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FeasibilityValidationError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise FeasibilityValidationError(f"expected JSON object: {path}")
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        values = [json.loads(line) for line in lines if line.strip()]
    except (OSError, json.JSONDecodeError) as exc:
        raise FeasibilityValidationError(f"cannot read JSONL {path}: {exc}") from exc
    if any(not isinstance(value, dict) for value in values):
        raise FeasibilityValidationError(f"expected JSON objects in {path}")
    return values


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise FeasibilityValidationError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def validate_negative_matrix(rows: list[dict[str, Any]]) -> Counter[str]:
    if len(rows) != 20 or {row.get("query_id") for row in rows} != EXPECTED_NEGATIVE_IDS:
        raise FeasibilityValidationError("negative feasibility matrix must contain the exact 20 revision-4 IDs")
    outcomes: Counter[str] = Counter()
    for row in rows:
        required = {
            "registered_category", "requested_target", "requested_obligations",
            "current_safe_corrective_obligations",
            "current_corrective_obligations_artificially_impossible",
            "approved_sections_relevant_to_useful_correction",
            "grounded_corrective_response_outline", "complete_safe_corrective_answer_possible",
            "recommended_expected_response", "exact_reason", "original_category_remains_isolated",
            "category_feasible_as_true_abstain_under_frozen_kb", "reviewer_status", "reviewer_rationale",
        }
        if not required.issubset(row):
            raise FeasibilityValidationError(f"incomplete negative feasibility row: {row.get('query_id')}")
        outcome = row["recommended_expected_response"]
        if outcome not in {"ANSWER_SAFE_CORRECTIVE", "ABSTAIN_ESCALATE"}:
            raise FeasibilityValidationError(f"invalid recommended response: {row['query_id']}")
        if row["complete_safe_corrective_answer_possible"] is not (outcome == "ANSWER_SAFE_CORRECTIVE"):
            raise FeasibilityValidationError(f"answerability/outcome mismatch: {row['query_id']}")
        if row["category_feasible_as_true_abstain_under_frozen_kb"] is not (outcome == "ABSTAIN_ESCALATE"):
            raise FeasibilityValidationError(f"category feasibility mismatch: {row['query_id']}")
        if row["original_category_remains_isolated"] is not True:
            raise FeasibilityValidationError(f"category not isolated: {row['query_id']}")
        if not row["reviewer_status"] or not row["reviewer_rationale"]:
            raise FeasibilityValidationError(f"missing feasibility reviewer provenance: {row['query_id']}")
        evidence_ids = [item.get("evidence_id") for item in row["approved_sections_relevant_to_useful_correction"]]
        if any(not value or "#" not in value for value in evidence_ids) or len(evidence_ids) != len(set(evidence_ids)):
            raise FeasibilityValidationError(f"invalid relevant evidence list: {row['query_id']}")
        outcomes[outcome] += 1
    if {row["query_id"] for row in rows if row["recommended_expected_response"] == "ANSWER_SAFE_CORRECTIVE"} != EXPECTED_ANSWER_SAFE_CORRECTIVE_IDS:
        raise FeasibilityValidationError("safe-corrective ID set does not match adjudication")
    if outcomes != Counter({"ANSWER_SAFE_CORRECTIVE": 15, "ABSTAIN_ESCALATE": 5}):
        raise FeasibilityValidationError(f"unexpected feasibility distribution: {dict(outcomes)}")
    return outcomes


def validate_category_summary(summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    categories = summary.get("categories", [])
    if len(categories) != 8 or summary.get("fixed_40_answer_20_abstain_feasible") is not False:
        raise FeasibilityValidationError("invalid category-level feasibility summary")
    matrix_counts: dict[str, Counter[str]] = {}
    for row in rows:
        matrix_counts.setdefault(row["registered_category"], Counter())[row["recommended_expected_response"]] += 1
    if {item.get("registered_category") for item in categories} != set(matrix_counts):
        raise FeasibilityValidationError("category set differs from negative matrix")
    for item in categories:
        counts = matrix_counts[item["registered_category"]]
        if item.get("required_count") != sum(counts.values()):
            raise FeasibilityValidationError(f"required count mismatch: {item['registered_category']}")
        if item.get("true_abstain_count") != counts["ABSTAIN_ESCALATE"]:
            raise FeasibilityValidationError(f"abstain count mismatch: {item['registered_category']}")
        if item.get("answer_safe_corrective_count") != counts["ANSWER_SAFE_CORRECTIVE"]:
            raise FeasibilityValidationError(f"corrective count mismatch: {item['registered_category']}")


def validate_provenance(audit: dict[str, Any]) -> None:
    if audit.get("pass_b_rows") != 3120:
        raise FeasibilityValidationError("Pass B row count mismatch")
    status_total = sum(audit.get(key, -10_000) for key in (
        "rows_missing_reviewer_status", "rows_with_revision_1_reviewer_status",
        "rows_with_revision_2_reviewer_status", "rows_with_revision_3_reviewer_status",
        "rows_with_revision_4_reviewer_status",
    ))
    if status_total != 3120 or audit.get("rows_missing_reviewer_status") != 1040 or audit.get("rows_with_revision_3_reviewer_status") != 2080:
        raise FeasibilityValidationError("Pass B reviewer-status counts are inconsistent")
    if sum(audit.get("reason_code_distribution", {}).values()) != 3120:
        raise FeasibilityValidationError("Pass B reason-code counts are inconsistent")
    if audit.get("material_rows_with_valid_revision_4_reviewer_provenance") != 0:
        raise FeasibilityValidationError("revision-4 reviewer provenance must remain failed")


def validate_positive_defects(rows: list[dict[str, Any]]) -> None:
    keys = {(row.get("query_id"), row.get("evidence_id")) for row in rows}
    required = {
        ("Q_V2_A_TRD04", "RUN_TRANSFER_DECLINED_001#action"),
        ("Q_V2_A_TRR04", "FAQ_TRANSFER_RECIPIENT_002#current_window"),
        ("Q_V2_A_TRR04", "POL_TRANSFER_RECIPIENT_001#trace_window"),
    }
    if not required.issubset(keys) or any(row.get("candidate_mapping_modified") is not False for row in rows):
        raise FeasibilityValidationError("positive-support defect audit is incomplete or mutates the candidate")


def validate_hard_negative_feasibility(audit: dict[str, Any]) -> None:
    candidates = audit.get("candidates", [])
    if audit.get("revision_4_assigned_hard_negative_count") != 0 or audit.get("nonzero_hard_negative_slice_feasible") is not True:
        raise FeasibilityValidationError("hard-negative feasibility lifecycle mismatch")
    if not candidates or audit.get("candidate_count") != len(candidates):
        raise FeasibilityValidationError("a nonzero hard-negative candidate slice is required")
    for row in candidates:
        if row.get("current_support_class") in {"DIRECT_SUPPORT", "PARTIAL_SUPPORT"}:
            raise FeasibilityValidationError("hard-negative candidate has legitimate support")
        if row.get("absent_from_all_complete_covers") is not True or row.get("approved_and_effective") is not True:
            raise FeasibilityValidationError("hard-negative candidate fails cover/eligibility checks")


def validate_rejected_revision(root: Path, inventory: dict[str, Any]) -> None:
    if inventory.get("revision_4_manifest_sha256") != EXPECTED_REV4_MANIFEST_SHA256:
        raise FeasibilityValidationError("recorded revision-4 manifest hash mismatch")
    if inventory.get("revision_4_review_bundle_sha256") != EXPECTED_REV4_BUNDLE_SHA256:
        raise FeasibilityValidationError("recorded revision-4 bundle hash mismatch")
    archive = root / "reports/week_03/rejected/critical_eval_v2_revision_4"
    artifacts = inventory.get("artifacts", [])
    if inventory.get("artifact_count") != len(artifacts):
        raise FeasibilityValidationError("revision-4 rejected inventory count mismatch")
    for item in artifacts:
        path = archive / item["path"]
        if _sha256(path) != item["sha256"] or path.stat().st_size != item["size_bytes"]:
            raise FeasibilityValidationError(f"rejected revision-4 artifact changed: {item['path']}")
    manifest = archive / "reports/week_03/results/critical_eval_v2_candidate_manifest.json"
    if _sha256(manifest) != EXPECTED_REV4_MANIFEST_SHA256:
        raise FeasibilityValidationError("rejected revision-4 manifest bytes changed")


def validate_historical_hashes(root: Path) -> int:
    config = _load_json(root / "configs/evaluation/critical_eval_v2.json")
    expected = config.get("historical_artifacts", {})
    for relative, digest in expected.items():
        if _sha256(root / relative) != digest:
            raise FeasibilityValidationError(f"historical W3-002 artifact changed: {relative}")
    return len(expected)


def validate_feasibility_package(root: Path) -> dict[str, Any]:
    results = root / "reports/week_03/results"
    matrix = _load_jsonl(results / "critical_eval_v2_revision_4_negative_feasibility_matrix.jsonl")
    outcomes = validate_negative_matrix(matrix)
    validate_category_summary(_load_json(results / "critical_eval_v2_revision_4_category_feasibility.json"), matrix)
    validate_provenance(_load_json(results / "critical_eval_v2_revision_4_pass_b_provenance_audit.json"))
    validate_positive_defects(_load_jsonl(results / "critical_eval_v2_revision_4_positive_support_defects.jsonl"))
    validate_hard_negative_feasibility(_load_json(results / "critical_eval_v2_revision_4_hard_negative_feasibility.json"))
    validate_rejected_revision(root, _load_json(results / "critical_eval_v2_revision_4_rejected_inventory.json"))
    historical_count = validate_historical_hashes(root)
    return {
        "status": "PASS",
        "negative_query_count": len(matrix),
        "response_counts": dict(outcomes),
        "historical_hash_count": historical_count,
        "revision_4_manifest_sha256": EXPECTED_REV4_MANIFEST_SHA256,
        "revision_4_review_bundle_sha256": EXPECTED_REV4_BUNDLE_SHA256,
        "evaluation_authorized": False,
    }
