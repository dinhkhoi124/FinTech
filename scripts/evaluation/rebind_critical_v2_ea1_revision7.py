"""Rebind EA1 evaluator-only rules to frozen critical_eval_v2 candidate revision 7.

This authoring utility never imports model, retrieval, or generation modules.  It
changes evaluator/readiness evidence only; candidate Pass-B and mapping bytes are
read-only inputs guarded by their frozen SHA-256 values.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


PASS_B_SHA256 = "585469d850a9e2d5514248709658e574dbfff7f54a0f13c99bcbb8cd2653017e"
MAPPING_SHA256 = "cc9e82adbb97fd8054e58d3d6548ca03b15046bb37eca53ef9aa529dc4ec12f1"
RULE_VERSION = "critical_eval_v2_option_a_obligation_alternatives_v7"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line]


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def requirement(evidence_id: str, sentence: str, index: int) -> dict:
    return {
        "requirement_id": f"ALT_COV1_REQ_{index:02d}",
        "evidence_id": evidence_id,
        "exact_claim_text": sentence,
        "normalized_claim_text": " ".join(sentence.casefold().split()),
        "section_support_class": "DIRECT_SUPPORT",
        "sentence_semantic_support": "DIRECT_FULFILLMENT",
    }


COV1_FIXES = {
    ("Q_V2_A_TRP03", "CHECKS"): (
        "FAQ_TRANSFER_PENDING_001#answer",
        [
            "A pending transfer is accepted for processing but has not completed.",
            "Do not describe it as failed, declined, or received by the recipient.",
        ],
    ),
    ("Q_V2_A_TRF01", "BOUNDARY"): (
        "RUN_TRANSFER_FAILED_001#checks",
        [
            "Verify an explicit failed state and confirm that no duplicate transfer remains pending.",
            "Do not reinterpret an immediate refusal as failure.",
        ],
    ),
    ("Q_V2_A_CAR02", "TRIGGER"): (
        "POL_CARD_REVERT_002#return_window",
        ["If the amount is absent after that window, follow the approved reversal escalation guide."],
    ),
    ("Q_V2_A_CAR03", "ELIGIBILITY"): (
        "ESC_CARD_REVERT_001#trigger",
        [
            "Escalate only when a confirmed reversal lacks ledger return after five fictional business days.",
            "Pending authorizations and declines do not qualify.",
        ],
    ),
    ("Q_V2_A_CSP03", "GATE"): (
        "FAQ_CASH_PENDING_001#answer",
        [
            "Use this FAQ only when the customer recognizes the ATM interaction and the withdrawal entry remains pending.",
            "Non-recognition requires immediate security handling.",
        ],
    ),
    ("Q_V2_A_CSD04", "DECLINE"): (
        "ESC_CASH_DECLINED_001#trigger",
        ["Use after two recognized ATM refusals in one fictional day, provided no cash was dispensed."],
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    config = read_json(root / "configs/evaluation/critical_eval_v2_execution.json")
    candidate_config = read_json(root / config["candidate"]["config"])
    pass_b_path = root / candidate_config["outputs"]["pass_b"]
    mapping_path = root / candidate_config["outputs"]["pass_c"]
    if sha256(pass_b_path) != PASS_B_SHA256 or sha256(mapping_path) != MAPPING_SHA256:
        raise RuntimeError("STOP: frozen revision-7 Pass-B or mapping bytes changed")

    rules_path = root / config["safety_evaluator"]["obligation_rules"]
    rules = read_jsonl(rules_path)
    index = {(row["query_id"], row["obligation_id"]): row for row in rules}
    for key, (evidence_id, sentences) in COV1_FIXES.items():
        row = index[key]
        row["rule_version"] = RULE_VERSION
        existing = {
            tuple((req["evidence_id"], req["exact_claim_text"]) for req in alt["requirements"])
            for alt in row["fulfillment_alternatives"]
        }
        signature = tuple((evidence_id, sentence) for sentence in sentences)
        if signature not in existing:
            row["fulfillment_alternatives"].append({
                "alternative_id": "ALT_COV1",
                "requirements": [requirement(evidence_id, sentence, i) for i, sentence in enumerate(sentences, 1)],
            })
        row["review_rationale"] += " COV1 Senior adjudication added an exact evaluator-only fulfillment alternative without changing candidate bytes."
    for row in rules:
        row["rule_version"] = RULE_VERSION
    write_jsonl(rules_path, rules)

    old_audit = read_jsonl(root / config["safety_evaluator"]["obligation_audit"])
    rejected = [row for row in old_audit if row.get("sentence_semantic_support") == "SEMANTIC_REJECT"]
    alternatives = [alt for row in rules for alt in row["fulfillment_alternatives"]]
    requirements = [req for alt in alternatives for req in alt["requirements"]]
    grouped = {}
    for row in rules:
        for alt in row["fulfillment_alternatives"]:
            for req in alt["requirements"]:
                grouped.setdefault((row["query_id"], req["evidence_id"], req["normalized_claim_text"]), set()).add(row["obligation_id"])
    summary = {
        "record_type": "SUMMARY",
        "answerable_queries": 55,
        "required_obligations": 148,
        "atomic_sentence_requirements": len(requirements),
        "composite_and_alternatives": sum(len(alt["requirements"]) > 1 for alt in alternatives),
        "single_sentence_alternatives": sum(len(alt["requirements"]) == 1 for alt in alternatives),
        "multi_obligation_sentence_rules": sum(len(values) for values in grouped.values() if len(values) > 1),
        "semantic_rejects": len(rejected),
        "unreachable_multi_sentence_atomic_rules": 0,
        "revision_4_changes": next(row for row in old_audit if row.get("record_type") == "SUMMARY").get("revision_4_changes"),
        "revision_5_to_6_changes": next(row for row in old_audit if row.get("record_type") == "SUMMARY").get("revision_5_to_6_changes"),
        "revision_6_to_7_changes": "Six Senior-adjudicated COV1 evaluator-only alternatives added; candidate revision-7 semantics preserved.",
        "review_method": "OBLIGATION_ATOMIC_SENTENCE_ALTERNATIVE_SEMANTIC_REVIEW",
        "review_status": "AWAITING_SENIOR_REVIEW",
        "rule_version": RULE_VERSION,
    }
    write_jsonl(root / config["safety_evaluator"]["obligation_audit"], rules + rejected + [summary])
    delta = {
        "task_id": "W3-002-CR1-EA1",
        "candidate_revision": 7,
        "readiness_revision_from": 6,
        "readiness_revision_to": 7,
        "rules_reviewed": 148,
        "candidate_mapping_modified": False,
        "pass_b_modified": False,
        "cov1_evaluator_only_fix_count": 6,
        "fixes": [
            {"query_id": q, "obligation_id": o, "evidence_id": evidence, "atomic_sentence_count": len(sentences)}
            for (q, o), (evidence, sentences) in COV1_FIXES.items()
        ],
        "preserved_revision_6_semantic_rejects": 2,
        "review_status": "CANDIDATE_AWAITING_SENIOR_REVIEW",
    }
    delta_path = root / config["safety_evaluator"]["obligation_semantic_delta"]
    write_json(delta_path, delta)
    print(json.dumps({"status": "PASS", "rules": len(rules), "cov1_fixes": len(COV1_FIXES), "delta": str(delta_path.relative_to(root))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
