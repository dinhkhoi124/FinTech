"""Controlled W2-003 R0/R1 benchmark lifecycle and validation."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import platform
import time
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from payresolve_ai.baselines.semantic import _load_encoder
from payresolve_ai.evaluation.gold_mapping import SCENARIO_QUERY_FIELDS, canonical_rows_sha256, projected_sha256
from payresolve_ai.kb.validation import canonical_dataset_sha256
from payresolve_ai.retrieval.corpus import build_corpus, canonical_bytes, load_jsonl, sha256_bytes, validate_corpus
from payresolve_ai.retrieval.dense import rank, r0_scores, r1_scores, validate_embeddings


class RetrievalBenchmarkError(RuntimeError):
    pass


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def load_config(root: Path, config_path: Path, *, require_local_model: bool = False) -> dict[str, Any]:
    config = _json(config_path)
    validate_encoder_contract(config["encoder"])
    if config["retrieval"]["lambda_grid"] != [0.05, 0.1, 0.15, 0.2] or config["retrieval"]["top_k"] != 3:
        raise RetrievalBenchmarkError("retrieval contract mismatch")
    if _sha(root / config["classifier"]["config"]) != config["classifier"]["config_sha256"]:
        raise RetrievalBenchmarkError("classifier config hash mismatch")
    if require_local_model:
        parameters = root / config["classifier"]["parameters"]
        if not parameters.is_file() or _sha(parameters) != config["classifier"]["parameters_sha256"]:
            raise RetrievalBenchmarkError("classifier parameters hash mismatch")
    return config


def validate_encoder_contract(encoder: dict[str, Any]) -> None:
    if encoder.get("revision") != "1110a243fdf4706b3f48f1d95db1a4f5529b4d41" or encoder.get("dimension") != 384 or encoder.get("normalize_embeddings") is not True:
        raise RetrievalBenchmarkError("encoder contract mismatch")


def verify_contract(root: Path, config_path: Path) -> dict[str, Any]:
    config = load_config(root, config_path)
    kb = root / config["kb_documents"]
    mapping = root / config["gold_mapping"]
    if _sha(kb) != config["frozen_hashes"]["kb_raw_sha256"]:
        raise RetrievalBenchmarkError("frozen KB raw hash mismatch")
    docs = load_jsonl(kb)
    if canonical_dataset_sha256(docs) != config["frozen_hashes"]["kb_canonical_sha256"]:
        raise RetrievalBenchmarkError("frozen KB canonical hash mismatch")
    rows = load_jsonl(mapping)
    gold_config = _json(root / config["gold_config"])
    scenarios = load_jsonl(root / gold_config["scenario_plan_path"])
    if canonical_rows_sha256(scenarios) != config["frozen_hashes"]["scenario_sha256"]:
        raise RetrievalBenchmarkError("frozen scenario hash mismatch")
    if projected_sha256(rows, SCENARIO_QUERY_FIELDS) != config["frozen_hashes"]["query_sha256"]:
        raise RetrievalBenchmarkError("frozen query dataset hash mismatch")
    if sha256_bytes(canonical_bytes(sorted(rows, key=lambda row: row["query_id"]))) != config["frozen_hashes"]["mapping_sha256"]:
        raise RetrievalBenchmarkError("frozen mapping hash mismatch")
    memberships = {}
    for split in ("development", "locked_test"):
        ids = sorted(row["query_id"] for row in rows if row["split"] == split)
        memberships[split] = hashlib.sha256(("\n".join(ids) + "\n").encode()).hexdigest()
    if memberships["development"] != config["frozen_hashes"]["development_membership_sha256"] or memberships["locked_test"] != config["frozen_hashes"]["locked_membership_sha256"]:
        raise RetrievalBenchmarkError("frozen membership hash mismatch")
    if len(rows) != 60 or Counter(row["split"] for row in rows) != {"development": 10, "locked_test": 50}:
        raise RetrievalBenchmarkError("mapping split contract mismatch")
    return {"status": "PASS", "rows": 60, "official_test_accessed": False, "memberships": memberships}


def _encoder(root: Path, config: dict[str, Any]):
    semantic = _json(root / config["classifier"]["config"])
    semantic["cache"]["huggingface_home"] = config["encoder"]["huggingface_home"]
    return _load_encoder(root, semantic)


def build(root: Path, config_path: Path) -> dict[str, Any]:
    verify_contract(root, config_path)
    config = load_config(root, config_path, require_local_model=True)
    docs = load_jsonl(root / config["kb_documents"])
    chunks = build_corpus(docs, date.fromisoformat(config["evaluation_as_of_date"]), config["corpus"]["chunk_text_template"])
    validate_corpus(chunks, date.fromisoformat(config["evaluation_as_of_date"]))
    document_count = len({row["document_id"] for row in chunks})
    if document_count != config["corpus"]["expected_documents"] or len(chunks) != config["corpus"]["expected_chunks"]:
        raise RetrievalBenchmarkError(f"corpus count mismatch: {document_count} documents, {len(chunks)} chunks")
    encoder = _encoder(root, config)
    embeddings = encoder.encode_function([row["text"] for row in chunks])
    validate_embeddings(embeddings, len(chunks), config["encoder"]["dimension"])
    cache = root / config["cache"]["directory"]
    cache.mkdir(parents=True, exist_ok=True)
    np.save(cache / "corpus_embeddings.npy", embeddings, allow_pickle=False)
    _write_jsonl(cache / "corpus.jsonl", chunks)
    manifest = {
        "task_id": "W2-003", "status": "FROZEN", "documents": document_count, "chunks": len(chunks),
        "draft_chunks": 0, "expired_chunks": 0, "duplicate_chunk_ids": 0, "missing_sections": 0,
        "chunk_order": "chunk_id_ascending", "chunk_text_template": config["corpus"]["chunk_text_template"],
        "chunk_alignment_sha256": hashlib.sha256(("\n".join(row["chunk_id"] for row in chunks) + "\n").encode()).hexdigest(),
        "corpus_sha256": sha256_bytes(canonical_bytes(chunks)), "embedding_shape": list(embeddings.shape),
        "embedding_sha256": hashlib.sha256(embeddings.tobytes()).hexdigest(), "encoder": encoder.provenance,
    }
    _write_json(root / config["outputs"]["corpus_manifest"], manifest)
    return manifest


def _load_classifier(root: Path, config: dict[str, Any]) -> tuple[list[str], np.ndarray, np.ndarray]:
    payload = json.loads(gzip.decompress((root / config["classifier"]["parameters"]).read_bytes()))
    if payload["encoder"]["revision"] != config["encoder"]["revision"] or payload["encoder"]["normalize_embeddings"] is not True:
        raise RetrievalBenchmarkError("portable classifier encoder mismatch")
    return payload["classes"], np.asarray(payload["coefficients"], dtype=np.float64), np.asarray(payload["intercept"], dtype=np.float64)


def _predict(embeddings: np.ndarray, classes: list[str], coef: np.ndarray, intercept: np.ndarray) -> list[tuple[str, float]]:
    logits = embeddings.astype(np.float64) @ coef.T + intercept
    logits -= logits.max(axis=1, keepdims=True)
    probabilities = np.exp(logits); probabilities /= probabilities.sum(axis=1, keepdims=True)
    indices = probabilities.argmax(axis=1)
    return [(classes[index], float(probabilities[row, index])) for row, index in enumerate(indices)]


def _load_runtime(root: Path, config: dict[str, Any]) -> tuple[list[dict[str, Any]], np.ndarray]:
    cache = root / config["cache"]["directory"]
    chunks = load_jsonl(cache / "corpus.jsonl")
    embeddings = np.load(cache / "corpus_embeddings.npy", allow_pickle=False)
    validate_embeddings(embeddings, len(chunks), config["encoder"]["dimension"])
    manifest = _json(root / config["outputs"]["corpus_manifest"])
    if hashlib.sha256(("\n".join(row["chunk_id"] for row in chunks) + "\n").encode()).hexdigest() != manifest["chunk_alignment_sha256"]:
        raise RetrievalBenchmarkError("corpus alignment hash mismatch")
    return chunks, embeddings


def _rank_queries(root: Path, config: dict[str, Any], queries: list[dict[str, Any]], boost: float | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    chunks, corpus_embeddings = _load_runtime(root, config)
    encoder = _encoder(root, config)
    query_embeddings = encoder.encode_function([row["query_text"] for row in queries])
    validate_embeddings(query_embeddings, len(queries), config["encoder"]["dimension"])
    classes, coef, intercept = _load_classifier(root, config)
    predictions = _predict(query_embeddings, classes, coef, intercept)
    ranked, diagnostics = [], []
    ids = [row["chunk_id"] for row in chunks]; scopes = [row["intent_scope"] for row in chunks]
    for query, embedding, prediction in zip(queries, query_embeddings, predictions, strict=True):
        base = r0_scores(embedding, corpus_embeddings)
        scores = base if boost is None else r1_scores(base, prediction[0], scopes, boost, tuple(config["retrieval"]["lambda_grid"]))
        ranked.append({"query_id": query["query_id"], "rankings": rank(scores, ids, 3)})
        diagnostics.append({"query_id": query["query_id"], "split": query["split"], "gold_intent": query["gold_intent"], "predicted_intent": prediction[0], "diagnostic_confidence": prediction[1], "prediction_correct": prediction[0] == query["gold_intent"]})
    return ranked, diagnostics


def metrics(queries: list[dict[str, Any]], rankings: list[dict[str, Any]], status_by_chunk: dict[str, str]) -> dict[str, Any]:
    by_id = {row["query_id"]: row for row in rankings}
    answer = [row for row in queries if row["expected_response_type"] == "ANSWER"]
    hit1 = recall3 = reciprocal = complete = relaxed1 = relaxed3 = 0.0
    for query in answer:
        ids = [item["chunk_id"] for item in by_id[query["query_id"]]["rankings"]]
        gold = set(query["gold_evidence_ids"]); relaxed = gold | set(query["acceptable_evidence_ids"])
        hit1 += ids[0] in gold
        recall3 += len(gold & set(ids)) / len(gold)
        ranks = [index + 1 for index, item in enumerate(ids) if item in gold]
        reciprocal += 1.0 / min(ranks) if ranks else 0.0
        complete += gold <= set(ids)
        relaxed1 += ids[0] in relaxed; relaxed3 += bool(relaxed & set(ids))
    count = len(answer)
    forbidden = {item for query in queries for item in query["forbidden_evidence_ids"]}
    all_rankings = [item for row in rankings for item in row["rankings"]]
    statuses = status_by_chunk
    missing_status = sorted({item["chunk_id"] for item in all_rankings} - set(statuses))
    if missing_status:
        raise RetrievalBenchmarkError(f"ranking status unknown for chunk: {missing_status[0]}")
    top1 = [row["rankings"][0] for row in rankings]
    draft1 = sum(statuses.get(item["chunk_id"]) == "DRAFT" for item in top1) / len(top1)
    draft3 = sum(any(statuses.get(item["chunk_id"]) == "DRAFT" for item in row["rankings"]) for row in rankings) / len(rankings)
    expired1 = sum(statuses.get(item["chunk_id"]) == "EXPIRED" for item in top1) / len(top1)
    expired3 = sum(any(statuses.get(item["chunk_id"]) == "EXPIRED" for item in row["rankings"]) for row in rankings) / len(rankings)
    return {
        "answer_queries": count, "safety_queries": len(queries) - count,
        "strict_hit_at_1": hit1 / count, "strict_recall_at_3": recall3 / count,
        "strict_mrr_at_3": reciprocal / count, "complete_gold_coverage_at_3": complete / count,
        "relaxed_hit_at_1": relaxed1 / count, "relaxed_hit_at_3": relaxed3 / count,
        "draft_leakage_at_1": draft1, "draft_leakage_at_3": draft3,
        "expired_leakage_at_1": expired1, "expired_leakage_at_3": expired3,
        "wrong_status_leakage_rate": sum(statuses.get(item["chunk_id"]) in {"DRAFT", "EXPIRED"} for item in all_rankings) / len(all_rankings),
        "forbidden_evidence_retrieval_rate": sum(item["chunk_id"] in forbidden for item in all_rankings) / len(all_rankings),
    }


def select_r1(root: Path, config_path: Path) -> dict[str, Any]:
    config = load_config(root, config_path, require_local_model=True); queries = [row for row in load_jsonl(root / config["gold_mapping"]) if row["split"] == "development"]
    if len(queries) != 10:
        raise RetrievalBenchmarkError("selection must use exactly ten development queries")
    runtime_chunks, _ = _load_runtime(root, config); statuses = {row["chunk_id"]: row["status"] for row in runtime_chunks}
    r0, diagnostics = _rank_queries(root, config, queries, None); r0_metric = metrics(queries, r0, statuses)
    grid = []
    for boost in config["retrieval"]["lambda_grid"]:
        rows, _ = _rank_queries(root, config, queries, boost); grid.append({"lambda": boost, "metrics": metrics(queries, rows, statuses)})
    selected = choose_lambda(grid)
    payload = {"task_id": "W2-003", "status": "FROZEN_PRELOCKED", "development_query_ids": sorted(row["query_id"] for row in queries), "locked_evaluated": False, "r0_metrics": r0_metric, "lambda_grid": grid, "selected_lambda": selected["lambda"], "selection_rule": config["retrieval"]["tie_break"], "retrieval_config_sha256": _sha(config_path)}
    _write_json(root / config["outputs"]["dev_selection"], payload)
    _write_jsonl(root / config["outputs"]["classifier_predictions"], diagnostics)
    return payload


def choose_lambda(grid: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply the preregistered metric and tie-break order."""
    return max(grid, key=lambda row: (row["metrics"]["strict_mrr_at_3"], row["metrics"]["strict_hit_at_1"], row["metrics"]["strict_recall_at_3"], -row["lambda"]))


