"""W1-003 frozen sentence-embedding validation baseline.

The implementation reuses the W1-002 locked development loader and metric
definitions. It never loads or encodes ``test.csv``; W1-004 owns the single
frozen-test comparison.
"""

from __future__ import annotations

import csv
import gzip
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
from sklearn.linear_model import LogisticRegression
from threadpoolctl import threadpool_limits

from payresolve_ai.baselines.lexical import (
    LockedDevelopmentData,
    _evaluate,
    _write_csv,
    load_locked_train_validation,
)
from payresolve_ai.data.banking77 import (
    canonical_json_bytes,
    resolve_repo_path,
    sha256_bytes,
    sha256_file,
)


MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_FAMILY = "Frozen Sentence Transformer embeddings + Logistic Regression"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
RUN_LABELS = frozenset({"primary", "reproducibility_rerun"})


class SemanticBaselineError(ValueError):
    """Raised when W1-003 violates its predeclared contract."""


@dataclass
class LoadedEncoder:
    encode_function: Callable[[list[str]], np.ndarray]
    provenance: dict[str, Any]
    load_seconds: float
    cache_footprint_bytes: int

    def encode(self, texts: list[str]) -> np.ndarray:
        return self.encode_function(texts)


def load_semantic_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    expected_top_level = {
        "task_id",
        "description",
        "data_config",
        "requirements",
        "locked_combined_membership_sha256",
        "lexical_manifest",
        "lexical_config",
        "lexical_config_sha256",
        "seed",
        "encoder",
        "classifier",
        "cache",
        "analysis",
        "outputs",
    }
    if set(config) != expected_top_level:
        raise SemanticBaselineError("top-level config differs from the single-model contract")
    if config.get("task_id") != "W1-003":
        raise SemanticBaselineError("task_id must be W1-003")
    encoder = config.get("encoder")
    if not isinstance(encoder, dict):
        raise SemanticBaselineError("encoder must be one object; model lists are forbidden")
    expected_encoder_keys = {
        "model_id",
        "revision",
        "source_url",
        "license",
        "frozen",
        "expected_dimension",
        "max_sequence_length",
        "pooling",
        "normalize_embeddings",
        "batch_size",
        "device",
        "show_progress_bar",
        "trust_remote_code",
    }
    if set(encoder) != expected_encoder_keys:
        raise SemanticBaselineError("encoder keys differ from the single reviewed contract")
    if encoder["model_id"] != MODEL_ID:
        raise SemanticBaselineError(f"W1-003 permits only {MODEL_ID}")
    if not FULL_SHA.fullmatch(str(encoder["revision"])):
        raise SemanticBaselineError("encoder revision must be an exact lowercase 40-char SHA")
    if encoder["frozen"] is not True:
        raise SemanticBaselineError("encoder must be frozen")
    if encoder["expected_dimension"] != 384:
        raise SemanticBaselineError("all-MiniLM-L6-v2 expected_dimension must be 384")
    if encoder["max_sequence_length"] != 256 or encoder["pooling"] != "mean":
        raise SemanticBaselineError("reviewed max length/pooling are 256 and mean")
    if encoder["normalize_embeddings"] is not True:
        raise SemanticBaselineError("normalization was predeclared true and cannot be selected")
    if not isinstance(encoder["batch_size"], int) or encoder["batch_size"] < 1:
        raise SemanticBaselineError("encoder batch_size must be a positive integer")
    if encoder["device"] != "cpu" or encoder["trust_remote_code"] is not False:
        raise SemanticBaselineError("reviewed execution requires CPU and trust_remote_code=false")

    classifier = config.get("classifier", {})
    expected_classifier = {
        "family": "LogisticRegression",
        "C": 1.0,
        "max_iter": 1000,
        "random_state": config.get("seed"),
        "solver": "lbfgs",
        "numerical_thread_limit": 1,
    }
    if classifier != expected_classifier or config.get("seed") != 20260723:
        raise SemanticBaselineError("classifier must match the predeclared W1-003 contract")

    output_keys = {
        "classifier",
        "metrics",
        "per_class",
        "predictions",
        "confusions",
        "embedding_manifest",
        "provenance",
        "comparison",
        "runtime",
        "manifest",
    }
    if set(config.get("outputs", {})) != output_keys:
        raise SemanticBaselineError(f"outputs must contain exactly {sorted(output_keys)}")
    local_paths = [
        config["outputs"]["classifier"],
        config.get("cache", {}).get("directory", ""),
        config.get("cache", {}).get("huggingface_home", ""),
    ]
    if any(not str(value).replace("\\", "/").startswith("artifacts/") for value in local_paths):
        raise SemanticBaselineError("weights, embeddings, and classifier must remain under artifacts/")
    if config.get("analysis", {}).get("material_f1_delta") != 0.1:
        raise SemanticBaselineError("material_f1_delta must remain predeclared at 0.1")
    return config


