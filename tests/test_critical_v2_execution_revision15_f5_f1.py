from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.evaluation import week3_critical_v2_execution as cli
from payresolve_ai.evaluation import critical_v2_execution as execution


ROOT = Path(__file__).resolve().parents[1]
CONFIG_REL = "configs/evaluation/critical_eval_v2_execution.json"
CONFIG_PATH = ROOT / CONFIG_REL


class Revision15F5F1FinalizationHashClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = execution.load_execution_config(CONFIG_PATH)
        self.outputs = self.config["evaluation_outputs"]
        self.future = {
            "authorization_commit": "a" * 40,
            "readiness_implementation_commit": "b" * 40,
        }

    def _copy(self, root: Path, relative: str) -> None:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)

    def _workspace(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory(prefix="ea1_r15_f5_f1_")
        root = Path(temporary.name)
        paths = {
            CONFIG_REL,
            self.config["state_machine"]["spec"],
            self.outputs["execution_state"],
            self.outputs["reproduction_comparison"],
            self.config["continuation"]["receipt"],
            execution.POSTEVAL_CONTINUATION_RECEIPT,
            self.config["continuation"]["historical_runtime_environment"]["path"],
            self.config["runtime_environment"]["manifest"],
            *self.outputs["primary"].values(),
            *self.outputs["reproducibility_rerun"].values(),
            *execution.evaluation_direct_input_references(self.config, "primary"),
            *execution.evaluation_direct_input_references(self.config, "reproducibility_rerun"),
        }
        for relative in paths:
            self._copy(root, relative)
        # The published source state is FINALIZED/history-12.  Reconstruct the
        # exact historical REPRO_VERIFIED/history-11 A16/F4 input consumed by
        # the one-shot F5 migration; using today's state directly would make
        # these historical tests depend on publication progress.
        state_path = root / self.outputs["execution_state"]
        historical_state = execution._read_json(state_path)
        historical_state.update(
            {
                "state": "REPRO_VERIFIED",
                "authorization_commit": execution.LEGACY_R15_F5_AUTHORIZATION_COMMIT,
                "readiness_implementation_commit": execution.LEGACY_R15_F5_READINESS_COMMIT,
                "history": historical_state["history"][:11],
            }
        )
        execution._atomic_write_json(state_path, historical_state)
        self.assertEqual(historical_state["state"], "REPRO_VERIFIED")
        self.assertEqual(len(historical_state["history"]), 11)
        self.assertEqual(
            execution.sha256_file(state_path), execution.LEGACY_R15_F5_STATE_SHA256
        )
        self.assertEqual(
            execution.sha256_file(root / execution.POSTEVAL_CONTINUATION_RECEIPT),
            execution.LEGACY_R15_F5_POSTEVAL_RECEIPT_SHA256,
        )
        self.assertFalse((root / execution.POSTVERIFY_CONTINUATION_RECEIPT).exists())
        self.assertFalse((root / self.outputs["final_summary"]).exists())
        authorization_path = root / self.config["authorization"]["committed_record"]
        authorization_path.parent.mkdir(parents=True, exist_ok=True)
        authorization_path.write_text(
            json.dumps(execution.POSTVERIFY_CONTINUATION_AUTHORIZATION_FIELDS, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return temporary, root

    def _migrate_and_finalize(self, root: Path) -> tuple[dict, dict, dict]:
        config_path = root / CONFIG_REL
        with patch.object(execution, "verify_execution_authorization", return_value=self.future), patch.object(
            execution, "freeze_or_verify_runtime_environment", side_effect=AssertionError("runtime must not execute")
        ):
            receipt = execution.migrate_r15_f5_postverify_continuation(root, config_path)
            pre_state = execution._read_json(root / self.outputs["execution_state"])
            summary = execution.finalize_results(root, config_path)
            verified = execution.verify_results(root, config_path)
        return receipt, pre_state, {"summary": summary, "verified": verified}

    def test_bug_fingerprints_are_locked(self) -> None:
        self.assertEqual(execution.LEGACY_R15_F5_STATE_SHA256, "7b221a4c35878a1aa597220e8e089d090bc9317f39b6201872cfa7c5f04387bd")
        self.assertEqual(execution.LEGACY_R15_F5_COMPARISON_SHA256, "3476317b6946f703b43375f039e3b4f25d777c42e7c055698d490585c5e9cb80")
        self.assertEqual(execution.LEGACY_R15_F5_POSTEVAL_RECEIPT_SHA256, "9d258ee17f64b930f092a7c6502f0e475405ed4773aab05e2cc06257070583d8")

    def test_postverify_migration_finalize_verify_pass_without_hash_cycle(self) -> None:
        temporary, root = self._workspace()
        try:
            before = execution._read_json(root / self.outputs["execution_state"])
            receipt, pre_state, result = self._migrate_and_finalize(root)
            state = execution._read_json(root / self.outputs["execution_state"])
            summary = execution._read_json(root / self.outputs["final_summary"])
            self.assertEqual(receipt["status_history"], ["PREPARED", "PASS"])
            self.assertEqual(pre_state["history"], before["history"])
            self.assertEqual(pre_state["state"], "REPRO_VERIFIED")
            self.assertEqual(state["state"], "FINALIZED")
            self.assertEqual(len(state["history"]), 12)
            self.assertEqual(result["verified"]["status"], "PASS")
            self.assertNotIn(self.outputs["execution_state"], summary["artifact_sha256"])
            self.assertEqual(summary["pre_finalization_state_sha256"], receipt["repaired_state_sha256"])
            self.assertEqual(set(summary["direct_input_sha256"]), set(state["history"][11]["direct_input_sha256"]))
            self.assertEqual(state["history"][11]["direct_output_sha256"], {self.outputs["final_summary"]: execution.sha256_file(root / self.outputs["final_summary"])})
            for counter in ("model_calls", "encoder_calls", "retrieval_calls", "generation_calls", "evaluator_calls", "comparator_calls"):
                self.assertEqual(receipt[counter], 0)
        finally:
            temporary.cleanup()

    def test_fourteen_finalization_negative_controls_fail_closed(self) -> None:
        temporary, root = self._workspace()
        try:
            config_path = root / CONFIG_REL
            with patch.object(execution, "verify_execution_authorization", return_value=self.future):
                execution.migrate_r15_f5_postverify_continuation(root, config_path)
                pre_state = execution._read_json(root / self.outputs["execution_state"])
                execution.finalize_results(root, config_path)
            finalized = Path(tempfile.mkdtemp(prefix="ea1_r15_f5_finalized_"))
            shutil.copytree(root, finalized, dirs_exist_ok=True)
            cases: list[tuple[str, callable]] = []
            summary_path = self.outputs["final_summary"]
            artifact_paths = [
                self.outputs["reproduction_comparison"],
                self.outputs["primary"]["outcomes"], self.outputs["primary"]["metrics"], self.outputs["primary"]["claim_audit"],
                self.outputs["reproducibility_rerun"]["outcomes"], self.outputs["reproducibility_rerun"]["metrics"], self.outputs["reproducibility_rerun"]["claim_audit"],
            ]

            def mutate_json(target: Path, mutator) -> None:
                payload = execution._read_json(target)
                mutator(payload)
                execution._atomic_write_json(target, payload)

            cases.append(("final_summary", lambda r: mutate_json(r / summary_path, lambda p: p.__setitem__("model_verdict", "MUTATED"))))
            for relative in artifact_paths:
                cases.append((relative, lambda r, rel=relative: (r / rel).open("ab").write(b"\n")))
            cases.append(("transition_input", lambda r: mutate_json(r / self.outputs["execution_state"], lambda p: p["history"][11]["direct_input_sha256"].__setitem__(artifact_paths[0], "0" * 64))))
            cases.append(("transition_output", lambda r: mutate_json(r / self.outputs["execution_state"], lambda p: p["history"][11]["direct_output_sha256"].__setitem__(summary_path, "0" * 64))))
            cases.append(("pre_state", lambda r: mutate_json(r / summary_path, lambda p: p.__setitem__("pre_finalization_state_sha256", "0" * 64))))

            detected = 0
            for name, mutate in cases:
                with self.subTest(name=name), tempfile.TemporaryDirectory(prefix="ea1_r15_f5_negative_") as case_dir:
                    case_root = Path(case_dir)
                    shutil.copytree(finalized, case_root, dirs_exist_ok=True)
                    mutate(case_root)
                    with patch.object(execution, "verify_execution_authorization", return_value=self.future), self.assertRaises(execution.CriticalV2ExecutionError):
                        execution.verify_results(case_root, case_root / CONFIG_REL)
                    detected += 1

            with tempfile.TemporaryDirectory(prefix="ea1_r15_f5_overwrite_") as case_dir:
                case_root = Path(case_dir)
                shutil.copytree(finalized, case_root, dirs_exist_ok=True)
                execution._atomic_write_json(case_root / self.outputs["execution_state"], pre_state)
                with patch.object(execution, "verify_execution_authorization", return_value=self.future), self.assertRaisesRegex(execution.CriticalV2ExecutionError, "overwrite"):
                    execution.finalize_results(case_root, case_root / CONFIG_REL)
                detected += 1
            with patch.object(execution, "verify_execution_authorization", return_value=self.future), self.assertRaisesRegex(execution.CriticalV2ExecutionError, "REPRO_VERIFIED"):
                execution.finalize_results(finalized, finalized / CONFIG_REL)
            detected += 1
            with tempfile.TemporaryDirectory(prefix="ea1_r15_f5_before_final_") as case_dir:
                case_root = Path(case_dir)
                shutil.copytree(finalized, case_root, dirs_exist_ok=True)
                execution._atomic_write_json(case_root / self.outputs["execution_state"], pre_state)
                (case_root / summary_path).unlink()
                with patch.object(execution, "verify_execution_authorization", return_value=self.future), self.assertRaisesRegex(execution.CriticalV2ExecutionError, "FINALIZED"):
                    execution.verify_results(case_root, case_root / CONFIG_REL)
                detected += 1
            self.assertEqual(detected, 14)
            shutil.rmtree(finalized)
        finally:
            temporary.cleanup()

    def test_cli_and_config_remain_explicit(self) -> None:
        parsed = cli.parser().parse_args(["migrate-r15-f5-postverify-continuation"])
        self.assertEqual(parsed.command, "migrate-r15-f5-postverify-continuation")
        self.assertEqual(execution.sha256_file(CONFIG_PATH), "36f372c6dd08e948bceea52d3222e8510e32382bec8748e264f8ac4eb977d943")


if __name__ == "__main__":
    unittest.main()
