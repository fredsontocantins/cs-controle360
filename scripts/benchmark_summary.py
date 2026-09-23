import time
import os

os.environ["CS_ALLOW_INSECURE_SECRETS"] = "1"
os.environ["CS_ADMIN_AUTH_ENABLED"] = "0"
os.environ["PYTHONPATH"] = "."

from backend.database import ensure_tables, seed_demo_data_if_needed
from backend.main import get_summary
from fastapi.testclient import TestClient
from backend.main import app

ensure_tables()
seed_demo_data_if_needed()

client = TestClient(app)

def run_benchmark():
    # Warmup
    client.get("/api/summary")

    iterations = 50
    start = time.perf_counter()
    for _ in range(iterations):
        resp = client.get("/api/summary")
        assert resp.status_code == 200
    elapsed = time.perf_counter() - start

    avg_ms = (elapsed / iterations) * 1000
    print(f"Benchmark /api/summary: {iterations} requests took {elapsed:.4f}s (avg: {avg_ms:.2f}ms/req)")

if __name__ == "__main__":
    run_benchmark()
