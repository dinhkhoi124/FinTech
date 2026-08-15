"""Detached verifier for the R15-F5-F1 finalization hash closure bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


REAL_A16 = "8de0061ed3f4e421353a3c47a733ab081bfccd88"
REAL_STATE_SHA256 = "7b221a4c35878a1aa597220e8e089d090bc9317f39b6201872cfa7c5f04387bd"
REAL_COMPARISON_SHA256 = "3476317b6946f703b43375f039e3b4f25d777c42e7c055698d490585c5e9cb80"
REAL_POSTEVAL_RECEIPT_SHA256 = "9d258ee17f64b930f092a7c6502f0e475405ed4773aab05e2cc06257070583d8"
A17_PATHS = sorted((
    "reports/week_03/results/critical_eval_v2_evaluation_authorization.json",
    "PROJECT_STATE.md", "TASKS.md", "reports/week_03/week_03_summary.md",
    "reports/week_03/daily/2026-08-13.md",
))


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(data: bytes):
    return json.loads(data.decode("utf-8"))


def run(*args: str, cwd: Path) -> str:
    return subprocess.run(args, cwd=cwd, check=True, text=True, capture_output=True).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    checks: dict[str, bool] = {}
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        checks["safe_archive_paths"] = all(
            not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts
            for name in names
        )
        members = {name: archive.read(name) for name in names}
    inventory = load(members["inventory.json"])
    expected_inventory = {
        row["path"]: (row["bytes"], row["sha256"]) for row in inventory["files"]
    }
    actual_inventory = {
        name: (len(data), digest(data)) for name, data in members.items() if name != "inventory.json"
    }
    checks["inventory_exact"] = inventory.get("status") == "PASS" and expected_inventory == actual_inventory
    metadata = load(members["bundle_metadata.json"])
    checks["real_base_exact"] = metadata.get("real_head") == REAL_A16
    checks["real_repository_not_mutated"] = metadata.get("real_repository_mutated") is False and metadata.get("real_finalization_executed") is False
    proposed = load(members["evidence/proposed_manifest.json"])
    checks["proposed_bytes_exact"] = all(
        members[f"proposed/{path}"] and len(members[f"proposed/{path}"]) == record["bytes"]
        and digest(members[f"proposed/{path}"]) == record["sha256"]
        for path, record in proposed.items()
    )
    real = load(members["evidence/real_evidence_hashes.json"])
    expected_real = {
        "reports/week_03/results/critical_eval_v2_execution_state.json": REAL_STATE_SHA256,
        "reports/week_03/results/critical_eval_v2_revision_7_reproduction_comparison.json": REAL_COMPARISON_SHA256,
        "reports/week_03/results/critical_eval_v2_revision_15_f4_posteval_continuation_receipt.json": REAL_POSTEVAL_RECEIPT_SHA256,
    }
    checks["real_evidence_exact"] = all(real[path]["sha256"] == value for path, value in expected_real.items())
    defect = load(members["evidence/defect_reproduction.json"])
    checks["bug_reproduced"] = (
        defect.get("status") == "PASS" and defect.get("finalize_status") == "PASS"
        and defect.get("verify_results_status") == "FAIL"
        and defect.get("buggy_final_summary_sha256") == "4e38d14512bcf41ea4c4c209a7f14dcbd9c8c361b7a90e9b53796d97cf4e3bb9"
        and defect.get("buggy_finalized_state_sha256") == "7b45821bcd84ba8b3579de73f7c28059b2378ff2b3dead866a1a4389f6fa3982"
    )
    negatives = load(members["evidence/negative_controls.json"])
    checks["negative_controls_14_of_14"] = negatives.get("status") == "PASS" and negatives.get("detected") == negatives.get("total") == 14 and all(row.get("status") == "PASS" for row in negatives.get("controls", []))
    topology = load(members["synthetic/topology.json"])
    summary = load(members["synthetic/final_summary.json"])
    state_before = load(members["synthetic/state_before.json"])
    migrated = load(members["synthetic/state_post_migration.json"])
    finalized = load(members["synthetic/finalized_state.json"])
    receipt = load(members["synthetic/postverify_receipt.json"])
    verified = load(members["synthetic/verify_results.json"])
    checks["continuation_preserves_history11"] = state_before["state"] == migrated["state"] == "REPRO_VERIFIED" and len(state_before["history"]) == 11 and state_before["history"] == migrated["history"]
    checks["continuation_receipt_pass"] = receipt.get("status_history") == ["PREPARED", "PASS"] and receipt.get("repaired_state_sha256") == digest((json.dumps(migrated, indent=2, sort_keys=True) + "\n").encode())
    checks["comparison_unchanged"] = real["reports/week_03/results/critical_eval_v2_revision_7_reproduction_comparison.json"]["sha256"] == REAL_COMPARISON_SHA256
    checks["finalized_history12"] = finalized.get("state") == "FINALIZED" and len(finalized.get("history", [])) == 12 and {key: finalized["history"][11].get(key) for key in ("from", "action", "to")} == {"from": "REPRO_VERIFIED", "action": "finalize", "to": "FINALIZED"}
    checks["no_state_summary_hash_cycle"] = "reports/week_03/results/critical_eval_v2_execution_state.json" not in summary.get("artifact_sha256", {}) and summary.get("pre_finalization_state_sha256") == receipt.get("repaired_state_sha256")
    expected_direct = {
        "reports/week_03/results/critical_eval_v2_revision_7_reproduction_comparison.json",
        "reports/week_03/results/critical_eval_v2_revision_7_primary_outcomes.jsonl",
        "reports/week_03/results/critical_eval_v2_revision_7_primary_metrics.json",
        "reports/week_03/results/critical_eval_v2_revision_7_primary_claim_audit.jsonl",
        "reports/week_03/results/critical_eval_v2_revision_7_reproduction_outcomes.jsonl",
        "reports/week_03/results/critical_eval_v2_revision_7_reproduction_metrics.json",
        "reports/week_03/results/critical_eval_v2_revision_7_reproduction_claim_audit.jsonl",
    }
    checks["final_direct_input_exact"] = set(summary.get("direct_input_sha256", {})) == expected_direct == set(finalized["history"][11]["direct_input_sha256"])
    checks["final_summary_semantics"] = summary.get("task_id") == "W3-002-CR1-EA1" and summary.get("critical_evaluated") is True and summary.get("primary_reproduction_identical") is True and summary.get("model_verdict") == "AWAITING_SENIOR_RESULT_REVIEW"
    checks["verify_results_pass"] = verified.get("status") == "PASS"
    boundary = load(members["synthetic/execution_boundary.json"])
    checks["zero_runtime_calls"] = boundary.get("status") == "PASS" and all(boundary.get(key) == 0 for key in ("model_calls", "encoder_calls", "retrieval_calls", "generation_calls", "evaluator_calls", "comparator_calls"))

    with tempfile.TemporaryDirectory(prefix="ea1_r15_f5_f1_verify_") as temporary:
        temp = Path(temporary)
        history_bundle = temp / "history.bundle"
        history_bundle.write_bytes(members["synthetic/r15_f5_f1_a17_history.bundle"])
        repo = temp / "repo"
        run("git", "clone", str(history_bundle), str(repo), cwd=temp)
        f5, a17 = topology["r15_f5_f1_commit"], topology["a17_commit"]
        checks["f5_parent_real_a16"] = run("git", "rev-parse", f"{f5}^", cwd=repo) == REAL_A16
        checks["a17_parent_f5"] = run("git", "rev-parse", f"{a17}^", cwd=repo) == f5
        changed = sorted(run("git", "diff", "--name-only", f"{f5}..{a17}", cwd=repo).splitlines())
        checks["a17_scope_exact"] = changed == A17_PATHS == sorted(topology["a17_changed_paths"])
        checks["proposed_match_f5_git_objects"] = all(
            subprocess.check_output(["git", "-C", str(repo), "show", f"{f5}:{path}"]) == members[f"proposed/{path}"]
            for path in proposed
        )
    status = "PASS" if all(checks.values()) else "FAIL"
    print(json.dumps({"status": status, "bundle_sha256": digest(bundle.read_bytes()), "checks": checks}, indent=2, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
