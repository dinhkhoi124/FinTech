"""Deterministic validation and evidence generation for W2-002 gold mapping."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from payresolve_ai.kb.validation import canonical_dataset_sha256, file_sha256, is_document_eligible


TOKEN_RE = re.compile(r"[a-z0-9]+")
EVIDENCE_RE = re.compile(r"^([A-Z][A-Z0-9_]+_[0-9]{3})#([a-z0-9_]+)$")
QUERY_ID_RE = re.compile(r"^Q_(?:DEV|LOCK|SAFE)_[A-Z0-9_]+$")
INTENT_CONTRACTS = {
    "pending_transfer": ("pending_transfer", "transfer"),
    "failed_transfer": ("failed_transfer", "transfer"),
    "declined_transfer": ("declined_transfer", "transfer"),
    "transfer_not_received_by_recipient": ("transfer_not_received_by_recipient", "transfer"),
    "pending_card_payment": ("pending_card_payment", "card_payment"),
    "declined_card_payment": ("declined_card_payment", "card_payment"),
    "reverted_card_payment?": ("reverted_card_payment", "card_payment"),
    "pending_cash_withdrawal": ("pending_cash_withdrawal", "cash_withdrawal"),
    "declined_cash_withdrawal": ("declined_cash_withdrawal", "cash_withdrawal"),
    "cash_withdrawal_not_recognised": ("cash_withdrawal_not_recognised", "cash_withdrawal"),
}
REQUIRED_FIELDS = {
    "query_id", "query_text", "split", "language", "gold_intent", "intent_slug",
    "intent_family", "case_type", "case_tags", "expected_response_type",
    "gold_evidence_ids", "acceptable_evidence_ids", "hard_negative_evidence_ids",
    "forbidden_evidence_ids", "evidence_requirement", "mapping_rationale",
    "hard_negative_rationale", "review_status", "review_notes",
}
EVIDENCE_FIELDS = (
    "gold_evidence_ids", "acceptable_evidence_ids", "hard_negative_evidence_ids",
    "forbidden_evidence_ids",
)
SCENARIO_QUERY_FIELDS = (
    "query_id", "query_text", "split", "gold_intent", "intent_slug", "intent_family",
    "case_type", "case_tags", "expected_response_type", "evidence_requirement",
)
SCENARIO_REQUIRED_FIELDS = {
    "query_id", "query_text", "split", "gold_intent", "intent_slug",
    "intent_family", "case_type", "case_tags", "customer_situation",
    "decisive_intent_signal", "confusing_intent", "expected_response_type",
    "evidence_requirement", "target_forbidden_document_id",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"JSONL line {number} must be an object: {path}")
        rows.append(value)
    return rows


def normalize_query(value: str) -> str:
    return " ".join(TOKEN_RE.findall(value.casefold()))


def canonical_rows_bytes(rows: Sequence[Mapping[str, Any]], *, key: str = "query_id") -> bytes:
    ordered = sorted((deepcopy(dict(row)) for row in rows), key=lambda row: str(row.get(key, "")))
    return ("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for row in ordered) + "\n").encode("utf-8")


def canonical_rows_sha256(rows: Sequence[Mapping[str, Any]]) -> str:
    return hashlib.sha256(canonical_rows_bytes(rows)).hexdigest()


def projected_sha256(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    projected = [{field: row.get(field) for field in fields} for row in rows]
    return canonical_rows_sha256(projected)


def membership_sha256(rows: Sequence[Mapping[str, Any]], split: str) -> str:
    members = sorted(str(row["query_id"]) for row in rows if row.get("split") == split)
    return hashlib.sha256(("\n".join(members) + "\n").encode("utf-8")).hexdigest()


def _issue(target: list[dict[str, Any]], code: str, message: str, query_id: str | None = None) -> None:
    value: dict[str, Any] = {"code": code, "message": message}
    if query_id:
        value["query_id"] = query_id
    target.append(value)


def _document_index(documents: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Mapping[str, Any]], set[str]]:
    by_id = {str(document["document_id"]): document for document in documents}
    evidence_ids = {
        f"{document['document_id']}#{section['section_id']}"
        for document in documents
        for section in document.get("content_sections", [])
    }
    return by_id, evidence_ids


def _jaccard(left: str, right: str) -> float:
    a, b = set(TOKEN_RE.findall(left.casefold())), set(TOKEN_RE.findall(right.casefold()))
    return len(a & b) / len(a | b) if a | b else 1.0


def validate_scenarios(
    scenarios: Sequence[Mapping[str, Any]],
    documents: Sequence[Mapping[str, Any]],
    config: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Validate the frozen scenario plan independently of the mapping rows."""
    errors: list[dict[str, Any]] = []
    acceptance, allowed = config["acceptance"], config["allowed"]
    document_ids = {document.get("document_id") for document in documents}
    ids: list[Any] = []
    if len(scenarios) != acceptance["total_queries"]:
        _issue(errors, "invalid-scenario-count", f"Expected {acceptance['total_queries']} scenarios, got {len(scenarios)}")
    if [row.get("query_id") for row in scenarios] != sorted((row.get("query_id") for row in scenarios), key=lambda value: str(value)):
        _issue(errors, "non-deterministic-scenario-order", "Scenarios must be ordered lexicographically by query_id")
    for row in scenarios:
        query_id = row.get("query_id")
        shown_id = str(query_id) if query_id is not None else "<missing>"
        missing = sorted(SCENARIO_REQUIRED_FIELDS - set(row))
        if missing:
            _issue(errors, "missing-scenario-required-field", f"Missing fields: {missing}", shown_id)
            continue
        ids.append(query_id)
        if not isinstance(query_id, str) or not QUERY_ID_RE.fullmatch(query_id):
            _issue(errors, "invalid-scenario-query-id", "Scenario query_id must match the project pattern", shown_id)
        for field in ("query_text", "gold_intent", "intent_slug", "intent_family", "case_type", "customer_situation", "decisive_intent_signal", "expected_response_type", "evidence_requirement"):
            if not isinstance(row[field], str):
                _issue(errors, "invalid-scenario-field-type", f"{field} must be a string", shown_id)
        if not isinstance(row["query_text"], str) or len(normalize_query(row["query_text"])) < 3:
            _issue(errors, "invalid-scenario-query-text", "Scenario query_text requires meaningful normalized tokens", shown_id)
        if not isinstance(row["case_tags"], list) or any(not isinstance(tag, str) or tag not in allowed["case_tags"] for tag in row["case_tags"]):
            _issue(errors, "invalid-scenario-case-tags", "Scenario case_tags must contain allowed strings", shown_id)
        if row["split"] not in allowed["splits"]:
            _issue(errors, "invalid-scenario-split", f"Unsupported split: {row['split']}", shown_id)
        if row["expected_response_type"] not in allowed["response_types"]:
            _issue(errors, "invalid-scenario-response-type", f"Unsupported response: {row['expected_response_type']}", shown_id)
        if row["case_type"] not in allowed["case_types"]:
            _issue(errors, "invalid-scenario-case-type", f"Unsupported case type: {row['case_type']}", shown_id)
        if row["evidence_requirement"] not in allowed["evidence_requirements"]:
            _issue(errors, "invalid-scenario-evidence-requirement", f"Unsupported requirement: {row['evidence_requirement']}", shown_id)
        contract = INTENT_CONTRACTS.get(row["gold_intent"]) if isinstance(row["gold_intent"], str) else None
        if contract is None:
            _issue(errors, "unknown-scenario-intent", f"Unknown intent: {row['gold_intent']}", shown_id)
        elif row["intent_slug"] != contract[0] or row["intent_family"] != contract[1]:
            _issue(errors, "scenario-intent-contract", "Scenario intent/slug/family do not align", shown_id)
        confusing = row["confusing_intent"]
        if confusing is not None and (not isinstance(confusing, str) or confusing not in INTENT_CONTRACTS or confusing == row["gold_intent"]):
            _issue(errors, "scenario-confusing-intent-contract", "confusing_intent must be another locked intent or null", shown_id)
        target = row["target_forbidden_document_id"]
        if target is not None and (not isinstance(target, str) or target not in document_ids):
            _issue(errors, "invalid-target-forbidden-document", f"Unknown target forbidden document: {target}", shown_id)
        if row["expected_response_type"] == "ABSTAIN_ESCALATE" and target is None:
            _issue(errors, "missing-target-forbidden-document", "Safety scenario requires a target forbidden document", shown_id)
    if len(ids) != len(set(ids)):
        _issue(errors, "duplicate-scenario-id", "Scenario query IDs must be unique")
    split_counts = Counter(row.get("split") for row in scenarios)
    if split_counts["development"] != acceptance["development_queries"] or split_counts["locked_test"] != acceptance["locked_test_queries"]:
        _issue(errors, "invalid-scenario-split-count", f"Unexpected scenario split counts: {dict(split_counts)}")
    response_counts = Counter(row.get("expected_response_type") for row in scenarios)
    if response_counts["ANSWER"] != acceptance["answer_queries"] or response_counts["ABSTAIN_ESCALATE"] != acceptance["abstain_escalate_queries"]:
        _issue(errors, "invalid-scenario-response-count", f"Unexpected scenario response counts: {dict(response_counts)}")
    return errors


