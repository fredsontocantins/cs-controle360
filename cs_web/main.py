"""FastAPI application that exposes the CS control dashboard."""

from __future__ import annotations

import io
import json
import os
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict

from fastapi import (
    Depends,
    FastAPI,
    Form,
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

from cs_control.loader import build_control_snapshot
from cs_web import db, utils
from cs_web.auth import (
    SESSION_COOKIE,
    SESSION_MAX_AGE,
    authenticate,
    ensure_default_admin,
    get_current_user,
    issue_session_token,
    require_role,
)
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
from cs_web.services import audit, export, stats

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.cache_size = 0


def _admin_token() -> str:
    return os.environ.get("CS_API_KEY", "cs-secret")


require_admin = Depends(require_role("admin"))
require_reader = Depends(require_role("admin", "viewer"))


def _module_catalog() -> list[dict[str, Any]]:
    modules = db.modules.list()
    if modules:
        return modules
    return [{"name": "Catálogo"}]


def _load_initial_snapshot() -> dict[str, Any] | None:
    initial_snapshot_file = BASE_DIR / "data" / "initial_snapshot.json"
    if not initial_snapshot_file.exists():
        return None
    try:
        with initial_snapshot_file.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
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
    ensure_default_admin()
    if not db.homologation.list():
        snapshot = _load_initial_snapshot()
        if not snapshot:
            hom_file = Path("Controle de Homologação.xlsx")
            custom_file = Path("modelo Customização.xlsx")
            if hom_file.exists() and custom_file.exists():
                snapshot = build_control_snapshot(hom_file, custom_file)
        if snapshot:
            db.seed_from_snapshot(snapshot)


def _redirect_to_login(request: Request) -> RedirectResponse:
    """Redirect an unauthenticated HTML request to /login with a return URL."""
    target = request.url.path
    if request.url.query:
        target += f"?{request.url.query}"
    return RedirectResponse(
        url=f"/login?next={target}", status_code=fastapi_status.HTTP_303_SEE_OTHER
    )


def _require_html_role(
    request: Request, *roles: str
) -> tuple[Dict[str, Any] | None, RedirectResponse | None]:
    """Resolve authentication for HTML routes."""
    user = get_current_user(request, None, None)
    if user is None:
        return None, _redirect_to_login(request)
    if roles and user.get("role") not in roles:
        return user, RedirectResponse(
            url="/", status_code=fastapi_status.HTTP_303_SEE_OTHER
        )
    return user, None


@app.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    next: str | None = Query(None, description="URL para redirecionar após o login"),
    error: str | None = Query(None),
) -> HTMLResponse:
    context = {"request": request, "next_url": next, "error": error}
    template = templates.env.get_template("login.html")
    return HTMLResponse(template.render(**context))


@app.post("/login", response_class=HTMLResponse, response_model=None)
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str | None = Form(None),
) -> HTMLResponse | RedirectResponse:
    user = authenticate(username, password)
    if not user:
        context = {
            "request": request,
            "next_url": next,
            "error": "Usuário ou senha inválidos",
        }
        template = templates.env.get_template("login.html")
        return HTMLResponse(
            template.render(**context),
            status_code=fastapi_status.HTTP_401_UNAUTHORIZED,
        )
    target = next if next and next.startswith("/") else "/"
    response = RedirectResponse(
        url=target, status_code=fastapi_status.HTTP_303_SEE_OTHER
    )
    response.set_cookie(
        key=SESSION_COOKIE,
        value=issue_session_token(int(user["id"])),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=os.environ.get("CS_SESSION_SECURE", "0").lower() in ("1", "true", "yes"),
    )
    return response


@app.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    response = RedirectResponse(
        url="/login", status_code=fastapi_status.HTTP_303_SEE_OTHER
    )
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.get("/logout")
async def logout_get(request: Request) -> RedirectResponse:
    return await logout(request)


