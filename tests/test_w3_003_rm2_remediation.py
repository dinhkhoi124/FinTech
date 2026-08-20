"""Active P0 regressions for the bounded W3-003 RM2 RED1 candidate."""

from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path

from payresolve_ai.generation.citations import CitationError, verify_draft
from payresolve_ai.generation.gate import build_idf
from payresolve_ai.generation.pipeline_v3 import load_v3_configuration, run_case_v3
from payresolve_ai.generation.routing_v3 import (
    FallbackSupportAuthorization,
    assess_requested_target,
    select_supported_standard_objectives,
)
from payresolve_ai.generation.support_v2 import best_sentence_support, build_canonical_idf
from payresolve_ai.generation.types import EvidenceChunk, GenerationDraft


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/generation/grounded_pipeline_v3.json"


def _chunk(
    evidence_id: str,
    scope: str,
    heading: str,
    content: str,
    score: float,
    rank: int,
    *,
    status: str = "APPROVED",
    document_type: str = "RUNBOOK",
) -> dict:
    document_id, section_id = evidence_id.split("#", 1)
    return {
        "chunk_id": evidence_id,
        "text": f"{heading}\n{content}",
        "document_id": document_id,
        "section_id": section_id,
        "title": f"Synthetic {document_id}",
        "document_type": document_type,
        "status": status,
        "version": "1.0",
        "effective_date": "2026-01-01",
        "expiry_date": None,
        "intent_scope": [scope],
        "heading": heading,
        "content": content,
        "score": score,
        "rank": rank,
    }


def _evidence(row: dict) -> EvidenceChunk:
    return EvidenceChunk(
        evidence_id=row["chunk_id"],
        document_id=row["document_id"],
        section_id=row["section_id"],
        title=row["title"],
        document_type=row["document_type"],
        status=row["status"],
        version=row["version"],
        effective_date=row["effective_date"],
        expiry_date=row["expiry_date"],
        intent_scope=tuple(row["intent_scope"]),
        heading=row["heading"],
        content=row["content"],
        score=row["score"],
        rank=row["rank"],
    )


