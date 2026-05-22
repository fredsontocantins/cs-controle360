"""CS-Controle 360 - FastAPI Backend (API Only)."""

from __future__ import annotations

from pathlib import Path

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
    """Get summary of all entities for dashboard."""
    from .models import AtividadeRepository, CustomizacaoRepository, HomologacaoRepository, ReleaseRepository, ClienteRepository, ModuloRepository
    from .models.atividade import normalize_person_name
    from .models.report_cycle import get_cycle, list_cycles, parse_cycle_datetime, get_cycle_window, get_active_cycle_started_at
    from .database import get_conn, run_query
    from .config import TABLE_ATIVIDADE

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

        # Date filtering logic replicated in SQL using multiple OR conditions
        # to match the Python 'any-field' logic.
        h_where = "check_date >= ? OR requested_production_date >= ? OR production_date >= ? OR created_at >= ?"
        h_params = (start_text, start_text, start_text, start_text)
        if end_text:
            h_where = f"({h_where}) AND (check_date < ? OR requested_production_date < ? OR production_date < ? OR created_at < ?)"
            h_params += (end_text, end_text, end_text, end_text)
        homologacoes = HomologacaoRepository.count(h_where, h_params)

        c_where = "received_at >= ? OR created_at >= ?"
        c_params = (start_text, start_text)
        if end_text:
            c_where = f"({c_where}) AND (received_at < ? OR created_at < ?)"
            c_params += (end_text, end_text)
        customizacoes = CustomizacaoRepository.count(c_where, c_params)

        a_where = "created_at >= ? OR updated_at >= ? OR completed_at >= ?"
        a_params = (start_text, start_text, start_text)
        if end_text:
            a_where = f"({a_where}) AND (created_at < ? OR updated_at < ? OR completed_at < ?)"
            a_params += (end_text, end_text, end_text)
        atividades_count = AtividadeRepository.count(a_where, a_params)

        r_where = "applies_on >= ? OR created_at >= ?"
        r_params = (start_text, start_text)
        if end_text:
            r_where = f"({r_where}) AND (applies_on < ? OR created_at < ?)"
            r_params += (end_text, end_text)
        releases = ReleaseRepository.count(r_where, r_params)

        # Tasks by owner using GROUP BY
        at_where = f"status = 'concluida' AND ({a_where})"
        group_sql = f"SELECT COALESCE(executor, owner, 'Sem responsável') as person, COUNT(*) as count FROM {TABLE_ATIVIDADE} WHERE {at_where} GROUP BY person"

        conn = get_conn()
        cur = run_query(conn, group_sql, a_params)
        rows = cur.fetchall()
        conn.close()

        grouped_cycle: dict[str, int] = {}
        for person, count in rows:
            label = normalize_person_name(person)
            key = label.casefold()
            grouped_cycle[key] = grouped_cycle.get(key, 0) + count

        tasks_by_owner = [
            {"owner": label, "count": count}
            for label, count in sorted(
                [(normalize_person_name(k), v) for k, v in grouped_cycle.items()],
                key=lambda item: (-item[1], item[0])
            )
        ]

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

    # Global counts for active cycle or overall totals
    cycle_started_at = get_active_cycle_started_at("reports")

    # Dashboard expects counts for the current context (usually active cycle)
    # but some totals might be desired for the entire database.
    # The original implementation for global counts (outside cycles) did NOT filter.

    # Overall database totals
    all_activities = AtividadeRepository.count()
    all_homologacoes = HomologacaoRepository.count()
    all_customizacoes = CustomizacaoRepository.count()
    all_releases = ReleaseRepository.count()

    # Completed tasks grouping (usually for the current context)
    if cycle_started_at:
        ga_where = "created_at >= ? OR updated_at >= ? OR completed_at >= ?"
        ga_params = (cycle_started_at, cycle_started_at, cycle_started_at)
        group_sql = f"SELECT COALESCE(executor, owner, 'Sem responsável') as person, COUNT(*) as count FROM {TABLE_ATIVIDADE} WHERE status = 'concluida' AND ({ga_where}) GROUP BY person"
        conn = get_conn()
        cur = run_query(conn, group_sql, ga_params)
        rows = cur.fetchall()
        conn.close()
    else:
        group_sql = f"SELECT COALESCE(executor, owner, 'Sem responsável') as person, COUNT(*) as count FROM {TABLE_ATIVIDADE} WHERE status = 'concluida' GROUP BY person"
        conn = get_conn()
        cur = run_query(conn, group_sql)
        rows = cur.fetchall()
        conn.close()

    global_grouped: dict[str, int] = {}
    for person, count in rows:
        label = normalize_person_name(person)
        key = label.casefold()
        global_grouped[key] = global_grouped.get(key, 0) + count

    completed_tasks_by_owner = [
        {"owner": label, "count": count}
        for label, count in sorted(
            [(normalize_person_name(k), v) for k, v in global_grouped.items()],
            key=lambda item: (-item[1], item[0])
        )
    ]

    completed_tasks_total = sum(item["count"] for item in completed_tasks_by_owner)
    clients_count = ClienteRepository.count()
    modules_count = ModuloRepository.count()

    summary = {
        "homologacoes": all_homologacoes,
        "customizacoes": all_customizacoes,
        "atividades": all_activities,
        "releases": all_releases,
        "clientes": clients_count,
        "modulos": modules_count,
        "completed_tasks_total": completed_tasks_total,
        "completed_tasks_by_owner": completed_tasks_by_owner,
        "activity_by_owner": completed_tasks_by_owner,
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
