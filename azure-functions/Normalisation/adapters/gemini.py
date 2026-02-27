from typing import Dict, Any, List
from .base import BaseProviderAdapter
from ..schema import RetrievalInfo, SpanModel
from ..utils import clean_text
from ..pricing import calculate_span_cost


class GeminiAdapter(BaseProviderAdapter):

    # ============================================================
    # USAGE EXTRACTION
    # ============================================================

    def extract_usage(self, raw: Dict[str, Any]):

        prompt = int(raw.get("tokens_in", 0) or 0)
        completion = int(raw.get("tokens_out", 0) or 0)
        total = int(raw.get("tokens", prompt + completion) or 0)

        return prompt, completion, total

    # ============================================================
    # RETRIEVAL METADATA
    # ============================================================

    def extract_retrieval(self, raw: Dict[str, Any]):

        for span in raw.get("spans", []):
            if span.get("name") == "vector-search":
                docs = span.get("output", {}).get("documents", [])
                return RetrievalInfo(
                    executed=True,
                    documents_found=len(docs),
                )

        return RetrievalInfo()

    # ============================================================
    # SPAN NORMALIZATION
    # ============================================================

    def extract_spans(self, raw: Dict[str, Any]) -> List[SpanModel]:

        spans = []
        model = raw.get("model")

        for span in raw.get("spans", []):

            metadata = span.get("metadata", {}) or {}

            prompt = int(metadata.get("tokens_in", 0) or 0)
            completion = int(metadata.get("tokens_out", 0) or 0)
            total = prompt + completion

            span_type = str(span.get("name", "unknown"))
            latency = int(span.get("latency_ms", 0) or 0)

            # 🔥 Calculate cost only for generation span
            cost = 0.0
            if span_type in ["generate-response", "llm", "generation"]:
                cost = calculate_span_cost(model, prompt, completion)

            spans.append(
                SpanModel(
                    span_id=str(span.get("span_id", "unknown")),
                    type=span_type,
                    name=span_type,
                    latency_ms=latency,
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

        for span in raw.get("spans", []):
            if span.get("name") == "vector-search":
                documents = span.get("output", {}).get("documents", [])

                for doc in documents:
                    content = doc.get("content")
                    if content:
                        contexts.append(clean_text(content))

        return contexts