@app.get("/", response_class=HTMLResponse, response_model=None)
async def dashboard(request: Request) -> HTMLResponse | RedirectResponse:
    current_user = get_current_user(request, None, None)
    if current_user is None:
        return _redirect_to_login(request)
    homologations = db.homologation.list()
    customizations = db.customizations.list()
    releases = db.releases.list()
    clients = db.clients.list()
    client_map = {client["id"]: client for client in clients}
    for release in releases:
        release["client_name"] = client_map.get(release.get("client_id"), {}).get("name")
    module_catalog = _module_catalog()
    client_summary = stats.build_client_summary(clients, homologations, customizations, releases)
    module_summary = stats.build_module_summary(homologations, customizations, releases)
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
    homologated_chart = stats.build_homologated_chart(homologations)
    stage_chart = stats.build_stage_chart(customizations)
    releases_chart = stats.build_releases_chart(releases)
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
        "homologated_chart": json.dumps(homologated_chart, ensure_ascii=False),
        "stage_chart": json.dumps(stage_chart, ensure_ascii=False),
        "releases_chart": json.dumps(releases_chart, ensure_ascii=False),
        "stage_summary": stats.build_stage_summary(customizations),
        "refresh_url": request.url.path + "?refresh=true",
        "admin_token": _admin_token(),
        "current_user": current_user,
    }
    context["snapshot"] = stats.get_meta_snapshot()
    context["active_nav"] = "dashboard"
    template = templates.env.get_template("dashboard.html")
    return HTMLResponse(template.render(**context))


def _render_list_page(
    request: Request,
    template_name: str,
    active_nav: str,
    extra: Dict[str, Any],
) -> HTMLResponse | RedirectResponse:
    user = get_current_user(request, None, None)
    if user is None:
        return _redirect_to_login(request)
    context: Dict[str, Any] = {
        "request": request,
        "current_user": user,
        "snapshot": stats.get_meta_snapshot(),
        "refresh_url": request.url.path + "?refresh=true",
        "active_nav": active_nav,
    }
    context.update(extra)
    template = templates.env.get_template(template_name)
    return HTMLResponse(template.render(**context))


@app.get("/homologations", response_class=HTMLResponse, response_model=None)
async def homologations_list(
    request: Request,
    q: str = Query("", description="Busca textual (módulo, cliente, status)"),
    homologated: str = Query("", description="Filtro: Sim, Não ou vazio"),
    page: int = Query(1, ge=1),
) -> HTMLResponse | RedirectResponse:
    items = db.homologation.list()
    if homologated:
        items = [i for i in items if (i.get("homologated") or "") == homologated]
    items = [
        i for i in items
        if utils.match_search(
            i, q, ("module", "client", "status", "observation", "homologation_version")
        )
    ]
    pagination = utils.paginate(items, page)
    return _render_list_page(
        request,
        "list_homologations.html",
        "homologations",
        {
            "homologations": pagination["items"],
            "pagination": pagination,
            "filters": {"q": q, "homologated": homologated},
        },
    )


@app.get("/customizations", response_class=HTMLResponse, response_model=None)
async def customizations_list(
    request: Request,
    q: str = Query(""),
    stage: str = Query(""),
    page: int = Query(1, ge=1),
) -> HTMLResponse | RedirectResponse:
    items = db.customizations.list()
    stage_summary = stats.build_stage_summary(items)
    if stage:
        items = [i for i in items if (i.get("stage") or "") == stage]
    items = [
        i for i in items
        if utils.match_search(
            i, q, ("proposal", "subject", "client", "module", "owner", "observations")
        )
    ]
    pagination = utils.paginate(items, page)
    return _render_list_page(
        request,
        "list_customizations.html",
        "customizations",
        {
            "customizations": pagination["items"],
            "pagination": pagination,
            "filters": {"q": q, "stage": stage},
            "stage_summary": stage_summary,
            "stage_labels": stats.STAGE_LABELS,
        },
    )


@app.get("/customizations/board", response_class=HTMLResponse, response_model=None)
async def customizations_board(
    request: Request,
    q: str = Query(""),
) -> HTMLResponse | RedirectResponse:
    items = db.customizations.list()
    if q:
        items = [
            i for i in items
            if utils.match_search(
                i, q, ("proposal", "subject", "client", "module", "owner", "observations")
            )
        ]
    columns = []
    for key, label in stats.STAGE_LABELS.items():
        column_items = [i for i in items if (i.get("stage") or "") == key]
        columns.append({"key": key, "label": label, "items": column_items})
    return _render_list_page(
        request,
        "board_customizations.html",
        "customizations",
        {
            "columns": columns,
            "filters": {"q": q},
            "stage_labels": stats.STAGE_LABELS,
        },
    )


