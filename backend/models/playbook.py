"""Playbook model and repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from ..config import TABLE_PLAYBOOK
from .report_cycle import get_cycle_window, parse_cycle_datetime
from .base import BaseRepository


class PlaybookRepository(BaseRepository):
    table = TABLE_PLAYBOOK
    columns = (
        "title",
        "origin",
        "source_type",
        "source_id",
        "source_key",
        "source_label",
        "area",
        "priority_score",
        "priority_level",
        "status",
        "summary",
        "content_json",
        "metrics_json",
        "created_at",
        "updated_at",
        "closed_at",
    )
    json_fields = ("content_json", "metrics_json")
    order_by = "created_at DESC"


def _within_cycle(row: Dict[str, Any], cycle_started_at: str | None, cycle_ended_at: str | None = None) -> bool:
    if not cycle_started_at:
        return False
    created_at = row.get("created_at") or row.get("updated_at")
    if not created_at:
        return False
    created_dt = parse_cycle_datetime(created_at)
    start_dt = parse_cycle_datetime(cycle_started_at)
    end_dt = parse_cycle_datetime(cycle_ended_at) if cycle_ended_at else None
    if created_dt < start_dt:
        return False
    if end_dt and created_dt >= end_dt:
        return False
    return True


def list_playbooks(cycle_id: int | None = None) -> List[Dict[str, Any]]:
    rows = PlaybookRepository.list()
    if cycle_id is None:
        return rows
    cycle_start, cycle_end = get_cycle_window(cycle_id)
    if cycle_start <= datetime.min:
        return []
    return [
        row
        for row in rows
        if _within_cycle(row, cycle_start.isoformat(), cycle_end.isoformat() if cycle_end else None)
    ]


def get_playbook(entity_id: int) -> Dict[str, Any] | None:
    return PlaybookRepository.get(entity_id)


def insert_playbook(data: Dict[str, Any]) -> int:
    payload = {**data}
    now = datetime.utcnow().isoformat()
    payload.setdefault("created_at", now)
    payload.setdefault("updated_at", now)
    payload.setdefault("status", "ativo")
    return PlaybookRepository.insert(payload)


def update_playbook(entity_id: int, data: Dict[str, Any]) -> bool:
    payload = {**data, "updated_at": datetime.utcnow().isoformat()}
    return PlaybookRepository.update(entity_id, payload)


def delete_playbook(entity_id: int) -> bool:
    return PlaybookRepository.delete(entity_id)
