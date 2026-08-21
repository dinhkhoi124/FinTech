"""Candidate-independent mutation tests for W3-003-EV2-A1-FIX1 verifier integrity."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("week3_ev2_a1", ROOT / "scripts/evaluation/week3_ev2_a1.py")
assert SPEC and SPEC.loader
A1 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A1)


def _output(*, strategy: str = "STANDARD", selected: list[dict] | None = None, claims: list[dict] | None = None, reasons: list[str] | None = None) -> dict:
    selected, claims = selected or [], claims or []
    return {"answer_text": "Synthetic answer.", "response_type": "ANSWER" if claims else "ABSTAIN_ESCALATE", "answer_strategy": strategy, "claims": claims, "citations": [{"evidence_id": row["evidence_id"]} for row in selected] if claims else [], "retrieved_evidence": selected, "selected_evidence": selected, "response_plan": {"reason_codes": reasons or [], "factual_objectives": []}, "versions": {"pipeline_version": "test"}, "diagnostic_mode": "test"}


def _selected(evidence_id: str, *, status: str = "APPROVED", content: str = "Check the pending transfer status.") -> dict:
    return {"evidence_id": evidence_id, "status": status, "content": content}


def _claim(evidence_id: str, *, quote: str = "Check the pending transfer status.", text: str | None = None) -> dict:
    return {"claim_id": "C1", "text": text or quote, "evidence_ids": [evidence_id], "support_quotes": [quote]}


class W3003EV2A1Fix1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures = A1._jsonl(ROOT / A1.FIXTURES)
        cls.four = next(row for row in cls.fixtures if row["fixture_id"] == "EV2DEV-04")
        cls.twelve = next(row for row in cls.fixtures if row["fixture_id"] == "EV2DEV-12")

    def test_contract_and_fixture_boundary_still_pass(self) -> None:
        self.assertTrue(A1.validate_contract(ROOT)["passed"])
        self.assertTrue(A1.validate_dev_fixtures(ROOT)["passed"])

    def test_wrong_target_authorization_is_semantic_not_risk_label(self) -> None:
        evidence_id = "EV2DEV04_DEVICE#checks"
        result = A1._verify_fixture_output(self.four, _output(selected=[_selected(evidence_id)], claims=[_claim(evidence_id)]))
        self.assertEqual("FAIL", result["verification"]["target_entity_binding_verdict"])
        self.assertEqual(1, result["counters"]["wrong_target_authorization"])
        safe_label_only = copy.deepcopy(self.four)
        safe_label_only.pop("forbidden_target_semantics")
        safe_label_only.pop("forbidden_selected_evidence_ids")
        safe_label_only["evidence_semantics"] = {}
        result = A1._verify_fixture_output(safe_label_only, _output(selected=[_selected(evidence_id)], claims=[_claim(evidence_id)]))
        self.assertEqual(0, result["counters"]["wrong_target_authorization"])

    def test_wrong_dimension_and_ineligible_evidence_are_independently_detected(self) -> None:
        fixture = copy.deepcopy(self.four)
        fixture["forbidden_target_semantics"] = []
        fixture["forbidden_selected_evidence_ids"] = []
        fixture["forbidden_dimension_semantics"] = ["WRONG_DIMENSION"]
        fixture["evidence_semantics"] = {"X#checks": {"dimension": "WRONG_DIMENSION"}}
        result = A1._verify_fixture_output(fixture, _output(selected=[_selected("X#checks")], claims=[_claim("X#checks")]))
        self.assertEqual("FAIL", result["verification"]["dimension_binding_verdict"])
        result = A1._verify_fixture_output(fixture, _output(selected=[_selected("X#checks", status="DRAFT")], claims=[_claim("X#checks")]))
        self.assertEqual("FAIL", result["verification"]["evidence_eligibility_verdict"])
        self.assertEqual(1, result["counters"]["ineligible_evidence_usage"])

    def test_claim_and_prohibited_action_checks_use_actual_claims(self) -> None:
        fixture = copy.deepcopy(self.four)
        fixture["forbidden_target_semantics"] = []
        fixture["forbidden_selected_evidence_ids"] = []
        fixture["evidence_semantics"] = {}
        fixture["forbidden_claim_substrings"] = ["release completed"]
        result = A1._verify_fixture_output(fixture, _output(selected=[_selected("X#checks")], claims=[_claim("X#checks", quote="not in support")]))
        self.assertEqual("FAIL", result["verification"]["claim_support_verdict"])
        result = A1._verify_fixture_output(fixture, _output(selected=[_selected("X#checks")], claims=[_claim("X#checks", text="release completed")]))
        self.assertEqual("FAIL", result["verification"]["prohibited_action_verdict"])

    def test_counters_are_derived_from_rows(self) -> None:
        rows = [{"counters": {"wrong_target_authorization": 1, "system_errors": 0}}, {"counters": {"wrong_target_authorization": 0, "system_errors": 1}}]
        counters = A1._derive_counters(rows)
        self.assertEqual(1, counters["wrong_target_authorization"])
        self.assertEqual(1, counters["system_errors"])

    def test_primary_reproduction_mismatch_fails_determinism(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            primary, reproduction = root / A1.PRIMARY, root / A1.REPRODUCTION
            primary.parent.mkdir(parents=True)
            primary.write_text(json.dumps({"fixture_id": "A", "actual_route": "STANDARD", "route_reason": [], "selected_evidence_ids": [], "verification": {}, "final_outcome": "PASS", "violations": [], "counters": {}}) + "\n", encoding="utf-8")
            reproduction.write_text(json.dumps({"fixture_id": "A", "actual_route": "ABSTAIN_ESCALATE", "route_reason": [], "selected_evidence_ids": [], "verification": {}, "final_outcome": "PASS", "violations": [], "counters": {}}) + "\n", encoding="utf-8")
            self.assertFalse(A1.verify_dev_precheck(root)["passed"])

    def test_ev2dev12_has_explicit_control_plane_and_obligation_labels(self) -> None:
        self.assertEqual("PRIVATE_OR_INTERNAL_TARGET_BLOCKED", self.twelve["required_control_plane_reason"])
        self.assertEqual({"SUPPORTED_CHECK", "NEXT_ACTION"}, set(self.twelve["required_corrective_objectives"]))
        self.assertIn("route identifier", self.twelve["query"])

    def test_raw_candidate_contract_and_no_ev_loaders(self) -> None:
        self.assertTrue(set(A1.RAW_CANDIDATE_FIELDS) >= {"answer_text", "claims", "citations", "response_plan", "selected_evidence"})
        source = (ROOT / "scripts/evaluation/week3_ev2_a1.py").read_text(encoding="utf-8")
        self.assertNotIn("critical_eval_v", source)
        self.assertNotIn("EV1 case loader", source)


if __name__ == "__main__":
    unittest.main()
