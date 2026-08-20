from __future__ import annotations

import unittest
from pathlib import Path

from payresolve_ai.generation.red1_verification import (
    AUTHORIZED_RED1_W3_001_MEMBERSHIP,
    AUTHORIZED_RED1_W3_001_MEMBERSHIP_PATH,
    ExactArtifactReader,
    Red1VerificationBoundaryError,
    authorize_red1_w3_001_membership,
)


class Red1VerificationBoundaryTests(unittest.TestCase):
    def test_exact_nonlocked_development_membership_is_accepted(self) -> None:
        self.assertEqual(
            AUTHORIZED_RED1_W3_001_MEMBERSHIP_PATH,
            authorize_red1_w3_001_membership(
                AUTHORIZED_RED1_W3_001_MEMBERSHIP,
                AUTHORIZED_RED1_W3_001_MEMBERSHIP_PATH,
            ),
        )

    def _assert_rejected_before_open(
        self,
        membership_id: str,
        membership_path: str,
    ) -> None:
        open_calls: list[Path] = []

        def spy(path: Path) -> bytes:
            open_calls.append(path)
            return b""

        reader = ExactArtifactReader(Path.cwd(), opener=spy)
        with self.assertRaises(Red1VerificationBoundaryError):
            authorized = authorize_red1_w3_001_membership(
                membership_id, membership_path
            )
            reader.read_bytes(authorized)
        self.assertEqual(0, len(open_calls))

    def test_consumed_w3_001_cr1_membership_is_rejected_before_open(self) -> None:
        self._assert_rejected_before_open(
            "w3_001_cr1_observed_holdout_now_development",
            "data/evaluation/evidence_gate_v2_holdout.jsonl",
        )

    def test_ev1_membership_is_rejected_before_open(self) -> None:
        self._assert_rejected_before_open(
            "W3_003_EV1",
            "data/evaluation/w3_003_independent_queries.jsonl",
        )

    def test_unknown_evaluation_membership_is_rejected_before_open(self) -> None:
        self._assert_rejected_before_open(
            "UNKNOWN_EVALUATION_MEMBERSHIP",
            "data/evaluation/unknown.jsonl",
        )

    def test_exact_id_with_non_allowlisted_path_is_rejected_before_open(self) -> None:
        self._assert_rejected_before_open(
            AUTHORIZED_RED1_W3_001_MEMBERSHIP,
            "data/evaluation/evidence_gate_dev_scenarios_v1.jsonl",
        )


if __name__ == "__main__":
    unittest.main()
