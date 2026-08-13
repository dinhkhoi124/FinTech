from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import numpy as np

from payresolve_ai.retrieval.benchmark import (
    RetrievalBenchmarkError,
    _artifact_hashes,
    _json,
    _paired,
    _read_csv,
    _tracked_corpus,
    _validate_dev_rankings,
    _validate_error_rows,
    _validate_paired_artifact,
    _validate_rankings,
    _verify_artifact_hashes,
    assert_reproducible,
    classify_error_case,
    choose_lambda,
    load_config,
    metrics,
    validate_encoder_contract,
    validate_frozen_selection,
    validate_selection_membership,
    verify_results,
)
from payresolve_ai.retrieval.corpus import CorpusError, build_corpus, validate_corpus
from payresolve_ai.retrieval.dense import DenseRetrievalError, r0_scores, r1_scores, rank, validate_embeddings


def document(status="APPROVED", effective="2026-01-01", expiry=None, doc_id="DOC_001"):
    return {"document_id":doc_id,"document_family_id":"F","title":"Title","document_type":"faq","intent_scope":["intent_a"],"intent_slugs":["intent_a"],"intent_family":"family","product":"p","status":status,"version":"1","effective_date":effective,"expiry_date":expiry,"risk_level":"low","content_sections":[{"section_id":"one","heading":"H","content":"C"}]}


def query(qid="Q", response="ANSWER", gold=None, acceptable=None):
    return {
        "query_id":qid,"expected_response_type":response,
        "gold_evidence_ids":gold or ["A#one"],"acceptable_evidence_ids":acceptable or [],
        "forbidden_evidence_ids":[],"hard_negative_evidence_ids":[],
        "evidence_requirement":"single_section",
    }


def ranking(qid="Q", ids=None):
    ids=ids or ["A#one","B#one","C#one"]
    return {"query_id":qid,"rankings":[{"chunk_id":value,"score":1-index/10} for index,value in enumerate(ids)]}


STATUSES = {f"{letter}#one": "APPROVED" for letter in "ABCD"}


class CorpusTests(unittest.TestCase):
    def test_eligible_section_corpus_is_deterministic(self):
        docs=[document(doc_id="B_001"),document(doc_id="A_001")]; a=build_corpus(docs,date(2026,7,28),"{title}|{heading}|{content}"); b=build_corpus(list(reversed(docs)),date(2026,7,28),"{title}|{heading}|{content}"); self.assertEqual(a,b)
    def test_draft_document_cannot_enter_corpus(self): self.assertEqual(build_corpus([document("DRAFT")],date(2026,7,28),"{content}"),[])
    def test_expired_document_cannot_enter_corpus(self): self.assertEqual(build_corpus([document("APPROVED",expiry="2026-07-28")],date(2026,7,28),"{content}"),[])
    def test_future_effective_document_cannot_enter_corpus(self): self.assertEqual(build_corpus([document(effective="2026-07-29")],date(2026,7,28),"{content}"),[])
    def test_duplicate_chunk_id_fails(self):
        with self.assertRaises(CorpusError): build_corpus([document(),document()],date(2026,7,28),"{content}")
    def test_chunk_intent_metadata_is_preserved(self): self.assertEqual(build_corpus([document()],date(2026,7,28),"{content}")[0]["intent_scope"],["intent_a"])
    def test_missing_sections_yields_no_chunks(self): self.assertEqual(build_corpus([{**document(),"content_sections":[]}],date(2026,7,28),"{content}"),[])


class DenseTests(unittest.TestCase):
    def test_embedding_chunk_alignment_mismatch_fails(self):
        with self.assertRaises(DenseRetrievalError): validate_embeddings(np.ones((2,384),dtype=np.float32),3)
    def test_encoder_revision_mismatch_fails(self):
        with self.assertRaises(RetrievalBenchmarkError): validate_encoder_contract({"revision":"wrong","dimension":384,"normalize_embeddings":True})
    def test_r0_score_equals_cosine_similarity(self): self.assertAlmostEqual(float(r0_scores(np.array([1.,0.]),np.array([[1.,0.],[0.,1.]]))[0]),1.0)
    def test_r0_ignores_predicted_intent(self): self.assertTrue(np.array_equal(r0_scores(np.array([1.,0.]),np.eye(2)),r0_scores(np.array([1.,0.]),np.eye(2))))
    def test_r1_applies_boost_only_on_matching_scope(self): self.assertTrue(np.allclose(r1_scores(np.array([.1,.2]),"a",[["a"],["b"]],.1,(.1,)),[.2,.2]))
    def test_r1_does_not_hard_filter_nonmatching_chunks(self): self.assertEqual(len(r1_scores(np.array([.1,.2]),"a",[["a"],["b"]],.1,(.1,))),2)
    def test_prediction_outside_subset_produces_no_boost(self): self.assertTrue(np.allclose(r1_scores(np.array([.1,.2]),"z",[["a"],["b"]],.1,(.1,)),[.1,.2]))
    def test_lambda_outside_frozen_grid_fails(self):
        with self.assertRaises(DenseRetrievalError): r1_scores(np.array([.1]),"a",[["a"]],.2,(.1,))
    def test_rank_tie_breaks_by_chunk_id(self): self.assertEqual(rank(np.array([.5,.5]),["B","A"],2)[0]["chunk_id"],"A")


