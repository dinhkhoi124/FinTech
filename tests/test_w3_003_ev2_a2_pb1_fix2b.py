"""FIX2B final Senior/tiebreak reconciliation regressions."""

from __future__ import annotations

import json
import hashlib
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from scripts.evaluation import week3_ev2_a2 as a2
from scripts.evaluation import week3_ev2_a2_fix2b as fix2b


ROOT = Path(__file__).resolve().parents[1]


def _json(path: Path) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _pass_b() -> list[dict]:
    return a2.read_jsonl(ROOT / a2.PASS_B)


def _pass_c() -> list[dict]:
    return a2.read_jsonl(ROOT / a2.PASS_C)


def _index(rows: list[dict]) -> dict[tuple[str, str], dict]:
    return {(row["case_id"], row["evidence_id"]): row for row in rows}


def _semantic_gold_identities() -> dict[str, str]:
    paths = (
        a2.PASS_A, a2.PASS_B, a2.PASS_C, a2.A2_MANIFEST,
        a2.OBLIGATION_CLASSIFICATION,
    )
    return {path.as_posix(): a2.file_sha256(ROOT / path) for path in paths}


@pytest.fixture(scope="module")
def pkg1_bundle() -> Path:
    before = _semantic_gold_identities()
    result = fix2b.build_bundle(ROOT)
    assert result["passed"] is True
    assert result["status"] == fix2b.STATUS
    assert result["staging_deleted"] is True
    assert result["standalone_replay"]["passed"] is True
    assert _semantic_gold_identities() == before
    return Path(result["path"])


def test_fix2b_exact_package_validates() -> None:
    result = fix2b.validate_fix2b(ROOT)
    assert result["passed"], result["errors"][:20]
    assert result["proof_counts"] == [24, 18, 12, 6]
    assert result["deterministic_derivation"] is True


def test_all_17_senior_pairs_exist_exactly_once() -> None:
    artifact = _json(fix2b.SENIOR_17)
    pairs = [(row["case_id"], row["evidence_id"]) for row in artifact["adjudications"]]
    assert len(pairs) == len(set(pairs)) == 17
    assert set(pairs) == {(row["case_id"], row["evidence_id"]) for row in fix2b.SENIOR_17_SPEC}


def test_a01_six_rows_retain_contextual_target_state_true() -> None:
    rows = [row for row in _pass_b() if row["case_id"] == "EV2-A2-A01"]
    expected_evidence = {
        row["evidence_id"] for row in fix2b.SENIOR_17_SPEC
        if row["case_id"] == "EV2-A2-A01"
    }
    selected = [row for row in rows if row["evidence_id"] in expected_evidence]
    assert len(selected) == 6
    assert all(
        row["support_class"] == "CONTEXTUAL_INSUFFICIENT"
        and row["target_match"] is True and row["state_match"] is True
        and row["obligations_covered"] == []
        for row in selected
    )


def test_a01_never_enters_positive_allowed_support() -> None:
    row = next(item for item in _pass_c() if item["case_id"] == "EV2-A2-A01")
    assert row["allowed_supporting_evidence"] == []
    assert row["acceptable_complete_support_sets"] == []


def test_card_declined_checks_remain_pending_contradictions() -> None:
    index = _index(_pass_b())
    for case_id in ("EV2-A2-C02", "EV2-A2-C14", "EV2-A2-S03", "EV2-A2-S04"):
        assert index[(case_id, "RUN_CARD_DECLINED_001#checks")]["support_class"] == "CONTRADICTION"


def test_cash_pending_faq_remains_declined_contradiction() -> None:
    index = _index(_pass_b())
    for case_id in ("EV2-A2-C04", "EV2-A2-C05", "EV2-A2-S07", "EV2-A2-S08"):
        assert index[(case_id, "FAQ_CASH_PENDING_001#answer")]["support_class"] == "CONTRADICTION"


def test_c06_immediate_trigger_is_explicit_contradiction() -> None:
    row = _index(_pass_b())[("EV2-A2-C06", "ESC_CASH_UNRECOG_001#immediate_trigger")]
    assert row["support_class"] == "CONTRADICTION"
    assert row["target_match"] is True and row["state_match"] is False
    assert row["contradiction_basis_quote"]


