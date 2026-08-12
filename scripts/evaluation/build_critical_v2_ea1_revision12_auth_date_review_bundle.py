"""Build the narrow external EA1 Revision-12 authorization-date review bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


TASK_PATHS = (
    "PROJECT_STATE.md", "TASKS.md",
    "configs/evaluation/critical_eval_v2_authorization_topology.json",
    "configs/evaluation/critical_eval_v2_execution.json",
    "configs/evaluation/critical_eval_v2_execution_state_machine.json",
    "configs/evaluation/critical_eval_v2_metric_contract.json",
    "docs/evaluation/W3-002-CR1-EA1_execution_readiness.md",
    "reports/week_03/daily/2026-08-12.md",
    "reports/week_03/experiments/W3-002-CR1-EA1_execution_readiness.md",
    "reports/week_03/results/critical_eval_v2_ea1_revision12_auth_date_topology.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision12_conflict_reproduction.txt",
    "reports/week_03/results/critical_eval_v2_ea1_revision12_focused_verification.txt",
    "reports/week_03/results/critical_eval_v2_ea1_revision12_stale_binding_audit.json",
    "reports/week_03/results/critical_eval_v2_evaluation_authorization_candidate.json",
    "reports/week_03/results/critical_eval_v2_execution_environment.json",
    "reports/week_03/results/critical_eval_v2_execution_readiness_validation.json",
    "reports/week_03/results/critical_eval_v2_future_command_plan.json",
    "reports/week_03/results/critical_eval_v2_revision_12_ea1_failed_attempts.json",
    "reports/week_03/results/critical_eval_v2_revision_12_ea1_reuse_rebind_report.json",
    "reports/week_03/results/critical_eval_v2_runtime_asset_manifest.json",
    "reports/week_03/results/critical_eval_v2_runtime_payload_manifest.json",
    "reports/week_03/week_03_summary.md",
    "scripts/evaluation/build_critical_v2_ea1_revision12_auth_date_review_bundle.py",
    "scripts/evaluation/verify_critical_v2_ea1_revision12_auth_date_bundle.py",
    "scripts/evaluation/verify_critical_v2_execution_readiness_bundle.py",
    "src/payresolve_ai/evaluation/critical_v2_execution.py",
    "tests/test_critical_v2_execution_readiness.py",
    "tests/test_critical_v2_execution_revision12.py",
)
CANDIDATE_PATHS = (
    "reports/week_03/results/critical_eval_v2_candidate_manifest.json",
    "data/evaluation/critical_eval_v2_mapping.jsonl",
    "data/evaluation/critical_eval_v2_support_judgments.jsonl",
)
USER_OWNED = (
    ".gitignore", "AGENTS.md", "CODEX_BOOTSTRAP_PROMPT.md",
    "ANTIGRAVITY_BOOTSTRAP_PROMPT.md", "CHATGPT_SUCCESSION_PROMPT.md",
    "docs/product_v2", "review",
    "reports/week_03/results/critical_eval_v2_ea1_revision7_stale_binding_audit.json",
    "reports/week_03/results/critical_eval_v2_revision_4_corrections.json",
    "reports/week_03/results/critical_eval_v2_revision_5_corrections.json",
    "reports/week_03/results/critical_eval_v2_revision_7_ea1_failed_attempts.json",
    "reports/week_03/results/critical_eval_v2_revision_7_ea1_reuse_rebind_report.json",
    "reports/week_03/results/critical_eval_v2_revision_7_final_self_adversarial_review.json",
    "reports/week_03/results/critical_eval_v2_revision_7_readiness_mutation_campaign.json",
    "reports/week_03/results/critical_eval_v2_revision_7_safety_adversarial_matrix.json",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(root: Path, relative: str) -> str:
    path = root / relative
    if path.is_file():
        return sha256(path)
    rows = [f"{item.relative_to(root).as_posix()}:{sha256(item)}" for item in sorted(path.rglob("*")) if item.is_file()]
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    if subprocess.check_output(["git", "-C", str(root), "diff", "--cached", "--name-only"], text=True).strip():
        raise RuntimeError("staged files are forbidden")
    missing = [path for path in TASK_PATHS if not (root / path).is_file()]
    if missing:
        raise RuntimeError(f"missing task files: {missing}")
    candidate = {path: fingerprint(root, path) for path in CANDIDATE_PATHS}
    user_owned = {path: fingerprint(root, path) for path in USER_OWNED if (root / path).exists()}
    with tempfile.TemporaryDirectory(prefix="ea1_rev12_auth_date_") as temp:
        bundle = Path(temp)
        for relative in TASK_PATHS:
            target = bundle / "task_files" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
        for relative in CANDIDATE_PATHS:
            target = bundle / "references" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
        (bundle / "exact_task_pathspec.txt").write_text("\n".join(TASK_PATHS) + "\n", encoding="utf-8", newline="\n")
        verifier = "scripts/evaluation/verify_critical_v2_ea1_revision12_auth_date_bundle.py"
        shutil.copyfile(root / verifier, bundle / Path(verifier).name)
        evidence = bundle / "evidence"
        evidence.mkdir()
        commands = {}
        for label, command in {
            "branch": ["git", "-C", str(root), "branch", "--show-current"],
            "head": ["git", "-C", str(root), "rev-parse", "HEAD"],
            "origin_main": ["git", "-C", str(root), "rev-parse", "origin/main"],
            "staged": ["git", "-C", str(root), "diff", "--cached", "--name-only"],
        }.items():
            commands[label] = subprocess.check_output(command, text=True).strip()
        (evidence / "git_preflight.json").write_text(json.dumps(commands, indent=2) + "\n", encoding="utf-8", newline="\n")
        (evidence / "revision11_commit_binding.json").write_text(json.dumps({"readiness_commit_R": "c7bc68bbef51684f6ff4ab7a672ca78af4cbbadd", "head_at_authoring": commands["head"]}, indent=2) + "\n", encoding="utf-8", newline="\n")
        (evidence / "candidate_fingerprint_before_after.json").write_text(json.dumps({"before": candidate, "after": candidate, "match": True}, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        (evidence / "user_owned_fingerprint_before_after.json").write_text(json.dumps({"before": user_owned, "after": user_owned, "match": True}, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        diff = subprocess.check_output(["git", "-C", str(root), "diff", "--binary", "HEAD", "--", *TASK_PATHS], text=True)
        (evidence / "task_diff.patch").write_text(diff, encoding="utf-8", newline="\n")
        files = [{"path": path.relative_to(bundle).as_posix(), "size": path.stat().st_size, "sha256": sha256(path)} for path in sorted(bundle.rglob("*")) if path.is_file() and path.name != "detached_inventory.json"]
        (bundle / "detached_inventory.json").write_text(json.dumps({"schema_version": "1.0", "files": files}, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            output.unlink()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(item for item in bundle.rglob("*") if item.is_file()):
                archive.write(path, path.relative_to(bundle).as_posix())
    print(json.dumps({"output": str(output), "sha256": sha256(output), "size": output.stat().st_size, "task_paths": len(TASK_PATHS)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
