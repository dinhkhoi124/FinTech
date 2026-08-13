"""R13 canonical runtime-environment provenance regressions."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from payresolve_ai.evaluation import critical_v2_execution as execution


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/evaluation/critical_eval_v2_execution.json"


class FakeDistribution:
    def __init__(self, name: str, version: str, marker: str | None = None) -> None:
        self.metadata = {"Name": name}
        self.version = version
        self._path = Path(f"{marker or name}-{version}.dist-info")
        self._marker = marker or f"{name}=={version}"

    def read_text(self, filename: str) -> str | None:
        if filename == "METADATA":
            return f"Name: {self.metadata['Name']}\nVersion: {self.version}\nMarker: {self._marker}\n"
        if filename == "RECORD":
            return f"{self._marker},,\n"
        return None


def inventory(*rows: FakeDistribution) -> dict:
    return execution.canonical_package_inventory(rows, required_core_versions={})


class CriticalV2EnvironmentProvenanceTests(unittest.TestCase):
    def test_env_01_duplicate_same_version_is_canonical_invariant(self) -> None:
        one = inventory(FakeDistribution("Demo_Pkg", "1.0"))
        two = inventory(FakeDistribution("Demo_Pkg", "1.0"), FakeDistribution("demo-pkg", "1.0"))
        self.assertEqual(one["canonical_package_fingerprint_sha256"], two["canonical_package_fingerprint_sha256"])
        self.assertEqual(two["duplicate_same_version_occurrence_count"], 1)

    def test_env_02_conflicting_versions_fail_closed(self) -> None:
        with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "CONFLICTING_DISTRIBUTION_VERSIONS"):
            inventory(FakeDistribution("demo", "1"), FakeDistribution("demo", "2"))

    def test_env_03_pep503_separator_normalization(self) -> None:
        result = inventory(
            FakeDistribution("demo-pkg", "1"),
            FakeDistribution("demo_pkg", "1"),
            FakeDistribution("demo.pkg", "1"),
        )
        self.assertEqual(result["canonical_rows"], ["demo-pkg==1"])

    def test_env_04_local_project_multiplicity_is_excluded(self) -> None:
        base = inventory(FakeDistribution("third-party", "1"))
        local = inventory(
            FakeDistribution("third-party", "1"),
            FakeDistribution("payresolve_ai", "0.0.0"),
            FakeDistribution("payresolve-ai", "0.0.0"),
        )
        self.assertEqual(base["canonical_package_fingerprint_sha256"], local["canonical_package_fingerprint_sha256"])
        self.assertEqual(local["excluded_local_project_distribution_occurrences"], 2)

    def test_env_05_raw_count_can_differ_while_canonical_is_equal(self) -> None:
        one = inventory(FakeDistribution("demo", "1"))
        two = inventory(FakeDistribution("demo", "1"), FakeDistribution("demo", "1"))
        self.assertNotEqual(one["raw_discovery_row_count"], two["raw_discovery_row_count"])
        self.assertEqual(one["canonical_package_fingerprint_sha256"], two["canonical_package_fingerprint_sha256"])

    def test_env_06_c1_c2_c3_c4_canonical_identities_equal(self) -> None:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        evidence = json.loads((ROOT / config["readiness_outputs"]["environment_reconciliation"]).read_text(encoding="utf-8"))
        identities = {
            (row["canonical_distribution_count"], row["canonical_package_fingerprint_sha256"])
            for row in evidence["context_invariance_results"]
        }
        self.assertEqual(len(identities), 1)

    def test_env_07_core_five_exact_versions_pass(self) -> None:
        result = execution.canonical_package_inventory()
        self.assertEqual(
            {name: row["version"] for name, row in result["core_ml_dependencies"].items()},
            execution.CORE_ML_DEPENDENCY_VERSIONS,
        )

    def test_env_08_wrong_core_version_rejects(self) -> None:
        with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "core dependency version mismatch"):
            execution.canonical_package_inventory(
                [FakeDistribution("numpy", "0")], required_core_versions={"numpy": "2.2.6"}
            )

    def test_env_09_core_conflicting_version_rejects(self) -> None:
        with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "CONFLICTING_DISTRIBUTION_VERSIONS"):
            execution.canonical_package_inventory(
                [FakeDistribution("numpy", "2.2.6"), FakeDistribution("numpy", "1.26.4")],
                required_core_versions={"numpy": "2.2.6"},
            )

    def test_env_10_readiness_and_runtime_share_identity_function(self) -> None:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        identity = execution.canonical_package_inventory()
        contract = execution.load_environment_contract(ROOT, config)
        authorization = {"authorization_commit": "a", "readiness_implementation_commit": "r",
                         "reviewed_environment_identity_sha256": contract["environment_identity_sha256"]}
        with patch.dict(os.environ, config["runtime_environment"]["required_environment"], clear=True), \
                patch.object(execution, "_gpu_summary", return_value={}):
            runtime = execution._runtime_environment_static(ROOT, CONFIG_PATH, config, authorization)
        for key in (
            "canonicalization_algorithm", "canonical_distribution_count",
            "canonical_package_fingerprint_sha256", "conflicting_version_count",
            "core_ml_dependencies",
        ):
            self.assertEqual(runtime["installed_packages"][key], identity[key])
        readiness = json.loads((ROOT / config["readiness_outputs"]["environment_manifest"]).read_text(encoding="utf-8"))
        for key in (
            "canonicalization_algorithm", "canonical_distribution_count",
            "canonical_package_fingerprint_sha256", "conflicting_version_count",
            "core_ml_dependencies",
        ):
            self.assertEqual(readiness["installed_packages"][key], identity[key])

    def test_env_11_authoring_path_is_not_duplicated(self) -> None:
        code = """
import sys
from pathlib import Path
from scripts.evaluation.week3_critical_v2_execution import ensure_source_root
root = Path(sys.argv[1]).resolve()
source = ensure_source_root(root)
print(sum(Path(entry or '.').resolve() == source for entry in sys.path))
"""
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str((ROOT / "src").resolve())
        result = subprocess.run(
            [sys.executable, "-c", code, str(ROOT)], cwd=ROOT, env=environment,
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(result.stdout.strip(), "1")

    def test_env_12_to_16_settled_r13_boundaries(self) -> None:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        probe = json.loads((ROOT / config["readiness_outputs"]["offline_encoder_probe"]).read_text(encoding="utf-8"))
        comparison = json.loads((ROOT / config["readiness_outputs"]["runtime_payload_comparison"]).read_text(encoding="utf-8"))
        negative = json.loads((ROOT / config["readiness_outputs"]["a12_negative_control"]).read_text(encoding="utf-8"))
        self.assertEqual(config["runtime_environment"]["required_environment"]["HF_HUB_OFFLINE"], "1")
        self.assertEqual(probe["embedding_ndarray_sha256"], "83483507be7e9c48ca8caff139e15dc3e1f88509addd55793b7fc96e95f87f8e")
        self.assertEqual(probe["network_attempt_count"], 0)
        self.assertEqual(negative["status"], "REJECTED_AS_EXPECTED")
        self.assertEqual(execution.verify_candidate_bytes(ROOT, config)["verified_artifacts"], 23)
        self.assertEqual((comparison["payload_count"], comparison["forbidden_field_occurrences"]), (60, 0))


if __name__ == "__main__":
    unittest.main()
