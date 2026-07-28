"""CLI for deterministic W2-002 gold evidence mapping validation."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from typing import Any

from payresolve_ai.evaluation.gold_mapping import (
    build_manifest,
    coverage_rows,
    load_json,
    load_jsonl,
    overlap_audit,
    validate_gold_mapping,
)
from payresolve_ai.kb.validation import file_sha256


def _resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--config", type=Path, default=Path("configs/evaluation/gold_mapping_v1.json"))
    parser.add_argument("--write-results", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    config = load_json(_resolve(root, str(args.config)))
    rows = load_jsonl(_resolve(root, config["mapping_path"]))
    scenarios = load_jsonl(_resolve(root, config["scenario_plan_path"]))
    kb_path = _resolve(root, config["kb_documents_path"])
    documents = load_jsonl(kb_path)
    audit = overlap_audit(
        rows,
        documents,
        near_threshold=float(config["acceptance"]["query_near_duplicate_threshold"]),
        kb_threshold=float(config["acceptance"]["query_to_kb_suspicious_overlap_threshold"]),
        banking77_train=_resolve(root, config["banking77_train_source"]),
        banking77_test=_resolve(root, config["banking77_test_source"]),
    )
    report = validate_gold_mapping(rows, scenarios, documents, config, audit=audit)
    actual_raw_hash = file_sha256(kb_path)
    if actual_raw_hash != config["expected_kb_raw_sha256"]:
        report["errors"].append({"code": "kb-raw-hash-mismatch", "message": f"Expected {config['expected_kb_raw_sha256']}, got {actual_raw_hash}"})
        report["valid"] = False
    manifest = build_manifest(report, config, documents, kb_path, audit)
    if args.write_results:
        _write_json(_resolve(root, config["outputs"]["validation"]), report)
        _write_json(_resolve(root, config["outputs"]["manifest"]), manifest)
        _write_json(_resolve(root, config["outputs"]["overlap_audit"]), audit)
        coverage_path = _resolve(root, config["outputs"]["coverage"])
        coverage_path.parent.mkdir(parents=True, exist_ok=True)
        coverage = coverage_rows(rows, documents, date.fromisoformat(config["evaluation_as_of_date"]))
        with coverage_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(coverage[0]))
            writer.writeheader()
            writer.writerows(coverage)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
