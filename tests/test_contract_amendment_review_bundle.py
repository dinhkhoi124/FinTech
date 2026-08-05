"""Tests for an extracted Option A contract-amendment review bundle."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / "scripts/evaluation/verify_contract_amendment_review_bundle.py"
SPEC = importlib.util.spec_from_file_location("contract_amendment_bundle_verifier", VERIFIER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load standalone contract-amendment bundle verifier")
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


@unittest.skipUnless((ROOT / "bundle_inventory.json").is_file(), "extracted bundle only")
class ContractAmendmentReviewBundleTests(unittest.TestCase):
    def test_inventory(self) -> None:
        self.assertGreater(VERIFIER.verify_inventory(ROOT), 0)

    def test_contract(self) -> None:
        VERIFIER.verify_contract(ROOT)

    def test_metrics_and_checklist(self) -> None:
        VERIFIER.verify_metrics_and_checklist(ROOT)

    def test_decision_bundle(self) -> None:
        VERIFIER.verify_decision_bundle(ROOT)

    def test_preservation(self) -> None:
        self.assertEqual(VERIFIER.verify_preservation(ROOT), {"revision_2": 17, "revision_3": 18, "revision_4": 19, "historical": 18})


if __name__ == "__main__":
    unittest.main()
