"""Offline grounded pipeline composition and development metrics."""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

from .citations import CitationError, verify_draft
from .context import ContextError, attach_ranked_evidence, render_context
from .extractive import ExtractiveEvidenceGenerator, extractable_sentences
from .gate import decide_gate
from .support_v2 import decide_gate_v2
from .types import EvidenceChunk, GenerationContext, GenerationDraft, GroundedGenerator


def abstain_response(query: dict[str, Any], prediction: dict[str, Any], gate: dict[str, Any], versions: dict[str, Any], fallback: str, retrieved: list[dict[str, Any]]) -> dict[str, Any]:
    return {"query_id": query["query_id"], "query_text": query["query_text"], "response_type": "ABSTAIN_ESCALATE", "answer_text": fallback, "claims": [], "citations": [], "predicted_intent": prediction["predicted_intent"], "intent_confidence": prediction["diagnostic_confidence"], "retriever_variant": "R0", "retrieved_evidence": retrieved, "selected_evidence": [], "gate": gate, "versions": versions}


def run_case(query: dict[str, Any], ranking: dict[str, Any], prediction: dict[str, Any], chunks: list[dict[str, Any]], idf: dict[str, float], config: dict[str, Any], candidate: dict[str, float], *, mode: str = "EVIDENCE_GATED", generator: GroundedGenerator | None = None) -> dict[str, Any]:
    as_of = date.fromisoformat(config["evaluation_as_of_date"])
    versions = {"pipeline_version": config["pipeline_version"], "generator_version": config["generator_version"], "gate_version": config["gate_version"], "intent_model": "semantic_all_minilm_l6_v2", "retriever": "R0", "retrieval_config_sha256": config["frozen"]["retrieval_config_sha256"], "kb_version": "kb_v1", "kb_canonical_sha256": config["frozen"]["kb_canonical_sha256"]}
    try:
        evidence = attach_ranked_evidence(ranking["rankings"], chunks, as_of)
    except ContextError:
        failed_gate = {"decision": "FAIL", "reason_code": "NO_ELIGIBLE_EVIDENCE", "mode": mode}
        return abstain_response(query, prediction, failed_gate, versions, config["safe_fallback"], [])
    retrieved = [item.to_dict() for item in evidence]
    gate = decide_gate(query["query_text"], evidence, idf, config["tokenizer"]["stopwords"], candidate, extractable=extractable_sentences(evidence), mode=mode)
    if gate["decision"] != "PASS":
        return abstain_response(query, prediction, gate, versions, config["safe_fallback"], retrieved)
    generator = generator or ExtractiveEvidenceGenerator(
        config["tokenizer"]["stopwords"], config["extractive"]["max_claims"],
        config["extractive"]["sentence_overlap_weight"], config["extractive"]["chunk_score_weight"],
    )
    try:
        draft = generator.generate(query["query_text"], evidence, GenerationContext(query["query_id"], render_context(query["query_text"], evidence), idf))
        answer = verify_draft(draft, evidence, as_of)
    except Exception as error:
        reason = "CITATION_CONTRACT_FAILURE" if isinstance(error, CitationError) else "GENERATOR_FAILURE"
        failed_gate = {**gate, "decision": "FAIL", "reason_code": reason}
        return abstain_response(query, prediction, failed_gate, versions, config["safe_fallback"], retrieved)
    return {"query_id": query["query_id"], "query_text": query["query_text"], "response_type": "ANSWER", "answer_text": answer, "claims": draft.claims, "citations": draft.citations, "predicted_intent": prediction["predicted_intent"], "intent_confidence": prediction["diagnostic_confidence"], "retriever_variant": "R0", "retrieved_evidence": retrieved, "selected_evidence": retrieved, "gate": gate, "versions": versions}


def run_case_v2(
    query: dict[str, Any], ranking: dict[str, Any], prediction: dict[str, Any],
    chunks: list[dict[str, Any]], raw_idf: dict[str, float], canonical_idf: dict[str, float],
    base_config: dict[str, Any], v2_config: dict[str, Any], lexicon: dict[str, Any],
    candidate: dict[str, float], *, generator: GroundedGenerator | None = None,
) -> dict[str, Any]:
    """Run gate v2 while retaining the accepted v1 context/generator/verifier."""
    as_of = date.fromisoformat(v2_config["evaluation_as_of_date"])
    versions = {
        "pipeline_version": v2_config["pipeline_version"],
        "generator_version": v2_config["generator_version"],
        "gate_version": v2_config["gate_version"],
        "intent_model": "semantic_all_minilm_l6_v2",
        "retriever": "R0",
        "retrieval_config_sha256": base_config["frozen"]["retrieval_config_sha256"],
        "kb_version": "kb_v1",
        "kb_canonical_sha256": v2_config["frozen"]["kb_canonical_sha256"],
        "lexicon_version": lexicon["version"],
    }
    try:
        evidence = attach_ranked_evidence(ranking["rankings"], chunks, as_of)
    except ContextError:
        gate = {"decision": "FAIL", "reason_code": "NO_ELIGIBLE_EVIDENCE", "mode": "EVIDENCE_GATED"}
        return abstain_response(query, prediction, gate, versions, base_config["safe_fallback"], [])
    retrieved = [item.to_dict() for item in evidence]
    gate = decide_gate_v2(
        query["query_text"], evidence, raw_idf, canonical_idf,
        base_config["tokenizer"]["stopwords"], lexicon, candidate,
        extractable=extractable_sentences(evidence),
    )
    if gate["decision"] != "PASS":
        return abstain_response(query, prediction, gate, versions, base_config["safe_fallback"], retrieved)
    generator = generator or ExtractiveEvidenceGenerator(
        base_config["tokenizer"]["stopwords"], base_config["extractive"]["max_claims"],
        base_config["extractive"]["sentence_overlap_weight"], base_config["extractive"]["chunk_score_weight"],
    )
    try:
        draft = generator.generate(query["query_text"], evidence, GenerationContext(query["query_id"], render_context(query["query_text"], evidence), raw_idf))
        answer = verify_draft(draft, evidence, as_of)
    except Exception as error:
        reason = "CITATION_CONTRACT_FAILURE" if isinstance(error, CitationError) else "GENERATOR_FAILURE"
        failed_gate = {**gate, "decision": "FAIL", "reason_code": reason}
        return abstain_response(query, prediction, failed_gate, versions, base_config["safe_fallback"], retrieved)
    return {"query_id": query["query_id"], "query_text": query["query_text"], "response_type": "ANSWER", "answer_text": answer, "claims": draft.claims, "citations": draft.citations, "predicted_intent": prediction["predicted_intent"], "intent_confidence": prediction["diagnostic_confidence"], "retriever_variant": "R0", "retrieved_evidence": retrieved, "selected_evidence": retrieved, "gate": gate, "versions": versions}


