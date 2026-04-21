"""Export service for generating reports in multiple formats."""

from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from typing import Any, Dict

import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from cs_web import db

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


def build_export_payload() -> dict[str, list[dict[str, Any]]]:
    """Build complete export payload."""
    return {
        "homologation": db.homologation.list(),
        "customizations": db.customizations.list(),
        "releases": db.releases.list(),
        "clients": db.clients.list(),
        "modules": db.modules.list(),
    }


def render_export_pdf(payload: dict[str, list[dict[str, Any]]]) -> bytes:
    """Generate PDF report."""
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
        _pdf_safe(f"Gerado em {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC"),
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
    return bytes(pdf.output())


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
