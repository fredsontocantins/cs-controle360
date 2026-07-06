"""CS-Controle 360 - FastAPI Backend (API Only)."""

from __future__ import annotations

from datetime import datetime
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


def _record_datetime(entity: dict, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = entity.get(key)
        if value:
            return str(value)
    return None


def _filter_cycle_records(records: list[dict], start: str, end: str | None, keys: tuple[str, ...]) -> list[dict]:
    from .models.report_cycle import parse_cycle_datetime

    cycle_start = parse_cycle_datetime(start)
    cycle_end = parse_cycle_datetime(end) if end else None
    filtered: list[dict] = []
    for record in records:
        record_value = _record_datetime(record, keys)
        if not record_value:
            continue
        record_dt = parse_cycle_datetime(record_value)
        if record_dt < cycle_start:
            continue
        if cycle_end and record_dt >= cycle_end:
            continue
        filtered.append(record)
    return filtered


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
    from .models.report_cycle import get_cycle, get_cycle_window, list_cycles, parse_cycle_datetime, get_open_cycle
    from .database import get_conn

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
        if not start or start <= datetime.min:
            return {
                "label": cycle.get("period_label") or f"Prestação {cycle.get('cycle_number') or cycle.get('id')}",
                "cycle_number": cycle.get("cycle_number"),
                "homologacoes": 0, "customizacoes": 0, "atividades": 0, "releases": 0,
                "completed_tasks_total": 0, "completed_tasks_by_owner": []
            }

        start_text = start.isoformat()
        end_text = end.isoformat() if end else None

        # SQL level filtering logic
        def get_where(fields: tuple[str, ...]) -> tuple[str, tuple]:
            # COALESCE across date fields to find the first non-empty value
            expr = "COALESCE(" + ", ".join([f"NULLIF({f}, '')" for f in fields[:-1]]) + f", {fields[-1]})"
            where = f"{expr} >= ?"
            params = [start_text]
            if end_text:
                where += f" AND {expr} < ?"
                params.append(end_text)
            return where, tuple(params)

        h_where, h_params = get_where(("check_date", "requested_production_date", "production_date", "created_at"))
        c_where, c_params = get_where(("received_at", "created_at"))
        a_where, a_params = get_where(("created_at", "updated_at", "completed_at"))
        r_where, r_params = get_where(("applies_on", "created_at"))

        homologacoes = HomologacaoRepository.count(h_where, h_params)
        customizacoes = CustomizacaoRepository.count(c_where, c_params)
        atividades_count = AtividadeRepository.count(a_where, a_params)
        releases = ReleaseRepository.count(r_where, r_params)
        tasks_by_owner = AtividadeRepository.get_tasks_by_owner(a_where, a_params)

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

    # Main dashboard counts (filtered by current cycle if any, matching previous behavior)
    open_cycle_obj = get_open_cycle("reports")
    cycle_start = open_cycle_obj.get("created_at") if open_cycle_obj else None
    if cycle_start:
        where = "COALESCE(NULLIF(created_at, ''), NULLIF(updated_at, ''), completed_at) >= ?"
        params = (cycle_start,)
        h_where = "COALESCE(NULLIF(check_date, ''), NULLIF(requested_production_date, ''), NULLIF(production_date, ''), created_at) >= ?"
        h_params = (cycle_start,)
        c_where = "COALESCE(NULLIF(received_at, ''), created_at) >= ?"
        c_params = (cycle_start,)
        r_where = "COALESCE(NULLIF(applies_on, ''), created_at) >= ?"
        r_params = (cycle_start,)

        homo_count = HomologacaoRepository.count(h_where, h_params)
        cust_count = CustomizacaoRepository.count(c_where, c_params)
        atividades_count = AtividadeRepository.count(where, params)
        rel_count = ReleaseRepository.count(r_where, r_params)
        tasks_by_owner = AtividadeRepository.get_tasks_by_owner(where, params)
    else:
        homo_count = cust_count = atividades_count = rel_count = 0
        tasks_by_owner = []

    try:
        clients_count = run_query(conn, "SELECT COUNT(*) FROM clients").fetchone()[0]
        modules_count = run_query(conn, "SELECT COUNT(*) FROM modules").fetchone()[0]
    except Exception:
        clients_count = modules_count = 0

    summary = {
        "homologacoes": homo_count,
        "customizacoes": cust_count,
        "atividades": atividades_count,
        "releases": rel_count,
        "clientes": clients_count,
        "modulos": modules_count,
        "completed_tasks_total": sum(item["count"] for item in tasks_by_owner),
        "completed_tasks_by_owner": tasks_by_owner,
        "activity_by_owner": tasks_by_owner,
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
