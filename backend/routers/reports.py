"""Reports API router."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from ..models import atividade, release as release_model
from ..services.report_generator import ReportGenerator
from ..services.pdf_intelligence import PDFIntelligenceService

router = APIRouter(prefix="/reports", tags=["reports"])


def _render_report_html(release_id: Optional[int] = None, release_name: Optional[str] = None) -> str:
    if release_id:
        activities = atividade.list_by_release(release_id)
    else:
        activities = atividade.list_atividade()

    generator = ReportGenerator()
    return generator.generate_html_report(activities, release_id=release_id, release_name=release_name)


def _resolve_release_name(release_id: Optional[int], release_name: Optional[str]) -> Optional[str]:
    if release_name:
        return release_name
    if not release_id:
        return None
    release_data = release_model.get_release(release_id)
    return release_data.get("release_name") if release_data else None


def _refresh_pdf_context() -> dict:
    service = PDFIntelligenceService()
    return service.refresh_application_context()


@router.get("/ticket-summary")
async def get_ticket_summary(release_id: Optional[int] = None):
    """Get ticket summary report."""
    pdf_context = _refresh_pdf_context()
    if release_id:
        activities = atividade.list_by_release(release_id)
    else:
        activities = atividade.list_atividade()

    generator = ReportGenerator()
    release_name = None
    if release_id:
        release_data = release_model.get_release(release_id)
        release_name = release_data.get("release_name") if release_data else None
    return generator.generate_ticket_report(
        activities,
        release_id=release_id,
        release_name=release_name,
        pdf_context=pdf_context,
    )


@router.get("/summary-text")
async def get_summary_text(release_id: Optional[int] = None):
    """Get text summary report."""
    pdf_context = _refresh_pdf_context()
    release_name = _resolve_release_name(release_id, None)
    activities = atividade.list_by_release(release_id) if release_id else atividade.list_atividade()
    generator = ReportGenerator()
    return {
        "report": generator.generate_summary_report(
            activities,
            release_id=release_id,
            release_name=release_name,
            pdf_context=pdf_context,
        )
    }


@router.get("/html")
async def get_html_report(release_id: Optional[int] = None, release_name: Optional[str] = None):
    """Get HTML management report."""
    pdf_context = _refresh_pdf_context()
    resolved_name = _resolve_release_name(release_id, release_name)
    if release_id:
        activities = atividade.list_by_release(release_id)
    else:
        activities = atividade.list_atividade()
    generator = ReportGenerator()
    return {
        "html": generator.generate_html_report(
            activities,
            release_id=release_id,
            release_name=resolved_name,
            pdf_context=pdf_context,
        )
    }


@router.get("/pdf")
async def get_pdf_report(release_id: Optional[int] = None, release_name: Optional[str] = None):
    """Render the current report view to PDF."""
    pdf_context = _refresh_pdf_context()
    resolved_name = _resolve_release_name(release_id, release_name)
    if release_id:
        activities = atividade.list_by_release(release_id)
    else:
        activities = atividade.list_atividade()
    generator = ReportGenerator()
    html = generator.generate_html_report(
        activities,
        release_id=release_id,
        release_name=resolved_name,
        pdf_context=pdf_context,
    )

    service = PDFIntelligenceService()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        output_path = Path(tmp_pdf.name)

    service.render_pdf_with_chrome(html, str(output_path))
    filename = "relatorio_gerencial.pdf" if not resolved_name else f"relatorio_gerencial_{resolved_name}.pdf"
    safe_filename = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in filename)
    return FileResponse(
        str(output_path),
        filename=safe_filename,
        media_type="application/pdf",
        background=BackgroundTask(lambda path: Path(path).unlink(missing_ok=True), str(output_path)),
    )


@router.get("/by-type/{tipo}")
async def get_by_type(tipo: str):
    """Get all tickets of a specific type."""
    generator = ReportGenerator()
    return generator.get_tickets_by_type(tipo)


@router.get("/ticket/{ticket}")
async def get_ticket(ticket: str):
    """Get a specific ticket by number."""
    generator = ReportGenerator()
    result = generator.get_ticket_by_number(ticket)
    if not result:
        return {"error": "Ticket not found"}
    return result
