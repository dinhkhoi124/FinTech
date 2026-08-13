"""R13 authorization-environment and complete runtime-source closure regressions."""

from __future__ import annotations

import copy
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from payresolve_ai.evaluation import critical_v2_execution as execution


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/evaluation/critical_eval_v2_execution.json"


class CriticalV2BindingFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = execution.load_execution_config(CONFIG_PATH)
        cls.contract = execution.load_environment_contract(ROOT, cls.config)
        cls.identity = cls.contract["environment_identity"]
        cls.authorization = {
            "authorization_commit": "A13",
            "readiness_implementation_commit": "R13",
            "reviewed_environment_identity_sha256": cls.contract[
                "environment_identity_sha256"
            ],
        }

    def _package_identity(self) -> dict:
        return execution.canonical_package_inventory()

    def _assert_runtime_rejects(self, packages: dict, *, python_version: str | None = None,
                                environment: dict[str, str] | None = None) -> None:
        loader = Mock()
        actual_environment = environment or self.config["runtime_environment"]["required_environment"]
        patches = [
            patch.object(execution, "verify_execution_authorization", return_value=self.authorization),
            patch.object(execution, "canonical_package_inventory", return_value=packages),
            patch.object(execution, "_gpu_summary", return_value={}),
        ]
        if python_version is not None:
            patches.append(patch.object(execution.platform, "python_version", return_value=python_version))
        with patch.dict(os.environ, actual_environment, clear=True):
            for item in patches:
                item.start()
            try:
                with self.assertRaises(execution.CriticalV2ExecutionError):
                    execution.run_critical(
                        ROOT, CONFIG_PATH, "primary", "V0",
                        model_loader=loader, executor=Mock(),
                    )
            finally:
                for item in reversed(patches):
                    item.stop()
        loader.assert_not_called()

    def test_env_auth_01_canonical_fingerprint_changed(self) -> None:
        packages = self._package_identity()
        packages["canonical_package_fingerprint_sha256"] = "0" * 64
        self._assert_runtime_rejects(packages)

    def test_env_auth_02_canonical_count_changed(self) -> None:
        packages = self._package_identity()
        packages["canonical_distribution_count"] += 1
        self._assert_runtime_rejects(packages)

    def test_env_auth_03_core_wrong_version(self) -> None:
        packages = self._package_identity()
        packages["core_ml_dependencies"]["numpy"]["version"] = "0.0.0"
        self._assert_runtime_rejects(packages)

    def test_env_auth_04_core_same_version_metadata_changed(self) -> None:
        packages = self._package_identity()
        packages["core_ml_dependencies"]["numpy"]["metadata_sha256"] = "1" * 64
        self._assert_runtime_rejects(packages)

    def test_env_auth_05_core_same_version_record_changed(self) -> None:
        packages = self._package_identity()
        packages["core_ml_dependencies"]["numpy"]["record_sha256"] = "2" * 64
        self._assert_runtime_rejects(packages)

    def test_env_auth_06_python_version_changed(self) -> None:
        self._assert_runtime_rejects(self._package_identity(), python_version="0.0.0")

    def test_env_auth_07_hf_offline_missing(self) -> None:
        environment = {"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
        self._assert_runtime_rejects(self._package_identity(), environment=environment)

    def test_authorization_candidate_binds_reviewed_environment(self) -> None:
        candidate = json.loads(
            (ROOT / self.config["authorization"]["candidate"]).read_text(encoding="utf-8")
        )
        contract_path = ROOT / self.config["readiness_outputs"]["environment_contract"]
        self.assertEqual(
            candidate["reviewed_environment_identity_sha256"],
            self.contract["environment_identity_sha256"],
        )
        self.assertEqual(
            candidate["environment_contract_artifact_sha256"],
            execution.sha256_file(contract_path),
        )
        self.assertIn(
            self.config["readiness_outputs"]["environment_manifest"],
            candidate["execution_artifact_sha256"],
        )
        self.assertIn(
            self.config["readiness_outputs"]["environment_contract"],
            candidate["execution_artifact_sha256"],
        )

    def test_complete_runtime_source_closure_is_authorization_bound(self) -> None:
        closure = execution.runtime_source_closure_payload(ROOT, self.config)
        self.assertEqual(closure["source_count"], 18)
        self.assertEqual(closure["silent_omissions"], 0)
        candidate = json.loads(
            (ROOT / self.config["authorization"]["candidate"]).read_text(encoding="utf-8")
        )
        for row in closure["modules"]:
            self.assertTrue(row["authorization_bound"])
            self.assertEqual(candidate["execution_artifact_sha256"][row["path"]], row["sha256"])

    def _assert_source_tamper_rejected(self, relative: str) -> None:
        candidate = json.loads(
            (ROOT / self.config["authorization"]["candidate"]).read_text(encoding="utf-8")
        )
        candidate["evaluation_authorized"] = True
        candidate["senior_authorization_verdict"] = self.config["authorization"]["required_verdict"]
        loader = Mock()
        with tempfile.TemporaryDirectory(prefix="ea1_r13_binding_") as temporary:
            isolated = Path(temporary)
            for path in execution.READINESS_HASH_PATHS:
                target = isolated / path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / path, target)
            tampered = isolated / relative
            tampered.write_bytes(tampered.read_bytes() + b"\n# isolated binding tamper\n")
            isolated_config = isolated / "configs/evaluation/critical_eval_v2_execution.json"
            with self.assertRaisesRegex(
                execution.CriticalV2ExecutionError,
                "authorization execution source/config/test hash mismatch",
            ):
                execution._validate_authorization_payload(
                    isolated, isolated_config, self.config, candidate
                )
        loader.assert_not_called()

    def test_source_tamper_generation_verification_rejected(self) -> None:
        self._assert_source_tamper_rejected("src/payresolve_ai/generation/verification.py")

    def test_source_tamper_banking77_rejected(self) -> None:
        self._assert_source_tamper_rejected("src/payresolve_ai/data/banking77.py")

    def test_source_tamper_additional_new_module_rejected(self) -> None:
        self._assert_source_tamper_rejected("src/payresolve_ai/generation/citations.py")


if __name__ == "__main__":
    unittest.main()
