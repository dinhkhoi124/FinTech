"""Build and verify a W3-002-CR1-EA1 readiness review bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
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
    "configs/evaluation/schemas/critical_eval_v2_evaluation.schema.json",
    "configs/evaluation/schemas/critical_eval_v2_raw_output.schema.json",
    "data/evaluation/critical_eval_v2_control_plane_boundary_rules.jsonl",
    "data/evaluation/critical_eval_v2_obligation_evaluator_rules.jsonl",
    "data/evaluation/critical_eval_v2_safety_evaluator_rules.jsonl",
    "docs/evaluation/W3-002-CR1-EA1_execution_readiness.md",
    "reports/week_03/daily/2026-08-10.md",
    "reports/week_03/daily/2026-08-11.md",
    "reports/week_03/experiments/W3-002-CR1-EA1_execution_readiness.md",
    "reports/week_03/results/critical_eval_v2_ea1_revision8_senior_safety_regressions.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision8_stale_binding_audit.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision7_rejection_lineage.json",
    "reports/week_03/results/critical_eval_v2_evaluation_authorization_candidate.json",
    "reports/week_03/results/critical_eval_v2_execution_environment.json",
    "reports/week_03/results/critical_eval_v2_execution_readiness_validation.json",
    "reports/week_03/results/critical_eval_v2_future_command_plan.json",
    "reports/week_03/results/critical_eval_v2_obligation_revision_7_semantic_delta.json",
    "reports/week_03/results/critical_eval_v2_obligation_sentence_semantic_audit.jsonl",
    "reports/week_03/results/critical_eval_v2_revision_7_cov1_safety_regressions.json",
    "reports/week_03/results/critical_eval_v2_revision_8_ea1_failed_attempts.json",
    "reports/week_03/results/critical_eval_v2_revision_8_ea1_reuse_rebind_report.json",
    "reports/week_03/results/critical_eval_v2_revision_7_evaluator_cover_equivalence.json",
    "reports/week_03/results/critical_eval_v2_revision_7_evaluator_cover_inconsistency.json",
    "reports/week_03/results/critical_eval_v2_revision_8_final_self_adversarial_review.json",
    "reports/week_03/results/critical_eval_v2_revision_7_independent_cover_reference.json",
    "reports/week_03/results/critical_eval_v2_revision_7_noncanonical_larger_covers.json",
    "reports/week_03/results/critical_eval_v2_revision_8_readiness_mutation_campaign.json",
    "reports/week_03/results/critical_eval_v2_revision_8_safety_adversarial_matrix.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision8_rejection_lineage.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision9_senior_safety_regressions.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision9_stale_binding_audit.json",
    "reports/week_03/results/critical_eval_v2_revision_9_cross_target_disclosure_coverage.json",
    "reports/week_03/results/critical_eval_v2_revision_9_disclosure_fixture_quality.json",
    "reports/week_03/results/critical_eval_v2_revision_9_disclosure_target_classification.json",
    "reports/week_03/results/critical_eval_v2_revision_9_ea1_failed_attempts.json",
    "reports/week_03/results/critical_eval_v2_revision_9_ea1_reuse_rebind_report.json",
    "reports/week_03/results/critical_eval_v2_revision_9_final_self_adversarial_review.json",
    "reports/week_03/results/critical_eval_v2_revision_9_readiness_mutation_campaign.json",
    "reports/week_03/results/critical_eval_v2_revision_9_safety_adversarial_matrix.json",
    "reports/week_03/results/critical_eval_v2_runtime_asset_manifest.json",
    "reports/week_03/results/critical_eval_v2_runtime_payload_manifest.json",
    "reports/week_03/week_03_summary.md",
    "scripts/evaluation/build_critical_v2_ea1_revision7_review_bundle.py",
    "scripts/evaluation/build_critical_v2_ea1_revision8_review_bundle.py",
    "scripts/evaluation/build_critical_v2_ea1_revision9_review_bundle.py",
    "scripts/evaluation/rebind_critical_v2_ea1_revision7.py",
    "scripts/evaluation/verify_critical_v2_execution_readiness_bundle.py",
    "scripts/evaluation/week3_critical_v2_execution.py",
    "src/payresolve_ai/evaluation/critical_v2_execution.py",
    "tests/test_critical_v2_execution_readiness.py",
)

BUNDLE_REVISION = 9
DETACHED_VERIFIER = "scripts/evaluation/verify_critical_v2_execution_readiness_bundle.py"
FOCUSED_MODULES = ("tests.test_critical_v2_execution_readiness",)
EXTRA_COMPILE_PATHS: tuple[str, ...] = ()

RELATED_MODULES = (
    "tests.test_critical_eval_v2_revision_7",
    "tests.test_critical_eval_v2",
    "tests.test_critical_v2_contract",
    "tests.test_critical_v2_feasibility",
    "tests.test_critical_safety_evaluation",
)

FROZEN_RAW_BANKING77 = Path(
    "data/raw/banking77/57ec275d8078af65b7731c2a98be812d844a6d6b"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(
    command: list[str], cwd: Path, *, env: dict[str, str] | None = None
) -> tuple[int, str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, env=env)
    return result.returncode, result.stdout + result.stderr


def write_command_evidence(
    path: Path,
    command: list[str],
    cwd: Path,
    *,
    env: dict[str, str] | None = None,
) -> None:
    code, output = run(command, cwd, env=env)
    path.write_text(
        "COMMAND: " + subprocess.list2cmdline(command) + f"\nEXIT_CODE: {code}\n\n" + output,
        encoding="utf-8",
        newline="\n",
    )
    if code:
        diagnostic_tail = output[-16000:]
        raise RuntimeError(
            f"verification command failed: {command}\n"
            f"--- captured output tail ---\n{diagnostic_tail}"
        )


def copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def collect_user_owned(root: Path) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for line in subprocess.check_output(
        ["git", "-C", str(root), "status", "--porcelain"], text=True
    ).splitlines():
        relative = line[3:].replace("\\", "/")
        if relative in TASK_PATHS or any(
            path.startswith(relative.rstrip("/") + "/") for path in TASK_PATHS
        ):
            continue
        path = root / relative.rstrip("/")
        if path.is_file():
            fingerprints[relative] = sha256(path)
        else:
            files = sorted(item for item in path.rglob("*") if item.is_file()) if path.is_dir() else []
            fingerprints[relative] = hashlib.sha256(
                "\n".join(
                    f"{item.relative_to(root).as_posix()}:{sha256(item)}"
                    for item in files
                ).encode()
            ).hexdigest()
    return fingerprints


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--isolated-root", type=Path, required=True)
    parser.add_argument("--senior-prompt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    python = args.python.resolve()
    isolated_parent = args.isolated_root.resolve()
    output = args.output.resolve()

    missing = [path for path in TASK_PATHS if not (root / path).is_file()]
    if missing:
        raise RuntimeError(f"task files missing: {missing}")
    if len(TASK_PATHS) != len(set(TASK_PATHS)):
        raise RuntimeError("duplicate task path")
    staged = subprocess.check_output(
        ["git", "-C", str(root), "diff", "--cached", "--name-only"], text=True
    ).splitlines()
    if staged:
        raise RuntimeError(f"staged files are forbidden: {staged}")
    user_owned_before = collect_user_owned(root)

    with tempfile.TemporaryDirectory(prefix=f"ea1_r{BUNDLE_REVISION}_bundle_") as temporary:
        bundle = Path(temporary)
        task_root = bundle / "task_files"
        references = bundle / "references"
        evidence = bundle / "evidence"
        evidence.mkdir(parents=True)
        for relative in TASK_PATHS:
            copy_file(root / relative, task_root / relative)

        manifest_path = root / "reports/week_03/results/critical_eval_v2_candidate_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        candidate_before = {
            relative: sha256(root / relative)
            for relative in sorted(manifest["artifact_sha256"])
        }
        candidate_before[manifest_path.relative_to(root).as_posix()] = sha256(manifest_path)
        reference_paths = {"reports/week_03/results/critical_eval_v2_candidate_manifest.json"}
        reference_paths.update(manifest["artifact_sha256"])
        reference_paths.update(
            {
                "configs/evaluation/critical_eval_v2_contract_option_a.json",
                "data/kb/kb_v1.jsonl",
                "reports/week_03/results/critical_eval_v2_revision_7_senior_semantic_approval.json",
            }
        )
        for relative in sorted(reference_paths):
            copy_file(root / relative, references / relative)

        (bundle / "exact_task_pathspec.txt").write_text(
            "\n".join(TASK_PATHS) + "\n", encoding="utf-8", newline="\n"
        )
        copy_file(
            root / DETACHED_VERIFIER,
            bundle / "verify_critical_v2_execution_readiness_bundle.py",
        )
        copy_file(args.senior_prompt, evidence / f"senior_readiness_revision{BUNDLE_REVISION}_correction.txt")

        write_command_evidence(
            evidence / "candidate_byte_verification.txt",
            [str(python), "scripts/evaluation/week3_critical_v2.py", "--root", ".", "--config", "configs/evaluation/critical_eval_v2.json", "verify-candidate"],
            root,
        )
        write_command_evidence(
            evidence / "readiness_verification.txt",
            [str(python), "scripts/evaluation/week3_critical_v2_execution.py", "--root", ".", "--config", "configs/evaluation/critical_eval_v2_execution.json", "verify-execution-readiness"],
            root,
        )
        write_command_evidence(
            evidence / "focused_tests.txt",
            [str(python), "-m", "unittest", *FOCUSED_MODULES, "-v"],
            root,
        )
        write_command_evidence(
            evidence / "related_tests.txt",
            [str(python), "-m", "unittest", *RELATED_MODULES, "-v"],
            root,
        )
        write_command_evidence(
            evidence / "project_docs_validation.txt",
            [str(python), "scripts/reporting/validate_project_docs.py", "--root", "."],
            root,
        )
        write_command_evidence(
            evidence / "git_diff_check.txt",
            ["git", "diff", "--check"],
            root,
        )
        write_command_evidence(
            evidence / "python_compile.txt",
            [str(python), "-m", "py_compile", "src/payresolve_ai/evaluation/critical_v2_execution.py", "scripts/evaluation/week3_critical_v2_execution.py", DETACHED_VERIFIER, "tests/test_critical_v2_execution_readiness.py", *EXTRA_COMPILE_PATHS],
            root,
        )

        # Always construct a fresh exact-byte snapshot. Reusing a caller-provided
        # directory can silently omit historical dependencies and can cause an
        # editable install to import source from the working repository.
        isolated_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=f"ea1_r{BUNDLE_REVISION}_exact_snapshot_", dir=isolated_parent
        ) as isolated_text:
            isolated = Path(isolated_text)
            tracked_output = subprocess.check_output(
                ["git", "-C", str(root), "ls-tree", "-r", "-z", "--name-only", "HEAD"]
            )
            tracked_paths = [
                item.decode("utf-8")
                for item in tracked_output.split(b"\0")
                if item
            ]
            modified_tracked = set(
                subprocess.check_output(
                    ["git", "-C", str(root), "diff", "--name-only", "HEAD"],
                    text=True,
                ).splitlines()
            )
            for relative in tracked_paths:
                target = isolated / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                if relative not in modified_tracked and (root / relative).is_file():
                    shutil.copyfile(root / relative, target)
                else:
                    target.write_bytes(
                        subprocess.check_output(
                            ["git", "-C", str(root), "cat-file", "blob", f"HEAD:{relative}"]
                        )
                    )
            for relative in TASK_PATHS:
                copy_file(root / relative, isolated / relative)
            frozen_raw_source = root / FROZEN_RAW_BANKING77
            if not frozen_raw_source.is_dir():
                raise RuntimeError(
                    f"frozen Banking77 dependency missing: {frozen_raw_source}"
                )
            shutil.copytree(
                frozen_raw_source,
                isolated / FROZEN_RAW_BANKING77,
                dirs_exist_ok=True,
            )
            subprocess.run(["git", "init", "--quiet"], cwd=isolated, check=True)
            subprocess.run(
                ["git", "config", "user.name", "EA1 Evidence Builder"],
                cwd=isolated,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "ea1-evidence@invalid.local"],
                cwd=isolated,
                check=True,
            )
            subprocess.run(["git", "add", "--all"], cwd=isolated, check=True)
            subprocess.run(
                ["git", "commit", "--quiet", "-m", f"EA1 revision {BUNDLE_REVISION} exact snapshot"],
                cwd=isolated,
                check=True,
            )
            modules = [
                "tests." + path.stem
                for path in sorted((isolated / "tests").glob("test_*.py"))
                if path.name
                not in {
                    "test_feasibility_review_bundle.py",
                    "test_contract_amendment_review_bundle.py",
                }
            ]
            isolated_env = os.environ.copy()
            isolated_env["PYTHONPATH"] = str(isolated / "src")
            write_command_evidence(
                evidence / "isolated_full_suite.txt",
                [str(python), "-m", "unittest", *modules, "-v"],
                isolated,
                env=isolated_env,
            )

        preflight_commands = (
            ["git", "status", "--short"], ["git", "branch", "--show-current"],
            ["git", "rev-parse", "HEAD"], ["git", "rev-parse", "origin/main"],
            ["git", "diff", "--cached", "--name-only"],
        )
        preflight = []
        for command in preflight_commands:
            code, output_text = run(command, root)
            preflight.append("COMMAND: " + subprocess.list2cmdline(command) + f"\nEXIT_CODE: {code}\n{output_text}")
            if code:
                raise RuntimeError(f"preflight command failed: {command}")
        (evidence / "git_preflight.txt").write_text("\n".join(preflight), encoding="utf-8", newline="\n")

        status = {}
        for relative in TASK_PATHS:
            lines = subprocess.check_output(
                ["git", "-C", str(root), "status", "--porcelain", "--", relative], text=True
            ).splitlines()
            if not lines:
                raise RuntimeError(f"task path is not commit-relevant: {relative}")
            status[relative] = lines[0][:2].strip() or lines[0][:2]
        (evidence / "commit_relevant_paths.json").write_text(
            json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
        diff = subprocess.run(
            ["git", "-C", str(root), "diff", "--binary", "HEAD", "--", *TASK_PATHS],
            text=True, capture_output=True, check=True,
        ).stdout
        (evidence / "task_diff.patch").write_text(diff, encoding="utf-8", newline="\n")
        stat = subprocess.run(
            ["git", "-C", str(root), "diff", "--stat", "HEAD", "--", *TASK_PATHS],
            text=True, capture_output=True, check=True,
        ).stdout
        (evidence / "task_diff_stat.txt").write_text(stat, encoding="utf-8", newline="\n")

        candidate_after = {
            relative: sha256(root / relative)
            for relative in sorted(manifest["artifact_sha256"])
        }
        candidate_after[manifest_path.relative_to(root).as_posix()] = sha256(manifest_path)
        if candidate_after != candidate_before:
            raise RuntimeError("candidate fingerprint changed during bundle build")
        user_owned_after = collect_user_owned(root)
        if user_owned_after != user_owned_before:
            raise RuntimeError("user-owned fingerprint changed during bundle build")
        (evidence / "candidate_fingerprint_before_after.json").write_text(
            json.dumps({"before": candidate_before, "after": candidate_after, "match": True}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n",
        )
        (evidence / "user_owned_fingerprint_before_after.json").write_text(
            json.dumps({"before": user_owned_before, "after": user_owned_after, "match": True}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n",
        )

        files = []
        for path in sorted(item for item in bundle.rglob("*") if item.is_file() and item.name != "detached_inventory.json"):
            files.append({"path": path.relative_to(bundle).as_posix(), "size": path.stat().st_size, "sha256": sha256(path)})
        (bundle / "detached_inventory.json").write_text(
            json.dumps({"schema_version": "1.0", "files": files}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n",
        )

        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(item for item in bundle.rglob("*") if item.is_file()):
                archive.write(path, path.relative_to(bundle).as_posix())

    print(json.dumps({
        "status": "PASS", "zip": str(output), "zip_sha256": sha256(output),
        "zip_size": output.stat().st_size, "task_path_count": len(TASK_PATHS),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
