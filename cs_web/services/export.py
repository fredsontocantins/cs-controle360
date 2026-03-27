"""Export service for generating reports in multiple formats."""

from __future__ import annotations

import io
import json
from datetime import datetime
from typing import Any, Dict

import pandas as pd
from fpdf import FPDF

from cs_web import db

def build_export_payload() -> dict[str, list[dict[str, Any]]]:
    """Build complete export payload."""
    return {
        "homologation": db.list_homologation(),
        "customizations": db.list_customizations(),
        "releases": db.list_releases(),
        "clients": db.list_clients(),
        "modules": db.list_modules(),
    }

def render_export_pdf(payload: dict[str, list[dict[str, Any]]]) -> bytes:
    """Generate PDF report."""
    pdf = FPDF()
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "CS Controle — Relatório consolidado", ln=1)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, f"Gerado em {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC", ln=1)
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
        lambda e: (
            f"{e.get('module') or 'Sem módulo'} / "
            f"{e.get('client') or 'Sem cliente'} | "
            f"{e.get('status') or 'sem status'} | "
            f"Solicitado {e.get('requested_production_date') or '—'} | "
            f"Produção {e.get('production_date') or '—'}"
        ),
    )
    _write_section(
        "Customizações",
        payload["customizations"],
        lambda e: (
            f"{e.get('proposal') or 'Sem proposta'} / "
            f"{e.get('client') or 'Sem cliente'} | "
            f"{e.get('stage') or 'sem etapa'} | "
            f"Valor {('R$ %.2f' % e.get('value')) if e.get('value') else 'N/A'}"
        ),
    )
    _write_section(
        "Releases",
        payload["releases"],
        lambda e: (
            f"{e.get('release_name') or 'Sem nome'} / "
            f"{e.get('module') or 'sem módulo'} | "
            f"Aplica em {e.get('applies_on') or '—'} | "
            f"Cliente {e.get('client') or '—'}"
        ),
    )
    return pdf.output(dest="S").encode("latin-1")

def export_xlsx(payload: dict[str, list[dict[str, Any]]]) -> bytes:
    """Generate XLSX export."""
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
    return buffer.getvalue()

def export_json(payload: dict[str, list[dict[str, Any]]]) -> str:
    """Generate JSON export."""
    return json.dumps(payload, ensure_ascii=False, indent=2)