"""Deterministic canonical support, dimension, and specificity checks for gate v2."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Any, Iterable, Sequence

from .extractive import split_sentences
from .gate import ambiguity_detected, override_requested, weighted_coverage
from .types import EvidenceChunk


DIMENSION_RULE_VERSION = "requested_dimension_rules_v2"


def _normalized_words(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return re.findall(r"[a-z0-9]+", normalized)


def _phrase_table(lexicon: dict[str, Any]) -> list[tuple[tuple[str, ...], str]]:
    rows: list[tuple[tuple[str, ...], str]] = []
    for concept, phrases in lexicon["concepts"].items():
        for phrase in phrases:
            words = tuple(_normalized_words(phrase))
            if not words:
                raise ValueError(f"empty lexicon phrase for {concept}")
            rows.append((words, concept))
    rows.sort(key=lambda row: (-len(row[0]), -sum(len(word) for word in row[0]), row[0], row[1]))
    if len({phrase for phrase, _ in rows}) != len(rows):
        raise ValueError("lexicon phrase maps to multiple concepts")
    return rows


def canonical_tokens(text: str, lexicon: dict[str, Any], stopwords: Iterable[str]) -> list[str]:
    words = _normalized_words(text)
    phrases = _phrase_table(lexicon)
    stop = set(stopwords)
    output: list[str] = []
    index = 0
    while index < len(words):
        match = next(((phrase, concept) for phrase, concept in phrases if tuple(words[index:index + len(phrase)]) == phrase), None)
        if match is None:
            if words[index] not in stop:
                output.append(words[index])
            index += 1
        else:
            output.append(match[1])
            index += len(match[0])
    return output


def canonicalize_text(text: str, lexicon: dict[str, Any], stopwords: Iterable[str] = ()) -> str:
    return " ".join(canonical_tokens(text, lexicon, stopwords))


DIMENSION_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("SPECIFIC_INTERNAL_DETAIL", (
        r"\b(?:internal|routing|queue|authorization|firmware|diagnostic|counterparty)\b.{0,35}\b(?:code|identifier|reference|route)\b",
        r"\b(?:rapid-release|release)\b.{0,20}\bidentifier\b",
        r"\b(?:priority|retired|general atm support)\b.{0,25}\broute\b",
        r"\b(?:hidden|system)\b.{0,20}\binstruction",
    )),
    ("EXACT_AMOUNT_OR_THRESHOLD", (
        r"\bexact\b.{0,30}\b(?:amount|threshold)\b",
        r"\bcompensation amount\b", r"\bapproval matrix\b", r"\bsalary threshold\b",
        r"\bguarante(?:e|ed)\b.{0,25}\b(?:amount|threshold|entitlement)\b",
    )),
    ("ESCALATION_OR_SECURITY", (r"\bescalat(?:e|ion)\b", r"\bsecurity\b", r"\bspecialist review\b", r"\bsafe handoff\b")),
    ("TIMING_WINDOW", (r"\bwhen\b", r"\bhow long\b", r"\bat what point\b", r"\bimmediate release\b", r"\b(?:day|days|hour|hours|window|deadline)\b")),
    ("RETRY", (r"\bretry\b", r"\btry again\b", r"\bresubmit\b", r"\bfurther attempt\b", r"\bonce more\b")),
    ("CHECKS", (r"\bcheck(?:s|ed|ing)?\b", r"\bconfirm\b", r"\bverify\b", r"\bnon-sensitive\b")),
    ("NEXT_ACTION", (r"\bwhat should (?:i|be) do(?:ne)?\b", r"\bwhat can i do\b", r"\bwhat happens next\b", r"\bwhat should i expect\b", r"\bwhat next\b", r"\brecipient-tracing result\b", r"\bhandle\b", r"\baction\b", r"\bdo now\b")),
    ("STATE_OR_MEANING", (r"\bwhat does (?:this|that)\b.{0,45}\bmean\b", r"\bmeaning\b", r"\bwhat state\b")),
    ("ELIGIBILITY", (r"\beligib(?:le|ility)\b", r"\bqualif(?:y|ies|ication)\b")),
)


def detect_requested_dimensions(text: str) -> tuple[dict[str, str | None], ...]:
    """Return every explicit requested dimension in deterministic rule order."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    matches: list[dict[str, str | None]] = []
    for dimension, patterns in DIMENSION_PATTERNS:
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                matches.append({
                    "dimension": dimension,
                    "matched_phrase": match.group(0),
                    "rule_version": DIMENSION_RULE_VERSION,
                })
                break
    return tuple(matches)


