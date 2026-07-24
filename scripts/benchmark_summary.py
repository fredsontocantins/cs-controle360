import time
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import ensure_tables
from backend.services.auth import bootstrap_default_admin

# Initialize and bootstrap
ensure_tables()
try:
    bootstrap_default_admin()
except Exception:
    pass

client = TestClient(app)

def run_benchmark():
    # Warm up
    client.get("/api/summary")

    start_time = time.perf_counter()
    iterations = 200
    for _ in range(iterations):
        client.get("/api/summary")
    end_time = time.perf_counter()

    elapsed = end_time - start_time
    avg_time_ms = (elapsed / iterations) * 1000
    print(f"Benchmark: 200 requests to /api/summary took {elapsed:.4f}s (Average: {avg_time_ms:.2f}ms per request)")

if __name__ == "__main__":
    run_benchmark()
