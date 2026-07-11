
import os
import time
import requests
import sqlite3
from datetime import datetime

# Set environment variables for testing
os.environ["DATABASE_URL"] = "" # Use SQLite for local benchmark
os.environ["CS_ADMIN_AUTH_ENABLED"] = "0"

# Assuming the server is running or we can call the functions directly
# For simplicity in this environment, I'll use the functions directly if possible,
# but it might be easier to use the TestClient if I can.

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import get_conn, run_query, ensure_tables, reset_application_data

client = TestClient(app)

def seed_data(count=1000):
    print(f"Seeding {count} activities...")
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    activities = []
    for i in range(count):
        activities.append((
            f"Task {i}",
            f"Owner {i % 10}",
            f"Executor {i % 5}",
            "concluida" if i % 2 == 0 else "backlog",
            now,
            now,
            now if i % 2 == 0 else None
        ))

    # Using raw SQL for speed of seeding
    conn.executemany(
        "INSERT INTO activities (title, owner, executor, status, created_at, updated_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        activities
    )
    conn.commit()
    conn.close()
    print("Done seeding.")

def benchmark_summary():
    start_time = time.time()
    response = client.get("/api/summary")
    end_time = time.time()

    if response.status_code == 200:
        print(f"Summary took {end_time - start_time:.4f} seconds")
        # print(response.json())
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    ensure_tables()
    reset_application_data()
    seed_data(2000)
    benchmark_summary()
    benchmark_summary()
    benchmark_summary()
