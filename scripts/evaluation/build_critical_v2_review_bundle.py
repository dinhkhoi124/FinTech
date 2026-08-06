"""Build the external W3-002-CR1 Senior review bundle without repository writes."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--config", type=Path, default=Path("configs/evaluation/critical_eval_v2.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    config_path = (root / args.config).resolve() if not args.config.is_absolute() else args.config
    config = json.loads(config_path.read_text(encoding="utf-8"))
    files = set(config["candidate_artifacts"])
    files.update(config["outputs"].values())
    files.update(
        value
        for key, value in config["revision_history"].items()
        if not key.endswith("_archive_root")
    )
    files.update(config["overlap_source_artifacts"])
    files.update(config["historical_artifacts"].keys())
    revision_2_inventory = json.loads((root / config["revision_history"]["rejected_revision_2_inventory"]).read_text(encoding="utf-8"))
    files.update(revision_2_inventory["artifact_sha256"])
    revision_3_inventory = json.loads((root / config["revision_history"]["rejected_revision_3_inventory"]).read_text(encoding="utf-8"))
    files.update(item["path"] for item in revision_3_inventory["artifacts"])
    revision_4_inventory = json.loads((root / config["revision_history"]["rejected_revision_4_inventory"]).read_text(encoding="utf-8"))
    revision_4_root = Path(config["revision_history"]["rejected_revision_4_archive_root"])
    files.update((revision_4_root / item["path"]).as_posix() for item in revision_4_inventory["artifacts"])
    revision_5_inventory = json.loads((root / config["revision_history"]["rejected_revision_5_inventory"]).read_text(encoding="utf-8"))
    revision_5_root = Path(config["revision_history"]["rejected_revision_5_archive_root"])
    files.update((revision_5_root / item["path"]).as_posix() for item in revision_5_inventory["artifacts"])
    files.update(
        {
            "PROJECT_STATE.md",
            "TASKS.md",
            "data/kb/kb_v1.jsonl",
            "configs/kb/kb_v1.json",
            "configs/evaluation/critical_eval_v2_contract_option_a.json",
            "docs/evaluation/W3-002-CR1_amended_contract.md",
            "docs/evaluation/critical_eval_v2_response_taxonomy.md",
            "src/payresolve_ai/evaluation/critical_v2.py",
            "src/payresolve_ai/evaluation/gold_mapping.py",
            "src/payresolve_ai/kb/validation.py",
            "src/payresolve_ai/data/banking77.py",
            "src/payresolve_ai/__init__.py",
            "src/payresolve_ai/evaluation/__init__.py",
            "src/payresolve_ai/kb/__init__.py",
            "src/payresolve_ai/data/__init__.py",
            "scripts/evaluation/week3_critical_v2.py",
            "scripts/evaluation/verify_review_bundle.py",
            "scripts/evaluation/build_critical_v2_review_bundle.py",
            "tests/test_critical_eval_v2.py",
            "reports/week_03/daily/2026-08-04.md",
            "reports/week_03/daily/2026-08-05.md",
            "reports/week_03/daily/2026-08-06.md",
            "reports/week_03/week_03_summary.md",
            "reports/week_03/experiments/W3-002-CR1_pristine_critical_evaluation_contract.md",
            "reports/week_03/experiments/W3-002-CR1_pre_evaluation_integrity.md",
            "reports/week_03/experiments/W3-002-CR1_revision_1_rejection_history.md",
            "reports/week_03/experiments/W3-002-CR1_revision_2_rejection_history.md",
            "reports/week_03/experiments/W3-002-CR1_revision_3_rejection_history.md",
            "reports/week_03/experiments/W3-002-CR1_revision_4_rejection_history.md",
            "reports/week_03/experiments/W3-002-CR1_revision_5_structural_authoring.md",
            "reports/week_03/experiments/W3-002-CR1_revision_6_semantic_correction.md",
            "reports/week_03/results/critical_eval_v2_revision_5_acceptance_checklist.json",
            "reports/week_03/results/critical_eval_v2_revision_4_rejected_inventory.json",
            "reports/week_03/results/critical_eval_v2_revision_4_negative_feasibility_matrix.jsonl",
            "reports/week_03/results/critical_eval_v2_revision_4_positive_support_defects.jsonl",
            "reports/week_03/results/critical_eval_v2_revision_4_hard_negative_feasibility.json",
            "reports/week_03/results/critical_eval_v2_isolated_full_test_output.txt",
            "reports/week_03/experiments/W3-002_critical_mapping_integrity_incident.md",
            "data/evaluation/critical_eval_v1_posthoc_support_judgments.jsonl",
            "reports/week_03/results/critical_eval_v1_posthoc_positive_integrity_audit.csv",
            "reports/week_03/results/critical_eval_v1_posthoc_negative_integrity_audit.csv",
            "reports/week_03/results/critical_eval_v1_integrity_incident_summary.json",
        }
    )
    missing = sorted(path for path in files if not (root / path).is_file())
    if missing:
        raise SystemExit(f"missing review inputs: {missing}")
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="w3-002-cr1-review-") as temporary:
        staging = Path(temporary)
        for relative in sorted(files):
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / relative, destination)
        status = subprocess.run(["git", "status", "--short"], cwd=root, check=True, text=True, capture_output=True).stdout
        diff_stat = subprocess.run(["git", "diff", "--stat"], cwd=root, check=True, text=True, capture_output=True).stdout
        (staging / "git_status.txt").write_text(status, encoding="utf-8", newline="\n")
        (staging / "git_diff_stat.txt").write_text(diff_stat, encoding="utf-8", newline="\n")
        task_pathspec = sorted(files)
        (staging / "task_pathspec.txt").write_text("\n".join(task_pathspec) + "\n", encoding="utf-8", newline="\n")
        task_diff = subprocess.run(
            ["git", "diff", "--", *task_pathspec], cwd=root, check=True, text=True, capture_output=True
        ).stdout
        (staging / "git_task_diff.patch").write_text(task_diff, encoding="utf-8", newline="\n")
        inventory = []
        for path in sorted(item for item in staging.rglob("*") if item.is_file()):
            relative = path.relative_to(staging).as_posix()
            inventory.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": sha256(path)})
        manifest = {
            "task_id": "W3-002-CR1",
            "candidate_revision": config["candidate_revision"],
            "rejected_revision_1_manifest_sha256": "39af29f929ef9a9287808c26d62787079e376a8b7ac05847fa10729d27374b99",
            "rejected_revision_2_manifest_sha256": "668992392f3e0f4addeb017a0028f6bc676614910d0e1c03fb8f3e3c51a20834",
            "rejected_revision_3_manifest_sha256": "650a8a5847d83211c96941e549bc4379df89e1ae91c857a59c65160a6ed0f688",
            "rejected_revision_3_review_bundle_sha256": "6e32aa4081c609fb8e2767c099af419f046cd6c6261aec39ddd11368a426603a",
            "rejected_revision_4_manifest_sha256": "b2b021c78f11ff4cf5d023044b464b43d806f0c0217fd8e3b196dfc736bb52af",
            "rejected_revision_4_review_bundle_sha256": "a081e909113a682e7790b758f2b90bea3eea26025103e7209dc1c32e8f04fa5e",
            "rejected_revision_5_manifest_sha256": "342e5652fb03f249eeb999f7b2c4452668b82ce83d28d65b9a3d452745cc2d32",
            "rejected_revision_5_review_bundle_sha256": "9599c09bac7d1b46c9d4893c546993958f40f64805db1b7fb8a97625b966debf",
            "standalone_verification_command": "python scripts/evaluation/verify_review_bundle.py --root .",
            "package_status": "FROZEN_CANDIDATE / AWAITING_SENIOR_SEMANTIC_REVIEW",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "repository_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, text=True, capture_output=True).stdout.strip(),
            "file_count_excluding_manifest": len(inventory),
            "files": inventory,
            "exclusions": [".git", ".gitignore", "docs/refactor", ".venv*", "artifacts", "outputs", "cache", "embeddings", "models", ".env", "secrets", "unrelated user/DOC artifacts"],
            "manifest_self_hash_excluded_to_avoid_recursive_hashing": True,
            "repository_staged_committed_or_pushed_by_bundle_command": False,
            "model_encoder_retrieval_generation_or_evaluation_executed": False,
        }
        (staging / "review_bundle_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        if output.exists():
            raise SystemExit(f"review bundle already exists: {output}")
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(item for item in staging.rglob("*") if item.is_file()):
                archive.write(path, path.relative_to(staging).as_posix())
    print(json.dumps({"zip_path": str(output), "sha256": sha256(output), "size_bytes": output.stat().st_size, "file_count": len(zipfile.ZipFile(output).infolist())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
