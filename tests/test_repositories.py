import pytest
import uuid
from backend.database import ensure_tables
from backend.models.cliente import ClienteRepository, insert_cliente, get_cliente

@pytest.fixture(autouse=True)
def setup_db():
    ensure_tables()

def test_cliente_repository_crud():
    unique_name = f"Test Client {uuid.uuid4().hex[:8]}"
    # Test Insert
    data = {"name": unique_name, "segment": "Testing", "owner": "Jules"}
    client_id = insert_cliente(data)
    assert client_id > 0

    # Test Get
    client = get_cliente(client_id)
    assert client is not None
    assert client["name"] == unique_name

    # Test List
    clients = ClienteRepository.list()
    assert len(clients) >= 1
    assert any(c["id"] == client_id for c in clients)

def test_base_repository_filtering_and_counting():
    # Insert multiple clients
    prefix = f"FilterTest-{uuid.uuid4().hex[:4]}"
    insert_cliente({"name": f"{prefix}-1", "segment": "A", "owner": "Bolt"})
    insert_cliente({"name": f"{prefix}-2", "segment": "B", "owner": "Bolt"})
    insert_cliente({"name": f"{prefix}-3", "segment": "A", "owner": "Bolt"})

    # Test count with filter
    count_a = ClienteRepository.count(where="segment = ?", params=("A",))
    assert count_a >= 2

    # Test list with filter
    list_a = ClienteRepository.list(where="segment = ?", params=("A",))
    assert len(list_a) >= 2
    for item in list_a:
        assert item["segment"] == "A"

    # Test count without filter
    total_count = ClienteRepository.count()
    total_list = ClienteRepository.list()
    assert total_count == len(total_list)
