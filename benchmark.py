import time
import os
import json
from fastapi.testclient import TestClient

os.environ["CS_ALLOW_INSECURE_SECRETS"] = "1"
os.environ["CS_ADMIN_AUTH_ENABLED"] = "0"
os.environ["CS_RESET_SAMPLE_DATA_ON_STARTUP"] = "1"

from backend.main import app
from backend.models.atividade import insert_atividade

client = TestClient(app)

def benchmark_summary():
    print("Seeding 1000 activities...")
    # Seed 1000 activities
    for i in range(1000):
        insert_atividade({
            "title": f"Activity {i}",
            "status": "concluida" if i % 2 == 0 else "backlog",
            "owner": "Bolt",
            "executor": "Bolt"
        })

    print("Data seeded. Running benchmark...")

    times = []
    for _ in range(5):
        start_time = time.time()
        response = client.get("/api/summary")
        end_time = time.time()
        times.append(end_time - start_time)
        print(f"Summary response time: {end_time - start_time:.4f}s")

    print(f"Average response time: {sum(times)/len(times):.4f}s")
    assert response.status_code == 200
    data = response.json()
    assert "atividades" in data
    assert data["atividades"] == 1000
    assert "completed_tasks_total" in data
    assert data["completed_tasks_total"] == 500

if __name__ == "__main__":
    benchmark_summary()
