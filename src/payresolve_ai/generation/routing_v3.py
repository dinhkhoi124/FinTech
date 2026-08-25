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
    detect_requested_dimensions,
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
class FallbackSupportAuthorization:
    evidence_id: str
    support_quote: str
    dimension: str
    coverage: float
    reason: str


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

_UNKNOWN_TRANSACTION_STATE_PATTERN = re.compile(
    r"\b(?:transaction|transfer|payment|withdrawal)\b.{0,24}\b(?:suspended|frozen|cancelled|canceled|quarantined)\b"
    r"|\b(?:suspended|frozen|cancelled|canceled|quarantined)\b.{0,24}\b(?:transaction|transfer|payment|withdrawal)\b",
    re.IGNORECASE,
)

_CONTROL_PLANE_TOKENS = {
    "authorization", "bypass", "code", "diagnostic", "disclose", "exact",
    "firmware", "guarantee", "guaranteed", "hidden", "identifier", "internal",
    "instruction", "matrix", "private", "queue", "reference", "release", "reveal",
    "route", "routing", "threshold",
}

_FALLBACK_GENERIC_OVERLAP_TOKENS = {"checks", "action", "retry", "timing", "not"}

_SAFE_SCOPE_HINTS: tuple[tuple[frozenset[str], frozenset[str]], ...] = (
    (frozenset({"terminal"}), frozenset({"card_payment"})),
    (frozenset({"merchant", "purchase", "shop"}), frozenset({"card_payment"})),
    (frozenset({"atm"}), frozenset({"cash_withdrawal"})),
    (frozenset({"recipient"}), frozenset({"transfer", "recipient"})),
)

_DOMAIN_FAMILY_SCOPE_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("cash_withdrawal", ("cash_withdrawal",)),
    ("card_payment", ("card_payment",)),
    ("transfer", ("transfer", "recipient")),
)

_DOMAIN_FAMILY_QUERY_CONCEPTS: dict[str, frozenset[str]] = {
    "cash_withdrawal": frozenset({"cash_machine", "cash_withdrawal"}),
    "card_payment": frozenset({"card_payment"}),
    "transfer": frozenset({"transfer", "recipient_not_received"}),
}

_DOMAIN_FAMILY_SENTENCE_PATTERN: dict[str, str] = {
    "cash_withdrawal": r"\b(?:atm|cash|withdrawal)\b",
    "card_payment": r"\b(?:card|payment|merchant|charge|purchase)\b",
    "transfer": r"\b(?:transfer|recipient|sender)\b",
}

_CHECKS_REQUEST_LANGUAGE_TOKENS = frozenset({
    "apply", "applies", "can", "could", "ended", "give", "help", "make",
    "need", "please", "safe", "safely", "should", "submitted", "tell",
    "use", "using", "want", "would",
})

_CHECKS_SINGLE_TARGETS_BY_DOMAIN: dict[str, dict[str, frozenset[str]]] = {
    "transfer": {"account": frozenset({"account"})},
    "card_payment": {"duplicate": frozenset({"duplicate", "duplicated"})},
}

_CHECKS_EXPLAINED_TOKENS = frozenset({
    "action", "atm", "beneficiary", "cash", "cash_machine", "cash_withdrawal",
    "card_payment", "checks", "confirm", "declined", "details", "failed",
    "finished", "has", "merchant", "not", "payment", "pending", "processing",
    "recipient", "recipient_not_received", "recognised", "retry", "reverted",
    "status", "timing", "transaction", "transfer", "unrecognised", "withdrawal",
})

_CHECKS_TARGET_EQUIVALENCE: dict[str, frozenset[str]] = {
    "account": frozenset({"account"}),
    "duplicate": frozenset({"duplicate", "duplicated"}),
}

# A requested account CHECKS target cannot be established by an incidental
# ``account`` token when the sentence's actual check object is a distinct
# registration/profile setting.  This is intentionally narrower than a target
# ontology and preserves ordinary references to devices outside these objects.
_CHECKS_TARGET_CONFLICT_PATTERNS: dict[str, tuple[str, ...]] = {
    "account": (
        r"\b(?:mobile[- ]?device|device)\s+(?:registration|profile|setting|configuration)\b",
        r"\bcustomer[- ]?profile\s+(?:registration|setting|configuration)\b",
    ),
}


