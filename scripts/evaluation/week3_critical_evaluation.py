"""Command-line lifecycle for W3-002 critical safety evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--config", type=Path, default=Path("configs/evaluation/critical_eval_v1.json"))
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("verify-contract", "validate-scenarios", "freeze-queries", "audit-mappings", "audit-overlap", "freeze-critical-set", "verify-pre-evaluation", "build-integrity-audit", "verify-integrity-incident", "finalize", "verify-results"):
        sub.add_parser(command)
    run = sub.add_parser("run-critical"); run.add_argument("--run-label", required=True, choices=("primary", "reproducibility_rerun"))
    return parser


def main() -> int:
    args = _parser().parse_args(); root = args.root.resolve(); config_path = (root / args.config).resolve() if not args.config.is_absolute() else args.config
    sys.path.insert(0, str(root / "src"))
    from payresolve_ai.evaluation.critical import audit_mappings, audit_overlap, freeze_critical_set, freeze_queries, load_config, scenario_rows, validate_scenarios, verify_pre_evaluation
    from payresolve_ai.evaluation.critical_verification import finalize, run_critical, verify_contract, verify_results
    from payresolve_ai.evaluation.critical_integrity import build_integrity_audits, verify_integrity_incident
    actions = {
        "verify-contract": lambda: verify_contract(root, config_path),
        "validate-scenarios": lambda: validate_scenarios(scenario_rows(), load_config(config_path)),
        "freeze-queries": lambda: freeze_queries(root, config_path),
        "audit-mappings": lambda: audit_mappings(root, config_path),
        "audit-overlap": lambda: audit_overlap(root, config_path),
        "freeze-critical-set": lambda: freeze_critical_set(root, config_path),
        "verify-pre-evaluation": lambda: verify_pre_evaluation(root, config_path),
        "build-integrity-audit": lambda: build_integrity_audits(root, config_path),
        "verify-integrity-incident": lambda: verify_integrity_incident(root, config_path),
        "run-critical": lambda: run_critical(root, config_path, args.run_label),
        "finalize": lambda: finalize(root, config_path),
        "verify-results": lambda: verify_results(root, config_path),
    }
    try: result = actions[args.command]()
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, indent=2)); return 1
    print(json.dumps(result, indent=2, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
