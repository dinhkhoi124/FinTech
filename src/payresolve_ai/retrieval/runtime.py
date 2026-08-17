"""Bounded offline corrective discovery without changing the W2 benchmark."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable, Mapping, Sequence


def _tokens(text: str, stopwords: Iterable[str]) -> set[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    stop = set(stopwords)
    return {token for token in re.findall(r"[a-z0-9]+", normalized) if token not in stop}


def expand_runtime_candidate_pools(
    queries: list[dict[str, Any]],
    tracked_rankings: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    max_candidates: int,
    stopwords: Iterable[str],
    *,
    max_scanned_chunks: int,
) -> list[dict[str, Any]]:
    """Preserve tracked top results and add bounded lexical discovery candidates."""
    if max_candidates < 1 or max_scanned_chunks < max_candidates:
        raise ValueError("invalid runtime retrieval bounds")
    if len(chunks) > max_scanned_chunks:
        raise ValueError("runtime corpus exceeds configured bounded scan")
    ranked_by_id = {row["query_id"]: row["rankings"] for row in tracked_rankings}
    chunk_by_id = {row["chunk_id"]: row for row in chunks}
    output: list[dict[str, Any]] = []
    for query in queries:
        existing = list(ranked_by_id[query["query_id"]])
        used = {row["chunk_id"] for row in existing}
        dominant_scope = set(chunk_by_id[existing[0]["chunk_id"]]["intent_scope"]) if existing else set()
        query_tokens = _tokens(query["query_text"], stopwords)
        supplements: list[tuple[int, float, str]] = []
        for chunk in chunks:
            if chunk["chunk_id"] in used:
                continue
            chunk_tokens = _tokens(chunk["text"], stopwords)
            coverage = len(query_tokens & chunk_tokens) / len(query_tokens) if query_tokens else 0.0
            if coverage > 0.0:
                same_scope = bool(dominant_scope & set(chunk["intent_scope"]))
                supplements.append((-int(same_scope), -coverage, chunk["chunk_id"]))
        supplements.sort()
        floor = float(existing[-1]["score"]) if existing else 0.0
        for index, (_, _, chunk_id) in enumerate(supplements, start=1):
            if len(existing) == max_candidates:
                break
            existing.append({"chunk_id": chunk_id, "score": floor - index * 1e-6})
        output.append({"query_id": query["query_id"], "rankings": existing[:max_candidates]})
    return output


def discover_corrective_candidates(
    blocked_reason: str,
    scope_anchor: Sequence[str],
    generic_obligations: Sequence[Sequence[str]],
    standard_rankings: Sequence[dict[str, Any]],
    eligible_corpus: Sequence[dict[str, Any]],
    objective_categories: Mapping[str, Sequence[str]],
    max_candidates: int,
    *,
    max_scanned_chunks: int,
) -> list[dict[str, Any]]:
    """Discover a deterministic corrective pool without query-overlap admission.

    The blocked request text is intentionally absent from this API.  Admission
    requires the independently established safe scope anchor; objective
    coverage then ranks candidates ahead of stable source order and chunk ID.
    """
    if not blocked_reason or not scope_anchor:
        return []
    if max_candidates < 1 or max_scanned_chunks < max_candidates:
        raise ValueError("invalid corrective discovery bounds")
    if len(eligible_corpus) > max_scanned_chunks:
        raise ValueError("runtime corpus exceeds configured bounded scan")

    anchor = set(scope_anchor)
    source_order = {row["chunk_id"]: index for index, row in enumerate(standard_rankings)}
    source_score = {row["chunk_id"]: float(row["score"]) for row in standard_rankings}
    default_order = len(source_order)
    ranked: list[tuple[int, int, int, str, dict[str, Any]]] = []
    for corpus_index, chunk in enumerate(eligible_corpus):
        if not anchor & set(chunk["intent_scope"]):
            continue
        categories = set(objective_categories.get(chunk["chunk_id"], ()))
        mandatory_hits = sum(bool(categories & set(group)) for group in generic_obligations)
        mandatory_categories = {category for group in generic_obligations for category in group}
        optional_hits = len(categories - mandatory_categories)
        order = source_order.get(chunk["chunk_id"], default_order + corpus_index)
        ranked.append((-mandatory_hits, -optional_hits, order, chunk["chunk_id"], chunk))
    ranked.sort(key=lambda row: row[:4])

    floor = min(source_score.values(), default=0.0)
    result: list[dict[str, Any]] = []
    for index, (_, _, _, chunk_id, _) in enumerate(ranked[:max_candidates], start=1):
        result.append({"chunk_id": chunk_id, "score": source_score.get(chunk_id, floor - index * 1e-6)})
    return result
