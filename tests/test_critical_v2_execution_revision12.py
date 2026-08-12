"""Focused authorization-date topology regressions for EA1 Revision 12."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from payresolve_ai.evaluation import critical_v2_execution as execution


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/evaluation/critical_eval_v2_execution.json"
EXPECTED_ALLOWLIST = {
    "reports/week_03/results/critical_eval_v2_evaluation_authorization.json",
    "PROJECT_STATE.md",
    "TASKS.md",
    "reports/week_03/week_03_summary.md",
    "reports/week_03/daily/2026-08-12.md",
}


class CriticalV2ExecutionRevision12Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def _assert_extra_path_rejected(self, path: str) -> None:
        config = copy.deepcopy(self.config)
        config["authorization"]["allowed_authorization_commit_paths"].append(path)
        with self.assertRaisesRegex(
            execution.CriticalV2ExecutionError, "daily-path topology"
        ):
            execution.validate_authorization_daily_path_topology(config)

    def test_auth_date_01_exact_revision12_allowlist_passes(self) -> None:
        result = execution.validate_authorization_daily_path_topology(self.config)
        self.assertEqual(set(result["allowed_paths"]), EXPECTED_ALLOWLIST)

    def test_auth_date_02_previous_daily_path_rejected(self) -> None:
        self._assert_extra_path_rejected("reports/week_03/daily/2026-08-11.md")

    def test_auth_date_03_older_daily_path_rejected(self) -> None:
        self._assert_extra_path_rejected("reports/week_03/daily/2026-08-10.md")

    def test_auth_date_04_future_daily_path_rejected(self) -> None:
        self._assert_extra_path_rejected("reports/week_03/daily/2026-08-13.md")

    def test_auth_date_05_candidate_and_execution_paths_rejected(self) -> None:
        for path in (
            "data/evaluation/critical_eval_v2_mapping.jsonl",
            "src/payresolve_ai/evaluation/critical_v2_execution.py",
        ):
            with self.subTest(path=path):
                self._assert_extra_path_rejected(path)


if __name__ == "__main__":
    unittest.main()
