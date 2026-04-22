"""Customização model and repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from ..config import TABLE_CUSTOMIZACAO
from .report_cycle import get_active_cycle_started_at, parse_cycle_datetime
from .base import BaseRepository


class CustomizacaoRepository(BaseRepository):
    """Repository for customização records."""

    table = TABLE_CUSTOMIZACAO
    columns = (
        "stage", "proposal", "subject", "client", "module", "module_id",
        "owner", "received_at", "status", "pf", "value", "observations",
        "pdf_path", "client_id", "created_at"
    )
    json_fields = ()
    order_by = "id DESC"


# Convenience functions for backwards compatibility
def _within_current_cycle(row: Dict[str, Any], cycle_started_at: str | None) -> bool:
    if not cycle_started_at:
        return False
    cycle_start = parse_cycle_datetime(cycle_started_at)
    if cycle_start <= datetime.min:
        return False
    candidate = row.get("received_at") or row.get("created_at")
    return parse_cycle_datetime(candidate) >= cycle_start


def list_customizacao(include_history: bool = False) -> List[Dict[str, Any]]:
    rows = CustomizacaoRepository.list()
    if include_history:
        return rows
    cycle_started_at = get_active_cycle_started_at("reports")
    if not cycle_started_at:
        return []
    return [row for row in rows if _within_current_cycle(row, cycle_started_at)]


def get_customizacao(entity_id: int) -> Dict[str, Any] | None:
    return CustomizacaoRepository.get(entity_id)


def insert_customizacao(data: Dict[str, Any]) -> int:
    payload = {**data}
    payload.setdefault("created_at", datetime.utcnow().isoformat())
    return CustomizacaoRepository.insert(payload)


def update_customizacao(entity_id: int, data: Dict[str, Any]) -> bool:
    return CustomizacaoRepository.update(entity_id, data)


def delete_customizacao(entity_id: int) -> bool:
    return CustomizacaoRepository.delete(entity_id)
