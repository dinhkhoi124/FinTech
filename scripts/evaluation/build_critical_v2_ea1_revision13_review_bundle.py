"""Build a detached, narrow EA1 Revision-13 readiness review bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


CORE_PATHS = (
    "PROJECT_STATE.md", "TASKS.md",
    "configs/evaluation/critical_eval_v2_authorization_topology.json",
    "configs/evaluation/critical_eval_v2_execution.json",
    "configs/evaluation/critical_eval_v2_execution_state_machine.json",
    "configs/evaluation/critical_eval_v2_metric_contract.json",
    "docs/evaluation/W3-002-CR1-EA1_execution_readiness.md",
    "reports/week_03/daily/2026-08-12.md", "reports/week_03/daily/2026-08-13.md",
    "reports/week_03/experiments/W3-002-CR1-EA1_execution_readiness.md",
    "reports/week_03/week_03_summary.md",
    "reports/week_03/results/critical_eval_v2_ea1_revision13_verification.txt",
    "reports/week_03/results/critical_eval_v2_runtime_execution_environment.json",
    "reports/week_03/results/critical_eval_v2_execution_state.json",
    "scripts/evaluation/build_critical_v2_ea1_revision13_review_bundle.py",
    "scripts/evaluation/prepare_critical_v2_ea1_revision13_evidence.py",
    "scripts/evaluation/verify_critical_v2_ea1_revision13_bundle.py",
    "scripts/evaluation/week3_critical_v2_execution.py",
    "src/payresolve_ai/evaluation/critical_v2_execution.py",
    "src/payresolve_ai/retrieval/benchmark.py", "src/payresolve_ai/baselines/semantic.py",
    "src/payresolve_ai/generation/context.py", "src/payresolve_ai/generation/gate.py",
    "src/payresolve_ai/generation/pipeline.py", "src/payresolve_ai/generation/support_v2.py",
    "src/payresolve_ai/generation/verification_v2.py", "src/payresolve_ai/retrieval/corpus.py",
    "src/payresolve_ai/generation/verification.py", "src/payresolve_ai/generation/extractive.py",
    "src/payresolve_ai/generation/citations.py", "src/payresolve_ai/generation/types.py",
    "src/payresolve_ai/baselines/lexical.py", "src/payresolve_ai/data/banking77.py",
    "src/payresolve_ai/evaluation/gold_mapping.py", "src/payresolve_ai/kb/validation.py",
    "src/payresolve_ai/retrieval/dense.py",
    "tests/test_critical_v2_execution_readiness.py",
    "tests/test_critical_v2_execution_revision12.py",
    "tests/test_critical_v2_execution_revision13.py",
    "tests/test_critical_v2_environment_provenance.py",
    "tests/test_critical_v2_binding_fix.py",
    "tests/test_critical_v2_auth_date_closure.py",
    "tests/test_critical_v2_review_scope_coverage.py",
    "tests/test_retrieval_benchmark.py",
)
EVIDENCE_KEYS = (
    "environment_manifest", "runtime_payload_manifest", "future_command_plan", "validation",
    "runtime_asset_manifest", "stale_binding_audit", "reuse_rebind_report", "failed_attempts",
    "runtime_incident_lineage", "preauthorization_reset_plan", "offline_encoder_probe",
    "transitive_runtime_source_binding", "runtime_asset_comparison",
    "runtime_payload_comparison", "a12_negative_control", "environment_reconciliation",
    "environment_contract", "runtime_source_closure", "binding_negative_controls",
)
REFERENCES = (
    "reports/week_03/results/critical_eval_v2_candidate_manifest.json",
    "data/evaluation/critical_eval_v2_mapping.jsonl",
    "data/evaluation/critical_eval_v2_support_judgments.jsonl",
)

PROTECTED_E1_PATHS = {
    "reports/week_03/results/critical_eval_v2_runtime_execution_environment.json",
    "reports/week_03/results/critical_eval_v2_execution_state.json",
}
USER_OWNED_EXACT = {
    ".gitignore", "AGENTS.md", "CODEX_BOOTSTRAP_PROMPT.md",
    "ANTIGRAVITY_BOOTSTRAP_PROMPT.md", "CHATGPT_SUCCESSION_PROMPT.md",
    "scripts/generate_slide_deck.py",
    "reports/week_03/results/critical_eval_v2_ea1_revision13_environment_drift_stop.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision7_stale_binding_audit.json",
    "reports/week_03/results/critical_eval_v2_revision_4_corrections.json",
    "reports/week_03/results/critical_eval_v2_revision_5_corrections.json",
    "reports/week_03/results/critical_eval_v2_revision_7_ea1_failed_attempts.json",
    "reports/week_03/results/critical_eval_v2_revision_7_ea1_reuse_rebind_report.json",
    "reports/week_03/results/critical_eval_v2_revision_7_final_self_adversarial_review.json",
    "reports/week_03/results/critical_eval_v2_revision_7_readiness_mutation_campaign.json",
    "reports/week_03/results/critical_eval_v2_revision_7_safety_adversarial_matrix.json",
}
USER_OWNED_PREFIXES = (
    "docs/product_v2/", "outputs/", "review/", "tests/test_reporting/",
    "reports/mentor_progress_visuals/", "reports/PayResolve_AI_Sprint3_",
    "reports/mentor_sprint_report_",
)


def dirty_paths(root: Path) -> list[str]:
    raw = subprocess.check_output(
        ["git", "-C", str(root), "status", "--porcelain=v1", "-z", "--untracked-files=all"]
    ).decode("utf-8")
    records = [record for record in raw.split("\0") if record]
    paths = []
    index = 0
    while index < len(records):
        record = records[index]
        status, relative = record[:2], record[3:].replace("\\", "/")
        paths.append(relative)
        index += 2 if status[0] in "RC" else 1
    return sorted(set(paths))


def classify_review_scope(
    root: Path, task_paths: set[str], observed_dirty: list[str] | None = None,
) -> dict[str, object]:
    observed = dirty_paths(root) if observed_dirty is None else sorted(set(observed_dirty))
    rows = []
    unclassified = []
    for relative in observed:
        if relative in PROTECTED_E1_PATHS:
            category = "PROTECTED_E1_EXCLUDE"
        elif relative.startswith("reports/week_03/review_bundles/") and relative.endswith(".zip"):
            category = "REVIEW_ZIP_EXCLUDE"
        elif relative in task_paths:
            category = "R13_TASK_OWNED_REVIEWED"
        elif relative in USER_OWNED_EXACT or relative.startswith(USER_OWNED_PREFIXES):
            category = "USER_OWNED_EXCLUDE"
        else:
            category = "UNCLASSIFIED"
            unclassified.append(relative)
        rows.append({"path": relative, "category": category})
    if unclassified:
        raise RuntimeError(f"R13_REVIEW_SCOPE_COVERAGE_INCOMPLETE: unclassified={unclassified}")
    return {"status": "PASS", "dirty_path_count": len(rows), "rows": rows}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    if subprocess.check_output(["git", "-C", str(root), "diff", "--cached", "--name-only"], text=True).strip():
        raise RuntimeError("staged files are forbidden")
    config = json.loads((root / "configs/evaluation/critical_eval_v2_execution.json").read_text(encoding="utf-8"))
    paths = list(dict.fromkeys(
        list(CORE_PATHS)
        + [config["readiness_outputs"][key] for key in EVIDENCE_KEYS]
        + [config["authorization"]["candidate"]]
    ))
    task_path_set = set(paths)
    coverage = classify_review_scope(root, task_path_set)
    reviewed_dirty = sorted(
        row["path"] for row in coverage["rows"]
        if row["category"] == "R13_TASK_OWNED_REVIEWED"
    )
    missing_reviewed = [path for path in reviewed_dirty if path not in task_path_set]
    if missing_reviewed:
        raise RuntimeError(
            f"R13_REVIEW_SCOPE_COVERAGE_INCOMPLETE: missing task_files={missing_reviewed}"
        )
    missing = [path for path in paths + list(REFERENCES) if not (root / path).is_file()]
    if missing:
        raise RuntimeError(f"missing bundle input: {missing}")
    with tempfile.TemporaryDirectory(prefix="ea1_r13_") as temp:
        bundle = Path(temp)
        for relative in paths:
            target = bundle / "task_files" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
        for relative in REFERENCES:
            target = bundle / "references" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
        verifier = root / "scripts/evaluation/verify_critical_v2_ea1_revision13_bundle.py"
        shutil.copyfile(verifier, bundle / verifier.name)
        evidence = bundle / "evidence"
        evidence.mkdir()
        proposed_rows = []
        for relative in reviewed_dirty:
            repository_path = root / relative
            bundled_path = bundle / "task_files" / relative
            if (
                not repository_path.is_file()
                or not bundled_path.is_file()
                or repository_path.read_bytes() != bundled_path.read_bytes()
            ):
                raise RuntimeError(
                    f"R13_REVIEW_SCOPE_COVERAGE_INCOMPLETE: byte mismatch={relative}"
                )
            proposed_rows.append({
                "path": relative,
                "bytes": repository_path.stat().st_size,
                "working_tree_sha256": sha256(repository_path),
                "task_files_sha256": sha256(bundled_path),
                "byte_equal": True,
            })
        coverage.update({
            "schema_version": "1.0",
            "task_id": config["task_id"],
            "readiness_revision": 13,
            "r13_task_owned_reviewed_count": len(reviewed_dirty),
            "r13_task_owned_reviewed_paths": reviewed_dirty,
            "all_reviewed_paths_present_in_task_files": True,
            "unclassified_path_count": 0,
        })
        (evidence / "review_scope_coverage.json").write_text(
            json.dumps(coverage, indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n",
        )
        proposed = {
            "schema_version": "1.0", "task_id": config["task_id"],
            "readiness_revision": 13, "status": "PASS",
            "proposed_commit_path_count": len(proposed_rows),
            "proposed_commit_paths": proposed_rows,
            "all_working_tree_bytes_equal_task_files": True,
            "protected_e1_paths_absent": not bool(set(reviewed_dirty) & PROTECTED_E1_PATHS),
            "review_zip_paths_absent": not any(path.endswith(".zip") for path in reviewed_dirty),
            "user_owned_paths_absent": not any(
                row["category"] == "USER_OWNED_EXCLUDE" and row["path"] in reviewed_dirty
                for row in coverage["rows"]
            ),
        }
        (evidence / "proposed_commit_paths.json").write_text(
            json.dumps(proposed, indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n",
        )
        git_state = {
            key: subprocess.check_output(command, text=True).strip()
            for key, command in {
                "branch": ["git", "-C", str(root), "branch", "--show-current"],
                "head": ["git", "-C", str(root), "rev-parse", "HEAD"],
                "origin_main": ["git", "-C", str(root), "rev-parse", "origin/main"],
                "staged": ["git", "-C", str(root), "diff", "--cached", "--name-only"],
            }.items()
        }
        (evidence / "git_preflight.json").write_text(json.dumps(git_state, indent=2) + "\n", encoding="utf-8", newline="\n")
        protected = {
            path: {"size": (root / path).stat().st_size, "sha256": sha256(root / path)}
            for path in (
                config["runtime_environment"]["manifest"],
                config["evaluation_outputs"]["execution_state"],
            )
        }
        (evidence / "protected_e1_hashes.json").write_text(json.dumps(protected, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        diff = subprocess.check_output(["git", "-C", str(root), "diff", "--binary", "HEAD", "--", *CORE_PATHS], text=True)
        (evidence / "task_diff.patch").write_text(diff, encoding="utf-8", newline="\n")
        files = [{"path": p.relative_to(bundle).as_posix(), "size": p.stat().st_size, "sha256": sha256(p)}
                 for p in sorted(bundle.rglob("*")) if p.is_file() and p.name != "detached_inventory.json"]
        (bundle / "detached_inventory.json").write_text(json.dumps({"schema_version": "1.0", "files": files}, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            output.unlink()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(p for p in bundle.rglob("*") if p.is_file()):
                archive.write(path, path.relative_to(bundle).as_posix())
    print(json.dumps({"output": str(output), "size": output.stat().st_size,
                      "sha256": sha256(output), "task_files": len(paths)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
