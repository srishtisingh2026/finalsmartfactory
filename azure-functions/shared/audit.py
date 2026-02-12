from datetime import datetime, timezone
import uuid
import logging
from shared.cosmos import audit_container

def audit_log(action: str, type: str, user: str, details: str):
    try:
        audit_container.create_item({
            "id": f"audit_{uuid.uuid4().hex}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "type": type,      # evaluator | template
            "user": user,      # email or "system"
            "details": details,
        })
    except Exception:
        # 🚨 audit must NEVER break the main flow
        logging.exception("Audit log write failed")
