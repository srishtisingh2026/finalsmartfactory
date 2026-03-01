import math
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query

# ✅ Read-only containers
from shared.cosmos import traces_read as traces_container
from shared.cosmos import evaluations_read as evaluations_container

router = APIRouter()


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def scrub(obj):
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: scrub(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub(i) for i in obj]
    return obj


def parse_timestamp(ts):
    if isinstance(ts, str):
        return ts
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts, tz=timezone.utc).isoformat()
    if isinstance(ts, datetime):
        return ts.astimezone(timezone.utc).isoformat()
    return None


def normalize_trace(t: dict) -> dict:
    session = t.get("session", {}) or {}
    request = t.get("request", {}) or {}
    model_info = t.get("model_info", {}) or {}
    performance = t.get("performance", {}) or {}
    usage = t.get("usage", {}) or {}
    cost = t.get("cost", {}) or {}

    return {
        "trace_id": t.get("trace_id") or t.get("id"),
        "trace_name": t.get("trace_name"),

        # Session Info
        "session_id": session.get("session_id"),
        "user_id": session.get("user_id"),

        # Input / Output
        "input": t.get("input_text"),
        "output": t.get("output_text"),

        # Request metadata
        "environment": request.get("environment"),
        "intent": request.get("intent"),
        "timestamp": parse_timestamp(request.get("timestamp") or t.get("_ts")),

        # Model info
        "provider": model_info.get("provider"),
        "model": model_info.get("model"),
        "temperature": model_info.get("temperature"),

        # Performance
        "latency_ms": performance.get("latency_ms"),
        "status": performance.get("status"),

        # Usage
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),

        # Cost
        "input_cost_usd": cost.get("input_cost_usd"),
        "output_cost_usd": cost.get("output_cost_usd"),
        "total_cost_usd": cost.get("total_cost_usd"),
        "currency": cost.get("currency"),

        # Retrieval
        "retrieval": t.get("retrieval"),
    }


# --------------------------------------------------
# Routes
# --------------------------------------------------

@router.get("")
def get_all_traces(
    session_id: str | None = Query(None),
    user_id: str | None = Query(None),
    model: str | None = Query(None),
    provider: str | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
):
    try:
        query = "SELECT * FROM c"
        parameters = []
        filters = []

        if session_id:
            filters.append("c.session.session_id = @session_id")
            parameters.append({"name": "@session_id", "value": session_id})

        if user_id:
            filters.append("c.session.user_id = @user_id")
            parameters.append({"name": "@user_id", "value": user_id})

        if model:
            filters.append("c.model_info.model = @model")
            parameters.append({"name": "@model", "value": model})

        if provider:
            filters.append("c.model_info.provider = @provider")
            parameters.append({"name": "@provider", "value": provider})

        if filters:
            query += " WHERE " + " AND ".join(filters)

        query += " ORDER BY c._ts DESC"

        raw_traces = list(
            traces_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )[:limit]

        # Fetch evaluations once
        evaluations = list(
            evaluations_container.query_items(
                query="SELECT c.trace_id, c.evaluator, c.score FROM c",
                enable_cross_partition_query=True,
            )
        )

        scores_map = {}
        for e in evaluations:
            trace_id = e.get("trace_id")
            if not trace_id:
                continue

            if trace_id not in scores_map:
                scores_map[trace_id] = {}

            scores_map[trace_id][e.get("evaluator")] = e.get("score")

        enriched_traces = []

        for t in raw_traces:
            normalized = normalize_trace(t)
            normalized["scores"] = scores_map.get(normalized["trace_id"], {})
            enriched_traces.append(normalized)

        return scrub(enriched_traces)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{trace_id}")
def get_trace(trace_id: str):
    try:
        trace_items = list(
            traces_container.query_items(
                query="SELECT * FROM c WHERE c.trace_id = @trace_id",
                parameters=[{"name": "@trace_id", "value": trace_id}],
                enable_cross_partition_query=True,
            )
        )

        if not trace_items:
            raise HTTPException(status_code=404, detail="Trace not found")

        normalized = normalize_trace(trace_items[0])

        eval_items = list(
            evaluations_container.query_items(
                query="SELECT c.evaluator, c.score FROM c WHERE c.trace_id = @trace_id",
                parameters=[{"name": "@trace_id", "value": trace_id}],
                enable_cross_partition_query=True,
            )
        )

        scores = {}
        for e in eval_items:
            scores[e.get("evaluator")] = e.get("score")

        normalized["scores"] = scores

        return scrub(normalized)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))