"""CLI for W3-002-CR1 candidate authoring; no inference dependencies."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--config", type=Path, default=Path("configs/evaluation/critical_eval_v2.json"))
    parser.add_argument("command", choices=("verify-pass-b", "recompute-overlap", "freeze-revision-7", "verify-candidate", "run-critical"))
    args = parser.parse_args()
    root = args.root.resolve()
    config = (root / args.config).resolve() if not args.config.is_absolute() else args.config
    sys.path.insert(0, str(root / "src"))
    from payresolve_ai.evaluation.critical_v2 import (
        CriticalV2Error,
        _catalog,
        assert_evaluation_execution_authorized,
        freeze_revision_7,
        load_config,
        load_jsonl,
        recompute_overlap,
        validate_pass_a,
        validate_pass_b,
        verify_candidate,
    )
    try:
        if args.command == "verify-pass-b":
            loaded = load_config(config)
            pass_a = load_jsonl(root / loaded["outputs"]["pass_a"])
            validate_pass_a(pass_a)
            eligible, _ = _catalog(root, loaded)
            result = {"status": "PASS", **validate_pass_b(pass_a, load_jsonl(root / loaded["outputs"]["pass_b"]), eligible)}
        elif args.command == "recompute-overlap":
            loaded = load_config(config)
            result, _ = recompute_overlap(root, loaded)
        elif args.command == "freeze-revision-7":
            result = freeze_revision_7(root, config)
        elif args.command == "verify-candidate":
            result = verify_candidate(root, config)
        else:
            manifest_path = root / load_config(config)["outputs"]["candidate_manifest"]
            assert_evaluation_execution_authorized(json.loads(manifest_path.read_text(encoding="utf-8")))
            raise CriticalV2Error("critical pipeline execution is intentionally unavailable in this authoring task")
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, indent=2))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
