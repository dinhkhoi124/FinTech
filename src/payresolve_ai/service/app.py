"""FastAPI application for the W4 safe-degraded local demo."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .adapters import RealPayResolveAIAdapter
from .audit_logging import QueryAuditLogger
from .contracts import (
    RUNTIME_MODE,
    SERVICE_VERSION,
    HealthResponse,
    QueryRequest,
    QueryResponse,
    ReadyResponse,
    SystemErrorResponse,
    VersionResponse,
)
from .query_service import QueryService, ServiceRuntimeFailure

DEFAULT_ORIGINS = ("http://localhost:8080", "http://127.0.0.1:8080")


def configured_origins() -> list[str]:
    raw = os.environ.get("PAYRESOLVE_CORS_ORIGINS")
    if raw is None:
        return list(DEFAULT_ORIGINS)
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    if not origins or "*" in origins:
        raise ValueError("CORS origins must be explicit")
    return origins


def _default_adapter_factory() -> RealPayResolveAIAdapter:
    return RealPayResolveAIAdapter()


def _default_audit_logger() -> QueryAuditLogger:
    raw_path = os.environ.get("PAYRESOLVE_QUERY_LOG_PATH")
    return QueryAuditLogger(Path(raw_path).resolve() if raw_path else None)


def create_app(
    *,
    adapter_factory: Callable[[], object] | None = None,
    audit_logger: QueryAuditLogger | None = None,
    allowed_origins: list[str] | None = None,
) -> FastAPI:
    factory = adapter_factory or _default_adapter_factory
    logger = audit_logger or _default_audit_logger()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.ready = False
        application.state.startup_error_code = None
        try:
            adapter = factory()
            application.state.query_service = QueryService(adapter, logger)
            application.state.versions = adapter.versions
            application.state.ready = True
        except Exception as error:
            application.state.startup_error_code = f"STARTUP_{type(error).__name__.upper()}"
            logger.emit_error(request_id=None, query=None, error_code=application.state.startup_error_code)
        yield

    application = FastAPI(title="PayResolve AI Safe-Degraded Demo", version=SERVICE_VERSION, lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins if allowed_origins is not None else configured_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @application.exception_handler(ServiceRuntimeFailure)
    async def runtime_failure_handler(_: Request, error: ServiceRuntimeFailure) -> JSONResponse:
        return JSONResponse(status_code=503, content={
            "request_id": error.request_id,
            "error": {
                "kind": "SYSTEM_ERROR",
                "code": error.error_code,
                "message": "The local PayResolve runtime could not complete the request.",
                "retryable": True,
            },
        })

    @application.get("/health", response_model=HealthResponse)
    async def health() -> dict:
        return {"status": "HEALTHY", "service_version": SERVICE_VERSION}

    @application.get("/ready", response_model=ReadyResponse)
    async def ready(request: Request):
        payload = {
            "ready": bool(request.app.state.ready),
            "runtime_mode": RUNTIME_MODE,
            "error_code": request.app.state.startup_error_code,
        }
        return payload if request.app.state.ready else JSONResponse(status_code=503, content=payload)

    @application.get("/version", response_model=VersionResponse)
    async def version(request: Request):
        if not request.app.state.ready:
            return JSONResponse(status_code=503, content={
                "request_id": None,
                "error": {
                    "kind": "SYSTEM_ERROR",
                    "code": request.app.state.startup_error_code or "RUNTIME_NOT_READY",
                    "message": "The local PayResolve runtime is not ready.",
                    "retryable": True,
                },
            })
        return {"runtime_mode": RUNTIME_MODE, "versions": request.app.state.versions}

    @application.post("/query", response_model=QueryResponse, responses={503: {"model": SystemErrorResponse}})
    async def query(payload: QueryRequest, request: Request):
        if not request.app.state.ready:
            error = ServiceRuntimeFailure(payload.request_id, request.app.state.startup_error_code or "RUNTIME_NOT_READY")
            return await runtime_failure_handler(request, error)
        return request.app.state.query_service.query(payload.request_id, payload.query)

    return application


app = create_app()
