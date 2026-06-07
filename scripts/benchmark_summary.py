
import time
import os
import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

# Set environment variables before importing the app
os.environ["CS_ADMIN_AUTH_ENABLED"] = "0"
os.environ["CS_ALLOW_INSECURE_SECRETS"] = "1"

from backend.main import app
from backend.database import ensure_tables, get_conn, run_query
from backend.config import TABLE_ATIVIDADE, TABLE_HOMOLOGACAO, TABLE_CUSTOMIZACAO, TABLE_RELEASE, TABLE_REPORT_CYCLE

client = TestClient(app)

def seed_data(num_records=1250):
    ensure_tables()
    conn = get_conn()
    now = datetime.utcnow()

    print(f"Seeding {num_records} records per table...")

    # Create a cycle
    run_query(conn, f"DELETE FROM {TABLE_REPORT_CYCLE}")
    run_query(conn, f"INSERT INTO {TABLE_REPORT_CYCLE} (scope_type, cycle_number, status, created_at, opened_at) VALUES (?, ?, ?, ?, ?)",
              ("reports", 1, "aberto", (now - timedelta(days=30)).isoformat(), (now - timedelta(days=30)).isoformat()))

    # Activities
    run_query(conn, f"DELETE FROM {TABLE_ATIVIDADE}")
    activities = []
    for i in range(num_records):
        status = "concluida" if i % 2 == 0 else "backlog"
        owner = f"Owner {i % 10}"
        created_at = (now - timedelta(days=i % 60)).isoformat()
        activities.append(("Task %d" % i, owner, owner, status, created_at, created_at))

    if os.getenv("DATABASE_URL"):
        with conn.cursor() as cur:
            cur.executemany(f"INSERT INTO {TABLE_ATIVIDADE} (title, owner, executor, status, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s)", activities)
    else:
        conn.executemany(f"INSERT INTO {TABLE_ATIVIDADE} (title, owner, executor, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)", activities)

    # Homologacao
    run_query(conn, f"DELETE FROM {TABLE_HOMOLOGACAO}")
    homologacoes = []
    for i in range(num_records):
        check_date = (now - timedelta(days=i % 60)).isoformat()
        homologacoes.append(("Module %d" % i, "Status", check_date, check_date))

    if os.getenv("DATABASE_URL"):
        with conn.cursor() as cur:
            cur.executemany(f"INSERT INTO {TABLE_HOMOLOGACAO} (module, status, check_date, created_at) VALUES (%s, %s, %s, %s)", homologacoes)
    else:
        conn.executemany(f"INSERT INTO {TABLE_HOMOLOGACAO} (module, status, check_date, created_at) VALUES (?, ?, ?, ?)", homologacoes)

    # Customizacao
    run_query(conn, f"DELETE FROM {TABLE_CUSTOMIZACAO}")
    customizacoes = []
    for i in range(num_records):
        created_at = (now - timedelta(days=i % 60)).isoformat()
        customizacoes.append(("Subject %d" % i, "Stage", created_at))

    if os.getenv("DATABASE_URL"):
        with conn.cursor() as cur:
            cur.executemany(f"INSERT INTO {TABLE_CUSTOMIZACAO} (subject, stage, created_at) VALUES (%s, %s, %s)", customizacoes)
    else:
        conn.executemany(f"INSERT INTO {TABLE_CUSTOMIZACAO} (subject, stage, created_at) VALUES (?, ?, ?)", customizacoes)

    # Releases
    run_query(conn, f"DELETE FROM {TABLE_RELEASE}")
    releases = []
    for i in range(num_records):
        created_at = (now - timedelta(days=i % 60)).isoformat()
        releases.append(("Release %d" % i, "1.0.%d" % i, created_at))

    if os.getenv("DATABASE_URL"):
        with conn.cursor() as cur:
            cur.executemany(f"INSERT INTO {TABLE_RELEASE} (release_name, version, created_at) VALUES (%s, %s, %s)", releases)
    else:
        conn.executemany(f"INSERT INTO {TABLE_RELEASE} (release_name, version, created_at) VALUES (?, ?, ?)", releases)

    conn.commit()
    conn.close()
    print("Seeding complete.")

def run_benchmark(iterations=5):
    print(f"Running benchmark ({iterations} iterations)...")
    latencies = []
    for i in range(iterations):
        start = time.time()
        response = client.get("/api/summary")
        end = time.time()
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            continue
        latencies.append(end - start)
        print(f"Iteration {i+1}: {end - start:.4f}s")

    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        print(f"Average latency: {avg_latency:.4f}s")
    else:
        print("No successful iterations.")

if __name__ == "__main__":
    seed_data(1250) # 5000 records total
    run_benchmark(5)
