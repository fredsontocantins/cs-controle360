"""Atividade model and repository."""

from __future__ import annotations
from ..database import run_query

from datetime import datetime
from typing import Any, Dict, List

from ..config import TABLE_ATIVIDADE
from .report_cycle import get_active_cycle_started_at, parse_cycle_datetime
from .base import BaseRepository


class AtividadeRepository(BaseRepository):
    """Repository for atividade records."""

    table = TABLE_ATIVIDADE
    columns = (
        "title", "release_id", "owner", "executor", "tipo", "ticket", "descricao_erro", "resolucao",
        "status", "created_at", "updated_at", "completed_at"
    )
    json_fields = ()
    order_by = "id DESC"


def normalize_person_name(value: Any) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    return text.strip().title()


def backfill_activity_people() -> int:
    updated = 0
    with AtividadeRepository._connect() as conn:
        rows = run_query(conn, f"SELECT id, owner, executor FROM {TABLE_ATIVIDADE}").fetchall()
        for row in rows:
            current_owner = normalize_person_name(row["owner"])
            current_executor = normalize_person_name(row["executor"] or current_owner)
            payload: Dict[str, Any] = {}
            if current_owner != (row["owner"] or ""):
                payload["owner"] = current_owner
            if current_executor != (row["executor"] or ""):
                payload["executor"] = current_executor
            if not payload:
                continue
            updated += 1
            run_query(conn,
                f"UPDATE {TABLE_ATIVIDADE} SET owner = ?, executor = ? WHERE id = ?",
                (
                    payload.get("owner", current_owner),
                    payload.get("executor", current_executor),
                    row["id"],
                ),
            )
        conn.commit()
    return updated


def _normalize(row: Dict[str, Any] | None) -> Dict[str, Any] | None:
    if not row:
        return None
    data = {**row}
    data.setdefault("status", "backlog")
    data.setdefault("title", data.get("ticket") or data.get("descricao_erro") or "Atividade sem título")
    data.setdefault("owner", normalize_person_name(data.get("owner")))
    data.setdefault("executor", normalize_person_name(data.get("executor") or data.get("owner")))
    return data


def _within_current_cycle(row: Dict[str, Any], cycle_started_at: str | None) -> bool:
    if not cycle_started_at:
        return False
    cycle_start = parse_cycle_datetime(cycle_started_at)
    if cycle_start <= datetime.min:
        return False
    return parse_cycle_datetime(row.get("created_at") or row.get("updated_at") or row.get("completed_at")) >= cycle_start


def list_atividade(include_history: bool = False, all_cycles: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    rows = [_normalize(row) for row in AtividadeRepository.list()]
    if include_history:
        return rows
    cycle_started_at = get_active_cycle_started_at("reports", all_cycles=all_cycles)
    if not cycle_started_at:
        return []
    return [row for row in rows if row and _within_current_cycle(row, cycle_started_at)]


def get_atividade(entity_id: int) -> Dict[str, Any] | None:
    return _normalize(AtividadeRepository.get(entity_id))


def insert_atividade(data: Dict[str, Any]) -> int:
    payload = {**data}
    payload.setdefault("status", "backlog")
    payload.setdefault("title", payload.get("ticket") or payload.get("descricao_erro") or "Atividade sem título")
    payload["owner"] = normalize_person_name(payload.get("owner"))
    payload["executor"] = normalize_person_name(payload.get("executor") or payload.get("owner"))
    payload.setdefault("created_at", datetime.utcnow().isoformat())
    payload.setdefault("updated_at", datetime.utcnow().isoformat())
    if payload.get("status") == "concluida":
        payload.setdefault("completed_at", datetime.utcnow().isoformat())
    return AtividadeRepository.insert(payload)


def update_atividade(entity_id: int, data: Dict[str, Any]) -> bool:
    payload = {**data}
    if "owner" in payload:
        payload["owner"] = normalize_person_name(payload.get("owner"))
    if "executor" in payload:
        payload["executor"] = normalize_person_name(payload.get("executor") or payload.get("owner"))
    if payload.get("status") == "concluida" and not payload.get("completed_at"):
        payload["completed_at"] = datetime.utcnow().isoformat()
    payload["updated_at"] = datetime.utcnow().isoformat()
    return AtividadeRepository.update(entity_id, payload)


def delete_atividade(entity_id: int) -> bool:
    return AtividadeRepository.delete(entity_id)


def list_by_release(release_id: int, include_history: bool = False) -> List[Dict[str, Any]]:
    """List activities for a specific release."""
    with AtividadeRepository._connect() as conn:
        rows = run_query(conn,
            f"SELECT * FROM {TABLE_ATIVIDADE} WHERE release_id = ? ORDER BY id DESC",
            (release_id,)
        ).fetchall()
    normalized = [_normalize(AtividadeRepository._to_dict(row)) for row in rows]
    if include_history:
        return normalized
    cycle_started_at = get_active_cycle_started_at("reports")
    if not cycle_started_at:
        return []
    return [row for row in normalized if row and _within_current_cycle(row, cycle_started_at)]


def list_by_status(status: str) -> List[Dict[str, Any]]:
    """List activities for a specific status."""
    with AtividadeRepository._connect() as conn:
        rows = run_query(conn,
            f"SELECT * FROM {TABLE_ATIVIDADE} WHERE status = ? ORDER BY id DESC",
            (status,)
        ).fetchall()
    return [_normalize(AtividadeRepository._to_dict(row)) for row in rows]
