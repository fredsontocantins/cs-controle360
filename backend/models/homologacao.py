"""Homologação model and repository."""

from __future__ import annotations

from typing import Any, Dict, List

from ..config import TABLE_HOMOLOGACAO
from .base import BaseRepository


class HomologacaoRepository(BaseRepository):
    """Repository for homologação records."""

    table = TABLE_HOMOLOGACAO
    columns = (
        "module", "module_id", "status", "check_date", "observation",
        "latest_version", "homologation_version", "production_version",
        "homologated", "client_presentation", "applied", "monthly_versions",
        "requested_production_date", "production_date", "client", "client_id"
    )
    json_fields = ("monthly_versions",)
    order_by = "id DESC"


# Convenience functions for backwards compatibility
def list_homologacao() -> List[Dict[str, Any]]:
    return HomologacaoRepository.list()


def get_homologacao(entity_id: int) -> Dict[str, Any] | None:
    return HomologacaoRepository.get(entity_id)


def insert_homologacao(data: Dict[str, Any]) -> int:
    return HomologacaoRepository.insert(data)


def update_homologacao(entity_id: int, data: Dict[str, Any]) -> bool:
    return HomologacaoRepository.update(entity_id, data)


def delete_homologacao(entity_id: int) -> bool:
    return HomologacaoRepository.delete(entity_id)