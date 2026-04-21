"""Customização API router."""

from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List
import shutil
from pathlib import Path

from ..models import customizacao
from ..schemas import customizacao as schema
from ..config import UPLOADS_DIR

router = APIRouter(prefix="/customizacao", tags=["customizacao"])


@router.get("", response_model=List[dict])
async def list_customizacoes():
    """List all customizations."""
    return customizacao.list_customizacao()


@router.get("/{entity_id}", response_model=dict)
async def get_customizacao(entity_id: int):
    """Get a single customization by ID."""
    result = customizacao.get_customizacao(entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Customização não encontrada")
    return result


@router.post("", response_model=dict)
async def create_customizacao(data: schema.CustomizacaoCreate):
    """Create a new customization."""
    entity_id = customizacao.insert_customizacao(data.model_dump())
    return customizacao.get_customizacao(entity_id)


@router.put("/{entity_id}", response_model=dict)
async def update_customizacao(entity_id: int, data: schema.CustomizacaoUpdate):
    """Update an existing customization."""
    success = customizacao.update_customizacao(entity_id, data.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="Customização não encontrada")
    return customizacao.get_customizacao(entity_id)


@router.delete("/{entity_id}")
async def delete_customizacao(entity_id: int):
    """Delete a customization."""
    success = customizacao.delete_customizacao(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Customização não encontrada")
    return {"status": "deleted"}


@router.post("/{entity_id}/upload-pdf")
async def upload_pdf(entity_id: int, file: UploadFile = File(...)):
    """Upload a PDF for a customization."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    custom = customizacao.get_customizacao(entity_id)
    if not custom:
        raise HTTPException(status_code=404, detail="Customização não encontrada")

    # Save file
    filename = f"customizacao_{entity_id}_{file.filename}"
    filepath = UPLOADS_DIR / filename

    with filepath.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Update record
    pdf_path = f"uploads/{filename}"
    customizacao.update_customizacao(entity_id, {"pdf_path": pdf_path})

    return {"pdf_path": pdf_path, "status": "uploaded"}