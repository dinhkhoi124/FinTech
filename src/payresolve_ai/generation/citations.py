"""Fail-closed exact-quote claim and citation verification."""

from __future__ import annotations

from datetime import date
from typing import Any

from .types import EvidenceChunk, GenerationDraft


class CitationError(ValueError):
    pass


CITATION_FIELDS = {
    "citation_id", "evidence_id", "document_id", "section_id", "title",
    "document_type", "status", "version",
}


def render_answer(claims: list[dict[str, Any]]) -> str:
    return " ".join(
        f"{claim['text']} {' '.join(f'[{alias}]' for alias in claim['citation_ids'])}"
        for claim in claims
    )


def verify_draft(draft: GenerationDraft, selected: list[EvidenceChunk], as_of: date) -> str:
    selected_by_id = {item.evidence_id: item for item in selected}
    aliases: list[str] = []
    citation_evidence_ids: list[str] = []
    for citation in draft.citations:
        if set(citation) != CITATION_FIELDS:
            raise CitationError("citation-metadata-mismatch")
        alias = citation.get("citation_id")
        evidence_id = citation.get("evidence_id")
        if not isinstance(alias, str) or not alias.strip():
            raise CitationError("citation-id-invalid")
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            raise CitationError("citation-evidence-id-invalid")
        aliases.append(alias)
        citation_evidence_ids.append(evidence_id)
    if len(aliases) != len(set(aliases)):
        raise CitationError("duplicate citation alias")
    if len(citation_evidence_ids) != len(set(citation_evidence_ids)):
        raise CitationError("duplicate citation evidence ID")
    citation_by_alias = {row["citation_id"]: row for row in draft.citations}
    used: set[str] = set()
    if not draft.claims:
        raise CitationError("empty claim set")
    claim_ids: list[str] = []
    for claim in draft.claims:
        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id.strip():
            raise CitationError("claim-id-invalid")
        claim_ids.append(claim_id)
        if not isinstance(claim.get("text"), str) or not claim["text"].strip():
            raise CitationError("claim text must be non-empty string")
        evidence_ids = claim.get("evidence_ids", [])
        quotes = claim.get("support_quotes", [])
        claim_aliases = claim.get("citation_ids", [])
        if not isinstance(evidence_ids, list) or not evidence_ids or not all(isinstance(value, str) and value.strip() for value in evidence_ids):
            raise CitationError("claim-evidence-id-invalid")
        if not isinstance(quotes, list) or not quotes or not all(isinstance(value, str) and value for value in quotes):
            raise CitationError("claim-support-quote-invalid")
        if not isinstance(claim_aliases, list) or not claim_aliases or not all(isinstance(value, str) and value.strip() for value in claim_aliases):
            raise CitationError("claim-citation-id-invalid")
        if not len(evidence_ids) == len(quotes) == len(claim_aliases):
            raise CitationError("claim-evidence-quote-alias-length-mismatch")
        for evidence_id, quote, alias in zip(evidence_ids, quotes, claim_aliases, strict=True):
            if "#" not in evidence_id or evidence_id not in selected_by_id:
                raise CitationError("citation references unselected evidence")
            item = selected_by_id[evidence_id]
            if item.status != "APPROVED" or date.fromisoformat(item.effective_date) > as_of or (item.expiry_date and not as_of < date.fromisoformat(item.expiry_date)):
                raise CitationError("citation references ineligible evidence")
            if not isinstance(quote, str) or quote not in item.content or claim["text"] != quote:
                raise CitationError("support quote is not exact extractive evidence")
            if alias not in citation_by_alias or citation_by_alias[alias]["evidence_id"] != evidence_id:
                raise CitationError("citation alias does not resolve to claim evidence")
            citation = citation_by_alias[alias]
            if citation["document_id"] != item.document_id:
                raise CitationError("citation-document-mismatch")
            if citation["section_id"] != item.section_id:
                raise CitationError("citation-section-mismatch")
            if citation["title"] != item.title or citation["document_type"] != item.document_type:
                raise CitationError("citation-metadata-mismatch")
            if citation["status"] != item.status:
                raise CitationError("citation-status-mismatch")
            if citation["version"] != item.version:
                raise CitationError("citation-version-mismatch")
            used.add(alias)
    if len(claim_ids) != len(set(claim_ids)):
        raise CitationError("duplicate claim ID")
    if used != set(aliases):
        raise CitationError("unused citation")
    return render_answer(draft.claims)
