from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from payresolve_ai.evaluation.gold_mapping import (  # noqa: E402
    canonical_rows_sha256,
    load_json,
    load_jsonl,
    membership_sha256,
    normalize_query,
    validate_gold_mapping,
)


class GoldEvidenceMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_json(REPO_ROOT / "configs/evaluation/gold_mapping_v1.json")
        cls.rows = load_jsonl(REPO_ROOT / cls.config["mapping_path"])
        cls.scenarios = load_jsonl(REPO_ROOT / cls.config["scenario_plan_path"])
        cls.documents = load_jsonl(REPO_ROOT / cls.config["kb_documents_path"])

    def report(self, rows=None, scenarios=None, documents=None, config=None):
        return validate_gold_mapping(
            deepcopy(self.rows if rows is None else rows),
            deepcopy(self.scenarios if scenarios is None else scenarios),
            deepcopy(self.documents if documents is None else documents),
            deepcopy(self.config if config is None else config),
        )

    @staticmethod
    def codes(report):
        return {item["code"] for item in report["errors"]}

    def test_valid_full_gold_mapping_passes(self):
        self.assertTrue(self.report()["valid"])

    def test_duplicate_query_id_fails(self):
        rows = deepcopy(self.rows)
        rows[1]["query_id"] = rows[0]["query_id"]
        self.assertIn("duplicate-query-id", self.codes(self.report(rows=rows)))

    def test_normalized_duplicate_query_text_fails(self):
        rows = deepcopy(self.rows)
        rows[1]["query_text"] = "  " + rows[0]["query_text"].upper() + "  "
        self.assertIn("normalized-duplicate-query", self.codes(self.report(rows=rows)))

    def test_unknown_gold_intent_fails(self):
        rows = deepcopy(self.rows)
        rows[0]["gold_intent"] = "unknown_intent"
        self.assertIn("unknown-gold-intent", self.codes(self.report(rows=rows)))

    def test_canonical_slug_mismatch_fails(self):
        rows = deepcopy(self.rows)
        rows[0]["intent_slug"] = "wrong_slug"
        self.assertIn("canonical-slug-mismatch", self.codes(self.report(rows=rows)))

    def test_invalid_split_count_fails(self):
        rows = deepcopy(self.rows)
        next(row for row in rows if row["split"] == "locked_test")["split"] = "development"
        self.assertIn("invalid-split-count", self.codes(self.report(rows=rows)))

    def test_answer_query_without_gold_evidence_fails(self):
        rows = deepcopy(self.rows)
        next(row for row in rows if row["expected_response_type"] == "ANSWER")["gold_evidence_ids"] = []
        self.assertIn("answer-without-gold", self.codes(self.report(rows=rows)))

    def test_safety_query_with_gold_evidence_fails(self):
        rows = deepcopy(self.rows)
        row = next(row for row in rows if row["expected_response_type"] == "ABSTAIN_ESCALATE")
        row["gold_evidence_ids"] = ["POL_TRANSFER_PENDING_002#eligibility"]
        self.assertIn("safety-with-active-evidence", self.codes(self.report(rows=rows)))

    def test_gold_evidence_referencing_missing_section_fails(self):
        rows = deepcopy(self.rows)
        rows[0]["gold_evidence_ids"] = ["FAQ_CARD_DECLINED_001#missing"]
        self.assertIn("missing-evidence-section", self.codes(self.report(rows=rows)))

    def test_gold_evidence_referencing_draft_fails(self):
        rows = deepcopy(self.rows)
        row = next(row for row in rows if row["gold_intent"] == "pending_transfer" and row["expected_response_type"] == "ANSWER")
        row["gold_evidence_ids"] = ["POL_TRANSFER_PENDING_003#proposed_window"]
        self.assertIn("ineligible-active-evidence", self.codes(self.report(rows=rows)))

    def test_gold_evidence_referencing_expired_fails(self):
        rows = deepcopy(self.rows)
        row = next(row for row in rows if row["gold_intent"] == "pending_transfer" and row["expected_response_type"] == "ANSWER")
        row["gold_evidence_ids"] = ["POL_TRANSFER_PENDING_001#old_window"]
        self.assertIn("ineligible-active-evidence", self.codes(self.report(rows=rows)))

    def test_hard_negative_overlapping_gold_evidence_fails(self):
        rows = deepcopy(self.rows)
        row = next(row for row in rows if row["expected_response_type"] == "ANSWER")
        row["hard_negative_evidence_ids"] = list(row["gold_evidence_ids"])
        self.assertIn("hard-negative-overlap", self.codes(self.report(rows=rows)))

    def test_forbidden_evidence_overlapping_gold_evidence_fails(self):
        rows = deepcopy(self.rows)
        row = next(row for row in rows if row["expected_response_type"] == "ANSWER")
        row["forbidden_evidence_ids"] = list(row["gold_evidence_ids"])
        self.assertIn("forbidden-overlap", self.codes(self.report(rows=rows)))

    def test_wrong_intent_family_mapping_fails(self):
        rows = deepcopy(self.rows)
        rows[0]["intent_family"] = "transfer"
        self.assertIn("wrong-intent-family", self.codes(self.report(rows=rows)))

    def test_insufficient_per_intent_coverage_fails(self):
        rows = deepcopy(self.rows)
        row = next(row for row in rows if row["gold_intent"] == "declined_card_payment" and row["split"] == "development")
        row["gold_intent"] = "pending_card_payment"
        row["intent_slug"] = "pending_card_payment"
        self.assertIn("insufficient-per-intent-coverage", self.codes(self.report(rows=rows)))

    def test_missing_eligible_document_coverage_fails(self):
        rows = deepcopy(self.rows)
        for row in rows:
            for field in ("gold_evidence_ids", "acceptable_evidence_ids", "hard_negative_evidence_ids"):
                row[field] = [value for value in row[field] if not value.startswith("ESC_CASH_DECLINED_001#")]
        self.assertIn("missing-eligible-document-coverage", self.codes(self.report(rows=rows)))

    def test_missing_ineligible_forbidden_coverage_fails(self):
        rows = deepcopy(self.rows)
        row = next(row for row in rows if "POL_CARD_REVERT_003#proposed_credit" in row["forbidden_evidence_ids"])
        row["forbidden_evidence_ids"] = []
        self.assertIn("missing-ineligible-forbidden-coverage", self.codes(self.report(rows=rows)))

    def test_invalid_multi_document_mapping_fails(self):
        rows = deepcopy(self.rows)
        row = next(row for row in rows if row["evidence_requirement"] == "multi_document")
        row["gold_evidence_ids"] = row["gold_evidence_ids"][:1]
        self.assertIn("invalid-multi-document", self.codes(self.report(rows=rows)))

    def test_non_empty_rationale_is_required(self):
        rows = deepcopy(self.rows)
        rows[0]["mapping_rationale"] = " "
        self.assertIn("empty-mapping-rationale", self.codes(self.report(rows=rows)))

    def test_dataset_hash_is_deterministic(self):
        self.assertEqual(canonical_rows_sha256(self.rows), canonical_rows_sha256(list(reversed(self.rows))))

    def test_scenario_plan_hash_is_deterministic(self):
        self.assertEqual(canonical_rows_sha256(self.scenarios), canonical_rows_sha256(list(reversed(self.scenarios))))

    def test_reverted_card_payment_round_trips_correctly(self):
        row = next(row for row in self.rows if row["gold_intent"] == "reverted_card_payment?")
        encoded = json.dumps(row)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["gold_intent"], "reverted_card_payment?")
        self.assertEqual(decoded["intent_slug"], "reverted_card_payment")

    def test_scenario_query_drift_fails(self):
        rows = deepcopy(self.rows)
        rows[0]["query_text"] += " changed"
        self.assertIn("scenario-query-drift", self.codes(self.report(rows=rows)))

    def test_scenario_hash_mismatch_fails(self):
        config = deepcopy(self.config)
        config["frozen_scenario_plan_sha256"] = "0" * 64
        self.assertIn("scenario-plan-hash-mismatch", self.codes(self.report(config=config)))

    def test_mapping_hash_changes_for_mapping_change(self):
        rows = deepcopy(self.rows)
        rows[0]["review_notes"] += " audit"
        self.assertNotEqual(canonical_rows_sha256(self.rows), canonical_rows_sha256(rows))

    def test_membership_hash_ignores_mapping_fields(self):
        rows = deepcopy(self.rows)
        rows[0]["mapping_rationale"] += " audit"
        self.assertEqual(membership_sha256(self.rows, "development"), membership_sha256(rows, "development"))

    def test_normalizer_ignores_case_and_punctuation(self):
        self.assertEqual(normalize_query("Card, DECLINED!"), normalize_query("card declined"))

    def test_invalid_review_status_fails(self):
        rows = deepcopy(self.rows)
        rows[0]["review_status"] = "PENDING"
        self.assertIn("invalid-review-status", self.codes(self.report(rows=rows)))

    def test_kb_canonical_hash_mismatch_fails(self):
        documents = deepcopy(self.documents)
        documents[0]["title"] += " changed"
        self.assertIn("kb-canonical-hash-mismatch", self.codes(self.report(documents=documents)))

    def test_hard_negative_must_support_confusing_intent(self):
        rows = deepcopy(self.rows)
        row = next(row for row in rows if row["expected_response_type"] == "ANSWER")
        row["hard_negative_evidence_ids"] = ["POL_CASH_DECLINED_001#eligibility"]
        self.assertIn("hard-negative-intent-mismatch", self.codes(self.report(rows=rows)))

    def test_hard_negative_cannot_support_gold_intent(self):
        rows = deepcopy(self.rows)
        row = next(row for row in rows if row["expected_response_type"] == "ANSWER")
        row["hard_negative_evidence_ids"] = ["FAQ_CARD_DECLINED_001#policy_gap"]
        self.assertIn("hard-negative-supports-gold-intent", self.codes(self.report(rows=rows)))

    def test_missing_confusing_intent_fails(self):
        scenarios = deepcopy(self.scenarios)
        scenario = next(row for row in scenarios if row["expected_response_type"] == "ANSWER")
        scenario["confusing_intent"] = None
        self.assertIn("missing-confusing-intent", self.codes(self.report(scenarios=scenarios)))

    def test_numeric_mapping_rationale_fails(self):
        rows = deepcopy(self.rows)
        rows[0]["mapping_rationale"] = 12345
        self.assertIn("invalid-mapping-rationale", self.codes(self.report(rows=rows)))

    def test_numeric_review_notes_fails(self):
        rows = deepcopy(self.rows)
        rows[0]["review_notes"] = 12345
        self.assertIn("invalid-review-notes", self.codes(self.report(rows=rows)))

    def test_non_string_evidence_id_fails(self):
        rows = deepcopy(self.rows)
        rows[0]["hard_negative_evidence_ids"] = [12345]
        self.assertIn("non-string-evidence-id", self.codes(self.report(rows=rows)))

    def test_invalid_query_id_fails(self):
        rows = deepcopy(self.rows)
        rows[0]["query_id"] = "bad id"
        self.assertIn("invalid-query-id", self.codes(self.report(rows=rows)))

    def test_empty_query_text_fails(self):
        rows = deepcopy(self.rows)
        rows[0]["query_text"] = " "
        self.assertIn("invalid-query-text", self.codes(self.report(rows=rows)))

    def test_duplicate_scenario_id_fails(self):
        scenarios = deepcopy(self.scenarios)
        scenarios[1]["query_id"] = scenarios[0]["query_id"]
        self.assertIn("duplicate-scenario-id", self.codes(self.report(scenarios=scenarios)))

    def test_missing_scenario_required_field_fails(self):
        scenarios = deepcopy(self.scenarios)
        scenarios[0].pop("customer_situation")
        self.assertIn("missing-scenario-required-field", self.codes(self.report(scenarios=scenarios)))

    def test_invalid_scenario_field_type_fails(self):
        scenarios = deepcopy(self.scenarios)
        scenarios[0]["customer_situation"] = 12345
        self.assertIn("invalid-scenario-field-type", self.codes(self.report(scenarios=scenarios)))

    def test_invalid_scenario_count_fails(self):
        scenarios = deepcopy(self.scenarios[:-1])
        self.assertIn("invalid-scenario-count", self.codes(self.report(scenarios=scenarios)))

    def test_scenario_confusing_intent_contract_fails(self):
        scenarios = deepcopy(self.scenarios)
        scenario = next(row for row in scenarios if row["expected_response_type"] == "ANSWER")
        scenario["confusing_intent"] = "unknown_intent"
        self.assertIn("scenario-confusing-intent-contract", self.codes(self.report(scenarios=scenarios)))

    def test_invalid_target_forbidden_document_fails(self):
        scenarios = deepcopy(self.scenarios)
        scenario = next(row for row in scenarios if row["expected_response_type"] == "ABSTAIN_ESCALATE")
        scenario["target_forbidden_document_id"] = "MISSING_DOC_999"
        self.assertIn("invalid-target-forbidden-document", self.codes(self.report(scenarios=scenarios)))


if __name__ == "__main__":
    unittest.main()
