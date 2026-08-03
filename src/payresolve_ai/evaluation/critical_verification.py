"""Runtime, metrics, ablations, and offline verification for W3-002."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from payresolve_ai.evaluation.gold_mapping import canonical_rows_sha256, load_jsonl
from payresolve_ai.generation.context import eligible_chunks
from payresolve_ai.generation.gate import build_idf
from payresolve_ai.generation.pipeline import _verified_answer, run_case_v2
from payresolve_ai.generation.support_v2 import build_canonical_idf
from payresolve_ai.generation.verification import write_json, write_jsonl
from payresolve_ai.generation.verification_v2 import load_v2_configuration, verify_contract as verify_gate_v2
from payresolve_ai.kb.validation import canonical_dataset_sha256
from payresolve_ai.retrieval.benchmark import _rank_queries

from .critical import CriticalEvaluationError, load_config, mapping_sha256, membership_sha256, sha256_file, validate_scenarios, verify_pre_evaluation


VARIANT_IDS = ("R0_EVIDENCE_GATED_V2", "R1_EVIDENCE_GATED_V2", "R0_ALWAYS_ANSWER")


def verify_contract(root: Path, config_path: Path) -> dict[str, Any]:
    config = load_config(config_path); frozen = config["frozen_upstream"]
    checks = {
        "kb_raw_sha256": root / config["kb_documents"],
        "w2_mapping_sha256": root / "data/evaluation/gold_mapping_v1.jsonl",
        "r0_locked_sha256": root / "reports/week_02/results/retrieval_locked_r0_rankings.jsonl",
        "r1_locked_sha256": root / "reports/week_02/results/retrieval_locked_r1_rankings.jsonl",
        "w2_metrics_sha256": root / "reports/week_02/results/retrieval_metrics.json",
        "gate_v2_config_sha256": root / config["gate_v2_config"],
        "lexicon_sha256": root / "configs/generation/banking_support_lexicon_v2.json",
    }
    for name, path in checks.items():
        actual = canonical_rows_sha256(load_jsonl(path)) if name == "w2_mapping_sha256" else sha256_file(path)
        if actual != frozen[name]:
            raise CriticalEvaluationError(f"frozen upstream mismatch: {name}")
    documents = load_jsonl(root / config["kb_documents"])
    if canonical_dataset_sha256(documents) != frozen["kb_canonical_sha256"]:
        raise CriticalEvaluationError("frozen canonical KB mismatch")
    verify_gate_v2(root, root / config["gate_v2_config"])
    variants = json.loads((root / config["variant_config"]).read_text(encoding="utf-8"))["variants"]
    if [row["id"] for row in variants] != list(VARIANT_IDS) or variants[1]["retrieval_lambda"] != 0.15:
        raise CriticalEvaluationError("exact-three-variant contract mismatch")
    return {"status": "PASS", "task_id": "W3-002", "variant_ids": list(VARIANT_IDS), "frozen_upstream": frozen}


def _runtime_material(root: Path, config_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, float], dict[str, float]]:
    config = load_config(config_path)
    v2, base, _, _, lexicon = load_v2_configuration(root, root / config["gate_v2_config"])
    retrieval = json.loads((root / config["retrieval_config"]).read_text(encoding="utf-8"))
    chunks = eligible_chunks(load_jsonl(root / config["kb_documents"]), date.fromisoformat(config["evaluation_as_of_date"]), retrieval["corpus"]["chunk_text_template"])
    return config, v2, base, lexicon, chunks, build_idf(chunks, base["tokenizer"]["stopwords"]), build_canonical_idf(chunks, lexicon, base["tokenizer"]["stopwords"])


def _evaluate(root: Path, config_path: Path, rows: list[dict[str, Any]], rankings: list[dict[str, Any]], predictions: list[dict[str, Any]], *, mode: str, retriever: str) -> list[dict[str, Any]]:
    _, v2, base, lexicon, chunks, raw_idf, canonical_idf = _runtime_material(root, config_path)
    variant = json.loads((root / load_config(config_path)["variant_config"]).read_text(encoding="utf-8"))
    policy = variant["gate_policy"]
    candidate = {"min_top1_score": policy["min_top1_score"], "min_best_sentence_support_coverage": policy["min_best_sentence_support_coverage"], "ambiguity_score_gap": policy["ambiguity_score_gap"]}
    rank_by_id = {row["query_id"]: row for row in rankings}; pred_by_id = {row["query_id"]: row for row in predictions}
    return [run_case_v2(row, rank_by_id[row["query_id"]], pred_by_id[row["query_id"]], chunks, raw_idf, canonical_idf, base, v2, lexicon, candidate, mode=mode, retriever_variant=retriever) for row in rows]


def run_critical(root: Path, config_path: Path, run_label: str) -> dict[str, Any]:
    if (root / "reports/week_03/results/critical_eval_v1_integrity_incident_summary.json").exists():
        raise CriticalEvaluationError("critical_eval_v1 is invalidated; encoder/retrieval/pipeline reruns are prohibited")
    config = load_config(config_path); verify_contract(root, config_path)
    rows = load_jsonl(root / config["dataset_path"]); runtime_rows = [{**row, "split": "critical"} for row in rows]
    retrieval = json.loads((root / config["retrieval_config"]).read_text(encoding="utf-8"))
    if run_label == "primary":
        verify_pre_evaluation(root, config_path, require_unexecuted=True)
        r0, predictions = _rank_queries(root, retrieval, runtime_rows, None)
        r1, r1_predictions = _rank_queries(root, retrieval, runtime_rows, 0.15)
        if predictions != r1_predictions:
            raise CriticalEvaluationError("classifier diagnostics changed across retrieval variants")
        outputs = {
            "v0_outputs": _evaluate(root, config_path, rows, r0, predictions, mode="EVIDENCE_GATED", retriever="R0"),
            "v1_outputs": _evaluate(root, config_path, rows, r1, predictions, mode="EVIDENCE_GATED", retriever="R1"),
            "v2_outputs": _evaluate(root, config_path, rows, r0, predictions, mode="ALWAYS_ANSWER", retriever="R0"),
        }
        write_jsonl(root / config["outputs"]["r0_rankings"], r0); write_jsonl(root / config["outputs"]["r1_rankings"], r1)
        write_jsonl(root / config["outputs"]["predictions"], predictions)
        for key, value in outputs.items(): write_jsonl(root / config["outputs"][key], value)
        return {"status": "PASS", "run_label": run_label, "cases_per_variant": 60, "variants": list(VARIANT_IDS)}
    if run_label != "reproducibility_rerun":
        raise CriticalEvaluationError("invalid run label")
    verify_pre_evaluation(root, config_path, require_unexecuted=False)
    r0, predictions = _rank_queries(root, retrieval, runtime_rows, None); r1, r1_predictions = _rank_queries(root, retrieval, runtime_rows, 0.15)
    regenerated = {
        "r0_rankings": r0, "r1_rankings": r1, "predictions": predictions,
        "v0_outputs": _evaluate(root, config_path, rows, r0, predictions, mode="EVIDENCE_GATED", retriever="R0"),
        "v1_outputs": _evaluate(root, config_path, rows, r1, predictions, mode="EVIDENCE_GATED", retriever="R1"),
        "v2_outputs": _evaluate(root, config_path, rows, r0, predictions, mode="ALWAYS_ANSWER", retriever="R0"),
    }
    if predictions != r1_predictions:
        raise CriticalEvaluationError("rerun classifier diagnostics mismatch")
    hashes = {}
    for key, value in regenerated.items():
        stored = load_jsonl(root / config["outputs"][key])
        if stored != value: raise CriticalEvaluationError(f"primary/reproduction mismatch: {key}")
        hashes[key] = canonical_rows_sha256(value)
    result = {"status": "PASS", "run_label": run_label, "primary_reproduction_identical": True, "stable_hashes": hashes}
    write_json(root / config["outputs"]["reproduction"], result)
    return result


def _is_relevant(query: dict[str, Any], output: dict[str, Any], as_of: date) -> tuple[bool, bool]:
    if output.get("response_type") != "ANSWER" or not _verified_answer(output, as_of): return False, False
    cited = {row["evidence_id"] for row in output.get("citations", [])}; gold = set(query.get("gold_evidence_ids", [])); acceptable = set(query.get("acceptable_evidence_ids", []))
    relevant = gold <= cited if query.get("evidence_requirement") == "multi_document" else bool(cited & (gold | acceptable))
    complete_multi = query.get("evidence_requirement") == "multi_document" and gold <= cited
    return relevant, complete_multi


def compute_metrics(queries: list[dict[str, Any]], outputs: list[dict[str, Any]], as_of: date) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    by_id = {row["query_id"]: row for row in queries}; outcomes = []; claims = []
    positive_answers = relevant_answers = wrong_evidence = complete_multi = negative_abstains = unsafe = system_errors = 0
    family_total = Counter(); family_correct = Counter(); dimension_total = Counter(); dimension_correct = Counter(); case_total = Counter(); case_correct = Counter()
    answer_count = verified_answers = total_claims = supported_claims = draft = expired = wrong_status_context = metadata_failures = 0
    reasons = Counter()
    for output in outputs:
        query = by_id[output["query_id"]]; positive = query["expected_response_type"] == "ANSWER"; response = output.get("response_type")
        reasons[output.get("gate", {}).get("reason_code", "SYSTEM_ERROR")] += 1
        verified = _verified_answer(output, as_of) if response == "ANSWER" else False
        relevant, multi_ok = _is_relevant(query, output, as_of)
        if positive:
            family_total[query["intent_family"]] += 1; dimension_total[query["requested_dimension"]] += 1
            positive_answers += response == "ANSWER"; relevant_answers += relevant; complete_multi += multi_ok
            wrong_evidence += response == "ANSWER" and not relevant
            family_correct[query["intent_family"]] += relevant; dimension_correct[query["requested_dimension"]] += relevant
            outcome = "SAFE_CORRECT_ANSWER" if relevant else "WRONG_ANSWER" if response == "ANSWER" else "WRONG_ABSTAIN_ESCALATE"
        else:
            case_total[query["case_type"]] += 1
            if response == "ABSTAIN_ESCALATE": negative_abstains += 1; case_correct[query["case_type"]] += 1; outcome = "SAFE_ABSTAIN_ESCALATE"
            elif response == "ANSWER": unsafe += 1; outcome = "WRONG_ANSWER"
            else: outcome = "SYSTEM_ERROR"
        if response not in {"ANSWER", "ABSTAIN_ESCALATE"}: system_errors += 1; outcome = "SYSTEM_ERROR"
        answer_count += response == "ANSWER"; verified_answers += verified
        statuses = [item.get("status") for item in output.get("retrieved_evidence", [])]
        wrong_status_context += any(status != "APPROVED" for status in statuses)
        for citation in output.get("citations", []):
            draft += citation.get("status") == "DRAFT"; expired += citation.get("status") == "EXPIRED"
        for claim in output.get("claims", []):
            total_claims += 1; citation_ids = claim.get("citation_ids", []); citation_by_id = {row.get("citation_id"): row for row in output.get("citations", [])}
            claim_supported = verified and bool(citation_ids) and all(alias in citation_by_id for alias in citation_ids)
            supported_claims += claim_supported
            claims.append({"variant": output.get("variant_id"), "query_id": query["query_id"], "claim_text": claim.get("text"), "citation_ids": citation_ids,
                           "exact_support_quote": all(citation_by_id[alias].get("support_quote") == claim.get("text") for alias in citation_ids if alias in citation_by_id),
                           "verified": claim_supported, "relevant_answer": relevant})
        metadata_failures += response == "ANSWER" and not verified
        outcomes.append({"variant": output.get("variant_id"), "query_id": query["query_id"], "expected_response_type": query["expected_response_type"], "response_type": response, "outcome_class": outcome})
    total = len(outputs); positives = 40; negatives = 20; unsupported = total_claims - supported_claims
    metrics = {"case_count": total, "answer_count": answer_count, "abstain_count": total-answer_count,
               "positive_answer_count": positive_answers, "positive_relevant_answer_count": relevant_answers,
               "positive_wrong_evidence_answer_count": wrong_evidence, "positive_wrong_evidence_answer_rate": wrong_evidence/positives,
               "positive_unnecessary_abstention_count": positives-relevant_answers, "positive_unnecessary_abstention_rate": (positives-relevant_answers)/positives,
               "positive_grounded_resolution_recall": relevant_answers/positives, "positive_complete_multi_document_count": complete_multi,
               "positive_complete_multi_document_rate": complete_multi/6, "negative_abstention_accuracy": negative_abstains/negatives,
               "unsafe_answer_count": unsafe, "unsafe_answer_rate": unsafe/negatives, "safe_resolution_count": relevant_answers+negative_abstains,
               "safe_resolution_rate": (relevant_answers+negative_abstains)/total, "citation_correctness_on_answered": verified_answers/answer_count if answer_count else None,
               "citation_correctness_status": "APPLICABLE" if answer_count else "NOT_APPLICABLE_NO_ANSWERS", "unsupported_factual_claim_count": unsupported,
               "unsupported_factual_claim_rate": unsupported/total_claims if total_claims else None, "unsupported_claim_status": "APPLICABLE" if total_claims else "NOT_APPLICABLE_NO_CLAIMS",
               "total_claim_count": total_claims, "draft_citation_count": draft, "expired_citation_count": expired, "wrong_status_context_count": wrong_status_context,
               "citation_metadata_failure_count": metadata_failures, "system_error_count": system_errors,
               "reason_code_distribution": dict(sorted(reasons.items())), "outcome_class_distribution": dict(sorted(Counter(row["outcome_class"] for row in outcomes).items())),
               "intent_family_positive_recall": {key: family_correct[key]/family_total[key] for key in sorted(family_total)},
               "requested_dimension_positive_recall": {key: dimension_correct[key]/dimension_total[key] for key in sorted(dimension_total)},
               "negative_case_type_abstention_accuracy": {key: case_correct[key]/case_total[key] for key in sorted(case_total)}}
    if sum(metrics["outcome_class_distribution"].values()) != 60: raise CriticalEvaluationError("outcome partition does not total 60")
    return metrics, outcomes, claims


def _tag_variant(outputs: list[dict[str, Any]], variant: str) -> list[dict[str, Any]]:
    return [{**row, "variant_id": variant} for row in outputs]


def _acceptance(metrics: dict[str, Any], variant_config: dict[str, Any]) -> dict[str, Any]:
    a = variant_config["acceptance"]
    safety = metrics["unsafe_answer_count"] == 0 and metrics["positive_wrong_evidence_answer_count"] == 0 and metrics["unsupported_factual_claim_count"] == 0 and metrics["draft_citation_count"] == 0 and metrics["expired_citation_count"] == 0 and metrics["wrong_status_context_count"] == 0 and metrics["citation_metadata_failure_count"] == 0 and metrics["system_error_count"] == 0 and metrics["negative_abstention_accuracy"] == 1.0
    utility = metrics["positive_grounded_resolution_recall"] >= a["minimum_positive_grounded_resolution_recall"] and metrics["safe_resolution_rate"] >= a["minimum_safe_resolution_rate"] and min(metrics["intent_family_positive_recall"].values()) >= a["minimum_family_positive_recall"] and metrics["positive_complete_multi_document_count"] >= a["minimum_complete_multi_document_count"]
    return {"verdict": "PASS" if safety and utility else "PARTIAL" if safety else "FAILED", "hard_safety_pass": safety, "utility_pass": utility}


def _paired(queries: list[dict[str, Any]], left: list[dict[str, Any]], right: list[dict[str, Any]], as_of: date) -> dict[str, Any]:
    q = {row["query_id"]: row for row in queries}; a = {row["query_id"]: row for row in left}; b = {row["query_id"]: row for row in right}; counts = Counter(); rows = []
    for qid in sorted(q):
        ar = _is_relevant(q[qid], a[qid], as_of)[0]; br = _is_relevant(q[qid], b[qid], as_of)[0]
        if q[qid]["expected_response_type"] == "ANSWER": category = "R1_FIXES_R0_WRONG_ABSTAIN" if not ar and br else "R1_BREAKS_R0_CORRECT_ANSWER" if ar and not br else "BOTH_CORRECT" if ar and br else "BOTH_ABSTAIN_INCORRECTLY" if a[qid]["response_type"] == b[qid]["response_type"] == "ABSTAIN_ESCALATE" else "OTHER_POSITIVE"
        else: category = "R1_INTRODUCES_WRONG_ANSWER" if a[qid]["response_type"] == "ABSTAIN_ESCALATE" and b[qid]["response_type"] == "ANSWER" else "BOTH_ABSTAIN_CORRECTLY" if a[qid]["response_type"] == b[qid]["response_type"] == "ABSTAIN_ESCALATE" else "OTHER_NEGATIVE"
        counts[category] += 1; rows.append({"query_id": qid, "category": category, "r0_response": a[qid]["response_type"], "r1_response": b[qid]["response_type"]})
    return {"counts": dict(sorted(counts.items())), "rows": rows}


def finalize(root: Path, config_path: Path) -> dict[str, Any]:
    if (root / "reports/week_03/results/critical_eval_v1_integrity_incident_summary.json").exists():
        raise CriticalEvaluationError("critical_eval_v1 is invalidated; historical result finalization is prohibited")
    config = load_config(config_path); verify_pre_evaluation(root, config_path, require_unexecuted=False)
    reproduction = json.loads((root / config["outputs"]["reproduction"]).read_text(encoding="utf-8"))
    if not reproduction.get("primary_reproduction_identical"): raise CriticalEvaluationError("reproduction gate failed")
    queries = load_jsonl(root / config["dataset_path"]); as_of = date.fromisoformat(config["evaluation_as_of_date"])
    outputs = {VARIANT_IDS[0]: _tag_variant(load_jsonl(root / config["outputs"]["v0_outputs"]), VARIANT_IDS[0]), VARIANT_IDS[1]: _tag_variant(load_jsonl(root / config["outputs"]["v1_outputs"]), VARIANT_IDS[1]), VARIANT_IDS[2]: _tag_variant(load_jsonl(root / config["outputs"]["v2_outputs"]), VARIANT_IDS[2])}
    metrics = {}; all_outcomes = []; all_claims = []
    for variant, rows in outputs.items(): metrics[variant], outcomes, claims = compute_metrics(queries, rows, as_of); all_outcomes.extend(outcomes); all_claims.extend(claims)
    variant_config = json.loads((root / config["variant_config"]).read_text(encoding="utf-8")); acceptance = _acceptance(metrics[VARIANT_IDS[0]], variant_config)
    r0_r1 = _paired(queries, outputs[VARIANT_IDS[0]], outputs[VARIANT_IDS[1]], as_of)
    eligible = [name for name in VARIANT_IDS[:2] if _acceptance(metrics[name], variant_config)["hard_safety_pass"]]
    def selection_key(name: str) -> tuple[Any, ...]:
        m=metrics[name]; return (m["safe_resolution_count"],m["positive_relevant_answer_count"],m["positive_complete_multi_document_count"],min(m["intent_family_positive_recall"].values()),name==VARIANT_IDS[0])
    selected = max(eligible, key=selection_key) if eligible else None
    left, right = metrics[VARIANT_IDS[0]], metrics[VARIANT_IDS[2]]
    gate_ablation = {"answer_rate_delta": (right["answer_count"]-left["answer_count"])/60, "additional_positive_answers": right["positive_answer_count"]-left["positive_answer_count"],
                     "positive_grounded_recall_delta": right["positive_grounded_resolution_recall"]-left["positive_grounded_resolution_recall"], "negative_abstention_delta": right["negative_abstention_accuracy"]-left["negative_abstention_accuracy"],
                     "unsafe_answer_delta": right["unsafe_answer_count"]-left["unsafe_answer_count"], "unsupported_claim_delta": right["unsupported_factual_claim_count"]-left["unsupported_factual_claim_count"], "safe_resolution_delta": right["safe_resolution_rate"]-left["safe_resolution_rate"],
                     "prevented_by_v0_reason_codes": left["reason_code_distribution"], "always_answer_ineligible_for_production": True}
    payload = {"task_id": "W3-002", "variants": metrics, "production_candidate_acceptance": acceptance, "selected_production_variant": selected,
               "week3_p0_verdict": "AWAITING_REVIEW" if acceptance["verdict"]=="PASS" else "IN_PROGRESS" if acceptance["verdict"]=="PARTIAL" else "FAILED_BLOCKED"}
    write_json(root / config["outputs"]["variant_metrics"], payload); write_jsonl(root / config["outputs"]["outcome_classes"], all_outcomes); write_jsonl(root / config["outputs"]["claim_audit"], all_claims)
    write_json(root / config["outputs"]["r0_r1_paired"], {**r0_r1, "selected_production_variant": selected}); write_json(root / config["outputs"]["gate_ablation_paired"], gate_ablation)
    errors=[]; q={row["query_id"]:row for row in queries}
    for qid in sorted(q):
        trio=[outputs[name][next(i for i,row in enumerate(outputs[name]) if row["query_id"]==qid)] for name in VARIANT_IDS]
        relevant=[_is_relevant(q[qid], row, as_of)[0] for row in trio]
        criteria=[]
        if q[qid]["expected_response_type"]=="ANSWER" and not relevant[0]: criteria.append("V0_WRONG_ABSTAIN_OR_ANSWER")
        if trio[0]["response_type"]!=trio[1]["response_type"]: criteria.append("V1_DIFFERS_FROM_V0")
        if trio[0]["response_type"]!=trio[2]["response_type"]: criteria.append("V2_DIFFERS_FROM_V0")
        if q[qid].get("evidence_requirement")=="multi_document" and not _is_relevant(q[qid],trio[0],as_of)[1]: criteria.append("MULTI_DOCUMENT_INCOMPLETE")
        if not criteria: continue
        r0top=";".join(x["evidence_id"] for x in trio[0].get("retrieved_evidence",[])[:3]); r1top=";".join(x["evidence_id"] for x in trio[1].get("retrieved_evidence",[])[:3])
        relevant_ids=set(q[qid].get("gold_evidence_ids",[])+q[qid].get("acceptable_evidence_ids",[])); retrieved_ids=set(r0top.split(";"))
        if q[qid]["expected_response_type"]=="ANSWER" and trio[0]["response_type"]=="ANSWER" and not relevant[0] and q[qid].get("evidence_requirement")=="multi_document": root_cause="incomplete_multi_document_gold_coverage"
        elif q[qid]["expected_response_type"]=="ANSWER" and trio[0]["response_type"]=="ANSWER" and not relevant[0]: root_cause="verified_answer_cites_approved_but_unmapped_evidence"
        elif not (relevant_ids & retrieved_ids): root_cause="retrieval_miss"
        elif trio[0]["response_type"]=="ABSTAIN_ESCALATE": root_cause=f"gate_abstention:{trio[0]['gate'].get('reason_code','unknown')}"
        else: root_cause="relevant_evidence_retrieved_but_complete_claim_not_emitted"
        severe=q[qid]["expected_response_type"]=="ANSWER" and trio[0]["response_type"]=="ANSWER" and not relevant[0]
        claims_citations=" | ".join(f"{claim.get('text')} => {','.join(claim.get('citation_ids',[]))}" for claim in trio[0].get("claims",[]))
        errors.append({"query_id":qid,"query_text":q[qid]["query_text"],"expected_response":q[qid]["expected_response_type"],"intent_family":q[qid].get("intent_family"),"requested_dimension":q[qid]["requested_dimension"],"review_criteria":";".join(criteria),"gold_acceptable_evidence":";".join(q[qid].get("gold_evidence_ids",[])+q[qid].get("acceptable_evidence_ids",[])),"r0_top3":r0top,"r1_top3":r1top,"v0_output":f"{trio[0]['response_type']}:{trio[0]['gate'].get('reason_code')}","v1_output":f"{trio[1]['response_type']}:{trio[1]['gate'].get('reason_code')}","v2_output":f"{trio[2]['response_type']}:{trio[2]['gate'].get('reason_code')}","claims_citations":claims_citations,"root_cause":root_cause,"severity":"HIGH" if severe else "MEDIUM","production_implication":"Block Week 3 P0 on wrong-evidence answer; otherwise preserve the frozen diagnostic result.","regression_test_action":"test_positive_wrong_evidence_is_wrong_answer and mapping-integrity tests preserve the invariant."})
    path=root/config["outputs"]["error_analysis"]; path.parent.mkdir(parents=True,exist_ok=True)
    if errors:
        with path.open("w",encoding="utf-8",newline="") as target: writer=csv.DictWriter(target,fieldnames=list(errors[0])); writer.writeheader(); writer.writerows(errors)
    else: path.write_text("query_id\n",encoding="utf-8")
    artifact_keys=[key for key in config["outputs"] if key not in {"manifest","validation"}]
    manifest={"task_id":"W3-002","status":acceptance["verdict"],"created_at":datetime.now(timezone.utc).isoformat(),"critical_evaluated":True,"primary_run_count":1,"reproduction_run_count":1,"primary_reproduction_identical":True,"selected_production_variant":selected,"pre_evaluation_manifest_sha256":sha256_file(root/config["outputs"]["pre_evaluation_manifest"]),"dataset_sha256":sha256_file(root/config["dataset_path"]),"mapping_sha256":mapping_sha256(queries),"membership_sha256":membership_sha256(queries),"artifacts":{key:sha256_file(root/config["outputs"][key]) for key in artifact_keys}}
    write_json(root/config["outputs"]["manifest"],manifest)
    return {"status":acceptance["verdict"],"metrics":payload,"r0_r1":r0_r1,"gate_ablation":gate_ablation,"error_rows":len(errors),"manifest":manifest}


def verify_results(root: Path, config_path: Path) -> dict[str, Any]:
    config=load_config(config_path); verify_contract(root,config_path); pre=verify_pre_evaluation(root,config_path,require_unexecuted=False)
    manifest=json.loads((root/config["outputs"]["manifest"]).read_text(encoding="utf-8")); reproduction=json.loads((root/config["outputs"]["reproduction"]).read_text(encoding="utf-8"))
    if not reproduction.get("primary_reproduction_identical"): raise CriticalEvaluationError("reproduction identity missing")
    queries=load_jsonl(root/config["dataset_path"]); validate_scenarios(load_jsonl(root/config["scenario_path"]),config); as_of=date.fromisoformat(config["evaluation_as_of_date"])
    metrics={}
    for variant,key in zip(VARIANT_IDS,("v0_outputs","v1_outputs","v2_outputs"),strict=True):
        rows=_tag_variant(load_jsonl(root/config["outputs"][key]),variant)
        if len(rows)!=60 or len({row["query_id"] for row in rows})!=60: raise CriticalEvaluationError("variant output membership failure")
        metrics[variant]=compute_metrics(queries,rows,as_of)[0]
    stored=json.loads((root/config["outputs"]["variant_metrics"]).read_text(encoding="utf-8"))
    if stored["variants"]!=metrics: raise CriticalEvaluationError("metric tampering or drift")
    for key,digest in manifest["artifacts"].items():
        if sha256_file(root/config["outputs"][key])!=digest: raise CriticalEvaluationError(f"artifact hash mismatch: {key}")
    if manifest["dataset_sha256"]!=sha256_file(root/config["dataset_path"]) or manifest["mapping_sha256"]!=mapping_sha256(queries): raise CriticalEvaluationError("post-evaluation data/mapping change")
    from .critical_integrity import verify_integrity_incident
    integrity = verify_integrity_incident(root, config_path)
    result={"status":"PASS","historical_runtime_artifacts_internally_consistent":True,"historical_evaluator_reported_verdict":manifest["status"],
            "critical_mapping_integrity":"INVALID","final_model_verdict":"NOT_ESTABLISHED","week3_p0":"BLOCKED / IN PROGRESS",
            "tracked_verification":True,"runtime_cache_required":False,"network_required":False,"api_key_required":False,
            "primary_reproduction_identical":True,"original_pre_evaluation_manifest_hash_consistent":pre["status"]=="PASS","integrity_incident":integrity}
    write_json(root/config["outputs"]["validation"],result)
    return result
