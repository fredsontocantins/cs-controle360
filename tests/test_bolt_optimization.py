
import pytest
from backend.database import ensure_tables
from backend.models.atividade import AtividadeRepository, insert_atividade
from backend.models.homologacao import HomologacaoRepository, insert_homologacao
from backend.models.customizacao import CustomizacaoRepository, insert_customizacao
from backend.models.release import ReleaseRepository, insert_release

@pytest.fixture(autouse=True)
def setup_db():
    ensure_tables()

def test_base_repository_count():
    # Initial counts
    h_count = HomologacaoRepository.count()
    a_count = AtividadeRepository.count()

    # Insert some data
    insert_homologacao({"module": "Test", "status": "pending"})
    insert_atividade({"title": "Test Task", "status": "backlog", "owner": "Bolt"})

    assert HomologacaoRepository.count() == h_count + 1
    assert AtividadeRepository.count() == a_count + 1

    # Filtered count
    assert AtividadeRepository.count(where="status = ?", params=("backlog",)) == 1
    assert AtividadeRepository.count(where="status = ?", params=("concluida",)) == 0

def test_atividade_get_tasks_by_owner():
    # Insert tasks with different owners/executors
    insert_atividade({"title": "Task 1", "status": "concluida", "owner": "Alice"})
    insert_atividade({"title": "Task 2", "status": "concluida", "executor": "Bob"})
    insert_atividade({"title": "Task 3", "status": "backlog", "owner": "Alice"})
    insert_atividade({"title": "Task 4", "status": "concluida", "owner": "Alice", "executor": "Charlie"})

    stats = AtividadeRepository.get_tasks_by_owner()
    # Should find Alice (1 task, Task 1), Bob (1 task, Task 2), Charlie (1 task, Task 4)
    # Task 3 is backlog, so ignored.

    owners = {s["owner"]: s["count"] for s in stats}
    assert owners["Alice"] == 1
    assert owners["Bob"] == 1
    assert owners["Charlie"] == 1
    assert len(stats) == 3

def test_api_summary_integration():
    from fastapi.testclient import TestClient
    from backend.main import app
    import os

    # Ensure env for test
    os.environ["CS_ALLOW_INSECURE_SECRETS"] = "1"
    os.environ["CS_ADMIN_AUTH_ENABLED"] = "0"

    client = TestClient(app)

    # Insert data to be summarized
    insert_homologacao({"module": "H1", "status": "ok", "check_date": "2023-05-01"})
    insert_atividade({"title": "A1", "status": "concluida", "owner": "Owner1", "completed_at": "2023-05-02"})

    response = client.get("/api/summary")
    assert response.status_code == 200
    data = response.json()

    assert data["homologacoes"] >= 1
    assert data["atividades"] >= 1
    assert data["completed_tasks_total"] >= 1

    # Check if owners are present
    owners = [o["owner"] for o in data["completed_tasks_by_owner"]]
    assert "Owner1" in owners
