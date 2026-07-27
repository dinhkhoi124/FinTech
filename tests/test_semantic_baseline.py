from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from payresolve_ai.baselines.lexical import LockedDevelopmentData
from payresolve_ai.baselines.semantic import (
    MODEL_ID,
    LoadedEncoder,
    SemanticBaselineError,
    _cache_paths,
    _load_embedding_cache,
    _write_embedding_cache,
    cache_key,
    load_semantic_config,
    run_validation,
    validate_embeddings,
)
from payresolve_ai.data.banking77 import Example, canonical_json_bytes, sha256_file


def example(sample_id: str, text: str, label: str) -> Example:
    return Example(sample_id, "train.csv", 1, text, label)


def normalized_embedding(text: str, dimension: int = 384) -> np.ndarray:
    value = np.zeros(dimension, dtype=np.float32)
    for index, byte in enumerate(text.encode("utf-8")):
        value[index % dimension] += float(byte + 1)
    return value / np.linalg.norm(value)


class SemanticBaselineTests(unittest.TestCase):
    def base_config(self) -> dict:
        return {
            "task_id": "W1-003",
            "description": "fixture",
            "data_config": "data.json",
            "requirements": "requirements.txt",
            "locked_combined_membership_sha256": "locked",
            "lexical_manifest": "lexical_manifest.json",
            "lexical_config": "lexical_config.json",
            "lexical_config_sha256": "placeholder",
            "seed": 20260723,
            "encoder": {
                "model_id": MODEL_ID,
                "revision": "1" * 40,
                "source_url": "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2",
                "license": "apache-2.0",
                "frozen": True,
                "expected_dimension": 384,
                "max_sequence_length": 256,
                "pooling": "mean",
                "normalize_embeddings": True,
                "batch_size": 4,
                "device": "cpu",
                "show_progress_bar": False,
                "trust_remote_code": False,
            },
            "classifier": {
                "family": "LogisticRegression",
                "C": 1.0,
                "max_iter": 1000,
                "random_state": 20260723,
                "solver": "lbfgs",
                "numerical_thread_limit": 1,
            },
            "cache": {
                "directory": "artifacts/cache",
                "huggingface_home": "artifacts/huggingface",
            },
            "analysis": {
                "lexical_per_class": "lexical_per_class.csv",
                "lexical_confusions": "lexical_confusions.csv",
                "material_f1_delta": 0.1,
                "focus_confusion_pairs": [["cash", "transfer"]],
            },
            "outputs": {
                "classifier": "artifacts/classifier.json.gz",
                "metrics": "results/metrics.json",
                "per_class": "results/per_class.csv",
                "predictions": "results/predictions.csv",
                "confusions": "results/confusions.csv",
                "embedding_manifest": "results/embedding_manifest.json",
                "provenance": "results/provenance.json",
                "comparison": "results/comparison.json",
                "runtime": "results/runtime.json",
                "manifest": "results/manifest.json",
            },
        }

    def locked_data(self) -> LockedDevelopmentData:
        train = [
            example("t1", "cash withdrawal atm", "cash"),
            example("t2", "get cash machine", "cash"),
            example("t3", "withdraw cash card", "cash"),
            example("t4", "atm gave cash", "cash"),
            example("t5", "bank transfer pending", "transfer"),
            example("t6", "send bank transfer", "transfer"),
            example("t7", "recipient transfer money", "transfer"),
            example("t8", "transfer to bank", "transfer"),
        ]
        validation = [
            example("v1", "cash from atm", "cash"),
            example("v2", "pending money transfer", "transfer"),
        ]
        return LockedDevelopmentData(
            categories=["cash", "transfer"],
            train=train,
            validation=validation,
            protocol_id="fixture",
            source_revision="0" * 40,
            combined_membership_sha256="locked",
            split_manifest_sha256="manifest",
        )

    def test_config_requires_exact_revision_frozen_encoder_and_one_model(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            for mutation, message in (
                (lambda value: value["encoder"].update(revision="main"), "exact lowercase"),
                (lambda value: value["encoder"].update(frozen=False), "must be frozen"),
                (lambda value: value["encoder"].update(expected_dimension=768), "must be 384"),
                (lambda value: value["encoder"].update(normalize_embeddings=False), "predeclared true"),
                (lambda value: value.update(encoder=[value["encoder"]]), "one object"),
                (lambda value: value.update(encoders=[value["encoder"]]), "single-model"),
            ):
                config = self.base_config()
                mutation(config)
                path.write_text(json.dumps(config), encoding="utf-8")
                with self.assertRaisesRegex(SemanticBaselineError, message):
                    load_semantic_config(path)

    def test_cache_key_changes_with_revision_normalization_and_protocol(self) -> None:
        data = self.locked_data()
        base = self.base_config()
        original = cache_key(base, data)
        changed_revision = self.base_config()
        changed_revision["encoder"]["revision"] = "2" * 40
        changed_normalization = self.base_config()
        changed_normalization["encoder"]["normalize_embeddings"] = False
        changed_data = LockedDevelopmentData(
            **{**data.__dict__, "protocol_id": "different"}
        )
        self.assertNotEqual(original, cache_key(changed_revision, data))
        self.assertNotEqual(original, cache_key(changed_normalization, data))
        self.assertNotEqual(original, cache_key(base, changed_data))

    def test_cache_round_trip_rejects_stale_ids_and_invalid_shape(self) -> None:
        ids = ["a", "b"]
        embeddings = np.stack([normalized_embedding("a"), normalized_embedding("b")])
        with tempfile.TemporaryDirectory() as temporary:
            embedding_path = Path(temporary) / "embeddings.npy"
            metadata_path = Path(temporary) / "metadata.json"
            _write_embedding_cache(
                embedding_path, metadata_path, embeddings, ids, "key", "train"
            )
            loaded, _ = _load_embedding_cache(
                embedding_path, metadata_path, ids, "key", "train", 384, True
            )
            np.testing.assert_array_equal(loaded, embeddings)
            with self.assertRaisesRegex(SemanticBaselineError, "misaligned"):
                _load_embedding_cache(
                    embedding_path,
                    metadata_path,
                    ["b", "a"],
                    "key",
                    "train",
                    384,
                    True,
                )
        with self.assertRaisesRegex(SemanticBaselineError, "invalid embedding shape"):
            validate_embeddings(np.zeros((2, 10), dtype=np.float32), ids, 384, False)

    def test_run_aligns_predictions_and_declares_frozen_test_isolation(self) -> None:
        data = self.locked_data()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self.base_config()
            lexical_config = root / config["lexical_config"]
            lexical_config.write_text("frozen lexical config\n", encoding="utf-8")
            config["lexical_config_sha256"] = sha256_file(lexical_config)
            (root / config["requirements"]).write_text(
                f"numpy=={np.__version__}\n", encoding="utf-8"
            )
            lexical_manifest = {
                "task_id": "W1-002",
                "test_evaluated": False,
                "config_sha256": config["lexical_config_sha256"],
                "combined_membership_sha256": "locked",
                "selected_candidate": {"id": "word_unigram"},
                "selected_validation_metrics": {"accuracy": 0.5, "macro_f1": 0.5},
            }
            (root / config["lexical_manifest"]).write_bytes(
                canonical_json_bytes(lexical_manifest)
            )
            (root / config["analysis"]["lexical_per_class"]).write_text(
                "label,precision,recall,f1,support\ncash,0.5,0.5,0.5,1\ntransfer,0.5,0.5,0.5,1\n",
                encoding="utf-8",
            )
            (root / config["analysis"]["lexical_confusions"]).write_text(
                "true_label,predicted_label,count\ncash,transfer,1\n", encoding="utf-8"
            )
            config_path = root / "semantic.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            def fake_loader(_root: Path, _config: dict) -> LoadedEncoder:
                def encode(texts: list[str]) -> np.ndarray:
                    return np.stack([normalized_embedding(text) for text in texts])

                return LoadedEncoder(encode, {"revision": "1" * 40}, 0.0, 0)

            with patch(
                "payresolve_ai.baselines.semantic.load_locked_train_validation",
                return_value=data,
            ):
                result = run_validation(
                    root, config_path, "primary", True, encoder_loader=fake_loader
                )

            self.assertFalse(result["metrics"]["test_evaluated"])
            self.assertFalse(result["manifest"]["test_encoded"])
            predictions = (root / config["outputs"]["predictions"]).read_text(
                encoding="utf-8"
            ).splitlines()
            self.assertEqual(len(predictions) - 1, len(data.validation))
            self.assertTrue((root / config["outputs"]["classifier"]).is_file())


if __name__ == "__main__":
    unittest.main()
