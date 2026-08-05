"""Validate the W3-002-CR1 Option A contract without inference."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--decision-bundle", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    sys.path.insert(0, str(root / "src"))
    from payresolve_ai.evaluation.critical_v2_contract import (  # noqa: PLC0415
        ContractValidationError,
        validate_contract_package,
    )

    try:
        result = validate_contract_package(root, args.decision_bundle)
    except ContractValidationError as exc:
        print(f"W3-002-CR1 Option A contract: FAIL — {exc}", file=sys.stderr)
        return 1
    print("W3-002-CR1 Option A contract: PASS")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
