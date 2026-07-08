import time
import statistics
from fastapi.testclient import TestClient
import os

# Set environment variables for testing
os.environ["CS_ALLOW_INSECURE_SECRETS"] = "1"
os.environ["PYTHONPATH"] = "."

from backend.main import app

def benchmark():
    with TestClient(app) as client:
        # Warmup
        for _ in range(5):
            client.get("/api/summary")

        times = []
        for _ in range(50):
            start = time.perf_counter()
            response = client.get("/api/summary")
            end = time.perf_counter()
            if response.status_code == 200:
                times.append((end - start) * 1000)
            else:
                print(f"Error: {response.status_code} - {response.text}")

        if times:
            print(f"Mean: {statistics.mean(times):.2f}ms")
            print(f"Median: {statistics.median(times):.2f}ms")
            print(f"Min: {min(times):.2f}ms")
            print(f"Max: {max(times):.2f}ms")

if __name__ == "__main__":
    benchmark()
