"""Base repository with common CRUD operations."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from ..config import DATABASE_PATH


class BaseRepository:
    """Base repository with common CRUD patterns."""

    table: str = ""
    columns: tuple = ()
    json_fields: tuple = ()
    order_by: str = "id"

    @classmethod
    def _connect(cls) -> sqlite3.Connection:
        Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def _to_dict(cls, row: sqlite3.Row) -> Dict[str, Any]:
        data = dict(row)
        for field in cls.json_fields:
            if field in data and data[field]:
                try:
                    data[field] = json.loads(data[field])
                except json.JSONDecodeError:
                    data[field] = {}
        return data

    @classmethod
    def list(cls) -> List[Dict[str, Any]]:
        with cls._connect() as conn:
            rows = conn.execute(f"SELECT * FROM {cls.table} ORDER BY {cls.order_by}").fetchall()
        return [cls._to_dict(row) for row in rows]

    @classmethod
    def get(cls, entity_id: int) -> Optional[Dict[str, Any]]:
        with cls._connect() as conn:
            row = conn.execute(f"SELECT * FROM {cls.table} WHERE id = ?", (entity_id,)).fetchone()
        return cls._to_dict(row) if row else None

    @classmethod
    def insert(cls, data: Dict[str, Any]) -> int:
        payload = {**data}
        for field in cls.json_fields:
            if field in payload and isinstance(payload[field], (dict, list)):
                payload[field] = json.dumps(payload[field])
        columns = [c for c in cls.columns if c in payload]
        values = {c: payload[c] for c in columns}
        with cls._connect() as conn:
            cursor = conn.execute(
                f"INSERT INTO {cls.table} ({','.join(columns)}) VALUES ({','.join(':' + c for c in columns)})",
                values,
            )
            return cursor.lastrowid or 0

    @classmethod
    def update(cls, entity_id: int, data: Dict[str, Any]) -> bool:
        payload = {k: v for k, v in data.items() if v is not None}
        if not payload:
            return False
        for field in cls.json_fields:
            if field in payload and isinstance(payload[field], (dict, list)):
                payload[field] = json.dumps(payload[field])
        columns = list(payload.keys())
        with cls._connect() as conn:
            conn.execute(
                f"UPDATE {cls.table} SET {','.join(f'{c}=:{c}' for c in columns)} WHERE id = :id",
                {**payload, "id": entity_id},
            )
            return conn.total_changes > 0

    @classmethod
    def delete(cls, entity_id: int) -> bool:
        with cls._connect() as conn:
            conn.execute(f"DELETE FROM {cls.table} WHERE id = ?", (entity_id,))
            return conn.total_changes > 0