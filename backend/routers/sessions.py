import math
from datetime import datetime, timezone
from collections import defaultdict
from fastapi import APIRouter, HTTPException
from shared.cosmos import traces_container_read as traces_container

SESSION_IDLE_TIMEOUT = 5 * 60  # 5 minutes
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


def safe_round(value: float, decimals: int = 6):
    return round(float(value), decimals)


def normalize_ts(ts):
    """Normalize Cosmos timestamps (ms or sec) → seconds."""
    if ts is None:
        return None
    if ts > 1e12:  # ms
        return ts / 1000
    return ts


def ts_to_iso(ts):
    """Convert seconds timestamp → ISO."""
    if ts is None:
        return None
    return datetime.utcfromtimestamp(ts).isoformat() + "Z"


# -----------------------------
# GET /sessions
# -----------------------------
@router.get("")
def list_sessions():
    try:
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
                "environment": None,
                "trace_count": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "total_cost_micro_usd": 0,
                "avg_latency_ms": 0.0,
                "created": None,
                "last_activity": None,
            }
        )

        # Aggregate sessions
        for t in traces:
            session_obj = t.get("session", {})
            request_obj = t.get("request", {})
            usage_obj = t.get("usage", {})
            cost_obj = t.get("cost", {})
            perf_obj = t.get("performance", {})

            session_id = session_obj.get("session_id")
            if not session_id:
                continue

            s = sessions[session_id]

            s["session_id"] = session_id
            s["user_id"] = session_obj.get("user_id", "unknown")
            s["environment"] = request_obj.get("environment")

            s["trace_count"] += 1
            s["total_tokens"] += usage_obj.get("total_tokens", 0)

            cost_usd = cost_obj.get("total_cost_usd", 0.0)
            s["total_cost_usd"] += cost_usd
            s["total_cost_micro_usd"] += int(cost_usd * 1_000_000)

            s["avg_latency_ms"] += perf_obj.get("latency_ms", 0)

            ts = normalize_ts(request_obj.get("timestamp"))
            if ts:
                if s["created"] is None or ts < s["created"]:
                    s["created"] = ts
                if s["last_activity"] is None or ts > s["last_activity"]:
                    s["last_activity"] = ts

        now_sec = datetime.now(timezone.utc).timestamp()

        # Compute final values
        for s in sessions.values():
            if s["trace_count"] > 0:
                s["avg_latency_ms"] = safe_round(s["avg_latency_ms"] / s["trace_count"], 2)

            s["total_cost_usd"] = safe_round(s["total_cost_usd"], 6)

            # Active session logic: use NOW if session still active
            last = s["last_activity"]
            created = s["created"]

            if last and (now_sec - last <= SESSION_IDLE_TIMEOUT):
                effective_end = now_sec
            else:
                effective_end = last

            s["session_start"] = ts_to_iso(created)
            s["session_end"] = ts_to_iso(effective_end)

            if created and effective_end:
                s["session_duration_ms"] = int((effective_end - created) * 1000)
            else:
                s["session_duration_ms"] = None

        return scrub(list(sessions.values()))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# GET /sessions/{session_id}
# -----------------------------
@router.get("/{session_id}")
def get_session(session_id: str):
    try:
        traces = list(
            traces_container.query_items(
                query="SELECT * FROM c WHERE c.session.session_id=@sid",
                parameters=[{"name": "@sid", "value": session_id}],
                enable_cross_partition_query=True,
            )
        )

        if not traces:
            raise HTTPException(status_code=404, detail="Session not found")

        session_obj = traces[0].get("session", {})
        request_obj = traces[0].get("request", {})

        total_cost_usd = sum(t.get("cost", {}).get("total_cost_usd", 0.0) for t in traces)

        # Normalize timestamps
        timestamps = [normalize_ts(t.get("request", {}).get("timestamp")) for t in traces]
        timestamps = [ts for ts in timestamps if ts]

        created = min(timestamps)
        last_activity = max(timestamps)

        now_sec = datetime.now(timezone.utc).timestamp()

        # Active session?
        if now_sec - last_activity <= SESSION_IDLE_TIMEOUT:
            effective_end = now_sec
        else:
            effective_end = last_activity

        session = {
            "session_id": session_id,
            "user_id": session_obj.get("user_id", "unknown"),
            "environment": request_obj.get("environment"),
            "trace_count": len(traces),
            "total_tokens": sum(t.get("usage", {}).get("total_tokens", 0) for t in traces),
            "total_cost_usd": safe_round(total_cost_usd, 6),
            "total_cost_micro_usd": int(total_cost_usd * 1_000_000),
            "avg_latency_ms": safe_round(
                sum(t.get("performance", {}).get("latency_ms", 0) for t in traces) / len(traces),
                2,
            ),
            "created": created,
            "last_activity": last_activity,
            "session_start": ts_to_iso(created),
            "session_end": ts_to_iso(effective_end),
            "session_duration_ms": int((effective_end - created) * 1000),
            "traces": traces,
        }

        return scrub(session)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))