"""Database connection and initialization."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import shutil
from typing import Any, Dict

from .config import (
    DATABASE_PATH,
    RESET_SAMPLE_DATA_ON_STARTUP,
    TABLE_ATIVIDADE,
    TABLE_CLIENTE,
    TABLE_CUSTOMIZACAO,
    TABLE_HOMOLOGACAO,
    TABLE_ACTIVITY_OWNER,
    TABLE_ACTIVITY_STATUS,
    TABLE_MODULO,
    TABLE_PLAYBOOK,
    TABLE_AUTH_AUDIT,
    TABLE_USER,
    TABLE_RELEASE,
    TABLE_REPORT_CYCLE,
    UPLOADS_DIR,
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


def _first_non_empty(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _normalize_legacy_datetime(*values: Any) -> str:
    from .models.report_cycle import parse_cycle_datetime

    candidate = _first_non_empty(*values)
    if not candidate:
        return datetime.utcnow().isoformat()
    parsed = parse_cycle_datetime(candidate)
    if parsed == datetime.min:
        return candidate
    return parsed.isoformat()


def sanitize_historical_data() -> None:
    """Normalize historical records without removing user data."""
    from .models.atividade import backfill_activity_people

    conn = get_conn()
    try:
        updated = 0

        # Homologações: ensure created_at exists for historical ordering
        rows = conn.execute(f"SELECT id, created_at, check_date, requested_production_date, production_date FROM {TABLE_HOMOLOGACAO}").fetchall()
        for row in rows:
            created_at = _first_non_empty(row["created_at"])
            if not created_at:
                normalized = _normalize_legacy_datetime(row["check_date"], row["requested_production_date"], row["production_date"])
                conn.execute(
                    f"UPDATE {TABLE_HOMOLOGACAO} SET created_at = ? WHERE id = ?",
                    (normalized, row["id"]),
                )
                updated += 1

        # Customizações: ensure created_at and received_at consistency
        rows = conn.execute(f"SELECT id, created_at, received_at FROM {TABLE_CUSTOMIZACAO}").fetchall()
        for row in rows:
            created_at = _first_non_empty(row["created_at"])
            if not created_at:
                normalized = _normalize_legacy_datetime(row["received_at"])
                conn.execute(
                    f"UPDATE {TABLE_CUSTOMIZACAO} SET created_at = ? WHERE id = ?",
                    (normalized, row["id"]),
                )
                updated += 1

        # Releases: ensure created_at and applies_on consistency
        rows = conn.execute(f"SELECT id, created_at, applies_on FROM {TABLE_RELEASE}").fetchall()
        for row in rows:
            created_at = _first_non_empty(row["created_at"])
            if not created_at:
                normalized = _normalize_legacy_datetime(row["applies_on"])
                conn.execute(
                    f"UPDATE {TABLE_RELEASE} SET created_at = ? WHERE id = ?",
                    (normalized, row["id"]),
                )
                updated += 1

        # Playbooks: keep timeline stable for historical filtering
        rows = conn.execute(f"SELECT id, created_at, updated_at FROM {TABLE_PLAYBOOK}").fetchall()
        for row in rows:
            created_at = _first_non_empty(row["created_at"])
            updated_at = _first_non_empty(row["updated_at"])
            if not created_at or not updated_at:
                normalized = _normalize_legacy_datetime(created_at, updated_at)
                conn.execute(
                    f"UPDATE {TABLE_PLAYBOOK} SET created_at = COALESCE(NULLIF(created_at, ''), ?), updated_at = COALESCE(NULLIF(updated_at, ''), ?) WHERE id = ?",
                    (normalized, normalized, row["id"]),
                )
                updated += 1

        # Report cycles: ensure period label exists for visibility
        rows = conn.execute(f"SELECT id, cycle_number, period_label FROM {TABLE_REPORT_CYCLE}").fetchall()
        for row in rows:
            period_label = _first_non_empty(row["period_label"])
            if not period_label:
                conn.execute(
                    f"UPDATE {TABLE_REPORT_CYCLE} SET period_label = ? WHERE id = ?",
                    (f"Prestação {row['cycle_number'] or row['id']}", row["id"]),
                )
                updated += 1

        if updated:
            conn.commit()
    finally:
        conn.close()

    backfill_activity_people()


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
            client_id INTEGER,
            created_at TEXT
        )
    """)
    _ensure_column(conn, TABLE_HOMOLOGACAO, "requested_production_date", "TEXT")
    _ensure_column(conn, TABLE_HOMOLOGACAO, "production_date", "TEXT")
    _ensure_column(conn, TABLE_HOMOLOGACAO, "client_id", "INTEGER")
    _ensure_column(conn, TABLE_HOMOLOGACAO, "module_id", "INTEGER")
    _ensure_column(conn, TABLE_HOMOLOGACAO, "client", "TEXT")
    _ensure_column(conn, TABLE_HOMOLOGACAO, "created_at", "TEXT")

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
            client_id INTEGER,
            created_at TEXT
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
    _ensure_column(conn, TABLE_CUSTOMIZACAO, "created_at", "TEXT")

    # Atividades table (NEW)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_ATIVIDADE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            client_id INTEGER,
            module_id INTEGER,
            owner TEXT,
            executor TEXT,
            status TEXT DEFAULT 'Em andamento',
            priority TEXT DEFAULT 'Normal',
            due_date TEXT,
            description TEXT,
            pdf_path TEXT,
            created_at TEXT,
            updated_at TEXT,
            completed_at TEXT,
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
    _ensure_column(conn, TABLE_ATIVIDADE, "executor", "TEXT")
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
    _ensure_column(conn, TABLE_ATIVIDADE, "completed_at", "TEXT")

    # Atividade catalog tables
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_ACTIVITY_OWNER} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_ACTIVITY_STATUS} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            label TEXT NOT NULL,
            hint TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    _ensure_column(conn, TABLE_ACTIVITY_OWNER, "name", "TEXT")
    _ensure_column(conn, TABLE_ACTIVITY_OWNER, "sort_order", "INTEGER")
    _ensure_column(conn, TABLE_ACTIVITY_OWNER, "is_active", "INTEGER")
    _ensure_column(conn, TABLE_ACTIVITY_OWNER, "created_at", "TEXT")
    _ensure_column(conn, TABLE_ACTIVITY_STATUS, "key", "TEXT")
    _ensure_column(conn, TABLE_ACTIVITY_STATUS, "label", "TEXT")
    _ensure_column(conn, TABLE_ACTIVITY_STATUS, "hint", "TEXT")
    _ensure_column(conn, TABLE_ACTIVITY_STATUS, "sort_order", "INTEGER")
    _ensure_column(conn, TABLE_ACTIVITY_STATUS, "is_active", "INTEGER")
    _ensure_column(conn, TABLE_ACTIVITY_STATUS, "created_at", "TEXT")

    from .models.atividade import backfill_activity_people

    backfill_activity_people()

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
            cycle_number INTEGER,
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
    _ensure_column(conn, TABLE_REPORT_CYCLE, "cycle_number", "INTEGER")
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

    # Users / authentication
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_USER} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT,
            role TEXT NOT NULL DEFAULT 'user',
            provider TEXT NOT NULL DEFAULT 'local',
            google_sub TEXT UNIQUE,
            full_name TEXT,
            approval_status TEXT NOT NULL DEFAULT 'approved',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_login_at TEXT
        )
    """)
    _ensure_column(conn, TABLE_USER, "username", "TEXT")
    _ensure_column(conn, TABLE_USER, "email", "TEXT")
    _ensure_column(conn, TABLE_USER, "password_hash", "TEXT")
    _ensure_column(conn, TABLE_USER, "role", "TEXT")
    _ensure_column(conn, TABLE_USER, "provider", "TEXT")
    _ensure_column(conn, TABLE_USER, "google_sub", "TEXT")
    _ensure_column(conn, TABLE_USER, "full_name", "TEXT")
    _ensure_column(conn, TABLE_USER, "approval_status", "TEXT")
    _ensure_column(conn, TABLE_USER, "is_active", "INTEGER")
    _ensure_column(conn, TABLE_USER, "created_at", "TEXT")
    _ensure_column(conn, TABLE_USER, "updated_at", "TEXT")
    _ensure_column(conn, TABLE_USER, "last_login_at", "TEXT")

    # Authentication audit logs
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_AUTH_AUDIT} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_user_id INTEGER,
            actor_username TEXT,
            target_user_id INTEGER,
            target_username TEXT,
            event_type TEXT NOT NULL,
            status TEXT NOT NULL,
            provider TEXT,
            message TEXT,
            details_json TEXT,
            created_at TEXT NOT NULL
        )
    """)
    _ensure_column(conn, TABLE_AUTH_AUDIT, "actor_user_id", "INTEGER")
    _ensure_column(conn, TABLE_AUTH_AUDIT, "actor_username", "TEXT")
    _ensure_column(conn, TABLE_AUTH_AUDIT, "target_user_id", "INTEGER")
    _ensure_column(conn, TABLE_AUTH_AUDIT, "target_username", "TEXT")
    _ensure_column(conn, TABLE_AUTH_AUDIT, "event_type", "TEXT")
    _ensure_column(conn, TABLE_AUTH_AUDIT, "status", "TEXT")
    _ensure_column(conn, TABLE_AUTH_AUDIT, "provider", "TEXT")
    _ensure_column(conn, TABLE_AUTH_AUDIT, "message", "TEXT")
    _ensure_column(conn, TABLE_AUTH_AUDIT, "details_json", "TEXT")
    _ensure_column(conn, TABLE_AUTH_AUDIT, "created_at", "TEXT")

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
    sanitize_historical_data()

    _seed_activity_catalogs()


