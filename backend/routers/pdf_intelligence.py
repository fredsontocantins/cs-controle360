"""PDF intelligence router."""

from __future__ import annotations

import json
import hashlib
import shutil
import tempfile
import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..config import UPLOADS_DIR
from ..models import customizacao, homologacao, release, atividade
from ..models.pdf_document import find_document_by_hash, get_document, insert_document, list_documents
from ..models.report_cycle import get_active_cycle, open_cycle
from ..services.pdf_intelligence import PDFIntelligenceService

router = APIRouter(prefix="/pdf-intelligence", tags=["pdf-intelligence"])


class PdfProcessRequest(BaseModel):
    document_ids: List[int] = Field(default_factory=list)
    scope_type: Optional[str] = None
    scope_id: Optional[int] = None
    scope_label: Optional[str] = None


def _scope_label(scope_type: str, scope_id: Optional[int]) -> Optional[str]:
    if scope_type == "release" and scope_id:
        data = release.get_release(scope_id)
        if data:
            return data.get("release_name") or data.get("version")
    if scope_type == "customizacao" and scope_id:
        data = customizacao.get_customizacao(scope_id)
        if data:
            return data.get("subject") or data.get("proposal")
    if scope_type == "homologacao" and scope_id:
        data = homologacao.get_homologacao(scope_id)
        if data:
            return data.get("module") or data.get("client")
    if scope_type == "atividade" and scope_id:
        data = atividade.get_atividade(scope_id)
        if data:
            return data.get("title") or data.get("ticket")
    return None


def _safe_token(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value).strip("_") or "file"


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_report_cycle(scope_label: Optional[str]) -> Optional[int]:
    cycle = get_active_cycle("reports", None)
    if cycle and cycle.get("status") == "aberto":
        return cycle.get("id")
    return open_cycle("reports", None, scope_label, None)


@router.post("/process")
async def process_pdf_documents(payload: PdfProcessRequest):
    """Process staged PDFs and optionally force re-read selected documents."""
    service = PDFIntelligenceService()
    cycle = get_active_cycle("reports", None)
    cycle_id = cycle.get("id") if cycle else None
    result = service.process_documents(
        document_ids=payload.document_ids,
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
        cycle_id=cycle_id,
    )
    context = service.refresh_application_context()
    audit = service.build_cycle_audit()
    return {
        "status": "processed",
        "documents": result["documents"],
        "skipped_documents": result["skipped_documents"],
        "messages": result["messages"],
        "context": context,
        "audit": audit,
    }


@router.get("")
async def list_pdf_documents(scope_type: Optional[str] = None, scope_id: Optional[int] = None):
    """List uploaded PDF intelligence documents."""
    return list_documents(scope_type=scope_type, scope_id=scope_id)


@router.get("/application-context")
async def get_application_context():
    """Return the consolidated intelligence of all PDFs in the application."""
    service = PDFIntelligenceService()
    return service.refresh_application_context()


@router.get("/cycle-audit")
async def get_cycle_audit():
    """Return the audit of PDFs already read versus new or changed files in the current cycle."""
    service = PDFIntelligenceService()
    return service.build_cycle_audit()