@app.get("/releases", response_class=HTMLResponse, response_model=None)
async def releases_list(
    request: Request,
    q: str = Query(""),
    page: int = Query(1, ge=1),
) -> HTMLResponse | RedirectResponse:
    items = db.releases.list()
    clients = {client["id"]: client for client in db.clients.list()}
    for release in items:
        release["client_name"] = clients.get(release.get("client_id"), {}).get("name")
    items = [
        i for i in items
        if utils.match_search(
            i, q, ("release_name", "module", "client", "client_name", "version", "notes")
        )
    ]
    pagination = utils.paginate(items, page)
    return _render_list_page(
        request,
        "list_releases.html",
        "releases",
        {
            "releases": pagination["items"],
            "pagination": pagination,
            "filters": {"q": q},
        },
    )


@app.get("/releases/timeline", response_class=HTMLResponse, response_model=None)
async def releases_timeline(
    request: Request,
    q: str = Query(""),
) -> HTMLResponse | RedirectResponse:
    items = db.releases.list()
    clients = {client["id"]: client for client in db.clients.list()}
    for release in items:
        release["client_name"] = clients.get(release.get("client_id"), {}).get("name")
    if q:
        items = [
            i for i in items
            if utils.match_search(
                i, q, ("release_name", "module", "client", "client_name", "version", "notes")
            )
        ]

    def _sort_key(entry: Dict[str, Any]) -> str:
        for field in ("released_at", "applied_at", "created_at"):
            value = entry.get(field)
            if value:
                return str(value)
        return ""

    items.sort(key=_sort_key, reverse=True)
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for entry in items:
        raw = _sort_key(entry)
        bucket = raw[:7] if raw else "sem-data"
        groups.setdefault(bucket, []).append(entry)
    month_names = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                   "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    grouped = []
    for bucket, entries in groups.items():
        if bucket == "sem-data":
            label = "Sem data"
        else:
            try:
                year, month = bucket.split("-")
                label = f"{month_names[int(month) - 1]} / {year}"
            except (ValueError, IndexError):
                label = bucket
        grouped.append({"bucket": bucket, "label": label, "items": entries})

    return _render_list_page(
        request,
        "timeline_releases.html",
        "releases",
        {
            "groups": grouped,
            "total": len(items),
            "filters": {"q": q},
        },
    )


@app.get("/modules", response_class=HTMLResponse, response_model=None)
async def modules_list(
    request: Request,
    q: str = Query(""),
    page: int = Query(1, ge=1),
) -> HTMLResponse | RedirectResponse:
    items = db.modules.list()
    items = [i for i in items if utils.match_search(i, q, ("name", "owner", "description"))]
    pagination = utils.paginate(items, page)
    return _render_list_page(
        request,
        "list_modules.html",
        "modules",
        {
            "modules": pagination["items"],
            "pagination": pagination,
            "filters": {"q": q},
        },
    )


@app.get("/clients", response_class=HTMLResponse, response_model=None)
async def clients_list(
    request: Request,
    q: str = Query(""),
    page: int = Query(1, ge=1),
) -> HTMLResponse | RedirectResponse:
    items = db.clients.list()
    items = [
        i for i in items
        if utils.match_search(i, q, ("name", "segment", "owner", "notes"))
    ]
    pagination = utils.paginate(items, page)
    return _render_list_page(
        request,
        "list_clients.html",
        "clients",
        {
            "clients": pagination["items"],
            "pagination": pagination,
            "filters": {"q": q},
        },
    )


@app.get("/api/snapshot")
async def get_snapshot() -> JSONResponse:
    return JSONResponse(
        {
            "built_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "source": "Banco SQLite interno",
            "homologation": db.homologation.list(),
            "customizations": db.customizations.list(),
            "releases": db.releases.list(),
            "clients": db.clients.list(),
        }
    )


@app.get("/api/homologation")
async def list_homologation(stage: str | None = Query(None)) -> JSONResponse:
    items = db.homologation.list()
    return JSONResponse(items)


