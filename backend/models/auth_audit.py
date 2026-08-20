"""Authentication audit log repository."""

from __future__ import annotations
from ..database import run_query

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import TABLE_AUTH_AUDIT
from .base import BaseRepository


class AuthAuditRepository(BaseRepository):
    table = TABLE_AUTH_AUDIT
    columns = (
        "user_id",
        "username",
        "action",
        "message",
        "ip_address",
        "user_agent",
        "status",
        "created_at",
    )
    json_fields = ()
    order_by = "created_at DESC"


def list_auth_audit(limit: int = 100) -> List[Dict[str, Any]]:
    with AuthAuditRepository._connect() as conn:
        rows = run_query(conn,
            f"SELECT * FROM {AuthAuditRepository.table} ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [AuthAuditRepository._to_dict(row) for row in rows]


def insert_auth_audit(data: Dict[str, Any]) -> int:
    payload = {**data}
    if "actor_user_id" in payload and "user_id" not in payload:
        payload["user_id"] = payload.pop("actor_user_id")
    if "actor_username" in payload and "username" not in payload:
        payload["username"] = payload.pop("actor_username")
    if "event_type" in payload and "action" not in payload:
        payload["action"] = payload.pop("event_type")
    payload.setdefault("action", "AUTH_EVENT")
    payload.setdefault("created_at", datetime.utcnow().isoformat())
    return AuthAuditRepository.insert(payload)

