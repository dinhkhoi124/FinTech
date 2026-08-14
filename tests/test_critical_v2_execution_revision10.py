from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from payresolve_ai.evaluation import critical_v2_execution as execution


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/evaluation/critical_eval_v2_execution.json"


class CriticalV2ExecutionRevision10Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = execution.load_execution_config(CONFIG_PATH)

    @staticmethod
    def _raw(*, answer: bool = False, text: str = "Supported sentence.") -> dict:
        row = {
            "execution_id": "critical_eval_v2_revision7_primary_V0",
            "run_label": "primary", "variant_id": "V0", "query_id": "q",
            "model_input_sha256": "0" * 64,
            "classifier_prediction": {"predicted_intent": "x", "top_k": []},
            "retrieval_strategy": "R0", "retrieved_evidence": [],
            "gate_inputs": {}, "gate_decision": {},
            "response": "I do not have enough approved evidence to answer this safely. Please escalate this case to an authorized support or policy owner.",
            "observed_response_type": "ABSTAIN_ESCALATE",
            "observed_answer_subtype_candidate": None,
            "cited_evidence_ids": [], "citation_records": [], "claim_records": [],
            "eligible_evidence_records": [], "latency_ms": {},
            "determinism": {"execution_contract_sha256": execution.sha256_file(CONFIG_PATH)},
            "execution_environment_reference": "environment.json",
            "execution_environment_sha256": "0" * 64, "system_error": None,
        }
        if answer:
            evidence = {
                "evidence_id": "E#s", "document_id": "E", "section_id": "s",
                "title": "Title", "document_type": "FAQ", "status": "APPROVED",
                "version": "1", "effective_date": "2020-01-01", "expiry_date": None,
                "intent_scope": ["x"], "heading": "Heading", "content": text,
                "score": 0.9, "rank": 1,
            }
            row.update({
                "response": f"{text} [C1]", "observed_response_type": "ANSWER",
                "retrieved_evidence": [{"evidence_id": "E#s", "status": "APPROVED"}],
                "eligible_evidence_records": [evidence], "cited_evidence_ids": ["E#s"],
                "citation_records": [{
                    "citation_id": "C1", "evidence_id": "E#s", "document_id": "E",
                    "section_id": "s", "title": "Title", "document_type": "FAQ",
                    "status": "APPROVED", "version": "1",
                }],
                "claim_records": [{
                    "claim_id": "CL1", "text": text, "evidence_ids": ["E#s"],
                    "support_quotes": [text], "citation_ids": ["C1"],
                }],
            })
        return row

    @staticmethod
    def _obligation(text: str, subtype: str) -> dict:
        return {"expected_answer_subtype": subtype, "required_obligations": [{
            "obligation_id": "O1", "description": "fixture",
            "acceptable_evidence_ids": ["E#s"],
            "fulfillment_alternatives": [{"alternative_id": "ALT_001", "requirements": [{
                "requirement_id": "ALT_001_REQ_01", "evidence_id": "E#s",
                "exact_claim_text": text,
                "normalized_claim_text": execution._normalise_claim_text(text),
            }]}],
        }]}

    @staticmethod
    def _safety_rule() -> dict:
        return {
            "forbidden_or_unsupported_target": "private token",
            "target_mention_patterns": ["private token"],
            "target_class": "DISCLOSURE_CAPABLE_TARGET",
            "disclosure_target_patterns": ["private token"],
            "safe_refusal_patterns": ["cannot provide"],
            "refusal_boundary_markers": ["cannot provide"],
            "clarification_or_escalation_markers": ["contact support"],
            "affirmative_compliance_patterns": ["use the private token"],
            "forbidden_disclosure_patterns": ["private token is"],
            "unsafe_action_patterns": [],
        }

    def test_f1_a_runtime_answer_remains_subtype_null(self) -> None:
        row = self._raw(answer=True)
        execution.validate_raw_output(row)
        self.assertIsNone(row["observed_answer_subtype_candidate"])

    def test_f1_b_runtime_abstain_remains_subtype_null(self) -> None:
        row = self._raw()
        execution.validate_raw_output(row)
        self.assertIsNone(row["observed_answer_subtype_candidate"])

    def test_f1_c_premature_standard_is_rejected(self) -> None:
        row = self._raw(); row["observed_answer_subtype_candidate"] = "STANDARD"
        with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "RAW_PRE_FREEZE_SUBTYPE_FORBIDDEN"):
            execution.validate_raw_output(row)

    def test_f1_d_premature_safe_corrective_is_rejected(self) -> None:
        row = self._raw(); row["observed_answer_subtype_candidate"] = "SAFE_CORRECTIVE"
        with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "RAW_PRE_FREEZE_SUBTYPE_FORBIDDEN"):
            execution.validate_raw_output(row)

    def test_f1_e_gold_loader_calls_zero_before_freeze(self) -> None:
        calls = {"gold_loader_calls": 0}
        def loader(_path: Path):
            calls["gold_loader_calls"] += 1
            return []
        state = {"state": "PRIMARY_FROZEN"}
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(self.config)
            config["evaluation_outputs"]["primary"]["raw_manifest"] = str(Path(directory) / "absent.json")
            with mock.patch.object(execution, "_require_authorized_state", return_value=(config, {}, state)), \
                    mock.patch.object(execution, "assert_evaluator_load_allowed", side_effect=execution.CriticalV2ExecutionError("evaluator cannot load before raw freeze")), \
                    mock.patch.object(execution, "_read_jsonl", side_effect=loader):
                with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "cannot load before"):
                    execution.evaluate_frozen_run(ROOT, CONFIG_PATH, "primary")
        self.assertEqual(calls["gold_loader_calls"], 0)

    def test_f1_f_post_freeze_standard_is_evaluator_derived(self) -> None:
        text = "Supported sentence."
        result = execution.evaluate_observed_semantics(
            self._raw(answer=True, text=text),
            {"final_expected_response_type": "ANSWER", "final_expected_answer_subtype": "STANDARD", "complete_requested_answer_covers": [["E#s"]]},
            None, "2026-07-28", self._obligation(text, "STANDARD"),
        )
        self.assertEqual(result["observed_answer_subtype"], "STANDARD")

    def test_f1_g_post_freeze_safe_corrective_is_evaluator_derived(self) -> None:
        text = "I cannot provide private token. Supported sentence."
        result = execution.evaluate_observed_semantics(
            self._raw(answer=True, text=text),
            {"final_expected_response_type": "ANSWER", "final_expected_answer_subtype": "SAFE_CORRECTIVE", "complete_corrective_answer_covers": [["E#s"]]},
            self._safety_rule(), "2026-07-28", self._obligation(text, "SAFE_CORRECTIVE"),
        )
        self.assertEqual(result["observed_answer_subtype"], "SAFE_CORRECTIVE")

    def test_f1_h_post_freeze_true_abstain_subtype_is_null(self) -> None:
        row = self._raw(); row["response"] = "Please contact support."
        result = execution.evaluate_observed_semantics(
            row,
            {"final_expected_response_type": "ABSTAIN_ESCALATE", "final_expected_answer_subtype": None},
            self._safety_rule(), "2026-07-28",
        )
        self.assertIsNone(result["observed_answer_subtype"])

    def test_f2_registry_is_exact_and_contains_no_invented_literals(self) -> None:
        registry = execution.build_disclosure_literal_registry(
            execution.build_safety_evaluator_rules(ROOT, self.config)
        )
        self.assertEqual(registry["disclosure_capable_query_count"], 8)
        self.assertEqual(registry["canonical_target_count"], 11)
        self.assertEqual(registry["targets_with_enumerated_literal_values"], 0)
        self.assertEqual(registry["targets_without_enumerated_literal_values"], 11)
        for row in registry["rows"]:
            with self.subTest(query_id=row["query_id"], target=row["canonical_target"]):
                result = execution.evaluate_narrow_literal_disclosure_guard(
                    f"The registered target is {row['canonical_target']}.", [], [], [row]
                )
                self.assertEqual(row["literal_status"], "NO_ENUMERATED_LITERAL_VALUE")
                self.assertEqual(row["enumerated_prohibited_literals"], [])
                self.assertFalse(result["unsafe"])
                self.assertEqual(result["enumerated_literal_count"], 0)

    def test_f2_parser_or_guard_truth_table_fails_closed(self) -> None:
        expected = {(False, False): False, (False, True): True, (True, False): True, (True, True): True}
        for inputs, verdict in expected.items():
            with self.subTest(inputs=inputs):
                self.assertIs(execution.combine_prohibited_disclosure_decisions(*inputs), verdict)

    def _validate_binding(self, row: dict) -> None:
        with mock.patch.object(execution, "verify_raw_environment_binding"):
            execution.validate_raw_execution_binding(
                ROOT, CONFIG_PATH, self.config, row,
                run_label="primary", variant_id="V0",
                payload_by_id={"q": {"query_id": "q", "model_input_sha256": "0" * 64}},
            )

    def test_f3_valid_binding_passes(self) -> None:
        self._validate_binding(self._raw())

    def test_f3_stale_revision6_execution_id_is_rejected(self) -> None:
        row = self._raw(); row["execution_id"] = "critical_eval_v2_revision6_primary_V0"
        with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "EXECUTION_ID_MISMATCH"):
            self._validate_binding(row)

    def test_f3_wrong_run_is_rejected(self) -> None:
        row = self._raw(); row["run_label"] = "reproducibility_rerun"
        with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "RUN_LABEL_MISMATCH"):
            self._validate_binding(row)

    def test_f3_wrong_variant_is_rejected(self) -> None:
        row = self._raw(); row["variant_id"] = "V1"
        with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "VARIANT_MISMATCH"):
            self._validate_binding(row)

    def test_f3_wrong_query_membership_is_rejected(self) -> None:
        row = self._raw(); row["query_id"] = "unknown"
        with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "QUERY_MEMBERSHIP_MISMATCH"):
            self._validate_binding(row)

    def test_f3_wrong_model_input_hash_is_rejected(self) -> None:
        row = self._raw(); row["model_input_sha256"] = "f" * 64
        with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "MODEL_INPUT_SHA_MISMATCH"):
            self._validate_binding(row)

    def test_f3_wrong_active_config_hash_is_rejected(self) -> None:
        row = self._raw(); row["determinism"]["execution_contract_sha256"] = "f" * 64
        with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "ACTIVE_CONFIG_SHA_MISMATCH"):
            self._validate_binding(row)

    def test_f3_pre_persistence_tamper_blocks_write_and_state_advance(self) -> None:
        rows = []
        payloads = []
        for index in range(60):
            query_id = f"q{index:02d}"
            model_input_sha256 = f"{index:064x}"
            row = self._raw()
            row.update({"query_id": query_id, "model_input_sha256": model_input_sha256})
            rows.append(row)
            payloads.append({
                "query_id": query_id,
                "model_input_text": f"text {index}",
                "model_input_sha256": model_input_sha256,
            })
        rows[0]["execution_id"] = "critical_eval_v2_revision6_primary_V0"
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
            with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "EXECUTION_ID_MISMATCH"):
                execution.run_critical(ROOT, CONFIG_PATH, "primary", "V0", executor=lambda *_: rows)
        writer.assert_not_called(); transition.assert_not_called()

    def _raw_file_fixture(self, root: Path, *, with_manifest: bool) -> tuple[dict, list[dict]]:
        config = copy.deepcopy(self.config)
        config["runtime_environment"]["manifest"] = "environment.json"
        environment = root / "environment.json"
        environment.write_text("{}\n", encoding="utf-8")
        environment_sha = execution.sha256_file(environment)
        targets = config["evaluation_outputs"]["primary"]
        for variant in execution.VARIANT_IDS:
            targets[f"{variant}_raw"] = f"{variant}.jsonl"
        targets["raw_manifest"] = "manifest.json"
        payloads = [
            {"query_id": f"q{index:02d}", "model_input_text": f"text {index}", "model_input_sha256": f"{index:064x}"}
            for index in range(60)
        ]
        hashes = {}
        for variant in execution.VARIANT_IDS:
            rows = []
            for payload in payloads:
                row = self._raw()
                row.update({
                    "execution_id": execution.runtime_execution_id(config, "primary", variant),
                    "variant_id": variant, "query_id": payload["query_id"],
                    "model_input_sha256": payload["model_input_sha256"],
                    "execution_environment_reference": "environment.json",
                    "execution_environment_sha256": environment_sha,
                })
                rows.append(row)
            path = root / targets[f"{variant}_raw"]
            execution._write_jsonl(path, rows)
            hashes[variant] = execution.sha256_file(path)
        if with_manifest:
            execution._write_json(root / targets["raw_manifest"], {
                "raw_outputs_frozen": True, "variant_sha256": hashes,
            })
        return config, payloads

    def test_f3_freeze_tamper_blocks_manifest_and_state_advance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, payloads = self._raw_file_fixture(root, with_manifest=False)
            path = root / config["evaluation_outputs"]["primary"]["V0_raw"]
            rows = execution._read_jsonl(path)
            rows[0]["determinism"]["execution_contract_sha256"] = "f" * 64
            execution._write_jsonl(path, rows)
            state = {"state": "PRIMARY_V2_COMPLETE", "history": []}
            with mock.patch.object(execution, "_require_authorized_state", return_value=(config, {}, state)), \
                    mock.patch.object(execution, "build_runtime_payloads", return_value=payloads), \
                    mock.patch.object(execution, "verify_raw_environment_binding"), \
                    mock.patch.object(execution, "_transition_state") as transition:
                with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "ACTIVE_CONFIG_SHA_MISMATCH"):
                    execution.freeze_raw_run(root, CONFIG_PATH, "primary")
            self.assertFalse((root / config["evaluation_outputs"]["primary"]["raw_manifest"]).exists())
            transition.assert_not_called()

    def test_f3_pre_gold_tamper_is_rejected_before_mapping_load(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, payloads = self._raw_file_fixture(root, with_manifest=True)
            targets = config["evaluation_outputs"]["primary"]
            path = root / targets["V0_raw"]
            rows = execution._read_jsonl(path)
            rows[0]["determinism"]["execution_contract_sha256"] = "f" * 64
            execution._write_jsonl(path, rows)
            manifest = execution._read_json(root / targets["raw_manifest"])
            manifest["variant_sha256"]["V0"] = execution.sha256_file(path)
            execution._write_json(root / targets["raw_manifest"], manifest)
            with mock.patch.object(execution, "load_execution_config", return_value=config), \
                    mock.patch.object(execution, "build_runtime_payloads", return_value=payloads), \
                    mock.patch.object(execution, "verify_raw_environment_binding"):
                with self.assertRaisesRegex(execution.CriticalV2ExecutionError, "ACTIVE_CONFIG_SHA_MISMATCH"):
                    execution.assert_evaluator_load_allowed(root, CONFIG_PATH, "primary")


if __name__ == "__main__":
    unittest.main()
