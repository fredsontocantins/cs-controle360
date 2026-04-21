"""Playbook model and repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from ..config import TABLE_PLAYBOOK
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


def list_playbooks() -> List[Dict[str, Any]]:
    return PlaybookRepository.list()


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

