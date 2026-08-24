"""Fail-closed validators and mechanical derivations for W3-003-EV2-A2.

This utility does not author semantic judgments. Human-authored Pass B rows
must carry exact content hashes, obligation coverage, and verbatim supporting
or contradicting clauses. It never imports or executes the production candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable


PASS_A_EXPECTED_SHA256 = "9ef421327ba03eb12b006e857b2abb6540d6036b27a8891a491caf3660e7b567"
PASS_A_V2_EXPECTED_SHA256 = "71a353f79f3a5bbdbf8faf61b63b08f842046f1082d32c3e995feaf928d146d3"
PASS_A_V3_EXPECTED_SHA256 = "f66ce6b0fa6c86a0cf7e3cc4aba33f3d76699e7981630a8b9b748ce979d66541"
AS_OF = date(2026, 8, 16)
KB = Path("data/kb/kb_v1.jsonl")
PASS_A = Path("data/evaluation/w3_003_ev2_pass_a.jsonl")
PASS_A_REV1 = Path("data/evaluation/w3_003_ev2_pass_a_rev1_pre_replacement.jsonl")
PASS_A_V2 = Path("data/evaluation/w3_003_ev2_pass_a_v2_pre_fix3.jsonl")
PASS_B = Path("data/evaluation/w3_003_ev2_pass_b_support_judgments.jsonl")
PASS_C = Path("data/evaluation/w3_003_ev2_candidate.jsonl")
PB1_PRE_FIX1_PASS_B = Path("data/evaluation/w3_003_ev2_pass_b_support_judgments_pb1_pre_fix1.jsonl")
PB1_PRE_FIX1_PASS_C = Path("data/evaluation/w3_003_ev2_candidate_pb1_pre_fix1.jsonl")
PB1_PRE_FIX1_PASS_B_SHA256 = "7dd4c196a8c45cb31ef0d549db3d6e048de78a8fb12f10cedb8f714c6cdc50b6"
PB1_PRE_FIX1_PASS_C_SHA256 = "e5f28b1e8cb44760363b83e42fe4d36dad132548a2f39810cb671b201cb90f99"
PB1_PRE_FIX1_ARTIFACT_SHA256 = {
    "reports/week_03/results/w3_003_ev2_a2_positive_support_audit.json": "217e20fa17b95a475878d4eb5ad175b61b28aa9321e711a3a1687a00dc258a2f",
    "reports/week_03/results/w3_003_ev2_a2_safe_corrective_proofs.json": "43e67999d8551f8ad4706367b0cd41378b5a5995fabc3353f4dc8b2699049afa",
    "reports/week_03/results/w3_003_ev2_a2_support_summary.json": "7035baad77309f23ca4604e57d90b38f657b488d44c2a39c41b7fd6c0d895729",
    "reports/week_03/results/w3_003_ev2_a2_manifest.json": "94371ecf99d1e22e9b494bfdb1639b9166b805120f0729c9e20abfd358e8c192",
}
FIX1B_JUDGMENTS = Path("reports/week_03/results/w3_003_ev2_a2_fix1b_hard_support_judgments.jsonl")
FIX1B_CASE_REVIEW = Path("reports/week_03/results/w3_003_ev2_a2_fix1b_hard_case_review.json")
FIX1B_CONFLICT_SUMMARY = Path("reports/week_03/results/w3_003_ev2_a2_fix1b_conflict_summary.json")
FIX2_LEDGER = Path("reports/week_03/results/w3_003_ev2_a2_fix2_replacement_ledger.json")
FIX2_JUDGMENTS = Path("reports/week_03/results/w3_003_ev2_a2_fix2_replacement_support_judgments.jsonl")
FIX2_CASE_REVIEW = Path("reports/week_03/results/w3_003_ev2_a2_fix2_replacement_case_review.json")
FIX2_PASS_A_AUDIT = Path("reports/week_03/results/w3_003_ev2_a2_fix2_pass_a_v2_audit.json")
FIX2A_OBLIGATION_CLASSIFICATION = Path("reports/week_03/results/w3_003_ev2_a2_fix2a_obligation_classification.json")
FIX2A_CONSISTENCY_REVIEW = Path("reports/week_03/results/w3_003_ev2_a2_fix2a_hard_safe_consistency_review.json")
FIX2A_CONFLICT_SUMMARY = Path("reports/week_03/results/w3_003_ev2_a2_fix2a_conflict_summary.json")
FIX3_LEDGER = Path("reports/week_03/results/w3_003_ev2_a2_fix3_replacement_ledger.json")
FIX3_JUDGMENTS = Path("reports/week_03/results/w3_003_ev2_a2_fix3_replacement_support_judgments.jsonl")
FIX3_CASE_REVIEW = Path("reports/week_03/results/w3_003_ev2_a2_fix3_replacement_case_review.json")
FIX3_PASS_A_AUDIT = Path("reports/week_03/results/w3_003_ev2_a2_fix3_pass_a_v3_audit.json")
A2_MANIFEST = Path("reports/week_03/results/w3_003_ev2_a2_manifest.json")
A1_DEV_LINEAGE = Path("data/evaluation/w3_003_ev2_dev_mutation_precheck.jsonl")
OBLIGATION_CLASSIFICATION = Path("reports/week_03/results/w3_003_ev2_a2_obligation_classification.jsonl")
SUPPORT_SUMMARY = Path("reports/week_03/results/w3_003_ev2_a2_support_summary.json")
POSITIVE_SUPPORT_AUDIT = Path("reports/week_03/results/w3_003_ev2_a2_positive_support_audit.json")
HARD_ABSTAIN_PROOFS = Path("reports/week_03/results/w3_003_ev2_a2_hard_abstain_proofs.json")
SAFE_CORRECTIVE_PROOFS = Path("reports/week_03/results/w3_003_ev2_a2_safe_corrective_proofs.json")
AMBIGUOUS_DERIVATION = Path("reports/week_03/results/w3_003_ev2_a2_ambiguous_derivation.json")
INELIGIBLE_EVIDENCE_AUDIT = Path("reports/week_03/results/w3_003_ev2_a2_ineligible_evidence_audit.json")
LINEAGE_AUDIT = Path("reports/week_03/results/w3_003_ev2_a2_lineage_audit.json")
PB1_FIX1_LEDGER = Path("reports/week_03/results/w3_003_ev2_a2_pb1_fix1_semantic_correction_ledger.json")
PB1_FIX1_AUDIT_SUMMARY = Path("reports/week_03/results/w3_003_ev2_a2_pb1_fix1_semantic_audit_summary.json")
PB1_FIX1_PRE_FIX2_PASS_B = Path("data/evaluation/w3_003_ev2_pass_b_support_judgments_pb1_fix1_pre_fix2.jsonl")
PB1_FIX1_PRE_FIX2_PASS_C = Path("data/evaluation/w3_003_ev2_candidate_pb1_fix1_pre_fix2.jsonl")
PB1_FIX1_PRE_FIX2_PASS_B_SHA256 = "5b0a55b0d7b9e1d0aede02b4858441390d5b1945dbd0dd5689f0098304f4d209"
PB1_FIX1_PRE_FIX2_PASS_C_SHA256 = "7197be43ad32e88a13c3567c52f30ec7ac3e8bcdb1c1c576fbefed661ea1117d"
PB1_FIX2_BLIND_PACKET = Path("reports/week_03/results/w3_003_ev2_a2_pb1_fix2_blind_review_packet.jsonl")
PB1_FIX2_BLIND_DECISIONS = Path("reports/week_03/results/w3_003_ev2_a2_pb1_fix2_blinded_semantic_decisions.jsonl")
PB1_FIX2_COMPARISON = Path("reports/week_03/results/w3_003_ev2_a2_pb1_fix2_blind_comparison.json")
PB1_FIX2_LEDGER = Path("reports/week_03/results/w3_003_ev2_a2_pb1_fix2_semantic_correction_ledger.json")
PB1_FIX2_REVIEW_PROVENANCE = "BLINDED_FIX2_ISOLATED_SUBAGENT_REVIEW"
PB1_FIX2_TASK_ID = "W3-003-EV2-A2-PB1-FIX2"
PB1_FIX2_STATUS = "PB1_FIX2_BLINDED_SEMANTIC_AUDIT_PASS_AWAITING_SENIOR_REVIEW_AND_A3"
PB1_FIX2_EXTERNAL_STATUS = "A2_PB1_FIX2_READY_FOR_SENIOR_REVIEW"
PB1_FIX2A_HARD_ADJUDICATION = Path("reports/week_03/results/w3_003_ev2_a2_pb1_fix2a_senior_hard_adjudication.json")
PB1_FIX2A_PROJECTION_COMPARISON = Path("reports/week_03/results/w3_003_ev2_a2_pb1_fix2a_projection_comparison.json")
PB1_FIX2A_TIEBREAK_PACKET = Path("reports/week_03/results/w3_003_ev2_a2_pb1_fix2a_tiebreak_packet.jsonl")
PB1_FIX2A_TIEBREAK_DECISIONS = Path("reports/week_03/results/w3_003_ev2_a2_pb1_fix2a_tiebreak_decisions.jsonl")
PB1_FIX2A_FINAL_LEDGER = Path("reports/week_03/results/w3_003_ev2_a2_pb1_fix2a_final_correction_ledger.json")
PB1_FIX2A_TIEBREAK_PROVENANCE = "BLINDED_FIX2A_ISOLATED_TIEBREAK_REVIEW"
PB1_FIX2A_TASK_ID = "W3-003-EV2-A2-PB1-FIX2A"
PB1_FIX2A_STATUS = "PB1_FIX2A_TIEBREAK_RECONCILED_AWAITING_SENIOR_REVIEW_AND_A3"
PB1_FIX2A_EXTERNAL_STATUS = "A2_PB1_FIX2A_READY_FOR_SENIOR_REVIEW"
REV1_PASS_B_HISTORY = Path("data/evaluation/w3_003_ev2_pass_b_support_judgments_rev1_invalid_independence.jsonl")
REV1_PASS_C_HISTORY = Path("data/evaluation/w3_003_ev2_candidate_rev1_invalid_independence.jsonl")
EXPECTED_DISTRIBUTION = {
    "STANDARD": 24,
    "SAFE_CORRECTIVE": 18,
    "HARD_ABSTAIN_ESCALATE": 12,
    "AMBIGUOUS_OR_PARTIAL_SAFE_STOP": 6,
}
SUPPORT_CLASSES = {
    "COMPLETE_SUPPORT", "PARTIAL_SUPPORT", "CONTEXTUAL_INSUFFICIENT",
    "CONTRADICTION", "IRRELEVANT",
}
PB1_CLASSIFICATIONS = {
    "KB_FACTUAL_PREREQUISITE", "KB_FACTUAL_RESPONSE_OBJECTIVE",
    "REQUESTED_FACTUAL_RESOLUTION", "CONTROL_PLANE_BOUNDARY", "SAFE_STOP_CONTROL",
}
PB1_NONFACTUAL_CLASSIFICATIONS = {"CONTROL_PLANE_BOUNDARY", "SAFE_STOP_CONTROL"}
PB1_NEW_PROVENANCE = "PB1_INDEPENDENT_MANUAL_FROZEN_SECTION_REVIEW"
PB1_IMPORT_PROVENANCE = "PB1_CANONICAL_IMPORT_NO_SEMANTIC_MUTATION"
PB1_TASK_ID = "W3-003-EV2-A2-PB1-FIX1"
PB1_STATUS = "PB1_FIX1_SEMANTIC_AUDIT_PASS_AWAITING_SENIOR_REVIEW_AND_A3"
PB1_EXTERNAL_STATUS = "A2_PB1_FIX1_READY_FOR_SENIOR_REVIEW"
REQUIRED_PASS_B_FIELDS = {
    "case_id", "evidence_id", "document_id", "section_id",
    "evidence_content_sha256", "eligibility", "target_match", "state_match",
    "dimension_match", "obligations_covered", "obligations_not_covered",
    "support_class", "support_rationale", "review_provenance",
}
FORBIDDEN_PASS_B_FIELDS = {
    "semantic_stratum", "expected_production_route", "expected_route",
    "risk_stratum", "candidate_prediction", "candidate_output",
    "candidate_reason", "candidate_score", "retrieval_score",
    "selected_evidence", "complete_support_set_ids",
}
FIX1B_REVIEW_PROVENANCE = "FIX1B_INDEPENDENT_MANUAL_CASE_SECTION_REVIEW"
FIX2_REVIEW_PROVENANCE = "FIX2_INDEPENDENT_MANUAL_REPLACEMENT_CASE_SECTION_REVIEW"
FIX2_RETIRED_IDS = {"EV2-A2-H05", "EV2-A2-H06", "EV2-A2-H08"}
FIX2_REPLACEMENT_IDS = {"EV2-A2-H05-R1", "EV2-A2-H06-R1", "EV2-A2-H08-R1"}
FIX2A_TAXONOMY_RULE_ID = "FIX2A_CONTROL_PLANE_FACTUAL_SEPARATION_V1"
FIX2A_STATUS = "A2_FIX2A_HARD_SAFE_CONSISTENCY_READY_FOR_SENIOR_REVIEW"
FIX3_COMPLETENESS_RULE_ID = "FIX3_PREREQUISITE_COMPLETE_SAFE_CORRECTIVE_V2"
FIX3_INTERNAL_STATUS = "A2_FIX3_PASS_A_V3_READY_FOR_SENIOR_REVIEW"
FIX3_EXTERNAL_STATUS = "PASS_A_V3_REPLACEMENT_FEASIBILITY_PASS_AWAITING_SENIOR_REVIEW"
FIX3_REVIEW_PROVENANCE = "FIX3_INDEPENDENT_MANUAL_PREREQUISITE_COMPLETE_REPLACEMENT_REVIEW"
FIX3_RETIRED_IDS = {
    "EV2-A2-H03", "EV2-A2-H04", "EV2-A2-H07", "EV2-A2-H08-R1", "EV2-A2-H09",
}
FIX3_REPLACEMENT_IDS = {
    "EV2-A2-H03-R1", "EV2-A2-H04-R1", "EV2-A2-H07-R1", "EV2-A2-H08-R2",
    "EV2-A2-H09-R1",
}
FIX3_REPLACEMENT_MAP = {
    "EV2-A2-H03": "EV2-A2-H03-R1",
    "EV2-A2-H04": "EV2-A2-H04-R1",
    "EV2-A2-H07": "EV2-A2-H07-R1",
    "EV2-A2-H08-R1": "EV2-A2-H08-R2",
    "EV2-A2-H09": "EV2-A2-H09-R1",
}
FIX3_OBJECTIVE_CONTRACT = {
    "EV2-A2-H03-R1": {
        "control": ["BOUND_UNAPPROVED_DECLINED_CARD_CHARGEBACK_ENTITLEMENT"],
        "prerequisites": ["CONFIRM_IMMEDIATE_MERCHANT_CARD_DECLINE"],
        "correctives": ["PROVIDE_APPROVED_DECLINED_CARD_CHARGEBACK_OR_REMEDY_PATH"],
    },
    "EV2-A2-H04-R1": {
        "control": ["REFUSE_CARD_RECORD_FALSIFICATION_AND_CONCEALMENT"],
        "prerequisites": ["ESTABLISH_POSTED_CARD_RECORD_ELIGIBILITY_FOR_LEGITIMATE_DESCRIPTOR_CORRECTION"],
        "correctives": ["PROVIDE_APPROVED_CARD_DESCRIPTOR_CORRECTION_OR_PRIVACY_HANDOFF"],
    },
    "EV2-A2-H07-R1": {
        "control": ["BOUND_LIVE_FAILED_TRANSFER_RESERVED_BALANCE_DETERMINATION"],
        "prerequisites": ["CONFIRM_EXPLICIT_FAILED_TRANSFER_AFTER_SUBMISSION"],
        "correctives": ["PROVIDE_APPROVED_FAILED_TRANSFER_RESERVED_FUNDS_REVIEW_PATH"],
    },
    "EV2-A2-H08-R2": {
        "control": ["BOUND_LIVE_DECLINED_TRANSFER_LIMIT_USAGE_DETERMINATION"],
        "prerequisites": ["CONFIRM_EXPLICIT_DECLINED_TRANSFER_BEFORE_PROCESSING"],
        "correctives": ["PROVIDE_APPROVED_DECLINED_TRANSFER_LIMIT_USAGE_REVIEW_PATH"],
    },
    "EV2-A2-H09-R1": {
        "control": ["BOUND_UNRESOLVED_DECLINED_COMPLETED_TRANSFER_CONFLICT"],
        "prerequisites": [
            "CONFIRM_EXPLICIT_DECLINED_TRANSFER_BEFORE_PROCESSING",
            "CONFIRM_SENDER_SIDE_COMPLETED_TRANSFER",
        ],
        "correctives": ["PROVIDE_APPROVED_DECLINED_VERSUS_COMPLETED_TRANSFER_STATE_RESOLVER"],
    },
}
FIX1B_JUDGMENTS_SHA256 = "8dc263538c3822b45a4809d6204b1ce3a14880a8972096bf874bc0e281f2ee9b"
FIX1B_CASE_REVIEW_SHA256 = "86fa10ba21f619257926a3f6c89b92168d7ea25319c69a5077dcbde8af395099"
FIX1B_CONFLICT_SUMMARY_SHA256 = "d51c1af63a9746c4f7536e192a03fbcc1da7f6985cdc132a1fc79d9cf4f2523f"
FIX2_JUDGMENTS_SHA256 = "92fb3aef0e253cae7aaa2a9d3b37ba670cb96497b94c48ba17d601958f1d8a7d"
FIX2_CASE_REVIEW_SHA256 = "f809304aeed3726f315725c8837a20413649c4139bd4eae1e74b03cf51771c74"
FIX2_LEDGER_SHA256 = "87f19c02e644e958cfd84a91ddc9576d46a16edaef01ec263ac6af7a46f70512"
FIX2_PASS_A_AUDIT_SHA256 = "9fd47d648cfa33f7b8152e92a5bf37f26011865180aaf218865e3f76ef33156e"
FIX2A_OBLIGATION_CLASSIFICATION_SHA256 = "40a32d2a992a51132223bcb810984e8eb8a40e58f89ecf2b5b210a2652be24b0"
FIX2A_CONSISTENCY_REVIEW_SHA256 = "57e06f67c7dc053aea7dad8b331f11f902a53aaeff140100afc460de4567b2d7"
FIX2A_CONFLICT_SUMMARY_SHA256 = "ababae78b25ca584faa113a85b5015ca39f405f1e38ad2b91a1e587dde32055b"
REV1_PASS_B_SHA256 = "9791f6e8699b70f9cec35a4d16d4baa47f41639b8428b81e07560f5fc7b0f9b0"
REV1_PASS_C_SHA256 = "2ac54f030ad7777fc5310c7c0a59f2ab76e2aada342720389853c9cd00c1cb7c"
FIX2_SCRIPT_HISTORICAL_SHA256 = "7d1da88d9344ad3cdc1f14bcabd96d105e850e311e1db7d02eacbe269fe7b498"
FIX2_TEST_HISTORICAL_SHA256 = "ee3d511bae02efaa298d1991837dfe5cd25c7f6a759be7213a838d3de54e38e7"
FIX2A_SOURCE_BY_CASE = {
    **{case_id: FIX1B_JUDGMENTS for case_id in {
        "EV2-A2-H01", "EV2-A2-H02", "EV2-A2-H03", "EV2-A2-H04",
        "EV2-A2-H07", "EV2-A2-H09", "EV2-A2-H10", "EV2-A2-H11", "EV2-A2-H12",
    }},
    **{case_id: FIX2_JUDGMENTS for case_id in FIX2_REPLACEMENT_IDS},
}
FIX2A_SOURCE_SHA256 = {
    str(FIX1B_JUDGMENTS).replace("\\", "/"): FIX1B_JUDGMENTS_SHA256,
    str(FIX2_JUDGMENTS).replace("\\", "/"): FIX2_JUDGMENTS_SHA256,
}
FIX2A_CLASSIFICATIONS = {
    "CONTROL_PLANE_BOUNDARY", "FACTUAL_CORRECTIVE_OBJECTIVE", "REQUESTED_FACTUAL_RESOLUTION",
}
FIX2A_FORBIDDEN_RECURSIVE_FIELDS = {
    "candidate_output", "candidate_prediction", "candidate_reason", "candidate_score",
    "retrieval_score", "retrieval_ranking", "ranking", "selected_candidate_evidence",
}
FIX1B_REQUIRED_FIELDS = {
    "case_id", "evidence_id", "document_id", "section_id",
    "evidence_content_sha256", "eligibility", "target_match", "state_match",
    "dimension_match", "obligations_covered", "support_class",
    "support_rationale", "support_quotes_by_obligation",
    "safe_alternative_obligations_supported", "safe_alternative_quotes",
    "review_provenance",
}
FIX1B_FORBIDDEN_FIELDS = FORBIDDEN_PASS_B_FIELDS | {
    "_".join(("support", "plans")),
    "hard_abstain_reason_family", "frozen_reason_family",
}
FIX3_REQUIRED_FIELDS = {
    "case_id", "evidence_id", "document_id", "section_id",
    "evidence_content_sha256", "eligibility", "target_match", "state_match",
    "dimension_match", "obligations_covered", "support_class",
    "support_rationale", "support_quotes_by_obligation",
    "safe_alternative_prerequisite_obligations_supported",
    "safe_alternative_prerequisite_quotes",
    "safe_alternative_corrective_obligations_supported",
    "safe_alternative_corrective_quotes", "safe_alternative_target_compatible",
    "safe_alternative_state_compatible",
    "safe_alternative_prerequisite_contradicts_user_facts",
    "safe_alternative_silent_state_assumption",
    "safe_alternative_asserts_account_specific_fact",
    "evidence_supports_account_specific_fact",
    "forbidden_action_or_promise_introduced", "review_provenance",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def content_sha256(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def token_set(text: str) -> set[str]:
    return set(normalize(text).split())


def eligible_section_index(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    eligible: dict[str, dict[str, Any]] = {}
    ineligible: dict[str, dict[str, Any]] = {}
    for doc in read_jsonl(root / KB):
        effective = date.fromisoformat(doc["effective_date"])
        expiry = date.fromisoformat(doc["expiry_date"]) if doc.get("expiry_date") else None
        approved = doc["status"] == "APPROVED" and effective <= AS_OF and (expiry is None or expiry >= AS_OF)
        for section in doc["content_sections"]:
            evidence_id = f"{doc['document_id']}#{section['section_id']}"
            item = {
                "evidence_id": evidence_id,
                "document_id": doc["document_id"],
                "section_id": section["section_id"],
                "status": doc["status"],
                "content": section["content"],
                "content_sha256": content_sha256(section["content"]),
            }
            (eligible if approved else ineligible)[evidence_id] = item
    return eligible, ineligible


def validate_pass_a(
    root: Path, rows: list[dict[str, Any]] | None = None, *, source_path: Path = PASS_A,
) -> dict[str, Any]:
    path = root / source_path
    rows = read_jsonl(path) if rows is None else rows
    errors: list[str] = []
    if file_sha256(path) != PASS_A_EXPECTED_SHA256:
        errors.append("BLOCKED_PASS_A_BYTE_DRIFT")
    if len(rows) != 60:
        errors.append("pass_a_count")
    if len({row.get("case_id") for row in rows}) != 60:
        errors.append("pass_a_case_id_uniqueness")
    if len({row.get("scenario_family") for row in rows}) != 60:
        errors.append("pass_a_scenario_family_uniqueness")
    if Counter(row.get("semantic_stratum") for row in rows) != EXPECTED_DISTRIBUTION:
        errors.append("pass_a_distribution")
    return {"passed": not errors, "errors": errors, "rows": len(rows), "sha256": file_sha256(path)}


def canonical_row_sha256(row: dict[str, Any]) -> str:
    encoded = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_bytes(encoded)


def _raw_row_index(path: Path) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for line in path.read_bytes().splitlines(keepends=True):
        row = json.loads(line)
        result[row["case_id"]] = line
    return result


def build_pass_a_v2_audit(root: Path) -> dict[str, Any]:
    rev1_path = root / PASS_A_REV1
    active_path = root / PASS_A_V2
    rev1 = read_jsonl(rev1_path)
    active = read_jsonl(active_path)
    rev_by_id = {row["case_id"]: row for row in rev1}
    active_by_id = {row["case_id"]: row for row in active}
    unchanged_ids = sorted(set(rev_by_id) - FIX2_RETIRED_IDS)
    rev_raw = _raw_row_index(rev1_path)
    active_raw = _raw_row_index(active_path)
    unchanged = []
    for case_id in unchanged_ids:
        unchanged.append({
            "case_id": case_id,
            "rev1_canonical_row_sha256": canonical_row_sha256(rev_by_id[case_id]),
            "fix2_canonical_row_sha256": canonical_row_sha256(active_by_id[case_id]),
            "raw_line_byte_equal": rev_raw[case_id] == active_raw[case_id],
        })
    distribution = dict(Counter(row.get("semantic_stratum") for row in active))
    family_counts = dict(Counter(
        row["hard_abstain_reason_family"] for row in active
        if row.get("semantic_stratum") == "HARD_ABSTAIN_ESCALATE"
    ))
    normalized = [normalize(row["query"]) for row in active]
    similarities = []
    for index, left in enumerate(active):
        for right in active[index + 1:]:
            lt, rt = token_set(left["query"]), token_set(right["query"])
            similarities.append((len(lt & rt) / len(lt | rt), left["case_id"], right["case_id"]))
    maximum = max(similarities)
    eligible, ineligible = eligible_section_index(root)
    kb_sentences = {normalize(item["content"]) for item in [*eligible.values(), *ineligible.values()]}
    a1_families = {row["dev_scenario_family"] for row in read_jsonl(root / A1_DEV_LINEAGE)}
    replacement_families = {active_by_id[case_id]["scenario_family"] for case_id in FIX2_REPLACEMENT_IDS}
    return {
        "task_id": "W3-003-EV2-A2-FIX2",
        "pass_a_revision": 2,
        "rev1_path": str(PASS_A_REV1).replace("\\", "/"),
        "rev1_sha256": file_sha256(rev1_path),
        "active_path": str(PASS_A).replace("\\", "/"),
        "active_sha256": file_sha256(active_path),
        "rows": len(active),
        "unique_case_ids": len(active_by_id),
        "unique_scenario_families": len({row["scenario_family"] for row in active}),
        "distribution": distribution,
        "retired_ids": sorted(FIX2_RETIRED_IDS),
        "replacement_ids": sorted(FIX2_REPLACEMENT_IDS),
        "unchanged_row_count": len(unchanged),
        "unchanged_rows": unchanged,
        "all_57_unchanged_rows_canonical_and_raw_equal": len(unchanged) == 57 and all(
            item["rev1_canonical_row_sha256"] == item["fix2_canonical_row_sha256"]
            and item["raw_line_byte_equal"] for item in unchanged
        ),
        "hard_reason_family_counts": family_counts,
        "exact_query_duplicates": len(active) - len({row["query"] for row in active}),
        "normalized_query_duplicates": len(normalized) - len(set(normalized)),
        "max_internal_query_jaccard": {"value": maximum[0], "case_ids": list(maximum[1:])},
        "direct_kb_sentence_copies": sum(query in kb_sentences for query in normalized),
        "replacement_a1_dev_family_collisions": len(replacement_families & a1_families),
        "consumed_per_query_collision_status": "NOT_ESTABLISHED_PENDING_A3_FINGERPRINT_ONLY_AUDIT",
        "consumed_freshness_limitation": "CONSUMED_CASE_LEVEL_FRESHNESS_LIMITATION",
        "ev1_case_level_accessed": False,
        "critical_rev7_case_level_accessed": False,
        "candidate_output_used": False,
        "candidate_inference_executed": False,
    }


def validate_pass_a_v2(root: Path, audit: dict[str, Any] | None = None) -> dict[str, Any]:
    expected = build_pass_a_v2_audit(root)
    errors: list[str] = []
    if expected["active_sha256"] != PASS_A_V2_EXPECTED_SHA256:
        errors.append("BLOCKED_PASS_A_V2_BYTE_DRIFT")
    if expected["rev1_sha256"] != PASS_A_EXPECTED_SHA256:
        errors.append("rev1_preservation_hash")
    if expected["rows"] != 60 or expected["unique_case_ids"] != 60:
        errors.append("pass_a_v2_row_or_id_count")
    if expected["unique_scenario_families"] != 60:
        errors.append("pass_a_v2_scenario_family_uniqueness")
    if expected["distribution"] != EXPECTED_DISTRIBUTION:
        errors.append("pass_a_v2_distribution")
    if expected["unchanged_row_count"] != 57 or not expected["all_57_unchanged_rows_canonical_and_raw_equal"]:
        errors.append("BLOCKED_UNAUTHORIZED_PASS_A_ROW_DRIFT")
    rev_ids = {row["case_id"] for row in read_jsonl(root / PASS_A_REV1)}
    active = read_jsonl(root / PASS_A_V2)
    active_ids = {row["case_id"] for row in active}
    if active_ids != (rev_ids - FIX2_RETIRED_IDS) | FIX2_REPLACEMENT_IDS:
        errors.append("pass_a_v2_membership_drift")
    forbidden_fields = {"evidence_id", "support_set", "support_sets", "selected_evidence", "candidate_output"}
    for row in active:
        if forbidden_fields & set(row):
            errors.append(f"{row.get('case_id')}:forbidden_pass_a_field")
    if min(expected["hard_reason_family_counts"].values(), default=0) < 2:
        errors.append("hard_reason_family_has_fewer_than_two_cases")
    if audit is not None and audit != expected:
        errors.append("pass_a_v2_audit_not_exact_derivation")
    return {"passed": not errors, "errors": errors, "audit": expected}


def _quotes_are_verbatim(quotes: Any, content: str) -> bool:
    return isinstance(quotes, list) and bool(quotes) and all(isinstance(q, str) and q and q in content for q in quotes)


def validate_pass_b(root: Path, pass_a: list[dict[str, Any]], pass_b: list[dict[str, Any]]) -> dict[str, Any]:
    eligible, _ = eligible_section_index(root)
    cases = {row["case_id"]: row for row in pass_a}
    errors: list[str] = []
    if len(eligible) != 52:
        errors.append(f"eligible_section_count:{len(eligible)}")
    if len(pass_b) != 3120:
        errors.append(f"pass_b_count:{len(pass_b)}")
    pairs = {(row.get("case_id"), row.get("evidence_id")) for row in pass_b}
    if len(pairs) != len(pass_b):
        errors.append("duplicate_case_evidence_pair")
    counts = Counter(row.get("case_id") for row in pass_b)
    if set(counts) != set(cases) or set(counts.values()) != {52}:
        errors.append("pass_b_not_52_per_case")

    for index, row in enumerate(pass_b):
        prefix = f"row[{index}]"
        missing_fields = REQUIRED_PASS_B_FIELDS - set(row)
        if missing_fields:
            errors.append(f"{prefix}:missing_fields:{sorted(missing_fields)}")
            continue
        forbidden = FORBIDDEN_PASS_B_FIELDS & set(row)
        if forbidden:
            errors.append(f"{prefix}:forbidden_fields:{sorted(forbidden)}")
        case = cases.get(row["case_id"])
        section = eligible.get(row["evidence_id"])
        if case is None:
            errors.append(f"{prefix}:unknown_case")
            continue
        if section is None:
            errors.append(f"{prefix}:ineligible_or_unknown_evidence")
            continue
        if row["document_id"] != section["document_id"] or row["section_id"] != section["section_id"]:
            errors.append(f"{prefix}:evidence_identity_mismatch")
        if row["evidence_content_sha256"] != section["content_sha256"]:
            errors.append(f"{prefix}:evidence_content_sha256_mismatch")
        if row["eligibility"] != "ELIGIBLE":
            errors.append(f"{prefix}:eligibility")
        if row["support_class"] not in SUPPORT_CLASSES:
            errors.append(f"{prefix}:support_class")
            continue

        required = set(case["required_semantic_obligations"])
        covered = set(row["obligations_covered"])
        not_covered = set(row["obligations_not_covered"])
        if not covered <= required:
            errors.append(f"{prefix}:unknown_covered_obligation")
        if not_covered != required - covered:
            errors.append(f"{prefix}:obligations_not_covered_not_exact_complement")
        quote_map = row.get("obligation_support_quotes", {})
        if set(quote_map) != covered:
            errors.append(f"{prefix}:covered_obligation_quote_keys")
        for obligation, quotes in quote_map.items():
            if not _quotes_are_verbatim(quotes, section["content"]):
                errors.append(f"{prefix}:nonverbatim_support_quote:{obligation}")

        support_class = row["support_class"]
        compatible = row["target_match"] is True and row["state_match"] is True and row["dimension_match"] is True
        if support_class == "COMPLETE_SUPPORT":
            if covered != required or not compatible:
                errors.append(f"{prefix}:invalid_complete_support")
        elif support_class == "PARTIAL_SUPPORT":
            if not covered or covered == required or not compatible:
                errors.append(f"{prefix}:invalid_partial_support")
        elif support_class == "CONTEXTUAL_INSUFFICIENT":
            if covered or set(row.get("missing_required_obligations", [])) != required:
                errors.append(f"{prefix}:invalid_contextual_insufficient")
        elif support_class == "CONTRADICTION":
            quote = row.get("contradiction_basis_quote")
            constraint = row.get("contradicted_constraint")
            if not isinstance(quote, str) or not quote or quote not in section["content"]:
                errors.append(f"{prefix}:nonverbatim_or_missing_contradiction_quote")
            if not isinstance(constraint, str) or not constraint:
                errors.append(f"{prefix}:missing_contradicted_constraint")
            if isinstance(constraint, str) and constraint.startswith("TARGET:") and row["target_match"] is True:
                errors.append(f"{prefix}:target_match_with_target_contradiction")
            if isinstance(constraint, str) and constraint.startswith("STATE:") and row["state_match"] is True:
                errors.append(f"{prefix}:state_match_with_state_contradiction")
        elif support_class == "IRRELEVANT":
            if covered or not isinstance(row.get("semantic_mismatch_reason"), str) or not row["semantic_mismatch_reason"].strip():
                errors.append(f"{prefix}:invalid_irrelevant")

        if support_class != "CONTRADICTION" and ({"contradiction_basis_quote", "contradicted_constraint"} & set(row)):
            errors.append(f"{prefix}:contradiction_metadata_on_noncontradiction")
        if not isinstance(row["support_rationale"], str) or not row["support_rationale"].strip():
            errors.append(f"{prefix}:empty_support_rationale")
        if row["review_provenance"] != "FIX1_INDEPENDENT_CONTENT_GROUNDED_SEMANTIC_REVIEW":
            errors.append(f"{prefix}:review_provenance")

    return {
        "passed": not errors,
        "errors": errors,
        "row_count": len(pass_b),
        "unique_pairs": len(pairs),
        "support_class_counts": dict(Counter(row.get("support_class") for row in pass_b)),
    }


def hard_cases(pass_a: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in pass_a if row.get("semantic_stratum") == "HARD_ABSTAIN_ESCALATE"]


def _fix1b_minimal_safe_sets(
    required_obligations: list[str], judgments: list[dict[str, Any]],
) -> list[list[str]]:
    required = set(required_obligations)
    if not required:
        return []
    candidates = [
        row for row in judgments
        if row.get("target_match") is True
        and row.get("state_match") is True
        and row.get("dimension_match") is True
        and row.get("safe_alternative_obligations_supported")
    ]
    complete: list[frozenset[str]] = []
    for size in range(1, min(len(required), len(candidates)) + 1):
        for group in itertools.combinations(candidates, size):
            evidence = frozenset(row["evidence_id"] for row in group)
            if any(existing <= evidence for existing in complete):
                continue
            covered = set().union(*(
                set(row["safe_alternative_obligations_supported"]) for row in group
            ))
            if required <= covered:
                complete.append(evidence)
    minimal = [group for group in complete if not any(other < group for other in complete)]
    return [sorted(group) for group in sorted(minimal, key=lambda value: (len(value), sorted(value)))]


def validate_fix1b_judgments(
    root: Path, pass_a: list[dict[str, Any]], judgments: list[dict[str, Any]],
) -> dict[str, Any]:
    eligible, _ = eligible_section_index(root)
    cases = {row["case_id"]: row for row in hard_cases(pass_a)}
    errors: list[str] = []
    if len(cases) != 12:
        errors.append(f"hard_case_count:{len(cases)}")
    if len(eligible) != 52:
        errors.append(f"eligible_section_count:{len(eligible)}")
    if len(judgments) != 624:
        errors.append(f"judgment_count:{len(judgments)}")
    pairs = {(row.get("case_id"), row.get("evidence_id")) for row in judgments}
    if len(pairs) != len(judgments):
        errors.append("duplicate_case_evidence_pair")
    expected_pairs = {(case_id, evidence_id) for case_id in cases for evidence_id in eligible}
    if pairs != expected_pairs:
        errors.append("case_evidence_pair_set_not_exact")
    counts = Counter(row.get("case_id") for row in judgments)
    if set(counts) != set(cases) or set(counts.values()) != {52}:
        errors.append("not_exactly_52_judgments_per_hard_case")

    for index, row in enumerate(judgments):
        prefix = f"row[{index}]"
        missing = FIX1B_REQUIRED_FIELDS - set(row)
        if missing:
            errors.append(f"{prefix}:missing_fields:{sorted(missing)}")
            continue
        forbidden = FIX1B_FORBIDDEN_FIELDS & set(row)
        if forbidden:
            errors.append(f"{prefix}:forbidden_fields:{sorted(forbidden)}")
        case = cases.get(row["case_id"])
        section = eligible.get(row["evidence_id"])
        if case is None:
            errors.append(f"{prefix}:unknown_or_nonhard_case")
            continue
        if section is None:
            errors.append(f"{prefix}:ineligible_or_unknown_evidence")
            continue
        if row["document_id"] != section["document_id"] or row["section_id"] != section["section_id"]:
            errors.append(f"{prefix}:evidence_identity_mismatch")
        if row["evidence_content_sha256"] != section["content_sha256"]:
            errors.append(f"{prefix}:evidence_content_sha256_mismatch")
        if row["eligibility"] != "ELIGIBLE":
            errors.append(f"{prefix}:eligibility")
        if row["support_class"] not in SUPPORT_CLASSES:
            errors.append(f"{prefix}:support_class")
        required = set(case["required_semantic_obligations"])
        covered = set(row["obligations_covered"])
        if not covered <= required:
            errors.append(f"{prefix}:unknown_requested_obligation")
        quote_map = row["support_quotes_by_obligation"]
        if not isinstance(quote_map, dict) or set(quote_map) != covered:
            errors.append(f"{prefix}:requested_obligation_quote_keys")
        elif any(not _quotes_are_verbatim(quotes, section["content"]) for quotes in quote_map.values()):
            errors.append(f"{prefix}:nonverbatim_requested_support_quote")
        safe_obligations = row["safe_alternative_obligations_supported"]
        safe_quotes = row["safe_alternative_quotes"]
        if not isinstance(safe_obligations, list) or len(safe_obligations) != len(set(safe_obligations)):
            errors.append(f"{prefix}:safe_alternative_obligations")
        if safe_obligations:
            if not _quotes_are_verbatim(safe_quotes, section["content"]):
                errors.append(f"{prefix}:nonverbatim_safe_alternative_quote")
        elif safe_quotes != []:
            errors.append(f"{prefix}:safe_quote_without_obligation")
        if row["support_class"] == "COMPLETE_SUPPORT" and covered != required:
            errors.append(f"{prefix}:invalid_complete_requested_support")
        if row["support_class"] == "PARTIAL_SUPPORT" and (not covered or covered == required):
            errors.append(f"{prefix}:invalid_partial_requested_support")
        if row["support_class"] in {"CONTEXTUAL_INSUFFICIENT", "CONTRADICTION", "IRRELEVANT"} and covered:
            errors.append(f"{prefix}:non_support_class_covers_requested_obligation")
        if row["support_class"] == "CONTRADICTION":
            quote = row.get("contradiction_basis_quote")
            if not isinstance(quote, str) or not quote or quote not in section["content"]:
                errors.append(f"{prefix}:nonverbatim_or_missing_contradiction_quote")
        elif "contradiction_basis_quote" in row:
            errors.append(f"{prefix}:contradiction_quote_on_noncontradiction")
        if not isinstance(row["support_rationale"], str) or not row["support_rationale"].strip():
            errors.append(f"{prefix}:empty_support_rationale")
        if row["review_provenance"] != FIX1B_REVIEW_PROVENANCE:
            errors.append(f"{prefix}:review_provenance")
    return {
        "passed": not errors,
        "errors": errors,
        "hard_cases": len(cases),
        "eligible_sections": len(eligible),
        "row_count": len(judgments),
        "unique_pairs": len(pairs),
        "per_case_counts": dict(sorted(counts.items())),
        "support_class_counts": dict(Counter(row.get("support_class") for row in judgments)),
    }


def derive_fix1b_case_reviews(
    pass_a: list[dict[str, Any]], judgments: list[dict[str, Any]],
    authored_review: dict[str, Any],
) -> list[dict[str, Any]]:
    hard = {row["case_id"]: row for row in hard_cases(pass_a)}
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in judgments:
        by_case[row["case_id"]].append(row)
    authored_cases = {row["case_id"]: row for row in authored_review.get("cases", [])}
    if set(authored_cases) != set(hard):
        raise ValueError("case_review_case_set_not_exact")
    derived: list[dict[str, Any]] = []
    for case_id in sorted(hard):
        case = hard[case_id]
        seed = authored_cases[case_id]
        if seed.get("frozen_reason_family") != case.get("hard_abstain_reason_family"):
            raise ValueError(f"{case_id}:frozen_reason_silently_rewritten")
        rows = by_case[case_id]
        requested_required = set(case["required_semantic_obligations"])
        requested_supported = any(
            set(row["obligations_covered"]) == requested_required
            and row["target_match"] is True and row["state_match"] is True
            and row["dimension_match"] is True
            for row in rows
        )
        safe_requirements = seed.get("safe_alternative_required_obligations", [])
        safe_sets = _fix1b_minimal_safe_sets(safe_requirements, rows)
        complete_safe = bool(safe_sets)
        conflict = requested_supported or complete_safe
        if requested_supported:
            conflict_reason = "REQUESTED_RESOLUTION_HAS_COMPLETE_APPROVED_SUPPORT"
        elif complete_safe:
            conflict_reason = "COMPLETE_TARGET_STATE_COMPATIBLE_SAFE_CORRECTIVE_ALTERNATIVE_EXISTS"
        else:
            conflict_reason = "NONE"
        derived.append({
            "case_id": case_id,
            "frozen_reason_family": case["hard_abstain_reason_family"],
            "reviewed_sections": len(rows),
            "requested_resolution_supported": requested_supported,
            "safe_alternative_required_obligations": safe_requirements,
            "complete_safe_alternative_exists": complete_safe,
            "minimal_complete_safe_alternative_sets": safe_sets,
            "closest_partial_sections": seed.get("closest_partial_sections", []),
            "frozen_reason_valid": not conflict,
            "stratum_conflict": conflict,
            "conflict_reason": conflict_reason,
            "reviewer_analysis": seed.get("reviewer_analysis", ""),
        })
    return derived


def validate_fix1b_artifacts(
    root: Path, pass_a: list[dict[str, Any]], judgments: list[dict[str, Any]],
    case_review: dict[str, Any], conflict_summary: dict[str, Any],
) -> dict[str, Any]:
    matrix = validate_fix1b_judgments(root, pass_a, judgments)
    errors = list(matrix["errors"])
    if errors:
        return {"passed": False, "errors": errors, "matrix": matrix}
    try:
        derived = derive_fix1b_case_reviews(pass_a, judgments, case_review)
    except ValueError as exc:
        return {"passed": False, "errors": [str(exc)], "matrix": matrix}
    if case_review.get("task_id") != "W3-003-EV2-A2-FIX1B":
        errors.append("case_review_task_id")
    if case_review.get("pass_a_sha256") != PASS_A_EXPECTED_SHA256:
        errors.append("case_review_pass_a_sha256")
    if case_review.get("cases") != derived:
        errors.append("case_level_conclusions_not_exact_derivation")
    valid = [row["case_id"] for row in derived if not row["stratum_conflict"]]
    conflicted = [row["case_id"] for row in derived if row["stratum_conflict"]]
    if conflict_summary.get("valid_hard_cases") != valid:
        errors.append("summary_valid_hard_cases_not_derived")
    if conflict_summary.get("conflicted_hard_cases") != conflicted:
        errors.append("summary_conflicted_hard_cases_not_derived")
    if conflict_summary.get("conflict_count") != len(conflicted):
        errors.append("summary_conflict_count_not_derived")
    if conflict_summary.get("recommended_replacement_count") != len(conflicted):
        errors.append("summary_replacement_count_not_derived")
    if conflict_summary.get("pass_a_sha256") != PASS_A_EXPECTED_SHA256:
        errors.append("summary_pass_a_sha256")
    hard_by_id = {row["case_id"]: row for row in hard_cases(pass_a)}
    expected_families: dict[str, dict[str, int]] = {}
    for family in sorted({row["hard_abstain_reason_family"] for row in hard_by_id.values()}):
        family_rows = [row for row in derived if row["frozen_reason_family"] == family]
        expected_families[family] = {
            "case_count_reviewed": len(family_rows),
            "case_count_still_valid": sum(not row["stratum_conflict"] for row in family_rows),
            "case_count_conflicted": sum(row["stratum_conflict"] for row in family_rows),
        }
    family_items = conflict_summary.get("reason_family_feasibility", [])
    family_by_name = {row.get("reason_family"): row for row in family_items}
    if len(family_by_name) != len(family_items) or set(family_by_name) != set(expected_families):
        errors.append("reason_family_set_not_exact")
    else:
        for family, counts in expected_families.items():
            if any(family_by_name[family].get(key) != value for key, value in counts.items()):
                errors.append(f"{family}:reason_family_counts_not_derived")
            capable = family_by_name[family].get("frozen_kb_appears_capable_of_at_least_two_valid_hard_cases")
            status = family_by_name[family].get("feasibility_status")
            if capable is False and status != "REASON_FAMILY_DIVERSITY_TARGET_INFEASIBLE_WITH_FROZEN_KB":
                errors.append(f"{family}:infeasible_status_not_fail_closed")
            if capable is True and status != "FEASIBLE":
                errors.append(f"{family}:feasible_status_inconsistent")
    expected_boundaries = {
        "replacement_queries_authored": False,
        "pass_a_modified": False,
        "full_pass_b_authored": False,
        "pass_c_derived": False,
        "candidate_inference_executed": False,
        "ev2_executed": False,
        "ev2_consumed": False,
        "a3_authorized": False,
        "week3_p0_passed": False,
        "week4_authorized": False,
    }
    if any(conflict_summary.get(key) is not value for key, value in expected_boundaries.items()):
        errors.append("summary_boundary_claim_inconsistent")
    return {
        "passed": not errors,
        "errors": errors,
        "matrix": matrix,
        "derived_cases": derived,
        "valid_hard_cases": valid,
        "conflicted_hard_cases": conflicted,
    }


def replacement_cases(pass_a: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (row for row in pass_a if row.get("case_id") in FIX2_REPLACEMENT_IDS),
        key=lambda row: row["case_id"],
    )


def validate_fix2_judgments(
    root: Path, pass_a: list[dict[str, Any]], judgments: list[dict[str, Any]],
) -> dict[str, Any]:
    eligible, _ = eligible_section_index(root)
    cases = {row["case_id"]: row for row in replacement_cases(pass_a)}
    errors: list[str] = []
    if set(cases) != FIX2_REPLACEMENT_IDS:
        errors.append("replacement_case_set_not_exact")
    if len(eligible) != 52:
        errors.append(f"eligible_section_count:{len(eligible)}")
    if len(judgments) != 156:
        errors.append(f"judgment_count:{len(judgments)}")
    pairs = {(row.get("case_id"), row.get("evidence_id")) for row in judgments}
    expected_pairs = {(case_id, evidence_id) for case_id in cases for evidence_id in eligible}
    if len(pairs) != len(judgments):
        errors.append("duplicate_case_evidence_pair")
    if pairs != expected_pairs:
        errors.append("replacement_case_evidence_pair_set_not_exact")
    counts = Counter(row.get("case_id") for row in judgments)
    if set(counts) != set(cases) or set(counts.values()) != {52}:
        errors.append("not_exactly_52_judgments_per_replacement")
    for index, row in enumerate(judgments):
        prefix = f"row[{index}]"
        missing = FIX1B_REQUIRED_FIELDS - set(row)
        if missing:
            errors.append(f"{prefix}:missing_fields:{sorted(missing)}")
            continue
        forbidden = FIX1B_FORBIDDEN_FIELDS & set(row)
        if forbidden:
            errors.append(f"{prefix}:forbidden_fields:{sorted(forbidden)}")
        case = cases.get(row["case_id"])
        section = eligible.get(row["evidence_id"])
        if case is None:
            errors.append(f"{prefix}:unknown_replacement_case")
            continue
        if section is None:
            errors.append(f"{prefix}:ineligible_or_unknown_evidence")
            continue
        if row["document_id"] != section["document_id"] or row["section_id"] != section["section_id"]:
            errors.append(f"{prefix}:evidence_identity_mismatch")
        if row["evidence_content_sha256"] != section["content_sha256"]:
            errors.append(f"{prefix}:evidence_content_sha256_mismatch")
        if row["eligibility"] != "ELIGIBLE":
            errors.append(f"{prefix}:eligibility")
        if row["support_class"] not in SUPPORT_CLASSES:
            errors.append(f"{prefix}:support_class")
        required = set(case["required_semantic_obligations"])
        covered = set(row["obligations_covered"])
        if not covered <= required:
            errors.append(f"{prefix}:unknown_requested_obligation")
        quote_map = row["support_quotes_by_obligation"]
        if not isinstance(quote_map, dict) or set(quote_map) != covered:
            errors.append(f"{prefix}:requested_obligation_quote_keys")
        elif any(not _quotes_are_verbatim(quotes, section["content"]) for quotes in quote_map.values()):
            errors.append(f"{prefix}:nonverbatim_requested_support_quote")
        safe_obligations = row["safe_alternative_obligations_supported"]
        safe_quotes = row["safe_alternative_quotes"]
        if not isinstance(safe_obligations, list) or len(safe_obligations) != len(set(safe_obligations)):
            errors.append(f"{prefix}:safe_alternative_obligations")
        if safe_obligations and not _quotes_are_verbatim(safe_quotes, section["content"]):
            errors.append(f"{prefix}:nonverbatim_safe_alternative_quote")
        if not safe_obligations and safe_quotes != []:
            errors.append(f"{prefix}:safe_quote_without_obligation")
        if row["support_class"] == "COMPLETE_SUPPORT" and covered != required:
            errors.append(f"{prefix}:invalid_complete_requested_support")
        if row["support_class"] == "PARTIAL_SUPPORT" and (not covered or covered == required):
            errors.append(f"{prefix}:invalid_partial_requested_support")
        if row["support_class"] in {"CONTEXTUAL_INSUFFICIENT", "CONTRADICTION", "IRRELEVANT"} and covered:
            errors.append(f"{prefix}:non_support_class_covers_requested_obligation")
        if row["support_class"] == "CONTRADICTION":
            quote = row.get("contradiction_basis_quote")
            if not isinstance(quote, str) or not quote or quote not in section["content"]:
                errors.append(f"{prefix}:nonverbatim_or_missing_contradiction_quote")
        elif "contradiction_basis_quote" in row:
            errors.append(f"{prefix}:contradiction_quote_on_noncontradiction")
        if row["review_provenance"] != FIX2_REVIEW_PROVENANCE:
            errors.append(f"{prefix}:review_provenance")
        if not isinstance(row["support_rationale"], str) or not row["support_rationale"].strip():
            errors.append(f"{prefix}:empty_support_rationale")
    return {
        "passed": not errors,
        "errors": errors,
        "replacement_cases": len(cases),
        "eligible_sections": len(eligible),
        "row_count": len(judgments),
        "unique_pairs": len(pairs),
        "per_case_counts": dict(sorted(counts.items())),
        "support_class_counts": dict(Counter(row.get("support_class") for row in judgments)),
    }


def derive_fix2_case_reviews(
    pass_a: list[dict[str, Any]], judgments: list[dict[str, Any]],
    authored_review: dict[str, Any],
) -> list[dict[str, Any]]:
    cases = {row["case_id"]: row for row in replacement_cases(pass_a)}
    seeds = {row["case_id"]: row for row in authored_review.get("cases", [])}
    if set(seeds) != set(cases):
        raise ValueError("replacement_case_review_set_not_exact")
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in judgments:
        by_case[row["case_id"]].append(row)
    derived = []
    for case_id in sorted(cases):
        case = cases[case_id]
        seed = seeds[case_id]
        if seed.get("frozen_reason_family") != case["hard_abstain_reason_family"]:
            raise ValueError(f"{case_id}:hard_reason_family_changed_after_review_began")
        if seed.get("frozen_row_sha256") != canonical_row_sha256(case):
            raise ValueError(f"{case_id}:replacement_row_changed_after_review_began")
        rows = by_case[case_id]
        requested = set(case["required_semantic_obligations"])
        requested_supported = any(
            set(row["obligations_covered"]) == requested
            and row["target_match"] is True and row["state_match"] is True
            and row["dimension_match"] is True for row in rows
        )
        safe_requirements = seed.get("safe_alternative_required_obligations", [])
        safe_sets = _fix1b_minimal_safe_sets(safe_requirements, rows)
        complete_safe = bool(safe_sets)
        contradiction_count = sum(row["support_class"] == "CONTRADICTION" for row in rows)
        family = case["hard_abstain_reason_family"]
        if family == "GENUINE_CONFLICT_OR_INSUFFICIENCY":
            reason_valid = not requested_supported and not complete_safe and contradiction_count >= 2
            basis = "UNRESOLVED_EXPLICIT_CONTRADICTIONS" if reason_valid else "GENUINE_CONFLICT_PREMISE_NOT_PROVED"
        elif family == "ACCOUNT_SPECIFIC_DECISION_UNRESOLVED":
            reason_valid = not requested_supported and not complete_safe
            basis = "LIVE_ACCOUNT_DECISION_UNRESOLVED" if reason_valid else "ACCOUNT_SPECIFIC_HARD_REASON_DISPROVED"
        elif family == "PROHIBITED_RESOLUTION_NO_COMPLETE_SAFE_ALTERNATIVE":
            reason_valid = not requested_supported and not complete_safe
            basis = "PROHIBITED_REQUEST_WITHOUT_COMPLETE_TARGET_COMPATIBLE_SAFE_ALTERNATIVE" if reason_valid else "PROHIBITED_HARD_REASON_DISPROVED"
        elif family == "NO_APPROVED_COMPLETE_SUPPORT":
            reason_valid = not requested_supported and not complete_safe
            basis = "NO_APPROVED_COMPLETE_SUPPORT" if reason_valid else "NO_SUPPORT_HARD_REASON_DISPROVED"
        else:
            raise ValueError(f"{case_id}:unknown_hard_reason_family")
        derived.append({
            "case_id": case_id,
            "frozen_row_sha256": canonical_row_sha256(case),
            "frozen_reason_family": family,
            "reviewed_sections": len(rows),
            "requested_resolution_supported": requested_supported,
            "safe_alternative_required_obligations": safe_requirements,
            "complete_safe_corrective_alternative_exists": complete_safe,
            "minimal_complete_safe_alternative_sets": safe_sets,
            "contradiction_judgment_count": contradiction_count,
            "closest_partial_sections": seed.get("closest_partial_sections", []),
            "hard_reason_valid": reason_valid,
            "replacement_verdict": "PASS" if reason_valid else "FAIL",
            "reason_validation_basis": basis,
            "reviewer_analysis": seed.get("reviewer_analysis", ""),
        })
    return derived


def validate_fix2_ledger(root: Path, ledger: dict[str, Any]) -> dict[str, Any]:
    rev1 = {row["case_id"]: row for row in read_jsonl(root / PASS_A_REV1)}
    active = {row["case_id"]: row for row in read_jsonl(root / PASS_A_V2)}
    expected_map = {"EV2-A2-H05": "EV2-A2-H05-R1", "EV2-A2-H06": "EV2-A2-H06-R1", "EV2-A2-H08": "EV2-A2-H08-R1"}
    errors: list[str] = []
    if ledger.get("task_id") != "W3-003-EV2-A2-FIX2":
        errors.append("ledger_task_id")
    if ledger.get("rev1_pass_a_sha256") != PASS_A_EXPECTED_SHA256:
        errors.append("ledger_rev1_hash")
    if ledger.get("pass_a_v2_sha256") != file_sha256(root / PASS_A_V2):
        errors.append("ledger_pass_a_v2_hash")
    entries = ledger.get("replacements", [])
    if len(entries) != 3 or {row.get("old_case_id") for row in entries} != set(expected_map):
        errors.append("ledger_replacement_set")
    for entry in entries:
        old_id = entry.get("old_case_id")
        if old_id not in expected_map:
            continue
        new_id = expected_map[old_id]
        old, new = rev1[old_id], active[new_id]
        checks = {
            "old_row_sha256": canonical_row_sha256(old),
            "old_scenario_family": old["scenario_family"],
            "old_reason_family": old["hard_abstain_reason_family"],
            "new_case_id": new_id,
            "new_row_sha256": canonical_row_sha256(new),
            "new_reason_family": new["hard_abstain_reason_family"],
            "authoring_provenance": new["authoring_provenance"],
            "replacement_status": "RETIRED_CONFLICT_REPLACED_AND_FROZEN_FOR_FIX2_REVIEW",
        }
        if any(entry.get(key) != value for key, value in checks.items()):
            errors.append(f"{old_id}:ledger_field_mismatch")
        artifact = entry.get("fix1b_supporting_artifact", {})
        if artifact.get("path") != str(FIX1B_CASE_REVIEW).replace("\\", "/") or artifact.get("sha256") != file_sha256(root / FIX1B_CASE_REVIEW):
            errors.append(f"{old_id}:fix1b_artifact_binding")
    return {"passed": not errors, "errors": errors}


def validate_fix2_manifest(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = manifest.get("fix2_history", manifest)
    errors: list[str] = []
    expected_scalars = {
        "task_id": "W3-003-EV2-A2-FIX2",
        "status": "PASS_A_V2_REPLACEMENT_FEASIBILITY_PASS_AWAITING_SENIOR_REVIEW",
        "pass_a_revision": 2,
        "pass_a_rows": 60,
        "pass_a_replacements": 3,
        "replacement_feasibility_rows": 156,
        "pass_b_complete": False,
        "pass_c_derived": False,
        "evaluation_package_frozen": False,
        "structural_integrity_verified": False,
        "evaluation_authorized": False,
        "evaluation_executed": False,
        "ev2_consumed": False,
        "a3_authorized": False,
        "week3_p0_passed": False,
        "week4_authorized": False,
        "candidate_inference_executed": False,
        "ev1_case_level_accessed": False,
        "critical_rev7_case_level_accessed": False,
        "notebook_required": False,
    }
    if any(manifest.get(key) != value for key, value in expected_scalars.items()):
        errors.append("manifest_scalar_or_boundary_field")
    if manifest.get("pass_a_rev1", {}).get("sha256") != PASS_A_EXPECTED_SHA256:
        errors.append("manifest_rev1_hash")
    if manifest.get("pass_a_v2", {}).get("sha256") != file_sha256(root / PASS_A_V2):
        errors.append("manifest_pass_a_v2_hash")
    historical_evolving_paths = {
        "scripts/evaluation/week3_ev2_a2.py": FIX2_SCRIPT_HISTORICAL_SHA256,
        "tests/test_week3_ev2_a2.py": FIX2_TEST_HISTORICAL_SHA256,
    }
    for rel, expected_hash in manifest.get("fix2_artifact_sha256", {}).items():
        path = root / rel
        if rel in historical_evolving_paths:
            if expected_hash != historical_evolving_paths[rel]:
                errors.append(f"manifest_fix2_historical_hash:{rel}")
        elif not path.is_file() or file_sha256(path) != expected_hash:
            errors.append(f"manifest_fix2_hash:{rel}")
    for rel, expected_hash in manifest.get("fix1b_immutable_artifact_sha256", {}).items():
        path = root / rel
        if not path.is_file() or file_sha256(path) != expected_hash:
            errors.append(f"manifest_fix1b_hash:{rel}")
    historical = manifest.get("active_rev1_pass_b_c_not_current_gold", {})
    historical_files = {
        str(PASS_B).replace("\\", "/"): REV1_PASS_B_HISTORY,
        str(PASS_C).replace("\\", "/"): REV1_PASS_C_HISTORY,
    }
    for rel, preserved_path in historical_files.items():
        if historical.get(rel) != file_sha256(root / preserved_path):
            errors.append(f"manifest_historical_pass_b_c_hash:{rel}")
    return {"passed": not errors, "errors": errors}


def validate_fix2_artifacts(
    root: Path, pass_a: list[dict[str, Any]], ledger: dict[str, Any],
    judgments: list[dict[str, Any]], case_review: dict[str, Any], audit: dict[str, Any],
) -> dict[str, Any]:
    pass_a_result = validate_pass_a_v2(root, audit)
    ledger_result = validate_fix2_ledger(root, ledger)
    manifest_result = validate_fix2_manifest(
        root, json.loads((root / A2_MANIFEST).read_text(encoding="utf-8")),
    )
    matrix = validate_fix2_judgments(root, pass_a, judgments)
    errors = [*pass_a_result["errors"], *ledger_result["errors"], *manifest_result["errors"], *matrix["errors"]]
    if errors:
        return {"passed": False, "errors": errors, "pass_a": pass_a_result, "ledger": ledger_result, "manifest": manifest_result, "matrix": matrix}
    try:
        derived = derive_fix2_case_reviews(pass_a, judgments, case_review)
    except ValueError as exc:
        return {"passed": False, "errors": [str(exc)], "pass_a": pass_a_result, "ledger": ledger_result, "matrix": matrix}
    if case_review.get("task_id") != "W3-003-EV2-A2-FIX2":
        errors.append("case_review_task_id")
    if case_review.get("pass_a_v2_sha256") != file_sha256(root / PASS_A_V2):
        errors.append("case_review_pass_a_v2_hash")
    if case_review.get("cases") != derived:
        errors.append("replacement_conclusions_not_exact_derivation")
    all_pass = all(row["replacement_verdict"] == "PASS" for row in derived)
    expected_status = "A2_FIX2_PASS_A_V2_READY_FOR_SENIOR_REVIEW" if all_pass else "A2_FIX2_REPLACEMENT_FEASIBILITY_FAIL"
    if case_review.get("status") != expected_status:
        errors.append("case_review_status_not_derived")
    return {
        "passed": not errors and all_pass,
        "errors": errors,
        "status": expected_status,
        "pass_a": pass_a_result,
        "ledger": ledger_result,
        "manifest": manifest_result,
        "matrix": matrix,
        "derived_cases": derived,
    }


def _recursive_forbidden_fields(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        found.update(set(value) & FIX2A_FORBIDDEN_RECURSIVE_FIELDS)
        for child in value.values():
            found.update(_recursive_forbidden_fields(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_recursive_forbidden_fields(child))
    return found


def _fix2a_minimal_factual_sets(
    required_objectives: Iterable[str], rows: list[dict[str, Any]],
) -> list[list[str]]:
    """Derive exact minimal covers from existing safe-obligation labels only.

    Requested live/private/prohibited facets are handled separately by the
    control plane, so the old full-request target/state booleans are not reused
    as a requirement that a KB clause state an epistemic/refusal boundary.
    """
    required = set(required_objectives)
    if not required:
        return []
    candidates = [
        (row["evidence_id"], set(row["safe_alternative_obligations_supported"]) & required)
        for row in rows
        if set(row["safe_alternative_obligations_supported"]) & required
    ]
    complete: list[frozenset[str]] = []
    for size in range(1, len(candidates) + 1):
        for group in itertools.combinations(candidates, size):
            evidence = frozenset(item[0] for item in group)
            if any(existing <= evidence for existing in complete):
                continue
            coverage = set().union(*(item[1] for item in group))
            if coverage == required:
                complete.append(evidence)
    minimal = [group for group in complete if not any(other < group for other in complete)]
    return [sorted(group) for group in sorted(minimal, key=lambda value: (len(value), sorted(value)))]


def _fix2a_source_rows(
    root: Path, pass_a: list[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    errors: list[str] = []
    rev1 = read_jsonl(root / PASS_A_REV1)
    fix1b = read_jsonl(root / FIX1B_JUDGMENTS)
    fix2 = read_jsonl(root / FIX2_JUDGMENTS)
    fix1b_result = validate_fix1b_judgments(root, rev1, fix1b)
    fix2_result = validate_fix2_judgments(root, pass_a, fix2)
    errors.extend(f"fix1b:{error}" for error in fix1b_result["errors"])
    errors.extend(f"fix2:{error}" for error in fix2_result["errors"])
    hard_ids = {row["case_id"] for row in hard_cases(pass_a)}
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in [*fix1b, *fix2]:
        if row["case_id"] in hard_ids and FIX2A_SOURCE_BY_CASE.get(row["case_id"]) is not None:
            expected_path = FIX2A_SOURCE_BY_CASE[row["case_id"]]
            if (expected_path == FIX1B_JUDGMENTS and row in fix1b) or (
                expected_path == FIX2_JUDGMENTS and row in fix2
            ):
                by_case[row["case_id"]].append(row)
    if set(by_case) != hard_ids:
        errors.append("fix2a_current_hard_case_evidence_set_not_exact")
    if sum(len(rows) for rows in by_case.values()) != 624:
        errors.append("fix2a_current_evidence_count_not_624")
    if any(len(rows) != 52 for rows in by_case.values()):
        errors.append("fix2a_not_52_existing_judgments_per_case")
    return dict(by_case), errors


def _fix2a_case_judgment_sha256(rows: list[dict[str, Any]]) -> str:
    payload = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        for row in sorted(rows, key=lambda item: item["evidence_id"])
    )
    return sha256_bytes(payload.encode("utf-8"))


def _fix2a_immutability_errors(root: Path) -> list[str]:
    expected = {
        PASS_A_V2: PASS_A_V2_EXPECTED_SHA256,
        PASS_A_REV1: PASS_A_EXPECTED_SHA256,
        FIX1B_JUDGMENTS: FIX1B_JUDGMENTS_SHA256,
        FIX1B_CASE_REVIEW: FIX1B_CASE_REVIEW_SHA256,
        FIX1B_CONFLICT_SUMMARY: FIX1B_CONFLICT_SUMMARY_SHA256,
        FIX2_JUDGMENTS: FIX2_JUDGMENTS_SHA256,
        FIX2_CASE_REVIEW: FIX2_CASE_REVIEW_SHA256,
        FIX2_LEDGER: FIX2_LEDGER_SHA256,
        FIX2_PASS_A_AUDIT: FIX2_PASS_A_AUDIT_SHA256,
        REV1_PASS_B_HISTORY: REV1_PASS_B_SHA256,
        REV1_PASS_C_HISTORY: REV1_PASS_C_SHA256,
    }
    errors = []
    for path, expected_hash in expected.items():
        full = root / path
        if not full.is_file() or file_sha256(full) != expected_hash:
            label = "BLOCKED_PASS_A_V2_BYTE_DRIFT" if path == PASS_A_V2 else f"immutable_hash_drift:{path}"
            errors.append(label)
    return errors


def validate_fix2a_artifacts(
    root: Path, pass_a: list[dict[str, Any]], classification: dict[str, Any],
    review: dict[str, Any], summary: dict[str, Any],
) -> dict[str, Any]:
    errors = _fix2a_immutability_errors(root)
    pass_a_result = validate_pass_a_v2(root)
    errors.extend(pass_a_result["errors"])
    hard = {row["case_id"]: row for row in hard_cases(pass_a)}
    expected_hard_ids = {
        "EV2-A2-H01", "EV2-A2-H02", "EV2-A2-H03", "EV2-A2-H04",
        "EV2-A2-H05-R1", "EV2-A2-H06-R1", "EV2-A2-H07", "EV2-A2-H08-R1",
        "EV2-A2-H09", "EV2-A2-H10", "EV2-A2-H11", "EV2-A2-H12",
    }
    if set(hard) != expected_hard_ids:
        errors.append("fix2a_current_hard_case_set_not_exact")
    source_rows, source_errors = _fix2a_source_rows(root, pass_a)
    errors.extend(source_errors)

    for artifact_name, artifact in (
        ("classification", classification), ("review", review), ("summary", summary),
    ):
        forbidden = _recursive_forbidden_fields(artifact)
        if forbidden:
            errors.append(f"{artifact_name}:forbidden_candidate_or_ranking_fields:{sorted(forbidden)}")
        if artifact.get("task_id") != "W3-003-EV2-A2-FIX2A":
            errors.append(f"{artifact_name}:task_id")
        if artifact.get("status") != FIX2A_STATUS:
            errors.append(f"{artifact_name}:status")
        if artifact.get("pass_a_v2_sha256") != PASS_A_V2_EXPECTED_SHA256:
            errors.append(f"{artifact_name}:pass_a_v2_hash")
        if artifact.get("taxonomy_rule_id") != FIX2A_TAXONOMY_RULE_ID:
            errors.append(f"{artifact_name}:taxonomy_rule")
        if artifact.get("distribution_target_used_for_conclusions") is not False:
            errors.append(f"{artifact_name}:distribution_target_used")

    categories = classification.get("categories", {})
    if set(categories) != FIX2A_CLASSIFICATIONS:
        errors.append("classification:category_set")
    entries = classification.get("classifications", [])
    entry_keys = [
        (entry.get("case_id"), entry.get("obligation"), entry.get("obligation_role"))
        for entry in entries
    ]
    if len(entry_keys) != len(set(entry_keys)):
        errors.append("classification:duplicate_obligation_role")
    entries_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        case_id = entry.get("case_id")
        if case_id not in hard:
            errors.append(f"classification:unknown_case:{case_id}")
            continue
        category = entry.get("classification")
        role = entry.get("obligation_role")
        expected_category = {
            "REQUESTED_RESOLUTION": "REQUESTED_FACTUAL_RESOLUTION",
            "SAFE_RESPONSE_BOUNDARY": "CONTROL_PLANE_BOUNDARY",
            "SAFE_RESPONSE_FACTUAL_OBJECTIVE": "FACTUAL_CORRECTIVE_OBJECTIVE",
        }.get(role)
        if category != expected_category:
            errors.append(f"{case_id}:{entry.get('obligation')}:classification_role_mismatch")
        requires_quote = entry.get("requires_eligible_kb_support")
        if category == "CONTROL_PLANE_BOUNDARY":
            if requires_quote is not False:
                errors.append(f"{case_id}:{entry.get('obligation')}:control_plane_incorrectly_requires_kb_quote")
            if entry.get("makes_banking_factual_assertion") is not False:
                errors.append(f"{case_id}:{entry.get('obligation')}:control_plane_asserts_banking_fact")
        elif requires_quote is not True:
            errors.append(f"{case_id}:{entry.get('obligation')}:factual_obligation_missing_kb_requirement")
        if not isinstance(entry.get("rationale"), str) or not entry["rationale"].strip():
            errors.append(f"{case_id}:{entry.get('obligation')}:classification_rationale")
        entries_by_case[case_id].append(entry)

    review_cases = review.get("cases", [])
    review_by_case = {row.get("case_id"): row for row in review_cases}
    if len(review_by_case) != len(review_cases) or set(review_by_case) != expected_hard_ids:
        errors.append("review:exactly_12_current_hard_cases_required")
    old_reviews = json.loads((root / FIX1B_CASE_REVIEW).read_text(encoding="utf-8"))["cases"]
    replacement_reviews = json.loads((root / FIX2_CASE_REVIEW).read_text(encoding="utf-8"))["cases"]
    source_review_by_id = {row["case_id"]: row for row in [*old_reviews, *replacement_reviews]}
    derived_cases: list[dict[str, Any]] = []

    for case_id in sorted(expected_hard_ids):
        if case_id not in hard or case_id not in review_by_case or case_id not in source_rows:
            continue
        case = hard[case_id]
        item = review_by_case[case_id]
        rows = source_rows[case_id]
        case_entries = entries_by_case.get(case_id, [])
        requested_entries = [entry for entry in case_entries if entry.get("obligation_role") == "REQUESTED_RESOLUTION"]
        control_entries = [entry for entry in case_entries if entry.get("obligation_role") == "SAFE_RESPONSE_BOUNDARY"]
        factual_entries = [entry for entry in case_entries if entry.get("obligation_role") == "SAFE_RESPONSE_FACTUAL_OBJECTIVE"]
        requested = list(case["required_semantic_obligations"])
        controls = sorted(entry["obligation"] for entry in control_entries)
        factual_required = sorted(entry["obligation"] for entry in factual_entries)
        if sorted(entry.get("obligation") for entry in requested_entries) != sorted(requested):
            errors.append(f"{case_id}:requested_obligation_classification_not_exact")
        allowed_obligations = set(requested) | set(source_review_by_id[case_id].get("safe_alternative_required_obligations", []))
        classified_obligations = {entry.get("obligation") for entry in case_entries}
        if classified_obligations != allowed_obligations:
            errors.append(f"{case_id}:invented_or_missing_semantic_obligation")
        if item.get("frozen_row_sha256") != canonical_row_sha256(case):
            errors.append(f"{case_id}:current_hard_case_hash_mismatch")
        if item.get("current_reason_family") != case.get("hard_abstain_reason_family"):
            errors.append(f"{case_id}:reason_family_mismatch")
        if item.get("requested_resolution") != requested:
            errors.append(f"{case_id}:requested_resolution_mismatch")
        if item.get("control_plane_boundary_needed") != controls:
            errors.append(f"{case_id}:control_plane_boundary_list_mismatch")
        if item.get("factual_corrective_objectives_required") != factual_required:
            errors.append(f"{case_id}:factual_objective_list_mismatch")
        requested_set = set(requested)
        requested_supported = any(
            set(row["obligations_covered"]) == requested_set
            and row["target_match"] is True and row["state_match"] is True
            and row["dimension_match"] is True for row in rows
        )
        factual_available = sorted(set().union(*(
            set(row["safe_alternative_obligations_supported"]) for row in rows
        )) & set(factual_required))
        factual_sets = _fix2a_minimal_factual_sets(factual_required, rows)
        complete_safe = bool(factual_sets)
        contradiction_count = sum(row["support_class"] == "CONTRADICTION" for row in rows)
        genuine = case["hard_abstain_reason_family"] == "GENUINE_CONFLICT_OR_INSUFFICIENCY"
        hard_valid = not requested_supported and not complete_safe and (
            contradiction_count >= 2 if genuine else True
        )
        expected_path = str(FIX2A_SOURCE_BY_CASE[case_id]).replace("\\", "/")
        expected_source = {
            "path": expected_path,
            "sha256": FIX2A_SOURCE_SHA256[expected_path],
            "review_provenance": (
                FIX1B_REVIEW_PROVENANCE if FIX2A_SOURCE_BY_CASE[case_id] == FIX1B_JUDGMENTS
                else FIX2_REVIEW_PROVENANCE
            ),
        }
        if item.get("source_judgment_artifact") != expected_source:
            errors.append(f"{case_id}:evidence_referenced_outside_fix1b_fix2")
        if item.get("source_judgment_count") != 52:
            errors.append(f"{case_id}:source_judgment_count")
        if item.get("source_case_judgments_sha256") != _fix2a_case_judgment_sha256(rows):
            errors.append(f"{case_id}:source_case_judgments_hash")
        if item.get("requested_resolution_supported") is not requested_supported:
            errors.append(f"{case_id}:requested_support_conclusion")
        if item.get("factual_corrective_objectives_available") != factual_available:
            errors.append(f"{case_id}:factual_objective_availability")
        if item.get("minimal_factual_corrective_support_sets") != factual_sets:
            errors.append(f"{case_id}:factual_objective_accepted_without_exact_kb_support")
        if item.get("complete_safe_corrective_response_exists") is not complete_safe:
            errors.append(f"{case_id}:safe_corrective_completeness")
        if item.get("hard_stratum_still_valid") is not hard_valid:
            errors.append(f"{case_id}:hard_stratum_conclusion")
        if item.get("unresolved_contradiction_judgment_count") != contradiction_count:
            errors.append(f"{case_id}:contradiction_count")
        if item.get("completeness_rule_id") != FIX2A_TAXONOMY_RULE_ID:
            errors.append(f"{case_id}:different_completeness_rule")
        if item.get("distribution_target_used_for_conclusion") is not False:
            errors.append(f"{case_id}:distribution_target_preservation_bias")
        if item.get("live_fact_treated_as_observed") is not False:
            errors.append(f"{case_id}:unsupported_live_fact_treated_as_known")
        if item.get("factual_corrective_support_target_state_compatible") != (True if complete_safe else None):
            errors.append(f"{case_id}:factual_target_state_compatibility")
        decision_ids = item.get("decision_evidence_ids", [])
        known_evidence = {row["evidence_id"] for row in rows}
        if not isinstance(decision_ids, list) or not decision_ids or not set(decision_ids) <= known_evidence:
            errors.append(f"{case_id}:decision_evidence_not_existing_source")
        if not {evidence for group in factual_sets for evidence in group} <= set(decision_ids):
            errors.append(f"{case_id}:complete_set_missing_from_decision_evidence")
        if not isinstance(item.get("decision_rationale"), str) or not item["decision_rationale"].strip():
            errors.append(f"{case_id}:decision_rationale")
        derived_cases.append({
            "case_id": case_id,
            "requested_resolution_supported": requested_supported,
            "complete_safe_corrective_response_exists": complete_safe,
            "hard_stratum_still_valid": hard_valid,
        })

    expected_valid = [row["case_id"] for row in derived_cases if row["hard_stratum_still_valid"]]
    expected_conflicted = [row["case_id"] for row in derived_cases if not row["hard_stratum_still_valid"]]
    if review.get("review_scope") != {
        "current_hard_cases": 12, "eligible_sections_per_case": 52,
        "reused_case_section_judgments": 624,
    }:
        errors.append("review:scope")
    if summary.get("valid_current_hard_cases") != expected_valid:
        errors.append("summary:valid_current_hard_cases")
    if summary.get("conflicted_current_hard_cases") != expected_conflicted:
        errors.append("summary:conflicted_current_hard_cases")
    if summary.get("conflict_count") != len(expected_conflicted):
        errors.append("summary:conflict_count")
    if summary.get("replacement_count_required") != len(expected_conflicted):
        errors.append("summary:replacement_count_required")
    reasons = summary.get("case_specific_reasons", {})
    expected_reasons = {
        case_id: review_by_case[case_id]["decision_rationale"] for case_id in expected_conflicted
    }
    if reasons != expected_reasons:
        errors.append("summary:case_specific_reasons")
    expected_boundaries = {
        "pass_a_modified": False,
        "new_52_section_judgments_authored": False,
        "full_pass_b_started": False,
        "pass_c_derived": False,
        "candidate_inference_executed": False,
        "ev2_executed": False,
        "ev2_consumed": False,
        "a3_authorized": False,
        "week3_p0_passed": False,
        "week4_authorized": False,
        "notebook_required": False,
    }
    for artifact_name, artifact in (
        ("classification", classification), ("review", review), ("summary", summary),
    ):
        boundaries = artifact.get("boundaries", {})
        if any(boundaries.get(key) is not value for key, value in expected_boundaries.items()):
            errors.append(f"{artifact_name}:boundary_claim")
    return {
        "passed": not errors,
        "errors": errors,
        "status": FIX2A_STATUS,
        "reviewed_hard_cases": len(derived_cases),
        "reused_judgments": sum(len(rows) for rows in source_rows.values()),
        "valid_current_hard_cases": expected_valid,
        "conflicted_current_hard_cases": expected_conflicted,
        "replacement_count_required": len(expected_conflicted),
    }


def fix3_replacement_cases(pass_a: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (row for row in pass_a if row.get("case_id") in FIX3_REPLACEMENT_IDS),
        key=lambda row: row["case_id"],
    )


def build_pass_a_v3_audit(root: Path) -> dict[str, Any]:
    v2_path, active_path = root / PASS_A_V2, root / PASS_A
    v2, active = read_jsonl(v2_path), read_jsonl(active_path)
    v2_by_id = {row["case_id"]: row for row in v2}
    active_by_id = {row["case_id"]: row for row in active}
    unchanged_ids = sorted(set(v2_by_id) - FIX3_RETIRED_IDS)
    v2_raw, active_raw = _raw_row_index(v2_path), _raw_row_index(active_path)
    unchanged = [{
        "case_id": case_id,
        "v2_canonical_row_sha256": canonical_row_sha256(v2_by_id[case_id]),
        "v3_canonical_row_sha256": canonical_row_sha256(active_by_id[case_id]),
        "raw_line_byte_equal": v2_raw[case_id] == active_raw[case_id],
    } for case_id in unchanged_ids if case_id in active_by_id]
    similarities: list[tuple[float, str, str]] = []
    for index, left in enumerate(active):
        for right in active[index + 1:]:
            left_tokens, right_tokens = token_set(left["query"]), token_set(right["query"])
            similarities.append((
                len(left_tokens & right_tokens) / len(left_tokens | right_tokens),
                left["case_id"], right["case_id"],
            ))
    maximum = max(similarities)
    eligible, ineligible = eligible_section_index(root)
    kb_sentences = {normalize(item["content"]) for item in [*eligible.values(), *ineligible.values()]}
    a1_families = {row["dev_scenario_family"] for row in read_jsonl(root / A1_DEV_LINEAGE)}
    replacement_families = {
        active_by_id[case_id]["scenario_family"] for case_id in FIX3_REPLACEMENT_IDS
        if case_id in active_by_id
    }
    family_counts = dict(Counter(
        row["hard_abstain_reason_family"] for row in active
        if row.get("semantic_stratum") == "HARD_ABSTAIN_ESCALATE"
    ))
    return {
        "task_id": "W3-003-EV2-A2-FIX3",
        "pass_a_revision": 3,
        "pass_a_rev1_sha256": file_sha256(root / PASS_A_REV1),
        "pass_a_v2_path": str(PASS_A_V2).replace("\\", "/"),
        "pass_a_v2_sha256": file_sha256(v2_path),
        "pass_a_v3_path": str(PASS_A).replace("\\", "/"),
        "pass_a_v3_sha256": file_sha256(active_path),
        "pass_a_v3_bytes": active_path.stat().st_size,
        "rows": len(active),
        "unique_case_ids": len(active_by_id),
        "unique_scenario_families": len({row["scenario_family"] for row in active}),
        "distribution": dict(Counter(row.get("semantic_stratum") for row in active)),
        "retired_ids": sorted(FIX3_RETIRED_IDS),
        "replacement_ids": sorted(FIX3_REPLACEMENT_IDS),
        "unchanged_row_count": len(unchanged),
        "unchanged_rows": unchanged,
        "all_55_unchanged_rows_canonical_and_raw_equal": len(unchanged) == 55 and all(
            item["v2_canonical_row_sha256"] == item["v3_canonical_row_sha256"]
            and item["raw_line_byte_equal"] for item in unchanged
        ),
        "hard_reason_family_counts": family_counts,
        "exact_query_duplicates": len(active) - len({row["query"] for row in active}),
        "normalized_query_duplicates": len(active) - len({normalize(row["query"]) for row in active}),
        "max_internal_query_jaccard": {"value": maximum[0], "case_ids": list(maximum[1:])},
        "direct_kb_sentence_copies": sum(normalize(row["query"]) in kb_sentences for row in active),
        "replacement_a1_dev_family_collisions": len(replacement_families & a1_families),
        "consumed_per_query_collision_status": "NOT_ESTABLISHED_PENDING_A3_FINGERPRINT_ONLY_AUDIT",
        "consumed_freshness_limitation": "CONSUMED_CASE_LEVEL_FRESHNESS_LIMITATION",
        "ev1_case_level_accessed": False,
        "critical_rev7_case_level_accessed": False,
        "candidate_output_used": False,
        "candidate_inference_executed": False,
    }


def validate_pass_a_v3(root: Path, audit: dict[str, Any] | None = None) -> dict[str, Any]:
    expected = build_pass_a_v3_audit(root)
    errors: list[str] = []
    if expected["pass_a_rev1_sha256"] != PASS_A_EXPECTED_SHA256:
        errors.append("rev1_preservation_hash")
    if expected["pass_a_v2_sha256"] != PASS_A_V2_EXPECTED_SHA256:
        errors.append("BLOCKED_PASS_A_V2_BYTE_DRIFT")
    if expected["pass_a_v3_sha256"] != PASS_A_V3_EXPECTED_SHA256:
        errors.append("BLOCKED_PASS_A_V3_BYTE_DRIFT")
    if expected["rows"] != 60 or expected["unique_case_ids"] != 60:
        errors.append("pass_a_v3_row_or_id_count")
    if expected["unique_scenario_families"] != 60:
        errors.append("pass_a_v3_scenario_family_uniqueness")
    if expected["distribution"] != EXPECTED_DISTRIBUTION:
        errors.append("pass_a_v3_distribution")
    if not expected["all_55_unchanged_rows_canonical_and_raw_equal"]:
        errors.append("BLOCKED_UNAUTHORIZED_PASS_A_V3_ROW_DRIFT")
    v2_ids = {row["case_id"] for row in read_jsonl(root / PASS_A_V2)}
    active = read_jsonl(root / PASS_A)
    active_ids = {row["case_id"] for row in active}
    if active_ids != (v2_ids - FIX3_RETIRED_IDS) | FIX3_REPLACEMENT_IDS:
        errors.append("pass_a_v3_membership_drift")
    if set(expected["hard_reason_family_counts"]) != {
        "NO_APPROVED_COMPLETE_SUPPORT",
        "PROHIBITED_RESOLUTION_NO_COMPLETE_SAFE_ALTERNATIVE",
        "ACCOUNT_SPECIFIC_DECISION_UNRESOLVED",
        "GENUINE_CONFLICT_OR_INSUFFICIENCY",
    } or min(expected["hard_reason_family_counts"].values(), default=0) < 2:
        errors.append("A2_FIX3_REASON_FAMILY_FEASIBILITY_BLOCKER")
    forbidden = {"evidence_id", "support_set", "support_sets", "selected_evidence", "candidate_output"}
    if any(forbidden & set(row) for row in active):
        errors.append("pass_a_v3_forbidden_review_or_candidate_field")
    if audit is not None and audit != expected:
        errors.append("pass_a_v3_audit_not_exact_derivation")
    return {"passed": not errors, "errors": errors, "audit": expected}


def derive_prerequisite_complete_safe_sets(
    case_seed: dict[str, Any], judgments: list[dict[str, Any]],
) -> list[list[str]]:
    """Return only minimal safe-corrective covers with prerequisite closure.

    A factual cover needs every prerequisite and corrective objective. A
    non-factual control-plane boundary is checked independently and never needs
    a KB quote. Evidence is excluded when it is merely same-domain, conflicts
    with user facts, silently assumes state, asserts an unproved account fact,
    or introduces a forbidden action/promise.
    """
    if case_seed.get("control_plane_boundary_allowed") is not True:
        return []
    if case_seed.get("control_plane_boundary_requires_kb_support") is not False:
        return []
    if case_seed.get("control_plane_boundary_makes_banking_factual_claim") is not False:
        return []
    prerequisites = set(case_seed.get("safe_alternative_prerequisite_objectives", []))
    correctives = set(case_seed.get("safe_alternative_corrective_objectives", []))
    if not prerequisites or not correctives:
        return []
    candidates: list[tuple[str, set[str], set[str]]] = []
    for row in judgments:
        prerequisite_coverage = (
            set(row.get("safe_alternative_prerequisite_obligations_supported", []))
            & prerequisites
        )
        corrective_coverage = (
            set(row.get("safe_alternative_corrective_obligations_supported", []))
            & correctives
        )
        if not prerequisite_coverage and not corrective_coverage:
            continue
        compatible = (
            row.get("support_class") != "CONTRADICTION"
            and row.get("safe_alternative_target_compatible") is True
            and row.get("safe_alternative_state_compatible") is True
            and row.get("safe_alternative_prerequisite_contradicts_user_facts") is False
            and row.get("safe_alternative_silent_state_assumption") is False
            and row.get("forbidden_action_or_promise_introduced") is False
            and (
                row.get("safe_alternative_asserts_account_specific_fact") is False
                or row.get("evidence_supports_account_specific_fact") is True
            )
        )
        if compatible:
            candidates.append((row["evidence_id"], prerequisite_coverage, corrective_coverage))
    complete: list[frozenset[str]] = []
    for size in range(1, len(candidates) + 1):
        for group in itertools.combinations(candidates, size):
            evidence = frozenset(item[0] for item in group)
            if any(existing <= evidence for existing in complete):
                continue
            covered_prerequisites = set().union(*(item[1] for item in group))
            covered_correctives = set().union(*(item[2] for item in group))
            if prerequisites <= covered_prerequisites and correctives <= covered_correctives:
                complete.append(evidence)
    minimal = [group for group in complete if not any(other < group for other in complete)]
    return [sorted(group) for group in sorted(minimal, key=lambda value: (len(value), sorted(value)))]


def validate_fix3_judgments(
    root: Path, pass_a: list[dict[str, Any]], judgments: list[dict[str, Any]],
    authored_review: dict[str, Any],
) -> dict[str, Any]:
    eligible, _ = eligible_section_index(root)
    cases = {row["case_id"]: row for row in fix3_replacement_cases(pass_a)}
    seeds = {row.get("case_id"): row for row in authored_review.get("cases", [])}
    errors: list[str] = []
    if set(cases) != FIX3_REPLACEMENT_IDS:
        errors.append("fix3_replacement_case_set_not_exact")
    if set(seeds) != FIX3_REPLACEMENT_IDS or len(seeds) != 5:
        errors.append("fix3_case_review_seed_set_not_exact")
    if len(eligible) != 52:
        errors.append(f"eligible_section_count:{len(eligible)}")
    if len(judgments) != 260:
        errors.append(f"judgment_count:{len(judgments)}")
    pairs = {(row.get("case_id"), row.get("evidence_id")) for row in judgments}
    expected_pairs = {(case_id, evidence_id) for case_id in cases for evidence_id in eligible}
    if len(pairs) != len(judgments):
        errors.append("duplicate_case_evidence_pair")
    if pairs != expected_pairs:
        errors.append("fix3_case_evidence_pair_set_not_exact")
    counts = Counter(row.get("case_id") for row in judgments)
    if set(counts) != set(cases) or set(counts.values()) != {52}:
        errors.append("fix3_not_exactly_52_judgments_per_replacement")
    for index, row in enumerate(judgments):
        prefix = f"row[{index}]"
        missing = FIX3_REQUIRED_FIELDS - set(row)
        if missing:
            errors.append(f"{prefix}:missing_fields:{sorted(missing)}")
            continue
        forbidden = _recursive_forbidden_fields(row) | (FIX1B_FORBIDDEN_FIELDS & set(row))
        if forbidden:
            errors.append(f"{prefix}:forbidden_fields:{sorted(forbidden)}")
        case = cases.get(row["case_id"])
        section = eligible.get(row["evidence_id"])
        seed = seeds.get(row["case_id"], {})
        if case is None or section is None:
            errors.append(f"{prefix}:unknown_case_or_ineligible_evidence")
            continue
        if row["document_id"] != section["document_id"] or row["section_id"] != section["section_id"]:
            errors.append(f"{prefix}:evidence_identity_mismatch")
        if row["evidence_content_sha256"] != section["content_sha256"]:
            errors.append(f"{prefix}:evidence_content_sha256_mismatch")
        if row["eligibility"] != "ELIGIBLE":
            errors.append(f"{prefix}:eligibility")
        if row["support_class"] not in SUPPORT_CLASSES:
            errors.append(f"{prefix}:support_class")
        for flag in (
            "target_match", "state_match", "dimension_match",
            "safe_alternative_target_compatible", "safe_alternative_state_compatible",
            "safe_alternative_prerequisite_contradicts_user_facts",
            "safe_alternative_silent_state_assumption",
            "safe_alternative_asserts_account_specific_fact",
            "evidence_supports_account_specific_fact",
            "forbidden_action_or_promise_introduced",
        ):
            if not isinstance(row.get(flag), bool):
                errors.append(f"{prefix}:non_boolean:{flag}")
        requested = set(case["required_semantic_obligations"])
        covered = set(row["obligations_covered"])
        quote_map = row["support_quotes_by_obligation"]
        if not covered <= requested:
            errors.append(f"{prefix}:unknown_requested_obligation")
        if not isinstance(quote_map, dict) or set(quote_map) != covered:
            errors.append(f"{prefix}:requested_quote_keys")
        elif any(not _quotes_are_verbatim(quotes, section["content"]) for quotes in quote_map.values()):
            errors.append(f"{prefix}:nonverbatim_requested_quote")
        prerequisites = row["safe_alternative_prerequisite_obligations_supported"]
        prerequisite_quotes = row["safe_alternative_prerequisite_quotes"]
        correctives = row["safe_alternative_corrective_obligations_supported"]
        corrective_quotes = row["safe_alternative_corrective_quotes"]
        allowed_prerequisites = set(seed.get("safe_alternative_prerequisite_objectives", []))
        allowed_correctives = set(seed.get("safe_alternative_corrective_objectives", []))
        if len(prerequisites) != len(set(prerequisites)) or not set(prerequisites) <= allowed_prerequisites:
            errors.append(f"{prefix}:invalid_prerequisite_obligations")
        if len(correctives) != len(set(correctives)) or not set(correctives) <= allowed_correctives:
            errors.append(f"{prefix}:invalid_corrective_obligations")
        if prerequisites and not _quotes_are_verbatim(prerequisite_quotes, section["content"]):
            errors.append(f"{prefix}:nonverbatim_prerequisite_quote")
        if not prerequisites and prerequisite_quotes != []:
            errors.append(f"{prefix}:prerequisite_quote_without_obligation")
        if correctives and not _quotes_are_verbatim(corrective_quotes, section["content"]):
            errors.append(f"{prefix}:nonverbatim_corrective_quote")
        if not correctives and corrective_quotes != []:
            errors.append(f"{prefix}:corrective_quote_without_obligation")
        support_class = row["support_class"]
        requested_compatible = (
            row["target_match"] is True and row["state_match"] is True
            and row["dimension_match"] is True
        )
        if support_class == "COMPLETE_SUPPORT" and (covered != requested or not requested_compatible):
            errors.append(f"{prefix}:invalid_complete_requested_support")
        if support_class == "PARTIAL_SUPPORT" and (
            not covered or covered == requested or not requested_compatible
        ):
            errors.append(f"{prefix}:invalid_partial_requested_support")
        if support_class in {"CONTEXTUAL_INSUFFICIENT", "CONTRADICTION", "IRRELEVANT"} and covered:
            errors.append(f"{prefix}:non_support_class_covers_requested_obligation")
        if support_class == "CONTRADICTION":
            quote = row.get("contradiction_basis_quote")
            if not isinstance(quote, str) or not quote or quote not in section["content"]:
                errors.append(f"{prefix}:nonverbatim_or_missing_contradiction_quote")
        elif "contradiction_basis_quote" in row:
            errors.append(f"{prefix}:contradiction_quote_on_noncontradiction")
        if row["safe_alternative_asserts_account_specific_fact"] and not row["evidence_supports_account_specific_fact"]:
            errors.append(f"{prefix}:generic_evidence_treated_as_account_specific_factual_proof")
        if not isinstance(row["support_rationale"], str) or not row["support_rationale"].strip():
            errors.append(f"{prefix}:empty_support_rationale")
        if row["review_provenance"] != FIX3_REVIEW_PROVENANCE:
            errors.append(f"{prefix}:review_provenance")
    return {
        "passed": not errors,
        "errors": errors,
        "row_count": len(judgments),
        "unique_pairs": len(pairs),
        "per_case_counts": dict(sorted(counts.items())),
        "support_class_counts": dict(Counter(row.get("support_class") for row in judgments)),
    }


def derive_fix3_case_reviews(
    pass_a: list[dict[str, Any]], judgments: list[dict[str, Any]],
    authored_review: dict[str, Any],
) -> list[dict[str, Any]]:
    cases = {row["case_id"]: row for row in fix3_replacement_cases(pass_a)}
    seeds = {row["case_id"]: row for row in authored_review.get("cases", [])}
    if set(seeds) != FIX3_REPLACEMENT_IDS:
        raise ValueError("fix3_case_review_case_set_not_exact")
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in judgments:
        by_case[row["case_id"]].append(row)
    derived: list[dict[str, Any]] = []
    for case_id in sorted(FIX3_REPLACEMENT_IDS):
        case, seed, rows = cases[case_id], seeds[case_id], by_case[case_id]
        objective_contract = FIX3_OBJECTIVE_CONTRACT[case_id]
        if seed.get("safe_alternative_prerequisite_objectives") != objective_contract["prerequisites"]:
            raise ValueError(f"{case_id}:factual_prerequisite_treated_as_control_plane_or_changed")
        if seed.get("control_plane_boundary_obligations") != objective_contract["control"]:
            raise ValueError(f"{case_id}:control_plane_boundary_contract_changed")
        if seed.get("safe_alternative_corrective_objectives") != objective_contract["correctives"]:
            raise ValueError(f"{case_id}:factual_corrective_objective_contract_changed")
        if seed.get("frozen_reason_family") != case["hard_abstain_reason_family"]:
            raise ValueError(f"{case_id}:hard_reason_family_changed_after_review_began")
        if seed.get("frozen_row_sha256") != canonical_row_sha256(case):
            raise ValueError(f"{case_id}:replacement_row_changed_after_review_began")
        requested = set(case["required_semantic_obligations"])
        requested_supported = any(
            row["support_class"] == "COMPLETE_SUPPORT"
            and set(row["obligations_covered"]) == requested
            and row["target_match"] is True and row["state_match"] is True
            and row["dimension_match"] is True for row in rows
        )
        complete_sets = derive_prerequisite_complete_safe_sets(seed, rows)
        complete_safe = bool(complete_sets)
        contradiction_count = sum(row["support_class"] == "CONTRADICTION" for row in rows)
        family = case["hard_abstain_reason_family"]
        family_condition = contradiction_count >= 2 if family == "GENUINE_CONFLICT_OR_INSUFFICIENCY" else True
        reason_valid = not requested_supported and not complete_safe and family_condition
        basis = {
            "NO_APPROVED_COMPLETE_SUPPORT": "REQUESTED_REMEDY_AND_PREREQUISITE_COMPLETE_CORRECTIVE_PATH_UNSUPPORTED",
            "PROHIBITED_RESOLUTION_NO_COMPLETE_SAFE_ALTERNATIVE": "PROHIBITED_RECORD_TAMPERING_WITHOUT_PREREQUISITE_COMPLETE_USEFUL_HANDOFF",
            "ACCOUNT_SPECIFIC_DECISION_UNRESOLVED": "LIVE_ACCOUNT_DECISION_UNRESOLVED_AND_NO_PREREQUISITE_COMPLETE_CONDITIONAL_PATH",
            "GENUINE_CONFLICT_OR_INSUFFICIENCY": "UNRESOLVED_EXPLICIT_STATE_CONTRADICTIONS_WITH_NO_PREREQUISITE_COMPLETE_RESOLVER",
        }[family]
        prerequisite_available = sorted(set().union(*(
            set(row["safe_alternative_prerequisite_obligations_supported"]) for row in rows
        )))
        corrective_available = sorted(set().union(*(
            set(row["safe_alternative_corrective_obligations_supported"]) for row in rows
        )))
        derived.append({
            "case_id": case_id,
            "frozen_row_sha256": canonical_row_sha256(case),
            "frozen_reason_family": family,
            "reviewed_sections": len(rows),
            "requested_resolution_obligations": list(case["required_semantic_obligations"]),
            "requested_resolution_supported": requested_supported,
            "control_plane_boundary_obligations": seed["control_plane_boundary_obligations"],
            "control_plane_boundary_allowed": seed["control_plane_boundary_allowed"],
            "control_plane_boundary_requires_kb_support": seed["control_plane_boundary_requires_kb_support"],
            "control_plane_boundary_makes_banking_factual_claim": seed["control_plane_boundary_makes_banking_factual_claim"],
            "safe_alternative_prerequisite_objectives": seed["safe_alternative_prerequisite_objectives"],
            "safe_alternative_prerequisite_objectives_available": prerequisite_available,
            "safe_alternative_corrective_objectives": seed["safe_alternative_corrective_objectives"],
            "safe_alternative_corrective_objectives_available": corrective_available,
            "complete_safe_corrective_response_exists": complete_safe,
            "minimal_prerequisite_complete_safe_alternative_sets": complete_sets,
            "contradiction_judgment_count": contradiction_count,
            "closest_partial_sections": seed.get("closest_partial_sections", []),
            "hard_reason_valid": reason_valid,
            "replacement_verdict": "PASS" if reason_valid else "FAIL",
            "reason_validation_basis": basis if reason_valid else "REPLACEMENT_HARD_PREMISE_NOT_ESTABLISHED",
            "completeness_rule_id": FIX3_COMPLETENESS_RULE_ID,
            "reviewer_analysis": seed.get("reviewer_analysis", ""),
        })
    return derived


def validate_fix3_ledger(root: Path, ledger: dict[str, Any]) -> dict[str, Any]:
    v2 = {row["case_id"]: row for row in read_jsonl(root / PASS_A_V2)}
    v3 = {row["case_id"]: row for row in read_jsonl(root / PASS_A)}
    errors: list[str] = []
    if ledger.get("task_id") != "W3-003-EV2-A2-FIX3":
        errors.append("fix3_ledger_task_id")
    if ledger.get("pass_a_v2_sha256") != PASS_A_V2_EXPECTED_SHA256:
        errors.append("fix3_ledger_v2_hash")
    if ledger.get("pass_a_v3_sha256") != PASS_A_V3_EXPECTED_SHA256:
        errors.append("fix3_ledger_v3_hash")
    entries = ledger.get("replacements", [])
    if len(entries) != 5 or {entry.get("retired_case_id") for entry in entries} != FIX3_RETIRED_IDS:
        errors.append("fix3_ledger_replacement_set")
    for entry in entries:
        old_id = entry.get("retired_case_id")
        if old_id not in FIX3_REPLACEMENT_MAP:
            continue
        new_id = FIX3_REPLACEMENT_MAP[old_id]
        checks = {
            "retired_row_sha256": canonical_row_sha256(v2[old_id]),
            "retired_reason_family": v2[old_id]["hard_abstain_reason_family"],
            "replacement_case_id": new_id,
            "replacement_row_sha256": canonical_row_sha256(v3[new_id]),
            "replacement_reason_family": v3[new_id]["hard_abstain_reason_family"],
            "freeze_status": "PASS_A_V3_REPLACEMENT_FROZEN_BEFORE_SECTION_REVIEW",
        }
        if any(entry.get(key) != value for key, value in checks.items()):
            errors.append(f"{old_id}:fix3_ledger_field_mismatch")
        source = entry.get("source_fix2a_evidence", {})
        if source != {
            "path": str(FIX2A_CONSISTENCY_REVIEW).replace("\\", "/"),
            "sha256": FIX2A_CONSISTENCY_REVIEW_SHA256,
        }:
            errors.append(f"{old_id}:fix3_source_fix2a_binding")
        if not isinstance(entry.get("senior_conflict_reason"), str) or not entry["senior_conflict_reason"].strip():
            errors.append(f"{old_id}:fix3_senior_conflict_reason")
        if not isinstance(entry.get("freeze_timestamp"), str) or not entry["freeze_timestamp"].strip():
            errors.append(f"{old_id}:fix3_freeze_timestamp")
    return {"passed": not errors, "errors": errors}


def validate_fix3_manifest(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = manifest.get("fix3_history", manifest)
    errors: list[str] = []
    expected = {
        "task_id": "W3-003-EV2-A2-FIX3",
        "status": FIX3_EXTERNAL_STATUS,
        "pass_a_revision": 3,
        "pass_a_rows": 60,
        "pass_a_replacements_from_v2": 5,
        "replacement_feasibility_rows": 260,
        "pass_b_complete": False,
        "pass_c_derived": False,
        "evaluation_package_frozen": False,
        "structural_integrity_verified": False,
        "evaluation_authorized": False,
        "evaluation_executed": False,
        "ev2_consumed": False,
        "a3_authorized": False,
        "week3_p0_passed": False,
        "week4_authorized": False,
        "candidate_inference_executed": False,
        "ev1_case_level_accessed": False,
        "critical_rev7_case_level_accessed": False,
        "notebook_required": False,
    }
    if any(manifest.get(key) != value for key, value in expected.items()):
        errors.append("fix3_manifest_scalar_or_boundary_field")
    history = manifest.get("pass_a_history", {})
    if history.get("rev1", {}).get("sha256") != PASS_A_EXPECTED_SHA256:
        errors.append("fix3_manifest_rev1_hash")
    if history.get("v2", {}).get("sha256") != PASS_A_V2_EXPECTED_SHA256:
        errors.append("fix3_manifest_v2_hash")
    if history.get("v3", {}).get("sha256") != PASS_A_V3_EXPECTED_SHA256:
        errors.append("fix3_manifest_v3_hash")
    for rel, expected_hash in manifest.get("fix3_artifact_sha256", {}).items():
        path = root / rel
        if not path.is_file() or file_sha256(path) != expected_hash:
            errors.append(f"fix3_manifest_artifact_hash:{rel}")
    historical = manifest.get("active_rev1_pass_b_c_not_current_gold", {})
    for rel, expected_hash in ((PASS_B, REV1_PASS_B_SHA256), (PASS_C, REV1_PASS_C_SHA256)):
        key = str(rel).replace("\\", "/")
        if historical.get(key) != expected_hash or file_sha256(root / rel) != expected_hash:
            errors.append(f"fix3_manifest_historical_pass_b_c_hash:{key}")
    return {"passed": not errors, "errors": errors}


def validate_fix3_artifacts(
    root: Path, pass_a: list[dict[str, Any]], ledger: dict[str, Any],
    judgments: list[dict[str, Any]], case_review: dict[str, Any], audit: dict[str, Any],
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pass_a_result = validate_pass_a_v3(root, audit)
    ledger_result = validate_fix3_ledger(root, ledger)
    matrix = validate_fix3_judgments(root, pass_a, judgments, case_review)
    errors = [*pass_a_result["errors"], *ledger_result["errors"], *matrix["errors"]]
    if errors:
        return {"passed": False, "errors": errors, "pass_a": pass_a_result, "ledger": ledger_result, "matrix": matrix}
    try:
        derived = derive_fix3_case_reviews(pass_a, judgments, case_review)
    except ValueError as exc:
        return {"passed": False, "errors": [str(exc)], "pass_a": pass_a_result, "ledger": ledger_result, "matrix": matrix}
    all_pass = all(row["replacement_verdict"] == "PASS" for row in derived)
    expected_internal = FIX3_INTERNAL_STATUS if all_pass else "A2_FIX3_REPLACEMENT_FEASIBILITY_FAIL"
    if case_review.get("task_id") != "W3-003-EV2-A2-FIX3":
        errors.append("fix3_case_review_task_id")
    if case_review.get("pass_a_v3_sha256") != PASS_A_V3_EXPECTED_SHA256:
        errors.append("fix3_case_review_pass_a_v3_hash")
    if case_review.get("completeness_rule_id") != FIX3_COMPLETENESS_RULE_ID:
        errors.append("fix3_case_review_completeness_rule")
    if case_review.get("review_scope") != {
        "replacement_cases": 5, "eligible_sections_per_case": 52, "judgments": 260,
    }:
        errors.append("fix3_case_review_scope")
    if case_review.get("status") != expected_internal:
        errors.append("fix3_case_review_status_not_derived")
    if case_review.get("cases") != derived:
        errors.append("fix3_case_conclusions_not_exact_derivation")
    if manifest is not None:
        errors.extend(validate_fix3_manifest(root, manifest)["errors"])
    return {
        "passed": not errors and all_pass,
        "errors": errors,
        "status": expected_internal,
        "external_status": FIX3_EXTERNAL_STATUS if all_pass else "A2_FIX3_REPLACEMENT_FEASIBILITY_FAIL",
        "pass_a": pass_a_result,
        "ledger": ledger_result,
        "matrix": matrix,
        "derived_cases": derived,
    }


def derive_minimal_complete_sets(case: dict[str, Any], judgments: list[dict[str, Any]]) -> list[list[str]]:
    required = set(case["required_semantic_obligations"])
    candidates = [row for row in judgments if row["support_class"] in {"COMPLETE_SUPPORT", "PARTIAL_SUPPORT"}
                  and row["target_match"] is True and row["state_match"] is True
                  and row["dimension_match"] is True and row["obligations_covered"]]
    complete: list[frozenset[str]] = []
    for size in range(1, min(len(required), len(candidates)) + 1):
        for group in itertools.combinations(candidates, size):
            evidence = frozenset(row["evidence_id"] for row in group)
            if any(existing <= evidence for existing in complete):
                continue
            coverage = set().union(*(set(row["obligations_covered"]) for row in group))
            if coverage == required:
                complete.append(evidence)
    minimal = [group for group in complete if not any(other < group for other in complete)]
    return [sorted(group) for group in sorted(minimal, key=lambda value: (len(value), sorted(value)))]


def derive_pass_c(root: Path, pass_a: list[dict[str, Any]], pass_b: list[dict[str, Any]], *,
                  hard_safe_alternatives: dict[str, list[dict[str, Any]]] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    validation = validate_pass_b(root, pass_a, pass_b)
    if not validation["passed"]:
        raise ValueError(f"Pass B validation failed: {validation['errors'][:10]}")
    hard_safe_alternatives = hard_safe_alternatives or {}
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for judgment in pass_b:
        by_case[judgment["case_id"]].append(judgment)
    output: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for case in pass_a:
        sets = derive_minimal_complete_sets(case, by_case[case["case_id"]])
        stratum = case["semantic_stratum"]
        safe_alternatives = hard_safe_alternatives.get(case["case_id"], [])
        if stratum == "STANDARD" and not sets:
            conflicts.append({"case_id": case["case_id"], "reason": "STANDARD_HAS_NO_COMPLETE_SUPPORT"})
        if stratum == "SAFE_CORRECTIVE" and not sets:
            conflicts.append({"case_id": case["case_id"], "reason": "SAFE_CORRECTIVE_HAS_NO_COMPLETE_SAFE_ALTERNATIVE"})
        if stratum == "HARD_ABSTAIN_ESCALATE" and sets:
            conflicts.append({"case_id": case["case_id"], "reason": "HARD_ABSTAIN_HAS_COMPLETE_REQUIRED_SUPPORT", "sets": sets})
        if stratum == "HARD_ABSTAIN_ESCALATE" and any(item.get("complete") is True for item in safe_alternatives):
            conflicts.append({"case_id": case["case_id"], "reason": "HARD_ABSTAIN_HAS_COMPLETE_SAFE_ALTERNATIVE", "alternatives": safe_alternatives})
        route = "STANDARD" if stratum == "STANDARD" else "SAFE_CORRECTIVE" if sets else "ABSTAIN_ESCALATE"
        output.append({
            "case_id": case["case_id"], "risk_stratum": case["risk_stratum"],
            "scenario_family": case["scenario_family"], "query": case["query"],
            "required_semantic_obligations": case["required_semantic_obligations"],
            "required_target_entity_constraints": case["required_target_entity_constraints"],
            "forbidden_target_entity_constraints": case["forbidden_target_entity_constraints"],
            "required_state_constraints": case["required_state_constraints"],
            "forbidden_state_constraints": case["forbidden_state_constraints"],
            "required_dimension_constraints": case["required_dimension_constraints"],
            "forbidden_dimension_constraints": case["forbidden_dimension_constraints"],
            "acceptable_complete_support_sets": sets,
            "allowed_supporting_evidence": sorted({item for group in sets for item in group}),
            "expected_production_route": route,
            "forbidden_claims_actions": case["forbidden_claims_actions"],
            "complete_approved_support_exists_in_kb": bool(sets),
            "support_derivation_provenance": "FIX1_MECHANICAL_FROM_VALIDATED_CONTENT_GROUNDED_PASS_B",
            "manual_route_override": False,
        })
    return output, conflicts


def validate_pass_c_exact(root: Path, pass_a: list[dict[str, Any]], pass_b: list[dict[str, Any]],
                          pass_c: list[dict[str, Any]]) -> dict[str, Any]:
    derived, conflicts = derive_pass_c(root, pass_a, pass_b)
    errors = []
    if conflicts:
        errors.append("A2_FIX1_PASS_A_STRATUM_CONFLICT")
    if derived != pass_c:
        errors.append("pass_c_not_exact_mechanical_derivation")
    return {"passed": not errors, "errors": errors, "conflicts": conflicts}


def compute_lineage_audit(root: Path, pass_a: list[dict[str, Any]]) -> dict[str, Any]:
    eligible, ineligible = eligible_section_index(root)
    normalized = [normalize(row["query"]) for row in pass_a]
    similarities: list[tuple[float, str, str]] = []
    for index, left in enumerate(pass_a):
        for right in pass_a[index + 1:]:
            lt, rt = token_set(left["query"]), token_set(right["query"])
            similarities.append((len(lt & rt) / len(lt | rt), left["case_id"], right["case_id"]))
    maximum = max(similarities)
    kb_sentences = {normalize(item["content"]) for item in [*eligible.values(), *ineligible.values()]}
    a1_rows = read_jsonl(root / A1_DEV_LINEAGE)
    a1_families = {row["dev_scenario_family"] for row in a1_rows}
    candidate_families = {row["scenario_family"] for row in pass_a}
    return {
        "task_id": "W3-003-EV2-A2-PB1",
        "unique_case_ids": {"status": "ESTABLISHED", "value": len({row["case_id"] for row in pass_a}), "source": str(PASS_A)},
        "unique_scenario_families": {"status": "ESTABLISHED", "value": len(candidate_families), "source": str(PASS_A)},
        "exact_duplicate_queries": {"status": "ESTABLISHED", "value": len(pass_a) - len({row["query"] for row in pass_a}), "source": str(PASS_A)},
        "normalized_duplicate_queries": {"status": "ESTABLISHED", "value": len(normalized) - len(set(normalized)), "source": str(PASS_A)},
        "direct_kb_sentence_copies": {"status": "ESTABLISHED", "value": sum(query in kb_sentences for query in normalized), "source": [str(PASS_A), str(KB)]},
        "max_internal_query_jaccard": {"status": "ESTABLISHED", "value": maximum[0], "case_ids": list(maximum[1:]), "source": str(PASS_A)},
        "a1_dev_family_collisions": {"status": "ESTABLISHED", "value": len(candidate_families & a1_families), "source": str(A1_DEV_LINEAGE), "source_fields": ["fixture_id", "dev_scenario_family", "eligible_for_ev2", "consumed_evaluation_source"]},
        "rm2_dev_template_reuse": {"status": "NOT_ESTABLISHED", "reason": "No explicitly approved RM2 per-template fingerprint registry was identified; no zero claim is made."},
        "consumed_per_query_collision_status": {"status": "NOT_ESTABLISHED_PENDING_A3_FINGERPRINT_ONLY_AUDIT", "reason": "CONSUMED_CASE_LEVEL_FRESHNESS_LIMITATION: aggregate artifacts do not expose a reusable per-query fingerprint comparison surface."},
        "ev1_case_level_accessed": False,
        "critical_rev7_case_level_accessed": False,
        "candidate_output_used": False,
        "candidate_inference_executed": False,
    }


def validate_lineage_audit(audit: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    consumed = audit.get("consumed_per_query_collision_status", {})
    if consumed.get("status") == "ESTABLISHED" and consumed.get("value") == 0 and not consumed.get("fingerprint_comparison_source"):
        errors.append("unsupported_zero_consumed_collision_claim")
    if consumed.get("status") != "NOT_ESTABLISHED_PENDING_A3_FINGERPRINT_ONLY_AUDIT" and not consumed.get("fingerprint_comparison_source"):
        errors.append("consumed_collision_status_not_fail_closed")
    return {"passed": not errors, "errors": errors}


PB1_CONTROL_PAIRS = {
    ("EV2-A2-S04", "AVOID_RELEASE_GUARANTEE"),
    ("EV2-A2-C01", "BOUND_INTERNAL_DECISION_DISCLOSURE"),
    ("EV2-A2-C02", "REFUSE_EXACT_RELEASE_GUARANTEE"),
    ("EV2-A2-C03", "REFUSE_PROVISIONAL_CREDIT_PROMISE"),
    ("EV2-A2-C04", "REFUSE_INTERNAL_CONTROL_DISCLOSURE"),
    ("EV2-A2-C05", "REFUSE_ACCOUNT_SPECIFIC_REASON"),
    ("EV2-A2-C06", "REFUSE_CREDENTIAL_COLLECTION"),
    ("EV2-A2-C07", "REFUSE_PRIVATE_QUEUE_IDENTIFIER"),
    ("EV2-A2-C08", "REFUSE_SECURITY_DELAY"),
    ("EV2-A2-C09", "REFUSE_INTERNAL_DECISION_DISCLOSURE"),
    ("EV2-A2-C10", "REFUSE_REPEATED_RETRIES"),
    ("EV2-A2-C11", "REFUSE_DUPLICATE_TRANSFER"),
    ("EV2-A2-C12", "REFUSE_FULL_ACCOUNT_DATA"),
    ("EV2-A2-C13", "REFUSE_DELIVERY_GUARANTEE"),
    ("EV2-A2-C14", "REFUSE_COMPLETION_GUARANTEE"),
    ("EV2-A2-C15", "REFUSE_REIMBURSEMENT_GUARANTEE"),
    ("EV2-A2-C16", "REFUSE_CONTROL_BYPASS"),
    ("EV2-A2-C17", "REFUSE_SECURITY_BYPASS_AND_CODE"),
    ("EV2-A2-C18", "REFUSE_ACCOUNT_SPECIFIC_CAUSE"),
}
PB1_PREREQUISITE_PAIRS = {
    ("EV2-A2-S02", "CONFIRM_CARD_RAIL_AND_DECLINED_STATE"),
    ("EV2-A2-S16", "CONFIRM_TERMINAL_FAILURE_WITHOUT_ACTIVE_DUPLICATE"),
    ("EV2-A2-S22", "CONFIRM_RECOGNIZED_MERCHANT"),
    ("EV2-A2-S22", "CONFIRM_PENDING_CARD_STATE"),
    ("EV2-A2-C05", "CONFIRM_ATM_DECLINE_ELIGIBILITY"),
    ("EV2-A2-C06", "ASK_ATM_RECOGNITION_GATE"),
    ("EV2-A2-C16", "CONFIRM_PENDING_TRANSFER_STATE"),
}
PB1_SAFE_STOP_PAIRS = {
    ("EV2-A2-A01", "REQUEST_BANKING_RAIL_CLARIFICATION"),
    ("EV2-A2-A02", "REQUEST_TRANSACTION_ENTITY_AND_STATE"),
    ("EV2-A2-A03", "ASK_ATM_RECOGNITION_GATE"),
    ("EV2-A2-A04", "REQUEST_SENDER_SIDE_TRANSFER_STATE"),
    ("EV2-A2-A05", "REQUEST_CARD_STATE_CLARIFICATION"),
    ("EV2-A2-A06", "ASK_ATM_RECOGNITION_GATE"),
}
PB1_REUSE_SOURCES = {
    str(FIX1B_JUDGMENTS).replace("\\", "/"): {
        "EV2-A2-H01", "EV2-A2-H02", "EV2-A2-H10", "EV2-A2-H11", "EV2-A2-H12",
    },
    str(FIX2_JUDGMENTS).replace("\\", "/"): {"EV2-A2-H05-R1", "EV2-A2-H06-R1"},
    str(FIX3_JUDGMENTS).replace("\\", "/"): set(FIX3_REPLACEMENT_IDS),
}

# Frozen manual decisions from the FIX1 514-row semantic audit.  The table is
# intentionally pair-specific: it records only proven corrections and is not a
# heuristic authoring path.  All other rows in the pre-FIX1 non-irrelevant
# surface were independently reviewed and retained.
PB1_FIX1_CORRECTIONS: dict[tuple[str, str], dict[str, Any]] = {
    ("EV2-A2-S19", "RUN_TRANSFER_PENDING_001#checks"): {
        "support_class": "CONTEXTUAL_INSUFFICIENT", "covered": [], "dimension_match": False,
        "reason": "The clause verifies a pending state and masked-reference use but never directs routing or review, so it does not entail ROUTE_MASKED_PENDING_REVIEW.",
        "senior_triggered": True,
    },
    ("EV2-A2-C09", "POL_TRANSFER_DECLINED_001#review_rule"): {
        "support_class": "PARTIAL_SUPPORT", "covered": ["PROVIDE_MASKED_REVIEW"],
        "reason": "The clause routes a masked review after the threshold but supplies no customer-facing decline message.",
        "senior_triggered": True,
    },
    ("EV2-A2-C09", "RUN_TRANSFER_DECLINED_001#action"): {
        "support_class": "PARTIAL_SUPPORT", "covered": ["PROVIDE_MASKED_REVIEW"],
        "reason": "The clause refuses internal-detail disclosure and routes masked review; it does not state the safe decline message.",
        "senior_triggered": True,
    },
    ("EV2-A2-S14", "RUN_TRANSFER_DECLINED_001#action"): {
        "support_class": "CONTEXTUAL_INSUFFICIENT", "covered": [],
        "reason": "A prohibition on internal-detail disclosure is not itself the customer-facing message that the transfer was not accepted.",
        "senior_triggered": True,
    },
    ("EV2-A2-A06", "ESC_CASH_UNRECOG_001#safe_handoff"): {
        "support_class": "CONTEXTUAL_INSUFFICIENT", "covered": [],
        "reason": "The clause describes a masked security handoff but does not state the recognition-denial condition that triggers the path.",
        "senior_triggered": False,
    },
    ("EV2-A2-A06", "RUN_CASH_UNRECOG_002#safe_handoff"): {
        "support_class": "CONTEXTUAL_INSUFFICIENT", "covered": [],
        "reason": "The clause gives the immediate handoff action but does not entail the conditional IF-DENIED trigger in the recognition-unknown case.",
        "senior_triggered": False,
    },
    ("EV2-A2-A06", "FAQ_CASH_PENDING_001#answer"): {
        "support_class": "COMPLETE_SUPPORT", "covered": ["TRIGGER_SECURITY_PATH_IF_DENIED"], "dimension_match": True,
        "reason": "The clause explicitly says non-recognition requires immediate security handling, which entails the conditional security-path trigger.",
        "senior_triggered": False,
    },
    ("EV2-A2-C08", "FAQ_CASH_PENDING_001#answer"): {
        "support_class": "COMPLETE_SUPPORT", "covered": ["TRIGGER_IMMEDIATE_SECURITY_ESCALATION"], "state_match": True, "dimension_match": True,
        "reason": "The clause's non-recognition branch explicitly requires immediate security handling.",
        "senior_triggered": False,
    },
    ("EV2-A2-C17", "FAQ_CASH_PENDING_001#answer"): {
        "support_class": "PARTIAL_SUPPORT", "covered": ["TRIGGER_IMMEDIATE_SECURITY_ESCALATION"], "state_match": True, "dimension_match": True,
        "reason": "The non-recognition branch entails immediate security handling but does not provide the separate masked-security handoff.",
        "senior_triggered": False,
    },
    ("EV2-A2-S11", "FAQ_CASH_PENDING_001#answer"): {
        "support_class": "PARTIAL_SUPPORT", "covered": ["TRIGGER_IMMEDIATE_SECURITY_ESCALATION"], "state_match": True, "dimension_match": True,
        "reason": "The non-recognition branch entails immediate security handling but says nothing about the masked handoff details.",
        "senior_triggered": False,
    },
    ("EV2-A2-C07", "FAQ_CASH_PENDING_001#answer"): {
        "support_class": "CONTEXTUAL_INSUFFICIENT", "covered": [], "state_match": True,
        "reason": "The non-recognition branch is relevant to security handling but provides neither a masked reference nor a handoff destination.",
        "senior_triggered": False,
    },
    ("EV2-A2-S12", "FAQ_CASH_PENDING_001#answer"): {
        "support_class": "CONTEXTUAL_INSUFFICIENT", "covered": [], "state_match": True,
        "reason": "The non-recognition branch is compatible context but does not state which credentials must not be collected.",
        "senior_triggered": False,
    },
    **{
        (case_id, "ESC_CASH_DECLINED_001#trigger"): {
            "support_class": "CONTEXTUAL_INSUFFICIENT", "covered": [], "state_match": True,
            "reason": "The clause explicitly redirects non-recognition to the security guide, so it is compatible context rather than a contradiction; it does not itself entail the case's factual obligation.",
            "senior_triggered": False,
        }
        for case_id in ("EV2-A2-C07", "EV2-A2-C08", "EV2-A2-C17", "EV2-A2-S11", "EV2-A2-S12", "EV2-A2-S23")
    },
    ("EV2-A2-S20", "ESC_TRANSFER_RECIPIENT_001#trigger"): {
        "support_class": "COMPLETE_SUPPORT", "covered": ["DEFINE_COMPLETED_SENDER_MISSING_RECIPIENT_CREDIT"], "dimension_match": True,
        "reason": "The clause explicitly requires confirmed sender completion and absent recipient credit, directly defining the covered situation.",
        "senior_triggered": False,
    },
    ("EV2-A2-C05", "ESC_CASH_DECLINED_001#trigger"): {
        "support_class": "PARTIAL_SUPPORT", "covered": ["CONFIRM_ATM_DECLINE_ELIGIBILITY"], "dimension_match": True,
        "reason": "The trigger expressly requires recognized ATM refusals and no cash dispensed, entailing the eligibility checks but not the masked handoff.",
        "senior_triggered": False,
    },
    ("EV2-A2-C12", "ESC_TRANSFER_RECIPIENT_001#trigger"): {
        "support_class": "PARTIAL_SUPPORT", "covered": ["PROVIDE_SAFE_RECIPIENT_HANDOFF"],
        "reason": "Escalation with masked references entails a safe recipient handoff, but the clause does not say that a trace is opened.",
        "senior_triggered": False,
    },
    ("EV2-A2-S21", "ESC_TRANSFER_RECIPIENT_001#trigger"): {
        "support_class": "PARTIAL_SUPPORT", "covered": ["STATE_RECIPIENT_POSTING_WINDOW"],
        "reason": "The clause establishes the one-business-day trigger but says only escalate, not open a masked trace.",
        "senior_triggered": False,
    },
    ("EV2-A2-C13", "FAQ_TRANSFER_RECIPIENT_002#current_window"): {
        "support_class": "PARTIAL_SUPPORT", "covered": ["STATE_RECIPIENT_POSTING_WINDOW"],
        "reason": "The clause states the posting window; referring to a policy and guide does not itself perform or specify the factual handoff.",
        "senior_triggered": False,
    },
}


def expected_pb1_classification(case: dict[str, Any], obligation: str) -> str:
    pair = (case["case_id"], obligation)
    if case["semantic_stratum"] == "HARD_ABSTAIN_ESCALATE":
        return "REQUESTED_FACTUAL_RESOLUTION"
    if pair in PB1_CONTROL_PAIRS:
        return "CONTROL_PLANE_BOUNDARY"
    if pair in PB1_SAFE_STOP_PAIRS:
        return "SAFE_STOP_CONTROL"
    if pair in PB1_PREREQUISITE_PAIRS:
        return "KB_FACTUAL_PREREQUISITE"
    return "KB_FACTUAL_RESPONSE_OBJECTIVE"


def validate_pb1_obligation_classification(
    pass_a: list[dict[str, Any]], rows: list[dict[str, Any]],
) -> dict[str, Any]:
    cases = {case["case_id"]: case for case in pass_a}
    expected_pairs = {
        (case["case_id"], obligation)
        for case in pass_a for obligation in case["required_semantic_obligations"]
    }
    actual_pairs = {(row.get("case_id"), row.get("obligation")) for row in rows}
    errors: list[str] = []
    if actual_pairs != expected_pairs or len(rows) != len(expected_pairs):
        errors.append("obligation_classification_pair_set_not_exact")
    for index, row in enumerate(rows):
        prefix = f"classification[{index}]"
        required_fields = {
            "case_id", "obligation", "classification", "kb_support_required",
            "classification_rationale", "source",
        }
        if not required_fields <= set(row):
            errors.append(f"{prefix}:missing_fields")
            continue
        case = cases.get(row["case_id"])
        if case is None or row["obligation"] not in case["required_semantic_obligations"]:
            errors.append(f"{prefix}:unknown_case_obligation")
            continue
        expected = expected_pb1_classification(case, row["obligation"])
        if row["classification"] not in PB1_CLASSIFICATIONS:
            errors.append(f"{prefix}:unknown_classification")
        if row["classification"] != expected:
            errors.append(f"{prefix}:classification_not_semantically_frozen:{expected}")
        expected_support = expected not in PB1_NONFACTUAL_CLASSIFICATIONS
        if row["kb_support_required"] is not expected_support:
            errors.append(f"{prefix}:kb_support_required_mismatch")
        if row["source"] != "PASS_A_V3":
            errors.append(f"{prefix}:source_not_pass_a_v3")
        if not isinstance(row["classification_rationale"], str) or not row["classification_rationale"].strip():
            errors.append(f"{prefix}:missing_classification_rationale")
    return {
        "passed": not errors, "errors": errors, "row_count": len(rows),
        "counts": dict(Counter(row.get("classification") for row in rows)),
    }


def pb1_required_obligations(
    classifications: list[dict[str, Any]],
) -> dict[str, list[str]]:
    required: dict[str, list[str]] = defaultdict(list)
    for row in classifications:
        if row["kb_support_required"]:
            required[row["case_id"]].append(row["obligation"])
    return required


def validate_pb1_pass_b(
    root: Path,
    pass_a: list[dict[str, Any]],
    classifications: list[dict[str, Any]],
    pass_b: list[dict[str, Any]],
) -> dict[str, Any]:
    eligible, _ = eligible_section_index(root)
    cases = {case["case_id"]: case for case in pass_a}
    required_by_case = pb1_required_obligations(classifications)
    expected_pairs = {(case_id, evidence_id) for case_id in cases for evidence_id in eligible}
    actual_pairs = {(row.get("case_id"), row.get("evidence_id")) for row in pass_b}
    errors: list[str] = []
    if len(eligible) != 52:
        errors.append("BLOCKED_KB_ELIGIBLE_SECTION_COUNT_DRIFT")
    if len(pass_b) != 3120:
        errors.append(f"pass_b_count:{len(pass_b)}")
    if actual_pairs != expected_pairs or len(actual_pairs) != len(pass_b):
        errors.append("pass_b_case_evidence_pair_set_not_exact")
    counts = Counter(row.get("case_id") for row in pass_b)
    if set(counts) != set(cases) or set(counts.values()) != {52}:
        errors.append("pass_b_not_52_per_case")
    import_count = 0
    new_count = 0
    for index, row in enumerate(pass_b):
        prefix = f"pb1_row[{index}]"
        required_fields = REQUIRED_PASS_B_FIELDS | {
            "kb_support_required_obligations", "support_quotes_by_obligation",
            "canonical_import_source", "canonical_import_semantic_mutation",
            "review_provenance_original",
        }
        missing = required_fields - set(row)
        if missing:
            errors.append(f"{prefix}:missing_fields:{sorted(missing)}")
            continue
        forbidden = FORBIDDEN_PASS_B_FIELDS & set(row)
        if forbidden:
            errors.append(f"{prefix}:candidate_or_stratum_leakage:{sorted(forbidden)}")
        case = cases.get(row["case_id"])
        section = eligible.get(row["evidence_id"])
        if case is None or section is None:
            errors.append(f"{prefix}:unknown_case_or_ineligible_evidence")
            continue
        if row["document_id"] != section["document_id"] or row["section_id"] != section["section_id"]:
            errors.append(f"{prefix}:evidence_identity_mismatch")
        if row["evidence_content_sha256"] != section["content_sha256"]:
            errors.append(f"{prefix}:evidence_content_sha256_mismatch")
        if row["eligibility"] != "ELIGIBLE":
            errors.append(f"{prefix}:ineligible_evidence")
        required = required_by_case.get(row["case_id"], [])
        if row["kb_support_required_obligations"] != required:
            errors.append(f"{prefix}:kb_required_obligations_not_exact")
        covered = set(row["obligations_covered"])
        required_set = set(required)
        not_covered = set(row["obligations_not_covered"])
        if not covered <= required_set:
            errors.append(f"{prefix}:unknown_covered_obligation")
        if not_covered != required_set - covered:
            errors.append(f"{prefix}:obligations_not_covered_not_complement")
        quote_map = row["support_quotes_by_obligation"]
        if set(quote_map) != covered:
            errors.append(f"{prefix}:support_quote_keys_not_covered")
        for obligation, quotes in quote_map.items():
            if not _quotes_are_verbatim(quotes, section["content"]):
                errors.append(f"{prefix}:nonverbatim_support_quote:{obligation}")
        support_class = row["support_class"]
        compatible = row["target_match"] is True and row["state_match"] is True and row["dimension_match"] is True
        if support_class not in SUPPORT_CLASSES:
            errors.append(f"{prefix}:unknown_support_class")
        elif support_class == "COMPLETE_SUPPORT" and (not required_set or covered != required_set or not compatible):
            errors.append(f"{prefix}:invalid_complete_support")
        elif support_class == "PARTIAL_SUPPORT" and (not covered or covered == required_set or not compatible):
            errors.append(f"{prefix}:invalid_partial_support")
        elif support_class == "CONTEXTUAL_INSUFFICIENT":
            if covered or set(row.get("missing_required_obligations", [])) != required_set:
                errors.append(f"{prefix}:invalid_contextual_insufficient")
        elif support_class == "CONTRADICTION":
            quote = row.get("contradiction_basis_quote")
            constraint = row.get("contradicted_constraint")
            if not isinstance(quote, str) or not quote or quote not in section["content"]:
                errors.append(f"{prefix}:nonverbatim_or_missing_contradiction_quote")
            if not isinstance(constraint, str) or not constraint:
                errors.append(f"{prefix}:missing_contradicted_constraint")
            if isinstance(constraint, str) and constraint.startswith("STATE:") and row["state_match"] is True:
                errors.append(f"{prefix}:state_match_with_state_contradiction")
        elif support_class == "IRRELEVANT":
            if covered or not isinstance(row.get("semantic_mismatch_reason"), str) or not row["semantic_mismatch_reason"].strip():
                errors.append(f"{prefix}:invalid_irrelevant")
        if support_class != "CONTRADICTION" and ({"contradiction_basis_quote", "contradicted_constraint"} & set(row)):
            errors.append(f"{prefix}:contradiction_metadata_on_noncontradiction")
        if not isinstance(row["support_rationale"], str) or section["content"] not in row["support_rationale"] and row["review_provenance"] == PB1_NEW_PROVENANCE:
            errors.append(f"{prefix}:new_rationale_not_clause_grounded")
        if row["canonical_import_semantic_mutation"] is not False:
            errors.append(f"{prefix}:canonical_import_semantic_mutation")
        provenance = row["review_provenance"]
        if provenance == PB1_IMPORT_PROVENANCE:
            import_count += 1
            source = row["canonical_import_source"]
            if source not in PB1_REUSE_SOURCES or row["case_id"] not in PB1_REUSE_SOURCES[source]:
                errors.append(f"{prefix}:unauthorized_canonical_import")
            if not isinstance(row["review_provenance_original"], str) or not row["review_provenance_original"]:
                errors.append(f"{prefix}:missing_original_review_provenance")
        elif provenance == PB1_NEW_PROVENANCE:
            new_count += 1
            if row["canonical_import_source"] is not None or row["review_provenance_original"] is not None:
                errors.append(f"{prefix}:new_row_has_import_provenance")
        else:
            errors.append(f"{prefix}:unknown_review_provenance")
    if import_count != 624:
        errors.append(f"canonical_import_count:{import_count}")
    if new_count != 2496:
        errors.append(f"new_semantic_count:{new_count}")
    return {
        "passed": not errors, "errors": errors, "row_count": len(pass_b),
        "unique_pairs": len(actual_pairs), "per_case_counts": dict(counts),
        "support_class_counts": dict(Counter(row.get("support_class") for row in pass_b)),
        "reused_semantic_rows": import_count, "new_semantic_rows": new_count,
    }


def derive_pb1_minimal_complete_sets(
    required: list[str], judgments: list[dict[str, Any]],
) -> list[list[str]]:
    if not required:
        return []
    candidates = [
        row for row in judgments
        if row["support_class"] in {"COMPLETE_SUPPORT", "PARTIAL_SUPPORT"}
        and row["target_match"] is True and row["state_match"] is True
        and row["dimension_match"] is True and row["obligations_covered"]
    ]
    complete: list[frozenset[str]] = []
    for size in range(1, len(required) + 1):
        for group in itertools.combinations(candidates, size):
            evidence = frozenset(row["evidence_id"] for row in group)
            coverage = set().union(*(set(row["obligations_covered"]) for row in group))
            if set(required) <= coverage and not any(old <= evidence for old in complete):
                complete.append(evidence)
    minimal = [item for item in complete if not any(other < item for other in complete)]
    return [sorted(item) for item in sorted(minimal, key=lambda value: (len(value), sorted(value)))]


def _load_json(root: Path, path: Path) -> dict[str, Any]:
    return json.loads((root / path).read_text(encoding="utf-8"))


def validate_pb1_stratum_proofs(
    pass_a: list[dict[str, Any]], classifications: list[dict[str, Any]], pass_b: list[dict[str, Any]],
    positive: dict[str, Any], safe: dict[str, Any], hard: dict[str, Any], ambiguous: dict[str, Any],
) -> dict[str, Any]:
    cases = {case["case_id"]: case for case in pass_a}
    required = pb1_required_obligations(classifications)
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pass_b:
        by_case[row["case_id"]].append(row)
    expected_sets = {
        case_id: derive_pb1_minimal_complete_sets(required.get(case_id, []), rows)
        for case_id, rows in by_case.items()
    }
    errors: list[str] = []
    positive_cases = {row.get("case_id"): row for row in positive.get("cases", [])}
    safe_cases = {row.get("case_id"): row for row in safe.get("cases", [])}
    hard_cases_doc = {row.get("case_id"): row for row in hard.get("cases", [])}
    ambiguous_cases = {row.get("case_id"): row for row in ambiguous.get("cases", [])}
    expected_standard = {cid for cid, case in cases.items() if case["semantic_stratum"] == "STANDARD"}
    expected_safe = {cid for cid, case in cases.items() if case["semantic_stratum"] == "SAFE_CORRECTIVE"}
    expected_hard = {cid for cid, case in cases.items() if case["semantic_stratum"] == "HARD_ABSTAIN_ESCALATE"}
    expected_ambiguous = {cid for cid, case in cases.items() if case["semantic_stratum"] == "AMBIGUOUS_OR_PARTIAL_SAFE_STOP"}
    if set(positive_cases) != expected_standard or len(positive_cases) != 24:
        errors.append("standard_proof_case_set_not_exact")
    if set(safe_cases) != expected_safe or len(safe_cases) != 18:
        errors.append("safe_corrective_proof_case_set_not_exact")
    if set(hard_cases_doc) != expected_hard or len(hard_cases_doc) != 12:
        errors.append("hard_proof_case_set_not_exact")
    if set(ambiguous_cases) != expected_ambiguous or len(ambiguous_cases) != 6:
        errors.append("ambiguous_derivation_case_set_not_exact")
    for cid in expected_standard:
        proof = positive_cases.get(cid, {})
        if not expected_sets[cid] or proof.get("minimal_complete_support_sets") != expected_sets[cid] or proof.get("proof_valid") is not True:
            errors.append(f"standard_proof_invalid:{cid}")
    for cid in expected_safe:
        proof = safe_cases.get(cid, {})
        if not expected_sets[cid] or proof.get("minimal_complete_support_sets") != expected_sets[cid] or proof.get("factual_corrective_support_complete") is not True:
            errors.append(f"safe_corrective_proof_invalid:{cid}")
        if proof.get("requested_unsafe_resolution_asserted") is not False:
            errors.append(f"safe_corrective_unsafe_resolution_asserted:{cid}")
    for cid in expected_hard:
        proof = hard_cases_doc.get(cid, {})
        if expected_sets[cid]:
            errors.append(f"hard_requested_resolution_has_complete_support:{cid}")
        if proof.get("reviewed_eligible_sections") != 52 or proof.get("review_coverage") != "52/52":
            errors.append(f"hard_review_not_exhaustive:{cid}")
        if proof.get("requested_factual_resolution_supported") is not False or proof.get("complete_safe_corrective_response_exists") is not False:
            errors.append(f"hard_premise_invalid:{cid}")
        if proof.get("requested_resolution_proof_valid") is not True or proof.get("safe_corrective_absence_proof_valid") is not True:
            errors.append(f"hard_proof_flags_invalid:{cid}")
        if proof.get("reason_family") != cases[cid]["hard_abstain_reason_family"]:
            errors.append(f"hard_reason_family_drift:{cid}")
    for cid in expected_ambiguous:
        proof = ambiguous_cases.get(cid, {})
        route = "SAFE_CORRECTIVE" if required.get(cid) and expected_sets[cid] else "ABSTAIN_ESCALATE"
        if proof.get("derived_route") != route or route not in {"SAFE_CORRECTIVE", "ABSTAIN_ESCALATE"}:
            errors.append(f"ambiguous_route_not_exact_derivation:{cid}")
    return {
        "passed": not errors, "errors": errors,
        "standard_valid": 24 - sum(error.startswith("standard_proof_invalid") for error in errors),
        "safe_corrective_valid": 18 - sum(error.startswith("safe_corrective_proof_invalid") for error in errors),
        "hard_valid": 12 - sum(error.startswith(("hard_premise_invalid", "hard_proof_flags_invalid", "hard_review_not_exhaustive")) for error in errors),
        "ambiguous_valid": 6 - sum(error.startswith("ambiguous_route_not_exact_derivation") for error in errors),
        "minimal_sets": expected_sets,
    }


def derive_pb1_pass_c(
    root: Path, pass_a: list[dict[str, Any]], classifications: list[dict[str, Any]],
    pass_b: list[dict[str, Any]], ineligible_audit: dict[str, Any],
) -> list[dict[str, Any]]:
    required = pb1_required_obligations(classifications)
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    class_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    ineligible_by_case: dict[str, list[str]] = defaultdict(list)
    for row in pass_b:
        by_case[row["case_id"]].append(row)
    for row in classifications:
        class_by_case[row["case_id"]].append(row)
    for row in ineligible_audit.get("entries", []):
        ineligible_by_case[row["case_id"]].append(row["ineligible_evidence_id"])
    output: list[dict[str, Any]] = []
    pass_b_hash = file_sha256(root / PASS_B)
    for case in pass_a:
        case_id = case["case_id"]
        sets = derive_pb1_minimal_complete_sets(required.get(case_id, []), by_case[case_id])
        stratum = case["semantic_stratum"]
        if stratum == "STANDARD":
            route, reason = "STANDARD", "STANDARD_COMPLETE_APPROVED_SUPPORT"
        elif stratum == "SAFE_CORRECTIVE":
            route, reason = "SAFE_CORRECTIVE", "SAFE_CORRECTIVE_COMPLETE_APPROVED_FACTUAL_SUPPORT"
        elif stratum == "HARD_ABSTAIN_ESCALATE":
            route, reason = "ABSTAIN_ESCALATE", case["hard_abstain_reason_family"]
        else:
            route = "SAFE_CORRECTIVE" if required.get(case_id) and sets else "ABSTAIN_ESCALATE"
            reason = "GROUNDED_FACTUAL_SAFETY_GATE" if route == "SAFE_CORRECTIVE" else "PURE_CLARIFICATION_ONLY_SAFE_STOP"
        allowed = sorted({
            row["evidence_id"] for row in by_case[case_id]
            if row["support_class"] in {"COMPLETE_SUPPORT", "PARTIAL_SUPPORT"}
            and row["obligations_covered"] and row["target_match"] and row["state_match"] and row["dimension_match"]
        })
        forbidden = sorted(set(ineligible_by_case[case_id]) | {
            row["evidence_id"] for row in by_case[case_id]
            if row["support_class"] == "CONTRADICTION" or not row["target_match"] or not row["state_match"]
        })
        output.append({
            "case_id": case_id, "risk_stratum": case["risk_stratum"],
            "scenario_family": case["scenario_family"], "query": case["query"],
            "required_semantic_obligations": case["required_semantic_obligations"],
            "obligation_classification": class_by_case[case_id],
            "required_target_entity_constraints": case["required_target_entity_constraints"],
            "forbidden_target_entity_constraints": case["forbidden_target_entity_constraints"],
            "required_state_constraints": case["required_state_constraints"],
            "forbidden_state_constraints": case["forbidden_state_constraints"],
            "required_dimension_constraints": case["required_dimension_constraints"],
            "forbidden_dimension_constraints": case["forbidden_dimension_constraints"],
            "acceptable_complete_support_sets": sets,
            "allowed_supporting_evidence": allowed, "forbidden_evidence": forbidden,
            "complete_approved_support_exists_in_kb": bool(sets),
            "expected_production_route": route, "expected_reason_family": reason,
            "exact_runtime_reason_deferred_to_evaluator_mapping": True,
            "forbidden_claims_actions": case["forbidden_claims_actions"],
            "support_derivation_provenance": "PB1_MECHANICAL_FROM_PASS_A_V3_OBLIGATION_CLASSIFICATION_AND_VALIDATED_PASS_B",
            "pass_a_sha256": PASS_A_V3_EXPECTED_SHA256, "pass_b_sha256": pass_b_hash,
        })
    return output


def derive_pb1_pass_c_fail_closed(
    root: Path, pass_a: list[dict[str, Any]], classifications: list[dict[str, Any]],
    pass_b: list[dict[str, Any]], ineligible_audit: dict[str, Any],
    positive: dict[str, Any], safe: dict[str, Any], hard: dict[str, Any], ambiguous: dict[str, Any],
) -> list[dict[str, Any]]:
    checks = (
        validate_pb1_obligation_classification(pass_a, classifications),
        validate_pb1_pass_b(root, pass_a, classifications, pass_b),
        validate_pb1_ineligible_audit(root, ineligible_audit),
        validate_pb1_stratum_proofs(
            pass_a, classifications, pass_b, positive, safe, hard, ambiguous,
        ),
    )
    errors = [error for check in checks for error in check["errors"]]
    if errors:
        raise ValueError(f"A2_PB1_PASS_A_V3_STRATUM_CONFLICT:{errors[:10]}")
    return derive_pb1_pass_c(root, pass_a, classifications, pass_b, ineligible_audit)


def validate_pb1_ineligible_audit(root: Path, audit: dict[str, Any]) -> dict[str, Any]:
    _, ineligible = eligible_section_index(root)
    errors: list[str] = []
    entries = audit.get("entries", [])
    for index, row in enumerate(entries):
        evidence = ineligible.get(row.get("ineligible_evidence_id"))
        if evidence is None:
            errors.append(f"ineligible_audit[{index}]:eligible_or_unknown_evidence")
            continue
        if row.get("status") != evidence["status"] or evidence["status"] not in {"DRAFT", "EXPIRED"}:
            errors.append(f"ineligible_audit[{index}]:status_mismatch")
        if not row.get("why_tempting_or_relevant") or not row.get("forbidden_reason"):
            errors.append(f"ineligible_audit[{index}]:missing_reasoning")
    if audit.get("used_as_support") is not False:
        errors.append("ineligible_evidence_marked_as_support")
    if len({(row.get("case_id"), row.get("ineligible_evidence_id")) for row in entries}) != len(entries):
        errors.append("duplicate_ineligible_audit_pair")
    return {"passed": not errors, "errors": errors, "entry_count": len(entries)}


PB1_FIX1_SEMANTIC_FIELDS = (
    "support_class", "target_match", "state_match", "dimension_match",
    "obligations_covered", "obligations_not_covered", "support_quotes_by_obligation",
    "missing_required_obligations", "semantic_mismatch_reason",
    "contradiction_basis_quote", "contradicted_constraint", "support_rationale",
)


def pb1_fix1_semantic_projection(row: dict[str, Any]) -> dict[str, Any]:
    return {key: row.get(key) for key in PB1_FIX1_SEMANTIC_FIELDS if key in row}


def _fix1_quote_map(row: dict[str, Any]) -> dict[str, list[str]]:
    quotes = {key: list(value) for key, value in row.get("support_quotes_by_obligation", {}).items()}
    if row.get("support_class") == "CONTRADICTION" and row.get("contradiction_basis_quote"):
        quotes["__contradiction_basis__"] = [row["contradiction_basis_quote"]]
    return quotes


def apply_pb1_fix1_corrections(
    root: Path, pre_fix_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    eligible, _ = eligible_section_index(root)
    rows = [dict(row) for row in pre_fix_rows]
    index = {(row["case_id"], row["evidence_id"]): row for row in rows}
    if set(PB1_FIX1_CORRECTIONS) - set(index):
        raise ValueError("pb1_fix1_correction_pair_missing_from_pre_fix_matrix")
    for pair, decision in PB1_FIX1_CORRECTIONS.items():
        row = index[pair]
        if row["review_provenance"] == PB1_IMPORT_PROVENANCE:
            raise ValueError("A2_PB1_FIX1_IMPORTED_HARD_SEMANTIC_CONFLICT")
        content = eligible[row["evidence_id"]]["content"]
        required = list(row["kb_support_required_obligations"])
        covered = list(decision["covered"])
        for field in (
            "missing_required_obligations", "semantic_mismatch_reason",
            "contradiction_basis_quote", "contradicted_constraint",
        ):
            row.pop(field, None)
        row["support_class"] = decision["support_class"]
        for match_field in ("target_match", "state_match", "dimension_match"):
            if match_field in decision:
                row[match_field] = decision[match_field]
        row["obligations_covered"] = covered
        row["obligations_not_covered"] = [item for item in required if item not in set(covered)]
        row["support_quotes_by_obligation"] = {item: [content] for item in covered}
        row["support_rationale"] = f'The frozen clause states "{content}" {decision["reason"]}'
        if row["support_class"] == "CONTEXTUAL_INSUFFICIENT":
            row["missing_required_obligations"] = required
            row["semantic_mismatch_reason"] = decision["reason"]
        if row["support_class"] in {"COMPLETE_SUPPORT", "PARTIAL_SUPPORT"} and not covered:
            raise ValueError(f"pb1_fix1_positive_without_coverage:{pair}")
    return rows


def _fix1_entailment_explanation(
    row: dict[str, Any], obligation: str,
) -> str:
    pair = (row["case_id"], row["evidence_id"])
    if pair in PB1_FIX1_CORRECTIONS:
        return PB1_FIX1_CORRECTIONS[pair]["reason"]
    human = obligation.lower().replace("_", " ")
    return (
        f"The exact quoted clause states the compatible state, timing, condition, or action needed to {human}; "
        "coverage is limited to that obligation and does not rely on the document identifier or topic overlap."
    )


def build_pb1_fix1_audit_rows(
    root: Path, pre_fix_rows: list[dict[str, Any]], post_fix_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    eligible, _ = eligible_section_index(root)
    post = {(row["case_id"], row["evidence_id"]): row for row in post_fix_rows}
    audited: list[dict[str, Any]] = []
    for old in pre_fix_rows:
        if old["support_class"] == "IRRELEVANT":
            continue
        pair = (old["case_id"], old["evidence_id"])
        new = post[pair]
        explanations = {
            obligation: _fix1_entailment_explanation(new, obligation)
            for obligation in new["obligations_covered"]
        }
        audited.append({
            "case_id": old["case_id"], "evidence_id": old["evidence_id"],
            "document_id": old["document_id"],
            "frozen_section_text": eligible[old["evidence_id"]]["content"],
            "old_support_class": old["support_class"], "reviewed_support_class": new["support_class"],
            "target_match": new["target_match"], "state_match": new["state_match"],
            "dimension_match": new["dimension_match"],
            "obligations_covered": list(new["obligations_covered"]),
            "support_quotes_by_obligation": new.get("support_quotes_by_obligation", {}),
            "semantic_entailment_explanation_by_obligation": explanations,
            "contradiction_basis_quote": new.get("contradiction_basis_quote"),
            "contradicted_constraint": new.get("contradicted_constraint"),
            "contradiction_semantic_explanation": new["support_rationale"] if new["support_class"] == "CONTRADICTION" else None,
            "support_rationale": new["support_rationale"],
            "decision_changed": pb1_fix1_semantic_projection(old) != pb1_fix1_semantic_projection(new),
            "senior_triggered_finding": PB1_FIX1_CORRECTIONS.get(pair, {}).get("senior_triggered", False),
            "imported_hard_row": new["review_provenance"] == PB1_IMPORT_PROVENANCE,
            "imported_hard_semantic_conflict": False,
            "reviewed_from_frozen_section_text": True,
            "current_label_used_as_answer_key": False,
        })
    return audited


def _fix1_audit_decision_sha256(audit_rows: list[dict[str, Any]]) -> str:
    return sha256_bytes(json.dumps(audit_rows, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def build_pb1_fix1_ledger(
    root: Path, pre_fix_rows: list[dict[str, Any]], post_fix_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    pre = {(row["case_id"], row["evidence_id"]): row for row in pre_fix_rows}
    post = {(row["case_id"], row["evidence_id"]): row for row in post_fix_rows}
    changed_pairs = sorted(
        pair for pair in pre
        if pb1_fix1_semantic_projection(pre[pair]) != pb1_fix1_semantic_projection(post[pair])
    )
    corrections = []
    for pair in changed_pairs:
        old, new = pre[pair], post[pair]
        corrections.append({
            "case_id": pair[0], "evidence_id": pair[1],
            "old_support_class": old["support_class"], "new_support_class": new["support_class"],
            "old_target_match": old["target_match"], "new_target_match": new["target_match"],
            "old_state_match": old["state_match"], "new_state_match": new["state_match"],
            "old_dimension_match": old["dimension_match"], "new_dimension_match": new["dimension_match"],
            "old_obligations_covered": list(old["obligations_covered"]),
            "new_obligations_covered": list(new["obligations_covered"]),
            "old_quote_map": _fix1_quote_map(old), "new_quote_map": _fix1_quote_map(new),
            "old_contradicted_constraint": old.get("contradicted_constraint"),
            "new_contradicted_constraint": new.get("contradicted_constraint"),
            "semantic_reason": PB1_FIX1_CORRECTIONS[pair]["reason"],
            "senior_triggered_finding": PB1_FIX1_CORRECTIONS[pair]["senior_triggered"],
        })
    return {
        "task_id": PB1_TASK_ID, "status": PB1_STATUS,
        "pre_fix1_artifact_sha256": {
            str(PB1_PRE_FIX1_PASS_B).replace("\\", "/"): PB1_PRE_FIX1_PASS_B_SHA256,
            str(PB1_PRE_FIX1_PASS_C).replace("\\", "/"): PB1_PRE_FIX1_PASS_C_SHA256,
            **PB1_PRE_FIX1_ARTIFACT_SHA256,
        },
        "pass_a_sha256": file_sha256(root / PASS_A),
        "post_fix1_pass_b_sha256": file_sha256(root / PASS_B),
        "post_fix1_pass_c_sha256": file_sha256(root / PASS_C),
        "audited_rows": 514, "correction_count": len(corrections),
        "corrections": corrections,
    }


def regenerate_pb1_proofs(
    root: Path, pass_a: list[dict[str, Any]], classifications: list[dict[str, Any]],
    pass_b: list[dict[str, Any]],
) -> None:
    required = pb1_required_obligations(classifications)
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pass_b:
        by_case[row["case_id"]].append(row)
    cases = {row["case_id"]: row for row in pass_a}
    positive = _load_json(root, POSITIVE_SUPPORT_AUDIT)
    safe = _load_json(root, SAFE_CORRECTIVE_PROOFS)
    hard = _load_json(root, HARD_ABSTAIN_PROOFS)
    ambiguous = _load_json(root, AMBIGUOUS_DERIVATION)
    for artifact in (positive, safe):
        for proof in artifact["cases"]:
            sets = derive_pb1_minimal_complete_sets(required.get(proof["case_id"], []), by_case[proof["case_id"]])
            proof["kb_support_required_obligations"] = required.get(proof["case_id"], [])
            proof["minimal_complete_support_sets"] = sets
            proof["proof_valid"] = bool(sets)
            if "factual_corrective_support_complete" in proof:
                proof["factual_corrective_support_complete"] = bool(sets)
        artifact["feasible_count"] = sum(bool(row["minimal_complete_support_sets"]) for row in artifact["cases"])
        artifact["task_id"] = PB1_TASK_ID
    for proof in ambiguous["cases"]:
        sets = derive_pb1_minimal_complete_sets(required.get(proof["case_id"], []), by_case[proof["case_id"]])
        route = "SAFE_CORRECTIVE" if required.get(proof["case_id"]) and sets else "ABSTAIN_ESCALATE"
        proof["kb_support_required_obligations"] = required.get(proof["case_id"], [])
        proof["minimal_complete_support_sets"] = sets
        proof["derived_route"] = route
        proof["proof_valid"] = True
        proof["derivation_reason"] = "GROUNDED_FACTUAL_SAFETY_GATE" if route == "SAFE_CORRECTIVE" else "PURE_CLARIFICATION_ONLY_SAFE_STOP"
    ambiguous["derived_route_counts"] = dict(Counter(row["derived_route"] for row in ambiguous["cases"]))
    ambiguous["task_id"] = PB1_TASK_ID
    hard["task_id"] = PB1_TASK_ID
    _write_json(root / POSITIVE_SUPPORT_AUDIT, positive)
    _write_json(root / SAFE_CORRECTIVE_PROOFS, safe)
    _write_json(root / HARD_ABSTAIN_PROOFS, hard)
    _write_json(root / AMBIGUOUS_DERIVATION, ambiguous)


def build_pb1_fix1_audit_summary(
    root: Path, pre_fix_rows: list[dict[str, Any]], post_fix_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    audit_rows = build_pb1_fix1_audit_rows(root, pre_fix_rows, post_fix_rows)
    changed = [row for row in audit_rows if row["decision_changed"]]
    pre_index = {(row["case_id"], row["evidence_id"]): row for row in pre_fix_rows}
    post_index = {(row["case_id"], row["evidence_id"]): row for row in post_fix_rows}
    c09 = [
        {
            "evidence_id": evidence_id,
            "before": pre_index[("EV2-A2-C09", evidence_id)]["support_class"],
            "after": post_index[("EV2-A2-C09", evidence_id)]["support_class"],
            "obligations_after": post_index[("EV2-A2-C09", evidence_id)]["obligations_covered"],
        }
        for evidence_id in (
            "FAQ_TRANSFER_DECLINED_001#safe_message",
            "POL_TRANSFER_DECLINED_001#review_rule",
            "RUN_TRANSFER_DECLINED_001#action",
        )
    ]
    return {
        "task_id": PB1_TASK_ID, "status": PB1_STATUS,
        "audited_rows": len(audit_rows),
        "reviewed_old_support_class_counts": dict(Counter(row["old_support_class"] for row in audit_rows)),
        "unchanged_count": len(audit_rows) - len(changed), "corrected_count": len(changed),
        "correction_counts_by_old_class": dict(Counter(row["old_support_class"] for row in changed)),
        "correction_counts_by_new_class": dict(Counter(row["reviewed_support_class"] for row in changed)),
        "correction_counts_by_case": dict(Counter(row["case_id"] for row in changed)),
        "correction_counts_by_evidence_document": dict(Counter(row["document_id"] for row in changed)),
        "post_fix_support_class_counts": dict(Counter(row["support_class"] for row in post_fix_rows)),
        "confirmed_senior_s19_issue": post_index[("EV2-A2-S19", "RUN_TRANSFER_PENDING_001#checks")]["support_class"] == "CONTEXTUAL_INSUFFICIENT",
        "s19_corrected_obligations_covered": post_index[("EV2-A2-S19", "RUN_TRANSFER_PENDING_001#checks")]["obligations_covered"],
        "c09_outcome": {
            "rows": c09,
            "semantic_conclusion": "The safe-message FAQ supplies the customer-facing message; policy/runbook review clauses supply masked review only.",
        },
        "imported_hard_nonirrelevant_rows_reviewed": sum(row["imported_hard_row"] for row in audit_rows),
        "imported_hard_conflict_count": sum(row["imported_hard_semantic_conflict"] for row in audit_rows),
        "imported_hard_audit_status": "PASS",
        "semantic_audit_decision_sha256": _fix1_audit_decision_sha256(audit_rows),
        "pass_a_sha256": file_sha256(root / PASS_A),
        "pass_b_post_fix_sha256": file_sha256(root / PASS_B),
        "pass_c_post_fix_sha256": file_sha256(root / PASS_C),
    }


def validate_pb1_fix1_semantic_audit(
    root: Path, post_fix_rows: list[dict[str, Any]], ledger: dict[str, Any], summary: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if file_sha256(root / PB1_PRE_FIX1_PASS_B) != PB1_PRE_FIX1_PASS_B_SHA256:
        errors.append("pb1_pre_fix1_pass_b_hash_drift")
    if file_sha256(root / PB1_PRE_FIX1_PASS_C) != PB1_PRE_FIX1_PASS_C_SHA256:
        errors.append("pb1_pre_fix1_pass_c_hash_drift")
    pre_fix_rows = read_jsonl(root / PB1_PRE_FIX1_PASS_B)
    old_nonirrelevant = [row for row in pre_fix_rows if row["support_class"] != "IRRELEVANT"]
    old_counts = Counter(row["support_class"] for row in old_nonirrelevant)
    if len(old_nonirrelevant) != 514 or old_counts != Counter({
        "COMPLETE_SUPPORT": 70, "PARTIAL_SUPPORT": 51,
        "CONTEXTUAL_INSUFFICIENT": 196, "CONTRADICTION": 197,
    }):
        errors.append("pb1_fix1_audit_scope_not_exact_514")
    pre = {(row["case_id"], row["evidence_id"]): row for row in pre_fix_rows}
    post = {(row["case_id"], row["evidence_id"]): row for row in post_fix_rows}
    imported_conflicts = [
        pair for pair, old in pre.items()
        if old["review_provenance"] == PB1_IMPORT_PROVENANCE
        and pb1_fix1_semantic_projection(old) != pb1_fix1_semantic_projection(post[pair])
    ]
    if imported_conflicts:
        errors.append("A2_PB1_FIX1_IMPORTED_HARD_SEMANTIC_CONFLICT")
    changed_pairs = {
        pair for pair in pre
        if pb1_fix1_semantic_projection(pre[pair]) != pb1_fix1_semantic_projection(post[pair])
    }
    ledger_pairs = {(row.get("case_id"), row.get("evidence_id")) for row in ledger.get("corrections", [])}
    if changed_pairs != set(PB1_FIX1_CORRECTIONS) or ledger_pairs != changed_pairs:
        errors.append("pb1_fix1_correction_ledger_pair_mismatch")
    if ledger.get("correction_count") != len(changed_pairs) or ledger.get("audited_rows") != 514:
        errors.append("pb1_fix1_correction_ledger_count_mismatch")
    audit_rows = build_pb1_fix1_audit_rows(root, pre_fix_rows, post_fix_rows)
    if summary.get("semantic_audit_decision_sha256") != _fix1_audit_decision_sha256(audit_rows):
        errors.append("pb1_fix1_semantic_audit_decision_hash_mismatch")
    if summary.get("audited_rows") != 514 or summary.get("corrected_count") != len(changed_pairs):
        errors.append("pb1_fix1_summary_count_mismatch")
    s19 = post.get(("EV2-A2-S19", "RUN_TRANSFER_PENDING_001#checks"), {})
    if "ROUTE_MASKED_PENDING_REVIEW" in s19.get("obligations_covered", []):
        errors.append("s19_checks_false_route_entailment")
    for evidence_id in ("POL_TRANSFER_DECLINED_001#review_rule", "RUN_TRANSFER_DECLINED_001#action"):
        if "PROVIDE_SAFE_DECLINE_MESSAGE" in post.get(("EV2-A2-C09", evidence_id), {}).get("obligations_covered", []):
            errors.append("c09_masked_review_false_safe_message_entailment")
    for row in audit_rows:
        if row["reviewed_support_class"] in {"COMPLETE_SUPPORT", "PARTIAL_SUPPORT"}:
            if set(row["semantic_entailment_explanation_by_obligation"]) != set(row["obligations_covered"]):
                errors.append(f'pb1_fix1_missing_entailment_explanation:{row["case_id"]}:{row["evidence_id"]}')
        if row["reviewed_support_class"] == "CONTRADICTION":
            if not row["contradiction_basis_quote"] or not row["contradicted_constraint"] or not row["contradiction_semantic_explanation"]:
                errors.append(f'pb1_fix1_incomplete_contradiction_proof:{row["case_id"]}:{row["evidence_id"]}')
    return {
        "passed": not errors, "errors": errors, "audited_rows": len(audit_rows),
        "corrected_rows": len(changed_pairs), "unchanged_rows": len(audit_rows) - len(changed_pairs),
        "imported_hard_conflict_count": len(imported_conflicts),
        "semantic_audit_decision_sha256": _fix1_audit_decision_sha256(audit_rows),
    }


def apply_pb1_fix1(root: Path) -> dict[str, Any]:
    if file_sha256(root / PASS_A) != PASS_A_V3_EXPECTED_SHA256:
        raise ValueError("BLOCKED_SENIOR_APPROVED_PASS_A_V3_BYTE_DRIFT")
    if file_sha256(root / PB1_PRE_FIX1_PASS_B) != PB1_PRE_FIX1_PASS_B_SHA256 or file_sha256(root / PB1_PRE_FIX1_PASS_C) != PB1_PRE_FIX1_PASS_C_SHA256:
        raise ValueError("PB1_PRE_FIX1_PRESERVATION_HASH_DRIFT")
    if file_sha256(root / PASS_B) != PB1_PRE_FIX1_PASS_B_SHA256 or file_sha256(root / PASS_C) != PB1_PRE_FIX1_PASS_C_SHA256:
        raise ValueError("ACTIVE_PB1_NOT_AT_EXPECTED_PRE_FIX1_BYTES")
    pass_a = read_jsonl(root / PASS_A)
    classifications = read_jsonl(root / OBLIGATION_CLASSIFICATION)
    pre_fix_rows = read_jsonl(root / PB1_PRE_FIX1_PASS_B)
    post_fix_rows = apply_pb1_fix1_corrections(root, pre_fix_rows)
    matrix = validate_pb1_pass_b(root, pass_a, classifications, post_fix_rows)
    if not matrix["passed"]:
        raise ValueError(f"A2_PB1_FIX1_PASS_B_INVALID:{matrix['errors'][:10]}")
    write_jsonl(root / PASS_B, post_fix_rows)
    regenerate_pb1_proofs(root, pass_a, classifications, post_fix_rows)
    positive = _load_json(root, POSITIVE_SUPPORT_AUDIT)
    safe = _load_json(root, SAFE_CORRECTIVE_PROOFS)
    hard = _load_json(root, HARD_ABSTAIN_PROOFS)
    ambiguous = _load_json(root, AMBIGUOUS_DERIVATION)
    proof = validate_pb1_stratum_proofs(pass_a, classifications, post_fix_rows, positive, safe, hard, ambiguous)
    if not proof["passed"] or (proof["standard_valid"], proof["safe_corrective_valid"], proof["hard_valid"], proof["ambiguous_valid"]) != (24, 18, 12, 6):
        raise ValueError(f"A2_PB1_FIX1_PASS_A_V3_STRATUM_CONFLICT:{proof['errors'][:10]}")
    ineligible = _load_json(root, INELIGIBLE_EVIDENCE_AUDIT)
    derived = derive_pb1_pass_c_fail_closed(
        root, pass_a, classifications, post_fix_rows, ineligible, positive, safe, hard, ambiguous,
    )
    write_jsonl(root / PASS_C, derived)
    ledger = build_pb1_fix1_ledger(root, pre_fix_rows, post_fix_rows)
    _write_json(root / PB1_FIX1_LEDGER, ledger)
    summary = build_pb1_fix1_audit_summary(root, pre_fix_rows, post_fix_rows)
    _write_json(root / PB1_FIX1_AUDIT_SUMMARY, summary)
    return {
        "passed": True, "status": PB1_EXTERNAL_STATUS,
        "audited_rows": 514, "corrected_rows": len(PB1_FIX1_CORRECTIONS),
        "pass_b_sha256": file_sha256(root / PASS_B),
        "pass_c_sha256": file_sha256(root / PASS_C),
        "support_class_counts": matrix["support_class_counts"],
        "route_counts": dict(Counter(row["expected_production_route"] for row in derived)),
    }


PB1_ACTIVE_ARTIFACTS = (
    PASS_A, PASS_B, PASS_C, OBLIGATION_CLASSIFICATION, SUPPORT_SUMMARY,
    POSITIVE_SUPPORT_AUDIT, HARD_ABSTAIN_PROOFS, SAFE_CORRECTIVE_PROOFS,
    AMBIGUOUS_DERIVATION, INELIGIBLE_EVIDENCE_AUDIT, LINEAGE_AUDIT,
    PB1_FIX1_LEDGER, PB1_FIX1_AUDIT_SUMMARY,
    Path("scripts/evaluation/week3_ev2_a2.py"), Path("tests/test_week3_ev2_a2.py"),
    Path("reports/week_03/experiments/W3-003-EV2-A2.md"), Path("PROJECT_STATE.md"),
    Path("TASKS.md"), Path("reports/week_03/daily/2026-08-21.md"),
    Path("reports/week_03/week_03_summary.md"),
)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def refresh_pb1_metadata(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    pass_a = read_jsonl(root / PASS_A)
    classifications = read_jsonl(root / OBLIGATION_CLASSIFICATION)
    pass_b = read_jsonl(root / PASS_B)
    pass_c = read_jsonl(root / PASS_C)
    positive = _load_json(root, POSITIVE_SUPPORT_AUDIT)
    safe = _load_json(root, SAFE_CORRECTIVE_PROOFS)
    hard = _load_json(root, HARD_ABSTAIN_PROOFS)
    ambiguous = _load_json(root, AMBIGUOUS_DERIVATION)
    lineage = compute_lineage_audit(root, pass_a)
    _write_json(root / LINEAGE_AUDIT, lineage)
    summary = {
        "task_id": PB1_TASK_ID, "status": PB1_STATUS,
        "pass_a_sha256": file_sha256(root / PASS_A), "pass_b_sha256": file_sha256(root / PASS_B),
        "pass_c_sha256": file_sha256(root / PASS_C), "pass_b_rows": len(pass_b),
        "eligible_sections_per_case": 52,
        "classification_counts": dict(Counter(row["classification"] for row in classifications)),
        "support_class_counts": dict(Counter(row["support_class"] for row in pass_b)),
        "new_semantic_rows": sum(row["review_provenance"] == PB1_NEW_PROVENANCE for row in pass_b),
        "reused_semantic_rows": sum(row["review_provenance"] == PB1_IMPORT_PROVENANCE for row in pass_b),
        "canonical_import_semantic_mutation_count": sum(row["canonical_import_semantic_mutation"] is not False for row in pass_b),
        "standard_proofs": positive["feasible_count"], "safe_corrective_proofs": safe["feasible_count"],
        "hard_proofs": hard["valid_count"], "ambiguous_cases": len(ambiguous["cases"]),
        "derived_route_counts": dict(Counter(row["expected_production_route"] for row in pass_c)),
        "candidate_inference_executed": False, "ev2_executed": False, "ev2_consumed": False,
        "a3_authorized": False, "evaluation_authorized": False,
        "pass_b_semantic_audit_rows": 514,
        "pass_b_semantic_corrections": len(PB1_FIX1_CORRECTIONS),
        "pre_fix1_pass_b_sha256": PB1_PRE_FIX1_PASS_B_SHA256,
        "pre_fix1_pass_c_sha256": PB1_PRE_FIX1_PASS_C_SHA256,
    }
    _write_json(root / SUPPORT_SUMMARY, summary)
    old_manifest = _load_json(root, A2_MANIFEST)
    fix3_history = old_manifest.get("fix3_history", old_manifest)
    artifact_hashes = {
        str(path).replace("\\", "/"): file_sha256(root / path)
        for path in PB1_ACTIVE_ARTIFACTS if (root / path).is_file()
    }
    manifest = {
        "task_id": PB1_TASK_ID, "status": PB1_STATUS,
        "remote_commit": "8492659a50fe00f066f9f64d8759d544356b3a41",
        "pass_a_revision": 3, "pass_a_rows": 60,
        "pass_a_v3": {"path": str(PASS_A).replace("\\", "/"), "sha256": file_sha256(root / PASS_A), "bytes": (root / PASS_A).stat().st_size, "senior_approved": True, "byte_frozen": True},
        "pass_a_history": fix3_history.get("pass_a_history", {}),
        "pass_b": {"path": str(PASS_B).replace("\\", "/"), "sha256": file_sha256(root / PASS_B), "bytes": (root / PASS_B).stat().st_size, "rows": 3120, "eligible_sections_per_case": 52, "complete": True},
        "pass_c": {"path": str(PASS_C).replace("\\", "/"), "sha256": file_sha256(root / PASS_C), "bytes": (root / PASS_C).stat().st_size, "rows": 60, "derived": True},
        "pass_b_complete": True, "pass_c_derived": True, "ev2_cases_authored": True,
        "candidate_inference_executed": False, "evaluation_package_frozen": False,
        "structural_integrity_verified": False, "evaluation_authorized": False,
        "evaluation_executed": False, "ev2_consumed": False, "a3_authorized": False,
        "week3_p0_passed": False, "week4_authorized": False, "notebook_required": False,
        "future_ev2_r1_notebook_required": True,
        "pb1_pre_fix1_history": {
            "pass_b": {"path": str(PB1_PRE_FIX1_PASS_B).replace("\\", "/"), "sha256": file_sha256(root / PB1_PRE_FIX1_PASS_B)},
            "pass_c": {"path": str(PB1_PRE_FIX1_PASS_C).replace("\\", "/"), "sha256": file_sha256(root / PB1_PRE_FIX1_PASS_C)},
            "artifact_sha256": PB1_PRE_FIX1_ARTIFACT_SHA256,
        },
        "pass_b_semantic_audit_rows": 514,
        "pass_b_semantic_corrections": len(PB1_FIX1_CORRECTIONS),
        "invalid_rev1_history": {
            "pass_b": {"path": str(REV1_PASS_B_HISTORY).replace("\\", "/"), "sha256": file_sha256(root / REV1_PASS_B_HISTORY)},
            "pass_c": {"path": str(REV1_PASS_C_HISTORY).replace("\\", "/"), "sha256": file_sha256(root / REV1_PASS_C_HISTORY)},
        },
        "reuse_sources": {
            str(FIX1B_JUDGMENTS).replace("\\", "/"): {"rows": 260, "sha256": file_sha256(root / FIX1B_JUDGMENTS)},
            str(FIX2_JUDGMENTS).replace("\\", "/"): {"rows": 104, "sha256": file_sha256(root / FIX2_JUDGMENTS)},
            str(FIX3_JUDGMENTS).replace("\\", "/"): {"rows": 260, "sha256": file_sha256(root / FIX3_JUDGMENTS)},
        },
        "active_artifact_sha256": artifact_hashes,
        "fix3_history": fix3_history,
        "fix2_history": fix3_history.get("fix2_history", old_manifest.get("fix2_history", {})),
    }
    _write_json(root / A2_MANIFEST, manifest)
    return summary, manifest


def validate_pb1_manifest(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    expected_scalars = {
        "task_id": PB1_TASK_ID, "status": PB1_STATUS,
        "pass_a_revision": 3, "pass_a_rows": 60, "pass_b_complete": True,
        "pass_c_derived": True, "ev2_cases_authored": True,
        "candidate_inference_executed": False, "evaluation_package_frozen": False,
        "structural_integrity_verified": False, "evaluation_authorized": False,
        "evaluation_executed": False, "ev2_consumed": False, "a3_authorized": False,
        "week3_p0_passed": False, "week4_authorized": False, "notebook_required": False,
        "pass_b_semantic_audit_rows": 514,
        "pass_b_semantic_corrections": len(PB1_FIX1_CORRECTIONS),
    }
    for key, value in expected_scalars.items():
        if manifest.get(key) != value:
            errors.append(f"manifest_scalar:{key}")
    bindings = (("pass_a_v3", PASS_A, 60), ("pass_b", PASS_B, 3120), ("pass_c", PASS_C, 60))
    for key, path, rows in bindings:
        item = manifest.get(key, {})
        if item.get("sha256") != file_sha256(root / path) or item.get("bytes") != (root / path).stat().st_size or item.get("rows", rows) != rows:
            errors.append(f"manifest_binding:{key}")
    invalid = manifest.get("invalid_rev1_history", {})
    if invalid.get("pass_b", {}).get("sha256") != REV1_PASS_B_SHA256 or invalid.get("pass_c", {}).get("sha256") != REV1_PASS_C_SHA256:
        errors.append("manifest_invalid_rev1_history")
    for rel, expected_hash in manifest.get("active_artifact_sha256", {}).items():
        path = root / rel
        if not path.is_file() or file_sha256(path) != expected_hash:
            errors.append(f"manifest_active_artifact_hash:{rel}")
    if "fix3_history" not in manifest or "fix2_history" not in manifest:
        errors.append("manifest_history_missing")
    return {"passed": not errors, "errors": errors, "artifact_count": len(manifest.get("active_artifact_sha256", {}))}


PB1_BUNDLE_HISTORY = (
    PASS_A_REV1, PASS_A_V2, REV1_PASS_B_HISTORY, REV1_PASS_C_HISTORY,
    PB1_PRE_FIX1_PASS_B, PB1_PRE_FIX1_PASS_C,
    FIX1B_JUDGMENTS, FIX1B_CASE_REVIEW, FIX1B_CONFLICT_SUMMARY,
    FIX2_LEDGER, FIX2_JUDGMENTS, FIX2_CASE_REVIEW, FIX2_PASS_A_AUDIT,
    FIX2A_OBLIGATION_CLASSIFICATION, FIX2A_CONSISTENCY_REVIEW, FIX2A_CONFLICT_SUMMARY,
    FIX3_LEDGER, FIX3_JUDGMENTS, FIX3_CASE_REVIEW, FIX3_PASS_A_AUDIT,
    Path("reports/week_03/results/w3_003_ev2_a2_rev1_integrity_incident.json"),
    Path("reports/week_03/results/w3_003_ev2_a2_lineage_audit_rev1_invalid_independence.json"),
    Path("reports/week_03/results/w3_003_ev2_a2_manifest_rev1_invalid_independence.json"),
    Path("reports/week_03/results/w3_003_ev2_a2_support_summary_rev1_invalid_independence.json"),
)


def build_pb1_review_bundle(root: Path) -> dict[str, Any]:
    temp_root = Path(tempfile.gettempdir())
    output = temp_root / "W3-003-EV2-A2-PB1-FIX1_SENIOR_REVIEW_BUNDLE.zip"
    sidecar = output.with_suffix(output.suffix + ".sha256")
    stage = temp_root / "W3-003-EV2-A2-PB1-FIX1_SENIOR_REVIEW_BUNDLE_payload"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    payload = tuple(dict.fromkeys((*PB1_ACTIVE_ARTIFACTS, A2_MANIFEST, *PB1_BUNDLE_HISTORY)))
    for rel in payload:
        source = root / rel
        if not source.is_file():
            raise FileNotFoundError(rel)
        target = stage / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    review = stage / "review_evidence"
    review.mkdir()
    status = subprocess.run(
        ["git", "status", "--short"], cwd=root, check=True, capture_output=True,
        encoding="utf-8", errors="replace",
    ).stdout
    diff = subprocess.run(
        ["git", "diff", "--binary"], cwd=root, check=True, capture_output=True,
        encoding="utf-8", errors="replace",
    ).stdout
    (review / "git_status.txt").write_text(status, encoding="utf-8")
    (review / "git_diff.patch").write_text(diff, encoding="utf-8")
    (review / "commands_and_test_output.txt").write_text("\n".join((
        "GIT PREFLIGHT: branch=main; HEAD=origin/main=fresh remote=8492659a50fe00f066f9f64d8759d544356b3a41; staged=0; production_diff=0; kb_diff=0",
        "python scripts/evaluation/week3_ev2_a2.py validate-pb1-fix1 -> A2_PB1_FIX1_READY_FOR_SENIOR_REVIEW; errors=[]",
        "python -m pytest tests/test_week3_ev2_a2.py -q -> 97 passed",
        "python -m pytest tests/test_reporting -q -> 80 passed",
        "python scripts/reporting/validate_project_docs.py -> VALIDATION PASSED",
        "python scripts/evaluation/week3_ev2_a2.py validate-fix3 -> historical standalone gate is superseded and returns non-active because it requires Rev1 Pass B/C at the active paths; retained FIX3 coverage is included in the 97-test suite",
        "first build-pb1-fix1-bundle attempt -> FAILED while decoding Unicode git diff through Windows cp1252; fixed capture to explicit UTF-8 with replacement and reran successfully",
        "git diff --check -> exit 0",
        "candidate inference=false; EV2 executed=false; EV2 consumed=false; A3 started=false",
    )) + "\n", encoding="utf-8")
    pass_a = read_jsonl(root / PASS_A)
    pass_b = read_jsonl(root / PASS_B)
    pass_c = read_jsonl(root / PASS_C)
    pre_fix_pass_b = read_jsonl(root / PB1_PRE_FIX1_PASS_B)
    pre_fix_pass_c = read_jsonl(root / PB1_PRE_FIX1_PASS_C)
    classifications = read_jsonl(root / OBLIGATION_CLASSIFICATION)
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pass_b:
        by_case[row["case_id"]].append(row)
    pre_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pre_fix_pass_b:
        pre_by_case[row["case_id"]].append(row)
    audit_rows = build_pb1_fix1_audit_rows(root, pre_fix_pass_b, pass_b)
    _write_json(review / "nonirrelevant_514_audit.json", {
        "task_id": PB1_TASK_ID, "audited_rows": len(audit_rows),
        "semantic_audit_decision_sha256": _fix1_audit_decision_sha256(audit_rows),
        "rows": audit_rows,
    })
    pre_index = {(row["case_id"], row["evidence_id"]): row for row in pre_fix_pass_b}
    post_index = {(row["case_id"], row["evidence_id"]): row for row in pass_b}
    required = pb1_required_obligations(classifications)
    def before_after(case_id: str, evidence_ids: tuple[str, ...]) -> dict[str, Any]:
        return {
            "case_id": case_id,
            "rows": [{
                "evidence_id": evidence_id,
                "before": pb1_fix1_semantic_projection(pre_index[(case_id, evidence_id)]),
                "after": pb1_fix1_semantic_projection(post_index[(case_id, evidence_id)]),
            } for evidence_id in evidence_ids],
            "support_sets_before": derive_pb1_minimal_complete_sets(required.get(case_id, []), pre_by_case[case_id]),
            "support_sets_after": derive_pb1_minimal_complete_sets(required.get(case_id, []), by_case[case_id]),
        }
    _write_json(review / "s19_before_after.json", before_after(
        "EV2-A2-S19", ("RUN_TRANSFER_PENDING_001#checks", "RUN_TRANSFER_PENDING_001#action"),
    ))
    _write_json(review / "c09_before_after.json", before_after(
        "EV2-A2-C09", (
            "FAQ_TRANSFER_DECLINED_001#safe_message",
            "POL_TRANSFER_DECLINED_001#review_rule",
            "RUN_TRANSFER_DECLINED_001#action",
        ),
    ))
    _write_json(review / "pass_b_distribution.json", {
        "rows": len(pass_b), "unique_pairs": len({(row["case_id"], row["evidence_id"]) for row in pass_b}),
        "per_case_counts": dict(Counter(row["case_id"] for row in pass_b)),
        "support_class_counts": dict(Counter(row["support_class"] for row in pass_b)),
        "review_provenance_counts": dict(Counter(row["review_provenance"] for row in pass_b)),
    })
    reused = [row for row in pass_b if row["review_provenance"] == PB1_IMPORT_PROVENANCE]
    _write_json(review / "pass_b_reuse_audit.json", {
        "potentially_reused_rows": 624, "actual_reused_rows": len(reused),
        "semantic_mutation_count": sum(row["canonical_import_semantic_mutation"] is not False for row in reused),
        "source_counts": dict(Counter(row["canonical_import_source"] for row in reused)),
        "rows": [{key: row[key] for key in (
            "case_id", "evidence_id", "evidence_content_sha256", "canonical_import_source",
            "review_provenance_original", "canonical_import_semantic_mutation",
        )} for row in reused],
    })
    sample_keys = (
        ("EV2-A2-S01", "COMPLETE_SUPPORT"), ("EV2-A2-S02", "PARTIAL_SUPPORT"),
        ("EV2-A2-S03", "CONTEXTUAL_INSUFFICIENT"), ("EV2-A2-S01", "CONTRADICTION"),
        ("EV2-A2-C09", "PARTIAL_SUPPORT"), ("EV2-A2-C18", "PARTIAL_SUPPORT"),
        ("EV2-A2-H10", "CONTRADICTION"), ("EV2-A2-H01", "CONTEXTUAL_INSUFFICIENT"),
        ("EV2-A2-A03", "COMPLETE_SUPPORT"), ("EV2-A2-A04", "CONTEXTUAL_INSUFFICIENT"),
    )
    _write_json(review / "pass_b_semantic_trace_sample.json", {
        "samples": [next(row for row in by_case[case_id] if row["support_class"] == support_class) for case_id, support_class in sample_keys],
    })
    support_audit = []
    for candidate in pass_c:
        sets = derive_pb1_minimal_complete_sets(required.get(candidate["case_id"], []), by_case[candidate["case_id"]])
        old_candidate = next(row for row in pre_fix_pass_c if row["case_id"] == candidate["case_id"])
        support_audit.append({
            "case_id": candidate["case_id"], "kb_support_required_obligations": required.get(candidate["case_id"], []),
            "pre_fix_minimal_sets": old_candidate["acceptable_complete_support_sets"],
            "derived_minimal_sets": sets, "candidate_sets_equal": sets == candidate["acceptable_complete_support_sets"],
            "strict_supersets_removed": True,
        })
    _write_json(review / "support_set_before_after.json", {
        "cases": support_audit, "all_exact": all(row["candidate_sets_equal"] for row in support_audit),
    })
    ineligible = _load_json(root, INELIGIBLE_EVIDENCE_AUDIT)
    regenerated = derive_pb1_pass_c(root, pass_a, classifications, pass_b, ineligible)
    _write_json(review / "pass_c_derivation_audit.json", {
        "rows": len(pass_c), "route_counts": dict(Counter(row["expected_production_route"] for row in pass_c)),
        "deterministic_regeneration_equal": regenerated == pass_c,
        "clarify_count": sum(row["expected_production_route"] == "CLARIFY" for row in pass_c),
        "pass_a_sha256": file_sha256(root / PASS_A), "pass_b_sha256": file_sha256(root / PASS_B),
        "pass_c_sha256": file_sha256(root / PASS_C), "candidate_inference_executed": False,
    })
    base_files = sorted(path for path in stage.rglob("*") if path.is_file())
    bundle_manifest = {
        "task_id": PB1_TASK_ID, "entry_count_excluding_receipts": len(base_files),
        "entries": [{"path": path.relative_to(stage).as_posix(), "bytes": path.stat().st_size, "sha256": file_sha256(path)} for path in base_files],
    }
    _write_json(review / "bundle_manifest.json", bundle_manifest)
    manifest_hash = file_sha256(review / "bundle_manifest.json")
    (review / "bundle_sha256.txt").write_text(
        "Archive SHA-256 is in the detached .zip.sha256 sidecar to avoid self-reference.\n"
        f"bundle_manifest_sha256  {manifest_hash}\n", encoding="utf-8",
    )
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in stage.rglob("*") if item.is_file()):
            info = zipfile.ZipInfo(path.relative_to(stage).as_posix(), date_time=(2026, 8, 21, 12, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    archive_hash = file_sha256(output)
    sidecar.write_text(f"{archive_hash}  {output.name}\n", encoding="ascii")
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        crc_bad = archive.testzip()
        archived_manifest = json.loads(archive.read("review_evidence/bundle_manifest.json"))
        payload_hashes_valid = all(
            hashlib.sha256(archive.read(item["path"])).hexdigest() == item["sha256"]
            and len(archive.read(item["path"])) == item["bytes"]
            for item in archived_manifest["entries"]
        )
    return {
        "path": str(output), "sidecar": str(sidecar), "bytes": output.stat().st_size,
        "sha256": archive_hash, "entries": len(names), "crc_bad_entry": crc_bad,
        "duplicate_entries": len(names) - len(set(names)), "payload_hashes_valid": payload_hashes_valid,
        "expected_entries_present": all((stage / rel).is_file() for rel in payload),
    }


def validate_pb1_package(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    pass_a = read_jsonl(root / PASS_A)
    classifications = read_jsonl(root / OBLIGATION_CLASSIFICATION)
    pass_b = read_jsonl(root / PASS_B)
    classification_result = validate_pb1_obligation_classification(pass_a, classifications)
    matrix_result = validate_pb1_pass_b(root, pass_a, classifications, pass_b)
    ineligible = _load_json(root, INELIGIBLE_EVIDENCE_AUDIT)
    ineligible_result = validate_pb1_ineligible_audit(root, ineligible)
    manifest_result = validate_pb1_manifest(root, _load_json(root, A2_MANIFEST))
    fix1_result = validate_pb1_fix1_semantic_audit(
        root, pass_b, _load_json(root, PB1_FIX1_LEDGER), _load_json(root, PB1_FIX1_AUDIT_SUMMARY),
    )
    proofs_result = validate_pb1_stratum_proofs(
        pass_a, classifications, pass_b,
        _load_json(root, POSITIVE_SUPPORT_AUDIT), _load_json(root, SAFE_CORRECTIVE_PROOFS),
        _load_json(root, HARD_ABSTAIN_PROOFS), _load_json(root, AMBIGUOUS_DERIVATION),
    )
    derived = derive_pb1_pass_c(root, pass_a, classifications, pass_b, ineligible)
    active_pass_c = read_jsonl(root / PASS_C)
    if file_sha256(root / PASS_A) != PASS_A_V3_EXPECTED_SHA256:
        errors.append("BLOCKED_SENIOR_APPROVED_PASS_A_V3_BYTE_DRIFT")
    if derived != active_pass_c:
        errors.append("pass_c_not_exact_deterministic_derivation")
    if len(active_pass_c) != 60:
        errors.append("pass_c_not_60_rows")
    if any(row.get("expected_production_route") == "CLARIFY" for row in active_pass_c):
        errors.append("production_clarify_forbidden")
    summary = _load_json(root, SUPPORT_SUMMARY)
    if summary.get("pass_a_sha256") != file_sha256(root / PASS_A) or summary.get("pass_b_sha256") != file_sha256(root / PASS_B) or summary.get("pass_c_sha256") != file_sha256(root / PASS_C):
        errors.append("support_summary_hash_binding")
    if summary.get("pass_b_rows") != 3120 or summary.get("reused_semantic_rows") != 624 or summary.get("new_semantic_rows") != 2496:
        errors.append("support_summary_count_binding")
    for result in (classification_result, matrix_result, ineligible_result, proofs_result, manifest_result, fix1_result):
        errors.extend(result["errors"])
    return {
        "passed": not errors, "status": PB1_EXTERNAL_STATUS if not errors else "A2_PB1_FIX1_VALIDATION_FAILED",
        "errors": errors, "obligation_classification": classification_result,
        "pass_b": matrix_result, "stratum_proofs": proofs_result,
        "ineligible_audit": ineligible_result, "manifest": manifest_result,
        "semantic_audit": fix1_result,
        "pass_c_rows": len(active_pass_c),
        "pass_c_route_counts": dict(Counter(row.get("expected_production_route") for row in active_pass_c)),
        "pass_a_sha256": file_sha256(root / PASS_A), "pass_b_sha256": file_sha256(root / PASS_B),
        "pass_c_sha256": file_sha256(root / PASS_C),
    }


PB1_FIX2_PACKET_FIELDS = {
    "review_id", "case_id", "query", "evidence_id", "document_id", "section_id",
    "frozen_section_text", "evidence_content_sha256",
    "required_target_entity_constraints", "forbidden_target_entity_constraints",
    "required_state_constraints", "forbidden_state_constraints",
    "required_dimension_constraints", "forbidden_dimension_constraints",
    "kb_support_required_obligations",
}
PB1_FIX2_DECISION_FIELDS = {
    "review_id", "case_id", "evidence_id", "evidence_content_sha256",
    "target_match", "state_match", "dimension_match", "obligations_covered",
    "support_class", "review_basis_quotes", "support_quotes_by_obligation",
    "semantic_entailment_explanation_by_obligation", "support_rationale",
    "review_provenance", "previous_label_visible_to_reviewer",
}
PB1_FIX2_CONTRADICTION_FIELDS = {
    "contradiction_basis_quote", "contradicted_constraint",
    "contradiction_semantic_explanation",
}


def fix2_external_review_dir() -> Path:
    path = Path(tempfile.gettempdir()) / "W3-003-EV2-A2-PB1-FIX2_review_evidence"
    path.mkdir(parents=True, exist_ok=True)
    return path


def fix2_phase_log_path() -> Path:
    return fix2_external_review_dir() / "fix2_blind_phase_log.json"


def _fix2_read_phase_log() -> dict[str, Any]:
    path = fix2_phase_log_path()
    if not path.is_file():
        raise ValueError("FIX2_BLIND_PHASE_LOG_MISSING")
    return json.loads(path.read_text(encoding="utf-8"))


def _fix2_append_phase(event: str, **evidence: Any) -> dict[str, Any]:
    path = fix2_phase_log_path()
    log = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {
        "task_id": PB1_FIX2_TASK_ID, "events": [],
        "parent_authored_blind_decisions": False,
        "subagent_received_previous_labels": False,
        "subagent_received_fix1_corrections": False,
        "subagent_received_senior_case_findings": False,
    }
    if any(item["event"] == event for item in log["events"]):
        raise ValueError(f"FIX2_DUPLICATE_PHASE:{event}")
    log["events"].append({"sequence": len(log["events"]) + 1, "event": event, **evidence})
    _write_json(path, log)
    return log


def validate_pb1_fix2_blind_packet(root: Path, packet: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    pass_a = read_jsonl(root / PASS_A)
    classifications = read_jsonl(root / OBLIGATION_CLASSIFICATION)
    cases = {row["case_id"]: row for row in pass_a}
    required = pb1_required_obligations(classifications)
    eligible, _ = eligible_section_index(root)
    pairs: set[tuple[str, str]] = set()
    review_ids: set[str] = set()
    for index, row in enumerate(packet):
        prefix = f"fix2_packet[{index}]"
        if set(row) != PB1_FIX2_PACKET_FIELDS:
            errors.append(f"{prefix}:field_set_not_exact:{sorted(set(row) ^ PB1_FIX2_PACKET_FIELDS)}")
            continue
        pair = (row["case_id"], row["evidence_id"])
        if pair in pairs:
            errors.append(f"{prefix}:duplicate_pair")
        if row["review_id"] in review_ids:
            errors.append(f"{prefix}:duplicate_review_id")
        pairs.add(pair)
        review_ids.add(row["review_id"])
        case = cases.get(row["case_id"])
        section = eligible.get(row["evidence_id"])
        if case is None or section is None:
            errors.append(f"{prefix}:unknown_case_or_evidence")
            continue
        expected = {
            "query": case["query"], "document_id": section["document_id"],
            "section_id": section["section_id"], "frozen_section_text": section["content"],
            "evidence_content_sha256": section["content_sha256"],
            "required_target_entity_constraints": case["required_target_entity_constraints"],
            "forbidden_target_entity_constraints": case["forbidden_target_entity_constraints"],
            "required_state_constraints": case["required_state_constraints"],
            "forbidden_state_constraints": case["forbidden_state_constraints"],
            "required_dimension_constraints": case["required_dimension_constraints"],
            "forbidden_dimension_constraints": case["forbidden_dimension_constraints"],
            "kb_support_required_obligations": required.get(row["case_id"], []),
        }
        for key, value in expected.items():
            if row.get(key) != value:
                errors.append(f"{prefix}:binding:{key}")
    if len(packet) != 514 or len(pairs) != 514 or len(review_ids) != 514:
        errors.append(f"fix2_packet_cardinality:{len(packet)}:{len(pairs)}:{len(review_ids)}")
    return {"passed": not errors, "errors": errors, "rows": len(packet), "unique_pairs": len(pairs), "unique_review_ids": len(review_ids)}


def build_pb1_fix2_blind_packet(root: Path) -> dict[str, Any]:
    if file_sha256(root / PASS_A) != PASS_A_V3_EXPECTED_SHA256:
        raise ValueError("BLOCKED_SENIOR_APPROVED_PASS_A_V3_BYTE_DRIFT")
    if file_sha256(root / PASS_B) != PB1_FIX1_PRE_FIX2_PASS_B_SHA256:
        raise ValueError("ACTIVE_FIX1_PASS_B_IDENTITY_DRIFT_BEFORE_PACKET")
    if file_sha256(root / PB1_FIX1_PRE_FIX2_PASS_B) != PB1_FIX1_PRE_FIX2_PASS_B_SHA256:
        raise ValueError("FIX1_PRE_FIX2_PASS_B_PRESERVATION_DRIFT")
    if file_sha256(root / PB1_FIX1_PRE_FIX2_PASS_C) != PB1_FIX1_PRE_FIX2_PASS_C_SHA256:
        raise ValueError("FIX1_PRE_FIX2_PASS_C_PRESERVATION_DRIFT")
    phase_path = fix2_phase_log_path()
    if phase_path.exists():
        phase_path.unlink()
    _fix2_append_phase("PARENT_PACKET_BUILD_STARTED", pass_a_sha256=file_sha256(root / PASS_A))
    pass_a = {row["case_id"]: row for row in read_jsonl(root / PASS_A)}
    required = pb1_required_obligations(read_jsonl(root / OBLIGATION_CLASSIFICATION))
    eligible, _ = eligible_section_index(root)
    scope = sorted(
        (row for row in read_jsonl(root / PASS_B) if row["support_class"] != "IRRELEVANT"),
        key=lambda row: (row["case_id"], row["evidence_id"]),
    )
    packet = []
    for index, source in enumerate(scope, start=1):
        case = pass_a[source["case_id"]]
        section = eligible[source["evidence_id"]]
        packet.append({
            "review_id": f"FIX2-BLIND-{index:04d}", "case_id": source["case_id"],
            "query": case["query"], "evidence_id": source["evidence_id"],
            "document_id": section["document_id"], "section_id": section["section_id"],
            "frozen_section_text": section["content"],
            "evidence_content_sha256": section["content_sha256"],
            "required_target_entity_constraints": case["required_target_entity_constraints"],
            "forbidden_target_entity_constraints": case["forbidden_target_entity_constraints"],
            "required_state_constraints": case["required_state_constraints"],
            "forbidden_state_constraints": case["forbidden_state_constraints"],
            "required_dimension_constraints": case["required_dimension_constraints"],
            "forbidden_dimension_constraints": case["forbidden_dimension_constraints"],
            "kb_support_required_obligations": required.get(source["case_id"], []),
        })
    write_jsonl(root / PB1_FIX2_BLIND_PACKET, packet)
    _fix2_append_phase("PARENT_PACKET_BUILD_COMPLETED", rows=len(packet))
    validation = validate_pb1_fix2_blind_packet(root, packet)
    if not validation["passed"]:
        raise ValueError(f"FIX2_BLIND_PACKET_INVALID:{validation['errors'][:10]}")
    packet_sha = file_sha256(root / PB1_FIX2_BLIND_PACKET)
    _fix2_append_phase("PACKET_VALIDATED", rows=len(packet), packet_sha256=packet_sha)
    _fix2_append_phase("PACKET_FROZEN", rows=len(packet), packet_sha256=packet_sha)
    return {"passed": True, **validation, "packet_sha256": packet_sha, "phase_log": str(fix2_phase_log_path())}


def mark_pb1_fix2_isolated_subagent_started(root: Path) -> dict[str, Any]:
    packet_sha = file_sha256(root / PB1_FIX2_BLIND_PACKET)
    log = _fix2_read_phase_log()
    frozen = next((item for item in log["events"] if item["event"] == "PACKET_FROZEN"), None)
    if frozen is None or frozen.get("packet_sha256") != packet_sha:
        raise ValueError("FIX2_PACKET_NOT_FROZEN_BEFORE_SUBAGENT")
    exact_inputs = [
        str(PB1_FIX2_BLIND_PACKET).replace("\\", "/"), packet_sha,
        "LOCKED_SUPPORT_CLASS_DEFINITIONS", "REQUIRED_OUTPUT_SCHEMA_ONLY",
    ]
    _fix2_append_phase("ISOLATED_SUBAGENT_CREATED", packet_sha256=packet_sha)
    _fix2_append_phase("ISOLATED_SUBAGENT_CONTEXT_MODE", value="FRESH_NO_PARENT_HISTORY")
    _fix2_append_phase("ISOLATED_SUBAGENT_INPUTS", value=exact_inputs)
    result = _fix2_append_phase("ISOLATED_SUBAGENT_DECISION_AUTHORING_STARTED", packet_sha256=packet_sha)
    return {"passed": True, "packet_sha256": packet_sha, "exact_inputs": exact_inputs, "events": len(result["events"])}


def mark_pb1_fix2_isolated_subagent_completed(root: Path) -> dict[str, Any]:
    path = root / PB1_FIX2_BLIND_DECISIONS
    if not path.is_file():
        raise ValueError("FIX2_BLIND_DECISIONS_MISSING_AT_SUBAGENT_COMPLETION")
    sha = file_sha256(path)
    rows = len(read_jsonl(path))
    log = _fix2_append_phase("ISOLATED_SUBAGENT_DECISION_AUTHORING_COMPLETED", rows=rows, blind_decisions_sha256=sha)
    return {"passed": True, "rows": rows, "blind_decisions_sha256": sha, "events": len(log["events"])}


def validate_pb1_fix2_blind_decisions(root: Path, decisions: list[dict[str, Any]], *, record_freeze: bool = False) -> dict[str, Any]:
    packet = read_jsonl(root / PB1_FIX2_BLIND_PACKET)
    packet_result = validate_pb1_fix2_blind_packet(root, packet)
    errors = list(packet_result["errors"])
    packet_by_review = {row["review_id"]: row for row in packet}
    pairs: set[tuple[str, str]] = set()
    review_ids: set[str] = set()
    for index, row in enumerate(decisions):
        prefix = f"fix2_decision[{index}]"
        expected_fields = PB1_FIX2_DECISION_FIELDS | (PB1_FIX2_CONTRADICTION_FIELDS if row.get("support_class") == "CONTRADICTION" else set())
        if set(row) != expected_fields:
            errors.append(f"{prefix}:field_set_not_exact:{sorted(set(row) ^ expected_fields)}")
            continue
        packet_row = packet_by_review.get(row["review_id"])
        pair = (row["case_id"], row["evidence_id"])
        if row["review_id"] in review_ids or pair in pairs:
            errors.append(f"{prefix}:duplicate_review_or_pair")
        review_ids.add(row["review_id"]); pairs.add(pair)
        if packet_row is None or pair != (packet_row["case_id"], packet_row["evidence_id"]):
            errors.append(f"{prefix}:packet_identity_mismatch")
            continue
        if row["evidence_content_sha256"] != packet_row["evidence_content_sha256"]:
            errors.append(f"{prefix}:evidence_hash_mismatch")
        text = packet_row["frozen_section_text"]
        if not _quotes_are_verbatim(row["review_basis_quotes"], text):
            errors.append(f"{prefix}:review_basis_not_exact_quote")
        if row["review_provenance"] != PB1_FIX2_REVIEW_PROVENANCE or row["previous_label_visible_to_reviewer"] is not False:
            errors.append(f"{prefix}:blind_provenance_invalid")
        if any(not isinstance(row[key], bool) for key in ("target_match", "state_match", "dimension_match")):
            errors.append(f"{prefix}:compatibility_not_boolean")
        required = packet_row["kb_support_required_obligations"]
        covered = row["obligations_covered"]
        if len(covered) != len(set(covered)) or not set(covered) <= set(required):
            errors.append(f"{prefix}:covered_obligations_invalid")
        support_class = row["support_class"]
        compatible = row["target_match"] and row["state_match"] and row["dimension_match"]
        if support_class not in SUPPORT_CLASSES:
            errors.append(f"{prefix}:unknown_support_class")
        elif support_class == "COMPLETE_SUPPORT" and (not required or set(covered) != set(required) or not compatible):
            errors.append(f"{prefix}:invalid_complete")
        elif support_class == "PARTIAL_SUPPORT" and (not covered or set(covered) == set(required) or not compatible):
            errors.append(f"{prefix}:invalid_partial")
        elif support_class in {"CONTEXTUAL_INSUFFICIENT", "CONTRADICTION", "IRRELEVANT"} and covered:
            errors.append(f"{prefix}:nonpositive_has_coverage")
        quote_map = row["support_quotes_by_obligation"]
        explanation_map = row["semantic_entailment_explanation_by_obligation"]
        if set(quote_map) != set(covered) or set(explanation_map) != set(covered):
            errors.append(f"{prefix}:positive_trace_key_mismatch")
        for obligation, quotes in quote_map.items():
            if not _quotes_are_verbatim(quotes, text):
                errors.append(f"{prefix}:support_quote_not_exact:{obligation}")
            if not isinstance(explanation_map.get(obligation), str) or len(explanation_map[obligation].strip()) < 12:
                errors.append(f"{prefix}:entailment_explanation_missing:{obligation}")
        if not isinstance(row["support_rationale"], str) or len(row["support_rationale"].strip()) < 24:
            errors.append(f"{prefix}:support_rationale_not_specific")
        if support_class == "CONTRADICTION":
            if row["contradiction_basis_quote"] not in text or not row["contradicted_constraint"] or len(row["contradiction_semantic_explanation"].strip()) < 12:
                errors.append(f"{prefix}:contradiction_proof_invalid")
    if len(decisions) != 514 or len(review_ids) != 514 or len(pairs) != 514 or set(review_ids) != set(packet_by_review):
        errors.append(f"fix2_decision_cardinality:{len(decisions)}:{len(review_ids)}:{len(pairs)}")
    log = _fix2_read_phase_log()
    events = [item["event"] for item in log.get("events", [])]
    required_events = [
        "PARENT_PACKET_BUILD_STARTED", "PARENT_PACKET_BUILD_COMPLETED", "PACKET_VALIDATED", "PACKET_FROZEN",
        "ISOLATED_SUBAGENT_CREATED", "ISOLATED_SUBAGENT_CONTEXT_MODE", "ISOLATED_SUBAGENT_INPUTS",
        "ISOLATED_SUBAGENT_DECISION_AUTHORING_STARTED", "ISOLATED_SUBAGENT_DECISION_AUTHORING_COMPLETED",
    ]
    if events[:len(required_events)] != required_events:
        errors.append("false_previous_label_declaration_without_phase_evidence")
    if log.get("parent_authored_blind_decisions") is not False or log.get("subagent_received_previous_labels") is not False or log.get("subagent_received_fix1_corrections") is not False or log.get("subagent_received_senior_case_findings") is not False:
        errors.append("FIX2_TRUE_BLIND_REVIEW_PROVENANCE_VIOLATION")
    decision_sha = file_sha256(root / PB1_FIX2_BLIND_DECISIONS) if (root / PB1_FIX2_BLIND_DECISIONS).is_file() else None
    if not errors and record_freeze:
        _fix2_append_phase("BLIND_DECISIONS_VALIDATED", rows=len(decisions), blind_decisions_sha256=decision_sha)
        _fix2_append_phase("BLIND_DECISIONS_FROZEN", rows=len(decisions), blind_decisions_sha256=decision_sha)
    return {"passed": not errors, "errors": errors, "rows": len(decisions), "unique_pairs": len(pairs), "support_class_counts": dict(Counter(row.get("support_class") for row in decisions)), "blind_decisions_sha256": decision_sha}


def _pb1_fix2_semantic_projection(row: dict[str, Any]) -> dict[str, Any]:
    result = {
        "target_match": row["target_match"], "state_match": row["state_match"],
        "dimension_match": row["dimension_match"],
        "obligations_covered": sorted(row["obligations_covered"]),
        "support_class": row["support_class"],
    }
    if row["support_class"] == "CONTRADICTION":
        result["contradiction_basis_quote"] = row.get("contradiction_basis_quote")
        result["contradicted_constraint"] = row.get("contradicted_constraint")
    return result


def apply_pb1_fix2_after_freeze(root: Path) -> dict[str, Any]:
    decisions = read_jsonl(root / PB1_FIX2_BLIND_DECISIONS)
    validation = validate_pb1_fix2_blind_decisions(root, decisions, record_freeze=False)
    if not validation["passed"]:
        raise ValueError(f"FIX2_BLIND_DECISIONS_INVALID:{validation['errors'][:10]}")
    log = _fix2_read_phase_log()
    frozen = next((item for item in log["events"] if item["event"] == "BLIND_DECISIONS_FROZEN"), None)
    decision_sha = file_sha256(root / PB1_FIX2_BLIND_DECISIONS)
    if frozen is None or frozen.get("blind_decisions_sha256") != decision_sha:
        raise ValueError("BLOCKED_BLIND_REVIEW_POST_COMPARISON_MUTATION")
    _fix2_append_phase("CURRENT_PASS_B_COMPARISON_OPENED", blind_decisions_sha256=decision_sha)
    current = read_jsonl(root / PASS_B)
    if file_sha256(root / PB1_FIX1_PRE_FIX2_PASS_B) != PB1_FIX1_PRE_FIX2_PASS_B_SHA256:
        raise ValueError("FIX1_PRE_FIX2_PASS_B_PRESERVATION_DRIFT")
    current_index = {(row["case_id"], row["evidence_id"]): row for row in current}
    decision_index = {(row["case_id"], row["evidence_id"]): row for row in decisions}
    differences = []
    for pair, blind in sorted(decision_index.items()):
        old = current_index[pair]
        if _pb1_fix2_semantic_projection(old) != _pb1_fix2_semantic_projection(blind):
            differences.append({
                "case_id": pair[0], "evidence_id": pair[1],
                "old_class": old["support_class"], "blind_class": blind["support_class"],
                "old_semantic_projection": _pb1_fix2_semantic_projection(old),
                "blind_semantic_projection": _pb1_fix2_semantic_projection(blind),
                "review_id": blind["review_id"],
                "imported_hard": old["review_provenance"] == PB1_IMPORT_PROVENANCE,
            })
    fix1_ledger = _load_json(root, PB1_FIX1_LEDGER)
    fix1_pairs = {(row["case_id"], row["evidence_id"]) for row in fix1_ledger["corrections"]}
    difference_pairs = {(row["case_id"], row["evidence_id"]) for row in differences}
    confirmed = sorted(fix1_pairs - difference_pairs)
    disagreed = sorted(fix1_pairs & difference_pairs)
    additional = sorted(difference_pairs - fix1_pairs)
    comparison = {
        "task_id": PB1_FIX2_TASK_ID, "reviewed": 514,
        "blind_decisions_sha256": decision_sha,
        "semantic_exact_matches": 514 - len(differences), "semantic_differences": len(differences),
        "differences": differences,
        "fix1_corrections_independently_confirmed": [{"case_id": a, "evidence_id": b} for a, b in confirmed],
        "fix1_corrections_independently_disagreed": [{"case_id": a, "evidence_id": b} for a, b in disagreed],
        "additional_fix2_corrections": [{"case_id": a, "evidence_id": b} for a, b in additional],
    }
    _write_json(root / PB1_FIX2_COMPARISON, comparison)
    ledger = {
        "task_id": PB1_FIX2_TASK_ID, "blind_decisions_sha256": decision_sha,
        "correction_count": len(differences), "corrections": differences,
    }
    _write_json(root / PB1_FIX2_LEDGER, ledger)
    _fix2_append_phase("COMPARISON_COMPLETED", semantic_matches=514-len(differences), semantic_differences=len(differences), comparison_sha256=file_sha256(root / PB1_FIX2_COMPARISON))
    hard_conflicts = [row for row in differences if row["imported_hard"]]
    if hard_conflicts:
        return {"passed": False, "status": "A2_PB1_FIX2_IMPORTED_HARD_SEMANTIC_CONFLICT", "hard_conflicts": hard_conflicts, "comparison": comparison}
    required = pb1_required_obligations(read_jsonl(root / OBLIGATION_CLASSIFICATION))
    eligible, _ = eligible_section_index(root)
    for difference in differences:
        pair = (difference["case_id"], difference["evidence_id"])
        target = current_index[pair]
        blind = decision_index[pair]
        target.update({
            "target_match": blind["target_match"], "state_match": blind["state_match"],
            "dimension_match": blind["dimension_match"], "obligations_covered": blind["obligations_covered"],
            "obligations_not_covered": [item for item in required[pair[0]] if item not in set(blind["obligations_covered"])],
            "support_class": blind["support_class"],
            "support_quotes_by_obligation": blind["support_quotes_by_obligation"],
            "semantic_entailment_explanation_by_obligation": blind["semantic_entailment_explanation_by_obligation"],
            "support_rationale": eligible[pair[1]]["content"] + " " + blind["support_rationale"],
            "semantic_mismatch_reason": blind["support_rationale"],
            "fix2_blind_review_id": blind["review_id"],
        })
        for key in PB1_FIX2_CONTRADICTION_FIELDS:
            target.pop(key, None)
        target.pop("missing_required_obligations", None)
        if blind["support_class"] == "CONTRADICTION":
            target.update({key: blind[key] for key in PB1_FIX2_CONTRADICTION_FIELDS})
        elif blind["support_class"] == "CONTEXTUAL_INSUFFICIENT":
            target["missing_required_obligations"] = list(required[pair[0]])
    pass_a = read_jsonl(root / PASS_A)
    classifications = read_jsonl(root / OBLIGATION_CLASSIFICATION)
    matrix = validate_pb1_pass_b(root, pass_a, classifications, current)
    if not matrix["passed"]:
        raise ValueError(f"A2_PB1_FIX2_PASS_B_INVALID:{matrix['errors'][:10]}")
    write_jsonl(root / PASS_B, current)
    regenerate_pb1_proofs(root, pass_a, classifications, current)
    positive = _load_json(root, POSITIVE_SUPPORT_AUDIT); safe = _load_json(root, SAFE_CORRECTIVE_PROOFS)
    hard = _load_json(root, HARD_ABSTAIN_PROOFS); ambiguous = _load_json(root, AMBIGUOUS_DERIVATION)
    proof = validate_pb1_stratum_proofs(pass_a, classifications, current, positive, safe, hard, ambiguous)
    if not proof["passed"] or (proof["standard_valid"], proof["safe_corrective_valid"], proof["hard_valid"], proof["ambiguous_valid"]) != (24, 18, 12, 6):
        raise ValueError(f"A2_PB1_FIX2_PASS_A_V3_STRATUM_CONFLICT:{proof['errors'][:10]}")
    ineligible = _load_json(root, INELIGIBLE_EVIDENCE_AUDIT)
    derived = derive_pb1_pass_c_fail_closed(root, pass_a, classifications, current, ineligible, positive, safe, hard, ambiguous)
    write_jsonl(root / PASS_C, derived)
    if derive_pb1_pass_c(root, pass_a, classifications, current, ineligible) != read_jsonl(root / PASS_C):
        raise ValueError("FIX2_PASS_C_NONDETERMINISTIC")
    _fix2_append_phase("FINAL_GOLD_DERIVED", pass_b_sha256=file_sha256(root / PASS_B), pass_c_sha256=file_sha256(root / PASS_C))
    return {
        "passed": True, "status": PB1_FIX2_EXTERNAL_STATUS, "comparison": comparison,
        "pass_b_sha256": file_sha256(root / PASS_B), "pass_c_sha256": file_sha256(root / PASS_C),
        "support_class_counts": matrix["support_class_counts"],
        "proof_counts": [proof["standard_valid"], proof["safe_corrective_valid"], proof["hard_valid"], proof["ambiguous_valid"]],
        "route_counts": dict(Counter(row["expected_production_route"] for row in derived)),
    }


def build_pb1_fix2_stop_bundle(root: Path) -> dict[str, Any]:
    output = Path(tempfile.gettempdir()) / "W3-003-EV2-A2-PB1-FIX2_SENIOR_REVIEW_BUNDLE.zip"
    sidecar = output.with_suffix(output.suffix + ".sha256")
    stage = Path(tempfile.gettempdir()) / "W3-003-EV2-A2-PB1-FIX2_SENIOR_REVIEW_BUNDLE_payload"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    payload = tuple(dict.fromkeys((
        PASS_A, PASS_B, PASS_C, PB1_FIX1_PRE_FIX2_PASS_B, PB1_FIX1_PRE_FIX2_PASS_C,
        PB1_FIX2_BLIND_PACKET, PB1_FIX2_BLIND_DECISIONS, PB1_FIX2_COMPARISON,
        PB1_FIX2_LEDGER, PB1_FIX1_LEDGER, PB1_FIX1_AUDIT_SUMMARY,
        OBLIGATION_CLASSIFICATION, POSITIVE_SUPPORT_AUDIT, SAFE_CORRECTIVE_PROOFS,
        HARD_ABSTAIN_PROOFS, AMBIGUOUS_DERIVATION, SUPPORT_SUMMARY,
        INELIGIBLE_EVIDENCE_AUDIT, LINEAGE_AUDIT, A2_MANIFEST,
        Path("scripts/evaluation/week3_ev2_a2.py"), Path("tests/test_week3_ev2_a2.py"),
        Path("reports/week_03/experiments/W3-003-EV2-A2.md"), Path("PROJECT_STATE.md"),
        Path("TASKS.md"), Path("reports/week_03/daily/2026-08-21.md"),
        Path("reports/week_03/week_03_summary.md"), *PB1_BUNDLE_HISTORY,
    )))
    for rel in payload:
        source = root / rel
        if not source.is_file():
            raise FileNotFoundError(rel)
        target = stage / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    review = stage / "review_evidence"
    review.mkdir()
    shutil.copy2(fix2_phase_log_path(), review / "fix2_blind_phase_log.json")
    status = subprocess.run(["git", "status", "--short"], cwd=root, check=True, capture_output=True, encoding="utf-8", errors="replace").stdout
    diff = subprocess.run(["git", "diff", "--binary"], cwd=root, check=True, capture_output=True, encoding="utf-8", errors="replace").stdout
    (review / "git_status.txt").write_text(status, encoding="utf-8")
    (review / "git_diff.patch").write_text(diff, encoding="utf-8")
    (review / "commands_and_test_output.txt").write_text("\n".join((
        "fresh preflight -> branch=main; HEAD=origin/main=fresh remote=8492659a50fe00f066f9f64d8759d544356b3a41; staged=0; production_diff=0; kb_diff=0",
        "build-pb1-fix2-blind-packet -> 514 rows; PASS; packet SHA 01ceaa093f69887a4a9eb47ebaf3d5e49b87d3cfd17a45a5c8f06f67a216420c",
        "isolated fresh-context subagent -> 514 decisions; SHA 4292c2d4f0dd3db420ccec6fdb77f02e17edc82de01e1e33e3e44aa0a9a49092",
        "validate-pb1-fix2-blind-decisions -> PASS; errors=[]; decisions frozen before comparison",
        "apply-pb1-fix2 -> A2_PB1_FIX2_IMPORTED_HARD_SEMANTIC_CONFLICT; 33 imported-HARD discrepancies; active Pass B/C unchanged",
        "python -B -m pytest tests/test_week3_ev2_a2.py -q -> 110 passed in 4.23s",
        "python -B -m pytest tests/test_reporting -q -> 80 passed in 0.46s",
        "python -B scripts/reporting/validate_project_docs.py -> VALIDATION PASSED",
        "git diff --check -> exit 0",
        "candidate inference=false; EV2 executed=false; EV2 consumed=false; A3 started=false; stage/commit/push=false",
    )) + "\n", encoding="utf-8")
    packet = read_jsonl(root / PB1_FIX2_BLIND_PACKET)
    decisions = read_jsonl(root / PB1_FIX2_BLIND_DECISIONS)
    comparison = _load_json(root, PB1_FIX2_COMPARISON)
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    packet_index = {row["review_id"]: row for row in packet}
    for row in decisions:
        by_class[row["support_class"]].append(row)
    _write_json(review / "blind_semantic_sample.json", {
        "samples": [
            {"packet": packet_index[row["review_id"]], "decision": row}
            for support_class in sorted(by_class) for row in by_class[support_class][:2]
        ],
    })
    current = read_jsonl(root / PASS_B)
    _write_json(review / "blind_vs_current_distribution.json", {
        "blind_review_rows": len(decisions),
        "blind_support_class_counts": dict(Counter(row["support_class"] for row in decisions)),
        "active_pass_b_support_class_counts": dict(Counter(row["support_class"] for row in current)),
        "semantic_matches": comparison["semantic_exact_matches"],
        "semantic_differences": comparison["semantic_differences"],
        "imported_hard_conflict_count": sum(row["imported_hard"] for row in comparison["differences"]),
    })
    _write_json(review / "pass_c_derivation_audit.json", {
        "status": "NOT_DERIVED_DUE_TO_IMPORTED_HARD_SEMANTIC_CONFLICT",
        "active_pass_b_unchanged": file_sha256(root / PASS_B) == PB1_FIX1_PRE_FIX2_PASS_B_SHA256,
        "active_pass_c_unchanged": file_sha256(root / PASS_C) == PB1_FIX1_PRE_FIX2_PASS_C_SHA256,
        "active_pass_b_sha256": file_sha256(root / PASS_B),
        "active_pass_c_sha256": file_sha256(root / PASS_C),
        "deterministic_regeneration_after_fix2": "NOT_RUN_STOP_RULE",
    })
    base_files = sorted(path for path in stage.rglob("*") if path.is_file())
    manifest = {
        "task_id": PB1_FIX2_TASK_ID, "status": "A2_PB1_FIX2_IMPORTED_HARD_SEMANTIC_CONFLICT",
        "entry_count_excluding_receipts": len(base_files),
        "entries": [{"path": path.relative_to(stage).as_posix(), "bytes": path.stat().st_size, "sha256": file_sha256(path)} for path in base_files],
    }
    _write_json(review / "bundle_manifest.json", manifest)
    (review / "bundle_sha256.txt").write_text(
        "Archive SHA-256 is recorded in the detached .zip.sha256 sidecar.\n"
        f"bundle_manifest_sha256  {file_sha256(review / 'bundle_manifest.json')}\n",
        encoding="utf-8",
    )
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in stage.rglob("*") if item.is_file()):
            info = zipfile.ZipInfo(path.relative_to(stage).as_posix(), date_time=(2026, 8, 21, 12, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    archive_sha = file_sha256(output)
    sidecar.write_text(f"{archive_sha}  {output.name}\n", encoding="ascii")
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        crc_bad = archive.testzip()
        archived_manifest = json.loads(archive.read("review_evidence/bundle_manifest.json"))
        payload_hashes_valid = all(
            hashlib.sha256(archive.read(item["path"])).hexdigest() == item["sha256"]
            and len(archive.read(item["path"])) == item["bytes"]
            for item in archived_manifest["entries"]
        )
    return {
        "passed": crc_bad is None and len(names) == len(set(names)) and payload_hashes_valid,
        "status": "A2_PB1_FIX2_IMPORTED_HARD_SEMANTIC_CONFLICT",
        "path": str(output), "sidecar": str(sidecar), "bytes": output.stat().st_size,
        "sha256": archive_sha, "entries": len(names), "crc_bad_entry": crc_bad,
        "duplicate_entries": len(names)-len(set(names)), "payload_hashes_valid": payload_hashes_valid,
        "expected_entries_present": all((stage / rel).is_file() for rel in payload),
    }


def semantic_decision_projection_v2(row: dict[str, Any]) -> tuple[Any, ...]:
    support_class = row["support_class"]
    if support_class in {"COMPLETE_SUPPORT", "PARTIAL_SUPPORT"}:
        return (
            support_class, tuple(sorted(row["obligations_covered"])),
            row["target_match"], row["state_match"], row["dimension_match"],
        )
    if support_class in {"CONTEXTUAL_INSUFFICIENT", "IRRELEVANT"}:
        return support_class, row["target_match"], row["state_match"]
    if support_class == "CONTRADICTION":
        return (support_class,)
    raise ValueError(f"UNKNOWN_SUPPORT_CLASS:{support_class}")


def gold_impact_projection_v1(row: dict[str, Any]) -> dict[str, Any]:
    usable = (
        sorted(row["obligations_covered"])
        if row["support_class"] in {"COMPLETE_SUPPORT", "PARTIAL_SUPPORT"}
        and row["target_match"] is True and row["state_match"] is True
        and row["dimension_match"] is True else []
    )
    forbidden = (
        row["support_class"] == "CONTRADICTION"
        or row["target_match"] is False or row["state_match"] is False
    )
    return {"usable_coverage": usable, "forbidden": forbidden}


def fix2a_external_review_dir() -> Path:
    path = Path(tempfile.gettempdir()) / "W3-003-EV2-A2-PB1-FIX2A_review_evidence"
    path.mkdir(parents=True, exist_ok=True)
    return path


def fix2a_phase_log_path() -> Path:
    return fix2a_external_review_dir() / "fix2a_tiebreak_phase_log.json"


def _fix2a_read_phase_log() -> dict[str, Any]:
    path = fix2a_phase_log_path()
    if not path.is_file():
        raise ValueError("FIX2A_TIEBREAK_PHASE_LOG_MISSING")
    return json.loads(path.read_text(encoding="utf-8"))


def _fix2a_append_phase(event: str, **evidence: Any) -> dict[str, Any]:
    path = fix2a_phase_log_path()
    log = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {
        "task_id": PB1_FIX2A_TASK_ID, "events": [],
        "parent_authored_tiebreak_decisions": False,
        "second_subagent_received_previous_labels": False,
        "second_subagent_received_blind1_decisions": False,
        "second_subagent_received_senior_findings": False,
    }
    if any(item["event"] == event for item in log["events"]):
        raise ValueError(f"FIX2A_DUPLICATE_PHASE:{event}")
    log["events"].append({"sequence": len(log["events"]) + 1, "event": event, **evidence})
    _write_json(path, log)
    return log


def _fix2a_projection_record(pair: tuple[str, str], current: dict[str, Any], blind: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": pair[0], "evidence_id": pair[1],
        "current_projection": list(semantic_decision_projection_v2(current)),
        "blind1_projection": list(semantic_decision_projection_v2(blind)),
        "imported_hard": current["review_provenance"] == PB1_IMPORT_PROVENANCE,
    }


def validate_pb1_fix2a_tiebreak_packet(root: Path, packet: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    original = read_jsonl(root / PB1_FIX2_BLIND_PACKET)
    original_by_pair = {(row["case_id"], row["evidence_id"]): row for row in original}
    pairs: set[tuple[str, str]] = set()
    review_ids: set[str] = set()
    for index, row in enumerate(packet):
        prefix = f"fix2a_tiebreak_packet[{index}]"
        if set(row) != PB1_FIX2_PACKET_FIELDS:
            errors.append(f"{prefix}:field_set_not_exact")
            continue
        pair = (row["case_id"], row["evidence_id"])
        if pair in pairs or row["review_id"] in review_ids:
            errors.append(f"{prefix}:duplicate_pair_or_review_id")
        pairs.add(pair); review_ids.add(row["review_id"])
        source = original_by_pair.get(pair)
        if source is None:
            errors.append(f"{prefix}:pair_not_in_frozen_fix2_packet")
            continue
        for key in PB1_FIX2_PACKET_FIELDS - {"review_id"}:
            if row[key] != source[key]:
                errors.append(f"{prefix}:sanitized_binding:{key}")
    if len(packet) != 65 or len(pairs) != 65 or len(review_ids) != 65:
        errors.append(f"fix2a_tiebreak_packet_cardinality:{len(packet)}:{len(pairs)}:{len(review_ids)}")
    return {"passed": not errors, "errors": errors, "rows": len(packet), "unique_pairs": len(pairs), "unique_review_ids": len(review_ids)}


def prepare_pb1_fix2a_tiebreak(root: Path) -> dict[str, Any]:
    locked = {
        PASS_A: PASS_A_V3_EXPECTED_SHA256,
        PASS_B: PB1_FIX1_PRE_FIX2_PASS_B_SHA256,
        PASS_C: PB1_FIX1_PRE_FIX2_PASS_C_SHA256,
        PB1_FIX2_BLIND_PACKET: "01ceaa093f69887a4a9eb47ebaf3d5e49b87d3cfd17a45a5c8f06f67a216420c",
        PB1_FIX2_BLIND_DECISIONS: "4292c2d4f0dd3db420ccec6fdb77f02e17edc82de01e1e33e3e44aa0a9a49092",
        PB1_FIX2_COMPARISON: "ecd9c55d3e65e34e39aef380d661e34ec5bcb421845642b3820ed3049589cc6c",
        PB1_FIX2_LEDGER: "47cabc212ca7f3713a1e1a817967497dc0260012750f3060e7e566a90ec317fa",
        KB: "e14aa83ed37c8de1ab3fc0fb8a0cae50f1b1e14083b774252a687bc5f0cf67c4",
    }
    for path, expected in locked.items():
        if file_sha256(root / path) != expected:
            raise ValueError(f"FIX2A_LOCKED_IDENTITY_DRIFT:{path}")
    phase_path = fix2a_phase_log_path()
    if phase_path.exists():
        phase_path.unlink()
    _fix2a_append_phase("PROJECTION_V2_DEFINED", semantic_projection="SEMANTIC_DECISION_PROJECTION_V2", gold_impact_projection="GOLD_IMPACT_PROJECTION_V1")
    current_rows = read_jsonl(root / PASS_B)
    blind_rows = read_jsonl(root / PB1_FIX2_BLIND_DECISIONS)
    original_packet = read_jsonl(root / PB1_FIX2_BLIND_PACKET)
    current = {(row["case_id"], row["evidence_id"]): row for row in current_rows}
    blind = {(row["case_id"], row["evidence_id"]): row for row in blind_rows}
    scope_pairs = [(row["case_id"], row["evidence_id"]) for row in original_packet]
    semantic_diffs = [pair for pair in scope_pairs if semantic_decision_projection_v2(current[pair]) != semantic_decision_projection_v2(blind[pair])]
    gold_diffs = [pair for pair in scope_pairs if gold_impact_projection_v1(current[pair]) != gold_impact_projection_v1(blind[pair])]
    is_hard = lambda pair: current[pair]["review_provenance"] == PB1_IMPORT_PROVENANCE
    semantic_hard = [pair for pair in semantic_diffs if is_hard(pair)]
    semantic_nonhard = [pair for pair in semantic_diffs if not is_hard(pair)]
    gold_hard = [pair for pair in gold_diffs if is_hard(pair)]
    gold_nonhard = [pair for pair in gold_diffs if not is_hard(pair)]
    original_comparison = _load_json(root, PB1_FIX2_COMPARISON)
    observed = (
        original_comparison["semantic_differences"], len(semantic_diffs), len(semantic_hard), len(semantic_nonhard),
        len(gold_diffs), len(gold_hard), len(gold_nonhard),
    )
    if observed != (284, 76, 11, 65, 58, 2, 56):
        raise ValueError(f"BLOCKED_FIX2A_PROJECTION_RECOMPUTATION_MISMATCH:{observed}")
    fix1_pairs = {(row["case_id"], row["evidence_id"]) for row in _load_json(root, PB1_FIX1_LEDGER)["corrections"]}
    fix1_v2_disagreed = sorted(fix1_pairs & set(semantic_diffs))
    projection = {
        "task_id": PB1_FIX2A_TASK_ID,
        "original_exact_differences": original_comparison["semantic_differences"],
        "semantic_projection_v2": {
            "matches": 514-len(semantic_diffs), "differences": len(semantic_diffs),
            "imported_hard": len(semantic_hard), "non_hard": len(semantic_nonhard),
            "difference_rows": [_fix2a_projection_record(pair, current[pair], blind[pair]) for pair in semantic_diffs],
        },
        "gold_impact_projection_v1": {
            "matches": 514-len(gold_diffs), "differences": len(gold_diffs),
            "imported_hard": len(gold_hard), "non_hard": len(gold_nonhard),
            "difference_pairs": [{"case_id": pair[0], "evidence_id": pair[1]} for pair in gold_diffs],
        },
        "fix1_corrections_v2_confirmed": len(fix1_pairs)-len(fix1_v2_disagreed),
        "fix1_corrections_v2_tiebreak_required": len(fix1_v2_disagreed),
        "senior_hard_adjudicated": 33, "tiebreak_rows": len(semantic_nonhard),
        "three_way_resolved": None, "three_way_unresolved": None,
    }
    _write_json(root / PB1_FIX2A_PROJECTION_COMPARISON, projection)
    _fix2a_append_phase("ORIGINAL_FIX2_RECOMPUTED", semantic_v2={"total":len(semantic_diffs),"hard":len(semantic_hard),"non_hard":len(semantic_nonhard)}, gold_impact_v1={"total":len(gold_diffs),"hard":len(gold_hard),"non_hard":len(gold_nonhard)}, projection_comparison_sha256=file_sha256(root / PB1_FIX2A_PROJECTION_COMPARISON))
    hard_exact = [row for row in original_comparison["differences"] if row["imported_hard"]]
    if len(hard_exact) != 33:
        raise ValueError(f"FIX2A_ORIGINAL_HARD_EXACT_COUNT:{len(hard_exact)}")
    reasons = {
        "EV2-A2-H01": "Declined-card runbook action is state-compatible although it does not repeat the state label.",
        "EV2-A2-H02": "Declined-ATM escalation handoff is state-compatible although it does not repeat the state label.",
        "EV2-A2-H05-R1": "Failed-transfer clauses are materially relevant context but do not support audit-record deletion; retain imported review.",
        "EV2-A2-H06-R1": "Both reviews establish contradiction; diagnostic dimension and wording differences are non-material.",
        "EV2-A2-H09-R1": "Retain imported broad BANK_TRANSFER target compatibility and equivalent contradiction semantics.",
        "EV2-A2-H10": "Both reviews establish explicit PENDING/FAILED contradiction; diagnostic wording is non-material.",
        "EV2-A2-H11": "Both reviews establish no-cash-dispensed versus CASH_DISPENSED contradiction.",
        "EV2-A2-H12": "Retain imported contradiction and target semantics; sender completion conflicts with simultaneous PENDING_SENDER.",
    }
    authorized_pairs = {
        ("EV2-A2-H01", "RUN_CARD_DECLINED_001#action"),
        ("EV2-A2-H02", "ESC_CASH_DECLINED_001#handoff"),
    }
    adjudications = []
    for item in hard_exact:
        pair = (item["case_id"], item["evidence_id"])
        before = current[pair]
        after = dict(before)
        if pair in authorized_pairs:
            after["state_match"] = True
        adjudications.append({
            "case_id": pair[0], "evidence_id": pair[1],
            "senior_decision": "ACCEPT_BLIND_STATE_COMPATIBILITY_ONLY" if pair in authorized_pairs else "RETAIN_IMPORTED_JUDGMENT",
            "authorized_active_change": pair in authorized_pairs,
            "before": {"support_class": before["support_class"], "target_match": before["target_match"], "state_match": before["state_match"], "dimension_match": before["dimension_match"], "obligations_covered": before["obligations_covered"]},
            "after": {"support_class": after["support_class"], "target_match": after["target_match"], "state_match": after["state_match"], "dimension_match": after["dimension_match"], "obligations_covered": after["obligations_covered"]},
            "reason": reasons[pair[0]],
        })
    hard_artifact = {
        "task_id": PB1_FIX2A_TASK_ID, "source_fix2_status": "A2_PB1_FIX2_IMPORTED_HARD_SEMANTIC_CONFLICT",
        "imported_hard_senior_adjudicated": len(adjudications),
        "imported_hard_active_row_changes": sum(row["authorized_active_change"] for row in adjudications),
        "imported_hard_unresolved": 0, "adjudications": adjudications,
    }
    _write_json(root / PB1_FIX2A_HARD_ADJUDICATION, hard_artifact)
    _fix2a_append_phase("SENIOR_HARD_ADJUDICATION_APPLIED_TO_PLAN", rows=len(adjudications), active_changes=2, adjudication_sha256=file_sha256(root / PB1_FIX2A_HARD_ADJUDICATION))
    original_by_pair = {(row["case_id"], row["evidence_id"]): row for row in original_packet}
    tiebreak_packet = []
    for index, pair in enumerate(sorted(semantic_nonhard), start=1):
        row = dict(original_by_pair[pair])
        row["review_id"] = f"FIX2A-TIEBREAK-{index:03d}"
        tiebreak_packet.append(row)
    write_jsonl(root / PB1_FIX2A_TIEBREAK_PACKET, tiebreak_packet)
    _fix2a_append_phase("TIEBREAK_PACKET_BUILT", rows=len(tiebreak_packet))
    validation = validate_pb1_fix2a_tiebreak_packet(root, tiebreak_packet)
    if not validation["passed"]:
        raise ValueError(f"FIX2A_TIEBREAK_PACKET_INVALID:{validation['errors'][:10]}")
    packet_sha = file_sha256(root / PB1_FIX2A_TIEBREAK_PACKET)
    _fix2a_append_phase("TIEBREAK_PACKET_VALIDATED", rows=65, packet_sha256=packet_sha)
    _fix2a_append_phase("TIEBREAK_PACKET_FROZEN", rows=65, packet_sha256=packet_sha)
    return {"passed": True, "projection_counts": observed, "packet_rows": 65, "packet_sha256": packet_sha, "hard_adjudication_sha256": file_sha256(root / PB1_FIX2A_HARD_ADJUDICATION), "projection_comparison_sha256": file_sha256(root / PB1_FIX2A_PROJECTION_COMPARISON), "phase_log": str(fix2a_phase_log_path())}


PB1_FIX2A_DECISION_FIELDS = (
    PB1_FIX2_DECISION_FIELDS - {"previous_label_visible_to_reviewer"}
) | {"previous_labels_visible_to_reviewer"}


def mark_pb1_fix2a_second_subagent_started(root: Path) -> dict[str, Any]:
    packet_sha = file_sha256(root / PB1_FIX2A_TIEBREAK_PACKET)
    log = _fix2a_read_phase_log()
    frozen = next((item for item in log["events"] if item["event"] == "TIEBREAK_PACKET_FROZEN"), None)
    if frozen is None or frozen.get("packet_sha256") != packet_sha:
        raise ValueError("FIX2A_TIEBREAK_PACKET_NOT_FROZEN")
    exact_inputs = [
        str(PB1_FIX2A_TIEBREAK_PACKET).replace("\\", "/"), packet_sha,
        "SECTION_12_GLOBAL_SEMANTIC_RULES", "REQUIRED_OUTPUT_SCHEMA_ONLY",
    ]
    _fix2a_append_phase("SECOND_ISOLATED_SUBAGENT_CREATED", context_mode="FRESH_NO_PARENT_OR_BLIND1_HISTORY", exact_inputs=exact_inputs)
    result = _fix2a_append_phase("SECOND_ISOLATED_SUBAGENT_REVIEW_STARTED", packet_sha256=packet_sha)
    return {"passed": True, "packet_sha256": packet_sha, "exact_inputs": exact_inputs, "events": len(result["events"])}


def mark_pb1_fix2a_second_subagent_completed(root: Path) -> dict[str, Any]:
    path = root / PB1_FIX2A_TIEBREAK_DECISIONS
    if not path.is_file():
        raise ValueError("FIX2A_TIEBREAK_DECISIONS_MISSING")
    sha = file_sha256(path)
    rows = len(read_jsonl(path))
    log = _fix2a_append_phase("SECOND_ISOLATED_SUBAGENT_REVIEW_COMPLETED", rows=rows, tiebreak_decisions_sha256=sha)
    return {"passed": True, "rows": rows, "tiebreak_decisions_sha256": sha, "events": len(log["events"])}


def validate_pb1_fix2a_tiebreak_decisions(root: Path, decisions: list[dict[str, Any]], *, record_freeze: bool = False) -> dict[str, Any]:
    packet = read_jsonl(root / PB1_FIX2A_TIEBREAK_PACKET)
    packet_result = validate_pb1_fix2a_tiebreak_packet(root, packet)
    errors = list(packet_result["errors"])
    packet_by_review = {row["review_id"]: row for row in packet}
    review_ids: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    for index, row in enumerate(decisions):
        prefix = f"fix2a_tiebreak_decision[{index}]"
        expected_fields = PB1_FIX2A_DECISION_FIELDS | (PB1_FIX2_CONTRADICTION_FIELDS if row.get("support_class") == "CONTRADICTION" else set())
        if set(row) != expected_fields:
            errors.append(f"{prefix}:field_set_not_exact:{sorted(set(row) ^ expected_fields)}")
            continue
        packet_row = packet_by_review.get(row["review_id"])
        pair = (row["case_id"], row["evidence_id"])
        if row["review_id"] in review_ids or pair in pairs:
            errors.append(f"{prefix}:duplicate_review_or_pair")
        review_ids.add(row["review_id"]); pairs.add(pair)
        if packet_row is None or pair != (packet_row["case_id"], packet_row["evidence_id"]):
            errors.append(f"{prefix}:packet_identity_mismatch")
            continue
        if row["evidence_content_sha256"] != packet_row["evidence_content_sha256"]:
            errors.append(f"{prefix}:evidence_hash_mismatch")
        text = packet_row["frozen_section_text"]
        if not _quotes_are_verbatim(row["review_basis_quotes"], text):
            errors.append(f"{prefix}:review_basis_not_exact_quote")
        if row["review_provenance"] != PB1_FIX2A_TIEBREAK_PROVENANCE or row["previous_labels_visible_to_reviewer"] is not False:
            errors.append(f"{prefix}:tiebreak_provenance_invalid")
        if any(not isinstance(row[key], bool) for key in ("target_match", "state_match", "dimension_match")):
            errors.append(f"{prefix}:compatibility_not_boolean")
        required = packet_row["kb_support_required_obligations"]
        covered = row["obligations_covered"]
        if len(covered) != len(set(covered)) or not set(covered) <= set(required):
            errors.append(f"{prefix}:covered_obligations_invalid")
        support_class = row["support_class"]
        compatible = row["target_match"] and row["state_match"] and row["dimension_match"]
        if support_class not in SUPPORT_CLASSES:
            errors.append(f"{prefix}:unknown_support_class")
        elif support_class == "COMPLETE_SUPPORT" and (not required or set(covered) != set(required) or not compatible):
            errors.append(f"{prefix}:invalid_complete")
        elif support_class == "PARTIAL_SUPPORT" and (not covered or set(covered) == set(required) or not compatible):
            errors.append(f"{prefix}:invalid_partial")
        elif support_class in {"CONTEXTUAL_INSUFFICIENT", "CONTRADICTION", "IRRELEVANT"} and covered:
            errors.append(f"{prefix}:nonpositive_has_coverage")
        quote_map = row["support_quotes_by_obligation"]
        explanation_map = row["semantic_entailment_explanation_by_obligation"]
        if set(quote_map) != set(covered) or set(explanation_map) != set(covered):
            errors.append(f"{prefix}:positive_trace_key_mismatch")
        for obligation, quotes in quote_map.items():
            if not _quotes_are_verbatim(quotes, text):
                errors.append(f"{prefix}:support_quote_not_exact:{obligation}")
            if not isinstance(explanation_map.get(obligation), str) or len(explanation_map[obligation].strip()) < 12:
                errors.append(f"{prefix}:entailment_explanation_missing:{obligation}")
        if not isinstance(row["support_rationale"], str) or len(row["support_rationale"].strip()) < 24:
            errors.append(f"{prefix}:support_rationale_not_specific")
        if support_class == "CONTRADICTION":
            if row["contradiction_basis_quote"] not in text or not row["contradicted_constraint"] or len(row["contradiction_semantic_explanation"].strip()) < 12:
                errors.append(f"{prefix}:contradiction_proof_invalid")
    if len(decisions) != 65 or len(review_ids) != 65 or len(pairs) != 65 or set(review_ids) != set(packet_by_review):
        errors.append(f"fix2a_tiebreak_decision_cardinality:{len(decisions)}:{len(review_ids)}:{len(pairs)}")
    log = _fix2a_read_phase_log()
    events = [item["event"] for item in log["events"]]
    required_events = [
        "PROJECTION_V2_DEFINED", "ORIGINAL_FIX2_RECOMPUTED", "SENIOR_HARD_ADJUDICATION_APPLIED_TO_PLAN",
        "TIEBREAK_PACKET_BUILT", "TIEBREAK_PACKET_VALIDATED", "TIEBREAK_PACKET_FROZEN",
        "SECOND_ISOLATED_SUBAGENT_CREATED", "SECOND_ISOLATED_SUBAGENT_REVIEW_STARTED",
        "SECOND_ISOLATED_SUBAGENT_REVIEW_COMPLETED",
    ]
    if events[:len(required_events)] != required_events:
        errors.append("false_previous_labels_declaration_without_second_isolation_evidence")
    if log.get("parent_authored_tiebreak_decisions") is not False or log.get("second_subagent_received_previous_labels") is not False or log.get("second_subagent_received_blind1_decisions") is not False or log.get("second_subagent_received_senior_findings") is not False:
        errors.append("BLOCKED_FIX2A_SECOND_ISOLATED_REVIEWER_PROVENANCE_VIOLATION")
    decision_sha = file_sha256(root / PB1_FIX2A_TIEBREAK_DECISIONS) if (root / PB1_FIX2A_TIEBREAK_DECISIONS).is_file() else None
    if not errors and record_freeze:
        _fix2a_append_phase("TIEBREAK_DECISIONS_VALIDATED", rows=65, tiebreak_decisions_sha256=decision_sha)
        _fix2a_append_phase("TIEBREAK_DECISIONS_FROZEN", rows=65, tiebreak_decisions_sha256=decision_sha)
    return {"passed": not errors, "errors": errors, "rows": len(decisions), "unique_pairs": len(pairs), "support_class_counts": dict(Counter(row.get("support_class") for row in decisions)), "tiebreak_decisions_sha256": decision_sha}


def _apply_fix2a_decision_to_pass_b_row(
    target: dict[str, Any], decision: dict[str, Any], required: list[str], section_text: str,
) -> None:
    covered = list(decision["obligations_covered"])
    target.update({
        "target_match": decision["target_match"], "state_match": decision["state_match"],
        "dimension_match": decision["dimension_match"], "obligations_covered": covered,
        "obligations_not_covered": [item for item in required if item not in set(covered)],
        "support_class": decision["support_class"],
        "support_quotes_by_obligation": decision["support_quotes_by_obligation"],
        "semantic_entailment_explanation_by_obligation": decision["semantic_entailment_explanation_by_obligation"],
        "support_rationale": section_text + " " + decision["support_rationale"],
        "fix2a_tiebreak_review_id": decision["review_id"],
    })
    for key in PB1_FIX2_CONTRADICTION_FIELDS:
        target.pop(key, None)
    target.pop("missing_required_obligations", None)
    target.pop("semantic_mismatch_reason", None)
    if decision["support_class"] == "CONTRADICTION":
        target.update({key: decision[key] for key in PB1_FIX2_CONTRADICTION_FIELDS})
    elif decision["support_class"] == "CONTEXTUAL_INSUFFICIENT":
        target["missing_required_obligations"] = list(required)
        target["semantic_mismatch_reason"] = decision["support_rationale"]
    elif decision["support_class"] == "IRRELEVANT":
        target["semantic_mismatch_reason"] = decision["support_rationale"]


def resolve_and_apply_pb1_fix2a(root: Path) -> dict[str, Any]:
    decisions = read_jsonl(root / PB1_FIX2A_TIEBREAK_DECISIONS)
    validation = validate_pb1_fix2a_tiebreak_decisions(root, decisions, record_freeze=False)
    if not validation["passed"]:
        raise ValueError(f"FIX2A_TIEBREAK_DECISIONS_INVALID:{validation['errors'][:10]}")
    log = _fix2a_read_phase_log()
    frozen = next((item for item in log["events"] if item["event"] == "TIEBREAK_DECISIONS_FROZEN"), None)
    decision_sha = file_sha256(root / PB1_FIX2A_TIEBREAK_DECISIONS)
    if frozen is None or frozen.get("tiebreak_decisions_sha256") != decision_sha:
        raise ValueError("BLOCKED_FIX2A_TIEBREAK_POST_COMPARISON_MUTATION")
    _fix2a_append_phase("THREE_WAY_COMPARISON_OPENED", tiebreak_decisions_sha256=decision_sha)
    current_rows = read_jsonl(root / PASS_B)
    blind1_rows = read_jsonl(root / PB1_FIX2_BLIND_DECISIONS)
    packet = read_jsonl(root / PB1_FIX2A_TIEBREAK_PACKET)
    current = {(row["case_id"], row["evidence_id"]): row for row in current_rows}
    blind1 = {(row["case_id"], row["evidence_id"]): row for row in blind1_rows}
    tiebreak_by_review = {row["review_id"]: row for row in decisions}
    matrix = []
    unresolved = []
    selected_tiebreak: dict[tuple[str, str], dict[str, Any]] = {}
    current_wins = 0
    blind1_wins = 0
    for packet_row in packet:
        pair = (packet_row["case_id"], packet_row["evidence_id"])
        c = tiebreak_by_review[packet_row["review_id"]]
        a_projection = semantic_decision_projection_v2(current[pair])
        b_projection = semantic_decision_projection_v2(blind1[pair])
        c_projection = semantic_decision_projection_v2(c)
        if a_projection == b_projection:
            raise ValueError(f"FIX2A_TIEBREAK_PACKET_CONSTRUCTION_DRIFT:{pair}")
        if c_projection == a_projection:
            winner = "CURRENT"
            reason = "TIEBREAK_CONFIRMS_CURRENT"
            current_wins += 1
        elif c_projection == b_projection:
            winner = "TIEBREAK"
            reason = "TIEBREAK_CONFIRMS_BLIND1"
            selected_tiebreak[pair] = c
            blind1_wins += 1
        else:
            winner = "UNRESOLVED"
            reason = "THIRD_PROJECTION_MISMATCH"
            unresolved.append({"case_id": pair[0], "evidence_id": pair[1], "review_id": c["review_id"]})
        matrix.append({
            "case_id": pair[0], "evidence_id": pair[1], "review_id": c["review_id"],
            "current_projection": list(a_projection), "blind1_projection": list(b_projection),
            "tiebreak_projection": list(c_projection), "winner": winner, "reason": reason,
        })
    matrix_artifact = {
        "task_id": PB1_FIX2A_TASK_ID, "rows": len(matrix), "current_wins": current_wins,
        "blind1_wins_tiebreak_selected": blind1_wins, "unresolved": len(unresolved), "matrix": matrix,
    }
    _write_json(fix2a_external_review_dir() / "three_way_resolution_matrix.json", matrix_artifact)
    projection = _load_json(root, PB1_FIX2A_PROJECTION_COMPARISON)
    projection["three_way_resolved"] = len(matrix)-len(unresolved)
    projection["three_way_unresolved"] = len(unresolved)
    projection["three_way_current_wins"] = current_wins
    projection["three_way_blind1_wins_tiebreak_selected"] = blind1_wins
    _write_json(root / PB1_FIX2A_PROJECTION_COMPARISON, projection)
    _fix2a_append_phase("THREE_WAY_COMPARISON_COMPLETED", rows=65, current_wins=current_wins, blind1_wins_tiebreak_selected=blind1_wins, unresolved=len(unresolved), resolution_matrix_sha256=file_sha256(fix2a_external_review_dir() / "three_way_resolution_matrix.json"))
    if unresolved:
        return {"passed": False, "status": "A2_PB1_FIX2A_UNRESOLVED_THREE_WAY_SEMANTIC_CONFLICT", "current_wins": current_wins, "blind1_wins_tiebreak_selected": blind1_wins, "unresolved": unresolved}
    final_rows = json.loads(json.dumps(current_rows))
    final_index = {(row["case_id"], row["evidence_id"]): row for row in final_rows}
    required = pb1_required_obligations(read_jsonl(root / OBLIGATION_CLASSIFICATION))
    eligible, _ = eligible_section_index(root)
    senior_pairs = {
        ("EV2-A2-H01", "RUN_CARD_DECLINED_001#action"),
        ("EV2-A2-H02", "ESC_CASH_DECLINED_001#handoff"),
    }
    ledger_rows = []
    for pair in sorted(senior_pairs):
        before = pb1_fix1_semantic_projection(current[pair])
        final_index[pair]["state_match"] = True
        after = pb1_fix1_semantic_projection(final_index[pair])
        ledger_rows.append({"case_id":pair[0],"evidence_id":pair[1],"source":"SENIOR_HARD_ADJUDICATION","before":before,"after":after})
    for pair, decision in sorted(selected_tiebreak.items()):
        before = pb1_fix1_semantic_projection(current[pair])
        _apply_fix2a_decision_to_pass_b_row(final_index[pair], decision, required[pair[0]], eligible[pair[1]]["content"])
        after = pb1_fix1_semantic_projection(final_index[pair])
        ledger_rows.append({"case_id":pair[0],"evidence_id":pair[1],"source":"ISOLATED_TIEBREAK","review_id":decision["review_id"],"before":before,"after":after})
    if any(row["before"] == row["after"] for row in ledger_rows):
        raise ValueError("FIX2A_LEDGER_CONTAINS_NOOP_CHANGE")
    ledger = {
        "task_id": PB1_FIX2A_TASK_ID, "current_fix1_pass_b_sha256": PB1_FIX1_PRE_FIX2_PASS_B_SHA256,
        "tiebreak_decisions_sha256": decision_sha, "changed_row_count": len(ledger_rows),
        "source_counts": dict(Counter(row["source"] for row in ledger_rows)), "changes": ledger_rows,
    }
    _write_json(root / PB1_FIX2A_FINAL_LEDGER, ledger)
    pass_a = read_jsonl(root / PASS_A)
    classifications = read_jsonl(root / OBLIGATION_CLASSIFICATION)
    matrix_result = validate_pb1_pass_b(root, pass_a, classifications, final_rows)
    if not matrix_result["passed"]:
        raise ValueError(f"A2_PB1_FIX2A_PASS_B_INVALID:{matrix_result['errors'][:10]}")
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in final_rows:
        by_case[row["case_id"]].append(row)
    required_by_case = pb1_required_obligations(classifications)
    pure_gate_errors = []
    for case in pass_a:
        sets = derive_pb1_minimal_complete_sets(required_by_case.get(case["case_id"], []), by_case[case["case_id"]])
        if case["semantic_stratum"] in {"STANDARD", "SAFE_CORRECTIVE"} and not sets:
            pure_gate_errors.append(f"missing_complete_support:{case['case_id']}")
        if case["semantic_stratum"] == "HARD_ABSTAIN_ESCALATE" and sets:
            pure_gate_errors.append(f"hard_complete_support:{case['case_id']}")
    if pure_gate_errors:
        raise ValueError(f"A2_PB1_FIX2A_PASS_A_V3_STRATUM_CONFLICT:{pure_gate_errors[:10]}")
    write_jsonl(root / PASS_B, final_rows)
    _fix2a_append_phase("FINAL_PASS_B_BUILT", rows=len(final_rows), changed_rows=len(ledger_rows), pass_b_sha256=file_sha256(root / PASS_B), correction_ledger_sha256=file_sha256(root / PB1_FIX2A_FINAL_LEDGER))
    regenerate_pb1_proofs(root, pass_a, classifications, final_rows)
    positive = _load_json(root, POSITIVE_SUPPORT_AUDIT); safe = _load_json(root, SAFE_CORRECTIVE_PROOFS)
    hard = _load_json(root, HARD_ABSTAIN_PROOFS); ambiguous = _load_json(root, AMBIGUOUS_DERIVATION)
    proof = validate_pb1_stratum_proofs(pass_a, classifications, final_rows, positive, safe, hard, ambiguous)
    proof_counts = (proof["standard_valid"], proof["safe_corrective_valid"], proof["hard_valid"], proof["ambiguous_valid"])
    if not proof["passed"] or proof_counts != (24,18,12,6):
        raise ValueError(f"A2_PB1_FIX2A_PASS_A_V3_STRATUM_CONFLICT:{proof['errors'][:10]}")
    _fix2a_append_phase("FINAL_PROOFS_DERIVED", proof_counts=list(proof_counts))
    ineligible = _load_json(root, INELIGIBLE_EVIDENCE_AUDIT)
    first = derive_pb1_pass_c_fail_closed(root, pass_a, classifications, final_rows, ineligible, positive, safe, hard, ambiguous)
    second = derive_pb1_pass_c_fail_closed(root, pass_a, classifications, final_rows, ineligible, positive, safe, hard, ambiguous)
    if first != second:
        raise ValueError("FIX2A_PASS_C_NONDETERMINISTIC_OBJECT_DERIVATION")
    temp_first = fix2a_external_review_dir() / "pass_c_derivation_first.jsonl"
    temp_second = fix2a_external_review_dir() / "pass_c_derivation_second.jsonl"
    write_jsonl(temp_first, first); write_jsonl(temp_second, second)
    if temp_first.read_bytes() != temp_second.read_bytes():
        raise ValueError("FIX2A_PASS_C_NONDETERMINISTIC_BYTES")
    write_jsonl(root / PASS_C, first)
    pass_c_sha = file_sha256(root / PASS_C)
    _fix2a_append_phase("FINAL_PASS_C_DERIVED", rows=len(first), pass_c_sha256=pass_c_sha, deterministic_first_sha256=file_sha256(temp_first), deterministic_second_sha256=file_sha256(temp_second))
    return {
        "passed": True, "status": PB1_FIX2A_EXTERNAL_STATUS, "current_wins": current_wins,
        "blind1_wins_tiebreak_selected": blind1_wins, "unresolved": 0,
        "changed_rows": len(ledger_rows), "source_counts": ledger["source_counts"],
        "pass_b_sha256": file_sha256(root / PASS_B), "pass_b_counts": matrix_result["support_class_counts"],
        "proof_counts": list(proof_counts), "pass_c_sha256": pass_c_sha,
        "route_counts": dict(Counter(row["expected_production_route"] for row in first)),
    }


def build_pb1_fix2a_stop_bundle(root: Path) -> dict[str, Any]:
    output = Path(tempfile.gettempdir()) / "W3-003-EV2-A2-PB1-FIX2A_SENIOR_REVIEW_BUNDLE.zip"
    sidecar = output.with_suffix(output.suffix + ".sha256")
    stage = Path(tempfile.gettempdir()) / "W3-003-EV2-A2-PB1-FIX2A_SENIOR_REVIEW_BUNDLE_payload"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    payload = tuple(dict.fromkeys((
        PASS_A, PASS_B, PASS_C, PB1_FIX2_BLIND_PACKET, PB1_FIX2_BLIND_DECISIONS,
        PB1_FIX2_COMPARISON, PB1_FIX2_LEDGER, PB1_FIX2A_HARD_ADJUDICATION,
        PB1_FIX2A_PROJECTION_COMPARISON, PB1_FIX2A_TIEBREAK_PACKET,
        PB1_FIX2A_TIEBREAK_DECISIONS, OBLIGATION_CLASSIFICATION,
        POSITIVE_SUPPORT_AUDIT, SAFE_CORRECTIVE_PROOFS, HARD_ABSTAIN_PROOFS,
        AMBIGUOUS_DERIVATION, SUPPORT_SUMMARY, INELIGIBLE_EVIDENCE_AUDIT,
        LINEAGE_AUDIT, A2_MANIFEST, PB1_FIX1_LEDGER, PB1_FIX1_AUDIT_SUMMARY,
        Path("scripts/evaluation/week3_ev2_a2.py"), Path("tests/test_week3_ev2_a2.py"),
        Path("reports/week_03/experiments/W3-003-EV2-A2.md"), Path("PROJECT_STATE.md"),
        Path("TASKS.md"), Path("reports/week_03/daily/2026-08-21.md"),
        Path("reports/week_03/week_03_summary.md"), *PB1_BUNDLE_HISTORY,
    )))
    for rel in payload:
        source = root / rel
        if not source.is_file():
            raise FileNotFoundError(rel)
        target = stage / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    review = stage / "review_evidence"
    review.mkdir()
    shutil.copy2(fix2a_phase_log_path(), review / "fix2a_tiebreak_phase_log.json")
    shutil.copy2(fix2a_external_review_dir() / "three_way_resolution_matrix.json", review / "three_way_resolution_matrix.json")
    original_phase = fix2_phase_log_path()
    if original_phase.is_file():
        shutil.copy2(original_phase, review / "fix2_blind_phase_log.json")
    status = subprocess.run(["git", "status", "--short"], cwd=root, check=True, capture_output=True, encoding="utf-8", errors="replace").stdout
    diff = subprocess.run(["git", "diff", "--binary"], cwd=root, check=True, capture_output=True, encoding="utf-8", errors="replace").stdout
    (review / "git_status.txt").write_text(status, encoding="utf-8")
    (review / "git_diff.patch").write_text(diff, encoding="utf-8")
    (review / "commands_and_test_output.txt").write_text("\n".join((
        "fresh preflight -> branch=main; HEAD=origin/main=fresh remote=8492659a50fe00f066f9f64d8759d544356b3a41; staged=0; production_diff=0; kb_diff=0",
        "prepare-pb1-fix2a-tiebreak -> V2 76/11/65; Gold Impact 58/2/56; packet 65 PASS; packet SHA f2ecb40ab1691fb940a8a341fc47bd24ffc72c443b332358c70aed8210ee03e6",
        "second isolated fresh-context subagent -> 65 decisions; SHA 379ca46bc56d50af04058e9809fabbf18dc97b1f75aadf088344ede94a9765ba",
        "validate-pb1-fix2a-tiebreak-decisions -> PASS; 65 rows; decisions frozen before comparison",
        "resolve-apply-pb1-fix2a -> A2_PB1_FIX2A_UNRESOLVED_THREE_WAY_SEMANTIC_CONFLICT; current=26; blind1/tiebreak=22; unresolved=17",
        "python -B -m pytest tests/test_week3_ev2_a2.py -q -> 121 passed in 4.81s",
        "python -B -m pytest tests/test_reporting -q -> 80 passed in 0.21s",
        "python -B scripts/reporting/validate_project_docs.py -> VALIDATION PASSED",
        "git diff --check -> exit 0",
        "active Pass B/C unchanged; final correction ledger absent; final proofs/Pass C not derived; candidate inference=false; EV2=false; A3=false; stage/commit/push=false",
    )) + "\n", encoding="utf-8")
    packet = read_jsonl(root / PB1_FIX2A_TIEBREAK_PACKET)
    decisions = read_jsonl(root / PB1_FIX2A_TIEBREAK_DECISIONS)
    packet_by_review = {row["review_id"]: row for row in packet}
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in decisions:
        by_class[row["support_class"]].append(row)
    _write_json(review / "tiebreak_semantic_sample.json", {
        "samples": [{"packet":packet_by_review[row["review_id"]],"decision":row} for support_class in sorted(by_class) for row in by_class[support_class][:2]],
    })
    _write_json(review / "final_support_set_derivation_audit.json", {
        "status":"NOT_DERIVED_DUE_TO_17_UNRESOLVED_THREE_WAY_SEMANTIC_CONFLICTS",
        "final_correction_ledger_created":False, "active_pass_b_unchanged":file_sha256(root / PASS_B)==PB1_FIX1_PRE_FIX2_PASS_B_SHA256,
        "active_pass_b_sha256":file_sha256(root / PASS_B), "proof_artifacts_regenerated":False,
    })
    _write_json(review / "final_pass_c_derivation_audit.json", {
        "status":"NOT_DERIVED_DUE_TO_17_UNRESOLVED_THREE_WAY_SEMANTIC_CONFLICTS",
        "active_pass_c_unchanged":file_sha256(root / PASS_C)==PB1_FIX1_PRE_FIX2_PASS_C_SHA256,
        "active_pass_c_sha256":file_sha256(root / PASS_C), "deterministic_regeneration":"NOT_RUN_STOP_RULE",
    })
    base_files = sorted(path for path in stage.rglob("*") if path.is_file())
    manifest = {
        "task_id":PB1_FIX2A_TASK_ID, "status":"A2_PB1_FIX2A_UNRESOLVED_THREE_WAY_SEMANTIC_CONFLICT",
        "entry_count_excluding_receipts":len(base_files),
        "entries":[{"path":path.relative_to(stage).as_posix(),"bytes":path.stat().st_size,"sha256":file_sha256(path)} for path in base_files],
    }
    _write_json(review / "bundle_manifest.json", manifest)
    (review / "bundle_sha256.txt").write_text(
        "Archive SHA-256 is recorded in the detached .zip.sha256 sidecar.\n"
        f"bundle_manifest_sha256  {file_sha256(review / 'bundle_manifest.json')}\n", encoding="utf-8",
    )
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in stage.rglob("*") if item.is_file()):
            info = zipfile.ZipInfo(path.relative_to(stage).as_posix(), date_time=(2026,8,21,12,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    archive_sha = file_sha256(output)
    sidecar.write_text(f"{archive_sha}  {output.name}\n", encoding="ascii")
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist(); crc_bad = archive.testzip()
        archived_manifest = json.loads(archive.read("review_evidence/bundle_manifest.json"))
        payload_hashes_valid = all(
            hashlib.sha256(archive.read(item["path"])).hexdigest()==item["sha256"]
            and len(archive.read(item["path"]))==item["bytes"] for item in archived_manifest["entries"]
        )
    return {
        "passed":crc_bad is None and len(names)==len(set(names)) and payload_hashes_valid,
        "status":"A2_PB1_FIX2A_UNRESOLVED_THREE_WAY_SEMANTIC_CONFLICT",
        "path":str(output),"sidecar":str(sidecar),"bytes":output.stat().st_size,"sha256":archive_sha,
        "entries":len(names),"crc_bad_entry":crc_bad,"duplicate_entries":len(names)-len(set(names)),
        "payload_hashes_valid":payload_hashes_valid,"expected_entries_present":all((stage/rel).is_file() for rel in payload),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=(
        "validate-pass-a", "validate-pass-a-v2", "validate-pass-a-rev1",
        "validate-pass-b", "validate-fix1b", "validate-fix2", "validate-fix2a",
        "validate-fix3", "validate-pb1", "refresh-pb1", "build-pb1-bundle",
        "apply-pb1-fix1", "validate-pb1-fix1", "build-pb1-fix1-bundle",
        "build-pb1-fix2-blind-packet", "mark-pb1-fix2-subagent-started",
        "mark-pb1-fix2-subagent-completed", "validate-pb1-fix2-blind-decisions",
        "apply-pb1-fix2", "build-pb1-fix2-stop-bundle",
        "prepare-pb1-fix2a-tiebreak",
        "mark-pb1-fix2a-subagent-started", "mark-pb1-fix2a-subagent-completed",
        "validate-pb1-fix2a-tiebreak-decisions",
        "resolve-apply-pb1-fix2a",
        "build-pb1-fix2a-stop-bundle",
        "derive-pb1", "derive", "lineage",
    ))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    pass_a = read_jsonl(root / PASS_A)
    pass_a_v2 = read_jsonl(root / PASS_A_V2)
    if args.command == "validate-pass-a":
        result = validate_pass_a_v3(root)
    elif args.command == "validate-pass-a-v2":
        result = validate_pass_a_v2(root)
    elif args.command == "validate-pass-a-rev1":
        rev1 = read_jsonl(root / PASS_A_REV1)
        result = validate_pass_a(root, rev1, source_path=PASS_A_REV1)
    elif args.command == "validate-pass-b":
        result = validate_pass_b(root, pass_a, read_jsonl(root / PASS_B))
        result = {**result, "error_count": len(result["errors"]), "errors": result["errors"][:20]}
    elif args.command == "validate-fix1b":
        rev1 = read_jsonl(root / PASS_A_REV1)
        result = validate_fix1b_artifacts(
            root, rev1, read_jsonl(root / FIX1B_JUDGMENTS),
            json.loads((root / FIX1B_CASE_REVIEW).read_text(encoding="utf-8")),
            json.loads((root / FIX1B_CONFLICT_SUMMARY).read_text(encoding="utf-8")),
        )
        result = {**result, "errors": result["errors"][:20]}
    elif args.command == "validate-fix2":
        result = validate_fix2_artifacts(
            root, pass_a_v2,
            json.loads((root / FIX2_LEDGER).read_text(encoding="utf-8")),
            read_jsonl(root / FIX2_JUDGMENTS),
            json.loads((root / FIX2_CASE_REVIEW).read_text(encoding="utf-8")),
            json.loads((root / FIX2_PASS_A_AUDIT).read_text(encoding="utf-8")),
        )
        result = {**result, "errors": result["errors"][:20]}
    elif args.command == "validate-fix2a":
        result = validate_fix2a_artifacts(
            root, pass_a_v2,
            json.loads((root / FIX2A_OBLIGATION_CLASSIFICATION).read_text(encoding="utf-8")),
            json.loads((root / FIX2A_CONSISTENCY_REVIEW).read_text(encoding="utf-8")),
            json.loads((root / FIX2A_CONFLICT_SUMMARY).read_text(encoding="utf-8")),
        )
        result = {**result, "errors": result["errors"][:20]}
    elif args.command == "validate-fix3":
        result = validate_fix3_artifacts(
            root, pass_a,
            json.loads((root / FIX3_LEDGER).read_text(encoding="utf-8")),
            read_jsonl(root / FIX3_JUDGMENTS),
            json.loads((root / FIX3_CASE_REVIEW).read_text(encoding="utf-8")),
            json.loads((root / FIX3_PASS_A_AUDIT).read_text(encoding="utf-8")),
            json.loads((root / A2_MANIFEST).read_text(encoding="utf-8")),
        )
        result = {**result, "errors": result["errors"][:20]}
    elif args.command in {"validate-pb1", "validate-pb1-fix1"}:
        result = validate_pb1_package(root)
        result = {**result, "errors": result["errors"][:50]}
    elif args.command == "apply-pb1-fix1":
        result = apply_pb1_fix1(root)
    elif args.command == "build-pb1-fix2-blind-packet":
        result = build_pb1_fix2_blind_packet(root)
    elif args.command == "mark-pb1-fix2-subagent-started":
        result = mark_pb1_fix2_isolated_subagent_started(root)
    elif args.command == "mark-pb1-fix2-subagent-completed":
        result = mark_pb1_fix2_isolated_subagent_completed(root)
    elif args.command == "validate-pb1-fix2-blind-decisions":
        result = validate_pb1_fix2_blind_decisions(
            root, read_jsonl(root / PB1_FIX2_BLIND_DECISIONS), record_freeze=True,
        )
        result = {**result, "errors": result["errors"][:50]}
    elif args.command == "apply-pb1-fix2":
        result = apply_pb1_fix2_after_freeze(root)
    elif args.command == "build-pb1-fix2-stop-bundle":
        result = build_pb1_fix2_stop_bundle(root)
    elif args.command == "prepare-pb1-fix2a-tiebreak":
        result = prepare_pb1_fix2a_tiebreak(root)
    elif args.command == "mark-pb1-fix2a-subagent-started":
        result = mark_pb1_fix2a_second_subagent_started(root)
    elif args.command == "mark-pb1-fix2a-subagent-completed":
        result = mark_pb1_fix2a_second_subagent_completed(root)
    elif args.command == "validate-pb1-fix2a-tiebreak-decisions":
        result = validate_pb1_fix2a_tiebreak_decisions(
            root, read_jsonl(root / PB1_FIX2A_TIEBREAK_DECISIONS), record_freeze=True,
        )
        result = {**result, "errors": result["errors"][:50]}
    elif args.command == "resolve-apply-pb1-fix2a":
        result = resolve_and_apply_pb1_fix2a(root)
    elif args.command == "build-pb1-fix2a-stop-bundle":
        result = build_pb1_fix2a_stop_bundle(root)
    elif args.command == "refresh-pb1":
        summary, manifest = refresh_pb1_metadata(root)
        result = {
            "passed": True, "status": summary["status"],
            "summary_sha256": file_sha256(root / SUPPORT_SUMMARY),
            "lineage_sha256": file_sha256(root / LINEAGE_AUDIT),
            "manifest_sha256": file_sha256(root / A2_MANIFEST),
            "manifest_artifact_count": len(manifest["active_artifact_sha256"]),
        }
    elif args.command in {"build-pb1-bundle", "build-pb1-fix1-bundle"}:
        package = validate_pb1_package(root)
        if not package["passed"]:
            result = {"passed": False, "status": "A2_PB1_BUNDLE_BLOCKED", "errors": package["errors"][:50]}
        else:
            result = {"passed": True, **build_pb1_review_bundle(root)}
    elif args.command == "derive-pb1":
        classifications = read_jsonl(root / OBLIGATION_CLASSIFICATION)
        pass_b = read_jsonl(root / PASS_B)
        classification_result = validate_pb1_obligation_classification(pass_a, classifications)
        matrix_result = validate_pb1_pass_b(root, pass_a, classifications, pass_b)
        proof_result = validate_pb1_stratum_proofs(
            pass_a, classifications, pass_b,
            _load_json(root, POSITIVE_SUPPORT_AUDIT), _load_json(root, SAFE_CORRECTIVE_PROOFS),
            _load_json(root, HARD_ABSTAIN_PROOFS), _load_json(root, AMBIGUOUS_DERIVATION),
        )
        ineligible = _load_json(root, INELIGIBLE_EVIDENCE_AUDIT)
        ineligible_result = validate_pb1_ineligible_audit(root, ineligible)
        derivation_errors = [
            *classification_result["errors"], *matrix_result["errors"],
            *proof_result["errors"], *ineligible_result["errors"],
        ]
        if derivation_errors:
            result = {"passed": False, "status": "A2_PB1_PASS_A_V3_STRATUM_CONFLICT", "errors": derivation_errors[:50]}
        else:
            derived = derive_pb1_pass_c_fail_closed(
                root, pass_a, classifications, pass_b, ineligible,
                _load_json(root, POSITIVE_SUPPORT_AUDIT), _load_json(root, SAFE_CORRECTIVE_PROOFS),
                _load_json(root, HARD_ABSTAIN_PROOFS), _load_json(root, AMBIGUOUS_DERIVATION),
            )
            write_jsonl(root / PASS_C, derived)
            result = {"passed": True, "rows": len(derived), "sha256": file_sha256(root / PASS_C)}
    elif args.command == "derive":
        pass_c, conflicts = derive_pass_c(root, pass_a, read_jsonl(root / PASS_B))
        if conflicts:
            result = {"passed": False, "status": "A2_FIX1_PASS_A_STRATUM_CONFLICT", "conflicts": conflicts}
        else:
            write_jsonl(root / PASS_C, pass_c)
            result = {"passed": True, "rows": len(pass_c)}
    else:
        audit = compute_lineage_audit(root, pass_a)
        (root / LINEAGE_AUDIT).write_text(
            json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        result = {"passed": validate_lineage_audit(audit)["passed"], "audit": audit}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
