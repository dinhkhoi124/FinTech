"""Focused routing, generation, and assembly tests for W3-003 RM1."""

from __future__ import annotations

import json
import unittest
from datetime import date
from pathlib import Path

from payresolve_ai.generation.citations import verify_draft
from payresolve_ai.generation.pipeline_v3 import (
    _fixture_chunks,
    load_v3_configuration,
    run_nonlocked_regression,
    run_case_v3,
    run_synthetic_behavior_suite,
)
from payresolve_ai.generation.types import EvidenceChunk, GenerationDraft


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/generation/grounded_pipeline_v3.json"


class GroundedPipelineV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config, cls.lexicon, cls.rows = load_v3_configuration(ROOT, CONFIG_PATH)
        cls.result = run_synthetic_behavior_suite(ROOT, CONFIG_PATH)

    def _row(self, query_id: str) -> dict:
        return next(row for row in self.rows if row["query_id"] == query_id)

    def _run(self, query_id: str, *, mode: str = "TARGET_AWARE") -> dict:
        row = self._row(query_id)
        chunks, rankings = _fixture_chunks(row)
        raw_idf = {token: 1.0 for token in "pending check transfer withdrawal merchant declined cash atm".split()}
        canonical_idf = dict(raw_idf)
        return run_case_v3(row, rankings, chunks, raw_idf, canonical_idf, self.config, self.lexicon, mode=mode)

    def test_synthetic_suite_routes_every_case_as_preregistered(self):
        self.assertEqual("PASS", self.result["status"])
        self.assertEqual([], self.result["mismatches"])
        self.assertEqual(14, self.result["cases"])

    def test_unknown_dimension_uses_direct_support_fallback(self):
        output = self._run("RM1_DEV_UNKNOWN_DIRECT")
        self.assertEqual("STANDARD", output["answer_strategy"])
        self.assertEqual("DIRECT_CANONICAL_SUPPORT", output["response_plan"]["reason_codes"][0])

    def test_genuine_competing_targets_fail_closed(self):
        output = self._run("RM1_DEV_AMBIGUOUS")
        self.assertEqual("ABSTAIN", output["answer_strategy"])
        self.assertEqual("AMBIGUOUS_COMPETING_TARGETS", output["response_plan"]["reason_codes"][0])

    def test_close_scores_for_same_target_are_not_semantic_ambiguity(self):
        row = json.loads(json.dumps(self._row("RM1_DEV_AMBIGUOUS")))
        row["candidate_evidence"][1]["intent_scope"] = list(row["candidate_evidence"][0]["intent_scope"])
        chunks, rankings = _fixture_chunks(row)
        idf = {token: 1.0 for token in "why declined merchant atm authorized".split()}
        output = run_case_v3(row, rankings, chunks, idf, idf, self.config, self.lexicon)
        self.assertEqual("STANDARD", output["answer_strategy"])

    def test_permissive_diagnostic_mode_cannot_reopen_blocked_target(self):
        for query_id in ("RM1_DEV_PRIVATE_CORRECTIVE", "RM1_DEV_INCOMPLETE_PRIVATE"):
            output = self._run(query_id, mode="PERMISSIVE_DIAGNOSTIC")
            self.assertNotEqual("STANDARD", output["answer_strategy"])
            self.assertEqual("BLOCKED_CONTROL_PLANE", output["response_plan"]["requested_target_status"])

    def test_complete_and_incomplete_corrective_plans_separate(self):
        self.assertEqual("CORRECTIVE", self._run("RM1_DEV_PRIVATE_CORRECTIVE")["answer_strategy"])
        self.assertEqual("ABSTAIN", self._run("RM1_DEV_INCOMPLETE_PRIVATE")["answer_strategy"])
        self.assertEqual("ABSTAIN", self._run("RM1_DEV_PARTIAL_EXACT")["answer_strategy"])

    def test_irrelevant_extractable_evidence_does_not_answer(self):
        output = self._run("RM1_DEV_OUT_OF_DOMAIN")
        self.assertEqual("ABSTAIN_ESCALATE", output["response_type"])
        self.assertEqual([], output["claims"])

    def test_ineligible_attractive_evidence_is_filtered_before_planning(self):
        output = self._run("RM1_DEV_INELIGIBLE_ATTRACTIVE")
        self.assertEqual("CORRECTIVE", output["answer_strategy"])
        selected = output["selected_evidence"]
        self.assertTrue(selected)
        self.assertTrue(all(item["status"] == "APPROVED" for item in selected))
        self.assertTrue(all(date.fromisoformat(item["effective_date"]) <= date(2026, 8, 16) for item in selected))
        self.assertFalse(any("PLACEHOLDER" in output["answer_text"] for _ in (0,)))

    def test_every_answered_factual_claim_passes_existing_verifier(self):
        for output in self.result["outputs"]:
            if output["response_type"] != "ANSWER":
                continue
            selected = [EvidenceChunk(**{**item, "intent_scope": tuple(item["intent_scope"])}) for item in output["selected_evidence"]]
            rendered = verify_draft(GenerationDraft(output["claims"], output["citations"]), selected, date(2026, 8, 16))
            self.assertTrue(rendered)

    def test_low_overlap_corrective_generation_is_plan_conditioned(self):
        row = self._row("RM1_DEV_LOW_OVERLAP")
        chunks, ordinary_rankings = _fixture_chunks(row)
        self.assertNotIn("DEV_CARD_DECLINED#action", {item["chunk_id"] for item in ordinary_rankings})
        output = self._run("RM1_DEV_LOW_OVERLAP")
        self.assertEqual("CORRECTIVE", output["answer_strategy"])
        self.assertIn("DEV_CARD_DECLINED#action", {item["evidence_id"] for item in output["selected_evidence"]})
        self.assertEqual(("declined_card_payment",), output["response_plan"]["corrective_scope_anchor"])
        self.assertEqual(
            [row["support_quote"] for row in output["response_plan"]["factual_objectives"]],
            [row["text"] for row in output["claims"]],
        )
        self.assertNotIn("authorization code", " ".join(row["text"].casefold() for row in output["claims"]))

        incomplete_chunks = [item for item in chunks if item["chunk_id"] != "DEV_CARD_DECLINED#action"]
        idf = {token: 1.0 for token in "terminal merchant refusal confirm declined".split()}
        incomplete = run_case_v3(row, ordinary_rankings, incomplete_chunks, idf, idf, self.config, self.lexicon)
        self.assertEqual("ABSTAIN", incomplete["answer_strategy"])
        self.assertIn("MISSING_NEXT_ACTION", incomplete["response_plan"]["reason_codes"])

    def test_out_of_domain_rich_corrective_corpus_has_no_scope_authority(self):
        row = self._row("RM1_DEV_OUT_OF_DOMAIN")
        self.assertGreaterEqual(len(row["candidate_evidence"]), 4)
        output = self._run("RM1_DEV_OUT_OF_DOMAIN")
        self.assertEqual("ABSTAIN", output["answer_strategy"])
        self.assertEqual((), output["response_plan"]["corrective_scope_anchor"])
        self.assertIn("NO_SAFE_CORRECTIVE_SCOPE_ANCHOR", output["response_plan"]["reason_codes"])

    def test_corrective_plan_can_exceed_standard_evidence_budget(self):
        output = self._run("RM1_DEV_WIDE_CORRECTIVE")
        self.assertEqual("CORRECTIVE", output["answer_strategy"])
        self.assertGreater(len(output["claims"]), self.config["standard"]["max_evidence"])
        self.assertLessEqual(len(output["claims"]), self.config["corrective"]["max_factual_claims"])

    def test_configuration_has_no_global_answer_bypass(self):
        payload = CONFIG_PATH.read_text(encoding="utf-8")
        self.assertNotIn("ALWAYS_ANSWER", payload)
        self.assertEqual("TARGET_AWARE", self.config["default_mode"])

    def test_fixture_is_development_only(self):
        dev = json.loads((ROOT / self.config["development_config"]).read_text(encoding="utf-8"))
        self.assertEqual("DEVELOPMENT_REGRESSION_ONLY", dev["classification"])
        self.assertFalse(dev["independent_evaluation"])

    def test_nonlocked_v2_to_v3_regression_contract_passes(self):
        result = run_nonlocked_regression(ROOT, CONFIG_PATH)
        self.assertEqual("PASS", result["status"])
        for membership in result["memberships"].values():
            self.assertTrue(all(membership["comparisons"].values()))
        self.assertFalse(result["product_approval_claimed"])
        self.assertEqual(0, sum(row["generic_rule_missing"] for row in result["standard_false_negatives"]))
        self.assertEqual(6, sum(row["disposition"] == "RESOLVED_BY_GENERIC_RULE" for row in result["standard_gap_dispositions"]))
        dispositions = {row.get("disposition") for row in result["standard_gap_dispositions"]}
        self.assertLessEqual(dispositions, {"RESOLVED_BY_GENERIC_RULE", "DESIRED_FAIL_CLOSED_WITH_PRODUCT_RULE"})


if __name__ == "__main__":
    unittest.main()
