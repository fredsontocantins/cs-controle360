"""CS-Controle 360 - FastAPI Backend (API Only)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import ensure_tables, reset_application_data, seed_from_snapshot, seed_demo_data_if_needed, _seed_activity_catalogs
from .database import run_query
from .config import CORS_ORIGINS, RESET_SAMPLE_DATA_ON_STARTUP, assert_secure_secrets
from .routers import auth, homologacao, customizacao, atividade, release, cliente, modulo, reports, pdf_intelligence, playbooks
from .services.auth import bootstrap_default_admin, get_current_user


assert_secure_secrets()


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

# Include API routers
app.include_router(auth.router, prefix="/api")
app.include_router(homologacao.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(customizacao.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(atividade.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(release.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(cliente.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(modulo.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(reports.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(pdf_intelligence.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(playbooks.router, prefix="/api", dependencies=[Depends(get_current_user)])




@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}


@app.get("/api/summary")
async def get_summary(cycle_id: int | None = None):
    """
    Get summary of all entities for dashboard.
    ⚡ Bolt Optimization: Uses SQL-level filtering and aggregation instead of in-memory processing.
    """
    from .models.atividade import AtividadeRepository, normalize_person_name
    from .models.customizacao import CustomizacaoRepository
    from .models.homologacao import HomologacaoRepository
    from .models.release import ReleaseRepository
    from .models.report_cycle import get_cycle, get_cycle_window, list_cycles, parse_cycle_datetime
    from .models.cliente import ClienteRepository
    from .models.modulo import ModuloRepository
    from .database import get_conn, run_query

    cycles = list_cycles("reports")
    open_cycle = next((cycle for cycle in cycles if cycle.get("status") == "aberto"), None)
    closed_cycles = [cycle for cycle in cycles if cycle.get("status") == "prestado"]
    closed_cycles.sort(key=lambda item: parse_cycle_datetime(item.get("created_at")), reverse=True)
    previous_cycle = closed_cycles[0] if closed_cycles else None

    def build_cycle_summary(cycle: dict | None) -> dict[str, object] | None:
        if not cycle:
            return None
        start, end = get_cycle_window(cycle["id"])
        start_text = start.isoformat() if start else None
        end_text = end.isoformat() if end else None

        if not start_text:
            return None

        # Build SQL date range conditions using COALESCE to match original multi-field logic
        # SQLite and Postgres both support COALESCE
        def get_date_where(fields: tuple[str, ...]) -> tuple[str, tuple[Any, ...]]:
            coalesce_expr = f"COALESCE({', '.join(fields)})"
            if end_text:
                return f"{coalesce_expr} >= ? AND {coalesce_expr} < ?", (start_text, end_text)
            return f"{coalesce_expr} >= ?", (start_text,)

        h_where, h_params = get_date_where(("check_date", "requested_production_date", "production_date", "created_at"))
        homologacoes = HomologacaoRepository.count(where=h_where, params=h_params)

        c_where, c_params = get_date_where(("received_at", "created_at"))
        customizacoes = CustomizacaoRepository.count(where=c_where, params=c_params)

        a_where, a_params = get_date_where(("created_at", "updated_at", "completed_at"))
        atividades_count = AtividadeRepository.count(where=a_where, params=a_params)

        r_where, r_params = get_date_where(("applies_on", "created_at"))
        releases = ReleaseRepository.count(where=r_where, params=r_params)

        # Task aggregation by owner (only completed tasks in the cycle)
        tasks_by_owner: list[dict[str, object]] = []
        group_where = f"status = 'concluida' AND {a_where}"

        # Use COALESCE for executor/owner fallback in SQL
        # SQLite and Postgres handle this well
        agg_sql = f"""
            SELECT
                COALESCE(NULLIF(executor, ''), NULLIF(owner, ''), 'Sem responsável') as person,
                COUNT(*) as count
            FROM {AtividadeRepository.table}
            WHERE {group_where}
            GROUP BY person
            ORDER BY count DESC, person ASC
        """

        with AtividadeRepository._connect() as conn:
            cur = run_query(conn, agg_sql, a_params)
            rows = cur.fetchall()
            for row in rows:
                tasks_by_owner.append({
                    "owner": normalize_person_name(row[0]),
                    "count": row[1]
                })

        return {
            "label": cycle.get("period_label") or f"Prestação {cycle.get('cycle_number') or cycle.get('id')}",
            "cycle_number": cycle.get("cycle_number"),
            "homologacoes": homologacoes,
            "customizacoes": customizacoes,
            "atividades": atividades_count,
            "releases": releases,
            "completed_tasks_total": sum(int(item["count"]) for item in tasks_by_owner),
            "completed_tasks_by_owner": tasks_by_owner,
        }

    previous_cycle_summary = build_cycle_summary(previous_cycle)
    current_cycle_summary = build_cycle_summary(open_cycle)
    selected_cycle_summary = build_cycle_summary(get_cycle(cycle_id)) if cycle_id else None

    # Global aggregation for all time (or active view)
    global_tasks_by_owner: list[dict[str, object]] = []
    global_agg_sql = f"""
        SELECT
            COALESCE(NULLIF(executor, ''), NULLIF(owner, ''), 'Sem responsável') as person,
            COUNT(*) as count
        FROM {AtividadeRepository.table}
        WHERE status = 'concluida'
        GROUP BY person
        ORDER BY count DESC, person ASC
    """
    with AtividadeRepository._connect() as conn:
        cur = run_query(conn, global_agg_sql)
        rows = cur.fetchall()
        for row in rows:
            global_tasks_by_owner.append({
                "owner": normalize_person_name(row[0]),
                "count": row[1]
            })

    summary = {
        "homologacoes": HomologacaoRepository.count(),
        "customizacoes": CustomizacaoRepository.count(),
        "atividades": AtividadeRepository.count(),
        "releases": ReleaseRepository.count(),
        "clientes": ClienteRepository.count(),
        "modulos": ModuloRepository.count(),
        "completed_tasks_total": sum(int(item["count"]) for item in global_tasks_by_owner),
        "completed_tasks_by_owner": global_tasks_by_owner,
        "activity_by_owner": global_tasks_by_owner,
        "current_cycle": current_cycle_summary,
        "previous_cycle": previous_cycle_summary,
        "selected_cycle": selected_cycle_summary,
    }
    return summary


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    ensure_tables()
    if RESET_SAMPLE_DATA_ON_STARTUP:
        reset_application_data()
        _seed_activity_catalogs()
        bootstrap_default_admin()
        seed_demo_data_if_needed()
        return

    bootstrap_default_admin()

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

    seed_demo_data_if_needed()

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# Serve frontend if exists - MOUNTED LAST
FRONTEND_DIR = BASE_DIR.parent / "frontend" / "dist"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

# CORS middleware for React frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
