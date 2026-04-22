"""Database connection and initialization."""

from __future__ import annotations

import json
from datetime import datetime
import sqlite3
from typing import Any, Dict

from .config import (
    DATABASE_PATH,
    TABLE_ATIVIDADE,
    TABLE_CLIENTE,
    TABLE_CUSTOMIZACAO,
    TABLE_HOMOLOGACAO,
    TABLE_MODULO,
    TABLE_PLAYBOOK,
    TABLE_RELEASE,
    TABLE_REPORT_CYCLE,
)


def get_conn() -> sqlite3.Connection:
    """Get database connection."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    """Add column to table if it doesn't exist."""
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def ensure_tables() -> None:
    """Create all tables if they don't exist."""
    conn = get_conn()

    # Homologação table
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_HOMOLOGACAO} (
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
            client TEXT,
            client_id INTEGER
        )
    """)
    _ensure_column(conn, TABLE_HOMOLOGACAO, "requested_production_date", "TEXT")
    _ensure_column(conn, TABLE_HOMOLOGACAO, "production_date", "TEXT")
    _ensure_column(conn, TABLE_HOMOLOGACAO, "client_id", "INTEGER")
    _ensure_column(conn, TABLE_HOMOLOGACAO, "module_id", "INTEGER")
    _ensure_column(conn, TABLE_HOMOLOGACAO, "client", "TEXT")

    # Customização table
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_CUSTOMIZACAO} (
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
    """)
    _ensure_column(conn, TABLE_CUSTOMIZACAO, "client_id", "INTEGER")
    _ensure_column(conn, TABLE_CUSTOMIZACAO, "module_id", "INTEGER")
    _ensure_column(conn, TABLE_CUSTOMIZACAO, "pdf_path", "TEXT")
    _ensure_column(conn, TABLE_CUSTOMIZACAO, "client", "TEXT")
    _ensure_column(conn, TABLE_CUSTOMIZACAO, "stage", "TEXT")
    _ensure_column(conn, TABLE_CUSTOMIZACAO, "proposal", "TEXT")
    _ensure_column(conn, TABLE_CUSTOMIZACAO, "subject", "TEXT")
    _ensure_column(conn, TABLE_CUSTOMIZACAO, "module", "TEXT")
    _ensure_column(conn, TABLE_CUSTOMIZACAO, "owner", "TEXT")
    _ensure_column(conn, TABLE_CUSTOMIZACAO, "received_at", "TEXT")
    _ensure_column(conn, TABLE_CUSTOMIZACAO, "status", "TEXT")
    _ensure_column(conn, TABLE_CUSTOMIZACAO, "pf", "REAL")
    _ensure_column(conn, TABLE_CUSTOMIZACAO, "value", "REAL")
    _ensure_column(conn, TABLE_CUSTOMIZACAO, "observations", "TEXT")

    # Atividades table (NEW)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_ATIVIDADE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            client_id INTEGER,
            module_id INTEGER,
            owner TEXT,
            status TEXT DEFAULT 'Em andamento',
            priority TEXT DEFAULT 'Normal',
            due_date TEXT,
            description TEXT,
            pdf_path TEXT,
            created_at TEXT,
            updated_at TEXT,
            release_id INTEGER,
            tipo TEXT,
            ticket TEXT,
            descricao_erro TEXT,
            resolucao TEXT,
            CHECK (title <> '')
        )
    """)
    _ensure_column(conn, TABLE_ATIVIDADE, "title", "TEXT")
    _ensure_column(conn, TABLE_ATIVIDADE, "client_id", "INTEGER")
    _ensure_column(conn, TABLE_ATIVIDADE, "module_id", "INTEGER")
    _ensure_column(conn, TABLE_ATIVIDADE, "owner", "TEXT")
    _ensure_column(conn, TABLE_ATIVIDADE, "release_id", "INTEGER")
    _ensure_column(conn, TABLE_ATIVIDADE, "tipo", "TEXT")
    _ensure_column(conn, TABLE_ATIVIDADE, "ticket", "TEXT")
    _ensure_column(conn, TABLE_ATIVIDADE, "descricao_erro", "TEXT")
    _ensure_column(conn, TABLE_ATIVIDADE, "resolucao", "TEXT")
    _ensure_column(conn, TABLE_ATIVIDADE, "priority", "TEXT")
    _ensure_column(conn, TABLE_ATIVIDADE, "due_date", "TEXT")
    _ensure_column(conn, TABLE_ATIVIDADE, "description", "TEXT")
    _ensure_column(conn, TABLE_ATIVIDADE, "pdf_path", "TEXT")
    _ensure_column(conn, TABLE_ATIVIDADE, "status", "TEXT")
    _ensure_column(conn, TABLE_ATIVIDADE, "created_at", "TEXT")
    _ensure_column(conn, TABLE_ATIVIDADE, "updated_at", "TEXT")

    # Releases table
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_RELEASE} (
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
    """)
    _ensure_column(conn, TABLE_RELEASE, "client_id", "INTEGER")
    _ensure_column(conn, TABLE_RELEASE, "client", "TEXT")
    _ensure_column(conn, TABLE_RELEASE, "module_id", "INTEGER")
    _ensure_column(conn, TABLE_RELEASE, "module", "TEXT")
    _ensure_column(conn, TABLE_RELEASE, "release_name", "TEXT")
    _ensure_column(conn, TABLE_RELEASE, "version", "TEXT")
    _ensure_column(conn, TABLE_RELEASE, "applies_on", "TEXT")
    _ensure_column(conn, TABLE_RELEASE, "notes", "TEXT")
    _ensure_column(conn, TABLE_RELEASE, "pdf_path", "TEXT")
    _ensure_column(conn, TABLE_RELEASE, "created_at", "TEXT")

    # Playbooks table
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_PLAYBOOK} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            origin TEXT NOT NULL,
            source_type TEXT,
            source_id INTEGER,
            source_key TEXT,
            source_label TEXT,
            area TEXT,
            priority_score REAL,
            priority_level TEXT,
            status TEXT DEFAULT 'ativo',
            summary TEXT,
            content_json TEXT,
            metrics_json TEXT,
            created_at TEXT,
            updated_at TEXT,
            closed_at TEXT
        )
    """)
    _ensure_column(conn, TABLE_PLAYBOOK, "title", "TEXT")
    _ensure_column(conn, TABLE_PLAYBOOK, "origin", "TEXT")
    _ensure_column(conn, TABLE_PLAYBOOK, "source_type", "TEXT")
    _ensure_column(conn, TABLE_PLAYBOOK, "source_id", "INTEGER")
    _ensure_column(conn, TABLE_PLAYBOOK, "source_key", "TEXT")
    _ensure_column(conn, TABLE_PLAYBOOK, "source_label", "TEXT")
    _ensure_column(conn, TABLE_PLAYBOOK, "area", "TEXT")
    _ensure_column(conn, TABLE_PLAYBOOK, "priority_score", "REAL")
    _ensure_column(conn, TABLE_PLAYBOOK, "priority_level", "TEXT")
    _ensure_column(conn, TABLE_PLAYBOOK, "status", "TEXT")
    _ensure_column(conn, TABLE_PLAYBOOK, "summary", "TEXT")
    _ensure_column(conn, TABLE_PLAYBOOK, "content_json", "TEXT")
    _ensure_column(conn, TABLE_PLAYBOOK, "metrics_json", "TEXT")
    _ensure_column(conn, TABLE_PLAYBOOK, "created_at", "TEXT")
    _ensure_column(conn, TABLE_PLAYBOOK, "updated_at", "TEXT")
    _ensure_column(conn, TABLE_PLAYBOOK, "closed_at", "TEXT")

    # Report cycles table
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_REPORT_CYCLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope_type TEXT NOT NULL,
            scope_id INTEGER,
            scope_label TEXT,
            period_label TEXT,
            status TEXT NOT NULL DEFAULT 'aberto',
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            closed_at TEXT
        )
    """)
    _ensure_column(conn, TABLE_REPORT_CYCLE, "scope_type", "TEXT")
    _ensure_column(conn, TABLE_REPORT_CYCLE, "scope_id", "INTEGER")
    _ensure_column(conn, TABLE_REPORT_CYCLE, "scope_label", "TEXT")
    _ensure_column(conn, TABLE_REPORT_CYCLE, "period_label", "TEXT")
    _ensure_column(conn, TABLE_REPORT_CYCLE, "status", "TEXT")
    _ensure_column(conn, TABLE_REPORT_CYCLE, "notes", "TEXT")
    _ensure_column(conn, TABLE_REPORT_CYCLE, "created_at", "TEXT")
    _ensure_column(conn, TABLE_REPORT_CYCLE, "updated_at", "TEXT")
    _ensure_column(conn, TABLE_REPORT_CYCLE, "closed_at", "TEXT")

    # PDF intelligence documents
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pdf_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope_type TEXT NOT NULL,
            scope_id INTEGER,
            scope_label TEXT,
            report_cycle_id INTEGER,
            filename TEXT NOT NULL,
            pdf_path TEXT NOT NULL,
            file_hash TEXT,
            file_size INTEGER,
            analysis_state TEXT,
            source_document_id INTEGER,
            allocation_method TEXT,
            allocation_reason TEXT,
            summary_json TEXT NOT NULL,
            last_analyzed_at TEXT,
            last_analyzed_hash TEXT,
            created_at TEXT NOT NULL
        )
    """)
    _ensure_column(conn, "pdf_documents", "scope_type", "TEXT")
    _ensure_column(conn, "pdf_documents", "scope_id", "INTEGER")
    _ensure_column(conn, "pdf_documents", "scope_label", "TEXT")
    _ensure_column(conn, "pdf_documents", "report_cycle_id", "INTEGER")
    _ensure_column(conn, "pdf_documents", "filename", "TEXT")
    _ensure_column(conn, "pdf_documents", "pdf_path", "TEXT")
    _ensure_column(conn, "pdf_documents", "file_hash", "TEXT")
    _ensure_column(conn, "pdf_documents", "file_size", "INTEGER")
    _ensure_column(conn, "pdf_documents", "analysis_state", "TEXT")
    _ensure_column(conn, "pdf_documents", "source_document_id", "INTEGER")
    _ensure_column(conn, "pdf_documents", "allocation_method", "TEXT")
    _ensure_column(conn, "pdf_documents", "allocation_reason", "TEXT")
    _ensure_column(conn, "pdf_documents", "summary_json", "TEXT")
    _ensure_column(conn, "pdf_documents", "last_analyzed_at", "TEXT")
    _ensure_column(conn, "pdf_documents", "last_analyzed_hash", "TEXT")
    _ensure_column(conn, "pdf_documents", "created_at", "TEXT")

    # Módulos table
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_MODULO} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            description TEXT,
            owner TEXT,
            created_at TEXT
        )
    """)

    # Clientes table
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_CLIENTE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            segment TEXT,
            owner TEXT,
            notes TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert sqlite3.Row to dict, handling JSON fields."""
    data = dict(row)
    for key in ["monthly_versions", "links"]:
        if key in data and data[key]:
            try:
                data[key] = json.loads(data[key])
            except (json.JSONDecodeError, TypeError):
                data[key] = {}
    return data


def seed_from_snapshot(snapshot: Dict[str, Any]) -> None:
    """Seed database from snapshot (backwards compatibility)."""
    import json
    ensure_tables()

    # Check if already seeded
    conn = get_conn()
    existing = conn.execute(f"SELECT COUNT(*) FROM {TABLE_HOMOLOGACAO}").fetchone()[0]
    if existing > 0:
        conn.close()
        return

    module_map: dict = {}
    client_map: dict = {}

    # Insert modules
    for module in snapshot.get("modules", []):
        cursor = conn.execute(
            f"INSERT INTO {TABLE_MODULO} (name, description, owner, created_at) VALUES (?, ?, ?, ?)",
            (module.get("name", ""), module.get("description", ""), module.get("owner", ""), datetime.utcnow().isoformat()),
        )
        if module.get("name"):
            module_map[module["name"]] = cursor.lastrowid

    # Insert clients
    for client in snapshot.get("clients", []):
        cursor = conn.execute(
            f"INSERT INTO {TABLE_CLIENTE} (name, segment, owner, notes, created_at) VALUES (?, ?, ?, ?, ?)",
            (client.get("name", ""), client.get("segment", ""), client.get("owner", ""), client.get("notes", ""), datetime.utcnow().isoformat()),
        )
        if client.get("name"):
            client_map[client["name"]] = cursor.lastrowid

    # Insert homologations
    for record in snapshot.get("homologation", []):
        module_name = record.get("module", "")
        client_name = record.get("client", "")
        module_id = module_map.get(module_name)
        client_id = client_map.get(client_name)
        monthly_versions = json.dumps(record.get("monthly_versions", {}))
        conn.execute(f"""
            INSERT INTO {TABLE_HOMOLOGACAO}
            (module, module_id, status, check_date, observation, latest_version,
             homologation_version, production_version, homologated, client_presentation,
             applied, monthly_versions, requested_production_date, production_date, client, client_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.get("module"), module_id, record.get("status"), record.get("check_date"),
            record.get("observation"), record.get("latest_version"), record.get("homologation_version"),
            record.get("production_version"), record.get("homologated"), record.get("client_presentation"),
            record.get("applied"), monthly_versions, record.get("requested_production_date"),
            record.get("production_date"), record.get("client"), client_id
        ))

    # Insert customizations
    for record in snapshot.get("customizations", []):
        module_name = record.get("module", "")
        client_name = record.get("client", "")
        module_id = module_map.get(module_name)
        client_id = client_map.get(client_name)
        conn.execute(f"""
            INSERT INTO {TABLE_CUSTOMIZACAO}
            (stage, proposal, subject, client, module, module_id, owner, received_at, status, pf, value, observations, pdf_path, client_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.get("stage"), record.get("proposal"), record.get("subject"), record.get("client"),
            record.get("module"), module_id, record.get("owner"), record.get("received_at"),
            record.get("status"), record.get("pf"), record.get("value"), record.get("observations"),
            record.get("pdf_path"), client_id
        ))

    # Insert releases
    for record in snapshot.get("releases", []):
        module_name = record.get("module", "")
        client_name = record.get("client", "")
        module_id = module_map.get(module_name)
        client_id = client_map.get(client_name)
        conn.execute(f"""
            INSERT INTO {TABLE_RELEASE}
            (module, module_id, release_name, version, applies_on, notes, client, pdf_path, client_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.get("module"), module_id, record.get("release_name"), record.get("version"),
            record.get("applies_on"), record.get("notes"), record.get("client"), record.get("pdf_path"),
            client_id, datetime.utcnow().isoformat()
        ))

    # Insert activities
    for record in snapshot.get("activities", []):
        conn.execute(f"""
            INSERT INTO {TABLE_ATIVIDADE}
            (title, release_id, tipo, ticket, descricao_erro, resolucao, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.get("title") or record.get("ticket") or record.get("descricao_erro") or "Atividade sem título",
            record.get("release_id"),
            record.get("tipo"),
            record.get("ticket"),
            record.get("descricao_erro"),
            record.get("resolucao"),
            record.get("status") or "backlog",
            record.get("created_at", datetime.utcnow().isoformat()),
            record.get("updated_at", datetime.utcnow().isoformat()),
        ))

    conn.commit()
    conn.close()
