"""Schema, seed and repository facade for the CS control SQLite store.

The data-access logic lives in :mod:`cs_web.repository` (one repository per
domain). This module owns the few responsibilities that are not per-domain:

* the physical location of the database file (imported from the repository
  module so both sides share a single source of truth);
* :func:`ensure_tables`, which applies the schema on startup;
* :func:`seed_from_snapshot`, which bootstraps the store from an initial
  JSON snapshot;
* convenient namespaced aliases so existing callers can keep writing
  ``db.homologation.list()``, ``db.customizations.insert(...)`` and so on.
"""

from __future__ import annotations

from typing import Any, Dict

from cs_web.repository import (
    BASE_DIR,
    DATA_DIR,
    DB_FILE,
    _connect,
    client_repo,
    customization_repo,
    homologation_repo,
    module_repo,
    release_repo,
)

# Namespaced handles exposed to the rest of the app, e.g. ``db.homologation``.
homologation = homologation_repo
customizations = customization_repo
releases = release_repo
clients = client_repo
modules = module_repo

HOMO_TABLE = homologation_repo.table
CUST_TABLE = customization_repo.table
RELEASE_TABLE = release_repo.table
CLIENT_TABLE = client_repo.table
MODULE_TABLE = module_repo.table


def _ensure_column(conn, table: str, column: str, definition: str) -> None:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def ensure_tables() -> None:
    """Create any missing tables / columns for the CS control store."""
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


def seed_from_snapshot(snapshot: Dict[str, Any]) -> None:
    """Populate an empty database from an initial JSON snapshot."""
    ensure_tables()
    if homologation_repo.list():
        return

    module_map: Dict[str, int] = {}
    client_map: Dict[str, int] = {}

    for module in snapshot.get("modules", []):
        module_id = module_repo.insert(module)
        name = module.get("name")
        if name:
            module_map[name] = module_id

    for client in snapshot.get("clients", []):
        client_id = client_repo.insert(client)
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
        homologation_repo.insert(_associate_ids(record))
    for record in snapshot.get("customizations", []):
        customization_repo.insert(_associate_ids(record))
    for record in snapshot.get("releases", []):
        release_repo.insert(_associate_ids(record))


__all__ = [
    "BASE_DIR",
    "DATA_DIR",
    "DB_FILE",
    "HOMO_TABLE",
    "CUST_TABLE",
    "RELEASE_TABLE",
    "CLIENT_TABLE",
    "MODULE_TABLE",
    "homologation",
    "customizations",
    "releases",
    "clients",
    "modules",
    "ensure_tables",
    "seed_from_snapshot",
]
