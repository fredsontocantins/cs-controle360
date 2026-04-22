"""Catalogs for activity owners and statuses."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from ..config import TABLE_ACTIVITY_OWNER, TABLE_ACTIVITY_STATUS
from .base import BaseRepository


class ActivityOwnerRepository(BaseRepository):
    table = TABLE_ACTIVITY_OWNER
    columns = ("name", "sort_order", "is_active", "created_at")
    json_fields = ()
    order_by = "sort_order ASC, name ASC"


class ActivityStatusRepository(BaseRepository):
    table = TABLE_ACTIVITY_STATUS
    columns = ("key", "label", "hint", "sort_order", "is_active", "created_at")
    json_fields = ()
    order_by = "sort_order ASC, label ASC"


def list_activity_owners() -> List[Dict[str, Any]]:
    return [row for row in ActivityOwnerRepository.list() if row.get("is_active", 1)]


def list_activity_statuses() -> List[Dict[str, Any]]:
    return [row for row in ActivityStatusRepository.list() if row.get("is_active", 1)]


def insert_activity_owner(name: str, sort_order: int = 0, is_active: int = 1) -> int:
    return ActivityOwnerRepository.insert(
        {
            "name": name,
            "sort_order": sort_order,
            "is_active": is_active,
            "created_at": datetime.utcnow().isoformat(),
        }
    )


def insert_activity_status(key: str, label: str, hint: str = "", sort_order: int = 0, is_active: int = 1) -> int:
    return ActivityStatusRepository.insert(
        {
            "key": key,
            "label": label,
            "hint": hint,
            "sort_order": sort_order,
            "is_active": is_active,
            "created_at": datetime.utcnow().isoformat(),
        }
    )


def update_activity_owner(owner_id: int, data: Dict[str, Any]) -> bool:
    payload = {k: v for k, v in data.items() if v is not None}
    if not payload:
        return False
    return ActivityOwnerRepository.update(owner_id, payload)


def update_activity_status(status_id: int, data: Dict[str, Any]) -> bool:
    payload = {k: v for k, v in data.items() if v is not None}
    if not payload:
        return False
    return ActivityStatusRepository.update(status_id, payload)


def delete_activity_owner(owner_id: int) -> bool:
    return ActivityOwnerRepository.delete(owner_id)


def delete_activity_status(status_id: int) -> bool:
    return ActivityStatusRepository.delete(status_id)
