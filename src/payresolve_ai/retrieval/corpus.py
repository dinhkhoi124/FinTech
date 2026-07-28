"""Deterministic eligible-section corpus construction."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable


class CorpusError(ValueError):
    """Raised when the retrieval corpus violates its frozen contract."""


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def eligible(document: dict[str, Any], as_of: date) -> bool:
    effective = date.fromisoformat(document["effective_date"])
    expiry = date.fromisoformat(document["expiry_date"]) if document.get("expiry_date") else None
    return document["status"] == "APPROVED" and effective <= as_of and (expiry is None or as_of < expiry)


def canonical_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    return ("\n".join(json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")) for row in rows) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def build_corpus(documents: list[dict[str, Any]], as_of: date, template: str) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for document in documents:
        if not eligible(document, as_of):
            continue
        for section in document.get("content_sections", []):
            chunk_id = f"{document['document_id']}#{section['section_id']}"
            chunks.append({
                "chunk_id": chunk_id,
                "document_id": document["document_id"],
                "document_family_id": document["document_family_id"],
                "document_type": document["document_type"],
                "intent_scope": list(document["intent_scope"]),
                "intent_slugs": list(document["intent_slugs"]),
                "intent_family": document["intent_family"],
                "product": document["product"],
                "status": document["status"],
                "version": document["version"],
                "effective_date": document["effective_date"],
                "expiry_date": document.get("expiry_date"),
                "risk_level": document["risk_level"],
                "section_id": section["section_id"],
                "heading": section["heading"],
                "content": section["content"],
                "text": template.format(title=document["title"], heading=section["heading"], content=section["content"]),
            })
    chunks.sort(key=lambda row: row["chunk_id"])
    ids = [row["chunk_id"] for row in chunks]
    if len(ids) != len(set(ids)):
        raise CorpusError("duplicate chunk ID")
    return chunks


def validate_corpus(chunks: list[dict[str, Any]], as_of: date) -> None:
    if not chunks:
        raise CorpusError("eligible corpus is empty")
    if [row["chunk_id"] for row in chunks] != sorted(row["chunk_id"] for row in chunks):
        raise CorpusError("corpus order is not deterministic")
    if len({row["chunk_id"] for row in chunks}) != len(chunks):
        raise CorpusError("duplicate chunk ID")
    for row in chunks:
        if row["status"] != "APPROVED":
            raise CorpusError("non-APPROVED chunk entered corpus")
        if date.fromisoformat(row["effective_date"]) > as_of:
            raise CorpusError("future-effective chunk entered corpus")
        if row.get("expiry_date") and not as_of < date.fromisoformat(row["expiry_date"]):
            raise CorpusError("expired chunk entered corpus")
