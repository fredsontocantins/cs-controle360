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


def _record_datetime(entity: dict, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = entity.get(key)
        if value:
            return str(value)
    return None


def _filter_cycle_records(records: list[dict], cycle_start: datetime, cycle_end: datetime | None, keys: tuple[str, ...]) -> list[dict]:
    filtered: list[dict] = []
    for record in records:
        # Optimization: use pre-parsed datetime if available
        record_dt = record.get("_dt_record")
        if not record_dt:
            record_value = _record_datetime(record, keys)
            if not record_value:
                continue
            from .models.report_cycle import parse_cycle_datetime
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
    from .models.report_cycle import get_cycle, get_cycle_window, list_cycles, parse_cycle_datetime
    from .database import get_conn
    from datetime import datetime

    # 1. Pre-fetch all data once
    all_homologacoes = list_homologacao(include_history=True)
    all_customizacoes = list_customizacao(include_history=True)
    all_activities = list_atividade(include_history=True)
    all_releases = list_release(include_history=True)
    cycles = list_cycles("reports")

    # 2. Pre-parse datetimes and normalize names to avoid redundant work in loops
    def pre_parse(records, keys, name_keys=None):
        for r in records:
            dt_str = _record_datetime(r, keys)
            r["_dt_record"] = parse_cycle_datetime(dt_str) if dt_str else datetime.min
            if name_keys:
                for nk in name_keys:
                    r[f"_norm_{nk}"] = normalize_person_name(r.get(nk))

    pre_parse(all_homologacoes, ("check_date", "requested_production_date", "production_date", "created_at"))
    pre_parse(all_customizacoes, ("received_at", "created_at"))
    pre_parse(all_activities, ("created_at", "updated_at", "completed_at"), ("executor", "owner"))
    pre_parse(all_releases, ("applies_on", "created_at"))
    for c in cycles:
        c["_dt_created"] = parse_cycle_datetime(c.get("created_at"))

    # Determine cycles
    open_cycle = next((c for c in cycles if c.get("status") == "aberto"), None)
    closed_cycles = sorted([c for c in cycles if c.get("status") == "prestado"], key=lambda x: x["_dt_created"], reverse=True)
    previous_cycle = closed_cycles[0] if closed_cycles else None

    # Pre-calculate windows for all cycles involved to avoid redundant list_cycles calls
    # We can use cycles list which is already sorted by created_at DESC from list_cycles
    cycle_map = {c["id"]: c for c in cycles}
    sorted_cycles = sorted(cycles, key=lambda x: x["_dt_created"])

    def get_window_optimized(cid: int):
        target = cycle_map.get(cid)
        if not target: return datetime.min, None
        start = target["_dt_created"]
        # Find next cycle in chronological order
        idx = sorted_cycles.index(target)
        end = sorted_cycles[idx+1]["_dt_created"] if idx + 1 < len(sorted_cycles) else None
        return start, end

    def build_cycle_summary(cycle: dict | None) -> dict[str, object] | None:
        if not cycle:
            return None

        start, end = get_window_optimized(cycle["id"])
        if start <= datetime.min:
            return None

        homo_count = len(_filter_cycle_records(all_homologacoes, start, end, ()))
        cust_count = len(_filter_cycle_records(all_customizacoes, start, end, ()))
        activities_cycle = _filter_cycle_records(all_activities, start, end, ())
        rel_count = len(_filter_cycle_records(all_releases, start, end, ()))

        grouped_cycle: dict[str, dict[str, object]] = {}
        for activity in activities_cycle:
            if activity.get("status") != "concluida":
                continue
            executor = activity.get("_norm_executor")
            owner = activity.get("_norm_owner")
            label = executor or owner or "Sem responsável"
            key = label.casefold()
            if key not in grouped_cycle:
                grouped_cycle[key] = {"owner": label, "count": 0}
            grouped_cycle[key]["count"] += 1

        tasks_by_owner = [
            {"owner": item["owner"], "count": item["count"]}
            for item in sorted(grouped_cycle.values(), key=lambda item: (-int(item["count"]), str(item["owner"])))
        ]

        return {
            "label": cycle.get("period_label") or f"Prestação {cycle.get('cycle_number') or cycle.get('id')}",
            "cycle_number": cycle.get("cycle_number"),
            "homologacoes": homo_count,
            "customizacoes": cust_count,
            "atividades": len(activities_cycle),
            "releases": rel_count,
            "completed_tasks_total": sum(item["count"] for item in tasks_by_owner),
            "completed_tasks_by_owner": tasks_by_owner,
        }

    previous_cycle_summary = build_cycle_summary(previous_cycle)
    current_cycle_summary = build_cycle_summary(open_cycle)
    selected_cycle_summary = build_cycle_summary(cycle_map.get(cycle_id)) if cycle_id else None

    # Global summary
    grouped: dict[str, dict[str, object]] = {}
    for activity in all_activities:
        # Note: top-level activities summary in original code uses list_atividade() WITHOUT include_history
        # This filters by CURRENT cycle if no history included.
        # But wait, looking at original code: `activities = list_atividade()`
        # list_atividade() defaults to include_history=False, so it filters by active cycle.

        # Let's re-filter all_activities for the "current" view (which is what list_atividade() does)
        # Actually, let's just use the logic from list_atividade:
        pass

    # list_atividade() filter logic:
    active_cycle_start_str = next((c.get("created_at") for c in cycles if c.get("status") == "aberto"), None)
    active_cycle_start = parse_cycle_datetime(active_cycle_start_str) if active_cycle_start_str else datetime.min

    current_activities = [a for a in all_activities if a["_dt_record"] >= active_cycle_start] if active_cycle_start > datetime.min else []

    for activity in current_activities:
        if activity.get("status") != "concluida":
            continue
        person_label = activity.get("_norm_executor") or activity.get("_norm_owner") or "Sem responsável"
        person_key = person_label.casefold()
        if person_key not in grouped:
            grouped[person_key] = {"owner": person_label, "count": 0}
        grouped[person_key]["count"] += 1

    completed_tasks_by_owner = [
        {"owner": item["owner"], "count": item["count"]}
        for item in sorted(grouped.values(), key=lambda item: (-int(item["count"]), str(item["owner"])))
    ]

    conn = get_conn()
    try:
        clients_count = run_query(conn, "SELECT COUNT(*) FROM clients").fetchone()[0]
        modules_count = run_query(conn, "SELECT COUNT(*) FROM modules").fetchone()[0]
    except Exception:
        clients_count = 0
        modules_count = 0
    finally:
        conn.close()

    summary = {
        "homologacoes": len([h for h in all_homologacoes if h["_dt_record"] >= active_cycle_start]) if active_cycle_start > datetime.min else 0,
        "customizacoes": len([c for c in all_customizacoes if c["_dt_record"] >= active_cycle_start]) if active_cycle_start > datetime.min else 0,
        "atividades": len(current_activities),
        "releases": len([r for r in all_releases if r["_dt_record"] >= active_cycle_start]) if active_cycle_start > datetime.min else 0,
        "clientes": clients_count,
        "modulos": modules_count,
        "completed_tasks_total": sum(item["count"] for item in completed_tasks_by_owner),
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
