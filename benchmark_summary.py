import time
import statistics
from fastapi.testclient import TestClient
from backend.main import app
import os

# Set environment variables for testing
os.environ["CS_ALLOW_INSECURE_SECRETS"] = "1"
os.environ["CS_ADMIN_AUTH_ENABLED"] = "0"

def benchmark():
    client = TestClient(app)
    # Ensure startup events are run
    with client:
        # Warmup
        client.get("/api/summary")

        times = []
        for _ in range(50):
            start = time.perf_counter()
            response = client.get("/api/summary")
            end = time.perf_counter()
            if response.status_code == 200:
                times.append(end - start)
            else:
                print(f"Error: {response.status_code}")

        if times:
            print(f"Mean: {statistics.mean(times):.6f}s")
            print(f"Median: {statistics.median(times):.6f}s")
            print(f"Min: {min(times):.6f}s")
            print(f"Max: {max(times):.6f}s")

if __name__ == "__main__":
    benchmark()