def _seed_activity_catalogs() -> None:
    conn = get_conn()
    now = datetime.utcnow().isoformat()

    status_rows = [
        ("backlog", "Backlog", "Itens recebidos e ainda não iniciados.", 1),
        ("em_andamento", "Em Andamento", "Em execução pela equipe.", 2),
        ("em_revisao", "Em Revisão", "Aguardando validação ou ajuste final.", 3),
        ("concluida", "Concluída", "Finalizada e pronta para relatório.", 4),
        ("bloqueada", "Bloqueada", "Dependência externa ou impedimento.", 5),
    ]
    owner_rows = [
        ("Equipe CS", 1),
        ("Desenvolvimento", 2),
        ("Suporte", 3),
        ("Implantação", 4),
        ("Gestão", 5),
    ]

    for key, label, hint, sort_order in status_rows:
        conn.execute(
            f"INSERT OR IGNORE INTO {TABLE_ACTIVITY_STATUS} (key, label, hint, sort_order, is_active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
            (key, label, hint, sort_order, now),
        )

    for name, sort_order in owner_rows:
        conn.execute(
            f"INSERT OR IGNORE INTO {TABLE_ACTIVITY_OWNER} (name, sort_order, is_active, created_at) VALUES (?, ?, 1, ?)",
            (name, sort_order, now),
        )

    conn.commit()
    conn.close()


