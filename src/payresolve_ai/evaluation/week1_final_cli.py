"""CLI for the preregistered W1-004 final evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from payresolve_ai.evaluation.week1_final import (
    Week1FinalEvaluationError,
    finalize_evaluation,
    run_final_evaluation,
    verify_final_results,
    verify_pretest_gate,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("verify-pretest")
    run = subparsers.add_parser("run")
    run.add_argument("--run-label", required=True, choices=("primary", "reproducibility_rerun"))
    subparsers.add_parser("finalize")
    subparsers.add_parser("verify-results")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    config = args.config if args.config.is_absolute() else root / args.config
    try:
        if args.command == "verify-pretest":
            result = verify_pretest_gate(root, config)
        elif args.command == "run":
            result = run_final_evaluation(root, config, args.run_label)
        elif args.command == "finalize":
            result = finalize_evaluation(root, config)
        else:
            result = verify_final_results(root, config)
    except Week1FinalEvaluationError as error:
        print(f"ERROR: {error}")
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0
