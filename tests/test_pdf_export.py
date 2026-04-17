"""Regression tests for the admin PDF export.

These tests cover two bugs that surfaced in production:

1. ``FPDFUnicodeEncodingException`` when the payload (or static copy) contained
   characters outside latin-1 such as an em dash (``—``) or bullet (``•``).
2. ``AttributeError: 'bytearray' object has no attribute 'encode'`` triggered
   by the legacy ``.encode("latin-1")`` call on fpdf2's ``output()``.
"""

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


def test_pdf_safe_rewrites_unicode_punctuation() -> None:
    from cs_web.main import _pdf_safe

    # em dash, en dash, bullet, smart quotes all get rewritten.
    assert _pdf_safe("foo \u2014 bar \u2013 baz") == "foo - bar - baz"
    assert _pdf_safe("\u2022 item") == "- item"
    assert _pdf_safe("\u201cquoted\u201d") == '"quoted"'
    # Accented chars that already fit in latin-1 pass through unchanged.
    assert _pdf_safe("Relat\u00f3rio") == "Relat\u00f3rio"
    # None/numbers don't crash.
    assert _pdf_safe(None) == ""
    assert _pdf_safe(42) == "42"


def test_render_export_pdf_handles_unicode_payload() -> None:
    from cs_web.main import _render_export_pdf

    payload = {
        "homologation": [
            {
                "module": "Cat\u00e1logo",
                "client": "ACME \u2014 Corp",
                "status": "Em Andamento",
                "requested_production_date": None,
                "production_date": None,
            }
        ],
        "customizations": [
            {
                "proposal": "095/2025",
                "client": "ACME",
                "stage": "aprovadas",
                "value": 1234.5,
            }
        ],
        "releases": [
            {
                "release_name": "Release 3.45",
                "module": "Cat\u00e1logo",
                "applies_on": None,
                "client": "ACME \u2014 Corp",
            }
        ],
        "clients": [],
        "modules": [],
    }

    data = _render_export_pdf(payload)

    assert isinstance(data, (bytes, bytearray))
    assert bytes(data).startswith(b"%PDF"), "output must be a valid PDF"


def test_admin_export_pdf_endpoint_returns_pdf(client: TestClient) -> None:
    cookie = _login(client)
    resp = client.get("/admin/export?format=pdf", cookies={"cs_session": cookie})
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("application/pdf")
    assert resp.content.startswith(b"%PDF")
