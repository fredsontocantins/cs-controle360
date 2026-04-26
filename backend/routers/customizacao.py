"""Customização API router — fully independent module."""

from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List
import shutil
from pathlib import Path

from ..models import customizacao
from ..schemas import customizacao as schema
from ..config import UPLOADS_DIR
from ..response import ok, ok_list, ok_deleted

MODULE = "customizacao"
router = APIRouter(prefix="/customizacao", tags=["customizacao"])


@router.get("/stats")
async def get_stats():
    items = customizacao.list_customizacao()
    total = len(items)
    by_status: dict[str, int] = {}
    by_module: dict[str, int] = {}
    for item in items:
        s = item.get("status") or "sem_status"
        by_status[s] = by_status.get(s, 0) + 1
        m = item.get("module") or "sem_modulo"
        by_module[m] = by_module.get(m, 0) + 1
    return ok(
        {"total": total, "by_status": by_status, "by_module": by_module},
        module=MODULE,
    )


@router.get("")
async def list_customizacoes():
    return ok_list(customizacao.list_customizacao(), module=MODULE)


@router.get("/{entity_id}")
async def get_customizacao(entity_id: int):
    result = customizacao.get_customizacao(entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Customização não encontrada")
    return ok(result, module=MODULE)


@router.post("")
async def create_customizacao(data: schema.CustomizacaoCreate):
    entity_id = customizacao.insert_customizacao(data.model_dump())
    return ok(customizacao.get_customizacao(entity_id), module=MODULE, meta={"action": "created"})


@router.put("/{entity_id}")
async def update_customizacao(entity_id: int, data: schema.CustomizacaoUpdate):
    success = customizacao.update_customizacao(entity_id, data.model_dump(exclude_unset=True))
    if not success:
        raise HTTPException(status_code=404, detail="Customização não encontrada")
    return ok(customizacao.get_customizacao(entity_id), module=MODULE, meta={"action": "updated"})


@router.delete("/{entity_id}")
async def delete_customizacao(entity_id: int):
    success = customizacao.delete_customizacao(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Customização não encontrada")
    return ok_deleted(module=MODULE)


@router.post("/{entity_id}/upload-pdf")
async def upload_pdf(entity_id: int, file: UploadFile = File(...)):
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    custom = customizacao.get_customizacao(entity_id)
    if not custom:
        raise HTTPException(status_code=404, detail="Customização não encontrada")

    filename = f"customizacao_{entity_id}_{file.filename}"
    filepath = UPLOADS_DIR / filename

    with filepath.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    pdf_path = f"uploads/{filename}"
    customizacao.update_customizacao(entity_id, {"pdf_path": pdf_path})

    return ok({"pdf_path": pdf_path}, module=MODULE, meta={"action": "uploaded"})
