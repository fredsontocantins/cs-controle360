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
    """Filter records within a datetime window, using caching for parsed datetimes."""
    from .models.report_cycle import parse_cycle_datetime

    filtered: list[dict] = []
    # Use a unique key for caching based on the fields we are checking
    cache_key = f"_dt_{hash(keys)}"

    for record in records:
        record_dt = record.get(cache_key)
        if record_dt is None:
            record_value = _record_datetime(record, keys)
            if not record_value:
                # Cache as min to avoid re-checking empty values
                record[cache_key] = datetime.min
                continue
            record_dt = parse_cycle_datetime(record_value)
            record[cache_key] = record_dt

        if record_dt <= datetime.min:
            continue

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

    conn = get_conn()
    # Pre-fetch all needed record sets with history to avoid redundant database calls later.
    all_atividades = list_atividade(include_history=True)
    all_homologacoes = list_homologacao(include_history=True)
    all_customizacoes = list_customizacao(include_history=True)
    all_releases = list_release(include_history=True)

    cycles = list_cycles("reports")
    # Store cycles in a way that's easy to lookup by ID for selected_cycle
    cycles_map = {c["id"]: c for c in cycles}
    open_cycle = next((cycle for cycle in cycles if cycle.get("status") == "aberto"), None)
    closed_cycles = [cycle for cycle in cycles if cycle.get("status") == "prestado"]
    closed_cycles.sort(key=lambda item: parse_cycle_datetime(item.get("created_at")), reverse=True)
    previous_cycle = closed_cycles[0] if closed_cycles else None

    # Pre-calculate cycle windows for build_cycle_summary
    def get_window_from_list(target_cycle: dict | None) -> tuple[datetime | None, datetime | None]:
        if not target_cycle:
            return None, None
        start = parse_cycle_datetime(target_cycle.get("created_at"))
        if start <= datetime.min:
            return None, None

        # Find the earliest cycle that started after this one
        later_cycles = [
            parse_cycle_datetime(c.get("created_at"))
            for c in cycles
            if parse_cycle_datetime(c.get("created_at")) > start
        ]
        end = min(later_cycles) if later_cycles else None
        return start, end

    prev_start, prev_end = get_window_from_list(previous_cycle)
    curr_start, curr_end = get_window_from_list(open_cycle)

    # Filter for top-level counts based on current cycle (standard behavior of list_* calls)
    homologacoes = _filter_cycle_records(
        all_homologacoes, curr_start, None,
        ("check_date", "requested_production_date", "production_date", "created_at")
    ) if curr_start else []
    customizacoes = _filter_cycle_records(
        all_customizacoes, curr_start, None,
        ("received_at", "created_at")
    ) if curr_start else []
    atividades = _filter_cycle_records(
        all_atividades, curr_start, None,
        ("created_at", "updated_at", "completed_at")
    ) if curr_start else []
    releases = _filter_cycle_records(
        all_releases, curr_start, None,
        ("applies_on", "created_at")
    ) if curr_start else []

    selected_cycle = cycles_map.get(cycle_id) if cycle_id else None
    sel_start, sel_end = get_window_from_list(selected_cycle)

    def build_cycle_summary(
        cycle: dict | None,
        start_dt: datetime | None,
        end_dt: datetime | None,
        homologacoes_history: list[dict],
        customizacoes_history: list[dict],
        atividades_history: list[dict],
        releases_history: list[dict]
    ) -> dict[str, object] | None:
        if not cycle or not start_dt:
            return None

        homologacoes = len(_filter_cycle_records(
            homologacoes_history,
            start_dt,
            end_dt,
            ("check_date", "requested_production_date", "production_date", "created_at"),
        ))
        customizacoes = len(_filter_cycle_records(
            customizacoes_history,
            start_dt,
            end_dt,
            ("received_at", "created_at"),
        ))
        atividades_cycle = _filter_cycle_records(
            atividades_history,
            start_dt,
            end_dt,
            ("created_at", "updated_at", "completed_at"),
        )
        releases = len(_filter_cycle_records(
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
            "label": cycle.get("period_label") or f"Prestação {cycle.get('cycle_number') or cycle.get('id')}",
            "cycle_number": cycle.get("cycle_number"),
            "homologacoes": homologacoes,
            "customizacoes": customizacoes,
            "atividades": len(atividades_cycle),
            "releases": releases,
            "completed_tasks_total": sum(item["count"] for item in tasks_by_owner),
            "completed_tasks_by_owner": tasks_by_owner,
        }

    previous_cycle_summary = build_cycle_summary(
        previous_cycle, prev_start, prev_end,
        all_homologacoes, all_customizacoes, all_atividades, all_releases
    )
    current_cycle_summary = build_cycle_summary(
        open_cycle, curr_start, curr_end,
        all_homologacoes, all_customizacoes, all_atividades, all_releases
    )
    selected_cycle_summary = build_cycle_summary(
        selected_cycle, sel_start, sel_end,
        all_homologacoes, all_customizacoes, all_atividades, all_releases
    )

    if current_cycle_summary:
        completed_tasks_by_owner = current_cycle_summary["completed_tasks_by_owner"]
        completed_tasks_total = int(current_cycle_summary["completed_tasks_total"])
    else:
        completed_tasks_by_owner = []
        completed_tasks_total = 0

    try:
        clients_count = run_query(conn, "SELECT COUNT(*) FROM clients").fetchone()[0]
        modules_count = run_query(conn, "SELECT COUNT(*) FROM modules").fetchone()[0]
    except Exception:
        clients_count = 0
        modules_count = 0

    # The summary counts should reflect the same behavior as before the optimization.
    # The standard list_* calls (without include_history=True) filter by the current cycle.
    summary = {
        "homologacoes": len(homologacoes),
        "customizacoes": len(customizacoes),
        "atividades": len(atividades),
        "releases": len(releases),
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
