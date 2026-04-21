"""Cliente model and repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from ..config import TABLE_CLIENTE
from .base import BaseRepository


class ClienteRepository(BaseRepository):
    """Repository for cliente records."""

    table = TABLE_CLIENTE
    columns = ("name", "segment", "owner", "notes", "created_at")
    json_fields = ()
    order_by = "name"


def list_cliente() -> List[Dict[str, Any]]:
    return ClienteRepository.list()


def get_cliente(entity_id: int) -> Dict[str, Any] | None:
    return ClienteRepository.get(entity_id)


def insert_cliente(data: Dict[str, Any]) -> int:
    payload = {**data}
    payload.setdefault("created_at", datetime.utcnow().isoformat())
    return ClienteRepository.insert(payload)


def update_cliente(entity_id: int, data: Dict[str, Any]) -> bool:
    return ClienteRepository.update(entity_id, data)


def delete_cliente(entity_id: int) -> bool:
    return ClienteRepository.delete(entity_id)