"""Approved/effective context construction with deterministic escaping."""

from __future__ import annotations

import html
from datetime import date
from typing import Any

from payresolve_ai.retrieval.corpus import build_corpus, validate_corpus

from .types import EvidenceChunk


class ContextError(ValueError):
    pass


def eligible_chunks(documents: list[dict[str, Any]], as_of: date, template: str) -> list[dict[str, Any]]:
    chunks = build_corpus(documents, as_of, template)
    validate_corpus(chunks, as_of)
    if len(chunks) != 52:
        raise ContextError(f"frozen eligible chunk count mismatch: {len(chunks)}")
    return chunks


def attach_ranked_evidence(rankings: list[dict[str, Any]], chunks: list[dict[str, Any]], as_of: date | None = None) -> list[EvidenceChunk]:
    by_id = {row["chunk_id"]: row for row in chunks}
    evidence: list[EvidenceChunk] = []
    for index, item in enumerate(rankings, start=1):
        chunk_id = item["chunk_id"]
        if chunk_id not in by_id:
            raise ContextError(f"ranking references non-eligible evidence: {chunk_id}")
        chunk = by_id[chunk_id]
        effective = date.fromisoformat(chunk["effective_date"])
        expiry = date.fromisoformat(chunk["expiry_date"]) if chunk.get("expiry_date") else None
        if chunk["status"] != "APPROVED" or (as_of is not None and (effective > as_of or (expiry is not None and not as_of < expiry))):
            raise ContextError(f"forbidden status entered context: {chunk_id}")
        evidence.append(EvidenceChunk(
            evidence_id=chunk_id, document_id=chunk["document_id"], section_id=chunk["section_id"],
            title=chunk["text"].split("\n", 1)[0], document_type=chunk["document_type"],
            status=chunk["status"], version=chunk["version"], effective_date=chunk["effective_date"],
            expiry_date=chunk.get("expiry_date"), intent_scope=tuple(chunk["intent_scope"]),
            heading=chunk["heading"], content=chunk["content"], score=float(item["score"]), rank=index,
        ))
    return evidence


def render_context(query: str, evidence: list[EvidenceChunk]) -> str:
    blocks = ["<UNTRUSTED_QUERY>", html.escape(query, quote=True), "</UNTRUSTED_QUERY>"]
    for item in evidence:
        blocks.extend([
            f'<EVIDENCE id="{html.escape(item.evidence_id, quote=True)}">',
            f"Title: {html.escape(item.title)}", f"Status: {item.status}", f"Version: {html.escape(item.version)}",
            "Content:", html.escape(item.content), "</EVIDENCE>",
        ])
    return "\n".join(blocks)
