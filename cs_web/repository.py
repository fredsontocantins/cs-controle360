"""Repository pattern for the CS control SQLite store.

This module centralises data-access logic. Each domain (homologation,
customizations, releases, clients, modules) has its own repository class
derived from :class:`BaseRepository`, which provides a minimal CRUD API:

- ``list()``        → returns every row, already ordered and deserialized.
- ``get(id)``       → returns a single record (or ``None``).
- ``insert(data)``  → inserts a record and returns the new id.
- ``update(id, d)`` → updates the record, returning ``True`` on changes.
- ``delete(id)``    → deletes the record, returning ``True`` on changes.

The schema and seeding helpers live in :mod:`cs_web.db`, which re-exports
these repositories as ``db.homologation``, ``db.customizations`` etc. so
callers have a single entrypoint.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_FILE = DATA_DIR / "control.db"


def _connect() -> sqlite3.Connection:
    """Open a SQLite connection pointing at the configured data file."""
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


class BaseRepository:
    """Generic SQLite-backed CRUD repository.

    Subclasses configure the behaviour through class attributes:

    ``table``
        Name of the SQL table backing this repository.
    ``columns``
        Columns accepted by :meth:`insert` (in INSERT column order).
    ``json_fields``
        Subset of ``columns`` whose values are serialized as JSON on write
        and parsed back into Python dicts on read.
    ``order_by``
        SQL fragment appended to ``SELECT * FROM <table> ORDER BY`` on
        :meth:`list` calls.
    ``defaults``
        Mapping of column name to default value (or zero-arg callable) used
        when an insert payload omits (or sets to ``None``) that column.
    """

    table: str = ""
    columns: Tuple[str, ...] = ()
    json_fields: Tuple[str, ...] = ()
    order_by: str = "id"
    defaults: Dict[str, Any] = {}

    def _row_to_dict(self, row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        if row is None:
            return None
        data = dict(row)
        for field in self.json_fields:
            if field in data:
                raw = data[field]
                try:
                    data[field] = json.loads(raw) if raw else {}
                except (json.JSONDecodeError, TypeError):
                    data[field] = {}
        return data

    def _serialize_json_fields(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        for field in self.json_fields:
            if field in payload and not isinstance(payload[field], str):
                payload[field] = json.dumps(payload[field] or {})
        return payload

    def list(self) -> List[Dict[str, Any]]:
        with _connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM {self.table} ORDER BY {self.order_by}"
            ).fetchall()
        return [self._row_to_dict(row) for row in rows if row is not None]

    def get(self, entity_id: int) -> Optional[Dict[str, Any]]:
        with _connect() as conn:
            row = conn.execute(
                f"SELECT * FROM {self.table} WHERE id = ?", (entity_id,)
            ).fetchone()
        return self._row_to_dict(row)

    def insert(self, data: Dict[str, Any]) -> int:
        payload: Dict[str, Any] = {**data}
        for key, default in self.defaults.items():
            if payload.get(key) is None:
                payload[key] = default() if callable(default) else default
        for column in self.columns:
            payload.setdefault(column, None)
        self._serialize_json_fields(payload)
        column_list = ",".join(self.columns)
        placeholders = ",".join(f":{column}" for column in self.columns)
        bind = {column: payload.get(column) for column in self.columns}
        with _connect() as conn:
            cursor = conn.execute(
                f"INSERT INTO {self.table} ({column_list}) VALUES ({placeholders})",
                bind,
            )
            return int(cursor.lastrowid)

    def update(self, entity_id: int, data: Dict[str, Any]) -> bool:
        payload = {key: value for key, value in data.items() if value is not None}
        if not payload:
            return False
        self._serialize_json_fields(payload)
        assignments = ",".join(f"{key}=:{key}" for key in payload)
        with _connect() as conn:
            conn.execute(
                f"UPDATE {self.table} SET {assignments} WHERE id = :id",
                {**payload, "id": entity_id},
            )
            return conn.total_changes > 0

    def delete(self, entity_id: int) -> bool:
        with _connect() as conn:
            conn.execute(f"DELETE FROM {self.table} WHERE id = ?", (entity_id,))
            return conn.total_changes > 0


class HomologationRepository(BaseRepository):
    table = "homologation"
    columns = (
        "module",
        "module_id",
        "status",
        "check_date",
        "observation",
        "latest_version",
        "homologation_version",
        "production_version",
        "homologated",
        "client_presentation",
        "applied",
        "monthly_versions",
        "requested_production_date",
        "production_date",
        "client_id",
    )
    json_fields = ("monthly_versions",)
    order_by = "id"


class CustomizationRepository(BaseRepository):
    table = "customizations"
    columns = (
        "stage",
        "proposal",
        "subject",
        "client",
        "module",
        "module_id",
        "owner",
        "received_at",
        "status",
        "pf",
        "value",
        "observations",
        "pdf_path",
        "client_id",
    )
    order_by = "id DESC"


class ReleaseRepository(BaseRepository):
    table = "releases"
    columns = (
        "module",
        "module_id",
        "release_name",
        "version",
        "applies_on",
        "notes",
        "client",
        "pdf_path",
        "client_id",
        "created_at",
    )
    order_by = "applies_on DESC, created_at DESC"
    defaults = {"created_at": _now_iso}


class ClientRepository(BaseRepository):
    table = "clients"
    columns = ("name", "segment", "owner", "notes", "created_at")
    order_by = "name"
    defaults = {"created_at": _now_iso}


class ModuleRepository(BaseRepository):
    table = "modules"
    columns = ("name", "description", "owner", "created_at")
    order_by = "name"
    defaults = {"created_at": _now_iso}


class AuditLogRepository(BaseRepository):
    """Append-only log of mutations made through the web UI / API.

    Each row captures who (username / user_id), when (timestamp),
    what (action + entity_type + entity_id) and the before/after
    JSON payloads so admins can reconstruct past state.
    """

    table = "audit_log"
    columns = (
        "timestamp",
        "user_id",
        "username",
        "action",
        "entity_type",
        "entity_id",
        "before",
        "after",
        "path",
        "ip",
    )
    json_fields = ("before", "after")
    order_by = "id DESC"
    defaults = {"timestamp": _now_iso}

    def list_paginated(
        self,
        *,
        page: int = 1,
        per_page: int = 50,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        username: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Return a page of rows plus the total matching count.

        All filters are optional and combined with ``AND``.
        """
        clauses: List[str] = []
        params: List[Any] = []
        if action:
            clauses.append("action = ?")
            params.append(action)
        if entity_type:
            clauses.append("entity_type = ?")
            params.append(entity_type)
        if username:
            clauses.append("username LIKE ?")
            params.append(f"%{username}%")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        offset = max(0, (max(1, page) - 1) * per_page)
        with _connect() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM {self.table}{where}", params
            ).fetchone()[0]
            rows = conn.execute(
                f"SELECT * FROM {self.table}{where} "
                f"ORDER BY {self.order_by} LIMIT ? OFFSET ?",
                [*params, per_page, offset],
            ).fetchall()
        items = [self._row_to_dict(row) for row in rows if row is not None]
        return items, int(total)

    def distinct_entity_types(self) -> List[str]:
        with _connect() as conn:
            rows = conn.execute(
                f"SELECT DISTINCT entity_type FROM {self.table} "
                f"WHERE entity_type IS NOT NULL ORDER BY entity_type"
            ).fetchall()
        return [row[0] for row in rows]


