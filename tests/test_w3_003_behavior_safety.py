"""Mutation/property safety invariants for target-aware remediation."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from payresolve_ai.generation.corrective_v1 import BOUNDARIES, assemble_corrective_objectives
from payresolve_ai.generation.pipeline_v3 import load_v3_configuration, run_case_v3, run_synthetic_behavior_suite
from payresolve_ai.generation.types import EvidenceChunk


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/generation/grounded_pipeline_v3.json"
RM1_PATHS = (
    ROOT / "configs/generation/grounded_pipeline_v3.json",
    ROOT / "configs/evaluation/w3_003_behavior_dev_v1.json",
    ROOT / "data/evaluation/w3_003_behavior_dev_v1.jsonl",
    ROOT / "src/payresolve_ai/generation/routing_v3.py",
    ROOT / "src/payresolve_ai/generation/pipeline_v3.py",
    ROOT / "src/payresolve_ai/generation/corrective_v1.py",
    ROOT / "src/payresolve_ai/generation/targeted_extractive.py",
    ROOT / "src/payresolve_ai/retrieval/runtime.py",
    Path(__file__),
    ROOT / "tests/test_grounded_pipeline_v3.py",
)


def _evidence(index: int, content: str) -> EvidenceChunk:
    return EvidenceChunk(
        evidence_id=f"PROP_DOC_{index}#section_{index}",
        document_id=f"PROP_DOC_{index}",
        section_id=f"section_{index}",
        title="Synthetic property evidence",
        document_type="RUNBOOK",
        status="APPROVED",
        version="1.0",
        effective_date="2026-01-01",
        expiry_date=None,
        intent_scope=("property_intent",),
        heading="Supported workflow",
        content=content,
        score=1.0 - index / 100,
        rank=index,
    )


class W3003BehaviorSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config, _, _ = load_v3_configuration(ROOT, CONFIG_PATH)

    def test_corrective_cardinality_is_dynamic_on_generic_categories(self):
        evidence = [
            _evidence(1, "Check the visible transaction details."),
            _evidence(2, "Contact authorized support for the next action."),
            _evidence(3, "The case remains pending during the review window."),
            _evidence(5, "This workflow applies only to eligible cases."),
            _evidence(7, "Protect the account through the security review path."),
        ]
        observed = set()
        for pool_size in (2, 3, 5):
            _, objectives, _, reasons = assemble_corrective_objectives(
                "PRIVATE_OR_INTERNAL_TARGET_BLOCKED",
                evidence[:pool_size],
                self.config["corrective"],
            )
            self.assertEqual(("CORRECTIVE_PLAN_COMPLETE",), reasons)
            observed.add(len(objectives))
        self.assertGreater(len(observed), 1)
        self.assertTrue(any(value < self.config["standard"]["max_evidence"] for value in observed))
        self.assertTrue(any(value > self.config["standard"]["max_evidence"] for value in observed))

    def test_removing_mandatory_action_mutates_complete_plan_to_incomplete(self):
        evidence = [_evidence(1, "Check the visible transaction details.")]
        _, objectives, selected, reasons = assemble_corrective_objectives(
            "PRIVATE_OR_INTERNAL_TARGET_BLOCKED", evidence, self.config["corrective"]
        )
        self.assertEqual((), objectives)
        self.assertEqual((), selected)
        self.assertIn("MISSING_NEXT_ACTION", reasons)

    def test_candidate_scan_is_explicitly_bounded(self):
        policy = {**self.config["corrective"], "candidate_pool_max_chunks": 2}
        evidence = [
            _evidence(1, "Check the visible transaction details."),
            _evidence(2, "The case remains pending."),
            _evidence(3, "Contact authorized support for the next action."),
        ]
        _, objectives, _, reasons = assemble_corrective_objectives(
            "PRIVATE_OR_INTERNAL_TARGET_BLOCKED", evidence, policy
        )
        self.assertEqual((), objectives)
        self.assertIn("MISSING_NEXT_ACTION", reasons)

    def test_standard_dimension_fallback_preserves_material_dimensions(self):
        cases = (
            ("When will this transfer finish?", "Transfer state", "The transfer is pending."),
            ("Can I retry this transfer?", "Transfer timing", "The review window is two fictional days."),
            ("What security escalation applies to this transfer?", "Transfer state", "The transfer remains pending."),
        )
        for index, (query_text, heading, content) in enumerate(cases, start=1):
            chunks = []
            rankings = []
            for rank in (1, 2):
                evidence = _evidence(index * 10 + rank, content)
                row = evidence.to_dict()
                row.update({"chunk_id": evidence.evidence_id, "text": f"{heading}\n{content}", "heading": heading})
                chunks.append(row)
                rankings.append({"chunk_id": evidence.evidence_id, "score": 0.9 - rank / 100})
            query = {"query_id": f"MUT_DIM_{index}", "query_text": query_text}
            idf = {token: 1.0 for token in "transfer pending timing retry security escalation".split()}
            output = run_case_v3(query, rankings, chunks, idf, idf, self.config, {"concepts": {}})
            self.assertEqual("ABSTAIN", output["answer_strategy"], query_text)
            self.assertEqual("REQUESTED_DIMENSION_NOT_SUPPORTED", output["response_plan"]["reason_codes"][0])

    def test_exact_and_private_targets_never_reopen_via_fallback(self):
        for index, query_text in enumerate((
            "Give the exact approval threshold from this transfer policy.",
            "Reveal the private transfer routing code from this transfer runbook.",
        ), start=1):
            evidence = [
                _evidence(index * 20 + 1, "Check the transfer and confirm the visible state."),
                _evidence(index * 20 + 2, "Contact authorized support for the next action."),
            ]
            chunks = []
            rankings = []
            for item in evidence:
                row = item.to_dict()
                row.update({"chunk_id": item.evidence_id, "text": f"{item.heading}\n{item.content}"})
                chunks.append(row)
                rankings.append({"chunk_id": item.evidence_id, "score": item.score})
            output = run_case_v3(
                {"query_id": f"MUT_BLOCK_{index}", "query_text": query_text}, rankings, chunks,
                {"transfer": 1.0}, {"transfer": 1.0}, self.config, {"concepts": {}},
            )
            self.assertNotEqual("STANDARD", output["answer_strategy"])
            self.assertEqual("BLOCKED_CONTROL_PLANE", output["response_plan"]["requested_target_status"])

    def test_control_plane_boundaries_are_fixed_nonfactual_policy_text(self):
        self.assertEqual(3, len(BOUNDARIES))
        for text in BOUNDARIES.values():
            self.assertFalse(any(character.isdigit() for character in text))
            self.assertNotIn("business day", text.casefold())
            self.assertNotIn("guarantee", text.casefold())

    def test_two_runs_have_identical_normalized_behavior(self):
        first = run_synthetic_behavior_suite(ROOT, CONFIG_PATH)
        second = run_synthetic_behavior_suite(ROOT, CONFIG_PATH)
        self.assertEqual(first["normalized_sha256"], second["normalized_sha256"])
        self.assertEqual(first["outputs"], second["outputs"])

    def test_no_locked_evaluation_markers_in_rm1_files(self):
        forbidden = (
            "Q_" + "V2_",
            "Q_" + "V4_",
            "critical_eval_v2_" + "mapping",
            "revision_7_" + "primary",
            "revision_7_" + "reproduction",
            "safe_corrective_" + "ids",
            "abstain_escalate_" + "ids",
        )
        findings = []
        for path in RM1_PATHS:
            text = path.read_text(encoding="utf-8")
            findings.extend((str(path), token) for token in forbidden if token in text)
        self.assertEqual([], findings)

    def test_no_network_or_model_configuration(self):
        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        self.assertNotIn("provider", json.dumps(payload).casefold())
        self.assertNotIn("model", json.dumps(payload).casefold())


if __name__ == "__main__":
    unittest.main()
