"""Build the detached R15-F3 committed-byte closure review bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path

from scripts.evaluation.prepare_critical_v2_ea1_revision15_f3_evidence import (
    F3_SCOPE,
    KNOWN_MISMATCHES,
)
from scripts.evaluation.verify_critical_v2_ea1_revision15_committed_tree import (
    BASE_COMMIT,
    candidate_at,
    git_bytes,
    sha256,
    verify_committed_tree,
    verify_proposed_scope,
)


PRESERVED_EVIDENCE = (
    "reports/week_03/results/critical_eval_v2_ea1_revision15_transition_contract_matrix.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_primary_preservation.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_f1_authority_finding.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_f1_negative_controls.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_f2_git_config_defect_reproduction.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_f2_real_repo_config_isolation.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_runtime_source_closure.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_isolated_migration.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_synthetic_premodel.json",
    "reports/week_03/results/critical_eval_v2_evaluation_authorization_candidate.json",
    "configs/evaluation/critical_eval_v2_execution.json",
)

LOCKED_PRIMARY = {
    "V0_raw": "c27ff7a80d3ed2214fca647ce46091a7ed2c8029ff0b8527fcad8d3e36844ab2",
    "V1_raw": "dff680373ff943adfe6379eb59add82b95254670653646ffc4abd946e562a608",
    "V2_raw": "943c4a7a1bc3e0d305962751256c1723d4e18ff8dd84b63fdd5b520532418a35",
    "raw_manifest": "114d29ec72a561886a8effd393510f9365e62f1d3c8783aa9def919fee04e0b3",
    "outcomes": "bb7715af1e22bbe1ce791f344c833358af7075ea6ae02adfc952f615dc1b64ce",
    "metrics": "ef480aae3d4d0f30e306c5fd9c2fb97ce1fe3dafda44c5a5caf7a4e592296c3b",
    "claim_audit": "3d6766797c65c876ce3070cef311587152b68655bd4ad7e88f8f753b754e80ae",
}


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--previous-review-bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    revision = args.revision
    parent = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", f"{revision}^"] , text=True
    ).strip()
    if parent != BASE_COMMIT:
        raise RuntimeError("synthetic corrective R parent mismatch")
    candidate = candidate_at(root, revision)
    expected = candidate["execution_artifact_sha256"]
    committed_rows = verify_committed_tree(root, revision, expected)
    scope_proof = verify_proposed_scope(
        root, BASE_COMMIT, revision, F3_SCOPE, expected
    )
    config = json.loads(
        git_bytes(root, revision, "configs/evaluation/critical_eval_v2_execution.json")
    )
    manifest_path = config["candidate"]["manifest"]
    manifest = json.loads(git_bytes(root, revision, manifest_path))
    candidate_exact = sum(
        sha256(git_bytes(root, revision, path)) == expected_sha
        for path, expected_sha in manifest["artifact_sha256"].items()
    )
    with tempfile.TemporaryDirectory(prefix="ea1_r15_f3_bundle_") as directory:
        bundle = Path(directory)
        for path in (*F3_SCOPE, *PRESERVED_EVIDENCE):
            write(bundle / "task_files" / path, git_bytes(root, revision, path))
        for path in expected:
            write(bundle / "readiness_files" / path, git_bytes(root, revision, path))
        with zipfile.ZipFile(args.previous_review_bundle.resolve()) as previous:
            for name in previous.namelist():
                if name.startswith("historical_references/") and not name.endswith("/"):
                    write(bundle / name, previous.read(name))
        proposed = [
            {
                "path": path,
                "bytes": len(git_bytes(root, revision, path)),
                "sha256": sha256(git_bytes(root, revision, path)),
            }
            for path in F3_SCOPE
        ]
        evidence = bundle / "evidence"
        evidence.mkdir(parents=True)
        (evidence / "proposed_commit_scope.json").write_text(
            json.dumps(
                {"status": "PASS", "count": len(proposed), "paths": proposed},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        proof = {
            "status": "PASS",
            "classification": "R15_POST_PUSH_COMMITTED_BYTE_CLOSURE_MISMATCH",
            "base_commit": BASE_COMMIT,
            "synthetic_corrective_r": subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", revision], text=True
            ).strip(),
            "synthetic_corrective_parent": parent,
            "committed_tree_hash_count": len(committed_rows),
            "committed_tree_exact_count": sum(
                row["committed_matches_review"] for row in committed_rows
            ),
            "candidate_manifest_exact_count": candidate_exact,
            "candidate_manifest_required_count": len(manifest["artifact_sha256"]),
            "known_corrected_paths": list(KNOWN_MISMATCHES),
            "scope_proof": scope_proof,
            "primary_hashes": LOCKED_PRIMARY,
            "model_calls": 0,
            "encoder_calls": 0,
            "retrieval_calls": 0,
            "generation_calls": 0,
            "migration_run": False,
            "reproduction_rerun": False,
            "primary_rerun": False,
            "synthetic_a15_run": False,
        }
        (evidence / "synthetic_corrective_r_proof.json").write_text(
            json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        ref = "refs/heads/r15-f3-review"
        subprocess.run(
            ["git", "-C", str(root), "update-ref", ref, revision], check=True
        )
        try:
            subprocess.run(
                ["git", "-C", str(root), "bundle", "create", str(evidence / "corrective_history.bundle"), ref],
                check=True,
                capture_output=True,
            )
        finally:
            subprocess.run(
                ["git", "-C", str(root), "update-ref", "-d", ref], check=True
            )
        verifier = root / "scripts/evaluation/verify_critical_v2_ea1_revision15_f3_bundle.py"
        write(bundle / verifier.name, verifier.read_bytes())
        files = [
            {
                "path": path.relative_to(bundle).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": file_sha(path),
            }
            for path in sorted(bundle.rglob("*"))
            if path.is_file()
        ]
        (bundle / "detached_inventory.json").write_text(
            json.dumps({"status": "PASS", "files": files}, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(bundle.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(bundle).as_posix())
    print(
        json.dumps(
            {
                "status": "PASS",
                "output": str(output),
                "bytes": output.stat().st_size,
                "sha256": file_sha(output),
                "inventory_count": len(files),
                "scope_count": len(F3_SCOPE),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
