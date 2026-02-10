from fastapi import APIRouter, HTTPException, Query

# ✅ Correct shared import (Key Vault already handled there)
from shared.cosmos import audit_container_read

router = APIRouter(prefix="/audit", tags=["Audit"])


# ---------------------------------------------------------
# GET AUDIT LOGS
# ---------------------------------------------------------
@router.get("")
def get_audit_logs(
    type: str | None = Query(None, description="Filter by type (evaluator, template)"),
    action: str | None = Query(None, description="Filter by action"),
    user: str | None = Query(None, description="Filter by user"),
    limit: int = Query(200, ge=1, le=1000),
):
    try:
        query = "SELECT * FROM c"
        filters = []
        params = []

        if type:
            filters.append("c.type = @type")
            params.append({"name": "@type", "value": type})

        if action:
            filters.append("c.action = @action")
            params.append({"name": "@action", "value": action})

        if user:
            filters.append("c.user = @user")
            params.append({"name": "@user", "value": user})

        if filters:
            query += " WHERE " + " AND ".join(filters)

        query += " ORDER BY c.timestamp DESC"

        items = list(
            audit_container_read.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True,
            )
        )

        # Limit after query (Cosmos ORDER BY + LIMIT is costly)
        return items[:limit]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
