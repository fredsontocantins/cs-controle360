
import time
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import ensure_tables, get_conn, run_query
from datetime import datetime, timedelta
import os

@pytest.fixture(autouse=True)
def setup_db():
    os.environ["DATABASE_URL"] = "" # Use SQLite for testing
    ensure_tables()
    conn = get_conn()
    from backend.config import TABLE_ATIVIDADE, TABLE_REPORT_CYCLE, TABLE_HOMOLOGACAO, TABLE_CUSTOMIZACAO, TABLE_RELEASE
    conn.execute(f"DELETE FROM {TABLE_ATIVIDADE}")
    conn.execute(f"DELETE FROM {TABLE_REPORT_CYCLE}")
    conn.execute(f"DELETE FROM {TABLE_HOMOLOGACAO}")
    conn.execute(f"DELETE FROM {TABLE_CUSTOMIZACAO}")
    conn.execute(f"DELETE FROM {TABLE_RELEASE}")
    conn.commit()
    yield
    conn.close()

def seed_data(num_records=1000):
    from backend.config import TABLE_ATIVIDADE, TABLE_REPORT_CYCLE
    conn = get_conn()
    now = datetime.utcnow()

    # Seed activities
    activities = []
    for i in range(num_records):
        created_at = (now - timedelta(days=i % 30)).isoformat()
        activities.append((f"Task {i}", "concluida" if i % 2 == 0 else "backlog", f"Owner {i % 10}", f"Executor {i % 10}", created_at, created_at))

    if activities:
        placeholders = "(?, ?, ?, ?, ?, ?)"
        conn.executemany(
            f"INSERT INTO {TABLE_ATIVIDADE} (title, status, owner, executor, created_at, updated_at) VALUES {placeholders}",
            activities
        )

    # Seed a cycle
    conn.execute(
        f"INSERT INTO {TABLE_REPORT_CYCLE} (scope_type, cycle_number, status, created_at, opened_at) VALUES (?, ?, ?, ?, ?)",
        ("reports", 1, "aberto", (now - timedelta(days=15)).isoformat(), (now - timedelta(days=15)).isoformat())
    )

    conn.commit()

def test_summary_performance():
    seed_data(2000)
    client = TestClient(app)

    # Measure first call (warm up)
    client.get("/api/summary", headers={"Authorization": "Bearer mock-token"})

    start_time = time.time()
    response = client.get("/api/summary", headers={"Authorization": "Bearer mock-token"})
    end_time = time.time()

    duration = end_time - start_time
    assert response.status_code == 200
    print(f"\nSummary API duration for 2000 records: {duration:.4f}s")

if __name__ == "__main__":
    # Manually run if needed
    setup_db()
    test_summary_performance()
