import math
import re
from datetime import datetime
from fastapi import APIRouter, HTTPException
from azure.cosmos.exceptions import CosmosResourceExistsError

# ✅ Correct shared imports (Key Vault handled internally)
from shared.cosmos import (
    templates_container,          # WRITE
    templates_container_read,     # READ
)
from shared.audit import audit_log

router = APIRouter()


# -----------------------------------------
# Helpers
# -----------------------------------------
def scrub(obj):
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: scrub(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub(i) for i in obj]
    return obj


def make_template_id(name: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_")


# ---------------------------------------------------------
# GET ALL TEMPLATES
# ---------------------------------------------------------
@router.get("")
def get_templates():
    try:
        items = list(
            templates_container_read.query_items(
                query="SELECT * FROM c",
                enable_cross_partition_query=True,
            )
        )

        templates = [
            {
                "template_id": t.get("template_id", t.get("id")),
                "name": t.get("name"),
                "version": t.get("version"),
                "description": t.get("description"),
                "model": t.get("model"),
                "inputs": t.get("inputs", []),
                "template": t.get("template"),
                "updated_at": t.get("updated_at"),
            }
            for t in items
        ]

        templates.sort(key=lambda x: (x["name"] or "").lower())
        return scrub({"templates": templates})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# GET TEMPLATE BY ID
# ---------------------------------------------------------
@router.get("/{template_id}")
def get_template(template_id: str):
    try:
        items = list(
            templates_container_read.query_items(
                query="SELECT * FROM c WHERE c.template_id=@id",
                parameters=[{"name": "@id", "value": template_id}],
                enable_cross_partition_query=True,
            )
        )

        if not items:
            raise HTTPException(status_code=404, detail="Template not found")

        return scrub(items[0])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# CREATE TEMPLATE
# ---------------------------------------------------------
@router.post("")
def create_template(payload: dict):
    try:
        name = payload.get("name")
        model = payload.get("model")
        template_text = payload.get("template")

        if not name:
            raise HTTPException(400, "name is required")
        if not model:
            raise HTTPException(400, "model is required")
        if not template_text:
            raise HTTPException(400, "template is required")

        template_id = payload.get("template_id") or make_template_id(name)

        doc = {
            "id": template_id,
            "template_id": template_id,
            "name": name,
            "version": payload.get("version", "1"),
            "description": payload.get("description", ""),
            "model": model,
            "inputs": payload.get("inputs", []),
            "template": template_text,
            "updated_at": datetime.utcnow().isoformat(),
        }

        # ✅ CREATE TEMPLATE (WRITE container)
        templates_container.create_item(doc)

        # ✅ AUDIT LOG (AFTER SUCCESS)
        audit_log(
            action="Template Created",
            type="template",
            user="system",  # replace later with real user
            details=f"Created template '{name}' (v{doc['version']})",
        )

        return {"status": "ok", "template": scrub(doc)}

    except CosmosResourceExistsError:
        raise HTTPException(
            status_code=409,
            detail="Template with this name already exists",
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
