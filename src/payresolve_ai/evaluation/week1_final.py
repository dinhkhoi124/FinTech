"""Locked W1-004 final evaluation for the two frozen Banking77 baselines."""

from __future__ import annotations

import copy
import csv
import importlib.metadata
import json
import platform
import subprocess
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
from threadpoolctl import threadpool_limits

from payresolve_ai.baselines.lexical import (
    _evaluate,
    _write_csv,
    _write_portable_model,
    build_pipeline,
)
from payresolve_ai.baselines.semantic import (
    LoadedEncoder,
    _build_classifier,
    _directory_size,
    _encode_or_load,
    _git_state,
    _load_encoder,
    _write_portable_classifier,
    load_semantic_config,
)
from payresolve_ai.data.banking77 import (
    Example,
    canonical_json_bytes,
    load_categories,
    load_config as load_data_config,
    load_examples,
    resolve_repo_path,
    sha256_bytes,
    sha256_file,
)


TASK_ID = "W1-004"
PROTOCOL_ID = "banking77_w1_v1"
MEMBERSHIP_SHA256 = "baa3d31f3ca2ad82e8a690a5caf0efdd44d25117fa77cdae8498a0c5b721c902"
SEMANTIC_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
RUN_LABELS = {"primary", "reproducibility_rerun"}
EXPECTED_COUNTS = {"locked_train": 8998, "locked_validation": 1005, "final_fit": 10003, "official_test": 3080, "classes": 77, "official_test_per_class": 40}
REVIEW_TAXONOMY = {f"T{index}" for index in range(1, 9)}


class Week1FinalEvaluationError(ValueError):
    """Raised when a W1-004 frozen-evaluation invariant is violated."""


@dataclass(frozen=True)
class FinalEvaluationData:
    categories: list[str]
    final_fit: list[Example]
    official_test: list[Example]
    protocol_id: str
    source_revision: str
    combined_membership_sha256: str
    split_manifest_sha256: str


def load_evaluation_config(path: Path) -> dict[str, Any]:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise Week1FinalEvaluationError(f"cannot load W1-004 config: {error}") from error
    required = {
        "task_id", "status", "preregistered_date", "pretest_git_head", "data",
        "candidates", "final_fit_protocol", "evaluation", "paired_analysis",
        "overlap_sensitivity", "manual_error_review", "downstream_decision_rule",
        "p0_gate", "run_policy", "prohibited_after_test_access", "outputs",
    }
    if set(config) != required:
        raise Week1FinalEvaluationError("W1-004 config top-level keys changed")
    if config["task_id"] != TASK_ID or config["status"] != "PREREGISTERED_BEFORE_OFFICIAL_TEST_ACCESS":
        raise Week1FinalEvaluationError("W1-004 must use the preregistered task/status")
    data = config["data"]
    if data.get("protocol_id") != PROTOCOL_ID or data.get("combined_membership_sha256") != MEMBERSHIP_SHA256:
        raise Week1FinalEvaluationError("locked Banking77 protocol or membership changed")
    if data.get("counts") != EXPECTED_COUNTS:
        raise Week1FinalEvaluationError("locked Banking77 counts changed")
    final_fit = config["final_fit_protocol"]
    if final_fit.get("scope") != "locked_train_plus_locked_validation" or final_fit.get("sample_count") != 10003:
        raise Week1FinalEvaluationError("final-fit scope must be all 10,003 non-test samples")
    if final_fit.get("same_training_scope_for_both_candidates") is not True:
        raise Week1FinalEvaluationError("both candidates must use identical final-fit scope")
    candidates = config["candidates"]
    if set(candidates) != {"lexical", "semantic"}:
        raise Week1FinalEvaluationError("exactly the two frozen candidates are required")
    if any(candidate.get("status") != "FROZEN_ON_VALIDATION" for candidate in candidates.values()):
        raise Week1FinalEvaluationError("both candidates must be frozen")
    if candidates["lexical"].get("selected_candidate_id") != "word_unigram":
        raise Week1FinalEvaluationError("lexical candidate must remain word_unigram")
    if candidates["semantic"].get("model_revision") != SEMANTIC_REVISION:
        raise Week1FinalEvaluationError("semantic revision changed")
    if config["evaluation"].get("scope") != "official_frozen_test":
        raise Week1FinalEvaluationError("evaluation scope must be official frozen test")
    if set(config["run_policy"].get("allowed", [])) != RUN_LABELS:
        raise Week1FinalEvaluationError("only primary and reproducibility rerun are allowed")
    if config["downstream_decision_rule"].get("third_model_allowed") is not False:
        raise Week1FinalEvaluationError("a third model is prohibited")
    return config


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise Week1FinalEvaluationError(f"cannot read JSON artifact {path}: {error}") from error


def _verify_hash(root: Path, relative: str, expected: str, label: str) -> Path:
    path = resolve_repo_path(root, relative)
    actual = sha256_file(path)
    if actual != expected:
        raise Week1FinalEvaluationError(f"{label} hash mismatch: {actual}")
    return path


def _implementation_hashes() -> dict[str, str]:
    module = Path(__file__)
    cli = module.with_name("week1_final_cli.py")
    return {"evaluation_module_sha256": sha256_file(module), "evaluation_cli_sha256": sha256_file(cli)}


