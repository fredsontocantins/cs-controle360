import time
import requests
import json
import sqlite3
from datetime import datetime, timedelta

def seed_data(num_records=1000):
    conn = sqlite3.connect('backend/data/controle360.db')

    # Clear existing data to have a clean benchmark
    tables = ['activities', 'homologacao', 'customizations', 'releases', 'report_cycles']
    for table in tables:
        conn.execute(f"DELETE FROM {table}")

    now = datetime.utcnow()

    # Create a cycle
    cycle_start = now - timedelta(days=30)
    conn.execute("INSERT INTO report_cycles (scope_type, cycle_number, status, created_at, opened_at) VALUES (?, ?, ?, ?, ?)",
                 ('reports', 1, 'aberto', cycle_start.isoformat(), cycle_start.isoformat()))

    # Seed activities
    activities = []
    for i in range(num_records):
        created_at = (now - timedelta(days=i % 60)).isoformat()
        activities.append((f"Activity {i}", "concluida", "Bolt", "Bolt", created_at, created_at, created_at))

    conn.executemany("INSERT INTO activities (title, status, owner, executor, created_at, updated_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?)", activities)

    # Seed homologacao
    homologacao = []
    for i in range(num_records):
        check_date = (now - timedelta(days=i % 60)).isoformat()
        homologacao.append((f"Module {i}", "homologado", check_date, check_date))

    conn.executemany("INSERT INTO homologacao (module, status, check_date, created_at) VALUES (?, ?, ?, ?)", homologacao)

    conn.commit()
    conn.close()
    print(f"Seeded {num_records} records into activities and homologacao.")

def benchmark_summary():
    # Note: Backend must be running
    try:
        start_time = time.time()
        response = requests.get("http://localhost:8000/api/summary")
        end_time = time.time()

        if response.status_code == 200:
            print(f"Summary response time: {end_time - start_time:.4f} seconds")
            # print(json.dumps(response.json(), indent=2))
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error connecting to backend: {e}")

if __name__ == "__main__":
    seed_data(1000)
    # This script assumes the server is running on localhost:8000
    # benchmark_summary()
