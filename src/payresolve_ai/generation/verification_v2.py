"""W3-001-CR1 design selection, one-time holdout, and tracked verification."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from payresolve_ai.evaluation.gold_mapping import canonical_rows_sha256, normalize_query
from payresolve_ai.kb.validation import canonical_dataset_sha256
from payresolve_ai.retrieval.benchmark import _rank_queries
from payresolve_ai.retrieval.corpus import load_jsonl

from .context import eligible_chunks
from .gate import build_idf
from .pipeline import development_metrics, run_case, run_case_v2
from .support_v2 import build_canonical_idf, detect_requested_dimension
from .verification import (
    GroundedPipelineError,
    load_configuration as load_v1_configuration,
    resolve_development_queries,
    sha256_file,
    verify_contract as verify_v1_contract,
    write_json,
    write_jsonl,
)


class EvidenceGateV2Error(GroundedPipelineError):
    pass


ADJUDICATION_CONFIG_PATH = Path("configs/evaluation/evidence_gate_v2_adjudication_v1.json")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_mapping_sha256(rows: list[dict[str, Any]]) -> str:
    return canonical_rows_sha256([{key: value for key, value in row.items() if key != "query_text"} for row in rows])


def _membership_sha256(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(("\n".join(sorted(row["query_id"] for row in rows)) + "\n").encode()).hexdigest()


def load_v2_configuration(root: Path, config_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    config = _load_json(config_path)
    base_path = root / config["base_pipeline_config"]
    base, base_gate, retrieval = load_v1_configuration(root, base_path)
    design = _load_json(root / config["design_config"])
    holdout = _load_json(root / config["holdout_config"])
    lexicon = _load_json(root / config["lexicon_config"])
    expected_grid = {
        "min_top1_score": [0.4, 0.45, 0.5],
        "min_best_sentence_support_coverage": [0.1, 0.2, 0.3],
        "ambiguity_score_gap": 0.03,
        "dimension_match_required": True,
        "unsupported_specificity_guard": True,
    }
    if config["gate_grid"] != expected_grid:
        raise EvidenceGateV2Error("gate-v2 grid drift")
    if config["retriever_variant"] != "R0" or config["top_k"] != 3 or config["predicted_intent_usage"] != "DIAGNOSTIC_ONLY":
        raise EvidenceGateV2Error("gate-v2 retrieval/intent contract mismatch")
    if config["generator_version"] != base["generator_version"] or config["evaluation_as_of_date"] != base["evaluation_as_of_date"]:
        raise EvidenceGateV2Error("accepted generator/as-of contract changed")
    if sha256_file(root / config["lexicon_config"]) != config["frozen"]["lexicon_sha256"]:
        raise EvidenceGateV2Error("frozen lexicon hash mismatch")
    if lexicon.get("holdout_outcomes_used") is not False or lexicon.get("learned_expansion") is not False:
        raise EvidenceGateV2Error("lexicon provenance contract mismatch")
    return config, base, design, holdout, lexicon


def verify_contract(root: Path, config_path: Path) -> dict[str, Any]:
    config, base, _, _, _ = load_v2_configuration(root, config_path)
    verify_v1_contract(root, root / config["base_pipeline_config"])
    checks = {
        "kb_raw_sha256": root / base["kb_documents"],
        "retrieval_locked_r0_sha256": root / "reports/week_02/results/retrieval_locked_r0_rankings.jsonl",
        "retrieval_locked_r1_sha256": root / "reports/week_02/results/retrieval_locked_r1_rankings.jsonl",
        "retrieval_metrics_sha256": root / "reports/week_02/results/retrieval_metrics.json",
        "gate_v1_scenario_sha256": root / "data/evaluation/evidence_gate_dev_scenarios_v1.jsonl",
        "gate_v1_dataset_sha256": root / "data/evaluation/evidence_gate_dev_v1.jsonl",
        "gate_v1_pipeline_config_sha256": root / config["base_pipeline_config"],
        "gate_v1_primary_outputs_sha256": root / base["outputs"]["primary_outputs"],
        "gate_v1_development_metrics_sha256": root / base["outputs"]["metrics"],
    }
    for name, path in checks.items():
        if sha256_file(path) != config["frozen"][name]:
            raise EvidenceGateV2Error(f"frozen upstream mismatch: {name}")
    documents = load_jsonl(root / base["kb_documents"])
    if canonical_dataset_sha256(documents) != config["frozen"]["kb_canonical_sha256"]:
        raise EvidenceGateV2Error("canonical KB mismatch")
    if canonical_rows_sha256(load_jsonl(root / base["w2_mapping"])) != config["frozen"]["w2_mapping_sha256"]:
        raise EvidenceGateV2Error("W2 mapping mismatch")
    return {"status": "PASS", "task_id": "W3-001-CR1", "selected_retriever": "R0", "gate_v1_preserved": True, "official_banking77_test_accessed": False}


def _csv_texts(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as source:
        return [row.get("text", "") for row in csv.DictReader(source)]


def validate_holdout(root: Path, config_path: Path) -> dict[str, Any]:
    config, base, _, holdout, _ = load_v2_configuration(root, config_path)
    scenario_path = root / holdout["scenario_path"]
    dataset_path = root / holdout["dataset_path"]
    ledger_path = root / holdout["correction_ledger_path"]
    rows, scenarios = load_jsonl(dataset_path), load_jsonl(scenario_path)
    frozen = holdout["frozen"]
    actual = {
        "scenario_raw_sha256": sha256_file(scenario_path),
        "dataset_raw_sha256": sha256_file(dataset_path),
        "dataset_canonical_sha256": canonical_rows_sha256(rows),
        "membership_sha256": _membership_sha256(rows),
        "mapping_sha256": _canonical_mapping_sha256(rows),
        "correction_ledger_raw_sha256": sha256_file(ledger_path),
    }
    if actual != frozen:
        raise EvidenceGateV2Error("frozen holdout hash mismatch")
    if len(rows) != 20 or len(scenarios) != 20:
        raise EvidenceGateV2Error("holdout must contain exactly 20 cases")
    answer = [row for row in rows if row["expected_response_type"] == "ANSWER"]
    negative = [row for row in rows if row["expected_response_type"] == "ABSTAIN_ESCALATE"]
    if len(answer) != 10 or len(negative) != 10 or len({row["gold_intent"] for row in answer}) != 10:
        raise EvidenceGateV2Error("holdout answer/abstain/intent distribution mismatch")
    if dict(sorted(Counter(row["case_type"] for row in negative).items())) != holdout["expected"]["negative_case_types"]:
        raise EvidenceGateV2Error("holdout negative distribution mismatch")
    scenario_by_id = {row["query_id"]: row for row in scenarios}
    if len(scenario_by_id) != 20 or {row["query_id"] for row in rows} != set(scenario_by_id):
        raise EvidenceGateV2Error("holdout scenario/dataset membership mismatch")
    for row in rows:
        scenario = scenario_by_id[row["query_id"]]
        for key in ("query_text", "expected_response_type", "gold_intent", "requested_dimension", "case_type"):
            if row[key] != scenario[key]:
                raise EvidenceGateV2Error(f"holdout scenario drift: {row['query_id']}:{key}")
        detected = detect_requested_dimension(row["query_text"])["dimension"]
        if detected != row["requested_dimension"]:
            raise EvidenceGateV2Error(f"holdout dimension rule mismatch: {row['query_id']} expected {row['requested_dimension']} got {detected}")
    documents = load_jsonl(root / base["kb_documents"])
    eligible = {f"{doc['document_id']}#{section['section_id']}" for doc in documents if doc["status"] == "APPROVED" for section in doc["content_sections"]}
    ineligible = {f"{doc['document_id']}#{section['section_id']}" for doc in documents if doc["status"] != "APPROVED" for section in doc["content_sections"]}
    for row in answer:
        if not row.get("gold_evidence_ids") or not set(row["gold_evidence_ids"] + row.get("acceptable_evidence_ids", [])) <= eligible:
            raise EvidenceGateV2Error(f"invalid positive evidence mapping: {row['query_id']}")
    for row in negative:
        if "requested_unsupported_detail" not in row or "approved_sections_reviewed" not in row or not set(row["approved_sections_reviewed"]) <= eligible or not set(row["attractive_forbidden_evidence_ids"]) <= ineligible:
            raise EvidenceGateV2Error(f"invalid negative evidence review: {row['query_id']}")
    design_queries = resolve_development_queries(root, _load_json(root / base["gate_dev_config"]))
    w2 = load_jsonl(root / holdout["w2_mapping_path"])
    other_texts = [row["query_text"] for row in design_queries + w2]
    texts = [row["query_text"] for row in rows]
    if set(texts) & set(other_texts) or {normalize_query(text) for text in texts} & {normalize_query(text) for text in other_texts}:
        raise EvidenceGateV2Error("holdout overlaps W3-v1/W2 queries")
    banking_overlap: dict[str, dict[str, Any]] = {}
    for split, key in (("train", "banking77_train_path"), ("official_test", "banking77_test_path")):
        corpus = _csv_texts(root / holdout[key])
        exact = len(set(texts) & set(corpus))
        normalized = len({normalize_query(text) for text in texts} & {normalize_query(text) for text in corpus})
        if exact or normalized:
            raise EvidenceGateV2Error(f"holdout Banking77 {split} overlap")
        banking_overlap[split] = {"exact_overlap": exact, "normalized_overlap": normalized, "contents_manually_inspected": False}
    token_set = lambda value: set(re.findall(r"[a-z0-9]+", value.casefold()))
    near = []
    threshold = holdout["near_duplicate_review_threshold"]
    for row in rows:
        left = token_set(row["query_text"])
        for prior in design_queries + w2:
            right = token_set(prior["query_text"])
            score = len(left & right) / len(left | right) if left | right else 0.0
            if score >= threshold:
                near.append({"holdout_query_id": row["query_id"], "prior_query_id": prior["query_id"], "jaccard": score})
    if near:
        raise EvidenceGateV2Error("unresolved holdout near-duplicate candidates")
    return {"status": "PASS", "dataset_name": holdout["dataset_name"], "cases": 20, "answer": 10, "abstain_escalate": 10, "positive_intents": 10, "negative_case_types": holdout["expected"]["negative_case_types"], "hashes": frozen, "exact_overlap": 0, "normalized_overlap": 0, "near_duplicate_candidates": 0, "banking77_overlap": banking_overlap, "official_test_contents_manually_inspected": False, "correction_ledger_entries": len(load_jsonl(ledger_path)), "holdout_evaluated": holdout["holdout_evaluated"]}


def _runtime_material(root: Path, config_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, float], dict[str, float]]:
    config, base, _, _, lexicon = load_v2_configuration(root, config_path)
    _, _, retrieval = load_v1_configuration(root, root / config["base_pipeline_config"])
    documents = load_jsonl(root / base["kb_documents"])
    chunks = eligible_chunks(documents, date.fromisoformat(config["evaluation_as_of_date"]), retrieval["corpus"]["chunk_text_template"])
    raw_idf = build_idf(chunks, base["tokenizer"]["stopwords"])
    canonical_idf = build_canonical_idf(chunks, lexicon, base["tokenizer"]["stopwords"])
    return config, base, lexicon, chunks, raw_idf, canonical_idf


def freeze_v2_design(root: Path, config_path: Path) -> dict[str, Any]:
    verify_contract(root, config_path); validate_holdout(root, config_path)
    config, base, design, _, _ = load_v2_configuration(root, config_path)
    queries = resolve_development_queries(root, _load_json(root / base["gate_dev_config"]))
    rankings = load_jsonl(root / base["outputs"]["rankings"])
    predictions = load_jsonl(root / base["outputs"]["predictions"])
    if {row["query_id"] for row in rankings} != {row["query_id"] for row in queries}:
        raise EvidenceGateV2Error("design rankings do not match frozen design membership")
    for row in queries:
        expected = design["expected_dimensions"][row["query_id"]]
        actual = detect_requested_dimension(row["query_text"])["dimension"]
        if actual != expected:
            raise EvidenceGateV2Error(f"design dimension mismatch: {row['query_id']} expected {expected} got {actual}")
    write_jsonl(root / config["outputs"]["design_rankings"], rankings)
    write_jsonl(root / config["outputs"]["design_predictions"], predictions)
    return {"status": "PASS", "cases": 20, "source": "frozen W3-001 tracked R0 runtime", "holdout_used": False}


def _grid(config: dict[str, Any]) -> list[dict[str, float]]:
    return [
        {"min_top1_score": score, "min_best_sentence_support_coverage": coverage, "ambiguity_score_gap": config["gate_grid"]["ambiguity_score_gap"]}
        for score in config["gate_grid"]["min_top1_score"]
        for coverage in config["gate_grid"]["min_best_sentence_support_coverage"]
    ]


def _v2_metrics(queries: list[dict[str, Any]], outputs: list[dict[str, Any]], as_of: date) -> dict[str, Any]:
    metrics = development_metrics(queries, outputs, as_of)
    by_id = {row["query_id"]: row for row in queries}
    relevant_families: set[str] = set()
    for output in outputs:
        query = by_id[output["query_id"]]
        if query["expected_response_type"] != "ANSWER" or output["response_type"] != "ANSWER":
            continue
        cited = {citation["evidence_id"] for citation in output["citations"]}
        gold, acceptable = set(query.get("gold_evidence_ids", [])), set(query.get("acceptable_evidence_ids", []))
        success = gold <= cited if query.get("evidence_requirement") == "multi_document" else bool(cited & (gold | acceptable))
        if success:
            relevant_families.add(query.get("intent_family", "unknown"))
    metrics.update({
        "intent_family_positive_coverage": len(relevant_families),
        "intent_families_with_positive_resolution": sorted(relevant_families),
        "dimension_counts": dict(sorted(Counter(str(row["gate"].get("requested_dimension", {}).get("dimension", "UNKNOWN")) for row in outputs).items())),
        "specificity_guard_trigger_count": sum(bool(row["gate"].get("specificity_guard", {}).get("triggered")) for row in outputs),
        "citation_metadata_failure_count": sum(row["gate"]["reason_code"] == "CITATION_CONTRACT_FAILURE" for row in outputs),
        "draft_expired_citation_count": sum(citation.get("status") in {"DRAFT", "EXPIRED"} for row in outputs for citation in row.get("citations", [])),
    })
    return metrics


def _evaluate_v2(root: Path, config_path: Path, queries: list[dict[str, Any]], rankings: list[dict[str, Any]], predictions: list[dict[str, Any]], candidate: dict[str, float]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    config, base, lexicon, chunks, raw_idf, canonical_idf = _runtime_material(root, config_path)
    rank_by_id, prediction_by_id = {row["query_id"]: row for row in rankings}, {row["query_id"]: row for row in predictions}
    if set(rank_by_id) != {row["query_id"] for row in queries} or set(prediction_by_id) != {row["query_id"] for row in queries}:
        raise EvidenceGateV2Error("runtime membership mismatch")
    outputs = [run_case_v2(row, rank_by_id[row["query_id"]], prediction_by_id[row["query_id"]], chunks, raw_idf, canonical_idf, base, config, lexicon, candidate) for row in queries]
    return outputs, _v2_metrics(queries, outputs, date.fromisoformat(config["evaluation_as_of_date"]))


def choose_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Apply the preregistered design-only eligibility and tie-break contract."""
    eligible = [row for row in candidates if row["eligible"]]
    if not eligible:
        return None
    return min(eligible, key=lambda row: (
        -row["metrics"]["positive_grounded_resolution_recall"],
        -row["metrics"]["safe_resolution_accuracy"],
        -row["metrics"]["intent_family_positive_coverage"],
        row["metrics"]["unnecessary_abstention_rate"],
        -row["metrics"]["negative_abstention_accuracy"],
        row["policy"]["min_top1_score"],
        row["policy"]["min_best_sentence_support_coverage"],
    ))