def verify_pretest_gate(root: Path, config_path: Path) -> dict[str, Any]:
    """Verify all frozen contracts without loading official test examples."""
    root = root.resolve()
    config = load_evaluation_config(config_path)
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise Week1FinalEvaluationError("Git HEAD unavailable for pre-test gate") from error
    if head != config["pretest_git_head"]:
        raise Week1FinalEvaluationError("pre-test Git HEAD differs from preregistration")
    data = config["data"]
    split_path = _verify_hash(root, data["split_manifest"], data["split_manifest_sha256"], "split manifest")
    split_manifest = _read_json(split_path)
    split = split_manifest.get("split", {})
    if split_manifest.get("protocol_id") != PROTOCOL_ID or split.get("combined_membership_sha256") != MEMBERSHIP_SHA256:
        raise Week1FinalEvaluationError("split manifest contract mismatch")
    if split.get("official_test_frozen") is not True or split.get("counts") != {"test": 3080, "train": 8998, "validation": 1005}:
        raise Week1FinalEvaluationError("official test is not frozen with expected counts")
    for name, candidate in config["candidates"].items():
        config_file = _verify_hash(root, candidate["config"], candidate["config_sha256"], f"{name} config")
        manifest_file = _verify_hash(root, candidate["manifest"], candidate["manifest_sha256"], f"{name} manifest")
        _verify_hash(root, candidate["requirements"], candidate["requirements_sha256"], f"{name} requirements")
        manifest = _read_json(manifest_file)
        if manifest.get("combined_membership_sha256") != MEMBERSHIP_SHA256:
            raise Week1FinalEvaluationError(f"{name} manifest membership mismatch")
        if manifest.get("test_evaluated") is not False:
            raise Week1FinalEvaluationError(f"{name} manifest indicates prior test evaluation")
        if name == "lexical":
            if manifest.get("config_sha256") != candidate["config_sha256"] or manifest.get("selected_candidate", {}).get("id") != "word_unigram":
                raise Week1FinalEvaluationError("lexical frozen selection mismatch")
        else:
            if manifest.get("test_encoded") is not False or manifest.get("semantic_config_sha256") != candidate["config_sha256"]:
                raise Week1FinalEvaluationError("semantic frozen manifest mismatch")
            semantic = load_semantic_config(config_file)
            if semantic["encoder"]["revision"] != SEMANTIC_REVISION:
                raise Week1FinalEvaluationError("semantic exact revision mismatch")
    existing = [relative for relative in config["outputs"].values() if resolve_repo_path(root, relative).exists()]
    if existing:
        raise Week1FinalEvaluationError(f"official-test artifacts already exist before primary run: {existing}")
    return {
        "task_id": TASK_ID,
        "git_head": head,
        "evaluation_config_sha256": sha256_file(config_path),
        "protocol_id": PROTOCOL_ID,
        "combined_membership_sha256": MEMBERSHIP_SHA256,
        "counts": EXPECTED_COUNTS,
        "lexical_frozen": True,
        "semantic_frozen": True,
        "semantic_revision": SEMANTIC_REVISION,
        "prior_test_artifacts": 0,
        "prior_test_encoded": False,
        "prior_test_evaluated": False,
    }


def load_final_evaluation_data(root: Path, config: dict[str, Any]) -> FinalEvaluationData:
    """First authorized content access to the official test under W1-004."""
    data_cfg_path = resolve_repo_path(root, config["data"]["config"])
    data_cfg = load_data_config(data_cfg_path)
    raw = resolve_repo_path(root, data_cfg["paths"]["raw_directory"])
    for filename in ("categories.json", "train.csv", "test.csv"):
        actual = sha256_file(raw / filename)
        expected = data_cfg["source"]["files"][filename]["sha256"]
        if actual != expected:
            raise Week1FinalEvaluationError(f"source checksum mismatch for {filename}: {actual}")
    manifest_path = resolve_repo_path(root, config["data"]["split_manifest"])
    manifest = _read_json(manifest_path)
    membership = manifest.get("membership", {})
    if sha256_bytes(canonical_json_bytes(membership)) != MEMBERSHIP_SHA256:
        raise Week1FinalEvaluationError("locked membership payload hash mismatch")
    categories = load_categories(raw / "categories.json")
    official_train = load_examples(raw / "train.csv")
    official_test = load_examples(raw / "test.csv")
    final_fit_ids = set(membership.get("train", [])) | set(membership.get("validation", []))
    test_ids = set(membership.get("test", []))
    if {item.sample_id for item in official_train} != final_fit_ids:
        raise Week1FinalEvaluationError("official train does not match locked train+validation membership")
    if {item.sample_id for item in official_test} != test_ids:
        raise Week1FinalEvaluationError("official test does not match locked test membership")
    final_fit = sorted(official_train, key=lambda item: item.sample_id)
    test = sorted(official_test, key=lambda item: item.sample_id)
    if len(final_fit) != 10003 or len(test) != 3080 or len(categories) != 77:
        raise Week1FinalEvaluationError("final evaluation counts mismatch")
    distribution = Counter(item.label for item in test)
    if set(distribution) != set(categories) or set(distribution.values()) != {40}:
        raise Week1FinalEvaluationError("official test must contain all 77 labels with support 40")
    return FinalEvaluationData(
        categories=categories,
        final_fit=final_fit,
        official_test=test,
        protocol_id=manifest["protocol_id"],
        source_revision=manifest["source_revision"],
        combined_membership_sha256=MEMBERSHIP_SHA256,
        split_manifest_sha256=sha256_file(manifest_path),
    )


