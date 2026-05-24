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
    if isinstance(payload.get("details_json"), dict):
        payload["details_json"] = json.dumps(payload["details_json"], ensure_ascii=False)
    return AuthAuditRepository.insert(payload)