def test_c06_prohibited_actions_is_contextual_not_contradiction() -> None:
    row = _index(_pass_b())[("EV2-A2-C06", "POL_CASH_UNRECOG_001#prohibited_actions")]
    assert row["support_class"] == "CONTEXTUAL_INSUFFICIENT"
    assert row["target_match"] is True and row["state_match"] is False
    assert "contradiction_basis_quote" not in row


def test_c06_security_rule_is_explicit_contradiction() -> None:
    row = _index(_pass_b())[("EV2-A2-C06", "POL_CASH_UNRECOG_001#security_rule")]
    assert row["support_class"] == "CONTRADICTION"
    assert row["target_match"] is True and row["state_match"] is False
    assert row["contradiction_basis_quote"]


def test_all_65_nonhard_rows_are_resolved_without_reviewer_three() -> None:
    matrix = fix2b.build_final_65_resolution_matrix(ROOT)
    assert matrix["rows"] == 65 and matrix["unresolved"] == 0
    assert matrix["decision_source_counts"] == {"CURRENT": 40, "BLIND1": 24, "TIEBREAK_UNIQUE": 1}
    source = (ROOT / "scripts/evaluation/week3_ev2_a2_fix2b.py").read_text(encoding="utf-8").lower()
    assert "spawn_agent" not in source
    assert "reviewer_3" not in source


def test_only_authorized_imported_hard_rows_changed() -> None:
    before = _index(a2.read_jsonl(ROOT / fix2b.PRE_FIX2B_PASS_B))
    after = _index(_pass_b())
    imported_changes = {
        pair for pair in before
        if before[pair] != after[pair]
        and before[pair]["review_provenance"] == a2.PB1_IMPORT_PROVENANCE
    }
    assert imported_changes == fix2b.HARD_CHANGES
    for pair in imported_changes:
        assert before[pair]["state_match"] is False
        assert after[pair]["state_match"] is True
        assert before[pair]["support_class"] == after[pair]["support_class"] == "CONTEXTUAL_INSUFFICIENT"
        assert before[pair]["obligations_covered"] == after[pair]["obligations_covered"] == []


def test_correction_ledger_equals_active_pass_b_diff() -> None:
    before = _index(a2.read_jsonl(ROOT / fix2b.PRE_FIX2B_PASS_B))
    after = _index(_pass_b())
    changed = {pair for pair in before if before[pair] != after[pair]}
    ledger = _json(fix2b.FINAL_LEDGER)
    ledger_pairs = {(row["case_id"], row["evidence_id"]) for row in ledger["changes"]}
    assert changed == ledger_pairs
    assert ledger["changed_row_count"] == len(changed)
    assert all(row["before_row_sha256"] != row["after_row_sha256"] for row in ledger["changes"])


def test_support_sets_are_fully_regenerated_without_strict_supersets() -> None:
    classifications = a2.read_jsonl(ROOT / a2.OBLIGATION_CLASSIFICATION)
    required = a2.pb1_required_obligations(classifications)
    by_case: dict[str, list[dict]] = defaultdict(list)
    for row in _pass_b():
        by_case[row["case_id"]].append(row)
    for candidate in _pass_c():
        sets = a2.derive_pb1_minimal_complete_sets(
            required.get(candidate["case_id"], []), by_case[candidate["case_id"]],
        )
        assert candidate["acceptable_complete_support_sets"] == sets
        frozen = [frozenset(group) for group in sets]
        assert not any(left < right for left in frozen for right in frozen)


def test_stale_allowed_and_forbidden_evidence_cannot_survive() -> None:
    pass_a = a2.read_jsonl(ROOT / a2.PASS_A)
    classifications = a2.read_jsonl(ROOT / a2.OBLIGATION_CLASSIFICATION)
    derived = a2.derive_pb1_pass_c(
        ROOT, pass_a, classifications, _pass_b(),
        _json(a2.INELIGIBLE_EVIDENCE_AUDIT),
    )
    assert derived == _pass_c()


def test_pass_c_is_byte_deterministic_and_has_no_clarify() -> None:
    pass_a = a2.read_jsonl(ROOT / a2.PASS_A)
    classifications = a2.read_jsonl(ROOT / a2.OBLIGATION_CLASSIFICATION)
    ineligible = _json(a2.INELIGIBLE_EVIDENCE_AUDIT)
    first = a2.derive_pb1_pass_c(ROOT, pass_a, classifications, _pass_b(), ineligible)
    second = a2.derive_pb1_pass_c(ROOT, pass_a, classifications, _pass_b(), ineligible)
    assert first == second == _pass_c()
    serialized_first = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in first)
    serialized_second = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in second)
    assert serialized_first.encode() == serialized_second.encode()
    assert Counter(row["expected_production_route"] for row in first)["CLARIFY"] == 0


