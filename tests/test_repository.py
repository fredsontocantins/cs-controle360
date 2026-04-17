"""Tests for the Repository pattern + schema bootstrap."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Redirect the repository module at a fresh SQLite file and seed schema."""
    from cs_web import db, repository

    db_file: Path = tmp_path / "control.db"
    monkeypatch.setattr(repository, "DATA_DIR", tmp_path)
    monkeypatch.setattr(repository, "DB_FILE", db_file)
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_FILE", db_file)
    db.ensure_tables()
    yield db


def test_ensure_tables_creates_expected_tables(isolated_db):
    import sqlite3

    with sqlite3.connect(isolated_db.DB_FILE) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert {
        "homologation", "customizations", "releases",
        "clients", "modules", "audit_log",
    } <= tables


def test_audit_log_filters_and_pagination(isolated_db):
    repo = isolated_db.audit_log

    for i in range(3):
        repo.insert({
            "user_id": 1,
            "username": "admin",
            "action": "create",
            "entity_type": "client",
            "entity_id": i,
            "before": None,
            "after": {"name": f"c{i}"},
            "path": "/admin/clients/create",
            "ip": "127.0.0.1",
        })
    repo.insert({
        "user_id": 2,
        "username": "viewer",
        "action": "delete",
        "entity_type": "module",
        "entity_id": 99,
        "before": {"name": "old"},
        "after": None,
    })

    items, total = repo.list_paginated()
    assert total == 4
    assert len(items) == 4
    assert items[0]["action"] == "delete"

    items, total = repo.list_paginated(action="create")
    assert total == 3
    assert all(row["action"] == "create" for row in items)

    items, total = repo.list_paginated(entity_type="module")
    assert total == 1
    assert items[0]["before"] == {"name": "old"}

    items, total = repo.list_paginated(username="admin")
    assert total == 3

    items, total = repo.list_paginated(per_page=2, page=2)
    assert total == 4
    assert len(items) == 2

    types = repo.distinct_entity_types()
    assert "client" in types and "module" in types


def test_module_repository_crud(isolated_db):
    repo = isolated_db.modules

    assert repo.list() == []

    module_id = repo.insert({"name": "Catálogo", "owner": "CS"})
    assert isinstance(module_id, int) and module_id > 0

    fetched = repo.get(module_id)
    assert fetched["name"] == "Catálogo"
    assert fetched["owner"] == "CS"
    assert fetched["created_at"]  # default applied

    assert repo.update(module_id, {"owner": "Squad A"}) is True
    assert repo.get(module_id)["owner"] == "Squad A"

    # Update with only None values should be a no-op.
    assert repo.update(module_id, {"owner": None}) is False

    assert repo.delete(module_id) is True
    assert repo.get(module_id) is None


def test_client_repository_ordering_by_name(isolated_db):
    repo = isolated_db.clients
    repo.insert({"name": "Zeta"})
    repo.insert({"name": "Alfa"})
    repo.insert({"name": "Meta"})

    names = [entry["name"] for entry in repo.list()]
    assert names == ["Alfa", "Meta", "Zeta"]


def test_homologation_repository_serializes_monthly_versions(isolated_db):
    repo = isolated_db.homologation
    entity_id = repo.insert(
        {
            "module": "Catálogo",
            "status": "Em Andamento",
            "monthly_versions": {"JAN/2026": "3.17.0"},
        }
    )

    record = repo.get(entity_id)
    assert record["monthly_versions"] == {"JAN/2026": "3.17.0"}

    # Raw row should be JSON-encoded text.
    import sqlite3

    with sqlite3.connect(isolated_db.DB_FILE) as conn:
        raw = conn.execute(
            "SELECT monthly_versions FROM homologation WHERE id = ?",
            (entity_id,),
        ).fetchone()[0]
    assert raw == '{"JAN/2026": "3.17.0"}'


def test_customization_repository_orders_latest_first(isolated_db):
    repo = isolated_db.customizations
    first = repo.insert({"stage": "em_elaboracao", "proposal": "001/2025"})
    second = repo.insert({"stage": "em_elaboracao", "proposal": "002/2025"})

    records = repo.list()
    assert [r["id"] for r in records] == [second, first]


def test_release_repository_applies_created_at_default(isolated_db):
    repo = isolated_db.releases
    release_id = repo.insert(
        {"module": "Catálogo", "release_name": "Release 3.45"}
    )
    record = repo.get(release_id)
    assert record["created_at"]
    assert record["module"] == "Catálogo"


def test_seed_from_snapshot_populates_and_is_idempotent(isolated_db):
    snapshot = {
        "modules": [{"name": "Catálogo"}, {"name": "Compras"}],
        "clients": [{"name": "ACME"}],
        "homologation": [
            {
                "module": "Catálogo",
                "client": "ACME",
                "status": "Em Andamento",
                "monthly_versions": {"JAN/2026": "3.17.0"},
            }
        ],
        "customizations": [
            {"stage": "em_elaboracao", "proposal": "001/2026", "client": "ACME"}
        ],
        "releases": [
            {
                "module": "Catálogo",
                "release_name": "Release 3.45",
                "applies_on": "2026-04-15",
                "client": "ACME",
            }
        ],
    }

    isolated_db.seed_from_snapshot(snapshot)

    assert len(isolated_db.modules.list()) == 2
    assert len(isolated_db.clients.list()) == 1

    [homologation] = isolated_db.homologation.list()
    assert homologation["module"] == "Catálogo"
    assert homologation["module_id"]  # linked to modules row
    assert homologation["client_id"]  # linked to clients row

    [customization] = isolated_db.customizations.list()
    assert customization["client_id"]

    [release] = isolated_db.releases.list()
    assert release["client_id"]
    assert release["created_at"]

    # Second call is a no-op because homologation is already populated.
    isolated_db.seed_from_snapshot(snapshot)
    assert len(isolated_db.homologation.list()) == 1
