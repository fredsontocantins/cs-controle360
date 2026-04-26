import pytest
import os
from httpx import AsyncClient, ASGITransport
from backend.database import ensure_tables

# Set auth disabled before importing app if possible, or use dependency override
os.environ["CS_ADMIN_AUTH_ENABLED"] = "0"
from backend.main import app

@pytest.fixture(autouse=True)
def setup_db():
    ensure_tables()

@pytest.mark.asyncio
async def test_read_homologacao():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/homologacao")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": "2.0.0"}
