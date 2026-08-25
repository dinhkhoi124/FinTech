"""PAYRESOLVE_QUERY_API_V1 HTTP contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

API_CONTRACT_VERSION = "PAYRESOLVE_QUERY_API_V1"
RUNTIME_MODE = "REAL_SAFE_DEGRADED"
SERVICE_VERSION = "w4_safe_degraded_service_v1"


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    query: str = Field(min_length=1, max_length=4000)

    @field_validator("request_id", "query")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class IntentMetadata(BaseModel):
    name: str
    confidence: float = Field(ge=0.0, le=1.0)


class Citation(BaseModel):
    citation_id: str
    evidence_id: str
    document_id: str
    section_id: str
    title: str
    document_type: str
    status: str
    version: str


class Evidence(BaseModel):
    evidence_id: str
    document_id: str
    section_id: str
    title: str
    document_type: str
    status: str
    version: str
    effective_date: str
    expiry_date: str | None
    intent_scope: list[str]
    heading: str
    content: str
    score: float
    rank: int


class ReleaseMetadata(BaseModel):
    scope: Literal["SAFE_DEGRADED_DEMO"]
    requires_human_review: Literal[True]
    autonomous_action_allowed: Literal[False]
    production_approved: Literal[False]


class VersionMetadata(BaseModel):
    service_version: str
    api_contract_version: Literal["PAYRESOLVE_QUERY_API_V1"]
    model_version: str
    kb_version: str
    retrieval_version: str
    candidate_commit: str


class LatencyMetadata(BaseModel):
    total_ms: float = Field(ge=0.0)
    classification_ms: float | None = Field(default=None, ge=0.0)
    retrieval_ms: float | None = Field(default=None, ge=0.0)
    generation_ms: float | None = Field(default=None, ge=0.0)


class QueryResponse(BaseModel):
    request_id: str
    runtime_mode: Literal["REAL_SAFE_DEGRADED"]
    response_type: Literal["ANSWER_STANDARD", "ANSWER_SAFE_CORRECTIVE", "ABSTAIN_ESCALATE"]
    intent: IntentMetadata | None
    answer: str
    reason: str
    grounded: bool
    escalate: bool
    citations: list[Citation]
    evidence: list[Evidence]
    release: ReleaseMetadata
    versions: VersionMetadata
    latency: LatencyMetadata


class HealthResponse(BaseModel):
    status: Literal["HEALTHY"]
    service_version: str


class ReadyResponse(BaseModel):
    ready: bool
    runtime_mode: Literal["REAL_SAFE_DEGRADED"]
    error_code: str | None = None


class VersionResponse(BaseModel):
    runtime_mode: Literal["REAL_SAFE_DEGRADED"]
    versions: VersionMetadata


class SystemErrorDetail(BaseModel):
    kind: Literal["SYSTEM_ERROR"]
    code: str
    message: str
    retryable: bool


class SystemErrorResponse(BaseModel):
    request_id: str | None
    error: SystemErrorDetail
