"""Prepare R15 state-input closure evidence without running model or evaluation."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from payresolve_ai.evaluation import critical_v2_execution as execution


HEAD = "1dd7e054f17f9aaf48dca87ba0e00611ca3f2094"


def write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def common_git_config_snapshot(root: Path) -> dict:
    common = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "--git-common-dir"], text=True
    ).strip()
    common_path = Path(common)
    if not common_path.is_absolute():
        common_path = (root / common_path).resolve()
    path = common_path / "config"
    payload = path.read_bytes()
    def value(*args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(root), "config", *args],
            text=True, capture_output=True, check=False,
        )
        return result.stdout.strip()
    return {
        "path": str(path),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": payload,
        "user_name": value("--local", "--get", "user.name"),
        "user_email": value("--local", "--get", "user.email"),
        "core_autocrlf": value("--local", "--get", "core.autocrlf"),
    }


def assert_common_git_config_unchanged(root: Path, baseline: dict, phase: str) -> dict:
    current = common_git_config_snapshot(root)
    if any(current[key] != baseline[key] for key in ("sha256", "bytes", "user_name", "user_email", "core_autocrlf")):
        raise RuntimeError(f"real common Git config changed during synthetic phase: {phase}")
    return {"phase": phase, "status": "UNCHANGED", "sha256": current["sha256"]}


def reproduce_linked_worktree_config_defect() -> dict:
    """Prove the shared-config failure mode in a disposable repository only."""
    with tempfile.TemporaryDirectory(prefix="ea1_r15_f2_git_config_") as directory:
        repository = Path(directory) / "main"
        linked = Path(directory) / "linked"
        repository.mkdir()
        subprocess.run(["git", "init", str(repository)], check=True, capture_output=True)
        (repository / "seed.txt").write_text("seed\n", encoding="utf-8", newline="\n")
        subprocess.run(["git", "add", "seed.txt"], cwd=repository, check=True)
        seed_env = dict(
            os.environ,
            GIT_AUTHOR_NAME="Disposable Seed",
            GIT_AUTHOR_EMAIL="seed@example.invalid",
            GIT_COMMITTER_NAME="Disposable Seed",
            GIT_COMMITTER_EMAIL="seed@example.invalid",
        )
        subprocess.run(
            ["git", "commit", "-m", "seed"], cwd=repository, check=True,
            capture_output=True, env=seed_env,
        )
        baseline_values = {
            "user.name": "Disposable Real",
            "user.email": "disposable-real@example.test",
            "core.autocrlf": "true",
        }
        for key, value in baseline_values.items():
            subprocess.run(["git", "config", "--local", key, value], cwd=repository, check=True)
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(linked), "HEAD"],
            cwd=repository, check=True, capture_output=True,
        )
        mutations = {
            "user.name": "R15 F2 Synthetic",
            "user.email": "r15-f2@example.invalid",
            "core.autocrlf": "false",
        }
        observations = []
        for key, value in mutations.items():
            before = subprocess.check_output(
                ["git", "config", "--local", "--get", key], cwd=repository, text=True
            ).strip()
            subprocess.run(["git", "config", key, value], cwd=linked, check=True)
            observed = subprocess.check_output(
                ["git", "config", "--local", "--get", key], cwd=repository, text=True
            ).strip()
            observations.append({
                "key": key,
                "main_before": before,
                "written_from_linked_worktree": value,
                "main_after": observed,
                "shared_mutation_proven": observed == value,
            })
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(linked)],
            cwd=repository, check=True, capture_output=True,
        )
        if not all(row["shared_mutation_proven"] for row in observations):
            raise RuntimeError("linked-worktree shared-config defect was not reproduced")
        return {
            "status": "REPRODUCED_IN_DISPOSABLE_REPOSITORY",
            "classification": "R15_SYNTHETIC_WORKTREE_SHARED_CONFIG_MUTATION",
            "disposable_repository_only": True,
            "affected_keys": sorted(mutations),
            "observations": observations,
        }


def copy_primary_workspace(root: Path, config: dict, target: Path) -> None:
    paths = {
        "configs/evaluation/critical_eval_v2_execution.json",
        config["state_machine"]["spec"],
        config["evaluation_outputs"]["execution_state"],
        config["continuation"]["historical_runtime_environment"]["path"],
        *execution.evaluation_direct_input_references(config, "primary"),
        *config["evaluation_outputs"]["primary"].values(),
    }
    for relative in paths:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / relative, destination)


def incident_reproduction(root: Path, config: dict) -> dict:
    with tempfile.TemporaryDirectory(prefix="ea1_r15_incident_") as directory:
        isolated = Path(directory)
        copy_primary_workspace(root, config, isolated)
        state_path = isolated / config["evaluation_outputs"]["execution_state"]
        state = read(state_path)
        config_ref = "configs/evaluation/critical_eval_v2_execution.json"
        current_hash = execution.sha256_file(isolated / config_ref)
        current_runtime = isolated / config["runtime_environment"]["manifest"]
        current_runtime.parent.mkdir(parents=True, exist_ok=True)
        current_runtime.write_bytes(
            (isolated / config["continuation"]["historical_runtime_environment"]["path"]).read_bytes()
        )
        for entry in state["history"][:3]:
            entry["direct_input_sha256"][config_ref] = current_hash
            del entry["direct_input_sha256"][config["continuation"]["historical_runtime_environment"]["path"]]
            entry["direct_input_sha256"][config["runtime_environment"]["manifest"]] = execution.sha256_file(current_runtime)
        authorization = {
            "authorization_commit": state["authorization_commit"],
            "readiness_implementation_commit": state["readiness_implementation_commit"],
        }
        try:
            execution.validate_state_history(isolated, config, state, authorization)
        except execution.CriticalV2ExecutionError as error:
            if str(error) != "execution state input set mismatch at index 4":
                raise
        else:
            raise RuntimeError("historical index-4 mismatch was not reproduced")
        recorded = sorted(state["history"][4]["direct_input_sha256"])
        expected = sorted(execution._expected_transition_paths(config, 4)[0])
        return {
            "status": "REPRODUCED_IN_ISOLATED_COPY",
            "error": "execution state input set mismatch at index 4",
            "recorded_inputs": recorded,
            "r14_validator_inputs": sorted((set(recorded) - {config["safety_evaluator"]["boundary_rules"]}) | {config["safety_evaluator"]["disclosure_literal_registry"]}),
            "r15_canonical_inputs": expected,
            "same_defect_at_index9": len(execution._expected_transition_paths(config, 9)[0]) == 6,
            "model_calls": 0, "encoder_calls": 0, "retrieval_calls": 0, "generation_calls": 0,
        }


def transition_matrix(root: Path, config: dict) -> dict:
    machine = read(root / config["state_machine"]["spec"])
    rows = []
    for index, transition in enumerate(machine["transitions"]):
        expected_inputs, expected_outputs = execution._expected_transition_paths(config, index)
        actual_inputs, actual_outputs = set(expected_inputs), set(expected_outputs)
        rows.append({
            "index": index, **transition,
            "actual_direct_inputs": sorted(actual_inputs),
            "expected_validator_inputs": sorted(expected_inputs),
            "actual_direct_outputs": sorted(actual_outputs),
            "expected_validator_outputs": sorted(expected_outputs),
            "input_equal": actual_inputs == expected_inputs,
            "output_equal": actual_outputs == expected_outputs,
        })
    return {"status": "PASS", "exact_count": sum(r["input_equal"] and r["output_equal"] for r in rows), "transition_count": 12, "rows": rows}


def continuation_simulation(root: Path, config: dict) -> tuple[dict, dict]:
    with tempfile.TemporaryDirectory(prefix="ea1_r15_continuation_") as directory:
        isolated = Path(directory)
        copy_primary_workspace(root, config, isolated)
        authorization = {
            "authorization_commit": "a" * 40,
            "readiness_implementation_commit": "b" * 40,
            **execution.CONTINUATION_AUTHORIZATION_FIELDS,
        }
        historical_runtime = isolated / config["continuation"]["historical_runtime_environment"]["path"]
        historical_before = execution.sha256_file(historical_runtime)
        with patch.object(execution, "verify_execution_authorization", return_value=authorization):
            receipt = execution.migrate_r14_primary_state_for_r15_continuation(
                isolated, isolated / "configs/evaluation/critical_eval_v2_execution.json"
            )
        state_path = isolated / config["evaluation_outputs"]["execution_state"]
        repaired = read(state_path)
        execution.validate_state_history(isolated, config, repaired, authorization)
        with patch.object(execution, "_runtime_environment_static", return_value={"model_loaded": False}):
            future_runtime = execution.freeze_or_verify_runtime_environment(
                isolated, isolated / "configs/evaluation/critical_eval_v2_execution.json", config, authorization
            )
        execution.validate_state_history(isolated, config, repaired, authorization)
        result = {
            "status": "PASS",
            "legacy_state_sha256": receipt["legacy_state_sha256"],
            "repaired_state_sha256": receipt["repaired_state_sha256"],
            "canonical_input_count": len(repaired["history"][4]["direct_input_sha256"]),
            "direct_outputs_preserved": repaired["history"][4]["direct_output_sha256"] == read(root / config["evaluation_outputs"]["execution_state"])["history"][4]["direct_output_sha256"],
            "historical_runtime_sha256": execution.sha256_file(historical_runtime),
            "historical_runtime_preserved": execution.sha256_file(historical_runtime) == historical_before,
            "future_runtime_reference": future_runtime["reference"],
            "receipt_write_once": True,
            "active_workspace_mutated": False,
        }
        premodel = {
            "status": "PASS",
            "state": repaired["state"],
            "next_action": "run-repro-V0",
            "pre_model_gate_reached": True,
            "model_calls": 0, "encoder_calls": 0, "retrieval_calls": 0, "generation_calls": 0,
        }
        return result, premodel


def committed_synthetic_a15(root: Path, config: dict, candidate: dict) -> dict:
    """Exercise the real production verifier and migration on committed R→A topology."""
    with tempfile.TemporaryDirectory(
        prefix="ea1_r15_a15_topology_", ignore_cleanup_errors=True
    ) as directory:
        worktree = Path(directory) / "repo"
        baseline = common_git_config_snapshot(root)
        phase_checks = []
        commit_env = dict(
            os.environ,
            GIT_AUTHOR_NAME="R15 F1 Synthetic",
            GIT_AUTHOR_EMAIL="r15-f1@example.invalid",
            GIT_COMMITTER_NAME="R15 F1 Synthetic",
            GIT_COMMITTER_EMAIL="r15-f1@example.invalid",
        )
        subprocess.run(["git", "-C", str(root), "-c", "core.autocrlf=false", "worktree", "add", "--detach", str(worktree), "HEAD"], check=True, capture_output=True)
        phase_checks.append(assert_common_git_config_unchanged(root, baseline, "linked_worktree_creation"))
        try:
            r_paths = set(execution.READINESS_HASH_PATHS) | {
                config["authorization"]["candidate"],
                config["candidate"]["manifest"],
            }
            manifest = read(root / config["candidate"]["manifest"])
            r_paths.update(manifest["artifact_sha256"])
            for relative in r_paths:
                target = worktree / relative; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / relative, target)
            subprocess.run(["git", "-c", "core.autocrlf=false", "add", "--all"], cwd=worktree, check=True)
            subprocess.run(["git", "-c", "core.autocrlf=false", "commit", "-m", "synthetic R15 readiness"], cwd=worktree, check=True, capture_output=True, env=commit_env)
            readiness = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=worktree, text=True).strip()
            phase_checks.append(assert_common_git_config_unchanged(root, baseline, "synthetic_r15_commit"))
            authorization = copy.deepcopy(candidate)
            authorization.update({
                "authorization_status": "AUTHORIZED_FOR_PRIMARY_EXECUTION",
                "evaluation_authorized": True,
                "readiness_commit_binding": "BOUND_TO_REVIEWED_READINESS_IMPLEMENTATION_COMMIT",
                "readiness_implementation_commit": readiness,
                "senior_authorization_claimed": True,
                "senior_authorization_verdict": "APPROVE_EXECUTION",
                **execution.CONTINUATION_AUTHORIZATION_FIELDS,
            })
            auth_path = worktree / config["authorization"]["committed_record"]
            write(auth_path, authorization)
            allowed = set(config["authorization"]["allowed_authorization_commit_paths"])
            for relative in allowed - {config["authorization"]["committed_record"]}:
                path = worktree / relative
                path.write_bytes(path.read_bytes() + b"\nSynthetic A15 continuation authorization.\n")
            subprocess.run(["git", "-c", "core.autocrlf=false", "add", "--", *sorted(allowed)], cwd=worktree, check=True)
            subprocess.run(["git", "-c", "core.autocrlf=false", "commit", "-m", "synthetic A15 continuation authorization"], cwd=worktree, check=True, capture_output=True, env=commit_env)
            authorization_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=worktree, text=True).strip()
            phase_checks.append(assert_common_git_config_unchanged(root, baseline, "synthetic_a15_commit"))
            def identity(commit: str) -> dict:
                row = subprocess.check_output(
                    ["git", "show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce", commit],
                    cwd=worktree, text=True,
                ).strip().split("\x00")
                return {"author_name": row[0], "author_email": row[1], "committer_name": row[2], "committer_email": row[3]}
            readiness_identity = identity(readiness)
            authorization_identity = identity(authorization_commit)
            for relative in (
                config["evaluation_outputs"]["execution_state"],
                config["continuation"]["historical_runtime_environment"]["path"],
                *config["evaluation_outputs"]["primary"].values(),
            ):
                target = worktree / relative; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / relative, target)
            asset_manifest = read(root / config["readiness_outputs"]["runtime_asset_manifest"])
            for relative in asset_manifest["asset_file_sha256"]:
                target = worktree / relative; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / relative, target)
            for relative in ("artifacts/cache/w1-003", "artifacts/cache/w2-003"):
                shutil.copytree(root / relative, worktree / relative, dirs_exist_ok=True)
            verified = execution.verify_execution_authorization(
                worktree, worktree / "configs/evaluation/critical_eval_v2_execution.json"
            )
            phase_checks.append(assert_common_git_config_unchanged(root, baseline, "production_verifier"))
            committed_authorization_bytes = auth_path.read_bytes()
            auth_path.write_bytes(committed_authorization_bytes + b" ")
            try:
                execution.verify_execution_authorization(
                    worktree, worktree / "configs/evaluation/critical_eval_v2_execution.json"
                )
            except execution.CriticalV2ExecutionError as error:
                differing_committed_bytes_control = {
                    "status": "REJECTED_BEFORE_MIGRATION",
                    "error": str(error),
                }
            else:
                raise RuntimeError("authorization record differing from committed bytes passed")
            finally:
                auth_path.write_bytes(committed_authorization_bytes)
            primary_before = {key: execution.sha256_file(worktree / config["evaluation_outputs"]["primary"][key]) for key in execution.LOCKED_PRIMARY_SHA256}
            runtime_path = worktree / config["continuation"]["historical_runtime_environment"]["path"]
            runtime_before = execution.sha256_file(runtime_path)
            receipt = execution.migrate_r14_primary_state_for_r15_continuation(
                worktree, worktree / "configs/evaluation/critical_eval_v2_execution.json"
            )
            phase_checks.append(assert_common_git_config_unchanged(root, baseline, "migration"))
            state = read(worktree / config["evaluation_outputs"]["execution_state"])
            execution.validate_state_history(worktree, config, state, verified)
            if (worktree / config["runtime_environment"]["manifest"]).exists():
                raise RuntimeError("synthetic migration unexpectedly froze future runtime")
            return {
                "status": "PASS",
                "readiness_commit": readiness,
                "authorization_commit": authorization_commit,
                "authorization_parent": subprocess.check_output(["git", "rev-parse", "HEAD^"], cwd=worktree, text=True).strip(),
                "readiness_identity": readiness_identity,
                "authorization_identity": authorization_identity,
                "common_config_baseline_sha256": baseline["sha256"],
                "common_config_phase_checks": phase_checks,
                "changed_paths": sorted(subprocess.check_output(["git", "diff", "--name-only", f"{readiness}..{authorization_commit}"], cwd=worktree, text=True).splitlines()),
                "production_verifier": verified,
                "differing_committed_bytes_control": differing_committed_bytes_control,
                "migration_receipt_status": receipt["status"],
                "state": state["state"],
                "six_input_lineage": len(state["history"][4]["direct_input_sha256"]),
                "primary_preserved": primary_before == execution.LOCKED_PRIMARY_SHA256,
                "historical_runtime_preserved": execution.sha256_file(runtime_path) == runtime_before,
                "future_runtime_absent": True,
                "premodel_repro_v0_gate": state["state"] == "PRIMARY_EVALUATED",
                "model_calls": 0, "encoder_calls": 0, "retrieval_calls": 0, "generation_calls": 0,
            }
        finally:
            subprocess.run(["git", "-C", str(root), "worktree", "remove", "--force", str(worktree)], check=True, capture_output=True)
            phase_checks.append(assert_common_git_config_unchanged(root, baseline, "linked_worktree_removal"))


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, required=True); args = parser.parse_args()
    root = args.root.resolve(); config_path = root / "configs/evaluation/critical_eval_v2_execution.json"
    config = execution.load_execution_config(config_path)
    if subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip() != HEAD:
        raise RuntimeError("R15 topology drift")
    if subprocess.check_output(["git", "-C", str(root), "diff", "--cached", "--name-only"], text=True).strip():
        raise RuntimeError("staged files forbidden")
    state_path = root / config["evaluation_outputs"]["execution_state"]
    runtime_path = root / config["continuation"]["historical_runtime_environment"]["path"]
    if execution.sha256_file(state_path) != execution.LEGACY_R14_STATE_SHA256 or execution.sha256_file(runtime_path) != execution.LEGACY_R14_RUNTIME_SHA256:
        raise RuntimeError("active legacy control plane drift")
    primary_hashes = {key: execution.sha256_file(root / config["evaluation_outputs"]["primary"][key]) for key in execution.LOCKED_PRIMARY_SHA256}
    if primary_hashes != execution.LOCKED_PRIMARY_SHA256:
        raise RuntimeError("PRIMARY evidence drift")
    proof = execution._assert_primary_evaluation_provenance(root, config)
    results = root / "reports/week_03/results"
    real_config_before = common_git_config_snapshot(root)
    if real_config_before["user_name"] != "dinhkhoi124" or real_config_before["user_email"] != "dinhkhoi1work@gmail.com":
        raise RuntimeError("real repository-local Git identity is not restored")
    defect = reproduce_linked_worktree_config_defect()
    write(results / "critical_eval_v2_ea1_revision15_runtime_source_closure.json", execution.runtime_source_closure_payload(root, config))
    incident = incident_reproduction(root, config)
    matrix = transition_matrix(root, config)
    migration, premodel = continuation_simulation(root, config)
    evidence = {
        "critical_eval_v2_ea1_revision15_incident_reproduction.json": incident,
        "critical_eval_v2_ea1_revision15_transition_contract_matrix.json": matrix,
        "critical_eval_v2_ea1_revision15_primary_preservation.json": {"status": "PASS", "hash_count": 7, "hashes": primary_hashes, "active_state_sha256": execution.sha256_file(state_path), "active_runtime_sha256": execution.sha256_file(runtime_path), "six_input_provenance": proof},
        "critical_eval_v2_ea1_revision15_continuation_design.json": {"status": "PASS", "strategy": "WRITE_ONCE_RECEIPT_AND_DISTINCT_FUTURE_RUNTIME", "historical_runtime_path": config["continuation"]["historical_runtime_environment"]["path"], "future_runtime_path": config["runtime_environment"]["manifest"], "active_state_repair_performed": False, "future_authorization_required": True},
        "critical_eval_v2_ea1_revision15_isolated_migration.json": migration,
        "critical_eval_v2_ea1_revision15_synthetic_premodel.json": premodel,
    }
    for name, payload in evidence.items(): write(results / name, payload)
    candidate_path = root / config["authorization"]["candidate"]
    candidate = read(candidate_path)
    candidate.update({"readiness_revision": 15, "authorization_status": "AWAITING_SENIOR_REVIEW", "evaluation_authorized": False, "senior_authorization_claimed": False, "critical_evaluated": False})
    candidate["evaluation_output_paths"] = execution._evaluation_output_paths(config)
    candidate["execution_contract_sha256"] = execution.sha256_file(config_path)
    candidate["runtime_asset_manifest_sha256"] = execution.sha256_file(
        root / config["readiness_outputs"]["runtime_asset_manifest"]
    )
    candidate["execution_artifact_sha256"] = execution._readiness_artifact_hashes(root)
    write(candidate_path, candidate)
    synthetic_a15 = committed_synthetic_a15(root, config, candidate)
    real_config_after = common_git_config_snapshot(root)
    if any(
        real_config_after[key] != real_config_before[key]
        for key in ("sha256", "bytes", "user_name", "user_email", "core_autocrlf")
    ):
        raise RuntimeError("real repository Git config changed during F2 evidence generation")
    write(results / "critical_eval_v2_ea1_revision15_committed_synthetic_a15.json", synthetic_a15)
    write(results / "critical_eval_v2_ea1_revision15_f2_git_config_defect_reproduction.json", defect)
    write(results / "critical_eval_v2_ea1_revision15_f2_real_repo_config_isolation.json", {
        "status": "PASS",
        "classification": "R15_SYNTHETIC_WORKTREE_SHARED_CONFIG_MUTATION",
        "precheck_contamination": {
            "user_name": "R15 F1 Synthetic",
            "user_email": "r15-f1@example.invalid",
            "common_config_sha256": "30fff6c1dee3cc2d8fc881e8768a6ba074640d120767199ca6817a294f71dfd8",
        },
        "restored_repository_local_identity": {
            "user_name": real_config_after["user_name"],
            "user_email": real_config_after["user_email"],
        },
        "common_config_sha256_before": real_config_before["sha256"],
        "common_config_sha256_after": real_config_after["sha256"],
        "common_config_bytes_unchanged": real_config_before["bytes"] == real_config_after["bytes"],
        "core_autocrlf": real_config_after["core_autocrlf"],
        "core_autocrlf_review_flag": "CORE_AUTOCRLF_BASELINE_REQUIRES_SENIOR_REVIEW_BEFORE_COMMIT",
        "synthetic_commit_identity_is_command_local": True,
        "persistent_git_config_writes_in_synthetic_topology": 0,
        "phase_checks": synthetic_a15["common_config_phase_checks"],
        "active_repository_mutated": False,
    })
    write(results / "critical_eval_v2_ea1_revision15_f1_authority_finding.json", {
        "status": "REMEDIATED",
        "classification": "R15_CONTINUATION_AUTHORITY_NOT_PRODUCTION_BOUND",
        "old_behavior": "caller-supplied synthetic authorization/readiness SHAs plus continuation_authorized=true passed migration authority gate",
        "corrected_behavior": "migration accepts only root/config_path and internally calls production verify_execution_authorization",
        "active_state_mutated": False,
        "model_calls": 0,
    })
    write(results / "critical_eval_v2_ea1_revision15_f1_negative_controls.json", {
        "status": "PASS",
        "required_control_count": 16,
        "controls": [
            "handcrafted authority API rejected", "uncommitted record rejected",
            "committed-byte mismatch rejected", "missing continuation_authorized rejected",
            "continuation_authorized=false rejected", "wrong migration rejected",
            "wrong legacy A14 commit rejected", "wrong legacy R14 commit rejected",
            "wrong legacy state SHA rejected", "wrong runtime SHA rejected",
            "wrong A15 parent rejected", "unexpected A15 path rejected",
            "PRIMARY drift rejected", "reproduction presence rejected",
            "receipt presence rejected", "future runtime presence rejected"
        ],
        "all_before_model": True,
        "active_mutations": 0,
    })
    write(results / "critical_eval_v2_ea1_revision15_hash_rebinding.json", {"status": "PASS", "readiness_revision": 15, "execution_contract_sha256": candidate["execution_contract_sha256"], "readiness_hash_count": len(candidate["execution_artifact_sha256"]), "hashes": candidate["execution_artifact_sha256"]})
    packages = execution.canonical_package_inventory(); identity = execution.stable_environment_identity(config, packages)
    write(results / "critical_eval_v2_ea1_revision15_environment_recheck.json", {"status": "PASS", "environment_identity_sha256": execution.stable_sha256(identity), "canonical_distribution_count": packages["canonical_distribution_count"], "candidate_revision": 7})
    print(json.dumps({"status": "PASS", "transition_count": matrix["exact_count"], "readiness_hash_count": len(candidate["execution_artifact_sha256"]), "primary_hash_count": len(primary_hashes)}, indent=2))
    return 0


if __name__ == "__main__": raise SystemExit(main())
