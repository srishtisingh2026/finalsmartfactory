from datetime import datetime
from fastapi import APIRouter, HTTPException
from azure.cosmos.exceptions import CosmosResourceExistsError

from backend.shared.cosmos import evaluators_container
from backend.shared.audit import audit_log

router = APIRouter()


# ---------------------------------------------------------
# GET ALL EVALUATORS
# ---------------------------------------------------------
@router.get("")
def get_evaluators():
    try:
        items = list(
            evaluators_container.query_items(
                query="SELECT * FROM c ORDER BY c.created_at DESC",
                enable_cross_partition_query=True,
            )
        )
        return {"evaluators": items}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# CREATE EVALUATOR
# ---------------------------------------------------------
@router.post("")
def create_evaluator(payload: dict):
    try:
        name = payload.get("score_name")
        template = payload.get("template")
        target = payload.get("target", "trace")

        # 🔥 **status defaults to active**
        status = payload.get("status", "active")

        if status not in {"active", "inactive"}:
            raise HTTPException(400, "status must be 'active' or 'inactive'")

        execution = payload.get("execution", {})

        if not name:
            raise HTTPException(400, "score_name is required")
        if not template or not template.get("id"):
            raise HTTPException(400, "template.id is required")

        evaluator_id = payload.get("id") or name.lower().replace(" ", "_")

        doc = {
            "id": evaluator_id,
            "score_name": name,
            "template": template,
            "target": target,
            "status": status,   # 🔥 only active/inactive
            "execution": execution,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Save evaluator
        evaluators_container.create_item(doc)

        # Audit
        audit_log(
            action="Evaluator Created",
            type="evaluator",
            user="system",
            details=f"Created evaluator '{name}' using template '{template.get('id')}'",
        )

        return {"status": "ok", "evaluator": doc}

    except CosmosResourceExistsError:
        raise HTTPException(
            status_code=409,
            detail="Evaluator with this name already exists",
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

