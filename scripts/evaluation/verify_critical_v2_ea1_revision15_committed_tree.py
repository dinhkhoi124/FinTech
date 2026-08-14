"""Fail-closed committed-tree closure checks for EA1 Revision 15 F3."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable


BASE_COMMIT = "5e89ec1ed2b7284ed5f263be674e3cb20e0facaf"
CANDIDATE_PATH = (
    "reports/week_03/results/"
    "critical_eval_v2_evaluation_authorization_candidate.json"
)


class CommittedTreeClosureError(RuntimeError):
    """Raised when reviewed bytes are not closed by a proposed commit tree."""


def git_bytes(root: Path, revision: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"{revision}:{path}"],
        capture_output=True,
    )
    if result.returncode:
        raise CommittedTreeClosureError(
            f"committed path unavailable: {revision}:{path}"
        )
    return result.stdout


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def candidate_at(root: Path, revision: str) -> dict[str, Any]:
    return json.loads(git_bytes(root, revision, CANDIDATE_PATH))


def audit_committed_tree(
    root: Path, revision: str, expected: dict[str, str]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path, reviewed_sha in sorted(expected.items()):
        try:
            committed_sha = sha256(git_bytes(root, revision, path))
        except CommittedTreeClosureError:
            committed_sha = None
        rows.append(
            {
                "path": path,
                "expected_reviewed_sha": reviewed_sha,
                "committed_sha": committed_sha,
                "committed_matches_review": committed_sha == reviewed_sha,
            }
        )
    return rows


def verify_committed_tree(
    root: Path, revision: str, expected: dict[str, str]
) -> list[dict[str, Any]]:
    rows = audit_committed_tree(root, revision, expected)
    failures = [row["path"] for row in rows if not row["committed_matches_review"]]
    if failures:
        raise CommittedTreeClosureError(
            "committed readiness byte mismatch: " + ", ".join(failures)
        )
    return rows


def changed_paths(root: Path, parent: str, revision: str) -> set[str]:
    output = subprocess.check_output(
        ["git", "-C", str(root), "diff", "--name-only", "-z", parent, revision]
    )
    return {item.decode("utf-8") for item in output.split(b"\0") if item}


def verify_proposed_scope(
    root: Path,
    parent: str,
    revision: str,
    proposed_paths: Iterable[str],
    hash_bound_paths: Iterable[str],
) -> dict[str, Any]:
    actual = changed_paths(root, parent, revision)
    proposed = set(proposed_paths)
    hash_bound = set(hash_bound_paths)
    omitted = sorted((actual & hash_bound) - proposed)
    extra = sorted(actual - proposed)
    declared_but_unchanged = sorted(proposed - actual)
    if omitted:
        raise CommittedTreeClosureError(
            "hash-bound changed path omitted from proposed scope: "
            + ", ".join(omitted)
        )
    if extra:
        raise CommittedTreeClosureError(
            "unreviewed extra committed path: " + ", ".join(extra)
        )
    if declared_but_unchanged:
        raise CommittedTreeClosureError(
            "proposed path absent from committed diff: "
            + ", ".join(declared_but_unchanged)
        )
    return {
        "status": "PASS",
        "actual_count": len(actual),
        "proposed_count": len(proposed),
        "hash_bound_changed_count": len(actual & hash_bound),
        "omitted": [],
        "extra": [],
    }
