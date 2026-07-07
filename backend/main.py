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


def _filter_cycle_records(records: list[dict], start_dt: datetime, end_dt: datetime | None, keys: tuple[str, ...]) -> list[dict]:
    """Filter records by a datetime window using pre-parsed datetimes when possible."""
    from .models.report_cycle import parse_cycle_datetime

    # start_dt and end_dt are expected to be datetime objects or None
    filtered: list[dict] = []
    for record in records:
        # Check cache first
        record_dt = record.get("_dt_cache")
        if not record_dt:
            record_value = _record_datetime(record, keys)
            if not record_value:
                continue
            record_dt = parse_cycle_datetime(record_value)
            # Cache it for other cycles in the same request
            record["_dt_cache"] = record_dt

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
    from .models.atividade import list_atividade, normalize_person_name
    from .models.customizacao import list_customizacao
    from .models.homologacao import list_homologacao
    from .models.release import list_release
    from .models.report_cycle import get_cycle, get_cycle_window, list_cycles, parse_cycle_datetime
    from .database import get_conn

    # 1. Pre-fetch entities with full history once to avoid redundant database calls.
    # For build_cycle_summary, we need history to filter by arbitrary cycle windows.
    # For global summary counts, we will filter this same list in-memory.
    from .models.atividade import _within_current_cycle as activity_within_cycle
    from .models.homologacao import _within_current_cycle as homologacao_within_cycle
    from .models.customizacao import _within_current_cycle as customization_within_cycle
    from .models.release import _within_current_cycle as release_within_cycle
    from .models.report_cycle import get_active_cycle_started_at

    activities_history = list_atividade(include_history=True)
    homologacoes_history = list_homologacao(include_history=True)
    customizacoes_history = list_customizacao(include_history=True)
    releases_history = list_release(include_history=True)

    # Derive "current" lists for global stats from history using the same logic as models
    active_cycle_start = get_active_cycle_started_at("reports")
    activities_current = [r for r in activities_history if activity_within_cycle(r, active_cycle_start)]
    homologacoes_current = [r for r in homologacoes_history if homologacao_within_cycle(r, active_cycle_start)]
    customizacoes_current = [r for r in customizacoes_history if customization_within_cycle(r, active_cycle_start)]
    releases_current = [r for r in releases_history if release_within_cycle(r, active_cycle_start)]
    cycles = list_cycles("reports")

    # 2. Identify relevant cycles and pre-calculate windows in one pass
    # We group cycles by scope to match get_cycle_window logic efficiently
    cycles_by_scope: dict[tuple[str, int | None], list[dict]] = {}
    for c in cycles:
        s_key = (str(c.get("scope_type") or "reports"), c.get("scope_id"))
        if s_key not in cycles_by_scope:
            cycles_by_scope[s_key] = []
        cycles_by_scope[s_key].append(c)

    # If selected_cycle is not in the pre-fetched "reports" cycles, fetch it and its scope
    selected_cycle = None
    if cycle_id:
        selected_cycle = next((c for c in cycles if c["id"] == cycle_id), None)
        if not selected_cycle:
            selected_cycle = get_cycle(cycle_id)
            if selected_cycle:
                s_key = (str(selected_cycle.get("scope_type") or "reports"), selected_cycle.get("scope_id"))
                if s_key not in cycles_by_scope:
                    cycles_by_scope[s_key] = list_cycles(s_key[0], s_key[1])

    # Pre-calculate windows for all relevant scopes
    cycle_windows = {}
    for scope_list in cycles_by_scope.values():
        sorted_scope = sorted(scope_list, key=lambda c: parse_cycle_datetime(c.get("created_at")))
        for i, cycle in enumerate(sorted_scope):
            start_dt = parse_cycle_datetime(cycle.get("created_at"))
            end_dt = parse_cycle_datetime(sorted_scope[i+1].get("created_at")) if i + 1 < len(sorted_scope) else None
            cycle_windows[cycle["id"]] = (start_dt, end_dt)

    open_cycle = next((cycle for cycle in cycles if cycle.get("status") == "aberto"), None)
    closed_cycles = [cycle for cycle in cycles if cycle.get("status") == "prestado"]
    closed_cycles.sort(key=lambda item: parse_cycle_datetime(item.get("created_at")), reverse=True)
    previous_cycle = closed_cycles[0] if closed_cycles else None

    def build_cycle_summary(cycle: dict | None) -> dict[str, object] | None:
        if not cycle:
            return None

        start_dt, end_dt = cycle_windows.get(cycle["id"], (None, None))
        label = cycle.get("period_label") or f"Prestação {cycle.get('cycle_number') or cycle.get('id')}"
        cycle_number = cycle.get("cycle_number")

        # Handle cycles with missing or invalid start dates by returning a zeroed summary
        if not start_dt or start_dt == parse_cycle_datetime(None):
            return {
                "label": label,
                "cycle_number": cycle_number,
                "homologacoes": 0,
                "customizacoes": 0,
                "atividades": 0,
                "releases": 0,
                "completed_tasks_total": 0,
                "completed_tasks_by_owner": [],
            }

        # Pass the history lists to the filter function to calculate windowed counts
        homologacoes_count = len(_filter_cycle_records(
            homologacoes_history,
            start_dt,
            end_dt,
            ("check_date", "requested_production_date", "production_date", "created_at"),
        ))
        customizacoes_count = len(_filter_cycle_records(
            customizacoes_history,
            start_dt,
            end_dt,
            ("received_at", "created_at"),
        ))
        atividades_cycle = _filter_cycle_records(
            activities_history,
            start_dt,
            end_dt,
            ("created_at", "updated_at", "completed_at"),
        )
        releases_count = len(_filter_cycle_records(
            releases_history,
            start_dt,
            end_dt,
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
            "label": label,
            "cycle_number": cycle_number,
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

    # 3. Clean up the cache from the entities before returning if we want to be strict,
    # but here they are just internal dicts. Let's reuse them for global stats.

    completed_tasks_by_owner: list[dict[str, object]] = []
    grouped: dict[str, dict[str, object]] = {}
    for activity in activities_current:
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

    conn = get_conn()
    try:
        clients_count = run_query(conn, "SELECT COUNT(*) FROM clients").fetchone()[0]
        modules_count = run_query(conn, "SELECT COUNT(*) FROM modules").fetchone()[0]
    except Exception:
        clients_count = 0
        modules_count = 0
    finally:
        conn.close()

    # 4. Remove internal cache keys from objects before sending response
    for coll in [activities_history, homologacoes_history, customizacoes_history, releases_history]:
        for item in coll:
            item.pop("_dt_cache", None)

    summary = {
        "homologacoes": len(homologacoes_current),
        "customizacoes": len(customizacoes_current),
        "atividades": len(activities_current),
        "releases": len(releases_current),
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
