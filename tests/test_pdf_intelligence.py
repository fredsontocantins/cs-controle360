import tempfile
import pytest
from backend.services.pdf_intelligence import PDFIntelligenceService
from fpdf import FPDF

def test_pdf_intelligence_analyze():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, "Exemplo de PDF com erro no fluxo de cadastro.")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_path = tmp.name
        pdf.output(pdf_path)

    service = PDFIntelligenceService()
    intel, allocation = service.analyze_pdf(
        pdf_path=pdf_path,
        filename="test_doc.pdf",
        scope_type="global",
        scope_id=1,
        scope_label="Global Test"
    )

    assert intel is not None
    assert intel.filename == "test_doc.pdf"
    assert intel.character_count > 0