def detect_requested_dimension(text: str) -> dict[str, str | None]:
    """Compatibility view for callers that consume one primary dimension."""
    matches = detect_requested_dimensions(text)
    if matches:
        return matches[0]
    return {"dimension": "UNKNOWN", "matched_phrase": None, "rule_version": DIMENSION_RULE_VERSION}


SPECIFICITY_PATTERNS: tuple[tuple[str, str], ...] = (
    ("HIDDEN_SYSTEM_INSTRUCTION", r"\b(?:hidden|system)\b.{0,20}\binstruction"),
    ("AUTHORIZATION_CODE", r"\bauthorization\b.{0,20}\bcode\b"),
    ("FIRMWARE_OR_DIAGNOSTIC_CODE", r"\b(?:firmware|diagnostic|device)\b.{0,25}\b(?:code|identifier)\b"),
    ("COUNTERPARTY_INTERNAL_REFERENCE", r"\b(?:counterparty|other institution|recipient bank)\b.{0,30}\b(?:internal|trace)\b.{0,20}\breference\b"),
    ("INTERNAL_QUEUE_OR_ROUTE", r"\b(?:internal queue|routing code|queue code|priority route|retired general atm support route|legacy routing code)\b"),
    ("INTERNAL_RELEASE_IDENTIFIER", r"\b(?:rapid-release|release)\b.{0,20}\bidentifier\b"),
    ("EXACT_COMPENSATION_AMOUNT", r"\b(?:exact )?compensation amount\b"),
    ("EXACT_APPROVAL_THRESHOLD", r"\bexact approval threshold\b"),
    ("SALARY_THRESHOLD", r"\bsalary threshold\b"),
    ("APPROVAL_MATRIX", r"\bapproval matrix\b"),
    ("GUARANTEED_ENTITLEMENT", r"\bguarante(?:e|ed|es)\b.{0,45}\b(?:credit|release|review|entitlement|accepted|amount)\b"),
    ("ACCOUNT_SPECIFIC_OUTCOME", r"(?:\b(?:will|does|can)\b.{0,35}\b(?:my|this)\b.{0,15}\b(?:account|case|claim|transaction)\b.{0,35}\b(?:receive|qualify|approved|accepted|credit|refund|release)\b|\b(?:my|this)\b.{0,15}\b(?:account|case|claim|transaction)\b.{0,35}\b(?:will|does|can|receive|qualify|approved|accepted|credit|refund|release)\b)"),
    ("PROHIBITED_PROCESS_ACTION", r"\b(?:conceal|delete|erase|falsify|alter)\b.{0,35}\b(?:audit|record|history|evidence|status|decision)\b"),
)


def requested_specificity_slots(query: str) -> list[dict[str, str]]:
    normalized = unicodedata.normalize("NFKC", query).casefold()
    slots = []
    for slot, pattern in SPECIFICITY_PATTERNS:
        match = re.search(pattern, normalized)
        if match:
            slots.append({"slot": slot, "matched_query_phrase": match.group(0)})
    return slots


