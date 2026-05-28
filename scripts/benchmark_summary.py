import time
import requests
import json
import os
import sys
from datetime import datetime

# Add root to sys.path
sys.path.append(os.getcwd())

from backend.database import get_conn, run_query, ensure_tables
from backend.config import TABLE_ATIVIDADE

def seed_data(count=10000):
    print(f"Seeding {count} activities...")
    ensure_tables()
    conn = get_conn()
    now = datetime.utcnow().isoformat()

    # Bulk insert for speed
    activities = []
    for i in range(count):
        activities.append((
            f"Activity {i}",
            f"Owner {i % 5}",
            f"Executor {i % 5}",
            "concluida" if i % 2 == 0 else "backlog",
            now,
            now,
            now if i % 2 == 0 else None
        ))

    if os.getenv("DATABASE_URL"):
        with conn.cursor() as cur:
            cur.executemany(
                f"INSERT INTO {TABLE_ATIVIDADE} (title, owner, executor, status, created_at, updated_at, completed_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                activities
            )
    else:
        conn.executemany(
            f"INSERT INTO {TABLE_ATIVIDADE} (title, owner, executor, status, created_at, updated_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            activities
        )
    conn.commit()
    conn.close()
    print("Seeding complete.")

def benchmark_summary():
    # We use the internal function since the server might not be running
    from backend.main import get_summary
    import asyncio

    print("Benchmarking /api/summary...")
    start_time = time.time()

    # Run get_summary (it's an async function)
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(get_summary())

    end_time = time.time()
    duration = end_time - start_time
    print(f"Summary response time: {duration:.4f} seconds")
    # print(f"Result: {json.dumps(result, indent=2)}")
    return duration

if __name__ == "__main__":
    # Ensure we use a local test DB if no DATABASE_URL
    if not os.getenv("DATABASE_URL"):
        os.environ["CS_ALLOW_INSECURE_SECRETS"] = "1"
        if os.path.exists("backend/data/controle360.db"):
             os.remove("backend/data/controle360.db")

    seed_data(50000)
    benchmark_summary()
