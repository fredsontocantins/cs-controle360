"""Release API router."""

from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List
import shutil
from pathlib import Path

from ..models import release
from ..models.atividade import list_by_release
from ..schemas import release as schema
from ..config import UPLOADS_DIR
from ..services.pdf_reader import PDFReaderService

router = APIRouter(prefix="/release", tags=["release"])


@router.get("", response_model=List[dict])
async def list_releases():
    """List all releases."""
    return release.list_release()


@router.get("/{entity_id}", response_model=dict)
async def get_release(entity_id: int):
    """Get a single release by ID."""
    result = release.get_release(entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Release não encontrado")
    return result


@router.post("", response_model=dict)
async def create_release(data: schema.ReleaseCreate):
    """Create a new release."""
    entity_id = release.insert_release(data.model_dump())
    return release.get_release(entity_id)


@router.put("/{entity_id}", response_model=dict)
async def update_release(entity_id: int, data: schema.ReleaseUpdate):
    """Update an existing release."""
    success = release.update_release(entity_id, data.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="Release não encontrado")
    return release.get_release(entity_id)


@router.delete("/{entity_id}")
async def delete_release(entity_id: int):
    """Delete a release."""
    success = release.delete_release(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Release não encontrado")
    return {"status": "deleted"}


@router.post("/{entity_id}/upload-pdf")
async def upload_pdf_and_extract(entity_id: int, file: UploadFile = File(...)):
    """Upload a PDF release note and automatically extract activities."""
    rel = release.get_release(entity_id)
    if not rel:
        raise HTTPException(status_code=404, detail="Release não encontrado")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    # Save PDF
    filename = f"release_{entity_id}_{file.filename}"
    filepath = UPLOADS_DIR / filename

    with filepath.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    pdf_path = f"uploads/{filename}"

    # Update release with PDF path
    release.update_release(entity_id, {"pdf_path": pdf_path})

    # Extract activities from PDF
    pdf_full_path = UPLOADS_DIR.parent / pdf_path
    try:
        pdf_reader = PDFReaderService()
        activity_ids = pdf_reader.extract_and_save(str(pdf_full_path), entity_id)
    except Exception as e:
        return {
            "pdf_path": pdf_path,
            "status": "uploaded_but_extraction_failed",
            "error": str(e),
            "activities_created": 0
        }

    return {
        "pdf_path": pdf_path,
        "pdf_url": f"/{pdf_path}",
        "status": "uploaded_and_processed",
        "activities_created": len(activity_ids),
        "activity_ids": activity_ids
    }


@router.get("/{entity_id}/atividades", response_model=List[dict])
async def get_release_atividades(entity_id: int):
    """Get all activities for a specific release."""
    rel = release.get_release(entity_id)
    if not rel:
        raise HTTPException(status_code=404, detail="Release não encontrado")
    return list_by_release(entity_id)
