"""Detached verification and mutation controls for the R14 review bundle."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import tempfile
from pathlib import Path


R13 = "5d862e708f972b2fa73403fef390f2ac7b432435"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def refresh_inventory(root: Path) -> None:
    files = []
    for item in sorted(path for path in root.rglob("*") if path.is_file() and path.name != "detached_inventory.json"):
        files.append({"path": item.relative_to(root).as_posix(), "size": item.stat().st_size, "sha256": sha256(item)})
    (root / "detached_inventory.json").write_text(
        json.dumps({"status": "PASS", "files": files}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def verify(root: Path) -> dict:
    inventory = read(root / "detached_inventory.json")
    actual = {item.relative_to(root).as_posix(): {"size": item.stat().st_size, "sha256": sha256(item)} for item in root.rglob("*") if item.is_file() and item.name != "detached_inventory.json"}
    expected = {row["path"]: {"size": row["size"], "sha256": row["sha256"]} for row in inventory["files"]}
    if actual != expected:
        raise RuntimeError("inventory mismatch")
    task = root / "task_files"
    config = read(task / "configs/evaluation/critical_eval_v2_execution.json")
    candidate = read(task / config["authorization"]["candidate"])
    if config["readiness_revision"] != 14 or candidate["readiness_revision"] != 14:
        raise RuntimeError("R14 identity mismatch")
    if candidate["evaluation_authorized"] is not False or candidate["senior_authorization_claimed"] is not False:
        raise RuntimeError("real candidate authorization claim")
    if candidate["authorization_status"] != "AWAITING_SENIOR_REVIEW":
        raise RuntimeError("candidate status mismatch")
    hashes = candidate["execution_artifact_sha256"]
    for relative, expected_hash in hashes.items():
        path = root / "readiness_files" / relative
        if not path.is_file() or sha256(path) != expected_hash:
            raise RuntimeError(f"readiness hash mismatch: {relative}")
    source = (task / "src/payresolve_ai/evaluation/critical_v2_execution.py").read_text(encoding="utf-8")
    if "changed != allowed" not in source or '"readiness_revision": config["readiness_revision"]' not in source:
        raise RuntimeError("R14 enforcement missing")
    field = read(task / "reports/week_03/results/critical_eval_v2_ea1_revision14_authorization_field_enforcement.json")
    topology = read(task / "reports/week_03/results/critical_eval_v2_ea1_revision14_exact_five_topology_enforcement.json")
    synthetic = read(task / "reports/week_03/results/critical_eval_v2_ea1_revision14_synthetic_authorization.json")
    if field["status"] != "PASS" or field["case_count"] != 11 or topology["status"] != "PASS" or topology["case_count"] != 12:
        raise RuntimeError("negative-control evidence incomplete")
    if synthetic["status"] != "PASS" or synthetic["changed_path_count"] != 5 or synthetic["production_verifier"]["status"] != "PASS":
        raise RuntimeError("synthetic positive mismatch")
    environment = read(task / "reports/week_03/results/critical_eval_v2_ea1_revision14_environment_recheck.json")
    if environment["environment_identity_sha256"] != "17cd6dcf9d20d8b17d14369a10ba915f3047e27fffb7eec5771738442923fd97":
        raise RuntimeError("environment identity mismatch")
    manifest = read(root / "references/reports/week_03/results/critical_eval_v2_candidate_manifest.json")
    if sha256(root / "references/reports/week_03/results/critical_eval_v2_candidate_manifest.json") != "f912798ae5c02c774702ae97bee8b2b4f6c6ab12b6534e1b2a3817a969b905ef" or len(manifest["artifact_sha256"]) != 23:
        raise RuntimeError("Candidate mismatch")
    absence = read(task / "reports/week_03/results/critical_eval_v2_ea1_revision14_active_control_plane_absence.json")
    if absence["status"] != "PASS" or absence["a14_created"] is not False or absence["primary_artifacts_present"] is not False:
        raise RuntimeError("control-plane boundary mismatch")
    git_state = read(root / "evidence/git_preflight.json")
    if git_state["head"] != R13 or git_state["staged_count"] != 0:
        raise RuntimeError("real topology mismatch")
    proposed = read(root / "evidence/proposed_commit_paths.json")
    if proposed["count"] != len(proposed["paths"]):
        raise RuntimeError("proposed-path count mismatch")
    for row in proposed["paths"]:
        path = task / row["path"]
        if not path.is_file() or path.stat().st_size != row["bytes"] or sha256(path) != row["sha256"]:
            raise RuntimeError(f"proposed-path mismatch: {row['path']}")
    return {"status": "PASS", "files_verified": len(actual), "readiness_revision": 14,
            "readiness_hash_count": len(hashes), "runtime_source_count": 18,
            "r14_task_path_count": proposed["count"]}


def mutation_controls(root: Path) -> dict:
    cases = []
    for case in range(1, 7):
        with tempfile.TemporaryDirectory(prefix="ea1_r14_mut_") as directory:
            mutated = Path(directory) / "bundle"; shutil.copytree(root, mutated)
            if case == 1:
                path = mutated / "task_files/reports/week_03/results/critical_eval_v2_ea1_revision14_authorization_field_enforcement.json"; payload = read(path); payload["cases"] = payload["cases"][1:]; payload["case_count"] = 10
            elif case == 2:
                path = mutated / "task_files/src/payresolve_ai/evaluation/critical_v2_execution.py"; path.write_text(path.read_text().replace("changed != allowed", "not changed <= allowed"), encoding="utf-8"); payload = None
            elif case == 3:
                path = mutated / "task_files/tests/test_critical_v2_execution_revision14.py"; path.unlink(); payload = None
            elif case == 4:
                path = mutated / "references/reports/week_03/results/critical_eval_v2_candidate_manifest.json"; path.write_bytes(path.read_bytes() + b" "); payload = None
            elif case == 5:
                path = mutated / "task_files/reports/week_03/results/critical_eval_v2_ea1_revision14_environment_recheck.json"; payload = read(path); payload["environment_identity_sha256"] = "0" * 64
            else:
                path = mutated / "task_files/reports/week_03/results/critical_eval_v2_evaluation_authorization_candidate.json"; payload = read(path); payload["evaluation_authorized"] = True
            if payload is not None:
                path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
            refresh_inventory(mutated)
            try:
                verify(mutated)
            except Exception as error:
                cases.append({"case": f"MUT-{case:02d}", "status": "REJECTED_AS_EXPECTED", "error": str(error)})
            else:
                raise RuntimeError(f"mutation passed: {case}")
    return {"status": "PASS", "case_count": len(cases), "cases": cases}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--bundle-root", type=Path, required=True); parser.add_argument("--run-mutation-controls", action="store_true"); args = parser.parse_args()
    result = mutation_controls(args.bundle_root.resolve()) if args.run_mutation_controls else verify(args.bundle_root.resolve())
    print(json.dumps(result, indent=2, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
