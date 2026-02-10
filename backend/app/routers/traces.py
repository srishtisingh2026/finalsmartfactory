import math
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query

# ✅ Correct shared import (read-only container)
from shared.cosmos import traces_container_read as traces_container

router = APIRouter()


# -----------------------------
# Helpers
# -----------------------------
def scrub(obj):
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: scrub(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub(i) for i in obj]
    return obj


# -----------------------------
# NORMALIZATION
# -----------------------------
def parse_timestamp(ts):
    if isinstance(ts, str):
        return ts
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    if isinstance(ts, datetime):
        return ts.astimezone(timezone.utc).isoformat()
    return None


def normalize_trace(t: dict) -> dict:
    return {
        "trace_id": t.get("trace_id") or t.get("id"),
        "session_id": t.get("session_id"),
        "user_id": t.get("user_id"),
        "trace_name": t.get("trace_name"),
        "input": t.get("input"),
        "output": t.get("output"),
        "timestamp": parse_timestamp(
            t.get("timestamp") or t.get("created_at") or t.get("_ts")
        ),
        "latency_ms": t.get("latency_ms") or t.get("latency") or 0,
        "tokens": t.get("tokens"),
        "tokens_in": t.get("tokens_in"),
        "tokens_out": t.get("tokens_out"),
        "cost": t.get("cost"),
        "model": t.get("model"),
    }


# -----------------------------
# Routes
# -----------------------------
@router.get("")
def get_all_traces(
    session_id: str | None = Query(None),
    user_id: str | None = Query(None),
    model: str | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
):
    try:
        query = "SELECT * FROM c"
        parameters = []
        filters = []

        if session_id:
            filters.append("c.session_id = @session_id")
            parameters.append({"name": "@session_id", "value": session_id})

        if user_id:
            filters.append("c.user_id = @user_id")
            parameters.append({"name": "@user_id", "value": user_id})

        if model:
            filters.append("c.model = @model")
            parameters.append({"name": "@model", "value": model})

        if filters:
            query += " WHERE " + " AND ".join(filters)

        # ✅ SAFE ORDER BY
        query += " ORDER BY c._ts DESC"

        raw = list(
            traces_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )

        normalized = [normalize_trace(t) for t in raw[:limit]]
        return scrub(normalized)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{trace_id}")
def get_trace(trace_id: str):
    try:
        query = "SELECT * FROM c WHERE c.trace_id = @trace_id"
        params = [{"name": "@trace_id", "value": trace_id}]

        items = list(
            traces_container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True,
            )
        )

        if not items:
            raise HTTPException(status_code=404, detail="Trace not found")

        return scrub(normalize_trace(items[0]))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
