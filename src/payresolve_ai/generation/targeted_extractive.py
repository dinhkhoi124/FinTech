"""Extractive generation conditioned on an explicit response target."""

from __future__ import annotations

from typing import Sequence

from .routing_v3 import FactualObjective
from .types import EvidenceChunk, GenerationContext, GenerationDraft


class TargetedExtractiveGenerator:
    def __init__(self, stopwords: list[str], standard_max_claims: int, sentence_overlap_weight: float, chunk_score_weight: float):
        self._stopwords = stopwords
        self._standard_max_claims = standard_max_claims
        self._sentence_overlap_weight = sentence_overlap_weight
        self._chunk_score_weight = chunk_score_weight

    def generate_standard(
        self,
        query: str,
        selected_evidence: Sequence[EvidenceChunk],
        generation_context: GenerationContext,
        objectives: Sequence[FactualObjective],
    ) -> GenerationDraft:
        del query, generation_context
        if not objectives:
            raise ValueError("STANDARD generation requires objective-bound extractive sentences")
        by_id = {item.evidence_id: item for item in selected_evidence}
        claims: list[dict] = []
        citations: list[dict] = []
        for index, objective in enumerate(objectives[: self._standard_max_claims], start=1):
            item = by_id.get(objective.evidence_id)
            if item is None or objective.support_quote not in item.content:
                raise ValueError("STANDARD objective is not bound to selected exact evidence")
            alias = f"E{index}"
            citations.append({
                "citation_id": alias,
                "evidence_id": item.evidence_id,
                "document_id": item.document_id,
                "section_id": item.section_id,
                "title": item.title,
                "document_type": item.document_type,
                "status": item.status,
                "version": item.version,
            })
            claims.append({
                "claim_id": f"C{index}",
                "text": objective.support_quote,
                "evidence_ids": [item.evidence_id],
                "support_quotes": [objective.support_quote],
                "citation_ids": [alias],
            })
        return GenerationDraft(claims=claims, citations=citations)

    def generate_corrective(
        self,
        objectives: Sequence[FactualObjective],
        selected_evidence: Sequence[EvidenceChunk],
    ) -> GenerationDraft:
        by_id = {item.evidence_id: item for item in selected_evidence}
        claims: list[dict] = []
        citations: list[dict] = []
        for index, objective in enumerate(objectives, start=1):
            item = by_id[objective.evidence_id]
            alias = f"E{index}"
            claims.append({
                "claim_id": f"C{index}",
                "text": objective.support_quote,
                "evidence_ids": [item.evidence_id],
                "support_quotes": [objective.support_quote],
                "citation_ids": [alias],
                "objective": objective.objective,
            })
            citations.append({
                "citation_id": alias,
                "evidence_id": item.evidence_id,
                "document_id": item.document_id,
                "section_id": item.section_id,
                "title": item.title,
                "document_type": item.document_type,
                "status": item.status,
                "version": item.version,
            })
        return GenerationDraft(claims=claims, citations=citations)
