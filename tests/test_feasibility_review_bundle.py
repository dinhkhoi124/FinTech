"""Tests for an extracted W3-002-CR1 contract-feasibility bundle."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / "scripts/evaluation/verify_feasibility_review_bundle.py"
SPEC = importlib.util.spec_from_file_location("feasibility_bundle_verifier", VERIFIER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load standalone feasibility bundle verifier")
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


@unittest.skipUnless(
    (ROOT / "bundle_inventory.json").is_file()
    and (ROOT / "review/contract_amendment_safety_challenges.jsonl").is_file(),
    "standalone feasibility-bundle-only tests: extracted bundle fixture root is absent",
)
class FeasibilityReviewBundleTests(unittest.TestCase):
    def test_inventory_is_complete(self) -> None:
        self.assertGreater(VERIFIER.verify_inventory(ROOT), 0)

    def test_exact_safety_challenge_contract(self) -> None:
        cases, cover_ids = VERIFIER.verify_cases(ROOT)
        self.assertEqual(len(cases), 20)
        self.assertEqual(sum(case["response_type"] == "ANSWER" for case in cases), 15)
        self.assertEqual(sum(case["response_type"] == "ABSTAIN_ESCALATE" for case in cases), 5)
        self.assertGreater(len(cover_ids), 0)

    def test_category_and_semantic_findings(self) -> None:
        cases, cover_ids = VERIFIER.verify_cases(ROOT)
        VERIFIER.verify_category_summary(ROOT, cases)
        VERIFIER.verify_findings(ROOT, cover_ids)

    def test_preservation_hashes(self) -> None:
        revision_count, historical_count = VERIFIER.verify_preservation(ROOT)
        self.assertEqual(revision_count, 19)
        self.assertEqual(historical_count, 18)

    def test_lifecycle_remains_unauthorized(self) -> None:
        VERIFIER.verify_lifecycle(ROOT)


if __name__ == "__main__":
    unittest.main()
