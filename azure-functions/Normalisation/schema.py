from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# =========================================================
# Base Schema
# Ensures None fields are excluded automatically
# =========================================================

class BaseSchema(BaseModel):

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        ser_json_exclude_none=True
    )


# =========================================================
# Status Enum
# =========================================================

class StatusEnum(str, Enum):
    success = "success"
    failure = "failure"


# =========================================================
# Session Information
# =========================================================

class SessionInfo(BaseSchema):

    session_id: str
    user_id: str


# =========================================================
# Request Information
# =========================================================

class RequestInfo(BaseSchema):

    timestamp: int
    environment: str
    intent: Optional[str] = None


# =========================================================
# Model Information
# =========================================================

class ModelInfo(BaseSchema):

    provider: str
    model: str


# =========================================================
# Performance Metrics
# =========================================================

class PerformanceInfo(BaseSchema):

    latency_ms: int
    status: StatusEnum


# =========================================================
# Usage Metrics
# =========================================================

class UsageInfo(BaseSchema):

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


# =========================================================
# Cost Metrics
# =========================================================

class CostInfo(BaseSchema):

    input_cost_usd: float = 0.0
    output_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    currency: str = "USD"


# =========================================================
# Retrieval Metadata
# =========================================================

class RetrievalInfo(BaseSchema):

    executed: bool = False
    documents_found: int = 0
    retrieval_confidence: Optional[float] = None
    best_score: Optional[float] = None


# =========================================================
# Span Model
# =========================================================

class SpanModel(BaseSchema):

    span_id: str
    type: str
    name: str
    latency_ms: int

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

    # Only present for LLM spans
    temperature: Optional[float] = None
    context_tokens: Optional[int] = None


# =========================================================
# Canonical Trace
# =========================================================

class CanonicalTrace(BaseSchema):

    id: str
    trace_id: str
    trace_name: str

    input_text: Optional[str] = None
    output_text: Optional[str] = None
    retrieved_context: Optional[List[str]] = None

    session: SessionInfo
    request: RequestInfo
    model_info: ModelInfo
    performance: PerformanceInfo
    usage: UsageInfo
    cost: CostInfo
    retrieval: RetrievalInfo

    spans: List[SpanModel]