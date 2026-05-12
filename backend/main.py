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
from .models.atividade import list_atividade, normalize_person_name
from .models.customizacao import list_customizacao
from .models.homologacao import list_homologacao
from .models.release import list_release
from .models.report_cycle import get_cycle, list_cycles, parse_cycle_datetime, get_active_cycle_started_at

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
    cycle_start = parse_cycle_datetime(start)
    cycle_end = parse_cycle_datetime(end) if end else None
    filtered: list[dict] = []
    for record in records:
        # Optimization: use pre-calculated _dt if available
        if "_dt" in record:
            record_dt = record["_dt"]
        else:
            record_value = _record_datetime(record, keys)
            if not record_value:
                continue
            record_dt = parse_cycle_datetime(record_value)
            record["_dt"] = record_dt # Cache for next cycle build in same request

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
    from .database import get_conn

    conn = get_conn()

    # Pre-fetch all data once to avoid N+1 queries
    all_activities = list_atividade(include_history=True)
    all_homologacoes = list_homologacao(include_history=True)
    all_customizacoes = list_customizacao(include_history=True)
    all_releases = list_release(include_history=True)

    cycles = list_cycles("reports")
    # Optimize cycle window calculation using pre-fetched cycles
    # Using a list comprehension to avoid in-place mutation of the original cycle records if possible,
    # but we need to keep the IDs for lookup.
    for cycle in cycles:
        cycle["_dt"] = parse_cycle_datetime(cycle.get("created_at"))

    sorted_cycles = sorted(cycles, key=lambda x: x["_dt"])

    def get_window(target_cycle: dict) -> tuple[datetime, datetime | None]:
        start = target_cycle["_dt"]
        # Fast lookup in pre-sorted list
        idx = next((i for i, c in enumerate(sorted_cycles) if c["id"] == target_cycle["id"]), -1)
        end = sorted_cycles[idx + 1]["_dt"] if idx != -1 and idx + 1 < len(sorted_cycles) else None
        return start, end

    open_cycle = next((cycle for cycle in cycles if cycle.get("status") == "aberto"), None)
    closed_cycles = [cycle for cycle in cycles if cycle.get("status") == "prestado"]
    closed_cycles.sort(key=lambda item: item["_dt"], reverse=True)
    previous_cycle = closed_cycles[0] if closed_cycles else None

    def build_cycle_summary(cycle: dict | None) -> dict[str, object] | None:
        if not cycle:
            return None
        start, end = get_window(cycle)
        start_text = start.isoformat()
        end_text = end.isoformat() if end else None

        homologacoes_count = len(_filter_cycle_records(
            all_homologacoes,
            start_text,
            end_text,
            ("check_date", "requested_production_date", "production_date", "created_at"),
        ))
        customizacoes_count = len(_filter_cycle_records(
            all_customizacoes,
            start_text,
            end_text,
            ("received_at", "created_at"),
        ))
        atividades_cycle = _filter_cycle_records(
            all_activities,
            start_text,
            end_text,
            ("created_at", "updated_at", "completed_at"),
        )
        releases_count = len(_filter_cycle_records(
            all_releases,
            start_text,
            end_text,
            ("applies_on", "created_at"),
        ))

        grouped_cycle: dict[str, dict[str, object]] = {}
        for activity in atividades_cycle:
            if activity.get("status") != "concluida":
                continue
            executor = normalize_person_name(activity.get("executor"))
            owner = normalize_person_name(activity.get("owner"))
            label = executor or owner or "Sem responsável"
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

    selected_cycle = None
    if cycle_id:
        selected_cycle = next((c for c in cycles if c["id"] == cycle_id), None)
        if not selected_cycle:
             selected_cycle = get_cycle(cycle_id)
             if selected_cycle:
                 selected_cycle["_dt"] = parse_cycle_datetime(selected_cycle.get("created_at"))

    selected_cycle_summary = build_cycle_summary(selected_cycle) if selected_cycle else None

    # Reuse current_cycle_summary for the main summary fields if available
    if current_cycle_summary:
        main_homologacoes = current_cycle_summary["homologacoes"]
        main_customizacoes = current_cycle_summary["customizacoes"]
        main_atividades_count = current_cycle_summary["atividades"]
        main_releases = current_cycle_summary["releases"]
        completed_tasks_total = current_cycle_summary["completed_tasks_total"]
        completed_tasks_by_owner = current_cycle_summary["completed_tasks_by_owner"]
    else:
        # Fallback to current filtered activities if no open cycle
        active_start = get_active_cycle_started_at("reports")
        if active_start:
            activities = _filter_cycle_records(all_activities, active_start, None, ("created_at", "updated_at", "completed_at"))
        else:
            activities = []

        main_homologacoes = 0
        main_customizacoes = 0
        main_atividades_count = len(activities)
        main_releases = 0

        grouped: dict[str, dict[str, object]] = {}
        for activity in activities:
            if activity.get("status") != "concluida":
                continue
            executor = normalize_person_name(activity.get("executor"))
            owner = normalize_person_name(activity.get("owner"))
            person_label = executor or owner or "Sem responsável"
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
        "homologacoes": main_homologacoes,
        "customizacoes": main_customizacoes,
        "atividades": main_atividades_count,
        "releases": main_releases,
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