def _selected_lexical_candidate(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    candidate_cfg = config["candidates"]["lexical"]
    lexical_config = _read_json(resolve_repo_path(root, candidate_cfg["config"]))
    manifest = _read_json(resolve_repo_path(root, candidate_cfg["manifest"]))
    selected = manifest["selected_candidate"]
    matching = [item for item in lexical_config["candidates"] if item["id"] == selected["id"]]
    if len(matching) != 1 or matching[0] != selected:
        raise Week1FinalEvaluationError("lexical selected candidate differs from frozen config")
    return selected


def _prediction_rows(
    examples: list[Example], classes: list[str], probabilities: np.ndarray
) -> list[dict[str, Any]]:
    if probabilities.shape != (len(examples), len(classes)):
        raise Week1FinalEvaluationError("probability matrix shape mismatch")
    rows: list[dict[str, Any]] = []
    for example, values in zip(examples, probabilities, strict=True):
        order = np.argsort(values)
        top = int(order[-1])
        second = int(order[-2])
        predicted = classes[top]
        rows.append(
            {
                "sample_id": example.sample_id,
                "true_label": example.label,
                "predicted_label": predicted,
                "correct": str(example.label == predicted).lower(),
                "confidence": float(values[top]),
                "margin": float(values[top] - values[second]),
            }
        )
    return rows


def _metric_payload(model: str, data: FinalEvaluationData, rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    labels = [row["true_label"] for row in rows]
    predicted = [row["predicted_label"] for row in rows]
    evaluation = _evaluate(labels, predicted, data.categories)
    correct = sum(row["correct"] == "true" for row in rows)
    metrics = {
        "task_id": TASK_ID,
        "model": model,
        "evaluation_scope": "official_frozen_test",
        "test_evaluated": True,
        "accuracy": evaluation["accuracy"],
        "macro_f1": evaluation["macro_f1"],
        "correct_count": correct,
        "error_count": len(rows) - correct,
        "counts": {"final_fit": 10003, "test": 3080, "classes": 77},
    }
    counts = Counter(
        (row["true_label"], row["predicted_label"])
        for row in rows if row["correct"] == "false"
    )
    confusions = [
        {"true_label": true, "predicted_label": pred, "count": count}
        for (true, pred), count in sorted(counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1]))
    ]
    return metrics, evaluation["per_class"], confusions


def _write_model_evidence(root: Path, config: dict[str, Any], prefix: str, rows: list[dict[str, Any]], metrics: dict[str, Any], per_class: list[dict[str, Any]], confusions: list[dict[str, Any]]) -> None:
    outputs = config["outputs"]
    resolve_repo_path(root, outputs[f"{prefix}_metrics"]).write_bytes(canonical_json_bytes(metrics))
    _write_csv(resolve_repo_path(root, outputs[f"{prefix}_per_class"]), ["label", "precision", "recall", "f1", "support"], per_class)
    _write_csv(resolve_repo_path(root, outputs[f"{prefix}_predictions"]), ["sample_id", "true_label", "predicted_label", "correct", "confidence", "margin"], rows)
    _write_csv(resolve_repo_path(root, outputs[f"{prefix}_confusions"]), ["true_label", "predicted_label", "count"], confusions)


def _fit_lexical(root: Path, config: dict[str, Any], data: FinalEvaluationData) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidate = _selected_lexical_candidate(root, config)
    pipeline = build_pipeline(candidate)
    vectorizer = pipeline.named_steps["tfidf"]
    classifier = pipeline.named_steps["classifier"]
    train_text = [item.text for item in data.final_fit]
    train_labels = [item.label for item in data.final_fit]
    test_text = [item.text for item in data.official_test]
    total_start = time.perf_counter()
    fit_vector_start = time.perf_counter()
    final_features = vectorizer.fit_transform(train_text)
    fit_vector_seconds = time.perf_counter() - fit_vector_start
    fit_start = time.perf_counter()
    with threadpool_limits(limits=1):
        classifier.fit(final_features, train_labels)
    classifier_fit_seconds = time.perf_counter() - fit_start
    vector_start = time.perf_counter()
    test_features = vectorizer.transform(test_text)
    test_vectorization_seconds = time.perf_counter() - vector_start
    prediction_start = time.perf_counter()
    with threadpool_limits(limits=1):
        probabilities = classifier.predict_proba(test_features)
    prediction_seconds = time.perf_counter() - prediction_start
    rows = _prediction_rows(data.official_test, list(classifier.classes_), probabilities)
    model_path = resolve_repo_path(root, config["outputs"]["lexical_model"])
    _write_portable_model(model_path, pipeline, candidate)
    runtime = {
        "final_fit_vectorization_seconds": fit_vector_seconds,
        "classifier_fit_seconds": classifier_fit_seconds,
        "test_vectorization_seconds": test_vectorization_seconds,
        "classifier_prediction_seconds": prediction_seconds,
        "total_seconds": time.perf_counter() - total_start,
        "feature_dimension": int(test_features.shape[1]),
        "model_artifact_bytes": model_path.stat().st_size,
        "numerical_thread_limit": 1,
    }
    return rows, runtime


def _semantic_cache_key(config_path: Path, data: FinalEvaluationData) -> str:
    return sha256_bytes(canonical_json_bytes({
        "task_id": TASK_ID,
        "evaluation_config_sha256": sha256_file(config_path),
        "membership": data.combined_membership_sha256,
        "model_revision": SEMANTIC_REVISION,
        "final_fit_order": "stable_sample_id_ascending",
        "test_order": "stable_sample_id_ascending",
    }))


