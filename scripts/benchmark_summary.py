
import time
import statistics
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import ensure_tables, reset_application_data, seed_demo_data_if_needed, _seed_activity_catalogs
from backend.services.auth import bootstrap_default_admin
import os

# Set environment variables for testing
os.environ["CS_ALLOW_INSECURE_SECRETS"] = "1"
os.environ["DATABASE_URL"] = "" # Use SQLite

def setup_db():
    ensure_tables()
    reset_application_data()
    _seed_activity_catalogs()
    try:
        bootstrap_default_admin()
    except Exception as e:
        print(f"Warning: Could not bootstrap admin: {e}")
    seed_demo_data_if_needed()

def benchmark_summary(iterations=100):
    client = TestClient(app)

    # Warmup
    client.get("/api/summary")

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        response = client.get("/api/summary")
        end = time.perf_counter()
        if response.status_code == 200:
            times.append((end - start) * 1000) # ms

    if not times:
        print("Error: All requests failed")
        return

    print(f"Benchmark Results ({iterations} iterations):")
    print(f"  Mean:   {statistics.mean(times):.2f} ms")
    print(f"  Median: {statistics.median(times):.2f} ms")
    print(f"  Min:    {min(times):.2f} ms")
    print(f"  Max:    {max(times):.2f} ms")

if __name__ == "__main__":
    setup_db()
    benchmark_summary()
