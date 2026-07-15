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


from datetime import datetime as dt_type

def _filter_cycle_records(records: list[dict], start: dt_type | str, end: dt_type | str | None, keys: tuple[str, ...]) -> list[dict]:
    """Filter records by cycle window using pre-parsed datetime objects if available."""
    from .models.report_cycle import parse_cycle_datetime

    # If start/end are strings, parse them once
    cycle_start = parse_cycle_datetime(start) if isinstance(start, str) else start
    cycle_end = parse_cycle_datetime(end) if isinstance(end, str) else end

    filtered: list[dict] = []
    for record in records:
        # Check for pre-parsed datetime in record cache
        record_dt = None
        for key in keys:
            cache_key = f"_dt_{key}"
            if cache_key in record:
                record_dt = record[cache_key]
                if record_dt:
                    break

        if not record_dt:
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
    """Get summary of all entities for dashboard with optimized batch processing."""
    from .models.atividade import list_atividade, normalize_person_name
    from .models.customizacao import list_customizacao
    from .models.homologacao import list_homologacao
    from .models.release import list_release
    from .models.report_cycle import get_cycle, list_cycles, parse_cycle_datetime
    from .database import get_conn

    # 1. Batch pre-fetch everything from database
    all_activities = list_atividade(include_history=True)
    all_homologations = list_homologacao(include_history=True)
    all_customizations = list_customizacao(include_history=True)
    all_releases = list_release(include_history=True)
    cycles = list_cycles("reports")

    # 2. Pre-parse datetimes and normalize names to avoid repeated work
    for act in all_activities:
        for k in ("created_at", "updated_at", "completed_at"):
            act[f"_dt_{k}"] = parse_cycle_datetime(act.get(k))
        # Pre-normalize and cache names
        act["_norm_executor"] = normalize_person_name(act.get("executor"))
        act["_norm_owner"] = normalize_person_name(act.get("owner"))

    for hom in all_homologations:
        for k in ("check_date", "requested_production_date", "production_date", "created_at"):
            hom[f"_dt_{k}"] = parse_cycle_datetime(hom.get(k))

    for cust in all_customizations:
        for k in ("received_at", "created_at"):
            cust[f"_dt_{k}"] = parse_cycle_datetime(cust.get(k))

    for rel in all_releases:
        for k in ("applies_on", "created_at"):
            rel[f"_dt_{k}"] = parse_cycle_datetime(rel.get(k))

    # 3. Calculate cycle windows in-memory
    # Sort cycles chronologically to find windows easily
    sorted_cycles = sorted(cycles, key=lambda c: parse_cycle_datetime(c.get("created_at")))
    cycle_windows = {}
    for i, c in enumerate(sorted_cycles):
        start = parse_cycle_datetime(c.get("created_at"))
        end = parse_cycle_datetime(sorted_cycles[i+1].get("created_at")) if i + 1 < len(sorted_cycles) else None
        cycle_windows[c["id"]] = (start, end)

    open_cycle = next((c for c in cycles if c.get("status") == "aberto"), None)
    closed_cycles = [c for c in cycles if c.get("status") == "prestado"]
    closed_cycles.sort(key=lambda c: parse_cycle_datetime(c.get("created_at")), reverse=True)
    previous_cycle = closed_cycles[0] if closed_cycles else None

    def build_cycle_summary(cycle: dict | None) -> dict[str, object] | None:
        if not cycle or cycle["id"] not in cycle_windows:
            return None

        start, end = cycle_windows[cycle["id"]]

        homologacoes_count = len(_filter_cycle_records(
            all_homologations, start, end,
            ("check_date", "requested_production_date", "production_date", "created_at"),
        ))
        customizacoes_count = len(_filter_cycle_records(
            all_customizations, start, end,
            ("received_at", "created_at"),
        ))
        atividades_cycle = _filter_cycle_records(
            all_activities, start, end,
            ("created_at", "updated_at", "completed_at"),
        )
        releases_count = len(_filter_cycle_records(
            all_releases, start, end,
            ("applies_on", "created_at"),
        ))

        grouped_cycle: dict[str, dict[str, object]] = {}
        for activity in atividades_cycle:
            if activity.get("status") != "concluida":
                continue
            label = activity["_norm_executor"] or activity["_norm_owner"] or "Sem responsável"
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

    # 4. Build summaries using pre-fetched and pre-processed data
    previous_cycle_summary = build_cycle_summary(previous_cycle)
    current_cycle_summary = build_cycle_summary(open_cycle)

    selected_cycle_obj = get_cycle(cycle_id) if cycle_id else None
    selected_cycle_summary = build_cycle_summary(selected_cycle_obj) if selected_cycle_obj else None

    # Global summaries
    grouped_global: dict[str, dict[str, object]] = {}
    # For global summary, we use current cycle activities (default behavior of list_atividade)
    # Actually list_atividade() filters by current cycle.
    # Let's replicate that logic using all_activities and open_cycle
    current_activities = []
    if open_cycle:
        c_start, c_end = cycle_windows[open_cycle["id"]]
        current_activities = _filter_cycle_records(
            all_activities, c_start, c_end,
            ("created_at", "updated_at", "completed_at")
        )

    for activity in current_activities:
        if activity.get("status") != "concluida":
            continue
        person_label = activity["_norm_executor"] or activity["_norm_owner"] or "Sem responsável"
        person_key = person_label.casefold()
        if person_key not in grouped_global:
            grouped_global[person_key] = {"owner": person_label, "count": 0}
        grouped_global[person_key]["count"] = int(grouped_global[person_key]["count"]) + 1

    completed_tasks_by_owner = [
        {"owner": item["owner"], "count": item["count"]}
        for item in sorted(grouped_global.values(), key=lambda item: (-int(item["count"]), str(item["owner"])))
    ]

    conn = get_conn()
    try:
        clients_count = run_query(conn, "SELECT COUNT(*) FROM clients").fetchone()[0]
        modules_count = run_query(conn, "SELECT COUNT(*) FROM modules").fetchone()[0]
    except Exception:
        clients_count = 0
        modules_count = 0
    conn.close()

    return {
        "homologacoes": len(all_homologations),
        "customizacoes": len(all_customizations),
        "atividades": len(all_activities),
        "releases": len(all_releases),
        "clientes": clients_count,
        "modulos": modules_count,
        "completed_tasks_total": sum(item["count"] for item in completed_tasks_by_owner),
        "completed_tasks_by_owner": completed_tasks_by_owner,
        "activity_by_owner": completed_tasks_by_owner,
        "current_cycle": current_cycle_summary,
        "previous_cycle": previous_cycle_summary,
        "selected_cycle": selected_cycle_summary,
    }


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
