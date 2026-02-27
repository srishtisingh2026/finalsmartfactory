from typing import Dict, Any, List
from ..schema import RetrievalInfo, SpanModel


class BaseProviderAdapter:

    def extract_usage(self, raw: Dict[str, Any]):
        return 0, 0, 0

    def extract_retrieval(self, raw: Dict[str, Any]) -> RetrievalInfo:
        return RetrievalInfo()

    def extract_spans(self, raw: Dict[str, Any]) -> List[SpanModel]:

        spans = []

        for span in raw.get("spans", []):
            spans.append(
                SpanModel(
                    span_id=str(span.get("span_id", "unknown")),
                    type=str(span.get("type", span.get("name", "unknown"))),
                    name=str(span.get("name", "unknown")),
                    latency_ms=int(span.get("latency_ms", 0) or 0),
                )
            )

        return spans