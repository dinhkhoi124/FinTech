"""W1-002 TF-IDF + Logistic Regression validation baseline.

This module deliberately has no code path that loads ``test.csv``. Model
selection is restricted to the locked training and validation membership from
W1-001; the official test set remains reserved for W1-004.
"""

from __future__ import annotations

import csv
import gzip
import importlib.metadata
import json
import platform
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_limits

from payresolve_ai.data.banking77 import (
    Banking77Error,
    Example,
    canonical_json_bytes,
    load_categories,
    load_config as load_data_config,
    load_examples,
    resolve_repo_path,
    sha256_bytes,
    sha256_file,
)


ALLOWED_ESTIMATOR = "sklearn.pipeline.Pipeline(TfidfVectorizer,LogisticRegression)"
MODEL_SELECTION_SPLITS = frozenset({"train", "validation"})
DEPENDENCIES = ("numpy", "scipy", "scikit-learn", "joblib", "threadpoolctl")


class LexicalBaselineError(ValueError):
    """Raised when W1-002 violates its frozen experiment contract."""


@dataclass(frozen=True)
class LockedDevelopmentData:
    categories: list[str]
    train: list[Example]
    validation: list[Example]
    protocol_id: str
    source_revision: str
    combined_membership_sha256: str
    split_manifest_sha256: str


def load_lexical_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("task_id") != "W1-002":
        raise LexicalBaselineError("task_id must be W1-002")
    if config.get("estimator") != ALLOWED_ESTIMATOR:
        raise LexicalBaselineError(f"estimator must be exactly {ALLOWED_ESTIMATOR}")
    if config.get("selection", {}).get("metric") != "macro_f1":
        raise LexicalBaselineError("selection.metric must be macro_f1")
    candidates = config.get("candidates")
    if not isinstance(candidates, list) or len(candidates) not in (1, 2):
        raise LexicalBaselineError("W1-002 permits one or two controlled candidates only")
    candidate_ids: set[str] = set()
    for candidate in candidates:
        candidate_id = candidate.get("id")
        if not isinstance(candidate_id, str) or not candidate_id or candidate_id in candidate_ids:
            raise LexicalBaselineError("candidate IDs must be unique non-empty strings")
        candidate_ids.add(candidate_id)
        tfidf = candidate.get("tfidf", {})
        if sorted(tfidf) != ["lowercase", "min_df", "ngram_range", "sublinear_tf"]:
            raise LexicalBaselineError("candidate TF-IDF keys are outside the controlled contract")
        ngram_range = tfidf.get("ngram_range")
        if ngram_range not in ([1, 1], [1, 2]):
            raise LexicalBaselineError("only word unigrams or word uni+bigrams are permitted")
        logistic = candidate.get("logistic_regression", {})
        if sorted(logistic) != ["C", "max_iter", "random_state", "solver"]:
            raise LexicalBaselineError("candidate LogisticRegression keys violate the contract")
        if logistic.get("solver") != "lbfgs" or logistic.get("random_state") != config.get("seed"):
            raise LexicalBaselineError("all candidates must use lbfgs and the experiment seed")
    output_paths = config.get("outputs", {})
    required_outputs = {
        "model",
        "metrics",
        "per_class",
        "predictions",
        "confusions",
        "manifest",
    }
    if set(output_paths) != required_outputs:
        raise LexicalBaselineError(f"outputs must contain exactly {sorted(required_outputs)}")
    if not str(output_paths["model"]).replace("\\", "/").startswith("artifacts/"):
        raise LexicalBaselineError("fitted model must be written under ignored artifacts/")
    return config


def _partition_official_train(
    examples: list[Example], membership: dict[str, list[str]]
) -> tuple[list[Example], list[Example]]:
    train_ids = set(membership.get("train", []))
    validation_ids = set(membership.get("validation", []))
    test_ids = set(membership.get("test", []))
    if train_ids & validation_ids or train_ids & test_ids or validation_ids & test_ids:
        raise LexicalBaselineError("locked split membership is not disjoint")
    observed_ids = {example.sample_id for example in examples}
    expected_ids = train_ids | validation_ids
    if observed_ids != expected_ids:
        raise LexicalBaselineError("official train rows do not match locked train+validation IDs")
    by_id = {example.sample_id: example for example in examples}
    return (
        [by_id[sample_id] for sample_id in sorted(train_ids)],
        [by_id[sample_id] for sample_id in sorted(validation_ids)],
    )


