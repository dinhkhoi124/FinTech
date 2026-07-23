from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from payresolve_ai.baselines.lexical import (
    ALLOWED_ESTIMATOR,
    LexicalBaselineError,
    LockedDevelopmentData,
    _partition_official_train,
    load_lexical_config,
    run_validation,
)
from payresolve_ai.data.banking77 import Example


def example(sample_id: str, text: str, label: str) -> Example:
    return Example(sample_id, "train.csv", 1, text, label)


class LexicalBaselineTests(unittest.TestCase):
    def base_config(self) -> dict:
        candidate = {
            "id": "word_unigram",
            "tfidf": {
                "lowercase": True,
                "min_df": 1,
                "ngram_range": [1, 1],
                "sublinear_tf": True,
            },
            "logistic_regression": {
                "C": 1.0,
                "max_iter": 200,
                "random_state": 7,
                "solver": "lbfgs",
            },
        }
        return {
            "task_id": "W1-002",
            "data_config": "data.json",
            "locked_combined_membership_sha256": "locked",
            "estimator": ALLOWED_ESTIMATOR,
            "seed": 7,
            "selection": {"metric": "macro_f1"},
            "candidates": [candidate],
            "outputs": {
                "model": "artifacts/model.joblib",
                "metrics": "results/metrics.json",
                "per_class": "results/per_class.csv",
                "predictions": "results/predictions.csv",
                "confusions": "results/confusions.csv",
                "manifest": "results/manifest.json",
            },
        }

    def test_partition_rejects_test_leakage_and_preserves_alignment(self) -> None:
        examples = [example("a", "alpha", "a"), example("b", "beta", "b")]
        train, validation = _partition_official_train(
            examples, {"train": ["a"], "validation": ["b"], "test": ["frozen"]}
        )
        self.assertEqual([item.sample_id for item in train], ["a"])
        self.assertEqual([item.sample_id for item in validation], ["b"])
        with self.assertRaisesRegex(LexicalBaselineError, "not disjoint"):
            _partition_official_train(
                examples, {"train": ["a"], "validation": ["b"], "test": ["b"]}
            )

    def test_config_rejects_a_third_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            config = self.base_config()
            config["candidates"] = [
                {**config["candidates"][0], "id": f"candidate-{index}"}
                for index in range(3)
            ]
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(LexicalBaselineError, "one or two"):
                load_lexical_config(path)

    def test_validation_run_is_aligned_and_deterministic(self) -> None:
        train = [
            example("t1", "cash withdrawal card", "cash"),
            example("t2", "withdraw money atm", "cash"),
            example("t3", "bank transfer pending", "transfer"),
            example("t4", "send transfer bank", "transfer"),
        ]
        validation = [
            example("v1", "cash from atm", "cash"),
            example("v2", "pending bank transfer", "transfer"),
        ]
        locked = LockedDevelopmentData(
            categories=["cash", "transfer"],
            train=train,
            validation=validation,
            protocol_id="fixture",
            source_revision="0" * 40,
            combined_membership_sha256="locked",
            split_manifest_sha256="manifest",
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = root / "lexical.json"
            config = self.base_config()
            config_path.write_text(json.dumps(config), encoding="utf-8")
            with patch(
                "payresolve_ai.baselines.lexical.load_locked_train_validation",
                return_value=locked,
            ):
                first = run_validation(root, config_path)
                first_predictions = (root / "results/predictions.csv").read_bytes()
                second = run_validation(root, config_path)
                second_predictions = (root / "results/predictions.csv").read_bytes()

            self.assertEqual(first["metrics"], second["metrics"])
            self.assertEqual(first_predictions, second_predictions)
            self.assertFalse(first["metrics"]["test_evaluated"])
            with (root / "results/predictions.csv").open(encoding="utf-8", newline="") as source:
                rows = list(csv.DictReader(source))
            self.assertEqual([row["sample_id"] for row in rows], ["v1", "v2"])
            self.assertEqual(len(rows), len(validation))


if __name__ == "__main__":
    unittest.main()