def test_manifest_and_execution_boundaries_are_fail_closed() -> None:
    manifest = _json(a2.A2_MANIFEST)
    assert manifest["status"] == fix2b.MANIFEST_STATUS
    assert manifest["evaluation_package_frozen"] is False
    assert manifest["structural_integrity_verified"] is False
    assert manifest["evaluation_authorized"] is False
    assert manifest["evaluation_executed"] is False
    assert manifest["ev2_consumed"] is False
    assert manifest["a3_authorized"] is False
    assert manifest["week3_p0_passed"] is False
    assert manifest["week4_authorized"] is False
    assert manifest["notebook_required"] is False
    source = (ROOT / "scripts/evaluation/week3_ev2_a2_fix2b.py").read_text(encoding="utf-8").lower()
    assert "run_case_v3" not in source
    assert "from payresolve_ai" not in source
    assert "import payresolve_ai" not in source


def test_pkg1_bundle_closes_all_locked_repository_dependencies(pkg1_bundle: Path) -> None:
    integrity = fix2b.verify_bundle_integrity(pkg1_bundle)
    assert integrity["passed"] is True
    assert integrity["locked_dependencies_present"] is True
    payload_paths = integrity["payload_paths"]
    assert {path.as_posix() for path in fix2b.LOCKED_HASHES} <= payload_paths
    assert a2.PB1_FIX2A_PROJECTION_COMPARISON.as_posix() in payload_paths
    assert a2.KB.as_posix() in payload_paths


def test_pkg1_bundle_preserves_exact_historical_phase_log_order(pkg1_bundle: Path) -> None:
    with zipfile.ZipFile(pkg1_bundle) as archive:
        for archived_rel, expected in fix2b.HISTORICAL_PROVENANCE.items():
            payload = archive.read(archived_rel)
            assert hashlib.sha256(payload).hexdigest() == expected["sha256"]
        blind_events = json.loads(
            archive.read("review_evidence/fix2_blind_phase_log.json")
        )["events"]
        tiebreak_events = json.loads(
            archive.read("review_evidence/fix2a_tiebreak_phase_log.json")
        )["events"]
    blind_sequence = {event["event"]: event["sequence"] for event in blind_events}
    assert blind_sequence["PACKET_FROZEN"] < blind_sequence["BLIND_DECISIONS_FROZEN"]
    assert blind_sequence["BLIND_DECISIONS_FROZEN"] < blind_sequence["CURRENT_PASS_B_COMPARISON_OPENED"]
    tiebreak_sequence = {event["event"]: event["sequence"] for event in tiebreak_events}
    assert tiebreak_sequence["TIEBREAK_PACKET_FROZEN"] < tiebreak_sequence["TIEBREAK_DECISIONS_FROZEN"]
    assert tiebreak_sequence["TIEBREAK_DECISIONS_FROZEN"] < tiebreak_sequence["THREE_WAY_COMPARISON_OPENED"]


def test_pkg1_standalone_replay_cannot_fall_back_to_current_worktree(
    pkg1_bundle: Path,
    tmp_path: Path,
) -> None:
    replay = fix2b.standalone_bundle_replay(pkg1_bundle)
    assert replay["passed"] is True
    assert replay["returncode"] == 0
    assert replay["status"] == fix2b.STATUS
    assert replay["pythonpath"] == "."
    assert replay["working_tree_fallback"] is False
    assert not Path(replay["extraction_path"]).exists()

    missing_projection = tmp_path / "missing_projection.zip"
    with zipfile.ZipFile(pkg1_bundle) as source, zipfile.ZipFile(
        missing_projection, "w", compression=zipfile.ZIP_DEFLATED,
    ) as target:
        for info in source.infolist():
            if info.filename == a2.PB1_FIX2A_PROJECTION_COMPARISON.as_posix():
                continue
            target.writestr(info, source.read(info.filename))
    failed_replay = fix2b.standalone_bundle_replay(missing_projection)
    assert failed_replay["passed"] is False
    assert failed_replay["returncode"] != 0
    assert "locked_identity_drift" in failed_replay["stdout"]
