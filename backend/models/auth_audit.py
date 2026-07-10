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
    payload = {**data}
    payload.setdefault("created_at", datetime.utcnow().isoformat())

    # Map service-layer fields to SQLite schema if needed
    if "user_id" not in payload and "actor_user_id" in payload:
        payload["user_id"] = payload["actor_user_id"]
    if "username" not in payload and "actor_username" in payload:
        payload["username"] = payload["actor_username"]
    if "action" not in payload and "event_type" in payload:
        payload["action"] = payload["event_type"]

    if isinstance(payload.get("details_json"), dict):
        payload["details_json"] = json.dumps(payload["details_json"], ensure_ascii=False)
    return AuthAuditRepository.insert(payload)