class UserRepository(BaseRepository):
    """Application user accounts for login-based authentication.

    ``role`` is one of ``admin`` (full CRUD) or ``viewer`` (read-only).
    ``password_hash`` stores a bcrypt hash; see :mod:`cs_web.auth`.
    """

    table = "users"
    columns = ("username", "password_hash", "role", "created_at")
    order_by = "username"
    defaults = {"created_at": _now_iso, "role": "viewer"}

    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        with _connect() as conn:
            row = conn.execute(
                f"SELECT * FROM {self.table} WHERE username = ?", (username,)
            ).fetchone()
        return self._row_to_dict(row)

    def update_password_hash(self, user_id: int, password_hash: str) -> bool:
        return self.update(user_id, {"password_hash": password_hash})


# Singleton instances shared by the FastAPI app and export services.
homologation_repo = HomologationRepository()
customization_repo = CustomizationRepository()
release_repo = ReleaseRepository()
client_repo = ClientRepository()
module_repo = ModuleRepository()
user_repo = UserRepository()
audit_log_repo = AuditLogRepository()


__all__ = [
    "BASE_DIR",
    "DATA_DIR",
    "DB_FILE",
    "BaseRepository",
    "HomologationRepository",
    "CustomizationRepository",
    "ReleaseRepository",
    "ClientRepository",
    "ModuleRepository",
    "UserRepository",
    "AuditLogRepository",
    "homologation_repo",
    "customization_repo",
    "release_repo",
    "client_repo",
    "module_repo",
    "user_repo",
    "audit_log_repo",
]
