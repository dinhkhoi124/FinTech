"""Narrow Revision-11 regressions for exact raw batch membership."""

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from payresolve_ai.evaluation import critical_v2_execution as execution
try:
    import test_critical_v2_execution_revision10 as revision10
except ModuleNotFoundError:  # Module-mode execution from the repository root.
    from tests import test_critical_v2_execution_revision10 as revision10


ROOT = revision10.ROOT
CONFIG_PATH = revision10.CONFIG_PATH


class CriticalV2ExecutionRevision11Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = execution.load_execution_config(CONFIG_PATH)

    def _batch(self, variant: str = "V0") -> tuple[list[dict], list[dict]]:
        payloads = [
            {
                "query_id": f"q{index:02d}",
                "model_input_text": f"text {index}",
                "model_input_sha256": f"{index:064x}",
            }
            for index in range(60)
        ]
        rows = []
        for payload in payloads:
            row = revision10.CriticalV2ExecutionRevision10Tests._raw()
            row.update(
                {
                    "execution_id": execution.runtime_execution_id(
                        self.config, "primary", variant
                    ),
                    "variant_id": variant,
                    "query_id": payload["query_id"],
                    "model_input_sha256": payload["model_input_sha256"],
                }
            )
            rows.append(row)
        return payloads, rows

    @staticmethod
    def _duplicate_first(rows: list[dict], count: int = 60) -> list[dict]:
        return [copy.deepcopy(rows[0]) for _ in range(count)]

    def _run_with_rows(
        self,
        payloads: list[dict],
        rows: list[dict],
        *,
        expected_error: str | None = None,
    ) -> tuple[mock.Mock, mock.Mock]:
        auth = {"authorization_commit": "a", "readiness_implementation_commit": "r"}
        state = {"state": "AUTHORIZED", **auth, "history": []}
        config = copy.deepcopy(self.config)
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(execution, "verify_execution_authorization", return_value=auth), \
                mock.patch.object(execution, "load_execution_config", return_value=config), \
                mock.patch.object(execution, "freeze_or_verify_runtime_environment", return_value={"path": CONFIG_PATH}), \
                mock.patch.object(execution, "_load_or_initialize_state", return_value=state), \
                mock.patch.object(execution, "validate_state_history"), \
                mock.patch.object(execution, "build_runtime_payloads", return_value=payloads), \
                mock.patch.object(execution, "verify_raw_environment_binding"), \
                mock.patch.object(execution, "_write_jsonl") as writer, \
                mock.patch.object(execution, "_transition_state") as transition:
            config["evaluation_outputs"]["primary"]["V0_raw"] = str(Path(directory) / "V0.jsonl")
            if expected_error is None:
                execution.run_critical(
                    ROOT, CONFIG_PATH, "primary", "V0", executor=lambda *_: rows
                )
            else:
                with self.assertRaisesRegex(
                    execution.CriticalV2ExecutionError, expected_error
                ):
                    execution.run_critical(
                        ROOT, CONFIG_PATH, "primary", "V0", executor=lambda *_: rows
                    )
                writer.assert_not_called()
                transition.assert_not_called()
        return writer, transition

    def test_f3_j_sixty_duplicate_valid_queries_rejected_before_persistence(self) -> None:
        payloads, valid_rows = self._batch()
        self._run_with_rows(
            payloads,
            self._duplicate_first(valid_rows),
            expected_error="RAW_BATCH_QUERY_UNIQUENESS_MISMATCH",
        )

    def test_f3_k_fifty_nine_unique_plus_one_duplicate_rejected_before_persistence(self) -> None:
        payloads, rows = self._batch()
        rows[-1] = copy.deepcopy(rows[0])
        self._run_with_rows(
            payloads,
            rows,
            expected_error="RAW_BATCH_QUERY_UNIQUENESS_MISMATCH",
        )

    def test_f3_l_exact_sixty_unique_membership_passes(self) -> None:
        payloads, rows = self._batch()
        writer, transition = self._run_with_rows(payloads, rows)
        writer.assert_called_once()
        transition.assert_called_once()

    def test_f3_m_duplicate_tamper_rejected_before_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            helper = revision10.CriticalV2ExecutionRevision10Tests()
            helper.config = self.config
            config, payloads = helper._raw_file_fixture(root, with_manifest=False)
            path = root / config["evaluation_outputs"]["primary"]["V0_raw"]
            rows = execution._read_jsonl(path)
            rows[-1] = copy.deepcopy(rows[0])
            execution._write_jsonl(path, rows)
            state = {"state": "PRIMARY_V2_COMPLETE", "history": []}
            with mock.patch.object(execution, "_require_authorized_state", return_value=(config, {}, state)), \
                    mock.patch.object(execution, "build_runtime_payloads", return_value=payloads), \
                    mock.patch.object(execution, "verify_raw_environment_binding"), \
                    mock.patch.object(execution, "_transition_state") as transition:
                with self.assertRaisesRegex(
                    execution.CriticalV2ExecutionError, "RAW_BATCH_QUERY_UNIQUENESS_MISMATCH"
                ):
                    execution.freeze_raw_run(root, CONFIG_PATH, "primary")
            self.assertFalse(
                (root / config["evaluation_outputs"]["primary"]["raw_manifest"]).exists()
            )
            transition.assert_not_called()

    def test_f3_n_duplicate_tamper_rejected_before_gold_load(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            helper = revision10.CriticalV2ExecutionRevision10Tests()
            helper.config = self.config
            config, payloads = helper._raw_file_fixture(root, with_manifest=True)
            targets = config["evaluation_outputs"]["primary"]
            path = root / targets["V0_raw"]
            rows = execution._read_jsonl(path)
            rows[-1] = copy.deepcopy(rows[0])
            execution._write_jsonl(path, rows)
            manifest = execution._read_json(root / targets["raw_manifest"])
            manifest["variant_sha256"]["V0"] = execution.sha256_file(path)
            execution._write_json(root / targets["raw_manifest"], manifest)
            with mock.patch.object(execution, "load_execution_config", return_value=config), \
                    mock.patch.object(execution, "build_runtime_payloads", return_value=payloads), \
                    mock.patch.object(execution, "verify_raw_environment_binding"):
                with self.assertRaisesRegex(
                    execution.CriticalV2ExecutionError, "RAW_BATCH_QUERY_UNIQUENESS_MISMATCH"
                ):
                    execution.assert_evaluator_load_allowed(root, CONFIG_PATH, "primary")


if __name__ == "__main__":
    unittest.main()
