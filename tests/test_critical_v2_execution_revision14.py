"""Revision-14 final-authorization verifier hardening regressions."""

from __future__ import annotations

import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from payresolve_ai.evaluation import critical_v2_execution as execution


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/evaluation/critical_eval_v2_execution.json"


class CriticalV2ExecutionRevision14Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = execution.load_execution_config(CONFIG_PATH)
        cls.candidate = json.loads(
            (ROOT / cls.config["authorization"]["candidate"]).read_text(encoding="utf-8")
        )

    def _final_authorization(self) -> dict[str, object]:
        authorization = copy.deepcopy(self.candidate)
        authorization.update(
            {
                "authorization_status": "AUTHORIZED_FOR_PRIMARY_EXECUTION",
                "evaluation_authorized": True,
                "readiness_commit_binding": (
                    "BOUND_TO_REVIEWED_READINESS_IMPLEMENTATION_COMMIT"
                ),
                "readiness_implementation_commit": "1" * 40,
                "senior_authorization_claimed": True,
                "senior_authorization_verdict": "APPROVE_EXECUTION",
                **execution.CONTINUATION_AUTHORIZATION_FIELDS,
            }
        )
        return authorization

    def test_r14_identity_is_active_and_candidate_remains_non_authorized(self) -> None:
        self.assertEqual(self.config["readiness_revision"], 15)
        self.assertEqual(self.candidate["readiness_revision"], 15)
        self.assertEqual(self.candidate["authorization_status"], "AWAITING_SENIOR_REVIEW")
        self.assertFalse(self.candidate["evaluation_authorized"])
        self.assertFalse(self.candidate["senior_authorization_claimed"])
        self.assertEqual(
            self.candidate["readiness_commit_binding"],
            "DEFERRED_TO_SEPARATE_AUTHORIZATION_RECORD",
        )

    def test_real_a15_authorization_rejects_unreviewed_f4_source_bytes(self) -> None:
        with self.assertRaisesRegex(
            execution.CriticalV2ExecutionError,
            "authorization execution source/config/test hash mismatch",
        ):
            execution._validate_authorization_payload(
                ROOT, CONFIG_PATH, self.config, self._final_authorization()
            )

    def test_final_authorization_field_mutations_reject(self) -> None:
        cases = {
            "AUTH-FIELD-01": ("readiness_revision", 13),
            "AUTH-FIELD-02": ("readiness_revision", 12),
            "AUTH-FIELD-03": ("authorization_status", "AWAITING_SENIOR_REVIEW"),
            "AUTH-FIELD-04": (
                "readiness_commit_binding",
                "DEFERRED_TO_SEPARATE_AUTHORIZATION_RECORD",
            ),
            "AUTH-FIELD-05": ("senior_authorization_claimed", False),
            "AUTH-FIELD-06": ("semantic_review_approved", False),
            "AUTH-FIELD-07": ("candidate_revision", 8),
            "AUTH-FIELD-08": ("task_id", "WRONG"),
            "AUTH-FIELD-09": ("authorization_topology", "WRONG"),
            "AUTH-FIELD-10": ("senior_authorization_verdict", "REJECT"),
            "AUTH-FIELD-11": ("evaluation_authorized", False),
        }
        for case, (field, value) in cases.items():
            with self.subTest(case=case):
                authorization = self._final_authorization()
                authorization[field] = value
                with self.assertRaises(execution.CriticalV2ExecutionError):
                    execution._validate_authorization_payload(
                        ROOT, CONFIG_PATH, self.config, authorization
                    )

    def _topology_case(
        self, changed: set[str], *, wrong_parent: bool = False
    ) -> tuple[Path, tempfile.TemporaryDirectory[str], dict[str, object], dict[str, object]]:
        temporary = tempfile.TemporaryDirectory(prefix="ea1_r14_topology_")
        repo = Path(temporary.name)
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "EA1 R14 Test"], cwd=repo, check=True)
        subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=repo, check=True)
        allowed = {
            "reports/week_03/results/critical_eval_v2_evaluation_authorization.json",
            "PROJECT_STATE.md",
            "TASKS.md",
            "reports/week_03/week_03_summary.md",
            "reports/week_03/daily/2026-08-13.md",
        }
        initial = allowed | changed | {"exec.py"}
        for relative in initial:
            path = repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("R14 readiness\n", encoding="utf-8", newline="\n")
        subprocess.run(["git", "add", "--all"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "R14"], cwd=repo, check=True, capture_output=True)
        readiness = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True
        ).strip()
        for relative in changed:
            (repo / relative).write_text("A14 authorization\n", encoding="utf-8", newline="\n")
        subprocess.run(["git", "add", "--all"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "A14"], cwd=repo, check=True, capture_output=True)
        authorization = {
            "readiness_implementation_commit": "0" * 40 if wrong_parent else readiness,
            "execution_artifact_sha256": {"exec.py": execution.sha256_file(repo / "exec.py")},
        }
        config = {"authorization": {"allowed_authorization_commit_paths": sorted(allowed)}}
        return repo, temporary, authorization, config

    def test_exact_five_topology_positive_and_negatives(self) -> None:
        authorization_path = (
            "reports/week_03/results/critical_eval_v2_evaluation_authorization.json"
        )
        exact = {
            authorization_path,
            "PROJECT_STATE.md",
            "TASKS.md",
            "reports/week_03/week_03_summary.md",
            "reports/week_03/daily/2026-08-13.md",
        }
        cases = {
            "AUTH-TOPO-01": (exact, False, True),
            "AUTH-TOPO-02": ({authorization_path}, False, False),
            "AUTH-TOPO-03": (exact - {"PROJECT_STATE.md"}, False, False),
            "AUTH-TOPO-04": (exact - {"TASKS.md"}, False, False),
            "AUTH-TOPO-05": (exact - {"reports/week_03/week_03_summary.md"}, False, False),
            "AUTH-TOPO-06": (exact - {"reports/week_03/daily/2026-08-13.md"}, False, False),
            "AUTH-TOPO-07": (exact | {"src/payresolve_ai/extra.py"}, False, False),
            "AUTH-TOPO-08": (exact | {"configs/evaluation/extra.json"}, False, False),
            "AUTH-TOPO-09": (
                (exact - {"reports/week_03/daily/2026-08-13.md"})
                | {"reports/week_03/daily/2026-08-12.md"},
                False,
                False,
            ),
            "AUTH-TOPO-10": (exact | {"reports/week_03/daily/2026-08-12.md"}, False, False),
            "AUTH-TOPO-11": (
                (exact - {"reports/week_03/daily/2026-08-13.md"})
                | {"reports/week_03/daily/2026-08-14.md"},
                False,
                False,
            ),
            "AUTH-TOPO-12": (exact, True, False),
        }
        for case, (changed, wrong_parent, should_pass) in cases.items():
            with self.subTest(case=case):
                repo, temporary, authorization, config = self._topology_case(
                    changed, wrong_parent=wrong_parent
                )
                try:
                    if should_pass:
                        execution._verify_authorization_topology(
                            repo, config, authorization, authorization_path
                        )
                    else:
                        with self.assertRaises(execution.CriticalV2ExecutionError):
                            execution._verify_authorization_topology(
                                repo, config, authorization, authorization_path
                            )
                finally:
                    temporary.cleanup()


if __name__ == "__main__":
    unittest.main()
