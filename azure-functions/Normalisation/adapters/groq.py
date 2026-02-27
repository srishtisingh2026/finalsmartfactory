from typing import Dict, Any, List
from .base import BaseProviderAdapter
from ..schema import RetrievalInfo, SpanModel
from ..utils import clean_text
from ..pricing import calculate_span_cost


class GroqAdapter(BaseProviderAdapter):

    # ============================================================
    # USAGE EXTRACTION
    # ============================================================

    def extract_usage(self, raw: Dict[str, Any]):

        # First try span-level usage
        for span in raw.get("spans", []):
            if span.get("type") == "llm" and span.get("usage"):
                usage = span["usage"]
                return (
                    int(usage.get("prompt_tokens", 0) or 0),
                    int(usage.get("completion_tokens", 0) or 0),
                    int(usage.get("total_tokens", 0) or 0),
                )

        # Fallback to provider_raw
        usage = raw.get("provider_raw", {}).get("usage", {})

        return (
            int(usage.get("prompt_tokens", 0) or 0),
            int(usage.get("completion_tokens", 0) or 0),
            int(usage.get("total_tokens", 0) or 0),
        )

    # ============================================================
    # RETRIEVAL METADATA
    # ============================================================

    def extract_retrieval(self, raw: Dict[str, Any]):

        return RetrievalInfo(
            executed=bool(raw.get("retrieval_executed", False)),
            documents_found=int(raw.get("documents_found", 0) or 0),
            retrieval_confidence=raw.get("retrieval_confidence"),
            best_score=(raw.get("rag_data") or {}).get("best_score"),
        )

    # ============================================================
    # SPAN NORMALIZATION
    # ============================================================


    def extract_spans(self, raw):

        spans = []

        model = raw.get("model")

        for span in raw.get("spans", []):

            usage = span.get("usage", {}) or {}

            prompt = int(usage.get("prompt_tokens", 0) or 0)
            completion = int(usage.get("completion_tokens", 0) or 0)
            total = int(usage.get("total_tokens", 0) or 0)

            cost = 0.0
            if span.get("type") == "llm":
                cost = calculate_span_cost(model, prompt, completion)

            spans.append(
                SpanModel(
                    span_id=str(span.get("span_id", "unknown")),
                    type=str(span.get("type", "unknown")),
                    name=str(span.get("name", "unknown")),
                    latency_ms=int(span.get("latency_ms", 0) or 0),
                    prompt_tokens=prompt,
                    completion_tokens=completion,
                    total_tokens=total,
                    cost_usd=cost,
                )
            )

        return spans
    # ============================================================
    # RETRIEVED DOCUMENT CONTENT
    # ============================================================

    def extract_retrieved_context(self, raw: Dict[str, Any]):

        contexts = []

        rag_data = raw.get("rag_data", {})
        docs = rag_data.get("retrieved_documents", [])

        for doc in docs:
            if isinstance(doc, dict):
                content = doc.get("content") or doc.get("content_preview")
                if content:
                    contexts.append(clean_text(content))

        return contexts