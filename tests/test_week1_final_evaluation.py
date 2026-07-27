from __future__ import annotations

import copy
import csv
import json
import tempfile
import unittest
from pathlib import Path

from payresolve_ai.evaluation.week1_final import (
    Week1FinalEvaluationError,
    _per_class_comparison,
    build_paired_rows,
    load_evaluation_config,
)
from payresolve_ai.data.banking77 import sha256_file


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "evaluation" / "banking77_w1_final.json"


def prediction(sample_id: str, true: str, predicted: str) -> dict[str, object]:
    return {
        "sample_id": sample_id,
        "true_label": true,
        "predicted_label": predicted,
        "correct": str(true == predicted).lower(),
        "confidence": 0.8,
        "margin": 0.4,
    }


class Week1FinalConfigTests(unittest.TestCase):
    def test_preregistered_repository_config_is_frozen_to_two_candidates(self) -> None:
        config = load_evaluation_config(CONFIG_PATH)
        self.assertEqual(set(config["candidates"]), {"lexical", "semantic"})
        self.assertEqual(config["final_fit_protocol"]["sample_count"], 10003)
        self.assertEqual(config["evaluation"]["sample_count"], 3080)
        self.assertFalse(config["downstream_decision_rule"]["third_model_allowed"])

    def test_config_rejects_revision_scope_and_candidate_overrides(self) -> None:
        original = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        mutations = (
            lambda value: value["candidates"]["semantic"].update(model_revision="main"),
            lambda value: value["final_fit_protocol"].update(scope="locked_train_only"),
            lambda value: value["candidates"].update(third_model={"status": "FROZEN_ON_VALIDATION"}),
            lambda value: value["downstream_decision_rule"].update(third_model_allowed=True),
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            for mutation in mutations:
                config = copy.deepcopy(original)
                mutation(config)
                path.write_text(json.dumps(config), encoding="utf-8")
                with self.assertRaises(Week1FinalEvaluationError):
                    load_evaluation_config(path)


class Week1FinalAlignmentTests(unittest.TestCase):
    def test_paired_rows_align_one_to_one_and_partition_all_outcomes(self) -> None:
        lexical = []
        semantic = []
        expected = {
            "both_correct": 770,
            "lexical_correct_semantic_wrong": 770,
            "lexical_wrong_semantic_correct": 770,
            "both_wrong": 770,
        }
        for index in range(3080):
            label = f"label_{index % 77}"
            group = index // 770
            lexical_prediction = label if group in (0, 1) else "wrong_lexical"
            semantic_prediction = label if group in (0, 2) else "wrong_semantic"
            lexical.append(prediction(f"id_{index:04d}", label, lexical_prediction))
            semantic.append(prediction(f"id_{index:04d}", label, semantic_prediction))
        paired, counts = build_paired_rows(lexical, semantic)
        self.assertEqual(len(paired), 3080)
        self.assertEqual(counts, expected)
        semantic[-1]["sample_id"] = "misaligned"
        with self.assertRaisesRegex(Week1FinalEvaluationError, "one-to-one"):
            build_paired_rows(lexical, semantic)

    def test_per_class_support_and_error_deltas_cover_all_3080_rows(self) -> None:
        lexical_rows = []
        semantic_rows = []
        lexical_per_class = []
        semantic_per_class = []
        for class_index in range(77):
            label = f"label_{class_index:02d}"
            lexical_per_class.append({"label": label, "precision": 0.8, "recall": 0.8, "f1": 0.8, "support": 40})
            semantic_per_class.append({"label": label, "precision": 0.9, "recall": 0.9, "f1": 0.9, "support": 40})
            for row_index in range(40):
                sample_id = f"{label}_{row_index:02d}"
                lexical_rows.append(prediction(sample_id, label, label if row_index < 32 else "wrong"))
                semantic_rows.append(prediction(sample_id, label, label if row_index < 36 else "wrong"))
        comparison, summary = _per_class_comparison(
            lexical_per_class, semantic_per_class, lexical_rows, semantic_rows
        )
        self.assertEqual(len(comparison), 77)
        self.assertEqual(sum(row["support"] for row in comparison), 3080)
        self.assertEqual(summary["improved"], 77)
        self.assertTrue(all(row["error_delta_semantic_minus_lexical"] == -4 for row in comparison))
        semantic_per_class[0]["support"] = 39
        with self.assertRaisesRegex(Week1FinalEvaluationError, "support must be 40"):
            _per_class_comparison(lexical_per_class, semantic_per_class, lexical_rows, semantic_rows)


class LockedWeek1FinalArtifactTests(unittest.TestCase):
    def test_final_manifest_records_frozen_access_and_reproduction(self) -> None:
        manifest = json.loads(
            (ROOT / "reports/week_01/results/week1_final_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["run_status"], "FINALIZED")
        self.assertTrue(manifest["test_encoded"])
        self.assertTrue(manifest["test_evaluated"])
        self.assertEqual(manifest["week1_p0_gate"], "PASS")
        self.assertEqual(
            manifest["evaluation_config_sha256"], sha256_file(CONFIG_PATH)
        )
        self.assertEqual(
            manifest["primary_stable_artifact_hashes"],
            manifest["reproducibility_stable_artifact_hashes"],
        )

    def test_test_predictions_and_per_class_support_are_complete(self) -> None:
        result_root = ROOT / "reports/week_01/results"
        prediction_sets = []
        for name in ("lexical", "semantic"):
            with (result_root / f"{name}_test_predictions.csv").open(
                "r", encoding="utf-8", newline=""
            ) as source:
                rows = list(csv.DictReader(source))
            self.assertEqual(len(rows), 3080)
            self.assertEqual(len({row["sample_id"] for row in rows}), 3080)
            self.assertTrue(all(row["predicted_label"] for row in rows))
            prediction_sets.append({row["sample_id"] for row in rows})
            with (result_root / f"{name}_test_per_class.csv").open(
                "r", encoding="utf-8", newline=""
            ) as source:
                per_class = list(csv.DictReader(source))
            self.assertEqual(len(per_class), 77)
            self.assertEqual(sum(int(row["support"]) for row in per_class), 3080)
            self.assertEqual({int(row["support"]) for row in per_class}, {40})
        self.assertEqual(prediction_sets[0], prediction_sets[1])

    def test_overlap_and_selected_model_follow_preregistered_contract(self) -> None:
        result_root = ROOT / "reports/week_01/results"
        overlap = json.loads(
            (result_root / "week1_overlap_sensitivity.json").read_text(encoding="utf-8")
        )
        selection = json.loads(
            (result_root / "week1_model_selection.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(overlap["affected_sample_ids"]), 7)
        self.assertFalse(overlap["canonical_benchmark_changed"])
        self.assertEqual(selection["decision_rule_branch"], "semantic_clear_gain")
        self.assertEqual(
            selection["selected_downstream_candidate"],
            "semantic_all_minilm_l6_v2",
        )
        self.assertTrue(selection["configuration_frozen_after_selection"])


if __name__ == "__main__":
    unittest.main()