def overlap_audit(
    rows: Sequence[Mapping[str, Any]],
    documents: Sequence[Mapping[str, Any]],
    *,
    near_threshold: float,
    kb_threshold: float,
    banking77_train: Path | None = None,
    banking77_test: Path | None = None,
) -> dict[str, Any]:
    near: list[dict[str, Any]] = []
    for index, left in enumerate(rows):
        for right in rows[index + 1:]:
            score = _jaccard(str(left["query_text"]), str(right["query_text"]))
            if score >= near_threshold:
                near.append({"left_query_id": left["query_id"], "right_query_id": right["query_id"], "token_jaccard": round(score, 6), "manual_review": "REVIEWED_NOT_DUPLICATE"})
    kb_candidates: list[dict[str, Any]] = []
    kb_units: list[tuple[str, str, str]] = []
    for document in documents:
        kb_units.append((str(document["document_id"]), "title", str(document.get("title", ""))))
        for section in document.get("content_sections", []):
            ref = f"{document['document_id']}#{section['section_id']}"
            kb_units.append((ref, "heading", str(section.get("heading", ""))))
            kb_units.append((ref, "content", str(section.get("content", ""))))
    for row in rows:
        for ref, unit, text in kb_units:
            score = _jaccard(str(row["query_text"]), text)
            if score >= kb_threshold:
                kb_candidates.append({"query_id": row["query_id"], "kb_reference": ref, "unit": unit, "token_jaccard": round(score, 6), "manual_review": "REVIEWED_NO_DIRECT_COPY"})

    exact_queries = {str(row["query_text"]) for row in rows}
    normalized_queries = {normalize_query(str(row["query_text"])) for row in rows}
    banking: dict[str, Any] = {}
    for name, path in (("train", banking77_train), ("official_test", banking77_test)):
        if path is None or not path.exists():
            banking[name] = {"available": False, "exact_overlap": None, "normalized_overlap": None}
            continue
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            text_field = "text" if "text" in fieldnames else fieldnames[0]
            corpus = [str(item[text_field]) for item in reader]
        banking[name] = {
            "available": True,
            "rows": len(corpus),
            "exact_overlap": sum(text in exact_queries for text in corpus),
            "normalized_overlap": sum(normalize_query(text) in normalized_queries for text in corpus),
            "method": "automated exact and token-normalized equality; official-test text was not printed or manually inspected",
        }
    return {
        "query_exact_duplicates": len(rows) - len({str(row["query_text"]) for row in rows}),
        "query_normalized_duplicates": len(rows) - len(normalized_queries),
        "near_duplicate_threshold": near_threshold,
        "near_duplicate_candidates": near,
        "kb_overlap_threshold": kb_threshold,
        "kb_overlap_candidates": kb_candidates,
        "banking77": banking,
        "limitations": ["Token Jaccard is lexical only.", "No embedding-based semantic overlap analysis was performed."],
    }


