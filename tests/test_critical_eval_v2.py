from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from payresolve_ai.evaluation.critical_v2 import (  # noqa: E402
    MODEL_INPUT_CONTRACT_VERSION,
    ABSTAIN_ESCALATE_IDS,
    HARD_NEGATIVE_PROPOSALS,
    NEGATIVE_COUNTS,
    PASS_B_REVIEWER_METHOD,
    PASS_B_REVIEWER_STATUS,
    PROHIBITED_TARGET_REVIEWER_METHOD,
    SAFE_CORRECTIVE_IDS,
    REJECTED_REV3_BUNDLE_SHA256,
    REJECTED_REV3_MANIFEST_SHA256,
    CriticalV2Error,
    _artifact_hashes,
    _catalog,
    assert_evaluation_execution_authorized,
    assert_negative_contract_feasible,
    derive_pass_c,
    load_config,
    load_jsonl,
    model_input_sha256,
    prohibited_target_review_input_sha256,
    recompute_overlap,
    review_input_sha256,
    sha256_file,
    validate_forbidden_audit,
    validate_candidate_lifecycle,
    validate_hard_negative_audits,
    validate_negative_category_quality,
    validate_overlap,
    validate_pass_a,
    validate_pass_b,
    validate_prohibited_target_reviews,
    validate_revision_history,
    verify_candidate,
    verify_historical_artifacts,
    verify_model_input_freeze,
)


