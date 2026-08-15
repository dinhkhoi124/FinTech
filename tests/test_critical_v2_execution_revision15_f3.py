from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.evaluation.prepare_critical_v2_ea1_revision15_f3_evidence import (
    F3_SCOPE,
    KNOWN_MISMATCHES,
)
from scripts.evaluation.verify_critical_v2_ea1_revision15_committed_tree import (
    BASE_COMMIT,
    CommittedTreeClosureError,
    audit_committed_tree,
    candidate_at,
    git_bytes,
    sha256,
    verify_committed_tree,
    verify_proposed_scope,
)


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_F3 = "a8dc336b73be6ec91b2280c56c048d348329cff5"


class Revision15F3CommittedTreeClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.revision = HISTORICAL_F3
        self.candidate = candidate_at(ROOT, self.revision)
        self.expected = self.candidate["execution_artifact_sha256"]

    def test_corrective_commit_tree_closes_all_62_reviewed_hashes(self) -> None:
        rows = verify_committed_tree(ROOT, self.revision, self.expected)
        self.assertEqual(len(rows), 62)
        self.assertTrue(all(row["committed_matches_review"] for row in rows))

    def test_initial_r15_commit_reproduces_exact_four_mismatches(self) -> None:
        rows = audit_committed_tree(ROOT, BASE_COMMIT, self.expected)
        mismatches = tuple(
            row["path"] for row in rows if not row["committed_matches_review"]
        )
        self.assertEqual(mismatches, KNOWN_MISMATCHES)

    def test_required_continuation_cli_is_committed_only_in_corrective_r(self) -> None:
        path = "scripts/evaluation/week3_critical_v2_execution.py"
        token = b"migrate-r15-continuation"
        self.assertNotIn(token, git_bytes(ROOT, BASE_COMMIT, path))
        self.assertIn(token, git_bytes(ROOT, self.revision, path))

    def test_exact_corrective_scope_passes(self) -> None:
        proof = verify_proposed_scope(
            ROOT, BASE_COMMIT, self.revision, F3_SCOPE, self.expected
        )
        self.assertEqual(proof["actual_count"], len(F3_SCOPE))
        self.assertEqual(proof["hash_bound_changed_count"], 4)

    def test_hash_bound_changed_path_omission_rejects(self) -> None:
        scope = [path for path in F3_SCOPE if path != KNOWN_MISMATCHES[0]]
        with self.assertRaisesRegex(
            CommittedTreeClosureError, "hash-bound changed path omitted"
        ):
            verify_proposed_scope(ROOT, BASE_COMMIT, self.revision, scope, self.expected)

    def test_working_tree_only_candidate_hash_rejects(self) -> None:
        mutated = copy.deepcopy(self.expected)
        mutated[KNOWN_MISMATCHES[0]] = "0" * 64
        with self.assertRaisesRegex(
            CommittedTreeClosureError, "committed readiness byte mismatch"
        ):
            verify_committed_tree(ROOT, self.revision, mutated)

    def test_initial_committed_r_differs_from_candidate_rejects(self) -> None:
        with self.assertRaisesRegex(
            CommittedTreeClosureError, "committed readiness byte mismatch"
        ):
            verify_committed_tree(ROOT, BASE_COMMIT, self.expected)

    def test_unreviewed_committed_extra_path_rejects(self) -> None:
        scope = [path for path in F3_SCOPE if path != "PROJECT_STATE.md"]
        with self.assertRaisesRegex(
            CommittedTreeClosureError, "unreviewed extra committed path"
        ):
            verify_proposed_scope(ROOT, BASE_COMMIT, self.revision, scope, self.expected)

    def test_user_owned_uncommitted_path_is_excluded(self) -> None:
        path = ROOT / "f3_user_owned_untracked_control.tmp"
        path.write_bytes(b"user-owned dirty control\n")
        try:
            proof = verify_proposed_scope(
                ROOT, BASE_COMMIT, self.revision, F3_SCOPE, self.expected
            )
            self.assertEqual(proof["status"], "PASS")
        finally:
            path.unlink()

    def test_candidate_revision_7_manifest_is_23_of_23_in_commit_tree(self) -> None:
        config = json.loads(
            git_bytes(
                ROOT,
                self.revision,
                "configs/evaluation/critical_eval_v2_execution.json",
            )
        )
        manifest_path = config["candidate"]["manifest"]
        manifest = json.loads(git_bytes(ROOT, self.revision, manifest_path))
        rows = manifest["artifact_sha256"]
        self.assertEqual(len(rows), 23)
        self.assertTrue(
            all(
                sha256(git_bytes(ROOT, self.revision, path)) == expected
                for path, expected in rows.items()
            )
        )


if __name__ == "__main__":
    unittest.main()