def _output_evidence(row: dict[str, Any]) -> list[EvidenceChunk]:
    return [EvidenceChunk(**{**item, "intent_scope": tuple(item["intent_scope"])}) for item in row.get("selected_evidence", [])]


def _verified_answer(row: dict[str, Any], as_of: date) -> bool:
    if row.get("response_type") != "ANSWER":
        return False
    try:
        verify_draft(GenerationDraft(row.get("claims", []), row.get("citations", [])), _output_evidence(row), as_of)
    except (CitationError, KeyError, TypeError, ValueError):
        return False
    return True


def _supported_claim_count(row: dict[str, Any], as_of: date) -> int:
    citations = row.get("citations", [])
    citation_by_id = {item.get("citation_id"): item for item in citations if isinstance(item, dict)}
    supported = 0
    for claim in row.get("claims", []):
        aliases = claim.get("citation_ids", []) if isinstance(claim, dict) else []
        claim_citations = [citation_by_id[alias] for alias in aliases if alias in citation_by_id]
        try:
            verify_draft(GenerationDraft([claim], claim_citations), _output_evidence(row), as_of)
        except (CitationError, KeyError, TypeError, ValueError):
            continue
        supported += 1
    return supported


def development_metrics(queries: list[dict[str, Any]], outputs: list[dict[str, Any]], as_of: date) -> dict[str, Any]:
    query_by_id = {row["query_id"]: row for row in queries}
    positives = [row for row in outputs if query_by_id[row["query_id"]]["expected_response_type"] == "ANSWER"]
    negatives = [row for row in outputs if query_by_id[row["query_id"]]["expected_response_type"] == "ABSTAIN_ESCALATE"]
    positive_answers = sum(row["response_type"] == "ANSWER" for row in positives)
    relevant_answers = 0
    for row in positives:
        query = query_by_id[row["query_id"]]
        if not _verified_answer(row, as_of):
            continue
        cited = {citation["evidence_id"] for citation in row["citations"]}
        gold = set(query.get("gold_evidence_ids", []))
        acceptable = set(query.get("acceptable_evidence_ids", []))
        success = gold <= cited if query.get("evidence_requirement") == "multi_document" else bool(cited & (gold | acceptable))
        relevant_answers += int(success)
    negative_abstains = sum(row["response_type"] == "ABSTAIN_ESCALATE" for row in negatives)
    unsafe = len(negatives) - negative_abstains
    unnecessary = len(positives) - relevant_answers
    answer_count = sum(row["response_type"] == "ANSWER" for row in outputs)
    verified_answer_count = sum(_verified_answer(row, as_of) for row in outputs)
    total_claims = sum(len(row.get("claims", [])) for row in outputs)
    supported_claims = sum(_supported_claim_count(row, as_of) for row in outputs)
    unsupported = total_claims - supported_claims
    return {
        "cases": len(outputs), "safe_resolution_accuracy": (relevant_answers + negative_abstains) / len(outputs),
        "positive_answer_count": positive_answers, "positive_relevant_answer_count": relevant_answers,
        "positive_wrong_evidence_answer_count": positive_answers - relevant_answers,
        "positive_grounded_resolution_recall": relevant_answers / len(positives) if positives else None,
        "negative_abstention_accuracy": negative_abstains / len(negatives) if negatives else None,
        "unsafe_answer_count": unsafe, "unsafe_answer_rate": unsafe / len(negatives) if negatives else None,
        "unnecessary_abstention_count": unnecessary, "unnecessary_abstention_rate": unnecessary / len(positives) if positives else None,
        "answer_count": answer_count, "verified_answer_count": verified_answer_count,
        "citation_correctness_on_answered": verified_answer_count / answer_count if answer_count else None,
        "citation_correctness_status": "APPLICABLE" if answer_count else "NOT_APPLICABLE_NO_ANSWERS",
        "total_claim_count": total_claims, "unsupported_claim_count": unsupported,
        "unsupported_claim_rate_on_claims": unsupported / total_claims if total_claims else None,
        "unsupported_claim_status": "APPLICABLE" if total_claims else "NOT_APPLICABLE_NO_CLAIMS",
        "response_counts": dict(sorted(Counter(row["response_type"] for row in outputs).items())),
        "reason_code_counts": dict(sorted(Counter(row["gate"]["reason_code"] for row in outputs).items())),
    }
