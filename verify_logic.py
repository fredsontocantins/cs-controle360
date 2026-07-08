import json
from fastapi.testclient import TestClient
import os

# Set environment variables for testing
os.environ["CS_ALLOW_INSECURE_SECRETS"] = "1"
os.environ["PYTHONPATH"] = "."

from backend.main import app

def verify():
    with TestClient(app) as client:
        response = client.get("/api/summary")
        assert response.status_code == 200
        data = response.json()

        # Check for leaked internal keys
        def check_leaks(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    assert not k.startswith("_"), f"Leaked key {k}"
                    check_leaks(v)
            elif isinstance(obj, list):
                for item in obj:
                    check_leaks(item)

        check_leaks(data)

        # Check top level keys
        expected_keys = {
            "homologacoes", "customizacoes", "atividades", "releases",
            "clientes", "modulos", "completed_tasks_total",
            "completed_tasks_by_owner", "activity_by_owner",
            "current_cycle", "previous_cycle", "selected_cycle"
        }
        assert expected_keys.issubset(data.keys())

        # Check cycle summary structure
        for cycle_key in ["current_cycle", "previous_cycle"]:
            if data[cycle_key]:
                c = data[cycle_key]
                assert "homologacoes" in c
                assert "customizacoes" in c
                assert "atividades" in c
                assert "releases" in c
                assert "completed_tasks_total" in c
                assert "completed_tasks_by_owner" in c

        print("Logic verification passed!")

if __name__ == "__main__":
    verify()