def _fit_semantic(
    root: Path,
    config_path: Path,
    config: dict[str, Any],
    data: FinalEvaluationData,
    encoder_loader: Callable[[Path, dict[str, Any]], LoadedEncoder] = _load_encoder,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    semantic_config_path = resolve_repo_path(root, config["candidates"]["semantic"]["config"])
    semantic = copy.deepcopy(load_semantic_config(semantic_config_path))
    semantic["cache"]["directory"] = config["outputs"]["semantic_cache"]
    encoder = encoder_loader(root, semantic)
    key = _semantic_cache_key(config_path, data)
    total_start = time.perf_counter()
    final_embeddings, final_meta, _, final_seconds = _encode_or_load(
        root, semantic, encoder, key, "final_fit",
        [item.sample_id for item in data.final_fit],
        [item.text for item in data.final_fit], True,
    )
    test_embeddings, test_meta, _, test_seconds = _encode_or_load(
        root, semantic, encoder, key, "official_test",
        [item.sample_id for item in data.official_test],
        [item.text for item in data.official_test], True,
    )
    classifier = _build_classifier(semantic)
    fit_start = time.perf_counter()
    with threadpool_limits(limits=semantic["classifier"]["numerical_thread_limit"]):
        classifier.fit(final_embeddings, [item.label for item in data.final_fit])
    fit_seconds = time.perf_counter() - fit_start
    prediction_start = time.perf_counter()
    with threadpool_limits(limits=semantic["classifier"]["numerical_thread_limit"]):
        probabilities = classifier.predict_proba(test_embeddings)
    prediction_seconds = time.perf_counter() - prediction_start
    rows = _prediction_rows(data.official_test, list(classifier.classes_), probabilities)
    model_path = resolve_repo_path(root, config["outputs"]["semantic_model"])
    _write_portable_classifier(model_path, classifier, semantic)
    runtime = {
        "model_load_seconds": encoder.load_seconds,
        "final_fit_encoding_seconds": final_seconds,
        "test_encoding_seconds": test_seconds,
        "classifier_fit_seconds": fit_seconds,
        "classifier_prediction_seconds": prediction_seconds,
        "total_seconds": time.perf_counter() - total_start + encoder.load_seconds,
        "embedding_dimension": semantic["encoder"]["expected_dimension"],
        "batch_size": semantic["encoder"]["batch_size"],
        "device": semantic["encoder"]["device"],
        "model_artifact_bytes": model_path.stat().st_size,
        "huggingface_cache_footprint_bytes": encoder.cache_footprint_bytes,
        "embedding_cache_footprint_bytes": _directory_size(resolve_repo_path(root, semantic["cache"]["directory"])),
        "cache_refreshed": True,
    }
    embedding = {
        "cache_key": key,
        "test_encoded": True,
        "cache_payload_tracked": False,
        "splits": {
            "final_fit": {name: value for name, value in final_meta.items() if name != "sample_ids"},
            "official_test": {name: value for name, value in test_meta.items() if name != "sample_ids"},
        },
        "model_provenance": encoder.provenance,
    }
    return rows, runtime, embedding


def _benchmark_rows(
    lexical_metrics: dict[str, Any], semantic_metrics: dict[str, Any],
    lexical_runtime: dict[str, Any], semantic_runtime: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "model": "lexical_word_unigram",
            "representation": "TF-IDF word unigram",
            "test_accuracy": lexical_metrics["accuracy"],
            "test_macro_f1": lexical_metrics["macro_f1"],
            "correct": lexical_metrics["correct_count"],
            "errors": lexical_metrics["error_count"],
            "dimension": lexical_runtime["feature_dimension"],
            "final_runtime_seconds": lexical_runtime["total_seconds"],
        },
        {
            "model": "semantic_all_minilm_l6_v2",
            "representation": "normalized frozen MiniLM embeddings",
            "test_accuracy": semantic_metrics["accuracy"],
            "test_macro_f1": semantic_metrics["macro_f1"],
            "correct": semantic_metrics["correct_count"],
            "errors": semantic_metrics["error_count"],
            "dimension": semantic_runtime["embedding_dimension"],
            "final_runtime_seconds": semantic_runtime["total_seconds"],
        },
    ]


