
import time
import requests
import sqlite3
import os
from datetime import datetime, timedelta

API_URL = "http://localhost:8000/api/summary"
DB_PATH = "backend/data/database.sqlite" # Adjust if necessary

def seed_data(num_records=1000):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"Seeding {num_records} activities...")
    now = datetime.utcnow()
    for i in range(num_records):
        created_at = (now - timedelta(days=i % 30)).isoformat()
        cursor.execute(
            "INSERT INTO activities (title, status, owner, executor, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (f"Task {i}", "concluida" if i % 2 == 0 else "backlog", f"Owner {i % 10}", f"Executor {i % 10}", created_at, created_at)
        )

    # Also seed a cycle to make sure cycle filtering is exercised
    cursor.execute(
        "INSERT INTO report_cycles (scope_type, cycle_number, status, created_at, opened_at) VALUES (?, ?, ?, ?, ?)",
        ("reports", 1, "aberto", (now - timedelta(days=15)).isoformat(), (now - timedelta(days=15)).isoformat())
    )

    conn.commit()
    conn.close()

def measure_api():
    try:
        start_time = time.time()
        response = requests.get(API_URL)
        end_time = time.time()

        if response.status_code == 200:
            print(f"API Response Time: {end_time - start_time:.4f} seconds")
            # print(response.json())
        else:
            print(f"API Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    # This script assumes the server is running.
    # For a local benchmark without a running server, we might need to call the function directly.
    pass
