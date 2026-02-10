import math
from collections import defaultdict
from fastapi import APIRouter, HTTPException

# ✅ Correct shared import (read-only container)
from shared.cosmos import traces_container_read as traces_container

router = APIRouter()


# -----------------------------
# Helpers
# -----------------------------
def scrub(obj):
    """
    Replace NaN / Infinity with None so FastAPI can serialize safely.
    """
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: scrub(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub(i) for i in obj]
    return obj


# -----------------------------
# Routes
# -----------------------------

@router.get("")
def list_sessions():
    try:
        # 🔥 Query ALL traces (read-only)
        traces = list(
            traces_container.query_items(
                query="SELECT * FROM c",
                enable_cross_partition_query=True,
            )
        )

        if not traces:
            return []

        sessions = defaultdict(
            lambda: {
                "session_id": None,
                "user_id": "unknown",
                "trace_count": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "created": None,
            }
        )

        for t in traces:
            session_id = t.get("session_id")
            if not session_id:
                continue

            s = sessions[session_id]
            s["session_id"] = session_id
            s["user_id"] = t.get("user_id", "unknown")
            s["trace_count"] += 1
            s["total_tokens"] += t.get("tokens", 0)
            s["total_cost"] += t.get("cost", 0.0)

            ts = t.get("timestamp")
            if ts and (s["created"] is None or ts < s["created"]):
                s["created"] = ts

        return scrub(list(sessions.values()))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}")
def get_session(session_id: str):
    try:
        # 🔥 Query all traces of a specific session (read-only)
        traces = list(
            traces_container.query_items(
                query="SELECT * FROM c WHERE c.session_id=@sid",
                parameters=[{"name": "@sid", "value": session_id}],
                enable_cross_partition_query=True,
            )
        )

        if not traces:
            raise HTTPException(status_code=404, detail="Session not found")

        session = {
            "session_id": session_id,
            "user_id": traces[0].get("user_id", "unknown"),
            "trace_count": len(traces),
            "total_tokens": sum(t.get("tokens", 0) for t in traces),
            "total_cost": sum(t.get("cost", 0.0) for t in traces),
            "created": min(
                t["timestamp"] for t in traces if t.get("timestamp")
            ),
            "traces": traces,
        }

        return scrub(session)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
