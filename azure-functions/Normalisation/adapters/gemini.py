from typing import Dict, Any, List
from .base import BaseProviderAdapter
from ..schema import RetrievalInfo, SpanModel
from ..utils import clean_text
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
    # RETRIEVAL METADATA
    # ============================================================

    def extract_retrieval(self, raw: Dict[str, Any]):

        for span in raw.get("spans", []):

            if span.get("name") == "vector-search" or span.get("type") == "retrieval":
                docs = span.get("output", {}).get("documents", []) or []

                return RetrievalInfo(
                    executed=True,
                    documents_found=len(docs),
                )

        return RetrievalInfo(
            executed=False,
            documents_found=0,
        )

    # ============================================================
    # SPAN NORMALIZATION
    # ============================================================

    def extract_spans(self, raw: Dict[str, Any]) -> List[SpanModel]:

        normalized_spans: List[SpanModel] = []

        model = raw.get("model", "") or ""

        for span in raw.get("spans", []):

            metadata = span.get("metadata", {}) or {}

            # Gemini span tokens live inside metadata
            prompt = int(metadata.get("tokens_in", 0) or 0)
            completion = int(metadata.get("tokens_out", 0) or 0)
            total = prompt + completion

            span_type = str(span.get("type", "unknown"))
            span_name = str(span.get("name", "unknown"))

            latency = int(span.get("latency_ms", 0) or 0)

            # 🔥 Only calculate cost for actual LLM generation spans
            cost = 0.0
            if span_type == "llm":
                cost = calculate_span_cost(model, prompt, completion)

            normalized_spans.append(
                SpanModel(
                    span_id=str(span.get("span_id", "unknown")),
                    type=span_type,
                    name=span_name,
                    latency_ms=latency,
                    prompt_tokens=prompt,
                    completion_tokens=completion,
                    total_tokens=total,
                    cost_usd=cost,
                )
            )

        return normalized_spans

    # ============================================================
    # RETRIEVED DOCUMENT CONTENT
    # ============================================================

    def extract_retrieved_context(self, raw: Dict[str, Any]):

        contexts: List[str] = []

        for span in raw.get("spans", []):

            if span.get("name") == "vector-search" or span.get("type") == "retrieval":

                documents = span.get("output", {}).get("documents", []) or []

                for doc in documents:
                    content = doc.get("content")
                    if content:
                        contexts.append(clean_text(content))

        return contexts