def _has_generic_private_target(query: str) -> bool:
    words = set(canonical_tokens(query, {"concepts": {}}, ()))
    return bool(words & {"private", "internal", "hidden"}) and bool(words & {"code", "identifier", "instruction", "route", "reference"})


def _best_canonical_sentence_support(
    query: str,
    item: EvidenceChunk,
    lexicon: dict[str, Any],
    canonical_idf: dict[str, float],
    stopwords: Iterable[str],
) -> tuple[float, str | None]:
    query_tokens = set(canonical_tokens(query, lexicon, stopwords))
    if not query_tokens:
        return 0.0, None
    fallback = math.log(len(canonical_idf) + 2) + 1
    denominator = math.fsum(canonical_idf.get(token, fallback) for token in sorted(query_tokens)) or 1.0
    candidates: list[tuple[float, str]] = []
    for sentence in split_sentences(item.content):
        sentence_tokens = set(canonical_tokens(f"{item.heading} {sentence}", lexicon, stopwords))
        overlap = query_tokens & sentence_tokens
        coverage = math.fsum(canonical_idf.get(token, fallback) for token in sorted(overlap)) / denominator
        candidates.append((coverage, sentence))
    return max(candidates, key=lambda row: (row[0], row[1]), default=(0.0, None))


def _canonical_sentence_coverage(
    query: str,
    item: EvidenceChunk,
    lexicon: dict[str, Any],
    canonical_idf: dict[str, float],
    stopwords: Iterable[str],
) -> float:
    return _best_canonical_sentence_support(query, item, lexicon, canonical_idf, stopwords)[0]


def _state_compatible_pool(
    query_concepts: set[str],
    evidence: Sequence[EvidenceChunk],
) -> tuple[tuple[EvidenceChunk, ...], tuple[str, ...]]:
    requested_states = tuple(sorted(concept for concept in _STATE_SCOPE_MARKERS if concept in query_concepts))
    if not requested_states:
        return tuple(evidence), ()
    compatible = tuple(
        item for item in evidence
        if all(
            any(marker in " ".join(item.intent_scope).casefold() for marker in _STATE_SCOPE_MARKERS[concept])
            for concept in requested_states
        )
    )
    return compatible, requested_states


def _single_checks_target(
    query: str,
    request_domain_family: str | None,
    requested_dimension: str,
    lexicon: dict[str, Any],
    stopwords: Iterable[str],
) -> str | None:
    """Return one proven CHECKS target, never a general completeness contract."""
    if requested_dimension != "CHECKS" or request_domain_family is None:
        return None
    allowed = _CHECKS_SINGLE_TARGETS_BY_DOMAIN.get(request_domain_family, {})
    if not allowed:
        return None
    tokens = set(canonical_tokens(query, lexicon, stopwords))
    residual = tokens - _CHECKS_EXPLAINED_TOKENS - _CHECKS_REQUEST_LANGUAGE_TOKENS - _CONTROL_PLANE_TOKENS
    targets = sorted(
        target for target, equivalents in allowed.items() if residual & equivalents
    )
    return targets[0] if len(targets) == 1 else None


def _sentence_matches_single_checks_target(
    sentence: str | None,
    target: str | None,
    lexicon: dict[str, Any],
    stopwords: Iterable[str],
) -> bool:
    if sentence is None:
        return False
    if target is None:
        return True
    sentence_tokens = set(canonical_tokens(sentence, lexicon, stopwords))
    target_present = bool(sentence_tokens & _CHECKS_TARGET_EQUIVALENCE[target])
    target_conflict = any(
        re.search(pattern, sentence, re.IGNORECASE)
        for pattern in _CHECKS_TARGET_CONFLICT_PATTERNS.get(target, ())
    )
    return target_present and not target_conflict


