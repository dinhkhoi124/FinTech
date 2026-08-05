"""Standalone verifier for an extracted W3-002-CR1 feasibility review bundle.

Uses only Python's standard library and bundled files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


SAFE_IDS = {
    "Q_V4_N_ID01", "Q_V4_N_ID02", "Q_V4_N_ID03", "Q_V4_N_ID04",
    "Q_V4_N_AM01", "Q_V4_N_AM02", "Q_V4_N_AM03",
    "Q_V4_N_DR01", "Q_V4_N_DR02", "Q_V4_N_DR03",
    "Q_V4_N_EX01", "Q_V4_N_EX02", "Q_V4_N_EX03", "Q_V4_N_IN01", "Q_V4_N_IN02",
}
ABSTAIN_IDS = {"Q_V4_N_CF01", "Q_V4_N_CF02", "Q_V4_N_OS01", "Q_V4_N_AB01", "Q_V4_N_AB02"}
EXPECTED_POSITIVE_DEFECTS = {
    ("Q_V2_A_TRD04", "RUN_TRANSFER_DECLINED_001#action"),
    ("Q_V2_A_TRR04", "FAQ_TRANSFER_RECIPIENT_002#current_window"),
    ("Q_V2_A_TRR04", "POL_TRANSFER_RECIPIENT_001#trace_window"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(not isinstance(value, dict) for value in values):
        raise RuntimeError(f"expected JSON objects: {path}")
    return values


def verify_inventory(root: Path) -> int:
    inventory = read_json(root / "bundle_inventory.json")
    expected = {item["path"] for item in inventory["files"]}
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    } - {"bundle_inventory.json"}
    if expected != actual or inventory.get("file_count_excluding_inventory") != len(expected):
        raise RuntimeError("bundle inventory path set/count mismatch")
    for item in inventory["files"]:
        path = root / item["path"]
        if path.stat().st_size != item["size_bytes"] or sha256(path) != item["sha256"]:
            raise RuntimeError(f"bundle inventory hash mismatch: {item['path']}")
    if inventory.get("candidate_revision_5_created") is not False or inventory.get("evaluation_authorized") is not False:
        raise RuntimeError("bundle inventory lifecycle is unauthorized")
    return len(expected)


def verify_cases(root: Path) -> tuple[list[dict[str, Any]], set[str]]:
    cases = read_jsonl(root / "review/contract_amendment_safety_challenges.jsonl")
    if len(cases) != 20 or {case.get("query_id") for case in cases} != SAFE_IDS | ABSTAIN_IDS:
        raise RuntimeError("contract amendment must contain the exact 20 safety challenges")
    taxonomy = read_json(root / "review/response_taxonomy_proposal.json")
    if taxonomy.get("response_type") != ["ANSWER", "ABSTAIN_ESCALATE"] or taxonomy.get("answer_subtype_for_answer") != ["STANDARD", "SAFE_CORRECTIVE"]:
        raise RuntimeError("response taxonomy proposal mismatch")
    if taxonomy.get("proposed_distribution") != {"ANSWER/STANDARD": 40, "ANSWER/SAFE_CORRECTIVE": 15, "ABSTAIN_ESCALATE": 5}:
        raise RuntimeError("proposed response distribution mismatch")
    outcomes = Counter((case["response_type"], case.get("answer_subtype")) for case in cases)
    if outcomes != Counter({("ANSWER", "SAFE_CORRECTIVE"): 15, ("ABSTAIN_ESCALATE", None): 5}):
        raise RuntimeError(f"safety-challenge distribution mismatch: {dict(outcomes)}")

    evidence = {row["evidence_id"]: row for row in read_jsonl(root / "review/approved_corrective_evidence_catalog.jsonl")}
    forbidden = set(read_json(root / "review/forbidden_evidence_catalog.json")["evidence_ids"])
    all_cover_ids: set[str] = set()
    for case in cases:
        query_id = case["query_id"]
        if query_id in SAFE_IDS:
            if case["response_type"] != "ANSWER" or case["answer_subtype"] != "SAFE_CORRECTIVE":
                raise RuntimeError(f"invalid safe-corrective taxonomy: {query_id}")
            obligations = case.get("corrective_obligations", [])
            covers = case.get("all_minimal_corrective_covers", [])
            if not obligations or not covers or not case.get("grounded_corrective_response_outline"):
                raise RuntimeError(f"incomplete corrective case: {query_id}")
            acceptable = {item["obligation_id"]: set(item["acceptable_evidence_ids"]) for item in obligations}
            if len(acceptable) != len(obligations):
                raise RuntimeError(f"duplicate corrective obligation: {query_id}")
            for cover in covers:
                cover_set = set(cover)
                if not cover_set or len(cover_set) != len(cover):
                    raise RuntimeError(f"invalid corrective cover: {query_id}")
                if cover_set & forbidden:
                    raise RuntimeError(f"forbidden evidence in corrective cover: {query_id}")
                for evidence_id in cover:
                    row = evidence.get(evidence_id)
                    if not row or row.get("status") != "APPROVED" or row.get("approved_and_effective") is not True:
                        raise RuntimeError(f"ineligible corrective evidence: {query_id}/{evidence_id}")
                if any(not (cover_set & ids) for ids in acceptable.values()):
                    raise RuntimeError(f"corrective cover misses an obligation: {query_id}")
                all_cover_ids.update(cover_set)
            expected_sections = min(len(cover) for cover in covers)
            expected_documents = min(len({evidence_id.split("#", 1)[0] for evidence_id in cover}) for cover in covers)
            if case.get("minimum_section_count") != expected_sections or case.get("minimum_document_count") != expected_documents:
                raise RuntimeError(f"corrective-cover minima mismatch: {query_id}")
            if not case.get("why_complete_and_useful") or not case.get("why_prohibited_request_is_not_revealed_or_authorized"):
                raise RuntimeError(f"missing corrective rationale: {query_id}")
        else:
            if case.get("requested_answer_covers") or case.get("corrective_answer_covers"):
                raise RuntimeError(f"abstain case contains a complete cover: {query_id}")
            required = (
                "requested_obligations", "possible_corrective_obligations_considered",
                "all_relevant_approved_effective_evidence_ids",
                "why_no_complete_requested_answer_cover_exists",
                "why_no_complete_safe_corrective_cover_exists",
                "required_escalation_or_clarification_boundary",
            )
            if any(key not in case or case[key] in (None, "") for key in required):
                raise RuntimeError(f"incomplete abstain rationale: {query_id}")
    if set(evidence) != all_cover_ids:
        raise RuntimeError("corrective evidence catalog must equal evidence used by covers")
    return cases, all_cover_ids


def verify_category_summary(root: Path, cases: list[dict[str, Any]]) -> None:
    summary = read_json(root / "reports/week_03/results/critical_eval_v2_revision_4_category_feasibility.json")
    counts: dict[str, Counter[str]] = {}
    for case in cases:
        outcome = "ANSWER_SAFE_CORRECTIVE" if case["response_type"] == "ANSWER" else "ABSTAIN_ESCALATE"
        counts.setdefault(case["category"], Counter())[outcome] += 1
    for row in summary.get("categories", []):
        observed = counts[row["registered_category"]]
        if row["answer_safe_corrective_count"] != observed["ANSWER_SAFE_CORRECTIVE"] or row["true_abstain_count"] != observed["ABSTAIN_ESCALATE"]:
            raise RuntimeError(f"category count mismatch: {row['registered_category']}")
    if summary.get("fixed_40_answer_20_abstain_feasible") is not False:
        raise RuntimeError("fixed contract must remain infeasible")


def verify_findings(root: Path, all_cover_ids: set[str]) -> None:
    provenance = read_json(root / "reports/week_03/results/critical_eval_v2_revision_4_pass_b_provenance_audit.json")
    if provenance.get("pass_b_rows") != 3120 or provenance.get("rows_missing_reviewer_status") != 1040 or provenance.get("rows_with_revision_3_reviewer_status") != 2080 or provenance.get("rows_with_revision_4_reviewer_status") != 0:
        raise RuntimeError("Pass B provenance finding mismatch")
    if sum(provenance.get("reason_code_distribution", {}).values()) != 3120:
        raise RuntimeError("Pass B reason-code distribution mismatch")
    defects = read_jsonl(root / "reports/week_03/results/critical_eval_v2_revision_4_positive_support_defects.jsonl")
    if not EXPECTED_POSITIVE_DEFECTS.issubset({(row.get("query_id"), row.get("evidence_id")) for row in defects}):
        raise RuntimeError("positive-support findings incomplete")
    hard = read_json(root / "review/hard_negative_feasibility_enriched.json")
    if hard.get("candidate_count") != 5 or len(hard.get("candidates", [])) != 5:
        raise RuntimeError("hard-negative candidate count mismatch")
    for row in hard["candidates"]:
        if row.get("approved_and_effective") is not True or row.get("current_support_class") in {"DIRECT_SUPPORT", "PARTIAL_SUPPORT"}:
            raise RuntimeError("hard-negative support/eligibility mismatch")
        if row.get("requested_obligations_supported") or row.get("corrective_obligations_supported"):
            raise RuntimeError("hard-negative candidate supports an obligation")
        if row.get("belongs_to_no_complete_requested_cover") is not True or row.get("belongs_to_no_complete_corrective_cover") is not True:
            raise RuntimeError("hard-negative candidate belongs to a complete cover")
        if row["evidence_id"] in all_cover_ids and row["query_id"] in SAFE_IDS:
            raise RuntimeError("hard-negative candidate conflicts with corrective cover")


def verify_preservation(root: Path) -> tuple[int, int]:
    evidence = read_json(root / "review/preservation_hashes.json")
    revision = evidence.get("revision_4_artifact_sha256", {})
    historical = evidence.get("historical_w3_002_artifact_sha256", {})
    if len(revision) != 19 or len(historical) != 18:
        raise RuntimeError("preservation artifact count mismatch")
    for relative, digest in {**revision, **historical}.items():
        path = root / relative
        if not path.is_file() or sha256(path) != digest:
            raise RuntimeError(f"preservation hash mismatch: {relative}")
    manifest = root / "preservation/revision_4/reports/week_03/results/critical_eval_v2_candidate_manifest.json"
    if sha256(manifest) != evidence.get("revision_4_manifest_sha256"):
        raise RuntimeError("revision-4 manifest hash mismatch")
    review_bundle = root / evidence.get("revision_4_review_bundle_path", "")
    if not review_bundle.is_file() or sha256(review_bundle) != evidence.get("revision_4_review_bundle_sha256"):
        raise RuntimeError("revision-4 rejected review-bundle hash mismatch")
    return len(revision), len(historical)


def verify_lifecycle(root: Path) -> None:
    lifecycle = read_json(root / "review/lifecycle.json")
    required_false = (
        "candidate_revision_5_created", "structural_integrity_verified",
        "pre_evaluation_integrity_passed", "senior_semantic_review_approved",
        "evaluation_authorized", "critical_evaluated",
    )
    if any(lifecycle.get(key) is not False for key in required_false):
        raise RuntimeError("unauthorized lifecycle field")
    if lifecycle.get("model_verdict") != "NOT_ESTABLISHED" or lifecycle.get("status") != "BLOCKED / CONTRACT_AMENDMENT_REQUIRED":
        raise RuntimeError("lifecycle status mismatch")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    inventory_count = verify_inventory(root)
    cases, cover_ids = verify_cases(root)
    verify_category_summary(root, cases)
    verify_findings(root, cover_ids)
    revision_count, historical_count = verify_preservation(root)
    verify_lifecycle(root)
    result = {
        "standalone_bundle_verification": "PASS",
        "inventory_files_verified": inventory_count,
        "safety_challenge_rows": len(cases),
        "answer_standard_proposed": 40,
        "answer_safe_corrective_proposed": 15,
        "abstain_escalate_proposed": 5,
        "corrective_cover_evidence_sections": len(cover_ids),
        "hard_negative_candidates": 5,
        "revision_4_artifacts_verified": revision_count,
        "historical_w3_002_artifacts_verified": historical_count,
        "senior_semantic_review_approved": False,
        "evaluation_authorized": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"standalone_bundle_verification": "FAIL", "error": str(exc)}, indent=2))
        raise SystemExit(1)
