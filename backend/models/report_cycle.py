"""Report cycle model for prestação de contas status."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import TABLE_REPORT_CYCLE
from .base import BaseRepository


class ReportCycleRepository(BaseRepository):
    table = TABLE_REPORT_CYCLE
    columns = (
        "scope_type",
        "scope_id",
        "scope_label",
        "period_label",
        "status",
        "notes",
        "created_at",
        "updated_at",
        "closed_at",
    )
    json_fields = ()
    order_by = "created_at DESC"


def _scope_filters(scope_type: str, scope_id: Optional[int]) -> tuple[str, list[Any]]:
    filters = ["scope_type = ?"]
    params: list[Any] = [scope_type]
    if scope_id is None:
        filters.append("scope_id IS NULL")
    else:
        filters.append("scope_id = ?")
        params.append(scope_id)
    return " AND ".join(filters), params


def list_cycles(scope_type: Optional[str] = None, scope_id: Optional[int] = None) -> List[Dict[str, Any]]:
    if scope_type is None:
        return ReportCycleRepository.list()
    where_clause, params = _scope_filters(scope_type, scope_id)
    with ReportCycleRepository._connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM {ReportCycleRepository.table} WHERE {where_clause} ORDER BY created_at DESC",
            params,
        ).fetchall()
    return [ReportCycleRepository._to_dict(row) for row in rows]


def get_active_cycle(scope_type: str, scope_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    where_clause, params = _scope_filters(scope_type, scope_id)
    with ReportCycleRepository._connect() as conn:
        row = conn.execute(
            f"SELECT * FROM {ReportCycleRepository.table} WHERE {where_clause} ORDER BY created_at DESC LIMIT 1",
            params,
        ).fetchone()
    return ReportCycleRepository._to_dict(row) if row else None


def get_cycle(cycle_id: int) -> Optional[Dict[str, Any]]:
    with ReportCycleRepository._connect() as conn:
        row = conn.execute(
            f"SELECT * FROM {ReportCycleRepository.table} WHERE id = ?",
            (cycle_id,),
        ).fetchone()
    return ReportCycleRepository._to_dict(row) if row else None


def open_cycle(scope_type: str, scope_id: Optional[int], scope_label: Optional[str], period_label: Optional[str]) -> int:
    payload = {
        "scope_type": scope_type,
        "scope_id": scope_id,
        "scope_label": scope_label,
        "period_label": period_label,
        "status": "aberto",
        "notes": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "closed_at": None,
    }
    return ReportCycleRepository.insert(payload)


def close_cycle(cycle_id: int, notes: Optional[str] = None) -> bool:
    payload = {
        "status": "prestado",
        "notes": notes,
        "updated_at": datetime.utcnow().isoformat(),
        "closed_at": datetime.utcnow().isoformat(),
    }
    return ReportCycleRepository.update(cycle_id, payload)


def reopen_cycle(cycle_id: int) -> bool:
    payload = {
        "status": "aberto",
        "updated_at": datetime.utcnow().isoformat(),
        "closed_at": None,
    }
    return ReportCycleRepository.update(cycle_id, payload)
