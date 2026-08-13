"""Build the detached R14 authorization-verifier hardening review bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from scripts.evaluation import build_critical_v2_ea1_revision13_review_bundle as r13


TASK_PATHS = (
    "PROJECT_STATE.md", "TASKS.md",
    "configs/evaluation/critical_eval_v2_authorization_topology.json",
    "configs/evaluation/critical_eval_v2_execution.json",
    "configs/evaluation/critical_eval_v2_execution_state_machine.json",
    "configs/evaluation/critical_eval_v2_metric_contract.json",
    "docs/evaluation/W3-002-CR1-EA1_execution_readiness.md",
    "reports/week_03/daily/2026-08-13.md",
    "reports/week_03/experiments/W3-002-CR1-EA1_execution_readiness.md",
    "reports/week_03/week_03_summary.md",
    "reports/week_03/results/critical_eval_v2_evaluation_authorization_candidate.json",
    "reports/week_03/results/critical_eval_v2_execution_environment.json",
    "reports/week_03/results/critical_eval_v2_execution_readiness_validation.json",
    "reports/week_03/results/critical_eval_v2_future_command_plan.json",
    "reports/week_03/results/critical_eval_v2_runtime_asset_manifest.json",
    "reports/week_03/results/critical_eval_v2_runtime_payload_manifest.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision14_active_control_plane_absence.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision14_authorization_field_enforcement.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision14_environment_recheck.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision14_exact_five_topology_enforcement.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision14_hash_rebinding.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision14_offline_encoder_probe.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision14_runtime_source_closure.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision14_synthetic_authorization.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision14_verifier_gap_lineage.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision14_review_scope_coverage.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision14_verification_summary.json",
    "scripts/evaluation/build_critical_v2_ea1_revision14_review_bundle.py",
    "scripts/evaluation/prepare_critical_v2_ea1_revision14_evidence.py",
    "scripts/evaluation/verify_critical_v2_ea1_revision14_bundle.py",
    "src/payresolve_ai/evaluation/critical_v2_execution.py",
    "tests/test_critical_v2_auth_date_closure.py",
    "tests/test_critical_v2_binding_fix.py",
    "tests/test_critical_v2_execution_revision13.py",
    "tests/test_critical_v2_execution_revision14.py",
    "tests/test_critical_v2_execution_readiness.py",
)
REFERENCES = (
    "reports/week_03/results/critical_eval_v2_candidate_manifest.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision13_environment_contract.json",
    "reports/week_03/results/incident_history/w3-002-cr1-ea1-a12-e1/critical_eval_v2_runtime_execution_environment.json",
    "reports/week_03/results/incident_history/w3-002-cr1-ea1-a12-e1/critical_eval_v2_execution_state.json",
    "reports/week_03/results/incident_history/w3-002-cr1-ea1-a12-e1/preauthorization_reset_receipt.json",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify(root: Path) -> dict:
    task = set(TASK_PATHS)
    rows, unclassified = [], []
    for path in r13.dirty_paths(root):
        if path in task:
            category = "R14_TASK_OWNED_REVIEWED"
        elif path.startswith("reports/week_03/results/incident_history/"):
            category = "PRESERVED_INCIDENT_HISTORY_EXCLUDE"
        elif path.startswith("reports/week_03/review_bundles/") and path.endswith(".zip"):
            category = "REVIEW_ZIP_EXCLUDE"
        elif path in r13.USER_OWNED_EXACT or any(path.startswith(prefix) for prefix in r13.USER_OWNED_PREFIXES):
            category = "USER_OWNED_EXCLUDE"
        else:
            category = "UNCLASSIFIED"
            unclassified.append(path)
        rows.append({"path": path, "category": category})
    if unclassified:
        raise RuntimeError(f"R14_REVIEW_SCOPE_INCOMPLETE: {unclassified}")
    reviewed = sorted(row["path"] for row in rows if row["category"] == "R14_TASK_OWNED_REVIEWED")
    if reviewed != sorted(TASK_PATHS):
        raise RuntimeError(f"R14 task-path mismatch missing={sorted(set(TASK_PATHS)-set(reviewed))}")
    return {"status": "PASS", "dirty_path_count": len(rows), "r14_task_owned_count": len(reviewed),
            "r14_task_owned_paths": reviewed, "unclassified_path_count": 0, "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    if subprocess.check_output(["git", "-C", str(root), "diff", "--cached", "--name-only"], text=True).strip():
        raise RuntimeError("staged files forbidden")
    coverage_path = root / "reports/week_03/results/critical_eval_v2_ea1_revision14_review_scope_coverage.json"
    if not coverage_path.exists():
        coverage_path.write_text("{}\n", encoding="utf-8", newline="\n")
    coverage = classify(root)
    coverage_path.write_text(json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    with tempfile.TemporaryDirectory(prefix="ea1_r14_bundle_") as directory:
        bundle = Path(directory)
        for relative in TASK_PATHS:
            target = bundle / "task_files" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
        for relative in REFERENCES:
            target = bundle / "references" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
        candidate = json.loads(
            (root / "reports/week_03/results/critical_eval_v2_evaluation_authorization_candidate.json").read_text(
                encoding="utf-8"
            )
        )
        for relative in sorted(candidate["execution_artifact_sha256"]):
            target = bundle / "readiness_files" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
        evidence = bundle / "evidence"; evidence.mkdir()
        topology = {"branch": subprocess.check_output(["git", "-C", str(root), "branch", "--show-current"], text=True).strip(),
                    "head": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
                    "parent": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD^"], text=True).strip(),
                    "staged_count": 0}
        (evidence / "git_preflight.json").write_text(json.dumps(topology, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        proposed = [{"path": path, "bytes": (root / path).stat().st_size, "sha256": sha256(root / path)} for path in sorted(TASK_PATHS)]
        (evidence / "proposed_commit_paths.json").write_text(json.dumps({"status": "PASS", "count": len(proposed), "paths": proposed}, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        verifier = root / "scripts/evaluation/verify_critical_v2_ea1_revision14_bundle.py"
        shutil.copyfile(verifier, bundle / verifier.name)
        files = []
        for item in sorted(path for path in bundle.rglob("*") if path.is_file()):
            relative = item.relative_to(bundle).as_posix()
            files.append({"path": relative, "size": item.stat().st_size, "sha256": sha256(item)})
        (bundle / "detached_inventory.json").write_text(json.dumps({"status": "PASS", "files": files}, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for item in sorted(path for path in bundle.rglob("*") if path.is_file()):
                archive.write(item, item.relative_to(bundle).as_posix())
    print(json.dumps({"status": "PASS", "task_path_count": len(TASK_PATHS), "output": str(output), "bytes": output.stat().st_size, "sha256": sha256(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
