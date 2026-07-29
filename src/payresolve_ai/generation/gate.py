"""Deterministic IDF coverage and evidence sufficiency gate."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Any, Iterable

from .types import EvidenceChunk


OVERRIDE_PATTERNS = (
    r"\bignore\b.{0,30}\b(policy|approved|instruction)",
    r"\bbypass\b.{0,30}\b(policy|approval|evidence|citation)",
    r"\b(use|show)\b.{0,20}\b(draft|expired)\b",
    r"\b(fabricate|guess|make up)\b",
    r"\b(omit|without|remove)\b.{0,20}\bcitation",
    r"\b(reveal|show)\b.{0,20}\b(hidden|system)\b.{0,20}\binstruction",
    r"\boverride\b.{0,20}\b(approved|evidence|policy)",
)


def tokenize(text: str, stopwords: Iterable[str]) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    stop = set(stopwords)
    return [token for token in re.findall(r"[a-z0-9]+", normalized) if token not in stop]


def build_idf(chunks: list[dict[str, Any]], stopwords: Iterable[str]) -> dict[str, float]:
    # The frozen retrieval unit is title + heading + content, not content alone.
    documents = [set(tokenize(row["text"], stopwords)) for row in chunks]
    frequencies = Counter(token for document in documents for token in document)
    total = len(documents)
    return {token: math.log((total + 1) / (frequency + 1)) + 1 for token, frequency in sorted(frequencies.items())}


def weighted_coverage(query: str, evidence: list[EvidenceChunk], idf: dict[str, float], stopwords: Iterable[str]) -> float:
    query_tokens = set(tokenize(query, stopwords))
    if not query_tokens:
        return 0.0
    evidence_tokens = set(tokenize(" ".join(f"{item.title} {item.heading} {item.content}" for item in evidence), stopwords))
    fallback = math.log(len(idf) + 2) + 1
    denominator = math.fsum(idf.get(token, fallback) for token in sorted(query_tokens))
    numerator = math.fsum(idf.get(token, fallback) for token in sorted(query_tokens & evidence_tokens))
    return numerator / denominator


def override_requested(query: str) -> bool:
    normalized = unicodedata.normalize("NFKC", query).casefold()
    return any(re.search(pattern, normalized) for pattern in OVERRIDE_PATTERNS)


def ambiguity_detected(evidence: list[EvidenceChunk], gap: float) -> bool:
    if len(evidence) < 2:
        return False
    return not set(evidence[0].intent_scope) & set(evidence[1].intent_scope) and evidence[0].score - evidence[1].score < gap


def decide_gate(
    query: str,
    evidence: list[EvidenceChunk],
    idf: dict[str, float],
    stopwords: Iterable[str],
    candidate: dict[str, float],
    *,
    extractable: bool,
    mode: str = "EVIDENCE_GATED",
) -> dict[str, Any]:
    top1 = evidence[0].score if evidence else None
    coverage = weighted_coverage(query, evidence, idf, stopwords) if evidence else 0.0
    override = override_requested(query)
    ambiguous = ambiguity_detected(evidence, candidate["ambiguity_score_gap"]) if evidence else False
    reason = "SUFFICIENT_APPROVED_EVIDENCE"
    decision = "PASS"
    if override:
        decision, reason = "FAIL", "UNTRUSTED_OVERRIDE_REQUEST"
    elif not evidence:
        decision, reason = "FAIL", "NO_ELIGIBLE_EVIDENCE"
    elif not extractable:
        decision, reason = "FAIL", "NO_VALID_EXTRACTIVE_CLAIM"
    elif mode != "ALWAYS_ANSWER" and ambiguous:
        decision, reason = "FAIL", "AMBIGUOUS_EVIDENCE"
    elif mode != "ALWAYS_ANSWER" and top1 < candidate["min_top1_score"]:
        decision, reason = "FAIL", "LOW_RETRIEVAL_SUPPORT"
    elif mode != "ALWAYS_ANSWER" and coverage < candidate["min_weighted_query_coverage"]:
        decision, reason = "FAIL", "LOW_QUERY_EVIDENCE_COVERAGE"
    return {
        "decision": decision, "reason_code": reason, "top1_score": top1,
        "weighted_query_coverage": coverage, "intent_ambiguity_detected": ambiguous,
        "override_request_detected": override,
    }
