"""Benchmark for /api/reports/intelligence endpoint."""
import time
import os
os.environ["CS_ALLOW_INSECURE_SECRETS"] = "1"
os.environ["CS_ADMIN_AUTH_ENABLED"] = "0"

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import ensure_tables

def benchmark():
    ensure_tables()
    client = TestClient(app)

    # Warmup
    client.get("/api/reports/intelligence")

    start = time.perf_counter()
    iterations = 20
    for _ in range(iterations):
        res = client.get("/api/reports/intelligence")
        assert res.status_code == 200
    elapsed = time.perf_counter() - start
    avg = (elapsed / iterations) * 1000
    print(f"Average response time for /api/reports/intelligence across {iterations} requests: {avg:.2f}ms")

if __name__ == "__main__":
    benchmark()
