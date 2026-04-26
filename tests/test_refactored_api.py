"""Tests for the refactored CS-Controle 360 API.

Tests cover:
1. Standardized envelope responses for each independent module
2. Module-specific /stats endpoints
3. The new /reports/intelligence consolidated endpoint
4. Backward compatibility of existing report endpoints
"""

import os
import pytest
from fastapi.testclient import TestClient

os.environ["CS_ALLOW_INSECURE_SECRETS"] = "1"
os.environ["CS_ADMIN_AUTH_ENABLED"] = "0"
os.environ["PYTHONPATH"] = "."

from backend.main import app

client = TestClient(app)


def _envelope_ok(resp_json: dict, module: str) -> None:
    assert resp_json["status"] == "ok", f"Unexpected status: {resp_json}"
    assert resp_json["module"] == module
    assert "data" in resp_json
    assert "meta" in resp_json
    assert "generated_at" in resp_json["meta"]


# ── Homologação ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestHomologacao:
    def test_list_returns_envelope(self):
        r = client.get("/api/homologacao")
        assert r.status_code == 200
        _envelope_ok(r.json(), "homologacao")
        assert isinstance(r.json()["data"], list)
        assert "count" in r.json()["meta"]

    def test_stats_returns_envelope(self):
        r = client.get("/api/homologacao/stats")
        assert r.status_code == 200
        _envelope_ok(r.json(), "homologacao")
        data = r.json()["data"]
        assert "total" in data
        assert "by_status" in data
        assert "by_module" in data

    def test_crud_lifecycle(self):
        payload = {"module": "TestMod", "status": "pendente", "observation": "Test obs"}
        r = client.post("/api/homologacao", json=payload)
        assert r.status_code == 200
        _envelope_ok(r.json(), "homologacao")
        assert r.json()["meta"].get("action") == "created"
        entity_id = r.json()["data"]["id"]

        r = client.get(f"/api/homologacao/{entity_id}")
        assert r.status_code == 200
        _envelope_ok(r.json(), "homologacao")

        r = client.put(f"/api/homologacao/{entity_id}", json={"observation": "Updated obs"})
        assert r.status_code == 200
        _envelope_ok(r.json(), "homologacao")
        assert r.json()["meta"].get("action") == "updated"

        r = client.delete(f"/api/homologacao/{entity_id}")
        assert r.status_code == 200
        _envelope_ok(r.json(), "homologacao")
        assert r.json()["meta"].get("action") == "deleted"

    def test_get_not_found(self):
        r = client.get("/api/homologacao/999999")
        assert r.status_code == 404


# ── Atividade ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestAtividade:
    def test_list_returns_envelope(self):
        r = client.get("/api/atividade")
        assert r.status_code == 200
        _envelope_ok(r.json(), "atividade")
        assert isinstance(r.json()["data"], list)

    def test_stats(self):
        r = client.get("/api/atividade/stats")
        assert r.status_code == 200
        _envelope_ok(r.json(), "atividade")
        data = r.json()["data"]
        assert "total" in data
        assert "by_tipo" in data
        assert "by_status" in data
        assert "by_owner" in data

    def test_catalogos(self):
        r = client.get("/api/atividade/catalogos")
        assert r.status_code == 200
        _envelope_ok(r.json(), "atividade")
        assert "owners" in r.json()["data"]
        assert "statuses" in r.json()["data"]


# ── Release ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestRelease:
    def test_list_returns_envelope(self):
        r = client.get("/api/release")
        assert r.status_code == 200
        _envelope_ok(r.json(), "release")
        assert isinstance(r.json()["data"], list)

    def test_stats(self):
        r = client.get("/api/release/stats")
        assert r.status_code == 200
        _envelope_ok(r.json(), "release")
        assert "total" in r.json()["data"]


# ── Cliente ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestCliente:
    def test_list_returns_envelope(self):
        r = client.get("/api/cliente")
        assert r.status_code == 200
        _envelope_ok(r.json(), "cliente")

    def test_stats(self):
        r = client.get("/api/cliente/stats")
        assert r.status_code == 200
        _envelope_ok(r.json(), "cliente")
        assert "total" in r.json()["data"]


