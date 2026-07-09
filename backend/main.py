"""CS-Controle 360 - FastAPI Backend (API Only)."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime

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


def _record_datetime(entity: dict, keys: tuple[str, ...]) -> datetime | None:
    # Use cached datetime if available
    for key in keys:
        cache_key = f"_dt_{key}"
        if cache_key in entity:
            return entity[cache_key]

        value = entity.get(key)
        if value:
            from .models.report_cycle import parse_cycle_datetime
            dt = parse_cycle_datetime(value)
            entity[cache_key] = dt # Cache it
            return dt
    return None


def _filter_cycle_records(records: list[dict], cycle_start: datetime, cycle_end: datetime | None, keys: tuple[str, ...]) -> list[dict]:
    if cycle_start <= datetime.min:
        return []

    filtered: list[dict] = []
    for record in records:
        record_dt = _record_datetime(record, keys)
        if not record_dt:
            continue
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
    from .models.report_cycle import get_cycle, get_cycle_window, list_cycles, parse_cycle_datetime, get_active_cycle_started_at
    from .database import get_conn

    # 1. Pre-fetch everything once
    all_activities = list_atividade(include_history=True)
    all_homologacoes = list_homologacao(include_history=True)
    all_customizacoes = list_customizacao(include_history=True)
    all_releases = list_release(include_history=True)

    cycles = list_cycles("reports")
    open_cycle = next((cycle for cycle in cycles if cycle.get("status") == "aberto"), None)
    closed_cycles = [cycle for cycle in cycles if cycle.get("status") == "prestado"]
    # Assuming list_cycles already sorts by created_at DESC, but ensuring here
    closed_cycles.sort(key=lambda item: parse_cycle_datetime(item.get("created_at")), reverse=True)
    previous_cycle = closed_cycles[0] if closed_cycles else None

    # Pre-parse names for efficiency in grouping
    def pre_parse(records):
        for r in records:
            if "executor" in r:
                r["_norm_executor"] = normalize_person_name(r["executor"])
            if "owner" in r:
                r["_norm_owner"] = normalize_person_name(r["owner"])

    pre_parse(all_activities)

    def build_cycle_summary(cycle: dict | None) -> dict[str, object] | None:
        if not cycle:
            return None
        start, end = get_cycle_window(cycle["id"])
        if not start or start <= datetime.min:
            return None

        homologacoes_cycle = _filter_cycle_records(
            all_homologacoes, start, end,
            ("check_date", "requested_production_date", "production_date", "created_at"),
        )
        customizacoes_cycle = _filter_cycle_records(
            all_customizacoes, start, end,
            ("received_at", "created_at"),
        )
        atividades_cycle = _filter_cycle_records(
            all_activities, start, end,
            ("created_at", "updated_at", "completed_at"),
        )
        releases_cycle = _filter_cycle_records(
            all_releases, start, end,
            ("applies_on", "created_at"),
        )

        grouped_cycle: dict[str, dict[str, object]] = {}
        for activity in atividades_cycle:
            if activity.get("status") != "concluida":
                continue
            label = activity.get("_norm_executor") or activity.get("_norm_owner") or "Sem responsável"
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

    selected_cycle_obj = get_cycle(cycle_id) if cycle_id else None
    selected_cycle_summary = build_cycle_summary(selected_cycle_obj) if selected_cycle_obj else None

    # Global summary counts (filtered by current cycle as per original logic)
    current_cycle_start_str = get_active_cycle_started_at("reports")
    current_cycle_start = parse_cycle_datetime(current_cycle_start_str) if current_cycle_start_str else datetime.min

    current_homologacoes = _filter_cycle_records(all_homologacoes, current_cycle_start, None, ("check_date", "requested_production_date", "production_date", "created_at"))
    current_customizacoes = _filter_cycle_records(all_customizacoes, current_cycle_start, None, ("received_at", "created_at"))
    current_activities = _filter_cycle_records(all_activities, current_cycle_start, None, ("created_at", "updated_at", "completed_at"))
    current_releases = _filter_cycle_records(all_releases, current_cycle_start, None, ("applies_on", "created_at"))

    # Global task grouping (from current activities)
    grouped: dict[str, dict[str, object]] = {}
    for activity in current_activities:
        if activity.get("status") != "concluida":
            continue
        person_label = activity.get("_norm_executor") or activity.get("_norm_owner") or "Sem responsável"
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

    # Clean up internal cached keys before returning
    def cleanup(records):
        for r in records:
            for k in list(r.keys()):
                if k.startswith("_"):
                    del r[k]

    cleanup(all_activities)
    cleanup(all_homologacoes)
    cleanup(all_customizacoes)
    cleanup(all_releases)

    summary = {
        "homologacoes": len(all_homologacoes),
        "customizacoes": len(all_customizacoes),
        "atividades": len(all_activities),
        "releases": len(all_releases),
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
