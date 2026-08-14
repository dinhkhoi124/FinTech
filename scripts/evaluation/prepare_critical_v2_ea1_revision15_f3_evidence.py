"""Prepare R15-F3 post-push committed-byte closure evidence without inference."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

from scripts.evaluation.verify_critical_v2_ea1_revision15_committed_tree import (
    BASE_COMMIT,
    CANDIDATE_PATH,
    audit_committed_tree,
    git_bytes,
    sha256,
)


KNOWN_MISMATCHES = (
    "scripts/evaluation/prepare_critical_v2_ea1_revision13_evidence.py",
    "scripts/evaluation/week3_critical_v2_execution.py",
    "tests/test_critical_v2_auth_date_closure.py",
    "tests/test_critical_v2_binding_fix.py",
)

F3_SCOPE = (
    "PROJECT_STATE.md",
    "TASKS.md",
    "docs/evaluation/W3-002-CR1-EA1_execution_readiness.md",
    "reports/week_03/daily/2026-08-14.md",
    "reports/week_03/experiments/W3-002-CR1-EA1_execution_readiness.md",
    "reports/week_03/week_03_summary.md",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_f3_committed_byte_audit.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_f3_root_cause.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_f3_corrective_scope.json",
    "reports/week_03/results/critical_eval_v2_ea1_revision15_f3_verification_summary.json",
    "scripts/evaluation/prepare_critical_v2_ea1_revision13_evidence.py",
    "scripts/evaluation/week3_critical_v2_execution.py",
    "tests/test_critical_v2_auth_date_closure.py",
    "tests/test_critical_v2_binding_fix.py",
    "scripts/evaluation/prepare_critical_v2_ea1_revision15_f3_evidence.py",
    "scripts/evaluation/verify_critical_v2_ea1_revision15_committed_tree.py",
    "scripts/evaluation/build_critical_v2_ea1_revision15_f3_review_bundle.py",
    "scripts/evaluation/verify_critical_v2_ea1_revision15_f3_bundle.py",
    "tests/test_critical_v2_execution_revision15_f3.py",
)


def write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--main-root", type=Path, required=True)
    parser.add_argument("--review-bundle", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    main_root = args.main_root.resolve()
    candidate = json.loads(git_bytes(root, BASE_COMMIT, CANDIDATE_PATH))
    expected = candidate["execution_artifact_sha256"]
    committed_rows = {
        row["path"]: row
        for row in audit_committed_tree(root, BASE_COMMIT, expected)
    }
    descriptions = {
        KNOWN_MISMATCHES[0]: "reviewed R13 compatibility evidence authoring required by R15 readiness hashes",
        KNOWN_MISMATCHES[1]: "required one-shot migrate-r15-continuation CLI",
        KNOWN_MISMATCHES[2]: "reviewed authorization-date closure regression compatibility",
        KNOWN_MISMATCHES[3]: "reviewed authorization/runtime binding regression compatibility",
    }
    rows = []
    with zipfile.ZipFile(args.review_bundle.resolve()) as archive:
        for path, reviewed_sha in sorted(expected.items()):
            reviewed = archive.read("readiness_files/" + path)
            working_path = main_root / path
            working = working_path.read_bytes() if working_path.is_file() else None
            committed = committed_rows[path]
            bundle_sha = sha256(reviewed)
            working_sha = sha256(working) if working is not None else None
            if committed["committed_matches_review"]:
                classification = (
                    "COMMITTED_MATCHES_REVIEW_WORKING_MATCHES"
                    if working_sha == reviewed_sha
                    else "USER_OWNED_OR_UNRELATED_DIRTY_CHANGE"
                )
            elif bundle_sha == reviewed_sha:
                classification = "REQUIRED_R15_REVIEWED_CHANGE"
            else:
                classification = "REVIEW_SOURCE_INCONSISTENCY"
            rows.append(
                {
                    "path": path,
                    "expected_reviewed_sha": reviewed_sha,
                    "reviewed_bundle_sha": bundle_sha,
                    "committed_r15_sha": committed["committed_sha"],
                    "working_tree_sha": working_sha,
                    "committed_matches_review": committed["committed_matches_review"],
                    "working_matches_review": working_sha == reviewed_sha,
                    "classification": classification,
                    "semantic_classification": descriptions.get(path),
                }
            )
        reviewed_cli = archive.read(
            "readiness_files/scripts/evaluation/week3_critical_v2_execution.py"
        )
    mismatches = [row for row in rows if not row["committed_matches_review"]]
    if len(rows) != 62 or tuple(row["path"] for row in mismatches) != KNOWN_MISMATCHES:
        raise RuntimeError("unexpected R15 committed-byte mismatch set")
    committed_cli = git_bytes(
        root, BASE_COMMIT, "scripts/evaluation/week3_critical_v2_execution.py"
    )
    cli_proof = {
        "classification": "R15_REQUIRED_CONTINUATION_CLI_NOT_COMMITTED",
        "token": "migrate-r15-continuation",
        "reviewed_contains_token": b"migrate-r15-continuation" in reviewed_cli,
        "committed_contains_token": b"migrate-r15-continuation" in committed_cli,
        "functional_omission": True,
    }
    if not cli_proof["reviewed_contains_token"] or cli_proof["committed_contains_token"]:
        raise RuntimeError("R15 CLI omission proof failed")
    results = root / "reports/week_03/results"
    write(
        results / "critical_eval_v2_ea1_revision15_f3_committed_byte_audit.json",
        {
            "status": "REPRODUCED_AND_CLASSIFIED",
            "classification": "R15_POST_PUSH_COMMITTED_BYTE_CLOSURE_MISMATCH",
            "base_commit": BASE_COMMIT,
            "audited_count": len(rows),
            "committed_mismatch_count": len(mismatches),
            "committed_mismatch_paths": [row["path"] for row in mismatches],
            "additional_mismatch_count": 0,
            "cli_omission_proof": cli_proof,
            "rows": rows,
        },
    )
    write(
        results / "critical_eval_v2_ea1_revision15_f3_root_cause.json",
        {
            "status": "ROOT_CAUSE_CONFIRMED",
            "classification": "R15_POST_PUSH_COMMITTED_BYTE_CLOSURE_MISMATCH",
            "cause_chain": [
                "authorization readiness hashes were computed from reviewed working-tree bytes",
                "the final proposed commit scope contained only 41 task paths",
                "manual staging verified exactly those 41 paths and their index bytes",
                "no gate compared all 62 hash-bound paths with the future readiness commit tree",
                "four dirty hash-bound compatibility/runtime files escaped the readiness commit",
            ],
            "bundle_internal_verification_was_correct_but_incomplete": True,
            "required_fix": "validate candidate hashes against committed corrective R tree and require every changed hash-bound path in proposed scope",
        },
    )
    write(
        results / "critical_eval_v2_ea1_revision15_f3_corrective_scope.json",
        {
            "status": "PROPOSED",
            "parent": BASE_COMMIT,
            "readiness_revision": 15,
            "path_count": len(F3_SCOPE),
            "paths": list(F3_SCOPE),
            "required_reviewed_omissions": list(KNOWN_MISMATCHES),
            "source_of_omission_bytes": "FINAL_R15_F2_REVIEW_BUNDLE_READINESS_FILES",
            "user_owned_unrelated_dirty_paths_excluded": True,
        },
    )
    write(
        results / "critical_eval_v2_ea1_revision15_f3_verification_summary.json",
        {
            "status": "PREPARED_FOR_SYNTHETIC_COMMIT_PROOF",
            "readiness_revision": 15,
            "model_calls": 0,
            "encoder_calls": 0,
            "retrieval_calls": 0,
            "generation_calls": 0,
            "primary_rerun": False,
            "reproduction_rerun": False,
            "migration_run": False,
        },
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "audited": len(rows),
                "mismatches": len(mismatches),
                "corrective_scope": len(F3_SCOPE),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
