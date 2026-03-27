"""FastAPI application that exposes the CS control dashboard."""

from __future__ import annotations

import io
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import (
    Depends,
    FastAPI,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    status as fastapi_status,
    File,
    UploadFile,
)
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import pandas as pd
from fpdf import FPDF

from cs_control.loader import build_control_snapshot
from cs_web import db
from cs_web.schemas import (
    CustomizationCreate,
    CustomizationUpdate,
    HomologationCreate,
    HomologationUpdate,
    ReleaseCreate,
    ReleaseUpdate,
    ClientCreate,
    ClientUpdate,
    ModuleCreate,
    ModuleUpdate,
)

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "static" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.cache_size = 0

def _admin_token() -> str:
    return os.environ.get("CS_API_KEY", "cs-secret")


def _allow_unsecured_admin() -> bool:
    return os.environ.get("CS_ALLOW_UNSECURED_ADMIN", "1").lower() in ("1", "true", "yes")

STAGE_LABELS = {
    "em_elaboracao": "Em Elaboração",
    "em_aprovacao": "Em Aprovação",
    "aprovadas": "Aprovadas",
    "aprovadas_sc": "Propostas Aprovadas (SC)",
}

INITIAL_SNAPSHOT_FILE = BASE_DIR / "data" / "initial_snapshot.json"
EXPORT_FORMATS = ("xlsx", "pdf", "json")


def _require_admin_access(
    api_key_header: str | None = Header(None, alias="X-API-Key"),
    api_key_query: str | None = Query(None, alias="api_key"),
) -> None:
    if _allow_unsecured_admin():
        return
    key = api_key_header or api_key_query
    if key != _admin_token():
        raise HTTPException(
            status_code=fastapi_status.HTTP_403_FORBIDDEN, detail="Invalid API key"
        )


def _admin_interface_requires_token() -> bool:
    return os.environ.get("CS_ADMIN_AUTH_ENABLED", "0").lower() in ("1", "true", "yes")


def _guard_admin_action(api_key: str | None = None) -> None:
    if _admin_interface_requires_token():
        _require_admin_access(api_key_query=api_key)


