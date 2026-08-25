"""Structured query audit logging without raw query or evaluation labels."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


class QueryAuditLogger:
    def __init__(self, path: Path | None = None, *, capture_records: bool = False):
        self._path = path
        self._capture_records = capture_records
        self.records: list[dict[str, Any]] = []
        self._lock = Lock()
        self._logger = logging.getLogger("payresolve_ai.service.query")

    def emit_success(self, query: str, response: dict[str, Any]) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": response["request_id"],
            "query_hash": hashlib.sha256(query.encode("utf-8")).hexdigest(),
            "intent": response["intent"]["name"] if response.get("intent") else None,
            "response_type": response["response_type"],
            "release_scope": response["release"]["scope"],
            "requires_human_review": response["release"]["requires_human_review"],
            "evidence_ids": [item["evidence_id"] for item in response["evidence"]],
            "citation_count": len(response["citations"]),
            "grounded": response["grounded"],
            "escalate": response["escalate"],
            "latency_ms": response["latency"]["total_ms"],
            **response["versions"],
            "status": "SUCCESS",
            "error_code": None,
        }
        self._emit(record)

    def emit_error(self, *, request_id: str | None, query: str | None, error_code: str) -> None:
        self._emit({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "query_hash": hashlib.sha256(query.encode("utf-8")).hexdigest() if query else None,
            "status": "ERROR",
            "error_code": error_code,
        })

    def _emit(self, record: dict[str, Any]) -> None:
        serialized = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self._logger.info(serialized)
        with self._lock:
            if self._capture_records:
                self.records.append(record)
            if self._path is not None:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with self._path.open("a", encoding="utf-8") as destination:
                    destination.write(serialized + "\n")
