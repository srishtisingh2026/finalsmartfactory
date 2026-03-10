from typing import Dict, Any, List

from .base import BaseProviderAdapter
from ..schema import RetrievalInfo, SpanModel
from ..utils import clean_text
from ..utils import compute_retrieval_metrics
from ..pricing import calculate_span_cost


class GeminiAdapter(BaseProviderAdapter):

    # ============================================================
    # USAGE EXTRACTION (TOP-LEVEL PROVIDER USAGE)
    # ============================================================

    def extract_usage(self, raw: Dict[str, Any]):

        usage = raw.get("provider_raw", {}).get("usage", {}) or {}

        prompt = int(usage.get("prompt_tokens", 0) or 0)
        completion = int(usage.get("completion_tokens", 0) or 0)
        total = int(usage.get("total_tokens", prompt + completion) or 0)

        return prompt, completion, total

    # ============================================================
    # RETRIEVAL METADATA (SPAN-BASED)
    # ============================================================

    def extract_retrieval(self, raw: Dict[str, Any]):

        retrieval_span = None

        for span in raw.get("spans", []):
            if span.get("type") == "retrieval":
                retrieval_span = span
                break

        if not retrieval_span:
            return RetrievalInfo(
                executed=False,
                documents_found=0,
                retrieval_confidence=None,
                best_score=None,
            )

        meta = retrieval_span.get("metadata", {}) or {}

        docs = meta.get("documents", []) or []
        scores = meta.get("scores", []) or []

        documents_found = len(docs)

        metrics = compute_retrieval_metrics(scores)

        return RetrievalInfo(
            executed=True,
            documents_found=documents_found,
            retrieval_confidence=metrics["retrieval_confidence"],
            best_score=metrics["max_score"],
        )

    # ============================================================
    # SPAN NORMALIZATION
    # ============================================================

    def extract_spans(self, raw: Dict[str, Any]) -> List[SpanModel]:

        normalized_spans: List[SpanModel] = []

        model = raw.get("model", "") or ""

        for span in raw.get("spans", []):

            usage = span.get("usage", {}) or {}
            metadata = span.get("metadata", {}) or {}

            prompt = int(usage.get("prompt_tokens", 0) or 0)
            completion = int(usage.get("completion_tokens", 0) or 0)
            total = int(usage.get("total_tokens", prompt + completion) or 0)

            span_type = str(span.get("type", "unknown"))
            span_name = str(span.get("name", "unknown"))

            latency = int(span.get("latency_ms", 0) or 0)

            cost = 0.0
            if span_type == "llm":
                cost = calculate_span_cost(model, prompt, completion)

            span_data = dict(
                span_id=str(span.get("span_id", "unknown")),
                parent_span_id=span.get("parent_span_id"),   # <-- ADD THIS
                trace_id=str(span.get("trace_id", raw.get("trace_id"))),
                type=span_type,
                name=str(span.get("name", "unknown")),
                status=str(span.get("status", "success")),
                start_time=int(span.get("start_time", 0) or 0),
                end_time=int(span.get("end_time", 0) or 0),
                latency_ms=int(span.get("latency_ms", 0) or 0),
                prompt_tokens=prompt,
                completion_tokens=completion,
                total_tokens=total,
                cost_usd=cost,

            )

            if span_type == "llm":

                temperature = metadata.get("temperature")
                context_tokens = metadata.get("context_tokens")

                if temperature is not None:
                    span_data["temperature"] = temperature

                if context_tokens is not None:
                    span_data["context_tokens"] = context_tokens

            normalized_spans.append(SpanModel(**span_data))

        return normalized_spans

    # ============================================================
    # RETRIEVED DOCUMENT CONTENT (SPAN-BASED)
    # ============================================================

    def extract_retrieved_context(self, raw: Dict[str, Any]):

        contexts: List[str] = []

        for span in raw.get("spans", []):

            if span.get("type") != "retrieval":
                continue

            meta = span.get("metadata", {}) or {}

            docs = meta.get("documents", []) or []

            for doc in docs:

                if isinstance(doc, dict):
                    content = doc.get("content") or doc.get("content_preview")
                else:
                    content = str(doc)

                if content:
                    contexts.append(clean_text(content))

        return contexts