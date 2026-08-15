from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.evaluation import week3_critical_v2_execution as cli
from scripts.evaluation import build_critical_v2_ea1_revision15_f4_review_bundle as f4_builder
from payresolve_ai.evaluation import critical_v2_execution as execution


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/evaluation/critical_eval_v2_execution.json"


class Revision15F4ComparatorCorrectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = execution.load_execution_config(CONFIG_PATH)
        self.outputs = self.config["evaluation_outputs"]

    @staticmethod
    def _rows(path: Path) -> list[dict]:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

    def _variant_rows(self, variant: str) -> tuple[list[dict], list[dict]]:
        return (
            self._rows(ROOT / self.outputs["primary"][f"{variant}_raw"]),
            self._rows(ROOT / self.outputs["reproducibility_rerun"][f"{variant}_raw"]),
        )

    def test_exact_frozen_evidence_is_provenance_valid_and_behavioral_180_of_180(self) -> None:
        total = 0
        for variant in execution.VARIANT_IDS:
            primary, reproduction = self._variant_rows(variant)
            result = execution.compare_reproducibility_variant(
                ROOT, CONFIG_PATH, self.config, variant, primary, reproduction
            )
            self.assertFalse(result["identical_excluding_run_identity_and_latency"])
            self.assertEqual(result["legacy_equal_rows"], 0)
            self.assertTrue(result["primary_provenance_valid"])
            self.assertTrue(result["reproduction_provenance_valid"])
            self.assertTrue(result["behavioral_identical"])
            self.assertEqual(result["behavioral_equal_rows"], 60)
            self.assertIn("determinism.seed", result["separately_validated_provenance_fields"]["primary"])
            self.assertNotIn("determinism.seed", result["excluded_nonbehavioral_fields"])
            total += result["behavioral_equal_rows"]
        self.assertEqual(total, 180)

    def test_twelve_behavioral_mutations_fail_closed(self) -> None:
        primary, reproduction = self._variant_rows("V0")
        mutations = {
            "classifier_prediction": lambda row: row["classifier_prediction"].update(predicted_intent="mutated"),
            "retrieval_strategy": lambda row: row.__setitem__("retrieval_strategy", "MUTATED"),
            "retrieved_evidence": lambda row: row["retrieved_evidence"][0].__setitem__("score", -1.0),
            "gate_inputs": lambda row: row["gate_inputs"].__setitem__("min_top1_score", -1.0),
            "gate_decision": lambda row: row["gate_decision"].__setitem__("decision", "MUTATED"),
            "response": lambda row: row.__setitem__("response", "mutated response"),
            "claim_records": lambda row: row.__setitem__("claim_records", [{"mutation": True}]),
            "citation_records": lambda row: row.__setitem__("citation_records", [{"mutation": True}]),
            "eligible_evidence_records": lambda row: row.__setitem__("eligible_evidence_records", [{"mutation": True}]),
            "model_input_sha256": lambda row: row.__setitem__("model_input_sha256", "0" * 64),
            "determinism.seed": lambda row: row["determinism"].__setitem__("seed", -1),
            "system_error": lambda row: row.__setitem__("system_error", "mutated"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                changed = copy.deepcopy(reproduction)
                mutate(changed[0])
                if name == "determinism.seed":
                    with self.assertRaises(execution.CriticalV2ExecutionError):
                        execution.compare_reproducibility_variant(
                            ROOT, CONFIG_PATH, self.config, "V0", primary, changed
                        )
                else:
                    result = execution.compare_reproducibility_variant(
                        ROOT, CONFIG_PATH, self.config, "V0", primary, changed
                    )
                    self.assertFalse(result["behavioral_identical"])
                    self.assertEqual(result["behavioral_equal_rows"], 59)

    def test_eight_provenance_mutations_fail_closed(self) -> None:
        primary, reproduction = self._variant_rows("V0")
        cases = {
            "primary_runtime_sha": (primary, "primary", lambda row: row.__setitem__("execution_environment_sha256", "0" * 64)),
            "primary_contract": (primary, "primary", lambda row: row["determinism"].__setitem__("execution_contract_sha256", "0" * 64)),
            "repro_runtime_sha": (reproduction, "reproducibility_rerun", lambda row: row.__setitem__("execution_environment_sha256", "0" * 64)),
            "repro_contract": (reproduction, "reproducibility_rerun", lambda row: row["determinism"].__setitem__("execution_contract_sha256", "0" * 64)),
            "repro_reference": (reproduction, "reproducibility_rerun", lambda row: row.__setitem__("execution_environment_reference", "unexpected.json")),
            "execution_id": (reproduction, "reproducibility_rerun", lambda row: row.__setitem__("execution_id", "malformed")),
            "run_label": (reproduction, "reproducibility_rerun", lambda row: row.__setitem__("run_label", "wrong")),
            "variant_id": (reproduction, "reproducibility_rerun", lambda row: row.__setitem__("variant_id", "V9")),
        }
        for name, (source, run_label, mutate) in cases.items():
            with self.subTest(name=name):
                row = copy.deepcopy(source[0])
                mutate(row)
                with self.assertRaises(execution.CriticalV2ExecutionError):
                    execution.validate_reproducibility_provenance(
                        ROOT, CONFIG_PATH, self.config, row,
                        run_label=run_label, variant_id="V0",
                    )

    def _copy(self, root: Path, relative: str) -> None:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)

    def _posteval_workspace(self) -> tuple[tempfile.TemporaryDirectory[str], Path, dict[str, str]]:
        temporary = tempfile.TemporaryDirectory(prefix="ea1_r15_f4_")
        root = Path(temporary.name)
        paths = {
            "configs/evaluation/critical_eval_v2_execution.json",
            self.config["state_machine"]["spec"],
            self.config["evaluation_outputs"]["execution_state"],
            self.config["continuation"]["receipt"],
            self.config["continuation"]["historical_runtime_environment"]["path"],
            self.config["runtime_environment"]["manifest"],
            *self.config["evaluation_outputs"]["primary"].values(),
            *self.config["evaluation_outputs"]["reproducibility_rerun"].values(),
            *execution.evaluation_direct_input_references(self.config, "primary"),
            *execution.evaluation_direct_input_references(self.config, "reproducibility_rerun"),
        }
        for relative in paths:
            self._copy(root, relative)
        authorization_path = root / self.config["authorization"]["committed_record"]
        authorization_path.parent.mkdir(parents=True, exist_ok=True)
        authorization_path.write_text(
            json.dumps(execution.POSTEVAL_CONTINUATION_AUTHORIZATION_FIELDS, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        future = {
            "authorization_commit": "a" * 40,
            "readiness_implementation_commit": "b" * 40,
        }
        return temporary, root, future

    def test_posteval_migration_preserves_state_history_then_verify_reaches_verified(self) -> None:
        temporary, root, future = self._posteval_workspace()
        try:
            state_path = root / self.outputs["execution_state"]
            before = json.loads(state_path.read_text(encoding="utf-8"))
            with patch.object(execution, "verify_execution_authorization", return_value=future), patch.object(
                execution, "freeze_or_verify_runtime_environment", side_effect=AssertionError("runtime must not execute")
            ):
                receipt = execution.migrate_r15_f4_posteval_continuation(root, root / "configs/evaluation/critical_eval_v2_execution.json")
                migrated = json.loads(state_path.read_text(encoding="utf-8"))
                self.assertEqual(receipt["status"], "PASS")
                self.assertEqual(migrated["state"], "REPRO_EVALUATED")
                self.assertEqual(len(migrated["history"]), 10)
                self.assertEqual(migrated["history"], before["history"])
                comparison = execution.verify_reproducibility(root, root / "configs/evaluation/critical_eval_v2_execution.json")
            verified = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(comparison["status"], "PASS")
            self.assertTrue(comparison["primary_reproduction_identical"])
            self.assertEqual(comparison["behavioral_equal_rows"], 180)
            self.assertEqual(verified["state"], "REPRO_VERIFIED")
            self.assertEqual(len(verified["history"]), 11)
            expected_inputs = {
                self.outputs[label]["raw_manifest"]
                for label in execution.RUN_LABELS
            } | {
                "configs/evaluation/critical_eval_v2_execution.json",
                self.config["continuation"]["historical_runtime_environment"]["path"],
                self.config["runtime_environment"]["manifest"],
            }
            self.assertEqual(
                set(verified["history"][10]["direct_input_sha256"]),
                expected_inputs,
            )
            for relative in sorted(expected_inputs):
                with self.subTest(material_input=relative):
                    mutated = copy.deepcopy(verified)
                    mutated["history"][10]["direct_input_sha256"][relative] = "0" * 64
                    with self.assertRaisesRegex(
                        execution.CriticalV2ExecutionError,
                        "state-bound artifact hash mismatch",
                    ):
                        execution.validate_state_history(
                            root, self.config, mutated, future
                        )
            self.assertEqual(receipt["model_calls"], 0)
            self.assertEqual(receipt["evaluator_calls"], 0)
        finally:
            temporary.cleanup()

    def test_posteval_migration_failure_keeps_prepared_receipt_and_legacy_state(self) -> None:
        temporary, root, future = self._posteval_workspace()
        try:
            state_path = root / self.outputs["execution_state"]
            before = execution.sha256_file(state_path)
            with patch.object(execution, "verify_execution_authorization", return_value=future), patch.object(
                execution, "_atomic_write_json", side_effect=OSError("injected failure")
            ):
                with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "PREPARED receipt"):
                    execution.migrate_r15_f4_posteval_continuation(root, root / "configs/evaluation/critical_eval_v2_execution.json")
            self.assertEqual(execution.sha256_file(state_path), before)
            receipt = json.loads((root / execution.POSTEVAL_CONTINUATION_RECEIPT).read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "PREPARED")
        finally:
            temporary.cleanup()

    def test_cli_and_revision_contract_remain_explicit(self) -> None:
        parsed = cli.parser().parse_args(["migrate-r15-f4-posteval-continuation"])
        self.assertEqual(parsed.command, "migrate-r15-f4-posteval-continuation")
        self.assertEqual(self.config["readiness_revision"], 15)
        self.assertEqual(
            execution.sha256_file(CONFIG_PATH),
            "36f372c6dd08e948bceea52d3222e8510e32382bec8748e264f8ac4eb977d943",
        )

    def test_stale_a15_rejects_f4_bytes_and_synthetic_a16_authorizes_exact_scope(self) -> None:
        with self.assertRaisesRegex(
            execution.CriticalV2ExecutionError,
            "authorization execution source/config/test hash mismatch",
        ):
            execution.verify_execution_authorization(ROOT, CONFIG_PATH)
        (ROOT / "review").mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="ea1_r15_f4_a16_test_", dir=ROOT / "review"
        ) as directory:
            proof = f4_builder.create_synthetic_proof(ROOT, Path(directory))
            repo = proof["repo"]
            authorization = json.loads(
                (repo / self.config["authorization"]["committed_record"])
                .read_text(encoding="utf-8")
            )
            self.assertEqual(proof["authorization"]["status"], "PASS")
            self.assertEqual(
                authorization["execution_artifact_sha256"],
                execution._readiness_artifact_hashes(repo),
            )
            self.assertEqual(
                authorization["readiness_implementation_commit"],
                proof["topology"]["r15_f4_commit"],
            )
            self.assertEqual(proof["comparison"]["behavioral_equal_rows"], 180)


if __name__ == "__main__":
    unittest.main()
