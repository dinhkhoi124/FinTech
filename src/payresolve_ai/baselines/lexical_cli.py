"""Command-line entry point for W1-002 validation-only experiments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .lexical import inspect_validation_errors, run_validation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--inspect-errors",
        type=int,
        default=0,
        help="Print this many representative validation errors after the run",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    config = args.config if args.config.is_absolute() else root / args.config
    result = run_validation(root, config.resolve())
    print(json.dumps(result["metrics"], indent=2, sort_keys=True))
    if args.inspect_errors:
        errors = inspect_validation_errors(root, config.resolve(), args.inspect_errors)
        print(json.dumps({"validation_error_examples": errors}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