class ProtocolMetricTests(unittest.TestCase):
    def test_dev_selection_uses_development_ids_only(self): validate_selection_membership([f"DEV{i}" for i in range(10)],["LOCK"])
    def test_locked_membership_cannot_enter_dev_selection(self):
        with self.assertRaises(RetrievalBenchmarkError): validate_selection_membership(["SAME"]*10,["SAME"])
    def test_selected_lambda_follows_metric_rule(self):
        grid=[{"lambda":.2,"metrics":{"strict_mrr_at_3":.5,"strict_hit_at_1":.4,"strict_recall_at_3":.6}},{"lambda":.1,"metrics":{"strict_mrr_at_3":.5,"strict_hit_at_1":.4,"strict_recall_at_3":.6}}]; self.assertEqual(choose_lambda(grid)["lambda"],.1)
    def test_locked_evaluation_requires_frozen_selection_manifest(self):
        with self.assertRaises(RetrievalBenchmarkError): validate_frozen_selection({"status":"DRAFT","locked_evaluated":False,"retrieval_config_sha256":"a"},"a")
    def test_locked_config_cannot_change_after_freeze(self):
        with self.assertRaises(RetrievalBenchmarkError): validate_frozen_selection({"status":"FROZEN_PRELOCKED","locked_evaluated":False,"retrieval_config_sha256":"a"},"b")
    def test_strict_metrics_use_only_gold_evidence(self): self.assertEqual(metrics([query(acceptable=["B#one"])],[ranking(ids=["B#one","C#one","D#one"])],STATUSES)["strict_hit_at_1"],0)
    def test_relaxed_metrics_include_acceptable_evidence(self): self.assertEqual(metrics([query(acceptable=["B#one"])],[ranking(ids=["B#one","C#one","D#one"])],STATUSES)["relaxed_hit_at_1"],1)
    def test_multi_document_recall_is_calculated_correctly(self): self.assertEqual(metrics([query(gold=["A#one","B#one"])],[ranking(ids=["A#one","C#one","D#one"])],STATUSES)["strict_recall_at_3"],.5)
    def test_complete_coverage_requires_every_gold_section(self): self.assertEqual(metrics([query(gold=["A#one","B#one"])],[ranking(ids=["A#one","C#one","D#one"])],STATUSES)["complete_gold_coverage_at_3"],0)
    def test_safety_queries_are_excluded_from_answer_mrr(self): self.assertEqual(metrics([query(),query("S","ABSTAIN_ESCALATE")],[ranking(),ranking("S")],STATUSES)["answer_queries"],1)
    def test_wrong_status_leakage_is_detected(self): self.assertGreater(metrics([query()],[ranking()],{"A#one":"DRAFT","B#one":"APPROVED","C#one":"APPROVED"})["wrong_status_leakage_rate"],0)
    def test_paired_outcomes_partition_all_answer_queries(self):
        result=_paired([query()],[ranking()], [ranking(ids=["B#one","A#one","C#one"])]); self.assertEqual(sum(result["counts"][key] for key in ("WIN","LOSS","TIE")),1)
    def test_primary_and_reproducibility_rankings_must_match(self):
        stable={"r0":[ranking()],"r1":[ranking()],"metrics":{},"paired":{}}; primary={"stable":stable}; rerun=copy.deepcopy(primary); rerun["stable"]["r1"][0]["rankings"][0]["chunk_id"]="X"
        with self.assertRaises(RetrievalBenchmarkError): assert_reproducible(primary,rerun,1e-7)
    def test_metric_artifact_tampering_is_detected_by_recompute(self): self.assertNotEqual(metrics([query()],[ranking()],STATUSES)["strict_mrr_at_3"],0.5)


