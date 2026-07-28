from __future__ import annotations

import json
import sys
import tempfile
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from payresolve_ai.kb.validation import (  # noqa: E402
    KBValidationError,
    canonical_dataset_sha256,
    is_document_eligible,
    load_config,
    load_documents,
    validate_kb,
)


class KBValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config(REPO_ROOT, Path("configs/kb/kb_v1.json"))
        cls.documents = load_documents(REPO_ROOT / cls.config["documents_path"])
        cls.hard_negatives = json.loads(
            (REPO_ROOT / cls.config["hard_negative_matrix_path"]).read_text(encoding="utf-8")
        )
        cls.document_plan = json.loads(
            (REPO_ROOT / cls.config["document_plan_path"]).read_text(encoding="utf-8")
        )
        cls.categories = json.loads(
            (REPO_ROOT / cls.config["canonical_intents_source"]).read_text(encoding="utf-8")
        )
        cls.as_of = date.fromisoformat(cls.config["evaluation_as_of_date"])

    def report_for(
        self,
        documents: list[dict] | None = None,
        *,
        hard_negatives: dict | None = None,
        document_plan: dict | None = None,
    ) -> dict:
        return validate_kb(
            deepcopy(self.documents if documents is None else documents),
            self.config,
            deepcopy(self.hard_negatives if hard_negatives is None else hard_negatives),
            canonical_categories=self.categories,
            document_plan=deepcopy(self.document_plan if document_plan is None else document_plan),
        )

    @staticmethod
    def codes(report: dict) -> set[str]:
        return {error["code"] for error in report["errors"]}

    def document(self, document_id: str) -> dict:
        return next(document for document in self.documents if document["document_id"] == document_id)

    def test_valid_approved_current_document_is_eligible(self) -> None:
        self.assertTrue(is_document_eligible(self.document("POL_TRANSFER_PENDING_002"), self.as_of))

    def test_draft_is_ineligible(self) -> None:
        self.assertFalse(is_document_eligible(self.document("POL_TRANSFER_PENDING_003"), self.as_of))

    def test_expired_is_ineligible(self) -> None:
        self.assertFalse(is_document_eligible(self.document("POL_TRANSFER_PENDING_001"), self.as_of))

    def test_future_effective_approved_is_ineligible(self) -> None:
        document = deepcopy(self.document("POL_TRANSFER_PENDING_002"))
        document["effective_date"] = "2027-01-01"
        self.assertFalse(is_document_eligible(document, self.as_of))

    def test_duplicate_document_id_fails(self) -> None:
        documents = deepcopy(self.documents)
        documents.append(deepcopy(documents[-1]))
        report = self.report_for(documents)
        self.assertIn("duplicate-document-id", self.codes(report))

    def test_unknown_intent_fails(self) -> None:
        documents = deepcopy(self.documents)
        documents[0]["intent_scope"] = ["unknown_intent"]
        documents[0]["intent_slugs"] = ["unknown_intent"]
        report = self.report_for(documents)
        self.assertIn("unknown-intent", self.codes(report))

    def test_canonical_label_slug_mismatch_fails(self) -> None:
        documents = deepcopy(self.documents)
        target = next(
            document for document in documents if document["document_id"] == "POL_CARD_REVERT_002"
        )
        target["intent_slugs"] = ["reverted_card_payment?"]
        report = self.report_for(documents)
        self.assertIn("intent-slug-mismatch", self.codes(report))
        self.assertIn("intent-slug-format", self.codes(report))

    def test_two_active_approved_versions_in_one_family_fail(self) -> None:
        documents = deepcopy(self.documents)
        expired = next(
            document for document in documents if document["document_id"] == "POL_TRANSFER_PENDING_001"
        )
        expired["status"] = "APPROVED"
        expired["expiry_date"] = None
        report = self.report_for(documents)
        self.assertIn("multiple-active-approved", self.codes(report))

    def test_cyclic_supersession_fails(self) -> None:
        documents = deepcopy(self.documents)
        oldest = next(
            document for document in documents if document["document_id"] == "POL_TRANSFER_PENDING_001"
        )
        oldest["supersedes_document_id"] = "POL_TRANSFER_PENDING_003"
        report = self.report_for(documents)
        self.assertIn("supersession-cycle", self.codes(report))

    def test_invalid_date_order_fails(self) -> None:
        documents = deepcopy(self.documents)
        expired = next(
            document for document in documents if document["document_id"] == "POL_CARD_REVERT_001"
        )
        expired["expiry_date"] = "2024-12-31"
        report = self.report_for(documents)
        self.assertIn("date-order", self.codes(report))

    def test_missing_required_coverage_fails(self) -> None:
        documents = [
            deepcopy(document)
            for document in self.documents
            if not (
                document["status"] == "APPROVED"
                and "declined_cash_withdrawal" in document["intent_scope"]
            )
        ]
        report = self.report_for(documents)
        self.assertIn("intent-coverage", self.codes(report))

    def test_non_string_title_fails(self) -> None:
        documents = deepcopy(self.documents)
        documents[0]["title"] = 42
        self.assertIn("title-type", self.codes(self.report_for(documents)))

    def test_short_or_empty_approved_by_fails(self) -> None:
        for value in ("", "x"):
            with self.subTest(value=value):
                documents = deepcopy(self.documents)
                documents[0]["approved_by"] = value
                self.assertIn("approved-by-contract", self.codes(self.report_for(documents)))

    def test_invalid_intent_family_fails(self) -> None:
        documents = deepcopy(self.documents)
        documents[0]["intent_family"] = "merchant"
        self.assertIn("intent-family-enum", self.codes(self.report_for(documents)))

    def test_invalid_product_fails(self) -> None:
        documents = deepcopy(self.documents)
        documents[0]["product"] = "wallet"
        self.assertIn("product-enum", self.codes(self.report_for(documents)))

    def test_intent_family_product_mismatch_fails(self) -> None:
        documents = deepcopy(self.documents)
        documents[0]["intent_family"] = "transfer"
        documents[0]["product"] = "bank_transfer"
        self.assertIn("intent-family-product-mismatch", self.codes(self.report_for(documents)))

    def test_invalid_supersedes_type_fails(self) -> None:
        documents = deepcopy(self.documents)
        target = next(document for document in documents if document["document_id"] == "POL_TRANSFER_PENDING_002")
        target["supersedes_document_id"] = 123
        self.assertIn("supersedes-type", self.codes(self.report_for(documents)))

    def test_disconnected_complete_version_family_fails(self) -> None:
        documents = deepcopy(self.documents)
        target = next(document for document in documents if document["document_id"] == "POL_TRANSFER_PENDING_002")
        target["supersedes_document_id"] = None
        report = self.report_for(documents)
        self.assertIn("version-chain-disconnected", self.codes(report))
        self.assertNotIn(
            "POL_TRANSFER_PENDING",
            report["first_28_quality_gate"]["complete_version_families"],
        )

    def test_non_monotonic_version_chain_fails(self) -> None:
        documents = deepcopy(self.documents)
        target = next(document for document in documents if document["document_id"] == "POL_TRANSFER_PENDING_002")
        target["version"] = "0.5"
        self.assertIn("version-chain-nonmonotonic-version", self.codes(self.report_for(documents)))

    def test_wrong_lifecycle_status_fails(self) -> None:
        documents = deepcopy(self.documents)
        target = next(document for document in documents if document["document_id"] == "POL_TRANSFER_PENDING_002")
        target["status"] = "DRAFT"
        self.assertIn("version-chain-status", self.codes(self.report_for(documents)))

    def test_version_plan_reference_mismatch_fails(self) -> None:
        plan = deepcopy(self.document_plan)
        plan["version_families"][0]["approved"] = "POL_MISSING_999"
        self.assertIn("version-plan-reference", self.codes(self.report_for(document_plan=plan)))

    def test_hard_negative_missing_required_field_fails(self) -> None:
        matrix = deepcopy(self.hard_negatives)
        relationship = matrix["relationships"][1]
        relationship_id = relationship["relationship_id"]
        del relationship["risk_if_confused"]
        report = self.report_for(hard_negatives=matrix)
        self.assertIn("hard-negative-required-field", self.codes(report))
        self.assertNotIn(
            relationship_id,
            report["first_28_quality_gate"]["fully_resolved_hard_negative_relationship_ids"],
        )

    def test_hard_negative_same_source_and_confusing_intent_fails(self) -> None:
        matrix = deepcopy(self.hard_negatives)
        matrix["relationships"][0]["confusing_intent"] = matrix["relationships"][0]["source_intent"]
        self.assertIn("hard-negative-same-intent", self.codes(self.report_for(hard_negatives=matrix)))

    def test_hard_negative_document_sets_must_be_disjoint(self) -> None:
        matrix = deepcopy(self.hard_negatives)
        matrix["relationships"][0]["hard_negative_document_ids"].append(
            matrix["relationships"][0]["positive_document_ids"][0]
        )
        self.assertIn("hard-negative-document-overlap", self.codes(self.report_for(hard_negatives=matrix)))

    def test_hard_negative_empty_shared_vocabulary_fails(self) -> None:
        matrix = deepcopy(self.hard_negatives)
        matrix["relationships"][0]["shared_vocabulary"] = []
        self.assertIn("hard-negative-shared-vocabulary", self.codes(self.report_for(hard_negatives=matrix)))

    def test_valid_full_kb_passes(self) -> None:
        report = validate_kb(
            deepcopy(self.documents),
            self.config,
            self.hard_negatives,
            canonical_categories=self.categories,
            document_plan=self.document_plan,
        )
        self.assertEqual("PASS", report["validation_result"], report["errors"])
        self.assertEqual(36, report["summary"]["document_count"])
        self.assertEqual(26, report["summary"]["eligible_document_count"])
        self.assertEqual("PASS", report["first_28_quality_gate"]["result"])
        self.assertEqual(20, report["first_28_quality_gate"]["eligible_approved_count"])

    def test_deterministic_dataset_hash_is_stable(self) -> None:
        expected = canonical_dataset_sha256(self.documents)
        self.assertEqual(expected, canonical_dataset_sha256(list(reversed(self.documents))))
        changed = deepcopy(self.documents)
        changed[0]["title"] += " changed"
        self.assertNotEqual(expected, canonical_dataset_sha256(changed))

    def test_question_mark_intent_round_trips_with_safe_slug(self) -> None:
        documents = [
            document
            for document in self.documents
            if "reverted_card_payment?" in document["intent_scope"]
        ]
        self.assertGreaterEqual(len(documents), 2)
        for document in documents:
            self.assertEqual(["reverted_card_payment?"], document["intent_scope"])
            self.assertEqual(["reverted_card_payment"], document["intent_slugs"])
            self.assertNotIn("?", document["intent_slugs"][0])

    def test_jsonl_is_strict_utf8_without_bom(self) -> None:
        payload = (REPO_ROOT / self.config["documents_path"]).read_bytes()
        self.assertFalse(payload.startswith(b"\xef\xbb\xbf"))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bom.jsonl"
            path.write_bytes(b"\xef\xbb\xbf" + payload)
            with self.assertRaisesRegex(KBValidationError, "Unexpected UTF-8 BOM"):
                load_documents(path)


if __name__ == "__main__":
    unittest.main()