def _requirements_versions(path: Path) -> dict[str, str]:
    versions: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        name, separator, expected = value.partition("==")
        if not separator:
            raise SemanticBaselineError(f"unpinned semantic requirement: {value}")
        actual = importlib.metadata.version(name)
        if actual != expected:
            raise SemanticBaselineError(
                f"dependency mismatch for {name}: expected {expected}, got {actual}"
            )
        versions[name] = actual
    return dict(sorted(versions.items()))


def _verify_lexical_contract(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    path = resolve_repo_path(root, config["lexical_manifest"])
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("task_id") != "W1-002" or manifest.get("test_evaluated") is not False:
        raise SemanticBaselineError("W1-002 manifest is not frozen validation-only evidence")
    if manifest.get("config_sha256") != config["lexical_config_sha256"]:
        raise SemanticBaselineError("W1-002 config hash changed after lexical freeze")
    lexical_config_path = resolve_repo_path(root, config["lexical_config"])
    if sha256_file(lexical_config_path) != config["lexical_config_sha256"]:
        raise SemanticBaselineError("current W1-002 config bytes differ from the frozen hash")
    if manifest.get("combined_membership_sha256") != config["locked_combined_membership_sha256"]:
        raise SemanticBaselineError("W1-002 and W1-003 membership hashes differ")
    if manifest.get("selected_candidate", {}).get("id") != "word_unigram":
        raise SemanticBaselineError("unexpected W1-002 frozen candidate")
    return manifest


def cache_key(config: dict[str, Any], data: LockedDevelopmentData) -> str:
    encoder = config["encoder"]
    value = {
        "protocol_id": data.protocol_id,
        "combined_membership_sha256": data.combined_membership_sha256,
        "model_id": encoder["model_id"],
        "revision": encoder["revision"],
        "expected_dimension": encoder["expected_dimension"],
        "max_sequence_length": encoder["max_sequence_length"],
        "pooling": encoder["pooling"],
        "normalize_embeddings": encoder["normalize_embeddings"],
        "batch_size": encoder["batch_size"],
    }
    return sha256_bytes(canonical_json_bytes(value))


def _sample_ids_sha256(sample_ids: list[str]) -> str:
    return sha256_bytes(("\n".join(sample_ids) + "\n").encode("ascii"))


def _embedding_sha256(embeddings: np.ndarray) -> str:
    header = canonical_json_bytes(
        {"dtype": str(embeddings.dtype), "shape": list(embeddings.shape)}
    )
    return sha256_bytes(header + np.ascontiguousarray(embeddings).tobytes())


def validate_embeddings(
    embeddings: np.ndarray,
    sample_ids: list[str],
    expected_dimension: int,
    normalize_embeddings: bool,
) -> np.ndarray:
    value = np.asarray(embeddings)
    if value.ndim != 2 or value.shape != (len(sample_ids), expected_dimension):
        raise SemanticBaselineError(
            f"invalid embedding shape {value.shape}; expected {(len(sample_ids), expected_dimension)}"
        )
    if value.dtype != np.float32:
        value = value.astype(np.float32)
    if not np.isfinite(value).all():
        raise SemanticBaselineError("embeddings contain non-finite values")
    if normalize_embeddings:
        norms = np.linalg.norm(value, axis=1)
        if not np.allclose(norms, 1.0, rtol=1e-4, atol=1e-4):
            raise SemanticBaselineError("normalized embeddings do not have unit L2 norm")
    return np.ascontiguousarray(value)


def _cache_paths(root: Path, config: dict[str, Any], key: str, split: str) -> tuple[Path, Path]:
    directory = resolve_repo_path(root, config["cache"]["directory"]) / key
    return directory / f"{split}_embeddings.npy", directory / f"{split}_metadata.json"


def _write_embedding_cache(
    embedding_path: Path,
    metadata_path: Path,
    embeddings: np.ndarray,
    sample_ids: list[str],
    key: str,
    split: str,
) -> dict[str, Any]:
    embedding_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = embedding_path.with_suffix(".npy.tmp")
    with temporary.open("wb") as target:
        np.save(target, embeddings, allow_pickle=False)
    temporary.replace(embedding_path)
    metadata = {
        "cache_key": key,
        "split": split,
        "rows": len(sample_ids),
        "dimension": int(embeddings.shape[1]),
        "dtype": str(embeddings.dtype),
        "sample_ids": sample_ids,
        "sample_ids_sha256": _sample_ids_sha256(sample_ids),
        "embedding_sha256": _embedding_sha256(embeddings),
        "cache_file_sha256": sha256_file(embedding_path),
    }
    metadata_path.write_bytes(canonical_json_bytes(metadata))
    return metadata


def _load_embedding_cache(
    embedding_path: Path,
    metadata_path: Path,
    sample_ids: list[str],
    key: str,
    split: str,
    expected_dimension: int,
    normalize_embeddings: bool,
) -> tuple[np.ndarray, dict[str, Any]]:
    if embedding_path.is_file() != metadata_path.is_file():
        raise SemanticBaselineError(f"partial {split} embedding cache")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("cache_key") != key or metadata.get("split") != split:
        raise SemanticBaselineError(f"stale/mismatched {split} embedding cache metadata")
    if metadata.get("sample_ids") != sample_ids:
        raise SemanticBaselineError(f"{split} cache sample IDs are misaligned")
    if metadata.get("cache_file_sha256") != sha256_file(embedding_path):
        raise SemanticBaselineError(f"{split} embedding cache file checksum mismatch")
    embeddings = np.load(embedding_path, allow_pickle=False)
    embeddings = validate_embeddings(
        embeddings, sample_ids, expected_dimension, normalize_embeddings
    )
    if metadata.get("embedding_sha256") != _embedding_sha256(embeddings):
        raise SemanticBaselineError(f"{split} embedding payload checksum mismatch")
    return embeddings, metadata


def _encode_or_load(
    root: Path,
    config: dict[str, Any],
    encoder: LoadedEncoder,
    key: str,
    split: str,
    sample_ids: list[str],
    texts: list[str],
    refresh: bool,
) -> tuple[np.ndarray, dict[str, Any], bool, float]:
    embedding_path, metadata_path = _cache_paths(root, config, key, split)
    if embedding_path.is_file() != metadata_path.is_file() and not refresh:
        raise SemanticBaselineError(f"partial {split} embedding cache")
    if embedding_path.is_file() and metadata_path.is_file() and not refresh:
        start = time.perf_counter()
        embeddings, metadata = _load_embedding_cache(
            embedding_path,
            metadata_path,
            sample_ids,
            key,
            split,
            config["encoder"]["expected_dimension"],
            config["encoder"]["normalize_embeddings"],
        )
        return embeddings, metadata, True, time.perf_counter() - start
    start = time.perf_counter()
    embeddings = validate_embeddings(
        encoder.encode(texts),
        sample_ids,
        config["encoder"]["expected_dimension"],
        config["encoder"]["normalize_embeddings"],
    )
    elapsed = time.perf_counter() - start
    metadata = _write_embedding_cache(
        embedding_path, metadata_path, embeddings, sample_ids, key, split
    )
    return embeddings, metadata, False, elapsed


def _directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _git_state(root: Path) -> dict[str, Any]:
    revision_result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if revision_result.returncode != 0:
        return {"available": False}
    status = subprocess.run(
        ["git", "-C", str(root), "status", "--short"],
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "available": True,
        "head": revision_result.stdout.strip(),
        "working_tree_dirty": bool(status.stdout.strip()),
    }


def _load_encoder(root: Path, config: dict[str, Any]) -> LoadedEncoder:
    encoder_config = config["encoder"]
    cache_root = resolve_repo_path(root, config["cache"]["huggingface_home"])
    cache_root.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(cache_root)
    os.environ["HF_HUB_CACHE"] = str(cache_root / "hub")
    start = time.perf_counter()
    try:
        from huggingface_hub import snapshot_download
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise SemanticBaselineError(
            "semantic dependency missing; install requirements/week1-semantic.txt"
        ) from error
    try:
        model = SentenceTransformer(
            encoder_config["model_id"],
            revision=encoder_config["revision"],
            device=encoder_config["device"],
            cache_folder=str(cache_root),
            trust_remote_code=encoder_config["trust_remote_code"],
        )
    except Exception as error:
        raise SemanticBaselineError(
            f"failed to load exact encoder revision {encoder_config['revision']}: {error}"
        ) from error
    model.max_seq_length = encoder_config["max_sequence_length"]
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    if any(parameter.requires_grad for parameter in model.parameters()):
        raise SemanticBaselineError("encoder parameters are not frozen")
    dimension = model.get_sentence_embedding_dimension()
    if dimension != encoder_config["expected_dimension"]:
        raise SemanticBaselineError(
            f"encoder dimension mismatch: expected 384, got {dimension}"
        )
    try:
        pooling = model[1].get_pooling_mode_str()
    except (AttributeError, IndexError, TypeError) as error:
        raise SemanticBaselineError("unable to verify sentence-transformer pooling") from error
    if pooling != encoder_config["pooling"]:
        raise SemanticBaselineError(f"pooling mismatch: expected mean, got {pooling}")
    snapshot = Path(
        snapshot_download(
            repo_id=encoder_config["model_id"],
            revision=encoder_config["revision"],
            cache_dir=str(cache_root),
            local_files_only=True,
        )
    )
    if snapshot.name != encoder_config["revision"]:
        raise SemanticBaselineError(
            f"resolved model snapshot {snapshot.name} differs from pinned revision"
        )
    files = []
    for path in sorted(item for item in snapshot.rglob("*") if item.is_file()):
        files.append(
            {
                "path": path.relative_to(snapshot).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    tokenizer_limit = getattr(model.tokenizer, "model_max_length", None)
    provenance = {
        "model_id": encoder_config["model_id"],
        "revision": encoder_config["revision"],
        "source_url": encoder_config["source_url"],
        "license": encoder_config["license"],
        "embedding_dimension": dimension,
        "sentence_transformer_max_sequence_length": model.max_seq_length,
        "tokenizer_model_max_length": tokenizer_limit,
        "pooling": pooling,
        "normalize_embeddings": encoder_config["normalize_embeddings"],
        "encoder_frozen": True,
        "device": encoder_config["device"],
        "trust_remote_code": encoder_config["trust_remote_code"],
        "downloaded_snapshot_files": files,
        "snapshot_footprint_bytes": sum(item["bytes"] for item in files),
    }
    load_seconds = time.perf_counter() - start

    def encode(texts: list[str]) -> np.ndarray:
        return np.asarray(
            model.encode(
                texts,
                batch_size=encoder_config["batch_size"],
                show_progress_bar=encoder_config["show_progress_bar"],
                convert_to_numpy=True,
                normalize_embeddings=encoder_config["normalize_embeddings"],
                device=encoder_config["device"],
            ),
            dtype=np.float32,
        )

    return LoadedEncoder(
        encode_function=encode,
        provenance=provenance,
        load_seconds=load_seconds,
        cache_footprint_bytes=_directory_size(cache_root),
    )


def _build_classifier(config: dict[str, Any]) -> LogisticRegression:
    value = config["classifier"]
    return LogisticRegression(
        C=value["C"],
        max_iter=value["max_iter"],
        random_state=value["random_state"],
        solver=value["solver"],
    )


def _write_portable_classifier(
    path: Path, classifier: LogisticRegression, config: dict[str, Any]
) -> None:
    payload = {
        "format": "payresolve-semantic-classifier-parameters-v1",
        "encoder": {
            "model_id": config["encoder"]["model_id"],
            "revision": config["encoder"]["revision"],
            "normalize_embeddings": config["encoder"]["normalize_embeddings"],
        },
        "classifier": config["classifier"],
        "classes": classifier.classes_.tolist(),
        "coefficients": classifier.coef_.tolist(),
        "intercept": classifier.intercept_.tolist(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(canonical_json_bytes(payload), compresslevel=9, mtime=0))


def _read_csv_counts(path: Path) -> dict[tuple[str, str], int]:
    with path.open("r", encoding="utf-8", newline="") as source:
        return {
            (row["true_label"], row["predicted_label"]): int(row["count"])
            for row in csv.DictReader(source)
        }


def _build_comparison(
    root: Path,
    config: dict[str, Any],
    semantic_evaluation: dict[str, Any],
    semantic_confusions: list[dict[str, Any]],
    lexical_manifest: dict[str, Any],
) -> dict[str, Any]:
    lexical_per_class_path = resolve_repo_path(root, config["analysis"]["lexical_per_class"])
    with lexical_per_class_path.open("r", encoding="utf-8", newline="") as source:
        lexical_rows = {row["label"]: row for row in csv.DictReader(source)}
    deltas = []
    for row in semantic_evaluation["per_class"]:
        lexical_f1 = float(lexical_rows[row["label"]]["f1"])
        delta = row["f1"] - lexical_f1
        deltas.append(
            {
                "label": row["label"],
                "lexical_f1": lexical_f1,
                "semantic_f1": row["f1"],
                "delta_f1": delta,
                "support": row["support"],
            }
        )
    threshold = config["analysis"]["material_f1_delta"]
    lexical_metrics = lexical_manifest["selected_validation_metrics"]
    semantic_accuracy = semantic_evaluation["accuracy"]
    semantic_macro_f1 = semantic_evaluation["macro_f1"]
    lexical_confusions = _read_csv_counts(
        resolve_repo_path(root, config["analysis"]["lexical_confusions"])
    )
    semantic_confusion_counts = {
        (row["true_label"], row["predicted_label"]): int(row["count"])
        for row in semantic_confusions
    }
    focus = []
    for pair in config["analysis"]["focus_confusion_pairs"]:
        key = (pair[0], pair[1])
        lexical_count = lexical_confusions.get(key, 0)
        semantic_count = semantic_confusion_counts.get(key, 0)
        focus.append(
            {
                "true_label": pair[0],
                "predicted_label": pair[1],
                "lexical_count": lexical_count,
                "semantic_count": semantic_count,
                "delta_count": semantic_count - lexical_count,
            }
        )
    lexical_pairs = set(lexical_confusions)
    new_pairs = [
        row for row in semantic_confusions
        if (row["true_label"], row["predicted_label"]) not in lexical_pairs
    ]
    return {
        "scope": "locked_validation_only_descriptive_no_retuning",
        "test_evaluated": False,
        "aggregate": {
            "lexical_accuracy": lexical_metrics["accuracy"],
            "semantic_accuracy": semantic_accuracy,
            "delta_accuracy": semantic_accuracy - lexical_metrics["accuracy"],
            "lexical_macro_f1": lexical_metrics["macro_f1"],
            "semantic_macro_f1": semantic_macro_f1,
            "delta_macro_f1": semantic_macro_f1 - lexical_metrics["macro_f1"],
        },
        "class_counts": {
            "improved": sum(row["delta_f1"] > 0 for row in deltas),
            "regressed": sum(row["delta_f1"] < 0 for row in deltas),
            "unchanged": sum(row["delta_f1"] == 0 for row in deltas),
            "material_improvements": sum(row["delta_f1"] >= threshold for row in deltas),
            "material_regressions": sum(row["delta_f1"] <= -threshold for row in deltas),
            "material_threshold": threshold,
        },
        "largest_improvements": sorted(deltas, key=lambda row: (-row["delta_f1"], row["label"]))[:10],
        "largest_regressions": sorted(deltas, key=lambda row: (row["delta_f1"], row["label"]))[:10],
        "focus_confusion_pairs": focus,
        "semantic_top_confusions": semantic_confusions[:20],
        "semantic_new_confusion_pairs": new_pairs[:20],
        "per_class": sorted(deltas, key=lambda row: row["label"]),
    }


def _write_runtime(path: Path, label: str, runtime: dict[str, Any]) -> dict[str, Any]:
    existing: dict[str, Any] = {"task_id": "W1-003", "runs": {}}
    if path.is_file():
        existing = json.loads(path.read_text(encoding="utf-8"))
    existing.setdefault("runs", {})[label] = runtime
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(existing))
    return existing


def run_smoke(root: Path, config_path: Path) -> dict[str, Any]:
    root = root.resolve()
    config = load_semantic_config(config_path)
    _requirements_versions(resolve_repo_path(root, config["requirements"]))
    _verify_lexical_contract(root, config)
    data = load_locked_train_validation(root, resolve_repo_path(root, config["data_config"]))
    categories = data.categories[:4]
    # Select per-label examples rather than depending on global row order.
    train = [item for label in categories for item in [x for x in data.train if x.label == label][:4]]
    validation = [
        item for label in categories for item in [x for x in data.validation if x.label == label][:1]
    ]
    encoder = _load_encoder(root, config)
    train_embeddings = validate_embeddings(
        encoder.encode([item.text for item in train]),
        [item.sample_id for item in train],
        config["encoder"]["expected_dimension"],
        config["encoder"]["normalize_embeddings"],
    )
    validation_embeddings = validate_embeddings(
        encoder.encode([item.text for item in validation]),
        [item.sample_id for item in validation],
        config["encoder"]["expected_dimension"],
        config["encoder"]["normalize_embeddings"],
    )
    with threadpool_limits(limits=1):
        classifier = _build_classifier(config)
        classifier.fit(train_embeddings, [item.label for item in train])
        predicted = classifier.predict(validation_embeddings)
    return {
        "task_id": "W1-003",
        "scope": "technical_smoke_not_final_evidence",
        "train_rows": len(train),
        "validation_rows": len(validation),
        "classes": len(set(item.label for item in train)),
        "embedding_shape_train": list(train_embeddings.shape),
        "embedding_shape_validation": list(validation_embeddings.shape),
        "prediction_rows": len(predicted),
        "test_evaluated": False,
    }


def verify_contract(root: Path, config_path: Path) -> dict[str, Any]:
    """Verify W1-001/W1-002/W1-003 development contracts without loading a model."""
    root = root.resolve()
    config = load_semantic_config(config_path)
    dependencies = _requirements_versions(resolve_repo_path(root, config["requirements"]))
    lexical = _verify_lexical_contract(root, config)
    data = load_locked_train_validation(root, resolve_repo_path(root, config["data_config"]))
    if data.combined_membership_sha256 != config["locked_combined_membership_sha256"]:
        raise SemanticBaselineError("semantic config membership hash mismatch")
    return {
        "task_id": "W1-003",
        "protocol_id": data.protocol_id,
        "source_revision": data.source_revision,
        "combined_membership_sha256": data.combined_membership_sha256,
        "counts": {
            "train": len(data.train),
            "validation": len(data.validation),
            "classes": len(data.categories),
            "frozen_test_from_manifest": 3080,
        },
        "lexical_selected_candidate": lexical["selected_candidate"]["id"],
        "lexical_config_sha256": lexical["config_sha256"],
        "semantic_model_id": config["encoder"]["model_id"],
        "semantic_model_revision": config["encoder"]["revision"],
        "dependencies_verified": len(dependencies),
        "test_evaluated": False,
        "test_encoded": False,
    }


def run_validation(
    root: Path,
    config_path: Path,
    run_label: str,
    refresh_cache: bool,
    encoder_loader: Callable[[Path, dict[str, Any]], LoadedEncoder] = _load_encoder,
) -> dict[str, Any]:
    if run_label not in RUN_LABELS:
        raise SemanticBaselineError(f"run_label must be one of {sorted(RUN_LABELS)}")
    total_start = time.perf_counter()
    root = root.resolve()
    config = load_semantic_config(config_path)
    requirements_path = resolve_repo_path(root, config["requirements"])
    dependencies = _requirements_versions(requirements_path)
    lexical_manifest = _verify_lexical_contract(root, config)
    data = load_locked_train_validation(root, resolve_repo_path(root, config["data_config"]))
    if data.combined_membership_sha256 != config["locked_combined_membership_sha256"]:
        raise SemanticBaselineError("semantic config is not pinned to loaded membership")

    encoder = encoder_loader(root, config)
    key = cache_key(config, data)
    train_ids = [item.sample_id for item in data.train]
    validation_ids = [item.sample_id for item in data.validation]
    train_embeddings, train_metadata, train_hit, train_seconds = _encode_or_load(
        root,
        config,
        encoder,
        key,
        "train",
        train_ids,
        [item.text for item in data.train],
        refresh_cache,
    )
    validation_embeddings, validation_metadata, validation_hit, validation_seconds = _encode_or_load(
        root,
        config,
        encoder,
        key,
        "validation",
        validation_ids,
        [item.text for item in data.validation],
        refresh_cache,
    )

    classifier = _build_classifier(config)
    fit_start = time.perf_counter()
    with threadpool_limits(limits=config["classifier"]["numerical_thread_limit"]):
        classifier.fit(train_embeddings, [item.label for item in data.train])
    fit_seconds = time.perf_counter() - fit_start
    prediction_start = time.perf_counter()
    with threadpool_limits(limits=config["classifier"]["numerical_thread_limit"]):
        predicted = list(classifier.predict(validation_embeddings))
    prediction_seconds = time.perf_counter() - prediction_start
    labels = [item.label for item in data.validation]
    evaluation = _evaluate(labels, predicted, data.categories)

    output_paths = {
        name: resolve_repo_path(root, relative) for name, relative in config["outputs"].items()
    }
    prediction_rows = [
        {
            "sample_id": item.sample_id,
            "true_label": item.label,
            "predicted_label": prediction,
            "correct": str(item.label == prediction).lower(),
        }
        for item, prediction in zip(data.validation, predicted, strict=True)
    ]
    confusion_counts = Counter(
        (row["true_label"], row["predicted_label"])
        for row in prediction_rows
        if row["correct"] == "false"
    )
    confusion_rows = [
        {"true_label": true, "predicted_label": prediction, "count": count}
        for (true, prediction), count in sorted(
            confusion_counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1])
        )
    ]
    _write_csv(
        output_paths["predictions"],
        ["sample_id", "true_label", "predicted_label", "correct"],
        prediction_rows,
    )
    _write_csv(
        output_paths["per_class"],
        ["label", "precision", "recall", "f1", "support"],
        evaluation["per_class"],
    )
    _write_csv(
        output_paths["confusions"],
        ["true_label", "predicted_label", "count"],
        confusion_rows,
    )
    _write_portable_classifier(output_paths["classifier"], classifier, config)

    correct_count = sum(row["correct"] == "true" for row in prediction_rows)
    metrics = {
        "task_id": "W1-003",
        "evaluation_scope": "locked_validation_only",
        "test_evaluated": False,
        "model_family": MODEL_FAMILY,
        "accuracy": evaluation["accuracy"],
        "macro_f1": evaluation["macro_f1"],
        "correct_count": correct_count,
        "error_count": len(prediction_rows) - correct_count,
        "counts": {
            "train": len(data.train),
            "validation": len(data.validation),
            "classes": len(data.categories),
        },
    }
    output_paths["metrics"].parent.mkdir(parents=True, exist_ok=True)
    output_paths["metrics"].write_bytes(canonical_json_bytes(metrics))
    embedding_manifest = {
        "task_id": "W1-003",
        "cache_key": key,
        "cache_payload_tracked": False,
        "test_encoded": False,
        "splits": {
            "train": {key: value for key, value in train_metadata.items() if key != "sample_ids"},
            "validation": {
                key: value for key, value in validation_metadata.items() if key != "sample_ids"
            },
        },
    }
    output_paths["embedding_manifest"].write_bytes(canonical_json_bytes(embedding_manifest))
    output_paths["provenance"].write_bytes(canonical_json_bytes(encoder.provenance))
    comparison = _build_comparison(
        root, config, evaluation, confusion_rows, lexical_manifest
    )
    output_paths["comparison"].write_bytes(canonical_json_bytes(comparison))

    runtime = {
        "run_label": run_label,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "device": config["encoder"]["device"],
        "batch_size": config["encoder"]["batch_size"],
        "model_load_seconds": encoder.load_seconds,
        "train_encoding_or_cache_seconds": train_seconds,
        "validation_encoding_or_cache_seconds": validation_seconds,
        "classifier_fit_seconds": fit_seconds,
        "validation_prediction_seconds": prediction_seconds,
        "total_experiment_seconds": time.perf_counter() - total_start,
        "train_cache_hit": train_hit,
        "validation_cache_hit": validation_hit,
        "train_rows": len(data.train),
        "validation_rows": len(data.validation),
        "embedding_dimension": config["encoder"]["expected_dimension"],
        "huggingface_cache_footprint_bytes": encoder.cache_footprint_bytes,
        "embedding_cache_footprint_bytes": _directory_size(
            resolve_repo_path(root, config["cache"]["directory"])
        ),
        "dependencies": dependencies,
    }
    runtime_runs = _write_runtime(output_paths["runtime"], run_label, runtime)
    artifact_hashes = {
        name: sha256_file(output_paths[name])
        for name in (
            "classifier",
            "metrics",
            "per_class",
            "predictions",
            "confusions",
            "embedding_manifest",
            "provenance",
            "comparison",
            "runtime",
        )
    }
    manifest = {
        "task_id": "W1-003",
        "status": "FROZEN_ON_VALIDATION",
        "model_family": MODEL_FAMILY,
        "evaluation_scope": "locked_validation_only",
        "test_evaluated": False,
        "test_encoded": False,
        "protocol_id": data.protocol_id,
        "source_revision": data.source_revision,
        "combined_membership_sha256": data.combined_membership_sha256,
        "split_manifest_sha256": data.split_manifest_sha256,
        "semantic_config_sha256": sha256_file(config_path),
        "semantic_requirements_sha256": sha256_file(requirements_path),
        "implementation": {
            "semantic_module_sha256": sha256_file(Path(__file__)),
            "semantic_cli_sha256": sha256_file(Path(__file__).with_name("semantic_cli.py")),
            "git": _git_state(root),
        },
        "lexical_manifest_sha256": sha256_file(
            resolve_repo_path(root, config["lexical_manifest"])
        ),
        "encoder": config["encoder"],
        "classifier": config["classifier"],
        "validation_metrics": {
            "accuracy": evaluation["accuracy"],
            "macro_f1": evaluation["macro_f1"],
        },
        "counts": metrics["counts"],
        "cache_key": key,
        "completed_runtime_labels": sorted(runtime_runs["runs"]),
        "artifacts": {
            name: {"path": config["outputs"][name], "sha256": digest}
            for name, digest in artifact_hashes.items()
        },
    }
    output_paths["manifest"].write_bytes(canonical_json_bytes(manifest))
    return {
        "metrics": metrics,
        "comparison": comparison["aggregate"],
        "runtime": runtime,
        "manifest": manifest,
    }


def verify_cache(root: Path, config_path: Path) -> dict[str, Any]:
    root = root.resolve()
    config = load_semantic_config(config_path)
    data = load_locked_train_validation(root, resolve_repo_path(root, config["data_config"]))
    key = cache_key(config, data)
    result: dict[str, Any] = {"cache_key": key, "test_encoded": False, "splits": {}}
    for split, examples in (("train", data.train), ("validation", data.validation)):
        embedding_path, metadata_path = _cache_paths(root, config, key, split)
        embeddings, metadata = _load_embedding_cache(
            embedding_path,
            metadata_path,
            [item.sample_id for item in examples],
            key,
            split,
            config["encoder"]["expected_dimension"],
            config["encoder"]["normalize_embeddings"],
        )
        result["splits"][split] = {
            "shape": list(embeddings.shape),
            "embedding_sha256": metadata["embedding_sha256"],
            "sample_ids_sha256": metadata["sample_ids_sha256"],
        }
    return result


def inspect_validation_errors(root: Path, config_path: Path, limit: int) -> list[dict[str, str]]:
    if limit < 1:
        return []
    root = root.resolve()
    config = load_semantic_config(config_path)
    data = load_locked_train_validation(root, resolve_repo_path(root, config["data_config"]))
    predictions_path = resolve_repo_path(root, config["outputs"]["predictions"])
    with predictions_path.open("r", encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    if [row["sample_id"] for row in rows] != [item.sample_id for item in data.validation]:
        raise SemanticBaselineError("semantic predictions are misaligned to locked validation")
    by_id = {item.sample_id: item for item in data.validation}
    counts = Counter(
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
            -counts[(row["true_label"], row["predicted_label"])],
            row["true_label"],
            row["predicted_label"],
            row["sample_id"],
        ),
    )[:limit]
