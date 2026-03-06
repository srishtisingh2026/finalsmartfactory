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

        rag = raw.get("rag_data", {}) or {}
        scores = rag.get("retrieval_scores", {}) or {}

        confidence = raw.get("retrieval_confidence")

        # ------------------------------------------------
        # Ensure confidence is always a float
        # ------------------------------------------------
        if isinstance(confidence, dict):
            confidence = confidence.get("avg_score")

        if confidence is None:
            confidence = scores.get("avg_score")

        if confidence is not None:
            confidence = float(confidence)

        # ------------------------------------------------
        # Documents found
        # ------------------------------------------------
        documents_found = raw.get("documents_found")

        if documents_found is None:
            documents_found = rag.get("documents_found")

        # fallback to span inspection
        if documents_found is None:

            for span in raw.get("spans", []):

                if span.get("type") == "retrieval" or span.get("name") == "vector-search":

                    docs = span.get("output", {}).get("documents", []) or []

                    documents_found = len(docs)
                    break

        documents_found = int(documents_found or 0)

        # ------------------------------------------------
        # Best score (cosine similarity = higher is better)
        # ------------------------------------------------
        best_score = scores.get("max_score")

        if best_score is not None:
            best_score = float(best_score)

        return RetrievalInfo(
            executed=bool(raw.get("retrieval_executed", documents_found > 0)),
            documents_found=documents_found,
            retrieval_confidence=confidence,
            best_score=best_score,
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
                type=span_type,
                name=span_name,
                latency_ms=latency,
                prompt_tokens=prompt,
                completion_tokens=completion,
                total_tokens=total,
                cost_usd=cost,
            )

            # Only for LLM spans (same behaviour as Groq)
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
    # RETRIEVED DOCUMENT CONTENT
    # ============================================================

    def extract_retrieved_context(self, raw: Dict[str, Any]):

        contexts: List[str] = []

        # Prefer canonical rag_data
        rag_data = raw.get("rag_data", {}) or {}

        docs = rag_data.get("retrieved_documents", []) or []

        for doc in docs:

            content = doc.get("content") or doc.get("content_preview")

            if content:
                contexts.append(clean_text(content))

        # fallback to span extraction
        if not contexts:

            for span in raw.get("spans", []):

                if span.get("type") == "retrieval" or span.get("name") == "vector-search":

                    documents = span.get("output", {}).get("documents", []) or []

                    for doc in documents:

                        content = doc.get("content")

                        if content:
                            contexts.append(clean_text(content))

        return contexts