def _best_requested_sentence_support(
    query: str,
    evidence: Sequence[EvidenceChunk],
    dimension: str,
    single_checks_target: str | None,
    lexicon: dict[str, Any],
    canonical_idf: dict[str, float],
    stopwords: Iterable[str],
) -> dict[str, Any]:
    support = best_sentence_support(
        query,
        evidence,
        dimension,
        lexicon,
        canonical_idf,
        stopwords,
        require_sentence_dimension_match=True,
    )
    by_id = {item.evidence_id: item for item in evidence}
    diagnostics = [
        {
            **row,
            "single_checks_target": single_checks_target,
            "single_checks_target_match": _sentence_matches_single_checks_target(
                row["sentence"], single_checks_target, lexicon, stopwords,
            ),
        }
        for row in support["sentence_diagnostics"]
    ]
    eligible = [
        row for row in diagnostics
        if row["dimension_match"] and row["single_checks_target_match"]
    ]
    best = max(
        eligible,
        key=lambda row: (
            row["coverage"],
            -by_id[row["evidence_id"]].rank,
            row["evidence_id"],
            row["sentence"],
        ),
        default=None,
    )
    return {
        "dimension_match": best is not None,
        "best_sentence_support_coverage": best["coverage"] if best else 0.0,
        "best_evidence_id": best["evidence_id"] if best else None,
        "best_sentence": best["sentence"] if best else None,
        "sentence_diagnostics": diagnostics,
    }


def _scope_domain_families(item: EvidenceChunk) -> frozenset[str]:
    scope = " ".join(item.intent_scope).casefold()
    return frozenset(
        family
        for family, markers in _DOMAIN_FAMILY_SCOPE_MARKERS
        if any(marker in scope for marker in markers)
    )


