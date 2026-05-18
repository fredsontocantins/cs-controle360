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
        # Check for pre-calculated datetime to avoid redundant parsing
        if "_dt" in record:
            record_dt = record["_dt"]
        else:
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
    from .models.atividade import list_atividade, normalize_person_name
    from .models.customizacao import list_customizacao
    from .models.homologacao import list_homologacao
    from .models.release import list_release
    from .models.report_cycle import list_cycles, parse_cycle_datetime
    from .database import get_conn

    # 1. Batch fetch all data once to avoid redundant database calls and N+1 query patterns
    activities_all = list_atividade(include_history=True)
    homologacoes_all = list_homologacao(include_history=True)
    customizacoes_all = list_customizacao(include_history=True)
    releases_all = list_release(include_history=True)
    cycles_all = list_cycles("reports")

    # 2. Pre-process records with parsed datetimes and normalized owner labels
    # This significantly reduces overhead during in-memory filtering and grouping
    for a in activities_all:
        a["_dt"] = parse_cycle_datetime(a.get("created_at") or a.get("updated_at") or a.get("completed_at"))
        executor = normalize_person_name(a.get("executor"))
        owner = normalize_person_name(a.get("owner"))
        a["_owner_label"] = executor or owner or "Sem responsável"

    for h in homologacoes_all:
        h["_dt"] = parse_cycle_datetime(h.get("check_date") or h.get("requested_production_date") or h.get("production_date") or h.get("created_at"))

    for c in customizacoes_all:
        c["_dt"] = parse_cycle_datetime(c.get("received_at") or c.get("created_at"))

    for r in releases_all:
        r["_dt"] = parse_cycle_datetime(r.get("applies_on") or r.get("created_at"))

    for cyc in cycles_all:
        cyc["_dt"] = parse_cycle_datetime(cyc.get("created_at"))

    # 3. Identify relevant cycles
    open_cycle = next((cycle for cycle in cycles_all if cycle.get("status") == "aberto"), None)
    closed_cycles = sorted(
        [cycle for cycle in cycles_all if cycle.get("status") == "prestado"],
        key=lambda item: item["_dt"],
        reverse=True
    )
    previous_cycle = closed_cycles[0] if closed_cycles else None

    # Helper to build cycle summary using pre-fetched data
    def build_cycle_summary(cycle: dict | None) -> dict[str, object] | None:
        if not cycle:
            return None

        # Optimize get_cycle_window by using pre-fetched and sorted cycles
        start = cycle["_dt"]
        if start <= datetime.min:
            return None

        later_cycles = sorted(
            [c for c in cycles_all if c["id"] != cycle["id"] and c["_dt"] > start],
            key=lambda c: c["_dt"]
        )
        end = later_cycles[0]["_dt"] if later_cycles else None

        start_text = start.isoformat()
        end_text = end.isoformat() if end else None

        homologacoes_count = len(_filter_cycle_records(homologacoes_all, start_text, end_text, ()))
        customizacoes_count = len(_filter_cycle_records(customizacoes_all, start_text, end_text, ()))
        atividades_cycle = _filter_cycle_records(activities_all, start_text, end_text, ())
        releases_count = len(_filter_cycle_records(releases_all, start_text, end_text, ()))

        grouped_cycle: dict[str, dict[str, object]] = {}
        for activity in atividades_cycle:
            if activity.get("status") != "concluida":
                continue
            label = activity["_owner_label"]
            key = label.casefold()
            if key not in grouped_cycle:
                grouped_cycle[key] = {"owner": label, "count": 0}
            grouped_cycle[key]["count"] = int(grouped_cycle[key]["count"]) + 1

        tasks_by_owner = [
            {"owner": item["owner"], "count": item["count"]}
            for item in sorted(grouped_cycle.values(), key=lambda item: (-int(item["count"]), str(item["owner"])))
        ]

        return {
            "label": cycle.get("period_label") or f"Prestação {cycle.get('cycle_number') or cycle.get('id')}",
            "cycle_number": cycle.get("cycle_number"),
            "homologacoes": homologacoes_count,
            "customizacoes": customizacoes_count,
            "atividades": len(atividades_cycle),
            "releases": releases_count,
            "completed_tasks_total": sum(item["count"] for item in tasks_by_owner),
            "completed_tasks_by_owner": tasks_by_owner,
        }

    # Build summaries for current, previous and selected cycles
    previous_cycle_summary = build_cycle_summary(previous_cycle)
    current_cycle_summary = build_cycle_summary(open_cycle)

    selected_cycle_record = None
    if cycle_id:
        selected_cycle_record = next((c for c in cycles_all if c["id"] == cycle_id), None)
    selected_cycle_summary = build_cycle_summary(selected_cycle_record) if selected_cycle_record else None

    # Calculate global totals and grouped data
    grouped_global: dict[str, dict[str, object]] = {}
    for activity in activities_all:
        if activity.get("status") != "concluida":
            continue
        label = activity["_owner_label"]
        key = label.casefold()
        if key not in grouped_global:
            grouped_global[key] = {"owner": label, "count": 0}
        grouped_global[key]["count"] = int(grouped_global[key]["count"]) + 1

    completed_tasks_by_owner = [
        {"owner": item["owner"], "count": item["count"]}
        for item in sorted(grouped_global.values(), key=lambda item: (-int(item["count"]), str(item["owner"])))
    ]
    completed_tasks_total = sum(item["count"] for item in completed_tasks_by_owner)

    # Database connection only for remaining counts
    conn = get_conn()
    try:
        clients_count = run_query(conn, "SELECT COUNT(*) FROM clients").fetchone()[0]
        modules_count = run_query(conn, "SELECT COUNT(*) FROM modules").fetchone()[0]
    except Exception:
        clients_count = 0
        modules_count = 0
    conn.close()

    # Get active cycle started_at for main view filtering (not include_history)
    # Optimized: Find the open cycle from our pre-fetched cycles_all list
    active_cycle = open_cycle
    active_start = str(active_cycle["created_at"]) if active_cycle and active_cycle.get("created_at") else None

    summary = {
        "homologacoes": len(_filter_cycle_records(homologacoes_all, active_start, None, ())) if active_start else 0,
        "customizacoes": len(_filter_cycle_records(customizacoes_all, active_start, None, ())) if active_start else 0,
        "atividades": len(_filter_cycle_records(activities_all, active_start, None, ())) if active_start else 0,
        "releases": len(_filter_cycle_records(releases_all, active_start, None, ())) if active_start else 0,
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