@app.post("/api/homologation", response_model=dict)
async def create_homologation(
    request: Request,
    payload: HomologationCreate,
    user: Dict[str, Any] = require_admin,
) -> JSONResponse:
    entity_id = audit.audit_insert(request, user, "homologation", db.homologation, payload.model_dump())
    created = db.homologation.get(entity_id)
    return JSONResponse(created)


@app.put("/api/homologation/{entity_id}", response_model=dict)
async def update_homologation(
    request: Request,
    entity_id: int,
    payload: HomologationUpdate,
    user: Dict[str, Any] = require_admin,
) -> JSONResponse:
    updated = audit.audit_update(
        request, user, "homologation", db.homologation, entity_id,
        payload.model_dump(exclude_none=True),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found or nada to update")
    return JSONResponse(db.homologation.get(entity_id))


@app.delete("/api/homologation/{entity_id}")
async def delete_homologation(
    request: Request, entity_id: int, user: Dict[str, Any] = require_admin
) -> JSONResponse:
    success = audit.audit_delete(request, user, "homologation", db.homologation, entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    return JSONResponse({"deleted": entity_id})


@app.get("/api/customizations")
async def list_customizations(stage: str | None = Query(None)) -> JSONResponse:
    items = db.customizations.list()
    if stage:
        items = [item for item in items if item.get("stage") == stage]
    return JSONResponse(items)


@app.post("/api/customizations", response_model=dict)
async def create_customization(
    request: Request,
    payload: CustomizationCreate,
    user: Dict[str, Any] = require_admin,
) -> JSONResponse:
    entity_id = audit.audit_insert(
        request, user, "customization", db.customizations, payload.model_dump()
    )
    return JSONResponse(db.customizations.get(entity_id))


@app.put("/api/customizations/{entity_id}", response_model=dict)
async def update_customization(
    request: Request,
    entity_id: int,
    payload: CustomizationUpdate,
    user: Dict[str, Any] = require_admin,
) -> JSONResponse:
    updated = audit.audit_update(
        request, user, "customization", db.customizations, entity_id,
        payload.model_dump(exclude_none=True),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found or nada to update")
    return JSONResponse(db.customizations.get(entity_id))


@app.delete("/api/customizations/{entity_id}")
async def delete_customization(
    request: Request, entity_id: int, user: Dict[str, Any] = require_admin
) -> JSONResponse:
    success = audit.audit_delete(request, user, "customization", db.customizations, entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    return JSONResponse({"deleted": entity_id})


@app.get("/api/releases")
async def list_releases() -> JSONResponse:
    releases = db.releases.list()
    clients = {client["id"]: client for client in db.clients.list()}
    for release in releases:
        client = clients.get(release.get("client_id"))
        release["client_name"] = client["name"] if client else None
    return JSONResponse(releases)


@app.post("/api/releases", response_model=dict)
async def create_release(
    request: Request,
    payload: ReleaseCreate,
    user: Dict[str, Any] = require_admin,
) -> JSONResponse:
    release_id = audit.audit_insert(request, user, "release", db.releases, payload.model_dump())
    release = db.releases.get(release_id)
    return JSONResponse(release or {})


@app.put("/api/releases/{entity_id}", response_model=dict)
async def update_release(
    request: Request,
    entity_id: int,
    payload: ReleaseUpdate,
    user: Dict[str, Any] = require_admin,
) -> JSONResponse:
    updated = audit.audit_update(
        request, user, "release", db.releases, entity_id,
        payload.model_dump(exclude_none=True),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found or nada to update")
    release = db.releases.get(entity_id)
    return JSONResponse(release or {})


@app.delete("/api/releases/{entity_id}")
async def delete_release(
    request: Request, entity_id: int, user: Dict[str, Any] = require_admin
) -> JSONResponse:
    success = audit.audit_delete(request, user, "release", db.releases, entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    return JSONResponse({"deleted": entity_id})


@app.get("/api/modules")
async def list_modules_api() -> JSONResponse:
    return JSONResponse(db.modules.list())


@app.post("/api/modules", response_model=dict)
async def create_module(
    request: Request,
    payload: ModuleCreate,
    user: Dict[str, Any] = require_admin,
) -> JSONResponse:
    module_id = audit.audit_insert(request, user, "module", db.modules, payload.model_dump())
    return JSONResponse(db.modules.get(module_id))


@app.put("/api/modules/{entity_id}", response_model=dict)
async def update_module(
    request: Request,
    entity_id: int,
    payload: ModuleUpdate,
    user: Dict[str, Any] = require_admin,
) -> JSONResponse:
    updated = audit.audit_update(
        request, user, "module", db.modules, entity_id,
        payload.model_dump(exclude_none=True),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found or nada to update")
    return JSONResponse(db.modules.get(entity_id))


@app.delete("/api/modules/{entity_id}")
async def delete_module(
    request: Request, entity_id: int, user: Dict[str, Any] = require_admin
) -> JSONResponse:
    success = audit.audit_delete(request, user, "module", db.modules, entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    return JSONResponse({"deleted": entity_id})


@app.get("/api/clients")
async def list_clients_api() -> JSONResponse:
    return JSONResponse(db.clients.list())


@app.post("/api/clients", response_model=dict)
async def create_client(
    request: Request,
    payload: ClientCreate,
    user: Dict[str, Any] = require_admin,
) -> JSONResponse:
    client_id = audit.audit_insert(request, user, "client", db.clients, payload.model_dump())
    return JSONResponse(db.clients.get(client_id))


@app.put("/api/clients/{entity_id}", response_model=dict)
async def update_client(
    request: Request,
    entity_id: int,
    payload: ClientUpdate,
    user: Dict[str, Any] = require_admin,
) -> JSONResponse:
    updated = audit.audit_update(
        request, user, "client", db.clients, entity_id,
        payload.model_dump(exclude_none=True),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found or nada to update")
    return JSONResponse(db.clients.get(entity_id))


@app.delete("/api/clients/{entity_id}")
async def delete_client(
    request: Request, entity_id: int, user: Dict[str, Any] = require_admin
) -> JSONResponse:
    success = audit.audit_delete(request, user, "client", db.clients, entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    return JSONResponse({"deleted": entity_id})


@app.get("/admin", response_class=HTMLResponse, response_model=None)
async def admin_console(request: Request) -> HTMLResponse | RedirectResponse:
    user, redirect = _require_html_role(request, "admin")
    if redirect is not None:
        return redirect
    homologations = db.homologation.list()
    customizations = db.customizations.list()
    releases = db.releases.list()
    clients = db.clients.list()
    client_map = {client["id"]: client for client in clients}
    for release in releases:
        release["client_name"] = client_map.get(release.get("client_id"), {}).get("name")
    module_catalog = _module_catalog()
    context = {
        "request": request,
        "homologations": homologations,
        "customizations": customizations,
        "stage_summary": stats.build_stage_summary(customizations),
        "admin_token": _admin_token(),
        "snapshot": stats.get_meta_snapshot(),
        "refresh_url": request.url.path + "?refresh=true",
        "module_catalog": module_catalog,
        "clients": clients,
        "releases": releases,
        "stage_labels": stats.STAGE_LABELS,
        "current_user": user,
    }
    template = templates.env.get_template("admin.html")
    return HTMLResponse(template.render(**context))


@app.get("/admin/audit", response_class=HTMLResponse, response_model=None)
async def admin_audit(
    request: Request,
    page: int = Query(1, ge=1),
    action: str = Query("", description="Filtrar por ação (create, update, delete)"),
    entity_type: str = Query("", description="Filtrar por tipo de entidade"),
    username: str = Query("", description="Buscar por usuário"),
) -> HTMLResponse | RedirectResponse:
    user, redirect = _require_html_role(request, "admin")
    if redirect is not None:
        return redirect
    per_page = 50
    items, total = db.audit_log.list_paginated(
        page=page,
        per_page=per_page,
        action=action or None,
        entity_type=entity_type or None,
        username=username or None,
    )
    total_pages = max(1, (total + per_page - 1) // per_page)
    pagination = {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_page": page - 1,
        "next_page": page + 1,
        "start": (page - 1) * per_page + 1 if total else 0,
        "end": min(page * per_page, total),
    }

    context = {
        "request": request,
        "current_user": user,
        "snapshot": stats.get_meta_snapshot(),
        "refresh_url": request.url.path + "?refresh=true",
        "active_nav": "audit",
        "pagination": pagination,
        "entries": items,
        "filters": {
            "action": action,
            "entity_type": entity_type,
            "username": username,
        },
        "entity_type_options": db.audit_log.distinct_entity_types(),
        "action_options": ["create", "update", "delete"],
        "entity_labels": audit.AUDIT_LABELS,
        "admin_token": _admin_token(),
    }
    template = templates.env.get_template("admin_audit.html")
    return HTMLResponse(template.render(**context))


@app.get("/admin/export", response_model=None)
async def admin_export(
    format: str = Query(
        "xlsx",
        description="Formato de exportação",
        pattern="^(xlsx|pdf|json)$",
    ),
    _user: Dict[str, Any] = require_admin,
) -> StreamingResponse | JSONResponse:
    payload = export.build_export_payload()
    fmt = format.lower()
    if fmt == "json":
        return JSONResponse(payload)
    if fmt == "xlsx":
        xlsx_bytes = export.export_xlsx(payload)
        headers = {
            "Content-Disposition": 'attachment; filename="cs-controle.xlsx"'
        }
        return StreamingResponse(
            io.BytesIO(xlsx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers,
        )
    if fmt == "pdf":
        pdf_bytes = export.render_export_pdf(payload)
        headers = {"Content-Disposition": 'attachment; filename="cs-controle.pdf"'}
        return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers=headers)
    raise HTTPException(status_code=400, detail="Formato inválido")


@app.post("/admin/homologation/create")
async def admin_create_homologation(
    request: Request,
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
    _user: Dict[str, Any] = require_admin,
) -> RedirectResponse:
    module_value, module_id = utils.resolve_module_selection(module_select, module_manual)
    client_id, client_label = utils.resolve_client_selection(client_select, client_manual)
    audit.audit_insert(
        request, _user, "homologation", db.homologation,
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
        },
    )
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.get("/admin/homologation/{entity_id}/edit", response_class=HTMLResponse, response_model=None)
async def admin_edit_homologation(
    request: Request, entity_id: int
) -> HTMLResponse | RedirectResponse:
    _user, redirect = _require_html_role(request, "admin")
    if redirect is not None:
        return redirect
    record = db.homologation.get(entity_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    context = {
        "request": request,
        "record": record,
        "admin_token": _admin_token(),
        "snapshot": stats.get_meta_snapshot(),
        "module_catalog": _module_catalog(),
        "clients": db.clients.list(),
        "refresh_url": request.url.path + "?refresh=true",
        "current_user": _user,
        "active_nav": "homologations",
    }
    template = templates.env.get_template("edit_homologation.html")
    return HTMLResponse(template.render(**context))


@app.post("/admin/homologation/{entity_id}/update")
async def admin_update_homologation(
    request: Request,
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
    _user: Dict[str, Any] = require_admin,
) -> RedirectResponse:
    payload: dict[str, Any] = {}
    module_value, module_id = utils.resolve_module_selection(module_select, module_manual)
    if module_value is not None:
        payload["module"] = module_value
    if module_id is not None:
        payload["module_id"] = module_id
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
    client_id, client_label = utils.resolve_client_selection(client_select, client_manual)
    if client_label is not None:
        payload["client"] = client_label
    if client_id is not None:
        payload["client_id"] = client_id
    if payload:
        audit.audit_update(request, _user, "homologation", db.homologation, entity_id, payload)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/homologation/{entity_id}/delete")
async def admin_delete_homologation(
    request: Request, entity_id: int, _user: Dict[str, Any] = require_admin,
) -> RedirectResponse:
    audit.audit_delete(request, _user, "homologation", db.homologation, entity_id)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/customizations/create")
async def admin_create_customization(
    request: Request,
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
    _user: Dict[str, Any] = require_admin,
) -> RedirectResponse:
    module_value, module_id = utils.resolve_module_selection(module_select, module_manual)
    client_id, client_label = utils.resolve_client_selection(client_select, client_manual)
    pdf_path = utils.save_pdf(pdf)
    audit.audit_insert(
        request, _user, "customization", db.customizations,
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
            "pf": utils.parse_optional_float(pf),
            "value": utils.parse_optional_float(value),
            "observations": observations,
            "pdf_path": pdf_path,
        },
    )
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.get("/admin/customizations/{entity_id}/edit", response_class=HTMLResponse, response_model=None)
async def admin_edit_customization(
    request: Request, entity_id: int
) -> HTMLResponse | RedirectResponse:
    _user, redirect = _require_html_role(request, "admin")
    if redirect is not None:
        return redirect
    record = db.customizations.get(entity_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    context = {
        "request": request,
        "record": record,
        "admin_token": _admin_token(),
        "snapshot": stats.get_meta_snapshot(),
        "module_catalog": _module_catalog(),
        "clients": db.clients.list(),
        "stage_labels": stats.STAGE_LABELS,
        "refresh_url": request.url.path + "?refresh=true",
        "current_user": _user,
        "active_nav": "customizations",
    }
    template = templates.env.get_template("edit_customization.html")
    return HTMLResponse(template.render(**context))


@app.post("/admin/customizations/{entity_id}/update")
async def admin_update_customization(
    request: Request,
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
    _user: Dict[str, Any] = require_admin,
) -> RedirectResponse:
    payload: dict[str, Any] = {}
    module_value, module_id = utils.resolve_module_selection(module_select, module_manual)
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
        payload["pf"] = utils.parse_optional_float(pf)
    if value is not None:
        payload["value"] = utils.parse_optional_float(value)
    if observations is not None:
        payload["observations"] = observations
    pdf_path = utils.save_pdf(pdf)
    if pdf_path:
        payload["pdf_path"] = pdf_path
    client_id, client_label = utils.resolve_client_selection(client_select, client_manual)
    if client_label is not None:
        payload["client"] = client_label
    if client_id is not None:
        payload["client_id"] = client_id
    if payload:
        audit.audit_update(request, _user, "customization", db.customizations, entity_id, payload)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/customizations/{entity_id}/delete")
async def admin_delete_customization(
    request: Request, entity_id: int, _user: Dict[str, Any] = require_admin,
) -> RedirectResponse:
    audit.audit_delete(request, _user, "customization", db.customizations, entity_id)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/releases/create")
async def admin_create_release(
    request: Request,
    module_select: str | None = Form(None),
    module_manual: str | None = Form(None),
    release_name: str = Form(...),
    version: str | None = Form(None),
    applies_on: str | None = Form(None),
    notes: str | None = Form(None),
    client_select: str | None = Form(None),
    client_manual: str | None = Form(None),
    pdf: UploadFile | None = File(None),
    _user: Dict[str, Any] = require_admin,
) -> RedirectResponse:
    module_value, module_id = utils.resolve_module_selection(module_select, module_manual)
    client_id, client_label = utils.resolve_client_selection(client_select, client_manual)
    pdf_path = utils.save_pdf(pdf)
    audit.audit_insert(
        request, _user, "release", db.releases,
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
        },
    )
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.get("/admin/releases/{entity_id}/edit", response_class=HTMLResponse, response_model=None)
async def admin_edit_release(
    request: Request, entity_id: int
) -> HTMLResponse | RedirectResponse:
    _user, redirect = _require_html_role(request, "admin")
    if redirect is not None:
        return redirect
    record = db.releases.get(entity_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    context = {
        "request": request,
        "record": record,
        "module_catalog": _module_catalog(),
        "clients": db.clients.list(),
        "admin_token": _admin_token(),
        "snapshot": stats.get_meta_snapshot(),
        "refresh_url": request.url.path + "?refresh=true",
        "current_user": _user,
        "active_nav": "releases",
    }
    template = templates.env.get_template("edit_release.html")
    return HTMLResponse(template.render(**context))


@app.post("/admin/releases/{entity_id}/update")
async def admin_update_release(
    request: Request,
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
    _user: Dict[str, Any] = require_admin,
) -> RedirectResponse:
    payload: dict[str, Any] = {}
    module_value, module_id = utils.resolve_module_selection(module_select, module_manual)
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
    client_id, client_label = utils.resolve_client_selection(client_select, client_manual)
    if client_label is not None:
        payload["client"] = client_label
    if client_id is not None:
        payload["client_id"] = client_id
    pdf_path = utils.save_pdf(pdf)
    if pdf_path:
        payload["pdf_path"] = pdf_path
    if payload:
        audit.audit_update(request, _user, "release", db.releases, entity_id, payload)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/releases/{entity_id}/delete")
async def admin_delete_release(
    request: Request, entity_id: int, _user: Dict[str, Any] = require_admin,
) -> RedirectResponse:
    audit.audit_delete(request, _user, "release", db.releases, entity_id)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/modules/create")
async def admin_create_module(
    request: Request,
    name: str = Form(...),
    description: str | None = Form(None),
    owner: str | None = Form(None),
    _user: Dict[str, Any] = require_admin,
) -> RedirectResponse:
    audit.audit_insert(
        request, _user, "module", db.modules,
        {
            "name": name,
            "description": description,
            "owner": owner,
        },
    )
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.get("/admin/modules/{entity_id}/edit", response_class=HTMLResponse, response_model=None)
async def admin_edit_module(
    request: Request, entity_id: int
) -> HTMLResponse | RedirectResponse:
    _user, redirect = _require_html_role(request, "admin")
    if redirect is not None:
        return redirect
    record = db.modules.get(entity_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    context = {
        "request": request,
        "record": record,
        "admin_token": _admin_token(),
        "snapshot": stats.get_meta_snapshot(),
        "refresh_url": request.url.path + "?refresh=true",
        "current_user": _user,
        "active_nav": "modules",
    }
    template = templates.env.get_template("edit_module.html")
    return HTMLResponse(template.render(**context))


@app.post("/admin/modules/{entity_id}/update")
async def admin_update_module(
    request: Request,
    entity_id: int,
    name: str | None = Form(None),
    description: str | None = Form(None),
    owner: str | None = Form(None),
    _user: Dict[str, Any] = require_admin,
) -> RedirectResponse:
    payload: dict[str, Any] = {}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if owner is not None:
        payload["owner"] = owner
    if payload:
        audit.audit_update(request, _user, "module", db.modules, entity_id, payload)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/modules/{entity_id}/delete")
async def admin_delete_module(
    request: Request, entity_id: int, _user: Dict[str, Any] = require_admin,
) -> RedirectResponse:
    audit.audit_delete(request, _user, "module", db.modules, entity_id)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/clients/create")
async def admin_create_client(
    request: Request,
    name: str = Form(...),
    segment: str | None = Form(None),
    owner: str | None = Form(None),
    notes: str | None = Form(None),
    _user: Dict[str, Any] = require_admin,
) -> RedirectResponse:
    audit.audit_insert(
        request, _user, "client", db.clients,
        {
            "name": name,
            "segment": segment,
            "owner": owner,
            "notes": notes,
        },
    )
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.get("/admin/clients/{entity_id}/edit", response_class=HTMLResponse, response_model=None)
async def admin_edit_client(
    request: Request, entity_id: int
) -> HTMLResponse | RedirectResponse:
    _user, redirect = _require_html_role(request, "admin")
    if redirect is not None:
        return redirect
    record = db.clients.get(entity_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    context = {
        "request": request,
        "record": record,
        "admin_token": _admin_token(),
        "snapshot": stats.get_meta_snapshot(),
        "refresh_url": request.url.path + "?refresh=true",
        "current_user": _user,
        "active_nav": "clients",
    }
    template = templates.env.get_template("edit_client.html")
    return HTMLResponse(template.render(**context))


@app.post("/admin/clients/{entity_id}/update")
async def admin_update_client(
    request: Request,
    entity_id: int,
    name: str | None = Form(None),
    segment: str | None = Form(None),
    owner: str | None = Form(None),
    notes: str | None = Form(None),
    _user: Dict[str, Any] = require_admin,
) -> RedirectResponse:
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
        audit.audit_update(request, _user, "client", db.clients, entity_id, payload)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/clients/{entity_id}/delete")
async def admin_delete_client(
    request: Request, entity_id: int, _user: Dict[str, Any] = require_admin,
) -> RedirectResponse:
    audit.audit_delete(request, _user, "client", db.clients, entity_id)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)