def _month_label(value: datetime) -> str:
    months = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
    ]
    return f"{months[value.month - 1]}/{value.year}"


def _set_time(value: datetime, hour: int, minute: int = 0) -> datetime:
    return value.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _clear_table(conn: sqlite3.Connection, table: str) -> None:
    conn.execute(f"DELETE FROM {table}")


def _reset_demo_storage() -> None:
    if UPLOADS_DIR.exists():
        for path in UPLOADS_DIR.glob("*"):
            if path.is_file():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def reset_application_data() -> None:
    conn = get_conn()
    try:
        for table in (
            TABLE_AUTH_AUDIT,
            TABLE_USER,
            "pdf_documents",
            TABLE_PLAYBOOK,
            TABLE_ATIVIDADE,
            TABLE_RELEASE,
            TABLE_CUSTOMIZACAO,
            TABLE_HOMOLOGACAO,
            TABLE_REPORT_CYCLE,
            TABLE_ACTIVITY_OWNER,
            TABLE_ACTIVITY_STATUS,
            TABLE_CLIENTE,
            TABLE_MODULO,
        ):
            _clear_table(conn, table)
        conn.execute("DELETE FROM sqlite_sequence")
        conn.commit()
    finally:
        conn.close()
    _reset_demo_storage()


def _seed_demo_dataset() -> None:
    conn = get_conn()
    counts = {
        "modules": conn.execute(f"SELECT COUNT(*) FROM {TABLE_MODULO}").fetchone()[0],
        "clients": conn.execute(f"SELECT COUNT(*) FROM {TABLE_CLIENTE}").fetchone()[0],
        "homologation": conn.execute(f"SELECT COUNT(*) FROM {TABLE_HOMOLOGACAO}").fetchone()[0],
        "customization": conn.execute(f"SELECT COUNT(*) FROM {TABLE_CUSTOMIZACAO}").fetchone()[0],
        "release": conn.execute(f"SELECT COUNT(*) FROM {TABLE_RELEASE}").fetchone()[0],
        "activity": conn.execute(f"SELECT COUNT(*) FROM {TABLE_ATIVIDADE}").fetchone()[0],
        "cycle": conn.execute(f"SELECT COUNT(*) FROM {TABLE_REPORT_CYCLE}").fetchone()[0],
    }
    conn.close()
    if any(counts.values()):
        return

    now = datetime.utcnow()
    previous_start = _set_time(now - timedelta(days=31), 8)
    current_start = _set_time(now - timedelta(days=1), 8)
    previous_label = _month_label(previous_start)
    current_label = _month_label(now)

    conn = get_conn()
    try:
        module_rows = [
            ("Catálogo", "Módulo de cadastros centrais e parametrizações.", "Equipe CS"),
            ("Patrimônio Mobiliário", "Controle de bens móveis e movimentações.", "Gestão de Ativos"),
            ("Patrimônio Imobiliário", "Controle de imóveis e documentos correlatos.", "Gestão de Ativos"),
            ("Operações", "Fila operacional, acompanhamento de entregas e status.", "Coordenação"),
            ("Portal do Cliente", "Acesso corporativo com foco em consulta e acompanhamento.", "Experiência do Cliente"),
            ("Integrações", "Conectores, rotinas de sincronização e monitoramento de interfaces.", "Arquitetura"),
        ]
        client_rows = [
            ("Cliente Piloto", "Piloto", "Operação", "Ambiente de testes inicial"),
            ("Cliente Corporativo", "Corporativo", "Operação", "Conta de demonstração gerencial"),
            ("Cliente Estratégico", "Estratégico", "Operação", "Conta de validação executiva"),
            ("Cliente Inovador", "Estratégico", "Expansão", "Conta com foco em evolução e adoção"),
        ]

        module_map: dict[str, int] = {}
        client_map: dict[str, int] = {}
        for name, description, owner in module_rows:
            cursor = conn.execute(
                f"INSERT INTO {TABLE_MODULO} (name, description, owner, created_at) VALUES (?, ?, ?, ?)",
                (name, description, owner, previous_start.isoformat()),
            )
            module_map[name] = cursor.lastrowid

        for name, segment, owner, notes in client_rows:
            cursor = conn.execute(
                f"INSERT INTO {TABLE_CLIENTE} (name, segment, owner, notes, created_at) VALUES (?, ?, ?, ?, ?)",
                (name, segment, owner, notes, previous_start.isoformat()),
            )
            client_map[name] = cursor.lastrowid

        conn.execute(
            f"""INSERT INTO {TABLE_REPORT_CYCLE}
                (cycle_number, scope_type, scope_id, scope_label, period_label, status, notes, created_at, updated_at, closed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                1,
                "reports",
                None,
                "Prestação 1",
                previous_label,
                "prestado",
                "Ciclo demonstrativo encerrado para leitura comparativa.",
                previous_start.isoformat(),
                (previous_start + timedelta(days=5)).isoformat(),
                (previous_start + timedelta(days=29)).isoformat(),
            ),
        )
        conn.execute(
            f"""INSERT INTO {TABLE_REPORT_CYCLE}
                (cycle_number, scope_type, scope_id, scope_label, period_label, status, notes, created_at, updated_at, closed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                2,
                "reports",
                None,
                "Prestação 2",
                current_label,
                "aberto",
                "Ciclo operacional atual para testes iniciais.",
                current_start.isoformat(),
                current_start.isoformat(),
                None,
            ),
        )

        conn.execute(
            f"""INSERT INTO {TABLE_HOMOLOGACAO}
                (module, module_id, status, check_date, observation, latest_version, homologation_version,
                 production_version, homologated, client_presentation, applied, monthly_versions,
                 requested_production_date, production_date, client, client_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "Catálogo",
                module_map["Catálogo"],
                "Homologado",
                previous_start.date().isoformat(),
                "Homologação concluída no ciclo anterior.",
                "3.45.2",
                "3.45.2-h",
                "3.45.2-p",
                "Sim",
                "Apresentado ao cliente em comitê.",
                "Sim",
                json.dumps({"marco": "3.45.2"}),
                previous_start.date().isoformat(),
                previous_start.date().isoformat(),
                "Cliente Piloto",
                client_map["Cliente Piloto"],
                previous_start.isoformat(),
            ),
        )
        conn.execute(
            f"""INSERT INTO {TABLE_HOMOLOGACAO}
                (module, module_id, status, check_date, observation, latest_version, homologation_version,
                 production_version, homologated, client_presentation, applied, monthly_versions,
                 requested_production_date, production_date, client, client_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "Operações",
                module_map["Operações"],
                "Homologado",
                previous_start.date().isoformat(),
                "Validação de fila operacional concluída com sucesso.",
                "4.01.0",
                "4.01.0-h",
                "4.01.0-p",
                "Sim",
                "Apresentado em revisão executiva.",
                "Sim",
                json.dumps({"marco": "4.01.0"}),
                previous_start.date().isoformat(),
                previous_start.date().isoformat(),
                "Cliente Estratégico",
                client_map["Cliente Estratégico"],
                previous_start.isoformat(),
            ),
        )
        conn.execute(
            f"""INSERT INTO {TABLE_HOMOLOGACAO}
                (module, module_id, status, check_date, observation, latest_version, homologation_version,
                 production_version, homologated, client_presentation, applied, monthly_versions,
                 requested_production_date, production_date, client, client_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "Patrimônio Mobiliário",
                module_map["Patrimônio Mobiliário"],
                "Em Homologação",
                current_start.date().isoformat(),
                "Homologação em andamento no mês aberto.",
                "3.46.0",
                "3.46.0-h",
                "3.46.0-p",
                "Não",
                "Aguardando validação.",
                "Não",
                json.dumps({"abril": "3.46.0"}),
                current_start.date().isoformat(),
                current_start.date().isoformat(),
                "Cliente Corporativo",
                client_map["Cliente Corporativo"],
                current_start.isoformat(),
            ),
        )
        conn.execute(
            f"""INSERT INTO {TABLE_HOMOLOGACAO}
                (module, module_id, status, check_date, observation, latest_version, homologation_version,
                 production_version, homologated, client_presentation, applied, monthly_versions,
                 requested_production_date, production_date, client, client_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "Portal do Cliente",
                module_map["Portal do Cliente"],
                "Em Análise",
                current_start.date().isoformat(),
                "Validação de acesso corporativo e jornada do cliente.",
                "2.18.0",
                "2.18.0-h",
                "2.18.0-p",
                "Não",
                "Agenda executiva pendente.",
                "Não",
                json.dumps({"abril": "2.18.0"}),
                current_start.date().isoformat(),
                current_start.date().isoformat(),
                "Cliente Inovador",
                client_map["Cliente Inovador"],
                current_start.isoformat(),
            ),
        )

        conn.execute(
            f"""INSERT INTO {TABLE_CUSTOMIZACAO}
                (stage, proposal, subject, client, module, module_id, owner, received_at, status, pf, value, observations, pdf_path, client_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "aprovadas",
                "PRO-2026-001",
                "Ajuste de fluxo operacional e relatório",
                "Cliente Piloto",
                "Catálogo",
                module_map["Catálogo"],
                "Equipe CS",
                previous_start.date().isoformat(),
                "Aprovadas",
                8.5,
                12000.0,
                "Customização usada como base de demonstração do mês anterior.",
                None,
                client_map["Cliente Piloto"],
                previous_start.isoformat(),
            ),
        )
        conn.execute(
            f"""INSERT INTO {TABLE_CUSTOMIZACAO}
                (stage, proposal, subject, client, module, module_id, owner, received_at, status, pf, value, observations, pdf_path, client_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "em_aprovacao",
                "PRO-2026-014",
                "Nova integração de acompanhamento",
                "Cliente Corporativo",
                "Patrimônio Imobiliário",
                module_map["Patrimônio Imobiliário"],
                "Gestão",
                current_start.date().isoformat(),
                "Em Aprovação",
                5.2,
                24000.0,
                "Item do ciclo aberto para validação gerencial.",
                None,
                client_map["Cliente Corporativo"],
                current_start.isoformat(),
            ),
        )
        conn.execute(
            f"""INSERT INTO {TABLE_CUSTOMIZACAO}
                (stage, proposal, subject, client, module, module_id, owner, received_at, status, pf, value, observations, pdf_path, client_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "em_elaboracao",
                "PRO-2026-022",
                "Painel executivo com alertas gerenciais",
                "Cliente Estratégico",
                "Operações",
                module_map["Operações"],
                "Coordenação",
                current_start.date().isoformat(),
                "Em Elaboração",
                6.8,
                18000.0,
                "Customização nova para leitura executiva do ciclo corrente.",
                None,
                client_map["Cliente Estratégico"],
                current_start.isoformat(),
            ),
        )
        conn.execute(
            f"""INSERT INTO {TABLE_CUSTOMIZACAO}
                (stage, proposal, subject, client, module, module_id, owner, received_at, status, pf, value, observations, pdf_path, client_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "aprovadas",
                "PRO-2026-031",
                "Ajuste de jornada do portal corporativo",
                "Cliente Inovador",
                "Portal do Cliente",
                module_map["Portal do Cliente"],
                "Experiência do Cliente",
                current_start.date().isoformat(),
                "Aprovadas",
                7.4,
                31000.0,
                "Customização focada em navegação e clareza de acompanhamento.",
                None,
                client_map["Cliente Inovador"],
                current_start.isoformat(),
            ),
        )

        conn.execute(
            f"""INSERT INTO {TABLE_RELEASE}
                (module, module_id, release_name, version, applies_on, notes, client, pdf_path, client_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "Catálogo",
                module_map["Catálogo"],
                "Release Operacional",
                "3.45.2",
                previous_start.date().isoformat(),
                "Release fechada com correções e ajustes no ciclo anterior.",
                "Cliente Piloto",
                None,
                client_map["Cliente Piloto"],
                previous_start.isoformat(),
            ),
        )
        conn.execute(
            f"""INSERT INTO {TABLE_RELEASE}
                (module, module_id, release_name, version, applies_on, notes, client, pdf_path, client_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "Patrimônio Mobiliário",
                module_map["Patrimônio Mobiliário"],
                "Release Atual",
                "3.46.0",
                current_start.date().isoformat(),
                "Entrega base para leitura e testes do mês aberto.",
                "Cliente Corporativo",
                None,
                client_map["Cliente Corporativo"],
                current_start.isoformat(),
            ),
        )
        conn.execute(
            f"""INSERT INTO {TABLE_RELEASE}
                (module, module_id, release_name, version, applies_on, notes, client, pdf_path, client_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "Operações",
                module_map["Operações"],
                "Release Gerencial",
                "4.01.0",
                current_start.date().isoformat(),
                "Entrega com foco em monitoramento e indicadores do mês aberto.",
                "Cliente Estratégico",
                None,
                client_map["Cliente Estratégico"],
                current_start.isoformat(),
            ),
        )
        conn.execute(
            f"""INSERT INTO {TABLE_RELEASE}
                (module, module_id, release_name, version, applies_on, notes, client, pdf_path, client_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "Portal do Cliente",
                module_map["Portal do Cliente"],
                "Versão Portal Corporativo",
                "2.18.0",
                current_start.date().isoformat(),
                "Versão de acesso corporativo com foco em adoção e acompanhamento.",
                "Cliente Inovador",
                None,
                client_map["Cliente Inovador"],
                current_start.isoformat(),
            ),
        )
        conn.execute(
            f"""INSERT INTO {TABLE_RELEASE}
                (module, module_id, release_name, version, applies_on, notes, client, pdf_path, client_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "Integrações",
                module_map["Integrações"],
                "Release Integrações",
                "1.09.0",
                current_start.date().isoformat(),
                "Ajustes de sincronização e monitoramento de interfaces.",
                "Cliente Corporativo",
                None,
                client_map["Cliente Corporativo"],
                current_start.isoformat(),
            ),
        )

        conn.execute(
            f"""INSERT INTO {TABLE_ATIVIDADE}
                (title, release_id, owner, executor, tipo, ticket, descricao_erro, resolucao, status, created_at, updated_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "Ajustar rotina de validação",
                1,
                "Equipe CS",
                "Marina Souza",
                "melhoria",
                "CDMES-2901",
                "Melhoria de processo no ciclo anterior.",
                "Checklist e validação cruzada implementados.",
                "concluida",
                previous_start.isoformat(),
                (previous_start + timedelta(days=2)).isoformat(),
                (previous_start + timedelta(days=2)).isoformat(),
            ),
        )
        conn.execute(
            f"""INSERT INTO {TABLE_ATIVIDADE}
                (title, release_id, owner, executor, tipo, ticket, descricao_erro, resolucao, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "Corrigir fluxo de cadastro",
                2,
                "Suporte",
                "Carlos Lima",
                "correcao_bug",
                "CDMES-2944",
                "Ajuste de validação no mês atual.",
                "Validação e revisão aplicadas no ciclo aberto.",
                "em_andamento",
                current_start.isoformat(),
                current_start.isoformat(),
            ),
        )
        conn.execute(
            f"""INSERT INTO {TABLE_ATIVIDADE}
                (title, release_id, owner, executor, tipo, ticket, descricao_erro, resolucao, status, created_at, updated_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "Validar acesso do portal",
                4,
                "Experiência do Cliente",
                "Juliana Costa",
                "melhoria",
                "CDMES-3034",
                "Adequar navegação e validação da jornada executiva.",
                "Fluxo simplificado e acompanhamento orientado ao cliente.",
                "concluida",
                current_start.isoformat(),
                current_start.isoformat(),
                current_start.isoformat(),
            ),
        )
        conn.execute(
            f"""INSERT INTO {TABLE_ATIVIDADE}
                (title, release_id, owner, executor, tipo, ticket, descricao_erro, resolucao, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "Revisar integração de espelho",
                5,
                "Arquitetura",
                "Paulo Mendes",
                "correcao_bug",
                "CDMES-3051",
                "Intermitência em sincronização de dados.",
                "Ajuste de integração e monitoramento aplicado.",
                "em_andamento",
                current_start.isoformat(),
                current_start.isoformat(),
            ),
        )
        conn.execute(
            f"""INSERT INTO {TABLE_ATIVIDADE}
                (title, release_id, owner, executor, tipo, ticket, descricao_erro, resolucao, status, created_at, updated_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "Ajustar painel de indicadores",
                3,
                "Coordenação",
                "Ana Ribeiro",
                "melhoria",
                "CDMES-3010",
                "Aprimoramento visual no painel gerencial.",
                "Painel reorganizado com cards executivos e leitura de ciclo.",
                "concluida",
                current_start.isoformat(),
                current_start.isoformat(),
                current_start.isoformat(),
            ),
        )

        playbook_rows = [
            (
                "Como evitar inconsistências de validação",
                "erro",
                "atividades",
                1,
                "validacao-regra",
                "Validação",
                78.0,
                "alta",
                "ativo",
                "Guia para reduzir erros de validação e reforçar checklist operacional.",
                {
                    "howto": ["Revisar campos obrigatórios.", "Validar antes de publicar.", "Registrar exceção no fluxo."],
                    "checklist": ["Campos completos", "Regra conferida", "Evidência anexada"],
                },
                {"errors": 4, "tickets": 2},
            ),
            (
                "Como usar a versão atual",
                "release",
                "release",
                2,
                "versao-atual",
                "Versão",
                64.0,
                "media",
                "ativo",
                "Guia executivo da versão aberta com foco em adoção e leitura rápida.",
                {
                    "howto": ["Abrir a versão no painel.", "Consultar notas e anexos.", "Validar impacto com o time."],
                    "examples": ["Versão 3.46.0", "Entrega corrente"],
                },
                {"releases": 1, "tickets": 1},
            ),
            (
                "Como acompanhar a operação executiva",
                "manual",
                "operacoes",
                3,
                "acompanhamento-executivo",
                "Operações",
                91.0,
                "alta",
                "ativo",
                "Guia para leitura do painel, alertas e decisões gerenciais do mês aberto.",
                {
                    "howto": ["Abrir o painel.", "Consultar alertas e tendências.", "Consolidar ações do mês."],
                    "beneficio": ["Visão executiva", "Tomada de decisão mais rápida"],
                },
                {"activities": 2, "alerts": 3},
            ),
            (
                "Como acelerar a adoção do portal",
                "predicao",
                "portal",
                4,
                "adoção-portal",
                "Portal do Cliente",
                88.0,
                "alta",
                "ativo",
                "Guia para reduzir fricção de acesso e orientar a experiência do cliente.",
                {
                    "howto": [
                        "Validar acesso do cliente.",
                        "Checar jornada de uso.",
                        "Registrar dúvidas para ajuste do fluxo.",
                    ],
                    "checklist": ["Acesso validado", "Fluxo simplificado", "Acompanhamento executado"],
                },
                {"adoption": 3, "support": 2},
            ),
        ]
        for title, origin, source_type, source_id, source_key, area, score, level, status, summary, content, metrics in playbook_rows:
            conn.execute(
                f"""INSERT INTO {TABLE_PLAYBOOK}
                    (title, origin, source_type, source_id, source_key, source_label, area, priority_score, priority_level, status, summary, content_json, metrics_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    title,
                    origin,
                    source_type,
                    source_id,
                    source_key,
                    title,
                    area,
                    score,
                    level,
                    status,
                    summary,
                    json.dumps(content, ensure_ascii=False),
                    json.dumps(metrics, ensure_ascii=False),
                    current_start.isoformat(),
                    current_start.isoformat(),
                ),
            )

        from fpdf import FPDF
        from .services.pdf_intelligence import PDFIntelligenceService

        def write_demo_pdf(filename: str, title: str, lines: list[str]) -> Path:
            path = UPLOADS_DIR / filename
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=16)
            pdf.multi_cell(0, 10, title)
            pdf.set_font("Helvetica", size=11)
            for line in lines:
                pdf.multi_cell(0, 8, line)
            pdf.output(str(path))
            return path

        demo_docs = [
            {
                "scope_type": "release",
                "scope_id": 1,
                "scope_label": "Catálogo",
                "report_cycle_id": 1,
                "filename": "prestacao_catalogo_3_45_2.pdf",
                "title": "Prestação de Contas - Catálogo v3.45.2",
                "lines": [
                    "Problema: inconsistência de validação em rotina de cadastro.",
                    "Solução: reforço de checklist, revisão de campos e evidência de aprovação.",
                    "Impacto: redução de retrabalho e ganho na auditoria.",
                    "Ticket CDMES-2901 relacionado ao ajuste.",
                ],
            },
            {
                "scope_type": "homologacao",
                "scope_id": 2,
                "scope_label": "Patrimônio Mobiliário",
                "report_cycle_id": 2,
                "filename": "prestacao_patrimonio_mobiliario_3_46_0.pdf",
                "title": "Prestação de Contas - Patrimônio Mobiliário v3.46.0",
                "lines": [
                    "Objetivo: validar a entrega corrente do ciclo aberto.",
                    "Escopo: fluxo de homologação e transição para produção.",
                    "Solução: conferência de status, responsável e executante.",
                    "Ticket CDMES-2944 registrado para acompanhamento.",
                ],
            },
            {
                "scope_type": "global",
                "scope_id": None,
                "scope_label": "Painel",
                "report_cycle_id": 2,
                "filename": "prestacao_painel_gerencial.pdf",
                "title": "Painel Gerencial - Evidências do Ciclo",
                "lines": [
                    "Dados do mês atual com foco em operação, versões e atividades concluídas.",
                    "Ação: acompanhar tendências, gerar guias e manter trilha de PDFs anexados.",
                    "Benefício: leitura executiva rápida com confidencialidade ao cliente.",
                ],
            },
            {
                "scope_type": "release",
                "scope_id": 4,
                "scope_label": "Portal do Cliente",
                "report_cycle_id": 2,
                "filename": "prestacao_portal_cliente_2_18_0.pdf",
                "title": "Prestação de Contas - Portal do Cliente v2.18.0",
                "lines": [
                    "Objetivo: fortalecer a jornada executiva do cliente no portal.",
                    "Escopo: navegação, consulta e clareza de acompanhamento.",
                    "Solução: melhoria de acesso, contexto e suporte ao cliente.",
                    "Ticket CDMES-3034 relacionado à evolução.",
                ],
            },
            {
                "scope_type": "global",
                "scope_id": None,
                "scope_label": "Integrações",
                "report_cycle_id": 2,
                "filename": "prestacao_integracoes_operacao.pdf",
                "title": "Painel de Integrações - Evidências Operacionais",
                "lines": [
                    "Problema: intermitência em sincronização de dados entre sistemas.",
                    "Solução: monitoramento reforçado e ajuste de integração.",
                    "Impacto: maior previsibilidade e menor risco operacional.",
                    "Ticket CDMES-3051 relacionado ao tratamento da falha.",
                ],
            },
        ]

        pdf_service = PDFIntelligenceService()
        for index, doc in enumerate(demo_docs, start=1):
            pdf_path = write_demo_pdf(doc["filename"], doc["title"], doc["lines"])
            analysis, allocation = pdf_service.analyze_pdf(
                str(pdf_path),
                doc["filename"],
                scope_type=doc["scope_type"],
                scope_id=doc["scope_id"],
                scope_label=doc["scope_label"],
            )
            payload = pdf_service.build_payload(analysis)
            payload["analysis_state"] = "analyzed"
            payload["allocation_method"] = allocation.get("allocation_method", "seeded")
            payload["allocation_reason"] = "Dados de demonstração semeados automaticamente."
            payload["report_cycle_id"] = doc["report_cycle_id"]
            current_hash = pdf_service._file_hash(str(pdf_path))
            current_size = pdf_service._file_size(str(pdf_path))
            conn.execute(
                """INSERT INTO pdf_documents
                    (scope_type, scope_id, scope_label, report_cycle_id, filename, pdf_path, file_hash, file_size,
                     analysis_state, source_document_id, allocation_method, allocation_reason, summary_json,
                     last_analyzed_at, last_analyzed_hash, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    payload["scope_type"],
                    payload["scope_id"],
                    payload["scope_label"],
                    payload["report_cycle_id"],
                    payload["filename"],
                    f"uploads/{pdf_path.name}",
                    current_hash,
                    current_size,
                    "analyzed",
                    None,
                    payload["allocation_method"],
                    payload["allocation_reason"],
                    json.dumps(payload, ensure_ascii=False),
                    payload["generated_at"],
                    current_hash,
                    current_start.isoformat(),
                ),
            )

        conn.commit()
    finally:
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
            (title, release_id, owner, executor, tipo, ticket, descricao_erro, resolucao, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.get("title") or record.get("ticket") or record.get("descricao_erro") or "Atividade sem título",
            record.get("release_id"),
            record.get("owner"),
            record.get("executor"),
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


def seed_demo_data_if_needed() -> None:
    """Seed a starter dataset for initial reading and testing."""
    _seed_demo_dataset()