def audit_dev_selection(root: Path, config_path: Path) -> dict[str, Any]:
    """Reproduce frozen development rankings without performing selection again."""
    verify_contract(root, config_path)
    config = load_config(root, config_path, require_local_model=True)
    selection = _json(root / config["outputs"]["dev_selection"])
    validate_frozen_selection(selection, config["frozen_selection_config_sha256"])
    all_queries = load_jsonl(root / config["gold_mapping"])
    development = sorted(
        (row for row in all_queries if row["split"] == "development"),
        key=lambda row: row["query_id"],
    )
    locked_ids = [row["query_id"] for row in all_queries if row["split"] == "locked_test"]
    validate_selection_membership(selection["development_query_ids"], locked_ids)
    if [row["query_id"] for row in development] != selection["development_query_ids"]:
        raise RetrievalBenchmarkError("frozen development query IDs mismatch")
    runtime_chunks, _ = _load_runtime(root, config)
    statuses = {row["chunk_id"]: row["status"] for row in runtime_chunks}
    rows: list[dict[str, Any]] = []
    r0, diagnostics = _rank_queries(root, config, development, None)
    predicted = {row["query_id"]: row["predicted_intent"] for row in diagnostics}
    recomputed_r0 = metrics(development, r0, statuses)
    if recomputed_r0 != selection["r0_metrics"]:
        raise RetrievalBenchmarkError("development R0 metrics differ from frozen selection")
    for item in r0:
        rows.append({"query_id": item["query_id"], "variant": "R0", "lambda": None, "predicted_intent": predicted[item["query_id"]], "rankings": item["rankings"]})
    recomputed_grid = []
    for boost in config["retrieval"]["lambda_grid"]:
        variant_rows, variant_predictions = _rank_queries(root, config, development, boost)
        if {row["query_id"]: row["predicted_intent"] for row in variant_predictions} != predicted:
            raise RetrievalBenchmarkError("classifier predictions changed across development variants")
        item_metrics = metrics(development, variant_rows, statuses)
        recomputed_grid.append({"lambda": boost, "metrics": item_metrics})
        for item in variant_rows:
            rows.append({"query_id": item["query_id"], "variant": f"R1_lambda_{boost:.2f}", "lambda": boost, "predicted_intent": predicted[item["query_id"]], "rankings": item["rankings"]})
    if recomputed_grid != selection["lambda_grid"]:
        raise RetrievalBenchmarkError("development grid metrics differ from frozen selection")
    if choose_lambda(recomputed_grid)["lambda"] != selection["selected_lambda"]:
        raise RetrievalBenchmarkError("development selected lambda differs from frozen selection")
    variant_order = {"R0": 0, "R1_lambda_0.05": 1, "R1_lambda_0.10": 2, "R1_lambda_0.15": 3, "R1_lambda_0.20": 4}
    rows.sort(key=lambda row: (row["query_id"], variant_order[row["variant"]]))
    _write_jsonl(root / config["outputs"]["dev_rankings"], rows)
    return {"status": "PASS", "rows": len(rows), "queries": len(development), "variants_per_query": 5, "selected_lambda": selection["selected_lambda"], "metrics_match": True}


