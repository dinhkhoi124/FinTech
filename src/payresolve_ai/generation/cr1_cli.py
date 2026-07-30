"""CLI for the reviewed W3-001-CR1 lifecycle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .verification_v2 import finalize, finalize_adjudication, freeze_v2_design, run_holdout, select_v2, validate_adjudication, validate_holdout, verify_contract, verify_preholdout, verify_results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--config", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("verify-contract", "validate-holdout", "validate-adjudication", "freeze-v2-design", "select-v2", "verify-preholdout", "finalize", "finalize-adjudication", "verify-results"):
        sub.add_parser(name)
    run = sub.add_parser("run-holdout")
    run.add_argument("--run-label", required=True, choices=["primary", "reproducibility_rerun"])
    args = parser.parse_args()
    root = args.root.resolve()
    config = (root / args.config).resolve() if not args.config.is_absolute() else args.config
    actions = {"verify-contract": verify_contract, "validate-holdout": validate_holdout, "validate-adjudication": validate_adjudication, "freeze-v2-design": freeze_v2_design, "select-v2": select_v2, "verify-preholdout": verify_preholdout, "finalize": finalize, "finalize-adjudication": finalize_adjudication, "verify-results": verify_results}
    result = run_holdout(root, config, args.run_label) if args.command == "run-holdout" else actions[args.command](root, config)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
