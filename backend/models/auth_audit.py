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
        "actor_user_id",
        "actor_username",
        "target_user_id",
        "target_username",
        "event_type",
        "provider",
        "details_json",
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
        records.append(data)
    return records


def insert_auth_audit(data: Dict[str, Any]) -> int:
    # Service layer sends (actor_user_id, actor_username, event_type)
    # Target schema and SQLite may have different naming conventions
    payload = {
        "actor_user_id": data.get("actor_user_id") or data.get("user_id"),
        "actor_username": data.get("actor_username") or data.get("username"),
        "event_type": data.get("event_type") or data.get("action") or "unknown",
        "message": data.get("message"),
        "ip_address": data.get("ip_address"),
        "user_agent": data.get("user_agent"),
        "status": data.get("status"),
        "details_json": data.get("details_json"),
        "provider": data.get("provider"),
        "target_user_id": data.get("target_user_id"),
        "target_username": data.get("target_username"),
    }

    # Force legacy column names to be populated for the SQLite BaseRepository.insert
    payload["user_id"] = payload["actor_user_id"]
    payload["username"] = payload["actor_username"]
    payload["action"] = payload["event_type"]

    # BaseRepository.insert only uses keys present in AuthAuditRepository.columns
    # and the provided data dict.
    payload.setdefault("created_at", datetime.utcnow().isoformat())
    if isinstance(payload.get("details_json"), dict):
        payload["details_json"] = json.dumps(payload["details_json"], ensure_ascii=False)
    return AuthAuditRepository.insert(payload)

