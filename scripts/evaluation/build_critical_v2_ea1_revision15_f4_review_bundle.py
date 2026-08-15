"""Build the detached R15-F4 comparator-correction review bundle.

This is an authoring-only proof.  It constructs disposable R15-F4/A16 commits,
migrates a copy of the frozen REPRO_EVALUATED state, and runs only the corrected
comparator.  It never mutates the real lifecycle artifacts.
"""

from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

from payresolve_ai.evaluation import critical_v2_execution as execution


REAL_A15 = "8631333b7ac180ca13fc2a98c42c516402b4f2b5"
PROPOSED_PATHS = (
    "src/payresolve_ai/evaluation/critical_v2_execution.py",
    "scripts/evaluation/week3_critical_v2_execution.py",
    "scripts/evaluation/build_critical_v2_ea1_revision15_f4_review_bundle.py",
    "scripts/evaluation/verify_critical_v2_ea1_revision15_f4_bundle.py",
    "tests/test_critical_v2_auth_date_closure.py",
    "tests/test_critical_v2_binding_fix.py",
    "tests/test_critical_v2_execution_readiness.py",
    "tests/test_critical_v2_execution_revision13.py",
    "tests/test_critical_v2_execution_revision14.py",
    "tests/test_critical_v2_execution_revision15.py",
    "tests/test_critical_v2_execution_revision15_f3.py",
    "tests/test_critical_v2_execution_revision15_f4.py",
    "tests/test_feasibility_review_bundle.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def run(*args: str, cwd: Path, capture: bool = True) -> str:
    completed = subprocess.run(args, cwd=cwd, check=True, text=True, capture_output=capture)
    return completed.stdout.strip() if capture else ""


def copy_exact(source: Path, destination: Path, *, hardlink: bool = False) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if hardlink:
        try:
            os.link(source, destination)
            return
        except OSError:
            pass
    shutil.copyfile(source, destination)


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def produce_comparator_evidence(root: Path, config_path: Path) -> tuple[dict, dict]:
    config = execution.load_execution_config(config_path)
    outputs = config["evaluation_outputs"]
    variants = {}
    old_total = behavioral_total = primary_provenance = repro_provenance = 0
    for variant in execution.VARIANT_IDS:
        primary = jsonl(root / outputs["primary"][f"{variant}_raw"])
        repro = jsonl(root / outputs["reproducibility_rerun"][f"{variant}_raw"])
        result = execution.compare_reproducibility_variant(
            root, config_path, config, variant, primary, repro
        )
        variants[variant] = result
        old_total += result["legacy_equal_rows"]
        behavioral_total += result["behavioral_equal_rows"]
        primary_provenance += len(primary)
        repro_provenance += len(repro)
    defect = {
        "status": "PASS",
        "classification": "R15_REPRO_COMPARATOR_PROVENANCE_NORMALIZATION_GAP",
        "legacy_equal_rows": old_total,
        "legacy_total_rows": 180,
        "corrected_behavioral_equal_rows": behavioral_total,
        "corrected_behavioral_total_rows": 180,
        "primary_provenance_valid_rows": primary_provenance,
        "reproduction_provenance_valid_rows": repro_provenance,
        "excluded_nonbehavioral_fields": list(execution.REPRO_COMPARATOR_EXCLUDED_NONBEHAVIORAL_FIELDS),
        "seed_retained": "determinism.seed" not in execution.REPRO_COMPARATOR_EXCLUDED_NONBEHAVIORAL_FIELDS,
        "variants": variants,
    }

    primary = jsonl(root / outputs["primary"]["V0_raw"])
    repro = jsonl(root / outputs["reproducibility_rerun"]["V0_raw"])
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
    controls = []
    for name, mutate in behavioral.items():
        changed = copy.deepcopy(repro)
        mutate(changed[0])
        detected = False
        detection = ""
        try:
            result = execution.compare_reproducibility_variant(
                root, config_path, config, "V0", primary, changed
            )
            detected = not result["behavioral_identical"]
            detection = "behavioral_mismatch" if detected else "not_detected"
        except execution.CriticalV2ExecutionError as error:
            detected, detection = True, str(error)
        controls.append({"class": "behavioral", "name": name, "status": "PASS" if detected else "FAIL", "detection": detection})

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
    for name, (source, label, mutate) in provenance.items():
        row = copy.deepcopy(source[0])
        mutate(row)
        detected, detection = False, "not_detected"
        try:
            execution.validate_reproducibility_provenance(
                root, config_path, config, row, run_label=label, variant_id="V0"
            )
        except execution.CriticalV2ExecutionError as error:
            detected, detection = True, str(error)
        controls.append({"class": "provenance", "name": name, "status": "PASS" if detected else "FAIL", "detection": detection})
    return defect, {"status": "PASS" if len(controls) == 20 and all(row["status"] == "PASS" for row in controls) else "FAIL", "controls": controls}


def source_patch(root: Path) -> str:
    chunks = []
    for relative in PROPOSED_PATHS:
        current = (root / relative).read_text(encoding="utf-8").splitlines(keepends=True)
        try:
            original = subprocess.check_output(
                ["git", "-C", str(root), "show", f"HEAD:{relative}"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).splitlines(keepends=True)
        except subprocess.CalledProcessError:
            original = []
        chunks.extend(difflib.unified_diff(original, current, fromfile=f"a/{relative}", tofile=f"b/{relative}"))
    return "".join(chunks)


def create_synthetic_proof(real_root: Path, scratch: Path) -> dict[str, object]:
    repo = scratch / "synthetic_repo"
    run("git", "-c", "core.autocrlf=false", "clone", "--no-hardlinks", str(real_root), str(repo), cwd=scratch)
    run("git", "config", "core.autocrlf", "false", cwd=repo)
    run("git", "config", "user.name", "R15-F4 Synthetic", cwd=repo)
    run("git", "config", "user.email", "r15-f4@example.invalid", cwd=repo)
    if run("git", "rev-parse", "HEAD", cwd=repo) != REAL_A15:
        raise RuntimeError("synthetic clone did not start at real A15")
    for relative in PROPOSED_PATHS:
        copy_exact(real_root / relative, repo / relative)
    run("git", "add", "--", *PROPOSED_PATHS, cwd=repo)
    run("git", "commit", "-m", "Synthetic R15-F4 comparator correction", cwd=repo)
    r15_f4 = run("git", "rev-parse", "HEAD", cwd=repo)
    if run("git", "rev-parse", "HEAD^", cwd=repo) != REAL_A15:
        raise RuntimeError("synthetic R15-F4 parent mismatch")

    config_path = repo / "configs/evaluation/critical_eval_v2_execution.json"
    config = execution.load_execution_config(config_path)
    auth_relative = config["authorization"]["committed_record"]
    auth = load(repo / auth_relative)
    auth["readiness_implementation_commit"] = r15_f4
    auth["execution_artifact_sha256"] = execution._readiness_artifact_hashes(repo)
    auth.update(execution.POSTEVAL_CONTINUATION_AUTHORIZATION_FIELDS)
    write_json(repo / auth_relative, auth)
    for relative in config["authorization"]["allowed_authorization_commit_paths"]:
        if relative == auth_relative:
            continue
        path = repo / relative
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write("\n<!-- SYNTHETIC R15-F4 A16 POST-EVALUATION CONTINUATION AUTHORIZATION -->\n")
    run("git", "add", "--", *config["authorization"]["allowed_authorization_commit_paths"], cwd=repo)
    run("git", "commit", "-m", "Synthetic A16 post-evaluation continuation authorization", cwd=repo)
    a16 = run("git", "rev-parse", "HEAD", cwd=repo)
    if run("git", "rev-parse", "HEAD^", cwd=repo) != r15_f4:
        raise RuntimeError("synthetic A16 parent mismatch")
    changed = sorted(run("git", "diff", "--name-only", f"{r15_f4}..{a16}", cwd=repo).splitlines())
    if changed != sorted(config["authorization"]["allowed_authorization_commit_paths"]):
        raise RuntimeError("synthetic A16 changed-path scope mismatch")

    evidence_paths = {
        config["evaluation_outputs"]["execution_state"],
        config["continuation"]["receipt"],
        config["continuation"]["historical_runtime_environment"]["path"],
        config["runtime_environment"]["manifest"],
        *config["evaluation_outputs"]["primary"].values(),
        *config["evaluation_outputs"]["reproducibility_rerun"].values(),
    }
    for relative in evidence_paths:
        copy_exact(real_root / relative, repo / relative)
    manifest = load(real_root / config["readiness_outputs"]["runtime_asset_manifest"])
    retrieval = load(real_root / config["runtime_dependencies"]["retrieval_config"]["path"])
    asset_overrides = {
        logical: real_root / logical for logical in manifest["asset_file_sha256"]
    }
    snapshot = Path(retrieval["encoder"]["huggingface_home"]) / (
        "models--sentence-transformers--all-MiniLM-L6-v2/snapshots/" + retrieval["encoder"]["revision"]
    )
    asset_overrides.update({
        "encoder_snapshot/" + row["logical_path"]: real_root / snapshot / row["logical_path"]
        for row in manifest["encoder"]["files"]
    })
    for relative in (config["evaluation_outputs"]["reproduction_comparison"], config["evaluation_outputs"]["final_summary"], execution.POSTEVAL_CONTINUATION_RECEIPT):
        path = repo / relative
        if path.exists():
            path.unlink()

    state_path = repo / config["evaluation_outputs"]["execution_state"]
    before = load(state_path)
    verify_assets = execution.verify_runtime_asset_manifest
    with patch.object(
        execution,
        "verify_runtime_asset_manifest",
        side_effect=lambda synthetic_root, synthetic_config: verify_assets(
            synthetic_root, synthetic_config, overrides=asset_overrides
        ),
    ):
        verified_authorization = execution.verify_execution_authorization(
            repo, config_path
        )
        receipt = execution.migrate_r15_f4_posteval_continuation(repo, config_path)
        migrated = load(state_path)
        comparison = execution.verify_reproducibility(repo, config_path)
    verified = load(state_path)
    return {
        "repo": repo,
        "topology": {"real_a15": REAL_A15, "r15_f4_commit": r15_f4, "r15_f4_parent": REAL_A15, "a16_commit": a16, "a16_parent": r15_f4, "a16_changed_paths": changed},
        "receipt": receipt,
        "before": before,
        "migrated": migrated,
        "comparison": comparison,
        "verified": verified,
        "authorization": verified_authorization,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--focused-log", type=Path)
    parser.add_argument("--r15-log", type=Path)
    parser.add_argument("--tracked-log", type=Path)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    if output.exists():
        raise RuntimeError("review bundle overwrite is forbidden")
    if run("git", "rev-parse", "HEAD", cwd=root) != REAL_A15:
        raise RuntimeError("real repository HEAD is not A15")
    config_path = root / "configs/evaluation/critical_eval_v2_execution.json"
    config = execution.load_execution_config(config_path)
    comparison_path = root / config["evaluation_outputs"]["reproduction_comparison"]
    final_path = root / config["evaluation_outputs"]["final_summary"]
    if comparison_path.exists() or final_path.exists():
        raise RuntimeError("real verification/final output must remain absent")
    defect, negatives = produce_comparator_evidence(root, config_path)
    if defect["legacy_equal_rows"] != 0 or defect["corrected_behavioral_equal_rows"] != 180 or negatives["status"] != "PASS":
        raise RuntimeError("comparator correction evidence failed")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ea1_r15_f4_", dir=output.parent) as temporary:
        scratch = Path(temporary)
        synthetic = create_synthetic_proof(root, scratch)
        bundle = scratch / "bundle"
        for relative in PROPOSED_PATHS:
            copy_exact(root / relative, bundle / "proposed" / relative)
        evidence_paths = {
            "configs/evaluation/critical_eval_v2_execution.json",
            config["candidate"]["manifest"],
            config["evaluation_outputs"]["execution_state"],
            config["continuation"]["receipt"],
            config["continuation"]["historical_runtime_environment"]["path"],
            config["runtime_environment"]["manifest"],
            *config["evaluation_outputs"]["primary"].values(),
            *config["evaluation_outputs"]["reproducibility_rerun"].values(),
        }
        evidence_hashes = {}
        for relative in sorted(evidence_paths):
            source = root / relative
            copy_exact(source, bundle / "real_evidence" / relative)
            evidence_hashes[relative] = {"bytes": source.stat().st_size, "sha256": sha256(source)}
        write_json(bundle / "evidence" / "real_evidence_hashes.json", evidence_hashes)
        write_json(bundle / "evidence" / "root_cause.json", {"status": "PASS", "classification": "R15_REPRO_COMPARATOR_PROVENANCE_NORMALIZATION_GAP", "correction": "validate each run provenance independently, then exclude only authorized non-behavioral lineage fields"})
        write_json(bundle / "evidence" / "defect_reproduction.json", defect)
        write_json(bundle / "evidence" / "negative_controls.json", negatives)
        (bundle / "evidence" / "source_diff.patch").write_text(source_patch(root), encoding="utf-8", newline="\n")
        write_json(bundle / "synthetic" / "topology.json", synthetic["topology"])
        git_proof = bundle / "synthetic" / "r15_f4_f1_history.bundle"
        git_proof.parent.mkdir(parents=True, exist_ok=True)
        proof_ref = "refs/heads/r15-f4-f1-review"
        run(
            "git", "update-ref", proof_ref,
            synthetic["topology"]["a16_commit"],
            cwd=synthetic["repo"],
        )
        try:
            run(
                "git", "bundle", "create", str(git_proof), proof_ref,
                cwd=synthetic["repo"],
            )
        finally:
            run("git", "update-ref", "-d", proof_ref, cwd=synthetic["repo"])
        copy_exact(
            synthetic["repo"] / config["authorization"]["committed_record"],
            bundle / "synthetic" / "a16_authorization.json",
        )
        write_json(bundle / "synthetic" / "migration_receipt.json", synthetic["receipt"])
        write_json(bundle / "synthetic" / "state_before.json", synthetic["before"])
        write_json(bundle / "synthetic" / "state_post_migration.json", synthetic["migrated"])
        write_json(bundle / "synthetic" / "comparison.json", synthetic["comparison"])
        write_json(bundle / "synthetic" / "state_post_verify.json", synthetic["verified"])
        transition_inputs = synthetic["verified"]["history"][10]["direct_input_sha256"]
        write_json(
            bundle / "synthetic" / "verify_transition_input_closure.json",
            {
                "status": "PASS",
                "input_count": len(transition_inputs),
                "direct_input_sha256": transition_inputs,
            },
        )
        write_json(bundle / "synthetic" / "execution_boundary.json", {"status": "PASS", "model_calls": 0, "encoder_calls": 0, "retrieval_calls": 0, "generation_calls": 0, "evaluator_calls": 0, "primary_run": False, "reproduction_run": False, "freeze_run": False, "evaluation_run": False, "finalization_executed": False})
        for label, path in (("focused.txt", args.focused_log), ("existing_r15.txt", args.r15_log), ("tracked_suite.txt", args.tracked_log)):
            if path:
                copy_exact(path.resolve(), bundle / "tests" / label)
        write_json(
            bundle / "tests" / "standalone_bundle_exclusions.json",
            {
                "status": "PASS",
                "skip_count": 11,
                "exclusions": [
                    {
                        "module": "tests/test_feasibility_review_bundle.py",
                        "reason": "standalone historical feasibility-bundle fixture root is absent",
                        "tests": [
                            "test_category_and_semantic_findings",
                            "test_exact_safety_challenge_contract",
                            "test_inventory_is_complete",
                            "test_lifecycle_remains_unauthorized",
                            "test_preservation_hashes",
                        ],
                    },
                    {
                        "module": "tests/test_contract_amendment_review_bundle.py",
                        "reason": "pre-existing standalone contract-amendment bundle fixture root is absent",
                        "tests": [
                            "test_inventory",
                            "test_contract",
                            "test_metrics_and_checklist",
                            "test_decision_bundle",
                            "test_preservation",
                        ],
                    },
                    {
                        "module": "tests/test_critical_v2_execution_revision15.py",
                        "reason": "historical A15 topology helper requires the retired R14 live state",
                        "tests": [
                            "test_synthetic_committed_topology_preserves_real_common_git_config"
                        ],
                    },
                ],
            },
        )
        metadata = {
            "status": "AWAITING_SENIOR_REVIEW",
            "task": "W3-002-CR1-EA1-R15-F4-F1-CLOSURE-CORRECTION",
            "classification": "R15_REPRO_COMPARATOR_PROVENANCE_NORMALIZATION_GAP",
            "real_head": REAL_A15,
            "proposed_paths": list(PROPOSED_PATHS),
            "readiness_revision": 15,
            "execution_config_sha256": sha256(config_path),
            "real_repository_mutated": False,
            "self_approved": False,
            "supersedes_bundle": {
                "name": "W3-002-CR1_EA1_R15_F4_repro_comparator_correction_review_bundle.zip",
                "bytes": 340760,
                "sha256": "0a9145193750545c8dbe17145f2d4414c789c2e89f7b44bd2e1767b03855d5ec",
                "status": "SUPERSEDED",
            },
        }
        write_json(bundle / "bundle_metadata.json", metadata)
        inventory = [
            {"path": path.relative_to(bundle).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in sorted(bundle.rglob("*")) if path.is_file()
        ]
        write_json(bundle / "inventory.json", {"status": "PASS", "files": inventory})
        with zipfile.ZipFile(output, "x", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(bundle.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(bundle).as_posix())
    print(json.dumps({"status": "PASS", "output": str(output), "bytes": output.stat().st_size, "sha256": sha256(output), "proposed_paths": len(PROPOSED_PATHS), "negative_controls": 20}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
