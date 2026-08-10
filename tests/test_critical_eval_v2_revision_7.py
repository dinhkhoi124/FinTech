"""Focused regression contract for W3-002-CR1 candidate revision 7."""

from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_json(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def read_jsonl(relative: str):
    return [json.loads(line) for line in (ROOT / relative).read_text(encoding="utf-8").splitlines() if line.strip()]


class CriticalEvalV2Revision7Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.delta = read_json("reports/week_03/results/critical_eval_v2_revision_7_semantic_delta.json")
        cls.corrections = read_json("reports/week_03/results/critical_eval_v2_revision_7_corrections.json")
        cls.cover_proof = read_json("reports/week_03/results/critical_eval_v2_revision_7_complete_cover_derivation.json")
        cls.model_inputs = read_json("reports/week_03/results/critical_eval_v2_revision_7_model_input_comparison.json")
        cls.manifest = read_json("reports/week_03/results/critical_eval_v2_candidate_manifest.json")
        cls.pass_a = read_jsonl("data/evaluation/critical_eval_v2_pass_a.jsonl")
        cls.pass_b = read_jsonl("data/evaluation/critical_eval_v2_support_judgments.jsonl")
        cls.mappings = {row["query_id"]: row for row in read_jsonl("data/evaluation/critical_eval_v2_mapping.jsonl")}
        cls.pass_b_by_key = {(row["query_id"], row["evidence_id"]): row for row in cls.pass_b}

    def test_exactly_four_pass_b_semantic_assignments_changed(self):
        expected = {
            ("Q_V2_A_TRD01", "POL_TRANSFER_DECLINED_001#eligibility"),
            ("Q_V2_A_TRD01", "RUN_TRANSFER_DECLINED_001#checks"),
            ("Q_V2_A_TRR02", "ESC_TRANSFER_RECIPIENT_001#trigger"),
            ("Q_V2_A_CSU03", "ESC_CASH_UNRECOG_001#safe_handoff"),
        }
        actual = {(row["query_id"], row["evidence_id"]) for row in self.delta["semantic_changes"]}
        self.assertEqual(expected, actual)
        self.assertEqual(4, self.delta["changed_semantic_pass_b_rows"])

    def test_no_fifth_semantic_pass_b_change(self):
        self.assertEqual(0, self.delta["unexpected_semantic_pass_b_rows"])
        self.assertTrue(self.delta["all_other_semantic_pass_b_rows_unchanged"])

    def test_trd01_policy_retains_state_loses_boundary(self):
        row = self.pass_b_by_key[("Q_V2_A_TRD01", "POL_TRANSFER_DECLINED_001#eligibility")]
        self.assertEqual(["STATE"], row["supported_requested_obligation_ids"])

    def test_trd01_run_retains_state_loses_boundary(self):
        row = self.pass_b_by_key[("Q_V2_A_TRD01", "RUN_TRANSFER_DECLINED_001#checks")]
        self.assertEqual(["STATE"], row["supported_requested_obligation_ids"])

    def test_trr02_escalation_retains_window_loses_trace(self):
        row = self.pass_b_by_key[("Q_V2_A_TRR02", "ESC_TRANSFER_RECIPIENT_001#trigger")]
        self.assertEqual(["WINDOW"], row["supported_requested_obligation_ids"])

    def test_csu03_escalation_retains_minimal_loses_prohibit(self):
        row = self.pass_b_by_key[("Q_V2_A_CSU03", "ESC_CASH_UNRECOG_001#safe_handoff")]
        self.assertEqual(["MINIMAL"], row["supported_requested_obligation_ids"])

    def test_trd01_faq_remains_only_complete_cover(self):
        self.assertEqual(
            [["FAQ_TRANSFER_DECLINED_001#answer"]],
            self.mappings["Q_V2_A_TRD01"]["complete_requested_answer_covers"],
        )

    def test_trr02_faq_and_policy_remain_complete_covers(self):
        self.assertEqual(
            [
                ["FAQ_TRANSFER_RECIPIENT_002#current_window"],
                ["POL_TRANSFER_RECIPIENT_001#trace_window"],
            ],
            self.mappings["Q_V2_A_TRR02"]["complete_requested_answer_covers"],
        )

    def test_csu03_requires_two_section_minimal_covers(self):
        mapping = self.mappings["Q_V2_A_CSU03"]
        expected = {
            frozenset(("POL_CASH_UNRECOG_001#prohibited_actions", "ESC_CASH_UNRECOG_001#safe_handoff")),
            frozenset(("POL_CASH_UNRECOG_001#prohibited_actions", "RUN_CASH_UNRECOG_002#safe_handoff")),
        }
        self.assertEqual(expected, {frozenset(cover) for cover in mapping["complete_requested_answer_covers"]})
        self.assertEqual(2, mapping["minimum_evidence_section_cover_size"])

    def test_model_input_freeze_is_60_of_60(self):
        self.assertEqual(60, self.model_inputs["query_count"])
        self.assertEqual(0, self.model_inputs["changed_count"])
        self.assertTrue(self.model_inputs["all_identical"])
        self.assertTrue(all(row["identical"] for row in self.model_inputs["rows"]))

    def test_distribution_remains_40_15_5(self):
        distribution = Counter((row["intended_response_type"], row.get("intended_answer_subtype")) for row in self.pass_a)
        self.assertEqual(40, distribution[("ANSWER", "STANDARD")])
        self.assertEqual(15, distribution[("ANSWER", "SAFE_CORRECTIVE")])
        self.assertEqual(5, distribution[("ABSTAIN_ESCALATE", None)])

    def test_hard_negative_set_unchanged(self):
        self.assertTrue(self.corrections["hard_negative_set_unchanged"])
        self.assertEqual(5, self.corrections["hard_negative_count"])
        self.assertEqual(5, len(self.corrections["hard_negative_pairs"]))

    def test_forbidden_evidence_semantics_unchanged(self):
        self.assertTrue(self.corrections["forbidden_evidence_semantics_unchanged"])
        self.assertEqual(64, len(self.corrections["forbidden_evidence_semantic_projection_sha256"]))

    def test_complete_cover_count_is_deterministic_92(self):
        self.assertEqual(92, self.cover_proof["total_complete_covers"])
        self.assertTrue(all(self.cover_proof["invalid_revision_6_covers_absent"].values()))
        self.assertTrue(all(self.cover_proof["replacement_covers_present"].values()))

    def test_no_revision_7_inference_or_evaluation_output_exists(self):
        self.assertFalse(self.manifest["model_loaded"])
        self.assertFalse(self.manifest["retrieval_executed"])
        self.assertFalse(self.manifest["generation_executed"])
        self.assertFalse(self.manifest["critical_pipeline_executed"])

    def test_candidate_is_not_senior_approved_or_evaluation_authorized(self):
        self.assertFalse(self.manifest["senior_semantic_review_approved"])
        self.assertFalse(self.manifest["evaluation_authorized"])
        self.assertFalse(self.manifest["critical_evaluated"])
        self.assertEqual("NOT_ESTABLISHED", self.manifest["model_verdict"])

    def test_support_class_distribution_is_unchanged(self):
        self.assertEqual(
            {"DIRECT_SUPPORT": 179, "PARTIAL_SUPPORT": 6, "CONTEXTUAL_BUT_INSUFFICIENT": 1452, "IRRELEVANT": 1483},
            dict(Counter(row["support_class"] for row in self.pass_b)),
        )

    def test_candidate_revision_and_predecessor_binding(self):
        self.assertEqual(7, self.manifest["candidate_revision"])
        self.assertEqual("d27de987d0eb7a942c88590eec9a30bdd6ee33d8", self.manifest["predecessor_candidate_commit"])
        self.assertEqual("2f42fb4ff7159ef2735ce88418b0dbfcc414b0091476f1882a83d13e807002ad", self.manifest["predecessor_manifest_sha256"])


if __name__ == "__main__":
    unittest.main()
