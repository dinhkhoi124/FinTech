"""Command-line interface for the W1-003 validation-only semantic baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .semantic import (
    inspect_validation_errors,
    run_smoke,
    run_validation,
    verify_cache,
    verify_contract,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("verify-contract")
    subparsers.add_parser("smoke")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument(
        "--run-label", choices=("primary", "reproducibility_rerun"), required=True
    )
    run_parser.add_argument("--refresh-cache", action="store_true")
    subparsers.add_parser("verify-cache")
    inspect_parser = subparsers.add_parser("inspect-errors")
    inspect_parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    root = args.root.resolve()
    config = args.config if args.config.is_absolute() else root / args.config
    if args.command == "verify-contract":
        result = verify_contract(root, config.resolve())
    elif args.command == "smoke":
        result = run_smoke(root, config.resolve())
    elif args.command == "run":
        result = run_validation(root, config.resolve(), args.run_label, args.refresh_cache)
    elif args.command == "verify-cache":
        result = verify_cache(root, config.resolve())
    else:
        result = {"validation_error_examples": inspect_validation_errors(root, config.resolve(), args.limit)}
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
