"""CLI for the explicit W3-001 lifecycle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .verification import build_dev_runtime, finalize, run_dev, select_gate, validate_gate_development, verify_contract, verify_results, verify_runtime_reproduction


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--config", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("verify-contract", "validate-gate-dev", "build-dev-runtime", "select-gate", "finalize", "verify-results", "verify-runtime-reproduction"):
        sub.add_parser(name)
    run = sub.add_parser("run-dev"); run.add_argument("--mode", choices=["evidence_gated"], default="evidence_gated"); run.add_argument("--run-label", choices=["primary", "reproducibility_rerun"], required=True)
    args = parser.parse_args(); root = args.root.resolve(); config = (root / args.config).resolve() if not args.config.is_absolute() else args.config
    actions = {"verify-contract": verify_contract, "validate-gate-dev": validate_gate_development, "build-dev-runtime": build_dev_runtime, "select-gate": select_gate, "finalize": finalize, "verify-results": verify_results, "verify-runtime-reproduction": verify_runtime_reproduction}
    result = run_dev(root, config, args.run_label) if args.command == "run-dev" else actions[args.command](root, config)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
