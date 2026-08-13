"""Independently verify the detached EA1 Revision-13 readiness bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def require_sha256(value: object, label: str) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise RuntimeError(f"invalid SHA-256: {label}")


def stable_sha256(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_bundle(root: Path) -> dict[str, object]:
    root = root.resolve()
    inventory = json.loads((root / "detached_inventory.json").read_text(encoding="utf-8"))
    inventory_paths = {row["path"] for row in inventory["files"]}
    for row in inventory["files"]:
        path = root / row["path"]
        if not path.is_file() or path.stat().st_size != row["size"] or sha256(path) != row["sha256"]:
            raise RuntimeError(f"inventory mismatch: {row['path']}")
    task = root / "task_files"
    config = json.loads((task / "configs/evaluation/critical_eval_v2_execution.json").read_text(encoding="utf-8"))
    if config.get("readiness_revision") != 13:
        raise RuntimeError("Revision 13 config required")
    expected_allowlist = {
        "reports/week_03/results/critical_eval_v2_evaluation_authorization.json",
        "PROJECT_STATE.md",
        "TASKS.md",
        "reports/week_03/week_03_summary.md",
        "reports/week_03/daily/2026-08-13.md",
    }
    authorization_config = config.get("authorization", {})
    if (
        authorization_config.get("reviewed_daily_report_path")
        != "reports/week_03/daily/2026-08-13.md"
        or set(authorization_config.get("allowed_authorization_commit_paths", []))
        != expected_allowlist
        or len(authorization_config.get("allowed_authorization_commit_paths", [])) != 5
        or "reports/week_03/daily/2026-08-12.md"
        in authorization_config.get("allowed_authorization_commit_paths", [])
    ):
        raise RuntimeError("active R13 authorization daily-path topology mismatch")
    if config["runtime_environment"]["required_environment"] != {
        "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "HF_HUB_OFFLINE": "1"
    }:
        raise RuntimeError("offline environment contract mismatch")
    outputs = config["readiness_outputs"]
    for key in (
        "runtime_incident_lineage", "preauthorization_reset_plan", "offline_encoder_probe",
        "transitive_runtime_source_binding", "runtime_asset_comparison",
        "runtime_payload_comparison", "a12_negative_control", "environment_reconciliation",
    ):
        payload = json.loads((task / outputs[key]).read_text(encoding="utf-8"))
        if payload.get("readiness_revision") != 13:
            raise RuntimeError(f"R13 evidence revision mismatch: {key}")
    probe = json.loads((task / outputs["offline_encoder_probe"]).read_text(encoding="utf-8"))
    if (
        probe.get("status") != "PASS"
        or probe.get("network_attempt_count") != 0
        or probe.get("production_local_files_only") is not True
        or probe.get("embedding_ndarray_sha256") != "83483507be7e9c48ca8caff139e15dc3e1f88509addd55793b7fc96e95f87f8e"
    ):
        raise RuntimeError("offline probe is not clean")
    reconciliation = json.loads((task / outputs["environment_reconciliation"]).read_text(encoding="utf-8"))
    if (
        reconciliation.get("classification") != "ENV_DISCOVERY_CONTEXT_DRIFT"
        or reconciliation.get("actual_package_installation_drift") is not False
        or reconciliation.get("package_mutation_performed") is not False
        or reconciliation.get("context_invariance_status") != "PASS"
    ):
        raise RuntimeError("environment reconciliation classification mismatch")
    canonical_rows = reconciliation.get("canonical_inventory")
    if not isinstance(canonical_rows, list) or canonical_rows != sorted(set(canonical_rows)):
        raise RuntimeError("canonical inventory is not sorted and unique")
    for row in canonical_rows:
        name, separator, version = row.partition("==")
        if not separator or name != normalized_name(name) or not version or name == "payresolve-ai":
            raise RuntimeError(f"noncanonical environment row: {row}")
    canonical_sha = hashlib.sha256(("\n".join(canonical_rows) + "\n").encode()).hexdigest()
    if (
        len(canonical_rows) != reconciliation.get("canonical_distribution_count")
        or canonical_sha != reconciliation.get("canonical_package_fingerprint_sha256")
    ):
        raise RuntimeError("canonical package identity mismatch")
    contexts = reconciliation.get("context_invariance_results", [])
    identities = {
        (row.get("canonical_distribution_count"), row.get("canonical_package_fingerprint_sha256"))
        for row in contexts
    }
    if {row.get("context_id") for row in contexts} != {"C1", "C2", "C3", "C4"} or identities != {(len(canonical_rows), canonical_sha)}:
        raise RuntimeError("C1/C2/C3/C4 canonical invariance mismatch")
    if any(row.get("conflicting_version_count") != 0 for row in contexts):
        raise RuntimeError("conflicting distribution versions present")
    if reconciliation.get("conflicting_version_negative_control", {}).get("status") != "CONFLICTING_DISTRIBUTION_VERSIONS_REJECTED":
        raise RuntimeError("conflicting-version negative control mismatch")
    expected_core = {
        "huggingface-hub": "1.4.0", "numpy": "2.2.6",
        "sentence-transformers": "5.2.2", "torch": "2.9.0", "transformers": "5.0.0",
    }
    core = reconciliation.get("core_ml_dependency_binding", {})
    if {name: row.get("version") for name, row in core.items()} != expected_core:
        raise RuntimeError("core dependency binding mismatch")
    for name, row in core.items():
        require_sha256(row.get("metadata_sha256"), f"{name} METADATA")
        if row.get("record_sha256") is not None:
            require_sha256(row.get("record_sha256"), f"{name} RECORD")
    environment = json.loads((task / outputs["environment_manifest"]).read_text(encoding="utf-8"))
    installed = environment.get("installed_packages", {})
    if (
        installed.get("canonical_distribution_count") != len(canonical_rows)
        or installed.get("canonical_package_fingerprint_sha256") != canonical_sha
        or installed.get("conflicting_version_count") != 0
        or installed.get("core_ml_dependencies") != core
    ):
        raise RuntimeError("readiness environment does not bind reconciled canonical identity")
    contract_path = task / outputs["environment_contract"]
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    identity = contract.get("environment_identity", {})
    if (
        contract.get("authorization_bound") is not True
        or contract.get("environment_identity_sha256") != stable_sha256(identity)
        or identity.get("canonical_distribution_count") != len(canonical_rows)
        or identity.get("canonical_package_fingerprint_sha256") != canonical_sha
        or identity.get("required_environment") != config["runtime_environment"]["required_environment"]
        or identity.get("python") != {
            "implementation": environment.get("python_implementation"),
            "version": environment.get("python_version"),
        }
        or identity.get("core_ml_dependencies") != {
            name: {key: row.get(key) for key in ("normalized_name", "version", "metadata_sha256", "record_sha256")}
            for name, row in core.items()
        }
        or environment.get("reviewed_environment_identity") != identity
        or environment.get("reviewed_environment_identity_sha256") != contract.get("environment_identity_sha256")
    ):
        raise RuntimeError("reviewed environment identity contract mismatch")
    candidate = json.loads((task / config["authorization"]["candidate"]).read_text(encoding="utf-8"))
    authorization_hashes = candidate.get("execution_artifact_sha256", {})
    retrieval_test = "tests/test_retrieval_benchmark.py"
    retrieval_task_path = task / retrieval_test
    if (
        not retrieval_task_path.is_file()
        or f"task_files/{retrieval_test}" not in inventory_paths
        or authorization_hashes.get(retrieval_test) != sha256(retrieval_task_path)
    ):
        raise RuntimeError(
            "R13_REVIEW_SCOPE_COVERAGE_INCOMPLETE: retrieval regression binding"
        )
    if (
        candidate.get("reviewed_environment_identity_sha256") != contract.get("environment_identity_sha256")
        or candidate.get("environment_contract_artifact_sha256") != sha256(contract_path)
        or authorization_hashes.get(outputs["environment_contract"]) != sha256(contract_path)
        or authorization_hashes.get(outputs["environment_manifest"]) != sha256(task / outputs["environment_manifest"])
    ):
        raise RuntimeError("authorization candidate environment binding mismatch")
    closure_path = task / outputs["runtime_source_closure"]
    closure = json.loads(closure_path.read_text(encoding="utf-8"))
    if (
        closure.get("source_count") != 18
        or len(closure.get("source_sha256", {})) != 18
        or closure.get("silent_omissions") != 0
        or closure.get("authorization_bound") is not True
        or len(closure.get("modules", [])) != 18
        or authorization_hashes.get(outputs["runtime_source_closure"]) != sha256(closure_path)
    ):
        raise RuntimeError("runtime source closure contract mismatch")
    for row in closure["modules"]:
        relative, expected = row.get("path"), row.get("sha256")
        if row.get("authorization_bound") is not True or closure["source_sha256"].get(relative) != expected:
            raise RuntimeError(f"runtime source closure row mismatch: {relative}")
        path = task / relative
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"runtime source hash mismatch: {relative}")
        if authorization_hashes.get(relative) != expected:
            raise RuntimeError(f"runtime source absent from authorization hash map: {relative}")
    enforcement_symbols = {
        "canonical_package_inventory", "stable_environment_identity",
        "environment_contract_payload", "load_environment_contract",
        "_validate_authorization_payload", "verify_execution_authorization",
        "freeze_or_verify_runtime_environment",
        "validate_authorization_daily_path_topology", "run_critical",
    }
    enforcement_row = next(
        (row for row in closure["modules"]
         if row.get("path") == "src/payresolve_ai/evaluation/critical_v2_execution.py"),
        None,
    )
    if enforcement_row is None or not enforcement_symbols <= set(
        enforcement_row.get("runtime_used_symbols", [])
    ):
        raise RuntimeError("authorization/environment enforcement-symbol closure mismatch")
    controls = json.loads((task / outputs["binding_negative_controls"]).read_text(encoding="utf-8"))
    if (
        controls.get("status") != "PASS"
        or controls.get("environment_control_count") != 7
        or controls.get("source_tamper_control_count") != 4
        or {row.get("case") for row in controls.get("environment_controls", [])}
        != {f"ENV-AUTH-0{index}" for index in range(1, 8)}
        or any(row.get("status") != "REJECTED_BEFORE_MODEL_LOAD" or row.get("model_loader_calls") != 0
               for row in controls.get("environment_controls", []) + controls.get("source_tamper_controls", []))
    ):
        raise RuntimeError("authorization binding negative-control evidence mismatch")
    date_controls = controls.get("authorization_date_controls", {})
    if (
        date_controls.get("status") != "PASS"
        or date_controls.get("reviewed_daily_report_path")
        != "reports/week_03/daily/2026-08-13.md"
        or set(date_controls.get("exact_allowed_paths", [])) != expected_allowlist
        or date_controls.get("active_case_count") != 7
        or date_controls.get("historical_revision12_fixture") != "PASS"
    ):
        raise RuntimeError("authorization-date control evidence mismatch")
    assets = json.loads((task / outputs["runtime_asset_manifest"]).read_text(encoding="utf-8"))
    if len(assets.get("encoder", {}).get("files", [])) != 11:
        raise RuntimeError("MiniLM snapshot binding count mismatch")
    negative = json.loads((task / outputs["a12_negative_control"]).read_text(encoding="utf-8"))
    if negative.get("status") != "REJECTED_AS_EXPECTED":
        raise RuntimeError("A12 negative control mismatch")
    if candidate.get("evaluation_authorized") is not False or candidate.get("senior_authorization_claimed") is not False:
        raise RuntimeError("authorization candidate overclaims")
    expected_candidate = {
        "candidate_manifest_sha256": "f912798ae5c02c774702ae97bee8b2b4f6c6ab12b6534e1b2a3817a969b905ef",
        "candidate_commit": "18a1840f39fef8f07337ff357f7991292389bae9",
    }
    if any(candidate.get(key) != value for key, value in expected_candidate.items()):
        raise RuntimeError("Candidate Revision 7 binding mismatch")
    coverage_path = root / "evidence/review_scope_coverage.json"
    proposed_path = root / "evidence/proposed_commit_paths.json"
    if not coverage_path.is_file() or not proposed_path.is_file():
        raise RuntimeError("R13_REVIEW_SCOPE_COVERAGE_INCOMPLETE: evidence missing")
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    proposed = json.loads(proposed_path.read_text(encoding="utf-8"))
    reviewed_paths = coverage.get("r13_task_owned_reviewed_paths", [])
    proposed_rows = proposed.get("proposed_commit_paths", [])
    if (
        coverage.get("status") != "PASS"
        or coverage.get("unclassified_path_count") != 0
        or coverage.get("r13_task_owned_reviewed_count") != len(reviewed_paths)
        or retrieval_test not in reviewed_paths
        or proposed.get("status") != "PASS"
        or proposed.get("proposed_commit_path_count") != len(proposed_rows)
        or {row.get("path") for row in proposed_rows} != set(reviewed_paths)
        or proposed.get("all_working_tree_bytes_equal_task_files") is not True
        or proposed.get("protected_e1_paths_absent") is not True
        or proposed.get("review_zip_paths_absent") is not True
        or proposed.get("user_owned_paths_absent") is not True
    ):
        raise RuntimeError("R13_REVIEW_SCOPE_COVERAGE_INCOMPLETE: audit contract")
    for row in proposed_rows:
        relative = row.get("path")
        bundled = task / relative
        if (
            not bundled.is_file()
            or f"task_files/{relative}" not in inventory_paths
            or row.get("byte_equal") is not True
            or row.get("working_tree_sha256") != sha256(bundled)
            or row.get("task_files_sha256") != sha256(bundled)
            or row.get("bytes") != bundled.stat().st_size
        ):
            raise RuntimeError(
                f"R13_REVIEW_SCOPE_COVERAGE_INCOMPLETE: proposed path={relative}"
            )
    reference_hashes = {
        "reports/week_03/results/critical_eval_v2_candidate_manifest.json": "f912798ae5c02c774702ae97bee8b2b4f6c6ab12b6534e1b2a3817a969b905ef",
        "data/evaluation/critical_eval_v2_mapping.jsonl": "cc9e82adbb97fd8054e58d3d6548ca03b15046bb37eca53ef9aa529dc4ec12f1",
        "data/evaluation/critical_eval_v2_support_judgments.jsonl": "585469d850a9e2d5514248709658e574dbfff7f54a0f13c99bcbb8cd2653017e",
    }
    for relative, expected in reference_hashes.items():
        if sha256(root / "references" / relative) != expected:
            raise RuntimeError(f"Candidate Revision 7 reference mismatch: {relative}")
    protected = {
        "reports/week_03/results/critical_eval_v2_runtime_execution_environment.json": (1750, "228a2f23c168092e41d0abebff7af468dc106b27a88e1bb6eef995af5f9739ca"),
        "reports/week_03/results/critical_eval_v2_execution_state.json": (227, "3908034af37fcdc11fa64d9f6024e775d24d435030246ee08ec4f48816f184ca"),
    }
    for relative, (size, expected) in protected.items():
        path = task / relative
        if not path.is_file() or path.stat().st_size != size or sha256(path) != expected:
            raise RuntimeError(f"preserved E1 evidence mismatch: {relative}")
    state = json.loads((task / "reports/week_03/results/critical_eval_v2_execution_state.json").read_text(encoding="utf-8"))
    if state.get("state") != "AUTHORIZED" or state.get("history") != []:
        raise RuntimeError("preserved E1 state/history mismatch")
    reset = json.loads((task / outputs["preauthorization_reset_plan"]).read_text(encoding="utf-8"))
    if reset.get("status") != "PLAN_ONLY_NOT_EXECUTED" or any(
        row.get("state") != "NOT_EXECUTED" for row in reset.get("steps", [])
    ):
        raise RuntimeError("preauthorization reset plan was executed")
    evaluation_paths = []
    for group in ("primary", "reproducibility_rerun"):
        evaluation_paths.extend(config["evaluation_outputs"][group].values())
    evaluation_paths.extend((
        config["evaluation_outputs"]["reproduction_comparison"],
        config["evaluation_outputs"]["final_summary"],
    ))
    if any((task / relative).exists() for relative in evaluation_paths):
        raise RuntimeError("primary/reproduction/evaluation output present")
    return {"status": "PASS", "files_verified": len(inventory["files"]),
            "readiness_revision": 13, "runtime_source_count": 18,
            "reviewed_dirty_path_count": len(reviewed_paths),
            "retrieval_test_bound": True,
            "authorization_path_count": 5,
            "reviewed_daily_report_path": authorization_config["reviewed_daily_report_path"],
            "environment_identity_sha256": contract["environment_identity_sha256"]}


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")


def _refresh_inventory(root: Path, relative: str) -> None:
    inventory_path = root / "detached_inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    path = root / relative
    row = next(item for item in inventory["files"] if item["path"] == relative)
    row["size"], row["sha256"] = path.stat().st_size, sha256(path)
    _write_json(inventory_path, inventory)


def _remove_inventory_row(root: Path, relative: str) -> None:
    inventory_path = root / "detached_inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory["files"] = [row for row in inventory["files"] if row["path"] != relative]
    _write_json(inventory_path, inventory)


def run_binding_negative_controls(root: Path) -> dict[str, object]:
    verify_bundle(root)
    results = []
    with tempfile.TemporaryDirectory(prefix="ea1_r13_bundle_negative_") as temporary:
        base = Path(temporary)
        for case in ("ENVIRONMENT_CONTRACT_ONLY", "AUTHORIZATION_BINDING_ONLY"):
            target = base / case
            shutil.copytree(root, target)
            task = target / "task_files"
            config = json.loads((task / "configs/evaluation/critical_eval_v2_execution.json").read_text(encoding="utf-8"))
            outputs = config["readiness_outputs"]
            if case == "ENVIRONMENT_CONTRACT_ONLY":
                relative = f"task_files/{outputs['environment_contract']}"
                path = target / relative
                payload = json.loads(path.read_text(encoding="utf-8"))
                payload["environment_identity"]["canonical_distribution_count"] += 1
                payload["environment_identity_sha256"] = stable_sha256(payload["environment_identity"])
            else:
                relative = f"task_files/{config['authorization']['candidate']}"
                path = target / relative
                payload = json.loads(path.read_text(encoding="utf-8"))
                payload["reviewed_environment_identity_sha256"] = "0" * 64
            _write_json(path, payload)
            _refresh_inventory(target, relative)
            try:
                verify_bundle(target)
            except RuntimeError as error:
                results.append({"case": case, "status": "REJECTED_AS_EXPECTED", "error": str(error)})
            else:
                raise RuntimeError(f"detached binding negative control passed: {case}")
    return {"status": "PASS", "cases": results, "case_count": len(results)}


def run_auth_date_negative_controls(root: Path) -> dict[str, object]:
    verify_bundle(root)
    results = []
    with tempfile.TemporaryDirectory(prefix="ea1_r13_auth_date_bundle_") as temporary:
        base = Path(temporary)
        for case in ("STALE_REVISION12", "BOTH_REVISION12_AND_REVISION13", "UNREVIEWED_REVISION14"):
            target = base / case
            shutil.copytree(root, target)
            relative = "task_files/configs/evaluation/critical_eval_v2_execution.json"
            path = target / relative
            config = json.loads(path.read_text(encoding="utf-8"))
            paths = config["authorization"]["allowed_authorization_commit_paths"]
            if case == "STALE_REVISION12":
                config["authorization"]["allowed_authorization_commit_paths"] = [
                    item.replace("2026-08-13", "2026-08-12") for item in paths
                ]
            elif case == "BOTH_REVISION12_AND_REVISION13":
                paths.append("reports/week_03/daily/2026-08-12.md")
            else:
                config["authorization"]["allowed_authorization_commit_paths"] = [
                    item.replace("2026-08-13", "2026-08-14") for item in paths
                ]
            _write_json(path, config)
            _refresh_inventory(target, relative)
            try:
                verify_bundle(target)
            except RuntimeError as error:
                results.append({"case": case, "status": "REJECTED_AS_EXPECTED", "error": str(error)})
            else:
                raise RuntimeError(f"detached auth-date negative control passed: {case}")
    return {"status": "PASS", "cases": results, "case_count": len(results)}


def run_review_scope_negative_controls(root: Path) -> dict[str, object]:
    verify_bundle(root)
    results = []
    with tempfile.TemporaryDirectory(prefix="ea1_r13_review_scope_") as temporary:
        base = Path(temporary)
        for case in ("OMITTED_RETRIEVAL_TEST", "UNREVIEWED_TASK_OWNED_DIRTY_PATH"):
            target = base / case
            shutil.copytree(root, target)
            if case == "OMITTED_RETRIEVAL_TEST":
                relative = "task_files/tests/test_retrieval_benchmark.py"
                (target / relative).unlink()
                _remove_inventory_row(target, relative)
            else:
                relative = "evidence/review_scope_coverage.json"
                path = target / relative
                coverage = json.loads(path.read_text(encoding="utf-8"))
                coverage["rows"].append({
                    "path": "tests/test_unreviewed_r13_task_owned.py",
                    "category": "UNCLASSIFIED",
                })
                coverage["dirty_path_count"] += 1
                coverage["unclassified_path_count"] = 1
                _write_json(path, coverage)
                _refresh_inventory(target, relative)
            try:
                verify_bundle(target)
            except RuntimeError as error:
                if "R13_REVIEW_SCOPE_COVERAGE_INCOMPLETE" not in str(error):
                    raise
                results.append({"case": case, "status": "REJECTED_AS_EXPECTED", "error": str(error)})
            else:
                raise RuntimeError(f"detached review-scope negative control passed: {case}")
    return {"status": "PASS", "cases": results, "case_count": len(results)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--run-binding-negative-controls", action="store_true")
    parser.add_argument("--run-auth-date-negative-controls", action="store_true")
    parser.add_argument("--run-review-scope-negative-controls", action="store_true")
    args = parser.parse_args()
    root = args.bundle_root.resolve()
    selected = sum((
        args.run_binding_negative_controls,
        args.run_auth_date_negative_controls,
        args.run_review_scope_negative_controls,
    ))
    if selected > 1:
        raise RuntimeError("select only one negative-control family")
    if args.run_binding_negative_controls:
        result = run_binding_negative_controls(root)
    elif args.run_auth_date_negative_controls:
        result = run_auth_date_negative_controls(root)
    elif args.run_review_scope_negative_controls:
        result = run_review_scope_negative_controls(root)
    else:
        result = verify_bundle(root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