def load_locked_train_validation(
    root: Path, data_config_path: Path
) -> LockedDevelopmentData:
    """Load only official train content and partition it by the W1-001 manifest."""
    data_config = load_data_config(data_config_path)
    raw_directory = resolve_repo_path(root, data_config["paths"]["raw_directory"])
    categories_path = raw_directory / "categories.json"
    official_train_path = raw_directory / "train.csv"
    for name, path in (("categories.json", categories_path), ("train.csv", official_train_path)):
        expected = data_config["source"]["files"][name]["sha256"]
        actual = sha256_file(path)
        if actual != expected:
            raise LexicalBaselineError(f"source checksum mismatch for {name}: {actual}")

    split_manifest_path = resolve_repo_path(root, data_config["paths"]["split_manifest"])
    manifest = json.loads(split_manifest_path.read_text(encoding="utf-8"))
    split = manifest.get("split", {})
    if manifest.get("protocol_id") != data_config["protocol_id"]:
        raise LexicalBaselineError("split protocol does not match data config")
    if manifest.get("source_revision") != data_config["source"]["revision"]:
        raise LexicalBaselineError("split source revision does not match data config")
    if split.get("official_test_frozen") is not True:
        raise LexicalBaselineError("official test must remain frozen")
    membership = manifest.get("membership", {})
    combined_hash = sha256_bytes(canonical_json_bytes(membership))
    if combined_hash != split.get("combined_membership_sha256"):
        raise LexicalBaselineError("combined membership hash mismatch")

    # Intentionally no reference to raw_directory / "test.csv" below this point.
    categories = load_categories(categories_path)
    official_train = load_examples(official_train_path)
    train, validation = _partition_official_train(official_train, membership)
    if set(example.label for example in train) != set(categories):
        raise LexicalBaselineError("locked training split does not contain all categories")
    if any(example.label not in set(categories) for example in validation):
        raise LexicalBaselineError("validation contains a label outside categories.json")
    return LockedDevelopmentData(
        categories=categories,
        train=train,
        validation=validation,
        protocol_id=manifest["protocol_id"],
        source_revision=manifest["source_revision"],
        combined_membership_sha256=combined_hash,
        split_manifest_sha256=sha256_file(split_manifest_path),
    )


def build_pipeline(candidate: dict[str, Any]) -> Pipeline:
    tfidf = candidate["tfidf"]
    logistic = candidate["logistic_regression"]
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=tfidf["lowercase"],
                    min_df=tfidf["min_df"],
                    ngram_range=tuple(tfidf["ngram_range"]),
                    sublinear_tf=tfidf["sublinear_tf"],
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    C=logistic["C"],
                    max_iter=logistic["max_iter"],
                    random_state=logistic["random_state"],
                    solver=logistic["solver"],
                ),
            ),
        ]
    )


def _evaluate(labels: list[str], predicted: list[str], categories: list[str]) -> dict[str, Any]:
    precision, recall, f1, support = precision_recall_fscore_support(
        labels, predicted, labels=categories, zero_division=0
    )
    per_class = [
        {
            "label": label,
            "precision": float(precision[index]),
            "recall": float(recall[index]),
            "f1": float(f1[index]),
            "support": int(support[index]),
        }
        for index, label in enumerate(categories)
    ]
    return {
        "accuracy": float(accuracy_score(labels, predicted)),
        "macro_f1": float(sum(item["f1"] for item in per_class) / len(per_class)),
        "per_class": per_class,
    }


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _dependency_versions() -> dict[str, str]:
    return {name: importlib.metadata.version(name) for name in DEPENDENCIES}


