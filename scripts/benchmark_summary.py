import time
import os
import sys
import asyncio
import sqlite3

# Add backend to sys.path
sys.path.append(os.getcwd())

from backend.main import get_summary
from backend.database import get_conn, ensure_tables, reset_application_data, _seed_activity_catalogs
from backend.models.atividade import insert_atividade
from backend.models.report_cycle import open_cycle

async def run_benchmark():
    os.environ["DATABASE_URL"] = "" # Use SQLite for benchmark

    # Pre-setup: ensure schema is correct for what we expect in this branch
    # (Since I'm in a shared environment, I must be careful)
    ensure_tables()
    reset_application_data()
    _seed_activity_catalogs()

    print("Seeding 2000 records for benchmark...")
    # Insert 2000 activities
    for i in range(2000):
        insert_atividade({
            "title": f"Task {i}",
            "owner": f"User {i % 5}",
            "executor": f"User {i % 5}",
            "status": "concluida",
            "completed_at": "2023-10-01T10:00:00"
        })

    # Create a cycle
    cycle_id = open_cycle("reports", None, "Cycle 1", "2023-10")

    print("Running benchmark (2000 records)...")
    start = time.time()
    summary = await get_summary(cycle_id)
    end = time.time()

    print(f"Summary response time: {end - start:.4f}s")
    print(f"Activities count: {summary['atividades']}")
    print(f"Completed tasks total: {summary['completed_tasks_total']}")

    # Verification
    assert summary['atividades'] == 2000
    assert summary['completed_tasks_total'] == 2000

if __name__ == "__main__":
    asyncio.run(run_benchmark())
