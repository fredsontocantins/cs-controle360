import time
import requests
import json
import sys
import os

# Add parent directory to path to allow importing from backend
sys.path.append(os.getcwd())

from backend.database import ensure_tables, get_conn, run_query
from backend.models.atividade import insert_atividade
from backend.models.homologacao import insert_homologacao
from backend.models.customizacao import insert_customizacao
from backend.models.release import insert_release
from backend.models.report_cycle import open_cycle

def setup_benchmark_data(count=1000):
    ensure_tables()
    print(f"Setting up {count} records for benchmark...")

    # Create a cycle
    cycle_id = open_cycle("reports", None, "Benchmark Cycle", "Benchmark Period")

    for i in range(count):
        if i % 100 == 0:
            print(f"Inserted {i} records...")

        insert_homologacao({
            "module": f"Module {i%10}",
            "status": "Finalizado",
            "check_date": "2023-01-01",
            "created_at": "2023-01-01T00:00:00"
        })

        insert_atividade({
            "title": f"Activity {i}",
            "owner": "Bolt",
            "executor": "Bolt",
            "status": "concluida",
            "created_at": "2023-01-01T00:00:00",
            "completed_at": "2023-01-01T00:00:00"
        })

        # Add some variety in owners
        if i % 10 == 0:
            insert_atividade({
                "title": f"Other Activity {i}",
                "owner": "Jules",
                "executor": "Jules",
                "status": "concluida",
                "created_at": "2023-01-01T00:00:00",
                "completed_at": "2023-01-01T00:00:00"
            })

def run_benchmark():
    # Use a dummy environment to avoid needing a real server if possible,
    # but since it's a FastAPI app, we can use TestClient
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)

    print("Running benchmark for /api/summary...")
    start_time = time.time()
    response = client.get("/api/summary")
    end_time = time.time()

    if response.status_code == 200:
        print(f"Success! Response time: {end_time - start_time:.4f} seconds")
        # print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    # Clear DB first if needed
    if os.path.exists("backend/data/controle360.db"):
        os.remove("backend/data/controle360.db")

    setup_benchmark_data(500) # Start with 500
    run_benchmark()

    setup_benchmark_data(1500) # Add more
    run_benchmark()
