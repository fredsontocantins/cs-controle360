"""Standardized API response envelope for CS-Controle 360.

Every module endpoint wraps its return in a consistent structure so
each menu has its own independent, predictable contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


def ok(
    data: Any,
    *,
    meta: Optional[dict] = None,
    module: Optional[str] = None,
) -> dict:
    envelope: dict[str, Any] = {
        "status": "ok",
        "module": module,
        "data": data,
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            **(meta or {}),
        },
    }
    return envelope


def ok_list(
    items: list,
    *,
    module: Optional[str] = None,
    meta: Optional[dict] = None,
) -> dict:
    return ok(
        items,
        module=module,
        meta={"count": len(items), **(meta or {})},
    )


def ok_deleted(*, module: Optional[str] = None) -> dict:
    return ok(None, module=module, meta={"action": "deleted"})
