import time
from fastapi.testclient import TestClient
from backend.main import app, startup
from backend.models.atividade import insert_atividade
from backend.models.homologacao import insert_homologacao
from backend.models.customizacao import insert_customizacao
from backend.models.release import insert_release
import asyncio
from datetime import datetime, UTC

async def benchmark():
    # Force startup to seed base tables
    await startup()

    # Seed a lot of data
    print("Seeding 1000 records...")
    for i in range(250):
        insert_atividade({"title": f"Task {i}", "owner": "Bolt", "executor": "Bolt", "status": "concluida"})
        insert_homologacao({"module": f"Module {i}", "status": "Homologado", "check_date": datetime.now(UTC).isoformat()})
        insert_customizacao({"subject": f"Custom {i}", "client": "Client A", "received_at": datetime.now(UTC).isoformat()})
        insert_release({"release_name": f"Release {i}", "version": "1.0", "applies_on": datetime.now(UTC).isoformat()})

    client = TestClient(app)

    # Warm up
    client.get("/api/summary")

    print("Benchmarking...")
    start = time.perf_counter()
    for _ in range(10):
        client.get("/api/summary")
    end = time.perf_counter()

    print(f"Average time for /api/summary (1000 total records): {(end - start) / 10:.4f}s")

if __name__ == "__main__":
    asyncio.run(benchmark())
