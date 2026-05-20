from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def build_audit_event(
    actor_id: str,
    actor_role: str,
    action: str,
    object_type: str,
    object_id: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "event_id": str(uuid4()),
        "actor_id": actor_id,
        "actor_role": actor_role,
        "action": action,
        "object_type": object_type,
        "object_id": object_id,
        "details": details or {},
        "created_at": datetime.now(UTC).isoformat(),
    }