def _standard_request_scope_pool(
    query_concepts: set[str],
    evidence: Sequence[EvidenceChunk],
) -> tuple[tuple[EvidenceChunk, ...], str | None, tuple[str, ...]]:
    """Apply request-domain coherence before any state/objective adjudication."""
    bounded = tuple(evidence)
    if not bounded:
        return (), None, ()
    requested_states = tuple(sorted(concept for concept in _STATE_SCOPE_MARKERS if concept in query_concepts))
    query_families = tuple(sorted(
        family
        for family, concepts in _DOMAIN_FAMILY_QUERY_CONCEPTS.items()
        if query_concepts & concepts
    ))
    all_families = tuple(sorted({family for item in bounded for family in _scope_domain_families(item)}))
    top_families = tuple(sorted(_scope_domain_families(bounded[0])))
    if len(query_families) == 1:
        family = query_families[0]
    elif requested_states and len(all_families) == 1:
        family = all_families[0]
    elif requested_states:
        family = None
    else:
        family = top_families[0] if len(top_families) == 1 else None

    if requested_states:
        domain_compatible = (
            tuple(item for item in bounded if family in _scope_domain_families(item))
            if family is not None else bounded
        )
    else:
        dominant_scope = set(bounded[0].intent_scope)
        domain_compatible = tuple(item for item in bounded if dominant_scope & set(item.intent_scope))
    return domain_compatible, family, requested_states


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
    requested_states = tuple(sorted(
        concept for concept in _STATE_SCOPE_MARKERS if concept in safe_query_tokens
    ))
    if len(requested_states) > 1:
        return {"anchor": (), "basis": (), "reason": "CONFLICTING_CORRECTIVE_STATE_ANCHOR"}
    anchor_text = " ".join(winner_anchor).casefold()
    if requested_states and not all(
        any(marker in anchor_text for marker in _STATE_SCOPE_MARKERS[state])
        for state in requested_states
    ):
        return {"anchor": (), "basis": (), "reason": "WRONG_STATE_CORRECTIVE_SCOPE_ANCHOR"}
    requested_families = tuple(sorted(
        family
        for family, concepts in _DOMAIN_FAMILY_QUERY_CONCEPTS.items()
        if safe_query_tokens & concepts
    ))
    anchor_families = tuple(sorted(
        family
        for family, markers in _DOMAIN_FAMILY_SCOPE_MARKERS
        if any(marker in anchor_text for marker in markers)
    ))
    if len(requested_families) > 1:
        return {"anchor": (), "basis": (), "reason": "AMBIGUOUS_CORRECTIVE_SCOPE_ANCHOR"}
    if requested_families and requested_families[0] not in anchor_families:
        return {"anchor": (), "basis": (), "reason": "WRONG_DOMAIN_CORRECTIVE_SCOPE_ANCHOR"}
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
    requested_state_names = tuple(sorted(
        concept for concept in _STATE_SCOPE_MARKERS if concept in query_concepts
    ))
    if len(requested_state_names) > 1:
        return {
            "status": RequestedTargetStatus.UNSUPPORTED,
            "reason": "CONFLICTING_REQUESTED_STATES",
            "dimension": detect_requested_dimension(query),
            "dimensions": detect_requested_dimensions(query),
            "conflicting_states": list(requested_state_names),
        }
    if not requested_state_names and _UNKNOWN_TRANSACTION_STATE_PATTERN.search(query):
        return {
            "status": RequestedTargetStatus.UNSUPPORTED,
            "reason": "UNKNOWN_REQUESTED_STATE",
            "dimension": detect_requested_dimension(query),
            "dimensions": detect_requested_dimensions(query),
        }
    domain_compatible, request_domain_family, requested_states = _standard_request_scope_pool(
        query_concepts, standard_evidence,
    )
    if requested_states and request_domain_family is None:
        return {
            "status": RequestedTargetStatus.UNSUPPORTED,
            "reason": "AMBIGUOUS_COMPETING_TARGETS",
            "dimension": detect_requested_dimension(query),
            "request_domain_family": None,
            "domain_compatible_evidence_ids": [item.evidence_id for item in domain_compatible],
        }
    state_compatible, _ = _state_compatible_pool(query_concepts, domain_compatible)
    if requested_states and not state_compatible:
        return {
            "status": RequestedTargetStatus.UNSUPPORTED,
            "reason": "EVIDENCE_TARGET_STATE_CONFLICT",
            "dimension": detect_requested_dimension(query),
            "conflicting_states": list(requested_states),
            "request_domain_family": request_domain_family,
            "domain_compatible_evidence_ids": [item.evidence_id for item in domain_compatible],
        }
    support_evidence = state_compatible if requested_states else domain_compatible
    if not support_evidence:
        return {
            "status": RequestedTargetStatus.UNSUPPORTED,
            "reason": "NO_REQUEST_DOMAIN_COMPATIBLE_EVIDENCE",
            "dimension": detect_requested_dimension(query),
            "request_domain_family": request_domain_family,
            "domain_compatible_evidence_ids": [],
        }

    dimensions = detect_requested_dimensions(query)
    dimension = dimensions[0] if dimensions else detect_requested_dimension(query)
    if len(dimensions) > 1:
        obligation_support: list[dict[str, Any]] = []
        for dimension_row in dimensions:
            dimension_name = str(dimension_row["dimension"])
            single_checks_target = _single_checks_target(
                query, request_domain_family, dimension_name, lexicon, stopwords,
            )
            support = _best_requested_sentence_support(
                query,
                support_evidence,
                dimension_name,
                single_checks_target,
                lexicon,
                canonical_idf,
                stopwords,
            )
            complete = (
                bool(support["dimension_match"])
                and float(support["best_sentence_support_coverage"]) >= policy["min_support_coverage"]
            )
            if complete and dimension_name == "TIMING_WINDOW":
                by_id = {item.evidence_id: item for item in support_evidence}
                authority = by_id.get(str(support["best_evidence_id"]))
                complete = bool(authority and authority.document_type.casefold() in {"policy", "faq"})
            obligation_support.append({
                "dimension": dimension_name,
                "complete": complete,
                "best_evidence_id": support["best_evidence_id"],
                "best_sentence": support["best_sentence"],
                "coverage": support["best_sentence_support_coverage"],
            })
        incomplete = [row["dimension"] for row in obligation_support if not row["complete"]]
        return {
            "status": RequestedTargetStatus.UNSUPPORTED if incomplete else RequestedTargetStatus.SUPPORTED,
            "reason": "INCOMPLETE_REQUESTED_OBLIGATION_COVERAGE" if incomplete else "COMPLETE_REQUESTED_OBLIGATION_COVERAGE",
            "dimension": dimension,
            "dimensions": dimensions,
            "requested_obligation_support": obligation_support,
            "incomplete_dimensions": incomplete,
            "support_evidence_ids": sorted({
                str(row["best_evidence_id"]) for row in obligation_support if row["complete"]
            }),
            "state_compatible_evidence_ids": [item.evidence_id for item in support_evidence],
            "request_domain_family": request_domain_family,
            "domain_compatible_evidence_ids": [item.evidence_id for item in domain_compatible],
            "fallback_support_authorizations": (),
        }
    single_checks_target = _single_checks_target(
        query, request_domain_family, str(dimension["dimension"]), lexicon, stopwords,
    )
    coverages = [
        _canonical_sentence_coverage(query, item, lexicon, canonical_idf, stopwords)
        for item in support_evidence
    ]
    relevant = [index for index, coverage in enumerate(coverages) if coverage >= policy["min_support_coverage"]]
    competing = False
    if len(support_evidence) >= 2 and len(relevant) >= 2:
        first, second = support_evidence[relevant[0]], support_evidence[relevant[1]]
        competing = (
            not set(first.intent_scope) & set(second.intent_scope)
            and first.score - second.score < policy["ambiguity_score_gap"]
        )
    if competing:
        return {"status": RequestedTargetStatus.UNSUPPORTED, "reason": "AMBIGUOUS_COMPETING_TARGETS", "dimension": dimension, "direct_coverages": coverages}

    if any(name not in _PRIVATE_SLOTS for name in slot_names):
        evidence_text = " ".join(f"{item.heading} {item.content}" for item in support_evidence).casefold()
        unsupported_slots = [
            row["slot"] for row in slots
            if row["matched_query_phrase"].casefold() not in evidence_text
        ]
        if unsupported_slots:
            return {"status": RequestedTargetStatus.BLOCKED_CONTROL_PLANE, "reason": "UNSUPPORTED_EXACT_OR_SPECIFIC_TARGET", "dimension": dimension, "unsupported_slots": unsupported_slots}

    if support_evidence[0].score < policy["min_top1_score"]:
        return {
            "status": RequestedTargetStatus.UNSUPPORTED,
            "reason": "LOW_RETRIEVAL_SUPPORT",
            "dimension": dimension,
            "direct_coverages": coverages,
            "state_compatible_evidence_ids": [item.evidence_id for item in support_evidence],
        }

    support_coverages = [
        _canonical_sentence_coverage(query, item, lexicon, canonical_idf, stopwords)
        for item in support_evidence
    ]

    fallback_authorizations: tuple[FallbackSupportAuthorization, ...] = ()
    fallback_coverage: float | None = None
    sentence_diagnostics: list[dict[str, Any]] = []
    if dimension["dimension"] == "UNKNOWN":
        supported = max(support_coverages, default=0.0) >= policy["min_support_coverage"]
        reason = "DIRECT_CANONICAL_SUPPORT" if supported else "LOW_DIRECT_CANONICAL_SUPPORT"
        support_evidence_ids = [
            item.evidence_id for item, coverage in zip(support_evidence, support_coverages, strict=True)
            if coverage >= policy["min_support_coverage"]
        ]
    else:
        support = best_sentence_support(
            query,
            support_evidence,
            str(dimension["dimension"]),
            lexicon,
            canonical_idf,
            stopwords,
        )
        supported = bool(support["dimension_match"]) and support["best_sentence_support_coverage"] >= policy["min_support_coverage"]
        reason = "DIMENSION_AWARE_SUPPORT" if supported else "REQUESTED_DIMENSION_NOT_SUPPORTED"
        sentence_support = _best_requested_sentence_support(
            query,
            support_evidence,
            str(dimension["dimension"]),
            single_checks_target,
            lexicon,
            canonical_idf,
            stopwords,
        )
        exact_sentence_meets_threshold = (
            bool(sentence_support["dimension_match"])
            and float(sentence_support["best_sentence_support_coverage"]) >= policy["min_support_coverage"]
        )
        if supported and not exact_sentence_meets_threshold:
            supported = False
            reason = "REQUESTED_DIMENSION_NOT_SUPPORTED"
        fallback_evidence_id = sentence_support["best_evidence_id"]
        fallback_sentence = sentence_support["best_sentence"]
        fallback_coverage = float(sentence_support["best_sentence_support_coverage"])
        sentence_diagnostics = sentence_support["sentence_diagnostics"]
        fallback_diagnostic = next(
            (
                row for row in sentence_support["sentence_diagnostics"]
                if row["evidence_id"] == fallback_evidence_id and row["sentence"] == fallback_sentence
            ),
            None,
        )
        fallback_substantive_overlap = bool(
            fallback_diagnostic
            and set(fallback_diagnostic["matched_canonical_tokens"]) - _FALLBACK_GENERIC_OVERLAP_TOKENS
        )
        fallback_sentence_domain_bound = bool(
            fallback_sentence
            and request_domain_family in _DOMAIN_FAMILY_SENTENCE_PATTERN
            and re.search(
                _DOMAIN_FAMILY_SENTENCE_PATTERN[request_domain_family],
                fallback_sentence,
                re.IGNORECASE,
            )
        )
        actionable_checks_only = (
            not support["dimension_match"]
            and dimension["dimension"] == "NEXT_ACTION"
            and any(
                coverage > 0.0
                and re.search(r"\b(?:check|confirm|review|inspect)\b", f"{item.heading} {item.content}", re.IGNORECASE)
                for item, coverage in zip(support_evidence, support_coverages, strict=True)
            )
        )
        if (
            not supported
            and sentence_support["dimension_match"]
            and fallback_evidence_id
            and fallback_sentence
            and fallback_coverage > 0.0
            and (fallback_substantive_overlap or fallback_sentence_domain_bound)
        ):
            top_scope = set(support_evidence[0].intent_scope)
            coherent_top = len(support_evidence) >= 2 and bool(top_scope & set(support_evidence[1].intent_scope))
            close_competitor = any(
                not top_scope & set(item.intent_scope)
                and support_evidence[0].score - item.score < policy["ambiguity_score_gap"]
                for item in support_evidence[1:]
            )
            support_in_scope = any(
                item.evidence_id == fallback_evidence_id and bool(top_scope & set(item.intent_scope))
                for item in support_evidence
            )
            state_bound_fallback = bool(requested_states) and support_in_scope
            if (coherent_top or state_bound_fallback) and support_in_scope and not close_competitor:
                supported = True
                reason = (
                    "STATE_COMPATIBLE_DIRECT_DIMENSION_FALLBACK"
                    if state_bound_fallback
                    else "COHERENT_DIRECT_DIMENSION_FALLBACK"
                )
                fallback_authorizations = (FallbackSupportAuthorization(
                    evidence_id=fallback_evidence_id,
                    support_quote=fallback_sentence,
                    dimension=str(dimension["dimension"]),
                    coverage=fallback_coverage,
                    reason=reason,
                ),)
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
                for item in support_evidence
            )
            if not authority_found:
                supported = False
                reason = "TIMING_POLICY_AUTHORITY_REQUIRED"
        support_evidence_ids = [fallback_evidence_id] if supported and fallback_evidence_id else []

    return {
        "status": RequestedTargetStatus.SUPPORTED if supported else RequestedTargetStatus.UNSUPPORTED,
        "reason": reason,
        "dimension": dimension,
        "dimensions": dimensions,
        "direct_coverages": coverages,
        "support_evidence_ids": support_evidence_ids,
        "state_compatible_evidence_ids": [item.evidence_id for item in support_evidence],
        "request_domain_family": request_domain_family,
        "domain_compatible_evidence_ids": [item.evidence_id for item in domain_compatible],
        "fallback_support_authorizations": fallback_authorizations if dimension["dimension"] != "UNKNOWN" else (),
        "fallback_support_coverage": fallback_coverage if dimension["dimension"] != "UNKNOWN" else None,
        "single_checks_target": single_checks_target,
        "single_checks_target_diagnostics": (
            sentence_diagnostics
            if dimension["dimension"] != "UNKNOWN" else []
        ),
    }


