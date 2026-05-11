import pytest
import uuid
from backend.models.atividade import insert_atividade, AtividadeRepository
from backend.models.homologacao import insert_homologacao, HomologacaoRepository

def test_count_with_filter():
    # Setup
    unique_title = f"Task {uuid.uuid4().hex}"
    insert_atividade({"title": unique_title, "status": "concluida"})
    insert_atividade({"title": f"{unique_title} 2", "status": "em_andamento"})

    # Test count without filter
    total = AtividadeRepository.count()
    assert total >= 2

    # Test count with filter
    completed = AtividadeRepository.count("status = ?", ("concluida",))
    assert completed >= 1

    pending = AtividadeRepository.count("status = ?", ("em_andamento",))
    assert pending >= 1

def test_list_with_filter():
    unique_module = f"Module {uuid.uuid4().hex}"
    insert_homologacao({"module": unique_module, "status": "homologado"})
    insert_homologacao({"module": "Other", "status": "pendente"})

    results = HomologacaoRepository.list("module = ?", (unique_module,))
    assert len(results) == 1
    assert results[0]["module"] == unique_module
