"""Run the Senior-review direct mutation probes for W2-002."""

from __future__ import annotations

import argparse
import sys
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from payresolve_ai.evaluation.gold_mapping import load_json, load_jsonl, validate_gold_mapping  # noqa: E402


EXPECTED = {
    "gold_intent_section_as_hard_negative": "hard-negative-supports-gold-intent",
    "unrelated_intent_as_hard_negative": "hard-negative-intent-mismatch",
    "numeric_mapping_rationale": "invalid-mapping-rationale",
    "numeric_review_notes": "invalid-review-notes",
    "duplicate_scenario_id": "duplicate-scenario-id",
    "missing_scenario_customer_situation": "missing-scenario-required-field",
    "invalid_scenario_confusing_intent": "scenario-confusing-intent-contract",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--config", type=Path, default=Path("configs/evaluation/gold_mapping_v1.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = load_json(config_path)
    base_rows = load_jsonl(root / config["mapping_path"])
    base_scenarios = load_jsonl(root / config["scenario_plan_path"])
    documents = load_jsonl(root / config["kb_documents_path"])

    cases: list[tuple[str, list[dict], list[dict]]] = []
    rows, scenarios = deepcopy(base_rows), deepcopy(base_scenarios)
    next(row for row in rows if row["expected_response_type"] == "ANSWER")["hard_negative_evidence_ids"] = ["FAQ_CARD_DECLINED_001#policy_gap"]
    cases.append(("gold_intent_section_as_hard_negative", rows, scenarios))
    rows, scenarios = deepcopy(base_rows), deepcopy(base_scenarios)
    next(row for row in rows if row["expected_response_type"] == "ANSWER")["hard_negative_evidence_ids"] = ["POL_CASH_DECLINED_001#eligibility"]
    cases.append(("unrelated_intent_as_hard_negative", rows, scenarios))
    rows, scenarios = deepcopy(base_rows), deepcopy(base_scenarios)
    rows[0]["mapping_rationale"] = 12345
    cases.append(("numeric_mapping_rationale", rows, scenarios))
    rows, scenarios = deepcopy(base_rows), deepcopy(base_scenarios)
    rows[0]["review_notes"] = 12345
    cases.append(("numeric_review_notes", rows, scenarios))
    rows, scenarios = deepcopy(base_rows), deepcopy(base_scenarios)
    scenarios[1]["query_id"] = scenarios[0]["query_id"]
    cases.append(("duplicate_scenario_id", rows, scenarios))
    rows, scenarios = deepcopy(base_rows), deepcopy(base_scenarios)
    scenarios[0].pop("customer_situation")
    cases.append(("missing_scenario_customer_situation", rows, scenarios))
    rows, scenarios = deepcopy(base_rows), deepcopy(base_scenarios)
    next(row for row in scenarios if row["expected_response_type"] == "ANSWER")["confusing_intent"] = "unknown_intent"
    cases.append(("invalid_scenario_confusing_intent", rows, scenarios))

    lines = ["W2-002 DIRECT MUTATION RESULTS"]
    all_expected = True
    for name, rows, scenarios in cases:
        report = validate_gold_mapping(rows, scenarios, documents, config)
        codes = sorted(error["code"] for error in report["errors"])
        expected = EXPECTED[name]
        passed = not report["valid"] and expected in codes
        all_expected &= passed
        lines.append(f"{name}: {'FAIL_AS_EXPECTED' if passed else 'UNEXPECTED_RESULT'} | expected={expected} | codes={','.join(codes)}")
    lines.append(f"OVERALL: {'PASS' if all_expected else 'FAIL'}")
    output = "\n".join(lines) + "\n"
    print(output, end="")
    if args.output:
        path = args.output if args.output.is_absolute() else root / args.output
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output, encoding="utf-8")
    return 0 if all_expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