def verify_prelocked(root: Path, config_path: Path) -> dict[str, Any]:
    verify_contract(root, config_path); config = load_config(root, config_path); selection = _json(root / config["outputs"]["dev_selection"])
    validate_frozen_selection(selection, config["frozen_selection_config_sha256"])
    validate_selection_membership(selection["development_query_ids"], [row["query_id"] for row in load_jsonl(root / config["gold_mapping"]) if row["split"] == "locked_test"])
    return {"status": "PASS", "selected_lambda": selection["selected_lambda"], "locked_evaluated": False}


def validate_frozen_selection(selection: dict[str, Any], config_hash: str) -> None:
    if selection.get("status") != "FROZEN_PRELOCKED" or selection.get("locked_evaluated") is not False or selection.get("retrieval_config_sha256") != config_hash:
        raise RetrievalBenchmarkError("locked evaluation requires unchanged frozen selection manifest")


def validate_selection_membership(development_ids: list[str], locked_ids: list[str]) -> None:
    if len(development_ids) != 10 or set(development_ids) & set(locked_ids):
        raise RetrievalBenchmarkError("development/locked membership leakage")


def assert_reproducible(primary: dict[str, Any], rerun: dict[str, Any], tolerance: float) -> None:
    for variant in ("r0", "r1"):
        first = primary["stable"][variant]; second = rerun["stable"][variant]
        if [row["query_id"] for row in first] != [row["query_id"] for row in second]:
            raise RetrievalBenchmarkError("reproducibility query alignment mismatch")
        for left, right in zip(first, second, strict=True):
            if [item["chunk_id"] for item in left["rankings"]] != [item["chunk_id"] for item in right["rankings"]]:
                raise RetrievalBenchmarkError("reproducibility ranking mismatch")
            if not np.allclose([item["score"] for item in left["rankings"]], [item["score"] for item in right["rankings"]], rtol=0.0, atol=tolerance):
                raise RetrievalBenchmarkError("reproducibility score mismatch")
    if primary["stable"]["metrics"] != rerun["stable"]["metrics"] or primary["stable"]["paired"] != rerun["stable"]["paired"]:
        raise RetrievalBenchmarkError("reproducibility metric or paired mismatch")


def _paired(queries: list[dict[str, Any]], r0: list[dict[str, Any]], r1: list[dict[str, Any]]) -> dict[str, Any]:
    a = {row["query_id"]: row for row in r0}; b = {row["query_id"]: row for row in r1}; rows=[]; counts=Counter()
    for query in queries:
        if query["expected_response_type"] != "ANSWER": continue
        gold=set(query["gold_evidence_ids"])
        def first(row):
            values=[i+1 for i,x in enumerate(row["rankings"]) if x["chunk_id"] in gold]; return min(values) if values else 4
        ra, rb=first(a[query["query_id"]]), first(b[query["query_id"]]); outcome="WIN" if rb<ra else "LOSS" if rb>ra else "TIE"; counts[outcome]+=1
        topa=a[query["query_id"]]["rankings"][0]["chunk_id"] in gold; topb=b[query["query_id"]]["rankings"][0]["chunk_id"] in gold
        category="r1_top1_corrected_r0_error" if topb and not topa else "r1_top1_broke_r0_success" if topa and not topb else "both_top1_correct" if topa else "both_top1_incorrect"; counts[category]+=1
        rows.append({"query_id":query["query_id"],"r0_first_gold_rank":ra if ra<=3 else None,"r1_first_gold_rank":rb if rb<=3 else None,"outcome":outcome,"top1_category":category})
    for key in ("WIN","LOSS","TIE","r1_top1_corrected_r0_error","r1_top1_broke_r0_success","both_top1_correct","both_top1_incorrect"):
        counts.setdefault(key,0)
    return {"counts":dict(counts),"rows":rows}


