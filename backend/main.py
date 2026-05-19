"""CS-Controle 360 - FastAPI Backend (API Only)."""

from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import ensure_tables, reset_application_data, seed_from_snapshot, seed_demo_data_if_needed, _seed_activity_catalogs
from .database import run_query
from .config import CORS_ORIGINS, RESET_SAMPLE_DATA_ON_STARTUP, assert_secure_secrets, logger
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
    """Get summary of all entities for dashboard."""
    from .models.atividade import AtividadeRepository, normalize_person_name
    from .models.customizacao import CustomizacaoRepository
    from .models.homologacao import HomologacaoRepository
    from .models.release import ReleaseRepository
    from .models.report_cycle import get_cycle, get_cycle_window, list_cycles, parse_cycle_datetime, get_active_cycle_started_at
    from .database import get_conn, run_query

    conn = get_conn()
    cycles = list_cycles("reports")
    open_cycle = next((cycle for cycle in cycles if cycle.get("status") == "aberto"), None)
    closed_cycles = [cycle for cycle in cycles if cycle.get("status") == "prestado"]
    closed_cycles.sort(key=lambda item: parse_cycle_datetime(item.get("created_at")), reverse=True)
    previous_cycle = closed_cycles[0] if closed_cycles else None

    def build_cycle_summary(cycle: dict | None) -> dict[str, object] | None:
        if not cycle:
            return None
        start, end = get_cycle_window(cycle["id"])
        if not start:
            return {
                "label": cycle.get("period_label") or f"Prestação {cycle.get('cycle_number') or cycle.get('id')}",
                "cycle_number": cycle.get("cycle_number"),
                "homologacoes": 0,
                "customizacoes": 0,
                "atividades": 0,
                "releases": 0,
                "completed_tasks_total": 0,
                "completed_tasks_by_owner": [],
            }

        start_text = start.isoformat()
        end_text = end.isoformat() if end else None

        # SQL filtering for cycle
        where_h = "check_date >= ? OR requested_production_date >= ? OR production_date >= ? OR created_at >= ?"
        params_h = (start_text, start_text, start_text, start_text)
        if end_text:
            where_h = f"({where_h}) AND (check_date < ? OR requested_production_date < ? OR production_date < ? OR created_at < ?)"
            params_h += (end_text, end_text, end_text, end_text)

        where_c = "received_at >= ? OR created_at >= ?"
        params_c = (start_text, start_text)
        if end_text:
            where_c = f"({where_c}) AND (received_at < ? OR created_at < ?)"
            params_c += (end_text, end_text)

        where_a = "created_at >= ? OR updated_at >= ? OR completed_at >= ?"
        params_a = (start_text, start_text, start_text)
        if end_text:
            where_a = f"({where_a}) AND (created_at < ? OR updated_at < ? OR completed_at < ?)"
            params_a += (end_text, end_text, end_text)

        where_r = "applies_on >= ? OR created_at >= ?"
        params_r = (start_text, start_text)
        if end_text:
            where_r = f"({where_r}) AND (applies_on < ? OR created_at < ?)"
            params_r += (end_text, end_text)

        homologacoes = HomologacaoRepository.count(where_h, params_h)
        customizacoes = CustomizacaoRepository.count(where_c, params_c)
        atividades_count = AtividadeRepository.count(where_a, params_a)
        releases = ReleaseRepository.count(where_r, params_r)

        # SQL Grouped aggregation for owner
        where_agg = f"status = 'concluida' AND ({where_a})"
        params_agg = params_a

        # Use COALESCE(executor, owner, 'Sem responsável') and group by it
        agg_sql = f"""
            SELECT COALESCE(NULLIF(executor, ''), NULLIF(owner, ''), 'Sem responsável') as person, COUNT(*) as count
            FROM activities
            WHERE {where_agg}
            GROUP BY COALESCE(NULLIF(executor, ''), NULLIF(owner, ''), 'Sem responsável')
            ORDER BY count DESC, person ASC
        """

        tasks_by_owner = []
        try:
            cursor = run_query(conn, agg_sql, params_agg)
            for row in cursor.fetchall():
                label = normalize_person_name(row[0])
                tasks_by_owner.append({"owner": label, "count": row[1]})
        except Exception as e:
            logger.error(f"Error aggregating tasks by owner in cycle: {e}")

        return {
            "label": cycle.get("period_label") or f"Prestação {cycle.get('cycle_number') or cycle.get('id')}",
            "cycle_number": cycle.get("cycle_number"),
            "homologacoes": homologacoes,
            "customizacoes": customizacoes,
            "atividades": atividades_count,
            "releases": releases,
            "completed_tasks_total": sum(item["count"] for item in tasks_by_owner),
            "completed_tasks_by_owner": tasks_by_owner,
        }

    previous_cycle_summary = build_cycle_summary(previous_cycle)
    current_cycle_summary = build_cycle_summary(open_cycle)
    selected_cycle_summary = build_cycle_summary(get_cycle(cycle_id)) if cycle_id else None

    # Global summary with SQL (Total counts should be truly global)
    atividades_total = AtividadeRepository.count()
    homologacoes_total = HomologacaoRepository.count()
    customizacoes_total = CustomizacaoRepository.count()
    releases_total = ReleaseRepository.count()

    agg_sql_global = """
        SELECT COALESCE(NULLIF(executor, ''), NULLIF(owner, ''), 'Sem responsável') as person, COUNT(*) as count
        FROM activities
        WHERE status = 'concluida'
        GROUP BY COALESCE(NULLIF(executor, ''), NULLIF(owner, ''), 'Sem responsável')
        ORDER BY count DESC, person ASC
    """
    completed_tasks_by_owner = []
    try:
        cursor = run_query(conn, agg_sql_global)
        for row in cursor.fetchall():
            label = normalize_person_name(row[0])
            completed_tasks_by_owner.append({"owner": label, "count": row[1]})
    except Exception as e:
        logger.error(f"Error aggregating tasks by owner global: {e}")

    try:
        clients_count = run_query(conn, "SELECT COUNT(*) FROM clients").fetchone()[0]
        modules_count = run_query(conn, "SELECT COUNT(*) FROM modules").fetchone()[0]
    except Exception:
        clients_count = 0
        modules_count = 0

    summary = {
        "homologacoes": homologacoes_total,
        "customizacoes": customizacoes_total,
        "atividades": atividades_total,
        "releases": releases_total,
        "clientes": clients_count,
        "modulos": modules_count,
        "completed_tasks_total": sum(item["count"] for item in completed_tasks_by_owner),
        "completed_tasks_by_owner": completed_tasks_by_owner,
        "activity_by_owner": completed_tasks_by_owner,
        "current_cycle": current_cycle_summary,
        "previous_cycle": previous_cycle_summary,
        "selected_cycle": selected_cycle_summary,
    }
    conn.close()
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
