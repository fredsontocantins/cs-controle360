"""Base repository with common CRUD operations."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from ..config import DATABASE_PATH, DATABASE_URL, logger
from ..database import get_conn, run_query
from ..exceptions import DatabaseOperationError, EntityNotFoundError

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None


class BaseRepository:
    """Base repository with common CRUD patterns."""

    table: str = ""
    columns: tuple = ()
    json_fields: tuple = ()
    order_by: str = "id"

    @classmethod
    def _connect(cls) -> Any:
        return get_conn()

    @classmethod
    def _to_dict(cls, row: Any) -> Dict[str, Any]:
        if row is None:
            return {}

        # Handle RealDictCursor (Postgres) or sqlite3.Row
        data = dict(row)
        for field in cls.json_fields:
            if field in data and data[field]:
                if isinstance(data[field], (dict, list)):
                    continue # Already parsed by PG JSONB
                try:
                    data[field] = json.loads(data[field])
                except (json.JSONDecodeError, TypeError):
                    data[field] = {}
        return data

    @classmethod
    def list(cls, where: Optional[str] = None, params: tuple = ()) -> List[Dict[str, Any]]:
        """List entities with optional filtering."""
        try:
            query = f"SELECT * FROM {cls.table}"
            if where:
                query += f" WHERE {where}"
            query += f" ORDER BY {cls.order_by}"

            with cls._connect() as conn:
                if DATABASE_URL:
                    # Convert SQLite ? to Postgres %s if needed (run_query handles this, but BaseRepository.list might be used directly)
                    sql = query.replace("?", "%s")
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute(sql, params)
                        rows = cur.fetchall()
                else:
                    rows = conn.execute(query, params).fetchall()
            return [cls._to_dict(row) for row in rows]
        except DatabaseOperationError:
            raise
        except Exception as e:
            logger.error(f"Error listing {cls.table}: {e}")
            raise DatabaseOperationError(f"Error listing {cls.table}: {e}")

    @classmethod
    def count(cls, where: Optional[str] = None, params: tuple = ()) -> int:
        """Count entities with optional filtering."""
        try:
            query = f"SELECT COUNT(*) FROM {cls.table}"
            if where:
                query += f" WHERE {where}"

            with cls._connect() as conn:
                cursor = run_query(conn, query, params)
                row = cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.error(f"Error counting {cls.table}: {e}")
            raise DatabaseOperationError(f"Error counting {cls.table}: {e}")

    @classmethod
    def get(cls, entity_id: int) -> Optional[Dict[str, Any]]:
        """Get an entity by ID. Returns None if not found."""
        try:
            with cls._connect() as conn:
                if DATABASE_URL:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute(f"SELECT * FROM {cls.table} WHERE id = %s", (entity_id,))
                        row = cur.fetchone()
                else:
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
                    if not DATABASE_URL:
                        payload[field] = json.dumps(payload[field])

            columns = [c for c in cls.columns if c in payload]

            with cls._connect() as conn:
                if DATABASE_URL:
                    placeholders = ",".join(["%s"] * len(columns))
                    sql = f"INSERT INTO {cls.table} ({','.join(columns)}) VALUES ({placeholders}) RETURNING id"
                    values = [payload[c] for c in columns]
                    with conn.cursor() as cur:
                        cur.execute(sql, values)
                        new_id = cur.fetchone()[0]
                    conn.commit()
                    return new_id
                else:
                    values = {c: payload[c] for c in columns}
                    cursor = conn.execute(
                        f"INSERT INTO {cls.table} ({','.join(columns)}) VALUES ({','.join(':' + c for c in columns)})",
                        values,
                    )
                    conn.commit()
                    return cursor.lastrowid or 0
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
                    if not DATABASE_URL:
                        payload[field] = json.dumps(payload[field])

            columns = list(payload.keys())
            with cls._connect() as conn:
                if DATABASE_URL:
                    set_clause = ",".join([f"{c}=%s" for c in columns])
                    sql = f"UPDATE {cls.table} SET {set_clause} WHERE id = %s"
                    values = [payload[c] for c in columns] + [entity_id]
                    with conn.cursor() as cur:
                        cur.execute(sql, values)
                        changes = cur.rowcount
                    conn.commit()
                    return changes > 0
                else:
                    conn.execute(
                        f"UPDATE {cls.table} SET {','.join(f'{c}=:{c}' for c in columns)} WHERE id = :id",
                        {**payload, "id": entity_id},
                    )
                    conn.commit()
                    return True # sqlite total_changes is tricky with context manager
        except Exception as e:
            logger.error(f"Error updating {cls.table} (id={entity_id}): {e}")
            raise DatabaseOperationError(f"Error updating {cls.table}: {e}")

    @classmethod
    def delete(cls, entity_id: int) -> bool:
        """Delete an entity by ID."""
        try:
            with cls._connect() as conn:
                if DATABASE_URL:
                    with conn.cursor() as cur:
                        cur.execute(f"DELETE FROM {cls.table} WHERE id = %s", (entity_id,))
                        changes = cur.rowcount
                    conn.commit()
                    return changes > 0
                else:
                    conn.execute(f"DELETE FROM {cls.table} WHERE id = ?", (entity_id,))
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"Error deleting from {cls.table} (id={entity_id}): {e}")
            return False