class W3003RM2RemediationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config, cls.lexicon, cls.dev_rows = load_v3_configuration(ROOT, CONFIG_PATH)

    def _run(self, query_text: str, chunks: list[dict]) -> dict:
        rankings = [
            {"chunk_id": row["chunk_id"], "score": row["score"], "rank": row["rank"]}
            for row in chunks
        ]
        raw_idf = build_idf(chunks, self.config["tokenizer"]["stopwords"])
        canonical_idf = build_canonical_idf(
            chunks, self.lexicon, self.config["tokenizer"]["stopwords"]
        )
        return run_case_v3(
            {"query_id": "RM2_RED1_SYNTHETIC", "query_text": query_text},
            rankings,
            chunks,
            raw_idf,
            canonical_idf,
            self.config,
            self.lexicon,
        )

    def _assess(self, query_text: str, chunks: list[dict]) -> dict:
        canonical_idf = build_canonical_idf(
            chunks, self.lexicon, self.config["tokenizer"]["stopwords"]
        )
        return assess_requested_target(
            query_text,
            tuple(_evidence(row) for row in chunks),
            self.lexicon,
            canonical_idf,
            self.config["tokenizer"]["stopwords"],
            self.config["standard"],
        )

    # Root A: candidate-aware state/domain adjudication.
    def test_a1_later_same_domain_requested_state_is_evaluated(self):
        chunks = [
            _chunk("A1_FAILED#state", "failed_transfer", "Failed transfer", "A failed transfer reached a terminal processing failure.", 0.90, 1),
            _chunk("A1_PENDING#checks", "pending_transfer", "Pending transfer checks", "Check the pending transfer reference and confirm the recipient details.", 0.84, 2),
        ]
        output = self._run("What checks apply to my pending transfer?", chunks)
        self.assertEqual("STANDARD", output["answer_strategy"], output["response_plan"])
        self.assertEqual({"A1_PENDING#checks"}, {row["evidence_id"] for row in output["selected_evidence"]})

    def test_a2_insufficient_requested_state_support_abstains(self):
        chunks = [
            _chunk("A2_FAILED#state", "failed_transfer", "Failed transfer", "A failed transfer reached a terminal processing failure.", 0.90, 1),
            _chunk("A2_PENDING#state", "pending_transfer", "Pending transfer state", "The transfer remains pending.", 0.84, 2),
        ]
        self.assertEqual("ABSTAIN", self._run("What checks apply to my pending transfer?", chunks)["answer_strategy"])

    def test_a3_wrong_domain_same_state_cannot_recover(self):
        chunks = [
            _chunk("A3_FAILED#state", "failed_transfer", "Failed transfer", "A failed transfer reached a terminal processing failure.", 0.90, 1),
            _chunk("A3_CARD#checks", "pending_card_payment", "Pending card checks", "Check the pending card payment merchant.", 0.84, 2),
        ]
        output = self._run("What checks apply to my pending transfer?", chunks)
        self.assertEqual("ABSTAIN", output["answer_strategy"], output["response_plan"])

    def test_a4_competing_ambiguity_remains_fail_closed(self):
        row = next(item for item in self.dev_rows if item["query_id"] == "RM1_DEV_AMBIGUOUS")
        chunks = [
            {**item, "chunk_id": item["evidence_id"], "text": f"{item['heading']}\n{item['content']}", "rank": rank}
            for rank, item in enumerate(row["candidate_evidence"], start=1)
        ]
        output = self._run(row["query_text"], chunks)
        self.assertEqual("ABSTAIN", output["answer_strategy"])
        self.assertEqual("AMBIGUOUS_COMPETING_TARGETS", output["response_plan"]["reason_codes"][0])

    # Root B: exact requested-objective binding with no same-scope padding.
    def test_b1_off_objective_same_scope_evidence_is_not_selected(self):
        chunks = [
            _chunk("B1_CHECKS#checks", "pending_card_payment", "Pending card checks", "Check the merchant name and confirm whether the card payment is duplicated.", 0.88, 1),
            _chunk("B1_STATE#state", "pending_card_payment", "Pending card state", "The card payment remains pending during processing.", 0.84, 2),
        ]
        output = self._run("What checks should I make for a pending card payment?", chunks)
        self.assertEqual("STANDARD", output["answer_strategy"])
        self.assertEqual({"B1_CHECKS#checks"}, {row["evidence_id"] for row in output["selected_evidence"]})
        self.assertFalse(any("remains pending" in row["text"] for row in output["claims"]))

    def test_b2_mixed_chunk_emits_only_exact_checks_sentence(self):
        sentence = "Confirm the merchant name and check whether the charge is duplicated."
        chunks = [_chunk(
            "B2_MIXED#checks", "pending_card_payment", "Pending card checks",
            f"The card payment remains pending during processing. {sentence}", 0.88, 1,
        )]
        output = self._run("What checks should I make for a pending card payment?", chunks)
        self.assertEqual("STANDARD", output["answer_strategy"], output["response_plan"])
        self.assertEqual([sentence], [row["text"] for row in output["claims"]])

    def test_b3_no_requested_objective_sentence_abstains(self):
        chunks = [_chunk("B3_STATE#state", "pending_card_payment", "Pending card state", "The card payment remains pending during processing.", 0.88, 1)]
        output = self._run("What checks should I make for a pending card payment?", chunks)
        self.assertEqual("ABSTAIN", output["answer_strategy"])
        self.assertEqual([], output["claims"])

    def test_b4_tamper_and_ineligible_citations_fail_closed(self):
        chunk = _chunk("B4_CHECKS#checks", "pending_card_payment", "Pending card checks", "Check the merchant name.", 0.88, 1)
        citation = {"citation_id": "E1", "evidence_id": "B4_CHECKS#checks", "document_id": "B4_CHECKS", "section_id": "checks", "title": chunk["title"], "document_type": "RUNBOOK", "status": "APPROVED", "version": "1.0"}
        tampered = GenerationDraft(
            claims=[{"claim_id": "C1", "text": "Invented claim.", "evidence_ids": ["B4_CHECKS#checks"], "support_quotes": ["Invented claim."], "citation_ids": ["E1"]}],
            citations=[citation],
        )
        with self.assertRaises(CitationError):
            verify_draft(tampered, [_evidence(chunk)], date(2026, 8, 16))
        exact = GenerationDraft(
            claims=[{"claim_id": "C1", "text": "Check the merchant name.", "evidence_ids": ["B4_CHECKS#checks"], "support_quotes": ["Check the merchant name."], "citation_ids": ["E1"]}],
            citations=[{**citation, "status": "DRAFT"}],
        )
        with self.assertRaises(CitationError):
            verify_draft(exact, [_evidence({**chunk, "status": "DRAFT"})], date(2026, 8, 16))

    # R1-R6: deliberately narrow CHECKS-only single-target safety boundary.
    def test_r1_transfer_account_rejects_mobile_device_sentence(self):
        chunks = [_chunk("R1_DEVICE#checks", "pending_transfer", "Pending transfer checks", "Check the transfer mobile-device registration.", 0.90, 1)]
        self.assertEqual("ABSTAIN", self._run("What checks apply to my pending transfer recipient account?", chunks)["answer_strategy"])

    def test_r2_card_duplicate_rejects_customer_profile_sentence(self):
        chunks = [_chunk("R2_PROFILE#checks", "pending_card_payment", "Pending card checks", "Check the card payment customer-profile setting.", 0.90, 1)]
        self.assertEqual("ABSTAIN", self._run("What checks confirm a pending card payment merchant duplicate?", chunks)["answer_strategy"])

    def test_r3_account_word_order_twin_keeps_protection(self):
        chunks = [_chunk("R3_DEVICE#checks", "pending_transfer", "Pending transfer checks", "Check the transfer mobile-device registration.", 0.90, 1)]
        self.assertEqual("ABSTAIN", self._run("What account checks apply to my pending transfer?", chunks)["answer_strategy"])

    def test_r4_exact_account_checks_sentence_is_standard(self):
        sentence = "Check the recipient account details for the pending transfer."
        chunks = [_chunk("R4_ACCOUNT#checks", "pending_transfer", "Pending transfer checks", sentence, 0.90, 1)]
        output = self._run("What account checks apply to my pending transfer?", chunks)
        self.assertEqual("STANDARD", output["answer_strategy"], output["response_plan"])
        self.assertEqual([sentence], [row["text"] for row in output["claims"]])

    def test_r5_generic_checks_query_does_not_invent_account_target(self):
        sentence = "Check the pending transfer status."
        chunks = [_chunk("R5_GENERIC#checks", "pending_transfer", "Pending transfer checks", sentence, 0.90, 1)]
        output = self._run("What checks apply to my pending transfer?", chunks)
        self.assertEqual("STANDARD", output["answer_strategy"], output["response_plan"])
        self.assertEqual([sentence], [row["text"] for row in output["claims"]])

    def test_r6_fallback_wrong_checks_target_is_not_authorized(self):
        query = "What account checks apply to my pending transfer?"
        rows = [_chunk("R6_DEVICE#checks", "pending_transfer", "Pending transfer checks", "Check the transfer mobile-device registration.", 0.84, 1)]
        policy = {**self.config["standard"], "min_support_coverage": 1.1}
        authorization = FallbackSupportAuthorization("R6_DEVICE#checks", "Check the transfer mobile-device registration.", "CHECKS", 0.1, "STATE_COMPATIBLE_DIRECT_DIMENSION_FALLBACK")
        selected, objectives = select_supported_standard_objectives(
            query, tuple(_evidence(row) for row in rows), self.lexicon,
            build_canonical_idf(rows, self.lexicon, self.config["tokenizer"]["stopwords"]),
            self.config["tokenizer"]["stopwords"], policy, (authorization,),
        )
        self.assertEqual((), selected)
        self.assertEqual((), objectives)

    # Compatibility boundaries retained from accepted RM1/FIX5 review.
    def test_fallback_exact_account_sentence_remains_authorized(self):
        query = "What account checks apply to my pending transfer?"
        sentence = "Check the recipient account details for the pending transfer."
        rows = [_chunk("F_ACCOUNT#checks", "pending_transfer", "Pending transfer checks", sentence, 0.84, 1)]
        policy = {**self.config["standard"], "min_support_coverage": 1.1}
        authorization = FallbackSupportAuthorization("F_ACCOUNT#checks", sentence, "CHECKS", 0.1, "STATE_COMPATIBLE_DIRECT_DIMENSION_FALLBACK")
        selected, objectives = select_supported_standard_objectives(
            query, tuple(_evidence(row) for row in rows), self.lexicon,
            build_canonical_idf(rows, self.lexicon, self.config["tokenizer"]["stopwords"]),
            self.config["tokenizer"]["stopwords"], policy, (authorization,),
        )
        self.assertEqual(("F_ACCOUNT#checks",), tuple(row.evidence_id for row in selected))
        self.assertEqual((sentence,), tuple(row.support_quote for row in objectives))

    def test_fallback_quote_substitution_fails_closed(self):
        query = "What account checks apply to my pending transfer?"
        sentence = "Check the recipient account details for the pending transfer."
        rows = [_chunk("F_SUB#checks", "pending_transfer", "Pending transfer checks", sentence, 0.84, 1)]
        policy = {**self.config["standard"], "min_support_coverage": 1.1}
        authorization = FallbackSupportAuthorization("F_SUB#checks", "Check a different sentence.", "CHECKS", 0.1, "STATE_COMPATIBLE_DIRECT_DIMENSION_FALLBACK")
        selected, objectives = select_supported_standard_objectives(
            query, tuple(_evidence(row) for row in rows), self.lexicon,
            build_canonical_idf(rows, self.lexicon, self.config["tokenizer"]["stopwords"]),
            self.config["tokenizer"]["stopwords"], policy, (authorization,),
        )
        self.assertEqual((), selected)
        self.assertEqual((), objectives)

    def test_next_action_sentence_matcher_equals_m1_stop_semantics(self):
        stop = _evidence(_chunk("N_STOP#boundary", "cash_withdrawal_not_recognised", "Recognition boundary", "If the customer does not recognize the event, stop this runbook.", 0.88, 1))
        action = _evidence(_chunk("N_USE#action", "cash_withdrawal_not_recognised", "Approved action", "Use the approved unrecognized-withdrawal review path.", 0.87, 1))
        idf = {token: 1.0 for token in "customer recognize event stop runbook use approved unrecognized withdrawal review path".split()}
        self.assertFalse(best_sentence_support("What should I do for an unrecognized ATM cash withdrawal?", [stop], "NEXT_ACTION", self.lexicon, idf, self.config["tokenizer"]["stopwords"], require_sentence_dimension_match=True)["dimension_match"])
        self.assertTrue(best_sentence_support("What should I do for an unrecognized ATM cash withdrawal?", [action], "NEXT_ACTION", self.lexicon, idf, self.config["tokenizer"]["stopwords"], require_sentence_dimension_match=True)["dimension_match"])

    def test_retry_plural_attempts_is_compatible_but_unrelated_attempts_are_not(self):
        valid = [_chunk("RETRY_VALID#boundary", "failed_transfer", "Retry boundary", "Do not recommend repeated attempts until checks confirm the original transfer has no active processing state.", 0.88, 1)]
        output = self._run("My transfer failed. Is it safe to try again?", valid)
        self.assertEqual("STANDARD", output["answer_strategy"], output["response_plan"])
        wrong = [_chunk("RETRY_WRONG#device", "failed_transfer", "Device history", "Repeated login attempts may lock an unrelated mobile device profile.", 0.88, 1)]
        self.assertEqual("ABSTAIN", self._run("My transfer failed. Is it safe to try again?", wrong)["answer_strategy"])

    def test_timing_window_keeps_m1_policy_authority_without_balance_literal(self):
        sentence = "The ledger return can take up to seven days after the reverted card payment."
        chunks = [_chunk("TIMING#policy", "reverted_card_payment", "Reverted card timing", sentence, 0.90, 1, document_type="POLICY")]
        output = self._run("When should my balance reflect a reverted card payment?", chunks)
        self.assertEqual("STANDARD", output["answer_strategy"], output["response_plan"])
        self.assertEqual([sentence], [row["text"] for row in output["claims"]])

    def test_corrective_route_is_unchanged(self):
        row = next(item for item in self.dev_rows if item["query_id"] == "RM1_DEV_PRIVATE_CORRECTIVE")
        chunks = [
            {**item, "chunk_id": item["evidence_id"], "text": f"{item['heading']}\n{item['content']}", "rank": rank}
            for rank, item in enumerate(row["candidate_evidence"], start=1)
        ]
        output = self._run(row["query_text"], chunks)
        self.assertEqual("CORRECTIVE", output["answer_strategy"])
        self.assertTrue(output["claims"])


if __name__ == "__main__":
    unittest.main()