def _write_portable_model(path: Path, pipeline: Pipeline, candidate: dict[str, Any]) -> None:
    """Persist fitted inference parameters in a byte-stable, library-neutral form."""
    vectorizer = pipeline.named_steps["tfidf"]
    classifier = pipeline.named_steps["classifier"]
    payload = {
        "format": "payresolve-lexical-parameters-v1",
        "candidate": candidate,
        "vocabulary": dict(sorted(vectorizer.vocabulary_.items())),
        "idf": vectorizer.idf_.tolist(),
        "classes": classifier.classes_.tolist(),
        "coefficients": classifier.coef_.tolist(),
        "intercept": classifier.intercept_.tolist(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(canonical_json_bytes(payload), compresslevel=9, mtime=0))


def run_validation(root: Path, config_path: Path) -> dict[str, Any]:
    root = root.resolve()
    config = load_lexical_config(config_path)
    data_config_path = resolve_repo_path(root, config["data_config"])
    data = load_locked_train_validation(root, data_config_path)
    if data.combined_membership_sha256 != config["locked_combined_membership_sha256"]:
        raise LexicalBaselineError("lexical config is not pinned to the loaded membership hash")

    train_text = [example.text for example in data.train]
    train_labels = [example.label for example in data.train]
    validation_text = [example.text for example in data.validation]
    validation_labels = [example.label for example in data.validation]
    runs: list[dict[str, Any]] = []
    fitted: dict[str, Pipeline] = {}
    predicted_by_id: dict[str, list[str]] = {}
    # Fixed single-thread numerical execution makes the fitted coefficients and
    # serialized model reproducible, not only the discrete predictions.
    with threadpool_limits(limits=1):
        for candidate in config["candidates"]:
            pipeline = build_pipeline(candidate)
            pipeline.fit(train_text, train_labels)
            predicted = list(pipeline.predict(validation_text))
            evaluation = _evaluate(validation_labels, predicted, data.categories)
            candidate_id = candidate["id"]
            fitted[candidate_id] = pipeline
            predicted_by_id[candidate_id] = predicted
            runs.append(
                {
                    "candidate_id": candidate_id,
                    "accuracy": evaluation["accuracy"],
                    "macro_f1": evaluation["macro_f1"],
                    "feature_count": len(pipeline.named_steps["tfidf"].vocabulary_),
                }
            )

    selected_run = max(runs, key=lambda item: (item["macro_f1"], item["accuracy"], item["candidate_id"]))
    selected_id = selected_run["candidate_id"]
    selected_candidate = next(item for item in config["candidates"] if item["id"] == selected_id)
    selected_model = fitted[selected_id]
    selected_predictions = predicted_by_id[selected_id]
    selected_evaluation = _evaluate(validation_labels, selected_predictions, data.categories)

    output_paths = {
        name: resolve_repo_path(root, relative) for name, relative in config["outputs"].items()
    }
    predictions_rows = [
        {
            "sample_id": example.sample_id,
            "true_label": example.label,
            "predicted_label": predicted,
            "correct": str(example.label == predicted).lower(),
        }
        for example, predicted in zip(data.validation, selected_predictions, strict=True)
    ]
    confusion_counts = Counter(
        (row["true_label"], row["predicted_label"])
        for row in predictions_rows
        if row["correct"] == "false"
    )
    confusion_rows = [
        {"true_label": true, "predicted_label": predicted, "count": count}
        for (true, predicted), count in sorted(
            confusion_counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1])
        )
    ]
    _write_csv(
        output_paths["predictions"],
        ["sample_id", "true_label", "predicted_label", "correct"],
        predictions_rows,
    )
    _write_csv(
        output_paths["per_class"],
        ["label", "precision", "recall", "f1", "support"],
        selected_evaluation["per_class"],
    )
    _write_csv(output_paths["confusions"], ["true_label", "predicted_label", "count"], confusion_rows)
    _write_portable_model(output_paths["model"], selected_model, selected_candidate)

    metrics = {
        "task_id": "W1-002",
        "evaluation_scope": "locked_validation_only",
        "test_evaluated": False,
        "selection_metric": "macro_f1",
        "candidate_results": runs,
        "selected_candidate_id": selected_id,
        "selected_validation_metrics": {
            "accuracy": selected_evaluation["accuracy"],
            "macro_f1": selected_evaluation["macro_f1"],
        },
        "counts": {"train": len(data.train), "validation": len(data.validation), "classes": len(data.categories)},
    }
    output_paths["metrics"].parent.mkdir(parents=True, exist_ok=True)
    output_paths["metrics"].write_bytes(canonical_json_bytes(metrics))
    evidence_hashes = {
        key: sha256_file(output_paths[key])
        for key in ("metrics", "per_class", "predictions", "confusions", "model")
    }
    manifest = {
        "task_id": "W1-002",
        "model_family": "TF-IDF + Logistic Regression",
        "model_artifact_format": "payresolve-lexical-parameters-v1 (canonical JSON + gzip mtime=0)",
        "evaluation_scope": "locked_validation_only",
        "test_evaluated": False,
        "protocol_id": data.protocol_id,
        "source_revision": data.source_revision,
        "combined_membership_sha256": data.combined_membership_sha256,
        "split_manifest_sha256": data.split_manifest_sha256,
        "config_sha256": sha256_file(config_path),
        "selected_candidate": selected_candidate,
        "selected_validation_metrics": metrics["selected_validation_metrics"],
        "counts": metrics["counts"],
        "runtime": {
            "python": platform.python_version(),
            "dependencies": _dependency_versions(),
            "numerical_thread_limit": 1,
        },
        "artifacts": {
            key: {"path": config["outputs"][key], "sha256": value}
            for key, value in evidence_hashes.items()
        },
    }
    output_paths["manifest"].parent.mkdir(parents=True, exist_ok=True)
    output_paths["manifest"].write_bytes(canonical_json_bytes(manifest))
    return {"metrics": metrics, "manifest": manifest}


def inspect_validation_errors(root: Path, config_path: Path, limit: int) -> list[dict[str, str]]:
    """Return representative validation errors ordered by frequent confusion pair."""
    if limit < 1:
        return []
    config = load_lexical_config(config_path)
    data = load_locked_train_validation(root, resolve_repo_path(root, config["data_config"]))
    predictions_path = resolve_repo_path(root, config["outputs"]["predictions"])
    with predictions_path.open("r", encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    if [row["sample_id"] for row in rows] != [item.sample_id for item in data.validation]:
        raise LexicalBaselineError("prediction IDs are not aligned to locked validation membership")
    by_id = {example.sample_id: example for example in data.validation}
    confusion_counts = Counter(
        (row["true_label"], row["predicted_label"])
        for row in rows
        if row["correct"] == "false"
    )
    errors = [
        {
            "sample_id": row["sample_id"],
            "text": by_id[row["sample_id"]].text,
            "true_label": row["true_label"],
            "predicted_label": row["predicted_label"],
        }
        for row in rows
        if row["correct"] == "false"
    ]
    return sorted(
        errors,
        key=lambda row: (
            -confusion_counts[(row["true_label"], row["predicted_label"])],
            row["true_label"],
            row["predicted_label"],
            row["sample_id"],
        ),
    )[:limit]
