"""R13 deterministic review-scope coverage regressions."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from payresolve_ai.evaluation import critical_v2_execution as execution
from scripts.evaluation import build_critical_v2_ea1_revision13_review_bundle as builder


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/evaluation/critical_eval_v2_execution.json"
RETRIEVAL_TEST = "tests/test_retrieval_benchmark.py"
EXPECTED_RETRIEVAL_TEST_SHA256 = (
    "87bceeb60fd079bd380b095cd6a76ec714d871b0303a8215b5cd9bf7cb358fb7"
)


class CriticalV2ReviewScopeCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = execution.load_execution_config(CONFIG_PATH)

    def test_review_coverage_01_retrieval_test_is_readiness_bound(self) -> None:
        self.assertIn(RETRIEVAL_TEST, execution.READINESS_HASH_PATHS)
        candidate = json.loads(
            (ROOT / self.config["authorization"]["candidate"]).read_text(encoding="utf-8")
        )
        self.assertEqual(
            candidate["execution_artifact_sha256"][RETRIEVAL_TEST],
            EXPECTED_RETRIEVAL_TEST_SHA256,
        )

    def test_review_coverage_02_retrieval_test_is_a_bundle_task_file(self) -> None:
        self.assertIn(RETRIEVAL_TEST, builder.CORE_PATHS)
        self.assertEqual(
            execution.sha256_file(ROOT / RETRIEVAL_TEST),
            EXPECTED_RETRIEVAL_TEST_SHA256,
        )

    def test_review_coverage_03_omitted_task_owned_test_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "R13_REVIEW_SCOPE_COVERAGE_INCOMPLETE"):
            builder.classify_review_scope(
                ROOT,
                set(builder.CORE_PATHS) - {RETRIEVAL_TEST},
                observed_dirty=[RETRIEVAL_TEST],
            )

    def test_review_coverage_04_unreviewed_task_owned_path_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "R13_REVIEW_SCOPE_COVERAGE_INCOMPLETE"):
            builder.classify_review_scope(
                ROOT,
                set(builder.CORE_PATHS),
                observed_dirty=["tests/test_unreviewed_r13_task_owned.py"],
            )

    def test_review_coverage_05_protected_e1_is_excluded(self) -> None:
        result = builder.classify_review_scope(
            ROOT,
            set(builder.CORE_PATHS),
            observed_dirty=sorted(builder.PROTECTED_E1_PATHS),
        )
        self.assertEqual(
            {row["category"] for row in result["rows"]},
            {"PROTECTED_E1_EXCLUDE"},
        )

    def test_review_coverage_06_user_owned_and_zip_paths_are_excluded(self) -> None:
        result = builder.classify_review_scope(
            ROOT,
            set(builder.CORE_PATHS),
            observed_dirty=[
                "docs/product_v2/00_PRODUCT_V2_INDEX.md",
                "reports/week_03/review_bundles/example.zip",
            ],
        )
        categories = {row["path"]: row["category"] for row in result["rows"]}
        self.assertEqual(
            categories["docs/product_v2/00_PRODUCT_V2_INDEX.md"],
            "USER_OWNED_EXCLUDE",
        )
        self.assertEqual(
            categories["reports/week_03/review_bundles/example.zip"],
            "REVIEW_ZIP_EXCLUDE",
        )


if __name__ == "__main__":
    unittest.main()