@router.post("/upload")
async def upload_pdf_documents(
    scope_type: str = Form("auto"),
    scope_id: Optional[int] = Form(None),
    scope_label: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
):
    """Upload one or more PDFs and stage them for later processing."""
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum PDF enviado.")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    service = PDFIntelligenceService()
    uploaded = []
    skipped = []

    resolved_label = scope_label or _scope_label(scope_type, scope_id)
    report_cycle_id = _resolve_report_cycle(resolved_label)

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"Arquivo inválido: {file.filename}")

        fd, temp_name = tempfile.mkstemp(prefix="pdfintel_", suffix=".pdf")
        os.close(fd)
        temp_path = Path(temp_name)
        target_path: Optional[Path] = None

        try:
            with temp_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            target_name = f"{_safe_token(scope_type)}_{scope_id or 'global'}_{_safe_token(Path(file.filename).stem)}.pdf"
            target_path = UPLOADS_DIR / target_name
            shutil.copy2(temp_path, target_path)
            current_hash = _file_hash(target_path)
            current_size = target_path.stat().st_size
            existing_document = find_document_by_hash(current_hash)

            if existing_document:
                existing_summary = existing_document.get("summary") or {}
                skipped.append(
                    {
                        "filename": file.filename,
                        "pdf_url": f"/uploads/{target_name}",
                        "status": "already_analyzed",
                        "message": "Arquivo PDF já foi analisado anteriormente e foi descartado da análise atual.",
                        "existing_document_id": existing_document.get("id"),
                        "existing_scope_type": existing_document.get("scope_type"),
                        "existing_scope_label": existing_document.get("scope_label"),
                        "allocation": {
                            "scope_type": existing_document.get("scope_type"),
                            "scope_id": existing_document.get("scope_id"),
                            "scope_label": existing_document.get("scope_label"),
                            "allocation_method": existing_document.get("allocation_method") or "existing",
                            "allocation_reason": "Arquivo já analisado anteriormente.",
                        },
                        "summary": existing_summary,
                    }
                )
                target_path.unlink(missing_ok=True)
                continue

            document_id = insert_document(
                {
                    "scope_type": scope_type,
                    "scope_id": scope_id,
                    "scope_label": resolved_label,
                    "report_cycle_id": report_cycle_id,
                    "filename": file.filename,
                    "pdf_path": f"uploads/{target_name}",
                    "file_hash": current_hash,
                    "file_size": current_size,
                    "analysis_state": "pending",
                    "source_document_id": None,
                    "allocation_method": "staged",
                    "allocation_reason": "Arquivo enviado e aguardando processamento no menu Relatórios.",
                    "summary_json": json.dumps({}, ensure_ascii=False),
                    "last_analyzed_at": None,
                    "last_analyzed_hash": None,
                }
            )

            uploaded.append({
                "id": document_id,
                "scope_type": scope_type,
                "scope_id": scope_id,
                "scope_label": resolved_label,
                "analysis_state": "pending",
                "report_cycle_id": report_cycle_id,
                "file_hash": current_hash,
                "allocation_method": "staged",
                "allocation_reason": "Arquivo enviado e aguardando processamento no menu Relatórios.",
                "pdf_url": f"/uploads/{target_name}",
            })
        finally:
            temp_path.unlink(missing_ok=True)

    status = "staged"
    if uploaded and skipped:
        status = "staged_with_duplicates"
    elif skipped and not uploaded:
        status = "already_analyzed"
    return {
        "status": status,
        "documents": uploaded,
        "skipped_documents": skipped,
        "messages": [item["message"] for item in skipped],
    }


@router.get("/{document_id}")
async def get_pdf_document(document_id: int):
    """Get a single analyzed PDF document."""
    result = get_document(document_id)
    if not result:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    return result


@router.get("/{document_id}/html")
async def get_pdf_document_html(document_id: int):
    """Get a printable HTML report for a document."""
    result = get_document(document_id)
    if not result:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    service = PDFIntelligenceService()
    return {"html": service.build_html_report(service.analyze(
        pdf_path=str(UPLOADS_DIR.parent / result["pdf_path"]),
        filename=result["filename"],
        scope_type=result["scope_type"],
        scope_id=result.get("scope_id"),
        scope_label=result.get("scope_label"),
    ))}


@router.get("/{document_id}/pdf")
async def download_pdf_document(document_id: int):
    """Render a PDF intelligence report to a PDF file."""
    result = get_document(document_id)
    if not result:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    service = PDFIntelligenceService()
    analysis = service.analyze(
        pdf_path=str(UPLOADS_DIR.parent / result["pdf_path"]),
        filename=result["filename"],
        scope_type=result["scope_type"],
        scope_id=result.get("scope_id"),
        scope_label=result.get("scope_label"),
    )
    html = service.build_html_report(analysis)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        output_path = tmp_pdf.name

    service.render_pdf_with_chrome(html, output_path)
    return FileResponse(output_path, filename=f"{Path(result['filename']).stem}_inteligencia.pdf", media_type="application/pdf")
