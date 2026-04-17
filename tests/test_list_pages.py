"""Tests for the read-only list pages with search and pagination."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("CS_SESSION_SECRET", "unit-tests-secret")
    monkeypatch.setenv("CS_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("CS_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("CS_API_KEY", "cs-secret")

    import cs_web.db as cs_db
    import cs_web.repository as cs_repo

    monkeypatch.setattr(cs_db, "DATA_DIR", data_dir, raising=False)
    monkeypatch.setattr(cs_db, "DB_PATH", data_dir / "control.db", raising=False)
    monkeypatch.setattr(cs_repo, "DATA_DIR", data_dir, raising=False)
    monkeypatch.setattr(cs_repo, "DB_FILE", data_dir / "control.db", raising=False)
    monkeypatch.setattr(cs_repo, "DB_PATH", data_dir / "control.db", raising=False)

    from cs_web.auth import ensure_default_admin
    from cs_web.main import app

    cs_db.ensure_tables()
    ensure_default_admin()
    return TestClient(app, follow_redirects=False)


def _login(client: TestClient) -> str:
    resp = client.post("/login", data={"username": "admin", "password": "admin-pass"})
    cookie = resp.cookies.get("cs_session")
    assert cookie is not None
    return cookie


def test_homologations_page_requires_login(client: TestClient) -> None:
    resp = client.get("/homologations")
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/login")


def test_homologations_page_renders_for_admin(client: TestClient) -> None:
    cookie = _login(client)
    for path in (
        "/homologations",
        "/customizations",
        "/releases",
        "/modules",
        "/clients",
    ):
        resp = client.get(path, cookies={"cs_session": cookie})
        assert resp.status_code == 200, path
        # The filter bar is rendered on every list page.
        assert 'class="filter-bar"' in resp.text, path


def test_search_filters_homologations(client: TestClient) -> None:
    import cs_web.db as db

    db.homologation.insert(
        {
            "module": "Catálogo de Produtos",
            "status": "Em homologação",
            "homologated": "Sim",
        }
    )
    db.homologation.insert(
        {
            "module": "Estoque Avançado",
            "status": "Pendente",
            "homologated": "Não",
        }
    )
    cookie = _login(client)

    resp = client.get("/homologations?q=estoque", cookies={"cs_session": cookie})
    assert resp.status_code == 200
    assert "Estoque Avançado" in resp.text
    assert "Catálogo de Produtos" not in resp.text

    resp_filter = client.get(
        "/homologations?homologated=Sim", cookies={"cs_session": cookie}
    )
    assert resp_filter.status_code == 200
    assert "Catálogo de Produtos" in resp_filter.text
    assert "Estoque Avançado" not in resp_filter.text


def test_pagination_splits_large_lists(client: TestClient) -> None:
    import cs_web.db as db

    for i in range(25):
        db.clients.insert({"name": f"Cliente {i:02d}"})
    cookie = _login(client)

    page1 = client.get("/clients?page=1", cookies={"cs_session": cookie})
    page2 = client.get("/clients?page=2", cookies={"cs_session": cookie})
    assert page1.status_code == 200
    assert page2.status_code == 200
    # Page 1 has 20 (DEFAULT_PAGE_SIZE), page 2 has the remaining 5.
    assert page1.text.count("<tr>") - 1 == 20  # minus the header row
    assert page2.text.count("<tr>") - 1 == 5
    assert "Página 2 / 2" in page2.text
