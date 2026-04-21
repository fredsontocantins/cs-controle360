"""Utility helpers for the CS web application."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple
from uuid import uuid4

from fastapi import UploadFile

from cs_web import db

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "static" / "uploads"
DEFAULT_PAGE_SIZE = 20


def parse_optional_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def save_pdf(upload: UploadFile | None) -> str | None:
    if not upload or not upload.filename:
        return None
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    target = UPLOADS_DIR / f"{uuid4().hex}{Path(upload.filename).suffix or '.pdf'}"
    with target.open("wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)
    return str(Path("uploads") / target.name)


def resolve_client_selection(client_select: str | None, client_manual: str | None) -> tuple[int | None, str | None]:
    client_id: int | None = None
    if client_select:
        try:
            client_id = int(client_select)
        except ValueError:
            client_id = None
    label = (client_manual or "").strip() or None
    if client_id and not label:
        client = db.clients.get(client_id)
        label = client["name"] if client else None
    return client_id, label


def resolve_module_selection(module_select: str | None, module_manual: str | None) -> tuple[str | None, int | None]:
    manual = (module_manual or "").strip()
    if manual:
        return manual, None
    if module_select:
        try:
            module_id = int(module_select)
        except ValueError:
            module_id = None
        else:
            module = db.modules.get(module_id)
            if module:
                return module.get("name"), module_id
    return None, None


def match_search(item: Dict[str, Any], query: str, fields: Tuple[str, ...]) -> bool:
    if not query:
        return True
    needle = query.strip().lower()
    if not needle:
        return True
    for field in fields:
        value = item.get(field)
        if value is None:
            continue
        if needle in str(value).lower():
            return True
    return False


def paginate(
    items: List[Dict[str, Any]],
    page: int,
    per_page: int = DEFAULT_PAGE_SIZE,
) -> Dict[str, Any]:
    total = len(items)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    return {
        "items": items[start:end],
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_page": page - 1,
        "next_page": page + 1,
        "start": start + 1 if total else 0,
        "end": min(end, total),
    }


__all__ = [
    "parse_optional_float",
    "save_pdf",
    "resolve_client_selection",
    "resolve_module_selection",
    "match_search",
    "paginate",
]
