
import time
import os
import sys
import json
from datetime import datetime, timedelta

# Mock environment
os.environ["CS_ADMIN_AUTH_ENABLED"] = "0"
os.environ["CS_ALLOW_INSECURE_SECRETS"] = "1"
os.environ["PYTHONPATH"] = "."

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import ensure_tables, reset_application_data, get_conn, run_query

def seed_data(num_records=1000):
    print(f"Seeding {num_records} records...")
    conn = get_conn()

    # Seed clients and modules
    run_query(conn, "INSERT INTO clients (name, created_at) VALUES (?, ?)", ("Benchmark Client", datetime.utcnow().isoformat()))
    run_query(conn, "INSERT INTO modules (name, created_at) VALUES (?, ?)", ("Benchmark Module", datetime.utcnow().isoformat()))
    conn.commit()

    client_id = 1
    module_id = 1

    # Seed activities
    activities = []
    base_date = datetime.utcnow()
    for i in range(num_records):
        status = "concluida" if i % 2 == 0 else "pendente"
        created_at = (base_date - timedelta(days=i%30)).isoformat()
        activities.append((
            f"Activity {i}", 1, 1, "Owner A" if i % 3 == 0 else "Owner B",
            "Executor X" if i % 4 == 0 else "Executor Y", status, created_at, created_at
        ))

    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO activities (title, client_id, module_id, owner, executor, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        activities
    )

    # Seed homologacoes
    homols = []
    for i in range(num_records // 10):
        created_at = (base_date - timedelta(days=i%30)).isoformat()
        homols.append(("Module X", 1, "pendente", created_at))
    cur.executemany(
        "INSERT INTO homologacao (module, module_id, status, created_at) VALUES (?, ?, ?, ?)",
        homols
    )

    conn.commit()
    conn.close()
    print("Seeding complete.")

def benchmark_summary(iterations=5):
    client = TestClient(app)
    latencies = []

    print(f"Running benchmark for /api/summary ({iterations} iterations)...")
    for i in range(iterations):
        start = time.time()
        response = client.get("/api/summary")
        end = time.time()
        latencies.append(end - start)
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)

    avg_latency = sum(latencies) / len(latencies)
    print(f"Average latency: {avg_latency:.4f}s")
    return avg_latency

if __name__ == "__main__":
    ensure_tables()
    reset_application_data()

    num_records = 1000
    if len(sys.argv) > 1:
        num_records = int(sys.argv[1])

    seed_data(num_records)
    benchmark_summary()