def run_locked(root: Path, config_path: Path, run_label: str) -> dict[str, Any]:
    if run_label not in {"primary","reproducibility_rerun"}: raise RetrievalBenchmarkError("invalid run label")
    verify_prelocked(root, config_path); config=load_config(root, config_path, require_local_model=True); selection=_json(root/config["outputs"]["dev_selection"])
    queries=[row for row in load_jsonl(root/config["gold_mapping"]) if row["split"]=="locked_test"]
    started=time.perf_counter(); r0, d0=_rank_queries(root,config,queries,None); r1,_=_rank_queries(root,config,queries,selection["selected_lambda"]); elapsed=time.perf_counter()-started
    runtime_chunks, _ = _load_runtime(root, config); statuses={row["chunk_id"]:row["status"] for row in runtime_chunks}
    m0,m1=metrics(queries,r0,statuses),metrics(queries,r1,statuses); paired=_paired(queries,r0,r1)
    cache=root/config["cache"]["directory"]; cache.mkdir(parents=True,exist_ok=True)
    stable={"r0":r0,"r1":r1,"metrics":{"r0":m0,"r1":m1},"paired":paired}
    stable_hash=hashlib.sha256(json.dumps(stable,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
    run={"run_label":run_label,"stable_sha256":stable_hash,"runtime_seconds":elapsed,"stable":stable}
    _write_json(cache/f"locked_{run_label}.json",run)
    if run_label=="primary":
        _write_jsonl(root/config["outputs"]["locked_r0"],r0); _write_jsonl(root/config["outputs"]["locked_r1"],r1)
        existing=load_jsonl(root/config["outputs"]["classifier_predictions"]); _write_jsonl(root/config["outputs"]["classifier_predictions"],existing+d0)
    else:
        primary=_json(cache/"locked_primary.json")
        assert_reproducible(primary,run,config["retrieval"]["score_tolerance"])
    return {"run_label":run_label,"metrics":stable["metrics"],"paired":paired["counts"],"runtime_seconds":elapsed,"stable_sha256":stable_hash}


def finalize(root: Path, config_path: Path) -> dict[str, Any]:
    config=load_config(root,config_path); cache=root/config["cache"]["directory"]; primary=_json(cache/"locked_primary.json"); rerun=_json(cache/"locked_reproducibility_rerun.json")
    assert_reproducible(primary,rerun,config["retrieval"]["score_tolerance"])
    stable=primary["stable"]; m0,m1=stable["metrics"]["r0"],stable["metrics"]["r1"]
    keys=("strict_mrr_at_3","strict_hit_at_1","strict_recall_at_3"); left=tuple(m1[k] for k in keys); right=tuple(m0[k] for k in keys); selected="R1" if left>right else "R0"
    decision={"selected_retriever":selected,"decision_metrics":list(keys),"r0":m0,"r1":m1,"delta_r1_minus_r0":{k:m1[k]-m0[k] for k in keys},"safety_gate_pass":m0["wrong_status_leakage_rate"]==m1["wrong_status_leakage_rate"]==0.0}
    _write_json(root/config["outputs"]["metrics"],{"task_id":"W2-003","decision":decision,"primary":stable["metrics"]})
    for key in ("WIN","LOSS","TIE","r1_top1_corrected_r0_error","r1_top1_broke_r0_success","both_top1_correct","both_top1_incorrect"):
        stable["paired"]["counts"].setdefault(key,0)
    _write_json(root/config["outputs"]["paired"],stable["paired"])
    _error_analysis(root,config)
    predictions=load_jsonl(root/config["outputs"]["classifier_predictions"])
    manifest={"task_id":"W2-003","status":"FINALIZED","retrieval_config_sha256":_sha(config_path),"frozen_inputs":config["frozen_hashes"],"corpus_manifest_sha256":_sha(root/config["outputs"]["corpus_manifest"]),"dev_selection_sha256":_sha(root/config["outputs"]["dev_selection"]),"implementation_sha256":{"corpus":_sha(Path(__file__).with_name("corpus.py")),"dense":_sha(Path(__file__).with_name("dense.py")),"benchmark":_sha(Path(__file__))},"encoder":config["encoder"],"classifier":config["classifier"],"classifier_diagnostic":{"queries":len(predictions),"correct":sum(row["prediction_correct"] for row in predictions),"accuracy":sum(row["prediction_correct"] for row in predictions)/len(predictions),"confidence_calibrated":False},"primary_stable_sha256":primary["stable_sha256"],"reproducibility_stable_sha256":rerun["stable_sha256"],"rankings_identical":True,"scores_identical_within_tolerance":True,"metrics_identical":True,"paired_outcomes_identical":True,"scores_tolerance":config["retrieval"]["score_tolerance"],"runtime_seconds":{"primary":primary["runtime_seconds"],"reproducibility_rerun":rerun["runtime_seconds"]},"decision":decision,"official_banking77_test_accessed":False,"created_at":datetime.now(timezone.utc).isoformat()}
    _write_json(root/config["outputs"]["version_manifest"],manifest); return manifest


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RetrievalBenchmarkError(f"refusing to write empty CSV: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def _tracked_corpus(root: Path, config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str], dict[str, str]]:
    documents = load_jsonl(root / config["kb_documents"])
    chunks = build_corpus(
        documents,
        date.fromisoformat(config["evaluation_as_of_date"]),
        config["corpus"]["chunk_text_template"],
    )
    validate_corpus(chunks, date.fromisoformat(config["evaluation_as_of_date"]))
    if len({row["document_id"] for row in chunks}) != 26 or len(chunks) != 52:
        raise RetrievalBenchmarkError("tracked eligible corpus count mismatch")
    all_status: dict[str, str] = {}
    headings: dict[str, str] = {}
    for document in documents:
        for section in document["content_sections"]:
            chunk_id = f"{document['document_id']}#{section['section_id']}"
            all_status[chunk_id] = document["status"]
            headings[chunk_id] = f"{document['title']} / {section['heading']}"
    return chunks, all_status, headings


def _first_gold_rank(ids: list[str], gold: set[str]) -> int | None:
    return next((index + 1 for index, chunk_id in enumerate(ids) if chunk_id in gold), None)


def _ranks_above_first_gold(ids: list[str], candidates: set[str], gold: set[str]) -> bool:
    """Return whether a candidate outranks strict gold, including gold-absent cases."""
    first_gold = _first_gold_rank(ids, gold)
    return any(
        chunk_id in candidates and (first_gold is None or rank < first_gold)
        for rank, chunk_id in enumerate(ids, start=1)
    )


def _has_non_gold_sibling_above_gold(ids: list[str], gold: set[str]) -> bool:
    first_gold = _first_gold_rank(ids, gold)
    gold_documents = {chunk_id.split("#", 1)[0] for chunk_id in gold}
    return any(
        chunk_id not in gold
        and chunk_id.split("#", 1)[0] in gold_documents
        and (first_gold is None or rank < first_gold)
        for rank, chunk_id in enumerate(ids, start=1)
    )


def classify_error_case(
    query: dict[str, Any],
    prediction: dict[str, Any],
    r0_ids: list[str],
    r1_ids: list[str],
    *,
    reviewed: bool,
) -> str:
    """Classify one retrieval error under the frozen, mutually exclusive precedence."""
    gold = set(query["gold_evidence_ids"])
    rank0 = _first_gold_rank(r0_ids, gold)
    rank1 = _first_gold_rank(r1_ids, gold)
    incomplete = not gold <= set(r1_ids)
    contract_multi = query["evidence_requirement"] == "multi_document"

    # Automatic G historically used multiple strict-gold sections. Review narrows
    # the final category to the explicit multi-document evidence contract only.
    if incomplete and (contract_multi if reviewed else len(gold) > 1):
        return "G"
    if prediction["prediction_correct"] and (rank1 or 4) < (rank0 or 4):
        return "A"
    if prediction["prediction_correct"] and (rank0 or 4) < (rank1 or 4):
        return "B"
    if not prediction["prediction_correct"] and (rank0 or 4) < (rank1 or 4):
        return "C"
    if _ranks_above_first_gold(r1_ids, set(query["hard_negative_evidence_ids"]), gold):
        return "E"
    if _has_non_gold_sibling_above_gold(r1_ids, gold):
        return "F"
    if not prediction["prediction_correct"] and rank1 is not None:
        return "D"
    return "I"


def _error_triggers(
    query: dict[str, Any], prediction: dict[str, Any], ids0: list[str], ids1: list[str]
) -> list[str]:
    gold = set(query["gold_evidence_ids"])
    rank0, rank1 = _first_gold_rank(ids0, gold), _first_gold_rank(ids1, gold)
    triggers: list[str] = []
    if ids0[0] != ids1[0]: triggers.append("top1_differs")
    if rank0 != rank1: triggers.append("first_gold_rank_changed")
    if not gold & set(ids0): triggers.append("r0_miss_top3")
    if not gold & set(ids1): triggers.append("r1_miss_top3")
    if query["evidence_requirement"] == "multi_document" and not gold <= set(ids1): triggers.append("multi_document_incomplete")
    if not prediction["prediction_correct"]: triggers.append("predicted_intent_wrong")
    return triggers


def _error_analysis(root: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    queries = {row["query_id"]: row for row in load_jsonl(root / config["gold_mapping"])}
    predictions = {row["query_id"]: row for row in load_jsonl(root / config["outputs"]["classifier_predictions"])}
    r0 = {row["query_id"]: row for row in load_jsonl(root / config["outputs"]["locked_r0"])}
    r1 = {row["query_id"]: row for row in load_jsonl(root / config["outputs"]["locked_r1"])}
    _, _, headings = _tracked_corpus(root, config)
    rows: list[dict[str, Any]] = []
    category_reason = {
        "A": "The classifier is correct and the intent boost improves the first strict-gold rank.",
        "B": "The classifier is correct but the intent boost worsens the first strict-gold rank.",
        "C": "The classifier is wrong and its +0.15 intent boost worsens strict-gold ranking.",
        "D": "The classifier prediction is incorrect, but strict gold remains in R1 top three.",
        "E": "A mapped semantic hard negative ranks above the first strict-gold section, or is present when strict gold is absent.",
        "F": "A non-gold sibling section from a gold document ranks above first strict gold, or is present when strict gold is absent.",
        "G": "The multi-document contract is only partially covered in the top three.",
        "I": "The query signal is too weak for the exact dense section ranking to place strict gold reliably.",
    }
    implication_by_category = {
        "A": "This is a bounded R1 gain, but it is insufficient to offset the locked aggregate regressions.",
        "B": "This shows intent-level metadata cannot guarantee section-level ranking quality; retain R0.",
        "C": "This is direct cascading damage from classifier error and supports retaining R0.",
        "D": "This shows R0 semantic similarity can be robust to a wrong classifier; no R1 preference follows.",
        "E": "The failure is semantic discrimination, not status filtering; keep the frozen R0 decision.",
        "F": "Intent boost cannot distinguish sections sharing document intent metadata; retain simpler R0.",
        "G": "The boost does not solve multi-document completeness and must not overturn the R0 decision.",
        "I": "The miss is not evidence for a larger boost; retain R0 and record the limitation.",
    }
    for query_id in sorted(queries):
        query = queries[query_id]
        if query["split"] != "locked_test" or query["expected_response_type"] != "ANSWER":
            continue
        ids0 = [item["chunk_id"] for item in r0[query_id]["rankings"]]
        ids1 = [item["chunk_id"] for item in r1[query_id]["rankings"]]
        gold = set(query["gold_evidence_ids"])
        prediction = predictions[query_id]
        rank0, rank1 = _first_gold_rank(ids0, gold), _first_gold_rank(ids1, gold)
        triggers = _error_triggers(query, prediction, ids0, ids1)
        if not triggers:
            continue
        automatic_category = classify_error_case(query, prediction, ids0, ids1, reviewed=False)
        category = classify_error_case(query, prediction, ids0, ids1, reviewed=True)
        decisive = query["mapping_rationale"].split(".", 1)[0].strip()
        non_gold = [chunk_id for chunk_id in ids1 if chunk_id not in gold]
        higher_non_gold = [chunk_id for index, chunk_id in enumerate(ids1, start=1) if chunk_id not in gold and (rank1 is None or index < rank1)]
        other_non_gold = [chunk_id for chunk_id in non_gold if chunk_id not in higher_non_gold]
        if category == "D":
            classifier_effect = (
                "The classifier prediction was incorrect, but strict gold remained in top 3. "
                "No non-gold sibling section from the gold document displaced it. Dense retrieval "
                "therefore succeeded despite the classifier error."
            )
        elif category == "E":
            classifier_effect = (
                "The mapped hard-negative section ranked above the first strict-gold section, "
                "making this a semantic confusion failure rather than a same-document wrong-section failure."
            )
        else:
            classifier_effect = (
                f"Prediction {prediction['predicted_intent']} is {'correct' if prediction['prediction_correct'] else 'incorrect'}; "
                + (f"the +0.15 boost changed top-3 from {ids0} to {ids1}." if ids0 != ids1 else "the +0.15 boost did not change the top-3 ordering.")
            )
        expected_text = "; ".join(f"{chunk_id} ({headings[chunk_id]})" for chunk_id in query["gold_evidence_ids"])
        higher_text = "; ".join(f"{chunk_id} ({headings[chunk_id]})" for chunk_id in higher_non_gold) or "None"
        other_text = "; ".join(f"{chunk_id} ({headings[chunk_id]})" for chunk_id in other_non_gold) or "None"
        root_cause = (
            f"Decisive signal: {decisive}. Expected strict evidence: {expected_text}. "
            f"Higher-ranked R1 non-gold sections: {higher_text}. Other R1 non-gold top-3 sections: {other_text}. "
            f"{classifier_effect} "
            f"Category {category}: {category_reason[category]}"
        )
        rows.append({
            "query_id": query_id, "query_text": query["query_text"], "gold_intent": query["gold_intent"],
            "predicted_intent": prediction["predicted_intent"], "r0_top3": json.dumps(ids0), "r1_top3": json.dumps(ids1),
            "gold_ids": json.dumps(query["gold_evidence_ids"]), "acceptable_ids": json.dumps(query["acceptable_evidence_ids"]),
            "hard_negative_ids": json.dumps(query["hard_negative_evidence_ids"]), "r0_first_gold_rank": rank0,
            "r1_first_gold_rank": rank1, "review_triggers": "|".join(triggers), "automatic_category": automatic_category, "category": category,
            "decisive_query_signal": decisive, "expected_gold_sections": expected_text,
            "displacing_sections": higher_text, "higher_ranked_non_gold_sections": higher_text,
            "other_non_gold_top3_sections": other_text, "classifier_effect": classifier_effect,
            "category_rationale": category_reason[category], "root_cause_analysis": root_cause,
            "decision_implication": implication_by_category[category],
        })
    _write_csv(root / config["outputs"]["error_analysis"], rows)
    return rows


def _safety_diagnostics(root: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    queries = {row["query_id"]: row for row in load_jsonl(root / config["gold_mapping"])}
    predictions = {row["query_id"]: row for row in load_jsonl(root / config["outputs"]["classifier_predictions"])}
    r0 = {row["query_id"]: row for row in load_jsonl(root / config["outputs"]["locked_r0"])}
    r1 = {row["query_id"]: row for row in load_jsonl(root / config["outputs"]["locked_r1"])}
    _, all_status, _ = _tracked_corpus(root, config)
    rows = []
    for query_id in sorted(queries):
        query = queries[query_id]
        if query["split"] != "locked_test" or query["expected_response_type"] != "ABSTAIN_ESCALATE":
            continue
        top0, top1 = r0[query_id]["rankings"], r1[query_id]["rankings"]
        all_items = top0 + top1
        status_leakage = any(all_status[item["chunk_id"]] != "APPROVED" for item in all_items)
        forbidden_leakage = any(item["chunk_id"] in set(query["forbidden_evidence_ids"]) for item in all_items)
        rows.append({
            "query_id": query_id, "query_text": query["query_text"], "gold_intent": query["gold_intent"],
            "predicted_intent": predictions[query_id]["predicted_intent"], "r0_top3": json.dumps(top0),
            "r1_top3": json.dumps(top1), "forbidden_evidence_ids": json.dumps(query["forbidden_evidence_ids"]),
            "status_leakage": str(status_leakage).lower(), "forbidden_evidence_leakage": str(forbidden_leakage).lower(),
            "diagnostic_notes": "Eligible-section rankings only; retrieval does not claim or evaluate abstention for this safety probe.",
        })
    _write_csv(root / config["outputs"]["safety_diagnostics"], rows)
    return rows


def _multi_document_diagnostics(root: Path, config: dict[str, Any], *, write: bool = True) -> dict[str, Any]:
    queries = [row for row in load_jsonl(root / config["gold_mapping"]) if row["split"] == "locked_test" and row["expected_response_type"] == "ANSWER" and row["evidence_requirement"] == "multi_document"]
    variants = {
        "r0": {row["query_id"]: row for row in load_jsonl(root / config["outputs"]["locked_r0"])},
        "r1": {row["query_id"]: row for row in load_jsonl(root / config["outputs"]["locked_r1"])},
    }
    payload: dict[str, Any] = {"task_id": "W2-003", "diagnostic_only": True, "multi_document_query_count": len(queries), "variants": {}}
    for name, ranking_by_id in variants.items():
        per_query, recalls, complete = [], [], 0
        for query in sorted(queries, key=lambda row: row["query_id"]):
            retrieved = [item["chunk_id"] for item in ranking_by_id[query["query_id"]]["rankings"]]
            gold = set(query["gold_evidence_ids"]); missing = sorted(gold - set(retrieved)); recall = len(gold & set(retrieved)) / len(gold)
            complete += not missing; recalls.append(recall)
            per_query.append({"query_id": query["query_id"], "gold_evidence_ids": sorted(gold), "retrieved_top3": retrieved, "gold_recall_at_3": recall, "complete": not missing, "missing_gold_sections": missing})
        payload["variants"][name] = {"mean_gold_recall_at_3": sum(recalls) / len(recalls), "complete_coverage_count": complete, "complete_coverage_rate": complete / len(queries), "per_query": per_query}
    if write:
        _write_json(root / config["outputs"]["multi_document_diagnostics"], payload)
    return payload


def _assert_accepted_locked_artifacts(root: Path, config: dict[str, Any]) -> None:
    for name, expected in config["accepted_locked_artifact_sha256"].items():
        path = root / config["outputs"][name]
        if _sha(path) != expected:
            raise RetrievalBenchmarkError(f"accepted locked artifact changed: {name}")


def _validate_rankings(
    rows: list[dict[str, Any]],
    expected_query_ids: set[str],
    candidate_ids: set[str],
    all_status: dict[str, str],
    *,
    label: str,
) -> None:
    actual_ids = [row.get("query_id") for row in rows]
    if len(rows) != len(expected_query_ids) or set(actual_ids) != expected_query_ids or len(actual_ids) != len(set(actual_ids)):
        raise RetrievalBenchmarkError(f"{label} query membership mismatch")
    for row in rows:
        ranked = row.get("rankings", [])
        ids = [item.get("chunk_id") for item in ranked]
        if len(ranked) != 3 or len(ids) != len(set(ids)):
            raise RetrievalBenchmarkError(f"{label} ranking must contain three unique chunks")
        for chunk_id in ids:
            if chunk_id not in all_status:
                raise RetrievalBenchmarkError(f"{label} ranking references unknown chunk: {chunk_id}")
            if all_status[chunk_id] in {"DRAFT", "EXPIRED"}:
                raise RetrievalBenchmarkError(f"{label} ranking contains {all_status[chunk_id]} chunk: {chunk_id}")
            if chunk_id not in candidate_ids:
                raise RetrievalBenchmarkError(f"{label} ranking contains non-candidate chunk: {chunk_id}")
        if any(float(ranked[index]["score"]) < float(ranked[index + 1]["score"]) for index in range(2)):
            raise RetrievalBenchmarkError(f"{label} ranking scores are not descending")


def _validate_dev_rankings(
    root: Path,
    config: dict[str, Any],
    queries: list[dict[str, Any]],
    candidate_ids: set[str],
    all_status: dict[str, str],
) -> dict[str, Any]:
    selection = _json(root / config["outputs"]["dev_selection"])
    validate_frozen_selection(selection, config["frozen_selection_config_sha256"])
    development = sorted((row for row in queries if row["split"] == "development"), key=lambda row: row["query_id"])
    locked_ids = {row["query_id"] for row in queries if row["split"] == "locked_test"}
    development_ids = {row["query_id"] for row in development}
    validate_selection_membership(selection["development_query_ids"], list(locked_ids))
    rows = load_jsonl(root / config["outputs"]["dev_rankings"])
    if len(rows) != 50:
        raise RetrievalBenchmarkError("development rankings must contain exactly 50 rows")
    expected_variants = {
        "R0": None,
        "R1_lambda_0.05": 0.05,
        "R1_lambda_0.10": 0.10,
        "R1_lambda_0.15": 0.15,
        "R1_lambda_0.20": 0.20,
    }
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        query_id, variant = row.get("query_id"), row.get("variant")
        if query_id in locked_ids:
            raise RetrievalBenchmarkError("locked query ID found in development rankings")
        if query_id not in development_ids:
            raise RetrievalBenchmarkError("unknown query ID found in development rankings")
        if variant not in expected_variants:
            raise RetrievalBenchmarkError(f"unknown development ranking variant: {variant}")
        if row.get("lambda") != expected_variants[variant]:
            raise RetrievalBenchmarkError(f"development variant/lambda mismatch: {variant}")
        if variant in grouped.setdefault(query_id, {}):
            raise RetrievalBenchmarkError(f"duplicate development ranking variant: {query_id}/{variant}")
        grouped[query_id][variant] = row
    for query_id in development_ids:
        if set(grouped.get(query_id, {})) != set(expected_variants):
            raise RetrievalBenchmarkError(f"missing development lambda variant: {query_id}")
    predictions = {row["query_id"]: row for row in load_jsonl(root / config["outputs"]["classifier_predictions"])}
    recomputed: dict[str, Any] = {}
    for variant, boost in expected_variants.items():
        variant_rows = [{"query_id": query["query_id"], "rankings": grouped[query["query_id"]][variant]["rankings"]} for query in development]
        _validate_rankings(variant_rows, development_ids, candidate_ids, all_status, label=f"development {variant}")
        for query in development:
            if grouped[query["query_id"]][variant]["predicted_intent"] != predictions[query["query_id"]]["predicted_intent"]:
                raise RetrievalBenchmarkError("development predicted intent mismatch")
        recomputed[variant] = metrics(development, variant_rows, all_status)
    if recomputed["R0"] != selection["r0_metrics"]:
        raise RetrievalBenchmarkError("development R0 metric tampering detected")
    grid = [{"lambda": boost, "metrics": recomputed[variant]} for variant, boost in expected_variants.items() if boost is not None]
    if grid != selection["lambda_grid"]:
        raise RetrievalBenchmarkError("development grid metric tampering detected")
    if choose_lambda(grid)["lambda"] != selection["selected_lambda"] or selection["selected_lambda"] != 0.15:
        raise RetrievalBenchmarkError("development selected lambda tampering detected")
    return {"rows": 50, "queries": 10, "variants_per_query": 5, "metrics": recomputed, "selected_lambda": 0.15}


def _validate_paired_artifact(queries: list[dict[str, Any]], r0: list[dict[str, Any]], r1: list[dict[str, Any]], stored: dict[str, Any]) -> dict[str, Any]:
    recomputed = _paired(queries, r0, r1)
    if recomputed != stored:
        raise RetrievalBenchmarkError("paired outcome artifact tampering detected")
    if sum(recomputed["counts"][key] for key in ("WIN", "LOSS", "TIE")) != 40:
        raise RetrievalBenchmarkError("paired outcome partition mismatch")
    return recomputed


def _validate_error_rows(
    error_rows: list[dict[str, Any]],
    locked_queries: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    r0_rows: list[dict[str, Any]],
    r1_rows: list[dict[str, Any]],
) -> None:
    query_by_id = {row["query_id"]: row for row in locked_queries}
    prediction_by_id = {row["query_id"]: row for row in predictions}
    r0_by_id = {row["query_id"]: [item["chunk_id"] for item in row["rankings"]] for row in r0_rows}
    r1_by_id = {row["query_id"]: [item["chunk_id"] for item in row["rankings"]] for row in r1_rows}
    error_ids = {row["query_id"] for row in error_rows}
    answer_ids = {row["query_id"] for row in locked_queries if row["expected_response_type"] == "ANSWER"}
    safety_ids = {row["query_id"] for row in locked_queries if row["expected_response_type"] == "ABSTAIN_ESCALATE"}
    expected_error_ids = {
        query_id
        for query_id in answer_ids
        if _error_triggers(
            query_by_id[query_id], prediction_by_id[query_id], r0_by_id[query_id], r1_by_id[query_id]
        )
    }
    if len(error_rows) != 28 or error_ids != expected_error_ids or error_ids & safety_ids:
        raise RetrievalBenchmarkError("ANSWER error-analysis membership mismatch")
    for row in error_rows:
        query_id = row["query_id"]
        expected_automatic_category = classify_error_case(
            query_by_id[query_id], prediction_by_id[query_id], r0_by_id[query_id], r1_by_id[query_id], reviewed=False
        )
        expected_reviewed_category = classify_error_case(
            query_by_id[query_id], prediction_by_id[query_id], r0_by_id[query_id], r1_by_id[query_id], reviewed=True
        )
        if row.get("automatic_category") != expected_automatic_category:
            if row.get("automatic_category") == "F" and expected_automatic_category != "F":
                raise RetrievalBenchmarkError(f"false-correct-document-wrong-section: {query_id}")
            if expected_automatic_category == "D":
                raise RetrievalBenchmarkError(f"classifier-wrong-success-category-mismatch: {query_id}")
            if expected_automatic_category == "E":
                raise RetrievalBenchmarkError(f"hard-negative-rank-category-mismatch: {query_id}")
            raise RetrievalBenchmarkError(f"error-category-semantic-mismatch: automatic/{query_id}")
        if row.get("category") != expected_reviewed_category:
            if row.get("category") == "F" and expected_reviewed_category != "F":
                raise RetrievalBenchmarkError(f"false-correct-document-wrong-section: {query_id}")
            if expected_reviewed_category == "D":
                raise RetrievalBenchmarkError(f"classifier-wrong-success-category-mismatch: {query_id}")
            if expected_reviewed_category == "E":
                raise RetrievalBenchmarkError(f"hard-negative-rank-category-mismatch: {query_id}")
            raise RetrievalBenchmarkError(f"error-category-semantic-mismatch: reviewed/{query_id}")
    expected_automatic = {"A": 3, "C": 4, "D": 4, "E": 4, "F": 2, "G": 4, "I": 7}
    expected_reviewed = {"A": 3, "C": 4, "D": 4, "E": 4, "F": 2, "G": 3, "I": 8}
    if dict(sorted(Counter(row["automatic_category"] for row in error_rows).items())) != expected_automatic:
        raise RetrievalBenchmarkError("automatic ANSWER error-analysis category counts mismatch")
    if dict(sorted(Counter(row["category"] for row in error_rows).items())) != expected_reviewed:
        raise RetrievalBenchmarkError("reviewed ANSWER error-analysis category counts mismatch")
    required = (
        "decisive_query_signal", "expected_gold_sections", "displacing_sections",
        "higher_ranked_non_gold_sections", "other_non_gold_top3_sections",
        "classifier_effect", "category_rationale", "root_cause_analysis", "decision_implication",
    )
    if any(not all(row.get(field, "").strip() for field in required) for row in error_rows):
        raise RetrievalBenchmarkError("row-level root-cause analysis is incomplete")
    roots = [row["root_cause_analysis"] for row in error_rows]
    if len(set(roots)) != 28 or any("Observed ranking/classifier interaction" in value for value in roots):
        raise RetrievalBenchmarkError("generic or duplicated root-cause analysis detected")


def _validate_safety_rows(safety_rows: list[dict[str, Any]], locked_queries: list[dict[str, Any]]) -> None:
    safety_ids = {row["query_id"] for row in locked_queries if row["expected_response_type"] == "ABSTAIN_ESCALATE"}
    if len(safety_rows) != 10 or {row["query_id"] for row in safety_rows} != safety_ids:
        raise RetrievalBenchmarkError("safety diagnostic membership mismatch")
    if any(row["status_leakage"] != "false" or row["forbidden_evidence_leakage"] != "false" for row in safety_rows):
        raise RetrievalBenchmarkError("safety diagnostic leakage detected")


def _artifact_hashes(root: Path, config_path: Path, config: dict[str, Any]) -> dict[str, str]:
    names = (
        "corpus_manifest", "dev_selection", "dev_rankings", "classifier_predictions",
        "locked_r0", "locked_r1", "metrics", "paired", "error_analysis",
        "safety_diagnostics", "multi_document_diagnostics",
    )
    values = {"retrieval_config": _sha(config_path)}
    values.update({name: _sha(root / config["outputs"][name]) for name in names})
    return values


def _verify_artifact_hashes(root: Path, config_path: Path, config: dict[str, Any], manifest: dict[str, Any]) -> None:
    current = _artifact_hashes(root, config_path, config)
    if manifest.get("artifact_sha256") != current:
        differing = sorted(name for name, value in current.items() if manifest.get("artifact_sha256", {}).get(name) != value)
        raise RetrievalBenchmarkError(f"version manifest artifact hash mismatch: {differing}")


def finalize_review_correction(root: Path, config_path: Path) -> dict[str, Any]:
    """Finalize review-only evidence without rerunning or rewriting locked results."""
    verify_contract(root, config_path)
    config = load_config(root, config_path)
    _assert_accepted_locked_artifacts(root, config)
    queries = load_jsonl(root / config["gold_mapping"])
    chunks, all_status, _ = _tracked_corpus(root, config)
    candidate_ids = {row["chunk_id"] for row in chunks}
    dev = _validate_dev_rankings(root, config, queries, candidate_ids, all_status)
    error_rows = _error_analysis(root, config)
    safety_rows = _read_csv(root / config["outputs"]["safety_diagnostics"])
    multi = _multi_document_diagnostics(root, config, write=False)
    if multi != _json(root / config["outputs"]["multi_document_diagnostics"]):
        raise RetrievalBenchmarkError("multi-document diagnostic tampering detected")
    automatic_counts = Counter(row["automatic_category"] for row in error_rows)
    reviewed_counts = Counter(row["category"] for row in error_rows)
    expected_automatic = {"A": 3, "C": 4, "D": 4, "E": 4, "F": 2, "G": 4, "I": 7}
    expected_reviewed = {"A": 3, "C": 4, "D": 4, "E": 4, "F": 2, "G": 3, "I": 8}
    if len(error_rows) != 28 or dict(sorted(automatic_counts.items())) != expected_automatic or dict(sorted(reviewed_counts.items())) != expected_reviewed:
        raise RetrievalBenchmarkError(f"corrected ANSWER error-analysis population mismatch: automatic={dict(automatic_counts)}, reviewed={dict(reviewed_counts)}")
    if len(safety_rows) != 10 or multi["multi_document_query_count"] != 4:
        raise RetrievalBenchmarkError("review-correction diagnostic count mismatch")
    previous = _json(root / config["outputs"]["version_manifest"])
    if previous.get("primary_stable_sha256") != config["accepted_stable_run_sha256"] or previous.get("reproducibility_stable_sha256") != config["accepted_stable_run_sha256"]:
        raise RetrievalBenchmarkError("accepted stable run hash changed before correction")
    manifest = {
        **previous,
        "status": "FINALIZED_REVIEW_CORRECTION",
        "retrieval_config_sha256": _sha(config_path),
        "artifact_sha256": _artifact_hashes(root, config_path, config),
        "implementation_sha256": {
            "corpus": _sha(Path(__file__).with_name("corpus.py")),
            "dense": _sha(Path(__file__).with_name("dense.py")),
            "benchmark": _sha(Path(__file__)),
            "benchmark_cli": _sha(Path(__file__).with_name("benchmark_cli.py")),
        },
        "review_correction": {
            "verdict": "FIX_REQUIRED",
            "root_cause": "Six rows were categorized F because the F predicate admitted the strict-gold chunk itself, while D covered only rank improvement instead of retained dense-retrieval success.",
            "fix": "Rank-aware mutually exclusive taxonomy with per-row semantic recomputation from frozen mappings, predictions, and rankings.",
            "regression": "Controlled category fixtures plus row-level and same-aggregate category-tampering checks.",
            "lesson": "Aggregate category totals cannot prove row-level taxonomy correctness.",
            "answer_error_analysis_rows": 28,
            "automatic_error_category_counts_before_manual_refinement": expected_automatic,
            "reviewed_error_category_counts": expected_reviewed,
            "safety_diagnostic_rows": 10,
            "development_ranking_rows": dev["rows"],
            "development_variants_per_query": dev["variants_per_query"],
            "multi_document_query_count": 4,
        },
        "initial_review_verdict": "FIX_REQUIRED",
        "final_senior_review_verdict": "APPROVE_COMMIT",
        "week_2_p0_gate": "PASSED",
        "accepted_locked_artifact_sha256": config["accepted_locked_artifact_sha256"],
        "accepted_locked_artifacts_byte_identical": True,
        "selected_lambda": 0.15,
        "selected_retriever": "R0",
        "corrected_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(root / config["outputs"]["version_manifest"], manifest)
    return {"status": "PASS", "locked_artifacts_unchanged": True, "dev_rankings": dev, "answer_error_rows": 28, "safety_rows": 10, "multi_document": multi, "selected_retriever": "R0"}


def verify_results(root: Path, config_path: Path, write: bool=True) -> dict[str, Any]:
    contract = verify_contract(root, config_path)
    config = load_config(root, config_path)
    _assert_accepted_locked_artifacts(root, config)
    manifest = _json(root / config["outputs"]["version_manifest"])
    if manifest.get("status") != "FINALIZED_REVIEW_CORRECTION":
        raise RetrievalBenchmarkError("review-corrected version manifest status mismatch")
    if manifest.get("retrieval_config_sha256") != _sha(config_path):
        raise RetrievalBenchmarkError("version manifest retrieval config hash mismatch")
    _verify_artifact_hashes(root, config_path, config, manifest)
    expected_implementation = {
        "corpus": _sha(Path(__file__).with_name("corpus.py")),
        "dense": _sha(Path(__file__).with_name("dense.py")),
        "benchmark": _sha(Path(__file__)),
        "benchmark_cli": _sha(Path(__file__).with_name("benchmark_cli.py")),
    }
    if manifest.get("implementation_sha256") != expected_implementation:
        raise RetrievalBenchmarkError("version manifest implementation hash mismatch")

    chunks, all_status, _ = _tracked_corpus(root, config)
    candidate_ids = {row["chunk_id"] for row in chunks}
    corpus_manifest = _json(root / config["outputs"]["corpus_manifest"])
    expected_alignment = hashlib.sha256(("\n".join(row["chunk_id"] for row in chunks) + "\n").encode()).hexdigest()
    expected_corpus_hash = sha256_bytes(canonical_bytes(chunks))
    corpus_checks = {
        "documents": 26, "chunks": 52, "draft_chunks": 0, "expired_chunks": 0,
        "duplicate_chunk_ids": 0, "missing_sections": 0,
        "chunk_order": "chunk_id_ascending",
        "chunk_text_template": config["corpus"]["chunk_text_template"],
        "chunk_alignment_sha256": expected_alignment, "corpus_sha256": expected_corpus_hash,
    }
    for key, expected in corpus_checks.items():
        if corpus_manifest.get(key) != expected:
            raise RetrievalBenchmarkError(f"tracked corpus manifest mismatch: {key}")

    all_queries = load_jsonl(root / config["gold_mapping"])
    development_ids = {row["query_id"] for row in all_queries if row["split"] == "development"}
    locked_queries = [row for row in all_queries if row["split"] == "locked_test"]
    locked_ids = {row["query_id"] for row in locked_queries}
    r0 = load_jsonl(root / config["outputs"]["locked_r0"])
    r1 = load_jsonl(root / config["outputs"]["locked_r1"])
    _validate_rankings(r0, locked_ids, candidate_ids, all_status, label="locked R0")
    _validate_rankings(r1, locked_ids, candidate_ids, all_status, label="locked R1")
    if ({row["query_id"] for row in r0} | {row["query_id"] for row in r1}) & development_ids:
        raise RetrievalBenchmarkError("development query ID found in locked rankings")
    stored_metrics = _json(root / config["outputs"]["metrics"])
    recomputed = {"r0": metrics(locked_queries, r0, all_status), "r1": metrics(locked_queries, r1, all_status)}
    if recomputed != stored_metrics.get("primary"):
        raise RetrievalBenchmarkError("locked metric artifact tampering detected")
    paired = _validate_paired_artifact(locked_queries, r0, r1, _json(root / config["outputs"]["paired"]))
    dev = _validate_dev_rankings(root, config, all_queries, candidate_ids, all_status)

    predictions = load_jsonl(root / config["outputs"]["classifier_predictions"])
    prediction_ids = [row.get("query_id") for row in predictions]
    if len(predictions) != 60 or set(prediction_ids) != development_ids | locked_ids or len(prediction_ids) != len(set(prediction_ids)):
        raise RetrievalBenchmarkError("classifier prediction membership mismatch")
    split_by_id = {row["query_id"]: row["split"] for row in all_queries}
    if any(row.get("split") != split_by_id[row["query_id"]] for row in predictions):
        raise RetrievalBenchmarkError("classifier prediction split mismatch")

    error_rows = _read_csv(root / config["outputs"]["error_analysis"])
    _validate_error_rows(error_rows, locked_queries, predictions, r0, r1)

    safety_rows = _read_csv(root / config["outputs"]["safety_diagnostics"])
    _validate_safety_rows(safety_rows, locked_queries)
    multi = _multi_document_diagnostics(root, config, write=False)
    if multi != _json(root / config["outputs"]["multi_document_diagnostics"]):
        raise RetrievalBenchmarkError("multi-document diagnostic tampering detected")
    if multi["multi_document_query_count"] != 4:
        raise RetrievalBenchmarkError("multi-document slice count mismatch")

    keys = ("strict_mrr_at_3", "strict_hit_at_1", "strict_recall_at_3")
    selected = "R1" if tuple(recomputed["r1"][key] for key in keys) > tuple(recomputed["r0"][key] for key in keys) else "R0"
    if selected != "R0" or stored_metrics.get("decision", {}).get("selected_retriever") != "R0" or manifest.get("selected_retriever") != "R0":
        raise RetrievalBenchmarkError("frozen retriever decision changed")
    if manifest.get("selected_lambda") != 0.15 or manifest.get("accepted_locked_artifacts_byte_identical") is not True:
        raise RetrievalBenchmarkError("version manifest frozen decision mismatch")
    result = {
        "task_id": "W2-003", "status": "PASS", "verification_scope": "tracked_evidence_only",
        "requires_local_cache_or_model": False, "answer_queries": 40, "safety_queries": 10,
        "development_rankings": {"rows": dev["rows"], "variants_per_query": dev["variants_per_query"]},
        "answer_error_analysis_rows": 28, "safety_diagnostic_rows": 10,
        "multi_document_query_count": 4, "selected_lambda": 0.15, "selected_retriever": "R0",
        "checks": {
            "frozen_contract": contract["status"], "accepted_locked_artifact_hashes": "PASS",
            "version_manifest_hashes": "PASS", "corpus_rebuilt_from_frozen_kb": "PASS",
            "candidate_status_from_frozen_kb": "PASS", "development_rankings_and_metrics": "PASS",
            "locked_membership_rankings_and_metrics": "PASS", "paired_outcomes": "PASS",
            "answer_error_analysis": "PASS", "safety_diagnostics": "PASS",
            "multi_document_diagnostics": "PASS", "decision_rule": "PASS",
        },
        "official_banking77_test_accessed": False,
    }
    if write:
        _write_json(root / config["outputs"]["validation"], result)
    return result


def verify_runtime_reproduction(root: Path, config_path: Path) -> dict[str, Any]:
    """Optional local verification that intentionally requires ignored runtime artifacts."""
    verify_contract(root, config_path)
    config = load_config(root, config_path, require_local_model=True)
    _assert_accepted_locked_artifacts(root, config)
    chunks, embeddings = _load_runtime(root, config)
    manifest = _json(root / config["outputs"]["corpus_manifest"])
    if list(embeddings.shape) != manifest["embedding_shape"] or hashlib.sha256(embeddings.tobytes()).hexdigest() != manifest["embedding_sha256"]:
        raise RetrievalBenchmarkError("local corpus embedding evidence mismatch")
    primary = _json(root / config["cache"]["directory"] / "locked_primary.json")
    rerun = _json(root / config["cache"]["directory"] / "locked_reproducibility_rerun.json")
    assert_reproducible(primary, rerun, config["retrieval"]["score_tolerance"])
    if primary.get("stable_sha256") != config["accepted_stable_run_sha256"] or rerun.get("stable_sha256") != config["accepted_stable_run_sha256"]:
        raise RetrievalBenchmarkError("accepted stable runtime hash mismatch")
    return {"task_id": "W2-003", "status": "PASS", "verification_scope": "local_runtime_reproduction", "requires_local_cache_or_model": True, "chunks": len(chunks), "embedding_shape": list(embeddings.shape), "stable_sha256": config["accepted_stable_run_sha256"]}
