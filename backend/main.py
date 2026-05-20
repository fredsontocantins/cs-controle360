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
    from .models.atividade import AtividadeRepository, normalize_person_name
    from .models.customizacao import CustomizacaoRepository
    from .models.homologacao import HomologacaoRepository
    from .models.release import ReleaseRepository
    from .models.report_cycle import get_cycle, get_cycle_window, list_cycles, parse_cycle_datetime
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

        # Optimized SQL-level filtering for cycle records
        def get_date_range_where(fields: tuple[str, ...]) -> tuple[str, list[str]]:
            clauses = []
            params = []
            for field in fields:
                clauses.append(f"{field} >= ?")
                params.append(start_text)
                if end_text:
                    clauses.append(f"{field} < ?")
                    params.append(end_text)

            # For multiple fields, it's (field1_range OR field2_range OR ...)
            # Simplified: any of these fields within the range
            combined_clauses = []
            for i in range(0, len(clauses), 2 if end_text else 1):
                if end_text:
                    combined_clauses.append(f"({clauses[i]} AND {clauses[i+1]})")
                else:
                    combined_clauses.append(clauses[i])

            return " OR ".join(combined_clauses), params

        h_where, h_params = get_date_range_where(("check_date", "requested_production_date", "production_date", "created_at"))
        homologacoes = HomologacaoRepository.count(h_where, tuple(h_params))

        c_where, c_params = get_date_range_where(("received_at", "created_at"))
        customizacoes = CustomizacaoRepository.count(c_where, tuple(c_params))

        a_where, a_params = get_date_range_where(("created_at", "updated_at", "completed_at"))
        atividades_count = AtividadeRepository.count(a_where, tuple(a_params))

        r_where, r_params = get_date_range_where(("applies_on", "created_at"))
        releases = ReleaseRepository.count(r_where, tuple(r_params))

        # Completed tasks by owner in the cycle
        tasks_by_owner: list[dict[str, object]] = []
        # We need status = 'concluida' AND (date range)
        where_tasks = f"status = 'concluida' AND ({a_where})"

        # Use run_query for direct aggregation
        query = f"""
            SELECT COALESCE(executor, owner, 'Sem responsável') as person, COUNT(*) as count
            FROM {AtividadeRepository.table}
            WHERE {where_tasks}
            GROUP BY COALESCE(executor, owner, 'Sem responsável')
            ORDER BY count DESC, person ASC
        """
        rows = run_query(conn, query, tuple(a_params)).fetchall()

        tasks_by_owner = []
        for row in rows:
            label = normalize_person_name(row[0])
            tasks_by_owner.append({"owner": label, "count": int(row[1])})

        # Re-sort after normalization because names like "john doe" and "John Doe" might be separate in DB
        # but normalized to the same thing. Actually normalize_person_name is pretty standard.
        # To be safe, we can regroup in Python if needed, but SQL group by is faster.
        # Let's regroup in Python to handle normalization perfectly if needed.
        grouped_tasks: dict[str, dict] = {}
        for item in tasks_by_owner:
            name = item["owner"]
            key = name.casefold()
            if key not in grouped_tasks:
                grouped_tasks[key] = {"owner": name, "count": 0}
            grouped_tasks[key]["count"] += item["count"]

        tasks_by_owner = sorted(grouped_tasks.values(), key=lambda x: (-x["count"], x["owner"]))

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

    # Global activity by owner
    query_global = f"""
        SELECT COALESCE(executor, owner, 'Sem responsável') as person, COUNT(*) as count
        FROM {AtividadeRepository.table}
        WHERE status = 'concluida'
        GROUP BY COALESCE(executor, owner, 'Sem responsável')
        ORDER BY count DESC, person ASC
    """
    rows_global = run_query(conn, query_global).fetchall()
    grouped_global: dict[str, dict] = {}
    for row in rows_global:
        name = normalize_person_name(row[0])
        key = name.casefold()
        if key not in grouped_global:
            grouped_global[key] = {"owner": name, "count": 0}
        grouped_global[key]["count"] += int(row[1])

    completed_tasks_by_owner = sorted(grouped_global.values(), key=lambda x: (-x["count"], x["owner"]))
    completed_tasks_total = sum(item["count"] for item in completed_tasks_by_owner)

    try:
        clients_count = run_query(conn, "SELECT COUNT(*) FROM clients").fetchone()[0]
        modules_count = run_query(conn, "SELECT COUNT(*) FROM modules").fetchone()[0]
    except Exception:
        clients_count = 0
        modules_count = 0

    summary = {
        "homologacoes": HomologacaoRepository.count(),
        "customizacoes": CustomizacaoRepository.count(),
        "atividades": AtividadeRepository.count(),
        "releases": ReleaseRepository.count(),
        "clientes": clients_count,
        "modulos": modules_count,
        "completed_tasks_total": completed_tasks_total,
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
