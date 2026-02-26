from datetime import datetime
from fastapi import APIRouter, HTTPException
from azure.cosmos.exceptions import CosmosResourceExistsError

from shared.cosmos import evaluators_container
from shared.audit import audit_log

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
        name = payload.get("name")
        template = payload.get("template")
        target = payload.get("target", "trace")
        status = payload.get("status", "active")
        execution = payload.get("execution", {})

        variable_mapping = payload.get("variable_mapping", {})

        # ---------------------------
        # Basic validation
        # ---------------------------
        if not name:
            raise HTTPException(400, "name is required")

        if status not in {"active", "inactive"}:
            raise HTTPException(400, "status must be 'active' or 'inactive'")

        # ---------------------------
        # Auto-generate score_name
        # ---------------------------
        score_name = payload.get("score_name") or name.lower().replace(" ", "_")

        # ---------------------------
        # Normalize template format
        # ---------------------------
        if isinstance(template, str):
            template = {"id": template}

        if not template or not template.get("id"):
            raise HTTPException(400, "template.id is required")

        # ---------------------------
        # Versioned ID
        # ---------------------------
        evaluator_id = payload.get("id") or f"{score_name}-v1"

        # ---------------------------
        # CREATE DOCUMENT
        # ---------------------------
        doc = {
            "id": evaluator_id,
            "name": name,
            "score_name": score_name,
            "template": template,
            "target": target,
            "status": status,

            # 🔥 SAVE VARIABLE MAPPING (FIX)
            "variable_mapping": variable_mapping,

            "execution": execution,
            "created_at": datetime.utcnow().isoformat(),
        }

        evaluators_container.create_item(doc)

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
            detail="Evaluator with this id already exists",
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
