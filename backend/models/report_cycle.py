"""Report cycle model for prestação de contas status."""

from __future__ import annotations
from ..database import run_query

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import TABLE_REPORT_CYCLE
from .base import BaseRepository


class ReportCycleRepository(BaseRepository):
    table = TABLE_REPORT_CYCLE
    columns = (
        "cycle_number",
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


def parse_cycle_datetime(value: Any) -> datetime:
    if not value:
        return datetime.min

    text = str(value).strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(text[:19] if fmt.endswith("%S") and "T" in text else text, fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return datetime.min


def list_cycles(scope_type: Optional[str] = None, scope_id: Optional[int] = None) -> List[Dict[str, Any]]:
    if scope_type is None:
        return ReportCycleRepository.list()
    where_clause, params = _scope_filters(scope_type, scope_id)
    with ReportCycleRepository._connect() as conn:
        rows = run_query(conn,
            f"SELECT * FROM {ReportCycleRepository.table} WHERE {where_clause} ORDER BY created_at DESC",
            params,
        ).fetchall()
    return [ReportCycleRepository._to_dict(row) for row in rows]


def get_active_cycle(scope_type: str, scope_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    where_clause, params = _scope_filters(scope_type, scope_id)
    with ReportCycleRepository._connect() as conn:
        row = run_query(conn,
            f"SELECT * FROM {ReportCycleRepository.table} WHERE {where_clause} AND status = 'aberto' ORDER BY created_at DESC LIMIT 1",
            params,
        ).fetchone()
        if row:
            return ReportCycleRepository._to_dict(row)

        fallback = run_query(conn,
            f"SELECT * FROM {ReportCycleRepository.table} WHERE {where_clause} ORDER BY created_at DESC LIMIT 1",
            params,
        ).fetchone()
    return ReportCycleRepository._to_dict(fallback) if fallback else None


def get_open_cycle(scope_type: str, scope_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    where_clause, params = _scope_filters(scope_type, scope_id)
    with ReportCycleRepository._connect() as conn:
        row = run_query(conn,
            f"SELECT * FROM {ReportCycleRepository.table} WHERE {where_clause} AND status = 'aberto' ORDER BY created_at DESC LIMIT 1",
            params,
        ).fetchone()
    return ReportCycleRepository._to_dict(row) if row else None


def get_active_cycle_started_at(scope_type: str, scope_id: Optional[int] = None) -> Optional[str]:
    cycle = get_open_cycle(scope_type, scope_id)
    if cycle and cycle.get("created_at"):
        return str(cycle["created_at"])
    return None


def get_cycle(cycle_id: int) -> Optional[Dict[str, Any]]:
    with ReportCycleRepository._connect() as conn:
        row = run_query(conn,
            f"SELECT * FROM {ReportCycleRepository.table} WHERE id = ?",
            (cycle_id,),
        ).fetchone()
    return ReportCycleRepository._to_dict(row) if row else None


def get_cycle_window(cycle_id: int) -> tuple[datetime, Optional[datetime]]:
    cycle = get_cycle(cycle_id)
    if not cycle:
        return datetime.min, None

    start = parse_cycle_datetime(cycle.get("created_at"))
    if start <= datetime.min:
        return datetime.min, None

    scope_type = str(cycle.get("scope_type") or "reports")
    scope_id = cycle.get("scope_id")
    scope_cycles = list_cycles(scope_type, scope_id)
    later_cycles = [
        item for item in scope_cycles
        if item.get("id") != cycle_id and parse_cycle_datetime(item.get("created_at")) > start
    ]
    later_cycles.sort(key=lambda item: parse_cycle_datetime(item.get("created_at")))
    end = parse_cycle_datetime(later_cycles[0].get("created_at")) if later_cycles else None
    return start, end


def open_cycle(scope_type: str, scope_id: Optional[int], scope_label: Optional[str], period_label: Optional[str]) -> int:
    existing_open = get_open_cycle(scope_type, scope_id)
    if existing_open and existing_open.get("id"):
        return int(existing_open["id"])

    next_number = 1
    where_clause, params = _scope_filters(scope_type, scope_id)
    with ReportCycleRepository._connect() as conn:
        row = run_query(conn,
            f"SELECT COALESCE(MAX(cycle_number), 0) AS max_cycle FROM {ReportCycleRepository.table} WHERE {where_clause}",
            params,
        ).fetchone()
        if row:
            next_number = int(row["max_cycle"] or 0) + 1
    payload = {
        "cycle_number": next_number,
        "scope_type": scope_type,
        "scope_id": scope_id,
        "scope_label": scope_label,
        "period_label": period_label or f"Prestação {next_number}",
        "status": "aberto",
        "notes": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "closed_at": None,
    }
    return ReportCycleRepository.insert(payload)


def close_cycle(cycle_id: int, notes: Optional[str] = None, period_label: Optional[str] = None) -> bool:
    current_open = None
    with ReportCycleRepository._connect() as conn:
        row = run_query(conn,
            f"SELECT * FROM {ReportCycleRepository.table} WHERE id = ? AND status = 'aberto' LIMIT 1",
            (cycle_id,),
        ).fetchone()
        if row:
            current_open = ReportCycleRepository._to_dict(row)

    if not current_open:
        return False

    payload = {
        "status": "prestado",
        "notes": notes,
        "updated_at": datetime.utcnow().isoformat(),
        "closed_at": datetime.utcnow().isoformat(),
    }
    if period_label:
        payload["period_label"] = period_label
    return ReportCycleRepository.update(cycle_id, payload)


def reopen_cycle(cycle_id: int) -> bool:
    payload = {
        "status": "aberto",
        "updated_at": datetime.utcnow().isoformat(),
        "closed_at": None,
    }
    return ReportCycleRepository.update(cycle_id, payload)
