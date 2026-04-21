"""Service for audit logging mutations made through the web UI / API."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import Request

from cs_web import db

AUDIT_LABELS: Dict[str, str] = {
    "homologation": "Homologação",
    "customization": "Customização",
    "release": "Release",
    "module": "Módulo",
    "client": "Cliente",
}


def record_audit(
    request: Request | None,
    user: Dict[str, Any] | None,
    action: str,
    entity_type: str,
    entity_id: int | None,
    before: Dict[str, Any] | None = None,
    after: Dict[str, Any] | None = None,
) -> None:
    """Best-effort audit log recorder. Never raises."""
    try:
        db.audit_log.insert(
            {
                "user_id": (user or {}).get("id"),
                "username": (user or {}).get("username"),
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "before": before,
                "after": after,
                "path": str(request.url.path) if request else None,
                "ip": request.client.host if request and request.client else None,
            }
        )
    except Exception:
        pass


def audit_insert(
    request: Request | None,
    user: Dict[str, Any] | None,
    entity_type: str,
    repo: Any,
    payload: Dict[str, Any],
) -> int:
    entity_id = repo.insert(payload)
    record_audit(
        request, user, "create", entity_type, entity_id,
        before=None, after=repo.get(entity_id),
    )
    return entity_id


def audit_update(
    request: Request | None,
    user: Dict[str, Any] | None,
    entity_type: str,
    repo: Any,
    entity_id: int,
    payload: Dict[str, Any],
) -> bool:
    before = repo.get(entity_id)
    updated = repo.update(entity_id, payload)
    if updated:
        record_audit(
            request, user, "update", entity_type, entity_id,
            before=before, after=repo.get(entity_id),
        )
    return updated


def audit_delete(
    request: Request | None,
    user: Dict[str, Any] | None,
    entity_type: str,
    repo: Any,
    entity_id: int,
) -> bool:
    before = repo.get(entity_id)
    deleted = repo.delete(entity_id)
    if deleted:
        record_audit(
            request, user, "delete", entity_type, entity_id,
            before=before, after=None,
        )
    return deleted
