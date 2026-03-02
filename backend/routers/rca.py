from fastapi import APIRouter, HTTPException
from shared.cosmos import rca_container_read as rca_container
router = APIRouter()


# -----------------------------
# GET /rca/{trace_id}
# -----------------------------
@router.get("/{trace_id}")
def get_rca(trace_id: str):
    try:
        items = list(
            rca_container.query_items(
                query="SELECT * FROM c WHERE c.trace_id=@tid",
                parameters=[{"name": "@tid", "value": trace_id}],
                enable_cross_partition_query=True,
            )
        )

        if not items:
            raise HTTPException(status_code=404, detail="RCA not found")

        return items[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
