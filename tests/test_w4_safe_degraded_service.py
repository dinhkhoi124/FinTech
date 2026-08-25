from __future__ import annotations

import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from payresolve_ai.service.adapters import AdapterResult, RealPayResolveAIAdapter
from payresolve_ai.service.app import create_app
from payresolve_ai.service.audit_logging import QueryAuditLogger
from payresolve_ai.service.contracts import API_CONTRACT_VERSION


VERSIONS = {
    "service_version": "w4_safe_degraded_service_v1",
    "api_contract_version": API_CONTRACT_VERSION,
    "model_version": "model@revision",
    "kb_version": "kb_v1",
    "retrieval_version": "R0",
    "candidate_commit": "a" * 40,
}
EVIDENCE = {
    "evidence_id": "kb:demo:section",
    "document_id": "kb:demo",
    "section_id": "section",
    "title": "Approved demo guidance",
    "document_type": "SUPPORT_GUIDANCE",
    "status": "APPROVED",
    "version": "1.0",
    "effective_date": "2026-01-01",
    "expiry_date": None,
    "intent_scope": ["cash_withdrawal"],
    "heading": "Next steps",
    "content": "Check the transaction status and contact support if it remains pending.",
    "score": 0.9,
    "rank": 1,
}
CITATION = {
    "citation_id": "E1",
    "evidence_id": EVIDENCE["evidence_id"],
    "document_id": EVIDENCE["document_id"],
    "section_id": EVIDENCE["section_id"],
    "title": EVIDENCE["title"],
    "document_type": EVIDENCE["document_type"],
    "status": "APPROVED",
    "version": "1.0",
}


def core_output(strategy: str = "STANDARD") -> dict:
    abstain = strategy == "ABSTAIN"
    return {
        "response_type": "ABSTAIN_ESCALATE" if abstain else "ANSWER",
        "answer_strategy": strategy,
        "answer_text": "Escalate to support." if abstain else "Check the transaction status.",
        "citations": [] if abstain else [CITATION],
        "selected_evidence": [] if abstain else [EVIDENCE],
        "retrieved_evidence": [EVIDENCE],
        "response_plan": {"reason_codes": ["TEST_REASON"]},
    }


class FakeAdapter:
    versions = VERSIONS

    def __init__(self, strategy: str = "STANDARD", *, fail: bool = False):
        self.strategy = strategy
        self.fail = fail

    def query(self, request_id: str, query_text: str) -> AdapterResult:
        if self.fail:
            raise OSError("synthetic runtime failure")
        return AdapterResult(core_output(self.strategy), "cash_withdrawal", 0.87, 1.0, 2.0, 3.0)


def client_for(adapter: FakeAdapter, logger: QueryAuditLogger | None = None) -> TestClient:
    return TestClient(create_app(adapter_factory=lambda: adapter, audit_logger=logger))


def test_health_ready_and_version_endpoints() -> None:
    with client_for(FakeAdapter()) as client:
        assert client.get("/health").json()["status"] == "HEALTHY"
        assert client.get("/ready").json() == {
            "ready": True,
            "runtime_mode": "REAL_SAFE_DEGRADED",
            "error_code": None,
        }
        version = client.get("/version").json()
        assert version["versions"] == VERSIONS


@pytest.mark.parametrize(
    ("strategy", "expected_type"),
    [("STANDARD", "ANSWER_STANDARD"), ("CORRECTIVE", "ANSWER_SAFE_CORRECTIVE")],
)
def test_factual_answers_are_grounded_and_human_review_only(strategy: str, expected_type: str) -> None:
    with client_for(FakeAdapter(strategy)) as client:
        response = client.post("/query", json={"request_id": "req-1", "query": "What should I check?"})
    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "req-1"
    assert body["response_type"] == expected_type
    assert body["grounded"] is True
    assert body["escalate"] is False
    assert body["release"] == {
        "scope": "SAFE_DEGRADED_DEMO",
        "requires_human_review": True,
        "autonomous_action_allowed": False,
        "production_approved": False,
    }
    assert body["citations"][0]["evidence_id"] == EVIDENCE["evidence_id"]
    assert body["evidence"][0]["status"] == "APPROVED"
    assert body["latency"]["total_ms"] >= 0


