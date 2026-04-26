"""Release API router — fully independent module."""

from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List
import shutil
from pathlib import Path

from ..models import release
from ..models.atividade import list_by_release
from ..schemas import release as schema
from ..config import UPLOADS_DIR
from ..services.pdf_reader import PDFReaderService
from ..response import ok, ok_list, ok_deleted

MODULE = "release"
router = APIRouter(prefix="/release", tags=["release"])


@router.get("/stats")
async def get_stats():
    items = release.list_release()
    total = len(items)
    by_module: dict[str, int] = {}
    for item in items:
        m = item.get("module") or "sem_modulo"
        by_module[m] = by_module.get(m, 0) + 1
    latest = items[0] if items else None
    return ok(
        {"total": total, "by_module": by_module, "latest": latest},
        module=MODULE,
    )


@router.get("")
async def list_releases():
    return ok_list(release.list_release(), module=MODULE)


@router.get("/{entity_id}")
async def get_release(entity_id: int):
    result = release.get_release(entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Release não encontrado")
    return ok(result, module=MODULE)


@router.post("")
async def create_release(data: schema.ReleaseCreate):
    entity_id = release.insert_release(data.model_dump())
    return ok(release.get_release(entity_id), module=MODULE, meta={"action": "created"})


@router.put("/{entity_id}")
async def update_release(entity_id: int, data: schema.ReleaseUpdate):
    success = release.update_release(entity_id, data.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="Release não encontrado")
    return ok(release.get_release(entity_id), module=MODULE, meta={"action": "updated"})


@router.delete("/{entity_id}")
async def delete_release(entity_id: int):
    success = release.delete_release(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Release não encontrado")
    return ok_deleted(module=MODULE)


@router.post("/{entity_id}/upload-pdf")
async def upload_pdf_and_extract(entity_id: int, file: UploadFile = File(...)):
    rel = release.get_release(entity_id)
    if not rel:
        raise HTTPException(status_code=404, detail="Release não encontrado")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"release_{entity_id}_{file.filename}"
    filepath = UPLOADS_DIR / filename

    with filepath.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    pdf_path = f"uploads/{filename}"
    release.update_release(entity_id, {"pdf_path": pdf_path})

    pdf_full_path = UPLOADS_DIR.parent / pdf_path
    try:
        pdf_reader = PDFReaderService()
        activity_ids = pdf_reader.extract_and_save(str(pdf_full_path), entity_id)
    except Exception as e:
        return ok(
            {"pdf_path": pdf_path, "activities_created": 0, "error": str(e)},
            module=MODULE,
            meta={"action": "uploaded_but_extraction_failed"},
        )

    return ok(
        {"pdf_path": pdf_path, "pdf_url": f"/{pdf_path}", "activities_created": len(activity_ids), "activity_ids": activity_ids},
        module=MODULE,
        meta={"action": "uploaded_and_processed"},
    )


@router.get("/{entity_id}/atividades")
async def get_release_atividades(entity_id: int):
    rel = release.get_release(entity_id)
    if not rel:
        raise HTTPException(status_code=404, detail="Release não encontrado")
    return ok_list(list_by_release(entity_id), module=MODULE)
