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
