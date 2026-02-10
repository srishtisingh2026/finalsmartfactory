import math
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query

# ✅ Correct shared import (Key Vault handled inside shared.cosmos)
from shared.cosmos import evaluations_container_read as evaluations_container

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
ALLOWED_STATUS = {"Completed", "Error", "Timeout"}


def parse_timestamp(ts):
    if isinstance(ts, str):
        return ts
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    if isinstance(ts, datetime):
        return ts.astimezone(timezone.utc).isoformat()
    return None


def compute_duration(e: dict):
    for key in ("duration_ms", "duration", "latency_ms", "eval_latency"):
        if isinstance(e.get(key), (int, float)):
            return int(e[key])

    try:
        if e.get("start_time") and e.get("end_time"):
            start = datetime.fromisoformat(e["start_time"])
            end = datetime.fromisoformat(e["end_time"])
            return int((end - start).total_seconds() * 1000)
    except Exception:
        pass

    return 0


def normalize_status(e: dict, score):
    raw = e.get("status")
    if raw in ALLOWED_STATUS:
        return raw

    if isinstance(raw, str):
        rl = raw.lower()
        if "timeout" in rl:
            return "Timeout"
        if "error" in rl or "fail" in rl:
            return "Error"

    return "Completed" if score is not None else "Error"


def normalize_eval(e: dict) -> dict:
    score = e.get("score")

    return {
        "evaluator_name": e.get("evaluator_name"),
        "trace_id": e.get("trace_id"),
        "score": score,
        "timestamp": parse_timestamp(
            e.get("timestamp") or e.get("created_at") or e.get("_ts")
        ),
        "duration_ms": compute_duration(e),
        "status": normalize_status(e, score),
    }


# -----------------------------
# Routes
# -----------------------------
@router.get("")
def get_all_evaluations(
    evaluator: str | None = Query(None),
    trace_id: str | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
):
    try:
        query = "SELECT * FROM c"
        parameters = []
        filters = []

        if evaluator:
            filters.append("c.evaluator_name = @evaluator")
            parameters.append({"name": "@evaluator", "value": evaluator})

        if trace_id:
            filters.append("c.trace_id = @trace_id")
            parameters.append({"name": "@trace_id", "value": trace_id})

        if filters:
            query += " WHERE " + " AND ".join(filters)

        # ✅ SAFE ORDER BY (always exists)
        query += " ORDER BY c._ts DESC"

        raw = list(
            evaluations_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )

        normalized = [normalize_eval(e) for e in raw[:limit]]
        return scrub(normalized)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
