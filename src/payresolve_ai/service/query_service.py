"""Application service coordinating the real adapter, release policy, and logs."""

from __future__ import annotations

from time import perf_counter
from typing import Protocol

from .adapters import AdapterResult
from .audit_logging import QueryAuditLogger
from .release_policy import apply_safe_degraded_policy


class QueryAdapter(Protocol):
    versions: dict[str, str]

    def query(self, request_id: str, query_text: str) -> AdapterResult: ...


class ServiceRuntimeFailure(RuntimeError):
    def __init__(self, request_id: str, error_code: str):
        super().__init__(error_code)
        self.request_id = request_id
        self.error_code = error_code


class QueryService:
    def __init__(self, adapter: QueryAdapter, audit_logger: QueryAuditLogger):
        self.adapter = adapter
        self.audit_logger = audit_logger

    def query(self, request_id: str, query_text: str) -> dict:
        started = perf_counter()
        try:
            result = self.adapter.query(request_id, query_text)
            response = apply_safe_degraded_policy(
                request_id=request_id,
                core_output=result.core_output,
                intent_name=result.intent_name,
                intent_confidence=result.intent_confidence,
                versions=self.adapter.versions,
                latency={
                    "total_ms": (perf_counter() - started) * 1000,
                    "classification_ms": result.classification_ms,
                    "retrieval_ms": result.retrieval_ms,
                    "generation_ms": result.generation_ms,
                },
            )
            self.audit_logger.emit_success(query_text, response)
            return response
        except Exception as error:
            error_code = f"RUNTIME_{type(error).__name__.upper()}"
            self.audit_logger.emit_error(request_id=request_id, query=query_text, error_code=error_code)
            raise ServiceRuntimeFailure(request_id, error_code) from None
