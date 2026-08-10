"""Build the detached W3-002-CR1 Revision-7 pre-evaluation review bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


PREDECESSOR_COMMIT = "d27de987d0eb7a942c88590eec9a30bdd6ee33d8"
PREDECESSOR_MANIFEST_SHA256 = "2f42fb4ff7159ef2735ce88418b0dbfcc414b0091476f1882a83d13e807002ad"
COV1_BUNDLE_SHA256 = "b804fa12a4bc6f12e3852552358a29af9e071e916c92b22959fefc6ff8a629ff"

EXACT_EXCLUDES = {
    ".gitignore", "AGENTS.md", "CODEX_BOOTSTRAP_PROMPT.md",
    "ANTIGRAVITY_BOOTSTRAP_PROMPT.md", "CHATGPT_SUCCESSION_PROMPT.md",
    "reports/week_03/results/critical_eval_v2_revision_4_corrections.json",
    "reports/week_03/results/critical_eval_v2_revision_5_corrections.json",
    "scripts/generate_slide_deck.py",
}
PREFIX_EXCLUDES = ("docs/product_v2/", "review/", "presentation/")


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def git_show(root: Path, relative: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{PREDECESSOR_COMMIT}:{relative}"], cwd=root,
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout


def task_pathspec(root: Path) -> list[str]:
    raw = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=root, check=True, stdout=subprocess.PIPE,
    ).stdout.decode("utf-8", errors="surrogateescape")
    paths = []
    for entry in raw.split("\0"):
        if not entry:
            continue
        relative = entry[3:].replace("\\", "/")
        if " -> " in relative:
            relative = relative.split(" -> ", 1)[1]
        if relative in EXACT_EXCLUDES or relative.startswith(PREFIX_EXCLUDES):
            continue
        paths.append(relative)
    result = sorted(set(paths))
    allowed = (
        "PROJECT_STATE.md", "TASKS.md", "configs/evaluation/critical_eval_v2.json",
        "data/evaluation/critical_eval_v2_", "reports/week_03/daily/2026-08-10.md",
        "reports/week_03/decisions/W3-002-CR1_COV1_",
        "reports/week_03/experiments/W3-002-CR1_revision_7_",
        "reports/week_03/results/critical_eval_v2_", "reports/week_03/week_03_summary.md",
        "scripts/evaluation/author_critical_v2_revision_7.py",
        "scripts/evaluation/build_critical_v2_revision_7_review_bundle.py",
        "scripts/evaluation/week3_critical_v2.py",
        "src/payresolve_ai/evaluation/critical_v2.py",
        "tests/test_critical_eval_v2.py", "tests/test_critical_eval_v2_revision_7.py",
    )
    unexpected = [path for path in result if not path.startswith(allowed)]
    if unexpected:
        raise RuntimeError(f"unexpected task path(s): {unexpected}")
    return result


STANDALONE = r'''from __future__ import annotations
import hashlib, json, sys
from collections import Counter
from pathlib import Path

ROOT=Path(sys.argv[1] if len(sys.argv)>1 else ".").resolve()
PRED_HASH="2f42fb4ff7159ef2735ce88418b0dbfcc414b0091476f1882a83d13e807002ad"
COV_HASH="b804fa12a4bc6f12e3852552358a29af9e071e916c92b22959fefc6ff8a629ff"
EXPECTED_KEYS={
 ("Q_V2_A_TRD01","POL_TRANSFER_DECLINED_001#eligibility"),
 ("Q_V2_A_TRD01","RUN_TRANSFER_DECLINED_001#checks"),
 ("Q_V2_A_TRR02","ESC_TRANSFER_RECIPIENT_001#trigger"),
 ("Q_V2_A_CSU03","ESC_CASH_UNRECOG_001#safe_handoff"),
}
USER_EXACT={".gitignore","AGENTS.md","CODEX_BOOTSTRAP_PROMPT.md","ANTIGRAVITY_BOOTSTRAP_PROMPT.md","CHATGPT_SUCCESSION_PROMPT.md"}
USER_PREFIX=("docs/product_v2/","review/","presentation/")
EA1={
"configs/evaluation/critical_eval_v2_authorization_topology.json","configs/evaluation/critical_eval_v2_execution.json",
"configs/evaluation/critical_eval_v2_execution_state_machine.json","configs/evaluation/critical_eval_v2_metric_contract.json",
"configs/evaluation/schemas/critical_eval_v2_evaluation.schema.json","configs/evaluation/schemas/critical_eval_v2_raw_output.schema.json",
"data/evaluation/critical_eval_v2_control_plane_boundary_rules.jsonl","data/evaluation/critical_eval_v2_obligation_evaluator_rules.jsonl",
"data/evaluation/critical_eval_v2_safety_evaluator_rules.jsonl","docs/evaluation/W3-002-CR1-EA1_execution_readiness.md",
"reports/week_03/daily/2026-08-07.md","reports/week_03/experiments/W3-002-CR1-EA1_execution_readiness.md",
"reports/week_03/results/critical_eval_v2_evaluation_authorization_candidate.json","reports/week_03/results/critical_eval_v2_execution_environment.json",
"reports/week_03/results/critical_eval_v2_execution_readiness_validation.json","reports/week_03/results/critical_eval_v2_future_command_plan.json",
"reports/week_03/results/critical_eval_v2_obligation_revision_6_semantic_delta.json","reports/week_03/results/critical_eval_v2_obligation_sentence_semantic_audit.jsonl",
"reports/week_03/results/critical_eval_v2_runtime_asset_manifest.json","reports/week_03/results/critical_eval_v2_runtime_payload_manifest.json",
"scripts/evaluation/verify_critical_v2_execution_readiness_bundle.py","scripts/evaluation/week3_critical_v2_execution.py",
"src/payresolve_ai/evaluation/critical_v2_execution.py","tests/test_critical_v2_execution_readiness.py",
}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def js(p): return json.loads(p.read_text(encoding="utf-8"))
def jl(p): return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]

inventory=js(ROOT/"bundle_inventory.json")
actual={p.relative_to(ROOT).as_posix():{"size":p.stat().st_size,"sha256":sha(p)} for p in ROOT.rglob("*") if p.is_file() and p.name!="bundle_inventory.json"}
assert actual==inventory["files"]
task_paths=(ROOT/"exact_task_pathspec.txt").read_text(encoding="utf-8").splitlines()
assert task_paths and all((ROOT/"task_files"/p).is_file() for p in task_paths)
assert not (set(task_paths)&USER_EXACT) and not any(p.startswith(USER_PREFIX) for p in task_paths)
assert not (set(task_paths)&EA1)

candidate=ROOT/"candidate_package"
manifest_path=candidate/"reports/week_03/results/critical_eval_v2_candidate_manifest.json"
manifest=js(manifest_path)
assert manifest["candidate_revision"]==7 and manifest["predecessor_candidate_revision"]==6
assert manifest["predecessor_candidate_commit"]=="d27de987d0eb7a942c88590eec9a30bdd6ee33d8"
assert manifest["predecessor_manifest_sha256"]==PRED_HASH and manifest["cov1_bundle_sha256"]==COV_HASH
assert all(sha(candidate/p)==h for p,h in manifest["artifact_sha256"].items())

pred=ROOT/"references/revision_6"
pred_manifest=pred/"reports/week_03/results/critical_eval_v2_candidate_manifest.json"
assert sha(pred_manifest)==PRED_HASH
pm=js(pred_manifest)
assert len(pm["artifact_sha256"])==18 and all(sha(pred/p)==h for p,h in pm["artifact_sha256"].items())
assert sha(ROOT/"references/W3-002-CR1_complete_cover_consistency_review_bundle.zip")==COV_HASH

delta=js(candidate/"reports/week_03/results/critical_eval_v2_revision_7_semantic_delta.json")
assert delta["changed_semantic_pass_b_rows"]==4 and delta["unexpected_semantic_pass_b_rows"]==0
assert {(r["query_id"],r["evidence_id"]) for r in delta["semantic_changes"]}==EXPECTED_KEYS
model=js(candidate/"reports/week_03/results/critical_eval_v2_revision_7_model_input_comparison.json")
assert model["query_count"]==60 and model["changed_count"]==0 and model["all_identical"] is True
pass_a=jl(candidate/"data/evaluation/critical_eval_v2_pass_a.jsonl")
assert Counter((r["intended_response_type"],r.get("intended_answer_subtype")) for r in pass_a)==Counter({("ANSWER","STANDARD"):40,("ANSWER","SAFE_CORRECTIVE"):15,("ABSTAIN_ESCALATE",None):5})
proof=js(candidate/"reports/week_03/results/critical_eval_v2_revision_7_complete_cover_derivation.json")
assert proof["total_complete_covers"]==92 and all(proof["invalid_revision_6_covers_absent"].values()) and all(proof["replacement_covers_present"].values())
assert manifest["senior_semantic_review_approved"] is False and manifest["evaluation_authorized"] is False
assert manifest["critical_evaluated"] is False and manifest["model_verdict"]=="NOT_ESTABLISHED"
assert all(manifest[k] is False for k in ("model_loaded","encoder_loaded","retrieval_executed","generation_executed","critical_pipeline_executed"))
task_names=set(task_paths)
assert not any("critical_eval_v2_v0_outputs" in p or "critical_eval_v2_v1_outputs" in p or "critical_eval_v2_v2_outputs" in p for p in task_names)
print("PASS: Revision-7 detached pre-evaluation review bundle")
print("PASS: predecessor revision 6 manifest and 18/18 artifacts")
print("PASS: COV1 hash; exact four Pass-B semantic changes; zero unexpected")
print("PASS: 60/60 model inputs; 40/15/5 distribution; 92 complete covers")
print("PASS: invalid covers absent and required replacement covers present")
print("PASS: revision 7 not Senior-approved; evaluation_authorized=false; no evaluation outputs")
print("PASS: rejected EA1 and user-owned paths absent")
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cov1-bundle", type=Path, required=True)
    parser.add_argument("--isolated-run", type=Path, required=True)
    args = parser.parse_args()
    root, output, cov1, isolated = args.root.resolve(), args.output.resolve(), args.cov1_bundle.resolve(), args.isolated_run.resolve()
    if sha_file(cov1) != COV1_BUNDLE_SHA256:
        raise RuntimeError("COV1 bundle hash mismatch")
    if subprocess.run(["git","diff","--cached","--name-only"],cwd=root,text=True,stdout=subprocess.PIPE,check=True).stdout.strip():
        raise RuntimeError("staged files are prohibited")
    paths = task_pathspec(root)
    stage = Path(tempfile.mkdtemp(prefix="W3-002-CR1_revision_7_bundle_", dir=output.parent))
    try:
        for relative in paths:
            source, destination = root/relative, stage/"task_files"/relative
            if not source.is_file(): raise RuntimeError(f"missing task file: {relative}")
            destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source,destination)
        (stage/"exact_task_pathspec.txt").write_text("\n".join(paths)+"\n",encoding="utf-8",newline="\n")

        config=json.loads((root/"configs/evaluation/critical_eval_v2.json").read_text(encoding="utf-8"))
        candidate_paths=set(config["candidate_artifacts"])|{config["outputs"]["candidate_manifest"]}
        for relative in sorted(candidate_paths):
            destination=stage/"candidate_package"/relative; destination.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(root/relative,destination)

        pred_manifest_bytes=git_show(root,"reports/week_03/results/critical_eval_v2_candidate_manifest.json")
        if sha_bytes(pred_manifest_bytes)!=PREDECESSOR_MANIFEST_SHA256: raise RuntimeError("predecessor manifest mismatch")
        pred_manifest=json.loads(pred_manifest_bytes.decode("utf-8"))
        pred_paths=set(pred_manifest["artifact_sha256"])|{"reports/week_03/results/critical_eval_v2_candidate_manifest.json"}
        for relative in sorted(pred_paths):
            destination=stage/"references/revision_6"/relative; destination.parent.mkdir(parents=True,exist_ok=True); destination.write_bytes(git_show(root,relative))
        refs=stage/"references"; refs.mkdir(exist_ok=True); shutil.copy2(cov1,refs/cov1.name)

        evidence=stage/"evidence"; evidence.mkdir()
        for name in ("isolated_full_suite.txt","isolated_full_suite_rerun.txt","harness_manifest.json","exact_task_pathspec.txt"):
            source=isolated/name
            if source.is_file(): shutil.copy2(source,evidence/("harness_"+name if name=="exact_task_pathspec.txt" else name))
        cleanup=json.loads(Path(r"C:\Users\Administrator\AppData\Local\Temp\r7_cleanup_preflight.json").read_text(encoding="utf-8"))
        write_json(evidence/"rejected_ea1_cleanup_summary.json",{
            "ea1_zip_sha256":cleanup["ea1_zip_sha256"],"task_path_count":cleanup["task_path_count"],
            "tracked_restored":cleanup["tracked_modified_count"],"untracked_removed":cleanup["task_owned_untracked_count"],
            "user_owned_out_of_scope_file_hash_count_preserved":len(cleanup["outside_file_hashes"]),
            "head":cleanup["head"],"origin_main":cleanup["origin_main"],"staged_files":0,
        })
        (stage/"standalone_verify.py").write_text(STANDALONE,encoding="utf-8",newline="\n")

        def refresh_inventory():
            files={p.relative_to(stage).as_posix():{"size":p.stat().st_size,"sha256":sha_file(p)} for p in sorted(stage.rglob("*")) if p.is_file() and p.name!="bundle_inventory.json"}
            write_json(stage/"bundle_inventory.json",{"task_id":"W3-002-CR1","candidate_revision":7,"files":files,"inventoried_payloads":len(files)})
        refresh_inventory()
        verify=subprocess.run([sys.executable,str(stage/"standalone_verify.py"),str(stage)],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (evidence/"standalone_verifier_output.txt").write_text(verify.stdout,encoding="utf-8",newline="\n")
        refresh_inventory()
        verify=subprocess.run([sys.executable,str(stage/"standalone_verify.py"),str(stage)],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (evidence/"standalone_verifier_output.txt").write_text(verify.stdout,encoding="utf-8",newline="\n")
        refresh_inventory()
        subprocess.run([sys.executable,str(stage/"standalone_verify.py"),str(stage)],check=True)

        if output.exists(): output.unlink()
        with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
            for path in sorted(stage.rglob("*")):
                if path.is_file(): archive.write(path,path.relative_to(stage).as_posix())
        inventory=json.loads((stage/"bundle_inventory.json").read_text(encoding="utf-8"))
        with zipfile.ZipFile(output) as archive: entries=len(archive.namelist())
        print(json.dumps({"status":"PASS","output":str(output),"sha256":sha_file(output),"size":output.stat().st_size,"entries":entries,"files":entries,"inventory":inventory["inventoried_payloads"],"task_path_count":len(paths),"standalone_output":verify.stdout.splitlines()},indent=2))
    finally:
        shutil.rmtree(stage)
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main())