def _candidate_payload(root: Path, config_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    config, base, _, _, _ = load_v2_configuration(root, config_path)
    queries = resolve_development_queries(root, _load_json(root / base["gate_dev_config"]))
    rankings = load_jsonl(root / config["outputs"]["design_rankings"])
    predictions = load_jsonl(root / config["outputs"]["design_predictions"])
    candidates = []
    for policy in _grid(config):
        outputs, metrics = _evaluate_v2(root, config_path, queries, rankings, predictions, policy)
        eligible = all(metrics[name] == 0 for name in ("unsafe_answer_count", "positive_wrong_evidence_answer_count", "unsupported_claim_count", "citation_metadata_failure_count"))
        candidate_id = f"S{policy['min_top1_score']:.2f}_C{policy['min_best_sentence_support_coverage']:.2f}"
        candidates.append({"candidate_id": candidate_id, "eligible": eligible, "policy": policy, "metrics": metrics, "outcomes": [{"query_id": row["query_id"], "response_type": row["response_type"], "reason_code": row["gate"]["reason_code"]} for row in outputs]})
    candidates.sort(key=lambda row: row["candidate_id"])
    selected = choose_candidate(candidates)
    payload = {"task_id": "W3-001-CR1", "selection_dataset": "gate_v2_design", "holdout_used": False, "candidate_count": 9, "candidates": candidates}
    if selected is None:
        selection = {"task_id": "W3-001-CR1", "status": "FAILED_NO_SAFE_CANDIDATE", "selection_dataset": "gate_v2_design", "holdout_query_ids_used": 0}
        return payload, selection
    selection = {
        "task_id": "W3-001-CR1", "status": "FROZEN_DESIGN_SELECTION", "selection_dataset": "gate_v2_design",
        "selected_candidate_id": selected["candidate_id"], "selected_policy": selected["policy"], "selected_metrics": selected["metrics"],
        "selection_rule": config["selection_tie_break"], "design_membership_sha256": _membership_sha256(queries),
        "holdout_query_ids_used": 0, "holdout_metrics_used": False, "pipeline_config_sha256": sha256_file(config_path),
        "lexicon_sha256": sha256_file(root / config["lexicon_config"]),
    }
    return payload, selection


def select_v2(root: Path, config_path: Path) -> dict[str, Any]:
    verify_contract(root, config_path); validate_holdout(root, config_path)
    config, _, _, holdout, _ = load_v2_configuration(root, config_path)
    payload, selection = _candidate_payload(root, config_path)
    write_json(root / config["outputs"]["candidate_metrics"], payload)
    selection["candidate_metrics_sha256"] = sha256_file(root / config["outputs"]["candidate_metrics"])
    write_json(root / config["outputs"]["selection"], selection)
    if selection["status"] != "FROZEN_DESIGN_SELECTION":
        return {"candidate_metrics": payload, "selection": selection}
    manifest = {
        "task_id": "W3-001-CR1", "status": "PRE_HOLDOUT_FROZEN", "holdout_evaluated": False,
        "created_at": datetime.now(timezone.utc).isoformat(), "pipeline_config_sha256": sha256_file(config_path),
        "design_config_sha256": sha256_file(root / config["design_config"]), "holdout_config_sha256": sha256_file(root / config["holdout_config"]),
        "lexicon_sha256": sha256_file(root / config["lexicon_config"]), "selection_sha256": sha256_file(root / config["outputs"]["selection"]),
        "candidate_metrics_sha256": sha256_file(root / config["outputs"]["candidate_metrics"]), "holdout_frozen": holdout["frozen"],
        "holdout_query_ids_used_for_selection": 0,
    }
    write_json(root / config["outputs"]["preholdout_manifest"], manifest)
    return {"candidate_metrics": payload, "selection": selection, "preholdout_manifest": manifest}


def verify_preholdout(root: Path, config_path: Path, *, require_unexecuted: bool = True) -> dict[str, Any]:
    verify_contract(root, config_path); holdout_validation = validate_holdout(root, config_path)
    config, _, _, holdout, _ = load_v2_configuration(root, config_path)
    stored_candidates = _load_json(root / config["outputs"]["candidate_metrics"])
    stored_selection = _load_json(root / config["outputs"]["selection"])
    expected_candidates, expected_selection = _candidate_payload(root, config_path)
    expected_selection["candidate_metrics_sha256"] = sha256_file(root / config["outputs"]["candidate_metrics"])
    if stored_candidates != expected_candidates or stored_selection != expected_selection:
        raise EvidenceGateV2Error("design selection drift or holdout contamination")
    manifest = _load_json(root / config["outputs"]["preholdout_manifest"])
    checks = {
        "pipeline_config_sha256": sha256_file(config_path),
        "design_config_sha256": sha256_file(root / config["design_config"]),
        "holdout_config_sha256": sha256_file(root / config["holdout_config"]),
        "lexicon_sha256": sha256_file(root / config["lexicon_config"]),
        "selection_sha256": sha256_file(root / config["outputs"]["selection"]),
        "candidate_metrics_sha256": sha256_file(root / config["outputs"]["candidate_metrics"]),
    }
    if any(manifest.get(key) != value for key, value in checks.items()) or manifest.get("holdout_frozen") != holdout["frozen"] or manifest.get("holdout_evaluated") is not False or manifest.get("holdout_query_ids_used_for_selection") != 0:
        raise EvidenceGateV2Error("pre-holdout manifest mismatch")
    holdout_outputs = [root / config["outputs"][key] for key in ("holdout_v1_outputs", "holdout_v2_outputs", "holdout_v2_reproduction")]
    if require_unexecuted and any(path.exists() for path in holdout_outputs):
        raise EvidenceGateV2Error("holdout was already executed")
    return {"status": "PASS", "selection_frozen": True, "holdout_evaluated": False, "holdout_query_ids_used_for_selection": 0, "holdout_validation": holdout_validation}


def _holdout_runtime(root: Path, config_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    config, base, _, holdout, _ = load_v2_configuration(root, config_path)
    queries = load_jsonl(root / holdout["dataset_path"])
    runtime_queries = [{**row, "split": "holdout"} for row in queries]
    retrieval = _load_json(root / base["retrieval_config"])
    return _rank_queries(root, retrieval, runtime_queries, None)


def _evaluate_v1_holdout(root: Path, config_path: Path, queries: list[dict[str, Any]], rankings: list[dict[str, Any]], predictions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    config, base, _, chunks, raw_idf, _ = _runtime_material(root, config_path)
    selection = _load_json(root / base["outputs"]["selection"])
    rank_by_id, pred_by_id = {row["query_id"]: row for row in rankings}, {row["query_id"]: row for row in predictions}
    outputs = [run_case(row, rank_by_id[row["query_id"]], pred_by_id[row["query_id"]], chunks, raw_idf, base, selection["selected_policy"]) for row in queries]
    return outputs, _v2_metrics(queries, outputs, date.fromisoformat(config["evaluation_as_of_date"]))


def run_holdout(root: Path, config_path: Path, run_label: str) -> dict[str, Any]:
    config, _, _, holdout, _ = load_v2_configuration(root, config_path)
    queries = load_jsonl(root / holdout["dataset_path"])
    selection = _load_json(root / config["outputs"]["selection"])
    if run_label == "primary":
        verify_preholdout(root, config_path, require_unexecuted=True)
        rankings, predictions = _holdout_runtime(root, config_path)
        write_jsonl(root / config["outputs"]["holdout_rankings"], rankings)
        write_jsonl(root / config["outputs"]["holdout_predictions"], predictions)
        v1_outputs, v1_metrics = _evaluate_v1_holdout(root, config_path, queries, rankings, predictions)
        v2_outputs, v2_metrics = _evaluate_v2(root, config_path, queries, rankings, predictions, selection["selected_policy"])
        write_jsonl(root / config["outputs"]["holdout_v1_outputs"], v1_outputs)
        write_jsonl(root / config["outputs"]["holdout_v2_outputs"], v2_outputs)
        write_json(root / config["outputs"]["holdout_metrics"], {"gate_v1": v1_metrics, "gate_v2": v2_metrics})
        return {"status": "PASS", "run_label": run_label, "gate_v1_metrics": v1_metrics, "gate_v2_metrics": v2_metrics}
    if run_label != "reproducibility_rerun":
        raise EvidenceGateV2Error("invalid holdout run label")
    verify_preholdout(root, config_path, require_unexecuted=False)
    stored_rankings = load_jsonl(root / config["outputs"]["holdout_rankings"])
    stored_predictions = load_jsonl(root / config["outputs"]["holdout_predictions"])
    rankings, predictions = _holdout_runtime(root, config_path)
    if rankings != stored_rankings or predictions != stored_predictions:
        raise EvidenceGateV2Error("holdout runtime reproduction mismatch")
    outputs, metrics = _evaluate_v2(root, config_path, queries, rankings, predictions, selection["selected_policy"])
    write_jsonl(root / config["outputs"]["holdout_v2_reproduction"], outputs)
    return {"status": "PASS", "run_label": run_label, "metrics": metrics, "primary_reproduction_identical": (root / config["outputs"]["holdout_v2_outputs"]).read_bytes() == (root / config["outputs"]["holdout_v2_reproduction"]).read_bytes()}


def _acceptance(config: dict[str, Any], design: dict[str, Any], holdout: dict[str, Any], v1_holdout: dict[str, Any]) -> dict[str, Any]:
    hard_names = ("unsafe_answer_count", "positive_wrong_evidence_answer_count", "unsupported_claim_count", "draft_expired_citation_count", "citation_metadata_failure_count")
    safety = all(design[name] == 0 and holdout[name] == 0 for name in hard_names)
    required = set(config["acceptance"]["required_intent_families"])
    utility = (
        holdout["positive_relevant_answer_count"] >= config["acceptance"]["minimum_positive_grounded_resolutions"]
        and holdout["positive_grounded_resolution_recall"] >= config["acceptance"]["minimum_positive_grounded_resolution_recall"]
        and required <= set(holdout["intent_families_with_positive_resolution"])
        and holdout["negative_abstention_accuracy"] >= config["acceptance"]["minimum_negative_abstention_accuracy"]
        and holdout["safe_resolution_accuracy"] >= config["acceptance"]["minimum_safe_resolution_accuracy"]
        and holdout["positive_grounded_resolution_recall"] > v1_holdout["positive_grounded_resolution_recall"]
        and holdout["unsafe_answer_rate"] <= v1_holdout["unsafe_answer_rate"]
    )
    verdict = "PASS" if safety and utility else "PARTIAL" if safety else "FAILED"
    return {"verdict": verdict, "hard_safety_requirements_pass": safety, "minimum_utility_requirements_pass": utility, "required_intent_families": sorted(required), "w3_002_state": "QUEUED / NOT STARTED" if verdict == "PASS" else "BLOCKED / NOT STARTED"}


def _error_rows(queries: list[dict[str, Any]], v1: list[dict[str, Any]], v2: list[dict[str, Any]]) -> list[dict[str, Any]]:
    query_by_id = {row["query_id"]: row for row in queries}
    v1_by_id, v2_by_id = {row["query_id"]: row for row in v1}, {row["query_id"]: row for row in v2}
    rows = []
    for query_id in sorted(query_by_id):
        query, left, right = query_by_id[query_id], v1_by_id[query_id], v2_by_id[query_id]
        relevant_ids = set(query.get("gold_evidence_ids", []) + query.get("acceptable_evidence_ids", []))
        retrieved_ids = [row["evidence_id"] for row in right.get("retrieved_evidence", [])]
        criteria = []
        if left["response_type"] != right["response_type"]: criteria.append("V1_V2_RESPONSE_DIFFERS")
        if query["expected_response_type"] == "ANSWER" and right["response_type"] == "ABSTAIN_ESCALATE": criteria.append("V2_UNNECESSARY_ABSTAIN")
        if right["response_type"] == "ANSWER": criteria.append("V2_ANSWER")
        if not right["gate"].get("dimension_match", False): criteria.append("DIMENSION_NOT_SUPPORTED")
        if right["gate"].get("specificity_guard", {}).get("triggered"): criteria.append("SPECIFICITY_GUARD_TRIGGER")
        if relevant_ids & set(retrieved_ids) and right["response_type"] != "ANSWER": criteria.append("RELEVANT_RETRIEVED_NO_ANSWER")
        if not criteria: continue
        cited = ";".join(row["evidence_id"] for row in right.get("citations", []))
        rows.append({
            "query_id": query_id, "review_criteria": ";".join(criteria), "expected_response_type": query["expected_response_type"],
            "requested_dimension": query["requested_dimension"], "top3_evidence": ";".join(retrieved_ids),
            "gate_v1_result": f"{left['response_type']}:{left['gate']['reason_code']}", "gate_v2_result": f"{right['response_type']}:{right['gate']['reason_code']}",
            "canonical_support_score": right["gate"].get("best_sentence_support_coverage", 0.0),
            "specificity_slot": ";".join(right["gate"].get("specificity_guard", {}).get("requested_slots", [])),
            "selected_claim_citation": cited,
            "root_cause": "retrieval_miss" if query["expected_response_type"] == "ANSWER" and not relevant_ids & set(retrieved_ids) else right["gate"]["reason_code"],
            "decision_implication": "Preserve frozen result; do not tune from holdout.",
        })
    return rows


def finalize(root: Path, config_path: Path) -> dict[str, Any]:
    config, base, _, holdout_config, _ = load_v2_configuration(root, config_path)
    verify_preholdout(root, config_path, require_unexecuted=False)
    primary = root / config["outputs"]["holdout_v2_outputs"]
    reproduction = root / config["outputs"]["holdout_v2_reproduction"]
    if primary.read_bytes() != reproduction.read_bytes():
        raise EvidenceGateV2Error("holdout primary/reproduction outputs differ")
    queries = load_jsonl(root / holdout_config["dataset_path"])
    rankings = load_jsonl(root / config["outputs"]["holdout_rankings"])
    predictions = load_jsonl(root / config["outputs"]["holdout_predictions"])
    selection = _load_json(root / config["outputs"]["selection"])
    v1_outputs, v1_metrics = _evaluate_v1_holdout(root, config_path, queries, rankings, predictions)
    v2_outputs, v2_metrics = _evaluate_v2(root, config_path, queries, rankings, predictions, selection["selected_policy"])
    design_metrics = selection["selected_metrics"]
    acceptance = _acceptance(config, design_metrics, v2_metrics, v1_metrics)
    comparison = {"task_id": "W3-001-CR1", "gate_v1_policy": "S0.40_C0.45", "gate_v2_policy": selection["selected_candidate_id"], "gate_v1": v1_metrics, "gate_v2": v2_metrics, "delta": {"positive_grounded_resolution_recall": v2_metrics["positive_grounded_resolution_recall"] - v1_metrics["positive_grounded_resolution_recall"], "unsafe_answer_rate": v2_metrics["unsafe_answer_rate"] - v1_metrics["unsafe_answer_rate"], "safe_resolution_accuracy": v2_metrics["safe_resolution_accuracy"] - v1_metrics["safe_resolution_accuracy"]}, "acceptance": acceptance}
    write_json(root / config["outputs"]["holdout_comparison"], comparison)
    error_rows = _error_rows(queries, v1_outputs, v2_outputs)
    error_path = root / config["outputs"]["error_analysis"]
    error_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["query_id", "review_criteria", "expected_response_type", "requested_dimension", "top3_evidence", "gate_v1_result", "gate_v2_result", "canonical_support_score", "specificity_slot", "selected_claim_citation", "root_cause", "decision_implication"]
    with error_path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields, lineterminator="\n"); writer.writeheader(); writer.writerows(error_rows)
    artifacts = [key for key in config["outputs"] if key not in {"manifest", "validation"}]
    manifest = {
        "task_id": "W3-001-CR1", "status": acceptance["verdict"], "created_at": datetime.now(timezone.utc).isoformat(),
        "holdout_evaluated": True, "holdout_evaluation_count": 1, "primary_reproduction_identical": True,
        "pipeline_config_sha256": sha256_file(config_path), "lexicon_sha256": sha256_file(root / config["lexicon_config"]),
        "holdout_frozen": holdout_config["frozen"], "selected_policy": selection["selected_policy"], "acceptance": acceptance,
        "artifact_sha256": {key: sha256_file(root / config["outputs"][key]) for key in artifacts},
        "gate_v1_config_sha256": sha256_file(root / config["base_pipeline_config"]), "w3_002_started": False, "week4_started": False,
    }
    write_json(root / config["outputs"]["manifest"], manifest)
    return {"manifest": manifest, "comparison": comparison, "error_analysis_rows": len(error_rows)}


def _adjudication_configuration(root: Path) -> dict[str, Any]:
    path = root / ADJUDICATION_CONFIG_PATH
    if not path.exists():
        raise EvidenceGateV2Error("mapping-audit-incomplete: adjudication config missing")
    config = _load_json(path)
    if config.get("application_stage") != "POST_HOLDOUT_RELEVANCE_METRICS_ONLY":
        raise EvidenceGateV2Error("unapproved-adjudication-operation: invalid application stage")
    return config


def _eligible_section_content(root: Path, base: dict[str, Any], as_of: date) -> dict[str, str]:
    eligible: dict[str, str] = {}
    for document in load_jsonl(root / base["kb_documents"]):
        effective = date.fromisoformat(document["effective_date"])
        expiry = date.fromisoformat(document["expiry_date"]) if document.get("expiry_date") else None
        if document["status"] != "APPROVED" or effective > as_of or (expiry is not None and expiry <= as_of):
            continue
        for section in document["content_sections"]:
            eligible[f"{document['document_id']}#{section['section_id']}"] = section["content"]
    return eligible


def _mapping_audit_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def validate_adjudication(root: Path, config_path: Path) -> dict[str, Any]:
    config, base, _, holdout, _ = load_v2_configuration(root, config_path)
    adjudication = _adjudication_configuration(root)
    if adjudication.get("pipeline_config") != config_path.relative_to(root).as_posix():
        raise EvidenceGateV2Error("unapproved-adjudication-operation: pipeline config mismatch")
    original_queries = load_jsonl(root / holdout["dataset_path"])
    original_frozen = {
        "scenario_raw_sha256": sha256_file(root / holdout["scenario_path"]),
        "dataset_raw_sha256": sha256_file(root / holdout["dataset_path"]),
        "membership_sha256": _membership_sha256(original_queries),
        "original_mapping_sha256": _canonical_mapping_sha256(original_queries),
        "primary_output_sha256": sha256_file(root / config["outputs"]["holdout_v2_outputs"]),
        "reproduction_output_sha256": sha256_file(root / config["outputs"]["holdout_v2_reproduction"]),
        "original_metrics_sha256": sha256_file(root / config["outputs"]["holdout_metrics"]),
    }
    for name, actual in original_frozen.items():
        if adjudication["frozen"].get(name) != actual:
            raise EvidenceGateV2Error(f"holdout-original-artifact-drift: {name}")
    audit_path = root / adjudication["mapping_audit"]
    overlay_path = root / adjudication["overlay"]
    if sha256_file(audit_path) != adjudication["frozen"]["mapping_audit_sha256"]:
        raise EvidenceGateV2Error("mapping-audit-incomplete: audit hash drift")
    if sha256_file(overlay_path) != adjudication["frozen"]["overlay_sha256"]:
        raise EvidenceGateV2Error("mapping-audit-overlay-mismatch: overlay hash drift")
    audit = _mapping_audit_rows(audit_path)
    positives = {row["query_id"]: row for row in original_queries if row["expected_response_type"] == "ANSWER"}
    if len(audit) != 10 or len({row["query_id"] for row in audit}) != 10 or {row["query_id"] for row in audit} != set(positives):
        raise EvidenceGateV2Error("mapping-audit-incomplete: expected all ten positive queries")
    if any("All 52 eligible approved sections were reviewed." not in row["review_rationale"] for row in audit):
        raise EvidenceGateV2Error("mapping-audit-incomplete: exhaustive review statement missing")
    audit_omissions = {
        row["query_id"]: row["omitted_direct_evidence_ids"]
        for row in audit
        if row["review_status"] == "DEFECT_FOUND"
    }
    if audit_omissions != adjudication["approved_omissions"]:
        raise EvidenceGateV2Error("mapping-audit-overlay-mismatch: approved omissions differ")
    overlay = load_jsonl(overlay_path)
    if len(overlay) != 3 or len({row["query_id"] for row in overlay}) != 3:
        raise EvidenceGateV2Error("adjudication-overlay-count-mismatch: overlay must contain exactly three rows")
    allowed_fields = {
        "query_id", "adjudication_type", "added_acceptable_evidence_ids",
        "requested_dimension", "exact_support_quote", "reason", "review_status",
    }
    eligible = _eligible_section_content(root, base, date.fromisoformat(config["evaluation_as_of_date"]))
    additions: dict[str, list[str]] = {}
    for row in overlay:
        if set(row) != allowed_fields or row["adjudication_type"] != "ADD_ACCEPTABLE_EVIDENCE":
            raise EvidenceGateV2Error("unapproved-adjudication-operation: overlay may only add acceptable evidence")
        query_id = row["query_id"]
        if query_id not in positives or row["requested_dimension"] != positives[query_id]["requested_dimension"]:
            raise EvidenceGateV2Error("unapproved-adjudication-operation: query metadata changed")
        added = row["added_acceptable_evidence_ids"]
        if added != [adjudication["approved_omissions"].get(query_id)]:
            raise EvidenceGateV2Error("mapping-audit-overlay-mismatch: non-audited evidence added")
        evidence_id = added[0]
        if evidence_id not in eligible:
            raise EvidenceGateV2Error("adjudication-evidence-not-eligible")
        if row["exact_support_quote"] != eligible[evidence_id]:
            raise EvidenceGateV2Error("adjudication-support-quote-mismatch")
        if row["review_status"] != "SENIOR_APPROVED_MAPPING_CORRECTION":
            raise EvidenceGateV2Error("unapproved-adjudication-operation: review status")
        if evidence_id in positives[query_id].get("gold_evidence_ids", []) + positives[query_id].get("acceptable_evidence_ids", []):
            raise EvidenceGateV2Error("unapproved-adjudication-operation: duplicate evidence addition")
        additions[query_id] = added
    adjudicated_queries = []
    for query in original_queries:
        updated = {**query}
        if query["query_id"] in additions:
            updated["acceptable_evidence_ids"] = [*query.get("acceptable_evidence_ids", []), *additions[query["query_id"]]]
        adjudicated_queries.append(updated)
    return {
        "status": "PASS",
        "config": adjudication,
        "audit": audit,
        "overlay": overlay,
        "original_queries": original_queries,
        "adjudicated_queries": adjudicated_queries,
        "original_mapping_sha256": _canonical_mapping_sha256(original_queries),
        "adjudicated_mapping_sha256": _canonical_mapping_sha256(adjudicated_queries),
        "original_artifact_sha256": original_frozen,
    }


def _verify_original_tracked(root: Path, config_path: Path) -> dict[str, Any]:
    contract = verify_contract(root, config_path)
    holdout_validation = validate_holdout(root, config_path)
    config, _, _, holdout, _ = load_v2_configuration(root, config_path)
    selection = _load_json(root / config["outputs"]["selection"])
    preholdout = _load_json(root / config["outputs"]["preholdout_manifest"])
    if selection.get("status") != "FROZEN_DESIGN_SELECTION" or selection.get("selected_candidate_id") != "S0.40_C0.20" or selection.get("holdout_query_ids_used") != 0 or selection.get("holdout_metrics_used") is not False:
        raise EvidenceGateV2Error("tracked design selection tampering")
    if preholdout.get("selection_sha256") != sha256_file(root / config["outputs"]["selection"]) or preholdout.get("candidate_metrics_sha256") != sha256_file(root / config["outputs"]["candidate_metrics"]):
        raise EvidenceGateV2Error("tracked design selection tampering")
    manifest = _load_json(root / config["outputs"]["manifest"])
    if manifest.get("pipeline_config_sha256") != sha256_file(config_path) or manifest.get("lexicon_sha256") != sha256_file(root / config["lexicon_config"]):
        raise EvidenceGateV2Error("holdout-original-artifact-drift: original manifest contract")
    for key, expected in manifest["artifact_sha256"].items():
        if sha256_file(root / config["outputs"][key]) != expected:
            raise EvidenceGateV2Error(f"holdout-original-artifact-drift: {key}")
    primary_path = root / config["outputs"]["holdout_v2_outputs"]
    reproduction_path = root / config["outputs"]["holdout_v2_reproduction"]
    if primary_path.read_bytes() != reproduction_path.read_bytes():
        raise EvidenceGateV2Error("holdout-original-artifact-drift: primary/reproduction mismatch")
    queries = load_jsonl(root / holdout["dataset_path"])
    v1_outputs = load_jsonl(root / config["outputs"]["holdout_v1_outputs"])
    v2_outputs = load_jsonl(primary_path)
    as_of = date.fromisoformat(config["evaluation_as_of_date"])
    v1_metrics = _v2_metrics(queries, v1_outputs, as_of)
    v2_metrics = _v2_metrics(queries, v2_outputs, as_of)
    stored_metrics = _load_json(root / config["outputs"]["holdout_metrics"])
    if stored_metrics != {"gate_v1": v1_metrics, "gate_v2": v2_metrics}:
        raise EvidenceGateV2Error("holdout-original-artifact-drift: original metric mismatch")
    acceptance = _acceptance(config, selection["selected_metrics"], v2_metrics, v1_metrics)
    comparison = _load_json(root / config["outputs"]["holdout_comparison"])
    if comparison.get("gate_v1") != v1_metrics or comparison.get("gate_v2") != v2_metrics or comparison.get("acceptance") != acceptance:
        raise EvidenceGateV2Error("holdout-original-artifact-drift: comparison mismatch")
    if acceptance["verdict"] != "FAILED" or manifest.get("status") != "FAILED" or manifest.get("acceptance") != acceptance:
        raise EvidenceGateV2Error("holdout-original-artifact-drift: original verdict conflated")
    return {
        "contract": contract, "holdout_validation": holdout_validation, "config": config,
        "selection": selection, "queries": queries, "v1_outputs": v1_outputs,
        "v2_outputs": v2_outputs, "v1_metrics": v1_metrics, "v2_metrics": v2_metrics,
        "acceptance": acceptance, "manifest": manifest,
    }


def _adjudication_payload(root: Path, config_path: Path) -> dict[str, Any]:
    original = _verify_original_tracked(root, config_path)
    validated = validate_adjudication(root, config_path)
    config = original["config"]
    as_of = date.fromisoformat(config["evaluation_as_of_date"])
    adjudicated_metrics = _v2_metrics(validated["adjudicated_queries"], original["v2_outputs"], as_of)
    adjudicated_metrics = {
        **adjudicated_metrics,
        "draft_citation_count": sum(c.get("status") == "DRAFT" for row in original["v2_outputs"] for c in row.get("citations", [])),
        "expired_citation_count": sum(c.get("status") == "EXPIRED" for row in original["v2_outputs"] for c in row.get("citations", [])),
    }
    acceptance = {
        **_acceptance(config, original["selection"]["selected_metrics"], adjudicated_metrics, original["v1_metrics"]),
        "w3_002_state": "BLOCKED PENDING FINAL SENIOR RE-REVIEW",
    }
    expected = {
        "answer_count": 7, "positive_answer_count": 7, "positive_relevant_answer_count": 7,
        "positive_wrong_evidence_answer_count": 0, "positive_grounded_resolution_recall": 0.7,
        "negative_abstention_accuracy": 1.0, "unsafe_answer_count": 0, "unsafe_answer_rate": 0.0,
        "unnecessary_abstention_count": 3, "unnecessary_abstention_rate": 0.3,
        "safe_resolution_accuracy": 0.85, "intent_family_positive_coverage": 3,
        "unsupported_claim_count": 0, "citation_metadata_failure_count": 0,
        "draft_citation_count": 0, "expired_citation_count": 0,
    }
    if any(adjudicated_metrics.get(key) != value for key, value in expected.items()):
        raise EvidenceGateV2Error("adjudicated-metric-mismatch")
    if acceptance["verdict"] != "PASS" or not acceptance["hard_safety_requirements_pass"] or not acceptance["minimum_utility_requirements_pass"]:
        raise EvidenceGateV2Error("adjudicated-metric-mismatch: acceptance")
    original_artifact = {
        "task_id": "W3-001-CR1", "evaluation": "ORIGINAL_FROZEN_MAPPING",
        "status": "FAILED_INVALIDATED_BY_INCOMPLETE_RELEVANCE_MAPPING",
        "mapping_sha256": validated["original_mapping_sha256"],
        "output_sha256": sha256_file(root / config["outputs"]["holdout_v2_outputs"]),
        "gate_v1": original["v1_metrics"], "gate_v2": original["v2_metrics"],
        "acceptance": original["acceptance"], "verdict": "FAILED",
    }
    adjudicated_artifact = {
        "task_id": "W3-001-CR1", "evaluation": "POST_HOC_MAPPING_ADJUDICATION",
        "status": "PASS_AWAITING_FINAL_RE_REVIEW",
        "mapping_sha256": validated["adjudicated_mapping_sha256"],
        "mapping_audit_sha256": sha256_file(root / validated["config"]["mapping_audit"]),
        "overlay_sha256": sha256_file(root / validated["config"]["overlay"]),
        "gate_v2": adjudicated_metrics, "acceptance": acceptance, "verdict": "PASS",
        "limitation": "The holdout is a post-hoc adjudicated evaluation rather than a pristine untouched-label evaluation.",
    }
    comparison = {
        "task_id": "W3-001-CR1", "gate_v1": original["v1_metrics"],
        "gate_v2_original": original["v2_metrics"], "gate_v2_adjudicated": adjudicated_metrics,
        "delta_gate_v1_to_adjudicated_v2": {
            "answer_count": adjudicated_metrics["answer_count"] - original["v1_metrics"]["answer_count"],
            "positive_grounded_resolution_recall": round(adjudicated_metrics["positive_grounded_resolution_recall"] - original["v1_metrics"]["positive_grounded_resolution_recall"], 12),
            "safe_resolution_accuracy": round(adjudicated_metrics["safe_resolution_accuracy"] - original["v1_metrics"]["safe_resolution_accuracy"], 12),
            "unsafe_answer_rate": round(adjudicated_metrics["unsafe_answer_rate"] - original["v1_metrics"]["unsafe_answer_rate"], 12),
        },
        "original_verdict": "FAILED", "adjudicated_verdict": "PASS", "adjudicated_acceptance": acceptance,
    }
    expected_delta = comparison["delta_gate_v1_to_adjudicated_v2"]
    if expected_delta != {"answer_count": 6, "positive_grounded_resolution_recall": 0.6, "safe_resolution_accuracy": 0.3, "unsafe_answer_rate": 0.0}:
        raise EvidenceGateV2Error("adjudicated-metric-mismatch: delta")
    return {"original": original, "validated": validated, "original_artifact": original_artifact, "adjudicated_artifact": adjudicated_artifact, "comparison": comparison}


def finalize_adjudication(root: Path, config_path: Path) -> dict[str, Any]:
    payload = _adjudication_payload(root, config_path)
    adjudication = payload["validated"]["config"]
    outputs = adjudication["outputs"]
    write_json(root / outputs["original_metrics"], payload["original_artifact"])
    write_json(root / outputs["adjudicated_metrics"], payload["adjudicated_artifact"])
    write_json(root / outputs["adjudicated_comparison"], payload["comparison"])
    manifest = {
        "task_id": "W3-001-CR1", "status": "PASS_AWAITING_FINAL_RE_REVIEW",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "adjudication_config_sha256": sha256_file(root / ADJUDICATION_CONFIG_PATH),
        "mapping_audit_sha256": sha256_file(root / adjudication["mapping_audit"]),
        "overlay_sha256": sha256_file(root / adjudication["overlay"]),
        "original_mapping_sha256": payload["validated"]["original_mapping_sha256"],
        "adjudicated_mapping_sha256": payload["validated"]["adjudicated_mapping_sha256"],
        "original_output_sha256": sha256_file(root / payload["original"]["config"]["outputs"]["holdout_v2_outputs"]),
        "reproduction_output_sha256": sha256_file(root / payload["original"]["config"]["outputs"]["holdout_v2_reproduction"]),
        "original_verdict": "FAILED", "adjudicated_verdict": "PASS",
        "audit_rows": 10, "audit_defect_rows": 3, "overlay_rows": 3,
        "application_stage": "POST_HOLDOUT_RELEVANCE_METRICS_ONLY",
        "encoder_retrieval_generation_rerun": False,
        "original_outputs_immutable": True,
        "w3_002_state": "BLOCKED PENDING FINAL SENIOR RE-REVIEW",
        "limitation": "The holdout remains a post-hoc adjudicated evaluation rather than a pristine untouched-label evaluation.",
        "artifact_sha256": {
            key: sha256_file(root / outputs[key])
            for key in ("original_metrics", "adjudicated_metrics", "adjudicated_comparison")
        },
    }
    write_json(root / outputs["adjudication_manifest"], manifest)
    return {"status": "PASS", "original_verdict": "FAILED", "adjudicated_verdict": "PASS", "manifest": manifest, "comparison": payload["comparison"]}


def verify_adjudication(root: Path, config_path: Path) -> dict[str, Any]:
    payload = _adjudication_payload(root, config_path)
    adjudication = payload["validated"]["config"]
    outputs = adjudication["outputs"]
    expected = {
        "original_metrics": payload["original_artifact"],
        "adjudicated_metrics": payload["adjudicated_artifact"],
        "adjudicated_comparison": payload["comparison"],
    }
    for key, value in expected.items():
        if _load_json(root / outputs[key]) != value:
            raise EvidenceGateV2Error(f"adjudicated-metric-mismatch: {key}")
    manifest = _load_json(root / outputs["adjudication_manifest"])
    fixed = {
        "adjudication_config_sha256": sha256_file(root / ADJUDICATION_CONFIG_PATH),
        "mapping_audit_sha256": sha256_file(root / adjudication["mapping_audit"]),
        "overlay_sha256": sha256_file(root / adjudication["overlay"]),
        "original_mapping_sha256": payload["validated"]["original_mapping_sha256"],
        "adjudicated_mapping_sha256": payload["validated"]["adjudicated_mapping_sha256"],
        "original_output_sha256": sha256_file(root / payload["original"]["config"]["outputs"]["holdout_v2_outputs"]),
        "reproduction_output_sha256": sha256_file(root / payload["original"]["config"]["outputs"]["holdout_v2_reproduction"]),
    }
    if any(manifest.get(key) != value for key, value in fixed.items()) or manifest.get("original_verdict") != "FAILED" or manifest.get("adjudicated_verdict") != "PASS" or manifest.get("encoder_retrieval_generation_rerun") is not False:
        raise EvidenceGateV2Error("adjudicated-metric-mismatch: manifest")
    for key, expected_hash in manifest.get("artifact_sha256", {}).items():
        if sha256_file(root / outputs[key]) != expected_hash:
            raise EvidenceGateV2Error(f"adjudicated-metric-mismatch: manifest artifact {key}")
    return {"status": "PASS", "original_verdict": "FAILED", "adjudicated_verdict": "PASS", "original_metrics": payload["original"]["v2_metrics"], "adjudicated_metrics": payload["adjudicated_artifact"]["gate_v2"], "comparison": payload["comparison"], "manifest": manifest}


def verify_results(root: Path, config_path: Path, *, write: bool = True) -> dict[str, Any]:
    adjudication = verify_adjudication(root, config_path)
    original = _verify_original_tracked(root, config_path)
    result = {
        "task_id": "W3-001-CR1", "status": "PASS",
        "verification_scope": "tracked_frozen_outputs_plus_post_hoc_relevance_adjudication",
        "requires_model_cache_or_network": False,
        "encoder_retrieval_generation_rerun": False,
        "contract": original["contract"], "holdout_validation": original["holdout_validation"],
        "candidate_count": 9, "selected_policy": original["selection"]["selected_policy"],
        "design_metrics": original["selection"]["selected_metrics"],
        "gate_v1_holdout_metrics": original["v1_metrics"],
        "gate_v2_original_holdout_metrics": original["v2_metrics"],
        "original_verdict": "FAILED",
        "gate_v2_adjudicated_holdout_metrics": adjudication["adjudicated_metrics"],
        "adjudicated_verdict": "PASS",
        "adjudication_manifest": adjudication["manifest"],
        "primary_reproduction_identical": True,
        "w3_002_state": "BLOCKED PENDING FINAL SENIOR RE-REVIEW", "week4_started": False,
    }
    if write:
        write_json(root / original["config"]["outputs"]["validation"], result)
    return result
