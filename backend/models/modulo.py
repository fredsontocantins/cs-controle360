"""Módulo model and repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from ..config import TABLE_MODULO
from .base import BaseRepository


class ModuloRepository(BaseRepository):
    """Repository for módulo records."""

    table = TABLE_MODULO
    columns = ("name", "description", "owner", "created_at")
    json_fields = ()
    order_by = "name"


def list_modulo() -> List[Dict[str, Any]]:
    return ModuloRepository.list()


def get_modulo(entity_id: int) -> Dict[str, Any] | None:
    return ModuloRepository.get(entity_id)


def insert_modulo(data: Dict[str, Any]) -> int:
    payload = {**data}
    payload.setdefault("created_at", datetime.utcnow().isoformat())
    return ModuloRepository.insert(payload)


def update_modulo(entity_id: int, data: Dict[str, Any]) -> bool:
    return ModuloRepository.update(entity_id, data)


def delete_modulo(entity_id: int) -> bool:
    return ModuloRepository.delete(entity_id)