class ErrorTaxonomyTests(unittest.TestCase):
    def _prediction(self, correct=True):
        return {"predicted_intent":"intent_a" if correct else "intent_b","prediction_correct":correct}

    def test_gold_chunk_itself_does_not_trigger_category_f(self):
        self.assertEqual(
            classify_error_case(query(), self._prediction(False), ["A#one","B#one","C#one"], ["A#one","B#one","C#one"], reviewed=True),
            "D",
        )

    def test_category_f_requires_non_gold_sibling_section(self):
        case=query(gold=["A#gold"])
        self.assertEqual(
            classify_error_case(case, self._prediction(), ["B#one","A#gold","C#one"], ["A#wrong","A#gold","C#one"], reviewed=True),
            "F",
        )

    def test_category_f_requires_sibling_to_outrank_gold(self):
        case=query(gold=["A#gold"])
        self.assertEqual(
            classify_error_case(case, self._prediction(), ["A#gold","B#one","A#wrong"], ["A#gold","B#one","A#wrong"], reviewed=True),
            "I",
        )

    def test_wrong_classifier_with_gold_retained_is_category_d(self):
        self.assertEqual(
            classify_error_case(query(), self._prediction(False), ["A#one","B#one","C#one"], ["A#one","C#one","B#one"], reviewed=True),
            "D",
        )

    def test_hard_negative_above_gold_is_category_e(self):
        case=query(gold=["A#gold"]); case["hard_negative_evidence_ids"]=["B#hard"]
        self.assertEqual(
            classify_error_case(case, self._prediction(), ["B#hard","A#gold","C#one"], ["B#hard","A#gold","C#one"], reviewed=True),
            "E",
        )


class ReviewCorrectionArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.config_path = cls.root / "configs/retrieval/kb_v1_r0_r1.json"
        cls.config = load_config(cls.root, cls.config_path)
        from payresolve_ai.retrieval.corpus import load_jsonl
        cls.load_jsonl = staticmethod(load_jsonl)
        cls.queries = load_jsonl(cls.root / cls.config["gold_mapping"])
        cls.predictions = load_jsonl(cls.root / cls.config["outputs"]["classifier_predictions"])
        cls.r0 = load_jsonl(cls.root / cls.config["outputs"]["locked_r0"])
        cls.r1 = load_jsonl(cls.root / cls.config["outputs"]["locked_r1"])
        chunks, cls.all_status, _ = _tracked_corpus(cls.root, cls.config)
        cls.candidate_ids = {row["chunk_id"] for row in chunks}

    def _copy_dev_evidence(self, target: Path):
        for name in ("dev_selection", "dev_rankings", "classifier_predictions"):
            source = self.root / self.config["outputs"][name]
            destination = target / self.config["outputs"][name]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    def _mutate_json(self, path: Path, mutate):
        payload = json.loads(path.read_text(encoding="utf-8")); mutate(payload)
        path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    def _mutate_jsonl(self, path: Path, mutate):
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]; mutate(rows)
        path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")

    def test_safety_queries_are_excluded_from_error_categories(self):
        errors = _read_csv(self.root / self.config["outputs"]["error_analysis"])
        safety = {row["query_id"] for row in self.queries if row["expected_response_type"] == "ABSTAIN_ESCALATE"}
        self.assertTrue({row["query_id"] for row in errors}.isdisjoint(safety))

    def test_safety_diagnostics_contains_all_ten_queries(self):
        rows = _read_csv(self.root / self.config["outputs"]["safety_diagnostics"])
        self.assertEqual(len(rows), 10)

    def test_answer_error_analysis_contains_only_answer_queries(self):
        response = {row["query_id"]: row["expected_response_type"] for row in self.queries}
        rows = _read_csv(self.root / self.config["outputs"]["error_analysis"])
        self.assertEqual(len(rows), 28); self.assertTrue(all(response[row["query_id"]] == "ANSWER" for row in rows))

    def test_dev_rankings_have_exact_five_variants_per_query(self):
        result = _validate_dev_rankings(self.root, self.config, self.queries, self.candidate_ids, self.all_status)
        self.assertEqual((result["rows"], result["variants_per_query"]), (50, 5))

    def test_dev_metrics_recompute_from_rankings(self):
        result = _validate_dev_rankings(self.root, self.config, self.queries, self.candidate_ids, self.all_status)
        self.assertEqual(result["metrics"]["R1_lambda_0.15"]["strict_mrr_at_3"], 0.4)

    def test_dev_metric_tampering_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp); self._copy_dev_evidence(target)
            selection = target / self.config["outputs"]["dev_selection"]
            self._mutate_json(selection, lambda value: value["lambda_grid"][2]["metrics"].__setitem__("strict_mrr_at_3", 0.9))
            with self.assertRaisesRegex(RetrievalBenchmarkError, "grid metric tampering"):
                _validate_dev_rankings(target, self.config, self.queries, self.candidate_ids, self.all_status)

    def test_dev_metric_and_selected_lambda_consistent_tampering_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp); self._copy_dev_evidence(target)
            selection = target / self.config["outputs"]["dev_selection"]
            def mutate(value):
                value["lambda_grid"][3]["metrics"]["strict_mrr_at_3"] = 0.9
                value["selected_lambda"] = 0.20
            self._mutate_json(selection, mutate)
            with self.assertRaisesRegex(RetrievalBenchmarkError, "grid metric tampering"):
                _validate_dev_rankings(target, self.config, self.queries, self.candidate_ids, self.all_status)

    def test_dev_selected_lambda_tampering_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp); self._copy_dev_evidence(target)
            selection = target / self.config["outputs"]["dev_selection"]
            self._mutate_json(selection, lambda value: value.__setitem__("selected_lambda", 0.20))
            with self.assertRaisesRegex(RetrievalBenchmarkError, "selected lambda tampering"):
                _validate_dev_rankings(target, self.config, self.queries, self.candidate_ids, self.all_status)

    def test_dev_rankings_reject_locked_query_id(self):
        locked_id = next(row["query_id"] for row in self.queries if row["split"] == "locked_test")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp); self._copy_dev_evidence(target); path = target / self.config["outputs"]["dev_rankings"]
            self._mutate_jsonl(path, lambda rows: rows[0].__setitem__("query_id", locked_id))
            with self.assertRaisesRegex(RetrievalBenchmarkError, "locked query ID"):
                _validate_dev_rankings(target, self.config, self.queries, self.candidate_ids, self.all_status)

    def test_dev_rankings_reject_missing_lambda_variant(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp); self._copy_dev_evidence(target); path = target / self.config["outputs"]["dev_rankings"]
            self._mutate_jsonl(path, lambda rows: rows.pop())
            with self.assertRaisesRegex(RetrievalBenchmarkError, "exactly 50"):
                _validate_dev_rankings(target, self.config, self.queries, self.candidate_ids, self.all_status)

    def test_dev_rankings_reject_duplicate_variant(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp); self._copy_dev_evidence(target); path = target / self.config["outputs"]["dev_rankings"]
            def mutate(rows):
                rows[-1]["query_id"] = rows[0]["query_id"]; rows[-1]["variant"] = rows[0]["variant"]; rows[-1]["lambda"] = rows[0]["lambda"]
            self._mutate_jsonl(path, mutate)
            with self.assertRaisesRegex(RetrievalBenchmarkError, "duplicate development ranking variant"):
                _validate_dev_rankings(target, self.config, self.queries, self.candidate_ids, self.all_status)

    def _copy_hash_evidence(self, target: Path):
        config_target = target / "configs/retrieval/kb_v1_r0_r1.json"; config_target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(self.config_path, config_target)
        for relative in self.config["outputs"].values():
            source = self.root / relative
            if source.is_file():
                destination = target / relative; destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, destination)
        return config_target

    def test_version_manifest_detects_dev_selection_hash_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp); config_path=self._copy_hash_evidence(target); manifest=_json(target/self.config["outputs"]["version_manifest"])
            path=target/self.config["outputs"]["dev_selection"]; path.write_text(path.read_text(encoding="utf-8")+" ",encoding="utf-8")
            with self.assertRaisesRegex(RetrievalBenchmarkError,"dev_selection"):
                _verify_artifact_hashes(target,config_path,self.config,manifest)

    def test_version_manifest_detects_corpus_manifest_hash_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp); config_path=self._copy_hash_evidence(target); manifest=_json(target/self.config["outputs"]["version_manifest"])
            path=target/self.config["outputs"]["corpus_manifest"]; path.write_text(path.read_text(encoding="utf-8")+" ",encoding="utf-8")
            with self.assertRaisesRegex(RetrievalBenchmarkError,"corpus_manifest"):
                _verify_artifact_hashes(target,config_path,self.config,manifest)

    def test_ranking_rejects_noneligible_chunk(self):
        statuses={**self.all_status,"FUTURE_001#one":"APPROVED"}
        with self.assertRaisesRegex(RetrievalBenchmarkError,"non-candidate"):
            _validate_rankings([ranking(ids=["FUTURE_001#one",*list(self.candidate_ids)[:2]])],{"Q"},self.candidate_ids,statuses,label="mutation")

    def test_ranking_rejects_draft_or_expired_chunk(self):
        bad=next(chunk_id for chunk_id,status in self.all_status.items() if status in {"DRAFT","EXPIRED"})
        with self.assertRaisesRegex(RetrievalBenchmarkError,"DRAFT|EXPIRED"):
            _validate_rankings([ranking(ids=[bad,*list(self.candidate_ids)[:2]])],{"Q"},self.candidate_ids,self.all_status,label="mutation")

    def test_locked_rankings_reject_development_membership(self):
        dev_id=next(iter({row["query_id"] for row in self.queries if row["split"]=="development"}))
        with self.assertRaisesRegex(RetrievalBenchmarkError,"membership"):
            _validate_rankings([ranking(qid=dev_id,ids=list(self.candidate_ids)[:3])],{"LOCK"},self.candidate_ids,self.all_status,label="locked")

    def test_paired_outcome_tampering_fails(self):
        locked=[row for row in self.queries if row["split"]=="locked_test"]
        r0=self.load_jsonl(self.root/self.config["outputs"]["locked_r0"]); r1=self.load_jsonl(self.root/self.config["outputs"]["locked_r1"])
        stored=_json(self.root/self.config["outputs"]["paired"]); stored["counts"]["WIN"] += 1
        with self.assertRaisesRegex(RetrievalBenchmarkError,"paired outcome artifact tampering"):
            _validate_paired_artifact(locked,r0,r1,stored)

    def test_error_categories_reject_safety_query(self):
        locked=[row for row in self.queries if row["split"]=="locked_test"]
        rows=_read_csv(self.root/self.config["outputs"]["error_analysis"]); safety_id=next(row["query_id"] for row in locked if row["expected_response_type"]=="ABSTAIN_ESCALATE")
        rows[0]["query_id"] = safety_id
        with self.assertRaisesRegex(RetrievalBenchmarkError,"ANSWER error-analysis membership"):
            _validate_error_rows(rows,locked,self.predictions,self.r0,self.r1)

    def test_error_row_category_is_recomputed_from_rankings(self):
        locked=[row for row in self.queries if row["split"]=="locked_test"]
        rows=_read_csv(self.root/self.config["outputs"]["error_analysis"])
        target=next(row for row in rows if row["category"]=="D")
        target["automatic_category"]="F"; target["category"]="F"
        with self.assertRaisesRegex(RetrievalBenchmarkError,"false-correct-document-wrong-section"):
            _validate_error_rows(rows,locked,self.predictions,self.r0,self.r1)

    def test_category_tampering_with_same_aggregate_counts_fails(self):
        locked=[row for row in self.queries if row["split"]=="locked_test"]
        rows=_read_csv(self.root/self.config["outputs"]["error_analysis"])
        first=next(row for row in rows if row["automatic_category"]=="D" and row["category"]=="D")
        second=next(row for row in rows if row["automatic_category"]=="E" and row["category"]=="E")
        first["automatic_category"],second["automatic_category"]=second["automatic_category"],first["automatic_category"]
        first["category"],second["category"]=second["category"],first["category"]
        with self.assertRaisesRegex(RetrievalBenchmarkError,"category-mismatch"):
            _validate_error_rows(rows,locked,self.predictions,self.r0,self.r1)

    def test_tracked_verify_detects_post_week2_implementation_change_without_local_cache(self):
        with mock.patch("payresolve_ai.retrieval.benchmark._load_runtime", side_effect=AssertionError("cache used")), mock.patch("payresolve_ai.retrieval.benchmark._load_classifier", side_effect=AssertionError("model used")), mock.patch("payresolve_ai.retrieval.benchmark._encoder", side_effect=AssertionError("encoder used")):
            # R13 intentionally changes benchmark.py to force local-only encoder
            # loading. The frozen Week-2 manifest must expose that provenance
            # drift without loading cache/model/encoder; it must not be rewritten.
            with self.assertRaisesRegex(RetrievalBenchmarkError, "implementation hash mismatch"):
                verify_results(self.root,self.config_path,write=False)


if __name__ == "__main__": unittest.main()
