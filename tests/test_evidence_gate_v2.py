"""W3-001-CR1 canonical support, isolation, and acceptance tests."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from payresolve_ai.generation.support_v2 import (
    best_sentence_support,
    build_canonical_idf,
    canonicalize_text,
    detect_requested_dimension,
    specificity_guard,
)
from payresolve_ai.generation.types import EvidenceChunk
from payresolve_ai.generation.verification_v2 import (
    ADJUDICATION_CONFIG_PATH,
    EvidenceGateV2Error,
    _acceptance,
    _holdout_runtime,
    choose_candidate,
    load_v2_configuration,
    validate_adjudication,
    validate_holdout,
    verify_adjudication,
    verify_preholdout,
    verify_results,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/generation/grounded_pipeline_v2.json"


def evidence(evidence_id: str, content: str, *, heading: str = "Action", rank: int = 1) -> EvidenceChunk:
    document_id, section_id = evidence_id.split("#", 1)
    return EvidenceChunk(evidence_id, document_id, section_id, "Synthetic", "policy", "APPROVED", "1.0", "2026-01-01", None, ("pending_transfer",), heading, content, 0.8, rank)


class EvidenceGateV2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config, cls.base, cls.design, cls.holdout, cls.lexicon = load_v2_configuration(ROOT, CONFIG_PATH)
        cls.stopwords = cls.base["tokenizer"]["stopwords"]

    # Canonical lexicon.
    def test_processing_normalizes_to_pending(self):
        self.assertIn("pending", canonicalize_text("still processing", self.lexicon).split())

    def test_refused_normalizes_to_declined(self):
        self.assertEqual("declined", canonicalize_text("refused", self.lexicon))

    def test_undone_normalizes_to_reverted(self):
        self.assertEqual("reverted", canonicalize_text("undone", self.lexicon))

    def test_recipient_no_credit_normalizes_correctly(self):
        self.assertEqual("recipient_not_received", canonicalize_text("other person has no credit", self.lexicon))

    def test_longest_phrase_match_is_deterministic(self):
        first = canonicalize_text("The recipient did not receive it", self.lexicon)
        second = canonicalize_text("The recipient did not receive it", self.lexicon)
        self.assertEqual(first, second)
        self.assertIn("recipient_not_received", first.split())

    def test_holdout_terms_do_not_mutate_frozen_lexicon(self):
        actual = hashlib.sha256((ROOT / self.config["lexicon_config"]).read_bytes()).hexdigest()
        self.assertEqual(self.config["frozen"]["lexicon_sha256"], actual)
        self.assertFalse(self.lexicon["holdout_outcomes_used"])

    # Requested dimension detector.
    def test_meaning_dimension(self): self.assertEqual("STATE_OR_MEANING", detect_requested_dimension("What does this mean?")["dimension"])
    def test_checks_dimension(self): self.assertEqual("CHECKS", detect_requested_dimension("What should I check?")["dimension"])
    def test_action_dimension(self): self.assertEqual("NEXT_ACTION", detect_requested_dimension("What happens next?")["dimension"])
    def test_timing_dimension(self): self.assertEqual("TIMING_WINDOW", detect_requested_dimension("When should it return?")["dimension"])
    def test_retry_dimension(self): self.assertEqual("RETRY", detect_requested_dimension("Can I try again?")["dimension"])
    def test_specific_internal_detail_dimension(self): self.assertEqual("SPECIFIC_INTERNAL_DETAIL", detect_requested_dimension("What internal queue code applies?")["dimension"])
    def test_unknown_dimension_abstains(self): self.assertEqual("UNKNOWN", detect_requested_dimension("A transaction exists.")["dimension"])

    def test_dimension_precedence_is_deterministic(self):
        query = "When is the internal queue code available?"
        self.assertEqual("SPECIFIC_INTERNAL_DETAIL", detect_requested_dimension(query)["dimension"])
        self.assertEqual(detect_requested_dimension(query), detect_requested_dimension(query))

    # Unsupported specificity.
    def test_unsupported_queue_code_abstains(self):
        result = specificity_guard("Which internal queue code applies?", [evidence("D#s", "Review after two days.")])
        self.assertTrue(result["triggered"])

    def test_unsupported_exact_amount_abstains(self):
        result = specificity_guard("What exact compensation amount is guaranteed?", [evidence("D#s", "Review after five days.")])
        self.assertTrue(result["triggered"])

    def test_supported_specific_detail_can_pass(self):
        result = specificity_guard("Which routing code applies?", [evidence("D#s", "The routing code is DEMO-1.")])
        self.assertFalse(result["triggered"])
        self.assertTrue(result["support_found"])

    def test_generic_word_code_does_not_always_abstain(self):
        self.assertFalse(specificity_guard("What code should I write in my notes?", [evidence("D#s", "Use a masked note.")])["triggered"])

    # Canonical sentence support.
    def _idf(self, items: list[EvidenceChunk]):
        chunks = [{"text": f"{item.heading}\n{item.content}"} for item in items]
        return build_canonical_idf(chunks, self.lexicon, self.stopwords)

    def test_canonical_paraphrase_improves_support(self):
        items = [evidence("D#s", "A pending transfer remains open.", heading="State")]
        result = best_sentence_support("Why is it still processing? What does this mean?", items, "STATE_OR_MEANING", self.lexicon, self._idf(items), self.stopwords)
        self.assertGreater(result["best_sentence_support_coverage"], 0.0)
        self.assertIn("pending", result["sentence_diagnostics"][0]["matched_canonical_tokens"])

    def test_dimension_mismatch_has_zero_support(self):
        items = [evidence("D#s", "A pending transfer remains open.", heading="State")]
        result = best_sentence_support("When can I retry?", items, "RETRY", self.lexicon, self._idf(items), self.stopwords)
        self.assertEqual(0.0, result["best_sentence_support_coverage"])

    def test_best_sentence_support_uses_top3_only(self):
        items = [evidence(f"D{i}#s", "No timing information.", rank=i) for i in range(1, 4)]
        items.append(evidence("D4#s", "Wait two business days.", heading="Timing window", rank=4))
        result = best_sentence_support("How many business days?", items, "TIMING_WINDOW", self.lexicon, self._idf(items), self.stopwords)
        self.assertNotEqual("D4#s", result["best_evidence_id"])

    def test_support_score_is_deterministic(self):
        items = [evidence("D#s", "Wait two business days.", heading="Timing window")]
        args = ("How many business days?", items, "TIMING_WINDOW", self.lexicon, self._idf(items), self.stopwords)
        self.assertEqual(best_sentence_support(*args), best_sentence_support(*args))

    # Selection and isolation (tracked artifacts exist after lifecycle execution).
    def test_v2_grid_has_exact_nine_candidates(self):
        self.assertEqual(9, len(self.config["gate_grid"]["min_top1_score"]) * len(self.config["gate_grid"]["min_best_sentence_support_coverage"]))

    def test_selection_uses_design_set_only(self):
        selection = json.loads((ROOT / self.config["outputs"]["selection"]).read_text(encoding="utf-8"))
        self.assertEqual("gate_v2_design", selection["selection_dataset"])
        self.assertFalse(selection["holdout_metrics_used"])

    def test_holdout_cannot_enter_selection(self):
        selection = json.loads((ROOT / self.config["outputs"]["selection"]).read_text(encoding="utf-8"))
        self.assertEqual(0, selection["holdout_query_ids_used"])

    def test_no_safe_candidate_returns_failed(self):
        self.assertIsNone(choose_candidate([{"eligible": False, "metrics": {}, "policy": {}}]))

    def test_selection_obeys_frozen_tie_break(self):
        def candidate(name, score, coverage):
            return {"candidate_id": name, "eligible": True, "metrics": {"positive_grounded_resolution_recall": 0.5, "safe_resolution_accuracy": 0.75, "intent_family_positive_coverage": 3, "unnecessary_abstention_rate": 0.5, "negative_abstention_accuracy": 1.0}, "policy": {"min_top1_score": score, "min_best_sentence_support_coverage": coverage}}
        selected = choose_candidate([candidate("high", 0.45, 0.2), candidate("low", 0.4, 0.1)])
        self.assertEqual("low", selected["candidate_id"])

    def test_holdout_requires_preselection_manifest(self):
        self.assertEqual("PASS", verify_preholdout(ROOT, CONFIG_PATH, require_unexecuted=False)["status"])

    def test_holdout_runtime_adds_split_without_mutating_frozen_data(self):
        frozen_rows = (ROOT / self.holdout["dataset_path"]).read_text(encoding="utf-8")
        with patch("payresolve_ai.generation.verification_v2._rank_queries", return_value=([], [])) as rank_queries:
            _holdout_runtime(ROOT, CONFIG_PATH)
        runtime_rows = rank_queries.call_args.args[2]
        self.assertTrue(runtime_rows)
        self.assertTrue(all(row["split"] == "holdout" for row in runtime_rows))
        self.assertTrue(all("split" not in json.loads(line) for line in frozen_rows.splitlines()))
        self.assertEqual(frozen_rows, (ROOT / self.holdout["dataset_path"]).read_text(encoding="utf-8"))

    def test_holdout_primary_and_rerun_match(self):
        left = ROOT / self.config["outputs"]["holdout_v2_outputs"]
        right = ROOT / self.config["outputs"]["holdout_v2_reproduction"]
        self.assertEqual(left.read_bytes(), right.read_bytes())

    # Post-holdout relevance adjudication.
    def _adjudication(self):
        return json.loads((ROOT / ADJUDICATION_CONFIG_PATH).read_text(encoding="utf-8"))

    def test_original_holdout_dataset_remains_byte_identical(self):
        actual = hashlib.sha256((ROOT / self.holdout["dataset_path"]).read_bytes()).hexdigest()
        self.assertEqual("6ea54ec1dd79987dcee329a200d6258629050944eabc238d8527581a2b968af8", actual)

    def test_mapping_audit_has_exact_ten_positive_rows(self):
        result = validate_adjudication(ROOT, CONFIG_PATH)
        self.assertEqual(10, len(result["audit"]))
        self.assertEqual(10, len({row["query_id"] for row in result["audit"]}))

    def test_mapping_audit_has_exact_three_omissions(self):
        result = validate_adjudication(ROOT, CONFIG_PATH)
        defects = {row["query_id"]: row["omitted_direct_evidence_ids"] for row in result["audit"] if row["review_status"] == "DEFECT_FOUND"}
        self.assertEqual(result["config"]["approved_omissions"], defects)

    def test_pending_transfer_action_is_direct_timing_support(self):
        rows = {row["query_id"]: row for row in validate_adjudication(ROOT, CONFIG_PATH)["overlay"]}
        self.assertEqual(["RUN_TRANSFER_PENDING_001#action"], rows["Q_V2_HOLD_TR_PEND_001"]["added_acceptable_evidence_ids"])

    def test_recipient_escalation_trigger_is_acceptable_timing_support(self):
        rows = {row["query_id"]: row for row in validate_adjudication(ROOT, CONFIG_PATH)["overlay"]}
        self.assertEqual(["ESC_TRANSFER_RECIPIENT_001#trigger"], rows["Q_V2_HOLD_TR_RECIP_001"]["added_acceptable_evidence_ids"])

    def test_cash_unrecognized_safe_handoff_is_acceptable_security_support(self):
        rows = {row["query_id"]: row for row in validate_adjudication(ROOT, CONFIG_PATH)["overlay"]}
        self.assertEqual(["ESC_CASH_UNRECOG_001#safe_handoff"], rows["Q_V2_HOLD_CASH_UNREC_001"]["added_acceptable_evidence_ids"])

    def test_overlay_has_exact_three_rows(self):
        self.assertEqual(3, len(validate_adjudication(ROOT, CONFIG_PATH)["overlay"]))

    def test_overlay_can_only_add_acceptable_evidence(self):
        for row in validate_adjudication(ROOT, CONFIG_PATH)["overlay"]:
            self.assertEqual("ADD_ACCEPTABLE_EVIDENCE", row["adjudication_type"])
            self.assertEqual(1, len(row["added_acceptable_evidence_ids"]))

    def test_original_metrics_remain_failed(self):
        result = verify_adjudication(ROOT, CONFIG_PATH)
        self.assertEqual("FAILED", result["original_verdict"])
        self.assertEqual(1, result["original_metrics"]["positive_wrong_evidence_answer_count"])

    def test_adjudicated_metrics_recompute_to_pass(self):
        result = verify_adjudication(ROOT, CONFIG_PATH)
        self.assertEqual("PASS", result["adjudicated_verdict"])
        self.assertEqual(0.7, result["adjudicated_metrics"]["positive_grounded_resolution_recall"])
        self.assertEqual(0, result["adjudicated_metrics"]["positive_wrong_evidence_answer_count"])

    def test_two_non_metric_affecting_omissions_do_not_change_outputs(self):
        outputs = {row["query_id"]: row for row in json.loads("[" + ",".join((ROOT / self.config["outputs"]["holdout_v2_outputs"]).read_text(encoding="utf-8").splitlines()) + "]")}
        for query_id, evidence_id in (
            ("Q_V2_HOLD_TR_RECIP_001", "ESC_TRANSFER_RECIPIENT_001#trigger"),
            ("Q_V2_HOLD_CASH_UNREC_001", "ESC_CASH_UNRECOG_001#safe_handoff"),
        ):
            self.assertNotIn(evidence_id, {citation["evidence_id"] for citation in outputs[query_id].get("citations", [])})

    def _assert_adjudication_tamper_rejected(self, mutate, pattern: str) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary_root = Path(directory)
            for name in ("configs", "data", "reports"):
                shutil.copytree(ROOT / name, temporary_root / name)
            temporary_config = temporary_root / "configs/generation/grounded_pipeline_v2.json"
            adjudication_path = temporary_root / ADJUDICATION_CONFIG_PATH
            adjudication = json.loads(adjudication_path.read_text(encoding="utf-8"))
            mutate(temporary_root, adjudication)
            adjudication_path.write_text(json.dumps(adjudication, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(EvidenceGateV2Error, pattern):
                validate_adjudication(temporary_root, temporary_config)

    def test_overlay_cannot_change_gold(self):
        def mutate(root, adjudication):
            path = root / adjudication["overlay"]
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            rows[0]["original_gold_evidence_ids"] = ["TAMPERED#gold"]
            path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")
            adjudication["frozen"]["overlay_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        self._assert_adjudication_tamper_rejected(mutate, "unapproved-adjudication-operation")

    def test_overlay_cannot_change_query_metadata(self):
        def mutate(root, adjudication):
            path = root / adjudication["overlay"]
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            rows[0]["requested_dimension"] = "CHECKS"
            path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")
            adjudication["frozen"]["overlay_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        self._assert_adjudication_tamper_rejected(mutate, "unapproved-adjudication-operation")

    def test_overlay_rejects_non_audited_evidence(self):
        def mutate(root, adjudication):
            path = root / adjudication["overlay"]
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            rows[0]["added_acceptable_evidence_ids"] = ["RUN_TRANSFER_PENDING_001#checks"]
            path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")
            adjudication["frozen"]["overlay_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        self._assert_adjudication_tamper_rejected(mutate, "mapping-audit-overlay-mismatch")

    def test_overlay_rejects_draft_or_expired_evidence(self):
        def mutate(root, adjudication):
            query_id = "Q_V2_HOLD_TR_PEND_001"; replacement = "POL_TRANSFER_PENDING_003#proposed_window"
            audit_path = root / adjudication["mapping_audit"]
            text = audit_path.read_text(encoding="utf-8").replace("RUN_TRANSFER_PENDING_001#action", replacement)
            audit_path.write_text(text, encoding="utf-8")
            adjudication["frozen"]["mapping_audit_sha256"] = hashlib.sha256(audit_path.read_bytes()).hexdigest()
            adjudication["approved_omissions"][query_id] = replacement
            overlay_path = root / adjudication["overlay"]
            rows = [json.loads(line) for line in overlay_path.read_text(encoding="utf-8").splitlines()]
            rows[0]["added_acceptable_evidence_ids"] = [replacement]
            overlay_path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")
            adjudication["frozen"]["overlay_sha256"] = hashlib.sha256(overlay_path.read_bytes()).hexdigest()
        self._assert_adjudication_tamper_rejected(mutate, "adjudication-evidence-not-eligible")

    def test_overlay_quote_must_match_source(self):
        def mutate(root, adjudication):
            path = root / adjudication["overlay"]
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            rows[0]["exact_support_quote"] += " tampered"
            path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")
            adjudication["frozen"]["overlay_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        self._assert_adjudication_tamper_rejected(mutate, "adjudication-support-quote-mismatch")

    def test_mapping_audit_incomplete_is_rejected(self):
        def mutate(root, adjudication):
            path = root / adjudication["mapping_audit"]
            rows = path.read_text(encoding="utf-8").splitlines()
            path.write_text("\n".join(rows[:-1]) + "\n", encoding="utf-8")
            adjudication["frozen"]["mapping_audit_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        self._assert_adjudication_tamper_rejected(mutate, "mapping-audit-incomplete")

    def test_overlay_row_count_tamper_is_rejected(self):
        def mutate(root, adjudication):
            path = root / adjudication["overlay"]
            rows = path.read_text(encoding="utf-8").splitlines()
            path.write_text("\n".join(rows[:-1]) + "\n", encoding="utf-8")
            adjudication["frozen"]["overlay_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        self._assert_adjudication_tamper_rejected(mutate, "adjudication-overlay-count-mismatch")

    # Acceptance contract.
    def _metrics(self, **overrides):
        base = {"unsafe_answer_count": 0, "positive_wrong_evidence_answer_count": 0, "unsupported_claim_count": 0, "draft_expired_citation_count": 0, "citation_metadata_failure_count": 0, "positive_relevant_answer_count": 5, "positive_grounded_resolution_recall": 0.5, "intent_families_with_positive_resolution": ["transfer", "card_payment", "cash_withdrawal"], "negative_abstention_accuracy": 1.0, "safe_resolution_accuracy": 0.75, "unsafe_answer_rate": 0.0}
        return {**base, **overrides}

    def test_unsafe_answer_fails_cr1(self):
        self.assertEqual("FAILED", _acceptance(self.config, self._metrics(), self._metrics(unsafe_answer_count=1), self._metrics(positive_grounded_resolution_recall=0.0))["verdict"])

    def test_wrong_evidence_answer_fails_cr1(self):
        self.assertEqual("FAILED", _acceptance(self.config, self._metrics(), self._metrics(positive_wrong_evidence_answer_count=1), self._metrics(positive_grounded_resolution_recall=0.0))["verdict"])

    def test_positive_recall_below_half_is_partial(self):
        result = _acceptance(self.config, self._metrics(), self._metrics(positive_relevant_answer_count=4, positive_grounded_resolution_recall=0.4, safe_resolution_accuracy=0.7), self._metrics(positive_grounded_resolution_recall=0.0))
        self.assertEqual("PARTIAL", result["verdict"])

    def test_all_three_families_required(self):
        result = _acceptance(self.config, self._metrics(), self._metrics(intent_families_with_positive_resolution=["transfer", "card_payment"]), self._metrics(positive_grounded_resolution_recall=0.0))
        self.assertEqual("PARTIAL", result["verdict"])

    def test_successful_recovery_passes(self):
        self.assertEqual("PASS", _acceptance(self.config, self._metrics(), self._metrics(), self._metrics(positive_grounded_resolution_recall=0.0))["verdict"])

    # Tracked verifier.
    def test_no_encoder_retrieval_or_generation_rerun_is_required(self):
        with patch("payresolve_ai.generation.verification_v2._rank_queries", side_effect=AssertionError("runtime forbidden")), patch("payresolve_ai.generation.verification_v2.run_case", side_effect=AssertionError("generation forbidden")), patch("payresolve_ai.generation.verification_v2.run_case_v2", side_effect=AssertionError("generation forbidden")):
            self.assertEqual("PASS", verify_results(ROOT, CONFIG_PATH, write=False)["status"])

    def test_frozen_holdout_validator_passes(self):
        self.assertEqual("PASS", validate_holdout(ROOT, CONFIG_PATH)["status"])

    def _assert_tracked_tamper_rejected(self, mutate) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary_root = Path(directory)
            for name in ("configs", "data", "reports"):
                shutil.copytree(ROOT / name, temporary_root / name)
            temporary_config = temporary_root / "configs/generation/grounded_pipeline_v2.json"
            mutate(temporary_root, temporary_config)
            with self.assertRaises(EvidenceGateV2Error):
                verify_results(temporary_root, temporary_config, write=False)

    def test_holdout_membership_contamination_is_rejected(self):
        def mutate(root, _):
            path = root / self.holdout["dataset_path"]
            rows = path.read_text(encoding="utf-8").splitlines()
            row = json.loads(rows[0]); row["query_text"] += " altered"
            rows[0] = json.dumps(row, ensure_ascii=False, sort_keys=True)
            path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        self._assert_tracked_tamper_rejected(mutate)

    def test_threshold_drift_is_rejected(self):
        def mutate(_, config_path):
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["gate_grid"]["min_top1_score"][0] = 0.39
            config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        self._assert_tracked_tamper_rejected(mutate)

    def test_lexicon_drift_is_rejected(self):
        def mutate(root, _):
            path = root / self.config["lexicon_config"]
            path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
        self._assert_tracked_tamper_rejected(mutate)

    def test_dimension_rule_drift_is_rejected(self):
        def mutate(_, config_path):
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["dimension_precedence"] = list(reversed(payload["dimension_precedence"]))
            config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        self._assert_tracked_tamper_rejected(mutate)

    def test_missing_specificity_slot_is_rejected(self):
        def mutate(root, _):
            path = root / self.config["outputs"]["holdout_v2_outputs"]
            rows = path.read_text(encoding="utf-8").splitlines()
            row = json.loads(rows[0]); row["gate"]["specificity_guard"]["requested_slots"] = []
            rows[0] = json.dumps(row, ensure_ascii=False, sort_keys=True)
            path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        self._assert_tracked_tamper_rejected(mutate)

    def test_wrong_evidence_positive_hidden_in_metrics_is_rejected(self):
        def mutate(root, _):
            path = root / self.config["outputs"]["holdout_metrics"]
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["gate_v2"]["positive_wrong_evidence_answer_count"] += 1
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        self._assert_tracked_tamper_rejected(mutate)

    def test_unsafe_answer_hidden_in_metrics_is_rejected(self):
        def mutate(root, _):
            path = root / self.config["outputs"]["holdout_metrics"]
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["gate_v2"]["unsafe_answer_count"] += 1
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        self._assert_tracked_tamper_rejected(mutate)

    def test_holdout_selection_contamination_is_rejected(self):
        def mutate(root, _):
            path = root / self.config["outputs"]["selection"]
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["holdout_query_ids_used"] = 1
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        self._assert_tracked_tamper_rejected(mutate)

    def test_gate_v1_output_tamper_is_rejected(self):
        def mutate(root, _):
            path = root / self.config["outputs"]["holdout_v1_outputs"]
            rows = path.read_text(encoding="utf-8").splitlines()
            row = json.loads(rows[0]); row["response_type"] = "TAMPERED"
            rows[0] = json.dumps(row, ensure_ascii=False, sort_keys=True)
            path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        self._assert_tracked_tamper_rejected(mutate)

    def test_gate_v2_output_tamper_is_rejected(self):
        def mutate(root, _):
            path = root / self.config["outputs"]["holdout_v2_outputs"]
            rows = path.read_text(encoding="utf-8").splitlines()
            row = json.loads(rows[0]); row["response_type"] = "TAMPERED"
            rows[0] = json.dumps(row, ensure_ascii=False, sort_keys=True)
            path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        self._assert_tracked_tamper_rejected(mutate)


if __name__ == "__main__":
    unittest.main()
