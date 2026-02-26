import logging
import os
import re
import ast
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime

from pydantic import BaseModel
from azure.cosmos import CosmosClient


# ============================================================
# ENUMS
# ============================================================

class StatusEnum(str, Enum):
    success = "success"
    failure = "failure"


# ============================================================
# CANONICAL SCHEMA
# ============================================================

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
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


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


# ============================================================
# MODEL PRICING
# ============================================================

MODEL_PRICING = {
    "llama-3.1-8b-instant": {"input_per_1k": 0.00005, "output_per_1k": 0.00008},
    "llama-3.3-70b-versatile": {"input_per_1k": 0.00059, "output_per_1k": 0.00079},
    "openai/gpt-oss-120b": {"input_per_1k": 0.00015, "output_per_1k": 0.00060},
}


# ============================================================
# PROVIDER DETECTION
# ============================================================

def detect_provider(raw: Dict[str, Any]) -> str:
    if raw.get("provider"):
        return raw["provider"]

    model = str(raw.get("model", "")).lower()

    if "gemini" in model:
        return "google"
    if "gpt" in model or "openai" in model:
        return "openai"
    if "llama" in model:
        return "groq"

    return "unknown"


# ============================================================
# SAFE HELPERS
# ============================================================

def safe_extract_text(value):
    if value is None:
        return None

    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        for key in ["query", "answer", "response", "content", "text"]:
            if key in value and isinstance(value[key], str):
                return value[key]
        return str(value)

    return str(value)


def extract_input(raw):
    return safe_extract_text(
        raw.get("input")
        or raw.get("question")
        or raw.get("request", {}).get("input")
    )


def extract_output(raw):
    output = raw.get("output")

    if output:
        extracted = safe_extract_text(output)
        if extracted:
            return extracted

    provider_raw = raw.get("provider_raw", {})
    choices = provider_raw.get("choices", [])
    if choices:
        return safe_extract_text(
            choices[0].get("message", {}).get("content")
        )

    return None


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\\n", " ")
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# RETRIEVAL EXTRACTION
# ============================================================

def extract_retrieval_info(raw):

    # Groq-style retrieval
    if raw.get("retrieval_executed") is not None:
        return RetrievalInfo(
            executed=bool(raw.get("retrieval_executed", False)),
            documents_found=int(raw.get("documents_found", 0) or 0),
            retrieval_confidence=raw.get("retrieval_confidence"),
            best_score=(raw.get("rag_data") or {}).get("best_score"),
        )

    # Gemini-style vector-search span
    for span in raw.get("spans", []):
        if span.get("name") == "vector-search":
            docs = span.get("output", {}).get("documents", [])
            return RetrievalInfo(
                executed=True,
                documents_found=len(docs),
            )

    return RetrievalInfo()


def extract_retrieved_context(raw):

    contexts = []

    # Groq style
    rag_data = raw.get("rag_data", {})
    docs = rag_data.get("retrieved_documents", [])

    for doc in docs:
        if isinstance(doc, dict):
            content = doc.get("content") or doc.get("content_preview")
            if content:
                contexts.append(clean_text(content))

    # Gemini style
    for span in raw.get("spans", []):
        if span.get("name") == "vector-search":
            documents = span.get("output", {}).get("documents", [])
            for doc in documents:
                content = doc.get("content")
                if content:
                    contexts.append(clean_text(content))

    return contexts


# ============================================================
# USAGE EXTRACTION
# ============================================================

def extract_usage(raw):

    # Gemini direct fields
    if raw.get("tokens_in") or raw.get("tokens_out"):
        prompt = int(raw.get("tokens_in", 0))
        completion = int(raw.get("tokens_out", 0))
        total = int(raw.get("tokens", prompt + completion))
        return prompt, completion, total

    # Span-based usage
    for span in raw.get("spans", []):
        if span.get("type") == "llm" and span.get("usage"):
            usage = span["usage"]
            return (
                int(usage.get("prompt_tokens", 0)),
                int(usage.get("completion_tokens", 0)),
                int(usage.get("total_tokens", 0)),
            )

    # provider_raw fallback
    usage = raw.get("provider_raw", {}).get("usage", {})
    return (
        int(usage.get("prompt_tokens", 0)),
        int(usage.get("completion_tokens", 0)),
        int(usage.get("total_tokens", 0)),
    )


