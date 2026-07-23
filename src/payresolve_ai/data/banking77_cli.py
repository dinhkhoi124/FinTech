"""Command-line interface for the locked W1-001 Banking77 data protocol."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from payresolve_ai.data.banking77 import (
    Banking77Error,
    acquire_source,
    load_config,
    verify_locked_artifacts,
    write_locked_artifacts,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Repository root")
    parser.add_argument("--config", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    acquire = subparsers.add_parser("acquire", help="Acquire exactly the pinned upstream files")
    acquire.add_argument("--refresh", action="store_true", help="Redownload pinned files")
    subparsers.add_parser("audit-lock", help="Audit data and write deterministic split artifacts")
    subparsers.add_parser("verify", help="Recompute and compare all locked artifacts")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    try:
        config = load_config(config_path)
        if args.command == "acquire":
            result = acquire_source(root, config, refresh=args.refresh)
        elif args.command == "audit-lock":
            artifacts = write_locked_artifacts(root, config)
            result = {
                "sample_counts": artifacts["audit_json"]["audit"]["sample_counts"],
                "intent_count": artifacts["audit_json"]["audit"]["labels"]["count"],
                "split_counts": artifacts["split_manifest"]["split"]["counts"],
                "combined_membership_sha256": artifacts["split_manifest"]["split"]
                ["combined_membership_sha256"],
            }
        else:
            result = verify_locked_artifacts(root, config)
    except (Banking77Error, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

