"""CLI for the frozen W3-003 independent product-gate lifecycle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from payresolve_ai.evaluation.w3_003_independent import (
    authorize_from_review,
    evaluate_frozen_primary,
    execute_runtime,
    finalize,
    freeze_primary,
    freeze_reproduction,
    verify_package,
    verify_reproducibility,
    verify_results,
)


DEFAULT_CONFIG = Path("configs/evaluation/w3_003_independent_eval_v1.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("command", choices=(
        "verify-package", "authorize", "run-primary", "freeze-primary", "evaluate",
        "run-reproduction", "freeze-reproduction", "verify-reproducibility", "finalize", "verify-results",
    ))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    command = args.command
    if command == "verify-package":
        result = verify_package(root, args.config)
    elif command == "authorize":
        result = authorize_from_review(root, args.config)
    elif command == "run-primary":
        result = execute_runtime(root, args.config, "primary")
    elif command == "freeze-primary":
        result = freeze_primary(root, args.config)
    elif command == "evaluate":
        result = evaluate_frozen_primary(root, args.config)
    elif command == "run-reproduction":
        result = execute_runtime(root, args.config, "reproduction")
    elif command == "freeze-reproduction":
        result = freeze_reproduction(root, args.config)
    elif command == "verify-reproducibility":
        result = verify_reproducibility(root, args.config)
    elif command == "finalize":
        result = finalize(root, args.config)
    else:
        result = verify_results(root, args.config)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
