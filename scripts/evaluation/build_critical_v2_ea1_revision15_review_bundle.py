"""Build the detached R15 evaluation-state closure review bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path


TASK_PATHS = (
    "PROJECT_STATE.md",
    "TASKS.md",
    "configs/evaluation/critical_eval_v2_authorization_topology.json",
    "configs/evaluation/critical_eval_v2_execution.json",
    "configs/evaluation/critical_eval_v2_execution_state_machine.json",
    "configs/evaluation/critical_eval_v2_metric_contract.json",
    "docs/evaluation/W3-002-CR1-EA1_execution_readiness.md",
    "reports/week_03/daily/2026-08-13.md",
    "reports/week_03/daily/2026-08-14.md",
    "reports/week_03/experiments/W3-002-CR1-EA1_execution_readiness.md",
    "reports/week_03/week_03_summary.md",
    "reports/week_03/results/critical_eval_v2_evaluation_authorization_candidate.json",
    "reports/week_03/results/critical_eval_v2_execution_environment.json",
    "reports/week_03/results/critical_eval_v2_future_command_plan.json",
    "reports/week_03/results/critical_eval_v2_runtime_asset_manifest.json",
    "reports/week_03/results/critical_eval_v2_runtime_payload_manifest.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_incident_reproduction.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_transition_contract_matrix.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_primary_preservation.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_continuation_design.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_committed_synthetic_a15.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_f1_authority_finding.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_f1_negative_controls.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_f2_git_config_defect_reproduction.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_f2_real_repo_config_isolation.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_isolated_migration.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_synthetic_premodel.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_runtime_source_closure.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_hash_rebinding.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_environment_recheck.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_verification_summary.json",
    "scripts/evaluation/prepare_critical_v2_ea1_revision15_evidence.py",
    "scripts/evaluation/build_critical_v2_ea1_revision15_review_bundle.py",
    "scripts/evaluation/verify_critical_v2_ea1_revision15_bundle.py",
    "src/payresolve_ai/evaluation/critical_v2_execution.py",
    "tests/test_critical_v2_execution_revision15.py",
    "tests/test_critical_v2_execution_readiness.py",
    "tests/test_critical_v2_execution_revision10.py",
    "tests/test_critical_v2_execution_revision11.py",
    "tests/test_critical_v2_execution_revision13.py",
    "tests/test_critical_v2_execution_revision14.py",
)


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    candidate = json.loads((root / "reports/week_03/results/critical_eval_v2_evaluation_authorization_candidate.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="ea1_r15_bundle_") as directory:
        bundle = Path(directory)
        for relative in TASK_PATHS:
            target = bundle / "task_files" / relative; target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(root / relative, target)
        for relative in candidate["execution_artifact_sha256"]:
            target = bundle / "readiness_files" / relative; target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(root / relative, target)
        references = [
            "reports/week_03/results/critical_eval_v2_execution_state.json",
            "reports/week_03/results/critical_eval_v2_runtime_execution_environment.json",
            *json.loads((root / "configs/evaluation/critical_eval_v2_execution.json").read_text(encoding="utf-8"))["evaluation_outputs"]["primary"].values(),
        ]
        for relative in references:
            target = bundle / "historical_references" / relative; target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(root / relative, target)
        proposed = [{"path": p, "bytes": (root / p).stat().st_size, "sha256": sha(root / p)} for p in TASK_PATHS]
        evidence = bundle / "evidence"; evidence.mkdir(); (evidence / "proposed_commit_scope.json").write_text(json.dumps({"status": "PASS", "count": len(proposed), "paths": proposed}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        verifier = root / "scripts/evaluation/verify_critical_v2_ea1_revision15_bundle.py"; shutil.copyfile(verifier, bundle / verifier.name)
        files = [{"path": p.relative_to(bundle).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(bundle.rglob("*")) if p.is_file()]
        (bundle / "detached_inventory.json").write_text(json.dumps({"status": "PASS", "files": files}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(bundle.rglob("*")):
                if path.is_file(): archive.write(path, path.relative_to(bundle).as_posix())
    print(json.dumps({"status": "PASS", "output": str(output), "bytes": output.stat().st_size, "sha256": sha(output), "task_path_count": len(TASK_PATHS)}, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
