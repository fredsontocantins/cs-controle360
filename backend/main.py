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


from datetime import datetime

def _record_datetime(entity: dict, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = entity.get(key)
        if value:
            return str(value)
    return None


def _filter_cycle_records(records: list[dict], start: datetime, end: datetime | None, keys: tuple[str, ...]) -> list[dict]:
    """Filter records within a cycle window, caching parsed datetimes on the records."""
    from .models.report_cycle import parse_cycle_datetime

    # Use a cache key to avoid repeated parsing of the same records
    cache_key = f"_dt_{hash(keys)}"
    filtered: list[dict] = []

    for record in records:
        record_dt = record.get(cache_key)
        if record_dt is None:
            record_value = _record_datetime(record, keys)
            if not record_value:
                record[cache_key] = datetime.min
                continue
            record_dt = parse_cycle_datetime(record_value)
            record[cache_key] = record_dt

        if record_dt <= datetime.min:
            continue
        if record_dt < start:
            continue
        if end and record_dt >= end:
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
    from .models.report_cycle import get_cycle, get_cycle_window, list_cycles, parse_cycle_datetime
    from .database import get_conn

    conn = get_conn()
    cycles = list_cycles("reports")

    # Pre-fetch all history once
    all_activities = list_atividade(include_history=True)
    all_homologacoes = list_homologacao(include_history=True)
    all_customizacoes = list_customizacao(include_history=True)
    all_releases = list_release(include_history=True)

    open_cycle = next((cycle for cycle in cycles if cycle.get("status") == "aberto"), None)
    closed_cycles = [cycle for cycle in cycles if cycle.get("status") == "prestado"]
    closed_cycles.sort(key=lambda item: parse_cycle_datetime(item.get("created_at")), reverse=True)
    previous_cycle = closed_cycles[0] if closed_cycles else None

    selected_cycle = get_cycle(cycle_id) if cycle_id else None

    # Pre-calculate windows to avoid redundant list_cycles calls
    # get_cycle_window re-lists cycles every time. We can optimize this by using our 'cycles' list.
    def get_window_from_list(cycle: dict | None) -> tuple[datetime, datetime | None]:
        if not cycle:
            return datetime.min, None
        start = parse_cycle_datetime(cycle.get("created_at"))
        if start <= datetime.min:
            return datetime.min, None

        # cycles is already sorted DESC by created_at from list_cycles()
        later_cycles = [
            c for c in cycles
            if c["id"] != cycle["id"] and parse_cycle_datetime(c.get("created_at")) > start
        ]
        later_cycles.sort(key=lambda c: parse_cycle_datetime(c.get("created_at")))
        end = parse_cycle_datetime(later_cycles[0].get("created_at")) if later_cycles else None
        return start, end

    def build_cycle_summary(cycle: dict | None) -> dict[str, object] | None:
        if not cycle:
            return None

        start_dt, end_dt = get_window_from_list(cycle)
        if start_dt <= datetime.min:
            return None

        homologacoes_cycle = _filter_cycle_records(
            all_homologacoes,
            start_dt,
            end_dt,
            ("check_date", "requested_production_date", "production_date", "created_at"),
        )
        customizacoes_cycle = _filter_cycle_records(
            all_customizacoes,
            start_dt,
            end_dt,
            ("received_at", "created_at"),
        )
        atividades_cycle = _filter_cycle_records(
            all_activities,
            start_dt,
            end_dt,
            ("created_at", "updated_at", "completed_at"),
        )
        releases_cycle = _filter_cycle_records(
            all_releases,
            start_dt,
            end_dt,
            ("applies_on", "created_at"),
        )

        tasks_by_owner: list[dict[str, object]] = []
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
            "homologacoes": len(homologacoes_cycle),
            "customizacoes": len(customizacoes_cycle),
            "atividades": len(atividades_cycle),
            "releases": len(releases_cycle),
            "completed_tasks_total": sum(item["count"] for item in tasks_by_owner),
            "completed_tasks_by_owner": tasks_by_owner,
        }

    previous_cycle_summary = build_cycle_summary(previous_cycle)
    current_cycle_summary = build_cycle_summary(open_cycle)
    selected_cycle_summary = build_cycle_summary(selected_cycle)

    if current_cycle_summary:
        completed_tasks_by_owner = current_cycle_summary["completed_tasks_by_owner"]
        completed_tasks_total = current_cycle_summary["completed_tasks_total"]
    else:
        completed_tasks_by_owner = []
        completed_tasks_total = 0

    try:
        clients_count = run_query(conn, "SELECT COUNT(*) FROM clients").fetchone()[0]
        modules_count = run_query(conn, "SELECT COUNT(*) FROM modules").fetchone()[0]
    except Exception:
        clients_count = 0
        modules_count = 0

    # Clean up internal cache keys before returning
    for records in (all_activities, all_homologacoes, all_customizacoes, all_releases):
        for r in records:
            for k in list(r.keys()):
                if k.startswith("_dt_"):
                    r.pop(k)

    summary = {
        "homologacoes": current_cycle_summary["homologacoes"] if current_cycle_summary else 0,
        "customizacoes": current_cycle_summary["customizacoes"] if current_cycle_summary else 0,
        "atividades": current_cycle_summary["atividades"] if current_cycle_summary else 0,
        "releases": current_cycle_summary["releases"] if current_cycle_summary else 0,
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
