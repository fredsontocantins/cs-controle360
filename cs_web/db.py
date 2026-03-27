"""Simple SQLite-based store for the CS control data."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_FILE = DATA_DIR / "control.db"
HOMO_TABLE = "homologation"
CUST_TABLE = "customizations"
RELEASE_TABLE = "releases"
CLIENT_TABLE = "clients"
MODULE_TABLE = "modules"


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def ensure_tables() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS homologation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module TEXT,
                module_id INTEGER,
                status TEXT,
                check_date TEXT,
                observation TEXT,
                latest_version TEXT,
                homologation_version TEXT,
                production_version TEXT,
                homologated TEXT,
                client_presentation TEXT,
                applied TEXT,
                monthly_versions TEXT,
                requested_production_date TEXT,
                production_date TEXT,
                client_id INTEGER
            )
            """
        )
        _ensure_column(conn, HOMO_TABLE, "requested_production_date", "TEXT")
        _ensure_column(conn, HOMO_TABLE, "production_date", "TEXT")
        _ensure_column(conn, HOMO_TABLE, "client_id", "INTEGER")
        _ensure_column(conn, HOMO_TABLE, "module_id", "INTEGER")
        _ensure_column(conn, HOMO_TABLE, "client", "TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS customizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stage TEXT,
                proposal TEXT,
                subject TEXT,
                client TEXT,
                module TEXT,
                module_id INTEGER,
                owner TEXT,
                received_at TEXT,
                status TEXT,
                pf REAL,
                value REAL,
                observations TEXT,
                pdf_path TEXT,
                client_id INTEGER
            )
            """
        )
        _ensure_column(conn, CUST_TABLE, "client_id", "INTEGER")
        _ensure_column(conn, CUST_TABLE, "module_id", "INTEGER")
        _ensure_column(conn, CUST_TABLE, "pdf_path", "TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                segment TEXT,
                owner TEXT,
                notes TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS releases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module TEXT,
                module_id INTEGER,
                release_name TEXT,
                version TEXT,
                applies_on TEXT,
                notes TEXT,
                client TEXT,
                pdf_path TEXT,
                client_id INTEGER,
                created_at TEXT
            )
            """
        )
        _ensure_column(conn, RELEASE_TABLE, "client_id", "INTEGER")
        _ensure_column(conn, RELEASE_TABLE, "client", "TEXT")
        _ensure_column(conn, RELEASE_TABLE, "module_id", "INTEGER")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                owner TEXT,
                created_at TEXT
            )
            """
        )


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    if "monthly_versions" in data:
        try:
            data["monthly_versions"] = json.loads(data["monthly_versions"] or "{}")
        except json.JSONDecodeError:
            data["monthly_versions"] = {}
    if "links" in data:
        try:
            data["links"] = json.loads(data["links"] or "{}")
        except json.JSONDecodeError:
            data["links"] = {}
    return data


def list_homologation() -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM homologation").fetchall()
    return [_row_to_dict(row) for row in rows]


def list_customizations() -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM customizations ORDER BY id DESC").fetchall()
    return [_row_to_dict(row) for row in rows]


def get_homologation(entity_id: int) -> Dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM homologation WHERE id = ?", (entity_id,)).fetchone()
    return _row_to_dict(row) if row else None


def get_customization(entity_id: int) -> Dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM customizations WHERE id = ?", (entity_id,)).fetchone()
    return _row_to_dict(row) if row else None


def insert_homologation(data: Dict[str, Any]) -> int:
    payload = {**data}
    payload["monthly_versions"] = json.dumps(payload.get("monthly_versions", {}))
    payload.setdefault("requested_production_date", None)
    payload.setdefault("production_date", None)
    payload.setdefault("client_id", None)
    payload.setdefault("module_id", None)
    with _connect() as conn:
        cursor = conn.execute(
            """INSERT INTO homologation
            (module,module_id,status,check_date,observation,latest_version,homologation_version,
            production_version,homologated,client_presentation,applied,monthly_versions,
            requested_production_date,production_date,client_id)
            VALUES (:module,:module_id,:status,:check_date,:observation,:latest_version,:homologation_version,
            :production_version,:homologated,:client_presentation,:applied,:monthly_versions,
            :requested_production_date,:production_date,:client_id)""",
            payload,
        )
        return cursor.lastrowid


def insert_customization(data: Dict[str, Any]) -> int:
    payload = {**data}
    payload.setdefault("pdf_path", None)
    payload.setdefault("client_id", None)
    payload.setdefault("module_id", None)
    with _connect() as conn:
        cursor = conn.execute(
            """INSERT INTO customizations (stage,proposal,subject,client,module,module_id,owner,received_at,status,pf,value,observations,pdf_path,client_id)
            VALUES (:stage,:proposal,:subject,:client,:module,:module_id,:owner,:received_at,:status,:pf,:value,:observations,:pdf_path,:client_id)""",
            payload,
        )
        return cursor.lastrowid


def update_homologation(entity_id: int, data: Dict[str, Any]) -> bool:
    payload = {
        key: json.dumps(value) if key == "monthly_versions" else value
        for key, value in data.items()
        if value is not None
    }
    if not payload:
        return False
    columns = ",".join(f"{k}=:{k}" for k in payload)
    with _connect() as conn:
        conn.execute(
            f"UPDATE {HOMO_TABLE} SET {columns} WHERE id = :id",
            {**payload, "id": entity_id},
        )
        return conn.total_changes > 0


def update_customization(entity_id: int, data: Dict[str, Any]) -> bool:
    payload = {k: v for k, v in data.items() if v is not None}
    if not payload:
        return False
    columns = ",".join(f"{k}=:{k}" for k in payload)
    with _connect() as conn:
        conn.execute(
            f"UPDATE {CUST_TABLE} SET {columns} WHERE id = :id",
            {**payload, "id": entity_id},
        )
        return conn.total_changes > 0


def delete_homologation(entity_id: int) -> bool:
    with _connect() as conn:
        conn.execute(f"DELETE FROM {HOMO_TABLE} WHERE id = ?", (entity_id,))
        return conn.total_changes > 0


def delete_customization(entity_id: int) -> bool:
    with _connect() as conn:
        conn.execute(f"DELETE FROM {CUST_TABLE} WHERE id = ?", (entity_id,))
        return conn.total_changes > 0


def list_releases() -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM releases ORDER BY applies_on DESC, created_at DESC").fetchall()
    return [_row_to_dict(row) for row in rows]


def get_release(entity_id: int) -> Dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM releases WHERE id = ?", (entity_id,)).fetchone()
    return _row_to_dict(row) if row else None

def insert_release(data: Dict[str, Any]) -> int:
    payload = {**data}
    payload.setdefault("created_at", datetime.utcnow().isoformat())
    payload.setdefault("client_id", None)
    payload.setdefault("client", None)
    payload.setdefault("module_id", None)
    with _connect() as conn:
        cursor = conn.execute(
            """INSERT INTO releases (module,module_id,release_name,version,applies_on,notes,client,pdf_path,client_id,created_at)
            VALUES (:module,:module_id,:release_name,:version,:applies_on,:notes,:client,:pdf_path,:client_id,:created_at)""",
            payload,
        )
    return cursor.lastrowid

def update_release(entity_id: int, data: Dict[str, Any]) -> bool:
    payload = {k: v for k, v in data.items() if v is not None}
    if not payload:
        return False
    columns = ",".join(f"{k}=:{k}" for k in payload)
    with _connect() as conn:
        conn.execute(
            f"UPDATE {RELEASE_TABLE} SET {columns} WHERE id = :id",
            {**payload, "id": entity_id},
        )
        return conn.total_changes > 0


def delete_release(entity_id: int) -> bool:
    with _connect() as conn:
        conn.execute(f"DELETE FROM {RELEASE_TABLE} WHERE id = ?", (entity_id,))
        return conn.total_changes > 0


def list_modules() -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM modules ORDER BY name").fetchall()
    return [dict(row) for row in rows]


def get_module(entity_id: int) -> Dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM modules WHERE id = ?", (entity_id,)).fetchone()
    return dict(row) if row else None


def insert_module(data: Dict[str, Any]) -> int:
    payload = {**data}
    payload.setdefault("created_at", datetime.utcnow().isoformat())
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO modules (name,description,owner,created_at) VALUES (:name,:description,:owner,:created_at)",
            payload,
        )
    return cursor.lastrowid


def update_module(entity_id: int, data: Dict[str, Any]) -> bool:
    payload = {k: v for k, v in data.items() if v is not None}
    if not payload:
        return False
    columns = ",".join(f"{k}=:{k}" for k in payload)
    with _connect() as conn:
        conn.execute(
            f"UPDATE {MODULE_TABLE} SET {columns} WHERE id = :id",
            {**payload, "id": entity_id},
        )
        return conn.total_changes > 0


def delete_module(entity_id: int) -> bool:
    with _connect() as conn:
        conn.execute(f"DELETE FROM {MODULE_TABLE} WHERE id = ?", (entity_id,))
        return conn.total_changes > 0


def list_clients() -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM clients ORDER BY name").fetchall()
    return [dict(row) for row in rows]


def get_client(entity_id: int) -> Dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM clients WHERE id = ?", (entity_id,)).fetchone()
    return dict(row) if row else None


def insert_client(data: Dict[str, Any]) -> int:
    payload = {**data}
    payload.setdefault("created_at", datetime.utcnow().isoformat())
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO clients (name,segment,owner,notes,created_at) VALUES (:name,:segment,:owner,:notes,:created_at)",
            payload,
        )
    return cursor.lastrowid


def update_client(entity_id: int, data: Dict[str, Any]) -> bool:
    payload = {k: v for k, v in data.items() if v is not None}
    if not payload:
        return False
    columns = ",".join(f"{k}=:{k}" for k in payload)
    with _connect() as conn:
        conn.execute(
            f"UPDATE {CLIENT_TABLE} SET {columns} WHERE id = :id",
            {**payload, "id": entity_id},
        )
        return conn.total_changes > 0


def delete_client(entity_id: int) -> bool:
    with _connect() as conn:
        conn.execute(f"DELETE FROM {CLIENT_TABLE} WHERE id = ?", (entity_id,))
        return conn.total_changes > 0


def seed_from_snapshot(snapshot: Dict[str, Any]) -> None:
    ensure_tables()
    if list_homologation():
        return
    module_map: dict[str, int] = {}
    client_map: dict[str, int] = {}

    for module in snapshot.get("modules", []):
        module_id = insert_module(module)
        name = module.get("name")
        if name:
            module_map[name] = module_id

    for client in snapshot.get("clients", []):
        client_id = insert_client(client)
        name = client.get("name")
        if name:
            client_map[name] = client_id

    def _associate_ids(record: Dict[str, Any]) -> Dict[str, Any]:
        candidate = {**record}
        module_name = candidate.get("module")
        if module_name and module_name in module_map:
            candidate["module_id"] = module_map[module_name]
        client_name = candidate.get("client")
        if client_name and client_name in client_map:
            candidate["client_id"] = client_map[client_name]
        return candidate

    for record in snapshot.get("homologation", []):
        insert_homologation(_associate_ids(record))
    for record in snapshot.get("customizations", []):
        insert_customization(_associate_ids(record))
    for record in snapshot.get("releases", []):
        insert_release(_associate_ids(record))
