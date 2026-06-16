import time
import requests
import json
import os
import sys

# Add backend to path so we can use models if needed, but we'll use API
sys.path.append(os.getcwd())

def seed_data(count=1000):
    from backend.database import get_conn, TABLE_ATIVIDADE, TABLE_HOMOLOGACAO, TABLE_CUSTOMIZACAO, TABLE_RELEASE, TABLE_REPORT_CYCLE
    from datetime import datetime, timedelta

    conn = get_conn()
    print(f"Seeding {count} records into each table...")

    # Create a cycle
    now = datetime.utcnow()
    start_date = (now - timedelta(days=30)).isoformat()
    conn.execute(f"INSERT INTO {TABLE_REPORT_CYCLE} (scope_type, scope_id, cycle_number, period_label, status, opened_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 ("reports", 1, 1, "Benchmark Cycle", "aberto", start_date, start_date))

    # Seed activities
    activities = []
    for i in range(count):
        activities.append((f"Activity {i}", "concluida", "Owner A", "Executor A", (now - timedelta(days=5)).isoformat()))

    if "postgres" in str(type(conn)).lower():
        cur = conn.cursor()
        cur.executemany(f"INSERT INTO {TABLE_ATIVIDADE} (title, status, owner, executor, completed_at, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                        [(*a, a[4]) for a in activities])
    else:
        conn.executemany(f"INSERT INTO {TABLE_ATIVIDADE} (title, status, owner, executor, completed_at, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        [(*a, a[4]) for a in activities])

    # Seed other tables
    other_tables = [TABLE_HOMOLOGACAO, TABLE_CUSTOMIZACAO, TABLE_RELEASE]
    for table in other_tables:
        items = []
        for i in range(count):
            items.append((f"Item {i}", (now - timedelta(days=5)).isoformat()))

        if "postgres" in str(type(conn)).lower():
            cur = conn.cursor()
            cur.executemany(f"INSERT INTO {table} (created_at, updated_at) VALUES (%s, %s)", items) # Adjust columns per table if needed
        else:
            # Most tables have created_at. Let's just use it.
            if table == TABLE_HOMOLOGACAO:
                conn.executemany(f"INSERT INTO {table} (module, created_at) VALUES (?, ?)", items)
            elif table == TABLE_CUSTOMIZACAO:
                conn.executemany(f"INSERT INTO {table} (subject, created_at) VALUES (?, ?)", items)
            elif table == TABLE_RELEASE:
                conn.executemany(f"INSERT INTO {table} (release_name, created_at) VALUES (?, ?)", items)

    conn.commit()
    conn.close()
    print("Seeding complete.")

def run_benchmark():
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.database import ensure_tables, reset_application_data

    ensure_tables()
    reset_application_data()
    seed_data(10000)

    client = TestClient(app)

    print("Starting benchmark...")
    # Warm up
    client.get("/api/summary")

    start_time = time.time()
    response = client.get("/api/summary")
    end_time = time.time()

    if response.status_code == 200:
        print(f"Summary response time (40k total records): {end_time - start_time:.4f} seconds")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    os.environ["CS_ADMIN_AUTH_ENABLED"] = "0"
    os.environ["CS_ALLOW_INSECURE_SECRETS"] = "1"
    run_benchmark()
