
import time
import os
import sys
from fastapi.testclient import TestClient

# Add current directory to path so we can import backend
sys.path.append(os.getcwd())

# Set environment variables for testing
os.environ["CS_ALLOW_INSECURE_SECRETS"] = "1"
os.environ["CS_ADMIN_AUTH_ENABLED"] = "0"

from backend.main import app
from backend.database import get_conn, ensure_tables
from backend.models.homologacao import insert_homologacao
from backend.models.atividade import insert_atividade
from backend.models.customizacao import insert_customizacao
from backend.models.release import insert_release
from backend.models.report_cycle import open_cycle, close_cycle

def seed_data(count=100):
    ensure_tables()
    conn = get_conn()
    # Clear tables
    tables = ["homologacao", "customizations", "activities", "releases", "report_cycles"]
    for table in tables:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()

    # Create cycles
    c1 = open_cycle("reports", None, "Reports", "Period 1")
    time.sleep(0.1)
    close_cycle(c1)
    c2 = open_cycle("reports", None, "Reports", "Period 2")

    # Seed records
    for i in range(count):
        insert_homologacao({
            "module": "Mod",
            "status": "ok",
            "check_date": "2024-01-01",
            "created_at": "2024-01-01"
        })
        insert_atividade({
            "title": f"Activity {i}",
            "status": "concluida",
            "owner": "Bolt",
            "executor": "Bolt",
            "created_at": "2024-01-01"
        })
        insert_customizacao({
            "subject": "Cust",
            "received_at": "2024-01-01",
            "created_at": "2024-01-01"
        })
        insert_release({
            "release_name": "Rel",
            "applies_on": "2024-01-01",
            "created_at": "2024-01-01"
        })

def run_benchmark():
    client = TestClient(app)

    # Warmup
    client.get("/api/summary")

    start_time = time.perf_counter()
    iterations = 20
    for _ in range(iterations):
        client.get("/api/summary")
    end_time = time.perf_counter()

    avg_time = (end_time - start_time) / iterations
    print(f"Average time for /api/summary: {avg_time:.4f} seconds ({iterations} iterations)")
    return avg_time

if __name__ == "__main__":
    print("Seeding data...")
    seed_data(200) # 200 of each entity
    print("Running benchmark...")
    run_benchmark()
