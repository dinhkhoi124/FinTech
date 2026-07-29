"""Deterministic evidence-only sentence generator."""

from __future__ import annotations

import math
import re
from typing import Sequence

from .gate import tokenize
from .types import EvidenceChunk, GenerationContext, GenerationDraft


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]


def extractable_sentences(evidence: Sequence[EvidenceChunk]) -> bool:
    return any(split_sentences(item.content) for item in evidence)


class ExtractiveEvidenceGenerator:
    def __init__(self, stopwords: list[str], max_claims: int, sentence_overlap_weight: float, chunk_score_weight: float):
        weights = (sentence_overlap_weight, chunk_score_weight)
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 for value in weights):
            raise ValueError("extractive weights must be non-negative numbers")
        if not math.isclose(float(sentence_overlap_weight) + float(chunk_score_weight), 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("extractive weight sum must equal 1.0")
        self.stopwords = stopwords
        self.max_claims = max_claims
        self.sentence_overlap_weight = float(sentence_overlap_weight)
        self.chunk_score_weight = float(chunk_score_weight)

    def generate(self, query: str, selected_evidence: Sequence[EvidenceChunk], generation_context: GenerationContext) -> GenerationDraft:
        query_tokens = set(tokenize(query, self.stopwords))
        fallback = max(generation_context.idf.values(), default=1.0)
        candidates: list[tuple[float, int, str, int, str, str, EvidenceChunk]] = []
        for item in selected_evidence:
            for sentence_index, sentence in enumerate(split_sentences(item.content)):
                sentence_tokens = set(tokenize(sentence, self.stopwords))
                denominator = math.fsum(generation_context.idf.get(token, fallback) for token in sorted(query_tokens)) or 1.0
                overlap = math.fsum(generation_context.idf.get(token, fallback) for token in sorted(query_tokens & sentence_tokens)) / denominator
                combined = self.sentence_overlap_weight * overlap + self.chunk_score_weight * ((item.score + 1.0) / 2.0)
                candidates.append((-combined, item.rank, item.section_id, sentence_index, item.evidence_id, sentence, item))
        candidates.sort()
        chosen: list[tuple[str, EvidenceChunk]] = []
        used_chunks: set[str] = set()
        for candidate in candidates:
            if candidate[6].evidence_id not in used_chunks:
                chosen.append((candidate[5], candidate[6])); used_chunks.add(candidate[6].evidence_id)
                if len(chosen) == self.max_claims: break
        if len(chosen) < self.max_claims:
            for candidate in candidates:
                pair = (candidate[5], candidate[6])
                if pair not in chosen:
                    chosen.append(pair)
                    if len(chosen) == self.max_claims: break
        claims, citations = [], []
        for index, (sentence, item) in enumerate(chosen, start=1):
            alias = f"E{index}"
            claims.append({"claim_id": f"C{index}", "text": sentence, "evidence_ids": [item.evidence_id], "support_quotes": [sentence], "citation_ids": [alias]})
            citations.append({"citation_id": alias, "evidence_id": item.evidence_id, "document_id": item.document_id, "section_id": item.section_id, "title": item.title, "document_type": item.document_type, "status": item.status, "version": item.version})
        return GenerationDraft(claims=claims, citations=citations)
