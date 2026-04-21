"""Release model and repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from ..config import TABLE_RELEASE
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


def list_release() -> List[Dict[str, Any]]:
    return ReleaseRepository.list()


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