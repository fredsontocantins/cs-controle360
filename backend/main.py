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
    keys: tuple[str, ...]
) -> list[dict]:
    filtered: list[dict] = []
    for record in records:
        # Check for pre-parsed datetime first
        record_dt = None
        for key in keys:
            dt_key = f"_dt_{key}"
            if dt_key in record:
                record_dt = record[dt_key]
                break

        if not record_dt:
            continue

        if record_dt < start:
            continue
        if end and record_dt >= end:
            continue

        # Return a shallow copy without internal keys to avoid leaking them in JSON response
        filtered.append({k: v for k, v in record.items() if not k.startswith("_")})
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

    from .models.report_cycle import get_active_cycle_started_at

    # Pre-fetch all data once
    all_homologacoes = list_homologacao(include_history=True)
    all_customizacoes = list_customizacao(include_history=True)
    all_activities = list_atividade(include_history=True)
    all_releases = list_release(include_history=True)
    cycles = list_cycles("reports")

    cycle_started_at = get_active_cycle_started_at("reports")
    cycle_start_dt = parse_cycle_datetime(cycle_started_at) if cycle_started_at else None

    # Pre-parse dates and normalize names to avoid redundant processing in loops
    def pre_parse(records, date_keys, people_keys=None):
        for r in records:
            for k in date_keys:
                val = r.get(k)
                if val:
                    r[f"_dt_{k}"] = parse_cycle_datetime(val)
            if people_keys:
                for pk in people_keys:
                    r[f"_norm_{pk}"] = normalize_person_name(r.get(pk))

    pre_parse(all_homologacoes, ("check_date", "requested_production_date", "production_date", "created_at"))
    pre_parse(all_customizacoes, ("received_at", "created_at"))
    pre_parse(all_activities, ("created_at", "updated_at", "completed_at"), ("executor", "owner"))
    pre_parse(all_releases, ("applies_on", "created_at"))
    for c in cycles:
        c["_dt_created_at"] = parse_cycle_datetime(c.get("created_at"))

    # Identify open and previous cycles from pre-fetched list
    open_cycle = next((cycle for cycle in cycles if cycle.get("status") == "aberto"), None)
    closed_cycles = [cycle for cycle in cycles if cycle.get("status") == "prestado"]
    closed_cycles.sort(key=lambda item: item["_dt_created_at"], reverse=True)
    previous_cycle = closed_cycles[0] if closed_cycles else None

    # Find selected cycle if provided
    selected_cycle = None
    if cycle_id:
        selected_cycle = next((c for c in cycles if c.get("id") == cycle_id), None)
        if not selected_cycle:
            selected_cycle = get_cycle(cycle_id)
            if selected_cycle:
                selected_cycle["_dt_created_at"] = parse_cycle_datetime(selected_cycle.get("created_at"))

    # Pre-sort cycles chronologically for window calculation
    sorted_cycles = sorted(cycles, key=lambda x: x["_dt_created_at"])

    def _get_record_dt(record: dict, keys: tuple[str, ...]) -> datetime | None:
        for k in keys:
            dt_key = f"_dt_{k}"
            if dt_key in record:
                return record[dt_key]
        return None

    def build_cycle_summary(cycle: dict | None) -> dict[str, object] | None:
        if not cycle:
            return None

        # Calculate window in-memory using sorted_cycles
        start = cycle["_dt_created_at"]
        end = None
        for i, c in enumerate(sorted_cycles):
            if c["id"] == cycle["id"]:
                if i + 1 < len(sorted_cycles):
                    end = sorted_cycles[i + 1]["_dt_created_at"]
                break

        homologacoes_count = len(_filter_cycle_records(
            all_homologacoes,
            start,
            end,
            ("check_date", "requested_production_date", "production_date", "created_at"),
        ))
        customizacoes_count = len(_filter_cycle_records(
            all_customizacoes,
            start,
            end,
            ("received_at", "created_at"),
        ))
        atividades_cycle = _filter_cycle_records(
            all_activities,
            start,
            end,
            ("created_at", "updated_at", "completed_at"),
        )
        releases_count = len(_filter_cycle_records(
            all_releases,
            start,
            end,
            ("applies_on", "created_at"),
        ))

        tasks_by_owner: list[dict[str, object]] = []
        grouped_cycle: dict[str, dict[str, object]] = {}
        for activity in atividades_cycle:
            if activity.get("status") != "concluida":
                continue
            # Use pre-normalized names
            executor = activity.get("_norm_executor")
            owner = activity.get("_norm_owner")
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
    selected_cycle_summary = build_cycle_summary(selected_cycle)

    # Derive global summary counts from pre-fetched lists
    def _clean(r): return {k: v for k, v in r.items() if not k.startswith("_dt_")}

    current_homologacoes = [
        _clean(r) for r in all_homologacoes
        if cycle_start_dt and (dt := _get_record_dt(r, ("check_date", "requested_production_date", "production_date", "created_at")))
        and dt >= cycle_start_dt
    ]
    current_customizacoes = [
        _clean(r) for r in all_customizacoes
        if cycle_start_dt and (dt := _get_record_dt(r, ("received_at", "created_at")))
        and dt >= cycle_start_dt
    ]
    current_activities = [
        _clean(r) for r in all_activities
        if cycle_start_dt and (dt := _get_record_dt(r, ("created_at", "updated_at", "completed_at")))
        and dt >= cycle_start_dt
    ]
    current_releases = [
        _clean(r) for r in all_releases
        if cycle_start_dt and (dt := _get_record_dt(r, ("applies_on", "created_at")))
        and dt >= cycle_start_dt
    ]

    # Derive global summary counts from pre-fetched lists
    def _clean(r): return {k: v for k, v in r.items() if not k.startswith("_")}

    current_homologacoes = [
        _clean(r) for r in all_homologacoes
        if cycle_start_dt and (dt := _get_record_dt(r, ("check_date", "requested_production_date", "production_date", "created_at")))
        and dt >= cycle_start_dt
    ]
    current_customizacoes = [
        _clean(r) for r in all_customizacoes
        if cycle_start_dt and (dt := _get_record_dt(r, ("received_at", "created_at")))
        and dt >= cycle_start_dt
    ]
    current_activities = [
        _clean(r) for r in all_activities
        if cycle_start_dt and (dt := _get_record_dt(r, ("created_at", "updated_at", "completed_at")))
        and dt >= cycle_start_dt
    ]
    current_releases = [
        _clean(r) for r in all_releases
        if cycle_start_dt and (dt := _get_record_dt(r, ("applies_on", "created_at")))
        and dt >= cycle_start_dt
    ]

    # Redo grouping and cleaning properly
    current_activities_raw = [
        r for r in all_activities
        if cycle_start_dt and (dt := _get_record_dt(r, ("created_at", "updated_at", "completed_at")))
        and dt >= cycle_start_dt
    ]
    current_activities = [_clean(r) for r in current_activities_raw]

    completed_tasks_by_owner: list[dict[str, object]] = []
    grouped: dict[str, dict[str, object]] = {}
    for activity in current_activities_raw:
        if activity.get("status") != "concluida":
            continue
        executor = activity.get("_norm_executor")
        owner = activity.get("_norm_owner")
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
        "atividades": len(current_activities_raw),
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
