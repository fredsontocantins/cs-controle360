"""Base repository with common CRUD operations."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import DATABASE_PATH, logger
from ..exceptions import DatabaseOperationError, EntityNotFoundError


class BaseRepository:
    """Base repository with common CRUD patterns."""

    table: str = ""
    columns: tuple = ()
    json_fields: tuple = ()
    order_by: str = "id"

    @classmethod
    def _connect(cls) -> sqlite3.Connection:
        try:
            Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(DATABASE_PATH)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise DatabaseOperationError(f"Could not connect to database: {e}")

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
        """List all entities in the table."""
        try:
            with cls._connect() as conn:
                rows = conn.execute(f"SELECT * FROM {cls.table} ORDER BY {cls.order_by}").fetchall()
            return [cls._to_dict(row) for row in rows]
        except DatabaseOperationError:
            raise
        except Exception as e:
            logger.error(f"Error listing {cls.table}: {e}")
            raise DatabaseOperationError(f"Error listing {cls.table}: {e}")

    @classmethod
    def get(cls, entity_id: int) -> Optional[Dict[str, Any]]:
        """Get an entity by ID. Returns None if not found."""
        try:
            with cls._connect() as conn:
                row = conn.execute(f"SELECT * FROM {cls.table} WHERE id = ?", (entity_id,)).fetchone()
            return cls._to_dict(row) if row else None
        except DatabaseOperationError:
            raise
        except Exception as e:
            logger.error(f"Error getting from {cls.table} (id={entity_id}): {e}")
            raise DatabaseOperationError(f"Error getting from {cls.table}: {e}")

    @classmethod
    def get_or_raise(cls, entity_id: int) -> Dict[str, Any]:
        """Get an entity by ID or raise EntityNotFoundError."""
        result = cls.get(entity_id)
        if result is None:
            raise EntityNotFoundError(cls.table, entity_id)
        return result

    @classmethod
    def insert(cls, data: Dict[str, Any]) -> int:
        """Insert a new entity."""
        try:
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
        except DatabaseOperationError:
            raise
        except Exception as e:
            logger.error(f"Error inserting into {cls.table}: {e}")
            raise DatabaseOperationError(f"Error inserting into {cls.table}: {e}")

    @classmethod
    def update(cls, entity_id: int, data: Dict[str, Any]) -> bool:
        """Update an existing entity."""
        try:
            payload = {k: v for k, v in data.items() if v is not None}
            if not payload:
                return False
            for field in cls.json_fields:
                if field in payload and isinstance(payload[field], (dict, list)):
                    payload[field] = json.dumps(payload[field])
            columns = list(payload.keys())
            with cls._connect() as conn:
                cursor = conn.execute(
                    f"UPDATE {cls.table} SET {','.join(f'{c}=:{c}' for c in columns)} WHERE id = :id",
                    {**payload, "id": entity_id},
                )
                return cursor.rowcount > 0
        except DatabaseOperationError:
            raise
        except Exception as e:
            logger.error(f"Error updating {cls.table} (id={entity_id}): {e}")
            raise DatabaseOperationError(f"Error updating {cls.table}: {e}")

    @classmethod
    def delete(cls, entity_id: int) -> bool:
        """Delete an entity by ID."""
        try:
            with cls._connect() as conn:
                cursor = conn.execute(f"DELETE FROM {cls.table} WHERE id = ?", (entity_id,))
                return cursor.rowcount > 0
        except DatabaseOperationError:
            raise
        except Exception as e:
            logger.error(f"Error deleting from {cls.table} (id={entity_id}): {e}")
            raise DatabaseOperationError(f"Error deleting from {cls.table}: {e}")
