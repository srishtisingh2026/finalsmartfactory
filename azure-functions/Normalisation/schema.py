from enum import Enum
from typing import Optional, List
from pydantic import BaseModel


class StatusEnum(str, Enum):
    success = "success"
    failure = "failure"


class SessionInfo(BaseModel):
    session_id: str
    user_id: str


class RequestInfo(BaseModel):
    timestamp: int
    environment: str
    intent: Optional[str] = None


class ModelInfo(BaseModel):
    provider: str
    model: str
    temperature: Optional[float] = None


class PerformanceInfo(BaseModel):
    latency_ms: int
    status: StatusEnum


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class CostInfo(BaseModel):
    input_cost_usd: float = 0.0
    output_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    currency: str = "USD"


class RetrievalInfo(BaseModel):
    executed: bool = False
    documents_found: int = 0
    retrieval_confidence: Optional[float] = None
    best_score: Optional[float] = None


class SpanModel(BaseModel):
    span_id: str
    type: str
    name: str
    latency_ms: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0   # ← ADD THIS


class CanonicalTrace(BaseModel):
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