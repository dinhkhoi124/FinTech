"""Validate W3-002-CR1 contract-amendment evidence without inference."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    sys.path.insert(0, str(root / "src"))
    from payresolve_ai.evaluation.critical_v2_feasibility import (  # noqa: PLC0415
        FeasibilityValidationError,
        validate_feasibility_package,
    )

    try:
        result = validate_feasibility_package(root)
    except FeasibilityValidationError as exc:
        print(f"W3-002-CR1 feasibility package: FAIL — {exc}", file=sys.stderr)
        return 1
    print("W3-002-CR1 feasibility package: PASS")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
