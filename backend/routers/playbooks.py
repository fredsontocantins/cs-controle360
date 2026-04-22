"""Playbooks API router."""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from starlette.background import BackgroundTask

from ..models import atividade, release as release_model
from ..models.pdf_document import list_documents
from ..models.playbook import delete_playbook, get_playbook, insert_playbook, list_playbooks, update_playbook
from ..models.report_cycle import close_cycle, get_active_cycle, get_cycle, get_open_cycle, list_cycles, open_cycle
from ..services.pdf_intelligence import PDFIntelligenceService
from ..services.playbook_generator import PlaybookGenerator
from ..schemas.playbook import (
    PlaybookGenerateManual,
    PlaybookStatusUpdate,
    PlaybookUpdate,
    ReportCycleClose,
    ReportCycleCreate,
)

router = APIRouter(prefix="/playbooks", tags=["playbooks"])


def _sanitize_filename(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value).strip("_") or "playbook"


def _cycle_scope(release_id: Optional[int], scope_type: str = "reports") -> tuple[str, Optional[int]]:
    return scope_type, release_id


@router.get("")
async def get_playbooks(cycle_id: Optional[int] = None):
    return list_playbooks(cycle_id)


@router.get("/dashboard")
async def get_dashboard(cycle_id: Optional[int] = None):
    generator = PlaybookGenerator()
    playbooks = list_playbooks(cycle_id)
    activities = atividade.list_atividade(include_history=cycle_id is not None)
    releases = release_model.list_release(include_history=cycle_id is not None)
    if cycle_id is not None:
        cycle = get_cycle(cycle_id)
        if cycle:
            from ..models.report_cycle import get_cycle_window, parse_cycle_datetime
            start, end = get_cycle_window(cycle_id)
            cycle_start = start.isoformat() if start else None
            cycle_end = end.isoformat() if end else None
            if cycle_start:
                activities = [
                    item for item in activities
                    if item and parse_cycle_datetime(item.get("created_at") or item.get("updated_at") or item.get("completed_at")) >= parse_cycle_datetime(cycle_start)
                    and (not cycle_end or parse_cycle_datetime(item.get("created_at") or item.get("updated_at") or item.get("completed_at")) < parse_cycle_datetime(cycle_end))
                ]
                releases = [
                    item for item in releases
                    if item and parse_cycle_datetime(item.get("applies_on") or item.get("created_at")) >= parse_cycle_datetime(cycle_start)
                    and (not cycle_end or parse_cycle_datetime(item.get("applies_on") or item.get("created_at")) < parse_cycle_datetime(cycle_end))
                ]
    return generator.build_dashboard(playbooks, activities, releases)


@router.get("/suggestions")
async def get_suggestions(cycle_id: Optional[int] = None):
    dashboard = await get_dashboard(cycle_id)
    return {"suggestions": dashboard["suggestions"], "coverage": dashboard["coverage"]}


@router.get("/cycles")
async def get_cycles(release_id: Optional[int] = None):
    return list_cycles("reports", release_id)


@router.get("/cycle")
async def get_cycle(release_id: Optional[int] = None):
    cycle = get_active_cycle("reports", release_id)
    return {"cycle": cycle}


@router.post("/cycle/open")
async def open_report_cycle(data: ReportCycleCreate):
    existing_open = get_open_cycle(data.scope_type or "reports", data.scope_id)
    if existing_open:
        return {"status": "aberto", "cycle": existing_open, "id": existing_open["id"], "existing": True}
    cycle_id = open_cycle(
        data.scope_type or "reports",
        data.scope_id,
        data.scope_label,
        data.period_label,
    )
    return {"status": "aberto", "cycle": get_active_cycle(data.scope_type or "reports", data.scope_id), "id": cycle_id}


@router.post("/cycle/close")
async def close_report_cycle(data: ReportCycleClose):
    cycle = get_open_cycle(data.scope_type or "reports", data.scope_id)
    if not cycle:
        raise HTTPException(status_code=404, detail="Não existe prestação de contas aberta para este recorte.")

    cycle_id = cycle["id"]
    success = close_cycle(cycle["id"], data.notes, data.closed_period_label)
    if not success:
        raise HTTPException(status_code=400, detail="Não foi possível fechar a prestação de contas.")

    reopened = None
    if data.reopen_new:
        open_cycle(data.scope_type or "reports", data.scope_id, data.scope_label, data.next_period_label)
        reopened = get_active_cycle(data.scope_type or "reports", data.scope_id)

    return {
        "status": "prestado",
        "closed_cycle": get_cycle(cycle_id),
        "opened_new": bool(data.reopen_new),
        "new_cycle": reopened,
    }


