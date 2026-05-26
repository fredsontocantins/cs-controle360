import time
import requests
import json
import sqlite3
from datetime import datetime, timedelta
import os
import subprocess

DB_PATH = 'backend/data/controle360.db'

def seed_data(num_records=10000):
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    # Let the app create tables first
    env = os.environ.copy()
    env["CS_ADMIN_AUTH_ENABLED"] = "0"
    env["CS_ALLOW_INSECURE_SECRETS"] = "1"

    # Trigger table creation by running a small script that imports ensure_tables
    subprocess.run(["python3", "-c", "from backend.database import ensure_tables; ensure_tables()"], env=env)

    conn = sqlite3.connect(DB_PATH)
    now = datetime.utcnow()

    # Create a cycle
    cycle_start = now - timedelta(days=30)
    conn.execute("INSERT INTO report_cycles (scope_type, cycle_number, status, created_at, opened_at) VALUES (?, ?, ?, ?, ?)",
                 ('reports', 1, 'aberto', cycle_start.isoformat(), cycle_start.isoformat()))

    # Seed activities
    print(f"Seeding {num_records} activities...")
    activities = []
    for i in range(num_records):
        created_at = (now - timedelta(days=i % 60)).isoformat()
        activities.append((f"Activity {i}", "concluida", "Bolt", "Bolt", created_at, created_at, created_at))

    conn.executemany("INSERT INTO activities (title, status, owner, executor, created_at, updated_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?)", activities)

    # Seed homologacoes
    print(f"Seeding {num_records} homologacoes...")
    homologacoes = []
    for i in range(num_records):
        check_date = (now - timedelta(days=i % 60)).isoformat()
        homologacoes.append((f"Module {i}", "homologado", check_date, check_date))

    conn.executemany("INSERT INTO homologacao (module, status, check_date, created_at) VALUES (?, ?, ?, ?)", homologacoes)

    conn.commit()
    conn.close()
    print(f"Seeded {num_records} records.")

def benchmark_summary():
    # Note: Backend must be running
    try:
        start_time = time.time()
        response = requests.get("http://localhost:8000/api/summary")
        end_time = time.time()

        if response.status_code == 200:
            print(f"Summary response time: {end_time - start_time:.4f} seconds")
            data = response.json()
            print(f"Total Activities: {data['atividades']}")
            print(f"Completed Tasks: {data['completed_tasks_total']}")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error connecting to backend: {e}")

if __name__ == "__main__":
    seed_data(10000)

    # Start server
    print("Starting server...")
    env = os.environ.copy()
    env["CS_ADMIN_AUTH_ENABLED"] = "0"
    env["CS_ALLOW_INSECURE_SECRETS"] = "1"
    server_proc = subprocess.Popen(["uvicorn", "backend.main:app", "--port", "8000"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    time.sleep(5)

    try:
        benchmark_summary()
    finally:
        server_proc.terminate()
        print("Server stopped.")
