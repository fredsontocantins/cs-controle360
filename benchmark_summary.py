import time
import os
import json
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import get_conn, run_query

os.environ["CS_ALLOW_INSECURE_SECRETS"] = "1"

def benchmark():
    with TestClient(app) as client:
        # Check initial state
        resp = client.get("/api/summary")
        data = resp.json()
        print(f"Initial counts: {data.get('homologacoes')} homologacoes, {data.get('customizacoes')} customizacoes")
        print(f"Current cycle: {data.get('current_cycle')}")

        # Warm up
        client.get("/api/summary")

        start = time.perf_counter()
        for _ in range(10):
            response = client.get("/api/summary")
        end = time.perf_counter()

        avg_time = (end - start) / 10
        print(f"Average time for /api/summary: {avg_time:.4f}s")

if __name__ == "__main__":
    benchmark()
