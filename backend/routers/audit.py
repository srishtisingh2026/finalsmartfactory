from fastapi import APIRouter, HTTPException, Query
from shared.cosmos import audit_container_read

router = APIRouter(prefix="/audit", tags=["Audit"])


# ---------------------------------------------------------
# GET AUDIT LOGS
# ---------------------------------------------------------
@router.get("")
def get_audit_logs(
    type: str | None = Query(None, description="Filter by type (evaluator, template, rca, etc.)"),
    action: str | None = Query(None, description="Filter by action"),
    user: str | None = Query(None, description="Filter by user"),
    search: str | None = Query(None, description="Search in details"),
    limit: int = Query(200, ge=1, le=1000),
):
    try:
        query = "SELECT * FROM c"
        filters = []
        params = []

        # ---- Dynamic Filters ----
        if type:
            filters.append("c.type = @type")
            params.append({"name": "@type", "value": type})

        if action:
            filters.append("c.action = @action")
            params.append({"name": "@action", "value": action})

        if user:
            filters.append("c.user = @user")
            params.append({"name": "@user", "value": user})

        if search:
            filters.append("CONTAINS(c.details, @search, true)")
            params.append({"name": "@search", "value": search})

        if filters:
            query += " WHERE " + " AND ".join(filters)

        # ISO timestamps sort correctly lexicographically
        query += " ORDER BY c.timestamp DESC"

        items = list(
            audit_container_read.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True,
            )
        )

        return items[:limit]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))