from __future__ import annotations

import copy
import unittest
from pathlib import Path

from payresolve_ai.evaluation.critical_v2_feasibility import (
    EXPECTED_ANSWER_SAFE_CORRECTIVE_IDS,
    FeasibilityValidationError,
    validate_category_summary,
    validate_feasibility_package,
    validate_hard_negative_feasibility,
    validate_negative_matrix,
    validate_positive_defects,
    validate_provenance,
)


ROOT = Path(__file__).resolve().parents[1]


class CriticalV2FeasibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import json

        results = ROOT / "reports/week_03/results"
        cls.matrix = [json.loads(line) for line in (results / "critical_eval_v2_revision_4_negative_feasibility_matrix.jsonl").read_text(encoding="utf-8").splitlines() if line]
        cls.category = json.loads((results / "critical_eval_v2_revision_4_category_feasibility.json").read_text(encoding="utf-8"))
        cls.provenance = json.loads((results / "critical_eval_v2_revision_4_pass_b_provenance_audit.json").read_text(encoding="utf-8"))
        cls.defects = [json.loads(line) for line in (results / "critical_eval_v2_revision_4_positive_support_defects.jsonl").read_text(encoding="utf-8").splitlines() if line]
        cls.hard = json.loads((results / "critical_eval_v2_revision_4_hard_negative_feasibility.json").read_text(encoding="utf-8"))

    def test_complete_package(self) -> None:
        result = validate_feasibility_package(ROOT)
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["evaluation_authorized"])

    def test_exact_distribution(self) -> None:
        counts = validate_negative_matrix(self.matrix)
        self.assertEqual(counts["ANSWER_SAFE_CORRECTIVE"], 15)
        self.assertEqual(counts["ABSTAIN_ESCALATE"], 5)

    def test_exact_corrective_ids(self) -> None:
        actual = {row["query_id"] for row in self.matrix if row["recommended_expected_response"] == "ANSWER_SAFE_CORRECTIVE"}
        self.assertEqual(actual, EXPECTED_ANSWER_SAFE_CORRECTIVE_IDS)

    def test_duplicate_negative_id_fails(self) -> None:
        rows = copy.deepcopy(self.matrix)
        rows[-1]["query_id"] = rows[0]["query_id"]
        with self.assertRaises(FeasibilityValidationError):
            validate_negative_matrix(rows)

    def test_answerability_mismatch_fails(self) -> None:
        rows = copy.deepcopy(self.matrix)
        rows[0]["complete_safe_corrective_answer_possible"] = False
        with self.assertRaises(FeasibilityValidationError):
            validate_negative_matrix(rows)

    def test_missing_reviewer_provenance_fails(self) -> None:
        rows = copy.deepcopy(self.matrix)
        rows[0]["reviewer_status"] = ""
        with self.assertRaises(FeasibilityValidationError):
            validate_negative_matrix(rows)

    def test_category_summary_matches_matrix(self) -> None:
        validate_category_summary(self.category, self.matrix)

    def test_category_count_mismatch_fails(self) -> None:
        summary = copy.deepcopy(self.category)
        summary["categories"][0]["required_count"] += 1
        with self.assertRaises(FeasibilityValidationError):
            validate_category_summary(summary, self.matrix)

    def test_provenance_counts(self) -> None:
        validate_provenance(self.provenance)

    def test_provenance_status_total_mismatch_fails(self) -> None:
        audit = copy.deepcopy(self.provenance)
        audit["rows_missing_reviewer_status"] -= 1
        with self.assertRaises(FeasibilityValidationError):
            validate_provenance(audit)

    def test_required_positive_defects(self) -> None:
        validate_positive_defects(self.defects)

    def test_candidate_mapping_mutation_fails(self) -> None:
        rows = copy.deepcopy(self.defects)
        rows[0]["candidate_mapping_modified"] = True
        with self.assertRaises(FeasibilityValidationError):
            validate_positive_defects(rows)

    def test_nonzero_hard_negative_slice(self) -> None:
        validate_hard_negative_feasibility(self.hard)
        self.assertGreater(self.hard["candidate_count"], 0)

    def test_supported_hard_negative_fails(self) -> None:
        audit = copy.deepcopy(self.hard)
        audit["candidates"][0]["current_support_class"] = "PARTIAL_SUPPORT"
        with self.assertRaises(FeasibilityValidationError):
            validate_hard_negative_feasibility(audit)


if __name__ == "__main__":
    unittest.main()
