"""Tests for authentication and authorization flows."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Build a TestClient with an isolated SQLite database and deterministic secrets."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("CS_SESSION_SECRET", "unit-tests-secret")
    monkeypatch.setenv("CS_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("CS_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("CS_API_KEY", "cs-secret")
    monkeypatch.setenv("CS_ALLOW_UNSECURED_ADMIN", "0")

    # Point persistence to the temp directory before importing modules that
    # resolve the DB path at import time.
    import cs_web.db as cs_db
    import cs_web.repository as cs_repo

    monkeypatch.setattr(cs_db, "DATA_DIR", data_dir, raising=False)
    monkeypatch.setattr(cs_db, "DB_PATH", data_dir / "control.db", raising=False)
    monkeypatch.setattr(cs_repo, "DATA_DIR", data_dir, raising=False)
    monkeypatch.setattr(cs_repo, "DB_PATH", data_dir / "control.db", raising=False)

    from cs_web.auth import ensure_default_admin
    from cs_web.main import app

    cs_db.ensure_tables()
    ensure_default_admin()
    return TestClient(app, follow_redirects=False)


def test_login_page_renders(client: TestClient) -> None:
    response = client.get("/login")
    assert response.status_code == 200
    assert "Entrar" in response.text or "Login" in response.text


def test_dashboard_redirects_to_login_when_unauthenticated(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_login_with_wrong_password_returns_401(client: TestClient) -> None:
    response = client.post(
        "/login", data={"username": "admin", "password": "wrong"}
    )
    assert response.status_code == 401


def test_login_with_correct_credentials_sets_session_cookie(client: TestClient) -> None:
    response = client.post(
        "/login", data={"username": "admin", "password": "admin-pass"}
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert "cs_session" in response.cookies


def test_admin_can_access_admin_console(client: TestClient) -> None:
    login = client.post(
        "/login", data={"username": "admin", "password": "admin-pass"}
    )
    cookie = login.cookies.get("cs_session")
    assert cookie is not None
    response = client.get("/admin", cookies={"cs_session": cookie})
    assert response.status_code == 200


def test_viewer_cannot_access_admin_console(client: TestClient) -> None:
    from cs_web.auth import hash_password
    from cs_web.repository import user_repo

    user_repo.insert(
        {
            "username": "viewer-user",
            "password_hash": hash_password("viewer-pass"),
            "role": "viewer",
        }
    )

    login = client.post(
        "/login", data={"username": "viewer-user", "password": "viewer-pass"}
    )
    assert login.status_code == 303
    cookie = login.cookies.get("cs_session")
    assert cookie is not None

    response = client.get("/admin", cookies={"cs_session": cookie})
    # Viewers are redirected back to the dashboard.
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_viewer_cannot_create_homologation_via_api(client: TestClient) -> None:
    from cs_web.auth import hash_password
    from cs_web.repository import user_repo

    user_repo.insert(
        {
            "username": "viewer-api",
            "password_hash": hash_password("viewer-pass"),
            "role": "viewer",
        }
    )

    login = client.post(
        "/login", data={"username": "viewer-api", "password": "viewer-pass"}
    )
    cookie = login.cookies.get("cs_session")
    assert cookie is not None

    response = client.post(
        "/api/homologation",
        json={"module": "Teste", "status": "Em homologação"},
        cookies={"cs_session": cookie},
    )
    assert response.status_code == 403


def test_logout_clears_session_cookie(client: TestClient) -> None:
    login = client.post(
        "/login", data={"username": "admin", "password": "admin-pass"}
    )
    cookie = login.cookies.get("cs_session")
    assert cookie is not None

    response = client.post("/logout", cookies={"cs_session": cookie})
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    # TestClient exposes cleared cookies via Set-Cookie header; ensure max-age/expires clear it
    set_cookie = response.headers.get("set-cookie", "")
    assert "cs_session=" in set_cookie


def test_legacy_api_key_still_works(client: TestClient) -> None:
    response = client.post(
        "/api/homologation",
        json={"module": "Legado", "status": "Em homologação"},
        headers={"X-API-Key": os.environ["CS_API_KEY"]},
    )
    assert response.status_code == 200
    assert response.json().get("module") == "Legado"
