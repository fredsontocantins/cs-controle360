import time
import requests

def benchmark_summary():
    # We need to start the server first or use TestClient
    # For simplicity, let's try to use the app directly with TestClient if possible,
    # but here I'll just assume the server might be running or I'll run it in background.

    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)

    # Warmup
    client.get("/api/summary")

    start = time.time()
    for _ in range(10):
        client.get("/api/summary")
    end = time.time()

    avg_time = (end - start) / 10
    print(f"Average time for /api/summary: {avg_time:.4f}s")

if __name__ == "__main__":
    benchmark_summary()
