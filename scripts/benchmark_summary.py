import time
from backend.main import app
from fastapi.testclient import TestClient
from backend.database import ensure_tables
from backend.services.auth import bootstrap_default_admin

def benchmark():
    ensure_tables()
    bootstrap_default_admin()
    client = TestClient(app)

    # Warmup
    client.get("/api/summary")

    iterations = 50
    start = time.perf_counter()
    for _ in range(iterations):
        resp = client.get("/api/summary")
        assert resp.status_code == 200
    elapsed = time.perf_counter() - start

    avg_time = (elapsed / iterations) * 1000
    print(f"Summary Endpoint: {iterations} requests took {elapsed:.4f}s (Average: {avg_time:.2f} ms/req)")

if __name__ == "__main__":
    benchmark()
