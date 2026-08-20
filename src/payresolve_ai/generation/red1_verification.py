"""Fail-closed clean-development verification boundary for RED1-RCV1.

This module intentionally does not call ``pipeline_v3.run_nonlocked_regression``.
That legacy helper loads two historical memberships implicitly, including a
consumed W3-001-CR1 holdout.  RCV1 instead binds one exact W3-001 development
membership and every artifact that the clean replay may open.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from .context import eligible_chunks
from .gate import build_idf
from .pipeline_v3 import normalized_result_bytes, run_case_v3
from .support_v2 import build_canonical_idf


AUTHORIZED_RED1_W3_001_MEMBERSHIP = (
    "EXPLICIT_NON_LOCKED_W3_001_DEVELOPMENT_ONLY"
)
AUTHORIZED_RED1_W3_001_MEMBERSHIP_PATH = (
    "data/evaluation/evidence_gate_dev_v1.jsonl"
)


class Red1VerificationBoundaryError(RuntimeError):
    """Raised before opening an artifact outside the RED1 clean allowlist."""


# Exact identities captured for the clean RCV1 replay.  W3-001 resolved output
# is used for query text so the broader W2 mapping (which contains locked rows)
# is never opened.
AUTHORIZED_RED1_ARTIFACT_SHA256: dict[str, str] = {
    "configs/generation/grounded_pipeline_v1.json":
        "3d9f7841e42634375fe548f691bdea8fe17535c50cb05d3a005f80290ed78988",
    "configs/generation/grounded_pipeline_v2.json":
        "9319799a704ddbc82e824f7351adc3852672e4b277efea2fc0bc552ef4f518f2",
    "configs/generation/grounded_pipeline_v3.json":
        "bca279ea11feffbde8b3fa569c3ea2a076d94664f6aa4e473a770b19c3428d09",
    "configs/generation/banking_support_lexicon_v2.json":
        "156314762b13f55437d947f72f4a8bd2d12943c3843292efffbc5ae59a2e1ef8",
    "configs/retrieval/kb_v1_r0_r1.json":
        "baf74f600b27279ce8fe2d3370d1a9179cc76f07e67597201ef0bc5a03a8929d",
    "data/kb/kb_v1.jsonl":
        "e14aa83ed37c8de1ab3fc0fb8a0cae50f1b1e14083b774252a687bc5f0cf67c4",
    AUTHORIZED_RED1_W3_001_MEMBERSHIP_PATH:
        "5101f5d337ea85c9b71b284485b871ec55c4eabaae43088bd5da65bb9c8f0ebb",
    "reports/week_03/results/grounded_pipeline_dev_outputs.jsonl":
        "ef405bec24bfac9723b930ac0ed4bd6a3c14d139b0ca3c0fb450e219f86bc118",
    "reports/week_03/results/evidence_gate_dev_rankings.jsonl":
        "d4decc72a999d7210ec632770d3d3aaa0c9c1c660f66cfc0279101406a76fba6",
}


def _normalized_relative_path(path: str | Path) -> str:
    raw = str(path).replace("\\", "/")
    pure = PurePosixPath(raw)
    if pure.is_absolute() or ".." in pure.parts:
        raise Red1VerificationBoundaryError("absolute or escaping artifact path denied")
    normalized = pure.as_posix()
    if normalized in {"", "."}:
        raise Red1VerificationBoundaryError("empty artifact path denied")
    return normalized


def authorize_red1_w3_001_membership(
    membership_id: str,
    membership_path: str | Path,
) -> str:
    """Authorize the sole RCV1 W3-001 membership before any file open."""

    normalized = _normalized_relative_path(membership_path)
    if membership_id != AUTHORIZED_RED1_W3_001_MEMBERSHIP:
        raise Red1VerificationBoundaryError(
            f"unauthorized RED1 membership identifier: {membership_id}"
        )
    if normalized != AUTHORIZED_RED1_W3_001_MEMBERSHIP_PATH:
        raise Red1VerificationBoundaryError(
            f"unauthorized RED1 membership path: {normalized}"
        )
    return normalized


class ExactArtifactReader:
    """Read only exact hash-bound allowlisted paths and record opened paths."""

    def __init__(
        self,
        root: Path,
        *,
        opener: Callable[[Path], bytes] | None = None,
    ) -> None:
        self.root = root.resolve()
        self._opener = opener or (lambda path: path.read_bytes())
        self.opened_paths: list[str] = []

    def read_bytes(self, relative_path: str | Path) -> bytes:
        normalized = _normalized_relative_path(relative_path)
        expected_sha256 = AUTHORIZED_RED1_ARTIFACT_SHA256.get(normalized)
        if expected_sha256 is None:
            raise Red1VerificationBoundaryError(
                f"artifact is outside exact RED1 allowlist: {normalized}"
            )
        candidate = self.root.joinpath(*PurePosixPath(normalized).parts)
        if candidate.is_symlink():
            raise Red1VerificationBoundaryError(
                f"symlink artifact denied before open: {normalized}"
            )
        payload = self._opener(candidate)
        actual_sha256 = hashlib.sha256(payload).hexdigest()
        if actual_sha256 != expected_sha256:
            raise Red1VerificationBoundaryError(
                f"hash drift for RED1 artifact: {normalized}"
            )
        self.opened_paths.append(normalized)
        return payload

    def read_json(self, relative_path: str | Path) -> dict[str, Any]:
        value = json.loads(self.read_bytes(relative_path).decode("utf-8"))
        if not isinstance(value, dict):
            raise Red1VerificationBoundaryError("expected JSON object")
        return value

    def read_jsonl(self, relative_path: str | Path) -> list[dict[str, Any]]:
        rows = [
            json.loads(line)
            for line in self.read_bytes(relative_path).decode("utf-8").splitlines()
            if line
        ]
        if not all(isinstance(row, dict) for row in rows):
            raise Red1VerificationBoundaryError("expected JSONL objects")
        return rows


def _validate_clean_contract(
    v1: dict[str, Any],
    v2: dict[str, Any],
    v3: dict[str, Any],
) -> None:
    expected = {
        "v1_retrieval": "configs/retrieval/kb_v1_r0_r1.json",
        "v1_kb": "data/kb/kb_v1.jsonl",
        "v1_rankings": "reports/week_03/results/evidence_gate_dev_rankings.jsonl",
        "v3_lexicon": "configs/generation/banking_support_lexicon_v2.json",
    }
    actual = {
        "v1_retrieval": v1.get("retrieval_config"),
        "v1_kb": v1.get("kb_documents"),
        "v1_rankings": (v1.get("outputs") or {}).get("rankings"),
        "v3_lexicon": v3.get("lexicon_config"),
    }
    if actual != expected:
        raise Red1VerificationBoundaryError("clean verification config path drift")
    if v3.get("default_mode") != "TARGET_AWARE":
        raise Red1VerificationBoundaryError("RED1 target-aware mode required")
    if v2.get("evaluation_as_of_date") != "2026-07-28":
        raise Red1VerificationBoundaryError("historical W3-001 as-of date drift")


def run_authorized_w3_001_development(
    root: Path,
    *,
    membership_id: str = AUTHORIZED_RED1_W3_001_MEMBERSHIP,
    membership_path: str | Path = AUTHORIZED_RED1_W3_001_MEMBERSHIP_PATH,
    reader: ExactArtifactReader | None = None,
) -> dict[str, Any]:
    """Run RED1 on exactly the original non-locked W3-001 development set."""

    authorized_path = authorize_red1_w3_001_membership(
        membership_id, membership_path
    )
    safe_reader = reader or ExactArtifactReader(root)

    v1 = safe_reader.read_json("configs/generation/grounded_pipeline_v1.json")
    v2 = safe_reader.read_json("configs/generation/grounded_pipeline_v2.json")
    v3 = safe_reader.read_json("configs/generation/grounded_pipeline_v3.json")
    _validate_clean_contract(v1, v2, v3)
    lexicon = safe_reader.read_json(v3["lexicon_config"])
    retrieval = safe_reader.read_json(v1["retrieval_config"])
    membership = safe_reader.read_jsonl(authorized_path)
    resolved_outputs = safe_reader.read_jsonl(
        "reports/week_03/results/grounded_pipeline_dev_outputs.jsonl"
    )
    ranking_rows = safe_reader.read_jsonl(v1["outputs"]["rankings"])
    documents = safe_reader.read_jsonl(v1["kb_documents"])

    if len(membership) != 20:
        raise Red1VerificationBoundaryError("W3-001 development membership drift")
    membership_by_id = {row["query_id"]: row for row in membership}
    resolved_by_id = {row["query_id"]: row for row in resolved_outputs}
    rankings_by_id = {row["query_id"]: row["rankings"] for row in ranking_rows}
    expected_ids = set(membership_by_id)
    if (
        len(expected_ids) != 20
        or set(resolved_by_id) != expected_ids
        or set(rankings_by_id) != expected_ids
    ):
        raise Red1VerificationBoundaryError("resolved development membership mismatch")

    historical_as_of = date.fromisoformat(v2["evaluation_as_of_date"])
    chunks = eligible_chunks(
        documents,
        historical_as_of,
        retrieval["corpus"]["chunk_text_template"],
    )
    raw_idf = build_idf(chunks, v3["tokenizer"]["stopwords"])
    canonical_idf = build_canonical_idf(
        chunks, lexicon, v3["tokenizer"]["stopwords"]
    )

    queries: list[dict[str, Any]] = []
    for query_id in sorted(expected_ids):
        membership_row = membership_by_id[query_id]
        resolved = resolved_by_id[query_id]
        queries.append(
            {
                "query_id": query_id,
                "query_text": resolved["query_text"],
                "expected_response_type": membership_row["expected_response_type"],
                "case_type": membership_row["case_type"],
                "source": membership_row["source"],
            }
        )

    outputs = [
        run_case_v3(
            row,
            rankings_by_id[row["query_id"]],
            chunks,
            raw_idf,
            canonical_idf,
            v3,
            lexicon,
        )
        for row in queries
    ]
    output_by_id = {row["query_id"]: row for row in outputs}
    answerable = [
        output_by_id[row["query_id"]]
        for row in queries
        if row["expected_response_type"] == "ANSWER"
    ]
    safety = [
        output_by_id[row["query_id"]]
        for row in queries
        if row["expected_response_type"] == "ABSTAIN_ESCALATE"
    ]
    reason_codes = Counter(
        output["response_plan"]["reason_codes"][0]
        for output in answerable
        if output["answer_strategy"] == "ABSTAIN"
    )
    unsafe_standard = sum(
        output["answer_strategy"] == "STANDARD" for output in safety
    )
    ineligible = sum(
        evidence["status"] != "APPROVED"
        or date.fromisoformat(evidence["effective_date"]) > historical_as_of
        or (
            evidence.get("expiry_date") is not None
            and historical_as_of >= date.fromisoformat(evidence["expiry_date"])
        )
        for output in outputs
        for evidence in output["selected_evidence"]
    )
    generation_failures = sum(
        any(str(code).startswith("GENERATION_OR_CITATION_FAILURE:") for code in output["response_plan"]["reason_codes"])
        for output in outputs
    )
    normalized_sha256 = hashlib.sha256(
        normalized_result_bytes(outputs)
    ).hexdigest()

    summary = {
        "membership_id": membership_id,
        "membership_path": authorized_path,
        "answerable_cases": len(answerable),
        "safe_standard_answers": sum(
            output["answer_strategy"] == "STANDARD" for output in answerable
        ),
        "answerable_abstentions": sum(
            output["answer_strategy"] == "ABSTAIN" for output in answerable
        ),
        "answerable_corrective_answers": sum(
            output["answer_strategy"] == "CORRECTIVE" for output in answerable
        ),
        "answerable_abstention_reason_codes": dict(sorted(reason_codes.items())),
        "safety_probes": len(safety),
        "safe_safety_probe_outcomes": sum(
            output["answer_strategy"] in {"ABSTAIN", "CORRECTIVE"}
            for output in safety
        ),
        "unsafe_standard_safety_answers": unsafe_standard,
        "citation_failures": generation_failures,
        "ineligible_selections": ineligible,
        "normalized_sha256": normalized_sha256,
        "opened_paths": safe_reader.opened_paths,
        "forbidden_file_open_calls": 0,
    }
    return {"summary": summary, "outputs": outputs}
