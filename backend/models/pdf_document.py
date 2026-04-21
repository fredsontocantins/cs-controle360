"""Repository for uploaded PDF intelligence documents."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import DATABASE_PATH
from .base import BaseRepository


class PdfDocumentRepository(BaseRepository):
    table = "pdf_documents"
    columns = (
        "scope_type",
        "scope_id",
        "scope_label",
        "report_cycle_id",
        "filename",
        "pdf_path",
        "file_hash",
        "file_size",
        "summary_json",
        "last_analyzed_at",
        "last_analyzed_hash",
        "created_at",
    )
    json_fields = ("summary_json",)
    order_by = "created_at DESC"


def list_documents(scope_type: Optional[str] = None, scope_id: Optional[int] = None) -> List[Dict[str, Any]]:
    query = f"SELECT * FROM {PdfDocumentRepository.table}"
    params: list[Any] = []
    filters: list[str] = []
    if scope_type:
        filters.append("scope_type = ?")
        params.append(scope_type)
    if scope_id is not None:
        filters.append("scope_id = ?")
        params.append(scope_id)
    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += " ORDER BY created_at DESC"
    with PdfDocumentRepository._connect() as conn:
        rows = conn.execute(query, params).fetchall()

    documents: List[Dict[str, Any]] = []
    for row in rows:
        data = PdfDocumentRepository._to_dict(row)
        if isinstance(data.get("summary_json"), str):
            try:
                data["summary"] = json.loads(data["summary_json"])
            except json.JSONDecodeError:
                data["summary"] = {}
        else:
            data["summary"] = data.get("summary_json") or {}
        documents.append(data)
    return documents


def get_document(document_id: int) -> Optional[Dict[str, Any]]:
    with PdfDocumentRepository._connect() as conn:
        row = conn.execute(f"SELECT * FROM {PdfDocumentRepository.table} WHERE id = ?", (document_id,)).fetchone()
    if not row:
        return None
    data = PdfDocumentRepository._to_dict(row)
    if isinstance(data.get("summary_json"), str):
        try:
            data["summary"] = json.loads(data["summary_json"])
        except json.JSONDecodeError:
            data["summary"] = {}
    else:
        data["summary"] = data.get("summary_json") or {}
    return data


def insert_document(data: Dict[str, Any]) -> int:
    payload = {**data}
    payload.setdefault("created_at", datetime.utcnow().isoformat())
    if isinstance(payload.get("summary_json"), dict):
        payload["summary_json"] = json.dumps(payload["summary_json"], ensure_ascii=False)
    return PdfDocumentRepository.insert(payload)


def update_document(document_id: int, data: Dict[str, Any]) -> bool:
    payload = {**data}
    if isinstance(payload.get("summary_json"), dict):
        payload["summary_json"] = json.dumps(payload["summary_json"], ensure_ascii=False)
    return PdfDocumentRepository.update(document_id, payload)


def count_documents(
    scope_type: Optional[str] = None,
    scope_id: Optional[int] = None,
    report_cycle_id: Optional[int] = None,
) -> int:
    query = f"SELECT COUNT(*) FROM {PdfDocumentRepository.table}"
    params: list[Any] = []
    filters: list[str] = []
    if scope_type:
        filters.append("scope_type = ?")
        params.append(scope_type)
    if scope_id is not None:
        filters.append("scope_id = ?")
        params.append(scope_id)
    if report_cycle_id is not None:
        filters.append("report_cycle_id = ?")
        params.append(report_cycle_id)
    if filters:
        query += " WHERE " + " AND ".join(filters)
    with PdfDocumentRepository._connect() as conn:
        row = conn.execute(query, params).fetchone()
    return int(row[0]) if row else 0
