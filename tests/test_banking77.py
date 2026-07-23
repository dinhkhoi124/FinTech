from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from payresolve_ai.data.banking77 import (  # noqa: E402
    Banking77Error,
    audit_examples,
    build_locked_split,
    load_categories,
    load_config,
    load_examples,
)


class Banking77FixtureMixin:
    def make_fixture(self, root: Path, *, invalid_label: bool = False) -> tuple[list[str], list, list]:
        categories = ["alpha", "beta", "gamma"]
        (root / "categories.json").write_text(json.dumps(categories), encoding="utf-8")
        train_rows = []
        for label in categories:
            for index in range(5):
                train_rows.append({"text": f"{label} training query {index}", "category": label})
        if invalid_label:
            train_rows[0]["category"] = "unknown"
        test_rows = [
            {"text": f"{label} official test query", "category": label} for label in categories
        ]
        for filename, rows in (("train.csv", train_rows), ("test.csv", test_rows)):
            with (root / filename).open("w", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=["text", "category"])
                writer.writeheader()
                writer.writerows(rows)
        return (
            load_categories(root / "categories.json"),
            load_examples(root / "train.csv"),
            load_examples(root / "test.csv"),
        )


class Banking77SplitTests(Banking77FixtureMixin, unittest.TestCase):
    def test_split_is_deterministic_stratified_and_disjoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            categories, train, test = self.make_fixture(Path(temporary))
            split_config = {
                "strategy": "official_test_plus_hash_stratified_validation",
                "seed": 20260723,
                "validation_fraction": {"numerator": 1, "denominator": 5},
            }
            first_membership, first_metadata = build_locked_split(
                categories, train, test, split_config
            )
            second_membership, second_metadata = build_locked_split(
                categories, list(reversed(train)), list(reversed(test)), split_config
            )

            self.assertEqual(first_membership, second_membership)
            self.assertEqual(first_metadata, second_metadata)
            self.assertEqual({"train": 12, "validation": 3, "test": 3}, first_metadata["counts"])
            self.assertTrue(first_metadata["official_test_frozen"])
            self.assertEqual(
                {example.sample_id for example in test}, set(first_membership["test"])
            )
            self.assertFalse(set(first_membership["train"]) & set(first_membership["validation"]))
            self.assertFalse(set(first_membership["train"]) & set(first_membership["test"]))
            self.assertTrue(
                all(count == 1 for count in first_metadata["class_distribution"]["validation"].values())
            )

    def test_invalid_label_prevents_locking(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            categories, train, test = self.make_fixture(Path(temporary), invalid_label=True)
            with self.assertRaisesRegex(Banking77Error, "Critical integrity failure"):
                audit_examples(
                    categories,
                    train,
                    test,
                    {"short_token_thresholds": [1, 2, 3], "shortest_examples_limit": 5},
                )

    def test_label_mapping_and_duplicate_audit_are_consistent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            categories, train, test = self.make_fixture(Path(temporary))
            audit = audit_examples(
                categories,
                train,
                test,
                {"short_token_thresholds": [1, 2, 3], "shortest_examples_limit": 5},
            )
            self.assertEqual({"alpha": 0, "beta": 1, "gamma": 2}, audit["labels"]["mapping"])
            self.assertEqual(0, audit["labels"]["invalid_label_rows"])
            self.assertEqual(0, audit["integrity"]["conflicting_label_queries"]["groups"])

    def test_normalized_cross_split_overlap_is_evidenced_without_removal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            categories, _, _ = self.make_fixture(root)
            train_path = root / "train.csv"
            with train_path.open("r", encoding="utf-8", newline="") as source:
                rows = list(csv.DictReader(source))
            rows[0]["text"] = "Shared   Query"
            with train_path.open("w", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=["text", "category"])
                writer.writeheader()
                writer.writerows(rows)
            test_path = root / "test.csv"
            with test_path.open("r", encoding="utf-8", newline="") as source:
                test_rows = list(csv.DictReader(source))
            test_rows[0]["text"] = "shared query"
            with test_path.open("w", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=["text", "category"])
                writer.writeheader()
                writer.writerows(test_rows)
            train = load_examples(train_path)
            test = load_examples(test_path)

            audit = audit_examples(
                categories,
                train,
                test,
                {"short_token_thresholds": [1, 2, 3], "shortest_examples_limit": 5},
            )
            overlap = audit["integrity"][
                "official_train_test_case_whitespace_normalized_overlap"
            ]
            self.assertEqual(1, overlap["distinct_queries"])
            self.assertEqual(1, overlap["label_consistent_queries"])
            self.assertEqual(0, overlap["label_conflicting_queries"])
            self.assertEqual("Shared   Query", overlap["examples"][0]["train"][0]["text"])


class Banking77ConfigTests(unittest.TestCase):
    def test_mutable_branch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "source": {
                            "revision": "master",
                            "files": {
                                "categories.json": {},
                                "train.csv": {},
                                "test.csv": {},
                            },
                        },
                        "split": {
                            "validation_fraction": {"numerator": 1, "denominator": 10}
                        },
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(Banking77Error, "exact 40-character"):
                load_config(path)


class LockedRepositoryArtifactTests(unittest.TestCase):
    def test_locked_manifest_declares_77_labels_and_frozen_test(self) -> None:
        manifest_path = REPO_ROOT / "data" / "banking77_split_manifest.json"
        if not manifest_path.is_file():
            self.skipTest("W1-001 locked manifest has not been generated yet")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        distributions = manifest["split"]["class_distribution"]
        self.assertEqual(77, len(distributions["train"]))
        self.assertEqual(set(distributions["train"]), set(distributions["validation"]))
        self.assertEqual(set(distributions["train"]), set(distributions["test"]))
        self.assertTrue(manifest["split"]["official_test_frozen"])
        self.assertEqual(
            len(manifest["membership"]["test"]), manifest["split"]["counts"]["test"]
        )


if __name__ == "__main__":
    unittest.main()
