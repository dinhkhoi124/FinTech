"""Focused EA1 Revision-13 offline/provenance readiness regressions."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from payresolve_ai.evaluation import critical_v2_execution as execution
from payresolve_ai.retrieval import benchmark


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/evaluation/critical_eval_v2_execution.json"


class CriticalV2ExecutionRevision13Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    def evidence(self, key: str) -> dict:
        return json.loads((ROOT / self.config["readiness_outputs"][key]).read_text(encoding="utf-8"))

    def test_r13_01_exact_offline_environment_contract(self) -> None:
        self.assertEqual(self.config["readiness_revision"], 13)
        self.assertEqual(self.config["runtime_environment"]["required_environment"], {
            "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "HF_HUB_OFFLINE": "1"
        })

    def test_r13_02_environment_guard_rejects_missing_hf_offline(self) -> None:
        authorization = {"authorization_commit": "a", "readiness_implementation_commit": "r"}
        environment = {"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
        with patch.dict(os.environ, environment, clear=True), patch.object(execution, "canonical_package_inventory", return_value={}), patch.object(execution, "_gpu_summary", return_value={}):
            with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "HF_HUB_OFFLINE"):
                execution._runtime_environment_static(ROOT, CONFIG_PATH, self.config, authorization)

    def test_r13_03_environment_guard_records_all_three_values(self) -> None:
        contract = execution.load_environment_contract(ROOT, self.config)
        authorization = {"authorization_commit": "a", "readiness_implementation_commit": "r",
                         "reviewed_environment_identity_sha256": contract["environment_identity_sha256"]}
        with patch.dict(os.environ, self.config["runtime_environment"]["required_environment"], clear=True), patch.object(execution, "_gpu_summary", return_value={}):
            result = execution._runtime_environment_static(ROOT, CONFIG_PATH, self.config, authorization)
        self.assertEqual(result["deterministic_environment"], self.config["runtime_environment"]["required_environment"])

    def test_r13_04_production_encoder_forces_local_files_only(self) -> None:
        retrieval = json.loads((ROOT / self.config["runtime_dependencies"]["retrieval_config"]["path"]).read_text(encoding="utf-8"))
        with patch.object(benchmark, "_load_encoder", return_value=object()) as loader:
            benchmark._encoder(ROOT, retrieval)
        self.assertIs(loader.call_args.args[1]["encoder"]["local_files_only"], True)

    def test_r13_05_offline_probe_has_zero_network_attempts(self) -> None:
        probe = self.evidence("offline_encoder_probe")
        self.assertEqual((probe["status"], probe["network_attempt_count"]), ("PASS", 0))
        self.assertFalse(probe["gold_or_evaluator_loaded"])
        self.assertFalse(probe["inference_or_evaluation_run"])

    def test_r13_06_offline_probe_vector_is_stable(self) -> None:
        probe = self.evidence("offline_encoder_probe")
        self.assertEqual(probe["shape"], [1, 384])
        self.assertEqual(probe["dtype"], "float32")
        self.assertEqual(probe["embedding_ndarray_sha256"], probe["expected_embedding_ndarray_sha256"])

    def test_r13_07_snapshot_manifest_reverification_passes(self) -> None:
        self.assertEqual(execution.verify_runtime_asset_manifest(ROOT, self.config)["status"], "PASS")

    def test_r13_08_all_transitive_runtime_sources_are_registered(self) -> None:
        binding = self.evidence("transitive_runtime_source_binding")
        expected = {row[0] for row in execution.RUNTIME_SOURCE_CLOSURE}
        self.assertEqual(set(binding["source_sha256"]), expected)
        self.assertEqual(binding["source_count"], 18)
        candidate = json.loads((ROOT / self.config["authorization"]["candidate"]).read_text(encoding="utf-8"))
        for path in expected:
            self.assertEqual(candidate["execution_artifact_sha256"][path], execution.sha256_file(ROOT / path))

    def test_r13_09_isolated_transitive_source_tamper_is_rejected(self) -> None:
        candidate = json.loads((ROOT / self.config["authorization"]["candidate"]).read_text(encoding="utf-8"))
        candidate["evaluation_authorized"] = True
        candidate["senior_authorization_verdict"] = self.config["authorization"]["required_verdict"]
        with tempfile.TemporaryDirectory(prefix="ea1_r13_tamper_") as temporary:
            isolated = Path(temporary)
            required = list(execution.READINESS_HASH_PATHS) + [self.config["readiness_outputs"]["runtime_asset_manifest"]]
            for relative in required:
                target = isolated / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
            tampered = isolated / execution.TRANSITIVE_RUNTIME_SOURCE_PATHS[0]
            tampered.write_bytes(tampered.read_bytes() + b"\n# isolated tamper\n")
            isolated_config = isolated / "configs/evaluation/critical_eval_v2_execution.json"
            with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "execution source/config/test hash mismatch"):
                execution._validate_authorization_payload(isolated, isolated_config, self.config, candidate)

    def test_r13_10_authorization_precedes_model_loader(self) -> None:
        loader = Mock()
        with self.assertRaises(execution.CriticalV2ExecutionError):
            execution.run_critical(ROOT, CONFIG_PATH, "primary", "V0", model_loader=loader, executor=Mock())
        loader.assert_not_called()

    def test_r13_11_a12_authorization_is_negative_control(self) -> None:
        evidence = self.evidence("a12_negative_control")
        self.assertEqual(evidence["status"], "REJECTED_AS_EXPECTED")
        self.assertFalse(evidence["model_loaded"])

    def test_r13_12_candidate_revision7_remains_23_of_23(self) -> None:
        self.assertEqual(execution.verify_candidate_bytes(ROOT, self.config)["verified_artifacts"], 23)

    def test_r13_13_candidate_core_hashes_are_unchanged(self) -> None:
        self.assertEqual(self.config["candidate"]["manifest_sha256"], execution.EXPECTED_CANDIDATE_MANIFEST_SHA256)
        self.assertEqual(execution.sha256_file(ROOT / "data/evaluation/critical_eval_v2_mapping.jsonl"), execution.EXPECTED_MAPPING_SHA256)
        self.assertEqual(execution.sha256_file(ROOT / "data/evaluation/critical_eval_v2_support_judgments.jsonl"), execution.EXPECTED_PASS_B_SHA256)

    def test_r13_14_all_primary_and_reproduction_outputs_remain_absent(self) -> None:
        preserved = {self.config["runtime_environment"]["manifest"], self.config["evaluation_outputs"]["execution_state"]}
        existing = [path for path in execution._evaluation_output_paths(self.config) if path not in preserved and (ROOT / path).exists()]
        self.assertEqual(existing, [])

    def test_r13_15_no_gold_or_evaluator_calls_and_candidate_not_authorized(self) -> None:
        incident = self.evidence("runtime_incident_lineage")
        self.assertEqual((incident["gold_loader_calls"], incident["evaluator_calls"]), (0, 0))
        candidate = json.loads((ROOT / self.config["authorization"]["candidate"]).read_text(encoding="utf-8"))
        self.assertIs(candidate["evaluation_authorized"], False)
        self.assertIs(candidate["senior_authorization_claimed"], False)


if __name__ == "__main__":
    unittest.main()
