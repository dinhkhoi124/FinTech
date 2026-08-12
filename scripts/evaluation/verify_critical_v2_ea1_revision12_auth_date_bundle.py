"""Standalone standard-library verifier for the EA1 Revision-12 auth-date bundle."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


EXPECTED_R = "c7bc68bbef51684f6ff4ab7a672ca78af4cbbadd"
EXPECTED_ALLOWLIST = {
    "reports/week_03/results/critical_eval_v2_evaluation_authorization.json",
    "PROJECT_STATE.md",
    "TASKS.md",
    "reports/week_03/week_03_summary.md",
    "reports/week_03/daily/2026-08-12.md",
}
EXPECTED_CANDIDATE = {
    "reports/week_03/results/critical_eval_v2_candidate_manifest.json":
        "f912798ae5c02c774702ae97bee8b2b4f6c6ab12b6534e1b2a3817a969b905ef",
    "data/evaluation/critical_eval_v2_mapping.jsonl":
        "cc9e82adbb97fd8054e58d3d6548ca03b15046bb37eca53ef9aa529dc4ec12f1",
    "data/evaluation/critical_eval_v2_support_judgments.jsonl":
        "585469d850a9e2d5514248709658e574dbfff7f54a0f13c99bcbb8cd2653017e",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    inventory = json.loads((root / "detached_inventory.json").read_text(encoding="utf-8"))
    actual = {
        item.relative_to(root).as_posix(): {"size": item.stat().st_size, "sha256": sha256(item)}
        for item in root.rglob("*")
        if item.is_file() and item.name != "detached_inventory.json"
    }
    expected = {row["path"]: {"size": row["size"], "sha256": row["sha256"]} for row in inventory["files"]}
    assert actual == expected, "detached inventory membership/hash mismatch"
    paths = (root / "exact_task_pathspec.txt").read_text(encoding="utf-8").splitlines()
    assert len(paths) == len(set(paths)) and paths, "invalid exact task pathspec"
    assert all((root / "task_files" / path).is_file() for path in paths), "missing task file"
    config = json.loads((root / "task_files/configs/evaluation/critical_eval_v2_execution.json").read_text(encoding="utf-8"))
    topology = json.loads((root / "task_files/configs/evaluation/critical_eval_v2_authorization_topology.json").read_text(encoding="utf-8"))
    assert config["readiness_revision"] == topology["readiness_revision"] == 12
    assert config["candidate_revision"] == 7
    assert set(config["authorization"]["allowed_authorization_commit_paths"]) == EXPECTED_ALLOWLIST
    assert "reports/week_03/daily/2026-08-11.md" not in EXPECTED_ALLOWLIST
    assert not (root / "task_files/reports/week_03/results/critical_eval_v2_evaluation_authorization.json").exists()
    binding = json.loads((root / "evidence/revision11_commit_binding.json").read_text(encoding="utf-8"))
    assert binding["readiness_commit_R"] == EXPECTED_R
    for relative, expected_hash in EXPECTED_CANDIDATE.items():
        assert sha256(root / "references" / relative) == expected_hash, relative
    state_text = (root / "task_files/PROJECT_STATE.md").read_text(encoding="utf-8")
    assert "evaluation_authorized=false" in state_text
    assert "critical_evaluated=false" in state_text
    assert "model_verdict=NOT_ESTABLISHED" in state_text
    print(f"PASS: detached EA1 Revision-12 bundle inventory={len(actual)}")
    print(f"PASS: exact task paths={len(paths)}; readiness R={EXPECTED_R}")
    print("PASS: authorization daily=2026-08-12 only; 2026-08-11 rejected")
    print("PASS: Candidate Revision 7 manifest/mapping/Pass-B immutable")
    print("PASS: evaluation_authorized=false; critical_evaluated=false")
    print("PASS: model_verdict=NOT_ESTABLISHED; authorization record A absent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