def select_supported_standard_objectives(
    query: str,
    candidate_pool: Sequence[EvidenceChunk],
    lexicon: dict[str, Any],
    canonical_idf: dict[str, float],
    stopwords: Iterable[str],
    policy: dict[str, Any],
    fallback_support_authorizations: Sequence[FallbackSupportAuthorization | dict[str, Any]] = (),
) -> tuple[tuple[EvidenceChunk, ...], tuple[FactualObjective, ...]]:
    """Bind each selected STANDARD chunk and exact claim sentence to the request."""
    if not candidate_pool:
        return (), ()
    query_concepts = set(canonical_tokens(query, lexicon, stopwords))
    domain_compatible, request_domain_family, requested_states = _standard_request_scope_pool(query_concepts, candidate_pool)
    if requested_states and len({family for item in domain_compatible for family in _scope_domain_families(item)}) > 1:
        return (), ()
    state_compatible, _ = _state_compatible_pool(query_concepts, domain_compatible)
    scoped_pool = state_compatible if requested_states else domain_compatible
    if not scoped_pool:
        return (), ()

    dimension_rows = detect_requested_dimensions(query)
    if len(dimension_rows) > 1:
        selected_by_id: dict[str, EvidenceChunk] = {}
        objectives: list[FactualObjective] = []
        used_support_pairs: set[tuple[str, str]] = set()
        for dimension_row in dimension_rows:
            dimension_name = str(dimension_row["dimension"])
            single_checks_target = _single_checks_target(
                query, request_domain_family, dimension_name, lexicon, stopwords,
            )
            choices: list[tuple[float, float, int, str, EvidenceChunk, str]] = []
            for item in scoped_pool:
                support = _best_requested_sentence_support(
                    query, [item], dimension_name, single_checks_target,
                    lexicon, canonical_idf, stopwords,
                )
                if not support["dimension_match"]:
                    continue
                coverage = float(support["best_sentence_support_coverage"])
                sentence = support["best_sentence"]
                if sentence is None or coverage < policy["min_support_coverage"]:
                    continue
                if (item.evidence_id, sentence) in used_support_pairs:
                    continue
                if dimension_name == "TIMING_WINDOW" and item.document_type.casefold() not in {"policy", "faq"}:
                    continue
                choices.append((-coverage, -item.score, item.rank, item.evidence_id, item, sentence))
            if not choices:
                return (), ()
            choice = min(choices, key=lambda row: row[:4])
            selected_by_id[choice[4].evidence_id] = choice[4]
            objectives.append(FactualObjective(dimension_name, choice[4].evidence_id, choice[5]))
            used_support_pairs.add((choice[4].evidence_id, choice[5]))
        selected = tuple(sorted(selected_by_id.values(), key=lambda item: (item.rank, item.evidence_id)))
        if len(selected) > policy["max_evidence"] or len(objectives) > policy["max_claims"]:
            return (), ()
        return selected, tuple(objectives)

    dimension = str((dimension_rows[0] if dimension_rows else detect_requested_dimension(query))["dimension"])
    single_checks_target = _single_checks_target(
        query, request_domain_family, dimension, lexicon, stopwords,
    )
    authorizations = tuple(
        value if isinstance(value, FallbackSupportAuthorization) else FallbackSupportAuthorization(**value)
        for value in fallback_support_authorizations
    )
    scored: list[tuple[float, float, int, str, EvidenceChunk, str]] = []
    for item in scoped_pool:
        if dimension == "UNKNOWN":
            coverage, sentence = _best_canonical_sentence_support(
                query, item, lexicon, canonical_idf, stopwords,
            )
            matched = sentence is not None and coverage >= policy["min_support_coverage"]
            if matched and sentence is not None:
                scored.append((-coverage, -item.score, item.rank, item.evidence_id, item, sentence))
        else:
            support = _best_requested_sentence_support(
                query,
                [item],
                dimension,
                single_checks_target,
                lexicon,
                canonical_idf,
                stopwords,
            )
            exact_sentences = set(split_sentences(item.content))
            authorized_quotes = {
                value.support_quote
                for value in authorizations
                if value.evidence_id == item.evidence_id
                and value.dimension == dimension
                and value.support_quote in exact_sentences
            }
            eligible = [
                diagnostic for diagnostic in support["sentence_diagnostics"]
                if diagnostic["dimension_match"]
                and diagnostic["single_checks_target_match"]
                and (
                    float(diagnostic["coverage"]) >= policy["min_support_coverage"]
                    or diagnostic["sentence"] in authorized_quotes
                )
            ]
            best = max(
                eligible,
                key=lambda row: (float(row["coverage"]), row["sentence"]),
                default=None,
            )
            if best is not None:
                scored.append((
                    -float(best["coverage"]),
                    -item.score,
                    item.rank,
                    item.evidence_id,
                    item,
                    best["sentence"],
                ))
    scored.sort(key=lambda row: row[:4])
    chosen = tuple(scored[: policy["max_evidence"]])
    evidence = tuple(row[4] for row in chosen)
    objectives = tuple(FactualObjective(dimension, row[4].evidence_id, row[5]) for row in chosen)
    return evidence, objectives


def select_supported_standard_evidence(
    query: str,
    candidate_pool: Sequence[EvidenceChunk],
    lexicon: dict[str, Any],
    canonical_idf: dict[str, float],
    stopwords: Iterable[str],
    policy: dict[str, Any],
) -> tuple[EvidenceChunk, ...]:
    """Select a bounded target-supporting subset from the runtime pool."""
    evidence, _ = select_supported_standard_objectives(
        query, candidate_pool, lexicon, canonical_idf, stopwords, policy,
    )
    return evidence
