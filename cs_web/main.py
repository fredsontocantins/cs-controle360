"""FastAPI application that exposes the CS control dashboard."""

from __future__ import annotations

import io
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
from uuid import uuid4

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

import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from cs_control.loader import build_control_snapshot
from cs_web import db
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

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "static" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.cache_size = 0

def _admin_token() -> str:
    return os.environ.get("CS_API_KEY", "cs-secret")


STAGE_LABELS = {
    "em_elaboracao": "Em Elaboração",
    "em_aprovacao": "Em Aprovação",
    "aprovadas": "Aprovadas",
    "aprovadas_sc": "Propostas Aprovadas (SC)",
}

INITIAL_SNAPSHOT_FILE = BASE_DIR / "data" / "initial_snapshot.json"
EXPORT_FORMATS = ("xlsx", "pdf", "json")


require_admin = Depends(require_role("admin"))
require_reader = Depends(require_role("admin", "viewer"))


AUDIT_LABELS: Dict[str, str] = {
    "homologation": "Homologação",
    "customization": "Customização",
    "release": "Release",
    "module": "Módulo",
    "client": "Cliente",
}


def _record_audit(
    request: Request | None,
    user: Dict[str, Any] | None,
    action: str,
    entity_type: str,
    entity_id: int | None,
    before: Dict[str, Any] | None = None,
    after: Dict[str, Any] | None = None,
) -> None:
    """Best-effort audit log recorder. Never raises."""
    try:
        db.audit_log.insert(
            {
                "user_id": (user or {}).get("id"),
                "username": (user or {}).get("username"),
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "before": before,
                "after": after,
                "path": str(request.url.path) if request else None,
                "ip": request.client.host if request and request.client else None,
            }
        )
    except Exception:
        pass


def _audit_insert(
    request: Request | None,
    user: Dict[str, Any] | None,
    entity_type: str,
    repo: Any,
    payload: Dict[str, Any],
) -> int:
    entity_id = repo.insert(payload)
    _record_audit(
        request, user, "create", entity_type, entity_id,
        before=None, after=repo.get(entity_id),
    )
    return entity_id


def _audit_update(
    request: Request | None,
    user: Dict[str, Any] | None,
    entity_type: str,
    repo: Any,
    entity_id: int,
    payload: Dict[str, Any],
) -> bool:
    before = repo.get(entity_id)
    updated = repo.update(entity_id, payload)
    if updated:
        _record_audit(
            request, user, "update", entity_type, entity_id,
            before=before, after=repo.get(entity_id),
        )
    return updated


def _audit_delete(
    request: Request | None,
    user: Dict[str, Any] | None,
    entity_type: str,
    repo: Any,
    entity_id: int,
) -> bool:
    before = repo.get(entity_id)
    deleted = repo.delete(entity_id)
    if deleted:
        _record_audit(
            request, user, "delete", entity_type, entity_id,
            before=before, after=None,
        )
    return deleted


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


