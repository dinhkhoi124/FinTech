"""Standalone verifier for an extracted W3-002-CR1 review bundle.

The command uses only Python's standard library plus source files contained in
the extracted bundle.  It never imports from the original repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_inventory(root: Path) -> dict[str, int]:
    path = root / "review_bundle_manifest.json"
    if not path.is_file():
        raise RuntimeError("review_bundle_manifest.json is missing")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    files = manifest.get("files", [])
    for item in files:
        target = root / item["path"]
        if not target.is_file() or target.stat().st_size != item["size_bytes"] or sha256(target) != item["sha256"]:
            raise RuntimeError(f"bundle inventory mismatch: {item['path']}")
    return {"inventory_files_verified": len(files)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--config", type=Path, default=Path("configs/evaluation/critical_eval_v2.json"))
    parser.add_argument("--skip-bundle-inventory", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    inventory = {"inventory_files_verified": 0} if args.skip_bundle_inventory else verify_inventory(root)
    sys.path.insert(0, str(root / "src"))
    from payresolve_ai.evaluation.critical_v2 import verify_candidate

    result = verify_candidate(root, root / args.config)
    output = {**inventory, **result, "standalone_bundle_verification": "PASS"}
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"standalone_bundle_verification": "FAIL", "error": str(error)}, indent=2))
        raise SystemExit(1)