def specificity_guard(query: str, evidence: Sequence[EvidenceChunk]) -> dict[str, Any]:
    slots = requested_specificity_slots(query)
    searched = [item.evidence_id for item in evidence[:3]]
    if not slots:
        return {"triggered": False, "requested_slots": [], "matched_query_phrases": [], "evidence_searched": searched, "support_found": False}
    evidence_text = " ".join(f"{item.heading} {item.content}" for item in evidence[:3]).casefold()
    supported_slots = []
    for row in slots:
        pattern = dict(SPECIFICITY_PATTERNS)[row["slot"]]
        if re.search(pattern, evidence_text):
            supported_slots.append(row["slot"])
    unsupported = [row for row in slots if row["slot"] not in supported_slots]
    return {
        "triggered": bool(unsupported),
        "requested_slots": [row["slot"] for row in slots],
        "matched_query_phrases": [row["matched_query_phrase"] for row in slots],
        "evidence_searched": searched,
        "support_found": not unsupported,
        "supported_slots": supported_slots,
    }


def _sentence_matches_dimension(text: str, dimension: str) -> bool:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    detected = {row["dimension"] for row in detect_requested_dimensions(normalized)}
    if dimension in detected:
        return True
    broad = {
        "STATE_OR_MEANING": r"\b(?:is|means|state|applies|accepted|terminal|open|recognized|recognised)\b",
        "CHECKS": r"\b(?:check|checks|confirm|verify|recognize|recognise|separate|exclude)\b",
        "NEXT_ACTION": r"\b(?:action|do not|avoid|prevent|route|use|provide|suggest|explain|follow|review|collect|record|send|apply)\b",
        "TIMING_WINDOW": r"\b(?:day|days|hour|hours|window|before|after|when|timing)\b",
        "RETRY": r"\b(?:retry|attempts?|resubmit|duplicate)\b",
        "ESCALATION_OR_SECURITY": r"\b(?:escalate|escalation|security|handoff|route)\b",
        "ELIGIBILITY": r"\b(?:eligibility|eligible|apply only|requires?)\b",
        "SPECIFIC_INTERNAL_DETAIL": r"\b(?:code|identifier|reference|route|instruction)\b",
        "EXACT_AMOUNT_OR_THRESHOLD": r"\b(?:amount|threshold|matrix|compensation)\b",
    }
    return bool(re.search(broad.get(dimension, r"(?!)"), normalized))


def build_canonical_idf(chunks: list[dict[str, Any]], lexicon: dict[str, Any], stopwords: Iterable[str]) -> dict[str, float]:
    documents = [set(canonical_tokens(row["text"], lexicon, stopwords)) for row in chunks]
    frequencies = Counter(token for document in documents for token in document)
    total = len(documents)
    return {token: math.log((total + 1) / (frequency + 1)) + 1 for token, frequency in sorted(frequencies.items())}


def best_sentence_support(
    query: str,
    evidence: Sequence[EvidenceChunk],
    dimension: str,
    lexicon: dict[str, Any],
    canonical_idf: dict[str, float],
    stopwords: Iterable[str],
    *,
    require_sentence_dimension_match: bool = False,
) -> dict[str, Any]:
    query_tokens = set(canonical_tokens(query, lexicon, stopwords))
    fallback = math.log(len(canonical_idf) + 2) + 1
    denominator = math.fsum(canonical_idf.get(token, fallback) for token in sorted(query_tokens)) or 1.0
    diagnostics = []
    for item in evidence[:3]:
        for sentence in split_sentences(item.content):
            dimension_text = sentence if require_sentence_dimension_match else f"{item.heading} {sentence}"
            dimension_match = _sentence_matches_dimension(dimension_text, dimension)
            sentence_tokens = set(canonical_tokens(dimension_text, lexicon, stopwords))
            overlap = query_tokens & sentence_tokens
            coverage = math.fsum(canonical_idf.get(token, fallback) for token in sorted(overlap)) / denominator if dimension_match else 0.0
            diagnostics.append({"evidence_id": item.evidence_id, "sentence": sentence, "dimension_match": dimension_match, "coverage": coverage, "matched_canonical_tokens": sorted(overlap)})
    matched = [row for row in diagnostics if row["dimension_match"]]
    best = max(matched, key=lambda row: (row["coverage"], -next(item.rank for item in evidence if item.evidence_id == row["evidence_id"]), row["evidence_id"], row["sentence"]), default=None)
    return {
        "dimension_match": best is not None,
        "best_sentence_support_coverage": best["coverage"] if best else 0.0,
        "best_evidence_id": best["evidence_id"] if best else None,
        "best_sentence": best["sentence"] if best else None,
        "sentence_diagnostics": diagnostics,
    }