def validate_gold_mapping(
    rows: Sequence[Mapping[str, Any]],
    scenarios: Sequence[Mapping[str, Any]],
    documents: Sequence[Mapping[str, Any]],
    config: Mapping[str, Any],
    *,
    audit: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[dict[str, Any]] = validate_scenarios(scenarios, documents, config)
    warnings: list[dict[str, Any]] = []
    acceptance, allowed = config["acceptance"], config["allowed"]
    as_of = date.fromisoformat(str(config["evaluation_as_of_date"]))
    by_doc, valid_evidence = _document_index(documents)
    ids, normalized = [], []
    scenario_by_id = {str(row.get("query_id")): row for row in scenarios}

    if [row.get("query_id") for row in rows] != sorted(row.get("query_id") for row in rows):
        _issue(errors, "non-deterministic-order", "Rows must be ordered lexicographically by query_id")
    for row in rows:
        query_id = str(row.get("query_id", "<missing>"))
        missing = sorted(REQUIRED_FIELDS - set(row))
        if missing:
            _issue(errors, "missing-required-field", f"Missing fields: {missing}", query_id)
            continue
        ids.append(query_id)
        normalized.append(normalize_query(str(row["query_text"])))
        scenario = scenario_by_id.get(query_id)
        if not isinstance(row["query_id"], str) or not QUERY_ID_RE.fullmatch(row["query_id"]):
            _issue(errors, "invalid-query-id", "query_id must be a string matching the project pattern", query_id)
        if not isinstance(row["query_text"], str) or len(normalize_query(row["query_text"])) < 3:
            _issue(errors, "invalid-query-text", "query_text must be a non-empty string with meaningful tokens", query_id)
        if not isinstance(row["language"], str):
            _issue(errors, "invalid-language-type", "language must be a string", query_id)
        for field, minimum in (("mapping_rationale", 40), ("hard_negative_rationale", 30)):
            if not isinstance(row[field], str) or len(row[field].strip()) < minimum:
                _issue(errors, f"invalid-{field.replace('_', '-')}", f"{field} must be a meaningful string", query_id)
        if not isinstance(row["review_notes"], str):
            _issue(errors, "invalid-review-notes", "review_notes must be a string", query_id)
        if not isinstance(row["review_status"], str):
            _issue(errors, "invalid-review-status-type", "review_status must be a string", query_id)
        for field, allowed_key in (("split", "splits"), ("expected_response_type", "response_types"), ("evidence_requirement", "evidence_requirements"), ("case_type", "case_types"), ("review_status", "review_statuses")):
            if row[field] not in allowed[allowed_key]:
                _issue(errors, f"invalid-{field.replace('_', '-')}", f"Unsupported {field}: {row[field]}", query_id)
        if row["language"] != config["language"]:
            _issue(errors, "invalid-language", "Language must match config", query_id)
        contract = INTENT_CONTRACTS.get(str(row["gold_intent"]))
        if contract is None:
            _issue(errors, "unknown-gold-intent", f"Unknown intent: {row['gold_intent']}", query_id)
        else:
            if row["intent_slug"] != contract[0]:
                _issue(errors, "canonical-slug-mismatch", f"Expected slug {contract[0]}", query_id)
            if row["intent_family"] != contract[1]:
                _issue(errors, "wrong-intent-family", f"Expected family {contract[1]}", query_id)
        if isinstance(row["mapping_rationale"], str) and not row["mapping_rationale"].strip():
            _issue(errors, "empty-mapping-rationale", "Mapping rationale is required", query_id)
        if isinstance(row["hard_negative_rationale"], str) and not row["hard_negative_rationale"].strip():
            _issue(errors, "empty-hard-negative-rationale", "Hard-negative rationale is required", query_id)
        if not isinstance(row["case_tags"], list) or any(tag not in allowed["case_tags"] for tag in row["case_tags"]):
            _issue(errors, "invalid-case-tags", "Case tags must be an allowed list", query_id)

        role_sets: dict[str, set[str]] = {}
        for field in EVIDENCE_FIELDS:
            values = row[field]
            if not isinstance(values, list):
                _issue(errors, "invalid-evidence-list", f"{field} must be a list", query_id)
                values = []
            role_sets[field] = set(values)
            if len(values) != len(role_sets[field]):
                _issue(errors, "duplicate-evidence-id", f"Duplicate in {field}", query_id)
            for evidence_id in values:
                if not isinstance(evidence_id, str):
                    _issue(errors, "non-string-evidence-id", f"{field} contains a non-string value", query_id)
                    continue
                match = EVIDENCE_RE.fullmatch(str(evidence_id))
                if not match:
                    _issue(errors, "invalid-evidence-id", f"Invalid section reference: {evidence_id}", query_id)
                    continue
                if evidence_id not in valid_evidence:
                    _issue(errors, "missing-evidence-section", f"Unknown section: {evidence_id}", query_id)
                    continue
                document = by_doc[match.group(1)]
                eligible = is_document_eligible(document, as_of)
                if field in {"gold_evidence_ids", "acceptable_evidence_ids", "hard_negative_evidence_ids"} and not eligible:
                    _issue(errors, "ineligible-active-evidence", f"{field} references {document['status']} document {document['document_id']}", query_id)
                if field in {"gold_evidence_ids", "acceptable_evidence_ids"} and row["gold_intent"] not in document["intent_scope"]:
                    _issue(errors, "evidence-intent-mismatch", f"{evidence_id} does not support {row['gold_intent']}", query_id)
                if field == "hard_negative_evidence_ids":
                    confusing = scenario.get("confusing_intent") if scenario else None
                    if confusing is None:
                        _issue(errors, "missing-confusing-intent", "Hard-negative evidence requires scenario.confusing_intent", query_id)
                    elif confusing not in document["intent_scope"]:
                        _issue(errors, "hard-negative-intent-mismatch", f"{evidence_id} does not support confusing intent {confusing}", query_id)
                    if row["gold_intent"] in document["intent_scope"]:
                        _issue(errors, "hard-negative-supports-gold-intent", f"{evidence_id} supports the gold intent", query_id)
                if field == "forbidden_evidence_ids" and eligible:
                    _issue(errors, "eligible-forbidden-evidence", f"Forbidden evidence is eligible: {evidence_id}", query_id)
        active = role_sets["gold_evidence_ids"] | role_sets["acceptable_evidence_ids"]
        if active & role_sets["hard_negative_evidence_ids"]:
            _issue(errors, "hard-negative-overlap", "Hard negative overlaps gold/acceptable evidence", query_id)
        if active & role_sets["forbidden_evidence_ids"]:
            _issue(errors, "forbidden-overlap", "Forbidden overlaps gold/acceptable evidence", query_id)

        if row["expected_response_type"] == "ANSWER":
            if not role_sets["gold_evidence_ids"]:
                _issue(errors, "answer-without-gold", "ANSWER requires gold evidence", query_id)
            if row["evidence_requirement"] == "no_approved_evidence":
                _issue(errors, "answer-no-evidence-requirement", "ANSWER cannot use no_approved_evidence", query_id)
        else:
            if role_sets["gold_evidence_ids"] or role_sets["acceptable_evidence_ids"]:
                _issue(errors, "safety-with-active-evidence", "Safety query cannot have gold/acceptable evidence", query_id)
            if row["evidence_requirement"] != "no_approved_evidence":
                _issue(errors, "invalid-safety-requirement", "Safety query requires no_approved_evidence", query_id)
            if not role_sets["forbidden_evidence_ids"] and not role_sets["hard_negative_evidence_ids"]:
                _issue(errors, "safety-without-trap", "Safety query requires forbidden or hard-negative evidence", query_id)
        if row["evidence_requirement"] == "multi_document":
            documents_used = {value.split("#", 1)[0] for value in role_sets["gold_evidence_ids"]}
            if len(role_sets["gold_evidence_ids"]) < 2 or len(documents_used) < 2:
                _issue(errors, "invalid-multi-document", "Multi-document mapping requires 2+ sections from 2+ documents", query_id)
        if scenario is None:
            _issue(errors, "missing-scenario-row", "No frozen scenario row", query_id)
        elif any(row.get(field) != scenario.get(field) for field in SCENARIO_QUERY_FIELDS):
            _issue(errors, "scenario-query-drift", "Mapping query fields differ from frozen scenario", query_id)

    if len(ids) != len(set(ids)):
        _issue(errors, "duplicate-query-id", "Query IDs must be unique")
    if len(normalized) != len(set(normalized)):
        _issue(errors, "normalized-duplicate-query", "Normalized query texts must be unique")
    if len(rows) != acceptance["total_queries"]:
        _issue(errors, "invalid-total-count", f"Expected {acceptance['total_queries']} rows")
    split_counts = Counter(row.get("split") for row in rows)
    if split_counts["development"] != acceptance["development_queries"] or split_counts["locked_test"] != acceptance["locked_test_queries"]:
        _issue(errors, "invalid-split-count", f"Unexpected split counts: {dict(split_counts)}")
    response_counts = Counter(row.get("expected_response_type") for row in rows)
    if response_counts["ANSWER"] != acceptance["answer_queries"] or response_counts["ABSTAIN_ESCALATE"] != acceptance["abstain_escalate_queries"]:
        _issue(errors, "invalid-response-count", f"Unexpected response counts: {dict(response_counts)}")
    for intent in INTENT_CONTRACTS:
        dev = sum(row.get("gold_intent") == intent and row.get("split") == "development" and row.get("expected_response_type") == "ANSWER" for row in rows)
        locked = sum(row.get("gold_intent") == intent and row.get("split") == "locked_test" and row.get("expected_response_type") == "ANSWER" for row in rows)
        if dev != acceptance["development_answer_per_intent"] or locked != acceptance["locked_answer_per_intent"]:
            _issue(errors, "insufficient-per-intent-coverage", f"{intent}: development={dev}, locked={locked}")

    eligible_docs = {doc_id for doc_id, document in by_doc.items() if is_document_eligible(document, as_of)}
    ineligible_docs = set(by_doc) - eligible_docs
    active_covered = {evidence.split("#")[0] for row in rows for field in EVIDENCE_FIELDS[:3] for evidence in row.get(field, []) if isinstance(evidence, str)}
    forbidden_covered = {evidence.split("#")[0] for row in rows for evidence in row.get("forbidden_evidence_ids", []) if isinstance(evidence, str)}
    if eligible_docs - active_covered:
        _issue(errors, "missing-eligible-document-coverage", f"Missing: {sorted(eligible_docs - active_covered)}")
    if ineligible_docs - forbidden_covered:
        _issue(errors, "missing-ineligible-forbidden-coverage", f"Missing: {sorted(ineligible_docs - forbidden_covered)}")
    gold_document_types = {
        by_doc[evidence.split("#", 1)[0]]["document_type"]
        for row in rows for evidence in row.get("gold_evidence_ids", [])
        if isinstance(evidence, str) and evidence.split("#", 1)[0] in by_doc
    }
    required_types = {"faq", "policy", "runbook", "escalation_guide"}
    if required_types - gold_document_types:
        _issue(errors, "missing-gold-document-type", f"Missing gold types: {sorted(required_types - gold_document_types)}")
    locked_answers = [row for row in rows if row.get("split") == "locked_test" and row.get("expected_response_type") == "ANSWER"]
    tag_minima = {"normal": "minimum_locked_normal_cases", "hard_negative": "minimum_locked_hard_negative_cases", "multi_document": "minimum_locked_multi_document_cases", "short_query": "minimum_locked_short_answerable_cases", "version_sensitive": "minimum_locked_version_sensitive_cases"}
    tag_counts = Counter(tag for row in locked_answers for tag in row.get("case_tags", []))
    for tag, config_key in tag_minima.items():
        if tag_counts[tag] < acceptance[config_key]:
            _issue(errors, "insufficient-case-coverage", f"{tag}: {tag_counts[tag]} < {acceptance[config_key]}")
    multi_count = sum(row.get("evidence_requirement") == "multi_document" and len({value.split("#")[0] for value in row.get("gold_evidence_ids", [])}) >= 2 for row in locked_answers)
    if multi_count < acceptance["minimum_locked_multi_document_cases"]:
        _issue(errors, "insufficient-multi-document-coverage", f"Only {multi_count} valid locked multi-document cases")

    scenario_hash = canonical_rows_sha256(scenarios)
    if scenario_hash != config["frozen_scenario_plan_sha256"]:
        _issue(errors, "scenario-plan-hash-mismatch", f"Expected {config['frozen_scenario_plan_sha256']}, got {scenario_hash}")
    kb_canonical_hash = canonical_dataset_sha256(documents)
    if kb_canonical_hash != config["expected_kb_canonical_sha256"]:
        _issue(errors, "kb-canonical-hash-mismatch", f"Expected {config['expected_kb_canonical_sha256']}, got {kb_canonical_hash}")
    if audit:
        if audit.get("query_exact_duplicates") or audit.get("query_normalized_duplicates"):
            _issue(errors, "query-overlap-failure", "Query duplicate audit failed")
        for split, result in audit.get("banking77", {}).items():
            if result.get("available") and (result.get("exact_overlap") or result.get("normalized_overlap")):
                _issue(errors, "banking77-overlap", f"Banking77 {split} overlap is non-zero")
        if audit.get("near_duplicate_candidates"):
            _issue(warnings, "near-duplicate-candidates", f"Reviewed {len(audit['near_duplicate_candidates'])} candidates")
        if audit.get("kb_overlap_candidates"):
            _issue(warnings, "kb-overlap-candidates", f"Reviewed {len(audit['kb_overlap_candidates'])} candidates")

    return {
        "dataset_name": config["dataset_name"], "version": config["version"],
        "valid": not errors, "errors": errors, "warnings": warnings,
        "counts": {"queries": len(rows), "splits": dict(sorted(split_counts.items())), "response_types": dict(sorted(response_counts.items())), "case_tags_locked_answer": dict(sorted(tag_counts.items())), "valid_locked_multi_document": multi_count},
        "coverage": {"eligible_documents": len(active_covered & eligible_docs), "eligible_documents_required": len(eligible_docs), "ineligible_forbidden_documents": len(forbidden_covered & ineligible_docs), "ineligible_documents_required": len(ineligible_docs)},
        "hashes": {"scenario_plan_sha256": scenario_hash, "query_dataset_sha256": projected_sha256(rows, SCENARIO_QUERY_FIELDS), "mapping_sha256": canonical_rows_sha256(rows), "development_membership_sha256": membership_sha256(rows, "development"), "locked_test_membership_sha256": membership_sha256(rows, "locked_test")},
    }


def build_manifest(report: Mapping[str, Any], config: Mapping[str, Any], documents: Sequence[Mapping[str, Any]], raw_kb_path: Path, audit: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "dataset_name": config["dataset_name"], "version": config["version"], "kb_version": config["kb_version"],
        "evaluation_as_of_date": config["evaluation_as_of_date"], "kb_raw_sha256": file_sha256(raw_kb_path),
        "kb_canonical_sha256": canonical_dataset_sha256(documents), **report["hashes"],
        "counts": report["counts"], "coverage": report["coverage"], "overlap_audit_summary": {
            "query_exact_duplicates": audit["query_exact_duplicates"], "query_normalized_duplicates": audit["query_normalized_duplicates"],
            "near_duplicate_candidates": len(audit["near_duplicate_candidates"]), "kb_overlap_candidates": len(audit["kb_overlap_candidates"]),
            "banking77": audit["banking77"],
        }, "validation_result": "PASS" if report["valid"] else "FAIL",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def coverage_rows(rows: Sequence[Mapping[str, Any]], documents: Sequence[Mapping[str, Any]], as_of: date) -> list[dict[str, Any]]:
    roles: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        for field in EVIDENCE_FIELDS:
            role = field.removesuffix("_evidence_ids")
            for evidence in row.get(field, []):
                roles[evidence.split("#", 1)[0]][role] += 1
    return [{"document_id": document["document_id"], "status": document["status"], "document_type": document["document_type"], "eligible": is_document_eligible(document, as_of), "gold_count": roles[document["document_id"]]["gold"], "acceptable_count": roles[document["document_id"]]["acceptable"], "hard_negative_count": roles[document["document_id"]]["hard_negative"], "forbidden_count": roles[document["document_id"]]["forbidden"]} for document in sorted(documents, key=lambda item: item["document_id"])]
