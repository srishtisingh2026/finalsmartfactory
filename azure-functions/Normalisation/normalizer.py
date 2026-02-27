from typing import Dict, Any

from .schema import (
    CanonicalTrace,
    SessionInfo,
    RequestInfo,
    ModelInfo,
    PerformanceInfo,
    UsageInfo,
)

from .pricing import calculate_cost
from .utils import (
    detect_provider,
    normalize_timestamp,
    extract_input,
    extract_output,
)

from .adapters.factory import get_adapter


# ============================================================
# MAIN NORMALIZER
# ============================================================

def normalize_trace(raw: Dict[str, Any]) -> CanonicalTrace:
    """
    Convert raw provider trace into CanonicalTrace format.
    Provider-specific logic is delegated to adapters.
    """

    # --------------------------------------------------------
    # Provider detection + adapter selection
    # --------------------------------------------------------
    provider = detect_provider(raw)
    adapter = get_adapter(provider)

    # --------------------------------------------------------
    # Basic fields
    # --------------------------------------------------------
    trace_id = raw.get("trace_id") or raw.get("id")

    timestamp = normalize_timestamp(raw.get("timestamp"))

    latency = raw.get("latency_ms", 0)
    if isinstance(latency, float):
        latency = int(latency)
    latency = int(latency or 0)

    status = raw.get("status", "success")
    if status not in ["success", "failure"]:
        status = "success"

    # --------------------------------------------------------
    # Usage extraction (provider-specific)
    # --------------------------------------------------------
    prompt_tokens, completion_tokens, total_tokens = (
        adapter.extract_usage(raw)
    )

    # --------------------------------------------------------
    # Cost calculation
    # --------------------------------------------------------
    cost = calculate_cost(
        raw.get("model"),
        prompt_tokens,
        completion_tokens,
    )

    # --------------------------------------------------------
    # Retrieval metadata + retrieved documents
    # --------------------------------------------------------
    retrieval = adapter.extract_retrieval(raw)
    retrieved_context = adapter.extract_retrieved_context(raw)

    # --------------------------------------------------------
    # Span extraction
    # --------------------------------------------------------
    spans = adapter.extract_spans(raw)

    # --------------------------------------------------------
    # Construct CanonicalTrace
    # --------------------------------------------------------
    return CanonicalTrace(
        id=str(trace_id),
        trace_id=str(trace_id),
        trace_name=str(raw.get("trace_name", "unknown")),

        input_text=extract_input(raw),
        output_text=extract_output(raw),
        retrieved_context=retrieved_context,

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
            latency_ms=latency,
            status=status,
        ),

        usage=UsageInfo(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        ),

        cost=cost,
        retrieval=retrieval,
        spans=spans,
    )