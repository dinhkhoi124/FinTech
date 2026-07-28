"""CLI for deterministic W2-001 synthetic-KB validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from payresolve_ai.kb.validation import (
    KBValidationError,
    load_config,
    load_documents,
    write_validation_outputs,
    validate_kb,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Repository root")
    parser.add_argument("--config", type=Path, required=True, help="KB validation config")
    parser.add_argument(
        "--write-results",
        action="store_true",
        help="Write validation report, manifest, and coverage evidence",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    try:
        config = load_config(root, config_path)
        documents = load_documents(root / config["documents_path"])
        hard_negative_matrix = json.loads(
            (root / config["hard_negative_matrix_path"]).read_text(encoding="utf-8")
        )
        document_plan = json.loads(
            (root / config["document_plan_path"]).read_text(encoding="utf-8")
        )
        categories = json.loads(
            (root / config["canonical_intents_source"]).read_text(encoding="utf-8")
        )
        report = validate_kb(
            documents,
            config,
            hard_negative_matrix,
            canonical_categories=categories,
            document_plan=document_plan,
        )
        if args.write_results:
            write_validation_outputs(root, config_path, config, report)
    except (KBValidationError, FileNotFoundError, json.JSONDecodeError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["validation_result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
