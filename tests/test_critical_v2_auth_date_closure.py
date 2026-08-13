"""Active R13 authorization-date and enforcement-closure regressions."""

from __future__ import annotations

import copy
import inspect
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from payresolve_ai.evaluation import critical_v2_execution as execution


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/evaluation/critical_eval_v2_execution.json"
DAILY_13 = "reports/week_03/daily/2026-08-13.md"
EXPECTED_ALLOWLIST = {
    "reports/week_03/results/critical_eval_v2_evaluation_authorization.json",
    "PROJECT_STATE.md",
    "TASKS.md",
    "reports/week_03/week_03_summary.md",
    DAILY_13,
}
ENFORCEMENT_SYMBOLS = (
    "canonical_package_inventory",
    "stable_environment_identity",
    "environment_contract_payload",
    "load_environment_contract",
    "_validate_authorization_payload",
    "verify_execution_authorization",
    "freeze_or_verify_runtime_environment",
    "validate_authorization_daily_path_topology",
    "run_critical",
)


class CriticalV2AuthDateClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = execution.load_execution_config(CONFIG_PATH)

    def _replace_daily(self, replacement: str) -> dict:
        config = copy.deepcopy(self.config)
        paths = config["authorization"]["allowed_authorization_commit_paths"]
        config["authorization"]["allowed_authorization_commit_paths"] = [
            replacement if path == DAILY_13 else path for path in paths
        ]
        return config

    def _assert_rejected(self, config: dict) -> None:
        with self.assertRaisesRegex(
            execution.CriticalV2ExecutionError, "daily-path topology"
        ):
            execution.validate_authorization_daily_path_topology(config)

    def test_auth13_date_01_exact_five_path_allowlist_passes(self) -> None:
        result = execution.validate_authorization_daily_path_topology(self.config)
        self.assertEqual(set(result["allowed_paths"]), EXPECTED_ALLOWLIST)
        self.assertEqual(result["reviewed_daily_report_path"], DAILY_13)

    def test_auth13_date_02_revision12_daily_is_stale(self) -> None:
        self._assert_rejected(
            self._replace_daily("reports/week_03/daily/2026-08-12.md")
        )

    def test_auth13_date_03_revision11_daily_is_stale(self) -> None:
        self._assert_rejected(
            self._replace_daily("reports/week_03/daily/2026-08-11.md")
        )

    def test_auth13_date_04_revision14_daily_is_unreviewed(self) -> None:
        self._assert_rejected(
            self._replace_daily("reports/week_03/daily/2026-08-14.md")
        )

    def test_auth13_date_05_source_or_candidate_path_is_rejected(self) -> None:
        for path in (
            "src/payresolve_ai/evaluation/critical_v2_execution.py",
            "data/evaluation/critical_eval_v2_mapping.jsonl",
        ):
            with self.subTest(path=path):
                config = copy.deepcopy(self.config)
                config["authorization"]["allowed_authorization_commit_paths"].append(path)
                self._assert_rejected(config)

    def test_auth13_date_06_both_revision12_and_revision13_are_rejected(self) -> None:
        config = copy.deepcopy(self.config)
        config["authorization"]["allowed_authorization_commit_paths"].append(
            "reports/week_03/daily/2026-08-12.md"
        )
        self._assert_rejected(config)

    def test_auth13_date_07_missing_revision13_daily_is_rejected(self) -> None:
        config = copy.deepcopy(self.config)
        config["authorization"]["allowed_authorization_commit_paths"].remove(DAILY_13)
        self._assert_rejected(config)

    def test_enforcement_symbols_are_in_root_source_closure_and_authorization(self) -> None:
        relative = "src/payresolve_ai/evaluation/critical_v2_execution.py"
        closure = execution.runtime_source_closure_payload(ROOT, self.config)
        row = next(item for item in closure["modules"] if item["path"] == relative)
        candidate = json.loads(
            (ROOT / self.config["authorization"]["candidate"]).read_text(encoding="utf-8")
        )
        self.assertIn(relative, execution.READINESS_HASH_PATHS)
        self.assertEqual(candidate["execution_artifact_sha256"][relative], row["sha256"])
        self.assertTrue(set(ENFORCEMENT_SYMBOLS) <= set(row["runtime_used_symbols"]))
        for symbol in ENFORCEMENT_SYMBOLS:
            with self.subTest(symbol=symbol):
                function = getattr(execution, symbol)
                self.assertEqual(Path(inspect.getsourcefile(function)).resolve(), (ROOT / relative).resolve())

    def test_critical_execution_source_tamper_rejected_before_model(self) -> None:
        relative = "src/payresolve_ai/evaluation/critical_v2_execution.py"
        candidate = json.loads(
            (ROOT / self.config["authorization"]["candidate"]).read_text(encoding="utf-8")
        )
        candidate["evaluation_authorized"] = True
        candidate["authorization_status"] = "AUTHORIZED_FOR_PRIMARY_EXECUTION"
        candidate["readiness_commit_binding"] = "BOUND_TO_REVIEWED_READINESS_IMPLEMENTATION_COMMIT"
        candidate["senior_authorization_claimed"] = True
        candidate["senior_authorization_verdict"] = self.config["authorization"]["required_verdict"]
        with tempfile.TemporaryDirectory(prefix="ea1_r13_auth_date_") as temporary:
            isolated = Path(temporary)
            for bound in execution.READINESS_HASH_PATHS:
                target = isolated / bound
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / bound, target)
            tampered = isolated / relative
            tampered.write_bytes(tampered.read_bytes() + b"\n# isolated enforcement tamper\n")
            with self.assertRaisesRegex(
                execution.CriticalV2ExecutionError,
                "authorization execution source/config/test hash mismatch",
            ):
                execution._validate_authorization_payload(
                    isolated,
                    isolated / "configs/evaluation/critical_eval_v2_execution.json",
                    self.config,
                    candidate,
                )


if __name__ == "__main__":
    unittest.main()
