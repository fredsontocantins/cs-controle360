import time
from fastapi.testclient import TestClient
from backend.main import app
import os

# Bypass security checks
os.environ["CS_ALLOW_INSECURE_SECRETS"] = "1"

client = TestClient(app)

def benchmark_summary():
    # Ensure tables are created and seeded
    with client:
        # Warm up
        client.get("/api/summary")

        start = time.perf_counter()
        iterations = 20
        for _ in range(iterations):
            response = client.get("/api/summary")
            assert response.status_code == 200
        end = time.perf_counter()

        avg_time = (end - start) / iterations
        print(f"Average time for /api/summary: {avg_time:.4f}s")

if __name__ == "__main__":
    benchmark_summary()
