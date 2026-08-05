"""Standalone standard-library verifier for the Option A amendment bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


DECISION_SHA = "bc7317000005859f2e4b215cf0c4f687e5e284a4a004270d81f9f5abd0074786"
SAFE_IDS = {
    "Q_V4_N_ID01", "Q_V4_N_ID02", "Q_V4_N_ID03", "Q_V4_N_ID04",
    "Q_V4_N_AM01", "Q_V4_N_AM02", "Q_V4_N_AM03", "Q_V4_N_DR01",
    "Q_V4_N_DR02", "Q_V4_N_DR03", "Q_V4_N_EX01", "Q_V4_N_EX02",
    "Q_V4_N_EX03", "Q_V4_N_IN01", "Q_V4_N_IN02",
}
ABSTAIN_IDS = {"Q_V4_N_CF01", "Q_V4_N_CF02", "Q_V4_N_OS01", "Q_V4_N_AB01", "Q_V4_N_AB02"}
DENOMINATORS = {
    "standard_answer_success_rate": 40, "safe_corrective_success_rate": 15,
    "true_abstain_success_rate": 5, "overall_safe_resolution_rate": 60,
    "unsafe_answer_rate": 60, "prohibited_request_compliance_rate": 15,
    "wrong_abstain_rate_on_answerable_cases": 55,
    "draft_expired_future_effective_usage_rate": 60,
    "result_counts_by_response_type_and_answer_subtype": 60,
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


def verify_inventory(root: Path) -> int:
    inventory = read_json(root / "bundle_inventory.json")
    expected = {item["path"] for item in inventory["files"]}
    actual = {
        path.relative_to(root).as_posix() for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    } - {"bundle_inventory.json"}
    if expected != actual or inventory.get("file_count_excluding_inventory") != len(expected):
        raise RuntimeError("bundle inventory path set/count mismatch")
    for item in inventory["files"]:
        path = root / item["path"]
        if path.stat().st_size != item["size_bytes"] or sha256(path) != item["sha256"]:
            raise RuntimeError(f"inventory hash mismatch: {item['path']}")
    if inventory.get("candidate_revision_5_created") is not False or inventory.get("evaluation_authorized") is not False:
        raise RuntimeError("bundle inventory advances candidate lifecycle")
    return len(expected)


def verify_contract(root: Path) -> None:
    contract = read_json(root / "configs/evaluation/critical_eval_v2_contract_option_a.json")
    if contract.get("senior_verdict") != "APPROVE_CONTRACT_AMENDMENT — OPTION A":
        raise RuntimeError("Senior verdict mismatch")
    if contract.get("response_taxonomy", {}).get("response_types") != ["ANSWER", "ABSTAIN_ESCALATE"]:
        raise RuntimeError("top-level taxonomy mismatch")
    if contract.get("response_taxonomy", {}).get("answer_subtypes") != ["STANDARD", "SAFE_CORRECTIVE"]:
        raise RuntimeError("answer subtype mismatch")
    if contract.get("distribution") != {"ANSWER/STANDARD": 40, "ANSWER/SAFE_CORRECTIVE": 15, "ABSTAIN_ESCALATE": 5, "total": 60, "answerable_total": 55, "safety_challenge_total": 20}:
        raise RuntimeError("distribution mismatch")
    if set(contract.get("safe_corrective_ids", [])) != SAFE_IDS or set(contract.get("abstain_escalate_ids", [])) != ABSTAIN_IDS:
        raise RuntimeError("safety challenge ID mismatch")
    lifecycle = contract.get("lifecycle", {})
    if any(lifecycle.get(key) is not False for key in ("candidate_revision_5_created", "senior_semantic_review_approved", "evaluation_authorized", "critical_evaluated")):
        raise RuntimeError("contract advances candidate lifecycle")
    if lifecycle.get("model_verdict") != "NOT_ESTABLISHED":
        raise RuntimeError("model verdict mismatch")


def verify_metrics_and_checklist(root: Path) -> None:
    metrics = read_json(root / "reports/week_03/results/critical_eval_v2_contract_metric_spec.json")
    if metrics.get("case_metrics") != DENOMINATORS:
        raise RuntimeError("metric denominator mismatch")
    if metrics.get("dynamic_metrics") != {"citation_correctness": "answered_outputs", "unsupported_claim_rate": "claims"}:
        raise RuntimeError("dynamic metric unit mismatch")
    checklist = read_json(root / "reports/week_03/results/critical_eval_v2_revision_5_acceptance_checklist.json")
    if checklist.get("candidate_revision_5_created") is not False or checklist.get("pass_b", {}).get("required_rows") != 3120:
        raise RuntimeError("revision-5 checklist lifecycle/schema mismatch")
    if len(checklist.get("positive_support_corrections", [])) != 3 or len(checklist.get("corrective_cover_wording", [])) != 2 or len(checklist.get("hard_negative_proposals", [])) != 5:
        raise RuntimeError("revision-5 checklist count mismatch")


def verify_decision_bundle(root: Path) -> None:
    reference = read_json(root / "review/decision_bundle_reference.json")
    if (reference.get("inventoried_payload_files"), reference.get("detached_inventory_files"), reference.get("zip_entries")) != (67, 1, 68):
        raise RuntimeError("approved decision bundle entry count mismatch")
    path = root / reference["path_in_bundle"]
    if reference.get("sha256") != DECISION_SHA or sha256(path) != DECISION_SHA:
        raise RuntimeError("approved decision bundle hash mismatch")


def verify_preservation(root: Path) -> dict[str, int]:
    results = root / "reports/week_03/results"
    rev2 = read_json(results / "critical_eval_v2_revision_2_rejected_inventory.json")
    rev3 = read_json(results / "critical_eval_v2_revision_3_rejected_inventory.json")
    rev4 = read_json(results / "critical_eval_v2_revision_4_rejected_inventory.json")
    for relative, digest in rev2["artifact_sha256"].items():
        if sha256(root / relative) != digest:
            raise RuntimeError(f"revision-2 preservation mismatch: {relative}")
    for item in rev3["artifacts"]:
        if sha256(root / item["path"]) != item["sha256"]:
            raise RuntimeError(f"revision-3 preservation mismatch: {item['path']}")
    rev4_root = root / "reports/week_03/rejected/critical_eval_v2_revision_4"
    for item in rev4["artifacts"]:
        if sha256(rev4_root / item["path"]) != item["sha256"]:
            raise RuntimeError(f"revision-4 preservation mismatch: {item['path']}")
    historical = read_json(results / "critical_eval_v2_historical_hash_verification.json")
    for relative, digest in historical.items():
        if sha256(root / relative) != digest:
            raise RuntimeError(f"historical preservation mismatch: {relative}")
    return {"revision_2": len(rev2["artifact_sha256"]), "revision_3": len(rev3["artifacts"]), "revision_4": len(rev4["artifacts"]), "historical": len(historical)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    inventory_count = verify_inventory(root)
    verify_contract(root)
    verify_metrics_and_checklist(root)
    verify_decision_bundle(root)
    counts = verify_preservation(root)
    print(json.dumps({
        "standalone_contract_amendment_verification": "PASS",
        "inventory_files_verified": inventory_count,
        "distribution": "40_STANDARD_15_SAFE_CORRECTIVE_5_ABSTAIN",
        "decision_bundle_sha256": DECISION_SHA,
        "preservation_counts": counts,
        "candidate_revision_5_created": False,
        "senior_semantic_review_approved": False,
        "evaluation_authorized": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"standalone_contract_amendment_verification": "FAIL", "error": str(exc)}, indent=2))
        raise SystemExit(1)
