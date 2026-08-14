from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.evaluation import week3_critical_v2_execution as cli
from scripts.evaluation import prepare_critical_v2_ea1_revision15_evidence as r15_evidence

from payresolve_ai.evaluation import critical_v2_execution as execution


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/evaluation/critical_eval_v2_execution.json"


class Revision15EvaluationStateClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = execution.load_execution_config(CONFIG_PATH)
        self.primary_refs = execution.evaluation_direct_input_references(
            self.config, "primary"
        )

    def _copy(self, target: Path, relative: str) -> None:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)

    def _primary_workspace(self, *, exact_legacy_state: bool) -> tuple[tempfile.TemporaryDirectory[str], Path, dict, dict]:
        temporary = tempfile.TemporaryDirectory(prefix="ea1_r15_state_")
        root = Path(temporary.name)
        config_relative = "configs/evaluation/critical_eval_v2_execution.json"
        state_relative = self.config["evaluation_outputs"]["execution_state"]
        paths = {
            config_relative,
            self.config["state_machine"]["spec"],
            self.config["continuation"]["historical_runtime_environment"]["path"],
            *self.primary_refs,
            *(self.config["evaluation_outputs"]["primary"].values()),
        }
        for relative in paths:
            self._copy(root, relative)
        self._copy(root, state_relative)
        state_path = root / state_relative
        state = json.loads(state_path.read_text(encoding="utf-8"))
        authorization = {
            "authorization_commit": "2" * 40,
            "readiness_implementation_commit": "3" * 40,
            "continuation_authorized": True,
            **execution.CONTINUATION_AUTHORIZATION_FIELDS,
        }
        if not exact_legacy_state:
            state["authorization_commit"] = authorization["authorization_commit"]
            state["readiness_implementation_commit"] = authorization[
                "readiness_implementation_commit"
            ]
            current_config_hash = execution.sha256_file(root / config_relative)
            current_runtime = root / self.config["runtime_environment"]["manifest"]
            current_runtime.parent.mkdir(parents=True, exist_ok=True)
            current_runtime.write_bytes(
                (root / self.config["continuation"]["historical_runtime_environment"]["path"]).read_bytes()
            )
            for entry in state["history"][:3]:
                entry["direct_input_sha256"][config_relative] = current_config_hash
                del entry["direct_input_sha256"][self.config["continuation"]["historical_runtime_environment"]["path"]]
                entry["direct_input_sha256"][self.config["runtime_environment"]["manifest"]] = execution.sha256_file(current_runtime)
            state["history"][4]["direct_input_sha256"] = {
                relative: execution.sha256_file(root / relative)
                for relative in self.primary_refs
            }
            state_path.write_text(
                json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        return temporary, root, state, authorization

    def test_historical_r14_index4_mismatch_is_reproduced_before_model(self) -> None:
        historical = json.loads(
            (ROOT / self.config["evaluation_outputs"]["execution_state"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertNotEqual(set(historical["history"][4]["direct_input_sha256"]), set(self.primary_refs))
        self.assertIn(self.config["safety_evaluator"]["boundary_rules"], historical["history"][4]["direct_input_sha256"])
        self.assertNotIn(self.config["safety_evaluator"]["disclosure_literal_registry"], historical["history"][4]["direct_input_sha256"])
        temporary, root, state, authorization = self._primary_workspace(exact_legacy_state=False)
        try:
            state["history"][4] = copy.deepcopy(historical["history"][4])
            with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "input set mismatch at index 4"):
                execution.validate_state_history(root, self.config, state, authorization)
        finally:
            temporary.cleanup()

    def test_one_canonical_six_input_closure_drives_indices4_and9(self) -> None:
        self.assertEqual(len(self.primary_refs), 6)
        expected_suffix = self.primary_refs[1:]
        repro = execution.evaluation_direct_input_references(
            self.config, "reproducibility_rerun"
        )
        self.assertEqual(repro[1:], expected_suffix)
        self.assertEqual(execution._expected_transition_paths(self.config, 4)[0], set(self.primary_refs))
        self.assertEqual(execution._expected_transition_paths(self.config, 9)[0], set(repro))

    def test_validator_rejects_missing_extra_and_wrong_hash_for_six_inputs(self) -> None:
        temporary, root, state, authorization = self._primary_workspace(exact_legacy_state=False)
        try:
            execution.validate_state_history(root, self.config, state, authorization)
            for relative in self.primary_refs:
                mutated = copy.deepcopy(state)
                del mutated["history"][4]["direct_input_sha256"][relative]
                with self.assertRaises(execution.CriticalV2ExecutionError):
                    execution.validate_state_history(root, self.config, mutated, authorization)
                mutated = copy.deepcopy(state)
                mutated["history"][4]["direct_input_sha256"][relative] = "0" * 64
                with self.assertRaises(execution.CriticalV2ExecutionError):
                    execution.validate_state_history(root, self.config, mutated, authorization)
            mutated = copy.deepcopy(state)
            mutated["history"][4]["direct_input_sha256"]["unexpected"] = "0" * 64
            with self.assertRaises(execution.CriticalV2ExecutionError):
                execution.validate_state_history(root, self.config, mutated, authorization)
        finally:
            temporary.cleanup()

    def test_boundary_and_literal_file_mutations_fail_validation(self) -> None:
        temporary, root, state, authorization = self._primary_workspace(exact_legacy_state=False)
        try:
            for key in ("boundary_rules", "disclosure_literal_registry"):
                path = root / self.config["safety_evaluator"][key]
                original = path.read_bytes()
                path.write_bytes(original + b"mutation")
                with self.assertRaises(execution.CriticalV2ExecutionError):
                    execution.validate_state_history(root, self.config, state, authorization)
                path.write_bytes(original)
        finally:
            temporary.cleanup()

    def test_isolated_one_time_continuation_preserves_primary_and_runtime(self) -> None:
        temporary, root, _, authorization = self._primary_workspace(exact_legacy_state=True)
        try:
            primary = self.config["evaluation_outputs"]["primary"]
            before = {key: execution.sha256_file(root / primary[key]) for key in execution.LOCKED_PRIMARY_SHA256}
            historical_runtime = root / self.config["continuation"]["historical_runtime_environment"]["path"]
            runtime_before = execution.sha256_file(historical_runtime)
            with patch.object(execution, "verify_execution_authorization", return_value=authorization):
                receipt = execution.migrate_r14_primary_state_for_r15_continuation(
                    root, root / "configs/evaluation/critical_eval_v2_execution.json"
                )
            repaired = json.loads(
                (root / self.config["evaluation_outputs"]["execution_state"]).read_text(encoding="utf-8")
            )
            execution.validate_state_history(root, self.config, repaired, authorization)
            self.assertEqual(len(repaired["history"][4]["direct_input_sha256"]), 6)
            self.assertEqual(before, execution.LOCKED_PRIMARY_SHA256)
            self.assertEqual(execution.sha256_file(historical_runtime), runtime_before)
            self.assertEqual(receipt["model_calls"], 0)
            with self.assertRaises(execution.CriticalV2ExecutionError):
                with patch.object(execution, "verify_execution_authorization", return_value=authorization):
                    execution.migrate_r14_primary_state_for_r15_continuation(
                        root, root / "configs/evaluation/critical_eval_v2_execution.json"
                    )
        finally:
            temporary.cleanup()

    def test_synthetic_future_runtime_reaches_pre_model_repro_v0_gate(self) -> None:
        temporary, root, _, authorization = self._primary_workspace(exact_legacy_state=True)
        try:
            with patch.object(execution, "verify_execution_authorization", return_value=authorization):
                execution.migrate_r14_primary_state_for_r15_continuation(
                    root, root / "configs/evaluation/critical_eval_v2_execution.json"
                )
            current_runtime = root / self.config["runtime_environment"]["manifest"]
            historical_runtime = root / self.config["continuation"]["historical_runtime_environment"]["path"]
            historical_hash = execution.sha256_file(historical_runtime)
            with patch.object(execution, "_runtime_environment_static", return_value={"model_loaded": False}):
                frozen = execution.freeze_or_verify_runtime_environment(
                    root, root / "configs/evaluation/critical_eval_v2_execution.json", self.config, authorization
                )
            repaired = json.loads(
                (root / self.config["evaluation_outputs"]["execution_state"]).read_text(encoding="utf-8")
            )
            execution.validate_state_history(root, self.config, repaired, authorization)
            self.assertTrue(current_runtime.is_file())
            self.assertEqual(execution.sha256_file(historical_runtime), historical_hash)
            self.assertEqual(frozen["reference"], self.config["runtime_environment"]["manifest"])
            self.assertEqual(repaired["state"], "PRIMARY_EVALUATED")
        finally:
            temporary.cleanup()

    def test_all_twelve_transition_contracts_are_defined(self) -> None:
        matrix = [execution._expected_transition_paths(self.config, index) for index in range(12)]
        self.assertEqual(len(matrix), 12)
        self.assertTrue(all(inputs and outputs for inputs, outputs in matrix))
        self.assertEqual(len(matrix[4][0]), 6)
        self.assertEqual(len(matrix[9][0]), 6)

    def test_handcrafted_authority_dict_is_not_a_supported_migration_api(self) -> None:
        temporary, root, _, authorization = self._primary_workspace(exact_legacy_state=True)
        try:
            state_path = root / self.config["evaluation_outputs"]["execution_state"]
            before = execution.sha256_file(state_path)
            with self.assertRaises(TypeError):
                execution.migrate_r14_primary_state_for_r15_continuation(
                    root, root / "configs/evaluation/critical_eval_v2_execution.json", authorization
                )
            self.assertEqual(execution.sha256_file(state_path), before)
            self.assertFalse((root / self.config["continuation"]["receipt"]).exists())
        finally:
            temporary.cleanup()

    def test_continuation_field_mutations_fail_authorization_validation(self) -> None:
        candidate = json.loads((ROOT / self.config["authorization"]["candidate"]).read_text(encoding="utf-8"))
        candidate.update({
            "authorization_status": "AUTHORIZED_FOR_PRIMARY_EXECUTION",
            "evaluation_authorized": True,
            "readiness_commit_binding": "BOUND_TO_REVIEWED_READINESS_IMPLEMENTATION_COMMIT",
            "readiness_implementation_commit": "1" * 40,
            "senior_authorization_claimed": True,
            "senior_authorization_verdict": "APPROVE_EXECUTION",
            **execution.CONTINUATION_AUTHORIZATION_FIELDS,
        })
        mutations = {
            "continuation_authorized": False,
            "continuation_migration": "WRONG",
            "continuation_from_authorization_commit": "0" * 40,
            "continuation_from_readiness_commit": "0" * 40,
            "continuation_legacy_state_sha256": "0" * 64,
            "continuation_legacy_runtime_environment_sha256": "0" * 64,
        }
        for key, value in mutations.items():
            with self.subTest(key=key):
                mutated = copy.deepcopy(candidate)
                mutated[key] = value
                with self.assertRaisesRegex(execution.CriticalV2ExecutionError, key):
                    execution._validate_authorization_payload(ROOT, CONFIG_PATH, self.config, mutated)
        missing = copy.deepcopy(candidate); del missing["continuation_authorized"]
        with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "continuation_authorized"):
            execution._validate_authorization_payload(ROOT, CONFIG_PATH, self.config, missing)

    def test_authorization_failure_precedes_all_migration_writes(self) -> None:
        temporary, root, _, _ = self._primary_workspace(exact_legacy_state=True)
        try:
            state_path = root / self.config["evaluation_outputs"]["execution_state"]
            before = execution.sha256_file(state_path)
            with patch.object(execution, "verify_execution_authorization", side_effect=execution.CriticalV2ExecutionError("uncommitted authorization record")):
                with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "uncommitted"):
                    execution.migrate_r14_primary_state_for_r15_continuation(
                        root, root / "configs/evaluation/critical_eval_v2_execution.json"
                    )
            self.assertEqual(execution.sha256_file(state_path), before)
            self.assertFalse((root / self.config["continuation"]["receipt"]).exists())
        finally:
            temporary.cleanup()

    def test_transaction_failure_leaves_prepared_recovery_receipt_and_legacy_state(self) -> None:
        temporary, root, _, authorization = self._primary_workspace(exact_legacy_state=True)
        try:
            state_path = root / self.config["evaluation_outputs"]["execution_state"]
            before = execution.sha256_file(state_path)
            with patch.object(execution, "verify_execution_authorization", return_value=authorization), patch.object(execution, "_atomic_write_json", side_effect=OSError("injected replace failure")):
                with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "PREPARED receipt"):
                    execution.migrate_r14_primary_state_for_r15_continuation(
                        root, root / "configs/evaluation/critical_eval_v2_execution.json"
                    )
            self.assertEqual(execution.sha256_file(state_path), before)
            receipt = json.loads((root / self.config["continuation"]["receipt"]).read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "PREPARED")
            with self.assertRaises(execution.CriticalV2ExecutionError):
                execution.validate_state_history(root, self.config, json.loads(state_path.read_text(encoding="utf-8")), authorization)
        finally:
            temporary.cleanup()

    def test_one_shot_cli_is_explicit(self) -> None:
        parsed = cli.parser().parse_args(["migrate-r15-continuation"])
        self.assertEqual(parsed.command, "migrate-r15-continuation")

    def test_migration_artifact_presence_and_drift_guards(self) -> None:
        cases = ("primary_drift", "reproduction_present", "future_runtime_present", "receipt_present")
        for case in cases:
            with self.subTest(case=case):
                temporary, root, _, authorization = self._primary_workspace(exact_legacy_state=True)
                try:
                    if case == "primary_drift":
                        path = root / self.config["evaluation_outputs"]["primary"]["V0_raw"]
                        path.write_bytes(path.read_bytes() + b"drift")
                    elif case == "reproduction_present":
                        path = root / self.config["evaluation_outputs"]["reproducibility_rerun"]["V0_raw"]
                        path.parent.mkdir(parents=True, exist_ok=True); path.write_text("occupied\n", encoding="utf-8")
                    elif case == "future_runtime_present":
                        path = root / self.config["runtime_environment"]["manifest"]
                        path.parent.mkdir(parents=True, exist_ok=True); path.write_text("{}\n", encoding="utf-8")
                    else:
                        path = root / self.config["continuation"]["receipt"]
                        path.parent.mkdir(parents=True, exist_ok=True); path.write_text("{}\n", encoding="utf-8")
                    state_path = root / self.config["evaluation_outputs"]["execution_state"]
                    before = execution.sha256_file(state_path)
                    with patch.object(execution, "verify_execution_authorization", return_value=authorization):
                        with self.assertRaises(execution.CriticalV2ExecutionError):
                            execution.migrate_r14_primary_state_for_r15_continuation(
                                root, root / "configs/evaluation/critical_eval_v2_execution.json"
                            )
                    self.assertEqual(execution.sha256_file(state_path), before)
                finally:
                    temporary.cleanup()

    def test_synthetic_committed_topology_preserves_real_common_git_config(self) -> None:
        candidate = json.loads(
            (ROOT / self.config["authorization"]["candidate"]).read_text(encoding="utf-8")
        )
        candidate["execution_contract_sha256"] = execution.sha256_file(CONFIG_PATH)
        candidate["execution_artifact_sha256"] = execution._readiness_artifact_hashes(ROOT)
        before = r15_evidence.common_git_config_snapshot(ROOT)
        result = r15_evidence.committed_synthetic_a15(ROOT, self.config, candidate)
        after = r15_evidence.common_git_config_snapshot(ROOT)
        self.assertEqual(before["sha256"], after["sha256"])
        self.assertEqual(before["bytes"], after["bytes"])
        self.assertEqual(before["user_name"], after["user_name"])
        self.assertEqual(before["user_email"], after["user_email"])
        self.assertEqual(before["core_autocrlf"], after["core_autocrlf"])
        self.assertEqual(len(result["common_config_phase_checks"]), 6)
        self.assertTrue(all(row["status"] == "UNCHANGED" for row in result["common_config_phase_checks"]))
        for identity in (result["readiness_identity"], result["authorization_identity"]):
            self.assertEqual(identity["author_name"], "R15 F1 Synthetic")
            self.assertEqual(identity["author_email"], "r15-f1@example.invalid")
            self.assertEqual(identity["committer_name"], "R15 F1 Synthetic")
            self.assertEqual(identity["committer_email"], "r15-f1@example.invalid")


if __name__ == "__main__":
    unittest.main()
