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




@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}


@app.get("/api/summary")
async def get_summary(cycle_id: int | None = None):
    """Get summary of all entities for dashboard."""
    from .models.atividade import AtividadeRepository, normalize_person_name, list_atividade
    from .models.customizacao import CustomizacaoRepository
    from .models.homologacao import HomologacaoRepository
    from .models.release import ReleaseRepository
    from .models.report_cycle import get_cycle, get_cycle_window, list_cycles, parse_cycle_datetime
    from .models.cliente import ClienteRepository
    from .models.modulo import ModuloRepository

    cycles = list_cycles("reports")
    open_cycle = next((cycle for cycle in cycles if cycle.get("status") == "aberto"), None)
    closed_cycles = [cycle for cycle in cycles if cycle.get("status") == "prestado"]
    closed_cycles.sort(key=lambda item: parse_cycle_datetime(item.get("created_at")), reverse=True)
    previous_cycle = closed_cycles[0] if closed_cycles else None

    def build_cycle_summary(cycle: dict | None) -> dict[str, object] | None:
        if not cycle:
            return None
        start, end = get_cycle_window(cycle["id"])
        start_text = start.isoformat() if start else None
        end_text = end.isoformat() if end else None

        if not start_text:
            return None

        # Build SQL where clause for cycle time window
        def cycle_where(fields: tuple[str, ...]) -> tuple[str, tuple]:
            conditions = []
            for field in fields:
                conditions.append(f"({field} >= ? AND (? IS NULL OR {field} < ?))")
            where = " OR ".join(conditions)
            params = []
            for _ in fields:
                params.extend([start_text, end_text, end_text])
            return where, tuple(params)

        h_where, h_params = cycle_where(("check_date", "requested_production_date", "production_date", "created_at"))
        homologacoes_count = HomologacaoRepository.count(where=h_where, params=h_params)

        c_where, c_params = cycle_where(("received_at", "created_at"))
        customizacoes_count = CustomizacaoRepository.count(where=c_where, params=c_params)

        a_where, a_params = cycle_where(("created_at", "updated_at", "completed_at"))
        # We need the activities to group by owner
        atividades_cycle = AtividadeRepository.list(where=a_where, params=a_params)

        r_where, r_params = cycle_where(("applies_on", "created_at"))
        releases_count = ReleaseRepository.count(where=r_where, params=r_params)

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
    selected_cycle_summary = build_cycle_summary(get_cycle(cycle_id)) if cycle_id else None

    # Global summary (respecting current active cycle for activities if not history)
    activities = list_atividade(include_history=False)
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

    summary = {
        "homologacoes": HomologacaoRepository.count(),
        "customizacoes": CustomizacaoRepository.count(),
        "atividades": len(activities), # matches list_atividade(include_history=False)
        "releases": ReleaseRepository.count(),
        "clientes": ClienteRepository.count(),
        "modulos": ModuloRepository.count(),
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