def decide_gate_v2(
    query: str,
    evidence: list[EvidenceChunk],
    raw_idf: dict[str, float],
    canonical_idf: dict[str, float],
    stopwords: Iterable[str],
    lexicon: dict[str, Any],
    candidate: dict[str, float],
    *,
    extractable: bool,
    mode: str = "EVIDENCE_GATED",
) -> dict[str, Any]:
    top1 = evidence[0].score if evidence else None
    dimension = detect_requested_dimension(query)
    specificity = specificity_guard(query, evidence)
    support = best_sentence_support(query, evidence, str(dimension["dimension"]), lexicon, canonical_idf, stopwords) if evidence and dimension["dimension"] != "UNKNOWN" else {"dimension_match": False, "best_sentence_support_coverage": 0.0, "best_evidence_id": None, "best_sentence": None, "sentence_diagnostics": []}
    override = override_requested(query)
    ambiguous = ambiguity_detected(evidence, candidate["ambiguity_score_gap"]) if evidence else False
    reason = "SUFFICIENT_APPROVED_EVIDENCE"
    decision = "PASS"
    if override:
        decision, reason = "FAIL", "UNTRUSTED_OVERRIDE_REQUEST"
    elif not evidence:
        decision, reason = "FAIL", "NO_ELIGIBLE_EVIDENCE"
    elif mode != "ALWAYS_ANSWER" and ambiguous:
        decision, reason = "FAIL", "AMBIGUOUS_EVIDENCE"
    elif mode != "ALWAYS_ANSWER" and specificity["triggered"]:
        decision, reason = "FAIL", "UNSUPPORTED_REQUESTED_DETAIL"
    elif mode != "ALWAYS_ANSWER" and (top1 is None or top1 < candidate["min_top1_score"]):
        decision, reason = "FAIL", "LOW_RETRIEVAL_SUPPORT"
    elif mode != "ALWAYS_ANSWER" and dimension["dimension"] == "UNKNOWN":
        decision, reason = "FAIL", "UNKNOWN_REQUESTED_DIMENSION"
    elif mode != "ALWAYS_ANSWER" and not support["dimension_match"]:
        decision, reason = "FAIL", "REQUESTED_DIMENSION_NOT_SUPPORTED"
    elif mode != "ALWAYS_ANSWER" and support["best_sentence_support_coverage"] < candidate["min_best_sentence_support_coverage"]:
        decision, reason = "FAIL", "LOW_CANONICAL_SENTENCE_SUPPORT"
    elif not extractable:
        decision, reason = "FAIL", "NO_VALID_EXTRACTIVE_CLAIM"
    return {
        "decision": decision,
        "reason_code": reason,
        "mode": mode,
        "top1_score": top1,
        "weighted_query_coverage_v1_diagnostic": weighted_coverage(query, evidence, raw_idf, stopwords) if evidence else 0.0,
        "requested_dimension": dimension,
        "dimension_match": support["dimension_match"],
        "best_sentence_support_coverage": support["best_sentence_support_coverage"],
        "best_support_evidence_id": support["best_evidence_id"],
        "best_support_sentence": support["best_sentence"],
        "sentence_support_diagnostics": support["sentence_diagnostics"],
        "specificity_guard": specificity,
        "intent_ambiguity_detected": ambiguous,
        "override_request_detected": override,
    }
