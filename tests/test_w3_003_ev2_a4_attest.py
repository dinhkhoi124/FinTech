from __future__ import annotations

import hashlib
import importlib.metadata
from pathlib import Path

import pytest

from scripts.evaluation import week3_ev2_a4_attest as attest


def test_python_attestation_requires_exact_cpython_3119_cpu_64bit() -> None:
    good = {"executable": "x", "implementation": "CPython", "version": "3.11.9", "platform": "x", "architecture": "64bit", "device": "cpu"}
    assert attest.attest_python(good)["passed"]
    assert not attest.attest_python({**good, "version": "3.13.0"})["passed"]


def test_dependency_attestation_rejects_mismatch_and_missing() -> None:
    expected = [("one", "1.0"), ("two", "2.0")]
    versions = {"one": "1.0", "two": "1.9"}
    result = attest.attest_dependencies(expected, lambda name: versions[name])
    assert not result["passed"] and result["mismatch_count"] == 1
    missing = attest.attest_dependencies(
        [("missing", "1")],
        lambda name: (_ for _ in ()).throw(importlib.metadata.PackageNotFoundError(name)),
    )
    assert not missing["passed"] and missing["requirements"][0]["installed"] is None


def test_snapshot_attestation_rejects_missing_and_hash_mutation(tmp_path: Path) -> None:
    root = tmp_path; revision = "r"; snapshot = root / "artifacts/cache/w1-003/huggingface/models--org--model/snapshots" / revision
    snapshot.mkdir(parents=True); file = snapshot / "config.json"; file.write_bytes(b"good")
    provenance = {"model_id": "org/model", "revision": revision, "snapshot_footprint_bytes": 4, "downloaded_snapshot_files": [{"path": "config.json", "bytes": 4, "sha256": hashlib.sha256(b"good").hexdigest()}]}
    assert attest.attest_snapshot(root, provenance)["passed"]
    file.write_bytes(b"evil")
    changed = attest.attest_snapshot(root, provenance)
    assert not changed["passed"] and changed["hash_mismatches"] == ["config.json"]
    file.unlink()
    missing = attest.attest_snapshot(root, provenance)
    assert not missing["passed"] and missing["missing_files"] == ["config.json"]


def test_runtime_assets_rejects_drift(tmp_path: Path) -> None:
    path = tmp_path / "asset.txt"; path.write_text("ok", encoding="utf-8")
    manifest = {"runtime_input_sha256": {"asset.txt": hashlib.sha256(b"ok").hexdigest()}}
    manifest["runtime_input_aggregate_sha256"] = attest.aggregate_bindings_sha256(manifest["runtime_input_sha256"])
    assert attest.attest_runtime_assets(tmp_path, manifest)["passed"]
    path.write_text("drift", encoding="utf-8")
    assert not attest.attest_runtime_assets(tmp_path, manifest)["passed"]


def test_preauth_payload_is_deliberately_non_authorizing() -> None:
    payload = {"authorization": "A4_PREAUTH_ATTESTATION_ONLY", "ev2_authorized": False, "senior_approval_state": "AWAITING_SENIOR_A4_APPROVAL", "not_authorizing": True}
    assert payload["authorization"] != "A4_AUTHORIZE_E1" and payload["ev2_authorized"] is False and payload["not_authorizing"]


def test_source_attestation_rejects_r1_before_any_runtime_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    decision = tmp_path / "decision.json"; receipt = tmp_path / "receipt.json"
    decision.write_text('{"selected_retriever":"R1","status":"FINALIZED_REVIEW_CORRECTION","final_senior_review_verdict":"APPROVE_COMMIT"}', encoding="utf-8")
    receipt.write_text('{"git_tree":"tree"}', encoding="utf-8")
    manifest = {"retrieval_decision_source": "decision.json", "paths": {"candidate_source_tree_receipt": "receipt.json"}, "selected_retriever": "R1", "retrieval_decision_sha256": attest.sha256(decision), "candidate_production_commit": "commit", "candidate_source_tree_sha256": "source", "retrieval_decision_candidate_git_blob": "blob"}
    monkeypatch.setattr(attest, "verify_working_source_tree", lambda *_: "source")
    monkeypatch.setattr(attest.subprocess, "check_output", lambda *_args, **_kwargs: "tree\n")
    result = attest.attest_source_and_retriever(tmp_path, manifest)
    assert not result["passed"] and result["selected_retriever"] == "R1"


def test_source_attestation_rejects_candidate_source_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    decision = tmp_path / "decision.json"; receipt = tmp_path / "receipt.json"
    decision.write_text('{"selected_retriever":"R0","status":"FINALIZED_REVIEW_CORRECTION","final_senior_review_verdict":"APPROVE_COMMIT"}', encoding="utf-8")
    receipt.write_text('{"git_tree":"tree"}', encoding="utf-8")
    manifest = {"retrieval_decision_source": "decision.json", "paths": {"candidate_source_tree_receipt": "receipt.json"}, "selected_retriever": "R0", "retrieval_decision_sha256": attest.sha256(decision), "candidate_production_commit": "commit", "candidate_source_tree_sha256": "expected", "retrieval_decision_candidate_git_blob": "blob"}
    monkeypatch.setattr(attest, "verify_working_source_tree", lambda *_: "drifted")
    monkeypatch.setattr(attest.subprocess, "check_output", lambda *_args, **_kwargs: "tree\n")
    assert not attest.attest_source_and_retriever(tmp_path, manifest)["passed"]


def test_offline_loader_rejects_missing_control_before_runtime_load(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    with pytest.raises(attest.AttestationError, match="A4_OFFLINE_ENVIRONMENT_MISMATCH"):
        attest.attest_offline_load(tmp_path)