# ── Módulo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestModulo:
    def test_list_returns_envelope(self):
        r = client.get("/api/modulo")
        assert r.status_code == 200
        _envelope_ok(r.json(), "modulo")

    def test_stats(self):
        r = client.get("/api/modulo/stats")
        assert r.status_code == 200
        _envelope_ok(r.json(), "modulo")
        assert "total" in r.json()["data"]


# ── Customização ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestCustomizacao:
    def test_list_returns_envelope(self):
        r = client.get("/api/customizacao")
        assert r.status_code == 200
        _envelope_ok(r.json(), "customizacao")

    def test_stats(self):
        r = client.get("/api/customizacao/stats")
        assert r.status_code == 200
        _envelope_ok(r.json(), "customizacao")
        assert "total" in r.json()["data"]


# ── Reports / Intelligence Hub ━━━━━━━━━━━━━━━━━━━

class TestReportsIntelligence:
    def test_intelligence_endpoint_returns_envelope(self):
        r = client.get("/api/reports/intelligence")
        assert r.status_code == 200
        body = r.json()
        _envelope_ok(body, "reports")
        data = body["data"]
        assert "pdf_intelligence" in data
        assert "playbooks" in data
        assert "cross_module" in data

    def test_intelligence_pdf_section(self):
        r = client.get("/api/reports/intelligence")
        data = r.json()["data"]["pdf_intelligence"]
        assert "themes" in data
        assert "sections" in data
        assert "knowledge_terms" in data
        assert "predictions" in data
        assert "recommendations" in data
        assert "action_items" in data

    def test_intelligence_playbooks_section(self):
        r = client.get("/api/reports/intelligence")
        data = r.json()["data"]["playbooks"]
        assert "totals" in data
        assert "suggestions" in data
        assert "ranking" in data
        assert "coverage" in data

    def test_intelligence_cross_module_section(self):
        r = client.get("/api/reports/intelligence")
        data = r.json()["data"]["cross_module"]
        assert "totals" in data
        totals = data["totals"]
        for key in ["homologacoes", "customizacoes", "atividades", "releases", "modulos", "clientes"]:
            assert key in totals
        assert "activity_by_status" in data
        assert "module_metrics" in data
        assert isinstance(data["module_metrics"], list)

    def test_intelligence_with_release_filter(self):
        r = client.get("/api/reports/intelligence", params={"release_id": 1})
        assert r.status_code == 200
        _envelope_ok(r.json(), "reports")

    def test_intelligence_meta_contains_filters(self):
        r = client.get("/api/reports/intelligence", params={"release_id": 5, "cycle_id": 2})
        assert r.status_code == 200
        meta = r.json()["meta"]
        assert meta["release_id"] == 5
        assert meta["cycle_id"] == 2


# ── Backward-compatible report endpoints ━━━━━━━━━━━━━━━━━

class TestReportsBackwardCompat:
    def test_ticket_summary(self):
        r = client.get("/api/reports/ticket-summary")
        assert r.status_code == 200

    def test_html_report(self):
        r = client.get("/api/reports/html")
        assert r.status_code == 200
        assert "html" in r.json()

    def test_summary_text(self):
        r = client.get("/api/reports/summary-text")
        assert r.status_code == 200
        assert "report" in r.json()

    def test_cycles(self):
        r = client.get("/api/reports/cycles")
        assert r.status_code == 200


# ── Response.py unit tests ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestResponseHelpers:
    def test_ok(self):
        from backend.response import ok
        result = ok({"foo": "bar"}, module="test")
        assert result["status"] == "ok"
        assert result["module"] == "test"
        assert result["data"] == {"foo": "bar"}
        assert "generated_at" in result["meta"]

    def test_ok_list(self):
        from backend.response import ok_list
        result = ok_list([1, 2, 3], module="test")
        assert result["data"] == [1, 2, 3]
        assert result["meta"]["count"] == 3

    def test_ok_deleted(self):
        from backend.response import ok_deleted
        result = ok_deleted(module="test")
        assert result["data"] is None
        assert result["meta"]["action"] == "deleted"

    def test_ok_with_meta(self):
        from backend.response import ok
        result = ok("value", module="m", meta={"extra": 42})
        assert result["meta"]["extra"] == 42
        assert "generated_at" in result["meta"]
