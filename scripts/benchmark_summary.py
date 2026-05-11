
import time
import statistics
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import ensure_tables, seed_demo_data_if_needed
import os

# Set environment variable to allow insecure secrets for testing
os.environ["CS_ALLOW_INSECURE_SECRETS"] = "1"

def benchmark_summary(iterations=50):
    client = TestClient(app)
    ensure_tables()
    # seed_demo_data_if_needed() # Ensure some data exists

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        response = client.get("/api/summary")
        end = time.perf_counter()
        assert response.status_code == 200
        times.append(end - start)

    avg_time = statistics.mean(times)
    min_time = min(times)
    max_time = max(times)
    print(f"Benchmark /api/summary ({iterations} iterations):")
    print(f"  Average: {avg_time:.4f}s")
    print(f"  Min:     {min_time:.4f}s")
    print(f"  Max:     {max_time:.4f}s")
    return avg_time

if __name__ == "__main__":
    benchmark_summary()
