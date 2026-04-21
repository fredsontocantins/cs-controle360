"""Customização model and repository."""

from __future__ import annotations

from typing import Any, Dict, List

from ..config import TABLE_CUSTOMIZACAO
from .base import BaseRepository


class CustomizacaoRepository(BaseRepository):
    """Repository for customização records."""

    table = TABLE_CUSTOMIZACAO
    columns = (
        "stage", "proposal", "subject", "client", "module", "module_id",
        "owner", "received_at", "status", "pf", "value", "observations",
        "pdf_path", "client_id"
    )
    json_fields = ()
    order_by = "id DESC"


# Convenience functions for backwards compatibility
def list_customizacao() -> List[Dict[str, Any]]:
    return CustomizacaoRepository.list()


def get_customizacao(entity_id: int) -> Dict[str, Any] | None:
    return CustomizacaoRepository.get(entity_id)


def insert_customizacao(data: Dict[str, Any]) -> int:
    return CustomizacaoRepository.insert(data)


def update_customizacao(entity_id: int, data: Dict[str, Any]) -> bool:
    return CustomizacaoRepository.update(entity_id, data)


def delete_customizacao(entity_id: int) -> bool:
    return CustomizacaoRepository.delete(entity_id)