def _build_homologated_chart(homologations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Distribution of homologação status (Sim / Não / Pendente)."""
    buckets: Dict[str, int] = {"Sim": 0, "Não": 0, "Pendente": 0}
    for entry in homologations:
        value = (entry.get("homologated") or "").strip() or "Pendente"
        buckets[value] = buckets.get(value, 0) + 1
    return [{"label": label, "value": count} for label, count in buckets.items()]


def _build_stage_chart(customizations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Customization funnel by stage, respecting STAGE_LABELS order."""
    counts: Dict[str, int] = {key: 0 for key in STAGE_LABELS}
    for entry in customizations:
        stage = entry.get("stage") or ""
        if stage in counts:
            counts[stage] += 1
    return [
        {"label": STAGE_LABELS[stage], "value": counts[stage]}
        for stage in STAGE_LABELS
    ]


def _build_releases_chart(releases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Number of releases per month over the last 6 months (including current)."""
    from datetime import date

    today = date.today()
    months: list[tuple[int, int]] = []
    year, month = today.year, today.month
    for _ in range(6):
        months.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    months.reverse()

    buckets: Dict[tuple[int, int], int] = {key: 0 for key in months}
    for entry in releases:
        for field in ("released_at", "created_at", "applied_at"):
            raw = entry.get(field)
            if not raw:
                continue
            try:
                parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            except ValueError:
                continue
            key = (parsed.year, parsed.month)
            if key in buckets:
                buckets[key] += 1
            break

    month_names = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                   "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    return [
        {"label": f"{month_names[m - 1]}/{y % 100:02d}", "value": buckets[(y, m)]}
        for (y, m) in months
    ]


def _resolve_client_selection(client_select: str | None, client_manual: str | None) -> tuple[int | None, str | None]:
    client_id: int | None = None
    if client_select:
        try:
            client_id = int(client_select)
        except ValueError:
            client_id = None
    label = (client_manual or "").strip() or None
    if client_id and not label:
        client = db.clients.get(client_id)
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
            module = db.modules.get(module_id)
            if module:
                return module.get("name"), module_id
    return None, None


def _module_label(entry: dict[str, Any]) -> str:
    label = (entry.get("module") or "").strip()
    if label:
        return label
    module_id = entry.get("module_id")
    if module_id:
        module = db.modules.get(module_id)
        if module:
            return module.get("name") or "Sem módulo"
    return "Sem módulo"


def _build_module_summary(
    homologations: list[dict[str, Any]],
    customizations: list[dict[str, Any]],
    releases: list[dict[str, Any]],
) -> List[dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    catalog = [module.get("name") for module in db.modules.list() if module.get("name")]
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
    modules = db.modules.list()
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
        "homologation": db.homologation.list(),
        "customizations": db.customizations.list(),
        "releases": db.releases.list(),
        "clients": db.clients.list(),
        "modules": db.modules.list(),
    }


# FPDF's core Helvetica font only supports latin-1. Map common Unicode
# punctuation that shows up in Portuguese UI copy/data to safe equivalents
# so the PDF export cannot crash with FPDFUnicodeEncodingException.
_PDF_TEXT_REPLACEMENTS = {
    "\u2014": "-",     # em dash
    "\u2013": "-",     # en dash
    "\u2212": "-",     # minus sign
    "\u2022": "-",     # bullet
    "\u00B7": "-",     # middle dot
    "\u2018": "'",     # left single quote
    "\u2019": "'",     # right single quote
    "\u201C": '"',     # left double quote
    "\u201D": '"',     # right double quote
    "\u2026": "...",   # ellipsis
    "\u00A0": " ",     # non-breaking space
}


def _pdf_safe(text: Any) -> str:
    """Return ``text`` coerced to a latin-1-encodable string.

    FPDF's built-in Helvetica font set only supports latin-1. Any
    character outside that range (em dashes, bullets, smart quotes, …)
    raises ``FPDFUnicodeEncodingException``. Most Portuguese accented
    characters already fit in latin-1; we only need to rewrite the
    punctuation listed in :data:`_PDF_TEXT_REPLACEMENTS` and fall back
    to ``?`` for anything else that slipped through.
    """
    if text is None:
        return ""
    value = str(text)
    for src, dst in _PDF_TEXT_REPLACEMENTS.items():
        value = value.replace(src, dst)
    # Anything left outside latin-1 is replaced with "?" to avoid crashing.
    return value.encode("latin-1", errors="replace").decode("latin-1")


def _render_export_pdf(payload: dict[str, list[dict[str, Any]]]) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    # ``new_x=LMARGIN`` is required because fpdf2's default of ``XPos.RIGHT``
    # leaves the cursor at the right margin, which makes the next
    # ``multi_cell(w=0, ...)`` call fail with ``FPDFException: Not enough
    # horizontal space to render a single character`` (the available width
    # becomes 0).
    pdf.cell(
        0,
        10,
        _pdf_safe("CS Controle — Relatório consolidado"),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(
        0,
        6,
        _pdf_safe(f"Gerado em {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(4)

    def _write_section(title: str, entries: list[dict[str, Any]], line_formatter) -> None:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(
            0,
            6,
            _pdf_safe(f"{title} ({len(entries)})"),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.set_font("Helvetica", "", 10)
        if not entries:
            pdf.cell(
                0,
                6,
                _pdf_safe("- Nenhum registro encontrado."),
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            return
        for entry in entries[:5]:
            pdf.multi_cell(
                0,
                6,
                _pdf_safe(f"- {line_formatter(entry)}"),
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
        pdf.ln(2)

    _write_section(
        "Homologações",
        payload["homologation"],
        lambda entry: (
            f"{entry.get('module') or 'Sem módulo'} / "
            f"{entry.get('client') or 'Sem cliente'} | "
            f"{entry.get('status') or 'sem status'} | "
            f"Solicitado {entry.get('requested_production_date') or '-'} | "
            f"Produção {entry.get('production_date') or '-'}"
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
            f"Aplica em {entry.get('applies_on') or '-'} | "
            f"Cliente {entry.get('client') or '-'}"
        ),
    )
    # fpdf2's ``output`` returns ``bytearray``; normalize to immutable bytes.
    return bytes(pdf.output(dest="S"))


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
    """Resolve authentication for HTML routes.

    Returns a tuple ``(user, redirect)``. Exactly one of the two will be
    non-``None``. Unauthenticated visitors are redirected to ``/login`` with
    a ``next`` parameter pointing back to the current URL. Authenticated
    users whose role is not allowed are redirected to the dashboard.
    """
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
    homologated_chart = _build_homologated_chart(homologations)
    stage_chart = _build_stage_chart(customizations)
    releases_chart = _build_releases_chart(releases)
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
        "stage_summary": _build_stage_summary(customizations),
        "refresh_url": request.url.path + "?refresh=true",
        "admin_token": _admin_token(),
        "current_user": current_user,
    }
    context["snapshot"] = _meta_snapshot()
    context["active_nav"] = "dashboard"
    template = templates.env.get_template("dashboard.html")
    return HTMLResponse(template.render(**context))


DEFAULT_PAGE_SIZE = 20


def _match_search(item: Dict[str, Any], query: str, fields: Tuple[str, ...]) -> bool:
    if not query:
        return True
    needle = query.strip().lower()
    if not needle:
        return True
    for field in fields:
        value = item.get(field)
        if value is None:
            continue
        if needle in str(value).lower():
            return True
    return False


def _paginate(
    items: List[Dict[str, Any]],
    page: int,
    per_page: int = DEFAULT_PAGE_SIZE,
) -> Dict[str, Any]:
    total = len(items)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    return {
        "items": items[start:end],
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_page": page - 1,
        "next_page": page + 1,
        "start": start + 1 if total else 0,
        "end": min(end, total),
    }


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
        "snapshot": _meta_snapshot(),
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
        if _match_search(
            i, q, ("module", "client", "status", "observation", "homologation_version")
        )
    ]
    pagination = _paginate(items, page)
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
    stage_summary = _build_stage_summary(items)
    if stage:
        items = [i for i in items if (i.get("stage") or "") == stage]
    items = [
        i for i in items
        if _match_search(
            i, q, ("proposal", "subject", "client", "module", "owner", "observations")
        )
    ]
    pagination = _paginate(items, page)
    return _render_list_page(
        request,
        "list_customizations.html",
        "customizations",
        {
            "customizations": pagination["items"],
            "pagination": pagination,
            "filters": {"q": q, "stage": stage},
            "stage_summary": stage_summary,
            "stage_labels": STAGE_LABELS,
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
            if _match_search(
                i, q, ("proposal", "subject", "client", "module", "owner", "observations")
            )
        ]
    columns = []
    for key, label in STAGE_LABELS.items():
        column_items = [i for i in items if (i.get("stage") or "") == key]
        columns.append({"key": key, "label": label, "items": column_items})
    return _render_list_page(
        request,
        "board_customizations.html",
        "customizations",
        {
            "columns": columns,
            "filters": {"q": q},
            "stage_labels": STAGE_LABELS,
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
        if _match_search(
            i, q, ("release_name", "module", "client", "client_name", "version", "notes")
        )
    ]
    pagination = _paginate(items, page)
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
            if _match_search(
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
    items = [i for i in items if _match_search(i, q, ("name", "owner", "description"))]
    pagination = _paginate(items, page)
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
        if _match_search(i, q, ("name", "segment", "owner", "notes"))
    ]
    pagination = _paginate(items, page)
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
            "built_at": datetime.utcnow().isoformat() + "Z",
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
    entity_id = _audit_insert(request, user, "homologation", db.homologation, payload.dict())
    created = db.homologation.get(entity_id)
    return JSONResponse(created)


@app.put("/api/homologation/{entity_id}", response_model=dict)
async def update_homologation(
    request: Request,
    entity_id: int,
    payload: HomologationUpdate,
    user: Dict[str, Any] = require_admin,
) -> JSONResponse:
    updated = _audit_update(
        request, user, "homologation", db.homologation, entity_id,
        payload.dict(exclude_none=True),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found or nada to update")
    return JSONResponse(db.homologation.get(entity_id))


@app.delete("/api/homologation/{entity_id}")
async def delete_homologation(
    request: Request, entity_id: int, user: Dict[str, Any] = require_admin
) -> JSONResponse:
    success = _audit_delete(request, user, "homologation", db.homologation, entity_id)
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
    entity_id = _audit_insert(
        request, user, "customization", db.customizations, payload.dict()
    )
    return JSONResponse(db.customizations.get(entity_id))


@app.put("/api/customizations/{entity_id}", response_model=dict)
async def update_customization(
    request: Request,
    entity_id: int,
    payload: CustomizationUpdate,
    user: Dict[str, Any] = require_admin,
) -> JSONResponse:
    updated = _audit_update(
        request, user, "customization", db.customizations, entity_id,
        payload.dict(exclude_none=True),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found or nada to update")
    return JSONResponse(db.customizations.get(entity_id))


@app.delete("/api/customizations/{entity_id}")
async def delete_customization(
    request: Request, entity_id: int, user: Dict[str, Any] = require_admin
) -> JSONResponse:
    success = _audit_delete(request, user, "customization", db.customizations, entity_id)
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
    release_id = _audit_insert(request, user, "release", db.releases, payload.dict())
    release = db.releases.get(release_id)
    return JSONResponse(release or {})


@app.put("/api/releases/{entity_id}", response_model=dict)
async def update_release(
    request: Request,
    entity_id: int,
    payload: ReleaseUpdate,
    user: Dict[str, Any] = require_admin,
) -> JSONResponse:
    updated = _audit_update(
        request, user, "release", db.releases, entity_id,
        payload.dict(exclude_none=True),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found or nada to update")
    release = db.releases.get(entity_id)
    return JSONResponse(release or {})


@app.delete("/api/releases/{entity_id}")
async def delete_release(
    request: Request, entity_id: int, user: Dict[str, Any] = require_admin
) -> JSONResponse:
    success = _audit_delete(request, user, "release", db.releases, entity_id)
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
    module_id = _audit_insert(request, user, "module", db.modules, payload.dict())
    return JSONResponse(db.modules.get(module_id))


@app.put("/api/modules/{entity_id}", response_model=dict)
async def update_module(
    request: Request,
    entity_id: int,
    payload: ModuleUpdate,
    user: Dict[str, Any] = require_admin,
) -> JSONResponse:
    updated = _audit_update(
        request, user, "module", db.modules, entity_id,
        payload.dict(exclude_none=True),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found or nada to update")
    return JSONResponse(db.modules.get(entity_id))


@app.delete("/api/modules/{entity_id}")
async def delete_module(
    request: Request, entity_id: int, user: Dict[str, Any] = require_admin
) -> JSONResponse:
    success = _audit_delete(request, user, "module", db.modules, entity_id)
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
    client_id = _audit_insert(request, user, "client", db.clients, payload.dict())
    return JSONResponse(db.clients.get(client_id))


@app.put("/api/clients/{entity_id}", response_model=dict)
async def update_client(
    request: Request,
    entity_id: int,
    payload: ClientUpdate,
    user: Dict[str, Any] = require_admin,
) -> JSONResponse:
    updated = _audit_update(
        request, user, "client", db.clients, entity_id,
        payload.dict(exclude_none=True),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Record not found or nada to update")
    return JSONResponse(db.clients.get(entity_id))


@app.delete("/api/clients/{entity_id}")
async def delete_client(
    request: Request, entity_id: int, user: Dict[str, Any] = require_admin
) -> JSONResponse:
    success = _audit_delete(request, user, "client", db.clients, entity_id)
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
        "stage_summary": _build_stage_summary(customizations),
        "admin_token": _admin_token(),
        "snapshot": _meta_snapshot(),
        "refresh_url": request.url.path + "?refresh=true",
        "module_catalog": module_catalog,
        "clients": clients,
        "releases": releases,
        "stage_labels": STAGE_LABELS,
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
        "snapshot": _meta_snapshot(),
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
        "entity_labels": AUDIT_LABELS,
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
    module_value, module_id = _resolve_module_selection(module_select, module_manual)
    client_id, client_label = _resolve_client_selection(client_select, client_manual)
    _audit_insert(
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
        "snapshot": _meta_snapshot(),
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
        _audit_update(request, _user, "homologation", db.homologation, entity_id, payload)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/homologation/{entity_id}/delete")
async def admin_delete_homologation(
    request: Request, entity_id: int, _user: Dict[str, Any] = require_admin,
) -> RedirectResponse:
    _audit_delete(request, _user, "homologation", db.homologation, entity_id)
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
    module_value, module_id = _resolve_module_selection(module_select, module_manual)
    client_id, client_label = _resolve_client_selection(client_select, client_manual)
    pdf_path = _save_pdf(pdf)
    _audit_insert(
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
            "pf": _parse_optional_float(pf),
            "value": _parse_optional_float(value),
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
        "snapshot": _meta_snapshot(),
        "module_catalog": _module_catalog(),
        "clients": db.clients.list(),
        "stage_labels": STAGE_LABELS,
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
        _audit_update(request, _user, "customization", db.customizations, entity_id, payload)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/customizations/{entity_id}/delete")
async def admin_delete_customization(
    request: Request, entity_id: int, _user: Dict[str, Any] = require_admin,
) -> RedirectResponse:
    _audit_delete(request, _user, "customization", db.customizations, entity_id)
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
    module_value, module_id = _resolve_module_selection(module_select, module_manual)
    client_id, client_label = _resolve_client_selection(client_select, client_manual)
    pdf_path = _save_pdf(pdf)
    _audit_insert(
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
        "snapshot": _meta_snapshot(),
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
        _audit_update(request, _user, "release", db.releases, entity_id, payload)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/releases/{entity_id}/delete")
async def admin_delete_release(
    request: Request, entity_id: int, _user: Dict[str, Any] = require_admin,
) -> RedirectResponse:
    _audit_delete(request, _user, "release", db.releases, entity_id)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/modules/create")
async def admin_create_module(
    request: Request,
    name: str = Form(...),
    description: str | None = Form(None),
    owner: str | None = Form(None),
    _user: Dict[str, Any] = require_admin,
) -> RedirectResponse:
    _audit_insert(
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
        "snapshot": _meta_snapshot(),
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
        _audit_update(request, _user, "module", db.modules, entity_id, payload)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/modules/{entity_id}/delete")
async def admin_delete_module(
    request: Request, entity_id: int, _user: Dict[str, Any] = require_admin,
) -> RedirectResponse:
    _audit_delete(request, _user, "module", db.modules, entity_id)
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
    _audit_insert(
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
        "snapshot": _meta_snapshot(),
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
        _audit_update(request, _user, "client", db.clients, entity_id, payload)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)


@app.post("/admin/clients/{entity_id}/delete")
async def admin_delete_client(
    request: Request, entity_id: int, _user: Dict[str, Any] = require_admin,
) -> RedirectResponse:
    _audit_delete(request, _user, "client", db.clients, entity_id)
    return RedirectResponse("/admin", status_code=fastapi_status.HTTP_303_SEE_OTHER)
