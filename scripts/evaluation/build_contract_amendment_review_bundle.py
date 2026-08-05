"""Build the W3-002-CR1 Option A contract-amendment review bundle.

The builder copies contract/reporting/preservation evidence only. It never
imports or executes candidate evaluation, retrieval, generation, or model code.
"""

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
from typing import Any


DECISION_BUNDLE_NAME = "W3-002-CR1_contract_feasibility_review_bundle.zip"
DECISION_BUNDLE_SHA256 = "bc7317000005859f2e4b215cf0c4f687e5e284a4a004270d81f9f5abd0074786"


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


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def copy_file(root: Path, staging: Path, relative: str, target: str | None = None) -> None:
    source = root / relative
    if not source.is_file():
        raise RuntimeError(f"missing bundle input: {relative}")
    destination = staging / (target or relative)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def git_output(root: Path, arguments: list[str]) -> dict[str, Any]:
    process = subprocess.run(["git", *arguments], cwd=root, text=True, capture_output=True, encoding="utf-8", errors="replace")
    return {"command": "git " + " ".join(arguments), "stdout": process.stdout, "stderr": process.stderr, "exit_code": process.returncode}


def copy_preservation(root: Path, staging: Path) -> dict[str, int]:
    results = root / "reports/week_03/results"
    rev2 = read_json(results / "critical_eval_v2_revision_2_rejected_inventory.json")
    rev3 = read_json(results / "critical_eval_v2_revision_3_rejected_inventory.json")
    rev4 = read_json(results / "critical_eval_v2_revision_4_rejected_inventory.json")
    for relative in rev2["artifact_sha256"]:
        copy_file(root, staging, relative)
    for item in rev3["artifacts"]:
        copy_file(root, staging, item["path"])
    for item in rev4["artifacts"]:
        relative = f"reports/week_03/rejected/critical_eval_v2_revision_4/{item['path']}"
        copy_file(root, staging, relative)
    historical = read_json(results / "critical_eval_v2_historical_hash_verification.json")
    for relative in historical:
        copy_file(root, staging, relative)
    return {"revision_2": 17, "revision_3": 18, "revision_4": 19, "historical": 18}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--decision-bundle", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    decision_bundle = args.decision_bundle.resolve()
    if sha256(decision_bundle) != DECISION_BUNDLE_SHA256:
        raise RuntimeError("approved decision bundle SHA-256 mismatch")

    repository_files = [
        "configs/evaluation/critical_eval_v2_contract_option_a.json",
        "docs/evaluation/W3-002-CR1_amended_contract.md",
        "docs/evaluation/critical_eval_v2_response_taxonomy.md",
        "PROJECT_STATE.md",
        "TASKS.md",
        "reports/week_03/daily/2026-08-05.md",
        "reports/week_03/week_03_summary.md",
        "reports/week_03/decisions/W3-002-CR1_contract_amendment_options.md",
        "reports/week_03/experiments/W3-002-CR1_contract_decision_evidence.md",
        "reports/week_03/results/critical_eval_v2_contract_metric_spec.json",
        "reports/week_03/results/critical_eval_v2_revision_5_acceptance_checklist.json",
        "reports/week_03/results/critical_eval_v2_contract_amendment_verification.txt",
        "reports/week_03/results/critical_eval_v2_revision_2_rejected_inventory.json",
        "reports/week_03/results/critical_eval_v2_revision_3_rejected_inventory.json",
        "reports/week_03/results/critical_eval_v2_revision_4_rejected_inventory.json",
        "reports/week_03/results/critical_eval_v2_historical_hash_verification.json",
        "src/payresolve_ai/evaluation/critical_v2_contract.py",
        "scripts/evaluation/validate_critical_v2_contract.py",
        "scripts/evaluation/build_contract_amendment_review_bundle.py",
        "scripts/evaluation/verify_contract_amendment_review_bundle.py",
        "tests/test_critical_v2_contract.py",
        "tests/test_contract_amendment_review_bundle.py",
    ]

    with tempfile.TemporaryDirectory(prefix="w3-002-cr1-contract-amendment-") as temporary:
        staging = Path(temporary)
        for relative in repository_files:
            copy_file(root, staging, relative)
        preservation_counts = copy_preservation(root, staging)
        decision_target = staging / "approved_decision" / DECISION_BUNDLE_NAME
        decision_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(decision_bundle, decision_target)
        write_json(staging / "review/decision_bundle_reference.json", {
            "path_in_bundle": f"approved_decision/{DECISION_BUNDLE_NAME}",
            "sha256": DECISION_BUNDLE_SHA256,
            "inventoried_payload_files": 67,
            "detached_inventory_files": 1,
            "zip_entries": 68,
        })
        write_json(staging / "review/lifecycle.json", {
            "senior_contract_amendment_approved": True,
            "contract_amendment_option": "OPTION_A",
            "contract_amendment_distribution": "40_STANDARD_15_SAFE_CORRECTIVE_5_ABSTAIN",
            "candidate_revision_4": "REJECTED / PRESERVED AS REVIEW HISTORY",
            "candidate_revision_5_created": False,
            "senior_semantic_review_approved": False,
            "evaluation_authorized": False,
            "critical_evaluated": False,
            "model_verdict": "NOT_ESTABLISHED",
            "week_3_p0": "BLOCKED / IN_PROGRESS",
            "week_4": "BLOCKED / NOT STARTED",
        })
        commands = [
            ["status"], ["status", "--short"], ["branch", "--show-current"],
            ["log", "-1", "--oneline"], ["rev-parse", "HEAD"],
            ["rev-parse", "origin/main"], ["diff", "--cached", "--name-only"],
            ["diff", "--check"], ["diff", "--stat"], ["diff", "--name-only"],
        ]
        write_json(staging / "verification/git_evidence.json", {"commands": [git_output(root, command) for command in commands]})
        (staging / "verification/exact_commands.txt").write_text(
            ".\\.venv-semantic\\Scripts\\python.exe scripts/evaluation/validate_critical_v2_contract.py --root . --decision-bundle <approved-bundle>\n"
            ".\\.venv-semantic\\Scripts\\python.exe -m unittest discover -s tests -p \"test_critical_v2_contract.py\" -v\n"
            ".\\.venv-semantic\\Scripts\\python.exe -m unittest discover -s tests -p \"test_contract_amendment_review_bundle.py\" -v\n"
            ".\\.venv-semantic\\Scripts\\python.exe scripts/reporting/validate_project_docs.py --root .\n"
            "git diff --check\n"
            "python scripts/evaluation/verify_contract_amendment_review_bundle.py --root .\n",
            encoding="utf-8", newline="\n",
        )
        inventory = [
            {"path": path.relative_to(staging).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in sorted(item for item in staging.rglob("*") if item.is_file())
        ]
        write_json(staging / "bundle_inventory.json", {
            "task_id": "W3-002-CR1",
            "package_type": "SENIOR_APPROVED_OPTION_A_CONTRACT_AMENDMENT_REVIEW",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "repository_head": git_output(root, ["rev-parse", "HEAD"])["stdout"].strip(),
            "file_count_excluding_inventory": len(inventory),
            "files": inventory,
            "inventory_self_hash_excluded_to_avoid_recursive_hashing": True,
            "preservation_counts": preservation_counts,
            "standalone_verification_command": "python scripts/evaluation/verify_contract_amendment_review_bundle.py --root .",
            "candidate_revision_5_created": False,
            "senior_semantic_review_approved": False,
            "evaluation_authorized": False,
            "inference_executed": False,
            "repository_staged_committed_or_pushed": False,
            "excluded": [".gitignore", ".git", "docs/refactor", ".venv*", "artifacts", "outputs", "models", "embeddings", ".env", "secrets"],
        })
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            output.unlink()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(item for item in staging.rglob("*") if item.is_file()):
                info = zipfile.ZipInfo(path.relative_to(staging).as_posix(), date_time=(2026, 8, 5, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(output) as archive:
        count = len(archive.infolist())
    print(json.dumps({"zip_path": str(output), "sha256": sha256(output), "size_bytes": output.stat().st_size, "file_count": count}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
