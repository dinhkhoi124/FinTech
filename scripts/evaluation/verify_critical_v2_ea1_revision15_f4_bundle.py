"""Detached, executable verification for the R15-F4-F1 review bundle."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch


REAL_A15 = "8631333b7ac180ca13fc2a98c42c516402b4f2b5"
CONFIG_SHA256 = "36f372c6dd08e948bceea52d3222e8510e32382bec8748e264f8ac4eb977d943"
CANDIDATE_MANIFEST_SHA256 = "f912798ae5c02c774702ae97bee8b2b4f6c6ab12b6534e1b2a3817a969b905ef"
PRIMARY_RUNTIME_SHA256 = "b036b8e337f809817dbbc6006e36d892c63480df2a919d9775279195c85bd22d"
REPRO_RUNTIME_SHA256 = "4176520d36027926d7e0f9497ed10c4e9477250e64908de4d417847e5237b879"
EXPECTED_TRANSITION_INPUT_SHA256 = {
    "reports/week_03/results/critical_eval_v2_revision_7_primary_raw_manifest.json":
        "114d29ec72a561886a8effd393510f9365e62f1d3c8783aa9def919fee04e0b3",
    "reports/week_03/results/critical_eval_v2_revision_7_reproduction_raw_manifest.json":
        "51a3a0843d9d91dcee36e83ed11bd9fa237b34d9f9abbbfa4401b88ce53d96e2",
    "configs/evaluation/critical_eval_v2_execution.json": CONFIG_SHA256,
    "reports/week_03/results/critical_eval_v2_runtime_execution_environment.json":
        PRIMARY_RUNTIME_SHA256,
    "reports/week_03/results/critical_eval_v2_revision_15_runtime_execution_environment.json":
        REPRO_RUNTIME_SHA256,
}


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def git(repo: Path, *args: str, binary: bool = False):
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        text=not binary,
        stderr=subprocess.STDOUT,
    )


def load_execution_module(repo: Path):
    source = repo / "src/payresolve_ai/evaluation/critical_v2_execution.py"
    spec = importlib.util.spec_from_file_location("ea1_r15_f4_f1_replay", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load proposed execution module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_inventory(extracted: Path) -> int:
    inventory_path = extracted / "inventory.json"
    listed = {row["path"]: row for row in load(inventory_path)["files"]}
    actual = {
        path.relative_to(extracted).as_posix(): path
        for path in extracted.rglob("*")
        if path.is_file() and path != inventory_path
    }
    if set(listed) != set(actual):
        raise RuntimeError("bundle inventory membership mismatch")
    for relative, path in actual.items():
        expected = {"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)}
        if listed[relative] != expected:
            raise RuntimeError(f"bundle inventory hash mismatch: {relative}")
    return len(listed)


def verify_real_evidence(extracted: Path) -> tuple[Path, dict]:
    evidence_root = extracted / "real_evidence"
    evidence_hashes = load(extracted / "evidence/real_evidence_hashes.json")
    for relative, expected in evidence_hashes.items():
        path = evidence_root / relative
        if (
            not path.is_file()
            or sha256(path) != expected["sha256"]
            or path.stat().st_size != expected["bytes"]
        ):
            raise RuntimeError(f"real evidence mismatch: {relative}")
    config_path = evidence_root / "configs/evaluation/critical_eval_v2_execution.json"
    config = load(config_path)
    if config["readiness_revision"] != 15 or sha256(config_path) != CONFIG_SHA256:
        raise RuntimeError("readiness revision or execution config changed")
    candidate = evidence_root / "reports/week_03/results/critical_eval_v2_candidate_manifest.json"
    if sha256(candidate) != CANDIDATE_MANIFEST_SHA256:
        raise RuntimeError("Candidate manifest changed")
    return evidence_root, config


def verify_git_proof(extracted: Path, replay: Path, metadata: dict) -> tuple[str, str, dict]:
    proof = extracted / "synthetic/r15_f4_f1_history.bundle"
    subprocess.run(
        [
            "git", "-c", "core.autocrlf=false", "clone", "-q", "-b",
            "r15-f4-f1-review", str(proof), str(replay),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "core.autocrlf", "false"],
        cwd=replay,
        check=True,
        capture_output=True,
    )
    a16 = git(replay, "rev-parse", "HEAD").strip()
    r15_f4 = git(replay, "rev-parse", "HEAD^").strip()
    parent = git(replay, "rev-parse", "HEAD^^").strip()
    if parent != REAL_A15:
        raise RuntimeError("Git object proof: R15-F4 parent is not real A15")
    changed_f4 = sorted(
        git(replay, "diff", "--name-only", f"{REAL_A15}..{r15_f4}").splitlines()
    )
    if changed_f4 != sorted(metadata["proposed_paths"]):
        raise RuntimeError("Git object proof: R15-F4 changed-path scope mismatch")
    config = load(replay / "configs/evaluation/critical_eval_v2_execution.json")
    allowed = sorted(config["authorization"]["allowed_authorization_commit_paths"])
    changed_a16 = sorted(git(replay, "diff", "--name-only", f"{r15_f4}..{a16}").splitlines())
    if changed_a16 != allowed:
        raise RuntimeError("Git object proof: A16 changed-path scope mismatch")
    auth_relative = config["authorization"]["committed_record"]
    authorization = json.loads(git(replay, "show", f"{a16}:{auth_relative}", binary=True))
    if authorization.get("readiness_implementation_commit") != r15_f4:
        raise RuntimeError("Git object proof: A16 readiness binding mismatch")
    for relative, expected in authorization["execution_artifact_sha256"].items():
        committed = git(replay, "show", f"{r15_f4}:{relative}", binary=True)
        if digest_bytes(committed) != expected:
            raise RuntimeError(f"Git object proof: readiness hash mismatch: {relative}")
    for relative in metadata["proposed_paths"]:
        committed = git(replay, "show", f"{r15_f4}:{relative}", binary=True)
        if committed != (extracted / "proposed" / relative).read_bytes():
            raise RuntimeError(f"Git object proof: proposed byte mismatch: {relative}")
    reported = load(extracted / "synthetic/topology.json")
    if reported["r15_f4_commit"] != r15_f4 or reported["a16_commit"] != a16:
        raise RuntimeError("reported topology differs from Git object proof")
    return r15_f4, a16, authorization


def copy_real_evidence(evidence_root: Path, replay: Path) -> None:
    for source in evidence_root.rglob("*"):
        if source.is_file():
            target = replay / source.relative_to(evidence_root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)


def asset_overrides(replay: Path, external_root: Path, config: dict) -> dict[str, Path]:
    manifest = load(replay / config["readiness_outputs"]["runtime_asset_manifest"])
    retrieval = load(replay / config["runtime_dependencies"]["retrieval_config"]["path"])
    overrides = {logical: external_root / logical for logical in manifest["asset_file_sha256"]}
    snapshot = Path(retrieval["encoder"]["huggingface_home"]) / (
        "models--sentence-transformers--all-MiniLM-L6-v2/snapshots/"
        + retrieval["encoder"]["revision"]
    )
    overrides.update({
        "encoder_snapshot/" + row["logical_path"]: external_root / snapshot / row["logical_path"]
        for row in manifest["encoder"]["files"]
    })
    for logical, path in overrides.items():
        if not path.is_file():
            raise RuntimeError(f"detached runtime-asset source absent: {logical}")
    return overrides


def replay_comparator_controls(execution, replay: Path, config_path: Path, config: dict) -> dict:
    outputs = config["evaluation_outputs"]
    old_total = behavioral_total = 0
    primary_provenance = repro_provenance = 0
    for variant in execution.VARIANT_IDS:
        primary = rows(replay / outputs["primary"][f"{variant}_raw"])
        repro = rows(replay / outputs["reproducibility_rerun"][f"{variant}_raw"])
        result = execution.compare_reproducibility_variant(
            replay, config_path, config, variant, primary, repro
        )
        old_total += result["legacy_equal_rows"]
        behavioral_total += result["behavioral_equal_rows"]
        primary_provenance += len(primary)
        repro_provenance += len(repro)
    if (old_total, behavioral_total, primary_provenance, repro_provenance) != (0, 180, 180, 180):
        raise RuntimeError("independent positive comparator replay mismatch")

    primary = rows(replay / outputs["primary"]["V0_raw"])
    repro = rows(replay / outputs["reproducibility_rerun"]["V0_raw"])
    behavioral = {
        "classifier_prediction": lambda row: row["classifier_prediction"].update(predicted_intent="mutated"),
        "retrieval_strategy": lambda row: row.__setitem__("retrieval_strategy", "MUTATED"),
        "retrieved_evidence": lambda row: row["retrieved_evidence"][0].__setitem__("score", -1.0),
        "gate_inputs": lambda row: row["gate_inputs"].__setitem__("min_top1_score", -1.0),
        "gate_decision": lambda row: row["gate_decision"].__setitem__("decision", "MUTATED"),
        "response": lambda row: row.__setitem__("response", "mutated response"),
        "claim_records": lambda row: row.__setitem__("claim_records", [{"mutation": True}]),
        "citation_records": lambda row: row.__setitem__("citation_records", [{"mutation": True}]),
        "eligible_evidence_records": lambda row: row.__setitem__("eligible_evidence_records", [{"mutation": True}]),
        "model_input_sha256": lambda row: row.__setitem__("model_input_sha256", "0" * 64),
        "determinism.seed": lambda row: row["determinism"].__setitem__("seed", -1),
        "system_error": lambda row: row.__setitem__("system_error", "mutated"),
    }
    behavioral_pass = 0
    for mutate in behavioral.values():
        changed = copy.deepcopy(repro)
        mutate(changed[0])
        try:
            result = execution.compare_reproducibility_variant(
                replay, config_path, config, "V0", primary, changed
            )
            detected = not result["behavioral_identical"]
        except execution.CriticalV2ExecutionError:
            detected = True
        behavioral_pass += int(detected)

    provenance = {
        "primary_runtime_sha": (primary, "primary", lambda row: row.__setitem__("execution_environment_sha256", "0" * 64)),
        "primary_contract": (primary, "primary", lambda row: row["determinism"].__setitem__("execution_contract_sha256", "0" * 64)),
        "repro_runtime_sha": (repro, "reproducibility_rerun", lambda row: row.__setitem__("execution_environment_sha256", "0" * 64)),
        "repro_contract": (repro, "reproducibility_rerun", lambda row: row["determinism"].__setitem__("execution_contract_sha256", "0" * 64)),
        "repro_reference": (repro, "reproducibility_rerun", lambda row: row.__setitem__("execution_environment_reference", "unexpected.json")),
        "execution_id": (repro, "reproducibility_rerun", lambda row: row.__setitem__("execution_id", "malformed")),
        "run_label": (repro, "reproducibility_rerun", lambda row: row.__setitem__("run_label", "wrong")),
        "variant_id": (repro, "reproducibility_rerun", lambda row: row.__setitem__("variant_id", "V9")),
    }
    provenance_pass = 0
    for source, label, mutate in provenance.values():
        row = copy.deepcopy(source[0])
        mutate(row)
        try:
            execution.validate_reproducibility_provenance(
                replay, config_path, config, row,
                run_label=label, variant_id="V0",
            )
        except execution.CriticalV2ExecutionError:
            provenance_pass += 1
    if behavioral_pass != 12 or provenance_pass != 8:
        raise RuntimeError("independent negative-control replay mismatch")
    return {
        "old_equal_rows": old_total,
        "behavioral_equal_rows": behavioral_total,
        "primary_provenance_rows": primary_provenance,
        "reproduction_provenance_rows": repro_provenance,
        "behavioral_negative_controls": behavioral_pass,
        "provenance_negative_controls": provenance_pass,
    }


def replay_migration_and_verify(execution, replay: Path, external_root: Path, config: dict) -> dict:
    config_path = replay / "configs/evaluation/critical_eval_v2_execution.json"
    state_path = replay / config["evaluation_outputs"]["execution_state"]
    comparison_path = replay / config["evaluation_outputs"]["reproduction_comparison"]
    final_path = replay / config["evaluation_outputs"]["final_summary"]
    receipt_path = replay / execution.POSTEVAL_CONTINUATION_RECEIPT
    for path in (comparison_path, final_path, receipt_path):
        path.unlink(missing_ok=True)
    before = load(state_path)
    overrides = asset_overrides(replay, external_root, config)
    verify_assets = execution.verify_runtime_asset_manifest
    with patch.object(
        execution,
        "verify_runtime_asset_manifest",
        side_effect=lambda synthetic_root, synthetic_config: verify_assets(
            synthetic_root, synthetic_config, overrides=overrides
        ),
    ), patch.object(
        execution,
        "freeze_or_verify_runtime_environment",
        side_effect=AssertionError("model runtime regeneration is forbidden"),
    ), patch.object(
        execution,
        "execute_variant_runtime",
        side_effect=AssertionError("model/retrieval/generation execution is forbidden"),
    ), patch.object(
        execution,
        "evaluate_frozen_run",
        side_effect=AssertionError("evaluator execution is forbidden"),
    ):
        authorization = execution.verify_execution_authorization(replay, config_path)
        receipt = execution.migrate_r15_f4_posteval_continuation(replay, config_path)
        migrated = load(state_path)
        comparison = execution.verify_reproducibility(replay, config_path)
    verified = load(state_path)
    if receipt.get("status_history") != ["PREPARED", "PASS"]:
        raise RuntimeError("migration did not prove PREPARED -> PASS")
    if (
        before["state"] != "REPRO_EVALUATED"
        or migrated["state"] != "REPRO_EVALUATED"
        or migrated["history"] != before["history"]
        or len(migrated["history"]) != 10
    ):
        raise RuntimeError("migration replay did not preserve evaluated state/history")
    if (
        comparison["status"] != "PASS"
        or comparison["behavioral_equal_rows"] != 180
        or verified["state"] != "REPRO_VERIFIED"
        or len(verified["history"]) != 11
    ):
        raise RuntimeError("verification replay did not reach REPRO_VERIFIED")
    if verified["history"][10]["direct_input_sha256"] != EXPECTED_TRANSITION_INPUT_SHA256:
        raise RuntimeError("verify transition does not bind exact five material inputs")
    if final_path.exists():
        raise RuntimeError("detached replay executed finalization")
    return {
        "authorization": authorization,
        "receipt": receipt,
        "before": before,
        "migrated": migrated,
        "comparison": comparison,
        "verified": verified,
        "comparison_sha256": sha256(comparison_path),
    }


def verify(bundle: Path, root: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="ea1_r15_f4_f1_verify_") as temporary:
        extracted = Path(temporary) / "bundle"
        extracted.mkdir()
        with zipfile.ZipFile(bundle) as archive:
            archive.extractall(extracted)
        inventory_count = verify_inventory(extracted)
        metadata = load(extracted / "bundle_metadata.json")
        if metadata["task"] != "W3-002-CR1-EA1-R15-F4-F1-CLOSURE-CORRECTION":
            raise RuntimeError("bundle task metadata mismatch")
        for relative in metadata["proposed_paths"]:
            if sha256(extracted / "proposed" / relative) != sha256(root / relative):
                raise RuntimeError(f"proposed source differs from working review bytes: {relative}")
        evidence_root, _ = verify_real_evidence(extracted)
        replay = Path(temporary) / "replay"
        r15_f4, a16, authorization = verify_git_proof(extracted, replay, metadata)
        copy_real_evidence(evidence_root, replay)
        execution = load_execution_module(replay)
        config = execution.load_execution_config(
            replay / "configs/evaluation/critical_eval_v2_execution.json"
        )
        controls = replay_comparator_controls(
            execution,
            replay,
            replay / "configs/evaluation/critical_eval_v2_execution.json",
            config,
        )
        lifecycle = replay_migration_and_verify(execution, replay, root, config)
        if authorization["execution_artifact_sha256"] != execution._readiness_artifact_hashes(replay):
            raise RuntimeError("A16 authorization does not bind exact replay readiness bytes")
        if lifecycle["receipt"] != load(extracted / "synthetic/migration_receipt.json"):
            raise RuntimeError("generated migration evidence differs from detached replay")
        if lifecycle["comparison"] != load(extracted / "synthetic/comparison.json"):
            raise RuntimeError("generated comparison evidence differs from detached replay")
        if lifecycle["verified"] != load(extracted / "synthetic/state_post_verify.json"):
            raise RuntimeError("generated post-verify state differs from detached replay")
        return {
            "status": "PASS",
            "inventory_files": inventory_count,
            "readiness_revision": 15,
            "execution_config_sha256": CONFIG_SHA256,
            "old_comparator_equal_rows": controls["old_equal_rows"],
            "corrected_behavioral_equal_rows": controls["behavioral_equal_rows"],
            "primary_provenance_rows": controls["primary_provenance_rows"],
            "reproduction_provenance_rows": controls["reproduction_provenance_rows"],
            "behavioral_negative_controls": controls["behavioral_negative_controls"],
            "provenance_negative_controls": controls["provenance_negative_controls"],
            "r15_f4_commit": r15_f4,
            "r15_f4_parent": REAL_A15,
            "a16_commit": a16,
            "a16_parent": r15_f4,
            "a16_changed_paths": 5,
            "migration_status_history": lifecycle["receipt"]["status_history"],
            "post_migration_state": lifecycle["migrated"]["state"],
            "post_verify_state": lifecycle["verified"]["state"],
            "post_verify_history": len(lifecycle["verified"]["history"]),
            "verify_transition_material_inputs": 5,
            "comparison_sha256": lifecycle["comparison_sha256"],
            "model_encoder_retrieval_generation_evaluator_calls": 0,
            "finalization_executed": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    print(json.dumps(verify(args.bundle.resolve(), args.root.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