def build_paired_rows(
    lexical: list[dict[str, Any]], semantic: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    lexical_by_id = {row["sample_id"]: row for row in lexical}
    semantic_by_id = {row["sample_id"]: row for row in semantic}
    if len(lexical_by_id) != 3080 or set(lexical_by_id) != set(semantic_by_id):
        raise Week1FinalEvaluationError("paired predictions are not one-to-one on 3,080 IDs")
    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for sample_id in sorted(lexical_by_id):
        left = lexical_by_id[sample_id]
        right = semantic_by_id[sample_id]
        if left["true_label"] != right["true_label"]:
            raise Week1FinalEvaluationError("paired true labels differ")
        left_correct = left["correct"] == "true"
        right_correct = right["correct"] == "true"
        if left_correct and right_correct:
            category = "both_correct"
        elif left_correct:
            category = "lexical_correct_semantic_wrong"
        elif right_correct:
            category = "lexical_wrong_semantic_correct"
        else:
            category = "both_wrong"
        counts[category] += 1
        rows.append({
            "sample_id": sample_id,
            "true_label": left["true_label"],
            "lexical_prediction": left["predicted_label"],
            "semantic_prediction": right["predicted_label"],
            "lexical_correct": str(left_correct).lower(),
            "semantic_correct": str(right_correct).lower(),
            "lexical_confidence": left["confidence"],
            "semantic_confidence": right["confidence"],
            "lexical_margin": left["margin"],
            "semantic_margin": right["margin"],
            "disagreement_category": category,
        })
    if sum(counts.values()) != 3080:
        raise Week1FinalEvaluationError("paired counts do not sum to official test size")
    return rows, dict(sorted(counts.items()))


def _per_class_comparison(
    lexical_per_class: list[dict[str, Any]], semantic_per_class: list[dict[str, Any]],
    lexical_rows: list[dict[str, Any]], semantic_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    left = {row["label"]: row for row in lexical_per_class}
    right = {row["label"]: row for row in semantic_per_class}
    if set(left) != set(right) or len(left) != 77:
        raise Week1FinalEvaluationError("per-class labels do not match all 77 intents")
    left_errors = Counter(row["true_label"] for row in lexical_rows if row["correct"] == "false")
    right_errors = Counter(row["true_label"] for row in semantic_rows if row["correct"] == "false")
    rows: list[dict[str, Any]] = []
    for label in sorted(left):
        if left[label]["support"] != 40 or right[label]["support"] != 40:
            raise Week1FinalEvaluationError("every official-test class support must be 40")
        delta = float(right[label]["f1"] - left[label]["f1"])
        rows.append({
            "label": label,
            "support": 40,
            "lexical_f1": left[label]["f1"],
            "semantic_f1": right[label]["f1"],
            "f1_delta_semantic_minus_lexical": delta,
            "lexical_errors": left_errors[label],
            "semantic_errors": right_errors[label],
            "error_delta_semantic_minus_lexical": right_errors[label] - left_errors[label],
        })
    summary = {
        "improved": sum(row["f1_delta_semantic_minus_lexical"] > 0 for row in rows),
        "regressed": sum(row["f1_delta_semantic_minus_lexical"] < 0 for row in rows),
        "unchanged": sum(row["f1_delta_semantic_minus_lexical"] == 0 for row in rows),
        "material_regressions_at_least_0_20": [
            row["label"] for row in rows if row["f1_delta_semantic_minus_lexical"] <= -0.20
        ],
    }
    return rows, summary


def _confusion_analysis(
    lexical_confusions: list[dict[str, Any]], semantic_confusions: list[dict[str, Any]]
) -> dict[str, Any]:
    def mapping(rows: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
        return {(row["true_label"], row["predicted_label"]): int(row["count"]) for row in rows}

    lexical = mapping(lexical_confusions)
    semantic = mapping(semantic_confusions)
    all_pairs = set(lexical) | set(semantic)
    comparison = [
        {
            "true_label": pair[0],
            "predicted_label": pair[1],
            "lexical_count": lexical.get(pair, 0),
            "semantic_count": semantic.get(pair, 0),
            "delta_semantic_minus_lexical": semantic.get(pair, 0) - lexical.get(pair, 0),
        }
        for pair in all_pairs
    ]
    comparison.sort(key=lambda row: (-max(row["lexical_count"], row["semantic_count"]), row["true_label"], row["predicted_label"]))
    symmetric: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {"lexical": 0, "semantic": 0})
    for (true, predicted), count in lexical.items():
        symmetric[tuple(sorted((true, predicted)))]["lexical"] += count
    for (true, predicted), count in semantic.items():
        symmetric[tuple(sorted((true, predicted)))]["semantic"] += count
    symmetric_rows = [
        {"intent_a": pair[0], "intent_b": pair[1], "lexical_count": values["lexical"], "semantic_count": values["semantic"], "delta_semantic_minus_lexical": values["semantic"] - values["lexical"]}
        for pair, values in symmetric.items()
    ]
    symmetric_rows.sort(key=lambda row: (-max(row["lexical_count"], row["semantic_count"]), row["intent_a"], row["intent_b"]))
    return {
        "top_20_directional": comparison[:20],
        "top_20_symmetric": symmetric_rows[:20],
        "improved_directional_pairs": sorted((row for row in comparison if row["delta_semantic_minus_lexical"] < 0), key=lambda row: (row["delta_semantic_minus_lexical"], row["true_label"], row["predicted_label"]))[:20],
        "worsened_directional_pairs": sorted((row for row in comparison if row["delta_semantic_minus_lexical"] > 0), key=lambda row: (-row["delta_semantic_minus_lexical"], row["true_label"], row["predicted_label"]))[:20],
        "shared_directional_pairs": sum(pair in lexical and pair in semantic for pair in all_pairs),
        "new_semantic_directional_pairs": sum(pair not in lexical and pair in semantic for pair in all_pairs),
    }


def _confidence_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def stats(values: list[float]) -> dict[str, float | int | None]:
        if not values:
            return {"count": 0, "mean": None, "median": None, "p25": None, "p75": None}
        array = np.asarray(values, dtype=np.float64)
        return {
            "count": len(values), "mean": float(array.mean()), "median": float(np.median(array)),
            "p25": float(np.quantile(array, 0.25)), "p75": float(np.quantile(array, 0.75)),
        }
    correct = [row for row in rows if row["correct"] == "true"]
    wrong = [row for row in rows if row["correct"] == "false"]
    return {
        "all_max_probability": stats([float(row["confidence"]) for row in rows]),
        "correct_max_probability": stats([float(row["confidence"]) for row in correct]),
        "incorrect_max_probability": stats([float(row["confidence"]) for row in wrong]),
        "all_top1_top2_margin": stats([float(row["margin"]) for row in rows]),
        "correct_top1_top2_margin": stats([float(row["margin"]) for row in correct]),
        "incorrect_top1_top2_margin": stats([float(row["margin"]) for row in wrong]),
    }


def _overlap_sensitivity(
    root: Path, config: dict[str, Any], data: FinalEvaluationData,
    lexical_rows: list[dict[str, Any]], semantic_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    audit = _read_json(resolve_repo_path(root, config["overlap_sensitivity"]["source"]))
    evidence = audit["audit"]["integrity"]["official_train_test_case_whitespace_normalized_overlap"]
    overlap_ids = {
        item["sample_id"] for example in evidence["examples"] for item in example["test"]
    }
    if len(overlap_ids) != 7:
        raise Week1FinalEvaluationError("overlap sensitivity must use exactly seven evidenced test IDs")
    test_ids = {item.sample_id for item in data.official_test}
    if not overlap_ids <= test_ids:
        raise Week1FinalEvaluationError("overlap evidence contains IDs outside official test")
    def evaluate(rows: list[dict[str, Any]]) -> dict[str, Any]:
        affected = [row for row in rows if row["sample_id"] in overlap_ids]
        excluded = [row for row in rows if row["sample_id"] not in overlap_ids]
        result = _evaluate(
            [row["true_label"] for row in excluded],
            [row["predicted_label"] for row in excluded], data.categories,
        )
        full = _evaluate(
            [row["true_label"] for row in rows],
            [row["predicted_label"] for row in rows], data.categories,
        )
        return {
            "affected_correct": sum(row["correct"] == "true" for row in affected),
            "affected_total": 7,
            "excluded_sample_count": len(excluded),
            "excluded_accuracy": result["accuracy"],
            "excluded_macro_f1": result["macro_f1"],
            "full_accuracy": full["accuracy"],
            "full_macro_f1": full["macro_f1"],
            "accuracy_change_excluded_minus_full": result["accuracy"] - full["accuracy"],
            "macro_f1_change_excluded_minus_full": result["macro_f1"] - full["macro_f1"],
        }
    return {
        "primary_benchmark": {"name": "Official Banking77 test", "sample_count": 3080},
        "sensitivity": {"name": "Official test excluding evidenced normalized-overlap samples", "sample_count": 3073},
        "affected_sample_ids": sorted(overlap_ids),
        "lexical": evaluate(lexical_rows),
        "semantic": evaluate(semantic_rows),
        "canonical_benchmark_changed": False,
    }


def _manual_review_candidates(
    data: FinalEvaluationData, paired_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    examples = {item.sample_id: item for item in data.official_test}
    selected: list[tuple[dict[str, Any], str]] = []
    used: set[str] = set()

    def add(rows: list[dict[str, Any]], reason: str, limit: int) -> None:
        count = 0
        for row in rows:
            if row["sample_id"] in used:
                continue
            selected.append((row, reason))
            used.add(row["sample_id"])
            count += 1
            if count == limit:
                break

    ordered = sorted(paired_rows, key=lambda row: row["sample_id"])
    add([row for row in ordered if row["disagreement_category"] == "lexical_wrong_semantic_correct"], "semantic_fix", 6)
    add([row for row in ordered if row["disagreement_category"] == "lexical_correct_semantic_wrong"], "lexical_only_correct", 6)
    add([row for row in ordered if row["disagreement_category"] == "both_wrong"], "both_wrong", 8)
    wrong = [row for row in paired_rows if row["disagreement_category"] != "both_correct"]
    add(sorted(wrong, key=lambda row: (-max(float(row["lexical_confidence"]), float(row["semantic_confidence"])), row["sample_id"])), "high_confidence_wrong", 4)
    add(sorted(wrong, key=lambda row: (min(float(row["lexical_margin"]), float(row["semantic_margin"])), row["sample_id"])), "low_margin_error", 3)
    short = sorted(wrong, key=lambda row: (len(examples[row["sample_id"]].text.split()), row["sample_id"]))
    add(short, "short_query_error", 3)
    add(ordered, "stable_fill", 30 - len(selected))
    result = []
    for row, reason in selected[:30]:
        example = examples[row["sample_id"]]
        result.append({
            "sample_id": row["sample_id"], "query_text": example.text,
            "true_label": row["true_label"], "lexical_prediction": row["lexical_prediction"],
            "semantic_prediction": row["semantic_prediction"],
            "lexical_confidence": row["lexical_confidence"], "semantic_confidence": row["semantic_confidence"],
            "lexical_margin": row["lexical_margin"], "semantic_margin": row["semantic_margin"],
            "disagreement_category": row["disagreement_category"], "selection_reason": reason,
            "error_category": "", "root_cause_hypothesis": "",
        })
    if len(result) != 30:
        raise Week1FinalEvaluationError("manual review candidate selection must produce 30 rows")
    return result


def _stable_output_names() -> tuple[str, ...]:
    return (
        "lexical_model", "semantic_model", "lexical_metrics", "lexical_per_class",
        "lexical_predictions", "lexical_confusions", "semantic_metrics",
        "semantic_per_class", "semantic_predictions", "semantic_confusions",
        "paired", "per_class_comparison",
        "confusion_analysis", "confidence", "overlap", "manual_review",
    )


def run_final_evaluation(
    root: Path, config_path: Path, run_label: str,
    encoder_loader: Callable[[Path, dict[str, Any]], LoadedEncoder] = _load_encoder,
) -> dict[str, Any]:
    if run_label not in RUN_LABELS:
        raise Week1FinalEvaluationError(f"run_label must be one of {sorted(RUN_LABELS)}")
    root = root.resolve()
    config = load_evaluation_config(config_path)
    manifest_path = resolve_repo_path(root, config["outputs"]["manifest"])
    config_hash = sha256_file(config_path)
    implementation = _implementation_hashes()
    previous: dict[str, Any] | None = None
    if run_label == "primary":
        verify_pretest_gate(root, config_path)
    else:
        if not manifest_path.exists():
            raise Week1FinalEvaluationError("reproducibility rerun requires a completed primary run")
        previous = _read_json(manifest_path)
        if previous.get("run_status") != "PRIMARY_COMPLETE":
            raise Week1FinalEvaluationError("reproducibility rerun is allowed exactly after primary")
        if previous.get("evaluation_config_sha256") != config_hash or previous.get("implementation") != implementation:
            raise Week1FinalEvaluationError("config/code changed after official-test access")
    total_start = time.perf_counter()
    data = load_final_evaluation_data(root, config)
    lexical_rows, lexical_runtime = _fit_lexical(root, config, data)
    semantic_rows, semantic_runtime, semantic_embedding = _fit_semantic(
        root, config_path, config, data, encoder_loader=encoder_loader
    )
    lexical_metrics, lexical_per_class, lexical_confusions = _metric_payload("lexical_word_unigram", data, lexical_rows)
    semantic_metrics, semantic_per_class, semantic_confusions = _metric_payload("semantic_all_minilm_l6_v2", data, semantic_rows)
    _write_model_evidence(root, config, "lexical", lexical_rows, lexical_metrics, lexical_per_class, lexical_confusions)
    _write_model_evidence(root, config, "semantic", semantic_rows, semantic_metrics, semantic_per_class, semantic_confusions)
    benchmark = _benchmark_rows(lexical_metrics, semantic_metrics, lexical_runtime, semantic_runtime)
    _write_csv(resolve_repo_path(root, config["outputs"]["benchmark_csv"]), list(benchmark[0]), benchmark)
    validation = {
        "lexical": _read_json(resolve_repo_path(root, config["candidates"]["lexical"]["manifest"]))["selected_validation_metrics"],
        "semantic": _read_json(resolve_repo_path(root, config["candidates"]["semantic"]["manifest"]))["validation_metrics"],
    }
    benchmark_json = {
        "task_id": TASK_ID, "test_evaluated": True, "rows": benchmark,
        "test_deltas_semantic_minus_lexical": {
            "accuracy": semantic_metrics["accuracy"] - lexical_metrics["accuracy"],
            "macro_f1": semantic_metrics["macro_f1"] - lexical_metrics["macro_f1"],
        },
        "generalization_change_test_minus_validation": {
            "lexical": {"accuracy": lexical_metrics["accuracy"] - validation["lexical"]["accuracy"], "macro_f1": lexical_metrics["macro_f1"] - validation["lexical"]["macro_f1"]},
            "semantic": {"accuracy": semantic_metrics["accuracy"] - validation["semantic"]["accuracy"], "macro_f1": semantic_metrics["macro_f1"] - validation["semantic"]["macro_f1"]},
        },
    }
    resolve_repo_path(root, config["outputs"]["benchmark_json"]).write_bytes(canonical_json_bytes(benchmark_json))
    paired_rows, paired_counts = build_paired_rows(lexical_rows, semantic_rows)
    _write_csv(resolve_repo_path(root, config["outputs"]["paired"]), list(paired_rows[0]), paired_rows)
    per_class_rows, per_class_summary = _per_class_comparison(lexical_per_class, semantic_per_class, lexical_rows, semantic_rows)
    _write_csv(resolve_repo_path(root, config["outputs"]["per_class_comparison"]), list(per_class_rows[0]), per_class_rows)
    confusion = _confusion_analysis(lexical_confusions, semantic_confusions)
    resolve_repo_path(root, config["outputs"]["confusion_analysis"]).write_bytes(canonical_json_bytes(confusion))
    confidence = {"diagnostic_only": True, "assumed_calibrated": False, "lexical": _confidence_summary(lexical_rows), "semantic": _confidence_summary(semantic_rows)}
    resolve_repo_path(root, config["outputs"]["confidence"]).write_bytes(canonical_json_bytes(confidence))
    overlap = _overlap_sensitivity(root, config, data, lexical_rows, semantic_rows)
    resolve_repo_path(root, config["outputs"]["overlap"]).write_bytes(canonical_json_bytes(overlap))
    review = _manual_review_candidates(data, paired_rows)
    _write_csv(resolve_repo_path(root, config["outputs"]["manual_review"]), list(review[0]), review)
    stable_hashes = {name: sha256_file(resolve_repo_path(root, config["outputs"][name])) for name in _stable_output_names()}
    if previous is not None and stable_hashes != previous["primary_stable_artifact_hashes"]:
        different = sorted(name for name in stable_hashes if stable_hashes[name] != previous["primary_stable_artifact_hashes"].get(name))
        raise Week1FinalEvaluationError(f"reproducibility mismatch in stable artifacts: {different}")
    runtime_path = resolve_repo_path(root, config["outputs"]["runtime"])
    runtime_payload = _read_json(runtime_path) if runtime_path.exists() and previous is not None else {"task_id": TASK_ID, "runs": {}}
    runtime_payload["runs"][run_label] = {
        "python": platform.python_version(), "platform": platform.platform(),
        "lexical": lexical_runtime, "semantic": semantic_runtime,
        "total_seconds": time.perf_counter() - total_start,
        "semantic_embedding": semantic_embedding,
    }
    runtime_path.write_bytes(canonical_json_bytes(runtime_payload))
    manifest = {
        "task_id": TASK_ID,
        "run_status": "REPRODUCIBILITY_COMPLETE" if previous is not None else "PRIMARY_COMPLETE",
        "test_encoded": True, "test_evaluated": True,
        "first_valid_test_access_run": "primary",
        "protocol_id": data.protocol_id,
        "source_revision": data.source_revision,
        "combined_membership_sha256": data.combined_membership_sha256,
        "split_manifest_sha256": data.split_manifest_sha256,
        "evaluation_config_sha256": config_hash,
        "implementation": implementation,
        "git": _git_state(root),
        "counts": EXPECTED_COUNTS,
        "frozen_candidates": config["candidates"],
        "completed_runs": ["primary", "reproducibility_rerun"] if previous is not None else ["primary"],
        "predictions_identical_across_runs": previous is not None,
        "metrics_identical_across_runs": previous is not None,
        "primary_stable_artifact_hashes": stable_hashes if previous is None else previous["primary_stable_artifact_hashes"],
        "reproducibility_stable_artifact_hashes": stable_hashes if previous is not None else None,
        "paired_outcome_counts": paired_counts,
        "per_class_summary": per_class_summary,
        "benchmark": benchmark_json,
        "manual_review_status": "PENDING_REVIEW",
        "model_selection_status": "PENDING_REVIEW",
        "week1_p0_gate": "PENDING_REVIEW",
    }
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    return {"manifest": manifest, "lexical_metrics": lexical_metrics, "semantic_metrics": semantic_metrics, "paired_counts": paired_counts}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def finalize_evaluation(root: Path, config_path: Path) -> dict[str, Any]:
    root = root.resolve()
    config = load_evaluation_config(config_path)
    manifest_path = resolve_repo_path(root, config["outputs"]["manifest"])
    manifest = _read_json(manifest_path)
    if manifest.get("run_status") != "REPRODUCIBILITY_COMPLETE":
        raise Week1FinalEvaluationError("finalization requires matching primary and reproducibility runs")
    if manifest.get("evaluation_config_sha256") != sha256_file(config_path) or manifest.get("implementation") != _implementation_hashes():
        raise Week1FinalEvaluationError("config/code changed after official-test access")
    review_path = resolve_repo_path(root, config["outputs"]["manual_review"])
    review = _read_csv(review_path)
    if not 20 <= len(review) <= 30:
        raise Week1FinalEvaluationError("manual error review must contain 20-30 rows")
    for row in review:
        if row.get("error_category") not in REVIEW_TAXONOMY or not row.get("root_cause_hypothesis", "").strip():
            raise Week1FinalEvaluationError("manual review requires taxonomy and root-cause hypothesis for every row")
    benchmark = _read_json(resolve_repo_path(root, config["outputs"]["benchmark_json"]))
    deltas = benchmark["test_deltas_semantic_minus_lexical"]
    per_class = _read_csv(resolve_repo_path(root, config["outputs"]["per_class_comparison"]))
    material_regressions = [row["label"] for row in per_class if float(row["f1_delta_semantic_minus_lexical"]) <= -0.20]
    if deltas["macro_f1"] >= 0.01 and deltas["accuracy"] >= 0 and not material_regressions:
        selected = "semantic_all_minilm_l6_v2"
        fallback = "lexical_word_unigram"
        rule = "semantic_clear_gain"
    elif abs(deltas["macro_f1"]) < 0.01 and abs(deltas["accuracy"]) < 0.01:
        selected = "lexical_word_unigram"
        fallback = "semantic_all_minilm_l6_v2"
        rule = "effective_tie"
    elif deltas["macro_f1"] <= -0.01 or deltas["accuracy"] <= -0.01 or material_regressions:
        selected = "lexical_word_unigram"
        fallback = "semantic_all_minilm_l6_v2"
        rule = "semantic_underperformance"
    else:
        selected = "lexical_word_unigram"
        fallback = "semantic_all_minilm_l6_v2"
        rule = "mixed_result"
    selected_config = config["candidates"]["semantic" if selected.startswith("semantic") else "lexical"]
    selection = {
        "task_id": TASK_ID, "selected_downstream_candidate": selected,
        "selected_config": selected_config["config"], "selected_config_sha256": selected_config["config_sha256"],
        "fallback_candidate": fallback, "decision_rule_branch": rule,
        "test_deltas_semantic_minus_lexical": deltas,
        "material_semantic_per_class_regressions_at_least_0_20": material_regressions,
        "known_limitations": [
            "seven normalized train/test boundary overlaps are retained in the canonical benchmark",
            "classifier probabilities are diagnostic and not calibrated",
            "CPU benchmark runtime is not production latency",
        ],
        "configuration_frozen_after_selection": True,
    }
    selection_path = resolve_repo_path(root, config["outputs"]["selection"])
    selection_path.write_bytes(canonical_json_bytes(selection))
    manifest["run_status"] = "FINALIZED"
    manifest["manual_review_status"] = "COMPLETE"
    manifest["manual_review_sha256"] = sha256_file(review_path)
    manifest["model_selection_status"] = "FROZEN"
    manifest["model_selection"] = selection
    manifest["model_selection_sha256"] = sha256_file(selection_path)
    manifest["week1_p0_gate"] = "PASS"
    manifest["gate_basis"] = config["p0_gate"]["criteria"]
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    return {"selection": selection, "week1_p0_gate": "PASS", "manual_review_rows": len(review)}


def verify_final_results(root: Path, config_path: Path) -> dict[str, Any]:
    root = root.resolve()
    config = load_evaluation_config(config_path)
    manifest = _read_json(resolve_repo_path(root, config["outputs"]["manifest"]))
    if manifest.get("run_status") != "FINALIZED" or manifest.get("test_encoded") is not True or manifest.get("test_evaluated") is not True:
        raise Week1FinalEvaluationError("final manifest is not finalized with test access recorded")
    if manifest.get("week1_p0_gate") != "PASS" or manifest.get("model_selection_status") != "FROZEN":
        raise Week1FinalEvaluationError("Week 1 gate/model selection is not frozen")
    for name, relative in config["outputs"].items():
        if name in {"lexical_model", "semantic_model", "semantic_cache"}:
            continue
        if not resolve_repo_path(root, relative).is_file():
            raise Week1FinalEvaluationError(f"required final evidence missing: {name}")
    lexical = _read_csv(resolve_repo_path(root, config["outputs"]["lexical_predictions"]))
    semantic = _read_csv(resolve_repo_path(root, config["outputs"]["semantic_predictions"]))
    paired, counts = build_paired_rows(lexical, semantic)
    if len(paired) != 3080 or sum(counts.values()) != 3080:
        raise Week1FinalEvaluationError("final paired evidence is not aligned")
    per_class = _read_csv(resolve_repo_path(root, config["outputs"]["per_class_comparison"]))
    if len(per_class) != 77 or sum(int(row["support"]) for row in per_class) != 3080:
        raise Week1FinalEvaluationError("final per-class evidence is incomplete")
    overlap = _read_json(resolve_repo_path(root, config["outputs"]["overlap"]))
    if len(overlap.get("affected_sample_ids", [])) != 7 or overlap.get("canonical_benchmark_changed") is not False:
        raise Week1FinalEvaluationError("overlap sensitivity contract mismatch")
    if manifest.get("primary_stable_artifact_hashes") != manifest.get("reproducibility_stable_artifact_hashes"):
        raise Week1FinalEvaluationError("primary/reproducibility stable hashes differ")
    return {
        "task_id": TASK_ID, "run_status": manifest["run_status"],
        "test_rows": 3080, "classes": 77, "paired_rows": 3080,
        "overlap_rows": 7, "selected_candidate": manifest["model_selection"]["selected_downstream_candidate"],
        "week1_p0_gate": manifest["week1_p0_gate"], "reproducibility_match": True,
    }
