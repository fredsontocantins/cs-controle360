"""Release model and repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from ..config import TABLE_RELEASE
from .report_cycle import get_active_cycle_started_at, parse_cycle_datetime
from .base import BaseRepository


class ReleaseRepository(BaseRepository):
    """Repository for release records."""

    table = TABLE_RELEASE
    columns = (
        "module", "module_id", "release_name", "version", "applies_on",
        "notes", "client", "pdf_path", "client_id", "created_at"
    )
    json_fields = ()
    order_by = "applies_on DESC, created_at DESC"


def _within_current_cycle(row: Dict[str, Any], cycle_started_at: str | None) -> bool:
    if not cycle_started_at:
        return False
    cycle_start = parse_cycle_datetime(cycle_started_at)
    if cycle_start <= datetime.min:
        return False
    created_at = parse_cycle_datetime(row.get("applies_on") or row.get("created_at"))
    return created_at >= cycle_start


def list_release(include_history: bool = False, all_cycles: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    rows = ReleaseRepository.list()
    if include_history:
        return rows
    cycle_started_at = get_active_cycle_started_at("reports", all_cycles=all_cycles)
    if not cycle_started_at:
        return []
    return [row for row in rows if _within_current_cycle(row, cycle_started_at)]


def get_release(entity_id: int) -> Dict[str, Any] | None:
    return ReleaseRepository.get(entity_id)


def insert_release(data: Dict[str, Any]) -> int:
    payload = {**data}
    payload.setdefault("created_at", datetime.utcnow().isoformat())
    return ReleaseRepository.insert(payload)


def update_release(entity_id: int, data: Dict[str, Any]) -> bool:
    return ReleaseRepository.update(entity_id, data)


def delete_release(entity_id: int) -> bool:
    return ReleaseRepository.delete(entity_id)
