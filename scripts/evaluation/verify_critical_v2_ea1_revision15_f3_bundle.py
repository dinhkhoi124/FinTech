"""Detached verifier for R15-F3 committed-tree closure review bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


BASE = "5e89ec1ed2b7284ed5f263be674e3cb20e0facaf"
CANDIDATE = "reports/week_03/results/critical_eval_v2_evaluation_authorization_candidate.json"
KNOWN = {
    "scripts/evaluation/prepare_critical_v2_ea1_revision13_evidence.py",
    "scripts/evaluation/week3_critical_v2_execution.py",
    "tests/test_critical_v2_auth_date_closure.py",
    "tests/test_critical_v2_binding_fix.py",
}
LOCKED_PRIMARY = {
    "V0_raw": "c27ff7a80d3ed2214fca647ce46091a7ed2c8029ff0b8527fcad8d3e36844ab2",
    "V1_raw": "dff680373ff943adfe6379eb59add82b95254670653646ffc4abd946e562a608",
    "V2_raw": "943c4a7a1bc3e0d305962751256c1723d4e18ff8dd84b63fdd5b520532418a35",
    "raw_manifest": "114d29ec72a561886a8effd393510f9365e62f1d3c8783aa9def919fee04e0b3",
    "outcomes": "bb7715af1e22bbe1ce791f344c833358af7075ea6ae02adfc952f615dc1b64ce",
    "metrics": "ef480aae3d4d0f30e306c5fd9c2fb97ce1fe3dafda44c5a5caf7a4e592296c3b",
    "claim_audit": "3d6766797c65c876ce3070cef311587152b68655bd4ad7e88f8f753b754e80ae",
}


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git_bytes(repo: Path, revision: str, path: str) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{revision}:{path}"]
    )


def verify(root: Path) -> dict:
    inventory = read(root / "detached_inventory.json")["files"]
    for row in inventory:
        path = root / row["path"]
        if (
            not path.is_file()
            or path.stat().st_size != row["bytes"]
            or sha(path.read_bytes()) != row["sha256"]
        ):
            raise RuntimeError(f"inventory mismatch: {row['path']}")
    proof = read(root / "evidence/synthetic_corrective_r_proof.json")
    scope = read(root / "evidence/proposed_commit_scope.json")
    with tempfile.TemporaryDirectory(prefix="ea1_r15_f3_detached_git_") as directory:
        repo = Path(directory) / "repo"
        subprocess.run(
            [
                "git", "clone", "--no-checkout", "-b", "r15-f3-review",
                str(root / "evidence/corrective_history.bundle"), str(repo),
            ],
            check=True,
            capture_output=True,
        )
        revision = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "refs/heads/r15-f3-review"],
            text=True,
        ).strip()
        parent = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", f"{revision}^"], text=True
        ).strip()
        if revision != proof["synthetic_corrective_r"] or parent != BASE:
            raise RuntimeError("corrective topology mismatch")
        candidate = json.loads(git_bytes(repo, revision, CANDIDATE))
        expected = candidate["execution_artifact_sha256"]
        if len(expected) != 62:
            raise RuntimeError("candidate readiness hash count mismatch")
        for path, expected_sha in expected.items():
            if sha(git_bytes(repo, revision, path)) != expected_sha:
                raise RuntimeError(f"committed-tree closure mismatch: {path}")
        proposed = {row["path"] for row in scope["paths"]}
        actual_raw = subprocess.check_output(
            ["git", "-C", str(repo), "diff", "--name-only", "-z", BASE, revision]
        )
        actual = {item.decode("utf-8") for item in actual_raw.split(b"\0") if item}
        if actual != proposed or len(actual) != scope["count"]:
            raise RuntimeError("corrective proposed-scope closure mismatch")
        for row in scope["paths"]:
            payload = git_bytes(repo, revision, row["path"])
            if len(payload) != row["bytes"] or sha(payload) != row["sha256"]:
                raise RuntimeError(f"corrective scope byte mismatch: {row['path']}")
        base_mismatches = {
            path
            for path, expected_sha in expected.items()
            if sha(git_bytes(repo, BASE, path)) != expected_sha
        }
        if base_mismatches != KNOWN:
            raise RuntimeError("initial R15 mismatch set mismatch")
        cli = "scripts/evaluation/week3_critical_v2_execution.py"
        token = b"migrate-r15-continuation"
        if token in git_bytes(repo, BASE, cli) or token not in git_bytes(repo, revision, cli):
            raise RuntimeError("functional CLI omission proof mismatch")
        config = json.loads(
            git_bytes(repo, revision, "configs/evaluation/critical_eval_v2_execution.json")
        )
        manifest_path = config["candidate"]["manifest"]
        manifest = json.loads(git_bytes(repo, revision, manifest_path))
        if len(manifest["artifact_sha256"]) != 23 or any(
            sha(git_bytes(repo, revision, path)) != expected_sha
            for path, expected_sha in manifest["artifact_sha256"].items()
        ):
            raise RuntimeError("Candidate Revision 7 committed-byte mismatch")
    historical = root / "historical_references"
    for key, expected_sha in LOCKED_PRIMARY.items():
        path = historical / config["evaluation_outputs"]["primary"][key]
        if not path.is_file() or sha(path.read_bytes()) != expected_sha:
            raise RuntimeError(f"PRIMARY preservation mismatch: {key}")
    state_path = historical / config["evaluation_outputs"]["execution_state"]
    runtime_path = historical / config["continuation"]["historical_runtime_environment"]["path"]
    if (
        sha(state_path.read_bytes()) != "6cab044610b566f4b7c6ecfbcafc5b49868891c167543ef950b20e29710416bd"
        or read(state_path)["state"] != "PRIMARY_EVALUATED"
        or sha(runtime_path.read_bytes()) != "b036b8e337f809817dbbc6006e36d892c63480df2a919d9775279195c85bd22d"
    ):
        raise RuntimeError("state/runtime preservation mismatch")
    task = root / "task_files/reports/week_03/results"
    audit = read(task / "critical_eval_v2_ea1_revision15_f3_committed_byte_audit.json")
    matrix = read(task / "critical_eval_v2_ea1_revision15_transition_contract_matrix.json")
    f1 = read(task / "critical_eval_v2_ea1_revision15_f1_negative_controls.json")
    f2 = read(task / "critical_eval_v2_ea1_revision15_f2_real_repo_config_isolation.json")
    summary = read(task / "critical_eval_v2_ea1_revision15_f3_verification_summary.json")
    if audit["audited_count"] != 62 or set(audit["committed_mismatch_paths"]) != KNOWN:
        raise RuntimeError("F3 audit evidence mismatch")
    if matrix["exact_count"] != 12 or matrix["transition_count"] != 12:
        raise RuntimeError("transition matrix mismatch")
    if f1["required_control_count"] != 16 or f1["status"] != "PASS":
        raise RuntimeError("F1 preservation mismatch")
    if f2["status"] != "PASS" or not f2["common_config_bytes_unchanged"]:
        raise RuntimeError("F2 isolation preservation mismatch")
    if summary["status"] != "PASS" or summary["full_executable_suite"]["passed"] < 799:
        raise RuntimeError("F3 regression summary mismatch")
    return {
        "status": "PASS",
        "inventory_count": len(inventory),
        "corrective_scope_count": scope["count"],
        "committed_tree_exact_count": 62,
        "candidate_exact_count": 23,
        "primary_exact_count": 7,
        "transition_count": 12,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.bundle_root.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
