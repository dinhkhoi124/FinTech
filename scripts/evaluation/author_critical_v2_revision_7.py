"""Author the Senior-adjudicated critical_eval_v2 candidate revision 7.

This command performs deterministic candidate authoring only.  It never imports
or invokes classifier, retriever, generator, encoder, or model runtime code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


PREDECESSOR_COMMIT = "d27de987d0eb7a942c88590eec9a30bdd6ee33d8"
PREDECESSOR_MANIFEST_SHA256 = "2f42fb4ff7159ef2735ce88418b0dbfcc414b0091476f1882a83d13e807002ad"
COV1_BUNDLE_SHA256 = "b804fa12a4bc6f12e3852552358a29af9e071e916c92b22959fefc6ff8a629ff"
REVIEWER_STATUS = "CANDIDATE_REVISION_7_AUTHOR_REVIEW_COMPLETE_AWAITING_SENIOR"
AUTHORING_SOURCE = "STANDALONE_SECTION_CONTENT_REVIEW_REVISION_7_COV1"
REASON_CODE = "REVISION_7_COV1_QUERY_OBLIGATION_SECTION_CONTENT_REVIEW"

FOUR_DELTAS = {
    ("Q_V2_A_TRD01", "POL_TRANSFER_DECLINED_001#eligibility"): (["STATE", "BOUNDARY"], ["STATE"]),
    ("Q_V2_A_TRD01", "RUN_TRANSFER_DECLINED_001#checks"): (["STATE", "BOUNDARY"], ["STATE"]),
    ("Q_V2_A_TRR02", "ESC_TRANSFER_RECIPIENT_001#trigger"): (["WINDOW", "TRACE"], ["WINDOW"]),
    ("Q_V2_A_CSU03", "ESC_CASH_UNRECOG_001#safe_handoff"): (["PROHIBIT", "MINIMAL"], ["MINIMAL"]),
}

CUSTOM_RATIONALES = {
    ("Q_V2_A_TRD01", "POL_TRANSFER_DECLINED_001#eligibility"): (
        "Revision-7 COV1 Senior adjudication Q_V2_A_TRD01 / POL_TRANSFER_DECLINED_001#eligibility: "
        "the section directly establishes explicit pre-processing refusal (STATE), but rail identity and timing do not "
        "directly exclude a post-submission technical failure; BOUNDARY is therefore not credited."
    ),
    ("Q_V2_A_TRD01", "RUN_TRANSFER_DECLINED_001#checks"): (
        "Revision-7 COV1 Senior adjudication Q_V2_A_TRD01 / RUN_TRANSFER_DECLINED_001#checks: "
        "the section directly establishes rail plus pre-processing declined state (STATE), but does not directly "
        "exclude a post-submission technical failure; BOUNDARY is therefore not credited."
    ),
    ("Q_V2_A_TRR02", "ESC_TRANSFER_RECIPIENT_001#trigger"): (
        "Revision-7 COV1 Senior adjudication Q_V2_A_TRR02 / ESC_TRANSFER_RECIPIENT_001#trigger: "
        "the section directly establishes the one-business-day escalation window (WINDOW), but escalation eligibility "
        "does not directly state when a synthetic trace may open; TRACE is therefore not credited."
    ),
    ("Q_V2_A_CSU03", "ESC_CASH_UNRECOG_001#safe_handoff"): (
        "Revision-7 COV1 Senior adjudication Q_V2_A_CSU03 / ESC_CASH_UNRECOG_001#safe_handoff: "
        "the section directly limits collection to a masked event reference (MINIMAL), but 'never credentials' does not "
        "directly enumerate PINs, passwords, one-time codes, and full card details; PROHIBIT is therefore not credited."
    ),
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8", newline="\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git_show(root: Path, relative: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{PREDECESSOR_COMMIT}:{relative}"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def git_json(root: Path, relative: str) -> dict[str, Any]:
    return json.loads(git_show(root, relative).decode("utf-8"))


def git_jsonl(root: Path, relative: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in git_show(root, relative).decode("utf-8").splitlines() if line.strip()]


def semantic_signature(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "support_class": row["support_class"],
        "supported_requested_obligation_ids": row.get("supported_requested_obligation_ids", []),
        "supported_corrective_obligation_ids": row.get("supported_corrective_obligation_ids", []),
        "hard_negative_review": row.get("hard_negative_review"),
    }


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def mapping_slice(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "query_id": row["query_id"],
        "requested_obligations": row["requested_obligations"],
        "complete_requested_answer_covers": row["complete_requested_answer_covers"],
        "all_minimal_covers": row["all_minimal_covers"],
        "minimum_evidence_section_cover_size": row["minimum_evidence_section_cover_size"],
        "minimum_distinct_document_cover_size": row["minimum_distinct_document_cover_size"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--cov1-bundle",
        type=Path,
        default=Path("../W3-002-CR1_complete_cover_consistency_review_bundle.zip"),
    )
    args = parser.parse_args()
    root = args.root.resolve()
    cov1 = args.cov1_bundle.resolve()
    sys.path.insert(0, str(root / "src"))

    from payresolve_ai.evaluation import critical_v2 as cv2

    config_path = root / "configs/evaluation/critical_eval_v2.json"
    if sha256(cov1) != COV1_BUNDLE_SHA256:
        raise RuntimeError("COV1 bundle hash mismatch")
    manifest_relative = "reports/week_03/results/critical_eval_v2_candidate_manifest.json"
    predecessor_manifest_bytes = git_show(root, manifest_relative)
    if sha256_bytes(predecessor_manifest_bytes) != PREDECESSOR_MANIFEST_SHA256:
        raise RuntimeError("revision-6 predecessor manifest hash mismatch")
    predecessor_manifest = json.loads(predecessor_manifest_bytes.decode("utf-8"))
    actual_predecessor = {path: sha256_bytes(git_show(root, path)) for path in predecessor_manifest["artifact_sha256"]}
    if actual_predecessor != predecessor_manifest["artifact_sha256"] or len(actual_predecessor) != 18:
        raise RuntimeError("revision-6 predecessor artifacts are not 18/18 unchanged")

    config = git_json(root, "configs/evaluation/critical_eval_v2.json")
    if config.get("candidate_revision") != 6:
        raise RuntimeError("authoring requires active revision-6 predecessor bytes")
    old_pass_a = git_jsonl(root, config["outputs"]["pass_a"])
    old_scenarios = git_jsonl(root, config["outputs"]["scenarios"])
    old_pass_b = git_jsonl(root, config["outputs"]["pass_b"])
    old_mapping = git_jsonl(root, config["outputs"]["pass_c"])
    old_support_counts = dict(Counter(row["support_class"] for row in old_pass_b))

    config["candidate_revision"] = 7
    config["candidate_id"] = "critical_eval_v2_candidate_revision_7"
    config["outputs"].pop("revision_6_corrections")
    config["outputs"].update({
        "cov1_senior_adjudication": "reports/week_03/results/critical_eval_v2_cov1_senior_adjudication.json",
        "revision_7_corrections": "reports/week_03/results/critical_eval_v2_revision_7_corrections.json",
        "revision_7_semantic_delta": "reports/week_03/results/critical_eval_v2_revision_7_semantic_delta.json",
        "revision_7_mapping_comparison": "reports/week_03/results/critical_eval_v2_revision_7_mapping_comparison.json",
        "revision_7_model_input_comparison": "reports/week_03/results/critical_eval_v2_revision_7_model_input_comparison.json",
        "revision_7_complete_cover_derivation": "reports/week_03/results/critical_eval_v2_revision_7_complete_cover_derivation.json",
    })
    old_correction = "reports/week_03/results/critical_eval_v2_revision_6_corrections.json"
    config["candidate_artifacts"] = [path for path in config["candidate_artifacts"] if path != old_correction]
    config["candidate_artifacts"].extend([
        config["outputs"]["cov1_senior_adjudication"],
        config["outputs"]["revision_7_corrections"],
        config["outputs"]["revision_7_semantic_delta"],
        config["outputs"]["revision_7_mapping_comparison"],
        config["outputs"]["revision_7_model_input_comparison"],
        config["outputs"]["revision_7_complete_cover_derivation"],
    ])
    write_json(config_path, config)

    scenarios = [{**row, "candidate_revision": 7} for row in old_scenarios]
    pass_a = []
    for row in old_pass_a:
        updated = {**row, "candidate_revision": 7}
        updated["candidate_authoring_rationale"] = row["candidate_authoring_rationale"].replace(
            "revision 6", "revision 7 after COV1 Senior adjudication"
        )
        pass_a.append(updated)
    write_jsonl(root / config["outputs"]["scenarios"], scenarios)
    write_jsonl(root / config["outputs"]["pass_a"], pass_a)
    pass_a_old_semantics = [{k: v for k, v in row.items() if k not in {"candidate_revision", "candidate_authoring_rationale"}} for row in old_pass_a]
    pass_a_new_semantics = [{k: v for k, v in row.items() if k not in {"candidate_revision", "candidate_authoring_rationale"}} for row in pass_a]
    scenario_old_semantics = [{k: v for k, v in row.items() if k != "candidate_revision"} for row in old_scenarios]
    scenario_new_semantics = [{k: v for k, v in row.items() if k != "candidate_revision"} for row in scenarios]
    if pass_a_old_semantics != pass_a_new_semantics or scenario_old_semantics != scenario_new_semantics:
        raise RuntimeError("Pass A or scenario semantics changed")

    model_rows = []
    for old, new in zip(old_pass_a, pass_a, strict=True):
        if old["query_id"] != new["query_id"]:
            raise RuntimeError("query order changed")
        model_rows.append({
            "query_id": old["query_id"],
            "model_input_contract_version": old["model_input_contract_version"],
            "revision_6_model_input_text": old["model_input_text"],
            "revision_6_model_input_sha256": old["model_input_sha256"],
            "revision_7_model_input_text": new["model_input_text"],
            "revision_7_model_input_sha256": new["model_input_sha256"],
            "identical": (
                old["model_input_text"], old["model_input_sha256"], old["model_input_contract_version"]
            ) == (
                new["model_input_text"], new["model_input_sha256"], new["model_input_contract_version"]
            ),
        })
    model_comparison = {
        "task_id": "W3-002-CR1",
        "predecessor_candidate_revision": 6,
        "candidate_revision": 7,
        "predecessor_candidate_commit": PREDECESSOR_COMMIT,
        "predecessor_manifest_sha256": PREDECESSOR_MANIFEST_SHA256,
        "query_count": len(model_rows),
        "changed_count": sum(not row["identical"] for row in model_rows),
        "all_identical": all(row["identical"] for row in model_rows),
        "rows": model_rows,
    }
    if model_comparison["query_count"] != 60 or not model_comparison["all_identical"]:
        raise RuntimeError("model-input freeze changed")
    write_json(root / config["outputs"]["revision_7_model_input_comparison"], model_comparison)

    eligible, _ = cv2._catalog(root, config)
    pass_a_by_id = {row["query_id"]: row for row in pass_a}
    pass_b = []
    semantic_changes = []
    for old in old_pass_b:
        row = dict(old)
        key = (row["query_id"], row["evidence_id"])
        row["candidate_revision"] = 7
        row["reviewer_status"] = REVIEWER_STATUS
        row["authoring_source"] = AUTHORING_SOURCE
        row["reason_code"] = REASON_CODE
        row["rationale"] = row["rationale"].replace("Revision-6 author review", "Revision-7 COV1-bound retained review")
        if key in FOUR_DELTAS:
            expected_old, expected_new = FOUR_DELTAS[key]
            if old["supported_requested_obligation_ids"] != expected_old or old["support_class"] != "DIRECT_SUPPORT":
                raise RuntimeError(f"unexpected predecessor semantics for {key}")
            row["supported_requested_obligation_ids"] = expected_new
            row["rationale"] = CUSTOM_RATIONALES[key]
        row["review_input_sha256"] = cv2.review_input_sha256(pass_a_by_id[row["query_id"]], eligible[row["evidence_id"]])
        if semantic_signature(old) != semantic_signature(row):
            semantic_changes.append({
                "query_id": row["query_id"],
                "evidence_id": row["evidence_id"],
                "revision_6": semantic_signature(old),
                "revision_7": semantic_signature(row),
                "senior_adjudication": "CANDIDATE_COVER_SEMANTIC_DEFECT_CONFIRMED",
            })
        pass_b.append(row)
    if {(r["query_id"], r["evidence_id"]) for r in semantic_changes} != set(FOUR_DELTAS):
        raise RuntimeError("semantic Pass-B delta is not exactly the four Senior rows")
    write_jsonl(root / config["outputs"]["pass_b"], pass_b)

    prohibited = git_jsonl(root, config["outputs"]["prohibited_target_review"])
    for row in prohibited:
        row["candidate_revision"] = 7
        row["reviewer_status"] = REVIEWER_STATUS
        row["reviewer_rationale"] = row["reviewer_rationale"].replace("revision-6", "revision-7")
        row["review_input_sha256"] = cv2.prohibited_target_review_input_sha256(pass_a_by_id[row["query_id"]])
    write_jsonl(root / config["outputs"]["prohibited_target_review"], prohibited)

    old_forbidden = git_jsonl(root, config["outputs"]["forbidden_audit"])
    forbidden = [dict(row) for row in old_forbidden]
    for row in forbidden:
        row["candidate_revision"] = 7
        row["reviewer_status"] = REVIEWER_STATUS
    forbidden_old_semantics = [{k: v for k, v in row.items() if k not in {"candidate_revision", "reviewer_status"}} for row in old_forbidden]
    forbidden_new_semantics = [{k: v for k, v in row.items() if k not in {"candidate_revision", "reviewer_status"}} for row in forbidden]
    if forbidden_old_semantics != forbidden_new_semantics:
        raise RuntimeError("forbidden-evidence audit semantics changed")
    write_jsonl(root / config["outputs"]["forbidden_audit"], forbidden)
    categories = git_jsonl(root, config["outputs"]["negative_category_quality_audit"])
    for row in categories:
        row["candidate_revision"] = 7
        row["reviewer_status"] = REVIEWER_STATUS
        row["reviewer_rationale"] = row["reviewer_rationale"].replace("Revision 6", "Revision 7")
    write_jsonl(root / config["outputs"]["negative_category_quality_audit"], categories)

    cv2.validate_pass_a(pass_a)
    cv2.validate_pass_b(pass_a, pass_b, eligible)
    mappings, _, hard_audits = cv2.derive_pass_c(pass_a, pass_b, prohibited)
    hard_negative_pairs = sorted((row["query_id"], row["evidence_id"]) for row in hard_audits)
    if set(hard_negative_pairs) != cv2.HARD_NEGATIVE_PROPOSALS:
        raise RuntimeError("hard-negative set changed")
    old_mapping_by_id = {row["query_id"]: row for row in old_mapping}
    new_mapping_by_id = {row["query_id"]: row for row in mappings}
    comparison_rows = [
        {
            "query_id": query_id,
            "revision_6": mapping_slice(old_mapping_by_id[query_id]),
            "revision_7": mapping_slice(new_mapping_by_id[query_id]),
        }
        for query_id in ("Q_V2_A_TRD01", "Q_V2_A_TRR02", "Q_V2_A_CSU03")
    ]
    mapping_comparison = {
        "task_id": "W3-002-CR1",
        "from_revision": 6,
        "to_revision": 7,
        "derived_mechanically_from_corrected_pass_b": True,
        "rows": comparison_rows,
    }
    write_json(root / config["outputs"]["revision_7_mapping_comparison"], mapping_comparison)

    total_covers = sum(
        len(row["complete_requested_answer_covers"]) + len(row["complete_corrective_answer_covers"])
        for row in mappings
    )
    cover_proof = {
        "candidate_revision": 7,
        "total_complete_covers": total_covers,
        "invalid_revision_6_covers_absent": {
            "TRD01_POL": ["POL_TRANSFER_DECLINED_001#eligibility"] not in new_mapping_by_id["Q_V2_A_TRD01"]["complete_requested_answer_covers"],
            "TRD01_RUN": ["RUN_TRANSFER_DECLINED_001#checks"] not in new_mapping_by_id["Q_V2_A_TRD01"]["complete_requested_answer_covers"],
            "TRR02_ESC": ["ESC_TRANSFER_RECIPIENT_001#trigger"] not in new_mapping_by_id["Q_V2_A_TRR02"]["complete_requested_answer_covers"],
            "CSU03_ESC_SINGLE": ["ESC_CASH_UNRECOG_001#safe_handoff"] not in new_mapping_by_id["Q_V2_A_CSU03"]["complete_requested_answer_covers"],
        },
        "replacement_covers_present": {
            "TRD01_FAQ": ["FAQ_TRANSFER_DECLINED_001#answer"] in new_mapping_by_id["Q_V2_A_TRD01"]["complete_requested_answer_covers"],
            "TRR02_FAQ": ["FAQ_TRANSFER_RECIPIENT_002#current_window"] in new_mapping_by_id["Q_V2_A_TRR02"]["complete_requested_answer_covers"],
            "TRR02_POL": ["POL_TRANSFER_RECIPIENT_001#trace_window"] in new_mapping_by_id["Q_V2_A_TRR02"]["complete_requested_answer_covers"],
            "CSU03_POL_ESC": sorted(["POL_CASH_UNRECOG_001#prohibited_actions", "ESC_CASH_UNRECOG_001#safe_handoff"]) in [sorted(x) for x in new_mapping_by_id["Q_V2_A_CSU03"]["complete_requested_answer_covers"]],
            "CSU03_POL_RUN": sorted(["POL_CASH_UNRECOG_001#prohibited_actions", "RUN_CASH_UNRECOG_002#safe_handoff"]) in [sorted(x) for x in new_mapping_by_id["Q_V2_A_CSU03"]["complete_requested_answer_covers"]],
        },
    }
    if total_covers != 92 or not all(cover_proof["invalid_revision_6_covers_absent"].values()) or not all(cover_proof["replacement_covers_present"].values()):
        raise RuntimeError(f"complete-cover derivation blocker: {cover_proof}")
    write_json(root / config["outputs"]["revision_7_complete_cover_derivation"], cover_proof)

    adjudication = {
        "task_id": "W3-002-CR1-COV1",
        "cov1_bundle_sha256": COV1_BUNDLE_SHA256,
        "total_complete_covers_reviewed": 94,
        "consistent": 84,
        "inconsistent": 10,
        "senior_adjudication_counts": {
            "EVALUATOR_RULE_INCOMPLETE": 6,
            "CANDIDATE_COVER_SEMANTIC_DEFECT_CONFIRMED": 4,
            "AMBIGUOUS": 0,
        },
        "candidate_defect_rows": semantic_changes,
        "revision_6_historical_semantic_approval": True,
        "revision_6_evaluation_authorization_eligibility": "SUPERSEDED_BY_COV1",
        "revision_6_evaluation_authorized": False,
        "candidate_revision_7_authoring_authorized": True,
        "candidate_revision_7_senior_approved": False,
    }
    adjudication_path = root / config["outputs"]["cov1_senior_adjudication"]
    write_json(adjudication_path, adjudication)
    decision_md = root / "reports/week_03/decisions/W3-002-CR1_COV1_senior_adjudication.md"
    decision_md.parent.mkdir(parents=True, exist_ok=True)
    decision_md.write_text(
        "# W3-002-CR1-COV1 Senior adjudication\n\n"
        "- Task: `W3-002-CR1-COV1`\n"
        f"- COV1 bundle SHA-256: `{COV1_BUNDLE_SHA256}`\n"
        "- Covers reviewed: 94; consistent: 84; inconsistent: 10\n"
        "- Senior result: 6 `EVALUATOR_RULE_INCOMPLETE`, 4 "
        "`CANDIDATE_COVER_SEMANTIC_DEFECT_CONFIRMED`, 0 ambiguous\n\n"
        "Revision 6 was `SEMANTICALLY_APPROVED_AT_THE_TIME` and is now "
        "`SUPERSEDED_PRE_EVALUATION_BY_COV1`. It was never evaluation-authorized. "
        "Candidate Revision 7 authoring is authorized, but Revision 7 is not Senior-approved.\n\n"
        "The four candidate defects are the two TRD01 BOUNDARY assignments, the TRR02 TRACE "
        "assignment, and the CSU03 PROHIBIT assignment described in the bound JSON record. "
        "The six evaluator-only findings remain deferred and candidate semantics are unchanged for them.\n",
        encoding="utf-8",
        newline="\n",
    )

    support_counts = dict(Counter(row["support_class"] for row in pass_b))
    semantic_delta = {
        "task_id": "W3-002-CR1",
        "candidate_revision": 7,
        "changed_semantic_pass_b_rows": len(semantic_changes),
        "unexpected_semantic_pass_b_rows": 0,
        "semantic_changes": semantic_changes,
        "all_other_semantic_pass_b_rows_unchanged": True,
        "support_class_counts_revision_6": old_support_counts,
        "support_class_counts_revision_7": support_counts,
    }
    if support_counts != old_support_counts:
        raise RuntimeError("Pass-B support-class distribution changed")
    write_json(root / config["outputs"]["revision_7_semantic_delta"], semantic_delta)

    comparison = {
        "task_id": "W3-002-CR1",
        "from_revision": 6,
        "to_revision": 7,
        "revision_6_status": "SEMANTICALLY_APPROVED_AT_THE_TIME / SUPERSEDED_PRE_EVALUATION_BY_COV1",
        "model_input_changed_count": 0,
        "response_contract": "40 ANSWER/STANDARD / 15 ANSWER/SAFE_CORRECTIVE / 5 ABSTAIN_ESCALATE",
        "pass_b_semantic_changes": semantic_changes,
        "changed_semantic_pass_b_rows": 4,
        "unexpected_semantic_pass_b_rows": 0,
        "all_other_pass_b_semantics_preserved": True,
        "support_class_counts": {"revision_6": old_support_counts, "revision_7": support_counts},
        "hard_negative_count": {"revision_6": 5, "revision_7": 5},
        "total_complete_covers": {"revision_6": 94, "revision_7": total_covers},
    }
    write_json(root / config["outputs"]["revision_comparison"], comparison)

    corrections = {
        "task_id": "W3-002-CR1",
        "candidate_revision": 7,
        "candidate_id": "critical_eval_v2_candidate_revision_7",
        "cov1_bundle_sha256": COV1_BUNDLE_SHA256,
        "senior_adjudication_record_sha256": sha256(adjudication_path),
        "predecessor_candidate_revision": 6,
        "predecessor_candidate_commit": PREDECESSOR_COMMIT,
        "predecessor_manifest_sha256": PREDECESSOR_MANIFEST_SHA256,
        "exact_four_pass_b_semantic_changes": semantic_changes,
        "changed_semantic_pass_b_rows": 4,
        "unexpected_semantic_pass_b_rows": 0,
        "derived_mapping_comparison_sha256": sha256(root / config["outputs"]["revision_7_mapping_comparison"]),
        "model_input_comparison_sha256": sha256(root / config["outputs"]["revision_7_model_input_comparison"]),
        "complete_cover_derivation_sha256": sha256(root / config["outputs"]["revision_7_complete_cover_derivation"]),
        "model_inputs_unchanged": "60/60",
        "distribution_unchanged": "40 ANSWER_STANDARD / 15 ANSWER_SAFE_CORRECTIVE / 5 ABSTAIN_ESCALATE",
        "support_class_distribution_unchanged": support_counts,
        "hard_negative_count": 5,
        "hard_negative_pairs": hard_negative_pairs,
        "hard_negative_set_unchanged": True,
        "pass_a_semantics_unchanged": True,
        "scenario_semantics_unchanged": True,
        "pass_a_semantic_projection_sha256": stable_hash(pass_a_new_semantics),
        "scenario_semantic_projection_sha256": stable_hash(scenario_new_semantics),
        "forbidden_evidence_semantics_unchanged": True,
        "forbidden_evidence_semantic_projection_sha256": stable_hash(forbidden_new_semantics),
        "evaluation_authorized": False,
        "critical_evaluated": False,
        "model_loaded": False,
        "retrieval_executed": False,
        "generation_executed": False,
        "inference_executed": False,
        "evaluation_executed": False,
    }
    write_json(root / config["outputs"]["revision_7_corrections"], corrections)

    overlap, _ = cv2.recompute_overlap(root, config, pass_a)
    write_json(root / config["outputs"]["overlap_audit"], overlap)
    manifest = cv2.freeze_revision_7(root, config_path)
    print(json.dumps({
        "status": "PASS",
        "candidate_revision": manifest["candidate_revision"],
        "predecessor_artifacts_verified": len(actual_predecessor),
        "changed_semantic_pass_b_rows": len(semantic_changes),
        "unexpected_semantic_pass_b_rows": 0,
        "total_complete_covers": total_covers,
        "support_class_counts": support_counts,
        "model_inputs_unchanged": 60,
        "distribution": "40/15/5",
        "hard_negative_count": manifest["hard_negative_count"],
        "evaluation_authorized": manifest["evaluation_authorized"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
