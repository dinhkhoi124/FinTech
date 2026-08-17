"""Target-aware response planning for the versioned grounded pipeline V3.

The router operates only on the live query and approved/effective evidence.  It
does not consume evaluation labels or gold mappings.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable, Sequence

from .extractive import split_sentences
from .gate import override_requested
from .support_v2 import (
    best_sentence_support,
    canonical_tokens,
    detect_requested_dimension,
    requested_specificity_slots,
)
from .types import EvidenceChunk


class ResponseTarget(str, Enum):
    STANDARD = "STANDARD"
    CORRECTIVE = "CORRECTIVE"
    ABSTAIN = "ABSTAIN"


class RequestedTargetStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    BLOCKED_CONTROL_PLANE = "BLOCKED_CONTROL_PLANE"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class FactualObjective:
    objective: str
    evidence_id: str
    support_quote: str


@dataclass(frozen=True)
class ResponsePlan:
    target: ResponseTarget
    reason_codes: tuple[str, ...]
    requested_target_status: RequestedTargetStatus
    selected_evidence: tuple[EvidenceChunk, ...]
    factual_objectives: tuple[FactualObjective, ...]
    control_plane_boundary: str | None
    corrective_scope_anchor: tuple[str, ...] = ()
    scope_anchor_basis: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["target"] = self.target.value
        value["requested_target_status"] = self.requested_target_status.value
        return value


_PRIVATE_SLOTS = {
    "PRIVATE_INTERNAL_IDENTIFIER",
    "HIDDEN_SYSTEM_INSTRUCTION",
    "AUTHORIZATION_CODE",
    "FIRMWARE_OR_DIAGNOSTIC_CODE",
    "COUNTERPARTY_INTERNAL_REFERENCE",
    "INTERNAL_QUEUE_OR_ROUTE",
    "INTERNAL_RELEASE_IDENTIFIER",
}

_STATE_SCOPE_MARKERS = {
    "pending": ("pending",),
    "declined": ("declined",),
    "failed": ("failed",),
    "reverted": ("reverted", "reversal"),
    "recipient_not_received": ("not_received", "recipient"),
    "unrecognised": ("not_recognised", "unrecognised"),
}

_CONTROL_PLANE_TOKENS = {
    "authorization", "bypass", "code", "diagnostic", "disclose", "exact",
    "firmware", "guarantee", "guaranteed", "hidden", "identifier", "internal",
    "instruction", "matrix", "private", "queue", "reference", "release", "reveal",
    "route", "routing", "threshold",
}

_SAFE_SCOPE_HINTS: tuple[tuple[frozenset[str], frozenset[str]], ...] = (
    (frozenset({"terminal"}), frozenset({"card_payment"})),
    (frozenset({"merchant", "purchase", "shop"}), frozenset({"card_payment"})),
    (frozenset({"atm"}), frozenset({"cash_withdrawal"})),
    (frozenset({"recipient"}), frozenset({"transfer", "recipient"})),
)


def _has_generic_private_target(query: str) -> bool:
    words = set(canonical_tokens(query, {"concepts": {}}, ()))
    return bool(words & {"private", "internal", "hidden"}) and bool(words & {"code", "identifier", "instruction", "route", "reference"})


def _canonical_sentence_coverage(
    query: str,
    item: EvidenceChunk,
    lexicon: dict[str, Any],
    canonical_idf: dict[str, float],
    stopwords: Iterable[str],
) -> float:
    query_tokens = set(canonical_tokens(query, lexicon, stopwords))
    if not query_tokens:
        return 0.0
    fallback = math.log(len(canonical_idf) + 2) + 1
    denominator = math.fsum(canonical_idf.get(token, fallback) for token in sorted(query_tokens)) or 1.0
    best = 0.0
    for sentence in split_sentences(item.content):
        sentence_tokens = set(canonical_tokens(f"{item.heading} {sentence}", lexicon, stopwords))
        overlap = query_tokens & sentence_tokens
        coverage = math.fsum(canonical_idf.get(token, fallback) for token in sorted(overlap)) / denominator
        best = max(best, coverage)
    return best


def derive_corrective_scope_anchor(
    query: str,
    standard_evidence: Sequence[EvidenceChunk],
    lexicon: dict[str, Any],
    stopwords: Iterable[str],
) -> dict[str, Any]:
    """Establish a business scope from non-sensitive query evidence.

    Retrieval order and classifier metadata are diagnostics only.  At least one
    safe query-to-scope signal is required, so a coherent but unrelated top
    result cannot authorize corrective discovery.
    """
    safe_query_tokens = set(canonical_tokens(query, lexicon, stopwords)) - _CONTROL_PLANE_TOKENS
    if not safe_query_tokens or not standard_evidence:
        return {"anchor": (), "basis": (), "reason": "NO_SAFE_CORRECTIVE_SCOPE_ANCHOR"}

    support: dict[tuple[str, ...], dict[str, Any]] = {}
    for item in standard_evidence:
        anchor = tuple(sorted(item.intent_scope))
        scope_tokens = set(canonical_tokens(" ".join(anchor).replace("_", " ").replace("?", ""), lexicon, stopwords))
        direct = safe_query_tokens & scope_tokens
        hints = [
            sorted(query_hint)
            for query_hint, required_scope in _SAFE_SCOPE_HINTS
            if safe_query_tokens & query_hint and required_scope <= scope_tokens
        ]
        if not direct and not hints:
            continue
        row = support.setdefault(anchor, {"evidence_ids": [], "direct": set(), "hints": []})
        row["evidence_ids"].append(item.evidence_id)
        row["direct"].update(direct)
        row["hints"].extend(hints)

    if not support:
        return {"anchor": (), "basis": (), "reason": "NO_SAFE_CORRECTIVE_SCOPE_ANCHOR"}
    ordered = sorted(
        support.items(),
        key=lambda row: (
            -len(row[1]["evidence_ids"]),
            -len(row[1]["direct"]),
            row[0],
        ),
    )
    winner_anchor, winner = ordered[0]
    if len(ordered) > 1:
        runner = ordered[1][1]
        if (len(winner["evidence_ids"]), len(winner["direct"])) == (
            len(runner["evidence_ids"]), len(runner["direct"])
        ):
            return {"anchor": (), "basis": (), "reason": "AMBIGUOUS_CORRECTIVE_SCOPE_ANCHOR"}
    basis = tuple(
        [f"QUERY_SCOPE_TOKEN:{token}" for token in sorted(winner["direct"])]
        + [f"SAFE_SCOPE_HINT:{'+'.join(hint)}" for hint in sorted({tuple(value) for value in winner["hints"]})]
        + [f"EVIDENCE_SCOPE:{evidence_id}" for evidence_id in winner["evidence_ids"]]
    )
    return {"anchor": winner_anchor, "basis": basis, "reason": "SAFE_CORRECTIVE_SCOPE_ANCHOR"}


def assess_requested_target(
    query: str,
    standard_evidence: Sequence[EvidenceChunk],
    lexicon: dict[str, Any],
    canonical_idf: dict[str, float],
    stopwords: Iterable[str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    """Assess the requested target before any permissive utility policy applies."""
    slots = requested_specificity_slots(query)
    slot_names = {row["slot"] for row in slots}
    if override_requested(query):
        return {"status": RequestedTargetStatus.BLOCKED_CONTROL_PLANE, "reason": "UNTRUSTED_OVERRIDE_REQUEST", "dimension": detect_requested_dimension(query)}
    if slot_names & _PRIVATE_SLOTS or _has_generic_private_target(query):
        return {"status": RequestedTargetStatus.BLOCKED_CONTROL_PLANE, "reason": "PRIVATE_OR_INTERNAL_TARGET_BLOCKED", "dimension": detect_requested_dimension(query)}
    if not standard_evidence:
        return {"status": RequestedTargetStatus.UNSUPPORTED, "reason": "NO_ELIGIBLE_EVIDENCE", "dimension": detect_requested_dimension(query)}

    query_concepts = set(canonical_tokens(query, lexicon, stopwords))
    top_scope = " ".join(standard_evidence[0].intent_scope).casefold()
    conflicting_states = [
        concept for concept, markers in _STATE_SCOPE_MARKERS.items()
        if concept in query_concepts and not any(marker in top_scope for marker in markers)
    ]
    if conflicting_states:
        return {
            "status": RequestedTargetStatus.UNSUPPORTED,
            "reason": "EVIDENCE_TARGET_STATE_CONFLICT",
            "dimension": detect_requested_dimension(query),
            "conflicting_states": conflicting_states,
        }

    dimension = detect_requested_dimension(query)
    coverages = [
        _canonical_sentence_coverage(query, item, lexicon, canonical_idf, stopwords)
        for item in standard_evidence
    ]
    relevant = [index for index, coverage in enumerate(coverages) if coverage >= policy["min_support_coverage"]]
    competing = False
    if len(standard_evidence) >= 2 and len(relevant) >= 2:
        first, second = standard_evidence[relevant[0]], standard_evidence[relevant[1]]
        competing = (
            not set(first.intent_scope) & set(second.intent_scope)
            and first.score - second.score < policy["ambiguity_score_gap"]
        )
    if competing:
        return {"status": RequestedTargetStatus.UNSUPPORTED, "reason": "AMBIGUOUS_COMPETING_TARGETS", "dimension": dimension, "direct_coverages": coverages}

    if any(name not in _PRIVATE_SLOTS for name in slot_names):
        evidence_text = " ".join(f"{item.heading} {item.content}" for item in standard_evidence).casefold()
        unsupported_slots = [
            row["slot"] for row in slots
            if row["matched_query_phrase"].casefold() not in evidence_text
        ]
        if unsupported_slots:
            return {"status": RequestedTargetStatus.BLOCKED_CONTROL_PLANE, "reason": "UNSUPPORTED_EXACT_OR_SPECIFIC_TARGET", "dimension": dimension, "unsupported_slots": unsupported_slots}

    if standard_evidence[0].score < policy["min_top1_score"]:
        return {"status": RequestedTargetStatus.UNSUPPORTED, "reason": "LOW_RETRIEVAL_SUPPORT", "dimension": dimension, "direct_coverages": coverages}

    if dimension["dimension"] == "UNKNOWN":
        supported = max(coverages, default=0.0) >= policy["min_support_coverage"]
        reason = "DIRECT_CANONICAL_SUPPORT" if supported else "LOW_DIRECT_CANONICAL_SUPPORT"
        support_evidence_ids = [
            item.evidence_id for item, coverage in zip(standard_evidence, coverages, strict=True)
            if coverage >= policy["min_support_coverage"]
        ]
    else:
        support = best_sentence_support(
            query,
            standard_evidence,
            str(dimension["dimension"]),
            lexicon,
            canonical_idf,
            stopwords,
        )
        supported = bool(support["dimension_match"]) and support["best_sentence_support_coverage"] >= policy["min_support_coverage"]
        reason = "DIMENSION_AWARE_SUPPORT" if supported else "REQUESTED_DIMENSION_NOT_SUPPORTED"
        fallback_evidence_id = support["best_evidence_id"]
        fallback_coverage = float(support["best_sentence_support_coverage"])
        actionable_checks_only = (
            not support["dimension_match"]
            and dimension["dimension"] == "NEXT_ACTION"
            and any(
                coverage > 0.0
                and re.search(r"\b(?:check|confirm|review|inspect)\b", f"{item.heading} {item.content}", re.IGNORECASE)
                for item, coverage in zip(standard_evidence, coverages, strict=True)
            )
        )
        if not supported and support["dimension_match"] and fallback_evidence_id and fallback_coverage > 0.0:
            top_scope = set(standard_evidence[0].intent_scope)
            coherent_top = len(standard_evidence) >= 2 and bool(top_scope & set(standard_evidence[1].intent_scope))
            close_competitor = any(
                not top_scope & set(item.intent_scope)
                and standard_evidence[0].score - item.score < policy["ambiguity_score_gap"]
                for item in standard_evidence[1:]
            )
            support_in_scope = any(
                item.evidence_id == fallback_evidence_id and bool(top_scope & set(item.intent_scope))
                for item in standard_evidence
            )
            if coherent_top and support_in_scope and not close_competitor:
                supported = True
                reason = "COHERENT_DIRECT_DIMENSION_FALLBACK"
        if not supported and actionable_checks_only:
            reason = "NEXT_ACTION_DIRECT_ACTION_REQUIRED"
        if supported and dimension["dimension"] == "TIMING_WINDOW":
            authority_found = any(
                item.document_type.casefold() in {"policy", "faq"}
                and re.search(
                    r"\b(?:day|days|hour|hours|window|before|after|timing)\b",
                    f"{item.heading} {item.content}", re.IGNORECASE,
                )
                and best_sentence_support(query, [item], "TIMING_WINDOW", lexicon, canonical_idf, stopwords)["best_sentence_support_coverage"] > 0.0
                for item in standard_evidence
            )
            if not authority_found:
                supported = False
                reason = "TIMING_POLICY_AUTHORITY_REQUIRED"
        support_evidence_ids = [fallback_evidence_id] if supported and fallback_evidence_id else []
    return {
        "status": RequestedTargetStatus.SUPPORTED if supported else RequestedTargetStatus.UNSUPPORTED,
        "reason": reason,
        "dimension": dimension,
        "direct_coverages": coverages,
        "support_evidence_ids": support_evidence_ids,
    }


def select_supported_standard_evidence(
    query: str,
    candidate_pool: Sequence[EvidenceChunk],
    lexicon: dict[str, Any],
    canonical_idf: dict[str, float],
    stopwords: Iterable[str],
    policy: dict[str, Any],
) -> tuple[EvidenceChunk, ...]:
    """Select a bounded target-supporting subset from the runtime pool."""
    if not candidate_pool:
        return ()
    dominant_scope = set(candidate_pool[0].intent_scope)
    coherent = [item for item in candidate_pool if dominant_scope & set(item.intent_scope)]
    dimension = detect_requested_dimension(query)["dimension"]
    scored: list[tuple[float, float, int, str, EvidenceChunk]] = []
    for item in coherent:
        if dimension == "UNKNOWN":
            coverage = _canonical_sentence_coverage(query, item, lexicon, canonical_idf, stopwords)
            matched = coverage >= policy["min_support_coverage"]
        else:
            support = best_sentence_support(query, [item], str(dimension), lexicon, canonical_idf, stopwords)
            coverage = float(support["best_sentence_support_coverage"])
            matched = bool(support["dimension_match"])
        if matched:
            scored.append((-coverage, -item.score, item.rank, item.evidence_id, item))
    scored.sort()
    return tuple(row[-1] for row in scored[: policy["max_evidence"]])
