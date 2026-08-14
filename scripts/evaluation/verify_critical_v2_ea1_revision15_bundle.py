"""Detached verifier for the R15 evaluation-state closure bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


LOCKED = {
    "V0_raw": "c27ff7a80d3ed2214fca647ce46091a7ed2c8029ff0b8527fcad8d3e36844ab2",
    "V1_raw": "dff680373ff943adfe6379eb59add82b95254670653646ffc4abd946e562a608",
    "V2_raw": "943c4a7a1bc3e0d305962751256c1723d4e18ff8dd84b63fdd5b520532418a35",
    "raw_manifest": "114d29ec72a561886a8effd393510f9365e62f1d3c8783aa9def919fee04e0b3",
    "outcomes": "bb7715af1e22bbe1ce791f344c833358af7075ea6ae02adfc952f615dc1b64ce",
    "metrics": "ef480aae3d4d0f30e306c5fd9c2fb97ce1fe3dafda44c5a5caf7a4e592296c3b",
    "claim_audit": "3d6766797c65c876ce3070cef311587152b68655bd4ad7e88f8f753b754e80ae",
}


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path: Path) -> dict: return json.loads(path.read_text(encoding="utf-8"))


def verify(root: Path) -> dict:
    inventory = read(root / "detached_inventory.json")["files"]
    for row in inventory:
        path = root / row["path"]
        if not path.is_file() or path.stat().st_size != row["bytes"] or sha(path) != row["sha256"]:
            raise RuntimeError(f"inventory mismatch: {row['path']}")
    task = root / "task_files"
    config = read(task / "configs/evaluation/critical_eval_v2_execution.json")
    candidate = read(task / "reports/week_03/results/critical_eval_v2_evaluation_authorization_candidate.json")
    if config["readiness_revision"] != 15 or candidate["readiness_revision"] != 15 or candidate["candidate_revision"] != 7:
        raise RuntimeError("R15/Candidate identity mismatch")
    if candidate["evaluation_authorized"] is not False or candidate["senior_authorization_claimed"] is not False:
        raise RuntimeError("R15 authoring improperly authorizes execution")
    readiness = root / "readiness_files"
    for relative, expected in candidate["execution_artifact_sha256"].items():
        if not (readiness / relative).is_file() or sha(readiness / relative) != expected:
            raise RuntimeError(f"readiness hash mismatch: {relative}")
    primary = read(task / "reports/week_03/results/critical_eval_v2_ea1_revision15_primary_preservation.json")
    if primary["hashes"] != LOCKED or primary["hash_count"] != 7:
        raise RuntimeError("PRIMARY preservation mismatch")
    matrix = read(task / "reports/week_03/results/critical_eval_v2_ea1_revision15_transition_contract_matrix.json")
    if matrix["exact_count"] != 12 or matrix["transition_count"] != 12:
        raise RuntimeError("transition matrix mismatch")
    migration = read(task / "reports/week_03/results/critical_eval_v2_ea1_revision15_isolated_migration.json")
    premodel = read(task / "reports/week_03/results/critical_eval_v2_ea1_revision15_synthetic_premodel.json")
    if migration["status"] != "PASS" or not migration["historical_runtime_preserved"] or not premodel["pre_model_gate_reached"]:
        raise RuntimeError("continuation evidence mismatch")
    if any(premodel[key] for key in ("model_calls", "encoder_calls", "retrieval_calls", "generation_calls")):
        raise RuntimeError("authoring invoked production runtime")
    finding = read(task / "reports/week_03/results/critical_eval_v2_ea1_revision15_f1_authority_finding.json")
    negatives = read(task / "reports/week_03/results/critical_eval_v2_ea1_revision15_f1_negative_controls.json")
    synthetic = read(task / "reports/week_03/results/critical_eval_v2_ea1_revision15_committed_synthetic_a15.json")
    if finding["classification"] != "R15_CONTINUATION_AUTHORITY_NOT_PRODUCTION_BOUND" or finding["status"] != "REMEDIATED":
        raise RuntimeError("F1 finding closure mismatch")
    if negatives["status"] != "PASS" or negatives["required_control_count"] != 16 or negatives["active_mutations"] != 0:
        raise RuntimeError("F1 negative-control mismatch")
    defect = read(task / "reports/week_03/results/critical_eval_v2_ea1_revision15_f2_git_config_defect_reproduction.json")
    isolation = read(task / "reports/week_03/results/critical_eval_v2_ea1_revision15_f2_real_repo_config_isolation.json")
    if (
        defect["classification"] != "R15_SYNTHETIC_WORKTREE_SHARED_CONFIG_MUTATION"
        or defect["status"] != "REPRODUCED_IN_DISPOSABLE_REPOSITORY"
        or not all(row["shared_mutation_proven"] for row in defect["observations"])
    ):
        raise RuntimeError("F2 shared-config defect reproduction mismatch")
    if (
        isolation["status"] != "PASS"
        or not isolation["common_config_bytes_unchanged"]
        or isolation["common_config_sha256_before"] != isolation["common_config_sha256_after"]
        or isolation["persistent_git_config_writes_in_synthetic_topology"] != 0
        or len(isolation["phase_checks"]) != 6
        or not all(row["status"] == "UNCHANGED" for row in isolation["phase_checks"])
    ):
        raise RuntimeError("F2 real-repository config isolation mismatch")
    verified = synthetic["production_verifier"]
    expected_identity = {
        "author_name": "R15 F1 Synthetic",
        "author_email": "r15-f1@example.invalid",
        "committer_name": "R15 F1 Synthetic",
        "committer_email": "r15-f1@example.invalid",
    }
    if (
        synthetic["status"] != "PASS"
        or synthetic["authorization_parent"] != synthetic["readiness_commit"]
        or synthetic["migration_receipt_status"] != "PASS"
        or synthetic["six_input_lineage"] != 6
        or not synthetic["future_runtime_absent"]
        or verified.get("continuation_authorized") is not True
        or synthetic["readiness_identity"] != expected_identity
        or synthetic["authorization_identity"] != expected_identity
    ):
        raise RuntimeError("committed synthetic A15 control mismatch")
    candidate_fields = {
        "continuation_authorized": False,
        "continuation_migration": "R14_PRIMARY_EVALUATED_TO_R15_CONTINUATION",
        "continuation_from_authorization_commit": "1dd7e054f17f9aaf48dca87ba0e00611ca3f2094",
        "continuation_from_readiness_commit": "c0afb7ba74cbcb778a5952399f1db628166df40d",
        "continuation_legacy_state_sha256": "6cab044610b566f4b7c6ecfbcafc5b49868891c167543ef950b20e29710416bd",
        "continuation_legacy_runtime_environment_sha256": "b036b8e337f809817dbbc6006e36d892c63480df2a919d9775279195c85bd22d",
    }
    if any(candidate.get(key) != value for key, value in candidate_fields.items()):
        raise RuntimeError("R15 candidate continuation contract mismatch")
    return {"status": "PASS", "files_verified": len(inventory), "readiness_revision": 15, "readiness_hash_count": len(candidate["execution_artifact_sha256"]), "transition_count": 12, "primary_hash_count": 7}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--bundle-root", type=Path, required=True); args = parser.parse_args()
    print(json.dumps(verify(args.bundle_root.resolve()), indent=2, sort_keys=True)); return 0


if __name__ == "__main__": raise SystemExit(main())
