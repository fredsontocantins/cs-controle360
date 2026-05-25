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
    from .models import (
        AtividadeRepository,
        CustomizacaoRepository,
        HomologacaoRepository,
        ReleaseRepository,
    )
    from .models.atividade import list_atividade, normalize_person_name
    from .models.customizacao import list_customizacao
    from .models.homologacao import list_homologacao
    from .models.release import list_release
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

        # SQL-level filtering for counts
        # We use COALESCE to mimic the original _record_datetime logic (prioritizing specific fields)
        h_dt = "COALESCE(check_date, requested_production_date, production_date, created_at)"
        h_where = f"{h_dt} >= ?"
        h_params = (start_text,)
        if end_text:
            h_where += f" AND {h_dt} < ?"
            h_params += (end_text,)
        homologacoes = HomologacaoRepository.count(h_where, h_params)

        c_dt = "COALESCE(received_at, created_at)"
        c_where = f"{c_dt} >= ?"
        c_params = (start_text,)
        if end_text:
            c_where += f" AND {c_dt} < ?"
            c_params += (end_text,)
        customizacoes = CustomizacaoRepository.count(c_where, c_params)

        a_dt = "COALESCE(completed_at, updated_at, created_at)"
        a_where = f"{a_dt} >= ?"
        a_params = (start_text,)
        if end_text:
            a_where += f" AND {a_dt} < ?"
            a_params += (end_text,)
        atividades_count = AtividadeRepository.count(a_where, a_params)

        r_dt = "COALESCE(applies_on, created_at)"
        r_where = f"{r_dt} >= ?"
        r_params = (start_text,)
        if end_text:
            r_where += f" AND {r_dt} < ?"
            r_params += (end_text,)
        releases = ReleaseRepository.count(r_where, r_params)

        # SQL-level aggregation for tasks by owner within cycle
        # We group by the raw name but normalize in Python to handle minor variations,
        # though ideally the data should be clean.
        tasks_sql = f"""
            SELECT COALESCE(executor, owner, 'Sem responsável') as owner_label, COUNT(*) as task_count
            FROM activities
            WHERE status = 'concluida' AND {a_where}
            GROUP BY COALESCE(executor, owner, 'Sem responsável')
        """
        tasks_cursor = run_query(conn, tasks_sql, a_params)

        # Merge counts in Python after normalization to handle cases like "John Doe" vs "john doe"
        grouped_cycle: dict[str, dict[str, object]] = {}
        for row in tasks_cursor.fetchall():
            label = normalize_person_name(row[0])
            key = label.casefold()
            if key not in grouped_cycle:
                grouped_cycle[key] = {"owner": label, "count": 0}
            grouped_cycle[key]["count"] = int(grouped_cycle[key]["count"]) + row[1]

        tasks_by_owner = [
            {"owner": item["owner"], "count": item["count"]}
            for item in sorted(grouped_cycle.values(), key=lambda item: (-int(item["count"]), str(item["owner"])))
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

    # Global tasks by owner aggregation
    global_tasks_sql = """
        SELECT COALESCE(executor, owner, 'Sem responsável') as owner_label, COUNT(*) as task_count
        FROM activities
        WHERE status = 'concluida'
        GROUP BY COALESCE(executor, owner, 'Sem responsável')
    """
    global_tasks_cursor = run_query(conn, global_tasks_sql)

    grouped_global: dict[str, dict[str, object]] = {}
    for row in global_tasks_cursor.fetchall():
        label = normalize_person_name(row[0])
        key = label.casefold()
        if key not in grouped_global:
            grouped_global[key] = {"owner": label, "count": 0}
        grouped_global[key]["count"] = int(grouped_global[key]["count"]) + row[1]

    completed_tasks_by_owner = [
        {"owner": item["owner"], "count": item["count"]}
        for item in sorted(grouped_global.values(), key=lambda item: (-int(item["count"]), str(item["owner"])))
    ]
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
