import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import ensure_tables
from backend.services.auth import bootstrap_default_admin

# Ensure tables and admin exist before tests
ensure_tables()
bootstrap_default_admin()

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": "2.0.0"}

def test_summary():
    response = client.get("/api/summary")
    # Should be 200 since ensure_tables was called
    assert response.status_code == 200

def test_auth_login_fail():
    response = client.post("/api/auth/login", json={"username": "wrong", "password": "password"})
    assert response.status_code == 401
