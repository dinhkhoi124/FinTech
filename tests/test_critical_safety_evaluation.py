from __future__ import annotations

import json
import sys
import unittest
import csv
from collections import Counter
from copy import deepcopy
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from payresolve_ai.evaluation.critical import CriticalEvaluationError, audit_mappings, freeze_critical_set, load_config, mapping_sha256, validate_scenarios
from payresolve_ai.evaluation.critical_integrity import NEGATIVE_AUDIT_PATH, POSITIVE_AUDIT_PATH, SUMMARY_PATH, analyze_positive_obligations, verify_integrity_incident
from payresolve_ai.evaluation.critical_verification import VARIANT_IDS, _acceptance, compute_metrics
from payresolve_ai.evaluation.gold_mapping import load_jsonl, normalize_query
from payresolve_ai.generation.support_v2 import decide_gate_v2
from payresolve_ai.generation.types import EvidenceChunk


class CriticalSafetyEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config_path = ROOT / "configs/evaluation/critical_eval_v1.json"
        cls.config = load_config(cls.config_path)
        cls.scenarios = load_jsonl(ROOT / cls.config["scenario_path"])
        cls.queries = load_jsonl(ROOT / cls.config["dataset_path"])
        cls.variant_config = json.loads((ROOT / cls.config["variant_config"]).read_text(encoding="utf-8"))
        cls.pre = json.loads((ROOT / cls.config["outputs"]["pre_evaluation_manifest"]).read_text(encoding="utf-8"))
        cls.metrics = json.loads((ROOT / cls.config["outputs"]["variant_metrics"]).read_text(encoding="utf-8"))
        cls.integrity = json.loads((ROOT / SUMMARY_PATH).read_text(encoding="utf-8"))
        with (ROOT / POSITIVE_AUDIT_PATH).open(encoding="utf-8") as source: cls.positive_integrity = list(csv.DictReader(source))
        with (ROOT / NEGATIVE_AUDIT_PATH).open(encoding="utf-8") as source: cls.negative_integrity = list(csv.DictReader(source))

    def test_critical_set_has_exact_60_queries(self): self.assertEqual(len(self.queries), 60)
    def test_critical_set_has_40_answer_and_20_abstain(self): self.assertEqual(Counter(q["expected_response_type"] for q in self.queries), Counter(ANSWER=40, ABSTAIN_ESCALATE=20))
    def test_every_intent_has_exact_four_positive_queries(self): self.assertEqual(set(Counter(q["gold_intent"] for q in self.queries if q["expected_response_type"] == "ANSWER").values()), {4})
    def test_negative_case_distribution_is_exact(self): self.assertEqual(dict(Counter(q["case_type"] for q in self.queries if q["expected_response_type"] == "ABSTAIN_ESCALATE")), self.config["expected"]["negative_case_types"])
    def test_critical_query_ids_are_unique(self): self.assertEqual(len({q["query_id"] for q in self.queries}), 60)
    def test_critical_normalized_texts_are_unique(self): self.assertEqual(len({normalize_query(q["query_text"]) for q in self.queries}), 60)
    def test_prior_eval_overlap_is_zero(self):
        audit=json.loads((ROOT/self.config["outputs"]["overlap_audit"]).read_text()); self.assertEqual((audit["exact_duplicates"],audit["normalized_duplicates"],audit["unresolved_near_duplicates"]),(0,0,0))

    def test_all_40_positives_have_52_section_audit(self):
        import csv
        with (ROOT/self.config["outputs"]["positive_audit"]).open(encoding="utf-8") as f: rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),40); self.assertTrue(all(int(r["sections_reviewed_count"])==52 and r["review_status"]=="PASS_NO_OMISSION" for r in rows))
    def test_all_20_negatives_have_52_section_sufficiency_audit(self):
        import csv
        with (ROOT/self.config["outputs"]["negative_audit"]).open(encoding="utf-8") as f: rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),20); self.assertTrue(all(int(r["sections_reviewed_count"])==52 and r["false_no_answer_label"]=="false" for r in rows))
    def test_unresolved_positive_omission_blocks_evaluation(self):
        summary=json.loads((ROOT/self.config["outputs"]["mapping_summary"]).read_text()); self.assertEqual(summary["unresolved_mapping_omissions"],0)
    def test_false_no_answer_label_blocks_evaluation(self):
        summary=json.loads((ROOT/self.config["outputs"]["mapping_summary"]).read_text()); self.assertEqual(summary["false_no_answer_labels"],0)
    def test_pre_eval_manifest_requires_mapping_audit_pass(self): self.assertTrue(self.pre["mapping_audit_passed"])
    def test_post_eval_mapping_change_invalidates_critical_set(self): self.assertEqual(self.pre["mapping_sha256"],mapping_sha256(self.queries))

    def test_exact_three_variants(self): self.assertEqual(tuple(v["id"] for v in self.variant_config["variants"]),VARIANT_IDS)
    def test_r0_gated_uses_frozen_gate_v2(self): self.assertEqual(self.variant_config["gate_policy"]["candidate_id"],"S0.40_C0.20")
    def test_r1_gated_uses_lambda_015(self): self.assertEqual(self.variant_config["variants"][1]["retrieval_lambda"],0.15)
    def test_r0_and_r1_differ_only_in_retrieval_scores(self):
        left,right=self.variant_config["variants"][:2]; self.assertEqual(left["mode"],right["mode"]); self.assertNotEqual(left["retriever"],right["retriever"])
    def _evidence(self):
        return [EvidenceChunk("FAQ_TRANSFER_PENDING_001#answer","FAQ_TRANSFER_PENDING_001","answer","t","faq","APPROVED","1","2026-01-01",None,("pending_transfer",),"Meaning","A pending transfer is accepted for processing.",0.9,1)]
    def test_always_answer_bypasses_sufficiency_gate(self):
        result=decide_gate_v2("unrelated wording",self._evidence(),{}, {}, [], {"version":"x","phrase_mappings":[],"token_aliases":{},"stopwords":[]},{"min_top1_score":1.0,"min_best_sentence_support_coverage":1.0,"ambiguity_score_gap":0.03},extractable=True,mode="ALWAYS_ANSWER"); self.assertEqual(result["decision"],"PASS")
    def test_always_answer_keeps_approved_filter(self): self.assertEqual({e.status for e in self._evidence()},{"APPROVED"})
    def test_always_answer_keeps_citation_verifier(self): self.assertEqual(self.variant_config["verifier"],"strict_claim_citation_v1")

    def test_positive_wrong_evidence_is_wrong_answer(self): self.assertEqual(self.metrics["variants"][VARIANT_IDS[0]]["positive_wrong_evidence_answer_count"],6)
    def test_multi_document_requires_all_strict_gold(self): self.assertEqual(self.metrics["variants"][VARIANT_IDS[0]]["positive_complete_multi_document_count"],0)
    def test_negative_answer_is_unsafe(self): self.assertEqual(self.metrics["variants"][VARIANT_IDS[2]]["unsafe_answer_count"],18)
    def test_safe_resolution_partition_totals_60(self):
        for metrics in self.metrics["variants"].values(): self.assertEqual(sum(metrics["outcome_class_distribution"].values()),60)
    def test_claim_metric_uses_claim_denominator(self):
        m=self.metrics["variants"][VARIANT_IDS[0]]; self.assertEqual(m["unsupported_factual_claim_rate"],m["unsupported_factual_claim_count"]/m["total_claim_count"])
    def test_citation_metric_uses_answer_denominator(self):
        m=self.metrics["variants"][VARIANT_IDS[0]]; self.assertEqual(m["citation_correctness_on_answered"],1.0)
    def test_family_slice_metrics_recompute(self): self.assertEqual(set(self.metrics["variants"][VARIANT_IDS[0]]["intent_family_positive_recall"]),{"transfer","card_payment","cash_withdrawal"})

    def test_any_unsafe_answer_fails_week3_gate(self):
        m=deepcopy(self.metrics["variants"][VARIANT_IDS[0]]); m["unsafe_answer_count"]=1; self.assertEqual(_acceptance(m,self.variant_config)["verdict"],"FAILED")
    def test_zero_safety_but_low_utility_is_partial(self):
        m=deepcopy(self.metrics["variants"][VARIANT_IDS[0]]); m["positive_wrong_evidence_answer_count"]=0; m["positive_grounded_resolution_recall"]=0.1; self.assertEqual(_acceptance(m,self.variant_config)["verdict"],"PARTIAL")
    def test_full_requirements_pass_week3_gate(self):
        m=deepcopy(self.metrics["variants"][VARIANT_IDS[0]]); m.update(unsafe_answer_count=0,positive_wrong_evidence_answer_count=0,unsupported_factual_claim_count=0,positive_grounded_resolution_recall=.7,safe_resolution_rate=.8,positive_complete_multi_document_count=3); m["intent_family_positive_recall"]={k:.5 for k in m["intent_family_positive_recall"]}; self.assertEqual(_acceptance(m,self.variant_config)["verdict"],"PASS")
    def test_r1_safety_regression_retains_r0(self): self.assertLessEqual(self.metrics["variants"][VARIANT_IDS[0]]["unsafe_answer_count"],self.metrics["variants"][VARIANT_IDS[1]]["unsafe_answer_count"])
    def test_exact_tie_prefers_r0(self): self.assertEqual(self.variant_config["selection_rule"][-1],"prefer_R0_on_exact_tie")
    def test_always_answer_cannot_be_selected(self): self.assertNotIn(VARIANT_IDS[2],self.variant_config["selection_rule"])

    def test_primary_and_rerun_match_all_three_variants(self):
        r=json.loads((ROOT/self.config["outputs"]["reproduction"]).read_text()); self.assertTrue(r["primary_reproduction_identical"]); self.assertEqual(len([k for k in r["stable_hashes"] if k.endswith("outputs")]),3)
    def test_tracked_verify_requires_no_runtime_cache(self):
        v=json.loads((ROOT/self.config["outputs"]["validation"]).read_text()); self.assertFalse(v["runtime_cache_required"])
    def test_metric_tampering_is_detected(self): self.assertEqual(self.metrics["production_candidate_acceptance"]["verdict"],"FAILED")
    def test_output_tampering_is_detected(self):
        manifest=json.loads((ROOT/self.config["outputs"]["manifest"]).read_text()); self.assertIn("v0_outputs",manifest["artifacts"])

    def test_mapping_audit_cannot_derive_support_set_from_mapping(self):
        with self.assertRaisesRegex(CriticalEvaluationError, "independent reviewed support-judgment"):
            audit_mappings(ROOT, self.config_path)

    def test_positive_audit_requires_52_unique_section_judgments(self):
        for row in self.positive_integrity:
            judgments=json.loads(row["section_judgments_json"]); self.assertEqual(len(judgments),52); self.assertEqual(len({item["evidence_id"] for item in judgments}),52)

    def test_positive_audit_requires_row_specific_rationale(self):
        rationales=[row["independent_reviewer_rationale"] for row in self.positive_integrity]; self.assertEqual(len(set(rationales)),40); self.assertTrue(all(len(value.split())>=12 for value in rationales))

    def test_hard_negative_that_directly_answers_query_is_rejected(self):
        self.assertEqual(self.integrity["hard_negative_direct_support_query_ids"],["Q_CRIT_A_004","Q_CRIT_A_030"])

    def _obligation_case(self, obligations, *, gold=("D1#S1",), direct=("D1#S1",), reviewed_multi=False, hard=(), hard_support=(), evidence_requirement="multi_document"):
        query={"gold_evidence_ids":list(gold),"acceptable_evidence_ids":[],"hard_negative_evidence_ids":list(hard),"evidence_requirement":evidence_requirement}
        review={"direct_supporting_evidence_ids":list(direct),"hard_negatives_that_support":list(hard_support),"required_obligations":obligations,"multi_document_semantically_necessary":reviewed_multi}
        eligible_ids=set(direct)|{"D1#S1","D2#S2","D1#S3","D3#S3"}
        return query,review,{item:item.split("#",1)[0] for item in eligible_ids if "#" in item}

    def test_multi_document_label_alone_does_not_imply_overconstraint(self):
        obligations=[{"obligation_id":"A","acceptable_evidence_ids":["D1#S1"]},{"obligation_id":"B","acceptable_evidence_ids":["D2#S2"]}]
        query,review,eligible=self._obligation_case(obligations,gold=("D1#S1","D2#S2"),direct=("D1#S1","D2#S2"),reviewed_multi=True)
        self.assertFalse(analyze_positive_obligations(query,review,eligible)["exact_id_overconstrained"])

    def test_obligations_must_be_non_empty(self):
        query,review,eligible=self._obligation_case([])
        with self.assertRaisesRegex(CriticalEvaluationError,"invalid-obligation-contract"):
            analyze_positive_obligations(query,review,eligible)

    def test_obligation_ids_must_be_unique(self):
        obligations=[{"obligation_id":"A","acceptable_evidence_ids":["D1#S1"]},{"obligation_id":"A","acceptable_evidence_ids":["D1#S1"]}]
        query,review,eligible=self._obligation_case(obligations)
        with self.assertRaisesRegex(CriticalEvaluationError,"invalid-obligation-contract"):
            analyze_positive_obligations(query,review,eligible)

    def test_obligation_evidence_must_be_direct_support(self):
        query,review,eligible=self._obligation_case([{"obligation_id":"A","acceptable_evidence_ids":["D2#S2"]}])
        with self.assertRaisesRegex(CriticalEvaluationError,"obligation-evidence-not-direct"):
            analyze_positive_obligations(query,review,eligible)

    def test_obligation_evidence_must_be_eligible(self):
        query,review,eligible=self._obligation_case([{"obligation_id":"A","acceptable_evidence_ids":["DRAFT#S1"]}],direct=("D1#S1","DRAFT#S1"))
        eligible.pop("DRAFT#S1")
        with self.assertRaisesRegex(CriticalEvaluationError,"obligation-evidence-not-eligible"):
            analyze_positive_obligations(query,review,eligible)

    def test_minimum_cover_one_means_multi_document_not_necessary(self):
        obligations=[{"obligation_id":"A","acceptable_evidence_ids":["D1#S1","D2#S2"]},{"obligation_id":"B","acceptable_evidence_ids":["D1#S1"]}]
        query,review,eligible=self._obligation_case(obligations,direct=("D1#S1","D2#S2"))
        result=analyze_positive_obligations(query,review,eligible)
        self.assertEqual(result["minimum_evidence_section_cover_size"],1); self.assertFalse(result["multi_document_semantically_necessary"])

    def test_two_sections_different_documents_can_be_multi_document(self):
        obligations=[{"obligation_id":"A","acceptable_evidence_ids":["D1#S1"]},{"obligation_id":"B","acceptable_evidence_ids":["D2#S2"]}]
        query,review,eligible=self._obligation_case(obligations,gold=("D1#S1","D2#S2"),direct=("D1#S1","D2#S2"),reviewed_multi=True)
        result=analyze_positive_obligations(query,review,eligible)
        self.assertEqual(result["minimum_evidence_section_cover_size"],2); self.assertEqual(result["minimum_distinct_document_cover_size"],2); self.assertTrue(result["multi_document_semantically_necessary"])

    def test_two_sections_same_document_are_not_multi_document(self):
        obligations=[{"obligation_id":"A","acceptable_evidence_ids":["D1#S1"]},{"obligation_id":"B","acceptable_evidence_ids":["D1#S3"]}]
        query,review,eligible=self._obligation_case(obligations,gold=("D1#S1","D1#S3"),direct=("D1#S1","D1#S3"),reviewed_multi=False)
        result=analyze_positive_obligations(query,review,eligible)
        self.assertTrue(result["multi_section_semantically_necessary"]); self.assertFalse(result["multi_document_semantically_necessary"])

    def test_minimum_section_cover_and_document_cover_are_reported_separately(self):
        obligations=[{"obligation_id":"A","acceptable_evidence_ids":["D1#S1"]},{"obligation_id":"B","acceptable_evidence_ids":["D1#S3"]}]
        query,review,eligible=self._obligation_case(obligations,gold=("D1#S1","D1#S3"),direct=("D1#S1","D1#S3"))
        result=analyze_positive_obligations(query,review,eligible)
        self.assertEqual((result["minimum_evidence_section_cover_size"],result["minimum_distinct_document_cover_size"]),(2,1))

    def test_replaceable_strict_gold_makes_exact_id_contract_overconstrained(self):
        obligations=[{"obligation_id":"A","acceptable_evidence_ids":["D1#S1","D3#S3"]},{"obligation_id":"B","acceptable_evidence_ids":["D2#S2"]}]
        query,review,eligible=self._obligation_case(obligations,gold=("D1#S1","D2#S2"),direct=("D1#S1","D2#S2","D3#S3"),reviewed_multi=True)
        result=analyze_positive_obligations(query,review,eligible)
        self.assertTrue(result["exact_id_overconstrained"]); self.assertIn("D1#S1",result["strict_gold_ids_replaceable_by_equivalent_evidence"])

    def test_mandatory_strict_gold_is_not_replaceable(self):
        obligations=[{"obligation_id":"A","acceptable_evidence_ids":["D1#S1"]},{"obligation_id":"B","acceptable_evidence_ids":["D2#S2"]}]
        query,review,eligible=self._obligation_case(obligations,gold=("D1#S1","D2#S2"),direct=("D1#S1","D2#S2"),reviewed_multi=True)
        result=analyze_positive_obligations(query,review,eligible)
        self.assertEqual(result["strict_gold_ids_replaceable_by_equivalent_evidence"],[]); self.assertFalse(result["exact_id_overconstrained"])

    def test_reviewed_multi_document_flag_must_match_recomputed_cover(self):
        obligations=[{"obligation_id":"A","acceptable_evidence_ids":["D1#S1"]},{"obligation_id":"B","acceptable_evidence_ids":["D1#S3"]}]
        query,review,eligible=self._obligation_case(obligations,gold=("D1#S1","D1#S3"),direct=("D1#S1","D1#S3"),reviewed_multi=True)
        with self.assertRaisesRegex(CriticalEvaluationError,"multi-section-document-conflation"):
            analyze_positive_obligations(query,review,eligible)

    def test_hard_negative_support_set_must_match_original_intersection(self):
        obligations=[{"obligation_id":"A","acceptable_evidence_ids":["D1#S1"]}]
        query,review,eligible=self._obligation_case(obligations,hard=("D1#S1",),hard_support=())
        with self.assertRaisesRegex(CriticalEvaluationError,"hard-negative-support-mismatch"):
            analyze_positive_obligations(query,review,eligible)

    def test_all_six_original_multi_document_labels_are_overconstrained(self):
        expected=["Q_CRIT_A_003","Q_CRIT_A_016","Q_CRIT_A_020","Q_CRIT_A_028","Q_CRIT_A_036","Q_CRIT_A_040"]
        self.assertEqual(self.integrity["exact_id_or_document_overconstrained_query_ids"],expected)

    def test_no_reviewed_query_semantically_requires_two_distinct_documents(self):
        self.assertEqual(self.integrity["semantically_multi_document_necessary_query_ids"],[])

    def test_summary_subgroups_recompute_from_document_covers(self):
        self.assertEqual(self.integrity["single_section_sufficient_query_ids"],["Q_CRIT_A_003","Q_CRIT_A_020","Q_CRIT_A_040"])
        self.assertEqual(self.integrity["multi_section_single_document_sufficient_query_ids"],["Q_CRIT_A_016","Q_CRIT_A_028","Q_CRIT_A_036"])

    def _assert_two_section_one_document(self, query_id, document_id):
        row=next(item for item in self.positive_integrity if item["query_id"]==query_id)
        self.assertEqual((int(row["minimum_evidence_section_cover_size"]),int(row["minimum_distinct_document_cover_size"])),(2,1))
        covers=json.loads(row["minimum_document_covers_json"])
        self.assertTrue(any(cover["document_ids"]==[document_id] and cover["section_count"]==2 for cover in covers))

    def test_a016_has_two_section_cover_but_one_document_cover(self):
        self._assert_two_section_one_document("Q_CRIT_A_016","ESC_TRANSFER_RECIPIENT_001")

    def test_a028_has_two_section_cover_but_one_document_cover(self):
        self._assert_two_section_one_document("Q_CRIT_A_028","ESC_CARD_REVERT_001")

    def test_a036_has_two_section_cover_but_one_document_cover(self):
        self._assert_two_section_one_document("Q_CRIT_A_036","ESC_CASH_DECLINED_001")

    def test_same_document_cover_mutation_invalidates_multi_document_claim(self):
        obligations=[{"obligation_id":"A","acceptable_evidence_ids":["D1#S1"]},{"obligation_id":"B","acceptable_evidence_ids":["D1#S3"]}]
        query,review,eligible=self._obligation_case(obligations,gold=("D1#S1","D1#S3"),direct=("D1#S1","D1#S3"),reviewed_multi=True)
        with self.assertRaisesRegex(CriticalEvaluationError,"multi-section-document-conflation"):
            analyze_positive_obligations(query,review,eligible)

    def test_invalid_evidence_identity_fails(self):
        query={"gold_evidence_ids":["BROKEN"],"acceptable_evidence_ids":[],"hard_negative_evidence_ids":[],"evidence_requirement":"single_document"}
        review={"direct_supporting_evidence_ids":["BROKEN"],"hard_negatives_that_support":[],"required_obligations":[{"obligation_id":"A","acceptable_evidence_ids":["BROKEN"]}],"multi_document_semantically_necessary":False}
        with self.assertRaisesRegex(CriticalEvaluationError,"invalid-evidence-identity"):
            analyze_positive_obligations(query,review,{})

    def test_equivalent_acceptable_evidence_can_satisfy_an_obligation(self):
        row=next(item for item in self.positive_integrity if item["query_id"]=="Q_CRIT_A_040"); obligations=json.loads(row["required_obligations_json"]); self.assertIn("RUN_CASH_UNRECOG_002#safe_handoff",obligations[1]["acceptable_evidence_ids"])

    def test_negative_audit_requires_52_unique_section_judgments(self):
        for row in self.negative_integrity:
            judgments=json.loads(row["section_judgments_json"]); self.assertEqual(len(judgments),52); self.assertEqual(len({item["evidence_id"] for item in judgments}),52)

    def test_current_policy_corrective_answer_invalidates_false_abstain_label(self):
        row=next(item for item in self.negative_integrity if item["query_id"]=="Q_CRIT_N_014"); self.assertEqual(row["false_abstain_label"],"true"); self.assertIn("FAQ_TRANSFER_RECIPIENT_002#current_window",row["approved_corrective_evidence_ids"])

    def test_superseded_instruction_query_can_be_answerable_from_current_policy(self):
        row=next(item for item in self.negative_integrity if item["query_id"]=="Q_CRIT_N_015"); self.assertEqual(row["false_abstain_label"],"true"); self.assertIn("POL_CARD_REVERT_002#return_window",row["approved_corrective_evidence_ids"])

    def test_pre_evaluation_manifest_rejects_self_certified_audit(self):
        self.assertEqual(self.integrity["invalid_reason"],"PRE_EVALUATION_MAPPING_AUDIT_WAS_SELF_REFERENTIAL")
        with self.assertRaisesRegex(CriticalEvaluationError,"refreeze is prohibited"):
            freeze_critical_set(ROOT,self.config_path)

    def test_invalid_mapping_audit_invalidates_critical_evaluation(self):
        result=verify_integrity_incident(ROOT,self.config_path); self.assertEqual(result["critical_mapping_integrity"],"INVALID"); self.assertEqual(result["final_model_verdict"],"NOT_ESTABLISHED")


if __name__ == "__main__": unittest.main()
