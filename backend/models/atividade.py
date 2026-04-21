"""Atividade model and repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from ..config import TABLE_ATIVIDADE
from .base import BaseRepository


class AtividadeRepository(BaseRepository):
    """Repository for atividade records."""

    table = TABLE_ATIVIDADE
    columns = (
        "title", "release_id", "tipo", "ticket", "descricao_erro", "resolucao",
        "status", "created_at", "updated_at"
    )
    json_fields = ()
    order_by = "id DESC"


def _normalize(row: Dict[str, Any] | None) -> Dict[str, Any] | None:
    if not row:
        return None
    data = {**row}
    data.setdefault("status", "backlog")
    data.setdefault("title", data.get("ticket") or data.get("descricao_erro") or "Atividade sem título")
    return data


def list_atividade() -> List[Dict[str, Any]]:
    return [_normalize(row) for row in AtividadeRepository.list()]


def get_atividade(entity_id: int) -> Dict[str, Any] | None:
    return _normalize(AtividadeRepository.get(entity_id))


def insert_atividade(data: Dict[str, Any]) -> int:
    payload = {**data}
    payload.setdefault("status", "backlog")
    payload.setdefault("title", payload.get("ticket") or payload.get("descricao_erro") or "Atividade sem título")
    payload.setdefault("created_at", datetime.utcnow().isoformat())
    payload.setdefault("updated_at", datetime.utcnow().isoformat())
    return AtividadeRepository.insert(payload)


def update_atividade(entity_id: int, data: Dict[str, Any]) -> bool:
    payload = {**data}
    payload["updated_at"] = datetime.utcnow().isoformat()
    return AtividadeRepository.update(entity_id, payload)


def delete_atividade(entity_id: int) -> bool:
    return AtividadeRepository.delete(entity_id)


def list_by_release(release_id: int) -> List[Dict[str, Any]]:
    """List activities for a specific release."""
    with AtividadeRepository._connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM {TABLE_ATIVIDADE} WHERE release_id = ? ORDER BY id DESC",
            (release_id,)
        ).fetchall()
    return [_normalize(AtividadeRepository._to_dict(row)) for row in rows]


def list_by_status(status: str) -> List[Dict[str, Any]]:
    """List activities for a specific status."""
    with AtividadeRepository._connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM {TABLE_ATIVIDADE} WHERE status = ? ORDER BY id DESC",
            (status,)
        ).fetchall()
    return [_normalize(AtividadeRepository._to_dict(row)) for row in rows]
