"""W3-001 lifecycle, development selection, and tracked verification."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from payresolve_ai.evaluation.gold_mapping import normalize_query
from payresolve_ai.kb.validation import canonical_dataset_sha256
from payresolve_ai.retrieval.benchmark import _rank_queries, verify_contract as verify_retrieval_contract
from payresolve_ai.retrieval.corpus import load_jsonl

from .context import eligible_chunks
from .gate import build_idf
from .pipeline import development_metrics, run_case


class GroundedPipelineError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def load_configuration(root: Path, config_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    gate_path = root / config["gate_dev_config"]
    gate_config = json.loads(gate_path.read_text(encoding="utf-8"))
    retrieval_path = root / config["retrieval_config"]
    retrieval = json.loads(retrieval_path.read_text(encoding="utf-8"))
    if config["retriever_variant"] != "R0" or config["top_k"] != 3 or config["default_mode"] != "EVIDENCE_GATED":
        raise GroundedPipelineError("pipeline retrieval/mode contract mismatch")
    if config["gate_grid"] != {"min_top1_score": [0.4, 0.45, 0.5, 0.55], "min_weighted_query_coverage": [0.3, 0.45, 0.6], "ambiguity_score_gap": 0.03}:
        raise GroundedPipelineError("gate grid is not frozen 4x3 contract")
    extractive = config.get("extractive", {})
    weights = (extractive.get("sentence_overlap_weight"), extractive.get("chunk_score_weight"))
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 for value in weights) or abs(sum(weights) - 1.0) > 1e-12:
        raise GroundedPipelineError("invalid extractive weight contract")
    if retrieval["accepted_locked_artifact_sha256"]["locked_r0"] != config["frozen"]["retrieval_locked_r0_sha256"]:
        raise GroundedPipelineError("selected R0 contract mismatch")
    return config, gate_config, retrieval


def resolve_development_queries(root: Path, gate_config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = load_jsonl(root / gate_config["dataset_path"])
    w2 = {row["query_id"]: row for row in load_jsonl(root / gate_config["w2_mapping_path"])}
    resolved = []
    for row in rows:
        if row["source"] == "w2_gold_mapping_reference":
            mapping_id = row["w2_mapping_id"]
            if mapping_id not in w2 or w2[mapping_id]["split"] != "development":
                raise GroundedPipelineError(f"invalid W2 development reference: {mapping_id}")
            resolved.append({**w2[mapping_id], "gate_case_type": "positive_reference", "gate_source": row["source"]})
        else:
            resolved.append({**row, "split": "development", "gate_case_type": row["case_type"], "gate_source": row["source"]})
    return sorted(resolved, key=lambda row: row["query_id"])


def _csv_texts(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    return [row.get("text", "") for row in rows]


def validate_gate_development(root: Path, config_path: Path) -> dict[str, Any]:
    config, gate_config, retrieval = load_configuration(root, config_path)
    scenario_path, dataset_path = root / gate_config["scenario_path"], root / gate_config["dataset_path"]
    if sha256_file(scenario_path) != gate_config["frozen_scenario_sha256"] or sha256_file(dataset_path) != gate_config["frozen_dataset_sha256"]:
        raise GroundedPipelineError("frozen gate-development file hash mismatch")
    raw = load_jsonl(dataset_path); scenarios = load_jsonl(scenario_path); resolved = resolve_development_queries(root, gate_config)
    positive = [row for row in raw if row["source"] == "w2_gold_mapping_reference"]
    negative = [row for row in raw if row["source"] == "w3_gate_development"]
    if len(raw) != 20 or len(positive) != 10 or len(negative) != 10 or len(scenarios) != 10:
        raise GroundedPipelineError("gate development must contain 10 positive references and 10 negative probes")
    expected_types = gate_config["expected"]["negative_case_types"]
    if dict(sorted(Counter(row["case_type"] for row in negative).items())) != expected_types:
        raise GroundedPipelineError("negative development case-type distribution mismatch")
    ids = [row["query_id"] for row in resolved]; texts = [row["query_text"] for row in resolved]
    if len(ids) != len(set(ids)) or len({normalize_query(text) for text in texts}) != 20:
        raise GroundedPipelineError("gate development IDs/texts are not unique")
    w2_rows = load_jsonl(root / gate_config["w2_mapping_path"])
    dev_ids = {row["query_id"] for row in w2_rows if row["split"] == "development"}
    locked = [row for row in w2_rows if row["split"] == "locked_test"]
    if {row["w2_mapping_id"] for row in positive} != dev_ids or set(ids) & {row["query_id"] for row in locked}:
        raise GroundedPipelineError("development/locked membership contamination")
    locked_exact = {row["query_text"] for row in locked}; locked_normalized = {normalize_query(row["query_text"]) for row in locked}
    new_texts = [row["query_text"] for row in negative]
    locked_exact_overlap = sum(text in locked_exact for text in new_texts)
    locked_normalized_overlap = sum(normalize_query(text) in locked_normalized for text in new_texts)
    banking = {}
    for split, key in (("train", "banking77_train_path"), ("official_test", "banking77_test_path")):
        corpus = _csv_texts(root / gate_config[key]); exact = set(corpus); normalized = {normalize_query(text) for text in corpus}
        banking[split] = {"exact_overlap": sum(text in exact for text in texts), "normalized_overlap": sum(normalize_query(text) in normalized for text in texts), "contents_manually_inspected": False}
    if locked_exact_overlap or locked_normalized_overlap or any(value["exact_overlap"] or value["normalized_overlap"] for value in banking.values()):
        raise GroundedPipelineError("gate development overlap audit is non-zero")
    documents = load_jsonl(root / config["kb_documents"]); chunks = eligible_chunks(documents, date.fromisoformat(config["evaluation_as_of_date"]), retrieval["corpus"]["chunk_text_template"])
    eligible_ids = {row["chunk_id"] for row in chunks}
    all_ids = {f"{doc['document_id']}#{section['section_id']}" for doc in documents for section in doc["content_sections"]}
    for row in negative:
        if not set(row["approved_sections_reviewed"]) <= eligible_ids or not set(row["attractive_forbidden_evidence_ids"]) <= all_ids - eligible_ids:
            raise GroundedPipelineError(f"negative evidence review contract mismatch: {row['query_id']}")
    return {"status": "PASS", "cases": 20, "positive": 10, "negative": 10, "negative_case_types": expected_types, "w2_locked_query_id_overlap": 0, "w2_locked_exact_text_overlap": locked_exact_overlap, "w2_locked_normalized_text_overlap": locked_normalized_overlap, "banking77_overlap": banking, "official_test_contents_manually_inspected": False, "scenario_sha256": gate_config["frozen_scenario_sha256"], "dataset_sha256": gate_config["frozen_dataset_sha256"]}


def verify_contract(root: Path, config_path: Path) -> dict[str, Any]:
    config, _, retrieval = load_configuration(root, config_path)
    verify_retrieval_contract(root, root / config["retrieval_config"])
    frozen_paths = {"kb_raw_sha256": root / config["kb_documents"], "retrieval_locked_r0_sha256": root / retrieval["outputs"]["locked_r0"], "retrieval_locked_r1_sha256": root / retrieval["outputs"]["locked_r1"], "retrieval_metrics_sha256": root / retrieval["outputs"]["metrics"]}
    for key, path in frozen_paths.items():
        if sha256_file(path) != config["frozen"][key]:
            raise GroundedPipelineError(f"frozen input mismatch: {key}")
    documents = load_jsonl(root / config["kb_documents"])
    if canonical_dataset_sha256(documents) != config["frozen"]["kb_canonical_sha256"]:
        raise GroundedPipelineError("frozen canonical KB mismatch")
    return {"status": "PASS", "selected_retriever": "R0", "w2_contract": "PASS", "official_banking77_test_accessed": False}


def _runtime_material(root: Path, config_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, float]]:
    config, gate_config, retrieval = load_configuration(root, config_path)
    queries = resolve_development_queries(root, gate_config)
    documents = load_jsonl(root / config["kb_documents"])
    chunks = eligible_chunks(documents, date.fromisoformat(config["evaluation_as_of_date"]), retrieval["corpus"]["chunk_text_template"])
    idf = build_idf(chunks, config["tokenizer"]["stopwords"])
    return config, queries, chunks, idf


def build_dev_runtime(root: Path, config_path: Path, *, write: bool = True) -> dict[str, Any]:
    verify_contract(root, config_path); validate_gate_development(root, config_path)
    config, queries, _, _ = _runtime_material(root, config_path)
    retrieval_config = json.loads((root / config["retrieval_config"]).read_text(encoding="utf-8"))
    rankings, predictions = _rank_queries(root, retrieval_config, queries, None)
    w2_dev_rows = load_jsonl(root / retrieval_config["outputs"]["dev_rankings"])
    expected_r0 = {row["query_id"]: row["rankings"] for row in w2_dev_rows if row["variant"] == "R0"}
    for row in rankings:
        if row["query_id"] in expected_r0 and row["rankings"] != expected_r0[row["query_id"]]:
            raise GroundedPipelineError(f"positive R0 ranking drift: {row['query_id']}")
    if write:
        write_jsonl(root / config["outputs"]["rankings"], rankings)
        write_jsonl(root / config["outputs"]["predictions"], predictions)
    return {"status": "PASS", "rankings": rankings, "predictions": predictions, "cases": 20, "positive_r0_matches_w2": 10}


def _grid(config: dict[str, Any]) -> list[dict[str, float]]:
    return [{"min_top1_score": score, "min_weighted_query_coverage": coverage, "ambiguity_score_gap": config["gate_grid"]["ambiguity_score_gap"]} for score in config["gate_grid"]["min_top1_score"] for coverage in config["gate_grid"]["min_weighted_query_coverage"]]


def _tracked_inputs(root: Path, config_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, float], list[dict[str, Any]], list[dict[str, Any]]]:
    config, queries, chunks, idf = _runtime_material(root, config_path)
    rankings = load_jsonl(root / config["outputs"]["rankings"]); predictions = load_jsonl(root / config["outputs"]["predictions"])
    ids = {row["query_id"] for row in queries}
    if {row["query_id"] for row in rankings} != ids or {row["query_id"] for row in predictions} != ids or len(rankings) != 20 or len(predictions) != 20:
        raise GroundedPipelineError("tracked runtime membership mismatch")
    eligible_ids = {row["chunk_id"] for row in chunks}
    if any(len(row["rankings"]) != 3 or not {item["chunk_id"] for item in row["rankings"]} <= eligible_ids for row in rankings):
        raise GroundedPipelineError("tracked R0 ranking contains invalid evidence")
    return config, queries, chunks, idf, rankings, predictions


def _evaluate_candidate(config: dict[str, Any], queries: list[dict[str, Any]], chunks: list[dict[str, Any]], idf: dict[str, float], rankings: list[dict[str, Any]], predictions: list[dict[str, Any]], candidate: dict[str, float]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rank_by_id = {row["query_id"]: row for row in rankings}; prediction_by_id = {row["query_id"]: row for row in predictions}
    outputs = [run_case(query, rank_by_id[query["query_id"]], prediction_by_id[query["query_id"]], chunks, idf, config, candidate) for query in queries]
    return outputs, development_metrics(queries, outputs, date.fromisoformat(config["evaluation_as_of_date"]))


def select_gate(root: Path, config_path: Path, *, write: bool = True) -> dict[str, Any]:
    verify_contract(root, config_path); validate_gate_development(root, config_path)
    config, queries, chunks, idf, rankings, predictions = _tracked_inputs(root, config_path)
    candidates = []
    for policy in _grid(config):
        outputs, metrics = _evaluate_candidate(config, queries, chunks, idf, rankings, predictions, policy)
        candidate_id = f"S{policy['min_top1_score']:.2f}_C{policy['min_weighted_query_coverage']:.2f}"
        candidates.append({"candidate_id": candidate_id, "policy": policy, "metrics": metrics, "outcomes": [{"query_id": row["query_id"], "response_type": row["response_type"], "reason_code": row["gate"]["reason_code"]} for row in outputs]})
    candidates.sort(key=lambda row: row["candidate_id"])
    selected = min(candidates, key=lambda row: (-row["metrics"]["safe_resolution_accuracy"], row["metrics"]["unsafe_answer_rate"], -row["metrics"]["positive_grounded_resolution_recall"], -row["metrics"]["negative_abstention_accuracy"], row["policy"]["min_top1_score"], row["policy"]["min_weighted_query_coverage"]))
    membership = hashlib.sha256(("\n".join(sorted(row["query_id"] for row in queries)) + "\n").encode()).hexdigest()
    candidate_payload = {"task_id": "W3-001", "development_only": True, "candidate_count": 12, "candidates": candidates}
    if write: write_json(root / config["outputs"]["candidate_metrics"], candidate_payload)
    selection = {"task_id": "W3-001", "status": "FROZEN_DEVELOPMENT_SELECTION", "development_only": True, "selected_candidate_id": selected["candidate_id"], "selected_policy": selected["policy"], "selected_metrics": selected["metrics"], "selection_rule": config["selection_tie_break"], "development_membership_sha256": membership, "pipeline_config_sha256": sha256_file(config_path), "gate_dev_config_sha256": sha256_file(root / config["gate_dev_config"]), "candidate_metrics_sha256": sha256_file(root / config["outputs"]["candidate_metrics"]) if write else None, "locked_query_ids_used": 0, "week3_critical_set_used": False}
    if write: write_json(root / config["outputs"]["selection"], selection)
    return {"candidate_metrics": candidate_payload, "selection": selection}


def run_dev(root: Path, config_path: Path, run_label: str, *, write: bool = True) -> dict[str, Any]:
    config, queries, chunks, idf, rankings, predictions = _tracked_inputs(root, config_path)
    selection = json.loads((root / config["outputs"]["selection"]).read_text(encoding="utf-8"))
    outputs, metrics = _evaluate_candidate(config, queries, chunks, idf, rankings, predictions, selection["selected_policy"])
    if write:
        key = "primary_outputs" if run_label == "primary" else "reproduction_outputs"
        write_jsonl(root / config["outputs"][key], outputs)
        if run_label == "primary": write_json(root / config["outputs"]["metrics"], metrics)
    return {"status": "PASS", "run_label": run_label, "outputs": outputs, "metrics": metrics}


def finalize(root: Path, config_path: Path) -> dict[str, Any]:
    config, _, _, idf, _, _ = _tracked_inputs(root, config_path)
    primary = root / config["outputs"]["primary_outputs"]; reproduction = root / config["outputs"]["reproduction_outputs"]
    if primary.read_bytes() != reproduction.read_bytes():
        raise GroundedPipelineError("primary/reproducibility outputs differ")
    artifact_names = ("rankings", "predictions", "candidate_metrics", "selection", "primary_outputs", "reproduction_outputs", "metrics")
    manifest = {"task_id": "W3-001", "status": "PARTIAL_UTILITY_NOT_DEMONSTRATED", "created_at": datetime.now(timezone.utc).isoformat(), "external_llm_provider_status": config["external_llm_provider_status"], "selected_retriever": "R0", "selected_gate": json.loads((root / config["outputs"]["selection"]).read_text(encoding="utf-8"))["selected_policy"], "pipeline_config_sha256": sha256_file(config_path), "gate_dev_config_sha256": sha256_file(root / config["gate_dev_config"]), "idf_sha256": hashlib.sha256(json.dumps(idf, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), "artifact_sha256": {name: sha256_file(root / config["outputs"][name]) for name in artifact_names}, "primary_reproduction_sha256": sha256_file(primary), "primary_reproduction_identical": True, "frozen": config["frozen"], "week3_critical_set_created": False, "w3_002_started": False}
    write_json(root / config["outputs"]["manifest"], manifest)
    return manifest


def verify_results(root: Path, config_path: Path, *, write: bool = True) -> dict[str, Any]:
    contract = verify_contract(root, config_path); dataset = validate_gate_development(root, config_path)
    config, queries, chunks, idf, rankings, predictions = _tracked_inputs(root, config_path)
    recomputed = select_gate(root, config_path, write=False)
    stored_candidates = json.loads((root / config["outputs"]["candidate_metrics"]).read_text(encoding="utf-8"))
    stored_selection = json.loads((root / config["outputs"]["selection"]).read_text(encoding="utf-8"))
    expected_selection = recomputed["selection"]
    expected_selection["candidate_metrics_sha256"] = sha256_file(root / config["outputs"]["candidate_metrics"])
    if stored_candidates != recomputed["candidate_metrics"] or stored_selection != expected_selection:
        raise GroundedPipelineError("candidate metrics or selected gate tampering detected")
    outputs, metrics = _evaluate_candidate(config, queries, chunks, idf, rankings, predictions, stored_selection["selected_policy"])
    for key in ("primary_outputs", "reproduction_outputs"):
        if load_jsonl(root / config["outputs"][key]) != outputs:
            raise GroundedPipelineError(f"pipeline output tampering detected: {key}")
    if json.loads((root / config["outputs"]["metrics"]).read_text(encoding="utf-8")) != metrics:
        raise GroundedPipelineError("development metric tampering detected")
    manifest = json.loads((root / config["outputs"]["manifest"]).read_text(encoding="utf-8"))
    if manifest["status"] != "PARTIAL_UTILITY_NOT_DEMONSTRATED" or manifest["pipeline_config_sha256"] != sha256_file(config_path):
        raise GroundedPipelineError("manifest contract mismatch")
    for name, expected_hash in manifest["artifact_sha256"].items():
        if sha256_file(root / config["outputs"][name]) != expected_hash:
            raise GroundedPipelineError(f"manifest artifact hash mismatch: {name}")
    result = {"task_id": "W3-001", "status": "PASS", "lifecycle_status": "PARTIAL_UTILITY_NOT_DEMONSTRATED", "verification_scope": "tracked_evidence_only", "requires_model_cache_or_network": False, "contract": contract, "development_dataset": dataset, "candidate_policies": 12, "selected_policy": stored_selection["selected_policy"], "development_metrics": metrics, "primary_reproduction_identical": True, "citation_contract": "PASS", "unsupported_claim_count": metrics["unsupported_claim_count"], "selected_retriever": "R0", "w3_002_started": False, "week3_critical_set_created": False}
    if write: write_json(root / config["outputs"]["validation"], result)
    return result


def verify_runtime_reproduction(root: Path, config_path: Path) -> dict[str, Any]:
    stored_config, _, _, _, stored_rankings, stored_predictions = _tracked_inputs(root, config_path)
    runtime = build_dev_runtime(root, config_path, write=False)
    if runtime["rankings"] != stored_rankings or runtime["predictions"] != stored_predictions:
        raise GroundedPipelineError("runtime rankings/predictions differ from tracked evidence")
    return {"task_id": "W3-001", "status": "PASS", "verification_scope": "optional_local_runtime", "requires_model_cache": True, "cases": 20, "selected_retriever": stored_config["retriever_variant"]}
