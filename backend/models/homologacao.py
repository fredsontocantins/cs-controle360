"""Homologação model and repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from ..config import TABLE_HOMOLOGACAO
from .report_cycle import get_active_cycle_started_at, parse_cycle_datetime
from .base import BaseRepository


class HomologacaoRepository(BaseRepository):
    """Repository for homologação records."""

    table = TABLE_HOMOLOGACAO
    columns = (
        "module", "module_id", "status", "check_date", "observation",
        "latest_version", "homologation_version", "production_version",
        "homologated", "client_presentation", "applied", "monthly_versions",
        "requested_production_date", "production_date", "client", "client_id", "created_at"
    )
    json_fields = ("monthly_versions",)
    order_by = "id DESC"


# Convenience functions for backwards compatibility
def _within_current_cycle(row: Dict[str, Any], cycle_started_at: str | None) -> bool:
    if not cycle_started_at:
        return False
    cycle_start = parse_cycle_datetime(cycle_started_at)
    if cycle_start <= datetime.min:
        return False
    candidate = row.get("check_date") or row.get("requested_production_date") or row.get("production_date") or row.get("created_at")
    return parse_cycle_datetime(candidate) >= cycle_start


def list_homologacao(include_history: bool = False) -> List[Dict[str, Any]]:
    rows = HomologacaoRepository.list()
    if include_history:
        return rows
    cycle_started_at = get_active_cycle_started_at("reports")
    if not cycle_started_at:
        return []
    return [row for row in rows if _within_current_cycle(row, cycle_started_at)]


def get_homologacao(entity_id: int) -> Dict[str, Any] | None:
    return HomologacaoRepository.get(entity_id)


def insert_homologacao(data: Dict[str, Any]) -> int:
    payload = {**data}
    payload.setdefault("created_at", datetime.utcnow().isoformat())
    return HomologacaoRepository.insert(payload)


def update_homologacao(entity_id: int, data: Dict[str, Any]) -> bool:
    return HomologacaoRepository.update(entity_id, data)


def delete_homologacao(entity_id: int) -> bool:
    return HomologacaoRepository.delete(entity_id)
