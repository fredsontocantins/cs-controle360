"""CS-Controle 360 - FastAPI Backend (API Only)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import ensure_tables, seed_from_snapshot
from .routers import homologacao, customizacao, atividade, release, cliente, modulo, reports, pdf_intelligence, playbooks


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "static" / "uploads"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


app = FastAPI(
    title="CS-Controle 360 API",
    description="API for controlling homologation, customization and releases",
    version="2.0.0"
)

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(homologacao.router, prefix="/api")
app.include_router(customizacao.router, prefix="/api")
app.include_router(atividade.router, prefix="/api")
app.include_router(release.router, prefix="/api")
app.include_router(cliente.router, prefix="/api")
app.include_router(modulo.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(pdf_intelligence.router, prefix="/api")
app.include_router(playbooks.router, prefix="/api")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}


@app.get("/api/summary")
async def get_summary():
    """Get summary of all entities for dashboard."""
    from .database import get_conn

    conn = get_conn()
    summary = {
        "homologacoes": conn.execute("SELECT COUNT(*) FROM homologacao").fetchone()[0],
        "customizacoes": conn.execute("SELECT COUNT(*) FROM customizations").fetchone()[0],
        "atividades": conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0],
        "releases": conn.execute("SELECT COUNT(*) FROM releases").fetchone()[0],
        "clientes": conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0],
        "modulos": conn.execute("SELECT COUNT(*) FROM modules").fetchone()[0],
    }
    conn.close()
    return summary


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    ensure_tables()

    snapshot_candidates = [
        DATA_DIR / "initial_snapshot.json",
        DATA_DIR / "control_snapshot.json",
        BASE_DIR.parent / "control_snapshot.json",
    ]

    for snapshot_path in snapshot_candidates:
        if snapshot_path.exists():
            import json
            with open(snapshot_path) as f:
                snapshot = json.load(f)
            seed_from_snapshot(snapshot)
            break