def _build_stage_summary(customizations: list[dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    summary: Dict[str, Dict[str, Any]] = {}
    for entry in customizations:
        stage = entry.get("stage") or "unknown"
        totals = summary.setdefault(
            stage,
            {"label": STAGE_LABELS.get(stage, stage), "count": 0, "value": 0.0, "pf": 0.0},
        )
        totals["count"] += 1
        totals["value"] += float(entry.get("value") or 0)
        totals["pf"] += float(entry.get("pf") or 0)
    return summary


def _resolve_client_selection(client_select: str | None, client_manual: str | None) -> tuple[int | None, str | None]:
    client_id: int | None = None
    if client_select:
        try:
            client_id = int(client_select)
        except ValueError:
            client_id = None
    label = (client_manual or "").strip() or None
    if client_id and not label:
        client = db.get_client(client_id)
        label = client["name"] if client else None
    return client_id, label


def _resolve_module_selection(module_select: str | None, module_manual: str | None) -> tuple[str | None, int | None]:
    manual = (module_manual or "").strip()
    if manual:
        return manual, None
    if module_select:
        try:
            module_id = int(module_select)
        except ValueError:
            module_id = None
        else:
            module = db.get_module(module_id)
            if module:
                return module.get("name"), module_id
    return None, None


def _module_label(entry: dict[str, Any]) -> str:
    label = (entry.get("module") or "").strip()
    if label:
        return label
    module_id = entry.get("module_id")
    if module_id:
        module = db.get_module(module_id)
        if module:
            return module.get("name") or "Sem módulo"
    return "Sem módulo"


def _build_module_summary(
    homologations: list[dict[str, Any]],
    customizations: list[dict[str, Any]],
    releases: list[dict[str, Any]],
) -> List[dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    catalog = [module.get("name") for module in db.list_modules() if module.get("name")]
    for name in catalog:
        summary.setdefault(name, {"label": name, "homologations": 0, "customizations": 0, "releases": 0})

    def increment(label: str, kind: str) -> None:
        node = summary.setdefault(label, {"label": label, "homologations": 0, "customizations": 0, "releases": 0})
        node[kind] += 1

    for entry in homologations:
        label = _module_label(entry)
        increment(label, "homologations")
    for entry in customizations:
        label = _module_label(entry)
        increment(label, "customizations")
    for entry in releases:
        label = entry.get("module") or _module_label(entry)
        increment(label, "releases")

    result = sorted(summary.values(), key=lambda item: (-(item["homologations"] + item["customizations"] + item["releases"]), item["label"]))
    for record in result:
        record["total"] = record["homologations"] + record["customizations"] + record["releases"]
    return result


def _save_pdf(upload: UploadFile | None) -> str | None:
    if not upload or not upload.filename:
        return None
    target = UPLOADS_DIR / f"{uuid4().hex}{Path(upload.filename).suffix or '.pdf'}"
    with target.open("wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)
    return str(Path("uploads") / target.name)


def _client_label(entry: dict[str, Any], client_lookup: dict[int, dict[str, Any]]) -> str:
    client_id = entry.get("client_id") or None
    if client_id:
        client = client_lookup.get(client_id)
        if client:
            return client.get("name") or "Sem cliente"
    return entry.get("client") or "Sem cliente"


def _build_client_summary(
    clients: list[dict[str, Any]],
    homologations: list[dict[str, Any]],
    customizations: list[dict[str, Any]],
    releases: list[dict[str, Any]],
) -> List[dict[str, Any]]:
    lookup = {client["id"]: client for client in clients}
    summary: dict[str, dict[str, Any]] = {}
    for client in clients:
        summary.setdefault(
            client["name"],
            {"name": client["name"], "homologations": 0, "customizations": 0, "releases": 0},
        )

    def increment(key: str, kind: str) -> None:
        node = summary.setdefault(key, {"name": key, "homologations": 0, "customizations": 0, "releases": 0})
        node[kind] += 1

    for record in homologations:
        label = _client_label(record, lookup)
        increment(label, "homologations")
    for record in customizations:
        label = _client_label(record, lookup)
        increment(label, "customizations")
    for record in releases:
        label = _client_label(record, lookup)
        increment(label, "releases")

    return sorted(summary.values(), key=lambda item: (item["name"] or "").lower())


def _module_catalog() -> list[dict[str, Any]]:
    modules = db.list_modules()
    if modules:
        return modules
    return [{"name": "Catálogo"}]


def _load_initial_snapshot() -> dict[str, Any] | None:
    if not INITIAL_SNAPSHOT_FILE.exists():
        return None
    try:
        with INITIAL_SNAPSHOT_FILE.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def _build_export_payload() -> dict[str, list[dict[str, Any]]]:
    return {
        "homologation": db.list_homologation(),
        "customizations": db.list_customizations(),
        "releases": db.list_releases(),
        "clients": db.list_clients(),
        "modules": db.list_modules(),
    }


def _render_export_pdf(payload: dict[str, list[dict[str, Any]]]) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "CS Controle — Relatório consolidado", ln=1)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(
        0,
        6,
        f"Gerado em {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
        ln=1,
    )
    pdf.ln(4)

    def _write_section(title: str, entries: list[dict[str, Any]], line_formatter) -> None:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 6, f"{title} ({len(entries)})", ln=1)
        pdf.set_font("Helvetica", "", 10)
        if not entries:
            pdf.cell(0, 6, "• Nenhum registro encontrado.", ln=1)
            return
        for entry in entries[:5]:
            pdf.multi_cell(0, 6, f"• {line_formatter(entry)}")
        pdf.ln(2)

    _write_section(
        "Homologações",
        payload["homologation"],
        lambda entry: (
            f"{entry.get('module') or 'Sem módulo'} / "
            f"{entry.get('client') or 'Sem cliente'} | "
            f"{entry.get('status') or 'sem status'} | "
            f"Solicitado {entry.get('requested_production_date') or '—'} | "
            f"Produção {entry.get('production_date') or '—'}"
        ),
    )
    _write_section(
        "Customizações",
        payload["customizations"],
        lambda entry: (
            f"{entry.get('proposal') or 'Sem proposta'} / "
            f"{entry.get('client') or 'Sem cliente'} | "
            f"{entry.get('stage') or 'sem etapa'} | "
            f"Valor {('R$ %.2f' % entry.get('value')) if entry.get('value') else 'N/A'}"
        ),
    )
    _write_section(
        "Releases",
        payload["releases"],
        lambda entry: (
            f"{entry.get('release_name') or 'Sem nome'} / "
            f"{entry.get('module') or 'sem módulo'} | "
            f"Aplica em {entry.get('applies_on') or '—'} | "
            f"Cliente {entry.get('client') or '—'}"
        ),
    )
    return pdf.output(dest="S").encode("latin-1")


def _meta_snapshot() -> Dict[str, Any]:
    return {
        "built_at": datetime.utcnow().isoformat() + "Z",
        "source": "Banco SQLite interno",
    }


def _parse_optional_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


app = FastAPI(
    title="CS Controle",
    description="Dashboard e APIs para monitorar homologação, versões e customizações.",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.on_event("startup")
async def startup_event() -> None:
    db.ensure_tables()
    if not db.list_homologation():
        snapshot = _load_initial_snapshot()
        if not snapshot:
            hom_file = Path("Controle de Homologação.xlsx")
            custom_file = Path("modelo Customização.xlsx")
            if hom_file.exists() and custom_file.exists():
                snapshot = build_control_snapshot(hom_file, custom_file)
        if snapshot:
            db.seed_from_snapshot(snapshot)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    homologations = db.list_homologation()
    customizations = db.list_customizations()
    releases = db.list_releases()
    clients = db.list_clients()
    module_catalog = _module_catalog()
    client_summary = _build_client_summary(clients, homologations, customizations, releases)
    module_summary = _build_module_summary(homologations, customizations, releases)
    module_chart = [
        {"label": entry["label"], "value": entry["total"]}
        for entry in module_summary
    ]
    client_chart = [
        {
            "label": entry["name"],
            "value": entry["homologations"] + entry["customizations"] + entry["releases"],
        }
        for entry in client_summary
    ]
    context = {
        "request": request,
        "homologations": homologations,
        "customizations": customizations,
        "releases": releases,
        "clients": clients,
        "module_catalog": module_catalog,
        "client_summary": client_summary,
        "module_summary": module_summary,
        "module_chart": json.dumps(module_chart, ensure_ascii=False),
        "client_chart": json.dumps(client_chart, ensure_ascii=False),
        "stage_summary": _build_stage_summary(customizations),
        "refresh_url": request.url.path + "?refresh=true",
        "admin_token": _admin_token(),
    }
    context["snapshot"] = _meta_snapshot()
    template = templates.env.get_template("dashboard.html")
    return HTMLResponse(template.render(**context))


@app.get("/api/snapshot")
async def get_snapshot() -> JSONResponse:
    return JSONResponse(
        {
            "built_at": datetime.utcnow().isoformat() + "Z",
            "source": "Banco SQLite interno",
            "homologation": db.list_homologation(),
            "customizations": db.list_customizations(),
            "releases": db.list_releases(),
            "clients": db.list_clients(),
        }
    )


@app.get("/api/homologation")
async def list_homologation(stage: str | None = Query(None)) -> JSONResponse:
    items = db.list_homologation()
    return JSONResponse(items)


@app.post("/api/homologation", response_model=dict)
async def create_homologation(
    payload: HomologationCreate,
    _secret: None = Depends(_require_admin_access),
) -> JSONResponse:
    entity_id = db.insert_homologation(payload.dict())
    created = db.get_homologation(entity_id)
    return JSONResponse(created)


@app.put("/api/homologation/{entity_id}", response_model=dict)
async def update_homologation(
    entity_id: int,
    payload: HomologationUpdate,
    _secret: None = Depends(_require_admin_access),
) -> JSONResponse:
    updated = db.update_homologation(entity_id, payload.dict(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found or nada to update")
    return JSONResponse(db.get_homologation(entity_id))


@app.delete("/api/homologation/{entity_id}")
async def delete_homologation(
    entity_id: int, _secret: None = Depends(_require_admin_access)
) -> JSONResponse:
    success = db.delete_homologation(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    return JSONResponse({"deleted": entity_id})


@app.get("/api/customizations")
async def list_customizations(stage: str | None = Query(None)) -> JSONResponse:
    items = db.list_customizations()
    if stage:
        items = [item for item in items if item.get("stage") == stage]
    return JSONResponse(items)


@app.post("/api/customizations", response_model=dict)
async def create_customization(
    payload: CustomizationCreate, _secret: None = Depends(_require_admin_access)
) -> JSONResponse:
    entity_id = db.insert_customization(payload.dict())
    return JSONResponse(db.get_customization(entity_id))


@app.put("/api/customizations/{entity_id}", response_model=dict)
async def update_customization(
    entity_id: int,
    payload: CustomizationUpdate,
    _secret: None = Depends(_require_admin_access),
) -> JSONResponse:
    updated = db.update_customization(entity_id, payload.dict(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found or nada to update")
    return JSONResponse(db.get_customization(entity_id))


@app.delete("/api/customizations/{entity_id}")
async def delete_customization(
    entity_id: int, _secret: None = Depends(_require_admin_access)
) -> JSONResponse:
    success = db.delete_customization(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    return JSONResponse({"deleted": entity_id})


@app.get("/api/releases")
async def list_releases() -> JSONResponse:
    releases = db.list_releases()
    clients = {client["id"]: client for client in db.list_clients()}
    for release in releases:
        client = clients.get(release.get("client_id"))
        release["client_name"] = client["name"] if client else None
    return JSONResponse(releases)


@app.post("/api/releases", response_model=dict)
async def create_release(
    payload: ReleaseCreate, _secret: None = Depends(_require_admin_access)
) -> JSONResponse:
    release_id = db.insert_release(payload.dict())
    release = db.get_release(release_id)
    return JSONResponse(release or {})


@app.put("/api/releases/{entity_id}", response_model=dict)
async def update_release(
    entity_id: int,
    payload: ReleaseUpdate,
    _secret: None = Depends(_require_admin_access),
) -> JSONResponse:
    updated = db.update_release(entity_id, payload.dict(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found or nada to update")
    release = db.get_release(entity_id)
    return JSONResponse(release or {})


@app.delete("/api/releases/{entity_id}")
async def delete_release(
    entity_id: int, _secret: None = Depends(_require_admin_access)
) -> JSONResponse:
    success = db.delete_release(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    return JSONResponse({"deleted": entity_id})


@app.get("/api/modules")
async def list_modules_api() -> JSONResponse:
    return JSONResponse(db.list_modules())


@app.post("/api/modules", response_model=dict)
async def create_module(
    payload: ModuleCreate, _secret: None = Depends(_require_admin_access)
) -> JSONResponse:
    module_id = db.insert_module(payload.dict())
    return JSONResponse(db.get_module(module_id))


@app.put("/api/modules/{entity_id}", response_model=dict)
async def update_module(
    entity_id: int,
    payload: ModuleUpdate,
    _secret: None = Depends(_require_admin_access),
) -> JSONResponse:
    updated = db.update_module(entity_id, payload.dict(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found or nada to update")
    return JSONResponse(db.get_module(entity_id))


@app.delete("/api/modules/{entity_id}")
async def delete_module(
    entity_id: int, _secret: None = Depends(_require_admin_access)
) -> JSONResponse:
    success = db.delete_module(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    return JSONResponse({"deleted": entity_id})


@app.get("/api/clients")
async def list_clients_api() -> JSONResponse:
    return JSONResponse(db.list_clients())


@app.post("/api/clients", response_model=dict)
async def create_client(
    payload: ClientCreate, _secret: None = Depends(_require_admin_access)
) -> JSONResponse:
    client_id = db.insert_client(payload.dict())
    return JSONResponse(db.get_client(client_id))


@app.put("/api/clients/{entity_id}", response_model=dict)
async def update_client(
    entity_id: int,
    payload: ClientUpdate,
    _secret: None = Depends(_require_admin_access),
) -> JSONResponse:
    updated = db.update_client(entity_id, payload.dict(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found or nada to update")
    return JSONResponse(db.get_client(entity_id))


@app.delete("/api/clients/{entity_id}")
async def delete_client(
    entity_id: int, _secret: None = Depends(_require_admin_access)
) -> JSONResponse:
    success = db.delete_client(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    return JSONResponse({"deleted": entity_id})


@app.get("/admin", response_class=HTMLResponse)
async def admin_console(request: Request) -> HTMLResponse:
    homologations = db.list_homologation()
    customizations = db.list_customizations()
    releases = db.list_releases()
    clients = db.list_clients()
    client_map = {client["id"]: client for client in clients}
    for release in releases:
        release["client_name"] = client_map.get(release.get("client_id"), {}).get("name")
    module_catalog = _module_catalog()
    context = {
        "request": request,
        "homologations": homologations,
        "customizations": customizations,
        "stage_summary": _build_stage_summary(customizations),
        "admin_token": _admin_token(),
        "snapshot": _meta_snapshot(),
        "refresh_url": request.url.path + "?refresh=true",
        "module_catalog": module_catalog,
        "clients": clients,
        "releases": releases,
        "stage_labels": STAGE_LABELS,
    }
    template = templates.env.get_template("admin.html")
    return HTMLResponse(template.render(**context))


@app.get("/admin/export", response_model=None)
async def admin_export(
    format: str = Query(
        "xlsx",
        description="Formato de exportação",
        pattern="^(xlsx|pdf|json)$",
    ),
    api_key: str | None = Query(
        None, alias="api_key", title="Token administrativo opcional"
    ),
) -> StreamingResponse | JSONResponse:
    _guard_admin_action(api_key)
    payload = _build_export_payload()
    fmt = format.lower()
    if fmt == "json":
        return JSONResponse(payload)
    if fmt == "xlsx":
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            pd.DataFrame(payload["homologation"]).to_excel(
                writer, sheet_name="Homologacoes", index=False
            )
            pd.DataFrame(payload["customizations"]).to_excel(
                writer, sheet_name="Customizacoes", index=False
            )
            pd.DataFrame(payload["releases"]).to_excel(
                writer, sheet_name="Releases", index=False
            )
            pd.DataFrame(payload["clients"]).to_excel(
                writer, sheet_name="Clientes", index=False
            )
            pd.DataFrame(payload["modules"]).to_excel(
                writer, sheet_name="Modulos", index=False
            )
        buffer.seek(0)
        headers = {
            "Content-Disposition": 'attachment; filename="cs-controle.xlsx"'
        }
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers,
        )
    if fmt == "pdf":
        pdf_bytes = _render_export_pdf(payload)
        buffer = io.BytesIO(pdf_bytes)
        headers = {"Content-Disposition": 'attachment; filename="cs-controle.pdf"'}
        return StreamingResponse(buffer, media_type="application/pdf", headers=headers)
    raise HTTPException(status_code=400, detail="Formato inválido")


@app.post("/admin/homologation/create")
async def admin_create_homologation(
    module_select: str | None = Form(None),
    module_manual: str | None = Form(None),
    status: str | None = Form(None),
    check_date: str | None = Form(None),
    requested_production_date: str | None = Form(None),
    production_date: str | None = Form(None),
    observation: str | None = Form(None),
    latest_version: str | None = Form(None),
    homologation_version: str | None = Form(None),
    production_version: str | None = Form(None),
    homologated: str | None = Form(None),
    client_presentation: str | None = Form(None),
    applied: str | None = Form(None),
    client_select: str | None = Form(None),
    client_manual: str | None = Form(None),
    api_key: str | None = Query(None, alias="api_key"),
) -> RedirectResponse:
    _guard_admin_action(api_key)
    module_value, module_id = _resolve_module_selection(module_select, module_manual)
    client_id, client_label = _resolve_client_selection(client_select, client_manual)
    db.insert_homologation(
        {
            "module": module_value,
            "module_id": module_id,
            "status": status,
            "check_date": check_date,
            "requested_production_date": requested_production_date,
            "production_date": production_date,
            "observation": observation,
            "latest_version": latest_version,
            "homologation_version": homologation_version,
            "production_version": production_version,
            "homologated": homologated,
            "client_presentation": client_presentation,
            "applied": applied,
            "client": client_label,
            "client_id": client_id,
            "monthly_versions": {},
        }
    )
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.get("/admin/homologation/{entity_id}/edit", response_class=HTMLResponse)
async def admin_edit_homologation(request: Request, entity_id: int) -> HTMLResponse:
    record = db.get_homologation(entity_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    context = {
        "request": request,
        "record": record,
        "admin_token": _admin_token(),
        "snapshot": _meta_snapshot(),
        "module_catalog": _module_catalog(),
        "clients": db.list_clients(),
        "refresh_url": request.url.path + "?refresh=true",
    }
    template = templates.env.get_template("edit_homologation.html")
    return HTMLResponse(template.render(**context))


@app.post("/admin/homologation/{entity_id}/update")
async def admin_update_homologation(
    entity_id: int,
    module_select: str | None = Form(None),
    module_manual: str | None = Form(None),
    status: str | None = Form(None),
    check_date: str | None = Form(None),
    requested_production_date: str | None = Form(None),
    production_date: str | None = Form(None),
    observation: str | None = Form(None),
    latest_version: str | None = Form(None),
    homologation_version: str | None = Form(None),
    production_version: str | None = Form(None),
    homologated: str | None = Form(None),
    client_presentation: str | None = Form(None),
    applied: str | None = Form(None),
    client_select: str | None = Form(None),
    client_manual: str | None = Form(None),
    api_key: str | None = Query(None, alias="api_key"),
) -> RedirectResponse:
    _guard_admin_action(api_key)
    payload: dict[str, Any] = {}
    module_value, module_id = _resolve_module_selection(module_select, module_manual)
    if module_value is not None:
        payload["module"] = module_value
    if module_id is not None:
        payload["module_id"] = module_id
    if module_value is not None:
        payload["module"] = module_value
    if status is not None:
        payload["status"] = status
    if check_date is not None:
        payload["check_date"] = check_date
    if requested_production_date is not None:
        payload["requested_production_date"] = requested_production_date
    if production_date is not None:
        payload["production_date"] = production_date
    if observation is not None:
        payload["observation"] = observation
    if latest_version is not None:
        payload["latest_version"] = latest_version
    if homologation_version is not None:
        payload["homologation_version"] = homologation_version
    if production_version is not None:
        payload["production_version"] = production_version
    if homologated is not None:
        payload["homologated"] = homologated
    if client_presentation is not None:
        payload["client_presentation"] = client_presentation
    if applied is not None:
        payload["applied"] = applied
    client_id, client_label = _resolve_client_selection(client_select, client_manual)
    if client_label is not None:
        payload["client"] = client_label
    if client_id is not None:
        payload["client_id"] = client_id
    if payload:
        db.update_homologation(entity_id, payload)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/homologation/{entity_id}/delete")
async def admin_delete_homologation(
    entity_id: int, api_key: str | None = Query(None, alias="api_key")
) -> RedirectResponse:
    _guard_admin_action(api_key)
    db.delete_homologation(entity_id)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/customizations/create")
async def admin_create_customization(
    stage: str = Form(...),
    proposal: str = Form(...),
    subject: str | None = Form(None),
    client_select: str | None = Form(None),
    client_manual: str | None = Form(None),
    module_select: str | None = Form(None),
    module_manual: str | None = Form(None),
    owner: str | None = Form(None),
    received_at: str | None = Form(None),
    status: str | None = Form(None),
    pf: str | None = Form(None),
    value: str | None = Form(None),
    observations: str | None = Form(None),
    pdf: UploadFile | None = File(None),
    api_key: str | None = Query(None, alias="api_key"),
) -> RedirectResponse:
    _guard_admin_action(api_key)
    module_value, module_id = _resolve_module_selection(module_select, module_manual)
    client_id, client_label = _resolve_client_selection(client_select, client_manual)
    pdf_path = _save_pdf(pdf)
    db.insert_customization(
        {
            "stage": stage,
            "proposal": proposal,
            "subject": subject,
            "client": client_label,
            "client_id": client_id,
            "module": module_value,
            "module_id": module_id,
            "owner": owner,
            "received_at": received_at,
            "status": status,
            "pf": _parse_optional_float(pf),
            "value": _parse_optional_float(value),
            "observations": observations,
            "pdf_path": pdf_path,
        }
    )
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.get("/admin/customizations/{entity_id}/edit", response_class=HTMLResponse)
async def admin_edit_customization(request: Request, entity_id: int) -> HTMLResponse:
    record = db.get_customization(entity_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    context = {
        "request": request,
        "record": record,
        "admin_token": _admin_token(),
        "snapshot": _meta_snapshot(),
        "module_catalog": _module_catalog(),
        "clients": db.list_clients(),
        "stage_labels": STAGE_LABELS,
        "refresh_url": request.url.path + "?refresh=true",
    }
    template = templates.env.get_template("edit_customization.html")
    return HTMLResponse(template.render(**context))


@app.post("/admin/customizations/{entity_id}/update")
async def admin_update_customization(
    entity_id: int,
    stage: str | None = Form(None),
    proposal: str | None = Form(None),
    subject: str | None = Form(None),
    client_select: str | None = Form(None),
    client_manual: str | None = Form(None),
    module_select: str | None = Form(None),
    module_manual: str | None = Form(None),
    owner: str | None = Form(None),
    received_at: str | None = Form(None),
    status: str | None = Form(None),
    pf: str | None = Form(None),
    value: str | None = Form(None),
    observations: str | None = Form(None),
    pdf: UploadFile | None = File(None),
    api_key: str | None = Query(None, alias="api_key"),
) -> RedirectResponse:
    _guard_admin_action(api_key)
    payload: dict[str, Any] = {}
    module_value, module_id = _resolve_module_selection(module_select, module_manual)
    if stage is not None:
        payload["stage"] = stage
    if proposal is not None:
        payload["proposal"] = proposal
    if subject is not None:
        payload["subject"] = subject
    if module_value is not None:
        payload["module"] = module_value
    if module_id is not None:
        payload["module_id"] = module_id
    if owner is not None:
        payload["owner"] = owner
    if received_at is not None:
        payload["received_at"] = received_at
    if status is not None:
        payload["status"] = status
    if pf is not None:
        payload["pf"] = _parse_optional_float(pf)
    if value is not None:
        payload["value"] = _parse_optional_float(value)
    if observations is not None:
        payload["observations"] = observations
    pdf_path = _save_pdf(pdf)
    if pdf_path:
        payload["pdf_path"] = pdf_path
    client_id, client_label = _resolve_client_selection(client_select, client_manual)
    if client_label is not None:
        payload["client"] = client_label
    if client_id is not None:
        payload["client_id"] = client_id
    if payload:
        db.update_customization(entity_id, payload)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/customizations/{entity_id}/delete")
async def admin_delete_customization(
    entity_id: int, api_key: str | None = Query(None, alias="api_key")
) -> RedirectResponse:
    _guard_admin_action(api_key)
    db.delete_customization(entity_id)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/releases/create")
async def admin_create_release(
    module_select: str | None = Form(None),
    module_manual: str | None = Form(None),
    release_name: str = Form(...),
    version: str | None = Form(None),
    applies_on: str | None = Form(None),
    notes: str | None = Form(None),
    client_select: str | None = Form(None),
    client_manual: str | None = Form(None),
    pdf: UploadFile | None = File(None),
    api_key: str | None = Query(None, alias="api_key"),
) -> RedirectResponse:
    _guard_admin_action(api_key)
    module_value, module_id = _resolve_module_selection(module_select, module_manual)
    client_id, client_label = _resolve_client_selection(client_select, client_manual)
    pdf_path = _save_pdf(pdf)
    db.insert_release(
        {
            "module": module_value,
            "module_id": module_id,
            "release_name": release_name,
            "version": version,
            "applies_on": applies_on,
            "notes": notes,
            "client": client_label,
            "client_id": client_id,
            "pdf_path": pdf_path,
        }
    )
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.get("/admin/releases/{entity_id}/edit", response_class=HTMLResponse)
async def admin_edit_release(request: Request, entity_id: int) -> HTMLResponse:
    record = db.get_release(entity_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    context = {
        "request": request,
        "record": record,
        "module_catalog": _module_catalog(),
        "clients": db.list_clients(),
        "admin_token": _admin_token(),
        "snapshot": _meta_snapshot(),
        "refresh_url": request.url.path + "?refresh=true",
    }
    template = templates.env.get_template("edit_release.html")
    return HTMLResponse(template.render(**context))


@app.post("/admin/releases/{entity_id}/update")
async def admin_update_release(
    entity_id: int,
    module_select: str | None = Form(None),
    module_manual: str | None = Form(None),
    release_name: str | None = Form(None),
    version: str | None = Form(None),
    applies_on: str | None = Form(None),
    notes: str | None = Form(None),
    client_select: str | None = Form(None),
    client_manual: str | None = Form(None),
    pdf: UploadFile | None = File(None),
    api_key: str | None = Query(None, alias="api_key"),
) -> RedirectResponse:
    _guard_admin_action(api_key)
    payload: dict[str, Any] = {}
    module_value, module_id = _resolve_module_selection(module_select, module_manual)
    if module_value is not None:
        payload["module"] = module_value
    if module_id is not None:
        payload["module_id"] = module_id
    if release_name is not None:
        payload["release_name"] = release_name
    if version is not None:
        payload["version"] = version
    if applies_on is not None:
        payload["applies_on"] = applies_on
    if notes is not None:
        payload["notes"] = notes
    client_id, client_label = _resolve_client_selection(client_select, client_manual)
    if client_label is not None:
        payload["client"] = client_label
    if client_id is not None:
        payload["client_id"] = client_id
    pdf_path = _save_pdf(pdf)
    if pdf_path:
        payload["pdf_path"] = pdf_path
    if payload:
        db.update_release(entity_id, payload)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/releases/{entity_id}/delete")
async def admin_delete_release(
    entity_id: int, api_key: str | None = Query(None, alias="api_key")
) -> RedirectResponse:
    _guard_admin_action(api_key)
    db.delete_release(entity_id)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/modules/create")
async def admin_create_module(
    name: str = Form(...),
    description: str | None = Form(None),
    owner: str | None = Form(None),
    api_key: str | None = Query(None, alias="api_key"),
) -> RedirectResponse:
    _guard_admin_action(api_key)
    db.insert_module(
        {
            "name": name,
            "description": description,
            "owner": owner,
        }
    )
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.get("/admin/modules/{entity_id}/edit", response_class=HTMLResponse)
async def admin_edit_module(request: Request, entity_id: int) -> HTMLResponse:
    record = db.get_module(entity_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    context = {
        "request": request,
        "record": record,
        "admin_token": _admin_token(),
        "snapshot": _meta_snapshot(),
        "refresh_url": request.url.path + "?refresh=true",
    }
    template = templates.env.get_template("edit_module.html")
    return HTMLResponse(template.render(**context))


@app.post("/admin/modules/{entity_id}/update")
async def admin_update_module(
    entity_id: int,
    name: str | None = Form(None),
    description: str | None = Form(None),
    owner: str | None = Form(None),
    api_key: str | None = Query(None, alias="api_key"),
) -> RedirectResponse:
    _guard_admin_action(api_key)
    payload: dict[str, Any] = {}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if owner is not None:
        payload["owner"] = owner
    if payload:
        db.update_module(entity_id, payload)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/modules/{entity_id}/delete")
async def admin_delete_module(
    entity_id: int, api_key: str | None = Query(None, alias="api_key")
) -> RedirectResponse:
    _guard_admin_action(api_key)
    db.delete_module(entity_id)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/clients/create")
async def admin_create_client(
    name: str = Form(...),
    segment: str | None = Form(None),
    owner: str | None = Form(None),
    notes: str | None = Form(None),
    api_key: str | None = Query(None, alias="api_key"),
) -> RedirectResponse:
    _guard_admin_action(api_key)
    db.insert_client(
        {
            "name": name,
            "segment": segment,
            "owner": owner,
            "notes": notes,
        }
    )
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.get("/admin/clients/{entity_id}/edit", response_class=HTMLResponse)
async def admin_edit_client(request: Request, entity_id: int) -> HTMLResponse:
    record = db.get_client(entity_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    context = {
        "request": request,
        "record": record,
        "admin_token": _admin_token(),
        "snapshot": _meta_snapshot(),
        "refresh_url": request.url.path + "?refresh=true",
    }
    template = templates.env.get_template("edit_client.html")
    return HTMLResponse(template.render(**context))


@app.post("/admin/clients/{entity_id}/update")
async def admin_update_client(
    entity_id: int,
    name: str | None = Form(None),
    segment: str | None = Form(None),
    owner: str | None = Form(None),
    notes: str | None = Form(None),
    api_key: str | None = Query(None, alias="api_key"),
) -> RedirectResponse:
    _guard_admin_action(api_key)
    payload: dict[str, Any] = {}
    if name is not None:
        payload["name"] = name
    if segment is not None:
        payload["segment"] = segment
    if owner is not None:
        payload["owner"] = owner
    if notes is not None:
        payload["notes"] = notes
    if payload:
        db.update_client(entity_id, payload)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/clients/{entity_id}/delete")
async def admin_delete_client(
    entity_id: int, api_key: str | None = Query(None, alias="api_key")
) -> RedirectResponse:
    _guard_admin_action(api_key)
    db.delete_client(entity_id)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)