def test_abstain_escalates_without_autonomous_action() -> None:
    with client_for(FakeAdapter("ABSTAIN")) as client:
        body = client.post("/query", json={"request_id": "req-abstain", "query": "Unsupported request"}).json()
    assert body["response_type"] == "ABSTAIN_ESCALATE"
    assert body["grounded"] is False
    assert body["escalate"] is True
    assert body["release"]["autonomous_action_allowed"] is False


@pytest.mark.parametrize("payload", [
    {"request_id": "req-empty", "query": "   "},
    {"request_id": "bad id", "query": "valid"},
    {"request_id": "req-extra", "query": "valid", "fixtureId": "mock-only"},
])
def test_invalid_contract_is_rejected(payload: dict) -> None:
    with client_for(FakeAdapter()) as client:
        assert client.post("/query", json=payload).status_code == 422


def test_system_error_is_structurally_distinct_from_abstain() -> None:
    with client_for(FakeAdapter(fail=True)) as client:
        response = client.post("/query", json={"request_id": "req-error", "query": "Run the runtime"})
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["kind"] == "SYSTEM_ERROR"
    assert body["request_id"] == "req-error"
    assert "response_type" not in body


def test_structured_log_hashes_query_and_has_no_forbidden_fields(tmp_path) -> None:
    log_path = tmp_path / "queries.jsonl"
    logger = QueryAuditLogger(log_path, capture_records=True)
    raw_query = "private demo query text"
    with client_for(FakeAdapter(), logger) as client:
        assert client.post("/query", json={"request_id": "req-log", "query": raw_query}).status_code == 200
    record = json.loads(log_path.read_text(encoding="utf-8"))
    assert record == logger.records[0]
    assert len(record["query_hash"]) == 64
    assert raw_query not in json.dumps(record)
    assert not ({"query", "gold", "evaluator"} & set(record))


def test_cors_is_explicit_for_local_shell() -> None:
    with client_for(FakeAdapter()) as client:
        response = client.options("/query", headers={
            "Origin": "http://localhost:8080",
            "Access-Control-Request-Method": "POST",
        })
        rejected = client.options("/query", headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
        })
    assert response.headers["access-control-allow-origin"] == "http://localhost:8080"
    assert "access-control-allow-origin" not in rejected.headers


def test_real_adapter_calls_v3_pipeline_interface_not_fixture(monkeypatch) -> None:
    observed = {}

    class Encoder:
        def encode_function(self, texts):
            observed["model_inputs"] = list(texts)
            return np.asarray([[1.0, 0.0]], dtype=np.float32)

    chunk = {**EVIDENCE, "chunk_id": EVIDENCE["evidence_id"], "text": "Approved demo guidance\nNext steps\n" + EVIDENCE["content"]}
    generation_config = {
        "tokenizer": {"stopwords": []},
    }
    adapter = RealPayResolveAIAdapter.from_components(
        encoder=Encoder(),
        classes=["cash_withdrawal", "other"],
        coefficients=np.asarray([[1.0, 0.0], [0.0, 1.0]]),
        intercept=np.asarray([0.0, 0.0]),
        chunks=[chunk],
        corpus_embeddings=np.asarray([[1.0, 0.0]], dtype=np.float32),
        retrieval_config={"encoder": {"dimension": 2}, "retrieval": {"top_k": 1}},
        generation_config=generation_config,
        lexicon={"concepts": {}},
        versions=VERSIONS,
    )

    def fake_run_case(query, rankings, chunks, raw_idf, canonical_idf, config, lexicon):
        observed["query"] = query
        observed["rankings"] = rankings
        observed["chunks"] = chunks
        return core_output("STANDARD")

    monkeypatch.setattr("payresolve_ai.service.adapters.run_case_v3", fake_run_case)
    result = adapter.query("req-real-interface", "Manual non-holdout demo query")
    assert result.core_output["answer_strategy"] == "STANDARD"
    assert observed["query"] == {
        "query_id": "req-real-interface",
        "query_text": "Manual non-holdout demo query",
    }
    assert "fixtureId" not in observed["query"]
    assert observed["rankings"][0]["chunk_id"] == EVIDENCE["evidence_id"]
