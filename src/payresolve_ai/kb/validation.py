"""Deterministic validation for the PayResolve controlled synthetic KB."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class KBValidationError(ValueError):
    """Raised when a KB input cannot be parsed or its contract is invalid."""


REQUIRED_FIELDS = {
    "document_id",
    "document_family_id",
    "title",
    "document_type",
    "intent_scope",
    "intent_slugs",
    "intent_family",
    "product",
    "status",
    "version",
    "effective_date",
    "expiry_date",
    "supersedes_document_id",
    "approved_by",
    "organization",
    "source_type",
    "language",
    "risk_level",
    "synthetic_disclaimer",
    "content_sections",
}
DOCUMENT_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]+_[0-9]{3}$")
FAMILY_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")
SLUG_RE = re.compile(r"^[a-z0-9_]+$")
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+$")
PLACEHOLDER_RE = re.compile(r"\b(?:TODO|TBD|lorem\s+ipsum)\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\s().-]*){8,}(?!\d)")
TOKEN_RE = re.compile(r"[a-z0-9]+")
FORBIDDEN_INSTITUTIONS = (
    "hsbc",
    "citibank",
    "bank of america",
    "jpmorgan",
    "wells fargo",
    "barclays",
    "revolut",
    "vinsmartfuture",
)
ALLOWED_INTENT_FAMILIES = {"transfer", "card_payment", "cash_withdrawal"}
ALLOWED_PRODUCTS = {"bank_transfer", "card_payment", "cash_withdrawal"}
INTENT_CONTRACTS = {
    "pending_transfer": ("transfer", "bank_transfer"),
    "failed_transfer": ("transfer", "bank_transfer"),
    "declined_transfer": ("transfer", "bank_transfer"),
    "transfer_not_received_by_recipient": ("transfer", "bank_transfer"),
    "pending_card_payment": ("card_payment", "card_payment"),
    "declined_card_payment": ("card_payment", "card_payment"),
    "reverted_card_payment?": ("card_payment", "card_payment"),
    "pending_cash_withdrawal": ("cash_withdrawal", "cash_withdrawal"),
    "declined_cash_withdrawal": ("cash_withdrawal", "cash_withdrawal"),
    "cash_withdrawal_not_recognised": ("cash_withdrawal", "cash_withdrawal"),
}
HARD_NEGATIVE_REQUIRED_FIELDS = {
    "relationship_id",
    "source_intent",
    "confusing_intent",
    "shared_vocabulary",
    "decisive_distinguishing_fact",
    "positive_document_ids",
    "hard_negative_document_ids",
    "risk_if_confused",
}
VERSION_PLAN_REQUIRED_FIELDS = {
    "document_family_id",
    "expired",
    "approved",
    "draft",
    "meaningful_change",
}


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    document_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.document_id is not None:
            result["document_id"] = self.document_id
        return result


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise KBValidationError(f"Cannot read JSON {path}: {exc}") from exc


def load_config(root: Path, config_path: Path) -> dict[str, Any]:
    path = config_path if config_path.is_absolute() else root / config_path
    config = _read_json(path)
    if not isinstance(config, dict):
        raise KBValidationError("KB config must be a JSON object")
    return config


def load_documents(path: Path) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise KBValidationError(f"Cannot read KB dataset {path}: {exc}") from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            document = json.loads(line)
        except json.JSONDecodeError as exc:
            raise KBValidationError(f"Invalid JSONL at line {line_number}: {exc}") from exc
        if not isinstance(document, dict):
            raise KBValidationError(f"JSONL line {line_number} must be an object")
        documents.append(document)
    return documents


def _parse_date(value: Any, *, field: str, document_id: str) -> date:
    if not isinstance(value, str):
        raise KBValidationError(f"{document_id}.{field} must be an ISO date string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise KBValidationError(f"{document_id}.{field} is not a valid ISO date") from exc


def is_document_eligible(document: Mapping[str, Any], as_of_date: date) -> bool:
    """Return eligibility using only the fixed configured reference date."""
    if document.get("status") != "APPROVED":
        return False
    effective = _parse_date(
        document.get("effective_date"),
        field="effective_date",
        document_id=str(document.get("document_id", "<unknown>")),
    )
    expiry_value = document.get("expiry_date")
    expiry = (
        _parse_date(
            expiry_value,
            field="expiry_date",
            document_id=str(document.get("document_id", "<unknown>")),
        )
        if expiry_value is not None
        else None
    )
    return effective <= as_of_date and (expiry is None or as_of_date < expiry)


def canonical_dataset_bytes(documents: Sequence[Mapping[str, Any]]) -> bytes:
    ordered = sorted((deepcopy(dict(document)) for document in documents), key=lambda item: item["document_id"])
    lines = [
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for document in ordered
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def canonical_dataset_sha256(documents: Sequence[Mapping[str, Any]]) -> str:
    return hashlib.sha256(canonical_dataset_bytes(documents)).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalized_content(document: Mapping[str, Any]) -> str:
    sections = document.get("content_sections", [])
    text = " ".join(str(section.get("content", "")) for section in sections if isinstance(section, dict))
    return " ".join(TOKEN_RE.findall(text.lower()))


def _token_jaccard(left: str, right: str) -> float:
    left_tokens = set(TOKEN_RE.findall(left.lower()))
    right_tokens = set(TOKEN_RE.findall(right.lower()))
    if not left_tokens and not right_tokens:
        return 1.0
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _detect_cycle(start: str, by_id: Mapping[str, Mapping[str, Any]]) -> bool:
    seen: set[str] = set()
    current: str | None = start
    while current is not None:
        if current in seen:
            return True
        seen.add(current)
        document = by_id.get(current)
        if document is None:
            return False
        successor = document.get("supersedes_document_id")
        current = successor if isinstance(successor, str) else None
    return False


def _evaluate_first_28_quality_gate(
    documents: Sequence[Mapping[str, Any]],
    config: Mapping[str, Any],
    hard_negative_matrix: Mapping[str, Any],
    document_plan: Mapping[str, Any],
    as_of_date: date,
    structurally_valid_families: set[str],
    structurally_valid_relationship_ids: set[str],
) -> dict[str, Any]:
    required = document_plan["first_28_gate_requirements"]
    planned_ids = document_plan["first_28_quality_gate_document_ids"]
    by_id = {str(document.get("document_id")): document for document in documents}
    errors: list[str] = []
    missing = sorted(set(planned_ids) - set(by_id))
    if missing:
        errors.append(f"missing planned documents: {missing}")
    if len(planned_ids) != required["document_count"] or len(planned_ids) != len(set(planned_ids)):
        errors.append("first-28 plan must contain exactly 28 unique document IDs")
    subset = [by_id[document_id] for document_id in planned_ids if document_id in by_id]
    for document in subset:
        errors.extend(
            f"{issue.code}: {issue.document_id or ''} {issue.message}"
            for issue in _validate_document(document, config, as_of_date)
        )
    normalized = [_normalized_content(document) for document in subset]
    if len(normalized) != len(set(normalized)):
        errors.append("first-28 subset contains normalized duplicate content")
    eligible: list[Mapping[str, Any]] = []
    for document in subset:
        try:
            if is_document_eligible(document, as_of_date):
                eligible.append(document)
        except KBValidationError:
            pass
    if len(eligible) < required["eligible_approved_count"]:
        errors.append(f"first-28 eligible count is {len(eligible)}")
    coverage: dict[str, dict[str, Any]] = {}
    for intent in config["locked_intent_slugs"]:
        matching = [document for document in eligible if intent in document["intent_scope"]]
        types = sorted({document["document_type"] for document in matching})
        coverage[intent] = {"eligible_approved_count": len(matching), "document_types": types}
        if len(matching) < required["minimum_eligible_documents_per_intent"]:
            errors.append(f"{intent} has fewer than two first-28 eligible documents")
        if len(types) < required["minimum_document_types_per_intent"]:
            errors.append(f"{intent} has fewer than two first-28 document types")
    subset_ids = set(planned_ids)
    complete_families = sorted(
        str(plan["document_family_id"])
        for plan in document_plan.get("version_families", [])
        if isinstance(plan, dict)
        and str(plan.get("document_family_id")) in structurally_valid_families
        and {plan.get("expired"), plan.get("approved"), plan.get("draft")} <= subset_ids
    )
    if len(complete_families) < required["minimum_complete_version_families"]:
        errors.append("first-28 subset lacks four complete version families")
    resolved_relationships = [
        relationship["relationship_id"]
        for relationship in hard_negative_matrix.get("relationships", [])
        if isinstance(relationship, dict)
        and relationship.get("relationship_id") in structurally_valid_relationship_ids
        and set(relationship.get("positive_document_ids", [])) <= subset_ids
        and set(relationship.get("hard_negative_document_ids", [])) <= subset_ids
    ]
    if len(resolved_relationships) < required["minimum_fully_resolved_hard_negative_relationships"]:
        errors.append(f"only {len(resolved_relationships)} hard-negative relationships resolve in first 28")
    return {
        "result": "PASS" if not errors else "FAIL",
        "errors": errors,
        "document_count": len(subset),
        "eligible_approved_count": len(eligible),
        "intent_coverage": coverage,
        "complete_version_families": complete_families,
        "fully_resolved_hard_negative_relationship_ids": resolved_relationships,
        "expansion_decision": document_plan["expansion_decision"],
    }


def _validate_document(
    document: Mapping[str, Any],
    config: Mapping[str, Any],
    as_of_date: date,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    document_id = str(document.get("document_id", "<unknown>"))
    missing = sorted(REQUIRED_FIELDS - set(document))
    extra = sorted(set(document) - REQUIRED_FIELDS)
    if missing:
        issues.append(ValidationIssue("schema-required", f"Missing fields: {missing}", document_id))
    if extra:
        issues.append(ValidationIssue("schema-extra", f"Unexpected fields: {extra}", document_id))
    if missing:
        return issues

    if not isinstance(document["document_id"], str) or not DOCUMENT_ID_RE.fullmatch(document["document_id"]):
        issues.append(ValidationIssue("document-id-format", "Invalid document_id", document_id))
    if not isinstance(document["document_family_id"], str) or not FAMILY_ID_RE.fullmatch(document["document_family_id"]):
        issues.append(ValidationIssue("family-id-format", "Invalid document_family_id", document_id))
    if not isinstance(document["title"], str):
        issues.append(ValidationIssue("title-type", "title must be a string", document_id))
    elif len(document["title"].strip()) < 5:
        issues.append(ValidationIssue("title-length", "title must contain at least five characters", document_id))
    if document["document_type"] not in config["allowed_document_types"]:
        issues.append(ValidationIssue("document-type-enum", "Unknown document_type", document_id))
    if document["status"] not in config["allowed_statuses"]:
        issues.append(ValidationIssue("status-enum", "Unknown status", document_id))
    if document["risk_level"] not in config["allowed_risk_levels"]:
        issues.append(ValidationIssue("risk-enum", "Unknown risk_level", document_id))
    if not isinstance(document["version"], str) or not VERSION_RE.fullmatch(document["version"]):
        issues.append(ValidationIssue("version-format", "Version must use major.minor", document_id))
    supersedes = document["supersedes_document_id"]
    if supersedes is not None and not isinstance(supersedes, str):
        issues.append(ValidationIssue("supersedes-type", "supersedes_document_id must be null or a string", document_id))
    elif isinstance(supersedes, str) and not DOCUMENT_ID_RE.fullmatch(supersedes):
        issues.append(ValidationIssue("supersedes-format", "Invalid supersedes_document_id", document_id))
    if not isinstance(document["approved_by"], str) or len(document["approved_by"].strip()) < 3:
        issues.append(ValidationIssue("approved-by-contract", "approved_by must contain at least three characters", document_id))
    if not isinstance(document["intent_family"], str) or document["intent_family"] not in ALLOWED_INTENT_FAMILIES:
        issues.append(ValidationIssue("intent-family-enum", "Unknown intent_family", document_id))
    if not isinstance(document["product"], str) or document["product"] not in ALLOWED_PRODUCTS:
        issues.append(ValidationIssue("product-enum", "Unknown product", document_id))
    if document["organization"] != config["organization"]:
        issues.append(ValidationIssue("organization", "Unexpected organization", document_id))
    if document["source_type"] != config["source_type"]:
        issues.append(ValidationIssue("source-type", "Unexpected source_type", document_id))
    if document["language"] != config["language"]:
        issues.append(ValidationIssue("language", "Unexpected language", document_id))
    if document["synthetic_disclaimer"] != config["synthetic_disclaimer"]:
        issues.append(ValidationIssue("synthetic-disclaimer", "Disclaimer does not match config", document_id))

    intent_scope = document["intent_scope"]
    intent_slugs = document["intent_slugs"]
    locked_mapping = config["locked_intent_slugs"]
    valid_intent_scope = isinstance(intent_scope, list) and bool(intent_scope) and all(
        isinstance(intent, str) for intent in intent_scope
    )
    valid_intent_slugs = isinstance(intent_slugs, list) and bool(intent_slugs) and all(
        isinstance(slug, str) for slug in intent_slugs
    )
    if not valid_intent_scope:
        issues.append(ValidationIssue("intent-scope", "intent_scope must be a non-empty list", document_id))
    elif len(intent_scope) != len(set(intent_scope)):
        issues.append(ValidationIssue("intent-scope-duplicate", "intent_scope contains duplicates", document_id))
    if not valid_intent_slugs:
        issues.append(ValidationIssue("intent-slugs", "intent_slugs must be a non-empty list", document_id))
    elif len(intent_slugs) != len(set(intent_slugs)):
        issues.append(ValidationIssue("intent-slug-duplicate", "intent_slugs contains duplicates", document_id))
    if valid_intent_scope and valid_intent_slugs:
        expected_contracts = {INTENT_CONTRACTS[intent] for intent in intent_scope if intent in INTENT_CONTRACTS}
        if len(expected_contracts) == 1:
            expected_family, expected_product = next(iter(expected_contracts))
            if (document["intent_family"], document["product"]) != (expected_family, expected_product):
                issues.append(
                    ValidationIssue(
                        "intent-family-product-mismatch",
                        f"Intents require ({expected_family}, {expected_product})",
                        document_id,
                    )
                )
        elif len(expected_contracts) > 1:
            issues.append(ValidationIssue("incompatible-intent-contracts", "Intent scope spans incompatible families", document_id))
        for index, intent in enumerate(intent_scope):
            if intent not in locked_mapping:
                issues.append(ValidationIssue("unknown-intent", f"Unknown intent: {intent}", document_id))
                continue
            expected_slug = locked_mapping[intent]
            actual_slug = intent_slugs[index] if index < len(intent_slugs) else None
            if actual_slug != expected_slug:
                issues.append(
                    ValidationIssue(
                        "intent-slug-mismatch",
                        f"{intent} must map to {expected_slug}, got {actual_slug}",
                        document_id,
                    )
                )
            if not isinstance(actual_slug, str) or not SLUG_RE.fullmatch(actual_slug):
                issues.append(ValidationIssue("intent-slug-format", f"Unsafe slug: {actual_slug}", document_id))
        if len(intent_scope) != len(intent_slugs):
            issues.append(ValidationIssue("intent-slug-length", "Intent and slug counts differ", document_id))

    try:
        effective = _parse_date(document["effective_date"], field="effective_date", document_id=document_id)
        expiry = (
            _parse_date(document["expiry_date"], field="expiry_date", document_id=document_id)
            if document["expiry_date"] is not None
            else None
        )
        if expiry is not None and effective >= expiry:
            issues.append(ValidationIssue("date-order", "effective_date must precede expiry_date", document_id))
        if document["status"] == "EXPIRED":
            if expiry is None:
                issues.append(ValidationIssue("expired-missing-date", "EXPIRED requires expiry_date", document_id))
            elif expiry > as_of_date:
                issues.append(ValidationIssue("expired-future-date", "EXPIRED expiry_date is after reference date", document_id))
        if document["status"] == "APPROVED" and expiry is not None and expiry <= as_of_date:
            issues.append(ValidationIssue("approved-already-expired", "APPROVED document is expired as of reference date", document_id))
    except KBValidationError as exc:
        issues.append(ValidationIssue("date-format", str(exc), document_id))

    sections = document["content_sections"]
    if not isinstance(sections, list) or not sections:
        issues.append(ValidationIssue("sections-empty", "content_sections must be non-empty", document_id))
    else:
        section_ids: list[str] = []
        for section in sections:
            if not isinstance(section, dict) or set(section) != {"section_id", "heading", "content"}:
                issues.append(ValidationIssue("section-schema", "Invalid section object", document_id))
                continue
            section_id = section["section_id"]
            if not isinstance(section_id, str) or not SLUG_RE.fullmatch(section_id):
                issues.append(ValidationIssue("section-id-format", f"Unsafe section_id: {section_id}", document_id))
            else:
                section_ids.append(section_id)
            if not isinstance(section["heading"], str) or len(section["heading"].strip()) < 2:
                issues.append(ValidationIssue("section-heading", "Section heading is empty", document_id))
            if not isinstance(section["content"], str) or len(section["content"].strip()) < 20:
                issues.append(ValidationIssue("section-content", "Section content is too short", document_id))
        if len(section_ids) != len(set(section_ids)):
            issues.append(ValidationIssue("section-id-duplicate", "Section IDs must be unique", document_id))

    content_parts = [str(document.get("title", ""))]
    if isinstance(sections, list):
        for section in sections:
            if isinstance(section, dict):
                content_parts.extend(
                    [str(section.get("heading", "")), str(section.get("content", ""))]
                )
    searchable_text = " ".join(content_parts)
    if PLACEHOLDER_RE.search(searchable_text):
        issues.append(ValidationIssue("placeholder", "Obvious placeholder text detected", document_id))
    if PHONE_RE.search(searchable_text):
        issues.append(ValidationIssue("phone-like-content", "Phone-like numeric content detected", document_id))
    lowered = searchable_text.lower()
    for institution in FORBIDDEN_INSTITUTIONS:
        if institution in lowered:
            issues.append(ValidationIssue("real-institution", f"Forbidden institution term: {institution}", document_id))
    return issues


def _version_tuple(value: Any) -> tuple[int, int] | None:
    if not isinstance(value, str) or not VERSION_RE.fullmatch(value):
        return None
    major, minor = value.split(".")
    return int(major), int(minor)


def _validate_version_families(
    document_plan: Mapping[str, Any],
    by_id: Mapping[str, Mapping[str, Any]],
    eligible_by_family: Mapping[str, list[str]],
) -> tuple[list[ValidationIssue], set[str]]:
    issues: list[ValidationIssue] = []
    valid_families: set[str] = set()
    plans = document_plan.get("version_families")
    if not isinstance(plans, list):
        return [ValidationIssue("version-plan-schema", "version_families must be a list")], valid_families

    used_role_ids: set[str] = set()
    for index, plan in enumerate(plans):
        plan_issues: list[ValidationIssue] = []
        label = f"version_families[{index}]"
        if not isinstance(plan, dict) or set(plan) != VERSION_PLAN_REQUIRED_FIELDS:
            issues.append(ValidationIssue("version-plan-schema", f"{label} must contain exactly {sorted(VERSION_PLAN_REQUIRED_FIELDS)}"))
            continue
        family_id = plan["document_family_id"]
        role_ids = [plan[role] for role in ("expired", "approved", "draft")]
        if not isinstance(family_id, str) or not FAMILY_ID_RE.fullmatch(family_id):
            plan_issues.append(ValidationIssue("version-plan-schema", f"{label} has invalid document_family_id"))
        if not isinstance(plan["meaningful_change"], str) or len(plan["meaningful_change"].strip()) < 20:
            plan_issues.append(ValidationIssue("version-plan-meaningful-change", f"{label} needs a meaningful change description"))
        if any(not isinstance(role_id, str) for role_id in role_ids) or len(set(role_ids)) != 3:
            plan_issues.append(ValidationIssue("version-plan-schema", f"{label} role IDs must be three unique strings"))
        else:
            reused = sorted(set(role_ids) & used_role_ids)
            if reused:
                plan_issues.append(ValidationIssue("version-plan-role-reuse", f"Role documents reused across plans: {reused}"))
            used_role_ids.update(role_ids)

        members = [by_id.get(role_id) if isinstance(role_id, str) else None for role_id in role_ids]
        missing_refs = [role_id for role_id, member in zip(role_ids, members) if member is None]
        if missing_refs:
            plan_issues.append(ValidationIssue("version-plan-reference", f"{label} references missing documents: {missing_refs}"))
        if any(member is None for member in members):
            issues.extend(plan_issues)
            continue

        expired, approved, draft = members
        assert expired is not None and approved is not None and draft is not None
        if any(member.get("document_family_id") != family_id for member in members):
            plan_issues.append(ValidationIssue("version-plan-family-mismatch", f"{label} role documents do not match {family_id}"))
        actual_statuses = [expired.get("status"), approved.get("status"), draft.get("status")]
        if actual_statuses != ["EXPIRED", "APPROVED", "DRAFT"]:
            plan_issues.append(ValidationIssue("version-chain-status", f"{label} statuses are {actual_statuses}"))
        if approved.get("supersedes_document_id") != plan["expired"] or draft.get("supersedes_document_id") != plan["approved"]:
            plan_issues.append(ValidationIssue("version-chain-disconnected", f"{label} supersession chain is not expired -> approved -> draft"))

        contract_fields = ("document_type", "intent_scope", "intent_slugs", "intent_family", "product")
        mismatches = [
            field for field in contract_fields
            if not (expired.get(field) == approved.get(field) == draft.get(field))
        ]
        if mismatches:
            plan_issues.append(ValidationIssue("version-chain-contract-mismatch", f"{label} differs on {mismatches}"))

        versions = [_version_tuple(member.get("version")) for member in members]
        if any(version is None for version in versions) or not (versions[0] < versions[1] < versions[2]):
            plan_issues.append(ValidationIssue("version-chain-nonmonotonic-version", f"{label} versions are not strictly increasing"))
        try:
            dates = [
                _parse_date(member.get("effective_date"), field="effective_date", document_id=str(member.get("document_id")))
                for member in members
            ]
            if not dates[0] < dates[1] < dates[2]:
                plan_issues.append(ValidationIssue("version-chain-nonmonotonic-date", f"{label} effective dates are not strictly increasing"))
        except KBValidationError:
            plan_issues.append(ValidationIssue("version-chain-nonmonotonic-date", f"{label} has an invalid effective date"))

        if eligible_by_family.get(str(family_id), []) != [plan["approved"]]:
            plan_issues.append(ValidationIssue("version-chain-approved-eligibility", f"{label} must have only the approved role eligible"))
        if not plan_issues:
            valid_families.add(str(family_id))
        issues.extend(plan_issues)
    return issues, valid_families


def _validate_hard_negative_relationships(
    hard_negative_matrix: Mapping[str, Any],
    locked_mapping: Mapping[str, str],
    by_id: Mapping[str, Mapping[str, Any]],
    eligible_ids: set[str],
) -> tuple[list[ValidationIssue], list[Mapping[str, Any]], set[str]]:
    issues: list[ValidationIssue] = []
    valid_relationship_ids: set[str] = set()
    relationships = hard_negative_matrix.get("relationships")
    if not isinstance(relationships, list):
        return [ValidationIssue("hard-negative-schema", "relationships must be a list")], [], valid_relationship_ids

    seen_ids: set[str] = set()
    for index, relationship in enumerate(relationships):
        relationship_issues: list[ValidationIssue] = []
        label = f"relationships[{index}]"
        if not isinstance(relationship, dict):
            issues.append(ValidationIssue("hard-negative-schema", f"{label} must be an object"))
            continue
        missing = sorted(HARD_NEGATIVE_REQUIRED_FIELDS - set(relationship))
        extra = sorted(set(relationship) - HARD_NEGATIVE_REQUIRED_FIELDS)
        if missing:
            relationship_issues.append(ValidationIssue("hard-negative-required-field", f"{label} missing fields: {missing}"))
        if extra:
            relationship_issues.append(ValidationIssue("hard-negative-extra-field", f"{label} has unexpected fields: {extra}"))

        relationship_id = relationship.get("relationship_id")
        if not isinstance(relationship_id, str) or not relationship_id.strip():
            relationship_issues.append(ValidationIssue("hard-negative-id", f"{label} has an invalid relationship_id"))
        elif relationship_id in seen_ids:
            relationship_issues.append(ValidationIssue("hard-negative-id", f"Duplicate relationship_id: {relationship_id}"))
        else:
            seen_ids.add(relationship_id)

        source_intent = relationship.get("source_intent")
        confusing_intent = relationship.get("confusing_intent")
        if (
            not isinstance(source_intent, str)
            or not isinstance(confusing_intent, str)
            or source_intent not in locked_mapping
            or confusing_intent not in locked_mapping
        ):
            relationship_issues.append(ValidationIssue("hard-negative-intent", f"Unknown relationship intents: {source_intent}, {confusing_intent}"))
        elif source_intent == confusing_intent:
            relationship_issues.append(ValidationIssue("hard-negative-same-intent", f"{relationship_id} uses the same source and confusing intent"))

        vocabulary = relationship.get("shared_vocabulary")
        if not isinstance(vocabulary, list) or not vocabulary or any(
            not isinstance(term, str) or not term.strip() for term in vocabulary
        ):
            relationship_issues.append(ValidationIssue("hard-negative-shared-vocabulary", f"{relationship_id} needs non-empty string vocabulary"))
        elif len(vocabulary) != len(set(vocabulary)):
            relationship_issues.append(ValidationIssue("hard-negative-shared-vocabulary", f"{relationship_id} vocabulary must be unique"))
        for field in ("decisive_distinguishing_fact", "risk_if_confused"):
            value = relationship.get(field)
            if not isinstance(value, str) or len(value.strip()) < 20:
                relationship_issues.append(ValidationIssue("hard-negative-text", f"{relationship_id}.{field} must be meaningful text"))

        document_sets: dict[str, list[str]] = {}
        for field in ("positive_document_ids", "hard_negative_document_ids"):
            values = relationship.get(field)
            if not isinstance(values, list) or not values or any(
                not isinstance(document_id, str) or not document_id for document_id in values
            ):
                relationship_issues.append(ValidationIssue("hard-negative-document-list", f"{relationship_id}.{field} must be a non-empty string list"))
                continue
            if len(values) != len(set(values)):
                relationship_issues.append(ValidationIssue("hard-negative-document-list", f"{relationship_id}.{field} contains duplicates"))
            document_sets[field] = values
        if len(document_sets) == 2 and set(document_sets["positive_document_ids"]) & set(document_sets["hard_negative_document_ids"]):
            relationship_issues.append(ValidationIssue("hard-negative-document-overlap", f"{relationship_id} document sets overlap"))

        if (
            isinstance(source_intent, str)
            and isinstance(confusing_intent, str)
            and source_intent in locked_mapping
            and confusing_intent in locked_mapping
        ):
            for field, expected_intent in (
                ("positive_document_ids", source_intent),
                ("hard_negative_document_ids", confusing_intent),
            ):
                for document_id in document_sets.get(field, []):
                    document = by_id.get(document_id)
                    if document is None:
                        relationship_issues.append(ValidationIssue("hard-negative-reference", f"Missing document {document_id}"))
                    elif expected_intent not in document.get("intent_scope", []):
                        relationship_issues.append(ValidationIssue("hard-negative-label", f"{document_id} does not cover {expected_intent}"))
                    elif document_id not in eligible_ids:
                        relationship_issues.append(ValidationIssue("hard-negative-ineligible", f"{document_id} is not eligible"))

        if not relationship_issues and isinstance(relationship_id, str):
            valid_relationship_ids.add(relationship_id)
        issues.extend(relationship_issues)
    return issues, relationships, valid_relationship_ids


def validate_kb(
    documents: Sequence[Mapping[str, Any]],
    config: Mapping[str, Any],
    hard_negative_matrix: Mapping[str, Any],
    *,
    canonical_categories: Iterable[str],
    document_plan: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a full KB and return machine-readable evidence without writing files."""
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    try:
        as_of_date = date.fromisoformat(config["evaluation_as_of_date"])
    except (KeyError, TypeError, ValueError) as exc:
        raise KBValidationError("evaluation_as_of_date must be a valid fixed ISO date") from exc

    locked_mapping = config["locked_intent_slugs"]
    category_set = set(canonical_categories)
    missing_upstream = sorted(set(locked_mapping) - category_set)
    if missing_upstream:
        errors.append(ValidationIssue("upstream-intents", f"Locked intents absent upstream: {missing_upstream}"))

    for document in documents:
        errors.extend(_validate_document(document, config, as_of_date))

    ids = [str(document.get("document_id")) for document in documents]
    duplicate_ids = sorted(identifier for identifier, count in Counter(ids).items() if count > 1)
    if duplicate_ids:
        errors.append(ValidationIssue("duplicate-document-id", f"Duplicate IDs: {duplicate_ids}"))
    if ids != sorted(ids):
        errors.append(ValidationIssue("document-order", "JSONL documents must be ordered by document_id"))

    by_id = {str(document.get("document_id")): document for document in documents}
    for document in documents:
        document_id = str(document.get("document_id"))
        supersedes = document.get("supersedes_document_id")
        if supersedes is not None:
            target = by_id.get(str(supersedes))
            if target is None:
                errors.append(ValidationIssue("broken-supersedes", f"Missing reference: {supersedes}", document_id))
            elif target.get("document_family_id") != document.get("document_family_id"):
                errors.append(ValidationIssue("cross-family-supersedes", f"Reference crosses family: {supersedes}", document_id))
        if _detect_cycle(document_id, by_id):
            errors.append(ValidationIssue("supersession-cycle", "Version chain contains a cycle", document_id))

    eligible: list[Mapping[str, Any]] = []
    for document in documents:
        try:
            if is_document_eligible(document, as_of_date):
                eligible.append(document)
        except KBValidationError:
            pass

    eligible_by_family: dict[str, list[str]] = defaultdict(list)
    for document in eligible:
        eligible_by_family[str(document["document_family_id"])].append(str(document["document_id"]))
    for family_id, active_ids in sorted(eligible_by_family.items()):
        if len(active_ids) > 1:
            errors.append(
                ValidationIssue("multiple-active-approved", f"{family_id} has active documents {active_ids}")
            )

    structurally_valid_families: set[str] = set()
    if document_plan is not None:
        lifecycle_issues, structurally_valid_families = _validate_version_families(
            document_plan, by_id, eligible_by_family
        )
        errors.extend(lifecycle_issues)

    for document in documents:
        status = document.get("status")
        if status in {"DRAFT", "EXPIRED"}:
            try:
                if is_document_eligible(document, as_of_date):
                    errors.append(ValidationIssue("ineligible-status-leak", f"{status} became eligible", str(document.get("document_id"))))
            except KBValidationError:
                pass

    acceptance = config["acceptance"]
    count = len(documents)
    if not acceptance["minimum_documents"] <= count <= acceptance["maximum_documents"]:
        errors.append(ValidationIssue("document-count", f"Document count {count} outside accepted range"))
    status_counts = Counter(str(document.get("status")) for document in documents)
    type_counts = Counter(str(document.get("document_type")) for document in documents)
    if dict(sorted(status_counts.items())) != dict(sorted(acceptance["required_status_counts"].items())):
        errors.append(ValidationIssue("status-counts", f"Actual status counts: {dict(status_counts)}"))
    if dict(sorted(type_counts.items())) != dict(sorted(acceptance["required_document_type_counts"].items())):
        errors.append(ValidationIssue("document-type-counts", f"Actual type counts: {dict(type_counts)}"))

    intent_coverage: dict[str, dict[str, Any]] = {}
    for intent in locked_mapping:
        matching = [document for document in eligible if intent in document.get("intent_scope", [])]
        types = sorted({str(document["document_type"]) for document in matching})
        intent_coverage[intent] = {
            "eligible_approved_count": len(matching),
            "document_types": types,
            "document_type_count": len(types),
            "document_ids": sorted(str(document["document_id"]) for document in matching),
        }
        if len(matching) < acceptance["minimum_eligible_documents_per_intent"]:
            errors.append(ValidationIssue("intent-coverage", f"{intent} has only {len(matching)} eligible documents"))
        if len(types) < acceptance["minimum_document_types_per_intent"]:
            errors.append(ValidationIssue("intent-type-coverage", f"{intent} has only document types {types}"))

    families: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for document in documents:
        families[str(document.get("document_family_id"))].append(document)
    complete_families = (
        sorted(structurally_valid_families)
        if document_plan is not None
        else sorted(
            family_id
            for family_id, members in families.items()
            if {"EXPIRED", "APPROVED", "DRAFT"} <= {str(member.get("status")) for member in members}
        )
    )
    if len(complete_families) < acceptance["minimum_complete_version_families"]:
        errors.append(ValidationIssue("version-family-count", f"Only {len(complete_families)} complete families"))

    content_groups: dict[str, list[str]] = defaultdict(list)
    for document in documents:
        content_groups[_normalized_content(document)].append(str(document.get("document_id")))
    duplicate_groups = [sorted(group) for group in content_groups.values() if len(group) > 1]
    if duplicate_groups:
        errors.append(ValidationIssue("normalized-duplicate", f"Duplicate content groups: {duplicate_groups}"))

    threshold = float(config["near_duplicate"]["candidate_threshold"])
    near_duplicate_candidates: list[dict[str, Any]] = []
    for left_index, left in enumerate(documents):
        left_text = _normalized_content(left)
        for right in documents[left_index + 1 :]:
            score = _token_jaccard(left_text, _normalized_content(right))
            if score >= threshold and left_text != _normalized_content(right):
                near_duplicate_candidates.append(
                    {
                        "left_document_id": left.get("document_id"),
                        "right_document_id": right.get("document_id"),
                        "token_jaccard": round(score, 6),
                    }
                )
    near_duplicate_candidates.sort(
        key=lambda row: (-row["token_jaccard"], row["left_document_id"], row["right_document_id"])
    )

    eligible_ids = {str(document.get("document_id")) for document in eligible}
    hard_negative_issues, relationships, structurally_valid_relationship_ids = (
        _validate_hard_negative_relationships(
            hard_negative_matrix, locked_mapping, by_id, eligible_ids
        )
    )
    errors.extend(hard_negative_issues)
    if len(relationships) < acceptance["minimum_hard_negative_relationships"]:
        errors.append(ValidationIssue("hard-negative-count", f"Only {len(relationships)} relationships"))

    result = {
        "validation_result": "PASS" if not errors else "FAIL",
        "errors": [issue.as_dict() for issue in errors],
        "warnings": [issue.as_dict() for issue in warnings],
        "summary": {
            "document_count": count,
            "eligible_document_count": len(eligible),
            "status_counts": dict(sorted(status_counts.items())),
            "document_type_counts": dict(sorted(type_counts.items())),
            "locked_intent_count": len(locked_mapping),
            "complete_version_family_count": len(complete_families),
            "complete_version_families": complete_families,
            "hard_negative_relationship_count": len(relationships),
            "exact_or_normalized_duplicate_group_count": len(duplicate_groups),
            "near_duplicate_candidate_count": len(near_duplicate_candidates),
        },
        "intent_coverage": intent_coverage,
        "eligible_document_ids": sorted(str(document["document_id"]) for document in eligible),
        "near_duplicate": {
            "method": config["near_duplicate"]["method"],
            "threshold": threshold,
            "candidates": near_duplicate_candidates,
            "manual_review_required": bool(near_duplicate_candidates),
        },
        "canonical_dataset_sha256": canonical_dataset_sha256(documents),
    }
    if document_plan is not None:
        first_28_gate = _evaluate_first_28_quality_gate(
            documents,
            config,
            hard_negative_matrix,
            document_plan,
            as_of_date,
            structurally_valid_families,
            structurally_valid_relationship_ids,
        )
        result["first_28_quality_gate"] = first_28_gate
        if first_28_gate["result"] != "PASS":
            result["errors"].append(
                {
                    "code": "first-28-quality-gate",
                    "message": "; ".join(first_28_gate["errors"]),
                }
            )
            result["validation_result"] = "FAIL"
    return result