# ============================================================
# COST CALCULATION
# ============================================================

def calculate_cost(model, prompt_tokens, completion_tokens):
    pricing = MODEL_PRICING.get(model, {"input_per_1k": 0, "output_per_1k": 0})

    input_cost = (prompt_tokens / 1000) * pricing["input_per_1k"]
    output_cost = (completion_tokens / 1000) * pricing["output_per_1k"]

    return CostInfo(
        input_cost_usd=round(input_cost, 6),
        output_cost_usd=round(output_cost, 6),
        total_cost_usd=round(input_cost + output_cost, 6),
    )


# ============================================================
# NORMALIZER
# ============================================================

def normalize_trace(raw):

    timestamp = raw.get("timestamp", 0)

    if isinstance(timestamp, str):
        try:
            timestamp = int(datetime.fromisoformat(timestamp).timestamp() * 1000)
        except Exception:
            timestamp = 0

    latency = raw.get("latency_ms", 0)
    if isinstance(latency, float):
        latency = int(latency)

    status = raw.get("status", "success")
    if status not in ["success", "failure"]:
        status = "success"

    provider = detect_provider(raw)

    prompt_tokens, completion_tokens, total_tokens = extract_usage(raw)

    cost = calculate_cost(
        raw.get("model"),
        prompt_tokens,
        completion_tokens,
    )

    spans = []
    for span in raw.get("spans", []):
        try:
            usage = span.get("usage", {})
            spans.append(
                SpanModel(
                    span_id=str(span.get("span_id", "unknown")),
                    type=str(span.get("type", span.get("name", "unknown"))),
                    name=str(span.get("name", "unknown")),
                    latency_ms=int(span.get("latency_ms", 0) or 0),
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens"),
                    total_tokens=usage.get("total_tokens"),
                )
            )
        except Exception:
            continue

    trace_id = raw.get("trace_id") or raw.get("id")

    return CanonicalTrace(
        id=str(trace_id),
        trace_id=str(trace_id),
        trace_name=str(raw.get("trace_name", "unknown")),

        input_text=extract_input(raw),
        output_text=extract_output(raw),
        retrieved_context=extract_retrieved_context(raw),

        session=SessionInfo(
            session_id=str(raw.get("session_id", "unknown")),
            user_id=str(raw.get("user_id", "unknown")),
        ),
        request=RequestInfo(
            timestamp=int(timestamp),
            environment=str(raw.get("environment", "unknown")),
            intent=raw.get("intent"),
        ),
        model_info=ModelInfo(
            provider=provider,
            model=str(raw.get("model", "unknown")),
            temperature=raw.get("temperature"),
        ),
        performance=PerformanceInfo(
            latency_ms=int(latency),
            status=status,
        ),
        usage=UsageInfo(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        ),
        cost=cost,
        retrieval=extract_retrieval_info(raw),
        spans=spans,
    )


# ============================================================
# AZURE FUNCTION ENTRY
# ============================================================

def main(documents):

    if not documents:
        logging.info("No documents received.")
        return

    logging.info(f"Processing {len(documents)} raw traces...")

    cosmos = CosmosClient.from_connection_string(
        os.environ["COSMOS_CONN_WRITE"]
    )

    db = cosmos.get_database_client("llmops-data")
    traces_container = db.get_container_client("traces")

    for raw in documents:
        try:
            canonical = normalize_trace(raw)
            traces_container.upsert_item(canonical.model_dump())
            logging.info(f"Normalized trace {canonical.trace_id}")
        except Exception as e:
            logging.error(f"Normalization failed: {str(e)}")