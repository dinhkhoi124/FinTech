"""Typed contracts for the deterministic grounded pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class EvidenceChunk:
    evidence_id: str
    document_id: str
    section_id: str
    title: str
    document_type: str
    status: str
    version: str
    effective_date: str
    expiry_date: str | None
    intent_scope: tuple[str, ...]
    heading: str
    content: str
    score: float
    rank: int

    def to_dict(self) -> dict:
        value = asdict(self)
        value["intent_scope"] = list(self.intent_scope)
        return value


@dataclass(frozen=True)
class GenerationContext:
    query_id: str
    context_block: str
    idf: dict[str, float]


@dataclass(frozen=True)
class GenerationDraft:
    claims: list[dict]
    citations: list[dict]


class GroundedGenerator(Protocol):
    def generate(
        self,
        query: str,
        selected_evidence: Sequence[EvidenceChunk],
        generation_context: GenerationContext,
    ) -> GenerationDraft: ...
