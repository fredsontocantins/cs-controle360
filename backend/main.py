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

# Pre-import models for get_summary optimization
from .models.atividade import list_atividade, normalize_person_name
from .models.customizacao import list_customizacao
from .models.homologacao import list_homologacao
from .models.release import list_release
from .models.report_cycle import list_cycles, parse_cycle_datetime
from .database import get_conn

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
    # Use pre-calculated _dt if available for performance
    if "_dt" in entity:
        return None  # We should use _dt directly in filter
    for key in keys:
        value = entity.get(key)
        if value:
            return str(value)
    return None


def _filter_cycle_records(records: list[dict], start_dt: datetime | None, end_dt: datetime | None, keys: tuple[str, ...]) -> list[dict]:
    if not start_dt:
        return []
    filtered: list[dict] = []
    for record in records:
        # Optimization: use pre-calculated _dt if available
        record_dt = record.get("_dt")
        if not record_dt:
            record_value = _record_datetime(record, keys)
            if not record_value:
                continue
            record_dt = parse_cycle_datetime(record_value)
            # Cache it for other filters in same request
            record["_dt"] = record_dt

        if record_dt < start_dt:
            continue
        if end_dt and record_dt >= end_dt:
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
    conn = get_conn()
    # Pre-fetch all data once to avoid repeated DB calls and processing
    activities = list_atividade(include_history=True)
    homologations = list_homologacao(include_history=True)
    customizations = list_customizacao(include_history=True)
    releases_list = list_release(include_history=True)

    # Pre-calculate normalized names and dates for activities
    for activity in activities:
        activity["_owner_label"] = normalize_person_name(activity.get("executor") or activity.get("owner"))
        activity["_dt"] = parse_cycle_datetime(activity.get("created_at") or activity.get("updated_at") or activity.get("completed_at"))

    cycles = list_cycles("reports")
    # Pre-parse cycle created_at for sorting and windowing
    for cycle in cycles:
        cycle["_dt"] = parse_cycle_datetime(cycle.get("created_at"))

    open_cycle = next((cycle for cycle in cycles if cycle.get("status") == "aberto"), None)
    closed_cycles = [cycle for cycle in cycles if cycle.get("status") == "prestado"]
    closed_cycles.sort(key=lambda item: item["_dt"], reverse=True)
    previous_cycle = closed_cycles[0] if closed_cycles else None

    # Helper to get cycle window without additional DB calls
    def get_window_optimized(cid: int) -> tuple[datetime, datetime | None]:
        target = next((c for c in cycles if c["id"] == cid), None)
        if not target:
            return datetime.min, None
        start = target["_dt"]
        # Find the next cycle in chronological order
        later = [c for c in cycles if c["id"] != cid and c["_dt"] > start]
        later.sort(key=lambda x: x["_dt"])
        end = later[0]["_dt"] if later else None
        return start, end

    def build_cycle_summary(cycle: dict | None) -> dict[str, object] | None:
        if not cycle:
            return None
        start_dt, end_dt = get_window_optimized(cycle["id"])

        homologacoes_count = len(_filter_cycle_records(
            homologations, start_dt, end_dt,
            ("check_date", "requested_production_date", "production_date", "created_at"),
        ))
        customizacoes_count = len(_filter_cycle_records(
            customizations, start_dt, end_dt,
            ("received_at", "created_at"),
        ))
        atividades_cycle = _filter_cycle_records(
            activities, start_dt, end_dt,
            ("created_at", "updated_at", "completed_at"),
        )
        releases_count = len(_filter_cycle_records(
            releases_list, start_dt, end_dt,
            ("applies_on", "created_at"),
        ))

        tasks_by_owner: list[dict[str, object]] = []
        grouped_cycle: dict[str, dict[str, object]] = {}
        for activity in atividades_cycle:
            if activity.get("status") != "concluida":
                continue
            label = activity.get("_owner_label") or "Sem responsável"
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
    selected_cycle_summary = build_cycle_summary(next((c for c in cycles if c["id"] == cycle_id), None)) if cycle_id else None

    completed_tasks_by_owner: list[dict[str, object]] = []
    grouped: dict[str, dict[str, object]] = {}
    for activity in activities:
        # Only count in main activities list (current cycle by default if not include_history)
        # But here list_atividade was called with include_history=True.
        # Original code used `activities = list_atividade()` which defaults to current cycle.
        # To preserve behavior for the main summary counts:
        pass

    # Wait, the original code had `activities = list_atividade()` which filters by current cycle.
    # I should re-fetch or filter from pre-fetched for the "total" summary.
    # Actually, the original summary returned ALL activities for total counts?
    # Let me re-read.
    # original: activities = list_atividade() (NOT include_history)
    # Then it used it for summary["atividades"] = len(activities)
    # AND for completed_tasks_by_owner.

    from .models.report_cycle import get_active_cycle_started_at
    current_start_at = get_active_cycle_started_at("reports")
    current_start_dt = parse_cycle_datetime(current_start_at) if current_start_at else None

    # Filter for "current" activities as per original behavior
    current_activities = [a for a in activities if current_start_dt and a["_dt"] >= current_start_dt] if current_start_dt else []

    for activity in current_activities:
        if activity.get("status") != "concluida":
            continue
        person_label = activity.get("_owner_label") or "Sem responsável"
        person_key = person_label.casefold()
        if person_key not in grouped:
            grouped[person_key] = {"owner": person_label, "count": 0}
        grouped[person_key]["count"] = int(grouped[person_key]["count"]) + 1

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
        "homologacoes": len([h for h in homologations if current_start_dt and h.get("_dt", parse_cycle_datetime(h.get("check_date") or h.get("created_at"))) >= current_start_dt]) if current_start_dt else 0,
        "customizacoes": len([c for c in customizations if current_start_dt and c.get("_dt", parse_cycle_datetime(c.get("received_at") or c.get("created_at"))) >= current_start_dt]) if current_start_dt else 0,
        "atividades": len(current_activities),
        "releases": len([r for r in releases_list if current_start_dt and r.get("_dt", parse_cycle_datetime(r.get("applies_on") or r.get("created_at"))) >= current_start_dt]) if current_start_dt else 0,
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
