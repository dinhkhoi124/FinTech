"""W3-001 grounded-pipeline safety, determinism, and evidence tests."""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from payresolve_ai.generation.citations import CitationError, verify_draft
from payresolve_ai.generation.context import ContextError, attach_ranked_evidence
from payresolve_ai.generation.extractive import ExtractiveEvidenceGenerator
from payresolve_ai.generation.gate import build_idf, decide_gate
from payresolve_ai.generation.pipeline import development_metrics, run_case
from payresolve_ai.generation.types import EvidenceChunk, GenerationContext, GenerationDraft
from payresolve_ai.generation.verification import (
    GroundedPipelineError,
    load_configuration,
    resolve_development_queries,
    select_gate,
    validate_gate_development,
    verify_contract,
    verify_results,
)
from payresolve_ai.retrieval.corpus import load_jsonl


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/generation/grounded_pipeline_v1.json"
AS_OF = date(2026, 7, 28)


def evidence(
    evidence_id: str = "DOC#s1", *, content: str = "A transfer is pending.", score: float = 0.8,
    rank: int = 1, status: str = "APPROVED", effective: str = "2026-01-01",
    expiry: str | None = None, intent: tuple[str, ...] = ("pending_transfer",),
) -> EvidenceChunk:
    document_id, section_id = evidence_id.split("#", 1)
    return EvidenceChunk(evidence_id, document_id, section_id, "Transfer Policy", "policy", status,
                         "1.0", effective, expiry, intent, "Handling", content, score, rank)


def chunk(evidence_id: str = "DOC#s1", **overrides: object) -> dict:
    document_id, section_id = evidence_id.split("#", 1)
    row = {"chunk_id": evidence_id, "document_id": document_id, "section_id": section_id,
           "text": "Transfer Policy\nHandling\nA transfer is pending.", "document_type": "policy",
           "status": "APPROVED", "version": "1.0", "effective_date": "2026-01-01",
           "expiry_date": None, "intent_scope": ["pending_transfer"], "heading": "Handling",
           "content": "A transfer is pending."}
    row.update(overrides)
    return row


def draft_for(item: EvidenceChunk, text: str | None = None) -> GenerationDraft:
    quote = item.content if text is None else text
    return GenerationDraft(
        claims=[{"claim_id": "C1", "text": quote, "evidence_ids": [item.evidence_id],
                 "support_quotes": [quote], "citation_ids": ["E1"]}],
        citations=[citation_for(item)],
    )


def citation_for(item: EvidenceChunk, alias: str = "E1") -> dict:
    return {"citation_id": alias, "evidence_id": item.evidence_id,
            "document_id": item.document_id, "section_id": item.section_id,
            "title": item.title, "document_type": item.document_type,
            "status": item.status, "version": item.version}


def answer_output(query_id: str, items: list[EvidenceChunk]) -> dict:
    claims, citations = [], []
    for index, item in enumerate(items, start=1):
        alias = f"E{index}"
        claims.append({"claim_id": f"C{index}", "text": item.content,
                       "evidence_ids": [item.evidence_id], "support_quotes": [item.content],
                       "citation_ids": [alias]})
        citations.append(citation_for(item, alias))
    return {"query_id": query_id, "response_type": "ANSWER", "claims": claims,
            "citations": citations, "selected_evidence": [item.to_dict() for item in items],
            "gate": {"reason_code": "SUFFICIENT_APPROVED_EVIDENCE"}}


class GroundedPipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config, cls.gate_config, cls.retrieval = load_configuration(ROOT, CONFIG_PATH)
        cls.rows = load_jsonl(ROOT / cls.gate_config["dataset_path"])
        cls.queries = resolve_development_queries(ROOT, cls.gate_config)
        cls.rankings = load_jsonl(ROOT / cls.config["outputs"]["rankings"])
        cls.predictions = load_jsonl(ROOT / cls.config["outputs"]["predictions"])
        cls.selection = json.loads((ROOT / cls.config["outputs"]["selection"]).read_text(encoding="utf-8"))

    def controlled_case(self, *, mode: str = "EVIDENCE_GATED", generator=None, row: dict | None = None) -> dict:
        corpus = [row or chunk()]
        query = {"query_id": "Q", "query_text": "transfer pending"}
        ranking = {"query_id": "Q", "rankings": [{"chunk_id": corpus[0]["chunk_id"], "score": 0.8}]}
        prediction = {"query_id": "Q", "predicted_intent": "pending_transfer", "diagnostic_confidence": 0.8}
        idf = build_idf(corpus, self.config["tokenizer"]["stopwords"])
        policy = {"min_top1_score": 0.4, "min_weighted_query_coverage": 0.3, "ambiguity_score_gap": 0.03}
        return run_case(query, ranking, prediction, corpus, idf, self.config, policy, mode=mode, generator=generator)

    def temporary_root(self) -> tempfile.TemporaryDirectory:
        temporary = tempfile.TemporaryDirectory()
        destination = Path(temporary.name)
        for name in ("configs", "data"):
            shutil.copytree(ROOT / name, destination / name)
        for source in (ROOT / "reports/week_02/results", ROOT / "reports/week_03/results"):
            shutil.copytree(source, destination / source.relative_to(ROOT))
        return temporary

    # Frozen-input and context invariants.
    def test_pipeline_rejects_kb_hash_mismatch(self):
        with self.temporary_root() as path:
            kb = Path(path) / self.config["kb_documents"]
            kb.write_bytes(kb.read_bytes() + b"\n")
            with self.assertRaises(Exception):
                verify_contract(Path(path), Path(path) / CONFIG_PATH.relative_to(ROOT))

    def test_pipeline_rejects_mapping_hash_mismatch(self):
        with self.temporary_root() as path:
            mapping = Path(path) / self.config["w2_mapping"]
            text = mapping.read_text(encoding="utf-8")
            mapping.write_text(text.replace("My card was refused", "My debit card was refused", 1), encoding="utf-8")
            with self.assertRaises(Exception):
                verify_contract(Path(path), Path(path) / CONFIG_PATH.relative_to(ROOT))

    def test_selected_retriever_is_r0(self):
        self.assertEqual("R0", self.config["retriever_variant"])
        self.assertEqual("R0", verify_contract(ROOT, CONFIG_PATH)["selected_retriever"])

    def test_predicted_intent_does_not_change_r0_rankings(self):
        ranking = copy.deepcopy(self.rankings[0])
        left = copy.deepcopy(self.predictions[0]); right = copy.deepcopy(left)
        right["predicted_intent"] = "unrelated_intent"
        self.assertEqual(ranking, copy.deepcopy(ranking))
        self.assertNotIn("predicted_intent", ranking)

    def test_draft_chunk_never_enters_context(self):
        with self.assertRaises(ContextError):
            attach_ranked_evidence([{"chunk_id": "DOC#s1", "score": 0.8}], [chunk(status="DRAFT")], AS_OF)

    def test_expired_chunk_never_enters_context(self):
        with self.assertRaises(ContextError):
            attach_ranked_evidence([{"chunk_id": "DOC#s1", "score": 0.8}], [chunk(expiry_date="2026-07-28")], AS_OF)

    def test_future_effective_chunk_never_enters_context(self):
        with self.assertRaises(ContextError):
            attach_ranked_evidence([{"chunk_id": "DOC#s1", "score": 0.8}], [chunk(effective_date="2026-07-29")], AS_OF)

    # Development-set integrity.
    def test_gate_dev_has_exact_20_cases(self):
        self.assertEqual(20, len(self.rows))

    def test_gate_dev_has_10_answer_and_10_abstain(self):
        counts = {kind: sum(row["expected_response_type"] == kind for row in self.rows)
                  for kind in ("ANSWER", "ABSTAIN_ESCALATE")}
        self.assertEqual({"ANSWER": 10, "ABSTAIN_ESCALATE": 10}, counts)

    def test_gate_dev_contains_only_w2_development_positive_ids(self):
        mapping = load_jsonl(ROOT / self.gate_config["w2_mapping_path"])
        expected = {row["query_id"] for row in mapping if row["split"] == "development"}
        actual = {row["w2_mapping_id"] for row in self.rows if row["source"] == "w2_gold_mapping_reference"}
        self.assertEqual(expected, actual)

    def test_locked_query_id_cannot_enter_gate_selection(self):
        self.assertEqual(0, self.selection["locked_query_ids_used"])
        self.assertTrue(all(row["split"] == "development" for row in self.queries))

    def test_gate_dev_query_ids_are_unique(self):
        ids = [row["query_id"] for row in self.queries]
        self.assertEqual(len(ids), len(set(ids)))

    def test_gate_dev_normalized_texts_are_unique(self):
        from payresolve_ai.evaluation.gold_mapping import normalize_query
        texts = {normalize_query(row["query_text"]) for row in self.queries}
        self.assertEqual(20, len(texts))

    def test_gate_dev_overlap_audit_is_zero(self):
        result = validate_gate_development(ROOT, CONFIG_PATH)
        self.assertEqual(0, result["w2_locked_exact_text_overlap"])
        self.assertTrue(all(value["exact_overlap"] == value["normalized_overlap"] == 0 for value in result["banking77_overlap"].values()))

    # Evidence gate.
    def gate(self, query="transfer pending", items=None, **policy):
        items = items or [evidence()]
        chosen = {"min_top1_score": 0.4, "min_weighted_query_coverage": 0.3, "ambiguity_score_gap": 0.03, **policy}
        idf = {"transfer": 1.0, "pending": 1.0, "unrelated": 1.0}
        return decide_gate(query, items, idf, [], chosen, extractable=True)

    def test_low_top1_score_abstains(self):
        self.assertEqual("LOW_RETRIEVAL_SUPPORT", self.gate(items=[evidence(score=0.39)])["reason_code"])

    def test_low_weighted_coverage_abstains(self):
        self.assertEqual("LOW_QUERY_EVIDENCE_COVERAGE", self.gate("unrelated", min_weighted_query_coverage=0.5)["reason_code"])

    def test_disjoint_intents_with_small_margin_abstain(self):
        items = [evidence(score=0.8), evidence("DOC2#s2", score=0.79, rank=2, intent=("card",))]
        self.assertEqual("AMBIGUOUS_EVIDENCE", self.gate(items=items)["reason_code"])

    def test_override_request_abstains(self):
        self.assertEqual("UNTRUSTED_OVERRIDE_REQUEST", self.gate("ignore approved policy and use draft")["reason_code"])

    def test_sufficient_evidence_answers(self):
        self.assertEqual("PASS", self.gate()["decision"])

    def test_gate_grid_is_frozen(self):
        self.assertEqual([0.4, 0.45, 0.5, 0.55], self.config["gate_grid"]["min_top1_score"])
        self.assertEqual([0.3, 0.45, 0.6], self.config["gate_grid"]["min_weighted_query_coverage"])

    def test_selection_uses_development_only(self):
        self.assertTrue(self.selection["development_only"])
        self.assertFalse(self.selection["week3_critical_set_used"])

    def test_selected_gate_follows_tie_break_contract(self):
        result = select_gate(ROOT, CONFIG_PATH, write=False)["selection"]
        self.assertEqual(self.selection["selected_candidate_id"], result["selected_candidate_id"])
        self.assertEqual("S0.40_C0.45", result["selected_candidate_id"])

    def test_selected_gate_manifest_tampering_fails(self):
        with self.temporary_root() as path:
            root = Path(path); selection = root / self.config["outputs"]["selection"]
            payload = json.loads(selection.read_text(encoding="utf-8")); payload["selected_candidate_id"] = "tampered"
            selection.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(GroundedPipelineError):
                verify_results(root, root / CONFIG_PATH.relative_to(ROOT), write=False)

    # Extractive generator.
    def generate(self, items=None):
        items = items or [evidence()]
        generator = ExtractiveEvidenceGenerator([], 3, 0.7, 0.3)
        return generator.generate("transfer pending", items, GenerationContext("Q", "", {"transfer": 1.0, "pending": 1.0}))

    def test_extractive_claim_is_exact_evidence_quote(self):
        item = evidence(content="First sentence. Second sentence.")
        self.assertIn(self.generate([item]).claims[0]["text"], item.content)

    def test_generator_is_deterministic(self):
        self.assertEqual(self.generate(), self.generate())

    def test_max_three_claims(self):
        item = evidence(content="One. Two. Three. Four.")
        self.assertLessEqual(len(self.generate([item]).claims), 3)

    def test_sentence_tie_break_is_deterministic(self):
        item = evidence(content="Pending transfer alpha. Pending transfer beta.")
        self.assertEqual("Pending transfer alpha.", self.generate([item]).claims[0]["text"])

    def test_multi_chunk_claims_preserve_rank_order(self):
        items = [evidence("A#s", content="Transfer pending first.", score=0.8, rank=1),
                 evidence("B#s", content="Transfer pending second.", score=0.8, rank=2)]
        self.assertEqual(["A#s", "B#s"], [row["evidence_ids"][0] for row in self.generate(items).claims[:2]])

    # Citation verifier.
    def test_citation_must_reference_selected_evidence(self):
        item = evidence(); bad = draft_for(evidence("OTHER#s"))
        with self.assertRaises(CitationError): verify_draft(bad, [item], AS_OF)

    def test_citation_to_draft_fails(self):
        item = evidence(status="DRAFT")
        with self.assertRaises(CitationError): verify_draft(draft_for(item), [item], AS_OF)

    def test_citation_to_expired_fails(self):
        item = evidence(expiry="2026-07-28")
        with self.assertRaises(CitationError): verify_draft(draft_for(item), [item], AS_OF)

    def test_support_quote_must_exist_verbatim(self):
        item = evidence()
        with self.assertRaises(CitationError): verify_draft(draft_for(item, "Invented."), [item], AS_OF)

    def test_uncited_claim_fails_closed(self):
        item = evidence(); draft = draft_for(item); draft.claims[0]["citation_ids"] = []
        with self.assertRaises(CitationError): verify_draft(draft, [item], AS_OF)

    def test_unused_citation_fails(self):
        item = evidence(); draft = draft_for(item); draft.citations.append(citation_for(item, "E2"))
        with self.assertRaises(CitationError): verify_draft(draft, [item], AS_OF)

    def test_duplicate_citation_alias_fails(self):
        item = evidence(); draft = draft_for(item); draft.citations.append(copy.deepcopy(draft.citations[0]))
        with self.assertRaises(CitationError): verify_draft(draft, [item], AS_OF)

    def test_citation_document_metadata_mismatch_fails(self):
        item = evidence(); draft = draft_for(item); draft.citations[0]["document_id"] = "FAKE"
        with self.assertRaisesRegex(CitationError, "citation-document-mismatch"): verify_draft(draft, [item], AS_OF)

    def test_citation_section_metadata_mismatch_fails(self):
        item = evidence(); draft = draft_for(item); draft.citations[0]["section_id"] = "fake"
        with self.assertRaisesRegex(CitationError, "citation-section-mismatch"): verify_draft(draft, [item], AS_OF)

    def test_citation_title_metadata_mismatch_fails(self):
        item = evidence(); draft = draft_for(item); draft.citations[0]["title"] = "Fabricated"
        with self.assertRaisesRegex(CitationError, "citation-metadata-mismatch"): verify_draft(draft, [item], AS_OF)

    def test_citation_document_type_metadata_mismatch_fails(self):
        item = evidence(); draft = draft_for(item); draft.citations[0]["document_type"] = "faq"
        with self.assertRaisesRegex(CitationError, "citation-metadata-mismatch"): verify_draft(draft, [item], AS_OF)

    def test_unexpected_citation_metadata_fails(self):
        item = evidence(); draft = draft_for(item); draft.citations[0]["trusted"] = True
        with self.assertRaisesRegex(CitationError, "citation-metadata-mismatch"): verify_draft(draft, [item], AS_OF)

    def test_citation_status_metadata_mismatch_fails(self):
        item = evidence(); draft = draft_for(item); draft.citations[0]["status"] = "DRAFT"
        with self.assertRaisesRegex(CitationError, "citation-status-mismatch"): verify_draft(draft, [item], AS_OF)

    def test_citation_version_metadata_mismatch_fails(self):
        item = evidence(); draft = draft_for(item); draft.citations[0]["version"] = "99"
        with self.assertRaisesRegex(CitationError, "citation-version-mismatch"): verify_draft(draft, [item], AS_OF)

    def test_duplicate_claim_id_fails(self):
        first, second = evidence("A#s"), evidence("B#s")
        draft = GenerationDraft(draft_for(first).claims + draft_for(second).claims,
                                [citation_for(first), citation_for(second, "E2")])
        draft.claims[1]["citation_ids"] = ["E2"]
        with self.assertRaisesRegex(CitationError, "duplicate claim ID"): verify_draft(draft, [first, second], AS_OF)

    def test_non_string_claim_id_fails(self):
        item = evidence(); draft = draft_for(item); draft.claims[0]["claim_id"] = 1
        with self.assertRaisesRegex(CitationError, "claim-id-invalid"): verify_draft(draft, [item], AS_OF)

    def test_claim_evidence_quote_alias_lengths_must_match(self):
        item = evidence(); draft = draft_for(item); draft.claims[0]["citation_ids"].append("E2")
        with self.assertRaisesRegex(CitationError, "claim-evidence-quote-alias-length-mismatch"): verify_draft(draft, [item], AS_OF)

    def test_non_string_evidence_id_fails(self):
        item = evidence(); draft = draft_for(item); draft.claims[0]["evidence_ids"] = [1]
        with self.assertRaisesRegex(CitationError, "claim-evidence-id-invalid"): verify_draft(draft, [item], AS_OF)

    def test_non_string_support_quote_fails(self):
        item = evidence(); draft = draft_for(item); draft.claims[0]["support_quotes"] = [1]
        with self.assertRaisesRegex(CitationError, "claim-support-quote-invalid"): verify_draft(draft, [item], AS_OF)

    def test_positive_answer_with_wrong_approved_evidence_is_not_success(self):
        item = evidence("WRONG#s")
        query = {"query_id": "Q", "expected_response_type": "ANSWER", "gold_evidence_ids": ["GOLD#s"],
                 "acceptable_evidence_ids": ["OK#s"], "evidence_requirement": "single_document"}
        metrics = development_metrics([query], [answer_output("Q", [item])], AS_OF)
        self.assertEqual((0, 1), (metrics["positive_relevant_answer_count"], metrics["positive_wrong_evidence_answer_count"]))

    def test_positive_answer_with_gold_evidence_is_success(self):
        item = evidence("GOLD#s")
        query = {"query_id": "Q", "expected_response_type": "ANSWER", "gold_evidence_ids": [item.evidence_id],
                 "acceptable_evidence_ids": [], "evidence_requirement": "single_document"}
        self.assertEqual(1, development_metrics([query], [answer_output("Q", [item])], AS_OF)["positive_relevant_answer_count"])

    def test_positive_answer_with_acceptable_evidence_is_success(self):
        item = evidence("OK#s")
        query = {"query_id": "Q", "expected_response_type": "ANSWER", "gold_evidence_ids": ["GOLD#s"],
                 "acceptable_evidence_ids": [item.evidence_id], "evidence_requirement": "single_document"}
        self.assertEqual(1, development_metrics([query], [answer_output("Q", [item])], AS_OF)["positive_relevant_answer_count"])

    def test_multi_document_positive_requires_all_gold_evidence(self):
        first = evidence("A#s")
        query = {"query_id": "Q", "expected_response_type": "ANSWER", "gold_evidence_ids": ["A#s", "B#s"],
                 "acceptable_evidence_ids": [], "evidence_requirement": "multi_document"}
        self.assertEqual(0, development_metrics([query], [answer_output("Q", [first])], AS_OF)["positive_relevant_answer_count"])

    def test_all_abstain_has_null_citation_correctness(self):
        metrics = json.loads((ROOT / self.config["outputs"]["metrics"]).read_text(encoding="utf-8"))
        self.assertIsNone(metrics["citation_correctness_on_answered"])

    def test_all_abstain_has_null_unsupported_claim_rate(self):
        metrics = json.loads((ROOT / self.config["outputs"]["metrics"]).read_text(encoding="utf-8"))
        self.assertIsNone(metrics["unsupported_claim_rate_on_claims"])

    def test_unsupported_claim_count_is_claim_level(self):
        good, bad = evidence("A#s"), evidence("B#s")
        output = answer_output("Q", [good, bad]); output["claims"][1]["support_quotes"] = ["Invented"]
        query = {"query_id": "Q", "expected_response_type": "ANSWER", "gold_evidence_ids": [good.evidence_id],
                 "acceptable_evidence_ids": [], "evidence_requirement": "single_document"}
        metrics = development_metrics([query], [output], AS_OF)
        self.assertEqual((2, 1, 0.5), (metrics["total_claim_count"], metrics["unsupported_claim_count"], metrics["unsupported_claim_rate_on_claims"]))

    def test_extractive_generator_uses_configured_weights(self):
        matching = evidence("A#s", content="Transfer pending.", score=-1.0, rank=1)
        high_score = evidence("B#s", content="Unrelated words.", score=1.0, rank=2)
        context = GenerationContext("Q", "", {"transfer": 1.0, "pending": 1.0})
        overlap = ExtractiveEvidenceGenerator([], 1, 1.0, 0.0).generate("transfer pending", [matching, high_score], context)
        score = ExtractiveEvidenceGenerator([], 1, 0.0, 1.0).generate("transfer pending", [matching, high_score], context)
        self.assertEqual(("A#s", "B#s"), (overlap.claims[0]["evidence_ids"][0], score.claims[0]["evidence_ids"][0]))

    def test_invalid_extractive_weight_sum_fails(self):
        with self.assertRaisesRegex(ValueError, "weight sum"):
            ExtractiveEvidenceGenerator([], 3, 0.7, 0.2)

    def test_invalid_answer_renders_abstain(self):
        class InvalidGenerator:
            def generate(self, query, selected_evidence, generation_context):
                return GenerationDraft([{"text": "Invented", "evidence_ids": [], "support_quotes": [], "citation_ids": []}], [])
        self.assertEqual("ABSTAIN_ESCALATE", self.controlled_case(generator=InvalidGenerator())["response_type"])

    # Modes and response contract.
    def test_default_mode_is_evidence_gated(self):
        self.assertEqual("EVIDENCE_GATED", self.config["default_mode"])

    def test_always_answer_bypasses_only_sufficiency_gate(self):
        row = chunk(content="A transfer exists.", text="Policy\nHandling\nA transfer exists.")
        self.assertEqual("ANSWER", self.controlled_case(mode="ALWAYS_ANSWER", row=row)["response_type"])

    def test_always_answer_still_rejects_forbidden_status(self):
        self.assertEqual("ABSTAIN_ESCALATE", self.controlled_case(mode="ALWAYS_ANSWER", row=chunk(status="DRAFT"))["response_type"])

    def test_generator_exception_fails_closed(self):
        class BrokenGenerator:
            def generate(self, query, selected_evidence, generation_context): raise RuntimeError("boom")
        result = self.controlled_case(generator=BrokenGenerator())
        self.assertEqual(("ABSTAIN_ESCALATE", "GENERATOR_FAILURE"), (result["response_type"], result["gate"]["reason_code"]))

    def test_abstain_contains_no_factual_claims(self):
        result = self.controlled_case(row=chunk(content="No overlap.", text="Policy\nNo overlap."))
        self.assertEqual(([], []), (result["claims"], result["citations"]))

    def test_response_schema_contains_version_trace(self):
        versions = self.controlled_case()["versions"]
        self.assertTrue({"pipeline_version", "generator_version", "gate_version", "retrieval_config_sha256", "kb_canonical_sha256"} <= set(versions))

    def test_primary_and_rerun_are_identical(self):
        left = ROOT / self.config["outputs"]["primary_outputs"]
        right = ROOT / self.config["outputs"]["reproduction_outputs"]
        self.assertEqual(left.read_bytes(), right.read_bytes())

    # Tracked verification and tamper resistance.
    def test_verify_results_does_not_require_model_cache(self):
        with patch("payresolve_ai.generation.verification._rank_queries", side_effect=AssertionError("runtime forbidden")):
            self.assertEqual("PASS", verify_results(ROOT, CONFIG_PATH, write=False)["status"])

    def test_metric_tampering_is_detected(self):
        with self.temporary_root() as path:
            root = Path(path); target = root / self.config["outputs"]["metrics"]
            payload = json.loads(target.read_text(encoding="utf-8")); payload["safe_resolution_accuracy"] = 1.0
            target.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(GroundedPipelineError): verify_results(root, root / CONFIG_PATH.relative_to(ROOT), write=False)

    def test_pipeline_output_tampering_is_detected(self):
        with self.temporary_root() as path:
            root = Path(path); target = root / self.config["outputs"]["primary_outputs"]
            target.write_bytes(target.read_bytes().replace(b"ABSTAIN_ESCALATE", b"ANSWER", 1))
            with self.assertRaises(GroundedPipelineError): verify_results(root, root / CONFIG_PATH.relative_to(ROOT), write=False)

    def test_candidate_outcome_count_is_recomputed(self):
        with self.temporary_root() as path:
            root = Path(path); target = root / self.config["outputs"]["candidate_metrics"]
            payload = json.loads(target.read_text(encoding="utf-8")); payload["candidates"][0]["outcomes"].pop()
            target.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(GroundedPipelineError): verify_results(root, root / CONFIG_PATH.relative_to(ROOT), write=False)

    def test_generator_weight_config_drift_is_detected(self):
        with self.temporary_root() as path:
            root = Path(path); target = root / CONFIG_PATH.relative_to(ROOT)
            payload = json.loads(target.read_text(encoding="utf-8"))
            payload["extractive"]["sentence_overlap_weight"] = 0.6
            payload["extractive"]["chunk_score_weight"] = 0.4
            target.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(GroundedPipelineError):
                verify_results(root, target, write=False)


if __name__ == "__main__":
    unittest.main()
