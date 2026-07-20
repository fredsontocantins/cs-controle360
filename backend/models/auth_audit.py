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
        "actor_user_id",
        "actor_username",
        "target_user_id",
        "target_username",
        "event_type",
        "status",
        "provider",
        "message",
        "details_json",
        "created_at",
        "user_id",
        "username",
        "action",
        "ip_address",
        "user_agent",
    )
    json_fields = ("details_json",)
    order_by = "created_at DESC"


def list_auth_audit(limit: int = 100) -> List[Dict[str, Any]]:
    with AuthAuditRepository._connect() as conn:
        rows = run_query(conn,
            f"SELECT * FROM {AuthAuditRepository.table} ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    records: List[Dict[str, Any]] = []
    for row in rows:
        data = AuthAuditRepository._to_dict(row)
        if isinstance(data.get("details_json"), str):
            try:
                data["details"] = json.loads(data["details_json"])
            except json.JSONDecodeError:
                data["details"] = {}
        else:
            data["details"] = data.get("details_json") or {}

        # Mirror keys for compatibility
        data["actor_user_id"] = data.get("actor_user_id") or data.get("user_id")
        data["actor_username"] = data.get("actor_username") or data.get("username")
        data["event_type"] = data.get("event_type") or data.get("action")
        records.append(data)
    return records


def insert_auth_audit(data: Dict[str, Any]) -> int:
    payload = {**data}

    # Mirror keys to support both schemas simultaneously without any breaking changes!
    if "actor_user_id" in payload:
        payload["user_id"] = payload["actor_user_id"]
    if "user_id" in payload:
        payload["actor_user_id"] = payload["user_id"]

    if "actor_username" in payload:
        payload["username"] = payload["actor_username"]
    if "username" in payload:
        payload["actor_username"] = payload["username"]

    if "event_type" in payload:
        payload["action"] = payload["event_type"]
    if "action" in payload:
        payload["event_type"] = payload["action"]

    payload.setdefault("action", "unknown_action")
    payload.setdefault("event_type", "unknown_action")
    payload.setdefault("created_at", datetime.utcnow().isoformat())

    if isinstance(payload.get("details_json"), dict):
        payload["details_json"] = json.dumps(payload["details_json"], ensure_ascii=False)
    return AuthAuditRepository.insert(payload)