def write_validation_outputs(
    root: Path,
    config_path: Path,
    config: Mapping[str, Any],
    report: Mapping[str, Any],
) -> dict[str, Any]:
    outputs = config["validation_outputs"]
    report_path = root / outputs["report"]
    manifest_path = root / outputs["manifest"]
    coverage_path = root / outputs["coverage"]
    for path in (report_path, manifest_path, coverage_path):
        path.parent.mkdir(parents=True, exist_ok=True)

    report_payload = dict(report)
    report_payload["validation_timestamp"] = datetime.now(timezone.utc).isoformat()
    report_path.write_text(
        json.dumps(report_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with coverage_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "canonical_intent",
                "intent_slug",
                "eligible_approved_count",
                "document_type_count",
                "document_types",
                "document_ids",
            ],
        )
        writer.writeheader()
        for intent, values in report["intent_coverage"].items():
            writer.writerow(
                {
                    "canonical_intent": intent,
                    "intent_slug": config["locked_intent_slugs"][intent],
                    "eligible_approved_count": values["eligible_approved_count"],
                    "document_type_count": values["document_type_count"],
                    "document_types": "|".join(values["document_types"]),
                    "document_ids": "|".join(values["document_ids"]),
                }
            )

    paths_to_hash = {
        "config_sha256": config_path,
        "schema_sha256": root / config["schema_path"],
        "intent_definitions_sha256": root / config["intent_definitions_path"],
        "hard_negative_matrix_sha256": root / config["hard_negative_matrix_path"],
        "document_plan_sha256": root / config["document_plan_path"],
        "generation_guideline_sha256": root / config["generation_guideline_path"],
    }
    manifest = {
        "dataset_name": config["dataset_name"],
        "kb_version": config["kb_version"],
        "evaluation_as_of_date": config["evaluation_as_of_date"],
        "canonical_dataset_sha256": report["canonical_dataset_sha256"],
        "document_count": report["summary"]["document_count"],
        "eligible_document_count": report["summary"]["eligible_document_count"],
        "status_counts": report["summary"]["status_counts"],
        "document_type_counts": report["summary"]["document_type_counts"],
        "intent_coverage": report["intent_coverage"],
        "complete_version_families": report["summary"]["complete_version_families"],
        "hard_negative_relationship_count": report["summary"]["hard_negative_relationship_count"],
        "validation_result": report["validation_result"],
        "validation_timestamp": report_payload["validation_timestamp"],
        "stable_identity_excludes_validation_timestamp": True,
        **{name: file_sha256(path) for name, path in paths_to_hash.items()},
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
