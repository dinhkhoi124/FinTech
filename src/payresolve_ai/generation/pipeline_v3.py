"""Versioned target-aware grounded pipeline and development-only harness."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path
from time import perf_counter_ns
from typing import Any, Sequence

from .citations import CitationError, verify_draft
from .context import render_context
from .corrective_v1 import (
    assemble_corrective_objectives,
    corrective_objective_categories,
    mandatory_corrective_groups,
)
from .gate import build_idf
from .routing_v3 import (
    RequestedTargetStatus,
    ResponsePlan,
    ResponseTarget,
    assess_requested_target,
    derive_corrective_scope_anchor,
    select_supported_standard_evidence,
)
from .support_v2 import build_canonical_idf
from .targeted_extractive import TargetedExtractiveGenerator
from .types import EvidenceChunk, GenerationContext


class PipelineV3Error(RuntimeError):
    pass


def _eligible(row: dict[str, Any], as_of: date) -> bool:
    if row.get("status") != "APPROVED":
        return False
    effective = date.fromisoformat(row["effective_date"])
    expiry = date.fromisoformat(row["expiry_date"]) if row.get("expiry_date") else None
    return effective <= as_of and (expiry is None or as_of < expiry)


def attach_runtime_candidate_pool(
    rankings: Sequence[dict[str, Any]],
    chunks: Sequence[dict[str, Any]],
    as_of: date,
    max_candidates: int,
) -> list[EvidenceChunk]:
    """Filter first, then take an explicitly bounded runtime candidate pool."""
    if max_candidates < 1:
        raise PipelineV3Error("candidate pool bound must be positive")
    by_id = {row["chunk_id"]: row for row in chunks}
    evidence: list[EvidenceChunk] = []
    for ranking in rankings:
        chunk = by_id.get(ranking["chunk_id"])
        if chunk is None or not _eligible(chunk, as_of):
            continue
        evidence.append(EvidenceChunk(
            evidence_id=chunk["chunk_id"],
            document_id=chunk["document_id"],
            section_id=chunk["section_id"],
            title=chunk.get("title") or chunk.get("text", "").split("\n", 1)[0],
            document_type=chunk["document_type"],
            status=chunk["status"],
            version=chunk["version"],
            effective_date=chunk["effective_date"],
            expiry_date=chunk.get("expiry_date"),
            intent_scope=tuple(chunk["intent_scope"]),
            heading=chunk["heading"],
            content=chunk["content"],
            score=float(ranking["score"]),
            rank=len(evidence) + 1,
        ))
        if len(evidence) == max_candidates:
            break
    return evidence


def build_response_plan(
    query: str,
    standard_evidence: Sequence[EvidenceChunk],
    canonical_idf: dict[str, float],
    config: dict[str, Any],
    lexicon: dict[str, Any],
    *,
    assessment: dict[str, Any] | None = None,
    corrective_pool: Sequence[EvidenceChunk] = (),
    scope_anchor: Sequence[str] = (),
    scope_anchor_basis: Sequence[str] = (),
) -> ResponsePlan:
    standard_evidence = tuple(standard_evidence[: config["standard"]["max_evidence"]])
    assessment = assessment or assess_requested_target(
        query, standard_evidence, lexicon, canonical_idf,
        config["tokenizer"]["stopwords"], config["standard"],
    )
    status = assessment["status"]
    reason = str(assessment["reason"])
    if status is RequestedTargetStatus.SUPPORTED:
        selected_standard = select_supported_standard_evidence(
            query,
            standard_evidence,
            lexicon,
            canonical_idf,
            config["tokenizer"]["stopwords"],
            config["standard"],
        )
        dominant_scope = set(standard_evidence[0].intent_scope) if standard_evidence else set()
        selected_list = list(selected_standard)
        for item in standard_evidence:
            if len(selected_list) == config["standard"]["max_evidence"]:
                break
            if item not in selected_list and dominant_scope & set(item.intent_scope):
                selected_list.append(item)
        selected_standard = tuple(selected_list)
        if selected_standard:
            return ResponsePlan(ResponseTarget.STANDARD, (reason,), status, selected_standard, (), None)
        return ResponsePlan(ResponseTarget.ABSTAIN, (reason, "NO_TARGET_SUPPORTING_STANDARD_SELECTION"), RequestedTargetStatus.UNSUPPORTED, (), (), None)
    if status is RequestedTargetStatus.BLOCKED_CONTROL_PLANE:
        if not scope_anchor:
            return ResponsePlan(
                ResponseTarget.ABSTAIN,
                (reason, "NO_SAFE_CORRECTIVE_SCOPE_ANCHOR"),
                status, (), (), None,
            )
        coherent_pool = tuple(item for item in corrective_pool if set(scope_anchor) & set(item.intent_scope))
        boundary, objectives, selected, corrective_reasons = assemble_corrective_objectives(
            reason,
            coherent_pool,
            config["corrective"],
        )
        if objectives:
            return ResponsePlan(
                ResponseTarget.CORRECTIVE,
                (reason, *corrective_reasons),
                status,
                selected,
                objectives,
                boundary,
                tuple(scope_anchor),
                tuple(scope_anchor_basis),
            )
        return ResponsePlan(
            ResponseTarget.ABSTAIN, (reason, *corrective_reasons), status, (), (), boundary,
            tuple(scope_anchor), tuple(scope_anchor_basis),
        )
    return ResponsePlan(ResponseTarget.ABSTAIN, (reason,), status, (), (), None)


def _abstain(query: dict[str, Any], plan: ResponsePlan, config: dict[str, Any], retrieved: list[EvidenceChunk]) -> dict[str, Any]:
    return {
        "query_id": query["query_id"],
        "query_text": query["query_text"],
        "response_type": "ABSTAIN_ESCALATE",
        "answer_strategy": "ABSTAIN",
        "answer_text": config["safe_fallback"],
        "claims": [],
        "citations": [],
        "retrieved_evidence": [item.to_dict() for item in retrieved],
        "selected_evidence": [],
        "response_plan": plan.to_dict(),
        "versions": {"pipeline_version": config["pipeline_version"], "gate_version": config["gate_version"], "generator_version": config["generator_version"]},
    }


def run_case_v3(
    query: dict[str, Any],
    rankings: Sequence[dict[str, Any]],
    chunks: Sequence[dict[str, Any]],
    raw_idf: dict[str, float],
    canonical_idf: dict[str, float],
    config: dict[str, Any],
    lexicon: dict[str, Any],
    *,
    mode: str = "TARGET_AWARE",
) -> dict[str, Any]:
    """Run V3. ``mode`` cannot bypass requested-target safety or routing."""
    as_of = date.fromisoformat(config["evaluation_as_of_date"])
    standard_pool = attach_runtime_candidate_pool(
        rankings,
        chunks,
        as_of,
        config["standard"]["max_evidence"],
    )
    assessment = assess_requested_target(
        query["query_text"], standard_pool, lexicon, canonical_idf,
        config["tokenizer"]["stopwords"], config["standard"],
    )
    pool = standard_pool
    scope_anchor: tuple[str, ...] = ()
    scope_anchor_basis: tuple[str, ...] = ()
    corrective_pool: list[EvidenceChunk] = []
    if assessment["status"] is RequestedTargetStatus.BLOCKED_CONTROL_PLANE:
        anchor = derive_corrective_scope_anchor(
            query["query_text"], standard_pool, lexicon, config["tokenizer"]["stopwords"]
        )
        scope_anchor = tuple(anchor["anchor"])
        scope_anchor_basis = tuple(anchor["basis"])
        if scope_anchor:
            from payresolve_ai.retrieval.runtime import discover_corrective_candidates

            eligible_corpus = [row for row in chunks if _eligible(row, as_of)]
            category_map = {
                row["chunk_id"]: corrective_objective_categories(f"{row['heading']} {row['content']}")
                for row in eligible_corpus
            }
            corrective_rankings = discover_corrective_candidates(
                str(assessment["reason"]), scope_anchor,
                mandatory_corrective_groups(str(assessment["reason"])),
                rankings, eligible_corpus, category_map,
                config["corrective"]["candidate_pool_max_chunks"],
                max_scanned_chunks=config["corrective"]["candidate_source_scan_max_chunks"],
            )
            corrective_pool = attach_runtime_candidate_pool(
                corrective_rankings, eligible_corpus, as_of,
                config["corrective"]["candidate_pool_max_chunks"],
            )
            pool = corrective_pool
    plan = build_response_plan(
        query["query_text"], standard_pool, canonical_idf, config, lexicon,
        assessment=assessment, corrective_pool=corrective_pool,
        scope_anchor=scope_anchor, scope_anchor_basis=scope_anchor_basis,
    )
    if plan.target is ResponseTarget.ABSTAIN:
        response = _abstain(query, plan, config, pool)
        response["diagnostic_mode"] = mode
        return response

    generator = TargetedExtractiveGenerator(
        config["tokenizer"]["stopwords"],
        config["standard"]["max_claims"],
        config["generator"]["sentence_overlap_weight"],
        config["generator"]["chunk_score_weight"],
    )
    selected = list(plan.selected_evidence)
    try:
        if plan.target is ResponseTarget.STANDARD:
            draft = generator.generate_standard(
                query["query_text"],
                selected,
                GenerationContext(query["query_id"], render_context(query["query_text"], selected), raw_idf),
            )
        else:
            draft = generator.generate_corrective(plan.factual_objectives, selected)
        factual_answer = verify_draft(draft, selected, as_of)
    except (CitationError, KeyError, TypeError, ValueError) as error:
        failed = ResponsePlan(
            ResponseTarget.ABSTAIN,
            (*plan.reason_codes, f"GENERATION_OR_CITATION_FAILURE:{type(error).__name__}"),
            plan.requested_target_status,
            (),
            (),
            plan.control_plane_boundary,
        )
        return _abstain(query, failed, config, pool)

    answer = factual_answer if plan.target is ResponseTarget.STANDARD else f"{plan.control_plane_boundary} {factual_answer}"
    return {
        "query_id": query["query_id"],
        "query_text": query["query_text"],
        "response_type": "ANSWER",
        "answer_strategy": plan.target.value,
        "answer_text": answer,
        "claims": draft.claims,
        "citations": draft.citations,
        "retrieved_evidence": [item.to_dict() for item in pool],
        "selected_evidence": [item.to_dict() for item in selected],
        "response_plan": plan.to_dict(),
        "diagnostic_mode": mode,
        "versions": {"pipeline_version": config["pipeline_version"], "gate_version": config["gate_version"], "generator_version": config["generator_version"]},
    }


def normalized_result_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def load_v3_configuration(root: Path, config_path: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    lexicon = json.loads((root / config["lexicon_config"]).read_text(encoding="utf-8"))
    dev = json.loads((root / config["development_config"]).read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in (root / dev["dataset_path"]).read_text(encoding="utf-8").splitlines() if line]
    if config["default_mode"] != "TARGET_AWARE" or "ALWAYS_ANSWER" in json.dumps(config):
        raise PipelineV3Error("V3 production mode must be target-aware without global answer bypass")
    if len(rows) != dev["expected_cases"] or any(row.get("use_expected_target_as_runtime_input") for row in rows):
        raise PipelineV3Error("development fixture contract mismatch")
    return config, lexicon, rows


def _fixture_chunks(row: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    chunks: list[dict[str, Any]] = []
    rankings: list[dict[str, Any]] = []
    ordinary_ids = set(row.get("standard_ranking_ids", ()))
    for index, evidence in enumerate(row["candidate_evidence"], start=1):
        chunk = {**evidence, "chunk_id": evidence["evidence_id"], "text": f"{evidence['title']}\n{evidence['heading']}\n{evidence['content']}"}
        chunks.append(chunk)
        if not ordinary_ids or evidence["evidence_id"] in ordinary_ids:
            rankings.append({"chunk_id": evidence["evidence_id"], "score": evidence["score"], "rank": len(rankings) + 1})
    return chunks, rankings


def run_synthetic_behavior_suite(root: Path, config_path: Path) -> dict[str, Any]:
    config, lexicon, rows = load_v3_configuration(root, config_path)
    all_chunks = [chunk for row in rows for chunk in _fixture_chunks(row)[0] if _eligible(chunk, date.fromisoformat(config["evaluation_as_of_date"]))]
    raw_idf = build_idf(all_chunks, config["tokenizer"]["stopwords"])
    canonical_idf = build_canonical_idf(all_chunks, lexicon, config["tokenizer"]["stopwords"])
    outputs: list[dict[str, Any]] = []
    latency: dict[str, list[int]] = {"STANDARD": [], "CORRECTIVE": [], "ABSTAIN": []}
    for row in rows:
        chunks, rankings = _fixture_chunks(row)
        started = perf_counter_ns()
        output = run_case_v3(row, rankings, chunks, raw_idf, canonical_idf, config, lexicon)
        elapsed = perf_counter_ns() - started
        latency[output["answer_strategy"]].append(elapsed)
        outputs.append(output)
    expected = {row["query_id"]: row["expected_target"] for row in rows}
    mismatches = [row["query_id"] for row in outputs if row["answer_strategy"] != expected[row["query_id"]]]
    citation_failures = 0
    for output in outputs:
        if output["response_type"] != "ANSWER":
            continue
        selected = [EvidenceChunk(**{**item, "intent_scope": tuple(item["intent_scope"])}) for item in output["selected_evidence"]]
        try:
            from .types import GenerationDraft
            verify_draft(GenerationDraft(output["claims"], output["citations"]), selected, date.fromisoformat(config["evaluation_as_of_date"]))
        except (CitationError, KeyError, TypeError, ValueError):
            citation_failures += 1
    result = {
        "task_id": config["task_id"],
        "development_only": True,
        "independent_evaluation": False,
        "status": "PASS" if not mismatches and not citation_failures else "FAIL",
        "cases": len(outputs),
        "target_counts": dict(sorted(Counter(row["answer_strategy"] for row in outputs).items())),
        "mismatches": mismatches,
        "citation_failures": citation_failures,
        "ineligible_selected_count": sum(any(item["status"] != "APPROVED" for item in row["selected_evidence"]) for row in outputs),
        "outputs": outputs,
        "latency_ns": {
            target: {"samples": len(values), "min": min(values) if values else None, "max": max(values) if values else None, "mean": sum(values) / len(values) if values else None}
            for target, values in latency.items()
        },
        "bounded_candidate_pool": config["corrective"]["candidate_pool_max_chunks"],
        "network_calls": 0,
    }
    result["normalized_sha256"] = hashlib.sha256(normalized_result_bytes({k: v for k, v in result.items() if k not in {"latency_ns", "normalized_sha256"}})).hexdigest()
    return result


def _nonlocked_metrics(queries: list[dict[str, Any]], outputs: list[dict[str, Any]], as_of: date) -> dict[str, Any]:
    by_id = {row["query_id"]: row for row in queries}
    positives = [row for row in outputs if by_id[row["query_id"]]["expected_response_type"] == "ANSWER"]
    negatives = [row for row in outputs if by_id[row["query_id"]]["expected_response_type"] == "ABSTAIN_ESCALATE"]
    relevant = 0
    wrong = 0
    citation_failures = 0
    for output in outputs:
        if output["response_type"] != "ANSWER":
            continue
        selected = [EvidenceChunk(**{**item, "intent_scope": tuple(item["intent_scope"])}) for item in output["selected_evidence"]]
        try:
            from .types import GenerationDraft
            verify_draft(GenerationDraft(output["claims"], output["citations"]), selected, as_of)
        except (CitationError, KeyError, TypeError, ValueError):
            citation_failures += 1
        query = by_id[output["query_id"]]
        if query["expected_response_type"] != "ANSWER":
            continue
        cited = {row["evidence_id"] for row in output["citations"]}
        gold = set(query.get("gold_evidence_ids", []))
        acceptable = set(query.get("acceptable_evidence_ids", []))
        success = gold <= cited if query.get("evidence_requirement") == "multi_document" else bool(cited & (gold | acceptable))
        relevant += int(success)
        wrong += int(not success)
    unsafe = sum(row["answer_strategy"] == "STANDARD" for row in negatives)
    negative_abstains = sum(row["answer_strategy"] == "ABSTAIN" for row in negatives)
    answer_count = sum(row["response_type"] == "ANSWER" for row in outputs)
    return {
        "cases": len(outputs),
        "positive_cases": len(positives),
        "negative_cases": len(negatives),
        "positive_grounded_resolution_count": relevant,
        "positive_grounded_resolution_recall": relevant / len(positives) if positives else None,
        "positive_wrong_evidence_answer_count": wrong,
        "unnecessary_abstention_count": len(positives) - relevant,
        "negative_abstention_accuracy": negative_abstains / len(negatives) if negatives else None,
        "negative_safe_resolution_accuracy": sum(row["answer_strategy"] in {"ABSTAIN", "CORRECTIVE"} for row in negatives) / len(negatives) if negatives else None,
        "unsafe_answer_count": unsafe,
        "unsupported_claim_count": citation_failures,
        "citation_correctness_on_answered": (answer_count - citation_failures) / answer_count if answer_count else None,
        "ineligible_evidence_usage_count": sum(
            item["status"] != "APPROVED" or date.fromisoformat(item["effective_date"]) > as_of
            for row in outputs for item in row["selected_evidence"]
        ),
        "response_counts": dict(sorted(Counter(row["answer_strategy"] for row in outputs).items())),
    }


def run_nonlocked_regression(root: Path, config_path: Path) -> dict[str, Any]:
    """Compare V3 with tracked, already-observed W3-001 development memberships."""
    from payresolve_ai.retrieval.corpus import load_jsonl
    from .context import eligible_chunks
    from .verification import resolve_development_queries

    config, lexicon, _ = load_v3_configuration(root, config_path)
    base = json.loads((root / "configs/generation/grounded_pipeline_v1.json").read_text(encoding="utf-8"))
    prior = json.loads((root / "configs/generation/grounded_pipeline_v2.json").read_text(encoding="utf-8"))
    retrieval = json.loads((root / base["retrieval_config"]).read_text(encoding="utf-8"))
    historical_as_of = date.fromisoformat(prior["evaluation_as_of_date"])
    documents = load_jsonl(root / base["kb_documents"])
    chunks = eligible_chunks(documents, historical_as_of, retrieval["corpus"]["chunk_text_template"])
    raw_idf = build_idf(chunks, config["tokenizer"]["stopwords"])
    canonical_idf = build_canonical_idf(chunks, lexicon, config["tokenizer"]["stopwords"])

    gate_dev = json.loads((root / base["gate_dev_config"]).read_text(encoding="utf-8"))
    memberships = {
        "w3_001_observed_development": {
            "queries": resolve_development_queries(root, gate_dev),
            "rankings": load_jsonl(root / base["outputs"]["rankings"]),
            "baseline": json.loads((root / prior["outputs"]["selection"]).read_text(encoding="utf-8"))["selected_metrics"],
        },
        "w3_001_cr1_observed_holdout_now_development": {
            "queries": load_jsonl(root / json.loads((root / prior["holdout_config"]).read_text(encoding="utf-8"))["dataset_path"]),
            "rankings": load_jsonl(root / prior["outputs"]["holdout_rankings"]),
            "baseline": json.loads((root / prior["outputs"]["holdout_metrics"]).read_text(encoding="utf-8"))["gate_v2"],
        },
    }
    results: dict[str, Any] = {}
    false_negatives: list[dict[str, Any]] = []
    gap_dispositions: list[dict[str, Any]] = []
    for name, membership in memberships.items():
        tracked_top = {row["query_id"]: row["rankings"] for row in membership["rankings"]}
        rankings = tracked_top
        if any(rankings[query_id][: config["standard"]["max_evidence"]] != values for query_id, values in tracked_top.items()):
            raise PipelineV3Error(f"runtime top-three drift on {name}")
        outputs = [run_case_v3(row, rankings[row["query_id"]], chunks, raw_idf, canonical_idf, config, lexicon) for row in membership["queries"]]
        metrics = _nonlocked_metrics(membership["queries"], outputs, historical_as_of)
        baseline = membership["baseline"]
        comparisons = {
            "unsafe_answers_zero": metrics["unsafe_answer_count"] == 0,
            "wrong_evidence_answers_zero": metrics["positive_wrong_evidence_answer_count"] == 0,
            "unsupported_claims_zero": metrics["unsupported_claim_count"] == 0,
            "ineligible_usage_zero": metrics["ineligible_evidence_usage_count"] == 0,
            "negative_safety_non_regression": metrics["negative_safe_resolution_accuracy"] >= baseline["negative_abstention_accuracy"],
            "citation_correctness_one": metrics["citation_correctness_on_answered"] == 1.0,
            "positive_grounded_resolution_non_regression": metrics["positive_grounded_resolution_count"] >= baseline["positive_relevant_answer_count"],
            "unnecessary_abstention_non_increase": metrics["unnecessary_abstention_count"] <= baseline["unnecessary_abstention_count"],
        }
        by_id = {row["query_id"]: row for row in membership["queries"]}
        for output in outputs:
            query = by_id[output["query_id"]]
            primary_reason = output["response_plan"]["reason_codes"][0]
            if (
                query["expected_response_type"] == "ANSWER"
                and output["answer_strategy"] == "STANDARD"
                and primary_reason == "COHERENT_DIRECT_DIMENSION_FALLBACK"
            ):
                gap_dispositions.append({
                    "membership": name,
                    "query_id": output["query_id"],
                    "disposition": "RESOLVED_BY_GENERIC_RULE",
                    "rule": primary_reason,
                })
            if query["expected_response_type"] == "ANSWER" and output["answer_strategy"] != "STANDARD":
                desired_fail_closed = primary_reason in {
                    "AMBIGUOUS_COMPETING_TARGETS",
                    "EVIDENCE_TARGET_STATE_CONFLICT",
                    "LOW_RETRIEVAL_SUPPORT",
                    "TIMING_POLICY_AUTHORITY_REQUIRED",
                    "NEXT_ACTION_DIRECT_ACTION_REQUIRED",
                }
                false_negatives.append({
                    "membership": name,
                    "query_id": output["query_id"],
                    "evidence_available": bool(output["retrieved_evidence"]),
                    "requested_target_support_result": output["response_plan"]["requested_target_status"],
                    "reason_codes": output["response_plan"]["reason_codes"],
                    "desired_fail_closed": desired_fail_closed,
                    "generic_rule_missing": bool(output["retrieved_evidence"]) and not desired_fail_closed,
                    "disposition": "DESIRED_FAIL_CLOSED_WITH_PRODUCT_RULE" if desired_fail_closed else "UNRESOLVED_GENERIC_RULE",
                })
                if desired_fail_closed:
                    gap_dispositions.append({
                        "membership": name,
                        "query_id": output["query_id"],
                        "disposition": "DESIRED_FAIL_CLOSED_WITH_PRODUCT_RULE",
                        "rule": primary_reason,
                    })
        results[name] = {"baseline_v2": baseline, "v3": metrics, "comparisons": comparisons, "outputs": outputs}
    all_comparisons = [value for result in results.values() for value in result["comparisons"].values()]
    return {
        "task_id": config["task_id"],
        "development_only": True,
        "product_approval_claimed": False,
        "status": "PASS" if all(all_comparisons) else "FAIL",
        "memberships": results,
        "standard_false_negatives": false_negatives,
        "standard_gap_dispositions": gap_dispositions,
        "complete_suite_rerun_after_rule_change": True,
        "runtime_model_or_network_used": False,
    }
