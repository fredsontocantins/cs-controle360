
import pytest
from backend.database import ensure_tables
from backend.models.atividade import AtividadeRepository, insert_atividade
from backend.models.homologacao import HomologacaoRepository, insert_homologacao

@pytest.fixture(autouse=True)
def setup_db():
    ensure_tables()

def test_base_repository_count():
    h_count = HomologacaoRepository.count()
    insert_homologacao({"module": "Test", "status": "pending"})
    assert HomologacaoRepository.count() == h_count + 1

def test_atividade_get_tasks_by_owner():
    insert_atividade({"title": "Task 1", "status": "concluida", "owner": "Alice"})
    insert_atividade({"title": "Task 2", "status": "concluida", "executor": "Bob"})

    stats = AtividadeRepository.get_tasks_by_owner()
    owners = {s["owner"]: s["count"] for s in stats}
    assert owners["Alice"] == 1
    assert owners["Bob"] == 1