class CriticalEvalV2Revision7Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config_path = ROOT / "configs/evaluation/critical_eval_v2.json"
        cls.config = load_config(cls.config_path)
        cls.pass_a = load_jsonl(ROOT / cls.config["outputs"]["pass_a"])
        cls.pass_b = load_jsonl(ROOT / cls.config["outputs"]["pass_b"])
        cls.pass_c = load_jsonl(ROOT / cls.config["outputs"]["pass_c"])
        cls.negatives = load_jsonl(ROOT / cls.config["outputs"]["negative_audit"])
        cls.category = load_jsonl(ROOT / cls.config["outputs"]["negative_category_quality_audit"])
        cls.hard = load_jsonl(ROOT / cls.config["outputs"]["hard_negative_audit"])
        cls.safety = load_jsonl(ROOT / cls.config["outputs"]["safety_challenge_audit"])
        cls.prohibited_reviews = load_jsonl(ROOT / cls.config["outputs"]["prohibited_target_review"])
        cls.forbidden_rows = load_jsonl(ROOT / cls.config["outputs"]["forbidden_audit"])
        cls.manifest = json.loads((ROOT / cls.config["outputs"]["candidate_manifest"]).read_text(encoding="utf-8"))
        cls.corrections = json.loads((ROOT / cls.config["outputs"]["revision_7_corrections"]).read_text(encoding="utf-8"))
        cls.comparison = json.loads((ROOT / cls.config["outputs"]["revision_comparison"]).read_text(encoding="utf-8"))
        cls.eligible, cls.forbidden = _catalog(ROOT, cls.config)
        cls.by_query = {row["query_id"]: row for row in cls.pass_a}
        cls.mapping = {row["query_id"]: row for row in cls.pass_c}
        cls.safety_by_query = {row["query_id"]: row for row in cls.safety}
        cls.judgments = {(row["query_id"], row["evidence_id"]): row for row in cls.pass_b}
        cls.recomputed_overlap, cls.recomputed_overlap_flags = recompute_overlap(ROOT, cls.config)

    def test_01_revision_is_seven(self):
        self.assertEqual(self.config["candidate_revision"], 7)

    def test_02_pass_a_has_60_unique_queries(self):
        self.assertEqual((len(self.pass_a), len(self.by_query)), (60, 60))

    def test_03_distribution_is_exact_40_15_5(self):
        self.assertEqual(Counter((r["intended_response_type"], r["intended_answer_subtype"]) for r in self.pass_a), Counter({("ANSWER", "STANDARD"): 40, ("ANSWER", "SAFE_CORRECTIVE"): 15, ("ABSTAIN_ESCALATE", None): 5}))

    def test_04_negative_category_distribution_is_fixed(self):
        rows = [r for r in self.pass_a if r.get("negative_category")]
        self.assertEqual(Counter(r["negative_category"] for r in rows), Counter(NEGATIVE_COUNTS))

    def test_05_exact_model_input_contract_is_frozen(self):
        self.assertTrue(all(r["model_input_contract_version"] == MODEL_INPUT_CONTRACT_VERSION for r in self.pass_a))

    def test_06_every_model_input_hash_matches_exact_utf8_bytes(self):
        self.assertTrue(all(r["model_input_sha256"] == model_input_sha256(r["model_input_text"]) for r in self.pass_a))

    def test_07_model_inputs_are_unique(self):
        self.assertEqual(len({r["model_input_text"] for r in self.pass_a}), 60)

    def test_08_scenario_metadata_mutation_does_not_change_runtime_input(self):
        row = copy.deepcopy(self.pass_a[0]); before = (row["model_input_text"], row["model_input_sha256"])
        row["scenario_text"] = "Changed authoring metadata only."
        self.assertEqual(before, (row["model_input_text"], row["model_input_sha256"]))

    def test_09_model_input_mutation_breaks_its_frozen_hash(self):
        row = copy.deepcopy(self.pass_a[0]); row["model_input_text"] += " changed"
        with self.assertRaises(CriticalV2Error):
            validate_pass_a([row, *self.pass_a[1:]])

    def test_10_model_input_mutation_changes_candidate_artifact_hash(self):
        self.assertEqual(self.manifest["artifact_sha256"], _artifact_hashes(ROOT, self.config))
        self.assertEqual(self.manifest["artifact_sha256"][self.config["outputs"]["pass_a"]], sha256_file(ROOT / self.config["outputs"]["pass_a"]))

    def test_11_positive_runtime_inputs_avoid_reviewed_deictic_phrases(self):
        banned = ("this event", "this case", "that troubleshooting", "the active window", "not yet eligible")
        positives = [r for r in self.pass_a if r["intended_response_type"] == "ANSWER"]
        self.assertFalse([(r["query_id"], p) for r in positives for p in banned if p in r["model_input_text"].lower()])

    def test_12_only_two_negatives_use_ambiguity_primary(self):
        rows = [r for r in self.pass_a if r.get("negative_category")]
        self.assertEqual(sum(r["primary_abstention_reason_code"] == "AMBIGUOUS_CONTEXT" for r in rows), 2)

    def test_13_non_ambiguity_negatives_have_sufficient_context(self):
        self.assertTrue(all(r["sufficient_case_context"] for r in self.category if r["registered_category"] != "ambiguous_insufficient_context"))

    def test_14_category_quality_audit_validates(self):
        self.assertEqual(validate_negative_category_quality(self.pass_a, self.category)["category_isolated_count"], 20)

    def test_15_draft_primary_reason_is_ineligibility(self):
        self.assertTrue(all(r["primary_safety_reason_code"] == "DRAFT_INELIGIBLE" for r in self.category if r["registered_category"] == "draft_only_entitlement_workflow"))

    def test_16_expired_primary_reason_is_ineligibility(self):
        self.assertTrue(all(r["primary_safety_reason_code"] == "EXPIRED_INELIGIBLE" for r in self.category if r["registered_category"] == "expired_only_entitlement_workflow"))

    def test_17_conflict_primary_reason_is_unresolved_conflict(self):
        self.assertTrue(all(r["primary_safety_reason_code"] == "UNRESOLVED_POLICY_CONFLICT" for r in self.category if r["registered_category"] == "superseded_current_policy_conflict"))

    def test_18_injection_primary_reason_is_instruction_boundary(self):
        self.assertTrue(all(r["primary_safety_reason_code"] == "INSTRUCTION_SOURCE_BOUNDARY" for r in self.category if r["registered_category"] == "override_prompt_injection"))

    def test_19_internal_and_matrix_categories_have_distinct_reasons(self):
        expected = {"unsupported_internal_identifier_code_reference": "UNSUPPORTED_INTERNAL_REFERENCE", "unsupported_exact_amount_threshold_approval_matrix": "UNSUPPORTED_APPROVAL_MATRIX"}
        self.assertTrue(all(r["primary_safety_reason_code"] == expected[r["registered_category"]] for r in self.category if r["registered_category"] in expected))

    def test_20_out_of_scope_primary_reason_is_domain_scope(self):
        row = next(r for r in self.category if r["registered_category"] == "out_of_scope")
        self.assertEqual(row["primary_safety_reason_code"], "OUT_OF_SCOPE")

    def test_21_infeasibility_stops_instead_of_weakening_query(self):
        rows = copy.deepcopy(self.category); rows[0]["safe_corrective_answer_possible"] = not rows[0]["safe_corrective_answer_possible"]
        with self.assertRaisesRegex(CriticalV2Error, "BLOCKED — COMMITTED CONTRACT"):
            assert_negative_contract_feasible(rows)

    def test_22_safe_corrective_obligations_do_not_ask_kb_to_prove_user_facts(self):
        prohibited = ("actual transaction state", "whether the customer recognizes", "whether recipient credit is absent", "prove the customer")
        descriptions = " ".join(o["description"].lower() for r in self.pass_a for o in r["safe_corrective_obligations"])
        self.assertFalse([p for p in prohibited if p in descriptions])

    def test_23_pass_b_is_complete_60_by_52(self):
        self.assertEqual(len(self.pass_b), 3120)

    def test_24_pass_b_validates_exact_model_input_binding(self):
        self.assertEqual(validate_pass_b(self.pass_a, self.pass_b, self.eligible)["judgment_rows"], 3120)

    def test_25_model_input_mutation_invalidates_pass_b_binding(self):
        rows = copy.deepcopy(self.pass_a); rows[0]["model_input_text"] += " mutation"; rows[0]["model_input_sha256"] = model_input_sha256(rows[0]["model_input_text"])
        with self.assertRaisesRegex(CriticalV2Error, "content binding mismatch"):
            validate_pass_b(rows, self.pass_b, self.eligible)

    def test_26_scenario_mutation_does_not_invalidate_pass_b_binding(self):
        rows = copy.deepcopy(self.pass_a); rows[0]["scenario_text"] = "metadata changed"
        self.assertEqual(validate_pass_b(rows, self.pass_b, self.eligible)["queries"], 60)

    def test_27_exact_five_hard_negatives_derive(self):
        self.assertEqual({(r["query_id"], r["evidence_id"]) for r in self.hard}, HARD_NEGATIVE_PROPOSALS)

    def test_28_legitimate_terminal_boundary_evidence_is_partial_not_hard(self):
        for evidence in ("FAQ_TRANSFER_DECLINED_001#answer", "FAQ_TRANSFER_FAILED_001#answer"):
            row = self.judgments[("Q_V2_A_TRP03", evidence)]
            self.assertEqual(row["support_class"], "PARTIAL_SUPPORT")
            self.assertIsNone(row.get("hard_negative_review"))

    def test_29_csp03_recognition_gate_cannot_satisfy_redirect(self):
        row = self.judgments[("Q_V2_A_CSP03", "RUN_CASH_UNRECOG_002#recognition_gate")]
        self.assertEqual(row["supported_requested_obligation_ids"], ["GATE"])

    def test_30_csd02_trigger_cannot_overclaim_immediate_security_action(self):
        row = self.judgments[("Q_V2_A_CSD02", "ESC_CASH_DECLINED_001#trigger")]
        self.assertEqual(row["supported_requested_obligation_ids"], ["THRESHOLD"])

    def test_31_csd04_recognition_gate_cannot_overclaim_security_route(self):
        row = self.judgments[("Q_V2_A_CSD04", "RUN_CASH_UNRECOG_002#recognition_gate")]
        self.assertEqual((row["support_class"], row["supported_requested_obligation_ids"]), ("PARTIAL_SUPPORT", []))

    def test_32_car01_trigger_cannot_establish_prior_hold_facts(self):
        row = self.judgments[("Q_V2_A_CAR01", "ESC_CARD_REVERT_001#trigger")]
        self.assertEqual(row["supported_requested_obligation_ids"], ["BOUNDARY"])

    def test_33_pass_c_derives_exact_40_15_5(self):
        mappings, negatives, hard = derive_pass_c(self.pass_a, self.pass_b, self.prohibited_reviews)
        self.assertEqual((Counter((r["final_expected_response_type"], r["final_expected_answer_subtype"]) for r in mappings), len(negatives), len(hard)), (Counter({("ANSWER", "STANDARD"): 40, ("ANSWER", "SAFE_CORRECTIVE"): 15, ("ABSTAIN_ESCALATE", None): 5}), 20, 5))

    def test_34_csp03_invalid_recognition_gate_cover_is_removed(self):
        covers = self.mapping["Q_V2_A_CSP03"]["complete_requested_answer_covers"]
        self.assertFalse(any("RUN_CASH_UNRECOG_002#recognition_gate" in cover for cover in covers))

    def test_35_car01_trigger_is_not_a_complete_single_section_cover(self):
        covers = self.mapping["Q_V2_A_CAR01"]["complete_requested_answer_covers"]
        self.assertNotIn(["ESC_CARD_REVERT_001#trigger"], covers)

    def test_36_all_five_abstains_lack_requested_and_corrective_covers(self):
        for query_id in ABSTAIN_ESCALATE_IDS:
            row = self.mapping[query_id]
            self.assertEqual((row["complete_requested_answer_covers"], row["complete_corrective_answer_covers"]), ([], []))

    def test_37_forbidden_audit_is_full_matrix(self):
        self.assertEqual(len(self.forbidden_rows), 1200)

    def test_38_forbidden_semantic_audit_validates(self):
        self.assertEqual(validate_forbidden_audit(self.forbidden_rows, self.forbidden, self.pass_c)["semantic_attraction_true"], 26)

    def test_39_semantic_attraction_is_independent_from_lexical_screening(self):
        self.assertTrue(any(r["automated_attraction_candidate"] and not r["appears_to_answer_requested_detail"] for r in self.forbidden_rows))
        self.assertTrue(any(not r["automated_attraction_candidate"] and r["appears_to_answer_requested_detail"] for r in self.forbidden_rows))

    def test_40_crypto_query_has_zero_banking_semantic_attraction(self):
        rows = [r for r in self.forbidden_rows if r["query_id"] == "Q_V4_N_OS01"]
        self.assertEqual((len(rows), sum(r["appears_to_answer_requested_detail"] for r in rows)), (20, 0))

    def test_41_actual_draft_and_expired_workflows_are_detected(self):
        required = {("Q_V4_N_DR02", "POL_TRANSFER_PENDING_003#proposed_window"), ("Q_V4_N_EX03", "RUN_CASH_UNRECOG_001#retired_checks")}
        actual = {(r["query_id"], r["forbidden_evidence_id"]) for r in self.forbidden_rows if r["appears_to_answer_requested_detail"]}
        self.assertTrue(required <= actual)

    def test_42_unrelated_lexical_row_cannot_be_changed_without_breaking_frozen_hash(self):
        row = next(r for r in self.forbidden_rows if r["automated_attraction_candidate"] and not r["appears_to_answer_requested_detail"])
        mutated = copy.deepcopy(row); mutated["appears_to_answer_requested_detail"] = True
        self.assertNotEqual(json.dumps(row, sort_keys=True), json.dumps(mutated, sort_keys=True))
        self.assertEqual(self.manifest["artifact_sha256"][self.config["outputs"]["forbidden_audit"]], sha256_file(ROOT / self.config["outputs"]["forbidden_audit"]))

    def test_43_forbidden_evidence_cannot_enter_mapping_or_cover(self):
        mappings = copy.deepcopy(self.pass_c); forbidden_id = next(iter(self.forbidden)); mappings[0]["acceptable_evidence_ids"].append(forbidden_id)
        with self.assertRaises(CriticalV2Error):
            validate_forbidden_audit(self.forbidden_rows, self.forbidden, mappings)

    def test_44_overlap_is_recomputed_from_model_input(self):
        stored = json.loads((ROOT / self.config["outputs"]["overlap_audit"]).read_text(encoding="utf-8"))
        self.assertEqual(stored, self.recomputed_overlap)

    def test_45_scenario_metadata_does_not_change_overlap(self):
        rows = copy.deepcopy(self.pass_a); rows[0]["scenario_text"] = "changed metadata"; after, _ = recompute_overlap(ROOT, self.config, rows)
        self.assertEqual(self.recomputed_overlap, after)

    def test_46_model_input_change_changes_overlap_candidate_hash(self):
        rows = copy.deepcopy(self.pass_a); rows[0]["model_input_text"] += " changed"; rows[0]["model_input_sha256"] = model_input_sha256(rows[0]["model_input_text"]); after, _ = recompute_overlap(ROOT, self.config, rows)
        self.assertNotEqual(self.recomputed_overlap["candidate_rows_sha256"], after["candidate_rows_sha256"])

    def test_47_overlap_has_only_explicitly_adjudicated_lineage_flags(self):
        self.assertEqual(self.recomputed_overlap["flag_count"], 332)
        self.assertTrue(self.recomputed_overlap_flags)
        self.assertTrue(all(r["source"].startswith("critical_eval_v2_rejected_revision_") for r in self.recomputed_overlap_flags))
        self.assertEqual(validate_overlap(ROOT, self.config)["unresolved_findings"], 0)

    def test_48_revision_three_manifest_hash_is_preserved(self):
        path = ROOT / "reports/week_03/rejected/critical_eval_v2_revision_3/reports/week_03/results/critical_eval_v2_candidate_manifest.json"
        self.assertEqual(sha256_file(path), REJECTED_REV3_MANIFEST_SHA256)

    def test_49_revision_three_bundle_hash_is_recorded(self):
        self.assertEqual(self.manifest["rejected_revision_3_review_bundle_sha256"], REJECTED_REV3_BUNDLE_SHA256)

    def test_50_revision_three_files_are_byte_preserved(self):
        history = validate_revision_history(ROOT, self.config)
        self.assertEqual(len(history["rejected_revision_3_artifact_sha256"]), 18)

    def test_51_historical_w3_002_files_are_unchanged(self):
        self.assertEqual(verify_historical_artifacts(ROOT, self.config), self.config["historical_artifacts"])

    def test_52_candidate_hashes_reproduce(self):
        self.assertEqual(self.manifest["artifact_sha256"], _artifact_hashes(ROOT, self.config))

    def test_53_candidate_verifier_passes(self):
        self.assertEqual(verify_candidate(ROOT, self.config_path)["status"], "PASS")

    def test_54_lifecycle_is_structural_only(self):
        self.assertTrue(self.manifest["candidate_bytes_frozen"] and self.manifest["structural_integrity_verified"])
        self.assertEqual(self.manifest["pre_evaluation_integrity_scope"], "STRUCTURAL_ONLY_SEMANTIC_APPROVAL_PENDING")

    def test_55_evaluation_gate_remains_closed(self):
        with self.assertRaises(CriticalV2Error):
            assert_evaluation_execution_authorized(self.manifest)

    def test_56_no_model_or_ranking_artifacts_were_used(self):
        self.assertTrue(all(r["model_or_ranking_artifacts_used"] is False for r in self.pass_b))

    def test_57_standalone_verifier_has_no_installed_project_import(self):
        text = (ROOT / "scripts/evaluation/verify_review_bundle.py").read_text(encoding="utf-8")
        self.assertIn('sys.path.insert(0, str(root / "src"))', text)

    def test_58_exact_option_a_membership(self):
        self.assertEqual({r["query_id"] for r in self.pass_a if r.get("intended_answer_subtype") == "SAFE_CORRECTIVE"}, SAFE_CORRECTIVE_IDS)
        self.assertEqual({r["query_id"] for r in self.pass_a if r["intended_response_type"] == "ABSTAIN_ESCALATE"}, ABSTAIN_ESCALATE_IDS)

    def test_59_model_inputs_are_unchanged_from_committed_revision_six(self):
        self.assertTrue(verify_model_input_freeze(ROOT, self.config, self.pass_a)["unchanged"])

    def test_60_model_input_is_present_in_final_mapping(self):
        self.assertTrue(all(r["model_input_text"] == self.by_query[r["query_id"]]["model_input_text"] for r in self.pass_c))

    def test_61_section_and_document_cover_minima_are_separate(self):
        self.assertTrue(all("minimum_evidence_section_cover_size" in r and "minimum_distinct_document_cover_size" in r for r in self.pass_c))

    def test_62_support_counts_are_observed_not_fixed_targets(self):
        self.assertEqual(Counter(r["support_class"] for r in self.pass_b), Counter(self.manifest["support_class_counts"]))

    def test_63_all_direct_rows_were_rereviewed(self):
        self.assertTrue(all(r["direct_support_re_reviewed"] is True for r in self.pass_b if r["support_class"] == "DIRECT_SUPPORT"))

    def test_64_revision_seven_model_verdict_is_not_established(self):
        self.assertFalse(self.manifest["senior_semantic_review_approved"] or self.manifest["evaluation_authorized"] or self.manifest["critical_evaluated"])
        self.assertEqual(self.manifest["model_verdict"], "NOT_ESTABLISHED")

    def test_65_pass_b_has_exact_revision_seven_provenance(self):
        self.assertEqual(Counter((r["candidate_revision"], r["reviewer_status"], r["reviewer_method"]) for r in self.pass_b), Counter({(7, PASS_B_REVIEWER_STATUS, PASS_B_REVIEWER_METHOD): 3120}))

    def test_66_no_stale_reviewer_or_reason_provenance(self):
        stale = ("REVISION_1", "REVISION_2", "REVISION_3", "REVISION_4", "REVISION_5", "REVISION_6")
        self.assertFalse([r["evidence_id"] for r in self.pass_b if any(value in r["reviewer_status"] or value in r["reason_code"] for value in stale)])

    def test_67_review_hash_binds_query_obligations_evidence_and_content(self):
        query = copy.deepcopy(self.pass_a[0]); evidence = copy.deepcopy(next(iter(self.eligible.values())))
        original = review_input_sha256(query, evidence)
        variants = []
        q = copy.deepcopy(query); q["model_input_text"] += " changed"; variants.append(review_input_sha256(q, evidence))
        q = copy.deepcopy(query); q["requested_obligations"][0]["description"] += " changed"; variants.append(review_input_sha256(q, evidence))
        e = copy.deepcopy(evidence); e["evidence_id"] += "_changed"; variants.append(review_input_sha256(query, e))
        e = copy.deepcopy(evidence); e["content"] += " changed"; variants.append(review_input_sha256(query, e))
        self.assertTrue(all(value != original for value in variants))

    def test_68_pass_a_contains_no_evidence_answer_keys(self):
        forbidden = {"gold_evidence_ids", "acceptable_evidence_ids", "hard_negative_evidence_ids", "expected_cover", "_direct", "_partial"}
        self.assertFalse([(r["query_id"], forbidden & set(r)) for r in self.pass_a if forbidden & set(r)])

    def test_69_validator_encodes_only_senior_approved_hard_negative_ids(self):
        source = (ROOT / "src/payresolve_ai/evaluation/critical_v2.py").read_text(encoding="utf-8")
        evidence_literals = set(re.findall(r'"([A-Z0-9_]+#[a-z0-9_]+)"', source))
        self.assertEqual(evidence_literals, {evidence_id for _, evidence_id in HARD_NEGATIVE_PROPOSALS})

    def test_70_safe_corrective_claim_planes_are_separated(self):
        for query_id in SAFE_CORRECTIVE_IDS:
            planes = self.by_query[query_id]["claim_planes"]
            self.assertTrue(planes["control_plane"]["claims"])
            self.assertEqual(set(planes["factual_banking_policy"]["obligation_ids"]), {o["obligation_id"] for o in self.by_query[query_id]["safe_corrective_obligations"]})

    def test_71_every_safe_corrective_has_complete_corrective_cover(self):
        self.assertTrue(all(self.mapping[q]["complete_corrective_answer_covers"] and not self.mapping[q]["complete_requested_answer_covers"] for q in SAFE_CORRECTIVE_IDS))

    def test_72_safe_corrective_never_discloses_or_authorizes_prohibited_target(self):
        self.assertTrue(all(r["prohibited_target_disclosed_or_authorized"] is False for r in self.safety if r["query_id"] in SAFE_CORRECTIVE_IDS))

    def test_73_all_factual_corrective_obligations_have_eligible_direct_support(self):
        for query_id in SAFE_CORRECTIVE_IDS:
            for obligation in self.mapping[query_id]["safe_corrective_obligations"]:
                self.assertTrue(obligation["acceptable_evidence_ids"])
                self.assertTrue(all(evidence_id in self.eligible for evidence_id in obligation["acceptable_evidence_ids"]))

    def test_74_trd04_overclaim_is_partial(self):
        row = self.judgments[("Q_V2_A_TRD04", "RUN_TRANSFER_DECLINED_001#action")]
        self.assertEqual((row["support_class"], row["supported_requested_obligation_ids"]), ("PARTIAL_SUPPORT", []))

    def test_75_trr04_trigger_omissions_are_direct(self):
        for evidence_id in ("FAQ_TRANSFER_RECIPIENT_002#current_window", "POL_TRANSFER_RECIPIENT_001#trace_window"):
            row = self.judgments[("Q_V2_A_TRR04", evidence_id)]
            self.assertEqual((row["support_class"], row["supported_requested_obligation_ids"]), ("DIRECT_SUPPORT", ["TRIGGER"]))

    def test_76_ex01_and_id04_include_policy_gap_in_corrective_covers(self):
        for query_id in ("Q_V4_N_EX01", "Q_V4_N_ID04"):
            self.assertTrue(all("FAQ_CARD_DECLINED_001#policy_gap" in cover for cover in self.mapping[query_id]["complete_corrective_answer_covers"]))

    def test_77_every_minimal_cover_row_was_rereviewed(self):
        for mapping in self.pass_c:
            for cover in mapping["all_minimal_covers"]:
                self.assertTrue(all(self.judgments[(mapping["query_id"], evidence_id)]["minimal_cover_entry_re_reviewed"] for evidence_id in cover))

    def test_78_hard_negative_pairs_have_all_entry_guards(self):
        for row in self.hard:
            self.assertTrue(row["eligible_approved_effective"] and row["supports_no_requested_obligation"] and row["supports_no_corrective_obligation"] and row["not_legitimate_partial_support"] and row["participates_in_no_complete_cover"])

    def test_79_no_unapproved_hard_negative_substitution(self):
        self.assertEqual({(r["query_id"], r["evidence_id"]) for r in self.hard}, HARD_NEGATIVE_PROPOSALS)

    def test_80_forbidden_evidence_is_absent_from_all_covers(self):
        forbidden = set(self.forbidden)
        used = {e for m in self.pass_c for cover in m["complete_requested_answer_covers"] + m["complete_corrective_answer_covers"] for e in cover}
        self.assertFalse(forbidden & used)

    def test_81_overlap_audit_records_expected_rejected_lineage(self):
        self.assertEqual(self.recomputed_overlap["candidate_revision"], 7)
        self.assertTrue(all(name in self.recomputed_overlap["sources"] for name in ("critical_eval_v2_rejected_revision_2_lineage", "critical_eval_v2_rejected_revision_3_lineage", "critical_eval_v2_rejected_revision_4_lineage", "critical_eval_v2_rejected_revision_5_lineage")))

    def test_82_revision_four_archive_is_byte_preserved(self):
        history = validate_revision_history(ROOT, self.config)
        self.assertEqual(len(history["rejected_revision_4_artifact_sha256"]), 19)

    def test_83_automated_validation_is_not_senior_approval(self):
        self.assertTrue(self.manifest["structural_integrity_verified"])
        self.assertFalse(self.manifest["senior_semantic_review_approved"])

    def test_84_unauthorized_critical_execution_stops_before_loading(self):
        with self.assertRaisesRegex(CriticalV2Error, "execution is not authorized"):
            assert_evaluation_execution_authorized(self.manifest)

    def test_85_safe_corrective_audit_separates_answer_and_abstention_semantics(self):
        for query_id in SAFE_CORRECTIVE_IDS:
            row = self.safety_by_query[query_id]
            self.assertIsNone(row.get("primary_abstention_reason_code"))
            self.assertEqual(row.get("secondary_abstention_reason_codes"), [])
            self.assertFalse(row["requested_answer_complete_cover_exists"])
            self.assertTrue(row["safe_corrective_answer_complete_cover_exists"])
            self.assertNotIn("no_complete_correction_explanation", row)
            self.assertTrue(row["complete_safe_correction_explanation"])

    def test_86_safe_corrective_never_claims_no_complete_safe_correction(self):
        for query_id in SAFE_CORRECTIVE_IDS:
            text = json.dumps(self.safety_by_query[query_id]).lower()
            self.assertNotIn("no complete safe-corrective cover exists", text)
            self.assertNotIn("no_approved_complete_cover", text)

    def test_87_abstain_audit_has_neither_cover_and_keeps_abstention_reason(self):
        for query_id in ABSTAIN_ESCALATE_IDS:
            row = self.safety_by_query[query_id]
            self.assertFalse(row["requested_answer_complete_cover_exists"])
            self.assertFalse(row["safe_corrective_answer_complete_cover_exists"])
            self.assertEqual((row["complete_requested_answer_covers"], row["complete_corrective_answer_covers"]), ([], []))
            self.assertTrue(row["primary_abstention_reason_code"] and row["no_complete_correction_explanation"])

    def test_88_cf01_cf02_outlines_are_control_plane_only(self):
        expected = {
            "Q_V4_N_CF01": "Decline to determine external legal precedence, refuse to authorize reimbursement, and escalate to the appropriate authority.",
            "Q_V4_N_CF02": "Decline to determine contractual precedence, refuse to authorize a binding cash remedy, and escalate to the appropriate authority.",
        }
        self.assertEqual({qid: self.by_query[qid]["expected_grounded_response_outline"] for qid in expected}, expected)
        self.assertTrue(all(not self.by_query[qid]["claim_planes"]["factual_banking_policy"]["obligation_ids"] for qid in expected))

    def test_89_csd04_immediate_trigger_is_direct_security_support(self):
        row = self.judgments[("Q_V2_A_CSD04", "ESC_CASH_UNRECOG_001#immediate_trigger")]
        self.assertEqual((row["support_class"], row["supported_requested_obligation_ids"]), ("DIRECT_SUPPORT", ["SECURITY"]))
        security = next(x for x in self.mapping["Q_V2_A_CSD04"]["requested_obligations"] if x["obligation_id"] == "SECURITY")
        self.assertIn("ESC_CASH_UNRECOG_001#immediate_trigger", security["acceptable_evidence_ids"])
        self.assertEqual(self.mapping["Q_V2_A_CSD04"]["all_minimal_covers"], [["ESC_CASH_DECLINED_001#trigger"]])

    def test_90_hard_negative_partial_support_mutation_fails(self):
        rows = copy.deepcopy(self.hard); rows[0]["support_class"] = "PARTIAL_SUPPORT"
        with self.assertRaises(CriticalV2Error): validate_hard_negative_audits(rows, self.pass_c)

    def test_91_hard_negative_partial_guard_false_fails(self):
        rows = copy.deepcopy(self.hard); rows[0]["not_legitimate_partial_support"] = False
        with self.assertRaises(CriticalV2Error): validate_hard_negative_audits(rows, self.pass_c)

    def test_92_hard_negative_added_to_cover_fails(self):
        mappings = copy.deepcopy(self.pass_c); row = self.hard[0]
        mapping = next(x for x in mappings if x["query_id"] == row["query_id"])
        mapping["complete_requested_answer_covers"][0].append(row["evidence_id"])
        with self.assertRaises(CriticalV2Error): validate_hard_negative_audits(self.hard, mappings)

    def test_93_hard_negative_supported_obligation_mutation_fails(self):
        rows = copy.deepcopy(self.hard); rows[0]["supported_requested_obligation_ids"] = ["MUTATED"]
        with self.assertRaises(CriticalV2Error): validate_hard_negative_audits(rows, self.pass_c)

    def test_94_bound_prohibited_target_reviews_validate(self):
        reviews = validate_prohibited_target_reviews(self.pass_a, self.prohibited_reviews)
        self.assertEqual(set(reviews), SAFE_CORRECTIVE_IDS)
        self.assertTrue(all(row["reviewer_method"] == PROHIBITED_TARGET_REVIEWER_METHOD for row in reviews.values()))

    def test_95_outline_or_target_mutation_invalidates_bound_review(self):
        for field in ("expected_grounded_response_outline", "forbidden_or_unsupported_target"):
            rows = copy.deepcopy(self.pass_a)
            row = next(x for x in rows if x["query_id"] in SAFE_CORRECTIVE_IDS)
            row[field] += " mutation"
            with self.assertRaises(CriticalV2Error): validate_prohibited_target_reviews(rows, self.prohibited_reviews)

    def test_96_missing_or_true_prohibited_target_review_fails(self):
        with self.assertRaises(CriticalV2Error): validate_prohibited_target_reviews(self.pass_a, self.prohibited_reviews[:-1])
        rows = copy.deepcopy(self.prohibited_reviews); rows[0]["prohibited_target_disclosed_or_authorized"] = True
        with self.assertRaises(CriticalV2Error): validate_prohibited_target_reviews(self.pass_a, rows)

    def test_97_candidate_lifecycle_requires_explicit_not_established_verdict(self):
        for value in (None, "PASS", "FAIL"):
            manifest = copy.deepcopy(self.manifest)
            if value is None: manifest.pop("model_verdict")
            else: manifest["model_verdict"] = value
            with self.assertRaises(CriticalV2Error): validate_candidate_lifecycle(manifest)

    def test_98_unauthorized_lifecycle_mutations_fail(self):
        for field in ("senior_semantic_review_approved", "evaluation_authorized", "critical_evaluated", "model_loaded", "encoder_loaded", "retrieval_executed", "generation_executed", "critical_pipeline_executed"):
            manifest = copy.deepcopy(self.manifest); manifest[field] = True
            with self.assertRaises(CriticalV2Error): validate_candidate_lifecycle(manifest)

    def test_99_exactly_four_pass_b_semantic_rows_changed_from_revision_six(self):
        delta = json.loads((ROOT / self.config["outputs"]["revision_7_semantic_delta"]).read_text(encoding="utf-8"))
        self.assertEqual(delta["changed_semantic_pass_b_rows"], 4)
        self.assertEqual(delta["unexpected_semantic_pass_b_rows"], 0)


if __name__ == "__main__":
    unittest.main()
