from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from payresolve_ai.evaluation.critical_v2_contract import (
    ABSTAIN_IDS,
    CASE_DENOMINATORS,
    SAFE_CORRECTIVE_IDS,
    ContractValidationError,
    validate_contract,
    validate_contract_package,
    validate_metric_spec,
    validate_revision_5_checklist,
)


ROOT = Path(__file__).resolve().parents[1]


class CriticalV2ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads((ROOT / "configs/evaluation/critical_eval_v2_contract_option_a.json").read_text(encoding="utf-8"))
        cls.metrics = json.loads((ROOT / "reports/week_03/results/critical_eval_v2_contract_metric_spec.json").read_text(encoding="utf-8"))
        cls.checklist = json.loads((ROOT / "reports/week_03/results/critical_eval_v2_revision_5_acceptance_checklist.json").read_text(encoding="utf-8"))

    def test_complete_contract_package(self) -> None:
        result = validate_contract_package(ROOT)
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["candidate_revision_5_created"])
        self.assertFalse(result["evaluation_authorized"])

    def test_exact_taxonomy_and_distribution(self) -> None:
        validate_contract(self.contract)
        self.assertEqual(set(self.contract["safe_corrective_ids"]), SAFE_CORRECTIVE_IDS)
        self.assertEqual(set(self.contract["abstain_escalate_ids"]), ABSTAIN_IDS)

    def test_third_top_level_response_fails(self) -> None:
        value = copy.deepcopy(self.contract)
        value["response_taxonomy"]["response_types"].append("SAFE_CORRECTIVE")
        with self.assertRaises(ContractValidationError):
            validate_contract(value)

    def test_distribution_drift_fails(self) -> None:
        value = copy.deepcopy(self.contract)
        value["distribution"]["ANSWER/SAFE_CORRECTIVE"] = 14
        with self.assertRaises(ContractValidationError):
            validate_contract(value)

    def test_candidate_authorization_fails(self) -> None:
        value = copy.deepcopy(self.contract)
        value["lifecycle"]["evaluation_authorized"] = True
        with self.assertRaises(ContractValidationError):
            validate_contract(value)

    def test_control_plane_literal_requirement_fails(self) -> None:
        value = copy.deepcopy(self.contract)
        value["claim_planes"]["control_plane"]["requires_literal_kb_nonexistence_statement"] = True
        with self.assertRaises(ContractValidationError):
            validate_contract(value)

    def test_metric_denominators(self) -> None:
        validate_metric_spec(self.metrics)
        self.assertEqual(self.metrics["case_metrics"], CASE_DENOMINATORS)

    def test_metric_denominator_drift_fails(self) -> None:
        value = copy.deepcopy(self.metrics)
        value["case_metrics"]["wrong_abstain_rate_on_answerable_cases"] = 40
        with self.assertRaises(ContractValidationError):
            validate_metric_spec(value)

    def test_revision_5_checklist(self) -> None:
        validate_revision_5_checklist(self.checklist)
        self.assertFalse(self.checklist["candidate_revision_5_created"])

    def test_missing_pass_b_field_fails(self) -> None:
        value = copy.deepcopy(self.checklist)
        value["pass_b"]["required_fields"].remove("review_input_sha256")
        with self.assertRaises(ContractValidationError):
            validate_revision_5_checklist(value)

    def test_hard_negative_substitution_fails(self) -> None:
        value = copy.deepcopy(self.checklist)
        value["hard_negative_proposals"][0][0] = "SUBSTITUTED"
        with self.assertRaises(ContractValidationError):
            validate_revision_5_checklist(value)


if __name__ == "__main__":
    unittest.main()
