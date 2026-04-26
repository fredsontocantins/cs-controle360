"""Reports API router — the intelligence hub of CS-Controle 360.

This router now centralises ALL application intelligence:
 • Ticket / module / release summaries (existing)
 • PDF Intelligence insights (consolidated from pdf_intelligence service)
 • Playbook recommendations and coverage (consolidated from playbook service)
 • Cross-module metrics aggregation
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from ..models import atividade, release as release_model, homologacao, customizacao, modulo, cliente
from ..models.playbook import list_playbooks
from ..models.report_cycle import get_cycle, list_cycles
from ..services.pdf_intelligence import PDFIntelligenceService
from ..services.playbook_generator import PlaybookGenerator
from ..services.report_generator import ReportGenerator
from ..response import ok

MODULE = "reports"
router = APIRouter(prefix="/reports", tags=["reports"])


def _resolve_release_name(release_id: Optional[int], release_name: Optional[str]) -> Optional[str]:
    if release_name:
        return release_name
    if not release_id:
        return None
    release_data = release_model.get_release(release_id)
    return release_data.get("release_name") if release_data else None


def _resolve_cycle_started_at(cycle_id: Optional[int] = None) -> Optional[str]:
    if cycle_id is None:
        return None
    cycle = get_cycle(cycle_id)
    if cycle and cycle.get("created_at"):
        return str(cycle["created_at"])
    return None


def _refresh_pdf_context() -> dict:
    service = PDFIntelligenceService()
    return service.refresh_application_context()


# ── NEW: Consolidated Intelligence endpoint ━━━━━━━━━━━━━━━━━━━━━━

@router.get("/intelligence")
async def get_consolidated_intelligence(
    release_id: Optional[int] = None,
    cycle_id: Optional[int] = None,
):
    """Consolidated intelligence hub: PDF insights + Playbook recommendations
    + cross-module metrics, all in one call.  This is the main data source
    for the Relatórios page frontend."""

    # 1. PDF Intelligence
    pdf_service = PDFIntelligenceService()
    pdf_context = pdf_service.refresh_application_context()
    pdf_audit = pdf_service.build_cycle_audit()

    # 2. Playbook dashboard
    playbook_gen = PlaybookGenerator()
    playbooks = list_playbooks(cycle_id)
    activities_for_pb = atividade.list_atividade(include_history=cycle_id is not None)
    releases_for_pb = release_model.list_release(include_history=cycle_id is not None)
    playbook_dashboard = playbook_gen.build_dashboard(playbooks, activities_for_pb, releases_for_pb)

    # 3. Cross-module metrics
    all_homologacoes = homologacao.list_homologacao()
    all_customizacoes = customizacao.list_customizacao()
    all_atividades = atividade.list_atividade()
    all_releases = release_model.list_release()
    all_modulos = modulo.list_modulo()
    all_clientes = cliente.list_cliente()

    module_metrics: dict[str, dict] = {}
    for m in all_modulos:
        name = m.get("name") or "sem_nome"
        module_metrics[name] = {
            "name": name,
            "description": m.get("description", ""),
            "owner": m.get("owner", ""),
            "homologacoes": 0,
            "customizacoes": 0,
            "atividades": 0,
            "releases": 0,
        }

    for h in all_homologacoes:
        name = h.get("module") or "sem_modulo"
        if name not in module_metrics:
            module_metrics[name] = {"name": name, "description": "", "owner": "", "homologacoes": 0, "customizacoes": 0, "atividades": 0, "releases": 0}
        module_metrics[name]["homologacoes"] += 1

    for c in all_customizacoes:
        name = c.get("module") or "sem_modulo"
        if name not in module_metrics:
            module_metrics[name] = {"name": name, "description": "", "owner": "", "homologacoes": 0, "customizacoes": 0, "atividades": 0, "releases": 0}
        module_metrics[name]["customizacoes"] += 1

    for r in all_releases:
        name = r.get("module") or "sem_modulo"
        if name not in module_metrics:
            module_metrics[name] = {"name": name, "description": "", "owner": "", "homologacoes": 0, "customizacoes": 0, "atividades": 0, "releases": 0}
        module_metrics[name]["releases"] += 1

    activity_by_status: dict[str, int] = {}
    activity_by_tipo: dict[str, int] = {}
    for a in all_atividades:
        s = a.get("status") or "sem_status"
        activity_by_status[s] = activity_by_status.get(s, 0) + 1
        t = a.get("tipo") or "sem_tipo"
        activity_by_tipo[t] = activity_by_tipo.get(t, 0) + 1

    cross_module = {
        "totals": {
            "homologacoes": len(all_homologacoes),
            "customizacoes": len(all_customizacoes),
            "atividades": len(all_atividades),
            "releases": len(all_releases),
            "modulos": len(all_modulos),
            "clientes": len(all_clientes),
        },
        "activity_by_status": activity_by_status,
        "activity_by_tipo": activity_by_tipo,
        "module_metrics": sorted(module_metrics.values(), key=lambda x: -(x["atividades"] + x["releases"] + x["homologacoes"] + x["customizacoes"])),
    }

    return ok(
        {
            "pdf_intelligence": {
                "totals": pdf_context.get("totals"),
                "themes": pdf_context.get("themes", []),
                "sections": pdf_context.get("sections", []),
                "knowledge_terms": pdf_context.get("knowledge_terms", []),
                "problem_solution_examples": pdf_context.get("problem_solution_examples", []),
                "predictions": pdf_context.get("predictions", []),
                "recommendations": pdf_context.get("recommendations", []),
                "action_items": pdf_context.get("action_items", []),
                "highlights": pdf_context.get("highlights", []),
                "cycle_documents": pdf_context.get("cycle_documents", 0),
                "total_documents": pdf_context.get("total_documents", 0),
                "cycle": pdf_context.get("cycle"),
            },
            "pdf_audit": {
                "counts": pdf_audit.get("counts", {}),
                "cycle": pdf_audit.get("cycle"),
            },
            "playbooks": {
                "totals": playbook_dashboard.get("totals", {}),
                "by_origin": playbook_dashboard.get("by_origin", {}),
                "by_priority": playbook_dashboard.get("by_priority", {}),
                "by_status": playbook_dashboard.get("by_status", {}),
                "coverage": playbook_dashboard.get("coverage", {}),
                "suggestions": playbook_dashboard.get("suggestions", []),
                "ranking": (playbook_dashboard.get("ranking") or [])[:10],
                "effectiveness": playbook_dashboard.get("effectiveness", {}),
            },
            "cross_module": cross_module,
        },
        module=MODULE,
        meta={"release_id": release_id, "cycle_id": cycle_id},
    )


# ── Existing endpoints (unchanged contract for backward compat) ━━━━━━

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
):
    """Get ticket summary report."""
    pdf_context = _refresh_pdf_context()
    if release_id:
        activities = atividade.list_by_release(release_id, include_history=True)
    else:
        activities = atividade.list_atividade(include_history=True)

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
        cycle_id=cycle_id,
        cycle_started_at=_resolve_cycle_started_at(cycle_id),
        focus_type=focus_type,
        focus_value=focus_value,
        focus_label=focus_label,
    )


@router.get("/summary-text")
async def get_summary_text(
    release_id: Optional[int] = None,
    cycle_id: Optional[int] = None,
    focus_type: Optional[str] = None,
    focus_value: Optional[str] = None,
    focus_label: Optional[str] = None,
):
    """Get text summary report."""
    pdf_context = _refresh_pdf_context()
    release_name = _resolve_release_name(release_id, None)
    activities = atividade.list_by_release(release_id, include_history=True) if release_id else atividade.list_atividade(include_history=True)
    generator = ReportGenerator()
    return {
        "report": generator.generate_summary_report(
            activities,
            release_id=release_id,
            release_name=release_name,
            pdf_context=pdf_context,
            cycle_id=cycle_id,
            cycle_started_at=_resolve_cycle_started_at(cycle_id),
            focus_type=focus_type,
            focus_value=focus_value,
            focus_label=focus_label,
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
):
    """Get HTML management report."""
    pdf_context = _refresh_pdf_context()
    resolved_name = _resolve_release_name(release_id, release_name)
    if release_id:
        activities = atividade.list_by_release(release_id, include_history=True)
    else:
        activities = atividade.list_atividade(include_history=True)
    generator = ReportGenerator()
    return {
        "html": generator.generate_html_report(
            activities,
            release_id=release_id,
            release_name=resolved_name,
            pdf_context=pdf_context,
            cycle_id=cycle_id,
            cycle_started_at=_resolve_cycle_started_at(cycle_id),
            focus_type=focus_type,
            focus_value=focus_value,
            focus_label=focus_label,
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
):
    """Render the current report view to PDF."""
    pdf_context = _refresh_pdf_context()
    resolved_name = _resolve_release_name(release_id, release_name)
    if release_id:
        activities = atividade.list_by_release(release_id, include_history=True)
    else:
        activities = atividade.list_atividade(include_history=True)
    generator = ReportGenerator()
    html = generator.generate_html_report(
        activities,
        release_id=release_id,
        release_name=resolved_name,
        pdf_context=pdf_context,
        cycle_id=cycle_id,
        cycle_started_at=_resolve_cycle_started_at(cycle_id),
        focus_type=focus_type,
        focus_value=focus_value,
        focus_label=focus_label,
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
