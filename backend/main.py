"""CS-Controle 360 - FastAPI Backend (API Only)."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import ensure_tables, reset_application_data, seed_from_snapshot, seed_demo_data_if_needed, _seed_activity_catalogs, get_conn
from .database import run_query
from .config import CORS_ORIGINS, RESET_SAMPLE_DATA_ON_STARTUP, assert_secure_secrets
from .routers import auth, homologacao, customizacao, atividade, release, cliente, modulo, reports, pdf_intelligence, playbooks
from .services.auth import bootstrap_default_admin, get_current_user

# Performance: Top-level imports to avoid repeated import overhead
from .models.atividade import list_atividade, normalize_person_name
from .models.customizacao import list_customizacao
from .models.homologacao import list_homologacao
from .models.release import list_release
from .models.report_cycle import get_cycle, list_cycles, parse_cycle_datetime


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


def _filter_cycle_records(records: list[dict], cycle_start: datetime | None, cycle_end: datetime | None) -> list[dict]:
    """Optimized filtering using pre-calculated _dt field."""
    if not cycle_start:
        return []

    filtered: list[dict] = []
    for record in records:
        record_dt = record.get("_dt", datetime.min)
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
    """Get summary of all entities for dashboard, optimized with pre-fetching and caching."""
    conn = get_conn()

    # Pre-fetch all data once with include_history=True to avoid N+1 and repeated DB calls
    all_activities = list_atividade(include_history=True)
    all_homologacoes = list_homologacao(include_history=True)
    all_customizacoes = list_customizacao(include_history=True)
    all_releases = list_release(include_history=True)

    # Pre-calculate common fields for filtering and display
    for activity in all_activities:
        val = _record_datetime(activity, ("created_at", "updated_at", "completed_at"))
        activity["_dt"] = parse_cycle_datetime(val)

        executor = normalize_person_name(activity.get("executor"))
        owner = normalize_person_name(activity.get("owner"))
        activity["_owner_label"] = executor or owner or "Sem responsável"

    for h in all_homologacoes:
        val = _record_datetime(h, ("check_date", "requested_production_date", "production_date", "created_at"))
        h["_dt"] = parse_cycle_datetime(val)

    for c in all_customizacoes:
        val = _record_datetime(c, ("received_at", "created_at"))
        c["_dt"] = parse_cycle_datetime(val)

    for r in all_releases:
        val = _record_datetime(r, ("applies_on", "created_at"))
        r["_dt"] = parse_cycle_datetime(val)

    cycles = list_cycles("reports")

    # Pre-parse created_at for all cycles to sort and windowing efficiently
    for cycle in cycles:
        cycle["_created_dt"] = parse_cycle_datetime(cycle.get("created_at"))

    open_cycle = next((cycle for cycle in cycles if cycle.get("status") == "aberto"), None)
    closed_cycles = [cycle for cycle in cycles if cycle.get("status") == "prestado"]
    closed_cycles.sort(key=lambda item: item["_created_dt"], reverse=True)
    previous_cycle = closed_cycles[0] if closed_cycles else None

    # Optimized window detection using pre-calculated cycles list
    def get_window(cid: int) -> tuple[datetime, datetime | None]:
        cycle = next((c for c in cycles if c["id"] == cid), None)
        if not cycle:
            return datetime.min, None
        start = cycle["_created_dt"]
        later = [c for c in cycles if c["id"] != cid and c["_created_dt"] > start]
        if not later:
            return start, None
        later.sort(key=lambda item: item["_created_dt"])
        return start, later[0]["_created_dt"]

    def build_cycle_summary(cycle: dict | None) -> dict[str, object] | None:
        if not cycle:
            return None

        start_dt, end_dt = get_window(cycle["id"])

        homologacoes_count = len(_filter_cycle_records(all_homologacoes, start_dt, end_dt))
        customizacoes_count = len(_filter_cycle_records(all_customizacoes, start_dt, end_dt))
        atividades_cycle = _filter_cycle_records(all_activities, start_dt, end_dt)
        releases_count = len(_filter_cycle_records(all_releases, start_dt, end_dt))

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

    previous_cycle_summary = build_cycle_summary(previous_cycle)
    current_cycle_summary = build_cycle_summary(open_cycle)

    selected_cycle_obj = get_cycle(cycle_id) if cycle_id else None
    selected_cycle_summary = build_cycle_summary(selected_cycle_obj) if selected_cycle_obj else None

    # Overall summary logic using pre-calculated results, preserving original filtering behavior
    if open_cycle:
        open_cycle_start = open_cycle["_created_dt"]
        current_activities = [a for a in all_activities if a["_dt"] >= open_cycle_start]
        current_homologacoes = [h for h in all_homologacoes if h["_dt"] >= open_cycle_start]
        current_customizacoes = [c for c in all_customizacoes if c["_dt"] >= open_cycle_start]
        current_releases = [r for r in all_releases if r["_dt"] >= open_cycle_start]
    else:
        current_activities = []
        current_homologacoes = []
        current_customizacoes = []
        current_releases = []

    grouped: dict[str, dict[str, object]] = {}
    for activity in current_activities:
        if activity.get("status") != "concluida":
            continue
        label = activity["_owner_label"]
        key = label.casefold()
        if key not in grouped:
            grouped[key] = {"owner": label, "count": 0}
        grouped[key]["count"] = int(grouped[key]["count"]) + 1

    completed_tasks_by_owner = [
        {"owner": item["owner"], "count": item["count"]}
        for item in sorted(grouped.values(), key=lambda item: (-int(item["count"]), str(item["owner"])))
    ]
    completed_tasks_total = sum(item["count"] for item in completed_tasks_by_owner)

    try:
        clients_count = run_query(conn, "SELECT COUNT(*) FROM clients").fetchone()[0]
        modules_count = run_query(conn, "SELECT COUNT(*) FROM modules").fetchone()[0]
    except Exception:
        clients_count = 0
        modules_count = 0

    summary = {
        "homologacoes": len(current_homologacoes),
        "customizacoes": len(current_customizacoes),
        "atividades": len(current_activities),
        "releases": len(current_releases),
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
