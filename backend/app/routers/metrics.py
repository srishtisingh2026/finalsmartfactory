import math
from fastapi import APIRouter, HTTPException

# ✅ Correct shared import (Key Vault handled internally)
from shared.cosmos import metrics_container_read as metrics_container

router = APIRouter()

METRICS_ID = "metrics_snapshot"
METRICS_PK = "metrics_snapshot"


# -----------------------------
# Helpers
# -----------------------------
def scrub(obj):
    """Replace NaN / Infinity with None so FastAPI can serialize safely."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: scrub(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub(i) for i in obj]
    return obj


def strip_cosmos_metadata(doc: dict):
    """Remove Cosmos internal fields before returning to UI."""
    return {k: v for k, v in doc.items() if not k.startswith("_")}


# -----------------------------
# Routes
# -----------------------------
@router.get("/metrics")
def get_metrics():
    """
    Dashboard metrics (read-only snapshot from Cosmos DB)
    """
    try:
        # 🚀 Single point read — no query, super fast
        snapshot = metrics_container.read_item(
            item=METRICS_ID,
            partition_key=METRICS_PK,
        )

        return scrub(strip_cosmos_metadata(snapshot))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
