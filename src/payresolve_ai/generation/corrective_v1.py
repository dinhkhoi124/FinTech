"""Generic corrective-plan assembly from approved runtime evidence."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Sequence

from .extractive import split_sentences
from .routing_v3 import FactualObjective
from .types import EvidenceChunk


BOUNDARIES = {
    "UNTRUSTED_OVERRIDE_REQUEST": "I cannot bypass the approved-evidence and citation controls.",
    "PRIVATE_OR_INTERNAL_TARGET_BLOCKED": "I cannot provide private or internal identifiers or instructions.",
    "UNSUPPORTED_EXACT_OR_SPECIFIC_TARGET": "I cannot assert the requested exact value or specific entitlement without approved support.",
}


OBJECTIVE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("SECURITY_CHECK", r"\b(?:secure|security|freeze|block|recognis|recogniz|protect)"),
    ("SUPPORTED_CHECK", r"\b(?:check|confirm|verify|review|compare|inspect)"),
    ("STATE_OR_TIMING", r"\b(?:pending|declined|reverted|state|business day|hour|window|timing)"),
    ("NEXT_ACTION", r"\b(?:contact|escalat\w*|report|follow|wait|retry|provide|record|use|route|action|avoid)\b"),
    ("ELIGIBILITY_OR_BOUND", r"\b(?:eligible|appl(?:y|ies)|only|limit|require|must|may)"),
)


MANDATORY_GROUPS = {
    "UNTRUSTED_OVERRIDE_REQUEST": (("NEXT_ACTION",),),
    "PRIVATE_OR_INTERNAL_TARGET_BLOCKED": (("SUPPORTED_CHECK", "SECURITY_CHECK"), ("NEXT_ACTION",)),
    "UNSUPPORTED_EXACT_OR_SPECIFIC_TARGET": (("STATE_OR_TIMING", "ELIGIBILITY_OR_BOUND"), ("NEXT_ACTION",)),
}


def corrective_objective_categories(text: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return tuple(name for name, pattern in OBJECTIVE_PATTERNS if re.search(pattern, normalized))


def mandatory_corrective_groups(blocked_reason: str) -> tuple[tuple[str, ...], ...]:
    """Expose generic obligation groups for target-aware candidate discovery."""
    return tuple(tuple(group) for group in MANDATORY_GROUPS.get(blocked_reason, ()))


def assemble_corrective_objectives(
    blocked_reason: str,
    candidate_evidence: Sequence[EvidenceChunk],
    policy: dict[str, Any],
) -> tuple[str | None, tuple[FactualObjective, ...], tuple[EvidenceChunk, ...], tuple[str, ...]]:
    """Return a complete bounded plan, or an empty plan when obligations fail."""
    boundary = BOUNDARIES.get(blocked_reason)
    groups = MANDATORY_GROUPS.get(blocked_reason)
    if boundary is None or groups is None:
        return None, (), (), ("CORRECTIVE_NOT_APPLICABLE",)

    max_candidates = int(policy["candidate_pool_max_chunks"])
    max_claims = int(policy["max_factual_claims"])
    bounded = list(candidate_evidence[:max_candidates])
    candidates: list[tuple[int, int, str, str, EvidenceChunk]] = []
    for item in bounded:
        for sentence_index, sentence in enumerate(split_sentences(item.content)):
            for category in corrective_objective_categories(f"{item.heading} {sentence}"):
                candidates.append((item.rank, sentence_index, category, sentence, item))

    chosen: list[FactualObjective] = []
    used_evidence: list[EvidenceChunk] = []
    used_evidence_ids: set[str] = set()
    used_sentences: set[tuple[str, str]] = set()
    missing: list[str] = []
    for group_index, group in enumerate(groups):
        available = [
            row for row in candidates
            if row[2] in group
            and row[4].evidence_id not in used_evidence_ids
            and (row[4].evidence_id, row[3]) not in used_sentences
        ]
        future_groups = groups[group_index + 1:]
        match = min(
            available,
            key=lambda row: (
                sum(
                    bool(set(corrective_objective_categories(f"{row[4].heading} {row[3]}")) & set(future_group))
                    for future_group in future_groups
                ),
                row[0], row[1], row[4].evidence_id, row[3],
            ),
            default=None,
        )
        if match is None:
            missing.append("|".join(group))
            continue
        _, _, category, sentence, item = match
        chosen.append(FactualObjective(category, item.evidence_id, sentence))
        used_sentences.add((item.evidence_id, sentence))
        used_evidence_ids.add(item.evidence_id)
        if item not in used_evidence:
            used_evidence.append(item)

    if missing:
        return boundary, (), (), tuple(f"MISSING_{value}" for value in missing)

    if policy.get("include_supported_optional_objectives", True):
        used_categories = {row.objective for row in chosen}
        for _, _, category, sentence, item in candidates:
            key = (item.evidence_id, sentence)
            if len(chosen) >= max_claims:
                break
            if category in used_categories or key in used_sentences or item.evidence_id in used_evidence_ids:
                continue
            chosen.append(FactualObjective(category, item.evidence_id, sentence))
            used_categories.add(category)
            used_sentences.add(key)
            used_evidence_ids.add(item.evidence_id)
            if item not in used_evidence:
                used_evidence.append(item)

    if len(chosen) > max_claims:
        return boundary, (), (), ("CORRECTIVE_CLAIM_BUDGET_EXCEEDED",)
    return boundary, tuple(chosen), tuple(used_evidence), ("CORRECTIVE_PLAN_COMPLETE",)