@router.post("/manual")
async def create_manual_playbook(data: PlaybookGenerateManual):
    generator = PlaybookGenerator()
    payload = generator.generate_manual(data.title, data.area, data.objective, data.audience, data.notes)
    entity_id = insert_playbook(payload)
    return get_playbook(entity_id)


@router.post("/generate/errors")
async def generate_error_playbooks(limit: int = Query(default=5, ge=1, le=20)):
    generator = PlaybookGenerator()
    items = generator.generate_from_errors(limit=limit)
    created = []
    for payload in items:
        existing = next((item for item in list_playbooks() if item.get("source_key") == payload.get("source_key")), None)
        if existing:
            update_playbook(existing["id"], payload)
            created.append(get_playbook(existing["id"]))
        else:
            entity_id = insert_playbook(payload)
            created.append(get_playbook(entity_id))
    return {"status": "generated", "playbooks": created}


@router.post("/generate/release/{release_id}")
async def generate_release_playbooks(release_id: int):
    generator = PlaybookGenerator()
    items = generator.generate_from_release(release_id)
    if not items:
        raise HTTPException(status_code=404, detail="Não foi possível gerar playbooks para esta release.")

    created = []
    for payload in items:
        existing = next((item for item in list_playbooks() if item.get("source_key") == payload.get("source_key")), None)
        if existing:
            update_playbook(existing["id"], payload)
            created.append(get_playbook(existing["id"]))
        else:
            entity_id = insert_playbook(payload)
            created.append(get_playbook(entity_id))
    return {"status": "generated", "playbooks": created}


@router.post("/generate/predictions")
async def generate_prediction_playbooks():
    service = PDFIntelligenceService()
    context = service.refresh_application_context()
    predictions = context.get("predictions") or []
    if not predictions:
        raise HTTPException(status_code=404, detail="Não há previsões disponíveis para gerar playbooks.")

    generator = PlaybookGenerator()
    items = generator.generate_from_predictions(predictions, scope_label=context.get("cycle", {}).get("period_label") if context.get("cycle") else None)
    created = []
    for payload in items:
        existing = next((item for item in list_playbooks() if item.get("source_key") == payload.get("source_key")), None)
        if existing:
            update_playbook(existing["id"], payload)
            created.append(get_playbook(existing["id"]))
        else:
            entity_id = insert_playbook(payload)
            created.append(get_playbook(entity_id))
    return {"status": "generated", "playbooks": created, "predictions": predictions[:10]}


@router.get("/{entity_id}")
async def get_single_playbook(entity_id: int):
    result = get_playbook(entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Playbook não encontrado")
    return result


@router.put("/{entity_id}")
async def update_single_playbook(entity_id: int, data: PlaybookUpdate):
    success = update_playbook(entity_id, data.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="Playbook não encontrado")
    return get_playbook(entity_id)


@router.patch("/{entity_id}/status")
async def update_playbook_status(entity_id: int, data: PlaybookStatusUpdate):
    payload = {"status": data.status}
    if data.status == "prestado":
        payload["closed_at"] = datetime.utcnow().isoformat()
    elif data.status == "ativo":
        payload["closed_at"] = None
    success = update_playbook(entity_id, payload)
    if not success:
        raise HTTPException(status_code=404, detail="Playbook não encontrado")
    return get_playbook(entity_id)


@router.delete("/{entity_id}")
async def remove_playbook(entity_id: int):
    success = delete_playbook(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Playbook não encontrado")
    return {"status": "deleted"}


@router.get("/{entity_id}/html")
async def get_playbook_html(entity_id: int):
    result = get_playbook(entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Playbook não encontrado")
    generator = PlaybookGenerator()
    return HTMLResponse(generator.build_playbook_html(result))


@router.get("/{entity_id}/pdf")
async def download_playbook_pdf(entity_id: int):
    result = get_playbook(entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Playbook não encontrado")
    generator = PlaybookGenerator()
    html = generator.build_playbook_html(result)
    service = PDFIntelligenceService()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        output_path = Path(tmp_pdf.name)

    service.render_pdf_with_chrome(html, str(output_path))
    filename = _sanitize_filename(f"{result['title']}_playbook.pdf")
    return FileResponse(
        str(output_path),
        filename=filename,
        media_type="application/pdf",
        background=BackgroundTask(lambda path: Path(path).unlink(missing_ok=True), str(output_path)),
    )
