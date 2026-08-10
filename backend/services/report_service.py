"""Service for handling report business logic."""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from ..models import atividade, release as release_model
from ..models.report_cycle import get_cycle
from .pdf_intelligence import PDFIntelligenceService
from .report_generator import ReportGenerator

class ReportService:
    """Orchestrates report generation and data fetching."""

    def __init__(self):
        self.pdf_service = PDFIntelligenceService()
        self.generator = ReportGenerator()

    def _resolve_release_name(self, release_id: Optional[int], release_name: Optional[str]) -> Optional[str]:
        if release_name:
            return release_name
        if not release_id:
            return None
        release_data = release_model.get_release(release_id)
        return release_data.get("release_name") if release_data else None

    def _resolve_cycle_started_at(self, cycle_id: Optional[int] = None) -> Optional[str]:
        if cycle_id is None:
            return None
        cycle = get_cycle(cycle_id)
        if cycle and cycle.get("created_at"):
            return str(cycle["created_at"])
        return None

    def _get_activities(self, release_id: Optional[int] = None) -> List[Dict[str, Any]]:
        if release_id:
            return atividade.list_by_release(release_id, include_history=True)
        return atividade.list_atividade(include_history=True)

    def get_ticket_summary(
        self,
        release_id: Optional[int] = None,
        cycle_id: Optional[int] = None,
        focus_type: Optional[str] = None,
        focus_value: Optional[str] = None,
        focus_label: Optional[str] = None,
    ):
        pdf_context = self.pdf_service.refresh_application_context()
        activities = self._get_activities(release_id)
        release_name = self._resolve_release_name(release_id, None)

        return self.generator.generate_ticket_report(
            activities,
            release_id=release_id,
            release_name=release_name,
            pdf_context=pdf_context,
            cycle_id=cycle_id,
            cycle_started_at=self._resolve_cycle_started_at(cycle_id),
            focus_type=focus_type,
            focus_value=focus_value,
            focus_label=focus_label,
        )

    def get_summary_text(self, **kwargs):
        pdf_context = self.pdf_service.refresh_application_context()
        release_id = kwargs.get("release_id")
        activities = self._get_activities(release_id)
        release_name = self._resolve_release_name(release_id, None)

        return self.generator.generate_summary_report(
            activities,
            pdf_context=pdf_context,
            release_name=release_name,
            cycle_started_at=self._resolve_cycle_started_at(kwargs.get("cycle_id")),
            **kwargs
        )

    def get_html_report(self, **kwargs):
        pdf_context = self.pdf_service.refresh_application_context()
        release_id = kwargs.get("release_id")
        activities = self._get_activities(release_id)
        release_name = self._resolve_release_name(release_id, kwargs.get("release_name"))

        return self.generator.generate_html_report(
            activities,
            pdf_context=pdf_context,
            release_name=release_name,
            cycle_started_at=self._resolve_cycle_started_at(kwargs.get("cycle_id")),
            **kwargs
        )
