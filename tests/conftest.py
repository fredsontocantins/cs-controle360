import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_database_connection():
    # Create a mock database connection
    connection = MagicMock()  
    # Set up any additional mock behavior here
    yield connection
    # Teardown code if necessary

@pytest.fixture
def mock_data():
    # Create and return mock data for tests
    return {
        'user': {'id': 1, 'name': 'Test User'},
        'item': {'id': 1, 'name': 'Test Item'}
    }
