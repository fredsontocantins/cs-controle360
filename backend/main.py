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


def _filter_cycle_records(
    records: list[dict],
    start: datetime,
    end: datetime | None,
    keys: tuple[str, ...],
) -> list[dict]:
    from .models.report_cycle import parse_cycle_datetime

    filtered: list[dict] = []
    cache_key = f"_dt_{hash(keys)}"

    for record in records:
        # Cache the parsed datetime on the record dictionary to avoid redundant parsing
        record_dt = record.get(cache_key)
        if record_dt is None:
            record_value = _record_datetime(record, keys)
            if not record_value:
                continue
            record_dt = parse_cycle_datetime(record_value)
            record[cache_key] = record_dt

        if record_dt < start:
            continue
        if end and record_dt >= end:
            continue

        # Create a shallow copy to return, without the internal cache key
        # to avoid leaking implementation details into the JSON response.
        clean_record = record.copy()
        clean_record.pop(cache_key, None)
        filtered.append(clean_record)
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
    from .models.report_cycle import get_cycle, list_cycles, parse_cycle_datetime
    from .database import get_conn

    conn = get_conn()

    # Pre-fetch all data to avoid N+1 and redundant DB calls
    activities_all = list_atividade(include_history=True)
    customizacoes_all = list_customizacao(include_history=True)
    homologacoes_all = list_homologacao(include_history=True)
    releases_all = list_release(include_history=True)

    cycles = list_cycles("reports")
    # Pre-sort cycles chronologically to optimize window calculations
    cycles_sorted = sorted(cycles, key=lambda c: parse_cycle_datetime(c.get("created_at")))

    open_cycle = next((cycle for cycle in cycles if cycle.get("status") == "aberto"), None)
    closed_cycles = [cycle for cycle in cycles if cycle.get("status") == "prestado"]
    closed_cycles.sort(key=lambda item: parse_cycle_datetime(item.get("created_at")), reverse=True)
    previous_cycle = closed_cycles[0] if closed_cycles else None
    selected_cycle = get_cycle(cycle_id) if cycle_id else None

    # Pre-calculate windows for all cycles involved to avoid redundant list_cycles calls
    def precompute_window(cycle: dict | None) -> tuple[datetime, datetime | None]:
        if not cycle:
            return datetime.min, None
        start = parse_cycle_datetime(cycle.get("created_at"))
        if start <= datetime.min:
            return datetime.min, None
        # Find next cycle in pre-sorted chronological order
        end = None
        for c in cycles_sorted:
            c_start = parse_cycle_datetime(c.get("created_at"))
            if c["id"] != cycle["id"] and c_start > start:
                end = c_start
                break
        return start, end

    def build_cycle_summary(cycle: dict | None) -> dict[str, object] | None:
        if not cycle:
            return None

        start, end = precompute_window(cycle)
        if start <= datetime.min:
            return None

        homologacoes = len(_filter_cycle_records(
            homologacoes_all,
            start,
            end,
            ("check_date", "requested_production_date", "production_date", "created_at"),
        ))
        customizacoes = len(_filter_cycle_records(
            customizacoes_all,
            start,
            end,
            ("received_at", "created_at"),
        ))
        atividades_cycle = _filter_cycle_records(
            activities_all,
            start,
            end,
            ("created_at", "updated_at", "completed_at"),
        )
        releases = len(_filter_cycle_records(
            releases_all,
            start,
            end,
            ("applies_on", "created_at"),
        ))

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
            "homologacoes": homologacoes,
            "customizacoes": customizacoes,
            "atividades": len(atividades_cycle),
            "releases": releases,
            "completed_tasks_total": sum(item["count"] for item in tasks_by_owner),
            "completed_tasks_by_owner": tasks_by_owner,
        }

    previous_cycle_summary = build_cycle_summary(previous_cycle)
    current_cycle_summary = build_cycle_summary(open_cycle)
    selected_cycle_summary = build_cycle_summary(selected_cycle) if selected_cycle else None

    # Replicate original filtering logic from models to avoid redundant DB calls
    # but still matching previous endpoint behavior for global counts.
    from .models.report_cycle import get_active_cycle_started_at
    cycle_started_at_str = get_active_cycle_started_at("reports")
    cycle_started_at = parse_cycle_datetime(cycle_started_at_str) if cycle_started_at_str else None

    def matches_current_cycle(row: dict, keys: tuple[str, ...]) -> bool:
        if not cycle_started_at or cycle_started_at <= datetime.min:
            return False
        # Simplified version of model filtering logic
        for key in keys:
            val = row.get(key)
            if val and parse_cycle_datetime(val) >= cycle_started_at:
                return True
        return False

    current_homologacoes = [h for h in homologacoes_all if matches_current_cycle(h, ("check_date", "requested_production_date", "production_date", "created_at"))]
    current_customizacoes = [c for c in customizacoes_all if matches_current_cycle(c, ("received_at", "created_at"))]
    current_atividades = [a for a in activities_all if matches_current_cycle(a, ("created_at", "updated_at", "completed_at"))]
    current_releases = [r for r in releases_all if matches_current_cycle(r, ("applies_on", "created_at"))]

    # Calculate global counts for completed tasks (all time)
    completed_tasks_by_owner: list[dict[str, object]] = []
    grouped: dict[str, dict[str, object]] = {}
    for activity in activities_all:
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
        "homologacoes": len(current_homologacoes),
        "customizacoes": len(current_customizacoes),
        "atividades": len(current_atividades),
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
