"""Banking77 acquisition, integrity audit, and deterministic split locking."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


REQUIRED_SOURCE_FILES = ("categories.json", "train.csv", "test.csv")
FULL_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
SAMPLE_ID_SCHEME = "sha256('banking77\\0' + source_file + '\\0' + row_number + '\\0' + text + '\\0' + label)"


class Banking77Error(ValueError):
    """Raised when the dataset violates the locked W1-001 contract."""


@dataclass(frozen=True)
class Example:
    sample_id: str
    source_file: str
    source_row: int
    text: str
    label: str


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    revision = config.get("source", {}).get("revision", "")
    if not FULL_GIT_SHA.fullmatch(revision):
        raise Banking77Error("source.revision must be an exact 40-character lowercase Git SHA")
    files = config.get("source", {}).get("files", {})
    if tuple(files) != REQUIRED_SOURCE_FILES:
        raise Banking77Error(f"source.files must contain exactly {REQUIRED_SOURCE_FILES}")
    fraction = config.get("split", {}).get("validation_fraction", {})
    numerator = fraction.get("numerator")
    denominator = fraction.get("denominator")
    if not isinstance(numerator, int) or not isinstance(denominator, int):
        raise Banking77Error("validation fraction must use integer numerator/denominator")
    if numerator <= 0 or denominator <= numerator:
        raise Banking77Error("validation fraction must satisfy 0 < numerator < denominator")
    return config


def resolve_repo_path(root: Path, relative: str) -> Path:
    root = root.resolve()
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise Banking77Error(f"Configured path escapes repository root: {relative}")
    return target


def acquire_source(root: Path, config: dict[str, Any], *, refresh: bool = False) -> dict[str, Any]:
    source = config["source"]
    revision = source["revision"]
    raw_directory = resolve_repo_path(root, config["paths"]["raw_directory"])
    required_raw_root = (root / "data" / "raw").resolve()
    if not raw_directory.is_relative_to(required_raw_root):
        raise Banking77Error("Raw dataset files must remain under data/raw/")
    raw_directory.mkdir(parents=True, exist_ok=True)

    file_manifest: dict[str, Any] = {}
    for filename in REQUIRED_SOURCE_FILES:
        target = raw_directory / filename
        url = (
            "https://raw.githubusercontent.com/PolyAI-LDN/"
            f"task-specific-datasets/{revision}/banking_data/{filename}"
        )
        if refresh or not target.is_file():
            request = urllib.request.Request(url, headers={"User-Agent": "PayResolve-W1-001/1.0"})
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read()
            temporary = target.with_suffix(target.suffix + ".tmp")
            temporary.write_bytes(payload)
            temporary.replace(target)

        actual_sha = sha256_file(target)
        expected_sha = source["files"][filename].get("sha256")
        if expected_sha and actual_sha != expected_sha:
            raise Banking77Error(
                f"Checksum mismatch for {filename}: expected {expected_sha}, got {actual_sha}"
            )
        file_manifest[filename] = {
            "bytes": target.stat().st_size,
            "raw_url": url,
            "sha256": actual_sha,
        }

    manifest = {
        "dataset": "Banking77",
        "authoritative_source": source["directory_url"],
        "repository_url": source["repository_url"],
        "revision": revision,
        "subdirectory": source["subdirectory"],
        "license": source.get("license"),
        "files": file_manifest,
    }
    manifest_path = resolve_repo_path(root, config["paths"]["source_manifest"])
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    return manifest


def _sample_id(source_file: str, source_row: int, text: str, label: str) -> str:
    payload = f"banking77\0{source_file}\0{source_row}\0{text}\0{label}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_categories(path: Path) -> list[str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise Banking77Error("categories.json must be a non-empty JSON list of strings")
    if any(not item.strip() for item in value):
        raise Banking77Error("categories.json contains an empty label")
    if len(set(value)) != len(value):
        raise Banking77Error("categories.json contains duplicate labels")
    return value


def load_examples(path: Path) -> list[Example]:
    examples: list[Example] = []
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != ["text", "category"]:
            raise Banking77Error(
                f"{path.name} columns must be exactly ['text', 'category']; got {reader.fieldnames}"
            )
        for data_index, row in enumerate(reader, start=1):
            text = row.get("text")
            label = row.get("category")
            if text is None or label is None:
                raise Banking77Error(f"{path.name} row {data_index} has a missing field")
            examples.append(
                Example(
                    sample_id=_sample_id(path.name, data_index, text, label),
                    source_file=path.name,
                    source_row=data_index,
                    text=text,
                    label=label,
                )
            )
    return examples


def _distribution(examples: Iterable[Example], categories: list[str]) -> dict[str, int]:
    counts = Counter(example.label for example in examples)
    return {label: counts[label] for label in categories}


def _duplicate_stats(examples: list[Example], key: Any) -> dict[str, int]:
    groups: dict[Any, int] = Counter(key(example) for example in examples)
    duplicates = [count for count in groups.values() if count > 1]
    return {
        "groups": len(duplicates),
        "rows_in_groups": sum(duplicates),
        "extra_rows": sum(count - 1 for count in duplicates),
    }


def _normalized_query(text: str) -> str:
    return " ".join(text.casefold().split())


def _cross_split_overlap(
    train: list[Example], test: list[Example], key: Any
) -> dict[str, Any]:
    train_groups: dict[Any, list[Example]] = defaultdict(list)
    test_groups: dict[Any, list[Example]] = defaultdict(list)
    for example in train:
        train_groups[key(example)].append(example)
    for example in test:
        test_groups[key(example)].append(example)
    train_keys = {item: len(examples) for item, examples in train_groups.items()}
    test_keys = {item: len(examples) for item, examples in test_groups.items()}
    shared = set(train_keys).intersection(test_keys)
    label_conflict_keys = [
        item
        for item in shared
        if len({example.label for example in train_groups[item] + test_groups[item]}) > 1
    ]
    return {
        "distinct_queries": len(shared),
        "train_rows": sum(train_keys[item] for item in shared),
        "test_rows": sum(test_keys[item] for item in shared),
        "label_consistent_queries": len(shared) - len(label_conflict_keys),
        "label_conflicting_queries": len(label_conflict_keys),
        "examples": [
            {
                "comparison_key": str(item),
                "train": [
                    {
                        "sample_id": example.sample_id,
                        "source_row": example.source_row,
                        "label": example.label,
                        "text": example.text,
                    }
                    for example in sorted(train_groups[item], key=lambda value: value.sample_id)
                ],
                "test": [
                    {
                        "sample_id": example.sample_id,
                        "source_row": example.source_row,
                        "label": example.label,
                        "text": example.text,
                    }
                    for example in sorted(test_groups[item], key=lambda value: value.sample_id)
                ],
            }
            for item in sorted(shared, key=str)
        ],
    }


def audit_examples(
    categories: list[str], train: list[Example], test: list[Example], audit_config: dict[str, Any]
) -> dict[str, Any]:
    all_examples = train + test
    category_set = set(categories)
    invalid = [example for example in all_examples if example.label not in category_set]
    empty_text = [example for example in all_examples if not example.text.strip()]
    empty_label = [example for example in all_examples if not example.label.strip()]

    query_labels: dict[str, set[str]] = defaultdict(set)
    query_rows: Counter[str] = Counter()
    for example in all_examples:
        query_labels[example.text].add(example.label)
        query_rows[example.text] += 1
    conflicting = [query for query, labels in query_labels.items() if len(labels) > 1]

    thresholds = audit_config["short_token_thresholds"]
    shortest = sorted(all_examples, key=lambda item: (len(item.text.split()), item.sample_id))
    limit = audit_config["shortest_examples_limit"]

    result = {
        "sample_counts": {
            "official_train": len(train),
            "official_test": len(test),
            "total": len(all_examples),
        },
        "labels": {
            "count": len(categories),
            "mapping": {label: index for index, label in enumerate(categories)},
            "official_train_distribution": _distribution(train, categories),
            "official_test_distribution": _distribution(test, categories),
            "invalid_label_rows": len(invalid),
            "labels_missing_from_official_train": [
                label for label, count in _distribution(train, categories).items() if count == 0
            ],
            "labels_missing_from_official_test": [
                label for label, count in _distribution(test, categories).items() if count == 0
            ],
        },
        "integrity": {
            "missing_or_null_fields": 0,
            "empty_text_rows": len(empty_text),
            "empty_label_rows": len(empty_label),
            "exact_query_duplicates": _duplicate_stats(all_examples, lambda item: item.text),
            "exact_query_label_duplicates": _duplicate_stats(
                all_examples, lambda item: (item.text, item.label)
            ),
            "conflicting_label_queries": {
                "groups": len(conflicting),
                "rows": sum(query_rows[query] for query in conflicting),
            },
            "official_train_test_exact_overlap": _cross_split_overlap(
                train, test, lambda item: item.text
            ),
            "official_train_test_case_whitespace_normalized_overlap": _cross_split_overlap(
                train, test, lambda item: _normalized_query(item.text)
            ),
        },
        "short_queries": {
            "counts_by_max_tokens": {
                str(threshold): sum(len(example.text.split()) <= threshold for example in all_examples)
                for threshold in thresholds
            },
            "shortest_examples": [
                {
                    "sample_id": example.sample_id,
                    "source_file": example.source_file,
                    "source_row": example.source_row,
                    "label": example.label,
                    "tokens": len(example.text.split()),
                    "text": example.text,
                }
                for example in shortest[:limit]
            ],
        },
        "near_duplicate_scope": (
            "Lightweight case-folded/whitespace-normalized exact overlap only; "
            "no fuzzy deduplication or data removal was performed."
        ),
    }
    if invalid or empty_text or empty_label:
        raise Banking77Error(
            "Critical integrity failure: invalid labels or empty text/label rows prevent locking"
        )
    return result


def build_locked_split(
    categories: list[str], train: list[Example], test: list[Example], split_config: dict[str, Any]
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    numerator = split_config["validation_fraction"]["numerator"]
    denominator = split_config["validation_fraction"]["denominator"]
    seed = split_config["seed"]
    by_label: dict[str, list[Example]] = defaultdict(list)
    for example in train:
        by_label[example.label].append(example)

    train_ids: list[str] = []
    validation_ids: list[str] = []
    for label in categories:
        examples = by_label[label]
        if len(examples) < 2:
            raise Banking77Error(f"Label {label!r} has fewer than two official training examples")
        ordered = sorted(
            examples,
            key=lambda item: hashlib.sha256(f"{seed}\0{item.sample_id}".encode("utf-8")).hexdigest(),
        )
        validation_count = max(1, (len(ordered) * numerator + denominator // 2) // denominator)
        validation_count = min(validation_count, len(ordered) - 1)
        validation_ids.extend(item.sample_id for item in ordered[:validation_count])
        train_ids.extend(item.sample_id for item in ordered[validation_count:])

    membership = {
        "train": sorted(train_ids),
        "validation": sorted(validation_ids),
        "test": sorted(example.sample_id for example in test),
    }
    split_by_id = {
        sample_id: split for split, sample_ids in membership.items() for sample_id in sample_ids
    }
    all_examples = train + test
    distributions = {
        split: _distribution(
            (example for example in all_examples if split_by_id[example.sample_id] == split), categories
        )
        for split in membership
    }
    membership_hashes = {
        split: sha256_bytes(("\n".join(sample_ids) + "\n").encode("ascii"))
        for split, sample_ids in membership.items()
    }
    metadata = {
        "strategy": split_config["strategy"],
        "seed": seed,
        "validation_fraction": split_config["validation_fraction"],
        "official_test_frozen": True,
        "official_train_only_for_train_and_validation": True,
        "sample_id_scheme": SAMPLE_ID_SCHEME,
        "counts": {split: len(sample_ids) for split, sample_ids in membership.items()},
        "class_distribution": distributions,
        "membership_sha256": membership_hashes,
        "combined_membership_sha256": sha256_bytes(canonical_json_bytes(membership)),
    }
    return membership, metadata


def build_artifacts(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    raw_directory = resolve_repo_path(root, config["paths"]["raw_directory"])
    categories = load_categories(raw_directory / "categories.json")
    train = load_examples(raw_directory / "train.csv")
    test = load_examples(raw_directory / "test.csv")
    audit = audit_examples(categories, train, test, config["audit"])
    membership, split_metadata = build_locked_split(categories, train, test, config["split"])
    source_manifest_path = resolve_repo_path(root, config["paths"]["source_manifest"])
    if not source_manifest_path.is_file():
        raise Banking77Error("Source manifest is missing; run acquire first")
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))

    split_manifest = {
        "dataset": "Banking77",
        "protocol_id": config["protocol_id"],
        "source_revision": config["source"]["revision"],
        "source_file_sha256": {
            name: source_manifest["files"][name]["sha256"] for name in REQUIRED_SOURCE_FILES
        },
        "split": split_metadata,
        "membership": membership,
    }
    audit_artifact = {
        "dataset": "Banking77",
        "protocol_id": config["protocol_id"],
        "source_revision": config["source"]["revision"],
        "source_file_sha256": split_manifest["source_file_sha256"],
        "audit": audit,
        "locked_split": split_metadata,
    }
    return {
        "split_manifest": split_manifest,
        "audit_json": audit_artifact,
        "audit_markdown": render_audit_markdown(audit_artifact),
    }


def render_audit_markdown(artifact: dict[str, Any]) -> str:
    audit = artifact["audit"]
    integrity = audit["integrity"]
    split = artifact["locked_split"]
    source_hashes = artifact["source_file_sha256"]
    official_train_values = list(audit["labels"]["official_train_distribution"].values())
    official_test_values = list(audit["labels"]["official_test_distribution"].values())
    locked_distributions = split["class_distribution"]
    normalized_overlap = integrity[
        "official_train_test_case_whitespace_normalized_overlap"
    ]

    def escape(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", " ")

    lines = [
        "# Banking77 Data Audit — W1-001",
        "",
        f"- Protocol: `{artifact['protocol_id']}`",
        f"- Authoritative upstream revision: `{artifact['source_revision']}`",
        "- Official `test.csv` is frozen and excluded from tuning.",
        "",
        "## Source checksums",
        "",
    ]
    lines.extend(f"- `{name}`: `{value}`" for name, value in source_hashes.items())
    lines.extend(
        [
            "",
            "## Actual sample and label counts",
            "",
            f"- Official train: {audit['sample_counts']['official_train']}",
            f"- Official test: {audit['sample_counts']['official_test']}",
            f"- Total: {audit['sample_counts']['total']}",
            f"- Intents: {audit['labels']['count']}",
            f"- Official-train class range: {min(official_train_values)}–{max(official_train_values)}",
            f"- Official-test class range: {min(official_test_values)}–{max(official_test_values)}",
            f"- Locked-train class range: {min(locked_distributions['train'].values())}–{max(locked_distributions['train'].values())}",
            f"- Validation class range: {min(locked_distributions['validation'].values())}–{max(locked_distributions['validation'].values())}",
            "",
            "## Integrity findings",
            "",
            f"- Empty text rows: {integrity['empty_text_rows']}",
            f"- Empty label rows: {integrity['empty_label_rows']}",
            f"- Invalid-label rows: {audit['labels']['invalid_label_rows']}",
            f"- Exact-query duplicate groups: {integrity['exact_query_duplicates']['groups']}",
            f"- Exact query-label duplicate groups: {integrity['exact_query_label_duplicates']['groups']}",
            f"- Conflicting-label query groups: {integrity['conflicting_label_queries']['groups']}",
            f"- Official train/test exact overlap: {integrity['official_train_test_exact_overlap']['distinct_queries']}",
            "- Official train/test case+whitespace-normalized overlap: "
            f"{normalized_overlap['distinct_queries']} "
            f"({normalized_overlap['label_consistent_queries']} label-consistent, "
            f"{normalized_overlap['label_conflicting_queries']} label-conflicting)",
            "- Decision: preserve the authoritative official boundary and flag "
            f"the {normalized_overlap['distinct_queries']} normalized overlaps as an evaluation "
            "limitation; do not remove or tune on test data.",
            "",
            "### Normalized official train/test overlap cases",
            "",
            "| Normalized query | Train label/text | Test label/text |",
            "|---|---|---|",
        ]
    )
    lines.extend(
        "| "
        + escape(item["comparison_key"])
        + " | "
        + escape("; ".join(f"{row['label']}: {row['text']}" for row in item["train"]))
        + " | "
        + escape("; ".join(f"{row['label']}: {row['text']}" for row in item["test"]))
        + " |"
        for item in normalized_overlap["examples"]
    )
    lines.extend(
        [
            "",
            "## Unusually short queries",
            "",
            f"- Up to 1 token: {audit['short_queries']['counts_by_max_tokens']['1']}",
            f"- Up to 2 tokens: {audit['short_queries']['counts_by_max_tokens']['2']}",
            f"- Up to 3 tokens: {audit['short_queries']['counts_by_max_tokens']['3']}",
            "",
            "| Tokens | Label | Text |",
            "|---:|---|---|",
        ]
    )
    lines.extend(
        f"| {item['tokens']} | `{item['label']}` | {escape(item['text'])} |"
        for item in audit["short_queries"]["shortest_examples"][:10]
    )
    lines.extend(
        [
            "",
            "## Locked protocol",
            "",
            f"- Strategy: `{split['strategy']}`",
            f"- Seed: `{split['seed']}`",
            f"- Train: {split['counts']['train']}",
            f"- Validation: {split['counts']['validation']}",
            f"- Locked test: {split['counts']['test']}",
            f"- Combined membership SHA-256: `{split['combined_membership_sha256']}`",
            "",
            "Detailed class distributions, short-query samples, membership IDs, and all counts are in the JSON artifacts.",
            "",
        ]
    )
    return "\n".join(lines)


def write_locked_artifacts(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    artifacts = build_artifacts(root, config)
    for key, config_key in (
        ("split_manifest", "split_manifest"),
        ("audit_json", "audit_json"),
    ):
        path = resolve_repo_path(root, config["paths"][config_key])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_json_bytes(artifacts[key]))
    markdown_path = resolve_repo_path(root, config["paths"]["audit_markdown"])
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(artifacts["audit_markdown"], encoding="utf-8", newline="\n")
    return artifacts


def verify_locked_artifacts(root: Path, config: dict[str, Any]) -> dict[str, str]:
    source_manifest_path = resolve_repo_path(root, config["paths"]["source_manifest"])
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    raw_directory = resolve_repo_path(root, config["paths"]["raw_directory"])
    for filename in REQUIRED_SOURCE_FILES:
        expected = config["source"]["files"][filename].get("sha256")
        if not expected:
            raise Banking77Error(f"Config is missing locked checksum for {filename}")
        actual = sha256_file(raw_directory / filename)
        if actual != expected or source_manifest["files"][filename]["sha256"] != expected:
            raise Banking77Error(f"Source checksum verification failed for {filename}")

    artifacts = build_artifacts(root, config)
    checksums: dict[str, str] = {}
    for key, config_key in (
        ("split_manifest", "split_manifest"),
        ("audit_json", "audit_json"),
    ):
        expected_bytes = canonical_json_bytes(artifacts[key])
        path = resolve_repo_path(root, config["paths"][config_key])
        if path.read_bytes() != expected_bytes:
            raise Banking77Error(f"Locked artifact differs from deterministic rerun: {path}")
        checksums[config_key] = sha256_bytes(expected_bytes)
    markdown_bytes = artifacts["audit_markdown"].encode("utf-8")
    markdown_path = resolve_repo_path(root, config["paths"]["audit_markdown"])
    if markdown_path.read_bytes() != markdown_bytes:
        raise Banking77Error(f"Audit Markdown differs from deterministic rerun: {markdown_path}")
    checksums["audit_markdown"] = sha256_bytes(markdown_bytes)
    return checksums
