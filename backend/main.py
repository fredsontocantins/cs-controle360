"""CS-Controle 360 - FastAPI Backend (API Only)."""

from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import ensure_tables, reset_application_data, seed_from_snapshot, seed_demo_data_if_needed, _seed_activity_catalogs
from .database import run_query
from .config import CORS_ORIGINS, RESET_SAMPLE_DATA_ON_STARTUP, assert_secure_secrets
from datetime import datetime
from .routers import auth, homologacao, customizacao, atividade, release, cliente, modulo, reports, pdf_intelligence, playbooks
from .services.auth import bootstrap_default_admin, get_current_user
from .models.atividade import list_atividade, normalize_person_name
from .models.customizacao import list_customizacao
from .models.homologacao import list_homologacao
from .models.release import list_release
from .models.report_cycle import get_cycle, get_cycle_window, list_cycles, parse_cycle_datetime, get_active_cycle_started_at
from .config import TABLE_CLIENTE, TABLE_MODULO


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
    # Use a unique key for the pre-calculated date based on the fields being checked
    cache_key = f"_dt_{hash(keys)}"

    for record in records:
        # Optimization: use pre-calculated _dt if available
        record_dt = record.get(cache_key)
        if record_dt is None:
            record_value = _record_datetime(record, keys)
            if not record_value:
                continue
            record_dt = parse_cycle_datetime(record_value)
            record[cache_key] = record_dt # Cache it for multiple cycles

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

    # ⚡ BOLT Optimization: Pre-fetch all data to eliminate N+1 queries
    # Fetching history=True to get all records for cycle filtering
    all_homologacoes = list_homologacao(include_history=True)
    all_customizacoes = list_customizacao(include_history=True)
    all_atividades = list_atividade(include_history=True)
    all_releases = list_release(include_history=True)

    # Optimization: Pre-calculate owner labels for activities
    for act in all_atividades:
        exec_name = normalize_person_name(act.get("executor"))
        owner_name = normalize_person_name(act.get("owner"))
        act["_owner_label"] = exec_name or owner_name or "Sem responsável"

    cycles = list_cycles("reports")
    for c in cycles:
        c["_dt"] = parse_cycle_datetime(c.get("created_at"))

    open_cycle = next((cycle for cycle in cycles if cycle.get("status") == "aberto"), None)
    closed_cycles = [cycle for cycle in cycles if cycle.get("status") == "prestado"]
    closed_cycles.sort(key=lambda item: item["_dt"], reverse=True)
    previous_cycle = closed_cycles[0] if closed_cycles else None

    # Cache for cycle windows to avoid redundant DB calls
    _window_cache = {}
    def get_window(cid: int):
        if cid not in _window_cache:
            _window_cache[cid] = get_cycle_window(cid)
        return _window_cache[cid]

    def build_cycle_summary(cycle: dict | None) -> dict[str, object] | None:
        if not cycle:
            return None

        start_dt, end_dt = get_window(cycle["id"])
        if start_dt <= datetime.min:
            return None

        homologacoes_count = len(_filter_cycle_records(
            all_homologacoes, start_dt, end_dt,
            ("check_date", "requested_production_date", "production_date", "created_at"),
        ))

        customizacoes_count = len(_filter_cycle_records(
            all_customizacoes, start_dt, end_dt,
            ("received_at", "created_at"),
        ))

        atividades_cycle = _filter_cycle_records(
            all_atividades, start_dt, end_dt,
            ("created_at", "updated_at", "completed_at"),
        )

        releases_count = len(_filter_cycle_records(
            all_releases, start_dt, end_dt,
            ("applies_on", "created_at"),
        ))

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
    selected_cycle_summary = build_cycle_summary(get_cycle(cycle_id)) if cycle_id else None

    # Global summary calculations
    # Wait, the original code used list_homologacao() which filters by current cycle if include_history=False
    # Let's preserve that behavior using the pre-fetched data

    current_cycle_start = parse_cycle_datetime(get_active_cycle_started_at("reports"))

    def is_current(record, keys):
        if current_cycle_start <= datetime.min:
            return False
        rdt = record.get("_dt")
        if rdt is None:
            val = _record_datetime(record, keys)
            if not val:
                return False
            rdt = parse_cycle_datetime(val)
            record["_dt"] = rdt
        return rdt >= current_cycle_start

    summary_homologacoes = len([h for h in all_homologacoes if is_current(h, ("check_date", "requested_production_date", "production_date", "created_at"))])
    summary_customizacoes = len([c for c in all_customizacoes if is_current(c, ("received_at", "created_at"))])
    summary_atividades = len([a for a in all_atividades if is_current(a, ("created_at", "updated_at", "completed_at"))])
    summary_releases = len([r for r in all_releases if is_current(r, ("applies_on", "created_at"))])

    # For "tasks_by_owner", the original code used all activities regardless of cycle
    grouped: dict[str, dict[str, object]] = {}
    for activity in all_atividades:
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
        clients_count = run_query(conn, f"SELECT COUNT(*) FROM {TABLE_CLIENTE}").fetchone()[0]
        modules_count = run_query(conn, f"SELECT COUNT(*) FROM {TABLE_MODULO}").fetchone()[0]
    except Exception:
        clients_count = 0
        modules_count = 0

    summary = {
        "homologacoes": summary_homologacoes,
        "customizacoes": summary_customizacoes,
        "atividades": summary_atividades,
        "releases": summary_releases,
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
