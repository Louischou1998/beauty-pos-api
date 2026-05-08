import json
import logging
from datetime import datetime
from typing import Any


logger = logging.getLogger("beauty_pos.audit")


def audit_event(action: str, result: str = "success", **fields: Any) -> None:
    payload = {
        "ts": datetime.utcnow().isoformat(timespec="seconds"),
        "action": action,
        "result": result,
        **fields,
    }
    logger.info(json.dumps(payload, ensure_ascii=False, default=str))
