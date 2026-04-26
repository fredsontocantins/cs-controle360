"""Reports API router."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from ..models.report_cycle import list_cycles
from ..services.report_service import ReportService
from ..services.pdf_intelligence import PDFIntelligenceService

router = APIRouter(prefix="/reports", tags=["reports"])

def get_report_service():
    return ReportService()

@router.get("/cycles")
async def get_report_cycles(release_id: Optional[int] = None):
    return list_cycles("reports", release_id)


@router.get("/ticket-summary")
async def get_ticket_summary(
    release_id: Optional[int] = None,
    cycle_id: Optional[int] = None,
    focus_type: Optional[str] = None,
    focus_value: Optional[str] = None,
    focus_label: Optional[str] = None,
    service: ReportService = Depends(get_report_service)
):
    """Get ticket summary report."""
    return service.get_ticket_summary(
        release_id=release_id,
        cycle_id=cycle_id,
        focus_type=focus_type,
        focus_value=focus_value,
        focus_label=focus_label
    )


@router.get("/summary-text")
async def get_summary_text(
    release_id: Optional[int] = None,
    cycle_id: Optional[int] = None,
    focus_type: Optional[str] = None,
    focus_value: Optional[str] = None,
    focus_label: Optional[str] = None,
    service: ReportService = Depends(get_report_service)
):
    """Get text summary report."""
    return {
        "report": service.get_summary_text(
            release_id=release_id,
            cycle_id=cycle_id,
            focus_type=focus_type,
            focus_value=focus_value,
            focus_label=focus_label
        )
    }


@router.get("/html")
async def get_html_report(
    release_id: Optional[int] = None,
    release_name: Optional[str] = None,
    cycle_id: Optional[int] = None,
    focus_type: Optional[str] = None,
    focus_value: Optional[str] = None,
    focus_label: Optional[str] = None,
    service: ReportService = Depends(get_report_service)
):
    """Get HTML management report."""
    return {
        "html": service.get_html_report(
            release_id=release_id,
            release_name=release_name,
            cycle_id=cycle_id,
            focus_type=focus_type,
            focus_value=focus_value,
            focus_label=focus_label
        )
    }


@router.get("/pdf")
async def get_pdf_report(
    release_id: Optional[int] = None,
    release_name: Optional[str] = None,
    cycle_id: Optional[int] = None,
    focus_type: Optional[str] = None,
    focus_value: Optional[str] = None,
    focus_label: Optional[str] = None,
    service: ReportService = Depends(get_report_service)
):
    """Render the current report view to PDF."""
    html = service.get_html_report(
        release_id=release_id,
        release_name=release_name,
        cycle_id=cycle_id,
        focus_type=focus_type,
        focus_value=focus_value,
        focus_label=focus_label
    )

    pdf_intelligence_service = PDFIntelligenceService()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        output_path = Path(tmp_pdf.name)

    pdf_intelligence_service.render_pdf_with_chrome(html, str(output_path))

    # Simple filename resolution
    resolved_name = release_name
    filename = "relatorio_gerencial.pdf" if not resolved_name else f"relatorio_gerencial_{resolved_name}.pdf"
    safe_filename = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in filename)

    return FileResponse(
        str(output_path),
        filename=safe_filename,
        media_type="application/pdf",
        background=BackgroundTask(lambda path: Path(path).unlink(missing_ok=True), str(output_path)),
    )


@router.get("/by-type/{tipo}")
async def get_by_type(tipo: str, service: ReportService = Depends(get_report_service)):
    """Get all tickets of a specific type."""
    return service.generator.get_tickets_by_type(tipo)


@router.get("/ticket/{ticket}")
async def get_ticket(ticket: str, service: ReportService = Depends(get_report_service)):
    """Get a specific ticket by number."""
    result = service.generator.get_ticket_by_number(ticket)
    if not result:
        return {"error": "Ticket not found"}
    return result
