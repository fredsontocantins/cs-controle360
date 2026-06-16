import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import ensure_tables, reset_application_data, get_conn, TABLE_ATIVIDADE, TABLE_REPORT_CYCLE
from datetime import datetime, timedelta
import os

@pytest.fixture(autouse=True)
def setup_db():
    os.environ["CS_ADMIN_AUTH_ENABLED"] = "0"
    os.environ["CS_ALLOW_INSECURE_SECRETS"] = "1"
    ensure_tables()
    reset_application_data()
    yield

def test_summary_performance_and_correctness():
    client = TestClient(app)
    conn = get_conn()

    # Create a cycle
    now = datetime.utcnow()
    start_date = (now - timedelta(days=10)).isoformat()
    conn.execute(f"INSERT INTO {TABLE_REPORT_CYCLE} (scope_type, scope_id, cycle_number, period_label, status, opened_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 ("reports", None, 1, "Test Cycle", "aberto", start_date, start_date))

    # Insert some activities within cycle
    activities = [
        ("Task 1", "concluida", "Alice", "Alice", (now - timedelta(days=5)).isoformat()),
        ("Task 2", "concluida", "Bob", "Bob", (now - timedelta(days=2)).isoformat()),
        ("Task 3", "backlog", "Alice", "Alice", (now - timedelta(days=1)).isoformat()),
    ]
    for title, status, owner, executor, completed_at in activities:
        conn.execute(f"INSERT INTO {TABLE_ATIVIDADE} (title, status, owner, executor, completed_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (title, status, owner, executor, completed_at, completed_at, completed_at))

    # Insert activity outside cycle
    outside_date = (now - timedelta(days=20)).isoformat()
    conn.execute(f"INSERT INTO {TABLE_ATIVIDADE} (title, status, owner, executor, completed_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 ("Old Task", "concluida", "Alice", "Alice", outside_date, outside_date, outside_date))

    conn.commit()
    conn.close()

    response = client.get("/api/summary")
    assert response.status_code == 200
    data = response.json()

    # Total counts
    assert data["atividades"] == 4

    # Current cycle counts
    current_cycle = data["current_cycle"]
    assert current_cycle is not None
    assert current_cycle["atividades"] == 3
    assert current_cycle["completed_tasks_total"] == 2

    owners = {item["owner"]: item["count"] for item in current_cycle["completed_tasks_by_owner"]}
    assert owners["Alice"] == 1
    assert owners["Bob"] == 1

    # Global counts
    assert data["completed_tasks_total"] == 3
